#!/usr/bin/env python3
import copy,json,pathlib,tempfile,unicodedata as ud,collections
from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import DecomposingRecordingPen
from build import ROOT
from build_code_features import build,BASE,OUT,FEATURES,CSTEM
from build_practical_refinement import sha
from code_feature_inventory import source_witnesses,feature_graphs
from hb import Shaper
from validate import ink_signature,shift_jis_repertoire
from samples import ALPHABETS,SAMPLES,MARK_SAMPLES
from render_code_features import CASES
NEGATIVE=['a < b','x > y','foo<T>','Array<Array<T>>','std::vector<std::vector<int>>','a->b','TODO Todo todo NOTE FIXME DEBUG','0xFF 0XAA 0b1010 10x10 0xyz 0x','## ### ---- ...','\\n \\t \\\\ \\u1234','<$> <|> <*> >>= =<< >=> <=<','::<T> ${x} #{x}','|> <| #(','(?<=a)b',';;; ;; // /* */']
BUNDLES=[{'ss08':1,'cv66':1},{'ss09':1,'ss10':1},{'ss11':1,'cv63':1},{'ss01':1,'ss02':1,'ss04':1}]
def names(rows):return [r['glyph'] for r in rows]
def geom(f,n):
 p=DecomposingRecordingPen(f.getGlyphSet());f.getGlyphSet()[n].draw(p);return p.value,f['hmtx'][n]
