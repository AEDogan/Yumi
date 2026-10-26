# 3. başlık — günlük senaryo yaşam döngüsü

26 Ekim 2026. Kullanıcı uzun ses testi sürerken bu başlığın paralel yürütülmesini istedi. Tek ajan kullanıldı. Skin/görünüm çalışması yapılmadı.

## Uygulanan düzeltmeler
- Uygun koltuk veya yerel varlık bulunamadığında henüz oluşturulmamış sahne üzerinde release çağrılması engellendi. Asıl hata durum mesajında korunuyor; 30 saniyelik yeniden deneme beklemesi çalışıyor.
- Karakter yaklaşma/geliş/dönüş sırasında iptal edilirse artık oturma ve eşya alma akışına devam etmiyor. Yalnız daha önce yürüdüğü rota noktalarından geri dönüyor; görünürlük artmadan sahne kapanıyor.
- Henüz kullanılmamış senaryonun eşyası için yapay taşıma/bırakma animasyonu başlatılmıyor. Kısmi oturma/masa hazırlığı iptalleri mevcut güvenli kalkış akışını izliyor, kullanılmamış eşya alma adımı atlanıyor.
- Tekrar iptal çağrıları dönüşü sıfırlamıyor. Yeni senaryo, eski sahne temizlenene kadar bekliyor; son istek uygulanıyor.
- Oturmuş ve eşya kullanmaya başlamış senaryolarda fiziksel eşya bırakma akışı korunuyor.

- Bitmiş sahnenin avatar tarafından bırakılan eski referansı, otomasyon kapalı/gizli/bastırılmışken de temizleniyor; ikinci release çağrısı yapılmıyor.

## Doğrulama
İki yeni test önce eski kaynakta başarısız oldu. Yeni testler yapıcı/varlık hatası, kısmi oluşturma temizliği, bekleyen istek değiştirme, iptal bastırması, devre dışı/gizli/bastırılmış durumda bitmiş sahne referansını temizleme ve erken/oturmuş iptal ayrımını kapsıyor.

Gerçek yerleşik Yumi modeli üzerinde dokuz senaryo × geliş/yürüyüş/dönüş = 27 erken iptal geçti. Oturma, konum sıçraması, iptal sırasında eşya alma, takılı kalan çıkış veya eski model varlığında değişiklik gözlenmedi. Dokuz senaryonun normal eşya bırakma/çıkışı da geçti: dinlenme, yazma, kodlama, gezinme, okuma, TV, toplantı, kahve, pencere. Kontroller sonlu pozları, kemik uzunluğunu, zemin ve eşya yüzey desteğini de içeriyor.

Gerçek Qt/three-vrm kontrolünde renderer_ready ve renderer_delivered true; iptal sonrası yalnız leave/depart aşamaları görüldü, sahne/oturma bağları temizlendi. İlk ekran dışı deneme kare üretmedi; test harness'ında framebuffer çizimi zorlandıktan sonra geçti. Görseller senaryo-iptal-oncesi.png ve senaryo-iptal-sonrasi.png.

Önceki tam model matrisi 120/120 geçmiş kaydıdır; bu tur bütün modeller tekrar doğrulandı sayılmaz. Giysi/saç/deri teması ve estetik kabul bu işin kapsamında değildir.

## İlgili dosyalar
Üretim: daily_scenarios.py, furniture_scene.py, scenario_activity.py. Yedekler sohbet work/core-runtime/scenario-lifecycle/ altında .before.py dosyalarıdır. Tekrar üretim: check_scenario_lifecycle.py, check_scenario_early_cancel.py, check_scenario_real_cancel.py ve render_scenario_cancel.py. Kanıt JSON dosyaları bu raporun yanındadır. Açık kullanıcı uygulaması yeniden başlatılmadı.
