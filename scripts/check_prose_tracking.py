"""Validate prose tracking metrics, unchanged ink/layout and finite real shaping."""
import argparse,copy,json,sys
from pathlib import Path
from fontTools.ttLib import TTFont
from build_prose_tracking import sha,weights,DELTA

def check(root,out):
 sys.path.insert(0,str(root/'scripts'));from hb import Shaper
 m=json.loads((out/'manifest.json').read_text());report=[];union=set();probes=0
 for r in m:
  src=root/r['source'];p=out/r['file'];assert sha(src)==r['source_sha256'] and sha(p)==r['sha256'];a=TTFont(src);b=TTFont(p);w=TTFont(p.with_suffix('.woff2'));primary=' Han ' not in r['family'];counts,policy=weights(a) if primary else ({n:int(v[0]>0) for n,v in a['hmtx'].metrics.items()},None)
  assert a.getGlyphOrder()==b.getGlyphOrder() and a.getBestCmap()==b.getBestCmap();union.update(b.getBestCmap());assert (b['hhea'].ascent,b['hhea'].descent,b['hhea'].lineGap)==(1150,-350,0)
  for n,(aw,lsb) in a['hmtx'].metrics.items():assert b['hmtx'][n]==(aw+DELTA*counts[n],lsb)
  for tag in a.keys():
   if tag not in ['GlyphOrder','name','head','hhea','hmtx','OS/2','GPOS']:assert a.reader[tag]==b.reader[tag],(r['family'],tag)
   if tag not in ['GlyphOrder','head','loca']:assert b[tag].compile(b)==w[tag].compile(w),(r['family'],tag,'woff')
  if primary:
   table=copy.deepcopy(b['GPOS'].table);index=len(a['GPOS'].table.LookupList.Lookup);assert len(table.LookupList.Lookup)==index+1;assert table.LookupList.Lookup[-1].LookupType==2
   table.LookupList.Lookup.pop();table.LookupList.LookupCount-=1
   for f in table.FeatureList.FeatureRecord:
    if f.FeatureTag=='mark':assert f.Feature.LookupListIndex.pop()==index;f.Feature.LookupCount-=1
   old=b['GPOS'].table;b['GPOS'].table=table;assert b['GPOS'].compile(b)==a['GPOS'].compile(a);b['GPOS'].table=old
  elif 'GPOS' in a:assert a.reader['GPOS']==b.reader['GPOS']
  for id in [0,1,2,4,6,13,14,16,17]:assert [(x.platformID,x.platEncID,x.langID,x.string) for x in a['name'].names if x.nameID==id]==[(x.platformID,x.platEncID,x.langID,x.string) for x in b['name'].names if x.nameID==id]
  s,t=Shaper(src),Shaper(p)
  if primary:
   samples=['日本語 ABC abc 0123','office fi fl IJ No.','q̈ x̂́ a̋ α̈ ộ','ｶﾞ ﾊﾟ ｳﾞ aﾞ fiﾞ','Árvíztűrő Tiếng Việt Καλημέρα','A\u00a0V A\u3000V','👩','𠀀 豈']
   tags=sorted({x.FeatureTag for x in a['GSUB'].table.FeatureList.FeatureRecord});profiles=[{}, {'kern':0}]+[{tag:v} for tag in tags for v in [0,1]]
   for text in samples:
    for feature in profiles:
     aa=s.shape(text,features=feature);bb=t.shape(text,features=feature);assert [(x['gid'],x['cluster']) for x in aa]==[(x['gid'],x['cluster']) for x in bb];expected=DELTA*sum(counts[x['glyph']] for x in aa);assert sum(x['advance'] for x in bb)-sum(x['advance'] for x in aa)==expected,(text,feature)
     probes+=1
   # Absolute positions within each valid combining cluster remain unchanged.
   marks=['q̈','x̂́','a̋','α̈','ộ','ｶﾞ','ﾊﾟ','ｳﾞ','aﾞ','fiﾞ']
   for text in marks:
    def pos(sh):
     pen=0;result=[]
     for x in sh.shape(text):result.append((x['gid'],pen+x['dx'],x['dy']));pen+=x['advance']
     return result
    assert pos(s)==pos(t),(text,pos(s),pos(t))
   for text,lang,n in [('fi','en',2),('fl','en',2),('IJ','nl',2),('ij','nl',2)]:assert sum(x['advance'] for x in t.shape(text,language=lang))-sum(x['advance'] for x in s.shape(text,language=lang))==20*n
  else:
   for cp in sorted(b.getBestCmap())[::max(1,len(b.getBestCmap())//40)]:
    aa=s.shape(chr(cp));bb=t.shape(chr(cp));assert [x['gid'] for x in aa]==[x['gid'] for x in bb];assert sum(x['advance'] for x in bb)-sum(x['advance'] for x in aa)==20;probes+=1
  report.append({'family':r['family'],'version':b['name'].getDebugName(5),'cmap':len(b.getBestCmap()),'glyphs':len(b.getGlyphOrder()),'outline_cmap_glyph_order_GSUB_GDEF_unchanged':True,'original_GPOS_preserved':True,'mapped_space_advances':{hex(cp):b['hmtx'][b.getBestCmap()[cp]][0] for cp in [32,160,0x3000]}})
 assert len(union)==105365
 (out/'validation.json').write_text(json.dumps({'fonts':report,'package_union':len(union),'shaping_checks':probes,'all_metrics_checked':True,'TTF_WOFF2_equivalent':True,'valid_mark_cluster_positions_preserved':True,'limits':'Encoded fi/fl/IJ/numero reuse weighted ligature advances; ligature ink/carets retained. mark=0 and arbitrary invalid repeated halfwidth voicing not guaranteed.'},indent=2)+'\n');print('Prose tracking invariance, metrics, formats and finite shaping passed',probes,flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--out',type=Path);a=p.parse_args();check(a.root,a.out or a.root/'fonts/gothic')
