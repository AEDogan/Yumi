# Yumi davranış, müzik ve temas tasarımı — 15 Ekim 2026

Senaryoların güncel ana listesi ve uygulama durumu **`YUMI_SENARYO_LISTESI.md`** içindedir; önce oraya bakılır. Bu belge ayrıntılı davranış/müzik tasarımını saklar. Koltuk/sehpa ve PC sahnesinde temel yürüyerek oturma/kalkma artık vardır; aşağıdaki kitap/TV/kahve hareketleri, müzik analizi ve tam kumaş deformasyonu henüz tamamlanmadı. Eski kaldırılmış katalog otomatik geri açılmayacak.

## Uygulanan ilk koruma: tam ekran oyun

`fullscreen_pause.py` öndeki pencerenin gerçek monitör alanını kaplayan istemci alanını denetler. Oyun tanımada Windows özel Direct3D tam ekran durumu ve Steam/Epic/Riot/Xbox/GOG kurulum yolu işaretleri kullanılır. Tarayıcılar ve bilinen video oynatıcıları otomatik oyun sayılmaz. Özel oyunlar için `settings.json` içindeki `fullscreen_game_names` yürütülebilir dosya adı listesi desteklenir; henüz ayar ekranı eklenmedi. Bilinmeyen klasördeki Vulkan/OpenGL oyunları otomatik tanınmayabilir. Her tam ekran uygulamayı oyun saymak film senaryosunu bozacağından yapılmadı.

Oyun algılanınca iki avatarın çizim isteği, hareket, durum, alfa okuma ve tıklama alanı zamanlayıcıları durur; karakter/ana pencere gizlenir. Bekleyen çizim de fizik/animasyon çalıştırmadan döner. Model bellekte kalır; oyun kapanınca yeniden yükleme gerektirmez. Pencere ve etkin zamanlayıcıların önceki hâli korunur. Ses oturumunu veya kullanıcının oyununu kapatmaz. Bekleyen çizim dışındaki Qt/Windows maliyeti sıfır değildir. Oyun kontrolü 750 ms aralıklı; geri dönüş iki temiz örnek sonrasında.

Yerel Qt kontrolü: 160 ms önce 11 çizim isteği; 200 ms duraklatmada 0; dönüşte 160 ms içinde 12. Altı zamanlayıcı durdu; başlangıçta gizli/durmuş öğeler dönüşte zorla açılmadı. Windows salt okunur probu çalıştı. Bunlar gerçek oyunun FPS ölçümü veya her oyun/çoklu monitör/DPI kabulü değildir.

## Öncelik ve zaman

1. Tam ekran oyun: tüm avatar/sahne çizimi durur; mutfak/dans/otomatik senaryo başlatılmaz.
2. Açık kullanıcı komutu ve canlı konuşma: mevcut iş güvenli ara noktada bırakılır.
3. Elle seçilmiş etkinlik (film, toplantı, okuma, çalışma) korunur.
4. Müzik: yalnız açık müzik modu/uygun kaynak doğrulandığında dansa adaydır.
5. Boşta davranış: gerçek boşta kalma süresine göre ilerler.

Klavye/fare yokluğu tek başına kullanıcı yokluğu değildir. Film, ders, toplantı, oyun ve kitap okuma pasif kullanım sayılır; sırf on dakika giriş olmadı diye mutfağa geçilmez. Kullanıcı dönüşünde küçük fare titreşimlerinden dolayı sahne aç/kapa döngüsü oluşmamalı. Giriş, güven ve etkinlik sınıflandırması ayrı tutulacak.

Her senaryo: `sahneyi getir → yaklaş → yerleş → davranış → eşyayı bırak → toparlan → sahneyi çıkar`. Yalnız görsel dekorun yana kayması yeterli değil; karakterin el/ayak/kalça temasları aynı zaman çizelgesinde hareket eder. Eşyalar son temas çözülmeden yok olmaz. Acil durdurma ve tam ekran oyun bunun istisnası olarak çizimi hemen kesebilir.

## Somut sahneler

