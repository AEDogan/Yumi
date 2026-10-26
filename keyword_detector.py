"""Small local name-only recognizer. No network, transcription persistence or TTS."""
import importlib,platform,struct,json,unicodedata
def prepare_vosk():
    system,architecture=platform.system,platform.architecture
    platform.system=lambda:'Windows';platform.architecture=lambda *args,**kwargs:(str(struct.calcsize('P')*8)+'bit','WindowsPE')
    try:return importlib.import_module('vosk')
    finally:platform.system,platform.architecture=system,architecture
def aliases(name):
    from wake_names import aliases as pronunciations
    return pronunciations(name)
class KeywordDetector:
    def __init__(self,path,name):
        from pathlib import Path
        from wake_names import ENGLISH_NAMES,normalized
        path=Path(path);english=path.parent/'wake-vosk-en'
        self.language='en' if normalized(name) in ENGLISH_NAMES and english.is_dir() else 'tr'
        selected=english if self.language=='en' else path
        vosk=prepare_vosk();vosk.SetLogLevel(-1);self.model=vosk.Model(str(selected));self.name=name
        self.phrases=[phrase for phrase in aliases(name) if phrase and all(self.model.vosk_model_find_word(word)>=0 for word in phrase.split())]
        # Register one spelling for an acoustically identical name. Listing
        # cat/katt or eddy/eddie together splits one recognition posterior into
        # two .5 alternatives and falsely fails the confidence check.
        canonical=normalized(name)
        if self.language=='en' and canonical in self.phrases:self.phrases=[canonical]
        if not self.phrases:raise ValueError('unsupported_name')
        grammar=list(self.phrases)
        if self.language=='en':
            # Other character names are acoustic negatives, never wake names.
            # Otherwise a grammar containing only Mira can force Clara/Lyra
            # into Mira with misleadingly high confidence.
            for other in sorted(ENGLISH_NAMES-{'kai'}):
                variants=aliases(other)
                supported=[p for p in variants if all(self.model.vosk_model_find_word(w)>=0 for w in p.split())]
                if other in supported:supported=[other]
                grammar.extend(supported)
        grammar=list(dict.fromkeys(grammar))
        self.recognizer=vosk.KaldiRecognizer(self.model,16000,json.dumps(grammar+['[unk]'],ensure_ascii=False));self.recognizer.SetWords(True);self.recognizer.SetPartialWords(True);self.finalized=False;self.stable=0
    def matches(self,result,voiced_seconds):
        if voiced_seconds<.12:return False
        from voice_profiles import wake_command
        if not wake_command(result.get('text',''),self.name)[0]:return False
        words=result.get('result',[])
        # Fixed vocabulary includes [unk]; require actual supported name words with confidence.
        for phrase in self.phrases:
            tokens=phrase.split()
            for start in range(len(words)-len(tokens)+1):
                span=words[start:start+len(tokens)]
                if [w.get('word') for w in span]==tokens and all(w.get('conf',0)>=.8 for w in span):return True
        return False
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
