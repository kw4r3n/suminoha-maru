# 墨羽 紹介・配布ページ

実フォントの試し書きと、本文・Code12・Code35の用途別TTF配布を行う静的ページです。HTML・CSS・JavaScriptで構成し、外部CDN・解析・フレームワークは使用しません。

[リポジトリの案内](../README.md) / [フォント一覧](../fonts/README.md)

## 起動手順

[requirements.txt](../requirements.txt) の依存関係が入ったPython環境で、リポジトリ直下から実行します。

```sh
# 正本を検証し、配布ZIP・Webフォント・ライセンス一覧を生成
python3 scripts/build_site_assets.py

# ローカル確認用のHTTPサーバーを起動
python3 -m http.server 8765 --bind 127.0.0.1 --directory site
```

[紹介ページ](http://127.0.0.1:8765/)を開きます。ライセンスはページ下部のリンクから、または[一覧ページ](http://127.0.0.1:8765/licenses/index.html)で確認できます。

`file://` でもライセンスの原文は読めますが、配布ファイルの通信確認は動作しません。サイト全体の確認にはHTTPを使ってください。

## ページでできること

- OS・ブラウザの設定に追従するライト／ダーク配色（ライセンス一覧も共通）
- 自由入力と文字サイズ変更
- 本文・Code12・Code35の切り替え
- コード書体のプログラミング合字・対応する字形の切り替え
- 用途別TTF ZIPのダウンロード
- ライセンス・帰属表示の原文の閲覧（JavaScript不要）

書体を切り替えても入力を保持します。本文ではコード専用の操作を無効にし、フォントの読み込み失敗には再試行を表示します。配布物が見つからない場合はリンクを無効にして案内します。

## 編集するファイル

| ファイル | 役割 |
|---|---|
| [index.html](index.html) | 紹介文・操作欄・配布リンク |
| [style.css](style.css) | 配色・レイアウト・レスポンシブ対応 |
| [app.js](app.js) | 試し書きの操作・読み込み回復・配布ファイルの確認 |
| `assets/plates/` | 羽根・墨の透過PNG |
| [build_site_assets.py](../scripts/build_site_assets.py) | 正本から配布素材とライセンス一覧を生成 |

## 生成されるファイル

| 場所 | 内容 |
|---|---|
| `fonts/` | 正本と同一のWOFF2、必要なライセンス、文字範囲別の `fonts.css` |
| `downloads/` | 用途別TTF ZIPと、サイズ・SHA-256を記録した `manifest.json` |
| `licenses/` | 用途・書体ごとに原文を展開して読める `index.html` |

これらはGit管理対象外です。生成物を直接編集せず、正本または生成スクリプトを修正して再生成します。生成先を変える場合は `python3 scripts/build_site_assets.py --out <dir>` を使用します。

生成前に各用途の4フォント、ハッシュ、必要なライセンスを検証します。TTF・WOFF2自体の変更やサブセット化は行いません。Webでは重複しない `unicode-range` により、入力文字に必要な補助漢字だけ読み込みます。ZIPは約21〜22 MBで、4書体・ライセンス・利用案内・SHA256SUMSを含みます。

## 検証手順

### PythonとJavaScriptの確認

```sh
python3 -m unittest discover -s tests -v
python3 scripts/check_repository_layout.py
node --check site/app.js
```

### ブラウザの操作確認

PlaywrightとそのFirefoxが利用できる環境で、上記のHTTPサーバーを起動して実行します。

```sh
node tests/site_browser_checks.js
```

別の場所に導入済みのPlaywrightは `PLAYWRIGHT_MODULE` にモジュールのパスを指定します。確認先は `SITE_URL` で変更できます。

[ブラウザ検証](../tests/site_browser_checks.js)では、書体・サイズ・合字・字形・入力保持、実際のダウンロード、読み込み失敗と回復、配布欠落、JavaScript無効、補助漢字の読み込み、320〜1536px幅を確認します。結果と画面は実行時に出力します。

Safari・Chromium・実機スマートフォンでは未確認です。未収録文字はブラウザの代替書体になるため、入力欄に見えたすべての文字を墨羽の収録文字とはみなさないでください。