| Etkinlik | Eşya ve ana hareket | Çeşitleme | Bitiş |
|---|---|---|---|
| Yazı yazma | PC masası ve sandalye yandan gelir; sandalyeye oturup klavyede yazar | Düşünür, yazmayı bırakıp ekrana bakar; mouse/klavye arasında geçer | Elleri masadan çeker, sandalyesini geriye alır, gerekiyorsa kalkar; sonra mobilya çıkar |
| Kitap | Tekli koltukta çapraz, kullanıcıya 30–45° dönük oturur; eline kitap alır | Sayfa çevirme, bakış değiştirme; uygun aralıklarla bacak değiştirme | Sayfayı bırakır, kitabı kapatıp sehpaya koyar; kullanıcıya döner |
| Film/TV | Koltuk, küçük TV ve kumanda gelir; TV yönünde oturur | Kumandaya seyrek basma; izleme sürer | Kumandayı bırakır, TV'den kullanıcıya döner; devam edecekse ayağa kalkmaz |
| Film 10 dk+ | Yan sehpada patlamış mısır/atıştırmalık belirir | Yaklaşık 30–40 sn değişken aralıklarla küçük bir lokma; arada oturuş/bakış değiştirme | Yiyeceği bırakır, çiğnemeyi bitirir; aynı anda yeme ve konuşma yapılmaz |
| Toplantı | Sade oturma, defter | Çok düşük hareket, seyrek not alma | Defteri kapatır; kendiliğinden konuşma ve büyük sahne değişimi yok |
| Müzik dinleme | Ayakta veya koltukta seçili tutum | Baş, omuz, parmak, ayakla vuruş; parça enerjisine göre sınırlı hareket | Vuruş kaybolunca hareketi azaltır ve durur |
| Dans | Boş ve temas güvenli alan | Tam beden klipleri; el/kol/bacak/gövde; güvenli geçişler | Vuruş üzerinde figürü tamamlar, dengeli beklemeye döner |

## Boşta kalma akışı

- 0–2/3 dakika: kısa bekleme; sakin duruş ve küçük bakış değişimleri.
- Önerilen ilk eşik 150 sn: koltuk/sehpa yana kayar, yaklaşır ve çapraz oturur; bacak bacak üstüne atar.
- 3–10 dakika: koltukta dinlenir. Esneme oturduğu yerde; esnemek için ayağa kalkmaz. Tekrarlı hareketler rastlantısal ama seyrek seçilir; her hareketin tamamlanması beklenir.
- 10 dakika: başka etkinlik yoksa küçük mutfak sahnesi gelir. Önce bacaklarını çözer, ayaklarını basar, kalkar ve mutfağa gider.
- Kahve hazırlama: yaklaşık 20 saniyelik makineyle uğraşma; fincan yerleştirme, düğme, bekleme, alma aşamaları. Makine ve fincan pozları fizik temas noktalarıdır.
- Sonrasında: fincanı taşır, pencere yanında düşünceli durur; arada yudum. İlk sürümde tam oda yerine küçük mutfak köşesi/pencere çerçevesi yeterli.
- Kullanıcı dönerse: fincanı güvenli yere bırakır veya kitabı kapatır; kullanıcıya bakar. Konuşma otururken mümkünse kalkmaz. Kalkması gerekiyorsa bacak/ayak/ellerle doğal biçimde kalkar; en son eşya çıkar.

Bekleme sırasında büyük hareket seçimi için tekrar engeli ve son hareket hafızası gerekir. Sahne geçişleri sırasında ikinci bir otomatik senaryo açılmaz. Kullanıcının yeniden uzaklaşması bitmemiş toparlanmayı tersine sıçratmaz.

## Müzik algısı ve dans zamanı

Mevcut `SystemAudio.sample()` yalnız çıkış tepe seviyesini okuyor. Bu müzik türü, BPM veya vuruş fazı ölçümü değildir. Mevcut ses şiddetine tepki veren davranış doğru ritim takibi diye sunulmayacak.

Hedef akış: seçili sistem ses kaynağı → müzik/konuşma ayrımı → tür olasılıkları + enerji → BPM ve vuruş zamanları → uygun klip ve hareket şiddeti. Mikrofon veya Yumi'nin kendi konuşması dans tetikleyicisi olmayacak. Film müziği de otomatik olarak film modunu bozmayacak. Müzik modu ve dans modu ayrı seçimler olacak.

