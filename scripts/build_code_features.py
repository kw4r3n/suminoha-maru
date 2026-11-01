#!/usr/bin/env python3
"""Retain complete applicable pinned Maple programming/optional upright repertoire."""
import argparse,copy,json,pathlib,shutil
from fontTools.ttLib import TTFont
from fontTools.otlLib.builder import buildLigatureSubstSubtable,buildLookup
from code_extras import ligature_font
from build import ROOT,rename
from build_practical_refinement import draw,save,version,sha,CSTEM
BASE=ROOT/'inputs/practical-refinement';OUT=ROOT/'inputs/code-features'
FEATURES=['calt','ccmp','locl','case','zero']+[f'ss{i:02}' for i in list(range(1,6))+list(range(7,12))]+[f'cv{i:02}' for i in list(range(1,12))+list(range(61,67))]
def build(output=None):
 out=pathlib.Path(output or OUT);out.mkdir(parents=True,exist_ok=True);old=TTFont(BASE/(CSTEM+'.ttf'));assert sha(BASE/(CSTEM+'.ttf'))=='f8d40483568fcb283a684ad8ce5a83e86a9db7c0c35b2d80c7414ed13d2260b3'
 f,_,_,_=ligature_font(FEATURES);frozen=copy.deepcopy(f);oldnames=set(old.getGlyphOrder());new=[]
 for n in f.getGlyphOrder():
  if n not in oldnames:
   g=draw(frozen,n,(.75,0,0,.75,0,0));f['glyf'][n]=g;f['hmtx'][n]=(round(frozen['hmtx'][n][0]*.75),getattr(g,'xMin',0));new.append(n)
 order=list(f.getGlyphOrder())
 for n in old.getGlyphOrder():
  f['glyf'][n]=copy.deepcopy(old['glyf'][n]);f['hmtx'][n]=old['hmtx'][n]
  if n not in order:order.append(n)
 f.setGlyphOrder(order)
 # The optional source zero feature must retain the selected dotted design too.
 if 'zero.zero' in f['glyf']:
  f['glyf']['zero.zero']=draw(old,old.getBestCmap()[48]);f['hmtx']['zero.zero']=old['hmtx'][old.getBestCmap()[48]]
 mapping=json.loads((BASE/'build.json').read_text())['code']['old_glyph_map'];accent=json.loads((ROOT/'inputs/code-small/build.json').read_text())['bounded_accent_fix'];lig={}
 for text,row in accent.items():
  n=row['glyph'];lig[tuple(mapping[g] for g in row['input_glyphs'])]=n;f['GDEF'].table.GlyphClassDef.classDefs[n]=1
 lookup=buildLookup([buildLigatureSubstSubtable(lig)],table='GSUB');tab=f['GSUB'].table;ix=len(tab.LookupList.Lookup);tab.LookupList.Lookup.append(lookup);tab.LookupList.LookupCount+=1
 for rec in tab.FeatureList.FeatureRecord:
  if rec.FeatureTag=='ccmp':rec.Feature.LookupListIndex.append(ix);rec.Feature.LookupCount+=1
 f=rename(f,'Morimo Code Small',['maplemono','kiwimaru']);src=TTFont(ROOT/'sources/maplemono/MapleMono-Regular.ttf')
 for rec in src['name'].names:
  if rec.nameID>=256:f['name'].setName(rec.toUnicode(),rec.nameID,rec.platformID,rec.platEncID,rec.langID)
 f['post'].formatType=2;f['post'].isFixedPitch=0;f['OS/2'].panose.bProportion=9
 for tag in ['hhea','OS/2']:
  for key in (['ascent','descent','lineGap'] if tag=='hhea' else ['sTypoAscender','sTypoDescender','sTypoLineGap','usWinAscent','usWinDescent']):setattr(f[tag],key,getattr(old[tag],key))
 version(f,'0.003','Selected Small540/1080,dotted0,marks and default calt retained; complete applicable Maple programming ss/cv upright alternates optional; no forced stylistic switches.')
 assert f.getBestCmap()==old.getBestCmap();save(f,out,CSTEM);shutil.copyfile(BASE/'Code-OFL.txt',out/'Code-OFL.txt')
 (out/'Code-NOTICES.md').write_text('# Morimo Code Small Regular0.003\n\n'+f['name'].getDebugName(0)+'\n\nPinned Maple v7.9/Kiwi OFL1.1 sources, same default selected Small contours/advances/dotted0/ten bounded accent repairs and inherited calt. Full applicable programming/upright cv/ss features retained as opt-in, including semantic alternate comparisons and arrows; no blanket enable. New contextual/alternate glyphs use the existing source600→720x1.2 then Small0.75 transform, i.e.x0.9/y0.75 with existing stage rounding. Default9149 glyphs exact. Optional zero output uses the same selected dotted0. Source UI labels restored. Fractions/super/subscripts and italic-only designs are outside this Regular programming scope. Existing external Nerd fallback stays separate, no full embedded Nerd claim. Font vertical metrics and Kitty configuration unchanged.\n')
 report={'version':'0.003','source_sha256':sha(ROOT/'sources/maplemono/MapleMono-Regular.ttf'),'baseline_sha256':sha(BASE/(CSTEM+'.ttf')),'features':sorted(FEATURES),'excluded_source_features':sorted({r.FeatureTag for r in src['GSUB'].table.FeatureList.FeatureRecord}-set(FEATURES)),'new_glyphs':new,'old_glyphs_preserved':len(oldnames),'coverage':len(f.getBestCmap()),'new_geometry':'Existing x1.2 ligature normalization then uniform0.75; no change to current9149 glyphs. Optionalzero output explicitly selected dotted design.','Kitty':'existing -2px setting untouched; expected23px at12pt'};(out/'build.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='new_glyphs'}));return report
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output');build(p.parse_args().output)
