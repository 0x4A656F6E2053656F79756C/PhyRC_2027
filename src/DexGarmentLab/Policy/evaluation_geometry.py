"""Numerical dressing measurements; no simulation or physics mutations.

Coverage is the fraction of the shoulder-elbow-wrist centreline enclosed by a
virtually capped garment. Cuff routing is checked separately so merely placing
cloth near an arm is insufficient. This is a documented geometric proxy, not a
surface-area metric specified by the proposal.
"""
import numpy as np


def boundary_loops(faces):
    faces = np.asarray(faces, dtype=int)
    directed = np.concatenate((faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]))
    _, inverse, counts = np.unique(np.sort(directed, axis=1), axis=0,
                                    return_inverse=True, return_counts=True)
    if np.any(counts > 2):
        raise ValueError('Garment must be a manifold triangle mesh')
    edges = directed[counts[inverse] == 1]
    following = dict(map(tuple, edges))
    if len(following) != len(edges) or set(following) != set(following.values()):
        raise ValueError('Garment boundary must have consistently oriented simple loops')
    loops = []
    while following:
        start = next(iter(following))
        loop, current = [], start
        while current in following:
            loop.append(current)
            current = following.pop(current)
        if current != start or len(loop) < 3:
            raise ValueError('Broken garment boundary')
        loops.append(np.asarray(loop, dtype=int))
    return loops


def capped_mesh(points, faces, loops):
    """Close openings for numeric containment ONLY; never write these to USD."""
    vertices = np.vstack((points, [points[ids].mean(0) for ids in loops]))
    caps = [[int(b), int(a), len(points) + i] for i, ids in enumerate(loops)
            for a, b in zip(ids, np.roll(ids, -1))]
    return vertices, np.vstack((faces, np.asarray(caps)))


def inside_mesh(queries, points, faces):
    """Generalized winding magnitude > 1/2 on an oriented closed surface."""
    queries, points = np.asarray(queries, float), np.asarray(points, float)
    result = np.zeros(len(queries), bool)
    if not len(queries):
        return result
    candidate = np.all((queries > points.min(0)) & (queries < points.max(0)), axis=1)
    triangles = points[np.asarray(faces)]
    for index in np.flatnonzero(candidate):
        a, b, c = (triangles[:, i] - queries[index] for i in range(3))
        la, lb, lc = (np.linalg.norm(v, axis=1) for v in (a, b, c))
        numerator = np.einsum('ij,ij->i', a, np.cross(b, c))
        denominator = (la * lb * lc + np.einsum('ij,ij->i', a, b) * lc
                       + np.einsum('ij,ij->i', b, c) * la
                       + np.einsum('ij,ij->i', c, a) * lb)
        winding = np.sum(2 * np.arctan2(numerator, denominator)) / (4 * np.pi)
        result[index] = abs(winding) > 0.5
    return result


def cuff_crossing(loop, inner_points, chain, planarity_limit=0.6):
    """Find an arm-chain crossing of a cuff polygon in either direction.

    chain contains shoulder, elbow, wrist, and a distal hand point. Nonplanar
    or collapsed cuffs are rejected instead of inferring entry from proximity.
    Returns the crossing position along the polyline, or None.
    """
    centre = loop.mean(0)
    _, singular, axes = np.linalg.svd(loop - centre, full_matrices=False)
    if singular[1] < 1e-5 or singular[2] / singular[1] > planarity_limit:
        return None
    normal = axes[2]
    if np.dot(normal, centre - inner_points.mean(0)) < 0:
        normal = -normal
    polygon = (loop - centre) @ axes[:2].T
    distance = 0.0
    for p, q in zip(chain, chain[1:]):
        length = np.linalg.norm(q - p)
        a, b = np.dot(p - centre, normal), np.dot(q - centre, normal)
        if (a < -1e-5 and b > 1e-5) or (a > 1e-5 and b < -1e-5):
            fraction = -a / (b - a)
            point = (p + fraction * (q - p) - centre) @ axes[:2].T
            inside = False
            for u, v in zip(polygon, np.roll(polygon, -1, axis=0)):
                if (u[1] > point[1]) != (v[1] > point[1]):
                    x = u[0] + (point[1] - u[1]) * (v[0] - u[0]) / (v[1] - u[1])
                    if point[0] < x:
                        inside = not inside
            if inside:
                return float(distance + fraction * length)
        distance += length
    return None


