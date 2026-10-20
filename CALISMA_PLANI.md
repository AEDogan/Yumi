> Kısa başlangıç: [DURUM.md](DURUM.md). Bu dosya ayrıntılı başvuru/geçmiş kaydıdır; açılışta tamamını okuma. Yeni durum özetini DURUM.md içinde güncelle; ayrıntılı açık işler burada korunur.

# Yumi çalışma planı — 13 Ekim 2026

## 14 Ekim: açılış onarımı ve yalnız native sesler — en son karar

Kullanıcı masaüstü Yumi'nin açılmadığını ve gerçek 14 Ekim prototip kopyasının boş komut penceresinde kaldığını bildirdi. Ses kütüphanesi ilk yüklemesindeki platform.system / WMI sorgusu 8 saniyelik stack testiyle takılma noktası olarak doğrulandı. Scoped WMI-free hazırlıkla aynı 6/4 GiB sınırında import geçti; masaüstü ana/karakter penceresi gerçek açılışta 12:43:58'de doğrulandı. Kısayol hedefi doğruydu, değiştirilmedi.

Kullanıcı bütün eski sesleri şimdilik kapatıp yalnız Gemini/ChatGPT native seslerini test etmeyi istedi. Windows/Edge/Piper/Chatterbox/deneysel TTS seçenekleri ve aktif ses yolları devre dışı; startup Piper/uyarı warmup yok. Eski yerel STT ve otomatik adla dinleme yeni native kabulüne kadar kapalı. Model/sürücü/sistem sesi dosyaları silinmedi. Masaüstü eski sohbet şu aşamada metindir; native ayrı prototipte. Gemini native sesleri listelenir; OpenAI anahtarı yok, test edildi/kullanılabilir gösterilmez. Kendi model adaptörleri sonraya ertelendi.

Kullanıcının gerçek 2026-10-14/realtime-voice-chat-2/outputs/yumi-live-prototype kopyası güncellendi. Aynı BASLAT.cmd --check ve run_live.py --devices yolları görünür durumlarla geçti; yeni ses/mikrofon oturumu açılmadı. Başlangıç 40 s, aygıt hazırlığı 8 s sınırında; açık kullanıcı testleri kapatılmadı. Bellek korumaları ve PAUSED otomasyon aynı. Ayrıntı: Yumi-acilis-onarimi.md. Sonraki tek kontrollü insan testi bu güncel kopyada; tam native ses kabulü ve avatar entegrasyonu hâlâ açık.




## 14 Ekim: yeni hedef — canlı ses çekirdeği ve bağımsız model/ses/avatar seçimi



Kullanıcı canlı konuşmayı anlama ve sohbeti Gemini veya resmî OpenAI ses API'sine taşımayı, önce mevcut uygulamadan ayrı küçük prototiple doğrulamayı onayladı. Avatar/skin/animasyon parçaları korunuyor. Eski uygulamayı silme, yeniden başlatma veya büyük geçiş bu aşamada yok.



Son tercih: varsayılan Gemini Live native ses; kullanıcı daha sonra kendi yerel/uzak dil ve ses modellerini bağlayabilmeli. Dil modeli, ses sağlayıcısı/ses kimliği ve avatar bağımsız tercihler. Prototip yalnız Gemini Live adaptörünü uyguluyor; özel modellerin yüklenmesi/uyarlanması planlandı, tamamlandı sayılmıyor. Mevcut Codex ses oturumunu gömme destekli bir özellik olarak varsayılmıyor. OpenAI seçeneği ayrı resmî API kimlik doğrulaması/erişimi gerektirir; kayıtlı OpenAI anahtarı bulunmadı ve ücretli erişim açılmadı.



Gemini'nin native sesini değiştirmek aynı dil/canlı konuşma motorunu korur, fakat oturumun yeniden yapılandırılması/bağlanması ve geçmişin devamı gerekir. Harici TTS transkript/sentez kuyruğu ekler; gecikme ve araya girme iptali ayrıca doğrulanır. Metin tabanlı özel dil modeli kendi başına ses anlama motoru değildir.



