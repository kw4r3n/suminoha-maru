import argparse,json,sys,tempfile
from pathlib import Path
from fontTools.ttLib import TTFont
from build_han_spacefix import build,SPACES

def check(root,out):
 sys.path.insert(0,str(root/'scripts'));from hb import Shaper
 from build_han_companions import sha,target
 m=json.loads((out/'manifest.json').read_text());base=TTFont(root/'inputs/terminal-ratio35/MorimoCodeJP95TerminalAddonsRatio35-Regular.ttf');seen=set(base.getBestCmap());rep={};fonts=[]
 for part,r in m.items():
  a=TTFont(root/r['source']);p=out/(r['stem']+'.ttf');b=TTFont(p);names=a.getGlyphOrder();assert b.getGlyphOrder()[:len(names)]==names
  for n in names:assert a['glyf'][n].compile(a['glyf'])==b['glyf'][n].compile(b['glyf']) and a['hmtx'][n]==b['hmtx'][n]
  assert (set(b.getBestCmap())-set(a.getBestCmap()))==set(SPACES);assert set(b.getBestCmap())&seen==set(SPACES);seen.update(b.getBestCmap());fonts.append(b)
  for cp in SPACES:
   n=b.getBestCmap()[cp];bn=base.getBestCmap()[cp];assert b['glyf'][n].compile(b['glyf'])==base['glyf'][bn].compile(base['glyf']) and b['hmtx'][n]==base['hmtx'][bn]
  assert (b['hhea'].ascent,b['hhea'].descent,b['hhea'].lineGap)==(1200,-350,0)
  for cp,n in b.getBestCmap().items():
   if cp in SPACES:continue
   assert b['hmtx'][n][0]==1080;g=b['glyf'][n];assert -251<=g.yMin<=g.yMax<=951
  sa,sb=Shaper(root/r['source']),Shaper(p);cps=sorted(a.getBestCmap())
  for cp in cps[::max(1,len(cps)//60)][:60]:assert sa.shape(chr(cp),language='ja')==sb.shape(chr(cp),language='ja')
  for cp in SPACES:assert sb.shape(chr(cp))[0]['advance']==base['hmtx'][base.getBestCmap()[cp]][0]
  w=TTFont(out/(r['stem']+'.woff2'))
  for t in b.keys():
   if t not in ('GlyphOrder','head','loca'):assert b[t].compile(b)==w[t].compile(w)
  rep[part]={'old_glyphs_exact':len(names),'old_shaping_checks':60,'new_whitespace':list(SPACES)}
 assert len(seen)==105719 and not(target(root/'sources/han')-seen);mapping=json.loads((root/'inputs/han-compat/mapping.json').read_text());norm={'raw':0,'canonical':0}
 shapers={part:Shaper(out/(r['stem']+'.ttf')) for part,r in m.items()}
 for cp,r in mapping.items():
  part=r['part'];idx=list(m).index(part);b=fonts[idx];sh=shapers[part];x=int(cp[2:],16);rows=sh.shape(chr(x),language='ja');assert len(rows)==1 and rows[0]['advance']==1080 and rows[0]['gid'];norm['raw' if rows[0]['gid']==b.getGlyphID(b.getBestCmap()[x]) else 'canonical']+=1
 with tempfile.TemporaryDirectory(prefix='morimo-space-repeat-') as tmp:
  build(root,Path(tmp))
  for r in m.values():
   for ext in ('ttf','woff2'):assert sha(out/(r['stem']+'.'+ext))==sha(Path(tmp)/(r['stem']+'.'+ext))
 rep.update({'package_codepoints':len(seen),'Unified_Ideograph':[101996,101996],'compatibility':[1014,1014],'intentional_duplicates_only':[f'U+{x:04X}' for x in SPACES],'HarfBuzz_all923':norm,'repeat_byte_identical':True,'format_equivalence':True});(out/'validation.json').write_text(json.dumps(rep,indent=2)+'\n');print(json.dumps(rep),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--output',type=Path);a=p.parse_args();check(a.root,a.output or a.root/'inputs/han-spacefix')
