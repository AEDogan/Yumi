"""Conversation backends, local voice, and live weather follow-up."""
from __future__ import annotations
import base64, io, json, os, re, shutil, subprocess, threading, wave
from functools import lru_cache
from pathlib import Path
import numpy as np
import requests

ROOT=Path(__file__).resolve().parent
OFFLINE_MESSAGE='Şu an internete bağlı değiliz.'
HIDDEN={'creationflags':subprocess.CREATE_NO_WINDOW} if os.name=='nt' else {}
_whisper=None
_model=None
_model_lock=threading.Lock()

def codex_path():
    candidate=shutil.which('codex')
    fallback=Path(os.environ.get('LOCALAPPDATA',''))/'Programs/OpenAI/Codex/bin/codex.exe'
    return candidate or (str(fallback) if fallback.exists() else None)

def login_status():
    executable=codex_path()
    if not executable: return 'Codex CLI bulunamadı.'
    result=subprocess.run([executable,'login','status'],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=15,**HIDDEN)
    return (result.stdout or result.stderr).strip()

def login():
    executable=codex_path()
    if not executable: raise RuntimeError('Codex CLI kurulu değil.')
    result=subprocess.run([executable,'login'],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=300,**HIDDEN)
    if result.returncode: raise RuntimeError((result.stderr or result.stdout).strip()[-1000:])
    return login_status()

def local_transcribe(samples,wake_name='Yumi'):
    from resource_guard import require_capacity,GiB
    require_capacity(GiB)
    global _model, _whisper
    whisper_dir=ROOT/'models/whisper-small'
    if (whisper_dir/'model.bin').exists():
        from faster_whisper import WhisperModel
        with _model_lock:
            if _whisper is None: _whisper=WhisperModel(str(whisper_dir),device='cpu',compute_type='int8',cpu_threads=4)
        segments,_=_whisper.transcribe(samples,language='tr',beam_size=5,vad_filter=True,initial_prompt=f'{wake_name} adlı sesli asistana Türkçe soru soruyorum. Hava durumu, şehir, İstanbul, Ankara.',condition_on_previous_text=False)
        return ' '.join(segment.text.strip() for segment in segments).strip()
    from vosk import Model, KaldiRecognizer, SetLogLevel
    model_dir=ROOT/'models/vosk-model-small-tr-0.3'
    if not model_dir.exists(): raise RuntimeError('Yerel Türkçe ses modeli eksik. KURULUM.cmd dosyasını çalıştırın.')
    with _model_lock:
        if _model is None:
            SetLogLevel(-1)
            _model=Model(str(model_dir))
    recognizer=KaldiRecognizer(_model,16000)
    pcm=np.clip(samples*32767,-32768,32767).astype('<i2').tobytes()
    parts=[]
    for offset in range(0,len(pcm),8000):
        if recognizer.AcceptWaveform(pcm[offset:offset+8000]): parts.append(json.loads(recognizer.Result()).get('text',''))
    parts.append(json.loads(recognizer.FinalResult()).get('text',''))
    return ' '.join(p for p in parts if p).strip()

def windows_speech(text,data_dir):
    directory=Path(data_dir)
    text_path=directory/'speech-input.txt'
    audio_path=directory/'speech-output.wav'
    text_path.write_text(text,encoding='utf-8')
    input_name=str(text_path).replace("'","''")
    output_name=str(audio_path).replace("'","''")
    script=f"Add-Type -AssemblyName System.Speech; $s=[System.Speech.Synthesis.SpeechSynthesizer]::new(); $v=$s.GetInstalledVoices() | Where-Object {{$_.VoiceInfo.Culture.Name -eq 'tr-TR'}} | Select-Object -First 1; if($v){{$s.SelectVoice($v.VoiceInfo.Name)}}; $s.SetOutputToWaveFile('{output_name}'); $t=[IO.File]::ReadAllText('{input_name}',[Text.Encoding]::UTF8); $s.Speak($t); $s.Dispose()"
    encoded=base64.b64encode(script.encode('utf-16-le')).decode('ascii')
    result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-EncodedCommand',encoded],capture_output=True,timeout=90,**HIDDEN)
    if result.returncode: raise RuntimeError('Windows ses motoru yanıt üretemedi.')
    return audio_path.read_bytes()

_piper=None
_piper_lock=threading.Lock()
def piper_speech(text):
    from resource_guard import require_capacity,GiB
    require_capacity(GiB)
    global _piper
    from piper import PiperVoice
    model=ROOT/'models/piper/tr_TR-dfki-medium.onnx'
    if not model.exists() or model.stat().st_size<1000000:raise RuntimeError('Yerel Türkçe Piper ses modeli henüz hazır değil.')
    with _piper_lock:
        if _piper is None:_piper=PiperVoice.load(str(model))
        buffer=io.BytesIO()
        with wave.open(buffer,'wb') as output:_piper.synthesize_wav(text,output)
        return buffer.getvalue()

