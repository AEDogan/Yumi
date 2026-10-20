"""Model-independent skeletal contact constraints, in the model's native world units.

This is a bounded capsule/particle layer, not triangle cloth or soft-body simulation.
No asset names, file names, external process, package or model-specific constants.
"""
from dataclasses import dataclass
import math
import numpy as np

@dataclass(frozen=True)
class Capsule:
    name:str
    first:int
    second:int
    radius:float

def capsule_distances(point,starts,ends):
    axes=ends-starts;squared=np.einsum('ij,ij->i',axes,axes)
    fraction=np.clip(np.einsum('ij,ij->i',point-starts,axes)/np.maximum(squared,1e-20),0.,1.)
    centers=starts+axes*fraction[:,None];delta=point-centers
    return np.linalg.norm(delta,axis=1),delta,axes

def push_out(point,starts,ends,radii,fallback=None):
    """Resolve the deepest capsule contact; exact-axis contact has a valid normal."""
    if not len(radii):return np.asarray(point,float).copy(),0.
    distances,delta,axes=capsule_distances(point,starts,ends)
    depths=radii-distances;index=int(np.argmax(depths));depth=float(depths[index])
    if depth<=1e-10:return np.asarray(point,float).copy(),0.
    normal=delta[index]
    if distances[index]<1e-10:
        axis=axes[index];axis=axis/max(float(np.linalg.norm(axis)),1e-10)
        normal=np.asarray(fallback if fallback is not None else [1.,0.,0.],float).copy()
        normal-=axis*float(normal@axis)
        if np.linalg.norm(normal)<1e-8:
            basis=np.eye(3)[int(np.argmin(np.abs(axis)))];normal=basis-axis*float(basis@axis)
        normal/=max(float(np.linalg.norm(normal)),1e-10)
    else:normal=normal/distances[index]
    return np.asarray(point,float)+normal*depth,depth

def sweep_capsules(start,end,starts,ends,radii):
    """Earliest entry of a moving point into static capsules, fraction in [0,1]."""
    start=np.asarray(start,float);direction=np.asarray(end,float)-start;speed2=float(direction@direction)
    if speed2<1e-20 or not len(radii):return None
    axes=ends-starts;length2=np.sum(axes*axes,axis=1);offset=start-starts
    dot_axis=axes@direction;dot_offset=np.sum(axes*offset,axis=1)
    a=length2*speed2-dot_axis*dot_axis
    b=length2*(offset@direction)-dot_offset*dot_axis
    c=length2*(np.sum(offset*offset,axis=1)-radii*radii)-dot_offset*dot_offset
    discriminant=b*b-a*c
    times=np.full(len(radii),np.inf)
    valid=(a>1e-16)&(discriminant>=0)&(length2>1e-16)
    root=np.full(len(radii),np.inf);root[valid]=(-b[valid]-np.sqrt(discriminant[valid]))/a[valid]
    along=dot_offset+np.where(valid,root,0.)*dot_axis
    valid&=(root>=0)&(root<=1)&(along>=0)&(along<=length2)
    times[valid]=root[valid]
    for centers in (starts,ends):
        delta=start-centers;half_b=delta@direction;disc=half_b*half_b-speed2*(np.sum(delta*delta,axis=1)-radii*radii)
        valid=disc>=0;root=np.full(len(radii),np.inf)
        root[valid]=(-half_b[valid]-np.sqrt(disc[valid]))/speed2
        valid&=(root>=0)&(root<=1);times=np.minimum(times,np.where(valid,root,np.inf))
    distances,_,_=capsule_distances(start,starts,ends)
    times[(distances<radii-1e-9)|(radii<=1e-10)]=np.inf
    index=int(np.argmin(times));fraction=float(times[index])
    if not np.isfinite(fraction):return None
    point=start+direction*fraction;axis=axes[index];size=length2[index]
    center=starts[index]+axis*np.clip(float((point-starts[index])@axis)/max(size,1e-20),0.,1.)
    normal=point-center;normal/=max(float(np.linalg.norm(normal)),1e-10)
    return fraction,point,normal

