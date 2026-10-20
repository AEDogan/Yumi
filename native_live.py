"""Qt-owned isolated Gemini Live worker. Only this controller's child is stopped."""
import json,os,queue,subprocess,sys,threading,time
from collections import deque
from pathlib import Path
from PySide6.QtCore import QObject,QTimer,Signal
class NativeLive(QObject):
    stateChanged=Signal(str)
    playbackChanged=Signal(bool,float)
    failed=Signal(str)
    finished=Signal()
    conversationPaused=Signal()
    transcriptChanged=Signal(str,int,str,str)
    transcriptEnded=Signal(str,int,bool)
    feedbackFailed=Signal()
    def __init__(self,parent=None,command=None):
        super().__init__(parent);self.process=None;self.command=command;self.events=queue.Queue(maxsize=128)
        self.stopping=False;self.ready=False;self.error_seen=False;self.deadline=0;self.diagnostics=deque(maxlen=128);self.idle_closed=False
        self.feedback_active=False;self.listening=False;self.pending_activation=False;self.pause_requested=False
        self.timer=QTimer(self);self.timer.setInterval(50);self.timer.timeout.connect(self.poll)
    @property
    def active(self):return self.process is not None
    def start(self,voice='Kore',name='Yumi',history=None,standby=False,microphone='Otomatik'):
        if self.active:return
        from resource_guard import require_capacity,GiB
        require_capacity(GiB)
        if self.command is None:
            import psutil
            for proc in psutil.process_iter(['cmdline']):
                try:
                    if any(a.replace('\\','/').lower().endswith(('/yumi-live-prototype/run_live.py','/live_voice/run_live.py')) for a in proc.info['cmdline'] or []):
                        raise RuntimeError('Başka bir canlı ses denemesi açık. Önce o oturumu kapat; ikinci mikrofon oturumu açılmadı.')
                except (psutil.NoSuchProcess,psutil.AccessDenied):pass
            root=Path(__file__).resolve().parent
            command=[str(root/'.venv/Scripts/python.exe'),'-u','-B',str(root/'live_voice/run_live.py'),'--worker','--ui-mode','--seconds','0','--voice',voice,'--name',name,'--history-stdin','--microphone',microphone]+(['--standby'] if standby else [])
        else:command=self.command
        environment=os.environ.copy();environment['PYTHONIOENCODING']='utf-8';environment['PYTHONUNBUFFERED']='1'
        self.idle_closed=False
        self.process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',env=environment,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        self.events=queue.Queue(maxsize=128);self.ready=False;self.stopping=False;self.error_seen=False;self.deadline=time.monotonic()+35
        process=self.process;events=self.events
        self.input_lock=threading.Lock()
        input_lock=self.input_lock
        from live_history import history_line
        initial=history_line(history or []) if self.command is None else None
        def read():
            if initial is not None:
                try:
                    with input_lock:
                        if not self.stopping:process.stdin.write(initial);process.stdin.flush()
                except (OSError,ValueError):return
            for line in process.stdout:
                try:item=json.loads(line)
                except (ValueError,TypeError):continue
                if isinstance(item,dict) and item.get('event') not in ('user_transcript','assistant_transcript'):
                    try:events.put_nowait(item)
                    except queue.Full:pass
        threading.Thread(target=read,daemon=True).start();self.timer.start();self.stateChanged.emit('Gemini Live bağlanıyor…')
    def control(self,kind):
        if not self.process or self.stopping:return False
        try:
            with self.input_lock:
                self.process.stdin.write(json.dumps({'kind':kind})+'\n');self.process.stdin.flush()
            return True
        except (OSError,ValueError):return False
    def activate(self):
        self.pending_activation=True
        if self.ready:
            self.pending_activation=False
            return self.control('activate')
        return self.active
    def deactivate(self):
        self.pending_activation=False;self.pause_requested=True
        return self.control('deactivate')
    def feedback(self,text):
        if not self.process or not self.ready or self.stopping:return False
        process=self.process
        payload=json.dumps({'kind':'skill_result','id':str(time.monotonic_ns()),'text':str(text)[:4000]},ensure_ascii=False)+'\n'
        def send():
            try:
                with self.input_lock:
                    if self.process is not process or self.stopping:return
                    process.stdin.write(payload);process.stdin.flush()
            except (OSError,ValueError):self.feedbackFailed.emit()
        threading.Thread(target=send,daemon=True).start();return True
    def stop(self):
        if not self.process or self.stopping:return
        self.stopping=True;self.deadline=time.monotonic()+1.5;self.stateChanged.emit('Canlı ses durduruluyor…')
        process=self.process
        def send_stop():
            try:
                with self.input_lock:process.stdin.write('STOP\n');process.stdin.flush()
            except (OSError,ValueError):pass
        threading.Thread(target=send_stop,daemon=True).start()
    @staticmethod
    def _kill_owned(process):
        # Windows venv launchers can have a real Python worker beneath them.
        # Killing only the launcher can leave the old voice session alive.
        import psutil
        try:children=psutil.Process(process.pid).children(recursive=True)
        except psutil.Error:children=[]
        for child in reversed(children):
            try:child.kill()
            except psutil.Error:pass
        try:process.kill()
        except OSError:pass
    def poll(self):
        process=self.process
        if process is None:self.timer.stop();return
        while True:
            try:item=self.events.get_nowait()
            except queue.Empty:break
            event=item.get('event')
            if event=='skill_feedback_started':self.feedback_active=True;continue
            if event in ('skill_feedback_done','skill_feedback_failed'):
                self.feedback_active=False
                if event=='skill_feedback_failed':self.feedbackFailed.emit()
                continue
            if event=='avatar_playback':
                level=item.get('level',0.)
                if isinstance(level,(int,float)):
                    self.playbackChanged.emit(bool(item.get('audible')),min(1.,max(0.,float(level))))
                continue
            if event=='transcript':
                role=item.get('role');turn=item.get('turn_id');text=item.get('text')
                if role=='assistant' and self.feedback_active:continue
                if role in ('user','assistant') and isinstance(turn,int) and isinstance(text,str):
                    self.transcriptChanged.emit(role,turn,text[:16000],item.get('mode','delta'))
                continue
            if event=='transcript_end':
                role=item.get('role');turn=item.get('turn_id')
                if role=='assistant' and self.feedback_active:continue
                if role in ('user','assistant') and isinstance(turn,int):self.transcriptEnded.emit(role,turn,bool(item.get('complete')))
                continue
            if event=='idle_timeout':self.idle_closed=True
            allowed={'event','session_seconds','phase','exception_type','close_code','error_code','dropped_blocks','overflow_count','clear_ms','after_clear_ms','local_energy_to_server_ms','estimated_dac_delay_seconds'}
            safe={key:value for key,value in item.items() if key in allowed and (value is None or isinstance(value,(str,int,float,bool)))}
            if event in {'error','transport_failure','input_recovered','local_energy_onset','user_activity_start','interrupted','audio_flushed','silence_to_device','goaway_notice','reconnecting','resumed'}:
                self.diagnostics.append(safe)
                if self.command is None:
                    try:
                        from app_paths import data_dir
                        path=data_dir()/'native_live_events.json'
                        temp=path.with_suffix('.tmp');temp.write_text(json.dumps(list(self.diagnostics),ensure_ascii=False),encoding='utf-8');os.replace(temp,path)
                    except OSError:pass
            if event in ('error','transport_failure') and self.feedback_active:
                self.feedback_active=False;self.feedbackFailed.emit()
            if event=='error':
                self.error_seen=True;self.failed.emit(str(item.get('message','Canlı ses hatası.')));self.stop()
            elif not self.stopping:
                if event=='listening':self.ready=True;self.listening=True;self.stateChanged.emit('Dinliyor · Gemini Live')
                elif event=='standby':
                    was_listening=self.listening;self.listening=False;self.ready=True
                    self.stateChanged.emit('Gemini bağlı · Mikrofon beklemede')
                    if self.pending_activation:self.activate()
                    elif was_listening or self.pause_requested:
                        self.pause_requested=False;self.conversationPaused.emit()
                elif event=='connected':self.stateChanged.emit('Gemini bağlantısı hazır')
                elif event=='reconnecting':self.ready=False;self.deadline=time.monotonic()+35;self.stateChanged.emit('Gemini bağlantısı sürdürülüyor…')
                elif event=='resumed':self.ready=True;self.stateChanged.emit('Dinliyor · Gemini Live' if self.listening else 'Gemini bağlı · Mikrofon beklemede')
                elif event=='user_activity_start':self.stateChanged.emit('Seni dinliyor · Gemini Live')
                elif event in ('first_audio_received','first_audio_to_device') and (self.listening or self.feedback_active):self.stateChanged.emit('Konuşuyor · Gemini Live')
                elif event in ('interrupted','playback_drained'):self.stateChanged.emit('Dinliyor · Gemini Live')
        if time.monotonic()>self.deadline and (self.stopping or not self.ready):
            if not self.stopping and not self.error_seen:self.error_seen=True;self.failed.emit('Canlı ses 35 saniyede hazır olmadı; yalnız bu oturum kapatıldı.')
            self._kill_owned(process)
            self.stopping=True
        if process.poll() is not None:
            if self.feedback_active:self.feedback_active=False;self.feedbackFailed.emit()
            if process.returncode and not self.stopping and not self.error_seen:self.failed.emit('Canlı ses başlatılamadı. Mikrofon/API erişimi hazır değil; yeniden deneyebilirsin.')
            for stream in (process.stdin,process.stdout):
                try:stream.close()
                except (OSError,ValueError):pass
            self.process=None;self.listening=False;self.pending_activation=False;self.timer.stop();self.finished.emit()
    def shutdown(self):
        self.stop()
        if self.process:
            try:self.process.wait(1.5)
            except subprocess.TimeoutExpired:self._kill_owned(self.process);self.process.wait(2)
            self.poll()
