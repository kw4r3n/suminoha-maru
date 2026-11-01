#!/usr/bin/env python3
"""Build a disjoint-script composite; preserve layout closure and mark positioning."""
import argparse, copy, hashlib, json, pathlib, tempfile, logging, unicodedata
from fontTools import subset
from fontTools.unicodedata import script
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.transformPen import TransformPen
from fontTools.merge import Merger
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._g_l_y_f import Glyph
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools.ttLib.tables._n_a_m_e import table__n_a_m_e
ROOT=pathlib.Path(__file__).resolve().parents[1]
EPOCH=2082844800 + 1792713600  # 2026-10-23 00:00:00 UTC, OpenType epoch
logging.getLogger('fontTools.subset').setLevel(logging.ERROR)

def source(family):
    return next((ROOT/'sources'/family).glob('*.ttf'))

def regular(family):
    f=TTFont(source(family),recalcTimestamp=False)
    if 'fvar' in f:
        f=instantiateVariableFont(f,{'wght':400},inplace=True)
    return f

def japanese(cp):
    return any(lo<=cp<=hi for lo,hi in [(0x2E80,0x30FF),(0x31F0,0x33FF),
        (0x3400,0x9FFF),(0xF900,0xFAFF),(0xFE30,0xFE4F),(0xFF00,0xFFEF)])

def restrict(f, unicodes, code=False):
    opt=subset.Options()
    opt.layout_features=['*']
    opt.hinting=False
    opt.name_IDs=['*'];opt.name_legacy=True;opt.name_languages=['*']
    # Code keeps ccmp/locl/mark/mkmk; optional ligatures and proportional widths are excluded.
    if code: opt.layout_features=['ccmp','locl','mark','mkmk','rlig']
    s=subset.Subsetter(options=opt);s.populate(unicodes=unicodes);s.subset(f)
    for tag in ['DSIG','STAT','meta','vhea','vmtx','BASE','VORG']:
        if tag in f: del f[tag]
    return f

def code_grid(f, narrow, wide, jp=False):
    # Grid padding is applied to outlines and corresponding anchors, not a metadata toggle.
    deltas={};metrics={}
    original=f.getGlyphSet();expected={};inventory=dict(composites=0,nested=0,nonidentity=0)
    for g in f.getGlyphOrder():
        glyph=f['glyf'][g]
        if glyph.isComposite():
            inventory['composites']+=1
            for component in glyph.components:
                assert hasattr(component,'x') and hasattr(component,'y'), 'Point-attached component needs explicit handling'
                assert not component.flags & 0x800, 'Scaled component offsets need explicit handling'
                if f['glyf'][component.glyphName].isComposite(): inventory['nested']+=1
                if hasattr(component,'transform'):
                    t=component.transform
                    assert t[0][1]==0 and t[1][0]==0, 'Shear/rotation needs y translation'
                    inventory['nonidentity']+=1
    for g,(advance,lsb) in list(f['hmtx'].metrics.items()):
        target=0 if advance==0 else ((narrow if advance<=500 else wide) if jp else narrow)
        delta=(target-advance)//2
        deltas[g]=delta
        metrics[g]=(target,lsb+delta)
    def digest(recording,delta=0):
        value=[(op,tuple(None if p is None else (round(float(p[0]+delta),6),round(float(p[1]),6)) for p in pts)) for op,pts in recording]
        return hashlib.sha256(repr(value).encode()).hexdigest()
    for g,delta in deltas.items():
        pen=DecomposingRecordingPen(original);original[g].draw(pen);expected[g]=digest(pen.value,delta)
    f['hmtx'].metrics.update(metrics)
    for g,delta in deltas.items():
        glyph=f['glyf'][g]
        if glyph.isComposite():
            for c in glyph.components:
                xscale=c.transform[0][0] if hasattr(c,'transform') else 1
                c.x+=round(delta-xscale*deltas[c.glyphName])
        elif glyph.numberOfContours>0:
            glyph.coordinates.translate((delta,0))
    if 'GPOS' in f:
        for lookup in f['GPOS'].table.LookupList.Lookup:
            for st in lookup.SubTable:
                if lookup.LookupType==9: st=st.ExtSubTable
                for coverage,field,recordfield,anchorfield in [
                    ('MarkCoverage','MarkArray','MarkRecord','MarkAnchor'),
                    ('Mark1Coverage','Mark1Array','MarkRecord','MarkAnchor'),
                    ('BaseCoverage','BaseArray','BaseRecord','BaseAnchor'),
                    ('Mark2Coverage','Mark2Array','Mark2Record','Mark2Anchor')]:
                    if not hasattr(st,coverage): continue
                    records=getattr(getattr(st,field),recordfield)
                    for g,record in zip(getattr(st,coverage).glyphs,records):
                        anchors=getattr(record,anchorfield)
                        if not isinstance(anchors,list): anchors=[anchors]
                        for anchor in anchors:
                            if anchor: anchor.XCoordinate+=deltas[g]
    for g in f.getGlyphOrder(): f['glyf'][g].recalcBounds(f['glyf'])
    modified=f.getGlyphSet()
    for g in f.getGlyphOrder():
        pen=DecomposingRecordingPen(modified);modified[g].draw(pen)
        assert digest(pen.value)==expected[g], ('Changed outline beyond intended translation',g)
    f._morimo_outline_check=dict(glyphs_checked=len(expected),**inventory)
    return f

