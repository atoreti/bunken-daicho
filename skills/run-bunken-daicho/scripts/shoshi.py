# -*- coding: utf-8 -*-
# 部品の版(uv run で走らせると、uv がこの版を、使う人の PC の Python を変えずに用意する。python で打っても動く)
# /// script
# requires-python = ">=3.10"
# dependencies = ["pymupdf==1.27.2.3"]
# ///
"""文献台帳の書誌の項目ファイル(run-bunken-daicho の工程3〜4)。標準ライブラリだけ。
決定= claude-harness の docs/user-decisions.md の D55(ch-f5x.3)。台帳の表はそのままにし、書誌の7項目
(著者名・年・題名・誌名・巻(号)・頁・出版社)をこのファイルに分けて持つ。表の「書誌」欄はこのファイルからこのスクリプトが書く
(手で2回書かないので、表とファイルが食い違わない)。納品物チェッカーは `--shoshi` でこのファイルを読み、7項目を1つずつ
DOI の登録機関の記録と照らす(段階B)。

置き場: 台帳の JSON と同じフォルダの「<台帳名>.shoshi.json」(JSON の無い古い台帳は、台帳と同じフォルダの「<台帳のファイル名から .md を除いた名前>.shoshi.json」)。

1行の項目(キーは英字。値は文字列。chosha だけ文字列の並び):
  n        台帳の # の番号
  shurui   ronbun(論文。既定)・hon(図書)・sho(図書の章)・hokoku(白書・報告書)・sonomama(項目に分けない。統計原表など)
  chosha   著者名の並び(原典の表記のまま。団体名も可)
  nen      年(4桁)  dai 題名(本題)  fukudai 副題(あれば)
  shi      誌名(sho では収録した図書の名)  maki 巻  gou 号  peji 頁(例 1-6)  shuppan 出版社(図書・報告書は要る)
  doi      DOI(あれば)
  kakunin  {"url": 書誌を確かめたページ, "hi": "YYYY-MM-DD"}(どこで・いつ確かめたか)
  shoshi   sonomama の時だけ。書誌欄にそのまま書く文

使い方:
  uv run shoshi.py <項目ファイル> tsuika --n 3 --chosha "平原 幸輝" --nen 2022 --dai "…" [--fukudai …] --shi "都市計画論文集" \
         --maki 57 --gou 1 --peji 1-6 [--shuppan …] [--doi …] --kakunin-url URL --kakunin-hi 2026-10-20 [--shurui ronbun]
  uv run shoshi.py <項目ファイル> tsuika --json-file 1行.json      (1行を JSON で渡す。同じ番号の行は置き換える)
  uv run shoshi.py <項目ファイル> kaku --daicho 台帳.md            (台帳の表の「書誌」欄を項目から書く)
  uv run shoshi.py <項目ファイル> tashikame [--daicho 台帳.md]     (形と、台帳の全行がそろっているか・書誌欄が項目から書いた形か)
  uv run shoshi.py <項目ファイル> miru [--n 3]
終わりの値: 0=できた / 1=形が外れた・台帳と食い違う(止める) / 2=使い方・ファイルの誤り
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from kyotsu import Stop, Usage, read_daicho, split_row, write_text  # noqa: E402

KIND = "bunken-shoshi"
V = 1
SHURUI = ("ronbun", "hon", "sho", "hokoku", "sonomama")
FIELDS = ("chosha", "nen", "dai", "fukudai", "shi", "maki", "gou", "peji", "shuppan", "doi")
CJK_RE = re.compile("[぀-ヿ㐀-鿿豈-﫿]")
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


def p(*a):
    print(*a)


def load(path):
    if not os.path.exists(path):
        return {"kind": KIND, "v": V, "rows": []}
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError, UnicodeDecodeError) as e:
        raise Usage("項目ファイルが読めない: %s (%s)" % (path, e))
    if not (isinstance(d, dict) and d.get("kind") == KIND and d.get("v") == V and isinstance(d.get("rows"), list)):
        raise Stop("項目ファイルの形でない(kind=%s・v=%d・rows の並びが要る): %s" % (KIND, V, path))
    return d


def save(path, d):
    d["rows"].sort(key=lambda r: r.get("n", 0))
    write_text(path, json.dumps(d, ensure_ascii=False, indent=1) + "\n")


def problems(r):
    """1行の形の外れ。→ 外れの並び"""
    out = []
    n = r.get("n")
    tag = "#%s" % n
    if not (isinstance(n, int) and n >= 1):
        return ["n が1以上の整数でない: %r" % n]
    sh = r.get("shurui", "ronbun")
    if sh not in SHURUI:
        out.append("%s: shurui は %s のどれか(%r)" % (tag, "・".join(SHURUI), sh))
    for k, v in r.items():
        vals = v if isinstance(v, list) else ([v] if isinstance(v, str) else [])
        if any("|" in x or "\n" in x for x in vals if isinstance(x, str)):
            out.append("%s: %s に縦棒か改行がある(表が壊れる)" % (tag, k))
    k = r.get("kakunin")
    if not (isinstance(k, dict) and str(k.get("url", "")).startswith("http") and DATE_RE.fullmatch(str(k.get("hi", "")))):
        out.append("%s: kakunin に url(書誌を確かめたページ)と hi(YYYY-MM-DD)が要る" % tag)
    if sh == "sonomama":
        if not (r.get("shoshi") or "").strip():
            out.append("%s: sonomama には shoshi(書誌欄に書く文)が要る" % tag)
        return out
    ch = r.get("chosha")
    if not (isinstance(ch, list) and ch and all(isinstance(x, str) and x.strip() for x in ch)):
        out.append("%s: chosha は著者名の並び(1人以上)" % tag)
    if not re.fullmatch(r"\d{4}", str(r.get("nen", ""))):
        out.append("%s: nen は4桁の年(%r)" % (tag, r.get("nen")))
    if not (r.get("dai") or "").strip():
        out.append("%s: dai(題名)が要る" % tag)
    if sh in ("ronbun", "sho") and not (r.get("shi") or "").strip():
        out.append("%s: %s には shi(%s)が要る" % (tag, sh, "誌名" if sh == "ronbun" else "収録した図書の名"))
    if sh in ("hon", "sho", "hokoku") and not (r.get("shuppan") or "").strip():
        out.append("%s: %s には shuppan(出版社・発行機関)が要る" % (tag, sh))
    for f in FIELDS:
        if f != "chosha" and r.get(f) is not None and not isinstance(r.get(f), str):
            out.append("%s: %s は文字列で書く" % (tag, f))
    return out


def join_authors(names):
    if all(not CJK_RE.search(x) for x in names):
        return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " & " + names[-1]
    return "・".join(names)


def render(r):
    """書誌欄に書く文。台帳のこれまでの書き方(著者(年)「題」誌名 巻(号), 頁)に合わせる"""
    sh = r.get("shurui", "ronbun")
    if sh == "sonomama":
        return r["shoshi"].strip()
    t = r["dai"].strip()
    if (r.get("fukudai") or "").strip():
        t += ("：" if CJK_RE.search(t) else ": ") + r["fukudai"].strip()
    head = "%s(%s)" % (join_authors([x.strip() for x in r["chosha"]]), r["nen"])
    pub = (r.get("shuppan") or "").strip()
    pg = (r.get("peji") or "").strip()
    if sh in ("hon", "hokoku"):
        return head + "『%s』%s" % (t, pub) + (", %s" % pg if pg else "")
    if sh == "sho":
        return head + "「%s」『%s』%s" % (t, r["shi"].strip(), pub) + (", %s" % pg if pg else "")
    vol, iss = (r.get("maki") or "").strip(), (r.get("gou") or "").strip()
    vi = vol + ("(%s)" % iss if iss and vol else ("%s号" % iss if iss else ""))
    s = head + "「%s」%s" % (t, r["shi"].strip())
    s += (" " + vi) if vi else ""
    s += (", " + pg) if pg else ""
    s += (", " + pub) if pub else ""
    return s


def row_from_args(a):
    if a.json_file:
        try:
            with open(a.json_file, encoding="utf-8") as f:
                r = json.load(f)
        except (OSError, ValueError, UnicodeDecodeError) as e:
            raise Usage("--json-file が読めない: %s" % e)
        if not isinstance(r, dict):
            raise Usage("--json-file は1行ぶんの JSON の物(辞書)")
        return r
    if a.n is None:
        raise Usage("--n(台帳の # の番号)が要る")
    r = {"n": a.n, "shurui": a.shurui or "ronbun"}
    for f in ("nen", "dai", "fukudai", "shi", "maki", "gou", "peji", "shuppan", "doi", "shoshi"):
        v = getattr(a, f)
        if v:
            r[f] = v
    if a.chosha:
        r["chosha"] = a.chosha
    r["kakunin"] = {"url": a.kakunin_url or "", "hi": a.kakunin_hi or ""}
    return r


def cmd_tsuika(a):
    d = load(a.file)
    r = row_from_args(a)
    bad = problems(r)
    if bad:
        raise Stop("この行は入れられない: " + " / ".join(bad))
    old = next((x for x in d["rows"] if x.get("n") == r["n"]), None)
    d["rows"] = [x for x in d["rows"] if x.get("n") != r["n"]] + [r]
    save(a.file, d)
    if old:
        diff = [k for k in sorted(set(old) | set(r)) if old.get(k) != r.get(k)]
        p("#%d を置き換えた(変わった項目: %s)" % (r["n"], "・".join(diff) or "なし"))
    else:
        p("#%d を足した" % r["n"])
    p("  書誌欄: " + render(r))
    return 0


def table_cols(lines):
    """台帳の表の見出し行ごとに (行の位置, # の列, 書誌の列) を返す"""
    out = []
    for i, ln in enumerate(lines):
        cells = split_row(ln)
        if cells and "#" in cells and "書誌" in cells:
            out.append((i, cells.index("#"), cells.index("書誌")))
    return out


def check_all(d):
    bad, seen = [], set()
    for r in d["rows"]:
        bad += problems(r)
        if r.get("n") in seen:
            bad.append("#%s が2行ある" % r.get("n"))
        seen.add(r.get("n"))
    return bad


def cmd_kaku(a):
    d = load(a.file)
    bad = check_all(d)
    if bad:
        raise Stop("項目ファイルの形が外れている: " + " / ".join(bad))
    by_n = {r["n"]: r for r in d["rows"]}
    info = read_daicho(a.daicho)
    lines = info["lines"]
    done, skip = [], []
    for hi, ni, bi in table_cols(lines):
        j = hi + 1
        while j < len(lines):
            cells = split_row(lines[j])
            if cells is None:
                break
            if cells and re.fullmatch(r"\d+", cells[ni] if ni < len(cells) else ""):
                n = int(cells[ni])
                if n in by_n and bi < len(cells):
                    cells[bi] = render(by_n[n])
                    lines[j] = "| " + " | ".join(cells) + " |"
                    done.append(n)
                elif n not in by_n:
                    skip.append(n)
            j += 1
    write_text(a.daicho, "\n".join(lines))
    p("書誌欄を書いた: %d行%s" % (len(done), ("(項目ファイルに無い行: %s)" % "・".join("#%d" % n for n in skip)) if skip else ""))
    rest = sorted(set(by_n) - set(done))
    if rest:
        p("★項目ファイルにあって台帳の表に無い行: " + "・".join("#%d" % n for n in rest))
    return 0


def norm_ws(s):
    return re.sub(r"\s+", " ", (s or "").strip())


def cmd_tashikame(a):
    d = load(a.file)
    bad = check_all(d)
    nrow = len(d["rows"])
    if a.daicho:
        by_n = {r["n"]: r for r in d["rows"]}
        info = read_daicho(a.daicho)
        seen = set()
        for _ln, n, cells in info["rows"]:
            if "書誌" not in cells:
                continue
            seen.add(n)
            r = by_n.get(n)
            if r is None:
                bad.append("台帳の #%d が項目ファイルに無い(shoshi.py tsuika で足す)" % n)
            elif not problems(r) and norm_ws(cells["書誌"]) != norm_ws(render(r)):
                bad.append("台帳の #%d の書誌欄が、項目から書いた形と違う(手で直した? 直す時は項目を tsuika で直して kaku で書き直す)" % n)
        for n in sorted(set(by_n) - seen):
            bad.append("項目ファイルの #%d が台帳の表に無い" % n)
    split = sum(1 for r in d["rows"] if r.get("shurui", "ronbun") != "sonomama")
    p("項目ファイル: %d行(項目に分けた %d行・分けていない %d行)" % (nrow, split, nrow - split))
    if bad:
        for b in bad:
            p("✕ " + b)
        return 1
    p("形と台帳の行: 食い違いなし")
    return 0


def cmd_miru(a):
    d = load(a.file)
    for r in d["rows"]:
        if a.n is None or r.get("n") == a.n:
            p("#%s %s" % (r.get("n"), render(r) if not problems(r) else "(形が外れている)"))
            if a.n is not None:
                p(json.dumps(r, ensure_ascii=False, indent=1))
    return 0


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="文献台帳の書誌の項目ファイル")
    ap.add_argument("file", help="項目ファイル(<台帳名>.shoshi.json)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("tsuika")
    t.add_argument("--n", type=int)
    t.add_argument("--shurui", choices=SHURUI)
    t.add_argument("--chosha", nargs="+")
    for f in ("nen", "dai", "fukudai", "shi", "maki", "gou", "peji", "shuppan", "doi", "shoshi"):
        t.add_argument("--" + f)
    t.add_argument("--kakunin-url")
    t.add_argument("--kakunin-hi")
    t.add_argument("--json-file")
    k = sub.add_parser("kaku")
    k.add_argument("--daicho", required=True)
    s = sub.add_parser("tashikame")
    s.add_argument("--daicho")
    m = sub.add_parser("miru")
    m.add_argument("--n", type=int)
    a = ap.parse_args(argv)
    try:
        return {"tsuika": cmd_tsuika, "kaku": cmd_kaku, "tashikame": cmd_tashikame, "miru": cmd_miru}[a.cmd](a)
    except Usage as e:
        p("使い方の誤り: %s" % e)
        return 2
    except Stop as e:
        p("✕ 止めた: %s" % e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
