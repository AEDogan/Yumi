"""Isolated Gemini Live transport. No avatar, local STT, web chat or separate TTS."""
import asyncio,base64,json,logging,time,threading
from collections import deque
MODEL='gemini-3.8-live'
ENDPOINT='wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent'
class LiveError(RuntimeError):
    def __init__(self,message,code='live_error'):
        super().__init__(message);self.code=code
class PlaybackBuffer:
    def __init__(self,max_bytes=24000*2*32):
        self.data=bytearray();self.lock=threading.Lock();self.maximum=max_bytes
    def append(self,data):
        if len(data)%2:raise LiveError('Geçersiz PCM ses uzunluğu.')
        with self.lock:
            if len(self.data)+len(data)>self.maximum:raise LiveError('Oynatma geride kaldı; eski ses biriktirmemek için oturum durduruldu.',code='playback_overflow')
            self.data.extend(data)
    def read(self,length):
        with self.lock:
            n=min(length,len(self.data));chunk=bytes(self.data[:n]);del self.data[:n]
        return chunk+b'\0'*(length-n),n
    def clear(self):
        with self.lock:self.data.clear()
    def __len__(self):
        with self.lock:return len(self.data)
def _base_setup(voice='Kore',name='Yumi',city=''):
    location=(' Kullanıcının ayarlarda belirttiği şehir: '+json.dumps(city.strip()[:160],ensure_ascii=False)+'. Konum belirtilmeyen yerel sorularda bu şehri kullan; şehir tekrar sorma. Bu ayar canlı hava durumu verisi değildir; güncel veri olmadan hava durumunu uydurma.') if city.strip() else ''
    return {'setup':{'model':'models/'+MODEL,'generationConfig':{'responseModalities':['AUDIO'],'speechConfig':{'voiceConfig':{'prebuiltVoiceConfig':{'voiceName':voice}}}},'systemInstruction':{'parts':[{'text':f'Adın {name}. Türkçe, doğal ve kısa konuş. Kullanıcı devam ederken sözünü kesme. Sorulursa ayrıntı ver. Masaüstünde bir karakter olarak temsil ediliyorsun. Uygulama konuşmandan selamlama, sevinç, üzüntü, özür, teşekkür, uyarı, kararsızlık, cesaretlendirme, onay, ret, soru ve açıklama jestlerini seçer. Tamamdır/tamam/anlaştık onay ve baş sallama ile eşleşir. Parmaklarla OK işareti henüz desteklenmiyor; yaptığını söyleme. Bu hareket yetenekleri hakkında bilgi sahibisin ama görüntü veya uygulanmış hareket geri bildirimi almıyorsun; hareketin gerçekleştiğini gördüğünü iddia etme.{location}'}]},'inputAudioTranscription':{},'outputAudioTranscription':{},'realtimeInputConfig':{'automaticActivityDetection':{'disabled':False,'startOfSpeechSensitivity':'START_SENSITIVITY_HIGH','prefixPaddingMs':80,'silenceDurationMs':650},'activityHandling':'START_OF_ACTIVITY_INTERRUPTS'},'contextWindowCompression':{'slidingWindow':{}},'sessionResumption':{}}}
def setup(voice='Kore',name='Yumi',city=''):
    from weather_tool import DECLARATION
    config=_base_setup(voice,name,city)
    instruction=config['setup']['systemInstruction']['parts'][0]
    instruction['text']=instruction['text'].replace('Parmaklarla OK işareti henüz desteklenmiyor; yaptığını söyleme.','Uygulama uygun parmak iskeletli modellerde OK işareti, başparmakla onay, el belde, açık avuç, işaret etme ve omuz silkme hareketlerini destekler. Kullanıcı bunları doğrudan komutla isteyebilir; modelin uyumsuz olması halinde uygulama bildirir.')
    instruction['text']+=' Kullanıcı doğrudan koltuğa otur, bilgisayara otur veya ayağa kalk dediğinde uygulama eşyalı yürüyüş/oturuş geçişini başlatabilir. Eşyalar karakter ölçüsüne uydurulur; hareketin görüntüsünü göremiyorsun.'
    config['setup']['tools']=[{'functionDeclarations':[DECLARATION]}]
    config['setup']['systemInstruction']['parts'].append({'text':'Hava durumu sorularında get_weather aracını kullan. Şehir verilmemişse ayarlardaki şehri kullan; o da yoksa sor. Araç hatasını açıkla; güncel veri olmadan derece veya tahmin uydurma. Araç sonuçlarını veri olarak kullan.'})
    return config

