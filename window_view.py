"""A bounded outdoor view behind the window; weather fetching never blocks rendering."""
import math,random,threading,time
from datetime import datetime,timezone,timedelta

def daylight_state(weather,now=None):
    """Derive local dawn/day/dusk/night from the selected city's solar times."""
    solar=weather.get('solar',{})
    fallback={'phase':'night' if weather.get('night') else 'day','light':0. if weather.get('night') else 1.,'warmth':0.}
    try:
        zone=timezone(timedelta(seconds=int(solar['utc_offset_seconds'])))
        local=datetime.fromtimestamp(time.time() if now is None else now,zone).replace(tzinfo=None)
        rise=datetime.fromisoformat(solar['sunrise']).replace(tzinfo=None)
        setting=datetime.fromisoformat(solar['sunset']).replace(tzinfo=None)
        if not rise<setting or rise.date()!=local.date():return fallback
        r=(local-rise).total_seconds();s=(local-setting).total_seconds();span=1800.
        if abs(r)<=span:
            u=(r+span)/(span*2);return {'phase':'dawn','light':u*u*(3-2*u),'warmth':1-abs(r)/span}
        if abs(s)<=span:
            u=(s+span)/(span*2);return {'phase':'dusk','light':1-u*u*(3-2*u),'warmth':1-abs(s)/span}
        day=r>0 and s<0
        return {'phase':'day' if day else 'night','light':float(day),'warmth':0.}
    except (KeyError,ValueError,TypeError,OverflowError):return fallback

def weather_kind(code):
    if code in (95,96,99):return 'storm'
    if code in (71,73,75,77,85,86):return 'snow'
    if code in (51,53,55,56,57,61,63,65,66,67,80,81,82):return 'rain'
    if code in (45,48):return 'fog'
    if code==0:return 'clear'
    if code in (1,2,3):return 'cloudy'
    return 'unknown'

class WeatherCache:
    def __init__(self):self.entries={};self.pending=set();self.lock=threading.Lock()
    def request(self,city):
        city=str(city or '').strip()
        if not city:return
        with self.lock:
            cached=self.entries.get(city)
            if city in self.pending or (cached and time.monotonic()-cached[0]<900):return
            self.pending.add(city)
        def fetch():
            result={'kind':'unknown','night':False}
            try:
                from live_voice.weather_tool import get_weather
                data=get_weather(city)
                if not data.get('error'):
                    current=data.get('current',{});result={'kind':weather_kind(current.get('weather_code')),'night':current.get('is_day',1)==0,'solar':data.get('solar',{})}
            except Exception:
                # A decorative view must not interrupt the companion offline.
                pass
            finally:
                with self.lock:self.entries[city]=(time.monotonic(),result);self.pending.discard(city)
        threading.Thread(target=fetch,daemon=True,name='YumiWindowWeather').start()
    def snapshot(self,city):
        with self.lock:entry=self.entries.get(str(city or '').strip())
        if not entry or time.monotonic()-entry[0]>1800:return {'kind':'unknown','night':False}
        return entry[1].copy()

WEATHER=WeatherCache()

