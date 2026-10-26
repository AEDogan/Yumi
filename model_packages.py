"""Signed, data-only character packages. Publisher keys never ship with Yumi."""
from pathlib import Path
from functools import lru_cache
import base64, hashlib, json, os, tempfile, zipfile
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

ROOT = Path(__file__).resolve().parent
MAX_MODEL = 256 * 1024 * 1024
CHECKS = ('rig', 'idle', 'walk', 'sit_stand', 'dance', 'contacts', 'expressions', 'hair_cloth')
FILES = {'manifest.json', 'manifest.sig', 'model.vrm'}
GROUPS = {'anime': 'Anime paketi', 'retro': 'Retro paketi', 'witcher': 'Witcher paketi'}

def digest(data):
    return hashlib.sha256(data).hexdigest()

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')

def validate_manifest(manifest):
    if manifest.get('format') != 'yumi-model-package' or manifest.get('version') != 1:
        raise ValueError('Model paketi sürümü desteklenmiyor.')
    if manifest.get('group') not in GROUPS:
        raise ValueError('Model paketi grubu Anime, Retro veya Witcher olmalı.')
    name = manifest.get('name')
    if not isinstance(name, str) or not name.strip() or len(name) > 30 or not all(c.isalpha() or c in " -'" for c in name):
        raise ValueError('Paketin model adı geçersiz.')
    if manifest.get('runtime') != 'yumi-v1':
        raise ValueError('Paket bu Yumi sürümüyle uyumlu değil.')
    report = manifest.get('acceptance', {})
    if (report.get('model_sha256') != manifest.get('model_sha256') or
        report.get('suite') != 'yumi-character-v1' or
        any(report.get('checks', {}).get(check) != 'pass' for check in CHECKS)):
        raise ValueError('Modelin hareket ve fizik kabul testleri tamamlanmamış.')

def verify_manifest(raw, signature):
    try:
        manifest = json.loads(raw)
        trust = json.loads((ROOT / 'assets/characters/package-trust.json').read_text(encoding='utf-8'))
        key = trust['keys'][manifest['publisher']]
        Ed25519PublicKey.from_public_bytes(base64.b64decode(key, validate=True)).verify(signature, raw)
        validate_manifest(manifest)
        return manifest
    except (KeyError, TypeError, ValueError, OSError) as error:
        raise ValueError('Model paketi doğrulanamadı: ' + str(error)) from error
    except Exception as error:
        raise ValueError('Model paketi imzası geçersiz.') from error

def read_package(source):
    source = Path(source)
    if source.suffix.lower() != '.yumimodel':
        raise ValueError('Yalnız onaylı .yumimodel paketleri eklenebilir.')
    try:
        with zipfile.ZipFile(source) as archive:
            entries = archive.infolist()
            if len(entries) != 3 or {i.filename for i in entries} != FILES:
                raise ValueError('Paket dosyaları geçersiz.')
            limits = {'manifest.json': 65536, 'manifest.sig': 64, 'model.vrm': MAX_MODEL}
            if any(i.file_size > limits[i.filename] or i.flag_bits & 1 for i in entries):
                raise ValueError('Paket boyutu veya şifreleme desteklenmiyor.')
            raw = archive.read('manifest.json')
            signature = archive.read('manifest.sig')
            manifest = verify_manifest(raw, signature)
            model = archive.read('model.vrm')
            if digest(model) != manifest['model_sha256']:
                raise ValueError('Model dosyası paketten sonra değiştirilmiş.')
            return manifest, model, raw, signature
    except zipfile.BadZipFile as error:
        raise ValueError('Model paketi okunamadı.') from error

def install_package(source):
    manifest, model, raw, signature = read_package(source)
    from vrm import load_data
    from model_compatibility import profile
    library = ROOT / 'skins'
    library.mkdir(exist_ok=True)
    # Validate before publishing either file; no archive paths are extracted.
    with tempfile.TemporaryDirectory(dir=library) as folder:
        staging = Path(folder) / 'model.vrm'
        staging.write_bytes(model)
        report = profile(load_data(str(staging)))
        if not report['desktop_supported']:
            raise ValueError('Paketin iskeleti masaüstü hareketlerini desteklemiyor.')
        name = 'package-' + digest(model) + '.vrm'
        receipt = library / (name + '.json')
        staged_receipt = Path(folder) / 'receipt.json'
        staged_receipt.write_text(json.dumps({'manifest': base64.b64encode(raw).decode(), 'signature': base64.b64encode(signature).decode()}), encoding='utf-8')
        os.replace(staging, library / name)
        os.replace(staged_receipt, receipt)
    return 'vrm:' + name

@lru_cache(maxsize=128)
def _approved(path, size, modified, receipt_modified, trust_modified):
    path = Path(path)
    try:
        receipt = path.with_name(path.name + '.json')
        if receipt.exists():
            doc = json.loads(receipt.read_text(encoding='utf-8'))
            manifest = verify_manifest(base64.b64decode(doc['manifest']), base64.b64decode(doc['signature']))
            return manifest if digest(path.read_bytes()) == manifest['model_sha256'] else None
        baseline = json.loads((ROOT / 'assets/characters/legacy-models.json').read_text(encoding='utf-8'))
        entry = baseline.get(path.name)
        return entry if entry and digest(path.read_bytes()) == entry['model_sha256'] else None
    except Exception:
        return None

def approved_model(path):
    path = Path(path)
    try:
        info = path.stat()
        receipt = path.with_name(path.name + '.json')
        trust = ROOT / 'assets/characters/package-trust.json'
        return _approved(str(path), info.st_size, info.st_mtime_ns, receipt.stat().st_mtime_ns if receipt.exists() else 0, trust.stat().st_mtime_ns)
    except OSError:
        return None
