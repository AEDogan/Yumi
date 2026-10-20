# Yumi ortak temas katmanı — 15 Ekim 2026

Güncel eşya eki: `furniture_contacts.py` gerçek eşya üçgenlerinden yüzey zarfları çıkarır, `springs.py` ikincil kemikleri bunlara karşı sınırlı toplu çözer. Eşyalı sahnelerde 30 Hz/yumuşatmalı fizik kullanılır. Bu tam kumaş/üçgen CCD çözümü değildir; sınıra takılan temaslar var. Son vertex projeksiyonu uzun saçları bozduğu için varsayılan kapalıdır. Vücut ve kıyafetin bütün pozlarda eşyaların öbür yanından çıkmayacağı henüz doğrulanmadı. Ayrıntılar, testler ve ağır modelde 57,6 FPS kısa ölçüm `KALDIGIMIZ_YER.md` içinde. Minimum 100 FPS sağlanmış değildir.

Kullanıcı kararı: yeni karakter geldikçe aynı fizik sorunlarını elle tekrar düzeltmek yerine Yumi içinde ortak çözüm. Uygulanan ilk katman `contact_physics.py`, `springs.py` ve `vrm.py` içindedir. Bu teslim tüm nesnelerin üçgen yüzey çarpışmasını veya basınca göre tam kumaş katlanmasını tamamlamaz.

## Çalışan kapsam

- Desteklenen humanoid VRM'nin semantik kemik eşlemesi ve skinned bind geometrisinden otomatik 14 kapsül: kalça, gövde, göğüs, baş, iki üst/alt bacak, iki üst/alt kol ve iki avuç bölgesi.
- Ölçüler model oranlarından türetilir. Yarıçaplar skin geometrisiyle sınırlandırılır. Karakterin dosya, mesh veya özel kemik görüntü adları için model listesi yoktur.
- Yaklaşık 12 bin yüzey örneği hazırlanır, 16 bin üst sınırı vardır. Örnekleme model verisi üzerinde bellekte önbelleğe alınır; her kare yeniden mesh taranmaz. Kaynak VRM değiştirilmez.
- Poz/retarget sonrası kolun alt bölümü ve bileği gövde/baş/üst bacak hacimleriyle kontrol edilir; iki kemikli IK ile düzeltme yapılır. Uzuv uzunlukları korunur, dirsek bükümü 135 derece ile sınırlıdır. Bilek korunurken 35 derece sınır yeniden uygulanır.
- Mevcut saç/kıyafet yaylarının uçları, otomatik gövde ve el/kol hacimlerine karşı sınanır. Kemik uzunluğu ve salınım konisiyle birlikte sınırlı yinelemeli projeksiyon uygulanır.
- Birbirine aykırı kısıtlarda daha düşük penetrasyonlu çözüm seçilir; çözülemeyen temaslar `physics.unresolved` sayısında tutulur. Mümkün olmayan teması çözülmüş diye gizleyen sınırsız itme yapılmaz.
- Yayların gövdeye bağlı bağlantı noktaları için bind boşluğu korunur; bu kaba hacimlerin içine kasıtlı yerleştirilmiş kökler yüklemede patlamaz. Bu toleranslar tam yüzey garantisi değildir.
- Esnek zincirin insan iskeletindeki bağlantısı başın altındaysa ortak kumaş kararlılık profiline alınır. Böylece pelerin/omuz kurdeleleri, isimleri değişse de etek gibi 12 derece sınırını ve yüksek sönümü kullanır. Baş çevresi zincirleri ve kuyruk ayrı kalır.
- Model ekleme/değiştirme zaten `VRMModel` kurduğu için fizik hazırlığı otomatik devreye girer; kullanıcıdan karakter başına zorunlu elle ayar istenmez.

## Kontroller

`work/check_contact_physics.py`: dört yerel VRM, kapsül merkezinde sıfır mesafe, küreye indirgenen kapsül, keyfi görüntü adları, sınırlı örnekleme, iki kol zinciri, idle/walk/wave/speech pozlarında sonlu dönüşümler ve uzuv uzunlukları sınandı.

Yapay olarak içeri çevrilmiş sol kolda ölçülen en büyük kapsül penetrasyonu (modelin ham biriminde):

| Model | Önce | Sonra |
|---|---:|---:|
| 1444557518205200992 | 0,124740 | 0,002316 |
| 4107103476080737641 | 0,101405 | 0,000789 |
| 4405699356021512973 | 0,081586 | 0 |
| Sonetto | 0,036646 | 0 |

