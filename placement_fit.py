"""Close placement on the rendered prop through the same arm/contact solver."""
import numpy as np
from interaction_ik import solve_hand

def refine(returner,world):
    r=returner
    if r.stage!='reach' or r.clock<1.4:return
    m=r.model;key=r.keys[r.index];physics=m.hair_springs.physics
    sides=('left','right') if key in ('book','notebook') else ('left',) if key=='bowl' else ('right',)
    initial=np.array([r.hand(world,side) for side in sides])
    saved=getattr(r,'fitted_goals',{}).get(key)
    base=saved if saved is not None else initial
    target=r.local_target(key)
    def pose(delta):
        trial=world.copy()
        for side,goal in zip(sides,base+delta):solve_hand(m,trial,side,goal,returning=True,preserve_elbow=True)
        if key=='mug':
            r.activity.cup_grip.align_forearm(trial);m.hand_poses.apply(trial,'cup_grip',selected='right')
        physics.solve_arms(trial,gripping=True,preserve_grip=True)
        matrix=r.held_matrix(key,trial)
        cloud=(np.c_[r.bounds[key],np.ones(8)]@matrix.T)[:,:3]
        bottom=np.array([(cloud[:,0].min()+cloud[:,0].max())*.5,cloud[:,1].min(),(cloud[:,2].min()+cloud[:,2].max())*.5])
        return bottom-target,trial
    delta=np.zeros(3);error,best=pose(delta);jacobian=None
    for _ in range(2):
        if np.linalg.norm(error)<.008:break
        jacobian=np.column_stack([(pose(delta+axis*.003)[0]-error)/.003 for axis in np.eye(3)])
        step=np.linalg.solve(jacobian.T@jacobian+np.eye(3)*.003,-jacobian.T@error)
        step*=min(1.,.025/max(float(np.linalg.norm(step)),1e-9))
        improved=False
        for rate in (1.,.5,.25):
            candidate=delta+step*rate;residual,trial=pose(candidate)
            if np.linalg.norm(residual)<np.linalg.norm(error):delta=candidate;error=residual;best=trial;improved=True;break
        if not improved:break
    # Bound movement per displayed frame; never snap a prop to its destination.
    motion=max(float(np.linalg.norm(r.hand(best,side)-r.hand(world,side))) for side in sides)
    r.fit_report={'error':float(np.linalg.norm(error)),'residual':error.tolist(),'motion':motion,'accepted':motion<.075,'jacobian':None if jacobian is None else jacobian.tolist()}
    if motion<.075:
        world[:]=best
        if not hasattr(r,'fitted_goals'):r.fitted_goals={}
        r.fitted_goals[key]=base+delta
    physics.update(world)
