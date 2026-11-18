# STOIQ（ストイック）

**日々、理想を磨く。** 食事・トレーニング・90日間の自己成長を、既存のdietappアカウントで使うFlaskアプリです。

公開先：[dietinfo.onrender.com](https://dietinfo.onrender.com)（旧DietInfoと同じURLを利用）。旧READMEの開発背景・記録は [docs/dietapp-history.md](docs/dietapp-history.md) に保存しています。

## 今回の変更

- トップ → 食事・レシピページ `/food`。5件のオリジナルレシピ、食材のAND検索・表記ゆれ対応、減量／筋づくり目的の絞り込み、材料・手順ページ。
- 手持ち食材からGeminiが最大3件を提案。フォームの食材・除外食材・目的・時間・人数だけを送信。日記、体重、ジム、アカウント情報は送信しません。
- 提案は本人だけの下書きとして保存。本人の確認後に公開でき、後から非公開に戻せます。公開すると未ログインの人も閲覧できます。
- 写真はPexelsの実写参考写真を使用し、各詳細ページに撮影者・出典・ライセンスを表示。レシピを実際に調理した完成写真とは区別しています。Cookpadからの無断転載やAI画像生成は行いません。[写真出典](static/images/recipes/CREDITS.md)。
- 自分のAIレシピには、使用権を持つ実写写真を追加できます。画像形式・サイズ確認、EXIF除去・縮小後、写真を既存DBに保存します。写真ファイル用の新たな有料ディスクは不要です。投稿者の実写・権利確認を必須にしていますが、AI画像を自動判定する仕組みではありません。
- `/growth` に90日チャレンジ、習慣チェックと編集、振り返り・感情整理、5カテゴリ自己評価、週次レビュー、体重・ウエスト推移を統合。既存の体重・筋トレ記録も参照します。個人記録はアカウントごとに非公開です。
- 従来のログイン、ジム・マシン、AIトレーニング、体重、食事記録のルートを維持。全POSTにCSRF保護を追加し、トレーニング提案のジム所有者チェックを追加。

## ローカル起動

Python 3.12以降を推奨します。依存を入れた環境で、このフォルダーを作業ディレクトリにして実行します。

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py migrate
python -m flask --app app run --port 5001
```

`http://localhost:5001` を開き、新規登録してください。`DATABASE_URL` 未設定のローカル環境は `instance/stoiq-local.db` を使います。公開データベースや以前のBECOMEのDBには自動接続・自動移行しません。

`.env.example` は設定項目の見本です。`.env` ファイルの自動読み込みは行いません。PowerShellまたはホスティングサービスの環境変数として設定してください。キーをチャットやGitに貼り付けないでください。

| 環境変数 | 用途 |
| --- | --- |
| `DATABASE_URL` | 公開環境の既存PostgreSQL接続先。既存値を維持 |
| `SECRET_KEY` | 本番セッション署名用のランダムな秘密値。設定を推奨。未設定時、現在のRenderは既存の永続ディスク `/var/data/stoiq/.session-key` に、ローカルは `instance/.session-key` に自動作成。永続ディスクもない公開環境では起動を拒否 |
| `SESSION_KEY_FILE` | 別の永続ディスクにセッションキーを保存する場合の絶対パス（任意） |
| `GEMINI_API_KEY` | dietappが利用しているGeminiキー。未設定時はAI提案を無効表示し、掲載レシピの検索は利用可能 |
| `GEMINI_MODEL` | 既存の `gemini-2.5-flash` を既定値として維持。アカウントで利用できるモデルに変更可能 |
| `AI_DAILY_LIMIT` | AIレシピの1ユーザー1日あたり呼び出し上限。既定10回。失敗した呼び出しも数えます |
| `PUBLIC_ORIGIN` | 公開URLのオリジン（例 `https://example.onrender.com`）。独自ドメイン使用時は設定 |
| `SQLITE_PATH` | ローカル開発用の別DBパス（任意。本番PostgreSQL設定時は不使用） |

## 既存の公開サイトへの反映

1. 既存PostgreSQLのバックアップを取得します。
2. 現在のRenderサービスの `DATABASE_URL`・`GEMINI_API_KEY` を維持し、セッションキーの保存先を確認します。現在のDietInfoサービスは既存の `/var/data` 永続ディスクを利用でき、`SECRET_KEY` 未設定時はその中に秘密のランダムキーを自動保存します。キーの再発行や新サービス作成は不要です。
3. GitHubに変更を反映します。既存のBuild Command **`bash build.sh`**、Start Command **`python -m gunicorn app:app`** はそのまま利用でき、`gunicorn.conf.py` が自動読み込みされます。
4. `gunicorn.conf.py` の起動フックが、ワーカー起動前にマイグレーションを実行します。`bash start.sh` を使う起動方法も用意しています。追加テーブルのみを作り、既存のテーブル・記録は削除しません。旧 `schema.sql` はDROPを含むため使用しないでください。
5. デプロイ後、公開URLでレシピ5件、ログイン、ジム・マシン、AIレシピ提案、保存・公開、成長記録を確認します。PCの電源を切っても、公開サーバーが稼働していればスマホから利用できます。

この変更をローカルに保存しただけでは、GitHubや公開サイトは更新されません。既存サービスの設定・実AI接続・本番PostgreSQLでの確認は別途必要です。HTTPSのCookie設定はRender環境で自動的に有効になります。

## BECOMEの既存記録を引き継ぐ

先に移行先のSTOIQアカウントを作成します。移行先の環境変数を確認したうえで、手元にある旧SQLite DBを読み取り専用で指定します。

```powershell
python manage.py import-become --source "C:\Users\rinse\自分磨きアプリ\prisma\dev.db" --username "移行先のユーザー名"
```

チャレンジ・習慣の実施履歴・日記・感情整理・自己評価・週次レビュー・身体記録・筋トレ詳細を、指定したアカウントに取り込みます。同じチャレンジの再取り込みはスキップします。元のDBは変更しません。ユーザー設定は移行先DBに保持します。旧レビューのスナップショットは `legacy_snapshot` として保持し、集計形式が違うため新形式の数値へ推測変換しません。習慣ログの旧メモは別途保持します。アカウント名の取り違えに注意してください。

個人のDBや日記をGitHubに含めないでください。本番へ取り込む場合は、信頼する環境から既存DBに接続してコマンドを実行します。

## 検証

```powershell
python -m pip install pytest
python -m pytest -q tests
```

ローカルSQLiteで14件成功・PostgreSQL専用1件をスキップ、独立したローカルPostgreSQL 16で15件すべて成功を確認しました。テストはGeminiのモックを使用し、実際のAI利用料金は発生しません。実APIの成功や公開中のPostgreSQLへの接続は未検証です。

PostgreSQLのテストは、専用のローカルクラスタ（127.0.0.1:55439、ユーザーstoiq_qa）を起動し、`STOIQ_TEST_POSTGRES_URL` を指定したときだけ実行できます。テストごとに専用スキーマを作成・削除します。本番データベースは使用できないよう接続先を制限しています。

ロールモデルのAI分析など、旧アプリで未完成だった機能はこの統合に自動で追加されません。食事の栄養数値は未検証の推計を表示せず、材料・分量・たんぱく質源を示しています。
