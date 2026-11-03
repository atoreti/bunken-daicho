# -*- coding: utf-8 -*-
# 部品の版(uv run で走らせると、uv がこの版を、使う人の PC の Python を変えずに用意する。python で打っても動く)
# /// script
# requires-python = ">=3.10"
# dependencies = ["pymupdf==1.27.2.3"]
# ///
"""kensaku.py・shoshi.py・kiroku.py の試験。uv run test_scripts.py で走らせる(標準ライブラリ+PyMuPDF・ネットには出ない)。

見ること(課題 ch-f5x.3・claude-harness の D55):
(1) 検索の記録: 語・DB・件数・一覧に出た数・新しい候補の数が1行に残る/失敗も1行/件数の表示が無い時は0件にしない
(2) J-STAGE: 間を空ける/切られたら、その回はもう投げない(投げなかったことも1行)
(3) 候補の一覧: 同じ文献を DOI・crid・題名+第一著者+年で1つにまとめる/別の検索で再び出たら経路を足す
(4) 判定: 採るには行番号・落とすには理由と決め手(30字まで)・保留には何が決まらないか/同じ行を2つの候補が採れない
(5) 帳尻: 見た=採った+落とした・保留の割合・未判定の数を一覧から数え、台帳の節を書き換える
(6) 突き合わせ: 台帳の行と「採った」・台帳の帳尻と一覧から数えた物・手で直した記録で止まる/NDLサーチの API・KAKEN を使ったのに
    探索記録に「使ったAPIと出典」の行が無いと止まる(課題 ch-9sm)
(7) 書誌の項目ファイル: 形の検査・書誌欄の書き方・台帳への書き込み・手で直した書誌欄で止まる
(8) 走行の記録: 論点の案と承認後の差・検索と候補の数・失敗した検索が未知の箱へ・手応えを後から足す
(9) 試験が効いているか(確かめを外すと、壊した物が通ってしまう)
(10) 抜き書きの場所(nukigaki.py・課題 ch-f5x.9・D64): 頁を出す/言い換えは見つからない/「…」の区切りは順に/負号を落とした写しは見つからない/
     刷りの頁と書誌の頁の食い違いを知らせる/文字の無い本文で止まる/負号の確かめを外すと壊した物が通る
(11) アプリケーション ID と KAKEN(課題 ch-e0n): CiNii・KAKEN にだけ ID を付ける/記録・一覧・画面に ID が残らない(応答・失敗の説明に
     混ざっても伏せる)/ID が無い・英数字だけの形でない時は投げずに止める/KAKEN の応答を読み、研究課題を課題の番号でまとめる/
     伏せ・形の確かめ・止まりを外すと壊した物が通る。ID は作り物を環境変数に入れて試す(本物の ID は使わない)
(12) 台帳の JSON(daicho.py・課題 ch-f5x.6・D67): 部分の JSON を確かめて入れる/選べない語・縦棒・抜き書きの無い行・
     精読と読めた範囲の食い違い・スクリプトが書く欄は入れない/候補の一覧から帳尻・行の論点・限界・方法の下書きを書く/
     HTML は台帳のフォルダ、Markdown は作業用フォルダ/Markdown は今の台帳と同じ形で、kensaku.py・shoshi.py の突き合わせを通る/
     チェッカーの申告を写さずに取り込む/要る行だけを抜き出す/写し直すと同じ Markdown になる/確かめを外すと壊した物が通る
(13) 確かめの回(kaime.py・課題 ch-f5x.7・D71): 回ごとに台帳の写し・確かめ役に渡す物を残し、結果を上書きしない/順に進める/
     前の回に直す指摘が無ければ次の回を作らない/指摘の外の行・書誌の項目が変わったら写さずに止まる(消した・足した行も)/
     結果が読めない時は合格にしない/最良版(通った最後の回。最後の回が通らなくても、通らない訳の行を通った回より後に直していなければ
     最後の回。通った回が無ければ点の高い回・同じ点なら後の回。D78)を決め、違えば台帳を戻す/
     書誌突合の1行の材料を出す/確かめは3回まで/指摘の外の確かめを外すと壊した物が通る
(14) 工程7 の追記の提案の確かめ(teian.py・課題 ch-hz0・D73): 言葉を付けた提案には見たページが要る/確かめに出した後は足さない/
     言葉ごとに回数を数える(全角と半角の括弧・タグの中の印)/J-STAGE は間をあけ、切られたら開かない/Google Scholar は開かない/
     確かめ役が通ったとしても、言葉が0回・根拠の字がページに無い・開き直していない提案は足せる提案にしない/結果が読めない・
     保存した中身や記録を書き換えた時は止まる/CiNii の ID を中身と記録に残さない/回数と根拠の確かめを外すと壊した物が通る
(15) 英語のデータベース(課題 ch-4f2・D75): OpenAlex・Semantic Scholar・arXiv・Crossref に語・年・件数を付けて送り、記録と
     候補の一覧に入れる/OpenAlex のキーは要求の欄にだけ入れ、URL・記録・画面に残さない(形の違う値は送らない)/1日の枠が尽きたら
     その日はもう送らない/一時的な断りは2・4・8秒で3回まで/arXiv は3秒あける/撤回された論文は採れない/arXiv の番号でまとめる/
     抄録を出どころと一緒に保存する/Semantic Scholar を使ったら出典の行を求める/枠の見分けと伏せを外すと壊した物が通る
(16) 同じ作業用フォルダを2つの処理が同時に使う(課題 ch-4f2 の試し): 答えを待つ間に別の処理が書いても番号がぶつからない/
     札を持つ処理が終わらなければ待った末に止まる/送る前に読んだ一覧で番号を付けると壊れる
(13 の続き) 機械の照らし(課題 ch-jxl・ch-gya): 確かめ役が原典から写した書誌と台帳の書誌を1字ずつ照らし、合わないのに指摘に無い項目・
     根拠を挙げていない要旨の箇条・CiNii で確かめた全文OA を重大に足す/点は観点の点から数え直す/原典の控えの置き場を渡し、
     台帳の置き場にファイルが増えたら止まる/写した書誌の無い結果は読めない/照らしを外すと壊した物が通る
(18) 本文の置き場を開いた記録(honbun.py・課題 ch-3ni の2回目の直し): 開いて保存し、頁の数と文字の取れない頁を残す/文字の取れない頁を
     画像にせずに本文精読済みは通さない/200頁に満たない本文の「200頁以上」は通さない/本文の無い置き場・開けなかった置き場は記録どおりの
     訳なら通す/J-STAGE に切られた後は開かない/照らしを外すと壊した物が通る
(17) 読み切っていない行・論点の承認・測れなかった物の例外(課題 ch-3ni・ch-21p・ch-2pi): 全文OA なのに抄録どまりの行と、無料の置き場が
     あるのに未入手の行は、訳が無いと入れない・作らない/論点の案・承認か未承認の記録・頭の部分の「(未承認)」が食い違うと作らず、
     未承認の時はチャットに見せる文を出す/チェッカーの測れなかった物が、断られた行と抄録に在る英語の行だけなら納めてよい、
     段階B・違反・和文の行・抄録に無い抜き書き・備考の無い 403 は例外にしない/照らしを外すと壊した物が通る
"""
import contextlib
import io
import json
import os
import re
import shutil
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import daicho  # noqa: E402
import kensaku  # noqa: E402
import kiroku  # noqa: E402
import kyotsu  # noqa: E402
import kaime  # noqa: E402
import nukigaki  # noqa: E402
import honbun  # noqa: E402
import shoshi  # noqa: E402
import teian  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
RESULTS = []
TMP = tempfile.mkdtemp(prefix="bunken-scripts-test-")


def ok(cond, name):
    RESULTS.append(bool(cond))
    print("  [%s] %s" % ("OK" if cond else "NG", name))


