# -*- coding: utf-8 -*-
# 部品の版(uv run で走らせると、uv がこの版を、使う人の PC の Python を変えずに用意する。python で打っても動く)
# /// script
# requires-python = ">=3.10"
# dependencies = ["pymupdf==1.27.2.3"]
# ///
"""走行の記録・未知の箱・論点の案(run-bunken-daicho の工程0・6)。標準ライブラリだけ。
決定= claude-harness の docs/user-decisions.md の D55(ch-f5x.3)。分析= 文献探しの分析 §6-3 の2(置き場= docs/skill-sources.md)
(走行の記録を1回1行で溜め、回をまたいで並べて決める)。未知の箱は勉強ハーネスの michi.jsonl と同じ考え(D48 の7)。

置き場(PC で1か所・git の外。ユーザーの決定): ~/.claude/bunken-daicho-kiroku/
  runs.jsonl   走行1回につき1行(テーマ・論点の案と承認後の差・DB ごとの検索の数・候補の数・台帳の行数・止めた理由・
               時間・ユーザーの手応え(逐語))。数は kensaku.py の記録から数える(自己申告にしない)
  michi.jsonl  作り手が気づいていない困りの声(DB の失敗・締め出し・ユーザーの「ほかに困ったこと」・担当が詰まった所)
  環境変数 BUNKEN_KIROKU_DIR か --kiroku で置き場を替えられる(試験の走行を本番の記録に混ぜない時・Chat)。
作業用フォルダ <w> に置くファイル:
  ronten.jsonl 確認ゲートで出した論点と適合の基準の案と、承認後の形(ch-f5x.8 の rlquiz の題材になる)

どのファイルもスクリプトが後ろに足すだけで書く(手で直さない= 指紋がつながらなくなり、読む時に止まる)。読んで ○× を付ける仕組みは後の段。

使い方:
  uv run kiroku.py ronten <w> an --ronten "1=…" --ronten "2(反論・限界)=…" … --kijun "…"          確認ゲートで出した案
  uv run kiroku.py ronten <w> shonin --ronten "1=…" … --kijun "…" [--kotoba "ユーザーの言葉(逐語)"]   承認された形
  uv run kiroku.py ronten <w> mishonin                                                          質問に答えられない走らせ方(案のまま進む)
  uv run kiroku.py hashiri <w> --daicho 台帳.md --theme "…" --tomete "止めた理由" [--fun 35] [--kotoba "…"] [--kiroku <置き場>]
  uv run kiroku.py kotoba R003 --kotoba "ユーザーの手応え(逐語)" [--kiroku <置き場>]             後から手応えを足す
  uv run kiroku.py michi --koe "…" --doko kensaku|kakunin|checker|user|sonota [--w <w>] [--kiroku <置き場>]
  uv run kiroku.py miru [--kazu 10] [--kiroku <置き場>]
終わりの値: 0=できた / 1=記録が決まりから外れた(止める) / 2=使い方・ファイルの誤り
"""
import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from kyotsu import Stop, Usage, append_log, read_daicho, read_log, ts  # noqa: E402
import kensaku  # noqa: E402

RUNS = "runs.jsonl"
MICHI = "michi.jsonl"
RONTEN = "ronten.jsonl"
KIND_R = "bunken-run"
KIND_M = "bunken-michi"
KIND_T = "bunken-ronten"
DOKO = ("kensaku", "kakunin", "checker", "user", "sonota")
RONTEN_ARG = re.compile(r"\s*(\d+)\s*((?:[(（][^)）]*[)）])?)\s*=\s*(.+)", re.S)


def p(*a):
    print(*a)


def kiroku_dir(a):
    d = getattr(a, "kiroku", None) or os.environ.get("BUNKEN_KIROKU_DIR")
    return d or os.path.join(os.path.expanduser("~"), ".claude", "bunken-daicho-kiroku")


def parse_ronten(items):
    out = []
    for s in items or []:
        m = RONTEN_ARG.fullmatch(s)
        if not m:
            raise Usage("--ronten は「番号=文」か「番号(種類)=文」の形: %r" % s)
        out.append({"n": int(m.group(1)), "shurui": m.group(2).strip("()（）") or "", "bun": m.group(3).strip()})
    nums = [x["n"] for x in out]
    if len(nums) != len(set(nums)):
        raise Usage("--ronten の番号が重なっている")
    return sorted(out, key=lambda x: x["n"])


