"""Small local name-only recognizer. No network, transcription persistence or TTS."""
import importlib,platform,struct,json,unicodedata
def prepare_vosk():
    system,architecture=platform.system,platform.architecture
    platform.system=lambda:'Windows';platform.architecture=lambda *args,**kwargs:(str(struct.calcsize('P')*8)+'bit','WindowsPE')
    try:return importlib.import_module('vosk')
    finally:platform.system,platform.architecture=system,architecture
def aliases(name):
    lowered=name.strip().replace('I','ı').replace('İ','i').lower()
    normalized=''.join(c for c in unicodedata.normalize('NFKD',lowered.replace('ı','i')) if not unicodedata.combining(c))
    extras={'clara':('klara','cılara','ciılara'),'david':('davit','deyvid')}.get(normalized,())
    return tuple(dict.fromkeys((lowered,normalized,*extras)))
class KeywordDetector:
    def __init__(self,path,name):
        vosk=prepare_vosk();vosk.SetLogLevel(-1);self.model=vosk.Model(str(path));self.name=name
        self.phrases=[phrase for phrase in aliases(name) if phrase and all(self.model.vosk_model_find_word(word)>=0 for word in phrase.split())]
        if not self.phrases:raise ValueError('unsupported_name')
        self.recognizer=vosk.KaldiRecognizer(self.model,16000,json.dumps(self.phrases+['[unk]'],ensure_ascii=False));self.recognizer.SetWords(True);self.recognizer.SetPartialWords(True);self.finalized=False;self.stable=0
    def matches(self,result,voiced_seconds):
        if voiced_seconds<.12:return False
        from voice_profiles import wake_command
        if not wake_command(result.get('text',''),self.name)[0]:return False
        words=result.get('result',[])
        # Fixed vocabulary includes [unk]; require actual supported name words with confidence.
        return any(word.get('word') in ' '.join(self.phrases).split() and word.get('conf',0)>=.8 for word in words)
    def accept(self,pcm,voiced_seconds):
        self.finalized=bool(self.recognizer.AcceptWaveform(pcm))
        if self.finalized:
            self.stable=0;return self.matches(json.loads(self.recognizer.Result()),voiced_seconds)
        partial=json.loads(self.recognizer.PartialResult())
        candidate={'text':partial.get('partial',''),'result':partial.get('partial_result',[])}
        self.stable=self.stable+1 if self.matches(candidate,voiced_seconds) else 0
        # Three consecutive 40ms blocks with confident word-level evidence;
        # don't wait for a long end-of-utterance silence to recognize the name.
        return self.stable>=3
