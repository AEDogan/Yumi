# Yumi — güncel başlangıç

26 Ekim 2026. Çalışma yeniden başladı: 1. başlık uzun ses kabulü açık; kullanıcının ayrıca istediği 3. başlık paketi tamamlandı.

## İlk okunacaklar
- Ayrıntılı kalan işler ve son doğrulama: docs/DEVIR-2026-10-26.md.
- Dosya yönlendirmesi: CODEBASE_MAP.md. Tüm klasörü tarama; ilgili dosya ve satırlardan ilerle.
- Önceki durum geçmişi: docs/archive/DURUM-before-2026-10-26-checkpoint.md. Yalnız ihtiyaç halinde aç.

## Aktif öncelik
Genel işleyiş önce: ses/bağlantı → otomatik davranış ve komut önceliği → günlük senaryolar → arayüz → veri/kurulum → genel uzun kabul. Skinler, model fizik/görünümü ve oyun hareket arşivi sonraya bırakıldı. Android ardından, Houdini en son. Genel FPS çalışması beklemede.

## Son tamamlananlar
- Ayrı Yumi proje kopyaları related-projects/ altında toplandı; aktif iç paketler değiştirilmedi.
- live_voice/live_core.py boşta kontrolüne son 250 ms oynatma koruması eklendi. Yeni hata testi, mevcut sessiz-yenileme ve sağlayıcı hata testleri geçti.
- Müzik durum metinlerindeki Türkçe kodlama hataları önceki turda düzeltildi.
- Skin prototipinin başarılı görünen bazı kareleri genel skin kabulü sayılmıyor. Yırtık, renk ve el tutuşu hâlâ açık.

## Sıradaki tek iş
Ses oturumunda kalan bağlantı kesilme/toparlanma akışları ve gerçek uzun kullanım kabulü. 1008 nedeni belirsiz; test kanıtı olmadan kota/süre sonucu çıkarma. Kullanıcının sohbet/ayarlarını koru; açık uygulamayı kendiliğinden kapatma.

Üretim kaynak değişiklikleri açık uygulamaya yüklenmiş sayılmıyor; yeniden başlatma yapılmadı.


## Son paket — 1 ve 3. başlık
- Ses: iptal edilmiş kurulum soketi, kapanış hatasında eski bağlantı, aygıt hatasında mikrofon lease/alıcı temizliği ve geç gelen eski soket mesajları düzeltildi. Dokuz odaklı test betiği geçti. Gerçek uzun test son 3420 saniye/6 yanıt kaydından sonra provider_closed ile başarısız sonlandı; kesin neden/kod kaydedilmemiş. Ayrı kontrollü gerçek yeniden bağlantı 2 yanıt/1 resume ile geçti. Uzun kabul açık; docs/SES-SONUC-2026-10-26.md.
- Senaryolar: oluşturulamamış sahneyi temizleme hatası ve erken iptalde oturma/eşya alma düzeltildi. Bitmiş sahne referansı devre dışı/gizli/bastırılmış durumda da temizleniyor. 27 erken iptal, 9 normal eşya bırakma/çıkış ve gerçek Qt/three-vrm kontrolü geçti. Ayrıntı docs/SENARYOLAR-2026-10-26.md.
- Kullanıcı cihaz köprüsünde geliştirici API key istemeyen hesap/QR eşleştirme araştırmasını listeye ekletti: docs/CIHAZ-BAGLANTISI-ARASTIRMA.md. Uygulama/cihaz işlemi yapılmadı.
- Witcher oyun karakter sesleri yalnız ertelenen karakter listesine eklendi; skin aşaması hâlâ beklemede.
