"""Debounced activity decisions; motion and object cleanup belong to scenes."""
import time

SCENARIOS={'kitap oku':'reading','film izle':'tv','tv izle':'tv','toplantıya katıl':'meeting',
           'kahve yap':'coffee','pencereden bak':'window','dinlen':'rest','yazı yaz':'typing',
           'kod yaz':'coding','webde oku':'browsing'}
MEETING_APPS={'ms-teams.exe','teams.exe','zoom.exe','webex.exe'}
CODING_APPS={'code.exe','cursor.exe','pycharm64.exe','idea64.exe','devenv.exe','rider64.exe','antigravity.exe'}
BROWSERS={'chrome.exe','msedge.exe','firefox.exe','brave.exe','opera.exe'}

def choose_scenario(sample,media,elapsed_quiet,manual=None):
    if manual:return manual
    app=sample.get('name','')
    if app in MEETING_APPS:return 'meeting'
    if app in {'vlc.exe','mpv.exe','potplayer64.exe','netflix.exe'}:return 'tv'
    if sample.get('keys',0)>=4:return 'coding' if app in CODING_APPS else 'typing'
    if app in CODING_APPS and sample.get('idle',0)<150:return 'coding'
    if media.get('playing') and media.get('kind')=='video':return 'tv'
    if app in BROWSERS and sample.get('idle',0)<150 and sample.get('keys',0)<4:return 'browsing'
    if media.get('playing'):return 'passive'
    idle=sample.get('idle',0.)
    if idle>=600:return 'coffee'
    if idle>=150:return 'rest'
    return None


class DailyDirector:
    def __init__(self,owner):
        self.owner=owner;self.manual=None;self.current=None;self.scene=None
        self.candidate=None;self.candidate_since=0.;self.next_sample=0.;self.next_keys=0.
        self.sample={'idle':0.,'keys':0.,'name':''};self.cooldown=0.;self.suppressed_until=0.
        self.media={}
    def switch_workspace(self,scenario):
        existing=self.owner.overlay.avatar.furniture
        desk={'typing','coding','browsing'}
        if existing and existing.activity and not existing.exit_requested and existing.activity.kind in desk and scenario in desk:
            if existing.activity.kind!=scenario:
                from scenario_activity import ScenarioActivity
                existing.activity.release();existing.activity=ScenarioActivity(existing,scenario)
            self.scene=existing;self.current=scenario
            return True
        return False
    def command(self,scenario):
        self.manual=scenario;self.candidate=None;self.candidate_since=0.;self.cooldown=0.
        self.suppressed_until=0.
        if self.switch_workspace(scenario):return
        existing=self.owner.overlay.avatar.furniture
        if existing is not None:
            self.scene=existing
            if existing.activity and existing.activity.kind==scenario and not existing.exit_requested:
                self.current=scenario;return
            existing.request_exit()
    def cancel(self,now=None):
        self.manual=None;self.current=None;self.suppressed_until=(time.perf_counter() if now is None else now)+30
        if self.scene and not self.scene.done:self.scene.request_exit()
    def tick(self,now):
        o=self.owner;avatar=o.overlay.avatar
        if not o.settings.get('daily_scenarios',True) and not self.manual:return
        if getattr(getattr(o,'fullscreen_pause',None),'paused',False):return
        if not avatar.model or not o.overlay.isVisible() or o.overlay.drag is not None:return
        if now<self.suppressed_until:return
        if now>=self.next_keys:
            o.activity.sample();self.next_keys=now+.08
        if now>=self.next_sample:
            self.sample=o.activity.snapshot();self.next_sample=now+1.
            self.media=dict(getattr(getattr(o,'media_activity',None),'state',{}))
            if not self.media.get('playing') and o.system_audio.sample()>.008:self.media={'playing':True,'kind':'unknown'}
        scene=avatar.furniture
        if scene is None and self.scene is not None:
            self.scene=None;self.current=None;self.cooldown=now+2.
        # Explicit furniture/actions take priority; never replace somebody's seat.
        if scene is not None and scene is not self.scene:return
        if o.busy or o.avatar.speaking or getattr(o,'pending_avatar_command',None):return
        music=getattr(o,'music_runtime',None)
        if music and music.enabled and music.mode in ('dance','pole') and (music.origin=='manual' or music.active):return
        media=self.media
        desired=choose_scenario(self.sample,media,self.sample.get('idle',0),self.manual)
        if self.current in ('typing','coding','browsing') and desired is None and self.sample.get('idle',0)<30:desired=self.current
        if self.current=='coffee' and desired=='coffee':return
        if desired=='passive':desired=None
        if desired!=self.candidate:self.candidate=desired;self.candidate_since=now;return
        delay=0. if self.manual else 2. if desired is None else 5.
        if now-self.candidate_since<delay or now<self.cooldown:return
        if desired==self.current:return
        if scene is not None:
            if self.switch_workspace(desired):return
            scene.request_exit();return
        if desired is None:return
        # Reuse the tested approach/sit/stand route. Per-scenario poses/props
        # are attached only after the selected seat fits this actual character.
        from furniture_scene import FurnitureScene
        from scenario_activity import ScenarioActivity
        mode='work' if desired in ('typing','coding','browsing','meeting') else 'lounge'
        try:
            if desired in ('coffee','window'):
                from coffee_scene import CoffeeScene
                scene=CoffeeScene(avatar.model,desired,city=o.settings.get('city',''))
            else:
                scene=FurnitureScene(avatar.model,getattr(avatar,'previous_chair',None),mode=mode)
                scene.activity=ScenarioActivity(scene,desired)
        except (OSError,ValueError) as error:
            if 'scene' in locals():scene.release()
            self.cooldown=now+30.;o.set_status('Senaryo açılamadı: '+str(error));return
        avatar.furniture=scene;avatar.previous_chair=scene.fit.item['id']
        self.scene=scene;self.current=desired
        o.manual_pose='idle';o.manual_pose_end=now+1.
