#!/usr/bin/env python3
import json,pathlib,unicodedata as ud
from fontTools.ttLib import TTFont
from build import ROOT
from hb import Shaper
from code_feature_inventory import source_witnesses
from render_code_defaults import SELECTED,CANDIDATES
from render_code_features import CASES
from samples import SAMPLES,MARK_SAMPLES
from validate import ink_signature,signature
FONT=ROOT/'inputs/code-features/MorimoCodeSmall-Regular.ttf';SOURCE=ROOT/'sources/maplemono/MapleMono-Regular.ttf'
def main():
 f=TTFont(FONT);s=Shaper(FONT);source=Shaper(SOURCE);_,byfeature=source_witnesses(TTFont(SOURCE));alltext=sorted(set().union(*(byfeature[k] for k in SELECTED)));ys=[];candidateproof=[]
 for text in alltext:
  a=s.shape(text,features=SELECTED);b=source.shape(text,features=SELECTED);assert [v['glyph'] for v in a]==[v['glyph'] for v in b],text;assert sum(v['advance'] for v in a)==round(.9*sum(v['advance'] for v in b))
 for lang,(_,text) in SAMPLES.items():
  a=s.shape(text,lang,features=SELECTED);b=s.shape(ud.normalize('NFD',text),lang,features=SELECTED);assert signature(s,a)==signature(s,b),(lang,'NFC/NFD')
  assert signature(s,a)==signature(s,s.shape(text,lang)),(lang,'ordinary text changed')
 for text in MARK_SAMPLES:
  lang='ja' if ord(text[0])>0x3000 else 'en';assert signature(s,s.shape(text,lang,features=SELECTED))==signature(s,s.shape(text,lang)),text
 rows=s.shape('<= >=',features=SELECTED);assert all('cv63' not in r['glyph'] for r in rows) and any('cv64' in r['glyph'] for r in rows)
 for tag,label,text,state in CANDIDATES:
  a=s.shape(text,features=SELECTED|{tag:0});b=s.shape(text,features=SELECTED|{tag:1});assert [r['glyph'] for r in a]!=[r['glyph'] for r in b],(tag,text,'no candidate difference');assert [r['glyph'] for r in b]==[r['glyph'] for r in source.shape(text,features=SELECTED|{tag:1})];candidateproof.append({'feature':tag,'text':text,'state':state,'source_choice_matches':True})
 interaction=[]
 for tag,_,text in CASES[:9]:
  individual=s.shape(text,features={tag:0 if tag=='cv63' else 1});combined=s.shape(text,features=SELECTED)
  if [v['glyph'] for v in individual]!=[v['glyph'] for v in combined]:interaction.append({'row':tag,'text':text,'individual':[v['glyph'] for v in individual],'combined':[v['glyph'] for v in combined]})
 report={'selected':SELECTED,'source_interactions':interaction,'displayed_rows_only':True,'cv63':'OFF,no arrow; cv64 ON controls overlapping comparisons','collapsed_rows_not_enabled':['ss01','ss02','ss04','ss05'],'source_derived_combined_profile_tests':len(alltext),'candidate_previews':candidateproof,'font_bytes':'unchanged; source feature switches remain intact','limits':'Defaults are Linux per-face Fontconfig settings, not portable embedded TTF defaults. Actual Qt ignores these defaults; per-app feature settings required. Source finite witnesses are not all arbitrary strings.'};(ROOT/'reports/code-defaults-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':main()
