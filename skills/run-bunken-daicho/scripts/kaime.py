# -*- coding: utf-8 -*-
# 部品の版(uv run で走らせると、uv がこの版を、使う人の PC の Python を変えずに用意する。python で打っても動く)
# /// script
# requires-python = ">=3.10"
# dependencies = ["pymupdf==1.27.2.3"]
# ///
"""工程5(書誌の突合)の確かめの回を残す(run-bunken-daicho)。標準ライブラリだけ。
決定= claude-harness の docs/user-decisions.md の D71(ch-f5x.7)。確かめ役 assign-bunken-evaluator は最大3回呼ぶ。回ごとに、
確かめに出した台帳の写し・確かめ役に渡す物・確かめの結果を、作業用フォルダの kaime/<回>/ に残す(上書きしない)。2回目からは、
前の回の写しと比べて変わった行が、どれも前の回で指摘された行かを数える(指摘の外を直さないため)。最後に最良版を決める。

置き場: <作業用フォルダ>/kaime/1/・2/・3/ に、<台帳名>.json と <台帳名>.shoshi.json と <台帳名>.md(確かめに出した台帳の写し。
確かめ役が読むのは Markdown の写し)・context.json(確かめ役に渡す物)・bunken-eval.json(確かめ役が書く結果)・
sabun.json(2回目から。前の回との違い)。最良版を決めたら kaime/saiyo.json。

使い方:
  uv run kaime.py <作業用フォルダ> junbi <台帳.json> --kai N
      N 回目の確かめの準備。台帳の JSON と書誌の項目ファイルと機械用の Markdown を kaime/N/ に写し、確かめ役に渡す context.json を
      書いて、そのパスを出す(確かめ役は Skill ツールでこのパスを引数にして呼ぶ)。Markdown が台帳の JSON か書誌の項目ファイルより
      古ければ止まる(kaku --w を打ってから)。2回目からは、前の回の写しと今の台帳を比べ、変わった行が前の回の
      指摘(重大・中と、開けなかった行)の中かを数えて sabun.json に書く。指摘の外の行が変わっていたら、何も写さずに止まる
      (戻してから打ち直す)。結果がもうある回は作り直さない。前の回に直す指摘が無ければ、次の回は作らない
  uv run kaime.py <作業用フォルダ> kekka --kai N
      N 回目の結果を読み、合否・点・指摘の数と、次にすること(止める/指摘の行を直して N+1 回目)を出す。
      結果が無い・読めない・合否か点が無い時は止まる(合格にしない。確かめ役を同じ回の context.json でもう一度だけ呼ぶ)
  uv run kaime.py <作業用フォルダ> saiyo <台帳.json>
      最良版を決める(合否が通ったの最後の回。ただし最後の回が通らなくても、通らない訳の行がその通った回より後に直した行に無ければ
      最後の回。通った回が無ければ点の高い回、同じ点なら後の回)。今の台帳と違えば、その回の写しを台帳の置き場に戻す
  uv run kaime.py <作業用フォルダ> matome
      書誌突合の1行に写す文(確かめた回数・回ごとの合否と点と指摘の数・採った回・指摘の外で変わった行の数)を出す
機械の照らし(結果を読む時に毎回。課題 ch-jxl・ch-gya): 確かめ役は、原典のページから写した書誌(genten_shoshi)と、要旨の箇条ごとの
  根拠の文(yoshi_konkyo)を結果に書く。このスクリプトが写しの書誌の項目と1字ずつ照らし、合わないのに確かめ役の指摘に無い項目・
  根拠を挙げていない箇条・CiNii や NDL の書誌のページで確かめた全文OA を、重大の指摘として足す(確かめ役は似た誌名への差し替えを
  見逃したことがある)。点は観点の点から重みで数え直し、合否は重大・開けなかった行・合格点から決め直す。結果を書いた後に確かめ役が
  台帳の置き場にファイルを置いていたら止まる(原典の控えは回のフォルダの genten/ に置く)
終わりの値: 0=できた / 1=決まりから外れた・結果が取れない(止める) / 2=使い方・ファイルの誤り
"""
import argparse
import html
import json
import os
import re
import shutil
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import daicho  # noqa: E402
import shoshi  # noqa: E402
from kyotsu import Stop, Usage, write_text  # noqa: E402

