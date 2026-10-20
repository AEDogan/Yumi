"""Readable native glass themes. Alpha applies to surfaces, never to text."""
from pathlib import Path
PALETTES={
 'pearl':('#f6f7fb','#1f2937','#6b7280','#4f68f2','#e8ecff','#eef2f7'),
 'night':('#171c28','#eef2ff','#a4aec5','#879bff','#303b5a','#283345'),
 'nexus':('#0c1929','#e2f1ff','#7ea5c7','#38bdf8','#13293f','#17385c'),
 'ios':('#f2f2f7','#000000','#6c6c70','#007aff','#ffffff','#e5e5ea'),
 'ios-dark':('#000000','#ffffff','#8e8e93','#0a84ff','#1c1c1e','#2c2c2e'),
 'lavender':('#f6f1fb','#352942','#887490','#9b6fcd','#eadff6','#e4f1eb')}
def _legacy_stylesheet(theme='pearl',opacity=94):
 bg,text,muted,accent,assistant,user=PALETTES.get(theme,PALETTES['pearl'])
 arrow=(Path(__file__).resolve().parent/'assets/chevron-down.svg').as_posix()
 def surface(color,alpha):
  return 'rgba(%d,%d,%d,%d)'%(*[int(color[i:i+2],16) for i in (1,3,5)],max(0,min(255,round(alpha*2.55))))
 return f"""
 QMainWindow{{background:transparent}} QWidget{{font-family:-apple-system,BlinkMacSystemFont,'SF Pro Text','Segoe UI Variable Text','Segoe UI',sans-serif;font-size:13px;color:{text}}}
 #root{{background:{surface(bg,opacity)};border:1px solid {surface(muted,22)};border-radius:20px}}
 #header,#stage,#panel{{background:transparent;border:0}} #brand{{font-size:12px;font-weight:600;color:{accent}}}
 #iconButton,#stageButton,#micButton{{border:0;border-radius:10px;background:{surface(muted,12)};color:{text}}}
 QPushButton:hover{{background:{surface(accent,28)}}} #heading{{font-size:20px;font-weight:600}} #status{{color:{muted};font-size:11px}}
 #badge{{background:{surface(accent,12)};color:{accent};padding:6px;border-radius:10px;font-size:10px}}
 #chatSidebar{{background:transparent;border:0}} #chatList{{background:{surface(assistant,65)};border:1px solid {surface(muted,18)};border-radius:10px;outline:0}}
 #chatList::item{{padding:9px 5px;border-radius:7px}} #chatList::item:selected{{background:{surface(accent,16)};color:{text}}} #chatList::item:focus{{border:1px solid {accent}}}
 #chatToggle,#newChat{{background:{surface(assistant,85)};border:1px solid {surface(muted,22)};border-radius:8px;padding:7px}} #chatToggle:checked{{background:{surface(accent,15)};color:{accent}}}
 QScrollArea,QScrollArea::viewport,#settingsContent,#messageContent{{background:transparent;border:0}}
 QLabel[role="assistant"]{{background:{surface(assistant,90)};color:{text};border-radius:15px;padding:12px}}
 QLabel[role="user"]{{background:{surface(user,92)};color:{text};border-radius:15px;padding:12px}}
 QLabel[role="error"]{{background:#ffe5e5;color:#933333;border-radius:15px;padding:12px}}
 QLineEdit{{background:{surface(muted,10)};border:1px solid {surface(muted,25)};padding:10px;border-radius:12px;selection-background-color:{accent}}}
 #sendButton,#jumpButton{{background:{accent};color:white;border:0;border-radius:11px}} #footer{{font-size:10px;color:{muted}}}
 QDialog{{background:{bg}}} QGroupBox{{border:1px solid {surface(muted,25)};border-radius:12px;margin-top:16px;padding:14px 8px 8px}} QGroupBox::title{{subcontrol-origin:margin;left:12px}}
 QDialog QPushButton{{background:{surface(accent,16)};border:0;border-radius:9px;padding:9px;color:{text}}}
 QComboBox{{background:{surface(assistant,88)};border:1px solid {surface(muted,55)};border-radius:9px;padding:8px 32px 8px 10px;min-height:22px}}
 QComboBox::drop-down{{subcontrol-origin:padding;subcontrol-position:top right;width:28px;border-left:1px solid {surface(muted,30)}}}
 QComboBox::down-arrow{{image:url({arrow});width:12px;height:8px;margin-right:7px}}
 QComboBox QAbstractItemView{{background:{bg};color:{text};selection-background-color:{accent}}}
 QTabWidget::pane{{border:0}} QTabBar::tab{{background:transparent;padding:9px 8px;color:{muted};border-radius:8px}} QTabBar::tab:selected{{background:{surface(accent,16)};color:{accent}}}
 QScrollBar:vertical{{background:transparent;width:6px;margin:2px}} QScrollBar::handle:vertical{{background:{surface(muted,42)};border-radius:3px;min-height:30px}}
 QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{{height:0}} QScrollBar::add-page:vertical,QScrollBar::sub-page:vertical{{background:transparent}}
 QMenu{{background:{bg};border:1px solid {surface(muted,25)};padding:6px}} QMenu::item:selected{{background:{surface(accent,25)}}}
 QSlider::groove:horizontal{{height:5px;background:{surface(muted,25)};border-radius:2px}} QSlider::handle:horizontal{{width:16px;margin:-6px 0;background:{accent};border-radius:8px}}
 """

from ui_theme import PALETTES,THEMES,stylesheet
