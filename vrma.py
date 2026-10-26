"""VRM Animation 1.0 GLB loader, quaternion interpolation and T-pose retargeting."""
import json,struct,math
from weakref import WeakKeyDictionary
from pathlib import Path
import numpy as np
from vrm import VRMData,rotation

def slerp(a,b,u):
    a=a/max(np.linalg.norm(a),1e-9);b=b/max(np.linalg.norm(b),1e-9);dot=float(a@b)
    if dot<0:b=-b;dot=-dot
    if dot>.9995:q=a*(1-u)+b*u;return q/max(np.linalg.norm(q),1e-9)
    angle=math.acos(max(-1,min(1,dot)));return (a*math.sin((1-u)*angle)+b*math.sin(u*angle))/math.sin(angle)

class MotionClip:
    def __init__(self,path):
        self.path=Path(path);raw=self.path.read_bytes()
        if len(raw)<20 or len(raw)>100*1024*1024:raise ValueError('Animasyon dosyası boyutu geçersiz.')
        magic,version,size=struct.unpack_from('<III',raw)
        if magic!=0x46546c67 or version!=2 or size!=len(raw):raise ValueError('Geçerli bir VRMA / GLB 2 dosyası değil.')
        offset=12;self.bin=b'';self.g=None
        while offset+8<=len(raw):
            size,kind=struct.unpack_from('<II',raw,offset);offset+=8
            if offset+size>len(raw):raise ValueError('Animasyon veri bloğu eksik.')
            if kind==0x4e4f534a:self.g=json.loads(raw[offset:offset+size])
            elif kind==0x004e4942:self.bin=raw[offset:offset+size]
            offset+=size
        if not self.g:raise ValueError('VRMA JSON bulunamadı.')
        ext=self.g.get('extensions',{}).get('VRMC_vrm_animation')
        if not ext or ext.get('specVersion') not in ('1.0','1.0-draft'):raise ValueError('VRM Animation bilgisi bulunamadı.')
        self.bones={name:v['node'] for name,v in ext.get('humanoid',{}).get('humanBones',{}).items()}
        if 'hips' not in self.bones:raise ValueError('Animasyonda hips kemiği yok.')
        self.nodes=self.g.get('nodes',[]);self.parents={};self.order=[]
        if len(self.nodes)>512:raise ValueError('Animasyon iskeleti çok büyük.')
        for i,n in enumerate(self.nodes):
            for child in n.get('children',[]):self.parents[child]=i
        def visit(i,seen):
            if i in seen:raise ValueError('Animasyon iskeletinde döngü var.')
            self.order.append(i)
            for child in self.nodes[i].get('children',[]):visit(child,seen|{i})
        for i in range(len(self.nodes)):
            if i not in self.parents:visit(i,set())
        self.local=[];self.world=np.tile(np.eye(4),(len(self.nodes),1,1))
        for n in self.nodes:
            m=np.eye(4);m[:3,:3]=rotation(n.get('rotation',[0,0,0,1]));m[:3,3]=n.get('translation',[0,0,0]);self.local.append(m)
        for i in self.order:self.world[i]=self.world[self.parents[i]]@self.local[i] if i in self.parents else self.local[i]
        animation=self.g.get('animations',[{}])[0];self.channels=[];self.duration=0.
        self.expressions={v['node']:name for group in ext.get('expressions',{}).values() for name,v in group.items()}
        for channel in animation.get('channels',[]):
            sampler=animation['samplers'][channel['sampler']];times=VRMData.array(self,sampler['input']).ravel();values=VRMData.array(self,sampler['output']);mode=sampler.get('interpolation','LINEAR');target=channel['target']
            if not len(times) or np.any(np.diff(times)<0) or not np.isfinite(times).all() or not np.isfinite(values).all():raise ValueError('Animasyon anahtarları geçersiz.')
            if mode not in ('LINEAR','STEP','CUBICSPLINE'):raise ValueError('Desteklenmeyen animasyon geçişi.')
            if len(values)!=len(times)*(3 if mode=='CUBICSPLINE' else 1):raise ValueError('Animasyon anahtar sayısı uyuşmuyor.')
            self.channels.append((target['node'],target['path'],times,values,mode));self.duration=max(self.duration,float(times[-1]))
        if not self.channels:raise ValueError('Animasyonda hareket kanalı yok.')
        self.retarget_cache=WeakKeyDictionary()
    def pose(self,t,target,loop=True):
        t=t%max(self.duration,1e-5) if loop else max(0.,min(t,max(0.,self.duration-1e-5)));local=[m.copy() for m in self.local];expression={}
        for node,path,times,values,mode in self.channels:
            i=max(0,min(len(times)-1,int(np.searchsorted(times,t,side='right')-1)));k=min(i+1,len(times)-1);dt=float(times[k]-times[i]);u=0 if dt<=0 else max(0,min(1,(t-times[i])/dt))
            if mode=='STEP':value=values[i]
            elif mode=='CUBICSPLINE':
                p0=values[3*i+1];p1=values[3*k+1];m0=values[3*i+2]*dt;m1=values[3*k]*dt
                value=(2*u**3-3*u**2+1)*p0+(u**3-2*u**2+u)*m0+(-2*u**3+3*u**2)*p1+(u**3-u**2)*m1
            elif path=='rotation':value=slerp(values[i],values[k],u)
            else:value=values[i]*(1-u)+values[k]*u
            if path=='rotation':local[node][:3,:3]=rotation(value)
            elif path=='translation':local[node][:3,3]=value
            if node in self.expressions and path=='translation':expression[self.expressions[node]]=float(np.clip(value[0],0,1))
        cached=self.retarget_cache.get(target)
        if cached is None:
            from motion_reference import reference_pose
            reference_local,reference_world=reference_pose(self,target)
            cached=[]
            for name,source in self.bones.items():
                # VRM 1 thumb names map to VRM 0's differently named joints.
                dest_name=name
                if target.legacy and 'Thumb' in name:dest_name=name.replace('Metacarpal','Proximal').replace('ThumbProximal','ThumbIntermediate') if 'Metacarpal' not in name else name.replace('Metacarpal','Proximal')
                if dest_name not in target.bones:continue
                dest=target.bones[dest_name];w=self.world[source,:3,:3];l=self.local[source][:3,:3]
                dw=reference_world[dest,:3,:3];dl=reference_local[dest][:3,:3]
                left=dl@np.linalg.inv(dw)@target.flip.T@w@np.linalg.inv(l)
                right=np.linalg.inv(w)@target.flip@dw
                cached.append((source,dest,left,right))
            self.retarget_cache[target]=cached
        rotations={dest:left@local[source][:3,:3]@right for source,dest,left,right in cached}
        source=self.bones['hips'];dest=target.bones['hips'];source_height=max(.001,self.world[source,1,3]);dest_height=(target.rest[dest,:3,3]@target.flip.T-target.origin)[1]
        parent=self.parents.get(source);parent_rotation=self.world[parent,:3,:3] if parent is not None else np.eye(3)
        translation=parent_rotation@(local[source][:3,3]-self.local[source][:3,3])*dest_height/source_height
        return rotations,target.flip.T@translation,expression

def library():
    folder=Path(__file__).parent/'motions';folder.mkdir(exist_ok=True)
    return sorted(folder.glob('*.vrma'))

def import_clip(path):
    import shutil
    clip=MotionClip(path);folder=Path(__file__).parent/'motions';folder.mkdir(exist_ok=True);dest=folder/Path(path).name
    if Path(path).resolve()!=dest.resolve():shutil.copy2(path,dest)
    return dest
