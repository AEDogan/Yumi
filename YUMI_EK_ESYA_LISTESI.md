# Yumi — sıradaki indirilecek eşyalar

15 Ekim 2026. Senaryoların ana kaydı `YUMI_SENARYO_LISTESI.md`. Mevcut koltuk/sehpa, PC, TV, TV sehpası, kumanda, kitap, kupa ve patlamış mısır tekrar indirilmeyecek.

## Gelen ve kopyası hazırlanan 17 yeni eşya

Optimize yerel kopyalar `items/alternatives` içinde; orijinaller korunuyor. Bunlar sahnede temas/ergonomi kabulü yapılmış eşyalar sayılmıyor. Sayfa/kapak gibi kaynak animasyonların korunması, runtime etkileşiminin bağlandığı anlamına gelmiyor.

| Gelen dosya | Hazır kopya / sıradaki kontrol |
|---|---|
| notebook.glb | Kopya hazır; el tutuşu, yazma ve sayfa/kapak animasyonu bekliyor |
| window (1).glb | Kopya hazır; yerleşim/cam kontrolü bekliyor; ilk pencere adayı |
| window.glb | Alternatif hazır; yerleşim/cam kontrolü bekliyor |
| void_frame_studio__coffee_machine.glb | Kopya hazır; ilk makine adayı; fincan ve el erişimi bekliyor |
| coffeemachinemodel_archviz_productdesign_free.glb | Alternatif hazır; cam/hazne görünümü ayrıca kontrol edilmeli |
| low-poly_modern_laptop_with_closing_animation.glb | Kopya hazır; masa/diz teması, menteşe ve runtime kapak kontrolü bekliyor |
| desk_lamp.glb | Kopya hazır; masa yerleşimi ve ışık bağlantısı bekliyor |
| flat_wooden_tray.glb | Kopya hazır; eşya ve el temasları bekliyor |
| glass_water_jug_high_poly.glb | Kopya hazır; el tutuşu, cam görünümü ve doldurma davranışı bekliyor |
| headphones.glb | Erkek karakterler için kullanıcının seçimi; 1.947.759 → 119.980 üçgen, bant/kulaklık görsel kontrolü geçti; kafaya oturtma bekliyor |
| cute_cat_headphones.glb | Kız karakterler için kullanıcının seçimi; 270.904 → 59.988 üçgen, bant/kulaklık görsel kontrolü geçti; saç/kafa teması bekliyor |
| pen_holder.glb | Kopya hazır; bağımsız kalemin alınıp alınamayacağı ve masa yerleşimi bekliyor |
| modern_slatted_wooden_tv_stand.glb | Alternatif hazır; TV ile ölçü/temas kontrolü bekliyor |
| boombox.glb | Kopya hazır; müzik sahnesine bağlantı bekliyor |
| furniture__no-27.glb | Dört karakter ölçüsü ve David/Sonetto GPU oturuş kontrolünden sonra aktif rastgele koltuk havuzuna alındı; genel kumaş kabulü açık |
| generic_television_set.glb | Alternatif hazır; TV sehpasıyla yerleşim bekliyor |
| mid_century_lounge_chair.glb | Dört karakter ölçüsü ve David/Sonetto GPU oturuş kontrolünden sonra aktif rastgele koltuk havuzuna alındı; genel kumaş kabulü açık |

Gelen pencere ve kahve makinesi alternatiflerinin son seçimi render/temas kabulünde yapılacak; sırf iki dosya geldiği için ikisi aynı anda sahneye eklenmeyecek. Kulaklıklarda kullanıcının kız/erkek tercihi korunacak; hangi karaktere hangi varyantın takılacağı profil/ayar üzerinden belirlenecek.

## Gerçekten eksik kalan indirmeler

| Öncelik | Eşya | Seçim ayrıntısı | Senaryo |
|---|---|---|---|
| 1 | Küçük mutfak tezgâhı ve alt dolap | Bütün oda yerine dar bir modül; üst yüzey boş olsun | S16 kahve |
| 2 | Tek kalem, gerekirse | Pen holder içindeki kalem bağımsız kullanılabiliyorsa yeniden indirmeye gerek yok | S08 toplantı/ders |
| 2 | Oyun kumandası | Elde tutulabilir; çok ağır model gerekmez | S12 pencereli oyun |
| 2 | Küçük kaşık | Tepsi geldi; yalnız kaşık eksik | S16 |
| 2 | Su şişesi | Kapak ayrı olabilirse iyi; bardağı mevcut drinkware paketinden karşılama incelenecek | E01 su molası |
| 3 | Tablet / e-kitap okuyucu | Kitap okuma için alternatif, zorunlu değil | E03 |
| 3 | Küçük masa mikrofonu | Ayak ve mikrofon ayrı olabilirse iyi | Toplantı/yayın |

GLB/glTF tercih edilir; dokulu FBX/BLEND de kaynak olarak alınabilir. FBX seçilirse yanında dokuları da bulunsun. Karakter modellerinden farklı olarak bu eşyaların tamamında insan iskeleti gerekmez; yalnız hareket edecek kapak, kol, düğme ve menteşe parçalarının ayrılabilmesi önemlidir. Orta/düşük poligon ve çoğunlukla 1K doku yeterlidir; tüm oda veya çok yüksek poligonlu dekor paketleri gerekli değil.
