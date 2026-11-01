import argparse,json,sys,tempfile,unicodedata
from pathlib import Path
from fontTools.ttLib import TTFont
from build_han_compat import build

def check(root,out):
 sys.path.insert(0,str(root/'scripts'));from hb import Shaper
 from build_han_companions import target,sha
 m=json.loads((out/'manifest.json').read_text());mapping=json.loads((out/'mapping.json').read_text());base=TTFont(root/'inputs/terminal-ratio35/MorimoCodeJP95TerminalAddonsRatio35-Regular.ttf');seen=set(base.getBestCmap());report={};normrows={}
 for part,r in m['parts'].items():
  old=root/'inputs/han-companions'/(r['stem']+'.ttf');new=out/(r['stem']+'.ttf');a,b=TTFont(old),TTFont(new);names=a.getGlyphOrder();assert b.getGlyphOrder()[:len(names)]==names
  for n in names:assert a['glyf'][n].compile(a['glyf'])==b['glyf'][n].compile(b['glyf']) and a['hmtx'][n]==b['hmtx'][n],n
  for cp,n in a.getBestCmap().items():assert a.getGlyphID(n)==b.getGlyphID(b.getBestCmap()[cp])
  assert (b['hhea'].ascent,b['hhea'].descent,b['hhea'].lineGap)==(1200,-350,0);assert not(set(b.getBestCmap())&seen);seen.update(b.getBestCmap());assert len(b.getGlyphOrder())<=65535
  added=set(b.getBestCmap())-set(a.getBestCmap());assert len(added)==r['added'];sa,sb=Shaper(old),Shaper(new);outcomes={'raw_cmap_selected':0,'canonical_glyph_selected':0};source=Shaper(root/'sources/han'/('NotoSansCJKjp-Regular.otf' if part=='JP' else 'PlangothicP1-Regular.ttf'))
  for cp in sorted(added):
   n=b.getBestCmap()[cp];g=b['glyf'][n];assert b['hmtx'][n][0]==1080 and 39<=g.xMin<=g.xMax<=1041 and -251<=g.yMin<=g.yMax<=951;ch=chr(cp);nfc=unicodedata.normalize('NFC',ch);assert nfc!=ch;rr=sb.shape(ch,language='ja');assert len(rr)==1 and rr[0]['gid']!=0 and rr[0]['advance']==1080
   raw=b.getGlyphID(n);canonical=b.getBestCmap().get(ord(nfc));gid=rr[0]['gid'];selected='raw_cmap_selected' if gid==raw else 'canonical_glyph_selected';assert gid==raw or canonical and gid==b.getGlyphID(canonical),(hex(cp),rr);outcomes[selected]+=1;normrows[f'U+{cp:04X}']={'NFC':f'U+{ord(nfc):04X}','part':part,'raw_gid':raw,'HarfBuzz_gid':gid,'result':selected,'source_HarfBuzz':source.shape(ch,language='ja')[0]['glyph']}
  cps=sorted(a.getBestCmap())
  for cp in cps[::max(1,len(cps)//60)][:60]:assert sa.shape(chr(cp),language='ja')==sb.shape(chr(cp),language='ja')
  w=TTFont(out/(r['stem']+'.woff2'))
  for t in b.keys():
   if t not in ('GlyphOrder','head','loca'):assert b[t].compile(b)==w[t].compile(w),t
  report[part]={'old_glyphs_exact':len(names),'old_shaping_probes':60,'added':len(added),'normalization':outcomes}
 rare=TTFont(root/'inputs/han-companions/MorimoRatio35HanRareB-Regular.ttf');assert not(set(rare.getBestCmap())&seen);seen.update(rare.getBestCmap());assert len(seen)==105719;assert not(target(root/'sources/han')-seen)
 with tempfile.TemporaryDirectory(prefix='morimo-compat-repeat-') as tmp:
  build(root,Path(tmp))
  for r in m['parts'].values():
   for ext in ('ttf','woff2'):assert sha(out/(r['stem']+'.'+ext))==sha(Path(tmp)/(r['stem']+'.'+ext))
 report['package_codepoints']=len(seen);report['compatibility_coverage']=[1014,1014];report['Unified_Ideograph_coverage']=[101996,101996];report['repeat_byte_identical']=True;report['format_equivalence']=True;report['limits']='NFC canonical selection may override raw compatibility cmap shapes. No IVS/regional/vertical/fullUnicode expansion.';(out/'normalization.json').write_text(json.dumps(normrows,indent=2)+'\n');(out/'validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--output',type=Path);a=p.parse_args();check(a.root,a.output or a.root/'inputs/han-compat')
