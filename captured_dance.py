"""Retarget the credited CMU salsa sequence onto measured humanoid limbs."""
import math
from pathlib import Path
import numpy as np
from hand_pose import turn,unit
from vrm import aim
from motion import ik
ROOT=Path(__file__).resolve().parent

def basis(lateral,up):
    x=unit(lateral);z=unit(np.cross(x,up));y=unit(np.cross(z,x));return np.column_stack((x,y,z))

class CapturedDance:
    uses_stage_bounds=True
    duration=180.;path=Path('Yumi-CMU-Salsa-Long');max_root_offset=4.;pole=False
    def __init__(self):
        data=np.load(ROOT/'motions/cmu-salsa-long.npz');self.names={str(n):i for i,n in enumerate(data['names'])}
        p=data['points'].astype(float);self.fps=float(data['fps']);self.start=2.;self.duration=(len(p)-1)/self.fps-self.start
        point=lambda name:p[0,self.names[name]]
        forward=basis(point('lhipjoint')-point('rhipjoint'),point('thorax')-point('root'))[:,2]
        yaw=math.atan2(forward[0],forward[2]);self.turn=turn(np.array([0.,1.,0.]),-yaw)
        p=p@self.turn.T;p[:,:,[0,2]]-=p[0,self.names['root'],[0,2]]
        self.floor=min(float(np.percentile(p[:180,self.names[n],1],3)) for n in ('ltibia','rtibia'))
        self.source_leg=float(np.median([np.linalg.norm(p[:,self.names[s+'femur']]-p[:,self.names[s+'hipjoint']],axis=1)+np.linalg.norm(p[:,self.names[s+'tibia']]-p[:,self.names[s+'femur']],axis=1) for s in ('l','r')]))
        root=p[:,self.names['root'],[0,2]].copy()
        p[:,:,[0,2]]+=(2*np.tanh(root/2)-root)[:,None,:]
        self.points=p;self.rest={}
    def presence(self,t):return 1.
    def frame_bounds(self,d):
        from scene_framing import corners
        canonical=lambda n:(d.rest[d.bones[n],:3,3]@d.flip.T-d.origin)*d.scale
        leg=np.linalg.norm(canonical('leftFoot')-canonical('leftLowerLeg'))+np.linalg.norm(canonical('leftLowerLeg')-canonical('leftUpperLeg'))
        p=self.points;source=np.linalg.norm(p[0,self.names['lfemur']]-p[0,self.names['lhipjoint']])+np.linalg.norm(p[0,self.names['ltibia']]-p[0,self.names['lfemur']])
        points=p[int(self.start*self.fps):int((self.start+self.duration)*self.fps)]*(leg/source)
        lo=points.min(axis=(0,1))-[.35,0,.35];hi=points.max(axis=(0,1))+[.35,.35,.35];lo[1]=0.
        return corners(lo,hi),corners([lo[0],0.,lo[2]],[hi[0],0.,hi[2]])
    def pose(self,t,d,loop=True):
        clock=min(self.duration-1e-5,max(0.,t%self.duration if loop else t))+self.start
        frame=clock*self.fps;i=int(frame);u=frame-i
        p=self.points[i]*(1-u)+self.points[min(i+1,len(self.points)-1)]*u
        src=lambda n:p[self.names[n]]
        r=self.rest.get(id(d))
        if r is None:
            r={n:(d.rest[k,:3,3]@d.flip.T-d.origin)*d.scale for n,k in d.bones.items()};self.rest[id(d)]=r
        leg=np.mean([np.linalg.norm(r[s+'LowerLeg']-r[s+'UpperLeg'])+np.linalg.norm(r[s+'Foot']-r[s+'LowerLeg']) for s in ('left','right')])
        scale=leg/self.source_leg
        hip=src('root')*scale;hip[1]+=(r['leftFoot'][1]+r['rightFoot'][1])*.5-self.floor*scale
        # Keep the desktop solo within a compact standing salsa vocabulary.
        # The source contains deep, very wide partner figures; transferring
        # those literally folds short imported skirts through the thighs.
        hip[1]=max(hip[1],r['hips'][1]-.06)
        rest_basis=basis(r['leftUpperLeg']-r['rightUpperLeg'],r['head']-r['hips'])
        pelvis=basis(src('lhipjoint')-src('rhipjoint'),src('thorax')-src('root'))@rest_basis.T
        chest=basis(src('lclavicle')-src('rclavicle'),src('upperneck')-src('upperback'))@rest_basis.T
        rotations={};cache={};j=d.bones
        shift=d.flip.T@((hip-r['hips'])/d.scale)
        def world(node):
            if node not in cache:
                parent=world(d.parents[node]) if node in d.parents else np.eye(4);local=d.local[node].copy()
                if node in rotations:local[:3,:3]=rotations[node]
                if node==j['hips']:local[:3,3]+=np.linalg.solve(parent[:3,:3],shift)
                cache[node]=parent@local
            return cache[node]
        def orient(node,value):
            parent=world(d.parents[node])[:3,:3] if node in d.parents else np.eye(3)
            rotations[node]=np.linalg.solve(parent,value);cache.clear()
        def pos(node):return (world(node)[:3,3]@d.flip.T-d.origin)*d.scale
        def fit(name,matrix):
            if name in j:orient(j[name],d.flip.T@matrix@d.flip@d.rest[j[name],:3,:3])
        fit('hips',pelvis);fit('spine',pelvis);fit('chest',chest);fit('upperChest',chest);fit('neck',chest);fit('head',chest)
        goals={}
        for side,s in (('left','l'),('right','r')):
            goal=src(s+'tibia')*scale;goal[1]+=r[side+'Foot'][1]-self.floor*scale
            offset=goal[[0,2]]-hip[[0,2]];reach=float(np.linalg.norm(offset));span=leg*.35
            if reach>1e-8:goal[[0,2]]=hip[[0,2]]+offset*(span*math.tanh(reach/span)/reach)
            goals[side]=goal
        # Different anatomical hip offsets must not force an overextended knee.
        lowering=0.
        for side,goal in goals.items():
            a,b,c=[j[side+n] for n in ('UpperLeg','LowerLeg','Foot')]
            current=pos(a);reach=np.linalg.norm(r[side+'LowerLeg']-r[side+'UpperLeg'])+np.linalg.norm(r[side+'Foot']-r[side+'LowerLeg'])
            horizontal=np.sum((goal[[0,2]]-current[[0,2]])**2)
            lowering=min(lowering,float(goal[1]+math.sqrt(max(0.,(reach*.995)**2-horizontal))-current[1]))
        shift+=d.flip.T@np.array([0.,lowering/d.scale,0.]);cache.clear()
        for side,s in (('left','l'),('right','r')):
            a,b,c=[j[side+n] for n in ('UpperLeg','LowerLeg','Foot')];root=pos(a)
            source_knee=src(s+'femur')-src(s+'hipjoint')
            knee,end=ik(root,goals[side],np.linalg.norm(r[side+'LowerLeg']-r[side+'UpperLeg']),np.linalg.norm(r[side+'Foot']-r[side+'LowerLeg']),source_knee,140)
            for node,first,last,direction in ((a,side+'UpperLeg',side+'LowerLeg',knee-root),(b,side+'LowerLeg',side+'Foot',end-knee)):
                orient(node,d.flip.T@aim(r[last]-r[first],direction)@d.flip@d.rest[node,:3,:3])
            forward=src(s+'foot')-src(s+'tibia');yaw=math.atan2(forward[0],forward[2]);pitch=-math.atan2(forward[1],np.linalg.norm(forward[[0,2]]))
            orient(c,d.flip.T@turn(np.array([0.,1.,0.]),yaw)@turn(np.array([1.,0.,0.]),float(np.clip(pitch,-.18,.18)))@d.flip@d.rest[c,:3,:3])
        for side,s in (('left','l'),('right','r')):
            a,b,c=[j[side+n] for n in ('UpperArm','LowerArm','Hand')];shoulder=pos(a)
            upper=np.linalg.norm(r[side+'LowerArm']-r[side+'UpperArm']);lower=np.linalg.norm(r[side+'Hand']-r[side+'LowerArm'])
            first=unit(src(s+'humerus')-src(s+'clavicle'));second=unit(src(s+'radius')-src(s+'humerus'))
            goal=shoulder+first*upper+second*lower
            elbow,end=ik(shoulder,goal,upper,lower,first,135)
            for node,start_name,end_name,direction in ((a,side+'UpperArm',side+'LowerArm',elbow-shoulder),(b,side+'LowerArm',side+'Hand',end-elbow)):
                orient(node,d.flip.T@aim(r[end_name]-r[start_name],direction)@d.flip@d.rest[node,:3,:3])
            orient(c,world(b)[:3,:3]@np.linalg.solve(d.rest[b,:3,:3],d.rest[c,:3,:3]))
        return rotations,shift,{'happy':.12}

