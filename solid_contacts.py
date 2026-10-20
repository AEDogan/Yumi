"""Bounded multi-layer triangle columns for local furniture contact proxies.

Unlike a top envelope, paired crossings leave air under a cushion empty.
Open/overflowing columns are unknown and never used as solid evidence.
"""
import numpy as np

class SolidColumns:
    def __init__(self,triangles,axes,size=64,max_hits=48):
        self.axes=axes;self.size=size;u,v,h=axes;t=np.asarray(triangles,float)
        self.minimum=t[:,:,[u,v]].min(axis=(0,1))-.01
        self.extent=t[:,:,[u,v]].max(axis=(0,1))+.01-self.minimum
        hits=np.full((size*size,max_hits),np.inf,dtype=np.float32);counts=np.zeros(size*size,dtype=np.int32)
        for triangle in t:
            a,b,c=triangle;du=b[u]-a[u];dv=b[v]-a[v];eu=c[u]-a[u];ev=c[v]-a[v];det=du*ev-dv*eu
            if abs(det)<1e-10:continue
            lo=np.maximum(0,np.floor((triangle[:,[u,v]].min(0)-self.minimum)/self.extent*size-.5).astype(int))
            hi=np.minimum(size-1,np.ceil((triangle[:,[u,v]].max(0)-self.minimum)/self.extent*size-.5).astype(int))
            if np.any(hi<lo):continue
            xx,yy=np.meshgrid(np.arange(lo[0],hi[0]+1),np.arange(lo[1],hi[1]+1))
            px=self.minimum[0]+(xx+.5)/size*self.extent[0]-a[u];py=self.minimum[1]+(yy+.5)/size*self.extent[1]-a[v]
            s=(px*ev-py*eu)/det;r=(du*py-dv*px)/det;inside=(s>=-1e-6)&(r>=-1e-6)&(s+r<=1.000001)
            ids=(yy[inside]*size+xx[inside]).ravel();values=(a[h]+s*(b[h]-a[h])+r*(c[h]-a[h]))[inside].ravel()
            slots=counts[ids];valid=slots<max_hits;hits[ids[valid],slots[valid]]=values[valid];counts[ids]+=1
        hits.sort(axis=1);finite=np.isfinite(hits)
        # Shared edges and coplanar triangles describe one crossing.
        gaps=np.zeros_like(hits);np.subtract(hits[:,1:],hits[:,:-1],out=gaps[:,1:],where=finite[:,1:]&finite[:,:-1])
        distinct=finite&np.c_[np.ones(len(hits),bool),gaps[:,1:]>1e-4]
        order=np.cumsum(distinct,axis=1)-1;rows,cols=np.nonzero(distinct)
        layers=np.full_like(hits,np.inf);layers[rows,order[rows,cols]]=hits[rows,cols]
        n=distinct.sum(axis=1);self.valid=(counts<max_hits)&(n>=2)&(n%2==0)
        self.layers=layers

    def query(self,points):
        points=np.asarray(points,float);uv=(points[:,list(self.axes[:2])]-self.minimum)/self.extent
        in_bounds=np.all((uv>=0)&(uv<1),axis=1);index=np.clip((uv*self.size).astype(int),0,self.size-1)
        flat=index[:,1]*self.size+index[:,0];layers=self.layers[flat];height=points[:,self.axes[2]]
        below=(layers<height[:,None]).sum(axis=1);valid=in_bounds&self.valid[flat]
        inside=valid&(below%2==1)
        low=layers[np.arange(len(points)),np.maximum(0,below-1)]
        high=layers[np.arange(len(points)),np.minimum(layers.shape[1]-1,below)]
        return valid,inside,low,high

class SolidContacts:
    def __init__(self,triangles,size=64):
        self.columns=[SolidColumns(triangles,axes,size) for axes in ((0,2,1),(0,1,2),(2,1,0))]

    def project(self,points,margin=.006):
        points=np.asarray(points,float);result=points.copy();valids=[];insides=[];distances=[];targets=[]
        for column in self.columns:
            valid,inside,low,high=column.query(points);axis=column.axes[2];value=points[:,axis]
            choose_low=np.abs(value-low)<np.abs(high-value)
            target=np.where(choose_low,low-margin,high+margin)
            valids.append(valid);insides.append(inside)
            distances.append(np.where(inside,np.abs(target-value),np.inf));targets.append(target)
        valid=np.array(valids);inside=np.array(insides)
        # Require agreement of at least two closed cross-sections. A known
        # outside section vetoes a correction instead of filling an open gap.
        solid=(inside.sum(axis=0)>=2)&~np.any(valid&~inside,axis=0)
        best=np.argmin(distances,axis=0)
        for i,column in enumerate(self.columns):
            selected=solid&(best==i);result[selected,column.axes[2]]=targets[i][selected]
        return result
