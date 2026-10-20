"""Close only after four seconds without input, generation or audible playback."""
import time
class IdleTimeout:
    def __init__(self,seconds=4):self.seconds=seconds;self.since=None
    def expired(self,session,now=None):
        now=time.monotonic() if now is None else now
        active=session.user_active or session.generating or session.response_pending or getattr(session,'tool_tasks',{}) or len(session.playback) or now-session.last_played<.15
        if active:self.since=None;return False
        if self.since is None:self.since=now
        return now-self.since>=self.seconds
