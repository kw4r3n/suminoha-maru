#!/usr/bin/env python3
"""Append-only restoration of the exact prior 501-point repertoire, no core glyph/layout edits."""
import argparse,collections,copy,hashlib,json,pathlib,unicodedata
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._c_m_a_p import CmapSubtable
from build import ROOT,EPOCH
FAMILY='Morimo Prose Zen';STEM='MorimoProseZen-Regular';VERSION='0.002'
BASE_SHA='365e8bb62015f3489b71959e896ead743b090146c92bcf410809e85e70a2736f'
REFERENCE_SHA='e045502cfa973eb9882beba844c843c7595ed99ee946bca644441ba0b654358d'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def targets():
 base=ROOT/'inputs/prose-zen'/(STEM+'.ttf');reference=ROOT/'inputs/prose/MorimoProse-Regular.ttf'
 assert sha(base)==BASE_SHA and sha(reference)==REFERENCE_SHA,'Pinned generated input mismatch'
 b=TTFont(base,recalcTimestamp=False);r=TTFont(reference,recalcTimestamp=False);gap=set(r.getBestCmap())-set(b.getBestCmap());assert len(gap)==501
 return b,r,gap

def build(output=None):
 out=pathlib.Path(output or ROOT/'inputs/prose-zen-restored');out.mkdir(parents=True,exist_ok=True)
 from fetch import main as verify
 verify()
 f,reference,gap=targets();base_cmap=dict(f.getBestCmap());old_order=list(f.getGlyphOrder());source=TTFont(ROOT/'sources/kiwimaru/KiwiMaru-Regular.ttf',recalcTimestamp=False);sc=source.getBestCmap();assert not gap-set(sc)
 roots={sc[cp] for cp in gap};closure=set()
 def collect(n):
  if n in closure:return
  closure.add(n);g=source['glyf'][n]
  if g.isComposite():
   for c in g.components:collect(c.glyphName)
 for n in sorted(roots):collect(n)
 names={n:'kiwiGap_'+n for n in sorted(closure)};new_order=[]
 for n in source.getGlyphOrder():
  if n not in closure:continue
  new=names[n];assert new not in old_order
  g=copy.deepcopy(source['glyf'][n]);g.removeHinting()
  if g.isComposite():
   for c in g.components:c.glyphName=names[c.glyphName]
  f['glyf'][new]=g;f['hmtx'][new]=source['hmtx'][n];new_order.append(new)
 f.setGlyphOrder(old_order+new_order)
 final_map=base_cmap|{cp:names[sc[cp]] for cp in gap}
 for t in f['cmap'].tables:
  if t.isUnicode() and t.format in [4,12,13]:
   for cp in gap:
    if t.format!=4 or cp<=0xFFFF:t.cmap[cp]=final_map[cp]
 if any(cp>0xFFFF for cp in gap) and not any(t.isUnicode() and t.format==12 for t in f['cmap'].tables):
  t=CmapSubtable.newSubtable(12);t.platformID=3;t.platEncID=10;t.language=0;t.cmap=dict(final_map);f['cmap'].tables.append(t)
 assert set(f.getBestCmap())==set(reference.getBestCmap())
 ky_ofl=(ROOT/'sources/kiwimaru/OFL.txt').read_text();ky_copyright=source['name'].getDebugName(0)
 old_ofl=(ROOT/'inputs/prose-zen/OFL.txt').read_text();start=old_ofl.index('This Font Software');combined_ofl=old_ofl[:start]+ky_copyright+'\n\n'+old_ofl[start:]
 replacements={0:f['name'].getDebugName(0)+'\n'+ky_copyright,3:VERSION+';MRMO;'+STEM,5:'Version '+VERSION,10:'Gap-only restoration of501 prior scalar codepoints; all pre-existing glyphs/metrics/layout retained. Japanese regional forms; no SC/TC localization claim.',13:combined_ofl}
 for rec in list(f['name'].names):
  if rec.nameID in replacements:f['name'].setName(replacements[rec.nameID],rec.nameID,rec.platformID,rec.platEncID,rec.langID)
 f['head'].fontRevision=.002;f['head'].modified=EPOCH;f.recalcTimestamp=False
 f['OS/2'].recalcUnicodeRanges(f);f['OS/2'].recalcCodePageRanges(f)
 f.save(out/(STEM+'.ttf'));f.flavor='woff2';f.save(out/(STEM+'.woff2'))
 (out/'OFL.txt').write_text(combined_ofl)
 (out/'NOTICES.txt').write_text('Morimo Prose Zen Regular0.002 — gap-only restoration\n\n'+f['name'].getDebugName(0)+'\n\nOriginal Nunito550/Zen Japanese/Noto450 Greek contours, advances and layout are unchanged. Only501 previously missing scalar codepoints are newly encoded from pinned Kiwi Maru Regular at original size, baseline and metrics, with source hint instructions omitted. CJK compatibility and angle-bracket raw glyphs retain source designs; Unicode NFC/NFD can fold canonical singleton codepoints to unified/core forms. No new regional locl/SC/TC behavior, IVS or vertical-layout promise.\n\nAll four exact OFL1.1 source notices are retained/embedded. Kiwi OFL declares no RFN, while its upstream README separately forbids キウイ丸 in derivative names; Morimo Prose Zen honors that restriction. No installation, font-default change, code-font modification or public font release.\n')
 rows=[]
 from fontTools.unicodedata import script
 for cp in sorted(gap):
  n=sc[cp];rows.append({'codepoint':f'U+{cp:04X}','scalar':cp,'character':chr(cp),'name':unicodedata.name(chr(cp),'UNNAMED'),'script':script(cp),'category':unicodedata.category(chr(cp)),'source_glyph':n,'target_glyph':names[n],'advance':source['hmtx'][n][0],'lsb':source['hmtx'][n][1],'NFC':[f'U+{ord(c):04X}' for c in unicodedata.normalize('NFC',chr(cp))],'NFD':[f'U+{ord(c):04X}' for c in unicodedata.normalize('NFD',chr(cp))]})
 report={'family':FAMILY,'version':VERSION,'baseline_sha256':BASE_SHA,'prior_repertoire_reference_sha256':REFERENCE_SHA,'Kiwi_source_sha256':sha(ROOT/'sources/kiwimaru/KiwiMaru-Regular.ttf'),'restored_codepoints':len(gap),'source_glyphs_copied':len(closure),'private_component_dependencies':len(closure-roots),'previous_glyphs':len(old_order),'total_glyphs':len(f.getGlyphOrder()),'cmap':len(final_map),'overwritten_codepoints':0,'layout_tables_changed':False,'scale':1,'translation':[0,0],'canonical_singletons':sum(r['NFD']!=[r['codepoint']] for r in rows),'by_script':dict(collections.Counter(r['script'] for r in rows)),'categories':dict(collections.Counter(r['category'] for r in rows)),'restored':rows,'source_name_mapping':names,'limits':'Restores only the prior9205-point scalar repertoire. Raw compatibility glyphs can differ from their normalized forms; no new locale-specific Chinese or variation-selector shaping. Existing layout tables are retained, not expanded for arbitrary new-base mark combinations.'}
 (out/'build.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ['restored','source_name_mapping']},ensure_ascii=False));return report
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output');build(p.parse_args().output)
