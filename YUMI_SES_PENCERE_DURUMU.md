# Ses bağlantısı ve pencere sahnesi — 17 Ekim 2026

## Son düzeltmeler — güneş saatleri, masa, okuma ve saç

- Kullanıcının “birkaç saniye” isteğine aykırı olan30sn süre4sn'ye geri çekildi. Gerçek geçen süre testinde son oynatmadan sonra4.19–4.20sn'de sohbet yakalaması kapandı, alıcı/bağlantı açık kaldı. Adla çağırma açıksa yerel wake mikrofonu yeniden kullanır; Windows mikrofon simgesinin açık kalması buluta ses aktarımı anlamına gelmez. Konuşma/yanıt/oynatma sürerken zaman aşımı uygulanmaz.
- Open-Meteo güncel şehir yanıtından sunrise/sunset ve utc_offset_seconds alınır; şehrin yerel tarih/saatine göre ±30dk yumuşak gündoğumu ve günbatımı geçişi, gündüz ve gece. Veri eksikse is_day tabanlı görünüm korunur. `work/window-solar-preview.png` dört evrenin gerçek renderıdır. Saat dönüşümü kaynağı: https://open-meteo.com/en/docs .
- Kullanıcının `table_-_hightop.glb` dosyasının kopyası `items/table_hightop.glb`:398 üçgen,378 vertex,1 materyal,3 texture, animasyon yok. Kaynak ve kopya SHA256 aynı: CB333A564459E6460766857761C9E1F61EAE02DE0B81FBE2D0840878F4A1D65A. Kaynak dosya değiştirilmedi. Yuvarlak tabla çapı1.04 kanonik birim, yükseklik karakterin dirsek/kol ölçüsünden; genişlik/yükseklik ayrı ölçeklenir. Makine ve kulplu bardağın tüm taban izdüşümleri dört modelde yuvarlak yüzey içinde doğrulandı. Yaklaşım/çıkış aynı tablanın muhafazakâr ayak izini kullanır.
- Kitap tutuşu omuz/baş/kol ölçülerine göre göğüs seviyesine alındı, sayfalar karaktere bakacak yönde -48° eğimli. Baş yaklaşık22° aşağı eğilir, küçük okuma taraması var. Sol el kitabı desteklerken sağ el sayfaya gider; hareket sırasında kitap ortalama el konumuyla sallanmaz. İlk okuma olayı12–18sn, sonraki aralar16–24sn. Kitabı kapatıp iki elle taşıma ve sehpaya bırakma geçişi de aynı ölçekle güncellendi.
- Sessiz oturuşta sürekli Sitting_Idle_Loop kaldırıldı; oturma/kalkma ve konuşma animasyonları korunur. Başa bağlı authored spring zincirleri materyal adı genel olsa bile tespit edilir; uzun pembe saçlı modelde32 düğüm. Oturuşta ek sönüm ve koltuğun baş köküne göre yüzey tarafını gözeten sınırlı temas düzeltmesi var. Saç ve kumaş için96'şar gerçek vertex örneği ayrılır; kumaşın örnek bütçesini tüketip saçı dışarıda bırakması önlendi.
- Bu, örneklenmiş iskelet/koltuk temasıdır; her vertex ve bütün pozlar için tam kumaş/saç öz-çarpışması garantisi değildir.

### Son testler

- `work/check_solar_idle_table.py`: gerçek4.2sn kapanış, bağlantının korunması, şehir saat dilimi/güneş evreleri, dört modelde yuvarlak tabla destek sınırları geçti.
- `work/check_coffee_contacts.py`: dört modelde bardak-parmak, yaklaşım ve çıkış geçti.
- `work/check_reading_exit.py`: dört modelde okuma pozları, uzuv uzunlukları, zemin ve kitabın kapanıp bırakılması/çıkış geçti.
- `work/render_reading_hair_table.py`: dört model × okuma/masa/kahve, gerçek render görüntüleri incelendi. GPU hazırlığından önceki CPU vertex skinning döngüsü testte atlanarak gereksiz uzun test süresi giderildi. `work/reading-hair-table-preview.png`.
- Son bir saniyede ölçülen sakin oturuş saç düğümü hareket aralıkları: David0.00422, pembe uzun saçlı0.00822, kısa koyu saçlı0.00476, Sonetto0.00694 kanonik birim. Saçlar dondurulmadı.
- `work/check_pink_hair_contacts.py`: kullanıcı görselindeki modelde96 gerçek saç yüzeyi örneği; kapalı koltuk proxy'sine kalan örnek penetrasyonu0.0. Bu ölçüm görünür bütün üçgenler veya her koltuk için sıfır penetrasyon kanıtı değildir.
- `work/check_contact_physics.py`, `work/check_persistent_voice.py`, `work/check_voice_weather_wake.py` ve değişen kaynakların sözdizimi kontrolü geçti. Gerçek hava servisi sunrise/sunset döndürdü.

## Ses

