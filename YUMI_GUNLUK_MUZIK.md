# Günlük senaryolar ve müzik — 17 Ekim 2026

## Kullanıcı geri bildirimi sonrası gerçek test ve düzeltme

Önceki geometrik/sahte sesli kontroller gerçek kullanım kabulü değildi. Kullanıcı komutların çalışmadığını ve direğin kaybolduğunu bildirdi. Bu bölüm aşağıdaki eski çalışma notlarının önündedir.

- `ritme göre dans et`, `ritimle dans et`, `müzikle dans et` artık hem yazılı hem çağrı adı ayrıştırıcısında tanınır. Önce yalnız `müziğe göre dans et` tanınıyordu.
- Açık `dans et` / `direk dansı yap` komutu hemen hareket başlatır. Ses/ritim yoksa durum satırında **serbest tempo** yazılır; ritim bulunduğunda hız ve faz sınırlı biçimde uyar. Sessizliği ölçülmüş BPM diye göstermez. Tür sınıflandırıcısı düşük skor verdi diye açık komut reddedilmez.
- Otomatik algılama gerçekten başlatıldı: Windows medya müziği veya en az2sn süren çıkış seviyesi yerel yakalamayı başlatır. Otomatik dans için müzik doğrulaması beklenir; video/tam ekran/konuşma ve elle durdurma korumaları var. Sağ tık → Müzik → **Müziği otomatik algıla** varsayılan açık; kapatılabilir. Otomatik dinleme mobilyada çalışan kişiyi zorla kaldırmaz.
- Direk sahnesi ritim belirsizliği, tür/şarkı güncellemesi ve Yumi'nin kendi cevabı yüzünden kaldırılmaz. Konuşurken çıkış analizi duraklar; beden/direk korunur. Tam ekran/sürükleme hareketi dondurur. Açık durdurma veya başka fiziksel komut yaklaşık4sn bırakma akışından geçer. Yeni seçilen modele aktif koreografi yeniden bağlanır.
- Direk koreografisinde48 müzikal saniyeye yayılan tam çevre yürüyüşleri, dış bacak yelpazesi, kontrollü alçalma, gövde dalgası, serbest kol yayları ve el kayışı var. Tam dönüşte kol/bacak baz yönleri de döndürülür; bind eksenlerinden ters bükülme önlenir. Yerde yapılan prosedürel ilk sürümdür; profesyonel pole mocap veya havada akrobasi tamamlandı sayılmaz.
- **Gerçek kabul:** `work/live_dance_acceptance.py` ayrı ayarlarda gerçek `MikaWindow`, gerçek gönder düğmesi, Windows çıkış ölçeri, WASAPI loopback, ONNX tür analizi ve OpenGL modeliyle95sn koştu. Müzik otomatik olarak yaklaşık15sn'de dansa geçti; yazılı `ritme göre dans et` hemen hareket verdi; direk yaklaşık56sn kesintisiz kaldı;3sn konuşma/düşük güven aralığını atlattı; açık `dur` sonrası çıktı. Son koşu çıkış kodu0, `work/live-dance-acceptance.json` hata listesi boş. Üretimden212 kare ve `work/live-pole-dance.gif` / `live-pole-contact-sheet.png` kaydedildi. Mikrofona/buluta başvurulmadı, yakalanan ses dosyaya yazılmadı.
- Test sınırı: bir önceki koşuda yaklaşık61sn'de sahne iptali yakalandı; o test profili Sonetto'dan David'e geçmişti. İptalin tetikleyicisi o koşuda kaydedilmediği için kesin sebebi ilan edilmedi. Sonraki koşuya geçiş çağrı izleri eklendi ve95sn koşu geçti; ayrıca örtük dinleme/sıfırlamanın direk sahibini kaldırması engellendi. Geçişler için300 belirsizlik/konuşma adımı ve dört modelde geometri kontrolleri geçti. Bu, her şarkıda kusursuz ritim veya estetik kabul garantisi değildir.

