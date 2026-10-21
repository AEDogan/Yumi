import datetime
import json
import os
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path
from typing import Any, Dict, List

from ..storage import SkillStorage


class CalendarSkill:
    """
    Gmail (Google Calendar API OAuth2) ve Outlook (Masaüstü MAPI/COM + Microsoft Graph API + Web/ICS fallback)
    üzerinden randevu/etkinlik oluşturma, listeleme ve çakışma kontrolü becerisi.
    """

    def __init__(self, storage: SkillStorage):
        self.storage = storage
        self.tokens_dir: Path = storage.tokens_dir
        self.google_creds_file = self.tokens_dir / "google_credentials.json"
        self.google_token_file = self.tokens_dir / "google_token.json"
        self.outlook_token_file = self.tokens_dir / "outlook_token.json"

    def get_connected_providers(self) -> List[str]:
        """Şu anda aktif/bağlı olan takvim sağlayıcılarını ('google', 'outlook') tespit eder."""
        connected: List[str] = []
        if self.google_token_file.exists() or self.google_creds_file.exists():
            connected.append("google")
        if self.outlook_token_file.exists() or self._is_outlook_desktop_available():
            connected.append("outlook")
        return connected

    def _is_outlook_desktop_available(self) -> bool:
        try:
            import win32com.client  # pywin32

            win32com.client.GetActiveObject("Outlook.Application")
            return True
        except Exception:
            return False

    def set_default_provider(self, provider: str) -> Dict[str, Any]:
        """
        Kullanıcının varsayılan takvim tercihini ('google', 'outlook', 'both', 'ask') kalıcı olarak kaydeder.
        Örn: 'Her zaman Outlook takvimimi kullan' dendiğinde çağrılır.
        """
        p = provider.strip().lower()
        alias = {
            "gmail": "google",
            "google": "google",
            "google calendar": "google",
            "google takvim": "google",
            "outlook": "outlook",
            "microsoft": "outlook",
            "hotmail": "outlook",
            "ikisi de": "both",
            "her ikisi": "both",
            "both": "both",
            "sor": "ask",
            "ask": "ask",
            "auto": "ask",
        }
        normalized = alias.get(p, "ask")

        def _upd(settings):
            settings = settings or {}
            settings["calendar_provider"] = normalized
            return settings

        self.storage.update_section("settings", _upd)

        labels = {
            "google": "Google Takvim (Gmail)",
            "outlook": "Microsoft Outlook Takvimi",
            "both": "hem Google hem Outlook takvimi",
            "ask": "her seferinde sana soracak şekilde",
        }
        return {
            "ok": True,
            "speech": f"Tamam, bundan sonra varsayılan takvim tercihini {labels[normalized]} olarak kaydettim. Tekrar söylemene gerek kalmayacak.",
            "default_provider": normalized,
        }

    def create_event(
        self,
        title: str,
        start_time_iso: str,
        end_time_iso: str | None = None,
        description: str = "",
        location: str = "",
        provider: str = "auto",
        open_web_confirm: bool = False,
    ) -> Dict[str, Any]:
        """
        Belirtilen tarih ve saatte Gmail (Google Calendar) veya Outlook takvimine randevu/etkinlik ekler.
        Hem Google hem Outlook bağlıysa ve kullanıcı bir tercih belirtmediyse (veya kalıcı varsayılan seçmediyse),
        çakışma olmaması için hangi takvime eklemek istediğini sorar.
        """
        try:
            start_dt = datetime.datetime.fromisoformat(start_time_iso)
        except ValueError:
            return {
                "ok": False,
                "speech": f"Tarih formatını anlayamadım ({start_time_iso}). Lütfen gün ve saati tekrar söyler misin?",
            }

        if end_time_iso:
            try:
                end_dt = datetime.datetime.fromisoformat(end_time_iso)
            except ValueError:
                end_dt = start_dt + datetime.timedelta(hours=1)
        else:
            end_dt = start_dt + datetime.timedelta(hours=1)

        req_provider = provider.strip().lower()
        saved_pref = self.storage.get("settings", {}).get("calendar_provider", "ask")
        connected = self.get_connected_providers()

        # Kullanıcı bu cümlede açıkça 'google'/'gmail' veya 'outlook' demediyse:
        if req_provider in ("auto", "ask", ""):
            if saved_pref in ("google", "outlook", "both"):
                req_provider = saved_pref
            elif len(connected) > 1:
                # Hem Google hem Outlook bağlı ve kalıcı tercih henüz seçilmemiş -> Çakışmayı önle, kullanıcıya sor!
                return {
                    "ok": False,
                    "needs_clarification": True,
                    "available_providers": connected,
                    "pending_event": {
                        "title": title,
                        "start_time_iso": start_dt.isoformat(),
                        "end_time_iso": end_dt.isoformat(),
                        "description": description,
                        "location": location,
                    },
                    "speech": (
                        f"Hem Google (Gmail) hem de Outlook takvimin bağlı görünüyor. "
                        f"'{title}' randevusunu Google Takvim'e mi yoksa Outlook takvimine mi ekleyeyim? "
                        f"(İstersen 'her zaman Outlook kullan' veya 'her zaman Google kullan' diyerek bunu kalıcı yapabilirsin.)"
                    ),
                }
            elif len(connected) == 1:
                req_provider = connected[0]
            else:
                req_provider = "local"

        results_log: List[str] = []
        synced_providers: List[str] = []

        # 1. Google Calendar (Gmail) Denemesi
        if req_provider in ("google", "gmail", "both"):
            g_res = self._create_google_event(title, start_dt, end_dt, description, location)
            if g_res.get("ok"):
                synced_providers.append("Google Takvim (Gmail)")
            else:
                results_log.append(g_res.get("reason", ""))
                if open_web_confirm:
                    url = self._build_google_web_url(title, start_dt, end_dt, description, location)
                    webbrowser.open(url)
                    synced_providers.append("Google Takvim (Web Penceresi)")

        # 2. Outlook (Masaüstü COM veya Microsoft Graph) Denemesi
        if req_provider in ("outlook", "microsoft", "both"):
            o_res = self._create_outlook_desktop_event(title, start_dt, end_dt, description, location)
            if o_res.get("ok"):
                synced_providers.append("Microsoft Outlook (Masaüstü)")
            else:
                g_graph_res = self._create_outlook_graph_event(title, start_dt, end_dt, description, location)
                if g_graph_res.get("ok"):
                    synced_providers.append("Outlook (Microsoft 365)")
                else:
                    results_log.append(o_res.get("reason", ""))
                    if open_web_confirm:
                        url = self._build_outlook_web_url(title, start_dt, end_dt, description, location)
                        webbrowser.open(url)
                        synced_providers.append("Outlook (Web Penceresi)")

        synced_label = " ve ".join(synced_providers) if synced_providers else None

        # 3. Yumi yerel takvim veritabanına da kaydet
        event_record = {
            "id": f"evt_{int(datetime.datetime.now().timestamp() * 1000)}",
            "title": title,
            "start": start_dt.isoformat(),
            "end": end_dt.isoformat(),
            "description": description,
            "location": location,
            "provider": synced_label or "Yumi Yerel Takvim",
            "google_web_url": self._build_google_web_url(title, start_dt, end_dt, description, location),
            "outlook_web_url": self._build_outlook_web_url(title, start_dt, end_dt, description, location),
        }

        def _append_evt(evts):
            evts = evts or []
            evts.append(event_record)
            evts.sort(key=lambda x: x["start"])
            return evts

        self.storage.update_section("local_events", _append_evt)

        formatted_date = start_dt.strftime("%d.%m.%Y saat %H:%M")
        target_name = synced_label if synced_label else "Yumi takvimine"
        speech = f"{formatted_date} için '{title}' etkinliğini {target_name} ekledim."

        return {
            "ok": True,
            "speech": speech,
            "event": event_record,
            "synced_provider": synced_label,
            "notes": [r for r in results_log if r],
        }

    def list_events(self, date_iso: str | None = None, days: int = 1, provider: str = "auto") -> Dict[str, Any]:
        """
        Belirli bir gün veya gün aralığındaki (varsayılan: bugün) Gmail, Outlook ve yerel takvim etkinliklerini listeler.
        """
        if date_iso:
            try:
                base_dt = datetime.datetime.fromisoformat(date_iso)
            except ValueError:
                base_dt = datetime.datetime.now()
        else:
            base_dt = datetime.datetime.now()

        start_range = base_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        end_range = start_range + datetime.timedelta(days=max(1, days))

        collected: List[Dict[str, Any]] = []

        # 1. Google Calendar'dan çek
        if provider in ("auto", "google", "gmail"):
            collected.extend(self._list_google_events(start_range, end_range))

        # 2. Outlook Masaüstü veya Graph'tan çek
        if provider in ("auto", "outlook", "microsoft"):
            outlook_evts = self._list_outlook_desktop_events(start_range, end_range)
            if not outlook_evts:
                outlook_evts = self._list_outlook_graph_events(start_range, end_range)
            collected.extend(outlook_evts)

        # 3. Yerel etkinlikleri birleştir (Mükerrer olanları başlık+saat ile filtrele)
        seen_keys = {(e["title"].lower(), e["start"][:16]) for e in collected}
        for loc in self.storage.get("local_events", []):
            try:
                loc_dt = datetime.datetime.fromisoformat(loc["start"])
                if start_range <= loc_dt < end_range:
                    key = (loc["title"].lower(), loc["start"][:16])
                    if key not in seen_keys:
                        collected.append(loc)
                        seen_keys.add(key)
            except Exception:
                continue

        collected.sort(key=lambda x: x["start"])

        if not collected:
            day_label = "bugün" if start_range.date() == datetime.date.today() else start_range.strftime("%d.%m.%Y tarihinde")
            return {
                "ok": True,
                "speech": f"Takviminde {day_label} için planlanmış bir etkinlik görünmüyor.",
                "events": [],
            }

        items_speech = []
        for ev in collected[:6]:
            try:
                t_str = datetime.datetime.fromisoformat(ev["start"]).strftime("%H:%M")
            except Exception:
                t_str = ev["start"]
            items_speech.append(f"saat {t_str} {ev['title']}")

        speech = f"Takviminde {len(collected)} etkinlik var: " + ", ".join(items_speech) + "."
        return {
            "ok": True,
            "speech": speech,
            "events": collected,
        }

    # --- GOOGLE CALENDAR (GMAIL) HELPER METOTLARI ---

    def _get_google_service(self):
        """
        google-api-python-client ve google-auth-oauthlib yüklüyse ve google_credentials.json mevcutsa
        Google Calendar API servisini döndürür.
        """
        if not self.google_creds_file.exists() and not self.google_token_file.exists():
            return None, "Google OAuth kimlik dosyası (google_credentials.json) henüz tanımlanmamış."

        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build

            scopes = ["https://www.googleapis.com/auth/calendar"]
            creds = None
            if self.google_token_file.exists():
                creds = Credentials.from_authorized_user_file(str(self.google_token_file), scopes)
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                elif self.google_creds_file.exists():
                    flow = InstalledAppFlow.from_client_secrets_file(str(self.google_creds_file), scopes)
                    creds = flow.run_local_server(port=0)
                else:
                    return None, "Google token süresi dolmuş ve credentials dosyası yok."
                with open(self.google_token_file, "w", encoding="utf-8") as token:
                    token.write(creds.to_json())

            service = build("calendar", "v3", credentials=creds)
            return service, ""
        except ImportError:
            return None, "Google Calendar kütüphaneleri (google-api-python-client) kurulu değil."
        except Exception as e:
            return None, f"Google Takvim bağlantı hatası: {e}"

    def _create_google_event(
        self,
        title: str,
        start_dt: datetime.datetime,
        end_dt: datetime.datetime,
        description: str,
        location: str,
    ) -> Dict[str, Any]:
        service, err = self._get_google_service()
        if not service:
            return {"ok": False, "reason": err}

        try:
            tz_offset = datetime.datetime.now().astimezone().strftime("%z")
            tz_formatted = f"{tz_offset[:3]}:{tz_offset[3:]}" if len(tz_offset) == 5 else "+03:00"
            body = {
                "summary": title,
                "location": location,
                "description": description,
                "start": {"dateTime": start_dt.strftime(f"%Y-%m-%dT%H:%M:%S{tz_formatted}")},
                "end": {"dateTime": end_dt.strftime(f"%Y-%m-%dT%H:%M:%S{tz_formatted}")},
            }
            created = service.events().insert(calendarId="primary", body=body).execute()
            return {"ok": True, "id": created.get("id"), "htmlLink": created.get("htmlLink")}
        except Exception as e:
            return {"ok": False, "reason": str(e)}

    def _list_google_events(
        self, start_range: datetime.datetime, end_range: datetime.datetime
    ) -> List[Dict[str, Any]]:
        service, _ = self._get_google_service()
        if not service:
            return []
        try:
            time_min = start_range.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
            time_max = end_range.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
            events_result = (
                service.events()
                .list(
                    calendarId="primary",
                    timeMin=time_min,
                    timeMax=time_max,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            results = []
            for item in events_result.get("items", []):
                start_val = item["start"].get("dateTime", item["start"].get("date"))
                end_val = item["end"].get("dateTime", item["end"].get("date"))
                results.append(
                    {
                        "id": item.get("id"),
                        "title": item.get("summary", "(Başlıksız)"),
                        "start": start_val,
                        "end": end_val,
                        "location": item.get("location", ""),
                        "provider": "Google Takvim (Gmail)",
                    }
                )
            return results
        except Exception:
            return []

    # --- OUTLOOK (WINDOWS MAPI/COM & MICROSOFT GRAPH) HELPER METOTLARI ---

    def _create_outlook_desktop_event(
        self,
        title: str,
        start_dt: datetime.datetime,
        end_dt: datetime.datetime,
        description: str,
        location: str,
    ) -> Dict[str, Any]:
        """
        Windows üzerinde yüklü klasik Outlook uygulaması varsa sıfır API ayarıyla doğrudan COM üzerinden ekler.
        """
        try:
            import win32com.client  # pywin32

            outlook = win32com.client.Dispatch("Outlook.Application")
            appt = outlook.CreateItem(1)  # 1 = olAppointmentItem
            appt.Subject = title
            appt.Start = start_dt.strftime("%Y-%m-%d %H:%M")
            duration_mins = max(1, int((end_dt - start_dt).total_seconds() // 60))
            appt.Duration = duration_mins
            if description:
                appt.Body = description
            if location:
                appt.Location = location
            appt.ReminderSet = True
            appt.ReminderMinutesBeforeStart = 15
            appt.Save()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "reason": f"Masaüstü Outlook COM kullanılamadı: {e}"}

    def _list_outlook_desktop_events(
        self, start_range: datetime.datetime, end_range: datetime.datetime
    ) -> List[Dict[str, Any]]:
        try:
            import win32com.client

            outlook = win32com.client.Dispatch("Outlook.Application")
            ns = outlook.GetNamespace("MAPI")
            calendar = ns.GetDefaultFolder(9)  # 9 = olFolderCalendar
            items = calendar.Items
            items.IncludeRecurrences = True
            items.Sort("[Start]")

            restriction = (
                f"[Start] >= '{start_range.strftime('%m/%d/%Y %I:%M %p')}' AND "
                f"[Start] < '{end_range.strftime('%m/%d/%Y %I:%M %p')}'"
            )
            restricted_items = items.Restrict(restriction)
            results = []
            for item in restricted_items:
                try:
                    s_dt = datetime.datetime(
                        item.Start.year, item.Start.month, item.Start.day, item.Start.hour, item.Start.minute
                    )
                    e_dt = datetime.datetime(
                        item.End.year, item.End.month, item.End.day, item.End.hour, item.End.minute
                    )
                    results.append(
                        {
                            "title": item.Subject,
                            "start": s_dt.isoformat(),
                            "end": e_dt.isoformat(),
                            "location": getattr(item, "Location", ""),
                            "provider": "Microsoft Outlook (Masaüstü)",
                        }
                    )
                except Exception:
                    continue
            return results
        except Exception:
            return []

    def _create_outlook_graph_event(
        self,
        title: str,
        start_dt: datetime.datetime,
        end_dt: datetime.datetime,
        description: str,
        location: str,
    ) -> Dict[str, Any]:
        """
        Microsoft Graph API token dosyası (outlook_token.json içinde access_token) varsa bulut Outlook takvimine yazar.
        """
        if not self.outlook_token_file.exists():
            return {"ok": False, "reason": "Outlook Graph token bulunamadı."}
        try:
            with open(self.outlook_token_file, "r", encoding="utf-8") as f:
                token_data = json.load(f)
            access_token = token_data.get("access_token")
            if not access_token:
                return {"ok": False, "reason": "Outlook access_token boş."}

            payload = {
                "subject": title,
                "body": {"contentType": "HTML", "content": description},
                "start": {"dateTime": start_dt.strftime("%Y-%m-%dT%H:%M:%S"), "timeZone": "Europe/Istanbul"},
                "end": {"dateTime": end_dt.strftime("%Y-%m-%dT%H:%M:%S"), "timeZone": "Europe/Istanbul"},
                "location": {"displayName": location},
            }
            req = urllib.request.Request(
                "https://graph.microsoft.com/v1.0/me/events",
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
                return {"ok": True, "id": resp_data.get("id")}
        except Exception as e:
            return {"ok": False, "reason": f"Outlook Graph hatası: {e}"}

    def _list_outlook_graph_events(
        self, start_range: datetime.datetime, end_range: datetime.datetime
    ) -> List[Dict[str, Any]]:
        if not self.outlook_token_file.exists():
            return []
        try:
            with open(self.outlook_token_file, "r", encoding="utf-8") as f:
                token_data = json.load(f)
            access_token = token_data.get("access_token")
            if not access_token:
                return []

            params = urllib.parse.urlencode(
                {
                    "startDateTime": start_range.isoformat(),
                    "endDateTime": end_range.isoformat(),
                    "$select": "subject,start,end,location",
                }
            )
            url = f"https://graph.microsoft.com/v1.0/me/calendarView?{params}"
            req = urllib.request.Request(
                url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Prefer": 'outlook.timezone="Europe/Istanbul"',
                },
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                results = []
                for item in data.get("value", []):
                    results.append(
                        {
                            "id": item.get("id"),
                            "title": item.get("subject", "(Başlıksız)"),
                            "start": item.get("start", {}).get("dateTime", ""),
                            "end": item.get("end", {}).get("dateTime", ""),
                            "location": item.get("location", {}).get("displayName", ""),
                            "provider": "Outlook (Microsoft 365)",
                        }
                    )
                return results
        except Exception:
            return []

    @staticmethod
    def _build_google_web_url(
        title: str,
        start_dt: datetime.datetime,
        end_dt: datetime.datetime,
        description: str,
        location: str,
    ) -> str:
        fmt = "%Y%m%dT%H%M%S"
        dates = f"{start_dt.strftime(fmt)}/{end_dt.strftime(fmt)}"
        params = urllib.parse.urlencode(
            {
                "action": "TEMPLATE",
                "text": title,
                "dates": dates,
                "details": description,
                "location": location,
            }
        )
        return f"https://calendar.google.com/calendar/render?{params}"

    @staticmethod
    def _build_outlook_web_url(
        title: str,
        start_dt: datetime.datetime,
        end_dt: datetime.datetime,
        description: str,
        location: str,
    ) -> str:
        params = urllib.parse.urlencode(
            {
                "path": "/calendar/action/compose",
                "rru": "addevent",
                "subject": title,
                "startdt": start_dt.strftime("%Y-%m-%dT%H:%M:%S"),
                "enddt": end_dt.strftime("%Y-%m-%dT%H:%M:%S"),
                "body": description,
                "location": location,
            }
        )
        return f"https://outlook.live.com/calendar/0/deeplink/compose?{params}"