KAI_MAX = 3
THRESHOLD = 80
SKILL_DIR = os.path.dirname(HERE)
CRITERIA = (os.path.join(SKILL_DIR, "SKILL.md"), os.path.join(SKILL_DIR, "references", "daicho-format.md"))
ROW_KEYS = ("gyou", "toukei")
# kaku --w・shinkoku が書く欄(直した所ではないので比べない)
SCRIPT_ROW_KEYS = {"ronten"}
SCRIPT_KEYS = set(daicho.SCRIPT_KEYS)


def p(*a):
    print(*a)


def kai_dir(w, n):
    return os.path.join(w, "kaime", str(n))


def eval_path(w, n):
    return os.path.join(kai_dir(w, n), "bunken-eval.json")


def copies(w, n, f):
    """N 回目の台帳の写しのパス。→ (台帳の JSON の写し, 書誌の項目ファイルの写し)"""
    b = daicho.base(f)
    return os.path.join(kai_dir(w, n), b + ".json"), os.path.join(kai_dir(w, n), b + ".shoshi.json")


def read_json(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError, UnicodeDecodeError):
        return None


def read_eval(w, n):
    """N 回目の確かめの結果。読めない・合否か点が無い時は None。台帳の写しがある回は、機械の照らしの指摘を足し、点と合否を決め直す"""
    ev = read_json(eval_path(w, n))
    if not isinstance(ev, dict) or not isinstance(ev.get("passed"), bool):
        return None
    if isinstance(ev.get("score"), bool) or not isinstance(ev.get("score"), (int, float)):
        return None
    fs = ev.get("feedback_structured")
    if fs is not None and not isinstance(fs, dict):
        return None
    ev = dict(ev)
    bd = (ev.get("quality") or {}).get("breakdown") if isinstance(ev.get("quality"), dict) else None
    if isinstance(bd, dict) and all(isinstance(bd.get(k), (int, float)) and not isinstance(bd.get(k), bool) for k, _ in OMOMI):
        ev["score_kakite"] = ev["score"]
        ev["score"] = round(sum(bd[k] * x for k, x in OMOMI) / sum(x for _, x in OMOMI), 1)
    cp = kai_copies(w, n)
    if cp is not None:
        if not isinstance(ev.get("genten_shoshi"), list) or not isinstance(ev.get("yoshi_konkyo"), list):
            return None
        extra = kikai_shiteki(ev, daicho.load(cp[0]), shoshi.load(cp[1]))
        if extra:
            fs = dict(ev.get("feedback_structured") or {})
            fs["high"] = list(fs.get("high") or []) + extra
            ev["feedback_structured"] = fs
            ev["kikai"] = extra
    ev["passed"] = bool(ev["passed"] and not findings(ev, ("high",)) and not ev.get("unverified_rows")
                        and ev["score"] >= THRESHOLD)
    return ev


# 観点の重み(assign-bunken-evaluator の eval-schema.json と同じ。点は確かめ役の計算でなく、ここで数え直す)
OMOMI = (("shoshi", 50), ("nyushu", 30), ("yoshi", 20))
# 機械が照らす書誌の項目(書誌の項目ファイルの鍵, 指摘の欄に出る語)
KOUMOKU = (("chosha", "著者"), ("nen", "年"), ("dai", "題"), ("shi", "誌"), ("maki", "巻"), ("gou", "号"), ("peji", "頁"),
           ("shuppan", "出版"))
HOJIN = re.compile(r"(一般|公益)(社団|財団)法人|特定非営利活動法人|NPO法人|(国立|公立)大学法人|学校法人|(地方)?独立行政法人|国立研究開発法人|"
                   r"株式会社|有限会社|合同会社|\(株\)|\b(inc|ltd|llc|corp|co|gmbh|plc)\b\.?", re.I)
SAKUIN = re.compile(r"(ci\.nii\.ac\.jp|cir\.nii\.ac\.jp|ndlsearch\.ndl\.go\.jp|iss\.ndl\.go\.jp|ndlonline\.ndl\.go\.jp)")


def kai_copies(w, n):
    """N 回目に確かめに出した台帳の写し。→ (台帳の JSON, 書誌の項目ファイル) か None(junbi で作った回でない)"""
    ctx = read_json(os.path.join(kai_dir(w, n), "context.json"))
    if not isinstance(ctx, dict) or not ctx.get("plan"):
        return None
    b = os.path.splitext(os.path.basename(ctx["plan"]))[0]
    cf, csf = os.path.join(kai_dir(w, n), b + ".json"), os.path.join(kai_dir(w, n), b + ".shoshi.json")
    return (cf, csf) if os.path.exists(cf) else None


