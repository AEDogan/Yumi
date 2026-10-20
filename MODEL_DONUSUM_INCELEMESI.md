# Yennefer ve Ciri — kaynak incelemesi

15 Ekim 2026. İnceleme ve Blender'da bellekte deformasyon testi yapıldı. Kaynak GLB'ler değiştirilmedi. Henüz VRM dosyası oluşturulmadı.

| Özellik | Yennefer | Ciri |
|---|---|---|
| Üçgen | 39.378 | 53.249 |
| Vertex / skin ağırlığı bulunan | 24.205 / 24.205 | 35.134 / 35.134 |
| Geçersiz veya ağırlıksız vertex | 0 | 0 |
| GLB skin / joint | 3 / toplam 534 | 1 / 205 |
| Gömülü animasyon | Yok | Motion, 828 kanal |
| Yüz yapısı | Ayrıntılı yüz kemikleri; morph yok | Yüz/göz/çene kemikleri; parçalar üzerinde isimsiz target_0 |
| Dokular | 4 gömülü görsel | 26 gömülü görsel |
| Malzeme | Specular/glossiness dönüşümü gerekli | Standart glTF malzemeleri |

İkisi de sabit kabuk değil. Blender'da sol dirsek kemiği oynatıldığında Yennefer'de 1.970, Ciri'de yaklaşık 2 bin vertex hareket etti. Bu işlevsel skin kanıtıdır; bütün hareketlerde deformasyon kalitesinin onayı değildir.

Ciri ilk dönüşüm adayı olarak daha uygun. İskeletin vücut, parmak, göz ve çene eşlemeleri; referans pozu, yardımcı/ölçek telafi kemikleri ve mevcut animasyonla birlikte doğrulanmalı. `target_0` adları hazır VRM konuşma/mimik seti sayılmaz.

Yennefer'de baş/yüz, gövde ve saç ayrı rig'lerde. Sadece bir rig'e humanoid eşleme koymak diğer parçaları geride bırakabilir. Ağırlıklar ve bind matrisleri korunarak rig'lerin birleştirilmesi veya eşgüdümlenmesi; malzemenin diffuse/specular/gloss dokularının karşılıklarının korunması gerekir.

İkisinde de yüz kemiklerinden en az göz kırpma ve konuşma ağız şekilleri üretilmeli, saç/kıyafet zincirleri uygun spring bone olarak ayarlanmalı. Yürüme, dönme, oturma, parmak jestleri ve dudak eşlemesi gerçek Yumi çiziminde doğrulanmadan kütüphaneye hazır diye eklenmemeli. Tamamen kayıpsız ve sorunsuz dönüşüm şu aşamada garanti edilmez.

Ayrıntılı kaynak sayımları ve hash'ler: `work/character-source-audit.json`. Blender deneyi: `work/character-rig-validation.json`. Kaynak metadata/lisansları raporda korunur; dışarı yükleme veya dağıtım yapılmadı.
