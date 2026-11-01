"""Metadata-only derivatives of pinned, validated Morimo inputs; no donor rebuild."""
import argparse,hashlib,json,shutil
from pathlib import Path
from fontTools.ttLib import TTFont

PINS = {
'inputs/prose-equal/MorimoProseZen-Regular.ttf':'967a944dc6c41b7d360cc571894c63d090a0734c84b86bce45535e25a6aea791',
'inputs/prose-han/MorimoProseHanJP-Regular.ttf':'3e3b2b34f9a4d6c057a82c9be62b49c8f1be06be43057c5bd508843eeb5435fb',
'inputs/prose-han/MorimoProseHanRareA-Regular.ttf':'1b739003ab6ff77e51c86176f753724ed1ef1eae398ce1002a6007266aa85b52',
'inputs/prose-han/MorimoProseHanRareB-Regular.ttf':'525ebe433014f099899e0b9aa807bffcc4116be69eaf20f986eaa345a5992bb4',
'inputs/terminal-ratio35/MorimoCodeJP95TerminalAddonsRatio35-Regular.ttf':'175ee5b2de7a1c6cb2337837ad4929b7aa312a3f957a93d62af371d1d35bdc88',
'inputs/han-spacefix/MorimoRatio35HanJP-Regular.ttf':'80a5f20d4167f3d27c700ccd09b746761c4cd857662c6775206dcfc6f65adf85',
'inputs/han-spacefix/MorimoRatio35HanRareA-Regular.ttf':'58c3a5fd899ccd38be623b3aaa1885348ab0ae5113d2cae68ef0bde55365e1fe',
'inputs/han-spacefix/MorimoRatio35HanRareB-Regular.ttf':'4281c85fd35e31ed1073c0d39ceb44dd4b6ffab32990b05461cd33b387a73f3c'}
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def build(root,out):
 out.mkdir(parents=True,exist_ok=True); rows=[]
 for kind,eng,jp,base,han,old in [('prose','Suminoha Maru Gothic','墨羽 丸ゴシック','inputs/prose-equal/MorimoProseZen-Regular.ttf','inputs/prose-han','Morimo Prose Zen'),('code','Suminoha Maru Code 35 NF','墨羽 丸コード 35 NF','inputs/terminal-ratio35/MorimoCodeJP95TerminalAddonsRatio35-Regular.ttf','inputs/han-spacefix','Morimo Code JP95 Terminal Addons Ratio35')]:
  sources=[(Path(base),'','',old)]
  for part in ['JP','RareA','RareB']:
   stem=('MorimoProseHan' if kind=='prose' else 'MorimoRatio35Han')+part+'-Regular.ttf'
   sources.append((Path(han)/stem,' Han '+part,' 漢字 '+part,('Morimo Prose Han ' if kind=='prose' else 'Morimo Ratio35 Han ')+part))
  for src,suffix,jsuffix,oldname in sources:
   assert sha(root/src)==PINS[str(src)],src
   fam=eng+suffix;jfam=jp+jsuffix;ps=fam.replace(' ','')+'-Regular';f=TTFont(root/src,recalcTimestamp=False)
   n=f['name'];n.names=[r for r in n.names if r.nameID not in {1,2,3,4,6,16,17,18,21,22,25}]
   for lang,fn in [(0x409,fam),(0x411,jfam)]:
    for id,value in {1:fn,2:'Regular',3:ps+';Suminoha;20261028',4:fn+' Regular',6:ps,16:fn,17:'Regular'}.items(): n.setName(value,id,3,1,lang)
   for id,value in {1:fam,2:'Regular',3:ps+';Suminoha;20261028',4:fam+' Regular',6:ps,16:fam,17:'Regular'}.items(): n.setName(value,id,0,4,0)
   path=out/(ps+'.ttf');f.save(path);f.flavor='woff2';f.save(path.with_suffix('.woff2'))
   lic=out/'licenses'/ps;lic.mkdir(parents=True,exist_ok=True)
   if suffix: shutil.copytree(root/han/'licenses',lic,dirs_exist_ok=True)
   elif kind=='prose':
    for p in (root/'inputs/prose-equal').glob('Prose-*'):shutil.copy2(p,lic/p.name)
   else:shutil.copytree(root/'inputs/terminal-ratio35/licenses',lic,dirs_exist_ok=True)
   rows.append(dict(kind=kind,family=fam,japanese_family=jfam,old_family=oldname,postscript=ps,source=str(src),source_sha256=sha(root/src),file=path.name,sha256=sha(path),woff2_sha256=sha(path.with_suffix('.woff2'))))
 (out/'manifest.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--out',type=Path);a=p.parse_args();build(a.root,a.out or a.root/'fonts/code35')
