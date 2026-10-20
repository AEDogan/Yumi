"""Update existing Yumi chat bubbles; persist only through normal chat history."""
from PySide6.QtCore import QTimer
class NativeTranscriptView:
    def __init__(self,window):
        self.window=window;self.turns={};self.ended={};self.dirty=set();self.follow=False;self.commands_done=set();self.command_epoch=0
        self.refresh_timer=QTimer(window);self.refresh_timer.setSingleShot(True);self.refresh_timer.setInterval(50);self.refresh_timer.timeout.connect(self.refresh)
        self.save_timer=QTimer(window);self.save_timer.setSingleShot(True);self.save_timer.setInterval(250);self.save_timer.timeout.connect(self.save)
    def refresh(self):
        for label,record in self.turns.values():
            if label in self.dirty:label.setText(record['text'])
        self.dirty.clear();self.window._layout_messages()
        if self.follow:
            scroll=self.window.scroll.verticalScrollBar();QTimer.singleShot(0,lambda:scroll.setValue(scroll.maximum()))
        self.follow=False
    def save(self):
        self.window._save_chat_history()
        if hasattr(self.window,'assistant'):
            self.window.assistant.history=[record.copy() for record in self.window.chat_history[-24:] if record.get('complete',True)]
    def new_session(self):
        self.finish_session();self.command_epoch+=1;self.commands_done.clear();self.turns.clear();self.ended.clear()
    def changed(self,role,turn,text,mode):
        if role not in ('user','assistant') or not text:return
        key=(role,turn);entry=self.turns.get(key)
        scroll=self.window.scroll.verticalScrollBar();follow=scroll.value()>=scroll.maximum()-24
        if entry is None:
            if len(self.turns)>=96:
                self.turns.pop(next(iter(self.turns)))
            record={'role':role,'text':'','complete':self.ended.get(key,False)}
            self.window.chat_history.append(record)
            label=self.window.add_message('',role,record=False);entry=(label,record);self.turns[key]=entry
        label,record=entry;old=record['text']
        # Normal provider deltas preserve whitespace; interim updates replace their snapshot.
        merged=text if mode=='snapshot' else old+text
        record['text']=merged[:16000];self.dirty.add(label);self.follow=self.follow or follow
        if not self.refresh_timer.isActive():self.refresh_timer.start()
        if key in self.ended:
            self.save_timer.start()
            if role=='user' and self.ended[key]:
                epoch=self.command_epoch
                QTimer.singleShot(700,lambda:self.run_command(key,epoch))
    def ended_turn(self,role,turn,complete):
        key=(role,turn)
        # Late turnComplete after cancellation cannot upgrade a cut assistant answer.
        if self.ended.get(key) is False and role=='assistant':complete=False
        self.ended[key]=complete;entry=self.turns.get(key)
        if entry:
            label,record=entry;record['complete']=complete
            label.setToolTip('Yanıt araya girildiği için kesildi.' if role=='assistant' and not complete else '')
            self.save_timer.start()
            if role=='user' and complete:
                epoch=self.command_epoch
                QTimer.singleShot(700,lambda:self.run_command(key,epoch))
    def run_command(self,key,epoch):
        if epoch!=self.command_epoch or key in self.commands_done:return
        entry=self.turns.get(key)
        if not entry or not self.ended.get(key):return
        self.commands_done.add(key)
        if hasattr(self.window,'_native_command'):self.window._native_command(entry[1]['text'])
    def finish_session(self):
        for (role,turn),(_,record) in list(self.turns.items()):
            if (role,turn) not in self.ended:self.ended_turn(role,turn,role=='user')
        if self.turns:
            self.refresh_timer.stop();self.refresh();self.save_timer.stop();self.save()
