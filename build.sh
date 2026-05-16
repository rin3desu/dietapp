#!/usr/bin/env bash
# 依存関係のインストール
pip install -r requirements.txt

# ★ここを追記：デプロイされるたびに自動でDBを初期化する
flask init-db