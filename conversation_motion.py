"""Text-guided procedural gestures and audio-clock driven Turkish mouth cues."""
import hashlib
import math
import re

INTENTS = {
    'greeting': ('merhaba', 'selam', 'günaydın', 'hoş geldin'),
    'happy': ('sevindim', 'harika', 'güzel', 'tebrik', 'muhteşem'),
    'sad': ('üzgün', 'üzüldüm', 'maalesef', 'başın sağ'),
    'sorry': ('özür', 'kusura', 'pardon'),
    'thanks': ('teşekkür', 'sağ ol', 'sağol', 'minnet'),
    'warning': ('dikkat', 'tehlike', 'sakın', 'uyarı'),
    'uncertain': ('belki', 'emin değil', 'sanırım', 'bilmiyorum'),
    'encourage': ('başarabilir', 'yanındayım', 'merak etme', 'birlikte'),
    'agree': ('evet', 'haklısın', 'katılıyorum', 'tabii', 'tamamdır', 'tamam', 'anlaştık', 'olur'),
    'disagree': ('hayır', 'katılmıyorum', 'olmaz'),
    'question': ('?', 'nasıl', 'hangi', 'neden'),
    'explain': (),
}
VOWELS = {'a':'aa','ı':'aa','e':'ee','i':'ih','o':'oh','ö':'oh','u':'ou','ü':'ou'}

def classify(text):
    lower=text.replace('İ','i').casefold()
    # A quoted/negated agreement must not win over an explicit refusal.
    order=('disagree',)+tuple(name for name in INTENTS if name!='disagree')
    return next((name for name in order if any(re.search(r'(?<!\w)'+re.escape(word),lower) for word in INTENTS[name])), 'explain')

def variants():
    """288 bounded combinations, each with its own timing, side and amplitude."""
    return [(intent, variant) for intent in INTENTS for variant in range(24)]

