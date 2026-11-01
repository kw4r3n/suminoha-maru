import statistics,math,json,pathlib
from fontTools.ttLib import TTFont
from build_code_common_size import build as core,ROOT,BASE
from build_practical_refinement import sha
OUT=ROOT/'inputs/code-topdown';CURRENT=ROOT/'inputs/code-common-size/MorimoCodeZenCommon110-Regular.ttf'
def build(output=None):
 out=pathlib.Path(output or OUT);f=TTFont(BASE);c=f.getBestCmap();jpchars='日田国語東京観機漢読あいうえおかきくけこ';lat='HINlhd';height=lambda ch:f['glyf'][c[ord(ch)]].yMax-f['glyf'][c[ord(ch)]].yMin
 jp=statistics.median(height(ch) for ch in jpchars);latin=statistics.median(height(ch) for ch in lat);desired=jp/latin
 names=json.loads((ROOT/'inputs/code-common-size/build.json').read_text())['110']['factors'];limits={}
 # Reserve~1px at each cell edge at14pt with current-2px line adjustment; no metric changes.
 for n in names:
  g=f['glyf'][n]
  if g.numberOfContours:limits[n]=min(1140/g.yMax if g.yMax>0 else 10,290/-g.yMin if g.yMin<0 else 10)
 limiting=min(limits,key=limits.get);safe=math.floor(min(desired,limits[limiting])*100)/100
 targets=[(safe*.95,'T95')];result=core(out,targets=targets)
 (out/'reference.json').write_text(json.dumps({'Japanese_reference_chars':jpchars,'Japanese_height_median':jp,'Latin_reference_chars':lat,'Latin_height_median':latin,'unbounded_match_factor':desired,'conservative_cell_ink_limits':[-290,1140],'font_metrics_unchanged':[1200,-350],'limiting_glyph':limiting,'bound':limits[limiting],'safe_upper_factor':safe,'targets':targets,'reason':'True match leaves no safe room for deepest contextual glyphs/marks in27px. Upper candidate is bounded and does not claim fullJapaneseheightmatch. Cell margin is conservative estimate; preview not universal native clipping proof.'},ensure_ascii=False,indent=2));return result
if __name__=='__main__':build()
