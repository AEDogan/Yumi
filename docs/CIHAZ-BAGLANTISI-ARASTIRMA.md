# Cihaz bağlantıları — araştırma ve yapılacaklar (26 Ekim 2026)

Kapsam: araştırma ve yapılacak kaydı. Hesaba giriş, cihaz eşleştirme, anahtar çıkarma, ağ taraması veya donanım komutu çalıştırılmadı. Ses/bağlantı testi ve günlük senaryo işi sürerken kullanıcı bu konuyu ayrıca listeye eklemeyi istedi.

## Bulgular

Son kullanıcı uygulamaları çoğu zaman geliştirici API anahtarı yerine hesap yetkisi, kullanıcı onaylı QR/kod eşleştirmesi veya fiziksel köprü düğmesi kullanır. Bir defalık kurulumdan sonra saklanan belirteç/sertifika kullanılabilir. Bu yetki, firmadan kullanıcıya verilmesi gereken genel bir geliştirici API anahtarıyla aynı şey değildir. Ayrıca ilk eşleştirmeden sonra komutların mutlaka doğrudan cihaza gitmesi gerekmez; üretici bulutu üzerinden çalışma sürebilir.

- **Tuya / Smart Life:** güncel Home Assistant akışı, uygulamadaki User Code ve uygulamayla taranan QR üzerinden yetkilendirir. Bu bulut entegrasyonu bütün cihaz işlevlerini garanti etmez. Kaynak: [Tuya entegrasyonu](https://www.home-assistant.io/integrations/tuya/).
- **Xiaomi:** Home Assistant xiaomi_miio, desteklenen cihazlarda Xiaomi Home hesabı ve doğru bölge üzerinden cihazın bağlantı bilgisini/tokenını otomatik alıp yerel ağa bağlanabiliyor. Xiaomi'nin resmî Xiaomi Home entegrasyonu ise OAuth 2.0 kullanıyor; yerel veya bulut çalışması cihaz/gateway/bölgeye bağlı. Mop Pro modelinin hangisine uyduğu doğrulanmalı; tüm Xiaomi/Roborock modelleri aynı kabul edilmemeli. Kaynaklar: [xiaomi_miio](https://www.home-assistant.io/integrations/xiaomi_miio/), [resmî Xiaomi Home entegrasyonu](https://github.com/XiaoMi/ha_xiaomi_home/blob/main/README.md).
- **Android/Google TV:** desteklenen Android TV Remote Service ile eşleştirme yolu mevcut. Yumi'de kodla eşleştirme daha önce uygulanmış ve gerçek TV kontrolü kaydedilmiş; bu özellik yeniden yapılacak sayılmamalı. Kaynak: [Android TV Remote](https://www.home-assistant.io/integrations/androidtv_remote/).
- **Matter:** uyumlu cihazlarda telefonla QR/kurulum kodu üzerinden commissioning ve uygun koşullarda başka denetleyiciyle paylaşım destekleniyor. Bu, Matter desteği olmayan eski cihazları otomatik uyumlu yapmaz. Kaynak: [Matter kurulumu/paylaşımı](https://www.home-assistant.io/integrations/matter).

## Mevcut Yumi kodu

`yumi_skills/ui_smart_home_panel.py:332` tüm sağlayıcılara aynı API Key/E-posta/IP ve API Secret/Şifre/Token alanlarını gösteriyor. Bu arayüz son kullanıcıya hangi bilginin gerektiğini açıklamıyor.

`yumi_skills/skills/smart_home_skill.py:224` içindeki Xiaomi yolu `micloud` hesap girişiyle cihaz/token bilgisi alıyor; fiziksel telefon uygulamasına bağlanan evrensel bir köprü değil. Tuya yolu `tinytuya.Cloud` ile geliştirici anahtarı ve secret bekliyor. Hue tarafında fiziksel köprü düğmesiyle kullanıcı oluşturma kodu mevcut. Uygulanmış kodun modern hesap/2FA akışlarında başarıyla çalıştığı bu araştırmada doğrulanmadı.

## Uygulanacak iş paketi

1. Kullanıcının mevcut cihazlarını marka/model, OEM uygulaması, bölge ve desteklenen protokol bazında envanterle. Yapılandırılmış cihazları/sırları çıktıya dökme.
2. Arayüzü sağlayıcıya göre düzenle: Cihazı keşfet → hesap yetkilendir/QR veya kodla eşleştir → cihaz seç → bağlantıyı test et. API key/secret varsayılan zorunlu alan olmasın.
3. Tuya için güncel son kullanıcı QR paylaşım SDK'sını ve Home Assistant köprüsünü değerlendir; Yumi'nin kendi uygulama kimliği/lisans gereksinimlerini doğrula. Başka entegrasyonun OAuth kimliğinin doğrudan kullanılabileceğini varsayma.
4. Xiaomi için mevcut MiCloud yolunun güncel hesap/2FA desteğini ve Mop Pro modelini doğrula; uygun hesap yetkilendirmesi veya Home Assistant adaptörünü seç. Belge/hata mesajlarında bütün markaları tek yerel protokol gibi sunma.
5. Kalıcı belirteç/sertifika saklama, süre yenileme, yetkiyi kaldırma ve yeniden eşleştirmeyi uygula. Şifreleri günlüklere yazma. Yerel/bulut çalışma bilgisini açık göster.
6. Gerçek cihazda kontrollü komut, uygulama/PC yeniden açılışı, IP değişimi, internet kesintisi ve yetki iptali kabulü yap. Hesapla listeleme başarılarını gerçek cihaz kontrolüyle karıştırma.

Home Assistant seçeneği ayrıca kurulmuş ve çalışan bir Home Assistant gerektirir; kullanıcıda varmış gibi varsayılmayacak. Şu an karar: uygun sağlayıcı başına uç kullanıcı bağlantısını destekleyen adaptör tasarımı; uygulama yapılmadı.

## Dar devam yolları
- `yumi_skills/ui_smart_home_panel.py`: marka köprüsü alanları ve TV eşleştirme arayüzü.
- `yumi_skills/skills/smart_home_skill.py`: keşif, kayıt, sync_cloud_bridge_devices ve komut yolları.
- `yumi_skills/android_tv_bridge.py`: mevcut TV eşleştirme/sertifika yaşam döngüsü.