def widen_european(f, factor=1.09):
    """Widen letters/digits/marks in fixed cells; leave encoded punctuation/graphics alone."""
    cmap=f.getBestCmap()
    seeds={cp for cp in cmap if script(cp) in {'Latn','Grek','Cyrl'} or
           (script(cp)=='Zinh' and unicodedata.category(chr(cp)).startswith('M')) or 0x30<=cp<=0x39}
    chosen=copy.deepcopy(f);options=subset.Options();options.layout_features=['ccmp','locl']
    sub=subset.Subsetter(options=options);sub.populate(unicodes=seeds);sub.subset(chosen)
    direct={cmap[cp] for cp in seeds}
    protected={glyph for cp,glyph in cmap.items() if cp not in seeds}-direct
    selected=set(chosen.getGlyphOrder())-protected-{'.notdef'}
    # Snapshot before any mutation: unselected composites may share selected components.
    gs=f.getGlyphSet();recordings={}
    for name in f.getGlyphOrder():
        pen=DecomposingRecordingPen(gs);gs[name].draw(pen);recordings[name]=pen.value
    changed=0;min_bearing=10000;exceptions={};factors={}
    for name,recording in recordings.items():
        old=f['glyf'][name];advance,lsb=f['hmtx'][name]
        if name not in selected and not old.isComposite(): continue
        pen=TTGlyphPen(None)
        if name in selected:
            baseline_pen=TTGlyphPen(None)
            for operation,points in recording:getattr(baseline_pen,operation)(*points)
            baseline=baseline_pen.glyph();baseline.recalcBounds(f['glyf'])
            center=advance/2 if advance else -360
            scale=factor;shift=0
            if advance and baseline.numberOfContours>0 and hasattr(baseline,'xMax'):
                span=baseline.xMax-baseline.xMin
                scale=min(factor,(advance-18)/span) if span else factor
                assert scale>=1,('Baseline ink too wide for unchanged cell',name,span)
                left=scale*baseline.xMin+(1-scale)*center
                right=scale*baseline.xMax+(1-scale)*center
                shift=max(0,9-left)-max(0,right-(advance-9))
                if scale<factor or abs(shift)>0.01:
                    exceptions[name]=dict(factor=scale,extra_translation=shift,before_bounds=[baseline.xMin,baseline.xMax])
            factors[name]=dict(factor=scale,translation=(1-scale)*center+shift)
            target=TransformPen(pen,(scale,0,0,1,(1-scale)*center+shift,0));changed+=1
        else:target=pen
        for operation,points in recording:getattr(target,operation)(*points)
        glyph=pen.glyph();glyph.recalcBounds(f['glyf']);f['glyf'][name]=glyph
        f['hmtx'][name]=(advance,glyph.xMin if hasattr(glyph,'xMin') else lsb)
        if name in selected and advance and glyph.numberOfContours>0 and hasattr(glyph,'xMax'):
            bearing=min(glyph.xMin,advance-glyph.xMax);min_bearing=min(min_bearing,bearing)
            assert bearing>=8,('Widened advancing glyph crosses safety margin',name,bearing)
    # Maple currently relies on HarfBuzz fallback marks; do not invent partial anchor support.
    assert 'GPOS' not in f or not f['GPOS'].table.LookupList.Lookup
    f._morimo_widening=dict(factor=factor,selected_glyphs=sorted(selected),per_glyph_factors=factors,bearing_capped=exceptions,glyphs_widened=changed,
                           minimum_selected_advance_bearing=min_bearing,rounded_to_integer_units=True)
    return f

