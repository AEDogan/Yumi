# Yumi — ana senaryo listesi

Güncelleme: 15 Ekim 2026. Bundan sonra senaryolar ve kalan işler için ilk bakılacak dosya budur. Ayrıntılı hareket/müzik tasarımı `YUMI_DAVRANIS_TASARIMI.md`, teknik devam noktası `KALDIGIMIZ_YER.md` içindedir. Bu liste gelecekte yapılacakları da içerir; bütün satırlar çalışıyor anlamına gelmez.

**Yeni indirilecek modellerin öncelikli listesi: `YUMI_EK_ESYA_LISTESI.md`.** Kahve makineleri, pencereler, kulaklıklar ve diğer 17 aday alındı; optimize kopyaları `items/alternatives` altında. İlk eksik mutfak tezgâhı; yeni eşyalarda tutuş/temas bağlama bekliyor.

## Son kullanıcı bildirimleri ve ortak düzeltmeler — 16 Ekim

- **SON KAPSAM:** kullanıcı FPS'i bekletip dans/otomatik günlük akışları yeniden istedi. İlk çalışan sürüm sağ tık menüsü ve ses/yazı komutlarına bağlandı. Güncel uygulama, kullanım ve kesin sınırlar `YUMI_GUNLUK_MUZIK.md` içinde. Aşağıdaki eski “plan/bekliyor” satırlarında yeni duruma göre şu farklar var: S02yazma/fare, S05kaynak kitap animasyonu, S06TV, S07kase/lokma, S08sade toplantı/defter, S09çıktıritmi/dinleme, S10ses saatli dans, S13/14otomatik eşik, S15hafif esneme, S16/17kahve/pencere temel sürümleri artık var. Tam diz üstü bacak çaprazlama, kulaklık uydurma, fiziksel elden-sehpaya bırakma, sesten tür sınıflandırma ve gerçek müzikte son kabul hâlâ açık. S18kapanış şu an kitap kapatma/yumuşak sönme+normal çıkış; fiziksel bırakma tamamlanmış sayılmaz.

- **PC görünümü ve göz teması:** oturuş -40° ile kullanıcıya daha açık; monitör yüzü örtmemesi için yana alındı, göz hizası/klavye ergonomisi korunuyor. Oturarak konuşurken gövde sabit, baş/boyun toplam42° sınırıyla kullanıcıya yumuşak yönelir; konuşma bitince geri döner. Dört modelde görsel, baş sınırı ve masa ergonomisi kontrolleri geçti.

- **Jest iyileştirmesi:** bel hedefi modelin gövde örneklerine göre ölçülüyor; kol hareketleri daha küçük/asimetrik. Oturarak konuşmada el hedefleri omuz, diz ve klavye yüksekliğine uyarlanıyor; nötr önkol çerçevesi ve oturma sonrası geçiş sıçramayı önlüyor. Dört modelde altı jestin ayakta ve iki oturma bağlamındaki eklem/uzunluk/geçiş kontrolleri geçti. Tam kıyafet/mobilya çarpışma kabulü ayrı açık iş; manuel eylemlerin önce kalkış kuralı korunur.

- **Son kapsam:** Ludovisions eklenmeyecek; oradan yalnız ifade/retarget bilgisi kullanılacak. Yeni `furniture__no-27` ve `mid_century_lounge_chair` ölçülüp aktif rastgele havuza eklendi. Ayrıntılı güncel teknik kayıt `KALDIGIMIZ_YER.md` başındadır.
- Kalça kökü/üst bacak eklemi farkı ve gerçek kıyafetli uyluk hacmi oturma hesabında; sandalye kenarları gerçek yüzey outline'ından ölçülüyor. Ortak vertexbuffer kullanan parçalarda yalnız çizilen indeksler ölçülüyor. Çok katmanlı yerel mobilya teması ve sınırlı gerçek kıyafet örnekleri var; tam kumaş/soft-body kabulü hâlâ açık.

