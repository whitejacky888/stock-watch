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
import glossary
import news
import candle_chart


def print_menu(settings):
    """
    メニュー(選択肢の一覧)を表示する関数。
    表示期間・表示モードは、現在の設定値をメニューの説明に表示する
    (今どうなっているかが一目で分かるようにするため)。
    """
    period_label, _ = plot_chart.PERIOD_OPTIONS[settings["period_index"]]
    mode_label = "変化率" if settings["mode"] == "percent" else "実額"

    print("")
    print("=" * 50)
    print("値動きウォッチ フェーズ6 - メニュー")
    print("=" * 50)
    print("1: ウォッチリストを表示する")
    print("2: 銘柄を追加する")
    print("3: 銘柄を非表示にする")
    print("4: 非表示中の銘柄を再表示する")
    print("5: 銘柄を削除する(完全に削除・元に戻せません)")
    print("6: データを取得してグラフを表示する")
    print("7: 表示期間を変更する(現在: " + period_label + ")")
    print("8: 表示モードを変更する(現在: " + mode_label + ")")
    print("9: 1つの銘柄だけを表示する(ソロ表示・実額表示への切り替えに便利)")
    print("10: 全ての銘柄を表示に戻す")
    print("11: 用語集を表示する")
    print("12: 用語を検索する")
    print("13: 関連ニュースを表示する")
    print("14: 詳細チャートを表示する(ローソク足・移動平均線・出来高)")
    print("0: 終了する")
    print("-" * 50)


def _format_change(diff, pct):
    """
    「前日比」「騰落率(%)」を、色付きの文字列にして返す関数。
    要件定義書 7.4節「前日比・騰落率を数値と色で分かりやすく表示する」に対応。

    日本の株価表示でよくある配色にならい、上昇=暖色(赤)、下落=寒色(青)にする
    (米国式の「上昇=緑、下落=赤」とは逆なので注意)。
    色付けには、ターミナルの「ANSIエスケープコード」という仕組みを使っている
    (VS Codeのターミナルであれば問題なく表示できるはず)。

    まだデータを取得していない銘柄の場合は diff が None になるので、
    その場合は「(データ未取得)」という文字列を返す。
    """
    if diff is None:
        return "(データ未取得。「6」でデータを取得すると表示されます)"

    sign = "+" if diff >= 0 else ""
    text = "{}{:.2f} ({}{:.2f}%)".format(sign, diff, sign, pct)

    if diff > 0:
        return "\033[31m" + text + "\033[0m"  # 赤(上昇)
    elif diff < 0:
        return "\033[34m" + text + "\033[0m"  # 青(下落)
    else:
        return text  # 変化なし(0)は色を付けない


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

    フェーズ4より、直近取得済みのデータがあれば「前日比」もあわせて
    表示するようにしました(データ未取得の場合はその旨を表示するだけで、
    ここで新たにデータ取得は行わない。取得は「6」で行う)。
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
        diff, pct = plot_chart.get_latest_change(item)
        print("      前日比: " + _format_change(diff, pct))
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


def handle_period(settings):
    """「7: 表示期間を変更する」が選ばれたときの処理。"""
    print("")
    print("表示したい期間を選んでください。")
    for i, (label, days) in enumerate(plot_chart.PERIOD_OPTIONS):
        print(str(i) + ": " + label)

    choice = ask_index("番号: ", len(plot_chart.PERIOD_OPTIONS))
    if choice is None:
        return

    settings["period_index"] = choice
    label, _ = plot_chart.PERIOD_OPTIONS[choice]
    print("表示期間を「" + label + "」に変更しました。")


def handle_mode(items, settings):
    """
    「8: 表示モードを変更する」が選ばれたときの処理。

    実額表示(要件定義書7.3節の「ソロ表示」)は、値の単位(円・pt など)が
    銘柄ごとに違うため、複数の銘柄を同時に比べるのには向いていません。
    そのため、実額表示に切り替えられるのは「表示中の銘柄がちょうど1つ」
    のときだけにしています。
    """
    visible_count = len([item for item in items if not item["hidden"]])

    print("")
    print("0: 変化率(%)で表示する(複数の銘柄を比較できる・通常はこちら)")
    print("1: 実額で表示する(表示中の銘柄が1つだけのときのみ選べます)")

    choice = ask_index("番号: ", 2)
    if choice is None:
        return

    if choice == 1 and visible_count != 1:
        print("実額表示にするには、表示中の銘柄を1つだけに絞ってください。")
        print("「9: 1つの銘柄だけを表示する(ソロ表示)」を使うと、1回の操作でまとめて切り替えられます。")
        print("(現在、表示中の銘柄が " + str(visible_count) + " 件あります)")
        return

    settings["mode"] = "absolute" if choice == 1 else "percent"
    mode_label = "実額" if choice == 1 else "変化率"
    print("表示モードを「" + mode_label + "」に変更しました。")


