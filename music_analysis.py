"""Bounded output-only rhythm analysis; audio stays in RAM on this computer."""
from collections import deque
import math,threading,time,queue
import numpy as np

GENRES=('pop','rock','indie','punk','metal','hip-hop','r&b','soul','funk','disco',
        'house','techno','trance','drum & bass','dubstep','ambient','lo-fi','jazz',
        'blues','country','folk','reggae','dancehall','reggaeton','salsa','bachata',
        'afrobeats','k-pop','latin pop','classical')
ALIASES={'rap':'hip-hop','hip hop':'hip-hop','alternative':'indie','rnb':'r&b',
         'orchestral':'classical','klasik':'classical','klasik müzik':'classical',
         'akustik':'folk','acoustic':'folk','lofi':'lo-fi','dnb':'drum & bass',
         'türkçe pop':'pop','turkish pop':'pop','elektronik':'house'}

def genre_name(text):
    text=str(text).casefold().strip()
    return text if text in GENRES else ALIASES.get(text,'unknown')


def output_channel(output,selected=None):
    """Retain audible loopback data even when stereo channels oppose in phase."""
    output=np.asarray(output,dtype=np.float32)
    if output.ndim!=2 or not output.shape[1]:raise ValueError('Invalid output channel layout')
    if not len(output) or not np.isfinite(output).all():return np.zeros(len(output),np.float32),None
    energy=np.mean(output*output,axis=0);strongest=int(np.argmax(energy))
    if selected is None or not 0<=selected<len(energy) or energy[selected]<energy[strongest]*.04:selected=strongest
    return output[:,selected],selected