Son kapsam: 2 — fiziksel eşya bırakma, 5 — senaryoların ara hareketleri, 6 — müzik/tür/ritim ve dans. FPS ve süpürge bekliyor.

## Kullanım

Sağ tık → Günlük senaryolar / Müzik. Yazı ve ses komutları:

- `kitap oku`, `film izle`, `yazı yaz`, `kod yaz`, `webde oku`, `toplantıya katıl`, `kahve yap`, `pencereden bak`, `dinlen`.
- `günlük senaryoları aç` / `günlük senaryoları kapat`.
- `müziğe göre dans et` / `dans et`, `direk dansı yap` / `pole dance yap`, `müzik dinle`, `müzik dansını durdur`.
- `müzik türü pop` gibi 30 aileden elle seçim; `müzik türü otomatik` ile medya etiketi + yerel ses tahmini.

Günlük ve müzik otomasyonu varsayılan açık. Başlangıç sessizken yakalama açılmaz; medya/çıkış etkinliğiyle yerel analiz başlar. Mikrofon kullanılmaz; ses sınırlı RAM penceresinde kalır, diske veya dış servise gönderilmez.

## Eşya bırakma ve günlük akış

- Gerçek boşta kalmada 150sn sonra dinlenme, 600sn sonra kahve. Film/toplantı/müzik pasif kullanım sayılır; sırf giriş yok diye kahveye geçilmez. Yazma/kodlama müzik dinlerken de seçilebilir. Kararlar kararlılık bekler; açık komut önceliklidir.
- Sabit PC seti, onaylanan 40° açı ve monitör hizası korunur. Yazma, kodlama ve web okuma ayrı davranışlardır. Düşünme/durma, fare/scroll, küçük bakış araları var. Eşya taşınmayan bu üç mod arasında aynı masada kalınır; farklı mobilyaya geçiş kalkıştan geçer.
- Koltukta esneme, esneme yüzü/göz kırpma, omuz gevşetme, küçük duruş değişiklikleri, kısa bakış, toplantıda başla onay ve deftere bakış var. Aynı ara hareket arka arkaya seçilmez. Esnemek için ayağa kalkılmaz. Konuşma sırasında ara hareketler geri çekilir; kitap/defter/kupa elleri korunur.
- Kitapta kaynağın gerçek sayfa ve kapama animasyonu kullanılır; kaynak geometri/UV/rig değiştirilmez. Kitap yatay bırakılır: kapama animasyonu kitabı zaten yatırdığı için ek90° dönüş kaldırıldı.
- TV'de 10dk sonrası kase ve 30–40sn aralıklı ara hareketler var. Kase önce kucakta desteklenir; sol el lokmayı alıp geri döner, kumanda sağ elde kalır. Konuşurken yeme durur. Lokma ortasında çıkış komutu gelirse kısa döngü bitirilip kase yeniden tutulur.
- Erişilmeyen sehpaya eşya elde taşınarak kalkılır ve yürünür. Ardışık bırakışlarda çömelme sıfırlanmaz; el bırakışta kısa süre temas pozunu korur. Kitap/kase/kumanda/defter/kupa ayrı ayrı sönmez: yüzeyde kalıp sahneyle birlikte çıkar. Kumanda kısa mesafeden bırakıldığında dikey yerçekimi hareketiyle iner.
- Kitap/TV için yeterli yüzeyli sehpa seçilir. İnce oval sehpa bu eşyalara uymadığında geniş alternatif kullanılır; sade dinlenmede iki sehpa rastgele kalır. Yerleştirme gerçek eşya geometrisinin izdüşümü ve sehpa üst yüzeyiyle denetlenir. Bu bağlama/IK/yüzey temasıdır; tam kumaş simülasyonu değildir.
- Kahve köşesinde yaklaşık20sn hazırlık, ardından pencereye yönelme ve seyrek yudum var. Toplantı sakin PC oturuşu ve defter kullanır; kulaklık takma/saça uyarlama henüz yok.

## Yerel tür algılama ve dans

