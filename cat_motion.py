"""Feline ear/tail animation on verified, skinned accessory chains.

Body-language reference: https://www.cats.org.uk/cats-blog/why-do-cats-have-tails
and https://www.cats.org.uk/help-and-advice/cat-behaviour/cat-body-language
Angles/timing are bounded animation choices, not inferred material mechanics.
"""
import math,re
import numpy as np
from hand_pose import turn

# lift, distributed curl, lateral sweep, Hz, ear back, ear out, tip flick
MOODS={
    'relaxed':(-38,5,2,.18,-5,3,1),
    'happy':(68,85,3,.28,-8,0,2),
    'curious':(12,4,2,.2,-18,0,12),
    'angry':(-18,4,27,1.1,40,28,10),
    'afraid':(-65,22,1,.16,55,35,1),
    'uneasy':(-40,10,12,.55,16,18,7),
    'sad':(-55,8,1,.13,5,25,1),
    'sleepy':(-48,18,.5,.12,0,10,.3),
}
def _ancestor(data,node):
    mapped=set(data.bones.values());seen=set()
    while node not in mapped and node in data.parents and node not in seen:
        seen.add(node);node=data.parents[node]
    return node if node in mapped else None

class CatRig:
    def __init__(self,data):
        self.tails=[];self.ears=[];self.controlled=set();self.data=data
        weighted=set()
        for part in data.parts:
            if part.get('skin') is None or 'joints' not in part:continue
            ids=np.unique(part['indices']);joints=data.skins[part['skin']][0][part['joints'][ids]]
            weighted.update(map(int,joints[part['weights'][ids]>1e-4]))
        descendants={}
        for node in reversed(data.order):
            descendants[node]={node}|set().union(*(descendants[c] for c in data.nodes[node].get('children',[])))
        hints={i:n.get('name','').casefold() for i,n in enumerate(data.nodes)}
        # A name alone is insufficient: require humanoid attachment and skin
        # support. Ponytails attach to the head, never the hips.
        tail={i for i,name in hints.items() if re.search(r'tail|shippo|尻尾|しっぽ|kuyruk',name)
            and not re.search(r'ponytail|hair',name) and _ancestor(data,i)==data.bones.get('hips')
            and bool(descendants[i]&weighted)}
        head=data.bones.get('head');head_y=data.rest[head,1,3] if head is not None else math.inf
        ear={i for i,name in hints.items() if re.search(r'catear|nekomimi|kemomimi|猫耳|獣耳|(^|[_ .-])(ear|ears|mimi)([_ .0-9-]|$)',name)
            and _ancestor(data,i)==head and data.rest[i,1,3]>head_y+.04/max(data.scale,1e-9)
            and bool(descendants[i]&weighted)}
        def outermost(nodes):
            result=[]
            for node in nodes:
                parent=data.parents.get(node)
                while parent is not None and parent not in nodes:parent=data.parents.get(parent)
                if parent is None:result.append(node)
            return sorted(result,key=data.order.index)
        for root in outermost(tail):
            chain=[];node=root
            while True:
                children=[c for c in data.nodes[node].get('children',[]) if c in descendants[root] and (descendants[c]&weighted or c in tail)]
                if len(children)!=1:break
                child=children[0]
                if np.linalg.norm(data.rest[child,:3,3]-data.rest[node,:3,3])*data.scale>1e-5:chain.append((node,child))
                node=child
            if len(chain)>=2:self.tails.append(chain);self.controlled.update(n for pair in chain for n in pair)
        for root in outermost(ear):
            x=(data.flip@data.rest[root,:3,3]-data.origin)[0]
            self.ears.append((root,1 if x>=0 else -1));self.controlled.update(descendants[root])
        self.report={'tail_chains':[[n for n,c in chain] for chain in self.tails],
            'ear_roots':[n for n,s in self.ears],'evidence':'accessory name + humanoid ancestry + indexed skin influence',
            'limits':['No new bones, fur, mesh deformation or physical coefficients were invented.']}

def emotion(text,intent):
    text=text.replace('İ','i').casefold()
    for mood,pattern in [('afraid',r'\b(korktum|korkuyorum|ürktüm|tedirginim)\b'),
                         ('angry',r'\b(sinirlendim|sinirliyim|kızgınım|öfkeliyim)\b')]:
        if re.search(pattern,text):return mood
    return {'greeting':'happy','happy':'happy','thanks':'happy','encourage':'happy',
        'sad':'sad','sorry':'sad','question':'curious','uncertain':'uneasy','warning':'curious'}.get(intent,'relaxed')

