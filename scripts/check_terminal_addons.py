import argparse,json,sys,tempfile,hashlib
from pathlib import Path
from fontTools.ttLib import TTFont
from PIL import Image,ImageDraw,ImageFont
from build_terminal_addons import build,EMOJI,SYMBOLS,sha

def check(root,sources,out,previews):
 sys.path.insert(0,str(root/'scripts'));from hb import Shaper
 from samples import SAMPLES,MARK_SAMPLES,CODE
 from render_code_defaults import SELECTED
 data=json.loads((out/'mapping.json').read_text());summary={}
 for tag,r in data.items():
  a=TTFont(root/r['base']);path=out/(r['stem']+'.ttf');b=TTFont(path);old=a.getGlyphOrder();order=b.getGlyphOrder();assert order[:len(old)]==old
  # Serialized post3 names can change for appended glyphs only; gids/layout of old glyphs stay fixed.
  for n in old:assert a['glyf'][n].compile(a['glyf'])==b['glyf'][n].compile(b['glyf']) and a['hmtx'][n]==b['hmtx'][n],n
  for t in ('GSUB','GDEF'):assert a[t].compile(a)==b[t].compile(b),t
  assert 'GPOS' not in b
  for cp,n in a.getBestCmap().items():assert b.getGlyphID(b.getBestCmap()[cp])==a.getGlyphID(n)
  added=set(b.getBestCmap())-set(a.getBestCmap());expected={int(x[2:],16) for x in r['mapping']};assert added==expected and len(added)==371 and len(b.getBestCmap())==9559
  bounds=[]
  for cp in added:
   n=b.getBestCmap()[cp];g=b['glyf'][n];aw=b['hmtx'][n][0];m=r['mapping'][f'U+{cp:04X}'];assert aw==m['advance'];assert 0<=g.xMin<g.xMax<=aw;assert -350<=g.yMin<g.yMax<=1200
   if m['separator']:
    sep=a['glyf'][a.getBestCmap()[0xe0b0]];assert (g.xMin,g.xMax,g.yMin,g.yMax)==(0,aw,sep.yMin,sep.yMax)
   bounds.append((g.yMin,g.yMax))
  sa,sb=Shaper(root/r['base']),Shaper(path);tags=sorted({x.FeatureTag for x in a['GSUB'].table.FeatureList.FeatureRecord});profiles=[{},SELECTED]+[SELECTED|{t:v} for t in tags for v in (0,1)]
  count=0
  for feat in profiles:
   for t in [x[1] for x in SAMPLES.values()]+MARK_SAMPLES+[CODE,'-> !== === <!-- [debug] [warning] ẍ̣']:
    assert sa.shape(t,features=feat)==sb.shape(t,features=feat),(tag,t,feat);count+=1
  for ch in EMOJI:
   rows=sb.shape(ch);assert len(rows)==1 and rows[0]['gid'] and rows[0]['advance']==1080
   for vs in ('\ufe0e','\ufe0f'):
    rr=[x for x in sb.shape(ch+vs) if x['advance'] or x['dx'] or x['dy']];assert [(x['gid'],x['advance']) for x in rr]==[(x['gid'],x['advance']) for x in rows]
  for colortag in ('COLR','CPAL','CBDT','CBLC','sbix','SVG '):assert colortag not in b
  w=TTFont(out/(r['stem']+'.woff2'))
  for t in b.keys():
   if t not in ('GlyphOrder','head','loca'):assert b[t].compile(b)==w[t].compile(w),t
  summary[tag]={'coverage':9559,'added':371,'old_glyphs_exact':len(old),'layout_exact':True,'old_run_shape_checks':count,'emoji_singletons_and_VS15_VS16':len(EMOJI),'added_bounds':[min(x[0] for x in bounds),max(x[1] for x in bounds)],'sizes':r['sizes'],'hashes':r['hashes'],'widths':[540 if tag=='Grid' else 720,1080],'seams':'New Powerline contour bounds match existing separator y edges and fullcell x edges; arbitrary backgrounds/rasterizers not certified'}
  previews.mkdir(parents=True,exist_ok=True);im=Image.new('RGB',(1780,620),'#14201a');d=ImageDraw.Draw(im);ui=ImageFont.truetype('/usr/share/fonts/TTF/DejaVuSans.ttf',20)
  d.text((20,15),'JP95 '+tag+' / 26px / selected features / red boxes = missing, no fallback',font=ui,fill='#dfede3')
  lines=['日本語 ABC 0O1lI Árvíztűrő x̂́ q̈','if (value !== null) return x => x === 0;','Prompt: '+chr(0xe718)+' 🎯 ⋈ ⌉ ⌊ ℂ ⋯ ⎥ ⎪',EMOJI,SYMBOLS,''.join(chr(x) for x in (0xf489,0xf413,0xf408,0xf418,0xf487)),''.join(chr(x) for x in (0xe0b0,0xe0b1,0xe0b4,0xe0b8,0xe0c0,0xe0c6,0xe0cc))]
  for col,(p,f,title) in enumerate([(root/r['base'],a,'Existing'),(path,b,'Additive prototype')]):
   x=22+col*890;d.text((x,62),title,font=ui,fill='#9dcab0');font=ImageFont.truetype(str(p),26,layout_engine=ImageFont.Layout.RAQM);c=f.getBestCmap()
   for i,text in enumerate(lines):
    xx=x;y=120+i*58
    if all(ord(ch) in c for ch in text):d.text((xx,y),text,font=font,fill='#dfede3',anchor='ls',features=[k+'='+str(v) for k,v in SELECTED.items()]);continue
    for ch in text:
     if ord(ch) in c:
      d.text((xx,y),ch,font=font,fill='#dfede3',anchor='ls');xx+=font.getlength(ch)
     else:d.rectangle((xx,y-21,xx+22,y),outline='#ff7979',width=1);xx+=28
  # Same occupied terminal-cell background on new Powerline sample.
  font=ImageFont.truetype(str(path),44);x=912;y=560
  for i,cp in enumerate((0xe0b0,0xe0b4,0xe0b8,0xe0c0,0xe0c6,0xe0cc)):
   ch=chr(cp);aw=font.getlength(ch);d.rectangle((x,y-40,x+aw,y+10),fill=('#284839' if i%2 else '#33634b'));d.text((x,y),ch,font=font,anchor='ls',fill='#dfede3');x+=aw
  im.save(previews/(tag+'.png'))
 with tempfile.TemporaryDirectory(prefix='morimo-addons-repeat-') as tmp:
  build(root,sources,Path(tmp))
  for r in data.values():
   for ext in ('ttf','woff2'):assert sha(out/(r['stem']+'.'+ext))==sha(Path(tmp)/(r['stem']+'.'+ext))
 summary['repeat_byte_identical']=True;(out/'validation.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--sources',type=Path);p.add_argument('--output',type=Path);p.add_argument('--previews',type=Path);a=p.parse_args();check(a.root,a.sources or a.root/'sources/terminal-addons',a.output or a.root/'inputs/terminal-addons',a.previews or a.root/'specimens/terminal-addons')
