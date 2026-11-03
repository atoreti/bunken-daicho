# -*- coding: utf-8 -*-
# 部品の版(uv run で走らせると、uv がこの版を、使う人の PC の Python を変えずに用意する。python で打っても動く)
# /// script
# requires-python = ">=3.10"
# dependencies = ["pymupdf==1.27.2.3"]
# ///
"""工程7(手引き wabun-db-guide.md への追記の提案)を、提案した会話とは別の会話で確かめる(run-bunken-daicho)。
標準ライブラリだけ(PDF のページを文字にする時だけ PyMuPDF)。決定= claude-harness の docs/user-decisions.md の D73(ch-hz0)。

手引きには、実在しない欄の名前(e-Stat の結果一覧の「提供年月」)を書いた提案が2件入ったことがある(2026-07)。そこで提案は
記録に書き、確かめ役 assign-bunken-guide-evaluator がページを開き直す。開き直すのも、提案の言葉がページに字のまま在るかを
数えるのもこのスクリプトで、足せる提案にするかもこのスクリプトが決める(確かめ役が「通った」と書いても、言葉が0回なら通さない)。

置き場: <作業用フォルダ>/teian/
  teian.jsonl   提案(1件1行)と、確かめに出した印(junbi)
  kazoe.jsonl   開き直したページごとの1行(URL・状態・中身の指紋・言葉ごとの回数)
  pages/        開き直したページの中身(T1-1.body)と、タグを外した文字(T1-1.txt)。数えたのは .body
  context.json  確かめ役に渡す物 / kakunin.json  確かめ役が書く結果 / kekka.json  3つに分けた結果
  記録(.jsonl)はスクリプトが後ろに足すだけで書く(手で直すと指紋がつながらず止まる)。

使い方:
  uv run teian.py <w> tsuika --db estat --bun "足す文" --go "調査年月" [--go …] --url "その言葉を見たページ" [--url …] [--setsu "節"]
      提案を1件書く(提案した会話が打つ)。--go は「このページにこの字のまま在る」と言う言葉(欄の名前・URL の ? の後ろの名前・
      URL の形)で、見たページから写す。--url には appid を入れない。字で確かめられない提案(一時的なエラー・遅さ)は --go を
      付けずに書けるが、足せる提案にはならない(手引きの「候補」節に置く提案になる)
  uv run teian.py <w> junbi
      確かめに出す。印を1行書き、確かめ役に渡す context.json を書いてパスを出す。この後は tsuika できない
  uv run teian.py <w> toru T1 [--url URL --hojo]
      (確かめ役が打つ)提案 T1 のページを開き直して pages/ に保存し、言葉ごとの回数と前後の字を出す。--hojo は中身を確かめる
      ために開く別のページ(仕様書など)で、回数は合否に使わない。J-STAGE は検索のスクリプトと同じ間合い(6秒以上あけ、
      切られたらその回は開かない)。CiNii・KAKEN の OpenSearch には環境変数のアプリケーション ID を付ける(保存する中身では伏せる)
  uv run teian.py <w> kekka [--yakunashi]
      確かめ役の結果と開き直した記録から、足せる提案・候補に置く提案・通らなかった提案に分け、チャットに写す形で出す。
      --yakunashi は確かめ役がいない環境で、全部を「確かめていない」として出す
  uv run teian.py <w> miru
      書いた提案の一覧
終わりの値: 0=できた / 1=決まりから外れた・結果が取れない(止める) / 2=使い方・ファイルの誤り / 3=開けなかったページがある(toru)
"""
import argparse
import hashlib
import html
import http.client
import json
import os
import re
import shutil
import socket
import sys
import time
import datetime
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kensaku  # noqa: E402
from kyotsu import Stop, Usage, append_log, read_log, ts, write_text  # noqa: E402

KIND_T = "bunken-teian"
KIND_Z = "bunken-teian-kazoe"
DIR = "teian"
DBS = {"cinii": "CiNii", "ndl": "NDLサーチ", "jstage": "J-STAGE", "kaken": "KAKEN", "estat": "e-Stat",
       "kikan": "機関リポジトリ", "scholar": "Google Scholar", "sonota": "そのほか"}
