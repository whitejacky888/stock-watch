"""
main.py
------------------------------------------------------------
このプログラムの「入り口(エントリーポイント)」です。

フェーズ1では「実行したら自動でデータ取得→グラフ表示して終了」という
シンプルな作りでしたが、フェーズ2では要件定義書 7.1節・7.8節に対応するために、
「番号を選んで操作する、メニュー形式」のプログラムに変わりました。

実行方法(VS Codeのターミナルで):
    python main.py

※ 実行する前に、README.md の手順に沿って仮想環境(venv)を作り、
   requirements.txt のライブラリをインストールしておいてください。
"""

import watchlist
import fetch_data
import plot_chart


def print_menu():
    """メニュー(選択肢の一覧)を表示する関数。"""
    print("")
    print("=" * 50)
    print("値動きウォッチ フェーズ2 - メニュー")
    print("=" * 50)
    print("1: ウォッチリストを表示する")
    print("2: 銘柄を追加する")
    print("3: 銘柄を非表示にする")
    print("4: 非表示中の銘柄を再表示する")
    print("5: 銘柄を削除する(完全に削除・元に戻せません)")
    print("6: データを取得してグラフを表示する")
    print("0: 終了する")
    print("-" * 50)


def show_watchlist(items):
    """
    ウォッチリストの中身を、番号付きの一覧として表示する関数。
    番号は、他のメニュー(非表示にする、削除するなど)で
    「どれを選ぶか」を指定するときにも使う。

    ※ 以前は1件を横長の表(1行)で表示していましたが、会社名や事業内容が
       長いと1行がとても横に長くなり、ターミナルの幅を超えて折り返されて
       しまい、「表示されているのに気づきにくい」状態になっていました。
       そこで、1件につき数行を使う「縦に並べる」形式に変更し、
       普通の広さのターミナルでも折り返しが起きにくいようにしています。
    """
    print("")
    print("=" * 60)
    print("ウォッチリスト一覧(全 " + str(len(items)) + " 件)")
    print("=" * 60)
    for i, item in enumerate(items):
        status = "非表示" if item["hidden"] else "表示中"
        kind_label = "指数" if item["kind"] == "index" else "個別銘柄"
        print("[{:>2}] {} / {} / {} ({})".format(i, status, kind_label, item["label"], item["symbol"]))
        print("      市場区分: " + item["market"])
        print("      事業内容: " + item["business"])
        print("-" * 60)

    company_count = watchlist.count_companies(items)
    print("個別銘柄の登録数: " + str(company_count) + " / " + str(watchlist.MAX_COMPANIES))


def ask_index(prompt, max_index):
    """
    ユーザーに番号を入力してもらい、0以上 max_index未満の整数として返す関数。
    数字以外が入力された場合や、範囲外の場合は None を返す
    (呼び出し元でエラーメッセージを出す)。
    """
    text = input(prompt).strip()
    if not text.isdigit():
        print("数字を入力してください。")
        return None

    index = int(text)
    if index < 0 or index >= max_index:
        print("その番号は一覧にありません。")
        return None

    return index


def handle_add(items):
    """
    「2: 銘柄を追加する」が選ばれたときの処理。
    証券コード(日本株)またはティッカー(米国株)を入力してもらい、
    yfinanceで会社名を確認してから、ウォッチリストに追加する。
    """
    if watchlist.count_companies(items) >= watchlist.MAX_COMPANIES:
        print("個別銘柄はすでに上限の" + str(watchlist.MAX_COMPANIES) + "社です。追加する前に、先に何か1社を削除してください。")
        return

    print("")
    print("追加したい会社の証券コード、またはティッカーシンボルを入力してください。")
    print("例: 日本株(トヨタ自動車) → 7203  /  米国株(Apple) → AAPL")
    user_input = input("証券コード・シンボル: ").strip()
    if user_input == "":
        print("何も入力されなかったため、追加を中止しました。")
        return

    symbol = watchlist.normalize_symbol(user_input)

    if watchlist.find_by_symbol(items, symbol) is not None:
        print("そのシンボル(" + symbol + ")はすでにウォッチリストに登録されています。")
        return

    print("yfinanceで " + symbol + " の情報を確認しています...")
    name = watchlist.fetch_company_name(symbol)

    if name is None:
        print("会社名を自動取得できませんでした(シンボルが誤っているか、通信の問題かもしれません)。")
        proceed = input("それでも手動で入力して追加を続けますか?(y/n): ").strip().lower()
        if proceed != "y":
            print("追加を中止しました。")
            return
        name = input("会社の表示名を入力してください: ").strip()
        if name == "":
            print("名前が入力されなかったため、追加を中止しました。")
            return
    else:
        print("見つかりました: " + name)

    # 市場区分・事業内容は、yfinanceから確実には取得できないため、
    # ユーザー自身に入力してもらう(空欄でもよいことにする)
    market = input("市場区分を入力してください(例: 東証プライム。分からなければ空欄でOK): ").strip()
    if market == "":
        market = "不明"

    business = input("事業内容を一言で入力してください(空欄でもOK): ").strip()
    if business == "":
        business = "(未入力)"

    print("")
    print("以下の内容で追加します。")
    print("  名前: " + name)
    print("  シンボル: " + symbol)
    print("  市場区分: " + market)
    print("  事業内容: " + business)
    confirm = input("よろしいですか?(y/n): ").strip().lower()
    if confirm != "y":
        print("追加を中止しました。")
        return

    ok, message = watchlist.add_company(items, symbol, name, market, business)
    print(message)


