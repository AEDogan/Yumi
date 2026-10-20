"""Simulate authored VRM0/VRM1 secondary chains, including anime accessories."""
import numpy as np
import math
import logging,os,weakref
from contact_physics import push_out

def quaternion_batch(m):
    """Rotation matrices to normalized quaternions without per-joint Python calls."""
    q=np.empty((len(m),4));trace=np.trace(m,axis1=1,axis2=2);positive=trace>0
    if np.any(positive):
        a=m[positive];s=np.sqrt(trace[positive]+1)*2
        q[positive]=np.column_stack(((a[:,2,1]-a[:,1,2])/s,(a[:,0,2]-a[:,2,0])/s,(a[:,1,0]-a[:,0,1])/s,s/4))
    largest=np.argmax(np.diagonal(m,axis1=1,axis2=2),axis=1)
    for i in range(3):
        mask=(~positive)&(largest==i)
        if not np.any(mask):continue
        a=m[mask];j=(i+1)%3;k=(i+2)%3;s=np.sqrt(np.maximum(1e-12,1+a[:,i,i]-a[:,j,j]-a[:,k,k]))*2
        value=np.empty((len(a),4));value[:,i]=s/4;value[:,3]=(a[:,k,j]-a[:,j,k])/s;value[:,j]=(a[:,j,i]+a[:,i,j])/s;value[:,k]=(a[:,k,i]+a[:,i,k])/s;q[mask]=value
    return q/np.maximum(np.linalg.norm(q,axis=1)[:,None],1e-10)

