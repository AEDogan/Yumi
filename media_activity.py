"""Read local Windows media status/genre only; no content leaves the machine."""
import asyncio,threading,hashlib
from music_analysis import genre_name

class MediaActivity:
    def __init__(self):
        self.state={'playing':False,'kind':'unknown','genre':'unknown'}
        self.stop_event=threading.Event()
        self.thread=threading.Thread(target=lambda:asyncio.run(self._run()),daemon=True,name='YumiMediaStatus')
    def start(self):self.thread.start()
    def stop(self):self.stop_event.set()
    async def _run(self):
        try:
            from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionManager as Manager
            manager=await Manager.request_async()
            while not self.stop_event.is_set():
                session=manager.get_current_session();state={'playing':False,'kind':'unknown','genre':'unknown'}
                if session:
                    info=session.get_playback_info();props=await session.try_get_media_properties_async()
                    # Enum values from the installed Windows.Media API:
                    # playback 4=Playing; media 1=Music, 2=Video.
                    kind=info.playback_type if info.playback_type is not None else props.playback_type
                    state['playing']=int(info.playback_status)==4
                    state['kind']={1:'music',2:'video'}.get(int(kind) if kind is not None else 0,'unknown')
                    genres=[genre_name(g) for g in props.genres]
                    state['genre']=next((g for g in genres if g!='unknown'),'unknown')
                    state['track_id']=hashlib.sha256((str(props.title)+'\0'+str(props.artist)).encode()).hexdigest()
                self.state=state
                await asyncio.sleep(1.5)
        except Exception:
            self.state={'playing':False,'kind':'unknown','genre':'unknown'}

