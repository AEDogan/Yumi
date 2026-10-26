"""Bounded desktop actions shared by typed and native voice commands."""
import time
from pathlib import Path
from PySide6.QtGui import QCursor
ROOT=Path(__file__).resolve().parent

def stop(window):
    window.pending_avatar_command=None
    finishing=window.music_runtime.stop() if hasattr(window,'music_runtime') else False
    if hasattr(window,'daily_director'):window.daily_director.cancel()
    from locomotion import halt
    halt(window)
    if hasattr(window,'voice_x'):del window.voice_x
    window.voice_target=None;window.music_dance=False;window.music_dancing=False
    window.manual_pose='clip' if finishing else 'idle';window.manual_pose_end=float('inf') if finishing else time.perf_counter()+3
    window.gesture_until=0.;window.avatar.hand_gesture=None
    for view in (window.avatar,window.overlay.avatar):
        if view.model:view.model.clip_loop=bool(finishing)

def clip(window,name,loop=False):
    stop(window);window._play_motion(ROOT/'motions'/name)
    if loop:
        window.manual_pose_end=float('inf')
        for view in (window.avatar,window.overlay.avatar):view.model.clip_loop=True

def execute(window,text):
    if text in ('ritme göre dans et','ritimle dans et','müzikle dans et'):text='müziğe göre dans et'
    if text in ('otomatik müzik tepkisini aç','otomatik müzik tepkisini kapat'):
        window.settings['music_auto']=text.endswith('aç')
        if not window.settings['music_auto'] and window.music_runtime.origin=='auto':window.music_runtime.stop(suppress=False)
        from app import save_settings
        save_settings(window.settings);return 'Otomatik müzik tepkisi '+('açık.' if window.settings['music_auto'] else 'kapalı.')
    if text in ('akıllı ev','akıllı evi aç','akıllı ev menüsü','akıllı ev menüsünü aç','akıllı ev panelini aç','cihazları göster','akıllı cihazlar','odaları göster'):
        if hasattr(window,'_open_smart_home'):window._open_smart_home()
        return 'Akıllı ev ve cihazlar panelini açıyorum.'
    from daily_scenarios import SCENARIOS
    from action_transition import ACTIONS,STOP
    if window.settings.get('skin')=='Clippy' and not text.startswith('karakter:') and text not in ('karakteri değiştir','sonraki karakter'):
        if text in ('el salla','merhaba de'):
            window.overlay.avatar.clippy.play('Wave');return 'Merhaba!'
        if text in ACTIONS or text in SCENARIOS:
            return 'Clippy kendi orijinal animasyonlarını kullanıyor.'
    runtime=getattr(window,'music_runtime',None)
    if runtime and runtime.active and runtime.motion and runtime.motion.pole and text not in STOP and (text in ACTIONS or text in SCENARIOS or text=='müzik dinle' or text.startswith('karakter:')):
        runtime.stop();window.pending_avatar_command=text
        return 'Önce direği bırakıp hareketi tamamlıyorum, ardından geçiyorum.'
    if text in SCENARIOS:
        existing=window.overlay.avatar.furniture
        if existing and existing.activity and existing.activity.kind==SCENARIOS[text] and not existing.exit_requested:
            window.daily_director.manual=SCENARIOS[text];return 'Zaten bu senaryodayım.'
        if window.daily_director.switch_workspace(SCENARIOS[text]):
            window.daily_director.manual=SCENARIOS[text];return 'Tamam, masa başında devam ediyorum.'
        stop(window);window.daily_director.command(SCENARIOS[text]);return 'Tamam, hazırlanıyorum.'
    if text in ('günlük senaryoları aç','günlük senaryoları kapat'):
        window.settings['daily_scenarios']=text.endswith('aç')
        if text.endswith('kapat'):window.daily_director.cancel()
        from app import save_settings
        save_settings(window.settings);return 'Günlük senaryolar '+('açık.' if window.settings['daily_scenarios'] else 'kapalı.')
    if text.startswith('müzik türü '):
        from music_analysis import genre_name
        genre=genre_name(text[len('müzik türü '):])
        automatic=text[len('müzik türü '):]=='otomatik'
        if genre=='unknown' and not automatic:return 'Bu müzik türünü tanımadım; müzik menüsünden seçebilirsin.'
        window.settings['music_family']=genre
        from app import save_settings
        save_settings(window.settings);return 'Müzik türü: '+('otomatik; medya etiketi ve yerel ses analizi' if automatic else genre)
    from action_transition import defer
    from action_transition import ACTIONS
    if (text in ACTIONS or text.startswith('karakter:')) and hasattr(window,'daily_director'):
        window.daily_director.manual=None;window.daily_director.suppressed_until=time.perf_counter()+30
    pending=defer(window,text)
    if pending is not None:return pending
    gestures={'ok işareti yap':'ok','okey işareti yap':'ok','başparmağını kaldır':'thumbs_up','başparmakla onayla':'thumbs_up','elini beline koy':'hip','avuçlarını aç':'open_palm','işaret et':'point','omuz silk':'shrug'}
    if text in gestures:
        model=window.overlay.avatar.model;style=gestures[text]
        if not model or not model.hand_poses.supports(style):return 'Bu modelde bu el hareketi için uygun parmak iskeleti yok.'
        stop(window);window.avatar.hand_gesture=style;window.gesture_until=time.perf_counter()+4.;window.last_user_action=time.perf_counter();window.overlay.sync()
        return 'Tamam.'
    if text in ('sağa git','sola git','buraya gel'):
        stop(window);window.overlay.show();left,right=window.overlay.walk_limits()
        x=QCursor.pos().x()-window.overlay.width()/2 if text=='buraya gel' else window.overlay.x()+(220 if text=='sağa git' else -220)
        window.voice_target=max(left,min(right,x));window.overlay.manually_placed=False
        return 'Geliyorum.' if text=='buraya gel' else 'Yürüyorum.'
    if text in ('dur','yürümeyi durdur','ayağa kalk','kalk','dansı durdur','dans etmeyi bırak','hareketi durdur','müzik dansını durdur'):
        stop(window)
        if getattr(getattr(window,'music_runtime',None),'finishing',None) is not None:return 'Elimi bırakıp dansı bitiriyorum.'
        if window.overlay.avatar.furniture:
            window.overlay.avatar.stand();return 'Kalkıyorum.'
        window.last_user_action=time.perf_counter();return 'Tamam, durdum.'
    if text in ('otur','koltuğa otur','biraz dinlen','bilgisayara otur','çalışmaya başla'):
        try:
            stop(window);window.overlay.avatar.sit('work' if text in ('bilgisayara otur','çalışmaya başla') else 'lounge');window.overlay.show();window.overlay.sync()
        except (ValueError,OSError) as error:return str(error)
        return 'Koltuğa geçiyorum.'
    if text in ('müziğe göre dans et','dans et','direk dansı yap','pole dance yap','müzik dinle'):
        if not window.overlay.avatar.model:return 'Müzik hareketleri için önce bir VRM karakter seç.'
        stop(window);window.music_runtime.start('listen' if text=='müzik dinle' else 'pole' if text in ('direk dansı yap','pole dance yap') else 'dance')
        return 'Dinliyorum.' if text=='müzik dinle' else 'Dansa başlıyorum; müziğin ritmi belirince ona uyacağım.'
    if text in ('karakteri değiştir','sonraki karakter') or text.startswith('karakter:'):
        from skins import available
        from voice_profiles import profile,character_name
        entries=[(label,key) for label,key in available(window.settings) if key.startswith('vrm:') or key=='Clippy']
        if not entries:return 'Kütüphanede VRM karakter yok.'
        if text.startswith('karakter:'):
            requested=text.split(':',1)[1].casefold();matches=[key for label,key in entries if str(profile(window.settings,key).get('name','')).casefold()==requested or label.casefold()==requested]
            if len(matches)!=1:return 'Karakter adı bulunamadı veya birden fazla model aynı adı kullanıyor.'
            key=matches[0]
        else:
            keys=[key for _,key in entries];current=window.settings['skin'];key=keys[(keys.index(current)+1)%len(keys)] if current in keys else keys[0]
        stop(window);window.overlay.select_skin(key)
        if getattr(window,'native_audio',None) and window.native_audio.active:
            window.voice_restart=True;window.native_audio.stop()
        return 'Karakter: '+character_name(window.settings)
    return None

