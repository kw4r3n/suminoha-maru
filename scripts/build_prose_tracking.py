"""Prose-only trailing advance tracking, preserving outline/layout tables."""
import argparse,hashlib,json,shutil,unicodedata
from pathlib import Path
from fontTools.ttLib import TTFont
VERSION='0.008';DELTA=20
TRACKING_NOTICE='Suminoha Maru Gothic revision0.008 adds20/1000em trailing advance per tracked base, with source-glyph-count ligature totals and a bounded halfwidth-voicing attachment adjustment. Outlines and all original donor attribution/licenses are retained. Full original OFL/Unicode notices in this directory remain applicable. No new source font or glyph design.\n'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def weights(f):
 c=f.getBestCmap();cl=getattr(f['GDEF'].table.GlyphClassDef,'classDefs',{});excluded={n for cp,n in c.items() if unicodedata.category(chr(cp)).startswith('M') or cp in [0xff9e,0xff9f]};excluded|={n for n,k in cl.items() if k==3};w={n:0 if a==0 or n in excluded else 1 for n,(a,_) in f['hmtx'].metrics.items()};initial=dict(w)
 for iteration in range(32):
  before=dict(w)
  for l in f['GSUB'].table.LookupList.Lookup:
   for s in l.SubTable:
    pairs=[]
    if l.LookupType==1:pairs=list(s.mapping.items())
    elif l.LookupType==3:pairs=[(a,b) for a,bs in s.alternates.items() for b in bs]
    for a,b in pairs:
     if w[b] and w[a]:w[b]=max(w[b],w[a])
    if l.LookupType==4:
     for a,rs in s.ligatures.items():
      for r in rs:
       n=sum(w[x] for x in [a]+r.Component)
       if w[r.LigGlyph]:w[r.LigGlyph]=max(w[r.LigGlyph],n)
  assert max(w.values())<=8,'Ambiguous recursive ligature weighting'
  if w==before:break
 else:raise AssertionError('Ligature weights did not converge')
 return w,{'zero_or_marks_preserved':sum(x==0 for x in w.values()),'multi_base_glyphs':{n:v for n,v in w.items() if v>1},'positive_spacing_marks_preserved':sorted(n for n in excluded if f['hmtx'][n][0]>0)}
def halfwidth_attachment(f,w):
 from fontTools.otlLib.builder import buildPairPosGlyphsSubtable,buildLookup,buildValue
 from collections import defaultdict
 classes=defaultdict(list)
 for name,count in w.items():
  if count:classes[count].append(name)
 voices=tuple(f.getBestCmap()[cp] for cp in [0xff9e,0xff9f])
 pairs={(name,voice):(buildValue({'XAdvance':-DELTA*count}),buildValue({'XAdvance':DELTA*count})) for count,names in classes.items() for name in names for voice in voices}
 sub=buildPairPosGlyphsSubtable(pairs,f.getReverseGlyphMap());lookup=buildLookup([sub]);table=f['GPOS'].table;idx=len(table.LookupList.Lookup);table.LookupList.Lookup.append(lookup);table.LookupList.LookupCount=len(table.LookupList.Lookup)
 for record in table.FeatureList.FeatureRecord:
  if record.FeatureTag=='mark':record.Feature.LookupListIndex.append(idx);record.Feature.LookupCount=len(record.Feature.LookupListIndex)
 return {'lookup_index':idx,'feature':'mark','scope':'single halfwidth voiced/semi-voiced mark after a tracked base','moves_trailing_tracking_after_mark':True}
def build(root,out,primary_only=False):
 out.mkdir(parents=True,exist_ok=True);source=json.loads((root/'fonts/code35/manifest.json').read_text());rows=[];previous=json.loads((out/'manifest.json').read_text()) if primary_only else []
 for r in source:
  if r['kind']!='prose':continue
  if primary_only and ' Han ' in r['family']:
   old=next(x for x in previous if x['file']==r['file']);assert sha(out/r['file'])==old['sha256'];rows.append(old);continue
  p=root/'fonts/code35'/r['file'];assert sha(p)==r['sha256'];f=TTFont(p,recalcTimestamp=False);assert f['head'].unitsPerEm==1000
  if ' Han ' not in r['family']:
   w,policy=weights(f);policy['halfwidth_attachment']=halfwidth_attachment(f,w)
  else:w={n:int(a>0) for n,(a,_) in f['hmtx'].metrics.items()};policy={'Han_and_empty_spaces':True}
  changes={}
  for n,(a,lsb) in list(f['hmtx'].metrics.items()):
   if w[n]:f['hmtx'][n]=(a+DELTA*w[n],lsb);changes[n]=DELTA*w[n]
  f['head'].fontRevision=float(VERSION);f['OS/2'].recalcAvgCharWidth(f)
  for rec in list(f['name'].names):
   val={3:VERSION+';Suminoha;'+r['postscript'],5:'Version '+VERSION}.get(rec.nameID)
   if val:f['name'].setName(val,rec.nameID,rec.platformID,rec.platEncID,rec.langID)
  target=out/r['file'];f.save(target);f.flavor='woff2';f.save(target.with_suffix('.woff2'));shutil.copytree(root/'fonts/code35/licenses'/r['postscript'],out/'licenses'/r['postscript'],dirs_exist_ok=True)
  (out/'licenses'/r['postscript']/'Tracking-NOTICE.txt').write_text(TRACKING_NOTICE)
  rows.append({**r,'source':'fonts/code35/'+r['file'],'source_sha256':r['sha256'],'sha256':sha(target),'woff2_sha256':sha(target.with_suffix('.woff2')),'version':VERSION,'tracking_units':DELTA,'changed_glyph_advances':len(changes),'policy':policy,'total_tracking_units':sum(changes.values())})
 (out/'manifest.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n');print('Built prose tracking0.008',flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--out',type=Path);p.add_argument('--primary-only',action='store_true');a=p.parse_args();build(a.root,a.out or a.root/'fonts/gothic',a.primary_only)
