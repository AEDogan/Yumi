"""Anatomical palm frames and cached finger poses, shared by humanoid avatars."""
import math
import numpy as np
from joint_limits import limit_rotation

def unit(value):return value/max(float(np.linalg.norm(value)),1e-10)
def turn(axis,angle):
    axis=unit(axis);x,y,z=axis;k=np.array([[0,-z,y],[z,0,-x],[-y,x,0]])
    return np.eye(3)+math.sin(angle)*k+(1-math.cos(angle))*(k@k)
def frame(forward,palm):
    forward=unit(forward);palm=unit(palm-forward*float(palm@forward))
    return np.column_stack((forward,np.cross(palm,forward),palm))

class HandPoses:
    def __init__(self,data,physics):
        self.data=data;self.physics=physics;self.hands={};self.cache={};self.ok_gap={}
        for side in ('left','right'):
            names=[side+n for n in ('Hand','MiddleProximal','IndexProximal','LittleProximal')]
            if not all(n in data.bones for n in names):continue
            hand,middle,index,little=[data.bones[n] for n in names]
            point=lambda n:data.rest[n,:3,3]@data.flip.T
            sign=1 if point(hand)[0]>=point(data.bones['hips'])[0] else -1
            forward=unit(point(middle)-point(hand));palm=unit(np.cross(forward,point(index)-point(little)))*sign
            self.hands[side]=(hand,frame(forward,palm),sign)
    def chain(self,side,finger):
        labels=('Metacarpal','Proximal','Distal') if finger=='Thumb' and not self.data.legacy else ('Proximal','Intermediate','Distal')
        return [self.data.bones.get(side+finger+label) for label in labels]
    def rotate_to(self,world,node,target):
        self.physics._rotate_subtree(world,node,target@np.linalg.inv(world[node,:3,:3]))
    def finger_pose(self,side,style):
        key=(side,style)
        if key in self.cache:return self.cache[key]
        d=self.data;world=d.rest.copy();hand,basis,sign=self.hands[side];palm=d.flip.T@basis[:,2];nodes=[]
        for finger in ('Index','Middle','Ring','Little','Thumb'):
            chain=self.chain(side,finger)
            if any(n is None for n in chain):continue
            nodes.extend(chain)
            angles=(12,18,10) if style=='relaxed' else (0,3,2) if style=='open_palm' else (8,12,8) if style=='hip' else (62,78,48)
            if style in ('book_grip','remote_grip','notebook_grip'):
                angles={'book_grip':(18,30,16),'remote_grip':(32,48,25),'notebook_grip':(10,20,12)}[style] if finger!='Thumb' else (12,20,10)
            if style=='cup_grip':angles=(48,68,32) if finger!='Thumb' else (18,32,20)
            if style=='point' and finger=='Index':angles=(0,2,0)
            if style=='thumbs_up' and finger=='Thumb':angles=(0,3,3)
            if style=='ok' and finger not in ('Index','Thumb'):angles=(5,8,4)
            if style=='ok' and finger=='Index':angles=(35,75,35)
            if style=='ok' and finger=='Thumb':angles=(10,35,15)
            for i,node in enumerate(chain):
                direction=d.rest[chain[min(i+1,2)],:3,3]-d.rest[chain[max(0,i-1)],:3,3]
                axis=np.linalg.solve(d.rest[node,:3,:3],np.cross(unit(direction),palm))
                local=d.local[node][:3,:3]@turn(axis,math.radians(angles[i]))
                parent=d.parents.get(node);parent_rotation=world[parent,:3,:3] if parent is not None else np.eye(3)
                self.rotate_to(world,node,parent_rotation@local)
        if style=='thumbs_up':
            chain=self.chain(side,'Thumb')
            if all(n is not None for n in chain):
                from vrm import aim
                node=chain[0];direction=world[chain[1],:3,3]-world[node,:3,3]
                # Thumb points across the palm; the wrist frame turns this up.
                desired=d.flip.T@(basis[:,1]*sign)
                target=aim(direction,desired)@world[node,:3,:3]
                parent=d.parents[node]
                self.rotate_to(world,node,world[parent,:3,:3]@limit_rotation(d.local[node][:3,:3],np.linalg.solve(world[parent,:3,:3],target),70))
        if style=='ok':
            index=self.chain(side,'Index');thumb=self.chain(side,'Thumb')
            if any(n is None for n in index+thumb):self.ok_gap[side]=float('inf')
            else:
                from vrm import aim
                tips={}
                for chain in (index,thumb):
                    last=chain[-1];delta=(d.rest[last,:3,3]-d.rest[chain[-2],:3,3])*.7
                    tips[last]=np.linalg.solve(d.rest[last,:3,:3],delta)
                point=lambda chain:world[chain[-1],:3,3]+world[chain[-1],:3,:3]@tips[chain[-1]]
                for _ in range(32):
                    target=(point(index)+point(thumb))*.5
                    if np.linalg.norm(point(index)-point(thumb))<self.physics.height*.0015:break
                    for chain in (index,thumb):
                        for node in reversed(chain):
                            pivot=world[node,:3,3];rotation=aim(point(chain)-pivot,target-pivot)@world[node,:3,:3]
                            parent=world[d.parents[node],:3,:3]
                            local=limit_rotation(d.local[node][:3,:3],np.linalg.solve(parent,rotation),70 if node==chain[0] else 95)
                            self.rotate_to(world,node,parent@local)
                self.ok_gap[side]=float(np.linalg.norm(point(index)-point(thumb)))
        result={node:np.linalg.solve(world[d.parents[node],:3,:3],world[node,:3,:3]) for node in nodes}
        self.cache[key]=result;return result
    def supported_sides(self,style):
        result=[]
        required=('Index','Thumb') if style=='ok' else ('Thumb',) if style=='thumbs_up' else ('Index',) if style=='point' else ()
        for side in self.hands:
            if any(n is None for finger in required for n in self.chain(side,finger)):continue
            if style=='ok':
                self.finger_pose(side,style)
                if self.ok_gap.get(side,float('inf'))>=self.physics.height*.006:continue
            result.append(side)
        return result
    def supports(self,style):
        if style not in ('open_palm','thumbs_up','point','ok','hip','shrug'):return False
        return bool(self.supported_sides(style))
    def fingers(self,world,side,style,weight=1.):
        if side not in self.hands:return
        from vrma import slerp
        from natural_walk import matrix_quaternion
        from vrm import rotation
        d=self.data
        for node,local in self.finger_pose(side,style).items():
            parent=world[d.parents[node],:3,:3]
            if weight<1.:
                current=np.linalg.solve(parent,world[node,:3,:3])
                local=rotation(slerp(matrix_quaternion(current),matrix_quaternion(local),weight))
            self.rotate_to(world,node,parent@local)
    def relax(self,world):
        for side in self.hands:self.fingers(world,side,'relaxed')
    def apply(self,world,style,selected='left',weight=1.):
        if style=='shrug':style='open_palm'
        if not style or style not in ('open_palm','thumbs_up','point','ok','hip','cup_grip'):return
        sides=self.supported_sides(style)
        if not sides:return
        if selected not in sides:selected=sides[0]
        d=self.data
        for side,(hand,basis,sign) in self.hands.items():
            if side!=selected and style!='open_palm':
                self.fingers(world,side,'relaxed',weight);continue
            lower=d.bones[side+'LowerArm'];axis=unit(world[hand,:3,3]-world[lower,:3,3])
            if style=='hip':forward=np.array([0.,-1.,0.]);normal=np.array([-sign,0.,0.])
            elif style=='open_palm':forward=np.array([sign*.15,.12,1.]);normal=np.array([0.,1.,.15])
            elif style=='point':forward=np.array([sign*.2,.15,1.]);normal=np.array([0.,-1.,0.])
            elif style=='ok':forward=np.array([sign*.12,1.,.15]);normal=np.array([0.,0.,1.])
            elif style=='cup_grip':
                forward=d.flip@axis;forward[1]=0.
                if np.linalg.norm(forward)<1e-6:forward=np.array([0.,0.,1.])
                forward=unit(forward);normal=-sign*unit(np.cross(np.array([0.,1.,0.]),forward))
            else:forward=np.array([sign*.7,0.,.7]);normal=np.array([0.,0.,1.])
            desired=frame(forward,normal)@basis.T
            palm=world[hand,:3,:3]@np.linalg.solve(d.rest[hand,:3,:3],d.flip.T@basis[:,2]);goal=d.flip.T@desired@basis[:,2]
            a=unit(palm-axis*float(palm@axis));b=unit(goal-axis*float(goal@axis))
            twist=math.atan2(float(axis@np.cross(a,b)),float(np.clip(a@b,-1,1)))
            amount=float(np.clip(twist,-1.2,1.2))*weight
            parent_lower=world[d.parents[lower],:3,:3]
            for _ in range(8):
                candidate=np.linalg.solve(d.local[lower][:3,:3],np.linalg.solve(parent_lower,turn(axis,amount)@world[lower,:3,:3]))
                angle=math.acos(float(np.clip((np.trace(candidate)-1)*.5,-1,1)))
                if angle<=math.radians(134)+1e-6:break
                amount*=.5
            self.physics._rotate_subtree(world,lower,turn(axis,amount))
            target=d.flip.T@desired@d.flip@d.rest[hand,:3,:3]
            parent=world[d.parents[hand],:3,:3];current=np.linalg.solve(parent,world[hand,:3,:3]);wanted=np.linalg.solve(parent,target)
            from vrma import slerp
            from natural_walk import matrix_quaternion
            from vrm import rotation
            local=rotation(slerp(matrix_quaternion(current),matrix_quaternion(wanted),weight))
            self.rotate_to(world,hand,parent@limit_rotation(d.local[hand][:3,:3],local,35))
            self.fingers(world,side,style,weight)
