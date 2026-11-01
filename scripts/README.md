# 生成・検証スクリプト

コマンドはリポジトリ直下で実行します。Pythonの `-O` は検証用assertを無効にするため使いません。

## 元フォントからの再生成

```sh
python3 scripts/rebuild_fonts.py
# 現行ファイルを変更せず、別の場所に生成する場合
python3 scripts/rebuild_fonts.py --out /tmp/suminoha-fonts
```

`sources/` の元フォントを検証し、合成・字形調整・字幅調整・補助漢字・字間調整を順に実行します。各工程の固定ハッシュ、現行フォントのハッシュ、ライセンスの検証がすべて成功してから出力先を入れ替えます。失敗時は既存のフォントを保持します。

`fonts/code35/` はCode35、`fonts/code12/` はCode12、`fonts/gothic/` は本文用です。

完全な再生成はLinux向けです。`requirements.txt` のPython依存に加え、HarfBuzz・Fontconfig・Pangoが必要です。小さい仮名の輪郭の光学調整には `build_prose_kana.py` に記録したFreeTypeライブラリを使用し、ライブラリ自体のSHA-256も照合します。このビルドツールが未導入、または異なる場合は生成前に停止します。フォントのインストール、アプリ設定の変更、公開は行いません。

## 読み取り専用の確認

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_repository_layout.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

元フォントの固定情報、現行フォント・ライセンス、再生成用のハッシュ記録を確認します。完全な再生成を行う検証は上記の `rebuild_fonts.py` を使います。

## 紹介ページの配布素材

`python3 scripts/build_site_assets.py` が現行フォントを検証し、用途別TTF ZIP・WOFF2・ライセンス一覧を `site/` に生成します。`--out <dir>` で生成先を変更できます。フォント本体の再生成・導入・公開は行いません。[紹介ページの手順](../site/README.md)を参照してください。

## 生成工程

`build_*`、`code_extras.py`、`code_ratio35.py` は、`rebuild_fonts.py` が順に呼び出します。再生成には個別のスクリプトではなく、上記のコマンドを使用してください。

`make_suminoha_companion_config.py` は現行3系列用のFontconfig設定を生成します。`install_prose_tracking_local.py` は本文用フォントをユーザー領域へ導入するスクリプトです。
