import json,unicodedata as ud
from fontTools.ttLib import TTFont
from build_code_common_size import *
from hb import Shaper
from validate import ink_signature
from samples import SAMPLES
from render_code_defaults import SELECTED
r=json.loads((OUT/'build.json').read_text());a=TTFont(CURRENT);reports={}
for key,row in r.items():
 f=TTFont(OUT/('MorimoCodeZenCommon'+key+'-Regular.ttf'));changed=set(row['factors']);assert a.getBestCmap()==f.getBestCmap()
 for n in a.getGlyphOrder():
  assert a['hmtx'][n][0]==f['hmtx'][n][0]
  if n not in changed:assert a['glyf'][n].compile(a['glyf'])==f['glyf'][n].compile(f['glyf']) and a['hmtx'][n]==f['hmtx'][n]
 for tag in ['GSUB','GDEF']:assert a[tag].compile(a)==f[tag].compile(f)
 s=Shaper(OUT/('MorimoCodeZenCommon'+key+'-Regular.ttf'));old=Shaper(CURRENT)
 for lang,(_,t) in SAMPLES.items():assert ink_signature(s,t,lang)==ink_signature(s,ud.normalize('NFD',t),lang),lang
 extra=['Français: déjà Noël, où ça? cœur æther.','Deutsch: Grüße, Straße, ÄÖÜ äöü.','WWMM WWWWW mmmmm minimumWidth maximumMemory','0O1lI 0123456789','q\u0308 x\u0302\u0301 a\u030b','!= !== === => -> >>= =<< |> <| \\n \\t']
 for t in extra:assert ink_signature(s,t,'en')==ink_signature(s,ud.normalize('NFD',t),'en');assert old.shape(t,features=SELECTED)==s.shape(t,features=SELECTED)
 for t,lang in [('日本語 とど カタカナ','ja'),('αβγ ΈΉΌΎΏ','el'),('ЁЙЇ','ru')]:assert ink_signature(s,t,lang)==ink_signature(old,t,lang)
 for n,xy in row['factors'].items():
  assert xy[1]==row['target_relative_to_original_Zen'];g=f['glyf'][n]
  if g.numberOfContours:assert -350<=g.yMin<g.yMax<=1200,n
 reports[key]={'coverage':len(f.getBestCmap()),'priority_glyphs':len(changed),'rare_other_glyphs_exact':len(f.getGlyphOrder())-len(changed),'shared_Y':row['target_relative_to_original_Zen'],'horizontal_caps':len(row['caps']),'ASCII_factors':row['ASCII_letter_digit_factors'],'P0_French_German_NFC_NFD':'pass','all_advances_features_positions':'exact','protected_scripts':'exact','vertical_bounds':'pass','arbitrary_shared_marks':'unchanged, inherited limits'}
(ROOT/'reports/code-common-size-validation.json').write_text(json.dumps(reports,indent=2));print({k:{x:y for x,y in v.items() if x!='ASCII_factors'} for k,v in reports.items()})
