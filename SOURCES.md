# 出典・ライセンス

現行ファミリーのソースと出力の対応は `fonts/*/manifest.json`、上流ファイルのURL・コミット・SHA-256は下記のロックファイルを参照してください。

## 上流ソース

| 役割 | ソース | 固定情報・原文 |
|---|---|---|
| 本文の欧文 | Nunito | `sources.lock.json`、`sources/nunito/` |
| 本文のギリシャ文字など | Noto Sans | `sources/notosans/lock.json` |
| 日本語 | Zen Maru Gothic・Kiwi Maru | `sources.lock.json`、`sources/japanese-medium.lock.json` |
| コードの欧文・合字 | Maple Mono v7.9 unhinted Regular | `sources.lock.json`、`sources/maplemono/` |
| 補助漢字 | Noto Sans CJK JP・Plangothic | `sources/han/lock.json` |
| 限定アイコン | Nerd Fonts Symbols Onlyの選択部分 | `sources/nerd-symbols/lock.json` |
| 追加記号・単色絵文字 | 各ソースの選択部分 | `sources/terminal-addons/lock.json` |
| 初期の再生成用基準 | Comfortaa | `sources.lock.json`、`sources/comfortaa/` |

Google Fontsの基準コミットは `e7db6ca603fd4862010383ff17ffd6cc4ffac1c0`。Mediumなどの追加入力は各ロックファイルのコミットとハッシュを使います。通常の再生成で可変ブランチへ差し替えません。

Maple Monoの元アーカイブはv7.9、SHA-256は `3a35f8f0669bef3dded9df208cc4526a6f7573210e134816e9084a8981271d75`。Regularと対応ライセンスだけを使用します。Nerd Fontsの元アーカイブはv3.5.1、SHA-256は `fdca3682534f6f65e1ccb2345b0362ccf67d9b8eca7c8025330946e93e2473bc`。選択したアイコンに対応する通知を保持し、元アーカイブ全体を単一ライセンスの素材として扱いません。

## 元フォントのダウンロード元

再生成に使う16ファイルの入手先です。「固定版のダウンロード」はロックファイルに記録されたURLを掲載しています。ZIPは必要なフォントとライセンスを展開して使います。配布ページに新しい版があっても、再生成にはロックファイルと同じSHA-256の入力が必要です。

