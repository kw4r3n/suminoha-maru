import copy,json,pathlib,unicodedata as ud,math
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.transformPen import TransformPen
from build import ROOT
from build_practical_refinement import version,save,sha
from build_code_latin_size import closure,BASE
from samples import ALPHABETS,MARK_SAMPLES
from hb import Shaper
OUT=ROOT/'inputs/code-common-size';CURRENT=ROOT/'inputs/code-latin-size/MorimoCodeZenLatin105-Regular.ttf'
def limit(f,n):
 g=f['glyf'][n];aw=f['hmtx'][n][0]
 if not g.numberOfContours:return 10.
 center=aw/2 if aw else (g.xMin+g.xMax)/2
 if '.liga' in n or '.seq' in n:low=min(0,math.floor(g.xMin/540)*540);high=max(aw,math.ceil(g.xMax/540)*540)
 elif aw and 0<=g.xMin<=g.xMax<=aw:low,high=0,aw
 else:low,high=g.xMin,g.xMax
 s=10.
 for edge,p in [(low,g.xMin),(high,g.xMax)]:
  if p!=center:s=min(s,(edge-center)/(p-center))
 return max(1.,s)
def build(output=None,targets=None):
 out=pathlib.Path(output or OUT);out.mkdir(parents=True,exist_ok=True);assert sha(CURRENT)=='a450dd2f76f4d50098618389ef7e6db4f5e6cd5c1e6e2d6aaee283fdf5b2672d'
 a=TTFont(BASE,recalcTimestamp=False);current=TTFont(CURRENT,recalcTimestamp=False);cm=a.getBestCmap()
 text=''.join(v for k,v in ALPHABETS.items() if k not in ['el','ru','ja'])+'àâäéèêëîïôöùûüÿçœæß';text+=text.upper();priority=set(range(32,127))|set(map(ord,text));priority&=set(cm)
 eligible=set(json.loads((ROOT/'inputs/code-latin-size/build.json').read_text())['105']['changed']);keep=closure(a,priority)&eligible
 # Never change an encoded rare character merely because layout closure touched it.
 keep-={n for cp,n in cm.items() if cp not in priority and n not in {cm[x] for x in priority}}
 families={}
 for cp in sorted(priority):
  n=cm[cp]
  if n not in keep or not chr(cp).isalpha():continue
  root=ud.normalize('NFD',chr(cp))[0];families[n]=root if root.isascii() else chr(cp)
 byname=dict(families)
 for n in keep:
  if n not in families and n.split('.')[0] in byname:families[n]=byname[n.split('.')[0]]
 sh=Shaper(BASE)
 for text in MARK_SAMPLES:
  if text[0].isascii():
   for row in sh.shape(text):
    if row['glyph'] in keep:families[row['glyph']]=text[0]
 report={}
 for factor,suffix in (targets or [(1.10,'110')]):
  f=copy.deepcopy(current);group={}
  for n,key in families.items():
   if n in {cm[cp] for cp in priority}:group[key]=min(group.get(key,factor),limit(a,n),factor)
  factors={};caps={}
  for n in sorted(keep):
   g=a['glyf'][n]
   if not g.numberOfContours:continue
   desired=group.get(families.get(n),factor);s=min(desired,limit(a,n));aw=a['hmtx'][n][0]
   # Do not shrink a current glyph while attempting enlargement.
   current_scale=json.loads((ROOT/'inputs/code-latin-size/build.json').read_text())['105']['caps'].get(n,1.05);s=max(s,current_scale)
   if s<factor-1e-8:caps[n]=s
   center=aw/2 if aw else (g.xMin+g.xMax)/2;rec=DecomposingRecordingPen(a.getGlyphSet());a.getGlyphSet()[n].draw(rec);p=TTGlyphPen(None);tr=TransformPen(p,(s,0,0,factor,center*(1-s),0))
   for op,pts in rec.value:getattr(tr,op)(*pts)
   z=p.glyph();z.recalcBounds(None);f['glyf'][n]=z;f['hmtx'][n]=(aw,z.xMin);factors[n]=[s,factor]
  fam='Morimo Code Zen Common '+suffix;stem='MorimoCodeZenCommon'+suffix+'-Regular'
  for r in list(f['name'].names):
   if r.nameID in [1,4,6,16,17]:f['name'].setName({1:fam,4:fam+' Regular',6:stem,16:fam,17:'Regular'}[r.nameID],r.nameID,r.platformID,r.platEncID,r.langID)
  version(f,'0.001','Preview common Latin ink targets; rare glyphs retained exact installed Latin105; fixed540/1080.');save(f,out,stem)
  common={chr(cp):factors.get(cm[cp],[1.05,1.05]) for cp in range(48,123) if chr(cp).isalnum() and cp in cm};report[suffix]={'target_relative_to_original_Zen':factor,'factors':factors,'caps':caps,'ASCII_letter_digit_factors':common,'priority_codepoints':sorted(priority),'coverage':len(cm),'policy':'Rare encoded forms exact installed105; Common group vertical scale shared across letters/digits/accents/relatedASCII closure. Horizontal growth independently capped, important accents grouped with ASCII base where possible; optional variants individually capped. Shared marks protected, normalNFC/NFD and bounded repairs tested. Baseline0, advance-centerX; original geometry scaled, no cumulative scaling.'}
 (out/'build.json').write_text(json.dumps(report,indent=2));(out/'OFL.txt').write_bytes((ROOT/'inputs/code-zen/OFL.txt').read_bytes());(out/'NOTICES.txt').write_text('Preview derivative of current installed cappedLatin105. CommonASCII and target French/German/Hungarian/Welsh/Vietnamese forms preferentially enlarged; rare glyphs preserved, no repertoire removal. Original Maple/Kiwi/Zen notices retained. No installation.\n');return report
if __name__=='__main__':build()
