# -*- coding: utf-8 -*-
"""run-bunken-daicho のスクリプトが共通に使う部品(記録のファイルの読み書き・題名のそろえ方・台帳の読み取り)。標準ライブラリだけ。

記録のファイル(kensaku.jsonl・kouho.jsonl・runs.jsonl・michi.jsonl)は、どれもスクリプトが後ろに足すだけで書く。
各行は前の行の指紋(mae)と自分の指紋(h)を持つ。手で直したり行を消したりすると指紋がつながらなくなり、読む時に止まる
(検索の数を自己申告にしないための仕掛け。決定= claude-harness の docs/user-decisions.md の D55)。
"""
import datetime
import hashlib
import html
import json
import os
import re

V = 1


class Stop(Exception):
    """記録・台帳が決まりから外れた(終わりの値 1)"""


class Usage(Exception):
    """使い方・ファイルの誤り(終わりの値 2)"""


# ---- 記録のファイル(後ろに足すだけ・指紋でつなぐ) ----

def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def finger(row):
    return hashlib.sha256(canonical({k: v for k, v in row.items() if k != "h"}).encode("utf-8")).hexdigest()[:16]


def read_log(path, kind):
    """記録を読む。無ければ空。壊れた行・別の種類の行・指紋がつながらない行で止める"""
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path, "rb") as f:
        raw = f.read()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise Stop("UTF-8 として読めない(壊れている): %s" % path)
    mae = ""
    for n, line in enumerate(text.split("\n"), 1):
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except (ValueError, RecursionError):
            raise Stop("%d 行目が読めない(壊れている): %s" % (n, path))
        if not (isinstance(r, dict) and r.get("kind") == kind and r.get("v") == V and isinstance(r.get("h"), str)):
            raise Stop("%d 行目がこの記録の行の形でない: %s" % (n, path))
        if r.get("mae") != mae or r["h"] != finger(r):
            raise Stop("%d 行目の指紋がつながらない(手で直したか、行を消した。記録はスクリプトが後ろに足すだけで書く): %s"
                       % (n, path))
        mae = r["h"]
        rows.append(r)
    return rows


def append_log(path, kind, new_rows):
    """記録の後ろに行を足す(指紋をつないで)。足した行を返す"""
    have = read_log(path, kind)
    mae = have[-1]["h"] if have else ""
    out = []
    for r in new_rows:
        r = dict(r, v=V, kind=kind, mae=mae)
        r.pop("h", None)
        r["h"] = finger(r)
        mae = r["h"]
        out.append(r)
    if out:
        d = os.path.dirname(os.path.abspath(path))
        os.makedirs(d, exist_ok=True)
        with open(path, "a", encoding="utf-8", newline="\n") as f:
            for r in out:
                f.write(canonical(r).replace(chr(0x2028), "\\u2028").replace(chr(0x2029), "\\u2029") + "\n")
    return out


def now_local():
    return datetime.datetime.now().astimezone().replace(microsecond=0)


def ts(t=None):
    return (t or now_local()).isoformat()


# ---- 題名・名前のそろえ方(D52: 控えめにそろえて完全一致。文字列全体の NFKC はしない) ----

DASH_RE = re.compile("[‐-―−─━﹘﹣]")
WAVE_RE = re.compile("[〜〰]")
OUTER = {"「": "」", "『": "』", "“": "”", '"': '"', "(": ")", "（": "）", "【": "】"}


def soroe(s):
    """控えめにそろえる: 文字参照とタグを除く・全角の英数記号(U+FF01〜FF5E)だけ半角に・空白を消す・ダッシュと波の類を1つに・
    『』を「」に・異体字の選択子と末尾の * を落とす・英字は小文字に・外側の括弧を外す。
    かなと漢字(新字・旧字を含む)は畳まない(旧字体の著者名= F-112 を人に見せるため)。
    納品物チェッカーの段階B(check_deliverable.py の _shoshi_soroe)と同じ規則"""
    s = html.unescape(html.unescape(s or ""))
    s = re.sub(r"<[^>]+>", "", s)
    s = re.sub("[︀-️\U000e0100-\U000e01ef]", "", s)
    s = "".join(chr(ord(c) - 0xFEE0) if 0xFF01 <= ord(c) <= 0xFF5E else c for c in s)
    s = re.sub(r"[\s　]+", "", s).replace("『", "「").replace("』", "」")
    s = DASH_RE.sub("-", s)
    s = WAVE_RE.sub("~", s)
    s = s.lower().rstrip("*")
    while len(s) >= 2 and OUTER.get(s[0]) == s[-1]:
        s = s[1:-1]
    return s


# ---- 台帳(Markdown)の読み取り ----

FENCE_RE = re.compile(r"^\s*(```|~~~)")


def strip_fences(lines):
    out, inside = [], False
    for ln in lines:
        if FENCE_RE.match(ln):
            inside = not inside
            out.append("")
            continue
        out.append("" if inside else ln)
    return out


def split_row(line):
    s = line.strip()
    if not s.startswith("|"):
        return None
    s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def read_daicho(path):
    """台帳を読む。→ {"lines": 行の並び, "rows": [(行番号, #, {列名: 値})], "ronten": {"1": "論点1(…)"}}"""
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        raise Usage("台帳が読めない: %s (%s)" % (path, e))
    except UnicodeDecodeError:
        raise Usage("台帳が UTF-8 として読めない: %s" % path)
    lines = text.split("\n")
    body = strip_fences(lines)
    rows, header = [], None
    for i, ln in enumerate(body):
        cells = split_row(ln)
        if cells is None:
            header = None
            continue
        if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
            continue
        if "#" in cells:
            header = cells
            continue
        if header and cells and re.fullmatch(r"\d+", cells[0]):
            rows.append((i + 1, int(cells[0]), dict(zip(header, cells))))
    ronten = {}
    for ln in body:
        # 論点の行はヘッダー(最初の表か ## の見出しより前)にだけある。帳尻の節の「- 論点1: 検索…」を拾わない
        if ln.startswith("|") or ln.startswith("## "):
            break
        m = re.match(r"^\s*-\s*(論点(\d+)(?:[(（][^)）]*[)）])?)\s*[:：]", ln)
        if m:
            ronten.setdefault(m.group(2), m.group(1))
    return {"text": text, "lines": lines, "rows": rows, "ronten": ronten}


def write_text(path, text):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
