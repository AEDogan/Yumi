"""Explicitly started, bounded microphone/speaker test; no background autostart."""
if __name__=='__main__':print('Yumi canlı ses başlatıcısı hazırlanıyor…',flush=True)
import argparse,asyncio,json,os,sys,time,queue,threading,subprocess
from array import array
import math
from collections import deque
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT.parent)]
from resource_guard import MemoryJob,GiB,require_capacity,pressure
from startup_runtime import prepare_audio_runtime
from live_core import LiveSession,LiveError
from contracts import SessionOptions,create_session
from app_paths import data_dir
UI_MODE='--ui-mode' in sys.argv
STOP_REQUESTED=threading.Event()
AUDIO_CONTROLS=queue.Queue(maxsize=8)
from skill_feedback import FeedbackQueue
SKILL_FEEDBACK=FeedbackQueue()
SAFE_EVENTS=deque(maxlen=128)
LAST_DIAGNOSTIC_WRITE=0.
def load_key():
    print('Korunan Gemini anahtarı okunuyor…',flush=True)
    from platform_win import unprotect
    file=data_dir()/'gemini-key.dat'
    if not file.exists():raise LiveError('Kayıtlı Gemini API anahtarı yok. Anahtarı sohbete yazma.')
    try:return unprotect(file.read_bytes()).decode('utf-8')
    except OSError:raise LiveError('Gemini anahtarı bu Windows güvenlik bağlamında çözülemedi. Prototipi anahtarın kaydedildiği kendi Windows oturumunda başlat.') from None
def native_preferences():
    try:
        saved=json.loads((data_dir()/'settings.json').read_text(encoding='utf-8'))
        profile=saved.get('voice_profiles',{}).get(saved.get('skin'),{})
        voice=profile.get('speech_voice',saved.get('speech_voice',''))
        voice=voice.split(':',1)[1] if voice.startswith('gemini-live:') else 'Kore'
        if voice not in ('Kore','Puck','Charon','Aoede','Fenrir'):voice='Kore'
        return voice,str(profile.get('name','Yumi')).strip() or 'Yumi'
    except (OSError,ValueError,TypeError,AttributeError):return 'Kore','Yumi'
def audio_route(device,direction):
    sd=prepare_audio_runtime()
    devices=sd.query_devices();hosts=sd.query_hostapis()
    if device is None:
        device=int(sd.default.device[direction]);name=devices[device]['name']
        # Prefer shared WASAPI for the SAME physical device, never a different mic.
        for i,item in enumerate(devices):
            if item['name']==name and hosts[item['hostapi']]['name']=='Windows WASAPI':device=i;break
    wasapi=hosts[devices[device]['hostapi']]['name']=='Windows WASAPI'
    return device,sd.WasapiSettings(exclusive=False,auto_convert=True) if wasapi else None
