"""Small beat accents layered on the authored full-body dance, not new clips."""
import math

def accents(genre,phase):
    beat=math.sin(phase*math.tau);half=math.sin(phase*math.pi)
    if genre in {'hip-hop','r&b','funk','soul','reggae','reggaeton','dancehall','afrobeats'}:
        return {'chest':(.025*beat,.035*half,.025*half),'head':(.025*beat,0.,0.)}
    if genre in {'house','techno','trance','disco','drum & bass','dubstep'}:
        return {'chest':(.018*beat,0.,.018*half),'leftUpperArm':(-.055*(.5+.5*half),0.,-.045*half),'rightUpperArm':(-.055*(.5-.5*half),0.,.045*half)}
    if genre in {'rock','metal','punk','indie'}:
        return {'head':(.065*beat,0.,0.),'chest':(.025*beat,0.,.02*half)}
    if genre in {'salsa','bachata','latin pop'}:
        return {'chest':(0.,.03*half,.045*half),'leftUpperArm':(.025*beat,0.,0.),'rightUpperArm':(-.025*beat,0.,0.)}
    return {'chest':(.012*beat,.015*half,.018*half)}
