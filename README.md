# Qwen Image 2.1 Character Sheet Designer

**選択したビューだけのQwen向けプロンプトとレイアウト画像を出力します。胸像・全身・手足の詳細を区別し、ノード内で生成プロンプトを確認できます。厳密な生成配置・向きの一致は保証しません。**

人物参照1枚から静止キャラクターシートを作るための、ComfyUI用プロンプト・レイアウト作成ノードです。H3 Character Sheet Designer の7ビュー、8部位入力、Auto／Manual寸法、保存・Undoの操作を固定リビジョンから再利用しています。

このパッケージは **QwenImage21CharacterSheetDesigner のみ登録**します。H3のインストールやPythonパッケージに依存せず、既存H3のノードID・ルート・ワークフローを変更しません。モデルのロード、画像読み込み、サンプリング、保存はワークフローのCoreノードが担当します。

## インストール

ZIP内の `Qwen-Image-2.1-Character-Sheet-Designer` フォルダーを `ComfyUI/custom_nodes/` 直下へ置き、ComfyUIを再起動してブラウザーを再読込します。同じQwen版を複数フォルダーに配置しないでください。

実行用の追加pip/npm依存関係はありません。プレビューAPIはComfyUIに含まれるaiohttpを使用します。モデルや外部LLMの自動取得・実行はありません。

必要なCore機能は `TextEncodeQwenImage21`、`QwenImage21Cache`、標準ローダー・KSampler・VAEDecodeです。標準ワークフローでは `SaveImageAdvanced` を使います。この保存ノードがない環境向けに標準 `SaveImage` 版も同梱しています。単にバージョン番号だけで互換性を保証せず、実環境でノード登録と出力寸法を確認してください。

## 使い方

ノード名は **Qwen Image 2.1 Character Sheet Designer**、カテゴリは `Qwen/CharacterSheet` です。

1. `workflows/QwenImage21_Character_Sheet_Designer.json` を読み込みます。
2. `LoadImage` で実在する人物参照を選び、3つの標準ローダーで所持しているQwen 2.1モデルを選択します。
3. Designerのビュー、サイズ、必要な部位指定を設定して生成します。

```text
Designer.prompt ─────────── TextEncodeQwenImage21.prompt
Designer.layout_image ──── TextEncodeQwenImage21.images.image_1
LoadImage.IMAGE ─────────── TextEncodeQwenImage21.images.image_2
                                  │ positive / negative
Designer.width / height           ↓
          └─ EmptyLatentImage ── KSampler ── VAEDecode ── SaveImageAdvanced
Designer.prompt ─────────── PreviewAny
Designer.layout_image ──── PreviewImage
```

出力は `prompt: STRING`、`width: INT`、`height: INT`、`layout_image: IMAGE` の4つです。既存3出力の順序と `state_json` の保存形式は維持します。`layout_image` は画面と同じ配置計算・マネキン素材から作る白背景のRGB画像で、幅・高さはDesignerの指定と一致します。標準PreviewImageやSaveImageへ接続できます。

同梱workflowは `use_layout_image=ON` です。プロンプトは `<image1>` を配置・大きさ・向き、`<image2>` を人物・衣装・画風として扱います。座標JSONと重複説明を除き、各ビューと部位指定を一度ずつ記述します。人物参照1枚だけの既存workflowでは既定のOFFを使い、人物を `images.image_1` へ接続します。ON/OFFは独立したBOOLEAN入力として保存されます。

`layout_image` とノード内プレビューは、選択した各ビューを黒い長方形の枠で囲みます。配置参照ONでは、この黒枠を完成画像に残し、枠内の灰色マネキンだけを人物へ置き換える編集指示を生成します。枠の位置・寸法、各マネキンの大きさ・向き・切り取り範囲を保持し、顔・胸は頭・首・肩・胸上部だけの胸像とします。定型文は一段落にまとめ、部位指定の原文と改行は保持します。公式の編集指針と検証条件は [docs/LAYOUT_REFERENCE_JA.md](docs/LAYOUT_REFERENCE_JA.md) を参照してください。

### ビューと部位

正面の顔・胸、左横顔・胸、全身正面、全身左側面、全身背面、両手詳細、両足／履物詳細の7ビューです。最低1ビューを選びます。

各カードのON/OFFは生成promptとlayout_imageの両方へ反映されます。全ONなら胸像2図・全身3図・手足の詳細2図、部分選択ならその構成と図数だけを指定します。全身1図では複数図の整列指示を出しません。「生成プロンプト」を開くと、現在のチェック状態とuse_layout_image設定に対応した出力文字列を確認できます。取得中・失敗時には古い文字列を現在の出力として表示しません。

部位は頭・髪、顔、上半身の服、背面の服、下半身、手・手袋、足・履物、全体・その他の8項目です。入力は自動翻訳せず原文を保持します。手・足の詳細をOFFにしても、手袋や靴の指定は全身に適用されます。背面柄は背面の衣服表面に限定し、顔を見せるための振り向きは要求しません。

ビューや部位指定は即時保存です。**数値の手入力はEnterまたはフォーカスを外したときに確定**します。入力途中・不正な数値は保存やQueueに入りません。表示される注意を確認して確定してください。プレビューの遅延・失敗は保存値を巻き戻しません。API失敗時もraw `state_json` 編集欄を開けます。

