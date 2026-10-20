"""Character-sized furniture fitting and continuous pelvis/foot/hand seat contacts."""
from dataclasses import dataclass
import math
import numpy as np
from motion import ik
from hand_pose import turn
from joint_limits import limit_rotation

@dataclass
class SeatFit:
    item:dict
    scale:float
    height:float
    padding:float
    upper:float
    lower:float
    width:float
    depth:float
    pivot:np.ndarray
    yaw:float
    hip_offset:float=0.
    stand_distance:float=0.

def thigh_clearance(model):
    """Clothed thigh envelope, distinct from the narrow body collision proxy."""
    d=model.data
    if hasattr(d,'_seat_padding'):return d._seat_padding
    physics=model.hair_springs.physics;points,dominant=physics.samples;clearances=[]
    for side in ('left','right'):
        first=d.bones[side+'UpperLeg'];second=d.bones[side+'LowerLeg']
        start=d.rest[first,:3,3];axis=d.rest[second,:3,3]-start;squared=float(axis@axis)
        if squared<1e-12:continue
        selected=points[dominant==first];fraction=(selected-start)@axis/squared
        selected=selected[(fraction>-.10)&(fraction<.90)]
        if len(selected)<12:continue
        fraction=(selected-start)@axis/squared
        distance=np.linalg.norm(selected-start-fraction[:,None]*axis,axis=1)*d.scale
        clearances.append(float(np.percentile(distance,95)))
    proxy=max((c.radius*d.scale for c in physics.capsules if c.name.endswith('Thigh')),default=.06)
    d._seat_padding=max([proxy,*clearances])+.015
    return d._seat_padding

def fit_chair(row,model):
    d=model.data;r=model.rest_canonical;p=row['seat'];upper=np.mean([np.linalg.norm(r[s+'LowerLeg']-r[s+'UpperLeg']) for s in ('left','right')]);lower=np.mean([np.linalg.norm(r[s+'Foot']-r[s+'LowerLeg']) for s in ('left','right')])
    body=model.hair_springs.physics
    thigh=next((c.radius*d.scale for c in body.capsules if c.name=='leftThigh'),upper*.10)
    padding=thigh_clearance(model)
    if padding>upper*.5:raise ValueError('Bacak/kıyafet hacmi bu oturma düzenine güvenle sığmıyor.')
    world=d.rest.copy();soles=model.ground.sample(world);floor=float(soles[:,1].min())
    ankle=float(np.mean([r[s+'Foot'][1] for s in ('left','right')])-floor)
    height=float(lower+ankle-padding);seat_height=max(.05,p['seat_height']-row['bounds']['min'][1]);scale=height/seat_height
    # Keep a leg-sized seat height. Deep seats that cannot fit at this height
    # are rejected below rather than lowering the pelvis into raised knees.
    height=scale*seat_height
    width=p['width']*scale;depth=p['depth']*scale;hips=abs(r['leftUpperLeg'][0]-r['rightUpperLeg'][0])
    if width<hips+thigh*2.3:raise ValueError('Koltuk karakterin kalça/bacak genişliğine uygun değil.')
    if depth<upper*.60 or depth>upper*1.85:raise ValueError('Koltuk derinliği karakterin uyluk ölçüsüne uygun değil.')
    forward=np.array(p['forward']);patch=np.array(p.get('outline',p['patch']));front=float(np.max(patch@forward));center=np.array(p['center'])
    # Leave space behind the knee; the pelvis is placed by thigh support,
    # rather than by the center of the chair's overall bounding box.
    support=max(upper*.60,upper-padding-.040)
    butt=front-support/scale;low=float(np.min(patch@forward));butt=max(low+.05*(front-low),min(front-.1*(front-low),butt))
    pivot=center+forward*(butt-float(center@forward));pivot[1]=row['bounds']['min'][1]
    yaw=math.degrees(math.atan2(float(forward[0]),float(forward[2])))
    hip_offset=float(r['hips'][1]-np.mean([r[s+'UpperLeg'][1] for s in ('left','right')]))
    stand_distance=max(float(upper),float(front-pivot@forward)*scale+padding+.025)
    if row['role']=='chair':
        bounds=row['bounds']
        footprint=np.array([[x,0.,z] for x in (bounds['min'][0],bounds['max'][0]) for z in (bounds['min'][2],bounds['max'][2])])
        stand_distance=max(stand_distance,float(np.max((footprint-pivot)@forward))*scale+thigh+.035)
    return SeatFit(row,float(scale),height,padding,float(upper),float(lower),float(width),float(depth),pivot,yaw,hip_offset,stand_distance)

