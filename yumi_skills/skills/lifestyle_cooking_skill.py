import datetime
import urllib.parse
import webbrowser
from typing import Any, Dict


class LifestyleCookingSkill:
    """
    Alexa & Google Asistan Yaşam, Mutfak ve Sağlık Becerileri:
    - Sesli adım adım yemek tarifi rehberi (sayaç önerili)
    - Ergonomi: Su içme, göz dinlendirme ve mola hatırlatıcıları
    - Google 'Call Screen' tarzı profesyonel e-posta ve mesaj taslağı hazırlayıcı
    - 'Telefonumu Bul' (Find My Phone - Google/iCloud veya Pushbullet/Telegram üzerinden zil çaldırma)
    """

    POPULAR_RECIPES = {
        "menemen": {
            "title": "Geleneksel Menemen",
            "servings": "2 Kişilik",
            "ingredients": ["3 adet yumurta", "2 adet domates", "2 adet sivri biber", "1 yemek kaşığı tereyağı/sıvı yağ", "Tuz, karabiber"],
            "steps": [
                "Biberleri ince ince doğrayıp tavada kızdırdığınız yağda hafifçe kavurun.",
                "Kabuklarını soyup küp küp doğradığınız domatesleri ekleyin ve tavanın kapağını kapatıp 8 dakika kısık ateşte pişmeye bırakın. (İsterseniz sizin için 8 dakikalık sayaç kurabilirim).",
                "Domatesler yumuşayınca tuz ve karabiberi ekleyip karıştırın.",
                "Yumurtaları kırın ve sarılarını hafifçe dağıtarak istediğiniz kıvama gelene kadar 2-3 dakika pişirin. Afiyet olsun!",
            ],
            "timer_suggestion_step_index": 1,
            "timer_seconds": 480,
        },
        "makarna": {
            "title": "Kıvamında Makarna",
            "servings": "3 Kişilik",
            "ingredients": ["1 paket makarna", "2 litre kaynar su", "1 tatlı kaşığı tuz", "1 yemek kaşığı zeytinyağı"],
            "steps": [
                "Geniş bir tencerede 2 litre suyu kaynatın ve içine tuz atın.",
                "Kaynayan suya makarnaları ekleyin ve al dente için tam 9 dakika kaynatın. (9 dakikalık makarna sayacı başlatayım mı?)",
                "Makarnayı süzün, isteğe göre tereyağı veya sosla harmanlayıp sıcak servis yapın.",
            ],
            "timer_suggestion_step_index": 1,
            "timer_seconds": 540,
        },
        "mercimek çorbası": {
            "title": "Süzme Kırmızı Mercimek Çorbası",
            "servings": "4 Kişilik",
            "ingredients": ["1 su bardağı kırmızı mercimek", "1 adet soğan", "1 adet havuç", "1 yemek kaşığı tereyağı", "5 su bardağı sıcak su", "Tuz, nane, kimyon"],
            "steps": [
                "Tencerede tereyağını eritip doğranmış soğan ve havuçları 3 dakika soteleyin.",
                "Yıkanmış mercimekleri ve sıcak suyu ekleyin. Kaynamaya başladıktan sonra kısık ateşte 20 dakika mercimekler dağılana kadar pişirin. (20 dakikalık çorba sayacı kurabilirim).",
                "Çorbayı pürüzsüz olana kadar blenderdan geçirin, baharatları ekleyip servis yapın.",
            ],
            "timer_suggestion_step_index": 1,
            "timer_seconds": 1200,
        },
    }

    def recipe_assistant(self, dish_name: str, step_number: int = 1) -> Dict[str, Any]:
        """
        Kullanıcıya adım adım yemek tarifi verir. Belirli bir pişirme süresi olan adımlarda
        Yumi'nin zamanlayıcı başlatması için sayaç süresi önerir.
        """
        dish_key = dish_name.strip().lower()
        matched = None
        for k, v in self.POPULAR_RECIPES.items():
            if k in dish_key or dish_key in k:
                matched = v
                break

        if not matched:
            # Genel yemek tarifi web aramasını hazırla
            url = f"https://www.nefisyemektarifleri.com/ara/?s={urllib.parse.quote(dish_name)}"
            return {
                "ok": True,
                "speech": f"'{dish_name}' için adım adım tarifi web üzerinden buldum, ekrana getiriyorum.",
                "recipe_url": url,
            }

        steps = matched["steps"]
        total_steps = len(steps)
        curr_idx = max(1, min(step_number, total_steps)) - 1
        curr_step_text = steps[curr_idx]

        speech_parts = [f"{matched['title']} - Adım {curr_idx + 1} / {total_steps}: {curr_step_text}"]
        suggest_timer = False
        timer_seconds = 0

        if curr_idx == matched.get("timer_suggestion_step_index"):
            suggest_timer = True
            timer_seconds = matched.get("timer_seconds", 300)
            mins = timer_seconds // 60
            speech_parts.append(f"Bu adım için {mins} dakikalık sayaç başlatmamı ister misiniz?")

        if curr_idx + 1 < total_steps:
            speech_parts.append("Hazır olduğunuzda 'sonraki adım' demeniz yeterli.")

        return {
            "ok": True,
            "speech": " ".join(speech_parts),
            "step_index": curr_idx + 1,
            "total_steps": total_steps,
            "suggest_timer": suggest_timer,
            "timer_seconds": timer_seconds,
            "ingredients": matched["ingredients"],
        }

    def ergonomics_and_hydration(self, action: str = "water") -> Dict[str, Any]:
        """
        Masa başında uzun süre çalışan kullanıcı için sağlık ve ergonomi önerileri:
        - action='water': Su içme hatırlatması
        - action='eyes': 20-20-20 kuralı göz dinlendirme
        - action='posture': Sırt ve dik duruş düzeltme
        """
        act = action.strip().lower()
        if "su" in act or act == "water":
            return {
                "ok": True,
                "speech": "Günün sağlıklı geçmesi için bir bardak su içme vakti! Vücudunuzu susuz bırakmayın.",
                "tip": "Günde en az 2-2.5 litre su tüketmeyi unutmayın.",
            }
        elif "göz" in act or "eye" in act:
            return {
                "ok": True,
                "speech": "20-20-20 kuralı zamanı: Ekrandan uzaklaşıp yaklaşık 6 metre uzaktaki bir noktaya 20 saniye boyunca bakın ve gözlerinizi dinlendirin.",
                "tip": "Göz kırpmayı ve ekran parlaklığını ortam ışığına ayarlamayı unutmayın.",
            }
        else:
            return {
                "ok": True,
                "speech": "Duruş kontrolü: Omuzlarınızı geriye alın, sırtınızı dikleştirin ve derin bir nefes alın. Omurganız size teşekkür edecek!",
                "tip": "Her 50 dakikada bir 2 dakika ayağa kalkıp esneyin.",
            }

    def find_my_phone(self) -> Dict[str, Any]:
        """
        Kullanıcının kayıp telefonunu bulması için Google / Apple Cihazımı Bul portalını açar
        veya bağlı bildirim köprüsüne zil çaldırma sinyali gönderir.
        """
        # Kullanıcının varsayılan tarayıcısında Google / iCloud Cihazımı Bul portalı
        url = "https://www.google.com/android/find"
        webbrowser.open(url)
        return {
            "ok": True,
            "speech": "Telefonunuzda yüksek sesle zil çaldırmak ve konumunu görmek için Cihazımı Bul servisini açıyorum.",
            "url": url,
        }

    def draft_quick_message_or_email(self, recipient: str, intent_description: str, tone: str = "nazik ve profesyonel") -> Dict[str, Any]:
        """
        Google Asistan tarzı: Kullanıcının söylediği amaca uygun hazır e-posta veya mesaj taslağı oluşturur.
        """
        now_date = datetime.datetime.now().strftime("%d.%m.%Y")
        subject = f"Bilgilendirme / Randevu Güncellemesi ({now_date})"
        body = (
            f"Merhaba {recipient.capitalize()},\n\n"
            f"{intent_description.strip().capitalize()}.\n\n"
            "Konuyla ilgili geri dönüşünüzü rica eder, iyi çalışmalar dilerim.\n\n"
            "Saygılarımla,"
        )

        mailto_url = f"mailto:?to={urllib.parse.quote(recipient)}&subject={urllib.parse.quote(subject)}&body={urllib.parse.quote(body)}"
        return {
            "ok": True,
            "speech": f"{recipient} için {tone} bir taslak metin hazırladım. İnceleyip gönderebilirsiniz.",
            "subject": subject,
            "body": body,
            "mailto_url": mailto_url,
        }
