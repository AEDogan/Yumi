# Yumi için 3D eşya indirme listesi

Güncel senaryo ve mevcut/eksik eşya kaydı **`YUMI_SENARYO_LISTESI.md`** içindedir. İlk paketin çoğu artık içeri alındı: 20 benzersiz GLB, 5 koltuk, 2 sehpa, sabit PC seti, kitap/TV/kumanda/kupa/patlamış mısır. Aşağıdaki tablolar ilk kaynak arama listesidir; aynı eşyaları yeniden indirmek gerekmez. Sahne hareketlerinin tümü henüz uygulanmadı.

## İlk indirilecek paket

| Eşya | Adet | Kullanım | Aramada kullanılabilecek ifade |
|---|---:|---|---|
| Tek kişilik geniş koltuk | 1 | Çapraz oturma, bacak bacak üstüne atma, kitap, esneme, TV | stylized armchair low poly |
| Bilgisayar masası | 1 | Yazı yazma, çalışma ve toplantı | stylized computer desk |
| Çalışma sandalyesi | 1 | Masa başında oturma | low poly office chair |
| Monitör ve ayrı ayak | 1 | Yazı yazma / toplantı | stylized desktop monitor |
| Klavye | 1 | Tuşlara basma | low poly keyboard |
| Fare | 1 | Bilgisayar kullanımı | low poly computer mouse |
| TV ve TV sehpası | 1 takım | Koltukta film/dizi izleme | stylized television stand |
| Kumanda | 1 | Arada düğmeye basma | low poly remote control |
| Kitap | 1 | Oturarak okuma, sayfa çevirme | rigged book page turn |
| Küçük yan sehpa | 1 | Kitap, kupa, kumanda bırakma | stylized side table |
| Kupa | 1 | Kahve içme, masaya bırakma | stylized coffee mug |
| Patlamış mısır kasesi | 1 | 10 dakikadan uzun filmde atıştırma | low poly popcorn bowl |
| Ayrı patlamış mısır taneleri | 2–3 biçim | El ile alıp ağza götürme | popcorn kernel 3d |

Koltuk ilk öncelik: geniş, mümkünse kolçakları alçak veya aralıklı olsun. Dar/kollukları yüksek koltuk, farklı modellerin kollarına ve çapraz bacaklarına çarpabilir. Oturak, sırt ve kolçak geometrisi seçilebilir olursa temas ayarı kolaylaşır.

## İkinci paket: uzun mola ve kahve

| Eşya | Adet | Gerekli ayrım |
|---|---:|---|
| Küçük mutfak tezgâhı ve alt dolap | 1 | Bütün oda yerine dar bir modül yeterli |
| Kahve makinesi | 1 | Kupa yuvası ve düğmeler erişilebilir; hareketli kol varsa ayrı parça |
| Kahve paketi / çekirdek kavanozu | 1 | Kapak ayrı olursa açılabilir |
| Kaşık | 1 | Ayrı nesne |
| Küçük tepsi | 1 | Ayrı nesne |
| Bağımsız pencere çerçevesi / pencere modülü | 1 | Cam, çerçeveden ayrı malzeme; duvarın küçük kısmı yeterli |
| Bar taburesi | 1 | İsteğe bağlı; kahve sonrası oturma |
| Su bardağı ve su şişesi | 1 takım | Kapak ayrı; kısa su molası |

Kahve içmek için ilk paketteki kupayı tekrar kullanırız. Kahve makinesinin gerçek sıvı simülasyonu gerektirmeyen bir modeli yeterli; sıvı ve buharı sonradan efekt olarak ekleyebiliriz.

## Üçüncü paket: ek senaryolar

| Eşya | Kullanım |
|---|---|
| Kulaklık | Müzik ve online toplantı; kafa bandı/kulaklıkların ayarlanabilmesi tercih |
| Küçük hoparlör çifti | Müzik sahnesi |
| Oyun kumandası | Pencereli oyun veya oyun molası; tam ekran oyunda modelin çizimi durur |
| Dizüstü bilgisayar | Koltukta çalışma; ekran ve taban ayrı pivotlu |
| Tablet / e-kitap okuyucu | Koltukta alternatif okuma |
| Telefon | Kısa bildirim tepkileri |
| Defter ve kalem | Not alma; defter kapağı ayrı olabilir |
| Masa lambası | Çalışma / okuma; ışığı biz ekleyebiliriz |
| Küçük çalışma mikrofonu | Toplantı / yayın |
| Atıştırmalık paketi | Filmde çeşitlilik; açık ve kapalı iki sürüm yeterli |
| Küçük çöp kutusu | Atıştırma / kahve sonrası toplama |
| Minder ve ince battaniye | İsteğe bağlı; battaniye kumaş temas sistemi gerektirdiği için sonraya kalsın |

Danslar için eşya şart değil. Dans animasyonu, VRM parmak/iskelet uyumu ve müzik ritmi algılama ayrı işlerdir. Sahneye koltuk, masa veya mutfak gelmesi de oturma/nesne tutma animasyonunu kendiliğinden sağlamaz.

## İndirirken teknik seçim

- Tercih: **GLB/glTF**. **FBX + dokular** veya **BLEND** de dönüştürme için kabul edilebilir. Bunlar eşya kaynağı formatlarıdır; Yumi'nin mevcut karakter seçicisi `.vrm` içindir. Eşya yükleyicisi ayrıca eklenecek.
- Aynı paketin stylized / anime / low-poly eşyaları daha tutarlı görünür. Fotoğraf gerçekçiliğinde ağır bir oda paketi gerekmiyor.
- Hareket edecek parçalar ayrı mesh olmalı: kitap kapağı/sayfalar, laptop ekranı, kahve kolu, dolap kapağı. Birleşik tek mesh hareketi zorlaştırır.
- **Kitap özel durum:** sadece kapalı statik kitap indirme. Açık ve kapalı hali, tercihen rig veya sayfa çevirme animasyonu bulunsun. O yoksa ayrı sayfalarla biz hazırlarız.
- Model ölçüsü biliniyorsa metre ölçeğinde olsun; koltuk oturma yüksekliği yaklaşık 40–50 cm, masa yüksekliği 70–75 cm başlangıç için uygundur. İskelet ölçülerine göre sonradan uyarlanacak.
- Başlangıç bütçesi: küçük eşyada yaklaşık 500–5.000, mobilyada 2.000–15.000 üçgen; tek bir modelde yüz binlerce üçgen gereksiz. Bunlar başlangıç hedefleri, ölçümle ayarlanacak.
- Dokular çoğunlukla 1K, önemli parçalarda 2K yeterli. UV ve temel renk dokusu olsun. Özel Blender/Unreal shader'ına bağlı görünüş, GLB'ye birebir taşınmayabilir.
- Pivotlar uygun olsun: dönecek kapak menteşesinde; masa/koltuk zeminde; tutulan eşyada tutuşa uygun merkez. Uygun değilse düzeltilebilir.
- Basit çarpışma geometrisi varsa al; yoksa eşya için ayrıca hazırlayacağız. Çarpışmalı model indirmek, kumaş veya el temasının her durumda çözülmesi anlamına gelmez.
- Ticari kullanım ve uygulama içinde yeniden dağıtım iznini kontrol et. Kaynak bağlantısı, üretici adı ve lisans dosyasını modelin yanında tut. “Ücretsiz” olması dağıtım izni anlamına gelmeyebilir.

Her model için kendi adıyla bir klasör açıp model, dokular, lisans ve kaynak bağlantısını birlikte sakla. İlk 13 satır öncelikli; hepsini birden indirmen gerekmiyor.
