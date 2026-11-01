import pathlib,json,sys,copy,collections
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
from fontTools.ttLib import TTFont
from fontTools import subset
from hb import Shaper
R=pathlib.Path(__file__).resolve().parents[1];src=TTFont(R/'sources/maplemono/MapleMono-Regular.ttf');cur=TTFont(R/'inputs/practical-refinement/MorimoCodeSmall-Regular.ttf');old=Shaper(R/'inputs/practical-refinement/MorimoCodeSmall-Regular.ttf');source=Shaper(R/'sources/maplemono/MapleMono-Regular.ttf')
features={}
for r in src['GSUB'].table.FeatureList.FeatureRecord:
 p=r.Feature.FeatureParams;features[r.FeatureTag]={'lookups':len(r.Feature.LookupListIndex),'label':src['name'].getDebugName(getattr(p,'UINameID',getattr(p,'FeatUILabelNameID',-1))) if p else None}
current=sorted({r.FeatureTag for r in cur['GSUB'].table.FeatureList.FeatureRecord});j={'state':'Pre-extension CodeSmall0.002 audit; superseded by code-features validation','pinned_source_features':features,'current_features':current,'missing_optional_features':sorted(set(features)-set(current)),'source_calt_top_lookups':features['calt']['lookups'],'current_calt_top_lookups':next(len(r.Feature.LookupListIndex) for r in cur['GSUB'].table.FeatureList.FeatureRecord if r.FeatureTag=='calt'),'previous_rendered_operator_cases':16,'note':'Lookup count is not a count of ligatures or supported strings. Default calt already imports126 top-level entries; optional ss/cv repertoire is excluded by old import whitelist.'};(R/'reports/code-feature-audit.json').write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n');print(json.dumps(j,ensure_ascii=False))
