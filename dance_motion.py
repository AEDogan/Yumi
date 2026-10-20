"""Beat-driven choreography, fitted to real limbs with planted support feet."""
import math
from dataclasses import replace
from pathlib import Path
import numpy as np
from motion import ik
from hand_pose import turn
from vrm import aim,rotation
from vrma import slerp
from natural_walk import matrix_quaternion
from dance_repertoire import Repertoire,canonical

def family(genre):
    if genre in {'hip-hop','r&b','soul','funk','reggae','dancehall','afrobeats'}:return 'groove'
    if genre in {'house','techno','trance','drum & bass','dubstep','disco'}:return 'club'
    if genre in {'rock','metal','punk','indie'}:return 'rock'
    if genre in {'salsa','bachata','latin pop','reggaeton'}:return 'latin'
    return 'pop'

class DanceMotion:
    duration=1152.
    max_root_offset=.16
    path=Path('Yumi-Rhythm-Dance')
    def __init__(self,seed=0,pole=False,entry_clock=0.):
        self.style='pop';self.previous='pop';self.changed=None;self.rest={}
        self.repertoire=Repertoire(seed);self.pole=pole;self.release_at=None
        self.entry_clock=entry_clock
        self.max_root_offset=3. if pole else .16
    def set_genre(self,genre,clock):
        desired=canonical(genre)
        if desired!=self.style:self.previous=self.style;self.style=desired;self.changed=clock
    def release(self,clock):
        if self.release_at is None:self.release_at=clock
    def presence(self,t):
        u=max(0.,min(1.,(t-self.entry_clock)/1.2))
        if self.release_at is not None:u*=max(0.,min(1.,1-(t-self.release_at-2.6)/1.2))
        return u*u*(3-2*u)
    def orbit(self,t):
        def authored(clock):
            elapsed=max(0.,clock-self.entry_clock-2.);turns=math.floor(elapsed/48);phase=elapsed%48
            def ease(start):
                u=max(0.,min(1.,(phase-start)/8));return u*u*(3-2*u)
            return turns*math.tau+ease(0)*math.pi/2+ease(16)*math.pi/2+ease(32)*math.pi
        angle=authored(t)
        if self.release_at is not None and t>=self.release_at:
            angle=authored(self.release_at);remaining=(angle+math.pi)%math.tau-math.pi
            u=max(0.,min(1.,(t-self.release_at)/2));angle-=remaining*u*u*(3-2*u)
        return angle
    def foot_orbit(self,t,index):
        beat=t*2;cell=math.floor(beat/2);phase=beat-cell*2
        if index==0:
            if phase>=1:return self.orbit((cell*2+1)/2)
            a,b=(cell*2-1)/2,(cell*2+1)/2;u=phase
        else:
            if phase<1:return self.orbit(cell)
            a,b=cell,cell+1;u=phase-1
        u=u*u*(3-2*u)
        return self.orbit(a)*(1-u)+self.orbit(b)*u
    def frame_bounds(self,d):
        from scene_framing import corners
        pole,height,_=self.pole_spec(d)
        r=self._rest(d)
        reach=max(np.linalg.norm(r[s+'LowerArm']-r[s+'UpperArm'])+np.linalg.norm(r[s+'Hand']-r[s+'LowerArm']) for s in ('left','right'))
        width=max(abs(r[s+'UpperArm'][0]) for s in ('left','right'))+reach*.60+.15
        actor=corners([-width,0,-.65],[width,height+.2,.65])
        sole=corners([-.5,0,-.4],[.5,0,.4]);points=[];floor=[]
        for angle in np.linspace(0.,math.tau,25):
            matrix=turn(np.array([0.,1.,0.]),angle)
            points.append(pole+(actor-pole)@matrix.T);floor.append(pole+(sole-pole)@matrix.T)
        points.append(corners(pole+[-.13,0,-.13],pole+[.13,height,.13]))
        floor.append(pole+np.array([[-.13,0,-.13],[.13,0,.13]]))
        return np.concatenate(points),np.concatenate(floor)
    def pole_spec(self,d):
        r=self._rest(d);side='right';shoulder=r[side+'UpperArm']
        reach=np.linalg.norm(r[side+'LowerArm']-shoulder)+np.linalg.norm(r[side+'Hand']-r[side+'LowerArm'])
        sign=1 if shoulder[0]>r['hips'][0] else -1
        return np.array([shoulder[0]+sign*reach*.42,0.,shoulder[2]+reach*.23]),float(r['head'][1]+.3),.035
    def grip_level(self,t):return .25+.12*math.sin(t*math.pi/8)
    def _rest(self,d):
        r=self.rest.get(id(d))
        if r is None:
            r={name:(d.rest[node,:3,3]@d.flip.T-d.origin)*d.scale for name,node in d.bones.items()};self.rest[id(d)]=r
        return r
    @staticmethod
    def _targets(beat,figure,phrase=0.):
        """Return canonical hip/foot goals and shoulder-relative hand goals.

        Every step shares contact instants on integer beats, including blends.
        The support foot stays at its rest location; there is no root travel.
        """
        f=figure;cycle=beat*math.pi;sway=math.sin(cycle)
        progress=max(0.,min(1.,phrase/32))
        bounce=.5-.5*math.cos(beat*math.tau)
        shift=np.array([.045*sway,-(.025+.035*f.energy)*bounce,0.])
        feet=[];hands=[]
        for sign in (1,-1):
            phase=cycle+(0 if sign==f.lead else math.pi)
            swing=max(0.,math.sin(phase));cell=int(beat//2)%4
            # No crossing stance: even grape/box steps keep knee and foot lateral.
            paths={'touch':(.13,0.,.08),'vstep':(.18,.10,.09),
                   'box':(.10,.11*(1 if cell<2 else -1),.07),
                   'heel':(.07,.13,.055),'side':(.18,.025,.065),
                   'mambo':(.055,.16*(1 if cell%2==0 else -1),.075),
                   'twist':(.11,.065*math.sin(beat*math.pi/2),.045),
                   'back':(.07,-.14,.07),'skate':(.16,-.09,.085),
                   'tap':(.08,.07*(1 if cell<2 else -1),.045),
                   'grape':(.17,.06*(1 if cell%2==0 else -1),.065),
                   'bounce':(.055,.025,.05),'stomp':(.085,.055,.11),
                   'march':(.045,.07,.12),'shuffle':(.115,.13*(1 if cell%2==0 else -1),.085),
                   'charleston':(.055,.16*math.cos(beat*math.pi/2),.09)}
            x,z,lift=paths[f.step]
            feet.append(np.array([sign*x*swing,lift*swing*swing,z*swing])*(.85+.15*f.energy))
            w=math.sin(phase);slow=math.sin(beat*math.pi/4+sign*.6)
            # Hands remain outside the torso. Long arcs differ from short accents.
            arms={'swing':(sign*.23,-.58+.10*w,.28+.13*w),
                  'wave':(sign*(.27+.08*slow),-.30+.33*slow,.30+.06*w),
                  'scoop':(sign*(.22+.06*w),-.50+.16*w,.33+.10*slow),
                  'point':(sign*(.30+.08*slow),-.05+.40*slow,.37),
                  'overhead':(sign*(.31+.06*w),.28+.24*slow,.26),
                  'box':(sign*.25,-.38+.10*math.sin(beat*math.tau),.38+.06*w),
                  'reach':(sign*(.25+.15*slow),-.26+.25*w,.38),
                  'roll':(sign*(.25+.06*math.cos(beat*math.pi/2)),-.36+.13*slow,.35+.08*math.sin(beat*math.pi/2)),
                  'fan':(sign*(.36+.10*slow),-.16+.30*slow,.22+.08*w),
                  'lock':(sign*.25,-.38+.13*math.tanh(3*w),.34+.08*math.tanh(3*slow))}
            hand=np.array(arms[f.arms]);hand[1]+=.035*f.variation*math.sin(beat*math.pi/8)
            # A figure develops across its full musical phrase rather than
            # replaying an identical 4/8-second loop inside a longer container.
            hand[0]*=1-.12*progress
            hand[1]+=.10*math.sin(progress*math.pi)
            hand[2]+=.05*math.sin(progress*math.pi/2)
            hands.append(hand)
        nod=.10*f.energy*math.sin(beat*math.tau) if f.step in ('stomp','march') else .025*bounce
        body=np.array([.025*bounce,f.hips*sway,(.018+f.hips*.6)*sway,.06*f.energy*bounce,nod])
        return shift,np.asarray(feet),np.asarray(hands),body
    def _sample(self,t,genre):
        a,b,u=self.repertoire.sample(genre,t*2)
        if self.pole:a,b=replace(a,lead=1),replace(b,lead=1)
        phase=max(0.,t*2)%self.repertoire.beats_per_figure
        aa=self._targets(t*2,a,phase);bb=self._targets(t*2,b,phase-self.repertoire.beats_per_figure)
        return tuple(x*(1-u)+y*u for x,y in zip(aa,bb))
    def pose(self,t,target,loop=True):
        current=self._sample(t,self.style)
        if self.changed is not None and t-self.changed<1.:
            previous=self._sample(t,self.previous);u=max(0.,min(1.,t-self.changed));u=u*u*(3-2*u)
            current=tuple(a*(1-u)+b*u for a,b in zip(previous,current))
        return self._pose(t,target,current)
    def _pose(self,t,d,targets):
        j=d.bones;r=self._rest(d)
        upper=float(np.mean([np.linalg.norm(r[s+'LowerLeg']-r[s+'UpperLeg']) for s in ('left','right')]))
        strength=upper/.75
        shift,feet,hands,body=targets;shift=shift*strength
        orbit=np.eye(3)
        if self.pole:
            shift*=.6
            phase=max(0.,t-self.entry_clock-2.)%48
            figure=int(phase//8);u=(phase%8)/8
            if figure in (1,3,5) and not getattr(self,'authored_pole_targets',False):
                shift[1]-=(.18 if figure==3 else .10)*math.sin(u*math.pi)**2
                shift[2]+=.04*math.sin(u*math.tau)
                hands=hands.copy()
                hands[0]=[.38+.08*math.sin(u*math.pi),-.35+.8*math.sin(u*math.pi),.32]
                feet=feet.copy();envelope=math.sin(u*math.pi)**2
                if figure==1:
                    # Outside-leg fan: the other sole remains planted throughout.
                    feet[:]=0.;feet[0]=[.28*envelope,.26*envelope,.08*envelope]
                    shift[0]-=.035*envelope
                elif figure==3:feet[:]=0.
                else:
                    feet[:]=0.;body=body.copy()
                    body[0]+=.08*math.sin(u*math.tau);body[3]+=.16*math.sin(u*math.tau)
            orbit=turn(np.array([0.,1.,0.]),self.orbit(t));pole,_,_=self.pole_spec(d)
            shift=pole+orbit@(r['hips']+shift-pole)-r['hips']
        rotations={};world_cache={}
        delta=d.flip.T@(shift/d.scale)
        def world(node):
            if node not in world_cache:
                parent=world(d.parents[node]) if node in d.parents else np.eye(4)
                local=d.local[node].copy()
                if node in rotations:local[:3,:3]=rotations[node]
                if node==j['hips']:local[:3,3]+=np.linalg.solve(parent[:3,:3],delta)
                world_cache[node]=parent@local
            return world_cache[node]
        def set_world(node,orientation):
            parent=world(d.parents[node])[:3,:3] if node in d.parents else np.eye(3)
            rotations[node]=np.linalg.solve(parent,orientation);world_cache.clear()
        def angles(name,values):
            if name not in j:return
            change=np.eye(3)
            for axis,angle in zip(np.eye(3),values):change=change@turn(axis,angle)
            set_world(j[name],d.flip.T@orbit@change@d.flip@d.rest[j[name],:3,:3])
        pitch,yaw,roll,chest,nod=body
        angles('hips',(pitch,yaw,roll));angles('spine',(pitch,-yaw*.5,roll*.5))
        angles('chest',(chest,yaw*.5,-roll));angles('head',(nod,-yaw*.5,roll*.3))
        for index,side in enumerate(('left','right')):
            sign=1 if r[side+'UpperLeg'][0]>r['hips'][0] else -1
            foot=r[side+'Foot'].copy()
            offset=feet[index].copy();offset[0]=sign*abs(offset[0]);foot+=offset*strength*(.65 if self.pole else 1.)
            foot_turn=np.eye(3)
            if self.pole:
                foot_turn=turn(np.array([0.,1.,0.]),self.foot_orbit(t,index))
                foot=pole+foot_turn@(foot-pole)
            a,b,c=[j[side+suffix] for suffix in ('UpperLeg','LowerLeg','Foot')]
            hip=(world(a)[:3,3]@d.flip.T-d.origin)*d.scale
            knee,end=ik(hip,foot,np.linalg.norm(r[side+'LowerLeg']-r[side+'UpperLeg']),np.linalg.norm(r[side+'Foot']-r[side+'LowerLeg']),orbit@np.array([0.,0.,1.]),135)
            for node,start_name,end_name,direction in ((a,side+'UpperLeg',side+'LowerLeg',knee-hip),(b,side+'LowerLeg',side+'Foot',end-knee)):
                set_world(node,d.flip.T@aim(orbit@(r[end_name]-r[start_name]),direction)@orbit@d.flip@d.rest[node,:3,:3])
            set_world(c,d.flip.T@foot_turn@d.flip@d.rest[c,:3,:3])
        for index,side in enumerate(('left','right')):
            a,b,c=[j[side+suffix] for suffix in ('UpperArm','LowerArm','Hand')]
            shoulder=(world(a)[:3,3]@d.flip.T-d.origin)*d.scale
            sign=1 if r[side+'UpperArm'][0]>r['hips'][0] else -1
            length_a=np.linalg.norm(r[side+'LowerArm']-r[side+'UpperArm']);length_b=np.linalg.norm(r[side+'Hand']-r[side+'LowerArm']);reach=length_a+length_b
            offsets=hands[index].copy();offsets[0]=sign*abs(offsets[0]);goal=shoulder+orbit@offsets*reach
            grip=None;grip_weight=0.
            if self.pole and side=='right':
                from hand_pose import frame,unit
                pole,height,radius=self.pole_spec(d)
                grip_weight=self.presence(max(0.,t-.6))
                # Release starts at the real clock, independent of the entry delay.
                if self.release_at is not None:grip_weight=min(grip_weight,max(0.,min(1.,1-(t-self.release_at-2.)/.65)))
                grip=pole.copy();grip[1]=shoulder[1]+reach*self.grip_level(t)
                normal=unit(np.array([pole[0]-shoulder[0],0.,pole[2]-shoulder[2]]))
                rest_normal=np.array([sign,0.,0.])
                forward=np.array([0.,1.,0.]);palm_length=reach*.075
                if all(side+n in r for n in ('MiddleProximal','IndexProximal','LittleProximal')):
                    palm_length=np.linalg.norm(r[side+'MiddleProximal']-r[side+'Hand'])*.55
                    rest_forward=unit(r[side+'MiddleProximal']-r[side+'Hand'])
                    rest_normal=unit(np.cross(rest_forward,r[side+'IndexProximal']-r[side+'LittleProximal']))*sign
                    grip_rotation=d.flip.T@frame(forward,normal)@frame(rest_forward,rest_normal).T@d.flip@d.rest[c,:3,:3]
                else:grip_rotation=d.rest[c,:3,:3]
                grip-=normal*(radius+.012)+forward*palm_length
                goal=goal*(1-grip_weight)+grip*grip_weight
            elbow,hand=ik(shoulder,goal,length_a,length_b,orbit@np.array([sign*.45,-1.,-.6]),130)
            for node,start_name,end_name,direction in ((a,side+'UpperArm',side+'LowerArm',elbow-shoulder),(b,side+'LowerArm',side+'Hand',hand-elbow)):
                set_world(node,d.flip.T@aim(orbit@(r[end_name]-r[start_name]),direction)@orbit@d.flip@d.rest[node,:3,:3])
            set_world(c,world(b)[:3,:3]@np.linalg.solve(d.rest[b,:3,:3],d.rest[c,:3,:3]))
            if grip is not None:
                current=world(c)[:3,:3]
                desired=rotation(slerp(matrix_quaternion(current),matrix_quaternion(grip_rotation),grip_weight))
                set_world(c,desired)
                # Close authored finger chains around the pole, preserving rig axes.
                for finger in ('Index','Middle','Ring','Little','Thumb'):
                    labels=('Metacarpal','Proximal','Distal') if finger=='Thumb' and not d.legacy else ('Proximal','Intermediate','Distal')
                    chain=[j.get(side+finger+label) for label in labels]
                    if any(n is None for n in chain):continue
                    for k,node in enumerate(chain):
                        direction=d.rest[chain[min(k+1,2)],:3,3]-d.rest[chain[max(0,k-1)],:3,3]
                        axis=np.linalg.solve(d.rest[node,:3,:3],np.cross(unit(direction),d.flip.T@rest_normal))
                        rotations[node]=d.local[node][:3,:3]@turn(axis,math.radians((35,62,35)[k])*grip_weight)
        return rotations,delta,{'happy':.16+.04*math.sin(t*math.pi/8),'relaxed':.08}
