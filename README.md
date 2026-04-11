# Dietapp - AI駆動型 総合フィットネス管理アプリ

## ① 概要（Overview）
**「限られた時間と環境で、最大の結果を出すためのAIパーソナルトレーナー」**

本プロジェクトは、日々の「体重」「食事」「トレーニング」を一元管理し、ユーザーが登録したジムの設備データに基づいて、最新AI（Google Gemini API）が最適なワークアウトメニューを自動生成するWebアプリケーションです。

単なる記録アプリにとどまらず、「今日はどのマシンを使って、どう鍛えればいいか分からない」というトレーニング初心者の課題を解決します。

## ② デモ（Demo）
- **App URL:**  https://dietinfo.onrender.com 
- **紹介動画 / スクリーンショット:**
  ![トップページ](URLを記載) | ![AIメニュー提案](URLを記載)
  *※GIFアニメーションを貼るとさらに効果的です*

## ③ 背景・課題設定（Why）
**なぜこのプロジェクトを作ったのか**
私自身がトレーニングを行う中で、既存のフィットネスアプリに対して以下の不満がありました。
1. **環境のミスマッチ:** 多くのAIメニュー提案アプリは一般的な種目を提示するだけで、「自分の通っているジムにそのマシンがない」という事態が頻発する。
2. **情報の分散:** 体重管理、食事記録、トレーニング記録で別々のアプリを使うのが煩わしい。

**解決した課題**
ユーザー自身の「マイジム」とそのジムにある「マシン」を事前にデータベースに登録しておくことで、**「今いるジムの設備だけで完結するメニュー」をAIに生成させる**仕組みを構築し、実用性の高いメニュー提案を実現しました。

## ④ 機能（Features）
- **AIメニュー提案機能（Gemini API連携）**
  - → ユーザーの「対象部位」「確保できる時間」「ジムにあるマシン」を条件に、AIがその日最適なセット数と回数を即座に生成するため。
- **マイジム＆マシン登録機能（Leaflet.js 地図連携）**
  - → オープンデータ（OpenStreetMap API）から現在地周辺のジムを検索・登録し、自分専用の設備リストを作成するため。
- **部位別トレーニング記録・1RM自動計算機能**
  - → 各セットの重量と回数から1RM（最大挙上重量）を推定し、成長を可視化するため。
- **体重推移グラフ＆写真付き食事記録機能**
  - → 日々の身体の変化と摂取カロリーのバランスを視覚的に振り返るため。

## ⑤ 技術スタック（Tech Stack）
- **Frontend:** HTML5, CSS3, JavaScript (Vanilla)
  - → 外部CSSフレームワークに依存せず、Flexbox/Gridを用いたモダンなレイアウトと、モチベーションを高める「サイバー・ネオン風ダークUI」をフルスクラッチで実装しました。
- **Backend:** Python 3, Flask
  - → 軽量かつルーティング設計が直感的であり、AIモデル（Gemini API）との非同期連携をシンプルに実装できるため採用しました。
- **Database:** SQLite
  - → RDBMSを用いたデータモデリング（User, Gym, Machine, TrainingSession等）の基礎を固め、トランザクション処理を確実に行うため。
- **External API:** Google Gemini 2.5 Flash API, OpenStreetMap API (Nominatim)

## ⑥ 工夫点・設計（Key Points）
- **AIプロンプトエンジニアリングの最適化**
  AIが冗長な挨拶や解説を出力しないよう、「あなたはプロのトレーナー」「以下の形式を厳守」といった強い制約とFew-Shot（出力例）をプロンプトに組み込み、UIに綺麗に収まる実用的なテキストのみを出力させるよう工夫しました。
- **MVCアーキテクチャを意識したルーティング設計**
  画面表示（GET）とデータ登録処理（POST）の責務をエンドポイントレベルで明確に分離し、二重送信防止（PRGパターン）やエラー時の安全なリダイレクト処理を実装しました。
- **没入感を高めるUI/UXデザイン**
  「ジムに行く前のモチベーション向上」をコンセプトに、ダークトーンの背景と`box-shadow`を駆使した自作のネオンエフェクトを採用。スマホでの利用を想定し、フォームのタップ領域を大きく取ったレスポンシブ設計にしています。

## ⑦ 苦労した点と解決方法（Challenges）
- **地図API連携とバックエンド間のデータ受け渡し**
  **課題:** Leaflet.jsを使ったフロントエンドの地図クリックイベントから取得した緯度・経度データを、いかにしてFlaskのバックエンドに渡し、SQLiteに保存するかが壁でした。
  **解決:** JavaScriptでクリックイベントをリッスンし、取得した座標を非表示の`<input type="hidden">`の`value`に動的にセットする手法を採用。`name`属性とFlaskの`request.form.get()`のキーを厳密に一致させることで、シームレスなデータ連携を実現しました。

- **リレーショナルデータベースの整合性維持**
  **課題:** 開発途中でテーブル構造を変更した際、既存データとの不整合による`Internal Server Error (500)`が頻発しました。
  **解決:** `CREATE TABLE IF NOT EXISTS`を用いた冪等性のあるスキーマ定義に修正し、外部キー制約（`FOREIGN KEY`）を適切に設定することで、ジムを削除した際に紐づくマシンデータも整合性を保って削除されるよう設計を見直しました。

## ⑧ 今後の改善（Future Work）
- [ ] 登録した食事の画像からカロリーを自動推計する機能（Vision APIの導入）
- [ ] トレーニング図鑑（Gif動画でのフォーム解説）ページの追加
- [ ] 高タンパク質レシピのシェア機能（ユーザー間コミュニティ機能）
- [ ] SQLiteからPostgreSQLへの移行と、AWS/GCPへの本格的なデプロイ

## ⑨ 使い方（Usage）
ローカル環境での実行方法です。

```bash
# 1. リポジトリのクローン
git clone [https://github.com/yourusername/diet-app.git](https://github.com/yourusername/diet-app.git)
cd diet-app

# 2. 仮想環境の作成と有効化
python -m venv .venv
# Windows: .venv\Scripts\activate
# Mac/Linux: source .venv/bin/activate

# 3. 依存関係のインストール
pip install -r requirements.txt

# 4. 環境変数の設定 (Gemini APIキー)
# Windows: set GEMINI_API_KEY="your_api_key_here"
# Mac/Linux: export GEMINI_API_KEY="your_api_key_here"

# 5. データベースの初期化
flask init-db

# 6. アプリケーションの起動
flask run

ディレクトリ構成
diet-app/
├── app.py                 # Flaskメインアプリケーション・ルーティング
├── schema.sql             # データベースのテーブル定義
├── requirements.txt       # Python依存パッケージ一覧
├── static/
│   ├── css/
│   │   ├── style.css      # 全体共通・トップページ用（ネオンUI）
│   │   ├── meal.css       # 食事記録用スタイル
│   │   └── training.css   # トレーニング記録用スタイル
│   └── uploads/           # 食事画像などの保存先
└── templates/             # Jinja2 HTMLテンプレート
    ├── layout.html        # 全体共通のヘッダー・ナビゲーション
    ├── index.html         # トップページ
    ├── login.html / register.html # 認証系
    ├── mypage.html        # ダッシュボード
    ├── weight.html / meal.html / training.html # 記録系
    ├── gym_register.html  # 地図連携（Leaflet.js）
    ├── gym_detail.html    # マシン管理
    └── recommend.html     # AIメニュー提案
