"""Use the user's default Chromium browser and real chat website, without API keys.

Only a dedicated Yumi profile is controlled; personal tabs and cookies are untouched.
The debugging endpoint is local and disappears when the owned process exits.
"""
import json
import os
from pathlib import Path
import re
import subprocess
import threading
import time
import winreg
from urllib.parse import urlparse

import requests
from websockets.sync.client import connect

SITES={'chatgpt-web':'https://chatgpt.com/','gemini-web':'https://gemini.google.com/?hl=tr'}
SESSION_PROMPT=('Bu sohbet boyunca yanıtlarını Türkçe, doğal ve doğrudan ver. Genel yaklaşımın birkaç kısa cümle olsun; hiçbir yanıtın beş cümleyi geçmesin. '
                'Konu daha uzun bir açıklama gerektiriyorsa önce kısa bir cevap ver ve «Bu konunun cevabı biraz uzun, istersen detaylı anlatayım» gibi doğal bir cümleyle bunu belirt; ayrıntı için kullanıcının onayını bekle. '
                'Yanıtlar sesli okunacak; uzun liste, tablo, Markdown ve gereksiz giriş kullanma. Bu mesaj bir sohbet tercihidir, kullanıcının sorusu değildir. Yalnızca «Tamam.» diyerek onayla.')
HIDDEN={'creationflags':subprocess.CREATE_NO_WINDOW} if os.name=='nt' else {}

class MessageNotSubmitted(RuntimeError):
    def __init__(self,message,text):
        super().__init__(message)
        self.retry_text=text

class ConversationCancelled(RuntimeError):
    pass

def normal_browser_pids(directory):
    """Find only ordinary browser roots using Yumi's exact dedicated profile."""
    if os.name!='nt':return []
    import base64
    argument=subprocess.list2cmdline(['--user-data-dir='+str(directory)]).replace("'","''")
    script=("$yumiArgument='"+argument+"'; Get-CimInstance Win32_Process | Where-Object { "
            "$_.Name -in @('chrome.exe','msedge.exe','brave.exe','opera.exe','vivaldi.exe','chromium.exe') "
            "-and $_.CommandLine -notmatch '--type=|--headless' "
            "-and ($_.CommandLine.Contains($yumiArgument+' ') -or $_.CommandLine.EndsWith($yumiArgument)) "
            "} | Select-Object -ExpandProperty ProcessId | ConvertTo-Json -Compress")
    result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-EncodedCommand',base64.b64encode(script.encode('utf-16-le')).decode('ascii')],capture_output=True,text=True,timeout=8,**HIDDEN)
    if result.returncode:raise RuntimeError('Yumi giriş penceresinin durumu kontrol edilemedi.')
    values=json.loads(result.stdout) if result.stdout.strip() else []
    return [int(value) for value in (values if isinstance(values,list) else [values])]

def close_browser_windows(pid):
    """Request normal window closure; never terminate a login process."""
    import ctypes
    from ctypes import wintypes
    user32=ctypes.windll.user32
    callback_type=ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)
    user32.GetWindowThreadProcessId.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.DWORD)]
    user32.IsWindowVisible.argtypes=[wintypes.HWND]
    user32.PostMessageW.argtypes=[wintypes.HWND,wintypes.UINT,wintypes.WPARAM,wintypes.LPARAM]
    user32.EnumWindows.argtypes=[callback_type,wintypes.LPARAM]
    def close(hwnd,_):
        owner=wintypes.DWORD();user32.GetWindowThreadProcessId(hwnd,ctypes.byref(owner))
        if owner.value==pid and user32.IsWindowVisible(hwnd):user32.PostMessageW(hwnd,0x0010,0,0)
        return True
    user32.EnumWindows(callback_type(close),0)

def browser_running(pid):
    import ctypes
    from ctypes import wintypes
    kernel=ctypes.windll.kernel32;kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];kernel.OpenProcess.restype=wintypes.HANDLE
    kernel.GetExitCodeProcess.argtypes=[wintypes.HANDLE,ctypes.POINTER(wintypes.DWORD)];kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    handle=kernel.OpenProcess(0x1000,False,pid)
    if not handle:return False
    try:
        code=wintypes.DWORD();return bool(kernel.GetExitCodeProcess(handle,ctypes.byref(code))) and code.value==259
    finally:kernel.CloseHandle(handle)

