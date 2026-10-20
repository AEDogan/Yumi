"""Bounded samples of authored finger skin, for offline grip fitting and QA."""
import numpy as np

def samples(data,side,finger,limit=96):
    cache=getattr(data,'_grip_surface_samples',None)
    if cache is None:data._grip_surface_samples={};cache=data._grip_surface_samples
    key=(side,finger,limit)
    if key in cache:return cache[key]
    chain={node for name,node in data.bones.items() if name.startswith(side+finger)}
    local=[];bones=[];weights=[]
    for part in data.parts:
        if part['skin'] is None or 'joints' not in part:continue
        nodes,inverse=data.skins[part['skin']];joints=nodes[part['joints']]
        influence=np.sum(part['weights']*np.isin(joints,list(chain)),axis=1)
        used=np.unique(part['indices']);used=used[influence[used]>.6]
        if not len(used):continue
        # Sampling follows referenced geometry only, including seam copies;
        # no semantic part-name or appearance-to-stiffness inference is used.
        used=used[np.linspace(0,len(used)-1,min(limit,len(used))).astype(int)]
        points=np.c_[part['pos'][used],np.ones(len(used))]
        bind=np.einsum('nkij,nj->nki',inverse[part['joints'][used]],points)
        local.append(bind);bones.append(joints[used]);weights.append(part['weights'][used])
    if not local:cache[key]=None;return None
    local=np.concatenate(local);bones=np.concatenate(bones);weights=np.concatenate(weights)
    selected=np.linspace(0,len(local)-1,min(limit,len(local))).astype(int)
    local=local[selected];bones=bones[selected];weights=weights[selected]
    unique,lookup=np.unique(bones,return_inverse=True)
    cache[key]=(local,weights,unique,lookup.reshape(bones.shape))
    return cache[key]

def points(sample,world,data):
    if sample is None:return np.empty((0,3))
    local,weights,nodes,lookup=sample
    matrices=np.stack([world(int(node)) for node in nodes]) if callable(world) else world[nodes]
    posed=np.sum(np.einsum('nkij,nkj->nki',matrices[lookup],local)*weights[:,:,None],axis=1)[:,:3]
    return (posed@data.flip.T-data.origin)*data.scale

def gaps(sample,world,data,pole,radius):
    posed=points(sample,world,data)
    return np.linalg.norm((posed-pole)[:,[0,2]],axis=1)-radius
