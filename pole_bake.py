"""Play fitted pole poses without running the offline hand solver each frame."""
from functools import lru_cache
from pathlib import Path
import hashlib
import numpy as np

ROOT=Path(__file__).resolve().parent
HZ=30
DURATION=40/1.5

@lru_cache(maxsize=1)
def signature():
    digest=hashlib.sha256()
    for name in ('pole_motion.py','pole_bake.py','dance_motion.py','hand_pose.py','joint_limits.py','motion.py'):
        digest.update((ROOT/name).read_bytes())
    return digest.hexdigest()

def path(data):return ROOT/'motions'/f'pole-{data.source_sha256[:16]}.npz'

def load(data):
    target=path(data)
    if not target.is_file():return None
    try:
        with np.load(target,allow_pickle=False) as source:
            if str(source['signature'])!=signature() or str(source['rig'])!=data.source_sha256:return None
            if str(source['mapping'])!=str(data.mapping_sha256):return None
            result={key:source[key].copy() for key in ('nodes','q','shift','hands','engaged')}
        if result['q'].shape!=(801,len(result['nodes']),4) or not np.isfinite(result['q']).all():return None
        return result
    except (OSError,ValueError,KeyError):return None

def sample(clip,t,data):
    key=id(data)
    if key not in clip.baked:clip.baked[key]=load(data)
    cache=clip.baked[key]
    if cache is None:return None
    clock=max(0.,t-clip.entry_clock)%DURATION;frame=clock*HZ;i=min(int(frame),799);u=frame-i
    a=cache['q'][i];b=cache['q'][i+1];b=np.where(np.sum(a*b,axis=1)[:,None]<0,-b,b)
    q=a*(1-u)+b*u;q/=np.maximum(np.linalg.norm(q,axis=1)[:,None],1e-12)
    x,y,z,w=q.T;r=np.empty((len(q),3,3))
    r[:,0,0]=1-2*(y*y+z*z);r[:,0,1]=2*(x*y-z*w);r[:,0,2]=2*(x*z+y*w)
    r[:,1,0]=2*(x*y+z*w);r[:,1,1]=1-2*(x*x+z*z);r[:,1,2]=2*(y*z-x*w)
    r[:,2,0]=2*(x*z-y*w);r[:,2,1]=2*(y*z+x*w);r[:,2,2]=1-2*(x*x+y*y)
    shift=cache['shift'][i]*(1-u)+cache['shift'][i+1]*u
    hands=cache['hands'][i]*(1-u)+cache['hands'][i+1]*u
    clip.support_targets[key]={side:hands[k] for k,side in enumerate(('left','right')) if cache['engaged'][i,k] and cache['engaged'][i+1,k]}
    return dict(zip(cache['nodes'],r)),shift,{'happy':.12,'relaxed':.08}
