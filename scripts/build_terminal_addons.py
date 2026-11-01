"""Additive terminal prototypes: immutable old glyphs/layout; explicit small emoji set."""
import argparse,copy,hashlib,json,tempfile,sys,shutil,unicodedata
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.boundsPen import ControlBoundsPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.transformPen import TransformPen
EMOJI='🤖✅❌🔧🔍💡📝📦🚀🎉🎯'
SYMBOLS='⚙⎋✖⏳⌛⏱⏻⏴⏵⏸⏹⏺⌘⌥⌫'
PROMPT=[0x22c8,0x2309,0x230a,0x2102,0x22ef,0x23a5,0x23aa]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def build(root,sources,out):
 sys.path.insert(0,str(root/'scripts'));from hb import Shaper
 assert sha(root/'sources/notosans/NotoSans[wdth,wght].ttf')=='bfb7bb691513f12e734dc346c03a03f784912432d7e3fa8e56efcf906fe86b3d'
 for p,h in [('inputs/code-jp-size/MorimoCodeLatin1216JP95-Regular.ttf','ebf522d3050776354973e5c65c808ecd13257e5051238c60264384222e1ab835'),('inputs/code-ratio23/MorimoCodeLatin1216JP95Ratio23-Regular.ttf','40d6c0f315a974f5bd23faf781d50e59f625e118cd8b66f6e109cf96328b8ce2')]:assert sha(root/p)==h
 for item in json.loads((sources/'lock.json').read_text()):assert sha(sources/item['path'])==item['sha256']
 nf=TTFont(root/'sources/nerd-symbols/SymbolsNerdFontMono-Regular.ttf');assert sha(root/'sources/nerd-symbols/SymbolsNerdFontMono-Regular.ttf')=='fe471e538392f51910faab985fa8e192a39dd3426125edd15b71b3680df0e749'
 donors={'Nerd':nf,'Symbols':TTFont(sources/'NotoSansSymbols-Regular.ttf'),'Symbols2':TTFont(sources/'NotoSansSymbols2-Regular.ttf'),'Math':TTFont(sources/'NotoSansMath-Regular.ttf'),'NotoSans':instantiateVariableFont(TTFont(root/'sources/notosans/NotoSans[wdth,wght].ttf'),{'wght':400,'wdth':100},inplace=True),'Emoji':instantiateVariableFont(TTFont(sources/'NotoEmoji[wght].ttf'),{'wght':400},inplace=True)}
 cm=TTFont(root/'inputs/code-jp-size/MorimoCodeLatin1216JP95-Regular.ttf').getBestCmap();nc=nf.getBestCmap();selected={cp:('Nerd',n) for cp,n in nc.items() if n.startswith(('pl-','ple-','oct-')) and cp not in cm};assert len(selected)==337
 selected[0xe718]=('Nerd',nc[0xe718])
 for ch in SYMBOLS+''.join(map(chr,PROMPT)):
  cp=ord(ch);assert cp not in cm
  key=next(k for k in ('Symbols','Symbols2','Math','NotoSans') if cp in donors[k].getBestCmap());selected[cp]=(key,donors[key].getBestCmap()[cp])
 # Resolve only requested emoji singletons through donor GSUB; no full emoji layout import.
 with tempfile.TemporaryDirectory() as tmp:
  p=Path(tmp)/'emoji.ttf';donors['Emoji'].save(p);sh=Shaper(p)
  for ch in EMOJI:
   rows=sh.shape(ch);assert len(rows)==1 and rows[0]['gid']!=0,(ch,rows)
   selected[ord(ch)]=('Emoji',rows[0]['glyph'])
  sh.close()
 assert len(selected)==371 and not (set(selected)&set(cm))
 gs={k:f.getGlyphSet() for k,f in donors.items()};out.mkdir(parents=True,exist_ok=True);results={}
 for tag,base,width in [('Grid','inputs/code-jp-size/MorimoCodeLatin1216JP95-Regular.ttf',540),('Ratio23','inputs/code-ratio23/MorimoCodeLatin1216JP95Ratio23-Regular.ttf',720)]:
  a=TTFont(root/base,recalcTimestamp=False);f=TTFont(root/base,recalcTimestamp=False);family='Morimo Code JP95 Terminal Addons '+tag;stem='MorimoCodeJP95TerminalAddons'+tag+'-Regular';mapping={}
  order=list(a.getGlyphOrder());sep=a['glyf'][cm[0xe0b0]];sy0,sy1=sep.yMin,sep.yMax
  for cp,(key,n) in sorted(selected.items()):
   pen=ControlBoundsPen(gs[key]);gs[key][n].draw(pen);assert pen.bounds,(hex(cp),n);x0,y0,x1,y1=pen.bounds
   wide=key=='Emoji' or unicodedata.east_asian_width(chr(cp)) in ('W','F');aw=1080 if wide else width
   issep=key=='Nerd' and n.startswith('ple-') and cp>=0xe0b0
   if issep:sx=aw/(x1-x0);ys=(sy1-sy0)/(y1-y0);dx=-x0*sx;dy=sy0-y0*ys
   else:
    sx=ys=min((aw-40)/(x1-x0),1000/(y1-y0));dx=(aw-(x1-x0)*sx)/2-x0*sx;dy=350-(y0+y1)*ys/2
   rec=DecomposingRecordingPen(gs[key]);gs[key][n].draw(rec);p=TTGlyphPen(None);tr=TransformPen(p,(sx,0,0,ys,dx,dy))
   for op,pts in rec.value:getattr(tr,op)(*pts)
   g=p.glyph();g.recalcBounds(None);name=f'addon.u{cp:05X}';f['glyf'][name]=g;f['hmtx'][name]=(aw,g.xMin);order.append(name)
   for t in f['cmap'].tables:
    if t.isUnicode() and (t.format==12 or (cp<=0xffff and t.format==4)):t.cmap[cp]=name
   mapping[f'U+{cp:04X}']={'source':key,'source_glyph':n,'glyph':name,'advance':aw,'matrix':[sx,0,0,ys,dx,dy],'separator':issep}
  f.setGlyphOrder(order)
  for r in list(f['name'].names):
   vals={1:family,4:family+' Regular',6:stem,16:family,17:'Regular',3:'0.001;MRMO;'+stem,5:'Version 0.001',10:'Additive monochrome terminal icons and bounded emoji prototype; no install.'}
   if r.nameID==0:vals[0]=a['name'].getDebugName(0)+'; Terminal additions: GitHub Inc.2023; Ryan L McIntyre2014/2016; konpa2015; Noto Project Authors2022; Google LLC2013/2022. See bundled complete notices.'
   if r.nameID in vals:f['name'].setName(vals[r.nameID],r.nameID,r.platformID,r.platEncID,r.langID)
  f['head'].fontRevision=.001;f.recalcTimestamp=False
  f.save(out/(stem+'.ttf'));f.flavor='woff2';f.save(out/(stem+'.woff2'))
  results[tag]={'family':family,'stem':stem,'base':base,'base_sha256':sha(root/base),'coverage':len(cm)+len(selected),'old_glyphs':len(a.getGlyphOrder()),'mapping':mapping,'hashes':{ext:sha(out/(stem+'.'+ext)) for ext in ('ttf','woff2')},'sizes':{ext:(out/(stem+'.'+ext)).stat().st_size for ext in ('ttf','woff2')}}
 (out/'mapping.json').write_text(json.dumps(results,sort_keys=True,indent=2)+'\n');return results
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--sources',type=Path);p.add_argument('--output',type=Path);a=p.parse_args();build(a.root,a.sources or a.root/'sources/terminal-addons',a.output or a.root/'inputs/terminal-addons')