class HairSprings:
    def __init__(self,data):
        self.data=data;self.states={};self.last=None;self.chains=[];self.external_velocity=np.zeros(3);self.centers={}
        self.simulation_hz=60.;self.step_clock=None;self.offset_previous=None;self.offset_current=None
        secondary=data.vrm.get('secondaryAnimation',{}) if data.legacy else {}
        if not data.legacy:
            extension=data.g.get('extensions',{}).get('VRMC_springBone',{})
            collider_groups=[]
            for collider in extension.get('colliders',[]):
                shape=collider.get('shape',{});sphere=shape.get('sphere',shape.get('capsule',{}))
                item={'offset':dict(zip('xyz',sphere.get('offset',[0,0,0]))),'radius':sphere.get('radius',0)}
                if 'tail' in sphere:item['tail']=dict(zip('xyz',sphere['tail']))
                collider_groups.append({'node':collider['node'],'colliders':[item]})
            groups=[]
            for spring in extension.get('springs',[]):
                indices=[index for ci in spring.get('colliderGroups',[]) for index in extension.get('colliderGroups',[])[ci].get('colliders',[])]
                joints=spring.get('joints',[])
                for joint,tip in zip(joints,joints[1:]):
                    groups.append({'comment':spring.get('name',''),'bones':[joint['node']],'tipNode':tip['node'],
                        'stiffiness':joint.get('stiffness',1.),'dragForce':joint.get('dragForce',.5),
                        'gravityDir':dict(zip('xyz',joint.get('gravityDir',[0,-1,0]))),'gravityPower':joint.get('gravityPower',0),
                        'hitRadius':joint.get('hitRadius',0),'colliderGroups':indices,'center':spring.get('center',-1)})
            secondary={'boneGroups':groups,'colliderGroups':collider_groups}
        self.colliders=secondary.get('colliderGroups',[])
        from contact_physics import AutoPhysicsRig
        self.physics=AutoPhysicsRig(data)
        assigned=set()
        for group in secondary.get('boneGroups',[]):
            kind=group.get('comment','').lower()
            root_names=' '.join(data.nodes[n].get('name','').lower() for n in group.get('bones',[]) if 0<=n<len(data.nodes))
            if any(word in kind+' '+root_names for word in ('tail','shippo','尻尾','しっぽ','kuyruk')):kind='tail'
            # Physics declarations define flexible parts; names are never an allowlist.
            nodes=[]
            def visit(node):
                if not 0<=node<len(data.nodes):return
                if node in data.bones.values():return
                if node not in assigned and data.nodes[node].get('children'):
                    nodes.append(node);assigned.add(node)
                if 'tipNode' in group:return
                for child in data.nodes[node].get('children',[]):visit(child)
            for root in group.get('bones',[]):visit(root)
            self.chains.append((group,nodes,kind))
        # Identify authored flexible scalp chains from their humanoid ancestry.
        # Short hair needs less lag than shoulder-length flexible strands.
        head=data.bones.get('head');scalp=[];lengths=[]
        for group,nodes,kind in self.chains:
            if not nodes:continue
            ancestor=nodes[0];attached=False
            while ancestor in data.parents:
                ancestor=data.parents[ancestor]
                if ancestor==head:attached=True;break
            if not attached:continue
            # Generic imported material names (material_0, etc.) do not identify
            # hair. Authored flexible chains attached to the head still need
            # scalp collision/damping, including flexible hat accessories.
            length=sum(np.linalg.norm(data.rest[group.get('tipNode',data.nodes[n]['children'][0]),:3,3]-data.rest[n,:3,3])*data.scale for n in nodes)
            scalp.extend(nodes);lengths.append(length)
        self.hair_nodes=set(scalp)
        self.short_hair_nodes=set(scalp) if lengths and float(np.median(lengths))<.17 else set()
        self.cloth_nodes=set()
        for group,nodes,kind in self.chains:
            # Authored flexible chains attached below the head share the cloth
            # stability profile. Cape/ribbon names vary across imported rigs;
            # fitting must follow the humanoid attachment, not a file allowlist.
            if not nodes or kind=='tail':continue
            ancestor=nodes[0]
            humanoid=set(data.bones.values())
            while ancestor in data.parents and ancestor not in humanoid:
                ancestor=data.parents[ancestor]
            if ancestor in humanoid and ancestor!=head:self.cloth_nodes.update(nodes)
        self.descendants={}
        def collect(node):
            result=[]
            for child in data.nodes[node].get('children',[]):
                if child in data.bones.values():continue
                result.append((node,child));result.extend(collect(child))
            return result
        for group,nodes,_ in self.chains:
            for node in nodes:
                self.descendants[node]=collect(node)
                self.physics.prepare_tip(node,group.get('tipNode',data.nodes[node]['children'][0]))
        selected={n for _,nodes,_ in self.chains for n in nodes}
        self.simulated_nodes=[n for n in data.order if n in selected]
        self.simulated_indices=np.array(self.simulated_nodes,int)
        self.simulated_parents=np.array([data.parents.get(n,-1) for n in self.simulated_nodes],int)
        self.rest_inverse=np.linalg.inv(np.array([data.local[n][:3,:3] for n in self.simulated_nodes])) if selected else np.empty((0,3,3))
        affected=selected|{child for n in self.simulated_nodes for _,child in self.descendants[n]}
        self.affected=[n for n in data.order if n in affected]
        self.cache_slots={n:i for i,n in enumerate(self.simulated_nodes)}
        self.backend='legacy' if os.environ.get('YUMI_VRM_RUNTIME')=='legacy' else 'three-vrm'
        self.runtime=None;self.runtime_error=None;self.runtime_attempted=False
    def apply(self,t,world):
        if self.backend=='three-vrm':
            self._apply_runtime(t,world);return
        if self.simulation_hz<=0:return self._simulate(t,world)
        interval=1./self.simulation_hz
        reset=self.step_clock is None or t<self.step_clock or t-self.step_clock>.15
        if reset or t-self.step_clock+1e-9>=interval:
            self._simulate(t,world)
            parents=world[np.maximum(self.simulated_parents,0),:3,:3].copy();parents[self.simulated_parents<0]=np.eye(3)
            after=np.linalg.solve(parents,world[self.simulated_indices,:3,:3])
            current=quaternion_batch(self.rest_inverse@after)
            previous=current.copy() if reset or self.offset_current is None else self.offset_current.copy()
            current[np.sum(previous*current,axis=1)<0]*=-1
            self.offset_previous=previous;self.offset_current=current;self.step_clock=t
        if self.offset_current is None or not len(self.simulated_nodes):return
        u=max(0.,min(1.,(t-self.step_clock)/interval))
        q=self.offset_previous*(1-u)+self.offset_current*u;q/=np.maximum(np.linalg.norm(q,axis=1)[:,None],1e-10)
        x,y,z,w=q.T;rotations=np.empty((len(q),3,3))
        rotations[:,0,0]=1-2*(y*y+z*z);rotations[:,0,1]=2*(x*y-z*w);rotations[:,0,2]=2*(x*z+y*w)
        rotations[:,1,0]=2*(x*y+z*w);rotations[:,1,1]=1-2*(x*x+z*z);rotations[:,1,2]=2*(y*z-x*w)
        rotations[:,2,0]=2*(x*z-y*w);rotations[:,2,1]=2*(y*z+x*w);rotations[:,2,2]=1-2*(x*x+y*y)
        # Every secondary joint has an authored bind local transform. Rebuild
        # each affected descendant once rather than rotating overlapping
        # subtrees and inverting a matrix for every joint on every render.
        for n in self.affected:
            local=self.data.local[n]
            if n in self.cache_slots:
                local=local.copy();local[:3,:3]=local[:3,:3]@rotations[self.cache_slots[n]]
            parent=self.data.parents.get(n)
            world[n]=world[parent]@local if parent is not None else local

    def _apply_runtime(self,t,world):
        if self.runtime_error:return
        try:
            if not self.runtime_attempted:
                self.runtime_attempted=True
                from three_vrm_runtime import ThreeVRMSprings
                self.runtime=ThreeVRMSprings(self.data)
                self.runtime_finalizer=weakref.finalize(self,self.runtime.close)
            self.runtime.apply(t,world)
            environment=getattr(self.physics,'environment',None)
            if environment is not None:environment.solve_springs(world,self)
        except (RuntimeError,OSError,ValueError) as error:
            self.runtime_error=str(error)
            logging.getLogger(__name__).exception('three-vrm secondary physics unavailable; authored skinning retained')
            if self.runtime:self.runtime.close()

    def close(self):
        if self.runtime:self.runtime.close();self.runtime=None

    def _simulate(self,t,world):
        from vrm import aim
        dt=1/30 if self.last is None else max(.001,min(.05,t-self.last));reset=self.last is None or t<self.last or t-self.last>.15;self.last=t
        d=self.data
        self.physics.update(world)
        cloth_frames={node:world[node,:3,:3].copy() for node in self.cloth_nodes}
        # A center is shared by many chains. Transform their state once using
        # the previous frame's center, rather than invert it for every joint.
        center_frames={}
        for group,_,_ in self.chains:
            center=group.get('center',-1)
            if 0<=center<len(world) and center not in center_frames:
                current=world[center].copy()
                movement=current@np.linalg.inv(self.centers[center]) if not reset and center in self.centers else None
                center_frames[center]=(current,movement)
        self.external_velocity*=np.exp(-dt/0.18)
        def descendants(node):
            for parent,child in self.descendants[node]:
                world[child]=world[parent]@d.local[child]
        for group,nodes,kind in self.chains:
            center_node=group.get('center',-1)
            center_matrix,movement=center_frames.get(center_node,(None,None))
            drag=max(.12 if kind!='hair' else 0.,min(.99,group.get('dragForce',.4)))
            stiffness=max(0.,group.get('stiffiness',.7));gravity=group.get('gravityDir',{})
            force=np.array([gravity.get('x',0),gravity.get('y',-1),gravity.get('z',0)])*group.get('gravityPower',0)*dt*dt
            inertia=.30 if 'skirt' in kind or 'dress' in kind else .22
            spheres=[]
            for ci in group.get('colliderGroups',[]):
                if ci>=len(self.colliders):continue
                collider=self.colliders[ci];matrix=world[collider['node']]
                for sphere in collider.get('colliders',[]):
                    offset=sphere.get('offset',{});pos=matrix@np.array([offset.get('x',0),offset.get('y',0),offset.get('z',0),1.])
                    tail=sphere.get('tail');end=matrix@np.array([tail.get('x',0),tail.get('y',0),tail.get('z',0),1.]) if tail else pos
                    spheres.append((pos[:3],end[:3],sphere.get('radius',0)+group.get('hitRadius',0)))
            starts=np.array([s[0] for s in spheres]);ends=np.array([s[1] for s in spheres]);radii=np.array([s[2] for s in spheres])
            for chain_index,node in enumerate(nodes):
                short_hair=node in self.short_hair_nodes
                cloth=node in self.cloth_nodes
                node_drag=max(drag,.78) if cloth else max(drag,.70) if short_hair else drag
                environment=getattr(self.physics,'environment',None)
                if node in self.hair_nodes and environment is not None and environment.scene.phase=='seated':
                    node_drag=max(node_drag,.90)
                node_stiffness=max(stiffness,1.5) if cloth else max(stiffness,1.0) if short_hair else stiffness
                child=group.get('tipNode',d.nodes[node]['children'][0]);anchor=world[node,:3,3].copy();rest_tip=world[child,:3,3].copy();delta=rest_tip-anchor;length=math.sqrt(float(delta@delta))
                if length<1e-6:continue
                if reset or node not in self.states:self.states[node]=(rest_tip.copy(),rest_tip.copy())
                tip,previous=self.states[node]
                if center_matrix is not None:
                    if movement is not None:
                        tip=movement[:3,:3]@tip+movement[:3,3];previous=movement[:3,:3]@previous+movement[:3,3]
                restoring=min(.7,node_stiffness*dt*12)
                rest_target=rest_tip
                predicted=tip+(tip-previous)*(1-node_drag)+(rest_target-tip)*restoring+force-self.external_velocity*dt*(.08 if cloth else inertia)
                direction=predicted-anchor;predicted=anchor+direction/max(math.sqrt(float(direction@direction)),1e-9)*length
                # Vector broad phase avoids visiting every authored collider
                # in Python for every spring node, even when none is touched.
                for _ in range(3 if spheres else 0):
                    projected,depth=push_out(predicted,starts,ends,radii)
                    if depth<=1e-10:break
                    direction=projected-anchor;predicted=anchor+direction/max(math.sqrt(float(direction@direction)),1e-9)*length
                original=rest_tip-anchor;direction=predicted-anchor
                # Bound excessive lag when a user switches pose or a frame stalls.
                constraint=cloth_frames[node]@d.local[child][:3,3] if cloth else original
                constraint=constraint/max(float(np.linalg.norm(constraint)),1e-9)*length
                cosine=float(constraint@direction)/(length*length)
                limit=math.cos(math.radians(12)) if short_hair or cloth else (.78 if kind!='hair' else .65)
                if cosine<limit:
                    if short_hair or cloth:
                        axis=constraint/length;tangent=direction-axis*float(direction@axis)
                        tangent/=max(float(np.linalg.norm(tangent)),1e-9)
                        direction=length*(axis*limit+tangent*math.sqrt(1-limit*limit))
                        predicted=anchor+direction
                    else:
                        direction=original*.65+direction*.35;predicted=anchor+direction/max(math.sqrt(float(direction@direction)),1e-9)*length
                maximum_angle=math.radians(12) if short_hair or cloth else math.acos(.78 if kind!='hair' else .65)
                predicted=self.physics.constrain_tip(node,anchor,predicted,length,rest_tip,maximum_angle,previous=tip)
                world[node,:3,:3]=aim(original,predicted-anchor)@world[node,:3,:3]
                descendants(node);self.states[node]=(predicted,tip.copy())
        self.centers={node:frame for node,(frame,_) in center_frames.items()}
        environment=getattr(self.physics,'environment',None)
        if environment is not None:environment.solve_springs(world,self)
