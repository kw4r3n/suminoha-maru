# 再生成用の設定と検証基準

[全体の案内](../README.md) / [現行フォント](../fonts/README.md)

元フォントは `sources/`、完成した本文・Code12・Code35は `fonts/` に置きます。

| 場所 | 用途 |
|---|---|
| `build-recipe.json` | 生成工程と配布フォントの固定ハッシュ |
| `build-baselines/` | 生成工程が参照する基準ハッシュ |
| `preservation/` | 字形・収録範囲の維持を確認するハッシュ |
| 各工程のディレクトリ | 生成に必要なライセンス・帰属表示 |
| `references/` | 検証用の基準ハッシュ |
