"""Fit a continuous sit/rise curve against actual, possibly open chair triangles."""
from collections import OrderedDict
import hashlib,json,os
from pathlib import Path
import numpy as np
from motion import ik
from triangle_contacts import TriangleContacts

_CACHE=OrderedDict()
def fit_curve(scene,triangles):
    model=scene.model;f=scene.fit;r=model.rest_canonical;d=model.data
    key=('v4',d.source_sha256,d.mapping_sha256,scene.fit.item.get('runtime_sha256',scene.fit.item.get('source_sha256')),round(f.scale,7),round(f.padding,7),round(f.stand_distance,7))
    if key in _CACHE:return _CACHE[key]
    cache=Path(__file__).resolve().parent/'work'/'seat-clearance'/(hashlib.sha256(json.dumps(key).encode()).hexdigest()+'.json')
    try:
        rows=json.loads(cache.read_text(encoding='utf-8'))
        weights,lifts,residual,forwards=rows
        if len(weights)==len(lifts)==len(forwards)==25 and np.isfinite(np.array([weights,lifts,forwards])).all() and 0<=residual<1 and weights[0]==0 and weights[-1]==1 and np.all(np.diff(weights)>0):
            result=(np.array(weights),np.array(lifts),float(residual),np.array(forwards));_CACHE[key]=result
            while len(_CACHE)>32:_CACHE.popitem(last=False)
            return result
    except (OSError,ValueError,TypeError):pass
    mesh=TriangleContacts(triangles);weights=np.linspace(0,1,25);lifts=[];forwards=[];residuals=[]
    radii={c.name:c.radius*d.scale for c in model.hair_springs.physics.capsules}
    amount=f.height+f.padding+f.hip_offset-r['hips'][1]
    def clearance(weight,lift,forward):
        points=[];radius=[]
        for side in ('left','right'):
            hip=r[side+'UpperLeg']+np.array([0.,amount*weight+lift,f.stand_distance*(1-weight)+forward])
            foot=r[side+'Foot']+np.array([0.,0.,f.stand_distance])
            knee,end=ik(hip,foot,np.linalg.norm(r[side+'LowerLeg']-r[side+'UpperLeg']),np.linalg.norm(r[side+'Foot']-r[side+'LowerLeg']),np.array([0.,0.,1.]),145)
            for a,b,name in ((hip,knee,'Thigh'),(knee,end,'Shin')):
                points.extend(a+(b-a)*np.linspace(0,1,9)[:,None])
                base=radii[side+name]
                vertical=base+(max(base,f.padding-.015)-base)*weight if name=='Thigh' else base
                radius.extend([(base,vertical)]*9)
        points=np.asarray(points);nearest,distance=mesh.nearest(points)
        normal=(points-nearest)/np.maximum(distance[:,None],1e-10)
        radius=np.asarray(radius)
        # Cushion compression clearance is vertical, not an isotropic balloon
        # that incorrectly makes a clothed thigh wider than the chair arms.
        effective=np.sqrt(radius[:,0]**2+(radius[:,1]**2-radius[:,0]**2)*normal[:,1]**2)
        gaps=distance-effective;index=int(np.argmin(gaps))
        return float(gaps[index]),normal[index]
    for weight in weights:
        lift=0.;forward=0.;gap,normal=clearance(weight,lift,forward)
        for _ in range(20):
            if gap>=.004 or weight<.05:break
            step=min(.025,max(.007,.005-gap))
            lift=min(.10,lift+step*max(0.,float(normal[1])))
            forward=min(.18,forward+step*max(0.,float(normal[2])))
            if normal[1]<.1 and normal[2]<.1:forward=min(.18,forward+.01)
            gap,normal=clearance(weight,lift,forward)
        lifts.append(lift);forwards.append(forward);residuals.append(max(0.,-gap))
    if os.environ.get('YUMI_SEAT_DIAGNOSTIC'):
        print('seat clearance',[(round(float(w),3),round(float(g),4),round(float(l),3),round(float(z),3)) for w,g,l,z in zip(weights,residuals,lifts,forwards) if g>.008],flush=True)
    result=(weights,np.asarray(lifts),float(max(residuals)),np.asarray(forwards))
    try:
        cache.parent.mkdir(parents=True,exist_ok=True)
        temporary=cache.with_suffix('.'+str(os.getpid())+'.tmp')
        temporary.write_text(json.dumps([weights.tolist(),lifts,result[2],forwards]),encoding='utf-8')
        temporary.replace(cache)
    except OSError:pass
    _CACHE[key]=result
    while len(_CACHE)>32:_CACHE.popitem(last=False)
    return result
