import argparse,json,sys,tempfile,hashlib
from pathlib import Path
from fontTools.ttLib import TTFont
from PIL import Image,ImageFont,ImageDraw
from build_han_companions import build,target,sha

def check(root,src,out,previews,repeat=True):
 sys.path.insert(0,str(root/'scripts'));from hb import Shaper
 m=json.loads((out/'manifest.json').read_text());base=root/'inputs/terminal-ratio35/MorimoCodeJP95TerminalAddonsRatio35-Regular.ttf';assert sha(base)==m['base_sha256'];bf=TTFont(base);seen=set(bf.getBestCmap());t=target(src);fonts=[bf];paths=[base];count=0;bounds=[0,0]
 for part,r in m['parts'].items():
  p=out/(r['stem']+'.ttf');f=TTFont(p);c=f.getBestCmap();assert not (set(c)&seen);assert set(c)<=t;seen.update(c);assert len(f.getGlyphOrder())<=65535;assert len(c)==r['codepoints'];assert (f['hhea'].ascent,f['hhea'].descent,f['hhea'].lineGap)==(1200,-350,0);sh=Shaper(p)
  for cp,n in c.items():
   g=f['glyf'][n];assert f['hmtx'][n][0]==1080;assert 39<=g.xMin<=g.xMax<=1041 and -251<=g.yMin<=g.yMax<=951;bounds=[min(bounds[0],g.yMin),max(bounds[1],g.yMax)]
  cps=sorted(c);sample=cps[::max(1,len(cps)//50)][:50]
  for cp in sample:
   rr=sh.shape(chr(cp),language='ja');assert len(rr)==1 and rr[0]['gid']!=0 and rr[0]['advance']==1080;count+=1
  w=TTFont(out/(r['stem']+'.woff2'))
  for tag in f.keys():
   if tag not in ('GlyphOrder','head','loca'):assert f[tag].compile(f)==w[tag].compile(w),tag
  paths.append(p);fonts.append(f)
 assert not (t-seen);assert len(seen)==9559+95237
 # Deterministic independent rebuild, discarded after comparison.
 if repeat:
  with tempfile.TemporaryDirectory(prefix='morimo-han-repeat-') as tmp:
   build(root,src,Path(tmp))
   for r in m['parts'].values():
    for ext in ('ttf','woff2'):assert sha(out/(r['stem']+'.'+ext))==sha(Path(tmp)/(r['stem']+'.'+ext))
 donor_probes=0
 mapping=json.loads((out/'mapping.json').read_text())
 for filename in ('NotoSansCJKjp-Regular.otf','PlangothicP1-Regular.ttf','PlangothicP2-Regular.ttf'):
  ds=Shaper(src/filename);cps=sorted(int(cp[2:],16) for cp,v in mapping.items() if v[1]==filename)
  for cp in cps[::max(1,len(cps)//30)][:30]:
   rr=ds.shape(chr(cp),language='ja');assert len(rr)==1 and rr[0]['glyph']==mapping[f'U+{cp:04X}'][2],(filename,hex(cp),rr);donor_probes+=1
 maps=[f.getBestCmap() for f in fonts];ff=[ImageFont.truetype(str(p),28,layout_engine=ImageFont.Layout.RAQM) for p in paths];ui=ImageFont.truetype('/usr/share/fonts/TTF/DejaVuSans.ttf',19);im=Image.new('RGB',(1800,1150),'#14201a');d=ImageDraw.Draw(im);d.text((24,20),'Ratio35 + Gothic Han companions / same28px / red box = missing, no system fallback',font=ui,fill='#dfede3');d.text((24,62),'Existing Ratio35 only',font=ui,fill='#9dcab0');d.text((924,62),'Ratio35 > Han JP > RareA > RareB',font=ui,fill='#9dcab0')
 sampletext=['既存の日本語と Latin 648 / 日本語 1080','日本語の形を保ち、足りない漢字だけ補います。','if (ready != null) return "日本語";','Noto JP: 麤 𠮷 𩸽 髙 靏 𠮟','Rare: '+''.join(chr(cp) for cp in sorted(set(maps[2]))[::max(1,len(maps[2])//8)][:8]),'RareB: '+''.join(chr(cp) for cp in sorted(set(maps[3]))[::max(1,len(maps[3])//8)][:8]),'Extension J: '+''.join(chr(cp) for cp in sorted(t) if 0x323b0<=cp<=0x3347f)[:8],'🤖 ✅ ❌ '+chr(0xe718)+' main / x̂́ q̈ a̋','Compatibility kept: 﨑 / IVS not added']
 for col in (0,1):
  x0=24+900*col;y=140
  for text in sampletext:
   x=x0;run='';last=0
   def flush(run,idx,x):
    if run:
     box=d.textbbox((x,y),run,font=ff[idx],anchor='ls');assert box[0]>=col*900 and box[2]<(col+1)*900 and box[1]>=0 and box[3]<1150;d.text((x,y),run,font=ff[idx],anchor='ls',fill='#dfede3');x+=ff[idx].getlength(run)
    return x
   for ch in text:
    idx=next((i for i,c in enumerate(maps[:1] if col==0 else maps) if ord(ch) in c),-1)
    if idx!=last:x=flush(run,last,x);run='';last=idx
    if idx<0:d.rectangle((x,y-24,x+25,y),outline='#ff7979');x+=30
    else:run+=ch
   x=flush(run,last,x);y+=88
 d.text((24,1040),'Only missing Unified_Ideograph scalars are supplied; no IVS, locale switching or complete Unicode claim.',font=ui,fill='#9dcab0');previews.mkdir(parents=True,exist_ok=True);im.save(previews/'comparison.png');report={'base_bit_exact':True,'scope':'Unicode17 Unified_Ideograph','unified_total':len(t),'base_Han':len(t&set(maps[0])),'Han_added':95237,'package_codepoints':len(seen),'scope_gaps':[],'cross_font_duplicates':0,'new_glyph_advance':1080,'new_bounds':bounds,'donor_HarfBuzz_default_glyph_probes':donor_probes,'sampled_HarfBuzz_singletons':count,'format_equivalence':True,'repeat_byte_identical':repeat,'limits':'No new IVS/variation/locl/vertical or arbitrary mark support; mainland forms only where NotoJP lacks glyph. Sampled raster and conversion tolerance1font unit, not native-terminal certification.'};(out/'validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--sources',type=Path);p.add_argument('--output',type=Path);p.add_argument('--previews',type=Path);a=p.parse_args();check(a.root,a.sources or a.root/'sources/han',a.output or a.root/'inputs/han-companions',a.previews or a.root/'specimens/han-companions')
