"""Append only missing compatibility Han; versioned outputs retain old glyph IDs."""
import argparse,json,sys
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.boundsPen import ControlBoundsPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.transformPen import TransformPen

def build(root,out):
 sys.path.insert(0,str(root/'scripts'));from build_han_companions import sha
 src=root/'sources/han'
 for row in json.loads((src/'lock.json').read_text()):assert sha(src/row['path'])==row['sha256']
 old=json.loads((root/'inputs/han-companions/manifest.json').read_text());b=TTFont(root/'inputs/terminal-ratio35/MorimoCodeJP95TerminalAddonsRatio35-Regular.ttf');seen=set(b.getBestCmap());scope=set()
 for line in (src/'PropList-17.txt').read_text().splitlines():
  line=line.split('#')[0].strip()
  if not line:continue
  span,prop=map(str.strip,line.split(';'))
  if prop=='Ideographic':
   z=span.split('..');scope.update(cp for cp in range(int(z[0],16),int(z[-1],16)+1) if 0xf900<=cp<=0xfaff or 0x2f800<=cp<=0x2fa1f)
 for r in old['parts'].values():
  p=root/'inputs/han-companions'/(r['stem']+'.ttf');assert sha(p)==r['hashes']['ttf'];seen.update(TTFont(p).getBestCmap())
 missing=scope-seen;assert len(scope)==1014 and len(missing)==923;out.mkdir(parents=True,exist_ok=True);mapping={};result={}
 for part,donor,expected in [('JP','NotoSansCJKjp-Regular.otf',330),('RareA','PlangothicP1-Regular.ttf',593)]:
  r=old['parts'][part];f=TTFont(root/'inputs/han-companions'/(r['stem']+'.ttf'),recalcTimestamp=False);a=TTFont(src/donor);cm=a.getBestCmap();cps=sorted(missing&set(cm));assert len(cps)==expected;missing-=set(cps);order=list(f.getGlyphOrder());gs=a.getGlyphSet()
  for cp in cps:
   n=cm[cp];bp=ControlBoundsPen(gs);gs[n].draw(bp);x0,y0,x1,y1=bp.bounds;s=min(1000/a['head'].unitsPerEm,1000/max(1,x1-x0),1200/max(1,y1-y0));dx=540-(x0+x1)*s/2;dy=0
   if y0*s < -250:dy=-250-y0*s
   if y1*s+dy>950:dy=950-y1*s
   rec=DecomposingRecordingPen(gs);gs[n].draw(rec);p=TTGlyphPen(None);tr=TransformPen(Cu2QuPen(p,max_err=1,reverse_direction=False),(s,0,0,s,dx,dy))
   for op,pts in rec.value:getattr(tr,op)(*pts)
   g=p.glyph();g.recalcBounds(None);name=f'compat{cp:05X}';f['glyf'][name]=g;f['hmtx'][name]=(1080,g.xMin);order.append(name)
   for tab in f['cmap'].tables:
    if tab.isUnicode() and (tab.format==12 or cp<=0xffff and tab.format==4):tab.cmap[cp]=name
   mapping[f'U+{cp:04X}']={'part':part,'donor':donor,'source_glyph':n,'transform':[s,dx,dy]}
  f.setGlyphOrder(order)
  for rec in list(f['name'].names):
   if rec.nameID in (3,5):f['name'].setName('0.002;MRMO;'+r['stem'] if rec.nameID==3 else 'Version 0.002',rec.nameID,rec.platformID,rec.platEncID,rec.langID)
  f['head'].fontRevision=.002;f.recalcTimestamp=False;f.save(out/(r['stem']+'.ttf'));f.flavor='woff2';f.save(out/(r['stem']+'.woff2'));result[part]={'family':r['family'],'stem':r['stem'],'added':len(cps),'coverage':r['codepoints']+len(cps),'old_sha256':r['hashes']['ttf'],'hashes':{e:sha(out/(r['stem']+'.'+e)) for e in ('ttf','woff2')},'sizes':{e:(out/(r['stem']+'.'+e)).stat().st_size for e in ('ttf','woff2')}};print(part,len(cps),flush=True)
 assert not missing;report={'scope':1014,'previous_present':91,'added':923,'missing':0,'parts':result,'RareB':'Unchanged original han-companions/MorimoRatio35HanRareB-Regular.ttf','base':'Unchanged original Ratio35','package_codepoints':105719};(out/'manifest.json').write_text(json.dumps(report,indent=2)+'\n');(out/'mapping.json').write_text(json.dumps(mapping,sort_keys=True,indent=2)+'\n');return report
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--output',type=Path);a=p.parse_args();build(a.root,a.output or a.root/'inputs/han-compat')