UI言語はComfyUIの `Comfy.Locale` が `ja` 系なら日本語、それ以外は英語です。生成用の定型文は英語です。

### 保存形式

H3と同じschema v1/v2を受理します。v1を読み込むだけでは移行せず、実際に部位を編集したときだけv2へ進みます。`state_json` に新しいキーは追加しません。

64KiBの厳密JSON、32以上の32倍数、Core MAX_RESOLUTION、部位ごと1000 UTF-16単位を検証します。未知キー、重複キー、無効なUnicode、数値文字列、小数、真偽値、NaN/Infinityを拒否します。不正データを初期値へ勝手に置換しません。

### サイズ

Autoは基準高を保って配置を算出し、両軸を32の倍数へ切り上げます。Manualは指定キャンバスに全体を縦横比維持で収め、ビュー変更でも寸法を変えません。高解像度を自動縮小しません。

| 設定 | 出力 |
|---|---:|
| 新規ノード既定：基本4面、Auto基準高1120 | 2208×1280 |
| 同梱標準workflow：元の5ビュー、Auto基準高1120 | 2816×1280 |
| 比較workflow：基本4面、Manual | 1344×768 |
| 基本4面、Auto基準高672 | 1344×768 |
| 詳細7面、Auto基準高672 | 1696×768 |

同梱workflowのencoderは `resolution=0` で配置画像の寸法を保持します。最初の参照と生成キャンバスの寸法を一致させるためです。人物参照は自身の寸法を32倍数へ丸めて処理されます。encoder自身のLATENT出力は使わず、Designer → EmptyLatentImage → KSamplerで出力寸法を供給します。

0は参照処理のメモリ使用量を増やします。負荷を下げる場合はDesignerの出力を小さくするか、encoderのresolutionを1024などへ変更できます。後者は配置参照と生成キャンバスの寸法が異なるため、配置への影響も確認してください。GPUでの速度・VRAMの比較は未実施です。

Coreの空latent補正にはチャンネル数だけでなく空間倍率も必要です。1344×768の比較ではQwen用latentが `[1,64,48,84]`、保存画像が1344×768になることを実機で確認してください。今回のCPU試験はCore関数の分離試験であり、実モデル・実保存の確認ではありません。

`Experimental` の1,032,192画素という閾値は既存UIから引き継いだ注意表示です。Qwenの品質限界、16GB VRAMの安全上限、生成禁止条件ではありません。

## 同梱ワークフロー

| ファイル | 用途 |
|---|---|
| `QwenImage21_Character_Sheet_Designer.json` | 元の5ビュー設定・基準高1120・SaveImageAdvancedを保持 |
| `QwenImage21_Character_Sheet_Designer_CoreSaveImage.json` | 上記と同じ条件で保存だけ標準SaveImageへ変更 |
| `QwenImage21_Basic4_1344x768_Comparison.json` | 基本4面・1344×768・固定seedの比較開始用 |

それぞれ13ノード・17リンクです。PreviewAnyには最終prompt、PreviewImageにはレイアウト画像が直接入ります。画像1は配置、画像2は人物参照です。

`.api.json` は同梱グラフから作った**静的なAPI形式候補**です。実FrontendのgraphToPromptで得た実測payloadではありません。通常はGUI用 `.json` を使い、実環境で検証するまでAPI投入成功を前提にしないでください。

モデル名は提供ファイルを保持しています。

- UNET: `qwen\qwen_image_2.1_int8_convrot.safetensors`
- CLIP: `qwen3vl_8b_int8_convrot.safetensors` / type `qwen_image`
- VAE: `qwen_image_2.1_vae_bf16.safetensors`

ローダーの選択値は配布にモデルが含まれる意味ではありません。参照画像の名前も元の保存値であり、画像そのものは同梱しません。環境に存在しないパス・ファイル名は標準ローダーから選び直します。

開始値は25 steps / CFG 1 / euler / simple / denoise 1 / batch 1、Cache auto/defaultです。標準workflowのseed動作は元のrandomizeを保持し、比較版だけ固定しています。PNG保存先は通常のComfyUI出力フォルダーです。メタデータと再読込の実機確認は未実施です。

## UIのマネキン素材について

**元のH3ビットマップ `mannequin-atlas.png` を同梱し、標準で有効にしました。** 1254×1254の元PNGを変更せず、顔・全身・手・足の7ビューを既存の座標で切り出して表示します。Git blobは `35dd5fabbe138b7b181b89d55432a6e53d0e9c34` です。

更新後はComfyUIを再起動し、ブラウザーを再読込してください。H3フォルダーからの手動取り込みは不要です。画面ではPNGを読み込めない場合だけSVG代替表示を使います。画像出力には同梱PNGが必要です。マネキンは配置と向きのガイドで、人物の画風は人物参照から指定します。モデルによる配置の一致は保証しません。

`tools/import_h3_artwork.py` は破損・欠落時の復旧用として引き続き利用できます。固定した元PNGのGit blobを検証し、異なる素材や既存の異なるコピーを黙って上書きしません。

## 検証状況

今回の追加機能はPython606件、JavaScript80件成功です。実ComfyUIの独立CPU環境で4出力登録、実FrontendからのQueue、2816×1280のレイアウトPNG保存、更新workflowの読込を確認しました。従来のH3幾何・保存stateとの互換性も検証しています。

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
