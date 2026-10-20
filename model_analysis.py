"""Evidence-based asset anatomy; metadata and virtual regions, never mesh surgery.

Appearance is not a constitutive material model. Mechanical properties remain
unknown unless an author supplied spring parameters or a verified override.
"""
from __future__ import annotations
import re
import numpy as np

VERSION=4
ALIASES={'aa':('aa','a'),'ih':('ih','i'),'ou':('ou','u'),'ee':('ee','e'),'oh':('oh','o'),
    'happy':('happy','joy'),'sad':('sad','sorrow'),'relaxed':('relaxed','fun'),
    'blinkLeft':('blinkleft','blink_l','blink'),'blinkRight':('blinkright','blink_r','blink'),
    'blink':('blink',),'angry':('angry',),'surprised':('surprised',),
    'browInnerUp':('browinnerup',),
    'browOuterUpLeft':('browouterupleft',),'browOuterUpRight':('browouterupright',),
    'browDownLeft':('browdownleft',),'browDownRight':('browdownright',),
    'cheekSquintLeft':('cheeksquintleft',),'cheekSquintRight':('cheeksquintright',),
    'eyeSquintLeft':('eyesquintleft',),'eyeSquintRight':('eyesquintright',),
    'eyeWideLeft':('eyewideleft',),'eyeWideRight':('eyewideright',)}
ALIAS_KEYS={k.lower():k for k in ALIASES}

def spring_declarations(data):
    """Preserve authored coefficients; membership is not a material classifier."""
    records=[]
    if data.legacy:
        groups=data.vrm.get('secondaryAnimation',{}).get('boneGroups',[])
        for group in groups:
            roots=[i for i in group.get('bones',[]) if isinstance(i,int) and 0<=i<len(data.nodes)]
            nodes=set();stack=list(roots)
            while stack:
                node=stack.pop()
                if node in nodes or node in data.bones.values():continue
                nodes.add(node);stack.extend(data.nodes[node].get('children',[]))
            records.append({'nodes':sorted(nodes),'source':'VRM.secondaryAnimation',
                'parameters':{k:group[k] for k in ('stiffiness','gravityPower','gravityDir','dragForce','hitRadius') if k in group}})
    else:
        for group in data.g.get('extensions',{}).get('VRMC_springBone',{}).get('springs',[]):
            joints=group.get('joints',[])
            records.append({'nodes':[j['node'] for j in joints if isinstance(j.get('node'),int) and 0<=j['node']<len(data.nodes)],
                'source':'VRMC_springBone','parameters':[{k:j[k] for k in ('node','stiffness','gravityPower','gravityDir','dragForce','hitRadius') if k in j} for j in joints]})
    return records

def region(name):
    if any(t in name for t in ('Thumb','Index','Middle','Ring','Little')):return 'finger'
    if 'Eye' in name:return 'eye'
    if name=='jaw':return 'jaw'
    if 'Hand' in name:return 'hand'
    if 'Arm' in name or 'Shoulder' in name:return 'arm'
    if 'Leg' in name:return 'leg'
    if 'Foot' in name or 'Toes' in name:return 'foot'
    if name in ('head','neck'):return name
    return 'torso'

def drawable_mask(part):
    """POSITION buffers may be shared; only indexed vertices belong to a part."""
    mask=np.zeros(len(part['pos']),dtype=bool)
    mask[np.asarray(part['indices']).reshape(-1)]=True
    return mask

