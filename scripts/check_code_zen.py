import json,tempfile,pathlib,unicodedata as ud
from fontTools.ttLib import TTFont
from build_code_zen import *
from hb import Shaper
from validate import ink_signature
from samples import SAMPLES
f=TTFont(OUT/(STEM+'.ttf'));old=TTFont(ROOT/'inputs/code-features/MorimoCodeSmall-Regular.ttf');r=json.loads((OUT/'build.json').read_text());changed={x['glyph'] for x in r['changed_encoded_glyphs']}
assert old.getBestCmap()==f.getBestCmap()
for n in old.getGlyphOrder():
 assert old['hmtx'][n][0]==f['hmtx'][n][0]
 if n not in changed:assert old['glyf'][n].compile(old['glyf'])==f['glyf'][n].compile(f['glyf']) and old['hmtx'][n]==f['hmtx'][n]
for tag in ['GSUB','GDEF']:assert old[tag].compile(old)==f[tag].compile(f)
s=Shaper(OUT/(STEM+'.ttf'))
for lang,(_,t) in SAMPLES.items():assert all(x['gid'] for x in s.shape(t,lang));assert ink_signature(s,t,lang)==ink_signature(s,ud.normalize('NFD',t),lang),lang
bounds=[]
for n in changed:
 g=f['glyf'][n];aw=f['hmtx'][n][0]
 if g.numberOfContours:
  assert g.yMin>=-350 and g.yMax<=1200,n
  if g.xMin<0 or g.xMax>aw:bounds.append(n)
with tempfile.TemporaryDirectory(prefix='morimo-codezen-repeat-') as t:
 build(t)
 for p in OUT.iterdir():assert sha(p)==sha(pathlib.Path(t)/p.name),p.name
(ROOT/'reports/code-zen-validation.json').write_text(json.dumps({'coverage':len(f.getBestCmap()),'changed_glyphs':len(changed),'unchanged_other_glyphs':len(f.getGlyphOrder())-len(changed),'GSUB_GDEF_exact':True,'all_advances_exact':True,'P0_NFC_NFD':'pass','vertical_bounds':'pass','horizontal_overhangs':bounds,'repeat':'five files identical'},indent=2))
