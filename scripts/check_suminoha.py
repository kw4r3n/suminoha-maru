"""Metadata-only invariance, shaping and native rendering checks, no installation."""
import argparse,hashlib,json,os,subprocess,sys,tempfile,unicodedata
from pathlib import Path
from fontTools.ttLib import TTFont
from build_suminoha import sha

def config(rows,out):
 s=['<?xml version="1.0"?><!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd"><fontconfig>']
 for r in rows:
  s.append(f'<alias binding="strong"><family>{r["old_family"]}</family><prefer><family>{r["family"]}</family></prefer></alias>')
 for r in rows:
  s.append(f'<match target="scan"><test name="postscriptname" compare="eq"><string>{r["postscript"]}</string></test><edit name="family" mode="append" binding="strong"><string>{r["old_family"]}</string></edit></match>')
 for kind in ['prose','code']:
  group=[r for r in rows if r['kind']==kind];base=group[0]
  for family in [base['family'],base['japanese_family']]:
   s.append(f'<match target="pattern"><test name="family" qual="any" compare="eq"><string>{family}</string></test><edit name="family" mode="append" binding="strong">'+''.join('<string>'+r['family']+'</string>' for r in group[1:])+'</edit></match>')
 s.append('</fontconfig>');(out/'67-suminoha.conf').write_text('\n'.join(s)+'\n')

