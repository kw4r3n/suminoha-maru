#!/usr/bin/env python3
"""Separate ligature and licensed Nerd subset trials; approved base fonts stay untouched."""
import copy,hashlib,json,pathlib,tempfile,zipfile
from fontTools import subset
from fontTools.merge import Merger
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.transformPen import TransformPen
from build import ROOT,regular,restrict,japanese,code_grid,five_greek_revert,rename,EPOCH
from fontTools.unicodedata import script
from hb import Shaper

def geometry(f,n):
 p=DecomposingRecordingPen(f.getGlyphSet());f.getGlyphSet()[n].draw(p)
 return p.value,f['hmtx'][n]
def ligature_font(features=None):
 from verify_extras_sources import verify
 verify()
 base=TTFont(ROOT/'inputs/dist/MorimoCodeGreek5-Regular.ttf',recalcTimestamp=False)
 a=regular('maplemono')
 for t in a['cmap'].tables:
  if t.isUnicode():t.cmap[0x212B]=t.cmap[0xC5]
 keep=set(a.getBestCmap());opt=subset.Options();opt.layout_features=features or ['ccmp','locl','calt','mark','mkmk','rlig'];opt.hinting=False
 ss=subset.Subsetter(options=opt);ss.populate(unicodes=keep);ss.subset(a)
 for tag in ['DSIG','STAT','meta','vhea','vmtx','BASE','VORG']:
  if tag in a:del a[tag]
 # Newly retained contextual glyphs are normalized from 600 to 720 horizontally;
 # negative bearings in multi-character ligatures intentionally span their input cells.
 gs=a.getGlyphSet();drawings={}
 for n in a.getGlyphOrder():
  p=DecomposingRecordingPen(gs);gs[n].draw(p);drawings[n]=p.value
 for n,rec in drawings.items():
  pen=TTGlyphPen(None);tr=TransformPen(pen,(1.2,0,0,1,0,0))
  for op,pts in rec:getattr(tr,op)(*pts)
  g=pen.glyph();g.recalcBounds(a['glyf']);a['glyf'][n]=g
  aw,lsb=a['hmtx'][n];a['hmtx'][n]=(round(aw*1.2),getattr(g,'xMin',round(lsb*1.2)))
 b=regular('kiwimaru');jp={cp for cp in b.getBestCmap() if (japanese(cp) or (cp>=0x2000 and script(cp)=='Zyyy')) and cp not in keep}
 b=code_grid(restrict(b,jp,True),720,1080,True)
 baseline_a=regular('maplemono')
 for t in baseline_a['cmap'].tables:
  if t.isUnicode():t.cmap[0x212B]=t.cmap[0xC5]
 baseline_a=five_greek_revert(code_grid(restrict(baseline_a,keep,True),720,1080))
 # Retain source glyph names across temporary serialization. With post v3, generic
 # glyphNNNN names shift when calt adds closure glyphs and cannot identify shapes.
 for ff in [a,b,baseline_a]:ff['post'].formatType=2.0
 with tempfile.TemporaryDirectory() as tmp:
  ap=pathlib.Path(tmp)/'a.ttf';bp=pathlib.Path(tmp)/'b.ttf';rp=pathlib.Path(tmp)/'baseline.ttf';a.save(ap);b.save(bp);baseline_a.save(rp);full=Merger().merge([str(ap),str(bp)]);namedbase=Merger().merge([str(rp),str(bp)])
 assert set(full.getBestCmap())==set(base.getBestCmap())
 assert len(namedbase.getGlyphOrder())==len(base.getGlyphOrder())
 mapping=dict(zip(base.getGlyphOrder(),namedbase.getGlyphOrder()))
 assert all(full.getBestCmap()[cp]==mapping[n] for cp,n in base.getBestCmap().items())
 # Copy decomposed approved contours: component names from the saved v3 base
 # are not stable across this additional calt closure.
 for old,n in mapping.items():
  rec=DecomposingRecordingPen(base.getGlyphSet());base.getGlyphSet()[old].draw(rec);pen=TTGlyphPen(None)
  for op,pts in rec.value:getattr(pen,op)(*pts)
  full['glyf'][n]=pen.glyph();full['hmtx'][n]=base['hmtx'][old]
 if 'GPOS' in full and not full['GPOS'].table.LookupList.Lookup:del full['GPOS']
 full=rename(full,'Morimo Code Liga',['maplemono','kiwimaru']);full.recalcTimestamp=False;full['post'].isFixedPitch=0
 basecheck=all(geometry(full,n)==geometry(base,old) for old,n in mapping.items());assert basecheck
 full['post'].formatType=2.0
 return full,base,basecheck,mapping