Son prototip engeli: araç bağlamında API çalıştı fakat ses aygıtı altyapısı beklemede kaldı; normal bağlamda WASAPI mikrofonu Invalid device (-9996) ve DPAPI çözümü güvenlik bağlamı hatası verdi. Aynı engelde tekrar yapılmıyor. Aygıt engeli çözüldü denmiyor; kendi Windows oturumunda BASLAT.cmd ile tek kontrollü deneme sıradaki adımdır. Açılış 8 saniyelik watchdog ve üst süreç toplam süre sınırıyla korunur. Dosyalar, mikrofon ve uygulama varsayılan ayarları değiştirilmedi; mevcut Yumi yeniden başlatılmadı. Sonuç: Yumi-canli-ses-sonuc.md.

Prototip: çalışma alanı outputs/yumi-live-prototype. Resmî Gemini 3.8 Live mevcut ücretsiz proje anahtarıyla gerçek native audio yanıt verdi. Sentetik ses girişi transkripti ve sesli yanıt geçti. İnsan mikrofonu ve sesle araya girme kabulü açık. AEC/yankı giderme bu masaüstü prototipinde uygulanmadı; ürünün açık hoparlör kabulünden önce çözülmeli. Zaman ölçümleri README ve JSON kayıtlarında.



Geçerliliği değişen işler: tarayıcı düğmesi/oturum otomasyonu, yerel Whisper/Vosk VAD zincirini ana sohbet olarak iyileştirme, edge-tts/site sesi üzerinden ana cevap, Qwen/llama çevrimdışı modeli varsayılan olarak kurma artık canlı çekirdeğin ön koşulu değil; yeni mimariyle YERİNE GEÇTİ veya özel model adaptörü aşamasına ERTELENDİ. Dosyaları silinmedi. Daha önce yapılmış düzeltmeler geçmiş kayıt olarak korunuyor.



Geçerli kalan işler: kullanıcı adıyla model listeleri ve kalıcılık; aynı pencerede kayan ayarlar; VRM uyarlaması, eklem/temas/giysi/fizik; bellek ve performans; desteklenen gerçek oturumlarda kesintiden toparlanma; güvenli kişisel kimlik bilgileriyle dağıtım; insanla tam sesli kabul. Dans/senaryo/müzik eski başarısız katalog olarak geri açılmaz; sonraki içerik aşamasında kalır.



Bellek sınırları ve boş bellek rezervi korunuyor. Ağır yerel model indirmesi/GPU testi yok; otomatik devam PAUSED kalıyor. Sonraki somut adım gerçek kullanıcıyla bağımsız çekirdeğin kabulü; sonra ses seviye/durum olaylarını mevcut avatar hareketlerine bağlamak. Bu bölüm güncel karardır; aşağıdaki tarihli uygulamalar bu kararla çelişiyorsa geçmiş kayıt sayılır.





## 14 Ekim: sistem kararlılığı ve bellek koruması — en son durum



Kullanıcı Monster Control Center/MonsterTuning erişim ihlallerini ve bilgisayar çökmesini bildirdi. Nedensellik kanıtlanmadı. Ağır indirme, paket/model/GPU testleri durduruldu; otomatik devam PAUSED. Kullanıcı bellek sınırını tüketmeden çalışmayı istedi.



Başlatıcıya Windows Job Object toplam 6 GiB / süreç başına 4 GiB taahhüt bellek sınırı eklendi. Sistem rezervi en az 12 GiB veya taahhüt sınırının %15'i ve 4 GiB fiziksel RAM; işin tahmini ihtiyacı ayrıca ekleniyor. Yerel STT/TTS başlangıç denetimi uygulanıyor. Henüz dağıtılmamış yerel model CPU/four threads, 4 GiB sınır ve saniyelik basınç denetimi kullanıyor. Büyük model/GPU testi yeniden başlatılmadı.



Gerçek küçük Windows sınır testi ve basınç kararları geçti. Güncel kaynakla canlı Yumi açılışı henüz denenmedi. Paket teslim edilebilir değil; yeni korumalarla derleme/test açık. Diğer uygulamalar ve sistem ayarları değiştirilmedi. GPU sürücüsünün bütün tahsislerini sınırlama garantisi yok. Ayrıntı: Yumi-bellek-korumasi.md.





