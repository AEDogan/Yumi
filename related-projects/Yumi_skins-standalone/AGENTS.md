# Proje çalışma kuralları

<!-- BEGIN CODEBASE MAP -->
## Dosya haritası ve dar kapsamlı arama

- Mevcut `DURUM.md` başlangıç kuralı varsa onu koru. Kod keşfine başlamadan önce kökteki `CODEBASE_MAP.md` dosyasını bir kez oku.
- Haritadan görevle ilgili yolu seç; önce yalnız o dizinde `rg -n -m 20` ile hedefli arama yap. Dosyaların yalnız gerekli satır aralıklarını oku; çıktıyı kısa tut.
- Sonuç bulunamazsa önce ilgili dizinde dosya adlarını `rg --files` ile ara; kapsamı aşamalı genişlet. Her görevde tüm proje ağacını veya içeriklerini dökme.
- Harita bir yönlendirmedir; güncelliğini ilgili yolların varlığıyla doğrula. Eksik/eski kayıt işin ilerlemesini engellemez.
- Bağımlılık, derleme, önbellek, model, medya, arşiv ve gizli ayar dosyalarını görev gerektirmedikçe tarama. `.env` içeriğini haritaya/çıktıya taşıma.
- Önemli dosya/dizin taşınır veya eklenirse yalnız ilgili harita kaydını güncelle. Her görevde haritayı yeniden üretme. Kaynak kodun doğruluğunu harita özetinden varsayma.
<!-- END CODEBASE MAP -->