HANTEI = ("tootta", "tooranai", "tashikamerarenai")
TIMEOUT = 60
OOKISA = 30_000_000   # これより大きい中身は数えない(PDF の白書など。読み込みで止まらないため)
# スクリプトから開かないサイト(Google Scholar は robots.txt が自動の取得を禁じる。wabun-db-guide.md の Google Scholar の節)
AKENAI = ("scholar.google.",)
BUN_MAX = 400
GO_MAX = 80
KONKYO_MAX = 160
KAKO = 30        # 前後の字の数
MISERU = 3       # 言葉ごとに見せる前後の字の数
SKILL_DIR = os.path.dirname(HERE)
GUIDE = os.path.join(SKILL_DIR, "references", "wabun-db-guide.md")
JIGO = "確かめ役の判定と食い違った"


def p(*a):
    print(*a)


def tdir(w):
    return os.path.join(w, DIR)


def path(w, name):
    return os.path.join(tdir(w), name)


def load(w):
    rows = read_log(path(w, "teian.jsonl"), KIND_T)
    teian = [r for r in rows if r.get("type") == "teian"]
    junbi = [r for r in rows if r.get("type") == "junbi"]
    return teian, (junbi[0] if junbi else None)


def find(teian, tid):
    for r in teian:
        if r["id"] == tid:
            return r
    raise Usage("提案 %s は無い(miru で一覧を見る)" % tid)


def norm(s):
    """数える時のそろえ方: 文字参照を戻し、NFKC(全角の括弧・英数と半角を同じに数える)"""
    return unicodedata.normalize("NFKC", html.unescape(s or ""))


def squash(s):
    return re.sub(r"\s+", "", s)


def visible(text):
    t = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", text)
    t = re.sub(r"(?s)<!--.*?-->", " ", t)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    return re.sub(r"[ \t\r\f\v]+", " ", norm(t))


def check_url(u):
    u = (u or "").strip()
    if not re.match(r"https?://", u):
        raise Usage("--url は http:// か https:// で始まる URL: %r" % u)
    return kensaku.check_url(u)


# ---- 開く ----

