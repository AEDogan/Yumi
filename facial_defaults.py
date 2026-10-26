"""Opt-in authored rest expressions; absent metadata leaves existing models unchanged."""
import math
from model_analysis import expression_name

def default_weights(data):
    extras=data.g.get('extras',{})
    config=extras.get('yumi',{}) if isinstance(extras,dict) else {}
    defaults=config.get('defaultExpressions',{}) if isinstance(config,dict) else {}
    if not isinstance(defaults,dict):return {}
    result={}
    for name,amount in defaults.items():
        if not isinstance(amount,(int,float)) or not math.isfinite(amount) or not 0<=amount<=1:continue
        for mesh,index,weight in data.expressions.get(expression_name(data,name),[]):
            key=(mesh,index);result[key]=min(1.,result.get(key,0.)+amount*weight)
    return result