| 元フォント | 配布元 | 固定版のダウンロード |
|---|---|---|
| Comfortaa / Comfortaa[wght].ttf | [配布ページ](https://github.com/google/fonts/tree/e7db6ca603fd4862010383ff17ffd6cc4ffac1c0/ofl/comfortaa) | [TTF](https://raw.githubusercontent.com/google/fonts/e7db6ca603fd4862010383ff17ffd6cc4ffac1c0/ofl/comfortaa/Comfortaa%5Bwght%5D.ttf) |
| Kiwi Maru / KiwiMaru-Regular.ttf | [配布ページ](https://github.com/google/fonts/tree/e7db6ca603fd4862010383ff17ffd6cc4ffac1c0/ofl/kiwimaru) | [TTF](https://raw.githubusercontent.com/google/fonts/e7db6ca603fd4862010383ff17ffd6cc4ffac1c0/ofl/kiwimaru/KiwiMaru-Regular.ttf) |
| Nunito / Nunito[wght].ttf | [配布ページ](https://github.com/google/fonts/tree/e7db6ca603fd4862010383ff17ffd6cc4ffac1c0/ofl/nunito) | [TTF](https://raw.githubusercontent.com/google/fonts/e7db6ca603fd4862010383ff17ffd6cc4ffac1c0/ofl/nunito/Nunito%5Bwght%5D.ttf) |
| Zen Maru Gothic / ZenMaruGothic-Regular.ttf | [配布ページ](https://github.com/google/fonts/tree/e7db6ca603fd4862010383ff17ffd6cc4ffac1c0/ofl/zenmarugothic) | [TTF](https://raw.githubusercontent.com/google/fonts/e7db6ca603fd4862010383ff17ffd6cc4ffac1c0/ofl/zenmarugothic/ZenMaruGothic-Regular.ttf) |
| Maple Mono Regular | [配布ページ](https://github.com/subframe7536/maple-font/releases/tag/v7.9) | [TTF ZIP](https://github.com/subframe7536/maple-font/releases/download/v7.9/MapleMono-TTF.zip) |
| Zen Maru Gothic / ZenMaruGothic-Medium.ttf | [配布ページ](https://github.com/google/fonts/tree/e7db6ca603fd4862010383ff17ffd6cc4ffac1c0/ofl/zenmarugothic) | [TTF](https://raw.githubusercontent.com/google/fonts/e7db6ca603fd4862010383ff17ffd6cc4ffac1c0/ofl/zenmarugothic/ZenMaruGothic-Medium.ttf) |
| Kiwi Maru / KiwiMaru-Medium.ttf | [配布ページ](https://github.com/google/fonts/tree/e7db6ca603fd4862010383ff17ffd6cc4ffac1c0/ofl/kiwimaru) | [TTF](https://raw.githubusercontent.com/google/fonts/e7db6ca603fd4862010383ff17ffd6cc4ffac1c0/ofl/kiwimaru/KiwiMaru-Medium.ttf) |
| NotoSans[wdth,wght].ttf | [配布ページ](https://github.com/google/fonts/tree/e7db6ca603fd4862010383ff17ffd6cc4ffac1c0/ofl/notosans) | [TTF](https://raw.githubusercontent.com/google/fonts/e7db6ca603fd4862010383ff17ffd6cc4ffac1c0/ofl/notosans/NotoSans%5Bwdth%2Cwght%5D.ttf) |
| NotoSansCJKjp-Regular.otf | [配布ページ](https://github.com/notofonts/noto-cjk/tree/523d033d6cb47f4a80c58a35753646f5c3608a78/Sans/OTF/Japanese) | [OTF](https://raw.githubusercontent.com/notofonts/noto-cjk/523d033d6cb47f4a80c58a35753646f5c3608a78/Sans/OTF/Japanese/NotoSansCJKjp-Regular.otf) |
| PlangothicP1-Regular.ttf | [配布ページ](https://github.com/Fitzgerald-Porthmouth-Koenigsegg/Plangothic_Project/releases/tag/V2.9.5795) | [TTF](https://github.com/Fitzgerald-Porthmouth-Koenigsegg/Plangothic_Project/releases/download/V2.9.5795/PlangothicP1-Regular.ttf) |
| PlangothicP2-Regular.ttf | [配布ページ](https://github.com/Fitzgerald-Porthmouth-Koenigsegg/Plangothic_Project/releases/tag/V2.9.5795) | [TTF](https://github.com/Fitzgerald-Porthmouth-Koenigsegg/Plangothic_Project/releases/download/V2.9.5795/PlangothicP2-Regular.ttf) |
| NotoEmoji[wght].ttf | [配布ページ](https://github.com/google/fonts/tree/e7db6ca603fd4862010383ff17ffd6cc4ffac1c0/ofl/notoemoji) | [TTF](https://raw.githubusercontent.com/google/fonts/e7db6ca603fd4862010383ff17ffd6cc4ffac1c0/ofl/notoemoji/NotoEmoji%5Bwght%5D.ttf) |
| NotoSansSymbols-Regular.ttf（2.003） | [配布ページ](https://github.com/notofonts/notofonts.github.io/tree/025970232f4f8ff349310d9785431e87d20ed27c/fonts/NotoSansSymbols/hinted/ttf) | [TTF](https://raw.githubusercontent.com/notofonts/notofonts.github.io/025970232f4f8ff349310d9785431e87d20ed27c/fonts/NotoSansSymbols/hinted/ttf/NotoSansSymbols-Regular.ttf) |
| NotoSansSymbols2-Regular.ttf（2.008） | [配布ページ](https://github.com/notofonts/notofonts.github.io/tree/025970232f4f8ff349310d9785431e87d20ed27c/fonts/NotoSansSymbols2/hinted/ttf) | [TTF](https://raw.githubusercontent.com/notofonts/notofonts.github.io/025970232f4f8ff349310d9785431e87d20ed27c/fonts/NotoSansSymbols2/hinted/ttf/NotoSansSymbols2-Regular.ttf) |
| NotoSansMath-Regular.ttf（3.000） | [配布ページ](https://github.com/notofonts/notofonts.github.io/tree/025970232f4f8ff349310d9785431e87d20ed27c/fonts/NotoSansMath/hinted/ttf) | [TTF](https://raw.githubusercontent.com/notofonts/notofonts.github.io/025970232f4f8ff349310d9785431e87d20ed27c/fonts/NotoSansMath/hinted/ttf/NotoSansMath-Regular.ttf) |
| SymbolsNerdFontMono-Regular.ttf | [配布ページ](https://github.com/ryanoasis/nerd-fonts/releases/tag/v3.5.1) | [Symbols Only ZIP](https://github.com/ryanoasis/nerd-fonts/releases/download/v3.5.1/NerdFontsSymbolsOnly.zip) |

フォント以外のライセンス原文・メタデータ・Unicodeデータの取得元は、上記「上流ソース」の各ロックファイルに記録しています。

## 基準入力の保存ハッシュ

| 保存している入力 | SHA-256 |
|---|---|
| `sources/comfortaa/METADATA.pb` | `70de3bdcdbe33269ad4e584eaa8514ff5e3359307edd534addfdbc199262a539` |
| `sources/comfortaa/OFL.txt` | `bc85bae0b512b799bbfb2b916e4d0a34cfd963d09778cd783e248b479e67760a` |
| `sources/comfortaa/Comfortaa[wght].ttf` | `0fc3f45dc48b614db9c39181502544b37217ecbf8bee2fb35886992bc96c5bd3` |
| `sources/kiwimaru/METADATA.pb` | `a219fb2dfd44148f5d2dce2e9648084caf6a42091606216309eb0a9a05fd584f` |
| `sources/kiwimaru/OFL.txt` | `07ceae7a6e3294cbbd0fdf6e35226550566a1cce9fd226d0f8a57f3d34c664fe` |
| `sources/kiwimaru/KiwiMaru-Regular.ttf` | `b0c3103b2639f690c1fcb44e060058383174bfd2eb72e6635bc9869b374dee87` |
| `sources/nunito/METADATA.pb` | `3e20743c7ddab54c6ac57d79a6be522d4bae795223855ce90a1b13c4132f0754` |
| `sources/nunito/OFL.txt` | `580df76c95a1ec5ab878ceb25bb3d85c6a076804e9c970c8c6972aea775fdf65` |
| `sources/nunito/Nunito[wght].ttf` | `bb55a5ca5c2042335b3991af27c4d0705d0ef41cac6164ac737fd8f2a1e85207` |
| `sources/zenmarugothic/METADATA.pb` | `ca7003349939baf51b9d493fc556be2a02bcae9adf954750b64968aeb0bef784` |
| `sources/zenmarugothic/OFL.txt` | `2a20cf7ce1909d8ee1e949095d340f7d7656705f7c810a2d6faf56800ad0cb3d` |
| `sources/zenmarugothic/ZenMaruGothic-Regular.ttf` | `a0c0b53543e0993ae2225e629c833f3d51495ad31720694ff112ce4ce11111ef` |
| `sources/maplemono/MapleMono-Regular.ttf` | `369583f0b555f33bdb6fdbcc2a6840a7a61a1d72c008a57a665baa36d7d5adf6` |
| `sources/maplemono/OFL.txt` | `eb2d28d2e565a0757e3d64e34ebb452e75a0cad87c0ab3faf4e08ba7596de902` |
| `sources/kiwimaru/UPSTREAM-README.md` | `3a3b6319f6fc2dda5a7e0e249b240537d0a9c8f8bd6973323eadb030766dea0e` |

再生成の手順は [READMEの「自分でビルドする」](README.md#自分でビルドする) を参照してください。