def handle_hide(items):
    """「3: 銘柄を非表示にする」が選ばれたときの処理。"""
    visible = [(i, item) for i, item in enumerate(items) if not item["hidden"]]
    if len(visible) == 0:
        print("表示中の銘柄がありません。")
        return

    print("")
    print("非表示にしたい銘柄の番号を選んでください。")
    for display_number, (real_index, item) in enumerate(visible):
        print(str(display_number) + ": " + item["label"] + " (" + item["symbol"] + ")")

    choice = ask_index("番号: ", len(visible))
    if choice is None:
        return

    real_index, item = visible[choice]
    ok, message = watchlist.set_hidden(items, real_index, True)
    print(message)


def handle_restore(items):
    """「4: 非表示中の銘柄を再表示する」が選ばれたときの処理。"""
    hidden = [(i, item) for i, item in enumerate(items) if item["hidden"]]
    if len(hidden) == 0:
        print("非表示中の銘柄はありません。")
        return

    print("")
    print("再表示したい銘柄の番号を選んでください。")
    for display_number, (real_index, item) in enumerate(hidden):
        print(str(display_number) + ": " + item["label"] + " (" + item["symbol"] + ")")

    choice = ask_index("番号: ", len(hidden))
    if choice is None:
        return

    real_index, item = hidden[choice]
    ok, message = watchlist.set_hidden(items, real_index, False)
    print(message)


def handle_remove(items):
    """
    「5: 銘柄を削除する」が選ばれたときの処理。
    基本の2指数(日経平均・NASDAQ)は削除の対象にはできない
    (watchlist.remove_company側でもチェックしているが、
     ここでも一覧に出さないことで、誤操作を防いでいる)。
    """
    companies = [(i, item) for i, item in enumerate(items) if item["kind"] == "company"]
    if len(companies) == 0:
        print("削除できる個別銘柄がありません。")
        return

    print("")
    print("削除したい銘柄の番号を選んでください。(この操作は元に戻せません)")
    for display_number, (real_index, item) in enumerate(companies):
        print(str(display_number) + ": " + item["label"] + " (" + item["symbol"] + ")")

    choice = ask_index("番号: ", len(companies))
    if choice is None:
        return

    real_index, item = companies[choice]
    confirm = input(item["label"] + " を本当に削除しますか?(y/n): ").strip().lower()
    if confirm != "y":
        print("削除を中止しました。")
        return

    ok, message = watchlist.remove_company(items, real_index)
    print(message)


def handle_fetch_and_plot(items):
    """
    「6: データを取得してグラフを表示する」が選ばれたときの処理。
    非表示中のものも含めて全件データ取得はするが、グラフに描くのは
    表示中(hidden が False)のものだけにする。
    """
    print("\n[ステップ1/2] yfinance から株価データを取得します(非表示中の銘柄も含みます)")
    fetch_data.fetch_all(items)

    visible_items = [item for item in items if not item["hidden"]]
    print("\n[ステップ2/2] グラフを表示します(表示中の " + str(len(visible_items)) + " 件)")
    plot_chart.plot_all(visible_items)


def main():
    # ウォッチリストを読み込む(初回はここで watchlist.json が自動作成される)
    items = watchlist.load_watchlist()

    while True:
        print_menu()
        choice = input("番号を選んでください: ").strip()

        if choice == "1":
            show_watchlist(items)
        elif choice == "2":
            handle_add(items)
        elif choice == "3":
            handle_hide(items)
        elif choice == "4":
            handle_restore(items)
        elif choice == "5":
            handle_remove(items)
        elif choice == "6":
            handle_fetch_and_plot(items)
        elif choice == "0":
            print("終了します。")
            break
        else:
            print("0〜6の番号を入力してください。")


# このファイルを直接 "python main.py" で実行したときだけ main() を呼び出す
if __name__ == "__main__":
    main()
