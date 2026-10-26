"""Local Discogs-EffNet inference, bounded RAM windows and conservative labels."""
from collections import deque
from pathlib import Path
import json,queue,threading,time
import numpy as np

FOLDER=Path(__file__).resolve().parent/'models'/'music'

def family(label):
    group,_,style=label.casefold().partition('---')
    if group=='non-music':return 'speech'
    exact={'k-pop':'k-pop','lo-fi':'lo-fi','afrobeat':'afrobeats','salsa':'salsa',
           'reggaeton':'reggaeton','dancehall':'dancehall','ambient':'ambient',
           'dark ambient':'ambient','disco':'disco','nu-disco':'disco','funk':'funk',
           'p.funk':'funk','rhythm & blues':'r&b','contemporary r&b':'r&b',
           'neo soul':'soul','soul':'soul','country':'country','folk':'folk',
           'dubstep':'dubstep','drum n bass':'drum & bass','jungle':'drum & bass'}
    if style in exact:return exact[style]
    if 'metal' in style or style in ('thrash','grindcore','deathcore'):return 'metal'
    if 'punk' in style or style in ('hardcore','crust'):return 'punk'
    if 'indie' in style or style=='alternative rock':return 'indie'
    if 'house' in style:return 'house'
    if 'techno' in style:return 'techno'
    if 'trance' in style:return 'trance'
    return {'hip hop':'hip-hop','jazz':'jazz','blues':'blues','classical':'classical',
            'pop':'pop','rock':'rock','reggae':'reggae','funk / soul':'soul'}.get(group,'unknown')

def resample(samples,rate):
    samples=np.asarray(samples,np.float32)
    if rate==16000:return samples
    if rate<8000 or rate>192000:raise ValueError('Unsupported audio sample rate')
    if rate>16000:
        n=np.arange(-48,49);cutoff=7200./rate
        kernel=2*cutoff*np.sinc(2*cutoff*n)*np.hamming(len(n));kernel/=kernel.sum()
        samples=np.convolve(samples,kernel,mode='same')
    return np.interp(np.arange(int(len(samples)*16000/rate))*rate/16000,np.arange(len(samples)),samples).astype(np.float32)

def mel_filters():
    # Slaney mel coordinates, triangular filters with unit area in Hz.
    def hz(m):return np.where(m<15,m*(200./3),1000*np.exp((m-15)*np.log(6.4)/27))
    edges=hz(np.linspace(0,15+np.log(8)*27/np.log(6.4),98));frequency=np.arange(257)*16000/512
    filters=np.maximum(0,np.minimum((frequency[None,:]-edges[:-2,None])/(edges[1:-1]-edges[:-2])[:,None],(edges[2:,None]-frequency[None,:])/(edges[2:]-edges[1:-1])[:,None]))
    return (filters*2/(edges[2:]-edges[:-2])[:,None]).astype(np.float32)

FILTERS=mel_filters()
def stationary_tone(samples,rate):
    """A steady single oscillator is insufficient evidence of music."""
    n=4096
    if len(samples)<n*2:return False
    starts=np.linspace(0,len(samples)-n,8).astype(int)
    frames=np.stack([samples[i:i+n] for i in starts]);power=np.abs(np.fft.rfft(frames*np.hanning(n),axis=1))**2
    peaks=np.argmax(power,axis=1);concentration=[]
    for row,peak in zip(power,peaks):concentration.append(row[max(0,peak-1):peak+2].sum()/max(row.sum(),1e-12))
    levels=np.sqrt(np.mean(frames*frames,axis=1))
    return bool(np.min(concentration)>.985 and np.ptp(peaks)<=1 and np.std(levels)<np.mean(levels)*.025)