## 14 Ekim: ücretsiz API sohbeti ve gerçek görüntüde bildirilen eklemler



- Seçili bağlantı artık Gemini API / gemini-3.5-flash-lite. AI Studio'da mevcut Mika anahtarının projesi Free tier olarak görüldü ve kayıt eşleşti; ücretli faturalandırma veya yeni anahtar oluşturulmadı.

- API'de üç gerçek soruda ilk metin 0,72–1,52 s, Qt penceresinde iki takip sorusu yaklaşık 2 s içinde geldi. Bağlam korundu. Gerçek seçili Emel sesine kadar uçtan uca oynatma geçti; ilk hoparlör başlangıcı 5,41 s. Uzun oturum/kota/ağ çeşitliliği açık. ChatGPT web doğrulaması ayrıca açık; ana sohbetin buna bağımlılığı kaldırıldı.

- API/model seçimi ayarlarda açıldı; yeniden açılışta web'e geri yönlendirme kaldırıldı. Boş akışı tekrar gönderme ve modeli habersiz değiştirme yok. API iptali, eksik yanıtı geçmişe tamamlanmış olarak almama, konuşurken yeni soru gönderme ve eski ses sonucunu atma kontrolleri geçti.

- Kullanıcının gerçek ekran görüntüsünde çömelmiş dizler ve ters dirsek bildirimi işlendi. Sabit çömelme kaldırıldı; pelvis bacak erişiminden hesaplanır, dirsek düzlemi düzeltildi. David/Clara'da diz/dirsek yönü, ayak basma, gerçek kemik hedefleri ve yandan GPU görüntüsü kontrol edildi. Diğer pozlarda tam anatomi/temas ve Clara giysi görüntüsü açık.

- Ayrıntı: Yumi-akici-sohbet-ve-eklemler.md; görüntü: Yumi-duzeltilmis-eklemler.png.

- Kullanıcı uyurken kendisine ihtiyaç duymayan tüm işleri sürdürme yetkisi verdi. Beş saatte bir bu sohbette devam otomasyonu etkin. Tek ajan; kullanıcı sorusu, ücretli modele geçme veya reset kredisi tüketme yok. İnsan doğrulaması gereken ve henüz tamamlanmamış maddeler açık bırakılır.





## 14 Ekim: öncelikli üç işe devam



- Sohbet: ayrı tercih gönderimi kaldırıldı; tek gerçek soruya kısa yanıt isteği eklendi. Durdur kontrolü, ses kuyruğunu kesme ve site doğrulamasını açık gösterme uygulandı. Qt ve gönderim/iptal kontrolleri geçti. Gemini gerçek yanıt ve devam sorusu verdi; 3,2–69,4 saniye arası gecikme ve başka denemede zaman aşımı görüldü. ChatGPT “Bir dakika lütfen…” doğrulamasında. Kararlılık kabulü açık.

- Mikrofon: askıya almada eski ses/kayıt kuyruğunu sıfırlama, 350 ms çıkış sesi bekleme, kısa darbe eleme ve sessiz elle dinlemeyi kapatma uygulandı. Gerçek mikrofon 16 kHz ses blokları üretti; yerel STT çalıştı. Üretilmiş seste yabancı isim algılama tutarsız olduğu için gerçek insan/gürültüyle uyandırma kabulü açık.

- Hareket: iki modelde bacak oranlarına göre adım çözümü ve aynı ritimden türetilen masaüstü ilerleme hızı uygulandı. Üç çevrim ve gerçek GPU çizimindeki ayak kemikleri hedeflerle eşleşti. Tam doğal hareket, dönüş/temas ve masaüstü video kabulü açık.

- Ayrıntı: Yumi-oncelikli-uc-is.md; yürüyüş fazları: Yumi-yuruyus-kontrol.png. Üç büyük iş tamamlandı olarak işaretlenmedi.





## 14 Ekim: uygulanan yeni düzeltmeler



- Açılış hazırlığı artık kendiliğinden sohbet mesajı göndermiyor veya bir tercih yanıtını beklemiyor. Kısa yanıt tercihi kullanıcı isteğinde ilk kez hazırlanır. Yeniden açılışların aynı başlangıç mesajını otomatik tekrar gönderme yolu kaldırıldı.

