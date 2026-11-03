# -*- coding: utf-8 -*-
# 部品の版(uv run で走らせると、uv がこの版を、使う人の PC の Python を変えずに用意する。python で打っても動く)
# /// script
# requires-python = ">=3.10"
# dependencies = ["pymupdf==1.27.2.3"]
# ///
"""文献台帳の正本(<台帳名>.json)と、そこから作る HTML・機械用の Markdown(run-bunken-daicho の工程4〜6)。標準ライブラリだけ。
決定= claude-harness の docs/user-decisions.md の D67(ch-f5x.6)。中身は JSON が正本で、人が見る HTML(型紙
assets/daicho-page.html)と、納品物チェッカー・確かめ役が読む Markdown は、このスクリプトが毎回同じ形で作る(手で書かない)。
Markdown の形は、これまでの台帳と同じ(チェッカーとその試験を変えずに使うため)。

置き場: 台帳の JSON・HTML・書誌の項目ファイル(<台帳名>.shoshi.json)は台帳のフォルダ。Markdown は作業用フォルダ
(<作業用フォルダ>/<台帳名>.md。ユーザーに渡さない)。

台帳の JSON はエディタで直接書き換えず、このスクリプトを通して書く(足すたびに形を確かめ、壊れた JSON や選べない語を
その場で止めるため)。Claude は小さな JSON(1件ぶん・頭の部分・探索記録の塊など)を作業用フォルダに書き、ireru で渡す。

使い方:
  uv run daicho.py <台帳.json> ireru --json-file 部分.json
      部分の JSON の上の段の鍵: atama(頭の部分。渡した鍵だけ置き換える)・shogou(宣言との照合の1行)・chui(読み方の注意の並び)・
      gyou(文献の行の並び。番号 n で突き合わせ、ある行は渡した鍵だけ置き換え、無い行は足す。{"n": 4, "kesu": true} で消す)・
      toukei(統計原表の行。gyou と同じ)・totsugo(書誌突合の1行)・tansaku(探索記録。mae と bloku。塊は midashi で突き合わせ)・
      nyushu_route(入手ルート提案の並び)・genkai(この台帳の限界に Claude が足す並び。任意)・
      db_na(手で記録した DB の読める名前。{"nochuri": "農林中金総合研究所の刊行物検索"}。限界の欄と方法の下書きに出る)
      スクリプトが書く欄(chojiri・hoho・genkai_kikai・行の ronten・shinkoku)は渡せない
  uv run daicho.py <台帳.json> shinkoku --kara チェッカーの出力.txt
      納品物チェッカーの出力から段階A・B・C の申告の囲みを取り出して入れる(書き写さない。1字でも違うと B-12・B-15・B-16 で止まる)
  uv run daicho.py <台帳.json> kensa
      形を確かめる(選べる語・必須の欄・表を壊す字・論点の番号・探索記録の次の一手・書誌の項目ファイルとの対応)
  uv run daicho.py <台帳.json> kaku --w <作業用フォルダ>
      検索の記録と候補の一覧から、選別の帳尻・各行の論点の番号・限界の欄の機械の部分・方法の節の下書きを数え直して台帳の JSON に入れ、
      HTML(台帳と同じフォルダの <台帳名>.html)と Markdown(<作業用フォルダ>/<台帳名>.md)を作る。kensa で外れがあれば作らない。
      --w を付けない時は数え直さず、入っている物で作る(--md で Markdown の置き場を渡した時だけ Markdown も作る)
  uv run daicho.py <台帳.json> miru [--n 3,5] [--kata text|json] [--yoshi]
      uradori・ronbun が台帳を読む入口。--n を付けないと、頭の部分(テーマ・適合の基準・論点の番号と文・読み方の注意・書誌突合)と
      1件1行の一覧(書誌・種別・入手状況・精読・論点の番号・リンク)を出す。まずこれで要る行を選び、--n でその行だけを --yoshi(要旨と抜き書き)つきで読む。
      台帳の大半を使う時は、選び直しを重ねず --yoshi で全部を1回で読む(何度も選ぶより読む字数が少ない)。
      json は書誌の項目ファイルの項目(chosha・nen・dai・fukudai・shi・maki・gou・peji・shuppan・doi)もつける
  uv run daicho.py <台帳.json> utsusu <古い台帳.md>
      これまでの Markdown の台帳を、この JSON の形に写し直す(古い台帳を HTML で見る時・Markdown の形が同じに作れるかの試験に使う)
  uv run daicho.py <台帳.json> reigai --kara チェッカーの出力.txt --w <作業用フォルダ>
      チェッカーが終了コード 3(測れなかった物が残った)で止まった時に、測れなかった物がどれも例外かを決める。例外は4つ:
      出版社に機械の取得を断られた(HTTP 401・403)行と、出版社のページに機械が証明書の誤りでつながらない行で、備考にそう書き
      DOI を持つ行/チェッカーが英語の本文を読めない(ページが散文を渡していない)英語の行/書誌欄の題名が『』でチェッカーが
      対照を置けない行(図書・報告書・白書)。どれも代わりの確かめを通した物だけを例外にする。断られた行のリンクは、行の DOI の
      リンクか、honbun.py でこの行の番号で開けた置き場だけ。抜き書き・要旨の「」は、その行の DOI で保存した抄録(shoroku/。
      頭の題名がこの行の題名と合う物)か、その行の置き場を honbun.py で開いた本文PDF(文字にこの行の題名が在る物)に原文のまま
      在る物だけ(区切りは6字以上。要旨の「」は要旨の全文で照らす。題名は書誌の項目ファイルの dai)。書き方の誤り・段階B の
      測れなかった物・違反・未検査は例外にしない。渡す出力は、kaku --w が書いた今の台帳の行から出た物に限る(Markdown を書いた
      記録 <Markdown>.kagi.jsonl と照らす)。例外だけなら 0 と納品のチャットに出す一覧、ほかがあれば 1(納めずに判断を待つ)
台帳の行の yomikiranai: 全文OA なのに抄録どまりの行と、候補の一覧に無料で読める置き場があるのに全文OA でない行は、
  本文を読み切れなかった訳(YOMIKIRANAI のどれか)で始めて読んだ範囲を書く。無いと入れない・作らない(kaku --w)。
  kaku --w は、本文が無料で読める行を honbun.py の開いた記録と照らす: 開いた記録が無い行・開けた本文を読み切っていない行
  (訳にできるのは 200頁以上の PDF・本文の無い置き場・画像にしても読めない頁だけ)・文字の取れない頁を画像にせずに
  本文精読済みにした行は、台帳を作らない。書いた行は限界の欄に並び、kaku が納品のチャットに出す一覧を出す。
  本文の置き場を開いたのに台帳に載せていない文献と、載せたが照らしの掛からない行で本文を読んでいない文献も、止めずに一覧に出す(D80)
終わりの値: 0=できた / 1=形が外れた・食い違う(止める) / 2=使い方・ファイルの誤り
"""
import argparse
import html
import json
import os
import re
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from kyotsu import Stop, Usage, ts, write_text  # noqa: E402

KIND = "bunken-daicho"
V = 1
TEMPLATE = os.path.join(os.path.dirname(HERE), "assets", "daicho-page.html")
NYUSHU = ("全文OA", "抄録のみ", "有料", "学内限定", "未入手")
SEIDOKU = ("本文精読済み", "抄録どまり")
# 本文が無料で読めるのに読み切っていない行の訳(行の yomikiranai はこのどれかで始め、続けて読んだ範囲を書く)。
# 決まりは全文を読むことで、読まずに抄録で済ませた台帳が2回続いたので(ch-3ni)、訳の無い行は入れない。訳が本当かは
# kaku --w が honbun.py の開いた記録と照らす(「時間切れ」を訳にした試しでは、置き場を1つも開かずに納めたので、外した)
YOMIKIRANAI = ("200頁以上", "画像でも読めない頁", "出版社に断られた", "開けなかった", "置き場に本文が無い")
# 長い名前から先に照らす(「統計原表(Excel・CSV)」を「統計原表」より先に)
SHUBETSU = ("学会誌(査読不明)", "統計原表(Excel・CSV)", "査読論文", "紀要", "学位論文", "白書・報告書", "統計原表", "書籍", "業界資料",
            "プレプリント")
YOTO = ("背景", "方法", "比較", "反論")
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
ATAMA = (("mokuteki", "目的"), ("shubetsu_hani", "種別範囲"), ("nendai", "年代範囲"), ("gengo", "言語"),
         ("kensu", "件数目安"), ("engine", "エンジン"), ("kijun", "適合の基準"))
ATAMA_ATO = (("hito_to_ba", "探し方(人と場)"), ("jikkobi", "実行日"))
# 凡例は daicho-format.md「凡例」節の逐語(チェッカーの B-6 が3種を見る)
HANREI = ("**凡例(種別)**: 査読論文=査読付と確認できたもの / 学会誌(査読不明)=学会・研究会の刊行物だが査読の有無を確認できなかったもの / "
          "紀要=大学等の紀要 / 学位論文=博士・修士 / 白書・報告書=官公庁等 / 統計原表=Excel/CSVの一次集計 / 書籍=出版社刊行の図書 / 業界資料=団体・企業資料 / "
          "プレプリント=査読を経ていない前刷り(arXiv 等)",
          "**凡例(入手状況)**: 全文OA=無料全文 / 抄録のみ=全文未入手 / 有料 / 学内限定 / 未入手=書誌のみ確定",
          "**凡例(精読)**: 本文精読済み=本文を全部読んで要旨を書いた / 抄録どまり=本文を全部は読んでいない(抄録・書誌・本文の一部から要旨を書いた)")
HIKITSUGI = "この台帳は run-uradori の裏取りソース、run-ronbun-shippitsu の引用文献リストの素材として使えます。"
SHINKOKU_MAE = "納品物チェッカー(check_deliverable.py)の段階A・B・Cの申告を、出力のまま貼った。"
SHINKOKU_RE = re.compile(r"^```(stage-[abc] v\d+)[^\n]*\n(.*?)\n```", re.S | re.M)
COLS = (("#", "n"), ("書誌", "shoshi"), ("種別", "shubetsu"), ("言語", "gengo"), ("発見経路", "keiro"), ("リンク", "link"),
        ("入手状況", "nyushu"), ("精読", "seidoku"), ("要旨", "yoshi"), ("抜き書き", "nukigaki"), ("用途タグ", "yoto"),
        ("アクセス日", "access"), ("備考", "biko"))
TCOLS = (("#", "n"), ("書誌", "shoshi"), ("種別", "shubetsu"), ("発見経路", "keiro"), ("リンク", "link"), ("入手状況", "nyushu"),
         ("用途タグ", "yoto"), ("アクセス日", "access"), ("調査年月", "chosa_nengetsu"), ("statInfId", "statinfid"),
         ("fileKind", "filekind"))
SCRIPT_KEYS = ("chojiri", "hoho", "genkai_kikai", "shinkoku")
# 文献の行のリンクの出どころ(D84。grounded-citations に倣い、Claude は URL を打たず出どころだけを書き、URL は kaku --w が記録から書く)
LINK_KOUHO = re.compile(r"K\d{4,}")
LINK_SRC = ("kouho", "honbun", "doi")
LINK_KATA = ('{"kouho": "K0012"}(候補の一覧の URL)・{"kouho": "K0012", "doi": true}(その候補の DOI)・'
             '{"honbun": true}(この行で最後に開けた本文の置き場。回を選ぶ時は {"honbun": 2})・'
             '{"doi": true}(書誌の項目ファイルの DOI)の並びで書く。どれにも "na"(リンクの名前)を添えてよい。'
             'URL は書かない(kaku --w が記録から書く)。検索に出ていない置き場は kensaku.py <作業用フォルダ> tsuika で一覧に足し、その番号で書く')
IRERU_KEYS = ("atama", "shogou", "chui", "gyou", "toukei", "totsugo", "tansaku", "nyushu_route", "genkai", "db_na")
DB_NA = {"cinii": "CiNii Research", "ndl": "国立国会図書館サーチ(NDLサーチ)", "jstage": "J-STAGE", "kaken": "KAKEN",
         "estat": "e-Stat", "scholar": "Google Scholar", "perplexity": "Perplexity",
         "openalex": "OpenAlex", "semanticscholar": "Semantic Scholar", "arxiv": "arXiv", "crossref": "Crossref"}
# Semantic Scholar の約款(Attribution の節)は、API で得た結果を使った論文に The Semantic Scholar Open Data Platform を引くよう求める
S2_HIKU = "Semantic Scholar を用いたので、引用文献に The Semantic Scholar Open Data Platform を挙げる(同 API の約款が求める)。"


def p(*a):
    print(*a)


# ---- 読み書き ----

def empty():
    return {"kind": KIND, "v": V, "atama": {"ronten": []}, "gyou": [], "toukei": []}


def load(path, must=True):
    if not os.path.exists(path):
        if must:
            raise Usage("台帳の JSON が無い: %s" % path)
        return empty()
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError, UnicodeDecodeError) as e:
        raise Usage("台帳の JSON が読めない: %s (%s)" % (path, e))
    if not (isinstance(d, dict) and d.get("kind") == KIND and d.get("v") == V):
        raise Stop("台帳の JSON の形でない(kind=%s・v=%d が要る): %s" % (KIND, V, path))
    d.setdefault("atama", {"ronten": []})
    d.setdefault("gyou", [])
    d.setdefault("toukei", [])
    return d


def save(path, d):
    for k in ("gyou", "toukei"):
        d[k].sort(key=lambda r: r.get("n", 0) if isinstance(r.get("n"), int) else 0)
    write_text(path, json.dumps(d, ensure_ascii=False, indent=1) + "\n")


def base(path):
    b = os.path.basename(path)
    return b[:-5] if b.endswith(".json") else b


def shoshi_path(path):
    return os.path.join(os.path.dirname(os.path.abspath(path)), base(path) + ".shoshi.json")


def load_shoshi(path):
    if not path or not os.path.exists(path):
        return {}
    import shoshi
    return {r["n"]: r for r in shoshi.load(path)["rows"] if isinstance(r.get("n"), int)}


# ---- マスの文(Markdown の表と HTML で同じ文を使う) ----

