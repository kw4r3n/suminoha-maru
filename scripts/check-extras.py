#!/usr/bin/env python3
import hashlib,json,unicodedata,tempfile
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen
from hb import Shaper
from code_extras import main,geometry
from samples import SAMPLES,MARK_SAMPLES
ROOT=Path(__file__).resolve().parents[1]
OPERATORS=['->','=>','!=','===','<=','>=','<-->','::','&&','||','...']
def check():
 report={'fonts':{},'repeat':{}}
 base=TTFont(ROOT/'inputs/dist/MorimoCodeGreek5-Regular.ttf');bc=base.getBestCmap();baseline=Shaper(ROOT/'inputs/dist/MorimoCodeGreek5-Regular.ttf')
 text='Árvíztűrő ŵŷ Ắằễộớựỹ ΈΉΌΎΏ Καλημέρα ЁЙЇ ЄҐ 日本語。'
 for stem in ['MorimoCodeLiga-Regular','MorimoCodeNerdSubset-Regular']:
  path=ROOT/'inputs/extras'/(stem+'.ttf');f=TTFont(path);sh=Shaper(path);gs=f.getGlyphSet();rows=[];y=[]
  for t in OPERATORS:
   on=sh.shape(t);off=sh.shape(t,features={'calt':0});assert [r['glyph'] for r in on]!=[r['glyph'] for r in off],(stem,t)
   assert sum(r['advance'] for r in on)==sum(r['advance'] for r in off)==720*len(t)
   x=0;lo=0;hi=0
   for r in on:
    p=BoundsPen(gs);gs[r['glyph']].draw(p)
    if p.bounds:
     lo=min(lo,x+r['dx']+p.bounds[0]);hi=max(hi,x+r['dx']+p.bounds[2]);y.extend([r['dy']+p.bounds[1],r['dy']+p.bounds[3]])
    x+=r['advance']
   assert lo>=-1 and hi<=x+1,(t,lo,hi,x)
   rows.append(dict(text=t,on=[r['glyph'] for r in on],off=[r['glyph'] for r in off],advance=x,ink_x=[lo,hi]))
  sig=lambda rr:[(r['glyph'],r['advance'],r['dx'],r['dy']) for r in rr]
  assert [(r['advance'],r['dx'],r['dy']) for r in sh.shape(text)]==[(r['advance'],r['dx'],r['dy']) for r in baseline.shape(text)]
  assert sig(sh.shape(text))==sig(sh.shape(unicodedata.normalize('NFD',text)))
  assert all(f['hmtx'][f.getBestCmap()[cp]][0]==base['hmtx'][n][0] for cp,n in bc.items())
  wf=TTFont(ROOT/'inputs/extras'/(stem+'.woff2'))
  assert f.getBestCmap()==wf.getBestCmap() and f['hmtx'].metrics==wf['hmtx'].metrics
  assert f['GSUB'].compile(f)==wf['GSUB'].compile(wf)
  for lang,(_,sample) in SAMPLES.items():
   assert sig(sh.shape(sample,lang))==sig(sh.shape(unicodedata.normalize('NFD',sample),lang))
   a=sh.shape(sample,lang,features={'calt':0});b=baseline.shape(sample,lang)
   assert len(a)==len(b)
   for x,z in zip(a,b):assert (x['advance'],x['dx'],x['dy'])==(z['advance'],z['dx'],z['dy']) and geometry(f,x['glyph'])==geometry(base,z['glyph'])
  for sample in MARK_SAMPLES:
   a=sh.shape(sample,features={'calt':0});b=baseline.shape(sample)
   assert len(a)==len(b)
   for x,z in zip(a,b):assert (x['advance'],x['dx'],x['dy'])==(z['advance'],z['dx'],z['dy']) and geometry(f,x['glyph'])==geometry(base,z['glyph'])
  icons={cp:n for cp,n in f.getBestCmap().items() if cp not in bc}
  for cp,n in icons.items():
   assert f['hmtx'][n][0]==720
   p=BoundsPen(gs);gs[n].draw(p)
   if p.bounds:
    assert p.bounds[0]>=9 and p.bounds[2]<=711,(n,p.bounds)
    y.extend(p.bounds[1::2])
   assert sh.shape(chr(cp))[0]['gid']!=0
  assert min(y)>=-400 and max(y)<=1300,(min(y),max(y))
  report['fonts'][stem]=dict(family=f['name'].getDebugName(1),postscript=f['name'].getDebugName(6),operators=rows,accent_mark_nfc_nfd='exact',unchanged_approved_text_shape='exact',base_advances='all preserved',icons=len(icons),icon_advance=720 if icons else None,all_p0_samples_nfc_nfd='pass; nine language samples',all_p0_vs_base_calt_off='exact contours and positions',mark_probes_vs_base='exact',ttf_woff2_cmap_metrics_gsub='exact',ink_y=[min(y),max(y)])
 with tempfile.TemporaryDirectory(prefix='morimo-extras-repeat-') as tmp:
  main(tmp)
  for path in sorted((ROOT/'inputs/extras').iterdir()):
   if path.suffix not in ['.ttf','.woff2','.json']:continue
   h=hashlib.sha256(path.read_bytes()).hexdigest();assert h==hashlib.sha256((Path(tmp)/path.name).read_bytes()).hexdigest(),path
   report['repeat'][path.name]=h
 (ROOT/'reports/code-extras.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'fonts':{k:{kk:vv for kk,vv in v.items() if kk!='operators'} for k,v in report['fonts'].items()},'repeat_files':len(report['repeat'])}))
if __name__=='__main__':check()