def five_greek_revert(f):
    """Use exact +9% geometry for only five requested glyphs; retain all other Wide15 data."""
    narrow=widen_european(copy.deepcopy(f),1.09)
    wide=widen_european(f,1.15)
    cmap=wide.getBestCmap();selected={cp:cmap[cp] for cp in [0x0388,0x0389,0x038C,0x038E,0x038F]}
    for name in selected.values():
        wide['glyf'][name]=copy.deepcopy(narrow['glyf'][name])
        wide['hmtx'][name]=narrow['hmtx'][name]
        wide._morimo_widening['per_glyph_factors'][name]=narrow._morimo_widening['per_glyph_factors'][name]
        wide._morimo_widening['bearing_capped'][name]=narrow._morimo_widening['bearing_capped'][name]
    wide._morimo_widening['five_greek']={f'U+{cp:04X}':name for cp,name in selected.items()}
    return wide

def rename(f,family,donors):
    copyright='\n'.join((ROOT/'sources'/d/'OFL.txt').read_text().split('\n\n')[0].strip() for d in donors)
    n=table__n_a_m_e('name');n.names=[]
    version='0.004' if family=='Morimo Code Greek5' else ('0.003' if family=='Morimo Code Wide15' else ('0.002' if family=='Morimo Code' else '0.001'))
    values={0:copyright,1:family,2:'Regular',3:f'{version};MRMO;{family.replace(" ","")}-Regular',
        4:family+' Regular',5:'Version '+version,6:family.replace(' ','')+'-Regular',
        7:'Provisional composite prototype; upstream names identify source attribution only.',
        8:'Morimo prototype contributors',9:'Upstream authors; composite build contributors',
        10:'P0 Regular composite. Japanese regional forms only. See accompanying reports and notices.',
        13:'\n\n'.join((ROOT/'sources'/d/'OFL.txt').read_text() for d in donors),
        14:'https://openfontlicense.org',16:family,17:'Regular'}
    for nameid,text in values.items():
        n.setName(text,nameid,3,1,0x409)
        n.setName(text,nameid,0,4,0)
    f['name']=n
    f['head'].created=f['head'].modified=EPOCH
    f['head'].macStyle=0
    f['OS/2'].usWeightClass=400;f['OS/2'].fsSelection=0x40|0x80;f['OS/2'].fsType=0
    f['OS/2'].achVendID='MRMO'
    f['OS/2'].sTypoAscender=f['hhea'].ascent=1300
    f['OS/2'].sTypoDescender=f['hhea'].descent=-400
    f['OS/2'].sTypoLineGap=f['hhea'].lineGap=0
    f['OS/2'].usWinAscent=1300;f['OS/2'].usWinDescent=400
    f['OS/2'].recalcUnicodeRanges(f);f['OS/2'].recalcCodePageRanges(f)
    return f

