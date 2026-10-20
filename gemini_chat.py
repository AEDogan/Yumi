"""Direct Gemini SSE chat: one request, bounded waiting and explicit failures."""
import json
import threading
import time
import requests

DEFAULT_MODEL='gemini-3.5-flash-lite'
CHAT_MODELS=(('Flash-Lite · hızlı sohbet','gemini-3.5-flash-lite'),('Flash · daha güçlü yanıt','gemini-3.8-flash'))
_connections=threading.local()
_skill_engine=None

def set_skill_engine(engine):
    global _skill_engine
    _skill_engine=engine

def _get_skill_engine():
    global _skill_engine
    if _skill_engine is None:
        try:
            import sys
            from pathlib import Path
            root_parent=str(Path(__file__).resolve().parent.parent)
            if root_parent not in sys.path:sys.path.insert(0,root_parent)
            from yumi_skills import YumiSkillEngine
            _skill_engine=YumiSkillEngine()
        except Exception:
            _skill_engine=None
    return _skill_engine

class ChatCancelled(RuntimeError):pass

def _session():
    if not hasattr(_connections,'http'):_connections.http=requests.Session()
    return _connections.http

def _check_cancel(cancel):
    if cancel is not None and cancel.is_set():raise ChatCancelled('Yanıt durduruldu; gelen metin korunuyor.')

def _build_payload(text,history,model=DEFAULT_MODEL,name='Yumi'):
    contents=[]
    for m in history[-24:]:
        if m.get('complete',True) is False or m.get('role') not in ('user','assistant'):continue
        value=str(m.get('text','')).strip()
        if not value or value in ('Yanıt alınamadı.','Mesaj tamamlanamadı.'):continue
        role='model' if m['role']=='assistant' else 'user'
        if contents and contents[-1]['role']==role:contents[-1]['parts'].append({'text':value})
        else:contents.append({'role':role,'parts':[{'text':value}]})
    while len(contents)>1 and sum(len(p['text']) for c in contents for p in c['parts'])>16000:contents.pop(0)
    if contents and contents[0]['role']=='model':contents.pop(0)
    contents.append({'role':'user','parts':[{'text':text[:8000]}]})
    config={'maxOutputTokens':2048,'thinkingConfig':{'thinkingLevel':'MINIMAL' if model==DEFAULT_MODEL else 'LOW'}}
    engine=_get_skill_engine()
    tools=engine.get_gemini_tools() if engine else None
    prompt=(
        f'Sen {name} adlı Türkçe konuşan masaüstü asistanısın. Ahmet ile doğal, sıcak ve doğrudan konuş. '
        'Konuşma geçmişini kullan; takip sorularında kişileri ve önceki konuyu hatırla. '
        'Gündelik sohbette genellikle 1–3 cümle yeterlidir. Kullanıcı açıklama veya ayrıntı isterse gerektiği kadar açıkla; '
        'cümle sayısına göre yanıtı yarıda kesme. Gereksiz selam, kalıp giriş ve sürekli soru kullanma. '
        'Bilmediğin bilgiyi uydurma ve yapmadığın bilgisayar işlemlerini yapmış gibi anlatma. '
        'Yanıt sesli okunabilir; sade metin kullan. Akıllı ev cihazları (ışıklar, televizyon, termostat, robot süpürge), '
        'takvim randevuları, sayaç/alarm, alışveriş ve yapılacaklar listesi, sesli notlar, yol tarifi ve müzik gibi işlemlerde '
        'ilgili aracı (function call) çağır.'
    )
    import datetime
    prompt+=' Şu anki yerel tarih ve saat: '+datetime.datetime.now().astimezone().isoformat()+'.'
    payload={'contents':contents,'generationConfig':config,'systemInstruction':{'parts':[{'text':prompt}]}}
    if tools:payload['tools']=tools
    return payload

def _raise_api_error(response,key):
    code=response.status_code
    if code==429:raise RuntimeError('Gemini ücretsiz kullanım sınırı doldu. AI Studio’daki kotayı kontrol et; ücretli modele geçilmedi.')
    if code in (401,403):raise RuntimeError('Gemini anahtarı bu modele erişemiyor. AI Studio’da anahtarın ve ücretsiz projenin durumunu kontrol et.')
    if code==404:raise RuntimeError('Seçilen Gemini modeli bu projede bulunamadı. Ayarlardan diğer sohbet modelini seç; model otomatik değiştirilmedi.')
    if code in (500,502,503,504):raise RuntimeError('Gemini şu an yanıt veremiyor. Biraz sonra yeniden deneyebilirsin.')
    raise RuntimeError(f'Gemini bağlantısı isteği tamamlayamadı ({code}).')

