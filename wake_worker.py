"""Opt-in local waiting microphone; releases it before signaling a name match."""
import sys,os,json,time,queue,threading,argparse,math
from array import array
from pathlib import Path
# A native import/driver can block before the Qt controller receives a ready event.
# Exit this worker itself so a Windows venv launcher cannot leave a blocked child.
PHASE='imports'
BOOT=threading.Timer(25,lambda:(print(json.dumps({'event':'error','code':'startup_timeout','phase':PHASE}),flush=True),os._exit(3)));BOOT.daemon=True;BOOT.start()
print(json.dumps({'event':'progress','phase':PHASE}),flush=True)
ROOT=Path(__file__).resolve().parent;sys.path[:0]=[str(ROOT/'live_voice'),str(ROOT)]
from resource_guard import MemoryJob,GiB,require_capacity,pressure
from startup_runtime import prepare_audio_runtime
from microphone_lease import MicrophoneLease
from keyword_detector import KeywordDetector
STOP=threading.Event()
def emit(event,**values):print(json.dumps({'event':event,**values},ensure_ascii=False),flush=True)
def main():
    global PHASE
    parser=argparse.ArgumentParser();parser.add_argument('--name',required=True);parser.add_argument('--model-path',default=str(ROOT/'models/wake-vosk-tr'));parser.add_argument('--check',action='store_true');parser.add_argument('--microphone',default='Otomatik');args=parser.parse_args()
    require_capacity(3*GiB//4);job=MemoryJob(GiB,3*GiB//4);job.attach();lease=None;stream=None;found=False
    for variable in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[variable]='1'
    try:
        PHASE='model';emit('progress',phase=PHASE)
        try:detector=KeywordDetector(Path(args.model_path),args.name)
        except ValueError:
            emit('unsupported_name');return
        if args.check:BOOT.cancel();emit('checked',supported_phrases=len(detector.phrases));return
        def controls():
            for line in sys.stdin:
                if line.strip()=='STOP':STOP.set();return
        threading.Thread(target=controls,daemon=True).start();PHASE='microphone_lease';emit('progress',phase=PHASE);lease=MicrophoneLease()
        blocks=queue.Queue(maxsize=8);overflow=False
        def capture(data,frames,timing,status):
            nonlocal overflow
            if status and not getattr(status,'input_overflow',False):overflow=True;return
            try:blocks.put_nowait(bytes(data))
            except queue.Full:
                try:blocks.get_nowait()
                except queue.Empty:pass
                try:blocks.put_nowait(bytes(data))
                except queue.Full:pass
        PHASE='audio';emit('progress',phase=PHASE)
        sd=prepare_audio_runtime();from run_live import audio_route
        from audio_devices import resolve_input
        device,settings=audio_route(resolve_input(args.microphone,sd),0)
        stream=sd.RawInputStream(device=device,extra_settings=settings,samplerate=16000,channels=1,dtype='int16',blocksize=640,latency='low',callback=capture);stream.start()
        BOOT.cancel();emit('ready');voiced=0.;noise_floor=.0025;checked=time.monotonic()
        while not STOP.is_set():
            now=time.monotonic()
            if now-checked>1:
                checked=now
                if pressure():raise RuntimeError('memory_pressure')
            if overflow:raise RuntimeError('microphone_failed')
            try:pcm=blocks.get(timeout=.1)
            except queue.Empty:continue
            values=array('h',pcm);level=math.sqrt(sum(v*v for v in values)/max(1,len(values)))/32768
            threshold=max(.0035,min(.012,noise_floor*2.8))
            if level>threshold:voiced+=len(pcm)/32000.
            elif voiced==0:noise_floor=.98*noise_floor+.02*min(level,.006)
            if detector.accept(pcm,voiced):found=True;break
            if detector.finalized:voiced=0.
            # Preserve speech evidence until Vosk finalizes. Its silence
            # endpoint can exceed one second for a short standalone name.
    finally:
        if stream:stream.stop();stream.close()
        if lease:lease.close()
    if found:emit('wake')
if __name__=='__main__':
    try:main()
    except Exception as error:
        code=getattr(error,'code',None) or ('memory_pressure' if str(error)=='memory_pressure' else 'worker_failed')
        emit('error',code=code,phase=PHASE,exception_type=type(error).__name__);raise SystemExit(1)