- Yeni yanıtı ayırt etmek için mesaj sayısına ek olarak sayfadaki yanıt elemanının kimliği izleniyor. Mesaj sayısının sabit kaldığı durumda da yeni yanıt algılama kontrolü geçti. Gecikmeli düğme, çift göndermeme, belirsiz kabul ve zaman aşımında durdurma kontrolleri yeniden geçti. Canlı sağlayıcı yanıtı bu değişiklikle henüz doğrulanmadı; sohbet işi açık.

- VRM yüklemede bütün kullanılan kol/bacak/el/ayak kemikleri ve düğüm numaraları erken doğrulanıyor. İki mevcut model geçti; eksik ayak ve hatalı kemik referansı bozuk örnekleri açık hata verdi. Genel anatomi/temas çözümü değildir.

- İki model aynı GPU çizim yolunda ekran dışı ölçüldü: David model hesabı 4,95 ms, çizim/GPU beklemesi 1,31 ms; Clara 5,20 ms ve 3,42 ms. David 17, Clara 89 çizim parçası içeriyor. Masaüstü FPS'i ölçülmüş sayılmıyor. Eklem optimizasyonu toplamda net hızlanma göstermediği için uygulanmadı. Ayrıntı Yumi-model-olcumleri.md içinde.



- Ayarlar, VRMA animasyon ekranı ve karakter ekleme ayrı uygulama pencereleri yerine ana penceredeki PageStack içinde açılıyor. 220 ms yandan giriş/çıkış, ekran yığını, tekrar açma koruması ve geçiş sırasında boyut değişimi kontrol edildi. Windows animasyonları kapalıysa geçiş animasyonsuz.

- Karakter ekleme engelleyici QDialog.exec döngüsünden çıkarıldı. Birden fazla dosya sırayla aynı pencere içinde işleniyor; alt ekran kapanınca önceki ayar alanları ve sekme korunuyor. Ses önizlemesi sayfa kapanırken/başka sayfaya geçerken iptal ediliyor.

- Resmî edge-tts 7.3.1 test edilip Yumi'nin sanal ortamına uygulandı. Yumi backend kodunda Ahmet 2,5 s ve Emel 1,9 s içinde ses üretti; ikisi de kelime zamanları döndürdü. Önizlemede gerçek oynatıcı PlayingState/EndOfMedia ile doğrulandı: üretim ve oynatma toplam Ahmet 5,7 s, Emel 4,6 s. Bu denemelerde 403 görülmedi; uzun oturum ve farklı ağ kararlılığı hâlâ genel kabul bekliyor.

- Ses önizleme dosyaları motor/ses kimliğine göre ayrıldı; başka sese geçildiğinde oynatıcının önceki dosyayı önbellekten yeniden çalması önlendi.

- Sohbet hâlâ açık: kısa test mesajı siteye ulaştı, fakat Gemini ve ChatGPT denemelerinde yeni tamamlanmış yanıt alınamadı. Gemini aynı profilin gizlenmiş normal Chromium penceresinde de doğrulanamadı. Bu deneysel tarayıcı modu ürün koduna uygulanmadı. Sorunun yalnızca dış sağlayıcıdan kaynaklandığı kanıtlanmadı; uçtan uca sohbet tamamlanmış sayılmıyor.

- Yeni doğal dans/senaryolar, tam anatomik temas/çarpışma, 100+ FPS ve paketli dağıtım henüz tamamlanmadı. Eski rastgele içerik geri açılmadı.



Ses paketi kaynağı: https://github.com/rany2/edge-tts/releases/tag/7.3.1



Kullanıcının son kararı: mevcut prosedürel danslar ve otomatik senaryolar tamamen kaldırılacak. Eski katalog ve poz sistemi yeni içerik için geri kullanılmayacak. Önce kullanılabilir çekirdek tamamlanacak.



## Bu tur uygulananlar



- Dans kataloğu, dans penceresi, dans ilerleme sistemi ve otomatik senaryo listesi uygulamadan kaldırıldı.

- Dans/senaryo düğmeleri, ayarları, zamanlayıcıları ve müzik/aktivite tetikleyicileri kaldırıldı. TV izleme, masa ve yatak otomatik davranışları da kapatılıp çizim yolları kaldırıldı.

