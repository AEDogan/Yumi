"""One predictable place for existing daily, music and motion-file actions."""
from PySide6.QtCore import Qt,QTimer
from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QGridLayout,QLabel,QPushButton,QGroupBox,QComboBox,QCheckBox

class ActivitiesDialog(QDialog):
    def __init__(self,owner):
        super().__init__(owner);self.owner=owner;self.setWindowFlags(Qt.WindowType.Widget);self.setModal(False)
        layout=QVBoxLayout(self);layout.setContentsMargins(22,18,22,18);layout.setSpacing(18)
        header=QHBoxLayout();title=QLabel('Hareket ve senaryolar');title.setObjectName('heading');header.addWidget(title,1)
        back=QPushButton('Sohbete dön');back.clicked.connect(self.reject);header.addWidget(back);layout.addLayout(header)
        note=QLabel('Günlük hareketleri başlat, müzik tepkisini ayarla veya kendi animasyonunu seç.');note.setWordWrap(True);layout.addWidget(note)
        daily=QGroupBox('Günlük senaryolar');grid=QGridLayout(daily)
        commands=[('Kitap oku','kitap oku'),('Bilgisayar','bilgisayara otur'),('Film izle','film izle'),('Kahve yap','kahve yap'),('Pencereden bak','pencereden bak'),('Dinlen','dinlen'),('Toplantı','toplantıya katıl'),('Ayağa kalk','ayağa kalk')]
        self.action_buttons={}
        for index,(title,command) in enumerate(commands):
            button=QPushButton(title);button.clicked.connect(lambda checked=False,command=command:self.run(command));grid.addWidget(button,index//2,index%2);self.action_buttons[command]=button
        layout.addWidget(daily)
        music=QGroupBox('Müzik');box=QVBoxLayout(music);self.automatic=QCheckBox('Müziği otomatik algıla');self.automatic.setChecked(owner.settings.get('music_auto',True));self.automatic.toggled.connect(lambda value:self.run('otomatik müzik tepkisini '+('aç' if value else 'kapat')));box.addWidget(self.automatic)
        self.genres=QComboBox();self.genres.addItem('Türü otomatik belirle','otomatik')
        from music_analysis import GENRES
        for key in GENRES:self.genres.addItem(key.title(),key)
        current=self.genres.findData(owner.settings.get('music_family','unknown'));self.genres.setCurrentIndex(max(0,current));self.genres.currentIndexChanged.connect(lambda _:self.run('müzik türü '+str(self.genres.currentData())));box.addWidget(self.genres)
        row=QHBoxLayout()
        for title,command in [('Dans et','dans et'),('Direk dansı','direk dansı yap'),('Durdur','dansı durdur')]:
            button=QPushButton(title);button.clicked.connect(lambda checked=False,command=command:self.run(command));row.addWidget(button);self.action_buttons[command]=button
        box.addLayout(row);layout.addWidget(music)
        files=QPushButton('Animasyon dosyaları');files.clicked.connect(lambda:QTimer.singleShot(0,owner._motion_library));layout.addWidget(files)
        self.status=QLabel('');self.status.setWordWrap(True);layout.addWidget(self.status);layout.addStretch()
    def run(self,command):
        from voice_actions import execute
        try:result=execute(self.owner,command)
        except Exception as error:result='Hareket başlatılamadı: '+str(error)
        if result:self.status.setText(result);self.owner.show_bubble(result)
