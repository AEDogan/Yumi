# Yumi ortak model incelemesi — 16 Ekim 2026

Son güncelleme17Ekim: şema4 gerçek kaş/yanak/göz hedeflerini anlamsal kontrollere eşler; eksik hedef uydurmaz. Dört rigde David11 gelişmiş kontrol içeriyor, diğerleri temel ifade hedeflerini kullanıyor. İfade katmanında aynı morph'a gelen en yüksek katkı korunur; zayıf rahat ifade güçlü gülümsemeyi ezmez. `work/check_expression_controls.py` ve gerçek çizici görüntüsü kontrol edildi.

Önceki şema3 düzeltmesi korunur: yalnız primitive indekslerinde gerçekten çizilen noktalar ölçülür; ortak buffer'ın kullanılmayan vertexleri bölge/mimik maskesinde0kalır. `vertices_buffer` ve `referenced_vertices` ayrı kaydedilir. Karakter bounds, taban ve beden kapsülü örnekleri aynı düzeltmeyi paylaşır.

Mobilya temasında gerçek yüzey outline'ı, hips/femur offseti, kıyafetli uyluk hacmi ve çokkatmanlı katı kolonları kullanılıyor. Açık kolonlar belirsizdir. Enfazla192kıyafetörneği yalnız mevcutclothspringkemiklerini sınırlı döndürür; tamkumaş/softbody veya bütünmeshkesişmesizliği değildir.

`model_analysis.py` artık VRM/GLB karakter yükleyicisinde ve eşya yükleyicisinde çalışır. Her kare ağır tarama yapmaz. Karakter profilinin bellekteki adresi `model.data.analysis`, eşyanınki `asset.analysis` olur.

## Kaydedilen bilgiler

- Mesh/material/node bağlantıları, üçgen/vertex sayıları, görünüm malzemesi ve adından gelen **doğrulanmamış** bölge ipuçları.
- Humanoid kemikleri ve parmaklar; mesh üzerindeki kemik etkilerinin ağırlıkları ve anatomik üst kemiği. Aynı primitive birden fazla bölgeyi içerebilir.
- Yüz ifadesi bağları ve modelde gerçekten olan ifadeler. Ortak ağız/göz/duygu komutları karakterin kendi hedeflerine çözülür; olmayan duygu uydurulmaz. VRM1 özel ifadeleri de okunur.
- VRM0/VRM1 kaynak yay zincirleri ve yazarın yazdığı katsayılar. Bir yayı takip eden saç/kıyafet etkisi, tam kumaş fiziği demek değildir.
- Kaynağın SHA-256 özeti, GLB humanoid eşlemesinin ayrı özeti, profil şeması sürümü. `work/analyze_models.py` bunlarla anahtarlanan JSON önbelleği üretir.

`region_weights` parmak/el/kol/bacak/baş gibi kemik etkileri için sanal vertex maskesi verir. `expression_mask` belirli yüz ifadesinin gerçekten oynattığı vertexleri gösterir. Bunlar kaynak geometriyi kesmez, UV/morph/skin bağlantısını bozmaz ve ek çizim çağrısı oluşturmaz. Baş ağırlığı tek başına göz/ağız sınırını kanıtlamaz; bu bölgeler kaynak ayrımı veya yüz şekilleri yeterliyse daha ayrıntılı bulunabilir.

## Sertlik ve esneklik sınırı

PBR renk, pürüzlülük ve metal değerlerinden kumaş sertliği, sürtünme, kalınlık veya bastırılınca çökme katsayısı çıkarılmıyor. Eksik mekanik değerler `unknown`/`null` kalır. Statik çizilen bir eşya da sırf bu yüzden fiziksel olarak katı kabul edilmez. Bu ayrım [glTF malzeme tanımı](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html) ve [VRM yay tanımı](https://github.com/vrm-c/vrm-specification/blob/master/specification/VRMC_springBone-1.0/README.md) temel alınarak yapıldı.

Henüz eksik: doğrulanmış mekanik profil düzenleme arayüzü; yeni malzeme katsayılarını çözücüye uygulama; otomatik tam anlamsal yüz/giysi segmentasyonu; sürekli yüzey çarpışması, gerçek kumaş/soft-body çözümü ve PC sandalyesi geçiş kabulü. Analiz profili bu işleri mümkün kılan kayıt katmanıdır, kendisi fizik çözücüsü değildir.

## Tekrar kullanılabilir beceriler

- Proje içi `.agents/skills/yumi-model-analysis/SKILL.md`; aynı beceri yerel Codex becerilerine kuruldu. Yeni model/retarget/fizik/sadeleştirme işinde ölçümleri yeniden kullanmayı ve gerekli tek kabul kontrolünü tarif eder. Beceri doğrulayıcısı geçti.
- [kajisho5/blender-skill](https://github.com/kajisho5/blender-skill) `blender-asset-qa` klasörüne indirildi ve yerel laptop kopyasında `info.py --skip-uv-overlap-check` çalıştırıldı. Rapor `work/blender-skill-laptop-qa.json`. Bu araç genel geometri denetimi yapar; malzemenin fiziksel türüne karar vermez. Hiçbir model buluta gönderilmedi.

## Kabul kaydı

Dört mevcut VRM'de profil, sonlu anatomik maskeler, ağırlık toplamları ve JSON çıktısı geçti. Sentetik birleşik meshte parmak/ağız maskesi, kaynak yay katsayısı ve bilinmeyen mekanik değer sınırları denetlendi. Ludovisions ayrıca aynı şemayla incelendi. Kaynak dosyalar değiştirilmedi. Oturma/zemin/giysi kabulü kendi testleri ve gerçek görüntüleriyle ayrıca değerlendirilir.
