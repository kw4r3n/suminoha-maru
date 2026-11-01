#!/usr/bin/env python3
"""Focused genuine Japanese weight balance + selected Small calt/leading refinement."""
import argparse,copy,hashlib,json,pathlib,tempfile,statistics
from fontTools import subset
from fontTools.merge import Merger
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.areaPen import AreaPen
from fontTools.pens.perimeterPen import PerimeterPen
from fontTools.otlLib.builder import buildLigatureSubstSubtable,buildLookup
from fontTools.unicodedata import script
from build import ROOT,EPOCH,regular,restrict,japanese,code_grid,five_greek_revert,rename
from build_prose_zen import build as core_prose
from build_prose_kana import derive,geometry,PAIRS
PSTEM='MorimoProseZen-Regular';CSTEM='MorimoCodeSmall-Regular'
PBASE=ROOT/'inputs/prose-zen-kana'/(PSTEM+'.ttf');CBASE=ROOT/'inputs/code-small'/(CSTEM+'.ttf')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def draw(f,n,matrix=None):
 rec=DecomposingRecordingPen(f.getGlyphSet());f.getGlyphSet()[n].draw(rec);p=TTGlyphPen(None);target=TransformPen(p,matrix) if matrix else p
 for op,pts in rec.value:getattr(target,op)(*pts)
 g=p.glyph();g.recalcBounds(None);return g

def version(f,v,description):
 for rec in list(f['name'].names):
  if rec.nameID in [3,5,10]:f['name'].setName({3:v+';MRMO;'+f['name'].getDebugName(6),5:'Version '+v,10:description}[rec.nameID],rec.nameID,rec.platformID,rec.platEncID,rec.langID)
 f['head'].fontRevision=float(v);f['head'].modified=EPOCH;f.recalcTimestamp=False

def save(f,out,stem):
 f.flavor=None;f.save(out/(stem+'.ttf'));f.flavor='woff2';f.save(out/(stem+'.woff2'));f.flavor=None

