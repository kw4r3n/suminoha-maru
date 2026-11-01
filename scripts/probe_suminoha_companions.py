"""Finite direct-family/fallback Pango tests; run under desired FONTCONFIG_FILE."""
import json,sys,subprocess,tempfile,unicodedata
from pathlib import Path
from fontTools.ttLib import TTFont

def probe(root,out,code12):
 out.mkdir(parents=True,exist_ok=True);prior=json.loads((root/'fonts/code35/manifest.json').read_text());new=json.loads((code12/'manifest.json').read_text());fonts={r['sha256']:TTFont((root/'fonts/code35' if r in prior else code12)/r['file']) for r in prior+new};report={};mapping=json.loads((root/'inputs/han-compat/mapping.json').read_text())
 for en,latin in [('Suminoha Maru Code 35 NF',648),('Suminoha Maru Code 12 NF',540)]:
  group=[]
  for suffix in ['', ' Han JP',' Han RareA',' Han RareB']:
   fam=en+suffix;text='AiW 㐀 䶶 𪑓 一\u00a0㐀\u3000䶶';p=out/'probe.json';subprocess.run(['pango-view','--no-display','--pixels','--font='+fam+' 1000','--text='+text,'--serialize-to='+str(p)],check=True,stdout=subprocess.DEVNULL);d=json.loads(p.read_text());assert d['output']['unknown-glyphs']==0;runs=[]
   for line in d['output']['lines']:
    for r in line['runs']:
     assert r['font']['checksum'] in fonts,r['font'];ft=fonts[r['font']['checksum']];assert ft['name'].getDebugName(1).startswith(en),r['font']
     for g in r['glyphs']:
      cp=ord(r['text'].encode()[g['log-cluster']:].decode()[0]);expected=latin if cp in list(map(ord,'AiW '))+[160] else 1080;assert g['width']==expected*1024,(fam,cp,g['width'],expected)
     runs.append({'text':r['text'],'font':r['font']['description'],'widths':[g['width']/1024 for g in r['glyphs']]})
   for name in [fam, fam.replace('Suminoha Maru Code','墨羽 丸コード').replace(' Han ',' 漢字 ')]:
    fp=Path(subprocess.check_output(['fc-match',name,'-f','%{file}'],text=True));assert fp.stem==en.replace(' ','')+'-Regular' # complete primary is the default match; charset-specific matches retain Han providers
   group.append({'family':fam,'unknown':0,'runs':runs})
  text=' '.join(chr(int(cp[2:],16)) for cp in sorted(mapping))+'\n日本語 ABC 𠀀\u00a0𠀁\u3000𠀂\t𠀀';p=out/'all923.json';subprocess.run(['pango-view','--no-display','--font='+en+' 12','--width=900','--wrap=word-char','--text='+text,'--serialize-to='+str(p)],check=True,stdout=subprocess.DEVNULL);d=json.loads(p.read_text());assert d['output']['unknown-glyphs']==0;counts={'raw':0,'canonical':0};seen=set()
  for line in d['output']['lines']:
   for r in line['runs']:
    ft=fonts[r['font']['checksum']];c=ft.getBestCmap()
    for g in r['glyphs']:
     cp=ord(r['text'].encode()[g['log-cluster']:].decode()[0]);key=f'U+{cp:04X}'
     if key not in mapping:continue
     seen.add(cp);raw=c.get(cp);nf=c.get(ord(unicodedata.normalize('NFC',chr(cp))))
     if raw and ft.getGlyphID(raw)==g['glyph']:counts['raw']+=1
     else:assert nf and ft.getGlyphID(nf)==g['glyph'];counts['canonical']+=1
  assert len(seen)==923;report[en]={'direct_family_tests':group,'all923_unknown':0,'compatibility_normalization':counts}
  sample='日本語 ABC iii WWW 0123 / 㐀 䶶 𪑓\nEnglish and 日本語 / 一二三四五六七八九十\n𠀀 𠀁 / 𠀀\u00a0𠀁 / 𠀀\u3000𠀁\n-> === !==  x̂́ q̈  / \ue0b0\ue0b0\ue0b2\ue0b2\n豈 更 丽 丸'
  for suffix in ['', ' Han JP']:
   name=('35' if latin==648 else '12')+('-main' if not suffix else '-han-direct');subprocess.run(['pango-view','--no-display','--pixels','--font='+en+suffix+' 24','--text='+sample,'--margin=18','--output='+str(out/(name+'.png')),'--serialize-to='+str(p)],check=True);assert json.loads(p.read_text())['output']['unknown-glyphs']==0
 (out/'native-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');(out/'probe.json').unlink();(out/'all923.json').unlink();print('Direct-family ASCII/space/Han Pango widths correct for both ratios; all923 corpora pass')
if __name__=='__main__':probe(Path(sys.argv[1]),Path(sys.argv[2]),Path(sys.argv[3]))