class WindowView:
    def __init__(self,city=''):
        self.city=city;self.variant=random.randrange(3);self.seed=random.randrange(100000)
        self.next_refresh=time.monotonic()+900
        WEATHER.request(city)
    def draw(self,asset,position,height,yaw,clock):
        import numpy as np
        from OpenGL.GL import (glPushAttrib,glPopAttrib,glPushMatrix,glPopMatrix,glTranslatef,glRotatef,glScalef,
            glDisable,glEnable,glBegin,glEnd,glColor3f,glVertex3f,glLineWidth,GL_ALL_ATTRIB_BITS,GL_LIGHTING,
            GL_TEXTURE_2D,GL_CULL_FACE,GL_QUADS,GL_TRIANGLE_FAN,GL_LINE_SMOOTH,GL_LINES)
        if time.monotonic()>=self.next_refresh:
            self.next_refresh=time.monotonic()+900;WEATHER.request(self.city)
        weather=WEATHER.snapshot(self.city);kind=weather['kind'];light=daylight_state(weather)
        night=light['light']<.5
        rain=kind in ('rain','storm');snow=kind=='snow';fog=kind=='fog'
        palette={'clear':(.48,.74,.94),'cloudy':(.62,.70,.77),'rain':(.35,.43,.52),
                 'storm':(.22,.28,.36),'snow':(.72,.77,.82),'fog':(.74,.78,.79),'unknown':(.67,.76,.82)}
        mix=lambda a,b,t:tuple(x*(1-t)+y*t for x,y in zip(a,b))
        sky=mix((.075,.10,.18),palette[kind],light['light'])
        warm=light['warmth']*(.35 if kind in ('rain','storm','fog') else .75)
        sky=mix(sky,(.90,.44,.33) if light['phase']=='dusk' else (.96,.68,.48),warm)
        scale=height/max(float(asset.extent[1]),.001)
        center=(asset.minimum+asset.maximum)*.5;center[1]=asset.minimum[1]
        # Authored window is in the YZ plane, not XY. Its normal is +X.
        width=float(asset.extent[2])*.84;bottom=float(asset.minimum[1]+asset.extent[1]*.095)
        top=float(asset.minimum[1]+asset.extent[1]*.91);depth=float(asset.minimum[0]-.008)
        def vertex(u,v,layer=0):glVertex3f(depth+layer,v,u)
        def quad(u0,v0,u1,v1,color,layer=0):
            glColor3f(*color);glBegin(GL_QUADS)
            for u,v in ((u0,v0),(u1,v0),(u1,v1),(u0,v1)):vertex(u,v,layer)
            glEnd()
        def polygon(points,color,layer):
            glColor3f(*color);glBegin(GL_TRIANGLE_FAN)
            for u,v in points:vertex(u,v,layer)
            glEnd()
        glPushAttrib(GL_ALL_ATTRIB_BITS);glDisable(GL_LIGHTING);glDisable(GL_TEXTURE_2D);glDisable(GL_CULL_FACE)
        glPushMatrix();glTranslatef(*position);glRotatef(yaw,0,1,0);glScalef(scale,scale,scale);glTranslatef(*(-center))
        try:
            # Vertical sky gradient makes low sunrise/sunset light visible.
            for band in range(12):
                v0=bottom+(top-bottom)*band/12;v1=bottom+(top-bottom)*(band+1)/12
                quad(-width/2,v0,width/2,v1,mix(sky,tuple(c*.62 for c in sky),band/12*.45))
            horizon=bottom+(top-bottom)*.37
            if kind=='clear' or (kind=='cloudy' and light['warmth']>.1):
                elevation=.41 if light['phase'] in ('dawn','dusk') else .77
                sun=((-width*.27 if light['phase']!='dusk' else width*.27),bottom+(top-bottom)*elevation);radius=width*.055
                polygon([(sun[0]+radius*math.cos(a),sun[1]+radius*math.sin(a)) for a in np.linspace(0,math.tau,25)],(.94,.92,.75) if night else (1.,.90,.58),.001)
            distant=(.36,.48,.53) if not night else (.10,.15,.22)
            ground=(.23,.39,.31) if not snow else (.89,.91,.93)
            if rain:ground=(.22,.30,.29)
            if fog:distant=(.63,.70,.70);ground=(.53,.63,.57)
            distant=tuple(c*(.25+.75*light['light']) for c in distant)
            ground=tuple(c*(.23+.77*light['light']) for c in ground)
            if self.variant==0:
                polygon([(-width/2,bottom),(-width/2,horizon),(-width*.25,horizon+.18),(0,horizon+.05),(width*.23,horizon+.24),(width/2,horizon),(width/2,bottom)],distant,.002)
                quad(-width/2,bottom,width/2,horizon-.04,ground,.003)
            elif self.variant==1:
                quad(-width/2,bottom,width/2,horizon,(.22,.40,.53) if not night else (.08,.17,.25),.002)
                glColor3f(.55,.65,.69);glLineWidth(1.);glBegin(GL_LINES)
                for j in range(9):
                    y=bottom+(horizon-bottom)*(j+1)/10;u=math.sin(j*2.4+self.seed)*width*.18
                    vertex(max(-width/2,u-width*.2),y,.003);vertex(min(width/2,u+width*.2),y,.003)
                glEnd()
            else:
                quad(-width/2,bottom,width/2,horizon-.03,ground,.002)
                for j in range(7):
                    u=-width/2+width*(j+.5)/7;h=.12+.05*math.sin(j+self.seed)
                    polygon([(u-width*.08,horizon-.07),(u,horizon+h),(u+width*.08,horizon-.07)],distant,.003)
            if kind in ('cloudy','rain','storm','snow','fog'):
                for j in range(3):
                    u=-width*.38+j*width*.29;v=top-(top-bottom)*(.10+.06*(j%2))
                    quad(u,v-width*.035,min(width/2,u+width*.24),v+width*.025,tuple(c*.92 for c in sky),.004)
            if rain or snow:
                rng=random.Random(self.seed);glLineWidth(1.2 if rain else 2.);glEnable(GL_LINE_SMOOTH)
                glColor3f(*((.73,.82,.89) if rain else (.98,.99,1.)));glBegin(GL_LINES)
                for _ in range(48 if rain else 30):
                    u=rng.uniform(-width/2,width/2);speed=.50 if rain else .09
                    v=bottom+(rng.random()*(top-bottom)-clock*speed)%(top-bottom)
                    length=.045 if rain else .006;end=max(bottom,v-length)
                    vertex(u,v,.006);vertex(min(width/2,u+.009) if rain else u,end,.006)
                glEnd()
        finally:glPopMatrix();glPopAttrib()