def fetch(url, timeout):
    """→ (中身の bytes or None, 状態, 説明, HTTP の番号, 中身の型)。状態は ok・kirareta(接続を切られた)・shippai"""
    req = urllib.request.Request(url, headers={"User-Agent": kensaku.UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            body = res.read(OOKISA + 1)
            if len(body) > OOKISA:
                return None, "shippai", "中身が %d バイトより大きい" % OOKISA, res.status, ""
            return body, "ok", "", res.status, res.headers.get("Content-Type", "")
    except urllib.error.HTTPError as e:
        return None, "shippai", "HTTP %d" % e.code, e.code, ""
    except urllib.error.URLError as e:
        r = e.reason
        if isinstance(r, (ConnectionResetError, ConnectionAbortedError)):
            return None, "kirareta", "接続を切られた(%s)" % r.__class__.__name__, None, ""
        if isinstance(r, (socket.timeout, TimeoutError)):
            return None, "shippai", "時間切れ(%d秒)" % timeout, None, ""
        return None, "shippai", "つながらない(%s)" % r, None, ""
    except (ConnectionResetError, ConnectionAbortedError, http.client.RemoteDisconnected) as e:
        return None, "kirareta", "接続を切られた(%s)" % e.__class__.__name__, None, ""
    except (socket.timeout, TimeoutError):
        return None, "shippai", "時間切れ(%d秒)" % timeout, None, ""
    except Exception as e:  # noqa: BLE001  開けなかったことも1行残すため
        return None, "shippai", "%s: %s" % (e.__class__.__name__, str(e)[:120]), None, ""


def needs_id(url):
    u = urllib.parse.urlsplit(url)
    return u.hostname in ("cir.nii.ac.jp", "kaken.nii.ac.jp") and u.path.startswith("/opensearch")


def is_jstage(url):
    h = urllib.parse.urlsplit(url).hostname or ""
    return h == "jstage.jst.go.jp" or h.endswith(".jstage.jst.go.jp")


def to_text(body, ctype, cs=None):
    """→ (文字 or None, 説明, 使った文字コード)。cs を渡すとその文字コードで読む(数えた時と同じ読み方で読み直すため)"""
    if body[:5] == b"%PDF-":
        try:
            try:
                import pymupdf as fitz
            except ImportError:
                import fitz
        except ImportError:
            return None, "PDF を文字にする PyMuPDF が無い(uv run で走らせ直す(uv が頭書きの版の PyMuPDF を用意し、使う人の PC の Python は変えない。uv が無ければ、ユーザーに uv を入れてもらう。claude.ai の作業場には PyMuPDF が無いので、そこでは pip install pymupdf で入れる))", "pdf"
        try:
            doc = fitz.open(stream=body, filetype="pdf")
            return "\n".join(pg.get_text() for pg in doc), "", "pdf"
        except Exception as e:  # noqa: BLE001
            return None, "PDF を文字にできない(%s)" % e.__class__.__name__, "pdf"
    if not cs:
        m = re.search(r"charset=([\w.-]+)", ctype or "", re.I) or re.search(rb"<meta[^>]+charset=[\"']?([\w.-]+)", body[:4096], re.I)
        cs = m.group(1) if m else "utf-8"
        cs = cs.decode("ascii", "replace") if isinstance(cs, bytes) else cs
    try:
        return body.decode(cs, "replace"), "", cs
    except LookupError:
        return body.decode("utf-8", "replace"), "", "utf-8"


def kaisu(text_n, go_list):
    return {g: text_n.count(norm(g)) for g in go_list}


def maego(text, g):
    """言葉の前後の字(見せる分だけ)"""
    out, i, gn = [], 0, norm(g)
    while len(out) < MISERU:
        j = text.find(gn, i)
        if j < 0:
            break
        a, b = max(0, j - KAKO), j + len(gn) + KAKO
        out.append(re.sub(r"\s+", " ", text[a:j]) + "【" + gn + "】" + re.sub(r"\s+", " ", text[j + len(gn):b]))
        i = j + len(gn)
    return out


# ---- 命令 ----

def cmd_tsuika(a):
    teian, junbi = load(a.w)
    if junbi:
        raise Stop("もう確かめに出した(%s)。確かめに出した後は提案を足さない(足した提案は確かめられないまま残るため)" % junbi["at"])
    if a.db not in DBS:
        raise Usage("--db は %s のどれか" % "・".join(DBS))
    bun = (a.bun or "").strip()
    if not bun or len(bun) > BUN_MAX:
        raise Usage("--bun(手引きに足す文)は1〜%d字" % BUN_MAX)
    go = []
    for g in a.go or []:
        g = g.strip()
        if not g or len(g) > GO_MAX:
            raise Usage("--go は1〜%d字の言葉: %r" % (GO_MAX, g))
        if norm(g) in (norm(x) for x in go):
            raise Usage("--go が重なっている: %r" % g)
        go.append(g)
    urls = []
    for u in a.url or []:
        u = check_url(u)
        if u not in urls:
            urls.append(u)
    if go and not urls:
        raise Usage("--go を付けた提案には、その言葉を見たページの --url が要る(ページが無いと字を数えられないため)")
    tid = "T%d" % (len(teian) + 1)
    row = {"type": "teian", "id": tid, "at": ts(), "db": a.db, "bun": bun, "go": go, "url": urls, "setsu": (a.setsu or "").strip()}
    append_log(path(a.w, "teian.jsonl"), KIND_T, [row])
    p("%s を書いた(%s・言葉 %d・ページ %d)%s" % (tid, DBS[a.db], len(go), len(urls),
                                         "" if go else "。字で確かめる言葉が無いので、足せる提案にはならない(候補に置く提案)"))
    return 0


def cmd_junbi(a):
    teian, junbi = load(a.w)
    if junbi:
        raise Stop("もう確かめに出した(%s)。確かめは1回。結果が読めない時は同じ %s で確かめ役をもう一度呼ぶ"
                   % (junbi["at"], path(a.w, "context.json")))
    if not teian:
        raise Stop("提案が無い(tsuika で書いてから)")
    append_log(path(a.w, "teian.jsonl"), KIND_T, [{"type": "junbi", "at": ts(), "kazu": len(teian)}])
    me = os.path.abspath(__file__)
    w = os.path.abspath(a.w)
    # uv があれば uv run(頭書きの版の PyMuPDF を uv が用意する)。無ければ python、python という名前も無い環境(python3 しか無い Mac など)では、いま動いている python の場所を書く
    py = "uv run" if shutil.which("uv") else "python" if shutil.which("python") else '"%s"' % sys.executable
    ctx = {"plan": os.path.abspath(path(a.w, "teian.jsonl")), "criteria": [GUIDE], "w": w, "teian_py": me,
           "toru": '%s "%s" "%s" toru <提案の番号>' % (py, me, w),
           "teian": [r["id"] for r in teian],
           "output_contract": {"eval_file": os.path.abspath(path(a.w, "kakunin.json"))}}
    write_text(path(a.w, "context.json"), json.dumps(ctx, ensure_ascii=False, indent=1) + "\n")
    p("確かめに出した(提案 %d件)。確かめ役に渡す物: %s" % (len(teian), os.path.abspath(path(a.w, "context.json"))))
    return 0


def cmd_toru(a):
    teian, junbi = load(a.w)
    if not junbi:
        raise Usage("まだ確かめに出していない(junbi の後に、確かめ役が打つ)")
    t = find(teian, a.tid)
    if a.url:
        u = check_url(a.url)
        if not a.hojo and u not in t["url"]:
            raise Usage("提案 %s に書かれていないページは --hojo で開く(合否に使うのは提案に書かれたページだけ)" % t["id"])
        urls = [u]
    else:
        if a.hojo:
            raise Usage("--hojo は --url と一緒に使う")
        urls = list(t["url"])
    if not urls:
        raise Usage("提案 %s にはページが無い(字で確かめられない提案。開かない)" % t["id"])
    zpath = path(a.w, "kazoe.jsonl")
    zall = read_log(zpath, KIND_Z)
    done = [r for r in zall if r["teian"] == t["id"]]
    os.makedirs(path(a.w, "pages"), exist_ok=True)
    bad = 0
    for u in urls:
        k = len(done) + 1
        row = {"type": "kazoe", "teian": t["id"], "k": k, "url": u, "hojo": bool(a.hojo), "at": ts(),
               "jotai": "", "why": "", "http": None, "size": 0, "sha": "", "file": "", "cs": "", "kaisu": {}}
        js = kensaku.jstage_state(a.w) if is_jstage(u) else None
        body = None
        # 同じ確かめの中で、ほかの提案のために開いたページは開き直さず、保存した中身で数える(外のサイトに同じページを何度も取りに行かないため)
        prev = next((r for r in zall if r["url"] == u and r["jotai"] == "ok" and r["at"] >= junbi["at"]), None)
        if prev is not None:
            text = page_text(a.w, prev)
            row.update(jotai="ok", http=prev["http"], size=prev["size"], sha=prev["sha"], file=prev["file"], cs=prev["cs"],
                       kaisu=kaisu(text, t["go"]), why="%s のページ%d の中身を使った(開き直していない)" % (prev["teian"], prev["k"]))
            append_log(zpath, KIND_Z, [row])
            done.append(row)
            zall.append(row)
            p("%s のページ%d%s(%s): %s。中身= %s/%s" % (t["id"], k, "(補助)" if row["hojo"] else "", u, row["why"],
                                                 os.path.abspath(tdir(a.w)), row["file"]))
            for g in t["go"]:
                n = row["kaisu"][g]
                p("  「%s」 %d回%s" % (g, n, "" if n else "  ★ページに無い"))
                for s in maego(text, g):
                    p("    …%s…" % s)
            continue
        if any(h in (urllib.parse.urlsplit(u).hostname or "") for h in AKENAI):
            row.update(jotai="yameta", why="スクリプトからは開かないサイト(robots.txt が自動の取得を禁じる)")
        elif kensaku.url_db(u) and kensaku.url_db(u) not in kensaku.tsukau_db():
            # 使う人が設定 BUNKEN_DB で外したデータベースのサイトは、確かめでも開かない(D84。仕事での商用の許諾など)
            row.update(jotai="yameta", why="設定 %s で外した %s のサイトなので開いていない" % (kensaku.TSUKAU_NAME, kensaku.url_db(u)))
        elif js is not None and js.get("kirareta"):
            row.update(jotai="yameta", why="この回は %s に J-STAGE に接続を切られたので開いていない" % js["kirareta"])
        else:
            if js is not None and js.get("saigo"):
                try:
                    last = datetime.datetime.fromisoformat(js["saigo"])
                    wait = kensaku.JSTAGE_MA - (datetime.datetime.now(last.tzinfo) - last).total_seconds()
                    if wait > 0:
                        time.sleep(wait)
                except ValueError:
                    pass
            aid = None
            if needs_id(u):
                try:
                    aid = kensaku.appid()
                except Usage as e:
                    row.update(jotai="shippai", why=str(e)[:200])
            if not row["jotai"]:
                body, st, why, code, ctype = fetch(u + ("&" if "?" in u else "?") + "appid=" + aid if aid else u, TIMEOUT)
                row["at"] = ts()
                if js is not None:
                    js["saigo"] = row["at"]
                    if st == "kirareta":
                        js["kirareta"] = row["at"]
                    kensaku.jstage_save(a.w, js)
                if aid and body is not None:
                    body = body.replace(aid.encode("utf-8"), kensaku.APPID_MASK.encode("utf-8"))
                row.update(jotai=st, why=kensaku.kakusu(why, aid), http=code)
        if body is not None:
            text, why, cs = to_text(body, ctype)
            if text is None:
                row.update(jotai="shippai", why=why)
            else:
                name = "%s-%d" % (t["id"], k)
                with open(path(a.w, os.path.join("pages", name + ".body")), "wb") as f:
                    f.write(body)
                write_text(path(a.w, os.path.join("pages", name + ".txt")), visible(text))
                tn = norm(text)
                row.update(size=len(body), sha=hashlib.sha256(body).hexdigest(), file="pages/%s.body" % name, cs=cs,
                           kaisu=kaisu(tn, t["go"]))
        append_log(zpath, KIND_Z, [row])
        done.append(row)
        zall.append(row)
        head = "%s のページ%d%s(%s)" % (t["id"], k, "(補助)" if row["hojo"] else "", u)
        if row["jotai"] != "ok":
            bad += 1
            p("%s: 開けなかった(%s)。記録に1行残した" % (head, row["why"] or row["jotai"]))
            if row["jotai"] == "kirareta":
                p("★J-STAGE に接続を切られた。この回は J-STAGE をもう開かない")
            continue
        p("%s: 開けた(HTTP %s・%d バイト)。中身= %s/%s ・タグを外した文字= %s" % (
            head, row["http"], row["size"], os.path.abspath(tdir(a.w)), row["file"], row["file"][:-5] + ".txt"))
        for g in t["go"]:
            n = row["kaisu"][g]
            p("  「%s」 %d回%s" % (g, n, "" if n else "  ★ページに無い"))
            for s in maego(tn, g):
                p("    …%s…" % s)
    return 3 if bad else 0


def read_kakunin(w, ids):
    f = path(w, "kakunin.json")
    try:
        with open(f, encoding="utf-8") as fh:
            ev = json.load(fh)
    except (OSError, ValueError):
        return None
    items = ev.get("teian") if isinstance(ev, dict) else None
    if not isinstance(items, list):
        return None
    out = {}
    for it in items:
        if not (isinstance(it, dict) and it.get("id") in ids and it.get("hantei") in HANTEI and it["id"] not in out):
            return None
        out[it["id"]] = it
    if set(out) != set(ids):     # 提案の番号が足りない結果は読まない(確かめていない提案を、確かめたように分けないため)
        return None
    return out


def page_text(w, r):
    """保存した中身を読み直す。指紋が記録と違えば止める(数えた後に書き換えた中身で通さないため)"""
    f = path(w, r["file"])
    try:
        with open(f, "rb") as fh:
            body = fh.read()
    except OSError:
        raise Stop("開き直したページの中身が無い: %s" % f)
    if hashlib.sha256(body).hexdigest() != r["sha"]:
        raise Stop("開き直したページの中身が、数えた時と違う(書き換えた): %s" % f)
    text, _, _ = to_text(body, "", r.get("cs") or None)
    return norm(text or "")


def utsushi(jissai, texts):
    """通らなかった提案に添える「ページにある書き方」。タグを含む写しと、ページに字のまま無い写しは出さない"""
    j = (jissai or "").strip()
    return j if j and "<" not in j and len(j) <= KONKYO_MAX and zai(j, texts) else ""


def tebiki_kaisu(go_list):
    """手引きに既に出てくる言葉の回数(足せる提案が、手引きの記述と重なっていないかを足す前に見るため)"""
    try:
        with open(GUIDE, encoding="utf-8") as f:
            g = norm(f.read())
    except OSError:
        return {}
    return {x: g.count(norm(x)) for x in go_list if g.count(norm(x))}


def zai(quote, texts):
    """確かめ役が写したページの字が、保存した中身に字のまま在るか(空白は無視。タグの中と外の両方で探す)"""
    q = squash(norm(quote))
    return bool(q) and any(q in squash(t) or q in squash(visible(t)) for t in texts)


def bunrui(w, t, junbi, zrows, ev):
    """→ (分け方 tasu|kouho|tooranai, 理由, 回数, 根拠)"""
    if not t["go"]:
        return "kouho", "字で確かめる言葉が無い", {}, ""
    mine = [r for r in zrows if r["teian"] == t["id"] and not r["hojo"] and r["url"] in t["url"] and r["at"] >= junbi["at"]]
    oks = [r for r in mine if r["jotai"] == "ok"]
    if not oks:
        why = "・".join(dict.fromkeys(r["why"] or r["jotai"] for r in mine)) or "確かめ役がページを開き直していない"
        return "kouho", "ページを開き直せなかった(%s)" % why, {}, ""
    texts = [page_text(w, r) for r in oks]
    cnt = {g: max(r["kaisu"].get(g, 0) for r in oks) for g in t["go"]}
    e = ev.get(t["id"]) if ev is not None else None
    zero = [g for g in t["go"] if cnt[g] == 0]
    akanai = [u for u in t["url"] if u not in {r["url"] for r in oks}]
    if zero and akanai:
        # 開けなかったページにその言葉が在るかもしれないので、通らないとも通ったとも決めない
        return "kouho", "・".join("「%s」は開けたページに0回" % g for g in zero) + "。開き直せなかったページがある(%s)" % " ・ ".join(akanai), cnt, ""
    if zero:
        why = "・".join("「%s」はページに0回" % g for g in zero)
        if e and e["hantei"] == "tootta":
            why += "(%s。確かめ役は通ったとした)" % JIGO
        jissai = utsushi((e or {}).get("jissai"), texts)
        if jissai:
            why += "。ページにある近い書き方「%s」" % jissai
        return "tooranai", why, cnt, ""
    if e is None:
        return "kouho", "確かめ役の判定が無い", cnt, ""
    if e["hantei"] == "tooranai":
        why = (e.get("riyuu") or "確かめ役が中身がページと合わないとした").strip()
        jissai = utsushi(e.get("jissai"), texts)
        if jissai:
            why += "。ページにある近い書き方「%s」" % jissai
        return "tooranai", why, cnt, ""
    if e["hantei"] == "tashikamerarenai":
        return "kouho", (e.get("riyuu") or "確かめ役が確かめられないとした").strip(), cnt, ""
    konkyo = (e.get("konkyo") or "").strip()
    if not konkyo or len(konkyo) > KONKYO_MAX:
        return "kouho", "確かめ役が根拠の字を写していない(%d字まで)" % KONKYO_MAX, cnt, ""
    if not any(norm(g) in norm(konkyo) for g in t["go"]):
        return "kouho", "確かめ役が写した根拠に、提案の言葉が入っていない", cnt, ""
    if not zai(konkyo, texts):
        return "kouho", "確かめ役が写した根拠の字が、開き直したページに無い", cnt, ""
    return "tasu", "", cnt, konkyo


def cmd_kekka(a):
    teian, junbi = load(a.w)
    if not teian:
        raise Stop("提案が無い")
    if a.yakunashi:
        res = [(t, "kouho", "確かめ役がいない環境で、確かめていない", {}, "") for t in teian]
        kakunin_at = ""
    else:
        if not junbi:
            raise Stop("まだ確かめに出していない(junbi を打って確かめ役を呼ぶ)")
        ev = read_kakunin(a.w, {t["id"] for t in teian})
        if ev is None:
            raise Stop("確かめ役の結果が無いか読めない(teian に提案ごとの id と hantei が要る)。足せる提案にしない。確かめ役を %s で"
                       "もう一度だけ呼び、それでも読めなければ、読めなかったことをチャットに書いてユーザーの判断を待つ"
                       % os.path.abspath(path(a.w, "context.json")))
        zrows = read_log(path(a.w, "kazoe.jsonl"), KIND_Z)
        res = [(t,) + bunrui(a.w, t, junbi, zrows, ev) for t in teian]
        kakunin_at = max((r["at"] for r in zrows), default="")
    out = {"tasu": [], "kouho": [], "tooranai": []}
    for t, c, why, cnt, konkyo in res:
        out[c].append({"id": t["id"], "db": t["db"], "bun": t["bun"], "go": t["go"], "url": t["url"], "setsu": t["setsu"],
                       "riyuu": why, "kaisu": cnt, "konkyo": konkyo})
    write_text(path(a.w, "kekka.json"), json.dumps({"at": ts(), "yakunashi": bool(a.yakunashi), **out},
                                                  ensure_ascii=False, indent=1) + "\n")
    L = ["## 手引き(wabun-db-guide.md)への追記の提案", ""]
    if a.yakunashi:
        L.append("確かめ役がいない環境なので、どの提案もページと照らしていない。手引きにはまだ書き込んでいない。")
    else:
        L.append("提案した会話とは別の会話の確かめ役が、提案のページを開き直して確かめた(最後に開いた時刻 %s)。"
                 "手引きにはまだ書き込んでいない。足すかどうかはユーザーが決める。" % (kakunin_at or "なし"))
    sec = (("tasu", "手引きに足せる提案(確かめ済み。「実証済み」の節に足せる)"),
           ("kouho", "「候補」の節に置く提案(確かめられなかった。使う前にその会話で確かめる)"),
           ("tooranai", "確かめで通らなかった提案(手引きに足さない)"))
    n = 0
    for key, head in sec:
        if not out[key]:
            continue
        L += ["", "### " + head]
        for it in out[key]:
            n += 1
            L.append("%d. [%s・%s] %s" % (n, it["id"], DBS[it["db"]], it["bun"]))
            if key == "tasu":
                L.append("   - 確かめ: %s で %s。根拠「%s」" % (" ・ ".join(it["url"]), "・".join(
                    "「%s」%d回" % (g, it["kaisu"][g]) for g in it["go"]), it["konkyo"]))
                tk = tebiki_kaisu(it["go"])
                if tk:
                    L.append("   - 手引きに既に出てくる言葉: %s(同じことが書いてないか、足す前に手引きを見る)"
                             % "・".join("「%s」%d回" % (g, n) for g, n in tk.items()))
            else:
                L.append("   - 理由: " + it["riyuu"])
    p("\n".join(L))
    p("")
    p("足せる %d件・候補に置く %d件・通らなかった %d件(上の節をそのまま納品のチャットに写す)"
      % (len(out["tasu"]), len(out["kouho"]), len(out["tooranai"])))
    return 0


def cmd_miru(a):
    teian, junbi = load(a.w)
    for t in teian:
        p("%s [%s] %s / 言葉: %s / ページ: %s" % (t["id"], DBS[t["db"]], t["bun"], "・".join(t["go"]) or "なし",
                                            " ・ ".join(t["url"]) or "なし"))
    p("提案 %d件。%s" % (len(teian), "確かめに出した(%s)" % junbi["at"] if junbi else "まだ確かめに出していない"))
    return 0


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="工程7 の追記の提案を、別の会話で確かめる")
    ap.add_argument("w", help="作業用フォルダ")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("tsuika")
    s.add_argument("--db", required=True)
    s.add_argument("--bun", required=True)
    s.add_argument("--go", action="append")
    s.add_argument("--url", action="append")
    s.add_argument("--setsu")
    sub.add_parser("junbi")
    s = sub.add_parser("toru")
    s.add_argument("tid")
    s.add_argument("--url")
    s.add_argument("--hojo", action="store_true")
    s = sub.add_parser("kekka")
    s.add_argument("--yakunashi", action="store_true")
    sub.add_parser("miru")
    a = ap.parse_args(argv)
    fn = {"tsuika": cmd_tsuika, "junbi": cmd_junbi, "toru": cmd_toru, "kekka": cmd_kekka, "miru": cmd_miru}[a.cmd]
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