- **Öncelikli açık hata:** PC sandalyesine oturma/kalkma sırasında bacakların sandalye içinden geçmesi. Yaklaşma rotası, oturma/kalkma boyunca bacak ve sandalye temasının sürekli ölçülmesi gerekiyor; tam çözüm kabulü yapılmadı.
- **Koltuk içinde model/dizlerin aşırı yukarı çıkması:** koltuğu sığdırmak için oturma yüksekliğini düşüren ölçek kısılması kaldırıldı. Bacak yüksekliğinde fazla derin kalan aday karakter için reddedilir. Dört karakterde taban, kemik uzunluğu ve kesintisiz giriş/çıkış kontrolleri geçti; tam kumaş kabulü değildir.
- **Sehpa–koltuk kesişmesi:** minder genişliği yerine koltuğun dış çerçevesinin dönüştürülmüş sınırları kullanılıyor; yan sehpayla en az 15 cm model birimi boşluk denetleniyor.
- **Siyah kutu koltuk `armchair_skin`:** aktif kütüphaneden çıkarıldı; proje kopyası arşivlendi, kullanıcının kaynağı korunuyor.
- **Eylemler arası geçiş:** koltuktayken PC, yön, el hareketi, dans veya karakter komutu verilirse önce mevcut kalkış/çıkış tamamlanır, sonra komut bir kez uygulanır. Yeni komut önceki bekleyeni değiştirir; dur/kalk bekleyeni iptal eder. Sohbet etmek zorunlu kalkış başlatmaz.
- **Ortak model incelemesi:** `model_analysis.py` karakter ve eşya yükleyicisine bağlandı. Anatomi/kemik/morph/spring kanıtı, belirsizlik ve sanal bölge maskeleri var; fiziksel kumaş/sertlik tahmini otomatik kesinleştirilmez. Ayrıntı `YUMI_MODEL_ANALIZI.md`.

## Kararlaştırılan mobilya seçimi

- **Dinlenme koltuğu:** her yeni oturma sahnesi başlarken karakter ölçülerine uygun adaylardan rastgele seçilir. Aktif kütüphanede 6 aday vardır; uygunluk nedeniyle her karakter hepsini kullanmaz. Bir önceki koltuğun dışında uygun aday varsa aynı koltuk arka arkaya seçilmez. İki yeni aday dört karakter ölçüsünden ve David/Sonetto oturma önizlemesinden geçti; bütün kumaş temasları için genel garanti yoktur.
- **Yan sehpa:** her yeni dinlenme sahnesinde mevcut 2 sehpadan rastgele seçilir. Aynı sehpanın arka arkaya gelmesi şu an mümkündür.
- **Sahne sürerken seçim korunur:** karakter otururken koltuk/sehpa birden değişmez. Yeniden seçim, sahne kapatılıp yeni oturma başlatıldığında yapılır.
- **PC masası:** kullanıcı mevcut modeli beğendi; `pc_desk_set` sabit set olarak korunacak. Masa/sandalye/ekran/klavye ölçüleri her karakterin anatomisine uyarlanmaya devam eder. Setin sabit olması tek bir fiziksel ölçünün bütün karakterlere zorlanması demek değildir.
- **Mevcut arayüz durumu:** rastgele koltuk/sehpa seçimi kodda aktiftir; ayrı bir “Rastgele / Sabit” ayar anahtarı henüz yoktur. İleride böyle bir tercih ekranı eklenirse varsayılan koltuk/sehpa rastgele, PC seti sabit olacak. Sabit seçilen uygunsuz mobilya için güvenli uyum kontrolü korunacak.
- Diğer sahnelerde de koltuk/sehpa kullanıldığında aynı seçim kuralı paylaşılacak. Karakter filmden kısa konuşmaya geçti diye bütün dekor yeniden çekilmeyecek.

## Ana senaryolar

