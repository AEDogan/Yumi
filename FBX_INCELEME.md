# FBX denemesi ve mevcut karakterlere aktarım

15 Ekim 2026. Orijinal FBX dosyaları değiştirilmedi; tüm inceleme ve dönüşümler `work/fbx_sources` içindeki kopyalarda yapıldı. VRM üretmek gerekmedi: Ludovisions, GLB ve dosyanın SHA-256 özetine bağlı yerel humanoid eşleme dosyasıyla Yumi'nin gerçek karakter işleme hattında çalıştırıldı.

## Hangi FBX kullanılabilir?

| Dosya | Bulunan durum | Karar |
|---|---|---|
| ludovisions_FC1.fbx | 102 kemik, 427.757 ağırlıklı vertex, 498.894 üçgen, gömülü dokular, yüz/ağız morphları | Gerçek hareketli karakter denemesi başarılı; kütüphane yayını ve performans sadeleştirmesi bekliyor |
| AnimeBoy1.fbx | İskelet ve vertex ağırlığı yok; eksik harici dokular | Şu an animasyonlu karakter olarak hazır değil |
| Boy2.fbx | Aynı eksikler | Hazır değil |
| Female_Human.fbx | Aynı eksikler | Hazır değil |
| Girl2.fbx | Aynı eksikler | Hazır değil |
| GothicDressGirl.fbx | Aynı eksikler | Hazır değil |
| RedTechwearGirl.fbx | Aynı eksikler | Hazır değil |
| WhiteWeddingDressGirl.fbx | Aynı eksikler | Hazır değil |

Deneme çıktısı: `work/fbx_sources/Ludovisions_FC1-Tpose.glb` ve yanındaki `.humanoid.json`. UI karakter kütüphanesine henüz eklenmedi. Kaynak lisansının koşulları bu incelemede doğrulanmadığından dağıtım yapılmadı.

## Çözülen kol sorunu

Kaynak Ludovisions A-pose, hareketlerin kaynak iskeleti T-pose idi. İlk denemede T-pose hareketleri A-pose dinlenme açısına eklendiği için kollar gövdeye giriyordu. `work/normalize_fbx_rest.py` yalnız deneme kopyasının dinlenme pozunu T-pose'a getirdi; geometri, normal ve morph farklarını aynı skin dönüşümüyle taşıdı, inverse bind matrislerini yeniledi. Eski trial kopyası da korundu.

Gerçek GPU karşılaştırması: `work/fbx_sources/ludovisions-tpose-diagnostic.png`. Dört hareket: `work/fbx_sources/ludovisions-preview.png`. Kollar ve eller artık görünür; bu görüntüler bütün hareketlerin estetik açıdan tamamlandığı anlamına gelmiyor. Özellikle wave klibinin eğilme karakteri ve kumaş/temas kabulü ayrıca değerlendirilmelidir.

Deterministik kontrol: `work/check_fbx_trial.py`. İskelet, üçgen indisleri, UV'ler, skin ağırlıkları, morph sayıları korundu; idle/walk/wave/listen ve altı el jestinde sonlu matris kontrolleri geçti. Bunlar tüm kumaş kesişmelerinin olmadığı garantisi değildir.

## Bu modelden mevcut VRM'lere ne alabiliriz?

**Evet, ifade anlamlarını ve zamanlamasını ortak kullanabiliriz.** Gülümseme, kaş kaldırma, göz kısma, şaşırma ve dudak senkronunu aynı semantik komutlarla her modelin kendi mevcut morphlarına yönlendirmek yararlı olur.

Ludovisions yüzünde 148 gerçek morph hedefi var (149 shape-key kaydı Basis dahil); dil/ağız meshinde ayrıca 37, iki yardımcı meshte birer hedef var. İlk GLB eşlemesine beş sesli ağız şekli, iki bağımsız göz kırpma, gülümseme, sakin, üzgün, kızgın ve şaşırmış ifadeleri bağlandı.

| Paylaşılabilecek davranış | Ludovisions örneği | Diğer modele uygulanış |
|---|---|---|
| Gülümseme | Mouth_Smile_L/R | Mevcut happy/joy veya sağ-sol smile hedefi |
| Şaşırma | Eye_Wide, iç kaş yükseltme, V_Open | surprised varsa tam; yoksa mevcut ağız ve göz hedefleriyle sınırlı |
| Şüphe/düşünme | Tek taraflı kaş kaldırma, göz kısma | Bu bağımsız hedefler varsa; yoksa daha genel ifade |
| Konuşma | V_Open, V_Wide, V_Tight_O vb. | Her karakterin a/i/u/e/o ya da aa/ih/ou/ee/oh hedefleri |
| Göz kırpma | Eye_Blink_L/R | Karakterin kendi blinkLeft/Right veya blink_l/r hedefleri |
| El/kol hareketi | Humanoid kemik hareketleri | Kemik ölçülerine göre retarget ve sonrasında IK/temas düzeltmesi |

**Morph vertex farkları doğrudan kopyalanamaz.** Farklı yüzlerde vertex sayısı, sırası ve topoloji farklıdır. Bu dosyadaki 148 yüz hedefini başka yüze eklemek, o yüzü otomatik olarak aynı ifadelerle donatmaz. Eksik hedef için o modele özel yeni sculpt/deformasyon işi gerekir. Twist, dil, yüz ve yardımcı kemikleri de aynı adla eklemek tek başına yarar sağlamaz; ilgili mesh ağırlıkları ve rig mantığı gerekir.

`work/fbx_sources/reuse-report.json` mevcut dört VRM'nin desteklediği ifade adlarını listeliyor. Bir modelde 75 ifade bulundu; diğerlerinde 13, 14 ve 16 ifade var. 16 Ekim güncellemesinde `model_analysis.py` ortak destek haritası runtime konuşma/klip/göz kırpma yoluna bağlandı. Her modelin mevcut hedefleri kullanılır; eksik duygular uydurulmaz. Yeni yüz şekli sculpt edilmedi. Ayrıntı `YUMI_MODEL_ANALIZI.md`.

**Dosyadaki action yeni bir hareket kütüphanesi sağlamıyor.** Kaynak action 2–251 kare aralığında 1.020 eğri içeriyor ancak hiçbir eğride değişen değer yok. `work/check_fbx_source_action_blender.py` ile ölçüldü; yürüyüş/dans/oturma klibi varmış gibi sunulmamalı. Yumi'de görülen hareketler mevcut Yumi hareketlerinden retarget edildi.

## Açık işler

- 499 bin üçgenlik karakterin morph ve görünümünü koruyarak ekran ölçeğine uygun LOD/sadeleştirme.
- Dört hareket, konuşma ve oturma için daha uzun görsel kabul; yardımcı twist deformasyonu kontrolü.
- GLB+eşleme dosyası için kütüphane içe aktarma akışı.
- Temel ifade destek haritası ve mevcut ağız/göz fallback'i eklendi; gelişmiş kaş/yanak ifadeleri, şiddet ayarı ve görsel kabul açık.
- Mobilya/kumaş çarpışması ve gerçek minimum FPS kabulü; bunlar bu FBX çalışmasıyla çözülmüş sayılmıyor.