- Tür önceliği: elle seçim → Windows medya etiketi → yerel ses modeli. Durum satırı türü, BPM'yi ve bilginin kaynağını gösterir.
- MTG Discogs-EffNet'in18MB ONNX modeli CPU'da tek iş parçacığıyla çalışır. 8–10sn RAM penceresi yaklaşık4sn arayla değerlendirilir; kabul için aynı aile iki pencerede doğrulanır. Düşük skor/yakın adaylar unknown kalır; konuşma baskınsa dans bastırılır. İlk tahmin beklenirken sakin dinlenir. Model/etiket yoksa belirli bir tür uydurulmaz.
- 30 aile seçimi korunur. Yerel modelde28 aileye doğrudan karşılık var; **bachata ve latin pop yalnız medya etiketi/elle seçimle** seçilir. Skorlar doğruluk yüzdesi değildir. Model kaynağı/hash/lisansı `models/music/README.md` ve `sources.json` içinde: https://essentia.upf.edu/models.html — CC BY-NC-SA4.0; yayıncı ayrıca ticari lisans sunar.
- `dance_repertoire.py` ve `dance_motion.py`: **20 tür × 12 adım/kol figürü birleşimi = 240 repertuvar girdisi**. Pop, rock, hip-hop, R&B, house, techno, trance, disco, funk, reggae, reggaeton, afrobeats, K-pop, Latin pop, salsa, bachata, country, jazz, metal ve drum & bass. Bunlar ortak 16 adım ve 10 kol hareketinden, türün vurgusu/kalça/gövde şiddetiyle oluşturulan prosedürel, türlerden esinlenen hareketlerdir; 240 ayrı mocap kaydı veya profesyonel dans tekniği iddiası değildir.
- Her figür32 vuruş; son2 vuruşta hedefler sonraki figüre karışır, sonra tek IK çözümü uygulanır. Aynı temel figür384 vuruş geçmeden dönmez:120 dans BPM'sinde3dk12sn, en hızlı desteklenen144 dans BPM'sinde2dk40sn. Sonraki turlarda öncü ayak ve kol ayrıntıları değişir; aynı figür/öncü/ayrıntı birleşimi6 tur dolmadan dönmez. Aynı şarkıda kısa sessizlik/konuşma arası ilk figüre sıfırlamaz, sonraki müzik cümlesinden sürdürür. İki görüntüleyici tek zaman çizelgesini paylaşır; her çizim rastgele yeniden seçim yapmaz.
- Direk dansı ayrı ve açık komutla açılır; türe göre otomatik direk belirmez. Ölçeği modelin gerçek omuz/kol ölçülerine göre belirlenen direk, avuç yönü ve parmak kavraması, elin yukarı/aşağı kayışı, destek ayağı sabitken ark boyunca adımlama, kontrollü çömelme ve serbest kol figürleri var. İlk sürüm zemindeki hareketlerden oluşur; havada asılma/ters akrobasi eklenmedi. Çıkışta yaklaşık4sn içinde ark tamamlanır, el bırakılır, sonra direk ve kadraj geri çekilir. Sonraki fiziksel komut çıkışı bekler.
- Gerçek kol/bacak uzunluklarıyla IK ve taban teması korunur; sınırlı yatay kalça hareketi artık görüntüleyicide yanlışlıkla sıfırlanmaz. Tür değişimi1sn karışır. Mutlu/sakin yüz ve figüre göre baş/gövde vurguları eklenir. Kaynak VRM/mesh/rig/UV dosyaları değiştirilmez. Diğer10 tür yakın repertuvara veya sakin dinlemeye yönlenir.
- Tür seçimi resmî bir küresel ilk20 sıralaması değildir. [IFPI'nin küresel dinleme araştırmasındaki](https://www.ifpi.org/ifpis-global-study-finds-were-listening-to-more-music-in-more-ways-than-ever/) geniş ailelerden seçilmiş pratik bir dans repertuvarıdır.
- Dans saati gözlenen vuruşları sayar; yarım zamanda dönüşümlü gerçek vuruşlara bağlanır. Tempo/faz düzeltmeleri sınırlıdır, saat sıçramaz. Şarkı değişiminde eski ses penceresi ve ritim sıfırlanır; gecikmiş tahmin yeni parçaya uygulanmaz.
- Geçici konuşma/ritim belirsizliği açık dans komutunu iptal etmez; kaynak ses analizi duraklar veya serbest tempo görünür. Sürükleme/tam ekran hareketi dondurur. Otomatik dans müzik doğrulaması ister ve6sn süren sessizlikte bırakır; ambient/lo-fi/classical/folk otomatik dinlemede kalır. Video bildirimi otomatik başlatmayı engeller.

## Doğrulama ve sınırlar

- `work/check_scenario_poses.py`: dört VRM × dokuz sahne, 36 durum. Varlıklar, sonlu pozlar, kol/bacak uzunlukları, taban, kesintisiz çıkış, ardışık bırakışta gövde sürekliliği, tüm eşyaların bırakılması, sehpa içinde kalma, yüzey teması ve kitabın yatay durması geçti.
- `work/check_snack_cleanup.py`: dört modelde lokma ortasında kesilme, kasenin kucakta desteklenmesi, yeniden tutulması ve iki eşyanın bırakılıp çıkılması geçti.
- `work/check_workspace_switch.py`: aynı masada üç mod arasında mobilya/pozisyon korunması ve farklı mobilyaya çıkış geçti.
- `work/check_choreography.py`:20 türde240 repertuvar girdisi; tür başına72 benzersiz figür/öncü/ayrıntı birleşimi,384 vuruş tekrar sınırı, sınırlı önbellek ve iki görünümde deterministik seçim geçti. Dört VRM'de20 tür ×12 figür ×3 an (2880 poz), uzuv uzunlukları, taban, türlerin farklılığı ve cümle sınırları denetlendi. Direkte avuç teması, destek ayağının yatayda sabitliği ve çıkış kontrol edildi.
- `work/check_music_runtime.py`, `check_music_lifecycle.py`, `check_pole_lifecycle.py`: ritim/tür önceliği, konuşma/sessizlik, jazz dansı, direk komutları, kontrollü çıkış, sonraki komutun beklemesi, otomatik devamın açık dur komutuyla iptali, şarkı değişimi ve kısa aradan sonra koreografiyi sürdürme geçti.
- `work/check_music_clock.py`:60/75/90/120/140/160/180/240 BPM saat girdilerinde60sn sentetik izlem ve tempo geçişi geçti. Bu, bütün bu tempoların gerçek müzikten hatasız çıkarıldığı iddiası değildir.
- `work/check_music_classifier.py`: gerçek ONNX ile resmi dubstep, Mozart ve techno WAV örnekleri doğru ayrıldı. Sessizlik/saf ton/geçersiz sayı reddi ve yeniden örnekleme filtresi geçti. Üç örnek kapsamlı tür doğruluğu ölçümü değildir.
- `work/check_music_lifecycle.py`: elle/medya/ses önceliği, eski şarkı tahmininin iptali, konuşma, tam ekran ve konuşma baskınlığı geçti. `check_daily_music.py`: sentetik60–180BPM, senaryo öncelikleri ve eşikler geçti.
- `work/check_live_music.py`: gerçek WASAPI çıkışı ve yerel tür işçisi sessizlikte14sn açık kalıp temiz kapandı; mikrofon, oynatma veya kaydedilen ses dosyası yok.
- `work/check_daily_ui.py`: ayrı test ayarlarıyla komutlar, otomasyon, tür seçimi/sıfırlama ve başlangıçta yakalama açılmaması geçti. Gerçek kullanıcı ayarı değiştirilmedi. Bağımlılık kontrolü temiz.
- Üretim çizicisinde incelendi: `work/choreography-20-preview.png`, `work/pole-choreography-preview.png`, `work/scenario-polish-preview.png`.

Kullanıcının çalan müziğiyle canlı ritim/tür/dans kabulü ve bütün türler için geniş doğruluk ölçümü açık. Tam kumaş/öz-çarpışma ve kulaklık uyarlama tamamlanmış sayılmaz. FPS çalışması yeniden açılmadı.
