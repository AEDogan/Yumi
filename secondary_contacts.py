"""Bounded skinned witnesses for authored springs against the posed body.

This adds contact to existing spring bones; it is not a cloth simulation.
Bind-pose overlap with coarse capsules is retained rather than inflated.
"""
import time
import numpy as np
from contact_physics import capsule_distances, push_out

class SecondaryContacts:
    def __init__(self,springs):
        self.springs=springs;self.samples=[];self.stats={}
        d=springs.data;p=springs.physics;eligible=springs.hair_nodes|springs.cloth_nodes
        # Independent budgets prevent garments consuming all scalp samples.
        for group in (springs.hair_nodes,springs.cloth_nodes):
            group={n for n in group if not set(d.bones.values()).intersection(p.children[n])}
            budget=96
            for part in d.parts:
                if budget<=0:break
                if part.get('skin') is None or 'joints' not in part:continue
                nodes,inverse=d.skins[part['skin']];mapped=nodes[part['joints']]
                weighted=part['weights']*np.isin(mapped,list(group));mass=weighted.sum(1)
                ids=np.intersect1d(np.flatnonzero(mass>.5),np.unique(part['indices']))
                if not len(ids):continue
                owners=mapped[ids,np.argmax(weighted[ids],axis=1)]
                chosen=[]
                for owner in np.unique(owners):
                    subset=ids[owners==owner]
                    chosen.extend(subset[np.linspace(0,len(subset)-1,min(4,len(subset)),dtype=int)])
                ids=np.array(chosen[:budget],int);budget-=len(ids)
                owners=mapped[ids,np.argmax(weighted[ids],axis=1)]
                points=self.skin(d.rest,part,ids)
                radii=np.array([np.minimum(p.radii,capsule_distances(point,p.starts,p.ends)[0]*.98)/np.maximum(p.radii,1e-12) for point in points])
                self.samples.append((part,ids,owners,radii))
        self.children={n:g.get('tipNode',d.nodes[n]['children'][0]) for g,nodes,_ in springs.chains for n in nodes if n in eligible}

    def skin(self,world,part,ids):
        d=self.springs.data;nodes,inverse=d.skins[part['skin']];palette=world[nodes]@inverse
        source=np.c_[part['pos'][ids],np.ones(len(ids))];posed=np.zeros_like(source)
        for k in range(4):posed+=np.einsum('nij,nj->ni',palette[part['joints'][ids,k]],source)*part['weights'][ids,k,None]
        return posed[:,:3]

    def solve(self,world):
        from vrm import aim
        from hand_pose import turn
        started=time.perf_counter();s=self.springs;d=s.data;p=s.physics;p.update(world)
        corrected=set();contacts=0;limited=0;maximum=0.
        environment=getattr(p,'environment',None)
        for part,ids,owners,bind_radii in self.samples:
            points=self.skin(world,part,ids);best={}
            for i,point in enumerate(points):
                # Preserve authored attachment overlap, including scalp roots.
                radii=p.radii*bind_radii[i]
                target,depth=push_out(point,p.starts,p.ends,radii)
                if depth*d.scale<.003:continue
                node=int(owners[i]);maximum=max(maximum,depth*d.scale)
                if node in self.children and (node not in best or depth>best[node][0]):best[node]=(depth,point,target)
            for node in sorted(best,key=lambda n:d.order.index(n)):
                ancestor=node
                while ancestor in d.parents and ancestor not in corrected:ancestor=d.parents[ancestor]
                if ancestor in corrected:continue
                depth,point,target=best[node]
                if environment is not None:
                    canonical=(target@d.flip.T-d.origin)*d.scale
                    root=(world[node,:3,3]@d.flip.T-d.origin)*d.scale
                    canonical=environment.project(canonical[None],root[None])[0]
                    target=d.flip.T@(canonical/d.scale+d.origin)
                old=point-world[node,:3,3];goal=target-world[node,:3,3]
                length=np.linalg.norm(old)
                if length<1e-8 or np.linalg.norm(goal)<1e-8:continue
                neutral=old/length;direction=goal/np.linalg.norm(goal)
                angle=np.arccos(np.clip(neutral@direction,-1,1));maximum_angle=np.radians(12 if node in s.cloth_nodes else 20)
                if angle>maximum_angle:
                    axis=np.cross(neutral,direction);size=np.linalg.norm(axis)
                    if size<1e-8:continue
                    direction=turn(axis/size,maximum_angle)@neutral;limited+=1
                p._rotate_subtree(world,node,aim(old,direction*length));corrected.add(node);contacts+=1
                child=self.children[node];tip=world[child,:3,3].copy();s.states[node]=(tip,tip.copy())
        self.stats={'samples':sum(len(ids) for _,ids,_,_ in self.samples),'contacts':contacts,'limited':limited,'input_max_depth':maximum,'milliseconds':(time.perf_counter()-started)*1000}
