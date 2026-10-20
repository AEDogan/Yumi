"""Separate desk, keyboard and display sizing from seated anatomy."""
import math
import numpy as np
from furniture_scene import rotation

class WorkstationFit:
    def __init__(self,asset,fit,model):
        self.asset=asset;self.source_rotation=rotation(-fit.yaw);r=model.rest_canonical
        hip_y=fit.height+fit.padding+fit.hip_offset;shoulder_width=abs(r['leftUpperArm'][0]-r['rightUpperArm'][0])
        uppers=[np.linalg.norm(r[s+'LowerArm']-r[s+'UpperArm']) for s in ('left','right')]
        lowers=[np.linalg.norm(r[s+'Hand']-r[s+'LowerArm']) for s in ('left','right')]
        upper=float(np.mean(uppers));lower=float(np.mean(lowers));shoulder=np.mean([r[s+'UpperArm'] for s in ('left','right')],axis=0)
        shoulder_y=hip_y+shoulder[1]-r['hips'][1]
        self.wrist=np.array([0.,shoulder_y-upper*.96,shoulder[2]+upper*.13+lower*.94])
        self.hand_spacing=shoulder_width*.42
        self.table_height=float(self.wrist[1]-.045)
        eyes=[r[s+'Eye'] for s in ('left','right') if s+'Eye' in r]
        eye=np.mean(eyes,axis=0) if eyes else r['head']+np.array([0.,.10,0.])
        self.eye_height=float(hip_y+eye[1]-r['hips'][1]);self.monitor_top=self.eye_height-.025
        self.width=max(shoulder_width*3.5,lower*3.3);self.depth=lower*2.25
        hand_length=float(np.mean([np.linalg.norm(r.get(s+'IndexProximal',r[s+'Hand'])-r[s+'Hand']) for s in ('left','right')]))
        self.keyboard_center=self.wrist+np.array([0.,-.035,max(.035,hand_length*.60)])
        self.monitor_distance=max(lower*1.8,self.keyboard_center[2]+lower*.85)
        # A centered display occludes the face in the viewer-facing desk pose.
        # Offset it toward the outer side, bounded to a 20-degree viewing angle
        # at the same eye height and distance; keep the keyboard centered.
        self.monitor_offset=-min(shoulder_width*.80,self.monitor_distance*math.tan(math.radians(20)))
        self.placements=[];self.floor=[]
        points={p['name']:p['pos']@self.source_rotation.T for p in asset.parts}
        structure=next(p for p in asset.parts if p['name'].casefold().startswith('table_white_wood'))
        structural_points=points[structure['name']];lo=structural_points.min(0);hi=structural_points.max(0)
        extent=hi-lo;self.table_front=self.keyboard_center[2]-lower*.58
        for part in asset.parts:
            name=part['name'];key=name.casefold();cloud=points[name];minimum=cloud.min(0);maximum=cloud.max(0);center=(minimum+maximum)*.5
            if 'chair' in key or key.startswith(('metalic_legs','table_top','table_desk_wooden_stand')):continue
            anchor=center.copy();anchor[1]=minimum[1]
            if name==structure['name']:
                scale=np.array([self.width/extent[0],self.table_height/extent[1],self.depth/extent[2]])
                target=np.array([0.,0.,self.table_front+self.depth*.5])
                self.floor=[[-self.width*.5,0.,self.table_front],[self.width*.5,0.,self.table_front+self.depth]]
            elif 'display' in key:
                scale=np.repeat((self.monitor_top-self.table_height)/(maximum[1]-minimum[1]),3)
                target=np.array([self.monitor_offset,self.table_height,self.monitor_distance])
            elif 'keyboard' in key:
                scale=np.repeat(shoulder_width*1.18/max(.05,maximum[0]-minimum[0]),3)
                target=self.keyboard_center.copy();target[1]=self.table_height+.008
            elif 'mouse' in key:
                scale=np.repeat(lower*.23/max(.025,maximum[2]-minimum[2]),3)
                target=np.array([-shoulder_width*.85,self.table_height+.008,self.keyboard_center[2]])
            else:
                scale=np.repeat(min(self.width/extent[0],self.depth/extent[2])*1.15,3)
                target=np.array([center[0]*self.width/extent[0],self.table_height+.006,self.keyboard_center[2]+(center[2]-.028)*self.depth/extent[2]])
            self.placements.append((name,anchor,scale,target))
        yaw=math.degrees(math.atan2(self.source_rotation[0,2],self.source_rotation[2,2]))
        self.draw_placements={name:(anchor,scale,target,yaw) for name,anchor,scale,target in self.placements}

    def draw(self):
        self.asset.draw(placements=self.draw_placements)