def cmd_ronten(a):
    path = os.path.join(a.w, RONTEN)
    row = {"type": a.dan, "at": ts()}
    if a.dan in ("an", "shonin"):
        rs = parse_ronten(a.ronten)
        if not rs:
            raise Usage("%s には --ronten が1つ以上要る" % a.dan)
        row["ronten"] = rs
        row["kijun"] = (a.kijun or "").strip()
        if a.kotoba:
            row["kotoba"] = a.kotoba
    elif a.ronten or a.kijun:
        raise Usage("mishonin には --ronten・--kijun を付けない(案のまま進んだ印だけを残す)")
    have = read_log(path, KIND_T)
    if a.dan != "an" and not any(r["type"] == "an" for r in have):
        raise Usage("先に an(確認ゲートで出した案)を残す")
    append_log(path, KIND_T, [row])
    p("論点の%sを残した: %s" % ({"an": "案", "shonin": "承認された形", "mishonin": "未承認の印"}[a.dan], path))
    return 0


def ronten_sa(w):
    """案と承認後の差。→ dict or None(案が無い)"""
    rows = read_log(os.path.join(w, RONTEN), KIND_T)
    an = next((r for r in reversed(rows) if r["type"] == "an"), None)
    if an is None:
        return None
    last = rows[-1]
    out = {"an": an["ronten"], "an_kijun": an.get("kijun", "")}
    if last["type"] == "mishonin" or last["type"] == "an":
        out["shonin"] = None
        out["jotai"] = "未承認" if last["type"] == "mishonin" else "承認の記録なし"
        return out
    sh = last
    a_by = {x["n"]: x for x in an["ronten"]}
    s_by = {x["n"]: x for x in sh["ronten"]}
    out.update(shonin=sh["ronten"], shonin_kijun=sh.get("kijun", ""), kotoba=sh.get("kotoba", ""), jotai="承認",
               tashita=[s_by[n] for n in sorted(set(s_by) - set(a_by))],
               keshita=[a_by[n] for n in sorted(set(a_by) - set(s_by))],
               naoshita=[{"n": n, "mae": a_by[n]["bun"], "ato": s_by[n]["bun"]} for n in sorted(set(a_by) & set(s_by))
                         if (a_by[n]["bun"], a_by[n]["shurui"]) != (s_by[n]["bun"], s_by[n]["shurui"])],
               kijun_naoshita=an.get("kijun", "") != sh.get("kijun", ""))
    return out


def tomatta_from(S):
    """失敗した検索を未知の箱の声にする"""
    out = []
    for s in S:
        if s.get("jotai") in kensaku.SHIPPAI:
            out.append({"type": "tomatta", "doko": "kensaku", "kensaku": s["id"],
                        "koe": "%s/%s 「%s」: %s %s" % (s["db"], s.get("hoho", ""), s["go"], kensaku.JOTAI_NAME.get(s["jotai"], s["jotai"]),
                                                       " ".join(s.get("keikoku") or [])[:200])})
    return out


def cmd_hashiri(a):
    S, cands, _ = kensaku.load(a.w)
    d = read_daicho(a.daicho)
    db = {}
    for s in S:
        x = db.setdefault(s["db"], {"hon": 0, "te": 0, "hit": 0, "shippai": 0, "atarashii": 0})
        x["hon"] += 1
        x["te"] += 1 if s.get("kiroku") == "te" else 0
        x["hit"] += s["kensu"] if isinstance(s.get("kensu"), int) else 0
        x["shippai"] += 1 if s.get("jotai") in kensaku.SHIPPAI else 0
        x["atarashii"] += s.get("atarashii") or 0
    ks = [c.get("kime") for c in cands.values()]
    kouho = {"n": len(cands), "sai": sum(1 for k in ks if k and k["kekka"] == "sai"),
             "otosu": {str(i): sum(1 for k in ks if k and k["kekka"] == "otosu" and k["riyuu"] == i) for i in kensaku.RIYUU},
             "horyu": sum(1 for k in ks if k and k["kekka"] == "horyu"), "mada": sum(1 for k in ks if not k),
             "te": sum(1 for c in cands.values() if c.get("kiroku") == "te")}
    kdir = kiroku_dir(a)
    runs = read_log(os.path.join(kdir, RUNS), KIND_R)
    rid = "R%03d" % (sum(1 for r in runs if r["type"] == "hashiri") + 1)
    row = {"type": "hashiri", "id": rid, "at": ts(), "theme": a.theme, "daicho": os.path.abspath(a.daicho),
           "w": os.path.abspath(a.w), "ronten": ronten_sa(a.w), "kensaku": db, "kouho": kouho,
           "gyou": len(d["rows"]), "ronten_daicho": len(d["ronten"]), "tomete": a.tomete or "", "fun": a.fun,
           "kotoba": a.kotoba or ""}
    append_log(os.path.join(kdir, RUNS), KIND_R, [row])
    voices = [dict(v, hashiri=rid, at=ts()) for v in tomatta_from(S)]
    if voices:
        append_log(os.path.join(kdir, MICHI), KIND_M, voices)
    p("走行の記録を1行足した: %s %s(%s)" % (rid, os.path.join(kdir, RUNS), a.theme))
    p("  検索 %d本(%s)・候補 %d件(採った %d・保留 %d・未判定 %d)・台帳 %d行"
      % (len(S), "・".join("%s %d" % (k, v["hon"]) for k, v in sorted(db.items())), kouho["n"], kouho["sai"],
         kouho["horyu"], kouho["mada"], len(d["rows"])))
    if row["ronten"] is None:
        p("  ★論点の案が残っていない(kiroku.py ronten <w> an で確認ゲートの時に残す)")
    if voices:
        p("  未知の箱に %d件(失敗した検索)を足した: %s" % (len(voices), os.path.join(kdir, MICHI)))
    if not a.kotoba:
        p("  ユーザーの手応えは、聞けたら kiroku.py kotoba %s --kotoba \"…\" で足す" % rid)
    return 0


