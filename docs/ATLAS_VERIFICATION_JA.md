# 元マネキンPNGの適用と差分検証

## 適用内容

- Qwen基準コミット: `bd0d7b014c01bb9fb472750bc41690e6f829a545`
- 素材の出典: H3 `bf792c652a9f50e895409e49fce667fef0f73c25` の `web/assets/mannequin-atlas.png`
- 元PNGのGit blob: `35dd5fabbe138b7b181b89d55432a6e53d0e9c34`
- SHA-256: `7213405d101a6ccc0152304680ab5a1b4f17ba456086f3469b41be1319b2b8f6`
- 1254×1254 / RGBA / 823743 bytes。元ファイルを再生成・加工せず、そのまま同梱
- `web/artwork_config.js` を有効化。画像を読み込めない場合の既存SVG fallbackを保持

実行時の変更は素材の追加とフラグ有効化だけです。既存の `web/artwork.js`、CSS、UI、state、node、compiler、workflowは変更していません。元PNGは表示専用です。プロンプト、生成入力、保存JSON、出力寸法、ロケールには影響しません。

## 成功した再検証

- JavaScript: **79件成功**。既存75件＋素材のSHA-256/PNG寸法/有効化、全7枠の座標、source clipPath、ID重複防止、fallback、全身の共通スケールを確認する4件
- Python: **580件成功**。state、compiler、HTTP、node、workflow、取り込みツールの既存試験
- `compileall` と変更対象JavaScriptの構文確認成功
- 元PNGの実画素を目視確認。切り出し座標はH3と同一。全身3枠は350×625で同じスケール
- 画像要素自体のsource clipPathが各cropを限定することを確認。レターボックス領域へ隣のセルが露出する実装には変更していません

実行コマンド:

```text
node --test tests/js/*.test.js
python -m pytest -q --ignore=tests/test_core_contract_isolated.py
python -m compileall -q qwen_image21_character_sheet tests/browser/offline_bundle.py
node --check web/artwork.js
node --check web/artwork_config.js
```

## 未実施の範囲

- 既存のCPU tensor試験3件はPyTorch未導入のため未実施。モデル・GPU・ユーザーPCは使用していません
- 今回のブラウザー再検証は未実施。headless Chromiumがローカルsocket制約で起動できず、利用可能なクラウドブラウザーもローカルHTML/localhostを開けませんでした
- そのため、適用後の選択状態・拡大縮小・実ComfyUI内の見た目は確認済みとしません。初版のSVG画面スクリーンショットは今回のPNG表示の証拠ではありません
- 実ComfyUI、Queue、GPU生成、画像保存、生成品質はこのUI素材更新の検証対象外です

オフラインブラウザー試験用bundleは、今後実行できる環境で同梱PNGの正確なバイト列をdata URIとして使用します。`file:`読込失敗でSVG fallbackに切り替わったまま成功したと誤認するのを防ぐためです。製品側の画像URLは変更していません。

更新後はComfyUIのブラウザーを再読込してください。H3から手動でコピーする必要はありません。
