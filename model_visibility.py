"""User-controlled character visibility, independent of chat and voice."""
import time

def visible(owner):return bool(owner.settings.get('model_visible',True))

def apply(owner):
    shown=visible(owner);game=bool(getattr(getattr(owner,'fullscreen_pause',None),'paused',False))
    # The current shell intentionally keeps its master AvatarView offscreen.
    # It is a state source, not a second character in the 31px status strip.
    owner.avatar.setVisible(shown and not hasattr(owner,'navigation'))
    button=getattr(owner,'model_visibility_button',None)
    if button:
        button.setText('Modeli gizle' if shown else 'Modeli göster')
        button.setToolTip('Yumi çalışmaya devam eder; yalnız karakter görünürlüğü değişir.')
    for view in (owner.avatar,owner.overlay.avatar):view.set_render_paused(not shown or game)
    owner.overlay.setVisible(shown and not game)
    owner.roam_clock=time.perf_counter();owner.last_render_movement=0.
    if not shown:owner.move_animation.stop()

def set_visible(owner,value):
    old=owner.settings.get('model_visible',True);owner.settings['model_visible']=bool(value)
    try:
        from app import save_settings
        save_settings(owner.settings)
    except OSError:
        owner.settings['model_visible']=old
        owner.show_error('Model görünürlüğü kaydedilemedi.');return
    apply(owner)

def add_action(menu,owner):
    action=menu.addAction('')
    def refresh():action.setText('Modeli gizle' if visible(owner) else 'Modeli göster')
    refresh();menu.aboutToShow.connect(refresh)
    action.triggered.connect(lambda checked=False:set_visible(owner,not visible(owner)))
    return action
