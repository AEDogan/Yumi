"""Safe categories without exposing raw provider text, tokens or credentials."""
def classify(code=None,reason=''):
    text=str(reason).casefold()[:4096]
    if code in (429,'RESOURCE_EXHAUSTED') or any(s in text for s in ('resource_exhausted','quota','rate limit','too many requests')):return 'quota'
    if code in (401,403,'UNAUTHENTICATED','PERMISSION_DENIED') or any(s in text for s in ('unauthenticated','permission_denied','permission denied','denied access','invalid api key','api key not valid','unauthorized')):return 'access'
    if code==1009 or 'message too big' in text or 'message too large' in text:return 'message_size'
    if any(s in text for s in ('not implemented','not supported','not enabled','unsupported')):return 'unsupported'
    if 'session' in text and any(s in text for s in ('expired','duration','time limit','ttl')):return 'session_expired'
    if any(s in text for s in ('timed out','timeout','inactivity')) and any(s in text for s in ('input','idle','inactivity')):return 'input_timeout'
    return 'provider_closed'

MESSAGES={
 'quota':'Gemini Live ses kullanım sınırına ulaşıldı. Biraz sonra mikrofonla yeniden deneyebilirsin; yazılı sohbeti kullanmaya devam edebilirsin.',
 'access':'Gemini Live ses erişimi reddedildi. Bu, web hesabıyla girişten ayrı ses bağlantısıdır; yazılı sohbeti kullanmaya devam edebilirsin.',
 'message_size':'Gemini Live isteği ileti boyutu sınırına takıldı. Son istek tekrarlanmadı; mikrofonla yeni bağlantı açabilirsin.',
 'unsupported':'Gemini Live bu oturumdaki bir isteği desteklemediği için ses bağlantısını kapattı. Mikrofonla yeniden bağlanabilirsin; son istek tekrarlanmadı.',
 'session_expired':'Gemini Live ses oturumunun süresi doldu. Mikrofonla yeniden bağlanabilirsin; yazılı sohbetin korunuyor.',
 'input_timeout':'Gemini Live giriş bekleme süresi dolduğu için ses bağlantısını kapattı. Mikrofonla yeniden bağlanabilirsin; sohbetin korunuyor.',
 'provider_closed':'Gemini Live ses bağlantısını kapattı. Kesin neden belirlenemedi; kota dolduğu doğrulanmadı. Mikrofonla yeniden bağlanabilirsin; yazılı sohbetin korunuyor.'}
def message(category):return MESSAGES.get(category,MESSAGES['provider_closed'])