def tail_paren(s):
    """末尾の (…) を対応する括弧ごと切り出す。→ (本体, 括弧の中)。無ければ (s, None)"""
    s = s.strip()
    if not s.endswith(")"):
        return s, None
    depth = 0
    for i in range(len(s) - 1, -1, -1):
        if s[i] == ")":
            depth += 1
        elif s[i] == "(":
            depth -= 1
            if depth == 0:
                return s[:i].strip(), s[i + 1:-1]
    return s, None


def cell_shubetsu(r):
    if r.get("shubetsu_bun") is not None:
        return r["shubetsu_bun"]
    return r.get("shubetsu", "") + ("(%s)" % r["shubetsu_konkyo"] if r.get("shubetsu_konkyo") else "")


def cell_link(r):
    if r.get("link_bun") is not None:
        return r["link_bun"]
    ls = r.get("link") or []
    if not ls:
        return ""
    s = ls[0]["url"]
    if len(ls) > 1:
        s += " (" + " ・".join(("%s: %s" % (x["na"], x["url"])) if x.get("na") else x["url"] for x in ls[1:]) + " )"
    return s


def cell_yoshi(r):
    y = r.get("yoshi") or {}
    if y.get("bun") is not None:
        return y["bun"]
    s = "(%s)" % y.get("han", "")
    if y.get("shurui"):
        s += y["shurui"] + "。"
    return s + "".join("<br>・" + k for k in y.get("kajo") or [])


def cell_nukigaki(r):
    if r.get("nukigaki_bun") is not None:
        return r["nukigaki_bun"]
    nk = r.get("nukigaki") or []
    if not nk:
        return "なし(%s)" % (r.get("nukigaki_nashi") or "書誌のみ")
    return " ".join("「%s」(%s)" % (x["bun"], x["basho"]) for x in nk)


def cell_toukei_nengetsu(r):
    if r.get("chosa_nengetsu_bun") is not None:
        return r["chosa_nengetsu_bun"]
    v = r.get("chosa_nengetsu") or ""
    return ("調査年月: %s(e-Stat結果一覧『調査年月』欄)" % v) if v else ""


def cell(r, key, sh):
    if key == "n":
        return str(r["n"])
    if key == "shoshi":
        if r.get("shoshi_bun") is not None:
            return r["shoshi_bun"]
        if r["n"] in sh:
            import shoshi
            return shoshi.render(sh[r["n"]])
        return ""
    if key == "shubetsu":
        return cell_shubetsu(r)
    if key == "link":
        return cell_link(r)
    if key == "yoshi":
        return cell_yoshi(r)
    if key == "nukigaki":
        return cell_nukigaki(r)
    if key == "chosa_nengetsu":
        return cell_toukei_nengetsu(r)
    v = r.get(key)
    if v is None and r.get("hoka"):
        v = r["hoka"].get(key)
    return "" if v is None else str(v)


# ---- 形の確かめ ----

