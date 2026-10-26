"""Explicit furniture actions with fitted seats and a continuous approach/exit."""
import math
import random
import numpy as np
from item_assets import ItemAsset, LIBRARY, manifest
from seat_rig import fit_chair, SeatedRig

def rotation(yaw):
    a=math.radians(yaw);c,s=math.cos(a),math.sin(a)
    return np.array([[c,0,s],[0,1,0],[-s,0,c]])

def ease(t):
    t=float(np.clip(t,0,1));return t*t*(3-2*t)

class FurnitureScene:
    def __init__(self,model,previous=None,rng=None,mode='lounge'):
        rng=rng or random.SystemRandom();choices=[]
        for row in manifest()['items']:
            if mode=='work':
                if row['role']!='desk_set':continue
            elif row['role']!='chair':continue
            if 'seat' not in row:continue
            try:choices.append(fit_chair(row,model))
            except ValueError:continue
        if not choices:raise ValueError('Bu karaktere uygun ölçüde koltuk bulunamadı.')
        others=[f for f in choices if f.item['id']!=previous]
        self.fit=rng.choice(others or choices);self.asset=ItemAsset(LIBRARY/self.fit.item['file'])
        self.rig=SeatedRig(self.fit);self.rig.mode=mode;self.model=model;self.old_locomotion=model.locomotion
        self.old_simulation_hz=model.hair_springs.simulation_hz
        from locomotion import Locomotion
        self.locomotion=Locomotion()
        self.phase='arrive';self.elapsed=0.;self.visibility=0.;self.position=np.zeros(3);self.heading=0.;self.pose='idle';self.done=False;self.exit_requested=False
        self.mode=mode;self.desk_visibility=0.;self.desk=None
        self.activity=None
        self.facing=-40. if mode=='work' else 22.;self.turn=rotation(self.facing);self.forward=self.turn[:,2]
        self.rig.viewer_yaw=-self.facing
        chair_parts=[p for p in self.asset.parts if mode!='work' or 'chair' in p['name'].casefold()]
        cloud=(np.concatenate([p['pos'][np.unique(p['indices'])] for p in chair_parts])-self.fit.pivot)@rotation(-self.fit.yaw).T*self.fit.scale
        self.chair_min=cloud.min(0);self.chair_max=cloud.max(0)
        front_extent=max(self.fit.upper,self.chair_max[2])
        self.origin=np.array([-.55,0.,0.])-self.forward*(front_extent+.55)
        half_width=abs(model.rest_canonical['leftUpperLeg'][0]-model.rest_canonical['rightUpperLeg'][0])*.5
        self.walk_radius=max(.12,half_width+.08)
        standing_distance=max(self.fit.stand_distance,front_extent+self.walk_radius+.035) if mode=='work' else self.fit.stand_distance
        self.stand=self.origin+self.forward*standing_distance
        lateral=self.turn[:,0]*(max(abs(self.chair_min[0]),abs(self.chair_max[0]))+.45)
        front=self.origin+self.forward*(front_extent+.50)
        self.route=[front+lateral,front,self.stand];self.route_index=0
        self.locomotion.speed_scale=1.18
        if mode=='work':self.route=self.plan_route(np.zeros(3),self.stand)
        self.table=None;self.table_row=None
        tables=[r for r in manifest()['items'] if r['role']=='side_table' and 'surface' in r]
        if mode=='work':
            self.desk=self.asset
            from workstation_fit import WorkstationFit
            self.workstation=WorkstationFit(self.asset,self.fit,model)
            self.keyboard_target=self.workstation.wrist
            self.rig.keyboard_target=self.keyboard_target;self.rig.hand_spacing=self.workstation.hand_spacing
        elif tables:
            self.set_table(rng.choice(tables))
        # Keep the home position outside the full swept return footprint,
        # including large chairs and rotated tabletop bounds.
        radius=max(.28,abs(model.rest_canonical['leftUpperArm'][0]-model.rest_canonical['rightUpperArm'][0])*.6)
        chair_world=np.array([[x,0.,z] for x in (self.chair_min[0],self.chair_max[0]) for z in (self.chair_min[2],self.chair_max[2])])@self.turn.T+self.origin
        front_edge=float(chair_world[:,2].max())
        if self.table:
            front_edge=max(front_edge,self.table_position[2]+self.table_row['bounds']['max'][2]*self.table_scale)
        shift=np.array([0.,0.,min(0.,-radius-.06-front_edge)])
        self.origin+=shift;self.stand+=shift
        self.route=[p+shift for p in self.route]
        if self.table:self.table_position+=shift
        if mode=='work':self.route=self.plan_route(np.zeros(3),self.stand)
        self.current_angle=0.
        self.support_points=self._floor_points()
        from furniture_contacts import FurnitureContacts
        self.contacts=FurnitureContacts(self)
        model.locomotion=self.locomotion;model.seating=self.rig;model.furniture_contacts=self.contacts
        model.hair_springs.simulation_hz=min(30.,self.old_simulation_hz) if self.old_simulation_hz>0 else self.old_simulation_hz
        model.hair_springs.physics.environment=self.contacts
        # Direct per-vertex projection remains a diagnostic: large corrections
        # can stretch hair polygons. Runtime uses constrained spring contacts.

    def set_table(self,row):
        if self.table:self.table.release()
        # The cantilever's open side must face the chair on its right.
        import copy
        row=copy.deepcopy(row)
        self.table_yaw=self.facing+180. if row['id']=='modern_ovale_side_table__low_poly_furniture_(1)' else 0.
        self.table_rotation=rotation(self.table_yaw)
        if self.table_yaw:
            for section in ('bounds','surface'):
                info=row[section]
                low,high=('min','max') if section=='bounds' else ('minimum','maximum')
                if low in info:
                    a=np.array(info[low]);b=np.array(info[high]);corners=np.array([[x,y,z] for x in (a[0],b[0]) for y in (a[1],b[1]) for z in (a[2],b[2])])@self.table_rotation.T
                    info[low]=corners.min(0).tolist();info[high]=corners.max(0).tolist()
                for key in ('center','patch'):
                    if key in info:info[key]=(np.array(info[key])@self.table_rotation.T).tolist()
        self.table_row=row;self.table=ItemAsset(LIBRARY/row['file'])
        p=row['surface'];self.table_scale=(self.fit.height+.10)/max(.05,p['center'][1]-row['bounds']['min'][1])
        corners=np.array([[x,0.,z] for x in (self.chair_min[0],self.chair_max[0]) for z in (self.chair_min[2],self.chair_max[2])])@self.turn.T+self.origin
        lo=np.array(row['bounds']['min'])*self.table_scale;hi=np.array(row['bounds']['max'])*self.table_scale
        # Fit against the actual chair's side in its own frame, not the
        # oversized world-axis box of a rotated backrest.
        table_points=np.concatenate([part['pos'][np.unique(part['indices'])] for part in self.table.parts])
        table_corners=table_points@self.table_rotation.T*self.table_scale
        local=table_corners@self.turn
        target=np.array([self.chair_min[0]-local[:,0].max()-.025,0.,(self.chair_min[2]+self.chair_max[2])*.5-(local[:,2].min()+local[:,2].max())*.5])
        self.table_position=self.origin+self.turn@target
        self.table_position[1]=0.
        for name in ('_framing_points','_framing_aspect'):
            if hasattr(self,name):delattr(self,name)

    def ensure_table(self,width,depth):
        def fits(row):
            p=row['surface'];scale=(self.fit.height+.10)/max(.05,p['center'][1]-row['bounds']['min'][1])
            extent=(np.array(p['maximum'])-p['minimum'])*scale
            return extent[0]>=width and extent[2]>=depth
        if self.table_row and fits(self.table_row):return
        choices=[row for row in manifest()['items'] if row['role']=='side_table' and 'surface' in row and fits(row)]
        if not choices:raise ValueError('Bu eşya için yeterli yüzeye sahip sehpa bulunamadı.')
        self.set_table(random.SystemRandom().choice(choices));self.support_points=self._floor_points()
        self.model.furniture_surface_guard=False

    def floor_points(self):
        if self.activity is not None and len(self.activity.extra_floor):return np.concatenate((self.support_points,self.activity.extra_floor))
        return self.support_points

    def _floor_points(self):
        corners=np.array([[x,0.,z] for x in (self.chair_min[0],self.chair_max[0]) for z in (self.chair_min[2],self.chair_max[2])])
        points=corners@self.turn.T+self.origin
        if self.table:
            lo=self.table_row['bounds']['min'];hi=self.table_row['bounds']['max']
            points=np.concatenate((points,np.array([[x,0.,z] for x in (lo[0],hi[0]) for z in (lo[2],hi[2])])*self.table_scale+self.table_position))
        if self.desk:
            points=np.concatenate((points,np.array(self.workstation.floor)@self.turn.T+self.origin))
        return points

    def request_exit(self):
        if self.exit_requested:return
        self.exit_requested=True
        if self.activity:
            self.activity.cleanup=True
            if self.phase in ('arrive','walk','turn','lower','equip'):
                # Nothing has been picked up yet. Do not invent a carried prop
                # or start its return animation while still approaching the seat.
                self.activity.abort_before_use=True;self.activity.ready_to_leave=True
        if self.phase=='arrive':
            self.depart_visibility=self.visibility;self.change_phase('depart')
        elif self.phase in ('walk','turn'):
            # Retrace only the already travelled waypoints, not the rest of the
            # approach. This preserves the route's known obstacle clearance.
            self.route=list(reversed(self.route[:self.route_index]))+[np.zeros(3)]
            self.route_index=0;self.change_phase('leave')

    def plan_route(self,start,goal):
        from scene_navigation import route
        half_width=abs(self.model.rest_canonical['leftUpperLeg'][0]-self.model.rest_canonical['rightUpperLeg'][0])*.5
        radius=max(.12,half_width+.08)
        a=((np.asarray(start)-self.origin)@self.turn)[[0,2]];b=((np.asarray(goal)-self.origin)@self.turn)[[0,2]]
        points=route(a,b,[(self.chair_min[[0,2]],self.chair_max[[0,2]])],radius)
        return [self.origin+self.turn@np.array([p[0],0.,p[1]]) for p in points]

    def change_phase(self,phase):
        self.phase=phase;self.elapsed=0.;self.locomotion.reset()

    def step(self,dt):
        dt=max(0.,min(.05,dt));self.elapsed+=dt;self.pose='idle'
        if self.old_simulation_hz>0:
            calm=self.phase=='seated' and not self.exit_requested and not self.model.hand_gesture and not getattr(self.model,'speaking_for_seat',False)
            self.model.hair_springs.simulation_hz=min(15. if calm else 30.,self.old_simulation_hz)
        if self.phase=='arrive':
            self.visibility=ease(self.elapsed/1.1)
            if self.elapsed>=1.1:self.change_phase('walk')
        elif self.phase in ('walk','leave','carry_walk'):
            target=self.route[self.route_index];delta=target-self.position;length=float(np.linalg.norm(delta))
            if length<.008:
                self.position=target.copy();self.route_index+=1
                if self.route_index>=len(self.route):self.change_phase('turn' if self.phase=='walk' else 'place_turn' if self.phase=='carry_walk' else 'depart')
            else:
                self.heading=math.degrees(math.atan2(delta[0],delta[2]))
                difference=(self.heading-self.current_angle+180)%360-180
                if abs(difference)<7:
                    from natural_walk import load_walk
                    distance=load_walk().travel_speed(self.model.data)*self.locomotion.advance(dt)
                    self.position+=delta/length*min(length,distance);self.pose='walk'
                else:self.locomotion.reset()
        elif self.phase=='turn':
            self.heading=self.facing
            if abs((self.current_angle-self.facing+180)%360-180)<1:self.change_phase('lower')
        elif self.phase=='lower':
            self.rig.phase='lower';self.rig.weight=ease(self.elapsed/1.5)
            self.position=self.stand*(1-self.rig.weight)+self.origin*self.rig.weight
            if self.elapsed>=1.5:self.rig.phase='idle';self.change_phase('equip' if self.desk else 'seated')
        elif self.phase=='equip':
            self.desk_visibility=ease(self.elapsed/1.2)
            if self.elapsed>=1.2:self.change_phase('seated')
        elif self.phase=='seated':
            returner=getattr(self.activity,'returner',None)
            if self.exit_requested and returner and not returner.ready:
                if returner.can_rise:returner.can_rise=False;self.change_phase('rise')
                elif not returner.standing and returner.stage=='align':self.change_phase('place_turn')
            elif self.exit_requested and (self.activity is None or self.activity.ready_to_leave):self.change_phase('unequip' if self.desk else 'rise')
        elif self.phase=='unequip':
            self.desk_visibility=1-ease(self.elapsed/1.2)
            if self.elapsed>=1.2:self.change_phase('rise')
        elif self.phase=='rise':
            self.rig.phase='rise';self.rig.weight=1-ease(self.elapsed/1.35)
            self.position=self.stand*(1-self.rig.weight)+self.origin*self.rig.weight
            if self.elapsed>=1.35:
                self.rig.phase='idle';returner=getattr(self.activity,'returner',None)
                if returner and not returner.ready and returner.standing:
                    self.route=returner.route;self.route_index=0;self.change_phase('carry_walk')
                else:
                    self.route=self.plan_route(self.position,np.zeros(3)) if self.mode=='work' else list(reversed(self.route[:-1]))+[np.zeros(3)]
                    self.route_index=0;self.change_phase('leave')
        elif self.phase=='place_turn':
            returner=self.activity.returner;self.heading=returner.heading
            if abs((self.current_angle-self.heading+180)%360-180)<1:
                self.change_phase('place');returner.stage='align';returner.clock=0.
        elif self.phase=='place':
            returner=self.activity.returner
            if returner.ready:
                if returner.standing:self.route=returner.exit_route;self.route_index=0;self.change_phase('leave')
                else:self.change_phase('seated')
        elif self.phase=='depart':
            self.heading=0.;self.visibility=getattr(self,'depart_visibility',1.)*(1-ease(self.elapsed/1.1))
            if self.elapsed>=1.1:
                self.done=True;self.model.seating=None;self.model.locomotion=self.old_locomotion
                self.model.hair_springs.simulation_hz=self.old_simulation_hz
        delta=(self.heading-self.current_angle+180)%360-180
        self.current_angle+=float(np.clip(delta,-180*dt,180*dt))
        if self.activity:self.activity.step(dt)
        return self.current_angle

    def draw(self):
        from OpenGL.GL import glPushMatrix,glPopMatrix,glTranslatef,glRotatef,glScalef
        slide=-4*(1-self.visibility)
        glPushMatrix();glTranslatef(slide,0,0);glTranslatef(*self.origin);glRotatef(self.facing-self.fit.yaw,0,1,0);glScalef(*([self.fit.scale]*3));glTranslatef(*(-self.fit.pivot));self.asset.draw(include=('chair',) if self.desk else ());glPopMatrix()
        if self.desk and self.desk_visibility>0:
            glPushMatrix();glTranslatef(*self.origin);glRotatef(self.facing,0,1,0);glTranslatef(4*(1-self.desk_visibility),0,4*(1-self.desk_visibility));self.workstation.draw();glPopMatrix()
        if self.table:
            glPushMatrix();glTranslatef(slide,0,0);glTranslatef(*self.table_position);glScalef(*([self.table_scale]*3));glTranslatef(0,-self.table_row['bounds']['min'][1],0);glRotatef(self.table_yaw,0,1,0);self.table.draw();glPopMatrix()
        if self.activity:self.activity.draw()

    def release(self):
        if self.activity:self.activity.release()
        self.contacts.release();self.model.furniture_contacts=None
        self.model.hair_springs.physics.environment=None
        self.asset.release()
        if self.table:self.table.release()
        self.model.seating=None;self.model.locomotion=self.old_locomotion
        self.model.hair_springs.simulation_hz=self.old_simulation_hz
