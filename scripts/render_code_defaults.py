#!/usr/bin/env python3
import html,json,pathlib
from build import ROOT
from render_code_features import CASES
SELECTED={'ss03':1,'ss05':1,'ss07':1,'ss08':1,'ss09':1,'ss10':1,'ss11':1,'cv63':0,'cv64':1,'cv66':1}
CANDIDATES=[('calt','HTML/XML operators','<!-- --> </> </ />','already enabled'),('calt','Functional operators','<*> <+> <|> >>= =<< >=> <=<','already enabled'),('calt','Ranges and optional expressions','.. ... ..< ?. ?? ?:','already enabled'),('cv01','Normalized symbol designs','$ % & @ Q && <!--','supported optional; not selected'),('cv61','Straight comma / semicolon tails',', ; first,second;','supported optional; not selected'),('cv62','More open question mark','? ?? ?. ?:','supported optional; not selected'),('cv65','Handwritten ampersand','& && &&=','supported optional; not selected'),('ss05','Ordinary escape backslash',r'\\ \n \t','selected on; toggle off to compare')]
def settings(d):return ','.join("'"+k+"' "+str(v) for k,v in d.items())
def page_header(title,description):return '''<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>@font-face{font-family:Small;src:url('fonts/Small.woff2')}*{box-sizing:border-box}body{background:#faf8f2;color:#263b30;margin:0;font:15px/1.65 system-ui}main{max-width:1320px;margin:auto;padding:26px 36px}h1{font-size:25px;font-weight:550}h2{font-size:16px;font-weight:550}.row{border-top:1px solid #cdd8cc;padding:8px 0}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:24px}.cell{min-width:0}pre{font:400 23px/1.6 Small;font-synthesis:none;overflow:auto;white-space:pre;margin:4px 0}small{color:#526b58}@media(max-width:760px){main{padding:18px}.grid{display:block}pre{font-size:19px}}</style><main><h1>'''+html.escape(title)+'</h1><p>'+html.escape(description)+'</p>'
def main():
 out=ROOT/'specimens/code-defaults';(out/'fonts').mkdir(parents=True,exist_ok=True);link=out/'fonts/Small.woff2'
 if not link.exists():link.symlink_to('../../../code-features/MorimoCodeSmall-Regular.woff2')
 s=page_header('コード用：選択された既定設定','前回の画像に表示された右側を採用。ただしcv63の矢印形はOFF。cv64と同じ比較記号を扱うため、cv64の横線形に統一しています。')+'<div class="grid"><p>前回の既定設定</p><p>今回の選択設定</p></div>'
 for tag,label,text in CASES[:9]:
  desc=tag+' · '+('OFF / cv64の横線形' if tag=='cv63' else 'ON')
  s+='<section class="row" data-tag="'+tag+'"><h2>'+html.escape(desc)+'</h2><div class="grid"><div class="cell"><pre>'+html.escape(text)+'</pre></div><div class="cell"><pre style="font-feature-settings:'+settings(SELECTED)+'">'+html.escape(text)+'</pre></div></div></section>'
 s+='<p>同時ONの相互作用：&lt;= / &gt;=はcv64の横線形、&gt;&gt;=はss08の矢印形になります（ss07単独ONの見本とは異なります）。</p><p>フォント専用のFontconfig既定機能設定として反映。TTFの字形や元の機能スイッチは変更していません。Kitty/Pangoでは反映確認済み。Qtはこの既定を自動採用しないため、アプリ内の明示設定が必要です。</p><small>文章用・字幅540/1080・ドット付き0・23pxKitty行高・既存Nerdフォールバックは維持。ss05は既定で有効。折り畳まれていたss01/ss02/ss04は選択していません。</small></main></html>';(out/'index.html').write_text(s)
 s=page_header('他にも使える演算子・任意の字形','すべて現在のMaple由来フォントに収録済み。新しい字形実装は不要です。任意機能のうちss05は今回の既定設定へ追加済みです。')
 for i,(tag,label,text,state) in enumerate(CANDIDATES):
  off=SELECTED|{tag:0};on=SELECTED|{tag:1};left=SELECTED if tag not in SELECTED else on;right=on if tag not in SELECTED else off;s+='<section class="row" data-tag="'+tag+'"><h2>'+html.escape(tag+' · '+label+' — '+state)+'</h2><div class="grid"><div class="cell"><small>'+('calt OFF（他の選択機能は維持）' if tag=='calt' else '現在の選択設定')+'</small><pre style="font-feature-settings:'+settings(left)+'">'+html.escape(text)+'</pre></div><div class="cell"><small>'+('現在すでに有効' if tag=='calt' else ('候補をON（見本のみ）' if tag not in SELECTED else 'OFFにした場合（見本）'))+'</small><pre style="font-feature-settings:'+settings(right)+'">'+html.escape(text)+'</pre></div></div></section>'
 s+='<p>一方、&lt;$&gt;、+=、-=、*=、%=、..=は、この元フォントで専用の全体合字を確認していません（..=の2点部分だけは合字）。新規実装の対象にはしていません。</p><small>Source: pinned Maple Mono v7.9 Regular、OFL1.1。任意のa/g/i/l/1等の文字違いも収録済みですが、今回は演算子と記号の候補に絞っています。</small></main></html>';(out/'candidates.html').write_text(s)
 (out/'choices.json').write_text(json.dumps({'selected':SELECTED,'unselected_displayed_cv63':0,'collapsed_rows_unchanged':['ss01','ss02','ss04'],'candidates':CANDIDATES},ensure_ascii=False,indent=2)+'\n')
 print('Selected-default and preview-only candidate pages prepared')
if __name__=='__main__':main()