class SpeechAudio(bytes):
    def __new__(cls,audio,boundaries=()):
        result=super().__new__(cls,audio);result.boundaries=tuple(boundaries);return result

@lru_cache(maxsize=32)
def local_speech(text,data_dir,voice='gemini-live:Kore'):
    raise RuntimeError('Eski TTS motorları kapalı. Native canlı ses ayrı Gemini Live denemesindedir.')


def chatterbox_speech(text):
    """Generate Turkish speech through the local Ultimate TTS Gradio service."""
    from app_paths import env_value
    base=env_value('CHATTERBOX_URL','http://127.0.0.1:7861').rstrip('/')
    api=base+'/gradio_api'
    try:
        endpoint=requests.get(api+'/info',timeout=5).json()['named_endpoints']['/generate_unified_tts']
        data=[item.get('parameter_default') for item in endpoint['parameters']]
        data[0]=text
        data[1]='Chatterbox Multilingual'
        data[2]='wav'
        data[10]='tr'
        response=requests.post(api+'/call/generate_unified_tts',json={'data':data},timeout=10)
        response.raise_for_status()
        event_id=response.json()['event_id']
        with requests.get(api+'/call/generate_unified_tts/'+event_id,stream=True,timeout=(5,120)) as result:
            result.raise_for_status()
            for line in result.iter_lines(decode_unicode=True):
                if not line or not line.startswith('data: '):continue
                output=json.loads(line[6:])
                if isinstance(output,list) and output and isinstance(output[0],dict):
                    sound=output[0]
                    path=Path(sound['path'])
                    if path.is_file():return path.read_bytes()
                    url=sound.get('url')
                    if url:
                        audio=requests.get(url,timeout=30)
                        audio.raise_for_status()
                        return audio.content
                if isinstance(output,dict) and output.get('error'):
                    raise RuntimeError(str(output['error']))
        raise RuntimeError('Ses motoru boş çıktı döndürdü.')
    except (requests.RequestException,KeyError,ValueError,IndexError) as error:
        raise RuntimeError('Yerel Chatterbox ses uygulamasına ulaşılamadı veya ses üretilemedi.') from error

def is_offline_error(error):
    """Only turn recognizable transport failures into an offline reply."""
    current=error
    while current is not None:
        if isinstance(current,(requests.ConnectionError,requests.ConnectTimeout,ConnectionError)):
            return True
        current=current.__cause__
    message=str(error).casefold()
    return any(word in message for word in (
        'name resolution','dns','network is unreachable','connection refused',
        'failed to connect','could not connect','internet connection',
        'network connection','getaddrinfo failed'))


def offline_warning_speech(data_dir,voice):
    """Use the same selected voice; never switch a female profile to a male voice."""
    import hashlib
    directory=Path(data_dir)
    name=hashlib.sha256(voice.encode('utf-8')).hexdigest()[:16]
    path=directory/('offline-warning-'+name+('.wav' if voice in ('piper-tr','windows','chatterbox-tr') else '.mp3'))
    if path.exists() and path.stat().st_size>100:return path.read_bytes()
    audio=local_speech(OFFLINE_MESSAGE,directory,voice)
    temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_bytes(audio);temporary.replace(path)
    return audio


def prepare_offline_warning(data_dir,voice):
    try:offline_warning_speech(data_dir,voice)
    except Exception:pass  # Online service may be unavailable; the selected voice stays unchanged.


