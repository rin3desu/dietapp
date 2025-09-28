#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

# flaskコマンドをpythonモジュールとして呼び出すように変更
python -m flask init-db