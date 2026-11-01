#!/usr/bin/env python3
"""Nunito-led proportional prose, one explicit Greek donor, unchanged Kiwi Japanese."""
import argparse,copy,hashlib,json,pathlib,tempfile,logging,unicodedata
from fontTools import subset
from fontTools.merge import Merger
from fontTools.ttLib import TTFont
from fontTools.ttLib.scaleUpem import scale_upem
from fontTools.ttLib.tables._g_l_y_f import Glyph
from fontTools.unicodedata import script
from build import ROOT,regular,restrict,japanese,rename,EPOCH
GREEK_SCALE=.98
GREEK_WEIGHT=380
FAMILY='Morimo Prose'
STEM='MorimoProse-Regular'
DONORS=['nunito','notosans','kiwimaru']
logging.getLogger('fontTools.subset').setLevel(logging.ERROR)

def sources():
 from fetch import main as verify
 verify()
 fonts={d:regular(d) for d in ['nunito','kiwimaru']}
 lock=json.loads((ROOT/'sources/notosans/lock.json').read_text())
 for x in lock:assert hashlib.sha256((ROOT/'sources/notosans'/x['name']).read_bytes()).hexdigest()==x['sha256']
 from fontTools.varLib.instancer import instantiateVariableFont
 fonts['notosans']=instantiateVariableFont(TTFont(next((ROOT/'sources/notosans').glob('*.ttf')),recalcTimestamp=False),{'wght':GREEK_WEIGHT,'wdth':100},inplace=True)
 # Unicode canonical Angstrom alias belongs to Nunito A-ring.
 for t in fonts['nunito']['cmap'].tables:
  if t.isUnicode():t.cmap[0x212B]=t.cmap[0xC5]
 return fonts

def build(output=None):
 out=pathlib.Path(output or ROOT/'inputs/prose');out.mkdir(parents=True,exist_ok=True)
 fonts=sources();n,g,j=[fonts[d] for d in DONORS]
 greek={cp for cp in g.getBestCmap() if script(cp)=='Grek'}
 # Remove Nunito's six incidental Greek symbols so the script has one donor.
 nk=set(n.getBestCmap())-greek
 # Keep the Greek donor's combining marks as real layout closure, permitting
 # the merge's script-specific locl routing rather than replacing Nunito marks.
 marks={ord(ch) for cp in greek for ch in unicodedata.normalize('NFD',chr(cp)) if unicodedata.category(ch).startswith('M')}
 marks|={0x308,0x301,0x302}
 a=restrict(n,nk)
 options=subset.Options();options.layout_features=['*'];options.layout_scripts=['grek'];options.hinting=False
 options.name_IDs=['*'];options.name_legacy=True;options.name_languages=['*']
 sub=subset.Subsetter(options=options);sub.populate(unicodes=greek|marks);sub.subset(g)
 b=g
 for tag in ['DSIG','STAT','meta','vhea','vmtx','BASE','VORG']:
  if tag in b:del b[tag]
 scale_upem(b,980);b['head'].unitsPerEm=1000
 keep=nk|greek|marks
 jp={cp for cp in j.getBestCmap() if (japanese(cp) or (cp>=0x2000 and script(cp)=='Zyyy')) and cp not in keep}
 c=restrict(j,jp)
 for f in [a,b,c]:f['post'].formatType=2.0
 with tempfile.TemporaryDirectory(prefix='morimo-prose-merge-') as tmp:
  paths=[]
  for i,f in enumerate([a,b,c]):
   p=pathlib.Path(tmp)/f'{i}.ttf';f.save(p);paths.append(str(p))
  merged=Merger().merge(paths)
 merged.recalcTimestamp=False
 empty=[]
 for name in merged.getGlyphOrder():
  glyph=merged['glyf'][name]
  if glyph.isComposite() and all(merged['glyf'][c.glyphName].numberOfContours==0 for c in glyph.components):merged['glyf'][name]=Glyph();empty.append(name)
 merged=rename(merged,FAMILY,DONORS)
 # A common baseline; natural proportional advances and existing kern/mark data.
 merged['hhea'].ascent=merged['OS/2'].sTypoAscender=1150
 merged['hhea'].descent=merged['OS/2'].sTypoDescender=-350
 merged['OS/2'].usWinAscent=1150;merged['OS/2'].usWinDescent=350
 merged['hhea'].lineGap=merged['OS/2'].sTypoLineGap=0
 merged['post'].isFixedPitch=0;merged['post'].formatType=2.0
 merged['OS/2'].panose.bProportion=3
 merged.save(out/(STEM+'.ttf'));merged.flavor='woff2';merged.save(out/(STEM+'.woff2'))
 copyrights=[(ROOT/'sources'/d/'OFL.txt').read_text().split('\n\n')[0].strip() for d in DONORS]
 ofl=(ROOT/'sources/nunito/OFL.txt').read_text();body=ofl[ofl.index('This Font Software'):]
 (out/'OFL.txt').write_text('\n'.join(copyrights)+'\nCopyright 2026 The Morimo Prototype Contributors\n\n'+body)
 (out/'NOTICES.txt').write_text('Morimo Prose Regular 0.001\n\n'+ '\n'.join(copyrights)+'\n\nNunito: Latin/Cyrillic and shared punctuation/marks. Noto Sans wght380/width100: explicit Greek supplement, uniformly scaled0.98 with layout coordinates; one script donor. Kiwi Maru: Japanese outlines/advances unchanged.\nAll OFL1.1; no RFN declaration in these exact notices. Kiwi upstream README separately prohibits キウイ丸 derivative naming; new family Morimo Prose avoids it.\nNo Comfortaa outlines, no browser fallback in this merged face. No upstream endorsement.\n')
 report={'family':FAMILY,'version':'0.001','donors':DONORS,'greek_scale':GREEK_SCALE,'greek_source_weight':GREEK_WEIGHT,'baseline_translation':0,'nunito_and_japanese_scale':1,'advances':'natural proportional Nunito/Greek; Japanese1000','vertical_metrics':[1150,-350,0],'selection_codepoints':{'nunito':len(nk),'greek':len(greek),'greek_combining_seed':len(marks),'japanese':len(jp)},'cmap':len(merged.getBestCmap()),'glyphs':len(merged.getGlyphOrder()),'empty_composites_normalized':len(empty),'GPOS_features':sorted({x.FeatureTag for x in merged['GPOS'].table.FeatureList.FeatureRecord}),'GSUB_scripts':[x.ScriptTag for x in merged['GSUB'].table.ScriptList.ScriptRecord],'style_limit':'Greek lowercase remains about8% taller and has less rounded terminals; Kiwi brush-like endings differ from Nunito. Noto wght380/scale0.98 matches measured82-unit H-stems; no outline dilation.'}
 (out/'build.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
 return report
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=pathlib.Path);build(p.parse_args().output)
