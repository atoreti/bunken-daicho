# -*- coding: utf-8 -*-
# 部品の版(uv run で走らせると、uv がこの版を、使う人の PC の Python を変えずに用意する。python で打っても動く)
# /// script
# requires-python = ">=3.10"
# dependencies = ["pymupdf==1.27.2.3"]
# ///
"""文献台帳の検索の記録と候補の一覧(run-bunken-daicho の工程2・4)。標準ライブラリだけ。
決定= claude-harness の docs/user-decisions.md の D55(ch-f5x.3)。材料= docs/academic-research-skills-analysis.md の
K2(検索の記録の欄・失敗も1行)・V3(全候補に経路と判定)・S7(保留と、保留の割合)・K3・I6(数の帳尻を判定のファイルから機械で)。

検索はこのスクリプトにさせ、語・DB・件数・時刻・成否を自動で1行ずつ残す(自己申告にしない)。検索に出た候補は全部
候補の一覧に入り、担当は候補ごとに 採る/落とす/保留 を付ける。台帳の「## 選別の帳尻」はこのスクリプトが一覧から数えて書く。

作業用フォルダ <w> に置くファイル(どれもこのスクリプトが後ろに足すだけ。手で直さない= 指紋がつながらなくなり、読む時に止まる):
  kensaku.jsonl  検索1本ごとに1行(手で記録した検索・失敗した検索・投げなかった検索も1行)
  kouho.jsonl    候補の一覧(候補・別の検索で再び出た・判定)
  jstage.json    J-STAGE に最後に投げた時刻と、この回に接続を切られたか(間を空けるため・切られた後は投げないため)

使い方:
  uv run kensaku.py <w> sagasu --db cinii|ndl|jstage|kaken|openalex|semanticscholar|arxiv|crossref --q "語" --ronten 1 [--hoho …] [--from YYYY] [--until YYYY] [--kazu 20] [--start 1]
      cinii の --hoho: all(既定)・articles・books・dissertations / ndl: any(既定)・title / jstage: global(既定。年で絞れない)・title・abst・zenbun
      kaken: kadai(既定。科研費の研究課題。--kazu は 20・50・100・200。--from・--until は助成の期間が一部でも入る課題)
      cinii と kaken は、ユーザーの環境変数 CINII_APPID のアプリケーション ID を付けて投げる(両方の規約が ID を求めるため)。
      ID は取りに行く時だけ付け、記録には ID の無い URL を残す。無い・英数字だけの形でない時は、投げずに止める(終わりの値 2)
      英語のデータベース(--q は英語に訳した語。訳した語がそのまま記録に残る):
        openalex: all(既定。題・抄録・本文)・title / semanticscholar: all / arxiv: all(既定)・ti・abs(語を AND でつなぐ)・shiki(--q を
        arXiv の検索式のまま送る) / crossref: all(既定)・shoshi(書誌の欄だけ)。openalex と semanticscholar の --kazu は100まで。
        --start は 1・1+kazu・1+2×kazu … のどれか(2ページ目より先を何千件も取り寄せない)
        openalex は、ユーザーの環境変数 OPENALEX_API_KEY があれば、そのキーを付けて投げる(無ければキー無しで投げる。キー無しの1日の枠は
        同じ回線の全員で分け合う)。キーは openalex.org のサインインにも使うので、記録・画面に出さない
        間合い: 同じ DB への問い合わせは PC 全体で1本ずつ、前から openalex・semanticscholar・crossref は1秒・arxiv は3秒あける。
        断られた(429)時は2・4・8秒(arxiv は3秒ずつ)待って3回まで。OpenAlex の1日の枠が尽きたら、その日(UTC)はもう送らない
  uv run kensaku.py <w> tsukau
      使うデータベースを出す。使う人が設定 BUNKEN_DB に「openalex,crossref」のように並べた物だけを使い、外した物には
      sagasu・te・shoroku・tsuika と、本文の置き場を開く honbun.py・ページを開き直す teian.py が送らずに止まる
      (仕事ではサービスごとに商用の許諾が違うため。D84)。置いていなければ全部使う
  uv run kensaku.py <w> settei
      スキルの設定ファイル(~/.claude/bunken-daicho/settings.json。環境変数 BUNKEN_SETTEI で置き場を変えられる)の置き場と、
      CINII_APPID・OPENALEX_API_KEY・BUNKEN_DB をどこから読むかを出す(値は出さない)。無ければひな形を作る
  uv run kensaku.py <w> shoroku --doi DOI | --arxiv ID
      英語の論文の抄録を Semantic Scholar → OpenAlex → Crossref(arXiv の番号なら arXiv)の順に取り、出どころの URL と一緒に
      <w>/shoroku/ に保存して出す(出版社のページが機械の取得を断る論文の抄録を、確かめ役も同じ形で読み直せるように)
  uv run kensaku.py <w> te --db estat --q "語" --ronten 3 [--kensu 32] [--jotai ok|zero|shippai] [--url …] [--memo …]
      スクリプトで扱わない DB(e-Stat・機関リポジトリ・人が手で検索した Google Scholar など)の検索を手で記録する(「手で記録」の印が付く)
  uv run kensaku.py <w> tsuika --ronten 2 --dai "題" --url URL --keiro "#3の引用文献より" [--kensaku S005] [--doi …] [--chosha 名 …] [--nen YYYY] [--shi 誌名]
      検索の一覧に出ない候補(芋づる・手で記録した検索で見つけた物)を一覧に足す
  uv run kensaku.py <w> kime K0012 sai --gyou 5 [--ronten 1,3]
  uv run kensaku.py <w> kime K0013 otosu --riyuu 4 --kimete "対象が韓国の農村"
  uv run kensaku.py <w> kime K0014 horyu --kimete "本文PDFが開けない。後で試す"
  uv run kensaku.py <w> ichiran [--ronten 1] [--mada]
  uv run kensaku.py <w> chojiri [--daicho 台帳.md] [--soe "3=中心と見た人と誌= …"]
      帳尻の節を出す。--daicho を付けると、台帳の「## 選別の帳尻」の節を書き換える(無ければ「## 探索記録」の前に入れる)
  uv run kensaku.py <w> tashikame --daicho 台帳.md
      記録の指紋・判定の形・台帳の行と「採った」の対応・台帳の帳尻が一覧から数えた物と同じか・
      NDLサーチの API や KAKEN を使った時の「使ったAPIと出典」の行が探索記録に在るかを調べる
終わりの値: 0=できた / 1=記録・台帳が決まりから外れた(止める) / 2=使い方・ファイル・ID の誤り / 3=検索に失敗した(失敗も1行残した)
"""
import argparse
import contextlib
import datetime
import html
import http.client
import json
import os
import re
import socket
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from kyotsu import Stop, Usage, append_log, read_daicho, read_log, soroe, ts, write_text  # noqa: E402

KENSAKU = "kensaku.jsonl"
KOUHO = "kouho.jsonl"
JSTAGE_STATE = "jstage.json"
KIND_S = "bunken-kensaku"
KIND_K = "bunken-kouho"
UA = "Mozilla/5.0 (compatible; run-bunken-daicho/1)"
DBS = {
    "cinii": {"hoho": ("all", "articles", "books", "dissertations"), "timeout": 40},
    "ndl": {"hoho": ("any", "title"), "timeout": 90},      # 実測 2026-10-20: 1回 17〜43秒・30秒で時間切れも1回
    "jstage": {"hoho": ("global", "title", "abst", "zenbun"), "timeout": 40},
    "kaken": {"hoho": ("kadai",), "timeout": 90},           # 実測 2026-11-01: 15件で 17秒・0.9MB(1件ごとに成果の一覧まで返る)
    # 英語のデータベース(claude-harness の D75。2026-11-02 に4つとも実機で確かめた)。間合いと断られた時の扱いは、参考にした手順書
    # (出どころ= claude-harness の docs/bunken-english-db-ch-4f2.md)と各サイトの約款どおり
    "openalex": {"hoho": ("all", "title"), "timeout": 30},
    "semanticscholar": {"hoho": ("all",), "timeout": 30},
    "arxiv": {"hoho": ("all", "ti", "abs", "shiki"), "timeout": 30},
    "crossref": {"hoho": ("all", "shoshi"), "timeout": 30},
}
EIGO = ("openalex", "semanticscholar", "arxiv", "crossref")
# 前の問い合わせから空ける秒数(PC 全体で1本ずつ)。arXiv の約款は、使う機械の全部を合わせて「3秒に1本・同時に1本」と定める。
# Crossref の語の検索は名乗り無しで「1秒に1本・同時に1本」(2026-11-02 の応答の欄 x-rate-limit-limit: 1・x-concurrency-limit: 1)。
# OpenAlex・Semantic Scholar は参考にした手順書の名乗り無しの間合い(1秒に1本)
AIDA = {"openalex": 1, "semanticscholar": 1, "arxiv": 3, "crossref": 1}
# 一時的に断られた(429)時に待つ秒数と回数(参考にした手順書: 2→4→8 秒で3回まで。arXiv は約款の間合いより短く待たない)
MATSU = {"openalex": (2, 4, 8), "semanticscholar": (2, 4, 8), "crossref": (2, 4, 8), "arxiv": (3, 3, 3)}
KAZU_MAX = {"openalex": 100, "semanticscholar": 100}
AIDA_DIR_ENV = "BUNKEN_AIDA_DIR"          # 前の時刻を置く所(試験では作業用の一時フォルダに替える)
JUNBAN_MATSU = 600                        # 順番待ちの上限(秒)
JUNBAN_FURUI = 180                        # これより古い順番の札は、落ちた処理の置き忘れとみなして外す
# OpenAlex の無料のキー(ユーザーが決めた 2026-11-02・D75。公式の値段のページ「$1 of API usage per day for free」
# 「no payment method required」)。キーは openalex.org のサインインにも使うので、送る時に要求の欄(Authorization)にだけ入れ、
# URL・記録・画面に出さない
OA_KEY_NAME = "OPENALEX_API_KEY"
OA_KEY_RE = re.compile(r"[A-Za-z0-9_\-]{8,128}")
OA_KEY_MASK = "(キー)"
ARXIV_NS = {"a": "http://www.w3.org/2005/Atom", "os": "http://a9.com/-/spec/opensearch/1.1/",
            "arxiv": "http://arxiv.org/schemas/atom"}
