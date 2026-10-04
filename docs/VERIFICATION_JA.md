# 検証報告 — 2026-10-05 JST

## 結論

**コードと配布用ファイルを実装し、Python583件・JavaScript75件・Chromium独立UI26項目が成功しました。実ComfyUIと画像生成品質の合否は未判定です。**

コミット・push・公開はしていません。新リポジトリは読み取り時点で空でした。既存H3は読み取り専用の参照として扱い、変更していません。

## 確認した範囲

| 項目 | 結果 | 証拠と範囲 |
|---|---|---|
| Python全試験 | PASS / 583 | `verification/python_tests.log` |
| JavaScript全試験 | PASS / 75 | `verification/javascript_tests.log` |
| H3状態・幾何・prompt互換性 | PASS | 全127ビュー集合×Auto/Manual×schema v1/v2＝508構成、追加サイズ、固定golden10組 |
| Qwen文章・部位適用 | PASS | compiler由来H3構文の除外、背面範囲、詳細OFF時の全身適用、原文Unicode保持 |
| 厳密JSON・サイズ | PASS | 64KiB境界、重複キー、型、未知値、1000 UTF-16単位、inactive寸法、Core上限 |
| HTTPプレビュー | PASS | 実aiohttpのHTTP200/400/413/415/500、Content-Length・chunked上限196608、node出力一致 |
| JA/EN・保存・Undo・ライフサイクル | PASS / 独立試験 | 実Chromium上の26項目。ComfyUIのhost API・history・Queue payloadは試験用代替 |
| UI画像の目視 | PASS / SVG代替 | `verification/ui_ja.png`、`ui_parts_en.png`。操作部の切れ・重なり、タブ、表示を確認 |
| workflow構造 | PASS | 3つのGUI workflowが各12ノード/15リンク。接続名・型・双方向参照・無循環・PE除去 |
| 空latentの空間補正 | PASS / 分離CPU試験 | Core関数を分離し、形式情報とutilsを代替。1344×768→[1,64,48,84]等を検査 |
| QwenのみのPython登録 | PASS / loader試験 | 通常のaliasおよびCore式に正規化したmodule pathでimport。PromptServerは代替 |
| 元のマネキンPNG | NOT_RUN / 未同梱 | 元PNGのバイナリを取得できず。H3同梱SVGを使用。取り込み用ツールあり |
| 実ComfyUIノード登録・実Pinia連携 | NOT_RUN | 実ComfyUIの起動環境ではない |
| 実Frontendのworkflow読込・graphToPrompt | NOT_RUN | 静的API形式候補は実Frontend出力の代替ではない |
| 実画像・モデルを使ったQueue | NOT_RUN | 実モデル・参照画像を配置していない |
| 実GPU、PNG保存・メタデータ再読込 | NOT_RUN | CPU環境。実画像保存成功を主張しない |
| 人物保持・向き・部位・画像品質・VRAM | NOT_RUN | GPU試験後に判定 |

## ブラウザー試験の条件

環境のChromiumはloopback HTTPへのページ移動を `ERR_BLOCKED_BY_ADMINISTRATOR` で拒否しました。そこでネットワークへ迂回アクセスするのではなく、実UIモジュールを静的に束ねたオフラインHTMLをブラウザーへ直接配置し、Pythonへの試験用bindingでcompiler結果を供給しています。HTTP実装は別のaiohttp試験で検証済みです。

これは実DOM・実ChromiumでのUI確認ですが、**実ComfyUIの画面確認ではありません**。`browser_results.json` に26項目とこの試験範囲を記録しています。初期HTTP試行のログも区別して残しています。

## 実装中に修正・確認した点

Qwen版のpreview障害時に、保存済みJSONが正常であってもraw編集欄を開けるようにしました。UI停止時も保存値へアクセスできることをブラウザー試験に追加しています。

pytestのパッケージ探索によるroot `__init__.py` の誤った単独importは、試験範囲を `tests` に限定して解決しました。製品側の相対importをpytest向けに変更していません。

リポジトリ名を未変換のPython dotted module名として渡す試験は失敗しましたが、Coreを確認すると実際は `module_path.replace(".", "_x_")` で登録します。試験用loaderをこの公式契約に修正し、実際の形式で成功しています。製品の不具合修正として数えていません。

## 基準

- H3配布: `bf792c652a9f50e895409e49fce667fef0f73c25`
- H3資料記載の動作コード: `1074be06120557df3439af19be38d036a122f655`
- ComfyUI Core参照: `f1072eb0350638a3390ddb6afbcaa8c6b237c6fd`
- Python3.13.5、Node22.16.0、pytest9.0.2、aiohttp3.13.3、PyTorch2.10.0+cpu
- Chromium144.0.7559.96、Playwright1.57.0、Linux

実行環境の詳細と時刻は `verification/environment.json`、全ファイルのハッシュは `manifest.json` に保存しています。新しい依存関係のインストールは行っていません。

## 実機で残る受入確認

まず既存H3とこのQwen版を一緒に読み込み、Qwenノードの表示、標準state_json、保存・再読込・Undoと実Queue payloadを確認します。生成に使うモデル・参照画像の存在とCoreノード定義を照合します。

次に基本4面の比較workflowで、実latentが[1,64,48,84]、出力PNGが1344×768になることを確認します。PNGから再読込したworkflow/stateと実行時の設定を照合します。

その後に標準5ビュー・全7ビュー、手袋・靴・背面柄、参照に見えない面、複数seedを評価します。モデル精度、cache、offload、生成時間、観測VRAMを記録し、CPU試験と画像品質を別々に判定します。**現在は実機受入と画像品質が未確認の実装プレビューです。**