- Eski dans/masa/yatak/TV pozları artık bir eski çağrı ulaşsa da çalıştırılmıyor.

- Kullanıcının VRM/VRMA modelleri ve GLB varlıkları korunuyor. Temel duruş, gezinme, selamlama, dinleme, konuşma ve elle animasyon dosyası oynatma kalıyor.

- Her soru öncesindeki ikinci web hazırlık döngüsü kaldırıldı. Gönderim ve yanıt aşamaları arayüze ayrı iletiliyor.

- Önceki turdaki gerçek Chromium giriş/tıklama, gönderim kabulü, tekrar göndermeme, zaman aşımında durdurma ve gönderilmemiş mesajı geri getirme değişiklikleri korundu.

- Kaldırma ve hata/ses kuyruğu kontrolleri, gerçek Qt pencere açılışı/çizimi, gecikmeli düğme ve belirsiz gönderim kontrolleri geçti.

- Dokuz gerçek VRM dosyasında temel hareket ve VRMA hesapları sonlu/geçerli kaldı. Yerel Piper gerçek WAV üretti (2,4 saniyelik ses); doğal hareket kalitesi ve gerçek hoparlör/mikrofon kabulü ayrıdır.

- Canlı çevrimiçi yanıt henüz başarıyla doğrulanmadı. Bu belge sohbetin hazır olduğunu iddia etmez.



## Sıralı işler ve kabul koşulları



### Eklenen arayüz isteği: aynı pencerede yandan kayan alt ekranlar



14 Ekim 2026 kullanıcı isteği.



- [ ] Ayarlar, yeni karakter/model ekleme, ses/model düzenleme ve animasyon gibi uygulama içi alt ekranlar ayrı popup pencereler yerine ana Yumi penceresinde üst üste gelen bir ekran yığını olarak açılmalı.

- [ ] Açılışta yeni ekran yandan kayarak gelmeli; kapat/geri işleminde ters yönde yana kayıp kapanmalı ve önceki ekran görünmeli. Önceki ekranın form değerleri, seçimi ve kaydırma konumu korunmalı.

- [ ] Geçiş sırasında tekrarlı tıklama yeni kopya ekranlar açmamalı; klavye odağı yalnızca üstteki ekranda olmalı. Kapanışta ses önizlemesi ve o ekrana ait işler iptal edilmeli.

- [ ] Kullanıcının küçültme/düğme kilidi hatası yeniden oluşmamalı; hareket azaltma tercihinde animasyonsuz geçiş desteklenmeli.

- Kabul: uygulama içi bu akışlarda ikinci pencere açılmaz; açılış ve kapanış kayması tutarlı çalışır, geri dönüşte önceki ekranın durumu korunur. İşletim sistemi dosya seçicileri ve web hesabına giriş penceresi ayrı platform akışlarıdır.

- Durum: 14 Ekim uygulandı; aynı pencere, giriş/çıkış, önceki alanlar, boyut değişimi ve animasyonsuz geçiş kontrolleri geçti. Kullanıcının gerçek kullanım kabulü ayrıca açık.



### Eklenen hata: yeni karakter ekranında ses önizlemesi



İlerleme: Önizleme sohbet ses kuyruğundan ayrıldı; hazırlama/çalma/hata görünür, tekrarlı tıklama engelli, hazırlama ve oynatmayı başlatma için ayrı 8 saniyelik sınır var. Ses seçimi/pencere kapanması önizlemeyi iptal ediyor; geç gelen ses çalmıyor. Başarılı örnekler aynı ses için bellekte saklanıyor. Yerel Piper gerçek ses cihazında PlayingState ve EndOfMedia ile doğrulandı (üretim ve oynatma toplam yaklaşık 5 s); sonraki deneme önbelleği kullandı. Microsoft Ahmet/Emel servis kararlılığı hâlâ açık; bu düzeltme dış hizmeti hızlandırdığı iddiasını taşımaz.



