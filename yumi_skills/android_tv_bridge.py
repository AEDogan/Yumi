"""Android/Google TV remote pairing; one owned loop and no ADB/root access."""
import asyncio,threading,hashlib,re

class AndroidTVBridge:
    def __init__(self,storage):
        self.storage=storage;self.loop=asyncio.new_event_loop();self.clients={}
        self.thread=threading.Thread(target=self.loop.run_forever,daemon=True,name='YumiTVBridge');self.thread.start()
    def call(self,coro,timeout=15):
        future=asyncio.run_coroutine_threadsafe(coro,self.loop)
        try:return future.result(timeout)
        except Exception:
            future.cancel();raise
    def client(self,host):
        from androidtvremote2 import AndroidTVRemote
        if host not in self.clients:
            key=hashlib.sha256(host.encode()).hexdigest()[:20];directory=self.storage.tokens_dir/'android-tv';directory.mkdir(exist_ok=True)
            self.clients[host]=AndroidTVRemote('Yumi',str(directory/(key+'.crt')),str(directory/(key+'.key')),host,loop=self.loop,enable_ime=False)
        return self.clients[host]
    async def _begin(self,host):
        remote=self.client(host);await remote.async_generate_cert_if_missing();await asyncio.wait_for(remote.async_start_pairing(),10)
        return {'ok':True,'speech':"TV ekranındaki eşleştirme kodunu aşağıdaki alana gir."}
    def begin(self,host):return self.call(self._begin(host))
    async def _finish(self,host,code):
        if not re.fullmatch('[A-Fa-f0-9]{6}',code.strip()):return {'ok':False,'speech':'TV ekranındaki altı haneli kodu gir.'}
        remote=self.client(host);await asyncio.wait_for(remote.async_finish_pairing(code.strip()),10)
        return {'ok':True,'speech':'TV eşleştirmesi tamamlandı.'}
    def finish(self,host,code):return self.call(self._finish(host,code))
    async def _control(self,host,action):
        keys={'power_on':'WAKEUP','power_off':'SLEEP','volume_up':'VOLUME_UP','volume_down':'VOLUME_DOWN','mute':'VOLUME_MUTE','home':'HOME','back':'BACK'}
        remote=self.client(host)
        try:
            await asyncio.wait_for(remote.async_connect(),8)
            if action=='status':
                if remote.is_on is None:return {'ok':False,'speech':'TV bağlı, ancak güç durumu henüz bildirilmedi.'}
                return {'ok':True,'speech':'TV açık.' if remote.is_on else 'TV bekleme durumunda.','is_on':remote.is_on}
            if action not in keys:return {'ok':False,'speech':'Bu TV komutu desteklenmiyor.'}
            remote.send_key_command(keys[action]);await asyncio.sleep(.15)
            return {'ok':True,'speech':'TV komutu gönderildi.'}
        finally:remote.disconnect()
    def control(self,host,action):return self.call(self._control(host,action))
    def close(self):
        def stop():
            for remote in self.clients.values():remote.disconnect()
            self.loop.stop()
        self.loop.call_soon_threadsafe(stop);self.thread.join(1)