class AudioDevice:
    def __init__(self,session,input_device=None,output_device=None):
        sd=prepare_audio_runtime()
        self.session=session;self.input=queue.Queue(maxsize=8);self.failure=None;self.first=True;self.dropped=0;self.overflows=0;self.energy_blocks=0;self.notified_dropped=0;self.notified_overflows=0;self.pending_onset=False
        input_device,input_settings=audio_route(input_device,0);output_device,output_settings=audio_route(output_device,1)
        session.emit('audio_routes',input_device=input_device,output_device=output_device)
        self.mic=sd.RawInputStream(device=input_device,extra_settings=input_settings,samplerate=16000,channels=1,dtype='int16',blocksize=640,latency='low',callback=self.capture)
        try:self.speaker=sd.RawOutputStream(device=output_device,extra_settings=output_settings,samplerate=24000,channels=1,dtype='int16',blocksize=480,latency='low',callback=self.output)
        except Exception:self.mic.close();raise
    def capture(self,data,frames,timing,status):
        if status:
            if getattr(status,'input_overflow',False):self.overflows+=1
            else:self.failure='Mikrofon aygıtı hata verdi.';return
        try:self.input.put_nowait(bytes(data))
        except queue.Full:
            try:self.input.get_nowait()
            except queue.Empty:pass
            try:self.input.put_nowait(bytes(data));self.dropped+=1
            except queue.Full:pass
        if time.monotonic()-self.session.last_played<.25 and self.session.local_onset is None:
            values=array('h',bytes(data));level=math.sqrt(sum(v*v for v in values)/max(1,len(values)))/32768
            self.energy_blocks=self.energy_blocks+1 if level>.025 else 0
            if self.energy_blocks>=2:self.session.local_onset=time.monotonic();self.pending_onset=True
        if self.first:self.first=False;self.session.emit('first_microphone_block')
    def output(self,out,frames,timing,status):
        if status and 'underflow' not in str(status):self.failure='Hoparlör aygıtı hata verdi.'
        data,count=self.session.playback.read(frames*2);out[:]=data
        if count:self.session.played(timing.outputBufferDacTime-timing.currentTime)
        else:self.session.silent_output()
    def start(self):self.speaker.start();self.mic.start()
    def close(self):
        for stream in (self.mic,self.speaker):
            try:stream.stop();stream.close()
            except Exception:pass
    async def send(self):
        while True:
            if self.failure:raise LiveError(self.failure)
            if self.dropped!=self.notified_dropped or self.overflows!=self.notified_overflows:
                self.session.emit('input_recovered',dropped_blocks=self.dropped,overflow_count=self.overflows)
                self.notified_dropped=self.dropped;self.notified_overflows=self.overflows
            if self.pending_onset:self.pending_onset=False;self.session.emit('local_energy_onset')
            try:pcm=self.input.get_nowait()
            except queue.Empty:await asyncio.sleep(.005);continue
            await self.session.send_audio(pcm)
def display(row):
    global LAST_DIAGNOSTIC_WRITE
    if row['event'] in ('user_transcript','assistant_transcript','transcript','transcript_end'):
        if UI_MODE and row['event'] in ('transcript','transcript_end'):print(json.dumps(row,ensure_ascii=False),flush=True)
        return
    if UI_MODE and row['event'] in {'error','transport_failure','input_recovered','local_energy_onset','user_activity_start','interrupted','audio_flushed','silence_to_device','goaway_notice','reconnecting','resumed','session_limit'}:
        fields={'event','session_seconds','phase','exception_type','close_code','dropped_blocks','overflow_count','clear_ms','after_clear_ms','local_energy_to_server_ms','estimated_dac_delay_seconds','error_code'}
        safe={key:value for key,value in row.items() if key in fields and (value is None or isinstance(value,(str,int,float,bool)))}
        SAFE_EVENTS.append(safe)
        if row['event']=='error' or time.monotonic()-LAST_DIAGNOSTIC_WRITE>.25:
            try:
                path=data_dir()/'native_live_events.json'
                temp=path.with_suffix('.worker.tmp');temp.write_text(json.dumps(list(SAFE_EVENTS),ensure_ascii=False),encoding='utf-8');os.replace(temp,path)
                LAST_DIAGNOSTIC_WRITE=time.monotonic()
            except OSError:pass
    if UI_MODE:
        if row['event'] not in ('user_transcript','assistant_transcript'):print(json.dumps(row,ensure_ascii=False),flush=True)
        return
    if row['event'].endswith('_transcript'):print(row['event'],row['text'],flush=True)
    else:print(row,flush=True)
def startup_guard(report=None):
    def abort():
        if report:Path(report).write_text(json.dumps({'passed':False,'human_live_acceptance':False,'error':'audio_device_open_timeout'},indent=2),encoding='utf-8')
        display({'event':'error','message':'Ses aygıtı 8 saniyede açılamadı; yalnız bu deneme süreci kapatılıyor.'})
        # A blocked native driver call cannot safely be cancelled as a Python future.
        os._exit(2)
    timer=threading.Timer(8,abort);timer.daemon=True;timer.start();return timer
