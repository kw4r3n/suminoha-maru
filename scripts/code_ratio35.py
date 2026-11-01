import argparse,json,hashlib,sys,tempfile,shutil
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.transformPen import TransformPen
from PIL import Image,ImageFont,ImageDraw
STEM='MorimoCodeJP95TerminalAddonsRatio35-Regular';FAMILY='Morimo Code JP95 Terminal Addons Ratio35'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def build(root,out):
 base=root/'inputs/terminal-addons/MorimoCodeJP95TerminalAddonsRatio23-Regular.ttf';assert sha(base)=='699f292496ca86094c2c5cd51acbdcd69a97a4ddc95c5c809fd4c94844043096'
 a=TTFont(base,recalcTimestamp=False);f=TTFont(base,recalcTimestamp=False);gs=a.getGlyphSet();separators={n for cp,n in a.getBestCmap().items() if 0xe0b0<=cp<=0xe0d7};maps=json.loads((root/'inputs/terminal-addons/mapping.json').read_text())['Ratio23']['mapping'];adds={a.getBestCmap()[int(cp[2:],16)]:m for cp,m in maps.items()};changes={}
 for n in a.getGlyphOrder():
  aw,lsb=a['hmtx'][n]
  if aw!=720:continue
  g=a['glyf'][n];sx=1;dx=-36;kind='translate'
  if n in separators and g.numberOfContours:sx=648/(g.xMax-g.xMin);dx=-g.xMin*sx;kind='separator_fit'
  elif '.liga' in n or '.seq' in n or adds.get(n,{}).get('separator'):sx=.9;dx=0;kind='connected_cell_scale'
  elif n in adds and g.numberOfContours and g.xMax-g.xMin>608:sx=608/(g.xMax-g.xMin);dx=324-(g.xMin+g.xMax)*sx/2;kind='icon_fit'
  rec=DecomposingRecordingPen(gs);gs[n].draw(rec);p=TTGlyphPen(None);tr=TransformPen(p,(sx,0,0,1,dx,0))
  for op,pts in rec.value:getattr(tr,op)(*pts)
  z=p.glyph();z.recalcBounds(None);f['glyf'][n]=z;f['hmtx'][n]=(648,getattr(z,'xMin',round(lsb+dx)));changes[n]=[sx,dx,kind]
 for r in list(f['name'].names):
  vals={1:FAMILY,4:FAMILY+' Regular',6:STEM,16:FAMILY,17:'Regular',3:'0.001;MRMO;'+STEM,5:'Version 0.001',10:'Native3:5 prototype ordinary648/Japanese1080; ink translated, connected geometry fitted.'}
  if r.nameID in vals:f['name'].setName(vals[r.nameID],r.nameID,r.platformID,r.platEncID,r.langID)
 f['OS/2'].xAvgCharWidth=648;f.recalcTimestamp=False;out.mkdir(parents=True,exist_ok=True);f.save(out/(STEM+'.ttf'));f.flavor='woff2';f.save(out/(STEM+'.woff2'));(out/'transforms.json').write_text(json.dumps(changes,sort_keys=True,indent=2)+'\n');return changes