def cmd_kotoba(a):
    kdir = kiroku_dir(a)
    path = os.path.join(kdir, RUNS)
    runs = read_log(path, KIND_R)
    if not any(r["type"] == "hashiri" and r["id"] == a.id for r in runs):
        raise Usage("走行の記録に %s が無い" % a.id)
    if not (a.kotoba or "").strip():
        raise Usage("--kotoba が空")
    append_log(path, KIND_R, [{"type": "kotoba", "id": a.id, "at": ts(), "kotoba": a.kotoba}])
    p("%s にユーザーの手応えを足した" % a.id)
    return 0


def cmd_michi(a):
    if a.doko not in DOKO:
        raise Usage("--doko は %s のどれか" % "・".join(DOKO))
    if not (a.koe or "").strip():
        raise Usage("--koe が空")
    kdir = kiroku_dir(a)
    row = {"type": "koe", "doko": a.doko, "koe": a.koe.strip(), "at": ts()}
    if a.w:
        row["w"] = os.path.abspath(a.w)
    append_log(os.path.join(kdir, MICHI), KIND_M, [row])
    p("未知の箱に1件足した: %s" % os.path.join(kdir, MICHI))
    return 0


def cmd_miru(a):
    kdir = kiroku_dir(a)
    runs = read_log(os.path.join(kdir, RUNS), KIND_R)
    box = read_log(os.path.join(kdir, MICHI), KIND_M)
    hs = [r for r in runs if r["type"] == "hashiri"]
    p("置き場: %s / 走行 %d回・未知の箱 %d件" % (kdir, len(hs), len(box)))
    for r in hs[-a.kazu:]:
        k = r["kouho"]
        p("  %s %s 「%s」 検索 %d本・候補 %d・採った %d・台帳 %d行・止めた理由: %s"
          % (r["id"], r["at"][:16], r["theme"], sum(v["hon"] for v in r["kensaku"].values()), k["n"], k["sai"], r["gyou"],
             r.get("tomete") or "-"))
    return 0


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="走行の記録・未知の箱・論点の案")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("ronten")
    r.add_argument("w")
    r.add_argument("dan", choices=("an", "shonin", "mishonin"))
    r.add_argument("--ronten", action="append")
    r.add_argument("--kijun")
    r.add_argument("--kotoba")
    h = sub.add_parser("hashiri")
    h.add_argument("w")
    h.add_argument("--daicho", required=True)
    h.add_argument("--theme", required=True)
    h.add_argument("--tomete")
    h.add_argument("--fun", type=int)
    h.add_argument("--kotoba")
    h.add_argument("--kiroku")
    k = sub.add_parser("kotoba")
    k.add_argument("id")
    k.add_argument("--kotoba", required=True)
    k.add_argument("--kiroku")
    m = sub.add_parser("michi")
    m.add_argument("--koe", required=True)
    m.add_argument("--doko", required=True)
    m.add_argument("--w")
    m.add_argument("--kiroku")
    v = sub.add_parser("miru")
    v.add_argument("--kazu", type=int, default=10)
    v.add_argument("--kiroku")
    a = ap.parse_args(argv)
    try:
        return {"ronten": cmd_ronten, "hashiri": cmd_hashiri, "kotoba": cmd_kotoba, "michi": cmd_michi,
                "miru": cmd_miru}[a.cmd](a)
    except Usage as e:
        p("使い方の誤り: %s" % e)
        return 2
    except Stop as e:
        p("✕ 止めた: %s" % e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
