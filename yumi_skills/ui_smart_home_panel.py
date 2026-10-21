from typing import Any, Dict, List

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .engine import YumiSkillEngine


class _AsyncBridgeWorker(QThread):
    finished_signal = Signal(dict)

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            res = self.fn(*self.args, **self.kwargs)
            self.finished_signal.emit(res)
        except Exception as e:
            self.finished_signal.emit({"ok": False, "speech": str(e)})


class AssignDeviceDialog(QDialog):
    """Bir odaya cihaz atamak veya yeni cihaz eklemek için açılan pencere."""

    def __init__(self, room_name: str, engine: YumiSkillEngine, parent=None):
        super().__init__(parent)
        self.room_name = room_name
        self.engine = engine
        self.setWindowTitle(f"'{room_name}' Odasına Cihaz Ekle / Ata")
        self.setMinimumWidth(320)
        self.setStyleSheet("font-size: 13px;")

        layout = QVBoxLayout(self)
        lbl = QLabel(f"<b>{room_name}</b> odasına eklemek istediğiniz cihazı seçin:")
        layout.addWidget(lbl)

        self.device_combo = QComboBox()
        devices: Dict[str, Any] = self.engine.storage.get("smart_devices", {})
        self.unassigned_keys = []
        for k, dev in devices.items():
            curr_room = dev.get("room", "")
            if curr_room != room_name:
                room_info = f" (Şu an: {curr_room})" if curr_room else " (Atanmamış)"
                self.device_combo.addItem(f"{dev.get('name')} [{dev.get('device_type')}]{room_info}", k)
                self.unassigned_keys.append(k)

        if not self.unassigned_keys:
            self.device_combo.addItem("Eklenebilecek boşta cihaz bulunamadı", None)

        layout.addWidget(self.device_combo)

        btn_row = QHBoxLayout()
        ok_btn = QPushButton("Bu Odaya Ata")
        ok_btn.clicked.connect(self._on_assign)
        cancel_btn = QPushButton("İptal")
        cancel_btn.setObjectName("secondaryBtn")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(ok_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

    def _on_assign(self):
        dev_key = self.device_combo.currentData()
        if not dev_key:
            QMessageBox.information(self, "Bilgi", "Seçilecek atanabilir cihaz yok.")
            return
        self.engine.smart_home.assign_device_to_room(dev_key, self.room_name)
        self.accept()


class RoomAccordionItem(QWidget):
    """
    Tıklanınca açılıp kapanan (akordeon) tek bir oda başlığı bileşeni.
    Oda adının yanında '+' butonu ile odaya cihaz atanır, odadaki cihazlar altında listelenir.
    """

    device_action_signal = Signal(str, str, bool)  # action_type, device_name, is_on
    refresh_signal = Signal()

    def __init__(self, room_name: str, devices: List[Dict[str, Any]], engine: YumiSkillEngine, parent=None):
        super().__init__(parent)
        self.room_name = room_name
        self.devices = devices
        self.engine = engine
        self.is_expanded = True
        self._setup_ui()

    def _setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 4, 0, 4)
        self.layout.setSpacing(2)

        # Başlık Çubuğu
        header_widget = QWidget()
        header_widget.setStyleSheet(
            "background-color: rgba(120, 140, 180, 0.12); border: 1px solid rgba(120, 140, 180, 0.22); border-radius: 8px; padding: 4px;"
        )
        h_layout = QHBoxLayout(header_widget)
        h_layout.setContentsMargins(8, 4, 8, 4)

        self.toggle_btn = QPushButton(f"▼  {self.room_name} ({len(self.devices)} cihaz)")
        self.toggle_btn.setStyleSheet(
            "background: transparent; border: none; font-size: 13px; font-weight: bold; text-align: left;"
        )
        self.toggle_btn.clicked.connect(self.toggle_expand)
        h_layout.addWidget(self.toggle_btn, 1)

        # '+' Odaya Cihaz Ekle/Ata Butonu
        add_btn = QPushButton("+ Cihaz Ekle")
        add_btn.setStyleSheet(
            "background-color: #10b981; color: white; padding: 4px 10px; font-size: 11px; border-radius: 5px; font-weight: bold;"
        )
        add_btn.setToolTip(f"'{self.room_name}' odasına cihaz ata")
        add_btn.clicked.connect(self._on_add_device_click)
        h_layout.addWidget(add_btn)

        # Odayı Sil Butonu (Atanmamış hariç)
        if self.room_name != "Atanmamış Cihazlar":
            del_room_btn = QPushButton("✕")
            del_room_btn.setStyleSheet(
                "background-color: rgba(120, 140, 180, 0.2); padding: 4px 8px; font-size: 11px; border-radius: 5px;"
            )
            del_room_btn.setToolTip("Oda başlığını sil")
            del_room_btn.clicked.connect(self._on_delete_room_click)
            h_layout.addWidget(del_room_btn)

        self.layout.addWidget(header_widget)

        # Cihazlar Listesi İçerik Alanı
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(12, 4, 4, 8)
        self.content_layout.setSpacing(4)

        self._populate_devices()
        self.layout.addWidget(self.content_widget)

    def toggle_expand(self):
        self.is_expanded = not self.is_expanded
        self.content_widget.setVisible(self.is_expanded)
        arrow = "▼" if self.is_expanded else "►"
        self.toggle_btn.setText(f"{arrow}  {self.room_name} ({len(self.devices)} cihaz)")

    def _populate_devices(self):
        # Önceki elemanları temizle
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self.devices:
            empty_lbl = QLabel("Bu odada henüz atanmış cihaz yok. '+ Cihaz Ekle' butonuna basarak cihaz ekleyebilirsiniz.")
            empty_lbl.setStyleSheet("color: #6b7280; font-size: 12px; font-style: italic; padding: 6px;")
            self.content_layout.addWidget(empty_lbl)
            return

        for dev in self.devices:
            dev_card = QWidget()
            dev_card.setStyleSheet(
                "background-color: rgba(120, 140, 180, 0.08); border: 1px solid rgba(120, 140, 180, 0.16); border-radius: 6px; padding: 4px;"
            )
            d_layout = QHBoxLayout(dev_card)
            d_layout.setContentsMargins(8, 4, 8, 4)

            icon = "💡" if dev.get("device_type") == "light" else ("📺" if dev.get("device_type") == "tv" else ("🧹" if dev.get("device_type") == "vacuum" else "🔌"))
            dev_info = QLabel(f"<b>{icon} {dev.get('name')}</b> <font color='#6b7280'>({dev.get('protocol')})</font>")
            dev_info.setStyleSheet("font-size: 13px;")
            d_layout.addWidget(dev_info, 1)

            # Test Aç/Kapat Butonları
            on_btn = QPushButton("Aç")
            on_btn.setStyleSheet("background-color: #2563eb; color: white; padding: 3px 8px; font-size: 11px; border-radius: 4px;")
            on_btn.clicked.connect(lambda _, d=dev: self.device_action_signal.emit("test", d.get("name"), True))

            off_btn = QPushButton("Kapat")
            off_btn.setStyleSheet("background-color: #374151; color: white; padding: 3px 8px; font-size: 11px; border-radius: 4px;")
            off_btn.clicked.connect(lambda _, d=dev: self.device_action_signal.emit("test", d.get("name"), False))

            # Odadan Çıkar Butonu
            eject_btn = QPushButton("Odadan Çıkar")
            eject_btn.setStyleSheet("background-color: #4b5563; color: #d1d5db; padding: 3px 6px; font-size: 10px; border-radius: 4px;")
            eject_btn.clicked.connect(lambda _, d=dev: self._on_eject_device(d.get("name")))

            d_layout.addWidget(on_btn)
            d_layout.addWidget(off_btn)
            d_layout.addWidget(eject_btn)
            self.content_layout.addWidget(dev_card)

    def _on_add_device_click(self):
        dlg = AssignDeviceDialog(self.room_name, self.engine, self)
        if dlg.exec():
            self.refresh_signal.emit()

    def _on_eject_device(self, dev_name: str):
        self.engine.smart_home.assign_device_to_room(dev_name, "")
        self.refresh_signal.emit()

    def _on_delete_room_click(self):
        reply = QMessageBox.question(
            self,
            "Odayı Sil",
            f"'{self.room_name}' odasını silmek istediğinize emin misiniz? (Cihazlar silinmez, 'Atanmamış' bölümüne geçer)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.engine.smart_home.delete_room(self.room_name)
            self.refresh_signal.emit()


class SmartHomePanelWidget(QWidget):
    """
    Yumi'nin ana penceresine doğrudan gömülebilen
    Odalar (Açılır Başlıklar/Akordeon) ve Akıllı Ev Yönetim Paneli.
    """

    def __init__(self, engine: YumiSkillEngine | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        self.engine = engine or YumiSkillEngine()
        self._active_worker: _AsyncBridgeWorker | None = None
        self._setup_ui()
        self.refresh_all()

    def _setup_ui(self) -> None:
        self.setWindowTitle("Yumi · Akıllı Ev & Odalar")
        self.setMinimumWidth(320)
        self.setStyleSheet(
            """
            QTabWidget::pane { border: 1px solid rgba(120, 140, 180, 0.2); border-radius: 8px; background: transparent; }
            QTabBar::tab { background: rgba(120, 140, 180, 0.15); padding: 7px 12px; border-top-left-radius: 6px; border-top-right-radius: 6px; margin-right: 4px; }
            QTabBar::tab:selected { background: #3b82f6; color: #ffffff; font-weight: bold; }
            QGroupBox { border: 1px solid rgba(120, 140, 180, 0.22); border-radius: 8px; margin-top: 10px; padding-top: 12px; font-weight: bold; }
            QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; }
            QPushButton#secondaryBtn { background-color: rgba(120, 140, 180, 0.2); }
            QPushButton#secondaryBtn:hover { background-color: rgba(120, 140, 180, 0.3); }
            QPushButton#dangerBtn { background-color: #dc2626; color: white; }
            QScrollArea { border: none; background: transparent; }
            """
        )

        root_layout = QVBoxLayout(self)
        header_lbl = QLabel("Akıllı Ev Odaları & Cihaz Yönetimi")
        header_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff; margin-bottom: 2px;")
        sub_lbl = QLabel(
            "Cihazlarınızı odalara (Oturma Odası, Yatak Odası vb.) atayabilir, başlıkları açıp kapatarak "
            "cihazları kontrol edebilir veya yeni cihaz ekleyebilirsiniz."
        )
        sub_lbl.setWordWrap(True)
        sub_lbl.setStyleSheet("color: #9ca3af; font-size: 12px; margin-bottom: 6px;")
        root_layout.addWidget(header_lbl)
        root_layout.addWidget(sub_lbl)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_rooms_tab(), "1. Odalar & Cihazlar (Açılır Başlıklar)")
        self.tabs.addTab(self._build_bridges_tab(), "2. Marka Köprüsü Bağla (Tuya, Xiaomi, Hue, IKEA)")
        self.tabs.addTab(self._build_scan_and_manual_tab(), "3. Wi-Fi Tara & Manuel Ekle")
        root_layout.addWidget(self.tabs)

        self.status_lbl = QLabel("Hazır.")
        self.status_lbl.setStyleSheet("color: #60a5fa; font-size: 12px; padding: 4px;")
        root_layout.addWidget(self.status_lbl)

    def _build_rooms_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        # Yeni Oda Ekleme Üst Çubuğu
        top_bar = QHBoxLayout()
        self.new_room_input = QLineEdit()
        self.new_room_input.setPlaceholderText("Yeni oda adı yazın (Örn: Salon, Çocuk Odası, Balkon)...")
        add_room_btn = QPushButton("+ Yeni Oda Oluştur")
        add_room_btn.setStyleSheet("background-color: #3b82f6; font-weight: bold;")
        add_room_btn.clicked.connect(self._on_add_new_room)
        top_bar.addWidget(self.new_room_input, 2)
        top_bar.addWidget(add_room_btn, 1)
        layout.addLayout(top_bar)

        # Kaydırılabilir Açılır Oda Başlıkları (Akordeon Alanı)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.rooms_container = QWidget()
        self.rooms_layout = QVBoxLayout(self.rooms_container)
        self.rooms_layout.setContentsMargins(4, 4, 4, 4)
        self.rooms_layout.setSpacing(6)
        self.rooms_layout.addStretch()
        self.scroll_area.setWidget(self.rooms_container)
        layout.addWidget(self.scroll_area)

        return page

    def _build_bridges_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        bridge_group = QGroupBox("Telefondaki / Evdeki Marka Köprüsünden Tüm Cihazları Çek")
        form = QFormLayout(bridge_group)

        self.bridge_platform_combo = QComboBox()
        self.bridge_platform_combo.addItem("Tuya / Smart Life (Akıllı Priz, Başucu Lambası, Ampul)", "tuya")
        self.bridge_platform_combo.addItem("Xiaomi Mi Home / Roborock / Yeelight", "xiaomi")
        self.bridge_platform_combo.addItem("Philips Hue Bridge (Yerel Köprü - Tek Tuşla Eşleştir)", "hue")
        self.bridge_platform_combo.addItem("IKEA Home Smart (DIRIGERA / TRÅDFRI Hub)", "ikea")
        self.bridge_platform_combo.addItem("TP-Link Tapo / Kasa (Ampul & Prizler)", "tapo")
        self.bridge_platform_combo.addItem("Home Assistant (Evrensel Köprü - Tüm Markalar)", "home_assistant")
        self.bridge_platform_combo.currentIndexChanged.connect(self._on_bridge_platform_changed)

        self.bridge_user_input = QLineEdit()
        self.bridge_pass_input = QLineEdit()
        self.bridge_pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.bridge_region_input = QLineEdit("eu")

        self.lbl_user = QLabel("API Key / E-posta / Köprü IP:")
        self.lbl_pass = QLabel("API Secret / Şifre / Token:")
        self.help_bridge_lbl = QLabel()
        self.help_bridge_lbl.setWordWrap(True)
        self.help_bridge_lbl.setStyleSheet("color: #93c5fd; font-size: 12px; padding: 6px; background: #14161b; border-radius: 6px;")

        form.addRow("Marka / Uygulama Köprüsü:", self.bridge_platform_combo)
        form.addRow(self.lbl_user, self.bridge_user_input)
        form.addRow(self.lbl_pass, self.bridge_pass_input)
        form.addRow("Bölge Kodu (Xiaomi/Tuya):", self.bridge_region_input)
        form.addRow("Nasıl Bağlanır?", self.help_bridge_lbl)

        sync_btn = QPushButton("Köprüye Bağlan ve Cihazları İsimleriyle Yumi'ye Aktar")
        sync_btn.clicked.connect(self._on_sync_bridge)
        form.addRow("", sync_btn)

        layout.addWidget(bridge_group)
        tv_group = QGroupBox('Android / Google TV — TV ekranındaki kodla eşleştir')
        tv_form = QFormLayout(tv_group)
        self.tv_host = QLineEdit()
        self.tv_host.setPlaceholderText('TV IP adresi')
        self.tv_name = QLineEdit('Salon TV')
        self.tv_code = QLineEdit()
        self.tv_code.setMaxLength(6)
        tv_form.addRow('IP adresi:', self.tv_host)
        tv_form.addRow('Cihaz adı:', self.tv_name)
        tv_form.addRow('TV ekranındaki kod:', self.tv_code)
        begin = QPushButton('TV’de eşleştirme kodunu göster')
        finish = QPushButton('Kodu doğrula ve TV’yi kaydet')
        begin.clicked.connect(lambda: self._pair_tv(False))
        finish.clicked.connect(lambda: self._pair_tv(True))
        tv_form.addRow(begin)
        tv_form.addRow(finish)
        layout.addWidget(tv_group)
        layout.addStretch()
        self._on_bridge_platform_changed()
        return page

    def _build_scan_and_manual_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        # Wi-Fi Tarama
        scan_group = QGroupBox("Evdeki Wi-Fi Ağını Otomatik Tara (Akıllı TV, Yeelight, Philips Hue, UPnP)")
        s_layout = QVBoxLayout(scan_group)
        scan_btn = QPushButton("Wi-Fi Ağındaki Cihazları Şimdi Tara")
        scan_btn.clicked.connect(self._on_scan_wifi)
        self.scan_results_combo = QComboBox()
        self.scan_results_combo.setPlaceholderText("Tarama sonuçları burada listelenir...")
        s_layout.addWidget(scan_btn)
        s_layout.addWidget(self.scan_results_combo)
        layout.addWidget(scan_group)

        # Manuel Cihaz Ekleme Formu
        man_group = QGroupBox("Cihazı Özel İsimle Kaydet (Örn: Salon TV, Yatak Odası TV, Başucu Lambası)")
        form = QFormLayout(man_group)

        self.man_name = QLineEdit()
        self.man_name.setPlaceholderText("Örn: Başucu Lambası, Salon TV, Robot Süpürge")

        self.man_type = QComboBox()
        self.man_type.addItem("Işık / Lamba (Prizdeki lambalar dahil)", "light")
        self.man_type.addItem("Akıllı Televizyon (TV)", "tv")
        self.man_type.addItem("Robot Süpürge", "vacuum")
        self.man_type.addItem("Akıllı Priz", "plug")

        self.man_proto = QComboBox()
        for label, code in [
            ("Tuya / Smart Life", "tuya"),
            ("Akıllı TV (LG / Samsung / Android TV DIAL)", "dlna_tv"),
            ("Xiaomi Yeelight", "yeelight"),
            ("Xiaomi Mi Home / Roborock", "xiaomi"),
            ("Philips Hue", "hue"),
            ("IKEA DIRIGERA", "ikea_dirigera"),
            ("TP-Link Tapo / Kasa", "tapo"),
            ("Home Assistant", "home_assistant"),
        ]:
            self.man_proto.addItem(label, code)

        self.man_ip = QLineEdit()
        self.man_ip.setPlaceholderText("Örn: 192.168.1.45")

        self.man_room_combo = QComboBox()
        self.man_token = QLineEdit()
        self.man_token.setEchoMode(QLineEdit.EchoMode.Password)
        self.man_token.setPlaceholderText("Varsa Local Key / Token / TV MAC Adresi")
        self.man_id = QLineEdit()
        self.man_id.setPlaceholderText("Varsa Tuya Device ID veya Entity ID")

        self.scan_results_combo.currentIndexChanged.connect(self._on_scan_item_picked)

        save_man_btn = QPushButton("Cihazı Yumi'ye Kaydet")
        save_man_btn.clicked.connect(self._on_save_manual)

        form.addRow("Yumi'deki Sesli Komut Adı:", self.man_name)
        form.addRow("Cihaz Türü:", self.man_type)
        form.addRow("Marka / Protokol:", self.man_proto)
        form.addRow("Atanacak Oda:", self.man_room_combo)
        form.addRow("Yerel Wi-Fi IP Adresi:", self.man_ip)
        form.addRow("Token / Local Key / TV MAC:", self.man_token)
        form.addRow("Cihaz ID (Tuya / Hue / HA):", self.man_id)
        form.addRow("", save_man_btn)

        layout.addWidget(man_group)
        return page

    # --- YÖNETİM & GÜNCELLEME METOTLARI ---

    def refresh_all(self) -> None:
        """Odalar akordeonunu ve oda seçim listelerini günceller."""
        rooms: List[str] = self.engine.smart_home.get_rooms()
        devices: Dict[str, Any] = self.engine.storage.get("smart_devices", {})

        # Manuel ekleme sekmesindeki oda combo'sunu doldur
        self.man_room_combo.clear()
        self.man_room_combo.addItem("(Oda Atanmasın)", "")
        for r in rooms:
            self.man_room_combo.addItem(r, r)

        # Odalar Akordeonunu Yeniden İnşa Et
        while self.rooms_layout.count() > 1:
            item = self.rooms_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Cihazları odalarına göre grupla
        devices_by_room: Dict[str, List[Dict[str, Any]]] = {r: [] for r in rooms}
        unassigned_devices: List[Dict[str, Any]] = []

        for dev in devices.values():
            room = dev.get("room", "").strip()
            if room and room in devices_by_room:
                devices_by_room[room].append(dev)
            else:
                unassigned_devices.append(dev)

        # 1. Tanımlı Odalar
        for room_name in rooms:
            room_devs = devices_by_room[room_name]
            acc_item = RoomAccordionItem(room_name, room_devs, self.engine, self)
            acc_item.device_action_signal.connect(self._on_device_action)
            acc_item.refresh_signal.connect(self.refresh_all)
            self.rooms_layout.insertWidget(self.rooms_layout.count() - 1, acc_item)

        # 2. Atanmamış Cihazlar Bölümü (Varsa en altta göster)
        if unassigned_devices:
            acc_unassigned = RoomAccordionItem("Atanmamış Cihazlar", unassigned_devices, self.engine, self)
            acc_unassigned.device_action_signal.connect(self._on_device_action)
            acc_unassigned.refresh_signal.connect(self.refresh_all)
            self.rooms_layout.insertWidget(self.rooms_layout.count() - 1, acc_unassigned)

    def _on_add_new_room(self) -> None:
        name = self.new_room_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Uyarı", "Lütfen oluşturmak istediğiniz oda adını yazın.")
            return
        res = self.engine.smart_home.add_room(name)
        self.status_lbl.setText(res.get("speech", ""))
        self.new_room_input.clear()
        self.refresh_all()

    def _on_device_action(self, action_type: str, dev_name: str, turn_on: bool) -> None:
        self.status_lbl.setText(f"'{dev_name}' komutu gönderiliyor...")
        devices = self.engine.storage.get("smart_devices", {})
        dtype = "light"
        for d in devices.values():
            if d.get("name") == dev_name:
                dtype = d.get("device_type", "light")
                break

        if dtype == "vacuum":
            name,args='control_vacuum',{'action':'start' if turn_on else 'pause','device_name':dev_name}
        elif dtype == "tv":
            name,args='control_smart_tv',{'action':'power_on' if turn_on else 'power_off','device_name':dev_name}
        else:
            name,args='control_light_or_plug',{'device_name':dev_name,'state':'on' if turn_on else 'off'}
        self._start_worker(self.engine.execute_skill,self._on_worker_done,name,args)

    def _start_worker(self,fn,callback,*args):
        from PySide6.QtWidgets import QApplication
        if self._active_worker and self._active_worker.isRunning():
            self.status_lbl.setText('Önce devam eden cihaz işleminin bitmesini bekle.');return
        worker=_AsyncBridgeWorker(fn,*args);self._active_worker=worker
        app=QApplication.instance()
        if not hasattr(app,'_yumi_skill_workers'):app._yumi_skill_workers=[]
        app._yumi_skill_workers.append(worker)
        worker.finished_signal.connect(callback)
        def release():
            if self._active_worker is worker:self._active_worker=None
            if worker in app._yumi_skill_workers:app._yumi_skill_workers.remove(worker)
            worker.deleteLater()
        worker.finished.connect(release);worker.start()

    def _on_bridge_platform_changed(self) -> None:
        plat = self.bridge_platform_combo.currentData()
        hints = {
            "tuya": (
                "Tuya API Key:",
                "Tuya API Secret:",
                "Smart Life / Tuya uygulamasındaki cihazlarınızı ('Başucu Lambası' vb.) isimleriyle çeker.",
            ),
            "xiaomi": (
                "Xiaomi (Mi Home) E-posta/ID:",
                "Xiaomi Şifresi:",
                "Mi Home hesabınızdaki Robot Süpürge, Yeelight ve Xiaomi prizlerinizi otomatik çeker.",
            ),
            "hue": (
                "Philips Hue Bridge IP Adresi:",
                "Hue Username (Boş bırakılabilir):",
                "Hue kutusunun üzerindeki fiziksel tuşa basıp aşağıdaki 'Köprüye Bağlan' butonuna tıklayın.",
            ),
            "ikea": (
                "IKEA DIRIGERA Hub IP Adresi:",
                "IKEA Hub Token:",
                "IKEA Home Smart (DIRIGERA) hub üzerindeki tüm akıllı ampul ve prizleri oda isimleriyle çeker.",
            ),
            "tapo": (
                "TP-Link (Tapo/Kasa) E-posta:",
                "TP-Link Şifresi:",
                "Evdeki Wi-Fi ağını tarayıp tüm TP-Link Tapo ve Kasa ampul/prizlerini Tapo isimleriyle ekler.",
            ),
            "home_assistant": (
                "Home Assistant URL (192.168.1.x:8123):",
                "Uzun Ömürlü Erişim Token'ı:",
                "Home Assistant'a bağlı tüm TV, süpürge, Zigbee/Tuya/Hue cihazlarınızı tek tıkla Yumi'ye aktarır.",
            ),
        }
        u_lbl, p_lbl, desc = hints.get(plat, ("Kullanıcı / IP:", "Şifre / Token:", ""))
        self.lbl_user.setText(u_lbl)
        self.lbl_pass.setText(p_lbl)
        self.help_bridge_lbl.setText(desc)

    def _on_sync_bridge(self) -> None:
        plat = self.bridge_platform_combo.currentData()
        user_val = self.bridge_user_input.text().strip()
        pass_val = self.bridge_pass_input.text().strip()
        region_val = self.bridge_region_input.text().strip() or "eu"

        self.status_lbl.setText(f"{plat.upper()} köprüsüne bağlanılıyor...")
        self._start_worker(self.engine.smart_home.sync_cloud_bridge_devices,self._on_worker_done,plat,user_val,pass_val,region_val)

    def _pair_tv(self, finish):
        host = self.tv_host.text().strip()
        code = self.tv_code.text().strip() if finish else ''
        if not host or (finish and len(code) != 6):
            self.status_lbl.setText('TV IP adresini ve TV’de görünen altı haneli kodu gir.');return
        self.status_lbl.setText('TV ile eşleştiriliyor…')
        self._start_worker(self.engine.smart_home.pair_android_tv, self._on_worker_done, host, code, self.tv_name.text().strip() or 'Salon TV')

    def _on_scan_wifi(self) -> None:
        self.status_lbl.setText("Evdeki Wi-Fi ağı taranıyor...")
        self._start_worker(self.engine.smart_home.discover_wifi_devices,self._on_scan_done)

    def _on_scan_done(self, res: Dict[str, Any]) -> None:
        self.status_lbl.setText(res.get("speech", ""))
        self.scan_results_combo.clear()
        discovered = res.get("discovered", [])
        if not discovered:
            self.scan_results_combo.addItem("Açık yayın yapan cihaz bulunamadı", None)
            return
        self.scan_results_combo.addItem("-- Bulunan Cihazlardan Seçin --", None)
        for d in discovered:
            self.scan_results_combo.addItem(f"{d['info']} - IP: {d['ip']}", d)

    def _on_scan_item_picked(self) -> None:
        data = self.scan_results_combo.currentData()
        if not data:
            return
        self.man_ip.setText(data.get("ip", ""))
        info_low = data.get("info", "").lower()
        if "tv" in info_low or "webos" in info_low or "samsung" in info_low or "dlna" in info_low:
            self.man_type.setCurrentIndex(1)
            self.man_proto.setCurrentIndex(1)
        elif "yeelight" in info_low:
            self.man_type.setCurrentIndex(0)
            self.man_proto.setCurrentIndex(2)
        elif "hue" in info_low:
            self.man_type.setCurrentIndex(0)
            self.man_proto.setCurrentIndex(4)

    def _on_save_manual(self) -> None:
        name = self.man_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Eksik Bilgi", "Lütfen cihaza bir ad verin (Örn: Başucu Lambası, Salon TV).")
            return
        res = self.engine.smart_home.register_smart_device(
            name=name,
            device_type=self.man_type.currentData(),
            brand_or_protocol=self.man_proto.currentData(),
            ip_address=self.man_ip.text().strip(),
            token_or_key=self.man_token.text().strip(),
            entity_id=self.man_id.text().strip(),
            room=self.man_room_combo.currentData() or "",
        )
        self.status_lbl.setText(res.get("speech", ""))
        self.man_name.clear()
        self.refresh_all()
        self.tabs.setCurrentIndex(0)

    def _on_worker_done(self, res: Dict[str, Any]) -> None:
        self.status_lbl.setText(res.get("speech", ""))
        self.refresh_all()
        if res.get("ok"):
            self.tabs.setCurrentIndex(0)


class SmartHomeDialog(QDialog):
    """
    Yumi PageStack ile tam uyumlu, akordeon odalar ve akıllı cihaz yönetim sayfası.
    """

    def __init__(self, parent, engine: YumiSkillEngine | None = None):
        super().__init__(parent)
        self.owner = parent
        self.engine = engine or getattr(parent, "skill_engine", None) or YumiSkillEngine()
        self.setWindowTitle("Yumi · Akıllı Ev & Odalar")
        self.setWindowFlags(Qt.WindowType.Widget)
        self.setModal(False)
        self.setWindowFlag(Qt.WindowType.WindowMinimizeButtonHint, False)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 10, 12, 12)
        outer.setSpacing(8)

        # Üst Başlık ve Geri Dön Butonu
        title_bar = QHBoxLayout()
        header_title = QLabel("🏠  Akıllı Ev & Cihazlar")
        header_title.setObjectName("heading")
        header_title.setStyleSheet("font-size: 15px; font-weight: bold;")
        title_bar.addWidget(header_title)
        title_bar.addStretch()

        back = QPushButton("Sohbete dön")
        back.setObjectName("chatToggle")
        back.clicked.connect(self.reject)
        title_bar.addWidget(back)
        outer.addLayout(title_bar)

        # Panel
        self.panel = SmartHomePanelWidget(engine=self.engine, parent=self)
        outer.addWidget(self.panel, 1)
