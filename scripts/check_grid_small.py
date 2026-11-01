#!/usr/bin/env python3
import hashlib,json,pathlib,tempfile,unicodedata
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.transformPen import TransformPen
from build import ROOT,japanese
from build_grid_small import build,FACES,NARROW,WIDE
from validate import ink_signature,shift_jis_repertoire
from samples import ALPHABETS,SAMPLES,MARK_SAMPLES
from hb import Shaper

def main():
 old=TTFont(ROOT/'inputs/dist/MorimoCodeGreek5-Regular.ttf');base=Shaper(ROOT/'inputs/dist/MorimoCodeGreek5-Regular.ttf');r=json.loads((ROOT/'inputs/grid-small/build.json').read_text());proof={}
 for family,stem,yscale in FACES:
  p=ROOT/'inputs/grid-small'/(stem+'.ttf');f=TTFont(p);sh=Shaper(p);c=f.getBestCmap();d=r['families'][family];matrices=d['all_glyph_matrices'];tests={}
  assert c==old.getBestCmap() and f.getGlyphOrder()==old.getGlyphOrder()
  assert f['GSUB'].compile(f)==old['GSUB'].compile(old) and 'GPOS' not in f
  for lang,text in ALPHABETS.items():assert not set(map(ord,text+text.upper()))-set(c),(family,lang,'coverage')
  assert not shift_jis_repertoire()-set(c)
  widths={a for a,b in f['hmtx'].metrics.values()};assert widths=={0,NARROW,WIDE}
  gs=old.getGlyphSet();jp_count=0;minimum=10000
  for n in f.getGlyphOrder():
   sx,sy,dx=matrices[n];pen=DecomposingRecordingPen(gs);gs[n].draw(pen);expected=TTGlyphPen(None);tr=TransformPen(expected,(sx,0,0,sy,dx,0))
   for op,pts in pen.value:getattr(tr,op)(*pts)
   g=expected.glyph();g.recalcBounds(f['glyf']);actual=f['glyf'][n]
   assert list(g.getCoordinates(f['glyf'])[0])==list(actual.getCoordinates(f['glyf'])[0]),(n,'affine')
   assert f['hmtx'][n][0]=={0:0,720:NARROW,1080:WIDE}[old['hmtx'][n][0]]
   if old['hmtx'][n][0]==WIDE:assert [sx,sy,dx]==[1,1,0];jp_count+=1
   if sx==.75 and actual.numberOfContours>0 and f['hmtx'][n][0]:minimum=min(minimum,actual.xMin,f['hmtx'][n][0]-actual.xMax)
  for cp,n in c.items():
   if japanese(cp):assert matrices[n][:2]==[1,1],(family,hex(cp),'Japanese scaled')
  sig=lambda rr:[(x['gid'],x['advance'],x['dx'],x['dy']) for x in rr]
  for lang,(_,text) in SAMPLES.items():
   a=sh.shape(text,lang);b=sh.shape(unicodedata.normalize('NFD',text),lang);assert all(x['gid'] for x in a+b);assert sig(a)==sig(b),(family,lang,'NFC/NFD');tests[lang]='zero missing, exact NFC/NFD'
  marks=[]
  for text in MARK_SAMPLES:
   jp=ord(text[0])>0x3000;lang='ja' if jp else 'en';a=ink_signature(sh,text,lang);b=ink_signature(base,text,lang);sx,sy=(1,1) if jp else (.75,yscale)
   assert len(a)==len(b),(family,text,'contours');xerror=yerror=0
   for (op,pts),(eop,epts) in zip(a,b):
    assert op==eop
    for v,w in zip(pts,epts):
     if v is None or w is None:assert v is w
     else:xerror=max(xerror,abs(v[0]-w[0]*sx));yerror=max(yerror,abs(v[1]-w[1]*sy))
   assert xerror<=2,(family,text,'mark x alignment',xerror)
   if jp or yscale==1:assert yerror<=2,(family,text,'mark affine error',yerror)
   # Small retains HarfBuzz's fixed em-based fallback gap. Record the strict
   # whole-run affine failure rather than silently widening its old tolerance.
   rows=sh.shape(text,lang);positioned=[]
   for row in rows:
    pen=BoundsPen(f.getGlyphSet());f.getGlyphSet()[row['glyph']].draw(pen)
    if pen.bounds:
     ymin=pen.bounds[1]+row['dy'];ymax=pen.bounds[3]+row['dy']
     assert ymin>=-400 and ymax<=1300,(family,text,'positioned mark clipping')
     positioned.append([row['glyph'],ymin,ymax])
   if not jp and len(rows)>1:
    assert all(positioned[i][1]>=positioned[i-1][2] for i in range(1,len(positioned))),(family,text,'above marks overlap')
   marks.append({'text':text,'max_x_affine_error':xerror,'max_y_affine_error':yerror,'strict_affine_within_2':max(xerror,yerror)<=2,'scale':[sx,sy],'positioned_y_bounds':positioned})
  for cp,n in c.items():
   if (0x20<=cp<=0x7e or unicodedata.category(chr(cp)).startswith('L') and not japanese(cp)) and f['hmtx'][n][0]==NARROW:
    g=f['glyf'][n]
    if hasattr(g,'xMax'):assert g.xMin>=0 and g.xMax<=NARROW,(family,hex(cp),'letter/ASCII ink bounds')
  for text in ['0O1lI[]{}()<>!=+-*/.,:;_','ŐőŰűŴŵŶŷΈΉΌΎΏ','АБВГДЕЁЖЗИЙ']:
   assert all(x['advance']==NARROW for x in sh.shape(text))
  for text in ['丸文字日本語東京京都あいうえお','１２３ＡＢＣ［］「」。、']:assert all(x['advance']==WIDE for x in sh.shape(text,'ja'))
  assert all(x['advance']==NARROW for x in sh.shape('ｱｲｳｴｵ','ja'))
  assert f['head'].yMin>=-400 and f['head'].yMax<=1300
  w=TTFont(p.with_suffix('.woff2'));assert w.getBestCmap()==c and w['hmtx'].metrics==f['hmtx'].metrics
  for tag in ['GSUB','GDEF']:assert w[tag].compile(w)==f[tag].compile(f)
  assert f['name'].getDebugName(1)==family and f['post'].isFixedPitch==0 and f['OS/2'].panose.bProportion==9
  proof[family]={'advances':sorted(widths),'glyph_affines':len(matrices),'fullwidth_outlines_exact':jp_count,'NFC_NFD':tests,'marks':marks,'minimum_Western_bearing':minimum,'bearing_limit':'Inherited connecting-arrow overhangs15 units per side and two unencoded helper overhangs; P0 letters and ASCII punctuation tested separately','bounds':[f['head'].xMin,f['head'].yMin,f['head'].xMax,f['head'].yMax],'no_missing_ShiftJIS':6879,'source_GSUB_exact':True}
 for rel,want in json.loads((ROOT/'inputs/preservation/prose-three-preserved.json').read_text()).items():
  p=ROOT/rel;assert hashlib.sha256(p.read_bytes()).hexdigest()==want,rel
 with tempfile.TemporaryDirectory(prefix='morimo-small-repeat-') as tmp:
  build(tmp);repeat={}
  for p in (ROOT/'inputs/grid-small').iterdir():
   h=hashlib.sha256(p.read_bytes()).hexdigest();assert h==hashlib.sha256((pathlib.Path(tmp)/p.name).read_bytes()).hexdigest(),p.name;repeat[p.name]=h
 result={'fonts':proof,'repeat':repeat,'retained_project_font_hashes_preserved':True,'limits':'Uniform Small does not meet the earlier strict whole-run affine mark gate: HarfBuzz fallback y_gap remains font y_scale/16. Actual offsets/clear gaps/bounds are recorded, not hidden by increasing the old tolerance. Existing connecting-arrow/helper overhangs scale with source; native terminal behavior untested. No installation, fork or mlterm test.'}
 (ROOT/'reports/grid-small.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