def travel(window,dt):
    target=getattr(window,'voice_target',None)
    if target is None:return False
    if window.overlay.drag is not None:window.voice_target=None;return False
    left,right=window.overlay.walk_limits();target=max(left,min(right,target));distance=target-window.overlay.x()
    if abs(distance)<2:
        from locomotion import halt
        halt(window)
        window.voice_target=None;window.manual_pose='idle';window.manual_pose_end=time.perf_counter()+3;window.last_user_action=time.perf_counter();return True
    from locomotion import stride_step
    direction=1 if distance>0 else -1
    window.avatar.walk_direction=direction;window.avatar.walking_turn=True
    if abs(window.overlay.avatar.yaw.angle-90*direction)>5:
        from locomotion import halt
        halt(window);window.manual_pose='idle';window.manual_pose_end=time.perf_counter()+.25
        window.overlay.sync();return True
    step=stride_step(window,direction,dt)
    x=getattr(window,'voice_x',float(window.overlay.x()))
    if abs(x-window.overlay.x())>1.5:x=float(window.overlay.x())
    x=max(left,min(right,x+direction*min(abs(step),abs(target-x))))
    window.voice_x=x;window.overlay.move(round(x),window.overlay.y());window.roam_x=x;return True

def music(window,now):
    if hasattr(window,'music_runtime'):window.music_runtime.tick(now)