def handle_solo(items):
    """
    「9: 1つの銘柄だけを表示する(ソロ表示)」が選ばれたときの処理。

    実額(実際の値)表示は、表示中の銘柄がちょうど1つのときしか選べない
    仕様になっている(理由: 日経平均のような数万pt単位の指数と、
    キーコーヒーのような数千円単位の株価を同じグラフに実額で重ねると、
    小さい方の値がほぼ0円の位置に張り付いてしまい、値動きが全く
    見えなくなってしまうため)。

    これまでは、1つに絞るために他の銘柄を「3: 銘柄を非表示にする」で
    1つずつ非表示にする必要があり、登録数が多いと手間がかかっていた。
    この機能は、選んだ1件だけを表示・それ以外は全て非表示、という状態を
    一度の操作で作れるようにするショートカットです。
    (非表示にするだけなので、データや登録情報が消えることはありません。
     元に戻したいときは「10: 全ての銘柄を表示に戻す」を使ってください)
    """
    if len(items) == 0:
        print("ウォッチリストに何も登録されていません。")
        return

    print("")
    print("1つだけ表示にしたい銘柄の番号を選んでください。(選んだ銘柄以外は非表示になります)")
    for i, item in enumerate(items):
        status = "非表示" if item["hidden"] else "表示中"
        print(str(i) + ": " + item["label"] + " (" + item["symbol"] + ") [現在: " + status + "]")

    choice = ask_index("番号: ", len(items))
    if choice is None:
        return

    for i, item in enumerate(items):
        item["hidden"] = (i != choice)
    watchlist.save_watchlist(items)

    print(items[choice]["label"] + " だけを表示するようにしました(他の銘柄はすべて非表示になりました)。")
    print("続けて「8: 表示モードを変更する」で実額表示に切り替えられます。")


def handle_show_all(items):
    """
    「10: 全ての銘柄を表示に戻す」が選ばれたときの処理。
    ソロ表示などで非表示にした銘柄を、まとめて全て表示中に戻す。
    """
    if len(items) == 0:
        print("ウォッチリストに何も登録されていません。")
        return

    for item in items:
        item["hidden"] = False
    watchlist.save_watchlist(items)

    print("全ての銘柄(" + str(len(items)) + " 件)を表示に戻しました。")
    print("※ 表示モードが「実額」のままだと、次にグラフを表示するときに自動で「変化率」に切り替わります。")


def _highlight(text, keyword):
    """
    文字列 text の中で、keyword に一致する部分を目立たせて返す関数
    (ターミナルの色付け機能(ANSIエスケープコード)を使う)。
    要件定義書 7.7節「検索語に一致する箇所をハイライト表示する」に対応。

    大文字・小文字を区別せずに探すが、実際に画面に出す文字列は
    元の表記(大文字・小文字)のまま使う。
    """
    if keyword == "":
        return text

    lower_text = text.lower()
    lower_keyword = keyword.lower()

    result = ""
    i = 0
    while i < len(text):
        idx = lower_text.find(lower_keyword, i)
        if idx == -1:
            result += text[i:]
            break
        result += text[i:idx]
        matched = text[idx:idx + len(keyword)]
        result += "\033[1;33m" + matched + "\033[0m"  # 太字・黄色で強調
        i = idx + len(keyword)
    return result


def handle_glossary():
    """
    「11: 用語集を表示する」が選ばれたときの処理。
    要件定義書 7.4節(学習支援機能)に対応。
    """
    print("")
    print("=" * 60)
    print("用語集(グラフや投資でよく出てくる言葉の解説)")
    print("=" * 60)
    for term, description in glossary.GLOSSARY:
        print("■ " + term)
        print("    " + description)
    print("-" * 60)
    print(str(len(glossary.GLOSSARY)) + " 件の用語を表示しました。")


