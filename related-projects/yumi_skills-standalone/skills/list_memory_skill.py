import datetime
from typing import Any, Dict

from ..storage import SkillStorage


class ListMemorySkill:
    """
    Alexa'nın Alışveriş Listesi, Yapılacaklar (To-Do) Listesi, Sesli Notlar
    ve 'Bunu Unutma' (Remember This) Kişisel Hafıza becerileri.
    """

    def __init__(self, storage: SkillStorage):
        self.storage = storage

    def add_to_list(self, item: str, list_name: str = "alışveriş") -> Dict[str, Any]:
        """Belirtilen listeye ('alışveriş' veya 'yapılacaklar' vb.) yeni bir öğe ekler."""
        key = list_name.strip().lower()
        clean_item = item.strip()
        if not clean_item:
            return {"ok": False, "speech": "Listeye eklenecek öğeyi anlayamadım."}

        def _updater(lists_dict):
            lists_dict = lists_dict or {}
            items = lists_dict.get(key, [])
            if clean_item not in items:
                items.append(clean_item)
            lists_dict[key] = items
            return lists_dict

        updated = self.storage.update_section("lists", _updater)
        return {
            "ok": True,
            "speech": f"'{clean_item}' öğesini {key} listene ekledim.",
            "list_name": key,
            "items": updated.get(key, []),
        }

    def remove_from_list(self, item: str, list_name: str = "alışveriş") -> Dict[str, Any]:
        """Belirtilen listeden bir öğeyi çıkarır veya listeyi temizler ('hepsi' denirse)."""
        key = list_name.strip().lower()
        target = item.strip().lower()
        lists_dict = self.storage.get("lists", {})
        items = lists_dict.get(key, [])

        if not items:
            return {"ok": True, "speech": f"{key.capitalize()} listen zaten boş."}

        if target in ("hepsi", "tümü", "all", "temizle"):
            lists_dict[key] = []
            self.storage.set("lists", lists_dict)
            return {"ok": True, "speech": f"{key.capitalize()} listendeki tüm öğeleri temizledim."}

        new_items = [i for i in items if target not in i.lower()]
        if len(new_items) == len(items):
            return {"ok": False, "speech": f"{key.capitalize()} listende '{item}' bulamadım."}

        lists_dict[key] = new_items
        self.storage.set("lists", lists_dict)
        return {"ok": True, "speech": f"'{item}' öğesini {key} listenden çıkardım.", "items": new_items}

    def get_list(self, list_name: str = "alışveriş") -> Dict[str, Any]:
        """Belirtilen listedeki tüm öğeleri sesli okur."""
        key = list_name.strip().lower()
        items = self.storage.get("lists", {}).get(key, [])
        if not items:
            return {"ok": True, "speech": f"{key.capitalize()} listen şu anda boş.", "items": []}

        joined = ", ".join(items)
        return {
            "ok": True,
            "speech": f"{key.capitalize()} listende {len(items)} öğe var: {joined}.",
            "items": items,
        }

    def remember_fact(self, subject: str, value: str) -> Dict[str, Any]:
        """
        Kullanıcının 'Yumi, yedek anahtarı mavi çekmeceye koyduğumu unutma' gibi kişisel hafıza kayıtlarını saklar.
        """
        key = subject.strip().lower()
        memories = self.storage.get("memories", {})
        memories[key] = {
            "subject": subject.strip(),
            "value": value.strip(),
            "updated_at": datetime.datetime.now().isoformat(),
        }
        self.storage.set("memories", memories)
        return {
            "ok": True,
            "speech": f"Tamam, '{subject}' bilgisini '{value}' olarak hafızama kaydettim, unutmayacağım.",
        }

    def recall_fact(self, query: str) -> Dict[str, Any]:
        """
        Daha önce kaydedilmiş kişisel hafıza bilgisini ('Yedek anahtar nerede?', 'Wi-Fi şifrem neydi?') geri getirir.
        """
        q = query.strip().lower()
        memories = self.storage.get("memories", {})
        if not memories:
            return {"ok": False, "speech": "Hafızamda henüz kayıtlı özel bir not bulunmuyor."}

        matches = []
        for k, rec in memories.items():
            if q in k or k in q or q in rec.get("value", "").lower():
                matches.append(rec)

        if not matches:
            return {"ok": False, "speech": f"Hafızamda '{query}' ile ilgili bir kayıt bulamadım."}

        parts = [f"{m['subject']}: {m['value']}" for m in matches]
        return {"ok": True, "speech": "Hatırladığım bilgi şöyle: " + "; ".join(parts) + ".", "matches": matches}

    def save_quick_note(self, content: str) -> Dict[str, Any]:
        """Hızlı sesli not kaydeder."""
        note = {
            "id": f"note_{int(datetime.datetime.now().timestamp() * 1000)}",
            "content": content.strip(),
            "created_at": datetime.datetime.now().isoformat(),
        }

        def _add(notes):
            notes = notes or []
            notes.append(note)
            return notes

        self.storage.update_section("notes", _add)
        return {"ok": True, "speech": "Notunu kaydettim.", "note": note}

    def save_detailed_voice_note(self, content: str, title: str = "", category: str = "Genel") -> Dict[str, Any]:
        """
        Sesli notu hem JSON veritabanına kaydeder hem de kullanıcının bilgisayarındaki
        'Belgelerim\\Yumi_Notlari\\' klasörüne kalıcı .txt ve .md (Markdown) dosyası olarak yazar.
        Böylece kullanıcı Not Defteri, Word veya Notion ile notlarına her an erişebilir!
        """
        import os
        import uuid
        from pathlib import Path

        now = datetime.datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M")
        clean_title = title.strip() or f"Sesli_Not_{now.strftime('%H%M%S')}"

        # Belgelerim / Yumi_Notlari klasör yolu
        user_docs = Path(os.environ.get("USERPROFILE", os.path.expanduser("~"))) / "Documents" / "Yumi_Notlari"

        # 1. Müstakil Markdown dosyası
        import re
        safe_title=re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_',clean_title).strip(' .')[:100] or 'Not'
        note_id=uuid.uuid4().hex
        file_name = f"{now.strftime('%Y-%m-%d_%H%M%S_%f')}_{safe_title.replace(' ', '_')}_{note_id[:12]}.md"
        target_file = user_docs / file_name

        md_content = (
            f"# {clean_title}\n\n"
            f"- **Tarih:** {date_str} {time_str}\n"
            f"- **Kategori:** {category}\n\n"
            f"## Not İçeriği\n{content.strip()}\n"
        )
        file_saved=False
        try:
            user_docs.mkdir(parents=True, exist_ok=True)
            with open(target_file, "x", encoding="utf-8") as f:
                f.write(md_content)
            file_saved=True
        except OSError:
            pass

        # 2. Günlük toplu günce dosyası (gunluk_notlar_2026-10-16.txt)
        daily_log = user_docs / f"gunluk_notlar_{date_str}.txt"
        try:
            with open(daily_log, "a", encoding="utf-8") as f:
                f.write(f"\n[{time_str}] [{category}] {clean_title}: {content.strip()}\n")
        except OSError:
            pass

        # 3. Yumi veritabanına indeksle
        note_record = {
            "id": f"vnote_{note_id}",
            "title": clean_title,
            "content": content.strip(),
            "category": category,
            "created_at": now.isoformat(),
            "file_path": str(target_file) if file_saved else None,
        }

        def _add_note(notes):
            notes = notes or []
            notes.append(note_record)
            return notes

        self.storage.update_section("notes", _add_note)

        speech = (f"'{clean_title}' başlıklı notunu kaydettim ve Belgelerim/Yumi Notları klasörüne yazdım." if file_saved
                  else f"'{clean_title}' başlıklı notunu uygulama içinde kaydettim; Belgelerim klasörüne dosya yazılamadı.")
        return {
            "ok": True,
            "speech": speech,
            "note": note_record,
            "saved_path": str(target_file) if file_saved else None,
            "file_saved": file_saved,
        }

    def read_voice_notes(self, query: str = "") -> Dict[str, Any]:
        """Kayıtlı sesli notları listeler ve Yumi'nin okuması için özetler."""
        notes = self.storage.get("notes", [])
        if not notes:
            return {"ok": True, "speech": "Kayıtlı hiçbir sesli notunuz bulunmuyor.", "notes": []}

        q = query.strip().lower()
        if q:
            filtered = [n for n in notes if q in n.get("content", "").lower() or q in n.get("title", "").lower() or q in n.get("category", "").lower()]
        else:
            filtered = notes[-5:]  # Son 5 not

        if not filtered:
            return {"ok": False, "speech": f"'{query}' ile ilgili bir not bulamadım."}

        parts = []
        for n in filtered:
            title = n.get("title") or n.get("content", "")[:30]
            parts.append(f"{title}: {n.get('content')}")

        speech = f"Toplam {len(filtered)} not buldum: " + ". ".join(parts) + "."
        return {"ok": True, "speech": speech, "notes": filtered}

    def save_user_preference_or_rule(self, rule_text: str, setting_key: str = "", setting_value: str = "") -> Dict[str, Any]:
        """
        Kullanıcının 'her zaman Outlook takvimimi kullan', 'müzikleri hep Spotify'dan aç',
        'hava durumunu hep Ankara için söyle' gibi kalıcı tercihlerini ve özel beceri kurallarını kaydeder.
        """
        clean_rule = rule_text.strip()
        sk = setting_key.strip().lower()
        sv = setting_value.strip()

        # Bilinen sistem ayarlarını otomatik güncelle
        if sk in ("calendar_provider", "default_city", "music_platform") and sv:
            def _upd_settings(s):
                s = s or {}
                s[sk] = sv
                return s
            self.storage.update_section("settings", _upd_settings)

        # Ayrıca doğal dil kuralı olarak da sakla ki Gemini her oturumda sistem promptunda görsün
        def _upd_rules(rules):
            rules = rules or []
            if clean_rule and clean_rule not in rules:
                rules.append(clean_rule)
            return rules

        all_rules = self.storage.update_section("user_rules", _upd_rules)
        return {
            "ok": True,
            "speech": f"Anlaşıldı, '{clean_rule}' tercihini kalıcı beceri kuralı olarak kaydettim. Bundan sonra hep buna göre hareket edeceğim.",
            "rules": all_rules,
        }

    def remove_user_rule(self, keyword: str) -> Dict[str, Any]:
        """Kayıtlı bir kalıcı kullanıcı kuralını/tercihini siler."""
        kw = keyword.strip().lower()
        rules = self.storage.get("user_rules", [])
        remaining = [r for r in rules if kw not in r.lower()]
        self.storage.set("user_rules", remaining)
        return {
            "ok": True,
            "speech": f"'{keyword}' ile ilgili kalıcı kuralı kaldırdım.",
            "rules": remaining,
        }