def build(output=None):
 out=pathlib.Path(output or ROOT/'inputs/practical-refinement');out.mkdir(parents=True,exist_ok=True)
 assert sha(PBASE)=='41ee669bc34289a4e27e20e50c83314b8782d329b1bab0dbc7e28a658c12ebdf'
 assert sha(CBASE)=='edd561ef009b90a62bec8a54bc17d32775365b6518ddbcbb435ce16e431d77ff'
 locks=json.loads((ROOT/'sources/japanese-medium.lock.json').read_text())
 for row in locks['files']:assert sha(ROOT/row['path'])==row['sha256']
 zp=ROOT/locks['files'][0]['path'];kp=ROOT/locks['files'][1]['path'];z=TTFont(zp);k=TTFont(kp);baseline=TTFont(PBASE)
 assert z['OS/2'].usWeightClass==k['OS/2'].usWeightClass==500
 for donor,original in [(z,ROOT/'sources/zenmarugothic/ZenMaruGothic-Regular.ttf'),(k,ROOT/'sources/kiwimaru/KiwiMaru-Regular.ttf')]:
  old=TTFont(original);assert donor.getBestCmap()==old.getBestCmap() and donor.getGlyphOrder()==old.getGlyphOrder();assert donor['name'].getDebugName(0)==old['name'].getDebugName(0)
 with tempfile.TemporaryDirectory(prefix='morimo-medium-core-') as tmp:
  core_prose(tmp,japanese_path=zp);p=TTFont(pathlib.Path(tmp)/(PSTEM+'.ttf'),recalcTimestamp=False)
 gap=set(baseline.getBestCmap())-set(p.getBestCmap());assert len(gap)==501;kc=k.getBestCmap();roots={kc[cp] for cp in gap};assert all(not k['glyf'][n].isComposite() for n in roots);old_order=list(p.getGlyphOrder());new_names=[]
 for n in k.getGlyphOrder():
  if n not in roots:continue
  name='kiwiGap_'+n;g=copy.deepcopy(k['glyf'][n]);g.removeHinting();p['glyf'][name]=g;p['hmtx'][name]=k['hmtx'][n];new_names.append(name)
 p.setGlyphOrder(old_order+new_names)
 for t in p['cmap'].tables:
  if t.isUnicode():
   for cp in gap:
    if t.format!=4 or cp<=0xffff:t.cmap[cp]='kiwiGap_'+kc[cp]
 from fontTools.ttLib.tables._c_m_a_p import CmapSubtable
 if not any(t.isUnicode() and t.format==12 for t in p['cmap'].tables):
  t=CmapSubtable.newSubtable(12);t.platformID=3;t.platEncID=10;t.language=0;t.cmap=p.getBestCmap()|{cp:'kiwiGap_'+kc[cp] for cp in gap};p['cmap'].tables.append(t)
 # Source Medium small/full pairs guide stroke compensation for the two derived kana.
 zc=z.getBestCmap();cal=[]
 for full,small in PAIRS:
  a=geometry(z,zc[ord(full)]);b=geometry(z,zc[ord(small)]);cal.append({'full':full,'small':small,'stroke_ratio':b['stroke_proxy']/a['stroke_proxy'],'full_bbox':a['bbox'],'small_bbox':b['bbox']})
 target=statistics.median(x['stroke_ratio'] for x in cal);scores=[]
 for strength in [8+i*.5 for i in range(13)]:
  ratios=[]
  for ch in ['か','け']:
   g,_=derive(z,zc[ord(ch)],strength);a=AreaPen(None);g.draw(a,None);b=PerimeterPen(None);g.draw(b,None);ratios.append(2*abs(a.value)/b.value/geometry(z,zc[ord(ch)])['stroke_proxy'])
  scores.append((sum((v-target)**2 for v in ratios),strength,ratios))
 _,strength,ratios=min(scores);derived=[]
 for cp,ch in [(0x3095,'か'),(0x3096,'け')]:
  n=p.getBestCmap()[cp];g,_=derive(z,zc[ord(ch)],strength);p['glyf'][n]=g;p['hmtx'][n]=(1000,g.xMin);derived.append({'codepoint':f'U+{cp:04X}','source':ch,'bbox':[g.xMin,g.yMin,g.xMax,g.yMax],'advance':1000})
 # Preserve the verified common OFL body/all copyright notices without name-table bloat.
 for rec in list(p['name'].names):
  if rec.nameID in [0,13]:p['name'].setName(baseline['name'].getDebugName(rec.nameID),rec.nameID,rec.platformID,rec.platEncID,rec.langID)
 version(p,'0.004','Nunito550 Latin/Cyrillic + Noto450 Greek retained; genuine Zen500 Japanese and Kiwi500 gap fillers; optically derived small ka/ke.');assert set(p.getBestCmap())==set(baseline.getBestCmap())
 save(p,out,PSTEM);(out/'Prose-OFL.txt').write_bytes((ROOT/'inputs/prose-zen-kana/OFL.txt').read_bytes())
 (out/'Prose-NOTICES.txt').write_text('Morimo Prose Zen Regular0.004\n\n'+p['name'].getDebugName(0)+'\n\nNunito550 Latin/Cyrillic and Noto450 Greek unchanged. Genuine Zen Maru Gothic Medium500 Japanese; Kiwi Maru Medium500 only prior501 gaps. Two derived small kana use Zen Medium ka/ke, uniform0.75, translate(+125,-35), optical compensation'+str(strength)+' units each axis, recenter half that extent, integer rounding. Original scale/proportions preserved; no blind numeric equal-darkness claim. Complete OFL1.1 notices retained; no source-header RFN; Kiwi README derivative-name restriction honored.\n')
 # Reconstruct validated source-name correspondence, then reuse the already validated calt face.
 g5=TTFont(ROOT/'inputs/dist/MorimoCodeGreek5-Regular.ttf');small=TTFont(CBASE);full=TTFont(ROOT/'inputs/extras/MorimoCodeLiga-Regular.ttf',recalcTimestamp=False)
 a=regular('maplemono')
 for t in a['cmap'].tables:
  if t.isUnicode():t.cmap[0x212B]=t.cmap[0xc5]
 keep=set(a.getBestCmap());a=five_greek_revert(code_grid(restrict(a,keep,True),720,1080));b=regular('kiwimaru');jp={cp for cp in b.getBestCmap() if (japanese(cp) or (cp>=0x2000 and script(cp)=='Zyyy')) and cp not in keep};b=code_grid(restrict(b,jp,True),720,1080,True)
 for f in [a,b]:f['post'].formatType=2
 with tempfile.TemporaryDirectory(prefix='morimo-small-map-') as tmp:
  paths=[]
  for i,f in enumerate([a,b]):q=pathlib.Path(tmp)/f'{i}.ttf';f.save(q);paths.append(str(q))
  named=Merger().merge(paths)
 assert len(named.getGlyphOrder())==len(g5.getGlyphOrder());mapping=dict(zip(g5.getGlyphOrder(),named.getGlyphOrder()));assert small.getGlyphOrder()[:len(g5.getGlyphOrder())]==g5.getGlyphOrder()
 # Scale only contextual closure glyphs from existing720-cell trial to selected540-cell Small.
 overlay=set(mapping.values());new_context=[];frozen_liga=copy.deepcopy(full)
 for n in list(full.getGlyphOrder()):
  if n in overlay:continue
  g=draw(frozen_liga,n,(.75,0,0,.75,0,0));aw=full['hmtx'][n][0];full['glyf'][n]=g;full['hmtx'][n]=(round(aw*.75),getattr(g,'xMin',0));new_context.append(n)
 for old,n in mapping.items():full['glyf'][n]=draw(small,old);full['hmtx'][n]=small['hmtx'][old]
 accent=json.loads((ROOT/'inputs/code-small/build.json').read_text())['bounded_accent_fix'];names=[];lig={};full_order=list(full.getGlyphOrder())
 for text,record in accent.items():
  n=record['glyph'];actual=small.getGlyphOrder()[len(g5.getGlyphOrder())+len(names)];assert n not in full.getGlyphOrder();full['glyf'][n]=draw(small,actual);full['hmtx'][n]=small['hmtx'][actual];names.append(n);lig[tuple(mapping[g] for g in record['input_glyphs'])]=n;full['GDEF'].table.GlyphClassDef.classDefs[n]=1;mapping[actual]=n
 full.setGlyphOrder(full_order+names);lookup=buildLookup([buildLigatureSubstSubtable(lig)],table='GSUB');tab=full['GSUB'].table;ix=len(tab.LookupList.Lookup);tab.LookupList.Lookup.append(lookup);tab.LookupList.LookupCount+=1
 for feature in tab.FeatureList.FeatureRecord:
  if feature.FeatureTag=='ccmp':feature.Feature.LookupListIndex.append(ix);feature.Feature.LookupCount+=1
 full=rename(full,'Morimo Code Small',['maplemono','kiwimaru']);full['post'].isFixedPitch=0;full['post'].formatType=2;full['OS/2'].panose.bProportion=9
 full['hhea'].ascent=full['OS/2'].sTypoAscender=1200;full['hhea'].descent=full['OS/2'].sTypoDescender=-350;full['hhea'].lineGap=full['OS/2'].sTypoLineGap=0;full['OS/2'].usWinAscent=1200;full['OS/2'].usWinDescent=350
 version(full,'0.002','Selected Small540/1080 and default dotted0/ten accent repairs retained; Maple calt programming ligatures; modest line metrics1200/-350.');assert set(full.getBestCmap())==set(small.getBestCmap())
 save(full,out,CSTEM);(out/'Code-OFL.txt').write_bytes((ROOT/'inputs/code-small/OFL.txt').read_bytes());(out/'Code-NOTICES.md').write_text('# Morimo Code Small Regular0.002\n\n'+full['name'].getDebugName(0)+'\n\nExact Maple v7.9/Kiwi OFL1.1 sources. Existing approved Small contours/advances, dotted0 and ten named source-positioned accent compositions retained. Existing validated Maple calt implementation reused; only newly retained contextual closure scales0.75 from the prior720-cell ligature face.540/1080 metrics; vertical line metrics1200/-350 versus1300/-400, no glyph resizing for spacing. External existing Nerd fallback remains separate; not full embedded Nerd coverage. Unknown arbitrary marks/native long-session comfort remain unverified.\n')
 report={'prose':{'version':'0.004','baseline_sha256':sha(PBASE),'Latin_weight':550,'Greek_weight':450,'Japanese_weight':500,'gap_weight':500,'gap_points':501,'new_Medium_sources':locks,'derived_small_kana':{'native_pair_stroke_ratio_median':target,'strength':strength,'actual_ratios':ratios,'scale':.75,'translation':[125,-35],'recenter':[-strength/2,-strength/2],'glyphs':derived},'coverage':len(p.getBestCmap()),'calibration':cal},'code':{'version':'0.002','baseline_sha256':sha(CBASE),'ligature_reference_sha256':sha(ROOT/'inputs/extras/MorimoCodeLiga-Regular.ttf'),'old_glyph_map':mapping,'new_contextual_glyphs':new_context,'ten_accent_repairs_retained':True,'advances':[0,540,1080],'line_metrics_before':[1300,-400,0],'line_metrics_after':[1200,-350,0],'coverage':len(full.getBestCmap()),'calt':True,'Nerd_fallback':'Existing installed font/config unchanged'} }
 (out/'build.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:{kk:vv for kk,vv in v.items() if kk not in ['old_glyph_map','calibration','new_contextual_glyphs','new_Medium_sources']} for k,v in report.items()},ensure_ascii=False));return report
if __name__=='__main__':
 q=argparse.ArgumentParser();q.add_argument('--output');build(q.parse_args().output)
