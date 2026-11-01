#!/usr/bin/env python3
"""Bounded coverage delta for the selected Japanese donor; no Chinese expansion."""
import collections,json
from fontTools.ttLib import TTFont
from fontTools.unicodedata import script
from build import ROOT
from validate import ranges,shift_jis_repertoire
from samples import ALPHABETS
old=set(TTFont(ROOT/'inputs/prose/MorimoProse-Regular.ttf').getBestCmap());new=set(TTFont(ROOT/'inputs/prose-zen/MorimoProseZen-Regular.ttf').getBestCmap());removed=old-new;added=new-old
p0=shift_jis_repertoire()|{ord(c) for text in ALPHABETS.values() for c in text+text.upper()};assert not p0-new
assert not {cp for cp in old if script(cp) in ['Latn','Grek','Cyrl']}-new
result={'previous_Nunito400_Kiwi_cmap':len(old),'selected_Nunito550_Zen_cmap':len(new),'removed_count':len(removed),'added_count':len(added),'removed_by_script':dict(collections.Counter(script(cp) for cp in removed)),'added_by_script':dict(collections.Counter(script(cp) for cp in added)),'removed_ranges':ranges(removed),'added_ranges':ranges(added),'bounded_P0_missing':[],'Latin_Greek_Cyrillic_encoded_coverage_preserved':True,'limits':'Extra Japanese/symbol coverage differs by donor. This is not complete Unicode, IVS or full SC/TC/localization support; only bounded horizontal P0 is tested.'}
(ROOT/'reports/prose-zen-coverage-delta.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if not k.endswith('_ranges')},ensure_ascii=False))
