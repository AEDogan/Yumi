"""Observed onset counts keep half-time dancing on alternating real beats."""
import math
def dance_rate(bpm):
    if not 40<=bpm<=260:return None
    safe=[bpm/120*x for x in (.5,1.,2.) if .6<=bpm/120*x<=1.2]
    return min(safe,key=lambda value:abs(value-1)) if safe else None

class BeatClock:
    def __init__(self):self.stamp=None;self.anchor=None;self.index=0.;self.beats=0.;self.rate=1.
    def advance(self,stamp,anchor,bpm):
        rate=dance_rate(bpm)
        if rate is None:return self.beats*.5
        factor=rate*120/bpm
        if self.stamp is None:
            self.stamp=stamp;self.anchor=anchor;self.rate=rate;self.beats=max(0.,stamp-anchor)*bpm/60*factor
            return self.beats*.5
        elapsed=max(0.,min(.2,stamp-self.stamp));self.stamp=stamp
        if anchor>self.anchor:
            self.index+=max(1,round((anchor-self.anchor)*bpm/60));self.anchor=anchor
        target=(self.index+(stamp-self.anchor)*bpm/60)*factor
        self.rate+=max(-elapsed*.3,min(elapsed*.3,rate-self.rate))
        self.beats+=elapsed*self.rate*2
        # Correct within a four-beat phrase, with a bounded phase velocity.
        error=(target-self.beats+2)%4-2
        self.beats+=max(-elapsed*.20,min(elapsed*.20,error*.2))
        return self.beats*.5
