import json,sys,hashlib,subprocess,os,unicodedata
from pathlib import Path
from fontTools.ttLib import TTFont

def check(root,out):
 sys.path.insert(0,str(root/'scripts'));from hb import Shaper
 m=json.loads((out/'manifest.json').read_text());result=[];seen=set();comp={};shapers={}
 for r in m:
  a=TTFont(root/r['source']);b=TTFont(out/r['file']);w=TTFont((out/r['file']).with_suffix('.woff2'));assert a.getGlyphOrder()==b.getGlyphOrder();assert a.getBestCmap()==b.getBestCmap();assert (b['hhea'].ascent,b['hhea'].descent,b['hhea'].lineGap)==(1200,-350,0)
  for t in a.keys():
   if t not in ['GlyphOrder','name','head','hmtx','OS/2']:assert a.reader[t]==b.reader[t],(r['family'],t)
   if t not in ['GlyphOrder','head','loca']:assert b[t].compile(b)==w[t].compile(w),(r['family'],t,'woff')
  a['OS/2'].usFirstCharIndex=b['OS/2'].usFirstCharIndex;assert a['OS/2'].compile(a)==b['OS/2'].compile(b)
  c=b.getBestCmap();han=' Han ' in r['family'];spaces={c[32],c[160]}
  for n,metric in a['hmtx'].metrics.items():assert b['hmtx'][n]==((540,0) if han and n in spaces else metric)
  for cp,n in c.items():
   if han:assert b['hmtx'][n][0]==(540 if cp in [32,160] else 1080)
  if seen:assert set(c)&seen=={32,160,0x3000}
  seen.update(c);s=Shaper(out/r['file']);old=Shaper(root/r['source']);texts=['ABC iii WWW','日本語 あいう','-> !== === <!--','a\u0301 x\u0302\u0301 q\u0308','🤖✅❌\ue0b0\ue0b2','𠀀𠮷㐀麤豈丽']
  for text in texts:
   if han: text=text.replace(' ','')
   for feat in [{},{'calt':0},{'calt':1,'ss03':1,'ss05':1,'ss07':1,'cv64':1,'cv66':1}]:assert s.shape(text,features=feat)==old.shape(text,features=feat)
  shapers[r['family']]=s;result.append({'family':r['family'],'cmap':len(c),'glyphs':len(b.getGlyphOrder()),'Han_or_primary_widths':'540/1080','unchanged_glyphs_features':True,'OS2_first_character_index':'space32 corrected when table reserialized','HB_checks':18})
 assert len(seen)==105719
 mapping=json.loads((root/'inputs/han-compat/mapping.json').read_text())
 for cp,r in mapping.items():
  part={'JP':'JP','RareA':'RareA','RareB':'RareB'}[r['part']];s=shapers['Suminoha Maru Code 12 NF Han '+part];row=s.shape(chr(int(cp[2:],16)));assert len(row)==1 and row[0]['gid'] and row[0]['advance']==1080
 (out/'validation.json').write_text(json.dumps({'fonts':result,'package_union':len(seen),'compatibility_HB':923,'limits':'Finite native renderer checks separately; no universal terminal acceptance.'},indent=2)+'\n');print('Code12 invariance, widths, formats and shaping passed')
if __name__=='__main__':check(Path(sys.argv[1]),Path(sys.argv[2]))