İki modelde küçük kalıntı var. Bunlar ham birimlerdir; doğrudan metre veya ekrandaki piksel olarak yorumlanmamalı. Bu test elin her parmağını veya kıyafetin bütün üçgenlerini ölçmez.

`work/profile_physics_ab.py` aynı süreçte fizik açık/kapalı eşlenmiş CPU ölçümü üretir. İlk karşılaştırmada medyan ek maliyet model başına yaklaşık 0,7–2 ms idi. `work/physics-paired-profile.json` son ölçümdür. Önce/sonra ayrı süreç ölçümleri farklı çalışma koşulları yüzünden hızlanma kanıtı sayılmaz. Bunlar toplam ekran FPS ölçümü değildir; ağır model mevcut hâliyle 100 FPS kabulünü geçmez.

Dört model için `work/physics-preview-*.png` çizimleri alındı ve incelendi. Sonetto omuz incelemesinde iç pelerin ile dış gövde yüzeylerinin aynı konumda ters normallerle bulunduğu saptandı. Dönüşüm bütün malzemeleri çift taraflı yaptığından iç yüzey dışarıdan da çiziliyordu. `Body_mat` dış yüz çizimine (`doubleSided=false`, VRM0 `_CullMode=2`) döndürüldü; diğer malzemelerin çift taraflılığı korundu. Yeniden üretilen `skins/Sonetto.vrm` doğrulandı. Dört açı/dört yürüyüş fazı karşılaştırmaları `work/sonetto/shoulders-before.png` ve `shoulders-after.png`; eski dosya `Sonetto-before-lining-fix.vrm` olarak korunur. Açık eski süreç henüz yeniden başlatılmadı; kullanıcıda yürüyüş/dönüş kabulü açık. Bu malzeme düzeltmesi genel kumaş fiziği çözümü değildir.

Konuşma jestlerinde el hedefi aşağıya/gövdeye yakına alındı. Dirsek kutbu aşağı yöneltildi ve özel konuşma kutbunu geçersiz kılan eski öne zorlama kaldırıldı. Dört model/12 niyet/24 varyant/dört zaman örneğinde toplam 4.608 hedef pozu; omuz altı dirsek, sınırlı yana açıklık ve kemik uzunlukları kontrolünden geçti. Dört gerçek çizim de alındı. Doğru avuç yönüyle el belde ve tüm hareket geçişlerinin insan kabulü hâlâ açık.

## Açık işler

1. Gerçek ayakkabı tabanı örnekleri, destek ayağı ve görev çubuğunun bulunduğu monitör/DPI bilgisiyle modelden bağımsız zemin ankrajı. Saç/etek/aksesuar alt sınırı zemin sayılmamalı. Kullanıcı bunu daha sonra kalıcı düzeltmemizi istedi; henüz uygulanmadı.
2. El belde için açık bilek/avuç yönü ve parmak temas pozu; mevcut kol kaçınması doğru el belde jesti değildir.
3. Kıyafet yüzeyleri için düşük çözünürlüklü fizik mesh'i, bükülme/esneme/sürtünme profilleri, yüzey çarpışması ve gerektiğinde kendi kendine temas. Mevcut katman kemik uçlarıyla çalışır; gerçek kumaş basınç deformasyonu değildir.
4. Eşya–eşya, el–eşya, koltuk–beden ve fincan/kitap tutuşları için ortak sahne kayıt sistemi ve temas ankrajları. Masa/koltuk/mutfak senaryoları henüz kurulmadı.
5. Hızlı hareketlerde sürekli temas, geniş giysi katmanları, modelin içinde başka giysi parçaları, animasyon geçişleri ve uzun oturumun görsel kabulü.
6. Fizik verisi veya esnek kemik bulunmayan yeni modeller için açık uyumluluk raporu. Modelin geometrisinden gerçek kumaş türü veya eksik kumaş ağı otomatik olarak kesin çıkarılamaz.

Fizik katmanı kaynak kodda etkin. Açık Yumi süreci otomatik kapatılmadı; yeni kodun kullanılması için tepsiden Çıkış ile yeniden açılması gerekir.

## Bu turdaki ayrı UI düzeltmesi

`_layout_messages()` her güncellemede önceki sabit yüksekliğin alt sınırını temizleyip metni tekrar ölçer. Önceki kod her transkript güncellemesinde iki piksel büyüyordu. Gerçek Qt testi 500 yenilemede sabit 60 px; uzun metin 842 px, kısa metne dönünce 43 px ölçtü. Dar pencere kontrolü de geçti. `work/check_chat_bubble_height.py`.
