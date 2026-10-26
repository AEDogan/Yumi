import re
from typing import Any, Dict, Optional
from .engine import YumiSkillEngine


class SkillDispatcher:
    """
    Kullanıcının Türkçe sesli veya yazılı komutlarını anında (sıfır gecikmeyle)
    YumiSkillEngine üzerindeki doğru beceriye yönlendiren yerel motor.
    """

    def __init__(self, engine: YumiSkillEngine):
        self.engine = engine

    @staticmethod
    def parse(text):
        class Probe:
            call=None
            def execute_skill(self,name,args=None):
                self.call=(name,args or {});return {'speech':'matched'}
        probe=Probe();SkillDispatcher(probe).dispatch(text)
        return probe.call

    @staticmethod
    def parse(text):
        class Probe:
            call=None
            def execute_skill(self,name,args=None):
                self.call=(name,args or {});return {'speech':'matched'}
        probe=Probe();SkillDispatcher(probe).dispatch(text)
        return probe.call

    def dispatch(self, text: str) -> Optional[str]:
        """
        Eğer metin doğrudan bir beceri komutu ise çalıştırır ve seslendirilecek Türkçe yanıtı döndürür.
        Eşleşmezse None döndürür (böylece Gemini AI sohbetine devredilir).
        """
        raw = text.strip()
        low = raw.lower().strip(" !?.")

        # 1. ZAMAN / SAYAÇ / ALARM / KRONOMETRE
        alarm=re.fullmatch(r"(?:saat\s*)?(\d{1,2})[:.](\d{2})(?:['’]?(?:a|e|ya|ye))?\s*(?:için\s*)?(?:bir\s*)?alarm\s*(?:kur|ayarla|başlat)",low)
        if alarm:
            return self.engine.execute_skill('set_alarm',{'alarm_time_hhmm':f'{int(alarm[1]):02d}:{alarm[2]}'}).get('speech')
        m_timer = re.search(r"(\d+)\s*(dakika|saniye|saat)(?:lik|lık|luk|lük)?\s*(?:bir\s*)?(?:sayaç|zamanlayıcı|alarm)\s*(?:başlat|kur|ayarla)", low)
        if m_timer:
            val = int(m_timer.group(1))
            unit = m_timer.group(2)
            seconds = val * 60 if unit == "dakika" else (val * 3600 if unit == "saat" else val)
            res = self.engine.execute_skill("set_timer", {"duration_seconds": seconds, "label": f"{val} {unit}"})
            return res.get("speech")

        if any(w in low for w in ["sayaçları listele", "sayaç var mı", "aktif sayaçlar", "kalan süre"]):
            res = self.engine.execute_skill("list_timers")
            return res.get("speech")

        if any(w in low for w in ["sayacı iptal et", "sayaçları iptal et", "zamanlayıcıyı durdur", "sayacı durdur"]):
            res = self.engine.execute_skill("cancel_timer")
            return res.get("speech")

        if "kronometre" in low:
            if any(w in low for w in ["başlat", "aç", "çalıştır"]):
                res = self.engine.execute_skill("stopwatch_control", {"action": "start"})
                return res.get("speech")
            if any(w in low for w in ["durdur", "bitir", "kapat"]):
                res = self.engine.execute_skill("stopwatch_control", {"action": "stop"})
                return res.get("speech")
            if any(w in low for w in ["sıfırla", "baştan"]):
                res = self.engine.execute_skill("stopwatch_control", {"action": "reset"})
                return res.get("speech")
            if any(w in low for w in ["kaç oldu", "durum", "kaç saniye", "kaç dakika"]):
                res = self.engine.execute_skill("stopwatch_control", {"action": "status"})
                return res.get("speech")

        # 2. AKILLI EV: TERMOSTAT / SICAKLIK (TEK SEFERLİK SET DEĞERİ)
        m_temp = re.search(r"(?:ev|oda|kombi|klima|termostat)\s*(?:sıcaklığını|derecesini)?\s*(\d+(?:[.,]\d+)?)\s*(?:derece(?:ye)?)?\s*(?:yap|ayarla|getir)", low)
        if m_temp:
            val_str = m_temp.group(1).replace(",", ".")
            try:
                target_temp = float(val_str)
                res = self.engine.execute_skill("control_climate_or_thermostat", {"target_temperature": target_temp})
                return res.get("speech")
            except ValueError:
                pass

        if any(w in low for w in ["ev kaç derece", "içerisi kaç derece", "oda sıcaklığı kaç", "ev sıcaklığı ne"]):
            res = self.engine.execute_skill("get_indoor_climate")
            return res.get("speech")

        # 3. AKILLI EV: IŞIK / PRİZ / LAMBA
        m_light = re.search(r"(salon|yatak odası|mutfak|çalışma odası|başucu|koridor)?\s*(?:odası\s*)?(ışığı|ışığını|ışıkları|ışıklarını|lambayı|lambasını|lambaları|prizi|prizini)\s*(aç|kapat|söndür|yak)", low)
        if m_light:
            room = m_light.group(1) or ""
            target_item = m_light.group(2)
            act_word = m_light.group(3)
            state = "off" if act_word in ["kapat", "söndür"] else "on"
            dev_name = f"{room.capitalize()} {target_item}".strip() if room else ("Başucu Lambası" if "başucu" in low else "Lamba")
            res = self.engine.execute_skill("control_light_or_plug", {"device_name": dev_name, "state": state})
            return res.get("speech")

        # 4. AKILLI EV: SÜPÜRGE
        if "süpürge" in low or "roborock" in low:
            if any(w in low for w in ["başlat", "çalıştır", "aç"]) or re.search(r"\bsüpür\b",low):
                res = self.engine.execute_skill("control_vacuum", {"action": "start"})
                return res.get("speech")
            if any(w in low for w in ["durdur", "beklet", "duraklat", "kapat"]):
                res = self.engine.execute_skill("control_vacuum", {"action": "pause"})
                return res.get("speech")
            if any(w in low for w in ["şarja", "yuvasına", "dock", "istasyona"]):
                res = self.engine.execute_skill("control_vacuum", {"action": "dock"})
                return res.get("speech")
            if any(w in low for w in ["şarjı kaç", "pil", "durum"]):
                res = self.engine.execute_skill("control_vacuum", {"action": "status"})
                return res.get("speech")

        # 5. AKILLI EV: TELEVİZYON
        if "televizyon" in low or " tv" in low or low.startswith("tv") or low in ("sesi kıs","sesi aç","sesini kıs","sesini aç"):
            tv_name = "Salon TV" if "salon" in low else ("Yatak Odası TV" if "yatak" in low else "televizyon")
            if ("ses" in low) and any(w in low for w in ("kıs","aç","sessize","sustur")):
                action="mute" if "sessize" in low or "sustur" in low else "volume_down" if "kıs" in low else "volume_up"
                return self.engine.execute_skill("control_smart_tv", {"device_name":tv_name,"action":action}).get("speech")
            if any(w in low for w in ["aç", "çalıştır"]):
                res = self.engine.execute_skill("control_smart_tv", {"device_name": tv_name, "action": "power_on"})
                return res.get("speech")
            if any(w in low for w in ["kapat", "kapa"]):
                res = self.engine.execute_skill("control_smart_tv", {"device_name": tv_name, "action": "power_off"})
                return res.get("speech")
            if "sesini aç" in low or "ses aç" in low:
                res = self.engine.execute_skill("control_smart_tv", {"device_name": tv_name, "action": "volume_up"})
                return res.get("speech")
            if "sesini kıs" in low or "ses kıs" in low:
                res = self.engine.execute_skill("control_smart_tv", {"device_name": tv_name, "action": "volume_down"})
                return res.get("speech")
            if "sessize al" in low or "sustur" in low:
                res = self.engine.execute_skill("control_smart_tv", {"device_name": tv_name, "action": "mute"})
                return res.get("speech")

        # 6. SEYAHAT, TRAFİK & KONUM (GOOGLE HARİTALAR)
        m_commute = re.search(r"(?:evden|buradan)?\s*([a-zA-ZçğıöşüÇĞİÖŞÜ\s]+?)(?:'ye|'ya|'e|'a|e|a)?\s*(?:nasıl giderim|ulaşım|yol tarifi|trafik nasıl|kaç dakika)", low)
        if m_commute:
            dest = m_commute.group(1).strip()
            if dest and dest not in ["evden", "buradan", "nereden", "ben"]:
                res = self.engine.execute_skill("get_commute_and_traffic", {"destination": dest, "origin": "ev", "open_in_browser": True})
                return res.get("speech")

        m_save_addr = re.search(r"ev\s*adresim(?:i)?\s*(.+?)\s*(?:olarak)?\s*kaydet", low)
        if m_save_addr:
            addr = m_save_addr.group(1).strip()
            res = self.engine.execute_skill("set_home_or_work_address", {"address_type": "home", "address": addr})
            return res.get("speech")

        if any(w in low for w in ["neredeyim", "şu anki konumum", "konumum ne", "hangi şehirdeyim"]):
            res = self.engine.execute_skill("get_current_location")
            return res.get("speech")

        # 7. SESLİ NOT ALMA & BELGELERİME KAYDETME
        m_note = re.search(r"(?:sesli\s*)?not\s*(?:al|kaydet|yaz)[:\s]+(.+)", low)
        if m_note:
            note_content = raw[m_note.start(1):].strip()
            res = self.engine.execute_skill("save_detailed_voice_note", {"content": note_content, "title": "Sesli Not", "category": "Genel"})
            return res.get("speech")

        if any(w in low for w in ["notlarımı oku", "aldığım notlar", "notları göster", "son notlarım"]):
            res = self.engine.execute_skill("read_voice_notes", {})
            return res.get("speech")

        # 8. LİSTE YÖNETİMİ (ALIŞVERİŞ / YAPILACAKLAR)
        m_add_list = re.search(r"(alışveriş|yapılacaklar)?\s*listem(?:e)?\s*(.+?)\s*ekle", low)
        if m_add_list:
            lst = m_add_list.group(1) or "alışveriş"
            item = m_add_list.group(2).strip()
            res = self.engine.execute_skill("add_to_list", {"list_name": lst, "item": item})
            return res.get("speech")

        if "alışveriş listem" in low or "alışveriş listemi oku" in low:
            res = self.engine.execute_skill("get_todo_list", {"list_name": "alışveriş"})
            return res.get("speech")

        if "yapılacaklar listem" in low or "yapılacakları oku" in low:
            res = self.engine.execute_skill("get_todo_list", {"list_name": "yapılacaklar"})
            return res.get("speech")

        # 9. GÜNLÜK BRİFİNG, DÖVİZ, HABERLER, TARİHTE BUGÜN
        if any(w in low for w in ["günaydın", "günlük brifing", "günün özeti"]):
            res = self.engine.execute_skill("daily_briefing", {})
            return res.get("speech")

        if "dolar" in low or "dolar kuru" in low or "dolar ne kadar" in low:
            res = self.engine.execute_skill("get_exchange_rates", {"currency": "USD"})
            return res.get("speech")

        if "euro" in low or "euro kuru" in low:
            res = self.engine.execute_skill("get_exchange_rates", {"currency": "EUR"})
            return res.get("speech")

        if "bitcoin" in low or "btc" in low:
            res = self.engine.execute_skill("get_exchange_rates", {"currency": "BTC"})
            return res.get("speech")

        if any(w in low for w in ["haberler", "günün haberleri", "son dakika"]):
            res = self.engine.execute_skill("get_news_headlines", {"limit": 3})
            return res.get("speech")

        if "tarihte bugün" in low:
            res = self.engine.execute_skill("get_today_in_history_or_fact", {})
            return res.get("speech")

        # 10. ALEXA RUTİNLERİ
        if any(w in low for w in ["evden çıkıyorum", "dışarı çıkıyorum"]):
            res = self.engine.execute_skill("leave_home_routine", {})
            return res.get("speech")

        if any(w in low for w in ["eve geldim", "geldim"]):
            res = self.engine.execute_skill("arrive_home_routine", {})
            return res.get("speech")

        if "çalışma modu" in low or "çalışma modunu aç" in low:
            res = self.engine.execute_skill("run_routine", {"routine_name": "çalışma modu"})
            return res.get("speech")

        # 11. KARAR VERİCİ
        if "yazı tura" in low or "yazı tura at" in low:
            res = self.engine.execute_skill("decision_maker", {"mode": "coin"})
            return res.get("speech")

        if "zar at" in low:
            res = self.engine.execute_skill("decision_maker", {"mode": "dice"})
            return res.get("speech")

        # 12. RADYO & MEDYA
        m_radio = re.search(r"(power fm|kral pop|süper fm|joy fm|fenomen)\s*(?:aç|çal|başlat)?", low)
        if m_radio:
            stn = m_radio.group(1)
            res = self.engine.execute_skill("play_live_radio", {"station_name": stn})
            return res.get("speech")

        # 13. SAĞLIK & ERGONOMİ
        if "su iç" in low or "su hatırlat" in low:
            res = self.engine.execute_skill("ergonomics_and_hydration", {"action": "water"})
            return res.get("speech")

        if "telefonumu bul" in low or "telefonum nerede" in low:
            res = self.engine.execute_skill("find_my_phone", {})
            return res.get("speech")

        return None
