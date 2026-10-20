"""Yumi paths and narrowly scoped compatibility with the previous installation."""
import os
from pathlib import Path

ROOT=Path(__file__).resolve().parent
APP_ID='YumiDesktopCompanion'
DATA_NAME='YumiDesktop'
LEGACY_DATA_NAME='MikaDesktop'

def env_value(name,default=None):
    """Old test/installation overrides remain readable during migration."""
    return os.environ.get('YUMI_'+name,os.environ.get('MIKA_'+name,default))

def data_dir(base=None):
    override=env_value('DATA_DIR')
    if override:return Path(override)
    parent=Path(base) if base is not None else Path(os.environ.get('APPDATA',str(ROOT)))
    target=parent/DATA_NAME;old=parent/LEGACY_DATA_NAME
    if old.exists() and not target.exists():
        # Same-volume rename preserves encrypted keys, browser storage and
        # every archived chat byte. A failed move leaves the old tree intact.
        old.rename(target)
    if old.exists() and target.exists():
        raise RuntimeError('İki kullanıcı veri klasörü bulundu. Verileri birleştirmeden önce güvenli geçiş denetimi gerekiyor; hiçbir kayıt değiştirilmedi.')
    return target

def migrated_default_name(value):
    value=str(value or '').strip()
    return 'Yumi' if not value or value.casefold()=='mika' else value
