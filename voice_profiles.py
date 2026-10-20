"""Persist each character's voice preferences without guessing VRM gender."""
from app_paths import migrated_default_name
VOICES=[(f'Gemini Live · {name} · {label}',f'gemini-live:{name}',gender) for name,gender,label in (
    ('Kore','female','Kadın · net'),('Puck','male','Erkek · canlı'),
    ('Charon','male','Erkek · sakin'),('Aoede','female','Kadın · yumuşak'),('Fenrir','male','Erkek · güçlü'))]
OPENAI_VOICES=['marin','cedar','coral','nova','shimmer','alloy','ash','ballad','echo','fable','onyx','sage','verse']
def profile(settings,key=None):
 key=key or settings['skin'];saved=settings.get('voice_profiles',{}).get(key)
 from skins import default_name
 name=default_name(key)
 if isinstance(saved,dict):
  result={**{'name':name,'gender':'female','speech_voice':'gemini-live:Kore','voice':'marin','adult':False},**saved}
  # Preserve the named voice in old profiles; the previous "any" catalog
  # allowed a contradictory gender filter to be saved alongside it.
  result['name']=migrated_default_name(result.get('name')) if str(result.get('name') or '').strip() else name
  result.setdefault('size',settings.get('size',100) if key==settings['skin'] else 100)
  actual=next((g for _,v,g in VOICES if v==result['speech_voice']),None)
  if actual and result['gender']!='any':result['gender']=actual
  return result
 voice=settings.get('speech_voice','gemini-live:Kore') if key==settings['skin'] else 'gemini-live:Kore'
 gender=next((g for _,v,g in VOICES if v==voice),'female')
 return {'name':name,'gender':'female' if gender=='any' else gender,'speech_voice':voice,'voice':settings.get('voice','marin'),'adult':False,'size':settings.get('size',100) if key==settings['skin'] else 100}
def apply_profile(settings,key):
 previous=profile(settings);settings.setdefault('voice_profiles',{})[settings['skin']]=previous
 saved=profile(settings,key)
 settings['skin']=key;settings.update(speech_voice=saved['speech_voice'],voice=saved.get('voice','marin'),size=int(saved.get('size',100)));settings['voice_profiles'][key]=saved
 return saved

def character_name(settings):
 return str(profile(settings).get('name','Yumi')).strip() or 'Yumi'

def wake_command(text,name):
 """Only whole name tokens wake the assistant; 'Amerika' does not match Yumi."""
 import re,unicodedata
 def normal(value):
  return ''.join(c for c in unicodedata.normalize('NFKD',value.casefold().replace('ı','i')) if not unicodedata.combining(c))
 # Normalize each character independently to retain original text offsets.
 normalized='';positions=[]
 for i,c in enumerate(text):
  part=normal(c);normalized+=part;positions.extend([i]*len(part))
 # Turkish recognizers spell foreign character names phonetically. Keep a small
 # exact-token alias list; broad fuzzy matching would wake on unrelated speech.
 aliases={'clara':('klara','cılara','ciılara'),'david':('davit','deyvid')}
 names=(normal(name),)+tuple(normal(v) for v in aliases.get(normal(name),()))
 match=re.search(r'(?<!\w)(?:'+'|'.join(re.escape(v) for v in names)+r')(?!\w)',normalized)
 if not match:return False,''
 end=positions[match.end()-1]+1
 return True,text[end:].lstrip(' ,:!?.')
