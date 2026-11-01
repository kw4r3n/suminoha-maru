"""Uninstalled Prose Zen companions derived from pinned validated donor geometry."""
import argparse,copy,json,sys,tempfile
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.transformPen import TransformPen
SPACES=(0x20,0xa0,0x3000)
def build(root,out):
 sys.path.insert(0,str(root/'scripts'));from build_han_companions import sha
 base=root/'inputs/prose-equal/MorimoProseZen-Regular.ttf';assert sha(base)=='967a944dc6c41b7d360cc571894c63d090a0734c84b86bce45535e25a6aea791';b=TTFont(base);bc=b.getBestCmap();inputs=json.loads((root/'inputs/han-spacefix/manifest.json').read_text());out.mkdir(parents=True,exist_ok=True);result={}
 for part,row in inputs.items():
  src=root/'inputs/han-spacefix'/(row['stem']+'.ttf');assert sha(src)==row['hashes']['ttf'];a=TTFont(src);f=TTFont(src,recalcTimestamp=False);c=a.getBestCmap();assert set(c)&set(bc)==set(SPACES);gs=a.getGlyphSet();changes={}
  for cp,n in c.items():
   if cp in SPACES:f['glyf'][n]=copy.deepcopy(b['glyf'][bc[cp]]);f['hmtx'][n]=b['hmtx'][bc[cp]];continue
   g=a['glyf'][n];s=min(1,960/(g.xMax-g.xMin));dx=500-(g.xMin+g.xMax)*s/2;rec=DecomposingRecordingPen(gs);gs[n].draw(rec);pen=TTGlyphPen(None);tr=TransformPen(pen,(s,0,0,s,dx,0))
   for op,pts in rec.value:getattr(tr,op)(*pts)
   z=pen.glyph();z.recalcBounds(None);f['glyf'][n]=z;f['hmtx'][n]=(1000,z.xMin);changes[f'U+{cp:04X}']=[s,dx]
  fam='Morimo Prose Han '+part;stem='MorimoProseHan'+part+'-Regular'
  for rec in list(f['name'].names):
   vals={1:fam,4:fam+' Regular',6:stem,16:fam,17:'Regular',3:'0.001;MRMO;'+stem,5:'Version 0.001'}
   if rec.nameID in vals:f['name'].setName(vals[rec.nameID],rec.nameID,rec.platformID,rec.platEncID,rec.langID)
  f['hhea'].ascent=1150;f['hhea'].descent=-350;f['hhea'].lineGap=0;os=f['OS/2'];os.sTypoAscender=1150;os.sTypoDescender=-350;os.sTypoLineGap=0;os.usWinAscent=1150;os.usWinDescent=350;os.xAvgCharWidth=1000;f['head'].fontRevision=.001;f.recalcTimestamp=False;f.save(out/(stem+'.ttf'));f.flavor='woff2';f.save(out/(stem+'.woff2'));result[part]={'family':fam,'stem':stem,'Han_added':len(c)-3,'hashes':{e:sha(out/(stem+'.'+e)) for e in ('ttf','woff2')},'sizes':{e:(out/(stem+'.'+e)).stat().st_size for e in ('ttf','woff2')},'input_sha256':sha(src)};(out/(part+'-transforms.json')).write_text(json.dumps(changes,separators=(',',':'))+'\n');print(part,flush=True)
 (out/'manifest.json').write_text(json.dumps({'base_family':'Morimo Prose Zen','base_sha256':sha(base),'parts':result},indent=2)+'\n');return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--output',type=Path);a=p.parse_args();build(a.root,a.output or a.root/'inputs/prose-han')