async def run(args):
    try:
        saved=json.loads((data_dir()/'settings.json').read_text(encoding='utf-8'))
        city=str(saved.get('city','')).strip()
    except (OSError,ValueError,TypeError,AttributeError):city=''
    session=create_session(SessionOptions(voice=args.voice,character_name=args.name,city=city),display);device=None;tasks=[];completed=False
    session.initial_history=getattr(args,'history',[])
    try:
        key=load_key()
        print('Gemini Live bağlantısı kuruluyor…',flush=True)
        await session.connect(key)
        if args.probe:
            speaker=None
            try:
                if args.play_test:
                    guard=startup_guard(args.report)
                    try:
                        sd=prepare_audio_runtime()
                        output=object.__new__(AudioDevice);output.session=session;output.failure=None
                        route,settings=audio_route(args.output_device,1)
                        session.emit('output_route',device=route)
                        speaker=sd.RawOutputStream(device=route,extra_settings=settings,samplerate=24000,channels=1,dtype='int16',blocksize=480,latency='low',callback=output.output)
                        speaker.start()
                    finally:guard.cancel()
                start=time.monotonic();await session.send_text('Türkçe sadece merhaba de.')
                while True:
                    item=json.loads(await asyncio.wait_for(session.ws.recv(),15));session.handle(item)
                    if not args.play_test:session.playback.clear()
                    if item.get('serverContent',{}).get('turnComplete'):break
                if not session.audio_bytes_received:raise LiveError('Denemede ses dönmedi.')
                if args.play_test:
                    deadline=time.monotonic()+12
                    while len(session.playback):
                        if output.failure:raise LiveError(output.failure)
                        if time.monotonic()>deadline:raise LiveError('Hoparlör kuyruğu zamanında boşalmadı.')
                        await asyncio.sleep(.02)
                    await asyncio.sleep(.15)
                    if session.first_play:raise LiveError('Ses aygıtına PCM aktarımı gözlenmedi.')
                session.emit('probe_complete',pcm_bytes=session.audio_bytes_received,total_seconds=round(time.monotonic()-start,3),human_live_test=False,output_device_test=args.play_test)
            finally:
                if speaker:speaker.stop();speaker.close()
        else:
            from browser_audio import BrowserAudioDevice
            from microphone_lease import MicrophoneLease
            from persistent_audio import serve
            print('YUMI_READY',flush=True)
            await serve(session,args,STOP_REQUESTED,AUDIO_CONTROLS,SKILL_FEEDBACK,BrowserAudioDevice,MicrophoneLease,pressure)
        completed=True
    finally:
        for task in tasks:task.cancel()
        if tasks:await asyncio.gather(*tasks,return_exceptions=True)
        if device:device.close()
        await session.close()
        if args.report:Path(args.report).write_text(json.dumps({'passed':completed,'model':'gemini-3.8-live','voice':args.voice,'human_live_acceptance':False,'events':list(session.metrics)},ensure_ascii=False,indent=2),encoding='utf-8')