def run(mod, *argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = mod.main(list(argv))
    return code, buf.getvalue()


def wdir(name):
    return os.path.join(TMP, name)


# ---- 作り物の応答(形は 2026-10-20 に実物で確かめた物に合わせた) ----

def cinii_json(total, items):
    return json.dumps({"opensearch:totalResults": str(total), "items": items}, ensure_ascii=False)


def cinii_item(crid, title, creator, journal, year, doi=None):
    it = {"@id": "https://cir.nii.ac.jp/crid/%s" % crid, "title": title, "dc:creator": [creator],
          "prism:publicationName": journal, "prism:publicationDate": year, "dc:type": "Article",
          "dc:identifier": [{"@type": "cir:NAID", "@value": "1"}]}
    if doi:
        it["dc:identifier"].append({"@type": "cir:DOI", "@value": doi})
    return it


def jstage_li(path, title, author, journal, year, vol, iss, doi):
    return ('<li><div class="searchlist-title"><a href="https://www.jstage.jst.go.jp/article/%s/_article/-char/ja" '
            'class="bluelink-style customTooltip" title="%s" >%s</a></div>'
            '<div class="searchlist-authortags customTooltip" title="%s">%s</div>'
            '<div class="searchlist-additional-info"><a href="https://www.jstage.jst.go.jp/browse/x/-char/ja" '
            'class="bluelink-style" >%s</a> <br> %s年 %s 巻 %s 号 p. 1-6 <br></div>'
            '<div class="result-doi-wrap"><span class="doi-icn">DOI</span><a href="https://doi.org/%s" '
            'class="bluelink-style">https://doi.org/%s</a></div>'
            '<div class="global-tags"><span class="tags-wrap freeaccess-tag-style" title="フリー">フリー</span></div></li>'
            % (path, title, title, author, author, journal, year, vol, iss, doi, doi))


def jstage_page(total, lis):
    head = '<span class="result-count">%d件中 1-%d の結果を表示しています</span>' % (total, len(lis)) if total is not None else ""
    return "<html>%s<ul>%s</ul></html>" % (head, "".join(lis))


NDL_RSS = """<rss xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:openSearch="http://a9.com/-/spec/opensearchrss/1.0/"
 xmlns:dcndl="http://ndl.go.jp/dcndl/terms/" xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#"
 xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
 xmlns:dcterms="http://purl.org/dc/terms/" version="2.0"><channel><title>t</title>
<openSearch:totalResults>55</openSearch:totalResults>
<item><title>空き家バンク制度の分析と展開</title><link>https://ndlsearch.ndl.go.jp/books/R000000004-I026572005</link>
<dc:title>空き家バンク制度の分析と展開</dc:title><dc:creator>霜垣 慎治</dc:creator>
<rdfs:seeAlso rdf:resource="https://cir.nii.ac.jp/crid/999"/>
<dc:description>掲載誌：都市問題 / 東京市政調査会 106(6) p.40-49</dc:description></item>
</channel></rss>"""


class FakeNet:
    def __init__(self, answers):
        self.answers = list(answers)
        self.urls = []

    def __call__(self, url, timeout):
        self.urls.append(url)
        if not self.answers:    # 投げないはずの問い合わせが来た(試験を落ちさせず、NG として数えるため失敗を返す)
            return None, "shippai", "試験: 用意の無い問い合わせ"
        return self.answers.pop(0)


@contextlib.contextmanager
def net(answers):
    fake = FakeNet(answers)
    old_f, old_s = kensaku.fetch, kensaku.time.sleep
    slept = []
    kensaku.fetch = fake
    kensaku.time.sleep = lambda s: slept.append(s)
    try:
        yield fake, slept
    finally:
        kensaku.fetch, kensaku.time.sleep = old_f, old_s


def logs(w):
    return (kyotsu.read_log(os.path.join(w, "kensaku.jsonl"), kensaku.KIND_S),
            kyotsu.read_log(os.path.join(w, "kouho.jsonl"), kensaku.KIND_K))


DAICHO = """# 文献台帳: 試験

- 目的: 試験
- 適合の基準: 国内の空き家の研究
- 論点1: 空き家バンクの研究
- 論点2(反論・限界): 空き家バンクが効かなかった研究
- 実行日: 2026-10-20

| # | 書誌 | 種別 | リンク | 入手状況 | アクセス日 |
|---|---|---|---|---|---|
| 1 | (後で書く) | 査読論文 | https://doi.org/10.1234/a | 全文OA | 2026-10-20 |
| 2 | (後で書く) | 紀要 | https://cir.nii.ac.jp/crid/222 | 抄録のみ | 2026-10-20 |

## 探索記録(再挑戦の起点)

今回は見つからなかった論点なし(全論点で文献を確保)

### 使ったAPIと出典
- この台帳の探索には、国立国会図書館サーチ(NDLサーチ)の API を用いた。
"""


def chojiri_lines(text):
    """台帳の「## 選別の帳尻」の節の箇条書き(ヘッダーの論点の行と混ぜない)"""
    ls = text.split("\n")
    st = ls.index("## 選別の帳尻")
    end = next((i for i in range(st + 1, len(ls)) if ls[i].startswith("## ")), len(ls))
    return [ln for ln in ls[st + 1:end] if ln.startswith("- ")]


def part_kensaku():
    print("(1)〜(6) 検索の記録・候補の一覧・判定・帳尻・突き合わせ")
    w = wdir("k1")
    items = [cinii_item("111", "空き家バンクの研究", "中川 訓範", "地域研究", "2011", doi="10.1234/A"),
             cinii_item("222", "空き家の利活用", "山田 太郎", "紀要", "2015")]
    with net([(cinii_json(120, items), "ok", "")]) as (fake, _):
        code, out = run(kensaku, w, "sagasu", "--db", "cinii", "--hoho", "articles", "--q", "空き家バンク", "--ronten", "1")
    S, K = logs(w)
    ok(code == 0 and len(S) == 1, "(1) 検索1本で記録が1行")
    s = S[0]
    ok(s["db"] == "cinii" and s["go"] == "空き家バンク" and s["kensu"] == 120 and s["deta"] == 2 and s["atarashii"] == 2
       and s["kiroku"] == "script" and s["jotai"] == "ok" and s["ronten"] == "1",
       "(1) 語・DB・件数・一覧に出た数・新しい候補の数・論点・スクリプトの印が残る")
    ok("articles?" in fake.urls[0] and "count=20" in fake.urls[0], "(1) CiNii の論文の窓口に既定20件で投げた")
    ok([k["id"] for k in K] == ["K0001", "K0002"] and K[0]["kagi"][0] == "doi:10.1234/a",
       "(3) 候補が2件、鍵は DOI(小文字)が先頭")

    # 同じ文献が J-STAGE から(DOI が同じ)・NDL から(crid が同じ)出る
    lis = [jstage_li("x/57/1/57_1", "空き家バンクの研究", "中川 訓範", "地域研究", "2011", "57", "1", "10.1234/a"),
           jstage_li("x/58/1/58_9", "空き家バンクの成約", "鈴木 一郎", "地域研究", "2016", "58", "1", "10.1234/b")]
    with net([(jstage_page(2, lis), "ok", "")]) as (fake, slept):
        code, out = run(kensaku, w, "sagasu", "--db", "jstage", "--hoho", "title", "--q", "空き家バンク", "--ronten", "2",
                        "--until", "2020")
    S, K = logs(w)
    ok(code == 0 and S[-1]["atarashii"] == 1 and S[-1]["deta"] == 2, "(3) DOI が同じ文献は新しい候補にしない")
    mata = [k for k in K if k["type"] == "mata"]
    ok(len(mata) == 1 and mata[0]["id"] == "K0001" and mata[0]["ronten"] == "2", "(3) 再び出た候補に経路(検索と論点)を足す")
    ok("item=2" in fake.urls[0] and "yearto=2020" in fake.urls[0], "(1) J-STAGE の題名の検索で年を絞った")
    nd = NDL_RSS.replace("https://cir.nii.ac.jp/crid/999", "https://cir.nii.ac.jp/crid/222")
    with net([(nd, "ok", "")]):
        code, out = run(kensaku, w, "sagasu", "--db", "ndl", "--q", "空き家バンク", "--ronten", "1")
    S, K = logs(w)
    ok(code == 0 and S[-1]["kensu"] == 55 and S[-1]["atarashii"] == 0, "(3) NDL の記録が CiNii の crid を持つ時は同じ文献にまとめる")
    # 題名+第一著者+年でまとめる(DOI も crid も無い)
    lis2 = [jstage_li("y/1/1/1_1", "空き家の利活用", "山田 太郎", "紀要", "2015", "1", "1", "10.9999/zz")]
    with net([(jstage_page(1, lis2), "ok", "")]) as (_f, slept):
        run(kensaku, w, "sagasu", "--db", "jstage", "--hoho", "abst", "--q", "空き家 利活用", "--ronten", "1")
    S, K = logs(w)
    ok(S[-1]["atarashii"] == 0, "(3) 題名+第一著者+年が同じなら同じ文献にまとめる")
    ok(slept and slept[0] > 0, "(2) J-STAGE は前に投げてから間を空ける")

    # 件数の表示が無い(J-STAGE の詳細検索の画面が返った)
    with net([(jstage_page(None, []), "ok", "")]):
        code, out = run(kensaku, w, "sagasu", "--db", "jstage", "--hoho", "title", "--q", "冷や汁", "--ronten", "1")
    S, _ = logs(w)
    ok(code == 0 and S[-1]["jotai"] == "kensu_nashi" and S[-1]["kensu"] is None and "0件と読まない" in out,
       "(1) 件数の表示が無い時は0件にせず「件数の表示なし」として残す")
    # 失敗
    with net([(None, "shippai", "HTTP 503")]):
        code, out = run(kensaku, w, "sagasu", "--db", "cinii", "--q", "空き家", "--ronten", "2")
    S, _ = logs(w)
    ok(code == 3 and S[-1]["jotai"] == "shippai" and "HTTP 503" in S[-1]["keikoku"], "(1) 失敗した検索も1行残し、終わりの値 3")
    # J-STAGE に切られる → その回はもう投げない
    with net([(None, "kirareta", "接続を切られた(ConnectionResetError)")]):
        code, out = run(kensaku, w, "sagasu", "--db", "jstage", "--q", "空き家", "--ronten", "2")
    ok(code == 3 and "もう投げない" in out, "(2) 切られたら知らせる")
    with net([]) as (fake, _):
        code, out = run(kensaku, w, "sagasu", "--db", "jstage", "--q", "空き家 活用", "--ronten", "2")
    S, _ = logs(w)
    ok(code == 3 and fake.urls == [] and S[-1]["jotai"] == "yameta", "(2) 切られた後は投げず、投げなかったことも1行残す")
    ok(len(S) == 8, "(1) 8本の検索(失敗・投げなかったを含む)が8行")

    # 手で記録・手で足す
    code, out = run(kensaku, w, "te", "--db", "cinii", "--q", "空き家", "--ronten", "1", "--kensu", "3")
    ok(code == 2, "(1) スクリプトで扱える DB を手で記録するなら理由(--memo)が要る")
    code, out = run(kensaku, w, "te", "--db", "estat", "--q", "空き家バンク", "--ronten", "2", "--kensu", "32")
    S, _ = logs(w)
    ok(code == 0 and S[-1]["kiroku"] == "te" and S[-1]["kensu"] == 32, "(1) e-Stat を手で記録すると「手で記録」の印")
    code, out = run(kensaku, w, "tsuika", "--ronten", "2", "--dai", "空き家バンクは効いたか", "--url",
                    "https://example.ac.jp/records/5", "--keiro", "#1の引用文献より", "--kensaku", S[-1]["id"],
                    "--chosha", "佐藤 花子", "--nen", "2019")
    _, K = logs(w)
    ok(code == 0 and K[-1]["kiroku"] == "te" and K[-1]["keiro"] == "#1の引用文献より", "(3) 一覧に出ない候補を経路つきで足す")
    code, out = run(kensaku, w, "ichiran")
    l1 = next((ln for ln in out.split("\n") if ln.startswith("K0001 |")), "")
    ok("cir.nii.ac.jp/crid/111" in l1 and "doi:10.1234/a" in l1,
       "(3) 一覧の行は、URL が CiNii のページでも、分かっている DOI を出す(DOI で候補を探せるように)")

    # 判定
    ids = ["K0001", "K0002", "K0003", "K0004"]
    ok(run(kensaku, w, "kime", "K0001", "sai")[0] == 2, "(4) 採るには行番号が要る")
    ok(run(kensaku, w, "kime", "K0003", "otosu", "--riyuu", "4")[0] == 2, "(4) 落とすには決め手の事実が要る")
    ok(run(kensaku, w, "kime", "K0003", "otosu", "--riyuu", "4", "--kimete", "あ" * 31)[0] == 2, "(4) 決め手の事実は30字まで")
    ok(run(kensaku, w, "kime", "K0003", "otosu", "--riyuu", "9", "--kimete", "x")[0] == 2, "(4) 理由は1〜5")
    ok(run(kensaku, w, "kime", "K0004", "horyu")[0] == 2, "(4) 保留には何が決まらないかが要る")
    run(kensaku, w, "kime", "K0001", "sai", "--gyou", "1")
    ok(run(kensaku, w, "kime", "K0003", "sai", "--gyou", "1")[0] == 2, "(4) 同じ行を2つの候補が採れない")
    run(kensaku, w, "kime", "K0002", "sai", "--gyou", "2")
    run(kensaku, w, "kime", "K0003", "otosu", "--riyuu", "4", "--kimete", "対象が台湾の都市")
    run(kensaku, w, "kime", "K0004", "horyu", "--kimete", "本文PDFが開けない")
    code, out = run(kensaku, w, "kime", "K0004", "otosu", "--riyuu", "3", "--kimete", "本文PDFが開けない")
    ok(code == 0 and "置き換えた" in out, "(4) 判定は後から置き換えられ、置き換えたと言う")
    run(kensaku, w, "kime", "K0004", "horyu", "--kimete", "本文PDFを後で試す")

    # 帳尻
    d = os.path.join(w, "daicho.md")
    kyotsu.write_text(d, DAICHO)
    code, out = run(kensaku, w, "chojiri", "--daicho", d)
    text = open(d, encoding="utf-8").read()
    ok(code == 0 and text.index("## 選別の帳尻") < text.index("## 探索記録"), "(5) 帳尻の節を探索記録の前に入れる")
    l1 = next(ln for ln in chojiri_lines(text) if ln.startswith("- 論点1:"))
    l2 = next(ln for ln in chojiri_lines(text) if ln.startswith("- 論点2(反論・限界):"))
    ok("一覧に出た 2件 / 見た 2件 / 採った 2件(#1・#2) / 落とした 0件" in l1 and "未判定 0件" in l1,
       "(5) 論点1: 一覧・見た・採った(行番号)・未判定を数える(見た=採った+落とした)")
    ok("一覧に出た 3件 / 見た 2件 / 採った 1件(#1) / 落とした 1件(④別の対象 1) / 保留 1件(保留の割合 33%)" in l2
       and "手で記録 1" in l2 and "失敗・件数なし 3" in l2,
       "(5) 論点2: 別の論点で採った候補も数え、保留の割合・手で記録・失敗の数を出す")
    ok("ヒット計 176件" in l1 and "ヒット計 34件" in l2,
       "(5) ヒット計は件数のある検索だけを足す(120+55+1。件数の表示なしは足さない / 2+32)")
    lz = next(ln for ln in chojiri_lines(text) if ln.startswith("- 全体"))
    ok("一覧に出た 4件(うち手で足した 1) / 見た 3件 / 採った 2件 / 落とした 1件 / 保留 1件 / 未判定 0件" in lz,
       "(5) 全体は重なりを除いて数える(数の引き算: 一覧 → 見た → 採った)")
    code, out = run(kensaku, w, "tashikame", "--daicho", d)
    ok(code == 0 and "食い違いなし" in out, "(6) 書いた直後は食い違いなし")
    no_ndl = text.replace("- この台帳の探索には、国立国会図書館サーチ(NDLサーチ)の API を用いた。\n", "")
    kyotsu.write_text(d, no_ndl)
    code, out = run(kensaku, w, "tashikame", "--daicho", d)
    ok(code == 1 and "NDLサーチの API が答えを返した検索があるのに" in out and "KAKEN" not in out,
       "(6) NDLサーチの API を使ったのに探索記録に明記の行が無いと止まる(KAKEN を使っていなければ KAKEN の行は求めない)")
    keep = kensaku.shussho_iru
    kensaku.shussho_iru = lambda S, cands: []
    try:
        ok(run(kensaku, w, "tashikame", "--daicho", d)[0] == 0, "(9) 出典の行の確かめを外すと、明記の無い台帳が通る(上の試験が効いている)")
    finally:
        kensaku.shussho_iru = keep
        kyotsu.write_text(d, text)

    # 帳尻を手で直す → 止まる
    kyotsu.write_text(d, text.replace("採った 2件(#1・#2)", "採った 3件(#1・#2・#3)"))
    code, out = run(kensaku, w, "tashikame", "--daicho", d)
    ok(code == 1 and "帳尻が、候補の一覧から数えた物と違う" in out, "(6) 手で直した帳尻で止まる")
    # 台帳に一覧から採っていない行
    t3 = text.replace("| 2 | (後で書く) | 紀要 | https://cir.nii.ac.jp/crid/222 | 抄録のみ | 2026-10-20 |",
                      "| 2 | (後で書く) | 紀要 | https://cir.nii.ac.jp/crid/222 | 抄録のみ | 2026-10-20 |\n"
                      "| 3 | x | 紀要 | https://e.jp/3 | 未入手 | 2026-10-20 |")
    kyotsu.write_text(d, t3)
    code, out = run(kensaku, w, "tashikame", "--daicho", d)
    ok(code == 1 and "#3 は、候補の一覧のどの候補からも採られていない" in out, "(6) 一覧から採っていない台帳の行で止まる")
    t4 = text.replace("| 2 | (後で書く) | 紀要 | https://cir.nii.ac.jp/crid/222 | 抄録のみ | 2026-10-20 |\n", "")
    kyotsu.write_text(d, t4)
    code, out = run(kensaku, w, "tashikame", "--daicho", d)
    ok(code == 1 and "台帳に #2 の行が無い" in out, "(6) 「採った」の行が台帳に無いと止まる")
    kyotsu.write_text(d, text)
    # 記録を手で直す → 止まる
    pk = os.path.join(w, "kouho.jsonl")
    raw = open(pk, encoding="utf-8").read()
    kyotsu.write_text(pk, raw.replace("対象が台湾の都市", "対象が台湾の農村"))
    code, out = run(kensaku, w, "tashikame", "--daicho", d)
    ok(code == 1 and "指紋がつながらない" in out, "(6) 手で直した候補の一覧で止まる")
    kyotsu.write_text(pk, raw)
    lines = raw.strip("\n").split("\n")
    kyotsu.write_text(pk, "\n".join(lines[:-2] + lines[-1:]) + "\n")
    code, out = run(kensaku, w, "tashikame", "--daicho", d)
    ok(code == 1 and "指紋がつながらない" in out, "(6) 行を消した候補の一覧で止まる")
    kyotsu.write_text(pk, raw)
    ok(run(kensaku, w, "tashikame", "--daicho", d)[0] == 0, "(9) 恒等対照: 戻せば通る")
    # 試験が効いているか: 突き合わせの帳尻の比べを外すと、手で直した帳尻が通る
    old = kensaku.tally
    kyotsu.write_text(d, text.replace("採った 2件(#1・#2)", "採った 3件(#1・#2・#3)"))
    kensaku.tally = lambda *a, **k: chojiri_lines(open(d, encoding="utf-8").read())
    try:
        ok(run(kensaku, w, "tashikame", "--daicho", d)[0] == 0, "(9) 数え直しを外すと手で直した帳尻が通る(=比べが効いている)")
    finally:
        kensaku.tally = old
        kyotsu.write_text(d, text)


def part_shoshi():
    print("(7) 書誌の項目ファイル")
    w = wdir("s1")
    os.makedirs(w, exist_ok=True)
    f = os.path.join(w, "daicho.shoshi.json")
    base = ["--kakunin-url", "https://doi.org/10.1234/a", "--kakunin-hi", "2026-10-20"]
    code, out = run(shoshi, f, "tsuika", "--n", "1", "--chosha", "平原 幸輝", "--nen", "2022", "--dai", "空き家率に基づく社会地図分析",
                    "--shi", "都市計画論文集", "--maki", "57", "--gou", "1", "--peji", "1-6", "--doi", "10.1234/a", *base)
    ok(code == 0 and "平原 幸輝(2022)「空き家率に基づく社会地図分析」都市計画論文集 57(1), 1-6" in out,
       "(7) 論文の書誌欄= 著者(年)「題」誌名 巻(号), 頁")
    ok(run(shoshi, f, "tsuika", "--n", "2", "--chosha", "山田 太郎", "--nen", "15", "--dai", "x", "--shi", "y", *base)[0] == 1,
       "(7) 年が4桁でない行は入れない")
    ok(run(shoshi, f, "tsuika", "--n", "2", "--chosha", "山田 太郎", "--nen", "2015", "--dai", "x", "--shi", "y")[0] == 1,
       "(7) 確かめたページと日付(kakunin)の無い行は入れない")
    ok(run(shoshi, f, "tsuika", "--n", "2", "--chosha", "山田 太郎", "--nen", "2015", "--dai", "a|b", "--shi", "y", *base)[0] == 1,
       "(7) 縦棒を含む項目は入れない(表が壊れる)")
    ok(run(shoshi, f, "tsuika", "--n", "2", "--shurui", "hon", "--chosha", "中川 寛子", "--nen", "2015", "--dai", "解決!空き家問題",
           *base)[0] == 1, "(7) 図書には出版社が要る")
    run(shoshi, f, "tsuika", "--n", "2", "--chosha", "山田 太郎", "--nen", "2015", "--dai", "空き家の利活用", "--fukudai", "A市の例",
        "--shi", "紀要", "--gou", "12", "--peji", "3-9", *base)
    r = shoshi.load(f)["rows"][1]
    ok(shoshi.render(r) == "山田 太郎(2015)「空き家の利活用：A市の例」紀要 12号, 3-9", "(7) 副題と号だけの書き方")
    ok(shoshi.render({"shurui": "hon", "chosha": ["中川 寛子"], "nen": "2015", "dai": "解決!空き家問題", "shuppan": "筑摩書房"})
       == "中川 寛子(2015)『解決!空き家問題』筑摩書房", "(7) 図書= 著者(年)『書名』出版社")
    ok(shoshi.render({"chosha": ["Alnes, P. K.", "Smith, J."], "nen": "2020", "dai": "Rural homes", "shi": "J. Rural", "maki": "3",
                      "peji": "1-9"}) == "Alnes, P. K. & Smith, J.(2020)「Rural homes」J. Rural 3, 1-9", "(7) 欧文の著者は & でつなぐ")
    d = os.path.join(w, "daicho.md")
    kyotsu.write_text(d, DAICHO)
    code, out = run(shoshi, f, "kaku", "--daicho", d)
    text = open(d, encoding="utf-8").read()
    ok(code == 0 and "| 1 | 平原 幸輝(2022)「空き家率に基づく社会地図分析」都市計画論文集 57(1), 1-6 | 査読論文 |" in text,
       "(7) 台帳の表の書誌欄を項目から書く(ほかの列はそのまま)")
    ok(run(shoshi, f, "tashikame", "--daicho", d)[0] == 0, "(7) 書いた直後は食い違いなし")
    kyotsu.write_text(d, text.replace("57(1), 1-6", "57(1), 1-9"))
    code, out = run(shoshi, f, "tashikame", "--daicho", d)
    ok(code == 1 and "#1 の書誌欄が、項目から書いた形と違う" in out, "(7) 書誌欄を手で直すと止まる")
    kyotsu.write_text(d, text.replace("| 2 | 山田", "| 3 | 山田"))
    code, out = run(shoshi, f, "tashikame", "--daicho", d)
    ok(code == 1 and "#3 が項目ファイルに無い" in out and "#2 が台帳の表に無い" in out, "(7) 台帳と項目ファイルの行がずれると止まる")
    kyotsu.write_text(d, text)
    old = shoshi.render
    kyotsu.write_text(d, text.replace("57(1), 1-6", "57(1), 1-9"))
    shoshi.render = lambda r: next(c["書誌"] for _l, n, c in kyotsu.read_daicho(d)["rows"] if n == r["n"])
    try:
        ok(run(shoshi, f, "tashikame", "--daicho", d)[0] == 0, "(9) 書き方の比べを外すと手で直した書誌欄が通る(=比べが効いている)")
    finally:
        shoshi.render = old
        kyotsu.write_text(d, text)


def part_kiroku():
    print("(8) 走行の記録・未知の箱・論点の案")
    w = wdir("k1")       # part_kensaku の作業用フォルダ(検索8本+手で記録1本)を使う
    kd = wdir("kiroku")
    code, _ = run(kiroku, "ronten", w, "shonin", "--ronten", "1=a")
    ok(code == 2, "(8) 案より先に承認は残せない")
    run(kiroku, "ronten", w, "an", "--ronten", "1=空き家バンクの研究", "--ronten", "2(反論・限界)=効かなかった研究",
        "--ronten", "3(人と場)=中心の研究者", "--kijun", "国内の空き家の研究")
    run(kiroku, "ronten", w, "shonin", "--ronten", "1=空き家バンクの研究", "--ronten", "2(反論・限界)=効かなかった研究と批判",
        "--ronten", "4=空き家の税制", "--kijun", "国内の空き家の研究。海外は外す", "--kotoba", "税制も入れて")
    sa = kiroku.ronten_sa(w)
    ok(sa["jotai"] == "承認" and [x["n"] for x in sa["tashita"]] == [4] and [x["n"] for x in sa["keshita"]] == [3]
       and sa["naoshita"][0]["n"] == 2 and sa["kijun_naoshita"] and sa["kotoba"] == "税制も入れて",
       "(8) 論点の案と承認後の差(足した・消した・直した・基準を直した)とユーザーの言葉")
    d = os.path.join(w, "daicho.md")
    code, out = run(kiroku, "hashiri", w, "--daicho", d, "--theme", "空き家バンク", "--tomete", "全論点に文献", "--fun", "30",
                    "--kiroku", kd)
    runs = kyotsu.read_log(os.path.join(kd, "runs.jsonl"), kiroku.KIND_R)
    box = kyotsu.read_log(os.path.join(kd, "michi.jsonl"), kiroku.KIND_M)
    r = runs[-1]
    ok(code == 0 and r["id"] == "R001" and r["kensaku"]["jstage"]["hon"] == 5 and r["kensaku"]["estat"]["te"] == 1
       and r["kouho"]["sai"] == 2 and r["kouho"]["horyu"] == 1 and r["gyou"] == 2 and r["ronten"]["jotai"] == "承認",
       "(8) 走行の1行に DB ごとの検索の数・候補の数・台帳の行数・論点の差が入る(数は記録から)")
    ok(len(box) == 4 and all(b["type"] == "tomatta" and b["hashiri"] == "R001" for b in box),
       "(8) 失敗・件数なし・切られた・投げなかった検索(4本)が未知の箱に入る")
    ok(run(kiroku, "kotoba", "R009", "--kotoba", "x", "--kiroku", kd)[0] == 2, "(8) 無い走行に手応えは足せない")
    run(kiroku, "kotoba", "R001", "--kotoba", "思ったより古い論文が多い", "--kiroku", kd)
    run(kiroku, "michi", "--koe", "CiNii の詳細ページが重い", "--doko", "kakunin", "--kiroku", kd)
    runs = kyotsu.read_log(os.path.join(kd, "runs.jsonl"), kiroku.KIND_R)
    box = kyotsu.read_log(os.path.join(kd, "michi.jsonl"), kiroku.KIND_M)
    ok(runs[-1]["type"] == "kotoba" and box[-1]["koe"] == "CiNii の詳細ページが重い", "(8) 手応えと声は後ろに足す")
    old = os.environ.get("BUNKEN_KIROKU_DIR")
    os.environ["BUNKEN_KIROKU_DIR"] = kd
    try:
        code, out = run(kiroku, "miru")
        ok(code == 0 and "走行 1回・未知の箱 5件" in out, "(8) 環境変数で置き場を替えられる")
    finally:
        if old is None:
            os.environ.pop("BUNKEN_KIROKU_DIR", None)
        else:
            os.environ["BUNKEN_KIROKU_DIR"] = old
    pr = os.path.join(kd, "runs.jsonl")
    raw = open(pr, encoding="utf-8").read()
    kyotsu.write_text(pr, raw.replace('"gyou":2', '"gyou":9'))
    ok(run(kiroku, "miru", "--kiroku", kd)[0] == 1, "(8) 手で直した走行の記録で止まる")
    kyotsu.write_text(pr, raw)
    w2 = wdir("k2")
    run(kiroku, "ronten", w2, "an", "--ronten", "1=x")
    run(kiroku, "ronten", w2, "mishonin")
    ok(kiroku.ronten_sa(w2)["jotai"] == "未承認", "(8) 質問に答えられない走らせ方は「未承認」として残る")
    ok(kiroku.kiroku_dir(type("A", (), {"kiroku": None})()).replace("\\", "/").endswith(".claude/bunken-daicho-kiroku")
       or os.environ.get("BUNKEN_KIROKU_DIR"), "(8) 既定の置き場は ~/.claude/bunken-daicho-kiroku")


def part_nukigaki():
    print("(10) 抜き書きの場所")
    honbun = os.path.join(TMP, "honbun.txt")
    pages = ["表紙の頁\n空き家の研究\n- 48 -",
             "本研究では、空き家バンクの登録物件数を\n比べた。気温は−5度下がった。\nCOVID-19 の流行で移住が増えた。\n- 49 -",
             "結論として、借り上げの方式が\n有効であることが示唆された。\n- 50 -"]
    kyotsu.write_text(honbun, "\f".join(pages))
    code, out = run(nukigaki, "basho", honbun, "借り上げの方式が有効であることが示唆された。", "--hajime", "48")
    ok(code == 0 and "本文 p.50" in out, "(10) 抜き書きの在る頁を、書誌の頁の最初から数えて出す")
    code, out = run(nukigaki, "basho", honbun, "空き家バンクの登録物件数を比べた。", "--hajime", "48", "--dai", "空き家の研究")
    ok(code == 0 and "本文 p.49" in out and "△" not in out, "(10) 改行をまたぐ抜き書きも見つかり、題名が出れば化けの知らせは出ない")
    code, out = run(nukigaki, "basho", honbun, "借り上げの方式が効果的であることが示唆された。")
    ok(code == 1 and "見つからない" in out, "(10) 言い換えた抜き書きは見つからない(終わりの値 1)")
    code, out = run(nukigaki, "basho", honbun, "空き家バンクの…比べた。", "--hajime", "48")
    ok(code == 0 and "区切り 2" in out, "(10) 「…」で区切ると区切りごとに順に探す")
    code, out = run(nukigaki, "basho", honbun, "比べた。…空き家バンクの")
    ok(code == 1, "(10) 区切りの順が原文と逆なら見つからない")
    code, out = run(nukigaki, "basho", honbun, "5度下がった。")
    ok(code == 1, "(10) 原文の負号を落として写した抜き書きは見つからない")
    code, out = run(nukigaki, "basho", honbun, "−5度下がった。")
    ok(code == 0, "(10) 負号ごと写した抜き書きは見つかる")
    code, out = run(nukigaki, "basho", honbun, "19 の流行で移住が増えた。")
    ok(code == 0, "(10) 英字の直後のハイフン(COVID-19)は負号にしない")
    code, out = run(nukigaki, "basho", honbun, "借り上げの方式が", "--hajime", "47")
    ok(code == 0 and "違う" in out, "(10) 書誌の頁から数えた頁と、頁の下に刷られた数の食い違いを知らせる")
    code, out = run(nukigaki, "basho", honbun, "借り上げの方式が", "--dai", "別の論文の題名")
    ok(code == 0 and "文字化けか" in out, "(10) 題名が本文の文字に出なければ知らせる")
    kara = os.path.join(TMP, "kara.txt")
    kyotsu.write_text(kara, " \f \n")
    ok(run(nukigaki, "basho", kara, "空き家バンクの登録")[0] == 3, "(10) 文字の無い本文で止まる(終わりの値 3)")
    ok(run(nukigaki, "basho", os.path.join(TMP, "nai.pdf"), "空き家バンクの登録")[0] == 2, "(10) ファイルが無ければ終わりの値 2")
    # 試験が効いているか: 負号の確かめを外すと、負号を落とした写しが通ってしまう
    keep = nukigaki.after_minus
    nukigaki.after_minus = lambda text, at: False
    try:
        broken = run(nukigaki, "basho", honbun, "5度下がった。")[0]
    finally:
        nukigaki.after_minus = keep
    ok(broken == 0, "(10) 負号の確かめを外すと、負号を落とした写しが通る(上の試験が効いている)")


FAKE_ID = "TESTid0123456789abcd"     # 作り物の ID(英数字20字。本物の ID は試験に使わない)

KAKEN_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<grantAwards><totalResults>15</totalResults><startIndex>1</startIndex><itemsPerPage>20</itemsPerPage>
<grantAward id="KAKENHI-PROJECT-20K14925" recordSet="kakenhi" projectType="project" awardNumber="20K14925">
<urlList><url>https://kaken.nii.ac.jp/grant/KAKENHI-PROJECT-20K14925/</url></urlList>
<summary xml:lang="en"><title>Study of vacant house banks</title><category>Early-Career Scientists</category>
<member role="principal_investigator"><personalName><fullName>Yamada Taro</fullName></personalName></member></summary>
<summary xml:lang="ja"><title>空き家バンクの成約の研究</title><category path="000252" niiCode="252">若手研究</category>
<institution sequence="1">○○大学</institution><institution sequence="2">九州大学</institution>
<member sequence="1" role="principal_investigator"><institution>○○大学</institution>
<personalName sequence="1"><fullName>山田 太郎</fullName><familyName>山田</familyName></personalName></member>
<member sequence="2" role="co_investigator_buntan"><personalName><fullName>鈴木 一郎</fullName></personalName></member>
<periodOfAward searchStartFiscalYear="2020" searchEndFiscalYear="2022"><startDate>2020-04-01</startDate></periodOfAward>
</summary>
<productList><product type="journal_article"><title>成果の論文</title><year>2022</year></product></productList>
</grantAward>
<grantAward id="KAKENHI-PROJECT-15K00001" awardNumber="15K00001">
<urlList><url>https://kaken.nii.ac.jp/grant/KAKENHI-PROJECT-15K00001/</url></urlList>
<summary xml:lang="ja"><title>空き家の利活用</title><category>基盤研究(C)</category><institution>九州大学</institution>
<member role="principal_investigator"><personalName><fullName>山田 太郎</fullName></personalName></member>
<periodOfAward searchStartFiscalYear="2015" searchEndFiscalYear="2017"/></summary>
</grantAward></grantAwards>"""


@contextlib.contextmanager
def env_id(value, registry=None):
    """環境変数 CINII_APPID を value にする(None なら消す)。Windows の登録から読む所は registry を返す作り物に替える"""
    old_v, old_u = os.environ.get(kensaku.APPID_NAME), kensaku.user_env
    if value is None:
        os.environ.pop(kensaku.APPID_NAME, None)
    else:
        os.environ[kensaku.APPID_NAME] = value
    kensaku.user_env = lambda name: registry if name == kensaku.APPID_NAME else None   # ほかの名前(BUNKEN_DB など)は登録に無い
    try:
        yield
    finally:
        kensaku.user_env = old_u
        if old_v is None:
            os.environ.pop(kensaku.APPID_NAME, None)
        else:
            os.environ[kensaku.APPID_NAME] = old_v


def raw_logs(w):
    return "".join(open(os.path.join(w, n), encoding="utf-8").read() for n in ("kensaku.jsonl", "kouho.jsonl")
                   if os.path.exists(os.path.join(w, n)))


def part_appid():
    print("(11) アプリケーション ID と KAKEN")
    w = wdir("a1")
    # 応答の題名に ID が混ざって返ってきた(作り物)。記録にも一覧にも画面にも残さない
    items = [cinii_item("777", "空き家の利活用", "山田 太郎", "紀要", "2015"),
             cinii_item("778", "題名に%sが混ざった" % FAKE_ID, "佐藤 花子", "紀要", "2016")]
    with env_id(FAKE_ID), net([(cinii_json(2, items), "ok", "")]) as (fake, _):
        code, out = run(kensaku, w, "sagasu", "--db", "cinii", "--q", "空き家", "--ronten", "1")
    S, K = logs(w)
    ok(code == 0 and fake.urls[0].endswith("&appid=" + FAKE_ID), "(11) CiNii には ID を付けて投げる")
    ok("appid" not in S[-1]["url"] and FAKE_ID not in raw_logs(w) and FAKE_ID not in out,
       "(11) 検索の記録の URL に ID が無く、応答に混ざった ID も記録・一覧・画面に残らない")
    ok("題名に(ID)が混ざった" in K[-1]["dai"], "(11) 応答に混ざった ID は伏せた字に替わる")
    with env_id(FAKE_ID), net([(None, "shippai", "InvalidURL: '/opensearch/all?q=x&appid=%s'" % FAKE_ID)]):
        code, out = run(kensaku, w, "sagasu", "--db", "cinii", "--q", "空き家 税", "--ronten", "1")
    S, _ = logs(w)
    ok(code == 3 and FAKE_ID not in raw_logs(w) and FAKE_ID not in out and "appid=(ID)" in S[-1]["keikoku"][-1],
       "(11) 失敗の説明に混ざった ID も伏せる")
    with env_id(None), net([(NDL_RSS, "ok", ""), (jstage_page(0, []), "ok", "")]) as (fake, _):
        c1 = run(kensaku, w, "sagasu", "--db", "ndl", "--q", "空き家", "--ronten", "1")[0]
        c2 = run(kensaku, w, "sagasu", "--db", "jstage", "--hoho", "title", "--q", "空き家", "--ronten", "1")[0]
    ok(c1 == 0 and c2 == 0 and not any("appid" in u for u in fake.urls), "(11) NDL・J-STAGE には ID を付けない(ID が無くても投げる)")

    # KAKEN
    with env_id(FAKE_ID), net([(KAKEN_XML, "ok", "")]) as (fake, _):
        code, out = run(kensaku, w, "sagasu", "--db", "kaken", "--q", "空き家バンク", "--ronten", "2",
                        "--from", "2015", "--until", "2020")
    S, K = logs(w)
    u = fake.urls[0]
    ok(code == 0 and u.startswith("https://kaken.nii.ac.jp/opensearch/?") and "format=xml" in u and "rw=20" in u
       and "st=1" in u and "s1=2015" in u and "s2=2020" in u and "o1=3" in u and u.endswith("&appid=" + FAKE_ID),
       "(11) KAKEN の研究課題の窓口に、XML・20件・年の範囲(期間が一部でも入る課題)・ID を付けて投げる")
    ok(S[-1]["db"] == "kaken" and S[-1]["hoho"] == "kadai" and S[-1]["kiroku"] == "script" and S[-1]["kensu"] == 15
       and S[-1]["deta"] == 2 and S[-1]["atarashii"] == 2 and "appid" not in S[-1]["url"],
       "(11) KAKEN の件数が手で記録でなく検索の記録に入る(題名・代表者・年が同じ論文とは別の候補)")
    k1 = next((k for k in K if k.get("kagi") == ["kaken:KAKENHI-PROJECT-20K14925"]), {})
    ok(k1.get("dai") == "空き家バンクの成約の研究" and k1["chosha"] == ["山田 太郎"] and k1["nen"] == "2020"
       and k1["shubetsu"] == "研究課題(若手研究)" and k1["shozoku"] == "○○大学" and k1["kikan"] == "2020-2022"
       and k1["url"] == "https://kaken.nii.ac.jp/grant/KAKENHI-PROJECT-20K14925/",
       "(11) KAKEN の応答から、日本語の題名・研究代表者だけ・開始の年度・研究種目・機関・期間・課題のページを読む")
    ok("期間:2020-2022" in out and "○○大学" in out, "(11) 一覧の行に機関と期間を出す")
    with env_id(FAKE_ID), net([(KAKEN_XML, "ok", "")]):
        run(kensaku, w, "sagasu", "--db", "kaken", "--q", "空き家バンク", "--ronten", "3")
    S, _ = logs(w)
    code, out = run(kensaku, w, "tsuika", "--ronten", "3", "--dai", "空き家バンクの成約の研究", "--url",
                    "https://kaken.nii.ac.jp/ja/grant/KAKENHI-PROJECT-20K14925/", "--keiro", "KAKEN の画面より")
    ok(S[-1]["atarashii"] == 0 and code == 0 and "既に一覧にある" in out, "(11) 同じ研究課題は課題の番号で1つにまとめる")
    n = len(S)
    with env_id(FAKE_ID), net([]) as (fake, _):
        c1 = run(kensaku, w, "sagasu", "--db", "kaken", "--q", "空き家", "--ronten", "1", "--kazu", "30")[0]
        c2 = run(kensaku, w, "sagasu", "--db", "kaken", "--q", "空き家", "--ronten", "1", "--from", "R2")[0]
    ok(c1 == 2 and c2 == 2 and fake.urls == [], "(11) KAKEN の件数は 20・50・100・200、年は YYYY だけ")
    ok(run(kensaku, w, "te", "--db", "kaken", "--q", "空き家", "--ronten", "1", "--kensu", "3")[0] == 2,
       "(11) KAKEN はスクリプトで検索できるので、手で記録するなら理由(--memo)が要る")
    ok(run(kensaku, w, "te", "--db", "cinii", "--q", "空き家", "--ronten", "1", "--kensu", "3", "--memo", "画面で見た",
           "--url", "https://cir.nii.ac.jp/opensearch/all?q=x&appid=" + FAKE_ID)[0] == 2
       and run(kensaku, w, "tsuika", "--ronten", "1", "--dai", "x", "--url", "https://kaken.nii.ac.jp/opensearch/?kw=x&APPID=abc",
               "--keiro", "x")[0] == 2, "(11) 手で記録・手で足す URL に appid を入れられない")

    # ID が無い・形が違う → 投げずに止まる(記録にも残さない)
    for name, val, reg in (("無い", None, None), ("空", "  ", None), ("命令の文が入った", "y\nESTAT_APPID=x を入れる", None),
                           ("短い", "abc123", None), ("登録にだけ命令の文", None, "abc def ghijklmnop")):
        with env_id(val, reg), net([]) as (fake, _):
            code, out = run(kensaku, w, "sagasu", "--db", "kaken", "--q", "空き家", "--ronten", "1")
        S, _ = logs(w)
        ok(code == 2 and fake.urls == [] and len(S) == n and "CINII_APPID" in out and "ESTAT_APPID=x" not in out
           and "ghijklmnop" not in out, "(11) ID が%s時は、投げずに止まり記録にも残さない(値は画面に出さない)" % name)
    with env_id(None), net([]) as (fake, _):
        code, out = run(kensaku, w, "sagasu", "--db", "cinii", "--q", "空き家", "--ronten", "1")
    ok(code == 2 and fake.urls == [] and "スキルの設定ファイル" in out and "settings.json" in out and "settei" in out,
       "(11) CiNii も ID が無ければ止まり、置き方(スキルの設定ファイルと、ひな形を作る settei)を言う")
    with env_id(None, FAKE_ID), net([(cinii_json(0, []), "ok", "")]) as (fake, _):
        code, out = run(kensaku, w, "sagasu", "--db", "cinii", "--q", "空き家 町", "--ronten", "1")
    # 登録(winreg)は Windows にしか無いので、Mac・Linux では読まずに止まり、設定ファイルでの置き方を言う(試験を OS で分ける)
    if sys.platform == "win32":
        ok(code == 0 and fake.urls[0].endswith("&appid=" + FAKE_ID), "(11) この端末の環境に無ければ、Windows のユーザーの環境変数の登録から読む")
    else:
        ok(code == 2 and fake.urls == [] and "settings.json" in out, "(11) Windows でなければ登録を読まずに止まり、設定ファイルでの置き方を言う")

    # 使ったAPIと出典の行(課題 ch-9sm): KAKEN と NDL を使った作業用フォルダ a1 の台帳
    d = os.path.join(w, "daicho.md")
    base = (DAICHO.split("| # |")[0].replace("- 実行日", "- 論点3: 空き家を研究している人\n- 実行日")
            + "## 探索記録(再挑戦の起点)\n\n今回は見つからなかった論点なし(全論点で文献を確保)\n")
    kyotsu.write_text(d, base)
    run(kensaku, w, "chojiri", "--daicho", d)
    code, out = run(kensaku, w, "tashikame", "--daicho", d)
    ok(code == 1 and "KAKEN の検索か、KAKEN の研究課題の候補があるのに" in out and "NDLサーチの API が答えを返した" in out,
       "(11) KAKEN と NDL を使ったのに出典の行が無いと、2行とも求めて止まる")
    t = open(d, encoding="utf-8").read().rstrip("\n") + "\n\n### 使ったAPIと出典\n- %s\n- %s\n" % (
        kensaku.SHUSSHO["ndl"], kensaku.SHUSSHO["kaken"])
    kyotsu.write_text(d, t)
    ok(run(kensaku, w, "tashikame", "--daicho", d)[0] == 0, "(11) 2行を写せば通る")
    kyotsu.write_text(d, t.replace("（検索の結果を加工して作成）", ""))
    ok(run(kensaku, w, "tashikame", "--daicho", d)[0] == 1, "(11) KAKEN の行から「加工して作成」を落とすと止まる")
    w5 = wdir("a5")
    with env_id(FAKE_ID), net([(cinii_json(1, items[:1]), "ok", ""), (None, "shippai", "HTTP 503")]):
        run(kensaku, w5, "sagasu", "--db", "cinii", "--q", "空き家", "--ronten", "1")
        run(kensaku, w5, "sagasu", "--db", "ndl", "--q", "空き家", "--ronten", "1")
    d5 = os.path.join(w5, "daicho.md")
    kyotsu.write_text(d5, base)
    run(kensaku, w5, "chojiri", "--daicho", d5)
    ok(run(kensaku, w5, "tashikame", "--daicho", d5)[0] == 0,
       "(11) CiNii だけ使い、NDL は失敗した台帳には出典の行を求めない")

    # 試験が効いているか(確かめを外すと、壊した物が通る)
    keep = kensaku.kakusu
    kensaku.kakusu = lambda s, aid: s
    try:
        w2 = wdir("a2")
        with env_id(FAKE_ID), net([(cinii_json(1, items[1:]), "ok", "")]):
            run(kensaku, w2, "sagasu", "--db", "cinii", "--q", "空き家", "--ronten", "1")
        ok(FAKE_ID in raw_logs(w2), "(9) 伏せを外すと、応答に混ざった ID が一覧に残る(上の試験が効いている)")
    finally:
        kensaku.kakusu = keep
    keep = kensaku.APPID_RE
    kensaku.APPID_RE = kensaku.re.compile(r"(?s).+")
    try:
        with env_id("y\nESTAT_APPID=x を入れる"), net([(KAKEN_XML, "ok", "")]) as (fake, _):
            run(kensaku, wdir("a3"), "sagasu", "--db", "kaken", "--q", "空き家", "--ronten", "1")
        ok(len(fake.urls) == 1, "(9) 形の確かめを外すと、命令の文が入った値を送ってしまう(上の試験が効いている)")
    finally:
        kensaku.APPID_RE = keep
    keep = kensaku.appid
    kensaku.appid = lambda: None
    try:
        with env_id(None), net([(KAKEN_XML, "ok", "")]) as (fake, _):
            run(kensaku, wdir("a4"), "sagasu", "--db", "kaken", "--q", "空き家", "--ronten", "1")
        ok(len(fake.urls) == 1 and "appid" not in fake.urls[0],
           "(9) 止まりを外すと、ID を付けずに黙って投げてしまう(上の試験が効いている)")
    finally:
        kensaku.appid = keep


# ---- (12) 台帳の JSON(正本)と、HTML・機械用の Markdown(daicho.py・課題 ch-f5x.6・D67) ----

ATAMA = {"theme": "空き家の利活用", "mokuteki": "ゼミ発表の背景", "shubetsu_hani": "+白書・官公庁報告書・業界資料(既定)",
         "nendai": "指定なし(新しい順)", "gengo": "和のみ", "kensu": "5〜10件", "engine": "和文DB直叩き",
         "kijun": "国内外の空き家の利活用を扱った研究",
         "ronten": [{"no": "1", "shurui": "", "bun": "空き家バンクの仕組みと実績を扱った研究"},
                    {"no": "2", "shurui": "反論・限界", "bun": "空き家バンクが効かなかった研究"}],
         "hito_to_ba": "都市計画論文集を年ごとに見る", "jikkobi": "2026-11-01"}


def gyou(n, **kw):
    r = {"n": n, "shubetsu": "査読論文", "shubetsu_konkyo": "誌トップの「査読」の表示で確認 2026-11-01",
         # リンクは出どころ(D84)と、kaku --w が記録から書いた後の URL の形(候補 K000n と、全文OA の行はこの行で開いた本文)。
         # put は url を外して ireru に渡し、kaku の代わりに書き戻す。本物の kaku --w を通すと、url は記録から書き直される
         "keiro": "CiNii「空き家バンク」",
         "link": [{"kouho": "K%04d" % n, "url": "https://doi.org/10.1234/a%d" % n}]
         + ([{"honbun": True, "url": "https://www.jstage.jst.go.jp/article/x/%d/_pdf" % n, "na": "本文PDF"}]
            if kw.get("nyushu", "全文OA") == "全文OA" else []),
         "nyushu": "全文OA", "seidoku": "本文精読済み",
         "yoshi": {"han": "本文より", "shurui": "事例研究", "kajo": ["A市の空き家バンクを調べた研究", "成約が増えた"]},
         "nukigaki": [{"bun": "成約件数は3年で2倍になった。", "basho": "本文 p.5「4. 結果」"}], "yoto": "背景・比較", "access": "2026-11-01"}
    r.update(kw)
    return r


def put(f, part, name="part.json"):
    """部分を ireru に渡す。文献の行のリンクの url(kaku --w が記録から書く欄)は外して渡し、入った後に kaku の代わりに書き戻す
    (kaku を通さない試験が URL の入った行を使えるように。url を渡すと ireru が止まることは part_link で試す)"""
    part = json.loads(json.dumps(part))
    urls = {}
    for r in part.get("gyou") or [] if isinstance(part, dict) else []:
        for i, x in enumerate(r.get("link") or [] if isinstance(r, dict) else []):
            if isinstance(x, dict) and "url" in x and any(k in x for k in daicho.LINK_SRC):
                urls[(r.get("n"), i)] = x.pop("url")
    pf = os.path.join(os.path.dirname(f), name)
    kyotsu.write_text(pf, json.dumps(part, ensure_ascii=False))
    res = run(daicho, f, "ireru", "--json-file", pf)
    if res[0] == 0 and urls:
        d = json.load(open(f, encoding="utf-8"))
        for r in d.get("gyou") or []:
            for i, x in enumerate(r.get("link") or []):
                if (r["n"], i) in urls:
                    x["url"] = urls[(r["n"], i)]
        daicho.save(f, d)
    return res


def part_daicho():
    print("(12) 台帳の JSON と HTML・機械用の Markdown")
    w = wdir("d1")
    top = wdir("d1out")
    os.makedirs(top, exist_ok=True)
    f = os.path.join(top, "daicho.json")
    # 検索の記録と候補(ネットに出ない「手で記録」と tsuika で作る)
    run(kensaku, w, "te", "--db", "cinii", "--q", "空き家バンク", "--ronten", "1", "--kensu", "30", "--memo", "試験(ネットに出ない)")
    run(kensaku, w, "te", "--db", "jstage", "--q", "空き家バンク 課題", "--ronten", "2", "--kensu", "0", "--jotai", "zero", "--memo", "試験(ネットに出ない)")
    for dai, url in (("空き家バンクの研究", "https://doi.org/10.1234/a1"), ("空き家の利活用", "https://doi.org/10.1234/a2"),
                     ("韓国の空き家", "https://doi.org/10.1234/z")):
        run(kensaku, w, "tsuika", "--ronten", "1", "--dai", dai, "--url", url, "--keiro", "CiNii", "--kensaku", "S001")
    run(kensaku, w, "kime", "K0001", "sai", "--gyou", "1", "--ronten", "1,2")
    run(kensaku, w, "kime", "K0002", "sai", "--gyou", "2")
    run(kensaku, w, "kime", "K0003", "otosu", "--riyuu", "5", "--kimete", "空き家の利活用を扱わない")
    run(kiroku, "ronten", w, "an", "--ronten", "1=空き家バンクの仕組みと実績を扱った研究", "--ronten", "2(反論・限界)=空き家バンクが効かなかった研究",
        "--kijun", "国内外の空き家の利活用を扱った研究")
    run(kiroku, "ronten", w, "shonin", "--ronten", "1=空き家バンクの仕組みと実績を扱った研究", "--ronten", "2(反論・限界)=空き家バンクが効かなかった研究",
        "--kijun", "国内外の空き家の利活用を扱った研究", "--kotoba", "このままで")
    with honbun_net([(PDF_FAKE, "ok", "", "application/pdf")], pages=["本文の文" * 40] * 6):
        run(honbun, w, "toru", "--n", "1", "--url", "https://www.jstage.jst.go.jp/article/x/1/_pdf")
    sf = os.path.join(top, "daicho.shoshi.json")
    for n, dai in ((1, "空き家バンクの研究"), (2, "空き家の利活用")):
        run(shoshi, sf, "tsuika", "--n", str(n), "--chosha", "山田 太郎", "--nen", "2020", "--dai", dai, "--shi", "都市計画論文集",
            "--maki", "55", "--gou", "1", "--peji", "1-6", "--kakunin-url", "https://doi.org/10.1234/a%d" % n, "--kakunin-hi", "2026-11-01")
    g2 = gyou(2, seidoku="抄録どまり", nyushu="抄録のみ", nukigaki=[{"bun": "空き家が減った。", "basho": "抄録"}],
              yoshi={"han": "抄録より", "shurui": "調査研究", "kajo": ["B町を調べた", "空き家が減った"]})
    code, out = put(f, {"atama": ATAMA, "gyou": [gyou(1), g2],
                        "tansaku": {"mae": "", "bloku": [{"midashi": "論点2(反論・限界): 空き家バンクが効かなかった研究",
                                                          "kajo": ["**試した表記・DB・クエリ**: J-STAGE「空き家バンク 課題」(0件)",
                                                                   "**次の一手**: CiNii で「空き家バンク 成約率」"]}]},
                        "nyushu_route": ["#2: 機関リポジトリで著者版を探す"], "genkai": ["英語の文献は探していない"]})
    ok(code == 0 and "入れた" in out, "(12) 頭の部分・文献の行・探索記録を部分の JSON から入れる")
    ok(run(daicho, f, "kensa")[0] == 0, "(12) 入れた直後は形の外れなし")
    code, out = run(daicho, f, "kaku", "--w", w)
    d = json.load(open(f, encoding="utf-8"))
    md = open(os.path.join(w, "daicho.md"), encoding="utf-8").read()
    page = open(os.path.join(top, "daicho.html"), encoding="utf-8").read()
    ok(code == 0 and os.path.exists(os.path.join(top, "daicho.html")) and not os.path.exists(os.path.join(top, "daicho.md")),
       "(12) HTML は台帳のフォルダ、Markdown は作業用フォルダにだけ作る")
    kagi_k = daicho.md_rireki(os.path.join(w, "daicho.md"))
    ok(kagi_k and kagi_k[-1]["kagi"] == daicho.md_kagi(os.path.join(w, "daicho.md")) and kagi_k[-1]["t"] <= time.time(),
       "(12) kaku --w は、Markdown を書いた時刻と台帳の行の指紋を残す(reigai が古いチェッカーの出力を止めるため)")
    ok(d["gyou"][0]["ronten"] == ["1", "2"] and d["gyou"][1]["ronten"] == ["1"], "(12) 各行の論点の番号を候補の一覧から書く")
    ok(any("採った 2件(#1・#2)" in x for x in d["chojiri"]["gyou"]) and any(x.startswith("- 論点2(反論・限界): ") for x in d["chojiri"]["gyou"]),
       "(12) 選別の帳尻を候補の一覧から数えて JSON に入れる(論点の名前つき)")
    ok("2026年11月1日に" in d["hoho"]["bun"] and "検索 2回" in d["hoho"]["bun"] and "採った" in d["hoho"]["bun"]
       and "〔AIの名前と版〕" in d["hoho"]["ai"], "(12) 方法の節の下書き: 日付・検索の本数・採った数を記録から書き、AI の名前は空欄で残す")
    ok(any("CiNii Research 1回" in x and "J-STAGE 1回" in x for x in d["genkai_kikai"]) and "英語の文献は探していない" in md,
       "(12) 限界の欄: 探したデータベースを記録から数え、Claude が足した行も並べる")
    ok("| 1 | 山田 太郎(2020)「空き家バンクの研究」都市計画論文集 55(1), 1-6 | 査読論文(誌トップの「査読」の表示で確認 2026-11-01) |" in md,
       "(12) Markdown の書誌欄は書誌の項目ファイルから書く")
    ok("(本文より)事例研究。<br>・A市の空き家バンクを調べた研究<br>・成約が増えた" in md and "「成約件数は3年で2倍になった。」(本文 p.5「4. 結果」)" in md,
       "(12) 要旨と抜き書きを今の台帳と同じ形で書く")
    ok(run(kensaku, w, "tashikame", "--daicho", os.path.join(w, "daicho.md"))[0] == 0
       and run(shoshi, sf, "tashikame", "--daicho", os.path.join(w, "daicho.md"))[0] == 0,
       "(12) 作った Markdown は kensaku.py と shoshi.py の突き合わせを通る")
    ok("<script src" not in page and "<link" not in page and "@@" not in page and page.count("<h2>文献の一覧</h2>") == 1,
       "(12) HTML は外から何も読み込まず、型紙の差し込み口が残らず、本文は1回だけ入る")
    ok('data-ronten="1 2"' in page and "論点ごとの文献の数" in page and "この台帳の限界" in page and "論文の方法の節の下書き" in page,
       "(12) HTML に論点で絞る印・論点の表・限界の欄・方法の下書きがある")
    ok('class="cite"' in page and 'id="copyall"' in page and 'id="kata"' in page
       and "山田太郎,2020,空き家バンクの研究,都市計画論文集,第55巻第1号,1-6" in page,
       "(12) 各文献に引用文献の形(既定はタイプB)とコピーのボタン、形の選び方とまとめてコピーがある")
    # 形は7つ・副題はどの形も「-副題-」(ユーザーの決定 2026-11-01・D70)
    ok([k for k, _ in daicho.CITE_KATA] == ["b", "a2", "a3", "a1", "c1", "c2", "shoshi"] and page.count('<option value="') == 7
       and "data-a1=" in page and "data-c2=" in page, "(12) 選べる引用文献の形は7つ(論文の6つの書き方と書誌欄のまま)で、どの文献にも入る")
    _sh = {1: {"n": 1, "chosha": ["南石 晃明"], "nen": "1985", "dai": "地帯較差", "fukudai": "岡山県における分析", "shi": "農業経済研究",
               "maki": "57", "gou": "3", "peji": "178-184"},
           2: {"n": 2, "shurui": "hon", "chosha": ["佐伯 尚美"], "nen": "1963", "dai": "日本農業金融史論", "fukudai": "副題", "shuppan": "御茶の水書房"}}
    _cs = [daicho.cite_strings({"n": n, "link": [{"url": "https://x.example/%d" % n}], "access": "2026-11-01"}, _sh) for n in (1, 2)]
    ok(all(("-岡山県における分析-" if i == 0 else "-副題-") in c[k] and "：" not in c[k].replace("閲覧日：", "")
           for i, c in enumerate(_cs) for k, _ in daicho.CITE_KATA if k != "shoshi"),
       "(12) 副題は書誌欄のまま以外のどの形も「-副題-」で区切る(論文と図書)")
    ok(_cs[0]["a1"] == "南石晃明, 1985,「地帯較差-岡山県における分析-」, 農業経済研究第57巻第3号, p178-184, https://x.example/1"
       and _cs[0]["c2"] == "南石晃明,「地帯較差-岡山県における分析-」.農業経済研究第57巻第3号.1985.pp178-184. 2026.11.1 閲覧. https://x.example/1",
       "(12) A-1 は書式の例の区切り(「年,「題」, … p頁, URL」)、C-2 は半角の区切りで閲覧日の頭の0を付けない")
    put(f, {"shogou": "種別範囲=適合(査読論文2) / 年代=適合", "totsugo": "全2行を照合した。訂正0件(1回目。J-STAGE の2行)。"})
    run(daicho, f, "kaku", "--w", w)
    page2 = open(os.path.join(top, "daicho.html"), encoding="utf-8").read()
    d = json.load(open(f, encoding="utf-8"))     # 下の「書き換えない」の比べの元を、ここで取り直す
    ok("<li><b>種別範囲</b>: 適合(査読論文2)</li>" in page2 and "<li>訂正0件(1回目。J-STAGE の2行)。</li>" in page2,
       "(12) 台帳の確かめは、宣言との照合を項目ごとに、書誌突合を1文ごと(括弧の中では切らない)に箇条にする")
    # 入れられない物
    ok(put(f, {"gyou": [gyou(3, nyushu="公開")]})[0] == 1, "(12) 選べない語(入手状況)の行は入れない")
    ok(put(f, {"gyou": [gyou(3, keiro="CiNii | J-STAGE")]})[0] == 1, "(12) 縦棒のある行は入れない(Markdown の表が壊れる)")
    ok(put(f, {"gyou": [gyou(3, nukigaki=[])]})[0] == 1, "(12) 本文から要旨を書いたのに抜き書きの無い行は入れない")
    ok(put(f, {"gyou": [gyou(3, yoshi={"han": "抄録より", "kajo": ["x"]})]})[0] == 1, "(12) 本文精読済みなのに読めた範囲が抄録の行は入れない")
    ok(put(f, {"chojiri": {}})[0] == 2 and put(f, {"gyou": [dict(gyou(3), ronten=["1"])]})[0] == 2,
       "(12) スクリプトが書く欄(帳尻・行の論点)は渡せない")
    ok(json.load(open(f, encoding="utf-8")) == d, "(12) 入れられなかった時は台帳の JSON を書き換えない")
    code, out = put(f, {"gyou": [{"n": 2, "access": "2026-11-02"}]})
    ok(code == 0 and json.load(open(f, encoding="utf-8"))["gyou"][1]["access"] == "2026-11-02"
       and json.load(open(f, encoding="utf-8"))["gyou"][1]["seidoku"] == "抄録どまり", "(12) ある行は渡した欄だけ置き換える")
    kyotsu.write_text(os.path.join(top, "bad.json"), '{"gyou": [{"n": 2, "biko": "a"b"}]}')
    ok(run(daicho, f, "ireru", "--json-file", os.path.join(top, "bad.json"))[0] == 2, "(12) 壊れた JSON は読めないと言って止まる")
    put(f, {"tansaku": {"bloku": [{"midashi": "論点1: 空き家バンクの仕組み", "kajo": ["**試した表記・DB・クエリ**: x"]}]}})
    code, out = run(daicho, f, "kensa")
    ok(code == 1 and "次の一手" in out, "(12) 探索記録の論点の塊に次の一手が無いと止まる")
    ok(run(daicho, f, "kaku", "--w", w)[0] == 1, "(12) 形が外れている間は HTML と Markdown を作らない")
    put(f, {"tansaku": {"bloku": [{"midashi": "論点1: 空き家バンクの仕組み", "kesu": True}]}})
    # 申告の取り込み
    outf = os.path.join(w, "checker.txt")
    kyotsu.write_text(outf, "前置き\n```stage-a v1\n★事実の関門 段階A\n・確かめたこと: 2本\n```\n後ろ\n```stage-c v1\n★段階C\n```\n")
    code, out = run(daicho, f, "shinkoku", "--kara", outf)
    run(daicho, f, "kaku", "--w", w)
    md = open(os.path.join(w, "daicho.md"), encoding="utf-8").read()
    ok(code == 0 and "```stage-a v1\n★事実の関門 段階A\n・確かめたこと: 2本\n```" in md and "```stage-c v1\n★段階C\n```" in md
       and md.index("## 機械照合の申告") > md.index("| 2 |"), "(12) チェッカーの出力から申告の囲みを写さずに取り込み、表より後ろに置く")
    # 抜き出して見る
    code, out = run(daicho, f, "miru", "--n", "1", "--kata", "json")
    got = json.loads(out)
    ok(code == 0 and got[0]["shoshi"]["chosha"] == ["山田 太郎"] and got[0]["seidoku"] == "本文精読済み",
       "(12) 要る行だけを、書誌の項目と精読の欄つきで抜き出す")
    ok(run(daicho, f, "miru", "--n", "9")[0] == 1, "(12) 台帳に無い番号は無いと言って止まる")
    # 古い Markdown の台帳の写し直し(同じ Markdown がもう一度作れるか)
    f2 = os.path.join(top, "utsushi.json")
    run(daicho, f2, "utsusu", os.path.join(w, "daicho.md"))
    run(daicho, f2, "kaku", "--md", os.path.join(top, "utsushi.md"))
    a = [x for x in md.split("\n") if x.strip()]
    b = [x for x in open(os.path.join(top, "utsushi.md"), encoding="utf-8").read().split("\n") if x.strip()]
    ok(a == b, "(12) Markdown の台帳を写し直して作り直すと、空行を除いて同じ Markdown になる")
    # 確かめを外すと、壊した物が通る
    keep = daicho.row_problems
    daicho.row_problems = lambda *x, **k: []
    try:
        ok(put(f, {"gyou": [gyou(3, nyushu="公開")]})[0] == 0, "(9) 行の確かめを外すと、選べない語の行が入ってしまう(上の試験が効いている)")
    finally:
        daicho.row_problems = keep



def genten_of(w, n):
    """n 回目の写しから、確かめ役が原典から写す書誌と要旨の根拠を作る(原典が台帳と合っている時の形)"""
    cf = os.path.join(kaime.kai_dir(w, n), "daicho.json")
    if not os.path.exists(cf):
        return [], []
    d = json.load(open(cf, encoding="utf-8"))
    sh = {r["n"]: r for r in shoshi.load(os.path.join(kaime.kai_dir(w, n), "daicho.shoshi.json")).get("rows") or []}
    gen, kon = [], []
    for r in d["gyou"]:
        s = sh.get(r["n"], {})
        g = {"row": "#%d" % r["n"], "url": "https://www.jstage.jst.go.jp/article/x/%d" % r["n"]}
        g.update({k: s[k] for k in ("chosha", "nen", "shi", "maki", "gou", "peji") if k in s})
        g["dai"] = s.get("dai", "") + ("：" + s["fukudai"] if s.get("fukudai") else "")
        g["nyushu_url"] = "https://www.jstage.jst.go.jp/article/x/%d/_article/-char/ja" % r["n"]
        gen.append(g)
        kon += [{"row": "#%d" % r["n"], "kajo": i, "konkyo": "原文の文", "sasae": True}
                for i in range(1, len((r.get("yoshi") or {}).get("kajo") or []) + 1)]
    return gen, kon


def write_eval(w, n, passed, score, high=(), medium=(), unverified=(), genten=None, konkyo=None, **kw):
    path = kaime.eval_path(w, n)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    g, k = genten_of(w, n)
    ev = {"score": score, "passed": passed, "checked_rows": 3,
          "feedback_structured": {"high": [{"row": r, "field": "要旨"} for r in high],
                                  "medium": [{"row": r, "field": "著者名"} for r in medium], "low": []},
          "unverified_rows": [{"row": r, "link": "x", "why": "403"} for r in unverified],
          "genten_shoshi": g if genten is None else genten, "yoshi_konkyo": k if konkyo is None else konkyo}
    ev.update(kw)
    kyotsu.write_text(path, json.dumps(ev, ensure_ascii=False))


def kaime_setup(name):
    """3行の台帳と書誌の項目ファイルと、作業用フォルダの機械用の Markdown を作る"""
    top, w = wdir(name + "out"), wdir(name)
    os.makedirs(top, exist_ok=True)
    os.makedirs(w, exist_ok=True)
    f = os.path.join(top, "daicho.json")
    put(f, {"atama": ATAMA, "gyou": [gyou(1), gyou(2), gyou(3)]})
    sf = os.path.join(top, "daicho.shoshi.json")
    for n in (1, 2, 3):
        shoshi_row(sf, n, "山田 太郎")
    kyotsu.write_text(os.path.join(w, "daicho.md"), "# 文献台帳(試験)\n")
    return f, sf, w


def shoshi_row(sf, n, chosha):
    run(shoshi, sf, "tsuika", "--n", str(n), "--chosha", chosha, "--nen", "2020", "--dai", "題%d" % n, "--shi", "都市計画論文集",
        "--maki", "55", "--gou", "1", "--peji", "1-6", "--kakunin-url", "https://doi.org/10.1234/a%d" % n, "--kakunin-hi", "2026-11-01")


def jb(w, f, n):
    """kaku --w の代わりに Markdown を書き直してから(台帳を直した後の形)、n 回目の準備を打つ"""
    md = os.path.join(w, "daicho.md")
    kyotsu.write_text(md, open(md, encoding="utf-8").read())
    return run(kaime, w, "junbi", f, "--kai", str(n))


def part_kaime():
    print("(13) 確かめの回(kaime.py)")
    f, sf, w = kaime_setup("k1")
    code, out = jb(w, f, 1)
    ctx = json.load(open(os.path.join(w, "kaime", "1", "context.json"), encoding="utf-8"))
    ok(code == 0 and os.path.exists(os.path.join(w, "kaime", "1", "daicho.json"))
       and os.path.exists(os.path.join(w, "kaime", "1", "daicho.shoshi.json")), "(13) 1回目: 台帳の JSON と書誌の項目ファイルを写す")
    ok(ctx["plan"] == os.path.abspath(os.path.join(w, "kaime", "1", "daicho.md"))
       and kaime.same_files(ctx["plan"], os.path.join(w, "daicho.md")) and ctx["threshold"] == 80
       and [os.path.basename(x) for x in ctx["criteria"]] == ["SKILL.md", "daicho-format.md"] and all(os.path.exists(x) for x in ctx["criteria"])
       and ctx["output_contract"]["eval_file"] == os.path.abspath(kaime.eval_path(w, 1)) and "context.json" in out,
       "(13) 確かめ役に渡す物: 回のフォルダに写した Markdown・基準の2つのファイル・合格点80・結果の置き場(回ごと)")
    ok(jb(w, f, 2)[0] == 1, "(13) 前の回の結果が無いうちは次の回を作らない")
    code, out = run(kaime, w, "kekka", "--kai", "1")
    ok(code == 1 and "合格にしない" in out, "(13) 結果が無い時は合格にしない")
    kyotsu.write_text(kaime.eval_path(w, 1), json.dumps({"score": 95, "feedback_structured": {}}))
    ok(run(kaime, w, "kekka", "--kai", "1")[0] == 1, "(13) 合否の無い結果は読めない扱い(合格にしない)")
    write_eval(w, 1, False, 95, high=["#2"], medium=["#3・#9"])
    code, out = run(kaime, w, "kekka", "--kai", "1")
    ok(code == 0 and "通らない・点 95" in out and "重大 1・中 1" in out and "junbi --kai 2" in out and "#2・#3・#9" in out,
       "(13) 結果を読み、点が80を超えても通らないなら、指摘の行を直して次の回へ")
    ok(jb(w, f, 1)[0] == 1, "(13) 結果のある回は作り直さない(上書きしない)")
    # 直した台帳から Markdown を作り直さずに準備すると止まる(確かめ役が古い Markdown を読まないため)
    put(f, {"gyou": [{"n": 2, "access": "2026-11-04"}]})
    code, out = run(kaime, w, "junbi", f, "--kai", "2")
    ok(code == 1 and "古い" in out and not os.path.exists(os.path.join(w, "kaime", "2")),
       "(13) Markdown が台帳の JSON より古いうちは準備しない(kaku --w を打ってから)")
    put(f, {"gyou": [{"n": 2, "access": "2026-11-01"}]})
    ok(kaime.row_numbers("#4(2文字目)") == {4} and kaime.row_numbers("#1・#32") == {1, 32} and kaime.row_numbers("4") == {4}
       and kaime.row_numbers("ヘッダー") == set(), "(13) 指摘の行の欄は # の付いた数だけを行番号に読む(「#4(2文字目)」の 2 を拾わない)")
    # 指摘の外を直すと止まる(文献の行・書誌の項目・消した行)
    put(f, {"gyou": [{"n": 2, "yoshi": {"han": "本文より", "shurui": "事例研究", "kajo": ["A市を調べた研究", "成約は横ばい"]}},
                     {"n": 1, "access": "2026-11-02"}]})
    code, out = jb(w, f, 2)
    ok(code == 1 and "#1(access)" in out and not os.path.exists(os.path.join(w, "kaime", "2")),
       "(13) 指摘の外の行(#1)が変わっていたら、何も写さずに止まる")
    put(f, {"gyou": [{"n": 1, "access": "2026-11-01"}]})
    shoshi_row(sf, 1, "山田 次郎")
    code, out = jb(w, f, 2)
    ok(code == 1 and "書誌の項目 #1(chosha)" in out, "(13) 指摘の外の書誌の項目が変わっても止まる")
    shutil.copyfile(os.path.join(w, "kaime", "1", "daicho.shoshi.json"), sf)
    put(f, {"gyou": [{"n": 1, "kesu": True}]})
    code, out = jb(w, f, 2)
    ok(code == 1 and "#1(消した)" in out, "(13) 指摘の外の行を消しても止まる")
    put(f, {"gyou": [gyou(1)]})
    # 指摘の行だけ直した(#3 は書誌の項目を直し、#2 は要旨を直した)
    shoshi_row(sf, 3, "山田 花子")
    put(f, {"shogou": "種別範囲=適合"})
    code, out = jb(w, f, 2)
    sb = kaime.read_json(os.path.join(w, "kaime", "2", "sabun.json")) or {}
    ok(code == 0 and sb.get("mae") == 1 and sb.get("shiteki_gyou") == [2, 3, 9] and sb.get("soto") == []
       and [(x["doko"], x["n"], x["nani"]) for x in sb.get("kawatta", [])] == [("gyou", 2, "yoshi"), ("shoshi", 3, "chosha")]
       and sb.get("zentai") == ["shogou"] and "指摘の外で変わった行: 0" in out,
       "(13) 2回目: 前の回の写しと比べ、変わった行(#2 要旨・#3 著者)がどれも指摘の行と記録し、台帳全体の欄は別に記録する")
    # 2回目は通ったが中が1件 → 3回目。3回目は通らない → 最良版は2回目で、台帳を戻す
    write_eval(w, 2, True, 96, medium=["#1"])
    code, out = run(kaime, w, "kekka", "--kai", "2")
    ok(code == 0 and "通った" in out and "junbi --kai 3" in out, "(13) 通っても中の指摘が残れば、直して次の回へ")
    put(f, {"gyou": [{"n": 1, "access": "2026-11-03"}]})
    ok(jb(w, f, 3)[0] == 0, "(13) 3回目: 指摘の行(#1)だけ直せば準備できる")
    write_eval(w, 3, False, 97, high=["#1"])
    code, out = run(kaime, w, "kekka", "--kai", "3")
    ok(code == 0 and "確かめは 3 回まで" in out, "(13) 3回目で通らなければ、直さずに止める")
    ok(jb(w, f, 4)[0] == 2, "(13) 4回目は作らない(確かめは3回まで)")
    code, out = run(kaime, w, "saiyo", f)
    two = os.path.join(w, "kaime", "2", "daicho.json")
    ok(code == 0 and "最良版= 2回目" in out and "戻した" in out and kaime.same_files(two, f),
       "(13) 3回目の通らない訳(#1)が3回目に直した行なら(直しで入った誤りかもしれない)、最良版は通った最後の回(2回目)。"
       "今の台帳と違うので、2回目の写しに戻す")
    code, out = run(kaime, w, "matome")
    ok(code == 0 and "確かめ役の確かめ 3回(1回目 通らない・95点・重大1・中1/2回目 通った・96点・中1/3回目 通らない・97点・重大1)" in out
       and "採ったのは2回目の台帳" in out and "指摘の外が変わった行 0" in out, "(13) 書誌突合の1行の材料: 回ごとの合否と点と指摘の数・採った回")
    # 3回目の通らない訳が、2回目より後に直していない行(#2・#3。2回目にも同じ所が在る)だけなら、指摘(#1)を直した3回目を採る(D78)
    three = os.path.join(w, "kaime", "3", "daicho.json")
    write_eval(w, 3, False, 97, high=["#2"], unverified=["#3"])
    code, out = run(kaime, w, "saiyo", f)
    sj = kaime.read_json(os.path.join(w, "kaime", "saiyo.json")) or {}
    ok(code == 0 and "最良版= 3回目" in out and "通らない訳の行(#2・#3)は 2回目より後に直していない" in out and kaime.same_files(three, f)
       and "残った指摘" in out and sj.get("kai") == 3 and sj.get("riyuu"),
       "(13) 最後の回が通らなくても、通らない訳の行を通った回より後に直していなければ、指摘を直した最後の回を採り、残った指摘を並べて判断を待つ")
    for ev_kw, why in ((dict(high=["#2"], score=70), "合格点に届かない"), (dict(high=["ヘッダー"], score=97), "行の無い重大の指摘"),
                       (dict(high=["#2", "#1"], score=97), "訳の行の1つ(#1)を3回目に直した")):
        sc = ev_kw.pop("score")
        write_eval(w, 3, False, sc, **ev_kw)
        ok("最良版= 2回目" in run(kaime, w, "saiyo", f)[1], "(13) 通らない訳の行が分からない・直した行に訳がある時は、通った最後の回(%s)" % why)
    keep = kaime.ochita_gyou
    kaime.ochita_gyou = lambda ev: {99}
    try:
        write_eval(w, 3, False, 97, high=["#1"])
        ok("最良版= 3回目" in run(kaime, w, "saiyo", f)[1], "(9) 通らない訳の行を読まないと、直しで入ったかもしれない誤りの回を採ってしまう(上の試験が効いている)")
    finally:
        kaime.ochita_gyou = keep
    # 最良版の決め方の細かい形(D78)。作り物の回で best_kai を直に呼ぶ。既定は 1回目と2回目が通り、2回目に #2・3回目に #5 を直した
    def hyoka(passed, high=(), unv=(), score=95, **kw):
        e = {"passed": passed, "score": score, "feedback_structured": {"high": [h if not isinstance(h, str) else {"row": h} for h in high]},
             "unverified_rows": [{"row": u} for u in unv]}
        e.update(kw)
        return e
    kata = [  # (訳, 回の結果, 回ごとの sabun(回: (変わった行, doko, zentai)。None は sabun.json が無い), 採る回)
        ("通らない訳の行を3回目に直していない", [True, True, hyoka(False, ["#7"])], {}, 3),
        ("通らない訳の行を3回目に直した", [True, True, hyoka(False, ["#5"])], {}, 2),
        ("開けなかった行を3回目に直した", [True, True, hyoka(False, unv=["#5"])], {}, 2),
        ("行のある指摘と行の無い指摘が混ざる", [True, True, hyoka(False, ["#7", "ヘッダー"])], {}, 2),
        ("行の欄が範囲(#5〜#7)", [True, True, hyoka(False, ["#5〜#7"])], {}, 2),
        ("行の欄が「ほか」", [True, True, hyoka(False, ["#7ほか2行"])], {}, 2),
        ("指摘の文が直した行(#5)にまたがる", [True, True, hyoka(False, [{"row": "#7", "message": "#5 と同じ論文"}])], {}, 2),
        ("辞書でない重大の指摘", [True, True, hyoka(False, feedback_structured={"high": [{"row": "#7"}, "要旨が原文と逆"]})], {}, 2),
        ("観点の足切りで落ちた", [True, True, hyoka(False, ["#7"], all_dimensions_passed=False)], {}, 2),
        ("観点の点が足切りの下", [True, True, hyoka(False, ["#7"], quality={"breakdown": {"yoshi": 50}, "dimension_thresholds": {"yoshi": 70}})], {}, 2),
        ("確かめ役が通らないとだけ書いた", [True, True, hyoka(False)], {}, 2),
        ("台帳全体の欄が変わった", [True, True, hyoka(False, ["#7"])], {3: ([5], "gyou", ["atama"])}, 2),
        ("3回目の sabun.json が無い", [True, True, hyoka(False, ["#7"])], {3: None}, 2),
        ("2回目の sabun.json が無い(2回目に何を直したか分からない)", [True, hyoka(False, ["#9"]), hyoka(False, ["#2"])], {2: None}, 1),
        ("書誌の項目だけを直した行が訳", [True, True, hyoka(False, ["#7"])], {3: ([7], "shoshi", [])}, 2),
        ("統計原表の行を直した行が訳", [True, True, hyoka(False, ["#7"])], {3: ([7], "toukei", [])}, 2),
        ("3回目に何も直していない", [True, True, hyoka(False, ["#7"])], {3: ([], "gyou", [])}, 2),
        ("2回目も通らず、訳の行を2回目に直した", [True, hyoka(False, ["#9"]), hyoka(False, ["#2"])], {}, 1),
        ("2回目に直した行は、通った2回目の物", [True, True, hyoka(False, ["#2"])], {}, 3),
        ("通った回が無い", [hyoka(False, ["#1"], score=80), hyoka(False, ["#1"], score=90), hyoka(False, ["#1"], score=85)], {}, 2),
    ]
    zure = []
    for i, (why, evs, sbs, want) in enumerate(kata):
        w5 = wdir("k5-%d" % i)
        for n in (2, 3):
            s = sbs.get(n, ([2] if n == 2 else [5], "gyou", []))
            if s is None:
                continue
            os.makedirs(kaime.kai_dir(w5, n), exist_ok=True)
            kyotsu.write_text(os.path.join(kaime.kai_dir(w5, n), "sabun.json"), json.dumps(
                {"mae": n - 1, "kawatta": [{"doko": s[1], "n": m, "nani": "x"} for m in s[0]], "zentai": s[2]}))
        done = [(n, hyoka(True) if e is True else e) for n, e in enumerate(evs, 1)]
        got = kaime.best_kai(done, w5)[0]
        if got != want:
            zure.append("%s: %d回目(採るのは%d回目)" % (why, got, want))
    ok(not zure, "(13) 最良版の決め方の%d通り(直した行・範囲の行・またがる指摘・足切り・sabun の無い回・何も直していない回など)。外れ= %s"
       % (len(kata), zure))
    # 1回目で直す指摘が無ければ、2回目は作らない
    f2, sf2, w2 = kaime_setup("k2")
    jb(w2, f2, 1)
    write_eval(w2, 1, True, 97)
    code, out = run(kaime, w2, "kekka", "--kai", "1")
    ok(code == 0 and "次: 止める(重大・中の指摘と開けなかった行が無い)" in out
       and jb(w2, f2, 2)[0] == 1, "(13) 1回目で重大・中・開けない行が無ければ止め、2回目は作らない")
    code, out = run(kaime, w2, "saiyo", f2)
    ok(code == 0 and "今の台帳がその回の台帳と同じ" in out, "(13) 最良版が今の台帳なら戻さない")
    # 通った回が無ければ点の高い回(同じ点なら後の回)。開けなかった行は直す行に数える
    f3, sf3, w3 = kaime_setup("k3")
    jb(w3, f3, 1)
    write_eval(w3, 1, False, 90, unverified=["#3"])
    code, out = run(kaime, w3, "kekka", "--kai", "1")
    ok("junbi --kai 2" in out and "#3" in out, "(13) 開けなかった行は直す行に数える")
    put(f3, {"gyou": [{"n": 3, "kesu": True}]})
    ok(jb(w3, f3, 2)[0] == 0, "(13) 開けなかった行(指摘の行)は消してよい")
    write_eval(w3, 2, False, 90, high=["#1"])
    code, out = run(kaime, w3, "saiyo", f3)
    ok(code == 0 and "最良版= 2回目" in out and "通らない" in out, "(13) 通った回が無ければ点の高い回、同じ点なら後の回。合否が通らないとチャットに並べる")
    # 指摘の外の確かめを外すと、壊した物が通る
    f4, sf4, w4 = kaime_setup("k4")
    jb(w4, f4, 1)
    write_eval(w4, 1, False, 95, high=["#2"])
    put(f4, {"gyou": [{"n": 1, "access": "2026-11-09"}]})
    keep = kaime.soto_rows
    kaime.soto_rows = lambda *x: []
    try:
        ok(jb(w4, f4, 2)[0] == 0, "(9) 指摘の外の確かめを外すと、指摘の外を直した台帳が通ってしまう(上の試験が効いている)")
    finally:
        kaime.soto_rows = keep
    # 機械の照らし(課題 ch-jxl・ch-gya): 確かめ役が原典から写した書誌と台帳の書誌を1字ずつ照らす
    f5, sf5, w5 = kaime_setup("k5")
    jb(w5, f5, 1)
    ctx = json.load(open(os.path.join(w5, "kaime", "1", "context.json"), encoding="utf-8"))
    ok(os.path.isdir(ctx["genten_dir"]) and ctx["genten_dir"].startswith(os.path.abspath(os.path.join(w5, "kaime", "1")))
       and "daicho.json" in ctx["daicho_files"], "(13) 確かめ役に、原典の控えの置き場(回のフォルダの genten/)を渡す")
    g, k = genten_of(w5, 1)
    g[1]["shi"] = "日本観光研究学会論文集"        # 似た誌名への差し替え(E9 で見逃した形)
    write_eval(w5, 1, True, 95, genten=g)
    code, out = run(kaime, w5, "kekka", "--kai", "1")
    ok(code == 0 and "通らない" in out and "重大(機械の照らし) #2 誌" in out and "junbi --kai 2" in out,
       "(13) 原典の誌名と台帳の誌名が合わないのに確かめ役が指摘しなければ、重大の指摘を足して通さない")
    write_eval(w5, 1, True, 95, genten=g, feedback_structured={"high": [], "medium": [{"row": "#2", "field": "誌名", "message": "略称"}], "low": []})
    ok("機械の照らし" not in run(kaime, w5, "kekka", "--kai", "1")[1], "(13) 確かめ役が指摘した項目には足さない")
    g, k = genten_of(w5, 1)
    g[0]["nyushu_url"] = "https://cir.nii.ac.jp/crid/1"
    write_eval(w5, 1, True, 95, genten=g, konkyo=k[1:])
    code, out = run(kaime, w5, "kekka", "--kai", "1")
    ok("#1 入手状況" in out and "#1 要旨: 機械の照らし: 要旨の箇条1の根拠" in out,
       "(13) 全文OA を CiNii の書誌のページで確かめた行と、根拠を挙げていない要旨の箇条は重大")
    write_eval(w5, 1, True, 99, quality={"overall": 99, "breakdown": {"shoshi": 90, "nyushu": 90, "yoshi": 100}})
    code, out = run(kaime, w5, "kekka", "--kai", "1")
    ok("点 92.0" in out and "確かめ役が書いた点は 99" in out, "(13) 点は観点の点から重みで数え直す(確かめ役の計算を使わない)")
    write_eval(w5, 1, True, 95)
    del_g = json.load(open(kaime.eval_path(w5, 1), encoding="utf-8"))
    del del_g["genten_shoshi"]
    kyotsu.write_text(kaime.eval_path(w5, 1), json.dumps(del_g, ensure_ascii=False))
    ok(run(kaime, w5, "kekka", "--kai", "1")[0] == 1, "(13) 原典から写した書誌の無い結果は読めない扱い(合格にしない)")
    write_eval(w5, 1, True, 95)
    kyotsu.write_text(os.path.join(os.path.dirname(f5), "genten-1.html"), "<html></html>")
    code, out = run(kaime, w5, "kekka", "--kai", "1")
    ok(code == 1 and "genten-1.html" in out and "genten" in out, "(13) 確かめの間に台帳の置き場にファイルが増えたら止まる")
    os.remove(os.path.join(os.path.dirname(f5), "genten-1.html"))
    g, k = genten_of(w5, 1)
    g[1]["shi"] = "日本観光研究学会論文集"
    write_eval(w5, 1, True, 95, genten=g)
    keep = kaime.kikai_shiteki
    kaime.kikai_shiteki = lambda *x: []
    try:
        ok("通った" in run(kaime, w5, "kekka", "--kai", "1")[1], "(9) 機械の照らしを外すと、似た誌名への差し替えが通ってしまう(上の試験が効いている)")
    finally:
        kaime.kikai_shiteki = keep


# ---- 工程7 の追記の提案の確かめ(teian.py・課題 ch-hz0・D73) ----

# 見出しの字は 2026-08-09 に e-Stat の結果一覧の原文で数えた物に合わせた(「公開（更新）日」は全角の括弧)
ESTAT_PAGE = ("<html><head><meta charset=\"utf-8\"></head><body><table><tr><th>政府統計名</th><th>提供統計名・提供分類</th>"
              "<th>調査年月</th><th>公開（更新）日</th><th>表示・ダウンロード</th></tr>"
              "<tr><td>６次産業化総合調査</td><td>令和6年度報告</td><td>2024年度</td><td>2026-07-07</td><td>EXCEL</td></tr>"
              "</table></body></html>").encode("utf-8")
# J-STAGE の記事ページのメタ情報の形(2026-08-09 に保存した記事ページ2枚に citation_doi が1回ずつ在る)
JSTAGE_PAGE = ("<html><head><meta name=\"citation_title\" content=\"農泊の研究\">"
               "<meta name=\"citation_doi\" content=\"10.1234/abc.1\"></head><body>本文</body></html>").encode("utf-8")
ESTAT_URL = "https://www.e-stat.go.jp/stat-search/files?page=1&query=6%E6%AC%A1%E7%94%A3%E6%A5%AD%E5%8C%96&layout=dataset"
JSTAGE_URL = "https://www.jstage.jst.go.jp/article/x/1/1/1_1/_article/-char/ja"


class FakePages:
    def __init__(self, pages):
        self.pages = dict(pages)
        self.urls = []

    def __call__(self, url, timeout):
        self.urls.append(url)
        base = url.split("&appid=")[0].split("?appid=")[0]
        if base not in self.pages:
            return None, "shippai", "試験: 用意の無いページ", None, ""
        v = self.pages[base]
        if isinstance(v, tuple):
            return v
        return v, "ok", "", 200, "text/html; charset=utf-8"


@contextlib.contextmanager
def pages(pg):
    fake = FakePages(pg)
    old_f, old_s = teian.fetch, teian.time.sleep
    slept = []
    teian.fetch = fake
    teian.time.sleep = lambda s: slept.append(s)
    try:
        yield fake, slept
    finally:
        teian.fetch, teian.time.sleep = old_f, old_s


def write_kakunin(w, items):
    with open(os.path.join(w, "teian", "kakunin.json"), "w", encoding="utf-8") as f:
        json.dump({"score": 0, "passed": False, "teian": items, "evaluator_skill": "assign-bunken-guide-evaluator"},
                  f, ensure_ascii=False)


def teian_setup(name):
    """仕込んだ誤り2件(提供年月・citation_review_status)・正しい提案2件・字で確かめられない提案1件"""
    w = wdir(name)
    tz = lambda *x: run(teian, w, "tsuika", *x)  # noqa: E731
    tz("--db", "estat", "--bun", "e-Stat の結果一覧には調査年月と公開(更新)日の欄がある", "--go", "調査年月",
       "--go", "公開(更新)日", "--url", ESTAT_URL)
    tz("--db", "estat", "--bun", "e-Stat の結果一覧の提供年月で年を絞る", "--go", "提供年月", "--url", ESTAT_URL)
    tz("--db", "jstage", "--bun", "J-STAGE の記事ページの citation_doi で DOI が取れる", "--go", "citation_doi", "--url", JSTAGE_URL)
    tz("--db", "jstage", "--bun", "J-STAGE の記事ページの citation_review_status で査読が分かる", "--go", "citation_review_status",
       "--url", JSTAGE_URL)
    tz("--db", "kikan", "--bun", "ある大学のリポジトリは 502 を断続的に返す")
    return w


def part_teian():
    print("(14) 工程7 の追記の提案の確かめ(teian.py)")
    w0 = wdir("t0")
    ok(run(teian, w0, "tsuika", "--db", "estat", "--bun", "x", "--go", "調査年月")[0] == 2,
       "(14) 言葉を付けた提案に、見たページが無ければ書かない")
    ok(run(teian, w0, "tsuika", "--db", "cinii", "--bun", "x", "--go", "a",
           "--url", "https://cir.nii.ac.jp/opensearch/all?q=a&appid=" + FAKE_ID)[0] == 2,
       "(14) ページの URL に appid を入れた提案は書かない")
    ok(run(teian, w0, "tsuika", "--db", "nanika", "--bun", "x")[0] == 2, "(14) 選べない DB の名前は書かない")
    w = teian_setup("t1")
    teian_rows, junbi = teian.load(w)
    ok(len(teian_rows) == 5 and junbi is None, "(14) 提案を5件書いた(確かめにはまだ出していない)")
    ok(run(teian, w, "toru", "T1")[0] == 2, "(14) 確かめに出す前はページを開かない")
    ok(run(teian, w, "kekka")[0] == 1, "(14) 確かめに出していなければ結果を出さない")
    code, out = run(teian, w, "junbi")
    ctx = json.load(open(os.path.join(w, "teian", "context.json"), encoding="utf-8"))
    ok(code == 0 and ctx["teian"] == ["T1", "T2", "T3", "T4", "T5"] and ctx["output_contract"]["eval_file"].endswith("kakunin.json"),
       "(14) 確かめに出すと、確かめ役に渡す物を書く")
    w9 = teian_setup("t1py")
    keep = teian.shutil.which
    teian.shutil.which = lambda name: None
    try:
        run(teian, w9, "junbi")
    finally:
        teian.shutil.which = keep
    ctx9 = json.load(open(os.path.join(w9, "teian", "context.json"), encoding="utf-8"))
    ok(ctx9["toru"].startswith('"%s" "' % sys.executable) and " toru <提案の番号>" in ctx9["toru"],
       "(14) python という名前の無い環境(python3 しか無い Mac など)では、いま動いている python の場所で命令を書く")
    w10 = teian_setup("t1uv")
    teian.shutil.which = lambda name: "C:/x/uv.exe" if name == "uv" else None
    try:
        run(teian, w10, "junbi")
    finally:
        teian.shutil.which = keep
    ctx10 = json.load(open(os.path.join(w10, "teian", "context.json"), encoding="utf-8"))
    ok(ctx10["toru"].startswith('uv run "') and " toru <提案の番号>" in ctx10["toru"],
       "(14) uv がある環境では、uv run で命令を書く(頭書きの版の PyMuPDF を uv が用意する)")
    ok(run(teian, w, "tsuika", "--db", "estat", "--bun", "y")[0] == 1, "(14) 確かめに出した後は提案を足さない")
    ok(run(teian, w, "junbi")[0] == 1, "(14) 確かめに出すのは1回")
    with pages({ESTAT_URL: ESTAT_PAGE, JSTAGE_URL: JSTAGE_PAGE}) as (fake, slept):
        c1, o1 = run(teian, w, "toru", "T1")
        c2, o2 = run(teian, w, "toru", "T2")
        c3, _ = run(teian, w, "toru", "T3")
        c4, o4 = run(teian, w, "toru", "T4")
        ok(c1 == 0 and "「調査年月」 1回" in o1 and "「公開(更新)日」 1回" in o1,
           "(14) 言葉ごとに回数を数える(半角の括弧で書いた言葉も、全角の括弧のページで数える)")
        ok(c2 == 0 and "「提供年月」 0回" in o2 and "ページに無い" in o2, "(14) ページに無い言葉は0回と出す")
        ok(c3 == 0 and c4 == 0 and "「citation_review_status」 0回" in o4, "(14) タグの中の印(メタ情報)も数える")
        ok(fake.urls == [ESTAT_URL, JSTAGE_URL] and "の中身を使った" in o2 and "の中身を使った" in o4,
           "(14) 同じ確かめの中で同じページは1回だけ開き、ほかの提案は保存した中身で数える")
        ok(run(teian, w, "toru", "T1", "--url", "https://www.e-stat.go.jp/other")[0] == 2,
           "(14) 提案に書かれていないページは、補助としてしか開かない")
        ok(run(teian, w, "toru", "T5")[0] == 2, "(14) 字で確かめられない提案はページを開かない")
    ok(os.path.exists(os.path.join(w, "teian", "pages", "T1-1.body")) and os.path.exists(os.path.join(w, "teian", "pages", "T1-1.txt")),
       "(14) 開き直したページの中身とタグを外した文字を残す")
    # 確かめ役は T2 を誤って通ったとし、T4 は正しく通らないとした
    good = [{"id": "T1", "hantei": "tootta", "konkyo": "<th>調査年月</th><th>公開（更新）日</th>", "riyuu": ""},
            {"id": "T2", "hantei": "tootta", "konkyo": "提供年月", "riyuu": ""},
            {"id": "T3", "hantei": "tootta", "konkyo": "<meta name=\"citation_doi\" content=\"10.1234/abc.1\">", "riyuu": ""},
            {"id": "T4", "hantei": "tooranai", "konkyo": "", "jissai": "citation_doi", "riyuu": "その印はページに無い"},
            {"id": "T5", "hantei": "tashikamerarenai", "konkyo": "", "riyuu": "一時的な話で、開き直しても確かめられない"}]
    write_kakunin(w, good)
    code, out = run(teian, w, "kekka")
    kk = json.load(open(os.path.join(w, "teian", "kekka.json"), encoding="utf-8"))
    ids = {k: [x["id"] for x in kk[k]] for k in ("tasu", "kouho", "tooranai")}
    ok(code == 0 and ids == {"tasu": ["T1", "T3"], "kouho": ["T5"], "tooranai": ["T2", "T4"]},
       "(14) 正しい2件は足せる、仕込んだ2件は通らない、字で確かめられない1件は候補に置く")
    ok("確かめ役は通ったとした" in out and "「提供年月」はページに0回" in out,
       "(14) 確かめ役が通ったとしても、言葉が0回なら通さず、食い違いを書く")
    ok("ページにある近い書き方「citation_doi」" in out, "(14) 通らなかった提案に、ページに実際にある近い書き方を添える")
    ok("手引きに既に出てくる言葉: 「調査年月」" in out, "(14) 足せる提案に、手引きに既に出てくる言葉の回数を添える(重なりを足す前に見る)")
    write_kakunin(w, good[:3] + [dict(good[3], jissai="<meta name=\"citation_doi\" content=\"10.1234/abc.1\">")] + good[4:])
    code, out = run(teian, w, "kekka")
    ok(code == 0 and "近い書き方" not in out.split("T4")[1].split("\n")[1], "(14) タグを含む写しは、ページにある書き方として出さない")
    ok("### 手引きに足せる提案" in out and "### 「候補」の節に置く提案" in out and "### 確かめで通らなかった提案" in out,
       "(14) チャットに写す形で3つの節に分けて出す")
    # 根拠の字がページに無い・根拠に提案の言葉が無い → 足せる提案にしない
    write_kakunin(w, [dict(good[0], konkyo="調査年月 と 提供日"), dict(good[2], konkyo="DOI が取れる")] + good[1:2] + good[3:])
    run(teian, w, "kekka")
    kk = json.load(open(os.path.join(w, "teian", "kekka.json"), encoding="utf-8"))
    ok([x["id"] for x in kk["tasu"]] == [] and {"T1", "T3"} <= {x["id"] for x in kk["kouho"]},
       "(14) 確かめ役が写した根拠の字がページに無い・根拠に提案の言葉が無いと、足せる提案にしない")
    keep = teian.zai
    teian.zai = lambda *x: True
    try:
        run(teian, w, "kekka")
        kk = json.load(open(os.path.join(w, "teian", "kekka.json"), encoding="utf-8"))
        ok("T1" in [x["id"] for x in kk["tasu"]], "(9) 根拠の字の確かめを外すと、ページに無い根拠で通ってしまう(上の試験が効いている)")
    finally:
        teian.zai = keep
    write_kakunin(w, good)
    # 言葉2つのうち1つだけが実在しない提案(根拠の字は実在する方で写せるので、回数の確かめだけが止める)
    w8 = wdir("t8")
    run(teian, w8, "tsuika", "--db", "estat", "--bun", "結果一覧には調査年月と提供年月の欄がある", "--go", "調査年月",
        "--go", "提供年月", "--url", ESTAT_URL)
    run(teian, w8, "junbi")
    with pages({ESTAT_URL: ESTAT_PAGE}):
        run(teian, w8, "toru", "T1")
    write_kakunin(w8, [{"id": "T1", "hantei": "tootta", "konkyo": "<th>調査年月</th>"}])
    run(teian, w8, "kekka")
    kk = json.load(open(os.path.join(w8, "teian", "kekka.json"), encoding="utf-8"))
    ok([x["id"] for x in kk["tooranai"]] == ["T1"], "(14) 言葉のうち1つでもページに無ければ通さない")
    keep = teian.kaisu
    try:
        teian.kaisu = lambda tn, gl: {g: 1 for g in gl}
        w9 = wdir("t9")
        run(teian, w9, "tsuika", "--db", "estat", "--bun", "結果一覧には調査年月と提供年月の欄がある", "--go", "調査年月",
            "--go", "提供年月", "--url", ESTAT_URL)
        run(teian, w9, "junbi")
        with pages({ESTAT_URL: ESTAT_PAGE}):
            run(teian, w9, "toru", "T1")
        write_kakunin(w9, [{"id": "T1", "hantei": "tootta", "konkyo": "<th>調査年月</th>"}])
        run(teian, w9, "kekka")
        kk = json.load(open(os.path.join(w9, "teian", "kekka.json"), encoding="utf-8"))
        ok([x["id"] for x in kk["tasu"]] == ["T1"], "(9) 回数の確かめを外すと、実在しない欄を含む提案が通ってしまう(上の試験が効いている)")
    finally:
        teian.kaisu = keep
    ok(run(teian, w, "kekka", "--yakunashi")[0] == 0 and len(json.load(open(os.path.join(w, "teian", "kekka.json"),
                                                                       encoding="utf-8"))["kouho"]) == 5,
       "(14) 確かめ役がいない環境では、全部を確かめていない提案として出す")
    # 結果が読めない・保存した中身を書き換えた・記録を手で直した → 止まる
    with open(os.path.join(w, "teian", "kakunin.json"), "w", encoding="utf-8") as f:
        f.write('{"teian": [{"id": "T1", "hantei": "maybe"}]}')
    ok(run(teian, w, "kekka")[0] == 1, "(14) 確かめ役の結果が読めない時は止まる(足せる提案にしない)")
    write_kakunin(w, good[:1] + good[2:])
    ok(run(teian, w, "kekka")[0] == 1, "(14) 確かめ役の結果に提案の番号が足りない時は止まる")
    write_kakunin(w, good)
    body = os.path.join(w, "teian", "pages", "T1-1.body")
    with open(body, "ab") as f:
        f.write("提供年月".encode("utf-8"))
    ok(run(teian, w, "kekka")[0] == 1, "(14) 数えた後に保存したページの中身を書き換えると止まる")
    with open(body, "wb") as f:
        f.write(ESTAT_PAGE)
    tj = os.path.join(w, "teian", "teian.jsonl")
    txt = open(tj, encoding="utf-8").read()
    with open(tj, "w", encoding="utf-8", newline="\n") as f:
        f.write(txt.replace("提供年月で年を絞る", "調査年月で年を絞る"))
    ok(run(teian, w, "kekka")[0] == 1, "(14) 提案の記録を手で直すと止まる")
    w5 = wdir("t5")
    run(teian, w5, "tsuika", "--db", "jstage", "--bun", "a", "--go", "citation_doi", "--url", JSTAGE_URL)
    run(teian, w5, "tsuika", "--db", "jstage", "--bun", "b", "--go", "citation_doi", "--url", JSTAGE_URL + "?y=2")
    run(teian, w5, "junbi")
    with pages({JSTAGE_URL: JSTAGE_PAGE, JSTAGE_URL + "?y=2": JSTAGE_PAGE}) as (fake, slept):
        run(teian, w5, "toru", "T1")
        run(teian, w5, "toru", "T2")
    ok(len(fake.urls) == 2 and len(slept) == 1 and 0 < slept[0] <= kensaku.JSTAGE_MA, "(14) J-STAGE の別のページは、前に開いてから間をあける")
    # 開けなかった・J-STAGE に切られた・開かないサイト → 候補に置く
    w2 = wdir("t2")
    run(teian, w2, "tsuika", "--db", "jstage", "--bun", "a", "--go", "citation_doi", "--url", JSTAGE_URL)
    run(teian, w2, "tsuika", "--db", "jstage", "--bun", "b", "--go", "citation_doi", "--url", JSTAGE_URL + "?x=1")
    run(teian, w2, "tsuika", "--db", "scholar", "--bun", "c", "--go", "Cited by", "--url", "https://scholar.google.com/scholar?q=a")
    run(teian, w2, "junbi")
    with pages({JSTAGE_URL: (None, "kirareta", "接続を切られた(ConnectionResetError)", None, "")}) as (fake, _):
        c1, o1 = run(teian, w2, "toru", "T1")
        c2, o2 = run(teian, w2, "toru", "T2")
        c3, o3 = run(teian, w2, "toru", "T3")
        ok(c1 == 3 and c2 == 3 and "開いていない" in o2 and len(fake.urls) == 1,
           "(14) J-STAGE に切られたら、その回は J-STAGE をもう開かない")
        ok(c3 == 3 and not any("scholar" in u for u in fake.urls), "(14) Google Scholar はスクリプトから開かない")
    write_kakunin(w2, [{"id": t, "hantei": "tootta", "konkyo": "citation_doi"} for t in ("T1", "T2", "T3")])
    run(teian, w2, "kekka")
    kk = json.load(open(os.path.join(w2, "teian", "kekka.json"), encoding="utf-8"))
    ok([x["id"] for x in kk["kouho"]] == ["T1", "T2", "T3"] and not kk["tasu"],
       "(14) 開き直せなかった提案は、確かめ役が通ったとしても候補に置く")
    # ページが2つある提案で、片方しか開けず、開けた方に言葉が無い → 通らないとも決めずに候補に置く
    w6 = wdir("t6")
    run(teian, w6, "tsuika", "--db", "estat", "--bun", "a", "--go", "提供年月", "--url", ESTAT_URL, "--url", ESTAT_URL + "&p=2")
    run(teian, w6, "junbi")
    with pages({ESTAT_URL: ESTAT_PAGE}):
        run(teian, w6, "toru", "T1")
    write_kakunin(w6, [{"id": "T1", "hantei": "tashikamerarenai", "riyuu": "片方が開けない"}])
    run(teian, w6, "kekka")
    kk = json.load(open(os.path.join(w6, "teian", "kekka.json"), encoding="utf-8"))
    ok([x["id"] for x in kk["kouho"]] == ["T1"] and not kk["tooranai"] and "開き直せなかったページがある" in kk["kouho"][0]["riyuu"],
       "(14) ページの一部が開けず、開けたページに言葉が無い提案は、通らないとせず候補に置く")
    # CiNii の OpenSearch: ID を付けて開き、保存する中身と記録では伏せる
    w3 = wdir("t3")
    cu = "https://cir.nii.ac.jp/opensearch/all?q=%E8%BE%B2%E6%B3%8A&format=json"
    run(teian, w3, "tsuika", "--db", "cinii", "--bun", "OpenSearch の結果に totalResults がある", "--go", "totalResults", "--url", cu)
    run(teian, w3, "junbi")
    with pages({cu: ('{"@id": "%s&appid=%s", "opensearch:totalResults": "5"}' % (cu, FAKE_ID)).encode("utf-8")}) as (fake, _):
        code, out = run(teian, w3, "toru", "T1")
    saved = open(os.path.join(w3, "teian", "pages", "T1-1.body"), encoding="utf-8").read()
    logtxt = open(os.path.join(w3, "teian", "kazoe.jsonl"), encoding="utf-8").read()
    ok(code == 0 and fake.urls and FAKE_ID in fake.urls[0] and FAKE_ID not in saved and FAKE_ID not in logtxt and FAKE_ID not in out,
       "(14) CiNii の OpenSearch には ID を付けて開き、保存する中身・記録・画面には ID を残さない")


# ---- (15) 英語のデータベース(課題 ch-4f2・D75)。応答の形は 2026-11-02 に実物で確かめた物に合わせた ----

FAKE_KEY = "TESTkey0123456789abcdEF"   # 作り物の OpenAlex のキー(本物のキーは試験に使わない)


def oa_work(wid, title, author, year, doi=None, lang="en", retracted=False, oa_url=""):
    return {"id": "https://openalex.org/" + wid, "doi": ("https://doi.org/" + doi) if doi else None, "display_name": title,
            "publication_year": year, "type": "article", "language": lang, "is_retracted": retracted,
            "authorships": [{"author": {"display_name": author}}],
            "primary_location": {"landing_page_url": "https://example.org/" + wid,
                                 "source": {"display_name": "Journal of Sport & Tourism", "host_organization_name": "Informa UK Limited"}},
            "open_access": {"is_oa": bool(oa_url), "oa_status": "green" if oa_url else "closed", "oa_url": oa_url or None},
            "biblio": {"volume": "16", "issue": "4", "first_page": "271", "last_page": "290"}}


def oa_json(total, works):
    return json.dumps({"meta": {"count": total}, "results": works})


S2_JSON = json.dumps({"total": 2, "offset": 0, "data": [
    {"paperId": "p1", "title": "Sport events and host cities", "year": 2019, "venue": "Tourism Management",
     "journal": {"name": "Tourism Management", "volume": "70", "pages": "1-10"}, "authors": [{"name": "Ann Lee"}],
     "externalIds": {"DOI": "10.1016/j.tourman.2018.01.001"}, "publicationTypes": ["JournalArticle"],
     "openAccessPdf": None, "url": "https://www.semanticscholar.org/paper/p1"},
    {"paperId": "p2", "title": "Forecasting tourism demand with deep learning", "year": 2018, "venue": "",
     "journal": None, "authors": [{"name": "Oscar Claveria"}], "externalIds": {"ArXiv": "1805.00878"},
     "publicationTypes": None, "openAccessPdf": {"url": "https://arxiv.org/pdf/1805.00878"},
     "url": "https://www.semanticscholar.org/paper/p2"}]})

ARXIV_XML = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/"
 xmlns:arxiv="http://arxiv.org/schemas/atom"><opensearch:totalResults>58</opensearch:totalResults>
<entry><id>http://arxiv.org/abs/1805.00878v1</id><published>2018-05-02T15:00:00Z</published>
<title>Modelling tourism demand to Spain with
  machine learning techniques</title><summary>This study assesses the influence of the forecast horizon.</summary>
<author><name>Oscar Claveria</name></author><author><name>Enric Monte</name></author>
<link title="pdf" href="http://arxiv.org/pdf/1805.00878v1" rel="related" type="application/pdf"/></entry>
</feed>"""

ARXIV_ERR = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">
<opensearch:totalResults>1</opensearch:totalResults>
<entry><id>http://arxiv.org/api/errors#incorrect_id_format</id><title>Error</title><summary>incorrect id format</summary></entry></feed>"""

CR_JSON = json.dumps({"message": {"total-results": 3868507, "items": [
    {"DOI": "10.1080/14775085.2011.635014", "title": ["Developing a framework for <i>evaluating</i> legacies"],
     "author": [{"given": "Mike", "family": "Weed"}], "issued": {"date-parts": [[2011, 11]]},
     "container-title": ["Journal of Sport &amp; Tourism"], "volume": "16", "issue": "4", "page": "271-290",
     "publisher": "Informa UK Limited", "type": "journal-article"}]}})


class FakeEigo:
    def __init__(self, answers):
        self.answers = list(answers)
        self.calls = []

    def __call__(self, url, timeout, headers=None):
        self.calls.append((url, dict(headers or {})))
        if not self.answers:
            return None, "shippai", "試験: 用意の無い問い合わせ", {}
        return self.answers.pop(0)


@contextlib.contextmanager
def eigo(answers, aida, key=None, registry=None):
    """英語の DB の問い合わせを作り物にする(aida= 前の時刻を置くフォルダの名前。試験ごとに別にする)"""
    fake = FakeEigo(answers)
    old_f, old_s = kensaku.fetch_eigo, kensaku.time.sleep
    old_k, old_u = os.environ.get(kensaku.OA_KEY_NAME), kensaku.user_env
    old_d = os.environ.get(kensaku.AIDA_DIR_ENV)
    slept = []
    kensaku.fetch_eigo = fake
    kensaku.time.sleep = lambda x: slept.append(x)
    kensaku.user_env = lambda name: registry if name == kensaku.OA_KEY_NAME else None   # ほかの名前(BUNKEN_DB など)は登録に無い
    os.environ[kensaku.AIDA_DIR_ENV] = os.path.join(TMP, "aida-" + aida)
    if key is None:
        os.environ.pop(kensaku.OA_KEY_NAME, None)
    else:
        os.environ[kensaku.OA_KEY_NAME] = key
    try:
        yield fake, slept
    finally:
        kensaku.fetch_eigo, kensaku.time.sleep, kensaku.user_env = old_f, old_s, old_u
        for name, v in ((kensaku.OA_KEY_NAME, old_k), (kensaku.AIDA_DIR_ENV, old_d)):
            if v is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = v


def urllib_unquote(u):
    return kensaku.urllib.parse.unquote_plus(u)


def part_eigo():
    print("(15) 英語のデータベース")
    ok429 = (None, "kotowari", "HTTP 429", {"x-ratelimit-remaining": "990"})
    # OpenAlex: 語・年・件数が URL に入り、キーは要求の欄だけに入る。言語・無料の置き場・撤回の印が一覧に残る
    w = wdir("e1")
    works = [oa_work("W1", "Developing a framework for evaluating legacies", "Mike Weed", 2011, "10.1080/14775085.2011.635014",
                     oa_url="https://repo.example.org/1.pdf"),
             oa_work("W2", "A retracted paper on sport tourism", "Bob Ray", 2016, "10.1/r", retracted=True)]
    with eigo([(oa_json(62391, works), "ok", "", {"x-ratelimit-remaining-usd": "0.098"})], "e1", key=FAKE_KEY) as (fake, _):
        code, out = run(kensaku, w, "sagasu", "--db", "openalex", "--q", "sport tourism economic impact", "--ronten", "1",
                        "--kazu", "25", "--from", "2015", "--until", "2024")
    S, K = logs(w)
    u, h = fake.calls[0]
    ok(code == 0 and "search=sport+tourism+economic+impact" in u and "per_page=25" in u and "page=1" in u
       and "from_publication_date%3A2015-01-01" in u and "to_publication_date%3A2024-12-31" in u,
       "(15) OpenAlex に語・年・件数を付けて送る")
    ok(h.get("Authorization") == "Bearer " + FAKE_KEY and FAKE_KEY not in u and FAKE_KEY not in raw_logs(w) and FAKE_KEY not in out,
       "(15) OpenAlex のキーは要求の欄にだけ入れ、URL・記録・画面に出さない")
    ok(S[-1]["kensu"] == 62391 and S[-1]["openalex_kagi"] == "あり" and S[-1]["waku_nokori_usd"] == "0.098",
       "(15) 件数・キーの有無(値でなく)・1日の枠の残りが記録に残る")
    k1 = [r for r in K if r.get("type") == "kouho"]
    ok(k1[0].get("gengo") == "en" and k1[0].get("oa_url") == "https://repo.example.org/1.pdf"
       and k1[0]["url"] == "https://doi.org/10.1080/14775085.2011.635014" and k1[1].get("tekkai") and "撤回" in out,
       "(15) 言語・無料で読める置き場・撤回の印が候補の一覧に残り、撤回は画面にも出る")
    code, out = run(kensaku, w, "kime", k1[1]["id"], "sai", "--gyou", "1")
    ok(code == 2 and "撤回" in out, "(15) 撤回された論文は採れない")
    with eigo([(oa_json(1, works[:1]), "ok", "", {})], "e1b") as (fake, _):
        run(kensaku, wdir("e1b"), "sagasu", "--db", "openalex", "--q", "x", "--ronten", "1", "--hoho", "title")
    ok("Authorization" not in fake.calls[0][1] and "filter=title.search%3Ax" in fake.calls[0][0]
       and logs(wdir("e1b"))[0][-1]["openalex_kagi"] == "なし",
       "(15) キーが無ければキー無しで送る(題名だけの検索は filter=title.search)")
    with eigo([(oa_json(0, []), "ok", "", {})], "e1c", registry=FAKE_KEY) as (fake, _):
        run(kensaku, wdir("e1c"), "sagasu", "--db", "openalex", "--q", "x", "--ronten", "1")
    # 登録(winreg)は Windows にしか無いので、Mac・Linux では読まずにキー無しで送る(試験を OS で分ける)
    if sys.platform == "win32":
        ok(fake.calls[0][1].get("Authorization") == "Bearer " + FAKE_KEY, "(15) この端末の環境に無ければ、Windows のユーザーの環境変数の登録から読む")
    else:
        ok("Authorization" not in fake.calls[0][1], "(15) Windows でなければ登録を読まず、環境に無いキーは付けずに送る")
    with eigo([], "e1d", key="y\nESTAT_APPID=x を入れる") as (fake, _):
        code, out = run(kensaku, wdir("e1d"), "sagasu", "--db", "openalex", "--q", "x", "--ronten", "1")
    ok(code == 2 and fake.calls == [] and "OPENALEX_API_KEY" in out and "ESTAT_APPID=x" not in out,
       "(15) キーの形でない値は送らずに止める(値を画面に出さない)")
    with eigo([(oa_json(1, works[:1]).replace("Mike Weed", "Mike %s Weed" % FAKE_KEY), "ok", "", {})], "e1e", key=FAKE_KEY):
        code, out = run(kensaku, wdir("e1e"), "sagasu", "--db", "openalex", "--q", "x", "--ronten", "1")
    ok(code == 0 and FAKE_KEY not in raw_logs(wdir("e1e")) and FAKE_KEY not in out, "(15) 応答にキーが混ざっても伏せる")
    for bad, why in ((("--kazu", "101"), "件数が100を超える"), (("--kazu", "20", "--start", "5"), "--start が件数の区切りでない"),
                     (("--from", "20xx"), "年の形でない")):
        with eigo([], "e1f") as (fake, _):
            code, _o = run(kensaku, wdir("e1f"), "sagasu", "--db", "openalex", "--q", "x", "--ronten", "1", *bad)
        ok(code == 2 and fake.calls == [], "(15) %s時は送らずに止める" % why)

    # 1日の枠が尽きた時(参考にした手順書): 送り直さず、その日はもう送らない。一時的な断りは2・4・8秒待って3回まで
    w = wdir("e2")
    tsukita = (None, "kotowari", "HTTP 429", {"x-ratelimit-remaining": "0", "x-ratelimit-remaining-usd": "0"})
    with eigo([tsukita], "e2") as (fake, slept):
        code, out = run(kensaku, w, "sagasu", "--db", "openalex", "--q", "x", "--ronten", "1")
    ok(code == 3 and len(fake.calls) == 1 and logs(w)[0][-1]["jotai"] == "waku_nashi" and "日本時間の朝9時" in out + str(logs(w)[0][-1]),
       "(15) OpenAlex の1日の枠が尽きたら、送り直さずに記録する")
    with eigo([(oa_json(0, []), "ok", "", {})], "e2") as (fake, _):
        code, out = run(kensaku, w, "sagasu", "--db", "openalex", "--q", "y", "--ronten", "1")
    ok(code == 3 and fake.calls == [] and logs(w)[0][-1]["jotai"] == "yameta",
       "(15) 枠が尽きた同じ日は、もう送らず、送らなかったことも1行残す")
    with eigo([(oa_json(0, []), "ok", "", {})], "e2", key=FAKE_KEY) as (fake, _):
        code, _o = run(kensaku, w, "sagasu", "--db", "openalex", "--q", "z", "--ronten", "1")
    ok(code == 0 and len(fake.calls) == 1, "(15) キー無しの枠が尽きた後でも、キーを置けば送る(枠が別)")
    w = wdir("e3")
    with eigo([ok429, ok429, ok429, ok429], "e3") as (fake, slept):
        code, out = run(kensaku, w, "sagasu", "--db", "semanticscholar", "--q", "x", "--ronten", "1")
    ok(code == 3 and len(fake.calls) == 4 and [x for x in slept if x >= 2] == [2, 4, 8]
       and logs(w)[0][-1]["jotai"] == "kotowari" and logs(w)[0][-1]["okurinaoshi"] == 3,
       "(15) 一時的に断られたら2・4・8秒待って3回まで送り直し、だめなら「断られた」と残す")
    with eigo([ok429, (S2_JSON, "ok", "", {})], "e3b") as (fake, slept):
        code, out = run(kensaku, wdir("e3b"), "sagasu", "--db", "semanticscholar", "--q", "sport events", "--ronten", "1",
                        "--from", "2015")
    S, K = logs(wdir("e3b"))
    ok(code == 0 and len(fake.calls) == 2 and S[-1]["okurinaoshi"] == 1 and "year=2015-" in fake.calls[0][0]
       and [r.get("doi") for r in K if r.get("type") == "kouho"] == ["10.1016/j.tourman.2018.01.001", None],
       "(15) Semantic Scholar: 1回待って通れば、送り直した数と候補を残す(年は year=)")

    # arXiv: 語を AND でつなぎ、3秒に1本(PC 全体)。種別はプレプリント。arXiv の番号で Semantic Scholar の候補とまとめる
    w = wdir("e3b")
    with eigo([(ARXIV_XML, "ok", "", {}), (ARXIV_XML, "ok", "", {})], "e4") as (fake, slept):
        code, out = run(kensaku, w, "sagasu", "--db", "arxiv", "--q", "tourism forecasting", "--ronten", "2",
                        "--from", "2015", "--until", "2020")
        run(kensaku, w, "sagasu", "--db", "arxiv", "--q", "ti:tourism", "--ronten", "2", "--hoho", "shiki")
    S, K = logs(w)
    u = urllib_unquote(fake.calls[0][0])
    ok(code == 0 and "all:tourism AND all:forecasting" in u and "submittedDate:[201501010000 TO 202012312359]" in u
       and "search_query=ti:tourism&" in urllib_unquote(fake.calls[1][0]),
       "(15) arXiv: 語を AND でつなぎ、年は投稿日で絞る(shiki は式のまま送る)")
    ok(any(2.5 < x <= 3 for x in slept), "(15) arXiv は前の問い合わせから3秒あける")
    new = [r for r in K if r.get("type") == "kouho"]
    ok(len(new) == 2 and any(r.get("type") == "mata" and r.get("kensaku") == S[-2]["id"] for r in K),
       "(15) arXiv の番号が同じ Semantic Scholar の候補と1つにまとめる")
    _, cands, _ = kensaku.load(w)
    c2 = [c for c in cands.values() if "arxiv:1805.00878" in c["kagi"]][0]
    ok(c2["dai"] == "Forecasting tourism demand with deep learning", "(15) まとめた候補は arXiv の番号の鍵を持つ")
    with eigo([(ARXIV_ERR, "ok", "", {})], "e4b"):
        code, out = run(kensaku, wdir("e4b"), "sagasu", "--db", "arxiv", "--q", "x", "--ronten", "1")
    ok(code == 3 and logs(wdir("e4b"))[0][-1]["jotai"] == "shippai" and "誤りの項目" in out,
       "(15) arXiv が誤りの項目を返したら、0件でなく失敗と残す")
    with eigo([(ARXIV_XML, "ok", "", {})], "e4c"):
        run(kensaku, wdir("e4c"), "sagasu", "--db", "arxiv", "--q", "tourism", "--ronten", "1")
    kc = [r for r in logs(wdir("e4c"))[1] if r.get("type") == "kouho"][0]
    ok(kc["shubetsu"] == "プレプリント" and kc["url"] == "https://arxiv.org/abs/1805.00878"
       and kc["dai"] == "Modelling tourism demand to Spain with machine learning techniques"
       and kc["oa_url"] == "https://arxiv.org/pdf/1805.00878v1",
       "(15) arXiv の候補は種別プレプリント・題の改行をそろえ・本文の置き場を https で残す")

    # Crossref: 題のタグを外す・書誌の欄だけの検索は query.bibliographic
    w = wdir("e5")
    with eigo([(CR_JSON, "ok", "", {})], "e5") as (fake, _):
        code, out = run(kensaku, w, "sagasu", "--db", "crossref", "--q", "sport legacy", "--ronten", "1", "--hoho", "shoshi",
                        "--kazu", "10", "--start", "11", "--from", "2010")
    kc = [r for r in logs(w)[1] if r.get("type") == "kouho"][0]
    u = fake.calls[0][0]
    ok(code == 0 and "query.bibliographic=sport+legacy" in u and "offset=10" in u and "from-pub-date%3A2010" in u
       and kc["dai"] == "Developing a framework for evaluating legacies" and kc["shi"] == "Journal of Sport & Tourism"
       and kc["nen"] == "2011" and kc["chosha"] == ["Mike Weed"],
       "(15) Crossref: 書誌の欄だけの検索・2ページ目・年で送り、題のタグを外して読む")

    # 抄録(shoroku): 抄録の無い所は次へ。OpenAlex の語の並びを文に戻し、出どころと一緒に保存する
    w = wdir("e6")
    s2_none = json.dumps({"paperId": "p", "title": "T", "abstract": None})
    oa_abs = json.dumps({"display_name": "T", "abstract_inverted_index": {"This": [0], "paper": [1, 4], "seeks": [2], "a": [3]}})
    with eigo([(s2_none, "ok", "", {}), (oa_abs, "ok", "", {})], "e6", key=FAKE_KEY) as (fake, _):
        code, out = run(kensaku, w, "shoroku", "--doi", "https://doi.org/10.1080/14775085.2011.635014")
    f = os.path.join(w, "shoroku", "10.1080_14775085.2011.635014.txt")
    body = open(f, encoding="utf-8").read() if os.path.exists(f) else ""
    ok(code == 0 and "This paper seeks a paper" in body and body.startswith("出どころ: https://api.openalex.org/works/doi:10.1080/")
       and FAKE_KEY not in body and fake.calls[0][0].startswith("https://api.semanticscholar.org/graph/v1/paper/DOI:10.1080/"),
       "(15) 抄録は Semantic Scholar → OpenAlex の順に取り、語の並びを文に戻して出どころと保存する(キーは残さない)")
    with eigo([(None, "shippai", "HTTP 404", {}), (None, "shippai", "HTTP 404", {}), (None, "shippai", "HTTP 404", {})], "e6b"):
        code, out = run(kensaku, wdir("e6b"), "shoroku", "--doi", "10.1/none")
    ok(code == 3 and "取れなかった" in out, "(15) どこにも抄録が無ければ、取れなかったと出す")

    # 出典の行(Semantic Scholar の約款): 検索が答えを返したか、抄録を取った時に求める
    d = os.path.join(wdir("e3b"), "daicho.md")
    base = DAICHO.split("| # |")[0] + "## 探索記録(再挑戦の起点)\n\n今回は見つからなかった論点なし(全論点で文献を確保)\n"
    kyotsu.write_text(d, base)
    run(kensaku, wdir("e3b"), "chojiri", "--daicho", d)
    code, out = run(kensaku, wdir("e3b"), "tashikame", "--daicho", d)
    ok(code == 1 and "Semantic Scholar の API が答えを返した検索がある" in out, "(15) Semantic Scholar を使ったのに出典の行が無いと止まる")
    t = open(d, encoding="utf-8").read().rstrip("\n") + "\n\n### 使ったAPIと出典\n- %s\n" % kensaku.SHUSSHO["semanticscholar"]
    kyotsu.write_text(d, t)
    ok(run(kensaku, wdir("e3b"), "tashikame", "--daicho", d)[0] == 0, "(15) 出典の行を写せば通る")
    d3 = os.path.join(wdir("e3"), "daicho.md")
    kyotsu.write_text(d3, base)
    run(kensaku, wdir("e3"), "chojiri", "--daicho", d3)
    ok(run(kensaku, wdir("e3"), "tashikame", "--daicho", d3)[0] == 0, "(15) Semantic Scholar に断られただけの台帳には出典の行を求めない")
    w7 = wdir("e7")
    with eigo([(json.dumps({"title": "T", "abstract": "An abstract."}), "ok", "", {})], "e7"):
        run(kensaku, w7, "shoroku", "--doi", "10.1/x")
    d7 = os.path.join(w7, "daicho.md")
    kyotsu.write_text(d7, base)
    run(kensaku, w7, "chojiri", "--daicho", d7)
    code, out = run(kensaku, w7, "tashikame", "--daicho", d7)
    ok(code == 1 and "Semantic Scholar から取った抄録がある" in out, "(15) Semantic Scholar から抄録を取った時も出典の行を求める")

    # 試験が効いているか(確かめを外すと、壊した物が通る)
    keep = kensaku.waku_tsukita
    kensaku.waku_tsukita = lambda db, hd: False
    try:
        with eigo([tsukita, tsukita, tsukita, tsukita], "e8") as (fake, _):
            run(kensaku, wdir("e8"), "sagasu", "--db", "openalex", "--q", "x", "--ronten", "1")
        ok(len(fake.calls) == 4, "(9) 枠の見分けを外すと、尽きた枠に送り直してしまう(上の試験が効いている)")
    finally:
        kensaku.waku_tsukita = keep
    keep = kensaku.OA_KEY_MASK
    kensaku.OA_KEY_MASK = FAKE_KEY
    try:
        with eigo([(oa_json(1, works[:1]).replace("Mike Weed", "Mike %s Weed" % FAKE_KEY), "ok", "", {})], "e9", key=FAKE_KEY):
            run(kensaku, wdir("e9"), "sagasu", "--db", "openalex", "--q", "x", "--ronten", "1")
        ok(FAKE_KEY in raw_logs(wdir("e9")), "(9) 伏せを外すと、応答に混ざったキーが一覧に残る(上の試験が効いている)")
    finally:
        kensaku.OA_KEY_MASK = keep


def part_kakikomi():
    print("(16) 同じ作業用フォルダを2つの処理が同時に使う")
    a_items = [cinii_item("901", "空き家の題A", "佐藤 花子", "紀要", "2016"), cinii_item("902", "空き家の題B", "鈴木 一郎", "紀要", "2017")]
    b_items = [cinii_item("903", "空き家の題C", "田中 二郎", "紀要", "2018"), cinii_item("904", "空き家の題D", "高橋 三子", "紀要", "2019")]

    def soto(w, mae_ni_yomu=False):
        """1本目の答えを待つ間に、別の処理が同じフォルダで検索して書く(2026-11-02 の試しで起きた形)"""
        calls = []
        old_f, old_load = kensaku.fetch, kensaku.load
        yonda = []

        def fake(url, timeout):
            calls.append(url)
            if len(calls) == 1:
                with contextlib.redirect_stdout(io.StringIO()):
                    kensaku.main([w, "sagasu", "--db", "cinii", "--q", "別の語", "--ronten", "1"])
                return cinii_json(2, a_items), "ok", ""
            return cinii_json(2, b_items), "ok", ""

        def stale_load(x):
            """壊しドリル: 外側の処理が番号を付ける時(5回目の読み)に、送る前に読んだ一覧(1回目)を渡す(直す前の形)"""
            yonda.append(old_load(x))
            return yonda[0] if len(yonda) == 5 else yonda[-1]
        kensaku.fetch = fake
        if mae_ni_yomu:
            kensaku.load = stale_load
        try:
            code, out = run(kensaku, w, "sagasu", "--db", "cinii", "--q", "空き家", "--ronten", "1")
        finally:
            kensaku.fetch, kensaku.load = old_f, old_load
        return code, out

    w = wdir("kk1")
    code, out = soto(w)
    try:
        S, K = logs(w)
        ids = [r["id"] for r in K if r.get("type") == "kouho"]
        good = len(ids) == len(set(ids)) == 4 and [r["id"] for r in S] == ["S001", "S002"]
    except kyotsu.Stop:
        good = False
    ok(code == 0 and good and run(kensaku, w, "ichiran")[0] == 0,
       "(16) 答えを待つ間に別の処理が書いても、番号は札を取ってから読み直して付けるので、ぶつからない")
    w = wdir("kk2")
    soto(w, mae_ni_yomu=True)
    code, out = run(kensaku, w, "ichiran")
    ok(code == 1 and "同じ番号" in out, "(9) 送る前に読んだ一覧のまま番号を付けると、同じ番号の候補が2つ入って止まる(上の試験が効いている)")
    w = wdir("kk3")
    os.makedirs(w, exist_ok=True)
    kyotsu.write_text(os.path.join(w, kensaku.KAKIKOMI_FUDA), "")
    keep = kensaku.JUNBAN_MATSU
    kensaku.JUNBAN_MATSU = -1
    try:
        with net([(cinii_json(2, a_items), "ok", "")]):
            code, out = run(kensaku, w, "sagasu", "--db", "cinii", "--q", "空き家", "--ronten", "1")
        code2, out2 = run(kensaku, w, "kime", "K0001", "sai", "--gyou", "1")
    finally:
        kensaku.JUNBAN_MATSU = keep
    ok(code == 1 and "順番待ち" in out and not os.path.exists(os.path.join(w, "kensaku.jsonl")) and code2 == 1,
       "(16) 札を持つ処理が終わらなければ、待った末に止まり、記録に書かない(判定の命令も同じ)")


REIGAI_OUT = """  ▲ B-11  リンクが現に届く(段階A)  — 段階A: 2本中 到達 1 / 届かない 0 / ★未検査 1
  ▲ B-14  引いた逐語が原典に現に在る(段階C)  — 段階C: 逐語 2本中 在った 0 / 無い 0 / ★未検査 2
  → 違反 %(ihan)s項目 / 要目視 0項目 / 未検査 0項目 / 合格 19項目 / **検査不能 2項目** (検査した規則 21)
```stage-a v1
★事実の関門 段階A
・★未検査 1件
   - L4 https://doi.org/10.1177/kot1 —— HTTP 403(拒まれた。★リンクの誤りとは限らない)
★この関門は「リンクが届くか」しか見ていない。
```
```stage-b v1
★事実の関門 段階B
・★測れなかった %(b)s件
%(bgyou)s★この関門は「書誌が登録機関の記録と合うか」しか見ていない。
```
```stage-c v1
★事実の関門 段階C
・★測れなかった 2件
   - L4 抜き書き「Prices rose by 5%%.」 —— 本文が取れていない(unreachable)
       当てたページ: https://doi.org/10.1177/kot1(取れていない: unreachable)
   - L5 抜き書き「Demand fell sharply.」 —— ページが散文を渡していない(和文の連なりの最長 0 < 100)
       当てたページ: https://doi.org/10.1016/x → https://linkinghub.elsevier.com/retrieve/pii/S1(判定不能)
★この関門は「逐語が原典に在るか」しか見ていない。
```
"""


PDF_FAKE = b"%PDF-1.4 fake"


@contextlib.contextmanager
def honbun_net(answers, pages=None):
    """honbun.py の取得を作り物にする(answers= [(中身, 状態, 説明, 型)]。pages= 頁ごとの文字。None なら本物の PyMuPDF で読む)"""
    q = list(answers)
    old_f, old_p, old_s = honbun.fetch_bytes, honbun.yomu_peeji, honbun.time.sleep
    old_d = os.environ.get(kensaku.AIDA_DIR_ENV)
    honbun.fetch_bytes = lambda url, timeout: q.pop(0)
    if pages is not None:
        honbun.yomu_peeji = lambda path: pages
    honbun.time.sleep = lambda x: None
    os.environ[kensaku.AIDA_DIR_ENV] = os.path.join(TMP, "aida-honbun")
    try:
        yield
    finally:
        honbun.fetch_bytes, honbun.yomu_peeji, honbun.time.sleep = old_f, old_p, old_s
        if old_d is None:
            os.environ.pop(kensaku.AIDA_DIR_ENV, None)
        else:
            os.environ[kensaku.AIDA_DIR_ENV] = old_d


def eigo_gyou(n, doi, bun, **kw):
    return gyou(n, gengo="英", nyushu="未入手", seidoku="抄録どまり", link=kw.pop("link", [{"doi": True, "url": "https://doi.org/" + doi}]),
                yoshi={"han": "抄録より", "shurui": "計量分析", "kajo": ["需要を予測した研究"]},
                nukigaki=[{"bun": bun, "basho": "抄録(Semantic Scholar の記録)"}], **kw)


def part_link():
    print("(19) 文献の行のリンクは出どころ(候補の番号・開いた本文・書誌の DOI)で書き、URL は kaku --w が記録から書く(D84)")
    top, w = wdir("lk1out"), wdir("lk1")
    os.makedirs(top, exist_ok=True)
    f = os.path.join(top, "daicho.json")
    sf = os.path.join(top, "daicho.shoshi.json")
    run(kensaku, w, "te", "--db", "cinii", "--q", "空き家バンク", "--ronten", "1", "--kensu", "3", "--memo", "試験(ネットに出ない)")
    run(kensaku, w, "tsuika", "--ronten", "1", "--dai", "空き家バンクの研究", "--url", "https://cir.nii.ac.jp/crid/1001",
        "--doi", "10.1234/lk1", "--keiro", "CiNii", "--kensaku", "S001")
    run(kensaku, w, "tsuika", "--ronten", "1", "--dai", "空き家の利活用", "--url", "https://repo.example.org/lk2", "--keiro", "#1の引用文献より")
    run(kensaku, w, "kime", "K0001", "sai", "--gyou", "1", "--ronten", "1,2")
    run(kensaku, w, "kime", "K0002", "sai", "--gyou", "2")
    for kind in ("an", "shonin"):
        run(kiroku, "ronten", w, kind, "--ronten", "1=空き家バンクの仕組みと実績を扱った研究", "--ronten", "2(反論・限界)=空き家バンクが効かなかった研究",
            "--kijun", "国内外の空き家の利活用を扱った研究", *(["--kotoba", "このままで"] if kind == "shonin" else []))
    with honbun_net([(PDF_FAKE, "ok", "", "application/pdf")] * 2, pages=["本文の文" * 40] * 6):
        run(honbun, w, "toru", "--n", "1", "--url", "https://repo.example.org/body1a.pdf")
        run(honbun, w, "toru", "--n", "1", "--url", "https://repo.example.org/body1b.pdf")
    shoshi_row(sf, 1, "山田 太郎")
    run(shoshi, sf, "tsuika", "--n", "2", "--chosha", "鈴木 花子", "--nen", "2021", "--dai", "空き家の利活用", "--shi", "都市計画論文集",
        "--maki", "56", "--gou", "1", "--peji", "7-12", "--doi", "10.1234/lk2", "--kakunin-url", "https://doi.org/10.1234/lk2",
        "--kakunin-hi", "2026-11-01")
    g1 = gyou(1, link=[{"kouho": "K0001", "doi": True}, {"kouho": "K0001", "na": "CiNii"}, {"honbun": 1, "na": "本文PDF"},
                       {"honbun": True, "na": "本文PDF(2回目)"}])
    g2 = gyou(2, nyushu="抄録のみ", seidoku="抄録どまり", nukigaki=[{"bun": "空き家が減った。", "basho": "抄録"}],
              yoshi={"han": "抄録より", "shurui": "調査研究", "kajo": ["B町を調べた", "空き家が減った"]},
              link=[{"doi": True}, {"kouho": "K0002", "na": "引用文献からたどった置き場"}])
    tansaku = {"mae": "", "bloku": [{"midashi": "論点2(反論・限界): 空き家バンクが効かなかった研究",
                                     "kajo": ["**試した表記・DB・クエリ**: J-STAGE「空き家バンク 課題」(0件)", "**次の一手**: CiNii で「空き家バンク 成約率」"]}]}
    # url を渡すと入れない(Claude が URL を打たない。打った URL は記録の URL と違っても気づけないため)
    code, out = put(f, {"atama": ATAMA, "gyou": [gyou(1, link=[{"url": "https://doi.org/10.1234/lk1"}])]})
    ok(code == 2 and "リンクに url は書かない" in out, "(19) リンクに url を書いた行は入れない")
    pf = os.path.join(top, "url.json")
    kyotsu.write_text(pf, json.dumps({"atama": ATAMA, "gyou": [dict(g1, link=[{"kouho": "K0001", "url": "https://doi.org/10.1234/lk1"}])]},
                                     ensure_ascii=False))
    ok(run(daicho, f, "ireru", "--json-file", pf)[0] == 2, "(19) 出どころと一緒でも、url を書いた行は入れない")
    code, out = put(f, {"atama": ATAMA, "gyou": [gyou(1, link=[{"na": "本文PDF"}])]})
    ok(code == 1 and "出どころ(kouho・honbun・doi)が無い" in out, "(19) 出どころの無いリンクは入れない")
    ok(put(f, {"atama": ATAMA, "gyou": [gyou(1, link=[{"kouho": "12"}])]})[0] == 1, "(19) 候補の番号は K0012 の形")
    code, out = put(f, {"atama": ATAMA, "gyou": [g1, g2], "tansaku": tansaku})
    d = json.load(open(f, encoding="utf-8"))
    ok(code == 0 and all("url" not in x for r in d["gyou"] for x in r["link"]), "(19) 出どころだけのリンクは入れ、URL はまだ書かない")
    code, out = run(daicho, f, "kaku", "--w", w)
    d = json.load(open(f, encoding="utf-8"))
    md = open(os.path.join(w, "daicho.md"), encoding="utf-8").read()
    want1 = ["https://doi.org/10.1234/lk1", "https://cir.nii.ac.jp/crid/1001", "https://repo.example.org/body1a.pdf",
             "https://repo.example.org/body1b.pdf"]
    want2 = ["https://doi.org/10.1234/lk2", "https://repo.example.org/lk2"]
    ok(code == 0 and [x["url"] for x in d["gyou"][0]["link"]] == want1 and [x["url"] for x in d["gyou"][1]["link"]] == want2
       and all(u in md for u in want1 + want2),
       "(19) kaku --w は、候補の URL と DOI・開いた本文の回ごとの置き場・書誌の項目ファイルの DOI から URL を書く")
    # 手で JSON の URL を書き換えても、kaku --w が記録の URL に戻す
    d["gyou"][0]["link"][0]["url"] = "https://doi.org/10.9999/tegaki"
    daicho.save(f, d)
    run(daicho, f, "kaku", "--w", w)
    md = open(os.path.join(w, "daicho.md"), encoding="utf-8").read()
    ok("10.9999/tegaki" not in md and json.load(open(f, encoding="utf-8"))["gyou"][0]["link"][0]["url"] == want1[0],
       "(19) JSON の URL を手で書き換えても、kaku --w が記録の URL に戻す")
    d = json.load(open(f, encoding="utf-8"))
    d["gyou"][0]["link"][0]["url"] = "https://doi.org/10.9999/tegaki"
    daicho.save(f, d)
    keep = daicho.link_from_records
    daicho.link_from_records = lambda d_, w_, sh_: []
    try:
        run(daicho, f, "kaku", "--w", w)
    finally:
        daicho.link_from_records = keep
    ok("10.9999/tegaki" in open(os.path.join(w, "daicho.md"), encoding="utf-8").read(),
       "(9) 記録から書くのを外すと、手で書いた URL が台帳に残ってしまう(上の試験が効いている)")
    run(daicho, f, "kaku", "--w", w)
    # 記録から書けない出どころは、台帳を作らない
    for link, kotoba, na in (([{"kouho": "K0099"}], "候補の一覧に K0099 が無い", "一覧に無い候補"),
                             ([{"honbun": 5}], "開けた本文の記録が無い(5回目)", "開いていない回"),
                             ([{"kouho": "K0002", "doi": True}], "K0002 の記録に DOI が無い", "DOI の無い候補"),
                             ([{"doi": True}], "書誌の項目ファイルの #1 に DOI が無い", "書誌に DOI の無い行")):
        put(f, {"gyou": [dict(g1, link=link)]})
        code, out = run(daicho, f, "kaku", "--w", w)
        ok(code == 1 and kotoba in out, "(19) 記録から URL を書けない出どころ(%s)は、台帳を作らない" % na)
    put(f, {"gyou": [g1]})
    code, out = run(daicho, f, "kaku")
    ok(code == 1 and "リンクの URL がまだ無い" in out, "(19) --w の無い kaku は、URL を記録から書いていないリンクのある台帳を作らない")
    ok(run(daicho, f, "kaku", "--w", w)[0] == 0, "(19) kaku --w で書き直すと通る")
    # 同じ URL になるリンクは1本にする(試しで、候補の URL が DOI や開いた本文と同じ行に、同じリンクが2本並んだ)
    put(f, {"gyou": [dict(g2, link=[{"doi": True}, {"kouho": "K0002"}, {"kouho": "K0002", "na": "同じ置き場"}])]})
    code, out = run(daicho, f, "kaku", "--w", w)
    ls = json.load(open(f, encoding="utf-8"))["gyou"][1]["link"]
    ok(code == 0 and [x["url"] for x in ls] == want2 and ls[1].get("na") == "同じ置き場"
       and "#2 のリンクの 3本目は、前のリンクと同じ URL なので外した" in out,
       "(19) 同じ URL になったリンク(候補の URL と DOI・開いた本文が同じ時など)は1本にして、外したことを出す")
    # 書誌の DOI を採った候補の DOI と照らす(D84 の7。AI が打った DOI の打ち間違いを、道具の段で止める)
    sh1 = ["--n", "1", "--chosha", "山田 太郎", "--nen", "2020", "--dai", "題1", "--shi", "都市計画論文集", "--maki", "55",
           "--gou", "1", "--peji", "1-6", "--kakunin-url", "https://doi.org/10.1234/lk1", "--kakunin-hi", "2026-11-01"]
    run(shoshi, sf, "tsuika", *sh1, "--doi", "10.1234/LK9")
    code, out = run(daicho, f, "kaku", "--w", w)
    ok(code == 1 and "#1: 書誌の項目ファイルの DOI(10.1234/lk9)が、この行が採った候補 K0001 の DOI(10.1234/lk1)と違う" in out,
       "(19) 書誌の DOI が、採った候補の DOI と違えば台帳を作らない(打ち間違いを止める)")
    keep = daicho.shikibetsu_problems
    daicho.shikibetsu_problems = lambda d_, w_, sh_: []
    try:
        ok(run(daicho, f, "kaku", "--w", w)[0] == 0, "(9) 照らしを外すと、打ち間違えた DOI のまま台帳ができてしまう(上の試験が効いている)")
    finally:
        daicho.shikibetsu_problems = keep
    run(shoshi, sf, "tsuika", *sh1, "--doi", "https://doi.org/10.1234/LK1")
    ok(run(daicho, f, "kaku", "--w", w)[0] == 0, "(19) 同じ DOI(大文字・doi.org の頭は気にしない)なら通る")
    # 「画像から書き写し」の抜き書きは、頁を画像にした記録と照らす(チェッカーは画像からの書き写しを照らさない)
    put(f, {"gyou": [dict(g1, nukigaki=[{"bun": "成約件数は3年で2倍になった。", "basho": "本文 p.5(画像から書き写し)"}])]})
    code, out = run(daicho, f, "kaku", "--w", w)
    ok(code == 1 and "「画像から書き写し」とあるのに、この行の番号で頁を画像にした記録が無い" in out,
       "(19) 画像から書き写した抜き書きは、頁を画像にした記録が無ければ台帳を作らない")
    kyotsu.append_log(os.path.join(w, honbun.LOG), honbun.KIND, [{"type": "gazo", "n": 1, "k": 2, "peeji": [5], "at": kyotsu.ts()}])
    ok(run(daicho, f, "kaku", "--w", w)[0] == 0, "(19) 頁を画像にした記録があれば通る")


def part_tsukau():
    print("(20) 使うデータベースを設定(BUNKEN_DB)で選び、外した物には送らない(D84。仕事ではサービスごとに商用の許諾が違う)")
    w = wdir("ts1")
    old = os.environ.pop(kensaku.TSUKAU_NAME, None)
    keep_ue, keep_ok = kensaku.user_env, kensaku.okuru
    kensaku.user_env = lambda name: None          # この PC のアカウントの環境変数を読まない
    calls = []
    kensaku.okuru = lambda db, url, h, k=None: (calls.append(db), (None, "shippai", "試験(ネットに出ない)", {}, 0))[1]
    try:
        code, out = run(kensaku, w, "tsukau")
        ok(code == 0 and "設定なし。全部使う" in out and "cinii・ndl・jstage" in out, "(20) 設定が無ければ全部使う(今までどおり)")
        os.environ[kensaku.TSUKAU_NAME] = "openalex, Crossref"
        code, out = run(kensaku, w, "tsukau")
        ok(code == 0 and "使うデータベース: openalex・crossref" in out and "外した" in out and "cinii" in out,
           "(20) 設定した物だけを使い、外した物も出す(大文字と空白は気にしない)")
        code, out = run(kensaku, w, "sagasu", "--db", "cinii", "--q", "空き家", "--ronten", "1")
        ok(code == 2 and "使わないことにした" in out and not os.path.exists(os.path.join(w, "kensaku.jsonl")),
           "(20) 外したデータベースには送らず、検索の記録も残さない")
        code, out = run(kensaku, w, "te", "--db", "cinii", "--q", "空き家", "--ronten", "1", "--kensu", "3", "--memo", "ブラウザで")
        ok(code == 2 and "使わないことにした" in out, "(20) 外したデータベースは、手で検索した記録にもしない")
        ok(run(kensaku, w, "te", "--db", "estat", "--q", "人口", "--ronten", "1", "--kensu", "3")[0] == 0,
           "(20) 道具に無いデータベース(e-Stat など)を手で記録するのは今までどおり")
        run(kensaku, w, "shoroku", "--doi", "10.1234/x")
        ok(calls == ["openalex", "crossref"], "(20) 抄録も、外した Semantic Scholar には問い合わせない")
        os.environ[kensaku.TSUKAU_NAME] = "cinii,ndl"
        code, out = run(kensaku, w, "shoroku", "--doi", "10.1234/x")
        ok(code == 2 and "どれも設定" in out, "(20) 抄録を取るデータベースがどれも外されていれば、問い合わせずに止める")
        os.environ[kensaku.TSUKAU_NAME] = "cinii,ciniii"
        code, out = run(kensaku, w, "tsukau")
        ok(code == 2 and "知らない名前がある(ciniii)" in out, "(20) 知らない名前(書き違い)があれば止める")
        os.environ[kensaku.TSUKAU_NAME] = "openalex"
        keep_t, keep_f = kensaku.tsukawanai, kensaku.fetch
        kensaku.tsukawanai = lambda db: None
        kensaku.fetch = lambda url, timeout: (None, "shippai", "試験(ネットに出ない)")
        try:
            run(kensaku, w, "sagasu", "--db", "cinii", "--q", "空き家", "--ronten", "1")
        finally:
            kensaku.tsukawanai, kensaku.fetch = keep_t, keep_f
        ok(os.path.exists(os.path.join(w, "kensaku.jsonl")), "(9) 関門を外すと、外したデータベースへの検索が走ってしまう(上の試験が効いている)")
    finally:
        kensaku.user_env, kensaku.okuru = keep_ue, keep_ok
        os.environ.pop(kensaku.TSUKAU_NAME, None)
        if old is not None:
            os.environ[kensaku.TSUKAU_NAME] = old


def part_settei():
    print("(21) ID・キー・使うデータベースをスキルの設定ファイルから読み、外したサイトは本文の置き場も候補も確かめのページも開かない(D84 の7)")
    w = wdir("st1")
    sp = os.path.join(TMP, "settei1", "settings.json")
    keep_s = os.environ.get(kensaku.SETTEI_ENV)
    keep_id = os.environ.pop(kensaku.APPID_NAME, None)
    keep_ue = kensaku.user_env
    kensaku.user_env = lambda name: None          # この PC のアカウントの環境変数を読まない
    os.environ[kensaku.SETTEI_ENV] = sp
    try:
        code, out = run(kensaku, w, "settei")
        d = json.load(open(sp, encoding="utf-8"))
        ok(code == 0 and "ひな形を作った" in out and d == {"CINII_APPID": "", "OPENALEX_API_KEY": "", "BUNKEN_DB": ""}
           and "置いていない" in out, "(21) settei は設定ファイルのひな形を作り、どの名前も置いていないと出す")
        kyotsu.write_text(sp, json.dumps({"CINII_APPID": "abcdefgh12345678", "BUNKEN_DB": ["openalex", "Crossref"]}))
        code, out = run(kensaku, w, "settei")
        ok(kensaku.appid() == "abcdefgh12345678" and "abcdefgh12345678" not in out and "CINII_APPID: 設定ファイルから読む" in out,
           "(21) ID を設定ファイルから読み、値は画面に出さない")
        ok(kensaku.tsukau_db() == ["openalex", "crossref"], "(21) 使うデータベースは設定ファイルの並び(大文字も読む)")
        os.environ[kensaku.APPID_NAME] = "zzzzzzzz99999999"
        ok(kensaku.appid() == "zzzzzzzz99999999", "(21) この端末の環境変数があれば、設定ファイルより先に読む")
        os.environ.pop(kensaku.APPID_NAME, None)
        code, out = run(honbun, w, "toru", "--n", "1", "--url", "https://www.jstage.jst.go.jp/article/x/1/_pdf")
        ok(code == 2 and "外した jstage のサイト" in out and not os.path.exists(os.path.join(w, "honbun.jsonl")),
           "(21) 外した J-STAGE の本文の PDF は開かず、記録も残さない")
        code, out = run(kensaku, w, "tsuika", "--ronten", "1", "--dai", "x", "--url", "https://cir.nii.ac.jp/crid/1", "--keiro", "CiNii")
        ok(code == 2 and "外した cinii のサイト" in out, "(21) 外した CiNii の URL は候補に足さない")
        code, out = run(kensaku, w, "te", "--db", "CiNii", "--q", "x", "--ronten", "1", "--kensu", "3", "--memo", "ブラウザで")
        ok(code == 2 and "使わないことにした" in out, "(21) 大文字を混ぜた手の記録も、外したデータベースなら止める")
        wt = teian_setup("st-teian")
        run(teian, wt, "junbi")
        code, out = run(teian, wt, "toru", "T3")
        ok("外した jstage のサイトなので開いていない" in out, "(21) 確かめでページを開き直す時も、外したデータベースのサイトは開かない")
        keep_t = kensaku.tsukawanai_url
        kensaku.tsukawanai_url = lambda url: None
        try:
            with honbun_net([(None, "shippai", "HTTP 403", "")]):
                run(honbun, w, "toru", "--n", "1", "--url", "https://www.jstage.jst.go.jp/article/x/1/_pdf")
        finally:
            kensaku.tsukawanai_url = keep_t
        ok(os.path.exists(os.path.join(w, "honbun.jsonl")),
           "(9) 関門を外すと、外した J-STAGE の PDF を取りに行ってしまう(上の試験が効いている)")
        kyotsu.write_text(sp, "{\"BUNKEN_DB\": \"openalex\",}")
        code, out = run(kensaku, w, "tsukau")
        ok(code == 2 and "読めない" in out, "(21) 設定ファイルが壊れていれば、全部使う形に黙って戻さずに止める")
    finally:
        kensaku.user_env = keep_ue
        if keep_s is None:
            os.environ.pop(kensaku.SETTEI_ENV, None)
        else:
            os.environ[kensaku.SETTEI_ENV] = keep_s
        if keep_id is not None:
            os.environ[kensaku.APPID_NAME] = keep_id


def part_kakunin():
    print("(17) 読み切っていない行・論点の承認・測れなかった物の例外(課題 ch-3ni・ch-21p・ch-2pi)")
    top, w = wdir("kn1out"), wdir("kn1")
    os.makedirs(top, exist_ok=True)
    f = os.path.join(top, "daicho.json")
    sf = os.path.join(top, "daicho.shoshi.json")
    # 全文OA なのに抄録どまりの行は、訳が無いと入れない
    ichibu = {"han": "本文の1〜3節より", "shurui": "事例研究", "kajo": ["A市を調べた研究"]}
    ok(put(f, {"atama": ATAMA, "gyou": [gyou(1, seidoku="抄録どまり", yoshi=ichibu)]})[0] == 1,
       "(17) 全文OA なのに抄録どまりで、読み切れなかった訳の無い行は入れない")
    ok(put(f, {"atama": ATAMA, "gyou": [gyou(1, seidoku="抄録どまり", yoshi=ichibu, yomikiranai="時間切れ(1〜3節まで読んだ)")]})[0] == 1,
       "(17) 訳は決まった語(200頁以上・画像でも読めない頁・出版社に断られた・開けなかった・置き場に本文が無い)で始める。時間切れは訳にならない")
    ok(put(f, {"atama": ATAMA, "gyou": [gyou(1, seidoku="抄録どまり", yoshi=ichibu, yomikiranai="200頁以上(1〜3節まで読んだ)")]})[0] == 0,
       "(17) 訳と読んだ範囲を書いた行は入れる")
    # 無料で読める置き場がある候補を採った行
    works = [oa_work("W9", "Tourism demand forecasting", "Ann Lee", 2020, "10.1234/oa", oa_url="https://repo.example.org/9.pdf")]
    with eigo([(oa_json(1, works), "ok", "", {"x-ratelimit-remaining-usd": "0.09"})], "kn1"):
        run(kensaku, w, "sagasu", "--db", "openalex", "--q", "tourism demand", "--ronten", "1")
    run(kensaku, w, "kime", "K0001", "sai", "--gyou", "2")
    put(f, {"gyou": [eigo_gyou(2, "10.1234/oa", "Demand fell sharply.", link=[{"kouho": "K0001", "doi": True}])],
            "tansaku": {"mae": "見つからなかった論点なし", "bloku": []}})
    for n in (1, 2):
        shoshi_row(sf, n, "山田 太郎")
    code, out = run(daicho, f, "kaku", "--w", w)
    ok(code == 1 and "#2: 本文が無料で読める(https://repo.example.org/9.pdf)のに、置き場を開いた記録が無い" in out
       and "#1: 本文が無料で読める(入手状況が全文OA)のに、置き場を開いた記録が無い" in out and "論点の案の記録が無い" in out,
       "(17) 本文が無料で読めるのに置き場を開いた記録の無い行(全文OA・無料の置き場のある候補)と、論点の記録の無い台帳は作らない")
    with honbun_net([(PDF_FAKE, "ok", "", "application/pdf"), (None, "shippai", "HTTP 403", "")], pages=["本文の文" * 40] * 250):
        run(honbun, w, "toru", "--n", "1", "--url", "https://www.jstage.jst.go.jp/article/x/1/_pdf")
        run(honbun, w, "toru", "--n", "2", "--url", "https://repo.example.org/9.pdf")
    run(kiroku, "ronten", w, "an", "--ronten", "1=空き家バンクの仕組みと実績を扱った研究", "--kijun", "国内外の空き家の利活用を扱った研究")
    ok("承認(kiroku.py ronten … shonin)か未承認" in run(daicho, f, "kaku", "--w", w)[1], "(17) 案だけで承認も未承認の印も無いと止まる")
    run(kiroku, "ronten", w, "mishonin")
    ok("「(未承認)」が無い" in run(daicho, f, "kaku", "--w", w)[1], "(17) 未承認で進めたのに頭の部分に「(未承認)」が無いと止まる")
    mi = dict(ATAMA, kijun=ATAMA["kijun"] + "(未承認)",
              ronten=[dict(x, bun=x["bun"] + "(未承認)") for x in ATAMA["ronten"]])
    put(f, {"atama": mi, "gyou": [{"n": 2, "yomikiranai": "出版社に断られた(無料の置き場も HTTP 403)"}]})
    code, out = run(daicho, f, "kaku", "--w", w)
    d = json.load(open(f, encoding="utf-8"))
    ok(code == 0 and "★論点と適合の基準は未承認" in out and "- 論点2(反論・限界): 空き家バンクが効かなかった研究(未承認)" in out
       and "- 適合の基準: 国内外の空き家の利活用を扱った研究(未承認)" in out,
       "(17) 未承認の時は、納品のチャットに見せる論点と適合の基準の文を出す")
    ok("★本文が無料で読めるのに、本文を読み切っていない行 2件" in out and "- #2: 出版社に断られた" in out
       and any(x.startswith("本文が無料で読めるのに、本文を読み切っていない行: #1(200頁以上") for x in d["genkai_kikai"]),
       "(17) 読み切っていない行は、限界の欄に並べ、納品のチャットに出す一覧も出す")
    keep = daicho.kakunin_w
    daicho.kakunin_w = lambda d, w: ([], [])
    try:
        run(kiroku, "ronten", w, "an", "--ronten", "1=x")
        ok(run(daicho, f, "kaku", "--w", w)[0] == 0, "(9) 記録との照らしを外すと、承認の記録の無い台帳が作られてしまう(上の試験が効いている)")
    finally:
        daicho.kakunin_w = keep
    # 測れなかった物が例外だけかを決める(reigai)
    top, w = wdir("rg1out"), wdir("rg1")
    os.makedirs(os.path.join(w, "shoroku"), exist_ok=True)
    os.makedirs(top, exist_ok=True)
    f = os.path.join(top, "daicho.json")
    kot = eigo_gyou(1, "10.1177/kot1", "Prices rose by 5%.", biko="出版社のページは機械の取得を断った(HTTP 403)。書誌は Crossref の記録で確定")
    put(f, {"atama": ATAMA, "gyou": [kot, eigo_gyou(2, "10.1016/x", "Demand fell sharply.")]})
    rg_shoshi(top, {1: "Pricing of tourism services", 2: "Demand forecasting for tourism"})
    rg_md(os.path.join(w, "daicho.md"), "# 文献台帳\n\n| # | 書誌 |\n| 1 | a |\n| 2 | b |\n")
    for name, dai, body in (("10.1177_kot1", "Pricing of tourism services: a study", "We find that Prices rose by 5%. Then"),
                            ("10.1016_x", "Demand forecasting for tourism", "After 2020, Demand fell sharply. Then")):
        kyotsu.write_text(os.path.join(w, "shoroku", name + ".txt"), "出どころ: https://api.semanticscholar.org/x\n題名: %s\n\n%s\n" % (dai, body))
    outf = os.path.join(w, "checker.txt")

    def reigai(ihan="0", b=0, bgyou=""):
        kyotsu.write_text(outf, REIGAI_OUT % {"ihan": ihan, "b": b, "bgyou": bgyou})
        return run(daicho, f, "reigai", "--kara", outf, "--w", w)
    code, out = reigai()
    ok(code == 0 and "納めてよい" in out and "段階A #1" in out and "段階C #2" in out and "チェッカーが英語の本文を読めない" in out,
       "(17) 測れなかった物が、断られた行と、抜き書きが保存した抄録に在る英語の行だけなら、納めてよいと一覧を出す")
    ok(reigai(b=1, bgyou="   - L5 10.1016/x —— 著者名= 表記系が違う\n")[0] == 1, "(17) 段階B の測れなかった物は例外にしない")
    ok(reigai(ihan="1")[0] == 1, "(17) 違反があれば例外にしない")
    kyotsu.write_text(os.path.join(w, "shoroku", "10.1016_x.txt"), "出どころ: https://api.semanticscholar.org/x\n題名: Demand forecasting for tourism\n\nDemand rose.\n")
    code, out = reigai()
    ok(code == 1 and "原文のまま無い" in out, "(17) 英語の行の抜き書きが保存した抄録に無ければ例外にしない")
    keep = daicho.eigo_nukigaki
    daicho.eigo_nukigaki = lambda r, w, sk=None, dai=None: (True, "")
    try:
        ok(reigai()[0] == 0, "(9) 抄録との照らしを外すと、抄録に無い抜き書きが例外で通ってしまう(上の試験が効いている)")
    finally:
        daicho.eigo_nukigaki = keep
    put(f, {"gyou": [{"n": 1, "biko": "Crossref で確定"}]})
    kyotsu.write_text(os.path.join(w, "shoroku", "10.1016_x.txt"), "出どころ: x\n題名: Demand forecasting for tourism\n\nAfter 2020 demand fell sharply.\n")
    ok(reigai()[0] == 1, "(17) 備考に断られたと書いていない 403 の行は例外にしない")
    put(f, {"gyou": [{"n": 1, "biko": "出版社のページは機械の取得を断った(HTTP 403)"}, {"n": 2, "gengo": "和"}]})
    ok(reigai()[0] == 1, "(17) 和文の行の測れなかった物は例外にしない")
    r2 = json.load(open(f, encoding="utf-8"))["gyou"][1]
    ok(daicho.inyou_ari(r2, w, "「予測できない」")[0] is False and daicho.inyou_ari(r2, w, "「demand fell sharply.」")[0] is True and daicho.inyou_ari(r2, w, "demand fell sharply.")[0] is True,
       "(17) 要旨の「」は、その文そのものを抄録と照らす(英語の行の要旨の日本語の「」を、行の抜き書きで代わりに通さない)")
    # 本文の抜き書きは、その行の置き場を開いた記録の PDF だけで照らす(別の行の PDF・確かめ役が控えた原典に在っても例外にしない。ch-9h8)
    src3 = os.path.join(TMP, "rg-body.pdf")
    make_pdf(src3, ["The tourism demand recovered after the pandemic in all regions."])
    b3 = open(src3, "rb").read()
    bun3 = "The tourism demand recovered after the pandemic"
    r3 = dict(eigo_gyou(3, "10.1016/x3", bun3), nukigaki=[{"bun": bun3, "basho": "本文 p.1"}])
    os.makedirs(os.path.join(w, "kaime", "1", "genten"), exist_ok=True)
    shutil.copy(src3, os.path.join(w, "kaime", "1", "genten", "p3.pdf"))
    with honbun_net([(b3, "ok", "", "application/pdf")]):
        run(honbun, w, "toru", "--n", "3", "--url", "https://repo.example.org/other3.pdf")
    nai = daicho.eigo_nukigaki(r3, w)
    nai_q = daicho.inyou_ari(r3, w, "「recovered after the pandemic」")
    keep = daicho.gyou_pdfs
    daicho.gyou_pdfs = lambda r, w_, sk=None: [os.path.join(rt, x) for rt, _d, fs in os.walk(w_) for x in fs if x.endswith(".pdf")]
    try:
        mae = daicho.eigo_nukigaki(r3, w)
    finally:
        daicho.gyou_pdfs = keep
    with honbun_net([(b3, "ok", "", "application/pdf")]):
        run(honbun, w, "toru", "--n", "3", "--url", "https://doi.org/10.1016/x3")
    ari = daicho.eigo_nukigaki(r3, w)
    ok(nai[0] is False and "照らしていない" in nai[1] and "other3.pdf" in nai[1] and nai_q[0] is False and "照らしていない" in nai_q[1]
       and ari[0] is True and daicho.inyou_ari(r3, w, "「recovered after the pandemic」")[0] is True,
       "(17) 英語の行の本文の抜き書きと要旨の「」は、その行の置き場を開いた PDF で照らし、別の文献の PDF や確かめ役の控えに在るだけでは"
       "例外にしない(照らす PDF が無い訳を出す)")
    os.makedirs(os.path.join(w, "shoroku"), exist_ok=True)
    kyotsu.write_text(os.path.join(w, "shoroku", "2101.12345.txt"), "出どころ: https://export.arxiv.org/x\n題名: t\n\nWe propose a new model.\n")
    ra = dict(gyou(4, gengo="英", link=[{"url": "https://arxiv.org/abs/2101.12345v2"}]),
              nukigaki=[{"bun": "We propose a new model.", "basho": "抄録(arXiv の記録)"}])
    ok(daicho.eigo_nukigaki(ra, w)[0] is True and daicho.inyou_ari(ra, w, "「…」")[0] is False,
       "(17) DOI の無い arXiv の行は、版を外した番号で保存した抄録で照らす。「…」だけの引用は落ちずに照らせないと出す")
    ok(mae[0] is True, "(9) 作業用フォルダの PDF を全部見ると、別の文献の PDF や控えで例外になってしまう(上の試験が効いている)")
    # 証明書の誤りで出版社のページにつながらない行と、書誌欄の題名が『』の行の例外(D81。Emerald の論文と報告書の行が毎回止まった)
    top2, w2 = wdir("rg2out"), wdir("rg2")
    os.makedirs(os.path.join(w2, "shoroku"), exist_ok=True)
    os.makedirs(top2, exist_ok=True)
    f2 = os.path.join(top2, "daicho.json")
    ssl1 = dict(eigo_gyou(1, "10.1108/ssl1", "Libraries help local firms."),
                biko="出版社のページは機械の取得を断った(Python からは証明書の誤りでつながらない)。書誌は Crossref の記録で確定")
    rep2 = dict(gyou(2, gengo="和", shubetsu="白書・報告書", link=[{"honbun": True, "url": "https://repo.example.org/rep2.pdf"}], nyushu="全文OA",
                     seidoku="本文精読済み"), nukigaki=[{"bun": "Support services spread in 2015.", "basho": "本文 p.1"}])
    put(f2, {"atama": ATAMA, "gyou": [ssl1, rep2]})
    rg_shoshi(top2, {1: "Libraries and local firms", 2: "Report on library support services"})
    kyotsu.write_text(os.path.join(w2, "shoroku", "10.1108_ssl1.txt"), "出どころ: https://api.semanticscholar.org/x\n題名: Libraries and local firms\n\nWe show that Libraries help local firms. Then\n")
    src2 = os.path.join(TMP, "rg2-rep.pdf")
    make_pdf(src2, ["Report on library support services. In the survey, Support services spread in 2015. Many libraries joined."])
    with honbun_net([(open(src2, "rb").read(), "ok", "", "application/pdf")], pages=None):
        run(honbun, w2, "toru", "--n", "2", "--url", "https://repo.example.org/rep2.pdf")
    out2 = os.path.join(w2, "checker.txt")
    ssl_out = (REIGAI_OUT % {"ihan": "0", "b": 0, "bgyou": ""}).replace(
        "L4 https://doi.org/10.1177/kot1 —— HTTP 403(拒まれた。★リンクの誤りとは限らない)",
        "L4 https://doi.org/10.1108/ssl1 —— 接続できなかった(SSLCertVerificationError)").replace(
        "L4 抜き書き「Prices rose by 5%.」 —— 本文が取れていない(unreachable)", "L4 抜き書き「Libraries help local firms.」 —— 本文が取れていない(unreachable)").replace(
        "L5 抜き書き「Demand fell sharply.」 —— ページが散文を渡していない(和文の連なりの最長 0 < 100)",
        "L5 抜き書き「Support services spread in 2015.」 —— 対照が置けない(書誌欄に題名の鍵括弧が無い)")

    def reigai2(md_row2="| 2 | 協議会(2016)『課題解決支援の報告書』協議会 |", kara=None):
        rg_md(os.path.join(w2, "daicho.md"), "# 文献台帳\n\n| # | 書誌 |\n| 1 | Aono(2024)「x」 |\n%s\n" % md_row2)
        kyotsu.write_text(out2, kara or ssl_out)
        return run(daicho, f2, "reigai", "--kara", out2, "--w", w2)
    code, out = reigai2()
    ok(code == 0 and "証明書の誤りでつながらない" in out and "出版社のページを機械が取れない行" in out and "書誌欄の題名が『』で、チェッカーが対照を置けない" in out,
       "(17) 証明書の誤りで出版社のページにつながらない行(備考と DOI)と、書誌欄の題名が『』の行の抜き書きは、保存した抄録・その行の本文PDF で照らして例外にする")
    ok(reigai2("| 2 | 協議会(2016)「課題解決支援の報告書」協議会 |")[0] == 1, "(17) 書誌欄の題名が『』でない行の「対照が置けない」は例外にしない")
    put(f2, {"gyou": [{"n": 2, "nukigaki": [{"bun": "Support services shrank in 2015.", "basho": "本文 p.1"}]}]})
    ok(reigai2()[0] == 1, "(17) 書誌欄の題名が『』の行でも、抜き書きがその行の本文PDF に無ければ例外にしない")
    put(f2, {"gyou": [{"n": 2, "nukigaki": [{"bun": "Support services spread in 2015.", "basho": "本文 p.1"}]}, {"n": 1, "biko": "書誌は Crossref の記録で確定"}]})
    ok(reigai2()[0] == 1, "(17) 証明書の誤りでも、備考に断られた・証明書の誤りと書いていない行は例外にしない")
    put(f2, {"gyou": [{"n": 1, "biko": ssl1["biko"]}]})
    keep = daicho.KOTOWA_RE
    daicho.KOTOWA_RE = re.compile(r"HTTP 40[13]")
    try:
        ok(reigai2()[0] == 1, "(9) 証明書の誤りを断られた行に数えないと、Emerald の論文の行が毎回止まる(上の試験が効いている)")
    finally:
        daicho.KOTOWA_RE = keep
    # 例外の抜け道を塞いだ5つ(2026-11-03 の最後の評価。直した経緯を知らない判定役が、写しの上で誤った行を通した)
    # (1) 段階A: 断られたリンクは、行の DOI のリンクか、honbun.py でこの行の番号で開けた置き場だけ。備考の「断っていない」は数えない
    pub = "https://publisher.example.com/article/ssl1"
    kara_pub = ssl_out.replace("L4 https://doi.org/10.1108/ssl1 —— 接続できなかった", "L4 %s —— 接続できなかった" % pub)
    code, out = reigai2(kara=kara_pub)
    nai_pub = code == 1 and "行の DOI のリンクでなく" in out
    ok(nai_pub and daicho.kotowa_row({"link": [{"url": "https://doi.org/10.1234/x"}], "biko": "出版社は機械の取得を断っていない"}) is False
       and daicho.kotowa_row({"link": [{"url": "https://doi.org/10.1234/x"}], "biko": "出版社は機械の取得を断った"}) is True,
       "(17) 断られた行の段階A の例外は、行の DOI のリンクだけにし、DOI でない開けていない置き場は例外にしない。備考の「断っていない」は断られた行に数えない")
    keep = daicho.kotowa_link
    daicho.kotowa_link = lambda r, url, w: "x"
    try:
        ok(reigai2(kara=kara_pub)[0] == 0, "(9) リンクを見ずに例外にすると、DOI でない開けていない置き場が何も照らさずに通る(上の試験が効いている)")
    finally:
        daicho.kotowa_link = keep
    # (2) 段階C: 英語の断られた行でも、区切りが短い・括弧が閉じないなど書き方の訳は例外にしない。代わりの照らしにも6字の下限
    kara_kizami = ssl_out.replace("L4 抜き書き「Libraries help local firms.」 —— 本文が取れていない(unreachable)",
                                  "L4 抜き書き「Libraries help local firms.」 —— 区切りが 6字に満たない —— 照らしていない")
    r_kizami = dict(ssl1, nukigaki=[{"bun": "We…help local firms.", "basho": "抄録(Semantic Scholar の記録)"}])
    ok(reigai2(kara=kara_kizami)[0] == 1 and daicho.eigo_nukigaki(r_kizami, w2)[0] is False and daicho.kugiri_mijikai("We…help local firms.")
       and not daicho.kugiri_mijikai("We show that…help local firms."),
       "(17) 区切りが6字に満たないという訳は、英語の断られた行でも例外にせず、代わりの照らしも6字に満たない区切りを照らさない")
    # (3) 要旨の「」は、チェッカーの一覧で90字に切れた字でなく、要旨の全文で照らす
    zen = "Libraries help local firms grow when public programmes connect owners to advisers, data, and" + " a network of lenders across the region."
    kyotsu.write_text(os.path.join(w2, "shoroku", "10.1108_ssl1.txt"), "出どころ: x\n題名: Libraries and local firms\n\n%s Then\n" % zen)
    r_zen = dict(ssl1, yoshi={"han": "抄録より", "kajo": ["「%s」" % zen]})
    r_kawa = dict(ssl1, yoshi={"han": "抄録より", "kajo": ["「%s」" % zen.replace("lenders across the region", "lenders who refused to help")]})
    kire = "「" + zen[:89]
    ok(daicho.inyou_ari(r_zen, w2, kire)[0] is True and daicho.inyou_ari(r_kawa, w2, kire)[0] is False
       and daicho.inyou_ari(ssl1, w2, kire)[0] is False,
       "(17) 要旨の「」は、一覧で切れた頭だけでなく要旨の全文で照らし、全文が要旨に見つからない切れた引用は通さない")
    # (4) 代わりの照らしの抄録・本文PDF は、この行の題名が在る物だけ(別の文献の抄録・PDF で通さない)
    kyotsu.write_text(os.path.join(w2, "shoroku", "10.1108_ssl1.txt"), "出どころ: x\n題名: A different paper on banks\n\nWe show that Libraries help local firms. Then\n")
    code, out = reigai2()
    betsu_sho = code == 1 and "題名が、この行の題名と合わない" in out
    kyotsu.write_text(os.path.join(w2, "shoroku", "10.1108_ssl1.txt"), "出どころ: x\n題名: Libraries and local firms\n\nWe show that Libraries help local firms. Then\n")
    ok(betsu_sho and reigai2()[0] == 0 and daicho.pdf_ni_aru([src2], "Support services spread in 2015.", "Report on library support services")
       and not daicho.pdf_ni_aru([src2], "Support services spread in 2015.", "Annual statistics of museums"),
       "(17) 代わりの照らしは、題名がこの行の題名と合わない抄録と、この行の題名が文字に無い本文PDF では通さない")
    keep = daicho.DAI_KASHIRA
    daicho.DAI_KASHIRA = 0
    try:
        ok(not daicho.dai_ni_aru("Libraries and local firms", "A different paper on banks"),
           "(9) 題名の頭が空なら、題名を照らしたことにしない(上の試験の題名の照らしが空回りしない)")
    finally:
        daicho.DAI_KASHIRA = keep
    rg_shoshi(top2, {2: "Report on library support services"})
    ok(reigai2()[0] == 1, "(17) 書誌の項目ファイルに題名の無い行は、代わりの照らしの文献が同じ物か確かめられないので例外にしない")
    rg_shoshi(top2, {1: "Libraries and local firms", 2: "Report on library support services"})
    # (5) 渡したチェッカーの出力が、いまの台帳の行から出た物か(古い出力で、後で書き換えた行を通さない)
    ok(reigai2()[0] == 0, "(17) 前提: いまの行から出た出力なら納めてよい")
    md2 = os.path.join(w2, "daicho.md")
    kyotsu.write_text(md2, open(md2, encoding="utf-8").read().replace("Aono(2024)「x」", "Aono(2024)「y」"))
    code, out = run(daicho, f2, "reigai", "--kara", out2, "--w", w2)
    furui = code == 1 and "この出力の後に台帳の行が変わった" in out
    # 出力の後に kaku で書き直した(記録が出力より後にある)時も、出力の時点の記録で比べる
    kyotsu.write_text(out2, ssl_out)
    with open(md2 + ".kagi.jsonl", "a", encoding="utf-8", newline="\n") as fk:
        fk.write(json.dumps({"t": time.time() + 60, "kagi": daicho.md_kagi(md2)}) + "\n")
    code, out = run(daicho, f2, "reigai", "--kara", out2, "--w", w2)
    ato = code == 1 and "この出力の後に台帳の行が変わった" in out
    # 行の字が同じでも、Markdown の行の位置がずれたら別の物(reigai は行の位置で台帳の行を引くため)
    rg_md(md2, "# 文献台帳\n\n| # | 書誌 |\n| 1 | Aono(2024)「x」 |\n| 2 | 協議会(2016)『課題解決支援の報告書』協議会 |\n")
    kyotsu.write_text(out2, ssl_out)
    kyotsu.write_text(md2, "# 文献台帳\n\n\n| # | 書誌 |\n| 1 | Aono(2024)「x」 |\n| 2 | 協議会(2016)『課題解決支援の報告書』協議会 |\n")
    code, out = run(daicho, f2, "reigai", "--kara", out2, "--w", w2)
    zure = code == 1 and "この出力の後に台帳の行が変わった" in out
    ok(ato and zure, "(17) 出力の後に書き直した記録では比べず、行の字が同じでも位置がずれたら、古い出力として止める")
    os.remove(md2 + ".kagi.jsonl")
    code, out = run(daicho, f2, "reigai", "--kara", out2, "--w", w2)
    ok(furui and code == 1 and "書いた記録が無い" in out,
       "(17) チェッカーの出力の後に台帳の行が変わった時と、kaku --w で書いた記録が無い時は、例外にしない")
    keep = daicho.md_kagi
    daicho.md_kagi = lambda p: "onaji"
    try:
        rg_md(md2, "# 文献台帳\n\n| # | 書誌 |\n| 1 | Aono(2024)「x」 |\n| 2 | 協議会(2016)『課題解決支援の報告書』協議会 |\n")
        kyotsu.write_text(out2, ssl_out)
        kyotsu.write_text(md2, open(md2, encoding="utf-8").read().replace("Aono(2024)「x」", "Aono(2024)「y」"))
        ok(run(daicho, f2, "reigai", "--kara", out2, "--w", w2)[0] == 0, "(9) 行の指紋を取らないと、古い出力で書き換えた行が通る(上の試験が効いている)")
    finally:
        daicho.md_kagi = keep
    # (1) の続き: DOI でない置き場も、この行の番号で honbun.py が開けていれば例外にする(中身は段階C の代わりの照らしで見る)
    with honbun_net([(open(src2, "rb").read(), "ok", "", "application/pdf")], pages=None):
        run(honbun, w2, "toru", "--n", "1", "--url", pub)
    code, out = reigai2(kara=kara_pub)
    ok(code == 0 and "honbun.py で開けた" in out, "(17) DOI でない置き場は、この行の番号で honbun.py が開けていれば段階A の例外にする")
    ok(kaime.soroe("一般社団法人 人工知能学会", "shuppan") == kaime.soroe("人工知能学会", "shuppan")
       and kaime.soroe("Elsevier Ltd", "shuppan") == kaime.soroe("Elsevier", "shuppan")
       and kaime.soroe("日本観光研究学会", "shuppan") != kaime.soroe("日本国際観光学会", "shuppan"),
       "(13) 機械の照らしは、出版社の法人の種類の語(一般社団法人・Ltd など)を除いてから比べる(別の名前は別のまま)")


def rg_md(path, text):
    """機械用の Markdown を書き、kaku --w と同じく書いた記録(時刻と行の指紋)を残す(reigai が古いチェッカーの出力を止めるため)"""
    kyotsu.write_text(path, text)
    with open(path + ".kagi.jsonl", "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps({"t": time.time() - 2, "kagi": daicho.md_kagi(path)}) + "\n")


def rg_shoshi(top, dais):
    """書誌の項目ファイル(題名だけ)を書く。dais= {行の番号: 題名}"""
    kyotsu.write_text(os.path.join(top, "daicho.shoshi.json"), json.dumps(
        {"kind": shoshi.KIND, "v": shoshi.V, "rows": [{"n": n, "dai": t} for n, t in sorted(dais.items())]}, ensure_ascii=False))


def pdf_buhin():
    """PDF を読む部品(PyMuPDF)。新しい名前 pymupdf か古い名前 fitz(スクリプトと同じ読み方)。無ければ None"""
    try:
        import pymupdf
        return pymupdf
    except ImportError:
        try:
            import fitz
            return fitz
        except ImportError:
            return None


def make_pdf(path, texts):
    """頁ごとの文字で小さな PDF を作る(英数字だけ。PyMuPDF の既定の字形で書ける字)"""
    pymupdf = pdf_buhin()
    doc = pymupdf.open()
    for t in texts:
        doc.new_page().insert_text((50, 72), t)
    doc.save(path)
    doc.close()


def part_honbun():
    print("(18) 本文の置き場を開いた記録(honbun.py・課題 ch-3ni の2回目の直し)")
    w = wdir("hb1")
    os.makedirs(w, exist_ok=True)
    long = chr(10).join(["This page has enough words to be read as body text %d." % i for i in range(5)])
    src = os.path.join(TMP, "hb-src.pdf")
    make_pdf(src, [long, "Fig. 1", long])
    body = open(src, "rb").read()
    with honbun_net([(body, "ok", "", "application/pdf")]):
        code, out = run(honbun, w, "toru", "--n", "1", "--url", "https://repo.example.org/1.pdf")
    recs = kyotsu.read_log(os.path.join(w, honbun.LOG), honbun.KIND)
    ok(code == 0 and recs[-1]["peeji"] == 3 and recs[-1]["kuzure"] == [2] and os.path.exists(os.path.join(w, recs[-1]["file"]))
       and "gazo --n 1 --k 1 --peeji 2" in out, "(18) 置き場を開いて保存し、頁の数と文字の取れない頁を記録して、画像にする命令を出す")
    seidoku = dict(gyou(1), seidoku="本文精読済み")
    x = honbun.by_n(honbun.kiroku(w))[1]
    ok(any("文字の取れない頁 2 を画像にした記録が無い" in m for m in daicho.honbun_problems(seidoku, None, x)),
       "(18) 文字の取れない頁を画像にせずに本文精読済みにした行は通さない")
    code, out = run(honbun, w, "gazo", "--n", "1", "--peeji", "2")
    ok(code == 0 and os.path.exists(os.path.join(w, "honbun", "1-1-p2.png"))
       and daicho.honbun_problems(seidoku, None, honbun.by_n(honbun.kiroku(w))[1]) == [],
       "(18) 頁を画像にした記録があれば通す(画像は回のフォルダの外の作業用フォルダに置く)")
    tochu = dict(gyou(1), seidoku="抄録どまり", yomikiranai="200頁以上(1〜3節まで読んだ)")
    ok(any("読み切っていない" in m for m in daicho.honbun_problems(tochu, None, honbun.by_n(honbun.kiroku(w))[1])),
       "(18) 開けた本文が200頁に満たないのに「200頁以上」を訳にした行は通さない")
    ok(run(honbun, w, "gazo", "--n", "2", "--peeji", "1")[0] == 2, "(18) 開いた記録の無い行の頁は画像にしない")
    with honbun_net([(b"<html><body><img src=fig.png></body></html>", "ok", "", "text/html"), (None, "shippai", "HTTP 503", "")]):
        run(honbun, w, "toru", "--n", "3", "--url", "https://ars.example.org/fig.jpg")
        code, out = run(honbun, w, "toru", "--n", "4", "--url", "https://hit-u.example.org/4.pdf")
    hb = honbun.by_n(honbun.kiroku(w))
    ok(daicho.honbun_problems(dict(gyou(3), seidoku="抄録どまり", yomikiranai="置き場に本文が無い(図の画像だけ)"), "x", hb[3]) == []
       and code == 3 and daicho.honbun_problems(dict(gyou(4), nyushu="未入手", seidoku="抄録どまり", yomikiranai="開けなかった(HTTP 503)"), "x", hb[4]) == []
       and daicho.honbun_problems(dict(gyou(4), seidoku="本文精読済み"), "x", hb[4]) != [],
       "(18) 本文の無い置き場・開けなかった置き場は、記録どおりの訳なら通し、開けなかったのに本文精読済みは通さない")
    kensaku.jstage_save(w, {"kirareta": "2026-11-02T05:00:00+09:00"})
    called = []
    with honbun_net([]):
        honbun.fetch_bytes = lambda url, timeout: called.append(url)
        code, out = run(honbun, w, "toru", "--n", "5", "--url", "https://www.jstage.jst.go.jp/article/x/5/_pdf")
    ok(code == 3 and not called and honbun.kiroku(w)[-1]["jotai"] == "yameta", "(18) この回に J-STAGE に切られた後は開かず、開いていないことを1行残す")
    # 別の文献を開いた記録で通さない(行の番号が付け替わった行が、採らなかった候補の PDF を開いた記録を持っていた。2026-11-02 の配る束の試し)
    K = honbun.kagi
    onaji = [  # 同じ文献の置き場の組(鍵が合わないと、正しい行が止まる)
        ("https://www.jstage.jst.go.jp/article/jslis/68/2/68_95/_pdf", "https://www.jstage.jst.go.jp/article/jslis/68/2/68_95/_article/-char/ja/"),
        ("https://www.jstage.jst.go.jp/article/jkg/58/7/58_KJ00004963193/_pdf", "http://jstage.jst.go.jp/article/jkg/58/7/58_kj00004963193/_article"),
        ("https://www.jstage.jst.go.jp/article/x/9/2/9_1/_html/-char/ja", "https://www.jstage.jst.go.jp/article/x/9/2/9_1/_article"),
        ("https://bmcpublichealth.biomedcentral.com/counter/pdf/10.1186/s12889-024-18535-5", "https://doi.org/10.1186/S12889-024-18535-5"),
        ("https://example.org/doi/pdf/10.1080/1368.2020.1?download=true", "https://doi.org/10.1080/1368.2020.1"),
        ("https://link.example.org/content/pdf/10.1007/s1.pdf", "https://doi.org/10.1007/s1"),
        ("https://journals.plos.org/plosone/article/file?id=10.1371/journal.pone.0123456&type=printable", "https://doi.org/10.1371/journal.pone.0123456"),
        ("https://www.biorxiv.org/content/10.1101/2020.01.01.123456v2.full.pdf", "https://doi.org/10.1101/2020.01.01.123456"),
        ("https://doi.org/10.1002%2Fasi.24000", "https://doi.org/10.1002/asi.24000"),
        ("https://arxiv.org/pdf/2002.07964v3", "https://arxiv.org/abs/2002.07964"),
        ("https://doi.org/10.48550/arXiv.2002.07964", "https://arxiv.org/abs/2002.07964"),
        ("https://arxiv.org/pdf/hep-th/9901001", "https://arxiv.org/abs/hep-th/9901001"),
        ("https://www.ncbi.nlm.nih.gov/pmc/articles/9754953", "https://pmc.ncbi.nlm.nih.gov/articles/PMC9754953/"),
        ("https://europepmc.org/backend/ptpmcrender.fcgi?accid=PMC11069228&blobtype=pdf", "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11069228/"),
        ("https://ira.lib.polyu.edu.hk/bitstream/10397/9005/1/x.pdf", "http://hdl.handle.net/10397/9005"),
        ("https://repo.example.ac.jp/record/2000/files/a.pdf", "https://repo.example.ac.jp/records/2000"),
        ("https://repo.example.ac.jp/?action=repository_uri&item_id=2000", "https://repo.example.ac.jp/records/2000"),
        ("https://dl.ndl.go.jp/pid/1234567", "https://dl.ndl.go.jp/info:ndljp/pid/1234567"),
        ("https://www.sciencedirect.com/science/article/pii/S0160738322001234/pdfft?md5=x", "https://www.sciencedirect.com/science/article/pii/S0160738322001234"),
        ("https://www.mdpi.com/2071-1050/12/3/1234/pdf?version=1580000000", "https://mdpi.com/2071-1050/12/3/1234/pdf"),
        ("https://cir.nii.ac.jp/crid/1390001205508427648?lang=ja", "https://cir.nii.ac.jp/crid/1390001205508427648"),
        ("https://dl.ndl.go.jp/view/download/digidepo_11253596_po_a.pdf?contentNo=1", "https://dl.ndl.go.jp/pid/11253596"),
        ("https://doi.org/10.1002/(SICI)1097-4571(199806)49:8%3C693::AID-ASI4%3E3.0.CO;2-0",
         "https://onlinelibrary.wiley.com/doi/pdf/10.1002/(SICI)1097-4571(199806)49:8<693::AID-ASI4>3.0.CO;2-0"),
    ]
    betsu = [  # 別の文献の置き場の組(鍵が合うと、別の文献を開いた記録で通る)
        ("https://www.jstage.jst.go.jp/article/jslis/60/3/60_KJ00009556443/_pdf", "https://www.jstage.jst.go.jp/article/jslis/68/2/68_95/_article/-char/ja/"),
        ("https://www.library.metro.tokyo.jp/pdf/zenkouto/pdf/2014all.pdf", "https://current.ndl.go.jp/ca1918"),
        ("https://a.example.ac.jp/bitstream/123456789/45/1/a.pdf", "https://b.example.ac.jp/handle/123456789/45"),
        ("https://repo-a.example.ac.jp/records/2000", "https://repo-b.example.ac.jp/records/2000"),
        ("https://doi.org/10.1234/a1", "https://doi.org/10.1234/a10"),
        ("https://www.ncbi.nlm.nih.gov/pmc/articles/PMC1106922/", "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11069228/"),
        ("https://cir.nii.ac.jp/crid/1390001205508427648", "https://cir.nii.ac.jp/crid/1390001205508427649"),
        ("https://www.mext.go.jp/a_menu/shougai/tosho/houkoku/06120702/001.pdf", "https://www.mext.go.jp/a_menu/shougai/tosho/houkoku/06040715/001.pdf"),
        ("https://doi.org/10.1002/(SICI)1097-4571(199806)49:8%3C693::AID-ASI4%3E3.0.CO;2-0",
         "https://doi.org/10.1002/(SICI)1097-4571(199806)49:8%3C700::AID-ASI5%3E3.0.CO;2-X"),
    ]
    zure = [x for x in onaji if not K(x[0]) & K(x[1])] + [x for x in betsu if K(x[0]) & K(x[1])]
    ok(not zure, "(18) 置き場の鍵: 本文PDF と記事・URL の中の DOI・arXiv・PMC・機関リポジトリ・NDL・CiNii の番号は同じ文献にそろえ、別の文献は別にする(外れ= %s)" % zure[:2])
    mine1 = set().union(*[K(x["url"]) for x in gyou(1)["link"]])
    hb = honbun.by_n(honbun.kiroku(w))
    ok(any("この行のリンクにも採った候補の置き場にも無い" in m and "題名と著者がこの行の書誌と合うかを確かめてから" in m
           for m in daicho.honbun_problems(seidoku, None, hb[1], mine1))
       and daicho.honbun_problems(seidoku, None, hb[1], mine1 | K("https://repo.example.org/1.pdf")) == [],
       "(18) 開いた記録の置き場が、行のリンクにも採った候補にも無い行は通さず、行の置き場を開いた記録なら通す")
    # 頁を画像にした記録は、何回目に開いた PDF の物かで照らす
    with honbun_net([(body, "ok", "", "application/pdf"), (body, "ok", "", "application/pdf")]):
        run(honbun, w, "toru", "--n", "6", "--url", "https://repo.example.org/other.pdf")
        run(honbun, w, "toru", "--n", "6", "--url", "https://doi.org/10.1234/a6")
    run(honbun, w, "gazo", "--n", "6", "--k", "1", "--peeji", "2")
    mine6 = set().union(*[K(x["url"]) for x in gyou(6)["link"]])
    s6 = dict(gyou(6), seidoku="本文精読済み")
    ok(any("gazo --n 6 --k 2 --peeji 2" in m for m in daicho.honbun_problems(s6, None, honbun.by_n(honbun.kiroku(w))[6], mine6)),
       "(18) 別の文献の PDF の頁を画像にした記録では、この行の PDF を画像にしたことにしない")
    keep = honbun.by_n

    def by_n_mae(rows):  # 回を記録しない前の形
        out = keep(rows)
        for x in out.values():
            x.pop("gazo_k", None)
        return out
    honbun.by_n = by_n_mae
    try:
        ok(daicho.honbun_problems(s6, None, honbun.by_n(honbun.kiroku(w))[6], mine6) == [],
           "(9) 画像にした PDF の回を記録しないと、別の文献の PDF を画像にした記録で通ってしまう(上の試験が効いている)")
    finally:
        honbun.by_n = keep
    code, out = run(honbun, w, "gazo", "--n", "6", "--peeji", "2")
    ok(code == 0 and "2回目に開いた PDF" in out and os.path.exists(os.path.join(w, "honbun", "6-2-p2.png"))
       and os.path.exists(os.path.join(w, "honbun", "6-1-p2.png"))
       and daicho.honbun_problems(s6, None, honbun.by_n(honbun.kiroku(w))[6], mine6) == []
       and run(honbun, w, "gazo", "--n", "6", "--k", "3", "--peeji", "2")[0] == 2 and "#6 2回目" in run(honbun, w, "miru", "--n", "6")[1],
       "(18) --k を省くと最後に開いた PDF を画像にし(画像の名前は回ごとに分ける)、無い回は使い方の誤りにし、miru は回を出す")
    # 置き場の違う PDF(付録・分冊)はどれも画像にする。同じ置き場を開き直した時は、どれかの回を画像にすればよい
    l11 = [{"url": "https://repo.example.org/11/main.pdf"}, {"url": "https://repo.example.org/11/appendix.pdf"}]
    with honbun_net([(body, "ok", "", "application/pdf")] * 4):
        run(honbun, w, "toru", "--n", "11", "--url", l11[0]["url"])
        run(honbun, w, "toru", "--n", "11", "--url", l11[1]["url"])
        run(honbun, w, "toru", "--n", "12", "--url", "https://doi.org/10.1234/a12")
        run(honbun, w, "toru", "--n", "12", "--url", "https://doi.org/10.1234/a12")
    run(honbun, w, "gazo", "--n", "11", "--k", "1", "--peeji", "2")
    run(honbun, w, "gazo", "--n", "12", "--k", "1", "--peeji", "2")
    mine11 = K(l11[0]["url"]) | K(l11[1]["url"])
    hb = honbun.by_n(honbun.kiroku(w))
    gazo_de = dict(gyou(11, link=l11), seidoku="抄録どまり", yomikiranai="画像でも読めない頁(2頁の図)")
    ok(any("2回目に開いた PDF" in m for m in daicho.honbun_problems(dict(gyou(11, link=l11), seidoku="本文精読済み"), None, hb[11], mine11))
       and daicho.honbun_problems(gazo_de, None, hb[11], mine11) != []
       and daicho.honbun_problems(dict(gyou(12), seidoku="本文精読済み"), None, hb[12], set().union(*[K(x["url"]) for x in gyou(12)["link"]])) == [],
       "(18) 付録など置き場の違う PDF の頁を画像にしていない行は、本文精読済みにも「画像でも読めない頁」にもしない。同じ置き場の開き直しは1回分でよい")
    run(honbun, w, "gazo", "--n", "11", "--k", "2", "--peeji", "2")
    ok(daicho.honbun_problems(gazo_de, None, honbun.by_n(honbun.kiroku(w))[11], mine11) == [],
       "(18) どの PDF の文字の取れない頁も画像にした行は、「画像でも読めない頁」を訳にできる")
    u = "https://repo.example.org/scan.pdf"
    scan = {"toru": [{"type": "toru", "n": 13, "k": 1, "url": u, "jotai": "ok", "shurui": "pdf", "peeji": 0, "kuzure": [],
                      "yomenai": "PDF を開けなかった(FileDataError)"}], "gazo": {1}, "gazo_k": {1: {1}}}
    ok(any("開けなかった" in m for m in daicho.honbun_problems(dict(gyou(13), seidoku="本文精読済み"), None, scan, K(u)))
       and daicho.honbun_problems(dict(gyou(13), seidoku="抄録どまり", yomikiranai="開けなかった(PDF が壊れている)"), None, scan, K(u)) == [],
       "(18) 開けても読めない PDF(壊れている・パスワード)は、開けなかった物と同じに扱う(本文精読済みにしない。訳は「開けなかった」)")
    # 置き場の同じ PDF の開き直し・「画像でも読めない頁」・本文でないページだけの行・絞った記録を後の判定に使うこと
    jp = "https://www.jstage.jst.go.jp/article/x/14/1/14_1/_pdf"
    pd = lambda k, url, ku, pe=3: {"type": "toru", "n": 14, "k": k, "url": url, "jotai": "ok", "shurui": "pdf", "peeji": pe, "kuzure": ku}  # noqa: E731
    two = {"toru": [pd(1, jp, [3]), pd(2, jp + "/-char/ja", [3])], "gazo": {3}, "gazo_k": {2: {3}}}
    ok(daicho.honbun_problems(dict(gyou(14), seidoku="本文精読済み"), None, two, K(jp)) == [],
       "(18) J-STAGE の同じ記事の PDF を、URL の形を変えて開き直した時は、どれかの回を画像にすればよい")
    again = {"toru": [pd(1, jp, [3]), pd(2, jp, [])], "gazo": set(), "gazo_k": {}}
    ok(daicho.honbun_problems(dict(gyou(14), seidoku="抄録どまり", yomikiranai="画像でも読めない頁(3頁)"), None, again, K(jp)) != [],
       "(18) 文字の取れない頁を1枚も画像にしていない行は、「画像でも読めない頁」を訳にできない")
    hp = "https://doi.org/10.1234/a15"
    stub = {"toru": [{"type": "toru", "n": 15, "k": 1, "url": hp, "jotai": "ok", "shurui": "html", "moji": 11}], "gazo": set(), "gazo_k": {}}
    longp = {"toru": [dict(stub["toru"][0], moji=8548)], "gazo": set(), "gazo_k": {}}
    ok(any("本文でないページ" in m for m in daicho.honbun_problems(dict(gyou(15), seidoku="本文精読済み"), None, stub, K(hp)))
       and daicho.honbun_problems(dict(gyou(15), seidoku="本文精読済み"), None, longp, K(hp)) == [],
       "(18) 開けたのが本文でない短いページ(出版社の飛び先など)だけの行は、本文精読済みにしない。本文のページなら通す")
    mix = {"toru": [{"type": "toru", "n": 16, "k": 1, "url": "https://doi.org/10.1234/a16", "jotai": "shippai", "why": "HTTP 403"},
                    pd(2, "https://repo.example.org/other16.pdf", [], 250)], "gazo": set(), "gazo_k": {}}
    m16 = K("https://doi.org/10.1234/a16")
    ok(daicho.honbun_problems(dict(gyou(16), seidoku="本文精読済み"), None, mix, m16) != []
       and daicho.honbun_problems(dict(gyou(16), seidoku="抄録どまり", yomikiranai="200頁以上"), None, mix, m16) != [],
       "(18) 鍵の合わない記録(別の文献の 250頁の PDF)は、本文精読済みにも「200頁以上」にも数えない")
    ok(daicho.gyou_kagi({"n": 17, "link_bun": "J-STAGE(https://www.jstage.jst.go.jp/article/x/17/1/17_1/_article)"}, [])
       & K("https://www.jstage.jst.go.jp/article/x/17/1/17_1/_pdf"),
       "(18) 文のまま残ったリンク(古い Markdown から写した行)の URL も、行の鍵に入れる")
    broken = os.path.join(w, "honbun", "6-2.pdf")
    keep_b = open(broken, "rb").read()
    open(broken, "wb").write(b"%PDF-broken")
    try:
        code, out = run(honbun, w, "gazo", "--n", "6", "--k", "2", "--peeji", "2")
    finally:
        open(broken, "wb").write(keep_b)
    ok(code == 3 and "画像にできない" in out, "(18) 保存した PDF が壊れている時、gazo は落ちずに画像にできないと出す")
    pymupdf = pdf_buhin()
    enc = os.path.join(TMP, "enc.pdf")
    doc = pymupdf.open()
    doc.new_page().insert_text((50, 72), "secret")
    doc.save(enc, encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw="u", owner_pw="o")
    doc.close()
    with honbun_net([(open(enc, "rb").read(), "ok", "", "application/pdf")], pages=None):
        code, out = run(honbun, w, "toru", "--n", "18", "--url", "https://repo.example.org/enc.pdf")
    last = honbun.kiroku(w)[-1]
    ok(code == 0 and last.get("yomenai") and "読めない" in out, "(18) パスワードの掛かった PDF は、落ちずに読めない PDF として記録する")
    # kakunin_w が行の鍵を作って渡す(つなぎ)。採った候補の鍵は、行のリンクと同じ文献と分かる候補の物だけを足す
    w7 = wdir("hb7")
    os.makedirs(w7, exist_ok=True)
    page = b"<html><body>" + ("本文の文。" * 900).encode("utf-8") + b"</body></html>"
    with honbun_net([(page, "ok", "", "text/html")] * 3):
        run(honbun, w7, "toru", "--n", "7", "--url", "https://repo.example.org/other7.html")
        run(honbun, w7, "toru", "--n", "8", "--url", "https://repo.example.org/a8.pdf")
        run(honbun, w7, "toru", "--n", "9", "--url", "https://www.jstage.jst.go.jp/article/x/9/1/9_A/_pdf")
    sai = {"type": "kime", "kekka": "sai"}
    fake = {"KA": {"url": "https://doi.org/10.1234/candA", "oa_url": "https://repo.example.org/a8.pdf", "kagi": ["doi:10.1234/canda"],
                   "kime": dict(sai, gyou=8)},
            "KC": {"url": "https://cir.nii.ac.jp/crid/111", "kagi": ["crid:111", "jstage:X/9/1/9_A"], "kime": dict(sai, gyou=9)}}
    rows = [dict(gyou(7), seidoku="本文精読済み"), dict(gyou(8), seidoku="本文精読済み"),
            dict(gyou(9, link=[{"url": "https://cir.nii.ac.jp/crid/111"}]), seidoku="本文精読済み")]
    keep_load = kensaku.load
    kensaku.load = lambda w_: ([], fake, {})
    try:
        bad7 = [m for m in daicho.kakunin_w({"atama": ATAMA, "gyou": rows}, w7)[0] if m.startswith("#")]
        bad8 = [m for m in daicho.kakunin_w({"atama": ATAMA, "gyou": [dict(rows[1], link=[{"url": "https://doi.org/10.1234/candA"}])]}, w7)[0]
                if m.startswith("#")]
        keep_p = daicho.honbun_problems
        daicho.honbun_problems = lambda r, o, x, k=None: keep_p(r, o, x)
        try:
            bad_mae = [m for m in daicho.kakunin_w({"atama": ATAMA, "gyou": rows}, w7)[0] if m.startswith("#")]
        finally:
            daicho.honbun_problems = keep_p
    finally:
        kensaku.load = keep_load
    ok(sorted(m.split(":")[0] for m in bad7) == ["#7", "#8"] and bad8 == [],
       "(18) kaku --w は、別の文献を開いた記録だけの行(#7)と、行のリンクと合わない候補の鍵で通りそうな行(#8)を止め、"
       "CiNii の候補の J-STAGE の鍵(大文字)で本文PDF を開いた行(#9)と、リンクと候補が同じ文献の行は通す")
    ok(bad_mae == [], "(9) kaku --w が行の鍵を渡さないと、別の文献を開いた記録で通ってしまう(上の試験が効いている)")
    # 本文の置き場を開いたのに台帳に載せていない・読んでいない文献は、納品のチャットに出す(開いた後に読みにくい文献を外すと通った。D80)
    w8 = wdir("hb8")
    os.makedirs(w8, exist_ok=True)
    page8 = b"<html><body>" + ("本文の文。" * 900).encode("utf-8") + b"</body></html>"
    with honbun_net([(PDF_FAKE, "ok", "", "application/pdf")] * 3, pages=["本文の文" * 40] * 4):
        run(honbun, w8, "toru", "--n", "1", "--url", "https://doi.org/10.1234/a1")              # 台帳の #1 の置き場(出さない)
        run(honbun, w8, "toru", "--n", "1", "--url", "https://repo.example.org/body1.pdf")      # #1 の番号でリンクに無い置き場
        run(honbun, w8, "toru", "--n", "5", "--url", "https://repo.example.org/toukei5.pdf")    # 統計原表の行の置き場(出さない)
    with honbun_net([(PDF_FAKE, "ok", "", "application/pdf")] * 2 + [(None, "shippai", "HTTP 403", "")], pages=["本文の文" * 40, "図"] * 38):
        run(honbun, w8, "toru", "--n", "2", "--url", "https://repo.example.org/drop.pdf")
        run(honbun, w8, "toru", "--n", "2", "--url", "https://repo.example.org/drop.pdf")       # 同じ置き場の開き直し(1つに)
        run(honbun, w8, "toru", "--n", "3", "--url", "https://repo.example.org/kotowa.pdf")     # 開けなかった(出さない)
    with honbun_net([(PDF_FAKE, "ok", "", "application/pdf")] * 6, pages=["本文の文" * 40] * 2):
        run(honbun, w8, "toru", "--n", "6", "--url", "https://www.jstage.jst.go.jp/article/y/6/1/6_1/_pdf")
        run(honbun, w8, "toru", "--n", "6", "--url", "https://www.jstage.jst.go.jp/article/y/6/1/6_1/_pdf/-char/ja")   # 同じ記事(1つに)
        run(honbun, w8, "toru", "--n", "7", "--url", "https://repo.example.org/oa7.pdf")       # 採った候補の無料の置き場(リンクは CiNii だけ。出さない)
        run(honbun, w8, "toru", "--n", "15", "--url", "https://repo.example.org/oa555.pdf")    # 採った時の番号のまま開いた(台帳では #3)
        run(honbun, w8, "toru", "--n", "14", "--url", "https://doi.org/10.1234/x14")           # DOI だけの候補に合う
        run(honbun, w8, "toru", "--n", "13", "--url", "https://repo.example.org/sho13.pdf")    # 台帳の #13 は抄録どまりで照らしが掛からない
    with honbun_net([(page8, "ok", "", "text/html"), (b"<html>x</html>", "ok", "", "text/html"), (b"%PDF-broken", "ok", "", "application/pdf")], pages=None):
        run(honbun, w8, "toru", "--n", "10", "--url", "https://repo.example.org/long10.html")   # 本文のページ(字数を出す)
        run(honbun, w8, "toru", "--n", "11", "--url", "https://doi.org/10.1234/stub11")         # 本文でない短いページ(出さない)
        run(honbun, w8, "toru", "--n", "12", "--url", "https://repo.example.org/broken12.pdf")  # 読めない PDF(印を出す)
    sai = {"type": "kime", "kekka": "sai"}
    fake8 = {"KD": {"id": "KD", "dai": "落とした報告書", "url": "https://repo.example.org/drop.pdf", "kime": {"kekka": "horyu", "kimete": "画像だけの頁が多い"}},
             "KJ": {"id": "KJ", "dai": "J-STAGE の記事", "url": "https://www.jstage.jst.go.jp/article/y/6/1/6_1/_article"},
             "K7": {"id": "K7", "dai": "CiNii の論文", "url": "https://cir.nii.ac.jp/crid/777", "oa_url": "https://repo.example.org/oa7.pdf", "kime": dict(sai, gyou=7)},
             "KA": {"id": "KA", "dai": "重複の甲", "url": "https://repo.example.org/oa555.pdf", "kime": {"kekka": "otosu", "kimete": "#3 と同じ論文"}},
             "KB": {"id": "KB", "dai": "重複の乙", "url": "https://cir.nii.ac.jp/crid/555", "oa_url": "https://repo.example.org/oa555.pdf", "kime": dict(sai, gyou=15)},
             "KX": {"id": "KX", "dai": "DOI だけの候補", "doi": "10.1234/X14"}}
    d8 = {"atama": ATAMA, "gyou": [dict(gyou(1), seidoku="本文精読済み"),
                                   dict(gyou(3, link=[{"url": "https://cir.nii.ac.jp/crid/555"}]), nyushu="抄録のみ", seidoku="抄録どまり"),
                                   dict(gyou(7, link=[{"url": "https://cir.nii.ac.jp/crid/777"}]), nyushu="抄録のみ", seidoku="抄録どまり"),
                                   dict(gyou(13, link=[{"url": "https://repo.example.org/sho13.pdf"}]), nyushu="抄録のみ", seidoku="抄録どまり")],
          "toukei": [{"n": 5, "link": [{"url": "https://repo.example.org/toukei5.pdf"}]}]}
    keep_load = kensaku.load
    kensaku.load = lambda w_: ([], fake8, {})
    try:
        chat8 = daicho.kakunin_w(d8, w8)[1]
        keep_n = daicho.nosenai
        daicho.nosenai = lambda *a: []
        try:
            chat_mae = daicho.kakunin_w(d8, w8)[1]
        finally:
            daicho.nosenai = keep_n
    finally:
        kensaku.load = keep_load
    ns8 = [x for x in chat8 if x.startswith("- https://")]

    def hit(s):
        return [x for x in ns8 if s in x.split("(")[0]]
    moji = [int(m) for x in hit("long10.html") for m in re.findall(r"中身 (\d+)字", x)]
    zure = [why for why, cond in (
        ("見出しと件数", any("台帳に載せていない・読んでいない文献 8件" in x for x in chat8) and len(ns8) == 8),
        ("落とした候補の判定", len(hit("drop.pdf")) == 1 and "PDF 76頁・文字の取れない頁 38" in hit("drop.pdf")[0]
         and "台帳に #2 の行は無い。載せなかった訳を書く" in hit("drop.pdf")[0] and "候補 KD「落とした報告書」は保留(画像だけの頁が多い)" in hit("drop.pdf")[0]),
        ("台帳に在る番号でリンクに無い置き場", any("台帳の #1 は在るが、この置き場はそのリンクに無い" in x and "候補の一覧に無い" in x for x in hit("body1.pdf"))),
        ("J-STAGE の同じ記事は1つ・判定していない", len(hit("jstage.jst.go.jp")) == 1 and "候補 KJ「J-STAGE の記事」は判定していない" in hit("jstage.jst.go.jp")[0]),
        ("2つの候補を両方・採った候補の今の行を指す", any("候補 KA「重複の甲」は落とした(#3 と同じ論文)" in x and "候補 KB「重複の乙」は採った(台帳の #3 の文献かもしれない" in x
                                            for x in hit("oa555.pdf"))),
        ("DOI だけの候補", any("候補 KX「DOI だけの候補」は判定していない" in x for x in hit("x14"))),
        ("本文のページは字数", bool(moji) and moji[0] >= 2000),
        ("読めない PDF の印", any("読めない PDF" in x for x in hit("broken12.pdf"))),
        ("抄録どまりの行の本文", any("台帳の #13 に載せたが、開いた本文を読まずに精読は「抄録どまり」" in x for x in hit("sho13.pdf"))),
        ("出さない物(台帳の行・統計原表・採った候補の無料の置き場・開けなかった・短いページ)",
         not any(hit(s) for s in ("10.1234/a1", "toukei5.pdf", "oa7.pdf", "kotowa.pdf", "stub11")))) if not cond]
    ok(not zure, "(18) 本文の置き場を開いたのに台帳に載せていない・読んでいない文献を、件ごとにすることと候補の判定と一緒に納品のチャットに出す。外れ= %s%s"
       % (zure, " 一覧= %s" % [x.split("(")[0] for x in ns8] if zure else ""))
    ok(not any("読んでいない文献" in x for x in chat_mae), "(9) 開いたのに載せなかった文献を数えないと、読みにくい文献を外したことがチャットに出ない(上の試験が効いている)")
    keep = daicho.honbun_problems
    daicho.honbun_problems = lambda *a: []
    try:
        run(kiroku, "ronten", w, "an", "--ronten", "1=x", "--kijun", "y")
        run(kiroku, "ronten", w, "shonin", "--ronten", "1=x", "--kijun", "y")
        bad, _ = daicho.kakunin_w({"atama": dict(ATAMA, ronten=[{"no": "1", "shurui": "", "bun": "x"}], kijun="y"),
                                   "gyou": [dict(gyou(9), seidoku="抄録どまり", yomikiranai="200頁以上")]}, w)
        ok(bad == [], "(9) 開いた記録との照らしを外すと、置き場を開かずに抄録で済ませた行が通ってしまう(上の試験が効いている)")
    finally:
        daicho.honbun_problems = keep


def main():
    if pdf_buhin() is None:
        # 部品が無いまま走らせると、PDF を作る所でエラーの文の山になり、何が足りないか分かりにくい(Mac・Linux で pip が止まった時)
        print("PDF を読む部品(PyMuPDF)が無いので、試験を走らせなかった。uv run test_scripts.py で走らせ直す"
              "(uv が、ファイルの頭に書いた版の PyMuPDF を用意する。uv が無い時は README の「入れ方」で uv を入れる)")
        return 2
    old = os.environ.get(kensaku.APPID_NAME)
    os.environ[kensaku.APPID_NAME] = FAKE_ID     # CiNii を投げる試験も、作り物の ID で動かす
    # 使う人の設定(スキルの設定ファイル・BUNKEN_DB・Windows のアカウントの環境変数の BUNKEN_DB)を読まない
    # (BUNKEN_DB を置いた PC で、試験が IndexError で落ちた。D84 の7の点検)
    os.environ[kensaku.SETTEI_ENV] = os.path.join(TMP, "settei-nashi", "settings.json")
    os.environ.pop(kensaku.TSUKAU_NAME, None)
    _ue = kensaku.user_env
    kensaku.user_env = lambda name: None if name == kensaku.TSUKAU_NAME else _ue(name)
    try:
        part_kensaku()
        part_shoshi()
        part_kiroku()
        part_nukigaki()
        part_appid()
        part_daicho()
        part_link()
        part_tsukau()
        part_settei()
        part_kaime()
        part_teian()
        part_eigo()
        part_kakikomi()
        part_kakunin()
        part_honbun()
    finally:
        shutil.rmtree(TMP, ignore_errors=True)
        if old is None:
            os.environ.pop(kensaku.APPID_NAME, None)
        else:
            os.environ[kensaku.APPID_NAME] = old
    n, bad = len(RESULTS), RESULTS.count(False)
    print("=" * 60)
    print("試験: %d項目中 %d合格 / %d不合格" % (n, n - bad, bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
