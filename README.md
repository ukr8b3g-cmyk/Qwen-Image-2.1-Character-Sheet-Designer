# Qwen Image 2.1 Character Sheet Designer

[English](#english)

## v1.5.6の変更点

- Reference V1.3の衣服設定に **衣服なし／体表を保持** を追加。13面の選択を保存したまま、衣装の前後を除いた11面を生成します。Autoに戻すと衣装の前後も対象に戻ります。
- **プロンプト** タブからビュー別の基本文を編集できます。通常版とTurbo版で使えます。
- Layout Image ONの標準5面では全身ガイドの幅を調整しました。衣服なしの11面では、全身正面と左右の顔の配置を明示し、白い余白で分けるガイドを使います。
- Turbo版でオオカミ参照・seed 42・3424×1280・Layout Image ONを使い、右上の左横顔と右中央の左斜め顔を含む11面を確認しました。全身側面・背面の描画サイズには差が残ります。既存のノードID・解像度設定・配布ワークフロー3件は同じです。[検証記録](verification/release_v156.json)

## v1.5.5の変更点 — ホットフィックス

- 未使用の合成設定でV1.3の通常生成を止めないように修正。合成設定エラーはSheet Assembleで報告し、キャンバス確保前に拒否します。
- 有効な個別生成は、全体概要がサイズ上限を超えてもプレビューを表示します。各画像の生成寸法・保存値は変更しません。
- V1.2／V1.3のGUI接続案内をSheet Encode方式へ修正し、参照不足を日英で表示します。旧V1.1の案内・ノードID・出力順・配布ワークフローは維持しています。
- CPU検証：Python 1,833件成功・過去素材不足1件スキップ、JavaScript 243件成功。再起動後の実プレビューAPIも確認。実画面の表示・保存再読込とGPU生成は今回未検証です。[検証記録](verification/release_v155.json)

## v1.5.4の変更点

- **通常版・Turbo版をLoRA対応テンプレートへ更新**：外部のPower Lora Loader (rgthree)でモデルに適用します。初期状態はLoRA未選択。配置・サブグラフ順序・生成設定は指定のワークフローを維持しています。
- **両版ともSave Image AdvancedでPNG保存**：8-bit／sRGB。保存名は保存ノードで変更できます。通常版・Turbo版には[rgthree-comfy](https://github.com/rgthree/rgthree-comfy)が必要です。
- **配線と実生成を確認**：CPU 1,819件成功・旧素材不足1件スキップ。実ComfyUIのAPI出力と、通常／Turbo各LoRAなし・ありの4生成を確認しました。検証は1参照・1 Seed・1種類のLoRAに限定します。[検証記録](verification/release_v154.json)

## v1.5.3の変更点

- **V1.3の再追加時のUI復元を修正**：ノードを削除してUndoした場合も、合成切替・補助出力メニュー・未接続出力の非表示を復元します。更新監視の重複も防ぎます。
- **既存の操作・保存形式を維持**：生成処理、出力番号、`state_json`、配布ワークフローは変更しません。

JavaScript 233件と関連CPU試験18件が成功。実ComfyUIでも削除→Undoを3回、設定変更、JSON保存・新規読込を確認しました。今回GPU生成は実施していません。[検証記録](verification/ui_readd_fix.json)

## v1.5.2の変更点

- **配布ワークフローを更新**：指定の通常版・Turbo版V1.3と旧V1.2を採用。サブグラフの並び・配置・生成設定を維持し、V1.3は標準Save Image、旧V1.2はSave Image AdvancedでPNG保存します。保存名は保存ノードで直接指定します。
- **未使用の補助出力を非表示**：`filename_suffix`・`sheet_plan`・`view_records`は未接続なら非表示。右クリックの「補助出力を表示」から戻せます。接続済みの出力と出力番号は維持します。
- **日英READMEの要件・モデルリンクを明記**：ComfyUI Core v0.37.0以上。通常モデル・Turboモデル・テキストエンコーダー・VAEのComfy-Org公式ダウンロード先を掲載。旧ノード・既存テンプレート・画像・旧Releaseは引き続き利用できます。

<img width="1543" height="713" alt="{3DB22210-59B7-4161-8A96-29B0211C5E33}" src="https://github.com/user-attachments/assets/785a18e0-fa55-41ab-b12a-d0d98b40f9ac" />


## v1.5.1の変更点

- V1.2の操作と配置を維持。標準はBatch Out OFF・Use Layout Image OFFで、保存ノードは1つです。Batch Out ONでも同じ保存先から各ビューを出力します。
- 合成設定は合成接続時だけ、既存Layout内の「Assembly / 合成」で表示します。プレビューの段を追加せず、生成サイズと合成サイズを分けます。旧ノード・テンプレートは維持します。
- [標準テンプレート](https://github.com/ukr8b3g-cmyk/Qwen-Image-2.1-Character-Sheet-Designer/blob/v1.5.5/workflows/QwenImage21_Character_Sheet_Designer_Reference_V13_template.json)。合成テンプレートは任意です。

## v1.5.0の変更点

- **Reference V1.3・Sheet Assembleを追加**：ビューを個別生成し、ID・枚数・配置計画を検査して1枚のシートへ合成します。生成サイズと合成サイズを別々に指定できます。
- **WebP合成テンプレートを追加**：Sheet Encode経由で参照を揃え、個別画像と合成画像を品質70で保存します。RGB／RGBAに対応し、透明部分は白背景に合成します。
- **足元の参照表現と利用説明を更新**：履物の外形・被覆・開口を維持する指示と中立的な`foot appearance`表現を採用。手・履物の着脱や形状はプロンプト制御のため保証できないことを日英で明記しました。

旧V1／V1.1／V1.2、既存テンプレート、旧Releaseは引き続き利用できます。

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

**Package v1.5.6** — a visual character-sheet designer for ComfyUI and Qwen Image 2.1.

Select views, keep a character consistent with image references, and generate either a sheet or independent images. No LLM, classifier, extra model, or H3 installation is required by this node pack. Model loading, encoding, sampling and saving remain in the workflow.

## 日本語

### ノードとバージョン

パッケージ全体のバージョンは **1.5.6** です。ノードの表示名にあるV1／V1.1／V1.2／V1.3は、互換性を保つためのノード系列名です。最新版は **Qwen 2.1 Sheet Designer Reference V1.3** です。

| 表示名 | 用途 | ノードID |
| --- | --- | --- |
| Qwen 2.1 Sheet Designer Reference V1.3 | 最新版。個別生成に合成計画・ビューIDを追加 | `QwenImage21CharacterSheetDesignerReferenceV13` |
| Qwen 2.1 Sheet Assemble | 個別画像を配置計画に従って合成 | `QwenImage21CharacterSheetAssemble` |
| Qwen 2.1 Sheet Designer Reference V1.2 | 既存6出力を維持。追加参照3枚、部位選択、個別出力、参照計画 | `QwenImage21CharacterSheetDesignerReferenceV12` |
| Qwen 2.1 Sheet Encode | Designerの参照計画に従って画像をCore Encoderへ渡す | `QwenImage21CharacterSheetEncode` |
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

### LoRAの使い方（通常版・Turbo版）

初期状態のままならLoRAなしで生成します。使用する場合は、Qwen Image 2.1に対応した重みを`ComfyUI/models/loras/`へ配置し、Power Lora Loaderで選択・強度を指定してください。適用先はモデルのみで、CLIPは変更しません。接続は`UNETLoader → Power Lora Loader → QwenImage21Cache → Sampler`です。画面上ではサブグラフとの往復接続に見えますが、実行時の依存関係は循環していません。

GPU確認は既存の1種類のLoRA・強度0.5による単独ビューの4枚です。すべてのLoRAや画角の正確さ、参照の完全一致、品質向上を保証するものではありません。旧V1.2テンプレートとノード本体の生成処理は変更していません。

### システム要件

- **ComfyUI Core v0.37.0以上**。Qwen Image 2.1の初対応版です（2026年9月21日公開）。不具合修正を含む最新の安定版を推奨します。[公式Release](https://github.com/Comfy-Org/ComfyUI/releases/tag/v0.37.0)。
- Qwen Image 2.1のモデル、Qwen3-VLテキストエンコーダー、対応VAEが必要です。モデルは同梱しません。
- 配布テンプレート3本はSave Image AdvancedでPNG保存します。
- 通常版・Turbo版には[rgthree-comfy](https://github.com/rgthree/rgthree-comfy)のPower Lora Loaderが必要です。LoRA重みは任意で、同梱しません。
- 今回の実生成確認はCore v0.41.0で実施しました。過去のUI確認環境はCore v0.40.0／Frontend 1.55.17です。初対応版で全機能を確認したという意味ではありません。

### 公式モデルのダウンロード

[Comfy-Org公式配布](https://huggingface.co/Comfy-Org/Qwen-Image-2.1)の、テンプレートで使用しているファイルです。通常版は通常モデル、Turbo版はTurboモデルを選び、同じテキストエンコーダーとVAEを使用します。

| 種類 | ファイルの直接ダウンロード | 配置先 |
| --- | --- | --- |
| 通常モデル / Normal model | [qwen_image_2.1_int8_convrot.safetensors](https://huggingface.co/Comfy-Org/Qwen-Image-2.1/resolve/main/diffusion_models/qwen_image_2.1_int8_convrot.safetensors) | `ComfyUI/models/diffusion_models/` |
| テキストエンコーダー / Text encoder | [qwen3vl_8b_int8_convrot.safetensors](https://huggingface.co/Comfy-Org/Qwen-Image-2.1/resolve/main/text_encoders/qwen3vl_8b_int8_convrot.safetensors) | `ComfyUI/models/text_encoders/` |
| VAE | [qwen_image_2.1_vae_bf16.safetensors](https://huggingface.co/Comfy-Org/Qwen-Image-2.1/resolve/main/vae/qwen_image_2.1_vae_bf16.safetensors) | `ComfyUI/models/vae/` |
| Turboモデル / Turbo model | [qwen_image_2.1_turbo_int8_convrot.safetensors](https://huggingface.co/Comfy-Org/Qwen-Image-2.1/resolve/main/diffusion_models/qwen_image_2.1_turbo_int8_convrot.safetensors) | `ComfyUI/models/diffusion_models/` |

配置後はLoaderで自分のファイルを選択してください。テンプレートのモデル名に含まれる`qwen\`などのサブフォルダー名も、実際の配置先に合わせて選び直します。Turboテンプレートは8ステップ・CFG 1です。モデル重みは同梱しません。

### テンプレート

用途に合わせて、workflowsフォルダーの3本から選んでください。

- [通常版V1.3](workflows/QwenImage21_Character_Sheet_Designer_Reference_v1.5.4_template.json)。通常モデルを使用し、30ステップ・CFG 1・Euler／simpleで生成します。
- [Turbo版V1.3](workflows/QwenImage21_Character_Sheet_Designer_Reference_v1.5.4_template_Turbo.json)。Turboモデル向けの8ステップManual Sigmas・CFG 1・Eulerで生成します。

- [旧版Reference V1.2](workflows/QwenImage21_Character_Sheet_Designer_Reference_V12_template.json)。Coreへの直接接続を使う既存構成向けです。部位専用参照や参照範囲の指定には、Sheet Encode経由の通常版・Turbo版を使ってください。

Character Imageに自分の画像を選び、使う追加参照だけを有効にしてください。通常版のノートにはWebPとありますが、実際の保存ノードは3本ともSave Image AdvancedでPNGを保存します。

### 旧版のダウンロードと互換性

旧V1やV1.2 Sheet Encode版は [v1.5.5タグのワークフロー](https://github.com/ukr8b3g-cmyk/Qwen-Image-2.1-Character-Sheet-Designer/tree/v1.5.5/workflows) から取得できます。既存の保存済みワークフローは引き続き読み込めます。

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

手や履物の選択は**プロンプトによる生成指示**です。初期状態ではLoRAは未選択です。LoRAを追加しても、グローブや靴の着用・取り外し、形状、左右の再現を保証するものではありません。参照画像やSeedによっては選択に従わず、再生成が必要な場合があります。指定は必要最小限にし、まずSeedを変えて比較してください。長く複雑な指示を重ねると、指示同士が干渉して汎用性を損なう場合があります。

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

### 個別生成からシートへ合成（V1.3）

専用の合成テンプレートは [v1.5.5タグ](https://github.com/ukr8b3g-cmyk/Qwen-Image-2.1-Character-Sheet-Designer/blob/v1.5.5/workflows/QwenImage21_Character_Sheet_Designer_Reference_V13_Assemble_template.json) から取得できます。V1.3の先頭6出力はV1.2と同じで、追加の`sheet_plan`・`view_records`とデコードしたIMAGEをSheet Assembleへ接続します。参照画像はDesignerとSheet Encodeの同名入力へ接続します。WebP保存には[Save WEBP Meta](https://github.com/ukr8b3g-cmyk/ComfyUI-save-webp-meta-node)が必要です。

**Batch Out ON・latent batch_size=1**で使用してください。Output sizeは各ビューの生成サイズ、Sheet canvas mode / width / heightは合成先のサイズです。合成Autoは選択全体を配置し、合成Manualは入力した幅×高さを固定します。合成を接続すると既存Layout内の「Assembly / 合成」で合成サイズと配置を確認できます。通常のLayout表示の大きさは維持します。

Sheet Assembleは元のリスト長、1ビュー1画像、ビューID、計画ハッシュ、寸法を検査します。欠損・重複・計画不一致はエラーにし、短いリストを末尾画像で補いません。画像はCPUで縦横比を保って白い枠内へ収め、RGBAの透明部分を白背景へ合成します。切り抜き・引き伸ばし・反転は行いません。合成上限は16,777,216画素です。

配置と宣言されたID対応は検査できますが、生成画像内の向き・人数・人物の高さ・足裏の位置や、上流ですでに複製・誤ラベルされた内容は判定しません。

### 参照の範囲と画質

Sheet Encodeの`reference_regions`で参照範囲を明示できます。空の`{}`は参照全体を使い、画像別・ビュー別の正規化矩形で入力範囲を指定できます。自動分類・自動切り取りはしません。[範囲指定の説明](docs/REFERENCE_REGIONS_JA.md)を参照してください。Encoderの`resolution`は参照のリサンプル量で、出力Width/Heightとは別です。

Qwenで作成した参照を編集する場合、参照作成時とは異なる編集Seedを選び、その編集Seedを比較中は固定する方法を確認しました。強い斑点が改善した局所試験ですが、すべての荒れの原因や解決を保証しません。WebP品質70は保存容量の設定で、生成された画素の不整合を直す設定ではありません。

### v1.5.2の確認範囲

今回の変更はフロントエンドの補助出力表示・配布ワークフロー・文書です。Python **1,813件成功・1件スキップ**（旧ローカル素材未提供）、JavaScript **226件成功**。6テンプレートを構造検査し、指定の3本を実ComfyUIで読み込み、実際のAPI出力のSeed・Steps・CFG・モデル名を確認しました。[今回の検証記録](verification/release_v152.json)。以前のGPU検証は下記v1.5.1の記録であり、今回の配布3本でGPU生成を再実行した結果ではありません。

### v1.5.1の確認範囲

Python **1,815件成功・1件スキップ**（旧ローカル比較素材が未提供）、JavaScript **222件成功**。7テンプレート、実Core CPU、実ComfyUI画面のUndo／Redo・保存・再読込を確認しました。GPUはAuto／Manual・Batch Out・Guideの5条件10枚を確認し、個別5枚は更新前と画素が一致しました。[検証記録](verification/release_v151.json)。

Manualの縦長サイズでは顔画像の余白が大きくなるため、個別出力の基本はAutoを推奨します。Guideは厳密な配置を保証せず、手・履物のプロンプト制御にも既存の限界があります。GPU確認は1参照・1Seedの限定試験です。

### v1.5.0の確認範囲

配布対象からPython **1,811件成功・1件スキップ**、JavaScript **216件成功**。実Core CPUで18ノードの入力検証、リスト処理、欠損拒否とGuide OFFを確認しました。GPUでは5ビューの個別生成＋1536×864合成を確認。足元の呼称比較は10組20枚、新しい手・足の参照5枚による比較は15条件です。

追加15条件では着用状態が13条件で一致し、グローブ除去・サンダル除去の2条件は不一致。足指・開口・着用表現にも課題が残ります。この件数は限定試験の結果であり、全画像の成功率ではありません。実ブラウザーでのUI保存・再読込は今回再検証していません。[GPU要約](verification/gpu_summary_v150.json)・[配布検証](verification/release_v150.json)。

### v1.4.1の変更と確認範囲

グローブを実際に着用する指示、左右一組の履物の整合、靴ありの明確な被覆、Autoでも人物が着た衣装を描く指示を改善しました。グローブの形・指の開きは参照／部位文に従い、未指定時だけ全指被覆を既定とします。旧ノードID・既存の保存状態・出力・配置計算を維持しています。

2026-10-13の関連Pythonテストは578件成功。実CoreのCPU確認では候補8グラフと最終Auto4グラフを検証し、CUDAを初期化していません。事前生成文のGPU比較は合計12枚です。初回8枚のうち6枚合格・Auto2枚失敗で、そのAuto文は不採用。裸足／ブーツ×2Seedの再試験4枚で被覆を確認しました。変更していない6条件と合わせて採用する生成文10条件を確認しています。

その後、再起動済みの実Designerで衣装Auto・Gloves・Footwear Auto・Manualシートの4条件を実行しました。4枚の寸法・実行文・保存設定を照合し、デコード後の画素は先に確認した候補と4/4一致しました。検証は参照3素材・編集2Seedに限定されます。ブーツ上端の収まり、足詳細の下腿、向き・細かな解剖形状には改善余地があります。すべての画像・選択組合せのGPU合格を示すものではありません。

配布ZIPの再検証はPython 1,734件成功・1件スキップ、JavaScript 216件成功です。今回指定されたテンプレートは接続整合性と名前・設定の保存を確認しました。このタイトル変更でGPU生成は繰り返していません。

記録は[最新GPU検証](verification/gpu_summary_v141.json)、[配布検証](verification/release_v141.json)にあります。公開対象はノード本体・必須UI素材・指定ワークフロー・README・利用説明と検証要約です。作業用仕様書、検証用画像、ローカル構成付き詳細記録と追加テストワークフローはローカルに保持し、配布しません。

## English

### What's new in v1.5.6

- Reference V1.3 adds **No clothing · natural body surface**. A 13-view selection remains saved while the sheet generates 11 views without the outfit front and back. Switch to Auto to restore the outfit views.
- Edit individual view prompts in the **Prompts** tab in both Normal and Turbo.
- With Layout Image on, the standard five-view guide gives full-body views more width. The clothing-free 11-view layout uses white gaps and assigns the frontal body and portrait angles explicitly.
- A Turbo GPU run with the wolf reference, seed 42, and a 3424 × 1280 canvas confirmed 11 views, including the upper-right left profile and middle-right left three-quarter portrait. Full-body side and rear height can still vary. Node IDs, size settings and all three distributed workflows are unchanged. [Verification](verification/release_v156.json)

### What's new in v1.5.5 — Hotfix

- Unused assembly settings no longer block V1.3 generation. Sheet Assemble reports invalid assembly plans and rejects them before allocating its canvas.
- Valid individual outputs retain their previews even when the whole-selection overview exceeds the size limit. Per-image dimensions and saved values are unchanged.
- V1.2/V1.3 GUI instructions now describe Sheet Encode, and missing references are reported in English/Japanese. Legacy V1.1 guidance, node IDs, output order and distributed workflows are preserved.
- CPU validation: 1,833 Python passes, one unavailable historical-fixture skip, and 243 JavaScript passes. The restarted ComfyUI preview API was also checked. Browser UI/save-reload and GPU generation were not retested. [Verification record](verification/release_v155.json)

### What's new in v1.5.4

- **Updated normal/Turbo templates with optional model-only LoRA loading** through Power Lora Loader (rgthree). No LoRA is selected initially. The supplied layout, subgraph ordering and generation settings are preserved.
- **Save Image Advanced PNG output in both templates**, using 8-bit sRGB. Edit filenames in the save node. These two templates require [rgthree-comfy](https://github.com/rgthree/rgthree-comfy).
- **Validated wiring and inference**: 1,819 CPU passes and one unavailable historical-fixture skip; actual ComfyUI API exports and four normal/Turbo LoRA-off/on generations. GPU evidence is limited to one reference, one seed and one adapter. [Verification record](verification/release_v154.json)


### What's new in v1.5.3

- **Restore V1.3 UI after node re-addition**: deleting a node and undoing now restores the assembly toggle, auxiliary-output menu, and hiding of unconnected auxiliary outputs. Update observers are not duplicated.
- **Keep existing behavior and serialization**: generation code, output indexes, `state_json`, and distributed workflows are unchanged.

All 233 JavaScript tests and 18 relevant CPU tests passed. Actual ComfyUI checks covered three delete/undo cycles, setting changes, JSON export, and fresh loading. No GPU generation was run for this fix. [Verification record](verification/ui_readd_fix.json)

### What's new in v1.5.2

- **Updated distribution workflows**: adopted the supplied normal/Turbo V1.3 and legacy V1.2 templates, preserving subgraph ordering, positions and generation settings. V1.3 uses standard Save Image; legacy V1.2 keeps Save Image Advanced. Both save PNG, with filenames set directly in the save node.
- **Hidden unused auxiliary outputs**: unconnected `filename_suffix`, `sheet_plan` and `view_records` are hidden. Use “Show auxiliary outputs” from the context menu to reveal them. Connected ports and output indexes stay intact.
- **Documented requirements and model links in both languages**: ComfyUI Core v0.37.0 or higher, with official Comfy-Org downloads for the normal/Turbo models, text encoder and VAE. Compatible nodes, existing templates, artwork and previous releases remain available.

### What's new in v1.5.1

- **Retained the V1.2 interface** with Batch Out and Use Layout Image defaulting OFF. The standard template uses one save node for either a sheet or separate views.
- **Moved optional assembly controls into the existing Layout area**, preserving preview size without another preview row. Generation and assembly sizes remain independent.
- **Added the one-save standard template**. Legacy nodes, templates, artwork and previous releases remain available.

### What's new in v1.5.0

- **Added Reference V1.3 and Sheet Assemble** to combine independently generated views after validating view IDs, list lengths and the sheet plan. Generation dimensions and the final sheet canvas are separate.
- **Added a WebP assembly template** using Sheet Encode, with individual and assembled images saved at quality 70. RGB/RGBA images are supported; transparency is composited onto white.
- **Updated foot-reference wording and usage guidance** to preserve silhouette, coverage and existing openings, with neutral `foot appearance` labels. Bilingual guidance explains that prompt-only hand/footwear controls do not guarantee removal, addition or exact shapes.

Legacy V1/V1.1/V1.2 nodes, existing templates and previous releases remain available.

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

Package **v1.5.6** includes **Reference V1.3**, **Sheet Assemble**, **Sheet Encode**, and compatible **V1/V1.1/V1.2** nodes. Node display versions identify compatible node families; they are not the package release number. No H3 installation or additional inference model is required by this pack.

Install this folder in `ComfyUI/custom_nodes`, or use the release ZIP. After your active work finishes, restart the ComfyUI backend and reload the browser. Qwen 2.1-capable ComfyUI Core, model weights, text encoder and VAE are required. Choose installed model files and your own images in the workflow.

### Optional LoRA loading (normal/Turbo)

Leave the loader empty for generation without a LoRA. To enable one, place Qwen Image 2.1-compatible weights in `ComfyUI/models/loras/`, then select the adapter and strength in Power Lora Loader. This is model-only loading; CLIP is unchanged. The execution path is `UNETLoader → Power Lora Loader → QwenImage21Cache → Sampler`. The visual connection returns through the generator subgraph, but the expanded execution graph is acyclic.

GPU checks covered four single-view outputs using one existing adapter at strength 0.5. They do not establish compatibility with every LoRA, exact camera/identity reproduction, or improved image quality. Legacy V1.2 and the node pack's generation implementation are unchanged.

### System requirements

- **ComfyUI Core v0.37.0 or higher**: the first stable release with Qwen Image 2.1 support, published September 21, 2026. Use the latest stable release for subsequent fixes. [Official release](https://github.com/Comfy-Org/ComfyUI/releases/tag/v0.37.0).
- Qwen Image 2.1 model weights, Qwen3-VL text encoder and the matching VAE are required and are not bundled.
- All three current templates use **Save Image Advanced (PNG)**.
- Normal/Turbo require Power Lora Loader from [rgthree-comfy](https://github.com/rgthree/rgthree-comfy). LoRA weights are optional and are not bundled.
- This release was tested on Core v0.41.0. Earlier UI checks used Core v0.40.0 / Frontend 1.55.17; this does not claim all-feature validation on the initial supported release.

### Official model downloads

These files are hosted by [Comfy-Org](https://huggingface.co/Comfy-Org/Qwen-Image-2.1) and match the template selections. Use the normal model for the normal workflow, or the Turbo model for the Turbo workflow, with the same text encoder and VAE.

| Component | Direct file download | Destination |
| --- | --- | --- |
| 通常モデル / Normal model | [qwen_image_2.1_int8_convrot.safetensors](https://huggingface.co/Comfy-Org/Qwen-Image-2.1/resolve/main/diffusion_models/qwen_image_2.1_int8_convrot.safetensors) | `ComfyUI/models/diffusion_models/` |
| テキストエンコーダー / Text encoder | [qwen3vl_8b_int8_convrot.safetensors](https://huggingface.co/Comfy-Org/Qwen-Image-2.1/resolve/main/text_encoders/qwen3vl_8b_int8_convrot.safetensors) | `ComfyUI/models/text_encoders/` |
| VAE | [qwen_image_2.1_vae_bf16.safetensors](https://huggingface.co/Comfy-Org/Qwen-Image-2.1/resolve/main/vae/qwen_image_2.1_vae_bf16.safetensors) | `ComfyUI/models/vae/` |
| Turboモデル / Turbo model | [qwen_image_2.1_turbo_int8_convrot.safetensors](https://huggingface.co/Comfy-Org/Qwen-Image-2.1/resolve/main/diffusion_models/qwen_image_2.1_turbo_int8_convrot.safetensors) | `ComfyUI/models/diffusion_models/` |

Select your installed files in the Loaders. Reselect any subfolder prefix such as `qwen\` to match your actual model path. The Turbo template uses 8 steps and CFG 1. Model weights are not bundled.

### Workflows

The current workflow folder contains three templates.

- [Normal V1.3](workflows/QwenImage21_Character_Sheet_Designer_Reference_v1.5.4_template.json) uses the normal model with 30 steps, CFG 1, and Euler / simple.
- [Turbo V1.3](workflows/QwenImage21_Character_Sheet_Designer_Reference_v1.5.4_template_Turbo.json) uses the Turbo model with an eight-step Manual Sigmas schedule, CFG 1, and Euler.

- [Legacy Reference V1.2](workflows/QwenImage21_Character_Sheet_Designer_Reference_V12_template.json) uses direct Core wiring. Use the Sheet Encode path in Normal or Turbo for dedicated part references, reference crops, and per-view reference routing.

Set the Character Image and enable any optional references you need. All three templates are wired to Save Image Advanced for PNG output. The note inside Normal describes WebP output from its earlier setup. The [v1.5.5 tag](https://github.com/ukr8b3g-cmyk/Qwen-Image-2.1-Character-Sheet-Designer/tree/v1.5.5/workflows) also provides the older V1 and V1.2 Sheet Encode templates. Existing saved workflows remain compatible.

Select from 13 view cards. The compact controls beneath clothing, hands and footwear choose **Auto / pants / skirt–robe**, **Auto / bare / gloves**, and **Auto / footwear on / footwear off**. All default to Auto, meaning follow references. They are prompts, not image classification. Footwear on leaves shoe type open; footwear off can preserve socks/tights. Use part text for specific details. Choices also apply to naturally visible parts in body views. Worn clothing and garment-only views are distinct.

Hand and footwear choices are **generation instructions in the prompt**. No LoRA is selected by default. Adding a LoRA does not guarantee that gloves or footwear will be added, removed, shaped or paired as requested. Results depend on the reference image and seed; another generation may be needed. Keep directives minimal and compare another seed first. Long, complex instructions can interfere with each other and reduce generality.

**Batch Out OFF** produces one arranged sheet. **Batch Out ON** independently generates each selected view in card order. Auto chooses sizes by view type; at panel height 1120, busts use 1024×1024, body/clothing 768×1344, hands/footwear 1184×864. **Manual width×height applies to every separate image when Batch Out is ON**, or to the whole sheet when OFF. The preview follows each output aspect ratio. These defaults are not universal quality optima.

The six V1.2 outputs are aligned ComfyUI lists: prompt, width, height, layout_image, filename_suffix, reference_plan. Connect width/height to EmptyLatentImage; keep latent batch_size 1 unless you need multiple samples per view. The supplied seed is shared across views. List execution may finish sampling all views before saving. Errors do not trigger automatic retries. Save nodes determine format, location and compression.

Guide OFF bypasses guide creation. Guide ON is a model reference, not hard masking or deterministic compositing. Sheet Encode supports optional explicit per-image/per-view `reference_regions`; `{}` uses complete sources. See [reference region documentation](docs/REFERENCE_REGIONS_JA.md). Encoder resolution resamples references and does not set output dimensions.

v1.4.1 improves worn gloves, consistent paired footwear, identifiable footwear coverage, and clothing-on-wearer instructions in Auto. IDs, old nodes, saved states, geometry and output contracts remain compatible. Relevant repair tests passed (578 Python); actual Core CPU checks and GPU acceptance are recorded separately. Ten final frozen-prompt conditions were checked, then four actual Designer cases matched their accepted candidate pixels exactly. GPU evidence is limited to three reference material sets and two edit seeds. Boot-top framing, lower-leg remnants and fine anatomy still need care; it is not all-image or all-combination acceptance. See [GPU record](verification/gpu_summary_v141.json) and [release validation](verification/release_v141.json).

Previous public package 0.1.0 is preserved on [legacy-v0.1.0](https://github.com/ukr8b3g-cmyk/Qwen-Image-2.1-Character-Sheet-Designer/tree/legacy-v0.1.0); use Code → Download ZIP on that branch. New releases are added as separate versions while previous downloads remain available. Compatible old nodes remain included with their stable IDs.


### Assemble independently generated views (V1.3)

The dedicated assembly template is available from the [v1.5.5 tag](https://github.com/ukr8b3g-cmyk/Qwen-Image-2.1-Character-Sheet-Designer/blob/v1.5.5/workflows/QwenImage21_Character_Sheet_Designer_Reference_V13_Assemble_template.json). Connect decoded IMAGE plus V1.3's sheet_plan and view_records to Sheet Assemble. The first six outputs preserve V1.2's contract. Reference images go to matching Designer and Sheet Encode inputs. This template requires [Save WEBP Meta](https://github.com/ukr8b3g-cmyk/ComfyUI-save-webp-meta-node).

Use **Batch Out ON and latent batch_size=1**. Output size controls each generated image; Sheet canvas mode / width / height controls the final sheet. Sheet Auto packs the complete selection; Sheet Manual fixes the final dimensions. With assembly connected, “Assembly” in the existing Layout area shows canvas settings and destination panel bounds without adding another preview row.

Sheet Assemble validates original list lengths, one image per view, IDs, plan hashes and dimensions. Missing, duplicate or mismatched records fail instead of repeating the last image. CPU composition preserves aspect ratio on white, composites RGBA transparency onto white, and neither crops, stretches nor mirrors images. The maximum canvas is 16,777,216 pixels. It verifies declared placement, not generated camera, figure count, body scale, sole alignment or already duplicated/mislabeled upstream content.

### v1.5.2 validation

This update changes auxiliary-output visibility, distributed workflows and documentation. **1,813 Python passes, one unavailable historical-fixture skip; 226 JavaScript passes**. Six workflows passed structure checks. All three supplied templates were loaded in actual ComfyUI, and their API exports confirmed seeds, steps, CFG and model selections. See the [current verification record](verification/release_v152.json). GPU results below belong to v1.5.1; they are not new GPU runs of these three distribution workflows.

### v1.5.1 validation

**1,815 Python passes, one unavailable historical local-fixture skip, and 222 JavaScript passes**. Seven templates, actual Core CPU behavior, and actual ComfyUI Undo/Redo, export and reload were verified. Five GPU conditions produced ten images covering Auto/Manual, Batch Out and Guide; five separate views matched pre-update pixels exactly. See [verification record](verification/release_v151.json).

Manual portrait dimensions can leave large margins around busts; Auto is the default recommendation for individual views. Guide does not guarantee exact geometry, and prompt-only hand/footwear control retains its existing limits. GPU evidence is limited to one reference and one seed.

### v1.5.0 validation

The staged distribution passed **1,811 Python tests (one historical local-fixture skip) and 216 JavaScript tests**. Actual Core CPU checks covered the 18-node graph, list dispatch, missing-image rejection and Guide OFF. GPU checks included five independent views plus a 1536×864 assembly, ten foot-label comparison pairs (20 images), and 15 conditions using five new hand/foot references.

Coverage matched the requested state in 13 holdout conditions; glove removal and sandal removal failed to follow the selected state. Toe definition, openings and worn-glove depiction still varied. These are limited-sample observations, not a success-rate estimate. Actual browser UI save/reload was not revalidated. See [GPU summary](verification/gpu_summary_v150.json) and [release checks](verification/release_v150.json).

## Development and provenance

```sh
python -m pytest
node --test tests/js/*.test.js
```

v1.5.0 staged-distribution validation: **1,811 Python tests passed, one historical local-fixture test skipped, and 216 JavaScript tests passed**. Actual Core CPU checks covered the 18-node assembly graph and list dispatch. Browser UI save/reload was not revalidated; static JavaScript tests and backend execution are separate evidence.

Tests distinguish state/layout/CPU contracts from UI and GPU image-quality evidence. One historical snapshot test requires a local pre-change fixture and skips when that fixture is absent. The local-only workflow-builder tests are not part of this distribution.

Artwork and the original UI/layout foundation come from [H3 Character Sheet Designer](https://github.com/ukr8b3g-cmyk/H3-Character-Sheet-Designer). This pack uses independent node IDs, routes and DOM namespaces. See [NOTICE.md](NOTICE.md) and `manifest.json` for source provenance, public verification summaries and LF-normalized hashes of the distributed files. Private development records are kept locally, outside the distribution. Preserve upstream notices when redistributing.

Installed-Core interoperability checks use the optional `QWEN_SHEET_TEST_COMFYUI_ROOT` environment variable pointing to your ComfyUI source folder. Without it, those host-specific tests skip; the distribution does not contain machine-specific paths or private source records.

### v1.4.2 validation / 検証範囲

This release adds workflow/documentation fixes and CPU regression coverage. GPU rendering and image quality were not retested for v1.4.2. Earlier GPU records describe v1.4.1 only. 本版は接続・案内の修正とCPU確認です。GPU再試験は行っていません。旧Release・既存画像・旧ノードを保持しています。

CPU validation: **159 passed**, including **32 new regressions**. The new template passed actual installed Core prompt validation (15 API nodes), with CUDA uninitialized and zero GPU submissions. CPU確認は159件成功（追加32件）、実Coreの15ノード入力検証も成功。[v1.4.2 record](verification/release_v142.json).

## License / ライセンス

Original code and documentation, plus the seven bundled PNGs and SVG fallback artwork explicitly listed in [NOTICE.md](NOTICE.md), are available under the [MIT License](LICENSE) to the extent ukr8b3g-cmyk holds the applicable rights. The maintainer confirmed that the listed artwork was created using GPT and authorized its redistribution under MIT. Third-party material retains its original terms, including the GPL-licensed ComfyUI test excerpt. Other screenshots, model weights, user-provided references and user-generated outputs are outside this grant. ComfyUI, models, dependencies and external services retain their own terms.

ukr8b3g-cmykが権利を有する自作コード・文書と、[NOTICE.md](NOTICE.md)に明記した同梱PNG 7点・SVGフォールバック素材に[MIT License](LICENSE)を適用します。管理者は対象素材がGPTで作成されたことと、MIT条件での再配布を許諾することを確認しています。第三者由来の素材には元の条件を維持し、ComfyUI由来のテスト抜粋はGPLのままです。その他のスクリーンショット、モデル重み、利用者の参照素材・生成物はこの許諾に含めません。ComfyUI・モデル・依存先・外部サービスの条件も別途適用されます。
