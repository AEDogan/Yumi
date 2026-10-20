> Kısa başlangıç: [DURUM.md](DURUM.md). Bu dosya ayrıntılı başvuru/geçmiş kaydıdır; açılışta tamamını okuma. Yeni durum özetini DURUM.md içinde güncelle; ayrıntılı açık işler burada korunur.

14 Ekim 2026: PageStack ile uygulama alt ekranları tek pencerede kayıyor; model ekleme asenkron. Edge-tts 7.3.1 uygulanıp Ahmet/Emel üretim ve gerçek oynatma testleri geçti. Web sohbeti hâlâ canlı yanıt kabulünü geçmedi. Güncel kanıt ve sıra CALISMA_PLANI.md içinde.

> 13 Ekim 2026 güncellemesi: Kullanıcı mevcut dans ve senaryoları tamamen kaldırdı. Eski katalog, otomatik davranışlar ve ilgili modüller artık uygulamada yok. Güncel çalışma sırası/kabul koşulları CALISMA_PLANI.md içindedir. Aşağıdaki kayıtların eski dans/senaryo özellikleri ve tamamlanma ifadeleri tarihsel durumdur; yeni içerik başlamadı.

# Son durum — 13 Ekim 2026

Güncel bağlantı web sohbetidir; önceki Codex/API bilgileri aşağıda tarihsel kayıt olarak tutulur. Güncel takip kaynağı KALAN_ISLER.md, kullanıcı rehberi README.md.

Kulaklık kaldırıldı. Bilek ve temel kemik dönüş zarfları bütün hareket çıktılarına uygulanıyor; tam yönlü anatomik menteşe ve çarpışma çözümü değildir. Kuyruk eğrisi/yerçekimi, zemine oturma IK'si, tarayıcı bağlantısını yeniden kullanma, önceden sohbet tercihi gönderme, eski yanıt ayrımı, sıralı TTS hazırlığı ve sürükleme önceliği düzeltildi. Otomatik/geometri/görsel kontroller geçti; 100 FPS sağlanmadı.

Gemini canlı sayfa kontrolü oturum gerektiğini gösterdi. Emel/Ahmet canlı ses denemesi Microsoft 403 ile başarısız oldu. Bunları bitmiş diye raporlama. Kullanıcı yeni varlık ve özellikleri erteledi; Meshy/Pinokio/kulaklık işlerini yeniden açma.

## Tarihsel notlar

# Mika · güncel doğrulanmış durum · 13 Ekim 2026