JSTAGE_ITEM = {"title": 2, "abst": 3, "zenbun": 4}
# CiNii Research と KAKEN の OpenSearch は、規約でアプリケーション ID が要る(CiNii のウェブ API 利用細則 第4条・
# OpenSearch の仕様の appid「必須です。」。ID は両方で共通)。ID はユーザーの環境変数に置き、git にも記録にも書かない。
APPID_NAME = "CINII_APPID"
APPID_DB = ("cinii", "kaken")
APPID_RE = re.compile(r"[A-Za-z0-9]{8,64}")   # 英数字だけの形の時だけ送る(2026-10-31 に別の命令の文が入った値を送ってしまった)
APPID_MASK = "(ID)"
KAKEN_RW = (20, 50, 100, 200)
# 使うデータベース(D84 の6)。仕事ではサービスごとに商用の許諾が違う(CiNii・KAKEN は学術研究か非営利に限る、など)ので、
# 使う人が設定で選ぶ。環境変数に「openalex,crossref」のようにカンマで並べる。置いていなければ全部使う(今までどおり)
TSUKAU_NAME = "BUNKEN_DB"
# ID・キー・使うデータベースを置くスキルの設定ファイル(D84 の7)。Claude Code 全体の設定(settings.json の env)に置くと、
# どのフォルダの会話でも、Claude が走らせる全部の命令に渡るため、スキルのスクリプトだけが読むファイルにする。
# 読む順= この端末の環境変数 → この設定ファイル → (Windows は)アカウントの環境変数。置き場を変える時は環境変数 BUNKEN_SETTEI
SETTEI_ENV = "BUNKEN_SETTEI"
# 外したデータベースのサイト(本文の置き場を開く・候補に足す時も、ここに当たる URL は送らない)
DB_HOSTS = {"cinii": ("ci.nii.ac.jp", "cir.nii.ac.jp"), "kaken": ("kaken.nii.ac.jp", "nrid.nii.ac.jp"),
            "ndl": ("ndlsearch.ndl.go.jp",), "jstage": ("jstage.jst.go.jp",), "openalex": ("openalex.org",),
            "semanticscholar": ("semanticscholar.org",), "arxiv": ("arxiv.org",), "crossref": ("crossref.org",)}
# 台帳の探索記録の「### 使ったAPIと出典」に写す行(daicho-format.md「使ったAPIと出典の行」。文面はユーザーが決めた 2026-11-01)。
# NDLサーチは API を使うサイトやアプリに明記を、KAKEN は内容を使う時に出典と加工したことを書くよう求める
SHUSSHO = {"ndl": "この台帳の探索には、国立国会図書館サーチ(NDLサーチ)の API を用いた。",
           "kaken": "出典：KAKEN：科学研究費助成事業データベース（国立情報学研究所）（検索の結果を加工して作成）",
           # Semantic Scholar の API の約款(Attribution の節。2026-11-02 に読んだ)は、使って得た物を載せる所に Semantic Scholar の
           # 出典を書くよう求める(論文にする時は The Semantic Scholar Open Data Platform を引く。daicho.py の方法の下書きが書き添える)
           "semanticscholar": "この台帳の探索には、Semantic Scholar の API を用いた(出典：Semantic Scholar)。"}
# J-STAGE は短い時間の大量の自動接続を締め出す(2026-10-20 に2回。3本並べで30分〜1時間40分。trials/bunken-coverage/RESULT.md)。
# 1本ずつ、前に投げてからこの秒数を空ける。切られたら、その回はもう投げない。
JSTAGE_MA = 6
RIYUU = {1: "①重複", 2: "②範囲外", 3: "③確かめられない", 4: "④別の対象", 5: "⑤論点に効かない"}
KEKKA = {"sai": "採った", "otosu": "落とした", "horyu": "保留"}
KIMETE_MAX = 30
SHIPPAI = ("shippai", "kirareta", "yameta", "kensu_nashi", "kotowari", "waku_nashi")
JOTAI_NAME = {"ok": "ヒットあり", "zero": "0件", "kensu_nashi": "件数の表示なし", "shippai": "失敗",
              "kirareta": "接続を切られた", "yameta": "投げていない(J-STAGE に切られた後・1日の枠が尽きた後)",
              "kotowari": "断られた(混んでいる・回数の上限。待って3回送り直した後)", "waku_nashi": "1日の枠が尽きた"}
KENSU_NASHI_HINT = ("件数の表示が無い(検索が実行されず詳細検索の画面が返った見込み)。0件と読まない。"
                    "語数を変える・全文検索に替える・同じ語を別の DB に投げる(wabun-db-guide.md の「検索語の並べ方」)")
RONTEN_RE = re.compile(r"[1-9][0-9]?")


def p(*a):
    print(*a)


# ---- 取りに行く ----

def fetch(url, timeout):
    """→ (本文 or None, 状態, 説明)。状態は ok・kirareta(接続を切られた)・shippai"""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return res.read().decode("utf-8", "replace"), "ok", ""
    except urllib.error.HTTPError as e:
        return None, "shippai", "HTTP %d" % e.code
    except urllib.error.URLError as e:
        r = e.reason
        if isinstance(r, (ConnectionResetError, ConnectionAbortedError)):
            return None, "kirareta", "接続を切られた(%s)" % r.__class__.__name__
        if isinstance(r, (socket.timeout, TimeoutError)):
            return None, "shippai", "時間切れ(%d秒)" % timeout
        return None, "shippai", "つながらない(%s)" % r
    except (ConnectionResetError, ConnectionAbortedError, http.client.RemoteDisconnected) as e:
        return None, "kirareta", "接続を切られた(%s)" % e.__class__.__name__
    except (socket.timeout, TimeoutError):
        return None, "shippai", "時間切れ(%d秒)" % timeout
    except Exception as e:  # noqa: BLE001  失敗も1行残すため、何で落ちても記録に回す
        return None, "shippai", "%s: %s" % (e.__class__.__name__, str(e)[:120])


def user_env(name):
    """Windows のユーザーの環境変数の登録から読む(置いた後に開いた端末でなくても読めるように)。無ければ None"""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            return str(winreg.QueryValueEx(k, name)[0])
    except (ImportError, OSError):
        return None


def settei_path():
    return os.environ.get(SETTEI_ENV) or os.path.join(os.path.expanduser("~"), ".claude", "bunken-daicho", "settings.json")


def settei_file():
    """スキルの設定ファイルの中身 {名前: 値}(無ければ {})。壊れていれば止める(黙って全部使う形や ID 無しに戻さない)"""
    path = settei_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8-sig") as f:
            d = json.load(f)
    except (OSError, ValueError) as e:
        raise Usage("スキルの設定ファイル %s が読めない(JSON の書き方を確かめる。最後の行の終わりのカンマなど): %s" % (path, str(e)[:100]))
    if not isinstance(d, dict):
        raise Usage("スキルの設定ファイル %s は { } で囲んだ形にする" % path)
    return d


def settei(name):
    """設定の値を読む(この端末の環境変数 → スキルの設定ファイル → Windows のアカウントの環境変数)。無ければ None。
    値は画面にも記録にも出さない"""
    v = os.environ.get(name)
    if v is None:
        f = settei_file().get(name)
        if isinstance(f, list):
            f = ",".join(str(x) for x in f)
        v = None if f in (None, "") else str(f)
    if v is None and sys.platform == "win32":
        v = user_env(name)
    return v


OKIKATA = ("使う人が、スキルの設定ファイル(%s。`kensaku.py <作業用フォルダ> settei` がひな形を作る)をエディタで開いて書く"
           "(値はチャットに貼らない)")


def appid():
    """CiNii と KAKEN のアプリケーション ID を読む。値は画面にも記録にも出さない。
    無い・英数字だけの形でない時は、投げずに止める(ID を付けずに投げる形に黙って戻さない)"""
    v = (settei(APPID_NAME) or "").strip()
    if not v:
        raise Usage("%s(CiNii と KAKEN のアプリケーション ID)が無いので、投げずに止めた。両方の規約が ID を求める。"
                    % APPID_NAME + OKIKATA % settei_path() +
                    "。置けない環境では、手で検索して te --db … --memo \"ID が無い\" で記録する")
    if not APPID_RE.fullmatch(v):
        raise Usage("%s の値が英数字だけの形でない(%d文字)ので、送らずに止めた。" % (APPID_NAME, len(v)) + OKIKATA % settei_path())
    return v


def tsukau_db():
    """使ってよいデータベースの並び(DBS の順)。置いていなければ全部。知らない名前があれば止める(書き違いで黙って外さないため)"""
    v = settei(TSUKAU_NAME)
    names = [x.strip().lower() for x in re.split(r"[,、\s]+", v or "") if x.strip()]
    if not names:
        return list(DBS)
    bad = [x for x in names if x not in DBS]
    if bad:
        raise Usage("設定 %s に知らない名前がある(%s)。使える名前は %s" % (TSUKAU_NAME, "・".join(bad), "・".join(DBS)))
    return [x for x in DBS if x in names]


def tsukawanai(db):
    """設定で外したデータベースなら止める"""
    if db in DBS and db not in tsukau_db():
        raise Usage("%s は設定 %s で使わないことにしたデータベースなので、送らずに止めた。使う人が規約を見て外した物なので、"
                    "ブラウザや手の検索でも開かず、同じ語を使えるデータベース(%s)に送る" % (db, TSUKAU_NAME, "・".join(tsukau_db())))


def url_db(url):
    """URL がどのデータベースのサイトか。→ 名前 or None"""
    h = (urllib.parse.urlsplit(url or "").hostname or "").lower()
    for db, hosts in DB_HOSTS.items():
        if any(h == x or h.endswith("." + x) for x in hosts):
            return db
    return None


def tsukawanai_url(url):
    """設定で外したデータベースのサイトの URL なら止める(本文の置き場を開く・候補に足す・ページを開き直す時も同じ関門を通す)"""
    db = url_db(url)
    if db and db not in tsukau_db():
        raise Usage("%s は、設定 %s で外した %s のサイトなので、開かずに止めた。使う人が規約を見て外した物なので、ブラウザでも開かない。"
                    "本文はほかの置き場(機関リポジトリなど)を探し、無ければ読み切れなかった訳に書く" % (url, TSUKAU_NAME, db))


def kakusu(s, aid):
    """文の中の ID を伏せる(応答の文・失敗の説明に混ざっても、記録と画面に出さないため)"""
    return s.replace(aid, APPID_MASK) if aid and isinstance(s, str) else s


# ---- 英語のデータベース(キー・順番・断られた時) ----

def oa_key():
    """OpenAlex のキーを読む。→ キー or None(無ければキー無しで投げる。キー無しも規約で認められている)。
    値はあるが形が違う時は、送らずに止める(別の文が入った値を外へ送らないため)"""
    v = (settei(OA_KEY_NAME) or "").strip()
    if not v:
        return None
    if not OA_KEY_RE.fullmatch(v):
        raise Usage("%s の値がキーの形(英数字と - _ だけ・8〜128字)でない(%d文字)ので、送らずに止めた。" % (OA_KEY_NAME, len(v))
                    + OKIKATA % settei_path())
    return v


