"""Small standing coffee corner with a routed approach and a real counter."""
import numpy as np
from furniture_scene import FurnitureScene

class CoffeeScene(FurnitureScene):
    def __init__(self,model,kind='coffee',city=''):
        super().__init__(model,mode='lounge')
        if self.table:self.table.release();self.table=None
        self.kind=kind
        self.mode='coffee'
        from furniture_scene import rotation
        self.facing=-40.;self.turn=rotation(self.facing);self.forward=self.turn[:,2]
        # Coffee layout must not inherit a randomly chosen hidden chair's size.
        self.stand=np.array([-.8,0.,-.9]);self.origin=self.stand.copy()
        model.furniture_contacts=None;model.hair_springs.physics.environment=None
        r=model.rest_canonical
        self.counter_height=float(np.mean([r[s+'UpperArm'][1]-np.linalg.norm(r[s+'LowerArm']-r[s+'UpperArm'])*1.15 for s in ('left','right')]))
        width=abs(r['leftUpperArm'][0]-r['rightUpperArm'][0])
        self.walk_radius=max(.32,width*.5+.14)
        front=self.walk_radius+.08
        self.counter_radius=.52
        self.counter_center=np.array([0.,0.,front+self.counter_radius])
        self.counter_min=np.array([-.52,0.,front]);self.counter_max=np.array([.52,self.counter_height,front+1.04])
        self.machine_local=np.array([.10,self.counter_height,front+.38])
        self.cup_local=np.array([-.23,self.counter_height,front+.25])
        self.machine_yaw=self.facing+180.
        # Place the view behind the actor. A diagonal rear-facing gaze shows
        # the scenery without requiring a head turn beyond the neck's limits.
        self.window_local=self.turn.T@np.array([1.1,0.,-1.35])
        self.window_yaw=-75.
        from window_view import WindowView
        self.window_view=WindowView(city)
        from scenario_activity import ScenarioActivity
        try:self.activity=ScenarioActivity(self,kind)
        except (OSError,ValueError):self.release();raise
        counter=self.activity.assets['counter']
        self.counter_scale=np.array([1.04/counter.extent[0],self.counter_height/counter.extent[1],1.04/counter.extent[2]])
        self.counter_anchor=(counter.minimum+counter.maximum)*.5;self.counter_anchor[1]=counter.minimum[1]
        window=self.activity.assets['window'];scale=1.25/window.extent[1]
        # Conservative rotated footprint, shared by approach and exit routes.
        relative=rotation(self.window_yaw-self.facing)
        half=np.abs(relative)[np.ix_([0,2],[0,2])]@(window.extent[[0,2]]*scale*.5)
        self.obstacles=[(self.counter_min[[0,2]],self.counter_max[[0,2]]),
                        (self.window_local[[0,2]]-half,self.window_local[[0,2]]+half)]
        try:self.route=self.plan_route(np.zeros(3),self.stand)
        except ValueError:self.release();raise
        self.route_index=0
    def plan_route(self,start,goal):
        from scene_navigation import route
        first=((start-self.stand)@self.turn)[[0,2]]
        last=((goal-self.stand)@self.turn)[[0,2]]
        return [self.stand+self.turn@np.array([p[0],0.,p[1]]) for p in route(first,last,self.obstacles,self.walk_radius)]
    def change_phase(self,phase):
        if phase=='lower':
            self.rig.weight=0.;self.rig.phase='idle';phase='seated'
        elif phase=='rise':
            self.route=self.plan_route(self.position,np.zeros(3));self.route_index=0;phase='leave'
        super().change_phase(phase)
    def floor_points(self):
        points=np.array([[x,0.,z] for x in (self.counter_min[0],self.counter_max[0]) for z in (self.counter_min[2],self.counter_max[2])])
        return points@self.turn.T+self.stand
    def step(self,dt):
        angle=super().step(dt)
        if self.phase=='seated' and (self.kind=='window' or self.activity.clock>=21) and not self.exit_requested:
            direction=self.turn@self.window_local
            self.heading=float(np.degrees(np.arctan2(direction[0],direction[2])))
        self.rig.standing_attention=self.phase=='seated';self.rig.viewer_yaw=-self.current_angle
        return angle
    def draw(self):
        from OpenGL.GL import glPushMatrix,glPopMatrix,glTranslatef,glRotatef,glScalef
        slide=-4*(1-self.visibility)
        glPushMatrix();glTranslatef(slide,0,0);glTranslatef(*self.stand);glRotatef(self.facing,0,1,0)
        glTranslatef(*self.counter_center);glScalef(*self.counter_scale);glTranslatef(*(-self.counter_anchor))
        self.activity.assets['counter'].draw()
        glPopMatrix();self.activity.draw()
