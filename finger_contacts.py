"""Bounded authored-chain fingertip contact with a known keyboard surface."""
import numpy as np
from joint_limits import limit_rotation
from vrm import aim

def key_press(model,world,side,finger,height,weight):
    hands=model.hand_poses;chain=hands.chain(side,finger)
    if side not in hands.hands or any(n is None for n in chain) or weight<.01:return
    d=model.data;physics=model.hair_springs.physics;last=chain[-1]
    extension=np.linalg.solve(d.rest[last,:3,:3],(d.rest[last,:3,3]-d.rest[chain[-2],:3,3])*.7)
    def tip():return world[last,:3,3]+world[last,:3,:3]@extension
    original=tip();canonical=(d.flip@original-d.origin)*d.scale
    # Never reach for an unrelated surface beyond this finger's workspace.
    if abs(canonical[1]-height)>.075:return
    target=canonical.copy();target[1]=height
    target=d.flip.T@((canonical*(1-weight)+target*weight)/d.scale+d.origin)
    return reach_tip(model,world,side,finger,target)

def reach_tip(model,world,side,finger,target):
    """CCD contact shared by keyboard and actual prop triangle surfaces."""
    hands=model.hand_poses;chain=hands.chain(side,finger)
    if side not in hands.hands or any(n is None for n in chain):return
    d=model.data;last=chain[-1]
    extension=np.linalg.solve(d.rest[last,:3,:3],(d.rest[last,:3,3]-d.rest[chain[-2],:3,3])*.7)
    def tip():return world[last,:3,3]+world[last,:3,:3]@extension
    for _ in range(5):
        if np.linalg.norm(tip()-target)*d.scale<.0015:break
        for node in reversed(chain):
            pivot=world[node,:3,3]
            candidate=aim(tip()-pivot,target-pivot)@world[node,:3,:3]
            parent=world[d.parents[node],:3,:3]
            local=limit_rotation(d.local[node][:3,:3],np.linalg.solve(parent,candidate),70 if node==chain[0] else 95)
            hands.rotate_to(world,node,parent@local)
