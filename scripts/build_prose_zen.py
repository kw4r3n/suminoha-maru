#!/usr/bin/env python3
"""Nunito-led proportional prose, one explicit Greek donor, Zen Japanese and an explicit source-derived fullwidth dollar."""
import argparse,copy,hashlib,json,pathlib,tempfile,logging,unicodedata
from fontTools import subset
from fontTools.merge import Merger
from fontTools.ttLib import TTFont
from fontTools.ttLib.scaleUpem import scale_upem
from fontTools.ttLib.tables._g_l_y_f import Glyph
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.unicodedata import script
from build import ROOT,regular,restrict,japanese,rename,EPOCH
GREEK_SCALE=1.0
GREEK_WEIGHT=450
FAMILY='Morimo Prose Zen'
STEM='MorimoProseZen-Regular'
DONORS=['nunito','notosans','zenmarugothic']
logging.getLogger('fontTools.subset').setLevel(logging.ERROR)

def sources(japanese_path=None,latin_weight=550):
 from fetch import main as verify
 verify()
 fonts={'zenmarugothic':TTFont(japanese_path,recalcTimestamp=False) if japanese_path else regular('zenmarugothic')}
 from fontTools.varLib.instancer import instantiateVariableFont
 fonts['nunito']=instantiateVariableFont(TTFont(next((ROOT/'sources/nunito').glob('*.ttf')),recalcTimestamp=False),{'wght':latin_weight},inplace=True)
 lock=json.loads((ROOT/'sources/notosans/lock.json').read_text())
 for x in lock:assert hashlib.sha256((ROOT/'sources/notosans'/x['name']).read_bytes()).hexdigest()==x['sha256']
 from fontTools.varLib.instancer import instantiateVariableFont
 fonts['notosans']=instantiateVariableFont(TTFont(next((ROOT/'sources/notosans').glob('*.ttf')),recalcTimestamp=False),{'wght':GREEK_WEIGHT,'wdth':100},inplace=True)
 # Unicode canonical Angstrom alias belongs to Nunito A-ring.
 for t in fonts['nunito']['cmap'].tables:
  if t.isUnicode():t.cmap[0x212B]=t.cmap[0xC5]
 # Zen lacks U+FF04. Derive only this missing fullwidth form from its own dollar,
 # centered in a 1000-unit cell without scaling; no extra donor or silent fallback.
 z=fonts['zenmarugothic']
 for tag in ['vhea','vmtx','BASE','VORG']:
  if tag in z:del z[tag]
 order=list(z.getGlyphOrder());name='morimoFullwidthDollar';donor=z.getBestCmap()[0x24];advance=z['hmtx'][donor][0];delta=(1000-advance)//2
 z.morimoDollarDerivation={'source':'Zen original dollar','original_advance':advance,'new_advance':1000,'outline_translation_x':delta,'scale':1}
 pen=TTGlyphPen(None);rp=DecomposingRecordingPen(z.getGlyphSet());z.getGlyphSet()[donor].draw(rp);tr=TransformPen(pen,(1,0,0,1,delta,0))
 for op,pts in rp.value:getattr(tr,op)(*pts)
 glyph=pen.glyph();glyph.recalcBounds(None);z['glyf'][name]=glyph;z['hmtx'][name]=(1000,glyph.xMin);z.setGlyphOrder(order+[name])
 for table in z['cmap'].tables:
  if table.isUnicode():table.cmap[0xFF04]=name
 return fonts