def analyze(data):
    springs=spring_declarations(data);spring_nodes={n for s in springs for n in s['nodes']}
    mapped={node:name for name,node in data.bones.items()};parts=[]
    for index,part in enumerate(data.parts):
        node=data.nodes[part['node']];mesh=data.g['meshes'][part['mesh']]
        materials=data.g.get('materials',[]);material=materials[part['material']] if part['material']<len(materials) else {}
        label=' '.join((node.get('name',''),mesh.get('name',''),material.get('name',''))).casefold()
        hints=[]
        for tag,pattern in [('hair',r'hair|髪|kami'),('eye',r'eye|瞳|iris|pupil'),('mouth',r'mouth|teeth|tongue|口'),
                            ('face',r'face|顔'),('cloth',r'cloth|dress|skirt|cape|jacket|coat|衣|服'),('shoe',r'shoe|boot|靴')]:
            if re.search(pattern,label):hints.append(tag)
        referenced=drawable_mask(part)
        record={'part':index,'node':part['node'],'mesh':part['mesh'],'material':part['material'],
            'name':node.get('name',mesh.get('name','')),'vertices':len(part['pos']),'triangles':len(part['indices'])//3,
            'vertices_buffer':len(part['pos']),'referenced_vertices':int(referenced.sum()),
            'semantic_hints':hints,'semantic_confidence':'name_hint_only' if hints else 'unknown',
            'mechanics':{'material':'unknown','stiffness':None,'friction':None,'thickness':None},
            'visual_material':{'name':material.get('name',''),'alphaMode':material.get('alphaMode','OPAQUE'),
                'doubleSided':material.get('doubleSided',False),'pbr':material.get('pbrMetallicRoughness',{})},
            'morph_targets':mesh.get('extras',{}).get('targetNames',[]),
            'expression_bindings':sorted(n for n,b in data.expressions.items() if any(mi==part['mesh'] for mi,_,_ in b)),
            'bone_influence':[],'regions':{},'spring_weight_fraction':0.,'deformation':'node_transform',
            'evidence':['glTF primitive/material references']}
        skin=part.get('skin')
        if skin is not None and 'weights' in part and 'joints' in part:
            joints=data.skins[skin][0];weights=part['weights'][referenced];local=part['joints'][referenced]
            histogram=np.bincount(local.ravel(),weights=weights.ravel(),minlength=len(joints));total=max(float(histogram.sum()),1e-12)
            regions={};spring_fraction=0.
            for joint in np.flatnonzero(histogram>1e-8):
                ni=int(joints[joint]);fraction=float(histogram[joint]/total);cursor=ni;seen=set()
                while cursor not in mapped and cursor in data.parents and cursor not in seen:
                    seen.add(cursor);cursor=data.parents[cursor]
                semantic=region(mapped[cursor]) if cursor in mapped else 'unmapped'
                regions[semantic]=regions.get(semantic,0.)+fraction
                if ni in spring_nodes:spring_fraction+=fraction
                record['bone_influence'].append({'node':ni,'name':data.nodes[ni].get('name',''),
                    'humanoid_ancestor':mapped.get(cursor),'weight_fraction':round(fraction,6)})
            record['bone_influence'].sort(key=lambda r:-r['weight_fraction'])
            record['regions']={k:round(v,6) for k,v in sorted(regions.items())}
            record['spring_weight_fraction']=round(spring_fraction,6)
            record['deformation']='skeletal_skin'
            record['evidence'].append('JOINTS_0 / normalized WEIGHTS_0; humanoid ancestor mapping')
            if spring_fraction>0:record['evidence'].append('authored spring joint influence; not full cloth')
        parts.append(record)
    expression_map={key:next((n for n in names if data.expressions.get(n)),None) for key,names in ALIASES.items()}
    return {'schema_version':VERSION,'source_sha256':data.source_sha256,
        'mapping_sha256':getattr(data,'mapping_sha256',None),'parts':parts,
        'humanoid':{k:{'node':v,'name':data.nodes[v].get('name','')} for k,v in sorted(data.bones.items())},
        'expressions':expression_map,'authored_springs':springs,
        'limits':['Name hints are unverified semantics.','Skin weights describe attachment, not material flexibility.',
                  'Mixed primitives remain virtual weighted regions; no destructive splitting.',
                  'No full cloth/self collision or mechanical constants inferred from PBR.']}

def expression_name(data,name):
    """Resolve only expressions that exist; unsupported expressions stay absent."""
    exact=name.lower()
    if data.expressions.get(exact):return exact
    return data.analysis['expressions'].get(ALIAS_KEYS.get(exact,exact))

def region_weights(data,part_index,target):
    """Non-destructive vertex mask from skin influence, computed only on demand.

    A finger mask denotes attachment to a finger bone, not a watertight finger
    mesh. Head weights cannot distinguish an eye from the surrounding face.
    """
    part=data.parts[part_index];result=np.zeros(len(part['pos']),dtype=np.float32)
    if part.get('skin') is None or 'joints' not in part:return result
    nodes=data.skins[part['skin']][0];mapped={n:k for k,n in data.bones.items()};selected=[]
    for i,node in enumerate(nodes):
        cursor=int(node);seen=set()
        while cursor not in mapped and cursor in data.parents and cursor not in seen:
            seen.add(cursor);cursor=data.parents[cursor]
        semantic=region(mapped[cursor]) if cursor in mapped else 'unmapped'
        if semantic==target:selected.append(i)
    result=np.sum(part['weights']*np.isin(part['joints'],selected),axis=1).astype(np.float32)
    result[~drawable_mask(part)]=0.
    return result

def expression_mask(data,part_index,name):
    """Vertices actually displaced by an authored expression, not guessed anatomy."""
    part=data.parts[part_index];result=np.zeros(len(part['pos']),dtype=bool)
    target=expression_name(data,name)
    for mesh,index,weight in data.expressions.get(target,[]):
        if mesh==part['mesh'] and weight and index in part['morphs']:
            result|=np.any(np.abs(part['morphs'][index])>1e-7,axis=1)
    return result&drawable_mask(part)

def analyze_prop(asset,source_sha256):
    """Profile static rest geometry without pretending its material is rigid."""
    from types import SimpleNamespace
    view=SimpleNamespace(g=asset.g,nodes=asset.g.get('nodes',[]),parts=asset.parts,
        bones={},parents={},skins=[],vrm={},legacy=False,expressions={},source_sha256=source_sha256)
    profile=analyze(view)
    for record in profile['parts']:
        record['deformation']='baked_rest_static'
        record['evidence'].append('Yumi item loader evaluates rest pose; source animation is not played')
    profile['limits'].append('Static rendering does not establish physical rigidity.')
    return profile