- Sohbet akışındaki bütün cümleler ve noktalamasız son bölüm sırayla ses kuyruğuna alınır. İlk ses bitse bile yanıt akışı tamamlanmadan yeni istek/mikrofon açılmaz. Ses hatası açık gösterilir; Emel/Nanami yerine otomatik erkek Piper sesi kullanılmaz.
- Kullanıcı mesajı yanıt beklenmeden atomik olarak kaydedilir; yerel komutlar ve asistan yanıtları da sohbet geçmişine girer. Yeniden yükleme kontrolü geçti.
- SSE okunurken küçük parçalar hemen iletilir, HTTP bağlantısı kapatılır. Anahtar URL yerine HTTP başlığında gönderilir. Ağ zaman aşımında aynı istem arka arkaya tekrar üretilmez (bağlantı 5s / okuma 12s). Kısmi yanıt sonrası bağlantı koparsa aynı isteği tekrar üretip sesleri üst üste bindirmez.
- 50 türün her birinde 100 farklı prosedürel figür dizisi var. Tür için belirlenen figür havuzları ve sabit tohum kullanılır; yeniden açılışta aynı seçimin koreografisi değişmez. Otomatik seçim boş rutin listesine erişmez. 5.000 kombinasyon gerçek VRM'de sonlu kemik konumları üretti. Bu, 5.000 mocap klibi veya doğal koreografi kalite onayı değildir.
- Statik iskelet koordinatları, dahili animasyon yolları ve yay alt ağaçları önbelleğe alındı; yay hesabı üç VRM'de önceki kodla 1e-10 toleransında eşdeğer. Çizimde MSAA durumu malzeme başına tekrar okunmaz.
- Aynı yürüyüş profilinde önce/sonra yaklaşık 32,8 FPS. GPU AMD Radeon RX 9070 XT, ekran 200 Hz, GPU skinning açık. PyOpenGL_accelerate 3.1.10 ile ortalama çizim süresi yaklaşık 9,7 ms → 7,3 ms (%24 azalma). Zamanlayıcı ve swap değişikliği hedefi çözmedi; 100+ FPS tamamlanmış değildir.
- Canlı Emel kontrolü: ilk 403 sonrasında tekrar başarılı; 34.272 bayt ses yaklaşık 4,1 saniyede üretildi. Gemini anahtarı model listesinde doğrulandı; aktif alias zaman aşımı, 3.6 ve 3.8 Flash 503 verdi. Sağlayıcı yanıt sorunu açık; hızlı sohbet tamamlandı denmez. Seçili model yeniden açılışta zorla değiştirilmez.
- Başlatıcıdaki QCoreApplication/QApplication çakışması kaldırıldı; yalnızca app.main QApplication oluşturur. Gerçek launch.py izole profille sorunsuz açılıp kapandı. Normal kullanıcı profiliyle Mika yeniden açıldı, süreç çalışıyor. Qt UI testinde 49 görünür türün 100 seçeneği, Tango otomatik figür değişimi, bağımsız dans/VRMA pencereleri ve yanıt bekleyen mesaj kaydı geçti.
- Nanami seçeneği Japonca ses olarak doğru etiketlendi; Türkçe telaffuzu deneysel. Japon sesinin Türkçe kalitesi doğrulanmış diye sunulmaz.
- Mikrofonun insan sesiyle testi, doğal dans/kıyafet/nesne çarpışması, bütün eklem sınırları ve temiz kurulum hâlâ açık. Pinokio ve ertelenmiş 3D varlık işlerine başlanmadı.

Aşağıdaki kayıtlar geçmiş çalışmalardır; çelişki varsa bu bölüm ve KALAN_ISLER.md geçerlidir.

# Mika · çalışma durumu

## 12 Ekim · Pinokio açıldıktan sonraki durum (en güncel)

- 13 Ekim takip: F5 Türkçe model indirmesi tamamlandı ve aynı kısa cümleyi `outputs/f5-turkish.wav` dosyasına üretti. Ancak İngilizce hazır referansla yerel Whisper çıktısı anlaşılmaz oldu: “Yadın ve çilt bir ince al, güleneyi bak.” Bu ilk F5 sesi uygun kabul edilmemeli ve Mika'da varsayılan yapılmamalı. Türkçe referansla yeniden deneme gerekir. Deneme sonrasında Pinokio kontrol hizmeti tekrar `ECONNREFUSED 192.168.1.37:42000` verdi; pterm ulaşılabilir olduğunda servisi ve mevcut model önbelleğini denetle. Chatterbox örneği önceki turda doğru çözülmüştü.
- Kullanıcının ek yatak görüntüsü düzeltmesi: yalnızca gövde hizası yetmedi, ayak şilteye giriyordu. `vrm.py` yatma pozunun iki bacağına ayrı kalça/diz/ayak yönü verdi. Üç VRM için yeniden alınan yatak görüntülerinde ayak merkezi yaklaşık 0,53–0,56 m; şilte yüzeyi yaklaşık 0,52 m. `outputs/sleep-check-1008834536223780037.png`, `outputs/sleep-check-2285521824446219752.png`, `outputs/sleep-check-7154677175075600880.png` yeni çıktılardır. Üçüncü taraf VRM kıyafet ve aksesuarlarının tüm yüzeyleri için çarpışma çözümü hâlâ yok.