def features(samples,rate):
    samples=resample(samples,rate)
    if len(samples)<16000*4:raise ValueError('At least four seconds of audio required')
    padded=np.pad(samples,(256,256));frames=np.lib.stride_tricks.sliding_window_view(padded,512)[::256]
    power=np.abs(np.fft.rfft(frames*np.hanning(512),axis=1))**2
    mel=np.log10(1+10000*(power@FILTERS.T)).astype(np.float32)
    starts=np.linspace(0,max(0,len(mel)-128),min(4,max(1,len(mel)//128))).astype(int)
    return np.stack([mel[i:i+128] for i in starts])

class GenreClassifier:
    def __init__(self):
        import onnxruntime as ort
        options=ort.SessionOptions();options.intra_op_num_threads=1;options.inter_op_num_threads=1
        self.session=ort.InferenceSession(str(FOLDER/'discogs-effnet-bsdynamic-1.onnx'),sess_options=options,providers=['CPUExecutionProvider'])
        self.labels=json.loads((FOLDER/'discogs-effnet-bsdynamic-1.json').read_text())['classes']
        self.groups={name:[i for i,label in enumerate(self.labels) if family(label)==name] for name in set(map(family,self.labels))}
    def predict(self,samples,rate):
        if not np.isfinite(samples).all() or np.sqrt(np.mean(np.square(samples)))<.0015:return {'genre':'unknown','genre_score':0.,'music_detected':False}
        if stationary_tone(samples,rate):return {'genre':'unknown','genre_score':0.,'music_detected':False}
        # A system-volume change must not turn the same song into a different
        # genre. Reject inaudible input first, then normalize only the private
        # inference window; never change speaker volume or the beat meter.
        samples=np.asarray(samples,np.float32)
        rms=float(np.sqrt(np.mean(samples*samples)));peak=float(np.max(np.abs(samples)))
        samples=samples*min(.25/max(rms,1e-9),.98/max(peak,1e-9))
        activations=self.session.run(['activations'],{'melspectrogram':features(samples,rate)})[0]
        scores=np.mean(activations,axis=0)
        ranked=sorted(((float(np.max(scores[indices])),name) for name,indices in self.groups.items() if name not in ('unknown','speech')),reverse=True)
        first,name=ranked[0];second=ranked[1][0]
        speech=float(np.max(scores[self.groups.get('speech',[])])) if self.groups.get('speech') else 0.
        # Conflicting short patches should be disclosed as ambiguity instead
        # of turning a mixed/processed output into a confident genre claim.
        votes=[]
        for patch in activations:
            ranked_patch=sorted(((float(np.max(patch[indices])),group) for group,indices in self.groups.items() if group not in ('unknown','speech')),reverse=True)
            votes.append(ranked_patch[0][1])
        agreement=votes.count(name)/max(1,len(votes))
        accepted=first>=.20 and first-second>=.08 and first>=second*1.15 and speech<max(.15,first*.9) and agreement>.5
        music=False if speech>=max(.15,first*.9) else True if first>=.20 else None
        return {'genre':name if accepted else 'unknown','genre_score':first,'music_detected':music,'genre_agreement':agreement,'genre_candidates':[(n,round(v,3)) for v,n in ranked[:3]]}

class GenreStability:
    """Require two accepted windows, allowing bounded compatible ambiguity.

    An ambiguous window never supplies a vote or publishes a genre. It may
    retain a pending accepted vote only when its leading evidence agrees.
    """
    def __init__(self):
        self.candidate=None;self.count=0;self.accepted_at=None;self.last_stamp=None

    def update(self,result,stamp):
        if not np.isfinite(stamp):
            self.__init__();return 'unknown'
        if self.last_stamp is not None and stamp<=self.last_stamp:
            self.__init__();return 'unknown'
        self.last_stamp=stamp
        if self.accepted_at is not None and stamp-self.accepted_at>12.:
            self.candidate=None;self.count=0;self.accepted_at=None
        genre=result['genre']
        if genre=='unknown':
            ranked=result.get('genre_candidates',[])
            compatible=(result.get('music_detected') is True and ranked and
                        ranked[0][0]==self.candidate and
                        result.get('genre_score',0.)>=.20 and
                        result.get('genre_agreement',0.)>.5)
            if not compatible:self.candidate=None;self.count=0;self.accepted_at=None
            return 'unknown'
        self.count=self.count+1 if genre==self.candidate else 1
        self.candidate=genre;self.accepted_at=stamp
        return genre if self.count>=2 else 'unknown'

class OutputGenre:
    def __init__(self):
        self.queue=queue.Queue(maxsize=1);self.stop_event=threading.Event();self.state={'genre':'unknown','genre_score':0.,'genre_stamp':0.}
        self.generation=0
        self.thread=threading.Thread(target=self._run,daemon=True,name='YumiLocalMusicGenre');self.thread.start()
    def offer(self,samples,rate,stamp):
        try:self.queue.put_nowait((samples,rate,stamp,self.generation))
        except queue.Full:pass
    def reset(self):
        self.generation+=1;self.state={'genre':'unknown','genre_score':0.,'genre_stamp':0.}
    def close(self):self.stop_event.set()
    def _run(self):
        try:
            classifier=GenreClassifier();stability=GenreStability();seen=self.generation
            while not self.stop_event.is_set():
                try:samples,rate,stamp,generation=self.queue.get(timeout=.2)
                except queue.Empty:continue
                if generation!=self.generation:continue
                if generation!=seen:stability=GenreStability();seen=generation
                result=classifier.predict(samples,rate)
                if self.stop_event.is_set():break
                if generation!=self.generation:continue
                # Music presence must not wait for a stable genre label. A
                # hip-hop/dubstep ambiguity previously hid positive music
                # evidence forever, so automatic dancing never started.
                label=stability.update(result,stamp)
                self.state={**result,'genre':label,'genre_stamp':stamp}
        except Exception:
            self.state={'genre':'unknown','genre_score':0.,'genre_stamp':0.,'genre_error':'Yerel tür modeli yüklenemedi; medya etiketi veya elle seçim kullanılabilir.'}
