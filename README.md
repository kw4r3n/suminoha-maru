# 墨羽 / Suminoha Maru

本文用の丸ゴシックと、欧文・漢字の幅比が異なる2種類のコード用フォントです。このリポジトリには、フォント本体、紹介・配布ページ、再生成用の元フォントと設定をまとめています。

## フォントを選ぶ

| 用途 | アプリで選ぶ書体名 | 仕様・ファイル |
|---|---|---|
| 本文 | Suminoha Maru Gothic | [本文の仕様・ファイル](fonts/gothic/README.md) — 自然な欧文幅と日本語。字間調整済み |
| コード 1：2 | Suminoha Maru Code 12 NF | [Code12の仕様・ファイル](fonts/code12/README.md) — 欧文540：漢字1080 |
| コード 3：5 | Suminoha Maru Code 35 NF | [Code35の仕様・ファイル](fonts/code35/README.md) — 欧文648：漢字1080 |

各パッケージには、主書体（primary）と補助漢字のHan JP・Han RareA・Han RareBの計4書体が含まれます。TTFはデスクトップ用、WOFF2はWeb用です。

用途別のTTFファイルは次のリンクから取得できます。フォントを使うだけならPython環境は不要です。

- 本文：[主書体](fonts/gothic/SuminohaMaruGothic-Regular.ttf)・[Han JP](fonts/gothic/SuminohaMaruGothicHanJP-Regular.ttf)・[Han RareA](fonts/gothic/SuminohaMaruGothicHanRareA-Regular.ttf)・[Han RareB](fonts/gothic/SuminohaMaruGothicHanRareB-Regular.ttf)
- Code12：[主書体](fonts/code12/SuminohaMaruCode12NF-Regular.ttf)・[Han JP](fonts/code12/SuminohaMaruCode12NFHanJP-Regular.ttf)・[Han RareA](fonts/code12/SuminohaMaruCode12NFHanRareA-Regular.ttf)・[Han RareB](fonts/code12/SuminohaMaruCode12NFHanRareB-Regular.ttf)
- Code35：[主書体](fonts/code35/SuminohaMaruCode35NF-Regular.ttf)・[Han JP](fonts/code35/SuminohaMaruCode35NFHanJP-Regular.ttf)・[Han RareA](fonts/code35/SuminohaMaruCode35NFHanRareA-Regular.ttf)・[Han RareB](fonts/code35/SuminohaMaruCode35NFHanRareB-Regular.ttf)

1. 用途を1つ選び、その用途のTTFを4ファイル取得します。
2. 取得した4ファイルをインストールし、通常は表にある主書体のファミリー名を選択します。バージョン番号はファミリー名に含まれません。補助漢字の自動選択はアプリや環境によって異なります。
3. ファイルを直接読み込むアプリでは、primary → Han JP → Han RareA → Han RareBの順に指定します。

## 仕様・制約

- 対象はRegular・横組みです。IVS・地域別漢字・縦組み・全Unicodeへの対応は保証していません。
- 本文用フォントは字間を調整済みです。アプリ側の追加字間は0を基準にします。丸め・合字・結合文字の制約は[本文の仕様](fonts/gothic/README.md)を参照してください。
- Code35は3：5の幅比を扱える描画環境が必要です。一般的な1：2端末用フォントではありません。Code12も含め、すべての端末での動作を保証するものではありません。
- NFは限定されたアイコン集合を指し、完全なNerd Fontsではありません。補助漢字には、主書体と字形や濃さの異なる文字があります。

## 自分でビルドする

フォントを使うだけなら、この作業は不要です。以下のコマンドは、リポジトリ直下で実行します。bashなどのPOSIXシェル用です。

### 環境を準備する

Python 3で仮想環境を作り、[requirements.txt](requirements.txt) の依存関係を導入します。

```sh
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements.txt
```

### フォントを再生成する

完全な再生成はLinux向けです。Pythonの依存関係に加え、HarfBuzz共有ライブラリ・Fontconfig（`fc-match`）・Pango（`pango-view`）と、`scripts/build_prose_kana.py` に記録したFreeTypeライブラリが必要です。FreeTypeのバージョンとハッシュが異なる場合は生成前に停止します。詳しくは [scripts/README.md](scripts/README.md) を参照してください。

```sh
python3 scripts/rebuild_fonts.py
# 現行ファイルを置き換えず、別の場所に出力する場合
python3 scripts/rebuild_fonts.py --out /tmp/suminoha-fonts
```

`sources/` の元フォントから全工程を実行し、ハッシュを照合した現行24ファイルだけを出力します。生成や検証が失敗した場合は既存のフォントを置き換えません。

### 配布ZIP・Web用ファイルを作る

```sh
python3 scripts/build_site_assets.py
```

既存の現行フォントから、用途別TTF ZIP、Web用フォント、ライセンス一覧を `site/` に作ります。この処理に必要なのはPythonの依存関係だけです。フォント本体の再生成は行いません。生成物の構成は [site/README.md](site/README.md) を参照してください。

### 検証する

```sh
python3 scripts/check_repository_layout.py
python3 -m unittest discover -s tests -v
```

配置・ハッシュ・ライセンスの確認と、回帰テストを実行します。回帰テストにはFontconfigも必要です。Pythonの `-O` は検証用assertを無効にするため使用しません。

## ファイル構成

| 場所 | 内容 |
|---|---|
| [fonts/](fonts/README.md) | 現行の本文・Code12・Code35 |
| [site/](site/README.md) | 紹介・試し書き・用途別TTF配布ページ |
| [inputs/](inputs/README.md) | 再生成用の設定・固定ハッシュ・ライセンス |
| [scripts/](scripts/README.md) | 生成・検証・保守の入口 |
| `sources/` / [SOURCES.md](SOURCES.md) | 上流ソース、固定ハッシュ、出典 |

## ライセンス

再配布時は、各パッケージの `licenses/` にあるライセンスと帰属表示を同梱します。[OFL.txt](OFL.txt)、[SOURCES.md](SOURCES.md) と各書体のライセンスを確認してください。用途別ZIPには必要な文書を同梱しています。
