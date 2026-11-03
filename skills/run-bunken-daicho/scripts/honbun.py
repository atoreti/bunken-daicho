# -*- coding: utf-8 -*-
# 部品の版(uv run で走らせると、uv がこの版を、使う人の PC の Python を変えずに用意する。python で打っても動く)
# /// script
# requires-python = ">=3.10"
# dependencies = ["pymupdf==1.27.2.3"]
# ///
"""本文の置き場を開いて保存し、開いた記録を残す(run-bunken-daicho の工程3「本文を読む」)。標準ライブラリ+PyMuPDF。

無料で読める置き場(機関リポジトリ・arXiv・J-STAGE の本文PDF など)がある文献を、開かずに抄録で済ませた台帳が続いた
(読み切れなかった訳に「時間切れ」と書けば通ったので、置き場を1つも開かずに納めた試しもあった。課題 ch-3ni)。そこで、
開いたかどうかと、開けた本文の頁の数・文字の取れない頁をこのスクリプトが記録に残し、`daicho.py … kaku --w` がその記録と
台帳の行を照らす(開いた記録の無い行・開けた本文を読み切っていない行は、台帳を作らない)。

置き場: <作業用フォルダ>/honbun/<行>-<回>.pdf か .html(取った中身)・<作業用フォルダ>/honbun/<行>-<回>-p<頁>.png(頁の画像)・
<作業用フォルダ>/honbun.jsonl(記録。スクリプトが後ろに足すだけで書く)。

使い方:
  uv run honbun.py <作業用フォルダ> toru --n 行 --url <置き場の URL>
      置き場を開いて保存する。PDF なら頁の数と、文字の取れない頁(画像だけの頁・表や図が文字にならず崩れた頁)を出す。
      開けなかった時(HTTP 403・503・証明書の誤り・接続を切られた)も1行残す。J-STAGE は間を空け、この回に切られた後は開かない
  uv run honbun.py <作業用フォルダ> gazo --n 行 [--k 回] --peeji 3,5
      その行で保存した PDF(--k を省くと最後に開いた物)の頁を画像(PNG)にして、置き場を出す。画像は Read で開いて読む
      (画像にした頁が、どの回に開いた PDF の物かと一緒に記録に残る)
  uv run honbun.py <作業用フォルダ> miru [--n 行]
      記録を行ごとにまとめて出す
終わりの値: 0=できた / 1=記録が壊れている・決まりの外 / 2=使い方の誤り / 3=開けなかった・頁を画像にできなかった
"""
import argparse
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from kyotsu import Stop, Usage, append_log, read_log, ts  # noqa: E402
import kensaku  # noqa: E402
import nukigaki  # noqa: E402

KIND = "bunken-honbun"
LOG = "honbun.jsonl"
DIR = "honbun"
TIMEOUT = 60
AIDA = 2                 # J-STAGE の外の置き場にも、続けて開く時は2秒あける
KUZURE_MOJI = 100        # そろえた字が100字に満たない頁を「文字の取れない頁」に数える(画像だけの頁・崩れた頁)
HONBUN_MOJI = 2000       # PDF でない中身は、そろえた字が2000字に満たなければ本文ではない(図・案内のページ)


def p(*a):
    print(*a)