Tür etiketi kararsızsa sık sık tarz değiştirilmeyecek; pencere boyunca güven ortalaması ve geçiş eşiği uygulanacak. Bilinmeyen/karma tür korunacak; kullanıcı elle düzeltebilecek. Beat güveni düşükse rastgele hızlı dans yerine küçük dinleme hareketi kullanılacak. Analiz periyodik, vuruş saati sürekli ve hafif olmalı; her çizim karesinde sınıflandırıcı çalıştırılmayacak.

Kliplerde kaynak tempo, ölçü, kaç vuruş sürdüğü, destek ayağı, giriş/çıkış pozu ve güvenli hız aralığı bulunmalı. İlk deneysel hız sınırı 0,8–1,2; sınır dışındaysa yarım/çift zaman veya başka klip seçilecek. Bütün iskeleti tek katsayıyla hızlandırıp temasları bozmak kabul edilmez. Geçişler vuruş/ölçü sınırında; ayak temasları korunur. Tempo değişimi yumuşak takip edilir. Geçiş başına destek ayağı, faz hatası ve geçiş sıçraması kontrol edilir.

Ritim saati ses yakalama zaman damgaları/hesaplanan gecikmeye dayanmalı; yalnız render dt ile ilerlememeli. Ağır model veya GPU analizi bu tasarım turunda kurulmadı. Essentia tür modelleri ve beat araçları araştırma adaylarıdır; paket/Windows uyumu ve model lisansı seçilmeden ürün bağımlılığı sayılmaz.

## 30 müzik ailesi için ilk kapsam

Bu liste dünya genelinde ölçülmüş ilk 30 popülerlik sıralaması değildir; yaygın tür/alt türleri kapsayan ürün tasarım listesidir. Bazı başlıklar örtüşür; algılayıcı çoklu etiket üretebilir. Her satır ayrı hazır koreografi anlamına gelmez.

| # | Tür/ailesi | Hareket yönü |
|---|---|---|
| 1 | Pop | Hafif adımlar ve açık kol jestleri |
| 2 | Rock | Ağırlık aktarma, sınırlı baş ve omuz vurgusu |
| 3 | Alternative / Indie | Daha sakin, asimetrik salınma |
| 4 | Punk | Kısa ve keskin enerji; kontrolsüz zıplama yok |
| 5 | Metal | Kontrollü headbang ve gövde; saç/kıyafet bütçesi sınırlı |
| 6 | Hip-hop / Rap | Diz/gövde groove ve kol figürleri |
| 7 | R&B | Yumuşak ağırlık ve gövde hareketi |
| 8 | Soul | Yavaş salınma, ifade ve el vurgusu |
| 9 | Funk | Senkoplu ayak/omuz, küçük izolasyonlar |
| 10 | Disco | Yan adım ve kollarla ritim |
| 11 | House | Tekrarlı footwork; destek ayağı belirgin |
| 12 | Techno | Küçük, düzenli gövde/ayak vurgusu |
| 13 | Trance | Daha açık kollar, ölçülü gövde salınımı |
| 14 | Drum & Bass | Yarım zaman seçeneği; hızlı müzikte makul hareket hızı |
| 15 | Dubstep | Kontrollü dur/vur ve izolasyon |
| 16 | Ambient / Chillout | Oturarak dinleme; zorunlu dans yok |
| 17 | Lo-fi / Trip-hop | Sakin baş, omuz ve parmak ritmi |
| 18 | Jazz | Swing/senkop duyarlılığı; sakin eşlik seçeneği |
| 19 | Blues | Düşük enerjili salınma ve ayak ritmi |
| 20 | Country | Uygun adım klibi; hatalı kültürel figür uydurma yok |
| 21 | Folk / Acoustic | Hafif sallanma veya oturarak dinleme |
| 22 | Reggae | Yavaş groove ve yan ağırlık |
| 23 | Dancehall | Uygun tam beden figürleri; sadece BPM eşitliği yetmez |
| 24 | Reggaeton | Ritmik gövde ve ayak; kontrollü genlik |
| 25 | Salsa | Uygun temel adım klibi ve ölçü bilgisi |
| 26 | Bachata | Uygun kısa yan adım klibi |
| 27 | Afrobeats | Gövde/omuz/ayak; türe uygun seçilmiş klipler |
| 28 | K-pop | Pop tabanı, ayrıca tasarlanmış koreografi seçeneği |
| 29 | Latin Pop | Pop/Latin karışımına göre seçim |
| 30 | Classical / Orchestral | Dinleme/yumuşak jest; belirgin ritim yoksa dans yok |

