"""Exact local avatar requests from completed user speech, never assistant text."""
import re
from voice_profiles import wake_command
def command_text(text,name,alias=''):
    text=text.strip()
    for called in (name,alias):
        if not called:continue
        matched,tail=wake_command(text,called)
        if matched and text[:len(text)-len(tail)].strip(' ,:!?.').casefold()==called.casefold():text=tail;break
    text=text.casefold().strip(' ,!?.')
    text=re.sub(r'^(?:lütfen|hadi)\s+','',text)
    text=re.sub(r'\s+lütfen$','',text)
    if text in ('ritme göre dans et','ritimle dans et','müzikle dans et'):return 'müziğe göre dans et'
    match=re.fullmatch(r'(.{1,60}?) karakterine geç',text)
    if match:return 'karakter:'+match.group(1)
    allowed={'sağa git','sola git','buraya gel','dur','yürümeyi durdur','otur','ayağa kalk','kalk','karakteri değiştir','sonraki karakter','müziğe göre dans et','müzik dansını durdur','dans et','dansı durdur','dans etmeyi bırak','hareketi durdur','el salla','merhaba de','büyü','küçül','biraz büyü','biraz küçül','gizlen','saklan','görün','geri gel'}
    allowed.update({'ok işareti yap','okey işareti yap','başparmağını kaldır','başparmakla onayla','elini beline koy','avuçlarını aç','işaret et','omuz silk'})
    allowed.update({'koltuğa otur','biraz dinlen','bilgisayara otur','çalışmaya başla'})
    allowed.update({'direk dansı yap','pole dance yap'})
    allowed.update({'otomatik müzik tepkisini aç','otomatik müzik tepkisini kapat'})
    from daily_scenarios import SCENARIOS
    allowed.update(SCENARIOS);allowed.update({'günlük senaryoları aç','günlük senaryoları kapat','müzik dinle'})
    if text.startswith('müzik türü '):
        from music_analysis import genre_name
        if text=='müzik türü otomatik' or genre_name(text[len('müzik türü '):])!='unknown':return text
    allowed.update({'akıllı ev','akıllı evi aç','akıllı ev menüsü','akıllı ev menüsünü aç','akıllı ev panelini aç','cihazları göster','akıllı cihazlar','odaları göster'})
    if text in allowed:return text
    try:
        from yumi_skills.dispatcher import SkillDispatcher
        if SkillDispatcher.parse(text):return text
    except ImportError:pass
    return None
