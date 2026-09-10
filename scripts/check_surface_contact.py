"""GPU regressions for continuous triangle contact, including thin tip tunnelling."""
import json
from pathlib import Path
import sys
sys.path.insert(0, '/project/src/DexGarmentLab')
from policy_cli import install_failure_handler
install_failure_handler()
import Env_StandAlone.Teleop_TShirt_Stretch4_Env as M
import numpy as np
import torch
import warp as wp
from Env_Config.Garment.SurfaceContactGuard import SurfaceContactGuard, _unit_interval_roots, _swept_edge_edge


@wp.kernel
def solve_roots(coefficients: wp.array(dtype=wp.vec4), roots: wp.array(dtype=wp.vec3)):
    c = coefficients[wp.tid()]
    roots[wp.tid()] = _unit_interval_roots(c[0], c[1], c[2], c[3])


@wp.kernel
def edge_control(result: wp.array(dtype=int)):
    result[0] = _swept_edge_edge(wp.vec3(0.,-.02,.004), wp.vec3(0.,.02,.004),
        wp.vec3(0.,0.,-.008), wp.vec3(0.,0.,-.008), wp.vec3(-.02,0.,0.), wp.vec3(.02,0.,0.))
    result[1] = _swept_edge_edge(wp.vec3(.03,-.02,.004), wp.vec3(.03,.02,.004),
        wp.vec3(0.,0.,-.008), wp.vec3(0.,0.,-.008), wp.vec3(-.02,0.,0.), wp.vec3(.02,0.,0.))


rng = np.random.default_rng(2027)
polynomials, expected = [], []
for degree in (1, 2, 3):
    for _ in range(100):
        roots = np.sort(rng.uniform(-.5, 1.5, degree))
        if degree > 1 and np.min(np.diff(roots)) < .03:
            continue
        coefficients = np.pad(np.poly(roots)[::-1], (0, 3-degree))
        polynomials.append(coefficients)
        expected.append(roots[(roots>0) & (roots<1)])
values = wp.array(np.array(polynomials), dtype=wp.vec4, device='cuda:0')
roots = wp.empty(len(polynomials), dtype=wp.vec3, device='cuda:0')
wp.launch(solve_roots, len(polynomials), inputs=[values,roots])
for want, found in zip(expected, roots.numpy()):
    found = np.sort(found[found>=0])
    np.testing.assert_allclose(found, want, atol=2e-4, rtol=0)
edges_result = wp.zeros(2,dtype=int,device='cuda:0')
wp.launch(edge_control, 1, inputs=[edges_result])
assert edges_result.numpy().tolist() == [1,0]

tip = np.array([[0,0,.001],[-.001,-.001,-.001],[.001,-.001,-.001],[0,.001,-.001]],dtype=np.float32)
body_tri = np.array([[0,1,2],[0,2,3],[0,3,1],[1,3,2]],dtype=np.int32)
sheet = np.array([[-.02,-.02,.004],[.02,-.02,.004],[0,.02,.004]],dtype=np.float32)
end = sheet + [0,0,-.008]
edges = torch.tensor([[0,1],[1,2],[2,0]],dtype=torch.int32,device='cuda:0')
tri = torch.tensor([[0,1,2]],dtype=torch.int32,device='cuda:0')
results = []
for use_graph in (False,True):
    for yaw, tilt in ((0,0),(-30,20),(30,-20),(-26.88,0)):
        a,b = np.radians([yaw,tilt])
        rotation = np.array([[np.cos(a),-np.sin(a),0],[np.sin(a),np.cos(a),0],[0,0,1]]) @ np.array([[1,0,0],[0,np.cos(b),-np.sin(b)],[0,np.sin(b),np.cos(b)]])
        def tensor(p):
            return torch.as_tensor(np.asarray(p)@rotation.T+[.05,-.02,.1],dtype=torch.float32,device='cuda:0')
        guard = SurfaceContactGuard(tensor(tip).cpu().numpy(),body_tri,'cuda:0',use_graph=use_graph)
        start,target = tensor(sheet),tensor(end)
        assert guard.count_intersections(start,edges,tri)==0
        assert guard.count_intersections(target,edges,tri)==0
        assert guard.count_intersections((start+target)/2,edges,tri)>0
        safe,_ = guard.sweep(start,target,torch.zeros_like(start),edges,tri)
        assert not torch.allclose(safe,target), 'A tip crossed the face interior undetected'
        assert guard.count_intersections(safe,edges,tri)==0
        # Free corners may slide below the tip while the face tilts above it.
        # The tip must remain on its original side of the triangle's plane.
        local = (safe.cpu().numpy()-[.05,-.02,.1])@rotation
        normal = np.cross(local[1]-local[0],local[2]-local[0])
        normal /= np.linalg.norm(normal)
        assert np.max((tip-local[0])@normal) < 1e-5, local
        tangent = tensor(sheet+[.01,0,0])
        moved,_ = guard.sweep(start,tangent,torch.zeros_like(start),edges,tri)
        torch.testing.assert_close(moved,tangent,atol=1e-6,rtol=0)
        far_start,far_end = tensor(sheet+[.1,0,0]),tensor(end+[.1,0,0])
        moved,_ = guard.sweep(far_start,far_end,torch.zeros_like(start),edges,tri)
        torch.testing.assert_close(moved,far_end,atol=1e-6,rtol=0)
        results.append({'graph':use_graph,'yaw_deg':yaw,'tilt_deg':tilt,'passed':True})
report = {'passed':True,'polynomial_controls':len(polynomials),'edge_controls':[True,False],
          'thin_tip_controls':results,'scope':'8mm triangle travel across a 2mm tip; tangential and free paths preserved'}
path = Path('/output/verification/surface-contact.json')
path.parent.mkdir(parents=True,exist_ok=True)
path.write_text(json.dumps(report,indent=2)+'\n')
print('SURFACE-CONTACT-PASS',report,flush=True)
M.simulation_app.close()
