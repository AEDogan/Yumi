# Yumi FPS incelemesi — 16 Ekim 2026

## Sonuç

Ana darboğaz, fizik ve iskelet hesaplarının çizimle aynı Qt arayüz iş parçacığında çalışması. Ekran kartı doğru kullanılıyor; GPU skinning açık, CPU skinning fallback'i kapalı. Uzun fizik adımları çizimi bekletiyor. CPU çekirdeği seçimi de sonucu ciddi etkiliyor.

Önceki 46 FPS kısa bir ölçümdü; bilgisayarın kapasite sınırı olarak yorumlanmamalı. Normal çekirdek seçimli koşularda yaklaşık 32–80 FPS görüldü. Eski kayıtlar çekirdeği izlemediği için bu değişimin tamamını P/E seçimine bağlamak doğru olmaz.

Bu incelemede üretim kodu ve kalıcı sistem ayarları değiştirilmedi. Fizik kapatma, hareket dondurma, tampon sıkıştırma ve CPU sabitlemesi yalnız ayrı test süreçlerine uygulandı. Ana Yumi, mikrofon ve bulut sohbeti açılmadı.

## Donanım ve ölçüm koşulları

- Intel Core i7-14700F: 20 çekirdek, 28 mantıksal işlemci; yaklaşık 32 GB RAM.
- AMD Radeon RX 9070 XT; WMI sürücü sürümü 32.0.32015.2008. OpenGL renderer aynı GPU, OpenGL 4.6 Compatibility, 26.9.2.260915.
- Ekran 200 Hz. Kod swap interval 0 ve 4 sample istiyor; gerçekleşen context 1 ve GL_SAMPLES=0 bildirdi. İstenen ayarlar gerçekleşmiş kabul edilmedi.
- Sahne: Leyla `4107103476080737641.vrm`, PC masası/sandalyesi, 400×440 viewport, sakin oturuş, saç/kıyafet fiziği 15 Hz. Görsel detay azaltılmadı.
- Isınmadan sonra yaklaşık dört saniyelik koşular sırayla ölçüldü. Bunlar uzun stres testi veya minimum FPS garantisi değildir.
- Windows CPU Set API: mantıksal 0–15 sınıf 1, 16–27 sınıf 0. Daha yüksek EfficiencyClass daha hızlı işlemci sınıfını belirtir: [Microsoft belgesi](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-system_cpu_set_information). Kontrollü P denemesi yalnız GUI thread CPU 0, E denemesi CPU 16 üzerindedir.
- GPU zaman sorgusu, modelin çizim komut aralığıdır; CPU komut gönderim boşluklarını da kapsayabilir. Saf rasterizer zamanı veya GPU kullanım yüzdesi değildir. CPU ve GPU süreleri örtüşebildiğinden toplanmaz.
- cProfile ayrı koşuda alındı; onun FPS'si optimizasyon kazancı olarak kullanılmadı. Isınma veya paralel metadata taramasıyla karışabilen erken koşular kontrollü tabloya alınmadı.

## Kontrollü sonuçlar

| Koşul | Ortalama FPS | Kare süresi p95 | paintGL ortalaması |
|---|---:|---:|---:|
| P çekirdeği, bütün hesaplar açık | 86,31 | 24,14 ms | 11,10 ms |
| E çekirdeği, bütün hesaplar açık | 23,99 | 63,37 ms | 41,14 ms |
| P çekirdeği, yalnız saç/kıyafet fiziği kapalı | 102,73 | 11,15 ms | 9,15 ms |
| P çekirdeği, hareket hesapları donuk, aynı 3D geometri çiziliyor | 179,93 | 6,49 ms | 3,90 ms |
| P çekirdeği, şeffaf masaüstü penceresi ve tıklama maskesi | 74,06 | 27,55 ms | 12,69 ms |

Saç/kıyafet fiziği kapalı satırda oturma/bacak IK, kol teması, animasyon ve yüz hesabı çalışmaya devam eder. Dondurulmuş satır gerçek 3D geometriyi çizer; iki boyutlu ekran görüntüsü değildir. Bu satırlar yalnız teşhis kontrolleridir.

