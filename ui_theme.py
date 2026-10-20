"""Shared native presentation tokens. Existing saved theme IDs remain valid."""
from pathlib import Path
PALETTES={
 'pearl':('#eff6f7','#183b44','#526e78','#277d8c','#ffffff','#ddf0f1'),
 'night':('#242427','#f5f5f7','#b5b5c0','#c4b3eb','#303035','#46434f'),
 'nexus':('#102633','#eaf6fb','#a1bbc9','#6dd3e8','#193642','#244a59'),
 'ios':('#f4f6f9','#1b293a','#59697d','#4168d9','#ffffff','#e8eefb'),
 'ios-dark':('#111820','#f0f4f8','#a4b2c4','#91b0ff','#1a2532','#30435d'),
 'lavender':('#f5f2fa','#332943','#746481','#8564bb','#ffffff','#eee5f8')}
THEMES=[('İnci','ios'),('Gece','ios-dark'),('Okyanus','nexus'),('Buz','pearl'),('Grafit','night'),('Lavanta','lavender')]

def stylesheet(theme='pearl',opacity=94):
 bg,text,muted,accent,panel,user=PALETTES.get(theme,PALETTES['pearl'])
 arrow=(Path(__file__).resolve().parent/'assets/chevron-down.svg').as_posix()
 def surface(color,alpha):
  return 'rgba(%d,%d,%d,%d)'%(*[int(color[i:i+2],16) for i in (1,3,5)],max(0,min(255,round(alpha*2.55))))
 return f"""
 QWidget{{font-family:'Segoe UI Variable Text','Segoe UI',sans-serif;font-size:14px;color:{text}}}
 QMainWindow{{background:transparent}} #root{{background:{surface(bg,opacity)};border:1px solid {surface(muted,24)};border-radius:18px}}
 #header,#stage{{background:transparent;border:0}} #brand{{font-size:25px;font-weight:700;color:{text}}}
 #brandDescription,#status,#footer,#sidebarCaption{{color:{muted};font-size:12px}} #status{{padding:0 4px}}
 #navigationRail{{background:transparent;border:0;border-right:1px solid {surface(muted,16)}}}
 QToolButton#navButton{{background:transparent;border:1px solid transparent;border-radius:12px;color:{muted};font-size:11px;padding:4px}}
 QToolButton#navButton:hover{{background:{surface(accent,10)};color:{text}}}
 QToolButton#navButton:checked{{background:{surface(accent,14)};color:{text};border-color:{surface(accent,18)}}}
 QToolButton#navButton:focus{{border:1px solid {accent}}}
 #panel{{background:{surface(panel,94)};border:0;border-top-left-radius:16px}}
 #heading{{font-size:21px;font-weight:600}} #badge{{color:{muted};font-size:12px;background:transparent}}
 QPushButton{{background:{surface(bg,92)};border:1px solid {surface(muted,24)};border-radius:9px;padding:8px 12px;min-height:22px}}
 QPushButton:hover{{background:{surface(accent,12)};border-color:{surface(accent,40)}}}
 QPushButton:pressed{{background:{surface(accent,20)}}}
 QPushButton:focus,QToolButton:focus,QLineEdit:focus,QComboBox:focus{{border:1px solid {accent}}}
 QPushButton:disabled,QToolButton:disabled{{color:{surface(muted,60)};border-color:{surface(muted,12)}}}
 #iconButton,#stageButton,#micButton{{background:transparent;border:1px solid transparent;border-radius:10px;min-height:0;padding:0}}
 #iconButton:hover,#stageButton:hover,#micButton:hover{{background:{surface(accent,12)}}}
 #micButton:checked{{background:{surface(accent,20)};border-color:{accent}}}
 #chatSidebar{{background:transparent;border:0}} #chatList{{background:transparent;border:0;outline:0;padding:3px 0}}
 #chatList::item{{padding:12px 9px;border:1px solid transparent;border-radius:9px;margin:2px 0}}
 #chatList::item:selected{{background:{surface(accent,12)};color:{text}}} #chatList::item:focus{{border:1px solid {accent}}}
 #chatList::item:hover{{background:{surface(accent,8)}}}
 #newChat{{background:{surface(accent,12)};border-color:transparent;color:{text};font-weight:600}}
 #chatToggle{{min-height:0;padding:6px 8px;background:transparent;border:1px solid {surface(muted,20)}}}
 #chatToggle:checked{{background:{surface(accent,9)}}}
 #deleteChat{{background:transparent;border-color:transparent;color:{muted};font-size:12px}}
 #deleteChat:hover{{background:#fce8ea;color:#9a2638}}
 QScrollArea,QScrollArea::viewport,#settingsContent,#messageContent{{background:transparent;border:0}}
 QLabel[role="assistant"]{{background:{surface(bg,96)};color:{text};border-radius:14px;padding:14px}}
 QLabel[role="user"]{{background:{surface(user,98)};color:{text};border-radius:14px;padding:14px}}
 QLabel[role="error"]{{background:#fce8ea;color:#922a3b;border-radius:12px;padding:14px}}
 #composer{{background:{surface(bg,96)};border:1px solid {surface(muted,28)};border-radius:14px}}
 QLineEdit{{background:{surface(panel,96)};border:1px solid {surface(muted,35)};padding:11px;border-radius:9px;selection-background-color:{accent}}}
 #messageInput{{background:transparent;border:0;padding:10px 4px;min-height:22px}}
 #sendButton,#jumpButton,#primaryButton{{background:{accent};color:{bg};border:1px solid transparent;font-weight:600}}
 #sendButton{{padding:0;min-height:0;border-radius:10px}}
 #sendButton:hover,#primaryButton:hover{{border:1px solid {text}}}
 #jumpButton{{border-radius:9px;padding:4px;min-height:0}}
 #footer{{font-size:11px;padding-top:3px}}
 QDialog,#settingsPage{{background:{bg}}}
 #settingsSections{{background:transparent;border:0;outline:0}}
 #settingsSections::item{{padding:13px 8px;border:1px solid transparent;border-radius:9px;margin:2px 0}}
 #settingsSections::item:selected{{background:{surface(accent,14)};color:{text}}}
 #settingsSections::item:focus{{border-color:{accent}}}
 #themeChoice{{background:{surface(panel,98)};border:1px solid {surface(muted,25)};padding:7px;min-height:60px;font-size:12px}}
 #themeChoice:checked{{border:2px solid {accent};background:{surface(accent,8)}}}
 QGroupBox{{background:{surface(panel,65)};border:1px solid {surface(muted,20)};border-radius:12px;margin-top:18px;padding:18px 12px 12px}}
 QGroupBox::title{{subcontrol-origin:margin;left:12px;font-weight:600}}
 QComboBox{{background:{surface(panel,98)};border:1px solid {surface(muted,35)};border-radius:9px;padding:9px 30px 9px 10px;min-height:22px}}
 QComboBox::drop-down{{subcontrol-origin:padding;subcontrol-position:top right;width:28px;border:0}}
 QComboBox::down-arrow{{image:url({arrow});width:12px;height:8px;margin-right:7px}}
 QComboBox QAbstractItemView{{background:{panel};color:{text};selection-background-color:{user};selection-color:{text};padding:5px}}
 QCheckBox{{spacing:9px;min-height:32px}} QCheckBox::indicator{{width:18px;height:18px}}
 QTabWidget::pane{{border:0}} QTabBar::tab{{padding:9px;background:transparent;color:{muted}}}
 QTabBar::tab:selected{{background:{surface(accent,14)};color:{text}}}
 QScrollBar:vertical{{background:transparent;width:6px;margin:2px}}
 QScrollBar::handle:vertical{{background:{surface(muted,40)};border-radius:3px;min-height:30px}}
 QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{{height:0}}
 QScrollBar::add-page:vertical,QScrollBar::sub-page:vertical{{background:transparent}}
 QMenu{{background:{panel};border:1px solid {surface(muted,25)};border-radius:10px;padding:6px}}
 QMenu::item{{padding:9px 18px;border-radius:6px}} QMenu::item:selected{{background:{surface(accent,14)}}}
 QSlider::groove:horizontal{{height:5px;background:{surface(muted,22)};border-radius:2px}}
 QSlider::handle:horizontal{{width:18px;margin:-7px 0;background:{accent};border-radius:9px}}
 """
