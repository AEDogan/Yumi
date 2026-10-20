# Yumi — beceri ve kahve sahnesi doğrulaması, 16 Ekim 2026

Son kullanıcı kararı: yerel işlem sonucunun Gemini Live'a gönderilip seçili sesle okunmasına açık onay verildi. İnternet yoksa yalnız ekranda gösterilecek. Açık/hazır canlı ses oturumuna sonuç iletimi eklendi; sonuç önce geçmiş ve balonda tutulur. Bağlantı/ses hatasında metin korunur, yerel işlem yeniden yürütülmez; yeni mikrofon oturumu açılmaz. Testler: `work/check_skill_feedback.py`, çevrimdışı geri dönüş eklenmiş `work/check_skill_ui.py`. Bunlar taklit taşıma testleridir; gerçek bulut/ses kabulü değildir.

Bu kayıt gerçek donanım testi ile taklit servis testini ayırır. İlk testler gerçek cihazları kullanmadı. Sonraki TV kabulünde kullanıcı ekran koduyla eşleştirmeyi tamamladı: Android TV açık durumunu bildirdi ve gerçek ses geri bildirimi **20 → 21 → 20** olarak doğrulandı (`work/check_live_tv.py`). Cihaz “Salon TV” olarak kayıtlı. TV güç açma/kapatma ve video aktarma denenmedi. Süpürge kullanıcının son talimatıyla beklemede; süpürgeye komut veya Mi Home giriş denemesi yapılmadı. Gerçek takvim, not ve mikrofon kullanılmadı. FPS çalışması bekliyor.

## Düzeltilen kahve sahnesi

- Rastgele görünmez koltuğun boyutuna bağlı yerleşim kaldırıldı. Karakter omuz genişliği + giysi payı ile yürüyüş yarıçapı ve tezgâh ön mesafesi hesaplanır.
- `scene_navigation.py`: genişletilmiş tezgâh/pencere ayak izleri çevresinde görünürlük grafiği, segment boyunca çarpışma kontrolü ve en kısa geçerli rota. Giriş ve çıkış ayrı hesaplanır; hedef eşyanın içindeyse hata verir.
- Kahve makinesinin önü karaktere döndürüldü. Tezgâh, makine, fincan, rota ve kadraj aynı yerleşim verilerini kullanır. Modeli kapatan masif blok yerine açık ayaklı tezgâh var.
- `cup_grip.py`: mevcut kırmızı fincanın ayrı kulp geometrisi ve karakterin avuç/parmak kemiklerinden tutuş. Parmak kıvrılması, omuz/dirsek/bilek sınırları ve son deforme parmaklardan rijit eşya dönüşümü; bileğe sabit dünya ofseti kaldırıldı. Fincan yaklaşma sırasında tezgâhta kalır, tutuş tamamlandığında ele alınır. Tutuşa yaklaşırken temas hatası geri beslenir.
- Dört karakterin giriş/çıkış segmentleri engellerden temiz. Dört karakterde alma anı temas hatası <0,015 sahne birimi; testte en büyük son ölçüm yaklaşık0,0002. Bu, tam parmak derisi/kumaş hacim simülasyonu değildir.
- Önizleme üretim kamerasından: `work/coffee-fixed.png`. Kolların/mimiklerin bütün kliplerde sanatçı düzeyinde kabulü, tam kumaş çarpışması ve fincanı fiziksel olarak yüzeye geri bırakma hâlâ ayrı açık işlerdir.

## Düzeltilen beceri entegrasyonu

