import sys,copy,json,hashlib,shutil
sys.path.insert(0,'scripts')
from build import ROOT
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.transformPen import TransformPen
from build_practical_refinement import save,version
from hb import Shaper
from validate import ink_signature
out=ROOT/'inputs/code-jp-size';out.mkdir(exist_ok=True)
base=ROOT/'inputs/code-topdown/MorimoCodeZenCommonT95-Regular.ttf'
a=TTFont(base,recalcTimestamp=False)
names={r['glyph'] for r in json.loads((ROOT/'inputs/code-zen/build.json').read_text())['changed_encoded_glyphs']}
report={}
for scale,suffix in [(0.95,'95')]:
 f=copy.deepcopy(a);gs=a.getGlyphSet()
 for n in names:
  aw=a['hmtx'][n][0];center=270 if aw==540 else 540
  rec=DecomposingRecordingPen(gs);gs[n].draw(rec);p=TTGlyphPen(None);tr=TransformPen(p,(scale,0,0,scale,center*(1-scale),500*(1-scale)))
  for op,pts in rec.value:getattr(tr,op)(*pts)
  g=p.glyph();g.recalcBounds(None);f['glyf'][n]=g;f['hmtx'][n]=(aw,getattr(g,'xMin',0))
 family='Morimo Code Latin1216 JP'+suffix;stem='MorimoCodeLatin1216JP'+suffix+'-Regular'
 for r in list(f['name'].names):
  if r.nameID in [1,4,6,16,17]:f['name'].setName({1:family,4:family+' Regular',6:stem,16:family,17:'Regular'}[r.nameID],r.nameID,r.platformID,r.platEncID,r.langID)
 version(f,'0.001','Preview Japanese ink scale '+suffix+'%; fixed advances.');save(f,out,stem)
 b=TTFont(out/(stem+'.ttf'));assert b.getBestCmap()==a.getBestCmap()
 for n in a.getGlyphOrder():
  assert b['hmtx'][n][0]==a['hmtx'][n][0]
  if n not in names:assert b['glyf'][n].compile(b['glyf'])==a['glyf'][n].compile(a['glyf']) and b['hmtx'][n]==a['hmtx'][n]
 for tag in ['GSUB','GPOS','GDEF']:
  if tag in a:assert b[tag].compile(b)==a[tag].compile(a)
 sh=Shaper(out/(stem+'.ttf'));pairs=[('ど','と\u3099'),('が','か\u3099'),('ぽ','ほ\u309a'),('ヴ','ウ\u3099')]
 for x,y in pairs:assert ink_signature(sh,x,'ja')==ink_signature(sh,y,'ja'),(suffix,x,y)
 bounds=[min(getattr(g,'yMin',0) for g in b['glyf'].glyphs.values()),max(getattr(g,'yMax',0) for g in b['glyf'].glyphs.values())]
 assert bounds[0]>=-350 and bounds[1]<=1200,bounds
 report[suffix]={'Japanese_ink_scale':scale,'Latin_vertical_scale':1.216,'Japanese_glyphs':len(names),'coverage':len(b.getBestCmap()),'bounds':bounds,'unchanged_nonJapanese_and_layout':True,'canonical_voiced_pairs_pass':len(pairs),'transform':'uniform about x540(full/zero),270(half),y500; advances preserved; Japanese sidebearings increase'}
(out/'validation.json').write_text(json.dumps(report,indent=2))
for name in ['OFL.txt','NOTICES.txt']:shutil.copyfile(ROOT/'inputs/code-topdown'/name,out/name)
print(json.dumps(report))
