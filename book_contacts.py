"""Book fingertip fitting against the actual opened, animated asset triangles."""
import numpy as np

def nearest_surface(point,triangles):
    a,b,c=triangles[:,0],triangles[:,1],triangles[:,2]
    ab=b-a;ac=c-a;normal=np.cross(ab,ac);n2=np.sum(normal*normal,axis=1)
    projected=point-normal*(np.sum((point-a)*normal,axis=1)/np.maximum(n2,1e-20))[:,None]
    ap=projected-a;aa=np.sum(ab*ab,axis=1);bb=np.sum(ab*ac,axis=1);cc=np.sum(ac*ac,axis=1)
    pa=np.sum(ap*ab,axis=1);pc=np.sum(ap*ac,axis=1);det=aa*cc-bb*bb
    u=(pa*cc-pc*bb)/np.maximum(det,1e-20);v=(pc*aa-pa*bb)/np.maximum(det,1e-20)
    valid=(n2>1e-16)&(u>=0)&(v>=0)&(u+v<=1)
    candidates=[np.where(valid[:,None],projected,np.inf)]
    for start,end in ((a,b),(b,c),(c,a)):
        edge=end-start;t=np.clip(np.sum((point-start)*edge,axis=1)/np.maximum(np.sum(edge*edge,axis=1),1e-20),0,1)
        candidates.append(start+t[:,None]*edge)
    candidates=np.concatenate(candidates);distances=np.sum((candidates-point)**2,axis=1)
    return candidates[int(np.argmin(distances))]

class BookContacts:
    def __init__(self,activity):
        self.activity=activity;asset=activity.assets['book'];transforms=asset.animation_matrices(3.)
        triangles=[]
        for part in asset.parts:
            p=(np.c_[part['pos'],np.ones(len(part['pos']))]@transforms[part['node']].T)[:,:3]
            triangles.append(p[part['indices'].reshape(-1,3)])
        self.triangles=np.concatenate(triangles);self.stats={}

    def matrix(self,model,world):
        from hand_pose import turn
        a=self.activity;asset=a.assets['book'];_,width=a.reading_target(model,world)
        sign=1 if model.rest_canonical['leftUpperArm'][0]>=model.rest_canonical['hips'][0] else -1
        center=a.hand(world,'left')-np.array([sign*width*.55,.018,-.02])
        origin=(asset.minimum+asset.maximum)*.5;origin[1]=asset.minimum[1]
        m=np.eye(4);m[:3,:3]=turn(np.array([1.,0.,0.]),np.radians(-48))*width/asset.extent[0]
        m[:3,3]=center-m[:3,:3]@origin
        return m

    def align_palms(self,model,world):
        from hand_pose import frame,turn
        from joint_limits import limit_forearm,limit_rotation
        d=model.data;p=model.hair_springs.physics
        normal=turn(np.array([1.,0.,0.]),np.radians(-48))@np.array([0.,1.,0.])
        for side in ('left','right'):
            if side=='right' and self.activity.event=='page':continue
            if side not in model.hand_poses.hands:continue
            hand,basis,sign=model.hand_poses.hands[side]
            forearm=d.bones[side+'LowerArm'];parent=world[d.parents[forearm],:3,:3]
            axis=world[hand,:3,3]-world[forearm,:3,3];axis/=max(np.linalg.norm(axis),1e-12)
            rest_axis=np.linalg.solve(d.rest[forearm,:3,:3],d.rest[hand,:3,3]-d.rest[forearm,:3,3])
            desired=d.flip.T@(frame(np.array([-sign,0.,0.]),normal)@basis.T)@d.flip@d.rest[hand,:3,:3]
            base=world[forearm,:3,:3].copy();best=None
            for angle in np.linspace(-np.pi*.5,np.pi*.5,13):
                candidate=turn(axis,angle)@base
                bounded=parent@limit_forearm(d.local[forearm][:3,:3],np.linalg.solve(parent,candidate),rest_axis)
                if np.linalg.norm(bounded-candidate)>.0001:continue
                wrist=candidate@limit_rotation(d.local[hand][:3,:3],np.linalg.solve(candidate,desired),35.)
                cost=np.linalg.norm(wrist-desired)+.015*abs(angle)
                if best is None or cost<best[0]:best=(cost,candidate,wrist)
            if best is not None:
                p._rotate_subtree(world,forearm,best[1]@np.linalg.inv(world[forearm,:3,:3]))
                p._rotate_subtree(world,hand,best[2]@np.linalg.inv(world[hand,:3,:3]))
                model.hand_poses.fingers(world,side,'book_grip',self.activity.weight)

    def solve(self,model,world):
        from finger_contacts import reach_tip
        d=model.data;a=self.activity
        # Turning pages change geometry; leave the reaching hand free during
        # that event rather than fitting it to an obsolete open-page surface.
        if a.cleanup:return
        self.align_palms(model,world)
        matrix=self.matrix(model,world)
        triangles=self.triangles@matrix[:3,:3].T+matrix[:3,3]
        gaps=[];initial=[];attempts=0;outside=0
        for side in ('left','right'):
            if side=='right' and a.event=='page':continue
            for finger in ('Index','Middle','Ring','Little','Thumb'):
                chain=model.hand_poses.chain(side,finger)
                if any(n is None for n in chain):continue
                last=chain[-1];extension=np.linalg.solve(d.rest[last,:3,:3],(d.rest[last,:3,3]-d.rest[chain[-2],:3,3])*.7)
                def point():return ((world[last,:3,3]+world[last,:3,:3]@extension)@d.flip.T-d.origin)*d.scale
                start=point();surface=nearest_surface(start,triangles);delta=start-surface;distance=np.linalg.norm(delta)
                if distance>.045:outside+=1;continue
                target=surface+delta/max(distance,1e-10)*.002
                snapshot=world.copy()
                reach_tip(model,world,side,finger,d.flip.T@(target/d.scale+d.origin))
                gap=float(np.linalg.norm(point()-nearest_surface(point(),triangles)))
                if gap>max(distance,.0025):world[:]=snapshot;continue
                attempts+=1;initial.append(float(distance));gaps.append(gap)
        self.stats={'fitted':attempts,'outside_workspace':outside,'initial_max_tip_gap':max(initial,default=None),'max_tip_gap':max(gaps,default=None)}