def soroe(v, key=""):
    """照らすためにそろえる(全角半角・記号・空白・大文字小文字・HTML の記号)。数の項目は数字だけ"""
    if isinstance(v, list):
        v = " ".join(str(x) for x in v)
    t = unicodedata.normalize("NFKC", html.unescape(str(v or "")))
    if key == "shuppan":
        # 法人の種類の語は、ページによって付いたり付かなかったりする(「一般社団法人 人工知能学会」と「人工知能学会」。試しで別の名前と数えた)
        t = HOJIN.sub("", t)
    if key in ("maki", "gou", "peji"):
        return re.sub(r"\D", "", t)
    if key == "nen":
        m = re.search(r"\d{4}", t)
        return m.group(0) if m else t
    return re.sub(r"[\W_]+", "", t).lower()


def kikai_shiteki(ev, d, sh):
    """確かめ役の結果を、確かめに出した台帳の写しと機械で照らす。→ 足す重大の指摘の並び"""
    unv = set()
    for u in ev.get("unverified_rows") or []:
        unv |= row_numbers(u.get("row") if isinstance(u, dict) else u)
    hit = set()
    for it in findings(ev, ("high", "medium", "low")):
        bun = "%s %s" % (it.get("field", ""), it.get("message", ""))
        for m in row_numbers(it.get("row")):
            hit |= {(m, go) for _, go in KOUMOKU + (("", "要旨"), ("", "入手")) if go in bun}
    gen = {}
    for g in ev.get("genten_shoshi") or []:
        if isinstance(g, dict):
            for m in row_numbers(g.get("row")):
                gen[m] = g
    kon = {}
    for k in ev.get("yoshi_konkyo") or []:
        if isinstance(k, dict) and isinstance(k.get("kajo"), int):
            for m in row_numbers(k.get("row")):
                kon[(m, k["kajo"])] = k
    rows = {r["n"]: r for r in sh.get("rows") or [] if isinstance(r, dict)}
    out = []

    def add(n, field, msg, led="", src=""):
        out.append({"area": "kikai", "row": "#%d" % n, "field": field, "ledger": led, "source": src, "message": "機械の照らし: " + msg})
    for r in d.get("gyou") or []:
        n = r.get("n")
        if not isinstance(n, int) or n in unv:
            continue
        g = gen.get(n)
        if g is None:
            add(n, "原典の書誌", "原典のページから写した書誌(genten_shoshi)が無い。書誌を1字ずつ照らせない")
        else:
            s = rows.get(n) or {}
            for key, go in KOUMOKU:
                led = (s.get("dai", "") + s.get("fukudai", "")) if key == "dai" else s.get(key)
                if key not in g or not led or (n, go) in hit:
                    continue
                if soroe(g[key], key) != soroe(led, key):
                    add(n, go, "原典の%sと台帳の%sが1字ずつ照らして合わないのに、指摘に無い。原典のページを開き直して、どちらが正しいかを確かめて直す"
                        % (go, go), " ".join(led) if isinstance(led, list) else str(led), str(g[key]))
            if r.get("nyushu") == "全文OA" and (n, "入手") not in hit:
                u = str(g.get("nyushu_url") or "")
                if not u:
                    add(n, "入手状況", "全文OA の行なのに、入手状況を確かめたページ(nyushu_url)が無い")
                elif SAKUIN.search(u):
                    add(n, "入手状況", "全文OA を書誌の索引のページ(CiNii・NDL)で確かめている。本文を出しているページで確かめる", src=u)
        y = r.get("yoshi") or {}
        if "書誌" in (y.get("han") or ""):
            continue
        for i in range(1, len(y.get("kajo") or []) + 1):
            k = kon.get((n, i))
            if k is None:
                add(n, "要旨", "要旨の箇条%dの根拠(支える原文の文)を挙げていない" % i)
            elif k.get("sasae") is False and (n, "要旨") not in hit:
                add(n, "要旨", "要旨の箇条%dは原文に支えられていないと書いたのに、指摘に無い" % i)
    return out


def findings(ev, levels=("high", "medium")):
    fs = ev.get("feedback_structured") or {}
    return [it for lv in levels for it in (fs.get(lv) or []) if isinstance(it, dict)]


