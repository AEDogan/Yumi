"""Publisher-only CLI: sign a model together with its completed acceptance report."""
import argparse, base64, json, zipfile
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from model_packages import canonical, digest, validate_manifest

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--key', required=True, type=Path)
    p.add_argument('--init', action='store_true')
    p.add_argument('--model', type=Path)
    p.add_argument('--name')
    p.add_argument('--group', choices=('anime','retro','witcher'))
    p.add_argument('--report', type=Path)
    p.add_argument('--output', type=Path)
    args = p.parse_args()
    if args.init:
        if args.key.exists():
            p.error('Anahtar zaten var; üzerine yazılmadı.')
        key = Ed25519PrivateKey.generate()
        args.key.parent.mkdir(parents=True, exist_ok=True)
        args.key.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        public = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        print(json.dumps({'keys': {'yumi-local-v1': base64.b64encode(public).decode()}}))
        return
    if not all((args.model, args.name, args.group, args.report, args.output)):
        p.error('--model, --name, --group, --report ve --output gerekli.')
    model = args.model.read_bytes()
    manifest = {'format':'yumi-model-package', 'version':1, 'runtime':'yumi-v1',
                'publisher':'yumi-local-v1', 'name':args.name, 'group':args.group, 'model_sha256':digest(model),
                'acceptance':json.loads(args.report.read_text(encoding='utf-8'))}
    validate_manifest(manifest)
    key = serialization.load_pem_private_key(args.key.read_bytes(), password=None)
    raw = canonical(manifest)
    if args.output.suffix.lower() != '.yumimodel' or args.output.exists():
        p.error('Yeni bir .yumimodel çıktı yolu belirt.')
    with zipfile.ZipFile(args.output, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('manifest.json', raw)
        archive.writestr('manifest.sig', key.sign(raw))
        archive.writestr('model.vrm', model)
    print('Paket oluşturuldu: ' + str(args.output))

if __name__ == '__main__':
    main()
