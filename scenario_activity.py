"""Seat-sized activity props, hand targets and interruptible cleanup."""
import math,random
import numpy as np
from item_assets import ItemAsset,LIBRARY
from hand_pose import turn
from joint_limits import limit_rotation
from scenario_timeline import next_event,duration,pulse as event_pulse

def smooth(u):
    u=float(np.clip(u,0.,1.));return u*u*(3-2*u)

class ScenarioActivity:
    def __init__(self,scene,kind):
        self.scene=scene;self.kind=kind;self.clock=0.;self.cleanup=False;self.cleanup_clock=0.;self.ready_to_leave=False
        self.assets={};self.rng=random.Random();self.event=None;self.previous_event=None;self.event_clock=0.;self.next_event=self.rng.uniform(28,36)
        self.snack_hand=None;self.snack_bowl=None;self.snack_lap=None
        self.extra_floor=np.empty((0,3))
        self.look_weight=0.
        self.pickup_correction=np.zeros(3)
        self.returner=None;self.return_started=False;self.abort_before_use=False
        if kind=='reading':self.next_event=self.rng.uniform(12,18)
        if kind=='window':self.next_event=self.rng.uniform(8,12)
        files={'reading':{'book':'book_animated_book__historical_book.glb'},'tv':{'tv':'flat_screen_television.glb','stand':'tv_stand.glb','remote':'tv_remote_control.glb','bowl':'popcorn_bowl.glb','snack':'popcorn_flake.glb'},
               'meeting':{'notebook':'alternatives/notebook.glb','microphone':'meeting_microphone.glb'},'coffee':{'machine':'alternatives/void_frame_studio__coffee_machine.glb','mug':'stylized_coffee_mug.glb','window':'alternatives/window.glb'},
               'window':{'mug':'stylized_coffee_mug.glb','window':'alternatives/window.glb'}}
        try:
            if kind in ('coffee','window'):files[kind]['counter']='table_hightop.glb'
            if kind in ('reading','tv'):
                scene.ensure_table(.46 if kind=='tv' else .23,.36 if kind=='tv' else .28)
            for key,file in files.get(kind,{}).items():
                asset=ItemAsset(LIBRARY/file)
                if key=='book':
                    transforms=asset.animation_matrices(3.)
                    cloud=np.concatenate([(np.column_stack((p['pos'],np.ones(len(p['pos']))))@transforms[p['node']].T)[:,:3] for p in asset.parts])
                    asset.minimum=cloud.min(0);asset.maximum=cloud.max(0);asset.extent=asset.maximum-asset.minimum
                self.assets[key]=asset
            self.cup_grip=None
            if 'mug' in self.assets:
                from cup_grip import CupGrip
                self.cup_grip=CupGrip(scene.model,self.assets['mug'])
            if kind=='tv':
                asset=self.assets['stand'];scale=.28/max(float(asset.extent[1]),.001)
                center=np.array([scene.fit.width*.5,0.,scene.fit.upper*2.8])
                points=np.array([[x,0.,z] for x in (-asset.extent[0]*scale*.5,asset.extent[0]*scale*.5) for z in (-asset.extent[2]*scale*.5,asset.extent[2]*scale*.5)])+center
                self.extra_floor=points@scene.turn.T+scene.origin
        except (OSError,ValueError):
            self.ready_to_leave=True;self.release();raise
        self.book_contacts=None
        if kind=='reading':
            from book_contacts import BookContacts
            self.book_contacts=BookContacts(self)
        scene.model.scenario_activity=self
    def step(self,dt):
        look=1. if self.scene.phase=='seated' and not getattr(self.scene.model,'speaking_for_seat',False) else 0.
        self.look_weight+=(look-self.look_weight)*(1-math.exp(-dt/.25))
        if self.cleanup and getattr(self,'abort_before_use',False):
            self.cleanup_clock+=dt;self.ready_to_leave=True
            return
        if self.cleanup:
            self.cleanup_clock+=dt
            # Finish the short lap-to-mouth-to-lap cycle before grasping the
            # bowl for exit. Attaching it to a hand mid-bite would teleport it.
            if not self.return_started and self.event=='snack' and self.event_clock<duration('snack'):
                self.event_clock=min(duration('snack'),self.event_clock+dt)
                return
            if self.event=='snack':self.event=None
            if not self.return_started:
                self.return_started=True
                if self.kind in ('reading','tv','meeting','coffee','window') and not (self.kind=='coffee' and self.clock<19):
                    from prop_return import PropReturn
                    self.returner=PropReturn(self)
            if self.returner:
                self.returner.step(dt);self.ready_to_leave=self.returner.ready
            else:self.ready_to_leave=self.cleanup_clock>=1.4
        if self.scene.phase!='seated' or getattr(self.scene.model,'speaking_for_seat',False):return
        self.clock+=dt
        if self.cleanup:return
        if self.event:
            self.event_clock+=dt
            if self.event_clock>=duration(self.event):self.previous_event=self.event;self.event=None;self.next_event=self.clock+self.rng.uniform(16,24) if self.kind=='reading' else self.clock+self.rng.uniform(30,40)
        elif self.clock>=self.next_event:
            self.event=next_event(self.kind,self.clock,self.previous_event,self.rng)
            self.event_clock=0.;self.next_event=self.clock+self.rng.uniform(30,40)
            if self.event=='snack':
                self.snack_hand=self.hand(self.scene.model.world,'left')
                self.snack_bowl=self.snack_hand+np.array([0.,-.10,.03])
                self.snack_lap=self.snack_bowl.copy();self.snack_lap[1]=self.scene.fit.height+self.scene.fit.padding+.07
    @property
    def weight(self):
        physical=self.kind in ('reading','tv','meeting','coffee','window')
        if physical and self.cleanup and not self.ready_to_leave:return 1.
        return 1.-smooth(self.cleanup_clock/1.25) if self.cleanup else 1.
    def hand(self,world,side):
        d=self.scene.model.data;return (world[d.bones[side+'Hand'],:3,3]@d.flip.T-d.origin)*d.scale
    def bowl_base(self,world):
        if self.event!='snack' or self.snack_lap is None:return self.hand(world,'left')+np.array([0.,-.10,.03])
        weight=smooth(self.event_clock/.65)*(1-smooth((self.event_clock-3.05)/.75))
        return self.snack_bowl*(1-weight)+self.snack_lap*weight
    def reading_target(self,model,world):
        d=model.data
        point=lambda n:(world[d.bones[n],:3,3]@d.flip.T-d.origin)*d.scale
        shoulder=(point('leftUpperArm')+point('rightUpperArm'))*.5
        reach=np.mean([np.linalg.norm(model.rest_canonical[s+'LowerArm']-model.rest_canonical[s+'UpperArm'])+np.linalg.norm(model.rest_canonical[s+'Hand']-model.rest_canonical[s+'LowerArm']) for s in ('left','right')])
        width=float(np.clip(np.linalg.norm(point('leftUpperArm')-point('rightUpperArm'))*1.1,.26,.38))
        anchor=np.array([shoulder[0],point('head')[1]-reach*.62,shoulder[2]+reach*.53])
        return anchor,width
    def hand_goals(self,model,world):
        d=model.data;f=self.scene.fit;goals={}
        if self.returner and not self.returner.ready:return self.returner.hand_goals(world)
        if self.scene.phase!='seated' or self.weight<=0:return goals
        canonical=lambda name:(world[d.bones[name],:3,3]@d.flip.T-d.origin)*d.scale
        pulse=event_pulse(self.event,self.event_clock)
        if getattr(model,'speaking_for_seat',False):pulse=0.
        for side in ('left','right'):
            sign=1 if model.rest_canonical[side+'UpperArm'][0]>=model.rest_canonical['hips'][0] else -1
            if self.kind=='reading':
                anchor,width=self.reading_target(model,world)
                # Put wrists outside the cover; the fingers extend inward
                # onto its edge. Wrist targets inside the cover drove the
                # whole palm through the pages.
                goal=anchor+np.array([sign*width*.55,0.,0.])
                if side=='right' and self.event=='page':
                    goal[0]=anchor[0]+sign*width*.55*(1-.8*pulse);goal+=np.array([0.,.04,.03])*pulse
                goals[side]=goal
            elif self.kind=='tv' and side=='right':
                goal=np.array([sign*f.width*.19,f.height+f.padding*2+.07,f.upper*.54])
                if self.event=='remote':goal+=np.array([0.,.12,.14])*pulse
                goals[side]=goal
            elif self.kind=='tv' and side=='left' and self.clock>=600:
                goal=np.array([sign*.13,f.height+f.padding*2+.10,f.upper*.6])
                if self.event=='snack' and self.snack_lap is not None:
                    if self.event_clock<.65:goal=self.snack_hand+(self.snack_lap-self.snack_bowl)*smooth(self.event_clock/.65)
                    elif self.event_clock<3.05:
                        eat=math.sin(math.pi*(self.event_clock-.65)/2.4) if not getattr(model,'speaking_for_seat',False) else 0.
                        lap=self.snack_lap+np.array([0.,.10,-.03]);goal=lap*(1-eat)+(canonical('head')+np.array([sign*.035,-.10,.13]))*eat
                    else:goal=self.snack_hand+(self.snack_lap-self.snack_bowl)*(1-smooth((self.event_clock-3.05)/.75))
                goals[side]=goal
            elif self.kind=='meeting':
                goals[side]=np.array([sign*.13,f.height+f.padding+.25,f.upper*.62])
            elif self.kind=='rest' and self.event in ('stretch','yawn'):
                shoulder=canonical(side+'UpperArm')
                goals[side]=canonical(side+'Hand')*(1-pulse)+(shoulder+np.array([sign*.18,.09,.30]))*pulse
            elif self.kind in ('typing','coding','browsing') and hasattr(self.scene.rig,'keyboard_target'):
                goal=self.scene.rig.keyboard_target.copy();goal[0]+=sign*self.scene.rig.hand_spacing
                if self.kind!='browsing' and self.event!='think':goal[1]+=.004*math.sin(self.clock*9+(0 if side=='left' else 1.5))
                if side=='right' and (self.kind=='browsing' or self.event=='mouse' or int(self.clock//16)%3==2):
                    goal=np.array([-abs(model.rest_canonical['leftUpperArm'][0]-model.rest_canonical['rightUpperArm'][0])*.85,goal[1],self.scene.workstation.keyboard_center[2]])
                if self.event=='think':goal+=np.array([0.,.04,.015])*pulse
                goals[side]=goal
            elif self.kind in ('coffee','window') and side=='right':
                shoulder=canonical(side+'UpperArm');reach=np.linalg.norm(model.rest_canonical[side+'LowerArm']-model.rest_canonical[side+'UpperArm'])+np.linalg.norm(model.rest_canonical[side+'Hand']-model.rest_canonical[side+'LowerArm'])
                goal=shoulder+np.array([sign*reach*.10,-reach*.56,reach*.35])
                if self.kind=='coffee' and self.clock<21:
                    pickup=self.cup_grip.wrist_for(self.scene.cup_local)+self.pickup_correction
                    approach=smooth((self.clock-15)/2)
                    lift=smooth((self.clock-19)/2)
                    goal=goal*(1-approach)+pickup*approach
                    goal=goal*(1-lift)+(shoulder+np.array([sign*reach*.10,-reach*.56,reach*.35]))*lift
                elif self.event=='sip':goal=goal*(1-pulse)+self.cup_grip.sip_goal(world)*pulse
                if self.kind!='coffee' or self.clock>=21:goal[1]=max(goal[1],self.scene.counter_height+.12)
                goals[side]=goal
            elif self.kind=='coffee' and side=='left' and self.clock<15:
                shoulder=canonical(side+'UpperArm')
                ready=shoulder+np.array([sign*.12,-.25,.32])
                press=self.scene.machine_local+np.array([0.,.23,-.25])
                pulse=smooth(self.clock/2)*(1-smooth((self.clock-12)/3))
                goals[side]=ready*(1-pulse)+press*pulse
        return goals
    def apply_pose(self,world,model):
        if self.returner:self.returner.apply_body(world)
        if model.hand_gesture:return
        if self.kind=='coffee' and self.clock<15 and not getattr(self,'pickup_layout_fitted',False):
            # Fit the placed cup before reaching starts. The complete cup
            # footprint must remain supported by the actual counter.
            self.pickup_layout_fitted=True
            grip=self.cup_grip;asset=self.assets['mug'];rotation=np.diag([grip.sign,1.,grip.sign])
            for _ in range(3):
                target=self.scene.cup_local+rotation@((grip.anchor-grip.center)*grip.scale)
                trial=world.copy();grip.fit_pickup(trial,target);error=grip.contact(trial)-target
                if np.linalg.norm(error)<.006:break
                candidate=self.scene.cup_local.copy();candidate[[0,2]]+=error[[0,2]]
                half=asset.extent[[0,2]]*grip.scale*.5
                if np.any(candidate[[0,2]]-half<self.scene.counter_min[[0,2]]) or np.any(candidate[[0,2]]+half>self.scene.counter_max[[0,2]]):break
                self.scene.cup_local=candidate
        from motion import ik
        from vrm import aim
        d=model.data;physics=model.hair_springs.physics
        if self.event and not self.cleanup and self.scene.phase=='seated' and not getattr(model,'speaking_for_seat',False):
            amount=event_pulse(self.event,self.event_clock)
            node=d.bones.get('head')
            angles={'glance':(0.,.16*amount,0.),'nod':(.055*math.sin(self.event_clock*5)*amount,0.,0.),'think':(-.025*amount,.055*amount,0.),'yawn':(-.07*amount,0.,0.),'note':(.09*amount,0.,0.)}.get(self.event)
            if node is not None and angles:
                local=world[d.parents[node],:3,:3];change=np.eye(3)
                for axis,angle in zip(np.eye(3),angles):change=change@turn(axis,angle)
                target=local@limit_rotation(d.local[node][:3,:3],np.linalg.solve(local,d.flip.T@change@d.flip@world[node,:3,:3]),45.)
                physics._rotate_subtree(world,node,target@np.linalg.inv(world[node,:3,:3]))
            if self.event in ('shoulders','settle','stretch'):
                node=d.bones.get('chest',d.bones.get('spine'))
                if node is not None:physics._rotate_subtree(world,node,d.flip.T@turn(np.array([0.,0.,1.]),.025*amount*(1 if self.event=='settle' else math.sin(self.event_clock*2)))@d.flip)
        if self.scene.phase=='seated' and self.look_weight>1e-4 and self.kind in ('reading','tv'):
            head=d.bones.get('head')
            if head is not None:
                pitch=(.38+.012*math.sin(self.clock*.8))*self.look_weight if self.kind=='reading' else 0.
                yaw=min(.55,math.atan2(self.scene.fit.width*.5,self.scene.fit.upper*2.8))*self.look_weight if self.kind=='tv' else .025*math.sin(self.clock*.6)*self.look_weight
                rotation=d.flip.T@turn(np.array([0.,1.,0.]),yaw)@turn(np.array([1.,0.,0.]),pitch)@d.flip
                parent=world[d.parents[head],:3,:3]
                local=np.linalg.solve(parent,rotation@world[head,:3,:3])
                bounded=parent@limit_rotation(d.local[head][:3,:3],local,45.)
                physics._rotate_subtree(world,head,bounded@np.linalg.inv(world[head,:3,:3]))
        if self.kind=='rest' and self.scene.phase=='seated':
            # A restrained ankle-over-ankle variation leaves a planted support
            # foot. Bulky thigh clothing receives a smaller crossing envelope.
            f=self.scene.fit;cycle=self.clock%75
            crossing=smooth((cycle-10)/3)*(1-smooth((cycle-60)/3))*self.weight
            crossing*=.55 if f.padding>f.upper*.25 else 1.
            if crossing>0:
                side='right' if int(self.clock//75)%2==0 else 'left';other='left' if side=='right' else 'right'
                a,b,c=[d.bones[side+p] for p in ('UpperLeg','LowerLeg','Foot')]
                old=world[c,:3,:3].copy();foot=(world[c,:3,3]@d.flip.T-d.origin)*d.scale
                support=(world[d.bones[other+'Foot'],:3,3]@d.flip.T-d.origin)*d.scale
                target=foot.copy();target[0]=support[0];target[1]+=.025;target[2]+=.16
                target=foot*(1-crossing)+target*crossing;raw=d.flip.T@(target/d.scale+d.origin)
                hip,knee,end=[world[n,:3,3].copy() for n in (a,b,c)]
                new_knee,new_foot=ik(hip,raw,np.linalg.norm(knee-hip),np.linalg.norm(end-knee),d.flip.T@np.array([0.,0.,1.]),145)
                physics._rotate_subtree(world,a,aim(knee-hip,new_knee-hip))
                physics._rotate_subtree(world,b,aim(world[c,:3,3]-world[b,:3,3],new_foot-world[b,:3,3]))
                physics._rotate_subtree(world,c,old@np.linalg.inv(world[c,:3,:3]))
        speaking=getattr(model,'speaking_for_seat',False)
        occupied={'left','right'} if self.kind in ('reading','meeting') or self.kind=='tv' and self.clock>=600 else {'right'} if self.kind in ('tv','coffee','window') else set()
        for side,goal in self.hand_goals(model,world).items():
            if speaking and side not in occupied:continue
            hand=world[d.bones[side+'Hand'],:3,3]
            current=(hand@d.flip.T-d.origin)*d.scale
            goal=current*(1-self.weight)+goal*self.weight
            from interaction_ik import solve_hand
            returning=bool(self.returner and not self.returner.ready)
            pole=None
            if returning and self.returner.stage=='reach' and self.returner.clock>1.3:
                pole=model.world[d.bones[side+'LowerArm'],:3,3]-model.world[d.bones[side+'UpperArm'],:3,3]
            solve_hand(model,world,side,goal,returning=returning,elbow_pole=pole)
        if self.cup_grip and (self.scene.phase=='seated' or self.returner and 'mug' not in self.returner.placed):
            grip=smooth((self.clock-17)/1.5) if self.kind=='coffee' else 1.
            if grip>.98:self.cup_grip.align_forearm(world)
            model.hand_poses.apply(world,'cup_grip',selected='right',weight=grip*self.weight)
            if self.event=='sip' and not self.cleanup:
                hand=d.bones['rightHand'];amount=event_pulse('sip',self.event_clock)
                parent=world[d.parents[hand],:3,:3]
                desired=d.flip.T@turn(np.array([1.,0.,0.]),-.24*amount)@d.flip@world[hand,:3,:3]
                target=parent@limit_rotation(d.local[hand][:3,:3],np.linalg.solve(parent,desired),35.)
                physics._rotate_subtree(world,hand,target@np.linalg.inv(world[hand,:3,:3]))
            if self.kind=='coffee' and 17.<=self.clock<19.:
                rotation=np.diag([self.cup_grip.sign,1.,self.cup_grip.sign])
                target=self.scene.cup_local+rotation@((self.cup_grip.anchor-self.cup_grip.center)*self.cup_grip.scale)
                if grip>.01:
                    fit_target=self.cup_grip.contact(world)*(1-grip)+target*grip
                    self.cup_grip.fit_pickup(world,fit_target)
                error=target-self.cup_grip.contact(world)
                self.pickup_correction=np.clip(self.pickup_correction+error*.7,-.12,.12)
    def apply_fingers(self,world,model):
        if model.hand_gesture or self.scene.phase not in ('seated','unequip'):return
        hands=model.hand_poses
        if self.cleanup:return
        if self.kind in ('reading','meeting','tv'):
            style={'reading':'book_grip','meeting':'notebook_grip','tv':'remote_grip'}[self.kind]
            for side in (('left','right') if self.kind!='tv' else ('right',)):
                hands.fingers(world,side,'point' if self.kind=='reading' and side=='right' and self.event=='page' else style,self.weight)
        if self.book_contacts is not None:self.book_contacts.solve(model,world)
        if self.kind in ('typing','coding','browsing') and self.event!='think' and not getattr(model,'speaking_for_seat',False):
            from finger_contacts import key_press
            workstation=self.scene.workstation
            for side in ('left','right'):
                mouse=side=='right' and (self.kind=='browsing' or self.event=='mouse' or int(self.clock//16)%3==2)
                if self.kind=='browsing' and not mouse:continue
                hands.fingers(world,side,'relaxed',self.weight)
                phase=self.clock*(3. if mouse else 4.5)+(0. if side=='left' else .45)
                finger='Index' if mouse else ('Index','Middle','Ring')[int(phase)%3]
                pulse=np.sin(np.pi*(phase%1.))**2
                key_press(model,world,side,finger,workstation.table_height+(.026 if mouse else .014),float(pulse)*self.weight)
    def _draw_asset(self,key,position,height,yaw=0.,pitch=0.,animation_time=None):
        from OpenGL.GL import glPushMatrix,glPopMatrix,glTranslatef,glRotatef,glScalef
        asset=self.assets.get(key)
        if asset is None:return
        scale=height/max(float(asset.extent[1]),.001)
        center=(asset.minimum+asset.maximum)*.5;center[1]=asset.minimum[1]
        glPushMatrix();glTranslatef(*position);glRotatef(yaw,0,1,0);glRotatef(pitch,1,0,0);glScalef(scale,scale,scale);glTranslatef(*(-center));asset.draw(animation_time=animation_time,opacity=getattr(self,'draw_opacity',1.));glPopMatrix()
    def draw(self):
        from OpenGL.GL import glPushMatrix,glPopMatrix,glTranslatef,glRotatef
        scene=self.scene;model=scene.model;d=model.data;f=scene.fit
        self.draw_opacity=1.
        slide=-4*(1-scene.visibility)
        # Static desk equipment follows the desk, including arrival/exit slides;
        # it must not inherit the character's hand or cleanup transformations.
        if self.kind=='meeting' and scene.desk_visibility>0:
            desk=scene.workstation
            height=desk.table_height*.23
            local=np.array([desk.width*.40,desk.table_height,desk.monitor_distance-.15*desk.depth])
            local+=np.array([4*(1-scene.desk_visibility),0.,4*(1-scene.desk_visibility)])
            self._draw_asset('microphone',scene.origin+scene.turn@local,height,scene.facing)
        if self.kind=='tv':
            position=scene.origin+scene.turn@np.array([f.width*.50,0.,f.upper*2.8])
            position[0]+=slide
            self._draw_asset('stand',position,.28,scene.facing)
            self._draw_asset('tv',position+np.array([0.,.28,0.]),.65,scene.facing+90)
        if self.kind in ('coffee','window'):
            base=getattr(scene,'stand',scene.origin)
            top=getattr(scene,'counter_height',f.height+f.padding+.3)
            self._draw_asset('machine',base+scene.turn@scene.machine_local+np.array([slide,0.,0.]),.38,scene.machine_yaw)
            window_bottom=max(top+.15,float(model.rest_canonical['head'][1])-.65)
            window_position=base+scene.turn@(scene.window_local+np.array([0.,window_bottom,0.]))+np.array([slide,0.,0.])
            window_yaw=getattr(scene,'window_yaw',scene.facing)
            if hasattr(scene,'window_view'):
                scene.window_view.draw(self.assets['window'],window_position,1.25,window_yaw,self.clock)
            self._draw_asset('window',window_position,1.25,window_yaw)
            if self.kind=='coffee' and self.clock<19 and not self.returner:
                placed=base+scene.turn@scene.cup_local+np.array([slide,0.,0.])
                self._draw_asset('mug',placed,self.cup_grip.height,scene.facing+180)
        if self.returner:self.returner.draw();return
        if scene.phase not in ('seated','unequip') or self.ready_to_leave:return
        if self.cleanup and self.kind not in ('reading','tv','meeting','coffee','window'):self.draw_opacity=1.-smooth((self.cleanup_clock-.55)/.75)
        def hand(side):return (model.world[d.bones[side+'Hand'],:3,3]@d.flip.T-d.origin)*d.scale
        # Attached objects use the character's final deformed hand position,
        # including contact corrections, rather than a guessed global point.
        glPushMatrix();glTranslatef(*scene.position);glRotatef(scene.current_angle,0,1,0)
        if self.kind=='reading':
            book=self.assets['book'];_,width=self.reading_target(model,model.world);height=width*book.extent[1]/book.extent[0]
            page_time=3.+min(1.5,self.event_clock*.47) if self.event=='page' else 3.
            if self.cleanup:page_time=3.+3.666*smooth(self.cleanup_clock/1.25)
            sign=1 if model.rest_canonical['leftUpperArm'][0]>=model.rest_canonical['hips'][0] else -1
            # The supporting wrist remains the anchor during a page turn.
            center=hand('left')-np.array([sign*width*.55,.018,-.02])
            self._draw_asset('book',center,height,pitch=-48,animation_time=page_time)
        elif self.kind=='tv':
            remote=hand('right')+np.array([0.,.008,.01])
            self._draw_asset('remote',remote,.025)
            if self.clock>=600:self._draw_asset('bowl',self.bowl_base(model.world),.17)
            if self.event=='snack' and .65<self.event_clock<1.9 and not getattr(model,'speaking_for_seat',False):self._draw_asset('snack',hand('left'),.02)
        elif self.kind=='meeting':
            self._draw_asset('notebook',(hand('left')+hand('right'))*.5+np.array([0.,-.025,.015]),.045)
        elif self.kind in ('coffee','window'):
            if self.kind=='window' or self.clock>=19:
                self.cup_grip.draw(model.world,self.draw_opacity)
        glPopMatrix()
    def release(self):
        if getattr(self.scene.model,'scenario_activity',None) is self:self.scene.model.scenario_activity=None
        for asset in self.assets.values():asset.release()
