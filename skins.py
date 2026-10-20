"""Local VRM library. Removed models are preserved under work/removed-skins."""
from pathlib import Path
import shutil,hashlib
from vrm import load_data
ROOT=Path(__file__).resolve().parent
LIBRARY=ROOT/'skins'

def skin_path(key):
    if not key.startswith('vrm:'):return None
    name=key[4:]
    if Path(name).name!=name or Path(name).suffix.lower()!='.vrm':return None
    path=LIBRARY/name
    return path if path.is_file() else None

def default_name(key):
    if not key.startswith('vrm:'):return key if key in ('Sakura','Midnight','Mint') else 'Yumi'
    path=skin_path(key)
    if path:
        try:
            meta=load_data(str(path.resolve())).meta
            name=str(meta.get('title') or meta.get('name') or '').strip()
            if name and not name.isdecimal() and not name.casefold().endswith('.vrm'):return name
        except (OSError,ValueError):pass
    return 'İsimsiz karakter'

def available(settings=None):
    entries=[(name,name) for name in ('Sakura','Midnight','Mint')]
    if LIBRARY.exists():
        for path in sorted(LIBRARY.glob('*.vrm')):
            try:
                key='vrm:'+path.name
                entries.append((default_name(key),key))
            except Exception:continue
    if settings is not None:
        profiles=settings.get('voice_profiles',{})
        labels=[]
        for fallback,key in entries:
            saved=profiles.get(key,{})
            if not isinstance(saved,dict):saved={}
            name=str(saved.get('name') or '').strip() or fallback
            labels.append((name,key))
        return labels
    return entries

def existing_model_key(source):
    source=Path(source).resolve()
    if not source.is_file():return None
    digest=hashlib.sha256(source.read_bytes()).digest()
    for path in LIBRARY.glob('*.vrm'):
        if hashlib.sha256(path.read_bytes()).digest()==digest:return 'vrm:'+path.name
    return None

def add_model(source):
    source=Path(source).resolve()
    if source.suffix.lower()!='.vrm':raise ValueError('Yalnız .vrm karakter dosyaları destekleniyor.')
    load_data(str(source))
    LIBRARY.mkdir(exist_ok=True)
    content=source.read_bytes();digest=hashlib.sha256(content).digest()
    for path in LIBRARY.iterdir():
        if path.suffix.lower()!='.vrm':continue
        if hashlib.sha256(path.read_bytes()).digest()==digest:return 'vrm:'+path.name
    name=source.stem;extension=source.suffix.lower();target=LIBRARY/(name+extension);number=2
    while target.exists():target=LIBRARY/(name+'-'+str(number)+extension);number+=1
    target.write_bytes(content);return 'vrm:'+target.name

def remove_model(key):
    path=skin_path(key)
    if path is None:return
    target_dir=ROOT/'work/removed-skins';target_dir.mkdir(parents=True,exist_ok=True)
    target=target_dir/path.name;number=2
    while target.exists():target=target_dir/(path.stem+'-'+str(number)+'.vrm');number+=1
    if not path.resolve().is_relative_to(LIBRARY.resolve()) or not target.resolve().is_relative_to(target_dir.resolve()):raise ValueError('Invalid model path')
    shutil.move(str(path),str(target))
