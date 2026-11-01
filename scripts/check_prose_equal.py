import json,tempfile,pathlib,unicodedata as ud
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import DecomposingRecordingPen
from build_prose_equal import build,ROOT,OUT,BASE,PSTEM,sha
from hb import Shaper
from validate import ink_signature,shift_jis_repertoire
from samples import ALPHABETS,SAMPLES,MARK_SAMPLES
f=TTFont(OUT/(PSTEM+'.ttf'));medium=TTFont(BASE/(PSTEM+'.ttf'));b=medium
assert f.getBestCmap()==b.getBestCmap() and len(f.getBestCmap())==9205
assert f.getGlyphOrder()==b.getGlyphOrder()
def geom(font,n):
 p=DecomposingRecordingPen(font.getGlyphSet());font.getGlyphSet()[n].draw(p);return p.value,font['hmtx'][n]
# Greek is between Nunito's1093 glyphs and Japanese. All Japanese+gap glyphs must remain exact genuine Medium.
start=medium.getGlyphOrder().index('.notdef.2')
for n in f.getGlyphOrder()[start:]:assert geom(f,n)==geom(medium,n),n
s=Shaper(OUT/(PSTEM+'.ttf'));widths={}
for lang,(_,text) in SAMPLES.items():
 assert all(r['gid'] for r in s.shape(text,lang)),lang
 assert ink_signature(s,text,lang)==ink_signature(s,ud.normalize('NFD',text),lang),lang
 widths[lang]=sum(r['advance'] for r in s.shape(text,lang))
for lang,chars in ALPHABETS.items():assert not set(map(ord,chars+chars.upper()))-set(f.getBestCmap()),lang
assert not shift_jis_repertoire()-set(f.getBestCmap())
for text in MARK_SAMPLES:assert all(v['gid'] for v in s.shape(text)),text
for n in f.getGlyphOrder():
 g=f['glyf'][n]
 if g.numberOfContours:assert g.yMin>=-350 and g.yMax<=1150,(n,'bounds')
w=TTFont(OUT/(PSTEM+'.woff2'));assert f.getBestCmap()==w.getBestCmap() and f['hmtx'].metrics==w['hmtx'].metrics
for tag in ['GSUB','GPOS','GDEF']:assert f[tag].compile(f)==w[tag].compile(w)
with tempfile.TemporaryDirectory(prefix='morimo-equal-repeat-') as t:
 build(t)
 for p in OUT.iterdir():assert sha(p)==sha(pathlib.Path(t)/p.name),p.name
report={'coverage':9205,'all_genuine_weights':500,'Japanese_glyphs_exact_Medium_baseline':len(f.getGlyphOrder())-start,'NFC_NFD_P0_samples':'pass','mark_samples':'all nonzero; inherited arbitrary-mark limits remain','vertical_bounds':'all ink inside1150/-350','TTF_WOFF2_layout_equivalent':True,'repeat':'all five files byte-identical','sample_widths':widths,'limits':'Inherited U0230/U0231/U1E1D and compatibility normalization differences; no Chinese regional/IVS support; numeric500 does not imply equal perceived darkness.'}
(ROOT/'reports/prose-equal-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
