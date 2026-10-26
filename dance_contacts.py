"""Conservative leg twist and facing limits after retargeting, before grounding."""
import math
import numpy as np
from joint_limits import limit_forearm
from hand_pose import turn

def legs(data,world,physics):
    j=data.bones
    for side in ('left','right'):
        for suffix,child,swing,twist in (('UpperLeg','LowerLeg',120.,45.),('LowerLeg','Foot',145.,12.)):
            node=j[side+suffix];end=j[side+child];parent=world[data.parents[node],:3,:3]
            axis=np.linalg.solve(data.rest[node,:3,:3],data.rest[end,:3,3]-data.rest[node,:3,3])
            local=np.linalg.solve(parent,world[node,:3,:3]);bounded=limit_forearm(data.local[node][:3,:3],local,axis,swing,twist)
            physics._rotate_subtree(world,node,parent@bounded@np.linalg.inv(world[node,:3,:3]))
        # A knee is a hinge, not a ball joint. Bound its signed flexion in
        # the authored femur frame; magnitude-only swing limits allow backwards
        # knees and sideways bending even when the angle is below 145 degrees.
        knee=j[side+'LowerLeg'];foot=j[side+'Foot']
        parent=world[data.parents[knee],:3,:3]
        rest=data.local[knee][:3,:3]
        local=np.linalg.solve(parent,world[knee,:3,:3])
        relative=np.linalg.solve(rest,local)
        direction=np.linalg.solve(data.rest[knee,:3,:3],data.rest[foot,:3,3]-data.rest[knee,:3,3]);direction/=np.linalg.norm(direction)
        hinge=np.linalg.solve(data.rest[knee,:3,:3],data.flip.T@np.array([1.,0.,0.]));hinge/=np.linalg.norm(hinge)
        bent=relative@direction;bent/=max(np.linalg.norm(bent),1e-12)
        flex=math.atan2(float(hinge@np.cross(direction,bent)),float(direction@bent))
        bounded=rest@turn(hinge,float(np.clip(flex,0.,math.radians(145))))
        physics._rotate_subtree(world,knee,parent@bounded@np.linalg.inv(world[knee,:3,:3]))
        from joint_limits import limit_rotation
        parent=world[data.parents[foot],:3,:3]
        bounded=limit_rotation(data.local[foot][:3,:3],np.linalg.solve(parent,world[foot,:3,:3]),55.)
        physics._rotate_subtree(world,foot,parent@bounded@np.linalg.inv(world[foot,:3,:3]))
        toes=j.get(side+'Toes')
        if toes is None:continue
        hip=j['hips'];body=data.flip@world[hip,:3,:3]@np.linalg.inv(data.rest[hip,:3,:3])@data.flip.T@np.array([0.,0.,1.])
        neutral=data.rest[toes,:3,3]-data.rest[foot,:3,3]
        forward=data.flip@world[foot,:3,:3]@np.linalg.solve(data.rest[foot,:3,:3],neutral)
        if np.linalg.norm(forward[[0,2]])<np.linalg.norm(neutral)*.2:continue
        yaw=math.atan2(forward[0],forward[2])-math.atan2(body[0],body[2]);yaw=(yaw+math.pi)%math.tau-math.pi
        bounded=float(np.clip(yaw,-math.pi/3,math.pi/3));delta=bounded-yaw
        if abs(delta)>1e-6:physics._rotate_subtree(world,foot,data.flip.T@turn(np.array([0.,1.,0.]),delta)@data.flip)

def head_proxy(data):
    if hasattr(data,'_dance_head_proxy'):return data._dance_head_proxy
    head=data.bones['head'];points=[]
    for part in data.parts:
        if part['kind']!='face' or part['skin'] is None or 'joints' not in part:continue
        nodes,inverse=data.skins[part['skin']];ids=part['joints'];mass=np.sum(part['weights']*(nodes[ids]==head),axis=1)
        used=np.unique(part['indices']);used=used[mass[used]>.7]
        if not len(used):continue
        source=np.c_[part['pos'][used],np.ones(len(used))];posed=np.zeros_like(source);palette=data.rest[nodes]@inverse
        for k in range(4):posed+=np.einsum('nij,nj->ni',palette[ids[used,k]],source)*part['weights'][used,k,None]
        points.append(posed[:,:3])
    if points:
        cloud=np.concatenate(points);lo,hi=np.percentile(cloud,[2,98],axis=0);center=(lo+hi)*.5;radius=float(np.max((hi-lo)*.5))
    else:center=data.rest[head,:3,3].copy();radius=np.linalg.norm(data.rest[head,:3,3]-data.rest[data.bones['hips'],:3,3])*.16
    local=np.linalg.solve(data.rest[head],np.r_[center,1.]);data._dance_head_proxy=(local,radius)
    return local,radius

def avoid_head(data,world,physics):
    """Check entire arm segments, including the elbow, against the fitted skull."""
    from motion import ik
    from vrm import aim
    from joint_limits import limit_rotation
    local,radius=head_proxy(data);center=(world[data.bones['head']]@local)[:3];radius+=physics.height*.018
    for side,(upper,lower,hand) in physics.arm_chains.items():
        wrist_rotation=world[hand,:3,:3].copy()
        for _ in range(8):
            shoulder,elbow,wrist=[world[n,:3,3].copy() for n in (upper,lower,hand)];best=None
            for a,b,upper_segment in ((shoulder,elbow,True),(elbow,wrist,False)):
                axis=b-a;fraction=float(np.clip((center-a)@axis/max(axis@axis,1e-12),0.,1.));point=a+axis*fraction
                radial=point-center;distance=float(np.linalg.norm(radial));depth=radius-distance
                if depth>physics.margin and (best is None or depth>best[0]):best=(depth,radial/max(distance,1e-9),fraction,upper_segment)
            if best is None:break
            depth,normal,fraction,is_upper=best
            if np.linalg.norm(normal)<.5:normal=data.flip.T@np.array([1. if side=='left' else -1.,0.,1.]);normal/=np.linalg.norm(normal)
            correction=normal*min(physics.height*.08,(depth+physics.margin)/max(fraction,.3))
            pole=elbow-shoulder+(correction if is_upper else np.zeros(3))
            middle,end=ik(shoulder,wrist+correction*(.35 if is_upper else 1.),np.linalg.norm(elbow-shoulder),np.linalg.norm(wrist-elbow),pole,134.)
            physics._rotate_subtree(world,upper,aim(elbow-shoulder,middle-shoulder))
            physics._rotate_subtree(world,lower,aim(world[hand,:3,3]-world[lower,:3,3],end-world[lower,:3,3]))
        parent=world[data.parents[hand],:3,:3];desired=parent@limit_rotation(data.local[hand][:3,:3],np.linalg.solve(parent,wrist_rotation),35.)
        physics._rotate_subtree(world,hand,desired@np.linalg.inv(world[hand,:3,:3]))
