import datetime
import json
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any, Dict

from ..storage import SkillStorage
from .calendar_skill import CalendarSkill


class BriefingSkill:
    """
    Alexa 'Flash Briefing' (Güne Başlangıç Özeti), Hava Durumu, Anlık Döviz/Kripto ve Haber Başlıkları becerisi.
    API anahtarı gerektirmeyen açık servisler (Open-Meteo, Frankfurter/Truncgil, Google News RSS) kullanır.
    """

    def __init__(self, storage: SkillStorage, calendar_skill: CalendarSkill):
        self.storage = storage
        self.calendar_skill = calendar_skill

    def get_weather(self, city: str | None = None) -> Dict[str, Any]:
        """Belirtilen şehrin anlık hava durumunu ve günlük en yüksek/düşük sıcaklığını getirir."""
        target_city = (city or self.storage.get("settings", {}).get("default_city", "Istanbul")).strip()
        try:
            geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(target_city)}&count=1&language=tr&format=json"
            with urllib.request.urlopen(geo_url, timeout=5) as resp:
                geo_data = json.loads(resp.read().decode("utf-8"))
            results = geo_data.get("results")
            if not results:
                return {"ok": False, "speech": f"{target_city} için konum bilgisi bulamadım."}

            loc = results[0]
            lat, lon = loc["latitude"], loc["longitude"]
            resolved_name = loc.get("name", target_city)

            w_url = (
                f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
                f"&current=temperature_2m,apparent_temperature,weather_code,wind_speed_10m"
                f"&daily=temperature_2m_max,temperature_2m_min&timezone=auto&forecast_days=1"
            )
            with urllib.request.urlopen(w_url, timeout=5) as resp:
                w_data = json.loads(resp.read().decode("utf-8"))

            curr = w_data.get("current", {})
            daily = w_data.get("daily", {})
            temp = round(curr['temperature_2m'])
            feels = round(curr.get("apparent_temperature", temp))
            desc = self._weather_code_tr(curr.get("weather_code", 0))
            t_max = round((daily.get("temperature_2m_max") or [temp])[0])
            t_min = round((daily.get("temperature_2m_min") or [temp])[0])

            speech = (
                f"{resolved_name} için hava şu an {desc} ve {temp} derece (hissedilen {feels} derece). "
                f"Bugün en yüksek {t_max}, en düşük {t_min} derece bekleniyor."
            )
            return {
                "ok": True,
                "speech": speech,
                "city": resolved_name,
                "temperature": temp,
                "condition": desc,
            }
        except Exception as e:
            return {"ok": False, "speech": "Hava durumu servisine şu an ulaşılamıyor.", "error": str(e)}

    def get_exchange_rates(self, currency: str = "USD") -> Dict[str, Any]:
        """Dolar (USD), Euro (EUR), Sterlin (GBP) veya Bitcoin (BTC) güncel Türk Lirası kurunu getirir."""
        code = currency.strip().upper()
        alias_map = {"DOLAR": "USD", "EURO": "EUR", "AVRO": "EUR", "STERLIN": "GBP", "BITCOIN": "BTC"}
        code = alias_map.get(code, code)

        try:
            if code == "BTC":
                url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd,try"
                with urllib.request.urlopen(url, timeout=5) as resp:
                    data = json.loads(resp.read().decode("utf-8")).get("bitcoin", {})
                usd_val = data.get("usd")
                try_val = data.get("try")
                return {
                    "ok": True,
                    "speech": f"1 Bitcoin şu anda {usd_val:,.0f} Dolar (yaklaşık {try_val:,.0f} Türk Lirası).",
                    "data": data,
                }

            url = f"https://api.frankfurter.dev/v1/latest?base={urllib.parse.quote(code)}&symbols=TRY"
            with urllib.request.urlopen(url, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            rate = data.get("rates", {}).get("TRY")
            if not rate:
                return {"ok": False, "speech": f"{code} kuru bilgisine ulaşamadım."}
            return {
                "ok": True,
                "speech": f"1 {code} şu anda {rate:.2f} Türk Lirası.",
                "rate": rate,
            }
        except Exception as e:
            return {"ok": False, "speech": "Kur bilgisi servisine şu an ulaşılamıyor.", "error": str(e)}

    def get_news_headlines(self, limit: int = 3) -> Dict[str, Any]:
        """Günün öne çıkan Türkçe haber başlıklarını getirir."""
        try:
            rss_url = "https://news.google.com/rss?hl=tr&gl=TR&ceid=TR:tr"
            req = urllib.request.Request(rss_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                xml_bytes = resp.read()
            root = ET.fromstring(xml_bytes)
            titles = []
            for item in root.findall("./channel/item")[: max(1, min(limit, 5))]:
                title_el = item.find("title")
                if title_el is not None and title_el.text:
                    clean_title = title_el.text.rsplit(" - ", 1)[0]
                    titles.append(clean_title)

            if not titles:
                return {"ok": False, "speech": "Güncel haber başlığı bulamadım."}

            speech = "Günün öne çıkan haber başlıkları: " + ". ".join(titles) + "."
            return {"ok": True, "speech": speech, "headlines": titles}
        except Exception as e:
            return {"ok": False, "speech": "Haber servisine şu an ulaşılamıyor.", "error": str(e)}

    def daily_briefing(self, city: str | None = None) -> Dict[str, Any]:
        """
        Alexa Flash Briefing: Hava durumu, bugünkü Gmail/Outlook takvim etkinlikleri, Dolar kuru ve haber özetini tek seferde sunar.
        """
        now_str = datetime.datetime.now().strftime("%d.%m.%Y, saat %H:%M")
        parts = [f"Günaydın! Bugün {now_str}."]

        weather = self.get_weather(city)
        if weather.get("ok"):
            parts.append(weather["speech"])

        cal = self.calendar_skill.list_events(days=1)
        if cal.get("ok"):
            parts.append(cal["speech"])

        fx = self.get_exchange_rates("USD")
        if fx.get("ok"):
            parts.append(fx["speech"])

        todo = self.storage.get("lists", {}).get("yapılacaklar", [])
        if todo:
            parts.append(f"Yapılacaklar listende {len(todo)} madde seni bekliyor.")
        news=self.get_news_headlines(limit=3)
        if news.get('ok'):parts.append(news['speech'])
        sections={'weather':weather,'calendar':cal,'fx':fx,'news':news}
        failures=[key for key,result in sections.items() if not result.get('ok')]
        if failures:parts.append('Bazı bölümlere şu an ulaşılamıyor: '+', '.join(failures)+'.')
        return {'ok':not failures,'speech':' '.join(parts),'sections':sections}

    def get_today_in_history_or_fact(self, mode: str = "history") -> Dict[str, Any]:
        """
        Günün Sözü, Tarihte Bugün Ne Oldu? ve İlginç Bilimsel / Kültürel Bilgiler.
        """
        import random
        now = datetime.datetime.now()

        if mode == "fact" or "bilgi" in mode.lower():
            facts = [
                "Bal arıları yüz tanıma yeteneğine sahiptir ve insan yüzlerini birbirinden ayırt edebilirler.",
                "Venüs gezegeninde bir gün, bir yıldan daha uzun sürer çünkü kendi ekseni etrafında çok yavaş döner.",
                "Ahtapotların üç kalbi ve mavi renkli kanı vardır.",
                "Satürn ve Jüpiter gezegenlerinde elmas yağmurları yağdığı tahmin edilmektedir.",
                "İnsan beyni uyanıkken yaklaşık 20 watt elektrik üretir; bu küçük bir LED ampulü yakmaya yeterlidir.",
            ]
            chosen = random.choice(facts)
            return {"ok": True, "speech": f"Günün ilginç bilgisi: {chosen}", "fact": chosen}
        else:
            month_names = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
            m_name = month_names[now.month - 1]
            day_str = f"{now.day}_{m_name}"
            # Wikipedia TR Tarihte Bugün API
            try:
                url = f"https://tr.wikipedia.org/api/rest_v1/feed/onthisday/events/{now.month}/{now.day}"
                req = urllib.request.Request(url, headers={"User-Agent": "YumiAssistant/1.0"})
                with urllib.request.urlopen(req, timeout=4) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                events = data.get("events", [])
                if events:
                    ev = events[0]
                    year = ev.get("year", "")
                    text = ev.get("text", "")
                    speech = f"Tarihte bugün ({now.day} {m_name} {year}): {text}"
                    return {"ok": True, "speech": speech, "year": year, "event": text}
            except Exception:
                pass
            return {
                "ok": False,
                "speech": f"Bugün {now.day} {m_name}. Tarihte bugün servisine şu an ulaşamıyorum.",
            }

    @staticmethod
    def _weather_code_tr(code: int) -> str:
        mapping = {
            0: "açık ve güneşli",
            1: "çoğunlukla açık",
            2: "parçalı bulutlu",
            3: "kapalı ve bulutlu",
            45: "sisli",
            48: "kırağılı sisli",
            51: "hafif çisenti yağışlı",
            53: "çisenti yağışlı",
            61: "hafif yağmurlu",
            63: "yağmurlu",
            65: "kuvvetli sağanak yağmurlu",
            71: "hafif kar yağışlı",
            73: "kar yağışlı",
            75: "yoğun kar yağışlı",
            80: "yer yer sağanak yağışlı",
            95: "gök gürültülü sağanak yağışlı",
        }
        return mapping.get(code, "parçalı bulutlu")
