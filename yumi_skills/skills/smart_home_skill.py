import json
import socket
import urllib.request
from typing import Any, Dict, List

from ..storage import SkillStorage


class SmartHomeSkill:
    """
    Alexa Akıllı Ev (Smart Home) Becerisi:
    - Evdeki Wi-Fi ağı üzerinde otomatik cihaz keşfi (SSDP / Yeelight / Hue / Kasa / Home Assistant)
    - Cihazları takma isimle ("Robot Süpürge", "Salon Işığı", "Gece Lambası") kaydetme ve hatırlama
    - Robot Süpürge Kontrolü (Xiaomi/Roborock/Dreame python-miio + Home Assistant köprüsü)
    - Akıllı Işık ve Priz Kontrolü (Philips Hue, Yeelight, TP-Link Tapo/Kasa, Tuya, Home Assistant)
    """

    def __init__(self, storage: SkillStorage):
        self.storage = storage
        self._tv_bridge = None

    def _android_tv(self):
        if self._tv_bridge is None:
            from ..android_tv_bridge import AndroidTVBridge
            self._tv_bridge = AndroidTVBridge(self.storage)
        return self._tv_bridge

    def pair_android_tv(self, host: str, code: str = '', name: str = 'Salon TV'):
        try:
            import ipaddress
            host = str(ipaddress.ip_address(host.strip()))
            result = self._android_tv().finish(host, code) if code else self._android_tv().begin(host)
            if code and result.get('ok'):
                self.register_smart_device(name=name, device_type='tv', brand_or_protocol='android_tv', ip_address=host)
            return result
        except Exception:
            return {'ok':False,'speech':'TV ile eşleşme tamamlanamadı. TV açık olmalı; IP adresini ve ekrandaki kodu kontrol et.'}

    def close(self):
        if self._tv_bridge is not None:
            self._tv_bridge.close(); self._tv_bridge = None

    def discover_wifi_devices(self, timeout_sec: float = 2.5) -> Dict[str, Any]:
        """
        Evdeki yerel Wi-Fi ağını (SSDP / UPnP ve Yeelight/Hue protokolleri ile) tarayarak
        bulunan akıllı cihazları listeler ve kaydedilmeye hazır hale getirir.
        """
        discovered: List[Dict[str, Any]] = []

        # 1. SSDP (UPnP / Philips Hue / Akıllı TV / IoT) UDP Multicast Taraması
        ssdp_request = (
            "M-SEARCH * HTTP/1.1\r\n"
            "HOST: 239.255.255.250:1900\r\n"
            'MAN: "ssdp:discover"\r\n'
            "MX: 2\r\n"
            "ST: ssdp:all\r\n\r\n"
        ).encode("utf-8")

        seen_ips = set()
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            sock.settimeout(timeout_sec)
            sock.sendto(ssdp_request, ("239.255.255.250", 1900))
            while True:
                try:
                    data, addr = sock.recvfrom(2048)
                    ip = addr[0]
                    if ip in seen_ips:
                        continue
                    text = data.decode("utf-8", errors="ignore")
                    low = text.lower()
                    if any(k in low for k in ("hue", "yeelight", "tuya", "tapo", "kasa", "xiaomi", "roborock", "dlna", "upnp", "webos", "samsung")):
                        seen_ips.add(ip)
                        server_line = ""
                        for line in text.splitlines():
                            if line.upper().startswith("SERVER:") or line.upper().startswith("ST:"):
                                server_line = line.split(":", 1)[1].strip()
                                break
                        discovered.append(
                            {
                                "ip": ip,
                                "info": server_line or "Wi-Fi Akıllı Cihaz",
                                "protocol": "hue" if "hue" in low else ("yeelight" if "yeelight" in low else "generic_upnp"),
                            }
                        )
                except socket.timeout:
                    break
            sock.close()
        except Exception:
            pass

        # 2. Yeelight Özel Multicast Taraması (239.255.255.250:1982)
        yeelight_msg = (
            "M-SEARCH * HTTP/1.1\r\n"
            "HOST: 239.255.255.250:1982\r\n"
            'MAN: "ssdp:discover"\r\n'
            "ST: wifi_bulb\r\n\r\n"
        ).encode("utf-8")
        try:
            ysock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            ysock.settimeout(1.2)
            ysock.sendto(yeelight_msg, ("239.255.255.250", 1982))
            while True:
                try:
                    data, addr = ysock.recvfrom(2048)
                    ip = addr[0]
                    if ip not in seen_ips:
                        seen_ips.add(ip)
                        discovered.append({"ip": ip, "info": "Xiaomi Yeelight Akıllı Ampul", "protocol": "yeelight"})
                except socket.timeout:
                    break
            ysock.close()
        except Exception:
            pass

        if not discovered:
            return {
                "ok": True,
                "speech": (
                    "Wi-Fi ağını taradım ancak doğrudan açık yayın yapan bir cihaz göremedim. "
                    "Xiaomi/Roborock süpürge, Tuya veya Home Assistant cihazlarını isim ve IP/token ile bir kez kaydedebilirsin."
                ),
                "discovered": [],
            }

        summary = ", ".join(f"{d['info']} ({d['ip']})" for d in discovered[:5])
        return {
            "ok": True,
            "speech": f"Wi-Fi ağında {len(discovered)} akıllı cihaz buldum: {summary}. Bunları istediğin oda veya cihaz adıyla kaydetmemi söyleyebilirsin.",
            "discovered": discovered,
        }

    def register_smart_device(
        self,
        name: str,
        device_type: str,
        brand_or_protocol: str,
        ip_address: str = "",
        token_or_key: str = "",
        entity_id: str = "",
        room: str = "",
        aliases_csv: str = "",
    ) -> Dict[str, Any]:
        """
        Bir akıllı ev cihazını (Robot süpürge, akıllı ışık, Tuya priz, Akıllı TV vb.) Yumi'nin içindeki özel adıyla kaydeder.
        Wi-Fi'da 'tuya-plug-01' olarak görünse bile Yumi'de 'Başucu Lambası' olarak kaydedilir ve o isimle tetiklenir.
        - name: Cihazın Yumi'deki özel adı (Örn: 'Başucu Lambası', 'Salon TV', 'Yatak Odası TV')
        - device_type: 'vacuum' (süpürge), 'light' (ışık/lamba), 'plug' (priz), 'tv' (televizyon)
        - brand_or_protocol: 'tuya', 'xiaomi', 'roborock', 'yeelight', 'hue', 'tapo', 'dlna_tv', 'home_assistant'
        - ip_address: Cihazın yerel Wi-Fi IP adresi
        - token_or_key: Tuya local_key, Xiaomi token, TV MAC adresi veya Home Assistant token'ı
        - entity_id: Tuya device_id veya Home Assistant entity_id
        - room: Bulunduğu oda (Örn: 'Salon', 'Yatak Odası')
        - aliases_csv: Virgülle ayrılmış alternatif seslenme adları (Örn: 'gece lambası, başucu ışığı')
        """
        key = name.strip().lower()
        alias_list = [a.strip().lower() for a in aliases_csv.split(",") if a.strip()]
        dev_record = {
            "name": name.strip(),
            "device_type": device_type.strip().lower(),
            "protocol": brand_or_protocol.strip().lower(),
            "ip": ip_address.strip(),
            "token": token_or_key.strip(),
            "entity_id": entity_id.strip(),
            "room": room.strip(),
            "aliases": alias_list,
        }

        def _upd(devices):
            devices = devices or {}
            devices[key] = dev_record
            return devices

        self.storage.update_section("smart_devices", _upd)
        return {
            "ok": True,
            "speech": f"Cihazı '{name}' adıyla kaydettim. Wi-Fi'daki fabrika adı ne olursa olsun artık '{name}' dediğinde doğrudan onu kontrol edeceğim.",
            "device": dev_record,
        }

    def rename_or_alias_device(self, current_name_or_ip: str, new_custom_name: str, treat_as_type: str = "") -> Dict[str, Any]:
        """
        Wi-Fi'da veya bulutta bulunan bir cihaza (örn: 'Tuya Smart Plug' veya '192.168.1.50')
        Alexa'daki gibi özel bir isim ('Başucu Lambası', 'Salon TV') atar.
        Priz olsa bile `treat_as_type='light'` verilirse lamba gibi davranır.
        """
        devices: Dict[str, Any] = self.storage.get("smart_devices", {})
        q = current_name_or_ip.strip().lower()
        target_key = None
        target_dev = None

        for k, dev in devices.items():
            if q == k or q == dev.get("ip", "").lower() or q == dev.get("entity_id", "").lower() or q in k:
                target_key = k
                target_dev = dev
                break

        if not target_dev:
            return {
                "ok": False,
                "speech": f"'{current_name_or_ip}' ile eşleşen bir cihaz bulamadım.",
            }

        old_name = target_dev["name"]
        aliases = target_dev.get("aliases", [])
        if old_name.lower() not in aliases:
            aliases.append(old_name.lower())

        target_dev["name"] = new_custom_name.strip()
        target_dev["aliases"] = aliases
        if treat_as_type.strip():
            target_dev["device_type"] = treat_as_type.strip().lower()

        del devices[target_key]
        devices[new_custom_name.strip().lower()] = target_dev
        self.storage.set("smart_devices", devices)

        return {
            "ok": True,
            "speech": f"'{old_name}' cihazının adını '{new_custom_name}' olarak güncelledim. Artık '{new_custom_name} aç/kapat' diyebilirsin.",
            "device": target_dev,
        }

    def sync_cloud_bridge_devices(self, platform_name: str, username_or_api_key: str = "", password_or_secret: str = "", region: str = "eu") -> Dict[str, Any]:
        """
        Telefondaki Xiaomi (Mi Home) veya Tuya (Smart Life) uygulama köprüsüne bağlanarak,
        kullanıcının telefonda cihazlara verdiği özel isimleri ('Başucu Lambası', 'Salon Süpürgesi' vb.),
        yerel Wi-Fi IP adreslerini ve şifreleme anahtarlarını (token / local_key) tek seferde Yumi'ye çeker.
        """
        plat = platform_name.strip().lower()

        # 1. Xiaomi Mi Home Bulut Köprüsü (micloud)
        if plat in ("xiaomi", "mihome", "mi home", "roborock"):
            try:
                from micloud import MiCloud  # type: ignore

                mc = MiCloud(username_or_api_key, password_or_secret)
                if not mc.login():
                    return {"ok": False, "speech": "Xiaomi Mi Home hesabına giriş yapılamadı, bilgileri kontrol et."}
                country={'eu':'de','tr':'de','turkey':'de','türkiye':'de'}.get(region.strip().lower(),region.strip().lower())
                raw_devices = mc.get_devices(country=country) or []
                count = 0
                for d in raw_devices:
                    name = d.get("name")
                    ip = d.get("localip", "")
                    token = d.get("token", "")
                    model = d.get("model", "").lower()
                    if not name or not ip:
                        continue
                    dtype = "vacuum" if ("vacuum" in model or "roborock" in model) else ("light" if "light" in model or "bulb" in model else "plug")
                    proto = "yeelight" if "yeelink" in model else "xiaomi"
                    self.register_smart_device(name=name, device_type=dtype, brand_or_protocol=proto, ip_address=ip, token_or_key=token, entity_id=str(d.get("did", "")))
                    self.storage.update_section('smart_devices',lambda devices,n=name.lower(),model=model:{**devices,n:{**devices[n],'model':model}})
                    count += 1
                return {
                    "ok": True,
                    "speech": f"Xiaomi Mi Home hesabından {count} cihazı telefonda verdiğin isimlerle Yumi'ye aktardım!",
                }
            except ImportError:
                return {
                    "ok": False,
                    "speech": "Xiaomi bulut senkronizasyonu için `pip install micloud python-miio` kurulumu gerekiyor.",
                }
            except Exception as e:
                return {"ok": False, "speech": f"Xiaomi bulut köprüsü hatası: {e}"}

        # 2. Tuya / Smart Life Köprüsü (tinytuya)
        if plat in ("tuya", "smartlife", "smart life"):
            try:
                import tinytuya  # type: ignore

                # Eğer kullanıcı tinytuya snapshot/devices.json oluşturduysa veya Cloud API bilgilerini verdiyse
                if username_or_api_key and password_or_secret:
                    cloud = tinytuya.Cloud(apiRegion=region, apiKey=username_or_api_key, apiSecret=password_or_secret)
                    tuya_devs = cloud.getdevices() or []
                    # Yerel ağdaki Tuya IP'lerini tara ve eşleştir
                    scanned = tinytuya.deviceScan(False, 2) or {}
                    ip_by_id = {v.get("gwId"): k for k, v in scanned.items() if v.get("gwId")}

                    count = 0
                    for td in tuya_devs:
                        dev_id = td.get("id", "")
                        custom_name = td.get("name", f"Tuya_{dev_id[:4]}")
                        local_key = td.get("key", "")
                        ip = ip_by_id.get(dev_id, td.get("ip", ""))
                        cat = td.get("category", "").lower()
                        # Kullanıcı prize 'lamba' veya 'ışık' adını verdiyse otomatik ışık olarak da işaretle
                        is_light_named = any(w in custom_name.lower() for w in ("lamba", "ışık", "isik", "ampul", "led"))
                        dtype = "light" if (is_light_named or "dj" in cat or "light" in cat) else "plug"
                        self.register_smart_device(
                            name=custom_name,
                            device_type=dtype,
                            brand_or_protocol="tuya",
                            ip_address=ip,
                            token_or_key=local_key,
                            entity_id=dev_id,
                        )
                        count += 1
                    return {
                        "ok": True,
                        "speech": f"Tuya Smart Life köprüsünden {count} cihazı ('{tuya_devs[0].get('name')}' dahil) telefonundaki isimleriyle Yumi'ye kaydettim!",
                    }
            except ImportError:
                return {
                    "ok": False,
                    "speech": "Tuya / Smart Life priz ve lambalarını kontrol etmek için `pip install tinytuya` paketi kurulmalı.",
                }
        # 3. Philips Hue Bridge (Yerel Köprü - Fiziksel Tuş Eşleştirmesi veya Mevcut API Key ile tüm lambaları ve isimlerini çeker)
        if plat in ("hue", "philips", "philips hue"):
            bridge_ip = username_or_api_key.strip()
            api_user = password_or_secret.strip()
            if not bridge_ip:
                return {"ok": False, "speech": "Philips Hue Bridge IP adresini girmelisin."}
            try:
                # Eğer henüz api_user yoksa, Hue Bridge üzerindeki fiziksel link butonuna basılmış kabul edip yeni kullanıcı oluşturur
                if not api_user:
                    pair_req = urllib.request.Request(
                        f"http://{bridge_ip}/api",
                        data=json.dumps({"devicetype": "yumi_assistant#pc"}).encode("utf-8"),
                        method="POST",
                    )
                    with urllib.request.urlopen(pair_req, timeout=5) as resp:
                        pair_data = json.loads(resp.read().decode("utf-8"))
                    if isinstance(pair_data, list) and pair_data and "error" in pair_data[0]:
                        return {
                            "ok": False,
                            "speech": "Philips Hue kutusunun üzerindeki fiziksel orta tuşa basıp 30 saniye içinde tekrar 'Bağla' butonuna tıkla.",
                        }
                    api_user = pair_data[0]["success"]["username"]

                # Tüm kayıtlı Hue ışık ve prizlerini telefonda verilen isimleriyle çek
                with urllib.request.urlopen(f"http://{bridge_ip}/api/{api_user}/lights", timeout=5) as resp:
                    lights_data = json.loads(resp.read().decode("utf-8"))
                count = 0
                for light_id, linfo in lights_data.items():
                    cname = linfo.get("name", f"Hue Işık {light_id}")
                    ltype = "plug" if "plug" in linfo.get("type", "").lower() else "light"
                    self.register_smart_device(
                        name=cname,
                        device_type=ltype,
                        brand_or_protocol="hue",
                        ip_address=bridge_ip,
                        token_or_key=api_user,
                        entity_id=str(light_id),
                    )
                    count += 1
                return {
                    "ok": True,
                    "speech": f"Philips Hue köprüsünden {count} cihazı kendi isimleriyle Yumi'ye aktardım!",
                    "hue_username": api_user,
                }
            except Exception as e:
                return {"ok": False, "speech": f"Philips Hue köprüsü bağlantı hatası: {e}"}

        # 4. IKEA Home Smart Köprüsü (DIRIGERA & TRÅDFRI Hub)
        if plat in ("ikea", "dirigera", "tradfri"):
            hub_ip = username_or_api_key.strip()
            hub_token = password_or_secret.strip()
            if not hub_ip or not hub_token:
                return {"ok": False, "speech": "IKEA Hub IP adresi ve güvenlik anahtarı (Token/Security Code) gerekli."}
            try:
                import dirigera  # type: ignore

                hub = dirigera.Hub(token=hub_token, ip_address=hub_ip)
                count = 0
                for lgt in hub.get_lights():
                    cname = getattr(lgt.attributes, "custom_name", "") or f"IKEA Işık {lgt.id[:4]}"
                    room_name = getattr(lgt.room, "name", "") if getattr(lgt, "room", None) else ""
                    self.register_smart_device(
                        name=cname,
                        device_type="light",
                        brand_or_protocol="ikea_dirigera",
                        ip_address=hub_ip,
                        token_or_key=hub_token,
                        entity_id=str(lgt.id),
                        room=room_name,
                    )
                    count += 1
                for out in hub.get_outlets():
                    cname = getattr(out.attributes, "custom_name", "") or f"IKEA Priz {out.id[:4]}"
                    room_name = getattr(out.room, "name", "") if getattr(out, "room", None) else ""
                    is_light = any(w in cname.lower() for w in ("lamba", "ışık", "isik", "ampul"))
                    self.register_smart_device(
                        name=cname,
                        device_type="light" if is_light else "plug",
                        brand_or_protocol="ikea_dirigera",
                        ip_address=hub_ip,
                        token_or_key=hub_token,
                        entity_id=str(out.id),
                        room=room_name,
                    )
                    count += 1
                return {"ok": True, "speech": f"IKEA DIRIGERA köprüsünden {count} cihazı kendi isimleriyle Yumi'ye kaydettim!"}
            except ImportError:
                return {"ok": False, "speech": "IKEA köprüsü için `pip install dirigera` paketi kurulmalı."}
            except Exception as e:
                return {"ok": False, "speech": f"IKEA köprüsü hatası: {e}"}

        # 5. TP-Link Tapo / Kasa Köprüsü (Yerel Ağdaki tüm Tapo/Kasa cihazlarını telefon uygulamasındaki alias isimleriyle çeker)
        if plat in ("tapo", "kasa", "tplink", "tp-link"):
            try:
                import asyncio
                from kasa import Credentials, Discover  # type: ignore

                creds = Credentials(username_or_api_key, password_or_secret) if username_or_api_key else None
                found = asyncio.run(Discover.discover(credentials=creds))
                count = 0
                for ip, kdev in found.items():
                    asyncio.run(kdev.update())
                    cname = kdev.alias or f"Tapo_{ip.split('.')[-1]}"
                    is_light = kdev.is_bulb or kdev.is_light_strip or any(w in cname.lower() for w in ("lamba", "ışık", "isik"))
                    self.register_smart_device(
                        name=cname,
                        device_type="light" if is_light else "plug",
                        brand_or_protocol="tapo",
                        ip_address=ip,
                        token_or_key=f"{username_or_api_key}:{password_or_secret}" if username_or_api_key else "",
                        entity_id=getattr(kdev, "device_id", ""),
                    )
                    count += 1
                return {"ok": True, "speech": f"TP-Link Tapo/Kasa ağından {count} cihazı özel isimleriyle içeri aktardım!"}
            except ImportError:
                return {"ok": False, "speech": "TP-Link Tapo/Kasa için `pip install python-kasa` paketi kurulmalı."}
            except Exception as e:
                return {"ok": False, "speech": f"TP-Link Tapo/Kasa hatası: {e}"}

        # 6. Home Assistant Evrensel Köprüsü (IKEA, Zigbee, Matter, LG/Samsung TV, Tuya dahil tüm cihazları tek seferde çeker!)
        if plat in ("home_assistant", "ha", "homeassistant"):
            base_url = username_or_api_key.strip().rstrip("/")
            ha_token = password_or_secret.strip()
            if not base_url.startswith("http"):
                base_url = f"http://{base_url}:8123"
            try:
                req = urllib.request.Request(
                    f"{base_url}/api/states",
                    headers={"Authorization": f"Bearer {ha_token}", "Content-Type": "application/json"},
                )
                with urllib.request.urlopen(req, timeout=6) as resp:
                    states = json.loads(resp.read().decode("utf-8"))
                count = 0
                for st in states:
                    ent_id = st.get("entity_id", "")
                    domain = ent_id.split(".")[0] if "." in ent_id else ""
                    if domain not in ("light", "switch", "vacuum", "media_player"):
                        continue
                    friendly = st.get("attributes", {}).get("friendly_name", ent_id)
                    dtype_map = {"light": "light", "switch": "plug", "vacuum": "vacuum", "media_player": "tv"}
                    dtype = dtype_map[domain]
                    if dtype == "plug" and any(w in friendly.lower() for w in ("lamba", "ışık", "isik")):
                        dtype = "light"
                    self.register_smart_device(
                        name=friendly,
                        device_type=dtype,
                        brand_or_protocol="home_assistant",
                        ip_address=base_url,
                        token_or_key=ha_token,
                        entity_id=ent_id,
                    )
                    count += 1
                return {"ok": True, "speech": f"Home Assistant köprüsünden {count} cihazı (ışık, priz, süpürge, TV) isimleriyle Yumi'ye aktardım!"}
            except Exception as e:
                return {"ok": False, "speech": f"Home Assistant köprüsü hatası: {e}"}

        return {
            "ok": False,
            "speech": f"'{platform_name}' köprüsü tanımsız. Desteklenenler: Xiaomi Mi Home, Tuya/Smart Life, Philips Hue, IKEA, TP-Link Tapo/Kasa, Home Assistant.",
        }

    def list_smart_devices(self) -> Dict[str, Any]:
        """Kayıtlı tüm akıllı ev cihazlarını Yumi'deki özel isimleriyle listeler."""
        devices: Dict[str, Any] = self.storage.get("smart_devices", {})
        if not devices:
            return {
                "ok": True,
                "speech": "Henüz kayıtlı bir akıllı ev cihazın yok. 'Ağdaki cihazları tara' diyebilir veya Xiaomi/Tuya cihazlarını tanıtabilirsin.",
                "devices": [],
            }
        names = [f"{d['name']} ({d['protocol']})" for d in devices.values()]
        return {
            "ok": True,
            "speech": f"Kayıtlı {len(names)} akıllı cihazın var: " + ", ".join(names) + ".",
            "devices": list(devices.values()),
        }

    def control_vacuum(self, action: str = "start", device_name: str = "süpürge") -> Dict[str, Any]:
        """
        Evdeki akıllı robot süpürgeyi (Roborock, Xiaomi Mi Home, Dreame veya Home Assistant) kontrol eder.
        Evde birden fazla süpürge varsa ve hangisi olduğu belirtilmediyse kullanıcıya sorar.
        """
        dev, ambiguity = self._resolve_device_or_ask(device_name, device_types=["vacuum"], generic_words=("süpürge", "supurge", "robot"))
        if ambiguity:
            return ambiguity
        if not dev:
            return {
                "ok": False,
                "speech": (
                    f"'{device_name}' henüz tanıtılmamış. Robot süpürgeni Mi Home köprüsüyle veya IP/token ile "
                    "bir kez kaydettikten sonra sesle çalıştırabilirim."
                ),
            }

        act = action.strip().lower()
        proto = dev.get("protocol", "")
        ip = dev.get("ip", "")
        token = dev.get("token", "")

        if proto in ("xiaomi", "roborock", "dreame", "miio","viomi"):
            try:
                from miio import Device,ViomiVacuum,RoborockVacuum,DreameVacuum
                model=dev.get('model','')
                if not model:model=Device(ip,token,timeout=3).info().model
                driver=ViomiVacuum if model.startswith('viomi.') else DreameVacuum if model.startswith('dreame.') else RoborockVacuum if model.startswith(('roborock.','rockrobo.')) else None
                if driver is None:return {'ok':False,'speech':f"{dev['name']} modeline uygun süpürge sürücüsü doğrulanamadı."}
                vac=driver(ip,token,model=model)
                if act in ("start", "başlat", "temizle"):
                    vac.start()
                    return {"ok": True, "speech": f"{dev['name']} temizliğe başladı."}
                elif act in ("stop", "pause", "durdur", "duraklat"):
                    vac.pause()
                    return {"ok": True, "speech": f"{dev['name']} duraklatıldı."}
                elif act in ("dock", "home", "şarj", "istasyon"):
                    vac.home()
                    return {"ok": True, "speech": f"{dev['name']} şarj istasyonuna dönüyor."}
                else:
                    st = vac.status()
                    return {
                        "ok": True,
                        "speech": f"{dev['name']} durumu: {st.state}, pil seviyesi yüzde {st.battery}.",
                    }
            except ImportError:
                return {
                    "ok": False,
                    "speech": "Xiaomi/Roborock yerel Wi-Fi kontrolü için 'python-miio' paketi kurulmalı (`pip install python-miio`).",
                }
            except Exception as e:
                return {"ok": False, "speech": f"Süpürgeye bağlanırken hata oluştu: {e}"}

        if proto in ("home_assistant", "ha"):
            service_map = {
                "start": "start",
                "stop": "pause",
                "pause": "pause",
                "dock": "return_to_base",
                "home": "return_to_base",
            }
            ha_service = service_map.get(act)
            if not ha_service:return {'ok':False,'speech':'Bu süpürge komutu desteklenmiyor; işlem uygulanmadı.'}
            return self._call_home_assistant(
                dev, domain="vacuum", service=ha_service, success_speech=f"{dev['name']} için '{act}' komutu uygulandı."
            )

        return {"ok": False, "speech": f"'{proto}' protokolü için süpürge komutu henüz yapılandırılmadı."}

    def control_light_or_plug(
        self,
        device_name: str,
        state: str = "on",
        brightness: int | None = None,
    ) -> Dict[str, Any]:
        """
        Evdeki Wi-Fi akıllı ışıkları ve akıllı prizleri (Tuya / Smart Life prizdeki Başucu Lambası, Yeelight, Philips Hue, Tapo, Home Assistant)
        kullanıcının verdiği özel isimle ('Başucu Lambası', 'Salon Işığı' vb.) açar/kapatır veya parlaklığını ayarlar.
        Eğer kullanıcı sadece 'ışığı aç' dediyse ve evde birden fazla ışık/lamba varsa hangisini istediğini sorar!
        """
        st = state.strip().lower()
        is_on = st not in ("off", "kapat", "kapalı", "false", "0")

        # 'tüm ışıklar' veya 'hepsi' dendiyse hepsini tek seferde aç/kapat
        if device_name.strip().lower() in ("hepsi", "tümü", "tüm ışıklar", "bütün ışıklar", "all"):
            devices: Dict[str, Any] = self.storage.get("smart_devices", {})
            targets = [d for d in devices.values() if d.get("device_type") in ("light", "plug")]
            if not targets:
                return {"ok": False, "speech": "Kayıtlı hiçbir akıllı ışık veya priz bulunamadı."}
            results = [self._execute_single_light_or_plug(d, is_on, brightness) for d in targets]
            ok_names = [d["name"] for d, r in zip(targets, results) if r.get("ok")]
            return {
                "ok": len(ok_names)==len(targets),
                "speech": f"Toplam {len(ok_names)} cihaz ({', '.join(ok_names)}) {'açıldı' if is_on else 'kapatıldı'}.",
            }

        dev, ambiguity = self._resolve_device_or_ask(
            device_name,
            device_types=["light", "plug"],
            generic_words=("ışık", "isik", "lamba", "ampul", "priz", "gece lambası"),
        )
        if ambiguity:
            return ambiguity
        if not dev:
            return {
                "ok": False,
                "speech": (
                    f"'{device_name}' adında kayıtlı bir akıllı ışık veya priz bulamadım. "
                    "Tuya prizini veya ampulünü 'Başucu Lambası olarak kaydet' diyerek bir kez tanıtabilirsin."
                ),
            }

        return self._execute_single_light_or_plug(dev, is_on, brightness)

    def _execute_single_light_or_plug(self, dev: Dict[str, Any], is_on: bool, brightness: int | None) -> Dict[str, Any]:
        proto = dev.get("protocol", "")
        ip = dev.get("ip", "")
        token = dev.get("token", "")
        entity_id = dev.get("entity_id", "")

        # 1. Tuya / Smart Life (Akıllı Priz veya Akıllı Ampul - örn: Tuya prize bağlı Başucu Lambası)
        if proto in ("tuya", "smartlife", "smart life"):
            try:
                import tinytuya  # type: ignore

                if dev.get("device_type") == "light" and brightness is not None:
                    d = tinytuya.BulbDevice(entity_id, ip, token)
                else:
                    d = tinytuya.OutletDevice(entity_id, ip, token)
                d.set_version(3.3)
                if is_on:
                    d.turn_on()
                    if brightness is not None and hasattr(d, "set_brightness_percentage"):
                        d.set_brightness_percentage(max(1, min(100, int(brightness))))
                else:
                    d.turn_off()
                return {"ok": True, "speech": f"{dev['name']} {'açıldı' if is_on else 'kapatıldı'}."}
            except ImportError:
                return {
                    "ok": False,
                    "speech": f"'{dev['name']}' (Tuya) kontrolü için `pip install tinytuya` paketi kurulmalı.",
                }
            except Exception as e:
                return {"ok": False, "speech": f"{dev['name']} (Tuya) bağlantısında hata: {e}"}

        # 2. Xiaomi Yeelight (Yerel TCP 55443)
        if proto == "yeelight" and ip:
            try:
                power_val = "on" if is_on else "off"
                cmd = {"id": 1, "method": "set_power", "params": [power_val, "smooth", 300]}
                self._send_yeelight_tcp(ip, cmd)
                if is_on and brightness is not None:
                    b_val = max(1, min(100, int(brightness)))
                    self._send_yeelight_tcp(ip, {"id": 2, "method": "set_bright", "params": [b_val, "smooth", 300]})
                action_tr = f"açıldı (parlaklık %{brightness})" if (is_on and brightness) else ("açıldı" if is_on else "kapatıldı")
                return {"ok": True, "speech": f"{dev['name']} {action_tr}."}
            except Exception as e:
                return {"ok": False, "speech": f"{dev['name']} bağlantısında hata: {e}"}

        # 3. Philips Hue (Yerel HTTP REST API)
        if proto == "hue" and ip:
            try:
                light_id = entity_id or "1"
                url = f"http://{ip}/api/{token}/lights/{light_id}/state"
                payload: Dict[str, Any] = {"on": is_on}
                if is_on and brightness is not None:
                    payload["bri"] = int(max(1, min(100, brightness)) * 2.54)
                req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), method="PUT")
                with urllib.request.urlopen(req, timeout=4):
                    pass
                return {"ok": True, "speech": f"{dev['name']} {'açıldı' if is_on else 'kapatıldı'}."}
            except Exception as e:
                return {"ok": False, "speech": f"Philips Hue bağlantısında hata: {e}"}

        # 4. TP-Link Tapo / Kasa (python-kasa)
        if proto in ("tapo", "kasa", "tplink") and ip:
            try:
                import asyncio
                from kasa import Discover  # type: ignore

                async def _toggle_kasa():
                    kdev = await Discover.discover_single(ip)
                    await kdev.update()
                    if is_on:
                        await kdev.turn_on()
                    else:
                        await kdev.turn_off()

                asyncio.run(_toggle_kasa())
                return {"ok": True, "speech": f"{dev['name']} {'açıldı' if is_on else 'kapatıldı'}."}
            except Exception as e:
                return {"ok": False, "speech": f"{dev['name']} (TP-Link) bağlantısında hata: {e}"}

        # 5. IKEA Home Smart (DIRIGERA Hub)
        if proto in ("ikea", "ikea_dirigera", "dirigera") and ip and token:
            try:
                import dirigera  # type: ignore

                hub = dirigera.Hub(token=token, ip_address=ip)
                try:
                    lgt = hub.get_light_by_id(entity_id)
                    lgt.set_light(lamp_on=is_on)
                    if is_on and brightness is not None:
                        lgt.set_light_level(light_level=max(1, min(100, int(brightness))))
                except Exception:
                    out = hub.get_outlet_by_id(entity_id)
                    out.set_on(outlet_on=is_on)
                return {"ok": True, "speech": f"{dev['name']} {'açıldı' if is_on else 'kapatıldı'}."}
            except Exception as e:
                return {"ok": False, "speech": f"{dev['name']} (IKEA) bağlantısında hata: {e}"}

        # 6. Home Assistant Köprüsü
        if proto in ("home_assistant", "ha"):
            domain = "switch" if dev.get("device_type") == "plug" else "light"
            service = "turn_on" if is_on else "turn_off"
            extra = {"brightness_pct": max(1, min(100, int(brightness)))} if (is_on and brightness and domain == "light") else {}
            return self._call_home_assistant(
                dev,
                domain=domain,
                service=service,
                extra_data=extra,
                success_speech=f"{dev['name']} {'açıldı' if is_on else 'kapatıldı'}.",
            )

        return {"ok": False, "speech": f"'{dev['name']}' ({proto}) için yerel bağlantı ayarlarını kontrol etmelisin."}

    def control_climate_or_thermostat(
        self,
        target_temperature: float,
        device_name: str = "termostat",
        hvac_mode: str = "heat",
    ) -> Dict[str, Any]:
        """
        Kombi, akıllı termostat (Tado, Netatmo, Tuya, Danfoss vb.) veya klimanın sıcaklık set değerini
        TEK SEFERLİK ayarlar.
        ÖNEMLİ KURAL: Bir arka plan döngüsü çalıştırmaz; kullanıcı daha sonra termostattan veya telefondan
        dereceyi elle düşürürse sıcaklığı asla geri zorlamaz, tamamen bir seferlik komut olarak çalışır.
        """
        temp = round(float(target_temperature), 1)
        dev, ambiguity = self._resolve_device_or_ask(
            device_name,
            device_types=["climate", "thermostat"],
            generic_words=("termostat", "kombi", "klima", "ısıtma", "sicaklik", "sıcaklık", "ev"),
        )
        if ambiguity:
            return ambiguity

        # Henüz kayıtlı termostat yoksa bile ayarı hafızaya kaydeder ve kullanıcıyı bilgilendirir
        if not dev:
            def _upd_set(s):
                s = s or {}
                s["last_target_temperature"] = temp
                return s
            self.storage.update_section("settings", _upd_set)
            return {
                "ok": False,
                "speech": f"Bağlı termostat bulunmadığı için sıcaklığı değiştiremedim. {temp} derece hedefini tercih olarak kaydettim; cihaza komut gönderilmedi.",
                "target_temperature": temp,
                "one_shot": True,
            }

        proto = dev.get("protocol", "")
        # Home Assistant üzerinden tek seferlik set_temperature komutu
        if proto in ("home_assistant", "ha"):
            res = self._call_home_assistant(
                dev,
                domain="climate",
                service="set_temperature",
                extra_data={"temperature": temp, "hvac_mode": hvac_mode},
                success_speech=f"{dev['name']} hedef sıcaklığı tek seferlik {temp} dereceye ayarlandı.",
            )
            res["one_shot"] = True
            return res

        # Tuya termostat kontrolü
        if proto in ("tuya", "smartlife"):
            try:
                import tinytuya  # type: ignore

                d = tinytuya.OutletDevice(dev.get("entity_id"), dev.get("ip"), dev.get("token"))
                d.set_version(3.3)
                d.set_value(2, int(temp * 10))  # Tuya sıcaklık genelde 10 katı integer olarak gider (21.5 -> 215)
                return {
                    "ok": True,
                    "speech": f"{dev['name']} sıcaklığı tek seferlik {temp} dereceye ayarlandı.",
                    "target_temperature": temp,
                    "one_shot": True,
                }
            except Exception as e:
                return {"ok": False, "speech": f"Tuya termostat bağlantı hatası: {e}"}

        return {
            "ok": False,
            "speech": f"{dev['name']} için {proto} bağlantısı sıcaklık ayarlamayı desteklemiyor; cihaza komut gönderilmedi.",
            "target_temperature": temp,
            "one_shot": True,
        }

    def get_indoor_climate(self, device_name: str = "termostat") -> Dict[str, Any]:
        """
        'Ev kaç derece?' sorusu için evdeki akıllı termostat veya sıcaklık/nem sensöründen
        anlık iç ortam sıcaklığını ve nem oranını okur.
        """
        dev = self._find_device(device_name, fallback_type="climate")
        if not dev:
            last_target = self.storage.get("settings", {}).get("last_target_temperature")
            return {
                "ok": False,
                "speech": "Doğrudan bağlı bir sıcaklık sensörü bulunamadı; güncel ev sıcaklığını ölçemiyorum."+(f" Kaydedilmiş hedef sıcaklık {last_target} derece." if last_target is not None else ''),
                "target_temperature": last_target,
            }

        proto = dev.get("protocol", "")
        if proto in ("home_assistant", "ha"):
            base_url = dev.get("ip", "").rstrip("/")
            token = dev.get("token", "")
            entity_id = dev.get("entity_id", "")
            if not base_url.startswith("http"):
                base_url = f"http://{base_url}:8123"
            try:
                req = urllib.request.Request(
                    f"{base_url}/api/states/{entity_id}",
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                )
                with urllib.request.urlopen(req, timeout=4) as resp:
                    st = json.loads(resp.read().decode("utf-8"))
                attrs = st.get("attributes", {})
                curr_temp = attrs.get("current_temperature", st.get("state"))
                import math
                curr_temp=float(curr_temp)
                if not math.isfinite(curr_temp):raise ValueError('Sensör ölçümü geçersiz.')
                humidity = attrs.get("current_humidity", "")
                hum_str = f", nem oranı yüzde {humidity}" if humidity else ""
                return {
                    "ok": True,
                    "speech": f"{dev['name']} sensörüne göre ev sıcaklığı şu an {curr_temp} derece{hum_str}.",
                    "temperature": curr_temp,
                    "humidity": humidity,
                }
            except Exception:
                pass

        return {"ok": False,"speech": f"{dev['name']} cihazından güncel sıcaklık ölçümü alınamadı."}

    def leave_home_routine(self) -> Dict[str, Any]:
        """
        Alexa Guard / 'Evden Çıkıyorum' Modu:
        - Açık kalan tüm ışıkları ve televizyonları kapatır.
        - Varsa robot süpürgeye temizliği başlatma komutu verir.
        - Bilgisayarı kilitler (Win+L).
        """
        return self._home_routine(False)

    def arrive_home_routine(self) -> Dict[str, Any]:
        """
        'Eve Geldim' Modu:
        - Giriş/Salon ışıklarını açar.
        - Varsa süpürgeyi şarj istasyonuna gönderir.
        - Karşılama ve günlük özet seslendirir.
        """
        return self._home_routine(True)

    def _home_routine(self, arriving):
        results=[]
        devices=self.storage.get('smart_devices',{})
        for dev in devices.values():
            kind=dev.get('device_type');name=dev['name']
            if kind in ('light','plug'):
                results.append(self.control_light_or_plug(name,state='on' if arriving else 'off'))
            elif kind=='tv' and not arriving:
                results.append(self.control_smart_tv('power_off',device_name=name))
            elif kind=='vacuum':
                results.append(self.control_vacuum('dock' if arriving else 'start',device_name=name))
        if not results:return {'ok':False,'speech':'Bu rutin için kayıtlı bir akıllı ev cihazı yok.','actions':[]}
        actions=[r.get('speech','') for r in results if r.get('ok')]
        failures=[r.get('speech','') for r in results if not r.get('ok')]
        speech=('Hoş geldin. ' if arriving else 'Görüşürüz. ')+' '.join(actions+failures)
        return {'ok':not failures,'speech':speech,'actions':actions,'failures':failures}

    def delete_smart_device(self, name: str) -> Dict[str, Any]:
        """Kayıtlı bir akıllı ev cihazını listeden siler."""
        key = name.strip().lower()
        devices: Dict[str, Any] = self.storage.get("smart_devices", {})
        if key in devices:
            removed = devices.pop(key)
            self.storage.set("smart_devices", devices)
            return {"ok": True, "speech": f"'{removed['name']}' cihazı silindi."}
        return {"ok": False, "speech": f"'{name}' adında kayıtlı bir cihaz bulunamadı."}

    def get_rooms(self) -> List[str]:
        """Kayıtlı odaların listesini döndürür."""
        return self.storage.get("rooms", ["Oturma Odası", "Yatak Odası", "Mutfak", "Çalışma Odası"])

    def add_room(self, room_name: str) -> Dict[str, Any]:
        """Yeni bir oda başlığı oluşturur."""
        clean = room_name.strip()
        if not clean:
            return {"ok": False, "speech": "Oda adı boş olamaz."}
        rooms: List[str] = self.get_rooms()
        if clean not in rooms:
            rooms.append(clean)
            self.storage.set("rooms", rooms)
        return {"ok": True, "speech": f"'{clean}' odası eklendi.", "rooms": rooms}

    def delete_room(self, room_name: str) -> Dict[str, Any]:
        """Oda başlığını siler ve o odadaki cihazların odasını boşaltır."""
        clean = room_name.strip()
        rooms: List[str] = self.get_rooms()
        if clean in rooms:
            rooms.remove(clean)
            self.storage.set("rooms", rooms)
        # O odadaki cihazları odaya atanmamış hale getir
        devices: Dict[str, Any] = self.storage.get("smart_devices", {})
        changed = False
        for dev in devices.values():
            if dev.get("room") == clean:
                dev["room"] = ""
                changed = True
        if changed:
            self.storage.set("smart_devices", devices)
        return {"ok": True, "speech": f"'{clean}' odası silindi.", "rooms": rooms}

    def assign_device_to_room(self, device_name_or_key: str, room_name: str) -> Dict[str, Any]:
        """Bir cihazı belirtilen odaya atar veya odadan çıkarır."""
        devices: Dict[str, Any] = self.storage.get("smart_devices", {})
        q = device_name_or_key.strip().lower()
        target = None
        for k, dev in devices.items():
            if q == k or q == dev.get("name", "").lower():
                target = dev
                break
        if not target:
            return {"ok": False, "speech": f"'{device_name_or_key}' cihazı bulunamadı."}
        target["room"] = room_name.strip()
        self.storage.set("smart_devices", devices)
        return {
            "ok": True,
            "speech": f"'{target['name']}' cihazı '{room_name or 'Atanmamış'}' odasına taşındı.",
            "device": target,
        }

    def control_smart_tv(
        self,
        action: str = "power_on",
        device_name: str = "televizyon",
        app_or_channel: str = "",
    ) -> Dict[str, Any]:
        """
        Evdeki Akıllı TV'yi kontrol eder.
        Evde birden fazla Akıllı TV varsa ('Salon TV', 'Yatak Odası TV' vb.) ve kullanıcı hangisi olduğunu
        belirtmediyse, hangisini kontrol etmek istediğini sorar!
        """
        dev, ambiguity = self._resolve_device_or_ask(
            device_name,
            device_types=["tv"],
            generic_words=("televizyon", "tv", "ekran", "televizyonu"),
        )
        if ambiguity:
            return ambiguity
        if not dev:
            return {
                "ok": False,
                "speech": (
                    f"'{device_name}' henüz tanıtılmamış. 'Ağdaki cihazları tara' diyerek televizyonunu bulabilir "
                    "veya 'Salon TV', 'Oda TV' gibi isimlendirerek kaydedebilirsin."
                ),
            }

        act = action.strip().lower()
        ip = dev.get("ip", "")
        mac_or_token = dev.get("token", "")
        proto = dev.get("protocol", "")

        if proto == 'android_tv':
            try:
                act = {'on':'power_on','aç':'power_on','ac':'power_on','wake':'power_on','off':'power_off'}.get(act,act)
                return self._android_tv().control(ip,act)
            except Exception:
                return {'ok':False,'speech':'TV bağlantısı kurulamadı. TV açık ve aynı ağda olmalı; gerekirse Akıllı Ev bölümünden tekrar eşleştir.'}

        if act in ("power_on", "on", "aç", "ac", "wake"):
            wol_sent = False
            if mac_or_token and (":" in mac_or_token or "-" in mac_or_token):
                wol_sent = self._send_wake_on_lan(mac_or_token)
            if proto in ("home_assistant", "ha"):
                return self._call_home_assistant(
                    dev, domain="media_player", service="turn_on", success_speech=f"{dev['name']} açılıyor."
                )
            if wol_sent:
                return {"ok": True, "speech": f"{dev['name']} için ağ üzerinden açılma (Wake-on-LAN) sinyali gönderildi."}
            return {
                "ok": False,
                "speech": f"{dev['name']} için açma komutu gönderilemedi. Ağdan uyandırma için TV'nin MAC adresi veya desteklenen bir köprü gerekli.",
            }

        if proto in ("home_assistant", "ha"):
            ha_map = {
                "power_off": "turn_off",
                "off": "turn_off",
                "mute": "volume_mute",
                "volume_up": "volume_up",
                "volume_down": "volume_down",
            }
            if act == "launch_app" and app_or_channel:
                return self._call_home_assistant(
                    dev,
                    domain="media_player",
                    service="select_source",
                    extra_data={"source": app_or_channel},
                    success_speech=f"{dev['name']} üzerinde {app_or_channel} açılıyor.",
                )
            ha_srv = ha_map.get(act)
            if not ha_srv:return {"ok":False,"speech":"Bu TV komutu desteklenmiyor; işlem uygulanmadı."}
            return self._call_home_assistant(
                dev, domain="media_player", service=ha_srv, extra_data={"is_volume_muted": True} if act=='mute' else None, success_speech=f"{dev['name']} komutu ({act}) uygulandı."
            )

        if act == "launch_app" and ip and app_or_channel:
            app_clean = "YouTube" if "youtube" in app_or_channel.lower() else ("Netflix" if "netflix" in app_or_channel.lower() else app_or_channel)
            if self._dial_launch_app(ip, app_clean, ""):
                return {"ok": True, "speech": f"{dev['name']} ekranında {app_clean} açıldı."}

        return {
            "ok": False,
            "speech": f"{dev['name']} ({ip}) için '{action}' komutu gönderilemedi; TV'nin açık ve aynı Wi-Fi ağında olduğundan emin ol.",
        }

    def cast_youtube_to_tv(
        self,
        video_url_or_query: str,
        device_name: str = "televizyon",
        wake_tv_first: bool = True,
    ) -> Dict[str, Any]:
        """
        Bilgisayarda izlenen bir YouTube videosunu televizyonu açıp doğrudan Akıllı TV'ye aktarır.
        Evde birden fazla Akıllı TV kayıtlıysa ('Salon TV', 'Mutfak TV' vb.) ve hangisi olduğu belirtilmediyse,
        videoyu hangi televizyona aktarmak istediğini sorar!
        """
        dev, ambiguity = self._resolve_device_or_ask(
            device_name,
            device_types=["tv"],
            generic_words=("televizyon", "tv", "ekran", "televizyona"),
        )
        if ambiguity:
            return ambiguity
        if not dev:
            return {
                "ok": False,
                "speech": (
                    f"Videoyu aktaracak kayıtlı bir televizyon ('{device_name}') bulamadım. "
                    "Önce 'Wi-Fi cihazlarını tara' diyerek televizyonunu tanıtmamı ister misin?"
                ),
            }

        ip = dev.get("ip", "")
        mac = dev.get("token", "")
        proto = dev.get("protocol", "")

        if wake_tv_first and mac and (":" in mac or "-" in mac):
            self._send_wake_on_lan(mac)

        video_id = self._resolve_youtube_video_id(video_url_or_query)
        if not video_id:
            return {
                "ok": False,
                "speech": f"'{video_url_or_query}' için geçerli bir YouTube videosu bulamadım.",
            }

        if proto in ("home_assistant", "ha"):
            return self._call_home_assistant(
                dev,
                domain="media_player",
                service="play_media",
                extra_data={
                    "media_content_id": f"https://www.youtube.com/watch?v={video_id}",
                    "media_content_type": "video",
                },
                success_speech=f"YouTube videosu {dev['name']} ekranına aktarıldı.",
            )

        if ip and self._dial_launch_app(ip, "YouTube", f"v={video_id}"):
            return {
                "ok": True,
                "speech": f"{dev['name']} üzerinde YouTube açıldı ve video televizyona aktarıldı!",
                "video_id": video_id,
                "tv_ip": ip,
            }

        return {
            "ok": False,
            "speech": (
                f"{dev['name']} ({ip}) televizyonuna bağlanamadım. TV'nin açık olduğundan ve TV'deki YouTube uygulamasının "
                "aynı Wi-Fi ağında olduğundan emin ol."
            ),
            "video_id": video_id,
        }

    @staticmethod
    def _send_wake_on_lan(mac_address: str) -> bool:
        """TV'yi Wi-Fi/Ağ üzerinden uyandırmak için standart Magic Packet gönderir."""
        try:
            clean_mac = mac_address.replace(":", "").replace("-", "").strip()
            if len(clean_mac) != 12:
                return False
            data = bytes.fromhex("FF" * 6 + clean_mac * 16)
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.sendto(data, ("255.255.255.255", 9))
            sock.close()
            return True
        except Exception:
            return False

    @staticmethod
    def _dial_launch_app(tv_ip: str, app_name: str, payload_body: str = "") -> bool:
        candidate_ports = [8008, 7676, 8001, 56789]
        for port in candidate_ports:
            url = f"http://{tv_ip}:{port}/apps/{app_name}"
            try:
                req = urllib.request.Request(
                    url,
                    data=payload_body.encode("utf-8"),
                    headers={"Content-Type": "text/plain; charset=utf-8"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=2.5) as resp:
                    if resp.status in (200, 201, 204):
                        return True
            except Exception:
                continue
        return False

    @staticmethod
    def _resolve_youtube_video_id(url_or_query: str) -> str:
        import re
        import urllib.parse

        q = url_or_query.strip()
        match = re.search(r"(?:v=|youtu\.be/|embed/|shorts/)([A-Za-z0-9_-]{11})", q)
        if match:
            return match.group(1)
        if re.fullmatch(r"[A-Za-z0-9_-]{11}", q):
            return q

        try:
            search_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(q)}"
            req = urllib.request.Request(search_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=4) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
            vid_match = re.search(r'"videoId":"([A-Za-z0-9_-]{11})"', html)
            if vid_match:
                return vid_match.group(1)
        except Exception:
            pass
        return ""

    def _resolve_device_or_ask(
        self,
        query_name: str,
        device_types: List[str],
        generic_words: tuple,
    ) -> tuple[Dict[str, Any] | None, Dict[str, Any] | None]:
        """
        1. Kullanıcının söylediği özel isim ('Başucu Lambası', 'Salon TV') veya alias/oda ile tam eşleşen cihaz varsa onu döndürür.
        2. Kullanıcı genel bir ifade kullandıysa ('televizyon', 'ışık') ve o kategoride:
           - Sadece 1 cihaz kayıtlıysa doğrudan onu döndürür.
           - Birden fazla cihaz kayıtlıysa (örn: hem 'Salon TV' hem 'Yatak Odası TV'), hangisini istediğini soran ambiguity yanıtı döndürür!
        """
        devices: Dict[str, Any] = self.storage.get("smart_devices", {})
        q = query_name.strip().lower()

        # 1. Doğrudan anahtar eşleşmesi
        if q in devices:
            return devices[q], None

        # 2. Özel isim, takma ad (alias) veya oda adı ile eşleşme (genel kelimeler hariç)
        if q not in generic_words:
            exact_matches = []
            for k, dev in devices.items():
                aliases = [a.lower() for a in dev.get("aliases", [])]
                room = dev.get("room", "").lower()
                if q in k or k in q or any(q in a or a in q for a in aliases) or (room and q in room):
                    exact_matches.append(dev)
            if len(exact_matches) == 1:
                return exact_matches[0], None
            if len(exact_matches) > 1:
                names = [d["name"] for d in exact_matches]
                return None, {
                    "ok": False,
                    "needs_clarification": True,
                    "candidates": names,
                    "speech": f"'{query_name}' ile eşleşen birden fazla cihaz var: {', '.join(names)}. Hangisini kastettin?",
                }

        # 3. Kategori bazlı adaylar (Örn: tüm TV'ler veya tüm ışıklar)
        candidates = [d for d in devices.values() if d.get("device_type") in device_types]
        if len(candidates) == 1:
            return candidates[0], None
        if len(candidates) > 1:
            # Varsayılan olarak atanmış bir cihaz var mı kontrol et
            settings = self.storage.get("settings", {})
            default_key = f"default_{device_types[0]}"
            default_dev_name = settings.get(default_key, "").lower()
            if default_dev_name and default_dev_name in devices:
                return devices[default_dev_name], None

            names = [d["name"] for d in candidates]
            return None, {
                "ok": False,
                "needs_clarification": True,
                "candidates": names,
                "speech": (
                    f"Evde birden fazla {query_name} kayıtlı: {', '.join(names)}. "
                    f"Hangisini kullanmamı istersin?"
                ),
            }

        return None, None

    @staticmethod
    def _send_yeelight_tcp(ip: str, payload: Dict[str, Any]) -> None:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3.0)
        s.connect((ip, 55443))
        msg = (json.dumps(payload) + "\r\n").encode("utf-8")
        s.sendall(msg)
        s.close()

    @staticmethod
    def _call_home_assistant(
        dev: Dict[str, Any],
        domain: str,
        service: str,
        extra_data: Dict[str, Any] | None = None,
        success_speech: str = "İşlem tamamlandı.",
    ) -> Dict[str, Any]:
        base_url = dev.get("ip", "").rstrip("/")
        token = dev.get("token", "")
        entity_id = dev.get("entity_id", "")
        if not base_url.startswith("http"):
            base_url = f"http://{base_url}:8123"

        url = f"{base_url}/api/services/{domain}/{service}"
        body = {"entity_id": entity_id}
        if extra_data:
            body.update(extra_data)

        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(body).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5):
                return {"ok": True, "speech": success_speech}
        except Exception as e:
            return {"ok": False, "speech": f"Home Assistant bağlantısı başarısız oldu: {e}"}
