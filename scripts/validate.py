#!/usr/bin/env python3
import collections, hashlib, json, pathlib, tempfile, unicodedata as ud
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.unicodedata import script
from PIL import ImageFont, features
from build import ROOT,regular,source,japanese
from hb import Shaper,version
from samples import SAMPLES,ALPHABETS,MARK_SAMPLES,CODE
from refinement import check as check_refinement,check_five_only

def ranges(cps):
    result=[]
    for cp in sorted(cps):
        if result and cp==result[-1][1]+1: result[-1][1]=cp
        else: result.append([cp,cp])
    return [f'U+{a:04X}'+(f'–U+{b:04X}' if a!=b else '') for a,b in result]

def signature(shaper,rows):
    glyphset=shaper.tt.getGlyphSet();result=[]
    for r in rows:
        pen=DecomposingRecordingPen(glyphset);glyphset[r['glyph']].draw(pen)
        result.append((pen.value,r['advance'],r['y_advance'],r['dx'],r['dy']))
    return result

def ink_signature(shaper,text,language):
    glyphset=shaper.tt.getGlyphSet();result=[];x=0
    for row in shaper.shape(text,language):
        pen=DecomposingRecordingPen(glyphset);glyphset[row['glyph']].draw(pen)
        for op,points in pen.value:
            result.append((op,tuple(None if p is None else (p[0]+x+row['dx'],p[1]+row['dy']) for p in points)))
        x+=row['advance']
    origin=next(p for _,pts in result for p in pts if p is not None)
    return [(op,tuple(None if p is None else (p[0]-origin[0],p[1]-origin[1]) for p in pts)) for op,pts in result]

def shift_jis_repertoire():
    cps=set()
    for lead in list(range(0x81,0xA0))+list(range(0xE0,0xF0)):
        for trail in range(0x40,0xFD):
            if trail==0x7F:continue
            try:cps.update(map(ord,bytes([lead,trail]).decode('shift_jis')))
            except UnicodeDecodeError:pass
    return cps

