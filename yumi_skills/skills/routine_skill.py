from typing import Any, Callable, Dict, List

from ..storage import SkillStorage


class RoutineSkill:
    """
    Alexa 'Routines' (Rutinler) motoru:
    Tek bir sesli komutla ('Yumi, çalışma modunu aç' veya 'Yumi, günaydın') birden fazla beceriyi zincirleme çalıştırır.
    """

    def __init__(self, storage: SkillStorage, executor_fn: Callable[[str, Dict[str, Any]], Dict[str, Any]]):
        self.storage = storage
        self.executor_fn = executor_fn

    def run_routine(self, routine_name: str) -> Dict[str, Any]:
        """Kayıtlı bir Alexa rutinini (örn: 'çalışma modu', 'günaydın') tetikler ve tüm adımlarını sırayla çalıştırır."""
        key = routine_name.strip().lower()
        routines = self.storage.get("routines", {})

        matched_steps = routines.get(key)
        if not matched_steps:
            for r_name, steps in routines.items():
                if key in r_name or r_name in key:
                    matched_steps = steps
                    key = r_name
                    break

        if not matched_steps:
            available = ", ".join(routines.keys())
            return {
                "ok": False,
                "speech": f"'{routine_name}' adında bir rutin bulamadım. Mevcut rutinler: {available}.",
            }

        speeches: List[str] = [f"'{key.capitalize()}' rutini başlatılıyor."]
        step_results = []
        for step in matched_steps:
            skill_name = step.get("skill")
            args = step.get("args", {})
            if skill_name:
                res = self.executor_fn(skill_name, args)
                step_results.append(res)
                if res.get("speech"):
                    speeches.append(res["speech"])

        return {
            "ok": bool(step_results) and all(result.get('ok') for result in step_results),
            "speech": " ".join(speeches),
            "routine": key,
            "results": step_results,
        }

    def save_routine(self, routine_name: str, steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Yeni bir zincirleme rutin kaydeder."""
        key = routine_name.strip().lower()
        routines = self.storage.get("routines", {})
        routines[key] = steps
        self.storage.set("routines", routines)
        return {
            "ok": True,
            "speech": f"'{routine_name}' rutini {len(steps)} adımla kaydedildi.",
        }
