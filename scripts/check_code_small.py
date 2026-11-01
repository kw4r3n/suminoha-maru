#!/usr/bin/env python3
import copy,hashlib,json,pathlib,tempfile,unicodedata
from fontTools.ttLib import TTFont
from build import ROOT
from build_code_small import build,FAMILY,STEM,SEQUENCES,zero_variant
from hb import Shaper
from samples import SAMPLES,ALPHABETS,MARK_SAMPLES
from validate import ink_signature,shift_jis_repertoire

def main():
 path=ROOT/'inputs/code-small'/(STEM+'.ttf');f=TTFont(path);old=TTFont(ROOT/'inputs/grid-small/MorimoGridSmall-Regular.ttf');c=f.getBestCmap();zero=c[48]
 assert c==old.getBestCmap() and f['hmtx'][zero][0]==540
 unchanged=0
 for name in old.getGlyphOrder():
  if name==zero:continue
  assert f['hmtx'][name]==old['hmtx'][name] and list(f['glyf'][name].getCoordinates(f['glyf'])[0])==list(old['glyf'][name].getCoordinates(old['glyf'])[0]),name
  unchanged+=1
 assert 'GPOS' not in f
 restored=copy.deepcopy(f);table=restored['GSUB'].table;index=len(table.LookupList.Lookup)-1;table.LookupList.Lookup.pop();table.LookupList.LookupCount-=1
 for fr in table.FeatureList.FeatureRecord:
  if fr.FeatureTag=='ccmp':assert fr.Feature.LookupListIndex.pop()==index;fr.Feature.LookupCount-=1
 assert restored['GSUB'].compile(restored)==old['GSUB'].compile(old)
 sh=Shaper(path);base=Shaper(ROOT/'inputs/dist/MorimoCodeGreek5-Regular.ttf');sig=lambda rows:[(r['gid'],r['advance'],r['dx'],r['dy']) for r in rows];samples={}
 for lang,text in ALPHABETS.items():assert not set(map(ord,text+text.upper()))-set(c),(lang,'coverage')
 assert not shift_jis_repertoire()-set(c)
 for lang,(_,text) in SAMPLES.items():
  a=sh.shape(text,lang);b=sh.shape(unicodedata.normalize('NFD',text),lang);assert all(r['gid'] for r in a+b);assert sig(a)==sig(b),(lang,'NFC/NFD');samples[lang]='zero missing, NFC/NFD exact'
 marks=[]
 for text in list(dict.fromkeys(MARK_SAMPLES+SEQUENCES)):
  jp=ord(text[0])>0x3000;lang='ja' if jp else ('el' if ord(text[0])>0x300 else 'en');a=ink_signature(sh,text,lang);b=ink_signature(base,text,lang);scale=1 if jp else .75
  assert len(a)==len(b),(text,'contours');error=0
  for (op,pts),(eop,epts) in zip(a,b):
   assert op==eop
   for v,w in zip(pts,epts):
    if v is None or w is None:assert v is w
    else:error=max(error,abs(v[0]-w[0]*scale),abs(v[1]-w[1]*scale))
  assert error<=2,(text,'mark error',error);marks.append({'text':text,'max_affine_error':error,'glyphs':len(sh.shape(text,lang))})
  assert sig(sh.shape(text,lang))==sig(sh.shape(unicodedata.normalize('NFD',text),lang))
  if text in SEQUENCES:assert len(sh.shape(text,lang))==1
 for text in ['x\u0302\u0341','X\u0302\u0341']:assert len(sh.shape(text))==1
 z=[sh.shape('0'),sh.shape('0',features={'zero':0}),sh.shape('0',features={'zero':1})];assert sig(z[0])==sig(z[1])==sig(z[2])
 assert z[0][0]['glyph']==zero
 source=TTFont(ROOT/'sources/maplemono/MapleMono-Regular.ttf');expected=zero_variant(source,'zero.zero');assert list(expected.getCoordinates(None)[0])==list(f['glyf'][zero].getCoordinates(f['glyf'])[0])
 coords,ends,_=f['glyf'][zero].getCoordinates(f['glyf']);bounds=[];start=0
 for end in ends:
  points=coords[start:end+1];bounds.append([min(p[0] for p in points),min(p[1] for p in points),max(p[0] for p in points),max(p[1] for p in points)]);start=end+1
 dot=min(bounds,key=lambda b:(b[2]-b[0])*(b[3]-b[1]));assert abs((dot[0]+dot[2])/2-270)<=1
 assert f['head'].yMin>=-400 and f['head'].yMax<=1300
 assert {v[0] for v in f['hmtx'].metrics.values()}=={0,540,1080}
 assert f['name'].getDebugName(1)==FAMILY and f['OS/2'].panose.bProportion==9
 w=TTFont(path.with_suffix('.woff2'));assert w.getBestCmap()==c and w['hmtx'].metrics==f['hmtx'].metrics
 for tag in ['GSUB','GDEF']:assert w[tag].compile(w)==f[tag].compile(f)
 for rel,want in json.loads((ROOT/'inputs/preservation/selected-preserved.json').read_text()).items():
  p=ROOT/rel;assert hashlib.sha256(p.read_bytes()).hexdigest()==want,rel
 repeat={}
 with tempfile.TemporaryDirectory(prefix='morimo-code-small-repeat-') as tmp:
  build(tmp)
  for p in (ROOT/'inputs/code-small').iterdir():
   h=hashlib.sha256(p.read_bytes()).hexdigest();assert hashlib.sha256((pathlib.Path(tmp)/p.name).read_bytes()).hexdigest()==h,p.name;repeat[p.name]=h
 result={'family':FAMILY,'unchanged_old_glyphs_except_zero':unchanged,'new_source_compositions':len(SEQUENCES),'cmap':len(c),'glyphs':len(f.getGlyphOrder()),'advances':[0,540,1080],'zero_default_unconditional':True,'zero_contour_boxes':bounds,'source_zero_alternate_exact':True,'samples':samples,'marks':marks,'retained_project_font_hashes_preserved':True,'repeat':repeat,'limits':'Ten lowercase/uppercase combinations repaired; unknown arbitrary marks retain fallback behavior. No programming ligatures/Nerd port in this base-face step.'}
 (ROOT/'reports/code-small.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
