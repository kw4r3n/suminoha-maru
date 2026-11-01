"""Build Code12 from pinned Grid and unchanged Code35 Han shapes."""
import argparse,json,shutil,hashlib
from pathlib import Path
from fontTools.ttLib import TTFont

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def build(root,out):
 out.mkdir(parents=True,exist_ok=True);rows=[];assert sha(root/'fonts/code35/manifest.json')=='91ed519d48c4a4ad540785d3bd5e4cc679cb974a8ab2475d394bd2e4d150e392';prior=json.loads((root/'fonts/code35/manifest.json').read_text());inputs=[dict(source='inputs/terminal-addons/MorimoCodeJP95TerminalAddonsGrid-Regular.ttf',sha256='73147c5213b81e6e13d5dc5103653ae0d27d5c885bdec8bc93f744dc1dc2697c',suffix='',jsuffix='',license='inputs/terminal-ratio35/licenses')]
 for part in ['JP','RareA','RareB']:
  r=next(x for x in prior if x['family']=='Suminoha Maru Code 35 NF Han '+part);inputs.append(dict(source='fonts/code35/'+r['file'],sha256=r['sha256'],suffix=' Han '+part,jsuffix=' 漢字 '+part,license='fonts/code35/licenses/'+r['postscript']))
 for r in inputs:
  src=root/r['source'];assert sha(src)==r['sha256'];f=TTFont(src,recalcTimestamp=False);family='Suminoha Maru Code 12 NF'+r['suffix'];jp='墨羽 丸コード 12 NF'+r['jsuffix'];ps=family.replace(' ','')+'-Regular'
  if r['suffix']:
   for cp in [32,160]:n=f.getBestCmap()[cp];assert not f['glyf'][n].numberOfContours;f['hmtx'][n]=(540,0)
   f['OS/2'].xAvgCharWidth=1080
  n=f['name'];n.names=[x for x in n.names if x.nameID not in {1,2,3,4,6,16,17,18,21,22,25}]
  for platform,encoding,lang,fn in [(3,1,0x409,family),(3,1,0x411,jp),(0,4,0,family)]:
   for id,val in {1:fn,2:'Regular',3:ps+';Suminoha;20261028',4:fn+' Regular',6:ps,16:fn,17:'Regular'}.items():n.setName(val,id,platform,encoding,lang)
  p=out/(ps+'.ttf');f.save(p);f.flavor='woff2';f.save(p.with_suffix('.woff2'));shutil.copytree(root/r['license'],out/'licenses'/ps,dirs_exist_ok=True);rows.append(dict(family=family,japanese_family=jp,postscript=ps,file=p.name,source=r['source'],source_sha256=r['sha256'],sha256=sha(p),woff2_sha256=sha(p.with_suffix('.woff2'))))
 (out/'manifest.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--out',type=Path);a=p.parse_args();build(a.root,a.out or a.root/'fonts/code12')