def row_numbers(s):
    """指摘の行の欄から行番号を読む。「#4」「#1・#32」は # の付いた数だけ(「#4(2文字目)」の 2 を拾わない)。# が無ければ数だけの欄(「4」)"""
    s = str(s or "")
    ns = re.findall(r"#\s*(\d+)", s)
    if not ns and re.fullmatch(r"[\s\d,、・]+", s):
        ns = re.findall(r"\d+", s)
    return {int(x) for x in ns}


def shiteki(ev):
    """直す指摘の行。→ (行番号の集合, 行の無い指摘の数)。重大・中の指摘と、開けなかった行"""
    rows, zentai = set(), 0
    for it in findings(ev):
        ns = row_numbers(it.get("row"))
        rows |= ns
        if not ns:
            zentai += 1
    for u in ev.get("unverified_rows") or []:
        rows |= row_numbers(u.get("row") if isinstance(u, dict) else u)
    return rows, zentai


def naosu_count(ev):
    """直す指摘の数(重大・中と、開けなかった行)"""
    return len(findings(ev)) + len(ev.get("unverified_rows") or [])


def by_n(rows):
    return {r["n"]: r for r in rows or [] if isinstance(r, dict) and isinstance(r.get("n"), int) and not isinstance(r.get("n"), bool)}


def diff_rows(old, new, ignore=()):
    """番号で突き合わせた行の違い。→ [(番号, 違いの説明)]"""
    a, b = by_n(old), by_n(new)
    out = []
    for n in sorted(set(a) | set(b)):
        if n not in b:
            out.append((n, "消した"))
        elif n not in a:
            out.append((n, "足した"))
        else:
            keys = sorted(k for k in set(a[n]) | set(b[n]) if k not in ignore and a[n].get(k) != b[n].get(k))
            if keys:
                out.append((n, "・".join(keys)))
    return out


def sabun(old_d, new_d, old_sh, new_sh):
    """前の回の写しと今の台帳の違い。→ {"gyou": […], "toukei": […], "shoshi": […], "zentai": [欄の名前]}"""
    out = {k: diff_rows(old_d.get(k), new_d.get(k), SCRIPT_ROW_KEYS) for k in ROW_KEYS}
    out["shoshi"] = diff_rows(old_sh.get("rows"), new_sh.get("rows"))
    skip = set(ROW_KEYS) | SCRIPT_KEYS
    out["zentai"] = sorted(k for k in set(old_d) | set(new_d) if k not in skip and old_d.get(k) != new_d.get(k))
    return out


def soto_rows(diff, rows):
    """指摘の外で変わった行。→ [(どこ, 番号, 違い)]"""
    return [(k, n, what) for k in ROW_KEYS + ("shoshi",) for n, what in diff[k] if n not in rows]


def where(k):
    return {"gyou": "文献の行", "toukei": "統計原表の行", "shoshi": "書誌の項目"}[k]


def load_pair(f, sf):
    return daicho.load(f), shoshi.load(sf)


def same_files(a, b):
    if not (os.path.exists(a) and os.path.exists(b)):
        return os.path.exists(a) == os.path.exists(b)
    with open(a, "rb") as x, open(b, "rb") as y:
        return x.read() == y.read()


def done_kai(w):
    """結果の読める回の並び。→ [(回, 結果)]"""
    return [(n, ev) for n in range(1, KAI_MAX + 1) for ev in [read_eval(w, n)] if ev is not None]


