"""Output-only music detection and explicit performances with stable lifetimes."""
import math,time
from music_analysis import OutputRhythm,genre_name
from music_clock import dance_rate
QUIET={'ambient','lo-fi','classical','folk'}

class MusicRuntime:
    def __init__(self,owner):
        self.owner=owner;self.output=OutputRhythm();self.enabled=False;self.active=False
        self.mode='listen';self.origin='manual';self.genre='unknown';self.genre_source='unknown'
        self.clock=0.;self.resume_clock=0.;self.motion=None;self.rate=1.;self.last_tick=None
        self.finishing=None;self.finish_clock=0.;self.resume_after_exit=False
        self.started_at=None;self.track_id=None;self.last_status=None;self.next_status=0.
        self.reported_error=None;self.last_beat=None;self.good_since=None;self.quiet_since=None
        self.auto_candidate=None;self.next_auto=0.;self.auto_suppressed=False;self.suppressed_track=None
        self.suppressed_quiet=None;self.next_probe=0.
    def start(self,mode='dance',origin='manual'):
        self.mode=mode;self.origin=origin;self.enabled=True;self.started_at=time.perf_counter()
        self.last_tick=self.started_at;self.clock=0.;self.resume_clock=0.;self.rate=1.
        self.last_beat=None;self.good_since=None;self.quiet_since=None;self.finishing=None
        self.active=False;self.track_id=None;self.reported_error=None;self.motion=None
        self.output.paused=False;self.output.start()
    def stop(self,suppress=True):
        if suppress:
            self.auto_suppressed=True;self.suppressed_track=self.track_id;self.suppressed_quiet=None
        self.output.stop()
        if self.active and self.motion.pole:self._finish(False);return True
        self.enabled=False;self._rest();return False
    def _finish(self,resume=False):
        if not resume:self.resume_after_exit=False
        if self.finishing is None:
            self.finishing=time.perf_counter();self.finish_clock=self.clock
            self.motion.release(self.clock);self.resume_after_exit=resume
    def _rest(self):
        # An explicit pole performance owns its scene until its release completes.
        # Listening/metadata updates are never allowed to tear down that owner.
        if self.active and self.motion.pole and self.enabled and self.finishing is None:return
        if self.active:
            self.resume_clock=self.clock;self.owner.manual_pose='idle';self.owner.manual_pose_end=time.perf_counter()+.6
        self.active=False;self.finishing=None
        for view in (self.owner.avatar,self.owner.overlay.avatar):
            if view.model:
                view.model.music_clip_time=None;view.model.music_listen=None;view.model.music_dance_accent=None
    def _apply(self):
        for view in (self.owner.avatar,self.owner.overlay.avatar):
            if view.model:
                if self.motion is not None and getattr(view.model,'clip',None) is not self.motion:
                    view.model.clip=self.motion;view.model.clip_loop=True
                view.model.music_clip_time=self.clock;view.model.music_listen=None;view.model.music_dance_accent=None
        self.owner.manual_pose='clip';self.owner.manual_pose_end=float('inf')
    def _status(self,text,now):
        if text!=self.last_status and now>=self.next_status:
            self.owner.set_status(text);self.last_status=text;self.next_status=now+2.
    def _auto(self,now,media,blocked):
        o=self.owner
        if blocked or not o.overlay.avatar.model or not o.settings.get('music_auto',True) or now<self.next_auto or now<self.next_probe:return
        self.next_probe=now+.75
        meter=getattr(o,'system_audio',None);level=meter.sample() if meter else 0.
        track=media.get('track_id')
        signal=bool(media.get('playing') and media.get('kind')=='music') or level>.008
        if self.auto_suppressed:
            if track and track!=self.suppressed_track:self.auto_suppressed=False
            elif not signal:
                if self.suppressed_quiet is None:self.suppressed_quiet=now
                if now-self.suppressed_quiet>=3:self.auto_suppressed=False
            else:self.suppressed_quiet=None
            if self.auto_suppressed:return
        # Browsers report music videos as Video too. Allow output analysis;
        # auto performance still requires fresh, positive music evidence.
        if not signal:self.auto_candidate=None;return
        if self.auto_candidate is None:self.auto_candidate=now
        if now-self.auto_candidate>=2:
            self.start('dance',origin='auto');self.auto_candidate=None
            self._status('Müzik kontrol ediliyor · yerel ses analizi',now)
    def tick(self,now):
        o=self.owner;media=getattr(getattr(o,'media_activity',None),'state',{})
        hard_block=bool(not o.settings.get('model_visible',True) or getattr(o.overlay,'drag',None) is not None or getattr(getattr(o,'fullscreen_pause',None),'paused',False))
        own_voice=bool(o.avatar.speaking or o.busy)
        if not self.enabled:self._auto(now,media,hard_block or own_voice);return
        elapsed=0. if self.last_tick is None else max(0.,min(1.,now-self.last_tick))
        dt=min(.2,elapsed);self.last_tick=now
        if self.finishing is not None:
            elapsed=max(0.,now-self.finishing);self.clock=self.finish_clock+elapsed;self._apply()
            if elapsed>=4.:
                resume=self.resume_after_exit;self._rest();self.enabled=resume
            return
        self.output.paused=hard_block or own_voice
        if hard_block:
            if self.active:self._apply()
            return
        track=media.get('track_id')
        if track and track!=self.track_id:
            if self.track_id is not None:self.output.reset_track();self.last_beat=None
            self.track_id=track
        state=self.output.snapshot();genre=genre_name(o.settings.get('music_family',''))
        source='manual' if genre!='unknown' else 'unknown'
        if genre=='unknown':
            genre=genre_name(media.get('genre','unknown'));source='media' if genre!='unknown' else 'unknown'
        if genre=='unknown' and now-state.get('genre_stamp',0)<18:
            genre=genre_name(state.get('genre','unknown'));source='audio' if genre!='unknown' else 'unknown'
        self.genre=genre;self.genre_source=source
        fresh=state.get('ready',False) and now-state.get('stamp',0)<2
        audible=fresh and state.get('level',0)>.0015
        beat_good=audible and not own_voice and state.get('confidence',0)>=.4 and dance_rate(state.get('bpm',0)) is not None
        if beat_good:self.last_beat=(now,state['bpm'])
        if state.get('error'):self._status('Ses analizi: '+state['error']+' · serbest dans kullanılabilir',now)
        music_known=(media.get('playing') and media.get('kind')=='music') or (now-state.get('genre_stamp',0)<18 and state.get('music_detected') is True)
        if self.origin=='auto':
            confirmed=audible and music_known and not own_voice
            if confirmed:
                self.quiet_since=None
                if self.good_since is None:self.good_since=now
            else:
                self.good_since=None
                if self.quiet_since is None:self.quiet_since=now
            if not self.active and (self.good_since is None or now-self.good_since<1.5):
                if self.started_at is not None and now-self.started_at>24:
                    self.stop(suppress=False);self.next_auto=now+20
                return
            if self.active and not own_voice and self.quiet_since is not None and now-self.quiet_since>6:
                self.stop(suppress=False);self.next_auto=now+3;return
        scene=o.overlay.avatar.furniture
        pole_owned=self.active and self.motion.pole
        director=getattr(o,'daily_director',None)
        if scene is not None and director and self.origin=='auto' and genre not in QUIET and music_known:
            activity=getattr(scene,'activity',None)
            if scene is director.scene and director.manual is None and getattr(activity,'kind',None)=='tv':
                scene.request_exit()
        listening=not pole_owned and (self.mode=='listen' or scene is not None or (self.origin=='auto' and genre in QUIET))
        if listening:
            if self.active:self._rest()
            phase=(now-state.get('beat_time',now))*state.get('bpm',0)/60
            for view in (o.avatar,o.overlay.avatar):
                if view.model:view.model.music_listen=(phase,.025)
            return
        if not self.active:
            from genre_dance import GenreDance
            self.clock=self.resume_clock
            if self.mode=='pole':
                from pole_motion import PoleMotion
                self.motion=PoleMotion(seed=self.track_id or self.started_at,entry_clock=self.clock)
            else:self.motion=GenreDance(seed=self.track_id or self.started_at,entry_clock=self.clock)
            for view in (o.avatar,o.overlay.avatar):
                if view.model:view.model.clip=self.motion;view.model.clip_loop=True
            self.active=True
        locked=self.last_beat is not None and now-self.last_beat[0]<8
        target_rate=dance_rate(self.last_beat[1]) if locked else 1.
        self.rate+=max(-dt*.3,min(dt*.3,target_rate-self.rate));self.clock+=elapsed*self.rate
        if beat_good:
            factor=target_rate*120/state['bpm']
            error=((now-state['beat_time'])*state['bpm']/60*factor-self.clock*2+2)%4-2
            self.clock+=max(-dt*.08,min(dt*.08,error*.1))
        self.motion.set_genre(genre,self.clock);self._apply()
        label={'manual':'elle seçim','media':'medya etiketi','audio':'sesten tahmin','unknown':'tür öğreniliyor'}[source]
        tempo=f"{round(self.last_beat[1])} BPM · ritme bağlı" if locked else 'serbest tempo · ritim bekleniyor'
        self._status(f"{'Direk dansı' if self.mode=='pole' else 'Dans'}: {genre if genre!='unknown' else 'genel'} · {tempo} · {label}",now)
