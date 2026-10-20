"""Exact nearest triangle contacts, including open furniture surfaces."""
import numpy as np

class TriangleContacts:
    def __init__(self,triangles):
        t=np.asarray(triangles,float)
        normal=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);length=np.linalg.norm(normal,axis=1)
        keep=length>1e-10;self.t=t[keep];self.normal=normal[keep]/length[keep,None]
        self.lo=self.t.min(1);self.hi=self.t.max(1);self.center=self.t.mean(1)
    def nearest(self,points):
        results=[];distances=[]
        for p in np.asarray(points,float):
            # A nearest centroid gives a safe upper bound. AABB pruning never
            # discards a long triangle merely because its centroid is far away.
            best=float(np.min(np.sum((self.center-p)**2,axis=1)))+1e-12
            delta=np.maximum(0,np.maximum(self.lo-p,p-self.hi))
            ids=np.flatnonzero(np.sum(delta*delta,axis=1)<=best)
            t=self.t[ids];n=self.normal[ids];a,b,c=t[:,0],t[:,1],t[:,2]
            q=p-n*np.sum((p-a)*n,axis=1)[:,None]
            u=b-a;v=c-a;w=q-a
            uu=np.sum(u*u,1);uv=np.sum(u*v,1);vv=np.sum(v*v,1)
            wu=np.sum(w*u,1);wv=np.sum(w*v,1);den=uu*vv-uv*uv
            s=(wu*vv-wv*uv)/np.maximum(den,1e-20);r=(wv*uu-wu*uv)/np.maximum(den,1e-20)
            valid=(s>=0)&(r>=0)&(s+r<=1)
            candidates=[np.where(valid[:,None],q,np.inf)]
            for first,last in ((a,b),(b,c),(c,a)):
                axis=last-first;fraction=np.clip(np.sum((p-first)*axis,1)/np.maximum(np.sum(axis*axis,1),1e-20),0,1)
                candidates.append(first+fraction[:,None]*axis)
            cloud=np.concatenate(candidates);squared=np.sum((cloud-p)**2,1);index=int(np.argmin(squared))
            results.append(cloud[index]);distances.append(np.sqrt(squared[index]))
        return np.asarray(results),np.asarray(distances)

    def segment_clearance(self,start,end,radius,samples=9):
        points=np.asarray(start)+(np.asarray(end)-start)*np.linspace(0,1,samples)[:,None]
        return float(self.nearest(points)[1].min()-radius)
