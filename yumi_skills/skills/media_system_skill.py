import ctypes
import os
import platform
import random
import subprocess
import urllib.parse
import webbrowser
from typing import Any, Dict


class MediaSystemSkill:
    """
    Alexa'nın Müzik/Medya (Spotify, YouTube, YouTube Music), Ortam Sesleri (Ambient Sounds),
    Windows Global Medya Tuşları (Oynat/Durdur, Sonraki Şarkı, Ses Kontrolü),
    Güvenli Sistem Uygulamaları ve Karar Verici (Yazı-Tura, Zar, Rastgele Seçim) becerileri.
    """

    AMBIENT_STREAMS = {
        "yağmur": "https://www.youtube.com/results?search_query=rain+sounds+relaxing+1+hour",
        "şömine": "https://www.youtube.com/results?search_query=fireplace+crackling+sound",
        "beyaz gürültü": "https://www.youtube.com/results?search_query=white+noise+focus",
        "orman": "https://www.youtube.com/results?search_query=forest+nature+sounds",
        "kafe": "https://www.youtube.com/results?search_query=coffee+shop+ambience",
        "lofi": "https://www.youtube.com/watch?v=jfKfPfyJRdk",
    }

    LIVE_RADIOS = {
        "power fm": "https://powerapp.com.tr/radyo/power-fm",
        "powerfm": "https://powerapp.com.tr/radyo/power-fm",
        "power türk": "https://powerapp.com.tr/radyo/powerturk",
        "powerturk": "https://powerapp.com.tr/radyo/powerturk",
        "kral pop": "https://www.kralmuzik.com.tr/radyo/kral-pop",
        "kralpop": "https://www.kralmuzik.com.tr/radyo/kral-pop",
        "süper fm": "https://karnaval.com/radyolar/superfm",
        "super fm": "https://karnaval.com/radyolar/superfm",
        "joy fm": "https://karnaval.com/radyolar/joyfm",
        "joyfm": "https://karnaval.com/radyolar/joyfm",
        "fenomen": "https://www.radyofenomen.com/canli-dinle",
        "radyo fenomen": "https://www.radyofenomen.com/canli-dinle",
        "virgin radio": "https://karnaval.com/radyolar/virginradioturkiye",
    }

    # WhatsApp ve Discord hariç temel araçlar ve medya uygulamaları
    WINDOWS_APPS = {
        "hesap makinesi": "calc.exe",
        "not defteri": "notepad.exe",
        "paint": "mspaint.exe",
        "görev yöneticisi": "taskmgr.exe",
        "dosya gezgini": "explorer.exe",
        "ayarlar": "ms-settings:",
        "spotify": "spotify:",
    }

    # Windows Virtual-Key kodları (Global medya ve ses kontrolü için)
    VK_MEDIA_NEXT_TRACK = 0xB0
    VK_MEDIA_PREV_TRACK = 0xB1
    VK_MEDIA_STOP = 0xB2
    VK_MEDIA_PLAY_PAUSE = 0xB3
    VK_VOLUME_MUTE = 0xAD
    VK_VOLUME_DOWN = 0xAE
    VK_VOLUME_UP = 0xAF

    def play_media_or_ambient(self, query: str, platform_target: str = "youtube") -> Dict[str, Any]:
        """
        Spotify, YouTube veya YouTube Music üzerinde şarkı/sanatçı/çalma listesi ya da odaklanma/ortam sesi başlatır.
        platform_target: 'spotify', 'youtube', 'youtube_music'
        """
        q_low = query.strip().lower()
        for key, url in self.AMBIENT_STREAMS.items():
            if key in q_low and platform_target.lower() == "youtube":
                webbrowser.open(url)
                return {
                    "ok": True,
                    "speech": f"{key.capitalize()} ortam sesini açıyorum.",
                    "url": url,
                }

        encoded = urllib.parse.quote(query.strip())
        pt = platform_target.strip().lower()

        if pt == "spotify":
            # Masaüstü Spotify yüklüyse URI ile, değilse web üzerinden açar
            spotify_uri = f"spotify:search:{encoded}"
            try:
                os.startfile(spotify_uri)  # type: ignore[attr-defined]
                url = spotify_uri
            except Exception:
                url = f"https://open.spotify.com/search/{encoded}"
                webbrowser.open(url)
            target_label = "Spotify"
        elif pt in ("youtube_music", "ytmusic", "youtube music"):
            url = f"https://music.youtube.com/search?q={encoded}"
            webbrowser.open(url)
            target_label = "YouTube Music"
        else:
            url = f"https://www.youtube.com/results?search_query={encoded}"
            webbrowser.open(url)
            target_label = "YouTube"

        return {
            "ok": True,
            "speech": f"'{query}' için {target_label} üzerinde oynatmayı başlatıyorum.",
            "url": url,
        }

    def play_live_radio(self, station_name: str) -> Dict[str, Any]:
        """
        Canlı Türkçe veya yabancı radyo istasyonlarını (Power FM, Kral Pop, Süper FM, Joy FM, Fenomen vb.) doğrudan başlatır.
        """
        st_low = station_name.strip().lower()
        target_url = None
        matched_name = station_name

        for k, url in self.LIVE_RADIOS.items():
            if k in st_low or st_low in k:
                target_url = url
                matched_name = k.title()
                break

        if not target_url:
            target_url = f"https://www.canliradyodinle.fm/?s={urllib.parse.quote(station_name)}"
            matched_name = station_name

        webbrowser.open(target_url)
        return {
            "ok": True,
            "speech": f"Canlı {matched_name} radyosunu açıyorum, keyifli dinlemeler!",
            "radio_url": target_url,
        }

    def media_transport_control(self, action: str = "play_pause", steps: int = 5) -> Dict[str, Any]:
        """
        Spotify, YouTube veya YouTube Music'te çalan medyayı ve sistem sesini Windows Global Medya Tuşları ile kontrol eder.
        action:
          - 'play_pause' / 'pause' / 'play' / 'resume': Müziği duraklatır veya devam ettirir
          - 'next': Sonraki şarkıya geçer
          - 'previous': Önceki şarkıya döner
          - 'stop': Medyayı durdurur
          - 'mute': Sesi tamamen kapatır/açar
          - 'volume_up': Sesi açar
          - 'volume_down': Sesi kısar
        """
        act = action.strip().lower()
        key_map = {
            "play_pause": (self.VK_MEDIA_PLAY_PAUSE, "Medya oynat/duraklat komutu gönderildi."),
            "play": (self.VK_MEDIA_PLAY_PAUSE, "Medya devam ettiriliyor."),
            "resume": (self.VK_MEDIA_PLAY_PAUSE, "Medya devam ettiriliyor."),
            "pause": (self.VK_MEDIA_PLAY_PAUSE, "Medya duraklatıldı."),
            "next": (self.VK_MEDIA_NEXT_TRACK, "Sonraki parçaya geçildi."),
            "sonraki": (self.VK_MEDIA_NEXT_TRACK, "Sonraki parçaya geçildi."),
            "previous": (self.VK_MEDIA_PREV_TRACK, "Önceki parçaya dönüldü."),
            "önceki": (self.VK_MEDIA_PREV_TRACK, "Önceki parçaya dönüldü."),
            "stop": (self.VK_MEDIA_STOP, "Medya durduruldu."),
            "mute": (self.VK_VOLUME_MUTE, "Sistem sesi değiştirildi."),
        }

        try:
            if act in ("volume_up", "ses aç", "sesi aç"):
                count = max(1, min(int(steps), 25))
                for _ in range(count):
                    self._press_vk(self.VK_VOLUME_UP)
                return {"ok": True, "speech": "Sesi açtım."}
            elif act in ("volume_down", "ses kıs", "sesi kıs"):
                count = max(1, min(int(steps), 25))
                for _ in range(count):
                    self._press_vk(self.VK_VOLUME_DOWN)
                return {"ok": True, "speech": "Sesi kıstım."}
            elif act in key_map:
                vk, msg = key_map[act]
                self._press_vk(vk)
                return {"ok": True, "speech": msg}
            else:
                return {"ok": False, "speech": f"'{action}' medya komutunu tanıyamadım."}
        except Exception as e:
            return {"ok": False, "speech": f"Medya kontrolü sırasında hata oluştu: {e}"}

    @staticmethod
    def _press_vk(vk_code: int) -> None:
        if hasattr(ctypes, "windll"):
            ctypes.windll.user32.keybd_event(vk_code, 0, 0, 0)
            ctypes.windll.user32.keybd_event(vk_code, 0, 2, 0)

    def launch_application(self, app_name: str) -> Dict[str, Any]:
        """Windows sistem uygulamalarını (Hesap makinesi, Not defteri, Spotify, Ayarlar vb.) açar."""
        name_low = app_name.strip().lower()
        cmd = self.WINDOWS_APPS.get(name_low)
        if not cmd:
            return {"ok": False, "speech": f"'{app_name}' uygulamasını izin verilen uygulama listemde bulamadım."}

        try:
            if cmd.endswith(":"):
                os.startfile(cmd)  # type: ignore[attr-defined]
            else:
                subprocess.Popen([cmd], shell=False)
            return {"ok": True, "speech": f"{app_name.capitalize()} açılıyor."}
        except Exception as e:
            return {"ok": False, "speech": f"{app_name} açılırken hata oluştu: {e}"}

    def system_status(self) -> Dict[str, Any]:
        """Bilgisayarın işletim sistemi ve pil/donanım durumu hakkında bilgi verir."""
        info = f"Sistem {platform.system()} {platform.release()} üzerinde çalışıyor."
        try:
            import psutil  # type: ignore

            cpu = psutil.cpu_percent(interval=0.2)
            ram = psutil.virtual_memory().percent
            battery = psutil.sensors_battery()
            bat_str = f", pil seviyesi yüzde {int(battery.percent)}" if battery else ""
            speech = f"İşlemci kullanımı yüzde {int(cpu)}, bellek kullanımı yüzde {int(ram)}{bat_str}."
            return {"ok": True, "speech": speech}
        except ImportError:
            return {"ok": True, "speech": info}

    def decision_maker(self, mode: str = "coin", options_csv: str = "", max_number: int = 100) -> Dict[str, Any]:
        """
        Alexa karar verici:
        - mode='coin': Yazı-tura atar.
        - mode='dice': Zar atar (1-6).
        - mode='number': 1 ile max_number arasında rastgele sayı tutar.
        - mode='pick': options_csv içindeki virgülle ayrılmış seçeneklerden birini seçer.
        """
        m = mode.strip().lower()
        if m in ("coin", "yazı tura", "yazi tura"):
            res = random.choice(["Yazı", "Tura"])
            return {"ok": True, "speech": f"Parayı havaya attım: {res} geldi!", "result": res}
        elif m in ("dice", "zar"):
            res = random.randint(1, 6)
            return {"ok": True, "speech": f"Zarı attım: {res} geldi!", "result": res}
        elif m in ("pick", "seç", "sec"):
            opts = [o.strip() for o in options_csv.split(",") if o.strip()]
            if not opts:
                return {"ok": False, "speech": "Seçim yapmam için seçenekleri söylemelisin."}
            chosen = random.choice(opts)
            return {"ok": True, "speech": f"Seçimim: {chosen}!", "result": chosen}
        else:
            upper = max(2, int(max_number))
            res = random.randint(1, upper)
            return {"ok": True, "speech": f"1 ile {upper} arasında tuttuğum sayı: {res}.", "result": res}