- [ ] Yeni karakter/model ekleme ekranındaki “Sesi dinle” düğmesi 15–20 saniye gecikiyor veya hiç ses üretmiyor. Kullanıcı David karakteri, “Erkek sesi” ve “Ahmet · erkek (çevrimiçi)” seçiminde bildirdi; diğer seslerde de kontrol edilmeli.

- [ ] Ses hazırlama, servis bağlantısı ve oynatma süreleri ayrı ölçülüp gecikme nedeni giderilmeli. Hazırlanma/oynatma/hata durumu görünür olmalı; sessiz başarısızlık ve sınırsız bekleme olmamalı.

- [ ] Tekrarlanan tıklamalar birden fazla örneği sıraya yığmamalı; ses seçimi değişince veya pencere kapanınca eski önizleme başlamamalı. Seçili ses habersiz başka sesle değiştirilmemeli.

- Kabul: seçilen sesin önizlemesi gerçekten duyulur; başarısızlıkta belirli bir zaman sınırı içinde açık hata ve yeniden deneme imkânı görünür. İlk ve tekrarlanan denemelerde başlangıç gecikmesi ölçülüp kaydedilir; arayüz kullanılabilir kalır.

- Durum: açık; kullanıcı ekran görüntüsü ve 15–20 saniyelik bekleme bildirimiyle doğruladı. Ses işine dahil.



### Eklenen hata: karakter adı model listelerinde kullanılmalı



Son düzeltme: model listesi yeniden doldurulurken geçici seçim sinyallerinin isim/ses profilini yanlış modele yazması önlendi. İçe aktarılan yeni profil eski form değerleriyle ezilmiyor. Liste yenileme ve aynı modeli yeniden ekleme kontrolü geçti. Kullanıcının iki mevcut VRM'sinin daha önce Mika olarak kalmış görünen adları Clara/David olarak geri getirildi; diğer ses tercihleri değiştirilmedi.



İlerleme: Kaydedilen karakter adı, ayarlardaki model seçimi ve sağ tık menüsündeki dosya başlığının yerine kullanılıyor. Düzenleme sırasında görünen ad hemen değişiyor; model anahtarı korunuyor. İki VRM ile Clara/David, ad değişimi ve kaydedilmiş profil üzerinden liste oluşturma kontrolü geçti. Değişiklik uygulandı; kullanıcıdaki yeniden açılmış görünüm son kabul bekliyor.



- [ ] Model eklendiğinde kullanıcının verdiği ad (örneğin Clara), ayarlardaki model seçimi, model kitaplığı ve sağ tık model menüsünde gösterilmeli. Dosya adı veya VRM içindeki sayısal başlık varsayılan görünen ad olmamalı.

- [ ] Karakter adı değiştirildiğinde bütün seçim listeleri hemen güncellenmeli; yeniden açılışta ad korunmalı. Dosya kimliği ve modele bağlı ses/profil eşleşmesi aynı kalmalı.

- Kabul: kullanıcının Clara adını verdiği 4405699356021512973 modeli bütün model seçimlerinde Clara olarak görünür. Aynı adlı modeller gerekirse kısa bir ayırt edici ekle gösterilir; dosya adı yalnızca teknik ayrıntıda yer alır.

- Durum: açık; kullanıcı ekran görüntüsüyle doğruladı. Arayüz/oturum işine dahil.



| Sıra | Alan | Sıradaki somut çalışma | Kapanış koşulu | Durum |

|---|---|---|---|---|

| 1 | Canlı ses | Gemini Live native audio çekirdeği; resmî OpenAI adaptörü ayrı erişime bağlı | İnsan mikrofonuyla takip sorusu, sessizlik ve araya girme kabulü | Ayrı prototip başladı; eski web sohbeti gereği yerine geçti |

| 2 | Ses seçimi | Native sesler; ileride bağımsız kullanıcı ses adaptörü | Aynı sohbet motorunda ses/oturum geçmişi devamı; harici ses gecikmesi ve iptali ölçülür | Native Gemini uygulanıyor; eski edge/site TTS ana akışı yerine geçti |

| 3 | Mikrofon | Sürekli çift yönlü PCM, sağlayıcı VAD, aygıt ve AEC | Gerçek kullanıcı, gürültü, yankı ve sesle kesme kabulü | Yerel Whisper/Vosk zinciri ana hedef olarak yerine geçti; insan kabulü açık |