def fetch_eigo(url, timeout, headers=None):
    """英語のデータベース用。→ (本文 or None, 状態, 説明, 応答の欄 {小文字の名前: 値})。
    状態は ok・kotowari(429= 混んでいる・回数の上限)・kirareta・shippai"""
    h = {"User-Agent": UA, "Accept": "application/json, application/atom+xml;q=0.9, */*;q=0.5"}
    h.update(headers or {})
    req = urllib.request.Request(url, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return (res.read().decode("utf-8", "replace"), "ok", "",
                    {k.lower(): v for k, v in res.headers.items()})
    except urllib.error.HTTPError as e:
        hd = {k.lower(): v for k, v in (e.headers.items() if e.headers else [])}
        return None, ("kotowari" if e.code == 429 else "shippai"), "HTTP %d" % e.code, hd
    except urllib.error.URLError as e:
        r = e.reason
        if isinstance(r, (ConnectionResetError, ConnectionAbortedError)):
            return None, "kirareta", "接続を切られた(%s)" % r.__class__.__name__, {}
        if isinstance(r, (socket.timeout, TimeoutError)):
            return None, "shippai", "時間切れ(%d秒)" % timeout, {}
        return None, "shippai", "つながらない(%s)" % r, {}
    except (ConnectionResetError, ConnectionAbortedError, http.client.RemoteDisconnected) as e:
        return None, "kirareta", "接続を切られた(%s)" % e.__class__.__name__, {}
    except (socket.timeout, TimeoutError):
        return None, "shippai", "時間切れ(%d秒)" % timeout, {}
    except Exception as e:  # noqa: BLE001  失敗も1行残すため、何で落ちても記録に回す
        return None, "shippai", "%s: %s" % (e.__class__.__name__, str(e)[:120]), {}


def aida_dir():
    return os.environ.get(AIDA_DIR_ENV) or os.path.join(tempfile.gettempdir(), "run-bunken-daicho-aida")


def aida_load(db):
    try:
        with open(os.path.join(aida_dir(), db + ".json"), encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


@contextlib.contextmanager
def fuda(lock, nani):
    """順番の札(lock のファイルを作れた処理だけが進む)。落ちた処理の置き忘れの札は JUNBAN_FURUI 秒で外す"""
    t0 = time.time()
    while True:
        try:
            os.close(os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
            break
        except FileExistsError:
            try:
                if time.time() - os.path.getmtime(lock) > JUNBAN_FURUI:
                    os.remove(lock)
                    continue
            except OSError:
                pass
            if time.time() - t0 > JUNBAN_MATSU:
                raise Stop("%s の順番待ちが %d 秒を超えた(別の処理が使い続けている。札= %s)" % (nani, JUNBAN_MATSU, lock))
            time.sleep(0.5)
    try:
        yield
    finally:
        try:
            os.remove(lock)
        except OSError:
            pass


@contextlib.contextmanager
def junban(db):
    """その DB への問い合わせを PC 全体で1本ずつにする(順番の札 <db>.lock)。→ 前の時刻などの dict(書き換えると、抜ける時に残る)"""
    d = aida_dir()
    os.makedirs(d, exist_ok=True)
    with fuda(os.path.join(d, db + ".lock"), db):
        st = aida_load(db)
        try:
            yield st
        finally:
            write_text(os.path.join(d, db + ".json"), json.dumps(st, ensure_ascii=False))


KAKIKOMI_FUDA = ".kakikomi.lock"


@contextlib.contextmanager
def kakikomi(w):
    """作業用フォルダの記録と候補の一覧を、読んで足すまで1つの処理だけにする(2026-11-02 の試しで、和文と英語の検索を
    2つの処理で同時に回した子の一覧に、同じ番号の候補が2つ入り、以後の検索が全部止まった。番号は読んだ時の数から付けるため)"""
    os.makedirs(w, exist_ok=True)
    with fuda(os.path.join(w, KAKIKOMI_FUDA), "作業用フォルダ"):
        yield


def utc_day():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")


def waku_tsukita(db, hd):
    """OpenAlex の 429 が「1日の枠が尽きた」か(参考にした手順書: X-RateLimit-Remaining が 0 なら、その日は送り直しても通らない)"""
    if db != "openalex":
        return False
    for k in ("x-ratelimit-remaining", "x-ratelimit-remaining-usd"):
        v = hd.get(k)
        try:
            if v is not None and float(v) <= 0:
                return True
        except ValueError:
            pass
    return False


def okuru(db, url, headers, kakusu_mono=None):
    """英語の DB に1本送る(間合い・断られた時の待ち・1日の枠)。→ (本文 or None, 状態, 説明, 応答の欄, 送り直した回数)。
    kakusu_mono は伏せる文字列(キー)"""
    with junban(db) as st:
        if db == "openalex" and st.get("tsukita") == utc_day() and st.get("kagi") == bool(kakusu_mono):
            return None, "yameta", "この日(UTC)は OpenAlex の1日の枠が尽きた後なので送っていない(枠は日本時間の朝9時に戻る)", {}, 0
        naoshi = 0
        while True:
            last = st.get("saigo")
            if isinstance(last, (int, float)):
                wait = AIDA[db] - (time.time() - last)
                if wait > 0:
                    time.sleep(wait)
            text, s, why, hd = fetch_eigo(url, DBS[db]["timeout"], headers)
            st["saigo"] = time.time()
            if kakusu_mono:
                text, why = [x.replace(kakusu_mono, OA_KEY_MASK) if isinstance(x, str) else x for x in (text, why)]
            if s == "kotowari" and waku_tsukita(db, hd):
                st.update(tsukita=utc_day(), kagi=bool(kakusu_mono))
                return None, "waku_nashi", "1日の枠が尽きた(HTTP 429・残り 0)。その日はもう送らない(枠は日本時間の朝9時に戻る)", hd, naoshi
            if s == "kotowari" and naoshi < len(MATSU[db]):
                time.sleep(MATSU[db][naoshi])
                naoshi += 1
                continue
            return text, s, why, hd, naoshi


def txt(v):
    if v is None:
        return ""
    if isinstance(v, list):
        return "・".join(x for x in (txt(i) for i in v) if x)
    if isinstance(v, dict):
        return txt(v.get("@value"))
    return str(v).strip()


def year_of(s):
    m = re.search(r"(1[89]\d\d|20\d\d)", s or "")
    return m.group(1) if m else ""


def crid_of(url):
    m = re.search(r"cir\.nii\.ac\.jp/crid/(\d+)", url or "")
    return m.group(1) if m else ""


def jstage_of(url):
    m = re.search(r"jstage\.jst\.go\.jp/article/([^?#]+?)/_(?:article|pdf)", url or "")
    return m.group(1) if m else ""


def doi_of(s):
    m = re.search(r"(10\.\d{4,9}/[^\s\"<>|]+)", s or "")
    return m.group(1).rstrip(".,;)") if m else ""


def kaken_of(url):
    m = re.search(r"kaken\.nii\.ac\.jp/(?:[a-z]{2}/)?grant/([A-Za-z0-9-]+)", url or "")
    return m.group(1) if m else ""


# ---- DB ごとの読み取り(→ 件数 or None, 候補の並び, 警告) ----

def url_cinii(a):
    q = {"q": a.q, "format": "json", "count": a.kazu, "start": a.start}
    if a.frm:
        q["from"] = a.frm
    if a.until:
        q["until"] = a.until
    return "https://cir.nii.ac.jp/opensearch/%s?%s" % (a.hoho, urllib.parse.urlencode(q))


def parse_cinii(text):
    d = json.loads(text)
    tot = str(d.get("opensearch:totalResults", ""))
    items = []
    for it in d.get("items") or []:
        cre = it.get("dc:creator") or []
        cre = cre if isinstance(cre, list) else [cre]
        doi = ""
        for idf in it.get("dc:identifier") or []:
            if isinstance(idf, dict) and idf.get("@type") == "cir:DOI":
                doi = txt(idf)
        url = txt(it.get("@id")) or txt((it.get("link") or {}).get("@id"))
        sp, ep = txt(it.get("prism:startingPage")), txt(it.get("prism:endingPage"))
        items.append({"dai": txt(it.get("title")), "chosha": [txt(c) for c in cre if txt(c)],
                      "nen": year_of(txt(it.get("prism:publicationDate"))), "shi": txt(it.get("prism:publicationName")),
                      "maki": txt(it.get("prism:volume")), "gou": txt(it.get("prism:number")),
                      "peji": "-".join(x for x in (sp, ep) if x), "shuppan": txt(it.get("dc:publisher")),
                      "shubetsu": txt(it.get("dc:type")), "url": url, "doi": doi, "crid": crid_of(url)})
    return (int(tot) if tot.isdigit() else None), items, []


NS = {"dc": "http://purl.org/dc/elements/1.1/", "dcndl": "http://ndl.go.jp/dcndl/terms/",
      "os": "http://a9.com/-/spec/opensearchrss/1.0/", "dcterms": "http://purl.org/dc/terms/",
      "rdfs": "http://www.w3.org/2000/01/rdf-schema#", "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
      "xsi": "http://www.w3.org/2001/XMLSchema-instance"}


def url_ndl(a):
    q = {("title" if a.hoho == "title" else "any"): a.q, "cnt": a.kazu, "idx": a.start}
    if a.frm:
        q["from"] = a.frm
    if a.until:
        q["until"] = a.until
    return "https://ndlsearch.ndl.go.jp/api/opensearch?" + urllib.parse.urlencode(q)


def parse_ndl(text):
    root = ET.fromstring(text)
    ch = root.find("channel")
    if ch is None:
        raise ValueError("RSS の channel が無い")
    tot = (ch.findtext("os:totalResults", default="", namespaces=NS) or "").strip()
    items = []
    for it in ch.findall("item"):
        link = (it.findtext("link") or "").strip()
        names = [x.text.strip() for x in it.findall("dc:creator", NS) if x.text and x.text.strip()]
        issued = it.findtext("dcterms:issued", default="", namespaces=NS) or it.findtext("dc:date", default="", namespaces=NS)
        desc = " ".join((x.text or "") for x in it.findall("dc:description", NS))
        doi, mo = "", []
        for x in it.findall("dc:identifier", NS):
            if "DOI" in (x.get("{%s}type" % NS["xsi"]) or "") and x.text:
                doi = doi_of(x.text) or x.text.strip()
        for x in it.findall("rdfs:seeAlso", NS):
            c = crid_of(x.get("{%s}resource" % NS["rdf"]) or "")
            if c:
                mo.append(c)
        m = re.search(r"掲載誌[:：]\s*([^/\n]+)", desc)
        m2 = re.search(r"R\d+-I\w+", link)
        items.append({"dai": (it.findtext("dc:title", default="", namespaces=NS) or it.findtext("title") or "").strip(),
                      "chosha": names, "nen": year_of(issued), "shi": m.group(1).strip() if m else "",
                      "shuppan": "・".join(x.text.strip() for x in it.findall("dc:publisher", NS) if x.text),
                      "shubetsu": "・".join((x.text or "").strip() for x in it.findall("category")),
                      "url": link, "doi": doi, "crid_mo": mo, "ndl": m2.group(0) if m2 else ""})
    return (int(tot) if tot.isdigit() else None), items, []


def url_jstage(a):
    if a.hoho == "global":
        return "https://www.jstage.jst.go.jp/result/global/-char/ja?" + urllib.parse.urlencode({"globalSearchKey": a.q})
    q = {"item": JSTAGE_ITEM[a.hoho], "word": a.q}
    if a.frm:
        q["yearfrom"] = a.frm[:4]
    if a.until:
        q["yearto"] = a.until[:4]
    return "https://www.jstage.jst.go.jp/search/global/_search/search/-char/ja?" + urllib.parse.urlencode(q)


def strip_tags(s):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", s or "")).split())


def parse_jstage(text):
    m = re.search(r"([\d,]+)\s*件中", text)
    parts = text.split('<div class="searchlist-title">')[1:]
    items = []
    for li in parts:
        tm = re.search(r'<a href="([^"]+)"[^>]*title="([^"]*)"', li)
        au = re.search(r'searchlist-authortags[^>]*title="([^"]*)"', li)
        inf = re.search(r'searchlist-additional-info">(.*?)</div>', li, re.S)
        info = strip_tags(inf.group(1)) if inf else ""
        shi = re.search(r'searchlist-additional-info">\s*<a[^>]*>([^<]*)</a>', li)
        dm = re.search(r'result-doi-wrap.*?href="https?://doi\.org/([^"]+)"', li, re.S)
        url = html.unescape(tm.group(1)) if tm else ""
        vm = re.search(r"(\S+)\s*巻", info)
        gm = re.search(r"(\S+)\s*号", info)
        pm = re.search(r"p\.\s*(\S+)", info)
        items.append({"dai": html.unescape(tm.group(2)).strip() if tm else "",
                      "chosha": [x.strip() for x in html.unescape(au.group(1)).split(",") if x.strip()] if au else [],
                      "nen": year_of(re.search(r"(\d{4})年", info).group(1)) if re.search(r"(\d{4})年", info) else "",
                      "shi": html.unescape(shi.group(1)).strip() if shi else "",
                      "maki": vm.group(1) if vm else "", "gou": gm.group(1) if gm else "",
                      "peji": pm.group(1) if pm else "",
                      "oa": "フリー" if "freeaccess-tag-style" in li else ("OA" if "openaccess" in li.lower() else ""),
                      "url": url, "doi": html.unescape(dm.group(1)) if dm else "", "jstage": jstage_of(url)})
    if m:
        return int(m.group(1).replace(",", "")), items, []
    return None, items, [KENSU_NASHI_HINT]


def url_kaken(a):
    """科研費の研究課題の OpenSearch(仕様= KAKEN_API_parameters_document_Ja.pdf 2026年3月版)。ID はここでは付けない"""
    q = {"kw": a.q, "format": "xml", "rw": a.kazu, "st": a.start}
    if a.frm or a.until:
        q["o1"] = 3     # 助成の期間が一部でも年の範囲に入る課題(開始の年だけで切ると、範囲をまたぐ課題が落ちるため)
        if a.frm:
            q["s1"] = a.frm[:4]
        if a.until:
            q["s2"] = a.until[:4]
    return "https://kaken.nii.ac.jp/opensearch/?" + urllib.parse.urlencode(q)


XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"


def parse_kaken(text):
    root = ET.fromstring(text)
    if root.tag != "grantAwards":
        raise ValueError("根が grantAwards でない(%s)" % root.tag[:40])
    tot = (root.findtext("totalResults") or "").strip()
    items = []
    for g in root.findall("grantAward"):
        url = (g.findtext("urlList/url") or "").strip()
        sums = g.findall("summary")
        s = next((x for x in sums if x.get(XML_LANG) == "ja"), sums[0] if sums else None)
        if s is None:
            continue
        pi = [(m.findtext("personalName/fullName") or "").strip() for m in s.findall("member")
              if m.get("role") == "principal_investigator"]
        per = s.find("periodOfAward")
        y1, y2 = (per.get("searchStartFiscalYear", ""), per.get("searchEndFiscalYear", "")) if per is not None else ("", "")
        cat = (s.findtext("category") or "").strip()
        items.append({"dai": (s.findtext("title") or "").strip(), "chosha": [x for x in pi if x], "nen": year_of(y1),
                      "shubetsu": "研究課題" + ("(%s)" % cat if cat else ""),
                      "shozoku": (s.findtext("institution") or "").strip(),
                      "kikan": "-".join(x for x in (y1, y2) if x),
                      "url": url, "kaken": kaken_of(url) or g.get("id", "")})
    return (int(tot) if tot.isdigit() else None), items, []


# ---- 英語のデータベースの読み取り(応答の形は 2026-11-02 に実物で確かめた物) ----

OA_SELECT = "id,doi,display_name,publication_year,authorships,primary_location,type,language,open_access,is_retracted,biblio"


def nendo(a):
    return (a.frm or "")[:4], (a.until or "")[:4]


def url_openalex(a):
    """works の検索(search= は題・抄録・本文、title は filter=title.search)。キーは URL に入れない(要求の欄で送る)"""
    q = {"per_page": a.kazu, "page": (a.start - 1) // a.kazu + 1, "select": OA_SELECT}
    f = []
    if a.hoho == "title":
        f.append("title.search:" + a.q.replace(",", " "))
    else:
        q["search"] = a.q
    y1, y2 = nendo(a)
    if y1:
        f.append("from_publication_date:%s-01-01" % y1)
    if y2:
        f.append("to_publication_date:%s-12-31" % y2)
    if f:
        q["filter"] = ",".join(f)
    return "https://api.openalex.org/works?" + urllib.parse.urlencode(q)


def moji(v):
    return str(v).strip() if v is not None else ""


def parse_openalex(text):
    d = json.loads(text)
    tot = (d.get("meta") or {}).get("count")
    items = []
    for w in d.get("results") or []:
        loc = w.get("primary_location") or {}
        src = loc.get("source") or {}
        bib = w.get("biblio") or {}
        oa = w.get("open_access") or {}
        doi = doi_of(w.get("doi") or "")
        it = {"dai": moji(w.get("display_name")),
              "chosha": [moji((x.get("author") or {}).get("display_name")) for x in w.get("authorships") or []
                         if moji((x.get("author") or {}).get("display_name"))],
              "nen": moji(w.get("publication_year")), "shi": moji(src.get("display_name")), "maki": moji(bib.get("volume")),
              "gou": moji(bib.get("issue")), "peji": "-".join(x for x in (moji(bib.get("first_page")), moji(bib.get("last_page"))) if x),
              "shuppan": moji(src.get("host_organization_name")), "shubetsu": moji(w.get("type")),
              "url": ("https://doi.org/" + doi) if doi else (moji(loc.get("landing_page_url")) or moji(w.get("id"))),
              "doi": doi, "gengo": moji(w.get("language")), "oa": ("OA(%s)" % moji(oa.get("oa_status"))) if oa.get("is_oa") else "",
              "oa_url": moji(oa.get("oa_url"))}
        if w.get("is_retracted"):
            it["tekkai"] = "OpenAlex が撤回と返した"
        items.append(it)
    warn = ["撤回された論文が一覧に出た(OpenAlex の is_retracted)。採らない"] if any(x.get("tekkai") for x in items) else []
    return (tot if isinstance(tot, int) else None), items, warn


S2_FIELDS = "title,authors,year,venue,journal,externalIds,publicationTypes,openAccessPdf,url"


def url_semanticscholar(a):
    q = {"query": a.q, "limit": a.kazu, "offset": a.start - 1, "fields": S2_FIELDS}
    y1, y2 = nendo(a)
    if y1 or y2:
        q["year"] = "%s-%s" % (y1, y2)
    return "https://api.semanticscholar.org/graph/v1/paper/search?" + urllib.parse.urlencode(q)


def parse_semanticscholar(text):
    d = json.loads(text)
    tot = d.get("total")
    items = []
    for x in d.get("data") or []:
        ext = x.get("externalIds") or {}
        j = x.get("journal") or {}
        doi = moji(ext.get("DOI"))
        pdf = moji((x.get("openAccessPdf") or {}).get("url"))
        items.append({"dai": moji(x.get("title")), "chosha": [moji(au.get("name")) for au in x.get("authors") or [] if moji(au.get("name"))],
                      "nen": moji(x.get("year")), "shi": moji(j.get("name")) or moji(x.get("venue")), "maki": moji(j.get("volume")),
                      "peji": moji(j.get("pages")), "shubetsu": "・".join(x.get("publicationTypes") or []),
                      "url": ("https://doi.org/" + doi) if doi else moji(x.get("url")), "doi": doi,
                      "oa": "OA" if pdf else "", "oa_url": pdf, "arxiv": moji(ext.get("ArXiv"))})
    return (tot if isinstance(tot, int) else None), items, []


def arxiv_shiki(a):
    """arXiv の検索式。ti・abs・all は語を AND でつなぐ(語を並べただけだと、どれか1語の文献まで出るため)"""
    e = a.q.strip() if a.hoho == "shiki" else " AND ".join("%s:%s" % (a.hoho, w) for w in a.q.split())
    y1, y2 = nendo(a)
    if y1 or y2:
        e = "(%s) AND submittedDate:[%s01010000 TO %s12312359]" % (e, y1 or "1991", y2 or "2999")
    return e


def url_arxiv(a):
    return "https://export.arxiv.org/api/query?" + urllib.parse.urlencode(
        {"search_query": arxiv_shiki(a), "start": a.start - 1, "max_results": a.kazu})


def arxiv_entries(text):
    root = ET.fromstring(text)
    tot = (root.findtext("os:totalResults", default="", namespaces=ARXIV_NS) or "").strip()
    out = []
    for e in root.findall("a:entry", ARXIV_NS):
        idu = (e.findtext("a:id", default="", namespaces=ARXIV_NS) or "").strip()
        if "/api/errors" in idu:
            raise ValueError("arXiv が誤りの項目を返した(%s)" % " ".join((e.findtext("a:summary", default="", namespaces=ARXIV_NS) or "").split())[:80])
        out.append(e)
    return tot, out


def parse_arxiv(text):
    tot, ents = arxiv_entries(text)
    items = []
    for e in ents:
        f = lambda k: " ".join((e.findtext(k, default="", namespaces=ARXIV_NS) or "").split())  # noqa: E731
        idu = f("a:id")
        aid = re.sub(r"v\d+$", "", idu.rsplit("/abs/", 1)[-1])
        pdf = next((l.get("href") or "" for l in e.findall("a:link", ARXIV_NS) if l.get("title") == "pdf"), "")
        items.append({"dai": f("a:title"), "chosha": [" ".join((x.findtext("a:name", default="", namespaces=ARXIV_NS) or "").split())
                                                    for x in e.findall("a:author", ARXIV_NS)],
                      "nen": year_of(f("a:published")), "shi": f("arxiv:journal_ref"), "shubetsu": "プレプリント",
                      "url": "https://arxiv.org/abs/" + aid, "doi": f("arxiv:doi"), "oa": "OA",
                      "oa_url": pdf.replace("http://", "https://", 1), "arxiv": aid})
    return (int(tot) if tot.isdigit() else None), items, []


CR_SELECT = "DOI,title,author,issued,container-title,volume,issue,page,publisher,type,URL"


def url_crossref(a):
    q = {("query.bibliographic" if a.hoho == "shoshi" else "query"): a.q, "rows": a.kazu, "offset": a.start - 1,
         "select": CR_SELECT}
    y1, y2 = nendo(a)
    f = (["from-pub-date:" + y1] if y1 else []) + (["until-pub-date:" + y2] if y2 else [])
    if f:
        q["filter"] = ",".join(f)
    return "https://api.crossref.org/works?" + urllib.parse.urlencode(q)


def ichi(v):
    return strip_tags(v[0] if isinstance(v, list) and v else (v if isinstance(v, str) else ""))


def parse_crossref(text):
    m = json.loads(text).get("message") or {}
    tot = m.get("total-results")
    items = []
    for w in m.get("items") or []:
        doi = moji(w.get("DOI"))
        dp = ((w.get("issued") or {}).get("date-parts") or [[None]])[0] or [None]
        au = [" ".join(x for x in (moji(z.get("given")), moji(z.get("family"))) if x) or moji(z.get("name")) for z in w.get("author") or []]
        items.append({"dai": ichi(w.get("title")), "chosha": [x for x in au if x], "nen": moji(dp[0]),
                      "shi": ichi(w.get("container-title")), "maki": moji(w.get("volume")), "gou": moji(w.get("issue")),
                      "peji": moji(w.get("page")), "shuppan": moji(w.get("publisher")), "shubetsu": moji(w.get("type")),
                      "url": ("https://doi.org/" + doi) if doi else moji(w.get("URL")), "doi": doi})
    return (tot if isinstance(tot, int) else None), items, []


ADAPTER = {"cinii": (url_cinii, parse_cinii), "ndl": (url_ndl, parse_ndl), "jstage": (url_jstage, parse_jstage),
           "kaken": (url_kaken, parse_kaken), "openalex": (url_openalex, parse_openalex),
           "semanticscholar": (url_semanticscholar, parse_semanticscholar), "arxiv": (url_arxiv, parse_arxiv),
           "crossref": (url_crossref, parse_crossref)}


# ---- 一覧の組み立て ----

def name_key(n):
    return re.sub(r"[,，、.]", "", soroe(n))


def keys_of(c):
    """同じ文献を1つにまとめる鍵。照合の順= DOI → J-STAGE の記事 → CiNii の crid → NDL → 題名+第一著者+年(V3 を和文に組み直した順)。
    KAKEN の研究課題は課題の番号だけで見る(題名と代表者と年が同じ論文と、課題を1つにしないため)"""
    if c.get("kaken"):
        return ["kaken:" + c["kaken"]]
    ks = []
    if c.get("doi"):
        ks.append("doi:" + c["doi"].lower())
    if c.get("arxiv"):
        ks.append("arxiv:" + c["arxiv"].lower())
    if c.get("jstage"):
        ks.append("jstage:" + c["jstage"])
    if c.get("crid"):
        ks.append("crid:" + c["crid"])
    for x in c.get("crid_mo") or []:
        ks.append("crid:" + x)
    if c.get("ndl"):
        ks.append("ndl:" + c["ndl"])
    t, y = soroe(c.get("dai")), c.get("nen") or ""
    a = name_key(c["chosha"][0]) if c.get("chosha") else ""
    if t and a and y:
        ks.append("tay:%s|%s|%s" % (t, a, y))
    return list(dict.fromkeys(ks))


def paths(w):
    return os.path.join(w, KENSAKU), os.path.join(w, KOUHO)


def load(w):
    """→ (検索の並び, 候補 {id: 状態}, 鍵 → id)"""
    ps, pk = paths(w)
    S = read_log(ps, KIND_S)
    sids = {r["id"] for r in S}
    cands, by_key = {}, {}
    for n, r in enumerate(read_log(pk, KIND_K), 1):
        t, cid = r.get("type"), r.get("id")
        if t == "kouho":
            if cid in cands:
                raise Stop("候補の一覧の %d 行目: 同じ番号 %s の候補が2つある" % (n, cid))
            cands[cid] = dict(r, ronten=list(r.get("ronten") or []), kensaku_mo=[], kime=None, kagi=list(r.get("kagi") or []))
            for k in r.get("kagi") or []:
                by_key.setdefault(k, cid)
        elif t in ("mata", "kime"):
            if cid not in cands:
                raise Stop("候補の一覧の %d 行目: 無い候補 %s を指している" % (n, cid))
            c = cands[cid]
            if t == "mata":
                if r.get("ronten") and r["ronten"] not in c["ronten"]:
                    c["ronten"].append(r["ronten"])
                c["kensaku_mo"].append(r.get("kensaku"))
                for k in r.get("kagi") or []:
                    by_key.setdefault(k, cid)
                    c["kagi"].append(k)
            else:
                c["kime"] = r
        else:
            raise Stop("候補の一覧の %d 行目: 知らない種類 %r" % (n, t))
        for s in [r.get("kensaku")] if r.get("kensaku") else []:
            if s not in sids:
                raise Stop("候補の一覧の %d 行目: 検索の記録に無い %s を指している" % (n, s))
    return S, cands, by_key


def next_id(prefix, n, width):
    return "%s%0*d" % (prefix, width, n + 1)


def merge(cands, by_key, items, sid, ronten, kiroku, keiro=None):
    """候補を一覧に入れる行を作る。→ (足す行, 新しい id の並び, 既にある id の並び)"""
    rows, new, old = [], [], []
    n = len(cands)
    for it in items:
        ks = keys_of(it)
        hit = next((by_key[k] for k in ks if k in by_key), None)
        if hit is None:
            # 同じ検索の中で同じ文献が2度出た時も1つにまとめる
            hit = next((r["id"] for r in rows if r["type"] == "kouho" and set(ks) & set(r["kagi"])), None)
        if hit is not None:
            extra = [k for k in ks if k not in by_key]
            row = {"type": "mata", "id": hit, "kensaku": sid, "ronten": ronten, "kagi": extra}
            if keiro:
                row["keiro"] = keiro
            rows.append(row)
            for k in extra:
                by_key[k] = hit
            old.append(hit)
            continue
        cid = next_id("K", n, 4)
        n += 1
        row = {"type": "kouho", "id": cid, "kensaku": sid, "ronten": [ronten], "kiroku": kiroku, "kagi": ks}
        for k in ("dai", "chosha", "nen", "shi", "maki", "gou", "peji", "shuppan", "shubetsu", "oa", "url", "doi",
                  "shozoku", "kikan", "gengo", "oa_url", "tekkai"):
            if it.get(k):
                row[k] = it[k]
        if keiro:
            row["keiro"] = keiro
        rows.append(row)
        for k in ks:
            by_key.setdefault(k, cid)
        new.append(cid)
    return rows, new, old


def state_label(c):
    k = c.get("kime")
    if not k:
        return "未判定"
    if k["kekka"] == "sai":
        return "採った #%d" % k["gyou"]
    if k["kekka"] == "otosu":
        return "落とした %s" % RIYUU[k["riyuu"]]
    return "保留"


def cut(s, n):
    s = str(s or "")
    return s if len(s) <= n else s[:n] + "…"


def show(c):
    """候補の1行。DOI を知っていれば(別の検索や tsuika でまとめた時に分かったものも)URL の後ろに出す"""
    doi = next((k[4:] for k in c.get("kagi") or [] if k.startswith("doi:")), "")
    url = c.get("url") or ""
    tail = " doi:%s" % doi if doi and doi not in url.lower() else ""
    if c.get("kikan"):
        tail += " 期間:%s" % c["kikan"]
    if c.get("oa_url") and c["oa_url"] != url:
        tail += " 無料で読める置き場:%s" % c["oa_url"]
    if c.get("tekkai"):
        tail += " ★撤回(%s)" % c["tekkai"]
    return "%s | %s | %s | %s | %s | %s%s" % (c["id"], c.get("nen") or "----", cut(c.get("dai"), 60),
                                             cut("・".join(c.get("chosha") or []), 24),
                                             cut(c.get("shi") or c.get("shozoku"), 24), url, tail)


# ---- J-STAGE の間合い ----

def jstage_state(w):
    path = os.path.join(w, JSTAGE_STATE)
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def jstage_save(w, d):
    os.makedirs(w, exist_ok=True)
    write_text(os.path.join(w, JSTAGE_STATE), json.dumps(d, ensure_ascii=False))


# ---- 命令 ----

def check_ronten(s):
    if not RONTEN_RE.fullmatch(str(s or "")):
        raise Usage("--ronten は論点の番号(1〜99)で渡す: %r" % s)
    return str(int(s))


def check_url(u):
    if re.search(r"[?&]appid=", u or "", re.I):
        raise Usage("--url に appid を入れない(ID を記録に残さないため)。appid= の無い URL を渡す")
    return u


def cmd_sagasu(a):
    a.db = (a.db or "").strip().lower()
    if a.db not in DBS:
        raise Usage("--db は %s のどれか(ほかの DB は te で手で記録する)" % "・".join(DBS))
    tsukawanai(a.db)
    a.hoho = a.hoho or DBS[a.db]["hoho"][0]
    if a.hoho not in DBS[a.db]["hoho"]:
        raise Usage("%s の --hoho は %s のどれか" % (a.db, "・".join(DBS[a.db]["hoho"])))
    if a.db == "jstage" and a.hoho == "global" and (a.frm or a.until):
        raise Usage("J-STAGE の global(全文検索の型)は年で絞れない。年で絞るなら --hoho zenbun・title・abst を使う")
    if a.db == "jstage" and a.start != 1:
        raise Usage("J-STAGE は --start(2ページ目以降)を扱っていない")
    if not (1 <= a.kazu <= 200):
        raise Usage("--kazu は 1〜200")
    if a.db == "kaken" and a.kazu not in KAKEN_RW:
        raise Usage("KAKEN の --kazu は %s のどれか" % "・".join(map(str, KAKEN_RW)))
    if a.db == "kaken" and any(x and not re.fullmatch(r"\d{4}", x[:4]) for x in (a.frm, a.until)):
        raise Usage("KAKEN の --from・--until は年(YYYY)で渡す")
    if a.db in EIGO and any(x and not re.fullmatch(r"\d{4}", x[:4]) for x in (a.frm, a.until)):
        raise Usage("%s の --from・--until は年(YYYY)で渡す" % a.db)
    if a.kazu > KAZU_MAX.get(a.db, 200):
        raise Usage("%s の --kazu は %d まで" % (a.db, KAZU_MAX[a.db]))
    if a.db in EIGO and (a.start < 1 or (a.start - 1) % a.kazu):
        raise Usage("%s の --start は 1・%d・%d … のどれか(1回の件数ずつ進める)" % (a.db, 1 + a.kazu, 1 + 2 * a.kazu))
    ronten = check_ronten(a.ronten)
    if not (a.q or "").strip():
        raise Usage("--q(検索語)が空")
    aid = appid() if a.db in APPID_DB else None
    key = oa_key() if a.db == "openalex" else None
    load(a.w)               # 記録が壊れていれば、送る前に止める(番号は答えが返ってから、読み直して付ける)
    make_url, parse = ADAPTER[a.db]
    url = make_url(a)       # 記録に残すのは ID の無い URL。ID は取りに行く時だけ付ける
    row = {"type": "kensaku", "id": None, "at": ts(), "ronten": ronten, "db": a.db, "hoho": a.hoho, "go": a.q,
           "shibori": {k: v for k, v in (("from", a.frm), ("until", a.until), ("start", a.start), ("kazu", a.kazu))
                       if v and not (a.db == "jstage" and k in ("start", "kazu"))},
           "url": url, "kiroku": "script", "keikoku": []}
    if a.db in EIGO:
        if a.db == "openalex":
            row["openalex_kagi"] = "あり" if key else "なし"
        text, st, why, hd, naoshi = okuru(a.db, url, {"Authorization": "Bearer " + key} if key else {}, key)
        row["at"] = ts()
        if naoshi:
            row["okurinaoshi"] = naoshi
        if hd.get("x-ratelimit-remaining-usd") is not None:
            row["waku_nokori_usd"] = hd["x-ratelimit-remaining-usd"]
        if st == "yameta":
            row.update(jotai="yameta", kensu=None, deta=0, atarashii=0)
            row["keikoku"].append(why)
            sid = kensaku_dake(a.w, row)
            p("%s %s/%s 「%s」 論点%s: %s。記録に1行残した。ほかの英語の DB に同じ語を送る" % (sid, a.db, a.hoho, a.q, ronten, why))
            return 3
        return sagasu_ato(a, row, ronten, parse, text, st, why)
    js = jstage_state(a.w) if a.db == "jstage" else None
    if js is not None and js.get("kirareta"):
        row.update(jotai="yameta", kensu=None, deta=0, atarashii=0,
                   keikoku=["この回は %s に J-STAGE に接続を切られたので投げていない(締め出しを長引かせないため)" % js["kirareta"]])
        sid = kensaku_dake(a.w, row)
        p("%s jstage/%s 「%s」 論点%s: 投げていない(この回は J-STAGE に切られた後)。記録に1行残した" % (sid, a.hoho, a.q, ronten))
        return 3
    if js is not None and js.get("saigo"):
        try:
            last = datetime.datetime.fromisoformat(js["saigo"])
            wait = JSTAGE_MA - (datetime.datetime.now(last.tzinfo) - last).total_seconds()
            if wait > 0:
                time.sleep(wait)
        except ValueError:
            pass
    text, st, why = fetch(url + "&appid=" + aid if aid else url, DBS[a.db]["timeout"])
    text, why = kakusu(text, aid), kakusu(why, aid)
    row["at"] = ts()
    if js is not None:
        js["saigo"] = row["at"]
        if st == "kirareta":
            js["kirareta"] = row["at"]
        jstage_save(a.w, js)
    return sagasu_ato(a, row, ronten, parse, text, st, why)


def kensaku_dake(w, row):
    """検索の記録に1行だけ足す(候補の無い行)。番号は札を取ってから読み直して付ける。→ 番号"""
    with kakikomi(w):
        S = read_log(paths(w)[0], KIND_S)
        row["id"] = next_id("S", len(S), 3)
        append_log(paths(w)[0], KIND_S, [row])
    return row["id"]


def sagasu_ato(a, row, ronten, parse, text, st, why):
    """応答を読み、記録と候補の一覧に足して画面に出す(どの DB も同じ)。記録と一覧は、札を取ってから読み直して番号を付ける
    (同じ作業用フォルダで別の処理が同時に検索していても、番号がぶつからないように)"""
    kensu, items = None, []
    if text is not None:
        try:
            kensu, items, warn = parse(text)
            row["keikoku"] += warn
        except (ValueError, ET.ParseError, AttributeError, TypeError) as e:
            st, why = "shippai", "応答を読めない(%s: %s)" % (e.__class__.__name__, str(e)[:80])
    if st != "ok":
        row.update(jotai=st, kensu=None, deta=0, atarashii=0)
        row["keikoku"].append(why)
        sid = kensaku_dake(a.w, row)
        p("%s %s/%s 「%s」 論点%s: %s(%s)。記録に1行残した" % (sid, a.db, a.hoho, a.q, ronten, JOTAI_NAME[st], why))
        if st == "kirareta" and a.db == "jstage":
            p("★J-STAGE に接続を切られた。この回は J-STAGE にもう投げない(記事ページ・PDF も開かない)。"
              "書誌の確定は DOI のページか CiNii で行い、J-STAGE だけにある文献は探索記録に残す")
        if st in ("kotowari", "waku_nashi"):
            p("★%s に断られた。ブラウザで開いて代わりに探さず(枠を越えないため)、同じ語をほかの英語の DB に送る" % a.db)
        return 3
    with kakikomi(a.w):
        S, cands, by_key = load(a.w)
        sid = next_id("S", len(S), 3)
        row["id"] = sid
        rows, new, old = merge(cands, by_key, items, sid, ronten, "script")
        jotai = "kensu_nashi" if kensu is None else ("zero" if kensu == 0 else "ok")
        row.update(jotai=jotai, kensu=kensu, deta=len(items), atarashii=len(new))
        append_log(paths(a.w)[0], KIND_S, [row])
        append_log(paths(a.w)[1], KIND_K, rows)
    head = "件数の表示なし" if kensu is None else "%d件" % kensu
    p("%s %s/%s 「%s」 論点%s: %s(一覧に出た %d件・新しい候補 %d件・既にある候補 %d件)"
      % (sid, a.db, a.hoho, a.q, ronten, head, len(items), len(new), len(set(old))))
    for w in row["keikoku"]:
        p("  ★" + w)
    _, cands2, _ = load(a.w)
    for cid in new:
        p("  " + show(cands2[cid]))
    for cid in dict.fromkeys(old):
        p("  (既にある)%s [%s]" % (show(cands2[cid]), state_label(cands2[cid])))
    return 0


SHOROKU = "shoroku"


def oa_shoroku(inv):
    """OpenAlex の抄録(語 → 位置の並び)を文に戻す"""
    pos = [(i, w) for w, idx in (inv or {}).items() for i in idx if isinstance(i, int)]
    return " ".join(w for _, w in sorted(pos))


def yomu_s2(text):
    d = json.loads(text)
    return moji(d.get("title")), " ".join(moji(d.get("abstract")).split())


def yomu_oa(text):
    d = json.loads(text)
    return moji(d.get("display_name")), oa_shoroku(d.get("abstract_inverted_index"))


def yomu_cr(text):
    m = json.loads(text).get("message") or {}
    sho = strip_tags(m.get("abstract") or "")
    return ichi(m.get("title")), re.sub(r"^(Abstract|ABSTRACT)\s+", "", sho)


def yomu_arxiv(text):
    _, ents = arxiv_entries(text)
    if not ents:
        return "", ""
    f = lambda k: " ".join((ents[0].findtext(k, default="", namespaces=ARXIV_NS) or "").split())  # noqa: E731
    return f("a:title"), f("a:summary")


def cmd_shoroku(a):
    if bool(a.doi) == bool(a.arxiv):
        raise Usage("--doi か --arxiv のどちらか1つを渡す")
    if a.arxiv:
        name = re.sub(r"v\d+$", "", a.arxiv.strip())
        tries = [("arxiv", "https://export.arxiv.org/api/query?" + urllib.parse.urlencode({"id_list": name}), yomu_arxiv)]
        mei = "arXiv: " + name
    else:
        name = doi_of(a.doi) or a.doi.strip()
        q = urllib.parse.quote(name, safe="/")
        tries = [("semanticscholar", "https://api.semanticscholar.org/graph/v1/paper/DOI:%s?fields=title,abstract" % q, yomu_s2),
                 ("openalex", "https://api.openalex.org/works/doi:%s?select=display_name,abstract_inverted_index" % q, yomu_oa),
                 ("crossref", "https://api.crossref.org/works/%s" % q, yomu_cr)]
        mei = "DOI: " + name
    tsukau = tsukau_db()
    if not [t for t in tries if t[0] in tsukau]:
        raise Usage("抄録を取るデータベース(%s)が、どれも設定(環境変数 %s)で外されている。抄録はページを開いて読む"
                    % ("・".join(t[0] for t in tries), TSUKAU_NAME))
    tries = [t for t in tries if t[0] in tsukau]
    key = oa_key()
    notes = []
    for db, url, yomu in tries:
        k = key if db == "openalex" else None
        text, st, why, _hd, _n = okuru(db, url, {"Authorization": "Bearer " + k} if k else {}, k)
        if st != "ok":
            notes.append("%s %s(%s)" % (db, JOTAI_NAME.get(st, st), why))
            continue
        try:
            dai, sho = yomu(text)
        except (ValueError, ET.ParseError, AttributeError, TypeError) as e:
            notes.append("%s 応答を読めない(%s)" % (db, e.__class__.__name__))
            continue
        if not sho:
            notes.append("%s 抄録が無い" % db)
            continue
        out = os.path.join(a.w, SHOROKU, re.sub(r"[^A-Za-z0-9._-]", "_", name) + ".txt")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        body = "出どころ: %s\n取った時刻: %s\n%s\n題名: %s\n\n%s\n" % (url, ts(), mei, dai, sho)
        write_text(out, body)
        if notes:
            p("(先に試した所: %s)" % " / ".join(notes))
        p("抄録を保存した: %s(出どころ= %s)\n題名: %s\n%s" % (out, db, dai, sho))
        if db == "semanticscholar":
            p("★Semantic Scholar から取った。台帳の探索記録の「使ったAPIと出典」に次の行を写す: - %s" % SHUSSHO["semanticscholar"])
        return 0
    p("抄録を取れなかった(%s): %s" % (mei, " / ".join(notes)))
    return 3


def shoroku_s2(w):
    """作業用フォルダの抄録のうち、Semantic Scholar から取った物の名前"""
    d = os.path.join(w, SHOROKU)
    out = []
    for n in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        try:
            with open(os.path.join(d, n), encoding="utf-8") as f:
                if f.readline().startswith("出どころ: https://api.semanticscholar.org/"):
                    out.append(n)
        except OSError:
            pass
    return out


def cmd_tsukau(a):
    have = tsukau_db()
    v = settei(TSUKAU_NAME)
    p("使うデータベース: %s(%s)" % ("・".join(have), ("設定 %s" % TSUKAU_NAME) if (v or "").strip() else "設定なし。全部使う"))
    nai = [x for x in DBS if x not in have]
    if nai:
        p("設定で外した(送らない。ブラウザや手の検索でも開かない): %s" % "・".join(nai))
    return 0


def cmd_settei(a):
    """スキルの設定ファイルの置き場と、どの名前がどこから読めるかを出す(値は出さない)。無ければひな形を作る"""
    path = settei_path()
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        write_text(path, json.dumps({APPID_NAME: "", OA_KEY_NAME: "", TSUKAU_NAME: ""}, ensure_ascii=False, indent=2) + "\n")
        if os.name != "nt":
            os.chmod(path, 0o600)              # ID とキーを書くので、本人だけが読める形にする
        p("スキルの設定ファイルのひな形を作った: %s" % path)
    else:
        p("スキルの設定ファイル: %s" % path)
    d = settei_file()
    for n in (APPID_NAME, OA_KEY_NAME, TSUKAU_NAME):
        if os.environ.get(n) is not None:
            src = "この端末の環境変数から読む"
        elif d.get(n) not in (None, ""):
            src = "設定ファイルから読む"
        elif sys.platform == "win32" and user_env(n):
            src = "Windows のアカウントの環境変数から読む"
        else:
            src = "置いていない"
        p("  %s: %s" % (n, src))
    p("値は画面に出さない。ID とキーは、使う人がこのファイルをエディタで開いて書く(チャットに貼らない)。"
      "%s は使うデータベースを「openalex,crossref」のようにカンマで並べる(空なら全部使う)" % TSUKAU_NAME)
    return 0


def cmd_te(a):
    ronten = check_ronten(a.ronten)
    if not (a.db or "").strip() or not (a.q or "").strip():
        raise Usage("--db と --q が要る")
    if a.db.strip().lower() in DBS:
        a.db = a.db.strip().lower()             # 「CiNii」のように大文字を混ぜても、外したデータベースの関門をすり抜けないように
    tsukawanai(a.db)
    if a.db in DBS and not a.memo:
        raise Usage("%s はスクリプトで検索できる。手で記録するなら --memo に理由を書く(例「Chat の環境で接続できない」)" % a.db)
    jotai = a.jotai or ("shippai" if a.kensu is None else ("zero" if a.kensu == 0 else "ok"))
    if jotai in ("ok", "zero") and a.kensu is None:
        raise Usage("--jotai %s なら --kensu(件数)が要る" % jotai)
    check_url(a.url)
    S, _, _ = load(a.w)
    sid = next_id("S", len(S), 3)
    row = {"type": "kensaku", "id": sid, "at": ts(), "ronten": ronten, "db": a.db, "hoho": a.hoho or "", "go": a.q,
           "shibori": {}, "url": a.url or "", "kiroku": "te", "jotai": jotai, "kensu": a.kensu, "deta": 0,
           "atarashii": 0, "keikoku": [], "memo": a.memo or ""}
    append_log(paths(a.w)[0], KIND_S, [row])
    p("%s %s 「%s」 論点%s: %s を手で記録した(印= 手で記録)。採否を決める候補は tsuika で一覧に足す"
      % (sid, a.db, a.q, ronten, ("%s件" % a.kensu) if a.kensu is not None else JOTAI_NAME[jotai]))
    return 0


def cmd_tsuika(a):
    ronten = check_ronten(a.ronten)
    if not (a.dai or "").strip() or not (a.url or "").strip() or not (a.keiro or "").strip():
        raise Usage("--dai・--url・--keiro(どうたどり着いたか)が要る")
    check_url(a.url)
    tsukawanai_url(a.url)
    S, cands, by_key = load(a.w)
    if a.kensaku and a.kensaku not in {r["id"] for r in S}:
        raise Usage("検索の記録に %s が無い" % a.kensaku)
    it = {"dai": a.dai, "url": a.url, "doi": a.doi or doi_of(a.url), "chosha": a.chosha or [], "nen": a.nen or "",
          "shi": a.shi or "", "crid": crid_of(a.url), "jstage": jstage_of(a.url), "kaken": kaken_of(a.url)}
    rows, new, old = merge(cands, by_key, [it], a.kensaku, ronten, "te", keiro=a.keiro)
    append_log(paths(a.w)[1], KIND_K, rows)
    _, cands2, _ = load(a.w)
    if new:
        p("一覧に足した(印= 手で足した): " + show(cands2[new[0]]))
    else:
        p("既に一覧にある: %s [%s](論点%s と経路を書き足した)" % (show(cands2[old[0]]), state_label(cands2[old[0]]), ronten))
    return 0


def cmd_kime(a):
    _, cands, _ = load(a.w)
    c = cands.get(a.id)
    if c is None:
        raise Usage("一覧に %s が無い(ichiran で番号を見る)" % a.id)
    row = {"type": "kime", "id": a.id, "kekka": a.kekka, "at": ts()}
    kimete = (a.kimete or "").strip()
    if len(kimete) > KIMETE_MAX:
        raise Usage("--kimete は %d 字まで(いま %d 字)" % (KIMETE_MAX, len(kimete)))
    if a.kekka == "sai":
        if not a.gyou or a.gyou < 1:
            raise Usage("sai には --gyou(台帳の行番号 #)が要る")
        if c.get("tekkai"):
            raise Usage("%s は撤回された論文(%s)なので採らない(D75)。落とすなら otosu --riyuu 2 --kimete \"撤回された論文\""
                        % (a.id, c["tekkai"]))
        other = [x["id"] for x in cands.values() if x["id"] != a.id and x.get("kime")
                 and x["kime"]["kekka"] == "sai" and x["kime"]["gyou"] == a.gyou]
        if other:
            raise Usage("台帳の #%d は %s が採っている。同じ文献の別の記録なら otosu --riyuu 1 --kimete \"#%d と同じ論文\""
                        % (a.gyou, other[0], a.gyou))
        row["gyou"] = a.gyou
    elif a.kekka == "otosu":
        if a.riyuu not in RIYUU:
            raise Usage("otosu には --riyuu 1〜5 が要る(%s)" % "・".join(RIYUU.values()))
        if not kimete:
            raise Usage("otosu には --kimete(決め手の事実。例「対象が韓国の農村」)が要る")
        row["riyuu"] = a.riyuu
    else:
        if not kimete:
            raise Usage("horyu には --kimete(何が決まらないか)が要る")
    if kimete:
        row["kimete"] = kimete
    if a.ronten:
        row["ronten"] = [check_ronten(x) for x in a.ronten.split(",") if x.strip()]
    prev = state_label(c)
    append_log(paths(a.w)[1], KIND_K, [row])
    _, cands2, _ = load(a.w)
    p("%s: %s%s" % (a.id, state_label(cands2[a.id]), "" if prev == "未判定" else "(前の判定「%s」を置き換えた)" % prev))
    return 0


def belongs(c):
    k = c.get("kime")
    return list(k["ronten"]) if k and k.get("ronten") else list(c["ronten"])


def cmd_ichiran(a):
    _, cands, _ = load(a.w)
    rs = [c for c in cands.values() if (not a.ronten or check_ronten(a.ronten) in belongs(c))
          and (not a.mada or not c.get("kime") or c["kime"]["kekka"] == "horyu")]
    for c in rs:
        p("%s [%s] 論点%s" % (show(c), state_label(c), ",".join(belongs(c))))
    p("(%d件)" % len(rs))
    return 0


def tally(S, cands, labels=None, soe=None):
    """論点ごとの帳尻の行を作る。→ 行の並び"""
    labels, soe = labels or {}, soe or {}
    nums = set(labels) | {r["ronten"] for r in S} | {x for c in cands.values() for x in belongs(c)}
    lines = []
    for r in sorted(nums, key=int):
        ss = [s for s in S if s["ronten"] == r]
        te = sum(1 for s in ss if s.get("kiroku") == "te")
        bad = sum(1 for s in ss if s.get("jotai") in SHIPPAI)
        hit = sum(s["kensu"] for s in ss if isinstance(s.get("kensu"), int))
        cs = [c for c in cands.values() if r in belongs(c)]
        sai = sorted({c["kime"]["gyou"] for c in cs if c.get("kime") and c["kime"]["kekka"] == "sai"})
        n_sai = sum(1 for c in cs if c.get("kime") and c["kime"]["kekka"] == "sai")
        ot = [c["kime"]["riyuu"] for c in cs if c.get("kime") and c["kime"]["kekka"] == "otosu"]
        ho = sum(1 for c in cs if c.get("kime") and c["kime"]["kekka"] == "horyu")
        mita = n_sai + len(ot)
        mada = len(cs) - mita - ho
        extra = []
        if te:
            extra.append("手で記録 %d" % te)
        if bad:
            extra.append("失敗・件数なし %d" % bad)
        head = labels.get(r, "論点%s" % r) + ": "
        if soe.get(r):
            head += soe[r] + " / "
        riyuu = "・".join("%s %d" % (RIYUU[k], ot.count(k)) for k in sorted(set(ot)))
        lines.append("- %s検索%d本%s・ヒット計 %d件(重なりを含む) / 一覧に出た %d件 / 見た %d件 / 採った %d件%s / "
                     "落とした %d件%s / 保留 %d件(保留の割合 %d%%) / 未判定 %d件"
                     % (head, len(ss), "(%s)" % "・".join(extra) if extra else "", hit, len(cs), mita, n_sai,
                        "(%s)" % "・".join("#%d" % g for g in sai) if sai else "", len(ot),
                        "(%s)" % riyuu if riyuu else "", ho, round(100 * ho / (mita + ho)) if mita + ho else 0, mada))
    allc = list(cands.values())
    n_sai = sum(1 for c in allc if c.get("kime") and c["kime"]["kekka"] == "sai")
    n_ot = sum(1 for c in allc if c.get("kime") and c["kime"]["kekka"] == "otosu")
    n_ho = sum(1 for c in allc if c.get("kime") and c["kime"]["kekka"] == "horyu")
    te_c = sum(1 for c in allc if c.get("kiroku") == "te")
    lines.append("- 全体(重なりを除く): 検索%d本(手で記録 %d・失敗・件数なし %d) / 一覧に出た %d件(うち手で足した %d) / "
                 "見た %d件 / 採った %d件 / 落とした %d件 / 保留 %d件 / 未判定 %d件"
                 % (len(S), sum(1 for s in S if s.get("kiroku") == "te"), sum(1 for s in S if s.get("jotai") in SHIPPAI),
                    len(allc), te_c, n_sai + n_ot, n_sai, n_ot, n_ho, len(allc) - n_sai - n_ot - n_ho))
    return lines


def section(lines):
    return ["## 選別の帳尻", "",
            "数は候補の一覧からスクリプトが数えた(kensaku.py chojiri・%s)。一覧に入るのは、各検索で画面に出た上位の候補と、手で足した候補だけ。" % ts(),
            ""] + lines + [""]


def put_section(text, sec):
    lines = text.split("\n")
    start = next((i for i, ln in enumerate(lines) if ln.strip() == "## 選別の帳尻"), None)
    if start is not None:
        end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
        return "\n".join(lines[:start] + sec + lines[end:])
    at = next((i for i, ln in enumerate(lines) if ln.startswith("## 探索記録")), None)
    if at is None:
        return text.rstrip("\n") + "\n\n" + "\n".join(sec)
    return "\n".join(lines[:at] + sec + lines[at:])


def parse_soe(items):
    out = {}
    for s in items or []:
        m = re.fullmatch(r"\s*(\d+)\s*=\s*(.+)", s)
        if not m:
            raise Usage("--soe は「番号=文」の形: %r" % s)
        out[str(int(m.group(1)))] = m.group(2).strip()
    return out


def cmd_chojiri(a):
    S, cands, _ = load(a.w)
    d = read_daicho(a.daicho) if a.daicho else None
    lines = tally(S, cands, d["ronten"] if d else None, parse_soe(a.soe))
    sec = section(lines)
    if d:
        write_text(a.daicho, put_section(d["text"], sec))
        p("台帳の「## 選別の帳尻」を書いた: %s" % a.daicho)
    p("\n".join(sec))
    return 0


def shussho_iru(S, cands):
    """探索記録に要る「使ったAPIと出典」の行。→ [(鍵, 要る理由)]"""
    out = []
    if any(s["db"] == "ndl" and s.get("kiroku") == "script" and s.get("jotai") in ("ok", "zero") for s in S):
        out.append(("ndl", "NDLサーチの API が答えを返した検索がある"))
    if (any(s["db"] == "kaken" and s.get("jotai") in ("ok", "zero") for s in S)
            or any(k.startswith("kaken:") for c in cands.values() for k in c.get("kagi") or [])):
        out.append(("kaken", "KAKEN の検索か、KAKEN の研究課題の候補がある"))
    if any(s["db"] == "semanticscholar" and s.get("kiroku") == "script" and s.get("jotai") in ("ok", "zero") for s in S):
        out.append(("semanticscholar", "Semantic Scholar の API が答えを返した検索がある"))
    return out


def section_lines(lines, head):
    st = next((i for i, ln in enumerate(lines) if ln.startswith(head)), None)
    if st is None:
        return None
    end = next((i for i in range(st + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    return lines[st + 1:end]


def cmd_tashikame(a):
    S, cands, _ = load(a.w)
    d = read_daicho(a.daicho)
    probs, notes = [], []
    rows = {n for _ln, n, _r in d["rows"]}
    sai = {}
    for c in cands.values():
        k = c.get("kime")
        if k and k["kekka"] == "sai":
            sai.setdefault(k["gyou"], []).append(c["id"])
    for g, ids in sorted(sai.items()):
        if g not in rows:
            probs.append("%s が「採った #%d」としているが、台帳に #%d の行が無い" % ("・".join(ids), g, g))
    for n in sorted(rows - set(sai)):
        probs.append("台帳の #%d は、候補の一覧のどの候補からも採られていない(検索か tsuika で一覧に入れてから kime sai --gyou %d)" % (n, n))
    for r in sorted({s["ronten"] for s in S} | {x for c in cands.values() for x in belongs(c)}, key=int):
        if d["ronten"] and r not in d["ronten"]:
            probs.append("台帳のヘッダーに無い論点%s の検索・候補がある" % r)
    want = [ln for ln in tally(S, cands, d["ronten"]) if ln.startswith("- ")]
    lines = d["lines"]
    st = next((i for i, ln in enumerate(lines) if ln.strip() == "## 選別の帳尻"), None)
    if st is None:
        probs.append("台帳に「## 選別の帳尻」の節が無い(kensaku.py chojiri --daicho で書く)")
    else:
        end = next((i for i in range(st + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
        have = [ln for ln in lines[st + 1:end] if ln.startswith("- ")]
        strip_soe = [re.sub(r"^(- 論点\d+(?:[(（][^)）]*[)）])?: ).*? / (検索\d+本)", r"\1\2", ln) for ln in have]
        if strip_soe != want and have != want:
            probs.append("台帳の帳尻が、候補の一覧から数えた物と違う(手で直したか、判定の後に数え直していない。"
                         "kensaku.py chojiri --daicho で書き直す)")
    tan = section_lines(lines, "## 探索記録")
    iru = shussho_iru(S, cands)
    s2 = shoroku_s2(a.w)
    if s2 and "semanticscholar" not in {k for k, _ in iru}:
        iru.append(("semanticscholar", "Semantic Scholar から取った抄録がある(%s)" % "・".join(s2[:3])))
    for key, why in iru:
        if tan is None or not any(SHUSSHO[key] in ln for ln in tan):
            probs.append("%sのに、台帳の探索記録に次の行が無い(daicho-format.md「使ったAPIと出典の行」。"
                         "「### 使ったAPIと出典」の下にそのまま写す): - %s" % (why, SHUSSHO[key]))
    mada = sum(1 for c in cands.values() if not c.get("kime"))
    ho = sum(1 for c in cands.values() if c.get("kime") and c["kime"]["kekka"] == "horyu")
    notes.append("検索 %d本(手で記録 %d)・候補 %d件・保留 %d件・未判定 %d件・台帳の行 %d行"
                 % (len(S), sum(1 for s in S if s.get("kiroku") == "te"), len(cands), ho, mada, len(rows)))
    for n in notes:
        p(n)
    if probs:
        for x in probs:
            p("✕ " + x)
        return 1
    p("記録の指紋・判定・台帳の行と帳尻: 食い違いなし")
    return 0


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="文献台帳の検索の記録と候補の一覧")
    ap.add_argument("w", help="作業用フォルダ")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sagasu")
    s.add_argument("--db", required=True)
    s.add_argument("--q", required=True)
    s.add_argument("--ronten", required=True)
    s.add_argument("--hoho")
    s.add_argument("--from", dest="frm")
    s.add_argument("--until")
    s.add_argument("--kazu", type=int, default=20)
    s.add_argument("--start", type=int, default=1)
    t = sub.add_parser("te")
    t.add_argument("--db", required=True)
    t.add_argument("--q", required=True)
    t.add_argument("--ronten", required=True)
    t.add_argument("--kensu", type=int)
    t.add_argument("--jotai", choices=("ok", "zero", "shippai", "kensu_nashi"))
    t.add_argument("--hoho")
    t.add_argument("--url")
    t.add_argument("--memo")
    u = sub.add_parser("tsuika")
    u.add_argument("--ronten", required=True)
    u.add_argument("--dai", required=True)
    u.add_argument("--url", required=True)
    u.add_argument("--keiro", required=True)
    u.add_argument("--kensaku")
    u.add_argument("--doi")
    u.add_argument("--chosha", nargs="*")
    u.add_argument("--nen")
    u.add_argument("--shi")
    k = sub.add_parser("kime")
    k.add_argument("id")
    k.add_argument("kekka", choices=tuple(KEKKA))
    k.add_argument("--gyou", type=int)
    k.add_argument("--riyuu", type=int)
    k.add_argument("--kimete")
    k.add_argument("--ronten")
    i = sub.add_parser("ichiran")
    i.add_argument("--ronten")
    i.add_argument("--mada", action="store_true")
    c = sub.add_parser("chojiri")
    c.add_argument("--daicho")
    c.add_argument("--soe", action="append")
    m = sub.add_parser("tashikame")
    m.add_argument("--daicho", required=True)
    sub.add_parser("tsukau")
    sub.add_parser("settei")
    r = sub.add_parser("shoroku")
    r.add_argument("--doi")
    r.add_argument("--arxiv")
    a = ap.parse_args(argv)
    try:
        if a.cmd != "tashikame" and not os.path.isdir(a.w):
            os.makedirs(a.w, exist_ok=True)
        fn = {"sagasu": cmd_sagasu, "te": cmd_te, "tsuika": cmd_tsuika, "kime": cmd_kime, "ichiran": cmd_ichiran,
              "chojiri": cmd_chojiri, "tashikame": cmd_tashikame, "shoroku": cmd_shoroku, "tsukau": cmd_tsukau, "settei": cmd_settei}[a.cmd]
        if a.cmd in ("te", "tsuika", "kime"):       # 読んで足すまでを1つの処理だけに(sagasu は答えが返ってから札を取る)
            with kakikomi(a.w):
                return fn(a)
        return fn(a)
    except Usage as e:
        p("使い方の誤り: %s" % e)
        return 2
    except Stop as e:
        p("✕ 止めた: %s" % e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