class RhythmTracker:
    def __init__(self):
        self.history=deque(maxlen=1200);self.previous=None;self.updated=-math.inf
        self.bpm=0.;self.confidence=0.;self.beat_time=0.;self.level=0.

    def feed(self,samples,rate,stamp):
        samples=np.asarray(samples,dtype=float)
        if not len(samples) or rate<=0 or not np.isfinite(samples).all() or not math.isfinite(stamp):
            self.confidence=0.;return
        if self.history and (stamp<=self.history[-1][0] or stamp-self.history[-1][0]>.25):
            self.history.clear();self.previous=None;self.bpm=0.;self.confidence=0.;self.updated=-math.inf
        rms=float(np.sqrt(np.mean(samples*samples)))
        self.level=max(rms,self.level*math.exp(-len(samples)/rate/.4))
        spectrum=np.abs(np.fft.rfft(samples*np.hanning(len(samples))))
        spectrum=np.log1p(spectrum)
        flux=0. if self.previous is None or len(self.previous)!=len(spectrum) else float(np.maximum(0.,spectrum-self.previous).mean())
        self.previous=spectrum;self.history.append((stamp,flux,self.level))
        if stamp-self.updated<.75:return
        self.updated=stamp
        rows=np.array(self.history);rows=rows[rows[:,0]>=stamp-10.]
        if len(rows)<80 or rows[-1,0]-rows[0,0]<3 or self.level<.0015:
            self.confidence=0.;return
        step=float(np.median(np.diff(rows[:,0])))
        if step<=0:return
        onset=rows[:,1];onset=np.maximum(0.,onset-np.median(onset))
        energy=float(onset@onset)
        if energy<1e-10:self.confidence=0.;return
        candidates=[]
        for lag in range(max(2,round(60/185/step)),min(len(onset)//2,round(60/60/step))+1):
            a=onset[:-lag];b=onset[lag:]
            score=float(a@b)/max(math.sqrt(float(a@a)*float(b@b)),1e-12)
            candidates.append((score,lag))
        score,lag=max(candidates)
        # Prefer the first strong repeat rather than a slower octave of it.
        lag=min(l for s,l in candidates if s>=max(.4,score*.94)) if score>=.4 else lag
        bpm=60/(lag*step)
        peaks=np.flatnonzero((onset[1:-1]>onset[:-2])&(onset[1:-1]>=onset[2:])&(onset[1:-1]>onset.max()*.10))+1
        if len(peaks)>1:
            selected=[int(peaks[0])]
            for peak in peaks[1:]:
                if rows[peak,0]-rows[selected[-1],0]>=.18:selected.append(int(peak))
                elif onset[peak]>onset[selected[-1]]:selected[-1]=int(peak)
            peaks=np.array(selected,int)
        if len(peaks)<4:self.confidence=0.;return
        intervals=np.diff(rows[peaks,0]);period=float(np.median(intervals))
        regularity=float(np.mean(abs(intervals-period)<period*.15))
        if 60/185<=period<=1.02 and regularity>=.75:
            # Quantized FFT blocks can give a stronger two-beat autocorrelation
            # than one beat. Observed, regular onset intervals resolve that
            # octave ambiguity without inventing extra beats between attacks.
            bpm=60/period;score=max(score,regularity*.95)
        self.confidence=float(np.clip(score,0.,1.))
        self.bpm=bpm if not self.bpm or abs(bpm-self.bpm)>15 else self.bpm*.75+bpm*.25
        # Anchor on an observed onset, not on render delta or a guessed clock.
        self.beat_time=float(rows[peaks[-1],0])

    def snapshot(self,stamp):
        return {'bpm':self.bpm,'confidence':self.confidence if stamp-self.updated<2 else 0.,
                'beat_time':self.beat_time,'level':self.level,'stamp':stamp}


class OutputRhythm:
    def __init__(self):
        self.thread=None;self.stop_event=threading.Event();self.paused=False
        self.state={'bpm':0.,'confidence':0.,'level':0.,'beat_time':0.,'stamp':0.,'error':None,'ready':False}
        self.lock=threading.Lock()
        self.track_generation=0
    def reset_track(self):
        self.track_generation+=1
        with self.lock:self.state={**self.state,'genre':'unknown','genre_stamp':0.,'music_detected':None,'confidence':0.,'bpm':0.,'beat_time':0.,'level':0.}
    def start(self):
        if self.thread and self.thread.is_alive():
            if not self.stop_event.is_set():return
            self.thread.join(.3)
            if self.thread.is_alive():
                with self.lock:self.state={**self.state,'error':'Ses aygıtı kapanıyor; birkaç saniye sonra yeniden dene.'}
                return
        with self.lock:self.state={'bpm':0.,'confidence':0.,'level':0.,'beat_time':0.,'stamp':0.,'error':None,'ready':False}
        self.stop_event.clear();self.thread=threading.Thread(target=self._run,daemon=True,name='YumiOutputRhythm');self.thread.start()
    def stop(self):self.stop_event.set()
    def snapshot(self):
        with self.lock:return dict(self.state)
    def _run(self):
        genre_worker=None
        try:
            import pyaudiowpatch as pa
            with pa.PyAudio() as audio:
                device=audio.get_default_wasapi_loopback()
                if not device.get('isLoopbackDevice'):raise ValueError('Çıkış loopback aygıtı bulunamadı.')
                channels=int(device['maxInputChannels']);rate=int(device['defaultSampleRate'])
                if not 1<=channels<=16:raise ValueError('Ses çıkışı kanal sayısı desteklenmiyor.')
                tracker=RhythmTracker();decimate=max(1,rate//12000);was_paused=False
                from music_genre import OutputGenre
                genre_worker=OutputGenre();genre_blocks=deque(maxlen=max(1,int(rate*10/1024)));next_genre=0.;generation=self.track_generation
                blocks=queue.Queue(maxsize=16);selected_channel=None;previous_stamp=None
                def callback(data,count,timing,status):
                    if self.stop_event.is_set():return None,pa.paComplete
                    block=(data,float(timing.get('input_buffer_adc_time',0.)),status,time.perf_counter())
                    try:blocks.put_nowait(block)
                    except queue.Full:
                        # Keep the newest sound, not a growing stale backlog.
                        try:blocks.get_nowait()
                        except queue.Empty:pass
                        try:blocks.put_nowait(block)
                        except queue.Full:pass
                    return None,pa.paContinue
                with audio.open(format=pa.paFloat32,channels=channels,rate=rate,input=True,
                                input_device_index=int(device['index']),frames_per_buffer=1024,stream_callback=callback) as stream:
                    origin=time.perf_counter()-stream.get_time()
                    with self.lock:self.state={**self.state,'ready':True,'error':None}
                    while not self.stop_event.is_set():
                        try:block,adc_time,status,captured_at=blocks.get(timeout=.15)
                        except queue.Empty:continue
                        if generation!=self.track_generation:
                            generation=self.track_generation;genre_blocks.clear();genre_worker.reset();tracker=RhythmTracker();next_genre=0.
                        if self.paused:
                            if not was_paused:
                                tracker=RhythmTracker();genre_blocks.clear();genre_worker.reset();next_genre=0.;was_paused=True
                                with self.lock:self.state={**self.state,'genre':'unknown','genre_stamp':0.,'music_detected':None,'confidence':0.,'level':0.,'bpm':0.}
                            continue
                        was_paused=False
                        output=np.frombuffer(block,dtype=np.float32).reshape(-1,channels)
                        # Surround/headphone effects can put opposite phase in
                        # L/R. Averaging cancels music before genre inference.
                        # Keep one energetic channel; avoid hopping on small pans.
                        prior_channel=selected_channel
                        mono,selected_channel=output_channel(output,selected_channel)
                        stamp=origin+adc_time if adc_time else captured_at
                        discontinuity=status or (previous_stamp is not None and
                            not 0<stamp-previous_stamp<1024/rate*1.5)
                        if discontinuity or (prior_channel is not None and prior_channel!=selected_channel):
                            # Missing blocks/channel splices are not continuous
                            # music. Never classify them as an intact window.
                            tracker=RhythmTracker();genre_blocks.clear();genre_worker.reset();next_genre=0.
                        previous_stamp=stamp
                        samples=mono[::decimate]
                        tracker.feed(samples,rate/decimate,stamp)
                        genre_blocks.append(mono)
                        if stamp>=next_genre and sum(map(len,genre_blocks))>=rate*8:
                            genre_worker.offer(np.concatenate(genre_blocks),rate,stamp);next_genre=stamp+4.
                        with self.lock:self.state={**tracker.snapshot(stamp),**genre_worker.state,'error':None,'ready':True}
        except Exception as error:
            with self.lock:self.state={**self.state,'confidence':0.,'level':0.,'error':str(error)[:180],'ready':False}
        finally:
            if genre_worker:genre_worker.close()
            with self.lock:self.state={**self.state,'ready':False}
