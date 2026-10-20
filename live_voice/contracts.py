"""Provider/model/voice/avatar choices remain separate. Only Gemini is implemented."""
from dataclasses import dataclass
from typing import Protocol,AsyncIterator,Callable
@dataclass(frozen=True)
class SessionOptions:
    provider:str='gemini-live'
    language_model:str='gemini-3.8-live'
    voice_provider:str='native'
    voice:str='Kore'
    avatar_id:str|None=None
    character_name:str='Yumi'
    city:str=''
@dataclass(frozen=True)
class Capabilities:
    native_audio:bool
    interruptions:bool
    external_voice_implemented:bool=False
class LiveTransport(Protocol):
    async def connect(self,key:str)->None:...
    async def send_audio(self,pcm:bytes,rate:int=16000)->None:...
    async def send_text(self,text:str)->None:...
    async def receive(self)->None:...
    async def close(self)->None:...
class TextModelAdapter(Protocol):
    def stream_text(self,history:list,question:str)->AsyncIterator[str]:...
    async def cancel(self)->None:...
class VoiceOutputAdapter(Protocol):
    def synthesize(self,text:str)->AsyncIterator[bytes]:...
    async def cancel(self)->None:...
def create_session(options:SessionOptions,on_event:Callable|None=None):
    if options.provider!='gemini-live':raise ValueError('Bu sağlayıcı adaptörü henüz uygulanmadı.')
    if options.language_model!='gemini-3.8-live':raise ValueError('Bu model canlı prototipte doğrulanmadı.')
    if options.voice_provider!='native':raise ValueError('Harici ses adaptörü planlandı; canlı prototipte henüz uygulanmadı.')
    from live_core import LiveSession
    return LiveSession(options.voice,options.character_name,on_event,city=options.city)