def main():
    report=dict(harfbuzz=version().decode(),pillow_raqm=features.version('raqm'),
                freetype=features.version('freetype2'),fonts={},sources={})
    for folder in sorted((ROOT/'sources').iterdir()):
        paths=list(folder.glob('*.ttf'))
        if not paths: continue
        f=TTFont(paths[0]);c=f.getBestCmap()
        report['sources'][folder.name]=dict(codepoints=len(c),scripts=dict(collections.Counter(script(cp) for cp in c)),
            name_copyright=f['name'].getDebugName(0),license=f['name'].getDebugName(13),
            tables=sorted(f.keys()),upem=f['head'].unitsPerEm,
            target_missing={k:ranges(set(map(ord,v+v.upper()))-set(c)) for k,v in ALPHABETS.items()})
    with tempfile.TemporaryDirectory(prefix='morimo-validate-') as tmp:
        donor=regular('comfortaa');donorpath=pathlib.Path(tmp)/'comfortaa.ttf';donor.save(donorpath)
        sourcehb=Shaper(donorpath);jp_hb=Shaper(source('kiwimaru'));maple_hb=Shaper(source('maplemono'))
        for family in ['Morimo','MorimoCode','MorimoGrid','MorimoCodeWide15','MorimoCodeGreek5']:
            path=ROOT/'inputs/dist'/(family+'-Regular.ttf');f=TTFont(path);c=f.getBestCmap();hb=Shaper(path)
            ink_factor=1.15 if family in ['MorimoCodeWide15','MorimoCodeGreek5'] else (1.09 if family=='MorimoCode' else 1.0)
            info=dict(codepoints=len(c),glyphs=len(f.getGlyphOrder()),coverage_ranges=ranges(c),
                samples={},alphabets={},metrics={},mark_tests=[],donor_equivalence=[],
                cmap_missing_p1={k:ranges(set(map(ord,v))-set(c)) for k,v in {
                    'Arabic':'العربية فارسی','Hebrew':'עברית','Thai':'ภาษาไทย','Korean':'한국어',
                    'Indic':'हिन्दी','Armenian':'Հայերեն','Georgian':'ქართული'}.items()})
            assert not shift_jis_repertoire()-set(c),(family,'Japanese repertoire missing',ranges(shift_jis_repertoire()-set(c)))
            for lang,(label,text) in SAMPLES.items():
                for form in ['NFC','NFD']:
                    textform=ud.normalize(form,text);rows=hb.shape(textform,lang)
                    missing=[r for r in rows if r['gid']==0]
                    info['samples'][lang+'_'+form]=dict(text=textform,missing=missing,
                        advance=sum(r['advance'] for r in rows),glyphs=rows)
                    assert not missing,(family,lang,form,missing)
                    if family=='Morimo':
                        original=(jp_hb if lang=='ja' else sourcehb).shape(textform,lang)
                        # Mixed Japanese punctuation may use the Latin donor; test pure runs separately.
                        if lang!='ja':
                            same=signature(hb,rows)==signature(sourcehb,original)
                            info['donor_equivalence'].append(dict(test=lang+'_'+form,equal=same))
                            assert same,(family,lang,form,'changed source shaping')
            info['nfc_nfd_equivalent']={}
            for lang in SAMPLES:
                keys=['gid','advance','y_advance','dx','dy']
                nfc=[tuple(row[k] for k in keys) for row in info['samples'][lang+'_NFC']['glyphs']]
                nfd=[tuple(row[k] for k in keys) for row in info['samples'][lang+'_NFD']['glyphs']]
                info['nfc_nfd_equivalent'][lang]=nfc==nfd
                assert nfc==nfd,(family,lang,'NFC/NFD shaped output differs')
            for lang,text in ALPHABETS.items():
                required=set(map(ord,text+text.upper()))
                info['alphabets'][lang]=dict(required=len(required),missing=ranges(required-set(c)))
                assert not required-set(c),(family,lang,ranges(required-set(c)))
            for text in MARK_SAMPLES:
                rows=hb.shape(text,'ja' if ord(text[0])>0x3000 else 'en')
                assert all(r['gid'] for r in rows),(family,text,rows)
                original=jp_hb if ord(text[0])>0x3000 else (sourcehb if family=='Morimo' else maple_hb)
                actual=ink_signature(hb,text,'ja' if ord(text[0])>0x3000 else 'en')
                expected=ink_signature(original,text,'ja' if ord(text[0])>0x3000 else 'en')
                error=0.0
                if family in ['MorimoCode','MorimoCodeWide15','MorimoCodeGreek5'] and ord(text[0])<0x3000:
                    same=len(actual)==len(expected)
                    if same:
                        for (op,pts),(eop,epts) in zip(actual,expected):
                            same &= op==eop and len(pts)==len(epts)
                            for a,e in zip(pts,epts):
                                if a is None or e is None:same &= a is e
                                else:error=max(error,abs(a[0]-e[0]*ink_factor),abs(a[1]-e[1]))
                    same &= error<=2.0
                else:same=actual==expected
                info['mark_tests'].append(dict(text=text,glyphs=rows,expected_ink_matches=same,max_coordinate_error=error,scale=ink_factor if family in ['MorimoCode','MorimoCodeWide15','MorimoCodeGreek5'] and ord(text[0])<0x3000 else 1.0))
                assert same,(family,text,'mark ink moved relative to base')
            if family=='Morimo':
                text='がぎぐげごぱぴぷぺぽパピプペポ漢字東京京都'
                for form in ['NFC','NFD']:
                    same=signature(hb,hb.shape(ud.normalize(form,text),'ja'))==signature(jp_hb,jp_hb.shape(ud.normalize(form,text),'ja'))
                    info['donor_equivalence'].append(dict(test='Japanese_'+form,equal=same));assert same
            else:
                narrow=720 if family in ['MorimoCode','MorimoCodeWide15','MorimoCodeGreek5'] else 600
                wide=1080 if family in ['MorimoCode','MorimoCodeWide15','MorimoCodeGreek5'] else 1200
                widths=collections.Counter(f['hmtx'][g][0] for g in c.values())
                info['metrics']['encoded_width_counts']=dict(sorted(widths.items()))
                assert set(widths)<={0,narrow,wide},(family,widths)
                for text in [''.join(chr(cp) for cp in range(0x20,0x7f)), 'αβγδεζηθικλμνξοπρστυφχψω',
                             'ŐőŰűŴŵŶŷẀẁẂẃẄẅỲỳ','АБВГДЕЁЖЗИЙ','[]{}()<>!=+-*/.,:;_']:
                    rows=hb.shape(text)
                    assert len(rows)==len(text),(family,'unexpected code ligature',text,rows)
                    assert all(r['advance']==narrow for r in rows),(family,'shaped narrow',text,rows)
                for text in ['丸文字日本語東京京都あいうえお','アイウエオガギグゲゴ','１２３ＡＢＣ［］「」。、']:
                    rows=hb.shape(text,'ja');assert all(r['advance']==wide for r in rows),(family,'shaped Japanese',rows)
                assert sum(r['advance'] for r in hb.shape('が','ja'))==sum(r['advance'] for r in hb.shape('か\u3099','ja'))==wide
                tags={fr.FeatureTag for fr in f['GSUB'].table.FeatureList.FeatureRecord}
                assert tags<={'ccmp','locl','mark','mkmk','rlig'},(family,tags)
                info['metrics']['retained_gsub_features']=sorted(tags)
                code_rows=[dict(line=i,glyphs=hb.shape(line,'ja')) for i,line in enumerate(CODE.splitlines())]
                assert all(r['gid'] for line in code_rows for r in line['glyphs'])
                info['metrics']['code_shape']=code_rows
                info['metrics']['latin_to_japanese']=f'{narrow}:{wide}'
                info['metrics']['terminal_standard_cells']=family=='MorimoGrid'
            # Decode every table and roundtrip webfont; fail on malformed output.
            for tag in f.keys(): f[tag]
            w=TTFont(path.with_suffix('.woff2'));assert w.getBestCmap()==c
            for tag in ['GSUB','GDEF']: assert tag in f and tag in w
            if family=='Morimo': assert 'GPOS' in f and 'GPOS' in w
            else: assert 'GPOS' not in f and 'GPOS' not in w
            names=[r.toUnicode() for r in f['name'].names if r.nameID in {1,3,4,6,16}]
            assert all('Comfortaa' not in n and 'Kiwi' not in n and 'Maple' not in n for n in names)
            assert f['head'].yMax<=f['OS/2'].usWinAscent and -f['head'].yMin<=f['OS/2'].usWinDescent
            info['metrics']['bounds']=[f['head'].xMin,f['head'].yMin,f['head'].xMax,f['head'].yMax]
            info['metrics']['vertical']=[f['hhea'].ascent,f['hhea'].descent,f['hhea'].lineGap]
            info['name_family']=f['name'].getDebugName(1)
            report['fonts'][family]=info;hb.close()
        sourcehb.close();jp_hb.close();maple_hb.close()
    report['refinement']=check_refinement()
    report['wide15_refinement']=check_refinement('Morimo Code Wide15')
    report['greek5_refinement']=check_refinement('Morimo Code Greek5')
    report['five_only']=check_five_only()
    preserved=json.loads((ROOT/'inputs/references/pre-greek5-hashes.json').read_text())
    for name,sha in preserved['sha256'].items():
        assert hashlib.sha256((ROOT/'inputs/dist'/name).read_bytes()).hexdigest()==sha,('Prior candidate changed',name)
    report['all_previous_candidates_preserved']=True
    preferred=json.loads((ROOT/'inputs/references/preferred-0.002-hashes.json').read_text())
    for name,sha in preferred['sha256'].items():
        assert hashlib.sha256((ROOT/'inputs/dist'/name).read_bytes()).hexdigest()==sha,('Preferred candidate changed',name)
    report['preferred_0_002_preserved']=True
    (ROOT/'reports/validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('PASS: P0 alphabets, NFC/NFD samples, mark shaping, donor equivalence, code grid, TTF/WOFF2 tables, names and bounds')

if __name__=='__main__': main()