def main(output=None):
 out=pathlib.Path(output or ROOT/'inputs/extras');out.mkdir(parents=True,exist_ok=True)
 full,base,basecheck,mapping=ligature_font()
 def save(f,stem):
  f.flavor=None;f.save(out/(stem+'.ttf'));f.flavor='woff2';f.save(out/(stem+'.woff2'));f.flavor=None
 save(full,'MorimoCodeLiga-Regular')
 icons=TTFont(ROOT/'sources/nerd-symbols/SymbolsNerdFontMono-Regular.ttf');cmap=icons.getBestCmap()
 selected={cp:n for cp,n in cmap.items() if n.startswith(('oct-','pl-','ple-')) and cp not in base.getBestCmap()}
 nf=copy.deepcopy(full);gs=icons.getGlyphSet();added=[]
 for cp,n in selected.items():
  p=TTGlyphPen(None);rec=DecomposingRecordingPen(gs);gs[n].draw(rec)
  # Vertical em normalization, horizontal fit to one 720-unit code cell.
  from fontTools.pens.boundsPen import BoundsPen
  bp=BoundsPen(gs);gs[n].draw(bp);scale=1000/icons['head'].unitsPerEm
  width=(bp.bounds[2]-bp.bounds[0])*scale if bp.bounds else 0
  sx=min(scale,700/(bp.bounds[2]-bp.bounds[0])) if width>700 else scale
  shift=360-sx*(bp.bounds[0]+bp.bounds[2])/2 if bp.bounds else 0
  tr=TransformPen(p,(sx,0,0,scale,shift,0))
  for op,pts in rec.value:getattr(tr,op)(*pts)
  g=p.glyph();g.recalcBounds(nf['glyf']);name='nerd.'+n;nf['glyf'][name]=g;nf['hmtx'][name]=(720,getattr(g,'xMin',0));added.append(name)
  for t in nf['cmap'].tables:
   if t.isUnicode() and (t.format==12 or cp<=0xffff):t.cmap[cp]=name
 nf.setGlyphOrder(nf.getGlyphOrder()+added)
 nf=rename(nf,'Morimo Code Nerd Subset',['maplemono','kiwimaru']);nf['post'].isFixedPitch=0
 notices='\n\n'.join((ROOT/'sources/nerd-symbols'/n).read_text() for n in ['LICENSE','octicons-LICENSE.txt','powerline-LICENSE.txt','powerline-extra-LICENSE.txt'])
 oldcopyright=nf['name'].getDebugName(0);oldlicense=nf['name'].getDebugName(13)
 for plat,enc in [(3,1),(0,4)]:
  nf['name'].setName(oldcopyright+'\nNerd icons: Copyright 2016 Ryan McIntyre; Copyright 2023 GitHub Inc.; Copyright 2013 Kim Silkebækken and other contributors.',0,plat,enc,0x409 if plat==3 else 0)
  nf['name'].setName(oldlicense+'\n\n'+notices,13,plat,enc,0x409 if plat==3 else 0)
 save(nf,'MorimoCodeNerdSubset-Regular')
 report=dict(base_font_sha256=hashlib.sha256((ROOT/'inputs/dist/MorimoCodeGreek5-Regular.ttf').read_bytes()).hexdigest(),approved_glyphs_preserved=len(base.getGlyphOrder()),preservation_pass=basecheck,new_ligature_closure_glyphs=len(full.getGlyphOrder())-len(base.getGlyphOrder()),features=sorted({x.FeatureTag for x in full['GSUB'].table.FeatureList.FeatureRecord}),icons=len(selected),icon_sets=['Octicons','Powerline','Powerline Extra'],icon_cmap={f'U+{c:04X}':n for c,n in selected.items()},limits=['Nerd-compatible MIT subset, not full Nerd Fonts coverage','No FontForge patcher/runtime installed; fontTools copies verified official source contours','2:3 editor face is not standard terminal double-cell compatible','Ligature-only output contours scaled x1.2 from Maple 600-cell to 720-cell; approved non-ligature glyphs unchanged'])
 (out/'build.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='icon_cmap'}))
 return report
if __name__=='__main__':main()
