"""Explicit name pronunciations shared by local recognition and command parsing.

No fuzzy substring matching; syllable sequences must match in their entirety.
"""
import unicodedata

PRONUNCIATIONS={
 'reina':('reyna',),'mira':(),'ren':(),'akira':(),
 'shiori':('she or ee',),'victoria':('viktoria',),'vita':(),'vivi':(),
 'yumi':('you me',),'haru':('har ooh',),'sora':('so rah',),
 'clippy':('clip pee',),'kaito':('kay toe',),'eddy':('eddie',),
 'clara':('klara','cılara','ciılara'),'neko':(),'kai':(),
 'lyra':('lira',),'cat':('ket','katt'),
 'david':('davit','deyvid'),
}
ENGLISH_NAMES=set(PRONUNCIATIONS)-{'david'}

def normalized(value):
 return ''.join(c for c in unicodedata.normalize('NFKD',value.casefold().replace('ı','i')) if not unicodedata.combining(c))

def aliases(name):
 lowered=name.strip().replace('I','ı').replace('İ','i').lower();key=normalized(lowered)
 return tuple(dict.fromkeys((lowered,key,*PRONUNCIATIONS.get(key,()))))
