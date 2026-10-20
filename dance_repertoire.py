"""Portable, genre-inspired choreography; no downloaded or licensed motion clips.

Twenty practical repertoire choices, not a purported worldwide sales ranking.
Each row authors twelve step/arm combinations. A seeded shuffle uses every
figure before revisiting it, with alternating lead and expression on later rounds.
"""
from dataclasses import dataclass
from functools import lru_cache
import hashlib
import random

@dataclass(frozen=True)
class Figure:
    step: str
    arms: str
    energy: float
    hips: float
    lead: int = 1
    variation: int = 0

# Step and arm vocabularies are sampled continuously, then fitted with limb IK.
# Different order, movement pairing, accent and amplitude are authored per genre.
ROWS = {
 'pop': ('touch/wave vstep/point box/fan heel/scoop side/reach mambo/box twist/roll back/swing skate/overhead tap/lock grape/fan bounce/wave', .85, .035),
 'rock': ('stomp/swing heel/point back/lock touch/reach twist/box march/overhead side/swing vstep/fan tap/point bounce/roll box/reach skate/scoop', .95, .018),
 'hip-hop': ('bounce/lock back/box skate/scoop heel/roll side/lock twist/reach vstep/box tap/wave stomp/scoop grape/roll mambo/point touch/fan', 1., .04),
 'r&b': ('side/scoop touch/wave back/roll twist/fan mambo/reach heel/scoop box/wave grape/swing tap/roll vstep/fan skate/reach bounce/box', .65, .065),
 'house': ('shuffle/swing skate/roll heel/reach vstep/overhead box/scoop back/fan touch/point grape/wave twist/box march/roll tap/swing side/overhead', 1., .03),
 'techno': ('march/box bounce/lock tap/overhead shuffle/reach stomp/roll vstep/box back/point heel/lock side/fan skate/overhead touch/scoop twist/wave', .95, .018),
 'trance': ('vstep/fan touch/overhead side/wave box/reach shuffle/fan back/overhead skate/wave heel/reach tap/roll grape/point march/scoop bounce/swing', .9, .03),
 'disco': ('twist/point grape/fan vstep/overhead heel/roll touch/point box/wave skate/fan back/reach side/roll mambo/scoop tap/lock march/swing', .9, .055),
 'funk': ('heel/lock twist/roll bounce/point skate/box back/scoop side/lock tap/fan mambo/roll touch/box vstep/wave grape/reach stomp/swing', .85, .055),
 'reggae': ('back/swing side/scoop bounce/roll tap/wave touch/box heel/swing twist/scoop mambo/reach grape/wave box/roll march/fan vstep/point', .6, .06),
 'reggaeton': ('mambo/box bounce/scoop side/roll tap/lock back/reach twist/box vstep/scoop heel/point touch/wave skate/fan grape/overhead stomp/swing', .85, .075),
 'afrobeats': ('skate/scoop heel/roll side/fan stomp/box bounce/wave mambo/swing twist/reach back/lock tap/scoop grape/point vstep/roll touch/overhead', .95, .065),
 'k-pop': ('vstep/lock tap/point box/wave touch/overhead heel/box skate/fan back/reach march/lock twist/scoop side/point grape/roll bounce/swing', .95, .04),
 'latin pop': ('mambo/fan side/reach twist/wave grape/scoop tap/point box/roll back/fan vstep/swing heel/overhead touch/box skate/lock bounce/reach', .85, .075),
 'salsa': ('mambo/reach back/fan side/scoop box/wave tap/roll twist/reach grape/fan heel/box vstep/point touch/swing skate/overhead march/lock', .85, .085),
 'bachata': ('side/wave tap/scoop grape/fan touch/reach twist/roll box/swing back/wave heel/fan mambo/box vstep/reach skate/point bounce/lock', .65, .085),
 'country': ('heel/swing grape/box stomp/point back/fan box/reach tap/lock march/scoop touch/swing vstep/roll twist/wave side/overhead skate/reach', .8, .025),
 'jazz': ('charleston/fan box/scoop heel/wave back/reach twist/roll grape/fan tap/box side/point march/swing mambo/overhead touch/lock vstep/reach', .7, .04),
 'metal': ('stomp/lock march/point bounce/box back/swing heel/reach vstep/lock tap/overhead side/box twist/point skate/swing touch/roll box/fan', 1., .015),
 'drum & bass': ('shuffle/box skate/lock back/roll heel/scoop tap/reach vstep/point bounce/overhead march/box side/wave twist/lock grape/fan stomp/swing', 1., .025),
}
ALIASES={'groove':'hip-hop','club':'house','latin':'salsa','soul':'r&b','dancehall':'reggae','dubstep':'drum & bass','punk':'rock','indie':'rock','blues':'jazz','folk':'country'}

def canonical(genre):
    value=ALIASES.get(genre,genre)
    return value if value in ROWS else 'pop'

class Repertoire:
    beats_per_figure=32
    def __init__(self,seed=0):self.seed=str(seed)
    @lru_cache(maxsize=12)
    def order(self,genre,round_index):
        # No shared mutable RNG: two views and four rigs get identical sequences.
        digest=hashlib.sha256(f'{self.seed}:{genre}'.encode()).digest()
        order=list(range(12));random.Random(int.from_bytes(digest[:8],'big')).shuffle(order)
        # Keep the base order for this song: each base figure is separated by
        # exactly 384 beats, even across rounds. Lead/variation change each round.
        return tuple(order)
    def figure(self,genre,index):
        genre=canonical(genre);row,energy,hips=ROWS[genre]
        round_index,slot=divmod(max(0,index),12)
        step,arms=row.split()[self.order(genre,round_index)[slot]].split('/')
        return Figure(step,arms,energy,hips,1 if round_index%2==0 else -1,round_index%3)
    def sample(self,genre,beat):
        index=int(max(0.,beat)//self.beats_per_figure)
        phase=max(0.,beat)%self.beats_per_figure
        blend=max(0.,(phase-(self.beats_per_figure-2))/2)
        blend=blend*blend*(3-2*blend)
        return self.figure(genre,index),self.figure(genre,index+1),blend