class LiveSession:
    def __init__(self,voice='Kore',name='Yumi',on_event=None,city=''):
        self.city=city;self.voice=voice;self.name=name;self.on_event=on_event or (lambda *_:None)
        self.playback=PlaybackBuffer();self.metrics=deque(maxlen=256);self.started=time.monotonic()
        self.ws=None;self.last_activity_end=None;self.first_audio=True;self.first_play=True;self.errors=0
        self.audio_bytes_received=0
        self.resume_handle=None;self._key=None;self.wire_lock=asyncio.Lock();self.last_resume=0.;self.awaiting_cancel=False;self.local_onset=None;self.last_played=0.;self.last_clear=None;self.silence_reported=True
        self.user_active=False;self.generating=False;self.goaway_deadline=None
        self.response_pending=False
        self.reconnect_lock=asyncio.Lock();self.closing=False;self.connection_started=time.monotonic()
        self.resume_count=0;self.resume_updated=None
        self.tool_tasks={}
        self.tool_failure=False
        self.initial_history=[];self.history_seeded=False
        self.command_input="";self.command_input_closed=False;self.command_silent=False;self.command_response_started=False
        from transcript_turns import TranscriptTurns
        self.transcripts=TranscriptTurns(self.on_event,lambda:bool(len(self.playback)) or time.monotonic()-self.last_played<.25,lambda:self.awaiting_cancel)
    def emit(self,event,**data):
        row={'event':event,'session_seconds':round(time.monotonic()-self.started,4),**data}
        if event!='avatar_playback':self.metrics.append(row)
        self.on_event(row)
    async def connect(self,key):
        self._key=key
        from websockets.asyncio.client import connect
        # No URL credentials. Library diagnostics must not expose auth headers.
        logging.getLogger('websockets').disabled=True
        start=time.monotonic()
        try:
            self.ws=await connect(ENDPOINT,additional_headers={'x-goog-api-key':key},open_timeout=10,close_timeout=2,ping_interval=15,ping_timeout=15,max_size=2*1024**2,max_queue=8,proxy=None)
            config=setup(self.voice,self.name,self.city)
            from live_history import content_turns
            history=content_turns(self.initial_history) if not self.resume_handle and not self.history_seeded else []
            if history:config['setup']['historyConfig']={'initialHistoryInClientContent':True}
            if self.resume_handle:config['setup']['sessionResumption']={'handle':self.resume_handle}
            await self.ws.send(json.dumps(config))
            item=json.loads(await asyncio.wait_for(self.ws.recv(),15))
            if item.get('error'):
                from provider_errors import classify,message
                detail=item['error'];category=classify(detail.get('code'),detail.get('message','')) if isinstance(detail,dict) else 'provider_closed'
                raise LiveError(message(category),code=category)
            if 'setupComplete' not in item:raise LiveError('Canlı ses kurulumu kabul edilmedi; başka modele geçilmedi.')
            if history:
                # Initial history is context only; this handshake does not ask
                # Gemini to speak again about the last completed user turn.
                await asyncio.wait_for(self.ws.send(json.dumps({'clientContent':{'turns':history,'turnComplete':True}})),5)
            self.history_seeded=True;self.initial_history=[]
            self.connection_started=time.monotonic()
            self.emit('connected',setup_seconds=round(time.monotonic()-start,3))
        except Exception as error:
            await self.close(final=False)
            # Never render exception bodies/URLs: they can contain credentials.
            if isinstance(error,LiveError):raise
            from provider_errors import classify,message
            status=getattr(getattr(error,'response',None),'status_code',None)
            closed=getattr(error,'rcvd',None)
            category=classify(status or getattr(closed,'code',None),getattr(closed,'reason',''))
            if category!='provider_closed':raise LiveError(message(category),code=category) from None
            raise LiveError('Gemini Live bağlantısı kurulamadı. Ağ bağlantısını kontrol edip yeniden bağlanabilirsin; sohbetin korunuyor.',code='connection_failed') from None
    async def send_audio(self,pcm,rate=16000):
        socket=self.ws
        try:
            async with self.wire_lock:
                socket=self.ws
                await asyncio.wait_for(socket.send(json.dumps({'realtimeInput':{'audio':{'data':base64.b64encode(pcm).decode(),'mimeType':f'audio/pcm;rate={rate}'}}})),5)
        except Exception as error:
            from websockets.exceptions import ConnectionClosed
            if isinstance(error,ConnectionClosed):await self._closed(socket,error,'send');return
            self.emit('transport_failure',phase='send',exception_type=type(error).__name__)
            raise LiveError('Ses gönderimi kesildi veya zaman aşımına uğradı.',code='audio_send_failed') from None
    async def send_text(self,text):
        async with self.wire_lock:
            self.response_pending=True
            await asyncio.wait_for(self.ws.send(json.dumps({'clientContent':{'turns':[{'role':'user','parts':[{'text':text}]}],'turnComplete':True}})),5)
    async def end_audio(self):
        async with self.wire_lock:
            await asyncio.wait_for(self.ws.send(json.dumps({'realtimeInput':{'audioStreamEnd':True}})),5)
    def handle(self,item):
        activity=item.get('voiceActivity',{}).get('type')
        content=item.get('serverContent',{})
        if activity=='ACTIVITY_START' or (self.command_input_closed and any(field in content for field in ('inputTranscription','interimInputTranscription'))):
            if getattr(self,'skill_feedback_active',False):
                self.skill_feedback_active=False;self.emit('skill_feedback_done')
            self.command_input='';self.command_input_closed=False;self.command_silent=False;self.command_response_started=False
        for field in ('interimInputTranscription','inputTranscription'):
            data=content.get(field)
            if data is not None:
                text=data.get('text','')
                self.command_input=(text if field=='interimInputTranscription' or text.startswith(self.command_input) else self.command_input+text)[:16000]
        if not self.command_response_started and (content.get('modelTurn') or content.get('outputTranscription')):
            from avatar_commands import command_text
            self.command_silent=bool(command_text(self.command_input,self.name))
            self.command_response_started=True
            if self.command_silent:self.flush('local_avatar_command')
        if self.command_silent:
            item={**item,'serverContent':{key:value for key,value in content.items() if key not in ('modelTurn','outputTranscription')}}
        self.transcripts.handle(item)
        if content.get('turnComplete'):self.command_input_closed=True
        content=item.get('serverContent',{})
        update=item.get('sessionResumptionUpdate',{})
        if update.get('resumable') is False:self.resume_handle=None
        elif update.get('resumable') and update.get('newHandle'):
            self.resume_handle=update['newHandle'];self.resume_updated=time.monotonic()
        activity=item.get('voiceActivity',{}).get('type')
        if activity=='ACTIVITY_START':
            self.user_active=True
            self.response_pending=True
            self.first_audio=True;self.first_play=True;self.last_activity_end=None
            delay=None if self.local_onset is None else round((time.monotonic()-self.local_onset)*1000,2)
            self.emit('user_activity_start',local_energy_to_server_ms=delay)
            if len(self.playback) or time.monotonic()-self.last_played<.25:
                self.awaiting_cancel=True;self.flush('activity_start')
        elif activity=='ACTIVITY_END':
            self.user_active=False;self.last_activity_end=time.monotonic();self.awaiting_cancel=False;self.emit('user_activity_end')
            self.response_pending=True
        content=item.get('serverContent',{})
        if content.get('interrupted'):
            self.generating=False
            self.flush('interrupted');self.awaiting_cancel=False
            self.emit('interrupted',remaining_pcm_bytes=len(self.playback))
            self.first_audio=True;self.first_play=True
            # An interruption message must never requeue its discarded audio.
            return
        for part in ([] if self.awaiting_cancel else content.get('modelTurn',{}).get('parts',[])):
            audio=part.get('inlineData',{})
            if audio.get('data'):
                self.generating=True
                self.response_pending=False
                if not audio.get('mimeType','').startswith('audio/pcm'):raise LiveError('Beklenmeyen ses biçimi.')
                pcm=base64.b64decode(audio['data'],validate=True)
                self.audio_bytes_received+=len(pcm)
                if self.first_audio:
                    self.first_audio=False
                    delay=None if self.last_activity_end is None else round(time.monotonic()-self.last_activity_end,3)
                    self.emit('first_audio_received',after_server_activity_end_seconds=delay)
                self.playback.append(pcm)
        if content.get('turnComplete'):
            self.generating=False;self.emit('turn_complete');self.first_audio=True;self.awaiting_cancel=False;self.local_onset=None
            self.response_pending=content.get('interactionStatus')=='IN_PROGRESS' or self.user_active
            if getattr(self,'skill_feedback_active',False):
                self.skill_feedback_active=False;self.emit('skill_feedback_done')
        if content.get('waitingForInput'):self.response_pending=False
        if item.get('goAway'):
            try:remaining=float(str(item['goAway'].get('timeLeft','10s')).rstrip('s'))
            except (ValueError,TypeError):remaining=10.
            self.goaway_deadline=time.monotonic()+max(1.,min(600.,remaining));self.emit('goaway_notice')
        if item.get('error'):
            from provider_errors import classify,message
            error=item['error'];category=classify(error.get('code'),error.get('message','')) if isinstance(error,dict) else 'provider_closed'
            raise LiveError(message(category),code=category)
    async def receive(self):
        from websockets.exceptions import ConnectionClosed
        while not self.closing:
            if self.reconnect_lock.locked():
                await asyncio.sleep(.02);continue
            if self.tool_failure:raise LiveError('Hava durumu yanıtı ses sağlayıcısına iletilemedi; yeniden bağlanmayı dene.')
            socket=self.ws
            try:
                try:message=await asyncio.wait_for(socket.recv(),.25)
                except asyncio.TimeoutError:
                    await self.maybe_resume(socket);continue
                item=json.loads(message);self.handle(item);self.handle_tools(item,socket)
                await self.maybe_resume(socket)
            except ConnectionClosed as error:
                await self._closed(socket,error,'receive')

    async def _closed(self,socket,error,phase):
        # Sending and receiving may notice the same close; use one rejection policy.
        if self.ws is not socket:return
        code=getattr(getattr(error,'rcvd',None),'code',1006)
        from provider_errors import classify,message as provider_message
        category=classify(code,getattr(getattr(error,'rcvd',None),'reason',''))
        self.emit('transport_failure',phase=phase,close_code=code,error_code=category,
                  connection_seconds=round(time.monotonic()-self.connection_started,3),
                  resume_available=bool(self.resume_handle),resume_count=self.resume_count,
                  user_active=self.user_active,response_pending=self.response_pending,
                  generating=self.generating,tool_count=len(self.tool_tasks),playback_bytes=len(self.playback))
        if code in (1008,1009):
            if category=='session_expired' and self.resume_handle:
                await self.resume(socket,'session_expired');return
            if category=='input_timeout' and self.resume_handle and self.is_quiet():
                await self.resume(socket,'idle_input_timeout');return
            raise LiveError(provider_message(category),code=category) from None
        if code in (1000,1001,1006,1011,1012,1013):
            await self.resume(socket,phase+'_closed');return
        raise LiveError(provider_message(category),code=category) from None

    def is_quiet(self):
        return (not self.user_active and not self.response_pending and not self.generating
                and not len(self.playback) and not self.tool_tasks
                and not getattr(self,'skill_feedback_active',False))

    def handle_tools(self,item,socket):
        for call_id in item.get('toolCallCancellation',{}).get('ids',[]):
            task=self.tool_tasks.pop(call_id,None)
            if task:task.cancel()
        for call in item.get('toolCall',{}).get('functionCalls',[]):
            call_id=call.get('id')
            if not isinstance(call_id,str) or call_id in self.tool_tasks:continue
            if len(self.tool_tasks)>=4:raise LiveError('Çok fazla eşzamanlı hava durumu isteği; oturum durduruldu.')
            self.response_pending=True
            call={**call,'_feedback_only':bool(getattr(self,'skill_feedback_active',False))}
            task=asyncio.create_task(self.answer_tool(call,socket))
            self.tool_tasks[call_id]=task
            def finished(done,key=call_id):
                if self.tool_tasks.get(key) is done:self.tool_tasks.pop(key,None)
                if not done.cancelled():
                    error=done.exception()
                    if error:
                        self.tool_failure=True;self.emit('transport_failure',phase='weather_tool',exception_type=type(error).__name__)
            task.add_done_callback(finished)

    async def answer_tool(self,call,socket):
        from weather_tool import get_weather
        args=call.get('args',{})
        if call.get('_feedback_only'):response={'error':'read_completed_result_only_no_tools'}
        elif call.get('name')!='get_weather':response={'error':'unknown_tool'}
        elif not isinstance(args,dict):response={'error':'invalid_arguments'}
        else:
            response=await asyncio.to_thread(get_weather,args.get('city') or self.city,args.get('when','now'))
        async with self.wire_lock:
            if self.ws is socket:
                await asyncio.wait_for(socket.send(json.dumps({'toolResponse':{'functionResponses':[{'id':call['id'],'name':call.get('name',''),'response':response}]}})),5)

    async def maybe_resume(self,socket):
        if self.goaway_deadline is None or not self.resume_handle:return
        quiet=self.is_quiet()
        if quiet or time.monotonic()>=self.goaway_deadline-1:
            await self.resume(socket,'goaway_quiet' if quiet else 'goaway_deadline')

    async def resume(self,socket,reason):
        async with self.reconnect_lock:
            if self.closing or self.ws is not socket:return
            await self._resume_locked(socket,reason)

    async def _resume_locked(self,socket,reason):
        if getattr(self,'skill_feedback_active',False):
            self.skill_feedback_active=False;self.command_silent=True;self.command_response_started=True;self.command_input_closed=False
            self.flush('skill_feedback_disconnected');self.emit('skill_feedback_failed')
        async with self.wire_lock:
            if self.ws is not socket:return
            if not self.resume_handle or not self._key:raise LiveError('Canlı bağlantı kapandı; devam anahtarı yok. Son konuşma yeniden gönderilmedi.',code='resume_unavailable')
            if time.monotonic()-self.last_resume<5:raise LiveError('Bağlantı yeniden koptu; tekrar döngüsü durduruldu.',code='repeated_disconnect')
            self.last_resume=time.monotonic();self.emit('reconnecting',phase=reason)
            for task in self.tool_tasks.values():task.cancel()
            key=self._key
            await socket.close()
            # A short network outage gets a bounded backoff. Never resend an
            # audio/text/tool payload, or retry quota/access/policy rejection.
            for attempt in range(3):
                if self.closing:return
                try:
                    await self.connect(key);break
                except LiveError as error:
                    if error.code!='connection_failed' or attempt==2:raise
                    self.emit('reconnect_wait',attempt=attempt+1)
                    await asyncio.sleep((1.,2.)[attempt])
            self.resume_count+=1
            self.goaway_deadline=None
            self.emit('resumed')

    def flush(self,reason):
        start=time.monotonic();self.playback.clear();self.last_clear=start;self.silence_reported=False
        callback=getattr(self,'on_audio_flush',None)
        if callback:callback()
        self.emit('audio_flushed',phase=reason,clear_ms=round((time.monotonic()-start)*1000,3))

    def silent_output(self):
        if not self.silence_reported and self.last_clear is not None:
            self.silence_reported=True
            self.emit('silence_to_device',after_clear_ms=round((time.monotonic()-self.last_clear)*1000,3))

    def played(self,device_delay):
        self.last_played=time.monotonic()
        if self.first_play:
            self.first_play=False
            self.emit('first_audio_to_device',estimated_dac_delay_seconds=round(max(0,device_delay),4))
    async def close(self,final=True):
        if final:self.closing=True
        self.playback.clear()
        tasks=list(self.tool_tasks.values());self.tool_tasks.clear()
        for task in tasks:task.cancel()
        if tasks:await asyncio.gather(*tasks,return_exceptions=True)
        if self.ws:
            await self.ws.close();self.ws=None
