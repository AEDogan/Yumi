"""Embedded static glTF props, baked once and cached in a GL display list."""
import json,struct,math,time
from pathlib import Path
import numpy as np
from PySide6.QtGui import QImage
from OpenGL.GL import *
from vrm import VRMData,rotation

class StaticGLB:
    array=VRMData.array
    def __init__(self,path):
        raw=Path(path).read_bytes()
        if len(raw)>40*1024*1024 or len(raw)<20:raise ValueError('Invalid prop size')
        magic,version,length=struct.unpack_from('<III',raw)
        if (magic,version,length)!=(0x46546c67,2,len(raw)):raise ValueError('Invalid GLB')
        self.bin=b'';self.g={};offset=12
        while offset+8<=len(raw):
            size,kind=struct.unpack_from('<II',raw,offset);offset+=8
            if offset+size>len(raw):raise ValueError('Truncated GLB')
            if kind==0x4e4f534a:self.g=json.loads(raw[offset:offset+size])
            elif kind==0x004e4942:self.bin=raw[offset:offset+size]
            offset+=size
        self.parts=[];self.textures={};self.display=None
        def visit(index,parent,seen):
            if index in seen:raise ValueError('Cyclic prop scene')
            node=self.g['nodes'][index]
            if 'matrix' in node:local=np.array(node['matrix']).reshape(4,4).T
            else:
                local=np.eye(4);local[:3,:3]=rotation(node.get('rotation',[0,0,0,1]))@np.diag(node.get('scale',[1,1,1]));local[:3,3]=node.get('translation',[0,0,0])
            world=parent@local
            if 'mesh' in node:
                for primitive in self.g['meshes'][node['mesh']]['primitives']:
                    if primitive.get('mode',4)!=4:continue
                    a=primitive['attributes'];pos=self.array(a['POSITION']);vertices=(np.c_[pos,np.ones(len(pos))]@world.T)[:,:3]
                    indices=self.array(primitive['indices']).ravel().astype('uint32') if 'indices' in primitive else np.arange(len(pos),dtype='uint32')
                    if len(indices)%3 or (len(indices) and indices.max()>=len(pos)):raise ValueError('Invalid triangle indices')
                    if 'NORMAL' in a:normals=self.array(a['NORMAL'])@np.linalg.inv(world[:3,:3])
                    else:
                        normals=np.zeros_like(vertices);tri=indices.reshape(-1,3);face=np.cross(vertices[tri[:,1]]-vertices[tri[:,0]],vertices[tri[:,2]]-vertices[tri[:,0]])
                        for col in range(3):np.add.at(normals,tri[:,col],face)
                    normals/=np.maximum(np.linalg.norm(normals,axis=1,keepdims=True),1e-8)
                    uv=self.array(a['TEXCOORD_0']) if 'TEXCOORD_0' in a else np.zeros((len(pos),2))
                    material=self.g.get('materials',[{}])[primitive.get('material',0)]
                    self.parts.append(dict(pos=np.ascontiguousarray(vertices,dtype='float32'),normal=np.ascontiguousarray(normals,dtype='float32'),uv=np.ascontiguousarray(uv,dtype='float32'),indices=indices,mat=material,name=node.get('name','')))
            for child in node.get('children',[]):visit(child,world,seen|{index})
        for root in self.g['scenes'][self.g.get('scene',0)]['nodes']:visit(root,np.eye(4),set())
        vertices=np.concatenate([p['pos'] for p in self.parts]);self.lo=vertices.min(axis=0);self.hi=vertices.max(axis=0)
        self.origin=np.array([(self.lo[0]+self.hi[0])/2,self.lo[1],(self.lo[2]+self.hi[2])/2])
    def texture(self,index):
        if index in self.textures:return self.textures[index]
        entry=self.g['images'][self.g['textures'][index]['source']]
        if 'bufferView' not in entry:raise ValueError('External prop textures are unsupported')
        view=self.g['bufferViews'][entry['bufferView']];offset=view.get('byteOffset',0)
        img=QImage.fromData(self.bin[offset:offset+view['byteLength']]).convertToFormat(QImage.Format.Format_RGBA8888)
        if img.isNull():raise ValueError('Invalid embedded texture')
        tex=glGenTextures(1);glBindTexture(GL_TEXTURE_2D,tex)
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_LINEAR);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_LINEAR)
        glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA,img.width(),img.height(),0,GL_RGBA,GL_UNSIGNED_BYTE,bytes(img.bits()))
        self.textures[index]=tex;return tex
    def draw(self,height,position,angle=0,channel=None):
        if self.display is None:
            # Upload textures before compiling commands into the display list.
            for part in self.parts:
                tex=part['mat'].get('pbrMetallicRoughness',{}).get('baseColorTexture')
                if tex:self.texture(tex['index'])
            self.display=glGenLists(1);glNewList(self.display,GL_COMPILE)
            glPushAttrib(GL_ALL_ATTRIB_BITS);glPushClientAttrib(GL_CLIENT_VERTEX_ARRAY_BIT)
            glDisable(GL_CULL_FACE);glEnable(GL_NORMALIZE);glBindBuffer(GL_ARRAY_BUFFER,0);glBindBuffer(GL_ELEMENT_ARRAY_BUFFER,0)
            for part in self.parts:
                mat=part['mat'];pbr=mat.get('pbrMetallicRoughness',{});tex=pbr.get('baseColorTexture')
                glColor4f(*getattr(self,'color_factor_override',pbr.get('baseColorFactor',[1,1,1,1])))
                if tex:glEnable(GL_TEXTURE_2D);glBindTexture(GL_TEXTURE_2D,self.textures[tex['index']])
                else:glDisable(GL_TEXTURE_2D)
                glEnableClientState(GL_VERTEX_ARRAY);glEnableClientState(GL_NORMAL_ARRAY);glEnableClientState(GL_TEXTURE_COORD_ARRAY)
                glVertexPointer(3,GL_FLOAT,0,part['pos']);glNormalPointer(GL_FLOAT,0,part['normal']);glTexCoordPointer(2,GL_FLOAT,0,part['uv'])
                glDrawElements(GL_TRIANGLES,len(part['indices']),GL_UNSIGNED_INT,part['indices'])
            glPopClientAttrib();glPopAttrib();glEndList()
        glPushMatrix();glTranslatef(*position);glRotatef(angle,0,1,0)
        scale=height/max(self.hi[1]-self.lo[1],1e-6);glScalef(scale,scale,scale);glTranslatef(*(-self.origin));glCallList(self.display)
        if channel is not None:
            glPushAttrib(GL_ALL_ATTRIB_BITS);glDisable(GL_LIGHTING);glDisable(GL_CULL_FACE);glDisable(GL_TEXTURE_2D)
            for part in self.parts:
                if part['mat'].get('name','').casefold()!='screen':continue
                lo=part['pos'].min(axis=0);hi=part['pos'].max(axis=0);z=hi[2]+.4
                glColor3f(.025,.025,.035)
                glBegin(GL_QUADS)
                for x,y in ((lo[0],lo[1]),(hi[0],lo[1]),(hi[0],hi[1]),(lo[0],hi[1])):glVertex3f(x,y,z)
                glEnd()
                if getattr(self,'screen_ready',False):
                    glEnable(GL_TEXTURE_2D);glBindTexture(GL_TEXTURE_2D,self.screen_texture);glColor3f(1,1,1)
                    center=(lo+hi)*.5;width=hi[0]-lo[0];height=hi[1]-lo[1]
                    if width/height>self.screen_aspect:width=height*self.screen_aspect
                    else:height=width/self.screen_aspect
                    lo=lo.copy();hi=hi.copy();lo[0]=center[0]-width*.5;hi[0]=center[0]+width*.5;lo[1]=center[1]-height*.5;hi[1]=center[1]+height*.5;z+=.1
                glBegin(GL_QUADS)
                for x,y,u,v in ((lo[0],lo[1],0,1),(hi[0],lo[1],1,1),(hi[0],hi[1],1,0),(lo[0],hi[1],0,0)):
                    glTexCoord2f(u,v);glVertex3f(x,y,z)
                glEnd()
            glPopAttrib()
        glPopMatrix()

    def set_screen_frame(self,image,revision):
        if getattr(self,'screen_revision',None)==revision:return
        self.screen_revision=revision;self.screen_ready=image is not None and not image.isNull()
        if not self.screen_ready:return
        self.screen_aspect=image.width()/max(image.height(),1)
        glPushAttrib(GL_TEXTURE_BIT)
        if not hasattr(self,'screen_texture'):self.screen_texture=glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D,self.screen_texture)
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_LINEAR);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_EDGE);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_CLAMP_TO_EDGE)
        glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA,image.width(),image.height(),0,GL_RGBA,GL_UNSIGNED_BYTE,bytes(image.bits()))
        glPopAttrib()
