"""Measure furniture contact anchors from real triangles in a metric GLB."""
import numpy as np

def surface_outline(triangles,height):
    """Convex footprint of actual surface vertices, not triangle centroids."""
    points=sorted(set(map(tuple,np.asarray(triangles).reshape(-1,3)[:,[0,2]])))
    def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    lower=[];upper=[]
    for p in points:
        while len(lower)>1 and cross(lower[-2],lower[-1],p)<=0:lower.pop()
        lower.append(p)
    for p in reversed(points):
        while len(upper)>1 and cross(upper[-2],upper[-1],p)<=0:upper.pop()
        upper.append(p)
    return [[float(x),float(height),float(z)] for x,z in lower[:-1]+upper[:-1]]

def exposed_from_above(points,asset,parts=None):
    """Reject hidden upward shell faces below the actual cushion surface."""
    triangles=np.concatenate([p['pos'][p['indices'].reshape(-1,3)] for p in (asset.parts if parts is None else parts)])
    a=triangles[:,0];u=triangles[:,1]-a;v=triangles[:,2]-a
    determinant=u[:,0]*v[:,2]-u[:,2]*v[:,0];valid=abs(determinant)>1e-10
    a,u,v,determinant=a[valid],u[valid],v[valid],determinant[valid]
    result=[]
    for start in range(0,len(points),24):
        q=points[start:start+24];dx=q[:,None,0]-a[None,:,0];dz=q[:,None,2]-a[None,:,2]
        first=(dx*v[:,2]-dz*v[:,0])/determinant;second=(u[:,0]*dz-u[:,2]*dx)/determinant
        inside=(first>=-1e-5)&(second>=-1e-5)&(first+second<=1.00001)
        y=a[:,1]+first*u[:,1]+second*v[:,1]
        result.extend(~np.any(inside&(y>q[:,None,1]+.012),axis=1))
    return np.asarray(result,dtype=bool)

def horizontal_surface(asset,parts=None,band=(.18,.78),occluder_parts=None):
    centers=[];areas=[];faces=[]
    for part in asset.parts if parts is None else parts:
        triangles=part['pos'][part['indices'].reshape(-1,3)];normal=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0]);area=np.linalg.norm(normal,axis=1)*.5
        center=triangles.mean(axis=1);normal/=np.maximum(area[:,None]*2,1e-12)
        lo=asset.minimum[1]+asset.extent[1]*band[0];hi=asset.minimum[1]+asset.extent[1]*band[1]
        mask=(normal[:,1]>.82)&(center[:,1]>=lo)&(center[:,1]<=hi)&(area>1e-9)
        centers.append(center[mask]);areas.append(area[mask]);faces.append(triangles[mask])
    points=np.concatenate(centers);weights=np.concatenate(areas);faces=np.concatenate(faces)
    if not len(points):raise ValueError('Oturma yüzeyi bulunamadı.')
    exposed=exposed_from_above(points,asset,occluder_parts);points=points[exposed];weights=weights[exposed];faces=faces[exposed]
    if not len(points):raise ValueError('Üstten erişilebilir oturma yüzeyi bulunamadı.')
    bins=np.linspace(asset.minimum[1],asset.maximum[1],101);hist,_=np.histogram(points[:,1],bins,weights=weights);index=int(np.argmax(hist))
    y=(bins[index]+bins[index+1])*.5;chosen=np.abs(points[:,1]-y)<max(asset.extent[1]*.02,.005)
    points=points[chosen];weights=weights[chosen];faces=faces[chosen];center=np.average(points,axis=0,weights=weights)
    keep=np.unique(np.r_[np.linspace(0,len(points)-1,min(128,len(points)),dtype=int),points.argmin(axis=0),points.argmax(axis=0)])
    return {'center':center.tolist(),'minimum':points.min(axis=0).tolist(),'maximum':points.max(axis=0).tolist(),'area':float(weights.sum()),'patch':points[keep].tolist(),'outline':surface_outline(faces,center[1])}

def seat_profile(asset,desk_set=False):
    parts=[p for p in asset.parts if 'chair' in p['name'].casefold()] if desk_set else asset.parts
    if not parts:raise ValueError('Masa setinde sandalye parçası bulunamadı.')
    explicit=[p for p in parts if 'seat' in p['name'].casefold()]
    surface=horizontal_surface(asset,explicit or parts,band=(.15,.75),occluder_parts=parts if desk_set else None);center=np.array(surface['center'])
    back_parts=[p for p in parts if any(word in p['name'].casefold() for word in ('back','rest')) and 'armrest' not in p['name'].casefold()]
    cloud=np.concatenate([p['pos'] for p in back_parts or parts])
    high=cloud[(cloud[:,1]>center[1]+asset.extent[1]*.20)&(np.abs(cloud[:,0]-center[0])<asset.extent[0]*.35)]
    if not len(high):raise ValueError('Sandalye sırtı bulunamadı.')
    back=np.median(high,axis=0);delta=back-center;delta[1]=0
    forward=-delta/max(float(np.linalg.norm(delta)),1e-8)
    side=np.cross([0.,1.,0.],forward)
    near=np.array(surface['outline'])
    width=float(np.ptp(near@side));depth=float(np.ptp(near@forward))
    return {**surface,'forward':forward.tolist(),'width':width,'depth':depth,'seat_height':float(center[1]),'back':back.tolist(),'status':'measured_pending_pose_validation'}
