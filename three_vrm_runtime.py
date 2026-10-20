"""Local three-vrm SpringBone bridge; models and user data never leave the PC."""
import atexit,json,logging,os,queue,shutil,subprocess,threading,uuid
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parent/'vrm_runtime'
log=logging.getLogger(__name__)

class RuntimeError3D(RuntimeError):pass

class Worker:
    def __init__(self):
        node=shutil.which('node')
        if not node:raise RuntimeError3D('three-vrm için Node.js çalışma zamanı bulunamadı.')
        if not (ROOT/'node_modules/@pixiv/three-vrm/package.json').is_file():
            raise RuntimeError3D('three-vrm yerel bağımlılıkları kurulmamış.')
        self.process=subprocess.Popen([node,str(ROOT/'spring_worker.mjs')],cwd=ROOT,
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,
            text=True,encoding='utf-8',bufsize=1,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        self.responses=queue.Queue();self.outbound=queue.Queue(maxsize=1);self.lock=threading.Lock();self.seq=0
        threading.Thread(target=self._read,args=(self.process.stdout,self.responses),daemon=True,name='YumiThreeVRM').start()
        threading.Thread(target=self._write,args=(self.process.stdin,self.outbound,self.responses),daemon=True,name='YumiThreeVRMWrite').start()
    @staticmethod
    def _read(stream,responses):
        try:
            for line in stream:
                try:responses.put(json.loads(line))
                except ValueError:responses.put({'ok':False,'error':'Invalid runtime response'})
        finally:responses.put({'ok':False,'error':'three-vrm runtime stopped'})
    @staticmethod
    def _write(stream,outbound,responses):
        while True:
            line=outbound.get()
            if line is None:return
            try:stream.write(line);stream.flush()
            except (OSError,ValueError):
                responses.put({'ok':False,'error':'three-vrm transport closed'});return
    def request(self,payload,timeout=.10):
        with self.lock:
            if self.process.poll() is not None:raise RuntimeError3D('three-vrm çalışma zamanı kapandı.')
            self.seq+=1;payload={**payload,'seq':self.seq}
            try:
                self.outbound.put_nowait(json.dumps(payload,allow_nan=False,separators=(',',':'))+'\n')
                result=self.responses.get(timeout=timeout)
            except (OSError,queue.Empty,queue.Full) as error:
                self.close();raise RuntimeError3D('three-vrm yanıt vermedi; modelin kaynak pozu korundu.') from error
            if not result.get('ok'):raise RuntimeError3D(result.get('error','three-vrm error'))
            if result.get('seq')!=self.seq:raise RuntimeError3D('three-vrm frame sequence mismatch')
            return result['result']
    def close(self):
        try:self.outbound.put_nowait(None)
        except queue.Full:pass
        if self.process.poll() is None:
            self.process.terminate()
            try:self.process.wait(timeout=1)
            except subprocess.TimeoutExpired:self.process.kill();self.process.wait(timeout=1)
        for pipe in (self.process.stdin,self.process.stdout):
            if pipe:
                try:pipe.close()
                except OSError:pass

_worker=None
def worker():
    global _worker
    if _worker is None or _worker.process.poll() is not None:_worker=Worker()
    return _worker
def shutdown():
    if _worker is not None:_worker.close()
atexit.register(shutdown)

class ThreeVRMSprings:
    def __init__(self,data):
        self.data=data;self.id=uuid.uuid4().hex;self.last=None;self.closed=False
        self.worker=worker()
        # Pass source declarations unchanged, not reconstructed guessed physics.
        schema={key:data.g.get(key,default) for key,default in (('nodes',[]),('extensions',{}),('extensionsUsed',[]))}
        result=self.worker.request({'op':'init','id':self.id,'json':schema,'local':np.asarray(data.local).transpose(0,2,1).reshape(-1,16).tolist()},timeout=15)
        self.indices=set(result['indices']);self.version=result['version'];self.declarations=result['declarations']
    def apply(self,t,world):
        d=self.data;local=world.copy()
        for n in d.order:
            parent=d.parents.get(n)
            if parent is not None:local[n]=np.linalg.solve(world[parent],world[n])
        dt=1/60 if self.last is None else t-self.last
        reset=self.last is None or dt<0 or dt>.15;self.last=t
        result=self.worker.request({'op':'step','id':self.id,'dt':max(0.,min(dt,.05)),'reset':reset,
            'local':local.transpose(0,2,1).reshape(-1,16).tolist()})
        from vrm import rotation
        for index,q in result['rotations']:
            # Preserve authored nonuniform scale, not only unit rotation.
            scale=np.linalg.norm(local[index,:3,:3],axis=0)
            if np.linalg.det(local[index,:3,:3])<0:scale[0]*=-1
            local[index,:3,:3]=rotation(q)@np.diag(scale)
        for n in d.order:
            parent=d.parents.get(n);world[n]=world[parent]@local[n] if parent is not None else local[n]
    def close(self):
        if self.closed:return
        self.closed=True
        if self.worker.process.poll() is None:
            try:self.worker.request({'op':'close','id':self.id})
            except RuntimeError3D:pass