def cmd_junbi(a):
    w, f, n = a.w, a.daicho, a.kai
    if not 1 <= n <= KAI_MAX:
        raise Usage("確かめは %d 回まで(--kai は 1〜%d)" % (KAI_MAX, KAI_MAX))
    if not os.path.exists(f):
        raise Usage("台帳の JSON が無い: %s" % f)
    md = os.path.join(w, daicho.base(f) + ".md")
    if not os.path.exists(md):
        raise Usage("作業用フォルダに機械用の Markdown が無い(先に daicho.py … kaku --w を打つ): %s" % md)
    if os.path.exists(eval_path(w, n)):
        raise Stop("%d回目の結果はもうある(上書きしない): %s" % (n, eval_path(w, n)))
    sf = daicho.shoshi_path(f)
    # 確かめ役が読むのは Markdown なので、直した台帳から作り直されていなければ止める(古い Markdown を確かめに出さないため)
    if os.path.getmtime(md) < max(os.path.getmtime(x) for x in (f, sf) if os.path.exists(x)):
        raise Stop("機械用の Markdown が台帳の JSON か書誌の項目ファイルより古い。daicho.py … kaku --w を打ってから junbi を打つ: %s" % md)
    d, sh = load_pair(f, sf)
    diff, rows = None, set()
    if n > 1:
        for k in range(1, n):
            if read_eval(w, k) is None:
                raise Stop("%d回目の結果が無いか読めない(順に進める): %s" % (k, eval_path(w, k)))
        prev = read_eval(w, n - 1)
        if naosu_count(prev) == 0:
            raise Stop("%d回目に直す指摘(重大・中・開けなかった行)が無いので、%d回目は作らない" % (n - 1, n))
        of, osf = copies(w, n - 1, f)
        diff = sabun(daicho.load(of), d, shoshi.load(osf), sh)
        rows, zentai = shiteki(prev)
        soto = soto_rows(diff, rows)
        if soto:
            for k, m, what in soto:
                p("✕ 指摘の外で変わった: %s #%d(%s)" % (where(k), m, what))
            raise Stop("%d回目の指摘の外の行が変わっている。指摘の行と欄だけを直し、ほかは %d回目の写し(%s)に戻してから打ち直す"
                       % (n - 1, n - 1, kai_dir(w, n - 1)))
    os.makedirs(kai_dir(w, n), exist_ok=True)
    cf, csf = copies(w, n, f)
    shutil.copyfile(f, cf)
    if os.path.exists(sf):
        shutil.copyfile(sf, csf)
    cmd = os.path.join(kai_dir(w, n), os.path.basename(md))
    shutil.copyfile(md, cmd)
    genten = os.path.join(kai_dir(w, n), "genten")
    os.makedirs(genten, exist_ok=True)
    top = os.path.dirname(os.path.abspath(f))
    ctx = {"plan": os.path.abspath(cmd), "criteria": [os.path.abspath(x) for x in CRITERIA], "threshold": THRESHOLD,
           "output_contract": {"eval_file": os.path.abspath(eval_path(w, n))}, "kai": n,
           "genten_dir": os.path.abspath(genten), "daicho_dir": top, "daicho_files": sorted(os.listdir(top))}
    ctx_path = os.path.join(kai_dir(w, n), "context.json")
    write_text(ctx_path, json.dumps(ctx, ensure_ascii=False, indent=1) + "\n")
    if diff is not None:
        changed = [(k, m, what) for k in ROW_KEYS + ("shoshi",) for m, what in diff[k]]
        write_text(os.path.join(kai_dir(w, n), "sabun.json"), json.dumps(
            {"mae": n - 1, "shiteki_gyou": sorted(rows), "kawatta": [{"doko": k, "n": m, "nani": what} for k, m, what in changed],
             "soto": [], "zentai": diff["zentai"]}, ensure_ascii=False, indent=1) + "\n")
        p("%d回目の写しから変わった行: %s" % (n - 1, " / ".join("%s #%d(%s)" % (where(k), m, what) for k, m, what in changed) or "無し"))
        if diff["zentai"]:
            p("台帳全体の欄で変わった所: %s" % "・".join(diff["zentai"]))
        p("指摘の外で変わった行: 0")
    p("%d回目の準備ができた。確かめ役に渡す物: %s" % (n, os.path.abspath(ctx_path)))
    return 0


