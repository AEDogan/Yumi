# Hesapla giriş — 17 Ekim 2026

Asistan ayarlarının üstündeki iki doğrudan düğme mevcut web sohbeti bağdaştırıcısını kullanır: Gemini hesabımla giriş yap ve ChatGPT hesabımla giriş yap. Kullanıcı kendi tarayıcı penceresinde giriş yapar; Yumi ayrı yerel tarayıcı profilini korur. API anahtarı yazmak gerekmez. Giriş tamamlandı düğmesi normal giriş penceresini kapatır ve aynı profille sohbeti hazırlar. Tarayıcı doğrulaması gerekiyorsa kullanıcı normal doğrulamayı tamamlar; aşılmaya çalışılmaz.

Bu düğmeler, sağlayıcıların kayıtlı OAuth uygulaması olarak Yumi'ye yetki verme akışı değildir. Web oturumu ve canlı ses API erişimi ayrıdır. Mevcut yerleşik ses Gemini Live API kullanır; web seçilince Gemini web sayfasının sesini kullanıyormuş gibi sunulmaz. Kullanıcı girişten sonra gerçek mesaj yanıtı alabildiğini onayladı.

Resmî API OAuth seçenekleri ayrıca var: [OpenAI Sign in with ChatGPT](https://developers.openai.com/siwc/quickstart) uygun uygulamalar ve yetki verilen Responses kullanımı için istemci kayıt/izin akışı tanımlar. Her özel istemcinin kendiliğinden kayıtlı olduğu varsayılmıyor. [Gemini OAuth](https://ai.google.dev/gemini-api/docs/oauth) Cloud projesi, API etkinleştirme ve masaüstü OAuth istemcisi kurulumu tarif eder. Bunların yerine başka uygulamanın istemci kimliği veya özel tokenı kopyalanmadı. Bu turda yeni OAuth uygulaması kaydedilmedi ve API OAuth ses bağdaştırıcısı eklenmedi.

Kontrol: `work/check_voice_selection_login.py` iki düğmenin doğru sağlayıcıya yönlenmesini, web seçiliyken API alanlarının gizlenmesini ve seçimin kaydını geçici veriyle gerçek Qt'de doğrular. Gerçek hesap girişini yapmış gibi raporlamaz.

## Ses seçimi düzeltmeleri

- Eski katalogdaki bütün sesler `any` olarak işaretliydi. Erkek filtresi Kore'yi de tutuyordu. Kore/Aoede kadın; Puck/Charon/Fenrir erkek olarak ayrıldı. Filtre değişince uygun ilk ses açıkça seçilir; isimden bağımsız rastgele ses atanmaz.
- Eski çelişkili profillerde sesin açık adı korunur; arayüz filtreyi o sesle tutarlı gösterir. Kullanıcı yeni bir ses seçip kaydettiğinde global ayar ve etkin karakter profili aynı değeri alır.
- Konuşma sırasında ayar kaydetme, eski oturumu kapatıp seçilen sesle yenisini kurar. Normal dört saniyelik sessizlik bağlantıyı korumaya devam eder; her konuşmada yeniden bağlanma eklenmedi.
- Zaman aşımında Windows venv başlatıcısının altında kalabilen yalnız uygulamanın kendi çocuk süreçleri de kapatılır. Diğer uygulamaların süreçlerine dokunulmaz.
- Yerel önizleme seçili sesle yalnız hoparlöre kısa bir Gemini örneği ister; mikrofon açmaz. İptal, zaman aşımı, meşgul durum ve yerel ad dinlemesini geri yükleme kontrol edildi.

Kanıt: `work/check_voice_preview.py`, `work/check_voice_selection_login.py`, `work/check_voice_worker_cleanup.py`, `work/check_persistent_voice.py`. Son insan kabulü: kullanıcı Charon önizleme ve konuşmanın aynı erkek sesiyle geldiğini ve hesap girişi sonrası mesaj yanıtını onayladı. Bu kabul, bütün sesleri ve iki sağlayıcının bütün işlevlerini ayrı ayrı sınamış sayılmaz.

Son bağlantı hatası: bilinmeyen kapanış kota diye kesinleştirilmez; yalnız sağlayıcının açık hata kategorisi güvenli metne çevrilir. Bekleme bağlantısındaki hata sohbet geçmişine eklenmez; bağlantı açıklaması ve kullanıcı isteğiyle yeniden bağlanma alanı gösterilir. Mikrofon açılmaz, eski istek yeniden gönderilmez. `work/check_provider_errors.py` ve `work/check_native_recovery.py` geçti; eski hata olayının kesin nedeni kayıttan çıkarılamıyor.
