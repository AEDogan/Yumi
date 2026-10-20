"""Sole geometry grounding and the desktop camera's perspective floor anchor."""
import math
import numpy as np

EYE=np.array([0.,1.8,8.5])
FORWARD=np.array([0.,-.33,-8.5]);FORWARD/=np.linalg.norm(FORWARD)
UP=np.cross([1.,0.,0.],FORWARD)
TAN_HALF_FOV=math.tan(math.radians(35)/2)
FLOOR_NDC=float((-EYE)@UP/((-EYE)@FORWARD))

def ground_pixel(height):return height*(1-FLOOR_NDC/TAN_HALF_FOV)/2

def projected_floor_offset(points,yaw=0.):
    if points is None or not len(points):return 0.
    a=math.radians(yaw);c,s=math.cos(a),math.sin(a)
    turn=np.array([[c,0,s],[0,1,0],[-s,0,c]])
    camera=np.asarray(points)@turn.T-EYE
    # Translate along camera-up, which leaves perspective depth unchanged.
    return float(np.max(FLOOR_NDC*(camera@FORWARD)-camera@UP))

class SoleGround:
    """Only vertices weighted to the foot/toes determine the support surface."""
    def __init__(self,data):
        self.data=data;self.groups=[];self.points=None;self.shift=0.;self.enabled=True;self.fallback=False
        self.foot_families={};self.plant_active=False;self.plant_started=None;self.plant_anchors={}
        records=[]
        for side in ('left','right'):
            foot=data.bones[side+'Foot'];ankle=data.rest[foot,:3,3]@data.flip.T
            knee=data.rest[data.bones[side+'LowerLeg'],:3,3]@data.flip.T
            leg=max(float(np.linalg.norm(ankle-knee)),1e-5)
            family={foot}
            for node in data.order:
                if data.parents.get(node) in family:family.add(node)
            self.foot_families[side]=family
            candidates=[]
            for part in data.parts:
                if part['skin'] is None or 'joints' not in part:continue
                nodes,inverse=data.skins[part['skin']];ids=part['joints'];weights=part['weights']
                mass=(np.isin(nodes[ids],list(family))*weights).sum(axis=1)
                chosen=np.intersect1d(np.flatnonzero(mass>=.5),np.unique(part['indices']))
                if not len(chosen):continue
                p=np.column_stack((part['pos'][chosen],np.ones(len(chosen))))
                matrices=data.rest[nodes]@inverse;posed=np.zeros((len(p),4))
                for k in range(4):posed+=np.einsum('nij,nj->ni',matrices[ids[chosen,k]],p)*weights[chosen,k,None]
                canonical=posed[:,:3]@data.flip.T
                near=(np.linalg.norm(canonical[:,[0,2]]-ankle[[0,2]],axis=1)<leg*.85)&(canonical[:,1]<ankle[1]+leg*.18)&(canonical[:,1]>ankle[1]-leg*.55)
                if np.any(near):candidates.append((part,chosen[near],canonical[near]))
            if candidates:
                lowest=min(float(p[:,1].min()) for _,_,p in candidates)
                for part,chosen,canonical in candidates:
                    band=canonical[:,1]<=lowest+leg*.10
                    chosen=chosen[band];canonical=canonical[band]
                    if not len(chosen):continue
                    # Preserve extrema; use a bounded interior sample on large shoes.
                    if len(chosen)>256:
                        keep=np.unique(np.r_[np.linspace(0,len(chosen)-1,250,dtype=int),canonical.argmin(axis=0),canonical.argmax(axis=0)])
                        chosen=chosen[keep]
                    records.append((part,chosen))
            else:
                self.fallback=True
                point=data.rest[foot,:3,3].copy()+data.flip.T@np.array([0.,-leg*.12,0.])
                local=np.linalg.solve(data.rest[foot],np.r_[point,1.])
                self.groups.append(('node',foot,local[None,:],None,None))
        for part,chosen in records:
            self.groups.append(('skin',part['skin'],np.column_stack((part['pos'][chosen],np.ones(len(chosen)))),part['joints'][chosen],part['weights'][chosen]))
        merged={};others=[]
        for kind,index,positions,ids,weights in self.groups:
            if kind=='node':others.append((kind,index,positions,ids,weights));continue
            merged.setdefault(index,[]).append((positions,ids,weights))
        self.groups=others
        for index,items in merged.items():
            positions=np.concatenate([x[0] for x in items]);ids=np.concatenate([x[1] for x in items]);weights=np.concatenate([x[2] for x in items])
            self.groups.append(('skin',index,positions,ids,weights))
        self.side_masks={}
        for side,family in self.foot_families.items():
            masks=[]
            for kind,index,positions,ids,weights in self.groups:
                if kind=='node':masks.append(np.full(len(positions),index in family))
                else:
                    nodes=data.skins[index][0];masks.append((np.isin(nodes[ids],list(family))*weights).sum(axis=1)>=.5)
            self.side_masks[side]=np.concatenate(masks)
    def sample(self,world,side=None):
        points=[];data=self.data;palettes={}
        for kind,index,positions,ids,weights in self.groups:
            if kind=='node':posed=positions@world[index].T
            else:
                if index not in palettes:
                    nodes,inverse=data.skins[index];palettes[index]=world[nodes]@inverse
                palette=palettes[index];posed=np.zeros((len(positions),4))
                for k in range(4):posed+=np.einsum('nij,nj->ni',palette[ids[:,k]],positions)*weights[:,k,None]
            points.append((posed[:,:3]@data.flip.T-data.origin)*data.scale)
        result=np.concatenate(points)
        return result if side is None else result[self.side_masks[side]]
    def plant(self,world,pose,t,physics):
        """Idle feet stay planted; walking and explicit clips keep authored lifts."""
        active=self.enabled and pose in ('idle','wave','listen')
        if not active:self.plant_active=False;self.plant_anchors={};return
        d=self.data
        if not self.plant_active:
            first=self.plant_started is None;self.plant_started=t-.3 if first else t
            source=d.rest if getattr(self,'neutral_pending',False) else world
            self.plant_anchors={side:source[d.bones[side+'Foot'],:3,3].copy() for side in ('left','right')}
            self.neutral_pending=False
        self.plant_active=True
        u=max(0.,min(1.,(t-self.plant_started)/.3));weight=u*u*(3-2*u)
        if weight<=0:return
        from vrma import slerp
        from natural_walk import matrix_quaternion
        from vrm import rotation,aim
        from motion import ik
        rotations={}
        for side in ('left','right'):
            node=d.bones[side+'Foot'];current=world[node,:3,:3]
            # Both sole surfaces have their bind orientation at rest, instead
            # of inheriting a raised heel from a retargeted talking clip.
            target=rotation(slerp(matrix_quaternion(current),matrix_quaternion(d.rest[node,:3,:3]),weight))
            scale=np.linalg.norm(current,axis=0);target=target@np.diag(scale)
            physics._rotate_subtree(world,node,target@np.linalg.inv(current));rotations[side]=world[node,:3,:3].copy()
        soles=self.sample(world)
        minima={side:float(soles[self.side_masks[side],1].min()) for side in ('left','right')};level=min(minima.values())
        goals={};lowering=0.
        for side in ('left','right'):
            a,b,c=[d.bones[side+p] for p in ('UpperLeg','LowerLeg','Foot')]
            foot=world[c,:3,3].copy();anchor=self.plant_anchors[side]
            target=foot+(anchor-foot)*weight;target[1]=foot[1]
            target+=d.flip.T@np.array([0.,(level-minima[side])*weight/d.scale,0.]);goals[side]=target
            hip=world[a,:3,3]@d.flip.T;end=target@d.flip.T
            reach=np.linalg.norm(d.rest[b,:3,3]-d.rest[a,:3,3])+np.linalg.norm(d.rest[c,:3,3]-d.rest[b,:3,3])
            horizontal=float(np.sum((end[[0,2]]-hip[[0,2]])**2))
            lowering=min(lowering,float(end[1]+math.sqrt(max(0.,(reach*.999)**2-horizontal))-hip[1]))
        world[:,:3,3]+=d.flip.T@np.array([0.,lowering,0.])
        for side,target in goals.items():
            a,b,c=[d.bones[side+p] for p in ('UpperLeg','LowerLeg','Foot')]
            hip,knee,foot=[world[n,:3,3].copy() for n in (a,b,c)]
            upper=float(np.linalg.norm(knee-hip));lower=float(np.linalg.norm(foot-knee))
            new_knee,new_foot=ik(hip,target,upper,lower,d.flip.T@np.array([0.,0.,1.]),145)
            physics._rotate_subtree(world,a,aim(knee-hip,new_knee-hip))
            physics._rotate_subtree(world,b,aim(world[c,:3,3]-world[b,:3,3],new_foot-world[b,:3,3]))
            physics._rotate_subtree(world,c,rotations[side]@np.linalg.inv(world[c,:3,:3]))
    def apply(self,world,pose):
        points=self.sample(world);self.shift=0.
        if self.enabled and pose!='clip':
            self.shift=-float(points[:,1].min())
            world[:,:3,3]+=self.data.flip.T@np.array([0.,self.shift/self.data.scale,0.])
            points[:,1]+=self.shift
        self.points=points