def cmd_kekka(a):
    w, n = a.w, a.kai
    if not 1 <= n <= KAI_MAX:
        raise Usage("確かめは %d 回まで(--kai は 1〜%d)" % (KAI_MAX, KAI_MAX))
    ev = read_eval(w, n)
    if ev is None:
        raise Stop("%d回目の結果が無いか読めない(合否・点、原典から写した書誌 genten_shoshi・要旨の根拠 yoshi_konkyo のどれかが無い)。"
                   "合格にしない。確かめ役を %s でもう一度だけ呼び、それでも読めなければ、読めなかったことをチャットに書いてユーザーの判断を待つ"
                   % (n, os.path.join(kai_dir(w, n), "context.json")))
    ctx = read_json(os.path.join(kai_dir(w, n), "context.json")) or {}
    if ctx.get("daicho_dir") and os.path.isdir(ctx["daicho_dir"]):
        new = sorted(set(os.listdir(ctx["daicho_dir"])) - set(ctx.get("daicho_files") or []))
        if new:
            raise Stop("確かめの間に台帳の置き場(%s)にファイルが増えた: %s。確かめ役の原典の控えなら %s に移してから kekka を打ち直す"
                       "(台帳の置き場には、ユーザーに渡す物だけを置く)" % (ctx["daicho_dir"], "・".join(new), ctx.get("genten_dir", "")))
    cnt = {lv: len(findings(ev, (lv,))) for lv in ("high", "medium", "low")}
    p("%d回目: %s・点 %s・重大 %d・中 %d・軽 %d・開けなかった行 %d・確かめた行 %s"
      % (n, "通った" if ev["passed"] else "通らない", ev["score"], cnt["high"], cnt["medium"], cnt["low"],
         len(ev.get("unverified_rows") or []), ev.get("checked_rows", "?")))
    if "score_kakite" in ev and ev["score_kakite"] != ev["score"]:
        p("  点は観点の点から数え直した(確かめ役が書いた点は %s)" % ev["score_kakite"])
    for it in ev.get("kikai") or []:
        p("  重大(機械の照らし) %s %s: %s" % (it["row"], it["field"], it["message"]))
    if naosu_count(ev) == 0:
        p("次: 止める(重大・中の指摘と開けなかった行が無い)。saiyo で最良版を決める")
    elif n >= KAI_MAX:
        p("次: 止める(確かめは %d 回まで)。直さずに saiyo で最良版を決める" % KAI_MAX)
    else:
        rows, zentai = shiteki(ev)
        p("次: 指摘の行だけを直して junbi --kai %d(直す行: %s%s)"
          % (n + 1, "・".join("#%d" % x for x in sorted(rows)) or "無し", "・行の無い指摘 %d件" % zentai if zentai else ""))
    return 0


HANI = re.compile(r"[〜~～\-–—]|ほか|など|等|以下|以上")    # 行の欄の範囲の書き方(「#5〜#7」「#7ほか2行」)


def ochita_gyou(ev):
    """通らない訳の行(重大の指摘(機械の照らしを含む)と開けなかった行。指摘の文に出てくるほかの行の番号も数える)。→ 行番号の集合。
    訳の行が分からない時は None: 合格点に届かない・観点の足切りで落ちた・重大の指摘に辞書でない物か行の無い物がある・
    行の欄が範囲の書き方・確かめ役が通らないとだけ書いた"""
    q = ev.get("quality") if isinstance(ev.get("quality"), dict) else {}
    bd, th = q.get("breakdown") or {}, q.get("dimension_thresholds") or {}
    if ev["score"] < THRESHOLD or ev.get("all_dimensions_passed") is False or any(
            isinstance(bd.get(k), (int, float)) and isinstance(v, (int, float)) and bd[k] < v for k, v in th.items()):
        return None
    high = list((ev.get("feedback_structured") or {}).get("high") or [])
    if any(not isinstance(it, dict) for it in high):
        return None
    rows = set()
    for it in high + [u if isinstance(u, dict) else {"row": u} for u in ev.get("unverified_rows") or []]:
        s = str(it.get("row") or "")
        ns = row_numbers(s)
        if not ns or HANI.search(s):
            return None
        rows |= ns
        for k in ("field", "message", "ledger", "source"):
            rows |= {int(x) for x in re.findall(r"#\s*(\d+)", str(it.get(k) or ""))}
    return rows or None


def kawatta_gyou(w, mae, ato):
    """mae 回の写しから ato 回の写しまでに変わった行(各回の sabun.json)。→ 行番号の集合。台帳全体の欄が変わった・記録が無い時は None"""
    out = set()
    for n in range(mae + 1, ato + 1):
        sb = read_json(os.path.join(kai_dir(w, n), "sabun.json"))
        if not isinstance(sb, dict) or sb.get("zentai"):
            return None
        out |= {x["n"] for x in sb.get("kawatta") or [] if isinstance(x, dict) and isinstance(x.get("n"), int)}
    return out