| 4 | Arayüz/oturum | Gönderim durumları, donma, model/ses/hesap kalıcılığı, uzun metin/DPI/tepsi | Yeniden açma ve pencere geçişlerinde kayıp/kilit/kesilme yok | Temizlik ve durum bildirimleri uygulandı; genel kabul açık |

| 5 | VRM uyarlaması | Kemik yönü, oran, ayak tabanı ve yüz/fizik uyumluluk raporu | Yeni desteklenen VRM elle düzeltme istemeden çalışır; uyumsuzluk açık gösterilir | Açık |

| 6 | Hareket/temas | Destek ayağı, pelvis, adım ilerlemesi ve yönlü eklem sınırları | Birkaç farklı VRM'de tam süreli yürüyüş/dönüş/temas kontrolü | Eski dans ve senaryolar kaldırıldı; yeni temel açık |

| 7 | Çarpışma/görüntü | Uzuv-gövde ve eşya teması; kumaş/aksesuar fiziği, MToon ve VRM1 | Temas ve görüntü hataları farklı VRM'lerde doğrulanmış şekilde giderilir | Açık |

| 8 | Yeni dans içeriği | Önce az sayıda tasarlanmış/lisansı uygun klip; vuruş ve ayak bilgisi | Türler görünür biçimde farklı; ayak ve gövde hareketi doğru; geçişler sıçramaz | Mevcut katalog kaldırıldı; yeni içerik başlamadı |

| 9 | Yeni senaryolar | Çekirdek davranışları giriş/yerleşme/davranış/çıkış ile yeniden kurma | Her sunulan senaryo tam süreli videoyla birkaç VRM'de kabul edilir | Eski sistem kaldırıldı; yeni içerik başlamadı |

| 10 | Müzik algılama | Yeni davranış temeli hazır olunca müzik/konuşma/video ayrımı ve tempo | Hikâye/konuşma/kendi TTS sesi dans başlatmaz | Eski tetikleyiciler kaldırıldı; yeni entegrasyon bekliyor |

| 11 | Performans | CPU/GPU/kare süresi ve modelleri karşılaştırma; sonra darboğaz düzeltmesi | Hedef donanımda yürüyüş/dans/konuşma/sürükleme için ölçülmüş akıcılık | Önceki ~33 FPS tarihi ölçümdür; yeni ölçüm açık |

| 12 | Kullanıcının modelleri | Yerel/uzak dil ve ses adaptörleri; ayrı seçilebilir kimlikler | Uyumluluk, bellek, gecikme ve iptal sözleşmesiyle doğrulanmış modeller | Arayüz sözleşmesi tanımlandı; yükleme/kurulum ertelendi, varsayılan bulut |

| 13 | Dağıtım | Yeni küçük ses çekirdeği + avatar; kişisel API kimlik bilgileri | Python/Pinokio gerektirmeyen test edilmiş paket, anahtar sızması yok | Eski yerel model içeren paketleme yaklaşımı yerine geçti; yeni kabul açık |

| 14 | Son kabul | Önce bağımsız canlı ses, ardından avatarla birlikte oturum | İnsanla aşama süreleri, takip, araya girme, uzun oturum ve bellek | İnsan canlı kabulü açık; ayrı/sentetik testler tam başarı sayılmaz |



Her iş aynı anda başlatılmış sayılmıyor. Bağımlılık sırasıyla ilerleniyor; ilk aşama uygulandı. Kısmi kontrol, tüm alanı tamamlanmış yapmaz. Yeni dans/senaryolar henüz yok ve eski başarısız içerik yeniden etkinleştirilmeyecek.



Pinokio ses denemeleri, Instagram koreografisi ve kaldırılmış kulaklık son tercihlere göre yeniden açılmadı. Yeni varlıklar için önceki erteleme sürüyor. Korunan TV/koltuk GLB'leri yeni temas sistemi hazır olunca yeniden değerlendirilebilir.



Detaylı geçmiş denetimi: Yumi-olgunluk-ve-kalan-isler.md. Oradaki mevcut özellik tablosu kaldırmadan önceki durumun tarihli kaydıdır; güncel dans/senaryo kararı bu belgededir.

