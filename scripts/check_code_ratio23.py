"""Assert invariants and actual HarfBuzz profiles, repeat build, render both faces."""
import argparse, collections, hashlib, json, sys, tempfile, unicodedata
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import DecomposingRecordingPen
from PIL import Image, ImageDraw, ImageFont
from build_code_ratio23 import build, STEM, sha

def check(root, out, previews):
    sys.path.insert(0,str(root/'scripts'))
    from hb import Shaper
    from samples import SAMPLES, MARK_SAMPLES, CODE
    from render_code_features import CASES
    from render_code_defaults import SELECTED
    bp=root/'inputs/code-jp-size/MorimoCodeLatin1216JP95-Regular.ttf';np=out/(STEM+'.ttf')
    a,b=TTFont(bp),TTFont(np);report=json.loads((out/'build.json').read_text());changes=report['transforms']
    assert a.getBestCmap()==b.getBestCmap() and a.getGlyphOrder()==b.getGlyphOrder()
    assert a['head'].unitsPerEm==b['head'].unitsPerEm==1000
    for tag in ('GSUB','GDEF','cmap'): assert a[tag].compile(a)==b[tag].compile(b)
    for tag in ('GPOS','kern'): assert tag not in a and tag not in b
    glyphsets={id(a):a.getGlyphSet(),id(b):b.getGlyphSet()}
    def points(f,n):
        gs=glyphsets[id(f)];p=DecomposingRecordingPen(gs);gs[n].draw(p);return p.value
    unchanged=0
    for n in a.getGlyphOrder():
        if n not in changes:
            assert a['glyf'][n].compile(a['glyf'])==b['glyf'][n].compile(b['glyf']) and a['hmtx'][n]==b['hmtx'][n],n
            unchanged+=1
        else:
            sx,dx=changes[n];pa,pb=points(a,n),points(b,n)
            assert len(pa)==len(pb),n
            for (op,xy),(op2,xy2) in zip(pa,pb):
                assert op==op2 and len(xy)==len(xy2)
                for p1,p2 in zip(xy,xy2):
                    if p1 is None: assert p2 is None; continue
                    x,y=p1;x2,y2=p2
                    assert abs(x*sx+dx-x2)<=.51 and y==y2,n
            assert b['hmtx'][n][0]==720
    assert a['hhea'].ascent==b['hhea'].ascent==1200 and a['hhea'].descent==b['hhea'].descent==-350
    sa,sb=Shaper(bp),Shaper(np)
    texts=[v[1] for v in SAMPLES.values()]+MARK_SAMPLES+[x[2] for x in CASES]+[CODE,'AB日本CD','ｱｲｳ 日本ＡＢ１２','-> --> === != !== <!-- --> </> <|> >>= =<< ... [debug] [warning]','a\u0323\u0302 x\u0308\u0323']
    tags=sorted({r.FeatureTag for r in a['GSUB'].table.FeatureList.FeatureRecord})
    profiles=[{},SELECTED,{'calt':0},SELECTED|{'calt':0}]+[SELECTED|{tag:v} for tag in tags for v in (0,1)]
    shaping=0;ligature_changes=0
    for features in profiles:
        for t in texts:
            aa,bb=sa.shape(t,features=features),sb.shape(t,features=features)
            assert [(r['glyph'],r['cluster'],r['dy'],r['y_advance']) for r in aa]==[(r['glyph'],r['cluster'],r['dy'],r['y_advance']) for r in bb],(features,t)
            for x,y in zip(aa,bb): assert y['advance']==x['advance']+(180 if x['glyph'] in changes else 0),(features,t,x,y)
            shaping+=1
    for t in ('->','===','!=','<!--','[debug]','[warning]'):
        on=sb.shape(t,features=SELECTED);off=sb.shape(t,features={k:0 for k in tags if k not in ('ccmp','locl')})
        assert sum(r['advance'] for r in on)==len(t)*720
        if [r['glyph'] for r in on]!=[r['glyph'] for r in off]:ligature_changes+=1
    assert ligature_changes>=5
    # HarfBuzz fallback mark positions must follow the translated base ink.
    mark_positions=0
    for t in ('x\u0308\u0323','q\u0301','x\u0300','w\u0323'):
        aa,bb=sa.shape(t),sb.shape(t);oa=ob=0
        assert len(aa)==len(bb)
        for x,y in zip(aa,bb):
            n=x['glyph'];shift=changes.get(n,[1,0])[1]
            assert ob+y['dx']+shift-(oa+x['dx'])==90,(t,x,y)
            assert x['dy']==y['dy']
            oa+=x['advance'];ob+=y['advance'];mark_positions+=1
    # Compare inherited NFC/NFD behavior; do not claim to repair old differences.
    canonical=0
    for t in MARK_SAMPLES+['ど','が','ぽ','ヴ','Árvíztűrő','Nguyễn']:
        for features in ({},SELECTED):
            forms=[unicodedata.normalize(k,t) for k in ('NFC','NFD')]
            old=[[(r['glyph'],r['advance'],r['dx'],r['dy']) for r in sa.shape(x,features=features)] for x in forms]
            new=[[(r['glyph'],r['advance'],r['dx'],r['dy']) for r in sb.shape(x,features=features)] for x in forms]
            if old[0]==old[1]: assert new[0]==new[1],t
            canonical+=1
    bounds=[min(g.yMin for g in b['glyf'].glyphs.values() if g.numberOfContours),max(g.yMax for g in b['glyf'].glyphs.values() if g.numberOfContours)]
    assert bounds[0]>=-350 and bounds[1]<=1200
    w=TTFont(out/(STEM+'.woff2'))
    for tag in b.keys():
        if tag not in ('GlyphOrder','head','loca'):assert b[tag].compile(b)==w[tag].compile(w),tag
    with tempfile.TemporaryDirectory(prefix='morimo-ratio23-') as tmp:
        build(root,Path(tmp))
        for ext in ('ttf','woff2'):assert sha(out/(STEM+'.'+ext))==sha(Path(tmp)/(STEM+'.'+ext)),ext
    previews.mkdir(parents=True,exist_ok=True)
    # Same point size, line height, colors, feature profile; no browser fallback.
    selected=[k+'='+str(v) for k,v in SELECTED.items()]
    samples={'mixed':['AB日本CD  ABCDEF / 日本語と Latin 2:3','丸みのある文字で、長い文章を読みやすく。','設定を読み込み、必要な項目だけ返す。','Árvíztűrő ŵŷ Nguyễn q̈ x̂́ a̋','ΈΉΌΎΏ Καλημέρα ЁЙЇ / ど ど ぽ ぽ','0O1lI 0123456789  ｱｲｳ 日本ＡＢ１２'], 'code':CODE.strip().splitlines()+['','// [debug] [warning] != !== === => -> >>=','// WWWMM gypjq ẮẰẴ ộựỹ Ĵ x̂́ q̈','const ready = value >= 0 && value !== null;','if (ready) return x => x === 0;']}
    for label,lines in samples.items():
        fonts=[ImageFont.truetype(str(path),24,layout_engine=ImageFont.Layout.RAQM) for path in (bp,np)]
        column=max(850,int(max(font.getlength(t,features=selected,language='ja') for font in fonts for t in lines))+60)
        im=Image.new('RGB',(column*2,180+len(lines)*42),'#14201a');d=ImageDraw.Draw(im)
        ui=ImageFont.truetype('/usr/share/fonts/TTF/DejaVuSans.ttf',21)
        d.text((24,20),'JP95 / same 24px size, 38px leading / explicit selected features',font=ui,fill='#dfede3')
        for col,(path,title) in enumerate([(bp,'Existing JP95 540 / 1080'),(np,'Ratio23 720 / 1080')]):
            x=24+col*column;d.text((x,65),title,font=ui,fill='#9dcab0')
            font=ImageFont.truetype(str(path),24,layout_engine=ImageFont.Layout.RAQM)
            for i,t in enumerate(lines):d.text((x,132+i*38),t,font=font,fill='#dfede3',anchor='ls',features=selected,language='ja')
        im.save(previews/(label+'.png'))
    result={'baseline_sha256':sha(bp),'hashes':{ext:sha(out/(STEM+'.'+ext)) for ext in ('ttf','woff2')},'coverage':len(b.getBestCmap()),'glyphs':len(b.getGlyphOrder()),'unchanged_glyphs':unchanged,'changed':dict(collections.Counter(report['kinds'].values())),'width_counts':dict(collections.Counter(v[0] for v in b['hmtx'].metrics.values())),'GSUB_features':tags,'shaping_checks':shaping,'profiles':len(profiles),'positioned_mark_glyph_checks':mark_positions,'canonical_checks':canonical,'ligature_substitution_probes':ligature_changes,'bounds':bounds,'TTF_WOFF2_tables_equal':True,'byte_identical_repeat':True,'render':'Pillow RAQM at24px/38px, selected features explicit, same source files, no fallback','limits':'Finite shaping samples; arbitrary marks inherited. No custom-terminal/native raster testing. Contextual glyphs scale horizontally, ordinary ink only translates.'}
    (out/'validation.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--output',type=Path);p.add_argument('--previews',type=Path);a=p.parse_args();check(a.root,a.output or a.root/'inputs/code-ratio23',a.previews or a.root/'specimens/code-ratio23')
