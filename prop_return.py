"""Carry props to a reachable surface, set down, release, then leave."""
import math
import numpy as np
from furniture_scene import rotation,ease
from hand_pose import turn

def translation(p):
    m=np.eye(4);m[:3,3]=p;return m

class PropReturn:
    def __init__(self,activity):
        self.activity=activity;self.scene=s=activity.scene;self.model=m=s.model
        self.keys={'reading':['book'],'tv':['bowl','remote'] if activity.clock>=600 else ['remote'],
                   'coffee':['mug'],'window':['mug'],'meeting':['notebook']}.get(activity.kind,[])
        self.standing=activity.kind in ('reading','tv');self.clock=0.;self.stage='close';self.index=0
        self.placed={};self.drops={};self.ready=False;self.can_rise=False;self.correction=np.zeros(3)
        self.closed_time=6.666;self.squat=0.;self.release_clock=0.
        self.book_start=3.+min(1.5,activity.event_clock*.47) if activity.event=='page' else 3.
        self.release_hands={}
        self.initial_hands={side:self.hand(m.world,side).copy() for side in ('left','right')}
        self.height={};self.scale={};self.anchors={};self.bounds={};self.clouds={}
        f=s.fit
        for key in self.keys:
            asset=activity.assets[key]
            height=activity.reading_target(m,m.world)[1]*asset.extent[1]/asset.extent[0] if key=='book' else activity.cup_grip.height if key=='mug' else .17 if key=='bowl' else .025 if key=='remote' else .045
            self.height[key]=height;self.scale[key]=height/asset.extent[1]
            anchor=(asset.minimum+asset.maximum)*.5;anchor[1]=asset.minimum[1];self.anchors[key]=anchor
            if key=='book':
                matrices=asset.animation_matrices(self.closed_time)
                transformed=[]
                for part in asset.parts:
                    vertices=part['pos'][np.unique(part['indices'])]
                    transformed.append((np.c_[vertices,np.ones(len(vertices))]@matrices[part['node']].T)[:,:3])
                points=np.concatenate(transformed)
            else:points=np.concatenate([p['pos'][np.unique(p['indices'])] for p in asset.parts])
            self.clouds[key]=np.c_[points,np.ones(len(points))]
            self.bounds[key]=np.array([[x,y,z] for x in (points[:,0].min(),points[:,0].max()) for y in (points[:,1].min(),points[:,1].max()) for z in (points[:,2].min(),points[:,2].max())])
        if self.standing:
            from furniture_contacts import SurfaceField
            triangles=np.concatenate([part['pos'][part['indices'].reshape(-1,3)] for part in s.table.parts])@s.table_rotation.T
            self.table_field=SurfaceField(triangles,(0,2,1))
            center=np.array(s.table_row['surface']['center']);center[1]-=s.table.minimum[1]
            self.surface=s.table_position+center*s.table_scale
            lo=np.array(s.table_row['bounds']['min']);hi=np.array(s.table_row['bounds']['max']);lo[1]=hi[1]=0.
            table_corners=np.array([[x,0.,z] for x in (lo[0],hi[0]) for z in (lo[2],hi[2])])*s.table_scale+s.table_position
            radius=max(.28,abs(m.rest_canonical['leftUpperArm'][0]-m.rest_canonical['rightUpperArm'][0])*.6)
            chair=np.array([[x,0.,z] for x in (s.chair_min[0],s.chair_max[0]) for z in (s.chair_min[2],s.chair_max[2])])@s.turn.T+s.origin
            self.approach=np.array([min(self.surface[0]-.12,chair[:,0].min()-radius-.06),0.,table_corners[:,2].max()+radius+.06])
            self.heading=math.degrees(math.atan2(self.surface[0]-self.approach[0],self.surface[2]-self.approach[2]))
            from scene_navigation import route
            self.obstacles=[(chair[:,[0,2]].min(0),chair[:,[0,2]].max(0)),(table_corners[:,[0,2]].min(0),table_corners[:,[0,2]].max(0))]
            # First step forward clears the chair's conservative footprint;
            # the remaining path uses the same swept-radius scene planner.
            front=s.origin+s.forward*(s.chair_max[2]+radius+.25)
            for _ in range(12):
                try:planned=route(front[[0,2]],self.approach[[0,2]],self.obstacles,radius);break
                except ValueError:front+=s.forward*.12
            else:raise ValueError('Sehpaya gÃƒÂ¼venli bÃ„Â±rakma yolu bulunamadÃ„Â±.')
            self.route=[front]+[np.array([p[0],0.,p[1]]) for p in planned]
            home_path=route(front[[0,2]],np.zeros(2),self.obstacles,radius)
            self.exit_route=[np.array([p[0],0.,p[1]]) for p in route(self.approach[[0,2]],front[[0,2]],self.obstacles,radius)]+[np.array([p[0],0.,p[1]]) for p in home_path]
        else:
            self.approach=s.position.copy();self.heading=s.facing
            self.surface=s.stand+s.turn@s.cup_local if 'mug' in self.keys else s.origin+s.turn@np.array([s.workstation.width*.20,s.workstation.table_height,s.workstation.table_front+s.workstation.depth*.20])

    def hand(self,world,side):
        d=self.model.data;return (world[d.bones[side+'Hand'],:3,3]@d.flip.T-d.origin)*d.scale
    def actor(self):return translation(self.scene.position)@np.block([[rotation(self.scene.current_angle),np.zeros((3,1))],[np.zeros((1,3)),np.ones((1,1))]])
    def animation(self):return self.book_start+(self.closed_time-self.book_start)*ease(self.clock/1.2) if self.stage=='close' else self.closed_time
    def held_matrix(self,key,world):
        if key=='mug':return self.activity.cup_grip.matrix(world)
        if key=='book':
            width=self.height[key]*self.activity.assets[key].extent[0]/self.activity.assets[key].extent[1]
            sign=1 if self.model.rest_canonical['leftUpperArm'][0]>=self.model.rest_canonical['hips'][0] else -1
            supported=self.hand(world,'left')-np.array([sign*width*.42,.018,-.02])
            carried=(self.hand(world,'left')+self.hand(world,'right'))*.5+np.array([0.,-.018,.02])
            blend=ease(self.clock/1.2) if self.stage=='close' else 1.
            base=supported*(1-blend)+carried*blend
            pitch=-48.*(1-ease(self.clock/1.3)) if self.stage=='reach' else 0. if self.stage in ('release','withdraw','done') else -48.
        elif key=='bowl':base=self.hand(world,'left')+np.array([0.,-.10,.03]);pitch=0.
        elif key=='notebook':base=(self.hand(world,'left')+self.hand(world,'right'))*.5+np.array([0.,-.025,.015]);pitch=0.
        else:base=self.hand(world,'right')+np.array([0.,.008,.01]);pitch=0.
        m=translation(base);m[:3,:3]=turn(np.array([1.,0.,0.]),math.radians(pitch))*self.scale[key]
        m[:3,3]-=m[:3,:3]@self.anchors[key];return m
    def target(self,key):
        if not self.standing:return self.surface.copy()
        if not hasattr(self,'targets'):
            patch=np.asarray(self.scene.table_row['surface']['patch'])[:,[0,2]]
            ordered=sorted(set(map(tuple,patch)));hull=[]
            def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
            for sequence in (ordered,ordered[::-1]):
                edge=[]
                for point in sequence:
                    while len(edge)>1 and cross(edge[-2],edge[-1],point)<=0:edge.pop()
                    edge.append(point)
                hull.extend(edge[:-1])
            hull=np.asarray(hull)*self.scene.table_scale+self.scene.table_position[[0,2]]
            edges=np.roll(hull,-1,axis=0)-hull
            normals=np.column_stack((-edges[:,1],edges[:,0]));normals/=np.linalg.norm(normals,axis=1)[:,None]
            lo=hull.min(0);hi=hull.max(0)
            grid=np.array([[x,z] for x in np.linspace(lo[0],hi[0],29) for z in np.linspace(lo[1],hi[1],29)])
            self.targets={};occupied=[]
            for item in self.keys:
                cloud=self.clouds[item][:,:3]*self.scale[item]
                midpoint=(cloud[:,[0,2]].min(0)+cloud[:,[0,2]].max(0))*.5
                offsets=cloud[:,[0,2]]-midpoint
                margin=(offsets@normals.T).min(0)
                candidates=np.vstack((self.surface[[0,2]],grid))
                valid=np.all(np.einsum('nej,ej->ne',candidates[:,None,:]-hull,normals)+margin>=.012,axis=1)
                extent=np.ptp(cloud[:,[0,2]],axis=0)*.5
                for center,half in occupied:
                    valid &= np.any(np.abs(candidates-center)>extent+half+.025,axis=1)
                choices=candidates[valid]
                if not len(choices):raise ValueError('EÅŸyanÄ±n tamamÄ±nÄ± destekleyen ayrÄ± bir sehpa alanÄ± bulunamadÄ±.')
                preferred=self.surface[[0,2]]+np.array([-.09,0.]) if item=='bowl' else self.approach[[0,2]]
                selected=choices[np.argmin(np.linalg.norm(choices-preferred,axis=1))]
                target=self.surface.copy();target[[0,2]]=selected
                self.targets[item]=target;occupied.append((selected,extent))
        return self.targets[key].copy()
    def local_target(self,key):return rotation(self.scene.current_angle).T@(self.target(key)-self.scene.position)
    def supported(self,points):
        if not self.scene.table:return False
        patch=np.array(self.scene.table_row['surface']['patch'])[:,[0,2]]
        ordered=sorted(set(map(tuple,patch)));hull=[]
        def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
        for sequence in (ordered,ordered[::-1]):
            edge=[]
            for p in sequence:
                while len(edge)>1 and cross(edge[-2],edge[-1],p)<=0:edge.pop()
                edge.append(p)
            hull.extend(edge[:-1])
        local=(points[:,[0,2]]-self.scene.table_position[[0,2]])/self.scene.table_scale
        if len(hull)<3:return False
        hull=np.asarray(hull);edges=np.roll(hull,-1,axis=0)-hull;offset=local[:,None,:]-hull
        return bool(np.all(edges[None,:,0]*offset[:,:,1]-edges[None,:,1]*offset[:,:,0]>=-1e-5))
    def support_delta(self,points):
        s=self.scene;local=(points-s.table_position)/s.table_scale;local[:,1]+=s.table.minimum[1]
        height,valid=self.table_field.sample(local)
        if not valid.any():return None
        top=s.table_position[1]+(height[valid]-s.table.minimum[1])*s.table_scale
        return float(np.max(top-points[valid,1]))
    def step(self,dt):
        self.clock+=dt;s=self.scene
        for key,(remaining,speed) in list(self.drops.items()):
            speed+=18.*dt;step=min(remaining,speed*dt)
            self.placed[key][1,3]-=step
            if remaining<=step:del self.drops[key]
            else:self.drops[key]=(remaining-step,speed)
        if self.stage=='close' and self.clock>=1.2:
            self.stage='carry' if self.standing else 'align';self.clock=0.;self.can_rise=self.standing
        if self.stage=='align' and abs((s.current_angle-self.heading+180)%360-180)<2:
            self.stage='reach';self.clock=0.
        if self.stage=='reach' and self.clock>1.6 and self.model.world is not None:
            key=self.keys[self.index];matrix=self.actor()@self.held_matrix(key,self.model.world)
            points=(np.c_[self.bounds[key],np.ones(8)]@matrix.T)[:,:3]
            bottom=np.array([(points[:,0].min()+points[:,0].max())*.5,points[:,1].min(),(points[:,2].min()+points[:,2].max())*.5])
            error=self.target(key)-bottom
            cloud=(self.clouds[key]@matrix.T)[:,:3]
            supported=not self.standing or self.supported(cloud)
            if self.standing:
                delta=self.support_delta(cloud)
                if delta is not None:error[1]=delta
                else:supported=False
            if key!='mug':self.correction=np.clip(self.correction+rotation(s.current_angle).T@error*.15,-.22,.22)
            if supported and np.linalg.norm(error)<.022:
                matrix[:3,3]+=error;self.placed[key]=matrix;self.stage='release';self.clock=0.
            elif self.standing and supported and delta is not None and abs(delta)<.006 and np.linalg.norm(error[[0,2]])<max(.04,self.height[key]*.3):
                # A measured supported spot is a valid destination; forcing an
                # arbitrary exact center can keep a collision-safe hand stuck.
                # Keep the reached X/Z and only settle the tiny vertical gap.
                self.placed[key]=matrix
                if delta<0:self.drops[key]=(-float(delta),0.)
                else:self.placed[key][1,3]+=delta
                self.stage='release';self.clock=0.
            elif self.standing and supported and delta is not None and -.15<delta<0:
                # Let a carried object just above a fully supporting tabletop fall
                # vertically under gravity, rather than snapping it to a point.
                self.placed[key]=matrix;self.drops[key]=(-float(delta),0.)
                self.stage='release';self.clock=0.
            if self.stage=='release':self.release_hands={side:self.hand(self.model.world,side).copy() for side in ('left','right')}
        if self.stage=='release' and self.clock>=.5:
            self.index+=1;self.correction=np.zeros(3);self.clock=0.
            self.stage='withdraw' if self.index>=len(self.keys) else 'reach'
        if self.stage=='withdraw' and self.clock>=1.2:self.ready=True;self.stage='done'
        desired=1. if self.stage in ('reach','release') else 0.
        self.squat+=float(np.clip(desired-self.squat,-dt/1.2,dt/1.2))
    def apply_body(self,world):
        if self.stage not in ('reach','release','withdraw') or not self.standing:return
        from motion import ik
        from vrm import aim
        m=self.model;d=m.data;r=m.rest_canonical;physics=m.hair_springs.physics
        shoulder=float(np.mean([r[s+'UpperArm'][1] for s in ('left','right')]))
        reach=float(np.mean([np.linalg.norm(r[s+'LowerArm']-r[s+'UpperArm'])+np.linalg.norm(r[s+'Hand']-r[s+'LowerArm']) for s in ('left','right')]))
        amount=min(self.scene.fit.upper*1.15,max(0.,shoulder-self.surface[1]-reach*.55))
        weight=ease(self.squat)
        feet={s:world[d.bones[s+'Foot'],:3,3].copy() for s in ('left','right')}
        world[:,:3,3]+=d.flip.T@np.array([0.,-amount*weight/d.scale,0.])
        for side in ('left','right'):
            a,b,c=[d.bones[side+p] for p in ('UpperLeg','LowerLeg','Foot')]
            old=world[c,:3,:3].copy();hip,knee,foot=[world[n,:3,3].copy() for n in (a,b,c)]
            new_knee,end=ik(hip,feet[side],np.linalg.norm(knee-hip),np.linalg.norm(foot-knee),d.flip.T@np.array([0.,0.,1.]),145)
            physics._rotate_subtree(world,a,aim(knee-hip,new_knee-hip));physics._rotate_subtree(world,b,aim(world[c,:3,3]-world[b,:3,3],end-world[b,:3,3]));physics._rotate_subtree(world,c,old@np.linalg.inv(world[c,:3,:3]))
        spine=d.bones.get('spine')
        # Squatting already lowers the shoulders. A deep additional spine bend
        # puts the tabletop target behind the abdomen on short/compact rigs,
        # so torso avoidance correctly rejects the hand target indefinitely.
        if spine is not None:physics._rotate_subtree(world,spine,d.flip.T@turn(np.array([1.,0.,0.]),.25*weight)@d.flip)
    def hand_goals(self,world):
        d=self.model.data;r=self.model.rest_canonical;goals={}
        placing=self.stage=='reach';key=self.keys[min(self.index,len(self.keys)-1)]
        for side in ('left','right'):
            needed=key in ('book','notebook') or side==('left' if key=='bowl' else 'right')
            if not needed and not any(k not in self.placed for k in self.keys if (k=='bowl')==(side=='left')):continue
            shoulder=(world[d.bones[side+'UpperArm'],:3,3]@d.flip.T-d.origin)*d.scale
            sign=1 if r[side+'UpperArm'][0]>=r['hips'][0] else -1
            carry=shoulder+np.array([sign*.16,-.40,.31])
            if key in ('book','notebook'):
                spacing=min(.12,max(.065,float(np.ptp(self.bounds[key][:,0]))*self.scale[key]*.5+.015))
                carry[0]=r['hips'][0]+sign*spacing
            if self.stage=='close':carry=self.initial_hands[side]*(1-ease(self.clock/1.2))+carry*ease(self.clock/1.2)
            if self.stage in ('release','withdraw') and side in self.release_hands:
                needed=key in ('book','notebook') or side==('left' if key=='bowl' else 'right')
                if needed:
                    blend=0. if self.stage=='release' else ease(self.clock/1.2)
                    goals[side]=self.release_hands[side]*(1-blend)+carry*blend
                    continue
            if placing and needed:
                target=self.local_target(key)
                fitted=getattr(self,'fitted_goals',{}).get(key)
                if fitted is not None:
                    sides=('left','right') if key in ('book','notebook') else ('left',) if key=='bowl' else ('right',)
                    goals[side]=fitted[sides.index(side)].copy();continue
                if key=='mug':
                    # The actual constrained palm orientation differs across
                    # rigs. Close the loop on the displayed cup, not a fixed
                    # bind-pose wrist offset that assumes an upright hand.
                    previous=self.model.world
                    matrix=self.held_matrix(key,previous)
                    points=(np.c_[self.bounds[key],np.ones(8)]@matrix.T)[:,:3]
                    bottom=np.array([(points[:,0].min()+points[:,0].max())*.5,points[:,1].min(),(points[:,2].min()+points[:,2].max())*.5])
                    goal=self.hand(previous,'right')+(target-bottom)*.6
                else:
                    matrix=self.held_matrix(key,world);points=(np.c_[self.bounds[key],np.ones(8)]@matrix.T)[:,:3]
                    hands=(self.hand(world,'left')+self.hand(world,'right'))*.5 if key in ('book','notebook') else self.hand(world,'left' if key=='bowl' else 'right')
                    offset=np.array([(points[:,0].min()+points[:,0].max())*.5,points[:,1].min(),(points[:,2].min()+points[:,2].max())*.5])-hands
                    goal=target-offset+np.array([sign*.14 if key in ('book','notebook') else 0.,0.,0.])
                goals[side]=carry*(1-ease(self.clock/1.4))+(goal+self.correction)*ease(self.clock/1.4)
            else:goals[side]=carry
        return goals
    def draw(self):
        from OpenGL.GL import glPushMatrix,glPopMatrix,glMultMatrixd
        s=self.scene;slide=-4*(1-s.visibility)
        for key in self.keys:
            if key in self.placed:
                matrix=self.placed[key].copy();matrix[0,3]+=slide
                if s.desk:matrix[:3,3]+=s.turn@np.array([4.,0.,4.])*(1-s.desk_visibility)
            else:matrix=self.actor()@self.held_matrix(key,self.model.world)
            glPushMatrix();glMultMatrixd(matrix.T.copy());self.activity.assets[key].draw(animation_time=self.animation() if key=='book' else None);glPopMatrix()

