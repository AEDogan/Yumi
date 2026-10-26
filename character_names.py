"""User-approved character names, with a one-time migration of old labels."""
import json,os
from pathlib import Path
REVISION='2026-10-22-approved-1'
NAMES={
 'vrm:madjin-Darkness_Shibu.vrm':'Reina','vrm:madjin-HairSample_Female.vrm':'Mira',
 'vrm:madjin-HairSample_Male.vrm':'Ren','vrm:madjin-Sendagaya_Shibu.vrm':'Akira',
 'vrm:madjin-Sendagaya_Shino.vrm':'Shiori','vrm:madjin-Victoria_Rubin.vrm':'Victoria',
 'vrm:madjin-Vita.vrm':'Vita','vrm:madjin-Vivi.vrm':'Vivi',
 'vrm:madjin-AvatarSample_A.vrm':'Yumi','vrm:madjin-AvatarSample_B.vrm':'Haru',
 'vrm:madjin-AvatarSample_C.vrm':'Sora','Clippy':'Clippy',
 'vrm:1444557518205200992.vrm':'Kaito','vrm:4107103476080737641.vrm':'Eddy',
 'vrm:4405699356021512973.vrm':'Clara','vrm:8151855394303479444.vrm':'Neko',
 'vrm:Sonetto.vrm':'Lyra',
}
def migrate(settings):
 if settings.get('character_names_revision')==REVISION:return False
 profiles=settings.setdefault('voice_profiles',{})
 for key,name in NAMES.items():
  saved=profiles.setdefault(key,{})
  if isinstance(saved,dict):saved.update(name=name,wake_alias=name)
 settings['character_names_revision']=REVISION
 return True

def refresh(settings,path=None):
 """Refresh only persisted name fields; leave live voice/UI state intact."""
 if path is None:
  from app_paths import data_dir
  path=data_dir()/'settings.json'
 try:saved=json.loads(Path(path).read_text(encoding='utf-8-sig'))
 except (OSError,ValueError):return False
 migrate(saved);changed=False
 settings['character_names_revision']=saved['character_names_revision']
 for key,profile in saved.get('voice_profiles',{}).items():
  if not isinstance(profile,dict):continue
  live=settings.setdefault('voice_profiles',{}).setdefault(key,{})
  if not isinstance(live,dict):continue
  for field in ('name','wake_alias'):
   if field in profile and live.get(field)!=profile[field]:live[field]=profile[field];changed=True
 return changed
