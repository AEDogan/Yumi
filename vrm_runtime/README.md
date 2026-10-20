# Yumi · three-vrm entegrasyonu

Seçim: **@pixiv/three-vrm 3.5.5**, **three 0.180.0**. UniVRM Unity gerektirdiği için mevcut Python/Qt uygulamasında daha büyük bir platform geçişi olurdu.

## Şu anda çalışan yollar

- `spring_worker.mjs`: kaynak VRM0/VRM1 SpringBone bildirimlerini değiştirmeden resmi `VRMSpringBoneLoaderPlugin` ile yükler. Kalıcı, gizli, yerel Node sürecinde resmi manager çalışır. Python hareket/IK pozu girer, ikincil kemik dönüşleri çıkar. JSON standart giriş/çıkış kullanılır; ağ portu ve model yüklemesi yoktur.
- `../three_vrm_runtime.py`: süre sınırlı, sıralı taşıma; kaynak ölçeği/negatif determinant korunur. Taşıma başarısızsa kaynak poz korunur, eski çözücüye sessizce dönülmez. Masaüstünde tek uyarı gösterilir. Mevcut mobilya temas adaptörü resmi simülasyonun ardından uygulanır; bu adaptör tam kumaş çözücüsü değildir.
- `viewer.html`, `viewer.mjs`, `../three_vrm_view.py`: model ekleme ekranında gerçek Three.js/VRMLoaderPlugin/MToon/SpringBone önizlemesi. Kaynak dosyalar yereldir; dış ağ ve seçilen VRM dışındaki yerel dosyalar engellenir. Önizleme yüklenmeden model ekleme kabul edilmez.
- Eski giysi sarkıtma/pelvis projeksiyonu three-vrm üzerinde ikinci kez uygulanmaz. Kaynak pantolon/gömlek geometrisi değiştirilmez.

## Masaüstü çizimi ve kalan sınırlar

Masaüstünün varsayılan yolu `../desktop_vrm.py` üzerinden Three.js/VRM/MToon çizimidir. Python animasyon, IK, kaynak SpringBone ve eşya yerleşimini hesaplar; `desktopFrame` son düğüm/morph/eşya matrislerini çizip şeffaf Qt katmanına aktarır. Aynı poza ikinci fizik veya önizleme RAF döngüsü uygulanmaz. OpenGL yükleme/hata geri dönüşü ve `YUMI_DESKTOP_RENDERER=legacy` tanı yolu korunur. İlk kare derlemesi 20 saniye, sonraki kareler 5 saniye ile sınırlıdır. Model nesli değişince eski eşya/kare sonuçları yok sayılır; gizleme ve kaldırma kardeş Qt katmanını da kapatır.

Beş model geçişi ve iki modelde sekiz gerçek sahne görüntüsü incelendi; hızlı seçim, boyutlandırma, duraklatma/dönüş ve model kaldırma testleri geçti. Tüm materyal/ifade/senaryoların görsel kabulü veya performans hedefi tamamlanmış sayılmaz. IK/koreografi kalitesi ve tam saç/kumaş/beden öz çarpışması ayrı işlerdir. SpringBone bunları otomatik çözmez; kaynakta fizik veya collider bulunmaması eksik veri olarak kalır. Mevcut mobilya adaptörü SDK'nın iç integratör durumuna temas geri bildirimi göndermediğinden uzun temaslarda ayrıca kabul gerekir.

## Kurulum ve çalışma

Node.js PATH üzerinde bulunmalı. Bu makinede kurulu Node.js kullanılır; yeni makine dağıtımına Node eklemek ayrıca gerekir. Çalışırken npm/internet kullanılmaz.

```powershell
cd C:\Projeler\Yumi\vrm_runtime
npm.cmd ci --ignore-scripts --no-audit --no-fund
```

Tam sürümler `package-lock.json` içindedir. Eski çözücü yalnız tanısal A/B için `YUMI_VRM_RUNTIME=legacy` ortam değişkeniyle seçilebilir; kullanıcı ayarına kaydedilmez.

## Doğrulama

- `work/check_three_vrm_runtime.py`: beş gerçek rig, kaynak hashleri, sonlu poz, kemik uzunlukları, saat sıfırlama.
- `work/check_three_vrm_contract.py`: VRM1 kapsül, kaynak katsayıları, gerçek kuvvet yanıtı ve bozulmadan hata durumu.
- `work/render_three_vrm_models.py`: beş gerçek VRM'nin resmi çizici görüntüsü.
- Mevcut senaryo, pole destek/çıkış ve model preset testleri ayrıca çalıştırılır; başarılı sayısal kontrol tek başına görsel kalite onayı değildir.

## Lisanslar

three-vrm ve Three.js MIT lisanslıdır. Paketlerin lisans metinleri `node_modules/@pixiv/*/LICENSE` ve `node_modules/three/LICENSE` içinde korunur. Kaynaklar: https://github.com/pixiv/three-vrm ve https://github.com/mrdoob/three.js . VRM dosyalarının kendi kullanım koşulları bağımsızdır; entegrasyon bunları değiştirmez.
