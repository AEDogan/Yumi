"""Small, non-repeating activity beats; a seated beat never changes furniture."""
import math
EVENTS={
    'rest':('stretch','yawn','shoulders','glance'),
    'reading':('page','page','glance','settle'),
    'tv':('remote','glance','settle'),
    'typing':('think','mouse','settle'),
    'coding':('think','mouse','glance'),
    'browsing':('scroll','think','glance'),
    'meeting':('nod','note','glance'),
    'coffee':('sip','glance'), 'window':('sip','glance')}

def next_event(kind,clock,previous,rng):
    choices=EVENTS.get(kind,())
    if kind=='tv' and clock>=600:choices=('snack','remote','snack','settle')
    if kind=='coffee' and clock<25:return None
    if kind in ('coffee','window') and previous is None:return 'sip'
    candidates=[event for event in choices if event!=previous] or list(choices)
    return rng.choice(candidates) if candidates else None

def duration(event):return 5. if event=='sip' else 3.8 if event=='snack' else 4.2 if event in ('stretch','yawn') else 3.2
def pulse(event,clock):
    if event=='sip':
        rise=max(0.,min(1.,clock/1.6));fall=max(0.,min(1.,(clock-2.8)/2.2))
        return rise*rise*(3-2*rise)*(1-fall*fall*(3-2*fall))
    return math.sin(math.pi*max(0.,min(1.,clock/duration(event)))) if event else 0.
def face(event,clock):
    weight=pulse(event,clock)
    if event=='yawn':return {'aa':.25*weight,'relaxed':.25*weight,'blink':.5*weight}
    if event=='think':return {'relaxed':.12*weight}
    if event in ('sip','settle'):return {'relaxed':.15*weight}
    if event=='nod':return {'happy':.12*weight}
    return {}
