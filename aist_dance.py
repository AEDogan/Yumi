"""Retarget source world rotations onto each avatar's measured bind axes."""
from functools import lru_cache
from pathlib import Path
import numpy as np
from vrm import rotation,aim

ROOT=Path(__file__).resolve().parent
MAPPING={'hips':0,'leftUpperLeg':1,'rightUpperLeg':2,'spine':3,'leftLowerLeg':4,'rightLowerLeg':5,'chest':6,'leftFoot':7,'rightFoot':8,'upperChest':9,'leftToes':10,'rightToes':11,'neck':12,'leftShoulder':13,'rightShoulder':14,'head':15,'leftUpperArm':16,'rightUpperArm':17,'leftLowerArm':18,'rightLowerArm':19,'leftHand':20,'rightHand':21}

@lru_cache(maxsize=7)
def load(style):
    with np.load(ROOT/'motions'/f'aist-{style}.npz',allow_pickle=False) as source:
        return source['q'].astype(float),source['move'].astype(float),float(source['fps'])

class AistDance:
    uses_stage_bounds=True;pole=False;max_root_offset=1.2
    def __init__(self,style='house'):
        self.style=style;self.path=Path('Yumi-AIST-'+style);self.q,self.move,self.fps=load(style);self.duration=(len(self.q)-1)/self.fps;self.bind={}
    def presence(self,t):return 1.
    def frame_bounds(self,d):
        from scene_framing import corners
        return corners([-1.8,0,-1.8],[1.8,4.,1.8]),corners([-1.8,0,-1.8],[1.8,0,1.8])
    def pose(self,t,d,loop=True):
        frame=(max(0.,t)%self.duration if loop else min(max(0.,t),self.duration))*self.fps;i=min(int(frame),len(self.q)-2);u=frame-i
        a=self.q[i];b=self.q[i+1];b=np.where(np.sum(a*b,axis=1)[:,None]<0,-b,b);q=a*(1-u)+b*u;q/=np.linalg.norm(q,axis=1)[:,None]
        source=np.array([rotation(value) for value in q]);j=d.bones
        if id(d) not in self.bind:
            canonical={name:(d.rest[node,:3,3]@d.flip.T-d.origin)*d.scale for name,node in j.items()};calibration={}
            for name,index in MAPPING.items():
                if name not in j:continue
                direction=None;goal=None
                for side in ('left','right'):
                    if name.startswith(side):
                        suffix=name[len(side):];child={'UpperArm':'LowerArm','LowerArm':'Hand','UpperLeg':'LowerLeg','LowerLeg':'Foot','Foot':'Toes','Hand':'MiddleProximal'}.get(suffix)
                        if child and side+child in j:
                            direction=canonical[side+child]-canonical[name]
                            goal=np.array([1. if side=='left' else -1.,0.,0.]) if suffix in ('UpperArm','LowerArm','Hand') else np.array([0.,0.,1.]) if suffix=='Foot' else np.array([0.,-1.,0.])
                calibration[name]=np.eye(3) if direction is None else aim(direction,goal)
            self.bind[id(d)]=(canonical,calibration)
        canonical,calibration=self.bind[id(d)];desired={}
        for name,index in MAPPING.items():
            if name in j:desired[j[name]]=d.flip.T@source[index]@calibration[name]@d.flip@d.rest[j[name],:3,:3]
        rotations={};world={}
        for node in d.order:
            parent=world[d.parents[node]] if node in d.parents else np.eye(3)
            local=np.linalg.solve(parent,desired[node]) if node in desired else d.local[node][:3,:3]
            if node in desired:rotations[node]=local
            world[node]=parent@local
        movement=self.move[i]*(1-u)+self.move[i+1]*u
        movement=movement.copy();movement[[0,2]]=.5*np.tanh(movement[[0,2]]/.5);movement[1]=np.clip(movement[1],-.14,.18)
        shift=d.flip.T@(movement/d.scale)
        return rotations,shift,{'happy':.15}
