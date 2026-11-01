#!/usr/bin/env python3
"""Two-glyph scope, preserved repertoire/layout/metrics, real shaping and repeat build."""
import hashlib,json,pathlib,subprocess,tempfile,unicodedata as ud
from fontTools.ttLib import TTFont
from build import ROOT
from build_prose_kana import BASE,STEM,build
from hb import Shaper
from validate import ink_signature,shift_jis_repertoire
from samples import SAMPLES,MARK_SAMPLES,ALPHABETS

def coords(f,n):
 a,e,b=f['glyf'][n].getCoordinates(f['glyf']);return list(a),list(e),[x&1 for x in b]
def sig(rows):return [(r['gid'],r['advance'],r['dx'],r['dy']) for r in rows]
def main():
 generic_before={n:subprocess.run(['fc-match','-f','%{file}',n],capture_output=True,text=True,check=True).stdout for n in ['sans-serif','serif','monospace']}
 path=ROOT/'inputs/prose-zen-kana'/(STEM+'.ttf');old=TTFont(BASE);new=TTFont(path);oc=old.getBestCmap();nc=new.getBestCmap();changed={nc[cp] for cp in [0x3095,0x3096]};assert nc==oc and len(nc)==9205;assert new.getGlyphOrder()==old.getGlyphOrder();exact=[]
 for n in old.getGlyphOrder():
  if n in changed:assert coords(old,n)!=coords(new,n) and old['hmtx'][n][0]==new['hmtx'][n][0]==1000
  else:assert coords(old,n)==coords(new,n) and old['hmtx'][n]==new['hmtx'][n],n;exact.append(n)
 for tag in ['GSUB','GPOS','GDEF']:assert old[tag].compile(old)==new[tag].compile(new),tag
 for tag in ['hhea','OS/2']:assert old[tag].compile(old)==new[tag].compile(new),tag
 assert [new['head'].xMin,new['head'].yMin,new['head'].xMax,new['head'].yMax]==[old['head'].xMin,old['head'].yMin,old['head'].xMax,old['head'].yMax]
 b=Shaper(BASE);a=Shaper(path)
 for cp in sorted(nc):assert sig(a.shape(chr(cp)))==sig(b.shape(chr(cp))),(hex(cp),'shaping/advance changed')
 for lang,text in ALPHABETS.items():assert not set(map(ord,text+text.upper()))-set(nc),lang
 assert not shift_jis_repertoire()-set(nc)
 for lang,(_,text) in SAMPLES.items():assert sig(a.shape(text,lang))==sig(b.shape(text,lang)) and sig(a.shape(text,lang))==sig(a.shape(ud.normalize('NFD',text),lang)),lang
 for text in MARK_SAMPLES+['α\u0301\u0308','ω\u0308','Η\u0301','n\u0303\u0301','Α\u0308','Ω\u0308']:
  lang='ja' if ord(text[0])>0x3000 else 'el' if ord(text[0])>0x300 else 'en';assert ink_signature(a,text,lang)==ink_signature(b,text,lang),text
 normalized_differences=[]
 for cp in nc:
  raw=chr(cp);nfc=ud.normalize('NFC',raw);nfd=ud.normalize('NFD',raw);an=a.shape(nfc,'ja');ad=a.shape(nfd,'ja')
  assert sig(an)==sig(b.shape(nfc,'ja')) and sig(ad)==sig(b.shape(nfd,'ja')),(hex(cp),'normalized behavior changed')
  if sig(an)!=sig(ad):normalized_differences.append({'codepoint':f'U+{cp:04X}','name':ud.name(raw),'NFC':sig(an),'NFD':sig(ad),'preexisting_unchanged':True,'positioned_ink_equal':ink_signature(a,nfc,'ja')==ink_signature(a,nfd,'ja')})
 strings=['かゕけゖぁぃぅぇぉっゃゅょゎ','か ゕ け ゖ','昔の資料に出てくる小さな「ゕ」「ゖ」も、周囲の文字から浮かずに読めるか確かめます。']
 for text in strings:assert all(r['gid'] for r in a.shape(text,'ja')) and sig(a.shape(text,'ja'))==sig(b.shape(text,'ja'))
 for cp in [0x3095,0x3096]:
  g=new['glyf'][nc[cp]];assert 0<g.xMin<g.xMax<1000 and -100<g.yMin<0 and 500<g.yMax<600
  assert sum(r['advance'] for r in a.shape('か'+chr(cp)+'け','ja'))==3000
 w=TTFont(path.with_suffix('.woff2'));assert w.getBestCmap()==nc and w['hmtx'].metrics==new['hmtx'].metrics
 for n in new.getGlyphOrder():assert coords(new,n)==coords(w,n)
 for tag in ['GSUB','GPOS','GDEF']:assert w[tag].compile(w)==new[tag].compile(new)
 assert new['name'].getDebugName(1)=='Morimo Prose Zen' and new['name'].getDebugName(5)=='Version 0.003'
 for rel,want in json.loads((ROOT/'inputs/preservation/prose-kana-preserved.json').read_text()).items():
  p=ROOT/rel;assert hashlib.sha256(p.read_bytes()).hexdigest()==want,rel
 generic={n:subprocess.run(['fc-match','-f','%{file}',n],capture_output=True,text=True,check=True).stdout for n in ['sans-serif','serif','monospace']};assert generic==generic_before
 report={'version':'0.003','cmap':len(nc),'changed_codepoints':['U+3095','U+3096'],'other_glyphs_and_metrics_exact':len(exact),'all_9205_default_gid_advance_offsets_exact':True,'all_9205_normalized_behavior_preserved':True,'preexisting_NFC_NFD_different':normalized_differences,'layout_byte_identical':['GSUB','GPOS','GDEF'],'hhea_OS2_byte_identical':True,'font_bounds_unchanged':True,'full_ka_ke_and_other_small_kana_unchanged':True,'retained_project_font_hashes_preserved':True,'generic_matches_unchanged':generic,'mark_probes_exact':15,'TTF_WOFF2_all_outlines_metrics_layout_equivalent':True,'repeat':{},'limits':'Only two geometries changed; aliases/GIDs/layout remain stable. Previously unencoded U+3099/U+309A and noncomposable small-kana voicing remain unsupported. Raw compatibility forms vs normalized forms retain0.002 behavior. No regional Chinese/IVS/vertical promise. Optical match remains user review.'}
 with tempfile.TemporaryDirectory(prefix='morimo-kana-repeat-') as tmp:
  build(tmp)
  for p in sorted((ROOT/'inputs/prose-zen-kana').iterdir()):
   h=hashlib.sha256(p.read_bytes()).hexdigest();assert h==hashlib.sha256((pathlib.Path(tmp)/p.name).read_bytes()).hexdigest(),p.name;report['repeat'][p.name]=h
 (ROOT/'reports/prose-kana.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':main()
