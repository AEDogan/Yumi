"""Read Windows output peak; no audio recording or transmission."""
import time
from ctypes import cast,POINTER

class SystemAudio:
    def __init__(self):
        self.meter=None; self.retry=0; self.peak=0; self.active_since=None
    def sample(self):
        now=time.monotonic()
        try:
            if self.meter is None:
                if now<self.retry:return 0
                from comtypes import CLSCTX_ALL
                from pycaw.pycaw import AudioUtilities,IAudioMeterInformation
                device=AudioUtilities.GetSpeakers()
                interface=device._dev.Activate(IAudioMeterInformation._iid_,CLSCTX_ALL,None)
                self.meter=cast(interface,POINTER(IAudioMeterInformation))
            self.peak=float(self.meter.GetPeakValue())
        except Exception:
            self.meter=None; self.retry=now+15; self.peak=0
        if self.peak>.025:
            if self.active_since is None:self.active_since=now
        elif self.peak<.002:self.active_since=None
        return self.peak
