# Yumi canlı ses — 14 Ekim 2026

Yumi'nin mikrofon düğmesi Gemini Live native ses oturumunu başlatır; ikinci tıklama durdurur. Eski STT/TTS zinciri kapalıdır. Kullanıcı gerçek konuşmanın çalıştığını doğruladı. OpenAI erişimi eklenmedi, ücretli proje açılmadı.

## Son düzeltme

Mikrofon ve hoparlör artık aynı geçici Chromium ses bağlamında çalışır. Mikrofon yankı ve gürültü giderme etkin olmadan açılmaz. Bu sayfa yalnız bilgisayardaki ses işleme içindir; internet erişimi engellenmiştir, API anahtarını veya konuşma metnini almaz. Gemini bağlantısını Python sürdürür. Ek pencere gösterilmez; yeni paket kurulmaz.

Araya girme açıktır. Sunucunun konuşma başlangıcı ve iptal olayları hem Python hem ses işleyicisi kuyruklarını temizler. Eski kuyruk nesline ait parçalar ve oynatma bildirimleri atılır. Oturum devam ettirme, mikrofon taşması kurtarma ve bellek korumaları korunur. İşletim sistemi kilidi aynı anda ikinci Yumi mikrofon işçisini reddeder.

Kullanıcı ve asistan transkripsiyonları aynı Gemini oturumundan mevcut sohbet baloncuklarına aktarılır. Parçalar tek baloncukta birleştirilir; kesilen yanıt ayrı tutulur. Ekran güncellemesi 50 ms aralıklarla birleştirilir. Metin yalnız mevcut sohbet geçmişinin normal saklama yoluna girer; tanı kaydına veya ayrı bir transkript dosyasına girmez. Arayüz değişikliği açık Yumi'nin yeniden açılmasını gerektirir.

Uygulama oturumu 8 saniye tam sessizlikte kapanır; kullanıcı konuşması, sağlayıcı yanıtını bekleme, üretim, bekleyen çıkış ve son hoparlör sesi bu sayacı sıfırlar. Eski kodda elle açılan dinlemenin boş bekleme sınırı 8 saniyeydi; 0,75 saniye ise yalnız cümle sonu eşiğiydi. Adla yeniden uyandırma henüz etkin değildir: bu Windows'ta çevrimdışı tanıyıcı yok, Vosk modeli yok. Eski Whisper/Vosk sohbet zinciri açılmadı ve Gemini'ye sürekli arka plan sesi gönderilmedi. Çağrı adı ileride etkin modelin `character_name` değerinden alınmalı; sabit Yumi adı kullanılmamalı.

Gerçek ölçümde 14,1 saniyelik yanıt 1,86 saniyede geldi. Oynatma düzenliyken kuyruk 12,22 saniyeye ulaştı; eski 8 saniyelik sınır geçerli yanıtı hata sayıyordu. Yeni sınır 32 saniye / 1.536.000 bayt. Giriş kuyruğu 320 ms; tarayıcı kuyruğu yaklaşık 60 ms hedefli ve ayrıca sınırlıdır. 6 GiB toplam / 4 GiB süreç sınırı ve diğer programlara bellek rezervi değişmedi.

## Gerçek test kapsamı

- Eski fiziksel ses yolunda 16 saniyelik Gemini testinde üç kesilme gözlendi. Tek oturum kullanıldı.
- Yankı/gürültü giderme açık fiziksel giriş/çıkışta kısa ve uzun yanıt testleri tamamlandı; kesilme ve hata olmadı. Uzun yanıtta bütün 14,1 saniyelik PCM çıkışı oynatma yolundan geçti; oynatma isteği aralığı en fazla 32 ms oldu.
- Fiziksel aygıtlar açıkken AEC sonrasına bilinen konuşma PCM'i kontrollü eklendi. Sağlayıcı bir kesme gönderdi, kuyruk temizlendi ve yeni yanıt geldi. Bu test gerçek insanın akustik araya girmesini kanıtlamaz.
- Hiçbir ses, transkript, anahtar veya devam anahtarı kaydedilmedi. Testler yalnız sayısal sonuç verdi.

Kullanıcı sesli akışın düzeldiğini doğruladı. Kalan kullanıcı kabul adımı: mevcut konuşma bitince Yumi'yi yeniden açıp mikrofonla konuşmak; iki tarafın metninin baloncuklarda görünmesini ve konuşma/oynatma bittikten 8 saniye sonra kapanmayı kontrol etmek. Uzun süreli kullanım ve değişen hoparlör/mikrofon yerleşimleri henüz tam doğrulanmadı. Adla uyandırma için hafif yerel bir algılayıcı hâlâ gereklidir.

## Ayrı prototipi başlatma

`BASLAT.cmd` mevcut Yumi Python ortamını ve korunan Gemini anahtarını kullanır. Varsayılan Windows mikrofonu ve hoparlörü seçilir. Özel aygıt numarasıyla ses açma yeni yankı korumalı yolda henüz desteklenmez; sessizce farklı aygıta geçilmez. Ses seçimi Kore/Puck/Charon/Aoede/Fenrir ile yapılabilir. Ayrı deneme 120 saniye veya Ctrl+C ile durur; Yumi düğmesiyle açılan oturum kullanıcı durdurana kadar sürer.

Mikrofon sesi oturum açıkken Gemini'ye gönderilir. Ses kaydı tutulmaz. Arayüzdeki metin normal sohbet geçmişine girer; ayrı ses/transkript kaydı veya tanı metni oluşturulmaz. Son durum ve süre kayıtları sınırlı tutulur. Diğer canlı denemelerle birlikte başlatılmaz. `--probe --play-test` yalnız sağlayıcı sesinin hoparlör yolunu kontrol eder, mikrofonu açmaz.

Kaynaklar: [Gemini kesme davranışı](https://ai.google.dev/gemini-api/docs/live-api/capabilities), [yankı giderme özelliği](https://developer.mozilla.org/en-US/docs/Web/API/MediaTrackConstraints/echoCancellation), [oturum devam ettirme](https://ai.google.dev/gemini-api/docs/live-api/session-management).