class Assistant:
    def __init__(self,settings,data_dir):
        self.settings=settings
        self.data_dir=Path(data_dir)
        self.history=[]
        self.pending_weather=False
        self.weather_city=''
        self.weather_tomorrow=False
        self.weather_locations={}
        self.web=None;self.web_lock=threading.Lock();self.reply_cancel=threading.Event()
        self.chat_scope=None;self.chat_urls={}

    def warm_browser(self):
        if self.settings.get('provider') not in ('chatgpt-web','gemini-web'):return
        with self.web_lock:
            if self.web is None:
                from browser_chat import BrowserChat
                self.web=BrowserChat(self.data_dir)
        return self.web.warm(self.settings['provider'])

    def browser_login(self,finish=False):
        with self.web_lock:
            if self.web is None:
                from browser_chat import BrowserChat
                self.web=BrowserChat(self.data_dir)
        provider=self.settings.get('provider','chatgpt-web')
        if provider not in ('chatgpt-web','gemini-web'):provider='chatgpt-web'
        if finish:return self.web.finish_login(provider)
        else:return self.web.show_login(provider)

    def begin_reply(self):
        self.reply_cancel.clear()

    def cancel_reply(self):
        self.reply_cancel.set()
        if self.web:self.web.cancel_request()

    def close(self):
        self.cancel_reply()
        if self.web:self.web.close()

    def ask(self,text,key='',previous=None):
        if self.settings.get('provider') in ('chatgpt-web','gemini-web'):return self.stream_ask(text,key,previous)
        lowered=text.lower()
        if self.weather_city and ('kaynak' in lowered or 'nereden aldın' in lowered):
            message='Open-Meteo verilerini kullanıyorum.';self._remember(text,message);return message,previous
        weather=any(term in lowered for term in ['hava durumu','hava nasıl','hava bugün','hava yarın','kaç derece']) or (bool(self.weather_city) and lowered.strip(' ?!.') in ('yarın','peki yarın','ya yarın'))
        if weather or self.pending_weather:
            place=text if self.pending_weather and not weather else self._place_in_text(text)
            if not place: place=self.settings.get('city','').strip() or self.weather_city
            if not place:
                self.pending_weather=True
                self.weather_tomorrow='yarın' in lowered
                message='Hangi şehir için hava durumunu öğrenmek istiyorsun?'
            else:
                was_pending=self.pending_weather
                self.pending_weather=False
                message=self._weather(place,self.weather_tomorrow if was_pending else 'yarın' in lowered)
            self._remember(text,message)
            return message,previous
        if self.settings.get('provider','codex')=='openai':
            from api import answer
            message,new_id=answer(key,text,previous,self.settings['model'],history=self.history)
        elif self.settings.get('provider')=='gemini':
            from gemini_api import answer as gemini_answer
            message,new_id=gemini_answer(key,text,self.history,self.settings.get('gemini_model','gemini-3.5-flash-lite'))
        else:
            message=self._codex(text)
            new_id=None
        self._remember(text,message)
        return message,new_id

    def stream_ask(self,text,key='',previous=None,on_chunk=None,on_status=None):
        if self.settings.get('provider') in ('chatgpt-web','gemini-web'):
            # Warm-up belongs to startup. Running it before every question
            # adds a second readiness loop and can consume the user's request.
            with self.web_lock:
                if self.web is None:
                    from browser_chat import BrowserChat
                    self.web=BrowserChat(self.data_dir)
            if on_status:on_status('Web sohbetine bağlanıyor…')
            with self.web.lock:
                self.web.use_conversation(self.chat_scope,self.chat_urls)
                self.web.ensure(self.settings['provider'])
                message=self.web.ask(text,on_chunk,on_status=on_status)
            self._remember(text,message);return message,None
        lowered=text.lower()
        if self.weather_city and ('kaynak' in lowered or 'nereden aldın' in lowered):
            message='Open-Meteo verilerini kullanıyorum.'
            if on_chunk:on_chunk(message)
            self._remember(text,message);return message,previous
        weather=any(term in lowered for term in ['hava durumu','hava nasıl','hava bugün','hava yarın','kaç derece']) or (bool(self.weather_city) and lowered.strip(' ?!. ') in ('yarın','peki yarın','ya yarın'))
        if weather or self.pending_weather:
            place=text if self.pending_weather and not weather else self._place_in_text(text)
            if not place:place=self.settings.get('city','').strip() or self.weather_city
            if not place:
                self.pending_weather=True;self.weather_tomorrow='yarın' in lowered
                message='Hangi şehir için hava durumunu öğrenmek istiyorsun?'
            else:
                was_pending=self.pending_weather;self.pending_weather=False
                message=self._weather(place,self.weather_tomorrow if was_pending else 'yarın' in lowered)
            if on_chunk:on_chunk(message)
            self._remember(text,message);return message,previous
        if self.settings.get('provider')=='gemini':
            from gemini_api import stream_answer as gemini_stream
            from voice_profiles import character_name
            message,new_id=gemini_stream(key,text,self.history,self.settings.get('gemini_model','gemini-3.5-flash-lite'),on_chunk=on_chunk,cancel=self.reply_cancel,on_status=on_status,name=character_name(self.settings))
        elif self.settings.get('provider')=='openai':
            from api import answer
            message,new_id=answer(key,text,previous,self.settings['model'],history=self.history)
            if on_chunk:on_chunk(message)
        else:
            message=self._codex(text);new_id=None
            if on_chunk:on_chunk(message)
        self._remember(text,message)
        return message,new_id

    def _remember(self,text,message):
        self.history.extend([{'role':'user','text':text},{'role':'assistant','text':message}])
        self.history=self.history[-24:]

    def _place_in_text(self,text):
        text=re.sub(r'(?i)bugün|yarın|hava durumu|hava nasıl|kaç derece|söyler misin|öğrenmek istiyorum|nasıl|için|olacak|nedir|söyle|peki|hava',' ',text)
        text=re.sub(r"['’](da|de|ta|te|nın|nin|nun|nün)\b",'',text,flags=re.I)
        return re.sub(r'[?!.,]',' ',text).strip()

    def _weather(self,place,tomorrow=False):
        location_key=place.strip().casefold()
        loc=self.weather_locations.get(location_key)
        if loc is None:
            response=requests.get('https://geocoding-api.open-meteo.com/v1/search',params={'name':place,'count':3,'language':'tr','format':'json'},timeout=20)
            response.raise_for_status()
            locations=response.json().get('results',[])
            if not locations:
                self.pending_weather=True
                return f'{place} için bir yer bulamadım. Şehir veya ilçeyi bir kez daha söyler misin?'
            loc=locations[0]
            self.weather_locations[location_key]=loc
            self.weather_locations[loc['name'].casefold()]=loc
        self.weather_city=loc['name']
        response=requests.get('https://api.open-meteo.com/v1/forecast',params={'latitude':loc['latitude'],'longitude':loc['longitude'],'current':'temperature_2m,weather_code','daily':'temperature_2m_max,temperature_2m_min,precipitation_probability_max','timezone':'auto','forecast_days':2},timeout=20)
        response.raise_for_status()
        data=response.json(); day=1 if tomorrow else 0
        daily=data['daily']; current=data['current']
        code=current['weather_code']
        desc='açık' if code==0 else 'parçalı bulutlu' if code<=2 else 'bulutlu' if code==3 else 'sisli' if code<=48 else 'yağışlı' if code<71 else 'karlı' if code<85 else 'sağanaklı'
        probability=daily['precipitation_probability_max'][day]
        rain='Yağmur beklenmiyor.' if probability<10 else 'Yağmur ihtimali düşük.' if probability<30 else 'Yağmur ihtimali var.' if probability<60 else 'Yağmur olasılığı yüksek.'
        if tomorrow:return f"{loc['name']} için yarın {daily['temperature_2m_min'][day]:.0f}–{daily['temperature_2m_max'][day]:.0f} derece. "+rain
        return f"{loc['name']} için şu an {current['temperature_2m']:.0f} derece, {desc}. "+rain

    def _codex(self,text):
        executable=codex_path()
        if not executable: raise RuntimeError('Codex CLI bulunamadı. Ayarlardan OpenAI API seçebilir veya Codex kurabilirsiniz.')
        prompt=('Sen Yumi adlı masaüstü sesli asistanısın. Kullanıcı Ahmet ile doğal Türkçe konuş. '
                'Türkçe düşünülmüş gibi akıcı, gündelik ve anlaşılır cümleler kur; kelime kelime çeviri gibi ifadelerden kaçın. '
                'Sen diye hitap et. İlk cümlede soruya doğrudan cevap ver. Selamı her yanıtta tekrarlama, kendini tanıtma. '
                'Varsayılan yanıtın bir veya iki kısa cümle olsun. Kullanıcı ayrıntı isterse genişlet. Kendiliğinden tarih, kaynak adı veya gereksiz teknik bilgi sayma. '
                'Konuşma geçmişindeki şehir, tercih ve takip sorularını kullan; belirsizlik varsa tek net soru sor. '
                'Sesli okunacak metinde tablo, emoji ve Markdown kullanma; doğal duraklar için noktalama kullan. '
                'Gerçekten erişmediğin ekranı gördüğünü veya bilgisayarda işlem yaptığını söyleme. '
                'Dosya okuma veya terminal komutu çalıştırma. Güncel bilgi gerektiğinde web araması kullan.\n')
        prompt+='Önceki konuşma: '+json.dumps(self.history,ensure_ascii=False)+'\nKullanıcı: '+text
        sandbox=self.data_dir/'conversation'; sandbox.mkdir(exist_ok=True)
        command=[executable,'exec','--ignore-user-config','--skip-git-repo-check','--sandbox','read-only','--ephemeral','--json','-c','web_search="cached"','-c','model_reasoning_effort="low"','-C',str(sandbox),'-']
        result=subprocess.run(command,input=prompt,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=150,**HIDDEN)
        messages=[]
        for line in result.stdout.splitlines():
            try:
                event=json.loads(line)
                item=event.get('item',{})
                if event.get('type')=='item.completed' and item.get('type')=='agent_message': messages.append(item.get('text',''))
            except ValueError: pass
        if result.returncode or not messages:
            detail=(result.stderr or result.stdout)[-1500:]
            if 'login' in detail.lower() or '401' in detail: raise RuntimeError('Codex oturumu açık değil. Ayarlardaki Codex ile giriş düğmesini kullanın.')
            raise RuntimeError('Codex yanıt veremedi: '+detail)
        return messages[-1]
