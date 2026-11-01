#!/usr/bin/env python3
"""Exact current cmap and localization audit; encoding sets are coverage proxies only."""
import json,unicodedata
from pathlib import Path
from fontTools.ttLib import TTFont
from hb import Shaper
ROOT=Path(__file__).resolve().parents[1]
SAMPLES={'SC':'简体中文：汉语阅读让我们认识这个世界，学习广东的历史与文化。龙、门、书、车、风。','TC':'繁體中文：漢語閱讀讓我們認識這個世界，學習廣東的歷史與文化。龍、門、書、車、風。','regional':'骨直令羽葛辻邊曜返遍'}
def repertoire(codec):
 found=set()
 for a in range(0x81,0xff):
  for b in range(0x40,0xff):
   try:s=bytes([a,b]).decode(codec)
   except UnicodeDecodeError:continue
   found.update(ord(c) for c in s if unicodedata.category(c)=='Lo' and 'CJK' in unicodedata.name(c,''))
 return found
def main():
 f=TTFont(ROOT/'inputs/dist/Morimo-Regular.ttf');cmap=f.getBestCmap();s=Shaper(ROOT/'inputs/dist/Morimo-Regular.ttf')
 report={'claim':'Partial shared Han coverage with Japanese glyph forms; neither full SC nor TC support/localization','repertoire_proxies':{},'samples':{},'localization':{},'limits':['GB2312 and Big5 Han repertoires are explicit legacy encoding proxies, not complete modern Chinese standards','No Chinese regional donor or Chinese typography QA has been added','Missing characters must not be concealed by system fallback']}
 for codec in ['gb2312','big5']:
  r=repertoire(codec);miss=sorted(r-set(cmap));report['repertoire_proxies'][codec]={'han_total':len(r),'covered':len(r)-len(miss),'missing':len(miss),'missing_codepoints':[f'U+{cp:04X}' for cp in miss]}
 for tag,text in SAMPLES.items():
  report['samples'][tag]={'text':text,'missing_characters':''.join(dict.fromkeys(c for c in text if ord(c) not in cmap)),'missing_codepoints':[f'U+{ord(c):04X}' for c in dict.fromkeys(text) if ord(c) not in cmap]}
  if tag=='regional':
   for language in ['ja','zh-Hans','zh-Hant','zh-HK']:
    report['localization'][language]=[dict(character=c,glyph=s.shape(c,language)[0]['glyph']) for c in text]
 report['GSUB_scripts']=[r.ScriptTag for r in f['GSUB'].table.ScriptList.ScriptRecord]
 report['regional_sample_identical']=len({json.dumps(v,sort_keys=True) for v in report['localization'].values()})==1
 report['options']={'primary':'Consider separate Noto Sans CJK SC/TC (and HK if requested) regional faces, OFL1.1, rather than blindly unioning Han glyphs','source':'https://github.com/notofonts/noto-cjk','needed':'Pin exact SC/TC fonts/licenses, decide rounded design compromise and default region vs locl, merge disjoint cmap with regional substitution support, test vocabulary/marks/punctuation and native language rendering. Full Chinese expansion not undertaken.'}
 (ROOT/'reports/chinese-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 lines=['# Current Simplified / Traditional Chinese audit','',report['claim']+'.','']
 for codec,r in report['repertoire_proxies'].items():lines.append(f'- {codec} Han proxy: {r["covered"]}/{r["han_total"]} covered; {r["missing"]} absent.')
 lines+=['','## Representative text','']
 for tag,r in report['samples'].items():lines += [f'- {tag}: {r["text"]}',f'  Missing: {r["missing_characters"] or "none"}.']
 lines+=['','The regional comparison glyphs shape identically for ja, zh-Hans, zh-Hant and zh-HK. GSUB scripts: '+', '.join(report['GSUB_scripts'])+'. This does not certify Chinese forms. All current Han originates in the Japanese Kiwi Maru donor.','',report['options']['primary']+'. See [official source](https://github.com/notofonts/noto-cjk). '+report['options']['needed'],'','Encoding counts are coverage proxies, not modern national/educational standard conformance. Complete missing-codepoint lists and per-language glyph IDs are in chinese-audit.json.']
 (ROOT/'reports/chinese-audit.md').write_text('\n'.join(lines)+'\n')
 print('\n'.join(lines[:18]))
if __name__=='__main__':main()
