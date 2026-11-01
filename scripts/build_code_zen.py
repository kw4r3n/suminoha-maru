import copy,json,pathlib,tempfile,shutil
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.transformPen import TransformPen
from build import ROOT,regular,japanese
from build_practical_refinement import version,save,sha
OUT=ROOT/'inputs/code-zen';STEM='MorimoCodeSmallZen-Regular';FAMILY='Morimo Code Small Zen'
def build(output=None):
 out=pathlib.Path(output or OUT);out.mkdir(parents=True,exist_ok=True)
 base=ROOT/'inputs/code-features/MorimoCodeSmall-Regular.ttf';source=ROOT/'inputs/prose-equal/MorimoProseZen-Regular.ttf'
 assert sha(base)=='a34d97cb430ca052536a7f2b0860cc650625ed5e02c0f030edede00629cd9448'
 assert sha(source)=='967a944dc6c41b7d360cc571894c63d090a0734c84b86bce45535e25a6aea791'
 f=TTFont(base,recalcTimestamp=False);p=TTFont(source);pc=p.getBestCmap();fc=f.getBestCmap();maple=set(regular('maplemono').getBestCmap());start=p.getGlyphOrder().index('.notdef.2');gs=p.getGlyphSet();changed=[];skipped=[]
 for cp,n in fc.items():
  if cp in maple or cp not in pc or p.getGlyphID(pc[cp])<start:continue
  aliases=[c for c,v in fc.items() if v==n]
  if any(c in maple for c in aliases):skipped.append(cp);continue
  aw=f['hmtx'][n][0];saw=p['hmtx'][pc[cp]][0];dx=(aw-saw)/2
  pen=TTGlyphPen(None);rec=DecomposingRecordingPen(gs);gs[pc[cp]].draw(rec);tr=TransformPen(pen,(1,0,0,1,dx,0))
  for op,pts in rec.value:getattr(tr,op)(*pts)
  g=pen.glyph();g.recalcBounds(None);f['glyf'][n]=g;f['hmtx'][n]=(aw,getattr(g,'xMin',0));changed.append({'cp':cp,'glyph':n,'source':pc[cp],'source_advance':saw,'code_advance':aw,'dx':dx,'dy':0})
 # Name only: retain original donor notices and feature graph; append Zen's copyright/OFL.
 for r in list(f['name'].names):
  if r.nameID in [1,4,6,16,17]:f['name'].setName({1:FAMILY,4:FAMILY+' Regular',6:STEM,16:FAMILY,17:'Regular'}[r.nameID],r.nameID,r.platformID,r.platEncID,r.langID)
 version(f,'0.001','Preview-only Zen500 Japanese over unchanged CodeSmall0.003.540/1080 grid; Western geometry/features retained.')
 save(f,out,STEM)
 (out/'OFL.txt').write_text((ROOT/'inputs/code-features/OFL.txt').read_text() if (ROOT/'inputs/code-features/OFL.txt').exists() else (ROOT/'inputs/code-features/Code-OFL.txt').read_text())
 with (out/'OFL.txt').open('a') as h:h.write('\n'+(ROOT/'sources/zenmarugothic/OFL.txt').read_text())
 (out/'NOTICES.txt').write_text('Morimo Code Small Zen preview0.001\nPinned Maple v7.9 and Kiwi: unchanged CodeSmall0.003 Western/Greek/features. Japanese encoded glyphs owned by prose0.007 Japanese subset use Zen500 and missing-only Kiwi500, including Zen-derived small kana. Source outlines scale1, baseline0; centered by half the advance delta into existing540/1080 cells. Maple-owned operators/punctuation excluded even if prose has another glyph. OFL1.1 notices retained. New family; no installation or implicit optional defaults. Use explicit feature list from specimen; external Nerd fallback separate.\n')
 report={'coverage':len(fc),'changed_encoded_glyphs':changed,'skipped_alias_conflicts':skipped,'source_sha256':sha(source),'base_sha256':sha(base),'source_Japanese_start_gid':start,'source_weights':500,'scale':1,'baseline':0,'advances':[0,540,1080],'features':'All original32 GSUB features retained; selected flags explicit in preview/Kitty; installed rule unchanged'}
 (out/'build.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');return report
if __name__=='__main__':build()