- 13 Ekim kullanıcı ekran görüntülerinde yatakta havada kalan iki VRM ve fazla yatay sürükleme savrulması görüldü. `vrm.py` yatak temas yüksekliği artık saç/aksesuar değil, yalnızca gövde mesh örneklerinden hesaplanıyor. `outputs/sleep-check-1008834536223780037.png`, `outputs/sleep-check-2285521824446219752.png` ve diğer iki örnek görsel olarak incelendi; gövde şilteye oturuyor. Tüm kıyafet/yatak çarpışması çözülmüş değildir. `overlay.py` yatay sürükleme hızının yay etkisini %45 azalttı, dikey etkiyi korudu.
- +18 açma adımları Davranış sekmesinde yan yana: önce karakterin 18+ olduğuna ilişkin onay, ardından sahne dansı seçeneği. `dance_ui.py` bu tarz seçilince otomatik müzik türü seçimini kapatıyor; aksi halde seçilen dans hemen değişiyordu. `work/check_adult_dance.py` ayar kaydı ve tür görünürlüğünü doğruladı. Kıyafet çıkarma animasyonu yok.
- F5 Gradio işi model dosyasını ~1,08/1,35 GB indirirken Pinokio kontrol bağlantısı koptu, F5 çevrimdışı kaldı. `pterm status --probe` sonrası F5 yeniden başlatıldı. Önceki event ID geçersiz; yeni ID `outputs/f5-turkish-job.json` içinde. İndirme yeniden başladı, aynı işi ikinci kez gönderme. Ultimate hazır ve açık kaldı. Takip otomasyonu hâlâ gerekli.

- Kullanıcı Pinokio'yu açtı; `pterm status --probe` ile F5 ve Ultimate TTS servisleri hazır. Ultimate içindeki Chatterbox Multilingual CPU üzerinde yüklendi. Aynı Türkçe test cümlesi `outputs/ultimate-chatterbox-tr.wav` dosyasına üretildi; yerel Whisper cümleyi eksiksiz çözdü. Yaklaşık 2,24 saniyelik sesin sıcak modelle üretimi 12,14 saniye sürdü. Doğal sesin öznel kalitesi kullanıcı dinlemesiyle ayrıca değerlendirilmeli.
- `backend.py` ve `voice_profiles.py` üzerinden isteğe bağlı `chatterbox-tr` kadın tonlu yerel ses seçeneği Mika'ya eklendi. Ultimate/Pinokio açık olmalıdır; bu henüz tek paketlik kurulum değildir. Çevrimdışı uyarı aynı motorla WAV olarak önbelleğe alındı; kısa uyarıda Whisper bazı kelimeleri yanlış çözdü, kalite kusursuz diye raporlanmamalı. Kod derlendi, ses sürekliliği kontrolü geçti. Canlı Mika uygulaması yeni kodla yeniden başlatılmadı.
- F5 için MIT lisanslı Karayakar Türkçe modelinin 1,35 GB kontrol noktası hâlâ indiriliyor. İş `outputs/f5-turkish-job.json` dosyasındaki Gradio event ID'siyle başladı; ikinci kez başlatma. İndirme bitince aynı cümlede kalite/hız kıyaslaması yapılacak. Pinokio takip otomasyonu bu nedenle açık.
- Prosedürel iki kemikli IK'ye dirsek için 150°, diz için 145° azami bükülme sınırı eklendi ve matematiksel örnek geçti. Bu tüm omuz/kalça/boyun/parmak sınırları, VRMA klipleri ve kıyafet/nesne çarpışması için genel çözüm değildir.

## 12 Ekim · güncel ek not

