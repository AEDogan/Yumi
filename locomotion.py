"""One accepted desktop movement clock, shared by both VRM views."""
import math
class Locomotion:
    def __init__(self):self.phase=0.;self.weight=0.;self.x=None
    def reset(self):self.weight=0.;self.x=None
    def advance(self,dt):
        dt=max(0.,min(.05,dt));self.weight=min(1.,self.weight+dt/.35)
        smooth=self.weight*self.weight*(3-2*self.weight)
        elapsed=dt*smooth*getattr(self,'speed_scale',1.);self.phase+=elapsed
        return elapsed

def ground_pixel(height):
    from grounding import ground_pixel as floor_pixel
    return floor_pixel(height)

def stride_step(window,direction,dt):
    model=window.overlay.avatar.model
    state=getattr(window,'locomotion',None)
    if state is None:
        state=window.locomotion=Locomotion()
    for view in (window.avatar,window.overlay.avatar):
        if view.model:view.model.locomotion=state
    elapsed=state.advance(dt)
    if model:
        from natural_walk import load_walk
        foot_depth=sum(model.rest_canonical[side+'Foot'][2] for side in ('left','right'))/2
        depth=max(1.,8.5-foot_depth)
        pixels=window.overlay.avatar.height()/(2*depth*math.tan(math.radians(35)/2))
        speed=load_walk().travel_speed(model.data)*pixels
    else:speed=100.
    window.avatar.walk_direction=direction;window.avatar.walking_turn=True
    window.manual_pose='walk';window.manual_pose_end=__import__('time').perf_counter()+.25
    return direction*speed*elapsed

def halt(window):
    if getattr(window,'locomotion',None):window.locomotion.reset()
