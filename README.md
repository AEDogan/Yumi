<!-- 14 Ekim: sohbet iptali, mikrofon kuyruk temizliği ve modele göre adım/ilerleme düzeltmeleri uygulandı. Web kararlılığı, adla uyandırma ve doğal temas kabulü hâlâ açık. CALISMA_PLANI.md güncel durumdur. -->
# Yumi · masaüstü sesli asistanı

18 Ekim 2026. Proje C:\Projeler\Yumi; Windows/Python/PySide6. Birleşik güncel durum ve açık kalite sınırları: `YUMI_GUNCEL_DURUM.md`.

## Kullanılabilir çekirdek

Ayarlar, karakter ekleme ve VRMA ekranları ana pencere içinde yandan kayarak açılıp kapanır; önceki ekranın alanları ve konumu korunur. Karakter ekleme ayrı popup ve engelleyici bekleme döngüsü kullanmaz. İşletim sistemi dosya seçicileri ve hesap girişi kendi platform akışlarıdır.


BASLAT.cmd veya Yumi masaüstü kısayoluyla açılır. Karakter sürüklenebilir, boyutu değiştirilebilir, VRM eklenip model/isim/ses profili seçilebilir. Temel gezinme ve selamlama korunur. Hazır VRMA dosyaları ayarlardaki animasyon dosyaları bölümünden elle oynatılabilir.

Kullanıcının isteğiyle mevcut prosedürel danslar ve bütün otomatik senaryolar kaldırıldı. Dans/senaryo kataloğu, düğmeleri, ayarları, zamanlayıcıları ve müzik/aktivite tetikleyicileri yoktur. Uyku, masa, oyun ve TV davranışları çalışmaz. Model ve GLB varlıkları korunmuştur. Yeni doğal dans ve senaryolar henüz yapılmadı.

## Sohbet ve ses

Varsayılan sohbet Gemini API / gemini-3.5-flash-lite ile doğrudan akar. Mevcut Yumi projesi AI Studio’da Free tier olarak doğrulandı; kota dolunca ücretli modele geçilmez. Ayarlarda Flash-Lite/Flash seçilebilir. Takip soruları bağlamı korur, Durdur isteği ve sesi keser; sesli yanıt sürerken yeni soru gönderilebilir. ChatGPT/Gemini web bağlantısı alternatif olarak ayarlardan seçilir. Ayrı Yumi profiliyle varsayılan Chromium tarayıcısı arka planda kullanılır; kişisel tarayıcı profili kullanılmaz. İlk giriş için normal giriş penceresinde kullanıcı oturum açar ve Giriş tamamlandı düğmesine basar. Firefox desteklenmez.

Gönderim ve yanıt aşamaları arayüzde ayrı gösterilir. Gönderim belirsizse mesaj otomatik tekrarlanmaz. Doğrudan ücretsiz API’de gerçek kısa yanıtlar 0,72–1,52 s, Qt penceresindeki takip soruları yaklaşık 2 s içinde geldi. Tam ses yolunda ilk hoparlör başlangıcı 5,41 s ölçüldü. Bunlar uzun kullanım, kota ve farklı ağlarda hız garantisi değildir. ChatGPT web doğrulaması ayrı olarak açıktır. Resmî edge-tts 7.3.1 güncellemesinden sonra Ahmet/Emel gerçek ses üretimi ve oynatma testleri geçti (üretim yaklaşık 1,9–2,5 s); uzun oturum kararlılığı ayrıca açık; site sesi canlı kabulü de tamamlanmadı. Yerel Piper gerçek WAV üretimi doğrulandı; Türkçe erkek sestir. Motor tercihi otomatik Piper'a çevrilmez.

Ctrl+Alt+M mikrofonu başlatır/durdurur. İsimle uyandırma, gürültü ve konuşma sonunda gönderim gerçek mikrofonla genel kabul bekler. Yerel STT/TTS, tam çevrimdışı sohbet anlamına gelmez; yerel sohbet modeli yoktur.

## Kontroller ve açık sınırlar

Yeni çekirdek Qt penceresi açılıp çizildi; kaldırılmış düğme/ayar/zamanlayıcılar ve eski poz çağrıları sınandı. Dokuz VRM'de duruş/yürüyüş/selamlama/dinleme/VRMA hesapları kontrol edildi. Ses sırası ve hata sonrası kilidin açılması otomatik kontrol edildi. Bunlar bütün hareketlerin doğal göründüğünü veya her VRM'nin uyumlu olduğunu kanıtlamaz.

Tam anatomik sınırlar, çarpışma/kumaş teması, yüz/görüntü kalitesi, 100+ FPS, tek kurulum ve uzun kullanım kabulü açıktır. Önceki yaklaşık 33 FPS tarihi ölçümdür; bu sürüm için yeni ölçüm yapılmadı.

Ayarlar/geçmiş/hata kaydı %APPDATA%\YumiDesktop altındadır. Eski kurulum verisi ilk geçişte dosyaları silmeden taşınır; iki ayrı veri klasörü bulunursa üzerine yazılmaz. Tepsi menüsünden çıkılır. Güncel sıra ve kabul koşulları `YUMI_GUNCEL_DURUM.md` içindedir; önceki plan ve devir kayıtları tarihsel kabul edilmelidir.
