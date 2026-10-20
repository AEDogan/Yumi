"""Read-only Open-Meteo weather for the native voice session."""
import threading
import requests

DECLARATION={'name':'get_weather','description':'Gerçek güncel hava durumu veya bugün/yarın tahmini. Şehir için kullanıcının söylediği veya ayarlardaki şehri kullan.','parameters':{'type':'OBJECT','properties':{'city':{'type':'STRING','description':'Şehir adı, varsa ülke ile'},'when':{'type':'STRING','enum':['now','today','tomorrow']}},'required':['city']}}
REQUESTS=threading.BoundedSemaphore(2)

def get_weather(city,when='now',http=requests):
    if not isinstance(city,str) or not city.strip() or len(city)>160:return {'error':'city_required','message':'Hangi şehir olduğunu sor.'}
    if when not in ('now','today','tomorrow'):return {'error':'unsupported_date','message':'Yalnız şimdi, bugün veya yarın destekleniyor.'}
    if not REQUESTS.acquire(blocking=False):return {'error':'weather_busy','message':'Önceki hava durumu sorgusu sürüyor; biraz sonra tekrar dene.'}
    try:
        geo=http.get('https://geocoding-api.open-meteo.com/v1/search',params={'name':city.strip(),'count':1,'language':'tr','format':'json'},timeout=(3,5))
        geo.raise_for_status();places=geo.json().get('results',[])
        if not places:return {'error':'city_not_found','message':'Şehir bulunamadı; şehir ve ülkeyi netleştir.'}
        place=places[0]
        response=http.get('https://api.open-meteo.com/v1/forecast',params={'latitude':place['latitude'],'longitude':place['longitude'],'current':'temperature_2m,apparent_temperature,weather_code,wind_speed_10m,is_day','daily':'weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,sunrise,sunset','timezone':'auto','forecast_days':2},timeout=(3,5))
        response.raise_for_status();data=response.json();daily=data['daily'];i=1 if when=='tomorrow' else 0
        result={'source':'Open-Meteo','city':place['name'],'country':place.get('country',''),'region':place.get('admin1',''),'timezone':data['timezone'],'date':daily['time'][i],'forecast':{key:daily[key][i] for key in ('weather_code','temperature_2m_max','temperature_2m_min','precipitation_probability_max')},'units':data.get('daily_units',{}),'weather_code_standard':'WMO: 0 açık; 1–3 bulutlu; 45/48 sis; 51–67 çisenti/yağmur; 71–77 kar; 80–82 sağanak; 85/86 kar sağanağı; 95–99 gök gürültülü fırtına.'}
        if when=='now':result.update(current=data['current'],current_units=data.get('current_units',{}))
        if daily.get('sunrise') and daily.get('sunset'):
            result['solar']={'sunrise':daily['sunrise'][i],'sunset':daily['sunset'][i],'utc_offset_seconds':data.get('utc_offset_seconds',0)}
        return result
    except (requests.RequestException,ValueError,KeyError,TypeError,IndexError):
        return {'error':'weather_unavailable','message':'Hava durumu servisine şu an ulaşılamadı. Tahmin uydurma; tekrar denenebileceğini söyle.'}
    finally:REQUESTS.release()