- Instagram videosunu bu kez tamamını oynatıp inceledim; önceki “aynı dans” gösterimi yanlıştı. Kullanıcı bu koreografiyi şimdilik bırakmamızı istedi. `edm-club-duel` genel bir kulüp rutini olarak kalır ve referansın bire bir karşılığı sayılmaz.
- Masaüstüne `C:\Users\ahmet\Desktop\Mika.lnk` oluşturuldu ve `C:\Projeler\Mika\.venv\Scripts\pythonw.exe` → `launch.py` hedefi doğrulandı.
- `vrm.py`, `springs.py`, `vrma.py` performans düzeltmeleri projeye uygulandı. Şeffaf VRM yürüme profilinde önceki 23,8 FPS, sonrasında 32,8 FPS görüldü. `check_sleep.py` ve 41 VRMA örnek noktasında matematiksel eşdeğerlik testi geçti. Canlı uygulama yeniden açılmadığı için bu kod mevcut çalışan süreçte henüz etkin değil. 100 FPS hedefi açık.
- Pinokio masaüstü başlatıcısı süreç kodu 0 ile hemen kapandı; `pterm search` hâlâ `ECONNREFUSED 192.168.1.37:42000`. Ultimate/F5 seslerini hazır veya entegre diye raporlama.
- Kullanıcının yeni anatomik eklem sınırı isteği `KALAN_ISLER.md` içine eklendi. `work/audit_anatomy.py` dokuz VRM'yi taradı: her birinde 17 temel humanoid kemiği mevcut; dolayısıyla imkânsız pozlar kemik eksikliğinden çok poz hedefi, hareket aralığı ve çarpışma kaynaklı. Rapor `outputs/vrm-anatomy-audit.json`. Sınır/çarpışma çözümü henüz uygulanmadı.
- Ayarların 5 sekmesi, ses tercihini koruma, mikrofonun sessizlikte komutu sonlandırması ve masaüstü tıklama/gezinme otomatik kontrolleri geçti. Bu testler gerçek kullanıcı hesabı, mikrofon veya canlı görünüm incelemesinin yerini tutmaz.
- Hava durumu takip sorularında aynı şehrin koordinatları tekrar aranmayacak şekilde oturum içi konum önbelleği eklendi. Kısa yanıt ve “peki yarın?” akışı `work/check_weather_cache.py` ile geçti.

## 12 Ekim · son tur (en güncel bilgi)

- Son kullanıcı isteği: 50 tür × 100 doğal hareket, ritim ve parça değişimine göre seçim; Instagram örneğindeki kulüp dansı; karakterin dans ederken yatayda yarım ekran genişliği içinde yer değiştirmesi. Şu an **30 tür, 301 genel prosedürel rutin ve 10 yetişkin sahne rutini** var; bunlar 5.000 ayrı mocap klibi değildir. EDM için örnekte görülen kol kaldırma, yana kayma ve ritmik kol çekme hareketlerinden esinlenen bir rutin eklendi. `DanceTravel` yalnızca `chasse` ve `slide` adım dizilerinde, salınım evresinde yatay yer değiştirir; diğer dans figürlerinde karakterin x konumu sabittir. 16 ms güncelleme ve yarım ekran genişliği sınırı sayısal olarak sınandı. Rutin değişimi eklem hedeflerinde yaklaşık 0,4–1,1 saniye yumuşatıldı. Gerçek VRM üzerinde canlı gözle doğrulama ve profesyonel hareket kalitesi hâlâ açık.
- Yetişkin sahne dansı seçeneği varsayılan kapalıdır; yalnızca karakter profilinde 18+ doğrulandıysa açılır. Çömelme hareketi var. Kıyafet çıkarma animasyonu yok. İçeriğin yaşı belirsiz VRM'lerde etkinleşmemesi gerekir.
- Son UI düzeltmeleri: popup konuşma balonu kapalı, sağ tık menüsü sade, ayar ve tema önizlemesi canlı, mikrofon açılır listesi okunur, kapat/dash tepsiye gizler. Oturma pelvis konumu ve kıyafet yay kemikleri düzeltildi; sandalye/etek katı temasları **tam çözülmedi**.
- Ultimate Pinokio uygulaması 7860 üzerinde hazır; Chatterbox Multilingual model yüklemesi **CUDA ağırlıklarının CPU'da açılamaması** nedeniyle başarısız oldu. F5 CPU kurulumu başlatıldı ve ilk açılışında 1,35 GB temel F5 modelini indiriyor. Henüz doğrulanmış kadın Türkçe ses örneği veya Mika entegrasyonu yok. Önceki Pinokio durum notları aşağıda tarihsel kayıt olarak kalmıştır.
- Seçili Codex hesap yanıtı kısa testte yaklaşık 32 saniyeydi. Emel TTS yaklaşık 3 saniye sonra 403 verdi. Gecikme ve kararlı kadın ses hâlâ açık.

