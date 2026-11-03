# -*- coding: utf-8 -*-
# 部品の版(uv run で走らせると、uv がこの版を、使う人の PC の Python を変えずに用意する。python で打っても動く)
# /// script
# requires-python = ">=3.10"
# dependencies = ["pymupdf==1.27.2.3"]
# ///
"""抜き書きの欄の場所を、本文から機械で出す(run-bunken-daicho の工程3「本文を読む」)。標準ライブラリ+PyMuPDF。

抜き書き(要旨の元にした原文の1〜2文)が、本文PDFのどの頁にそのまま在るかを探し、台帳に書く場所(「本文 p.6」)を出す。
頁を目で数えて書くと書き間違えるので、ここで出した頁を写す(決定= claude-harness の docs/user-decisions.md の D64)。
見つからなければ、その抜き書きは原文のままではない(写し間違い・言い換え)。台帳に書く前に直す。

使い方:
  uv run nukigaki.py basho <本文PDF か .txt> "<抜き書き>" [--hajime 48] [--dai "題名の一部"]
      --hajime  書誌の頁の最初(論文が48頁から始まるなら 48)。PDF の1枚目を48頁と数えて、刷られた頁を出す
      --dai     書誌欄の題名の一部。本文の文字に題名が出なければ、文字化けの疑いとして知らせる
      .txt は、頁の区切りを改ページの字(\\f)で表したものとして読む

照らし方(チェッカーの段階C の抜き書きの照合と同じ):
  - 空白・改行を落とし、全角半角(NFKC)とダッシュの類をそろえてから探す
  - 抜き書きを「…」で区切ると、区切りごとに順に探す(2段組の PDF で左右の段が混ざる所・途中を省いた所)
  - 数で始まる区切りは、原文で負号(−)の直後にある所には当てない(負号を落として写すと見つからない。負号ごと写す)
終わりの値: 0=見つかった / 1=見つからない / 2=使い方・ファイルの誤り / 3=本文を文字にできない
"""
import argparse
import os
import re
import sys
import unicodedata

DASHES = "‐‑‒–—―−－ーｰ"
MINUS = "-"                       # そろえた後の負号(ダッシュの類はすべてこの字になる)
WORD_CHAR = re.compile(r"[A-Za-z0-9%°]")
SIGNED_NUMBER = re.compile(r"[.]?\d")
FOOTER = re.compile(r"^\s*[-‐‑‒–—―−－]?\s*(\d{1,4})\s*[-‐‑‒–—―−－]?\s*$")


class Usage(Exception):
    """使い方・ファイルの誤り(終わりの値 2)"""


class NoText(Exception):
    """本文を文字にできない(終わりの値 3)"""


def norm(s):
    """照合のためにそろえる。空白を落とし、全角半角とダッシュの類をそろえる。字そのものは変えない"""
    t = unicodedata.normalize("NFKC", s or "")
    t = re.sub(r"[\s　]+", "", t)
    return re.sub("[" + DASHES + "]", MINUS, t)


def read_pages(path):
    """本文を頁ごとの文字のリストにする"""
    if not os.path.isfile(path):
        raise Usage("ファイルが無い: %s" % path)
    if path.lower().endswith(".txt"):
        return open(path, encoding="utf-8", errors="replace").read().split("\f")
    try:
        import pymupdf as fitz
    except ImportError:
        try:
            import fitz
        except ImportError as e:
            raise NoText("PDF を読む道具(PyMuPDF)が無い(%s)。uv run で走らせ直す(uv が頭書きの版の PyMuPDF を用意し、使う人の PC の Python は変えない。uv が無ければ、ユーザーに uv を入れてもらう。claude.ai の作業場には PyMuPDF が無いので、そこでは pip install pymupdf で入れる)" % e.__class__.__name__)
    try:
        doc = fitz.open(path)
    except Exception as e:  # noqa: BLE001  壊れた PDF・PDF でないファイル
        raise NoText("PDF を開けなかった(%s)" % e.__class__.__name__)
    return [p.get_text() for p in doc]


def after_minus(text, at):
    """text の at の直前が負号か。英数字の直後のハイフンは語の一部(COVID-19・18-65)なので負号にしない"""
    if at <= 0 or text[at - 1] != MINUS:
        return False
    return not (at >= 2 and WORD_CHAR.fullmatch(text[at - 2]))