class SeatedRig:
    def __init__(self,fit):self.fit=fit;self.weight=0.;self.phase='idle';self.mode='lounge'
    def apply(self,world,model):
        weight=float(np.clip(self.weight,0.,1.))
        if weight<=0:return
        d=model.data;physics=model.hair_springs.physics;f=self.fit
        from vrm import aim
        def canonical(node):return (world[node,:3,3]@d.flip.T-d.origin)*d.scale
        hips=d.bones['hips'];hip=canonical(hips);old_feet={side:canonical(d.bones[side+'Foot']) for side in ('left','right')}
        # The humanoid hips node is a rig root, not the thigh joint. Different
        # avatars place it above or below the femur attachment. Fit the actual
        # thigh centerline to the cushion, preserving the authored root offset.
        amount=(f.height+f.padding+f.hip_offset-hip[1])*weight
        forward_clearance=0.
        if hasattr(self,'clearance_curve'):
            weights,lifts,residual,forwards=self.clearance_curve
            amount+=float(np.interp(weight,weights,lifts))
            forward_clearance=float(np.interp(weight,weights,forwards))
        world[:,:3,3]+=d.flip.T@np.array([0.,amount/d.scale,forward_clearance/d.scale])
        for side in ('left','right'):
            a,b,c=[d.bones[side+p] for p in ('UpperLeg','LowerLeg','Foot')]
            hip,knee,foot=[world[n,:3,3].copy() for n in (a,b,c)];foot_rotation=world[c,:3,:3].copy()
            upper=float(np.linalg.norm(knee-hip));lower=float(np.linalg.norm(foot-knee))
            target=old_feet[side].copy();target[2]+=(f.stand_distance or f.upper)*weight
            raw=d.flip.T@(target/d.scale+d.origin)
            new_knee,new_foot=ik(hip,raw,upper,lower,d.flip.T@np.array([0.,0.,1.]),145)
            physics._rotate_subtree(world,a,aim(knee-hip,new_knee-hip))
            physics._rotate_subtree(world,b,aim(world[c,:3,3]-world[b,:3,3],new_foot-world[b,:3,3]))
            physics._rotate_subtree(world,c,foot_rotation@np.linalg.inv(world[c,:3,:3]))
        # A small forward lean transfers weight while lowering/rising; the
        # settled lounge pose has a modest supported recline.
        spine=d.bones.get('spine');lean=.14*math.sin(math.pi*weight)-(.08 if self.mode=='lounge' else 0.)*weight
        if spine is not None:physics._rotate_subtree(world,spine,d.flip.T@turn(np.array([1.,0.,0.]),lean)@d.flip)
        speaking=getattr(model,'speaking_for_seat',False)
        style=getattr(model,'active_hand_style',model.hand_gesture)
        gesturing=bool(style or speaking)
        targets=model.conversation.arm_targets(model.rest_canonical,style) if gesturing else {}
        if weight>0:
            for side,sign in (('left',1),('right',-1)):
                a,b,c=[d.bones[side+p] for p in ('UpperArm','LowerArm','Hand')]
                shoulder,elbow,hand=[world[n,:3,3].copy() for n in (a,b,c)];hand_rotation=world[c,:3,:3].copy()
                sign=1 if canonical(a)[0]>=canonical(hips)[0] else -1
                goal=np.array([canonical(hips)[0]+sign*f.width*.16,f.height+f.padding*2+.06,f.upper*.50])
                if self.mode=='work' and hasattr(self,'keyboard_target'):
                    goal=self.keyboard_target.copy();goal[0]+=sign*self.hand_spacing
                selected=(model.conversation.variant%2==0)==(side=='left')
                active=gesturing and (selected or style in ('open_palm','shrug'))
                pole=np.array([sign*.25,-1.,.35])
                if active and side+'Hand' in targets:
                    # Rebase the standing gesture on the actually seated
                    # shoulder, after pelvis shift and supported torso lean.
                    goal=canonical(a)+targets[side+'Hand']-model.rest_canonical[side+'UpperArm']
                    reach=float(np.linalg.norm(elbow-shoulder)+np.linalg.norm(hand-elbow))*d.scale
                    goal[1]=max(goal[1],f.height+f.padding+reach*.20)
                    goal[2]=max(goal[2],f.upper*.44)
                    if style=='hip':
                        goal[0]=canonical(hips)[0]+sign*min(f.width*.32,reach*.48)
                        pole=np.array([sign*.8,-.35,.1])
                    if self.mode=='work' and hasattr(self,'keyboard_target'):
                        # Lift an expressive hand clear of the keyboard/table;
                        # the resting hand remains at its fitted typing point.
                        goal[1]=max(goal[1],self.keyboard_target[1]+reach*.16)
                target=canonical(c)*(1-weight)+goal*weight;target=d.flip.T@(target/d.scale+d.origin)
                upper=float(np.linalg.norm(elbow-shoulder));lower=float(np.linalg.norm(hand-elbow))
                new_elbow,new_hand=ik(shoulder,target,upper,lower,d.flip.T@pole,135)
                target_rotation=aim(d.rest[b,:3,3]-d.rest[a,:3,3],new_elbow-shoulder)@d.rest[a,:3,:3]
                physics._rotate_subtree(world,a,target_rotation@np.linalg.inv(world[a,:3,:3]))
                parent=world[d.parents[a],:3,:3]
                bounded=parent@limit_rotation(d.local[a][:3,:3],np.linalg.solve(parent,world[a,:3,:3]),155.)
                physics._rotate_subtree(world,a,bounded@np.linalg.inv(world[a,:3,:3]))
                neutral=world[d.parents[b],:3,:3]@d.local[b][:3,:3]
                source=neutral@np.linalg.solve(d.rest[b,:3,:3],d.rest[c,:3,3]-d.rest[b,:3,3])
                target_rotation=aim(source,new_hand-world[b,:3,3])@neutral
                physics._rotate_subtree(world,b,target_rotation@np.linalg.inv(world[b,:3,:3]))
                parent=world[d.parents[b],:3,:3]
                bounded=parent@limit_rotation(d.local[b][:3,:3],np.linalg.solve(parent,world[b,:3,:3]),134.)
                physics._rotate_subtree(world,b,bounded@np.linalg.inv(world[b,:3,:3]))
                hand_rotation=world[b,:3,:3]@np.linalg.solve(d.rest[b,:3,:3],d.rest[c,:3,:3])
                physics._rotate_subtree(world,c,hand_rotation@np.linalg.inv(world[c,:3,:3]))
                parent=world[d.parents[c],:3,:3]
                bounded=parent@limit_rotation(d.local[c][:3,:3],np.linalg.solve(parent,world[c,:3,:3]),35.)
                physics._rotate_subtree(world,c,bounded@np.linalg.inv(world[c,:3,:3]))
            if style:
                model.hand_poses.apply(world,style,'left' if model.conversation.variant%2==0 else 'right',weight)
