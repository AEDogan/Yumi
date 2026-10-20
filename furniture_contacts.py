"""Surface envelopes of actual prop triangles, shared by CPU validation and GPU.

This final-surface guard supplements bone contacts; it is not a cloth solver.
"""
import numpy as np
from collections import OrderedDict

_SOLID_CACHE=OrderedDict()

class SurfaceField:
    def __init__(self,triangles,axes,direction=1,positive_only=False,size=96):
        self.axes=axes;self.direction=direction;self.texture=None
        triangles=np.asarray(triangles,dtype=float);u,v,h=axes
        if positive_only:
            triangles=triangles[(triangles[:,:,h]*direction).mean(1)>0]
        self.minimum=triangles[:,:, [u,v]].min(axis=(0,1))-.015
        maximum=triangles[:,:, [u,v]].max(axis=(0,1))+.015;self.extent=maximum-self.minimum
        self.values=np.full((size,size),-np.inf);self.size=size
        # Triangle rasterization, not an overall object bounding box. Holes
        # between chair arms and underneath the desk remain open.
        for triangle in triangles:
            a,b,c=triangle;du=b[u]-a[u];dv=b[v]-a[v];eu=c[u]-a[u];ev=c[v]-a[v];det=du*ev-dv*eu
            if abs(det)<1e-10:continue
            low=np.floor((triangle[:,[u,v]].min(0)-self.minimum)/self.extent*size-.5).astype(int)
            high=np.ceil((triangle[:,[u,v]].max(0)-self.minimum)/self.extent*size-.5).astype(int)
            low=np.maximum(0,low);high=np.minimum(size-1,high)
            if np.any(high<low):continue
            x=np.arange(low[0],high[0]+1);y=np.arange(low[1],high[1]+1)
            xx,yy=np.meshgrid(x,y);px=self.minimum[0]+(xx+.5)/size*self.extent[0]-a[u];py=self.minimum[1]+(yy+.5)/size*self.extent[1]-a[v]
            s=(px*ev-py*eu)/det;t=(du*py-dv*px)/det;inside=(s>=-1e-6)&(t>=-1e-6)&(s+t<=1.000001)
            height=(a[h]+s*(b[h]-a[h])+t*(c[h]-a[h]))*direction
            region=self.values[low[1]:high[1]+1,low[0]:high[0]+1]
            np.maximum(region,np.where(inside,height,-np.inf),out=region)
        valid=np.isfinite(self.values);self.values=np.where(valid,self.values*direction,0.)
        self.valid=valid

    def sample(self,points):
        uv=(points[:,list(self.axes[:2])]-self.minimum)/self.extent
        inside=np.all((uv>=0)&(uv<1),axis=1);index=np.clip((uv*self.size).astype(int),0,self.size-1)
        return self.values[index[:,1],index[:,0]],inside&self.valid[index[:,1],index[:,0]]

    def bind(self,unit):
        from OpenGL.GL import glActiveTexture,glGenTextures,glBindTexture,glTexImage2D,glTexParameteri,GL_TEXTURE0,GL_TEXTURE_2D,GL_RGBA32F,GL_RGBA,GL_FLOAT,GL_TEXTURE_MIN_FILTER,GL_TEXTURE_MAG_FILTER,GL_NEAREST,GL_TEXTURE_WRAP_S,GL_TEXTURE_WRAP_T,GL_CLAMP_TO_EDGE
        glActiveTexture(GL_TEXTURE0+unit)
        if self.texture is None:
            self.texture=int(glGenTextures(1));glBindTexture(GL_TEXTURE_2D,self.texture)
            pixels=np.zeros((self.size,self.size,4),dtype='float32');pixels[:,:,0]=self.values;pixels[:,:,1]=self.valid
            glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,self.size,self.size,0,GL_RGBA,GL_FLOAT,pixels)
            for parameter,value in ((GL_TEXTURE_MIN_FILTER,GL_NEAREST),(GL_TEXTURE_MAG_FILTER,GL_NEAREST),(GL_TEXTURE_WRAP_S,GL_CLAMP_TO_EDGE),(GL_TEXTURE_WRAP_T,GL_CLAMP_TO_EDGE)):glTexParameteri(GL_TEXTURE_2D,parameter,value)
        else:glBindTexture(GL_TEXTURE_2D,self.texture)

    def release(self):
        if self.texture is not None:
            from OpenGL.GL import glDeleteTextures
            glDeleteTextures([self.texture]);self.texture=None

