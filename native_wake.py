"""Qt controller for a private local name-only worker, never a cloud session."""
import os,subprocess,threading,queue,json,time
from pathlib import Path
from PySide6.QtCore import QObject,QTimer,Signal
class NativeWake(QObject):
    wakeDetected=Signal()
    ready=Signal(str)
    failed=Signal(str)
    def __init__(self,parent=None,command=None):
        super().__init__(parent);self.command=command;self.process=None;self.enabled=False;self.name='';self.wake_name='';self.events=queue.Queue(maxsize=8);self.woke=False;self.deadline=0;self.error=False
        self.timer=QTimer(self);self.timer.setInterval(50);self.timer.timeout.connect(self.poll)
        self.retry=QTimer(self);self.retry.setSingleShot(True);self.retry.timeout.connect(self.retry_start)
        self.paused=False;self.attempts=0;self.unsupported=False;self.exhausted=False;self.notified=False;self.phase='imports';self.hard_deadline=0.;self.ready_since=None
        self.reader_done=threading.Event();self.reader_done.set()
    def configure(self,enabled,name,paused=False,wake_name='',microphone='Otomatik'):
        wake_name=wake_name.strip() or name
        changed=name!=self.name or wake_name!=self.wake_name or microphone!=getattr(self,'microphone','Otomatik')
        self.microphone=microphone
        if changed or not enabled or paused:self.pause()
        if changed or enabled!=self.enabled:self.attempts=0;self.unsupported=False;self.exhausted=False;self.notified=False
        self.paused=paused
        self.enabled=enabled;self.name=name;self.wake_name=wake_name
        if enabled and not paused and not self.unsupported and not self.exhausted and self.process is None and not self.retry.isActive():
            try:self.start()
            except Exception:
                self.report_failure('Yerel çağrı adı dinlemesi açılamadı; yeniden denenecek.');self.schedule_retry()
    def report_failure(self,message):
        if not self.notified:self.notified=True;self.failed.emit(message)
    def retry_start(self):
        if self.enabled and not self.paused and not self.unsupported and not self.exhausted and self.process is None:
            try:self.start()
            except Exception:self.schedule_retry()
    def schedule_retry(self):
        if self.enabled and not self.paused and not self.unsupported and self.attempts<3:
            self.attempts+=1;self.retry.start(2000*self.attempts)
        elif self.enabled and not self.paused and not self.unsupported:self.exhausted=True
    def start(self):
        from resource_guard import require_capacity,GiB
        require_capacity(3*GiB//4);root=Path(__file__).resolve().parent
        command=self.command or [str(root/'.venv/Scripts/python.exe'),'-u','-B',str(root/'wake_worker.py'),'--name',self.wake_name,'--microphone',getattr(self,'microphone','Otomatik')]
        env=os.environ.copy();env['PYTHONIOENCODING']='utf-8';env['OPENBLAS_NUM_THREADS']='1';env['OMP_NUM_THREADS']='1'
        self.events=queue.Queue(maxsize=8);self.woke=False;self.error=False;self.ready_since=None;self.phase='imports';self.deadline=time.monotonic()+10;self.hard_deadline=time.monotonic()+30
        self.process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,encoding='utf-8',env=env,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        events=self.events;process=self.process;reader_done=threading.Event();self.reader_done=reader_done
        def read():
            try:
                for line in process.stdout:
                    try:item=json.loads(line)
                    except ValueError:continue
                    if item.get('event') in ('progress','ready','wake','checked','unsupported_name','error'):
                        try:events.put_nowait(item)
                        except queue.Full:pass
            finally:reader_done.set()
        threading.Thread(target=read,daemon=True).start();self.timer.start()
    def poll(self):
        process=self.process
        if process is None:self.timer.stop();return
        while not self.events.empty():
            item=self.events.get_nowait();event=item['event']
            if event=='progress':
                self.phase=item.get('phase','imports');self.deadline=min(self.hard_deadline,time.monotonic()+(20 if self.phase=='model' else 10))
            elif event=='ready':
                self.deadline=float('inf');self.ready_since=time.monotonic();self.ready.emit(self.wake_name)
            elif event=='wake':self.woke=True
            elif event in ('unsupported_name','error'):
                self.error=True;self.unsupported=event=='unsupported_name'
                codes={'microphone_already_active':'Başka bir Yumi mikrofon oturumu açık. Önce o oturumu kapat.', 'memory_pressure':'Yerel çağrı adı dinlemesi için kullanılabilir bellek azaldı.', 'startup_timeout':'Yerel çağrı adı servisi hazırlanırken zaman aşımına uğradı.'}
                message='Bu model adı yerel tanıyıcıda desteklenmiyor; mikrofon düğmesini kullanabilirsin.' if event=='unsupported_name' else codes.get(item.get('code'),'Yerel çağrı adı dinlemesi açılamadı; mikrofon düğmesini kullanabilirsin.')
                self.report_failure(message)
        if self.ready_since is not None and time.monotonic()-self.ready_since>30 and not self.error:
            self.attempts=0;self.notified=False
        if time.monotonic()>self.deadline:
            phase='ses modeli' if self.phase=='model' else 'mikrofon'
            self.pause();self.paused=False;self.report_failure('Yerel çağrı adı dinlemesinde '+phase+' hazırlığı zaman aşımına uğradı.');self.schedule_retry();return
        if process.poll() is not None:
            # The worker exits immediately after emitting wake. Drain its final
            # stdout event before cleanup; process exit can beat the reader thread.
            if not self.reader_done.is_set() or not self.events.empty():return
            wake=self.woke;code=process.returncode;self.cleanup()
            if wake and self.enabled:self.wakeDetected.emit()
            else:
                if code and not self.error:self.report_failure('Yerel çağrı adı işleyicisi kapandı; mikrofon düğmesini kullanabilirsin.')
                self.schedule_retry()
    def cleanup(self):
        if self.process:
            for stream in (self.process.stdin,self.process.stdout):
                try:stream.close()
                except (OSError,ValueError):pass
        self.process=None;self.timer.stop()
    def pause(self):
        self.paused=True;self.retry.stop()
        if not self.process:return
        try:self.process.stdin.write('STOP\n');self.process.stdin.flush();self.process.wait(1.5)
        except (OSError,ValueError,subprocess.TimeoutExpired):
            try:
                from native_live import NativeLive
                NativeLive._kill_owned(self.process);self.process.wait(1)
            except OSError:pass
        self.cleanup()
    def shutdown(self):self.enabled=False;self.pause()