Proje C:\Projeler\Mika, Python/PySide6, tek ajan. Electron yok.

12 Ekim: yüz dokusu/saydamlık, toon normal/emisyon, mipmap/MSAA düzeltildi; VRM0 saç yayı/çarpışması eklendi. 30 tür x10 prosedürel dans: dance.py, dance_catalog.json, dance_ui.py. Rock/metal/EDM dahil. Tür/BPM elle, başlık eşleşmesi isteğe bağlı; gerçek ses türü/beat analizi yok.

Kullanıcı Microsoft çevrimiçi Türkçe sesi açıkça onayladı. edge-tts Emel/Ahmet, Windows yedek; app QAudioBufferOutput ile gerçek ses seviyesine ağız morphu bağlandı. Codex/API Türkçe sohbet istemi daha doğal ve bağlama uygun hale getirildi.

vrma.py normalize humanoid retarget, LINEAR/STEP/CUBICSPLINE, yüz kanalları. motion_ui.py dosya içe aktar/oynat. motions/pixiv-test.vrma yalnızca kısa MIT örnek, gerçek dans paketi değil. Kullanıcı giriş yaptığı VRoid sayfasının Greeting/Energetic duruşları browser runtime ile görüldü. Modelde gömülü animasyon yok.

Yatak, masa, ekran yönü, gerçek kemik IK önceki turda düzeltildi. Kupa/kitap/kumanda gerçek el konumuna bağlandı; farklı çalışma/mola jestleri eklendi. 48 senaryo 29 ortak poz kullanıyor. Profesyonel mocap, tam MToon, VRM1 saç fiziği, tam müzik tanıma, yatak deformasyonu hâlâ eksik. Ultra gerçekçi diye sunma.

Kontrol: work/check_vrm.py, check_dance.py, check_voice_clip.py, check_scenarios.py. outputs/dans-onizleme.mp4, turkce-dogal-ses.mp3, vrm-face.png, vrm-uyku.png, vrm-masa.png. Gerçek mikrofon insan sesiyle kullanıcı testi gerekiyor. README güncel ayrıntıları içerir.

## Pinokio ses denemesi · 12 Ekim

Kullanıcı Ultimate-TTS-Studio ve e2-f5-tts kurulumunu tamamlayıp denemeyi açıkça onayladı. pterm üzerinden iki install.js çalışıyor; henüz hazır API yok. Microsoft 403 hatasında eski Windows sesine otomatik geçiş kaldırıldı, aynı seçili sesle geçici hatada bir tekrar var; 403 doğrudan görünür hata olur. work/check_voice_consistency.py ilk başarılı ve sonraki başarısız yanıtın asla Windows'a dönmediğini doğruladı. Mika yeniden başlatıldı.

Pinokio skill pterm-first: uygulama dahili CLI çalıştırma veya launcher dosyalarını değiştirme. Yerel konfigürasyon C:\Users\ahmet\.pinokio\config.json; home C:\pinokio; pterm C:\pinokio\bin\npm\pterm.cmd. İki uygulama başlangıçta yalnızca launcher vardı; kullanıcı kurulumu ayrıca onayladı. F5 temel model en/zh; gerçek Türkçe kalite henüz sınanmadı. Ultimate içindeki Chatterbox Multilingual Türkçe adayı. Kurulum tamamlanınca status --probe, API keşfi ve aynı Türkçe metinle ses örnekleri gerekiyor.

