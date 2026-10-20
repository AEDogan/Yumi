"""Native presentation components. No transport, model or device ownership."""
from PySide6.QtCore import Qt,QSize,QByteArray,QRectF
from PySide6.QtGui import QIcon,QPixmap,QPainter,QColor
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (QWidget,QHBoxLayout,QVBoxLayout,QGridLayout,QStackedWidget,
    QListWidget,QListWidgetItem,QPushButton,QToolButton,QButtonGroup,QSizePolicy,
    QFrame,QLabel,QScrollArea,QLayout,QLineEdit,QSizeGrip,QMenu)

PATHS={
 'chat':'<path d="M5 4h14a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H9l-6 3V6a2 2 0 0 1 2-2Z"/><path d="M7 9h10M7 13h7"/>',
 'model':'<circle cx="12" cy="8" r="4"/><path d="M4 21v-2a8 8 0 0 1 16 0v2"/>',
 'motion':'<circle cx="14" cy="4" r="2"/><path d="m8 9 5-2 3 5 5 1M13 7l-2 7-6 7m6-7 5 3 1 4M8 9l-4 5"/>',
 'home':'<path d="m3 11 9-8 9 8M5 10v11h14V10M10 21v-7h4v7"/>',
 'theme':'<circle cx="12" cy="12" r="9"/><path d="M12 3v18"/><path d="M12 5a7 7 0 0 1 0 14Z" fill="currentColor"/>',
 'settings':'<path d="M4 7h16M4 17h16"/><circle cx="8" cy="7" r="3"/><circle cx="16" cy="17" r="3"/>',
 'history':'<path d="M4 7v5h5M4 12a8 8 0 1 0 2-6M12 7v5l3 2"/>',
 'mic':'<rect x="9" y="3" width="6" height="12" rx="3"/><path d="M5 11v1a7 7 0 0 0 14 0v-1M12 19v3M8 22h8"/>',
 'send':'<path d="m3 3 19 9-19 9 4-9-4-9ZM7 12h15"/>',
 'stop':'<rect x="6" y="6" width="12" height="12" rx="2"/>',
 'close':'<path d="m6 6 12 12M18 6 6 18"/>',
 'minimize':'<path d="M5 12h14"/>',
 'plus':'<path d="M12 5v14M5 12h14"/>',
 'wave':'<path d="M7 12V7a1.5 1.5 0 0 1 3 0v4-7a1.5 1.5 0 0 1 3 0v7-6a1.5 1.5 0 0 1 3 0v7-3a1.5 1.5 0 0 1 3 0v6a7 7 0 0 1-13 3L3 13a1.5 1.5 0 0 1 2-2l2 1Z"/>',
}

def icon(name,color='#596a80',size=22):
    path=PATHS.get(name,PATHS['chat']).replace('currentColor',color)
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round">{path}</svg>'
    pixmap=QPixmap(size*2,size*2);pixmap.fill(Qt.GlobalColor.transparent);pixmap.setDevicePixelRatio(2.)
    painter=QPainter(pixmap);QSvgRenderer(QByteArray(svg.encode())).render(painter,QRectF(0,0,size,size));painter.end()
    return QIcon(pixmap)

class NavigationRail(QWidget):
    def __init__(self,actions,parent=None):
        super().__init__(parent);self.setObjectName('navigationRail');self.setFixedWidth(74)
        layout=QVBoxLayout(self);layout.setContentsMargins(7,14,7,12);layout.setSpacing(8)
        self.buttons={};self.group=QButtonGroup(self);self.group.setExclusive(True)
        for key,title,callback in actions:
            if key=='theme':layout.addStretch()
            button=QToolButton();button.setObjectName('navButton');button.setText(title);button.setAccessibleName(title)
            button.setToolTip(title);button.setCheckable(True);button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            button.setIconSize(QSize(23,23));button.setFixedSize(58,60);button.clicked.connect(callback)
            self.group.addButton(button);layout.addWidget(button);self.buttons[key]=button
        self.buttons['chat'].setChecked(True)
    def recolor(self,color):
        for key,button in self.buttons.items():button.setIcon(icon(key,color))
    def select(self,key):
        if key in self.buttons:self.buttons[key].setChecked(True)
    def compact(self,height):
        small=height<400;tiny=height<290
        self.layout().setContentsMargins(7,6 if small else 14,7,6 if small else 12)
        self.layout().setSpacing(2 if tiny else 4 if small else 8)
        for button in self.buttons.values():
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly if tiny else Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            button.setFixedSize(58,28 if tiny else 44 if small else 60)
            button.setIconSize(QSize(20 if small else 23,20 if small else 23))