Ham kayıtlar `work/fps-cpu-p-core.json`, `fps-cpu-e-core.json`, `fps-p-core-no-physics.json`, `fps-p-core-frozen.json`, `fps-p-core-overlay.json`.

## 1. Uzun fizik adımları — en önemli bulgu

`avatar.py:170` içindeki paintGL, önce `model.frame`, sonra çizimi çağırır. `vrm.py:505–510` oturma, kol, saç/kıyafet ve temas hesaplarını aynı iş parçacığında tamamlar. Diğer CPU çekirdekleri boş olsa bile bu ardışık yol kendiliğinden paralelleşmez.

P çekirdeğinde model.frame ortalaması 7,45 ms; bunun içindeki secondary apply ortalaması 2,81 ms. Ancak fizik çözüldüğü tek adım ortalama 14,66 ms, p95 14,98 ms sürüyor. Şeffaf overlayde tek adım 16,42 ms, E çekirdeğinde 39,28 ms.

100 FPS için bütün kare 10 ms; 60 FPS için 16,67 ms olmalı. Tek fizik adımı bu bütçeye yaklaşıyor veya aşıyor, ardından animasyon/çizim geliyor. Fizik 15 Hz olsa da çalıştığı kareyi bloke ediyor. Bu yüzden ortalama 86 FPS ile birlikte p95 24 ms kareler görülebiliyor. Ortalama FPS ve düzgün kare dağılımı ayrı hedefler.

Son serbest çekirdek seçimi koşusu yaklaşık 80 FPS verdi; örnekler çoğunlukla P çekirdeklerindeydi. P/E deneyi çekirdek sınıfına duyarlılığı kanıtlıyor, önceki 46 FPS ölçümünün mutlaka E çekirdeğinde olduğunu kanıtlamıyor.

## 2. Küçük Python/NumPy işlemlerinin toplam maliyeti

Gerçek kare döngüsünün cProfile kaydında yaklaşık dört saniyede 4,38 milyon çağrı var. Yaklaşık 209 kare ve 53 fizik adımında:

| Bölüm | Kümülatif süre | Çağrı |
|---|---:|---:|
| model.frame | 2,871 s | 209 |
| secondary apply, model.frame içinde | 1,307 s | 209 |
| secondary simulate, apply içinde | 1,217 s | 53 |
| constrain_tip | 0,530 s | 5512 |
| joint limits | 0,517 s | 10032 |
| VRM draw | 0,698 s | 209 |
| Mobilya çizimi | 0,252 s | 418 |
| Mobilya yay teması | 0,216 s | 53 |

İç içe süreler toplanmaz. Yalnız yeni mobilya katmanı değil; beden kapsülleri, yayların yinelemeli teması, joint limitleri ve küçük matris/vektör işlemleri birlikte maliyet oluşturuyor. NumPy kullanılması Python kontrol döngüsünü otomatik olarak toplu bir çözücüye dönüştürmüyor.

Authored klipten önce prosedürel poz hesaplanıp bazı sonuçlarının atıldığı yol da var. Bu koşuda `MotionRig.sample` toplam yaklaşık 0,060 s; temizlik adayı ama ana darboğaz değil. Profil: `work/fps-cpu-profile.pstats` ve `work/fps-cpu-profile-hotspots.txt`.

## 3. Çizim ve veri düzeni — ikincil yük

P çekirdeğinde karakter çiziminin CPU gönderim süresi yaklaşık 2,59 ms, mobilyanın 0,84 ms. Model GPU komut aralığı yaklaşık 1,67 ms. Aynı geometri hareket donukken yaklaşık 180 FPS çizilebiliyor.

GPU skinning var, fakat kalıcı mesh VBO/EBO yolu yok: `vrm.py:712–748` ve `item_assets.py:116` NumPy client array adresleriyle çiziyor. Her malzeme parçasında state/uniform/texture çağrıları ve küçük dizi oluşturma var. Gerçek PCIe aktarım miktarı ölçülmedi; bütün kaynak tamponun her kare aynen taşındığı iddia edilmiyor.

