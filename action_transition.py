"""Queue explicit avatar actions until a furniture exit has completed."""
import time

STOP={'dur','yürümeyi durdur','ayağa kalk','kalk','dansı durdur','dans etmeyi bırak','hareketi durdur','müzik dansını durdur'}
SIT={'otur':'lounge','koltuğa otur':'lounge','biraz dinlen':'lounge','bilgisayara otur':'work','çalışmaya başla':'work'}
ACTIONS=set(SIT)|{'sağa git','sola git','buraya gel','dans et','hadi dans et','müziğe göre dans et','el salla','merhaba de','ok işareti yap','okey işareti yap','başparmağını kaldır','başparmakla onayla','elini beline koy','avuçlarını aç','işaret et','omuz silk','karakteri değiştir','sonraki karakter'}
ACTIONS.update({'direk dansı yap','pole dance yap','müzik dinle'})

def defer(window,command):
    if command in STOP:
        window.pending_avatar_command=None
        return None
    if command not in ACTIONS and not command.startswith('karakter:'):return None
    scene=getattr(window.overlay.avatar,'furniture',None)
    if scene is None:
        window.pending_avatar_command=None
        return None
    window.last_user_action=time.perf_counter()
    if SIT.get(command)==scene.mode and not scene.exit_requested:
        window.pending_avatar_command=None
        return 'Zaten bu konuma geçiyorum veya oturuyorum.'
    window.pending_avatar_command=command
    scene.request_exit()
    return 'Önce kalkıyorum, ardından istediğin hareketi yapacağım.'

def dispatch(window):
    if getattr(getattr(window,'music_runtime',None),'finishing',None) is not None:return False
    command=getattr(window,'pending_avatar_command',None)
    if not command or window.overlay.avatar.furniture is not None:return False
    if getattr(window.overlay,'drag',None) is not None:return False
    window.pending_avatar_command=None
    window.last_user_action=time.perf_counter()
    response=window._local_command(command)
    if response:window.show_bubble(response)
    return True
