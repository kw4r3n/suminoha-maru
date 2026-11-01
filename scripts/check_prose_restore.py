#!/usr/bin/env python3
"""Verify append-only geometry/layout, exact repertoire, normalized forms and source provenance."""
import collections,hashlib,json,pathlib,subprocess,tempfile,unicodedata as ud
from fontTools.ttLib import TTFont
from build import ROOT
from build_prose_restore import build,targets,STEM
from hb import Shaper
from validate import signature,ink_signature,shift_jis_repertoire
from samples import ALPHABETS,SAMPLES,MARK_SAMPLES

def sig(rows):return [(r['gid'],r['advance'],r['dx'],r['dy']) for r in rows]
def check():
 generic_before={n:subprocess.run(['fc-match','-f','%{file}',n],capture_output=True,text=True,check=True).stdout for n in ['sans-serif','serif','monospace']}
 path=ROOT/'inputs/prose-zen-restored'/(STEM+'.ttf');f=TTFont(path);old,reference,gap=targets();c=f.getBestCmap();oc=old.getBestCmap();report=json.loads((ROOT/'inputs/prose-zen-restored/build.json').read_text());source=TTFont(ROOT/'sources/kiwimaru/KiwiMaru-Regular.ttf');sc=source.getBestCmap()
 assert set(c)==set(reference.getBestCmap()) and set(c)-set(oc)==gap and len(gap)==501
 assert f.getGlyphOrder()[:len(old.getGlyphOrder())]==old.getGlyphOrder()
 for cp,n in oc.items():assert c[cp]==n
 for name in old.getGlyphOrder():
  assert f['hmtx'][name]==old['hmtx'][name]
  a,ae,af=f['glyf'][name].getCoordinates(f['glyf']);b,be,bf=old['glyf'][name].getCoordinates(old['glyf'])
  assert list(a)==list(b) and list(ae)==list(be) and [v&1 for v in af]==[v&1 for v in bf],name
 for tag in ['GSUB','GPOS','GDEF']:assert f[tag].compile(f)==old[tag].compile(old),(tag,'existing layout changed')
 for tag,fields in {'hhea':['ascent','descent','lineGap','advanceWidthMax'],'OS/2':['sTypoAscender','sTypoDescender','sTypoLineGap','usWinAscent','usWinDescent','usWeightClass','xAvgCharWidth','sxHeight','sCapHeight']}.items():
  for field in fields:assert getattr(f[tag],field)==getattr(old[tag],field),(tag,field)
 assert f['head'].unitsPerEm==old['head'].unitsPerEm and f['head'].yMin>=-350 and f['head'].yMax<=1150
 for src,new in report['source_name_mapping'].items():
  a,ae,af=source['glyf'][src].getCoordinates(source['glyf']);b,be,bf=f['glyf'][new].getCoordinates(f['glyf'])
  assert list(a)==list(b) and list(ae)==list(be) and [v&1 for v in af]==[v&1 for v in bf],src
  assert source['hmtx'][src]==f['hmtx'][new]
 for cp in gap:assert c[cp]==report['source_name_mapping'][sc[cp]]
 before=Shaper(ROOT/'inputs/prose-zen'/(STEM+'.ttf'));after=Shaper(path);ky=Shaper(ROOT/'sources/kiwimaru/KiwiMaru-Regular.ttf')
 # Detect any conditional-normalization/layout effect on previously encoded inputs.
 for cp in sorted(oc):assert sig(before.shape(chr(cp)))==sig(after.shape(chr(cp))),(hex(cp),'existing single input changed')
 normalized=[];raw_changes=[];default_core=[];spacing_changes=[]
 for cp in sorted(gap):
  raw=chr(cp);a=after.shape(ud.normalize('NFC',raw),'ja');b=after.shape(ud.normalize('NFD',raw),'ja');assert a and all(r['gid'] for r in a+b);assert sig(a)==sig(b),(hex(cp),'NFC/NFD')
  rows=after.shape(raw,'ja');assert all(r['gid'] for r in rows),(hex(cp),'raw missing')
  if all(r['glyph'].startswith('kiwiGap_') for r in rows):
   assert signature(after,rows)==signature(ky,ky.shape(raw,'ja')),(hex(cp),'default source mismatch')
  else:
   assert ud.normalize('NFD',raw)!=raw and signature(after,rows)==signature(before,before.shape(ud.normalize('NFD',raw),'ja')),(hex(cp),'unexpected default normalization')
   default_core.append(f'U+{cp:04X}')
  if sig(rows)!=sig(a):raw_changes.append(f'U+{cp:04X}')
  text='A'+raw+'A';r=after.shape(text);expected=2*f['hmtx'][c[ord('A')]][0]+sum(x['advance'] for x in after.shape(raw));actual=sum(x['advance'] for x in r)
  if actual!=expected:spacing_changes.append({'codepoint':f'U+{cp:04X}','difference':actual-expected})
 assert not spacing_changes,spacing_changes
 samples={}
 for lang,text in ALPHABETS.items():assert not set(map(ord,text+text.upper()))-set(c),lang
 assert not shift_jis_repertoire()-set(c)
 for lang,(_,text) in SAMPLES.items():
  rows=after.shape(text,lang);assert all(r['gid'] for r in rows) and sig(rows)==sig(after.shape(ud.normalize('NFD',text),lang));assert sig(rows)==sig(before.shape(text,lang)),lang;samples[lang]='exact prior output, zero missing, NFC/NFD exact'
 mark_tests=MARK_SAMPLES+['α\u0301\u0308','ω\u0308','Η\u0301','n\u0303\u0301','Α\u0308','Ω\u0308']
 for text in mark_tests:
  lang='ja' if ord(text[0])>0x3000 else 'el' if ord(text[0])>0x300 else 'en';assert ink_signature(after,text,lang)==ink_signature(before,text,lang),(text,'existing mark placement changed')
 new_mark_probes={t:after.shape(t,'ja') for t in ['ゕ','ゖ','ゕ\u3099','ゖ\u309a']}
 w=TTFont(path.with_suffix('.woff2'));assert w.getBestCmap()==c and w['hmtx'].metrics==f['hmtx'].metrics
 for tag in ['GSUB','GPOS','GDEF']:assert w[tag].compile(w)==f[tag].compile(f)
 assert f['name'].getDebugName(1)==old['name'].getDebugName(1) and f['name'].getDebugName(5)=='Version 0.002'
 assert source['name'].getDebugName(0) in f['name'].getDebugName(0)
 for rel,want in json.loads((ROOT/'inputs/preservation/prose-restore-preserved.json').read_text()).items():
  p=ROOT/rel;assert hashlib.sha256(p.read_bytes()).hexdigest()==want,rel
 generic={n:subprocess.run(['fc-match','-f','%{file}',n],capture_output=True,text=True,check=True).stdout for n in ['sans-serif','serif','monospace']};assert generic==generic_before
 proof={'cmap':len(c),'restored':len(gap),'missing_prior_repertoire':[],'glyphs':len(f.getGlyphOrder()),'old_glyphs_exact':len(old.getGlyphOrder()),'old_codepoint_outputs_exact':len(oc),'source_glyphs_exact':len(report['source_name_mapping']),'layout_tables_byte_identical':['GSUB','GPOS','GDEF'],'global_metrics_unchanged':True,'normalized_new_NFC_NFD_equal':501,'raw_vs_normalized_different':raw_changes,'raw_default_uses_core_canonical_form':default_core,'A_new_A_extra_kerning':spacing_changes,'samples':samples,'existing_mark_probes_exact':len(mark_tests),'new_kana_probes':new_mark_probes,'font_bounds':[f['head'].xMin,f['head'].yMin,f['head'].xMax,f['head'].yMax],'retained_project_font_hashes_preserved':True,'generic_matches_unchanged':generic,'repeat':{},'limits':'Raw canonical singleton compatibility glyphs may differ from NFC/NFD-normalized unified forms. Existing layout retained; no new mark anchors or Chinese regional/IVS/vertical shaping. Nonstandard voiced small kana are probed, not certified.'}
 with tempfile.TemporaryDirectory(prefix='morimo-restore-repeat-') as tmp:
  build(tmp)
  for p in sorted((ROOT/'inputs/prose-zen-restored').iterdir()):
   h=hashlib.sha256(p.read_bytes()).hexdigest();assert h==hashlib.sha256((pathlib.Path(tmp)/p.name).read_bytes()).hexdigest(),p.name;proof['repeat'][p.name]=h
 (ROOT/'reports/prose-restore.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in proof.items() if k not in ['new_kana_probes','samples','raw_vs_normalized_different']},ensure_ascii=False));print('Raw/normalized different:',len(raw_changes),'canonical default core:',default_core)
if __name__=='__main__':check()
