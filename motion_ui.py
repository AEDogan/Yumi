from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog,QVBoxLayout,QComboBox,QLabel,QPushButton,QFileDialog
from vrma import library,import_clip

class MotionDialog(QDialog):
    def __init__(self,owner):
        super().__init__(owner);self.owner=owner;self.setWindowTitle('Yumi · VRMA animasyonları');self.resize(440,280)
        self.setWindowFlags(Qt.WindowType.Widget);self.setModal(False)
        layout=QVBoxLayout(self);back=QPushButton('Geri');back.clicked.connect(self.reject);layout.addWidget(back);self.combo=QComboBox();layout.addWidget(self.combo)
        note=QLabel('VRoid Photo Booth ile aynı .vrma biçimindeki hareket dosyalarını ekle. VRM karaktere uyarlanır. Yumi jestleri ücretsiz Quaternius konuşma klibinden türetilmiştir.');note.setWordWrap(True);layout.addWidget(note)
        add=QPushButton('VRMA dosyası ekle');play=QPushButton('Seçili hareketi oynat');stop=QPushButton('Durdur')
        for button in (add,play,stop):layout.addWidget(button)
        self.status=QLabel();self.status.setWordWrap(True);layout.addWidget(self.status)
        add.clicked.connect(self.add);play.clicked.connect(self.play);stop.clicked.connect(self.stop);self.fill()
    def fill(self):
        self.combo.clear()
        names={'VRMA_01':'VRoid · Tam vücut göster','VRMA_02':'VRoid · Selamlaşma','VRMA_03':'VRoid · Zafer işareti','VRMA_04':'VRoid · Atış','VRMA_05':'VRoid · Dönüş','VRMA_06':'VRoid · Model pozu','VRMA_07':'VRoid · Çömelme'}
        names.update({'Yumi-Gesture-'+key:'Yumi · '+label for key,label in {'greeting':'Selamlama','happy':'Sevinç','sad':'Üzüntü','sorry':'Özür','thanks':'Teşekkür','warning':'Uyarı / ciddi ifade','uncertain':'Kararsızlık','encourage':'Cesaretlendirme','agree':'Onay','disagree':'Ret','question':'Soru','explain':'Açıklama'}.items()})
        for path in library():self.combo.addItem(names.get(path.stem,'PIXIV · kısa retarget testi' if path.stem=='pixiv-test' else path.stem.replace('quaternius-','Quaternius · ')),str(path))
    def add(self):
        path,_=QFileDialog.getOpenFileName(self,'VRMA animasyon seç','','VRM Animation (*.vrma)')
        if not path:return
        try:
            dest=import_clip(path);self.fill();self.combo.setCurrentIndex(self.combo.findData(str(dest)))
        except Exception as error:self.status.setText(str(error))
    def play(self):
        if not self.combo.currentData():return
        try:self.owner._play_motion(self.combo.currentData());self.status.setText('Oynatılıyor · '+self.combo.currentText())
        except Exception as error:self.status.setText(str(error))
    def stop(self):
        import time
        self.owner.manual_pose='idle';self.owner.manual_pose_end=time.perf_counter()+3
