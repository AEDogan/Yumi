# Yumi — kısa başlangıç

20 Ekim 2026. Proje C:\Projeler\Yumi; kullanıcı verisi %APPDATA%\YumiDesktop. Kullanıcı bu sohbetin listesinde 3/6/7/8/9/10'u seçti: çizici, müzik, temaslar, senaryolar, model uyumu, ekranlar. Aşağıdaki son kontroller ayrı test süreçlerinde yapıldı; kullanıcının açık Yumi'si yeniden başlatılmadı. Eski ayrıntılı kayıtlar başvuru olarak korunur.

## Mevcut durum ve son doğrulama
- Adlar/presetler modele özel korunuyor; model menüsünde kullanıcı adı gösteriliyor. 19 Ekim seçim/kayıt/yeniden yükleme/boş ad ve UI kontrolleri geçti; o tarihte açık eski uygulamaya yeni kod yüklenmemişti.
- Resmî three-vrm ikincil kemik fiziği yerel gizli Node sürecinde. Masaüstünde varsayılan çizici artık desktop_vrm.py / viewer.mjs: Python son poz ve GLB dönüşümlerini verir, Three.js/VRM/MToon görüntüsü şeffaf Qt katmanına aktarılır. Önizleme ayrı kalır; OpenGL hazırlık/hata geri dönüşü ve tanısal legacy çizim korunur. Beş gerçek model geçişi, Clara/yeni modelde sekiz gerçek sahne görüntüsü, hızlı model değiştirme, boyutlandırma, gizleme/dönüş ve VRM kaldırma geçti. İlk malzeme derlemesi için 20 sn, sonraki kareler için 5 sn sınırı var. Eski yükleme/kare geri çağrıları yeni nesle yazamaz; önizleme RAF'ı masaüstünde ikinci çizim döngüsü açmaz.
- Sehpa değişiminde ensure_table içindeki tanımsız model başvurusu düzeltildi. Beş model × dokuz senaryo = 45 poz/uzuv/zemin/eşya bırakma/çıkış kontrolü geçti. FurnitureContacts üst spring kemiği düzeltildikten sonra alt kemiğin eski tanığını aynı adımda uygulamaz; odaklı zincir testi ve gerçek beden kontrolleri geçti. Pembe modelde 96 saç tanığı için kapalı koltuk vekili nüfuzu 0 ölçüldü; genel sıfır çarpışma garantisi değildir.
- Model uyumluluğu uzuv hiyerarşisini, yinelenmiş zorunlu kemik atamasını ve parmak zinciri bağlantısını denetliyor. Beş model ve bozuk eşlemeler geçti; beş modelde oturma/çalışma, altı jest, konuşma/geçiş/eklem sınırı kontrolleri geçti.
- Loopback kuyruğu eski blok yerine yenisini tutar; kayıp blok/kanal değişiminde tür penceresi ve ritim geçmişi sıfırlanır. Parça sıfırlama eski BPM/seviyeyi de temizler. Eşit yama oyu kesin tür kabul edilmez. Dubstep/klasik/techno dosya ve farklı seviye testleri, ritim saati, film/konuşma engeli ve kesik ses akışı testi geçti. Gerçek dubstep çıkışında önce kalıcı hip-hop, son kontrolde unknown görüldü; dubstep doğru tanıma hâlâ açık. Çıkış-kaynak korelasyonu .5821, SNR -2.9 dB; 44.1/48 kHz oran denemeleri bunu açıklamadı. Kök neden belirlenmedi; ses diske kaydedilmedi, mikrofon açılmadı.
- DPI alfa bileşimindeki çift ölçek düzeltildi; boş siluet eski tıklama alanını tutmaz. Arayüz %100/%150/%200; mantıksal alfa koordinatları %100/%150/%200/%300 geçti. Sistemde tek 1920×1080 ekran var; fiziksel çoklu monitör geçişi doğrulanmadı.
- Senaryolar, fiziksel bırakma ve kısa masa rotaları mevcut; sıfırdan yapılacak diye sayma. Model/ses/pencere geçişleri ve toplantı mikrofonu önceki kayıtlarda doğrulandı.
- Sesli çağırmanın ilk/ikinci denemesi ve seçili erkek sesinin çalışması daha önce kullanıcı onayı aldı. Uzun oturum kararlılığı ve belirsiz 1008 hatası açık.

## Sıradaki tek iş paketi
Seçilen kapsam içinde sıradaki dar iş: gerçek hoparlör dubstep sinyalinin kaynakla neden uyuşmadığını ve tür doğruluğunu ayır; unknown sonucunu doğru tanıma diye kapatma. Tam kumaş/öz-çarpışma, tüm jestlerin estetik kabulü, pencereli oyun/kumanda ve fiziksel çoklu monitör hâlâ açık. Mikrofonu veya ücretli ses sağlayıcısını kendiliğinden açma. Sesin 1008 işi önceki önceliktir; kullanıcı bu turda onu seçmedi.

## Diğer açık işler — ayrıntı kaydında korunuyor
- Gerçek web sohbetinde DOM/toparlama ve mükerrer gönderim kabulü; sesin ağ/kota/erişim hataları, yankı ve uzun çağırma zinciri.
- Doğal dans, pole kavrama/koreografi, müzik türü/ritim doğruluğu; modelden bağımsız beden–saç–giysi–eşya teması ve senaryo kalitesi.
- Model uyarlaması/mimik/jestlerin geniş görsel kabulü; yüksek DPI/çoklu monitör, yerleşim ve masaüstü etkileşimi; gerçek GPU kare süresi. Minimum 100 FPS ve tam kumaş/öz-çarpışma kabulü tamamlanmadı.
- Sonraki eSpeak/Pinokio başvuru sohbeti: “Yumi'de eSpeak ve Pinokio kullanımı” (01a15379-a239-7c90-a962-9b31aab34e08). Bu özet o sohbetin teknik sonucunu doğrulamıyor; bu bileşenlerde iş varsa yalnız ilgili sonuca başvur.

## Göreve göre kaynak seç
- Ayrıntılı güncel açık işler: YUMI_GUNCEL_DURUM.md, ilgili başlık. Eski ayrıntı: KALDIGIMIZ_YER.md; tümünü başlangıçta okuma.
- Ses: native_live.py, native_wake.py, live_voice/, live_history.py; web: browser_chat.py.
- Fizik/çizim: three_vrm_runtime.py, vrm_runtime/README.md, vrm.py; model incelemesinde YUMI_MODEL_ANALIZI.md ve ilgili skill.
- Bu turun tekrar üretilebilir testleri work/check_selected_regressions.py, work/check_desktop_hit.py, work/check_renderer_lifecycle.py, work/accept_selected_visual.py. Ayrıntı ve sekiz sahne görüntüsü: C:\Users\ahmet\Documents\Codex\2026-10-20\yum\outputs.
- Senaryo: YUMI_SENARYO_LISTESI.md; ilgili işlev testleri work/ altında. Geçmiş FPS değerlerini güncel ölçüm gibi sunma.

## Korunacak sınırlar
Tek ajan; kullanıcı model/veri/ayarlarını koru. Çalışan Yumi'yi ve mikrofon kullanan süreci kendiliğinden kapatma. Kaynak VRM/FBX/Blender dosyasını değiştirme; kopyada çalış. Gerçek kullanım kabulüyle sentetik test sonucunu ayır. Eski belgelerdeki Mika yolu tarihsel; güncel proje Yumi.