def handle_glossary_search():
    """
    「12: 用語を検索する」が選ばれたときの処理。
    要件定義書 7.7節(用語検索機能)に対応。
    """
    print("")
    keyword = input("検索したいキーワードを入力してください: ").strip()
    if keyword == "":
        print("何も入力されなかったため、検索を中止しました。")
        return

    results = glossary.search_glossary(keyword)
    print("")
    if len(results) == 0:
        print("「" + keyword + "」に一致する用語は見つかりませんでした。")
        return

    print("=" * 60)
    print("「" + keyword + "」の検索結果(" + str(len(results)) + " 件)")
    print("=" * 60)
    for term, description in results:
        print("■ " + _highlight(term, keyword))
        print("    " + _highlight(description, keyword))
    print("-" * 60)


def _hex_to_ansi_fg(hex_color):
    """
    "#e6194b" のような16進数カラーコードを、ターミナルの文字色を
    変える「ANSIエスケープコード」(24bitカラー版)に変換する関数。
    グラフの線の色(watchlist.pyのCOLOR_PALETTE)と、ニュースのタグの色を
    揃えるために使う。
    """
    hex_color = (hex_color or "").lstrip("#")
    if len(hex_color) != 6:
        return ""
    try:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
    except ValueError:
        return ""
    return "\033[38;2;{};{};{}m".format(r, g, b)


def _colorize_tag(text, hex_color):
    """
    文字列 text を、hex_color の色で色付けして返す関数。
    色が無効・取得できない場合は、色付けせずそのまま返す。
    """
    ansi_code = _hex_to_ansi_fg(hex_color)
    if ansi_code == "":
        return text
    return ansi_code + text + "\033[0m"


def handle_news(items):
    """
    「13: 関連ニュースを表示する」が選ばれたときの処理。
    要件定義書 7.6節(ニュース表示機能)に対応。

    表示中(hidden が False)の銘柄の中から、ニュースを見たい銘柄を
    選んでもらう(要件定義書の「タグをクリックして絞り込む」に相当する
    操作を、ターミナルでは番号選択で行う)。「0」を選ぶと、表示中の
    銘柄すべてのニュースをまとめて新しい順に表示する。

    ニュースはGoogleニュースの検索RSS(日本語・日本向け設定)経由で
    取得するため、追加のAPIキー登録は不要。ニュース本文の「やさしい解説」
    の自動生成は今回のバージョンでは未対応(README・要件定義書に
    将来の課題として記載)。
    """
    visible = [item for item in items if not item["hidden"]]
    if len(visible) == 0:
        print("表示中の銘柄がありません。「4: 非表示中の銘柄を再表示する」などで、")
        print("先にニュースを見たい銘柄を表示中にしてください。")
        return

    print("")
    print("ニュースを見たい銘柄を選んでください。")
    print("0: 表示中の銘柄すべてのニュースをまとめて見る")
    for i, item in enumerate(visible):
        print(str(i + 1) + ": " + item["label"] + " (" + item["symbol"] + ")")

    choice = ask_index("番号: ", len(visible) + 1)
    if choice is None:
        return

    targets = visible if choice == 0 else [visible[choice - 1]]

    print("")
    print("Googleニュース(日本語)から関連ニュースを取得しています...")
    all_news = news.fetch_news_for_tickers(targets, limit_per_ticker=5)

    if len(all_news) == 0:
        print("関連ニュースが見つかりませんでした(銘柄によってはニュースが少ない・無いことがあります)。")
        return

    print("")
    print("=" * 60)
    print("関連ニュース(" + str(len(all_news)) + " 件・新しい順)")
    print("=" * 60)
    for entry in all_news:
        tag = "[" + entry["ticker_label"] + "]"
        published_text = entry["published"].strftime("%Y-%m-%d %H:%M") if entry["published"] else "日時不明"
        print(_colorize_tag(tag, entry["ticker_color"]) + " " + entry["title"])
        print("    配信元: " + (entry["publisher"] or "不明") + " / " + published_text)
        if entry["link"]:
            print("    " + entry["link"])
        print("-" * 60)

    print("※ 見出し・配信元などはGoogleニュース経由で取得した、日本の各配信元による情報そのものです。")
    print("  分からない言葉が出てきたら、「12: 用語を検索する」で調べてみてください。")


