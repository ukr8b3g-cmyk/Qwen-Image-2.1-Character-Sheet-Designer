# 実装の確定内容と資料間の差分

対象: Qwen-Image-2.1-Character-Sheet-Designer / 実装プレビュー0.1.0

## 優先順位

今回の「新しい独立リポジトリで実装」という依頼を配置先の指示とし、追加DOCX `Qwen_Image21_Character_Sheet_Designer_Implementation_Spec_JA(1).docx` を機能仕様の基準にしました。以前のv1.1案と矛盾する内容は隠さず、以下のように扱っています。

| 内容 | 今回の実装 |
|---|---|
| 同一H3パッケージへの追加 | 新リポジトリを独立パッケージ化。登録はQwenのみ。既存H3には変更なし |
| 独自schema v1 / reference_mode | 不採用。追加DOCXどおりH3共通のschema v1/v2 |
| 人物＋衣装の参照モード | 初版から除外。人物参照1枚 |
| Manual1344×768を標準初期値 | 既定のAuto1120を保持。元workflowの5ビューを保持し、比較版を別ファイル化 |
| 生成promptにlayout JSONを入れない | 追加DOCXどおりQwen専用contentのlayout JSONとパネル文章を含める |
| 高解像度の別閾値 | 既存1,032,192画素の注意表示を維持。禁止・自動縮小には使わない |
| PreviewAnyを削除 | 最終prompt確認用として保持。Designerに直結しPE依存を除去 |
| 保存ノードSaveImageのみ | 標準は資料どおりSaveImageAdvanced。標準SaveImage版も別途同梱 |
| 数値入力を即時同期 | 元UIのEnter/blur確定を維持。未確定の数値は保存／Queue対象外と明示 |

## ソースの再利用

H3配布基準は `bf792c652a9f50e895409e49fce667fef0f73c25`。資料にある動作コード基準は `1074be06120557df3439af19be38d036a122f655` と解決し、別の参照として記録しました。実際に取り込んだ各ファイルのGit blob SHAを検証しています。

H3の検証・正規化、幾何計算、layout JSON serializerをQwen内部の `common/` に分離しました。H3用の完成promptを生成して置換する方式ではありません。Qwenのview説明、panel content、promptは独立した `compiler.py` で組み立てます。UIのstate処理は固定H3ソースをそのまま再利用します。

H3そのものは変更せず、試験に固定ソースを置き、抽出した幾何へ元のH3文章を再結合してbyte parityを確認しました。将来H3が更新されても、このQwenパッケージの挙動が自動変更される構成にはしていません。

## UIと登録の分離

CSS、SVGのID、DOM widget名、拡張名、プレビューURLをQwen用に分離しました。H3/Qwen併存時のスタイルやルートの取り違えを防ぎます。標準 `state_json` の位置とvalue getter/setterを保持し、非保存DOM widgetは別名で追加します。

追加DOCXのAPI障害時編集条件に合わせ、Qwen版ではpreviewに失敗した場合もraw JSON編集欄へアクセスできるようにしました。入力原文は初期値へ置き換えません。

元PNGはH3のGit blob `35dd5fabbe138b7b181b89d55432a6e53d0e9c34` と一致するファイルを同梱し、標準で有効にしています。7ビューの切り出し座標とsource clipPathは既存のH3由来の実装を保持しました。SVG代替はローカルPNGの読込失敗時だけ使用します。検証付き取り込みツールは復旧用として残しています。純粋コンパイラや通常のnode importはファイルコピーやネットワーク取得を行いません。

## ワークフロー原本

取得できた原本は `image_qwen_image_2_1_image_edit.json`（20ノード/24リンク）と `H3_Character_Sheet_Designer_wf (2).json`（5ノード/5リンク）です。DOCXで表記される `(1)` とファイル名は異なるため、同一ファイルであるとは主張しません。利用した `(2)` の実際の5ビュー状態とSHA-256を記録し、その値を保持しました。

H3側のLoadImage4、Designer15の保存状態、SaveImageAdvanced20を採用し、Qwen側の3ローダー、Cache、encoder、EmptyLatentImage、KSampler、VAEDecode、PreviewAnyへ接続しました。リンク番号・port番号は入力名／出力名から再作成し、双方のリンク参照を検査しました。

ComfyUI Core参照は `f1072eb0350638a3390ddb6afbcaa8c6b237c6fd`。Coreのloaderはパス中のピリオドを `_x_` に置換してPythonへ登録する実装でした。試験もこの実際の契約に合わせています。任意の未変換dotted module名による読み込み失敗をComfyUIの不具合とは扱っていません。

## 今回の範囲外

コミット・push・PR・Release・Registry登録、ユーザーのWindows環境への配置、モデル／参照画像の取得、実ComfyUI、GPU生成は行っていません。複数参照、衣装役割、ビュー別の別生成と合成、追加LLM、画像による厳密配置制約も実装していません。