Kullanıcı iki uygulamanın kurulumunu tamamlayıp denemeyi tekrar açıkça onayladı. Her iki install.js aktif. F5 ROCm bağımlılıkları yaklaşık 1.7GB; download yavaş. Ultimate kaynak clone tamamlandı, gradio/pip bağımlılıkları indiriliyor. Türkçe F5 adayları Karayakar/F5-TTS-Turkish ve marduk-ra/F5-TTS-Turkish; henüz model indirilmedi. Son ses dosyaları app.py içinde response-monotonic_ns adıyla üretiliyor, eski oynatıcı önbelleği tekrar kullanılamaz.

Son değişiklik: Gemini API ve ayrı DPAPI anahtarı/model ayarı eklendi; Gemini sesi/ASR yerel yolları kullanır. overlay.py alpha QRegion ile boş alan tıklama geçirir, native WindowFromPoint kontrolü geçti. Oval masaüstü zemin yok, görev çubuğu üst kenarı floor. Tam ekran genişliği yürüyüş ve elle sürüklemede durma; menüden görev çubuğuna dönülür. Sağ tık VRM model yükle. work/check_desktop_gemini.py geçti. Pinokio otomatik takip görevi devam ediyor, launcher kurulumu bu değişikliklerde etkilenmedi.


## Ses takip güncellemesi · 12 Ekim 15:37
Ultimate IndexTTS indirmeleri bitti. start.js çalışıyor, F5 handler açılışta openai/whisper-large-v3-turbo modelini checkpoints/f5/cache içine indiriyor; API henüz hazır değil. Bu indirmeyi tekrar başlatma. Ultimate Torchaudio 2.4.1 onaylı düzeltmesi tamamlandı. F5 kurulum tamamlandı fakat AMD ROCm Torch dağıtımında torch.distributed.ReduceOp yok; başlangıç başarısız. Kullanıcı F5 torch.js AMD satırlarının CPU Torch/Torchaudio 2.7.0, Torchvision 0.22.0 olarak düzeltilmesini açıkça onayladı. Orijinal work/f5-torch-before-cpu-fix.js içinde. C:/pinokio/api/e2-f5-tts.git/repair-cpu.js pterm ile başlatıldı, Torch 205.2MiB indiriyor; yeniden başlatma. Tamamlanınca F5 start.js pterm ile başlat, status --probe kontrolü yap. İki gerçek Türkçe ses örneği hâlâ üretilmedi; kalite ve offline kullanım henüz doğrulanmadı. Otomasyon aktif kalmalı.

## Son çalışma · 12 Ekim akşamı

Kullanıcı 3D varlıkları erteledi. Saç sürükleme koordinatları `motion_space.py` ile VRM/sahne dönüşümüne çevrildi. `beat_clock.py` monoton vuruş saati ve yumuşak onset hizası ekler. `dance.py` destek ayağı, kol erişimi, ayak sınırları ve kalıp geçişleri artık sürekli. 30×10 düzenin el/ayak sınırı sayısal olarak sınandı; en büyük 0.0002 vuruş sınırı atlaması 0.00021 m. Güncel dans video önizlemesi üretildi. Overlay silüet okuması 100 yerine 200 ms aralıkta; UI tıklama ve gezinme testi geçti.

Çevrimdışı yanıt metni ve seçili sesle ses önbelleği eklendi. Önbellek başarısızsa ses sessizce başka cinsiyete geçirilmez. Kullanıcı DPAPI anahtarı kendi hesabında çözüldü; 3.8 Flash geçici 503/zaman aşımı verdi, 3.6 Flash gerçek API yanıtı verdi ve aktif ayar 3.6'ya alındı. Google Gemini 3.8 Flash-Lite TTS Türkçe kadın ses isteği 503 verdi; üretildi diye sunulamaz.

Pinokio kontrol düzlemi kapalı (`ECONNREFUSED 192.168.1.37:42000`, loopback de kapalı); Ultimate/F5 ses testlerini servis gelmeden tekrar başlatma. Önce pterm status --probe ve günlükleri kontrol et. Pinokio takip otomasyonu hâlâ açık. Çalışan Mika launch.py yeni kodla yeniden açıldı. KALAN_ISLER.md güncel engelleri listeler. 3D GLB'ye dokunulmadı.