def fetch_bytes(url, timeout):
    """→ (中身の bytes or None, 状態, 説明, Content-Type)。状態は ok・kirareta・shippai"""
    req = urllib.request.Request(url, headers={"User-Agent": kensaku.UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return res.read(), "ok", "", res.headers.get("Content-Type", "")
    except urllib.error.HTTPError as e:
        return None, "shippai", "HTTP %d" % e.code, ""
    except urllib.error.URLError as e:
        r = e.reason
        if isinstance(r, (ConnectionResetError, ConnectionAbortedError)):
            return None, "kirareta", "接続を切られた(%s)" % r.__class__.__name__, ""
        return None, "shippai", "つながらない(%s)" % str(r)[:120], ""
    except (ConnectionResetError, ConnectionAbortedError) as e:
        return None, "kirareta", "接続を切られた(%s)" % e.__class__.__name__, ""
    except Exception as e:  # noqa: BLE001  失敗も1行残すため
        return None, "shippai", "%s: %s" % (e.__class__.__name__, str(e)[:120]), ""


def yomu_peeji(path):
    """保存した PDF の頁ごとの文字(試験で差し替える)"""
    return nukigaki.read_pages(path)


def kiroku(w):
    return read_log(os.path.join(w, LOG), KIND)


def by_n(rows):
    """記録を行ごとに。→ {行: {"toru": [...], "gazo": set(頁), "gazo_k": {開いた回 or None: set(頁)}}}"""
    out = {}
    for r in rows:
        x = out.setdefault(r["n"], {"toru": [], "gazo": set(), "gazo_k": {}})
        if r["type"] == "toru":
            x["toru"].append(r)
        elif r["type"] == "gazo":
            x["gazo"] |= set(r.get("peeji") or [])
            x["gazo_k"].setdefault(r.get("k"), set()).update(r.get("peeji") or [])
    return out


def kagi(url):
    """URL から、どの文献の置き場かを名指す鍵(doi:・jstage:・crid:・arxiv:・pmc:・hdl:・url:)。
    開いた記録が台帳のその行の文献のものかを照らすのに使う(行の番号が付け替わり、別の文献を開いた記録で
    「本文を読んだ」が通った試しがあった。2026-11-02 の配る束の試し)。jstage:・crid:・doi:・arxiv: は候補の鍵(kensaku.keys_of)と同じ形"""
    u = urllib.parse.unquote((url or "").strip())
    if not u:
        return set()
    m = re.match(r"(?i)^https?://([^/?#]+)", u)
    host = re.sub(r"^www\.", "", m.group(1).lower()) if m else ""
    base = re.split(r"[?#]", u, 1)[0]
    query = u.split("#", 1)[0].partition("?")[2]
    # url: は scheme・www.・末尾の /・# と、中身の変わらない引数(download・version・sequence)を外してそろえる
    q = "&".join(x for x in query.split("&") if x and x.split("=", 1)[0].lower() not in ("download", "version", "sequence"))
    path = re.sub(r"(?i)^https?://[^/?#]+", "", base).rstrip("/")
    out = {"url:" + (host + path + ("?" + q if q else "")).lower()}
    # DOI は符号を戻した形から、< > も含めて取る(古い Wiley の SICI 形の DOI は < > を持つ。kensaku.doi_of は < で切るので、
    # 同じ号の別の論文と同じ鍵になった)
    doi = (re.search(r"(10\.\d{4,9}/[^\s\"|]+)", base) or re.search(r"(10\.\d{4,9}/[^&\s#]+)", query) or [None, ""])[1]
    doi = re.sub(r"(\.full\.pdf|\.full|\.pdf|/(?:full|abstract|pdf|fulltext|epdf|pdfdirect))+$", "", doi.lower().rstrip(".,;)/"))
    if doi.startswith("10.1101/"):
        doi = re.sub(r"v\d+$", "", doi)          # bioRxiv・medRxiv の版
    if doi:
        out.add("doi:" + doi)
        if doi.startswith("10.48550/arxiv."):
            out.add("arxiv:" + doi[len("10.48550/arxiv."):])
    if kensaku.crid_of(u):
        out.add("crid:" + kensaku.crid_of(u))
    for pre, pat in (("jstage:", r"jstage\.jst\.go\.jp/article/([^?#]+?)/_(?:article|pdf|html)"),
                     ("arxiv:", r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5}|[a-z\-]+(?:\.[a-z]{2})?/\d{7})"),
                     ("pmc:", r"\b(PMC\d+)"), ("pmc:pmc", r"/pmc/articles/(\d+)"),
                     ("ndlpid:", r"dl\.ndl\.go\.jp/(?:info:ndljp/)?pid/(\d+)"), ("ndlpid:", r"dl\.ndl\.go\.jp/.*?digidepo_(\d+)"),
                     ("pii:", r"/pii/(S?[0-9X]{10,})")):
        m = re.search(pat, u, re.I)
        if m:
            out.add(pre + m.group(1).lower())
    m = re.search(r"(?:hdl\.handle\.net/|/bitstream/|/handle/)(\d+(?:\.\d+)*/\d+)", u)
    if m:
        # 123456789 は番号を登録していない DSpace の既定の番号で、ほかのリポジトリとぶつかるので、置き場の名前と組にする
        out.add("hdl:" + (host + "/" if m.group(1).startswith("123456789/") else "") + m.group(1))
    m = re.search(r"/records?/(\d+)(?:[/?#]|$)", u) or re.search(r"[?&]item_id=(\d+)", u)
    if m:
        out.add("rec:%s/%s" % (host, m.group(1)))   # 機関リポジトリ(WEKO)などの同じ置き場の記録の番号
    return out


def cmd_toru(a):
    w = a.w
    if not a.url.startswith(("http://", "https://")):
        raise Usage("--url は http(s) の URL")
    kensaku.tsukawanai_url(a.url)    # 使う人が設定 BUNKEN_DB で外したデータベースのサイト(J-STAGE の本文の PDF など)は開かない(D84)
    js_url = "jstage.jst.go.jp" in a.url
    with kensaku.kakikomi(w):
        have = kiroku(w)
    k = 1 + sum(1 for r in have if r["type"] == "toru" and r["n"] == a.n)
    row = {"type": "toru", "n": a.n, "k": k, "url": a.url, "at": ts()}
    js = kensaku.jstage_state(w) if js_url else None
    if js is not None and js.get("kirareta"):
        row.update(jotai="yameta", why="この回は %s に J-STAGE に接続を切られたので開いていない" % js["kirareta"])
    else:
        lock = "jstage" if js_url else "honbun"
        with kensaku.junban(lock) as st:
            last = st.get("saigo")
            ma = kensaku.JSTAGE_MA if js_url else AIDA
            if isinstance(last, (int, float)) and ma - (time.time() - last) > 0:
                time.sleep(ma - (time.time() - last))
            body, jotai, why, ctype = fetch_bytes(a.url, TIMEOUT)
            st["saigo"] = time.time()
        row.update(jotai=jotai, why=why)
        if js is not None:
            js["saigo"] = row["at"]
            if jotai == "kirareta":
                js["kirareta"] = row["at"]
            kensaku.jstage_save(w, js)
        if jotai == "ok":
            pdf = body[:5] == b"%PDF-"
            os.makedirs(os.path.join(w, DIR), exist_ok=True)
            path = os.path.join(w, DIR, "%d-%d.%s" % (a.n, k, "pdf" if pdf else "html"))
            with open(path, "wb") as f:
                f.write(body)
            row.update(file=os.path.relpath(path, w), shurui="pdf" if pdf else "html", ctype=ctype[:80], baito=len(body))
            if pdf:
                try:
                    pages = yomu_peeji(path)
                    row.update(peeji=len(pages), kuzure=[i + 1 for i, t in enumerate(pages) if len(nukigaki.norm(t)) < KUZURE_MOJI])
                except Exception as e:  # noqa: BLE001  壊れた PDF・パスワード付きの PDF(頁の文字を取る時に ValueError)・道具が無い
                    row.update(peeji=0, kuzure=[], yomenai=(str(e) or e.__class__.__name__)[:120])
            else:
                text = re.sub(r"<script.*?</script>|<style.*?</style>|<[^>]+>", " ", body.decode("utf-8", "replace"), flags=re.S)
                row.update(moji=len(nukigaki.norm(text)))
    with kensaku.kakikomi(w):
        append_log(os.path.join(w, LOG), KIND, [row])
    if row["jotai"] != "ok":
        p("#%d 開けなかった(%s): %s。記録に1行残した。台帳の行の yomikiranai は「開けなかった(%s)」か「出版社に断られた(%s)」で始める"
          % (a.n, row.get("why") or row["jotai"], a.url, row.get("why") or row["jotai"], row.get("why") or row["jotai"]))
        return 3
    if row["shurui"] == "pdf":
        ku = row.get("kuzure") or []
        p("#%d 開けた: PDF %d頁。保存= %s" % (a.n, row.get("peeji", 0), os.path.join(w, row["file"])))
        if row.get("yomenai"):
            p("  ★PDF を読めない(%s)。PyMuPDF が無いなら uv run で走らせ直す(uv が頭書きの版の PyMuPDF を用意し、使う人の PC の Python は変えない。uv が無ければ、ユーザーに uv を入れてもらう。claude.ai の作業場には PyMuPDF が無いので、そこでは pip install pymupdf で入れる)。中身が壊れている・パスワードが"
              "掛かっている時は、ほかの置き場を開くか、行の yomikiranai を「開けなかった(PDF が壊れている など)」で始める" % row["yomenai"])
        elif ku:
            p("  ★文字の取れない頁: %s。honbun.py … gazo --n %d --k %d --peeji %s で画像にして、Read で見て読む(見ないと本文精読済みにできない)"
              % ("・".join(map(str, ku)), a.n, k, ",".join(map(str, ku))))
        p("  本文を全部読んでから要旨を書く(読み切れない訳にできるのは 200頁以上・画像でも読めない頁だけ)")
    else:
        p("#%d 開けた: PDF でない中身(%s・そろえた字 %d字)。保存= %s%s" % (
            a.n, row.get("ctype") or "?", row.get("moji", 0), os.path.join(w, row["file"]),
            "。本文ではなさそう(図か案内のページ)。本文PDF の URL があれば、それを開く" if row.get("moji", 0) < HONBUN_MOJI else ""))
    return 0


def cmd_gazo(a):
    w = a.w
    try:
        want = sorted({int(x) for x in a.peeji.split(",") if x.strip()})
    except ValueError:
        raise Usage("--peeji は 3,5 のような頁の数の並び")
    oks = [r for r in kiroku(w) if r["type"] == "toru" and r["n"] == a.n and r.get("jotai") == "ok" and r.get("shurui") == "pdf"]
    if not oks:
        raise Usage("#%d の PDF を開いた記録が無い(先に toru を打つ)" % a.n)
    if a.k is not None:
        oks = [r for r in oks if r.get("k") == a.k]
        if not oks:
            raise Usage("#%d の %d回目に開いた PDF の記録が無い(miru --n %d で回を見る)" % (a.n, a.k, a.n))
    src = os.path.join(w, oks[-1]["file"])
    try:
        import pymupdf as fitz
    except ImportError:
        try:
            import fitz
        except ImportError:
            p("頁を画像にする道具(PyMuPDF)が無い。uv run で走らせ直す(uv が頭書きの版の PyMuPDF を用意し、使う人の PC の Python は変えない。uv が無ければ、ユーザーに uv を入れてもらう。claude.ai の作業場には PyMuPDF が無いので、そこでは pip install pymupdf で入れる)")
            return 3
    out = []
    try:
        doc = fitz.open(src)
        for n in want:
            if not 1 <= n <= len(doc):
                raise Usage("#%d の PDF は %d頁まで(%d頁は無い)" % (a.n, len(doc), n))
            path = os.path.join(w, DIR, "%d-%d-p%d.png" % (a.n, oks[-1].get("k") or 0, n))
            doc[n - 1].get_pixmap(dpi=150).save(path)
            out.append(path)
    except Usage:
        raise
    except Exception as e:  # noqa: BLE001  保存した PDF が無い・壊れている・パスワードが掛かっている
        p("#%d の %s回目に開いた PDF(%s)を画像にできない(%s: %s)。toru で開き直すか、ほかの置き場を開く"
          % (a.n, oks[-1].get("k"), src, e.__class__.__name__, str(e)[:80]))
        return 3
    with kensaku.kakikomi(w):
        append_log(os.path.join(w, LOG), KIND, [{"type": "gazo", "n": a.n, "k": oks[-1].get("k"), "peeji": want, "at": ts()}])
    p("#%d の %s頁(%d回目に開いた PDF)を画像にした。Read で1枚ずつ開いて読む:" % (a.n, "・".join(map(str, want)), oks[-1].get("k") or 0))
    for x in out:
        p("  " + x)
    return 0


def cmd_miru(a):
    for n, x in sorted(by_n(kiroku(a.w)).items()):
        if a.n and n != a.n:
            continue
        for r in x["toru"]:
            p("#%d %s回目 %s %s %s" % (n, r.get("k"), r["url"], r["jotai"], "PDF %s頁・崩れ %s" % (r.get("peeji"), r.get("kuzure")) if r.get("shurui") == "pdf"
                                else ("中身 %s字" % r.get("moji") if r.get("jotai") == "ok" else r.get("why", ""))))
        if x["gazo"]:
            p("#%d 画像にした頁: %s" % (n, "・".join(map(str, sorted(x["gazo"])))))
    return 0


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="本文の置き場を開き、開いた記録を残す")
    ap.add_argument("w", help="作業用フォルダ")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("toru")
    s.add_argument("--n", type=int, required=True)
    s.add_argument("--url", required=True)
    s = sub.add_parser("gazo")
    s.add_argument("--n", type=int, required=True)
    s.add_argument("--k", type=int, help="何回目に開いた PDF か(省くと、その行で最後に開いた PDF)")
    s.add_argument("--peeji", required=True)
    s = sub.add_parser("miru")
    s.add_argument("--n", type=int)
    a = ap.parse_args(argv)
    fn = {"toru": cmd_toru, "gazo": cmd_gazo, "miru": cmd_miru}[a.cmd]
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
