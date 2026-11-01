"""Minimal base-identical whitespace exception for Han companions."""
import argparse,copy,json,sys
from pathlib import Path
from fontTools.ttLib import TTFont
SPACES=(0x20,0xa0,0x3000)
def build(root,out):
 sys.path.insert(0,str(root/'scripts'));from build_han_companions import sha
 base=root/'inputs/terminal-ratio35/MorimoCodeJP95TerminalAddonsRatio35-Regular.ttf';assert sha(base)=='175ee5b2de7a1c6cb2337837ad4929b7aa312a3f957a93d62af371d1d35bdc88';b=TTFont(base);bc=b.getBestCmap();cm=json.loads((root/'inputs/han-compat/manifest.json').read_text());old=json.loads((root/'inputs/han-companions/manifest.json').read_text());out.mkdir(parents=True,exist_ok=True);result={}
 for part in ('JP','RareA','RareB'):
  row=cm['parts'][part] if part!='RareB' else old['parts'][part];folder='inputs/han-compat' if part!='RareB' else 'inputs/han-companions';p=root/folder/(row['stem']+'.ttf');assert sha(p)==row['hashes']['ttf'];f=TTFont(p,recalcTimestamp=False);order=list(f.getGlyphOrder());changes={}
  for cp in SPACES:
   assert cp not in f.getBestCmap();n=bc[cp];assert b['glyf'][n].numberOfContours==0;new=f'baseSpace{cp:04X}';f['glyf'][new]=copy.deepcopy(b['glyf'][n]);f['hmtx'][new]=b['hmtx'][n];order.append(new)
   for tab in f['cmap'].tables:
    if tab.isUnicode() and tab.format in (4,12):tab.cmap[cp]=new
   changes[f'U+{cp:04X}']={'base_glyph':n,'metric':b['hmtx'][n]}
  f.setGlyphOrder(order)
  for rec in list(f['name'].names):
   if rec.nameID in (3,5):f['name'].setName('0.003;MRMO;'+row['stem'] if rec.nameID==3 else 'Version 0.003',rec.nameID,rec.platformID,rec.platEncID,rec.langID)
  f['head'].fontRevision=.003;f.recalcTimestamp=False;f.save(out/(row['stem']+'.ttf'));f.flavor='woff2';f.save(out/(row['stem']+'.woff2'));result[part]={'family':row['family'],'stem':row['stem'],'source':str(Path(folder)/(row['stem']+'.ttf')),'source_sha256':sha(p),'spaces':changes,'hashes':{e:sha(out/(row['stem']+'.'+e)) for e in ('ttf','woff2')},'sizes':{e:(out/(row['stem']+'.'+e)).stat().st_size for e in ('ttf','woff2')}};print(part,flush=True)
 (out/'manifest.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--output',type=Path);a=p.parse_args();build(a.root,a.output or a.root/'inputs/han-spacefix')
