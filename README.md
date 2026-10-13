# Qwen Image 2.1 Character Sheet Designer

[English](#english)

<img width="1543" height="713" alt="{3DB22210-59B7-4161-8A96-29B0211C5E33}" src="https://github.com/user-attachments/assets/785a18e0-fa55-41ab-b12a-d0d98b40f9ac" />


## v1.4.2の変更点

- **Sheet Encode対応テンプレートを追加**：部位参照の画像番号とEncoder入力を同じ参照計画に揃えます。
- **既存テンプレートの注記を訂正**：Core直接配線の制約と、専用参照を使う場合の接続先を明記しました。
- **CPU回帰試験を追加**：標準構成・部位参照・欠番・同役割優先・Guide・Batch Outを確認します。

## v1.4.1の主な変更点（前回公開版0.1.0から）

- **Batch Out**：選択ビューを1枚ずつ生成。Autoはビュー別サイズ、Manualは指定幅×高さを各画像に適用。
- **追加参照3枠・Sheet Encode**：参照の役割分けと明示的な範囲指定に対応。
- **部位別選択**：衣装・手・履物をカード直下で選択。すべてAutoが初期値。
- **生成指示の改善**：グローブ着用、左右の履物、靴の被覆、Autoの着用衣装を改善。

旧V1／V1.1ノードと既存ワークフローを互換用に保持しています。

**Package v1.4.2** — a visual character-sheet designer for ComfyUI and Qwen Image 2.1.

Select views, keep a character consistent with image references, and generate either a sheet or independent images. No LLM, classifier, extra model, or H3 installation is required by this node pack. Model loading, encoding, sampling and saving remain in the workflow.

## 日本語

### ノードとバージョン

パッケージ全体のバージョンは **1.4.2** です。ノードの表示名にあるV1／V1.1／V1.2は、互換性を保つためのノード系列名です。最新版は **Qwen 2.1 Sheet Designer Reference V1.2** です。

| 表示名 | 用途 | ノードID |
| --- | --- | --- |
| Qwen 2.1 Sheet Designer Reference V1.2 | 最新版。追加参照3枚、部位選択、個別出力、参照計画 | `QwenImage21CharacterSheetDesignerReferenceV12` |
| Qwen 2.1 Sheet Encode | V1.2の参照計画に従って画像をCore Encoderへ渡す | `QwenImage21CharacterSheetEncode` |
| Qwen 2.1 Sheet Designer Reference V1.1 | 既存ワークフロー用の互換ノード | `QwenImage21CharacterSheetDesignerMultiReference` |
| Qwen 2.1 Sheet Designer V1 | 初期ワークフロー用の互換ノード | `QwenImage21CharacterSheetDesigner` |

### インストール・更新

ComfyUIの`custom_nodes`内にこのリポジトリを配置します。Gitでのインストール例：

```sh
cd ComfyUI/custom_nodes
git clone https://github.com/ukr8b3g-cmyk/Qwen-Image-2.1-Character-Sheet-Designer.git
```

ZIPの場合は[Releases](https://github.com/ukr8b3g-cmyk/Qwen-Image-2.1-Character-Sheet-Designer/releases)の配布ZIPを展開し、`__init__.py`があるフォルダーを`custom_nodes`へ入れます。既存のGitインストールはComfyUI-Managerまたは通常のGit更新手順で更新してください。作業中の生成が終わってからComfyUIバックエンドを再起動し、ブラウザーを再読込します。

Qwen 2.1対応のComfyUI Core（`TextEncodeQwenImage21`、`QwenImage21Cache`）とQwen 2.1のモデル・テキストエンコーダー・VAEが必要です。モデルは同梱していません。テンプレート内のモデル名は環境に合わせて選び直してください。

### テンプレート

部位専用参照やBatch Outには、まず[Sheet Encode対応テンプレート](workflows/QwenImage21_Character_Sheet_Designer_Reference_V12_Sheet_Encode_template.json)を読み込みます。`prompt`・`reference_plan`・`layout_image`と人物・追加参照を同名入力へ接続済みです。幅・高さ、生成・PNG保存設定は既存版を維持しています。

[Core直接接続テンプレート](workflows/QwenImage21_Character_Sheet_Designer_Reference_V12_template.json)も残しています。標準シートの同一人物の補足参照用で、部位専用の役割・参照範囲はSheet Encode版を使ってください。直接配線ではビューごとの参照選別が反映されず、プロンプトの画像番号と入力画像がずれる場合があります。

既存版では今回指定されたサブグラフ構成のワークフローを採用し、4つのLoad Imageのタイトルを次の名前へ変更しています。配線・生成設定・保存設定は元のワークフローと同じです。

| タイトル | Designer入力 | Core Encoder入力 |
| --- | --- | --- |
| Character Image | `character_image` | `images.image_2` |
| Reference Image 1 | `reference_image_1` | `images.image_3` |
| Reference Image 2 | `reference_image_2` | `images.image_4` |
| Reference Image 3 | `reference_image_3` | `images.image_5` |

`layout_image`は`images.image_1`へ接続済みです。Guide OFFではNoneとなり、Coreが有効画像の番号を詰めます。追加参照3つは初期状態でバイパスされています。自分の画像を各Load Imageで選び、使う追加参照だけを有効にしてください。画像データは配布物に含めていません。

標準5ビュー、Auto・基準高1120、Guide OFF、Batch Out OFF、30ステップ、CFG 1、Euler／simple、Encoder resolution 1024です。保存は指定ワークフローどおり`SaveImageAdvanced`のPNGです。この保存ノードがない環境では標準`SaveImage`へ置き換えられます。

参照の役割をビューごとに振り分ける場合は、Qwen 2.1 Sheet Encodeを使い、Designerの`prompt`・`reference_plan`・`layout_image`と、人物・追加参照を同じ名前の入力へ接続します。WebP保存には[Save WEBP Meta](https://github.com/ukr8b3g-cmyk/ComfyUI-save-webp-meta-node)を利用できます。Core Encoderへ直接つなぐテンプレートでは、`reference_plan`による参照の除外・並べ替えや`reference_regions`の切り取りは実行されません。

既存の[V1ワークフロー](workflows/QwenImage21_Character_Sheet_Designer_wf.json)も残しています。旧V1／V1.1ノードIDは維持し、ユーザーの既存ワークフローを読み込めます。

### 旧版のダウンロードと互換性

更新前の公開版（パッケージ0.1.0）は[legacy-v0.1.0ブランチ](https://github.com/ukr8b3g-cmyk/Qwen-Image-2.1-Character-Sheet-Designer/tree/legacy-v0.1.0)へ固定して残しています。そのブランチでCode → Download ZIPから取得できます。最新版にも旧V1／V1.1ノードを同梱し、既存のノードIDとワークフローを維持します。

今後も新しいバージョンのReleaseを追加し、既存Release・旧版のダウンロードを残す方針です。互換用ノードの表示名と、パッケージ全体のバージョンを分けて管理します。

### 見たまま使う

上のカードで出力するビューを選びます。Reference V1.2は胸像6種、全身正面・側面・背面、衣装正面・背面、両手、足・履物の13ビューに対応します。下のプレビューは選択内容と出力比率を表示します。

衣装・手・足のカード直下で部位ごとの選択ができます。初期値はすべてAutoです。性別で分類しません。

| 部位 | 選択肢 | 動作 |
| --- | --- | --- |
| 衣装 | Auto／パンツ型／スカート・ローブ型 | 脚ごとに分かれる形、または連続した裾を指定。丈・色・柄などは参照と部位文から維持 |
| 手 | Auto／素手／グローブ | 全身・着用衣装に見える手にも適用。グローブは実際に着用する指示 |
| 足・履物 | Auto／靴あり／靴なし | 靴種は固定せず参照と衣装に従う。靴なしは靴下・タイツを強制的に除去しない |

Autoは参照に従う生成指示です。画像認識によって選択欄が自動で変わる機能ではありません。Auto以外は選んだ型・被覆を優先し、部位文で両立する詳細を指定できます。完全な裸足や特定の靴・グローブは部位文へ入力します。衣装正面・背面は「着用」と「衣服のみ」を区別します。着用では頭を画面外に置いた人物、衣服のみでは人体を追加しない指示です。

「部位指定」では追加参照の役割を選びます。同一人物の補足、顔、頭部、衣装全体、衣装正面、衣装背面、手、履物を指定できます。Designerへ接続するだけでは生成用Encoderへ画像は渡りません。上の表のように両方へ接続してください。異なる部位の参照を混ぜる場合はSheet Encodeへ接続する構成が適しています。

「スタイル」は指定なし、アニメ、写真、写実絵画、写実アニメ、油彩、水彩、ガッシュ、色鉛筆、3D CGから選べます。指定なしは参照の画風に従います。数値入力はEnterまたはフォーカス移動で確定します。UIはComfyUIの言語設定に従って日本語／英語を切り替えます。

### Auto・Manual・Batch Out

| サイズ設定 | Batch Out OFF | Batch Out ON |
| --- | --- | --- |
| Auto | 選択ビューからシート全体の寸法・配置を計算 | 各ビューの種類に応じた寸法で独立生成 |
| Manual | 入力した幅×高さのシート内へ選択ビューを配置 | 入力した幅×高さを**各1枚**へ共通適用 |

Batch Out ONは生成後のシート分割ではありません。選択したビューをカード順に別々に生成します。例えば5ビュー・Manual 768×1152なら768×1152の画像を5枚生成します。プレビューも各画像の比率で表示します。Manualの保存済み寸法はビューやBatch切替で勝手に変更しません。

Auto・基準高1120での個別出力寸法は次の既定値です。すべてのモデルや参照に対する画質の最適値を保証するものではありません。

| ビュー | 個別出力寸法 |
| --- | --- |
| 胸像 | 1024×1024 |
| 全身・衣装 | 768×1344 |
| 手・足／履物 | 1184×864 |

V1.2の6出力は`prompt`、`width`、`height`、`layout_image`、`filename_suffix`、`reference_plan`です。対応したComfyUIリストとして出力します。幅・高さは`EmptyLatentImage`へ接続し、Encoderが返すlatentを出力サイズの代用にしません。latentのbatch_size=1なら選択数分を生成します。Bに変更すれば選択数×B枚です。全ビューはその投入のSeedを共有します。

標準のComfyUIリスト実行では全ビューのEncode→Sample→Decode→Saveと進むため、途中でまだ画像ファイルが保存されていないことがあります。エラー時の自動再送・自動再開は行いません。保存形式・場所・圧縮率は保存ノードで指定します。

Guide ONは配置の参照画像を作ります。Guide OFFでは作成せずNoneを返します。ガイドはモデルへの指示であり、生成画像を厳密に分割・合成するマスクではありません。向きや細部がずれる場合があります。

### 参照の範囲と画質

Sheet Encodeの`reference_regions`で参照範囲を明示できます。空の`{}`は参照全体を使い、画像別・ビュー別の正規化矩形で入力範囲を指定できます。自動分類・自動切り取りはしません。[範囲指定の説明](docs/REFERENCE_REGIONS_JA.md)を参照してください。Encoderの`resolution`は参照のリサンプル量で、出力Width/Heightとは別です。

Qwenで作成した参照を編集する場合、参照作成時とは異なる編集Seedを選び、その編集Seedを比較中は固定する方法を確認しました。強い斑点が改善した局所試験ですが、すべての荒れの原因や解決を保証しません。WebP品質70は保存容量の設定で、生成された画素の不整合を直す設定ではありません。

### v1.4.1の変更と確認範囲

グローブを実際に着用する指示、左右一組の履物の整合、靴ありの明確な被覆、Autoでも人物が着た衣装を描く指示を改善しました。グローブの形・指の開きは参照／部位文に従い、未指定時だけ全指被覆を既定とします。旧ノードID・既存の保存状態・出力・配置計算を維持しています。

2026-10-13の関連Pythonテストは578件成功。実CoreのCPU確認では候補8グラフと最終Auto4グラフを検証し、CUDAを初期化していません。事前生成文のGPU比較は合計12枚です。初回8枚のうち6枚合格・Auto2枚失敗で、そのAuto文は不採用。裸足／ブーツ×2Seedの再試験4枚で被覆を確認しました。変更していない6条件と合わせて採用する生成文10条件を確認しています。

その後、再起動済みの実Designerで衣装Auto・Gloves・Footwear Auto・Manualシートの4条件を実行しました。4枚の寸法・実行文・保存設定を照合し、デコード後の画素は先に確認した候補と4/4一致しました。検証は参照3素材・編集2Seedに限定されます。ブーツ上端の収まり、足詳細の下腿、向き・細かな解剖形状には改善余地があります。すべての画像・選択組合せのGPU合格を示すものではありません。

配布ZIPの再検証はPython 1,734件成功・1件スキップ、JavaScript 216件成功です。今回指定されたテンプレートは接続整合性と名前・設定の保存を確認しました。このタイトル変更でGPU生成は繰り返していません。

記録は[最新GPU検証](verification/gpu_summary_v141.json)、[配布検証](verification/release_v141.json)にあります。公開対象はノード本体・必須UI素材・指定ワークフロー・README・利用説明と検証要約です。作業用仕様書、検証用画像、ローカル構成付き詳細記録と追加テストワークフローはローカルに保持し、配布しません。

## English

### What's new in v1.4.2

- **Added a Sheet Encode template** so per-part reference tags and Encoder images use the same reference plan.
- **Corrected the preserved direct template's note** to explain its limits and when Sheet Encode is required.
- **Added CPU regression tests** for defaults, dedicated roles, missing slots, duplicate-role priority, Guide and Batch Out.


### What's new in v1.4.1 (since public package 0.1.0)

- **Batch Out** generates selected views individually. Auto uses view-specific sizes; Manual applies width × height to each image.
- **Three extra references and Sheet Encode** support reference roles and explicit source regions.
- **Per-part controls** beneath the cards select clothing, hands and footwear; all default to Auto.
- **Improved generation prompts** cover worn gloves, paired footwear, shoe coverage and Auto clothing-on-wearer views.

Legacy V1/V1.1 nodes and existing workflows remain compatible.

Package **v1.4.2** includes the latest **Reference V1.2**, **Sheet Encode**, and the compatible **V1/V1.1** nodes. Node display versions identify compatible node families; they are not the package release number. No H3 installation or additional inference model is required by this pack.

Install this folder in `ComfyUI/custom_nodes`, or use the release ZIP. After your active work finishes, restart the ComfyUI backend and reload the browser. Qwen 2.1-capable ComfyUI Core, model weights, text encoder and VAE are required. Choose installed model files and your own images in the workflow.

Use the [Sheet Encode template](workflows/QwenImage21_Character_Sheet_Designer_Reference_V12_Sheet_Encode_template.json) for dedicated references, per-view Batch Out routing or explicit crops. It connects prompt, reference_plan, layout and matching image inputs while preserving output dimensions, sampling and PNG saving. The preserved direct template is for standard sheets using same_character supplements; dedicated roles can make its image tags disagree with Core inputs.

The original [Reference V1.2 template](workflows/QwenImage21_Character_Sheet_Designer_Reference_V12_template.json). Its four Load Image titles are **Character Image**, **Reference Image 1**, **Reference Image 2**, **Reference Image 3**. Only those titles were changed in the supplied template; wiring and generation/save settings are preserved. Optional references are bypassed by default. It uses Core TextEncodeQwenImage21 and PNG SaveImageAdvanced. Replace the save node with standard SaveImage if unavailable.

Connect each image to both the Designer and the Encoder. Core image slot 1 receives the layout, slot 2 the character, slots 3–5 the optional references. Guide OFF supplies None; Core compacts active image numbers. Direct Core wiring does not execute the per-output reference plan or explicit source crops. For heterogeneous references, connect matching named image inputs, prompt, reference_plan and layout_image to Qwen 2.1 Sheet Encode. Save WEBP Meta is an optional WebP output node. No reference-image bytes or model weights are distributed.

Select from 13 view cards. The compact controls beneath clothing, hands and footwear choose **Auto / pants / skirt–robe**, **Auto / bare / gloves**, and **Auto / footwear on / footwear off**. All default to Auto, meaning follow references. They are prompts, not image classification. Footwear on leaves shoe type open; footwear off can preserve socks/tights. Use part text for specific details. Choices also apply to naturally visible parts in body views. Worn clothing and garment-only views are distinct.

**Batch Out OFF** produces one arranged sheet. **Batch Out ON** independently generates each selected view in card order. Auto chooses sizes by view type; at panel height 1120, busts use 1024×1024, body/clothing 768×1344, hands/footwear 1184×864. **Manual width×height applies to every separate image when Batch Out is ON**, or to the whole sheet when OFF. The preview follows each output aspect ratio. These defaults are not universal quality optima.

The six V1.2 outputs are aligned ComfyUI lists: prompt, width, height, layout_image, filename_suffix, reference_plan. Connect width/height to EmptyLatentImage; keep latent batch_size 1 unless you need multiple samples per view. The supplied seed is shared across views. List execution may finish sampling all views before saving. Errors do not trigger automatic retries. Save nodes determine format, location and compression.

Guide OFF bypasses guide creation. Guide ON is a model reference, not hard masking or deterministic compositing. Sheet Encode supports optional explicit per-image/per-view `reference_regions`; `{}` uses complete sources. See [reference region documentation](docs/REFERENCE_REGIONS_JA.md). Encoder resolution resamples references and does not set output dimensions.

v1.4.1 improves worn gloves, consistent paired footwear, identifiable footwear coverage, and clothing-on-wearer instructions in Auto. IDs, old nodes, saved states, geometry and output contracts remain compatible. Relevant repair tests passed (578 Python); actual Core CPU checks and GPU acceptance are recorded separately. Ten final frozen-prompt conditions were checked, then four actual Designer cases matched their accepted candidate pixels exactly. GPU evidence is limited to three reference material sets and two edit seeds. Boot-top framing, lower-leg remnants and fine anatomy still need care; it is not all-image or all-combination acceptance. See [GPU record](verification/gpu_summary_v141.json) and [release validation](verification/release_v141.json).

Previous public package 0.1.0 is preserved on [legacy-v0.1.0](https://github.com/ukr8b3g-cmyk/Qwen-Image-2.1-Character-Sheet-Designer/tree/legacy-v0.1.0); use Code → Download ZIP on that branch. New releases are added as separate versions while previous downloads remain available. Compatible old nodes remain included with their stable IDs.

## Development and provenance

```sh
python -m pytest
node --test tests/js/*.test.js
```

Release ZIP validation: 1,734 Python tests passed, one historical local-fixture test skipped, and 216 JavaScript tests passed. The supplied template passed graph and paired-reference wiring checks; its four-title change was not GPU-retested.

Tests distinguish state/layout/CPU contracts from UI and GPU image-quality evidence. One historical snapshot test requires a local pre-change fixture and skips when that fixture is absent. The local-only workflow-builder tests are not part of this distribution.

Artwork and the original UI/layout foundation come from [H3 Character Sheet Designer](https://github.com/ukr8b3g-cmyk/H3-Character-Sheet-Designer). This pack uses independent node IDs, routes and DOM namespaces. See [NOTICE.md](NOTICE.md) and `manifest.json` for source provenance, public verification summaries and LF-normalized hashes of the distributed files. Private development records are kept locally, outside the distribution. Preserve upstream notices when redistributing.

Installed-Core interoperability checks use the optional `QWEN_SHEET_TEST_COMFYUI_ROOT` environment variable pointing to your ComfyUI source folder. Without it, those host-specific tests skip; the distribution does not contain machine-specific paths or private source records.

### v1.4.2 validation / 検証範囲

This release adds workflow/documentation fixes and CPU regression coverage. GPU rendering and image quality were not retested for v1.4.2. Earlier GPU records describe v1.4.1 only. 本版は接続・案内の修正とCPU確認です。GPU再試験は行っていません。旧Release・既存画像・旧ノードを保持しています。

CPU validation: **159 passed**, including **32 new regressions**. The new template passed actual installed Core prompt validation (15 API nodes), with CUDA uninitialized and zero GPU submissions. CPU確認は159件成功（追加32件）、実Coreの15ノード入力検証も成功。[v1.4.2 record](verification/release_v142.json).
