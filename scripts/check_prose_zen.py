#!/usr/bin/env python3
import hashlib,json,pathlib,tempfile,unicodedata as ud
from fontTools.ttLib import TTFont
from fontTools.ttLib.scaleUpem import scale_upem
from fontTools.pens.boundsPen import BoundsPen
from fontTools.unicodedata import script
from build import ROOT,regular
from build_prose_zen import build,sources,STEM,FAMILY,GREEK_WEIGHT,GREEK_SCALE
from hb import Shaper
from samples import SAMPLES,ALPHABETS,MARK_SAMPLES
from validate import signature,ink_signature,shift_jis_repertoire,ranges

def main():
 path=ROOT/'inputs/prose-zen'/(STEM+'.ttf');f=TTFont(path);cm=f.getBestCmap();sh=Shaper(path)
 report={'coverage':{},'samples':{},'marks':[],'donor_equivalence':{},'repeat':{},'old_fonts_preserved':False,'limits':['Horizontal Regular P0 test repertoires only; Japanese forms only; new Zen coverage differs from Kiwi and has no SC/TC localization claim','Greek lowercase/detail and Zen Japanese texture remain optical review points','Native apps, long-session comfort and arbitrary combining sequences unverified']}
 for lang,text in ALPHABETS.items():
  required=set(map(ord,text+text.upper()));missing=required-set(cm);assert not missing,(lang,ranges(missing));report['coverage'][lang]={'required':len(required),'missing':[]}
 jis=shift_jis_repertoire();assert not jis-set(cm);report['shift_jis']={'covered':len(jis),'total':len(jis)}
 allink=[]
 for lang,(_,text) in SAMPLES.items():
  a=sh.shape(ud.normalize('NFC',text),lang);b=sh.shape(ud.normalize('NFD',text),lang);sig=lambda rows:[(x['gid'],x['advance'],x['dx'],x['dy']) for x in rows]
  assert all(x['gid'] for x in a+b),(lang,'notdef')
  assert sig(a)==sig(b),(lang,'NFC/NFD')
  report['samples'][lang]={'nfc_nfd_exact':True,'glyphs':a}
  for row in a:
   p=BoundsPen(f.getGlyphSet());f.getGlyphSet()[row['glyph']].draw(p)
   if p.bounds:allink.extend([p.bounds[1]+row['dy'],p.bounds[3]+row['dy']])
 with tempfile.TemporaryDirectory(prefix='morimo-prose-check-') as tmp:
  refs={}
  for d,ff in sources().items():
   for tag in ['DSIG','STAT','vhea','vmtx','BASE','VORG']:
    if tag in ff:del ff[tag]
   p=pathlib.Path(tmp)/(d+'.ttf');ff.save(p);refs[d]=Shaper(p)
  for lang,(_,text) in SAMPLES.items():
   if lang in ['el','ja']:continue
   ref=refs['nunito'];assert signature(sh,sh.shape(text,lang))==signature(ref,ref.shape(text,lang)),(lang,'Nunito changed')
   report['donor_equivalence'][lang]='exact Nunito contours/advances/offsets'
  for text in ['Ελληνικά','Καλημέρα','κόσμε','ΈΉΌΎΏ','ΐΰ','ΆΊ','αβγδεζηθικλμνξοπρσςτυφχψω']:
   ref=refs['notosans'];assert signature(sh,sh.shape(text,'el'))==signature(ref,ref.shape(text,'el')),(text,'Greek donor changed')
  report['donor_equivalence']['el']='exact natural-size Noto450 Greek word contours/advances/offsets; shared spaces/punctuation remain Nunito'
  for text in ['がぎぐげごぱぴぷぺぽパピプペポ漢字東京京都','日本語の文章。ひらがな・カタカナ。','＄１２３円、日本語。']:
   ref=refs['zenmarugothic'];assert signature(sh,sh.shape(text,'ja'))==signature(ref,ref.shape(text,'ja')),(text,'Japanese donor changed')
  report['donor_equivalence']['ja']='exact Zen pure Japanese contours/advances/offsets'
  for text in MARK_SAMPLES+['α\u0301\u0308','ω\u0308','Η\u0301','n\u0303\u0301','Α\u0308','Ω\u0308']:
   lang='ja' if ord(text[0])>0x3000 else ('el' if script(ord(text[0]))=='Grek' else 'en')
   donor='zenmarugothic' if lang=='ja' else ('notosans' if lang=='el' else 'nunito')
   ref=refs[donor];actual=ink_signature(sh,text,lang);expected=ink_signature(ref,text,lang)
   assert actual==expected,(text,'positioned mark differs',donor)
   report['marks'].append({'text':text,'donor':donor,'positioned_ink_exact':True,'glyphs':sh.shape(text,lang)})
 # All encoded Greek canonical aliases normalize identically under the selected donor.
 canon=[]
 for cp in cm:
  if script(cp)!='Grek':continue
  text=chr(cp);a=sh.shape(ud.normalize('NFC',text),'el');b=sh.shape(ud.normalize('NFD',text),'el')
  assert sig(a)==sig(b),(hex(cp),'Greek canonical alias');canon.append(cp)
 report['greek_canonical_codepoints_tested']=len(canon)
 widths={ch:f['hmtx'][cm[ord(ch)]][0] for ch in 'ilMW012あ日本。、αοΗΙ'};assert len({widths[c] for c in 'ilMW012'})>=5
 report['advances']=widths;report['latin_proportional']=True
 for tag in f.keys():f[tag]
 w=TTFont(path.with_suffix('.woff2'));assert w.getBestCmap()==cm and w['hmtx'].metrics==f['hmtx'].metrics
 for tag in ['GSUB','GPOS','GDEF']:assert w[tag].compile(w)==f[tag].compile(f)
 assert f['name'].getDebugName(1)==FAMILY;assert f['name'].getDebugName(6)=='MorimoProseZen-Regular'
 for n in f['name'].names:
  if n.nameID in [1,3,4,6,16]:assert all(x not in n.toUnicode() for x in ['Nunito','MPLUS','Kiwi','Comfortaa'])
 assert f['post'].isFixedPitch==0
 assert f['head'].yMax<=1150 and f['head'].yMin>=-350,(f['head'].yMin,f['head'].yMax)
 assert min(allink)>=-350 and max(allink)<=1150
 report['font_bounds']=[f['head'].xMin,f['head'].yMin,f['head'].xMax,f['head'].yMax];report['shaped_sample_ink_y']=[min(allink),max(allink)];report['vertical']=[1150,-350,0];report['cmap']=len(cm);report['glyphs']=len(f.getGlyphOrder());report['ttf_woff2_layout_equal']=True
 for rel,expected in json.loads((ROOT/'inputs/preservation/selected-preserved.json').read_text()).items():
  p=ROOT/rel;assert hashlib.sha256(p.read_bytes()).hexdigest()==expected,rel
 for n,expected in json.loads((ROOT/'inputs/build-baselines/code-small.json').read_text())['repeat'].items():assert hashlib.sha256((ROOT/'inputs/code-small'/n).read_bytes()).hexdigest()==expected,n
 assert f['OS/2'].usWeightClass==550
 for donor in ['nunito','notosans','zenmarugothic']:
  original=TTFont(next((ROOT/'sources'/donor).glob('*.ttf')));assert original['name'].getDebugName(0) in f['name'].getDebugName(0)
 report['old_fonts_preserved']=True
 with tempfile.TemporaryDirectory(prefix='morimo-prose-repeat-') as tmp:
  build(tmp)
  for p in sorted((ROOT/'inputs/prose-zen').iterdir()):
   expected=hashlib.sha256(p.read_bytes()).hexdigest();assert expected==hashlib.sha256((pathlib.Path(tmp)/p.name).read_bytes()).hexdigest(),p.name
   report['repeat'][p.name]=expected
 (ROOT/'reports/prose-zen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ['samples','marks']}))
if __name__=='__main__':main()
