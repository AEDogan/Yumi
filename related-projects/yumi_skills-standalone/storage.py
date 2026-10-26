import json
import os
import threading
from pathlib import Path
from typing import Any, Dict

class SkillStorage:
    """
    %APPDATA%\\YumiDesktop\\skills_data.json üzerinde thread-safe kalıcı veri yönetimi sağlar.
    """
    def __init__(self, custom_dir: str | None = None):
        if custom_dir:
            self.base_dir = Path(custom_dir)
        else:
            appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
            self.base_dir = Path(appdata) / "YumiDesktop"
        
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.tokens_dir = self.base_dir / "tokens"
        self.tokens_dir.mkdir(parents=True, exist_ok=True)
        self.db_file = self.base_dir / "skills_data.json"
        self._lock = threading.RLock()
        self._data: Dict[str, Any] = self._load()

    def _default_schema(self) -> Dict[str, Any]:
        return {
            "timers": [],
            "alarms": [],
            "reminders": [],
            "lists": {
                "alışveriş": [],
                "yapılacaklar": []
            },
            "notes": [],
            "memories": {},
            "local_events": [],
            "routines": {
                "çalışma modu": [
                    {"skill": "set_timer", "args": {"duration_seconds": 1500, "label": "Pomodoro"}},
                    {"skill": "get_todo_list", "args": {"list_name": "yapılacaklar"}}
                ],
                "günaydın": [
                    {"skill": "daily_briefing", "args": {"city": "Istanbul"}}
                ]
            },
            "settings": {
                "default_city": "Istanbul",
                "calendar_provider": "ask",  # ask, google, outlook, both, local
                "music_platform": "youtube"
            },
            "user_rules": [],
            "smart_devices": {},
            "rooms": ["Oturma Odası", "Yatak Odası", "Mutfak", "Çalışma Odası"]
        }

    def _load(self) -> Dict[str, Any]:
        if not self.db_file.exists():
            data = self._default_schema()
            self._save(data)
            return data
        try:
            with open(self.db_file, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            defaults = self._default_schema()
            for k, v in defaults.items():
                if k not in loaded:
                    loaded[k] = v
            return loaded
        except Exception:
            return self._default_schema()

    def _save(self, data: Dict[str, Any] | None = None) -> None:
        with self._lock:
            target = data if data is not None else self._data
            temp_file = self.db_file.with_suffix(".tmp")
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(target, f, ensure_ascii=False, indent=2)
            temp_file.replace(self.db_file)

    def get(self, section: str, default: Any = None) -> Any:
        with self._lock:
            return self._data.get(section, default)

    def set(self, section: str, value: Any) -> None:
        with self._lock:
            self._data[section] = value
            self._save()

    def update_section(self, section: str, updater_fn) -> Any:
        with self._lock:
            current = self._data.get(section)
            updated = updater_fn(current)
            self._data[section] = updated
            self._save()
            return updated
