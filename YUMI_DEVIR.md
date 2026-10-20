> Kısa başlangıç: [DURUM.md](DURUM.md). Bu dosya ayrıntılı başvuru/geçmiş kaydıdır; açılışta tamamını okuma. Yeni durum özetini DURUM.md içinde güncelle; ayrıntılı açık işler burada korunur.

# Yumi devir notu — 15 Ekim 2026

**Güncel devam noktası: `KALDIGIMIZ_YER.md`.** Kullanıcı eşya işini yeniden açtı: 20 benzersiz GLB alındı, yürüyerek oturma/kalkma, rastgele koltuk/sehpa ve karakter anatomisine göre masa/ekran/klavye ölçüleri bağlandı. Dans ve otomatik günlük zamanlayıcılar bekliyor. Tam kumaş–eşya kesişmesi ve ağır eşyalı sahnede performans hâlâ açık; tamamlanmış diye sunma. Yennefer/Ciri gerçek rig incelemesi `MODEL_DONUSUM_INCELEMESI.md` içinde, VRM çıktıları henüz yok. Aşağıdaki kayıtlar önceki teslimin ayrıntılarıdır; güncel dosyanın ilk bölümleri önceliklidir.

En son: solda açılıp kapanan ayrı sohbet listesi ve Yeni sohbet eklendi. `chat_store.py` atomik yerel `chats.json` arşivi tutar; son değişen mesajdan beş gün sonra siler (açılışta ve açıkken dakikada bir, etkin yanıt/ses bitince). Sadece okumak veya sesi kapatmak süreyi uzatmaz. Eski `chat_history.json` başarılı taşımadan sonra kaldırılır. API geçmişi, bekleyen şehir sorusu ve web sohbet URL'leri seçili sohbetle sınırlanır; açık ses/yanıt sırasında sohbet değiştirilemez. Bu yerel silme kuralıdır; sağlayıcı hesabındaki sunucu kayıtlarını silmez.

Kullanıcı 15 Ekim'de açıkça “yumiye özel olarak bu geçmişi paylaşmayı onaylıyorum” dedi. Önceki otomatik onay engelinin istediği izin alındı ve aktarım bağlandı. Yalnız seçili Yumi sohbetinin son 24 tamamlanmış mesajı, toplam en fazla 16.000 karakter (mesaj başına 4.000) yeni Gemini Live oturumuna özel stdin üzerinden aktarılır. Diğer sohbetler, eksik yanıtlar, argüman/env/geçici dosya/log üzerinden metin aktarımı yok. Worker `--history-stdin` yalnız uygulama/worker modunda kabul eder, ilk satırı kontrol dinleyicisi başlamadan okur; STOP ile erken iptal desteklenir. İlk setup'ta `historyConfig.initialHistoryInClientContent=true`, ardından context turns gönderilir; geçmiş kendi başına yanıt üretmez. Resume'da yeniden gönderilmez. `work/check_live_history.py`: gerçek alt süreç borusu, STOP, sınırlar, setup sırası, boş geçmiş ve resume tekilleştirmesi geçti. `work/check_live_history_service.py`: gerçek Gemini bağlantısı history + hava aracı şemasını kabul etti; yapay “papatya” geçmişini yeni soruda doğru hatırladı. Mikrofon/hoparlör açılmadı, gerçek kayıtlı mesajlar kullanılmadı. Değişiklik için açık eski Yumi sürecinin yeniden başlatılması gerekir.

Sesli hava durumu: `live_voice/weather_tool.py` Open-Meteo sorgusu ve araç bildirimi eklendi. Live setup tools listesine bağlandı; asenkron cevap, iptal, eski socket'e yanıt vermeme, eşzamanlı istek sınırı var. Sahte websocket kontrolleri ve Ankara için gerçek Open-Meteo çağrısı geçti; gerçek Gemini ses oturumuyla uçtan uca kabul yapılmadı. Adla çağırma: geçici hata artık kullanıcı seçeneğini kalıcı kapatmıyor; iki/dört/altı saniye aralıklı en fazla üç tekrar, desteklenmeyen adda açık hata var. Dictionary David/Leyla/Mika için çevrimdışı geçti. Kayıtlı `name_wake_enabled` tekrar açıldı, diğer güncel ayarlar korundu; çalışan eski süreç bu ayarı henüz yeniden yüklemedi.

