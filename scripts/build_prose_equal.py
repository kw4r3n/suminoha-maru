#!/usr/bin/env python3
"""Genuine500 baseline; preserve established proportions and Japanese Medium derivations."""
import copy,json,pathlib,tempfile,shutil
from fontTools.ttLib import TTFont
from build import ROOT
import build_prose_zen as core
from build_practical_refinement import version,save,PSTEM,sha
OUT=ROOT/'inputs/prose-equal';BASE=ROOT/'inputs/practical-refinement'
def build(output=None):
 out=pathlib.Path(output or OUT);out.mkdir(parents=True,exist_ok=True)
 p=TTFont(BASE/(PSTEM+'.ttf'),recalcTimestamp=False)
 jp=ROOT/'sources/japanese-medium/zenmarugothic/ZenMaruGothic-Medium.ttf'
 assert sha(jp)=='3cfdb98a13571ede17fcc769f5093a97c38b80a7b9b2ab754a26b4d822092b3b'
 old=core.GREEK_WEIGHT
 try:
  core.GREEK_WEIGHT=500
  with tempfile.TemporaryDirectory(prefix='morimo-equal-core-') as t:
   core.build(t,japanese_path=jp,latin_weight=500);n=TTFont(pathlib.Path(t)/(PSTEM+'.ttf'),recalcTimestamp=False)
 finally:core.GREEK_WEIGHT=old
 order=p.getGlyphOrder();assert n.getGlyphOrder()==order[:9460]
 for name in n.getGlyphOrder():p['glyf'][name]=copy.deepcopy(n['glyf'][name]);p['hmtx'][name]=n['hmtx'][name]
 for tag in ['GSUB','GPOS','GDEF']:p[tag]=copy.deepcopy(n[tag])
 p['OS/2'].usWeightClass=500
 version(p,'0.007','Genuine Nunito500 / Noto Sans500 Greek / Zen Maru500 / Kiwi500 gaps. Original proportions; no global Japanese optical emboldening. Existing derived small kana retained from genuine Medium baseline.')
 save(p,out,PSTEM);shutil.copyfile(BASE/'Prose-OFL.txt',out/'Prose-OFL.txt')
 (out/'Prose-NOTICES.txt').write_text('Morimo Prose Zen Regular0.007\n\n'+p['name'].getDebugName(0)+'\n\nGenuine Nunito500 Latin/Cyrillic; Noto Sans500 Greek wdth100; Zen Maru Gothic Medium500 Japanese; Kiwi Maru Medium500 only501 prior gaps. Original scale/baseline/proportions retained. No global Japanese synthetic weight correction. Derived small kana retain Zen500 construction: scale0.75, translate125,-35, local optical compensation10.5, recenter-5.25, integer rounding; advance1000. Numeric500 is a baseline, not equal perceived darkness. All four OFL1.1 notices retained; no header RFN; Kiwi derivative-name restriction honored. No new Chinese localization or arbitrary mark guarantee.\n')
 (out/'build.json').write_text(json.dumps({'version':'0.007','weights':dict.fromkeys(['Nunito','Noto Sans Greek','Zen Maru','Kiwi gaps'],500),'Japanese_extra_emboldening':0,'small_kana':'Existing Zen500 optical small-form derivation retained; not global weight correction','coverage':len(p.getBestCmap()),'Greek_scale':1,'proportions':'unchanged, source natural advances','reference':sha(BASE/(PSTEM+'.ttf'))},indent=2)+'\n')
 return p
if __name__=='__main__':build()