| Kimlik | Senaryo | Yumi ne yapacak? | Eşya durumu | Uygulama durumu |
|---|---|---|---|---|
| S01 | Kullanıcıyla sohbet | Bakış, yüz ve doğal el/kol jestleri; oturuyorsa konuşmak için zorunlu kalkmaz | Zorunlu eşya yok | Temel sohbet/jestler var; otururken jest–eşya teması geliştirilecek |
| S02 | Yazı yazma / mail / chat | PC başına yürüyüp oturur; klavyede yazar, düşünürken kısa durur, fareye geçer | Sabit PC seti, klavye ve fare hazır | Otomatik yazma seçimi, parmak/bilek ve fare döngüsü var; hassas tuş teması kabulü açık |
| S03 | Kodlama / yoğun çalışma | PC'de odaklanma, düşünme ve küçük bakış araları | Aynı PC seti | `kod yaz` ve uygulama algılama var; diğer PC modlarına aynı masada geçer |
| S04 | Web / haber / uzun metin okuma | Sakin okuma, seyrek fare/scroll | PC seti hazır | `webde oku` ve otomatik tarayıcı davranışı var; yazma gibi sürekli parmak oynatmaz |
| S05 | Koltukta kitap okuma | Kitap tutma, kaynak sayfa ve kapama animasyonu; yatay sehpaya bırakma | Uygun geniş sehpa ve kitap hazır | Fiziksel taşıma/bırakma dört modelde geçti; tam diz üstü bacak çaprazlama açık |
| S06 | Film / dizi / TV izleme | Koltukta TV'ye bakar, seyrek kumanda hareketi | Koltuk, sehpa, TV, TV sehpası ve kumanda hazır | Medya/komut seçimi, yerleşim ve temel hareket var; TV yayını kopyalanmaz |
| S07 | Uzun filmde atıştırma | 10 dakika sonra kucakta kase, 30–40 saniye arayla lokma | Kase ve ayrı patlamış mısır hazır | Temel döngü var; konuşurken yeme vurgusu kesilir; hassas parmak/yiyecek teması açık |
| S08 | Online toplantı / ders / sunum | Sakin PC oturuşu, deftere bakış ve başla onay | PC/defter hazır; iki kulaklık alındı | Defter tutuşu ve bırakma var; kulaklık kafa/saç uyarlaması açık |
| S09 | Müzik dinleme | Oturarak veya ayakta sakin ritim eşliği | Çıkış loopback ve yerel tür modeli hazır | Medya/elle seçim + yerel28 aile tahmini; bachata/Latin pop etiket/elle seçim; kapsamlı doğruluk kabulü açık |
| S10 | Müzikle dans / direk dansı | 20 türde12'şer adım/kol birleşimi;32 vuruşluk cümleler, en hızlı tempoda2dk40sn temel figür tekrarı yok; kısa aradan kaldığı bölümde devam | Normal dans eşyasız; direk dansında ölçüye göre yerel direk | Dört modelde20 tür, avuç teması, destek ayağı ve kontrollü çıkış testli; prosedürel tür esinleri, profesyonel mocap değil; canlı müzik kabulü açık |
| S11 | Tam ekran oyun | Karakter ve sahne çizimini/fizik zamanlayıcılarını durdurur; oyun bitince önceki duruma döner | Eşya gerekmez | Koruma uygulandı; gerçek oyunlarla kapsamlı kabul açık |
| S12 | Pencereli oyun / oyun molası | Sakin eşlik; isteğe bağlı kumandayla oyun pozu; tam ekran korumasına uyar | PC seti hazır; el oyun kumandası eksik | Plan; ekran üstünü kapatan otomatik büyük sahne açılmayacak |
| S13 | Kısa bekleme | İlk 150 saniye sakin bekleme | Eşya gerekmez | Otomatik yöneticiye bağlı; pasif medya/toplantı boşta sayılmaz |
| S14 | Uzun işlem / indirme bekleme / dinlenme | 150 saniye sonrası koltuğa yürür, dinlenir | Rastgele koltuk/sehpa hazır | Otomatik eşik ve ölçülü ayak bileği çaprazlama var; tam diz üstüne bacak çaprazlama açık |
| S15 | Oturarak esneme / gevşeme | Oturduğu yerde esneme, göz/yüz, omuz gevşetme ve küçük duruş değişikliği | Mevcut koltuğu korur | Tekrarsız ara hareketler var; konuşma sırasında geri çekilir, esneme için kalkmaz |
| S16 | 10 dk+ gerçek mola — kahve hazırlama | 600 saniye boşta kalınca köşeye yürür, yaklaşık20 saniye hazırlık | Makine, kupa ve basit uygulama tezgâhı | Temel ayakta akış var; makine düğmesi/avuç/yüzey teması ince kabulü açık |
| S17 | Kahveyle pencere başında dalma | Hazırlık sonrası pencereye yönelir, seyrek yudum | Kupa/pencere hazır | Temel yönelme/yudum ve ayrı komut var; fiziksel kupa bırakma açık |
| S18 | Kullanıcının geri gelişi / seslenmesi | Kitap kapama, eşya taşıma/bırakma, temas çözme, kalkış/yürüme; dekor en son çıkar | İlgili sahnenin eşyaları | Ortak fiziksel bırakma ve lokma sırasında kesilme dört modelde geçti; tam kumaş garantisi değildir |