Türkçe kullanım için ayrıca Türk halk oyunları, arabesk, Türk sanat müziği ve Türkçe pop alt profilleri değerlendirilir. Bölgesel danslar rastgele bir pop klibine tür etiketi yapıştırılarak tamamlanmış sayılmaz.

## Jestler ve temas ön koşulu

İstenen yeni jestler: gerçek parmakla OK, başparmakla onay, el belde, açık avuçla açıklama, işaret etme, omuz silkme, kısa alkış, otururken esneme, kitap/sayfa, kumanda ve fincan tutuşları. Bunlar yüz ifadesiyle eşleşir, fakat hepsi aynı anda oynatılmaz. El doluyken aynı ele bağımsız konuşma jesti verilmez; otururken bacak klibi ayakta dansla karışmaz.

El belde mevcut kodda hazır bir temas pozu değildir: `ConversationMotion.arm_targets()` el konumu ve dirsek hedefi üretir; `vrm.py` üst/alt kolu hedefe çevirir, avuç içini bele çeviren bağımsız bilek yönü çözülmez. Önce bu hedef ve bilek/önkol dönüşü hazırlanmalı; kumaş fiziği hatalı pozu tek başına düzeltmez.

Temas katmanları:

1. Yönlü omuz/dirsek/bilek sınırları, gövde/kol/bacak için basit kapsül hacimleri, parmak ve avuç yönü.
2. Kitap/fincan/klavye/koltuk için el, parmak, kalça ve ayak ankrajları; uygun yaklaşma/ayrılma hareketleri.
3. Kumaşa özel bükülme, esneme, sürtünme, sönüm ve kalınlık profilleri; görünür mesh yerine düşük çözünürlüklü simülasyon yüzeyi.
4. Etek/pelerin/kurdele için gövde ve el çarpışmaları; gerektiğinde kumaşın kendi kendine teması. Yalnız spring-bone zincir uçlarını itmek tam yüzey teması değildir.
5. Karmaşık yumuşak dolgu (minder vb.) için önceden hazırlanmış şekil düzeltmeleri veya ayrı yumuşak cisim çözümü. Her eşyada pahalı hacim simülasyonu zorunlu değil.

Mevcut yay kemikleri genel basınçla kumaş katlanması sağlamıyor. Sonetto dönüşümünde yay grupları var fakat gövde/el collider grupları hazırlanmadı. İlk öncelik kol/bilek pozu ve kaba çarpışma; ardından el belde, çapraz bacak, oturarak kitap ve fincan için temas önizlemeleri. Bu kapı geçmeden büyük mutfak/çoklu mobilya davranışları tamamlandı sayılmamalı.

Unreal tarafında Control Rig/IK poz hazırlama; Chaos Cloth ve Panel Cloth Editor giysi; Physics Asset gövde temas hacimleri; Chaos Flesh hacimsel yumuşak cisimler için adaydır. Yumi Python/PySide/OpenGL ile çizildiği için Unreal çalışma zamanı simülasyonu VRM/VRMA aktarımıyla otomatik gelmez. Seçilmiş sabit hareketler kemik/şekil animasyonuna dönüştürülebilir; yeni temaslara tepki veren fizik için Yumi içinde çözüm veya ayrı motor entegrasyonu gerekir. Motor geçişi bu turda yapılmadı.

## Kaynaklar

- https://musicbrainz.org/genres — tür sözlüğü; popülerlik sıralaması değil.
- https://essentia.upf.edu/models.html — tür modelleri; model lisansları ayrıca kontrol edilmeli.
- https://essentia.upf.edu/reference/std_BeatTrackerMultiFeature.html — vuruş konumları ve güven çıktısı.
- https://learn.microsoft.com/en-us/windows/win32/api/shellapi/ne-shellapi-query_user_notification_state — özel D3D tam ekran durumu.
- https://dev.epicgames.com/documentation/en-us/unreal-engine/clothing-tool-in-unreal-engine---properties-reference — giysi simülasyonu özellikleri.
- https://dev.epicgames.com/documentation/en-us/unreal-engine/panel-cloth-editor-overview — kumaş hazırlama iş akışı.
- https://dev.epicgames.com/documentation/unreal-engine/chaos-flesh-overview — hacimsel yumuşak cisim sistemi.