def find_pieces(pieces, text):
    """区切りがどれも前の区切りより後ろに順に在れば、最初の区切りの始まりと最後の区切りの終わりを返す。無ければ None"""
    pos, first = 0, None
    for piece in pieces:
        at = text.find(piece, pos)
        while at >= 0 and SIGNED_NUMBER.match(piece) and after_minus(text, at):
            at = text.find(piece, at + 1)
        if at < 0:
            return None
        if first is None:
            first = at
        pos = at + len(piece)
    return first, pos


def footer_number(page_text):
    """頁の上か下の数だけの行(「- 6 -」「49」)から、刷られた頁の数を拾う。拾えなければ None"""
    lines = [l for l in page_text.splitlines() if l.strip()]
    for l in lines[-3:] + lines[:3]:
        m = FOOTER.match(l)
        if m:
            return int(m.group(1))
    return None


def basho(pages, quote, hajime=None):
    """抜き書きの場所を探す。→ dict(見つからなければ None)"""
    pieces = [norm(p) for p in quote.split("…") if norm(p)]
    if not pieces:
        raise Usage("抜き書きが空")
    normed = [norm(p) for p in pages]
    joined, starts = "", []
    for t in normed:
        starts.append(len(joined))
        joined += t
    hit = find_pieces(pieces, joined)
    if hit is None:
        return None

    def page_of(off):
        i = 0
        while i + 1 < len(starts) and starts[i + 1] <= off:
            i += 1
        return i

    p0, p1 = page_of(hit[0]), page_of(max(hit[0], hit[1] - 1))
    out = {"pdf": (p0 + 1, p1 + 1), "kugiri": len(pieces)}
    foot = [footer_number(pages[i]) for i in (p0, p1)]
    if hajime is not None:
        out["suri"] = (hajime + p0, hajime + p1)
        out["sure_chigai"] = any(f is not None and f != s for f, s in zip(foot, out["suri"]))
    elif all(f is not None for f in foot):
        out["suri"] = tuple(foot)
    out["foot"] = tuple(foot)
    return out


def kakikata(r):
    """台帳の場所の書き方。刷られた頁が分からなければ PDF の何枚目で書く"""
    if "suri" in r:
        a, b = r["suri"]
        return "本文 p.%d" % a if a == b else "本文 pp.%d-%d" % (a, b)
    a, b = r["pdf"]
    return "本文PDF の %d枚目" % a if a == b else "本文PDF の %d〜%d枚目" % (a, b)


def main(argv=None):
    ap = argparse.ArgumentParser(description="抜き書きが本文のどの頁にそのまま在るかを探す")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("basho")
    b.add_argument("path")
    b.add_argument("quote")
    b.add_argument("--hajime", type=int)
    b.add_argument("--dai")
    try:
        a = ap.parse_args(argv)
    except SystemExit as e:
        return 2 if e.code else 0
    try:
        pages = read_pages(a.path)
        if not "".join(norm(p) for p in pages):
            raise NoText("本文の文字が1字も取れなかった(画像だけの PDF の見込み)")
        warn = []
        if a.dai and norm(a.dai) not in "".join(norm(p) for p in pages):
            warn.append("題名「%s」が本文の文字に出ない。文字化けか、別の文献の PDF の疑い(手引きの「本文PDFの読み取り」)" % a.dai)
        r = basho(pages, a.quote, a.hajime)
    except Usage as e:
        print("✕ %s" % e)
        return 2
    except NoText as e:
        print("✕ %s" % e)
        return 3
    for w in warn:
        print("△ %s" % w)
    if r is None:
        print("✕ 抜き書きが本文にそのまま見つからない(全%d枚)。写し間違いか言い換え。原文から切り出し直す"
              "(数で始まるなら直前の負号ごと写す・省いた所は「…」で区切る)" % len(pages))
        return 1
    print("○ 見つかった: PDF の %s枚目(区切り %d)" % ("%d" % r["pdf"][0] if r["pdf"][0] == r["pdf"][1]
                                                 else "%d〜%d" % r["pdf"], r["kugiri"]))
    if r.get("sure_chigai"):
        print("△ 書誌の頁から数えた頁(%s)と、頁の上下に刷られた数(%s)が違う。表紙の付いた PDF などの見込み。"
              "刷られた数を確かめて場所を書く" % (r["suri"], r["foot"]))
    print("場所の書き方: %s" % kakikata(r))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
