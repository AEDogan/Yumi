# Yumi arayüz yenilemesi — 17 Ekim 2026

## Tasarım kararı

Masaüstü karakterinin yanında kullanılan sakin, kompakt bir kontrol merkezi. Dikkat sohbet ve karakterde; ayarlar, cihazlar ve hareketler sabit gezinme noktalarında. Pazarlama sayfası/animasyonlu hikâye önerisi bu ürün için uygun bulunmadı; yerel masaüstü etkileşimi esas alındı.

Temel açık palet: İnci #F5F7FA, yüzey #FFFFFF, yazı #182638, ikincil #596A80, vurgu #4468D9, çizgi #DEE5EF. Koyu palet aynı hiyerarşiyi korur. Altı mevcut tema anahtarı korunur; görünür küçük tema önizlemeleri eklenir. Windows'ta Segoe UI Variable / Segoe UI; gövde14px, yardımcı12px, bölüm başlığı20px. Tekrar eden eş boyutlu kartlar ve dekoratif gradient yığını yok.

```
yumi                                      pencere kontrolleri
durum / bağlantı
Sohbet    Geçmiş (aç/kapat)     Sohbet başlığı / senaryolar
Model     Yeni sohbet         Mesajlar
Hareket   Sohbet listesi       ...
Ev        Seçili sohbeti sil   Mesaj yaz / mikrofon / gönder
Görünüm                       Bağlantı ve mikrofon açıklaması
Ayarlar
```

Ana gezinme sabit ve çakışmasız. Sohbet geçmişi yalnız sohbet alanında; ayarlarda bölüm listesi solda, seçilen içerik sağda. Kontrollerin başlıkları/tıklama hedefleri görünür; klavye odağı ve açık/koyu karşıtlığı korunur. Dar görünümde geçmiş kapatılabilir, balonlar içerik alanına göre genişler.

## İşlev eşlemesi / korunacak davranış

- Sohbet: mevcut `_send`, `_mic`, `_cancel_reply`, geçmiş seçme/yeni/silme. Gerçek arşiv ve API test sırasında değiştirilmeyecek.
- Model ve ses: mevcut SettingsDialog model/ses bölümleri, karakter profilleri, model ekleme/kaldırma.
- Hareket: mevcut yerel komutlar, günlük senaryolar, müzik türü/otomasyon ve VRMA dosya kütüphanesi.
- Akıllı ev: mevcut SmartHomeDialog/cihaz köprüsü; gezinme testinde gerçek cihaz komutu yok.
- Görünüm: tema ve opaklık, canlı önizleme, iptalde geri alma, kaydetmede kalıcılık.
- Ayarlar: sağlayıcı/anahtar, ses, davranış ve Windows başlangıcı korunur.
- Tepsi ve masaüstü sağ tık eylemleri korunur. Yeni sayfalar mevcut PageStack ile açılıp kapanır.

## Kalite kapısı

Kaynak sözdizimi ve mevcut sohbet/ses testleri; geçici veriyle gerçek Qt düğme/menü/gezinme/geri dönüş testi; tema önizleme/iptal/kayıt; dar/geniş pencere; açık/koyu/lavanta gerçek ekran görüntülerini inceleme. Bu çalışma diğer beş başlığın tamamlandığı anlamına gelmez; ses kabulü, dans, müzik doğrulaması, fizik ve mimikler ayrı izlenir.