class FurnitureContacts:
    names=('seatTop','chairFront','deskTop','deskBack','deskLeft','deskRight')
    def __init__(self,scene):
        self.scene=scene;self.fields=[];self.matrix=np.eye(4);self.inverse=np.eye(4)
        from furniture_scene import rotation
        triangles=[]
        source_triangles=[]
        for p in scene.asset.parts:
            if scene.desk and 'chair' not in p['name'].casefold():continue
            source_triangles.append(p['pos'][p['indices'].reshape(-1,3)])
            points=(p['pos']-scene.fit.pivot)@rotation(-scene.fit.yaw).T*scene.fit.scale
            triangles.append(points[p['indices'].reshape(-1,3)])
        triangles=np.concatenate(triangles);height=scene.fit.height
        from seat_clearance import fit_curve
        self.seat_curve=fit_curve(scene,triangles)
        scene.rig.clearance_curve=self.seat_curve
        # Cache unscaled source geometry so every avatar reuses one proxy.
        from solid_contacts import SolidContacts
        key=(str(scene.asset.path.resolve()),scene.asset.path.stat().st_mtime_ns,bool(scene.desk))
        if key not in _SOLID_CACHE:
            _SOLID_CACHE[key]=SolidContacts(np.concatenate(source_triangles))
            while len(_SOLID_CACHE)>4:_SOLID_CACHE.popitem(last=False)
        self.solids=_SOLID_CACHE[key];_SOLID_CACHE.move_to_end(key)
        self.source_rotation=rotation(scene.fit.yaw)
        self.witnesses=[]
        d=scene.model.data;springs=scene.model.hair_springs
        # Reserve separate budgets: a dress encountered first must not consume
        # every sample and silently disable the scalp's actual mesh contacts.
        for selected_nodes in (springs.hair_nodes,springs.cloth_nodes):
            remaining=96
            for part in d.parts:
                if remaining<=0:break
                if part.get('skin') is None or 'joints' not in part:continue
                nodes=d.skins[part['skin']][0];mapped=nodes[part['joints']]
                weights=part['weights']*np.isin(mapped,list(selected_nodes));mass=weights.sum(axis=1)
                selected=np.intersect1d(np.flatnonzero(mass>.30),np.unique(part['indices']))
                if not len(selected):continue
                dominant=np.argmax(weights[selected],axis=1);owners=mapped[selected,dominant];chosen=[]
                for owner in np.unique(owners):
                    group=selected[owners==owner];chosen.extend(group[np.linspace(0,len(group)-1,min(4,len(group)),dtype=int)])
                chosen=np.asarray(chosen[:remaining],int);remaining-=len(chosen)
                owner=mapped[chosen,np.argmax(weights[chosen],axis=1)]
                self.witnesses.append((part,chosen,owner,weights[chosen].max(axis=1)))
        top=triangles[(triangles[:,:,1].mean(1)>height-.10)&(triangles[:,:,1].mean(1)<height+.10)]
        self.fields=[SurfaceField(top,(0,2,1)),SurfaceField(triangles,(0,1,2))]
        if scene.desk:
            structure=[]
            for name,anchor,scale,target in scene.workstation.placements:
                p=next(p for p in scene.asset.parts if p['name']==name)
                # Peripherals join the top contact surface; panels are restricted
                # to the desk structure so display/keyboard do not close leg room.
                points=(p['pos']@scene.workstation.source_rotation.T-anchor)*scale+target
                if name.casefold().startswith('table_white_wood'):structure.append(points[p['indices'].reshape(-1,3)])
            structure=np.concatenate(structure)
            self.fields.extend([SurfaceField(structure,(0,2,1)),SurfaceField(structure,(0,1,2),-1),SurfaceField(structure,(2,1,0),1,True),SurfaceField(structure,(2,1,0),-1,True)])
        self.update()

    def update(self):
        from furniture_scene import rotation
        s=self.scene;self.matrix[:3,:3]=s.turn.T@rotation(s.current_angle)
        self.matrix[:3,3]=s.turn.T@(s.position-s.origin-np.array([-4*(1-s.visibility),0.,0.]))
        self.inverse=np.linalg.inv(self.matrix)

    def project(self,points,roots):
        p=np.asarray(points)@self.matrix[:3,:3].T+self.matrix[:3,3];root=np.asarray(roots)@self.matrix[:3,:3].T+self.matrix[:3,3]
        margin=.012;seat=self.scene.fit.height
        f=self.scene.fit
        source=(p/f.scale)@self.source_rotation.T+f.pivot
        corrected=self.solids.project(source,margin=.006/f.scale)
        p=(corrected-f.pivot)@self.source_rotation*f.scale
        if len(self.fields)>2 and self.scene.desk_visibility>0:
            shift=np.array([4.,0.,4.])*(1-self.scene.desk_visibility);p-=shift;root-=shift
            table=self.scene.workstation.table_height
            h,valid=self.fields[2].sample(p);mask=valid&(root[:,1]>table-.08)&(p[:,1]<h+margin)
            p[mask,1]=h[mask]+margin
            h,valid=self.fields[3].sample(p);mask=valid&(root[:,2]<h+.04)&(p[:,2]>h-margin)
            p[mask,2]=h[mask]-margin
            for index,sign in ((4,1),(5,-1)):
                h,valid=self.fields[index].sample(p);mask=valid&(root[:,0]*sign<h*sign+.04)&(p[:,0]*sign>h*sign-margin)
                p[mask,0]=h[mask]-sign*margin
            p+=shift
        return p@self.inverse[:3,:3].T+self.inverse[:3,3]

    def bind(self,model):
        from OpenGL.GL import glUniform1i,glUniform1f,glUniform3fv,glUniform4fv,glUniformMatrix4fv,glActiveTexture,GL_TEXTURE0
        self.update();u=model.uniforms
        glUniform1i(u['furnitureEnabled'],1);glUniform1i(u['deskEnabled'],int(self.scene.desk_visibility>0))
        glUniform3fv(u['deskShift'],1,np.array([4.,0.,4.],dtype='float32')*(1-self.scene.desk_visibility))
        glUniform1f(u['seatHeight'],self.scene.fit.height);glUniform1f(u['deskHeight'],self.scene.workstation.table_height if self.scene.desk else 0.)
        glUniformMatrix4fv(u['contactFrame'],1,True,np.asarray(self.matrix,dtype='float32'));glUniformMatrix4fv(u['contactInverse'],1,True,np.asarray(self.inverse,dtype='float32'))
        for i,field in enumerate(self.fields):
            name=self.names[i];field.bind(3+i);glUniform1i(u[name],3+i)
            glUniform4fv(u[name+'Bounds'],1,np.asarray([*field.minimum,*field.extent],dtype='float32'))
        glActiveTexture(GL_TEXTURE0)

    def project_hair(self,points,roots):
        """Keep scalp-attached strands on their root's side of the backrest."""
        p=np.asarray(points)@self.matrix[:3,:3].T+self.matrix[:3,3]
        root=np.asarray(roots)@self.matrix[:3,:3].T+self.matrix[:3,3]
        front,valid=self.fields[1].sample(p)
        mask=valid&(p[:,1]>self.scene.fit.height+.08)&(root[:,2]>front-.025)&(p[:,2]<front+.012)&(p[:,2]>front-.55)
        p[mask,2]=front[mask]+.012
        return p@self.inverse[:3,:3].T+self.inverse[:3,3]

    def solve_springs(self,world,springs,selected_nodes=None):
        """One bounded batch per secondary simulation step; preserve lengths."""
        if self.scene.rig.weight<=0:return
        from vrm import aim
        from hand_pose import turn
        d=springs.data;pairs=[]
        for group,nodes,kind in springs.chains:
            for node in nodes:
                if selected_nodes is None or node in selected_nodes:pairs.append((node,group.get('tipNode',d.nodes[node]['children'][0])))
        if not pairs:return
        order={node:i for i,node in enumerate(d.order)}
        pairs=sorted(dict(pairs).items(),key=lambda pair:order[pair[0]])
        nodes=np.array([a for a,b in pairs]);children=np.array([b for a,b in pairs]);fractions=np.array([.35,.65,1.])
        anchor=world[nodes,:3,3].copy();tip=world[children,:3,3].copy()
        points=(anchor[:,None,:]+(tip-anchor)[:,None,:]*fractions[None,:,None]).reshape(-1,3)
        canonical=(points@d.flip.T-d.origin)*d.scale
        roots=np.repeat((anchor@d.flip.T-d.origin)*d.scale,3,axis=0)
        corrected=self.project(canonical,roots)
        hair=np.repeat(np.isin(nodes,list(springs.hair_nodes)),3)
        if np.any(hair):
            head=(world[d.bones['head'],:3,3]@d.flip.T-d.origin)*d.scale
            corrected[hair]=self.project_hair(corrected[hair],np.repeat(head[None,:],int(hair.sum()),axis=0))
        delta=(corrected-canonical).reshape(-1,3,3)
        self.spring_contacts=0;self.spring_unresolved=0;self.spring_deferred=0;corrected_nodes=set()
        for i,(node,child) in enumerate(pairs):
            sizes=np.linalg.norm(delta[i],axis=1);j=int(sizes.argmax())
            if sizes[j]<.003:continue
            ancestor=d.parents.get(node)
            while ancestor is not None and ancestor not in corrected_nodes:ancestor=d.parents.get(ancestor)
            if ancestor is not None:
                # Batch samples preceded the parent's correction. Applying the
                # child's old displacement now would overcorrect this chain.
                self.spring_deferred+=1;continue
            self.spring_contacts+=1;original=world[child,:3,3]-world[node,:3,3];length=np.linalg.norm(original)
            if length<1e-8:continue
            goal=original+d.flip.T@(delta[i,j]/(d.scale*fractions[j]));goal/=max(float(np.linalg.norm(goal)),1e-8)
            neutral=original/length;angle=np.arccos(np.clip(neutral@goal,-1,1))
            maximum=np.radians(12 if node in springs.cloth_nodes or node in springs.short_hair_nodes else 40)
            if angle>maximum:
                axis=np.cross(neutral,goal);axis/=max(float(np.linalg.norm(axis)),1e-8);goal=turn(axis,maximum)@neutral
                self.spring_unresolved+=1
            springs.physics._rotate_subtree(world,node,aim(original,goal*length))
            corrected_nodes.add(node)
            current=world[child,:3,3].copy();springs.states[node]=(current,current.copy())
        if selected_nodes is None:self.solve_cloth_witnesses(world,springs,dict(pairs))

    def solve_cloth_witnesses(self,world,springs,children):
        """Bounded real cloth vertex samples; rotate authored cloth chains only."""
        from vrm import aim
        from hand_pose import turn
        d=springs.data;best={};self.cloth_witness_contacts=0;self.cloth_witness_limited=0
        for part,ids,owners,influence in self.witnesses:
            nodes,inverse=d.skins[part['skin']];palette=world[nodes]@inverse
            source=np.c_[part['pos'][ids],np.ones(len(ids))];posed=np.zeros_like(source)
            for k in range(4):posed+=np.einsum('nij,nj->ni',palette[part['joints'][ids,k]],source)*part['weights'][ids,k,None]
            canonical=(posed[:,:3]@d.flip.T-d.origin)*d.scale
            corrected=self.project(canonical,canonical)
            hair=np.isin(owners,list(springs.hair_nodes))
            if np.any(hair):
                head=(world[d.bones['head'],:3,3]@d.flip.T-d.origin)*d.scale
                corrected[hair]=self.project_hair(corrected[hair],np.repeat(head[None,:],int(hair.sum()),axis=0))
            delta=corrected-canonical
            for i,size in enumerate(np.linalg.norm(delta,axis=1)):
                node=int(owners[i])
                if size>.003 and node in children and (node not in best or size>best[node][0]):
                    best[node]=(size,posed[i,:3],delta[i]/max(.35,float(influence[i])))
        corrected_nodes=set();self.cloth_witness_deferred=0
        for node in sorted(best,key=lambda n:springs.physics.data.order.index(n)):
            ancestor=d.parents.get(node);defer=False
            while ancestor is not None:
                if ancestor in corrected_nodes:defer=True;break
                ancestor=d.parents.get(ancestor)
            if defer:
                # Parent rotation changed this witness. Re-evaluate its skin
                # next step rather than applying a second stale correction.
                self.cloth_witness_deferred+=1;continue
            size,point,delta=best[node];anchor=world[node,:3,3];old=point-anchor
            goal=old+d.flip.T@(delta/d.scale);length=float(np.linalg.norm(old))
            if length<1e-8:continue
            neutral=old/length;goal/=max(float(np.linalg.norm(goal)),1e-8)
            angle=float(np.arccos(np.clip(neutral@goal,-1,1)));maximum=np.radians(20)*self.scene.rig.weight
            if angle>maximum:
                axis=np.cross(neutral,goal);axis/=max(float(np.linalg.norm(axis)),1e-8)
                goal=turn(axis,maximum)@neutral;self.cloth_witness_limited+=1
            springs.physics._rotate_subtree(world,node,aim(old,goal*length));self.cloth_witness_contacts+=1;corrected_nodes.add(node)
            current=world[children[node],:3,3].copy();springs.states[node]=(current,current.copy())

    def release(self):
        for field in self.fields:field.release()

def contact_roots(data,part):
    """A cloth chain inherits its closest humanoid attachment as safe side."""
    if 'contact_roots' in part:return part['contact_roots']
    result=np.zeros((len(part['pos']),4),dtype='float32')
    if part['skin'] is not None and 'joints' in part:
        nodes,inverse=data.skins[part['skin']];lookup={int(n):i for i,n in enumerate(nodes)};human=set(data.bones.values());mapped=[]
        for index,node in enumerate(nodes):
            node=int(node)
            while node not in human and node in data.parents:node=data.parents[node]
            mapped.append(lookup.get(node,index))
        strongest=part['joints'][np.arange(len(result)),part['weights'].argmax(1)]
        ids=np.asarray(mapped)[strongest];origins=np.linalg.inv(inverse)[:,:3,3]
        result[:,:3]=origins[ids];result[:,3]=ids
    part['contact_roots']=result;return result
