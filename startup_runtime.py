"""Load Windows audio without unbounded WMI platform detection."""
import importlib,os,platform,struct,sys,threading
_lock=threading.RLock()
_startup_trace=None
def guard_startup(log_dir,seconds=25):
    import faulthandler,logging
    global _startup_trace
    logger=logging.getLogger('yumi.startup');logger.setLevel(logging.INFO)
    logger.info('Startup entered; bounded audio initialization enabled')
    _startup_trace=open(os.path.join(log_dir,'startup-trace.log'),'a',encoding='utf-8')
    faulthandler.dump_traceback_later(seconds,file=_startup_trace,exit=True)
def mark_startup_ready():
    import faulthandler,logging
    global _startup_trace
    if _startup_trace is not None:
        faulthandler.cancel_dump_traceback_later();_startup_trace.close();_startup_trace=None
        logging.getLogger('yumi.startup').info('Desktop window startup ready')
def prepare_audio_runtime():
    with _lock:
        if 'sounddevice' in sys.modules:return sys.modules['sounddevice']
        if os.name!='nt':return importlib.import_module('sounddevice')
        system,architecture=platform.system,platform.architecture
        # sounddevice only needs the OS and pointer width to choose its bundled DLL.
        # Scope these answers to this import; restore the public APIs afterwards.
        platform.system=lambda:'Windows'
        platform.architecture=lambda *args,**kwargs:(str(struct.calcsize('P')*8)+'bit','WindowsPE')
        try:return importlib.import_module('sounddevice')
        finally:platform.system,platform.architecture=system,architecture