def build(output):
    output.mkdir(parents=True,exist_ok=True)
    from fetch import main as verify_sources
    verify_sources()
    summary={}
    for family,latin,narrow in [('Morimo','comfortaa',0),('Morimo Code','maplemono',720),('Morimo Grid','maplemono',600),('Morimo Code Wide15','maplemono',720),('Morimo Code Greek5','maplemono',720)]:
        code=bool(narrow)
        wide=1080 if narrow==720 else 1200
        a=regular(latin)
        # U+212B is canonically Å; encode it with the Western Å, never a mismatched JP Latin glyph.
        for table in a['cmap'].tables:
            if table.isUnicode() and 0x00C5 in table.cmap and 0x212B not in table.cmap:
                table.cmap[0x212B]=table.cmap[0x00C5]
        acmap=a.getBestCmap(); keep=set(acmap)
        # Keep one Western donor and disjoint Japanese ranges; no regional CJK union.
        a=restrict(a,keep,code)
        b=regular('kiwimaru');bcmap=b.getBestCmap()
        jp={cp for cp in bcmap if (japanese(cp) or (cp>=0x2000 and script(cp)=='Zyyy')) and cp not in keep}
        b=restrict(b,jp,code)
        if code:
            a=code_grid(a,narrow,wide)
            b=code_grid(b,narrow,wide,jp=True)
            if family=='Morimo Code': a=widen_european(a)
            elif family=='Morimo Code Wide15': a=widen_european(a,1.15)
            elif family=='Morimo Code Greek5': a=five_greek_revert(a)
        widening=getattr(a,'_morimo_widening',None)
        outline_checks=[getattr(font,'_morimo_outline_check',None) for font in [a,b]]
        with tempfile.TemporaryDirectory(prefix='morimo-') as tmp:
            ap=pathlib.Path(tmp)/'latin.ttf';bp=pathlib.Path(tmp)/'jp.ttf'
            a.save(ap);b.save(bp)
            f=Merger().merge([str(ap),str(bp)])
        f.recalcTimestamp=False
        # Empty GPOS suppresses HarfBuzz fallback marks, which the Maple source uses.
        if 'GPOS' in f and not f['GPOS'].table.LookupList.Lookup:
            del f['GPOS']
        # Firefox warns on an empty composite inherited through Kiwi's feature closure.
        empty_composites=[]
        for g in f.getGlyphOrder():
            glyph=f['glyf'][g]
            if glyph.isComposite() and all(f['glyf'][c.glyphName].numberOfContours==0 for c in glyph.components):
                f['glyf'][g]=Glyph();empty_composites.append(g)
        f=rename(f,family,[latin,'kiwimaru'])
        # Dual-cell fonts are not globally single-advance. Tell fontconfig truthfully.
        f['post'].isFixedPitch=0
        if code:
            f['OS/2'].panose.bProportion=9 if narrow==600 else 0
            if 'kern' in f: del f['kern']
        stem=family.replace(' ','')+'-Regular'
        ttf=output/(stem+'.ttf');f.save(ttf)
        f.flavor='woff2';f.save(output/(stem+'.woff2'))
        summary[family]=dict(latin_donor=latin,japanese_donor='kiwimaru',narrow_advance=narrow,wide_advance=wide if code else None,
             latin_codepoints=len(keep),japanese_codepoints=len(jp),
             encoded_codepoints=len(f.getBestCmap()),glyphs=f['maxp'].numGlyphs,
             tables=sorted(f.keys()),upem=f['head'].unitsPerEm,outline_translation_checks=outline_checks,empty_composites_normalized=len(empty_composites),european_widening=widening)
        print(f'{family}: {summary[family]["encoded_codepoints"]} codepoints, {ttf.stat().st_size} TTF bytes')
    (output/'build-summary.json').write_text(json.dumps(summary,indent=2)+'\n')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=pathlib.Path,default=ROOT/'inputs/dist')
    build(parser.parse_args().output)