Konuşma kolları daha aşağıda/gövdeye yakın, dirsek yönü ortak düzeltildi. 4.608 hedef pozu ve dört modelin gerçek çizimleri kontrol edildi. Sonetto'da iç/dış pelerin aynı konumda ters normallere sahip; yanlış çift taraflı gövde malzemesi düzeltildi, yedek alındı ve VRM yeniden kitaplığa kopyalandı. Kullanıcı yürüyüş/dönüş kabulü açık. `FIZIK_DURUMU.md` kapsam ve açık işleri içerir. `YUMI_3D_INDIRME_LISTESI.md` öncelikli 13 eşya ve mutfak/ek senaryo paketlerini listeler. Eşya yükleyicisi, oturma/tutuş sahneleri, ritim/genre analizi ve ayakkabı/görev çubuğu ankrajı hâlâ açık. Açık Yumi yeniden başlatılmadı.

Son ekler: `YUMI_DAVRANIS_TASARIMI.md` son kullanıcı kararlarını içerir: tam ekran oyunda duraklatma, 30 müzik ailesi, ritim takibi, masa/kitap/TV/mutfak, zamanlı mola ve yumuşak geri dönüş, el/bilek/kumaş temas ön koşulları. Tam ekran koruması uygulandı ve izole Qt testinden geçti; senaryo sahneleri ve müzik analizi henüz uygulanmadı. Sonetto'nun kullanıcı tarafından işaretlenen havadaki `Glasfeder` aksesuarı kaldırıldı; çıktı 15.461.976 bayt. Önceki aksesuarlı sürüm `work/sonetto/Sonetto-with-accessory.vrm` içinde korunur.

Kaynak: `yumide nerede kalmıştık` sohbeti (01a13c21-586d-77b3-9dfc-669e73862485), son kullanıcı kararları ve yerel çıktılar. Eski CALISMA_PLANI.md ve README.md'deki ses/animasyon durumları güncel uygulamayı tam yansıtmıyor.

## Kaldığımız somut iş

Sonetto `[Reverse1999]_Sonetto_Basic.blend` modelini VRM'ye dönüştürme isteği yarım kalmıştı. Bu oturumda Blender arşivi tamamlandı (ZIP CRC kontrolü geçti), resmî VRM eklentisi indirildi (SHA-256 sürüm bilgisiyle eşleşti) ve dönüşüm yapıldı. Kaynak dosya değiştirilmedi. İlk inceleme 176 kemik, temel şekil dahil 61 farklı şekil anahtarı ve hazır animasyon bulunmadığını gösterdi.

Çıktı: `skins/Sonetto.vrm`, 15.500.448 bayt. Yumi'nin kitaplığına eklendi; etkin karakter/ses/ayar değiştirilmedi. Yumi yükleyicisinde 53 humanoid/parmak/eye eşlemesi birebir doğrulandı; 15 dolu ağız/yüz ifadesi, üç gömülü temel renk dokusu ve 48 yay grubu var. 12 jest ve 66 klibin beşer fazdaki dönüşümleri sonlu kaldı. `work/sonetto/Sonetto-preview.png` mevcut Yumi GPU çizicisinden alındı ve incelendi. Bunlar tüm hareketlerin doğal olduğuna veya kumaş temasına genel kabul değildir.

Özgün Eevee matcap/ışık malzemeleri temel renk dokulu MToon'a sadeleştirildi. Özel maskelerin tüm görünüş etkileri birebir taşınmadı. Saç/etek/aksesuar temasının tam hareketli görsel kabulü ve yeni modelle gerçek canlı konuşma kabulü açık.

Çalışma klasörü: `work/sonetto`. Kaynak modele ve mevcut kullanıcı ayarlarına dokunmadan dönüşüm yapılacak. Çıktıda humanoid/parmak kemikleri, ağız ve mimik eşlemesi, dokular, malzemeler ve saç/etek fiziği denetlenmeli. Özgün lisans/attribution bilgisi korunmalı; dağıtım izni varsayılmamalı.

## Son sohbette uygulananlar

