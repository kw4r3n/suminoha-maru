#!/usr/bin/env python3
import hashlib,json,pathlib,tempfile,unicodedata as ud
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import DecomposingRecordingPen
from build import ROOT
from build_practical_refinement import build,PSTEM,CSTEM,PBASE,CBASE
from hb import Shaper
from validate import ink_signature,signature,shift_jis_repertoire
from samples import ALPHABETS,SAMPLES,MARK_SAMPLES
OPERATORS=['->','=>','!=','===','<=','>=','<-->','::','&&','||','...','!==','==','++','--','<=><=>']
def geom(f,n):
 p=DecomposingRecordingPen(f.getGlyphSet());f.getGlyphSet()[n].draw(p);return p.value,f['hmtx'][n]
def main():
 out=ROOT/'inputs/practical-refinement';j=json.loads((out/'build.json').read_text());p=TTFont(out/(PSTEM+'.ttf'));po=TTFont(PBASE);c=TTFont(out/(CSTEM+'.ttf'));co=TTFont(CBASE);ps=Shaper(out/(PSTEM+'.ttf'));pos=Shaper(PBASE);cs=Shaper(out/(CSTEM+'.ttf'));cos=Shaper(CBASE)
 assert set(p.getBestCmap())==set(po.getBestCmap()) and set(c.getBestCmap())==set(co.getBestCmap())
 mp=j['code']['old_glyph_map'];assert len(mp)==len(co.getGlyphOrder())==8999
 for old,new in mp.items():assert geom(co,old)==geom(c,new),(old,new,'Small glyph changed')
 for cp,old in co.getBestCmap().items():assert c.getBestCmap()[cp]==mp[old],hex(cp)
 assert c['hhea'].ascent==1200 and c['hhea'].descent==-350 and c['hhea'].lineGap==0
 assert c['OS/2'].sTypoAscender==1200 and c['OS/2'].sTypoDescender==-350 and c['OS/2'].usWinDescent==350
 assert p['hhea'].ascent==1150 and p['hhea'].descent==-350
 prose_samples={};code_samples={};ys=[]
 for lang,chars in ALPHABETS.items():
  for f in [p,c]:assert not set(map(ord,chars+chars.upper()))-set(f.getBestCmap()),lang
 for f in [p,c]:assert not shift_jis_repertoire()-set(f.getBestCmap())
 for lang,(_,text) in SAMPLES.items():
  for sh in [ps,cs]:assert all(r['gid'] for r in sh.shape(text,lang))
  assert ink_signature(cs,text,lang)==ink_signature(cos,text,lang),(lang,'Small text changed')
  assert ink_signature(cs,text,lang)==ink_signature(cs,ud.normalize('NFD',text),lang),(lang,'Small NFC/NFD')
  if lang!='ja':assert ink_signature(ps,text,lang)==ink_signature(pos,text,lang),(lang,'Latin/Greek/Cyrillic changed')
  assert ink_signature(ps,text,lang)==ink_signature(ps,ud.normalize('NFD',text),lang),(lang,'prose NFC/NFD')
  prose_samples[lang]='coverage/NFC-NFD pass; non-Japanese old contours/positions exact';code_samples[lang]='old contours/positions exact including accents'
 for text in MARK_SAMPLES+['α\u0301\u0308','ω\u0308','Η\u0301','n\u0303\u0301','Α\u0308','Ω\u0308','x\u0302\u0301','a\u030b','q\u0308']:
  lang='ja' if ord(text[0])>0x3000 else 'el' if ord(text[0])>0x300 else 'en'
  assert ink_signature(cs,text,lang)==ink_signature(cos,text,lang),(text,'Small mark changed')
  if lang!='ja':assert ink_signature(ps,text,lang)==ink_signature(pos,text,lang),(text,'prose Western mark changed')
 for text in ['0','0O 1lI','10 1001','0xFF','0b10','[0]','00.10']:
  oldrows=cos.shape(text);newrows=cs.shape(text);oldzero=[r for r in oldrows if r['glyph']==co.getBestCmap()[48]];newzero=[r for r in newrows if r['glyph']==c.getBestCmap()[48]]
  assert len(oldzero)==len(newzero)==text.count('0') and signature(cs,newzero)==signature(cos,oldzero),(text,'default dotted0 changed')
 ops=[];gs=c.getGlyphSet()
 for text in OPERATORS:
  on=cs.shape(text);off=cs.shape(text,features={'calt':0});assert all(r['gid'] for r in on+off)
  assert sum(r['advance'] for r in on)==sum(r['advance'] for r in off)==540*len(text),(text,'cell advance')
  assert signature(cs,off)==signature(cos,cos.shape(text)),(text,'calt-off shape')
  assert [r['glyph'] for r in on]!=[r['glyph'] for r in off],(text,'ligature not active')
  x=0;lo=0;hi=0
  for row in on:
   b=BoundsPen(gs);gs[row['glyph']].draw(b)
   if b.bounds:lo=min(lo,x+row['dx']+b.bounds[0]);hi=max(hi,x+row['dx']+b.bounds[2]);ys.extend([row['dy']+b.bounds[1],row['dy']+b.bounds[3]])
   x+=row['advance']
  assert lo>=-1 and hi<=x+1,(text,lo,hi,x);ops.append({'text':text,'on':[r['glyph'] for r in on],'off':[r['glyph'] for r in off],'advance':x})
 for lang,(_,text) in SAMPLES.items():
  for row in cs.shape(text,lang):
   b=BoundsPen(gs);gs[row['glyph']].draw(b)
   if b.bounds:ys.extend([b.bounds[1]+row['dy'],b.bounds[3]+row['dy']])
 assert min(ys)>=-350 and max(ys)<=1200,(min(ys),max(ys))
 for stem,f in [(PSTEM,p),(CSTEM,c)]:
  w=TTFont(out/(stem+'.woff2'));assert f.getBestCmap()==w.getBestCmap() and f['hmtx'].metrics==w['hmtx'].metrics
  for tag in ['GSUB','GPOS','GDEF']:
   if tag in f:assert f[tag].compile(f)==w[tag].compile(w)
 proof={'prose':{'cmap':len(p.getBestCmap()),'Latin550_Greek450_preserved':True,'Japanese500_gaps500':True,'samples':prose_samples,'small_kana':j['prose']['derived_small_kana'],'font_bounds':[p['head'].xMin,p['head'].yMin,p['head'].xMax,p['head'].yMax]},'code':{'cmap':len(c.getBestCmap()),'all8999_old_glyphs_metrics_exact':True,'default_dotted0_contexts_exact':True,'source_contextual_0x':'Maple calt changes x to the existing multiplication glyph in0x tokens; dotted zero unchanged','samples':code_samples,'operators':ops,'metrics':[1200,-350,0],'tested_ink_y':[min(ys),max(ys)],'Nerd_fallback_unchanged':True},'repeat':{},'limits':'Known arbitrary combining/three inherited prose normalization limitations remain; no new Chinese regional/IVS/vertical coverage or bold/italic expansion. Numerically equal weights do not establish visual darkness.'}
 with tempfile.TemporaryDirectory(prefix='morimo-practical-repeat-') as tmp:
  build(tmp)
  for q in sorted(out.iterdir()):
   h=hashlib.sha256(q.read_bytes()).hexdigest();assert h==hashlib.sha256((pathlib.Path(tmp)/q.name).read_bytes()).hexdigest(),q.name;proof['repeat'][q.name]=h
 (ROOT/'reports/practical-refinement.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'prose_cmap':proof['prose']['cmap'],'code_cmap':proof['code']['cmap'],'operators':len(ops),'tested_ink_y':proof['code']['tested_ink_y'],'repeat_files':len(proof['repeat'])}))
if __name__=='__main__':main()
