# Yumi çalışma tercihleri

Kullanıcının açık talimatı: varsayılan olarak tek ajanla çalış; yalnızca kullanıcı açıkça takım istediğinde ekip kullan. Proje C:\Projeler\Yumi altında tutulur. Gizli bilgileri dosyalara veya çıktılara yazma.


## Kısa başlangıç ve bağlam bütçesi
- Başlangıç dosyası `DURUM.md`. Önce yalnız bunu ve kullanıcının görevini oku; ayrıntılı geçmişe görev gerektirdikçe ilgili başlıktan git. Eski devir notlarının birbirine verdiği başlangıç bağlantıları yerine bu dosyayı esas al.
- Güncel durum bir özet ve yönlendirmedir; ayrıntılı açık işler silinmiş veya tamamlanmış sayılmaz. İş bitiminde yalnız değişen durumu ve sıradaki somut işi güncelle; belgeyi yaklaşık 1–2 sayfa tut.
- Arama/çıktıyı ilgili dosya ve satırlarla sınırla. Büyük çıktıları dosyada tutup kısa sonuç döndür. Geçmiş sohbeti veya bütün plan belgelerini topluca okuma.
- Kullanıcının kapsamını tamamla; kapsam genişse işleri sırayla somut kabul ölçütleriyle bitir. Yeni gerekçe olmadan geçen kontrolleri tekrarlama. Belge/ayar değişikliğinde uygulama ekranı değişmiyorsa tarayıcı ve ekran görüntüsü gerekmez; işlev/UI değişikliklerinde mevcut kabul kuralları geçerlidir.
- Yardımcı süreç başlatmalarında süre sınırı ve kısa sağlık kontrolü kullan. Çalışan kullanıcı uygulamasını kendiliğinden kapatma.

<!-- BEGIN CODEBASE MAP -->
## Dosya haritası ve dar kapsamlı arama

- Mevcut `DURUM.md` başlangıç kuralı varsa onu koru. Kod keşfine başlamadan önce kökteki `CODEBASE_MAP.md` dosyasını bir kez oku.
- Haritadan görevle ilgili yolu seç; önce yalnız o dizinde `rg -n -m 20` ile hedefli arama yap. Dosyaların yalnız gerekli satır aralıklarını oku; çıktıyı kısa tut.
- Sonuç bulunamazsa önce ilgili dizinde dosya adlarını `rg --files` ile ara; kapsamı aşamalı genişlet. Her görevde tüm proje ağacını veya içeriklerini dökme.
- Harita bir yönlendirmedir; güncelliğini ilgili yolların varlığıyla doğrula. Eksik/eski kayıt işin ilerlemesini engellemez.
- Bağımlılık, derleme, önbellek, model, medya, arşiv ve gizli ayar dosyalarını görev gerektirmedikçe tarama. `.env` içeriğini haritaya/çıktıya taşıma.
- Önemli dosya/dizin taşınır veya eklenirse yalnız ilgili harita kaydını güncelle. Her görevde haritayı yeniden üretme. Kaynak kodun doğruluğunu harita özetinden varsayma.
<!-- END CODEBASE MAP -->
