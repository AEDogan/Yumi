"""Conservative forward arm envelope shared by dance and conversation gestures."""
import numpy as np
from motion import ik

def limit_rotation(rest,posed,max_degrees=35.):
    """Conservative rotation envelope from bind pose; not a full collision solver."""
    if np.array_equal(rest,posed):return posed
    relative=np.linalg.solve(rest,posed)
    u,scale,v=np.linalg.svd(relative)
    turn=u@np.diag([1.,1.,np.linalg.det(u@v)])@v
    angle=np.arccos(np.clip((np.trace(turn)-1.)*.5,-1.,1.))
    limit=np.deg2rad(max_degrees)
    if angle<=limit:return posed
    values,vectors=np.linalg.eig(turn)
    axis=np.real(vectors[:,np.argmin(np.abs(values-1.))])
    axis/=max(np.linalg.norm(axis),1e-12)
    skew=np.array([turn[2,1]-turn[1,2],turn[0,2]-turn[2,0],turn[1,0]-turn[0,1]])
    if np.dot(axis,skew)<0:axis=-axis
    x,y,z=axis;k=np.array([[0.,-z,y],[z,0.,-x],[-y,x,0.]])
    bounded=np.eye(3)+np.sin(limit)*k+(1-np.cos(limit))*(k@k)
    return rest@bounded@(turn.T@relative)

limit_wrist=limit_rotation

def limit_forearm(rest,posed,axis,swing_degrees=135.,twist_degrees=90.):
    """Bound elbow swing and pronation separately for an authored grip."""
    from natural_walk import matrix_quaternion
    from vrm import rotation
    q=matrix_quaternion(np.linalg.solve(rest,posed));q=q/max(np.linalg.norm(q),1e-12)
    if q[3]<0:q=-q
    axis=np.asarray(axis,float);axis=axis/max(np.linalg.norm(axis),1e-12)
    twist=np.r_[axis*float(q[:3]@axis),q[3]];twist/=max(np.linalg.norm(twist),1e-12)
    def multiply(a,b):return np.r_[a[3]*b[:3]+b[3]*a[:3]+np.cross(a[:3],b[:3]),a[3]*b[3]-a[:3]@b[:3]]
    swing=multiply(q,np.r_[-twist[:3],twist[3]])
    def bound(value,degrees):
        if value[3]<0:value=-value
        angle=2*np.arctan2(np.linalg.norm(value[:3]),value[3]);maximum=np.deg2rad(degrees)
        if angle<=maximum:return value
        direction=value[:3]/max(np.linalg.norm(value[:3]),1e-12)
        return np.r_[direction*np.sin(maximum/2),np.cos(maximum/2)]
    return rest@rotation(multiply(bound(swing,swing_degrees),bound(twist,twist_degrees)))

def rotation_limits(bones):
    limits={}
    for name,node in bones.items():
        if name.endswith('Hand'):limit=35.
        elif name.endswith('LowerArm'):limit=135.
        elif name.endswith('UpperArm'):limit=155.
        elif name.endswith('Shoulder'):limit=50.
        elif name.endswith('UpperLeg'):limit=120.
        elif name.endswith('LowerLeg'):limit=145.
        elif name.endswith('Foot'):limit=55.
        elif 'Proximal' in name:limit=70. if 'Thumb' in name else 85.
        elif 'Intermediate' in name or 'Distal' in name:limit=95.
        elif name in ('neck','head'):limit=50.
        elif name in ('spine','chest','upperChest'):limit=45.
        else:continue
        limits[node]=limit
    return limits

def safe_arm(shoulder,hand,upper,lower,sign,pole=None):
    shoulder=np.asarray(shoulder,float);hand=np.asarray(hand,float).copy()
    reach=upper+lower
    hand[2]=max(hand[2],shoulder[2]+min(.04,reach*.08))
    hand[0]=sign*max(sign*hand[0],sign*shoulder[0]-.08*reach)
    elbow,hand=ik(shoulder,hand,upper,lower,[sign*.6,-.45,.85] if pole is None else pole,135)
    if pole is None and elbow[2]<shoulder[2]-.025:
        elbow,hand=ik(shoulder,hand,upper,lower,[0,0,1],135)
    return elbow,hand