## Daha sonra değerlendirilecek ekler

Bunlar ana akışlar bittikten sonra ele alınabilecek önerilerdir; kendiliğinden devreye alınmayacak.

| Kimlik | Ek senaryo | Gerekli ekler |
|---|---|---|
| E01 | Su molası | Bardak/şişe, tutuş ve yudum hareketi; drinkware paketinin uygun parçaları incelenecek |
| E02 | Çizim / tasarım / yaratıcı çalışma | PC sahnesiyle başlanabilir; ayrı çizim tableti veya defter/kalem daha sonra |
| E03 | Koltukta laptop / tablet / e-kitap | Laptop/tablet modeli, diz–eşya–el teması |
| E04 | Gece dinlenmesi / uyuklama | İlk tercih rahat koltukta oturarak uyuklama; önceki yere uzanma/yatak yaklaşımı otomatik geri açılmayacak |

## Uygulama sırası

1. **Ortak zemin, ergonomi, vücut/kıyafet–eşya teması ve performans.** Tam kumaş kesişmesizliği henüz doğrulanmadı; ağır eşyalı sahne performansı açık. Bu eksikler senaryo çoğaltılarak gizlenmeyecek.
2. **PC hareketleri:** S02–S04, ardından S08'in sade dinleme sürümü. Mevcut sabit masa ve oturma altyapısı kullanılır.
3. **Dinlenme ve okuma:** S14–S15, ardından kitap tutuşu/sayfa çevirme ile S05.
4. **TV ve atıştırma:** S06–S07; kumanda, kase ve lokma hareketleri.
5. **Ortak kullanıcıya dönüş:** S18 her yeni senaryonun bitişine eklenir; sona bırakılan ayrı bir özellik değildir.
6. **Uzun mola/kahve/pencere:** eksik modeller geldikten ve fincan teması tamamlandıktan sonra S16–S17.
7. **Müzik ve dans:** S09–S10 aktif ve ayrı modlar. Güncel doğrulama/sınırlar `YUMI_GUNLUK_MUZIK.md` içinde; FPS bekliyor.

Bu sıra bir çalışma kaydıdır. Bu istekte yeni senaryo uygulaması veya otomatik zamanlayıcı başlatılmadı.

## Bütün sahnelerde korunacak kurallar

- Akış: sahneyi getir → yürüyerek yaklaş → dön/yerleş → davranış → tutulan eşyayı bırak → toparlan/kalk → eşyaları çıkar. Işınlanma ve temas sürerken eşya yok etme yok.
- Film, toplantı, ders ve okuma sırasında klavye/fare kullanılmaması “kullanıcı yok” sayılmaz. Böyle bir etkinlik sürerken 10 dk eşiği mutfağı tetiklemez.
- Kullanıcı geri geldiğinde bütün dekor birden kaybolmaz. Oturarak konuşmak mümkünse karakter ayakta bekleme pozuna zorlanmaz.
- Tam ekran oyun koruması bütün sahnelere üstün gelir. Dönüşte önceki duruma güvenli biçimde devam edilir.
- İlk sürümlerde açık kullanıcı seçimi/komutu esas alınır. Etkinliği otomatik algılama ayrı geliştirmedir; uygulanmış veya her uygulamada güvenilir kabul edilmez.
- Elde kitap/kupa/kumanda varken aynı ele bağımsız konuşma jesti verilmez. Yeme/yudumlama konuşmayla çakışmaz.
- Bacak bacak üstüne atma, esneme, kolçak ve kumaş temasları her uygun karakter/koltuk birleşiminde doğrulanmadan tamamlandı sayılmaz.
- Rastgelelik uygunluk kontrollerinden sonra uygulanır; dar koltuğa rastgele oturtma veya sahne ortasında mobilya değiştirme yapılmaz.
