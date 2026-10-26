# Aktif Yumi beceri paketi — dar harita

Bu paket uygulamanın aktif import yoludur. related-projects altındaki standalone kopya ile karıştırma. Başlangıç ../DURUM.md.

- engine.py / dispatcher.py: yerel beceri kaydı ve yönlendirme.
- ui_smart_home_panel.py: marka köprüsü alanları, cihaz listesi ve Android TV eşleştirme arayüzü.
- skills/smart_home_skill.py: keşif, kayıt, sync_cloud_bridge_devices, sağlayıcı komutları. Kullanıcı/API bilgilerini günlüğe dökme.
- android_tv_bridge.py: mevcut yerel TV kod/sertifika eşleştirmesi; çalışmış özelliği yeniden yapma.
- storage.py: beceri verisi ve kalıcılık; dosya içerikleri/sırlar gereksiz okunmamalı.
- ../docs/CIHAZ-BAGLANTISI-ARASTIRMA.md: hesap/OAuth, QR/kod ve cihaz modeli/bölgesine göre yapılacak bağlantı işi. Araştırma kaydıdır, uygulanmış özellik değildir.