class SectionTabs(QWidget):
    """QTabWidget-compatible section selection with readable horizontal labels."""
    def __init__(self,parent=None):
        super().__init__(parent);self.setObjectName('sectionTabs')
        layout=QHBoxLayout(self);layout.setContentsMargins(0,0,0,0);layout.setSpacing(18)
        self.list=QListWidget();self.list.setObjectName('settingsSections');self.list.setFixedWidth(114)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff);self.list.setWordWrap(True)
        self.list.setAccessibleName('Ayar bölümleri');self.stack=QStackedWidget()
        layout.addWidget(self.list);layout.addWidget(self.stack,1);self.list.currentRowChanged.connect(self.stack.setCurrentIndex)
    def addTab(self,widget,title):
        self.list.addItem(QListWidgetItem(title));index=self.stack.addWidget(widget)
        if index==0:self.list.setCurrentRow(0)
        return index
    def setCurrentIndex(self,index):self.list.setCurrentRow(index)
    def currentIndex(self):return self.stack.currentIndex()
    def count(self):return self.stack.count()
    def widget(self,index):return self.stack.widget(index)

class ThemePicker(QWidget):
    def __init__(self,combo,parent=None):
        super().__init__(parent);self.combo=combo;self.buttons={};self.group=QButtonGroup(self);self.group.setExclusive(True);layout=QGridLayout(self)
        layout.setContentsMargins(0,0,0,0);layout.setSpacing(8)
        from themes import PALETTES
        for index in range(combo.count()):
            key=combo.itemData(index);bg,text,muted,accent,assistant,user=PALETTES[key]
            button=QPushButton(combo.itemText(index));button.setObjectName('themeChoice');button.setCheckable(True)
            button.setAccessibleName(combo.itemText(index)+' teması');button.setMinimumHeight(76)
            self.group.addButton(button)
            pix=QPixmap(76,36);pix.fill(QColor(bg));p=QPainter(pix);p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.fillRect(4,4,16,28,QColor(user));p.fillRect(25,8,40,7,QColor(assistant));p.fillRect(36,21,34,7,QColor(accent));p.end()
            button.setIcon(QIcon(pix));button.setIconSize(QSize(76,36))
            button.clicked.connect(lambda checked=False,index=index:combo.setCurrentIndex(index))
            layout.addWidget(button,index//2,index%2);self.buttons[key]=button
        combo.currentIndexChanged.connect(self.sync);self.sync()
    def sync(self,*args):
        for key,button in self.buttons.items():button.setChecked(key==self.combo.currentData())

def build_window(w):
    """Build controls around the existing action handlers and state fields."""
    from avatar import AvatarView
    from page_stack import PageStack
    root=QWidget();root.setObjectName('root');w.setCentralWidget(root)
    outer=QVBoxLayout(root);outer.setContentsMargins(1,1,1,1);outer.setSpacing(0)
    header=QFrame();header.setObjectName('header');header.setFixedHeight(61);header.installEventFilter(w)
    row=QHBoxLayout(header);row.setContentsMargins(21,8,15,5);row.setSpacing(13)
    title=QLabel('yumi');title.setObjectName('brand');title.installEventFilter(w);row.addWidget(title)
    description=QLabel('Masaüstü asistanın');description.setObjectName('brandDescription');w.brand_description=description;row.addWidget(description);row.addStretch()
    from model_visibility import visible,set_visible
    w.model_visibility_button=QPushButton('Modeli gizle' if visible(w) else 'Modeli göster')
    w.model_visibility_button.setObjectName('secondaryButton');w.model_visibility_button.setMinimumHeight(32)
    w.model_visibility_button.setAccessibleName('Modeli gizle veya göster')
    w.model_visibility_button.clicked.connect(lambda:set_visible(w,not visible(w)));row.addWidget(w.model_visibility_button)
    w.header_buttons={}
    for key,tip,callback in [('minimize','Pencereyi gizle',w.hide),('close','Sistem tepsisine küçült',w.hide)]:
        button=QPushButton();button.setObjectName('iconButton');button.setFixedSize(34,34);button.setToolTip(tip);button.setAccessibleName(tip);button.clicked.connect(callback);row.addWidget(button);w.header_buttons[key]=button
    outer.addWidget(header)
    stage=QFrame();stage.setObjectName('stage');stage.setFixedHeight(31)
    row=QHBoxLayout(stage);row.setContentsMargins(22,0,18,7)
    w.avatar=AvatarView(stage);w.avatar.skin=w.settings['skin'];w.avatar.hide();w.avatar.timer.stop()
    w.bubble=QLabel('',stage);w.bubble.hide()
    w.status=QLabel('Hazır');w.status.setObjectName('status');w.status.setMinimumWidth(0);w.status.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred);row.addWidget(w.status,1)
    outer.addWidget(stage);w.stage=stage
    w.web_recovery=QWidget();recovery=QVBoxLayout(w.web_recovery)
    recovery.setContentsMargins(22,6,18,8)
    w.web_recovery_text=QLabel('Web bağlantısı hazır değil. Sohbetin korunuyor.');w.web_recovery_text.setWordWrap(True)
    w.web_recovery_text.setMinimumWidth(0);recovery.addWidget(w.web_recovery_text)
    actions=QGridLayout();actions.setColumnStretch(0,1);actions.setColumnStretch(1,1);actions.setColumnStretch(2,1);recovery.addLayout(actions)
    w.web_retry_button=QPushButton('Yeniden bağlan');w.web_retry_button.clicked.connect(w._retry_browser);actions.addWidget(w.web_retry_button,0,0)
    for text,finish in [('Site doğrulamasını aç',False),('Doğrulamayı tamamladım',True)]:
        button=QPushButton('Doğruladım' if finish else 'Siteyi aç');button.setAccessibleName(text);button.setToolTip(text);button.clicked.connect(lambda _=False,finish=finish:w._browser_login(w.settings['provider'],finish));actions.addWidget(button,0,2 if finish else 1)
    outer.addWidget(w.web_recovery);w.web_recovery.hide()
    w.native_recovery=QWidget();recovery=QHBoxLayout(w.native_recovery)
    recovery.setContentsMargins(22,6,18,8)
    w.native_recovery_text=QLabel();w.native_recovery_text.setWordWrap(True)
    w.native_recovery_text.setMinimumWidth(0);recovery.addWidget(w.native_recovery_text,1)
    w.native_reconnect_button=QPushButton('Sese yeniden bağlan')
    w.native_reconnect_button.clicked.connect(w._reconnect_native);recovery.addWidget(w.native_reconnect_button)
    outer.addWidget(w.native_recovery);w.native_recovery.hide()
    body=QHBoxLayout();body.setContentsMargins(0,0,0,0);body.setSpacing(0);outer.addLayout(body,1)
    w.navigation=NavigationRail([
        ('chat','Sohbet',w._nav_chat),('model','Model',lambda:w._nav_settings(2,'model')),
        ('motion','Hareket',lambda:w._route_page('motion',w._activities)),
        ('home','Ev',lambda:w._route_page('home',w._open_smart_home)),
        ('theme','Tema',lambda:w._nav_settings(4,'theme')),
        ('settings','Ayarlar',lambda:w._nav_settings(0,'settings'))])
    w.navigation.setSizePolicy(QSizePolicy.Policy.Fixed,QSizePolicy.Policy.Ignored)
    body.addWidget(w.navigation)
    w.pages=PageStack(reduced_motion=w.settings.get('reduce_motion',False));w.pages.pageClosed.connect(w._page_closed);body.addWidget(w.pages,1)
    w.panel=QFrame();w.panel.setObjectName('panel');w.pages.addWidget(w.panel)
    layout=QVBoxLayout(w.panel);layout.setContentsMargins(18,17,18,10);layout.setSpacing(14)
    top=QHBoxLayout();top.setSpacing(10)
    w.chat_toggle=QPushButton('Geçmiş');w.chat_toggle.setObjectName('chatToggle');w.chat_toggle.setCheckable(True);w.chat_toggle.setChecked(True);w.chat_toggle.setToolTip('Sohbet geçmişini göster / gizle');top.addWidget(w.chat_toggle)
    name=QLabel('Sohbet');name.setObjectName('heading');top.addWidget(name);top.addStretch()
    w.badge=QLabel('');w.badge.setObjectName('badge');w.badge.hide()
    w.wave_button=QPushButton();w.wave_button.setObjectName('stageButton');w.wave_button.setFixedSize(34,34);w.wave_button.setAccessibleName('El salla');w.wave_button.setToolTip('El salla');w.wave_button.clicked.connect(w._wave);top.addWidget(w.wave_button)
    layout.addLayout(top)
    content=QHBoxLayout();content.setSpacing(18)
    w.chat_sidebar=QFrame();w.chat_sidebar.setObjectName('chatSidebar');w.chat_sidebar.setFixedWidth(164)
    sidebar=QVBoxLayout(w.chat_sidebar);sidebar.setContentsMargins(0,0,0,0);sidebar.setSpacing(9)
    w.new_chat_button=QPushButton('Yeni sohbet');w.new_chat_button.setObjectName('newChat');w.new_chat_button.clicked.connect(w._new_chat);sidebar.addWidget(w.new_chat_button)
    w.chat_list=QListWidget();w.chat_list.setObjectName('chatList');w.chat_list.setAccessibleName('Sohbet geçmişi')
    w.chat_list.setWordWrap(True);w.chat_list.itemClicked.connect(w._select_chat_item);w.chat_list.itemActivated.connect(w._select_chat_item)
    w.chat_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu);w.chat_list.customContextMenuRequested.connect(w._chat_context_menu);sidebar.addWidget(w.chat_list,1)
    w.delete_chat_button=QPushButton('Sohbeti sil');w.delete_chat_button.setObjectName('deleteChat');w.delete_chat_button.setAccessibleName('Seçili sohbeti sil');w.delete_chat_button.clicked.connect(lambda:w._delete_chat());sidebar.addWidget(w.delete_chat_button)
    retention=QLabel('Son mesajdan 5 gün sonra silinir');retention.setObjectName('sidebarCaption');retention.setWordWrap(True);sidebar.addWidget(retention)
    w.chat_toggle.toggled.connect(lambda checked:w._layout_stage());content.addWidget(w.chat_sidebar)
    w.chat_messages=QWidget();w.chat_messages.setMinimumWidth(0)
    messages=QVBoxLayout(w.chat_messages);messages.setContentsMargins(0,0,0,0);messages.setSpacing(12);content.addWidget(w.chat_messages,1);layout.addLayout(content,1)
    w.scroll=QScrollArea();w.scroll.setWidgetResizable(True);w.scroll.setFrameShape(QFrame.Shape.NoFrame);w.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff);w.scroll.viewport().setAutoFillBackground(False)
    w.message_box=QWidget();w.message_box.setObjectName('messageContent');w.message_layout=QVBoxLayout(w.message_box)
    w.message_layout.setContentsMargins(0,8,0,4);w.message_layout.setSpacing(12);w.message_layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize);w.message_layout.addStretch();w.message_labels=[]
    w.scroll.setWidget(w.message_box);w.scroll.viewport().installEventFilter(w);messages.addWidget(w.scroll,1)
    w.jump_button=QPushButton('Son mesaja dön',w.scroll.viewport());w.jump_button.setObjectName('jumpButton');w.jump_button.setFixedSize(132,34);w.jump_button.clicked.connect(w._jump_latest);w.jump_button.hide()
    w.scroll.verticalScrollBar().valueChanged.connect(w._update_jump);w.scroll.verticalScrollBar().rangeChanged.connect(w._update_jump)
    w._load_chat_history()
    composer_frame=QFrame();composer_frame.setObjectName('composer');composer=QHBoxLayout(composer_frame);composer.setContentsMargins(7,5,7,5);composer.setSpacing(7)
    w.mic_button=QPushButton();w.mic_button.setObjectName('micButton');w.mic_button.setCheckable(True);w.mic_button.setFixedSize(42,42);w.mic_button.setAccessibleName('Sesli sohbeti başlat veya durdur');w.mic_button.setToolTip('Sesli sohbeti başlat / durdur');w.mic_button.clicked.connect(w._mic);composer.addWidget(w.mic_button)
    w.input=QLineEdit();w.input.setMinimumWidth(40);w.input.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Fixed);w.input.setObjectName('messageInput');w.input.setPlaceholderText('Yumi’ye bir şey yaz…');w.input.setAccessibleName('Mesajın');w.input.returnPressed.connect(w._send);composer.addWidget(w.input,1)
    w.send_button=QPushButton();w.send_button.setObjectName('sendButton');w.send_button.setFixedSize(42,42);w.send_button.setToolTip('Mesajı gönder');w.send_button.setAccessibleName('Mesajı gönder');w.send_button.clicked.connect(w._send);composer.addWidget(w.send_button)
    w.stop_reply_button=QPushButton('Durdur');w.stop_reply_button.hide();w.stop_reply_button.clicked.connect(w._cancel_reply);composer.addWidget(w.stop_reply_button)
    messages.addWidget(composer_frame)
    foot=QHBoxLayout();w.voice_hint=QLabel('Sesli sohbet için mikrofona dokun');w.voice_hint.setObjectName('footer');w.voice_hint.setWordWrap(True);w.voice_hint.setMinimumWidth(0);foot.addWidget(w.voice_hint,1)
    grip=QSizeGrip(w);grip.setFixedSize(17,17);foot.addWidget(grip);messages.addLayout(foot)
    w.apply_theme()