def main():
    p=argparse.ArgumentParser()
    p.add_argument('--probe',action='store_true');p.add_argument('--play-test',action='store_true');p.add_argument('--devices',action='store_true')
    p.add_argument('--ui-mode',action='store_true',help=argparse.SUPPRESS);p.add_argument('--worker',action='store_true',help=argparse.SUPPRESS)
    p.add_argument('--history-stdin',action='store_true',help=argparse.SUPPRESS)
    p.add_argument('--standby',action='store_true',help=argparse.SUPPRESS)
    p.add_argument('--microphone',default='Otomatik')
    p.add_argument('--voice',choices=['Kore','Puck','Charon','Aoede','Fenrir']);p.add_argument('--name')
    p.add_argument('--input-device',type=int);p.add_argument('--output-device',type=int);p.add_argument('--seconds',type=int,default=120);p.add_argument('--report')
    a=p.parse_args()
    a.history=[]
    if a.history_stdin:
        if not a.worker or not a.ui_mode or a.probe or a.devices:p.error('Geçmiş aktarımı yalnız uygulamanın ses alt sürecinde kullanılabilir.')
        from live_history import read_history
        try:a.history=read_history(sys.stdin)
        except (ValueError,OSError):p.error('Sohbet bağlamı okunamadı; ses oturumunu yeniden başlat.')
        if a.history is None:return
    if a.microphone!='Otomatik':a.input_device=a.microphone
    saved_voice,saved_name=native_preferences();a.voice=a.voice or saved_voice;a.name=a.name or saved_name
    if a.ui_mode and a.worker and not a.probe:a.seconds=0
    if a.play_test and not a.probe:p.error('--play-test requires --probe')
    if not (1<=a.seconds<=300 or (a.ui_mode and a.worker and a.seconds==0)):p.error('Deneme süresi 1–300; uygulama oturumu durdurulana kadar açık olabilir.')
    if a.ui_mode:
        def controls():
            for line in sys.stdin:
                if line.strip()=='STOP':STOP_REQUESTED.set();return
                try:item=json.loads(line)
                except ValueError:continue
                if isinstance(item,dict) and item.get('kind') in ('activate','deactivate'):
                    try:AUDIO_CONTROLS.put_nowait(item['kind'])
                    except queue.Full:pass
                else:SKILL_FEEDBACK.enqueue(line)
        threading.Thread(target=controls,daemon=True).start()
    print('Bellek rezervi ve süreç sınırları kontrol ediliyor…',flush=True)
    require_capacity(GiB);job=MemoryJob(6*GiB,4*GiB);job.attach()
    if not a.worker:
        environment=os.environ.copy();environment['PYTHONIOENCODING']='utf-8'
        child=subprocess.Popen([sys.executable,'-u','-B',str(Path(__file__).resolve()),*sys.argv[1:],'--worker'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',env=environment)
        ready=threading.Event()
        def forward():
            for line in child.stdout:
                print(line,end='',flush=True)
                if line.strip()=='YUMI_READY':ready.set()
        threading.Thread(target=forward,daemon=True).start()
        try:
            if not a.probe and not a.devices:
                deadline=time.monotonic()+40
                while child.poll() is None and not ready.is_set():
                    if time.monotonic()>deadline:raise subprocess.TimeoutExpired('startup',40)
                    time.sleep(.05)
            result=child.wait(timeout=45 if a.probe or a.devices else a.seconds+5)
            time.sleep(.05)
            raise SystemExit(result)
        except (subprocess.TimeoutExpired,KeyboardInterrupt):
            child.terminate()
            try:child.wait(3)
            except subprocess.TimeoutExpired:child.kill();child.wait(3)
            if a.report:Path(a.report).write_text(json.dumps({'passed':False,'human_live_acceptance':False,'error':'session_process_timeout_or_interrupt'},indent=2),encoding='utf-8')
            print('Deneme alt süreci kapatıldı; diğer uygulamalara dokunulmadı.')
            raise SystemExit(2)
    if a.devices:
        guard=startup_guard(a.report)
        try:
            sd=prepare_audio_runtime()
            print(sd.query_devices());return
        finally:guard.cancel()
    try:
        if a.play_test:
            guard=startup_guard(a.report)
            try:
                prepare_audio_runtime()
                print('Ses aygıtı altyapısı hazır.',flush=True)
            finally:guard.cancel()
        if a.probe:asyncio.run(run(a))
        else:
            os.environ['QTWEBENGINE_CHROMIUM_FLAGS']=os.environ.get('QTWEBENGINE_CHROMIUM_FLAGS','')+' --disable-gpu --disable-background-timer-throttling --disable-renderer-backgrounding'
            from browser_audio import run_qt
            run_qt(run(a))
    except KeyboardInterrupt:print('Oturum kapatıldı.');return
    except Exception as error:
        message=str(error) if isinstance(error,LiveError) else 'Oturum durduruldu: '+type(error).__name__
        display({'event':'error','message':message,'exception_type':type(error).__name__,'error_code':getattr(error,'code','runtime_error')})
        raise SystemExit(1)
if __name__=='__main__':main()
