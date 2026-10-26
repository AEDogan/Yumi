import datetime
from typing import Any, Callable, Dict, List

from .skills import (
    BriefingSkill,
    CalendarSkill,
    LifestyleCookingSkill,
    ListMemorySkill,
    MediaSystemSkill,
    RoutineSkill,
    SmartHomeSkill,
    TimeSkill,
    TravelCommuteSkill,
)
from .storage import SkillStorage


class YumiSkillEngine:
    """
    Yumi projesi için Amazon Alexa ve Google Asistan yetenekleri (Skills) ana motoru.
    - Gemini API Function Calling (Tools) bildirimlerini otomatik üretir.
    - Hem doğrudan Gemini `tools` listesi olarak verilebilir, hem de JSON/Dict tabanlı tool_call yanıtlarını çalıştırır.
    """

    def __init__(
        self,
        custom_storage_dir: str | None = None,
        on_alert_callback: Callable[[str, Dict[str, Any]], None] | None = None,
    ):
        self.storage = SkillStorage(custom_dir=custom_storage_dir)
        self.calendar = CalendarSkill(self.storage)
        self.time = TimeSkill(self.storage, on_alert_callback=on_alert_callback)
        self.lists = ListMemorySkill(self.storage)
        self.briefing = BriefingSkill(self.storage, self.calendar)
        self.media = MediaSystemSkill()
        self.smart_home = SmartHomeSkill(self.storage)
        self.travel = TravelCommuteSkill(self.storage)
        self.lifestyle = LifestyleCookingSkill()
        self.routines = RoutineSkill(self.storage, self.execute_skill)

        self._registry: Dict[str, Callable[..., Dict[str, Any]]] = {
            # 1. Takvim (Gmail / Google Calendar & Outlook)
            "create_calendar_event": self.calendar.create_event,
            "list_calendar_events": self.calendar.list_events,
            "set_default_calendar_provider": self.calendar.set_default_provider,
            # 2. Zaman Yönetimi (Sayaç, Alarm, Hatırlatıcı, Kronometre)
            "set_timer": self.time.set_timer,
            "list_timers": self.time.list_timers,
            "cancel_timer": self.time.cancel_timer,
            "set_alarm": self.time.set_alarm,
            "set_reminder": self.time.set_reminder,
            "stopwatch_control": self.time.stopwatch_control,
            # 3. Liste, Sesli Notlar (Dosyaya ve DB'ye), Hafıza ve Kalıcı Tercih/Kurallar
            "add_to_list": self.lists.add_to_list,
            "remove_from_list": self.lists.remove_from_list,
            "get_todo_list": self.lists.get_list,
            "save_detailed_voice_note": self.lists.save_detailed_voice_note,
            "read_voice_notes": self.lists.read_voice_notes,
            "remember_fact": self.lists.remember_fact,
            "recall_fact": self.lists.recall_fact,
            "save_quick_note": self.lists.save_quick_note,
            "save_user_preference_or_rule": self.lists.save_user_preference_or_rule,
            "remove_user_rule": self.lists.remove_user_rule,
            # 4. Günlük Brifing, Hava Durumu, Döviz, Haberler ve Tarihte Bugün/Bilgi
            "get_weather": self.briefing.get_weather,
            "get_exchange_rates": self.briefing.get_exchange_rates,
            "get_news_headlines": self.briefing.get_news_headlines,
            "get_today_in_history_or_fact": self.briefing.get_today_in_history_or_fact,
            "daily_briefing": self.briefing.daily_briefing,
            # 5. Medya (Spotify, YouTube, YouTube Music), Canlı Radyo, Ortam Sesleri, Sistem & Karar Verici
            "play_media_or_ambient": self.media.play_media_or_ambient,
            "play_live_radio": self.media.play_live_radio,
            "media_transport_control": self.media.media_transport_control,
            "launch_application": self.media.launch_application,
            "system_status": self.media.system_status,
            "decision_maker": self.media.decision_maker,
            # 6. Akıllı Ev (Wi-Fi Keşif, Tuya/Xiaomi/Hue/IKEA, Robot Süpürge, Işıklar, Prizler, Akıllı TV, Tek Seferlik Termostat Set Değeri & Çıkış/Giriş Modu)
            "discover_wifi_devices": self.smart_home.discover_wifi_devices,
            "register_smart_device": self.smart_home.register_smart_device,
            "rename_or_alias_device": self.smart_home.rename_or_alias_device,
            "sync_cloud_bridge_devices": self.smart_home.sync_cloud_bridge_devices,
            "list_smart_devices": self.smart_home.list_smart_devices,
            "control_vacuum": self.smart_home.control_vacuum,
            "control_light_or_plug": self.smart_home.control_light_or_plug,
            "control_smart_tv": self.smart_home.control_smart_tv,
            "cast_youtube_to_tv": self.smart_home.cast_youtube_to_tv,
            "control_climate_or_thermostat": self.smart_home.control_climate_or_thermostat,
            "get_indoor_climate": self.smart_home.get_indoor_climate,
            "leave_home_routine": self.smart_home.leave_home_routine,
            "arrive_home_routine": self.smart_home.arrive_home_routine,
            # 7. Seyahat, Konum, Canlı Trafik, Google Haritalar & Kargo/Uçuş Takibi (Google Asistan)
            "get_commute_and_traffic": self.travel.get_commute_and_traffic,
            "set_home_or_work_address": self.travel.set_home_or_work_address,
            "get_current_location": self.travel.get_current_location,
            "track_shipment_or_flight": self.travel.track_shipment_or_flight,
            # 8. Yaşam, Adım Adım Yemek Tarifi, Ergonomi & Mesaj Taslağı
            "recipe_assistant": self.lifestyle.recipe_assistant,
            "ergonomics_and_hydration": self.lifestyle.ergonomics_and_hydration,
            "find_my_phone": self.lifestyle.find_my_phone,
            "draft_quick_message_or_email": self.lifestyle.draft_quick_message_or_email,
            # 9. Alexa Rutinleri (Kayıt + Çalıştırma)
            "run_routine": self.routines.run_routine,
            "save_routine": self.routines.save_routine,
        }

    def execute_skill(self, skill_name: str, args: Dict[str, Any] | None = None) -> Dict[str, Any]:
        """İsmi ve argümanları verilen beceriyi çalıştırır ve Yumi'nin seslendireceği sonucu döndürür."""
        fn = self._registry.get(skill_name)
        if not fn:
            return {"ok": False, "speech": f"'{skill_name}' adında bir beceri tanımlı değil."}
        try:
            result=fn(**(args or {}))
        except Exception as e:
            result={"ok": False, "speech": f"Beceri çalıştırılırken bir sorun oluştu: {e}", "error": str(e)}
        callback=getattr(self,'on_result',None)
        if callback:
            try:callback(skill_name,result)
            except Exception:pass
        return result

    def get_system_instruction_addon(self) -> str:
        """
        Gemini sistem promptuna eklenecek güncel tarih/saat, bağlı takvim durumu ve kullanıcının kalıcı kuralları.
        """
        now_iso = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        settings = self.storage.get("settings", {})
        cal_pref = settings.get("calendar_provider", "ask")
        connected = self.calendar.get_connected_providers()
        user_rules = self.storage.get("user_rules", [])

        rules_block = ""
        if user_rules:
            rules_block = " Kullanıcının kaydettiği kalıcı kurallar/tercihler: [" + " | ".join(user_rules) + "]."

        return (
            f"Şu anki yerel tarih ve saat: {now_iso}. "
            f"Bağlı takvim hesapları: {connected or ['yerel']}. Kayıtlı varsayılan takvim tercihi: '{cal_pref}'. "
            "Eğer hem 'google' hem 'outlook' bağlıysa ve varsayılan tercih 'ask' ise, kullanıcı hangi takvimi istediğini "
            "belirtmediğinde `create_calendar_event` aracı `needs_clarification=True` döndürür; bu durumda kullanıcıya "
            "Google Takvim mi yoksa Outlook mu istediğini sor. "
            "Kullanıcı 'her zaman Outlook takvimi kullan' veya benzeri kalıcı bir alışkanlık/kural söylediğinde "
            "`set_default_calendar_provider` veya `save_user_preference_or_rule` aracını çağırarak bunu kalıcı kaydet."
            f"{rules_block}"
        )

    def get_gemini_callable_tools(self) -> List[Callable[..., Dict[str, Any]]]:
        """
        `google-genai` SDK'sında `config=types.GenerateContentConfig(tools=engine.get_gemini_callable_tools())`
        olarak doğrudan verilebilecek Python fonksiyon listesi.
        """
        return list(self._registry.values())

    def get_gemini_function_declarations(self) -> List[Dict[str, Any]]:
        """
        REST API veya düşük seviye Gemini `function_declarations` JSON şeması gerektiğinde kullanılır.
        """
        return [
            {
                "name": "create_calendar_event",
                "description": "Gmail (Google Calendar) veya Microsoft Outlook takvimine yeni bir randevu, toplantı veya etkinlik ekler.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "title": {"type": "STRING", "description": "Randevu veya etkinliğin başlığı"},
                        "start_time_iso": {
                            "type": "STRING",
                            "description": "Başlangıç tarihi ve saati ISO 8601 formatında (Örn: 2026-10-17T14:30:00)",
                        },
                        "end_time_iso": {
                            "type": "STRING",
                            "description": "Bitiş tarihi ve saati ISO 8601 formatında (Opsiyonel, verilmezse +1 saat)",
                        },
                        "description": {"type": "STRING", "description": "Etkinlik açıklaması veya notu"},
                        "location": {"type": "STRING", "description": "Toplantı yeri veya adresi"},
                        "provider": {
                            "type": "STRING",
                            "description": "Hedef takvim: 'auto', 'google' (Gmail için), 'outlook' (Outlook için)",
                        },
                        "open_web_confirm": {
                            "type": "BOOLEAN",
                            "description": "API bağlı değilse tarayıcıda hazır takvim ekleme penceresini açar",
                        },
                    },
                    "required": ["title", "start_time_iso"],
                },
            },
            {
                "name": "list_calendar_events",
                "description": "Gmail (Google Calendar), Outlook ve yerel takvimdeki randevuları/etkinlikleri listeler.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "date_iso": {
                            "type": "STRING",
                            "description": "Sorgulanacak gün ISO formatında (Örn: 2026-10-16T00:00:00). Boşsa bugün.",
                        },
                        "days": {"type": "INTEGER", "description": "Kaç günlük etkinlik listeleneceği (Varsayılan: 1)"},
                        "provider": {"type": "STRING", "description": "'auto', 'google' veya 'outlook'"},
                    },
                },
            },
            {
                "name": "set_timer",
                "description": "Belirtilen süre (saniye) için geri sayım sayacı (timer) başlatır.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "duration_seconds": {"type": "INTEGER", "description": "Saniye cinsinden süre (Örn: 5 dk = 300)"},
                        "label": {"type": "STRING", "description": "Sayacın adı (Örn: Makarna, Çay, Pomodoro)"},
                    },
                    "required": ["duration_seconds"],
                },
            },
            {
                "name": "list_timers",
                "description": "Çalışmakta olan aktif zamanlayıcıları ve kalan sürelerini söyler.",
                "parameters": {"type": "OBJECT", "properties": {}},
            },
            {
                "name": "cancel_timer",
                "description": "Aktif bir zamanlayıcıyı veya tüm zamanlayıcıları iptal eder.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "label": {"type": "STRING", "description": "İptal edilecek sayacın adı (Boşsa tümünü iptal eder)"}
                    },
                },
            },
            {
                "name": "set_alarm",
                "description": "Belirli bir saate (SS:DD) alarm kurar.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "alarm_time_hhmm": {"type": "STRING", "description": "Alarm saati, örn: '07:30' veya '19:00'"},
                        "label": {"type": "STRING", "description": "Alarm başlığı"},
                    },
                    "required": ["alarm_time_hhmm"],
                },
            },
            {
                "name": "set_reminder",
                "description": "Belirli bir tarih ve saatte kullanıcıya bir konuyu hatırlatmak için hatırlatıcı kurar.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "text": {"type": "STRING", "description": "Hatırlatılacak konu"},
                        "remind_at_iso": {"type": "STRING", "description": "Hatırlatma zamanı ISO formatında"},
                    },
                    "required": ["text", "remind_at_iso"],
                },
            },
            {
                "name": "add_to_list",
                "description": "Alışveriş listesine veya yapılacaklar (to-do) listesine yeni bir madde ekler.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "item": {"type": "STRING", "description": "Eklenecek ürün veya görev"},
                        "list_name": {"type": "STRING", "description": "'alışveriş' veya 'yapılacaklar'"},
                    },
                    "required": ["item"],
                },
            },
            {
                "name": "remove_from_list",
                "description": "Alışveriş veya yapılacaklar listesinden bir öğeyi siler.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "item": {"type": "STRING", "description": "Silinecek öğe (Tümünü silmek için 'hepsi')"},
                        "list_name": {"type": "STRING", "description": "'alışveriş' veya 'yapılacaklar'"},
                    },
                    "required": ["item"],
                },
            },
            {
                "name": "get_todo_list",
                "description": "Alışveriş veya yapılacaklar listesindeki maddeleri okur.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "list_name": {"type": "STRING", "description": "'alışveriş' veya 'yapılacaklar'"}
                    },
                },
            },
            {
                "name": "remember_fact",
                "description": "Kullanıcının 'bunu unutma' dediği kişisel bir bilgiyi hafızaya kaydeder.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "subject": {"type": "STRING", "description": "Bilginin konusu (Örn: yedek anahtar, wifi şifresi)"},
                        "value": {"type": "STRING", "description": "Hatırlanacak detay (Örn: mavi çekmecede)"},
                    },
                    "required": ["subject", "value"],
                },
            },
            {
                "name": "recall_fact",
                "description": "Hafızaya kaydedilmiş kişisel bir bilgiyi sorgular.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {"query": {"type": "STRING", "description": "Aranan konu veya anahtar kelime"}},
                    "required": ["query"],
                },
            },
            {
                "name": "get_weather",
                "description": "Belirtilen şehrin anlık hava durumunu ve sıcaklık tahminini getirir.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {"city": {"type": "STRING", "description": "Şehir adı (Örn: Istanbul, Ankara)"}},
                },
            },
            {
                "name": "get_exchange_rates",
                "description": "Dolar (USD), Euro (EUR), Sterlin (GBP) veya Bitcoin (BTC) güncel kurunu getirir.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {"currency": {"type": "STRING", "description": "Para birimi: USD, EUR, GBP, BTC"}},
                },
            },
            {
                "name": "get_news_headlines",
                "description": "Günün öne çıkan güncel haber başlıklarını getirir.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {"limit": {"type": "INTEGER", "description": "Haber sayısı (Varsayılan: 3)"}},
                },
            },
            {
                "name": "daily_briefing",
                "description": "Alexa Flash Briefing: Hava durumu, bugünkü takvim randevuları, döviz kuru ve yapılacakları özetler.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {"city": {"type": "STRING", "description": "Hava durumu için şehir adı"}},
                },
            },
            {
                "name": "play_media_or_ambient",
                "description": "Spotify, YouTube veya YouTube Music üzerinde şarkı/müzik ya da odaklanma/ortam sesi (yağmur, şömine, beyaz gürültü, lofi) açar.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "query": {"type": "STRING", "description": "Çalınacak ortam sesi, şarkı veya sanatçı adı"},
                        "platform_target": {
                            "type": "STRING",
                            "description": "'spotify', 'youtube' veya 'youtube_music'",
                        },
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "media_transport_control",
                "description": "Çalan müziği/videoyu (Spotify, YouTube, YouTube Music) durdurur, devam ettirir, sonraki/önceki şarkıya geçer veya sistem sesini açıp kısar.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "action": {
                            "type": "STRING",
                            "description": "'play_pause', 'pause', 'resume', 'next', 'previous', 'stop', 'mute', 'volume_up', 'volume_down'",
                        },
                        "steps": {"type": "INTEGER", "description": "Ses açma/kısma adım sayısı (Varsayılan: 5)"},
                    },
                    "required": ["action"],
                },
            },
            {
                "name": "launch_application",
                "description": "Bilgisayardaki temel uygulamaları (hesap makinesi, not defteri, spotify, ayarlar vb.) açar.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {"app_name": {"type": "STRING", "description": "Açılacak uygulamanın adı"}},
                    "required": ["app_name"],
                },
            },
            {
                "name": "discover_wifi_devices",
                "description": "Evdeki yerel Wi-Fi ağını tarayarak akıllı ışıkları, TV'leri ve IoT cihazlarını otomatik bulur.",
                "parameters": {"type": "OBJECT", "properties": {}},
            },
            {
                "name": "register_smart_device",
                "description": "Evdeki bir Wi-Fi akıllı cihazı (Robot süpürge, akıllı ampul, Tuya priz, Akıllı TV) Yumi'deki özel adıyla ('Başucu Lambası', 'Salon TV') kaydeder.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "name": {"type": "STRING", "description": "Cihaza verilecek sesli komut adı (Örn: 'Başucu Lambası', 'Salon TV', 'Yatak Odası TV')"},
                        "device_type": {"type": "STRING", "description": "'vacuum' (süpürge), 'light' (ışık/lamba), 'plug' (priz), 'tv' (televizyon)"},
                        "brand_or_protocol": {
                            "type": "STRING",
                            "description": "'tuya', 'xiaomi', 'roborock', 'yeelight', 'hue', 'tapo', 'dlna_tv', 'home_assistant'",
                        },
                        "ip_address": {"type": "STRING", "description": "Cihazın yerel Wi-Fi IP adresi (Örn: 192.168.1.45)"},
                        "token_or_key": {"type": "STRING", "description": "Varsa Tuya local_key, Xiaomi token, TV MAC adresi veya API anahtarı"},
                        "entity_id": {"type": "STRING", "description": "Tuya device_id veya Home Assistant entity_id"},
                        "room": {"type": "STRING", "description": "Bulunduğu oda (Örn: 'Salon', 'Yatak Odası')"},
                        "aliases_csv": {"type": "STRING", "description": "Virgülle ayrılmış alternatif takma adlar"},
                    },
                    "required": ["name", "device_type", "brand_or_protocol"],
                },
            },
            {
                "name": "rename_or_alias_device",
                "description": "Wi-Fi'da fabrika adıyla ('Tuya Plug' vb.) görünen bir cihaza Alexa'daki gibi özel bir isim ('Başucu Lambası', 'Salon TV') verir.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "current_name_or_ip": {"type": "STRING", "description": "Cihazın mevcut adı veya IP adresi"},
                        "new_custom_name": {"type": "STRING", "description": "Yeni özel adı (Örn: 'Başucu Lambası')"},
                        "treat_as_type": {"type": "STRING", "description": "Priz bir lambaya bağlıysa 'light' olarak işaretlemek için"},
                    },
                    "required": ["current_name_or_ip", "new_custom_name"],
                },
            },
            {
                "name": "sync_cloud_bridge_devices",
                "description": "Telefondaki Xiaomi (Mi Home) veya Tuya (Smart Life) uygulama köprüsüne bağlanarak tüm cihazları telefonda verilen özel isimleriyle ('Başucu Lambası' vb.) Yumi'ye aktarır.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "platform_name": {"type": "STRING", "description": "'xiaomi' veya 'tuya'"},
                        "username_or_api_key": {"type": "STRING", "description": "Xiaomi e-postası veya Tuya API Key"},
                        "password_or_secret": {"type": "STRING", "description": "Xiaomi şifresi veya Tuya API Secret"},
                        "region": {"type": "STRING", "description": "Bölge kodu (Varsayılan: 'eu')"},
                    },
                    "required": ["platform_name"],
                },
            },
            {
                "name": "control_vacuum",
                "description": "Evdeki akıllı robot süpürgeyi başlatır ('start'), durdurur ('pause'), şarj istasyonuna gönderir ('dock') veya pil/durum bilgisini okur ('status').",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "action": {"type": "STRING", "description": "'start', 'pause', 'dock' veya 'status'"},
                        "device_name": {"type": "STRING", "description": "Süpürgenin kayıtlı adı (Varsayılan: 'süpürge')"},
                    },
                    "required": ["action"],
                },
            },
            {
                "name": "control_light_or_plug",
                "description": "Evdeki Wi-Fi akıllı ışıkları veya prizleri açar ('on'), kapatır ('off') veya parlaklığını (%1-%100) ayarlar.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "device_name": {"type": "STRING", "description": "Işığın veya prizin adı (Örn: 'Salon Işığı', 'Gece Lambası')"},
                        "state": {"type": "STRING", "description": "'on' (aç) veya 'off' (kapat)"},
                        "brightness": {"type": "INTEGER", "description": "1-100 arası parlaklık yüzdesi (opsiyonel)"},
                    },
                    "required": ["device_name", "state"],
                },
            },
            {
                "name": "control_smart_tv",
                "description": "Evdeki Akıllı TV'yi (LG, Samsung, Android TV vb.) açar ('power_on'), kapatır ('power_off'), sesini ayarlar ('mute', 'volume_up', 'volume_down') veya TV'de uygulama açar ('launch_app').",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "action": {
                            "type": "STRING",
                            "description": "'power_on', 'power_off', 'mute', 'volume_up', 'volume_down', 'launch_app'",
                        },
                        "device_name": {"type": "STRING", "description": "TV'nin kayıtlı adı (Varsayılan: 'televizyon')"},
                        "app_or_channel": {"type": "STRING", "description": "Açılacak uygulama ('youtube', 'netflix' vb.)"},
                    },
                    "required": ["action"],
                },
            },
            {
                "name": "cast_youtube_to_tv",
                "description": "Bilgisayarda izlenen bir YouTube videosunu (link veya video adı/konusu) televizyonu açıp doğrudan Akıllı TV ekranındaki YouTube uygulamasına aktarır ve oynatır.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "video_url_or_query": {
                            "type": "STRING",
                            "description": "YouTube video URL'si, video ID'si veya aranacak video başlığı",
                        },
                        "device_name": {"type": "STRING", "description": "Hedef TV adı (Varsayılan: 'televizyon')"},
                        "wake_tv_first": {
                            "type": "BOOLEAN",
                            "description": "TV kapalıysa önce Wake-on-LAN ile uyandırır (Varsayılan: True)",
                        },
                    },
                    "required": ["video_url_or_query"],
                },
            },
            {
                "name": "decision_maker",
                "description": "Yazı-tura atar ('coin'), zar atar ('dice'), rastgele sayı tutar ('number') veya seçenekler arasından seçim yapar ('pick').",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "mode": {"type": "STRING", "description": "'coin', 'dice', 'number' veya 'pick'"},
                        "options_csv": {"type": "STRING", "description": "Virgülle ayrılmış seçenekler (mode='pick' ise)"},
                        "max_number": {"type": "INTEGER", "description": "Üst sınır (mode='number' ise, varsayılan 100)"},
                    },
                },
            },
            {
                "name": "run_routine",
                "description": "Birden fazla eylemi tek komutla çalıştıran Alexa rutinini ('çalışma modu', 'günaydın' vb.) başlatır.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {"routine_name": {"type": "STRING", "description": "Çalıştırılacak rutinin adı"}},
                    "required": ["routine_name"],
                },
            },
            {
                "name": "set_default_calendar_provider",
                "description": "Kullanıcının varsayılan takvim tercihini ('google', 'outlook', 'both' veya 'ask') kalıcı olarak kaydeder. 'Her zaman Outlook takvimimi kullan' dendiğinde çağrılır.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "provider": {
                            "type": "STRING",
                            "description": "'google' (Gmail takvimi), 'outlook' (Outlook takvimi), 'both' (ikisi birden) veya 'ask' (her seferinde sor)",
                        }
                    },
                    "required": ["provider"],
                },
            },
            {
                "name": "save_user_preference_or_rule",
                "description": "Kullanıcının Yumi'ye öğrettiği kalıcı alışkanlıkları, tercihleri veya özel beceri kurallarını kaydeder ('her zaman X yap', 'varsayılan şehrimi Ankara yap' vb.).",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "rule_text": {"type": "STRING", "description": "Kalıcı kuralın veya tercihin açıklaması"},
                        "setting_key": {
                            "type": "STRING",
                            "description": "Opsiyonel sistem ayarı anahtarı: 'calendar_provider', 'default_city', 'music_platform'",
                        },
                        "setting_value": {"type": "STRING", "description": "Opsiyonel sistem ayarı değeri"},
                    },
                    "required": ["rule_text"],
                },
            },
            {
                "name": "save_detailed_voice_note",
                "description": "Sesli notu kullanıcının bilgisayarındaki 'Belgelerim\\Yumi_Notlari\\' klasörüne tarihli .txt ve .md dosyası olarak kaydeder ve hafızaya alır.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "content": {"type": "STRING", "description": "Notun içeriği"},
                        "title": {"type": "STRING", "description": "Not başlığı"},
                        "category": {"type": "STRING", "description": "Kategori (İş, Fikir, Günlük, Alışveriş)"},
                    },
                    "required": ["content"],
                },
            },
            {
                "name": "read_voice_notes",
                "description": "Bilgisayara kaydedilmiş sesli notları listeler ve okur.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {"query": {"type": "STRING", "description": "Aranacak kelime veya tarih (boşsa son notlar)"}},
                },
            },
            {
                "name": "control_climate_or_thermostat",
                "description": "Evdeki akıllı termostat, kombi veya klimanın hedef sıcaklığını TEK SEFERLİK ayarlar. Asla arka planda sıcaklığı geri zorlamaz.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "target_temperature": {"type": "NUMBER", "description": "Hedef sıcaklık santigrat derece cinsinden (Örn: 21.0 veya 22.5)"},
                        "device_name": {"type": "STRING", "description": "Termostat veya klima adı (Varsayılan: 'termostat')"},
                    },
                    "required": ["target_temperature"],
                },
            },
            {
                "name": "get_indoor_climate",
                "description": "'Ev kaç derece?' sorusu için evdeki termostat veya sıcaklık/nem sensöründen anlık iç ortam sıcaklığını okur.",
                "parameters": {"type": "OBJECT", "properties": {}},
            },
            {
                "name": "leave_home_routine",
                "description": "'Evden çıkıyorum' / 'Dışarı çıkıyorum' dendiğinde tüm ışıkları/TV'leri kapatır, süpürgeyi çalıştırır ve bilgisayarı kilitler.",
                "parameters": {"type": "OBJECT", "properties": {}},
            },
            {
                "name": "arrive_home_routine",
                "description": "'Eve geldim' dendiğinde giriş/salon ışıklarını açar, süpürgeyi şarja gönderir ve günün özetini sunar.",
                "parameters": {"type": "OBJECT", "properties": {}},
            },
            {
                "name": "get_commute_and_traffic",
                "description": "'Evden şuraya nasıl giderim?', 'Trafiğe göre Maslak'a ne zaman varırım?' soruları için canlı sürüş/toplu taşıma süresi ve resmi Google Haritalar yol tarifi bağlantısı üretir.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "destination": {"type": "STRING", "description": "Gidilecek varış noktası (Örn: 'Maslak', 'İş', 'Kadıköy')"},
                        "origin": {"type": "STRING", "description": "Başlangıç noktası (Varsayılan: 'ev'. Kayıtlı ev adresini veya mevcut IP konumunu otomatik kullanır)"},
                        "travel_mode": {"type": "STRING", "description": "'driving' (araba/varsayılan), 'transit' (toplu taşıma/otobüs/metro), 'walking' (yürüyüş), 'bicycling' (bisiklet)"},
                        "open_in_browser": {"type": "BOOLEAN", "description": "Rotayı doğrudan kullanıcının web tarayıcısında Google Haritalar sekmesi olarak açmak için True (Varsayılan: False)"},
                    },
                    "required": ["destination"],
                },
            },
            {
                "name": "set_home_or_work_address",
                "description": "Kullanıcının 'Ev' veya 'İş' adresini ('Kadıköy Moda', 'Levent Plaza No:5' vb.) kalıcı olarak kaydeder. 'Ev adresimi ... olarak kaydet' dendiğinde çağrılır.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "address_type": {"type": "STRING", "description": "'home' (ev) veya 'work' (iş)"},
                        "address": {"type": "STRING", "description": "Açık adres veya semt/ilçe/şehir bilgisi"},
                    },
                    "required": ["address_type", "address"],
                },
            },
            {
                "name": "get_current_location",
                "description": "Kullanıcının şu anki konum bilgisini (kayıtlı ev adresi veya ağ tabanlı şehir/ilçe tespiti) sorgular.",
                "parameters": {"type": "OBJECT", "properties": {}},
            },
            {
                "name": "track_shipment_or_flight",
                "description": "Kargo takip numarasını veya uçuş kodunu (TK1923 vb.) sorgular.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "query_code": {"type": "STRING", "description": "Kargo takip numarası veya Uçuş Kodu"},
                        "tracking_type": {"type": "STRING", "description": "'cargo', 'flight' veya 'auto'"},
                    },
                    "required": ["query_code"],
                },
            },
            {
                "name": "play_live_radio",
                "description": "Canlı radyo istasyonu (Power FM, Kral Pop, Süper FM, Joy FM, Fenomen) açar.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {"station_name": {"type": "STRING", "description": "Radyo istasyonu adı"}},
                    "required": ["station_name"],
                },
            },
            {
                "name": "recipe_assistant",
                "description": "Yemek tarifi adımlarını sesli anlatır ve pişirme sürelerine göre sayaç önerir.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "dish_name": {"type": "STRING", "description": "Yemek adı (Menemen, Makarna, Mercimek Çorbası)"},
                        "step_number": {"type": "INTEGER", "description": "Kaçıncı adım (Varsayılan: 1)"},
                    },
                    "required": ["dish_name"],
                },
            },
            {
                "name": "ergonomics_and_hydration",
                "description": "Masa başında çalışan kullanıcı için su içme, 20-20-20 kuralı göz dinlendirme veya dik duruş hatırlatması yapar.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {"action": {"type": "STRING", "description": "'water' (su), 'eyes' (göz), 'posture' (duruş)"}},
                },
            },
            {
                "name": "find_my_phone",
                "description": "Kullanıcının kayıp telefonunu bulması için 'Cihazımı Bul' servisini açar.",
                "parameters": {"type": "OBJECT", "properties": {}},
            },
            {
                "name": "draft_quick_message_or_email",
                "description": "Google Asistan tarzı: Hızlı ve nazik e-posta veya mesaj taslağı hazırlar.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "recipient": {"type": "STRING", "description": "Alıcı adı veya e-postası"},
                        "intent_description": {"type": "STRING", "description": "Mesajın amacı/konusu"},
                    },
                    "required": ["recipient", "intent_description"],
                },
            },
        ]
