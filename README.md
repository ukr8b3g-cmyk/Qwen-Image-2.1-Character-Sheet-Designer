# Qwen Image 2.1 Character Sheet Designer

**v0.1.0 implementation preview — CPU / JavaScript / offline browser checks passed; real ComfyUI and GPU validation pending.**

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
LoadImage.IMAGE ─────────── TextEncodeQwenImage21.images.image_1
                                  │ positive / negative
Designer.width / height           ↓
          └─ EmptyLatentImage ── KSampler ── VAEDecode ── SaveImageAdvanced
Designer.prompt ─────────── PreviewAny
```

Designerの `state_json` が唯一の保存入力です。出力は `prompt: STRING`、`width: INT`、`height: INT` の3つだけです。画像入力はDesignerに増設せず、参照はencoderへ直接接続します。参照がなくてもDesigner自体は文章を作れるため、`images.image_1` の接続を確認してください。

### ビューと部位

正面の顔・胸、左横顔・胸、全身正面、全身左側面、全身背面、両手詳細、両足／履物詳細の7ビューです。最低1ビューを選びます。

部位は頭・髪、顔、上半身の服、背面の服、下半身、手・手袋、足・履物、全体・その他の8項目です。入力は自動翻訳せず原文を保持します。手・足の詳細をOFFにしても、手袋や靴の指定は全身に適用されます。背面柄は背面の衣服表面に限定し、顔を見せるための振り向きは要求しません。

ビューや部位指定は即時保存です。**数値の手入力はEnterまたはフォーカスを外したときに確定**します。入力途中・不正な数値は保存やQueueに入りません。表示される注意を確認して確定してください。プレビューの遅延・失敗は保存値を巻き戻しません。API失敗時もraw `state_json` 編集欄を開けます。

UI言語はComfyUIの `Comfy.Locale` が `ja` 系なら日本語、それ以外は英語です。生成用の定型文は英語です。

### 保存形式

H3と同じschema v1/v2を受理します。v1を読み込むだけでは移行せず、実際に部位を編集したときだけv2へ進みます。`reference_mode` や `model` は追加しません。以前の案にある衣装参照・複数画像役割の設定は初版の非対象です。

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

encoderの `resolution=1024` は**参照画像の処理面積の目安**であり、出力幅・高さではありません。参照の縦横比を保持する設定です。encoder自身のLATENT出力は使わず、Designer → EmptyLatentImage → KSamplerで出力寸法を供給します。

Coreの空latent補正にはチャンネル数だけでなく空間倍率も必要です。1344×768の比較ではQwen用latentが `[1,64,48,84]`、保存画像が1344×768になることを実機で確認してください。今回のCPU試験はCore関数の分離試験であり、実モデル・実保存の確認ではありません。

`Experimental` の1,032,192画素という閾値は既存UIから引き継いだ注意表示です。Qwenの品質限界、16GB VRAMの安全上限、生成禁止条件ではありません。

## 同梱ワークフロー

| ファイル | 用途 |
|---|---|
| `QwenImage21_Character_Sheet_Designer.json` | 元の5ビュー設定・基準高1120・SaveImageAdvancedを保持 |
| `QwenImage21_Character_Sheet_Designer_CoreSaveImage.json` | 上記と同じ条件で保存だけ標準SaveImageへ変更 |
| `QwenImage21_Basic4_1344x768_Comparison.json` | 基本4面・1344×768・固定seedの比較開始用 |

それぞれ12ノード・15リンクです。PE/TextGenerate、サイズSwitch、H3 subgraph、動画・音声分岐は含みません。PreviewAnyにはDesignerと同じ最終promptが直接入ります。

`.api.json` は同梱グラフから作った**静的なAPI形式候補**です。実FrontendのgraphToPromptで得た実測payloadではありません。通常はGUI用 `.json` を使い、実環境で検証するまでAPI投入成功を前提にしないでください。

モデル名は提供ファイルを保持しています。

- UNET: `qwen\qwen_image_2.1_int8_convrot.safetensors`
- CLIP: `qwen3vl_8b_int8_convrot.safetensors` / type `qwen_image`
- VAE: `qwen_image_2.1_vae_bf16.safetensors`

ローダーの選択値は配布にモデルが含まれる意味ではありません。参照画像の名前も元の保存値であり、画像そのものは同梱しません。環境に存在しないパス・ファイル名は標準ローダーから選び直します。

開始値は25 steps / CFG 1 / euler / simple / denoise 1 / batch 1、Cache auto/defaultです。標準workflowのseed動作は元のrandomizeを保持し、比較版だけ固定しています。PNG保存先は通常のComfyUI出力フォルダーです。メタデータと再読込の実機確認は未実施です。

## UIのマネキン素材について

**元のビットマップ `mannequin-atlas.png` は作業環境から取得できなかったため、この実装版には含まれていません。** 今回は同じH3リビジョンに含まれるSVG代替素材を同梱し、7ビューすべての表示を確認しました。操作UIと幾何は再利用していますが、元のPNGと同一の見た目を確認済みとはしていません。

既存H3フォルダーがある場合、Qwenフォルダーで次を実行すると、固定した元PNGのGit blob SHAを検証してからQwen側へコピーします。H3側は読み取りのみです。ネットワーク・モデルダウンロードは行いません。

```powershell
python .\tools\import_h3_artwork.py "..\H3-Character-Sheet-Designer"
```

成功後はブラウザーを再読込します。異なる素材や既存の異なるコピーを黙って上書きしません。素材は表示専用で、生成入力へ接続されません。

## 検証状況

2026-10-05 JST。Linux上のCPU環境で **Python583成功、JavaScript75成功、Chromium独立UI26項目成功**です。詳細は `docs/VERIFICATION_JA.md`、記録は `verification/`、ハッシュは `manifest.json` を参照してください。

**実ComfyUIの登録・Pinia・ワークフロー読込・実Queue・画像保存・GPU生成は未検証です。** 実画像の人物保持、左右、全身欠け、部位変更、出力寸法、速度・VRAMに合格を付けていません。初版の画像品質と公開可否は実機評価後に判断します。

## 開発用確認

以下は既存のPython/Nodeテスト環境から実行します。テスト用パッケージの自動インストールはありません。

```text
python -m pytest -q
node --test tests/js/*.test.js
python tests/browser/verify_browser.py --chromium <Chromium実行ファイルのパス>
```

ブラウザー試験はPlaywrightが使える環境用です。実UIモジュールを静的に束ね、実Chromium内で操作し、ComfyUI hostとpreview transportは試験用代替を使います。HTTP自体はaiohttpによる別試験で検証しています。

プレビューを手動確認する独立デモは `python tools/serve_demo.py --port 8197` で起動し、loopbackの `/tests/browser/index.html` を開きます。これはComfyUIではなく試験用画面です。