class AutoPhysicsRig:
    """Fit once from humanoid semantics and skin geometry; pose colliders each frame."""
    def __init__(self,data):
        self.data=data;self.capsules=[];self.children={i:[] for i in range(len(data.nodes))}
        self.enabled=True
        self.tip_radii={};self.segment_radii={};self.fractions=np.array([.35,.65,1.]);self.corrections=0;self.unresolved=0;self.arm_corrections=0;self.swept_contacts=0
        rest=data.rest;bones=data.bones
        self.height=max(float(np.linalg.norm(rest[bones['head'],:3,3]-rest[bones['hips'],:3,3]))*2.3,1e-5)
        self.margin=self.height*.0015
        self.samples=self._skin_samples()
        for node in data.order:
            ancestor=node
            while ancestor in data.parents:
                ancestor=data.parents[ancestor];self.children[ancestor].append(node)
        chest='upperChest' if 'upperChest' in bones else 'chest' if 'chest' in bones else 'spine' if 'spine' in bones else 'hips'
        neck='neck' if 'neck' in bones else 'head'
        definitions=[('pelvis','leftUpperLeg','rightUpperLeg',.065),('torso','hips',chest,.073),('chest',chest,neck,.065),('head','head','head',.060)]
        for side in ('left','right'):
            definitions.extend([(side+'Thigh',side+'UpperLeg',side+'LowerLeg',.032),(side+'Shin',side+'LowerLeg',side+'Foot',.022),(side+'Arm',side+'UpperArm',side+'LowerArm',.020),(side+'Forearm',side+'LowerArm',side+'Hand',.017),(side+'Palm',side+'Hand',side+'MiddleProximal',.016)])
        for name,first,second,factor in definitions:
            if first not in bones:continue
            a=bones[first];b=bones.get(second,a);base=self.height*factor
            radius=self._fit_radius(a,b,base) if name!='head' else base
            self.capsules.append(Capsule(name,a,b,radius))
        self.arm_body=np.array([i for i,c in enumerate(self.capsules) if c.name in ('pelvis','torso','chest','head','leftThigh','rightThigh')],int)
        self.arm_chains={}
        for side in ('left','right'):
            a,b,c=(bones[side+part] for part in ('UpperArm','LowerArm','Hand'))
            if b in self.children[a] and c in self.children[b]:self.arm_chains[side]=(a,b,c)
        self.starts=np.empty((0,3));self.ends=np.empty((0,3));self.radii=np.empty(0)
        self.update(rest)
    def _skin_samples(self):
        data=self.data;points=[];dominant=[]
        cached=getattr(data,'_contact_samples',None)
        if cached is not None:return cached
        referenced=[np.unique(part['indices']) for part in data.parts]
        total=sum(len(ids) for ids in referenced)
        stride=max(1,math.ceil(total/12000));remaining=16000
        for part,used in zip(data.parts,referenced):
            if part['skin'] is None or 'joints' not in part:continue
            if remaining<=0:break
            chosen=used[::stride][:remaining]
            position=part['pos'][chosen]
            ids=part['joints'][chosen];weights=part['weights'][chosen]
            remaining-=len(position)
            palette,inverse=data.skins[part['skin']];matrices=data.rest[palette]@inverse
            homogeneous=np.column_stack((position,np.ones(len(position))));posed=np.zeros((len(position),4))
            for k in range(ids.shape[1]):posed+=np.einsum('nij,nj->ni',matrices[ids[:,k]],homogeneous)*weights[:,k,None]
            points.append(posed[:,:3]);dominant.append(palette[ids[np.arange(len(ids)),np.argmax(weights,axis=1)]])
        result=(np.concatenate(points),np.concatenate(dominant)) if points else (np.empty((0,3)),np.empty(0,int))
        data._contact_samples=result
        return result
    def _fit_radius(self,first,second,base):
        points,dominant=self.samples;chosen=points[(dominant==first)|(dominant==second)]
        if len(chosen)<12:return base
        start=self.data.rest[first,:3,3];axis=self.data.rest[second,:3,3]-start;squared=float(axis@axis)
        if squared<1e-15:return base
        fractions=(chosen-start)@axis/squared;chosen=chosen[(fractions>.12)&(fractions<.88)]
        if len(chosen)<12:return base
        fractions=(chosen-start)@axis/squared;distances=np.linalg.norm(chosen-start-fractions[:,None]*axis,axis=1)
        # Lower quantile avoids treating a loose skirt or cape as solid body.
        return float(np.clip(np.percentile(distances,35),base*.70,base*1.35))
    def update(self,world):
        self.starts=np.array([world[c.first,:3,3] for c in self.capsules])
        self.ends=np.array([world[c.second,:3,3] for c in self.capsules])
        # Account for global scale changes while preserving the fitted bind geometry.
        self.radii=np.array([c.radius*np.linalg.norm(world[c.first,:3,0])/max(np.linalg.norm(self.data.rest[c.first,:3,0]),1e-10) for c in self.capsules])
        self.axes=self.ends-self.starts;self.axis_squared=np.maximum(np.einsum('ij,ij->i',self.axes,self.axes),1e-20)
    def begin_frame(self,world):
        self.corrections=0;self.unresolved=0;self.arm_corrections=0;self.swept_contacts=0;self.update(world)
    def _rotate_subtree(self,world,node,turn):
        ids=[node]+self.children[node];pivot=world[node,:3,3].copy()
        world[ids,:3,3]=(world[ids,:3,3]-pivot)@turn.T+pivot
        world[ids,:3,:3]=np.einsum('ij,njk->nik',turn,world[ids,:3,:3])
    def _grasp_elbow(self,world,upper,lower,hand,starts,ends,radii):
        """Avoid the torso by changing the elbow plane before moving a grip."""
        from motion import ik
        from vrm import aim
        from hand_pose import turn
        from joint_limits import limit_rotation,limit_forearm
        d=self.data;shoulder,elbow,wrist=[world[n,:3,3].copy() for n in (upper,lower,hand)]
        axis=wrist-shoulder;axis/=max(float(np.linalg.norm(axis)),1e-9)
        a,b=np.linalg.norm(elbow-shoulder),np.linalg.norm(wrist-elbow)
        rest_axis=np.linalg.solve(d.rest[lower,:3,:3],d.rest[hand,:3,3]-d.rest[lower,:3,3])
        for angle in (0.,-.5,.5,-1.,1.,-1.5,1.5,-2.,2.,math.pi):
            middle,end=ik(shoulder,wrist,a,b,turn(axis,angle)@(elbow-shoulder),135.)
            trial=world.copy()
            self._rotate_subtree(trial,upper,aim(elbow-shoulder,middle-shoulder))
            self._rotate_subtree(trial,lower,aim(trial[hand,:3,3]-trial[lower,:3,3],end-trial[lower,:3,3]))
            valid=True
            for node in (upper,lower):
                parent=trial[d.parents[node],:3,:3];local=np.linalg.solve(parent,trial[node,:3,:3])
                bounded=limit_rotation(d.local[node][:3,:3],local,155.) if node==upper else limit_forearm(d.local[node][:3,:3],local,rest_axis)
                if np.linalg.norm(bounded-local)>1e-4:valid=False;break
            if not valid or np.linalg.norm(trial[hand,:3,3]-wrist)>1e-5:continue
            depths=[]
            for fraction in (.45,.75,1.):
                point=middle*(1-fraction)+wrist*fraction
                distances,_,_=capsule_distances(point,starts,ends)
                depths.append(max(0.,float(np.max(radii+self.height*.015-distances))))
            depth=max(depths)
            if depth<=self.margin:
                world[:]=trial;return True
        return False

    def solve_arms(self,world,gripping=False,preserve_grip=False):
        from motion import ik
        from vrm import aim
        from joint_limits import limit_rotation
        self.begin_frame(world)
        if not self.enabled:return
        starts=self.starts[self.arm_body];ends=self.ends[self.arm_body];body_radii=self.radii[self.arm_body]
        for side,(upper,lower,hand) in self.arm_chains.items():
            wrist_rotation=world[hand,:3,:3].copy()
            corrected=False
            fixed=preserve_grip and self._grasp_elbow(world,upper,lower,hand,starts,ends,body_radii)
            for _ in range(0 if fixed else 6):
                shoulder=world[upper,:3,3].copy();elbow=world[lower,:3,3].copy();wrist=world[hand,:3,3].copy()
                best_depth=0.;correction=np.zeros(3)
                for fraction in (.45,.75,1.):
                    point=elbow*(1-fraction)+wrist*fraction
                    projected,depth=push_out(point,starts,ends,body_radii+self.height*.015,self.data.flip.T@np.array([1 if side=='left' else -1,0,1]))
                    if depth>best_depth:best_depth=depth;correction=(projected-point)/max(fraction,.5)
                if best_depth<self.margin:break
                correction*=min(1.,self.height*.06/max(float(np.linalg.norm(correction)),1e-10))
                a=float(np.linalg.norm(elbow-shoulder));b=float(np.linalg.norm(wrist-elbow))
                pole=elbow-shoulder
                new_elbow,new_wrist=ik(shoulder,wrist+correction,a,b,pole,135)
                self._rotate_subtree(world,upper,aim(elbow-shoulder,new_elbow-shoulder))
                self._rotate_subtree(world,lower,aim(world[hand,:3,3]-world[lower,:3,3],new_wrist-world[lower,:3,3]))
                self.arm_corrections+=1
                corrected=True
            # IK bounds geometric flexion, but inherited forearm twist can
            # still exceed the local joint envelope after contact correction.
            if corrected:
                for node,limit in ((upper,155.),(lower,134.)):
                    parent_rotation=world[self.data.parents[node],:3,:3]
                    local=np.linalg.solve(parent_rotation,world[node,:3,:3])
                    if gripping and node==lower:
                        from joint_limits import limit_forearm
                        axis=np.linalg.solve(self.data.rest[lower,:3,:3],self.data.rest[hand,:3,3]-self.data.rest[lower,:3,3])
                        bounded=limit_forearm(self.data.local[node][:3,:3],local,axis)
                    else:bounded=limit_rotation(self.data.local[node][:3,:3],local,limit)
                    target=parent_rotation@bounded
                    self._rotate_subtree(world,node,target@np.linalg.inv(world[node,:3,:3]))
            # Arm avoidance must not arbitrarily spin the hand/finger pose.
            parent=self.data.parents.get(hand)
            parent_rotation=world[parent,:3,:3] if parent is not None else np.eye(3)
            wrist_local=limit_rotation(self.data.local[hand][:3,:3],np.linalg.solve(parent_rotation,wrist_rotation),35.)
            wrist_target=parent_rotation@wrist_local
            self._rotate_subtree(world,hand,wrist_target@np.linalg.inv(world[hand,:3,:3]))
        self.update(world)
    def prepare_tip(self,node,child):
        if node in self.tip_radii:return
        point=self.data.rest[child,:3,3]
        starts=np.array([self.data.rest[c.first,:3,3] for c in self.capsules]);ends=np.array([self.data.rest[c.second,:3,3] for c in self.capsules])
        distances,_,_=capsule_distances(point,starts,ends)
        # Attachment points can intentionally start inside a coarse body capsule.
        # Preserve that bind clearance rather than explode the rig on first load.
        self.tip_radii[node]=np.minimum(np.array([c.radius for c in self.capsules])+self.margin,distances*.98)
        anchor=self.data.rest[node,:3,3];points=anchor+self.fractions[:,None]*(point-anchor)
        self.segment_radii[node]=np.array([np.minimum(np.array([c.radius for c in self.capsules])+self.margin,capsule_distances(p,starts,ends)[0]*.98) for p in points])
    def constrain_tip(self,node,anchor,predicted,length,rest_tip,max_angle,previous=None):
        if not self.enabled:return predicted
        radii=np.minimum(self.radii+self.margin,self.segment_radii[node])
        def contact(tip):
            points=anchor+self.fractions[:,None]*(tip-anchor)
            offset=points[:,None,:]-self.starts
            u=np.clip(np.sum(offset*self.axes,axis=2)/self.axis_squared,0.,1.)
            delta=offset-u[:,:,None]*self.axes;distances=np.linalg.norm(delta,axis=2)
            depths=radii-distances;row,col=np.unravel_index(int(np.argmax(depths)),depths.shape)
            return float(depths[row,col]),delta[row,col],float(distances[row,col]),self.fractions[row],col
        neutral=(rest_tip-anchor)/max(length,1e-12);cosine=math.cos(max_angle);sine=math.sin(max_angle)
        def constrain(point):
            direction=point-anchor;direction/=max(float(np.linalg.norm(direction)),1e-12)
            if float(direction@neutral)<cosine:
                tangent=direction-neutral*float(direction@neutral);size=float(np.linalg.norm(tangent))
                direction=neutral if size<1e-10 else neutral*cosine+tangent/size*sine
            return anchor+direction*length
        swept=None
        if previous is not None and np.linalg.norm(predicted-previous)>self.margin*2:
            swept=sweep_capsules(previous,predicted,self.starts,self.ends,np.minimum(self.radii+self.margin,self.tip_radii[node]))
            if swept is not None:
                _,point,normal=swept;predicted=constrain(point+normal*self.margin);self.swept_contacts+=1
        initial=contact(predicted)
        if initial[0]<=1e-10:return predicted
        best=predicted.copy();best_depth=initial[0]
        for _ in range(4):
            depth,normal,distance,fraction,col=contact(predicted)
            if depth<=1e-8:break
            if distance<1e-10:
                axis=self.axes[col]/max(float(np.linalg.norm(self.axes[col])),1e-10)
                normal=neutral-axis*float(neutral@axis)
                if np.linalg.norm(normal)<1e-10:
                    basis=np.eye(3)[int(np.argmin(np.abs(axis)))];normal=basis-axis*float(basis@axis)
            normal=normal/max(float(np.linalg.norm(normal)),1e-10)
            predicted=constrain(predicted+normal*depth/fraction)
            residual=contact(predicted)[0]
            if residual<best_depth:best=predicted.copy();best_depth=residual
        # Prefer the animated pose if constraints make the simulated tip less safe.
        residual=contact(rest_tip)[0]
        rest_safe=swept is None or sweep_capsules(previous,rest_tip,self.starts,self.ends,np.minimum(self.radii+self.margin,self.tip_radii[node])) is None
        if residual<best_depth and rest_safe:best=rest_tip.copy();best_depth=residual
        self.corrections+=1
        if best_depth>self.margin:self.unresolved+=1
        return best
    def report(self):
        return {'version':1,'capsules':len(self.capsules),'geometry_samples':len(self.samples[0]),'arm_chains':len(self.arm_chains),'spring_contact_nodes':len(self.tip_radii),'automatic':True,'scope':'skeletal capsule contacts; no triangle cloth or soft-body simulation'}