class GarmentGeometry:
    def __init__(self, rest_points, faces, coverage_samples=40):
        self.faces = np.asarray(faces, int)
        self.loops = boundary_loops(self.faces)
        if len(self.loops) != 4:
            raise ValueError('Evaluation currently requires a shirt with four openings')
        # Current T-shirt rest coordinates: sleeves are the two X extremes.
        ordered = sorted(self.loops, key=lambda ids: rest_points[ids, 0].mean())
        self.cuffs = [ordered[0], ordered[-1]]
        centres = [rest_points[ids, 0].mean() for ids in ordered]
        if min(centres[1] - centres[0], centres[-1] - centres[-2]) < 0.05:
            raise ValueError('Cannot identify two distinct rest-shape cuffs')
        self.inner = [np.setdiff1d(np.unique(self.faces[np.isin(self.faces, ids).any(1)]), ids)
                      for ids in self.cuffs]
        # Of the remaining torso openings the collar has the smaller perimeter.
        torso = ordered[1:-1]
        self.collar = min(torso, key=lambda ids: np.linalg.norm(
            np.diff(np.vstack((rest_points[ids], rest_points[ids[:1]])), axis=0), axis=1).sum())
        self.collar_inner = np.setdiff1d(np.unique(self.faces[np.isin(self.faces, self.collar).any(1)]), self.collar)
        self.coverage_samples = coverage_samples

    def measure(self, points, arms, neck_chain=None, head_surface=None):
        vertices, closed_faces = capped_mesh(points, self.faces, self.loops)
        wrists, coverage, diagnostic = {}, {}, {}
        used_cuffs = {}
        for side, chain in arms.items():
            chain = np.asarray(chain)
            lengths = np.linalg.norm(np.diff(chain[:3], axis=0), axis=1)
            arm_length = lengths.sum()
            positions = (np.arange(self.coverage_samples) + 0.5) / self.coverage_samples * arm_length
            probes = np.array([chain[0] + d / lengths[0] * (chain[1] - chain[0])
                               if d < lengths[0] else
                               chain[1] + (d - lengths[0]) / lengths[1] * (chain[2] - chain[1])
                               for d in positions])
            crossings = [(i, cuff_crossing(points[ids], points[inner], chain))
                         for i, (ids, inner) in enumerate(zip(self.cuffs, self.inner))]
            valid = [(i, d) for i, d in crossings if d is not None]
            # A forearm/wrist must route through exactly one physical cuff.
            route = len(valid) == 1
            contained = inside_mesh(np.vstack((probes, chain[2:])), vertices, closed_faces)
            i, distance = valid[0] if route else (None, None)
            # During first entry, wrist is inside and the cuff is still distal
            # to it. After advancement the wrist is outside past the cuff;
            # require some proximal arm containment to keep routing valid.
            wrists[side] = bool(route and (contained[-2] or
                                          (distance < arm_length and contained[:-2].any())))
            coverage[side] = float(contained[:-2].mean()) if wrists[side] else 0.0
            used_cuffs[side] = i if wrists[side] else None
            diagnostic[side] = {'cuff_index': i, 'crossing_distance_from_shoulder_m': distance,
                                'arm_length_m': float(arm_length), 'centreline_coverage': coverage[side],
                                'hand_out': bool(wrists[side] and distance < arm_length
                                                 and not contained[-2:].any())}
        # Both arms passing the same opening do not dress two sleeves.
        if used_cuffs.get('left') is not None and used_cuffs.get('left') == used_cuffs.get('right'):
            wrists = {side: False for side in arms}
            coverage = {side: 0.0 for side in arms}
            for side in arms:
                diagnostic[side]['hand_out'] = False
        if neck_chain is not None:
            # Chest must be in the torso, neck/head outside through the COLLAR,
            # not merely near the neckline or through a sleeve/hem.
            chain = np.asarray(neck_chain)
            crossing = cuff_crossing(points[self.collar], points[self.collar_inner], chain)
            inside = inside_mesh(chain, vertices, closed_faces)
            # A skeleton's neck joint can lie BELOW a properly seated collar.
            # Test exposed head skin instead of requiring that internal joint
            # to be outside. This rejects a neckline still caught on the face.
            neck_distance = float(np.linalg.norm(chain[1] - chain[0]))
            head_clearance = None
            if head_surface is not None:
                loop = points[self.collar]
                centre = loop.mean(0)
                _, _, axes = np.linalg.svd(loop - centre, full_matrices=False)
                normal = axes[2]
                if np.dot(normal, centre - points[self.collar_inner].mean(0)) < 0:
                    normal = -normal
                head_clearance = float(np.min((np.asarray(head_surface) - centre) @ normal))
            neck_out = bool(crossing is not None and inside[0] and not inside[-1]
                            and (head_clearance >= -0.005 if head_clearance is not None
                                 else crossing < neck_distance and not inside[1]))
            diagnostic['neck'] = {'neck_out': neck_out, 'collar_crossing_from_chest_m': crossing,
                                  'chest_neck_head_inside': inside.tolist(),
                                  'head_min_clearance_above_collar_m': head_clearance}
            diagnostic['dressing_complete'] = bool(neck_out and all(wrists.get(s, False)
                and diagnostic[s]['hand_out'] for s in ('left', 'right')))
        return wrists, coverage, diagnostic