| Model | Üçgen | Malzeme primitive | Konum tamponu kayıtları toplamı | Primitive başına referanslı vertex | Spring node |
|---|---:|---:|---:|---:|---:|
| David | 39556 | 17 | 104084 | 29109 | 25 |
| Leyla | 181335 | 32 | 1042635 | 115559 | 104 |
| Eddy | 28515 | 89 | 685560 | 20240 | 41 |
| Sonetto | 42622 | 5 | 33377 | 30532 | 58 |

Kayıtlar primitive'ler üzerinden toplanır; farklı parçalarda aynı fiziksel nokta paylaşılabilir. Düşük üçgen sayısı tek başına düşük CPU gönderim maliyeti demek değildir.

Test kopyasında Leyla'nın tamponları 1042635 → 115559 kayda indirildi; her üçgenin konumu aynen korunduğu doğrulandı. Ancak tek başına FPS kazancı tutarlı tekrar üretilemedi: fizik kapalı normal 76,23; kompakt 71,61 FPS. Fizik açık kompakt 56,53 FPS verdi ama o koşuda fizik adımı maliyeti de değişti. Bellek/veri düzeni kazancı açık, FPS çözümü henüz kanıtlanmış değil. Üretim loaderına uygulanmadı.

## 4. Şeffaflık ve diğer olasılıklar

- Gerçek overlayde async PBO çalışıyor; grabFramebuffer fallback'i yok. P çekirdeğinde alpha-mask güncellemesi ortalama 0,714 ms, p95 0,972 ms. Ana darboğaz değil. Serbest çekirdekli maskeli 42,13/maskesiz 46,53 FPS farkının tamamı maskeye atfedilmez; bu ikisinin CPU dağılımı kaydedilmedi.
- Gizli ikinci AvatarView'in timer'ı durdurulmuş. İki model nesnesi bellekte bulunabilir; iki sürekli renderer kanıtı yok.
- Retarget matrisleri ve dokular zaten önbellekli. Her kare yeniden doku çözülmüyor.
- Geçiş SVD işlemleri kısa geçiş penceresindedir; sabit oturuştaki bütün düşüşü açıklamaz.
- NumPy/OpenBLAS varsayılan 24 thread kullanıyor. Tek thread denemesi tutarlı kazanç vermedi; yalnız thread sayısını 1 yapmak çözüm olarak önerilmiyor.
- VSync/kompozisyon etkisi tamamen dışlanmadı. Gerçek context swap 1 bildiriyor; kodda 46 FPS sınırı yok. Sürücü ayarları değiştirilmedi.

## Uygulama öncelikleri

1. **Fiziği çizimin kritik yolundan ayır:** ayrı süreç veya toplu/native hesap; son tamamlanmış pozu zaman damgasıyla interpolate ederek çiz. Yalnız Python threadine taşımak yeterli olmayabilir. Eski temas verisi ve oturma geçişleri ayrıca doğrulanmalı.
2. **Fizik/iskelet işlemlerini toplulaştır:** bağımsız yaylar, kapsül testleri ve joint limitleri. Mevcut temas davranışı korunmalı; kontrolleri kapatmak optimizasyon sayılmamalı.
3. **Kalıcı GPU tamponları ve malzeme önbelleği:** statik vertex/normal/UV/joint/index verileri VBO/EBO; değişen morphlar için sınırlı güncelleme. Geometri, UV, skin ve morph eşitliği test edilmeli.
4. **Gerçek uygulamada CPU zamanlamasını izle:** kontrollü P/E sonucundan uygulamanın tamamını kalıcı tek çekirdeğe sabitleme sonucu çıkarılmamalı. Arka plan ve oyun koşulları da ölçülmeli.
5. **Uzun kabul koşusu:** aynı model/sahne/ölçekle ortalama, p95/p99, arayüz gecikmesi, CPU sınıfı ve GPU yolu birlikte kaydedilmeli. Minimum 100 FPS hâlâ doğrulanmış değil.

Tekrar üretim: `work/diagnose_fps.py`. CPU topolojisi: `work/cpu_topology.py`. Bağımsız statik inceleme: `work/fps-static-review.md`.