def short_reply(text):
    ends=list(re.finditer(r'(?<!\d)[.!?]+["”’\']*(?=\s|$)',text))
    return (text[:ends[4].end()],True) if len(ends)>=5 else (text,False)

def default_browser():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,r'Software\Microsoft\Windows\Shell\Associations\UrlAssociations\https\UserChoice') as key:
            prog_id=winreg.QueryValueEx(key,'ProgId')[0]
    except OSError:
        raise RuntimeError('Windows varsayılan tarayıcısı belirlenemedi.') from None
    command=''
    for hive,prefix in ((winreg.HKEY_CURRENT_USER,'Software\\Classes\\'),(winreg.HKEY_LOCAL_MACHINE,'Software\\Classes\\')):
        try:
            with winreg.OpenKey(hive,prefix+prog_id+r'\shell\open\command') as key:
                command=winreg.QueryValueEx(key,'')[0];break
        except OSError:pass
    match=re.match(r'^\s*"([^"]+\.exe)"',command,re.I)
    executable=Path(os.path.expandvars(match.group(1))) if match else None
    if executable is None or not executable.exists():
        known={'chromehtml':Path(os.environ.get('PROGRAMFILES',''))/'Google/Chrome/Application/chrome.exe',
               'msedgehtm':Path(os.environ.get('PROGRAMFILES(X86)',''))/'Microsoft/Edge/Application/msedge.exe'}
        executable=next((path for name,path in known.items() if prog_id.lower().startswith(name) and path.exists()),None)
    if executable is None:raise RuntimeError('Varsayılan tarayıcının çalıştırılabilir dosyası bulunamadı.')
    if executable.name.lower() not in ('chrome.exe','msedge.exe','brave.exe','opera.exe','vivaldi.exe','chromium.exe'):
        raise RuntimeError('Varsayılan tarayıcı '+executable.name+'. Görünmez bağlantı şu anda Chromium tabanlı tarayıcıları destekliyor.')
    return executable

# DOM state is read from the visible site's own composer and assistant responses.
# There is no private service endpoint, cookie export or authentication bypass.
DOM = r"""(() => {
 const visible = e => !!e && !!(e.offsetWidth || e.offsetHeight || e.getClientRects().length);
 const text = e => String(e?.innerText ?? e?.textContent ?? '').trim();
 const first = selectors => selectors.flatMap(s=>[...document.querySelectorAll(s)]).find(visible);
 const gemini = location.hostname.endsWith('gemini.google.com');
 const editor = first(gemini ? ['rich-textarea [contenteditable="true"]','[contenteditable="true"][role="textbox"]','textarea'] : ['#prompt-textarea','[contenteditable="true"][data-lexical-editor="true"]','textarea[data-id="root"]','textarea']);
 const replies = [...document.querySelectorAll(gemini ? 'model-response' : '[data-message-author-role="assistant"]')].filter(visible);
 window.__yumiReplyIds ||= new WeakMap();window.__yumiReplySerial ||= 0;
 const replyId=e=>{if(!e)return null;if(!window.__yumiReplyIds.has(e))window.__yumiReplyIds.set(e,++window.__yumiReplySerial);return window.__yumiReplyIds.get(e);};
 const texts = replies.map(e => text(e.querySelector('.markdown, message-content, .model-response-text') || e));
 const buttons = [...document.querySelectorAll('button')].filter(visible);
 const stop = buttons.find(b=>/^(stop|stop generating|stop response|yanıtı durdur|durdur|üretimi durdur)$/i.test((b.getAttribute('aria-label')||b.getAttribute('title')||b.innerText).trim()) || b.matches('[data-testid="stop-button"],.stop-button'));
 const send = first(['button[data-testid="send-button"]','button[aria-label="Send prompt"]','button[aria-label="Send message"]','button[aria-label="Mesaj gönder"]','button[aria-label="Gönder"]','button.send-button']);
 const login=[...buttons,...document.querySelectorAll('a')].some(e=>visible(e) && /^(sign in|log in|login|oturum aç|oturum açın|giriş yap)$/i.test(text(e)));
 const verification=/just a moment|bir dakika lütfen|verify you are human|insan olduğunuzu/i.test((document.title||'')+' '+text(document.body));
 return {editor:!!editor, login, verification, reply_id:replyId(replies.at(-1)),count:texts.length, text:texts.at(-1)||'', busy:!!stop, draft:editor ? String(editor.value ?? editor.innerText ?? editor.textContent ?? '').trim() : '', users:document.querySelectorAll(gemini ? 'user-query' : '[data-message-author-role="user"]').length, send:!!send && !send.disabled, url:location.href};
})()"""

