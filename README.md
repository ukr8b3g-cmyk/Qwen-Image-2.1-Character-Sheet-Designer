[English](#english)

# Qwen Image 2.1 Character Sheet Designer
<img width="1770" height="742" alt="{AC046BB6-4485-4305-9F8A-5EF5CC7C107F}" src="https://github.com/user-attachments/assets/e6889eeb-53fc-458e-a1ab-cdeebf1a6728" />

<a id="japanese"></a>
**選択したビューだけのQwen向けプロンプトとレイアウト画像を出力します。胸像・全身・手足の詳細を区別し、ノード内で生成プロンプトを確認できます。厳密な生成配置・向きの一致は保証しません。**

人物参照1枚から静止キャラクターシートを作るための、ComfyUI用プロンプト・レイアウト作成ノードです。H3 Character Sheet Designer の7ビュー、8部位入力、Auto／Manual寸法、保存・Undoの操作を固定リビジョンから再利用しています。

**同梱テンプレートではLoRAを使用していません。** 人物の画像参照、マネキンのレイアウト画像、ノードが生成する自然言語プロンプトをQwen Image 2.1へ渡して生成します。配置・ビュー・部位・スタイルをプロンプティングで指定する構成で、人物専用LoRAの学習は必要ありません。参照画像の人物・衣装を維持しながら、選択したビューを描くように指示します。

このパッケージは **QwenImage21CharacterSheetDesigner のみ登録**します。H3のインストールやPythonパッケージに依存せず、既存H3のノードID・ルート・ワークフローを変更しません。モデルのロード、画像読み込み、サンプリング、保存はワークフローのCoreノードが担当します。

## インストール

### Gitでインストール（clone）

Gitを用意し、`<ComfyUIフォルダー>` を使用中のComfyUIの場所に置き換えて実行します。

```sh
cd "<ComfyUIフォルダー>/custom_nodes"
git clone https://github.com/ukr8b3g-cmyk/Qwen-Image-2.1-Character-Sheet-Designer.git
```

導入後はComfyUIを再起動し、ブラウザーを再読込します。

### ZIPでインストール

ZIP内の `Qwen-Image-2.1-Character-Sheet-Designer` フォルダーを `ComfyUI/custom_nodes/` 直下へ置き、ComfyUIを再起動してブラウザーを再読込します。同じQwen版を複数フォルダーに配置しないでください。

### 更新（pull）

cloneで導入したフォルダー内で実行します。

```sh
cd "<ComfyUIフォルダー>/custom_nodes/Qwen-Image-2.1-Character-Sheet-Designer"
git pull --ff-only
```

更新後はComfyUIを再起動し、ブラウザーを再読込します。ローカル変更がある場合は、先にコミットまたは退避してください。ZIPで導入した場合は新しいZIPで更新します。

### 開発者向け：変更を公開（push）

`push` は自分の変更をGitHubへ送る操作です。通常のインストール・更新には不要で、送信先への書き込み権限が必要です。READMEを編集した場合の例：

```sh
git status
git add README.md
git commit -m "Update README"
git push origin main
```

この例はリポジトリのフォルダー内で実行します。他のファイルを変更した場合は、`git add` にそのファイルを指定します。フォークを使う場合は、`origin` を自分のフォークに設定します。

### 必要な環境

実行用の追加pip/npm依存関係はありません。プレビューAPIはComfyUIに含まれるaiohttpを使用します。モデルや外部LLMの自動取得・実行はありません。

必要なCore機能は `TextEncodeQwenImage21`、`QwenImage21Cache`、標準ローダー・KSampler・VAEDecodeです。テンプレートでは `SaveImageAdvanced` を使います。この保存ノードがない環境では標準 `SaveImage` に差し替えてください。実環境でノード登録と出力寸法を確認してください。

## 使い方

ノード名は **Qwen Image 2.1 Character Sheet Designer**、カテゴリは `Qwen/CharacterSheet` です。

1. `workflows/QwenImage21_Character_Sheet_Designer.json` を読み込みます。
2. `LoadImage` で実在する人物参照を選び、生成用サブグラフのモデル設定で所持しているQwen 2.1モデルを選択します。
3. Designerのビュー、サイズ、必要な部位指定を設定して生成します。

```text
Designer.prompt ─────────── TextEncodeQwenImage21.prompt
Designer.layout_image ──── TextEncodeQwenImage21.images.image_1
LoadImage.IMAGE ─────────── TextEncodeQwenImage21.images.image_2
                                  │ positive / negative
Designer.width / height           ↓
          └─ EmptyLatentImage ── KSampler ── VAEDecode ── SaveImageAdvanced
Designer.prompt ─────────── PreviewAny（サブグラフ内）
```

出力は `prompt: STRING`、`width: INT`、`height: INT`、`layout_image: IMAGE` の4つです。既存3出力の順序と `state_json` の保存形式は維持します。`layout_image` は画面と同じ配置計算・マネキン素材から作る白背景のRGB画像で、幅・高さはDesignerの指定と一致します。標準PreviewImageやSaveImageへ接続できます。

同梱workflowは `use_layout_image=ON` です。プロンプトは `<image1>` を配置・大きさ・向き、`<image2>` を人物・衣装・画風として扱います。座標JSONと重複説明を除き、各ビューと部位指定を一度ずつ記述します。人物参照1枚だけの既存workflowでは既定のOFFを使い、人物を `images.image_1` へ接続します。ON/OFFは独立したBOOLEAN入力として保存されます。

`layout_image` とノード内プレビューは、選択した各ビューを黒い長方形の枠で囲みます。配置参照ONでは、この黒枠を完成画像に残し、枠内の灰色マネキンだけを人物へ置き換える編集指示を生成します。枠の位置・寸法、各マネキンの大きさ・向き・切り取り範囲を保持し、顔・胸は頭・首・肩・胸上部だけの胸像とします。定型文は一段落にまとめ、部位指定の原文と改行は保持します。公式の編集指針と検証条件は [docs/LAYOUT_REFERENCE_JA.md](docs/LAYOUT_REFERENCE_JA.md) を参照してください。

### ビューと部位

正面の顔・胸、左横顔・胸、全身正面、全身左側面、全身背面、両手詳細、両足／履物詳細の7ビューです。最低1ビューを選びます。

新規ノードは「標準5ビュー」（顔・胸、左横顔・胸、全身正面、全身左側面、全身背面）、Auto基準高1120、スタイル指定なしです。「基本4面」は左横顔・胸を省いた構成で、プリセットから切り替えられます。初期ノードサイズは添付ワークフローと同じ870×1100です。保存済みのビュー・スタイル選択は初期値へ置き換えません。

各カードのON/OFFは生成promptとlayout_imageの両方へ反映されます。全ONなら胸像2図・全身3図・手足の詳細2図、部分選択ならその構成と図数だけを指定します。全身1図では複数図の整列指示を出しません。「生成プロンプト」を開くと、現在のチェック状態とuse_layout_image設定に対応した出力文字列を確認できます。取得中・失敗時には古い文字列を現在の出力として表示しません。

部位は頭・髪、顔、上半身の服、背面の服、下半身、手・手袋、足・履物、全体・その他の8項目です。入力は自動翻訳せず原文を保持します。手・足の詳細をOFFにしても、手袋や靴の指定は全身に適用されます。背面柄は背面の衣服表面に限定し、顔を見せるための振り向きは要求しません。

ビューや部位指定は即時保存です。**数値の手入力はEnterまたはフォーカスを外したときに確定**します。入力途中・不正な数値は保存やQueueに入りません。表示される注意を確認して確定してください。プレビューの遅延・失敗は保存値を巻き戻しません。API失敗時もraw `state_json` 編集欄を開けます。

UI言語はComfyUIの `Comfy.Locale` が `ja` 系なら日本語、それ以外は英語です。生成用の定型文は英語です。

### スタイル

「部位指定」の右の「スタイル」タブで、指定なし（既定）・アニメ・フォト（写真）・写実（絵画）・写実アニメ・油彩・水彩・ガッシュ・色鉛筆・3D CGから1つを選びます。選択中はタブ外にスタイル名と解除ボタンを表示します。写実アニメは参照の顔立ち・体格に、アニメの線と立体的な陰影を指定します。

指定なしでは従来のプロンプトを変更しません。選択時は参照画風の維持指示を置き換え、描画方法だけを全ビューへ共通指定します。人物・衣装・既存小物・色・柄と配置は保持し、明示された部位指定を尊重します。各スタイルは独自のプロンプト候補で、追加物や人物の変化を完全に防ぐものではありません。

選択は独立したoptional COMBO入力 `style` として保存され、Undoに対応します。既存のstate_json v1/v2と出力4端子は維持します。更新後はComfyUIを再起動し、ブラウザーを再読込してください。

### 保存形式

H3と同じschema v1/v2を受理します。v1を読み込むだけでは移行せず、実際に部位を編集したときだけv2へ進みます。`state_json` に新しいキーは追加しません。

64KiBの厳密JSON、32以上の32倍数、Core MAX_RESOLUTION、部位ごと1000 UTF-16単位を検証します。未知キー、重複キー、無効なUnicode、数値文字列、小数、真偽値、NaN/Infinityを拒否します。不正データを初期値へ勝手に置換しません。

### サイズ

Autoは基準高を保って配置を算出し、両軸を32の倍数へ切り上げます。Manualは指定キャンバスに全体を縦横比維持で収め、ビュー変更でも寸法を変えません。高解像度を自動縮小しません。

| 設定 | 出力 |
|---|---:|
| 新規ノード・標準workflow：標準5ビュー、Auto基準高1120 | 2816×1280 |
| 基本4面プリセット：Auto基準高1120 | 2208×1280 |
| 基本4面、Manual | 1344×768 |
| 基本4面、Auto基準高672 | 1344×768 |
| 詳細7面、Auto基準高672 | 1696×768 |

テンプレートは、添付のサブグラフ構成、30 steps、CFG 1、encoderの `resolution=1024`、モデル指定を保持します。添付で逆になっていた参照接続を、配置画像 `image_1`・人物画像 `image_2` に揃えています。encoder自身のLATENT出力は使わず、Designer → EmptyLatentImage → KSamplerで出力寸法を供給します。

encoderの `resolution=1024` では配置参照と生成キャンバスの寸法が異なるため、配置への影響も確認してください。GPUでの速度・VRAMの比較は未実施です。

Coreの空latent補正にはチャンネル数だけでなく空間倍率も必要です。1344×768の比較ではQwen用latentが `[1,64,48,84]`、保存画像が1344×768になることを実機で確認してください。今回のCPU試験はCore関数の分離試験であり、実モデル・実保存の確認ではありません。

`Experimental` の1,032,192画素という閾値は既存UIから引き継いだ注意表示です。Qwenの品質限界、16GB VRAMの安全上限、生成禁止条件ではありません。

## 同梱ワークフロー

| ファイル | 用途 |
|---|---|
| `QwenImage21_Character_Sheet_Designer.json` | 標準5ビュー・基準高1120・添付のサブグラフとSaveImageAdvancedを保持 |

同梱ワークフローはこの1ファイルだけです。基本4面や詳細7面への切り替えはDesignerのプリセットを使います。ルートは4ノード・6リンク、生成サブグラフ内は9ノード・22リンクです。PreviewAnyには最終promptが入ります。画像1は配置、画像2は人物参照です。

API形式が必要な場合は、読み込んだテンプレートからComfyUIの「Export (API)」で保存します。`tools/workflow.py` もGUIテンプレート1本だけを出力します。

モデル名は提供ファイルを保持しています。

- UNET: `qwen\qwen_image_2.1_int8_convrot.safetensors`
- CLIP: `qwen3vl_8b_int8_convrot.safetensors` / type `qwen_image`
- VAE: `qwen_image_2.1_vae_bf16.safetensors`

ローダーの選択値は配布にモデルが含まれる意味ではありません。参照画像の名前も元の保存値であり、画像そのものは同梱しません。環境に存在しないパス・ファイル名は標準ローダーから選び直します。

開始値は30 steps / CFG 1 / euler / simple / denoise 1 / batch 1、Cache auto/defaultです。seed動作は元のrandomizeを保持します。PNG保存先は通常のComfyUI出力フォルダーです。生成画像のメタデータと再読込の実機確認は未実施です。

## UIのマネキン素材について

**元のH3ビットマップ `mannequin-atlas.png` を同梱し、標準で有効にしました。** 1254×1254の元PNGを変更せず、顔・全身・手・足の7ビューを既存の座標で切り出して表示します。Git blobは `35dd5fabbe138b7b181b89d55432a6e53d0e9c34` です。

更新後はComfyUIを再起動し、ブラウザーを再読込してください。H3フォルダーからの手動取り込みは不要です。画面ではPNGを読み込めない場合だけSVG代替表示を使います。画像出力には同梱PNGが必要です。マネキンは配置と向きのガイドで、人物の画風は人物参照から指定します。モデルによる配置の一致は保証しません。

`tools/import_h3_artwork.py` は破損・欠落時の復旧用として引き続き利用できます。固定した元PNGのGit blobを検証し、異なる素材や既存の異なるコピーを黙って上書きしません。

## 検証状況

整理後の検証はPython1,041件、JavaScript83件成功です。スタイルと標準5ビューテンプレートの実装では、実ComfyUIの独立CPU環境でスタイル選択・解除・Undo・保存再読込、5ビュー／基本4面の切り替え、新規ノードの870×1100サイズを確認しました。スタイル指定なしの40条件は従来promptと一致し、テンプレートのAPI入力も実Frontendの出力と一致しました。今回のスタイル・テンプレートでのGPU画質評価は未実施です。記録は `verification/styles.json` と `verification/templates.json` を参照してください。

以下は配置画像追加時までの検証記録です。

配置画像追加時はPython606件、JavaScript80件成功です。実ComfyUIの独立CPU環境で4出力登録、実FrontendからのQueue、2816×1280のレイアウトPNG保存、更新workflowの読込を確認しました。従来のH3幾何・保存stateとの互換性も検証しています。

既存のGPUサーバーで元の人物参照・seed・25 steps・CFG 1を使い、配置画像＋簡潔プロンプトで2回生成しました。拡大図2つ＋全身3つの構成になり、元の結果の中央人物の薄れは見られませんでした。ただし、正面拡大図は斜め向き、側面はガイドと逆向きのままです。配置画像は制御用のハードマスクではありません。1人物・1seedの確認であり、7ビュー全組合せ、部位変更、画質全般、VRAM比較の合格を示すものではありません。

GPU試験では稼働サーバーを再起動せず、生成済みの配置PNGをLoadImageへ接続し、最終版と同じpromptを直接渡しました。Designerの新しい4出力を通常の環境で使うには、ファイル更新後のComfyUI再起動とブラウザー再読込が必要です。記録は `verification/layout_reference.json` を参照してください。

元PNG適用後の再検証はPython580件・JavaScript79件成功です。PyTorch未導入のため既存CPU tensor試験3件は未実施。今回のブラウザー再検証は環境制約で実行できていません。元PNGの画素、同一ハッシュ、7ビューの切り出し・クリップ・同一スケールは確認済みです。詳細は `docs/ATLAS_VERIFICATION_JA.md` を参照してください。

以下は初版の記録です。

2026-10-05 JST。Linux上のCPU環境で **Python583成功、JavaScript75成功、Chromium独立UI26項目成功**です。詳細は `docs/VERIFICATION_JA.md`、記録は `verification/`、ハッシュは `manifest.json` を参照してください。

初版時点では実ComfyUIの登録・ワークフロー読込・実Queue・画像保存・GPU生成は未検証でした。上記の今回の確認とは区別してください。人物画像の品質に合格を付けていません。

## 開発用確認

以下は既存のPython/Nodeテスト環境から実行します。テスト用パッケージの自動インストールはありません。

```text
python -m pytest -q
node --test tests/js/*.test.js
python tests/browser/verify_browser.py --chromium <Chromium実行ファイルのパス>
```

ブラウザー試験はPlaywrightが使える環境用です。実UIモジュールを静的に束ね、実Chromium内で操作し、ComfyUI hostとpreview transportは試験用代替を使います。HTTP自体はaiohttpによる別試験で検証しています。

プレビューを手動確認する独立デモは `python tools/serve_demo.py --port 8197` で起動し、loopbackの `/tests/browser/index.html` を開きます。これはComfyUIではなく試験用画面です。

---

<a id="english"></a>

## English

[日本語へ戻る](#japanese)

**Outputs a Qwen prompt and layout image for the selected views only. Busts, full-body views and hand/foot details are described separately. You can inspect the generated prompt inside the node. Exact placement and viewing direction are not guaranteed.**

This ComfyUI node composes prompts and layouts for a static character sheet from one character reference image. It reuses the seven views, eight part inputs, Auto/Manual sizing, saved state and Undo behavior from a pinned revision of H3 Character Sheet Designer.

**The bundled template does not use a LoRA.** It generates through Qwen Image 2.1 using the character reference, a mannequin layout image and the natural-language prompt produced by this node. Layout, views, part details and rendering style are specified through prompting; training a character-specific LoRA is not required. The prompt asks the model to preserve the reference character and outfit while drawing the selected views.

The package registers only **QwenImage21CharacterSheetDesigner**. It does not require H3 or its Python package, and it does not change H3 node IDs, routes or workflows. Core workflow nodes handle model loading, image loading, sampling and saving.

### Installation

#### Install with Git (clone)

Install Git and replace `<ComfyUI folder>` with the path to your ComfyUI installation.

```sh
cd "<ComfyUI folder>/custom_nodes"
git clone https://github.com/ukr8b3g-cmyk/Qwen-Image-2.1-Character-Sheet-Designer.git
```

Restart ComfyUI and reload the browser after installation.

#### Install from ZIP

Place the `Qwen-Image-2.1-Character-Sheet-Designer` folder from the ZIP directly under `ComfyUI/custom_nodes/`, then restart ComfyUI and reload the browser. Avoid installing multiple copies of this Qwen node.

#### Update (pull)

For a Git installation, run the following inside the cloned repository:

```sh
cd "<ComfyUI folder>/custom_nodes/Qwen-Image-2.1-Character-Sheet-Designer"
git pull --ff-only
```

Restart ComfyUI and reload the browser after updating. Commit or set aside local edits before pulling. For a ZIP installation, update from a new ZIP.

#### Publish your changes (push; developers)

`push` sends your changes to GitHub. It is not needed for ordinary installation or updates and requires write access to the destination repository. Example after editing the README:

```sh
git status
git add README.md
git commit -m "Update README"
git push origin main
```

Run these commands inside the repository folder. For other edits, pass the changed filenames to `git add`. If you use a fork, configure `origin` to point to your fork.

#### Requirements

No additional runtime pip/npm dependencies are required. The preview API uses aiohttp bundled with ComfyUI. The package does not automatically download models or run an external LLM.

Required Core features are `TextEncodeQwenImage21`, `QwenImage21Cache`, standard loaders, KSampler and VAEDecode. The template uses `SaveImageAdvanced`; replace it with the standard `SaveImage` node if unavailable. Check node registration and output dimensions in your environment.

### Usage

Find **Qwen Image 2.1 Character Sheet Designer** under `Qwen/CharacterSheet`.

1. Load `workflows/QwenImage21_Character_Sheet_Designer.json`.
2. Select an available character reference in `LoadImage` and select your installed Qwen 2.1 models in the generation subgraph.
3. Set the Designer views, dimensions and any part directives, then generate.

```text
Designer.prompt ─────────── TextEncodeQwenImage21.prompt
Designer.layout_image ──── TextEncodeQwenImage21.images.image_1
LoadImage.IMAGE ─────────── TextEncodeQwenImage21.images.image_2
                                  │ positive / negative
Designer.width / height           ↓
          └─ EmptyLatentImage ── KSampler ── VAEDecode ── SaveImageAdvanced
Designer.prompt ─────────── PreviewAny (inside the subgraph)
```

The four outputs are `prompt: STRING`, `width: INT`, `height: INT` and `layout_image: IMAGE`. The original three output positions and the `state_json` format are preserved. The layout output is a white-background RGB image made from the same geometry and mannequin artwork as the preview, at the Designer's output dimensions. It can connect to standard PreviewImage or SaveImage nodes.

The bundled template enables `use_layout_image`. The prompt uses `<image1>` for placement, size and direction, and `<image2>` for character identity, clothing and rendering style. Each selected view and part directive is described once without coordinate JSON. For an existing workflow using only a character reference, keep the default OFF setting and connect the character to `images.image_1`. The ON/OFF setting is saved as an independent BOOLEAN input.

Both the preview and `layout_image` enclose each selected view in a black rectangular frame. With layout referencing enabled, the prompt asks the model to keep those frames in the finished sheet and replace only the gray mannequins. It asks to preserve frame position and dimensions, mannequin size, direction and crop. Portraits are busts containing the head, neck, shoulders and upper chest only. Fixed instructions form one paragraph; original part text and line breaks are retained. See [docs/LAYOUT_REFERENCE_JA.md](docs/LAYOUT_REFERENCE_JA.md) for editing guidance and verification conditions (Japanese).

#### Views and part directives

Seven views are available: front face/bust, left-profile face/bust, front full body, left-side full body, back full body, both hands and feet/footwear. At least one view must remain selected.

New nodes default to **Standard · 5 views**: the two busts and three full-body views, Auto body height 1120, and no style override. **Basic · 4 views** omits the left-profile bust and is available as a preset. Initial node size is 870×1100, matching the supplied workflow. Loading saved selections does not replace them with the defaults.

Each view checkbox affects both the prompt and layout image. All seven enabled means two busts, three full-body views and two detail panels. A partial selection describes only those panels and their count. One full-body view does not receive multi-view alignment instructions. Open **Generated prompt** to inspect the current output for the selection and layout-reference setting. A stale prompt is not shown as current while a request is pending or has failed.

The eight part inputs are head/hair, face, upper clothing, back clothing, lower body, hands/gloves, feet/footwear and overall/other. They preserve your text without automatic translation. Glove and shoe instructions still apply to full-body views when the hand/foot detail panels are disabled. Back patterns are restricted to the back of the clothing; the prompt does not ask the character to turn around to show the face.

View and part edits save immediately. **Typed numeric values commit on Enter or blur.** Incomplete or invalid numbers do not enter the saved state or queue. Preview delays or failures do not roll back saved values. The raw `state_json` editor remains available when the API fails.

The UI follows ComfyUI's `Comfy.Locale`: Japanese for `ja` locales, English otherwise. Fixed generation instructions are in English.

#### Style

Use the **Style** tab to the right of **Part directives**. Choose one of: None (default), Anime, Photo, Realistic painting, Semi-realistic anime, Oil painting, Watercolor, Gouache, Colored pencil or 3D CG. An active style badge and a Clear button stay visible outside the tab. Semi-realistic anime asks for anime linework and modeled shading while preserving the reference facial and body proportions.

None leaves the existing prompt unchanged. Selecting a style replaces the instruction to preserve the reference rendering medium and applies only the rendering treatment consistently across all selected views. The prompt preserves identity, outfit, existing accessories, colors, patterns and placement, while respecting explicit part directives. These are custom prompt presets; they cannot guarantee that the model will avoid every unwanted addition or character change.

Style is saved as an independent optional COMBO input, `style`, and supports Undo. Existing `state_json` v1/v2 and the four output sockets are preserved. Restart ComfyUI and reload the browser after updating.

#### Saved state

The node accepts H3-compatible schema v1/v2. Reading v1 alone does not migrate it; editing a part advances it to v2. No new keys are added to `state_json`.

Validation covers strict JSON up to 64 KiB, dimensions of at least 32 and multiples of 32, Core MAX_RESOLUTION, and 1000 UTF-16 units per part. Unknown or duplicate keys, invalid Unicode, numeric strings, fractional dimensions, booleans as numbers, NaN and Infinity are rejected. Invalid data is not silently replaced with defaults.

#### Dimensions

Auto computes the arrangement from body height and rounds both dimensions up to multiples of 32. Manual fits the whole arrangement into the requested canvas while preserving its aspect ratio; changing views does not change the canvas size. High resolutions are not automatically reduced.

| Setting | Output |
|---|---:|
| New node / template: Standard 5 views, Auto body height 1120 | 2816×1280 |
| Basic 4-view preset, Auto body height 1120 | 2208×1280 |
| Basic 4 views, Manual | 1344×768 |
| Basic 4 views, Auto body height 672 | 1344×768 |
| Detail 7 views, Auto body height 672 | 1696×768 |

The template preserves the supplied subgraph, 30 steps, CFG 1, encoder `resolution=1024` and model selections. Reference connections are corrected to layout `image_1` and character `image_2`. The encoder's LATENT output is not used: Designer → EmptyLatentImage → KSampler supplies the output dimensions.

At encoder `resolution=1024`, layout-reference dimensions differ from the generation canvas. Check its effect on placement in your environment. GPU speed/VRAM comparisons have not been performed.

Core empty-latent correction must handle spatial scale as well as channels. For a 1344×768 comparison, check that the Qwen latent is `[1,64,48,84]` and the saved image is 1344×768. The CPU check isolates Core functions; it does not prove real-model generation or image saving.

The inherited **Experimental** threshold of 1,032,192 pixels is an advisory display value, not a Qwen quality limit, a safe 16 GB VRAM ceiling or a generation prohibition.

### Bundled workflow

Only `workflows/QwenImage21_Character_Sheet_Designer.json` is bundled. It uses Standard 5 views, body height 1120, the supplied generation subgraph and SaveImageAdvanced. Select Basic 4 views or Detail 7 views through the Designer presets. The root has four nodes and six links; the generation subgraph has nine nodes and 22 links. PreviewAny receives the final prompt. Image 1 is the layout and image 2 is the character reference.

For an API payload, load the template and use ComfyUI's **Export (API)**. `tools/workflow.py` also writes only the single GUI template.

The saved model names are:

- UNET: `qwen\qwen_image_2.1_int8_convrot.safetensors`
- CLIP: `qwen3vl_8b_int8_convrot.safetensors` / type `qwen_image`
- VAE: `qwen_image_2.1_vae_bf16.safetensors`

Models and the character reference image are not bundled. Reselect filenames through the standard loaders if they do not exist in your environment.

Starting settings are 30 steps / CFG 1 / euler / simple / denoise 1 / batch 1, with Cache auto/default. The supplied randomize seed behavior is preserved. PNGs save to the normal ComfyUI output folder. Generated-image metadata and reloading have not been verified in a live environment.

### Mannequin artwork

The original H3 bitmap, `mannequin-atlas.png`, is bundled and enabled by default. The unchanged 1254×1254 PNG is cropped at the existing coordinates for the seven views. Its Git blob is `35dd5fabbe138b7b181b89d55432a6e53d0e9c34`.

Restart ComfyUI and reload the browser after updating. No manual copying from H3 is needed. The UI falls back to SVG only if the PNG cannot be loaded; image output requires the bundled PNG. Mannequins guide arrangement and direction. The character reference supplies rendering style unless a style is selected. Exact model adherence is not guaranteed.

`tools/import_h3_artwork.py` remains available for recovery from missing or damaged artwork. It verifies the pinned original Git blob and does not silently overwrite a different existing image.

### Verification

After consolidating the workflow, **1,041 Python tests and 83 JavaScript tests passed**. An isolated CPU ComfyUI environment verified style selection/clear, Undo, save/reload, switching between five and four views, and the 870×1100 new-node size. Forty no-style conditions matched the previous prompt, and the template's API inputs matched the actual Frontend export. GPU image-quality evaluation for these style/template changes has not been performed. See `verification/styles.json` and `verification/templates.json`.

Earlier verification records:

- Layout-output addition: 606 Python and 80 JavaScript tests passed. Live isolated CPU ComfyUI checks covered four output sockets, queue submission through the Frontend, a saved 2816×1280 layout PNG and workflow loading.
- Earlier GPU checks generated two sheets using one character reference, one seed, 25 steps and CFG 1 with a layout image and compact prompt. They produced two enlarged studies plus three full-body views without the original central fading. The front study was still angled, and the side view faced the opposite direction to its guide. The layout image is not a hard mask. These checks do not establish all seven-view combinations, part-edit behavior, general image quality or VRAM performance.
- Those GPU checks used a saved layout PNG and the final prompt directly without restarting the running server. Using the Designer's four outputs after an update requires restarting ComfyUI and reloading the browser. See `verification/layout_reference.json`.
- Original atlas update: 580 Python and 79 JavaScript tests passed. Three CPU tensor tests were not run because PyTorch was unavailable; that browser recheck was blocked by environment constraints. Pixels, matching hashes, seven crops, clipping and scale were checked. See [docs/ATLAS_VERIFICATION_JA.md](docs/ATLAS_VERIFICATION_JA.md).
- Initial version, 2026-10-05 JST: 583 Python tests, 75 JavaScript tests and 26 isolated Chromium UI checks passed on Linux CPU. At that stage, live ComfyUI registration, queueing, saving and GPU generation were not verified. See [docs/VERIFICATION_JA.md](docs/VERIFICATION_JA.md), `verification/` and `manifest.json`.

### Development checks

Run in an existing Python/Node test environment. Test dependencies are not installed automatically.

```text
python -m pytest -q
node --test tests/js/*.test.js
python tests/browser/verify_browser.py --chromium <path-to-Chromium>
```

Browser checks require Playwright. They bundle the real UI modules and exercise them in Chromium with a test ComfyUI host and preview transport. HTTP behavior is checked separately through aiohttp.

For a standalone preview demo, run `python tools/serve_demo.py --port 8197` and open loopback `/tests/browser/index.html`. This is a test page, not ComfyUI.
