"""Bounded yaw: reverse through the viewer, with a gaze pause for flat skins."""
class YawTurn:
    def __init__(self):
        self.angle=0.;self.pause=0.;self.destination=0.;self.front=False

    def advance(self,target,dt,is_3d=True):
        target=max(-90.,min(90.,target));dt=max(0.,min(.05,dt))
        if abs(target-self.destination)>20:
            self.front=not is_3d and self.angle*target<0
            self.pause=0.;self.destination=target
        else:self.destination=target
        if self.pause>0:
            self.pause=max(0.,self.pause-dt);return self.angle
        goal=0. if self.front else target
        difference=goal-self.angle
        step=min(abs(difference),240.*dt)
        self.angle+=step if difference>0 else -step
        if self.front and abs(self.angle)<.01:
            self.front=False;self.pause=.15
        return self.angle