SEND = r"""((text) => {
 const visible = e=>!!e && !!(e.offsetWidth || e.offsetHeight || e.getClientRects().length);
 const gemini=location.hostname.endsWith('gemini.google.com');
 const selectors=gemini?['rich-textarea [contenteditable="true"]','[contenteditable="true"][role="textbox"]','textarea']:['#prompt-textarea','[contenteditable="true"][data-lexical-editor="true"]','textarea[data-id="root"]','textarea'];
 const editor=selectors.flatMap(s=>[...document.querySelectorAll(s)]).find(visible);
 if(!editor) return false;
 editor.focus();
 if(editor.tagName==='TEXTAREA') {
   Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value').set.call(editor,text);
   editor.dispatchEvent(new Event('input',{bubbles:true}));
 } else {
   const range=document.createRange();range.selectNodeContents(editor);
   const selection=getSelection();selection.removeAllRanges();selection.addRange(range);
   document.execCommand('insertText',false,text);
   editor.dispatchEvent(new InputEvent('input',{bubbles:true,inputType:'insertText',data:text}));
 }
 return true;
})"""

CLICK_SEND = r"""(() => {
 const b=[...document.querySelectorAll('button[data-testid="send-button"],button[aria-label="Send prompt"],button[aria-label="Send message"],button[aria-label="Mesaj gönder"],button[aria-label="Gönder"],button.send-button')].find(b=>b.offsetWidth && !b.disabled);
 if(b){const r=b.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2};} return null;
})()"""

STOP = r"""(() => {
 const b=[...document.querySelectorAll('button')].find(b=>b.offsetWidth && (b.matches('[data-testid="stop-button"],.stop-button') || /^(stop|stop generating|stop response|yanıtı durdur|durdur|üretimi durdur)$/i.test((b.getAttribute('aria-label')||b.getAttribute('title')||b.innerText).trim())));
 if(b)b.click();return !!b;
})()"""