def handle_candlestick(items, settings):
    """
    「14: 詳細チャートを表示する(ローソク足・移動平均線・出来高)」が
    選ばれたときの処理。要件定義書 7.3節・11章フェーズ6に対応。

    ローソク足は1つの銘柄の値動きを細かく見るためのグラフなので、
    複数銘柄の比較グラフ(6)とは別に、必ず1つだけ銘柄を選んでもらう。
    表示期間は「7」で設定した値をそのまま使う(この画面専用の設定は
    持たない)。移動平均線の表示ON/OFFは、選んだ都度たずねる。
    """
    if len(items) == 0:
        print("ウォッチリストに何も登録されていません。")
        return

    print("")
    print("詳細チャートを見たい銘柄を、1つ選んでください。")
    for i, item in enumerate(items):
        print(str(i) + ": " + item["label"] + " (" + item["symbol"] + ")")

    choice = ask_index("番号: ", len(items))
    if choice is None:
        return

    ticker = items[choice]

    print("")
    print("[ステップ1/2] " + ticker["label"] + " のデータを取得しています...")
    fetch_data.fetch_all([ticker])

    ma_input = input("移動平均線(" + str(candle_chart.DEFAULT_MA_DAYS) + "日)を表示しますか?(y/n): ").strip().lower()
    show_ma = (ma_input == "y")

    period_label, period_days = plot_chart.PERIOD_OPTIONS[settings["period_index"]]

    print("")
    print("[ステップ2/2] ローソク足チャートを表示します(" + period_label + "・移動平均線"
          + ("あり" if show_ma else "なし") + ")")
    candle_chart.plot_candlestick(ticker, period_days=period_days, period_label=period_label, show_ma=show_ma)


def handle_fetch_and_plot(items, settings):
    """
    「6: データを取得してグラフを表示する」が選ばれたときの処理。
    非表示中のものも含めて全件データ取得はするが、グラフに描くのは
    表示中(hidden が False)のものだけにする。
    表示期間・表示モードは、現在の settings の値を使う。
    """
    print("\n[ステップ1/2] yfinance から株価データを取得します(非表示中の銘柄も含みます)")
    fetch_data.fetch_all(items)

    visible_items = [item for item in items if not item["hidden"]]

    # 実額表示は銘柄が1つのときだけ有効。複数ある状態で実額設定のままだった場合は、
    # ここで安全のため変化率表示に切り替える(値の単位が違うものを実額で
    # 重ねて表示すると、グラフとして意味をなさないため)。
    mode = settings["mode"]
    if mode == "absolute" and len(visible_items) != 1:
        print("※ 実額表示は銘柄が1つのときだけ使えるため、今回は変化率で表示します。")
        mode = "percent"

    period_label, period_days = plot_chart.PERIOD_OPTIONS[settings["period_index"]]

    print("\n[ステップ2/2] グラフを表示します(表示中の " + str(len(visible_items)) + " 件 / "
          + period_label + " / " + ("実額" if mode == "absolute" else "変化率") + ")")
    plot_chart.plot_all(visible_items, period_days=period_days, period_label=period_label, mode=mode)


def main():
    # ウォッチリストを読み込む(初回はここで watchlist.json が自動作成される)
    items = watchlist.load_watchlist()

    # 表示設定(期間・モード)。watchlist.json とは違い、ファイルには保存せず、
    # プログラムを実行している間だけ覚えている設定にしている
    # (要件定義書では「保存する」対象として明記されていないため、
    #  ここではシンプルに「起動するたびに既定値に戻る」形にしています)。
    settings = {
        "period_index": 3,  # PERIOD_OPTIONS の3番目 = "1年"(既定値)
        "mode": "percent",  # 既定は変化率表示
    }

    while True:
        print_menu(settings)
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
            handle_fetch_and_plot(items, settings)
        elif choice == "7":
            handle_period(settings)
        elif choice == "8":
            handle_mode(items, settings)
        elif choice == "9":
            handle_solo(items)
        elif choice == "10":
            handle_show_all(items)
        elif choice == "11":
            handle_glossary()
        elif choice == "12":
            handle_glossary_search()
        elif choice == "13":
            handle_news(items)
        elif choice == "14":
            handle_candlestick(items, settings)
        elif choice == "0":
            print("終了します。")
            break
        else:
            print("0〜14の番号を入力してください。")


# このファイルを直接 "python main.py" で実行したときだけ main() を呼び出す
if __name__ == "__main__":
    main()
