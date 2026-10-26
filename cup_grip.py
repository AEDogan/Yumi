"""Mug handle contact authored in asset space, fitted to anatomical fingers."""
import numpy as np
from hand_pose import unit,frame

class CupGrip:
    def __init__(self,model,asset):
        self.model=model;self.asset=asset;d=model.data;self.side='right'
        required=['right'+finger+joint for finger in ('Index','Middle','Little') for joint in ('Proximal','Intermediate')]
        if 'right' not in model.hand_poses.hands or any(name not in d.bones for name in required):
            raise ValueError('Bu modelin parmak iskeleti fincan tutuşunu desteklemiyor.')
        self.hand,self.basis,self.sign=model.hand_poses.hands[self.side]
        self.center=(asset.minimum+asset.maximum)*.5;self.center[1]=asset.minimum[1]
        # This asset's separate handle primitive lies on +X. The grip is the
        # outer handle bar, not the object's origin or the character's wrist.
        handle=asset.parts[1]['pos']
        self.anchor=np.array([handle[:,0].max()-.004,(handle[:,1].min()+handle[:,1].max())*.5,0.])
        palm=model.rest_canonical['rightIndexProximal']-model.rest_canonical['rightLittleProximal']
        self.height=float(np.clip(np.linalg.norm(palm)*2.1,.16,.25))
        self.scale=self.height/asset.extent[1]
        bind=d.rest.copy();model.hand_poses.fingers(bind,'right','cup_grip')
        contact=self.contact(bind)
        wrist=self.canonical(bind,self.hand)
        self.bind_offset=contact-wrist
        self.desired=frame(np.array([0.,0.,1.]),np.array([-self.sign,0.,0.]))@self.basis.T
        body=asset.parts[0]['pos'];self.rim_center=(body.min(0)+body.max(0))*.5
        self.rim_center[1]=body[:,1].max();self.rim_radius=(body.max(0)-body.min(0))[[0,2]]*.5
        from model_analysis import expression_mask
        candidates=[]
        for index,part in enumerate(d.parts):
            mask=expression_mask(d,index,'aa')
            if not np.any(mask):continue
            vertices=part['pos'][mask];points=np.c_[vertices,np.ones(len(vertices))]
            if part['skin'] is not None and 'joints' in part:
                nodes,inverse=d.skins[part['skin']];palette=d.rest[nodes]@inverse;posed=np.zeros_like(points)
                for k in range(4):posed+=np.einsum('nij,nj->ni',palette[part['joints'][mask,k]],points)*part['weights'][mask,k,None]
                vertices=posed[:,:3]
            else:vertices=(points@d.rest[part['node']].T)[:,:3]
            label=d.g['materials'][part['material']].get('name','').lower()
            candidates.append((0 if 'mouth' in label else 1,vertices.mean(0)))
        if candidates:mouth=min(candidates,key=lambda row:row[0])[1]
        else:mouth=d.rest[d.bones['head'],:3,3]+d.flip.T@np.array([0.,-.07,.09])/d.scale
        self.mouth_local=np.linalg.solve(d.rest[d.bones['head']],np.r_[mouth,1.])
        self.sip_solution=None;self.sip_mouth=None
    def canonical(self,world,node):
        d=self.model.data;return (world[node,:3,3]@d.flip.T-d.origin)*d.scale
    def contact(self,world):
        d=self.model.data
        nodes=[d.bones['right'+finger+'Intermediate'] for finger in ('Index','Middle')]
        point=np.mean([self.canonical(world,n) for n in nodes],axis=0)
        forward=unit(self.canonical(world,d.bones['rightMiddleProximal'])-self.canonical(world,self.hand))
        across=unit(self.canonical(world,d.bones['rightIndexProximal'])-self.canonical(world,d.bones['rightLittleProximal']))
        palm=unit(np.cross(forward,across))*self.sign
        return point+palm*.012
    def matrix(self,world):
        d=self.model.data
        across=unit(self.canonical(world,d.bones['rightIndexProximal'])-self.canonical(world,d.bones['rightLittleProximal']))
        forward=unit(self.canonical(world,d.bones['rightMiddleProximal'])-self.canonical(world,self.hand))
        x=-unit(np.cross(forward,across))*self.sign
        y=unit(across-x*float(across@x));z=unit(np.cross(x,y))
        rotation=np.column_stack((x,y,z))
        matrix=np.eye(4);matrix[:3,:3]=rotation*self.scale
        matrix[:3,3]=self.contact(world)-matrix[:3,:3]@self.anchor
        return matrix
    def wrist_for(self,base):
        # Upright desired cup: its handle points toward the outer right hand.
        rotation=np.diag([self.sign,1.,self.sign])
        grip=np.asarray(base)+rotation@((self.anchor-self.center)*self.scale)
        return grip-self.desired@self.bind_offset
    def mouth(self,world):
        d=self.model.data;raw=(world[d.bones['head']]@self.mouth_local)[:3]
        return (raw@d.flip.T-d.origin)*d.scale
    def rim(self,world):
        matrix=self.matrix(world);local=(np.linalg.inv(matrix)@np.r_[self.mouth(world),1.])[:3]
        direction=local[[0,2]]-self.rim_center[[0,2]];direction/=max(np.linalg.norm(direction),1e-9)
        point=self.rim_center.copy();point[[0,2]]+=direction*self.rim_radius
        return (matrix@np.r_[point,1.])[:3]
    def align_forearm(self,world):
        from hand_pose import turn
        from joint_limits import limit_forearm,limit_rotation
        d=self.model.data;b=d.bones['rightLowerArm'];c=self.hand;parent=world[d.parents[b],:3,:3]
        axis=unit(world[c,:3,3]-world[b,:3,3]);rest_axis=np.linalg.solve(d.rest[b,:3,:3],d.rest[c,:3,3]-d.rest[b,:3,3])
        forward=d.flip@axis;forward[1]=0.
        if np.linalg.norm(forward)<1e-6:forward=np.array([0.,0.,1.])
        forward=unit(forward);normal=-self.sign*unit(np.cross(np.array([0.,1.,0.]),forward))
        desired=d.flip.T@(frame(forward,normal)@self.basis.T)@d.flip@d.rest[c,:3,:3];base=world[b,:3,:3].copy();best=None
        for angle in np.linspace(-np.pi*.5,np.pi*.5,13):
            candidate=turn(axis,angle)@base;local=np.linalg.solve(parent,candidate)
            bounded=parent@limit_forearm(d.local[b][:3,:3],local,rest_axis)
            if np.linalg.norm(bounded-candidate)>.0001:continue
            hand=candidate@limit_rotation(d.local[c][:3,:3],np.linalg.solve(candidate,desired),35.)
            cost=np.linalg.norm(hand-desired)+.015*abs(angle)
            if best is None or cost<best[0]:best=(cost,candidate)
        if best is not None:self.model.hair_springs.physics._rotate_subtree(world,b,best[1]@np.linalg.inv(world[b,:3,:3]))
    def fit_pickup(self,world,target):
        """Fit the real constrained finger contact, rather than a bind offset."""
        from interaction_ik import solve_hand
        d=self.model.data;p=self.model.hair_springs.physics
        base=world.copy()
        pole=getattr(self,'pickup_pole',None)
        def evaluate(goal):
            trial=base.copy();solve_hand(self.model,trial,'right',goal,elbow_pole=pole)
            self.align_forearm(trial);self.model.hand_poses.apply(trial,'cup_grip',selected='right')
            p.solve_arms(trial,gripping=True)
            return self.contact(trial)-target,trial
        goal=getattr(self,'pickup_solution',self.canonical(world,self.hand)).copy()
        error,best=evaluate(goal)
        if np.linalg.norm(error)>.006:
            original_goal=goal.copy();best_pole=pole
            for bend in ([self.sign*.8,-.35,.1],[self.sign*.6,-.45,.85],[self.sign*.3,-1.,-.3]):
                pole=d.flip.T@np.asarray(bend,float)
                candidate,trial=evaluate(original_goal)
                if np.linalg.norm(candidate)<np.linalg.norm(error):error=candidate;best=trial;best_pole=pole
            pole=best_pole
        if np.linalg.norm(error)>.006:
            for offset in ([-.15,0,0],[.15,0,0],[0,0,-.15],[0,0,.15]):
                candidate_goal=goal+offset;candidate,trial=evaluate(candidate_goal)
                if np.linalg.norm(candidate)<np.linalg.norm(error):goal=candidate_goal;error=candidate;best=trial
        for _ in range(8):
            if np.linalg.norm(error)<.004:break
            jac=np.column_stack([(evaluate(goal+axis*.003)[0]-error)/.003 for axis in np.eye(3)])
            step=np.linalg.solve(jac.T@jac+np.eye(3)*.002,-jac.T@error)
            step*=min(1.,.08/max(np.linalg.norm(step),1e-10));improved=False
            for rate in (1.,.5,.25):
                candidate,trial=evaluate(goal+rate*step)
                if np.linalg.norm(candidate)<np.linalg.norm(error):goal=goal+rate*step;error=candidate;best=trial;improved=True;break
            if not improved:break
        # Retain the incoming pose if no physically bounded candidate improves it.
        if np.linalg.norm(error)<np.linalg.norm(self.contact(world)-target):world[:]=best
        self.pickup_solution=goal;self.pickup_pole=pole;self.pickup_error=float(np.linalg.norm(self.contact(world)-target))

    def sip_goal(self,world):
        """Solve the actual constrained arm/hand/rim chain, once per head pose."""
        mouth=self.mouth(world)
        if self.sip_solution is not None and np.linalg.norm(mouth-self.sip_mouth)<.015:return self.sip_solution
        from motion import ik
        from vrm import aim
        from joint_limits import limit_rotation
        from hand_pose import turn
        d=self.model.data;physics=self.model.hair_springs.physics
        a,b,c=[d.bones['right'+name] for name in ('UpperArm','LowerArm','Hand')]
        def posed(goal):
            trial=world.copy();shoulder,elbow,hand=[trial[n,:3,3].copy() for n in (a,b,c)]
            raw=d.flip.T@(goal/d.scale+d.origin)
            middle,end=ik(shoulder,raw,np.linalg.norm(elbow-shoulder),np.linalg.norm(hand-elbow),d.flip.T@np.array([self.sign*.22,-1.,.35]),132)
            physics._rotate_subtree(trial,a,aim(elbow-shoulder,middle-shoulder))
            neutral=trial[d.parents[b],:3,:3]@d.local[b][:3,:3]
            source=neutral@np.linalg.solve(d.rest[b,:3,:3],d.rest[c,:3,3]-d.rest[b,:3,3])
            desired=aim(source,end-trial[b,:3,3])@neutral;parent=trial[d.parents[b],:3,:3]
            desired=parent@limit_rotation(d.local[b][:3,:3],np.linalg.solve(parent,desired),134.)
            physics._rotate_subtree(trial,b,desired@np.linalg.inv(trial[b,:3,:3]))
            desired=trial[b,:3,:3]@np.linalg.solve(d.rest[b,:3,:3],d.rest[c,:3,:3])
            physics._rotate_subtree(trial,c,desired@np.linalg.inv(trial[c,:3,:3]))
            self.align_forearm(trial);self.model.hand_poses.apply(trial,'cup_grip',selected='right')
            parent=trial[d.parents[c],:3,:3];desired=d.flip.T@turn(np.array([1.,0.,0.]),-.24)@d.flip@trial[c,:3,:3]
            desired=parent@limit_rotation(d.local[c][:3,:3],np.linalg.solve(parent,desired),35.)
            physics._rotate_subtree(trial,c,desired@np.linalg.inv(trial[c,:3,:3]))
            return self.rim(trial)-self.mouth(trial)
        head=self.canonical(world,d.bones['head']);goal=head+np.array([self.sign*.06,-.20,.13])
        error=posed(goal)
        # Wrist bounds create several IK branches. Select a reachable starting
        # branch before taking small Jacobian steps toward the lip contact.
        for x in (-.20,0.,.20):
            for y in (-.32,-.20,-.08):
                for z in (.05,.15,.25):
                    candidate_goal=head+np.array([x,y,z]);candidate=posed(candidate_goal)
                    if np.linalg.norm(candidate)<np.linalg.norm(error):goal=candidate_goal;error=candidate
        for _ in range(14):
            if np.linalg.norm(error)<.004:break
            jacobian=np.column_stack([(posed(goal+axis*.003)-error)/.003 for axis in np.eye(3)])
            step=np.linalg.solve(jacobian.T@jacobian+np.eye(3)*.002,-jacobian.T@error)
            step*=min(1.,.08/max(np.linalg.norm(step),1e-9))
            improved=False
            for rate in (1.,.5,.25):
                trial=goal+step*rate;candidate=posed(trial)
                if np.linalg.norm(candidate)<np.linalg.norm(error):goal=trial;error=candidate;improved=True;break
            if not improved:break
        self.sip_solution=goal;self.sip_mouth=mouth.copy();self.sip_error=float(np.linalg.norm(error))
        return goal
    def meet_rim(self,world,amount):
        """A small deliberate head tilt closes the final lip/rim gap."""
        if amount<.85:return
        d=self.model.data;head=d.bones.get('head')
        if head is None:return
        mouth=self.mouth(world);rim=self.rim(world)
        if np.linalg.norm(rim-mouth)>.07:return
        from vrm import aim
        from joint_limits import limit_rotation
        pivot=self.canonical(world,head)
        change=aim(mouth-pivot,rim-pivot)
        change=limit_rotation(np.eye(3),change,8.*amount)
        raw=d.flip.T@change@d.flip
        self.model.hair_springs.physics._rotate_subtree(world,head,raw)
    def draw(self,world,opacity=1.):
        from OpenGL.GL import glPushMatrix,glPopMatrix,glMultMatrixd
        glPushMatrix();glMultMatrixd(self.matrix(world).T.copy());self.asset.draw(opacity=opacity);glPopMatrix()
