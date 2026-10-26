"""Pose-time drape and cushion contacts for hip-suspended authored skirts.
Source geometry, UVs, weights and assets stay immutable.
"""
import numpy as np

def panels(model):
    if hasattr(model,'_seated_panels'):return model._seated_panels
    from garment_contacts import hanging_nodes
    d=model.data;hip=d.bones['hips'];suspended=hanging_nodes(model);eligible=set(suspended);result=[]
    # Thigh-attached skirt panels keep their authored moving frame. They need
    # body contact too, but must never receive pelvis-frame draping.
    for node in model.hair_springs.cloth_nodes:
        ancestor=node
        while ancestor in d.parents and ancestor not in d.bones.values():ancestor=d.parents[ancestor]
        if ancestor in (d.bones['leftUpperLeg'],d.bones['rightUpperLeg']):eligible.add(node)
    for ordinal,part in enumerate(d.parts):
        if part['kind']!='cloth' or part['skin'] is None or 'joints' not in part:continue
        nodes,inverse=d.skins[part['skin']];mapped=nodes[part['joints']]
        used=np.unique(part['indices'])
        mass=np.sum(part['weights']*np.isin(mapped,list(eligible)),axis=1)
        if not np.any(mass[used]>.15):continue
        palette=d.rest[nodes]@inverse
        skin=np.sum(palette[part['joints']]*part['weights'][:,:,None,None],axis=1)
        rest=np.einsum('nij,nj->ni',skin,np.c_[part['pos'],np.ones(len(part['pos']))])[:,:3]
        canonical=(rest-d.rest[hip,:3,3])@d.flip.T*d.scale
        depth=-canonical[:,1];radial=np.maximum(np.linalg.norm(canonical[:,[0,2]],axis=1),.01)
        front=np.clip((canonical[:,2]/radial-.05)/.65,0,1)
        suspended_mass=np.sum(part['weights']*np.isin(mapped,list(suspended)),axis=1)
        blend=front*np.clip((depth+.04)/.15,0,1)*np.clip(suspended_mass/np.maximum(mass,1e-9),0,1)
        # Include side/back skirt vertices for cushion contact as well.
        ids=used[(depth[used]>-.20)&(mass[used]>.15)]
        if len(ids):result.append((ordinal,part,ids,rest[ids],canonical[ids],blend[ids]))
    model._seated_panels=result;return result

