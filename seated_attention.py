"""Bounded, damped viewer attention without turning the seated torso."""
import math
import numpy as np
from hand_pose import turn
from joint_limits import limit_rotation


class SeatedAttention:
    def __init__(self):
        self.angle=0.
        self.last=None

    def apply(self,model,world,t,speaking):
        dt=0. if self.last is None else max(0.,min(.06,t-self.last))
        self.last=t
        d=model.data;rig=model.seating;target=0.
        weight=0. if rig is None else 1. if getattr(rig,'standing_attention',False) else rig.weight
        if rig is not None and weight>0 and speaking:
            head=d.bones.get('head')
            if head is not None:
                forward=world[head,:3,:3]@np.linalg.solve(d.rest[head,:3,:3],d.flip.T@np.array([0.,0.,1.]))
                forward=d.flip@forward
                yaw=math.atan2(float(forward[0]),float(forward[2]))
                desired=math.radians(getattr(rig,'viewer_yaw',0.))
                delta=(desired-yaw+math.pi)%(2*math.pi)-math.pi
                target=float(np.clip(delta,-math.radians(42),math.radians(42)))*weight
        # Ease into eye contact and back toward the display. No snap at speech
        # boundaries, and no large turn after a render pause or a stalled frame.
        change=(target-self.angle)*(1-math.exp(-dt/(.24 if speaking else .42)))
        self.angle+=float(np.clip(change,-math.radians(85)*dt,math.radians(85)*dt))
        if rig is None or weight<=0:
            self.angle=0.;return
        amount=self.angle*weight
        nodes=[(d.bones[n],share) for n,share in (('neck',.28),('head',.72)) if n in d.bones]
        total=sum(share for _,share in nodes)
        for node,share in nodes:
            rotation=d.flip.T@turn(np.array([0.,1.,0.]),amount*share/total)@d.flip
            parent=world[d.parents[node],:3,:3] if node in d.parents else np.eye(3)
            local=np.linalg.solve(parent,rotation@world[node,:3,:3])
            # Preserve the existing nod/tilt, with the same anatomical joint
            # envelope used for the other animations.
            bounded=parent@limit_rotation(d.local[node][:3,:3],local,45.)
            model.hair_springs.physics._rotate_subtree(world,node,bounded@np.linalg.inv(world[node,:3,:3]))