def main():
 srcpath=ROOT/'sources/maplemono/MapleMono-Regular.ttf';src=TTFont(srcpath);old=TTFont(BASE/(CSTEM+'.ttf'));f=TTFont(OUT/(CSTEM+'.ttf'));sh=Shaper(OUT/(CSTEM+'.ttf'));source=Shaper(srcpath);before=Shaper(BASE/(CSTEM+'.ttf'));assert f.getBestCmap()==old.getBestCmap()
 for n in old.getGlyphOrder():assert geom(old,n)==geom(f,n),(n,'old geometry changed')
 assert set(v[0] for v in f['hmtx'].metrics.values())<={0,540,1080}
 assert (f['hhea'].ascent,f['hhea'].descent,f['hhea'].lineGap)==(1200,-350,0)
 for lang,chars in ALPHABETS.items():assert not set(map(ord,chars+chars.upper()))-set(f.getBestCmap()),lang
 assert not shift_jis_repertoire()-set(f.getBestCmap())
 for lang,(_,text) in SAMPLES.items():
  assert ink_signature(sh,text,lang)==ink_signature(before,text,lang),(lang,'default changed')
  assert ink_signature(sh,text,lang)==ink_signature(sh,ud.normalize('NFD',text),lang),(lang,'NFC/NFD')
 for text in MARK_SAMPLES+['α\u0301\u0308','ω\u0308','Η\u0301','n\u0303\u0301','Α\u0308','Ω\u0308','x\u0302\u0301','a\u030b','q\u0308']:
  lang='ja' if ord(text[0])>0x3000 else 'el' if ord(text[0])>0x300 else 'en';assert ink_signature(sh,text,lang)==ink_signature(before,text,lang),text
 # Compare semantic source graph after only explicit non-programming/italic filtering.
 selected=copy.deepcopy(src)
 for t in selected['cmap'].tables:
  if t.isUnicode():t.cmap[0x212b]=t.cmap[0xc5]
 o=subset.Options();o.layout_features=FEATURES;sub=subset.Subsetter(options=o);sub.populate(unicodes=set(selected.getBestCmap()));sub.subset(selected)
 graphfont=copy.deepcopy(f)
 for rec in graphfont['GSUB'].table.FeatureList.FeatureRecord:
  if rec.FeatureTag=='ccmp':rec.Feature.LookupListIndex=rec.Feature.LookupListIndex[:-1]
 a,b=feature_graphs(selected),feature_graphs(graphfont);assert a==b,'Applicable source GSUB graph changed'
 # UI names remain available to feature selectors after derivative renaming.
 labels={}
 for rec in f['GSUB'].table.FeatureList.FeatureRecord:
  p=rec.Feature.FeatureParams
  if p:
   label=f['name'].getDebugName(getattr(p,'UINameID',getattr(p,'FeatUILabelNameID',-1)));assert label,rec.FeatureTag;labels[rec.FeatureTag]=label
 _,witnesses=source_witnesses(src);alltext=sorted(set().union(*(witnesses[k] for k in FEATURES)));features={};count=0;totalchanged=0;examples={};gs=f.getGlyphSet();ys=[];overhang=[]
 for text in alltext+NEGATIVE:
  assert names(sh.shape(text))==names(before.shape(text)),('default repertoire change',text)
 for feature in FEATURES:
  cases=sorted(witnesses[feature]|{text for tag,_,text in CASES if tag==feature});changed=0;shown=[]
  for text in cases:
   opts={} if feature in ['calt','ccmp','locl'] else {feature:1};actual=sh.shape(text,features=opts);expected=source.shape(text,features=opts);assert names(actual)==names(expected),(feature,text,names(actual),names(expected));assert all(r['gid'] for r in actual)
   assert sum(r['advance'] for r in actual)==round(sum(r['advance'] for r in expected)*.9),(feature,text,'advance')
   different=names(actual)!=names(sh.shape(text,features={feature:0}))
   if different:
    changed+=1
    if len(shown)<12:shown.append(text)
   x=0;lo=0;hi=0
   for row in actual:
    pen=BoundsPen(gs);gs[row['glyph']].draw(pen)
    if pen.bounds:ys.extend([pen.bounds[1]+row['dy'],pen.bounds[3]+row['dy']]);lo=min(lo,x+row['dx']+pen.bounds[0]);hi=max(hi,x+row['dx']+pen.bounds[2])
    x+=row['advance']
   if lo<0 or hi>x:overhang.append({'feature':feature,'text':text,'left':lo,'right':hi-x})
  features[feature]={'source_derived_cases':len(cases),'observed_feature_changes':changed,'examples':shown};count+=len(cases);totalchanged+=changed
 for opts in BUNDLES:
  for text in alltext+NEGATIVE:assert names(sh.shape(text,features=opts))==names(source.shape(text,features=opts)),(opts,text,'feature combination')
 for text in ['0','0O 1lI','1001','0xFF','0b10','00.10']:
  for opts in [{}, {'zero':1}]+[{k:1} for k in FEATURES if k not in ['ccmp','locl']]:
   rows=sh.shape(text,features=opts);zero=[r for r in rows if r['glyph'] in ['zero','zero.zero']];assert len(zero)==text.count('0'),(text,opts)
   for row in zero:assert geom(f,row['glyph'])==geom(old,old.getBestCmap()[48]),('dot changed',text,opts)
 assert min(ys)>=-350 and max(ys)<=1200,(min(ys),max(ys))
 for n in f.getGlyphOrder():
  g=f['glyf'][n]
  if g.numberOfContours:assert g.yMin>=-350 and g.yMax<=1200,(n,'glyph vertical bounds')
 w=TTFont(OUT/(CSTEM+'.woff2'));assert f.getBestCmap()==w.getBestCmap() and f['hmtx'].metrics==w['hmtx'].metrics
 for tag in ['GSUB','GDEF']:assert f[tag].compile(f)==w[tag].compile(w)
 report={'coverage':len(f.getBestCmap()),'preserved_default_glyphs':len(old.getGlyphOrder()),'new_glyphs':len(f.getGlyphOrder())-len(old.getGlyphOrder()),'applicable_source_feature_graphs_exact':len(a),'features':features,'source_feature_labels':labels,'unique_source_derived_strings':len(alltext),'individual_feature_shape_comparisons':count,'case_inventory':'Source-derived witnesses plus13 verified donor-feature demonstration rows','feature_bundle_shape_comparisons':len(BUNDLES)*(len(alltext)+len(NEGATIVE)),'negative_contexts':NEGATIVE,'default_repertoire_matches_old':True,'tested_ink_y':[min(ys),max(ys)],'observed_horizontal_overhang':overhang,'all_existing_marks_and_default_dotted0_preserved':True,'repeat':{},'limits':'Finite source-derived witnesses and graph preservation, not exhaustive arbitrary strings/language grammar. Optional features require app settings and stay off by default. Italic-only and fraction/super/subscript/aalt typography excluded explicitly.'}
 with tempfile.TemporaryDirectory(prefix='morimo-code-feature-repeat-') as tmp:
  build(tmp)
  for p in OUT.iterdir():assert sha(p)==sha(pathlib.Path(tmp)/p.name),p.name;report['repeat'][p.name]=sha(p)
 (ROOT/'reports/code-features-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ['features','source_feature_labels','observed_horizontal_overhang','repeat','negative_contexts']}))
if __name__=='__main__':main()
