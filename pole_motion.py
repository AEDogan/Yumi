"""Authored climb/hang/spin phrase with measured two-hand pole support.

Canonical coordinates are fitted to each humanoid. This is keyed animation,
not a general rigid-body simulation or a captured professional performance.
"""
import math
from pathlib import Path
import numpy as np
from dance_motion import DanceMotion
from hand_pose import turn,unit,frame
from motion import ik
from vrm import aim
from joint_limits import limit_rotation,limit_forearm

UP=np.array([0.,1.,0.])
def ease(a,b,t):
    u=float(np.clip((t-a)/(b-a),0.,1.));return u*u*(3-2*u)

class PoleMotion(DanceMotion):
    path=Path('Yumi-Pole-Climb-Hang-Spin')
    duration=1152.;uses_stage_bounds=True
    def __init__(self,seed=0,entry_clock=0.,**_):
        super().__init__(seed,pole=True,entry_clock=entry_clock)
        self.support_targets={}
        self.baked={};self._baking=False
    def pole_spec(self,d):
        point,height,radius=super().pole_spec(d)
        return point,height+.65,.025
    def phrase_clock(self,t):return max(0.,t-self.entry_clock)*1.5
    def phrase(self,t):
        elapsed=self.phrase_clock(t)
        # A complete controlled descent precedes the next climb.
        phase=elapsed%40.
        lift=.48*ease(5,10,phase)+.22*ease(12,16,phase)
        lift*=1-ease(29,35,phase)
        tuck= ease(4,8,phase)*(1-ease(29,35,phase))
        extension=ease(21,24,phase)*(1-ease(26,29,phase))
        angle=math.tau*(elapsed//40)+math.tau*ease(16,29,phase)
        grip= ease(1,3,phase)*(1-ease(36,39,phase))
        if self.release_at is not None and t>=self.release_at:
            frozen=self.phrase_before_release(self.release_at)
            u=ease(self.release_at,self.release_at+2.4,t)
            lift=frozen[0]*(1-u);tuck=frozen[1]*(1-u);extension=frozen[2]*(1-u)
            remaining=(frozen[3]+math.pi)%math.tau-math.pi
            angle=frozen[3]-remaining*u;grip=frozen[4]*(1-ease(self.release_at+2.4,self.release_at+3.2,t))
        return lift,tuck,extension,angle,grip
    def phrase_before_release(self,t):
        release=self.release_at;self.release_at=None
        try:return self.phrase(t)
        finally:self.release_at=release
    def frame_bounds(self,d):
        points,floor=super().frame_bounds(d)
        points[:,1]*=1.15
        return points,floor
    def targets(self,t,d,offsets=None):
        r=self._rest(d);pole,height,radius=self.pole_spec(d)
        lift,tuck,extension,angle,grip=self.phrase(t)
        # Scale climb with arm reach, not source asset units.
        reach=np.mean([np.linalg.norm(r[s+'LowerArm']-r[s+'UpperArm'])+np.linalg.norm(r[s+'Hand']-r[s+'LowerArm']) for s in ('left','right')])
        lift*=reach;orbit=turn(UP,angle)
        toward=pole-r['hips'];facing=math.atan2(toward[0],toward[2])
        body=orbit@turn(UP,facing*grip)
        hip=pole+orbit@((r['hips']-pole)*np.array([1-.12*tuck,1.,1-.12*tuck]));hip[1]+=lift
        hands={};feet={}
        for side in ('left','right'):
            shoulder=hip+body@(r[side+'UpperArm']-r['hips'])
            normal=unit(np.array([pole[0]-shoulder[0],0.,pole[2]-shoulder[2]]))
            # One fixed hand supports each climb while the other releases,
            # moves upwards and closes again. Neither slides under load.
            phase=self.phrase_clock(t)%40.
            clock=phase
            if self.release_at is not None and t>=self.release_at:
                clock=self.phrase_clock(self.release_at)%40.
            if side=='right':
                level=(.25+.55*ease(8,11,clock))*(1-ease(31.5,34,clock))+.25*ease(31.5,34,clock)
                moving=ease(7.5,8,clock)*(1-ease(11,11.5,clock))+ease(31,31.5,clock)*(1-ease(34,34.5,clock))
            else:
                level=(.52+.70*ease(12,15,clock))*(1-ease(29,30.5,clock))+.52*ease(29,30.5,clock)
                moving=ease(11.5,12,clock)*(1-ease(15,15.5,clock))+ease(28.5,29,clock)*(1-ease(30.5,31,clock))
            y=r[side+'UpperArm'][1]+reach*level
            if self.release_at is not None and t>=self.release_at:
                frozen_lift=self.phrase_before_release(self.release_at)[0]*reach
                y-=frozen_lift-lift
            goal=pole.copy();goal[1]=min(height-.12,y)
            palm=reach*.07
            if side+'MiddleProximal' in r:palm=np.linalg.norm(r[side+'MiddleProximal']-r[side+'Hand'])*.55
            sign=1 if r[side+'UpperArm'][0]>r['hips'][0] else -1
            forward=unit(np.cross(UP,normal)*sign+UP*.45)
            goal-=normal*(radius+.006+.055*moving)+forward*palm
            relaxed=shoulder+body@np.array([(.08 if r[side+'UpperArm'][0]>r['hips'][0] else -.08),-reach*.87,.10])
            hands[side]=(relaxed*(1-grip)+goal*grip,normal,grip*(1-.95*moving))
            if offsets and side in offsets:
                value,n,w=hands[side];hands[side]=(value+offsets[side],n,w)
            foot=r[side+'Foot'].copy()
            bent=foot.copy();bent[1]+=reach*.44
            bent[2]-=reach*.44
            if side=='left':
                sign=1 if foot[0]>r['hips'][0] else -1
                bent+=np.array([sign*reach*.65,-reach*.30,reach*.14])*extension
            foot=foot*(1-tuck)+bent*tuck
            feet[side]=hip+body@(foot-r['hips'])
        return hip,body,hands,feet
    def pose(self,t,d,loop=True,_offsets=None,_iteration=0):
        if _iteration==0 and not self._baking and self.release_at is None:
            from pole_bake import sample
            baked=sample(self,t,d)
            if baked is not None:return baked
        r=self._rest(d);j=d.bones;hip,orbit,hands,feet=self.targets(t,d,_offsets)
        delta=d.flip.T@((hip-r['hips'])/d.scale);rotations={};cache={}
        def world(node):
            if node not in cache:
                parent=world(d.parents[node]) if node in d.parents else np.eye(4);local=d.local[node].copy()
                if node in rotations:local[:3,:3]=rotations[node]
                if node==j['hips']:local[:3,3]+=np.linalg.solve(parent[:3,:3],delta)
                cache[node]=parent@local
            return cache[node]
        def orient(node,canonical):
            parent=world(d.parents[node])[:3,:3] if node in d.parents else np.eye(3)
            rotations[node]=np.linalg.solve(parent,d.flip.T@canonical@d.flip@d.rest[node,:3,:3]);cache.clear()
        def pos(node):return (world(node)[:3,3]@d.flip.T-d.origin)*d.scale
        for name in ('hips','spine','chest','upperChest','neck','head'):
            if name in j:orient(j[name],orbit)
        self.support_targets[id(d)]={}
        for side in ('left','right'):
            for suffix,goal,pole,maxflex in [('Leg',feet[side],orbit@np.array([0.,0.,1.]),140),('Arm',hands[side][0],orbit@np.array([1. if r[side+'UpperArm'][0]>r['hips'][0] else -1.,-.5,.25]),130)]:
                labels=('UpperLeg','LowerLeg','Foot') if suffix=='Leg' else ('UpperArm','LowerArm','Hand')
                a,b,c=[j[side+n] for n in labels];start=pos(a)
                middle,end=ik(start,goal,np.linalg.norm(r[side+labels[1]]-r[side+labels[0]]),np.linalg.norm(r[side+labels[2]]-r[side+labels[1]]),pole,maxflex)
                orient(a,aim(r[side+labels[1]]-r[side+labels[0]],middle-start))
                orient(b,aim(r[side+labels[2]]-r[side+labels[1]],end-middle))
                orient(c,orbit)
                if suffix=='Arm':
                    normal,weight=hands[side][1:];sign=1 if r[side+'UpperArm'][0]>r['hips'][0] else -1
                    if all(side+n in r for n in ('MiddleProximal','IndexProximal','LittleProximal')):
                        forward=unit(r[side+'MiddleProximal']-r[side+'Hand'])
                        rest_normal=unit(np.cross(forward,r[side+'IndexProximal']-r[side+'LittleProximal']))*sign
                        # Palm axis follows pole; wrist envelope still applies
                        # in the renderer and cannot be bypassed by this clip.
                        desired_forward=unit(np.cross(UP,normal)*sign+UP*.45)
                        desired=d.flip.T@(frame(desired_forward,normal)@frame(forward,rest_normal).T)@d.flip@d.rest[c,:3,:3]
                        # Share axial rotation with the forearm. Clamping a
                        # large wrist turn alone leaves the palm facing away.
                        base=world(b)[:3,:3].copy();parent=world(d.parents[b])[:3,:3]
                        axis=unit(world(c)[:3,3]-world(b)[:3,3]);best=None
                        for angle in np.linspace(-math.pi*.55,math.pi*.55,13):
                            candidate=turn(axis,angle)@base
                            local=np.linalg.solve(parent,candidate)
                            rest_axis=np.linalg.solve(d.rest[b][:3,:3],d.rest[c][:3,3]-d.rest[b][:3,3])
                            bounded=parent@limit_forearm(d.local[b][:3,:3],local,rest_axis)
                            if np.linalg.norm(bounded-candidate)>.0001:continue
                            hand= candidate@limit_rotation(d.local[c][:3,:3],np.linalg.solve(candidate,desired),34.)
                            cost=np.linalg.norm(hand-desired)+.015*abs(angle)
                            if best is None or cost<best[0]:best=(cost,candidate,hand)
                        if best is not None:
                            rotations[b]=np.linalg.solve(parent,best[1]);cache.clear()
                            rotations[c]=np.linalg.solve(best[1],best[2]);cache.clear()
                        for finger in ('Index','Middle','Ring','Little','Thumb'):
                            labels=('Metacarpal','Proximal','Distal') if finger=='Thumb' and not d.legacy else ('Proximal','Intermediate','Distal')
                            chain=[j.get(side+finger+n) for n in labels]
                            if any(n is None for n in chain):continue
                            for k,node in enumerate(chain):
                                direction=d.rest[chain[min(k+1,2)],:3,3]-d.rest[chain[max(0,k-1)],:3,3]
                                axis=np.linalg.solve(d.rest[node,:3,:3],np.cross(unit(direction),d.flip.T@rest_normal))
                                angles=(65,82,48) if finger!='Thumb' else (32,58,35)
                                rotations[node]=d.local[node][:3,:3]@turn(axis,math.radians(angles[k])*weight)
                        cache.clear()
                        pole,_,radius=self.pole_spec(d)
                        if weight>.98 and _iteration>=2:
                            for finger in ('Index','Middle','Ring','Little'):
                                chain=[j.get(side+finger+n) for n in ('Proximal','Intermediate','Distal')]
                                if any(n is None for n in chain):continue
                                angles=np.radians([65.,82.,48.]);axes=[]
                                for k,node in enumerate(chain):
                                    direction=d.rest[chain[min(k+1,2)],:3,3]-d.rest[chain[max(0,k-1)],:3,3]
                                    axes.append(unit(np.linalg.solve(d.rest[node][:3,:3],np.cross(unit(direction),d.flip.T@rest_normal))))
                                last=chain[-1];tip_offset=np.linalg.solve(d.rest[last][:3,:3],(d.rest[last,:3,3]-d.rest[chain[-2],:3,3])*.7)
                                def contact_cost():
                                    points=[pos(n) for n in chain]
                                    tip=(world(last)[:3,3]+world(last)[:3,:3]@tip_offset)@d.flip.T
                                    points.append((tip-d.origin)*d.scale)
                                    points=np.asarray(points)
                                    samples=np.concatenate((points,(points[:-1]+points[1:])*.5))
                                    gap=np.linalg.norm((samples-pole)[:,[0,2]],axis=1)-radius
                                    return float((gap[3]-.004)**2+.5*(gap[2]-.006)**2+10*np.sum(np.minimum(gap+.006,0.)**2))
                                for step in (20.,8.,3.):
                                    for k,node in enumerate(chain):
                                        saved=angles[k];best=(contact_cost(),saved)
                                        for change in (-step,step):
                                            value=float(np.clip(saved+math.radians(change),math.radians((40,50,20)[k]),math.radians(84 if k==0 else 94)))
                                            rotations[node]=d.local[node][:3,:3]@turn(axes[k],value);cache.clear()
                                            cost=contact_cost()
                                            if cost<best[0]:best=(cost,value)
                                        angles[k]=best[1];rotations[node]=d.local[node][:3,:3]@turn(axes[k],best[1]);cache.clear()
                        labels=('Metacarpal','Proximal','Distal') if not d.legacy else ('Proximal','Intermediate','Distal')
                        thumb=[j.get(side+'Thumb'+n) for n in labels]
                        if weight>.5 and _iteration>=2 and all(n is not None for n in thumb):
                            pole,_,radius=self.pole_spec(d)
                            target=pole+normal*radius*.35-np.cross(UP,normal)*sign*radius*.8
                            target[1]=pos(j[side+'IndexProximal'])[1]-.025
                            target=d.flip.T@(target/d.scale+d.origin)
                            last=thumb[-1];tip_offset=np.linalg.solve(d.rest[last,:3,:3],(d.rest[last,:3,3]-d.rest[thumb[-2],:3,3])*.7)
                            def thumb_tip():return world(last)[:3,3]+world(last)[:3,:3]@tip_offset
                            for _ in range(12):
                                if np.linalg.norm(thumb_tip()-target)*d.scale<.003:break
                                for node in reversed(thumb):
                                    pivot=world(node)[:3,3];desired=aim(thumb_tip()-pivot,target-pivot)@world(node)[:3,:3]
                                    parent=world(d.parents[node])[:3,:3]
                                    local=limit_rotation(d.local[node][:3,:3],np.linalg.solve(parent,desired),69. if node==thumb[0] else 94.)
                                    rotations[node]=local;cache.clear()
                    if weight>.98:self.support_targets[id(d)][side]=goal.copy()
        if _iteration<3:
            cache.clear();offsets=dict(_offsets or {});correction=0.
            pole,_,_=self.pole_spec(d)
            for side in ('left','right'):
                if hands[side][2]<.5:continue
                names=[side+finger+joint for finger in ('Index','Little') for joint in ('Proximal','Distal')]
                if not all(n in j for n in names):continue
                # Fit the cavity between palm and curled fingers, rather
                # than attaching the wrist joint to the cylinder surface.
                center=np.mean([pos(j[n]) for n in names],axis=0)
                error=pole-center;error[1]=0.
                length=float(np.linalg.norm(error));correction=max(correction,length)
                offsets[side]=offsets.get(side,np.zeros(3))+error*min(1.,.12/max(length,1e-9))
            if correction>.002 or _iteration<2:return self.pose(t,d,loop,offsets,_iteration+1)
        return rotations,delta,{'happy':.12,'relaxed':.08}
    def supported(self,t,d,world):
        """Only actual post-limit hand contact permits authored aerial support."""
        if self.phrase(t)[0]<=.001:return False
        goals=self.support_targets.get(id(d),{})
        for side,goal in goals.items():
            hand=(world[d.bones[side+'Hand'],:3,3]@d.flip.T-d.origin)*d.scale
            if np.linalg.norm(hand-goal)<.025 and self.grasp_quality(d,world,side)['grasped']:return True
        return False
    def grasp_quality(self,d,world,side):
        pole,_,radius=self.pole_spec(d)
        point=lambda name:(world[d.bones[side+name],:3,3]@d.flip.T-d.origin)*d.scale
        names=[finger+joint for finger in ('Index','Little') for joint in ('Proximal','Distal')]
        if not all(side+n in d.bones for n in names):return {'grasped':False}
        center=np.mean([point(n) for n in names],axis=0)
        center_error=float(np.linalg.norm((center-pole)[[0,2]]))
        gaps=[abs(float(np.linalg.norm((point(f+'Distal')-pole)[[0,2]])-radius)) for f in ('Index','Middle','Ring','Little')]
        labels=('Metacarpal','Proximal','Distal') if not d.legacy else ('Proximal','Intermediate','Distal')
        thumb=[d.bones.get(side+'Thumb'+n) for n in labels]
        thumb_gap=float('inf')
        if all(n is not None for n in thumb):
            last=thumb[-1];offset=np.linalg.solve(d.rest[last,:3,:3],(d.rest[last,:3,3]-d.rest[thumb[-2],:3,3])*.7)
            tip=((world[last,:3,3]+world[last,:3,:3]@offset)@d.flip.T-d.origin)*d.scale
            thumb_gap=abs(float(np.linalg.norm((tip-pole)[[0,2]])-radius))
        return {'grasped':bool(center_error<.015 and sum(gap<.025 for gap in gaps)>=2 and thumb_gap<.02),'cavity_error':center_error,'finger_gaps':gaps,'thumb_gap':thumb_gap}
