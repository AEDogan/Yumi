"""Shared constrained arm solve for activity targets and placement fitting."""
import numpy as np
from motion import ik
from vrm import aim
from joint_limits import limit_rotation

def solve_hand(model,world,side,goal,returning=False,preserve_elbow=False,elbow_pole=None):
    d=model.data;physics=model.hair_springs.physics
    a,b,c=[d.bones[side+p] for p in ('UpperArm','LowerArm','Hand')]
    shoulder,elbow,hand=[world[n,:3,3].copy() for n in (a,b,c)]
    target=d.flip.T@(np.asarray(goal)/d.scale+d.origin)
    sign=1 if model.rest_canonical[side+'UpperArm'][0]>=model.rest_canonical['hips'][0] else -1
    pole=elbow-shoulder if preserve_elbow else d.flip.T@np.array([sign*.22,-1.,.35])
    if elbow_pole is not None:pole=elbow_pole
    knee,tip=ik(shoulder,target,np.linalg.norm(elbow-shoulder),np.linalg.norm(hand-elbow),pole,132)
    physics._rotate_subtree(world,a,aim(elbow-shoulder,knee-shoulder))
    neutral=world[d.parents[b],:3,:3]@d.local[b][:3,:3]
    source=neutral@np.linalg.solve(d.rest[b,:3,:3],d.rest[c,:3,3]-d.rest[b,:3,3])
    target_rotation=aim(source,tip-world[b,:3,3])@neutral;parent=world[d.parents[b],:3,:3]
    target_rotation=parent@limit_rotation(d.local[b][:3,:3],np.linalg.solve(parent,target_rotation),134.)
    if returning:target_rotation=aim(world[c,:3,3]-world[b,:3,3],tip-world[b,:3,3])@world[b,:3,:3]
    physics._rotate_subtree(world,b,target_rotation@np.linalg.inv(world[b,:3,:3]))
    neutral_hand=world[b,:3,:3]@np.linalg.solve(d.rest[b,:3,:3],d.rest[c,:3,:3])
    physics._rotate_subtree(world,c,neutral_hand@np.linalg.inv(world[c,:3,:3]))
    model.hand_poses.fingers(world,side,'relaxed')
