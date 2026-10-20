"""Humanoid joints, two-bone IK, and damped transitions for the dummy rig."""
import math,time
import numpy as np

def ik(start,end,a,b,pole,max_flex_degrees=150):
    start=np.asarray(start,float);end=np.asarray(end,float)
    delta=end-start;dist=float(np.linalg.norm(delta))
    direction=delta/dist if dist>1e-6 else np.array([0.,0.,1.])
    # A nearly coincident target otherwise folds the elbow or knee through
    # itself. Bound the interior flexion before solving the two-bone triangle.
    flex=math.radians(max(0,min(175,max_flex_degrees)))
    min_reach=math.sqrt(max(0,a*a+b*b+2*a*b*math.cos(flex)))
    dist=max(min_reach,min(a+b-1e-4,dist));end=start+direction*dist
    bend=np.asarray(pole,float);bend-=direction*np.dot(bend,direction)
    if np.linalg.norm(bend)<1e-6:bend=np.cross(direction,[0,0,1])
    bend/=max(float(np.linalg.norm(bend)),1e-6)
    along=(a*a-b*b+dist*dist)/(2*dist)
    middle=start+direction*along+bend*math.sqrt(max(0,a*a-along*along))
    return middle,end

class MotionRig:
    def __init__(self):
        self.positions={};self.velocity={};self.last=time.perf_counter()
    def sample(self,t,pose,desk):
        now=time.perf_counter();dt=min(.06,max(.001,now-self.last));self.last=now
        targets={};walk=pose=='walk'
        breath=math.sin(t*1.8)*.012
        shift=math.sin(t*5)*.025 if walk else math.sin(t*.65)*.012
        targets['hips']=np.array([shift,.90+breath,0.])
        targets['spine']=np.array([shift*.7,1.63+breath,.025])
        targets['head']=np.array([shift*.35,2.45+breath,.02])
        for side,label in [(-1,'left'),(1,'right')]:
            phase=t*(5 if walk else 3.8)+ (math.pi if side<0 else 0)
            swing=math.sin(phase)
            hip=np.array([side*.19+shift,.90+breath,0.])
            if walk:ankle=np.array([side*.19,.15+max(0,swing)*.10,swing*.27])
            else:ankle=np.array([side*.19,.15,.045])
            knee,ankle=ik(hip,ankle,.39,.38,[0,0,1],145)
            targets[label+'UpperLeg']=hip;targets[label+'LowerLeg']=knee;targets[label+'Foot']=ankle
            shoulder=np.array([side*.49+shift*.7,2.02+breath,.0])
            wrist=np.array([side*.57+shift*.6,1.28+breath,.12])
            if pose=='wave' and side>0:wrist=np.array([.75+math.sin(t*7)*.10,2.76,.16])
            elif pose=='listen' and side>0:wrist=np.array([.34,2.40,.18])
            if walk:wrist=np.array([side*.57,1.31,-swing*.23])
            elbow,wrist=ik(shoulder,wrist,.40,.42,[side*.65,0,.4])
            targets[label+'UpperArm']=shoulder;targets[label+'LowerArm']=elbow;targets[label+'Hand']=wrist
        for key,target in targets.items():
            if key not in self.positions:self.positions[key]=target.copy();self.velocity[key]=np.zeros(3)
            current=self.positions[key];velocity=self.velocity[key];omega=14.;decay=math.exp(-omega*dt)
            delta=current-target;temp=(velocity+omega*delta)*dt
            self.positions[key]=target+(delta+temp)*decay;self.velocity[key]=(velocity-omega*temp)*decay
        # Resolve after damping so interpolation never stretches a limb.
        for side, label in [(-1, 'left'), (1, 'right')]:
            shoulder = self.positions[label+'UpperArm']; wrist = self.positions[label+'Hand']
            elbow, wrist = ik(shoulder, wrist, .40, .42, self.positions[label+'LowerArm']-shoulder)
            # Torso collision avoidance: keep elbow and wrist outside ribcage
            if abs(elbow[0]) < 0.22 and 1.15 < elbow[1] < 2.05:
                elbow[0] = math.copysign(0.22, side)
            if abs(wrist[0]) < 0.14 and 1.10 < wrist[1] < 1.95 and abs(wrist[2]) < 0.18:
                wrist[0] = math.copysign(0.14, side)
            self.positions[label+'LowerArm'] = elbow; self.positions[label+'Hand'] = wrist
            hip = self.positions[label+'UpperLeg']; ankle = self.positions[label+'Foot']
            knee, ankle = ik(hip, ankle, .39, .38, self.positions[label+'LowerLeg']-hip, 145)
            # Knee and foot self-collision: prevent legs from crossing through each other
            if side < 0:
                if knee[0] > -0.05: knee[0] = -0.05
                if ankle[0] > -0.04: ankle[0] = -0.04
            else:
                if knee[0] < 0.05: knee[0] = 0.05
                if ankle[0] < 0.04: ankle[0] = 0.04
            self.positions[label+'LowerLeg'] = knee; self.positions[label+'Foot'] = ankle
        return self.positions