def _events(response):
    data=[]
    for line in response.iter_lines(chunk_size=64,decode_unicode=True):
        if isinstance(line,bytes):line=line.decode('utf-8')
        if not line:
            if data:yield '\n'.join(data);data=[]
        elif line.startswith('data:'):data.append(line[5:].lstrip())
    if data:yield '\n'.join(data)

def stream_answer(key,text,history,model=DEFAULT_MODEL,on_chunk=None,cancel=None,on_status=None,name='Yumi'):
    if not key:raise ValueError('Ayarlar → Asistan → Gemini API bölümüne ücretsiz projenin anahtarını ekle.')
    model=model or DEFAULT_MODEL
    if model not in {v for _,v in CHAT_MODELS}:raise ValueError('Ayarlardan desteklenen ücretsiz sohbet modelini seç.')
    _check_cancel(cancel)
    endpoint=f'https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent?alt=sse'
    if on_status:on_status('Gemini’ye bağlanıyor…')
    response=None;parts=[];finish=None;started=time.monotonic();calls={}
    try:
        response=_session().post(endpoint,headers={'x-goog-api-key':key},json=_build_payload(text,history,model,name),stream=True,timeout=(5,12))
        response.encoding='utf-8'
        _check_cancel(cancel)
        if not response.ok:_raise_api_error(response,key)
        if on_status:on_status('Yanıt bekleniyor…')
        for event in _events(response):
            _check_cancel(cancel)
            if time.monotonic()-started>45:raise RuntimeError('Yanıt akışı zaman sınırını aştı; gelen metin korunuyor.')
            if event=='[DONE]':continue
            try:data=json.loads(event)
            except (ValueError,TypeError):raise RuntimeError('Gemini yanıt akışı okunamadı; aynı mesaj yeniden gönderilmedi.') from None
            if 'error' in data:raise RuntimeError('Gemini yanıt akışını bir hatayla sonlandırdı; gelen metin korunuyor.')
            if data.get('promptFeedback',{}).get('blockReason'):raise RuntimeError('Gemini bu isteğe yanıt üretemedi; mesaj yeniden gönderilmedi.')
            candidates=data.get('candidates',[])
            if not candidates:continue
            candidate=candidates[0]
            for part in candidate.get('content',{}).get('parts',[]):
                chunk=part.get('text','')
                if chunk and not part.get('thought'):
                    if not parts and on_status:on_status('Yanıt geliyor…')
                    parts.append(chunk)
                    if on_chunk:on_chunk(chunk)
                if 'functionCall' in part:
                    fc=part['functionCall']
                    if not isinstance(fc,dict) or not fc.get('name') or not isinstance(fc.get('args',{}),dict):
                        raise RuntimeError('Beceri çağrısı eksik; işlem uygulanmadı.')
                    identity=fc.get('id') or json.dumps(fc,sort_keys=True,ensure_ascii=False)
                    calls[identity]=fc
            finish=candidate.get('finishReason',finish)
        _check_cancel(cancel)
        if finish not in ('STOP','FUNCTION_CALL'):
            if finish=='MAX_TOKENS':raise RuntimeError('Yanıt uzunluk sınırında kesildi; gelen metin korunuyor.')
            raise RuntimeError('Gemini yanıtı tamamlamadı; gelen metin korunuyor ve soru tekrar gönderilmedi.')
        for fc in calls.values():
            _check_cancel(cancel)
            engine=_get_skill_engine()
            if not engine:raise RuntimeError('Yerel beceri motoru kullanılamıyor; işlem uygulanmadı.')
            if on_status:on_status('İşlem yürütülüyor…')
            response_data=engine.execute_skill(fc['name'],fc.get('args',{}))
            speech=response_data.get('speech','')
            if speech:
                if parts:speech='\n'+speech
                parts.append(speech)
                if on_chunk:on_chunk(speech)
        result=''.join(parts).strip()
        if not result:raise RuntimeError('Gemini boş yanıt döndürdü; soru tekrar gönderilmedi.')
        return result,None
    except requests.RequestException:
        _check_cancel(cancel)
        raise RuntimeError('Gemini bağlantısı kesildi veya zamanında yanıt vermedi; gelen metin korunuyor. Yeniden deneyebilirsin.') from None
    finally:
        if response is not None:response.close()

def answer(key,text,history,model=DEFAULT_MODEL):
    return stream_answer(key,text,history,model)
