"""Slow humanoid gait using each model's own limb lengths and sagittal IK."""
import math
import numpy as np
from motion import ik

PERIOD=1.45
STANCE=.62

def dimensions(rest):
    leg=float(np.mean([np.linalg.norm(rest[s+'LowerLeg']-rest[s+'UpperLeg'])+np.linalg.norm(rest[s+'Foot']-rest[s+'LowerLeg']) for s in ('left','right')]))
    return leg,.15*leg

def travel_speed(rest):
    return 2*dimensions(rest)[1]/(STANCE*PERIOD)

def foot_roll(u):
    def ease(x):x=max(0.,min(1.,x));return x*x*(3-2*x)
    if u<STANCE:
        if u<.12:return math.radians(-6)*(1-ease(u/.12))
        return math.radians(10)*ease((u-(STANCE-.15))/.15)
    return math.radians(10)-math.radians(16)*ease((u-STANCE)/(1-STANCE))

def sample(rest,t,period=PERIOD,clearance=0.):
    phase=(t/period)%1.
    leg,stride=dimensions(rest)
    root=np.array([.006*leg*math.sin(phase*2*math.pi),0.,0.])
    ankles={};heights=[]
    for side,offset in [('left',0.),('right',.5)]:
        u=(phase+offset)%1.;ankle=rest[side+'Foot'].copy()
        if u<STANCE:ankle[2]+=stride*(1-2*u/STANCE)
        else:
            swing=(u-STANCE)/(1-STANCE)
            # Match stance velocity at both ends instead of abruptly reversing.
            slope=-2*stride*(1-STANCE)/STANCE
            ankle[2]+=(-stride)*(2*swing**3-3*swing**2+1)+slope*(swing**3-2*swing**2+swing)+stride*(-2*swing**3+3*swing**2)+slope*(swing**3-swing**2)
            ankle[1]+=.065*leg*math.sin(math.pi*swing)**2
        # Roll on the shoe contact instead of rotating through the floor.
        pitch=foot_roll(u);front=.12*leg;rear=.04*leg
        toes=rest.get(side+'Toes')
        if toes is not None:front=max(.08*leg,abs(float(toes[2]-rest[side+'Foot'][2])))
        sole=max(0.,float(rest[side+'Foot'][1]))
        ankle[1]+=sole*(math.cos(pitch)-1)+max(front*math.sin(pitch),-rear*math.sin(pitch))
        ankles[side]=ankle
        a=np.linalg.norm(rest[side+'LowerLeg']-rest[side+'UpperLeg']);b=np.linalg.norm(rest[side+'Foot']-rest[side+'LowerLeg'])
        reach=math.sqrt(a*a+b*b+2*a*b*math.cos(math.radians(10)))
        hip=rest[side+'UpperLeg']+root
        lateral=(hip[0]-ankle[0])**2+(hip[2]-ankle[2])**2
        heights.append(ankle[1]+math.sqrt(max(0.,reach*reach-lateral))-rest[side+'UpperLeg'][1])
    # Derive pelvis height from reach, not a permanent crouch. A smooth minimum
    # keeps both legs reachable through double support and heel contact.
    lowest=min(heights);soft=.0015*leg
    root[1]=lowest-soft*math.log(sum(math.exp(-(h-lowest)/soft) for h in heights))
    joints={k:v.copy()+root for k,v in rest.items()}
    for side,offset in [('left',0.),('right',.5)]:
        sign=1. if rest[side+'UpperLeg'][0]>0 else -1.
        u=(phase+offset)%1.;stance=STANCE
        hip=rest[side+'UpperLeg']+root
        ankle=ankles[side]
        knee,ankle=ik(hip,ankle,np.linalg.norm(rest[side+'LowerLeg']-rest[side+'UpperLeg']),np.linalg.norm(rest[side+'Foot']-rest[side+'LowerLeg']),[0,0,1])
        joints[side+'UpperLeg']=hip;joints[side+'LowerLeg']=knee;joints[side+'Foot']=ankle
        shoulder=rest[side+'UpperArm']+root
        upper=np.linalg.norm(rest[side+'LowerArm']-rest[side+'UpperArm']);lower=np.linalg.norm(rest[side+'Hand']-rest[side+'LowerArm'])
        # Keep hands outside the hip/torso envelope, with relaxed elbow flexion.
        lateral=max(abs(rest[side+'UpperLeg'][0])+.15*leg,abs(shoulder[0])+.07*leg,clearance)
        wrist=np.array([sign*lateral,shoulder[1]-(upper+lower)*.95,shoulder[2]+.035*leg-.075*leg*math.cos(2*math.pi*u)])
        # Forearm folds toward the front, with the elbow behind the arm-hand
        # line. A forward elbow pole previously produced reversed flexion.
        elbow,wrist=ik(shoulder,wrist,upper,lower,[sign*.12,0,-1])
        joints[side+'UpperArm']=shoulder;joints[side+'LowerArm']=elbow;joints[side+'Hand']=wrist
    return joints,root