def verify(root,out,previews):
 sys.path.insert(0,str(root/'scripts'));from hb import Shaper
 from samples import SAMPLES,MARK_SAMPLES
 from render_code_defaults import SELECTED
 base=root/'inputs/terminal-addons/MorimoCodeJP95TerminalAddonsRatio23-Regular.ttf';p=out/(STEM+'.ttf');a=TTFont(base);b=TTFont(p);changes=json.loads((out/'transforms.json').read_text());assert a.getBestCmap()==b.getBestCmap() and len(b.getBestCmap())==9559 and a.getGlyphOrder()==b.getGlyphOrder()
 for tag in ('GSUB','GDEF'):assert a[tag].compile(a)==b[tag].compile(b)
 for n in a.getGlyphOrder():
  assert b['hmtx'][n][0]==(648 if a['hmtx'][n][0]==720 else a['hmtx'][n][0])
  if n not in changes:assert a['glyf'][n].compile(a['glyf'])==b['glyf'][n].compile(b['glyf']) and a['hmtx'][n]==b['hmtx'][n]
 assert (b['hhea'].ascent,b['hhea'].descent,b['hhea'].lineGap)==(1200,-350,0)
 sa,sb=Shaper(base),Shaper(p);tags=sorted({x.FeatureTag for x in a['GSUB'].table.FeatureList.FeatureRecord});texts=[x[1] for x in SAMPLES.values()]+MARK_SAMPLES+['=== -> <!-- [debug] [warning] != >>=','🤖✅❌🔧🔍💡📝📦🚀🎉🎯'];count=0
 for features in [{},SELECTED]+[SELECTED|{t:v} for t in tags for v in (0,1)]:
  for text in texts:
   aa,bb=sa.shape(text,features=features),sb.shape(text,features=features);assert [(x['gid'],x['cluster'],x['dy']) for x in aa]==[(x['gid'],x['cluster'],x['dy']) for x in bb]
   for x,y in zip(aa,bb):assert y['advance']==(648 if x['advance']==720 else x['advance'])
   count+=1
 for text in ('ẍ̣','q́','ẉ'):
  aa,bb=sa.shape(text),sb.shape(text);oa=ob=0
  for x,y in zip(aa,bb):
   assert ob+y['dx']+changes.get(y['glyph'],[1,0])[1]-(oa+x['dx'])==-36
   oa+=x['advance'];ob+=y['advance']
 bounds=[min(g.yMin for g in [b['glyf'][n] for n in b.getGlyphOrder()] if g.numberOfContours),max(g.yMax for g in [b['glyf'][n] for n in b.getGlyphOrder()] if g.numberOfContours)];assert -350<=bounds[0] and bounds[1]<=1200
 w=TTFont(out/(STEM+'.woff2'))
 for t in b.keys():
  if t not in ('GlyphOrder','head','loca'):assert b[t].compile(b)==w[t].compile(w)
 with tempfile.TemporaryDirectory() as tmp:
  build(root,Path(tmp))
  for ext in ('ttf','woff2'):assert sha(out/(STEM+'.'+ext))==sha(Path(tmp)/(STEM+'.'+ext))
 previews.mkdir(parents=True,exist_ok=True);ui=ImageFont.truetype('/usr/share/fonts/TTF/DejaVuSans.ttf',21)
 sections=[('Height reference / same baseline',['日本語 ABC HINlhd / あいうえお abcdef gypjq']),('Japanese paragraph',['設定を読み込み、必要な項目を確認します。','日本語と欧文の間隔を、同じ大きさで比べます。','画面に並ぶ文字を、落ち着いて読めるでしょうか。']),('English paragraph',['Read the current settings and check each value.','The same ink size now uses a narrower advance.','Compare ordinary reading rhythm and mixed text.']),('Mixed code / prompt',['def load_profile(name: str) -> dict:','    # 日本語コメントと Nguyen / Árvíztűrő','    if name != "": return {"ready": True}','    return "こんにちは、世界。"','❯ '+chr(0xe0a0)+' main '+chr(0xe718)+' 🎯 🤖 ✅ ❌']),('Stress: marks, joined operators and separators',['x̂́ q̈ a̋ ẍ̣ gypjq ẮẰẴ ộựỹ Ĵ','[debug] [warning] === != !== -> >>= <!--',''.join(chr(x) for x in (0xe0b0,0xe0b4,0xe0b8,0xe0c0,0xe0c6,0xe0cc))])]
 im=Image.new('RGB',(1800,1240),'#14201a');d=ImageDraw.Draw(im);d.text((24,18),'2:3 vs 3:5 / identical 24px, 38px leading / actual fonts, no fallback',font=ui,fill='#dfede3');d.text((24,56),'2:3  720 / 1080',font=ui,fill='#9dcab0');d.text((924,56),'3:5  648 / 1080',font=ui,fill='#9dcab0');y=115
 for title,lines in sections:
  for col,path in enumerate((base,p)):
   x=24+col*900;d.text((x,y),title,font=ui,fill='#9dcab0');font=ImageFont.truetype(str(path),24,layout_engine=ImageFont.Layout.RAQM)
   for i,line in enumerate(lines):
    bbx=d.textbbox((x,y+62+i*38),line,font=font,anchor='ls',features=[k+'='+str(v) for k,v in SELECTED.items()]);assert bbx[0]>=col*900 and bbx[2]<(col+1)*900 and bbx[3]<1240,bbx
    d.text((x,y+62+i*38),line,font=font,anchor='ls',fill='#dfede3',features=[k+'='+str(v) for k,v in SELECTED.items()])
  y+=78+len(lines)*38
 im.save(previews/'comparison.png');result={'coverage':9559,'ordinary_advance':648,'Japanese_advance':1080,'line_metrics':[1200,-350,0],'bounds':bounds,'shaping_checks':count,'repeat_identical':True,'ordinary_ink':'translation -36; no rescaling','contextual_ink':'x0.9 for joined operators; fullcell separator fit648; oversized addon icons fit608','changed':len(changes),'hashes':{e:sha(out/(STEM+'.'+e)) for e in ('ttf','woff2')},'sizes':{e:(out/(STEM+'.'+e)).stat().st_size for e in ('ttf','woff2')}};(out/'validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--output',type=Path);p.add_argument('--previews',type=Path);a=p.parse_args();o=a.output or a.root/'inputs/terminal-ratio35';build(a.root,o);verify(a.root,o,a.previews or a.root/'specimens/terminal-ratio35')
