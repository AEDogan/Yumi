"""Local VRM library. Removed models are preserved under work/removed-skins."""
from pathlib import Path
import shutil,hashlib,json
from vrm import load_data
ROOT=Path(__file__).resolve().parent
LIBRARY=ROOT/'skins'
BUILTIN_ROOT=ROOT/'assets/characters'
_manifest=BUILTIN_ROOT/'manifest.json'
BUILTINS=json.loads(_manifest.read_text(encoding='utf-8'))['models'] if _manifest.is_file() else {}

def is_builtin(key):
    return key=='Clippy' or key in BUILTINS

def default_skin():
    preferred='vrm:madjin-AvatarSample_A.vrm'
    if skin_path(preferred):return preferred
    return next((key for key in BUILTINS if skin_path(key)), 'Clippy')

def valid_skin(key):
    return isinstance(key,str) and (key=='Clippy' or skin_path(key) is not None)

def skin_path(key):
    if not key.startswith('vrm:'):return None
    name=key[4:]
    if Path(name).name!=name or Path(name).suffix.lower()!='.vrm':return None
    path=(BUILTIN_ROOT/name) if key in BUILTINS else (LIBRARY/name)
    if not path.is_file():return None
    if key not in BUILTINS:
        from model_packages import approved_model
        if not approved_model(path):return None
    return path

def default_name(key):
    from character_names import NAMES
    if key.startswith('vrm:') and key not in BUILTINS:
        from model_packages import approved_model
        entry=approved_model(LIBRARY/key[4:]) if Path(key[4:]).name==key[4:] else None
        if entry:return entry['name']
    if key in NAMES:return NAMES[key]
    if key=='Clippy':return 'Clippy'
    if key in BUILTINS:return BUILTINS[key]['name']
    if not key.startswith('vrm:'):return 'Yumi'
    path=skin_path(key)
    if path:
        try:
            meta=load_data(str(path.resolve())).meta
            name=str(meta.get('title') or meta.get('name') or '').strip()
            if name and not name.isdecimal() and not name.casefold().endswith('.vrm'):return name
        except (OSError,ValueError):pass
    return 'İsimsiz karakter'

def available(settings=None):
    entries=[(item['name'],key) for key,item in BUILTINS.items() if skin_path(key)]
    entries.append(('Clippy','Clippy'))
    if LIBRARY.exists():
        for path in sorted(LIBRARY.glob('*.vrm')):
            try:
                key='vrm:'+path.name
                if skin_path(key):entries.append((default_name(key),key))
            except Exception:continue
    return [(default_name(key),key) for _,key in entries]

def package_group(key):
    if key=='Clippy':return 'retro'
    if key in BUILTINS:return 'anime'
    if isinstance(key,str) and key.startswith('vrm:') and Path(key[4:]).name==key[4:]:
        from model_packages import approved_model
        entry=approved_model(LIBRARY/key[4:])
        if entry:return entry.get('group','anime')
    return None

def grouped_available(settings=None):
    from model_packages import GROUPS
    entries=available(settings)
    return [(title,[(name,key) for name,key in entries if package_group(key)==group])
            for group,title in GROUPS.items()]

def existing_model_key(source):
    source=Path(source).resolve()
    if not source.is_file():return None
    digest=hashlib.sha256(source.read_bytes()).digest()
    for path in [*(BUILTIN_ROOT/key[4:] for key in BUILTINS),*LIBRARY.glob('*.vrm')]:
        if hashlib.sha256(path.read_bytes()).digest()==digest:return 'vrm:'+path.name
    return None

def add_model(source):
    from model_packages import install_package
    return install_package(source)


def remove_model(key):
    if is_builtin(key):raise ValueError('Yerleşik karakterler kaldırılamaz.')
    path=skin_path(key)
    if path is None:return
    target_dir=ROOT/'work/removed-skins';target_dir.mkdir(parents=True,exist_ok=True)
    target=target_dir/path.name;number=2
    while target.exists():target=target_dir/(path.stem+'-'+str(number)+'.vrm');number+=1
    if not path.resolve().is_relative_to(LIBRARY.resolve()) or not target.resolve().is_relative_to(target_dir.resolve()):raise ValueError('Invalid model path')
    shutil.move(str(path),str(target))