def check(root,out,installed=False):
 sys.path.insert(0,str(root/'scripts'));from hb import Shaper
 rows=json.loads((out/'manifest.json').read_text());report={'fonts':[]};ps=set();samples=['ABC abc 0123','日本語 かな カナ','a\u0301 x\u0302\u0301 q\u0308','-> => === != <= >= /* */','🤖 ✅ ❌ \ue0b0\ue0b2 \uf101','𠀀𠮷麤豈丽']
 for r in rows:
  if installed: continue
  src=root/r['source'];p=out/r['file'];assert sha(src)==r['source_sha256'] and sha(p)==r['sha256'];a=TTFont(src);b=TTFont(p);w=TTFont(p.with_suffix('.woff2'))
  assert a.keys()==b.keys() and a.getGlyphOrder()==b.getGlyphOrder()
  for t in a.keys():
   if t not in ['GlyphOrder','name','head']:assert a[t].compile(a)==b[t].compile(b),(r['family'],t)
   if t not in ['GlyphOrder','head','loca']:assert b[t].compile(b)==w[t].compile(w),(r['family'],t,'woff')
  ah=a['head'].compile(a);bh=b['head'].compile(b);assert ah[:8]+ah[12:]==bh[:8]+bh[12:]
  assert r['postscript'] not in ps and len(r['postscript'])<=63;ps.add(r['postscript'])
  for id in [0,13,14]:assert [(n.platformID,n.platEncID,n.langID,n.string) for n in a['name'].names if n.nameID==id]==[(n.platformID,n.platEncID,n.langID,n.string) for n in b['name'].names if n.nameID==id]
  sa,sb=Shaper(src),Shaper(p);profiles=[{}, {'calt':0},{'calt':1,'ss03':1,'ss05':1,'ss07':1,'ss08':1,'ss09':1,'ss10':1,'ss11':1,'cv63':0,'cv64':1,'cv66':1}]
  for text in samples:
   for prof in profiles:assert sa.shape(text,features=prof)==sb.shape(text,features=prof)
  sa.close();sb.close();report['fonts'].append({'family':r['family'],'cmap':len(b.getBestCmap()),'glyphs':len(b.getGlyphOrder()),'non_name_tables_identical':True,'HB_checks':len(samples)*len(profiles)})
 config(rows,out)
 mapping=json.loads((root/'inputs/han-compat/mapping.json').read_text());text=' '.join(chr(int(cp[2:],16)) for cp in sorted(mapping));extra='\n日本語 ABC 𠀀 𠀁 𠀂\n𠀀\u00a0𠀁\u00a0𠀂\n𠀀\u3000𠀁\u3000𠀂\n𠀀\t𠀁\n麤 𠮷'
 with tempfile.TemporaryDirectory(prefix='suminoha-check-') as td:
  td=Path(td);env=os.environ.copy()
  if not installed:
   cfg=td/'fonts.conf';cfg.write_text(f'<fontconfig><dir>{out.resolve()}</dir><cachedir>{td}/cache</cachedir><include>{out.resolve()}/67-suminoha.conf</include></fontconfig>');env['FONTCONFIG_FILE']=str(cfg)
  for r in rows:
   if installed:
    physical=Path.home()/'.local/share/fonts'/r['postscript'].removesuffix('-Regular')/r['file'];assert sha(physical)==r['sha256']
   for name in [r['family'],r['japanese_family'],r['old_family']]:
    path=Path(subprocess.check_output(['fc-match',name,'-f','%{file}'],env=env,text=True));expected=r['sha256']
    if installed and ' Han ' in r['family']: expected=next(x['sha256'] for x in rows if x['kind']==r['kind'] and ' Han ' not in x['family'])
    assert sha(path)==expected,(name,str(path))
  for kind in ['prose','code']:
   group=[r for r in rows if r['kind']==kind];base=group[0];fonts={r['sha256']:TTFont(out/r['file']) for r in group};union=set().union(*(set(f.getBestCmap()) for f in fonts.values()));assert len(union)==(105365 if kind=='prose' else 105719)
   serial=td/(kind+'.json');subprocess.run(['pango-view','--no-display','--font='+base['family']+' 12','--language=ja','--width=900','--wrap=word-char','--text='+text+extra,'--serialize-to='+str(serial)],check=True,env=env,stdout=subprocess.DEVNULL);d=json.loads(serial.read_text());assert d['output']['unknown-glyphs']==0
   counts={'raw':0,'canonical':0};seen=set()
   for line in d['output']['lines']:
    for run in line['runs']:
     f=fonts[run['font']['checksum']];c=f.getBestCmap()
     for g in run['glyphs']:
      cp=ord(run['text'].encode()[g['log-cluster']:].decode()[0]);key=f'U+{cp:04X}'
      if key not in mapping:continue
      seen.add(cp);raw=c.get(cp);nf=c.get(ord(unicodedata.normalize('NFC',chr(cp))))
      if raw and f.getGlyphID(raw)==g['glyph']:counts['raw']+=1
      else:assert nf and f.getGlyphID(nf)==g['glyph'];counts['canonical']+=1
   assert len(seen)==923
   sample='日本語 ABC abc 0123 同じ文字のまま\nまるい本文と Code -> === !=\n漢字: 麤 𠮷 𠀀 𰀀 𱍐\n空白: 𠀀 𠀁 / 𠀀\u00a0𠀁 / 𠀀\u3000𠀁\n互換: 豈 更 丽 丸'
   if kind=='code':sample+='\n🤖 ✅ ❌  \ue0b0\ue0b0\ue0b2\ue0b2'
   subprocess.run(['pango-view','--no-display','--font='+base['family']+' 18','--language=ja','--margin=20','--text='+sample,'--output='+str(out/(kind+('-installed' if installed else '-preview')+'.png')),'--serialize-to='+str(serial)],env=env,check=True);assert json.loads(serial.read_text())['output']['unknown-glyphs']==0
   if not installed:
    olddir=td/('old-'+kind);olddir.mkdir()
    for r in group:(olddir/Path(r['source']).name).symlink_to(root/r['source'])
    oldcfg=td/('old-'+kind+'.conf');oldcfg.write_text('<fontconfig><dir>'+str(olddir)+'</dir><cachedir>'+str(td/'old-cache')+'</cachedir><match target="pattern"><test name="family" compare="eq"><string>'+base['old_family']+'</string></test><edit name="family" mode="append" binding="strong">'+''.join('<string>'+r['old_family']+'</string>' for r in group[1:])+'</edit></match></fontconfig>')
    oldenv=env|{'FONTCONFIG_FILE':str(oldcfg)};oldimg=td/(kind+'-old.png')
    subprocess.run(['pango-view','--no-display','--font='+base['old_family']+' 18','--language=ja','--margin=20','--text='+sample,'--output='+str(oldimg)],env=oldenv,check=True)
    from PIL import Image,ImageChops
    assert Image.open(oldimg).size==Image.open(out/(kind+'-preview.png')).size
    assert ImageChops.difference(Image.open(oldimg).convert('RGB'),Image.open(out/(kind+'-preview.png')).convert('RGB')).getbbox() is None
   report[kind]={'union':len(union),'all923_unknown':0,'normalization':counts,'sample_unknown':0}
 report['installed']=installed;(out/('installed-validation.json' if installed else 'validation.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--out',type=Path);p.add_argument('--installed',action='store_true');a=p.parse_args();check(a.root,a.out or a.root/'fonts/code35',a.installed)
