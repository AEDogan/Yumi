"""Embedded static glTF props, separate from the humanoid VRM character library."""
import json,struct
from pathlib import Path
import numpy as np
from vrm import VRMData,rotation
from PySide6.QtGui import QImage
from OpenGL.GL import *

LIBRARY=Path(__file__).resolve().parent/'items'

class ItemAsset:
    array=VRMData.array
    def __init__(self,path):
        self.path=Path(path);raw=self.path.read_bytes();self.g=None;self.bin=b'';self.parts=[];self.textures={}
        if len(raw)<20 or len(raw)>150*1024**2:raise ValueError('Eşya dosyası boyutu uygun değil.')
        magic,version,size=struct.unpack_from('<III',raw)
        if magic!=0x46546c67 or version!=2 or size!=len(raw):raise ValueError('Geçersiz GLB eşya.')
        offset=12
        while offset+8<=len(raw):
            size,kind=struct.unpack_from('<II',raw,offset);offset+=8
            if offset+size>len(raw):raise ValueError('Eksik eşya verisi.')
            if kind==0x4e4f534a:self.g=json.loads(raw[offset:offset+size])
            if kind==0x004e4942:self.bin=raw[offset:offset+size]
            offset+=size
        if not self.g:raise ValueError('Eşya JSON verisi yok.')
        nodes=self.g.get('nodes',[]);parents={};world={};visiting=set()
        for i,node in enumerate(nodes):
            for child in node.get('children',[]):parents[child]=i
        def transform(i):
            if i in world:return world[i]
            if i in visiting or not 0<=i<len(nodes):raise ValueError('Geçersiz eşya hiyerarşisi.')
            visiting.add(i);n=nodes[i]
            if 'matrix' in n:m=np.array(n['matrix'],float).reshape(4,4).T
            else:
                m=np.eye(4);m[:3,:3]=rotation(n.get('rotation',[0,0,0,1]))@np.diag(n.get('scale',[1,1,1]));m[:3,3]=n.get('translation',[0,0,0])
            world[i]=transform(parents[i])@m if i in parents else m;visiting.remove(i)
            if not np.isfinite(world[i]).all():raise ValueError('Geçersiz eşya dönüşümü.')
            return world[i]
        for i in range(len(nodes)):transform(i)
        self.node_world=world;self.node_parents=parents;self.node_order=list(world)
        self.node_inverse={i:np.linalg.inv(m) for i,m in world.items()}
        self.animation_cache={};self.animation_channels=[];self.animation_duration=0.
        for animation in self.g.get('animations',[])[:1]:
            for channel in animation.get('channels',[]):
                sampler=animation['samplers'][channel['sampler']];target=channel['target']
                if target['path'] not in ('translation','rotation','scale'):continue
                times=self.array(sampler['input']).ravel();values=self.array(sampler['output'])
                mode=sampler.get('interpolation','LINEAR')
                if not len(times) or mode not in ('LINEAR','STEP','CUBICSPLINE'):continue
                if not 0<=target['node']<len(nodes) or len(values)!=len(times)*(3 if mode=='CUBICSPLINE' else 1):raise ValueError('Geçersiz eşya animasyon kanalı.')
                if not np.isfinite(times).all() or not np.isfinite(values).all() or np.any(np.diff(times)<0):raise ValueError('Geçersiz eşya animasyonu.')
                self.animation_channels.append((target['node'],target['path'],times,values,mode))
                self.animation_duration=max(self.animation_duration,float(times[-1]))
        active=set()
        def visit(i):
            if i in active:return
            active.add(i)
            for child in nodes[i].get('children',[]):visit(child)
        scene=self.g.get('scenes',[{'nodes':[i for i in range(len(nodes)) if i not in parents]}])[self.g.get('scene',0)]
        for i in scene.get('nodes',[]):visit(i)
        for i in sorted(active):
            node=nodes[i]
            if 'mesh' not in node:continue
            mesh=self.g['meshes'][node['mesh']]
            for primitive in mesh.get('primitives',[]):
                if primitive.get('mode',4)!=4:continue
                a=primitive['attributes'];pos=self.array(a['POSITION']).astype(float);normal=self.array(a['NORMAL']).astype(float) if 'NORMAL' in a else np.tile([0,1,0.],(len(pos),1))
                if 'skin' in node and 'JOINTS_0' in a:
                    skin=self.g['skins'][node['skin']];joints=np.array(skin['joints'],int)
                    inverse=self.array(skin['inverseBindMatrices']).reshape((-1,4,4)).transpose(0,2,1) if 'inverseBindMatrices' in skin else np.tile(np.eye(4),(len(joints),1,1))
                    palette=np.array([world[int(j)] for j in joints])@inverse;ids=self.array(a['JOINTS_0']).astype(int);weights=self.array(a['WEIGHTS_0']).astype(float);weights/=np.maximum(weights.sum(axis=1)[:,None],1e-10)
                    p=np.column_stack((pos,np.ones(len(pos))));posed=np.zeros_like(p);norm=np.zeros_like(normal)
                    for k in range(4):
                        posed+=np.einsum('nij,nj->ni',palette[ids[:,k]],p)*weights[:,k,None]
                        norm+=np.einsum('nij,nj->ni',palette[ids[:,k],:3,:3],normal)*weights[:,k,None]
                    pos=posed[:,:3];normal=norm
                else:
                    pos=(np.column_stack((pos,np.ones(len(pos))))@world[i].T)[:,:3];normal=normal@np.linalg.inv(world[i][:3,:3])
                normal/=np.maximum(np.linalg.norm(normal,axis=1)[:,None],1e-10)
                indices=self.array(primitive['indices']).astype('uint32').ravel() if 'indices' in primitive else np.arange(len(pos),dtype='uint32')
                if len(indices) and indices.max()>=len(pos):raise ValueError('Geçersiz eşya üçgeni.')
                part={'name':node.get('name',mesh.get('name','')),'pos':np.ascontiguousarray(pos,dtype='float32'),'normal':np.ascontiguousarray(normal,dtype='float32'),'uv':np.ascontiguousarray(self.array(a['TEXCOORD_0']) if 'TEXCOORD_0' in a else np.zeros((len(pos),2)),dtype='float32'),'indices':indices,'material':primitive.get('material',0)}
                part.update(node=i,mesh=node['mesh'],skin=None)
                self.parts.append(part)
        if not self.parts:raise ValueError('Eşya görünür üçgen içermiyor.')
        points=np.concatenate([p['pos'] for p in self.parts]);self.minimum=points.min(axis=0);self.maximum=points.max(axis=0);self.extent=self.maximum-self.minimum
        self.triangles=sum(len(p['indices'])//3 for p in self.parts)
        if self.triangles>200000:raise ValueError('Eşya çalışma zamanı bütçesini aşıyor; önce sadeleştirilmeli.')
        import hashlib
        from model_analysis import analyze_prop
        self.analysis=analyze_prop(self,hashlib.sha256(raw).hexdigest())
    def texture(self,index):
        if index in self.textures:return self.textures[index]
        image=self.g['images'][self.g['textures'][index]['source']]
        if 'bufferView' not in image:raise ValueError('Yalnız gömülü eşya dokuları destekleniyor.')
        view=self.g['bufferViews'][image['bufferView']];start=view.get('byteOffset',0);q=QImage.fromData(self.bin[start:start+view['byteLength']])
        if q.isNull():raise ValueError('Eşya dokusu okunamadı.')
        if max(q.width(),q.height())>2048:q=q.scaled(2048,2048,aspectMode=__import__('PySide6.QtCore',fromlist=['Qt']).Qt.AspectRatioMode.KeepAspectRatio)
        q=q.convertToFormat(QImage.Format.Format_RGBA8888);tex=int(glGenTextures(1));glBindTexture(GL_TEXTURE_2D,tex);glPixelStorei(GL_UNPACK_ALIGNMENT,1)
        glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA,q.width(),q.height(),0,GL_RGBA,GL_UNSIGNED_BYTE,bytes(q.bits()));glGenerateMipmap(GL_TEXTURE_2D)
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_LINEAR_MIPMAP_LINEAR);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_REPEAT);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_REPEAT);self.textures[index]=tex;return tex
    def animation_matrices(self,t):
        if not self.animation_channels:return {}
        tick=round(max(0.,min(float(t),self.animation_duration))*30)
        if tick in self.animation_cache:return self.animation_cache[tick]
        from vrma import slerp
        nodes=self.g.get('nodes',[]);changes={};clock=tick/30
        for node,path,times,values,mode in self.animation_channels:
            i=max(0,min(len(times)-1,int(np.searchsorted(times,clock,side='right')-1)));k=min(i+1,len(times)-1)
            dt=float(times[k]-times[i]);u=0. if dt<=0 else float(np.clip((clock-times[i])/dt,0.,1.))
            if mode=='STEP':value=values[i]
            elif mode=='CUBICSPLINE':
                value=(2*u**3-3*u*u+1)*values[3*i+1]+(u**3-2*u*u+u)*dt*values[3*i+2]+(-2*u**3+3*u*u)*values[3*k+1]+(u**3-u*u)*dt*values[3*k]
            elif path=='rotation':value=slerp(values[i],values[k],u)
            else:value=values[i]*(1-u)+values[k]*u
            changes.setdefault(node,{})[path]=value
        world={}
        for node in self.node_order:
            n=nodes[node];c=changes.get(node,{})
            if 'matrix' in n and not c:local=np.array(n['matrix']).reshape(4,4).T
            else:
                local=np.eye(4);local[:3,:3]=rotation(c.get('rotation',n.get('rotation',[0,0,0,1])))@np.diag(c.get('scale',n.get('scale',[1,1,1])))
                local[:3,3]=c.get('translation',n.get('translation',[0,0,0]))
            world[node]=world[self.node_parents[node]]@local if node in self.node_parents else local
        result={p['node']:world[p['node']]@self.node_inverse[p['node']] for p in self.parts}
        if len(self.animation_cache)>8:self.animation_cache.clear()
        self.animation_cache[tick]=result;return result

    def draw(self,exclude=(),include=(),placements=None,animation_time=None,opacity=1.):
        opacity=float(np.clip(opacity,0.,1.))
        if opacity<=.001:return
        from desktop_vrm import PROP_SINK
        sink=PROP_SINK.get()
        if sink is not None:
            sink.capture(self,exclude,include,placements,animation_time,opacity);return
        glPushAttrib(GL_ALL_ATTRIB_BITS);glUseProgram(0);glActiveTexture(GL_TEXTURE0)
        glEnable(GL_LIGHTING);glEnable(GL_NORMALIZE);glEnableClientState(GL_VERTEX_ARRAY);glEnableClientState(GL_NORMAL_ARRAY);glEnableClientState(GL_TEXTURE_COORD_ARRAY)
        matrix_pushed=False
        animation=self.animation_matrices(animation_time) if animation_time is not None else {}
        try:
            for part in self.parts:
                if any(word.casefold() in part['name'].casefold() for word in exclude):continue
                if include and not any(word.casefold() in part['name'].casefold() for word in include):continue
                if placements is not None:
                    if part['name'] not in placements:continue
                    anchor,scale,target,yaw=placements[part['name']]
                    glPushMatrix();matrix_pushed=True;glTranslatef(*target);glScalef(*scale);glTranslatef(*(-anchor));glRotatef(yaw,0,1,0)
                if part.get('node') in animation:
                    if not matrix_pushed:glPushMatrix();matrix_pushed=True
                    glMultMatrixd(np.ascontiguousarray(animation[part['node']].T))
                materials=self.g.get('materials',[]);mat=materials[part['material']] if materials else {};pbr=mat.get('pbrMetallicRoughness',{})
                rgba=pbr.get('baseColorFactor',[1,1,1,1]);texture=pbr.get('baseColorTexture',{}).get('index')
                # A black PBR material still has dielectric highlights. The
                # compatibility renderer needs that specular term explicitly.
                metallic=pbr.get('metallicFactor',1.);roughness=pbr.get('roughnessFactor',.6)
                glColor4f(*[max(.055,float(c)) for c in rgba[:3]],rgba[3]*opacity)
                glMaterialfv(GL_FRONT_AND_BACK,GL_SPECULAR,[.04*(1-metallic)+float(c)*metallic for c in rgba[:3]]+[1.])
                glMaterialf(GL_FRONT_AND_BACK,GL_SHININESS,max(4.,min(96.,2/(roughness**4+.0001)-2)))
                if texture is None:glDisable(GL_TEXTURE_2D)
                else:glEnable(GL_TEXTURE_2D);glBindTexture(GL_TEXTURE_2D,self.texture(texture));glTexEnvi(GL_TEXTURE_ENV,GL_TEXTURE_ENV_MODE,GL_MODULATE)
                if mat.get('doubleSided'):glDisable(GL_CULL_FACE)
                else:glEnable(GL_CULL_FACE);glCullFace(GL_BACK)
                mode=mat.get('alphaMode','OPAQUE');glEnable(GL_ALPHA_TEST);glAlphaFunc(GL_GREATER,mat.get('alphaCutoff',.5) if mode=='MASK' else .02)
                if mode=='BLEND' or opacity<.999:glEnable(GL_BLEND);glBlendFunc(GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA);glDepthMask(GL_FALSE)
                else:glDisable(GL_BLEND);glDepthMask(GL_TRUE)
                glVertexPointer(3,GL_FLOAT,0,part['pos']);glNormalPointer(GL_FLOAT,0,part['normal']);glTexCoordPointer(2,GL_FLOAT,0,part['uv']);glDrawElements(GL_TRIANGLES,len(part['indices']),GL_UNSIGNED_INT,part['indices'])
                if matrix_pushed:glPopMatrix();matrix_pushed=False
        finally:
            if matrix_pushed:glPopMatrix()
            glDisableClientState(GL_VERTEX_ARRAY);glDisableClientState(GL_NORMAL_ARRAY);glDisableClientState(GL_TEXTURE_COORD_ARRAY);glPopAttrib()
    def release(self):
        if self.textures:glDeleteTextures(list(self.textures.values()));self.textures.clear()

def manifest():
    path=LIBRARY/'manifest.json'
    if not path.exists():return {'version':1,'items':[]}
    return json.loads(path.read_text(encoding='utf-8'))
