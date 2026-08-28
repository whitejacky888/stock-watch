#!/bin/bash
# ==============================================================
# start_app.sh
# ------------------------------------------------------------
# 値動きウォッチ(Web版)を起動して、ブラウザで自動的に開くための
# スクリプトです。デスクトップのアイコンから、このスクリプトを
# 実行する想定です(README.md参照)。
# ==============================================================

# このスクリプト自身がある場所(stock-watchフォルダ)に移動する
cd "$(dirname "$0")" || exit 1

# 仮想環境(venv)があれば有効にする
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

URL="http://127.0.0.1:5000"

# すでにWebアプリが起動していないか確認する
if curl -s "$URL" > /dev/null 2>&1; then
    echo "すでに起動しているようです。ブラウザを開きます。"
else
    echo "値動きウォッチ(Web版)を起動しています..."
    nohup python3 app.py > app.log 2>&1 &

    # 起動するまで少し待つ(最大10秒)
    for i in $(seq 1 20); do
        if curl -s "$URL" > /dev/null 2>&1; then
            break
        fi
        sleep 0.5
    done
fi

# 既定のブラウザで開く
xdg-open "$URL" > /dev/null 2>&1 &
