#!/usr/bin/env python3
"""Selected Small: default upstream dotted zero and bounded source-derived ccmp accents."""
import argparse,copy,hashlib,json,pathlib,unicodedata
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.transformPen import TransformPen
from fontTools.otlLib.builder import buildLigatureSubstSubtable,buildLookup
from build import ROOT,rename
from hb import Shaper
FAMILY='Morimo Code Small';STEM='MorimoCodeSmall-Regular'
SEQUENCES=['x\u0302\u0301','x\u0302','q\u0308','a\u030b','α\u0308']
SEQUENCES+= [s.upper() for s in SEQUENCES]

def affine_glyph(g,matrix):
 p=TTGlyphPen(None);g.draw(TransformPen(p,matrix),None);out=p.glyph();out.recalcBounds(None);return out

def zero_variant(source,name):
 # Reproduce original integer rounding at every existing source→Greek5→Small stage.
 g=affine_glyph(source['glyf'][name],(1,0,0,1,60,0))
 g=affine_glyph(g,(1.15,0,0,1,(1-1.15)*360,0))
 return affine_glyph(g,(.75,0,0,.75,0,0))

def build(output=None):
 out=pathlib.Path(output or ROOT/'inputs/code-small');out.mkdir(parents=True,exist_ok=True)
 from fetch import main as verify
 verify()
 baseline=ROOT/'inputs/grid-small/MorimoGridSmall-Regular.ttf';want=json.loads((ROOT/'inputs/build-baselines/grid-small.json').read_text())['repeat'][baseline.name]
 assert hashlib.sha256(baseline.read_bytes()).hexdigest()==want
 f=TTFont(baseline,recalcTimestamp=False);original=copy.deepcopy(f);cmap=f.getBestCmap()
 source=TTFont(ROOT/'sources/maplemono/MapleMono-Regular.ttf',recalcTimestamp=False)
 witness=zero_variant(source,'zero');zero=cmap[48]
 assert list(witness.getCoordinates(None)[0])==list(f['glyf'][zero].getCoordinates(f['glyf'])[0]),'Zero source pipeline witness mismatch'
 dotted=zero_variant(source,'zero.zero');f['glyf'][zero]=dotted;f['hmtx'][zero]=(540,dotted.xMin)
 # Keep default cmap identity: every application receives the dotted contour without zero=1.
 assert f.getBestCmap()[48]==zero and f['glyf'][zero].numberOfContours==3
 base=Shaper(ROOT/'inputs/dist/MorimoCodeGreek5-Regular.ttf');gs=base.tt.getGlyphSet();mapping={};compositions={};original_order=list(f.getGlyphOrder());new_names=[]
 for i,text in enumerate(SEQUENCES):
  rows=base.shape(text,'el' if ord(text[0])>0x300 else 'en');assert sum(r['advance'] for r in rows)==720
  pen=TTGlyphPen(None);x=0
  for row in rows:
   tr=TransformPen(pen,(.75,0,0,.75,.75*(x+row['dx']),.75*row['dy']))
   gs[row['glyph']].draw(DecomposingProxy(tr,gs));x+=row['advance']
  glyph=pen.glyph();glyph.recalcBounds(None);name=f'morimoAccent{i:02d}'
  f['glyf'][name]=glyph;f['hmtx'][name]=(540,glyph.xMin)
  new_names.append(name)
  keys=tuple(row['glyph'] for row in rows);mapping[keys]=name
  f['GDEF'].table.GlyphClassDef.classDefs[name]=1
  compositions[text]={'glyph':name,'input_glyphs':keys,'source_rows':rows,'input_stage':'after existing ccmp/locl; appended lookup','scale':[.75,.75]}
 f.setGlyphOrder(original_order+new_names)
 lookup=buildLookup([buildLigatureSubstSubtable(mapping)],table='GSUB');table=f['GSUB'].table
 index=len(table.LookupList.Lookup);table.LookupList.Lookup.append(lookup);table.LookupList.LookupCount+=1
 for feature in table.FeatureList.FeatureRecord:
  if feature.FeatureTag=='ccmp':feature.Feature.LookupListIndex.append(index);feature.Feature.LookupCount+=1
 f=rename(f,FAMILY,['maplemono','kiwimaru']);f['post'].isFixedPitch=0;f['OS/2'].panose.bProportion=9
 assert 'GPOS' not in f
 f.save(out/(STEM+'.ttf'));f.flavor='woff2';f.save(out/(STEM+'.woff2'))
 for name in ['OFL.txt']:(out/name).write_bytes((ROOT/'inputs/grid-small'/name).read_bytes())
 (out/'NOTICES.md').write_text('# Morimo Code Small Regular 0.001\n\nMaple Mono v7.9 + Kiwi Maru, exact pinned OFL 1.1 sources. All source copyright/OFL notices retained and embedded; Kiwi derivative-name restriction honored. New family avoids upstream names.\n\nSelected Small 540/1080 geometry unchanged except default zero uses Maple zero.zero (centered dot), with the exact prior transforms and integer rounding. O and all other existing glyphs/advances remain unchanged. Ten narrowly scoped canonical base+mark combinations use source-positioned outlines at uniform0.75 through default ccmp; general mark fallback remains active, no partial GPOS invented. Unknown combining sequences remain unverified and can retain fixed-em fallback gaps. No optional feature setting is needed for digit0. No installation/default changes/public release.\n')
 report={'family':FAMILY,'version':'0.001','baseline_sha256':want,'advances':[0,540,1080],'zero':{'source':'Pinned Maple Mono v7.9 zero.zero, source standard zero feature alternate','default_cmap_glyph':zero,'upstream_default_pipeline_matches_baseline':True,'optional_features_required':False},'bounded_accent_fix':compositions,'GPOS_added':False,'limits':'Only the ten named lowercase/uppercase sequences are repaired to scaled source positioning. Arbitrary combining sequences retain prior fallback behavior; no all-mark readiness claim.'}
 (out/'build.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'family':FAMILY,'zero':report['zero'],'accent_compositions':len(compositions)},ensure_ascii=False));return report

class DecomposingProxy:
 def __init__(self,target,gs):self.target=target;self.gs=gs
 def __getattr__(self,key):return getattr(self.target,key)
 def addComponent(self,name,transform):
  gs=self.gs;pen=DecomposingRecordingPen(gs);gs[name].draw(pen);tr=TransformPen(self.target,transform)
  for op,pts in pen.value:getattr(tr,op)(*pts)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output');build(p.parse_args().output)
