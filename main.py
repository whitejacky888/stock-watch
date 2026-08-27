"""
main.py
------------------------------------------------------------
このプログラムの「入り口(エントリーポイント)」です。
これを実行すると、
  ① fetch_data.py でyfinance経由から株価データを取得
  ② plot_chart.py でグラフを表示
という2つの処理をまとめて、順番に行います。

実行方法(VS Codeのターミナルで):
    python main.py

※ 実行する前に、README.md の手順に沿って仮想環境(venv)を作り、
   requirements.txt のライブラリをインストールしておいてください。
"""

import fetch_data
import plot_chart


def main():
    print("=" * 50)
    print("値動きウォッチ フェーズ1試作 - 開始")
    print("=" * 50)

    print("\n[ステップ1/2] yfinance から株価データを取得します")
    fetch_data.fetch_all()

    print("\n[ステップ2/2] グラフを表示します")
    plot_chart.plot_all()

    print("\n" + "=" * 50)
    print("終了しました")
    print("=" * 50)


# このファイルを直接 "python main.py" で実行したときだけ main() を呼び出す
if __name__ == "__main__":
    main()
