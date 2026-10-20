"""Local independent chats; expire five days after the last changed message."""
import json,time,uuid
from pathlib import Path
from urllib.parse import urlparse

RETENTION=5*24*60*60

def messages(value):
    if not isinstance(value,list):return []
    return [{key:r[key] for key in ('role','text','complete') if key in r} for r in value if isinstance(r,dict) and r.get('role') in ('user','assistant') and isinstance(r.get('text'),str)][-100:]

class ChatStore:
    def __init__(self,directory,clock=time.time):
        self.directory=Path(directory);self.path=self.directory/'chats.json';self.clock=clock
        self.chats=[];self.active=None;self.load()
    def load(self):
        legacy=self.directory/'chat_history.json'
        if self.path.exists():
            data=json.loads(self.path.read_text(encoding='utf-8'))
            if not isinstance(data,dict) or data.get('version')!=1 or not isinstance(data.get('chats'),list):raise ValueError('Geçersiz sohbet arşivi; dosya korunuyor.')
            for row in data['chats']:
                if not isinstance(row,dict) or not isinstance(row.get('id'),str):continue
                stamp=row.get('updated_at')
                if not isinstance(stamp,(float,int)) or not 0<=stamp<=self.clock()+60:continue
                urls=row.get('web_urls',{})
                urls={key:url for key,url in urls.items() if isinstance(url,str) and urlparse(url).scheme=='https' and urlparse(url).hostname=={'chatgpt-web':'chatgpt.com','gemini-web':'gemini.google.com'}.get(key)} if isinstance(urls,dict) else {}
                self.chats.append({'id':row['id'],'updated_at':stamp,'messages':messages(row.get('messages',[])),'web_urls':urls})
            self.active=data.get('active')
        elif legacy.exists():
            old=messages(json.loads(legacy.read_text(encoding='utf-8')))
            if old:self.chats=[{'id':uuid.uuid4().hex,'updated_at':legacy.stat().st_mtime,'messages':old}]
        self.prune()
        if not self.chats:self.new(save=False)
        if not any(c['id']==self.active for c in self.chats):self.active=self.chats[0]['id']
        self.save()
        # Remove the duplicate legacy transcript only after atomic migration.
        if legacy.exists():legacy.unlink()
    @property
    def current(self):return next(c for c in self.chats if c['id']==self.active)
    def prune(self):
        old=len(self.chats);self.chats=[c for c in self.chats if self.clock()-c['updated_at']<=RETENTION]
        return len(self.chats)!=old
    def save(self):
        self.directory.mkdir(parents=True,exist_ok=True)
        temp=self.path.with_suffix('.json.tmp')
        temp.write_text(json.dumps({'version':1,'active':self.active,'chats':self.chats},ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(self.path)
    def update(self,records):
        clean=messages(records)
        if self.current['messages']!=clean:self.current.update(messages=clean,updated_at=self.clock())
        self.save()
    def new(self,save=True):
        self.active=uuid.uuid4().hex;self.chats.insert(0,{'id':self.active,'updated_at':self.clock(),'messages':[]})
        if save:self.save()
        return self.active
    def select(self,key):
        if not any(c['id']==key for c in self.chats):return False
        self.active=key;self.save();return True
    def delete(self,key):
        if not any(c['id']==key for c in self.chats):return False
        previous,active=self.chats,self.active
        self.chats=[c for c in self.chats if c['id']!=key]
        if not self.chats:self.new(save=False)
        elif self.active==key:self.active=max(self.chats,key=lambda c:c['updated_at'])['id']
        try:self.save()
        except OSError:
            self.chats,self.active=previous,active
            raise
        return True
    def title(self,chat):
        text=next((m['text'] for m in chat['messages'] if m['role']=='user'),'Yeni sohbet')
        return ' '.join(text.split())[:46] or 'Yeni sohbet'
