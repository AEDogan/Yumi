"""Bounded chat context shared over a private pipe, never command-line arguments."""
import json

MAX_CHARS=16000
MAX_LINE=MAX_CHARS*12+4096

def recent_history(records):
    if not isinstance(records,list):return []
    result=[];remaining=MAX_CHARS
    for record in reversed(records[-96:]):
        if not isinstance(record,dict) or not record.get('complete',True):continue
        role=record.get('role');text=record.get('text')
        if role not in ('user','assistant') or not isinstance(text,str) or not text.strip():continue
        text=text[-min(4000,remaining):]
        result.append({'role':role,'text':text});remaining-=len(text)
        if not remaining or len(result)>=24:break
    return list(reversed(result))

def history_line(records):
    return json.dumps({'history':recent_history(records)},ensure_ascii=False)+'\n'

def read_history(stream):
    line=stream.readline(MAX_LINE)
    if not line.endswith('\n'):raise ValueError('Invalid context envelope')
    if line.strip()=='STOP':return None
    value=json.loads(line)
    return recent_history(value.get('history',[])) if isinstance(value,dict) else []

def content_turns(records):
    return [{'role':'model' if r['role']=='assistant' else 'user','parts':[{'text':r['text']}]} for r in recent_history(records)]
