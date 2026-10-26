import json
import urllib.parse
import urllib.request
import webbrowser
from typing import Any, Dict


class TravelCommuteSkill:
    """
    Google Asistan tarzı Seyahat, İşe Gidiş / Trafik Yoğunluğu, Varış Süresi ve Kargo / Uçuş Takip Becerisi.
    - Ev/İş adresi kaydı ve önceliği
    - IP tabanlı sıfır konfigürasyon konum tespiti (Zero-Config Geolocation)
    - Google Haritalar (Google Maps) resmi yönlendirme URL'si oluşturma ve tarayıcıda açma
    - Açık kaynaklı OSRM motoru ile canlı mesafe ve trafikli sürüş süresi tahmini
    """

    # Popüler şehir merkezleri varsayılan koordinatları
    LANDMARKS = {
        "kadıköy": (40.9927, 29.0277),
        "kadikoy": (40.9927, 29.0277),
        "maslak": (41.1105, 29.0210),
        "beşiktaş": (41.0422, 29.0067),
        "besiktas": (41.0422, 29.0067),
        "şişli": (41.0602, 28.9877),
        "sisli": (41.0602, 28.9877),
        "taksim": (41.0370, 28.9850),
        "üsküdar": (41.0267, 29.0153),
        "uskudar": (41.0267, 29.0153),
        "levent": (41.0782, 29.0117),
        "kızılay": (39.9208, 32.8541),
        "ankara": (39.9334, 32.8597),
        "alsancak": (38.4382, 27.1434),
        "izmir": (38.4237, 27.1428),
    }

    def __init__(self, storage=None):
        self.storage = storage
        self._cached_ip_location: Dict[str, Any] | None = None

    def get_current_location(self) -> Dict[str, Any]:
        """
        Kullanıcının kayıtlı ev adresini veya Wi-Fi / IP tabanlı anlık coğrafi konumunu döndürür.
        """
        saved_home = ""
        if self.storage:
            settings = self.storage.get("settings", {})
            saved_home = settings.get("home_address", "")

        ip_loc = self._get_ip_location()

        if saved_home:
            speech = f"Kayıtlı ev adresiniz: {saved_home}."
            if ip_loc.get("city"):
                speech += f" (Wi-Fi/IP ağınız ise {ip_loc.get('city')}, {ip_loc.get('country')} bölgesinde görünüyor.)"
            return {
                "ok": True,
                "speech": speech,
                "home_address": saved_home,
                "network_location": ip_loc,
                "source": "saved_profile",
            }

        city = ip_loc.get("city")
        if not city:return {'ok':False,'speech':'Ağ konumunu belirleyemedim. Başlangıç adresini belirtmen gerekiyor.'}
        region = ip_loc.get("regionName", "")
        speech = f"Şu anki konumunuz ağ bağlantınız üzerinden {city} ({region}) olarak algılandı. Dilerseniz 'Ev adresimi ... olarak kaydet' diyerek tam evinizi tanımlayabilirsiniz."
        return {
            "ok": True,
            "speech": speech,
            "home_address": None,
            "network_location": ip_loc,
            "source": "ip_geolocation",
        }

    def set_home_or_work_address(self, address_type: str, address: str) -> Dict[str, Any]:
        """
        Kullanıcının 'Ev' veya 'İş' adresini kalıcı olarak hafızaya kaydeder.
        Örn: 'Ev adresimi Kadıköy Moda olarak kaydet'
        """
        addr_clean = address.strip()
        type_key = "home_address" if "ev" in address_type.lower() or "home" in address_type.lower() else "work_address"
        label = "Ev" if type_key == "home_address" else "İş"

        if self.storage:
            def _update(settings):
                s = settings or {}
                s[type_key] = addr_clean
                return s

            self.storage.update_section("settings", _update)

        speech = (
            f"{label} adresiniz başarıyla '{addr_clean}' olarak kaydedildi. "
            f"Artık '{label.lower()}den şuraya nasıl giderim' veya 'trafiği kontrol et' dediğinizde bu adresi başlangıç noktası alacağım."
        )
        return {
            "ok": True,
            "speech": speech,
            "address_type": type_key,
            "address": addr_clean,
        }

    def get_commute_and_traffic(
        self,
        destination: str,
        origin: str = "ev",
        travel_mode: str = "driving",
        open_in_browser: bool = False,
    ) -> Dict[str, Any]:
        """
        'Evden Kadıköy'e nasıl giderim?' veya 'Buradan Maslak'a trafik nasıl?' gibi sorular için:
        - Başlangıç noktasını (kayıtlı ev adresi veya IP konumu) çözer.
        - Google Haritalar resmi yol tarifi bağlantısını oluşturur.
        - Sürüş mesafesini ve trafiğe bağlı tahmini varış süresini hesaplar.
        """
        dest_clean = destination.strip()
        orig_clean = origin.strip() if origin else "ev"
        orig_label = orig_clean

        # Başlangıç noktası "ev", "burası", "mevcut konum" ise kullanıcının adresini al
        orig_lower = orig_clean.lower()
        if orig_lower in ["ev", "home", "evim", "burası", "burasi", "mevcut konum", "su anki konum", "şu anki konum", ""]:
            saved_home = ""
            if self.storage:
                saved_home = self.storage.get("settings", {}).get("home_address", "")
            if saved_home:
                orig_clean = saved_home
                orig_label = f"Kayıtlı ev adresiniz ({saved_home})"
            else:
                ip_loc = self._get_ip_location()
                city = ip_loc.get("city")
                if not city:return {'ok':False,'speech':'Başlangıç konumunu belirleyemedim. Ev adresini kaydetmen gerekiyor.'}
                orig_clean = city
                orig_label = f"Mevcut konumunuz ({city})"

        # Varış noktası "iş" ise kayıtlı iş adresine bak
        dest_lower = dest_clean.lower()
        if dest_lower in ["iş", "is", "isyeri", "işyeri", "work"]:
            if self.storage:
                saved_work = self.storage.get("settings", {}).get("work_address", "")
                if saved_work:
                    dest_clean = saved_work

        # Google Haritalar Travel Mode eşlemesi: driving, transit, walking, bicycling
        mode_param = "driving"
        mode_lower = travel_mode.lower()
        mode_turkish = "sürüş"
        if "toplu" in mode_lower or "transit" in mode_lower or "otobüs" in mode_lower or "metro" in mode_lower:
            mode_param = "transit"
            mode_turkish = "toplu taşıma"
        elif "yürü" in mode_lower or "walk" in mode_lower:
            mode_param = "walking"
            mode_turkish = "yürüyüş"
        elif "bisiklet" in mode_lower or "bike" in mode_lower:
            mode_param = "bicycling"
            mode_turkish = "bisiklet"

        # Resmi Google Maps Universal Directions URL
        google_maps_url = (
            f"https://www.google.com/maps/dir/?api=1"
            f"&origin={urllib.parse.quote(orig_clean)}"
            f"&destination={urllib.parse.quote(dest_clean)}"
            f"&travelmode={mode_param}"
        )

        # Koordinatları çöz ve OSRM ile mesafe/süre tahmini yap
        orig_coords = self._resolve_location(orig_clean)
        dest_coords = self._resolve_location(dest_clean)

        if not orig_coords or not dest_coords or mode_param!='driving':
            speech = (
                f"{orig_label} ile {dest_clean} arasındaki {mode_turkish} rotasını ve canlı trafik durumunu "
                f"Google Haritalar üzerinden açıyorum."
            )
            if open_in_browser:
                try:
                    webbrowser.open(google_maps_url)
                except Exception:
                    pass
            return {
                "ok": True,
                "speech": speech,
                "google_maps_url": google_maps_url,
                "origin": orig_clean,
                "destination": dest_clean,
                "travel_mode": mode_param,
            }

        try:
            lat1, lon1 = orig_coords
            lat2, lon2 = dest_coords
            url = f"https://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false"
            req = urllib.request.Request(url, headers={"User-Agent": "YumiAssistant/1.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            routes = data.get("routes", [])
            if not routes:
                raise ValueError("Rota bulunamadı")

            route = routes[0]
            distance_km = round(route["distance"] / 1000.0, 1)
            duration_mins = round(route["duration"] / 60.0)

            # Şehir içi trafik gecikme çarpanı
            traffic_mins = duration_mins
            speech = (
                f"{orig_label} noktasından {dest_clean} istikametine mesafe yaklaşık {distance_km} kilometre. "
                f"Trafik hesaba katılmadan sürüş süresi yaklaşık {traffic_mins} dakika. "
                f"Canlı trafik için Google Haritalar bağlantısını hazırladım."
            )

            if open_in_browser:
                try:
                    webbrowser.open(google_maps_url)
                except Exception:
                    pass

            return {
                "ok": True,
                "speech": speech,
                "distance_km": distance_km,
                "estimated_minutes": traffic_mins,
                "live_traffic": False,
                "google_maps_url": google_maps_url,
                "origin": orig_clean,
                "destination": dest_clean,
                "travel_mode": mode_param,
            }
        except Exception:
            speech = f"{orig_label} noktasından {dest_clean} konumuna Google Haritalar canlı rotasını açıyorum."
            if open_in_browser:
                try:
                    webbrowser.open(google_maps_url)
                except Exception:
                    pass
            return {
                "ok": True,
                "speech": speech,
                "google_maps_url": google_maps_url,
                "origin": orig_clean,
                "destination": dest_clean,
                "travel_mode": mode_param,
            }

    def track_shipment_or_flight(self, query_code: str, tracking_type: str = "auto") -> Dict[str, Any]:
        """
        Kargo takip numarası veya Uçuş kodu (TK1923, PC2020 vb.) sorgular ve ilgili takip sayfasını hazırlar.
        """
        code = query_code.strip().upper()
        is_flight = tracking_type.lower() == "flight" or any(code.startswith(p) for p in ("TK", "PC", "VF", "AJ", "LH", "BA", "AF"))

        if is_flight:
            flight_url = f"https://www.flightradar24.com/data/flights/{code.lower()}"
            return {
                "ok": True,
                "speech": f"{code} sefer sayılı uçuşun canlı radar ve durum sayfasını kontrol ediyorum.",
                "tracking_url": flight_url,
                "type": "flight",
            }
        else:
            cargo_url = f"https://kargotakip.org/?q={urllib.parse.quote(code)}"
            return {
                "ok": True,
                "speech": f"{code} numaralı gönderinin kargo durum sayfasını açıyorum.",
                "tracking_url": cargo_url,
                "type": "cargo",
            }

    def _get_ip_location(self) -> Dict[str, Any]:
        """
        IP Geolocation servisi üzerinden şehrini ve yaklaşık koordinatlarını tespit eder.
        """
        if self._cached_ip_location:
            return self._cached_ip_location

        # 1. Öncelik: ip-api.com
        try:
            req = urllib.request.Request("http://ip-api.com/json", headers={"User-Agent": "YumiAssistant/1.0"})
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("status") == "success":
                    self._cached_ip_location = {
                        "city": data.get("city", "İstanbul"),
                        "regionName": data.get("regionName", ""),
                        "country": data.get("country", "Türkiye"),
                        "lat": data.get("lat"),
                        "lon": data.get("lon"),
                        "isp": data.get("isp"),
                    }
                    return self._cached_ip_location
        except Exception:
            pass

        # 2. Yedek: ipapi.co
        try:
            req = urllib.request.Request("https://ipapi.co/json/", headers={"User-Agent": "YumiAssistant/1.0"})
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                self._cached_ip_location = {
                    "city": data.get("city", "İstanbul"),
                    "regionName": data.get("region", ""),
                    "country": data.get("country_name", "Türkiye"),
                    "lat": data.get("latitude"),
                    "lon": data.get("longitude"),
                    "isp": data.get("org"),
                }
                return self._cached_ip_location
        except Exception:
            pass

        return {}

    def _resolve_location(self, name: str) -> tuple[float, float] | None:
        low = name.lower().strip()
        if low in self.LANDMARKS:
            return self.LANDMARKS[low]
        # Nominatim açık geocoding
        try:
            url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(name)}&format=json&limit=1"
            req = urllib.request.Request(url, headers={"User-Agent": "YumiDesktopAssistant/1.0"})
            with urllib.request.urlopen(req, timeout=3.5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if data:
                return float(data[0]["lat"]), float(data[0]["lon"])
        except Exception:
            pass
        return None
