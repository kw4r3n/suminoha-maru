#!/usr/bin/env python3
"""Only U+3095/U+3096: source-Zen optical small forms, all other glyphs retained."""
import argparse,copy,ctypes as C,hashlib,json,pathlib,statistics
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates
from fontTools.misc.roundTools import otRound
from fontTools.pens.areaPen import AreaPen
from fontTools.pens.perimeterPen import PerimeterPen
from build import ROOT,EPOCH
STEM='MorimoProseZen-Regular';VERSION='0.003'
BASE=ROOT/'inputs/prose-zen-restored'/(STEM+'.ttf');BASE_SHA='9f61453efa38dd563bc6ceafb66561a20363eb9d4036f0620714c432e09c100e'
ZEN=ROOT/'sources/zenmarugothic/ZenMaruGothic-Regular.ttf';ZEN_SHA='a0c0b53543e0993ae2225e629c833f3d51495ad31720694ff112ce4ce11111ef'
LIB=pathlib.Path('/usr/lib/libfreetype.so.6.20.7')
LIB_SHA='e21271fcdb58bac3a87844265f5c45c3e93d28223f949a70858abe846b11fb9a'
PAIRS=list(zip('あいうえおつやゆよわ','ぁぃぅぇぉっゃゅょゎ'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def geometry(f,n):
 g=f['glyf'][n];gs=f.getGlyphSet();a=AreaPen(gs);gs[n].draw(a);p=PerimeterPen(gs);gs[n].draw(p)
 return {'bbox':[g.xMin,g.yMin,g.xMax,g.yMax],'area':abs(a.value),'perimeter':p.value,'stroke_proxy':2*abs(a.value)/p.value,'points':len(g.getCoordinates(f['glyf'])[0]),'contours':g.numberOfContours}
class Vector(C.Structure):_fields_=[('x',C.c_long),('y',C.c_long)]
class Outline(C.Structure):_fields_=[('n_contours',C.c_ushort),('n_points',C.c_ushort),('points',C.POINTER(Vector)),('tags',C.POINTER(C.c_ubyte)),('contours',C.POINTER(C.c_ushort)),('flags',C.c_int)]
def library():
 assert sha(LIB)==LIB_SHA,'Pinned FreeType build tool mismatch'
 lib=C.CDLL(str(LIB));lib.FT_Outline_EmboldenXY.argtypes=[C.POINTER(Outline),C.c_long,C.c_long];lib.FT_Outline_EmboldenXY.restype=C.c_int
 lib.FT_Init_FreeType.argtypes=[C.POINTER(C.c_void_p)];handle=C.c_void_p();assert lib.FT_Init_FreeType(C.byref(handle))==0
 a=C.c_int();b=C.c_int();c=C.c_int();lib.FT_Library_Version(handle,C.byref(a),C.byref(b),C.byref(c));lib.FT_Done_FreeType(handle)
 return lib,f'{a.value}.{b.value}.{c.value}'
def derive(f,source_name,strength=8):
 g=copy.deepcopy(f['glyf'][source_name]);assert not g.isComposite();g.removeHinting();coords,ends,flags=g.getCoordinates(f['glyf'])
 # Exact initial 3/4 scale about x=500 and downward35 units, 26.6 font-unit grid.
 points=(Vector*len(coords))(*(Vector(otRound((.75*x+125)*64),otRound((.75*y-35)*64)) for x,y in coords));tags=(C.c_ubyte*len(coords))(*(v&1 for v in flags));contours=(C.c_ushort*len(ends))(*ends);outline=Outline(len(ends),len(coords),points,tags,contours,0)
 lib,version=library();assert lib.FT_Outline_EmboldenXY(C.byref(outline),otRound(strength*64),otRound(strength*64))==0
 # Optical compensation8 units in each axis, then recenter the added extent4.
 g.coordinates=GlyphCoordinates([(otRound((p.x-strength*32)/64),otRound((p.y-strength*32)/64)) for p in points]);g.recalcBounds(f['glyf'])
 return g,version

def build(output=None):
 assert sha(BASE)==BASE_SHA and sha(ZEN)==ZEN_SHA,'Pinned baseline/source mismatch'
 out=pathlib.Path(output or ROOT/'inputs/prose-zen-kana');out.mkdir(parents=True,exist_ok=True)
 f=TTFont(BASE,recalcTimestamp=False);source=TTFont(ZEN,recalcTimestamp=False);c=f.getBestCmap();sc=source.getBestCmap();cal=[]
 for full,small in PAIRS:
  a=geometry(source,sc[ord(full)]);b=geometry(source,sc[ord(small)]);ab=a['bbox'];bb=b['bbox'];cal.append({'full':full,'small':small,'full_geometry':a,'small_geometry':b,'bbox_x_ratio':(bb[2]-bb[0])/(ab[2]-ab[0]),'bbox_y_ratio':(bb[3]-bb[1])/(ab[3]-ab[1]),'stroke_proxy_ratio':b['stroke_proxy']/a['stroke_proxy'],'bottom_translation_after_075':bb[1]-.75*ab[1]})
 changed=[]
 for cp,full in [(0x3095,'か'),(0x3096,'け')]:
  n=c[cp];assert list(c.values()).count(n)==1,'Unexpected alias';before=geometry(f,n);g,ftversion=derive(source,sc[ord(full)]);f['glyf'][n]=g;f['hmtx'][n]=(1000,g.xMin);after=geometry(f,n);original=geometry(source,sc[ord(full)])
  changed.append({'codepoint':f'U+{cp:04X}','character':chr(cp),'target_name_legacy':n,'Zen_source_character':full,'Zen_source_name':sc[ord(full)],'before':before,'after':after,'full_source':original,'derived_stroke_ratio':after['stroke_proxy']/original['stroke_proxy'],'advance':1000,'new_lsb':g.xMin})
 replacements={3:VERSION+';MRMO;'+STEM,5:'Version '+VERSION,10:'Only small hiragana U+3095/U+3096 derived optically from pinned Zen ka/ke. All other glyphs, coverage, advances and layout retained from0.002.'}
 for rec in list(f['name'].names):
  if rec.nameID in replacements:f['name'].setName(replacements[rec.nameID],rec.nameID,rec.platformID,rec.platEncID,rec.langID)
 f['head'].fontRevision=.003;f['head'].modified=EPOCH;f.recalcTimestamp=False
 f.save(out/(STEM+'.ttf'));f.flavor='woff2';f.save(out/(STEM+'.woff2'))
 (out/'OFL.txt').write_bytes((ROOT/'inputs/prose-zen-restored/OFL.txt').read_bytes())
 (out/'NOTICES.txt').write_text('Morimo Prose Zen Regular 0.003 — two small-kana refinement\n\n'+f['name'].getDebugName(0)+'\n\nOnly U+3095/U+3096 use derived Zen Maru Gothic ka/ke contours, calibrated to Zen small hiragana. Source scale0.75, x+125/y-35, FreeType outline embolden8 units each axis, recenter-4/-4, integer OpenType rounding;1000 advances. All other glyphs, coverage, metrics and GSUB/GPOS/GDEF are unchanged from0.002. Legacy private glyph names retained for stable IDs. Four complete OFL1.1 source notices retained; Kiwi README derivative-name restriction honored. No installation/default/code-font changes. Noncomposable voiced small kana and Chinese regional/IVS/vertical shaping remain unsupported/unverified.\n')
 report={'family':'Morimo Prose Zen','version':VERSION,'baseline_sha256':BASE_SHA,'Zen_source_sha256':ZEN_SHA,'FreeType':{'library':str(LIB),'version':ftversion,'sha256':sha(LIB),'api':'FT_Outline_EmboldenXY','reference':'https://freetype.org/freetype2/docs/reference/ft2-outline_processing.html#ft_outline_emboldenxy'},'transformation':{'uniform_scale':.75,'initial_translation':[125,-35],'outline_embolden_XY':[8,8],'post_translation':[-4,-4],'arithmetic':'26.6 font-unit fixed point; final fontTools otRound to integer','advance':1000},'calibration':cal,'medians':{k:statistics.median(r[k] for r in cal) for k in ['bbox_x_ratio','bbox_y_ratio','stroke_proxy_ratio','bottom_translation_after_075']},'changed':changed,'preserved':'All other glyphs/mappings/advances/layout; existing full ka/ke unchanged. Same9205 codepoints; no new combining anchors or localization.'}
 (out/'build.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'medians':report['medians'],'FreeType':report['FreeType'],'changed':changed},ensure_ascii=False))
 return report
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output');build(p.parse_args().output)
