"""Separate JP95 720/1080 derivative; no installation or settings writes."""
import argparse, hashlib, json, shutil
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.transformPen import TransformPen

FAMILY = 'Morimo Code Latin1216 JP95 Ratio23'
STEM = 'MorimoCodeLatin1216JP95Ratio23-Regular'
BASE_SHA = 'ebf522d3050776354973e5c65c808ecd13257e5051238c60264384222e1ab835'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def build(root, out):
    base = root/'inputs/code-jp-size/MorimoCodeLatin1216JP95-Regular.ttf'
    assert sha(base) == BASE_SHA
    a = TTFont(base, recalcTimestamp=False)
    f = TTFont(base, recalcTimestamp=False)
    assert 'GPOS' not in a and 'kern' not in a
    jp = {r['glyph'] for r in json.loads((root/'inputs/code-zen/build.json').read_text())['changed_encoded_glyphs']}
    gs = a.getGlyphSet(); changes = {}; kinds = {}
    for n in a.getGlyphOrder():
        aw, lsb = a['hmtx'][n]
        assert aw in (0, 540, 1080), (n, aw)
        if aw != 540 or n in jp: continue
        contextual = '.liga' in n or '.seq' in n
        sx, dx = (4/3, 0) if contextual else (1, 90)
        rec = DecomposingRecordingPen(gs); gs[n].draw(rec)
        pen = TTGlyphPen(None); tr = TransformPen(pen, (sx,0,0,1,dx,0))
        for op, pts in rec.value: getattr(tr,op)(*pts)
        g = pen.glyph(); g.recalcBounds(None); f['glyf'][n] = g
        f['hmtx'][n] = (720, getattr(g,'xMin',0) if g.numberOfContours else round(lsb*sx+dx))
        changes[n] = [sx, dx]; kinds[n] = 'contextual_cell_scale' if contextual else 'center_translation'
    for r in list(f['name'].names):
        values = {1:FAMILY,2:'Regular',3:'0.001;MRMO;'+STEM,4:FAMILY+' Regular',5:'Version 0.001',6:STEM,16:FAMILY,17:'Regular',10:'JP95 separate native 2:3 advances; ordinary ink preserved; contextual operators fit 720 cells.'}
        if r.nameID in values: f['name'].setName(values[r.nameID],r.nameID,r.platformID,r.platEncID,r.langID)
    f['post'].isFixedPitch = 0
    f['OS/2'].xAvgCharWidth = 720
    f['head'].fontRevision = .001
    f['head'].modified = a['head'].modified
    out.mkdir(parents=True,exist_ok=True)
    f.save(out/(STEM+'.ttf')); f.flavor='woff2'; f.save(out/(STEM+'.woff2'))
    for n in ('OFL.txt','NOTICES.txt'): shutil.copyfile(root/'inputs/code-jp-size'/n,out/n)
    report = {'family':FAMILY,'baseline_sha256':BASE_SHA,'ordinary_advances':[720,1080], 'Japanese_halfwidth':540,'zero_width':0,'transforms':changes,'kinds':kinds,'policy':'Ordinary Western outlines translated +90; Japanese-owned 540 and all1080/zero glyphs exact. Contextual .liga/.seq x4/3 for connected strokes and full run coverage. GSUB/GDEF exact; no GPOS/kern exists in baseline.'}
    (out/'build.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
    return report
if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--output',type=Path);args=p.parse_args()
    build(args.root,args.output or args.root/'inputs/code-ratio23')
