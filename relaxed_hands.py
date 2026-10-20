"""Model-space relaxed hands; bend toward the palm, never guess local X."""
import math
import numpy as np
from vrm import rotation
_CACHE={}
def relaxed_hands(rotations,target):
 key=id(target)
 if key not in _CACHE:
  rest={name:(target.rest[node,:3,3]@target.flip.T-target.origin)*target.scale for name,node in target.bones.items()};adjustments={}
  for side in ('left','right'):
   hand=side+'Hand';index=side+'IndexProximal';little=side+'LittleProximal'
   if not all(n in rest for n in (hand,index,little)):continue
   palm=np.cross(rest[index]-rest[hand],rest[little]-rest[hand]);palm/=max(1e-9,np.linalg.norm(palm))
   thumb=side+('ThumbProximal' if target.legacy else 'ThumbMetacarpal')
   if thumb in rest and np.dot(palm,rest[thumb]-rest[hand])<0:palm=-palm
   angles={'Index':(12,18,10),'Middle':(15,22,12),'Ring':(18,25,14),'Little':(22,27,15),'Thumb':(7,10,12)}
   for finger,degrees in angles.items():
    labels=('Proximal','Intermediate','Distal') if finger!='Thumb' or target.legacy else ('Metacarpal','Proximal','Distal')
    for k,label in enumerate(labels):
     name=side+finger+label;node=target.bones.get(name)
     if node is None:continue
     following=side+finger+labels[k+1] if k<2 else None
     if following in rest:direction=rest[following]-rest[name]
     elif k>0:direction=rest[name]-rest[side+finger+labels[k-1]]
     else:continue
     direction/=max(1e-9,np.linalg.norm(direction));axis=np.cross(direction,palm);axis/=max(1e-9,np.linalg.norm(axis))
     local_axis=np.linalg.inv(target.rest[node,:3,:3])@target.flip.T@axis
     local_axis/=max(1e-9,np.linalg.norm(local_axis));theta=math.radians(degrees[k])
     adjustments[node]=rotation([*(local_axis*math.sin(theta/2)),math.cos(theta/2)])
   thumb_labels=('Proximal','Intermediate') if target.legacy else ('Metacarpal','Proximal')
   first=side+'Thumb'+thumb_labels[0];next_thumb=side+'Thumb'+thumb_labels[1]
   middle=side+'MiddleProximal';next_middle=side+'MiddleIntermediate'
   if all(n in rest for n in (first,next_thumb,middle,next_middle)):
    thumb_dir=rest[next_thumb]-rest[first];thumb_dir/=max(1e-9,np.linalg.norm(thumb_dir))
    finger_dir=rest[next_middle]-rest[middle];finger_dir/=max(1e-9,np.linalg.norm(finger_dir))
    axis=np.cross(thumb_dir,finger_dir);axis/=max(1e-9,np.linalg.norm(axis));node=target.bones[first]
    local_axis=np.linalg.inv(target.rest[node,:3,:3])@target.flip.T@axis;local_axis/=max(1e-9,np.linalg.norm(local_axis))
    theta=min(math.radians(18),math.acos(float(np.clip(np.dot(thumb_dir,finger_dir),-1,1)))*.4)
    adjustments[node]=adjustments.get(node,np.eye(3))@rotation([*(local_axis*math.sin(theta/2)),math.cos(theta/2)])
   node=target.bones[hand];forward=rest[side+'MiddleProximal']-rest[hand];forward/=max(1e-9,np.linalg.norm(forward));axis=np.cross(forward,palm);axis/=max(1e-9,np.linalg.norm(axis));local_axis=np.linalg.inv(target.rest[node,:3,:3])@target.flip.T@axis;local_axis/=max(1e-9,np.linalg.norm(local_axis));theta=math.radians(3)
   adjustments[node]=rotation([*(local_axis*math.sin(theta/2)),math.cos(theta/2)])
  _CACHE[key]=adjustments
 result=dict(rotations)
 for node,offset in _CACHE[key].items():result[node]=result.get(node,target.local[node][:3,:3])@offset
 return result
