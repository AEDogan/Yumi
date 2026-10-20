"""Blend arm/finger changes from the displayed pose, including consecutive speech."""
import numpy as np
class ArmTransition:
    def __init__(self,data,physics):
        self.data=data;self.physics=physics;self.signature=None;self.entry={};self.started=0.
        self.last_final_time=None;self.final_active_until=0.
        chosen={node for name,node in data.bones.items() if any(part in name for part in ('Shoulder','UpperArm','LowerArm','Hand','Proximal','Intermediate','Distal','Metacarpal'))}
        self.nodes=[n for n in data.order if n in chosen]
        from joint_limits import rotation_limits
        self.limits=rotation_limits(data.bones)
    def apply(self,world,previous,t,signature):
        d=self.data
        if self.signature is None:self.signature=signature;return
        if signature!=self.signature:
            self.signature=signature;self.started=t
            self.entry={n:np.linalg.solve(previous[d.parents[n],:3,:3],previous[n,:3,:3]) if n in d.parents else previous[n,:3,:3].copy() for n in self.nodes}
        if not self.entry:return
        u=max(0.,min(1.,(t-self.started)/.5));u=u*u*(3-2*u)
        if u>=1:self.entry={};return
        from natural_walk import matrix_quaternion
        from vrma import slerp
        from vrm import rotation
        from joint_limits import limit_rotation
        targets={n:np.linalg.solve(world[d.parents[n],:3,:3],world[n,:3,:3]) if n in d.parents else world[n,:3,:3].copy() for n in self.nodes}
        for n in self.nodes:
            local=rotation(slerp(matrix_quaternion(self.entry[n]),matrix_quaternion(targets[n]),u))
            if n in self.limits:local=limit_rotation(d.local[n][:3,:3],local,self.limits[n])
            parent=world[d.parents[n],:3,:3] if n in d.parents else np.eye(3)
            self.physics._rotate_subtree(world,n,(parent@local)@np.linalg.inv(world[n,:3,:3]))

    def limit_final(self,world,previous,t,active):
        """Bound post-contact elbow branch changes, not only the input pose."""
        elapsed=.016 if self.last_final_time is None else max(.001,min(.1,t-self.last_final_time))
        self.last_final_time=t
        if active:self.final_active_until=t+.55
        if t>self.final_active_until:return
        d=self.data
        nodes=[n for n in self.nodes if any(d.bones.get(side+part)==n for side in ('left','right') for part in ('Shoulder','UpperArm','LowerArm','Hand'))]
        from natural_walk import matrix_quaternion
        from vrma import slerp
        from vrm import rotation
        original=world.copy()
        targets={n:np.linalg.solve(original[d.parents[n],:3,:3],original[n,:3,:3]) for n in nodes}
        entries={n:np.linalg.solve(previous[d.parents[n],:3,:3],previous[n,:3,:3]) for n in nodes}
        alpha=1.
        for _ in range(8):
            world[:]=original
            for n in nodes:
                local=rotation(slerp(matrix_quaternion(entries[n]),matrix_quaternion(targets[n]),alpha))
                parent=world[d.parents[n],:3,:3]
                self.physics._rotate_subtree(world,n,(parent@local)@np.linalg.inv(world[n,:3,:3]))
            safe=True
            for side in ('left','right'):
                hand=d.bones.get(side+'Hand');upper=d.bones.get(side+'UpperArm');lower=d.bones.get(side+'LowerArm')
                if any(n is None for n in (hand,upper,lower)):continue
                reach=np.linalg.norm(d.rest[lower,:3,3]-d.rest[upper,:3,3])+np.linalg.norm(d.rest[hand,:3,3]-d.rest[lower,:3,3])
                if np.linalg.norm(world[hand,:3,3]-previous[hand,:3,3])>reach*elapsed*1.65:safe=False
            if safe:return
            alpha*=.5
