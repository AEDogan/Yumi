"""Authored lower-garment skin regions against measured, posed leg capsules."""
import numpy as np

def hanging_nodes(model):
    """Hip-frame projection is valid only for authored hip-suspended panels.

    Direct leg skinning (trousers) and springs attached to a thigh (shirt hems)
    follow different moving frames. A ray away from the pelvis can drive their
    inner faces through the opposite leg; leave their authored skinning intact.
    """
    d=model.data;eligible=set();humanoid=set(d.bones.values())
    for node in model.hair_springs.cloth_nodes:
        ancestor=node
        while ancestor in d.parents and ancestor not in humanoid:ancestor=d.parents[ancestor]
        if ancestor==d.bones.get('hips'):eligible.add(node)
    return eligible

def weights(model,part):
    if 'garment_contact_weight' in part:return part['garment_contact_weight']
    d=model.data;result=np.zeros(len(part['pos']),dtype='float32')
    # The upstream solver owns authored secondary deformation. Do not apply
    # the old pelvis-frame hanging/projection on top of its spring results.
    if getattr(model.hair_springs,'backend',None)=='three-vrm':
        part['garment_contact_weight']=result;return result
    if part['skin'] is not None and 'joints' in part:
        eligible=hanging_nodes(model)
        nodes=d.skins[part['skin']][0][part['joints']]
        result=np.sum(part['weights']*np.isin(nodes,list(eligible)),axis=1).astype('float32')
        result=np.clip((result-.15)/.60,0.,1.).astype('float32')
        referenced=np.zeros(len(result),dtype=bool);referenced[part['indices']]=True;result[~referenced]=0.
    part['garment_contact_weight']=result;return result

def rest_points(model,part):
    """Bind geometry in the source skeleton frame, shared by seam duplicates."""
    if 'garment_rest' not in part:
        d=model.data;nodes,inverse=d.skins[part['skin']];palette=d.rest[nodes]@inverse
        points=np.c_[part['pos'],np.ones(len(part['pos']))];result=np.zeros_like(points)
        for channel in range(4):
            result+=np.einsum('nij,nj->ni',palette[part['joints'][:,channel]],points)*part['weights'][:,channel,None]
        eligible=list(hanging_nodes(model))
        joints=nodes[part['joints']]
        hanging=np.sum(part['weights']*np.isin(joints,eligible),axis=1)
        hanging*=weights(model,part)>0
        part['garment_rest']=np.ascontiguousarray(np.c_[result[:,:3],hanging],dtype='float32')
    return part['garment_rest']

def capsules(model):
    d=model.data;p=model.hair_springs.physics;p.update(model.world)
    indices=[i for i,c in enumerate(p.capsules) if c.name in ('pelvis','leftThigh','leftShin','rightThigh','rightShin')]
    if not hasattr(d,'_garment_body_radii') or set(indices)!=set(d._garment_body_radii):
        radii={}
        for i in indices:
            c=p.capsules[i];a=d.rest[c.first,:3,3];axis=d.rest[c.second,:3,3]-a;squared=max(float(axis@axis),1e-9);samples=[]
            for part in d.parts:
                if part['kind']!='body' or part['skin'] is None or 'joints' not in part:continue
                joints=d.skins[part['skin']][0][part['joints']]
                influenced=[d.bones['hips']] if c.name=='pelvis' else [c.first,c.second]
                influence=np.sum(part['weights']*np.isin(joints,influenced),axis=1)
                used=np.unique(part['indices']);used=used[(influence[used]>.6)&(weights(model,part)[used]<.15)][::2]
                if not len(used):continue
                points=np.c_[part['pos'][used],np.ones(len(used))];nodes,inverse=d.skins[part['skin']];palette=d.rest[nodes]@inverse;posed=np.zeros_like(points)
                for channel in range(4):posed+=np.einsum('nij,nj->ni',palette[part['joints'][used,channel]],points)*part['weights'][used,channel,None]
                fraction=(posed[:,:3]-a)@axis/squared;valid=(fraction>.1)&(fraction<.85)
                distance=np.linalg.norm(posed[valid,:3]-a-fraction[valid,None]*axis,axis=1)
                if c.name=='pelvis':distance=np.abs((posed[valid,:3]-a)@(d.flip.T@np.array([0.,0.,1.])))
                # A horizontal pelvis axis also projects distant leg vertices
                # into its interval. Those are not pelvis thickness samples.
                samples.extend(distance[distance<c.radius*1.8])
            radii[i]=float(np.percentile(samples,98)) if samples else c.radius
        d._garment_body_radii=radii
    start=np.zeros((6,4),dtype='float32');end=np.zeros((6,4),dtype='float32')
    for k,i in enumerate(indices[:6]):
        start[k,:3]=(p.starts[i]@d.flip.T-d.origin)*d.scale;end[k,:3]=(p.ends[i]@d.flip.T-d.origin)*d.scale
        # A finite triangle spans a chord of the curved body surface. Reserve
        # clearance for that interior, not just for its endpoint vertices.
        start[k,3]=d._garment_body_radii[i]*d.scale+.020
    return start,end

def project(points,normals,weight,start,end,center=None):
    """CPU reference for the exact vertex shader contact, preserving topology."""
    result=np.asarray(points,float).copy();normals=np.asarray(normals,float)
    if center is not None:
        outward=result-np.asarray(center);outward[:,1]=0.
        valid=np.linalg.norm(outward,axis=1)>1e-7;normals=normals.copy();normals[valid]=outward[valid]
    normals=normals/np.maximum(np.linalg.norm(normals,axis=1)[:,None],1e-9)
    for _ in range(2):
        for a,b in zip(start,end):
            if a[3]<=0:continue
            axis=b[:3]-a[:3];fraction=np.clip((result-a[:3])@axis/max(axis@axis,1e-9),0.,1.)
            radial=result-(a[:3]+fraction[:,None]*axis);distance=np.linalg.norm(radial,axis=1)
            hit=(distance<a[3])&(weight>0)
            along=np.sum(radial*normals,axis=1)
            travel=-along+np.sqrt(np.maximum(0.,along*along+a[3]*a[3]-distance*distance))
            result[hit]+=normals[hit]*travel[hit,None]*weight[hit,None]
    # Overlapping leg proxies can otherwise throw a panel across the body.
    # Bound visual correction; unresolved contact remains a QA limitation.
    displacement=result-np.asarray(points);length=np.linalg.norm(displacement,axis=1)
    result=np.asarray(points)+displacement*np.minimum(1.,.12/np.maximum(length,1e-9))[:,None]
    return result
