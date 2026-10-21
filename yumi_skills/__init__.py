from .engine import YumiSkillEngine
from .storage import SkillStorage


def get_smart_home_panel(engine: YumiSkillEngine | None = None, parent=None):
    """Yumi PySide6 arayüzüne doğrudan gömülebilecek Akıllı Ev & Cihaz Köprüleri ekranını döndürür."""
    from .ui_smart_home_panel import SmartHomePanelWidget

    return SmartHomePanelWidget(engine=engine, parent=parent)


__all__ = ["YumiSkillEngine", "SkillStorage", "get_smart_home_panel"]
