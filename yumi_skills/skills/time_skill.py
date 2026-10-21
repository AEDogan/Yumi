import datetime
import threading
import time
from typing import Any, Callable, Dict, List

from ..storage import SkillStorage


class TimeSkill:
    """
    Alexa tarzı Zamanlayıcı (Timer), Alarm, Hatırlatıcı (Reminder) ve Kronometre (Stopwatch) becerileri.
    Arka planda çalışan hafif bir daemon thread ile süresi dolan sayaçları/alarmları Yumi'ye sesli bildirim olarak iletir.
    """

    def __init__(self, storage: SkillStorage, on_alert_callback: Callable[[str, Dict[str, Any]], None] | None = None):
        self.storage = storage
        self.on_alert = on_alert_callback
        self._stopwatch_start: float | None = None
        self._running = True
        self._worker = threading.Thread(target=self._background_loop, daemon=True, name="YumiTimeSkillWorker")
        self._worker.start()

    def stop_worker(self) -> None:
        self._running = False

    def set_timer(self, duration_seconds: int, label: str = "Zamanlayıcı") -> Dict[str, Any]:
        """
        Belirtilen saniye kadar geri sayım sayacı kurar.
        Örn: 'Makarna için 8 dakika sayaç kur' -> duration_seconds=480, label='Makarna'
        """
        if duration_seconds <= 0:
            return {"ok": False, "speech": "Sayaç süresi sıfırdan büyük olmalıdır."}

        now = time.time()
        timer_obj = {
            "id": f"tmr_{int(now * 1000)}",
            "label": label,
            "duration_seconds": duration_seconds,
            "expires_at": now + duration_seconds,
            "created_at": datetime.datetime.now().isoformat(),
        }

        def _add(timers):
            timers = timers or []
            timers.append(timer_obj)
            return timers

        self.storage.update_section("timers", _add)
        human_dur = self._format_duration(duration_seconds)
        return {
            "ok": True,
            "speech": f"{label} için {human_dur} süreli zamanlayıcı başlatıldı.",
            "timer": timer_obj,
        }

    def list_timers(self) -> Dict[str, Any]:
        """Aktif zamanlayıcıları ve kalan sürelerini listeler."""
        now = time.time()
        timers = [t for t in self.storage.get("timers", []) if t.get("expires_at", 0) > now]
        self.storage.set("timers", timers)

        if not timers:
            return {"ok": True, "speech": "Şu anda çalışan aktif bir zamanlayıcı yok.", "timers": []}

        parts = []
        for t in timers:
            rem = int(max(0, t["expires_at"] - now))
            parts.append(f"{t['label']} sayacının bitmesine {self._format_duration(rem)} kaldı")

        return {"ok": True, "speech": ", ".join(parts) + ".", "timers": timers}

    def cancel_timer(self, label: str | None = None) -> Dict[str, Any]:
        """İsme göre veya tüm zamanlayıcıları iptal eder."""
        timers = self.storage.get("timers", [])
        if not timers:
            return {"ok": True, "speech": "İptal edilecek aktif bir zamanlayıcı yok."}

        if not label:
            self.storage.set("timers", [])
            return {"ok": True, "speech": "Tüm zamanlayıcıları iptal ettim."}

        remaining = [t for t in timers if label.lower() not in t.get("label", "").lower()]
        removed_count = len(timers) - len(remaining)
        self.storage.set("timers", remaining)

        if removed_count == 0:
            return {"ok": False, "speech": f"'{label}' adında aktif bir zamanlayıcı bulamadım."}
        return {"ok": True, "speech": f"{label} zamanlayıcısını iptal ettim."}

    def set_alarm(self, alarm_time_hhmm: str, label: str = "Alarm") -> Dict[str, Any]:
        """
        Belirli bir saate (SS:DD, örn: '07:30' veya '18:45') alarm kurar.
        """
        try:
            parts = alarm_time_hhmm.strip().split(":")
            hour, minute = int(parts[0]), int(parts[1])
            now = datetime.datetime.now()
            target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if target <= now:
                target += datetime.timedelta(days=1)
        except Exception:
            return {"ok": False, "speech": f"Alarm saatini anlayamadım ({alarm_time_hhmm}). Lütfen 08:30 gibi belirt."}

        alarm_obj = {
            "id": f"alm_{int(time.time() * 1000)}",
            "label": label,
            "time_hhmm": f"{hour:02d}:{minute:02d}",
            "target_iso": target.isoformat(),
            "active": True,
        }

        def _add(alarms):
            alarms = alarms or []
            alarms.append(alarm_obj)
            return alarms

        self.storage.update_section("alarms", _add)
        return {
            "ok": True,
            "speech": f"Saat {hour:02d}:{minute:02d} için {label} kuruldu.",
            "alarm": alarm_obj,
        }

    def set_reminder(self, text: str, remind_at_iso: str) -> Dict[str, Any]:
        """
        Belirli bir tarih/saat için hatırlatıcı ekler.
        """
        try:
            target = datetime.datetime.fromisoformat(remind_at_iso)
        except ValueError:
            return {"ok": False, "speech": "Hatırlatıcı zamanını anlayamadım."}

        rem_obj = {
            "id": f"rem_{int(time.time() * 1000)}",
            "text": text,
            "target_iso": target.isoformat(),
            "triggered": False,
        }

        def _add(rems):
            rems = rems or []
            rems.append(rem_obj)
            return rems

        self.storage.update_section("reminders", _add)
        formatted = target.strftime("%H:%M")
        return {
            "ok": True,
            "speech": f"Tamam, saat {formatted} olduğunda '{text}' konusunu sana hatırlatacağım.",
            "reminder": rem_obj,
        }

    def stopwatch_control(self, action: str = "start") -> Dict[str, Any]:
        """Kronometreyi başlatır ('start'), durdurur/süreyi okur ('stop' / 'status')."""
        action = action.lower().strip()
        if action == "start":
            self._stopwatch_start = time.time()
            return {"ok": True, "speech": "Kronometre başlatıldı."}
        elif action in ("stop", "reset"):
            if self._stopwatch_start is None:
                return {"ok": False, "speech": "Çalışan bir kronometre yok."}
            elapsed = int(time.time() - self._stopwatch_start)
            self._stopwatch_start = None
            return {"ok": True, "speech": f"Kronometre durduruldu. Geçen süre: {self._format_duration(elapsed)}."}
        else:
            if self._stopwatch_start is None:
                return {"ok": True, "speech": "Kronometre şu an çalışmıyor."}
            elapsed = int(time.time() - self._stopwatch_start)
            return {"ok": True, "speech": f"Kronometrede şu ana kadar {self._format_duration(elapsed)} geçti."}

    def _background_loop(self) -> None:
        while self._running:
            try:
                self._check_expirations()
            except Exception:
                pass
            time.sleep(1.0)

    def _check_expirations(self) -> None:
        now_ts = time.time()
        now_dt = datetime.datetime.now()

        # 1. Zamanlayıcılar
        timers = self.storage.get("timers", [])
        if timers:
            still_running = []
            expired = []
            for t in timers:
                if t.get("expires_at", 0) <= now_ts:
                    expired.append(t)
                else:
                    still_running.append(t)
            if expired:
                self.storage.set("timers", still_running)
                for exp in expired:
                    msg = f"Zamanlayıcı süresi doldu: {exp.get('label', 'Zamanlayıcı')}!"
                    if self.on_alert:
                        self.on_alert(msg, {"type": "timer", "item": exp})

        # 2. Alarmlar
        alarms = self.storage.get("alarms", [])
        if alarms:
            changed = False
            for a in alarms:
                if a.get("active"):
                    try:
                        target_dt = datetime.datetime.fromisoformat(a["target_iso"])
                        if (now_dt.astimezone(target_dt.tzinfo) if target_dt.tzinfo else now_dt) >= target_dt:
                            a["active"] = False
                            changed = True
                            msg = f"Saat {a.get('time_hhmm')} oldu! {a.get('label', 'Alarm')} zamanı!"
                            if self.on_alert:
                                self.on_alert(msg, {"type": "alarm", "item": a})
                    except Exception:
                        continue
            if changed:
                self.storage.set("alarms", alarms)

        # 3. Hatırlatıcılar
        reminders = self.storage.get("reminders", [])
        if reminders:
            changed = False
            for r in reminders:
                if not r.get("triggered"):
                    try:
                        target_dt = datetime.datetime.fromisoformat(r["target_iso"])
                        if (now_dt.astimezone(target_dt.tzinfo) if target_dt.tzinfo else now_dt) >= target_dt:
                            r["triggered"] = True
                            changed = True
                            msg = f"Hatırlatıcı: {r.get('text')}!"
                            if self.on_alert:
                                self.on_alert(msg, {"type": "reminder", "item": r})
                    except Exception:
                        continue
            if changed:
                self.storage.set("reminders", reminders)

    @staticmethod
    def _format_duration(seconds: int) -> str:
        hours, rem = divmod(seconds, 3600)
        minutes, secs = divmod(rem, 60)
        parts = []
        if hours:
            parts.append(f"{hours} saat")
        if minutes:
            parts.append(f"{minutes} dakika")
        if secs or not parts:
            parts.append(f"{secs} saniye")
        return " ".join(parts)
