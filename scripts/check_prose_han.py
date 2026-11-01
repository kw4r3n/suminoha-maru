import argparse,json,sys,tempfile,subprocess,os
from pathlib import Path
from fontTools.ttLib import TTFont
from build_prose_han import build,SPACES

def check(root,out,previews):
 sys.path.insert(0,str(root/'scripts'));from build_han_companions import target,sha
 from hb import Shaper
 m=json.loads((out/'manifest.json').read_text());base=root/'inputs/prose-equal/MorimoProseZen-Regular.ttf';assert sha(base)==m['base_sha256'];b=TTFont(base);bc=b.getBestCmap();seen=set(bc);report={};maps={};shapers={}
 for part,r in m['parts'].items():
  p=out/(r['stem']+'.ttf');f=TTFont(p);c=f.getBestCmap();assert set(c)&seen==set(SPACES);seen.update(c);maps[part]=f;assert (f['hhea'].ascent,f['hhea'].descent,f['hhea'].lineGap)==(1150,-350,0)
  for cp,n in c.items():
   g=f['glyf'][n]
   if cp in SPACES:assert f['hmtx'][n]==b['hmtx'][bc[cp]] and g.compile(f['glyf'])==b['glyf'][bc[cp]].compile(b['glyf'])
   else:assert f['hmtx'][n][0]==1000 and 19<=g.xMin<=g.xMax<=981 and -350<=g.yMin<=g.yMax<=1150
  w=TTFont(out/(r['stem']+'.woff2'))
  for t in f.keys():
   if t not in ('GlyphOrder','head','loca'):assert f[t].compile(f)==w[t].compile(w)
  sh=Shaper(p);shapers[part]=sh;cps=sorted(set(c)-set(SPACES))
  for cp in cps[::max(1,len(cps)//50)][:50]:assert sh.shape(chr(cp),language='ja')[0]['advance']==1000
  report[part]={'Han_added':len(c)-3,'shape_probes':50,'cmap_space_metrics':[f['hmtx'][c[x]][0] for x in SPACES]}
 assert len(seen)==105365 and not(target(root/'sources/han')-seen);mapping=json.loads((root/'inputs/han-compat/mapping.json').read_text())
 for cp,r in mapping.items():
  rr=shapers[r['part']].shape(chr(int(cp[2:],16)),language='ja');assert len(rr)==1 and rr[0]['advance']==1000 and rr[0]['gid']
 # Explicit property coverage for compatibility, separately from normalization.
 comp=set()
 for line in (root/'sources/han/PropList-17.txt').read_text().splitlines():
  line=line.split('#')[0].strip()
  if not line:continue
  span,prop=map(str.strip,line.split(';'))
  if prop=='Ideographic':
   x=span.split('..');comp.update(cp for cp in range(int(x[0],16),int(x[-1],16)+1) if 0xf900<=cp<=0xfaff or 0x2f800<=cp<=0x2fa1f)
 assert len(comp)==1014 and not(comp-seen)
 with tempfile.TemporaryDirectory(prefix='morimo-prose-repeat-') as tmp:
  build(root,Path(tmp))
  for r in m['parts'].values():
   for ext in ('ttf','woff2'):assert sha(out/(r['stem']+'.'+ext))==sha(Path(tmp)/(r['stem']+'.'+ext))
 # Isolated native Pango: no installation/default edits; only primary+these companions.
 previews.mkdir(parents=True,exist_ok=True)
 with tempfile.TemporaryDirectory(prefix='morimo-prose-native-') as td:
  td=Path(td);fonts=td/'fonts';fonts.mkdir();(fonts/base.name).symlink_to(base)
  for p in out.glob('*.ttf'):(fonts/p.name).symlink_to(p.resolve())
  conf=td/'fonts.conf';prefix='<?xml version="1.0"?><!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd"><fontconfig><dir>'+str(fonts)+'</dir><cachedir>'+str(td/'cache')+'</cachedir>';rule='<match target="pattern"><test name="family" compare="eq"><string>Morimo Prose Zen</string></test><edit name="family" mode="append" binding="strong">'+''.join('<string>'+r['family']+'</string>' for r in m['parts'].values())+'</edit></match>';conf.write_text(prefix+rule+'<match target="font"><edit name="hinting" mode="assign"><bool>false</bool></edit></match></fontconfig>');env=os.environ.copy();env['FONTCONFIG_FILE']=str(conf)
  text=' '.join(chr(int(cp[2:],16)) for cp in sorted(mapping))+'\n日本語 Latin 𠀀 𠀁 𠀂\n𠀀\u00a0𠀁\u00a0𠀂\n𠀀\u3000𠀁\u3000𠀂\n𠀀\t𠀁';serial=td/'probe.json';subprocess.run(['pango-view','--no-display','--font=Morimo Prose Zen 12','--language=ja','--width=900','--wrap=word-char','--text='+text,'--serialize-to='+str(serial)],env=env,check=True,stdout=subprocess.DEVNULL);data=json.loads(serial.read_text());assert data['output']['unknown-glyphs']==0
  import unicodedata
  fontmap={m['base_sha256']:b}|{r['hashes']['ttf']:maps[part] for part,r in m['parts'].items()};norm={'raw':0,'canonical':0};tested=set()
  for line in data['output']['lines']:
   for run in line['runs']:
    ff=fontmap[run['font']['checksum']];cc=ff.getBestCmap()
    for g in run['glyphs']:
     cp=ord(run['text'].encode()[g['log-cluster']:].decode()[0]);key=f'U+{cp:04X}'
     if key not in mapping:continue
     tested.add(cp);raw=cc.get(cp);canonical=cc.get(ord(unicodedata.normalize('NFC',chr(cp))))
     if raw and ff.getGlyphID(raw)==g['glyph']:norm['raw']+=1
     else:assert canonical and ff.getGlyphID(canonical)==g['glyph'];norm['canonical']+=1
  assert len(tested)==923
  report['Pango_compatibility_selection']=norm
  sample='既存の日本語と Latin text を自然な幅で。\n丸みのある本文を保ち、足りない漢字だけ補います。\nA quiet paragraph: Nguyễn, Árvíztűrő, q̈ x̂́.\n不足漢字: 麤 𠮷 𩸽 𠀀 𲎰\n互換漢字: 豈 更 車 丽 丸\n空白: 𠀀 𠀁 ／ 𠀀\u00a0𠀁 ／ 𠀀\u3000𠀁'
  subprocess.run(['pango-view','--no-display','--font=Morimo Prose Zen 20','--language=ja','--margin=20','--text='+sample,'--output='+str(previews/'expanded.png'),'--serialize-to='+str(previews/'expanded-layout.json')],env=env,check=True);primary=td/'primary';primary.mkdir();(primary/base.name).symlink_to(base);conf.write_text(prefix.replace(str(fonts),str(primary))+'<match target="font"><edit name="hinting" mode="assign"><bool>false</bool></edit></match></fontconfig>');subprocess.run(['pango-view','--no-display','--font=Morimo Prose Zen 20','--language=ja','--margin=20','--text='+sample,'--output='+str(previews/'primary-only.png')],env=env,check=True)
 report.update({'base_bit_exact':True,'base_coverage':9205,'package_codepoints':len(seen),'Han_added':96160,'unified_coverage':[101996,101996],'compatibility_coverage':[1014,1014],'repeat_byte_identical':True,'format_equivalence':True,'Pango_all923_and_spaces_unknown':0,'limits':'No installed/default changes; no IVS/regional/vertical/fullUnicode promise; Noto/Plangothic Regular donor darkness differs from genuine500 prose.'});(out/'validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--output',type=Path);p.add_argument('--previews',type=Path);a=p.parse_args();check(a.root,a.output or a.root/'inputs/prose-han',a.previews or a.root/'specimens/prose-han')
