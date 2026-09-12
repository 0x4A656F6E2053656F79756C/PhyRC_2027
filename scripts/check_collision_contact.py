"""Numeric collision-surface tests independent of Isaac and its solver."""
from pathlib import Path
import sys
import unittest
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src/DexGarmentLab'))
from Policy.evaluation_contact import (CollisionContact, TriangleTree, triangle_pairs_touch,
    segment_distance_squared, point_triangle_distance_squared)


class ContactTests(unittest.TestCase):
    def test_parallel_triangle_offset_threshold(self):
        a = np.array([[[0., 0, 0], [2, 0, 0], [0, 2, 0]]])
        for distance, expected in ((.015, False), (.014, True), (.013, True)):
            self.assertEqual(triangle_pairs_touch(a, a + [0, 0, distance], .014), expected)

    def test_edge_face_crossing_without_close_vertices(self):
        a = np.array([[[-2., -2, 0], [2, -2, 0], [0, 2, 0]]])
        b = np.array([[[-.5, 0, -2], [.5, 0, 2], [.5, 0, -2]]])
        self.assertGreater(point_triangle_distance_squared(b[:, 0], a)[0], 1)
        self.assertTrue(triangle_pairs_touch(a, b, 0))
        self.assertFalse(triangle_pairs_touch(a, b + [10, 0, 0], .014))

    def test_edge_edge_minimum_and_degenerate_segments(self):
        p, q = np.array([[-1., 0, 0]]), np.array([[1., 0, 0]])
        a, b = np.array([[0., -1, .01]]), np.array([[0., 1, .01]])
        self.assertAlmostEqual(segment_distance_squared(p, q, a, b)[0], .0001)
        self.assertAlmostEqual(segment_distance_squared(p, q, a, a)[0], 1.0001)
        self.assertAlmostEqual(segment_distance_squared(p, p, a, b)[0], 1.0001)
        self.assertAlmostEqual(segment_distance_squared(p, q, p + [0, 2, 0], q + [0, 2, 0])[0], 4)

    def test_bvh_matches_all_pairs_and_rigid_transform(self):
        rng = np.random.default_rng(0)
        body = rng.normal(size=(50, 3, 3))
        garment = rng.normal(size=(3, 3, 3))
        rotation = np.array([[0, -1, 0], [1, 0, 0], [0, 0, 1]])
        for offset in (0, 3, 30):
            cloth = garment + offset
            expected = triangle_pairs_touch(np.repeat(cloth, len(body), 0), np.tile(body, (len(cloth), 1, 1)), .014)
            for transform in (False, True):
                c, b = (cloth @ rotation + 10, body @ rotation + 10) if transform else (cloth, body)
                self.assertEqual(TriangleTree(b).touches(c, c.min(1), c.max(1), .014), expected)

    def test_cloth_face_interior_sphere_contact_and_human_transform(self):
        context = dict(version=1, garment_faces=[[0, 1, 2]], garment_contact_offset_m=.008,
                       colliders=[dict(path='/World/Human/HandSphere', type='sphere', points=[[0, 0, 0]],
                                       radius=.1, contact_offset_m=.006)])
        human = np.eye(4); human[3, :3] = [2, 3, 4]
        detector = CollisionContact(context, human)
        tri = np.array([[-2, -2, .113], [2, -2, .113], [0, 2, .113]]) + [2, 3, 4]
        self.assertTrue(detector.touches(tri))
        self.assertEqual(detector.last_collider, '/World/Human/HandSphere')
        self.assertFalse(detector.touches(tri + [0, 0, .002]))


if __name__ == '__main__':
    unittest.main(verbosity=2)
