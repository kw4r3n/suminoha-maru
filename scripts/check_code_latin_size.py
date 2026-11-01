import json,pathlib,unicodedata as ud
from fontTools.ttLib import TTFont
from build_code_latin_size import *
from hb import Shaper
from validate import ink_signature
from samples import SAMPLES
from render_code_defaults import SELECTED
r=json.loads((OUT/'build.json').read_text());a=TTFont(BASE);reports={}
for suffix,row in r.items():
 p=OUT/('MorimoCodeZenLatin'+suffix+'-Regular.ttf');f=TTFont(p);changed=set(row['changed']);assert a.getBestCmap()==f.getBestCmap()
 for n in a.getGlyphOrder():
  assert a['hmtx'][n][0]==f['hmtx'][n][0]
  if n not in changed:assert a['glyf'][n].compile(a['glyf'])==f['glyf'][n].compile(f['glyf']) and a['hmtx'][n]==f['hmtx'][n]
 for tag in ['GSUB','GDEF']:assert a[tag].compile(a)==f[tag].compile(f)
 s=Shaper(p);old=Shaper(BASE)
 for lang,(_,text) in SAMPLES.items():assert ink_signature(s,text,lang)==ink_signature(s,ud.normalize('NFD',text),lang),lang
 contexts=['0O1lI 0001','q\u0308 x\u0302\u0301 a\u030b','!= !== == === => -> >>= =<< <|> |>','\\n \\t \\\\','日本語 とど カタカナ','αβγ ΈΉΌΎΏ ЁЙЇ']
 for text in contexts:
  before=old.shape(text,features=SELECTED);after=s.shape(text,features=SELECTED);assert before==after,'Shaping positions changed'
 for text,lang in [('日本語 とど カタカナ','ja'),('αβγ ΈΉΌΎΏ','el'),('ЁЙЇ','ru')]:assert ink_signature(s,text,lang)==ink_signature(old,text,lang)
 over=[]
 for n in changed:
  g=f['glyf'][n];aw=f['hmtx'][n][0]
  if g.numberOfContours:
   assert g.yMin>=-350 and g.yMax<=1200,n
   if aw and (g.xMin<0 or g.xMax>aw):over.append(n)
 reports[suffix]={'changed':len(changed),'capped':len(row['caps']),'horizontal_overhang_glyphs':over,'positions_features_exact':True,'NFC_NFD_P0':'pass','pure_Japanese_Greek_Cyrillic':'exact','vertical_bounds':'pass','shared_marks':'Unscaled shared glyphs retained; arbitrary mark positioning not broadly repaired'}
(ROOT/'reports/code-latin-size-validation.json').write_text(json.dumps(reports,indent=2));print(json.dumps(reports))