- Gemini canlı ses, oynatılan ses düzeyine bağlı ağız ve konuşma metnine göre jest/mimik seçimi bağlandı.
- Sessizlik sınırı 4 saniye; konuşma ve oynatma sırasında oturum kapanmamalı.
- Karakter profiline bağlı adla uyandırma ve ayrı seslenme yazımı eklendi. Balıkesir/şehir ayarı canlı oturuma bağlandı. İnsan mikrofonuyla genel kabul ayrıca açık.
- Sesli hareket komutları eklendi; hareket komutlarına fazladan model yanıtını susturma düzeltildi.
- Kullanıcının onayladığı kısa adımlı yürüyüş, rahat el/parmak pozu, saç düzeltmesi uygulandı. Bacak kesişmesi iki modelde düzeltildi. Adımlı dönüş ve tam kıyafet çarpışması eksik.
- Önceki sohbet iskeletli GLB desteğinin eklendiğini raporluyor. Ancak bu oturumda okunan `skins.py` yalnız `.vrm` kabul ediyor; GLB desteğini mevcut kaynak için tamamlanmış sayma. Sonetto bu yüzden gerçek VRM olarak teslim edildi.
- 12 jest kategorisi ve toplam 66 animasyon mevcut; bunlar 120 bitmiş senaryo anlamına gelmiyor.
- Etek savrulması için sönüm ve 12 derece sapma sınırı eklendi; tam kumaş simülasyonu değil.
- Son FPS ölçümleri yaklaşık 180/159 ortalama; 197 üst sınır isteği var, minimum 100 FPS kabulü açık.

## Mimik ve vücut dili listesi

Mevcut 12 kategori: selamlama, sevinç, üzüntü, özür, teşekkür, uyarı, kararsızlık, cesaretlendirme, onay, ret, soru ve açıklama. “Tamamdır” baş sallama seçiyor; parmaklarla OK işareti henüz yok. Model yetenekler hakkında bilgilendiriliyor, uygulanmış hareketin görüntüsünü veya geri bildirimini almıyor.

120 senaryo kapsamı için eksikler:

- Dinleme: dikkatli bakış, küçük onaylar, düşünme, kullanıcıya dönme.
- Konuşma: açık avuç, işaret etme, omuz silkme, parmakla OK, başparmakla onay.
- Tepkiler: kahkaha, alkış, irkilme, gerilme, hayal kırıklığı.
- Günlük eşlik: esneme, sıkılma, uyuklama, otururken pozisyon değiştirme.
- Geçiş: yürüyüş/dinleme, oturma/konuşma, dans/bekleme arasında doğal geçişler.
- Seçim: doğru anda doğru hareket, şiddet ve zamanlama; salt animasyon sayısını artırmak yeterli değil.

120 senaryonun tek tek numaralı tam listesi bu sohbetin okunabilen mesajlarında bulunmadı; yeniden üretildi diye sunulmamalı. İlgili diğer kaynak sohbet: `YUMI VRM hareketlerini iyileştirme planı`.

Ücretli paketler satın alınmadı. MetaHuman yüz sistemi ve Game Animation Sample'ın tüm klipleri aktarılmadı. Ağır model/GPU testleri ve sınırsız bellek kullanımı yeniden başlatılmamalı. Projenin 6 GiB toplam/4 GiB süreç koruması korunmalı.

## Bu oturum

Canlı metin birleştirmesinde `delta` parçası önceki metinle başlıyorsa yanlışlıkla öncekinin yerine geçiyordu. Baloncuk ve jest metni artık yalnız `snapshot` olayında değiştirilir; `delta` daima eklenir. Art arda aynı kelime/hece kaybolmamalı. Canlı kullanıcı testi yapılmadı.

`work/check_native_text_merge.py`: altı tekrar/snapshot örneği, baloncuk-jest tutarlılığı ve kaynak derleme kontrolü geçti. `vrm.py` artık VRM0 `unknown` ifadelerinde gerçek adları kullanıyor; şaşırma/kızarma/gözyaşı birbirini ezmiyor. Konuşma katmanının sağ/sol göz kırpma adları VRM0 ve VRM1 anahtarlarıyla eşleştirildi. Sonetto yükleme/jest/klip kontrolü bu düzeltmelerden sonra yeniden geçti. Bağımsız kod onayı veya canlı mikrofon testi yapılmadı.
