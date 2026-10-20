"""Blend a reviewed capture into the genre repertoire without changing its clock."""
from pathlib import Path
import hashlib,math
import numpy as np
from dance_motion import DanceMotion
from vrma import slerp
from natural_walk import matrix_quaternion
from vrm import rotation

# These are source dance styles, not claims that a music genre has one dance.
CAPTURE_STYLES={'pop':'popping','k-pop':'la-hip-hop','hip-hop':'hip-hop','r&b':'la-hip-hop',
                'house':'house','techno':'house','trance':'waacking','disco':'waacking',
                'funk':'locking','jazz':'jazz','drum & bass':'house','salsa':'salsa','latin pop':'salsa',
                'rock':'locking','metal':'locking','reggae':'la-hip-hop','reggaeton':'hip-hop',
                'afrobeats':'hip-hop','bachata':'salsa','country':'jazz'}
VARIATIONS={'pop':'la-hip-hop','rock':'hip-hop','hip-hop':'la-hip-hop','r&b':'jazz',
            'house':'locking','techno':'popping','trance':'house','disco':'locking',
            'funk':'popping','reggae':'jazz','reggaeton':'la-hip-hop','afrobeats':'house',
            'k-pop':'popping','country':'locking','jazz':'waacking','metal':'hip-hop','drum & bass':'locking'}
INTENSITY={'r&b':.82,'reggae':.74,'bachata':.82,'country':.88,'trance':.90}

class GenreDance(DanceMotion):
    path=Path('Yumi-Genre-Dance');max_root_offset=4.;uses_stage_bounds=True
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.capture=None;self.captures={};self.capture_weight=0.;self.max_root_offset=4.
    def frame_bounds(self,d):
        # All captured styles share a stable stage envelope across genre changes.
        from scene_framing import corners
        return corners([-2.,0.,-2.],[2.,4.2,2.]),corners([-2.,0.,-2.],[2.,0.,2.])
    def captured(self,style):
        if style not in self.captures:
            if style=='salsa':
                from captured_dance import CapturedDance
                self.captures[style]=CapturedDance()
            else:
                from aist_dance import AistDance
                self.captures[style]=AistDance(style)
        self.capture=self.captures[style]
        return self.capture
    def sample_style(self,t,d,style,loop):
        capture=CAPTURE_STYLES.get(style)
        if capture:
            offset=int.from_bytes(hashlib.sha256(style.encode()).digest()[:4],'big')%3000/30
            clock=t+offset;alternate=VARIATIONS.get(style,capture);phase=int(max(0.,t)//16)
            current,following=(capture,alternate) if phase%2==0 else (alternate,capture)
            result=self.captured(current).pose(clock,d,loop=True)
            u=float(np.clip((max(0.,t)%16-14.5)/1.5,0.,1.));u=u*u*(3-2*u)
            if u>0 and current!=following:
                other=self.captured(following).pose(clock,d,loop=True)
                result=self.blend(result,other,u,d)
            rotations={node:value.copy() for node,value in result[0].items()};strength=INTENSITY.get(style,1.)
            if strength<1:
                for name,node in d.bones.items():
                    if node in rotations and any(part in name for part in ('Arm','Shoulder','neck','head')):
                        rotations[node]=rotation(slerp(matrix_quaternion(d.local[node][:3,:3]),matrix_quaternion(rotations[node]),strength))
            # Small genre accents complement the captured body motion. Shared
            # source families are deliberately labelled as inspired variants.
            pulse=math.sin(t*math.tau)
            accents={'metal':('head',.13),'rock':('head',.07),'country':('chest',.025),
                     'reggae':('chest',.035),'reggaeton':('hips',.025),'afrobeats':('hips',.035),'bachata':('hips',.025)}
            if style in accents:
                name,amount=accents[style];node=d.bones.get(name)
                if node is not None:
                    from hand_pose import turn
                    axis=np.array([1.,0.,0.]) if name=='head' else np.array([0.,0.,1.])
                    base=d.rest[node,:3,:3];change=np.linalg.solve(base,d.flip.T@turn(axis,amount*pulse)@d.flip@base)
                    rotations[node]=rotations.get(node,d.local[node][:3,:3])@change
            return rotations,result[1],result[2]
        # Evaluate the requested procedural style without changing shared state.
        return self._pose(t,d,self._sample(t,style))
    @staticmethod
    def blend(a,b,weight,d):
        rotations={node:rotation(slerp(matrix_quaternion(a[0].get(node,d.local[node][:3,:3])),matrix_quaternion(b[0].get(node,d.local[node][:3,:3])),weight)) for node in a[0].keys()|b[0].keys()}
        face={name:a[2].get(name,0.)*(1-weight)+b[2].get(name,0.)*weight for name in a[2].keys()|b[2].keys()}
        return rotations,a[1]*(1-weight)+b[1]*weight,face
    def pose(self,t,d,loop=True):
        u=1. if self.changed is None else float(np.clip((t-self.changed)/1.5,0.,1.));u=u*u*(3-2*u)
        desired=float(self.style in CAPTURE_STYLES);previous=float(self.previous in CAPTURE_STYLES)
        self.capture_weight=previous*(1-u)+desired*u
        captured=self.sample_style(t,d,self.style,loop)
        if u>=.999:return captured
        generic=self.sample_style(t,d,self.previous,loop);weight=u
        rotations={}
        for node in generic[0].keys()|captured[0].keys():
            a=generic[0].get(node,d.local[node][:3,:3]);b=captured[0].get(node,d.local[node][:3,:3])
            rotations[node]=rotation(slerp(matrix_quaternion(a),matrix_quaternion(b),weight))
        expressions={name:generic[2].get(name,0.)*(1-weight)+captured[2].get(name,0.)*weight for name in generic[2].keys()|captured[2].keys()}
        return rotations,generic[1]*(1-weight)+captured[1]*weight,expressions