def best_kai(done, w=None):
    """最良版の回。→ (回, 訳)。
    - 通った回が無い: 点の高い回(同じ点なら後の回)
    - 最後の回が通った: 最後の回
    - 最後の回が通らない: 通らない訳の行が、通った最後の回より後に直した行に1つも無ければ、最後の回(通った回にも同じ所が在り、
      後の回はその上で指摘を直している。3回目で直した要旨の誤りが、2回目を採ったために渡す台帳に戻った試しがあった。ユーザーの決定=
      claude-harness の D78)。直した行に訳がある(直しで入った誤りかもしれない)・訳の行が分からない時は、通った最後の回"""
    passed = [n for n, ev in done if ev["passed"]]
    if not passed:
        return max(done, key=lambda x: (x[1]["score"], x[0]))[0], ""
    last, ev = done[-1]
    if passed[-1] == last or w is None:
        return passed[-1], ""
    ochi, kawa = ochita_gyou(ev), kawatta_gyou(w, passed[-1], last)
    # 通った回より後に何も直していなければ(中身は通った回と同じ)、通った回を採る
    if ochi is not None and kawa and not ochi & kawa:
        return last, ("%d回目は通らないが、通らない訳の行(%s)は %d回目より後に直していない(%d回目にも同じ所が在る)ので、指摘を直した%d回目を採った"
                      % (last, "・".join("#%d" % x for x in sorted(ochi)), passed[-1], passed[-1], last))
    return passed[-1], ""


def cmd_saiyo(a):
    w, f = a.w, a.daicho
    done = done_kai(w)
    if not done:
        raise Stop("結果の読める回が無い(合格にしない): %s" % os.path.join(w, "kaime"))
    best, riyuu = best_kai(done, w)
    ev = dict(done)[best]
    cf, csf = copies(w, best, f)
    sf = daicho.shoshi_path(f)
    if not os.path.exists(cf):
        raise Stop("%d回目の台帳の写しが無い: %s" % (best, cf))
    modoshita = not (same_files(cf, f) and same_files(csf, sf))
    if modoshita:
        shutil.copyfile(cf, f)
        if os.path.exists(csf):
            shutil.copyfile(csf, sf)
    write_text(os.path.join(w, "kaime", "saiyo.json"), json.dumps(
        {"kai": best, "passed": ev["passed"], "score": ev["score"], "modoshita": modoshita,
         "kaisu": len(done), "riyuu": riyuu}, ensure_ascii=False, indent=1) + "\n")
    if riyuu:
        p(riyuu)
    if modoshita:
        p("最良版= %d回目。今の台帳と違ったので、%d回目の写しを台帳の置き場に戻した。kaku --w と工程4 の機械照合を通し直す" % (best, best))
    else:
        p("最良版= %d回目。今の台帳がその回の台帳と同じ" % best)
    if not ev["passed"]:
        p("最良版の合否は通らない。残った指摘(%s)をチャットに並べてユーザーの判断を待つ" % eval_path(w, best))
    return 0


def cmd_matome(a):
    w = a.w
    sj = read_json(os.path.join(w, "kaime", "saiyo.json"))
    if not isinstance(sj, dict):
        raise Stop("先に saiyo を打つ")
    parts = []
    for n, ev in done_kai(w):
        cnt = [(lv, len(findings(ev, (k,)))) for lv, k in (("重大", "high"), ("中", "medium"))]
        un = len(ev.get("unverified_rows") or [])
        s = "%d回目 %s・%s点" % (n, "通った" if ev["passed"] else "通らない", ev["score"])
        s += "".join("・%s%d" % (lv, c) for lv, c in cnt if c) + ("・開けなかった行%d" % un if un else "")
        parts.append(s)
    soto = 0
    for n in range(2, KAI_MAX + 1):
        sb = read_json(os.path.join(kai_dir(w, n), "sabun.json"))
        if isinstance(sb, dict):
            soto += len(sb.get("soto") or [])
    p("確かめ役の確かめ %d回(%s)。採ったのは%d回目の台帳。2回目からの直しで指摘の外が変わった行 %d"
      % (len(parts), "/".join(parts), sj["kai"], soto))
    return 0


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="工程5 の確かめの回を残す")
    ap.add_argument("w", help="作業用フォルダ")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("junbi")
    s.add_argument("daicho", help="台帳の JSON(<台帳名>.json)")
    s.add_argument("--kai", type=int, required=True)
    s = sub.add_parser("kekka")
    s.add_argument("--kai", type=int, required=True)
    s = sub.add_parser("saiyo")
    s.add_argument("daicho", help="台帳の JSON(<台帳名>.json)")
    sub.add_parser("matome")
    a = ap.parse_args(argv)
    fn = {"junbi": cmd_junbi, "kekka": cmd_kekka, "saiyo": cmd_saiyo, "matome": cmd_matome}[a.cmd]
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