- “Süpürgeyi şarja gönder” ve durum soruları yanlışlıkla temizlik başlatıyordu: düzeltildi. TV ses açma/kısma, güç açma ile karışmıyor. Saat biçimindeki yerel alarm komutu eklendi.
- Aynı başlıkla alınan notlar gün içinde birbirinin üzerine yazılmıyor; başlıktaki dosya yolu karakterleri temizleniyor.
- `daily_briefing` sonuç döndürmüyordu: düzeltildi. Hava, takvim, döviz ve haber bölümleri ve kısmi başarısızlık bilgisi dönüyor.
- Bağlı termostat/sensör veya desteklenen TV açma bağlantısı yoksa sahte başarı bildirilmiyor. Sensörden alınmayan22 derece değeri kaldırıldı. Desteklenmeyen TV komutu artık varsayılan olarak kapatma yapmıyor. HA sessize alma zorunlu parametresi tamamlandı.
- Evden çıkış/dönüş rutinleri yalnız başarılı cihaz sonuçlarını başarılı sayıyor; sessizce bilgisayar kilitleme kaldırıldı. Genel rutin sonucu da alt adımların hatalarını yansıtıyor.
- OSRM sürüş süresi canlı trafikmiş gibi1,25 ile çarpılmıyor. Rota cevabı trafik içermediğini söyler, canlı trafik için harita bağlantısı verir. IP konumu alınamazsa İstanbul/Kadıköy tahmini gerçek konum diye söylenmiyor.
- Uygulama, panel ve Gemini yazılı sohbeti aynı beceri motorunu kullanıyor; ayrı motorun sayaç/ayar kaybetmesi önlendi. Test veri dizini motor için de geçerli. Takvim bağlantısı sorgusu Outlook'u kendiliğinden başlatmıyor.
- Yerel komutlar ve panel cihaz işlemleri arka planda çalışır; arayüz iş parçacığını ağ beklemesiyle kilitlemez. Süre/alarm uyarıları Qt sinyaliyle ana iş parçacığına gelir; uyarı etiketi korunur. Panel işçisi kapanan sayfadan bağımsız tutulur; uygulama çıkarken sürmekte olan panel işinin tamamlanması beklenir.
- Yazılı Gemini akışı tamamlanmadan beceri uygulanmaz; yinelenen tam çağrı tek kez yürütülür. Kesilmiş/bitmemiş akışta işlem yapılmaz. Bu testler gerçek Gemini bağlantısı kullanmadı.
- Sonuçla uyumlu mimik/onay: başarıda hafif mutlu ifade ve küçük baş onayı, eller boşsa başparmak; hatada belirsizlik, açıklama gerekiyorsa soru ifadesi. Elde eşya veya aktif mobilya sahnesi varken otomatik el jesti eklenmez; senaryo tutuşu korunur.
- Canlı sesin tamamlanan kullanıcı yazısını ayrıştıran yolu da beceri komutlarını tanır. Sonuç balonda gösterilir. Canlı ses işçisi aynı paket yolunu kullanır.

## Testler ve kapsamları

- `work/check_coffee_contacts.py`: dört karakter, giriş/çıkış boyunca süpürülmüş ayak izi, alma temas hatası, son parmak dönüşümü.
- `work/check_scenario_poses.py`: dört karakter × yedi senaryo, sonlu pozlar, kemik boyları, zemin ve kesilebilir çıkış.
- `work/check_scene_framing.py`: on koltuk/sehpa eşleşmesi × beş oran; dört karakter × PC/TV/kahve/pencere × üç oran.
- `work/check_skill_integration.py`:26 Türkçe yönlendirme/argüman; izole liste/not/sayaç/alarm/kronometre/adres/rutin/takvim ve20dk önce hatırlatıcı kaydı; sahte HA tek seferlik sıcaklık ve sessize alma; Gemini tekrar/kesilme; sonuç tepkisi seçimi.
- `work/check_skill_services.py`: sahte HTTP/soket ile hava/döviz/haber/tarih/brifing, başarı ve bağlantı hatası; doğru rota süresi; sayaç/alarm/hatırlatıcı yalnız bir kez; oda; sahte Xiaomi/Tuya adaptörleri; Wi-Fi keşif.
- `work/check_skill_ui.py`: sayfa aç/geri/yeniden aç, oda akordeonu ve atama, yerel ses ayrıştırma, ortak motor/izole dizin, iş sürerken UI zamanlayıcısı, ana iş parçacığında etiketli uyarı, dolu ellerin korunması.
- `work/check_skill_reactions.py`: dört gerçek karakter × altı sonuç ifadesi/baş onayı,45° baş sınırı, kol kemik uzunlukları ve sonlu morph/poz verileri geçti.
- `work/check_daily_ui.py`: günlük senaryo komutları/ayarları regresyonu. Değişen22 üretim Python dosyası için sözdizimi kontrolü.

## Gerçek ortamda açık olanlar

- Bu sanal ortamda `tinytuya`, `micloud`, `miio`, `kasa`, `dirigera`, `google.auth`, `msal` bulunmuyor. İlgili bağlantılar paket/hesap/cihaz eşleştirmesi olmadan gerçek donanımda çalışır diye onaylanmadı. HA ve basit HTTP/soket yolları için de gerçek cihaz kabulü yapılmadı. Tuya termostatın DP/ölçek eşleştirmesi model özelinde doğrulanmalıdır.
- Gerçek Gemini doğal dil üretimi, canlı servislerin güncel erişilebilirliği ve insanla sesli kullanım bu taklit testlerinden çıkarılamaz. Karmaşık takvim+hatırlatıcı yazılı araç bildirimlerinde var; canlı ses prototipinde bütün bu bulut araçlarının doğrudan kayıtlı olduğu iddia edilmez.
- **Sesli sonuç için onay alındı:** İlk yama otomatik onay denetimince durdurulmuştu. Kullanıcı daha sonra açıkça “geminiye gönder okusun” diyerek izin verdi, çevrimdışı yalnız metin istedi. Yukarıdaki yeni akış uygulandı. Genel `_speak`/ayrı TTS davranışı değiştirilmedi; yalnız hazır Gemini Live oturumu yerel sonuçları okur. Oturum kapalıysa da sonuç ekranda kalır.
