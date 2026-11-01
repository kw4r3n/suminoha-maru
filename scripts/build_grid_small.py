#!/usr/bin/env python3
"""Selected small-Latin input derived from exact Greek5; preserve existing fonts."""
import argparse,copy,hashlib,json,pathlib
from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.transformPen import TransformPen
from build import ROOT,rename,japanese
BASE='099b6815ce68c12cc5daf383fb4da3a42640ef389a4207e6a580de2f878620be'
FACES=[('Morimo Grid Small','MorimoGridSmall-Regular',.75)]
X=.75;NARROW=540;WIDE=1080

def japanese_closure(f):
 c=f.getBestCmap();cp={p for p,n in c.items() if japanese(p) or f['hmtx'][n][0]==WIDE}
 g=copy.deepcopy(f);s=subset.Subsetter();s.populate(unicodes=cp);s.subset(g)
 return set(g.getGlyphOrder())-{'.notdef'}|{n for n,(a,b) in f['hmtx'].metrics.items() if a==WIDE}

def build(output=None):
 out=pathlib.Path(output or ROOT/'inputs/grid-small');out.mkdir(parents=True,exist_ok=True)
 from fetch import main as verify
 verify()
 path=ROOT/'inputs/dist/MorimoCodeGreek5-Regular.ttf';assert hashlib.sha256(path.read_bytes()).hexdigest()==BASE
 old=TTFont(path,recalcTimestamp=False);jp=japanese_closure(old);gs=old.getGlyphSet();records={}
 for n in old.getGlyphOrder():
  p=DecomposingRecordingPen(gs);gs[n].draw(p);records[n]=p.value
 assert 'GPOS' not in old
 results={}
 for family,stem,yscale in FACES:
  f=copy.deepcopy(old);changes={};minbear=10000
  for n,rec in records.items():
   advance,lsb=old['hmtx'][n];newadvance={0:0,720:NARROW,1080:WIDE}[advance]
   sx,sy,dx=(1.,1.,(newadvance-advance)/2) if n in jp else (X,yscale,0.)
   pen=TTGlyphPen(None);tr=TransformPen(pen,(sx,0,0,sy,dx,0))
   for op,pts in rec:getattr(tr,op)(*pts)
   g=pen.glyph();g.recalcBounds(f['glyf']);f['glyf'][n]=g
   f['hmtx'][n]=(newadvance,getattr(g,'xMin',round(lsb*sx+dx)))
   if g.numberOfContours>0 and newadvance and n not in jp:
    minbear=min(minbear,g.xMin,newadvance-g.xMax)
   changes[n]=[sx,sy,dx]
  f=rename(f,family,['maplemono','kiwimaru']);f['post'].isFixedPitch=0;f['OS/2'].panose.bProportion=9
  for field in ['sxHeight','sCapHeight']:
   if hasattr(f['OS/2'],field):setattr(f['OS/2'],field,round(getattr(old['OS/2'],field)*yscale))
  if 'kern' in f:del f['kern']
  f.save(out/(stem+'.ttf'));f.flavor='woff2';f.save(out/(stem+'.woff2'))
  results[family]={'stem':stem,'Latin_matrix':[X,0,0,yscale,0,0],'advances':[0,NARROW,WIDE],'all_glyph_matrices':changes,'Western_glyphs':len(changes)-len(jp),'Japanese_fullwidth_and_closure':len(jp),'Japanese_narrow_cells':sum(old['hmtx'][n][0]==720 for n in jp),'minimum_Western_bearing':minbear,'Japanese':'Fullwidth advance1080 and all contours unchanged. Halfwidth cells720→540, contours translate-90 only.','Greek_five':'Inherited exact selective Greek5 geometry, then same Western affine; no new cap or Greek-wide reversion.'}
 notices=[(ROOT/'sources'/d/'OFL.txt').read_text().split('\n\n')[0].strip() for d in ['maplemono','kiwimaru']]
 license_text=(ROOT/'sources/maplemono/OFL.txt').read_text()
 (out/'OFL.txt').write_text('\n'.join(notices)+'\nCopyright 2026 The Morimo Prototype Contributors\n\n'+license_text[license_text.index('This Font Software'):])
 (out/'NOTICES.md').write_text('# Morimo Grid Small / Grid Tall Regular 0.001\n\n'+'\n'.join(notices)+'\n\nPinned Maple Mono v7.9 + Kiwi Maru sources; exact Greek5 derivative baseline. New names honor source naming restrictions. Small: Western x0.75/y0.75; Tall: x0.75/y1.0, baseline0. Both actual540/1080 advances. Fullwidth Japanese contours/advance unchanged. Halfwidth kana contours only centered in540 cells. Western accents, punctuation and marks use the matching whole affine. No installation, default change, terminal fork or mlterm setup. Native terminal behavior and sustained comfort unverified.\n')
 report={'baseline_sha256':BASE,'version':'0.001','families':results,'scope':'Actual fonts; preview only, no installation or replacement. Existing 18 fonts and installed prose preserved.'}
 (out/'build.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({k:{x:y for x,y in v.items() if x!='all_glyph_matrices'} for k,v in results.items()},ensure_ascii=False))
 return report
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output');build(p.parse_args().output)
