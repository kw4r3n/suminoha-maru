"""Disjoint additive Han companions; never modify the Ratio35 base."""
import argparse,hashlib,json,sys,shutil,tempfile
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.boundsPen import ControlBoundsPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.transformPen import TransformPen
FILES=['NotoSansCJKjp-Regular.otf','PlangothicP1-Regular.ttf','PlangothicP2-Regular.ttf']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def target(src):
 s=set()
 for l in (src/'PropList-17.txt').read_text().splitlines():
  l=l.split('#')[0].strip()
  if not l:continue
  span,prop=map(str.strip,l.split(';'))
  if prop=='Unified_Ideograph':
   x=span.split('..');s.update(range(int(x[0],16),int(x[-1],16)+1))
 return s

def build(root,src,out):
 for r in json.loads((src/'lock.json').read_text()):assert sha(src/r['path'])==r['sha256']
 base=root/'inputs/terminal-ratio35/MorimoCodeJP95TerminalAddonsRatio35-Regular.ttf';assert sha(base)=='175ee5b2de7a1c6cb2337837ad4929b7aa312a3f957a93d62af371d1d35bdc88';b=TTFont(base);seen=set(b.getBestCmap());t=target(src);fonts=[TTFont(src/n) for n in FILES];cm=[f.getBestCmap() for f in fonts];selection=[];gains=[]
 for i,c in enumerate(cm):
  new=sorted((set(c)&t)-seen);seen.update(new);selection.extend((cp,i,c[cp]) for cp in new);gains.append(len(new))
 assert not (t-seen);jp=[r for r in selection if r[1]==0];rare=[r for r in selection if r[1]!=0];parts=[('JP',jp),('RareA',rare[:40000]),('RareB',rare[40000:])];sets=[f.getGlyphSet() for f in fonts];out.mkdir(parents=True,exist_ok=True);mapping={};reports={}
 for suffix,rows in parts:
  family='Morimo Ratio35 Han '+suffix;stem='MorimoRatio35Han'+suffix+'-Regular';glyphs={'.notdef':TTGlyphPen(None).glyph()};metrics={'.notdef':(1080,0)};cmap={};order=['.notdef'];changes=[]
  for j,(cp,i,n) in enumerate(rows):
   gs=sets[i];bp=ControlBoundsPen(gs);gs[n].draw(bp);assert bp.bounds,(hex(cp),i);x0,y0,x1,y1=bp.bounds;upm=fonts[i]['head'].unitsPerEm;s=min(1000/upm,1000/max(1,x1-x0),1200/max(1,y1-y0));dx=540-(x0+x1)*s/2;dy=0
   if y0*s < -250:dy=-250-y0*s
   if y1*s+dy>950:dy=950-y1*s
   rec=DecomposingRecordingPen(gs);gs[n].draw(rec);pen=TTGlyphPen(None);quad=Cu2QuPen(pen,max_err=1,reverse_direction=False);tr=TransformPen(quad,(s,0,0,s,dx,dy))
   for op,pts in rec.value:getattr(tr,op)(*pts)
   g=pen.glyph();g.recalcBounds(None);name=f'u{cp:05X}';assert 39<=g.xMin<=g.xMax<=1041 and -251<=g.yMin<=g.yMax<=951,(hex(cp),g.xMin,g.yMin,g.yMax)
   glyphs[name]=g;metrics[name]=(1080,g.xMin);order.append(name);cmap[cp]=name;mapping[f'U+{cp:04X}']=[suffix,FILES[i],n];changes.append([cp,s,dx,dy])
  fb=FontBuilder(1000,isTTF=True);fb.setupGlyphOrder(order);fb.setupCharacterMap(cmap);fb.setupGlyf(glyphs);fb.setupHorizontalMetrics(metrics);fb.setupHorizontalHeader(ascent=1200,descent=-350,lineGap=0);fb.setupNameTable({'familyName':family,'styleName':'Regular','uniqueFontIdentifier':'0.001;MRMO;'+stem,'fullName':family+' Regular','psName':stem,'version':'Version 0.001','copyright':'©2014-2021 Adobe; Copyright2024 Fitzgerald P. Köeingsegg. Complete notices bundled.','licenseDescription':'SIL Open Font License1.1; see complete donor notices.','licenseInfoURL':'https://openfontlicense.org'});fb.setupOS2(sTypoAscender=1200,sTypoDescender=-350,sTypoLineGap=0,usWinAscent=1200,usWinDescent=350,usWeightClass=400);fb.setupPost();f=fb.font;f['head'].created=b['head'].created;f['head'].modified=b['head'].modified;f.recalcTimestamp=False;f.save(out/(stem+'.ttf'));f.flavor='woff2';f.save(out/(stem+'.woff2'));reports[suffix]={'family':family,'stem':stem,'codepoints':len(rows),'glyphs':len(order),'hashes':{e:sha(out/(stem+'.'+e)) for e in ('ttf','woff2')},'sizes':{e:(out/(stem+'.'+e)).stat().st_size for e in ('ttf','woff2')}};(out/(suffix+'-transforms.json')).write_text(json.dumps(changes,separators=(',',':'))+'\n');print(suffix,len(rows),flush=True)
 result={'base_sha256':sha(base),'scope':'Unicode17 Unified_Ideograph property only; compatibility Han outside this property preserved only if already in base; no IVS/vertical/regional/fullUnicode claim','target':len(t),'base_Han':len(t&set(b.getBestCmap())),'gains':dict(zip(FILES,gains)),'remaining':len(t-seen),'parts':reports};(out/'manifest.json').write_text(json.dumps(result,indent=2)+'\n');(out/'mapping.json').write_text(json.dumps(mapping,sort_keys=True,separators=(',',':'))+'\n');return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--sources',type=Path);p.add_argument('--output',type=Path);a=p.parse_args();build(a.root,a.sources or a.root/'sources/han',a.output or a.root/'inputs/han-companions')
