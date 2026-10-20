"""One entry per Windows audio endpoint, shared by capture clients."""
def input_devices(sd=None):
    if sd is None:
        from startup_runtime import prepare_audio_runtime
        sd=prepare_audio_runtime()
    devices=sd.query_devices();hosts=sd.query_hostapis()
    inputs=[(i,d) for i,d in enumerate(devices) if d['max_input_channels']>0]
    wasapi=[(i,d) for i,d in inputs if hosts[d['hostapi']]['name']=='Windows WASAPI']
    seen=set();result=[]
    for index,item in wasapi or inputs:
        name=item['name'].strip();key=name.casefold()
        if key in seen or key.startswith(('microsoft sound mapper','primary sound capture')):continue
        seen.add(key);result.append((index,name))
    return result

def resolve_input(name,sd=None):
    if name in (None,'','Otomatik'):return None
    for index,label in input_devices(sd):
        if label==name:return index
    raise ValueError('Seçilen mikrofon bulunamadı. Ses ayarlarından bağlı bir mikrofon seç.')