def patches(model):
    seating=model.seating
    weight=float(seating.weight) if seating is not None else 0.
    if weight<=.001:return []
    d=model.data;w=model.world;hip=d.bones['hips'];out=[]
    frame=w[hip]@np.linalg.inv(d.rest[hip]);origin=(w[hip,:3,3]@d.flip.T-d.origin)*d.scale
    # Actual leg direction controls the drape continuously during lower/rise.
    pitches=[]
    for side in ('left','right'):
        axis=(w[d.bones[side+'LowerLeg'],:3,3]-w[d.bones[side+'UpperLeg'],:3,3])@d.flip.T
        pitches.append(np.arctan2(max(0.,axis[2]),-axis[1]))
    angle=min(float(np.mean(pitches)),np.radians(80))
    for ordinal,part,ids,rest,relative,blend in panels(model):
        nodes,inverse=d.skins[part['skin']];palette=w[nodes]@inverse
        skin=np.sum(palette[part['joints'][ids]]*part['weights'][ids,:,None,None],axis=1)
        posed=np.einsum('nij,nj->ni',skin,np.c_[part['pos'][ids],np.ones(len(ids))])[:,:3]
        posed=(posed@d.flip.T-d.origin)*d.scale
        hanging=(np.c_[rest,np.ones(len(ids))]@frame.T)[:,:3]
        target=(hanging@d.flip.T-d.origin)*d.scale
        depth=np.maximum(0.,-relative[:,1])
        target[:,1]+=depth*(1-np.cos(angle))
        target[:,2]+=depth*np.sin(angle)
        # The front cloth lies above the occupied thighs rather than being
        # pushed sideways between their overlapping collision capsules.
        p=model.hair_springs.physics;p.update(w)
        for i,c in enumerate(p.capsules):
            if c.name not in ('leftThigh','rightThigh'):continue
            a=(p.starts[i]@d.flip.T-d.origin)*d.scale;b=(p.ends[i]@d.flip.T-d.origin)*d.scale
            axis=b-a;horizontal=axis[[0,2]];den=max(horizontal@horizontal,1e-9)
            f=np.clip((target[:,[0,2]]-a[[0,2]])@horizontal/den,0,1)
            center=a+f[:,None]*axis;distance=np.sum((target[:,[0,2]]-center[:,[0,2]])**2,axis=1)
            radius=c.radius*d.scale+.025;valid=distance<radius*radius
            top=center[:,1]+np.sqrt(np.maximum(0.,radius*radius-distance))
            target[valid,1]=np.maximum(target[valid,1],top[valid])
        amount=blend*weight
        corrected=posed+(target-posed)*amount[:,None]
        # Spring rotations cannot remove deep panel/body overlap. Project
        # only this hip-suspended draw region, retaining authored bind overlap.
        def distances(points,starts,ends):
            axes=ends-starts;squared=np.maximum(np.sum(axes*axes,axis=1),1e-12)
            fractions=np.clip(np.einsum('vci,ci->vc',points[:,None,:]-starts,axes)/squared,0,1)
            centers=starts+fractions[:,:,None]*axes
            radial=points[:,None,:]-centers
            lengths=np.linalg.norm(radial,axis=2)
            return radial,lengths
        starts=(p.starts@d.flip.T-d.origin)*d.scale;ends=(p.ends@d.flip.T-d.origin)*d.scale
        radii=p.radii*d.scale
        cache=part.setdefault('_seat_bind_contacts',{})
        if len(ids) not in cache:
            rest_points=(rest@d.flip.T-d.origin)*d.scale
            rest_starts=np.array([(d.rest[c.first,:3,3]@d.flip.T-d.origin)*d.scale for c in p.capsules])
            rest_ends=np.array([(d.rest[c.second,:3,3]@d.flip.T-d.origin)*d.scale for c in p.capsules])
            _,lengths=distances(rest_points,rest_starts,rest_ends)
            cache[len(ids)]=np.minimum(radii,lengths*.98)
        contact_radii=cache[len(ids)]
        for _ in range(6):
            radial,lengths=distances(corrected,starts,ends)
            depths=contact_radii-lengths;which=depths.argmax(1)
            depth=depths[np.arange(len(ids)),which]
            normals=radial[np.arange(len(ids)),which]/np.maximum(lengths[np.arange(len(ids)),which,None],1e-9)
            if float(depth.max())<.001:break
            correction=np.maximum(0,depth+.001)*weight
            correction*=np.clip(((-relative[:,1])+.20)/.12,0,1)
            corrected+=normals*correction[:,None]
        environment=getattr(model.hair_springs.physics,'environment',None)
        if environment is not None and not environment.scene.desk:
            # A point below a thin cushion may be outside its closed solid.
            # For waist-suspended cloth, use the occupied seat's top crossing
            # to stop it passing through and hanging underneath the cushion.
            local=corrected@environment.matrix[:3,:3].T+environment.matrix[:3,3]
            top,valid=environment.fields[0].sample(local)
            root=origin@environment.matrix[:3,:3].T+environment.matrix[:3,3]
            hit=valid&(local[:,1]<top+.015)&(root[1]>top-.04)
            local[hit,1]+=(top[hit]+.015-local[hit,1])*weight
            corrected=local@environment.inverse[:3,:3].T+environment.inverse[:3,3]
        source=(corrected/d.scale+d.origin)@d.flip
        bind=np.linalg.solve(skin,np.c_[source,np.ones(len(ids))][...,None])[... ,0][:,:3]
        out.append({'part':ordinal,'ids':ids.tolist(),'positions':np.round(bind,6).ravel().tolist()})
    return out
