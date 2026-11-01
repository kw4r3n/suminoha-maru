"""Read-only installed-font verification plus headless synthetic Pango evidence."""
import argparse,json,subprocess,tempfile,unicodedata,sys
from pathlib import Path
from fontTools.ttLib import TTFont

def probe(root):
 sys.path.insert(0,str(root/'scripts'));from build_han_companions import sha
 m=json.loads((root/'inputs/han-spacefix/manifest.json').read_text());mapping=json.loads((root/'inputs/han-compat/mapping.json').read_text());families={'base':'Morimo Code JP95 Terminal Addons Ratio35'}|{k:r['family'] for k,r in m.items()};fonts={};resolved={}
 for key,fam in families.items():
  path=Path(subprocess.check_output(['fc-match',fam,'-f','%{file}'],text=True));expected='175ee5b2de7a1c6cb2337837ad4929b7aa312a3f957a93d62af371d1d35bdc88' if key=='base' else m[key]['hashes']['ttf'];assert sha(path)==expected;(fonts.update({expected:TTFont(path)}));resolved[fam]={'path':str(path),'sha256':expected}
 text=' '.join(chr(int(cp[2:],16)) for cp in sorted(mapping));extra='\n日本語 ABC 𠀀 𠀁 𠀂\n𠀀\u00a0𠀁\u00a0𠀂\n𠀀\u3000𠀁\u3000𠀂\n𠀀\t𠀁\n麤 𠮷';counts={'raw':0,'canonical':0};seen=set()
 with tempfile.TemporaryDirectory(prefix='morimo-pango-fixed-') as td:
  p=Path(td)/'all.json';subprocess.run(['pango-view','--no-display','--font=Morimo Code JP95 Terminal Addons Ratio35 12','--language=ja','--width=900','--wrap=word-char','--text='+text+extra,'--serialize-to='+str(p)],check=True,stdout=subprocess.DEVNULL);d=json.loads(p.read_text());assert d['output']['unknown-glyphs']==0
  for line in d['output']['lines']:
   for run in line['runs']:
    f=fonts[run['font']['checksum']];c=f.getBestCmap()
    for g in run['glyphs']:
     cp=ord(run['text'].encode()[g['log-cluster']:].decode()[0]);k=f'U+{cp:04X}'
     if k not in mapping:continue
     seen.add(cp);raw=c.get(cp);nf=c.get(ord(unicodedata.normalize('NFC',chr(cp))));gid=g['glyph']
     if raw and f.getGlyphID(raw)==gid:counts['raw']+=1
     else:assert nf and f.getGlyphID(nf)==gid;counts['canonical']+=1
 assert len(seen)==923
 out=root/'specimens/han-spacefix';out.mkdir(exist_ok=True);sample='既存 日本語 ABC 麤 𠮷\nASCII: 𠀀 𠀁 𠀂\nNBSP: 𠀀\u00a0𠀁\u00a0𠀂\n全角: 𠀀\u3000𠀁\u3000𠀂\n互換: 豈 更 車 丽 丸 𪘀';serial=out/'installed-layout.json';subprocess.run(['pango-view','--no-display','--font=Morimo Code JP95 Terminal Addons Ratio35 18','--language=ja','--margin=18','--text='+sample,'--output='+str(out/'installed-pango.png'),'--serialize-to='+str(serial)],check=True);assert json.loads(serial.read_text())['output']['unknown-glyphs']==0
 result={'resolved':resolved,'Pango_all923':counts,'unknown_glyphs':0,'spaces_tested':['U+0020','U+00A0','U+3000','TAB','LF'],'native_sample_unknown':0,'limits':'No live application restart; other whitespace/IVS/regional/vertical behavior not promised.'};(root/'reports/han-spacefix-pango.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);a=p.parse_args();probe(a.root)
