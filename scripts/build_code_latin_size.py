import copy,json,pathlib,tempfile,math
from fontTools.ttLib import TTFont
from fontTools import subset
from fontTools.unicodedata import script
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.transformPen import TransformPen
from build import ROOT
from build_practical_refinement import version,save,sha
OUT=ROOT/'inputs/code-latin-size';BASE=ROOT/'inputs/code-zen/MorimoCodeSmallZen-Regular.ttf'
def closure(f,cps):
 g=copy.deepcopy(f);o=subset.Options();o.layout_features=['*'];s=subset.Subsetter(options=o);s.populate(unicodes=cps);s.subset(g);return set(g.getGlyphOrder())
def build(output=None):
 out=pathlib.Path(output or OUT);out.mkdir(parents=True,exist_ok=True);assert sha(BASE)=='65011dba377c2336050e5dfc3b9f054ba17913df71e89c5e3b486cdfba8cff36'
 a=TTFont(BASE,recalcTimestamp=False);c=a.getBestCmap();marks={p for p in c if script(p) in ['Zinh']};latin={p for p in c if script(p)=='Latn' or 0x20<=p<=0x7e};keep=closure(a,latin|marks);protected=closure(a,{p for p in c if script(p) in ['Grek','Cyrl']}|marks);keep-=protected;keep.discard('.notdef')
 # Only source Western closure, never Japanese ownership. Exclude any encoded Japanese glyph regardless of layout closure.
 keep-={n for p,n in c.items() if script(p) in ['Hani','Hira','Kana','Hang'] or 0xff00<=p<=0xffef}
 records={}
 for n in sorted(keep):
  p=DecomposingRecordingPen(a.getGlyphSet());a.getGlyphSet()[n].draw(p);records[n]=p.value
 result={}
 for factor,suffix in [(1.05,'105')]:
  f=copy.deepcopy(a);caps={};changed=[]
  for n,rec in records.items():
   g=a['glyf'][n];aw=a['hmtx'][n][0]
   if not g.numberOfContours:continue
   center=aw/2 if aw else (g.xMin+g.xMax)/2;s=factor
   if '.liga' in n or '.seq' in n:
    low=min(0,math.floor(g.xMin/540)*540);high=max(aw,math.ceil(g.xMax/540)*540)
   elif aw and 0<=g.xMin<=g.xMax<=aw:low,high=0,aw
   else:low,high=g.xMin,g.xMax
   for edge,point in [(low,g.xMin),(high,g.xMax)]:
    d=point-center
    if d:s=min(s,(edge-center)/d)
   s=max(1.,s)
   if s<factor-1e-8:caps[n]=s
   pen=TTGlyphPen(None);tr=TransformPen(pen,(s,0,0,s,center*(1-s),0))
   for op,pts in rec:getattr(tr,op)(*pts)
   z=pen.glyph();z.recalcBounds(None);f['glyf'][n]=z;f['hmtx'][n]=(aw,z.xMin);changed.append(n)
  family='Morimo Code Zen Latin '+suffix;stem='MorimoCodeZenLatin'+suffix+'-Regular'
  for r in list(f['name'].names):
   if r.nameID in [1,4,6,16,17]:f['name'].setName({1:family,4:family+' Regular',6:stem,16:family,17:'Regular'}[r.nameID],r.nameID,r.platformID,r.platEncID,r.langID)
  version(f,'0.001','Preview Latin/ASCII code glyph ink enlargement only; protected Greek/Cyrillic/Japanese and shared marks unchanged; safety caps.');save(f,out,stem)
  result[suffix]={'factor':factor,'changed':changed,'caps':caps,'shared_marks':'Preserved to protect Greek/Cyrillic; composed Latin/NFD and existing boundedccmp transformed whole. Arbitrary noncomposable marks not newly repaired.','origin':'baseline y0; advance center x; zero-advance contextual glyph ink center','coverage':len(c)}
 (out/'build.json').write_text(json.dumps(result,indent=2));(out/'OFL.txt').write_bytes((ROOT/'inputs/code-zen/OFL.txt').read_bytes());(out/'NOTICES.txt').write_text('Preview derivatives of pinned current CodeSmallZen. Only Latin/ASCII and associated GSUB closure ink scaled; Japanese/Greek/Cyrillic/shared marks protected. Source notices retained. No install/default changes.\n');return result
if __name__=='__main__':build()