- `audio_devices.py`: Windows WASAPI giriş uçları üzerinden liste; bu bilgisayarda varsayılan + Realtek ve DroidCam. Aynı aygıtın MME/DirectSound/WASAPI tekrarları kaldırıldı. Mikrofon seçimi yerel wake ve Chromium AEC işçisine aktarılır; bulunamayan seçim başka mikrofona sessizce düşmez.
- Uygulama açılırken Gemini Live anahtarı varsa mikrofonu açmadan hazır bağlantı kurar. Ad/buton sohbeti aynı bağlantıda mikrofonu etkinleştirir. Durdurma veya4sn etkinliksiz bekleme sohbet yakalamasını kapatır, yerel wake kilidini bırakır, bağlantıyı korur. Sunucu bağlantı yenilemeleri mevcut session resumption yolunu kullanır. Beklemede buluta ortam PCM gönderilmez.
- Sohbet değişimi, model/ses/mikrofon ayarı veya tamamlanan yazılı sohbet bağlamı yeni kurulum gerektirebilir; sıradan sesli konuşma aralarında yeniden bağlanılmaz.
- Yerel beceri sonuçları mikrofon açılmadan ayrı çıkış aygıtıyla Gemini sesinden okunabilir. Erişim yoksa ekrandaki sonuç korunur.
- Ayarlar → Davranış: “Windows açıldığında Yumi’yi başlat”. HKCU Run / Yumi, pythonw ve launch.py yolları doğrulanır. Kullanıcı işaretlemeden etkinleştirilmedi; mevcut durumda kapalı.
- Kullanıcı görselindeki doğrulama hatası `chatgpt-web` sağlayıcısındandı. Sağlayıcı değiştirilmedi, doğrulama atlatılmadı. Hata sonrası mesaj taslağı korunur; boş “Mesaj tamamlanamadı” balonu kaldırılır; “Site doğrulamasını aç” ve “Doğrulamayı tamamladım” düğmeleri sunulur. Gerçek site doğrulamasını kullanıcı tamamlamalıdır.

## Pencere

- Pencere karakterin arka çaprazında; hedefe gövde dönüşü yaklaşık141°. Authored pencere YZ düzleminde olduğundan normaline uygun -75° yerleşim kullanılır. Yürüyüş/çıkış engelleri ve kadraj aynı döndürülmüş yerleşimi kullanır.
- Her sahne girişinde üç yerel çizilmiş manzaradan rastgele biri seçilir: deniz, dağ, ağaçlık. Sahne sırasında değişip sıçramaz. Görünüm cam arkasındadır; yağmur/kar dışarıdaki panel sınırında kalır.
- Ayarlardaki şehir için Open-Meteo güncel weather_code/is_day, arka plan işçisinde alınır; 15 dk önbellek ve yenileme. Yağmur, kar, sis, bulut, fırtına ve gece paleti. Veri yok/eskimişse nötr görünüm, hava durumu uydurulmaz. Kaynak: https://open-meteo.com/en/docs .

## Doğrulama

- `work/check_persistent_voice.py`: aygıt tekrarları, kesin seçim, iki konuşma/tek alıcı, sessizlikte bağlantının korunması, mikrofon kilidi bırakma, hata temizliği, Qt etkinleştirme/iptal ve mock Windows başlangıç kayıt aç/kapat.
- `work/check_wake_recovery.py`, `work/check_voice_weather_wake.py`, `work/check_native_text_merge.py` geçti.
- `work/probe_live_standby.py`: gerçek Gemini kurulumu +7 sn mikrofon açılmadan bekleme geçti.
- `work/probe_selected_microphone.py`: gerçek Realtek seçimi, yankı/gürültü giderme, buluta PCM göndermeden açma geçti.
- `work/probe_wake_startup.py`: yerel David dinleyicisi yaklaşık0.55 sn hazır; test hemen durdurur, kayıt almaz.
- `work/check_live_app_startup.py`: gerçek MikaWindow başlangıcında Gemini hazır + yerel wake hazır + bulut mikrofon kapalı + metin sohbeti serbest birlikte geçti.
- `work/check_voice_settings_ui.py`: gerçek ayarlar arayüzü ve iki mikrofon doğrulandı, görseller kaydedildi.
- `work/check_coffee_contacts.py`: dört modelde yaklaşım/çıkış engelleri ve bardak-parmak teması geçti. `work/render_window_weather.py`: arka yöne gövde ve dört hava görünümü gerçek renderda kontrol edildi; `work/window-weather-preview.png`.
- Kayıtlı şehir için gerçek Open-Meteo sorgusu başarılı; yağmur ve gündüz alanları döndü. Hassas şehir/anahtar/konuşma dökümü rapora yazılmadı.
- Açık kabul sınırı: kullanıcının gerçekten seslenerek başlattığı ve karşılıklı konuştuğu deneme bu turda yapılmadı. Web hesabı tarayıcı doğrulaması çözülmüş sayılmıyor. Akrobatik pole dansı bitmiş sayılmıyor.

## Dansın devam noktası

Kullanıcı kesintinin kendisinden kaynaklandığını açıkladı; artık iptal tetikleyicisi açık hata olarak izlenmeyecek. İstenen pole hareketi yükselme, asılma ve dönüş içeren akrobatik dans. Önceki zeminde hareket bunun karşılığı değil. `work/dance_quality_prototypes.py`, CMU salsa kaynak/örnekleri ve inceleme GIF'leri saklandı; üretimde akrobatik klip veya havada destek fiziği henüz yok. Ses ve pencere işleri araya girdi. FPS ve süpürge hâlâ beklemede.
