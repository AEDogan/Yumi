# Yumi model paketleri

Uygulama yalnız güvenilen yayıncı tarafından imzalanmış `.yumimodel` dosyalarını alır. Paket üç dosyadan oluşur: `model.vrm`, `manifest.json`, `manifest.sig`. Kod veya çalıştırılabilir dosya içermez. VRM içindeki iskelet eşlemesi, ifadeler ve fizik verileri korunur; hareketler paketin `yumi-v1` çalışma sözleşmesiyle Yumi tarafından yürütülür.

Manifest: format `yumi-model-package`, version 1, runtime `yumi-v1`, publisher, name, model_sha256, acceptance. Kabul raporu suite `yumi-character-v1`, model_sha256 ve checks sözlüğü taşır. rig, idle, walk, sit_stand, dance, contacts, expressions, hair_cloth alanlarının tamamı gerçek test ve görsel kabulden sonra `pass` olmalıdır. Bu raporu doldurmak testlerin yerine geçmez; yayıncı yalnız doğruladığı modeli imzalar. Henüz hiçbir Witcher modeli bu aşamayı tamamlamadı.

Yayıncı aracı: `publish_model_package.py --key PRIVATE.pem --model MODEL.vrm --name Clara --group anime --report acceptance.json --output Clara.yumimodel`. Özel anahtar uygulamayla dağıtılmaz; güvenilen açık anahtarlar assets/characters/package-trust.json içindedir. Yeni anahtar üretimi yayıncıda `--init --key PRIVATE.pem` ile yapılır; mevcut anahtar üzerine yazılmaz. `cryptography` bağımlılığı requirements.txt içinde.

Yeni paket kurulumunda imza, içerik hash'i, sürüm, kabul raporunun modele bağlılığı ve gerçek humanoid hiyerarşisi doğrulanır. Paket adı kullanıcı tarafından değiştirilemez. Eski kişisel ad/seslenme ayarları aktivasyonu değiştirmez; Türkçe okunuş eşlemeleri korunur. Eski modeller yalnız legacy-models.json içindeki hash'leri aynıysa korunur; bu istisna yeni ham VRM yükleme yolu değildir ve fizik kabulü anlamına gelmez.

Gerileme kapısı: yeni model/iskelet/hareket/fizik değişikliği sonrası oturma-kalkma, yürüyüş, dans, eşya temasları, mimik ve saç/etek tüm onaylı modellerde yeniden kontrol edilmelidir. Başarısız veya eksik kontrol yayınlanamaz. Tam otomatik görsel/fizik test paketi sonraki aşamadadır.

## Paket aileleri
Model manifestindeki imzalı `group` zorunludur: `anime`, `retro` veya `witcher`. Mevcut 16 VRM Anime, Clippy Retro grubundadır. Witcher grubu ayrılmıştır; modeller kabul edilmeden kataloğa eklenmez. Kütüphane ve sağ tık menüsü aynı grupları kullanır. Bunlar paket aileleridir; bu değişiklik mevcut kabul edilmemiş modelleri toplu dağıtım arşivine veya onaylı pakete dönüştürmez.
