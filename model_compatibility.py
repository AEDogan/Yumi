"""Capabilities measured from the imported rig; source assets remain immutable."""
import numpy as np

REQUIRED=('hips','head','leftUpperArm','leftLowerArm','leftHand','rightUpperArm',
          'rightLowerArm','rightHand','leftUpperLeg','leftLowerLeg','leftFoot',
          'rightUpperLeg','rightLowerLeg','rightFoot')

def profile(data):
    missing=[name for name in REQUIRED if name not in data.bones]
    def chain_valid(names):
        nodes=[data.bones.get(name) for name in names]
        if any(node is None for node in nodes) or len(set(nodes))!=len(nodes):return False
        for parent,child in zip(nodes,nodes[1:]):
            seen=set();ancestor=data.parents.get(child)
            while ancestor is not None and ancestor!=parent and ancestor not in seen:
                seen.add(ancestor);ancestor=data.parents.get(ancestor)
            if ancestor!=parent:return False
        return True
    fingers={side:[finger for finger in ('Thumb','Index','Middle','Ring','Little')
        if chain_valid([side+'Hand']+[side+finger+joint for joint in
               (('Metacarpal','Proximal','Distal') if finger=='Thumb' and not data.legacy
                else ('Proximal','Intermediate','Distal'))])] for side in ('left','right')}
    issues=[];lengths={};rest=getattr(data,'rest',None)
    if rest is not None:
        for name,node in data.bones.items():
            if not isinstance(node,(int,np.integer)) or not 0<=node<len(rest):
                issues.append(name+': geçersiz kemik indeksi');continue
            matrix=rest[node]
            if not np.isfinite(matrix).all() or np.linalg.cond(matrix[:3,:3])>1e6:
                issues.append(name+': geçersiz veya tekil başlangıç dönüşümü')
        for side in ('left','right'):
            for chain in (('UpperArm','LowerArm','Hand'),('UpperLeg','LowerLeg','Foot')):
                names=[side+n for n in chain]
                if not all(n in data.bones for n in names):continue
                if not chain_valid(names):issues.append(side+chain[0]+': hatalı uzuv hiyerarşisi')
                if any(not isinstance(data.bones[n],(int,np.integer)) or not 0<=data.bones[n]<len(rest) for n in names):continue
                values=[float(np.linalg.norm(rest[data.bones[b],:3,3]-rest[data.bones[a],:3,3])) for a,b in zip(names,names[1:])]
                lengths[side+chain[0]]=values
                if min(values)<1e-7:issues.append(side+chain[0]+': sıfır uzunluklu uzuv')
        required_nodes=[data.bones[n] for n in REQUIRED if n in data.bones]
        if len(set(required_nodes))!=len(required_nodes):issues.append('Bir düğüm birden fazla zorunlu kemiğe atanmış.')
        if not missing and not chain_valid(['hips','head']):issues.append('Baş, kalça kökünün altında değil.')
    springs=data.analysis.get('authored_springs',[]) if getattr(data,'analysis',None) else []
    return {'source_sha256':data.source_sha256,'mapping_sha256':getattr(data,'mapping_sha256',None),
        'source_version':'VRM0' if data.legacy else 'VRM1','missing_required_bones':missing,
        'fingers':fingers,'limb_lengths':lengths,'rig_issues':issues,
        'expressions':sorted(n for n,b in data.expressions.items() if b),
        'authored_spring_chains':len(springs),'physics_missing':not bool(springs),
        'desktop_supported':not missing and not issues,
        'limits':['Kaynakta olmayan yüz ifadesi veya fizik eklenmedi.','SpringBone tam kumaş/öz-çarpışma çözümü değildir.']}

def summary(report):
    rows=[]
    if report['missing_required_bones']:rows.append('Eksik iskelet: '+', '.join(report['missing_required_bones']))
    rows.extend(report['rig_issues'])
    for side,label in (('left','Sol'),('right','Sağ')):
        absent=5-len(report['fingers'][side])
        if absent:rows.append(f'{label} elde {absent} parmak zinciri eksik; ilgili jestler sınırlı.')
    if report['physics_missing']:rows.append('Kaynakta ikincil fizik tanımı yok.')
    return '\n'.join(rows) or 'İskelet, parmaklar ve kaynak fizik tanımları hazır.'
