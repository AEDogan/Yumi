"""Skill outcome drives expression; occupied hands keep their scenario pose."""
def reaction(name,result):
    if name=='alert':return 'warning',None
    if result.get('needs_clarification'):return 'question',None
    if not result.get('ok'):return 'uncertain',None
    if name in ('daily_briefing','arrive_home_routine'):return 'greeting',None
    if name.startswith(('get_','list_','read_','recall_','discover_')):return 'explain',None
    return 'agree','thumbs_up'

def face(intent,weight):
    return {name:amount*weight for name,amount in {
        'agree':{'happy':.22},'greeting':{'happy':.3},'uncertain':{'sad':.16},
        'question':{'surprised':.16},'warning':{'surprised':.22},'explain':{'relaxed':.12}
    }.get(intent,{}).items()}

def head_pose(intent,age):
    import math
    weight=max(0.,min(1.,age/.18,(2.8-age)/.6))
    return .045*math.sin(age*5)*weight if intent=='agree' else 0.
