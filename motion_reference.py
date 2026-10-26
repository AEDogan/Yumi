"""Opt-in source reference alignment, without changing the asset bind pose."""
import numpy as np
from weakref import WeakKeyDictionary
from vrm import aim
from functools import lru_cache
from pathlib import Path

MODE='source-limb-directions-v1'

@lru_cache(maxsize=1)
def _hand_reference():
    # Our walk clip has no finger markers. Use the existing Yumi greeting's
    # authored knuckle plane, aligned to the walk clip's forearm direction.
    import vrma
    return vrma.MotionClip(Path(vrma.__file__).resolve().parent/'motions/Yumi-Gesture-greeting.vrma')

def hand_basis(clip,side):
    names=[side+p for p in ('Hand','IndexProximal','LittleProximal')]
    donor=clip if all(n in clip.bones for n in names) else _hand_reference()
    hand,index,little=[donor.world[donor.bones[n],:3,3] for n in names]
    forward=(index+little)*.5-hand;forward/=max(np.linalg.norm(forward),1e-12)
    lateral=index-little;lateral-=forward*np.dot(lateral,forward);lateral/=max(np.linalg.norm(lateral),1e-12)
    basis=np.column_stack((forward,lateral,np.cross(forward,lateral)))
    if donor is not clip:
        a,b=side+'LowerArm',side+'Hand'
        source=clip.world[clip.bones[b],:3,3]-clip.world[clip.bones[a],:3,3]
        reference=donor.world[donor.bones[b],:3,3]-donor.world[donor.bones[a],:3,3]
        basis=aim(reference,source)@basis
    return basis

def reference_pose(clip,target):
    extras=target.g.get('extras',{})
    config=extras.get('yumi',{}) if isinstance(extras,dict) else {}
    if not isinstance(config,dict) or config.get('motionReference')!=MODE:
        return target.local,target.rest
    cache=getattr(clip,'_reference_pose_cache',None)
    if cache is None:cache=WeakKeyDictionary();clip._reference_pose_cache=cache
    if target in cache:return cache[target]
    local=[matrix.copy() for matrix in target.local]
    def forward():
        world=np.empty_like(target.rest)
        for node in target.order:
            parent=world[target.parents[node]] if node in target.parents else np.eye(4)
            world[node]=parent@local[node]
        return world
    world=forward()
    for side in ('left','right'):
        for first,second in (('UpperArm','LowerArm'),('LowerArm','Hand')):
            a,b=side+first,side+second
            if not all(n in target.bones and n in clip.bones for n in (a,b)):continue
            source=clip.world[clip.bones[b],:3,3]-clip.world[clip.bones[a],:3,3]
            desired=target.flip.T@source
            node=target.bones[a];child=target.bones[b]
            current=world[child,:3,3]-world[node,:3,3]
            if min(np.linalg.norm(current),np.linalg.norm(desired))<1e-8:continue
            rotation=aim(current,desired)@world[node,:3,:3]
            parent=target.parents.get(node)
            local[node][:3,:3]=np.linalg.solve(world[parent,:3,:3],rotation) if parent is not None else rotation
            world=forward()
    # Match the palm frame as well as the arm directions. A hand has a forward
    # axis and a palm normal; matching only the elbow leaves the wrist twisted.
    for side in ('left','right'):
        names=[side+p for p in ('Hand','IndexProximal','LittleProximal')]
        if not all(n in target.bones for n in names) or side+'Hand' not in clip.bones:continue
        def palm_frame(matrices,bones):
            hand,index,little=[matrices[bones[n],:3,3] for n in names]
            forward=(index+little)*.5-hand;forward/=max(np.linalg.norm(forward),1e-12)
            lateral=index-little;lateral-=forward*np.dot(lateral,forward)
            if np.linalg.norm(lateral)<1e-8:return None
            lateral/=np.linalg.norm(lateral)
            return np.column_stack((forward,lateral,np.cross(forward,lateral)))
        source=hand_basis(clip,side);current=palm_frame(world,target.bones)
        if source is None or current is None:continue
        node=target.bones[side+'Hand'];rotation=(target.flip.T@source@current.T)@world[node,:3,:3]
        parent=target.parents.get(node)
        local[node][:3,:3]=np.linalg.solve(world[parent,:3,:3],rotation) if parent is not None else rotation
        world=forward()
    cache[target]=(local,world)
    return local,world
