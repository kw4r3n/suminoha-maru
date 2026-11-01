"""Independent final-font checks against the retained 0.001 Code review baseline."""
import hashlib,json,unicodedata
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from build import ROOT,regular,restrict

def outline(font,name):
    if not hasattr(font,'_review_glyphset'):font._review_glyphset=font.getGlyphSet()
    gs=font._review_glyphset;p=DecomposingRecordingPen(gs);gs[name].draw(p);return p.value

def transformed(recording,scale,translation):
    pen=TTGlyphPen(None);target=TransformPen(pen,(scale,0,0,1,translation,0))
    for op,points in recording:getattr(target,op)(*points)
    glyph=pen.glyph();p=DecomposingRecordingPen({})
    glyph.draw(p,None);return p.value

def check(family='Morimo Code'):
    baseline=json.loads((ROOT/'inputs/references/refinement-baseline.json').read_text())
    for name,sha in baseline['sha256'].items():
        path=ROOT/'inputs/references'/name if name.startswith('MorimoCode') else ROOT/'inputs/dist'/name
        assert hashlib.sha256(path.read_bytes()).hexdigest()==sha,('Preserved baseline changed',name)
    old=TTFont(ROOT/'inputs/references/MorimoCode-0.001-Regular.ttf');new=TTFont(ROOT/'inputs/dist'/(family.replace(' ','')+'-Regular.ttf'))
    summary=json.loads((ROOT/'inputs/dist/build-summary.json').read_text())[family]['european_widening']
    f=regular('maplemono')
    for table in f['cmap'].tables:
        if table.isUnicode() and 0xC5 in table.cmap and 0x212B not in table.cmap:table.cmap[0x212B]=table.cmap[0xC5]
    f=restrict(f,set(f.getBestCmap()),True);western=f.getGlyphOrder()
    assert len(old.getGlyphOrder())==len(new.getGlyphOrder())
    assert {cp:old.getGlyphID(g) for cp,g in old.getBestCmap().items()}=={cp:new.getGlyphID(g) for cp,g in new.getBestCmap().items()}
    counts={'widened':0,'other_western_unchanged':0,'japanese_unchanged':0}
    for i,oldname in enumerate(old.getGlyphOrder()):
        newname=new.getGlyphName(i);before=outline(old,oldname);after=outline(new,newname)
        assert old['hmtx'][oldname][0]==new['hmtx'][newname][0],('Advance changed',i)
        if i<len(western) and western[i] in summary['per_glyph_factors']:
            spec=summary['per_glyph_factors'][western[i]]
            expected=transformed(before,spec['factor'],spec['translation'])
            assert after==expected,('Unexpected widened outline',i,western[i])
            counts['widened']+=1
        else:
            assert before==after,('Unselected/Japanese outline changed',i,oldname)
            counts['other_western_unchanged' if i<len(western) else 'japanese_unchanged']+=1
    # Default code substitutions and glyph order must remain identical.
    assert old.getTableData('GSUB')==new.getTableData('GSUB')
    capped={name:spec for name,spec in summary['bearing_capped'].items() if spec['factor']<summary['factor']-1e-9}
    capped_letters={f'U+{cp:04X}':chr(cp) for cp,name in f.getBestCmap().items() if name in capped and unicodedata.category(chr(cp)).startswith('L')}
    return dict(capped_letter_codepoint_count=len(capped_letters),capped_letters=capped_letters,capped_glyph_count=len(capped),capped_glyphs=capped,baseline_commit=baseline['commit'],factor=summary['factor'],advances_unchanged=True,
        exhaustive_outline_counts=counts,gsub_bytes_identical=True,bearing_exceptions=summary['bearing_capped'],
        minimum_selected_bearing=summary['minimum_selected_advance_bearing'])

def check_five_only():
    from hb import Shaper
    old=TTFont(ROOT/'inputs/dist/MorimoCodeWide15-Regular.ttf');narrow=TTFont(ROOT/'inputs/dist/MorimoCode-Regular.ttf');new=TTFont(ROOT/'inputs/dist/MorimoCodeGreek5-Regular.ttf')
    selected={new.getGlyphID(new.getBestCmap()[cp]) for cp in [0x0388,0x0389,0x038C,0x038E,0x038F]}
    assert len(old.getGlyphOrder())==len(new.getGlyphOrder())
    actual_changes=[]
    for i,name in enumerate(old.getGlyphOrder()):
        nname=new.getGlyphName(i);expected=narrow if i in selected else old;ename=expected.getGlyphName(i)
        assert outline(new,nname)==outline(expected,ename),('Unintended five-only geometry change',i,name)
        assert new['hmtx'][nname]==expected['hmtx'][ename]
        if outline(new,nname)!=outline(old,name):actual_changes.append(i)
    assert set(actual_changes)<=selected
    assert old.getTableData('GSUB')==new.getTableData('GSUB')
    sh=Shaper(ROOT/'inputs/dist/MorimoCodeGreek5-Regular.ttf');proof=[]
    for ch,alias in zip('ΈΉΌΎΏ',[0x1FC9,0x1FCB,0x1FF9,0x1FEB,0x1FFB]):
        assert unicodedata.normalize('NFC',chr(alias))==ch
        variants=[ch,chr(alias),unicodedata.normalize('NFD',ch),unicodedata.normalize('NFD',ch).replace('\u0301','\u0341')]
        def sig(text):return [(r['gid'],r['advance'],r['dx'],r['dy']) for r in sh.shape(text,'el')]
        assert all(sig(text)==sig(ch) for text in variants)
        assert sig(ch+'\u0308')==sig(unicodedata.normalize('NFD',ch)+'\u0308')
        proof.append(dict(character=ch,forms=variants,equivalent=True))
    sh.close()
    return dict(rule='Only U+0388/U+0389/U+038C/U+038E/U+038F copy exact +9% geometry including prior safety cap; every other glyph equals Wide15',selected_count=5,actual_outline_changes=len(actual_changes),unchanged_other_glyphs=len(old.getGlyphOrder())-5,canonical_equivalents=proof,gsub_bytes_equal_wide15=True)
