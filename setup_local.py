"""Download the optional local Turkish voice model from its publisher."""
from pathlib import Path
import io,zipfile,requests
root=Path(__file__).resolve().parent/'models'
root.mkdir(exist_ok=True)
if not (root/'vosk-model-small-tr-0.3').exists():
    print('Turkce ses modeli indiriliyor (~35 MB)...')
    response=requests.get('https://alphacephei.com/vosk/models/vosk-model-small-tr-0.3.zip',timeout=180)
    response.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        for name in archive.namelist():
            if not (root/name).resolve().is_relative_to(root.resolve()):raise ValueError('Invalid archive path')
        archive.extractall(root)
print('Yerel ses modeli hazir.')

import os
os.environ['HF_HUB_DISABLE_XET']='1'
from faster_whisper.utils import download_model
whisper=root/'whisper-small'
if not (whisper/'model.bin').exists():
    print('Whisper small Turkce konusma modeli indiriliyor (~480 MB)...')
    download_model('small',output_dir=str(whisper))
print('Whisper modeli hazir.')