class ConversationMotion:
    def __init__(self):
        self.text=''; self.intent='explain'; self.variant=0; self.serial=0
        self.position=0.; self.duration=0.; self.boundaries=[]
        self.waist={};self.fitted_data=None

    def fit(self,rest,data,physics):
        """Cache a conservative clothed waist contact from the existing skin samples."""
        import numpy as np
        self.fitted_data=data
        hips=rest['hips'];chest=rest.get('chest',rest.get('spine',hips))
        y=hips[1]+(chest[1]-hips[1])*.38
        points,dominant=physics.samples
        torso=[data.bones[n] for n in ('hips','spine','chest') if n in data.bones]
        points=(points[np.isin(dominant,torso)]@data.flip.T-data.origin)*data.scale
        for side in ('left','right'):
            shoulder=rest[side+'UpperArm'];sign=1 if shoulder[0]>=hips[0] else -1
            reach=np.linalg.norm(rest[side+'LowerArm']-shoulder)+np.linalg.norm(rest[side+'Hand']-rest[side+'LowerArm'])
            band=points[(abs(points[:,1]-y)<reach*.13)&((points[:,0]-hips[0])*sign>0)]
            width=float(np.percentile(abs(band[:,0]-hips[0]),85)) if len(band)>8 else abs(shoulder[0]-hips[0])*.82
            # Broad capes are not a torso. Keep ambiguous geometry a safe
            # approximation rather than reaching deep into an outfit.
            width=float(np.clip(width,abs(shoulder[0]-hips[0])*.65,reach*.42))
            self.waist[side]=np.array([hips[0]+sign*(width+reach*.065),y,shoulder[2]+reach*.07])

    def begin(self,text,boundaries=()):
        self.text=text; self.intent=classify(text); self.serial+=1
        self.variant=int.from_bytes(hashlib.sha256((text+str(self.serial)).encode()).digest()[:4],'big')%24
        self.position=0.; self.duration=0.; self.boundaries=list(boundaries)

    def sample(self,level):
        t=max(0.,self.position); variant=self.variant; side=1 if variant%2 else -1
        speed=.8+(variant//2)*.045; strength=.65+(variant%6)*.07
        beat=math.sin(t*3.2*speed); pulse=math.sin(math.pi*min(1.,t/.3)) if t<.3 else 1.
        end=min(1.,max(0.,(self.duration-t)/.3)) if self.duration else 1.
        weight=pulse*end*strength
        # Joint-local rotations in radians; upper arm twists remain small.
        bones={'chest':(.018*beat,0,side*.025*beat), 'head':(.035*beat,side*.035,side*.025),
               'leftUpperArm':(-.07*max(0,beat),0,-.035), 'rightUpperArm':(-.07*max(0,-beat),0,.035),
               'leftLowerArm':(-.15-.08*beat,0,0), 'rightLowerArm':(-.15+.08*beat,0,0)}
        face={}; intent=self.intent
        if intent in ('happy','greeting','thanks','encourage'):
            face['happy']=.25 if intent!='happy' else .48
            bones['head']=(-.03+.04*beat,side*.035,side*.06)
        if intent in ('sad','sorry'):
            face['sad']=.4; bones['head']=(.12,0,side*.035); bones['chest']=(.045,0,0)
        if intent in ('question','uncertain'):
            face['surprised']=.18; bones['head']=(.025,side*.055,side*.11)
            bones[('left' if side<0 else 'right')+'LowerArm']=(-.35-.05*beat,0,0)
        if intent=='warning':
            face['angry']=.15; bones['head']=(-.025,0,0)
            bones[('left' if side<0 else 'right')+'LowerArm']=(-.4,0,0)
        if intent=='agree':bones['head']=(.09*beat,0,0)
        if intent=='disagree':bones['head']=(0,.13*beat,0)
        if intent=='thanks':bones['chest']=(.06,0,0)
        # Subtle asymmetry and independent eye timing make expressions vary
        # without requiring custom face meshes or extra inference calls.
        squint=.018+(variant//6)*.012
        face['blinkLeft']=squint*(1+.18*side*beat)
        face['blinkRight']=squint*(1-.18*side*beat)
        if intent in ('happy','greeting','encourage'):face['relaxed']=.03+.004*variant
        if intent in ('sad','sorry'):face['lookDown']=.07+.003*variant
        # Independent authored controls only resolve on rigs that have them.
        # A brief expression accent follows the phrase instead of pumping
        # cheeks and brows periodically throughout every sentence.
        accent=math.exp(-((t-(.8+(variant%3)*.25))/1.15)**2)
        if intent in ('question','uncertain'):
            face['browInnerUp']=.12*accent
            face['browOuterUpLeft' if side<0 else 'browOuterUpRight']=.20*accent
        elif intent in ('happy','greeting','thanks','encourage'):
            for eye in ('Left','Right'):
                face['cheekSquint'+eye]=.13*accent
                face['eyeSquint'+eye]=.045*accent
        elif intent in ('sad','sorry'):
            face['browInnerUp']=.20*accent
        elif intent=='warning':
            for eye in ('Left','Right'):
                face['browDown'+eye]=.16*accent;face['eyeWide'+eye]=.06*accent
        # Mouth follows the actual playback clock, never the render clock.
        word=''; fraction=0.
        for start,duration,text in self.boundaries:
            if start<=t<start+duration:
                word=text; fraction=(t-start)/max(duration,.001); break
        if not self.boundaries and self.text:
            word=self.text; fraction=min(.999,t/max(self.duration,len(self.text)/14.,.1))
        lips={}
        if word and level>.015:
            index=min(len(word)-1,int(fraction*len(word))); char=word[index].casefold()
            shape=VOWELS.get(char)
            if shape is None and char not in 'mbp .,!?:;':
                shape=next((VOWELS[c.casefold()] for c in word[max(0,index-1):index+2] if c.casefold() in VOWELS),'aa')
            if shape:lips[shape]=min(.85,max(0.,level))
        if not lips and level>.015:lips['aa']=min(.85,level)
        return {name:tuple(a*weight for a in angles) for name,angles in bones.items() if 'Arm' not in name}, {name:value*weight for name,value in face.items()}, lips

    def arm_targets(self,rest,style=None):
        import numpy as np
        from joint_limits import safe_arm
        result={};t=self.position;speed=.8+(self.variant//2)*.045
        # Two quiet, unequal phrases avoid a metronomic mirrored arm pump.
        emphasis=.5+.35*math.sin(t*2.1*speed)+.15*math.sin(t*.83+1.2)
        for side,sign in (('left',1),('right',-1)):
            if not all(side+part in rest for part in ('UpperArm','LowerArm','Hand')):continue
            shoulder=rest[side+'UpperArm'];center=rest.get('hips',np.zeros(3));sign=1 if shoulder[0]>=center[0] else -1
            a=float(np.linalg.norm(rest[side+'LowerArm']-shoulder));b=float(np.linalg.norm(rest[side+'Hand']-rest[side+'LowerArm']));reach=a+b
            hand=shoulder+np.array([sign*reach*.07,-reach*.94,reach*.09])
            pole=[sign*.18,-1.,.30]
            selected=(self.variant%2==0)==(side=='left')
            if selected and self.intent in ('question','explain','warning','uncertain','encourage'):
                hand=shoulder+np.array([sign*reach*.10,-reach*(.72-.035*emphasis),reach*(.31+.035*emphasis)])
            if selected and self.intent in ('greeting','happy'):
                hand=shoulder+np.array([sign*reach*.19,-reach*.27,reach*.43])
            if selected and style in ('thumbs_up','ok','point'):
                hand=shoulder+np.array([sign*reach*.15,-reach*.38,reach*.49])
            if selected and style=='point':
                hand=shoulder+np.array([sign*reach*.13,-reach*.39,reach*.66])
            if style=='open_palm':
                hand=shoulder+np.array([sign*reach*(.13 if selected else .09),-reach*(.64 if selected else .73),reach*(.43 if selected else .32)])
            if style=='shrug':hand=shoulder+np.array([sign*reach*.23,-reach*.56,reach*.40])
            if selected and style=='hip':
                hip=rest.get(side+'UpperLeg',center)
                hand=self.waist.get(side,np.array([hip[0]+sign*reach*.16,center[1]+reach*.32,shoulder[2]+reach*.07])).copy()
                pole=[sign*1.,-.20,-.12]
            # A downward elbow pole keeps speech gestures close to the ribs.
            # The old outward pole lifted the elbow above a chest-level hand.
            elbow,hand=safe_arm(shoulder,hand,a,b,sign,pole=pole)
            result[side+'UpperArm']=shoulder;result[side+'LowerArm']=elbow;result[side+'Hand']=hand
        return result