class BrowserChat:
    def __init__(self,data_dir,isolated=False):
        self.directory=Path(data_dir)/'browser-profile';self.process=None;self.socket=None
        self.owns_browser=False;self.isolated=isolated
        self.lock=threading.RLock();self.sequence=0;self.provider=None;self.headed=False;self.url=None;self.urls={}
        self.cancel_event=threading.Event()
        self.conversation_scope=None
        self.http=requests.Session();self.http.trust_env=False
        self.urls_file=Path(data_dir)/'browser-conversations.json'
        self.preferences_file=Path(data_dir)/'browser-preferences.json';self.prepared={}
        try:
            saved=json.loads(self.urls_file.read_text(encoding='utf-8'))
            self.urls={key:url for key,url in saved.items() if key in SITES and isinstance(url,str) and urlparse(url).hostname==urlparse(SITES[key]).hostname and urlparse(url).scheme=='https'}
        except (OSError,ValueError,AttributeError):pass
        try:
            saved=json.loads(self.preferences_file.read_text(encoding='utf-8'))
            if saved.get('version')==1 and isinstance(saved.get('conversations'),dict):self.prepared=saved['conversations']
        except (OSError,ValueError,AttributeError):pass

    def use_conversation(self,scope,urls):
        if scope is None or scope==self.conversation_scope:return
        self.conversation_scope=scope;self.urls=urls;self.url=None;self.provider=None
        # The local chat archive owns these URLs and expires them with the chat.
        self.urls_file=None

    def remember_url(self,url):
        if url and urlparse(url).scheme=='https' and urlparse(url).hostname==urlparse(SITES[self.provider]).hostname:
            self.url=url;self.urls[self.provider]=url
            if self.urls_file is None:return
            temporary=self.urls_file.with_suffix('.tmp');temporary.parent.mkdir(parents=True,exist_ok=True)
            temporary.write_text(json.dumps(self.urls),encoding='utf-8');temporary.replace(self.urls_file)

    def rpc(self,method,params=None):
        self.sequence+=1;request_id=self.sequence
        self.socket.send(json.dumps({'id':request_id,'method':method,'params':params or {}}))
        deadline=time.monotonic()+8
        while time.monotonic()<deadline:
            event=json.loads(self.socket.recv(timeout=max(.01,deadline-time.monotonic())))
            if event.get('id')!=request_id:continue
            if 'error' in event:raise RuntimeError('Tarayıcı bağlantısı: '+event['error'].get('message','hata'))
            return event.get('result',{})
        raise RuntimeError('Tarayıcı bağlantısı zaman aşımına uğradı.')

    def evaluate(self,source):
        # A navigation can briefly remove the page's default JS context.
        # Retry only this explicit pre-execution error, never a timeout or a
        # partially completed submission that could duplicate a user message.
        for attempt in range(3):
            try:
                result=self.rpc('Runtime.evaluate',{'expression':source,'returnByValue':True,'awaitPromise':True});break
            except RuntimeError as error:
                transient=any(s in str(error) for s in ('Cannot find default execution context','Execution context was destroyed','Cannot find context with specified id'))
                if source not in (DOM,CLICK_SEND) or not transient or attempt==2:raise
                time.sleep(.2*(attempt+1))
        if 'exceptionDetails' in result:
            # A read-only page probe can run before its document exists during
            # navigation. Never retry SEND/CLICK or arbitrary JS exceptions.
            detail=result['exceptionDetails'];description=detail.get('exception',{}).get('description','')
            if source==DOM and 'TypeError' in description and any(s in description for s in ('null','undefined')):
                return {}
            raise RuntimeError('Sohbet sayfası okunamadı.')
        return result.get('result',{}).get('value')

    def attach(self,port,provider):
        base=f'http://127.0.0.1:{int(port)}'
        pages=self.http.get(base+'/json/list',timeout=3).json()
        page=None if self.isolated else next((p for p in pages if p.get('type')=='page' and p.get('url','').startswith(SITES[provider].split('?')[0])),None)
        if page is None:page=self.http.put(base+'/json/new?'+SITES[provider],timeout=3).json()
        endpoint=page['webSocketDebuggerUrl']
        if urlparse(endpoint).hostname not in ('127.0.0.1','localhost'):
            raise RuntimeError('Yumi tarayıcı bağlantısı yerel değil.')
        self.socket=connect(endpoint,proxy=None,open_timeout=3,max_size=8*1024*1024,ping_interval=None)
        self.provider=provider;self.headed=False
        self.rpc('Page.enable');self.rpc('Runtime.enable')
        self.rpc('Emulation.setFocusEmulationEnabled',{'enabled':True})
        if self.conversation_scope is not None:
            self.url=self.urls.get(provider,SITES[provider]);self.rpc('Page.navigate',{'url':self.url})

    def ensure(self,provider,headed=False):
        if provider not in SITES:raise ValueError('Bilinmeyen web asistanı.')
        if self.socket and self.socket.close_code is None and (self.process is None or self.process.poll() is None) and self.headed==headed:
            if self.provider!=provider:
                if self.url:self.urls[self.provider]=self.url
                self.provider=provider;self.url=self.urls.get(provider,SITES[provider]);self.rpc('Page.navigate',{'url':self.url})
            return
        if self.headed and self.process and self.process.poll() is None:
            raise RuntimeError('Giriş penceresini kapat, ardından Giriş tamamlandı düğmesine bas. Oturumun saklanır.')
        self.close();executable=default_browser();self.directory.mkdir(parents=True,exist_ok=True)
        portfile=self.directory/'DevToolsActivePort'
        if not headed and portfile.exists():
            try:
                self.attach(int(portfile.read_text().splitlines()[0]),provider)
                return
            except Exception:
                if self.socket:
                    try:self.socket.close()
                    except Exception:pass
                self.socket=None
        if not headed and normal_browser_pids(self.directory):
            raise RuntimeError('Yumi giriş penceresi açık. Oturumunu tamamladıktan sonra Giriş tamamlandı düğmesine bas.')
        portfile.unlink(missing_ok=True)
        command=[str(executable),'--user-data-dir='+str(self.directory),'--remote-debugging-port=0',
                 '--remote-debugging-address=127.0.0.1','--no-first-run','--no-default-browser-check',
                 '--disable-background-timer-throttling','--disable-renderer-backgrounding']
        if not headed:command+=['--headless=new','--window-size=1200,900']
        target=self.url if self.provider==provider and self.url else self.urls.get(provider,SITES[provider])
        command.append(target)
        self.process=subprocess.Popen(command,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,**HIDDEN)
        self.owns_browser=True
        self.provider=provider;self.headed=headed
        deadline=time.monotonic()+12
        try:
            while time.monotonic()<deadline:
                if self.process.poll() is not None:raise RuntimeError('Varsayılan tarayıcı arka planda başlatılamadı.')
                if portfile.exists():
                    lines=portfile.read_text().splitlines()
                    if lines:break
                time.sleep(.1)
            else:raise RuntimeError('Tarayıcı başlaması zaman aşımına uğradı.')
            self.attach(int(lines[0]),provider)
        except Exception:
            self.close();raise

    def show_login(self,provider):
        with self.lock:
            if provider not in SITES:raise ValueError('Bilinmeyen web asistanı.')
            if self.headed and self.process and self.process.poll() is None:
                raise RuntimeError('Açık giriş penceresini önce kapat; ardından diğer siteyi açabilirsin.')
            self.close();self.directory.mkdir(parents=True,exist_ok=True)
            # Authentication happens in a normal browser, without a debugging
            # endpoint or headless/automation flags. Never inspect credentials.
            self.process=subprocess.Popen([str(default_browser()),
                '--user-data-dir='+str(self.directory),'--disable-background-mode','--new-window',SITES[provider]],
                stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,**HIDDEN)
            self.provider=provider;self.headed=True;self.url=None
            return 'Normal tarayıcıda giriş yap; ardından Giriş tamamlandı düğmesine bas. Yumi giriş penceresini kapatıp arka plan bağlantısını hazırlayacak.'

    def finish_login(self,provider):
        with self.lock:
            # The button closes Yumi's own login window. Requiring the user to
            # close it first made "take browser to background" appear broken.
            pids=normal_browser_pids(self.directory)
            for pid in pids:close_browser_windows(pid)
            deadline=time.monotonic()+8
            while any(browser_running(pid) for pid in pids):
                if time.monotonic()>=deadline:
                    raise RuntimeError('Yumi giriş penceresi kapanmayı bekliyor. Açık bir tarayıcı onayını tamamlayıp tekrar dene.')
                time.sleep(.1)
            if pids or self.headed:self.process=None;self.headed=False
            self.ensure(provider,headed=False)
            deadline=time.monotonic()+15
            while time.monotonic()<deadline:
                state=self.evaluate(DOM) or {}
                if state.get('editor') and not state.get('login'):
                    self.remember_url(state.get('url'))
                    return 'Web sohbeti arka planda hazır.'
                if state.get('login'):
                    raise RuntimeError('Site hâlâ giriş istiyor. Seçilen siteye giriş yap bölümünden oturumu tamamla.')
                time.sleep(.15)
            raise RuntimeError('Site bağlantısı doğrulanamadı. Giriş penceresinde site uyarısını kontrol et.')

    def warm(self,provider):
        with self.lock:
            self.ensure(provider)
            deadline=time.monotonic()+15
            while time.monotonic()<deadline:
                state=self.evaluate(DOM) or {}
                if state.get('login'):return False
                if state.get('editor') and not state.get('busy'):
                    self.remember_url(state.get('url'));return True
                time.sleep(.15)
            return False

    def prepare_session(self,state):
        if self.prepared.get(self.provider)==state.get('url'):return
        self.ask(SESSION_PROMPT,_setup=True)
        state=self.evaluate(DOM) or {}
        self.remember_url(state.get('url'))
        self.prepared[self.provider]=state.get('url')
        temporary=self.preferences_file.with_suffix('.tmp')
        temporary.write_text(json.dumps({'version':1,'conversations':self.prepared}),encoding='utf-8')
        temporary.replace(self.preferences_file)

    def read_aloud(self,on_start=None):
        with self.lock:
            if not self.socket:raise RuntimeError('Ses için açık web sohbeti bulunamadı.')
            text=(self.evaluate(DOM) or {}).get('text','')
            clipped,limited=short_reply(text)
            if limited and clipped.strip()!=text.strip():
                raise RuntimeError('Site yanıtı beş cümleyi aştığı için uzun metnin sesli okuması durduruldu. Yumi’daki kısa yanıtı bir TTS sesiyle dinleyebilirsin.')
            clicked=self.evaluate(r'''(() => {
                window.__yumiVoice={started:false,done:false};
                if(!window.__yumiVoiceHook){
                    window.__yumiVoiceHook=true;
                    const play=HTMLMediaElement.prototype.play;
                    HTMLMediaElement.prototype.play=function(...args){
                        window.__yumiVoice.started=true;window.__yumiVoice.done=false;
                        this.addEventListener('ended',()=>window.__yumiVoice.done=true,{once:true});
                        this.addEventListener('error',()=>window.__yumiVoice.done=true,{once:true});
                        return play.apply(this,args);
                    };
                }
                const gemini=location.hostname.endsWith('gemini.google.com');
                const replies=[...document.querySelectorAll(gemini?'model-response':'[data-message-author-role="assistant"]')];
                let root=replies.at(-1);
                if(root && !gemini)root=root.closest('article')||root.parentElement;
                const button=[...(root||document).querySelectorAll('button')].find(b=>
                    /read aloud|sesli oku|dinle|listen|listen to response/i.test(b.getAttribute('aria-label')||b.getAttribute('title')||b.innerText));
                if(!button)return false;button.click();return true;
            })()''')
            if not clicked:raise RuntimeError('Bu yanıtta sitenin sesli okuma düğmesi bulunamadı. Yumi için bir TTS sesi seçebilirsin.')
            # Explicitly detect an available site control; never substitute another voice.
            state=self.evaluate('window.__yumiVoice')
            deadline=time.monotonic()+8
            while time.monotonic()<deadline:
                state=self.evaluate('window.__yumiVoice') or {}
                if state.get('started'):break
                time.sleep(.15)
            else:raise RuntimeError('Sitenin sesli okuması başlamadı. Tarayıcıya giriş bölümünde ses düğmesini kontrol et veya Yumi için bir TTS sesi seç.')
            if on_start:on_start()
            deadline=time.monotonic()+90
            while time.monotonic()<deadline:
                state=self.evaluate('window.__yumiVoice') or {}
                if state.get('done'):return
                time.sleep(.15)
            raise RuntimeError('Sitenin sesli okuması tamamlanmadı.')

    def ask(self,text,on_chunk=None,_setup=False,on_status=None):
        with self.lock:
            self.cancel_event.clear()
            original_text=text
            if self.headed:raise RuntimeError('Giriş penceresini kapatıp Giriş tamamlandı düğmesine bas.')
            self.ensure(self.provider or 'chatgpt-web')
            deadline=time.monotonic()+20
            while time.monotonic()<deadline:
                self._check_cancel()
                state=self.evaluate(DOM) or {}
                if state.get('verification'):raise MessageNotSubmitted('Site tarayıcı doğrulaması istiyor. Ayarlar → Seçilen siteye giriş yap bölümünde doğrulamayı tamamla; mesajın gönderilmedi.',text)
                if state.get('editor') and not state.get('busy') and state.get('url','').startswith(SITES[self.provider].split('?')[0]):break
                if state.get('login'):
                    raise RuntimeError('Web hesabına giriş gerekiyor. Ayarlar → Seçilen siteye giriş yap bölümünde oturum aç; ardından tarayıcıyı arka plana al.')
                time.sleep(.15)
            else:raise RuntimeError('Web sohbeti hazır değil. Ayarlar → Tarayıcıya giriş ile siteyi aç; giriş veya site doğrulamasını tamamla.')
            if state.get('busy'):raise RuntimeError('Tarayıcıdaki önceki yanıt hâlâ sürüyor.')
            # Send one request only: a separate preference turn can block the real question.
            if not _setup:
                text='Türkçe ve en fazla beş kısa cümleyle yanıt ver.\n\n'+text
            draft=state.get('draft','').strip()
            if draft and draft not in (original_text.strip(),text.strip()):
                raise MessageNotSubmitted('Web sayfasında başka bir taslak var. Taslağı korumak için yeni mesaj gönderilmedi.',original_text)
            self.remember_url(state.get('url'))
            if on_status:on_status('Mesaj gönderiliyor…')
            baseline=state['count'];old=state['text'];old_reply=state.get('reply_id')
            # Select the composer contents, then use Chromium's real input path.
            # Synthetic input events can leave Angular/React's send state stale.
            focused=self.evaluate(r"""(() => {
                const visible=e=>e && (e.offsetWidth || e.offsetHeight);
                const editor=[...document.querySelectorAll('rich-textarea [contenteditable="true"],#prompt-textarea,[contenteditable="true"][role="textbox"],textarea')].find(visible);
                if(!editor)return false;
                editor.focus();
                if(editor.tagName==='TEXTAREA')editor.select();
                else {const range=document.createRange();range.selectNodeContents(editor);const selection=getSelection();selection.removeAllRanges();selection.addRange(range);}
                return true;
            })()""")
            if not focused:raise RuntimeError('Web sohbetinin mesaj kutusu bulunamadı.')
            self.rpc('Input.insertText',{'text':text[:4000]})
            submitted=False
            send_deadline=time.monotonic()+12
            while time.monotonic()<send_deadline:
                self._check_cancel()
                point=self.evaluate(CLICK_SEND)
                if point:
                    # Send from the focused composer. The native keyboard
                    # path is independent of a responsive button moving
                    # between coordinate sampling and mouse dispatch.
                    self.rpc('Input.dispatchKeyEvent',{'type':'keyDown','key':'Enter','code':'Enter','windowsVirtualKeyCode':13,'nativeVirtualKeyCode':13,'text':'\r','unmodifiedText':'\r'})
                    self.rpc('Input.dispatchKeyEvent',{'type':'keyUp','key':'Enter','code':'Enter','windowsVirtualKeyCode':13,'nativeVirtualKeyCode':13})
                    submitted=True;break
                time.sleep(.15)
            if not submitted:raise MessageNotSubmitted('Site mesajı göndermeye hazır olmadı. Mesaj kutuda korunuyor; yeniden deneyebilirsin.',original_text)
            # Never submit twice: a slow acknowledgement could duplicate a message.
            ack_deadline=time.monotonic()+15
            while time.monotonic()<ack_deadline:
                self._check_cancel()
                accepted=self.evaluate(DOM) or {}
                if accepted.get('users',0)>state.get('users',0) or accepted.get('busy') or accepted.get('count',0)>baseline:
                    self.remember_url(accepted.get('url'));break
                time.sleep(.15)
            else:raise RuntimeError('Site gönderimi doğrulamadı. Tekrar göndermeden önce web sohbetini kontrol et.')
            if on_status:on_status('Mesaj ulaştı · yanıt bekleniyor…')
            full='';stable=0.;last_change=time.monotonic();started=False;deadline=time.monotonic()+120
            while time.monotonic()<deadline:
                self._check_cancel()
                state=self.evaluate(DOM) or {};current=state.get('text','')
                current,limit_reached=short_reply(current)
                # A previous long reply can differ from its clipped text.
                # Only a newly added assistant message belongs to this request.
                is_new=state.get('count',0)>baseline or (state.get('reply_id') is not None and state.get('reply_id')!=old_reply)
                if is_new and current:
                    if not started and on_status:on_status('Yanıt geliyor…')
                    started=True
                    if current!=full:
                        if current.startswith(full):
                            delta=current[len(full):]
                            if delta and on_chunk:on_chunk(delta)
                        else:raise RuntimeError('Site yanıt metnini değiştirdi; görünen kısmi yanıt korunuyor.')
                        full=current;last_change=time.monotonic();stable=0.
                    else:stable=time.monotonic()-last_change
                    if limit_reached:
                        self.evaluate(STOP);self.remember_url(state.get('url'));return full
                    if not state.get('busy') and stable>.8:
                        self.remember_url(state.get('url'));return full
                if not started and time.monotonic()>deadline-30:
                    self.evaluate(STOP)
                    raise RuntimeError('Mesaj siteye ulaştı fakat yanıt başlamadı. Aynı mesajı tekrar göndermeden önce Ayarlar’dan sohbet sayfasını kontrol et.')
                time.sleep(.08)
            self.evaluate(STOP)
            raise RuntimeError('Web sohbeti zamanında tamamlanmadı; varsa görünen kısmi yanıt korunuyor.')

    def cancel_request(self):
        # UI thread sets a flag only. CDP commands remain on the request worker.
        self.cancel_event.set()

    def _check_cancel(self):
        if self.cancel_event.is_set():
            self.evaluate(STOP)
            raise ConversationCancelled('Yanıt durduruldu; gelen metin korunuyor.')

    def close(self):
        if self.socket:
            try:
                if self.owns_browser:self.rpc('Browser.close')
                elif self.isolated:self.rpc('Page.close')
            except Exception:pass
            try:self.socket.close()
            except Exception:pass
        self.socket=None
        if self.process and self.owns_browser and not self.headed:
            try:self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:self.process.terminate()
        self.process=None;self.owns_browser=False