def texts(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from texts(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from texts(v)


def link_katachi(x):
    """文献の行のリンク1本の出どころの形。→ 外れの文か None"""
    if "kouho" in x:
        if not LINK_KOUHO.fullmatch(str(x["kouho"])) or "honbun" in x or x.get("doi", True) is not True:
            return "kouho は候補の番号(K0012 の形)。その候補の DOI にする時だけ doi: true を添える"
    elif "honbun" in x:
        h = x["honbun"]
        if not (h is True or (type(h) is int and h >= 1)):
            return "honbun は true(この行で最後に開けた置き場)か、開いた回の番号(1 以上)"
    elif x.get("doi") is not True:
        return "出どころ(kouho・honbun・doi)が無い。" + LINK_KATA
    if "url" in x and not str(x["url"]).startswith(("http://", "https://")):
        return "url が http(s) で始まらない(url は kaku --w が記録から書く)"
    return None


def row_problems(r, ronten_nos, toukei=False):
    tag = "#%s" % r.get("n")
    out = []
    if not (isinstance(r.get("n"), int) and r["n"] >= 1):
        return ["行の番号 n が1以上の整数でない: %r" % r.get("n")]
    if any("|" in t or "\n" in t or "\r" in t for t in texts(r)):
        out.append("%s: 縦棒「|」か改行がある(Markdown の表が壊れる。箇条は kajo の並びに分ける)" % tag)
    if r.get("shubetsu_bun") is None and r.get("shubetsu") not in SHUBETSU:
        out.append("%s: shubetsu は %s のどれか(%r)" % (tag, "・".join(SHUBETSU), r.get("shubetsu")))
    if r.get("nyushu") not in NYUSHU:
        out.append("%s: nyushu は %s のどれか(%r)" % (tag, "・".join(NYUSHU), r.get("nyushu")))
    if r.get("link_bun") is None:
        ls = r.get("link")
        if toukei:
            if not (isinstance(ls, list) and ls and all(isinstance(x, dict) and str(x.get("url", "")).startswith(("http://", "https://")) for x in ls)):
                out.append("%s: link は {url, na} の並びで1本以上(全行リンク必須)" % tag)
        elif not (isinstance(ls, list) and ls and all(isinstance(x, dict) for x in ls)):
            out.append("%s: link は出どころの並びで1本以上(全行リンク必須)。%s" % (tag, LINK_KATA))
        else:
            out += ["%s: リンクの %d本目: %s" % (tag, i, w) for i, x in enumerate(ls, 1) for w in [link_katachi(x)] if w]
    if not DATE_RE.fullmatch(str(r.get("access", ""))):
        out.append("%s: access(アクセス日)は YYYY-MM-DD" % tag)
    if not (r.get("keiro") or "").strip():
        out.append("%s: keiro(発見経路)が要る" % tag)
    yt = r.get("yoto") or ""
    if not any(w in yt for w in YOTO):
        out.append("%s: yoto(用途タグ)に 背景・方法・比較・反論 のどれかを含める(%r)" % (tag, yt))
    for k in r.get("ronten") or []:
        if ronten_nos and str(k) not in ronten_nos:
            out.append("%s: 論点%s は頭の部分に無い" % (tag, k))
    if toukei:
        if not (r.get("chosa_nengetsu") or r.get("chosa_nengetsu_bun")):
            out.append("%s: 統計原表の行には chosa_nengetsu(e-Stat の結果一覧の『調査年月』)が要る" % tag)
        return out
    if r.get("seidoku") not in SEIDOKU:
        out.append("%s: seidoku は %s のどちらか(%r)" % (tag, "・".join(SEIDOKU), r.get("seidoku")))
    yk = (r.get("yomikiranai") or "").strip()
    if yk and not yk.startswith(YOMIKIRANAI):
        out.append("%s: yomikiranai(本文を読み切れなかった訳)は %s のどれかで始め、続けて読んだ範囲を書く(%r)"
                   % (tag, "・".join(YOMIKIRANAI), yk))
    elif r.get("nyushu") == "全文OA" and r.get("seidoku") == "抄録どまり" and not yk:
        out.append("%s: 全文OA なのに抄録どまり。本文を全部読んで本文精読済みにする(読み切れない時だけ yomikiranai に訳(%s)と読んだ範囲を書く)"
                   % (tag, "・".join(YOMIKIRANAI)))
    y = r.get("yoshi") or {}
    if y.get("bun") is None:
        if not (y.get("han") or "").strip():
            out.append("%s: yoshi.han(読めた範囲。「本文より」「抄録より」「書誌のみ」など)が要る" % tag)
        kj = y.get("kajo")
        if not (isinstance(kj, list) and 1 <= len(kj) <= 4 and all(isinstance(k, str) and k.strip() for k in kj)):
            out.append("%s: yoshi.kajo は箇条の並び(2〜4つが目安・1〜4)" % tag)
        han = y.get("han") or ""
        if r.get("seidoku") == "本文精読済み" and "抄録" in han:
            out.append("%s: 本文精読済みなのに読めた範囲が「%s」(精読の欄と食い違う)" % (tag, han))
        nk = r.get("nukigaki")
        if r.get("nukigaki_bun") is None:
            if nk and not all(isinstance(x, dict) and (x.get("bun") or "").strip() and (x.get("basho") or "").strip() for x in nk):
                out.append("%s: nukigaki は {bun(原文のまま), basho(場所)} の並び" % tag)
            if not nk and not any(w in han for w in ("書誌", "目次", "題名")):
                out.append("%s: 要旨を「%s」から書いた行には抜き書きを置く(題名・書誌・目次だけの行だけが「なし」)" % (tag, han))
    return out


def problems(d, sh=None, strict=True):
    out = []
    a = d.get("atama") or {}
    if strict:
        for k, na in (("theme", "テーマ"),) + ATAMA + ATAMA_ATO:
            if not (a.get(k) or "").strip():
                out.append("頭の部分: %s(%s)が要る" % (k, na))
        if a.get("jikkobi") and not DATE_RE.fullmatch(a["jikkobi"]):
            out.append("頭の部分: jikkobi(実行日)は YYYY-MM-DD")
    rs = a.get("ronten") or []
    nos = [str(r.get("no")) for r in rs]
    if strict and not (isinstance(rs, list) and rs):
        out.append("頭の部分: ronten(論点)が1つ以上要る")
    if len(set(nos)) != len(nos):
        out.append("頭の部分: 論点の番号が重なっている")
    seen = set()
    for key, tk in (("gyou", False), ("toukei", True)):
        for r in d.get(key) or []:
            out += row_problems(r, set(nos), tk)
            if r.get("n") in seen:
                out.append("#%s が2行ある(番号は台帳全体で一意)" % r.get("n"))
            seen.add(r.get("n"))
            if sh is not None and strict and r.get("shoshi_bun") is None and r.get("n") not in sh:
                out.append("#%s: 書誌の項目ファイルに行が無い(shoshi.py tsuika --n %s で入れる)" % (r.get("n"), r.get("n")))
    if strict and not d.get("gyou"):
        out.append("文献の行(gyou)が1つも無い")
    t = d.get("tansaku") or {}
    bl = t.get("bloku") or []
    ron_bl = [b for b in bl if (b.get("midashi") or "").startswith("論点")]
    for b in ron_bl:
        if not any("**次の一手**" in k for k in (b.get("kajo") or []) + (b.get("gyou") or [])):
            out.append("探索記録の「%s」に「**次の一手**: …」の箇条が無い" % b.get("midashi"))
    if strict and not ron_bl and "見つからなかった論点なし" not in (t.get("mae") or ""):
        out.append("探索記録: 論点の塊が無い時は mae に「見つからなかった論点なし」と書く(空と区別するため)")
    for x in texts({k: d.get(k) for k in ("shogou", "totsugo", "chui", "nyushu_route", "genkai")}):
        if "\n" in x:
            out.append("改行のある文がある(並びに分ける): %s…" % x[:30])
    return out


# ---- 部分を入れる ----

def merge_rows(have, new, nos, toukei):
    by = {r["n"]: r for r in have if isinstance(r.get("n"), int)}
    touched = []
    for r in new if isinstance(new, list) else [new]:
        if not isinstance(r, dict) or not isinstance(r.get("n"), int):
            raise Usage("行は番号 n(整数)を持つ辞書で渡す: %r" % (r,))
        if "ronten" in r:
            raise Usage("#%d: 行の ronten はスクリプトが候補の一覧から書く(kaku --w)" % r["n"])
        if r.get("kesu"):
            by.pop(r["n"], None)
            continue
        if not toukei and isinstance(r.get("link"), list) and any(isinstance(x, dict) and "url" in x for x in r["link"]):
            raise Usage("#%d: リンクに url は書かない(D84。kaku --w が候補・開いた本文・書誌の DOI の記録から書く)。%s" % (r["n"], LINK_KATA))
        by[r["n"]] = dict(by.get(r["n"], {}), **r)
        touched.append(r["n"])
    rows = sorted(by.values(), key=lambda r: r["n"])
    bad = [x for r in rows if r["n"] in touched for x in row_problems(r, nos, toukei)]
    return rows, touched, bad


def cmd_ireru(a):
    d = load(a.file, must=False)
    try:
        with open(a.json_file, encoding="utf-8") as f:
            part = json.load(f)
    except (OSError, ValueError, UnicodeDecodeError) as e:
        raise Usage("--json-file が読めない(JSON の書き方を確かめる): %s" % e)
    if not isinstance(part, dict):
        raise Usage("--json-file は上の段が辞書の JSON")
    for k in part:
        if k in SCRIPT_KEYS:
            raise Usage("%s はスクリプトが書く欄(kaku --w・shinkoku)" % k)
        if k not in IRERU_KEYS:
            raise Usage("知らない鍵 %r(入れられるのは %s)" % (k, "・".join(IRERU_KEYS)))
    msgs, bad = [], []
    if "atama" in part:
        if not isinstance(part["atama"], dict):
            raise Usage("atama は辞書")
        d["atama"] = dict(d.get("atama") or {}, **part["atama"])
        msgs.append("頭の部分(%s)" % "・".join(part["atama"]))
    nos = {str(r.get("no")) for r in d["atama"].get("ronten") or []}
    for key, tk in (("gyou", False), ("toukei", True)):
        if key in part:
            d[key], touched, b = merge_rows(d.get(key) or [], part[key], nos, tk)
            bad += b
            msgs.append("%s %d行" % ("文献の行" if key == "gyou" else "統計原表の行", len(touched)))
    if "tansaku" in part:
        t = d.get("tansaku") or {"mae": "", "bloku": []}
        nt = part["tansaku"]
        if "mae" in nt:
            t["mae"] = nt["mae"]
        bl = {b["midashi"]: b for b in t.get("bloku") or []}
        order = [b["midashi"] for b in t.get("bloku") or []]
        for b in nt.get("bloku") or []:
            if not (isinstance(b, dict) and b.get("midashi")):
                raise Usage("探索記録の塊は midashi(見出し)を持つ辞書")
            if b.get("kesu"):
                bl.pop(b["midashi"], None)
                continue
            if b["midashi"] not in bl:
                order.append(b["midashi"])
            bl[b["midashi"]] = {"midashi": b["midashi"], "kajo": list(b.get("kajo") or [])}
        t["bloku"] = [bl[m] for m in order if m in bl]
        d["tansaku"] = t
        msgs.append("探索記録")
    for k in ("shogou", "chui", "totsugo", "nyushu_route", "genkai", "db_na"):
        if k in part:
            d[k] = part[k]
            msgs.append(k)
    if bad:
        raise Stop("入れられない(台帳の JSON は書き換えていない): " + " / ".join(bad))
    save(a.file, d)
    p("入れた: " + "・".join(msgs))
    return 0


def cmd_shinkoku(a):
    d = load(a.file)
    try:
        with open(a.kara, encoding="utf-8") as f:
            text = f.read()
    except (OSError, UnicodeDecodeError) as e:
        raise Usage("チェッカーの出力が読めない: %s" % e)
    got = {m.group(1): m.group(2) for m in SHINKOKU_RE.finditer(text.replace("\r\n", "\n"))}
    if not got:
        raise Stop("チェッカーの出力に申告の囲み(```stage-a v1 など)が無い。--type bunken で段階を付けて走らせた出力を渡す")
    d["shinkoku"] = dict(d.get("shinkoku") or {}, **got)
    save(a.file, d)
    p("申告を入れた: " + "・".join(sorted(got)))
    return 0


def cmd_kensa(a):
    d = load(a.file)
    bad = problems(d, load_shoshi(shoshi_path(a.file)), strict=not d.get("utsushi"))
    if bad:
        for x in bad:
            p("✕ " + x)
        return 1
    p("台帳の JSON: 外れなし(文献 %d行・統計原表 %d行)" % (len(d["gyou"]), len(d["toukei"])))
    return 0


# ---- 文献の行のリンクの URL を記録から書く(D84) ----

def link_from_records(d, w, sh):
    """文献の行のリンクの出どころ(候補の番号・開いた本文・書誌の DOI)から URL を書く。Claude が書いた URL は使わない
    (記憶や写し間違いの URL が入らないように。grounded-citations の「番号だけを書き、URL は台帳が書き出す」)。→ 外れの並び"""
    import honbun
    import kensaku
    _S, cands, _ = kensaku.load(w)
    toru = [t for t in honbun.kiroku(w) if t.get("type") == "toru" and t.get("jotai") == "ok"]
    out = []
    for r in d["gyou"]:
        if r.get("link_bun") is not None:
            continue
        for i, x in enumerate(r.get("link") or [], 1):
            if not isinstance(x, dict) or link_katachi(x):
                continue
            url, why = "", ""
            if "kouho" in x:
                c = cands.get(x["kouho"])
                if c is None:
                    why = "候補の一覧に %s が無い(検索に出ていない置き場は kensaku.py <作業用フォルダ> tsuika で一覧に足し、その番号で書く)" % x["kouho"]
                elif x.get("doi"):
                    doi = (c.get("doi") or "").strip()
                    url, why = ("https://doi.org/" + doi, "") if doi else ("", "%s の記録に DOI が無い" % x["kouho"])
                else:
                    url = (c.get("url") or "").strip()
                    why = "" if url else "%s の記録に URL が無い" % x["kouho"]
            elif "honbun" in x:
                ok = [t for t in toru if t.get("n") == r["n"] and (x["honbun"] is True or t.get("k") == x["honbun"])]
                url = ok[-1]["url"] if ok else ""
                why = "" if ok else ("この行の番号で開けた本文の記録が無い%s(honbun.py <作業用フォルダ> toru --n %s --url <置き場> で開く。"
                                     "開いた回は honbun.py <作業用フォルダ> miru --n %s で見る)"
                                     % ("" if x["honbun"] is True else "(%s回目)" % x["honbun"], r["n"], r["n"]))
            else:
                doi = ((sh.get(r["n"]) or {}).get("doi") or "").strip()
                url, why = ("https://doi.org/" + doi, "") if doi else ("", "書誌の項目ファイルの #%s に DOI が無い(shoshi.py の tsuika で doi を入れる)" % r["n"])
            if url:
                x["url"] = url
            else:
                x.pop("url", None)
                out.append("#%s: リンクの %d本目の URL を記録から書けない: %s" % (r["n"], i, why))
        # 同じ URL のリンクは1本にする(候補の URL が DOI や開いた本文と同じ時に、出どころを別々に書くと2本並んだ。D84 の試し)。
        # 同じかは grounded-citations の normalize_url と同じく、末尾の「/」と「#…」を落として見る
        seen, keep = {}, []
        for i, x in enumerate(r.get("link") or [], 1):
            u = (x.get("url") or "").split("#", 1)[0].rstrip("/") if isinstance(x, dict) else ""
            if u and u in seen:
                if x.get("na") and not seen[u].get("na"):
                    seen[u]["na"] = x["na"]          # 外す方の名前(「本文PDF」など)は残す方に引き継ぐ
                p("(#%s のリンクの %d本目は、前のリンクと同じ URL なので外した: %s)" % (r["n"], i, x["url"]))
                continue
            if u:
                seen[u] = x
            keep.append(x)
        if r.get("link") is not None:
            r["link"] = keep
    return out


def doi_soroe(x):
    return re.sub(r"^(https?://(dx\.)?doi\.org/|doi:)", "", (x or "").strip(), flags=re.I).lower()


def shikibetsu_problems(d, w, sh):
    """AI が手で書いた識別子を記録と照らす(D84 の7。grounded-citations の「打った物を記録で確かめる」)。→ 外れの並び
    ・書誌の項目ファイルの DOI と、その行が採った候補の DOI(検索の答えから道具が書いた物)が違えば止める(打ち間違いか別の文献)
    ・抜き書きに「画像から書き写し」とあるのに、この行の番号で頁を画像にした記録(honbun.py gazo)が無ければ止める
      (チェッカーは画像からの書き写しを照らさないので、画像を見た記録で代わりに確かめる)"""
    import honbun
    import kensaku
    _S, cands, _ = kensaku.load(w)
    sai = {}
    for c in cands.values():
        k = c.get("kime") if isinstance(c.get("kime"), dict) else None
        if k and k.get("kekka") == "sai":
            sai[k.get("gyou")] = c
    gazo = {t.get("n") for t in honbun.kiroku(w) if t.get("type") == "gazo"}
    out = []
    for r in d["gyou"]:
        s_doi = doi_soroe((sh.get(r["n"]) or {}).get("doi"))
        c = sai.get(r["n"])
        c_doi = doi_soroe((c or {}).get("doi"))
        if s_doi and c_doi and s_doi != c_doi:
            out.append("#%s: 書誌の項目ファイルの DOI(%s)が、この行が採った候補 %s の DOI(%s)と違う(打ち間違いか、別の文献)。"
                       "DOI のページを開いて確かめ、書誌の項目ファイルを直す" % (r["n"], s_doi, c.get("id"), c_doi))
        if any("画像から書き写し" in str(x.get("basho") or "") for x in r.get("nukigaki") or [] if isinstance(x, dict)) \
                and r["n"] not in gazo:
            out.append("#%s: 抜き書きの場所に「画像から書き写し」とあるのに、この行の番号で頁を画像にした記録が無い"
                       "(honbun.py <作業用フォルダ> gazo --n %s --peeji … で画像にし、Read で見て書き写す)" % (r["n"], r["n"]))
    return out


# ---- 記録から数え直す(帳尻・論点の番号・限界・方法の節の下書き) ----

def hizuke(s):
    m = DATE_RE.fullmatch(s or "")
    return "%d年%d月%d日" % tuple(int(x) for x in s.split("-")) if m else (s or "〔日付〕")


def from_records(d, w):
    import kensaku
    S, cands, _ = kensaku.load(w)
    a = d["atama"]
    labels = {}
    for r in a.get("ronten") or []:
        labels[str(r["no"])] = "論点%s" % r["no"] + ("(%s)" % r["shurui"] if r.get("shurui") else "")
    lines = kensaku.tally(S, cands, labels)
    d["chojiri"] = {"toki": ts(), "gyou": lines}
    by_n = {}
    for c in cands.values():
        k = c.get("kime")
        if k and k["kekka"] == "sai":
            for x in kensaku.belongs(c):
                by_n.setdefault(k["gyou"], set()).add(x)
    for r in d["gyou"] + d["toukei"]:
        r["ronten"] = sorted(by_n.get(r["n"], set()), key=int)
    # 限界の欄の機械の部分(使ったデータベース・失敗した検索・言語・年代・時点)
    dbs = Counter(s["db"] for s in S)
    te_only = {x for x in dbs if all(s.get("kiroku") == "te" for s in S if s["db"] == x)}
    own = d.get("db_na") or {}
    na = lambda x: own.get(x) or (DB_NA.get(x, x) + ("(手で記録)" if x in te_only and x not in DB_NA else ""))
    bad = Counter(s["db"] for s in S if s.get("jotai") in kensaku.SHIPPAI)
    k = ["言語: %s" % a.get("gengo", ""), "年代: %s" % a.get("nendai", ""),
         "探したデータベース(検索の回数): " + "・".join("%s %d回" % (na(x), n) for x, n in dbs.most_common())]
    if bad:
        k.append("失敗した検索(接続を切られた・件数の表示なし など): " + "・".join("%s %d回" % (na(x), n) for x, n in bad.most_common()))
    yk = ["#%s(%s)" % (r["n"], r["yomikiranai"].strip()) for r in d["gyou"] if (r.get("yomikiranai") or "").strip()]
    if yk:
        k.append("本文が無料で読めるのに、本文を読み切っていない行: " + "・".join(yk))
    k.append("時点: %s に探した結果(この後に出た文献は入っていない)" % a.get("jikkobi", ""))
    d["genkai_kikai"] = k
    # 方法の節の下書き(数は記録から。名前と版・決まりは空欄)
    allc = list(cands.values())
    n_mita = sum(1 for c in allc if c.get("kime") and c["kime"]["kekka"] in ("sai", "otosu"))
    n_sai = len({c["kime"]["gyou"] for c in allc if c.get("kime") and c["kime"]["kekka"] == "sai"})
    gos = []
    for s in S:
        if s.get("go") and s["go"] not in gos:
            gos.append(s["go"])
    rei = "」「".join(gos[:3])
    nl = len(labels)
    bun = ("文献は、%sに、%sで探した。検索語は「%s」など%d通りで、%sの論点ごとに表記と語の並べ方を変えて検索した(検索 %d回)。"
           "検索の結果の一覧に出た %d件のうち %d件の題名・抄録などを見て、「%s」に合う %d件を採った。"
           "種別の範囲は「%s」、年代の範囲は「%s」、言語は「%s」とした。"
           % (hizuke(a.get("jikkobi", "")), "・".join(na(x) for x in dbs), rei, len(gos), ("%dつ" % nl) if nl < 10 else ("%d個" % nl),
              len(S), len(allc), n_mita, (a.get("kijun") or "").replace("(未承認)", ""), n_sai,
              a.get("shubetsu_hani", ""), a.get("nendai", ""), a.get("gengo", "")))
    if any(s["db"] == "semanticscholar" and s.get("jotai") in ("ok", "zero") for s in S):
        bun += S2_HIKU
    ai = ("文献の検索・選別と要旨の下書きには、生成AI(〔AIの名前と版〕)を用いた。書誌はすべて原典のページで確かめ、"
          "要旨は〔本文・抄録〕を読んで作成し、〔著者名〕が内容を確認した。〔大学・投稿先の決まりに合わせて書き足す〕")
    d["hoho"] = {"bun": bun, "ai": ai}


# ---- Markdown(機械用の写し) ----

def md_table(rows, cols, sh):
    use = [(na, k) for na, k in cols if k in ("n", "shoshi") or any(cell(r, k, sh) for r in rows) or
           na in ("#", "書誌", "種別", "発見経路", "リンク", "入手状況", "精読", "要旨", "抜き書き", "用途タグ", "アクセス日")]
    out = ["| " + " | ".join(na for na, _ in use) + " |", "|" + "---|" * len(use)]
    for r in rows:
        out.append("| " + " | ".join(cell(r, k, sh) for _, k in use) + " |")
    return out


def render_md(d, sh):
    a = d["atama"]
    L = ["# 文献台帳: %s" % a.get("theme", ""), ""]
    for k, na in ATAMA:
        if k in a:
            L.append("- %s: %s" % (na, a[k]))
    for r in a.get("ronten") or []:
        L.append("- 論点%s%s: %s" % (r["no"], "(%s)" % r["shurui"] if r.get("shurui") else "", r.get("bun", "")))
    for kv in a.get("hoka") or []:
        L.append("- %s: %s" % (kv[0], kv[1]))
    for k, na in ATAMA_ATO:
        if k in a:
            L.append("- %s: %s" % (na, a[k]))
    L.append("")
    if d.get("shogou"):
        L += ["**宣言との照合**: %s" % d["shogou"], ""]
    L += list(HANREI) + [""]
    for c in d.get("chui") or []:
        L += ["**読み方の注意**: %s" % c, ""]
    for x in d.get("atama_bun") or []:
        L += [x, ""]
    L += ["## 台帳本体", ""]
    cols = [c for c in COLS if c[1] not in ("gengo", "biko") or any(r.get(c[1]) for r in d["gyou"])]
    if d.get("retsu"):
        known = dict(COLS)
        cols = [(na, known.get(na, na)) for na in d["retsu"]]
    L += md_table(d["gyou"], cols, sh) + [""]
    if d["toukei"]:
        L += ["## 統計原表", ""] + md_table(d["toukei"], TCOLS, sh) + [""]
    if d.get("totsugo"):
        L += ["**書誌突合(SKILL.md §2-5)**: %s" % d["totsugo"], ""]
    if d.get("shinkoku"):
        L += ["## 機械照合の申告", "", SHINKOKU_MAE, ""]
        for fuda in sorted(d["shinkoku"]):
            L += ["```%s" % fuda, d["shinkoku"][fuda], "```", ""]
    if d.get("chojiri"):
        L += ["## 選別の帳尻", "",
              "数は候補の一覧からスクリプトが数えた(kensaku.py chojiri・%s)。一覧に入るのは、各検索で画面に出た上位の候補と、手で足した候補だけ。"
              % d["chojiri"].get("toki", ""), ""] + d["chojiri"]["gyou"] + [""]
    t = d.get("tansaku") or {}
    L += ["## 探索記録(再挑戦の起点)", ""]
    if t.get("mae"):
        L += [t["mae"], ""]
    for b in t.get("bloku") or []:
        L += ["### " + b["midashi"]] + (b["gyou"] if "gyou" in b else ["- " + k for k in b.get("kajo") or []]) + [""]
    if d.get("nyushu_route"):
        L += ["## 入手ルート提案", ""] + ["- " + x for x in d["nyushu_route"]] + [""]
    gk = (d.get("genkai_kikai") or []) + (d.get("genkai") or [])
    if gk:
        L += ["## この台帳の限界", ""] + ["- " + x for x in gk] + [""]
    if d.get("hoho"):
        L += ["## 方法の節の下書き", "", d["hoho"]["bun"], "", d["hoho"]["ai"], ""]
    for s in d.get("sonota_setsu") or []:
        L += ["## " + s["midashi"], ""] + s["gyou"] + [""]
    L += [d.get("hikitsugi") or HIKITSUGI, ""]
    return "\n".join(L)


# ---- 引用文献の形(HTML でコピーする。形は run-ronbun-shippitsu の references/formats.md の例に合わせる) ----

# 7つ(論文の6つの書き方と書誌欄のまま)・副題はどの形も「-副題-」(ユーザーの決定 2026-11-01。claude-harness の D70)。
# A-1・C-2 の書式の例は Web の資料だけなので、論文と図書は同じ型の A-2・A-3・C-1 の項目の順に当てはめた
CITE_KATA = (("b", "タイプB(学会誌・紀要の論文)"), ("a2", "タイプA-2(研究大会の梗概)"), ("a3", "タイプA-3"), ("a1", "タイプA-1(角括弧型)"),
             ("c1", "タイプC-1(レポートの脚注)"), ("c2", "タイプC-2(脚注・半角区切り)"), ("shoshi", "書誌欄のまま"))


def cite_authors(names):
    names = [re.sub(r"\(.*?\)|（.*?）", "", x).strip() for x in names]
    if all(not re.search("[぀-ヿ㐀-鿿]", x) for x in names):
        return ", ".join(names)
    return "・".join(re.sub(r"[\s　]+", "", x) for x in names)


def cite_strings(r, sh):
    """1件の引用文献の形(番号は付けない。本文の初出順で振るため)。書誌の項目ファイルが無い行は書誌欄のままだけ"""
    s = sh.get(r["n"])
    url = ""
    if s and (s.get("doi") or "").strip():
        url = "https://doi.org/" + s["doi"].strip()
    elif r.get("link"):
        url = r["link"][0]["url"]
    out = {"shoshi": cell(r, "shoshi", sh) + ((" " + url) if url else "")}
    if not s or s.get("shurui", "ronbun") == "sonomama":
        return out
    au, nen = cite_authors(s.get("chosha") or []), s.get("nen", "")
    dai, fuku = (s.get("dai") or "").strip(), (s.get("fukudai") or "").strip()
    shi, pub, pg = (s.get("shi") or "").strip(), (s.get("shuppan") or "").strip(), (s.get("peji") or "").strip()
    maki, gou = (s.get("maki") or "").strip(), (s.get("gou") or "").strip()
    if maki.isdigit() and gou:
        vg = "第%s巻第%s号" % (maki, gou)
    elif maki.isdigit():
        vg = "第%s巻" % maki
    elif maki:
        vg = maki + (("第%s号" % gou) if gou else "")
    else:
        vg = ("第%s号" % gou) if gou else ""
    acc = (r.get("access") or "").replace("-", ".")
    # C-2 の閲覧日は頭の0を付けない(書式の例「2024.9.5 閲覧.」)
    acc2 = ".".join(str(int(x)) if x.isdigit() else x for x in acc.split(".")) if acc else ""
    etsu2 = ("%s 閲覧. " % acc2) if acc2 else ""
    title = dai + ("-%s-" % fuku if fuku else "")
    sh_kind = s.get("shurui", "ronbun")
    if sh_kind in ("hon", "hokoku"):
        out["b"] = ",".join(x for x in (au, nen, title, pub) if x)
        out["a2"] = "%s,『%s』.%s.%s．%s" % (au, title, pub, nen, url)
        out["a3"] = "%s,『%s』,%s,%s.%s" % (au, title, pub, nen, url)
        out["a1"] = "%s, %s,%s" % (au, nen, ", ".join(x for x in ("『%s』" % title, pub, url) if x))
        out["c1"] = "%s，『%s』．%s．%s. %s 閲覧日：%s" % (au.replace("・", "、"), title, pub, nen, url, acc)
        out["c2"] = "%s,『%s』.%s.%s. %s%s" % (au, title, pub, nen, etsu2, url)
        return out
    t_q = "「%s」" % title
    where = shi if sh_kind != "sho" else "『%s』" % shi
    out["b"] = ",".join(x for x in (au, nen, title, where, vg, pg) if x)
    out["a2"] = "%s,%s.%s%s.%s.%s．%s" % (au, t_q, where, vg, nen, ("pp." + pg) if pg else "", url)
    out["a3"] = "%s,%s,%s,%s,%s.%s" % (au, t_q, where, nen, ("p" + pg) if pg else "", url)
    out["a1"] = "%s, %s,%s" % (au, nen, ", ".join(x for x in (t_q, where + vg, ("p" + pg) if pg else "", url) if x))
    out["c1"] = "%s，%s．%s%s．%s. %s %s 閲覧日：%s" % (au.replace("・", "、"), t_q, where, vg, nen, ("pp" + pg + ".") if pg else "", url, acc)
    out["c2"] = "%s,%s.%s%s.%s.%s %s%s" % (au, t_q, where, vg, nen, ("pp" + pg + ".") if pg else "", etsu2, url)
    return out


def split_bun(s):
    """文を「。」で区切る(括弧の中の「。」では切らない)"""
    out, cur, depth = [], "", 0
    for ch in s or "":
        cur += ch
        if ch in "(（「『":
            depth += 1
        elif ch in ")）」』":
            depth = max(0, depth - 1)
        elif ch == "。" and depth == 0:
            out.append(cur.strip())
            cur = ""
    if cur.strip():
        out.append(cur.strip())
    return out


def kakunin_html(d):
    """台帳の確かめ(宣言との照合・書誌突合・読み方の注意)を、項目と1文ごとの箇条に割る"""
    o = []
    if d.get("shogou"):
        items = []
        for part in d["shogou"].split(" / "):
            m = re.match(r"^\s*([^=＝]{1,8})[=＝](.*)$", part)
            items.append("<li><b>%s</b>: %s</li>" % (E(m.group(1)), E(m.group(2))) if m else "<li>%s</li>" % E(part))
        o.append("<h3>宣言との照合(依頼で決めた範囲と、台帳の中身が合っているか)</h3><ul>%s</ul>" % "".join(items))
    if d.get("totsugo"):
        o.append("<h3>書誌突合(書誌を原典のページと1項目ずつ照らした結果)</h3><ul>%s</ul>" % "".join("<li>%s</li>" % E(x) for x in split_bun(d["totsugo"])))
    for c in d.get("chui") or []:
        o.append("<h3>読み方の注意</h3><ul>%s</ul>" % "".join("<li>%s</li>" % E(x) for x in split_bun(c)))
    return "".join(o)


# ---- HTML(人が見るページ) ----

E = html.escape
NYUSHU_CLS = {"全文OA": "ok", "抄録のみ": "warn", "未入手": "warn", "有料": "ac", "学内限定": "ac"}


def bib_parts(r, sh):
    """→ (著者, 年, 題, 残り)。書誌の項目ファイルがあればその項目、無ければ書誌の文を分ける"""
    s = sh.get(r["n"])
    if s and s.get("shurui", "ronbun") != "sonomama":
        import shoshi
        t = s["dai"].strip() + (("：" + s["fukudai"].strip()) if (s.get("fukudai") or "").strip() else "")
        whole = shoshi.render(s)
        head = "%s(%s)" % (shoshi.join_authors([x.strip() for x in s["chosha"]]), s["nen"])
        q = "『%s』" % t if s.get("shurui") in ("hon", "hokoku") else "「%s」" % t
        rest = whole[len(head) + len(q):] if whole.startswith(head + q) else ""
        return shoshi.join_authors(s["chosha"]), s["nen"], q, rest.strip()
    text = s["shoshi"] if s else cell(r, "shoshi", sh)
    m = re.match(r"^(.*?)\((\d{4}[a-z]?)\)(.*)$", text)
    if not m:
        return "", "", text, ""
    au, yr, rest = m.groups()
    t = re.match(r"^([「『].*?[」』])(.*)$", rest.strip())
    return (au, yr, t.group(1), t.group(2).strip()) if t else (au, yr, rest, "")


def link_label(x, i):
    na = x.get("na") or ""
    if "doi.org" in x["url"]:
        return "DOI"
    if "PDF" in na or x["url"].endswith((".pdf", "_pdf")):
        return "本文PDF"
    if "記事" in na:
        return "記事"
    return na or ("ページ" if i == 0 else "ほか")


def html_item(r, sh, rnames, toukei=False):
    au, yr, ti, rest = bib_parts(r, sh)
    y = r.get("yoshi") or {}
    rts = r.get("ronten") or []
    attrs = 'data-ronten="%s" data-nyushu="%s" data-seidoku="%s"' % (" ".join(rts), E(r.get("nyushu", "")), E(r.get("seidoku", "")))
    b = ['<span class="b">%s</span>' % E(r.get("shubetsu") or cell_shubetsu(r)),
         '<span class="b %s">%s</span>' % (NYUSHU_CLS.get(r.get("nyushu"), ""), E(r.get("nyushu", "")))]
    if not toukei:
        b.append('<span class="b %s">%s</span>' % ("ok" if r.get("seidoku") == "本文精読済み" else "warn", E(r.get("seidoku", ""))))
    if y.get("shurui"):
        b.append('<span class="b">%s</span>' % E(y["shurui"]))
    b += ['<span class="b rt" title="%s">論点%s</span>' % (E(rnames.get(x, "")), E(x)) for x in rts]
    o = ['<details class="it" id="g%d" %s><summary>' % (r["n"], attrs),
         '<div class="bib"><span class="no">#%d</span>%s%s<span class="ti">%s</span> %s</div>'
         % (r["n"], E(au), "(%s)" % E(yr) if yr else "", E(ti), E(rest)),
         '<div class="badges">%s</div></summary><div class="body">' % "".join(b)]
    cs = cite_strings(r, sh)
    o.append('<div class="cite"><span class="cite-l">引用文献の形</span><span class="cite-t" %s>%s</span>'
             '<button class="chip copy" type="button">コピー</button></div>'
             % (" ".join('data-%s="%s"' % (k, E(v)) for k, v in cs.items()), E(cs.get("b") or cs["shoshi"])))
    if y.get("bun") is not None:
        o.append("<p>%s</p>" % E(y["bun"]).replace("&lt;br&gt;", "<br>"))
    elif y:
        o.append('<div class="han">読めた範囲: %s</div><ul>%s</ul>' % (E(y.get("han", "")), "".join("<li>%s</li>" % E(k) for k in y.get("kajo") or [])))
    if r.get("nukigaki"):
        for x in r["nukigaki"]:
            o.append('<blockquote>「%s」<span class="where">%s</span></blockquote>' % (E(x["bun"]), E(x["basho"])))
    elif r.get("nukigaki_bun"):
        o.append("<blockquote>%s</blockquote>" % E(r["nukigaki_bun"]))
    elif not toukei:
        o.append('<div class="m">抜き書き: なし(%s)</div>' % E(r.get("nukigaki_nashi") or "書誌のみ"))
    if r.get("link_bun") is not None:
        urls = re.findall(r"https?://[^\s)（）]+", r["link_bun"])
        links = " ・ ".join('<a href="%s">%s</a>' % (E(u), "リンク%d" % (i + 1)) for i, u in enumerate(urls))
    else:
        links = " ・ ".join('<a href="%s">%s</a>' % (E(x["url"]), E(link_label(x, i))) for i, x in enumerate(r.get("link") or []))
    dl = [("リンク", links), ("種別の根拠", E(r.get("shubetsu_konkyo") or "")), ("見つけた道", E(r.get("keiro", ""))),
          ("使い道", E(r.get("yoto", ""))), ("アクセス日", E(r.get("access", "")))]
    if toukei:
        dl += [("調査年月", E(r.get("chosa_nengetsu", ""))), ("statInfId", E(r.get("statinfid", ""))), ("fileKind", E(r.get("filekind", "")))]
    if r.get("gengo"):
        dl.append(("言語", E(r["gengo"])))
    if r.get("biko"):
        dl.append(("備考", E(r["biko"])))
    o.append("<dl>%s</dl></div></details>" % "".join("<dt>%s</dt><dd>%s</dd>" % (k, v) for k, v in dl if v))
    return "".join(o)


def chips(group, label, values):
    return '<div class="chips"><span class="gl">%s</span>%s</div>' % (label, "".join(
        '<button class="chip" data-g="%s" data-v="%s" aria-pressed="false">%s</button>' % (group, E(v), E(t)) for v, t in values))


def render_html(d, sh):
    a = d["atama"]
    rows = d["gyou"]
    rnames = {}
    for r in a.get("ronten") or []:
        rnames[str(r["no"])] = "論点%s%s: %s" % (r["no"], "(%s)" % r["shurui"] if r.get("shurui") else "", r.get("bun", ""))
    ny = Counter(r.get("nyushu") for r in rows + d["toukei"])
    sd = Counter(r.get("seidoku") for r in rows)
    P = ['<div class="label">文献台帳</div><h1>%s</h1><div>目的: %s</div>' % (E(a.get("theme", "")), E(a.get("mokuteki", ""))),
         '<div class="m">種別範囲: %s ／ 年代範囲: %s ／ 言語: %s ／ 件数目安: %s ／ 実行日: %s</div>'
         % tuple(E(a.get(k, "")) for k in ("shubetsu_hani", "nendai", "gengo", "kensu", "jikkobi"))]
    P.append('<div class="card sum"><span class="lab">サマリー</span><ul><li>%d件%s。入手: %s。精読: %s</li>'
             % (len(rows) + len(d["toukei"]), "(統計原表 %d件を含む)" % len(d["toukei"]) if d["toukei"] else "",
                "・".join("%s %d" % kv for kv in ny.most_common()), "・".join("%s %d" % kv for kv in sd.most_common())))
    ron = a.get("ronten") or []
    empty = [x for x in ron if not any(str(x["no"]) in (r.get("ronten") or []) for r in rows + d["toukei"])]
    if ron:
        P.append("<li>論点 %d個のうち、文献のある論点 %d個%s</li>" % (len(ron), len(ron) - len(empty),
                 ("・文献の無い論点: " + "・".join("論点%s" % x["no"] for x in empty)) if empty else ""))
    P.append("</ul></div>")
    gk = (d.get("genkai_kikai") or []) + (d.get("genkai") or [])
    if gk:
        P.append('<div class="card lim"><span class="lab">この台帳の限界</span><ul>%s</ul></div>' % "".join("<li>%s</li>" % E(x) for x in gk))
    kak = kakunin_html(d)
    if kak:
        P.append('<details class="fold"><summary>台帳の確かめ(宣言との照合・書誌突合・読み方の注意)</summary><div class="kak">%s</div></details>' % kak)
    # 論点ごとの文献の数(D52 の I5。行を押すとその論点に絞る)
    P.append('<h2>論点ごとの文献の数</h2><div class="m">適合の基準: %s</div>' % E(a.get("kijun", "")))
    cj = {}
    for ln in (d.get("chojiri") or {}).get("gyou") or []:
        m = re.match(r"^- 論点(\d+)", ln)
        if m:
            cj[m.group(1)] = ln
    tb = " ".join(b["midashi"] for b in (d.get("tansaku") or {}).get("bloku") or [])
    P.append("<table><tr><th>論点</th><th>採った</th><th>見た</th><th>未判定</th><th>探索記録</th></tr>")
    for x in ron:
        no = str(x["no"])
        c = cj.get(no, "")
        num = lambda key, c=c: (re.search(key + r" (\d+)件", c) or [None, "—"])[1]
        n_sai = sum(1 for r in rows + d["toukei"] if no in (r.get("ronten") or []))
        P.append('<tr class="rt" data-v="%s"><td>論点%s%s<br><span class="m">%s</span></td><td class="n">%d</td><td class="n">%s</td>'
                 '<td class="n">%s</td><td>%s</td></tr>' % (E(no), E(no), "(%s)" % E(x["shurui"]) if x.get("shurui") else "", E(x.get("bun", "")),
                                                        n_sai, num("見た"), num("未判定"), "あり" if ("論点" + no) in tb else "—"))
    P.append('</table><div class="m">採った= この論点の材料として台帳に載せた件数(1件が2つ以上の論点に入るので、合計は件数より多くなることがある)。見た・未判定= 検索の一覧に出た候補のうち、載せるか落とすかを決めた数と、まだ決めていない数。探索記録の「あり」= 薄かった所と次の一手を、下の「探索記録」の欄に書いた。(未承認)= 論点と基準を、依頼した人にまだ確かめていない。</div>'
             '<div class="m">探し方(人と場): %s</div>' % E(a.get("hito_to_ba", "")))
    # 一覧(番号順・論点と入手と精読で絞る。D67 の 3)
    P.append('<h2>文献の一覧</h2><div class="bar">')
    P.append(chips("ronten", "論点", [(str(x["no"]), "論点%s%s" % (x["no"], "(%s)" % x["shurui"] if x.get("shurui") else "")) for x in ron]))
    P.append(chips("nyushu", "入手", [(k, k) for k in NYUSHU if ny.get(k)]))
    P.append(chips("seidoku", "精読", [(k, k) for k in SEIDOKU if sd.get(k)]))
    P.append('<div class="chips"><span class="gl">探す</span><input type="search" id="q" placeholder="著者・題・要旨の語">'
             '<button class="chip" id="openall">すべて開く</button><span class="cnt" id="cnt"></span></div>'
             '<div class="chips"><span class="gl">引用の形</span><select id="kata">%s</select>'
             '<button class="chip" id="copyall" type="button">表示中の文献をまとめてコピー</button>'
             '<span class="cnt">番号は付けない(本文の初出順で振る)。刊行の月日は台帳に無いので年だけ</span></div></div>'
             % "".join('<option value="%s">%s</option>' % kv for kv in CITE_KATA))
    P.extend(html_item(r, sh, rnames) for r in rows)
    if d["toukei"]:
        P.append("<h3>統計原表</h3>")
        P.extend(html_item(r, sh, rnames, toukei=True) for r in d["toukei"])
    if d.get("hoho"):
        P.append('<h2>論文の方法の節の下書き</h2><div class="m">数は検索の記録と候補の一覧からスクリプトが書いた。〔 〕は自分で埋める。</div>'
                 '<div class="draft">%s</div><div class="draft">%s</div>' % (E(d["hoho"]["bun"]), E(d["hoho"]["ai"])))
    P.append("<h2>探した記録</h2>")
    if d.get("chojiri"):
        P.append('<details class="fold"><summary>選別の帳尻(論点ごとに、探した数・見た数・採った数)</summary>'
                 '<p class="m">落とした理由の番号: ①重複 ②範囲外(種別・年代・言語) ③確かめられない(ページが開けない) ④別の対象 ⑤論点に効かない。'
                 'ヒット計= 検索ごとの件数の合計(同じ文献が何度も数えられている)。</p><ul>%s</ul></details>'
                 % "".join("<li>%s</li>" % E(x[2:] if x.startswith("- ") else x) for x in d["chojiri"]["gyou"]))
    t = d.get("tansaku") or {}
    body = ('<p class="m">%s</p>' % E(t["mae"]) if t.get("mae") else "") + "".join(
        "<h3>%s</h3><ul>%s</ul>" % (E(b["midashi"]), "".join("<li>%s</li>" % E(re.sub(r"^- ", "", k).replace("**", ""))
                                                         for k in (b["gyou"] if "gyou" in b else b.get("kajo") or []) if k.strip()))
        for b in t.get("bloku") or [])
    P.append('<details class="fold"><summary>探索記録(薄かった論点と次の一手・%d項目)</summary>%s</details>' % (len(t.get("bloku") or []), body))
    if d.get("nyushu_route"):
        P.append('<details class="fold"><summary>手に入っていない文献の入手の道(%d件)</summary><ul>%s</ul></details>'
                 % (len(d["nyushu_route"]), "".join("<li>%s</li>" % E(x) for x in d["nyushu_route"])))
    if d.get("shinkoku"):
        P.append('<details class="fold"><summary>機械照合の申告(段階%s をチェッカーの出力のまま)</summary>%s</details>'
                 % ("・".join(k[6].upper() for k in sorted(d["shinkoku"])), "".join("<pre>%s</pre>" % E(d["shinkoku"][k]) for k in sorted(d["shinkoku"]))))
    P.append('<h2>凡例</h2><div class="m">%s</div>' % "<br>".join(E(re.sub(r"\*\*", "", h)) for h in HANREI))
    P.append('<p class="m">%s</p>' % E(HIKITSUGI))
    with open(TEMPLATE, encoding="utf-8") as f:
        page = f.read()
    return page.replace("@@TITLE@@", E("文献台帳: " + a.get("theme", ""))).replace("@@BODY@@", "\n".join(P))


def honbun_problems(r, oa_url, x, kagi=None):
    """本文が無料で読める行を、開いた記録(honbun.py)と照らす。kagi= その行の文献の鍵(honbun.kagi の形)を渡すと、
    鍵の合わない置き場を開いた記録は数えない(別の文献を開いた記録で通さないため)。→ 外れの並び"""
    import honbun
    n, yk = r["n"], (r.get("yomikiranai") or "").strip()
    where = oa_url or "入手状況が全文OA"
    toru = x["toru"]
    if kagi is not None:
        toru = [t for t in x["toru"] if honbun.kagi(t.get("url")) & kagi]
        if x["toru"] and not toru:
            return ["#%s: 開いた記録の置き場(%s)が、この行のリンクにも採った候補の置き場にも無い(別の文献を開いた記録かもしれない。"
                    "行の番号が付け替わった時など)。この行のリンクか採った候補の置き場を honbun.py <作業用フォルダ> toru --n %s --url <置き場> "
                    "で開き直す。リンクに無い置き場で本文を読んだ時は、その本文の題名と著者がこの行の書誌と合うかを確かめてから、"
                    "行の link に {\"honbun\": 開いた回} を足す(合わなければ別の文献なので足さない。URL は kaku --w が開いた記録から書く)"
                    % (n, "・".join(sorted({t.get("url", "") for t in x["toru"]})), n)]
    if not toru:
        return ["#%s: 本文が無料で読める(%s)のに、置き場を開いた記録が無い。honbun.py <作業用フォルダ> toru --n %s --url <置き場> で開き、"
                "本文を全部読む" % (n, where, n)]
    x = dict(x, toru=toru)
    # 開けても読めない PDF(壊れている・パスワードが掛かっている・PyMuPDF が無い。toru が yomenai を残す)は、開けなかった物と同じに扱う
    oks = [t for t in x["toru"] if t.get("jotai") == "ok" and not t.get("yomenai")]
    if not oks:
        why = "・".join(sorted({t.get("yomenai") or t.get("why") or t.get("jotai", "") for t in x["toru"]}))
        if r.get("seidoku") == "本文精読済み":
            return ["#%s: 置き場を開けなかった(%s)のに本文精読済み" % (n, why)]
        if not yk.startswith(("開けなかった", "出版社に断られた")):
            return ["#%s: 置き場を開けなかった(%s)ので、yomikiranai は「開けなかった(…)」か「出版社に断られた(…)」で始める" % (n, why)]
        return []
    pdfs = [t for t in oks if t.get("shurui") == "pdf"]
    gk = x.get("gazo_k") or {None: x.get("gazo") or set()}

    def mada_of(t):
        # その回に開いた PDF の、画像にしていない文字の取れない頁(回の書かれていない古い画像の記録は、どの回にも数える)
        return sorted(set(t.get("kuzure") or []) - (gk.get(t.get("k"), set()) | gk.get(None, set())))

    def okiba(t):
        # 同じ置き場の目印。J-STAGE は記事の鍵で数える(…/_pdf と …/_pdf/-char/ja のように形の違う同じ記事の PDF を開き直した試しがあった)
        ks = honbun.kagi(t.get("url"))
        return next((k for k in ks if k.startswith("jstage:")), None) or next((k for k in ks if k.startswith("url:")), t.get("url"))
    # 置き場ごとに、どれかの回で文字の取れない頁を全部画像にしていればよい(同じ置き場を開き直した時)。
    # 置き場の違う PDF(付録・分冊・概要版)は、どれも画像にする
    oki = {}
    for t in pdfs:
        oki.setdefault(okiba(t), []).append(t)
    nokori = [ts[-1] for ts in oki.values() if all(mada_of(t) for t in ts)]
    not_text = not pdfs and all((t.get("moji") or 0) < honbun.HONBUN_MOJI for t in oks)
    if r.get("seidoku") == "本文精読済み":
        if nokori:
            t = nokori[0]
            mada = mada_of(t)
            return ["#%s: %s回目に開いた PDF の文字の取れない頁 %s を画像にした記録が無い(honbun.py <作業用フォルダ> gazo --n %s --k %s "
                    "--peeji %s で画像にして見る)。画像で見ずに本文精読済みにしない"
                    % (n, t.get("k"), "・".join(map(str, mada)), n, t.get("k"), ",".join(map(str, mada)))]
        if not_text:
            return ["#%s: 開けたのは本文でないページ(PDF でない中身 %s字。図・案内・飛び先のページ)だけなのに本文精読済み。"
                    "本文PDF か本文のページを開いて読む" % (n, "・".join(str(t.get("moji")) for t in oks))]
        return []
    big = any((t.get("peeji") or 0) >= 200 for t in pdfs)
    # 「画像でも読めない頁」は、文字の取れない頁のある PDF を、その頁まで画像にして見た時だけ訳にできる
    gazo_de = not nokori and any(t.get("kuzure") and not mada_of(t) for t in pdfs)
    if (yk.startswith("200頁以上") and big) or (yk.startswith("置き場に本文が無い") and not_text)             or (yk.startswith("画像でも読めない頁") and gazo_de):
        return []
    desc = "PDF %s頁" % "・".join(str(t.get("peeji")) for t in pdfs) if pdfs else "中身 %s字" % "・".join(str(t.get("moji")) for t in oks)
    return ["#%s: 開けた本文(%s)を読み切っていない。全部読んで本文精読済みにする(訳にできるのは、200頁以上の PDF・図や案内だけの"
            "ページ(置き場に本文が無い)・画像にしても読めない頁(画像にした記録が要る)だけ。時間がかかることは訳にならない)" % (n, desc)]


def kouho_kagi(c):
    """候補の鍵(url・oa_url・doi・候補の一覧の鍵。honbun.kagi の形)"""
    import honbun
    s, doi = set(), c.get("doi")
    for u in (c.get("url"), c.get("oa_url"), "https://doi.org/" + doi if isinstance(doi, str) and doi else None):
        if isinstance(u, str):
            s |= honbun.kagi(u)
    return s | {x.lower() for x in c.get("kagi") or [] if isinstance(x, str)}


def sai_kagi(cands):
    """採った候補の鍵を、採った時の行の番号ごとに。→ {行: [鍵の集まり]}"""
    out = {}
    for c in cands.values():
        k = c.get("kime")
        if k and k["kekka"] == "sai":
            out.setdefault(k["gyou"], []).append(kouho_kagi(c))
    return out


KEKKA_GO = {"otosu": "落とした", "horyu": "保留", "sai": "採った"}


def nosenai(d, w, cands, sk, kensa=()):
    """本文の置き場を開いて本文が開けたのに、台帳に載せていない・読んでいない記録。→ 納品のチャットに出す行の並び。
    1. どの台帳の行(文献・統計原表)の鍵とも合わない記録(台帳に載せなかった文献)
    2. 行の鍵と合うが、その行に全部読む照らし(kensa= 照らしの掛かる行の番号)が掛からず、精読が本文精読済みでなく、
       読み切れなかった訳(yomikiranai)も無い記録(行を「抄録のみ」にして残すと、照らしを通った)
    本文でないページ(PDF でなく HONBUN_MOJI 字に満たない)・開けなかった記録・url の無い記録は出さない。同じ置き場(J-STAGE は記事)は1つに"""
    import honbun
    bunken = [r for r in d.get("gyou") or [] if isinstance(r, dict)]
    rows = bunken + [r for r in d.get("toukei") or [] if isinstance(r, dict)]
    mine = [(r, gyou_kagi(r, sk.get(r.get("n"), []))) for r in rows]
    link = [(r, gyou_kagi(r, [])) for r in rows]
    aru = {r.get("n") for r in rows}
    ck = [(c, kouho_kagi(c)) for c in cands.values() if isinstance(c, dict)]
    out, mita = [], set()
    for t in honbun.kiroku(w):
        if t.get("type") != "toru" or t.get("jotai") != "ok" or not isinstance(t.get("url"), str):
            continue
        pdf = t.get("shurui") == "pdf"
        if not pdf and (t.get("moji") or 0) < honbun.HONBUN_MOJI:
            continue
        ks = honbun.kagi(t["url"])
        u = next((k for k in ks if k.startswith("jstage:")), None) or next((k for k in ks if k.startswith("url:")), t["url"])
        if u in mita:
            continue
        what = ("PDF %s頁・文字の取れない頁 %d%s" % (t.get("peeji"), len(t.get("kuzure") or []), "・読めない PDF" if t.get("yomenai") else "")
                if pdf else "中身 %s字" % t.get("moji"))
        au = [r for r, m in mine if ks & m]
        if au:
            # 統計原表の行は精読の欄を持たないので、読んだかを問わない
            yomazu = [r for r in au if any(r is b for b in bunken) and r.get("n") not in kensa and r.get("seidoku") != "本文精読済み"
                      and not (r.get("yomikiranai") or "").strip()]
            if yomazu and len(yomazu) == len(au):
                mita.add(u)
                out.append("- %s(%s。台帳の #%s に載せたが、開いた本文を読まずに精読は「%s」。全部読んで本文精読済みにするか、"
                           "読み切れなかった訳を yomikiranai に書く)" % (t["url"], what, yomazu[0].get("n"), yomazu[0].get("seidoku")))
            continue
        mita.add(u)
        kouho = []
        for c, cks in ck:
            if not cks & ks:
                continue
            k = c.get("kime") if isinstance(c.get("kime"), dict) else {}
            if k.get("kekka") == "sai":
                hoka = [r.get("n") for r, m in link if cks & m]
                ketsu = "採った" + ("(台帳の %s の文献かもしれない。そうならその行の番号で開き直し、link に {\"honbun\": true} を足す)" % "・".join("#%s" % x for x in hoka) if hoka else "")
            elif k:
                ketsu = "%s(%s)" % (KEKKA_GO.get(k.get("kekka"), k.get("kekka")), k.get("kimete") or "訳の書き無し")
            else:
                ketsu = "判定していない"
            kouho.append("候補 %s「%s」は%s" % (c.get("id"), str(c.get("dai") or "")[:40], ketsu))
        gyou = ("台帳の #%s は在るが、この置き場はそのリンクに無い。#%s の本文なら、題名と著者を確かめてから link に {\"honbun\": %s} を足す"
                % (t.get("n"), t.get("n"), t.get("k")) if t.get("n") in aru else "台帳に #%s の行は無い。載せなかった訳を書く" % t.get("n"))
        out.append("- %s(%s。#%s の番号で %s回目に開いた。%s。%s)" % (t["url"], what, t.get("n"), t.get("k"), gyou,
                                                         "・".join(kouho) or "候補の一覧に無い"))
    return out


def gyou_kagi(r, kouho):
    """その行の文献の鍵。行のリンクの鍵に、リンクと鍵が1つでも合う(同じ文献と分かる)採った候補の鍵を足す
    (候補を採った時の行の番号のまま台帳の行を並べ替えると、別の文献の候補の鍵が混ざるため)。kouho= sai_kagi のその行の番号の並び"""
    import honbun
    mine = set()
    for x in r.get("link") or []:
        mine |= honbun.kagi(x.get("url") if isinstance(x, dict) else x)
    for u in re.findall(r"https?://[^\s)（）]+", r.get("link_bun") or ""):    # 古い Markdown から写し、文のまま残ったリンク
        mine |= honbun.kagi(u)
    for s in kouho:
        if s & mine:
            mine |= s
    return mine


def gyou_pdfs(r, w, sk=None):
    """その行の文献の置き場を開いた記録(honbun.py)のうち、開けた PDF のパス(置き場の鍵が行と合う物だけ)。sk= sai_kagi の結果"""
    import honbun
    import kensaku
    if sk is None:
        sk = sai_kagi(kensaku.load(w)[1])
    mine = gyou_kagi(r, sk.get(r["n"], []))
    return [os.path.join(w, t["file"]) for t in honbun.kiroku(w)
            if t["type"] == "toru" and t["n"] == r["n"] and t.get("jotai") == "ok" and t.get("shurui") == "pdf"
            and t.get("file") and honbun.kagi(t.get("url")) & mine]


def kakunin_w(d, w):
    """作業用フォルダの記録と台帳を照らす(kaku --w)。→ (外れの並び, 納品のチャットに出す行の並び)"""
    import honbun
    import kensaku
    import kiroku
    bad, chat = [], []
    _s, cands, _ = kensaku.load(w)
    # 本文が無料で読める文献は、置き場を開いて全部読む(置き場を開かずに抄録で済ませた台帳が続いた。ch-3ni)。
    # 開いたか・開けた本文の頁の数・文字の取れない頁を画像にしたかは honbun.py の記録で照らす(申告では通さない)
    # 開いた記録は、置き場の鍵がその行の鍵(gyou_kagi)と合う物だけを数える(行の番号が付け替わり、別の文献を開いた記録を持つ行があった)
    oa = {}
    for c in cands.values():
        k = c.get("kime")
        if k and k["kekka"] == "sai" and c.get("oa_url"):
            oa.setdefault(k["gyou"], c["oa_url"])
    sk = sai_kagi(cands)
    hb = honbun.by_n(honbun.kiroku(w))
    for r in d.get("gyou") or []:
        n = r["n"]
        if not (r.get("nyushu") == "全文OA" or n in oa):
            continue
        bad += honbun_problems(r, oa.get(n), hb.get(n) or {"toru": [], "gazo": set()}, gyou_kagi(r, sk.get(n, [])))
    # 論点と適合の基準の承認の記録(未承認のまま納め、チャットにも見せなかった台帳があった。ch-21p)
    a = d.get("atama") or {}
    sa = kiroku.ronten_sa(w)
    mi = "(未承認)" in json.dumps({"k": a.get("kijun"), "r": a.get("ronten")}, ensure_ascii=False)
    if sa is None:
        bad.append("論点の案の記録が無い(確認ゲートで kiroku.py ronten <作業用フォルダ> an … を打つ)")
    elif sa["jotai"] == "承認の記録なし":
        bad.append("論点の案はあるが、承認(kiroku.py ronten … shonin)か未承認(kiroku.py ronten … mishonin)の記録が無い")
    elif mi and sa["jotai"] != "未承認":
        bad.append("頭の部分に「(未承認)」とあるのに、論点の記録は「%s」(未承認で進めたなら kiroku.py ronten … mishonin)" % sa["jotai"])
    elif sa["jotai"] == "未承認" and not mi:
        bad.append("論点の記録は未承認なのに、頭の部分の適合の基準・論点に「(未承認)」が無い")
    if sa and sa["jotai"] == "未承認":
        chat.append("★論点と適合の基準は未承認。納品のチャットに次の文をそのまま見せ、承認か直しを求める(台帳の頭に添えただけでは届かない):")
        for x in a.get("ronten") or []:
            chat.append("- 論点%s%s: %s" % (x.get("no"), "(%s)" % x["shurui"] if x.get("shurui") else "", x.get("bun", "")))
        chat.append("- 適合の基準: %s" % a.get("kijun", ""))
        if a.get("hito_to_ba"):
            chat.append("- 探し方(人と場): %s" % a["hito_to_ba"])
    yk = [r for r in d.get("gyou") or [] if (r.get("yomikiranai") or "").strip()]
    if yk:
        chat.append("★本文が無料で読めるのに、本文を読み切っていない行 %d件。納品のチャットに1件も落とさずに出す:" % len(yk))
        chat += ["- #%s: %s" % (r["n"], r["yomikiranai"].strip()) for r in yk]
    # 本文の置き場を開いたのに台帳に載せていない・読んでいない文献(開いた後に読みにくい文献を台帳から外すと、全部読む照らしを
    # 通ってしまった。2026-11-02 の配る束の試し。ユーザーの決定= claude-harness の D80)。止めずに、納品のチャットに出す
    kensa = {r.get("n") for r in d.get("gyou") or [] if r.get("nyushu") == "全文OA" or r.get("n") in oa}
    ns = nosenai(d, w, cands, sk, kensa)
    if ns:
        chat.append("★本文の置き場を開いたのに、台帳に載せていない・読んでいない文献 %d件。納品のチャットに1件も落とさずに出し、"
                    "件ごとに書いたこと(載せなかった訳を書く・行の link に {\"honbun\": 開いた回} を足す・全部読むか読み切れなかった訳を書く)をする"
                    "(読みにくいことは訳にならない):" % len(ns))
        chat += ns
    return bad, chat


def cmd_kaku(a):
    d = load(a.file)
    sh = load_shoshi(shoshi_path(a.file))
    chat = []
    strict = not d.get("utsushi")
    bad = []
    if a.w:
        from_records(d, a.w)
        bad += link_from_records(d, a.w, sh) + shikibetsu_problems(d, a.w, sh)
    elif strict:
        bad += ["#%s: リンクの URL がまだ無い(kaku --w <作業用フォルダ> で記録から書く)" % r["n"] for r in d["gyou"]
                if r.get("link_bun") is None and any(isinstance(x, dict) and not x.get("url") for x in r.get("link") or [])]
    bad += problems(d, sh, strict=strict)
    if a.w and strict:
        b, chat = kakunin_w(d, a.w)
        bad += b
    if bad and strict:
        for x in bad:
            p("✕ " + x)
        raise Stop("台帳の JSON の形が外れているので、HTML と Markdown を作らない(上の ✕ を直す)")
    if a.w:
        save(a.file, d)
    out_html = a.html or os.path.join(os.path.dirname(os.path.abspath(a.file)), base(a.file) + ".html")
    write_text(out_html, render_html(d, sh))
    p("HTML: %s" % out_html)
    out_md = a.md or (os.path.join(a.w, base(a.file) + ".md") if a.w else None)
    if out_md:
        write_text(out_md, render_md(d, sh))
        # 書いた時刻と台帳の行の指紋を残す(reigai が、渡されたチェッカーの出力がいまの行から出た物かを見る)
        import time
        with open(out_md + ".kagi.jsonl", "a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps({"t": time.time(), "kagi": md_kagi(out_md)}) + "\n")
        p("Markdown(機械用。チェッカーと確かめ役に渡す): %s" % out_md)
    for x in bad:
        p("(写し直した台帳のため止めない)✕ " + x)
    for x in chat:
        p(x)
    return 0


# ---- 測れなかった物が例外だけかを決める(reigai) ----

REIGAI_ITEM = re.compile(r"^\s*- L(\d+) (.*?) —— (.*)$")
REIGAI_A = ("B-11", "B-12", "B-13", "B-14", "B-15", "B-16")


def md_kagi(md_path):
    """機械用の Markdown の、台帳の行(番号で始まる表の行)を、Markdown の行の番号ごと並べた指紋(申告の節・選別の帳尻の時刻が変わっても変わらない)"""
    import hashlib
    with open(md_path, encoding="utf-8") as f:
        rows = ["%d:%s" % (i, line.rstrip("\r\n")) for i, line in enumerate(f, 1) if re.match(r"\|\s*\d+\s*\|", line)]
    return hashlib.sha256("\n".join(rows).encode("utf-8")).hexdigest()[:16]


def md_rireki(md_path):
    """kaku が機械用の Markdown を書いた記録(<Markdown>.kagi.jsonl。時刻と md_kagi)。→ 古い順の並び"""
    out = []
    try:
        with open(md_path + ".kagi.jsonl", encoding="utf-8") as f:
            for line in f:
                try:
                    x = json.loads(line)
                except ValueError:
                    continue
                if isinstance(x, dict) and isinstance(x.get("t"), (int, float)) and isinstance(x.get("kagi"), str):
                    out.append(x)
    except OSError:
        pass
    return sorted(out, key=lambda x: x["t"])


def md_line_rows(md_path):
    """機械用の Markdown の行の番号(1から)→ 台帳の行の番号"""
    out = {}
    with open(md_path, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            m = re.match(r"\|\s*(\d+)\s*\|", line)
            if m:
                out[i] = int(m.group(1))
    return out


def reigai_items(block):
    """申告の囲みの「★未検査 n件」「★測れなかった n件」の下の項目。→ [(Markdown の行, 何, 訳, 当てたページ)]"""
    lines = block.split("\n")
    out, on = [], False
    for i, x in enumerate(lines):
        if re.match(r"^・★(未検査|測れなかった) \d+件", x):
            on = True
            continue
        if not on:
            continue
        m = REIGAI_ITEM.match(x)
        if m:
            nxt = lines[i + 1] if i + 1 < len(lines) else ""
            ate = nxt.split("当てたページ:", 1)[1].strip() if "当てたページ:" in nxt else ""
            out.append((int(m.group(1)), m.group(2), m.group(3), ate))
        elif not x.strip().startswith("当てたページ:"):
            on = False
    return out


def row_doi(r):
    import kensaku
    for x in r.get("link") or []:
        got = kensaku.doi_of(x.get("url", ""))
        if got:
            return got
    return ""


def kotowa_row(r):
    """出版社に断られた行として扱えるか(DOI を持ち、備考に断られた・証明書の誤りでつながらないと書いてある)"""
    return bool(row_doi(r)) and bool(KOTOWA_BIKO.search(r.get("biko") or ""))


def kotowa_link(r, url, w):
    """段階A で届かなかったリンクを、断られた行の例外に入れてよいか。→ 代わりの確かめの説明(入れない時は None)。
    行の DOI のリンクは、書誌を段階B が登録の記録で確かめる。DOI でない置き場は、この行の番号で honbun.py が開けた物だけ
    (中身は段階C の代わりの照らしで見る)。どちらでもないリンクは何も確かめていないので、例外にしない"""
    import honbun
    import kensaku
    doi = kensaku.doi_of(url or "")
    if doi and doi.lower() == row_doi(r).lower():
        return "書誌は登録の記録で確かめた"
    ks = honbun.kagi(url)
    if any(t["type"] == "toru" and t.get("n") == r["n"] and t.get("jotai") == "ok" and honbun.kagi(t.get("url")) & ks
           for t in honbun.kiroku(w)):
        return "この置き場は honbun.py で開けた。書誌は登録の記録で確かめた"
    return None


# 段階A の訳のうち、出版社が機械の取得を断った(401・403)物と、出版社のページに機械が証明書の誤りでつながらない物。
# 後者は Emerald で、Python から開くと毎回 SSLCertVerificationError になった(curl では 403。2026-11-02 の配る束の試し。D81)
KOTOWA_RE = re.compile(r"HTTP 40[13]|SSLCertVerificationError|CERTIFICATE_VERIFY_FAILED|certificate verify failed", re.I)
# 備考の「断られた・証明書の誤り」の書き方(「断っていない」は数えない)
KOTOWA_BIKO = re.compile(r"断られ|断った|断ってい(?!ない)|証明書")
# 代わりの照らしでも、区切りはチェッカーと同じく6字以上(細かく刻むと言い換えが通る。チェッカーの nukigaki_short と同じ数)
KUGIRI_MIN = 6
# 代わりの照らしの抄録・本文PDF が、この行の文献かを見る題名の頭の長さ(字と数字で数える。副題・版の違いで題名の後ろが変わっても外さないため)
DAI_KASHIRA = 20
# チェッカーの一覧は引用を90字で切る。括弧を外してこの長さ以上なら、切れた字かもしれない
KIRE = 88
# 段階C の訳のうち、書誌欄の題名が『』(図書・報告書・白書の書き方)なので、チェッカーが対照を置けない物(D81)
TAISHO_NASHI = "対照が置けない"


def eigo_nukigaki(r, w, sk=None, dai=None):
    """英語の行の抜き書きが、その行の DOI で保存した抄録か、その行の置き場を開いた本文PDF(gyou_pdfs)に原文のまま在るか。→ (在るか, 説明)。
    dai(書誌の項目ファイルの題名)を渡すと、抄録と本文PDF はこの行の題名が在る物だけで照らす(別の文献の抄録・PDF で通さないため)"""
    nks = r.get("nukigaki") or []
    if not nks:
        return False, "抜き書きが無い"
    sho, sho_nai = shoroku(r, w, dai)
    pdfs = None
    for nk in nks:
        bun, basho = nk.get("bun") or "", nk.get("basho") or ""
        if kugiri_mijikai(bun):
            return False, "抜き書きに%d字に満たない区切りが在る(チェッカーと同じく照らさない)" % KUGIRI_MIN
        if "抄録" in basho:
            if sho is None:
                return False, "抄録の抜き書きだが、" + sho_nai
            if aru(sho, bun) is None:
                return False, "抜き書きが保存した抄録に原文のまま無い"
        else:
            pdfs = gyou_pdfs(r, w, sk) if pdfs is None else pdfs
            if not pdfs:
                return False, pdf_nai(r, w)
            if not pdf_ni_aru(pdfs, bun, dai):
                return False, "本文の抜き書きが、この行の置き場を開いた記録(honbun.py)の本文PDF(この行の題名が在る物)に原文のまま無い"
    return True, "抜き書きは%sに原文のまま在る" % ("保存した抄録" if all("抄録" in (x.get("basho") or "") for x in nks) else "保存した抄録・この行の本文PDF")


def shoroku(r, w, dai=None):
    """その行の DOI(無ければリンクの arXiv の番号)で作業用フォルダに保存した抄録。→ (本文, 無い時の訳)。
    名前は kensaku.py … shoroku と同じ(--doi は DOI、--arxiv は版を外した番号。英数字と ._- のほかは _)。
    dai を渡すと、頭の「題名:」の行にこの行の題名が在る抄録だけを返す"""
    import honbun
    names = [row_doi(r)] if row_doi(r) else []
    for x in r.get("link") or []:
        names += [k[len("arxiv:"):] for k in honbun.kagi(x.get("url") if isinstance(x, dict) else x) if k.startswith("arxiv:")]
    for name in names:
        path = os.path.join(w, "shoroku", re.sub(r"[^A-Za-z0-9._-]", "_", name) + ".txt")
        if os.path.exists(path):
            parts = open(path, encoding="utf-8").read().split("\n\n", 1)
            if dai and not dai_ni_aru(dai, parts[0]):
                return None, "保存した抄録(%s)の題名が、この行の題名と合わない(別の文献の抄録か)" % os.path.basename(path)
            return parts[-1], ""
    return None, "この行の DOI か arXiv の番号で保存した抄録(shoroku/)が無い"


def dai_kagi(s):
    """題名を照らす鍵。全角半角と大文字小文字をそろえ、字と数字だけを残す(PDF の行末のハイフン・記号・空白の違いで外さないため)"""
    import unicodedata
    t = unicodedata.normalize("NFKC", s or "").casefold()
    return "".join(c for c in t if unicodedata.category(c)[0] in "LN")


def dai_ni_aru(dai, text):
    """その文に、この行の題名の頭(字と数字で DAI_KASHIRA 字)が在るか"""
    k = dai_kagi(dai)[:DAI_KASHIRA]
    return bool(k) and k in dai_kagi(text)


def kugiri_mijikai(bun):
    """引用を「…」で区切った区切りに、空白を落として KUGIRI_MIN 字に満たない物が在るか(チェッカーの nukigaki_short と同じ決まり)"""
    import nukigaki
    pieces = [x for x in (nukigaki.norm(p) for p in (bun or "").split("…")) if x]
    return not pieces or min(len(x) for x in pieces) < KUGIRI_MIN


def yoshi_zenbun(r, q):
    """要旨の「」のうち、頭が q と合う物の全文(チェッカーの一覧は引用を90字で切るので、切れた字だけで照らさないため)。
    合う物が無ければ、q が切れていない長さなら q、切れたかもしれない長さなら None"""
    import nukigaki
    y = r.get("yoshi")
    texts = [y] if isinstance(y, str) else [y.get("han") or ""] + [str(x) for x in y.get("kajo") or []] if isinstance(y, dict) else []
    nq = nukigaki.norm(q)
    for s in texts:
        for k in re.findall(r"「(.*?)」", s):
            if nq and nukigaki.norm(k).startswith(nq):
                return k
    return q if len(q) < KIRE else None


def aru(text, bun):
    """抄録の文に、その文が原文のまま在るか(nukigaki.basho。照らせない形の文(「…」だけなど)は無いと数える)"""
    import nukigaki
    try:
        return nukigaki.basho([text], bun)
    except (nukigaki.Usage, Usage):
        return None


def pdf_nai(r, w):
    """照らす本文PDF が無い時の説明(この行の番号で開いた PDF が、鍵が合わずに外れたのか、そもそも無いのか)"""
    import honbun
    hoka = sorted({t.get("url", "") for t in honbun.kiroku(w) if t["type"] == "toru" and t["n"] == r["n"] and t.get("shurui") == "pdf"})
    if hoka:
        return ("この行の番号で開いた PDF(%s)は、置き場がこの行のリンクにも採った候補にも無いので照らしていない(別の文献か、"
                "行の番号が付け替わった時)。この行の本文なら、題名と著者がこの行の書誌と合うかを確かめてから、行の link に {\"honbun\": 開いた回} を足す(開いた回は honbun.py <作業用フォルダ> miru --n %s で見る)"
                % ("・".join(hoka), r["n"]))
    return "この行の置き場を開いた PDF が無い(本文の抜き書きなら、honbun.py <作業用フォルダ> toru --n %s --url <本文PDF> で開いてから照らす)" % r["n"]


def pdf_ni_aru(paths, bun, dai=None):
    """渡した本文PDF(その行の gyou_pdfs)のどれかに、その文が原文のまま在るか。作業用フォルダのほかの PDF(別の行の本文・
    確かめ役が控えた原典 kaime/<回>/genten/)は見ない(別の文献の PDF に同じ字が在っても例外にしないため)。
    dai を渡すと、文字にこの行の題名が在る PDF だけを見る(置き場が別の文献を指していても通さないため)"""
    import nukigaki
    for path in paths:
        try:
            pages = nukigaki.read_pages(path)
            if dai and not dai_ni_aru(dai, "".join(pages)):
                continue
            if nukigaki.basho(pages, bun) is not None:
                return True
        except (nukigaki.NoText, nukigaki.Usage, Usage, OSError):
            continue
    return False


def inyou_ari(r, w, what, sk=None, dai=None):
    """チェッカーが測れなかった引用(抜き書きか、要旨などの「」)が、その行の保存した抄録か本文PDFに原文のまま在るか。→ (在るか, 説明)。
    要旨の「」は、その文そのものを、要旨から引いた全文で照らす(英語の論文の行の要旨の日本語の「」を、行の抜き書きで代わりに通した試しがあった)"""
    if what.startswith("抜き書き「"):
        return eigo_nukigaki(r, w, sk, dai)
    t = what.strip()
    m = re.match(r"^「(.*?)(」)?$", t)
    q = yoshi_zenbun(r, m.group(1) if m else t)       # 要旨の「」は、チェッカーの一覧では括弧を外した字で出る
    if q is None:
        return False, "引用「%s」の全文が、この行の要旨に見つからない(チェッカーの一覧は90字で切れるので、切れた字だけでは照らさない)" % t[:40]
    if not q.strip():
        return False, "引用の形が読めず照らせない"
    if kugiri_mijikai(q):
        return False, "引用に%d字に満たない区切りが在る(チェッカーと同じく照らさない)" % KUGIRI_MIN
    sho, _ = shoroku(r, w, dai)
    pdfs = gyou_pdfs(r, w, sk)
    if (sho is not None and aru(sho, q) is not None) or pdf_ni_aru(pdfs, q, dai):
        return True, "引用はこの行の保存した抄録・本文PDFに原文のまま在る"
    return False, ("引用「%s」が、この行の保存した抄録にも、置き場を開いた記録(honbun.py)の本文PDF(この行の題名が在る物)にも原文のまま無い"
                   "(原文の逐語でない「」は、要旨から外すか原文の字にする)%s" % (q[:40], "" if pdfs else "。" + pdf_nai(r, w)))


def cmd_reigai(a):
    d = load(a.file)
    try:
        with open(a.kara, encoding="utf-8") as f:
            text = f.read().replace("\r\n", "\n")
    except (OSError, UnicodeDecodeError) as e:
        raise Usage("チェッカーの出力が読めない: %s" % e)
    md = os.path.join(a.w, base(a.file) + ".md")
    if not os.path.exists(md):
        raise Usage("作業用フォルダに機械用の Markdown が無い: %s" % md)
    m = re.search(r"→ 違反 (\d+)項目 / 要目視 \d+項目 / 未検査 (\d+)項目", text)
    if not m:
        raise Usage("チェッカーの出力に締めの行(→ 違反 n項目 / …)が無い。--type bunken で走らせた出力を渡す")
    ng, ok_ = [], []
    # 渡された出力が、いまの台帳の行から出た物か(古い出力を渡すと、後で書き換えた行を照らさずに通る)
    mae = [x for x in md_rireki(md) if x["t"] <= os.path.getmtime(a.kara)]
    if not mae:
        ng.append(("全体", "-", "チェッカーの出力", "この出力より前に kaku --w で台帳の Markdown を書いた記録が無い(kaku --w の後にチェッカーを打ち、その出力を渡す)"))
    elif mae[-1]["kagi"] != md_kagi(md):
        ng.append(("全体", "-", "チェッカーの出力", "この出力の後に台帳の行が変わった(古い出力では照らせない。チェッカーを打ち直し、その出力を渡す)"))
    if int(m.group(1)) or int(m.group(2)):
        ng.append(("全体", "-", "違反 %s項目・未検査 %s項目" % (m.group(1), m.group(2)), "違反と未検査は例外にしない"))
    for b in re.findall(r"^\s*▲ (B-\d+)", text, re.M):
        if b not in REIGAI_A:
            ng.append(("全体", "-", "▲ %s" % b, "段階A・B・C の外の検査不能は例外にしない"))
    blocks = {k.split()[0]: v for k, v in SHINKOKU_RE.findall(text)}
    import kensaku
    sk = sai_kagi(kensaku.load(a.w)[1])     # 本文PDF は、その行の置き場を開いた記録の物だけで照らす(gyou_pdfs)
    lrow = md_line_rows(md)
    with open(md, encoding="utf-8") as f:
        md_lines = f.read().split("\n")
    rows = {r["n"]: r for r in d.get("gyou") or []}
    sh = load_shoshi(shoshi_path(a.file))
    kotowa = set()
    for L, what, why, _ate in reigai_items(blocks.get("stage-a", "")):
        n = lrow.get(L)
        r = rows.get(n)
        kawari = kotowa_link(r, what, a.w) if r is not None and KOTOWA_RE.search(why) and kotowa_row(r) else None
        if kawari:
            kotowa.add(n)
            shogen = re.search(r"HTTP 40[13]", why)
            ok_.append(("段階A", n, what, ("出版社に機械の取得を断られた(%s)" % why.split("(")[0] if shogen else
                                         "出版社のページに機械が証明書の誤りでつながらない(%s)" % why[:60]) + "。" + kawari))
        elif r is not None and KOTOWA_RE.search(why) and kotowa_row(r):
            ng.append(("段階A", n, what, why + "(行の DOI のリンクでなく、honbun.py でも開けていない置き場。開けない置き場なら link から外す)"))
        else:
            ng.append(("段階A", n, what, why + ("" if r is None or not KOTOWA_RE.search(why) else
                                              "(備考に断られた・証明書の誤りと書いていないか DOI が無い)")))
    for L, what, why, _ate in reigai_items(blocks.get("stage-b", "")):
        ng.append(("段階B", lrow.get(L), what, why))
    for L, what, why, ate in reigai_items(blocks.get("stage-c", "")):
        n = lrow.get(L)
        r = rows.get(n)
        dai = (sh.get(n) or {}).get("dai")
        if r is None:
            ng.append(("段階C", n, what, why))
        elif not dai and (n in kotowa or r.get("gengo") == "英" or TAISHO_NASHI in why):
            # 代わりの照らしは、抄録・本文PDF がこの行の文献かを題名で見る。題名が無ければ照らせない
            ng.append(("段階C", n, what, why + "。書誌の項目ファイルにこの行の題名(dai)が無く、代わりの照らしの抄録・本文PDF がこの行の文献か確かめられない"))
        elif n in kotowa and "取れていない" in why:
            # 断られた行の抜き書きも、作業用フォルダに保存した抄録か本文PDFに原文のまま在るかを照らす(チェッカーの代わり)
            found, setsumei = inyou_ari(r, a.w, what, sk, dai)
            (ok_ if found else ng).append(("段階C", n, what, ("出版社のページを機械が取れない行(断られた・証明書の誤り)。" if found else why + "。") + setsumei))
        elif r.get("gengo") == "英" and "散文を渡していない" in why:
            found, setsumei = inyou_ari(r, a.w, what, sk, dai)
            (ok_ if found else ng).append(("段階C", n, what, ("チェッカーが英語の本文を読めない。" if found else why + "。") + setsumei))
        elif TAISHO_NASHI in why and isinstance(L, int) and 0 < L <= len(md_lines) and "『" in md_lines[L - 1]:
            # 書誌欄の題名が『』の行(図書・報告書・白書)は、チェッカーが対照を置けないので、その行の本文PDF と抄録で照らす(D81)
            found, setsumei = inyou_ari(r, a.w, what, sk, dai)
            (ok_ if found else ng).append(("段階C", n, what, ("書誌欄の題名が『』で、チェッカーが対照を置けない。" if found else why + "。") + setsumei))
        else:
            ng.append(("段階C", n, what, why))
    if not ok_ and not ng:
        p("測れなかった物は無い(この出力なら終了コード 3 ではない)")
        return 0
    if ng:
        p("✕ 納めない。例外にできない物が %d件ある(納品のチャットに並べてユーザーの判断を待つ):" % len(ng))
        for s, n, what, why in ng:
            p("  - %s %s %s —— %s" % (s, "#%s" % n if isinstance(n, int) else "(行が分からない)" if n is None else "", what, why))
        if ok_:
            p("例外にできた物 %d件(上と一緒に並べる):" % len(ok_))
            for s, n, what, why in ok_:
                p("  - %s #%s %s —— %s" % (s, n, what, why))
        return 1
    p("納めてよい(測れなかった物 %d件は、どれも例外)。納品のチャットに次の一覧を1件も落とさずに出す:" % len(ok_))
    for s, n, what, why in ok_:
        p("  - %s #%s %s —— %s" % (s, n, what, why))
    return 0


# ---- 抜き出して見る ----

def cmd_miru(a):
    d = load(a.file)
    sh = load_shoshi(shoshi_path(a.file))
    want = {int(x) for x in re.split(r"[,、・\s]+", a.n) if x.strip()} if a.n else None
    rows = [r for r in d["gyou"] + d["toukei"] if want is None or r["n"] in want]
    if want:
        miss = sorted(want - {r["n"] for r in rows})
        if miss:
            raise Stop("台帳に無い番号: " + "・".join("#%d" % n for n in miss))
    if a.kata == "json":
        out = []
        for r in rows:
            o = {k: r[k] for k in ("n", "shubetsu", "nyushu", "seidoku", "ronten", "access", "link") if k in r}
            o["shoshi_bun"] = cell(r, "shoshi", sh)
            if r["n"] in sh:
                o["shoshi"] = {k: v for k, v in sh[r["n"]].items() if k != "n"}
            if a.yoshi:
                o["yoshi"], o["nukigaki"] = r.get("yoshi"), r.get("nukigaki")
            out.append(o)
        p(json.dumps(out, ensure_ascii=False, indent=1))
        return 0
    if want is None:
        at = d["atama"]
        p("文献台帳: %s(%d件・実行日 %s)" % (at.get("theme", ""), len(rows), at.get("jikkobi", "")))
        p("適合の基準: %s" % at.get("kijun", ""))
        for x in at.get("ronten") or []:
            p("論点%s%s: %s" % (x["no"], "(%s)" % x["shurui"] if x.get("shurui") else "", x.get("bun", "")))
        for c in d.get("chui") or []:
            p("読み方の注意: %s" % c)
        if d.get("totsugo"):
            p("書誌突合: %s" % d["totsugo"])
        p("抜き書きの場所に「画像から書き写し」とある行は、画像だけの PDF から書き写した文で、チェッカーは原典と照らしていない")
        p("一覧(#番号 書誌 | 種別 | 入手状況 | 精読 | 論点 | リンク)。要旨と抜き書きは --n 番号 --yoshi で読む:")
    for r in rows:
        p("#%d %s | %s | %s | %s | 論点%s | %s" % (r["n"], cell(r, "shoshi", sh), cell_shubetsu(r), r.get("nyushu", ""),
                                               r.get("seidoku", "—"), "・".join(r.get("ronten") or []) or "—", cell_link(r)))
        if a.yoshi:
            p("   要旨: " + cell_yoshi(r).replace("<br>", " "))
            p("   抜き書き: " + cell_nukigaki(r))
    return 0


# ---- 古い Markdown の台帳を写し直す ----

HEAD_RE = re.compile(r"^- (.+?)[:：] ?(.*)$")
RONTEN_RE = re.compile(r"^論点(\d+)(?:\((.+)\))?$")


def split_row(line):
    s = line.strip()[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def parse_row(cols, cells):
    raw = dict(zip(cols, cells))
    known = {na: k for na, k in COLS + TCOLS}
    r = {"n": int(raw["#"])}
    for na, v in raw.items():
        k = known.get(na)
        if k in (None,):
            r.setdefault("hoka", {})[na] = v
        elif k not in ("n",):
            r[k + "_bun"] = v
    # 分けられる欄は分け、分けた物から同じ文が作れる時だけ分けた形にする(作れなければ文のまま持つ)
    for k, fn, cellfn in (("shubetsu", split_shubetsu, cell_shubetsu), ("link", split_link, cell_link),
                          ("yoshi", split_yoshi, cell_yoshi), ("nukigaki", split_nukigaki, cell_nukigaki),
                          ("chosa_nengetsu", split_nengetsu, cell_toukei_nengetsu)):
        bun = r.get(k + "_bun")
        if bun is None:
            continue
        got = fn(bun)
        if got is not None:
            trial = dict(got)
            if k == "yoshi":
                trial = {"yoshi": got}
            if cellfn(trial) == bun:
                r.pop(k + "_bun")
                r.update(trial)
                continue
        if k == "yoshi":
            r.pop("yoshi_bun")
            r["yoshi"] = {"bun": bun}
    for k in ("keiro", "nyushu", "seidoku", "yoto", "access", "gengo", "biko", "statinfid", "filekind"):
        if r.get(k + "_bun") is not None:
            r[k] = r.pop(k + "_bun")
    return r


def split_shubetsu(s):
    for v in SHUBETSU:
        if s == v:
            return {"shubetsu": v}
        if s.startswith(v + "(") and s.endswith(")"):
            return {"shubetsu": v, "shubetsu_konkyo": s[len(v) + 1:-1]}
    return None


def split_link(s):
    urls = re.findall(r"https?://[^\s)（）]+", s)
    if not urls:
        return None
    ls = [{"url": urls[0]}]
    for u in urls[1:]:
        before = s[:s.find(u)]
        m = re.search(r"([^\s(・]+?)[:：]\s*$", before)
        ls.append({"url": u, "na": m.group(1)} if m else {"url": u})
    return {"link": ls}


def split_yoshi(s):
    parts = s.split("<br>・")
    m = re.match(r"^\((.*?)\)([^()]*)$", parts[0])
    if not m:
        return None
    rest = m.group(2)
    if rest and not rest.endswith("。"):
        return None
    return {"han": m.group(1), "shurui": rest[:-1] if rest else "", "kajo": parts[1:]}


def split_nukigaki(s):
    m = re.fullmatch(r"なし\((.*)\)", s)
    if m:
        return {"nukigaki": [], "nukigaki_nashi": m.group(1)}
    body, basho = tail_paren(s)
    if basho is not None and body.startswith("「") and body.endswith("」"):
        return {"nukigaki": [{"bun": body[1:-1], "basho": basho}]}
    return None


def split_nengetsu(s):
    m = re.fullmatch(r"調査年月: (.+?)\(e-Stat結果一覧『調査年月』欄\)", s)
    return {"chosa_nengetsu": m.group(1)} if m else None


def cmd_utsusu(a):
    try:
        with open(a.md_file, encoding="utf-8") as f:
            text = f.read()
    except (OSError, UnicodeDecodeError) as e:
        raise Usage("台帳が読めない: %s (%s)" % (a.md_file, e))
    d = empty()
    d["utsushi"] = {"moto": os.path.basename(a.md_file), "hi": ts()[:10]}
    at = d["atama"]
    rev = {na: k for k, na in ATAMA + ATAMA_ATO}
    sec, cols, blk, fence = None, None, None, None
    tansaku = {"mae": "", "bloku": []}
    for ln in text.replace("\r\n", "\n").split("\n"):
        if ln.startswith("この台帳は run-uradori"):
            d["hikitsugi"] = ln.strip()
            continue
        if fence is not None:
            if ln.startswith("```"):
                d.setdefault("shinkoku", {})[fence[0]] = "\n".join(fence[1])
                fence = None
            else:
                fence[1].append(ln)
            continue
        if ln.startswith("```stage-"):
            fence = (ln[3:].strip(), [])
            continue
        if ln.startswith("# 文献台帳"):
            at["theme"] = re.split(r"[:：]", ln, 1)[1].strip() if re.search(r"[:：]", ln) else ln[2:]
            continue
        if ln.startswith("## "):
            sec, cols, blk = ln[3:].strip(), None, None
            if not (sec.startswith(("台帳本体", "統計原表", "機械照合", "選別の帳尻", "探索記録", "入手ルート"))):
                d.setdefault("sonota_setsu", []).append({"midashi": sec, "gyou": []})
            continue
        if sec is None:
            m = HEAD_RE.match(ln)
            if m:
                k, v = m.group(1).strip(), m.group(2)
                rm = RONTEN_RE.match(k)
                if rm:
                    at["ronten"].append({"no": rm.group(1), "shurui": rm.group(2) or "", "bun": v})
                elif k in rev:
                    at[rev[k]] = v
                else:
                    at.setdefault("hoka", []).append([k, v])
            elif ln.startswith("**宣言との照合**"):
                d["shogou"] = re.split(r"[:：]", ln, 1)[1].strip()
            elif ln.startswith("**読み方の注意**"):
                d.setdefault("chui", []).append(re.split(r"[:：]", ln, 1)[1].strip())
            elif ln.strip() and not ln.startswith(("**凡例", "# ")):
                d.setdefault("atama_bun", []).append(ln)
            continue
        if sec.startswith(("台帳本体", "統計原表")):
            if ln.startswith("|"):
                cells = split_row(ln)
                if cols is None or "#" in cells and not re.fullmatch(r"\d+", cells[0]):
                    cols = cells
                    if sec.startswith("台帳本体"):
                        d["retsu"] = cells
                    continue
                if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c) or not re.fullmatch(r"\d+", cells[0]):
                    continue
                r = parse_row(cols, cells)
                (d["toukei"] if sec.startswith("統計原表") else d["gyou"]).append(r)
            elif ln.startswith("**書誌突合"):
                d["totsugo"] = re.split(r"[:：]", ln, 1)[1].strip()
            continue
        if sec.startswith("選別の帳尻"):
            if ln.startswith("- "):
                d.setdefault("chojiri", {"toki": "", "gyou": []})["gyou"].append(ln)
            elif "kensaku.py chojiri" in ln:
                m = re.search(r"chojiri・([^)]*)\)", ln)
                d.setdefault("chojiri", {"toki": "", "gyou": []})["toki"] = m.group(1) if m else ""
            continue
        if sec.startswith("探索記録"):
            if ln.startswith("### "):
                blk = {"midashi": ln[4:].strip(), "gyou": []}
                tansaku["bloku"].append(blk)
            elif blk is not None:
                if ln.strip() and ln.strip() != HIKITSUGI:
                    blk["gyou"].append(ln)
            elif ln.strip() and blk is None and ln.strip() != HIKITSUGI:
                tansaku["mae"] = (tansaku["mae"] + " " + ln.strip()).strip()
            continue
        if sec.startswith("入手ルート"):
            if ln.startswith("- "):
                d.setdefault("nyushu_route", []).append(ln[2:])
            continue
        if d.get("sonota_setsu") and sec == d["sonota_setsu"][-1]["midashi"] and ln.strip() and ln.strip() != HIKITSUGI:
            d["sonota_setsu"][-1]["gyou"].append(ln)
    d["tansaku"] = tansaku
    by_n = {r["n"]: r for r in d["gyou"] + d["toukei"]}
    for ln in (d.get("chojiri") or {}).get("gyou") or []:
        m = re.match(r"^- 論点(\d+)", ln)
        t = re.search(r"採った \d+件\(([^)]*)\)", ln)
        if m and t:
            for x in re.findall(r"#(\d+)", t.group(1)):
                if int(x) in by_n and m.group(1) not in by_n[int(x)].setdefault("ronten", []):
                    by_n[int(x)]["ronten"].append(m.group(1))
    out = a.file
    save(out, d)
    p("写した: %s(文献 %d行・統計原表 %d行・論点 %d個・探索記録の塊 %d・申告 %s)"
      % (out, len(d["gyou"]), len(d["toukei"]), len(at["ronten"]), len(tansaku["bloku"]), "・".join(sorted(d.get("shinkoku") or {})) or "なし"))
    return 0


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="文献台帳の JSON(正本)と HTML・機械用の Markdown")
    ap.add_argument("file", help="台帳の JSON(<台帳名>.json)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("ireru")
    s.add_argument("--json-file", required=True)
    s = sub.add_parser("shinkoku")
    s.add_argument("--kara", required=True)
    sub.add_parser("kensa")
    s = sub.add_parser("kaku")
    s.add_argument("--w")
    s.add_argument("--md")
    s.add_argument("--html")
    s = sub.add_parser("miru")
    s.add_argument("--n")
    s.add_argument("--kata", choices=("text", "json"), default="text")
    s.add_argument("--yoshi", action="store_true")
    s = sub.add_parser("utsusu")
    s.add_argument("md_file")
    s = sub.add_parser("reigai")
    s.add_argument("--kara", required=True)
    s.add_argument("--w", required=True)
    a = ap.parse_args(argv)
    fn = {"ireru": cmd_ireru, "shinkoku": cmd_shinkoku, "kensa": cmd_kensa, "kaku": cmd_kaku, "miru": cmd_miru,
          "utsusu": cmd_utsusu, "reigai": cmd_reigai}[a.cmd]
    try:
        return fn(a)
    except Stop as e:
        p("✕ " + str(e))
        return 1
    except Usage as e:
        p("使い方の誤り: " + str(e))
        return 2


if __name__ == "__main__":
    sys.exit(main())
