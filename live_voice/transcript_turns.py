"""Tag provider transcription deltas for UI only; never retain text or log it."""
class TranscriptTurns:
    def __init__(self,publish,playing,waiting=lambda:False):
        self.publish=publish;self.playing=playing;self.waiting=waiting;self.user_id=0;self.user_active=False;self.assistant_id=0;self.assistant_open=False;self.blocked=False;self.user_interim=False;self.user_closed=False
    def end(self,role,turn,complete):
        if turn:self.publish({'event':'transcript_end','role':role,'turn_id':turn,'complete':complete})
    def begin_assistant(self):
        if not self.assistant_open:
            self.assistant_id+=1;self.assistant_open=True
        self.blocked=False
    def cut(self):
        self.end('assistant',self.assistant_id,False);self.assistant_open=False;self.blocked=True
    def handle(self,item):
        activity=item.get('voiceActivity',{}).get('type')
        if activity=='ACTIVITY_START':
            if not self.user_active:
                self.user_closed=False
                self.end('user',self.user_id,True);self.user_id+=1;self.user_interim=False
            self.user_active=True
            if self.assistant_open or self.playing():self.cut()
        elif activity=='ACTIVITY_END':
            self.user_active=False;self.end('user',self.user_id,True)
        content=item.get('serverContent',{})
        for field,mode in [('interimInputTranscription','snapshot'),('inputTranscription','delta')]:
            data=content.get(field)
            if data is not None:
                if self.user_closed:
                    self.user_id+=1;self.user_closed=False;self.user_interim=False
                if not self.user_id:self.user_id=1
                if field=='interimInputTranscription':self.user_interim=True
                elif self.user_interim:mode='snapshot';self.user_interim=False
                text=data.get('text','')
                if text:self.publish({'event':'transcript','role':'user','turn_id':self.user_id,'text':text,'mode':mode})
                if data.get('finished'):self.end('user',self.user_id,True)
        if content.get('interrupted'):
            self.cut();return
        if content.get('modelTurn',{}).get('parts') and not self.waiting():self.begin_assistant()
        data=content.get('outputTranscription')
        if data is not None and not self.blocked:
            self.begin_assistant();text=data.get('text','')
            if text:self.publish({'event':'transcript','role':'assistant','turn_id':self.assistant_id,'text':text,'mode':'delta'})
        if content.get('turnComplete'):
            if not self.blocked:self.end('assistant',self.assistant_id,True)
            self.end('user',self.user_id,True);self.user_closed=True;self.assistant_open=False