class CatMotion:
    def __init__(self,data):
        self.rig=CatRig(data);self.names=list(MOODS);self.weights=np.zeros(len(MOODS));self.weights[0]=1
        self.last=None;self.hold_until=-math.inf;self.held='relaxed';self.state='relaxed';self.previous={}
    @property
    def report(self):return self.rig.report
    def apply(self,t,world,model,pose,speaking):
        rig=self.rig;d=rig.data
        if not rig.tails and not rig.ears:return
        reset=self.last is None or t<self.last or t-self.last>.5
        if self.last is not None and t<self.last:self.hold_until=-math.inf;self.held='relaxed'
        dt=1/60 if reset else max(0.,t-self.last);self.last=t
        if reset:self.previous.clear()
        override=getattr(model,'cat_emotion',None)
        if override in MOODS:state=override
        elif speaking:
            conversation=model.conversation;state=emotion(conversation.text,conversation.intent)
            self.held=state;self.hold_until=t+4.
        elif pose=='listen':state='curious'
        elif t<self.hold_until:state=self.held
        elif getattr(getattr(model,'scenario_activity',None),'event',None)=='yawn':state='sleepy'
        else:state='relaxed'
        self.state=state;target=np.zeros(len(MOODS));target[self.names.index(state)]=1
        self.weights+=(target-self.weights)*(1-math.exp(-min(dt,.1)/.4))
        params=self.weights@np.asarray(list(MOODS.values()),float)
        lift,curl,sweep,hz,ear_back,ear_out,flick=params
        strength=.35 if pose=='clip' else 1.
        physics=model.hair_springs.physics;physics.update(world)
        from vrm import aim
        def basis(anchor):return world[anchor,:3,:3]@np.linalg.inv(d.rest[anchor,:3,:3])@d.flip.T
        axes=basis(d.bones['hips'])
        hip_frame=world[d.bones['hips'],:3,:3]@np.linalg.inv(d.rest[d.bones['hips'],:3,:3])
        for chain in rig.tails:
            for index,(node,child) in enumerate(chain):
                fraction=index/max(1,len(chain)-1);anchor=world[node,:3,3].copy();before=world[child,:3,3].copy()
                original=before-anchor;length=float(np.linalg.norm(original))
                pitch=lift+curl*fraction**3
                yaw=sweep*math.sin(t*math.tau*hz-fraction*.7)/(1+index*.65)
                # Curiosity is primarily a small tip movement, not dog-like
                # whole-tail happiness wagging. Smooth periodic accents.
                yaw+=flick*fraction**3*math.sin(t*3.4)*math.exp(-((t%4.2-1.7)/.65)**2)
                rotation=turn(axes[:,1],math.radians(yaw)*strength)@turn(axes[:,0],math.radians(pitch)*strength)
                neutral=hip_frame@(d.rest[child,:3,3]-d.rest[node,:3,3])
                desired=rotation@neutral/max(float(np.linalg.norm(neutral)),1e-9)*.9+original/max(length,1e-9)*.1
                predicted=anchor+desired/max(float(np.linalg.norm(desired)),1e-9)*length
                if node in physics.segment_radii:
                    predicted=physics.constrain_tip(node,anchor,predicted,length,before,math.radians(115),previous=self.previous.get(node))
                point=(d.flip@predicted-d.origin)*d.scale
                if point[1]<.025:
                    direction=(d.flip@(predicted-anchor))*d.scale;dy=.025-(d.flip@anchor-d.origin)[1]*d.scale
                    if abs(dy)<length*d.scale:
                        horizontal=direction[[0,2]];horizontal/=max(float(np.linalg.norm(horizontal)),1e-9)
                        direction[[0,2]]=horizontal*math.sqrt(max(0.,(length*d.scale)**2-dy**2));direction[1]=dy
                        predicted=anchor+d.flip.T@direction/d.scale
                physics._rotate_subtree(world,node,aim(original,predicted-anchor));self.previous[node]=world[child,:3,3].copy()
        axes=basis(d.bones['head'])
        for node,side in rig.ears:
            # Both ears flatten for fear; curious listening has a small,
            # independent orienting twitch instead of synchronized flapping.
            twitch=2.2*math.sin(t*2.7+side*.8)*math.exp(-((t%5.1-2.)/.3)**2)
            rotation=turn(axes[:,0],math.radians(-ear_back+twitch)*strength)@turn(axes[:,2],math.radians(-side*ear_out)*strength)
            physics._rotate_subtree(world,node,rotation)
        environment=getattr(physics,'environment',None)
        if environment is not None:environment.solve_springs(world,model.hair_springs,selected_nodes=rig.controlled)