def build(output=None,japanese_path=None,latin_weight=550):
 out=pathlib.Path(output or ROOT/'inputs/prose-zen');out.mkdir(parents=True,exist_ok=True)
 fonts=sources(japanese_path,latin_weight);n,g,j=[fonts[d] for d in DONORS]
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
 assert b['head'].unitsPerEm==1000  # Preserve genuine Greek source proportions and size.
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
 copyrights=list(dict.fromkeys([(ROOT/'sources'/d/'OFL.txt').read_text().split('\n\n')[0].strip() for d in DONORS]+[fonts[d]['name'].getDebugName(0) for d in DONORS]))
 for rec in list(merged['name'].names):
  if rec.nameID==0:merged['name'].setName('\n'.join(copyrights),0,rec.platformID,rec.platEncID,rec.langID)
 # A common baseline; natural proportional advances and existing kern/mark data.
 merged['hhea'].ascent=merged['OS/2'].sTypoAscender=1150
 merged['hhea'].descent=merged['OS/2'].sTypoDescender=-350
 merged['OS/2'].usWinAscent=1150;merged['OS/2'].usWinDescent=350
 merged['hhea'].lineGap=merged['OS/2'].sTypoLineGap=0
 merged['OS/2'].usWeightClass=latin_weight
 merged['post'].isFixedPitch=0;merged['post'].formatType=2.0
 merged['OS/2'].panose.bProportion=3
 merged.save(out/(STEM+'.ttf'));merged.flavor='woff2';merged.save(out/(STEM+'.woff2'))
 ofl=(ROOT/'sources/nunito/OFL.txt').read_text();body=ofl[ofl.index('This Font Software'):]
 (out/'OFL.txt').write_text('\n'.join(copyrights)+'\nCopyright 2026 The Morimo Prototype Contributors\n\n'+body)
 (out/'NOTICES.txt').write_text('Morimo Prose Zen Regular 0.001\n\n'+'\n'.join(copyrights)+'\n\nNunito genuine wght550: Latin/Cyrillic and shared punctuation/marks. Zen Maru Gothic Regular400: Japanese, original contours/advances. Source-derived U+FF04 centers Zen dollar in1000 units without scaling because the source lacks that fullwidth codepoint. Noto Sans wght450/wdth100: explicit Greek supplement, natural size/proportions; no x/y scale.\nAll exact source OFL1.1 notices retained/embedded; no RFN declarations in their headers. New derivative family name; no upstream endorsement or implicit fallback. No installed-font replacement, font-default/generic assignments or serif redesign. Morimo remains sans-serif.\n')
 def ymax(font,cp):
  p=BoundsPen(font.getGlyphSet());font.getGlyphSet()[font.getBestCmap()[cp]].draw(p);return p.bounds[3]
 report={'family':FAMILY,'version':'0.001','donors':DONORS,'nunito_source_weight':latin_weight,'Japanese_source_weight':j['OS/2'].usWeightClass,'greek_scale':1,'greek_source_weight':GREEK_WEIGHT,'baseline_translation':0,'nunito_and_japanese_scale':1,'advances':'natural proportional; Japanese1000','global_weight_metadata':latin_weight,'vertical_metrics':[1150,-350,0],'selection_codepoints':{'nunito':len(nk),'greek':len(greek),'greek_combining_seed':len(marks),'japanese':len(jp)},'cmap':len(merged.getBestCmap()),'glyphs':len(merged.getGlyphOrder()),'empty_composites_normalized':len(empty),'GPOS_features':sorted({x.FeatureTag for x in merged['GPOS'].table.FeatureList.FeatureRecord}),'GSUB_scripts':[x.ScriptTag for x in merged['GSUB'].table.ScriptList.ScriptRecord],'fullwidth_dollar':j.morimoDollarDerivation,'style_measurements':{'Nunito_o_top':ymax(n,ord('o')),'Noto_omicron_top':ymax(fonts['notosans'],ord('ο')),'H_stem_pixel_reference_at1000px':{'Nunito550':98,'Noto450':99}},'style_limit':'Greek uses explicit Noto Sans; lowercase is naturally taller and terminals less rounded. H-stem observation does not prove whole-text perceived weight equality. No independent height adjustment or synthetic weight.'}
 (out/'build.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
 return report
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=pathlib.Path);build(p.parse_args().output)
