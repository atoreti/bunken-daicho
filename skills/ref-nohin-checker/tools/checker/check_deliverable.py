# -*- coding: utf-8 -*-
"""自作スキルの納品物が、各スキルのSKILL.md・referencesに書かれた規則に適合するかの機械照合。

対象: uradori出典台帳 / bunken-daicho文献台帳 / ronbun-shippitsu原稿 / html-visualizer成果物
規則の一覧と原典(file:line)は同フォルダの deliverable-rules.md、実装上の正は本ファイルの RULES 定義。
`--list-rules` で現在の実装が持つ規則を出力できる(規則表とのドリフト検知用)。

使い方:
  python check_deliverable.py <file> [<file> ...]
  python check_deliverable.py 台帳.md --type uradori
  python check_deliverable.py out.html --type html --artifact   # ★原典が書いている正規形
  python check_deliverable.py 断片.md --artifact                # ★拡張子が .html でなくても html として検査
  python check_deliverable.py out.html --expect-count 8 --count-pattern 'class="idea-card"'
  python check_deliverable.py --list-rules

終了コード: 違反(✕)が1件でもあれば 1。
           違反は無いが検査不能(▲)が1件でもあれば 3(★段5・2026-08-19 に繋いだ)。
           どちらも無ければ 0。要目視(△)・未検査(―)は終了コードに影響させない。
           ★3 は「検査できなかった項目が残っている」であって「違反が無かった」ではない
           (4スキルの SKILL.md に受け取り方を明記済み。0 以外なら納品しない)。

設計方針: 違反ゼロのときも「何を検査したか」を全項目分出力する。
         人間の解釈が要る項目は判定せず、△(要目視)または ―(未検査)として理由つきで残す。
"""
import argparse
import contextlib
import os
import re
import sys
from html.parser import HTMLParser

sys.stdout.reconfigure(encoding="utf-8")
# ★★2026-08-23 に足した。**stderr だけ既定の文字コード(Windows では cp932)のままだった。**
#   ⇒ 引数エラー・未捕捉の例外など**エラーの側の出力だけが文字化けして読めなくなる**。
#   ★現に踏んだ: `--type ronbun --artifact` の食い違いを落とす工事で、
#     エラー文が読めているかを確かめる常設テストが**エラー文を読めずに落ちた**。
#   ★この体系の言い方をすれば —— **stdout(合格の側)は整えて stderr(失敗の側)は放置していた。**
#     出力を1本にまとめて拾う呼び出し(corpus_run.py など)では、
#     **同じ1本の中で文字コードが2つ混ざる**ことになる。
sys.stderr.reconfigure(encoding="utf-8")

# ---------------------------------------------------------------- 規則メタデータ
# level: "ng"=違反として数える / "gray"=要目視(自動判定しない) / "info"=未検査になりうる補助
# origin: 原典の file:line。ここを空にした規則を追加しない(検証規律)。
RULES = [
    # ---- uradori 出典台帳 ----
    ("U-0",  "uradori", "台帳が機械照合できる形である(検査不能が残っていない)",
     "run-uradori/SKILL.md:90, run-uradori/references/daicho-format.md:23", "ng"),
    ("U-1",  "uradori", "リンク全行必須",                 "run-uradori/SKILL.md:15, run-uradori/references/daicho-format.md:35", "ng"),
    ("U-2",  "uradori", "ヘッダーブロック4項目",           "run-uradori/references/daicho-format.md:7-15", "ng"),
    ("U-3",  "uradori", "必須列の存在(水準依存)",          "run-uradori/references/daicho-format.md:28-40", "ng"),
    ("U-4",  "uradori", "判定語は5語のみ",                 "run-uradori/SKILL.md:80, run-uradori/references/daicho-format.md:33", "ng"),
    ("U-5",  "uradori", "判定サマリーの存在・件数一致",     "run-uradori/SKILL.md:86, run-uradori/references/daicho-format.md:133-138", "ng"),
    ("U-6",  "uradori", "凡例(判定)が5語すべて・サマリー直後", "run-uradori/references/daicho-format.md:149, run-uradori/references/daicho-format.md:156, run-uradori/references/daicho-format.md:160, run-uradori/SKILL.md:86, run-uradori/references/daicho-format.md:152", "ng"),
    ("U-7",  "uradori", "凡例(分類)が登場分類を網羅",       "run-uradori/references/daicho-format.md:153, run-uradori/references/daicho-format.md:156", "ng"),
    ("U-8",  "uradori", "探索記録セクション・次の一手",     "run-uradori/SKILL.md:86, run-uradori/references/daicho-format.md:158-173", "ng"),
    ("U-9",  "uradori", "具体値の格上げ禁止(条件付きは逐語で支える)", "run-uradori/SKILL.md:78, run-uradori/references/daicho-format.md:131", "ng"),
    ("U-10", "uradori", "条件付き裏付けは備考に条件を記載", "run-uradori/SKILL.md:71, run-uradori/references/daicho-format.md:124", "ng"),
    ("U-11", "uradori", "反証は逐語を添える",              "run-uradori/references/daicho-format.md:125, run-uradori/references/daicho-format.md:125", "ng"),
    ("U-12", "uradori", "アクセス日(水準③で必須・日付形式)", "run-uradori/references/daicho-format.md:39", "ng"),
    ("U-13", "uradori", "アーカイブのみの行は条件付き止まり", "run-uradori/references/daicho-format.md:186", "ng"),
    ("U-14", "uradori", "未処置が残ったまま「提出可」と書かない",       "run-uradori/references/daicho-format.md:145, run-uradori/references/daicho-format.md:127", "ng"),
    ("U-15", "uradori", "水準③: 裏付け行の逐語が空でない",           "run-uradori/SKILL.md:26, run-uradori/references/daicho-format.md:37", "ng"),
    ("U-16", "uradori", "水準③: 裏付けの格付け(一次)を備考に書く",   "run-uradori/SKILL.md:26, run-uradori/references/source-hierarchy.md:12, run-uradori/references/source-hierarchy.md:27", "ng"),
    ("U-17", "uradori", "到達範囲(本文到達/抄録どまり)の記載",       "run-uradori/references/daicho-format.md:38, run-uradori/references/daicho-format.md:73", "ng"),
    ("U-18", "uradori", "対象範囲の実体(受領と抽出)の開示",         "run-uradori/references/daicho-format.md:75, run-uradori/SKILL.md:33", "ng"),
    ("U-19", "uradori", "格付けの宣言とリンクの内部矛盾",           "run-uradori/references/source-hierarchy.md:30, run-uradori/references/source-hierarchy.md:40", "ng"),
    # ---- 事実の関門【段階A】(2026-08-29・ユーザー裁定)。★リンクが**現に届くか**を叩いて確かめる ----
    #   ★U-1 は「リンクが**在るか**」を見る。★U-20 は「そのリンクが**届くか**」を見る。**別の検査である。**
    #   ★原典は既にこれを求めている(★新しい基準を発明していない)——「実際にアクセスし…台帳に載せる」。
    ("U-20", "uradori", "リンクが現に届く(段階A)",
     "run-uradori/SKILL.md:14-15-16", "ng"),
    # ---- 事実の関門【段階A-3】(2026-08-30・ユーザー裁定133「網まで作る」) ----
    #   ★U-20 は「リンクが**届くか**」を見る。★U-21 は「**その申告が納品物に載ったか**」を見る。
    #   ★★**別の検査である** —— 前者は事実、後者は**その事実が受け手に届く経路に載ったか**。
    # ---- 事実の関門【段階C】(2026-08-31・ユーザー裁定の3段階の設計の C)。★B-14 の uradori 版 ----
    #   ★原典は「③は「」付き逐語引用(**取得原文からの転記のみ**)」と定めている。
    #   ⇒ ★**鍵括弧に入れたなら、それは取得した原文に在るはずである。**★この規則はそこだけを見る。
    ("U-22", "uradori", "引いた逐語が原典に現に在る(段階C)",
     "run-uradori/references/daicho-format.md:37-38", "ng"),
    ("U-21", "uradori", "段階Aの申告を納品物に同梱(この走行の申告と一致)",
     "ref-nohin-checker/SKILL.md:68-63", "ng"),
    # ---- 事実の関門【段階C-2】(2026-09-01)。★U-21 の段階C 版。★bunken 版は B-16 ----
    #   ★U-22 は「逐語が**原典に在るか**」を見る。★U-23 は「**その申告が納品物に載ったか**」を見る。
    #   ★★**別の検査である** —— 前者は事実、後者は**その事実が受け手に届く経路に載ったか**。
    #   🔴★**段階B-2 と違い、段階C は uradori にも規則が在る**(`FULLTEXT_RULES` が2種別)。
    #     ⇒ ★**同梱の規則も2本要る。**★「1組足すだけ」ではなかった。
    ("U-23", "uradori", "段階Cの申告を納品物に同梱(この走行の申告と一致)",
     "ref-nohin-checker/SKILL.md:79-82", "ng"),
    # ---- C-5 コードの囲み(2026-10-05・ユーザー裁定「(ア) 説明書に1行足し不合格に」)。★bunken 版は B-18 ----
    #   ★閉じていない囲みの後ろは `strip_code_fences` が空にする ⇒ 点検できなかったことを ▲ で名乗る(→ `check_fence_closed`)。
    ("U-24", "uradori", "コードの囲みが閉じている(閉じていない囲みの後ろは点検できない)",
     "run-uradori/references/daicho-format.md:4", "ng"),
    # ---- 受理層の残り(2026-10-05・ユーザー裁定 問い1 (ア)・問い3 (ア))。★bunken 版は B-19・B-20 ----
    #   ★全角の縦棒で書いた表の行・UTF-8 で読めない行は、点検できなかったことを ▲ で名乗る
    #     (→ `check_fullwidth_table` / `check_utf8`)。★先に説明書へ1行ずつ足してから繋いだ(C-5 と同じ順番)。
    ("U-25", "uradori", "表の縦棒が半角である(全角の「｜」で書いた表の行は点検できない)",
     "run-uradori/references/daicho-format.md:26", "ng"),
    ("U-26", "uradori", "台帳が UTF-8 で読める(読めない字の行は点検できない)",
     "run-uradori/references/daicho-format.md:5", "ng"),
    # ---- bunken-daicho 文献台帳 ----
    # ★段5-1(2026-08-19)で足した門番。U-0 の bunken 版である。
    ("B-0",  "bunken",  "台帳が機械照合できる形である(検査不能が残っていない)",
     "run-bunken-daicho/SKILL.md:61-61, run-bunken-daicho/references/daicho-format.md:71-74", "ng"),
    ("B-1",  "bunken",  "リンク全行必須",                 "run-bunken-daicho/SKILL.md:15, run-bunken-daicho/references/daicho-format.md:86", "ng"),
    ("B-2",  "bunken",  "ヘッダーの目的・実行日",          "run-bunken-daicho/references/daicho-format.md:7-27", "ng"),
    ("B-3",  "bunken",  "必須列の存在",                   "run-bunken-daicho/references/daicho-format.md:79-92", "ng"),
    ("B-4",  "bunken",  "入手状況の語彙5種",               "run-bunken-daicho/references/daicho-format.md:135-139", "ng"),
    ("B-5",  "bunken",  "精読フラグの語彙2種",             "run-bunken-daicho/references/daicho-format.md:88, run-bunken-daicho/references/daicho-format.md:143", "ng"),
    ("B-6",  "bunken",  "凡例3種(種別・入手状況・精読)",    "run-bunken-daicho/references/daicho-format.md:235-242", "ng"),
    ("B-7",  "bunken",  "探索記録の次の一手",              "run-bunken-daicho/references/daicho-format.md:280-304", "ng"),
    ("B-8",  "bunken",  "アクセス日の日付形式",            "run-bunken-daicho/references/daicho-format.md:92", "ng"),
    # ---- 統計原表行の追加メタ(A-4・2026-07-20 / F-109・2026-08-17) --------------------
    # ★2026-08-22 に `NOT_MECHANIZED` から外して実装した(段5 B-2)。見送り理由は 2026-08-18 に
    #   すでに崩れており、★**見送りの理由が崩れたのに見送りのままにするのは fail-open と同じ構造**である。
    # ★★**2本に分けたのは必須度が違うからである。**原典は3つのメタの必須度を1文字も書いていないので、
    #   一律に必須へ倒すのは**原典に無い基準の発明**になる(規則表 deliverable-rules.md の原則1)。
    #   分け方の根拠は `TOUKEI_META` の註に書いた —— **どれも原典の中にある**。
    #   1本にまとめると画面に出る記号が1つしか無くなり、**どのメタが原因か読み手に伝わらない**。
    #   `--list-rules` の level も、✕ と △ が混ざった規則では嘘になる。
    ("B-9",  "bunken",  "統計原表行の調査年月(欄名つき)",
     "run-bunken-daicho/references/daicho-format.md:224-225, run-bunken-daicho/references/daicho-format.md:226", "ng"),
    ("B-10", "bunken",  "統計原表行の statInfId・fileKind(推奨)",
     "run-bunken-daicho/references/daicho-format.md:227, run-bunken-daicho/references/daicho-format.md:228", "gray"),
    # ---- 事実の関門【段階A】(2026-08-29・ユーザー裁定)。★U-20 の bunken 版 ----
    #   ★原典は「リンク先が開けなくなっていたら、その行は書誌を確定できていない扱いに戻」せと
    #     **既に定めている**。★この規則はその判断に要る事実(=届くか)を機械で採るだけである。
    ("B-11", "bunken",  "リンクが現に届く(段階A)",
     "run-bunken-daicho/SKILL.md:14-15-70", "ng"),
    # ---- 事実の関門【段階A-3】(2026-08-30・ユーザー裁定133)。★U-21 の bunken 版 ----
    ("B-12", "bunken",  "段階Aの申告を納品物に同梱(この走行の申告と一致)",
     "ref-nohin-checker/SKILL.md:68-63", "ng"),
    # ---- 事実の関門【段階B】(2026-08-31・ユーザー裁定の3段階の設計の B)。★uradori 版は無い ----
    #   ★原典は工程5 で「書誌欄をリンク先の原典ページと1項目ずつ突き合わせる」を
    #     **人手の必須工程**として定めている。★この規則は、その突合のうち
    #     **DOI の登録機関に問い合わせて機械で決まる3項目**を採る(★項目ファイル `--shoshi` が渡されたら7項目。D55)。
    #   🔴★**人手の工程を置き換えるものではない**(★DOI を持たない行と、登録機関に記録が無い行は人が見る)。
    ("B-13", "bunken",  "書誌が DOI の登録機関の記録と合う(段階B)",
     "run-bunken-daicho/SKILL.md:62-62-69", "ng"),
    # ---- 事実の関門【段階C】(2026-08-31)。★U-22 の bunken 版 ----
    #   ★原典は「要旨は自分の言葉でまとめる。原文の文をそのまま持ってくるなら「」で囲み、
    #     逐語だと示す」と定めている。⇒ ★**囲んだなら、原文に在るはずである。**
    #   ★2026-10-31(起票 `KICKOFF-nukigaki-b14-b17.md`・claude-harness の D64): 「抜き書き」の欄も照らす
    #     (★外側の「」を1本・「…」の区切りは順に・数で始まる区切りは負号の直後に当てない・画像から書き写した物は照らさず申告)。
    ("B-14", "bunken",  "引いた逐語が原典に現に在る(段階C)",
     "run-bunken-daicho/references/daicho-format.md:162-89-200-199-197-198-195", "ng"),
    # ---- 事実の関門【段階B-2】(2026-09-01)。★B-12 の段階B 版。★uradori 版は無い ----
    #   ★B-13 は「書誌が**合っているか**」を見る。★B-15 は「**その申告が納品物に載ったか**」を見る。
    #   ★★**別の検査である** —— 前者は事実、後者は**その事実が受け手に届く経路に載ったか**。
    ("B-15", "bunken",  "段階Bの申告を納品物に同梱(この走行の申告と一致)",
     "ref-nohin-checker/SKILL.md:72-74", "ng"),
    # ---- 事実の関門【段階C-2】(2026-09-01)。★U-23 の bunken 版 ----
    #   ★B-14 は「逐語が**原典に在るか**」を見る。★B-16 は「**その申告が納品物に載ったか**」を見る。
    ("B-16", "bunken",  "段階Cの申告を納品物に同梱(この走行の申告と一致)",
     "ref-nohin-checker/SKILL.md:79-82", "ng"),
    # ---- 台帳の【中】の食い違い(2026-10-05・ユーザー裁定 2026-10-04)。★ネットにも段階C の結果にも触らない ----
    #   ★精読が「本文精読済み」なのに、入手状況・要旨の読めた範囲の印が「本文に届いていない」側を名乗る行。
    #   ★原典の言葉の定義だけで「両立しない」と言える組だけを見る(→ `check_bunken_seidoku_mujun` の註)。
    #   ★2026-10-05(起票 `KICKOFF-b17-tsuika.md`): ④ 逆向き(抄録どまり × 本文の印だけ)・⑤ 精読を介さない組
    #     (抄録のみ・未入手 × 本文の印)を足した。★⑤ は精読を介さないので、題名を「精読と、…」から「精読・…が互いに」に直した。
    #   ★2026-10-31(起票 `KICKOFF-nukigaki-b14-b17.md`・claude-harness の D64): ⑥ 精読の言い過ぎ(本文精読済み × 本文の一部を名乗る印)を足した。
    ("B-17", "bunken",  "精読・入手状況・要旨の読めた範囲が互いに食い違わない",
     "run-bunken-daicho/references/daicho-format.md:136, run-bunken-daicho/references/daicho-format.md:139, run-bunken-daicho/references/daicho-format.md:143, run-bunken-daicho/SKILL.md:16, run-bunken-daicho/references/daicho-format.md:89, run-bunken-daicho/references/daicho-format.md:147, run-bunken-daicho/references/daicho-format.md:122, run-bunken-daicho/references/daicho-format.md:143, run-bunken-daicho/references/daicho-format.md:143", "ng"),
    # ---- C-5 コードの囲み(2026-10-05)。★U-24 の bunken 版 ----
    ("B-18", "bunken",  "コードの囲みが閉じている(閉じていない囲みの後ろは点検できない)",
     "run-bunken-daicho/references/daicho-format.md:4", "ng"),
    # ---- 受理層の残り(2026-10-05)。★U-25・U-26 の bunken 版 ----
    ("B-19", "bunken",  "表の縦棒が半角である(全角の「｜」で書いた表の行は点検できない)",
     "run-bunken-daicho/references/daicho-format.md:76", "ng"),
    ("B-20", "bunken",  "台帳が UTF-8 で読める(読めない字の行は点検できない)",
     "run-bunken-daicho/references/daicho-format.md:5", "ng"),
    # ---- ronbun-shippitsu 原稿 ----
    # ★段5-3(2026-08-20)で足した門番。U-0・B-0・H-0 の ronbun 版である。
    #   ★**これで4種別すべてが on になる**(段5 の最後)。
    ("R-0",  "ronbun",  "原稿が機械照合できる形である(検査不能が残っていない)",
     "run-ronbun-shippitsu/SKILL.md:87-87", "ng"),
    ("R-1",  "ronbun",  "(図表n)参照とキャプションの相互対応", "run-ronbun-shippitsu/SKILL.md:84, run-ronbun-shippitsu/SKILL.md:70", "ng"),
    ("R-2",  "ronbun",  "上付き引用番号と文献リストの相互対応", "run-ronbun-shippitsu/SKILL.md:84", "ng"),
    ("R-3",  "ronbun",  "図表番号体系を混在させない",       "run-ronbun-shippitsu/SKILL.md:67", "ng"),
    ("R-4",  "ronbun",  "図表参照の句点は括弧の後",         "run-ronbun-shippitsu/SKILL.md:68, run-ronbun-shippitsu/references/kosei-yogo.md:145", "ng"),
    ("R-5",  "ronbun",  "用字用語(×側の語)",              "run-ronbun-shippitsu/references/kosei-yogo.md:4, run-ronbun-shippitsu/references/kosei-yogo.md:8-68, run-ronbun-shippitsu/references/kosei-yogo.md:128-149", "ng"),
    ("R-6",  "ronbun",  "単位は記号を使う",                "run-ronbun-shippitsu/references/kosei-yogo.md:70, run-ronbun-shippitsu/references/kosei-yogo.md:74-84", "ng"),
    ("R-7",  "ronbun",  "数字は半角(全角数字を使わない)",   "run-ronbun-shippitsu/references/kosei-yogo.md:91, run-ronbun-shippitsu/references/kosei-yogo.md:93", "ng"),
    ("R-8",  "ronbun",  "5ケタ以上は万・億で区切る",        "run-ronbun-shippitsu/references/kosei-yogo.md:117, run-ronbun-shippitsu/references/kosei-yogo.md:121-124", "ng"),
    ("R-9",  "ronbun",  "英字は半角(Ｇ8・Ｕターンを除く)",  "run-ronbun-shippitsu/references/kosei-yogo.md:86-89", "ng"),
    ("R-10", "ronbun",  "西暦を使う(元号を使わない)",       "run-ronbun-shippitsu/references/kosei-yogo.md:98", "ng"),
    ("R-11", "ronbun",  "増減はプラス/マイナスで書かない",  "run-ronbun-shippitsu/references/kosei-yogo.md:97", "ng"),
    ("R-12", "ronbun",  "分数は「3分の1」",                "run-ronbun-shippitsu/references/kosei-yogo.md:97", "ng"),
    ("R-13", "ronbun",  "並列の鍵括弧に読点を挟まない",     "run-ronbun-shippitsu/references/kosei-yogo.md:67, run-ronbun-shippitsu/references/kosei-yogo.md:146", "ng"),
    ("R-14", "ronbun",  "句点は閉じ括弧の外",              "run-ronbun-shippitsu/references/kosei-yogo.md:68", "ng"),
    ("R-15", "ronbun",  "用字用語(原典が使い分けを指示)",   "run-ronbun-shippitsu/references/kosei-yogo.md:11, run-ronbun-shippitsu/references/kosei-yogo.md:22, run-ronbun-shippitsu/references/kosei-yogo.md:33-34, run-ronbun-shippitsu/references/kosei-yogo.md:36-37, run-ronbun-shippitsu/references/kosei-yogo.md:57", "gray"),
    ("R-16", "ronbun",  "用字用語(執筆モード依存の4組)",    "run-ronbun-shippitsu/SKILL.md:77", "gray"),
    ("R-17", "ronbun",  "一人称は「筆者」",                "run-ronbun-shippitsu/SKILL.md:60", "gray"),
    ("R-18", "ronbun",  "主観的評価語(原典に明示の2語)",    "run-ronbun-shippitsu/SKILL.md:60", "gray"),
    ("R-19", "ronbun",  "九州・沖縄・山口の市に県名を付けない", "run-ronbun-shippitsu/references/kosei-yogo.md:105-106", "gray"),
    # ---- html-visualizer 成果物 ----
    # ★段5-2(2026-08-19)で足した門番。U-0・B-0 の html 版である。
    ("H-0",  "html",    "成果物が機械照合できる形である(検査不能が残っていない)",
     "run-html-visualizer/SKILL.md:101-101", "ng"),
    ("H-1",  "html",    "外部リソースを参照しない",         "run-html-visualizer/SKILL.md:74-78, run-html-visualizer/SKILL.md:79, run-html-visualizer/SKILL.md:97", "ng"),
    ("H-2",  "html",    "主要コンテナ・style・scriptの開閉整合", "run-html-visualizer/SKILL.md:98", "ng"),
    ("H-3",  "html",    "完全なHTML文書/アーティファクト骨格", "run-html-visualizer/SKILL.md:86, run-html-visualizer/SKILL.md:88", "ng"),
    # ★2026-10-18(ch-6o6・ユーザーの決定 D42): 暗い画面は頼まれた時だけ。旧= テーマ切替(data-theme)対応(artifact 時に必須)。
    #   ★水準は gray —— ユーザーが暗い画面を頼んだかは機械に見えないので ✕ にしない(H-7 と同じ扱い)。
    ("H-4",  "html",    "画面は明るい色だけ・body に背景色(暗い画面は頼まれた時だけ)", "run-html-visualizer/SKILL.md:86", "gray"),
    ("H-5",  "html",    "全量保持(件数突合)",              "run-html-visualizer/SKILL.md:99", "ng"),
    ("H-6",  "html",    "テンプレート必須要素の存在",       "run-html-visualizer/SKILL.md:96, run-html-visualizer/SKILL.md:101", "ng"),
    # ---- 柱5②(2026-10-04・起票 `KICKOFF-a-nokori.md`)。★実行時の通信の機械側 ----
    #   ★原典(SKILL.md「絶対制約: 完全自己完結」の一句)は段4(`140eb79`)で既に足してある。★この規則はその機械側である。
    #   ★ユーザー決定(2026-08-17)の逐語=「規定は足す。ただし機械側は当面 △(要目視)にとどめる。
    #     ✕への昇格は【確認可能部分言語 S】を定義できてから」(`DESIGN.md` 柱5)。⇒ ★水準は gray(✕ にしない)。
    #   ★H-1〜H-6 と違い、SKILL.md の「生成後の自己チェック」4項目の外(絶対制約の一句)を指す。
    ("H-7",  "html",    "実行時に外部と通信しない(原典が名指す4つの書き方)", "run-html-visualizer/SKILL.md:75", "gray"),
]

# 機械化を見送った項目(実行時に「未検査」として明示するため、理由つきで保持する)
# ★第3要素は**控え**である(原典に到達できない環境でだけ表に出る)。逐語から導出できる環境では
#   使われない。★2026-08-18: この控えが**4件とも腐っていた**ことが常設テスト F-9 の新しい照合で
#   露見したので、導出結果に合わせて直した(bunken/ronbun の本体改訂に追従できていなかった)。
#   **控えを持つ限り、控えを照合する項目を必ず併せて置くこと。**
# ★★2026-08-18(段4のあと): **第3要素は【生成物】になった。手で書き換えないこと。**
#   `python sync_rules_md.py` が逐語から導出して書き戻す(`--check` で差分だけ見られる)。
#   照合する項目(F-9)だけでは**赤くなるが直せない** —— 本体を1行足すたびに人が手で控えを直す形になり、
#   実際に段4で 5件が赤くなった。**照合と再生成は対で置く。**
NOT_MECHANIZED = [
    ("uradori", "備考の長文禁止", "run-uradori/references/daicho-format.md:40",
     "「1行程度」の閾値が原典にない。数値を決めると新しい品質基準の発明になる"),
    ("bunken", "J-STAGE記事直URLの併記",
     "run-bunken-daicho/references/daicho-format.md:86, run-bunken-daicho/references/daicho-format.md:231",
     "「J-STAGE収録誌かどうか」が台帳の記載だけからは判定できない"),
    # ★★2026-08-22(B'-1・台帳 F-076)。**本体側は 2026-08-17 に実装済みだが、この表に載っていなかった** ——
    #   台帳の `applied` 欄の逐語「本体側のみ実装。**チェッカー側(見送り表への追加)は申し送りのみ**」。
    #   ★見送りの理由は「難しいから」ではなく**構造上できないから**である: 「その数字が原典に印字されて
    #     いたのか、台帳側が合算・換算・推計して作ったのか」は、**原典に実アクセスしないと決まらない**。
    #     🔴★**訂正(2026-08-29・司令塔18)**: 旧文=「同梱の点検プログラムにネットワーク機能は1行も無い(`DESIGN.md` §8 D-2 と同じ壁)」。
    #     ★2026-08-29 の段階A(事実の関門)でネットワーク機能は現に入った。★**ただし段階A が確かめるのは【リンクが届くか】だけで、
    #     原典の本文までは読んでいなかった**。★**追記(2026-09-01)**: ★2026-08-31 の段階C(B-14)で本文も現に取得するようになった。★**ただし見るのは【鍵括弧の逐語が在るか】だけで、数字の出所は判定できない。**★この項目はいまも見送りのままである。
    #   ★**見送り表に載せることが仕事である。**載っていない見送りは「未検査」として印字されず、
    #     読み手からは「検査した」と区別が付かない —— それがこの体系の言う fail-open の形である。
    ("bunken", "要旨欄の出所(印字された値か台帳が導いた値か)",
     "run-bunken-daicho/references/daicho-format.md:145-153",
     "その数字が原典に印字されていたか台帳側が導いた(合算・換算・推計)かは、"
     "原典へ実アクセスしないと決まらない。★2026-08-29 の段階A(事実の関門)でネットワーク機能は現に入った。が、段階A が確かめるのはリンクが届くかだけであった。★2026-08-31 の段階C(B-14)で原典の本文も現に取得するようになったが、見るのは鍵括弧に入れた逐語が在るかだけで、その数字が印字された値か台帳が導いた値かは判定できない"),
    # ★★2026-08-22(F-105・bunken 唯一の P0)。**申し送りが逐語でこの工事を名指ししていた** ——
    #   `runs\checker\bunken-yori-no-moushiokuri.md` §A「`NOT_MECHANIZED` に『**書誌の転記の正しさ**』を
    #   **見送りとして明記**し、`deliverable-rules.md` にも追記する」。
    #   ★**本体側は 2026-08-17 に済んでいる** —— `run-bunken-daicho/SKILL.md` の §2 工程5 が逐語で
    #     「★**同梱の点検プログラムはこれを検査できない**(ネットワークにつなぐ機能を持たないため
    #     構造上できない)。**だから人手の工程としてここに置いてある**」と書いた。
    #   ★★**本体が「機械には無理だから人がやれ」と書いたのに、機械の側はそれを1文字も印字していなかった。**
    #     ⇒ 読み手からは「検査した」と区別が付かない。**これがこの体系の言う fail-open の形である**
    #     (すぐ上の F-076 と同じ壁・同じ処置)。
    #   ★**壁は `DESIGN.md` §8 D-2 と同じ**(実アクセスが要る)。★★**D-2 は【載せる理由】であって
    #     【載せなくてよい理由】ではない。**D-2 が言うのは「突合そのものを別工程にする」ことで、
    #     この項目が言うのは「突合していないと画面に印字する」ことである。**別の工事である。**
    ("bunken", "書誌の転記の正しさ(リンク先の原典との1項目ずつの突合)",
     "run-bunken-daicho/SKILL.md:62-71",
     "書誌欄をリンク先の原典ページと突き合わせるには原典へ実アクセスが要る。"
     "★2026-08-29 の段階A(事実の関門)でネットワーク機能は現に入った。★2026-08-31 の段階B(B-13)が DOI の登録機関の記録と【著者名・誌名・巻(号)】の3項目を突き合わせるようになった。★2026-10-20(D55)から、書誌の項目ファイル(--shoshi)が渡された走行では残る4項目(年・題名・頁・出版社)も照らす。★渡されない走行の4項目と、DOI を持たない行・登録機関に記録が無い行は、いまも人が突き合わせる(DESIGN.md §8 D-2)。"
     "本体側は SKILL.md §2 工程5 に人手の必須工程として置いてある"),
    # ★★2026-08-22(網3・台帳 F-021)。**この行を足させたのは歯止めのほうである** ——
    #   常設テスト F-32(「未検査と自称しているのに見送り表に無い」)を置いたら、
    #   B-2 の `ok_note` 逐語「目的・実行日あり ※中間行(…)はキー名が確定していないため未検査」が
    #   **見送り表9要素のどれでもない**と鳴った。★**合格の記号(◎)を出しながら、その註で未検査を
    #   自称している**という形で、読み手は集計行からも見送り欄からもこれを知れなかった。
    #   ★**処置は原典が決めている** —— 申し送り(`runs/checker/bunken-yori-no-moushiokuri.md` §A)の
    #   F-021 の逐語が「**B-2の未検査注記を集計行と見送り欄にも出す**」と書いている(採否= 採用)。
    #   ★★**見送りの理由が他の8件と違うことを隠さない**: これは「構造上できない」ではなく
    #     **「まだ機械化していない」**である(F-021 の前半「件数目安の宣言値と実カウントの突合」は
    #     機械化できる。★**この工事では実装していない。未達として残っている**)。
    #     先例= 統計原表行の追加メタ(2026-08-18 に「機械化できる/実装は段5」と理由を書き換え、
    #     2026-08-22 に B-9・B-10 として実装して**この表から外した**)。同じ道をたどるべき項目である。
    ("bunken", "確認ゲートの承認値(ヘッダー中間行)と本体の照合",
     "run-bunken-daicho/references/daicho-format.md:29-49",
     "★構造上できないのではなく【まだ機械化していない】。★2026-08-28 に**件数目安は機械化した**"
     "(B-2 が宣言帯と実カウントを突き合わせて画面に出す)。★残るのは"
     "種別範囲・年代範囲・言語・エンジンの4項目で、宣言も本体との照合も検査していない(台帳 F-021)"),
    # ★★2026-08-22(網3・2件目)。**この行も歯止めが足させた。**しかも★**網3 を置いた当人が
    #   最初に取りこぼした地点**である —— B-3 は `r.ok_note(...)` ではなく **`r.note += ...`** で
    #   「※言語列は「和のみで充足したら省略可」のため未検査」と自称していた。
    #   ★F-32 の走査に `AugAssign` を足した途端に鳴った(本体の `.note +=` は7か所・うち自称1か所)。
    #   ★★**見送りの理由は構造上できないことである**(本体 L3601-3605 の註が既に半分書いていた):
    #     省略が正当だったか= 「和のみで充足したか」を判定するには**各行の本文言語**が要るが、
    #     それは**省略された当の列**にしか書かれていない。★**判定に要る情報が、判定対象の不在に
    #     よって失われる**という形なので、台帳の記載だけからは決まらない。
    ("bunken", "言語列(条件付き列。省略が正当だったか)",
     "run-bunken-daicho/references/daicho-format.md:84",
     "原典は「和のみで充足したら列ごと省略可」と定めるが、充足したかの判定には各行の本文言語が要り、"
     "それは省略された当の列にしか書かれていない(判定に要る情報が判定対象の不在で失われる)"),
    # ★★2026-08-22: **統計原表行の追加メタは、ここから外して B-9・B-10 として実装した。**
    #   見送り理由は 2026-08-18 の時点ですでに2つとも崩れていた(前半= 欄名は F-109 で『調査年月』に
    #   確定した / 後半= 統計原表の行は**種別の値**で見分けられるので別ブロックでも検査は届く。
    #   記録: `runs\checker\evidence\toukei-probe.txt`)。
    #   ★**見送りの理由が崩れたのに見送りのままにするのは fail-open と同じ構造**である。
    #   ★残っていた制約(段2の結合が正典表に無い列を落とす)への答えが
    #     「**列ではなく生の行テキストとその表自身の見出しを読む**」で、それが `check_bunken_toukei` である。
    ("ronbun", "語尾で事実と解釈を区別する", "run-ronbun-shippitsu/SKILL.md:56",
     "その文が事実か解釈かの判定に人間の読解が要る"),
    ("ronbun", "単位「トン◎ / t×」", "run-ronbun-shippitsu/references/kosei-yogo.md:79",
     "1文字「t」の検索は誤検出が支配的になる"),
    ("ronbun", "会社名は正式名で(株)(有)もつける", "run-ronbun-shippitsu/references/kosei-yogo.md:101",
     "「正式名かどうか」を本文だけからは判定できない"),
    ("ronbun", "東京23区・政令市の区名表記", "run-ronbun-shippitsu/references/kosei-yogo.md:106-111",
     "地名辞書が必要で、「北区」等は他都市の区名と衝突する"),
    ("ronbun", "九州・沖縄・山口の町村に県名を付ける", "run-ronbun-shippitsu/references/kosei-yogo.md:107",
     "「○○町」が地名か施設名かの判別に辞書が要り、誤検出が支配的になる"),
]

# ------------------------------------------------ 原典の位置は「記録」せず「導出」する
# ★2026-08-17 の工事。**行番号を持たない。**規則は原典の**逐語を1句**だけ持ち、
#   位置(file:line)はその逐語を原典から検索して**導く**。
#
#   なぜこうするか(実測): 2026-08-17 の bunken 本体改訂1回(daicho-format.md 98行→198行)で
#   B-1〜B-8 の8件が**全部**ずれた。常設テスト D-6 は「行番号がファイルの行数を超えていない」しか
#   見ないので、ファイルが伸びた今回は**素通りした**。行番号を「記録」として持つ限り必ず腐る。
#   **導出結果にすれば、ずれは構造的に起こらない。**
#   ★この体系は2026-08-09 に既に同じ結論へ到達している(「行番号でなく逐語で位置を指すこと」)。
#     規則表の原典欄だけがその学びから取り残されていた。
#
# 書式: 鍵 -> [(原典ファイル, 逐語)] または [(原典ファイル, 開始の逐語, 終了の逐語)]
#   鍵は規則ID("B-1")、機械化見送り項目は "NM:<種別>:<項目名>"。
#
# ★逐語は原典に**ちょうど1回**現れること。**0回=原典を失った / 2回以上=位置を特定できない。**
#   どちらも「導出できない」であり、**黙って合格に倒さず ▲(検査不能)にする**(柱2と同じ筋)。
# ★逐語が原典の改稿で消えて「原典を失った」と鳴るのは**正しい挙動**である
#   (規定が変わったのだから規則を見直すべき)。**誤検出として黙らせないこと。**
# ★53規則を一度にやらない。まず実測でずれていた規則から。逐語を持たない規則は従来どおり
#   D-6(行数を超えていないか)だけが効く。**段階的に強くなる形にしてある。**
#   ★現況(2026-08-18): **53規則すべてが逐語を持つ**(uradori 20・bunken 8・ronbun 19・html 6)。
#   手書きの行番号だけに頼る規則は**もう1本も無い**。残っているのは
#   **機械化を見送った項目のうち4件**(ronbun の単位「t」・会社名・東京23区・町村の県名)で、
#   これは常設テスト F-9 が件数を固定して見張っている(=黙って増えない)。
# ★html を先に片付けたのは、**段4で run-html-visualizer/SKILL.md が2か所編集される**からである
#   (ronbun は1か所)。行が増える予定のあるファイルほど、手書きの行番号は早く腐る。
ORIGIN_QUOTES = {
    # ---- uradori(2026-08-04 の本体全面改修で SKILL.md 側の行番号がずれていた) ----
    # ★2026-08-18: uradori の20規則すべてに逐語を持たせた。追加した14本のうち**11本(12か所)は
    #   規則表と実装が別々の行を指していた** —— 食い違いは「どちらも書き写した記録であること」の証拠で、
    #   とくに腐りやすい印だった。逐語にすれば3者(実装・規則表・原典)が同じ1句に収束する。
    "U-0": [("run-uradori/SKILL.md", "**「未検査(―)」が出た項目は「合格」ではない。**"),
            ("run-uradori/references/daicho-format.md", "**台帳本体は必ずMarkdownの表で書く。**")],
    "U-1": [("run-uradori/SKILL.md", "**リンク必須**: 台帳の全行に URL"),
            ("run-uradori/references/daicho-format.md", "**鉄則: 全行必須**")],
    "U-2": [("run-uradori/references/daicho-format.md",
             "## ヘッダーブロック(台帳冒頭に必須)", "- 実行日: 2026-07-18")],
    "U-3": [("run-uradori/references/daicho-format.md",
             "| 列 | 内容 | ①軽装 | ②標準 | ③提出級 |",
             "| 備考 | 一次/二次の別、未到達理由、鮮度、代替文献の有無等。")],
    "U-4": [("run-uradori/SKILL.md", "台帳では上記5語のみを使う"),
            ("run-uradori/references/daicho-format.md",
             "| 判定 | 裏付け / 条件付き裏付け / 反証 / 未確認 / 未到達")],
    "U-5": [("run-uradori/SKILL.md", "台帳末尾に判定サマリー"),
            ("run-uradori/references/daicho-format.md", "## サマリー(台帳末尾に必須)",
             "裏付け 8 / 条件付き 2 / 反証 1 / 未確認 1 / 未到達 1(全13主張)")],
    # U-6 と U-7 は同じ1行(凡例の但し書き)の**別の半分**を指す。規則が2つの要求から成るため
    "U-6": [("run-uradori/references/daicho-format.md", "**判定サマリーの直後に圧縮2行の凡例を必ず置く**"),
            ("run-uradori/references/daicho-format.md", "(判定5語は全て載せる)"),
            # ★2026-10-04(起票 `KICKOFF-a-nokori.md` U-6): 「間に探索記録の節を挟まない」の根拠。
            #   ★原典は凡例→探索記録の順を定めているので、探索記録の節がサマリーと凡例の間に在れば、
            #     「直後」をどう読んでも直後ではない。
            ("run-uradori/references/daicho-format.md", "凡例の後に独立セクション「探索記録(再挑戦の起点)」を必ず置く"),
            # ★2026-10-05(起票 `KICKOFF-u6-nokori.md`): 「所見を挟んでよい」(裁定 (イ) の根拠)と、
            #   凡例が【一行定義】で書式が「語=意味」であること(F-045・F-026 の根拠)。
            ("run-uradori/SKILL.md", "と所見、その直後に**凡例**(判定・分類の一行定義。書式はdaicho-format.md)"),
            ("run-uradori/references/daicho-format.md", "**凡例(判定)**: 裏付け=原文が主張を直接支持")],
    "U-7": [("run-uradori/references/daicho-format.md", "**凡例(分類)**: 数値・規格=基準値・含有量等"),
            ("run-uradori/references/daicho-format.md", "台帳に登場しない分類は凡例から省いてよい")],
    "U-8": [("run-uradori/SKILL.md", "**探索記録(再挑戦の起点)**セクション"),
            ("run-uradori/references/daicho-format.md",
             "## 探索記録(再挑戦の起点)(必須・2026-07-18ユーザー確定)",
             "**「次の一手」(何が確認できれば解決するか)を必ず書く**")],
    "U-9": [("run-uradori/SKILL.md", "**具体値の格上げ禁止(2026-07-20確定)**"),
            ("run-uradori/references/daicho-format.md", "**但し書き(具体値の格上げ禁止・2026-07-20確定)**")],
    "U-10": [("run-uradori/SKILL.md", "何が条件かを備考に必須"),
             ("run-uradori/references/daicho-format.md",
              "- **条件付き裏付け**: 部分一致・条件付きの支持・近似値")],
    # ★U-11 の2句目は「この義務は水準①でも例外にしない」の側。**規則が全水準で効く根拠**である
    "U-11": [("run-uradori/references/daicho-format.md", "矛盾箇所の逐語を必ず添える"),
             ("run-uradori/references/daicho-format.md",
              "**反証の行が1件でもあるなら、水準①でも要旨/逐語列を立てる**")],
    "U-12": [("run-uradori/references/daicho-format.md", "| アクセス日 | 実際にアクセスして確認した日付")],
    "U-13": [("run-uradori/references/daicho-format.md",
              "アーカイブにのみ到達できた場合は**「条件付き裏付け」止まり**")],
    # ★U-14 の2句目が、規則が「未到達も未処置に数える」と決めている根拠(原典の逐語)である
    "U-14": [("run-uradori/references/daicho-format.md", "反証・未確認が残ったまま「提出可」とは書かない。"),
             ("run-uradori/references/daicho-format.md", "**裏付けとしてカウントしない**")],
    "U-15": [("run-uradori/SKILL.md", "一次必須+逐語引用+アクセス日+到達不能時は代替探索"),
             ("run-uradori/references/daicho-format.md", "③は「」付き逐語引用(取得原文からの転記のみ)")],
    "U-16": [("run-uradori/SKILL.md", "一次必須+逐語引用+アクセス日+到達不能時は代替探索"),
             ("run-uradori/references/source-hierarchy.md",
              "水準③: 一次必須(到達不能なら代替探索の上、未到達として残す)"),
             ("run-uradori/references/source-hierarchy.md", "台帳の備考欄に「一次」「二次」を書く")],
    # ★U-17 の2句目は bunken の語彙も受ける根拠(原典が「同じ意味として読み替えてよい」と書いている)
    "U-17": [("run-uradori/references/daicho-format.md", "語は「本文到達」「抄録どまり」の2語"),
             ("run-uradori/references/daicho-format.md",
              "bunken の「本文精読済み」と uradori の「本文到達」を同じ意味として読み替えてよい")],
    "U-18": [("run-uradori/references/daicho-format.md", "## 対象範囲の実体(受領と抽出)(必須・2026-08-04確定)"),
             ("run-uradori/SKILL.md", "結果は台帳の「対象範囲の実体(受領と抽出)」節に必ず転記する")],
    "U-19": [("run-uradori/references/source-hierarchy.md", "**格だけでなく「何としての一次か」を必ず添える**"),
             ("run-uradori/references/source-hierarchy.md",
              "**書き手自身の宣言との内部矛盾の1点だけ**")],
    # ★段階A(2026-08-29)。★原典は3つの句でこれを求めている ——
    #   実アクセスして載せること / ローカル資料はファイルパスでよいこと / 到達できなければ「未到達」と残すこと。
    #   ★**この規則は新しい基準を発明していない。**原典が既に求めているものを機械で採るだけである。
    "U-20": [("run-uradori/SKILL.md",
              "このセッション内で WebFetch / Read 等により実際にアクセスし、内容を目視確認できたソースのみを台帳に載せる",
              "台帳の全行に URL(ローカル資料はファイルパス)を付ける",
              "到達できなかったソースは「未到達」として正直に残す")],
    # ★段階A-3(2026-08-30)。★原典は2つの句でこれを求めている ——
    #   ★同梱そのものと、★**空にしないこと**(=チェッカーが無い環境での受け皿)。
    #   ★**この規則は新しい基準を発明していない。**★原典が求めているものを機械で確かめるだけである。
    # ★段階C(2026-08-31)。★原典の2つの句を指す ——
    #   ★**鍵括弧に入れたら逐語である**(=取得原文からの転記のみ)/ ★**どこまで読んだかを書く**。
    "U-22": [("run-uradori/references/daicho-format.md",
              "③は「」付き逐語引用(取得原文からの転記のみ)",
              "原典の**どこまで読んだか**")],
    # ★2026-10-11(ch-ylp・ユーザー許可「原典の場所を直してよい」): 申告の囲みの段落は ref-nohin-checker に移した(逐語は変えていない)。
    "U-21": [("ref-nohin-checker/SKILL.md",
              "段階Aの申告ブロックを、納品物に必ず同梱する(省略不可)",
              "★**囲みを空にしない。**")],
    # ★段階C-2(2026-09-01)。★原典の2つの句を指す ——
    #   ★同梱そのものと、★**逐語の引用が1本も無い台帳でも貼ること**。
    #   🔴★**2つ目に「囲みを空にしない」を選ばなかった** —— ★U-21 と同じ句になり、
    #     ★**どちらの義務が消えても片方の指し先が生き残ってしまう**からである。
    "U-23": [("ref-nohin-checker/SKILL.md",
              "段階Cの申告ブロックを、納品物に必ず同梱する(省略不可)",
              "★**逐語の引用が1本も無い台帳でも貼る**")],
    # ★U-24(C-5・2026-10-05): ユーザー裁定「(ア) 説明書に1行足し不合格に」で説明書に足した1行の太字の句。
    "U-24": [("run-uradori/references/daicho-format.md", "**コードの囲みは必ず閉じる**")],
    # ★U-25・U-26(2026-10-05・起票 `KICKOFF-juri-tsuzuki.md`): ユーザー裁定 問い1 (ア)・問い3 (ア) で説明書に足した1行の太字の句。
    "U-25": [("run-uradori/references/daicho-format.md", "**表の縦棒に全角の「｜」を使わない**")],
    "U-26": [("run-uradori/references/daicho-format.md", "**台帳は UTF-8 で保存する**")],
    # ---- bunken-daicho(2026-08-17 の本体改訂で8件すべてずれた。この工事の発端) ----
    # ★B-0 の原典は段4(2026-08-18)で本体に入れた一文である。
    #   uradori の U-0 が `run-uradori/SKILL.md` の「未検査は合格ではない」に拠るのと同じ位置づけ。
    # ★2026-08-19(段5-1): 台帳本体の枝を門番の対象に含めたので、**その根拠の逐語を足した**。
    #   1つ目= 表で書くこと(F-001・2026-08-17 に本体へ入った規定)。
    #   2つ目= ★**行の向きまで定めている句**。これが要る —— 縦型台帳(項目を行にした表)も
    #   「Markdown の表」ではあるので、「表で書く」だけでは対象外だと言い切れない。
    #   「以降が**各文献の行**」が、1行=1文献であることを定めている当の句である。
    "B-0": [("run-bunken-daicho/SKILL.md", "**「違反が無かった」ではない。**",
             "何が検査されなかったのかを出力で読み、**書式を直してから通し直す**"),
            ("run-bunken-daicho/references/daicho-format.md",
             "**台帳本体は必ず Markdown の表で書く(F-001・2026-08-17)。**",
             "1行目がヘッダー行、2行目が `|---|` の区切り行、以降が各文献の行")],
    "B-1": [("run-bunken-daicho/SKILL.md", "2. **全行リンク必須**"),
            ("run-bunken-daicho/references/daicho-format.md", "**全行必須(鉄則)**")],
    "B-2": [("run-bunken-daicho/references/daicho-format.md", "## ヘッダーブロック(冒頭に必須)",
             "(人も点検プログラムもどの値がどのキーのものか拾えなくなる)。")],
    "B-3": [("run-bunken-daicho/references/daicho-format.md", "| 列 | 内容 | 必須度 |",
             "| アクセス日 | 実アクセスした日付 | 必須 |")],
    "B-4": [("run-bunken-daicho/references/daicho-format.md", "- **全文OA** — 全文が無料公開",
             "- **未入手** — 書誌は確定したが本文にまだ到達していない")],
    "B-5": [("run-bunken-daicho/references/daicho-format.md", "| 精読 | 要旨が**本文精読済み**か**抄録どまり**か。"),
            ("run-bunken-daicho/references/daicho-format.md", "**精読フラグの運用(A-8・2026-07-20)**")],
    "B-6": [("run-bunken-daicho/references/daicho-format.md",
             "## 凡例(必須・uradori段3で確定した標準搭載)", "**凡例(精読)**: 本文精読済み=")],
    "B-7": [("run-bunken-daicho/references/daicho-format.md",
             "## 探索記録(再挑戦の起点)(必須・uradori段3で確定した標準搭載)",
             "空欄は「探したが無かった」と「そもそも書かなかった」の区別がつかない")],
    "B-8": [("run-bunken-daicho/references/daicho-format.md", "| アクセス日 | 実アクセスした日付 | 必須 |")],
    # ★B-9 は**2つの逐語**を持つ。①欄の定義そのもの(「年代ゲートはこの調査年月で判定する」= 必須の根拠)と、
    #   ②F-109 が足した「欄名を必ず書き添える」。★**この節で「必ず」が使われている唯一の箇所が②である。**
    #   ③は原典が名指しで禁じた旧欄名の一句(値そのものは `TOUKEI_META` が1か所だけで持つ)。
    "B-9": [("run-bunken-daicho/references/daicho-format.md",
             "- **調査年月** — e-Stat の統計表検索の結果一覧にある **『調査年月』**(いつ調べたか)をそのまま写す。**年代ゲートはこの調査年月で判定する**",
             "★**欄名を必ず書き添える**(F-109・2026-08-17)"),
            ("run-bunken-daicho/references/daicho-format.md", "**この名前で書かない**")],
    # ★B-10 は2つのメタを持つので逐語も2つ。**片方が原典から消えたら気づけるように別々の spec にする**
    #   (1つの spec にまとめると、片方だけ消えても「範囲」としては成立してしまう)。
    "B-10": [("run-bunken-daicho/references/daicho-format.md", "- **statInfId** — e-Statの統計表ID"),
             ("run-bunken-daicho/references/daicho-format.md", "- **fileKind** — 0=Excel(既定)/1=CSV(表により404あり)")],
    # ★段階A(2026-08-29)。★U-20 の bunken 版。★原典は3つの句でこれを求めている ——
    #   文献ページへ実アクセスして確定すること / DOI を優先し安定URLを貼ること /
    #   ★**開けなくなっていたら「書誌を確定できていない」扱いに戻すこと**(=届くかが判断の入力である)。
    "B-11": [("run-bunken-daicho/SKILL.md",
              "文献ページへこのセッション内で実アクセスして確定してから台帳に載せる",
              "DOIを優先し、なければ安定URL。リンクのない行は作らない",
              "リンク先が開けなくなっていたら、その行は")],
    # ★段階A-3(2026-08-30)。★U-21 の bunken 版。★原典の2つの句を指す。
    # ★2026-10-11(ch-ylp・ユーザー許可「原典の場所を直してよい」): 申告の囲みの段落は ref-nohin-checker に移した(逐語は変えていない)。
    "B-12": [("ref-nohin-checker/SKILL.md",
              "段階Aの申告ブロックを、納品物に必ず同梱する(省略不可)",
              "★**囲みを空にしない。**")],
    # ★段階B(2026-08-31)。★原典は3つの句でこの突合を求めている ——
    #   突合そのもの / 何を突き合わせるか(7項目) / どこを特に見るか(固有名詞)。
    #   🔴★**「機械にはできない」と書いた句は指していない** —— そこは段階A の着地で
    #     既に偽になっており、★**この規則が閉じようとしている当のものだからである。**
    "B-13": [("run-bunken-daicho/SKILL.md",
              "**★書誌の突合(納品前に必須。省略しない)**",
              "1項目ずつ突き合わせる",
              "特に見るのは**固有名詞**")],
    # ★段階C(2026-08-31)。★U-22 の bunken 版。★原典の2つの句を指す。
    # ★2026-10-31(起票 `KICKOFF-nukigaki-b14-b17.md`): 書式の「抜き書き」の節の5つの句を足した(計7つ)——
    #   照合の当て先(リンクの欄の URL)/ 外側の「」/「…」の区切りは順に / 負号ごと写す / 画像から書き写した物は機械で照らせない。
    "B-14": [("run-bunken-daicho/references/daicho-format.md",
              "**要旨は自分の言葉でまとめる。原文の文をそのまま持ってくるなら「」で囲み、逐語だと示す。**",
              "読めた範囲を明記(全文/抄録より)",
              "チェッカーの段階C も、リンクの欄の URL に当てて照らす",
              "原文の中の「」は、そのまま写す(全体を外側の「」で囲む)",
              "途中を省くときは「…」で区切る(区切りごとに、原文の中で順に照らす)",
              "数で始まる所を切り出すときは、原文でその直前にある負号(−)ごと写す",
              "この印の抜き書きは機械では照らせないので、確かめ役が頁の画像と照らす")],
    # ★段階B-2(2026-09-01)。★B-12 の段階B 版。★原典の2つの句を指す ——
    #   ★同梱そのものと、★**段階A の囲みとは別に置くこと**(=1つに畳ませない)。
    "B-15": [("ref-nohin-checker/SKILL.md",
              "段階Bの申告ブロックを、納品物に必ず同梱する(省略不可)",
              "★**この囲みは段階Aのものとは別に置く**")],
    # ★段階C-2(2026-09-01)。★U-23 の bunken 版。★原典の2つの句を指す。
    #   🔴★**2つ目は B-15 と別の句にしてある** —— ★bunken には「★**この囲みは段階Aの
    #     ものとは別に置く**」が段階B の側にも在るので、そちらを指すと**どちらの義務を
    #     指しているか決まらない**(★uradori では起きない・bunken でだけ起きる形)。
    "B-16": [("ref-nohin-checker/SKILL.md",
              "段階Cの申告ブロックを、納品物に必ず同梱する(省略不可)",
              "★**逐語の引用が1本も無い台帳でも貼る**")],
    # ★B-17(2026-10-05): 4つの逐語。①②入手状況の2語の定義(本文に届いていない側)/ ③精読の定義 /
    #   ④鉄則3「(抄録より)」の印の定義(★SKILL.md の鉄則は「絶対規定」の節にある)。
    #   ★2026-10-05(起票 `KICKOFF-b17-tsuika.md`)に2つ足した(計6つ): 要旨の読めた範囲の印の形を決める2か所
    #     ——「(全文/抄録より)」と「(ページ本文より)」(★当時、④⑤ が本文の印として読むのは、この2つの形だけ)。
    #   ★2026-10-06(起票 `KICKOFF-honbun-yori.md`・ユーザー裁定 2026-10-05 ⑧ (ウ))に1つ足した(計7つ): 説明書に足した1行
    #     「(本文より)」(★④⑤ が本文の印として読む形は、これで3つ)。
    "B-17": [("run-bunken-daicho/references/daicho-format.md", "- **抄録のみ** — 抄録は読めたが全文は未入手"),
             ("run-bunken-daicho/references/daicho-format.md", "- **未入手** — 書誌は確定したが本文にまだ到達していない"),
             ("run-bunken-daicho/references/daicho-format.md", "**精読フラグの運用(A-8・2026-07-20)**"),
             ("run-bunken-daicho/SKILL.md", "3. **読めた範囲に正直**"),
             ("run-bunken-daicho/references/daicho-format.md", "読めた範囲を明記(全文/抄録より)"),
             ("run-bunken-daicho/references/daicho-format.md",
              "要旨欄の出所ラベル(「(抄録より)」「(ページ本文より)」)は**どこまで読んだか**を表すもの"),
             ("run-bunken-daicho/references/daicho-format.md", "**「(本文より)」も、本文を読んで書いた側の印である**"),
             # ★2026-10-31(起票 `KICKOFF-nukigaki-b14-b17.md`)に2つ足した(計9つ): ⑥ の原典 —— 言い過ぎの組の定義と、
             #   全部読んだ時の形に画像の印を足した句(★どちらも書式の「精読フラグの運用」の段落)。
             ("run-bunken-daicho/references/daicho-format.md", "本文の一部を名乗る印と「本文精読済み」の組は、言い過ぎである"),
             ("run-bunken-daicho/references/daicho-format.md", "印は「(本文の画像より)」(全部読んだ時の形)")],
    # ★B-18(C-5・2026-10-05): U-24 の bunken 版。説明書に足した1行の太字の句。
    "B-18": [("run-bunken-daicho/references/daicho-format.md", "**コードの囲みは必ず閉じる**")],
    # ★B-19・B-20(2026-10-05): U-25・U-26 の bunken 版。説明書に足した1行の太字の句。
    "B-19": [("run-bunken-daicho/references/daicho-format.md", "**表の縦棒に全角の「｜」を使わない**")],
    "B-20": [("run-bunken-daicho/references/daicho-format.md", "**台帳は UTF-8 で保存する**")],
    # ---- ronbun-shippitsu(R-1・R-2 は同じ SKILL.md:77 を指していたが :77 は校正用語の箇条書き) ----
    # ★段5-3(2026-08-20): 門番 R-0 の原典。**exit 3 の受け取り方の一文だけ**である ——
    #   B-0 は「台帳本体は表で書く」という**形の規定**も併せて指しているが、ronbun には
    #   対応するものが無い(原稿の書式を「機械が読める形」に縛る規定が原典に無い)。
    #   ★H-0 と同じく、**無い規定を指したことにしない。指せるものだけを指す。**
    "R-0": [("run-ronbun-shippitsu/SKILL.md", "**「違反が無かった」ではない。**",
             "何が検査されなかったのかを出力で読み、**書式を直してから通し直す**")],
    "R-1": [("run-ronbun-shippitsu/SKILL.md", "**整合の最終確認**"),
            ("run-ronbun-shippitsu/SKILL.md", "キャプションは図表の**下**に「図表n.タイトル」")],
    "R-2": [("run-ronbun-shippitsu/SKILL.md", "**本文の上付き引用番号と文献リストの相互対応**")],
    "R-3": [("run-ronbun-shippitsu/SKILL.md", "1つの文書内で混在させない。")],
    "R-4": [("run-ronbun-shippitsu/SKILL.md", "**句点は括弧の後**"),
            ("run-ronbun-shippitsu/references/kosei-yogo.md", "←図表参照の句点位置")],
    # ★R-5〜R-15・R-19 は 2026-08-18 に逐語化(残り12本)。原典は用語集 `kosei-yogo.md` で、
    #   **この文書は「規定そのものが表と箇条書きでできている」**——◎×の対が規則の本体である。
    #   なので範囲(開始の逐語〜終了の逐語)で持つものが多い。**節の見出しは指さない**が、
    #   規定文が見出し行に載っている場合(R-6・R-9)は、見出し記号を含めず**規定文だけ**を逐語にする。
    "R-5": [("run-ronbun-shippitsu/references/kosei-yogo.md", "以下、◎＝使う表記、×＝使わない表記。"),
            ("run-ronbun-shippitsu/references/kosei-yogo.md",
             "| ◎ 使う | × 使わない | 備考 |", "| 「 」。 | 「 。」 | 句点は閉じ括弧の外に打つ |"),
            # ★用語集の表に無い語(鍵となる・関わらず・止まっている・取組む)はこの節だけが出どころ
            ("run-ronbun-shippitsu/references/kosei-yogo.md",
             "- × 3か月、3ヶ月 → ◎ 3カ月", "- 同様の例：売り上げ（名詞は売上）、下請け（名詞は下請）")],
    "R-6": [("run-ronbun-shippitsu/references/kosei-yogo.md", "原則として記号を用いる。ただし、トンはカタカナとする。"),
            ("run-ronbun-shippitsu/references/kosei-yogo.md",
             "| cm | センチメートル |", "| L | リットル（メルマガはカタカナ） |")],
    # ★R-7 の手書きは 91,117 を指していた。だが 117 は「裁定は上の【数字】節が正本」と自ら書いた
    #   **再掲**である。原典が正本と名乗っている 91 と、1ケタも半角と確定した裁定の 93 を指す。
    "R-7": [("run-ronbun-shippitsu/references/kosei-yogo.md", "数字は半角（1ケタも半角）※この節が数字表記の裁定の正本"),
            ("run-ronbun-shippitsu/references/kosei-yogo.md", "**文書タイプを問わず、1ケタの数字も半角**とする")],
    # R-7 と R-8 は 117 行目を共有していた。R-8 は「5ケタ以上は万、億で区切り」の側だけを指す
    "R-8": [("run-ronbun-shippitsu/references/kosei-yogo.md", "5ケタ以上は万、億で区切り、基本的に漢数字は使用しない。"),
            ("run-ronbun-shippitsu/references/kosei-yogo.md",
             "- 万進法と千進法の折衷表記で統一：", "  - × 1,234,000人 → ◎ 123万4,000人")],
    "R-9": [("run-ronbun-shippitsu/references/kosei-yogo.md",
             "基本的に半角表記", "G8（この場合は全角で表記）、Uターン（この場合は全角で表記）")],
    "R-10": [("run-ronbun-shippitsu/references/kosei-yogo.md", "2010年、2010〜2015年（× 平成22年）＝西暦を使う")],
    # ★R-11 と R-12 は**同じ1行の別の半分**を指す(U-6/U-7 と同じ形)。増減の側と分数の側
    "R-11": [("run-ronbun-shippitsu/references/kosei-yogo.md", "5％増（× プラス5％）、3％減（× マイナス3％）")],
    "R-12": [("run-ronbun-shippitsu/references/kosei-yogo.md", "3分の1（× 1／3。◎「3分の1」は原本では空欄のため補完）")],
    "R-13": [("run-ronbun-shippitsu/references/kosei-yogo.md", "並列の鍵括弧に読点を挟まない（原本1頁目・3頁目とも同じ）"),
             ("run-ronbun-shippitsu/references/kosei-yogo.md", "←並列の鍵括弧に読点を挟まない")],
    "R-14": [("run-ronbun-shippitsu/references/kosei-yogo.md", "句点は閉じ括弧の外に打つ")],
    # ★R-15 は要目視に回した6語の**一語ずつ**が出どころ。備考「状況により使い分け」は原典に3か所
    #   あって一意にならないので、◎×の対そのもの(行)を指す。33-34 と 36-37 は◎×が逆転する組
    "R-15": [("run-ronbun-shippitsu/references/kosei-yogo.md", "| 足下 | 足元 | 状況により使い分け |"),
             ("run-ronbun-shippitsu/references/kosei-yogo.md", "| 〜するうえで | 〜する上で | 状況により使い分け |"),
             ("run-ronbun-shippitsu/references/kosei-yogo.md",
              "| さらに、（接続詞） | 更に、（接続詞） | |", "| 更に（副詞） | さらに（副詞） | |"),
             ("run-ronbun-shippitsu/references/kosei-yogo.md",
              "| したがって、（接続詞） | 従って、（接続詞） | |", "| 法律に従う | 法律にしたがう |"),
             ("run-ronbun-shippitsu/references/kosei-yogo.md",
              "| …をみると（※実際にみる(look)行為は「見る」） | …を見ると | 状況により使い分け |")],
    "R-16": [("run-ronbun-shippitsu/SKILL.md", "**用語集と教授論文の実態が食い違う項目に注意**")],
    "R-17": [("run-ronbun-shippitsu/SKILL.md", "**一人称は「筆者」、自分の研究は「本研究」「本稿」「本調査」。**")],
    "R-18": [("run-ronbun-shippitsu/SKILL.md", "主観的評価語（素晴らしい・非常に等）を避ける")],
    # ★R-19 の手書きは 105-107 を指していた。だが 107 は**町村**の規定であり、これは
    #   機械化見送り項目「九州・沖縄・山口の町村に県名を付ける」の原典である。R-19 は**市**の規則
    #   なので、適用範囲の宣言(105)から市の規定(106)までを指す。**規則の中身は変えていない。**
    "R-19": [("run-ronbun-shippitsu/references/kosei-yogo.md",
              "＜九州・沖縄・山口管内の場合＞", "市は「〇〇市」と表記。政令区の区名は書かない。")],
    # ---- html-visualizer(2026-08-18 に逐語化。★実測でずれていたのではなく「まだ手書きだった」) ----
    # ★この6本は 2026-08-17 の実測では**行番号が全部正しかった**。それでも逐語にするのは、
    #   段4で run-html-visualizer/SKILL.md に**2か所**書き足す予定があるからである。
    #   手書きのままだと、行が増えた瞬間に**誰にも気づかれずに**ずれる(効いている検査は D-6 =
    #   「行数を超えていないか」だけで、ファイルが伸びる方向のずれは素通りする)。
    # ★段5-2(2026-08-19): 門番 H-0 の原典。**exit 3 の受け取り方の一文だけ**である ——
    #   B-0 は「台帳本体は表で書く」という**形の規定**も指しているが、html には対応するものが無い
    #   (原典に「スクリプトを書かない」等の許可範囲の規定が無いことは DESIGN §6 が名指ししている)。
    #   ★無い規定を指したことにしない。指せるものだけを指す。
    "H-0": [("run-html-visualizer/SKILL.md", "**「違反が無かった」ではない。**",
             "何が検査されなかったのかを出力で読み、**書式を直してから通し直す**")],
    # ★H-1〜H-6 は SKILL.md の「生成後の自己チェック」4項目と1対1に対応している
    #   (SKILL.md が「上の2・3・4を check_deliverable.py で機械照合できる」と自分で割り当てている)。
    #   逐語もその割り当ての行を含める —— **なぜこの規則が在るのか**が原典に書いてある場所だからである。
    "H-1": [("run-html-visualizer/SKILL.md",
             "CSS・JSはすべてインラインに書く。外部CDN・外部スタイルシート・Webフォント・外部画像は参照しない",
             "1ファイル(1アーティファクト)で完結させる。"),
            # ★実装は `<a href>` を対象外にしている。その根拠はこの1行で、**手書きの原典欄には入っていなかった**
            ("run-html-visualizer/SKILL.md", "`<a href>` による外部サイトへのリンクは描画に影響しないので使ってよい。"),
            ("run-html-visualizer/SKILL.md",
             "**自己完結**: 外部リソース参照(src・hrefのCDN・Webフォント・外部画像)が無いこと")],
    "H-2": [("run-html-visualizer/SKILL.md",
             "**構文**: タグの閉じ整合(主要コンテナ・style・scriptの開閉対応)を確認する。")],
    # H-3 と H-4 は同じ1行(出力先の連鎖のアーティファクト側)の**別の部分**を指す(U-6/U-7 と同じ形)
    "H-3": [("run-html-visualizer/SKILL.md", "スケルトンは発行時に付与されるため DOCTYPE/html/head/body タグは書かない"),
            ("run-html-visualizer/SKILL.md", "完全なHTML文書(DOCTYPE〜)として `.html` ファイルに保存し")],
    "H-4": [("run-html-visualizer/SKILL.md", "画面は明るい色だけで作り、`body` に背景色を指定する")],
    "H-5": [("run-html-visualizer/SKILL.md",
             "**全量保持**: 入力の件数(案数・手法数・ステージ数)とHTML内の件数が一致するか突合する。")],
    # ★H-6 の2句目が「常に未検査(―)にしてよい」の根拠である。実装のコメントは以前から
    #   「原典が**目視のまま**と人間へ明示的に割り当てている」と述べていたのに、
    #   手書きの原典欄はその行を指していなかった(要求の本体である :68 だけを指していた)。
    "H-6": [("run-html-visualizer/SKILL.md", "**必須要素の存在**: 使用テンプレートが必須と定める要素"),
            ("run-html-visualizer/SKILL.md",
             "1(必須要素)はテンプレートごとの規定なので機械照合の対象外——目視のまま。")],
    # ★柱5②(2026-10-04・H-7): 原典が名指す4つの書き方の一句。★「など」の先は照合しない(R-18 と同じ作法)。
    #   ★この一句は H-1 の範囲の原典(「CSS・JSはすべて…」〜「1ファイル…で完結させる。」)の中にも入っている。
    #     ★H-1 が見るのは静的な参照で、実行時の通信は見ない —— ★そこを見るのがこの規則である。
    "H-7": [("run-html-visualizer/SKILL.md",
             "**実行時に外部と通信しない。**`fetch` / `XMLHttpRequest` / WebSocket / 動的な `import()` など、**開いたあとにネットワークへ取りに行く書き方をしない**")],
    # ---- 引数の供給者表(HTML_ARG_SUPPLIER)の原典欄。★段5-2(2026-08-19) ------------
    # ★bunken の `BCOL:` と同じ筋である。html には「この引数を誰が供給するのか」を写した表が
    #   実装に無く、H-5 の2つの枝が `supplier="呼び出し"` を**その場に手書き**していた。
    #   分類そのものは正しかったが、**その分類が何に拠るのかを実装のどこも指していなかった** ——
    #   門番の逐語が「責任が…**呼び出し**のものは拾わない」と分岐の根拠にしている当の値である。
    #   段5-2 で門番を html に繋ぐ以上、この値は**原典を指せる形**でなければならない。
    # ★★逐語は「**誰が付けるのか**」を定めている句を丸ごと含める(BCOL が必須度のセルまで
    #   含めるのと同じ理由)。原典が「既定で推定する」等に書き換われば逐語が失われ F-11 が赤くなる。
    # ★鍵が1つなのは、**原典が2つの引数を1句でまとめて定めているから**である。
    #   同じ逐語を2つの鍵に写すと「同じ知識を二重に持たない」の作法に反する。
    #   ★`--artifact` は**同じ括弧の中の別の句**が定めており、この鍵の逐語には入らない
    #     (下の HTML_ARG_SUPPLIER の註も参照。表に入れない理由はそこに書いた)。
    "HARG:全量保持の2引数は付けたときだけ照合される": [
        ("run-html-visualizer/SKILL.md",
         "全量保持は `--expect-count N --count-pattern RE` を付けたときだけ照合される")],
    # ★段5-3(2026-08-20): R系の**本文の引用記法**を定める1句。`RONBUN_CITE_RESP` の原典。
    #   ★逐語に「上付き番号」というセルまで含める(BCOL: が必須度のセルを含めるのと同じ理由)——
    #     原典が本文の記法を書き換えれば逐語が失われ、F-11 が赤くなる。
    #   ★なぜ style-guide.md を指すか: `SKILL.md` の当該句は**相互対応**を求める句であって
    #     「本文の記法が上付きであること」を定めてはいない。`formats.md` の同趣旨の句は
    #     文書タイプごとに3回出るので `locate_quote` が ambiguous になり位置を特定できない。
    #     ★**指せるものだけを指す**(H-0 の註と同じ作法)。
    "RCITE:本文中は上付き番号": [
        ("run-ronbun-shippitsu/references/style-guide.md",
         "本文では「著者（発表年）上付き番号」で引用する")],
    # ---- ★用字用語の1語ごとの原典(申-1・C-2・2026-08-22)。**違反1件ごとに画面へ出る。**
    #   ★★由来: この位置は長らく**整数で持たれていた**(`YOJI_NG` 等の第3要素・79個)。
    #     用語集が1行伸びれば79個が一斉にずれるのに、常設テスト D-6 は「行番号が行数を
    #     超えていないか」しか見ないので**伸びる向きのずれは緑のまま通る**(申-7)。
    #   ★逐語は原典の**表の1行**(◎セルと×セル)である。原典にちょうど1回だけ現れる。
    #   ★★79個のうち9個は**2語で1行を共有する**(「伺う」「窺う」がどちらも
    #     `| うかがう | 伺う、窺う |` を指す等)ので、鍵は **70個**である。
    "YOGO:1人当り": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "| 1人当り | 1人当たり |")],
    "YOGO:あまり・・・": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "| あまり・・・ | 余り・・・ |")],
    "YOGO:第1次": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "| 第1次 | 第一次 |")],
    "YOGO:いまだ": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "| いまだ | 未だ |")],
    "YOGO:うかがう": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "| うかがう | 伺う、窺う |")],
    "YOGO:受入（名詞の時）／受入れ（動詞の時）": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "| 受入（名詞の時）／受入れ（動詞の時） | 受け入れ |")],
    "YOGO:生み出し": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "| 生み出し | 産み出し |")],
    "YOGO:ウエイト": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "| ウエイト | ウェイト |")],
    "YOGO:ウェブサイト": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "| ウェブサイト | ウエブサイト、ホームページ |")],
    "YOGO:ウェブサイト(表記)": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "| ウェブサイト と表記 | HP、ホームページ |")],
    "YOGO:売上": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "| 売上 | 売り上げ |")],
    "YOGO:行う": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "| 行う | 行なう |")],
    "YOGO:およぼす": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "| およぼす | 及ぼす |")],
    "YOGO:3カ月": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "| 3カ月 | 3か月、3ケ月 |")],
    "YOGO:買物": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "| 買物 | 買い物 |")],
    "YOGO:買い替え": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "| 買い替え | 買換え |")],
    "YOGO:稼働率": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "| 稼働率 | 稼動率 |")],
    "YOGO:比べて": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "| 比べて | 較べて |")],
    "YOGO:ケタ": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "| ケタ | 桁 |")],
    "YOGO:つきごと、〜ごと": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "| つきごと、〜ごと | 月毎、〜毎 |")],
    "YOGO:さまざま": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "| さまざま | 様々 |")],
    "YOGO:すみ分け": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "| すみ分け | 棲み分け |")],
    "YOGO:仕組み": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "| 仕組み | 仕組 |")],
    "YOGO:下請": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "| 下請 | 下請け |")],
    "YOGO:すべて": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "| すべて | 全て、総て |")],
    "YOGO:前年比": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "| 前年比 | 対前年比 |")],
    "YOGO:全国シェア": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "| 全国シェア | 対全国シェア |")],
    "YOGO:ただし": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "| ただし | 但し |")],
    "YOGO:ため": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "| ため | 為 |")],
    "YOGO:ちなみに": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "| ちなみに | 因みに |")],
    "YOGO:手がける": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "| 手がける | 手掛ける |")],
    "YOGO:できる": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "| できる | 出来る |")],
    "YOGO:取り組み→取組み": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "| 取り組み→取組み | ")],
    "YOGO:取り組む(熟語)": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "- × 取組む（熟語の場合） → ◎ 取り組む")],
    "YOGO:・・・するなかで、": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "| ・・・するなかで、 | ・・・する中で |")],
    "YOGO:1つ、ひとつ、2つ、ふたつ": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "| 1つ、ひとつ、2つ、ふたつ | 一つ、二つ |")],
    "YOGO:何カ月ぶり": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "| 何カ月ぶり | 何カ月振り |")],
    "YOGO:ほとんど": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "| ほとんど | 殆ど |")],
    "YOGO:見込み": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "| 見込み | 見込 |")],
    "YOGO:みられる": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "| みられる | 見られる |")],
    "YOGO:みずから": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "| みずから | 自ら |")],
    "YOGO:見据える": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "| 見据える | 見すえる |")],
    "YOGO:難しい": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "| 難しい | むずかしい |")],
    "YOGO:めど": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "| めど | 目処、目途 |")],
    "YOGO:・・・もとに": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "| ・・・もとに | ・・・元に、基に |")],
    "YOGO:横ばい": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "| 横ばい | 横這い |")],
    "YOGO:わかる": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "| わかる | 判る、分かる |")],
    "YOGO:30〜40代": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "| 30〜40代 | 30歳〜40歳代 |")],
    "YOGO:カギとなる": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "- × 鍵となる → ◎ カギとなる")],
    "YOGO:かかわらず": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "- × 関わらず、拘わらず → ◎ かかわらず")],
    "YOGO:とどまっている": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "- × 止まっている → ◎ とどまっている")],
    "YOGO:足下": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "| 足下 | 足元 |")],
    "YOGO:〜するうえで": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "| 〜するうえで | 〜する上で |")],
    "YOGO:さらに、（接続詞）": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "| さらに、（接続詞） | 更に、（接続詞） |")],
    "YOGO:更に（副詞）": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "| 更に（副詞） | さらに（副詞） |")],
    "YOGO:したがって、（接続詞）": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "| したがって、（接続詞） | 従って、（接続詞） |")],
    "YOGO:…をみると（※実際にみる(look)行為は「見る」）": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "| …をみると（※実際にみる(look)行為は「見る」） | …を見ると |")],
    "YOGO:わが国": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "| わが国 | 我が国 |")],
    "YOGO:位置づけ": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "| 位置づけ | 位置付け |")],
    "YOGO:とくに": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "| とくに | 特に |")],
    "YOGO:km2（上付き）": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "| km2（上付き） | 平方キロメートル |")],
    "YOGO:m2（上付き）": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "| m2（上付き） | 平方メートル |")],
    "YOGO:m3（上付き）": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "| m3（上付き） | 立方メートル |")],
    "YOGO:cm": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "| cm | センチメートル |")],
    "YOGO:km": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "| km | キロメートル |")],
    "YOGO:kg": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "| kg | キログラム |")],
    "YOGO:ha": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "| ha | ヘクタール |")],
    "YOGO:L": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "| L | リットル（メルマガはカタカナ） |")],
    "YOGO:m": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "| m | メートル |")],
    "YOGO:g": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "| g | グラム |")],
    # ---- 機械化を見送った項目(実行時に原典つきで印字するので、同じくずれる) ----
    "NM:uradori:備考の長文禁止": [
        ("run-uradori/references/daicho-format.md", "**長文禁止**——1行程度に留め")],
    "NM:bunken:J-STAGE記事直URLの併記": [
        ("run-bunken-daicho/references/daicho-format.md", "**DOIとJ-STAGE記事直URLを併記**"),
        ("run-bunken-daicho/references/daicho-format.md", "## リンクのJ-STAGE直URL併記(A-7・2026-07-20)")],
    # ★2026-08-22(B'-1): 逐語は**節の見出しから最後の箇条まで**を指す範囲指定にした。
    #   規定が3つの箇条に分かれており、1句だけを指すと「どれを見送ったのか」が伝わらないため。
    "NM:bunken:要旨欄の出所(印字された値か台帳が導いた値か)": [
        ("run-bunken-daicho/references/daicho-format.md",
         "## 導いた値の書き分け(F-076・2026-08-17)",
         "**原典に無い基準日・時点を書かない。**")],
    # ★2026-08-22(F-105): 逐語は**工程5の見出しから最後の箇条まで**の範囲指定。
    #   規定が「全行を1項目ずつ突き合わせる」「機械にはできない」「訂正結果を1行残す」の
    #   3つに分かれており、1句だけを指すと**何を見送ったのか**が伝わらないため。
    "NM:bunken:書誌の転記の正しさ(リンク先の原典との1項目ずつの突合)": [
        ("run-bunken-daicho/SKILL.md",
         "**★書誌の突合(納品前に必須。省略しない)**",
         "**その申し送りの根拠がこの1行になる**")],
    # ★2026-08-22(網3・F-021): 逐語は**節の見出しから最後の1文まで**の範囲指定。
    #   規定が「承認値を書き換えずに写す」「3項目を照合して1行書く」「食い違いは黙って直さない」に
    #   分かれており、1句だけを指すと**何を見送ったのか**が伝わらないため。
    "NM:bunken:確認ゲートの承認値(ヘッダー中間行)と本体の照合": [
        ("run-bunken-daicho/references/daicho-format.md",
         "### ヘッダーの宣言と本体の照合(F-021・2026-08-17)",
         "読み手が序論に「査読論文のみを対象に12件を収集した」と書けるかどうかは、この1行で決まる。")],
    # ★2026-08-22(網3・2件目): 逐語は**列の要否表のその1行**。★規則 B-3 が読む "BCOL:言語" と
    #   **同じ逐語**を指す —— 同じ規定について「列の不在は対象外」と「値は未検査」の2つを言うため。
    "NM:bunken:言語列(条件付き列。省略が正当だったか)": [
        ("run-bunken-daicho/references/daicho-format.md",
         "| 言語 | 和/英=**本文言語**(主題ではなく本文が書かれた言語。海外事例を扱う和文論文は『和』)。和主英従モード時のみ。**和のみで充足したら列ごと省略可** | 条件付き |")],
    "NM:ronbun:語尾で事実と解釈を区別する": [
        ("run-ronbun-shippitsu/SKILL.md", "**語尾で事実と解釈を区別する。**")],
    # ★2026-08-18(申-5): 残る見送り4件も逐語化した。**「規則として実装していない」ことと
    #   「原典の指し先が腐ってよい」ことは別である** —— 用語集が1行伸びれば同じように腐る。
    #   これで NOT_MECHANIZED は8件すべてが逐語を持つ。
    #   ★常設テスト F-9 の歯止めは**架け替えた**(「逐語なしが4件」→「見送り項目そのものが8件」)。
    #     数えるものが変わっただけで、外していない —— 目的は「見送りが黙って増えないこと」である。
    "NM:ronbun:単位「トン◎ / t×」": [
        # ★単位表で**左右が反転している唯一の行**(他は 記号|読み、この行だけ ◎トン|×t)
        ("run-ronbun-shippitsu/references/kosei-yogo.md", "| トン | t |")],
    "NM:ronbun:会社名は正式名で(株)(有)もつける": [
        # ★節に本文が無く**見出しが規定そのもの**。R-6・R-9 と同じく見出し記号を含めず規定文だけを指す
        ("run-ronbun-shippitsu/references/kosei-yogo.md", "正式名で(株)、(有)もつける")],
    "NM:ronbun:東京23区・政令市の区名表記": [
        ("run-ronbun-shippitsu/references/kosei-yogo.md",
         "市は「〇〇市」と表記。政令区の区名は書かない。", "東京23区は「東京都〇〇区」で表記。")],
    "NM:ronbun:九州・沖縄・山口の町村に県名を付ける": [
        # ★R-19(市の規則)が指す行とは**別の行**であることを、ここで固定する
        ("run-ronbun-shippitsu/references/kosei-yogo.md", "町村は「△△県■■町」と表記。")],

    # ---- 判定の本文・理由に手書きされていた原典(申-2)と、水準表の原典欄(申-3) ----
    # ★2026-08-18 の工事。**規則の原典欄(53本)は逐語で閉じたが、行番号は別の場所にも残っていた。**
    #   ここが腐ると「規定による対象外(not_applicable)」の**証明が嘘になる** ——
    #   `DESIGN.md` §7-1 が名指しした穴そのものである:
    #     「not_applicable の原典引数が嘘でも通る。行番号の上限は既存テストが見るが、内容の一致は見ない」
    #   ★実際に1件腐っていた: B-7 の skip は `daicho-format.md:68-81` を名乗っていたが、
    #     2026-08-17 の bunken 改訂でその範囲は**別の規定(推奨欄の下限)**になっていた(正しくは 174-197)。
    #     これは「予防」ではなく**現に嘘をついていた原典**である。
    # ★規則自身の原典と同じものは鍵を作らない(`r.origin` を使う)。**同じ知識を二重に持たない。**
    #   鍵を作ったのは「規則の原典より**狭い一点**を指す必要がある」場合だけである。
    "SK:U-16:水準①②は一次必須でない": [
        ("run-uradori/references/source-hierarchy.md",
         "水準③: 一次必須(到達不能なら代替探索の上、未到達として残す)"),
        ("run-uradori/references/source-hierarchy.md", "台帳の備考欄に「一次」「二次」を書く")],
    "SK:U-17:到達範囲は水準①では任意": [
        ("run-uradori/references/daicho-format.md", "| 到達範囲 | 原典の**どこまで読んだか**")],
    # ★MSG: は**画面に出る**文言に埋め込む原典である(他の鍵より腐りの害が大きい)
    "MSG:U-0:未検査は合格ではない": [
        ("run-uradori/SKILL.md", "**「未検査(―)」が出た項目は「合格」ではない。**")],
    "MSG:H-4:暗い画面は頼まれた時だけ": [
        ("run-html-visualizer/SKILL.md", "暗い画面(`prefers-color-scheme` と `:root[data-theme]` への対応)は、ユーザーが頼んだ時だけ付ける")],
    # ★★H-5 が**合格したとき**に画面へ出す開示(2026-08-24・裁定「規定書と画面の両方」)。
    #   ★合格の行にしか出さない —— 未検査・不一致の行に「機械では検証できない」と添えると、
    #     突合が**行われなかった**ことに注釈が付いて「考慮のうえ通した」ように読める。
    #   ★規定書側(run-html-visualizer/SKILL.md)と画面側の**両方**に置くのが裁定である。
    #     片方を消しても気づけるよう、逐語で繋いである(逐語が消えれば F-11 が赤くなる)。
    "MSG:H-5:件数の出どころは機械では検証できない": [
        ("run-html-visualizer/SKILL.md",
         "2引数を正しく選ぶ責任は機械ではなく渡す側にあり、ここは終了コードでは守られていない")],
    # ★門番が**画面に出す**文言に埋める原典。種別ごとに別である ——
    #   bunken の納品物の画面に uradori の SKILL.md を出したら、書き手はどこを読めばよいか分からない。
    "MSG:B-0:検査できなかった項目が残っている": [
        ("run-bunken-daicho/SKILL.md",
         "**`exit 3` は「検査できなかった項目が残っている」**の意味であり")],
    "MSG:R-0:検査できなかった項目が残っている": [
        ("run-ronbun-shippitsu/SKILL.md",
         "**`exit 3` は「検査できなかった項目が残っている」**の意味であり")],
    "MSG:H-0:検査できなかった項目が残っている": [
        ("run-html-visualizer/SKILL.md",
         "**`exit 3` は「検査できなかった項目が残っている」**の意味であり")],
    # ---- 水準表(URADORI_COL_REQ)の原典欄。**判定に効く知識の出どころ**である(申-3) ----
    # ★列の要否を決めているのは**表の行そのもの**なので、行を指す(見出しではない)。
    "COL:分類": [
        ("run-uradori/references/daicho-format.md",
         "| 分類 | 数値・規格 / 制度・法令 / 実在性 / 文献 / 相場・時事 |")],
    # ★COL:逐語 は U-15 の skip(水準①②では逐語の全行必須が効かない)とも**同じ行**を指すので共用する
    "COL:逐語": [
        ("run-uradori/references/daicho-format.md", "| 要旨/逐語 | ②は原文の要旨。")],
    "COL:アクセス日": [
        ("run-uradori/references/daicho-format.md", "| アクセス日 | 実際にアクセスして確認した日付")],
    "COL:備考": [
        ("run-uradori/references/daicho-format.md", "| 備考 | 一次/二次の別、未到達理由、鮮度、代替文献の有無等。")],

    # ---- 列の要否表(BUNKEN_COL_REQ)の原典欄。★段5-1(2026-08-19) ----------------
    # ★bunken には「列の要否」を1か所に写した表が無かった(`BUNKEN_COLS` は列名の別名しか持たない)。
    #   そのため**原典が「推奨」と定める列の不在**(精読)まで `missing_input(納品物)` に落ちており、
    #   段3の門番に繋ぐと**書き手に直せないもので納品を止める逆向きの事故**になっていた。
    #   門番の逐語:「責任が**規定**(水準表が任意と定める列の不在)…のものは拾わない ——
    #   拾えば書き手に直せないもので納品を止める**逆向きの事故**になる」。
    # ★★逐語は**行を丸ごと**指し、**必須度のセルまで逐語に含める**。ここがこの鍵の要点である ——
    #   原典が「推奨」を「必須」に書き換えた瞬間に逐語が失われ、F-11 が赤くなる。
    #   uradori の `COL:` は内容欄までしか指しておらず、**要否だけが黙って変わっても気づけない**。
    #   要否を写す表の原典は、**要否そのものを逐語に含めること。**
    "BCOL:#": [("run-bunken-daicho/references/daicho-format.md",
                "| # | **台帳全体で一意**の連番(1から)。**空欄・重複を禁じる。表を割っても通しで続ける**(1つ目の表が#1〜#8なら次の表は#9から。表ごとに1へ戻さない)。uradori・ronbun-shippitsuへ渡すときの対応番号になる | 必須 |")],
    "BCOL:書誌": [("run-bunken-daicho/references/daicho-format.md",
                   "| 書誌 | 著者・年・題・誌名・巻(号)・頁。**各文献の詳細/DOIページで確定したもののみ** | 必須 |")],
    "BCOL:種別": [("run-bunken-daicho/references/daicho-format.md",
                   "| 種別 | 査読論文/学会誌(査読不明)/紀要/学位論文/白書・報告書/統計原表(Excel・CSV)/書籍/業界資料/プレプリント。**「査読論文」と書けるのは下記「査読の確定手続き」を踏んだ行だけ** | 必須 |")],
    "BCOL:言語": [("run-bunken-daicho/references/daicho-format.md",
                   "| 言語 | 和/英=**本文言語**(主題ではなく本文が書かれた言語。海外事例を扱う和文論文は『和』)。和主英従モード時のみ。**和のみで充足したら列ごと省略可** | 条件付き |")],
    "BCOL:発見経路": [("run-bunken-daicho/references/daicho-format.md",
                       "| 発見経路 | DB名+検索語、または芋づる(例: CiNii「6次産業化 直売所」/「#3の引用文献より」) | 推奨 |")],
    "BCOL:リンク": [("run-bunken-daicho/references/daicho-format.md",
                     "| リンク | 優先順: DOI/J-STAGE記事ページ(本文に最短)> 機関リポジトリ本文ページ > crid等の書誌ページ(補助)。**全行必須(鉄則)**。J-STAGE収録誌は**DOIとJ-STAGE記事直URLを併記**する(下記A-7) | 必須 |")],
    "BCOL:入手状況": [("run-bunken-daicho/references/daicho-format.md",
                       "| 入手状況 | 下記の語彙から | 必須 |")],
    "BCOL:精読": [("run-bunken-daicho/references/daicho-format.md",
                   "| 精読 | 要旨が**本文精読済み**か**抄録どまり**か。執筆(断定の粒度)・裏取り(照合の粒度)の両下流が参照する | 推奨 |")],
    "BCOL:要旨": [("run-bunken-daicho/references/daicho-format.md",
                   "| 要旨 | 2〜3行。読めた範囲を明記(全文/抄録より)。**自分の言葉でまとめる。原文の文をそのまま使うなら「」で囲んで逐語だと示す**(下記「要旨の書き方」)。**原典に印字されている値と、台帳側が導いた値(合算・換算・推計)を混ぜない**(下記「導いた値の書き分け」) | 推奨 |")],
    # ★2026-10-31(起票 `KICKOFF-nukigaki-b14-b17.md`): 書式の列の表に足した1行。★条件付き = 要旨を本文か抄録から書いた行に要る列。
    "BCOL:抜き書き": [("run-bunken-daicho/references/daicho-format.md",
                       "| 抜き書き | 要旨の元にした原文の1〜2文を「」で原文のまま囲み、場所を添える(例「…といえよう。」(本文 p.6「6. 終わりに」))。**要旨を本文か抄録から書いた行には必ず置き**、題名・書誌・目次だけから書いた行は「なし(書誌のみ)」と書く(下記「抜き書き」) | 条件付き |")],
    "BCOL:用途タグ": [("run-bunken-daicho/references/daicho-format.md",
                       "| 用途タグ | 背景/方法/比較/反論——執筆のどこで使えるか。**4語のいずれかを必ず含める**(下記「推奨欄の下限」) | 推奨 |")],
    # ★アクセス日だけは B-8 の規則の原典と**同じ1行**を指す。uradori の `COL:アクセス日` と U-12 が
    #   同じ逐語を持つのと同じ形である(規則が持つのは「日付形式の規定」、この鍵が持つのは「列の要否」)。
    "BCOL:アクセス日": [("run-bunken-daicho/references/daicho-format.md",
                         "| アクセス日 | 実アクセスした日付 | 必須 |")],

    # ---- 統計原表行の追加メタの必須度表 `TOUKEI_META` が指す原典(2026-08-22) --------
    # ★★`BCOL:` と**同じ作法**である —— 逐語は**必須度の根拠まで含む**。
    #   原典はこの3つの必須度を「必須/推奨」という語では書いていない。書いてあるのは**根拠**のほうで、
    #   逐語がその根拠ごと消えれば F-11 が赤くなる:
    #     ・調査年月 …… 「**年代ゲートはこの調査年月で判定する**」= **下流の判定が現に依存している**
    #     ・statInfId … 「載せると再到達が1手 / **載せないと下流が検索からやり直しになる**」= 不便の説明
    #     ・fileKind … 「0=Excel(**既定**)」= **既定値がある**。無くても既定で動く
    #   ★根拠を欠いた逐語(欄名だけ)を指さない。指すと「必須度を自分で決めた」ことになる。
    "TMETA:調査年月": [("run-bunken-daicho/references/daicho-format.md",
                        "- **調査年月** — e-Stat の統計表検索の結果一覧にある **『調査年月』**(いつ調べたか)をそのまま写す。**年代ゲートはこの調査年月で判定する**")],
    "TMETA:statInfId": [("run-bunken-daicho/references/daicho-format.md", "載せないと下流が検索からやり直しになる")],
    "TMETA:fileKind": [("run-bunken-daicho/references/daicho-format.md", "- **fileKind** — 0=Excel(既定)/1=CSV(表により404あり)")],

    # ---- 受理プロファイル ADMIT_PROFILE の条項が指す原典(申-9・2026-08-18) ----
    # ★鍵を作るのは「規則の原典より**狭い一点**を指す必要がある」ときだけ(SK: と同じ作法)。
    #   ★**新しい逐語は1本も作っていない** —— 6条項とも既に在る逐語に寄せた。
    #   鍵が要らなかった4条項(P-05→U-2 / P-07・P-08→H-2 / P-09→H-1)は規則IDをそのまま使う。
    #
    # ★**なぜその指し先を選んだか**(条項ごとに1行。後から照合できるように残す):
    #   ・P-01 表が読めない …… U-0 は原典を2つ持つが、**表の形を定めているのは台帳側の1句だけ**
    #     である(SKILL.md 側の「未検査は合格ではない」は**扱い**の規定で、形を1文字も定めない)。
    #     ★導入時(git 0b51127)の手書きも U-0 の**台帳側だけ**を写していた(機械で照合済み)。
    #   ・P-04 見出しが読めない …… 同じく U-5 の**台帳側だけ**を指す。節を見出しで区切ることを
    #     定めているのは台帳側で、SKILL.md 側はサマリーの**中身**の規定である。導入時の手書きも同じ。
    #   ・P-05 ヘッダーが読めない …… U-2 の原典は台帳側の1つだけで、それが「キー: 値」の並び
    #     そのものなので**全部**を指す(導入時の手書きは U-2 の原典欄と完全一致だった)。
    #   ・P-07 HTML が解析できない …… H-2 の原典は1つだけ(タグの閉じ整合)。**全部**を指す。
    #   ・P-08 タグが対応しない …… 同上(P-07 と同じ規定に拠る条項である)。
    #   ・P-09 資源辺が読めない …… H-1 の**3つ全部**を指す。★1つも落とせない —— 3つ目は
    #     「`<a href>` は使ってよい」の1句で、**どの属性値を資源辺と数えるか**を決めている。
    #     この条項は資源辺の範囲そのものを開示するものなので、外すと開示が嘘になる。
    "AP:P-01:台帳本体は表で書く": [
        ("run-uradori/references/daicho-format.md", "**台帳本体は必ずMarkdownの表で書く。**")],
    # ★★P-03(`unclosed_fence`)は 2026-10-05(C-5)に原典が入った —— ユーザー裁定「(ア) 説明書に1行足し不合格に」で
    #   uradori と bunken-daicho の説明書に「**コードの囲みは必ず閉じる**」を足した。★P-06 と同じく、札を直して原典を名乗らせる。
    # ★**uradori と bunken の【両方】を指す**(★R系(ronbun)には原典が無く、判定にも繋いでいない)。
    "AP:P-03:コードの囲みは必ず閉じる": [
        ("run-uradori/references/daicho-format.md", "**コードの囲みは必ず閉じる**"),
        ("run-bunken-daicho/references/daicho-format.md", "**コードの囲みは必ず閉じる**")],
    # ★★P-02(`fullwidth_pipe`)・P-10(`encoding_error`)は 2026-10-05(起票 `KICKOFF-juri-tsuzuki.md`)に原典が入った ——
    #   ユーザー裁定 問い1 (ア)・問い3 (ア) で、uradori と bunken-daicho の説明書に1行ずつ足した。★P-03・P-06 と同じく札を直す。
    # ★**uradori と bunken の【両方】を指す**(★R系・html には原典が無く、判定にも繋いでいない)。
    "AP:P-02:表の縦棒に全角の「｜」を使わない": [
        ("run-uradori/references/daicho-format.md", "**表の縦棒に全角の「｜」を使わない**"),
        ("run-bunken-daicho/references/daicho-format.md", "**表の縦棒に全角の「｜」を使わない**")],
    "AP:P-10:台帳は UTF-8 で保存する": [
        ("run-uradori/references/daicho-format.md", "**台帳は UTF-8 で保存する**"),
        ("run-bunken-daicho/references/daicho-format.md", "**台帳は UTF-8 で保存する**")],
    "AP:P-04:必須の節は見出しで区切る": [
        ("run-uradori/references/daicho-format.md", "## サマリー(台帳末尾に必須)",
         "裏付け 8 / 条件付き 2 / 反証 1 / 未確認 1 / 未到達 1(全13主張)")],
    # ★★P-06 は 2026-08-18 の段4(`ecea6df`)で原典が入ったのに、受理プロファイル側が
    #   「機械側の都合」と名乗ったままだった(第2群Bの発見・2026-08-22)。★**原典が後から生えても
    #   自動では札が剥がれない**ので、常設テスト F-31 を同じコミット群で置いてある。
    # ★**逐語は【行を丸ごと】指す**(`BCOL:` と同じ作法)—— この条項が拠っているのは
    #   「兼用しない」だけでなく **「その必須概念が「ある」とは数えない」という結末**までを含む
    #   1行であり、片方だけを指すと**もう片方が黙って書き換わっても気づけない**。
    # ★**uradori と bunken の【両方】を指す**: この条項の発行地点 `collect_ledger_tables` は
    #   両方の台帳を通り、原典の句は**一字一句同じものが両方に在る**(2026-08-22 実測)。
    #   片方だけを指すと、指した側が消えて他方が残ったとき「原典を失った」と嘘を言う。
    "AP:P-06:1つの物理列を2つの必須概念に兼用しない": [
        ("run-uradori/references/daicho-format.md", "**1つの物理列を2つの必須概念に兼用しない。**必須の概念にはそれぞれ**別の列**を立てる。1つの列に2つの概念を詰めた表は、**その必須概念が「ある」とは数えない**。"),
        ("run-bunken-daicho/references/daicho-format.md", "**1つの物理列を2つの必須概念に兼用しない。**必須の概念にはそれぞれ**別の列**を立てる。1つの列に2つの概念を詰めた表は、**その必須概念が「ある」とは数えない**。")],
}

# ★規則表 deliverable-rules.md の**散文**が引く原典(申-4)。表の「原典」欄の外にあるので
#   `sync_rules_md.py` の生成対象ではない。**静的な .md に導出結果は書けない**ので
#   (2026-08-18 の工事で確定した事実)、散文からも行番号を追い出し、逐語だけを置いた。
#   ここに登録した逐語は常設テスト F-11 が「原典にちょうど1回あるか」と
#   「規則表の散文に載っているか」の**両方**から見る。片側だけだと静かにずれる。
# ★棚卸し(evidence\tegaki-census.txt)は散文のリンクを5個としていたが、実測は**7個**だった
#   (「検査できない形の納品物について」節の裸の言及2個が数えられていなかった)。
RULES_MD_PROSE_QUOTES = [
    # R-15 の「◎×が逆転する組」の解説(2組・4行)
    ("run-ronbun-shippitsu/references/kosei-yogo.md", "| さらに、（接続詞） | 更に、（接続詞） | |"),
    ("run-ronbun-shippitsu/references/kosei-yogo.md", "| 更に（副詞） | さらに（副詞） | |"),
    ("run-ronbun-shippitsu/references/kosei-yogo.md", "| したがって、（接続詞） | 従って、（接続詞） | |"),
    ("run-ronbun-shippitsu/references/kosei-yogo.md", "| 法律に従う | 法律にしたがう |"),
    # R-16 の解説(★旧の手書き :70 は別の規定=図表の頁位置を指していた)
    ("run-ronbun-shippitsu/SKILL.md", "**用語集と教授論文の実態が食い違う項目に注意**"),
    # 「検査できない形の納品物について」節(★旧の手書き :16 / :15 / :85 はいずれも別の規定を指していた)
    ("run-uradori/references/daicho-format.md", "**台帳本体は必ずMarkdownの表で書く。**"),
    ("run-bunken-daicho/references/daicho-format.md", "台帳本体は必ず Markdown の表で書く"),
    ("run-uradori/SKILL.md", "**「未検査(―)」が出た項目は「合格」ではない。**"),
]

_ORIGIN_CACHE = {}


def origin_root():
    """原典(4スキル)が置かれている場所。

    通常は本ファイル(`<skills>/tools/checker/`)から2つ上。★環境変数 `CHECKER_SKILLS_ROOT` で
    上書きできるのは、変異解析ハーネスが**隔離場所に写して**常設テストを走らせるためである
    (写した先には4スキルが無いので、原典の在処だけを実物に向ける)。
    """
    env = os.environ.get("CHECKER_SKILLS_ROOT")
    if env and os.path.isdir(env):
        return env
    here = os.path.dirname(os.path.abspath(__file__))          # <skills>/tools/checker
    return os.path.dirname(os.path.dirname(here))              # <skills>


def origin_lines(relpath):
    """原典ファイルの行配列。読めなければ None。"""
    if relpath not in _ORIGIN_CACHE:
        p = os.path.join(origin_root(), relpath.replace("/", os.sep))
        try:
            with open(p, encoding="utf-8") as f:
                _ORIGIN_CACHE[relpath] = f.read().split("\n")
        except OSError:
            _ORIGIN_CACHE[relpath] = None
    return _ORIGIN_CACHE[relpath]


def locate_quote(relpath, quote):
    """逐語から行番号を導出する。返り値 (行番号 or None, 事由)。

    事由: ok / lost(0回=原典を失った) / ambiguous(2回以上=位置を特定できない) /
          unreachable(原典ファイルに到達できない)
    """
    src = origin_lines(relpath)
    if src is None:
        return None, "unreachable"
    hits = [i + 1 for i, ln in enumerate(src) if quote in ln]
    if not hits:
        return None, "lost"
    if len(hits) > 1:
        return None, "ambiguous"
    return hits[0], "ok"


def derive_origin(key, fallback=""):
    """原典の表示文字列を逐語から導出する。返り値 (origin, 問題の一覧)。

    ★逐語を持たない規則は fallback(手書きの origin)をそのまま返す。段階的に強くする形。
    ★1つでも導出できなければ fallback を返し、問題を上へ返す(黙って部分的な位置を出さない)。
    """
    specs = ORIGIN_QUOTES.get(key)
    if not specs:
        return fallback, []
    parts, problems = [], []
    for spec in specs:
        relpath, quotes = spec[0], spec[1:]
        nums = []
        for q in quotes:
            n, why = locate_quote(relpath, q)
            if n is None:
                problems.append((relpath, q, why))
            else:
                nums.append(n)
        if len(nums) == len(quotes):
            parts.append("%s:%s" % (relpath, "-".join(str(x) for x in nums)))
    if problems:
        # ★★ここが「開示は腐る」を塞ぐ1か所である。控えをそのまま返すと、呼び出し側は
        #   **原典を失ったのか、いま導出できたのか**を区別できない —— 画面には
        #   `SKILL.md:101` と live な位置そのままの顔で出続ける(2026-08-25 に現物で再現)。
        # ★★鍵を1つずつ潰さない。**控えを選ぶ地点はここだけ**なので、ここに印を付ければ
        #   `origin_at` / `origin_short` / `rule_meta` / 受理プロファイル / 機械化見送りの
        #   すべての出口が同時に塞がる(★構造で塞ぐ)。
        # ★印を足しても `ORIGIN_RE` は先頭の file:line に当たるので、
        #   `not_applicable` / `needs_human` の「原典 file:line が要る」検査は通る(F-6 を壊さない)。
        return with_lost_note(fallback, problems), problems
    return ", ".join(parts), []


# ★★控えに付ける印。★**`unreachable` には付けない** —— それは「拾ってはいけない検体」である。
#   逐語(`origin_at` の註):「F-6 が『原典に到達できない環境でも検査は動く』ことを保証している」。
#   ★原典ファイルごと到達できないのは**チェッカーを4スキルの外へ写して使う正当な場合**であり、
#   そのとき控えを出すのは腐りではない(到達できなかった原典は report() が別に名指しで印字する)。
#   ★塞ぐのは「**原典は読めているのに、その中に逐語が無い/2か所ある**」= 開示が腐った場合だけ。
ORIGIN_LOST_TAG = "★原典を失った"


def lost_note(problems):
    """喪失の理由を**読める1句**にする。★`unreachable` だけなら空文字(=印を付けない)。"""
    real = [p for p in problems if p[2] != "unreachable"]
    if not real:
        return ""
    return "%s(%s)" % (ORIGIN_LOST_TAG,
                       " / ".join("%s の「%s」が%s" % (f, q[:20], WHY_LABEL[w])
                                  for f, q, w in real))


def with_lost_note(fallback, problems):
    """控えに印を付けて返す。★印が要らなければ控えを**1文字も変えずに**返す(恒等)。"""
    note = lost_note(problems)
    if not note:
        return fallback
    return ("%s %s" % (fallback, note)) if fallback else note


# ★控え(fallback)は**1か所に集める**。呼び出し側に散らすと、散らした数だけ
#   「誰も照合していない手書きの行番号」が生まれる —— それがこの工事で潰している当のものである。
#   ★ここに書く値は**導出結果と1文字も違ってはならない**。常設テスト F-11 が毎回照合する。
# ★★この控えは【生成物】である(2026-08-18)。**手で書き換えず** `python sync_rules_md.py` を走らせること。
ORIGIN_FALLBACK = {
    # ---- ★用字用語の1語ごとの控え(申-1・C-2・2026-08-22)。**生成物。手で書き換えない。**
    "YOGO:1人当り":
        "run-ronbun-shippitsu/references/kosei-yogo.md:10",
    "YOGO:あまり・・・":
        "run-ronbun-shippitsu/references/kosei-yogo.md:12",
    "YOGO:第1次":
        "run-ronbun-shippitsu/references/kosei-yogo.md:13",
    "YOGO:いまだ":
        "run-ronbun-shippitsu/references/kosei-yogo.md:15",
    "YOGO:うかがう":
        "run-ronbun-shippitsu/references/kosei-yogo.md:16",
    "YOGO:受入（名詞の時）／受入れ（動詞の時）":
        "run-ronbun-shippitsu/references/kosei-yogo.md:17",
    "YOGO:生み出し":
        "run-ronbun-shippitsu/references/kosei-yogo.md:18",
    "YOGO:ウエイト":
        "run-ronbun-shippitsu/references/kosei-yogo.md:19",
    "YOGO:ウェブサイト":
        "run-ronbun-shippitsu/references/kosei-yogo.md:20",
    "YOGO:ウェブサイト(表記)":
        "run-ronbun-shippitsu/references/kosei-yogo.md:54",
    "YOGO:売上":
        "run-ronbun-shippitsu/references/kosei-yogo.md:21",
    "YOGO:行う":
        "run-ronbun-shippitsu/references/kosei-yogo.md:23",
    "YOGO:およぼす":
        "run-ronbun-shippitsu/references/kosei-yogo.md:24",
    "YOGO:3カ月":
        "run-ronbun-shippitsu/references/kosei-yogo.md:25",
    "YOGO:買物":
        "run-ronbun-shippitsu/references/kosei-yogo.md:26",
    "YOGO:買い替え":
        "run-ronbun-shippitsu/references/kosei-yogo.md:27",
    "YOGO:稼働率":
        "run-ronbun-shippitsu/references/kosei-yogo.md:28",
    "YOGO:比べて":
        "run-ronbun-shippitsu/references/kosei-yogo.md:29",
    "YOGO:ケタ":
        "run-ronbun-shippitsu/references/kosei-yogo.md:30",
    "YOGO:つきごと、〜ごと":
        "run-ronbun-shippitsu/references/kosei-yogo.md:31",
    "YOGO:さまざま":
        "run-ronbun-shippitsu/references/kosei-yogo.md:32",
    "YOGO:すみ分け":
        "run-ronbun-shippitsu/references/kosei-yogo.md:35",
    "YOGO:仕組み":
        "run-ronbun-shippitsu/references/kosei-yogo.md:38",
    "YOGO:下請":
        "run-ronbun-shippitsu/references/kosei-yogo.md:39",
    "YOGO:すべて":
        "run-ronbun-shippitsu/references/kosei-yogo.md:40",
    "YOGO:前年比":
        "run-ronbun-shippitsu/references/kosei-yogo.md:41",
    "YOGO:全国シェア":
        "run-ronbun-shippitsu/references/kosei-yogo.md:42",
    "YOGO:ただし":
        "run-ronbun-shippitsu/references/kosei-yogo.md:43",
    "YOGO:ため":
        "run-ronbun-shippitsu/references/kosei-yogo.md:44",
    "YOGO:ちなみに":
        "run-ronbun-shippitsu/references/kosei-yogo.md:45",
    "YOGO:手がける":
        "run-ronbun-shippitsu/references/kosei-yogo.md:46",
    "YOGO:できる":
        "run-ronbun-shippitsu/references/kosei-yogo.md:47",
    "YOGO:取り組み→取組み":
        "run-ronbun-shippitsu/references/kosei-yogo.md:49",
    "YOGO:取り組む(熟語)":
        "run-ronbun-shippitsu/references/kosei-yogo.md:148",
    "YOGO:・・・するなかで、":
        "run-ronbun-shippitsu/references/kosei-yogo.md:50",
    "YOGO:1つ、ひとつ、2つ、ふたつ":
        "run-ronbun-shippitsu/references/kosei-yogo.md:51",
    "YOGO:何カ月ぶり":
        "run-ronbun-shippitsu/references/kosei-yogo.md:52",
    "YOGO:ほとんど":
        "run-ronbun-shippitsu/references/kosei-yogo.md:53",
    "YOGO:見込み":
        "run-ronbun-shippitsu/references/kosei-yogo.md:55",
    "YOGO:みられる":
        "run-ronbun-shippitsu/references/kosei-yogo.md:56",
    "YOGO:みずから":
        "run-ronbun-shippitsu/references/kosei-yogo.md:58",
    "YOGO:見据える":
        "run-ronbun-shippitsu/references/kosei-yogo.md:59",
    "YOGO:難しい":
        "run-ronbun-shippitsu/references/kosei-yogo.md:60",
    "YOGO:めど":
        "run-ronbun-shippitsu/references/kosei-yogo.md:61",
    "YOGO:・・・もとに":
        "run-ronbun-shippitsu/references/kosei-yogo.md:62",
    "YOGO:横ばい":
        "run-ronbun-shippitsu/references/kosei-yogo.md:63",
    "YOGO:わかる":
        "run-ronbun-shippitsu/references/kosei-yogo.md:65",
    "YOGO:30〜40代":
        "run-ronbun-shippitsu/references/kosei-yogo.md:66",
    "YOGO:カギとなる":
        "run-ronbun-shippitsu/references/kosei-yogo.md:133",
    "YOGO:かかわらず":
        "run-ronbun-shippitsu/references/kosei-yogo.md:134",
    "YOGO:とどまっている":
        "run-ronbun-shippitsu/references/kosei-yogo.md:140",
    "YOGO:足下":
        "run-ronbun-shippitsu/references/kosei-yogo.md:11",
    "YOGO:〜するうえで":
        "run-ronbun-shippitsu/references/kosei-yogo.md:22",
    "YOGO:さらに、（接続詞）":
        "run-ronbun-shippitsu/references/kosei-yogo.md:33",
    "YOGO:更に（副詞）":
        "run-ronbun-shippitsu/references/kosei-yogo.md:34",
    "YOGO:したがって、（接続詞）":
        "run-ronbun-shippitsu/references/kosei-yogo.md:36",
    "YOGO:…をみると（※実際にみる(look)行為は「見る」）":
        "run-ronbun-shippitsu/references/kosei-yogo.md:57",
    "YOGO:わが国":
        "run-ronbun-shippitsu/references/kosei-yogo.md:64",
    "YOGO:位置づけ":
        "run-ronbun-shippitsu/references/kosei-yogo.md:14",
    "YOGO:とくに":
        "run-ronbun-shippitsu/references/kosei-yogo.md:48",
    "YOGO:km2（上付き）":
        "run-ronbun-shippitsu/references/kosei-yogo.md:78",
    "YOGO:m2（上付き）":
        "run-ronbun-shippitsu/references/kosei-yogo.md:77",
    "YOGO:m3（上付き）":
        "run-ronbun-shippitsu/references/kosei-yogo.md:81",
    "YOGO:cm":
        "run-ronbun-shippitsu/references/kosei-yogo.md:74",
    "YOGO:km":
        "run-ronbun-shippitsu/references/kosei-yogo.md:76",
    "YOGO:kg":
        "run-ronbun-shippitsu/references/kosei-yogo.md:83",
    "YOGO:ha":
        "run-ronbun-shippitsu/references/kosei-yogo.md:80",
    "YOGO:L":
        "run-ronbun-shippitsu/references/kosei-yogo.md:84",
    "YOGO:m":
        "run-ronbun-shippitsu/references/kosei-yogo.md:75",
    "YOGO:g":
        "run-ronbun-shippitsu/references/kosei-yogo.md:82",
    "SK:U-16:水準①②は一次必須でない":
        "run-uradori/references/source-hierarchy.md:12, run-uradori/references/source-hierarchy.md:27",
    "SK:U-17:到達範囲は水準①では任意": "run-uradori/references/daicho-format.md:38",
    "MSG:U-0:未検査は合格ではない": "run-uradori/SKILL.md:90",
    "MSG:H-4:暗い画面は頼まれた時だけ": "run-html-visualizer/SKILL.md:86",
    "MSG:H-5:件数の出どころは機械では検証できない": "run-html-visualizer/SKILL.md:103",
    "MSG:B-0:検査できなかった項目が残っている": "run-bunken-daicho/SKILL.md:61",
    "MSG:H-0:検査できなかった項目が残っている": "run-html-visualizer/SKILL.md:101",
    "MSG:R-0:検査できなかった項目が残っている": "run-ronbun-shippitsu/SKILL.md:87",
    "COL:分類": "run-uradori/references/daicho-format.md:32",
    "COL:逐語": "run-uradori/references/daicho-format.md:37",
    "COL:アクセス日": "run-uradori/references/daicho-format.md:39",
    "COL:備考": "run-uradori/references/daicho-format.md:40",
    "BCOL:#": "run-bunken-daicho/references/daicho-format.md:81",
    "BCOL:書誌": "run-bunken-daicho/references/daicho-format.md:82",
    "BCOL:種別": "run-bunken-daicho/references/daicho-format.md:83",
    "BCOL:言語": "run-bunken-daicho/references/daicho-format.md:84",
    "BCOL:発見経路": "run-bunken-daicho/references/daicho-format.md:85",
    "BCOL:リンク": "run-bunken-daicho/references/daicho-format.md:86",
    "BCOL:入手状況": "run-bunken-daicho/references/daicho-format.md:87",
    "BCOL:精読": "run-bunken-daicho/references/daicho-format.md:88",
    "BCOL:要旨": "run-bunken-daicho/references/daicho-format.md:89",
    "BCOL:抜き書き": "run-bunken-daicho/references/daicho-format.md:90",
    "BCOL:用途タグ": "run-bunken-daicho/references/daicho-format.md:91",
    "BCOL:アクセス日": "run-bunken-daicho/references/daicho-format.md:92",
    "TMETA:調査年月": "run-bunken-daicho/references/daicho-format.md:224",
    "TMETA:statInfId": "run-bunken-daicho/references/daicho-format.md:227",
    "TMETA:fileKind": "run-bunken-daicho/references/daicho-format.md:228",
    "HARG:全量保持の2引数は付けたときだけ照合される": "run-html-visualizer/SKILL.md:101",
    "RCITE:本文中は上付き番号": "run-ronbun-shippitsu/references/style-guide.md:61",
}


def origin_at(key):
    """`skip_as`/`observe` に渡す原典 `file:line` を**逐語から導出する**(申-2・申-3)。

    ★なぜ控え(fallback)を残すか —— **F-6 が「原典に到達できない環境でも検査は動く」ことを
      保証しているから**である。導出できない環境で空文字を返すと `observe()` の検査
      (`not_applicable`/`needs_human` には原典の file:line が要る)で落ち、**道具が死ぬ**。
      控えは横着ではなく、**既存の保証から強制されている**。
    ★控えの役目は `RULES` 第4要素と同じ(原典に到達できない環境でだけ表に出る)。ただし
      **控えが導出結果とずれていないことを常設テスト F-11 が毎回見る**点が違う ——
      この照合が無かったために、B-7 の skip は 106行ぶんずれたまま誰にも気づかれなかった。
    """
    return derive_origin(key, ORIGIN_FALLBACK[key])[0]


def origin_short(key):
    """★**画面に出る**文言へ埋め込む短い形「ファイル名:行」を導出する。

    1か所だけを指す鍵に使う。複数を指す鍵に当てると、どれを指しているのか読み手に伝わらないので、
    そのときは省略せず全体を返す(黙って先頭や末尾を選ばない)。
    """
    o = origin_at(key)
    # ★印は落とさない。★短縮は**印より前の部分だけ**に当てる —— 印の中には原典のパスが
    #   入っているので、そのまま `rsplit("/")` すると位置ではなく理由の途中で切れる。
    head, sep, tail = o.partition(" " + ORIGIN_LOST_TAG)
    short = head.rsplit("/", 1)[-1] if ", " not in head else head
    return short + sep + tail


WHY_LABEL = {"lost": "見つからない(原典を失った)", "ambiguous": "2か所以上あり位置を特定できない",
             "unreachable": "原典ファイルに到達できない"}


def code_span(text):
    """逐語を Markdown のコードスパンにする。★中身を1文字も加工しない。

    `|` は表のセルを割るので GFM の作法どおり `\\|` に逃がす(表示は `|` に戻る)。
    囲みは中身のバッククォートより1本長くするので、逐語に ` が入っても壊れない。
    """
    n = max((len(m) for m in re.findall(r"`+", text)), default=0) + 1
    pad = " " if text.startswith("`") or text.endswith("`") else ""
    return "%s%s%s%s%s" % ("`" * n, pad, text.replace("|", "\\|"), pad, "`" * n)


def origin_md_cell(key, fallback=""):
    """規則表 deliverable-rules.md の「原典」欄を**生成する**。生成できなければ None。

    ★**行番号を1つも書かない。**書けば原典が1行伸び縮みするだけで規則表が黙って腐る
      —— 2026-08-17 の bunken 本体改訂1回で常設テスト F-4 が4件赤くなり、
      「ずれを検出する」形では**本体を1行足すたびに赤くなる**ことが実測された。
      ★**通らないゲートは、偽陽性を出す検査と同じく「無いのと同じ」になる**
      (`30-round-flow.md` §4-B)。だから欄には**原典ファイルへのリンクと逐語だけ**を置く。
    ★逐語は Ctrl+F でそのまま探せるので、行番号より寿命が長く、位置も一意である
      (原典にちょうど1回あることは実行時と常設テスト F-1 が別々に確かめる)。
    ★逐語を持たない規則は None を返す = **生成の対象外**(規則表は手書きのまま)。
    """
    specs = ORIGIN_QUOTES.get(key)
    if not specs:
        return None
    _o, problems = derive_origin(key, fallback)
    if problems:                     # 原典を失った/位置が定まらない —— 生成しない(黙って埋めない)
        return None
    return ", ".join(
        "[%s](../../%s) %s" % (spec[0].rsplit("/", 1)[-1], spec[0],
                               " 〜 ".join(code_span(q) for q in spec[1:]))
        for spec in specs)


def origin_gate(results):
    """★原典を失った規則を ▲(検査不能)へ倒す。**黙って合格にしない。**

    規則が拠って立つ逐語が原典から消えたなら、その規則がいまも規定を写しているかは分からない。
    ○ を出すのは fail-open である。柱2「検査できなかったものを合格に数えない」と同じ筋で ▲ にする。
    ★責任の所在は「人間」(規則表の管理者)である。**書き手には直せない。**

    返り値: [(規則ID, 問題の一覧)]。**原典ファイルごと到達できない場合はここでは倒さない**
    (チェッカーを4スキルの外へ写して使う正当な場合があり、全規則を ▲ にすると道具が死ぬ)。
    ★その代わり黙らせない —— 到達できなかった原典は report() が必ず名指しで印字する。
    """
    lost = []
    for r in results:
        _o, problems = derive_origin(r.rule_id)
        real = [p for p in problems if p[2] != "unreachable"]
        if not real:
            continue
        lost.append((r.rule_id, real))
        detail = " / ".join("%s に「%s」が%s" % (f, q[:24], WHY_LABEL[w]) for f, q, w in real)
        r.findings = []
        r.blocked("原典を失った(規則の拠り所が原典に無い): %s" % detail)
        r.observe("needs_human", assignee="規則表の管理者", origin=r.origin)
    return lost


def origin_unreachable(keys):
    """到達できなかった原典ファイルの一覧(重複を除く)。"""
    out = []
    for k in keys:
        for _f, _q, w in derive_origin(k)[1]:
            if w == "unreachable" and _f not in out:
                out.append(_f)
    return out


def origin_coverage():
    """★原典 file:line を名乗る【地点の全体】と、そのうち逐語で照合できている数を返す。

    ★★`00-principles.md` §12 の条件1「**全体を、測定器の外から取る**」。
      ここでの網は `ORIGIN_QUOTES`(逐語の表)である。全体はその**外**にある4つの表
      —— 規則表 `RULES` / 機械化見送り `NOT_MECHANIZED` / 控えの表 `ORIGIN_FALLBACK` /
      受理プロファイル `ADMIT_PROFILE` —— から取る。★全体を `ORIGIN_QUOTES` 自身から作ると
      外側は**恒等的に 0** になり、自明に緑になる。
    ★★外側 = **逐語を持たない地点**である。逐語を持つ地点は、原典から消えれば
      `derive_origin` が控えに印を付け、規則なら `origin_gate` が ▲ へ倒す。
      逐語を持たない地点は、原典が何行伸び縮みしても**誰にも気づけない**。
    ★「原典を名乗っていない地点」(受理プロファイルの『機械側の都合』など)は
      **規定による対象外**であり、外側ではない。★黙って消さず、規則名と件数で並べて出す
      (`20-evidence-rules.md` §3-D ③「規則名と件数つきで画面に列挙する」)。

    返り値: (原典を名乗る地点の名前, そのうち逐語が無い地点の名前, 原典を名乗らない地点の名前)
    """
    rows = ([("規則" + r[0], r[0], r[3]) for r in RULES]
            + [("見送り:" + ti, nm_key(t, ti), o) for t, ti, o, _w in NOT_MECHANIZED]
            + [("控え:" + k, k, v) for k, v in ORIGIN_FALLBACK.items()]
            + [("受理" + c[0], c[5], c[4]) for c in ADMIT_PROFILE])
    named, outside, unnamed = [], [], []
    for label, key, origin in rows:
        if not origin or not ORIGIN_RE.search(str(origin)):
            unnamed.append(label)
            continue
        named.append(label)
        if key not in ORIGIN_QUOTES:
            outside.append(label)
    return named, outside, unnamed


# 記号。**「―」と「▲」は意味が違う。**
#   ― = 規定によりこの納品物には適用されない項目(検査しなくてよかった)
#   ▲ = 納品物の形が原因で実行できなかった項目(検査したかったのにできなかった)
# この2つを1つの箱に入れていたため、どちらを終了コードに繋いでも事故になっていた
# (前者を繋ぐと html-visualizer は H-6 が常に未検査なので全件不合格、繋がないと F-046 が残る)。
MARK = {"ok": "○", "ng": "✕", "gray": "△", "skip": "―", "blocked": "▲"}
EMPTY_CELL = {"", "-", "--", "—", "–", "ー", "‐", "なし", "N/A", "n/a", "未記入"}

# ---------------------------------------------------------------- 用字用語辞書
# 出典: run-ronbun-shippitsu/references/kosei-yogo.md(行番号は各エントリ末尾)
# 分類の原則: 原典の備考欄に「状況により使い分け」「要検討」がある語、および
#            run-ronbun-shippitsu/SKILL.md:70 でモード依存とされた4組は GRAY に回し、自動判定しない。
YOJI_NG = [
    (r"人当たり",            "1人当り", "YOGO:1人当り"),
    (r"余り",                "あまり", "YOGO:あまり・・・"),
    (r"第一次",              "第1次", "YOGO:第1次"),
    (r"未だ",                "いまだ", "YOGO:いまだ"),
    (r"伺う",                "うかがう", "YOGO:うかがう"),
    (r"窺う",                "うかがう", "YOGO:うかがう"),
    (r"受け入れ",            "受入(名詞)／受入れ(動詞)", "YOGO:受入（名詞の時）／受入れ（動詞の時）"),
    (r"産み出",              "生み出", "YOGO:生み出し"),
    (r"ウェイト",            "ウエイト", "YOGO:ウエイト"),
    (r"ウエブサイト",        "ウェブサイト", "YOGO:ウェブサイト"),
    (r"ホームページ",        "ウェブサイト", "YOGO:ウェブサイト"),
    (r"HP",                  "ウェブサイト", "YOGO:ウェブサイト(表記)"),
    (r"売り上げ(?![るたてれよまら])", "売上(名詞)", "YOGO:売上"),
    (r"行な",                "行う・行って", "YOGO:行う"),
    (r"及ぼ",                "およぼす", "YOGO:およぼす"),
    (r"(か月|ヶ月|ケ月)",    "カ月", "YOGO:3カ月"),
    (r"買い物",              "買物", "YOGO:買物"),
    (r"買換え",              "買い替え", "YOGO:買い替え"),
    (r"稼動率",              "稼働率", "YOGO:稼働率"),
    (r"較べ",                "比べ", "YOGO:比べて"),
    (r"桁",                  "ケタ", "YOGO:ケタ"),
    (r"月毎",                "つきごと", "YOGO:つきごと、〜ごと"),
    (r"毎に",                "〜ごとに", "YOGO:つきごと、〜ごと"),
    (r"様々",                "さまざま", "YOGO:さまざま"),
    (r"棲み分け",            "すみ分け", "YOGO:すみ分け"),
    (r"仕組(?![みまむめも])", "仕組み", "YOGO:仕組み"),
    (r"下請け",              "下請", "YOGO:下請"),
    (r"総て",                "すべて", "YOGO:すべて"),
    (r"対前年比",            "前年比", "YOGO:前年比"),
    (r"対全国シェア",        "全国シェア", "YOGO:全国シェア"),
    (r"但し",                "ただし", "YOGO:ただし"),
    (r"(?<![一-鿿])為[にの]", "ため", "YOGO:ため"),
    (r"因みに",              "ちなみに", "YOGO:ちなみに"),
    (r"手掛け",              "手がける", "YOGO:手がける"),
    (r"出来(?=[るたなまれ])", "できる", "YOGO:できる"),
    (r"取り組み(?![まもた])", "取組み(名詞)", "YOGO:取り組み→取組み"),
    (r"取組む",              "取り組む(動詞)", "YOGO:取り組む(熟語)"),
    (r"する中で",            "するなかで", "YOGO:・・・するなかで、"),
    (r"一つ",                "1つ・ひとつ", "YOGO:1つ、ひとつ、2つ、ふたつ"),
    (r"二つ",                "2つ・ふたつ", "YOGO:1つ、ひとつ、2つ、ふたつ"),
    (r"カ月振り",            "カ月ぶり", "YOGO:何カ月ぶり"),
    (r"殆ど",                "ほとんど", "YOGO:ほとんど"),
    (r"見込(?![みまむめ])",  "見込み", "YOGO:見込み"),
    (r"見られる",            "みられる", "YOGO:みられる"),
    (r"自ら",                "みずから", "YOGO:みずから"),
    (r"見すえ",              "見据え", "YOGO:見据える"),
    (r"むずかしい",          "難しい", "YOGO:難しい"),
    (r"目処",                "めど", "YOGO:めど"),
    (r"目途",                "めど", "YOGO:めど"),
    (r"(?<![一-鿿])元に", "もとに", "YOGO:・・・もとに"),
    (r"(?<![一-鿿])基に", "もとに", "YOGO:・・・もとに"),
    (r"横這い",              "横ばい", "YOGO:横ばい"),
    (r"判る",                "わかる", "YOGO:わかる"),
    (r"分かる",              "わかる", "YOGO:わかる"),
    (r"\d+歳〜\d+歳代",      "30〜40代の形", "YOGO:30〜40代"),
    (r"鍵となる",            "カギとなる", "YOGO:カギとなる"),
    (r"関わらず",            "かかわらず", "YOGO:かかわらず"),
    (r"拘わらず",            "かかわらず", "YOGO:かかわらず"),
    (r"止まっている",        "とどまっている", "YOGO:とどまっている"),
]

YOJI_GRAY = [
    (r"足元",     "足下（原典備考: 状況により使い分け）", "YOGO:足下"),
    (r"する上で", "〜するうえで（原典備考: 状況により使い分け）", "YOGO:〜するうえで"),
    (r"更に",     "接続詞なら「さらに、」、副詞なら「更に」が◎（◎×が逆転する組）", "YOGO:さらに、（接続詞）"),
    (r"さらに",   "接続詞なら「さらに、」、副詞なら「更に」が◎（◎×が逆転する組）", "YOGO:更に（副詞）"),
    (r"従って",   "接続詞なら「したがって、」、動詞なら「法律に従う」が◎（◎×が逆転する組）", "YOGO:したがって、（接続詞）"),
    (r"を見ると", "…をみると（原典備考: 実際にみる(look)行為は「見る」）", "YOGO:…をみると（※実際にみる(look)行為は「見る」）"),
]

YOJI_MODE = [
    (r"全て",     "すべて（新規執筆は用語集どおり／リライトは原文尊重）", "YOGO:すべて"),
    (r"我が国",   "わが国（同上）", "YOGO:わが国"),
    (r"位置付け", "位置づけ（同上）", "YOGO:位置づけ"),
    (r"特に",     "とくに（同上）", "YOGO:とくに"),
]

# 単位は長い順に照合する(「平方キロメートル」を「メートル」で二重検出しないため)
TANI_NG = [
    ("平方キロメートル", "km2(上付き)", "YOGO:km2（上付き）"),
    ("平方メートル",     "m2(上付き)", "YOGO:m2（上付き）"),
    ("立方メートル",     "m3(上付き)", "YOGO:m3（上付き）"),
    ("センチメートル",   "cm", "YOGO:cm"),
    ("キロメートル",     "km", "YOGO:km"),
    ("キログラム",       "kg", "YOGO:kg"),
    ("ヘクタール",       "ha", "YOGO:ha"),
    ("リットル",         "L", "YOGO:L"),
    ("メートル",         "m", "YOGO:m"),
    ("グラム",           "g", "YOGO:g"),
]

KYUSHU_KEN = "福岡|佐賀|長崎|熊本|大分|宮崎|鹿児島|沖縄|山口"

URADORI_HANTEI = ["裏付け", "条件付き裏付け", "反証", "未確認", "未到達"]
# 既知のアーカイブ提供者(U-13)。**この列挙は網羅ではない**ので、○の文言でもそう断る。
# 国立国会図書館WARP は官公庁サイトが消えたときの主要な受け皿で、warp.da.ndl.go.jp と
# warp.ndl.go.jp の2ホストが現用(前者は後者へ301)。素の archive.org/details も対象に含める。
ARCHIVE_HOSTS = re.compile(
    r"web\.archive\.org|archive\.(?:today|is|ph)|megalodon\.jp"
    r"|warp\.(?:da\.)?ndl\.go\.jp|perma\.cc|webcitation\.org|(?<!\w)archive\.org")
URADORI_BUNRUI = ["数値・規格", "制度・法令", "実在性", "文献", "相場・時事"]
# 到達範囲(U-17)。bunken の「精読」列(BUNKEN_SEIDOKU)と同じ軸を測る。
# 文献の行では「本文到達」=bunken の「本文精読済み」として読み替えてよい(daicho-format.md)。
URADORI_TOTATSU = ["本文到達", "抄録どまり"]
# 「原文に到達できていない」と備考が述べていることを示す語(U-9)。
# **この列挙は網羅ではない。**言い換えればすり抜けられるので、出力にもその旨を書き、
# 語彙に頼らない側の検査(逐語が空なら違反)と併用する(20-evidence-rules.md 禁止事項0)。
MITOTATSU_WORDS = re.compile(
    r"未到達|到達不能|到達でき(?:ず|ない|なかった)|アクセスでき(?:ず|ない|なかった)|アクセス不能"
    r"|直読(?:できず|不可|できない)|読め(?:ず|ない|なかった)|入手でき(?:ず|ない|なかった)|未入手"
    r"|閲覧でき(?:ず|ない|なかった)|ペイウォール|有料|会員限定|40[34]")
# 原本に到達できなくても条件付き裏付けにしてよい正規の経路(daicho-format.md のアーカイブの節)
ARCHIVE_WORDS = re.compile(r"アーカイブ|Wayback|wayback|WARP|魚拓|保存版")
# 具体値(数値)を含む主張か。原典の但し書きは「この規律は『具体値・数値』に限る」と範囲を切っている。
GUTAICHI = re.compile(r"[0-9０-９]")
BUNKEN_NYUSHU = ["全文OA", "抄録のみ", "有料", "学内限定", "未入手"]
BUNKEN_SEIDOKU = ["本文精読済み", "抄録どまり"]

DATE_RE = re.compile(r"(\d{4})[-/年\.]\s*(\d{1,2})[-/月\.]\s*(\d{1,2})日?")


# ---------------------------------------------------------------- 汎用ユーティリティ
class Result:
    """1規則分の検査結果。status は ok / ng / gray / skip。"""

    def __init__(self, rule_id, title, origin):
        self.rule_id = rule_id
        self.title = title
        self.origin = origin
        self.status = "ok"
        self.findings = []   # (lineno or None, message)
        self.note = ""
        # 段0で足した欄。**既存の判定・記号・集計行1行目には一切影響しない。**
        # 7状態(柱2)を記録する場所。未設定の間は status からの推定を state_guess() が返す。
        self.state = None
        self.state_info = {}

    def fail(self, lineno, msg):
        self.status = "ng"
        self.findings.append((lineno, msg))

    def gray(self, lineno, msg):
        if self.status != "ng":
            self.status = "gray"
        self.findings.append((lineno, msg))

    def skip(self, reason):
        """規定によりこの納品物には適用されない(検査しなくてよかった)。"""
        self.status = "skip"
        self.note = reason

    def blocked(self, reason):
        """納品物の形が原因で実行できなかった(検査したかったのにできなかった)。
        **合格には数えない。**門番規則がこれを数えて違反を立てる。"""
        self.status = "blocked"
        self.note = reason

    def ok_note(self, note):
        self.note = note

    def observe(self, state, **info):
        """★段1: 7状態(柱2)を**記録するだけ**。記号(status)も集計行1行目も1つも動かさない。

        判定へ繋ぐのは段3以降(種別ごとに独立したフラグで1つずつ本番の納品物を通す)。
        ★**要点は引数である。**原典を書けない「規定による対象外」は、この関数を通れない。
        母集合を数えていなければ「検査できた」を名乗れない。
        **後から規則を足す者も、この制約から逃げられない。**
        """
        if state not in STATE_TO_STATUS:
            raise ValueError("7状態のいずれかであること: %r" % state)
        if state in ("not_applicable", "needs_human"):
            o = info.get("origin")
            if not o or not ORIGIN_RE.search(str(o)):
                raise ValueError("%s には原典の file:line が要る: rule=%s origin=%r"
                                 % (state, self.rule_id, o))
        if state == "needs_human" and not info.get("assignee"):
            raise ValueError("needs_human には割当先が要る: rule=%s" % self.rule_id)
        if state == "missing_input":
            if not info.get("what"):
                raise ValueError("missing_input には欠けた物の名前が要る: rule=%s" % self.rule_id)
            if info.get("supplier") not in SUPPLIERS:
                raise ValueError("missing_input の supplier は %s のいずれか: rule=%s supplier=%r"
                                 % ("/".join(SUPPLIERS), self.rule_id, info.get("supplier")))
        if state == "partial":
            if not isinstance(info.get("read"), int) or not isinstance(info.get("total"), int):
                raise ValueError("partial には 読めた数/全体数 が要る: rule=%s" % self.rule_id)
        if state == "clean":
            if not isinstance(info.get("scanned"), int) or not isinstance(info.get("targets"), int):
                raise ValueError("clean には母集合数と対象数が要る: rule=%s" % self.rule_id)
            # ★★2026-08-22(裁定 C-6 + 未決5)。**7コンストラクタと同じ強さに揃えた。**
            #   ★由来: 申-15 の条件A で「7本の守りが `observe` に1対1で在るか」を
            #     **同じ引数を両方へ渡して16通り**試したところ、★**食い違いはこの2つだけ**だった ——
            #     `clean()` は拒むのに `observe` は通す、という**片側だけの守り**である。
            #   ★★**この2つは「新しい品質基準」ではない。**算術としてありえない申告
            #     (母集合が負 / 対象が母集合より多い)を拒むだけであり、
            #     `DESIGN.md` G10「読み取った全物理行が…**ちょうど1つ**に勘定され、
            #     **勘定が合わない実行は終了コード0を出さない**」の内側にある。
            #   ★★**ユーザーの裁定(2026-08-22)である。**原典が定めた句があるわけではない ——
            #     「7本を落とすか、`observe` を強くするか」の二択で**後者が選ばれた**。
            #     ★次に読む者へ: **これは「原典が決めた」ではなく「ユーザーが決めた」**である。
            #   ★実測: 足しても常設テストは全緑のまま(=現に誰も違反していない)。
            #     足すのは「いま通っているものを止める」工事ではなく「**次に間違える者を止める**」工事。
            if info["scanned"] < 0 or info["targets"] < 0:
                raise ValueError("clean の母集合数・対象数は0以上の整数が要る: rule=%s scanned=%r targets=%r"
                                 % (self.rule_id, info["scanned"], info["targets"]))
            if info["targets"] > info["scanned"]:
                raise ValueError("対象数が母集合数を超えている: rule=%s %d/%d"
                                 % (self.rule_id, info["targets"], info["scanned"]))
        self.state = state
        self.state_info = info
        return self

    def state_guess(self):
        """7状態のうちどれかを返す。**段1で明示的に振り分けるまでの暫定の読み**である。

        ★推定であることを隠さない: `state` が None のものは「まだ振り分けていない」という
        事実そのものであり、段1の進捗はこの None の数が減ることで測る。
        """
        if self.state:
            return self.state
        return {"ok": "clean", "ng": "violation", "gray": "needs_human",
                "skip": "not_applicable", "blocked": "partial"}[self.status]


def nm_key(target, title):
    """機械化見送り項目の鍵(ORIGIN_QUOTES 用)。"""
    return "NM:%s:%s" % (target, title)


def rule_meta(rule_id):
    for rid, _target, title, origin, _lv in RULES:
        if rid == rule_id:
            # ★逐語を持つ規則は、ここで**行番号を導出する**(表に書いてある数字を信じない)。
            return title, derive_origin(rid, origin)[0]
    raise KeyError(rule_id)


def strip_code_fences(lines):
    """フェンス付きコードブロックの行を空文字に置き換える(行番号を保つため削除はしない)。"""
    out, in_fence = [], False
    for ln in lines:
        if re.match(r"^\s*(```|~~~)", ln):
            in_fence = not in_fence
            out.append("")
            continue
        out.append("" if in_fence else ln)
    return out


def mask_noise(text):
    """URL・インラインコード・Markdownリンク先を伏せ字にする(用字用語・数値検査の誤検出防止)。"""
    text = re.sub(r"`[^`]*`", lambda m: "　" * len(m.group(0)), text)
    text = re.sub(r"https?://\S+", lambda m: "　" * len(m.group(0)), text)
    text = re.sub(r"\]\([^)]*\)", lambda m: "　" * len(m.group(0)), text)
    return text


def split_row(s):
    s = s.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", s)]


def is_separator_row(cells):
    return bool(cells) and all(re.fullmatch(r":?-{2,}:?", c.replace(" ", "")) for c in cells)


def norm_header(cell):
    c = cell.replace("*", "").replace("　", "").strip()
    c = re.sub(r"\s+", "", c)
    return c


def parse_md_tables(lines):
    """Markdown表を全部拾う。返り値: [{'header':[...], 'hline':int, 'rows':[(lineno,[cells])]}]"""
    tables, i, n = [], 0, len(lines)
    while i < n - 1:
        cells = split_row(lines[i]) if "|" in lines[i] else None
        nxt = split_row(lines[i + 1]) if "|" in lines[i + 1] else None
        if cells and nxt and len(cells) >= 2 and is_separator_row(nxt) and len(nxt) == len(cells):
            header = [norm_header(c) for c in cells]
            rows, j = [], i + 2
            while j < n and "|" in lines[j] and lines[j].strip():
                rc = split_row(lines[j])
                if is_separator_row(rc):
                    j += 1
                    continue
                rows.append((j + 1, rc))
                j += 1
            tables.append({"header": header, "hline": i + 1, "rows": rows})
            i = j
            continue
        i += 1
    return tables


def find_col(header, aliases):
    """別名リストのどれかに一致する列の index を返す。無ければ None。"""
    for idx, h in enumerate(header):
        for a in aliases:
            if h == a or a in h:
                return idx
    return None


def cell(row, idx):
    if idx is None or idx >= len(row):
        return ""
    return row[idx].strip()


def is_empty(v):
    return v.replace("*", "").strip() in EMPTY_CELL


def looks_like_link(v):
    """セル内のどこかにURL・ファイルパスがあれば可(「抄録(PubMed): https://…」のような
    ラベル接頭辞つきの実例が台帳にあるため、先頭一致では判定しない)。"""
    v = v.strip()
    if re.search(r"(https?|file)://\S", v):
        return True
    if re.search(r"\bdoi:\s*10\.\d{4}", v, re.I):
        return True
    for cand in re.findall(r"\]\(([^)]+)\)", v) + [v]:     # Markdownリンク先も見る
        c = cand.strip("<>`() 　")
        if re.search(r"[A-Za-z]:[\\/]", c) or c.startswith(("/", "./", "../", "~/", "\\\\")):
            return True
        if re.search(r"\.(pdf|xlsx?|csv|docx?|md|html?|txt|pptx?)(\s|$)", c, re.I):
            return True
    return False


# ================================================================================
# 事実の関門【段階A】—— 納品物に書かれたリンクが、現に届くか
# --------------------------------------------------------------------------------
# ★出所= ユーザーの裁定(2026-08-29)。起票 `KICKOFF-jijitsu-kanmon-A.md`(★追補が正本)。
#
# ★★**この段階が見るのは「リンクが届くか」だけである。**
#   書誌がリンク先と合っているか(段階B)・本文の内容と合っているか(段階C)は**見ていない**。
#   ⇒ 見ていない範囲は `report()` が**走行のたびに画面へ出す**(`00-principles.md` §12)。
#
# 🔴★★**決定性**(`20-evidence-rules.md` §1 [挙動-コード] の合格条件の逐語
#   「決定的であること(乱数・時刻依存なら固定方法を明記)」):
#   **判定は、保存した取得結果だけから決まる。**外へ出るのは取得のときだけである。
#   ⇒ **判定の3母集団の走行は、一度もネットワークに触らない。**
#   ★これが無いと「チェッカーが変わったから動いた」と「外の世界が変わったから動いた」が
#     区別できなくなる(★指摘の出所= 前任の司令塔16)。
#
# 🔴★★**「叩いていない」を黙って合格にしない**(起票 §2-1):
#   取得結果が渡されない走行は▲(検査不能・責任=**呼び出し**)であり、終了コードは 3 になる。
#   ★**既にある形をそのまま使っている** —— 期待件数を渡さない走行を「測っていない」として
#     扱うユーザー裁定(2026-08-23)と同じ筋である。逐語(`runs/checker/REPRODUCE.md` §3-2):
#     「期待件数が渡されないときは『測っていない』として扱います」
#     「『期待件数は渡されたときだけ照合される』は道具の都合であって、
#       『測ったことにしてよい』根拠ではありません」
#   ★★**記号を「―」ではなく▲にした理由**(裁定122・125):
#     `--expect-count` 未指定(H-5)は「―」だが、こちらは▲にした。**終了コードはどちらも 3 で同じ**で、
#     変えたのは**人の目に入る強さ**だけである。★ユーザーの逐語=「**違反0のときが一番危ない**」。
#   ★どちらの記号でも門番は拾わない(責任=呼び出しは書き手に直せないため)。→ `check_kanmon` の註。

# ★この段階が【見ていない】範囲。★走行のたびに、そのまま画面へ出す。★条件を付けて省かない。
LINK_UNSEEN = (
    "書誌(著者名・誌名・巻号)がリンク先と合っているかは確かめていない —— 段階B",
    "本文の内容と、リンク先に書いてあることが合っているかは確かめていない —— 段階C",
)

# ★取り出しの述語。★**実装に入る前に現物(実在の台帳39本)で数え、偽陽性を2件つかまえた**:
#   ① `[A-Za-z]:[\\/]` は `http://` の中の `p:/` に当たる。素で数えると「ローカルパス風」が
#      **230件**に膨れた(★真の値は 16)。⇒ **先に URL を伏せてから、残りにパスの述語を当てる。**
#   ② `^/` で始まるセル4件は、実体が**「/」1文字**(表の区切り)だった。⇒ 長さで落とす。
# ★★URL の中の括弧(2026-09-28・起票 `KICKOFF-url-kakko-kireru.md`)。
#   🔴★旧版は `)` を字の並びから外し、`(` は通していた ⇒ ★`…/S0378-5122(12)00270-8/fulltext` を `…(12` で切り、
#     ★**別の URL を叩いていた**(段階A と段階C。★段階B の DOI の2本も同じ形)。★全角の `（` `）` は通していた ⇒
#     ★`（URL）` の閉じ括弧を URL に含めていた。
#   ★**`(` が URL に入るのは、中身が ASCII の URL の字だけでできた対 `( … )` の一部としてだけ**(★2段の入れ子まで)。
#     ★閉じない `(`・中身に非ASCII を持つ対・全角の `（` `）` は入れない。★それ以外の字の扱いは、
#     ★下の「丸括弧以外の全角の括弧類」(後半)を除いて旧と1字も変えていない。
#   ★根拠= 起票 §2 の2本の線(括弧を含む正しい URL は最後まで取り出す / 文の括弧と `[文](URL)` の閉じ括弧は含めない)
#     + RFC 3986(URI の字は ASCII。括弧は URI の中に在ってよい)+ CommonMark(リンク先の括弧は対のときだけリンク先の一部)。
#   ★現物(2026-09-28・両方の木の追跡下の .md / .html): 中身が ASCII で閉じる対は4形とも URL の一部だった
#     (`S0378-5122(12)…`・`0305-0548(84)…` ほか)。★非ASCII の対・閉じない `(`・全角の丸括弧は**全部が注か文の括弧**だった。
#   🔴★**見ていない形**(★上と同じ範囲を同じ日に測って、どちらも 0件。★「無い」ではない):
#     URL の末尾に空白なしで付けた ASCII だけの注(`URL(PDF)` の形)は URL に入れる /
#     括弧の中に非ASCII を持つ IRI(`…/wiki/宮崎_(宮崎市)` の形)は括弧の手前で切る。
#   ★★**丸括弧以外の全角の括弧類**(★後半・2026-10-04・担当27-9。★司令塔27 の決定 (b)。`HANDOFF.md` §5 の逐語
#     「URL の全角の閉じ括弧 = (b)」= 「丸括弧以外の全角の閉じ括弧類(`〉` `」` など)は、対になっていないときだけ URL の終わりにする」):
#     ★**閉じ括弧は、同じ URL の中で同じ種類の開き括弧と対になっているときだけ URL に入れる。**★対でなければ URL の終わり。
#       ⇒ `〈URL〉`・`「URL」` の閉じ括弧を URL に含めない / 実在の IRI `…/2023/【観光①】日本における宿泊税の導入効果.pdf` は切らない。
#     ★「全角の括弧類」の範囲(★決定は例で言っている。★範囲は担当27-9 が決めた):
#       ★Unicode の一般カテゴリが Ps(開き)/ Pe(閉じ)で、東アジアの字幅が W / F の字。★`（` `）` は除く(★前半のまま常に止める)。
#       ★表= `_URL_FW_PAIRS`。★常設テスト LA-19 が、表を `unicodedata`(★道具の外)から字の名前で導き直して毎回突き合わせ、
#         ★1字ずつ3つの取り出し口に当てる(★表に手で選んだ字だけを書くと鳴る)。
#     ★対の中身は、URL の字と ASCII の丸括弧の対(`_URL_PAREN`)。★非ASCII を許す(★`【観光①】`)。
#     ★対になっていない開き括弧は、前半と同じく URL に入れる(★決定は閉じ括弧だけを言っている)。
#   🔴★**見ていない形**(★扱いは前半の版= skills `3349f04` のまま):
#     `’` `”`(★一般カテゴリ Pf・字幅 A)/ `＞`(Sm)/ `｣`(半角)/ URL の直後に空白なしで続く和文 /
#     ★全角の括弧類の入れ子(★対の中の別の全角の括弧は対に数えない ⇒ ★外側の閉じ括弧で切る)/
#     ★URL の直後に空白なしで書いた全角の括弧の対(`URL【注】` の形。★対なので URL に入る)。
#   ★前半の版のこの段の逐語(★消さずに写す)=「丸括弧以外の全角の括弧類(`〉` `」` `【` など)と、URL の直後に続く和文は、
#     扱いを1字も変えていない(★起票も原典も決めていない。★実在の IRI に `【…】` を持つものが在る)」。
#   ★記録= `runs/checker/JISSOU-url-kakko-kireru.md`(harness)。
_URL_PAREN_CH = r"(?:(?![<>\"'`|()\]}])[!-~])"
_URL_PAREN = r"\((?:%s|\(%s*\))*\)" % (_URL_PAREN_CH, _URL_PAREN_CH)
# ★全角の括弧類の対(★開き・閉じの2字)。★`〝` は `〞` とも `〟` とも対になる(★日本語の組みは `〝…〟`)。
_URL_FW_PAIRS = (
    "〈〉", "《》", "「」", "『』", "【】", "〔〕", "〖〗", "〘〙", "〚〛", "〝〞", "〝〟", "［］", "｛｝", "｟｠",
    "\u2329\u232a",                                                    # ★山括弧の旧い字(★見た目は `〈〉` と同じ)
    "\ufe17\ufe18", "\ufe35\ufe36", "\ufe37\ufe38", "\ufe39\ufe3a", "\ufe3b\ufe3c", "\ufe3d\ufe3e",
    "\ufe3f\ufe40", "\ufe41\ufe42", "\ufe43\ufe44", "\ufe47\ufe48",    # ★縦書きの形
    "\ufe59\ufe5a", "\ufe5b\ufe5c", "\ufe5d\ufe5e",                    # ★小さい形
)
_URL_FW_OPEN = "".join(sorted(set(p[0] for p in _URL_FW_PAIRS)))
_URL_FW_CLOSE = "".join(sorted(set(p[1] for p in _URL_FW_PAIRS)))


def _url_run(stop):
    """URL の字の並び(★1字以上)を組む。★`stop` は、その口で URL を終える字(★文字クラスの中身)。

    ★字の並びから丸括弧と全角の括弧類を外し、★ASCII の丸括弧の対(`_URL_PAREN`)・同じ種類の全角の括弧の対・
      対になっていない全角の開き括弧、としてだけ戻す。★取り出し4本がこの1か所を共有する。
    """
    ch = "[^%s%s%s]" % (stop, _URL_FW_OPEN, _URL_FW_CLOSE)
    fw_pair = "|".join("%s(?:%s|%s)*%s" % (p[0], ch, _URL_PAREN, p[1]) for p in _URL_FW_PAIRS)
    return "(?:%s|%s|%s|[%s])+" % (ch, _URL_PAREN, fw_pair, _URL_FW_OPEN)


LINK_URL_RE = re.compile(r"https?://" + _url_run(r"\s<>\"'`|()（）\]}、。，．"))
LINK_MD_RE = re.compile(r"\]\(\s*(" + _url_run(r"()（）\s") + ")")
LINK_DOI_RE = re.compile(r"\bdoi:\s*(10\.\d{4,9}/" + _url_run(r"\s|()（）\]、。") + ")", re.I)
LINK_WINPATH_RE = re.compile(r"[A-Za-z]:[\\/][^\s|]+")
LINK_POSIXPATH_RE = re.compile(r"(?:^|[\s(])((?:\.{1,2}/|~/|/)[^\s|)]{2,})")


def extract_links(cell):
    """セル1つから、段階Aが見る対象を取り出す。→ [(種別, 値)]

    種別: `url`(叩く) / `path`(在るかを見る) / `doi`(★組み立てない= 未検査)
    ★同じ値は1回しか返さない(★同じ URL を1回の走行で二度叩かない・起票 §2-5)。
    ★`doi:` を `https://doi.org/…` へ**組み立てない**(裁定③)——
      組み立て方は原典に書かれていない。**埋めない。**未検査として申告する。
    """
    out, seen = [], set()

    def add(kind, val):
        val = (val or "").strip().strip("<>`,").rstrip(".")
        if len(val) < 2 or (kind, val) in seen:
            return
        seen.add((kind, val))
        out.append((kind, val))

    text = cell or ""
    for m in LINK_MD_RE.findall(text):
        if m.lower().startswith(("http://", "https://")):
            add("url", m)
    for u in LINK_URL_RE.findall(text):
        add("url", u)
    rest = LINK_URL_RE.sub(" ", text)          # ★偽陽性① —— URL を伏せてから当てる
    for d in LINK_DOI_RE.findall(rest):
        add("doi", d)
    for p in LINK_WINPATH_RE.findall(rest):
        add("path", p)
    for p in LINK_POSIXPATH_RE.findall(rest):
        add("path", p)
    return out


LINK_TIMEOUT_DEFAULT = 10.0
LINK_UA = "skill-review-checker/stage-A (link reachability only)"
LINK_EVIDENCE_VERSION = 1

# 🔴★★**この点検プログラムが外へ出る口は、下の `http_probe` ただ1つである。**
#   ★常設テストはここを差し替える(★ネットワークの無い環境でもテストが通るため・起票 §2-3)。
#   ★★**差し替えたまま出荷していないこと**を常設テストが毎回確かめる ——
#     「差し替えたから通った」を「合格」と読ませないためである(起票 §2-3 の逐語)。
LINK_PROBE = None


def link_probe():
    """いま使う取得の口を返す。★差し替えられていなければ `http_probe`。"""
    return LINK_PROBE or http_probe


def http_probe(url, timeout):
    """URL を1本叩いて、届いたかを返す。→ (reach, detail)

    reach の意味:
      `ok`      … 届いた
      `dead`    … ★**現に届かない**(=✕ を立てる)
      `refused` … ★**測れていない**(=▲。★拒まれた・時間切れ・相手側の失敗)

    🔴★★**`refused` を `dead` に倒さない**(裁定①)——
      「届かなかった」と「こちらが拒まれた」は別である。✕ にすると、
      **リンクは正しいのにサイトが機械を拒んでいるだけの行**を違反にする(偽陽性)。
    ★★**`dead` を名乗るのは、証拠があいまいでない場合だけにしてある** ——
      4xx のうち認証・拒否・過多(401/403/429)を除いたものと、**名前が引けない**場合だけ。
      それ以外(接続の失敗・時間切れ・5xx)は `refused` に倒す。
      ★これは検査を弱めているのではない —— **`refused` は合格ではなく▲であり、終了コードは 3** である。
    """
    import socket
    import urllib.error
    import urllib.request

    def _open(req):
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return "ok", "HTTP %s" % getattr(res, "status", "?")

    head = urllib.request.Request(url, method="HEAD", headers={"User-Agent": LINK_UA})
    try:
        return _open(head)
    except urllib.error.HTTPError as e:
        if e.code in (405, 501):
            # ★HEAD を受け付けない相手が現にいる。**GET で当て直す**(★同じ URL を二度は叩かない
            #   という約束は「同じ判定のために二度」の意味であり、方式を変えた1回の再試行は含まない)。
            try:
                return _open(urllib.request.Request(url, headers={"User-Agent": LINK_UA}))
            except urllib.error.HTTPError as e2:
                return (("dead" if 400 <= e2.code < 500 and e2.code not in (401, 403, 429)
                         else "refused"), "GET で HTTP %d" % e2.code)
            except Exception as e2:
                return "refused", "GET で再試行して %s" % e2.__class__.__name__
        if e.code in (401, 403, 429):
            return "refused", "HTTP %d(拒まれた。★リンクの誤りとは限らない)" % e.code
        if 400 <= e.code < 500:
            return "dead", "HTTP %d" % e.code
        return "refused", "HTTP %d(相手側の失敗)" % e.code
    except urllib.error.URLError as e:
        why = getattr(e, "reason", e)
        if isinstance(why, socket.gaierror):
            return "dead", "名前が引けない(%s)" % why
        return "refused", "接続できなかった(%s)" % why.__class__.__name__
    except Exception as e:
        return "refused", "%s" % e.__class__.__name__


def link_evidence_load(path):
    """取得結果を読む。→ (対応表 or None, 読めなかった理由 or None)

    ★**判定はここから読んだものだけで決まる。**★走行中に外へ出ることはない。
    """
    import json
    try:
        with open(path, encoding="utf-8") as f:
            doc = json.load(f)
    except OSError as e:
        return None, "取得結果を開けなかった(%s): %s" % (e.__class__.__name__, path)
    except ValueError as e:
        return None, "取得結果が JSON として読めなかった(%s): %s" % (e.__class__.__name__, path)
    if not isinstance(doc, dict) or "results" not in doc:
        return None, "取得結果の形が違う(results が無い): %s" % path
    ver = doc.get("version")
    if ver != LINK_EVIDENCE_VERSION:
        # ★★黙って読まない。★版が違えば、何を測ったものか分からない。
        return None, "取得結果の版が違う(この道具は %d を読む / 渡されたのは %r): %s" % (
            LINK_EVIDENCE_VERSION, ver, path)
    got = doc["results"]
    if not isinstance(got, dict):
        return None, "取得結果の results が対応表でない: %s" % path
    return got, None


def link_evidence_save(path, results, stamp):
    """取得結果を書く。★あとから監査できる形にする(起票 §2-4)。"""
    import json
    doc = {
        "version": LINK_EVIDENCE_VERSION,
        "stage": "A",
        "tool": "check_deliverable.py",
        "fetched_at": stamp,
        "note": "段階A(リンクが届くか)だけの記録である。書誌の照合(段階B)・"
                "本文の照合(段階C)は含まない。",
        "results": results,
    }
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")


# ★取得したい対象を、判定と**同じ述語**で集めるための置き場。
#   ★★別に書き起こすと、集めた先と判定した先がずれても誰も気づけない(この体系が現に踏んだ形)。
#   ⇒ `--fetch-links` は、判定と同じ経路を1回空走りさせて、ここに溜まったものを叩く。
LINK_WANTED = []

# ★いま走っている検査が使う取得結果。★`main()` が `--links` から読み込んで置く。
#   ★★**None は「叩いていない」を意味する。**★既定は None であり、**黙って合格にはならない**。
LINK_EVIDENCE = None


def link_verdict(kind, value, evidence):
    """1本ぶんの判定。→ (どう数えるか, 説明)

    どう数えるか: `ok` / `dead`(✕) / `unmeasured`(▲)
    """
    if kind == "doi":
        # ★★組み立てない(裁定③)。★永久に未検査になるぶんは、申告文で人に見せる。
        return "unmeasured", "doi: 形式(組み立て方が原典に無いので叩いていない)"
    if kind == "path":
        # ★原典が「ローカル資料はファイルパス」を許している(裁定②)。★許された形の裏を取るだけ。
        return ("ok", "在る") if os.path.exists(value) else ("dead", "そのパスが無い")
    rec = evidence.get(value)
    if not isinstance(rec, dict) or "reach" not in rec:
        return "unmeasured", "取得結果にこの URL が無い"
    reach = rec.get("reach")
    detail = rec.get("detail") or ""
    if reach == "ok":
        return "ok", detail
    if reach == "dead":
        return "dead", detail
    return "unmeasured", detail or "測れていない"


# ★段階Aの規則。★種別ごとに1本ずつ。★**ここが唯一の対応表である**(名前で引かない)。
LINK_RULES = {"uradori": "U-20", "bunken": "B-11"}

# ★★事実の関門【段階A-3】—— 申告を**納品物に同梱**させ、この走行の申告と突き合わせる。
#   ★出所= ユーザー裁定133(2026-08-29)「網まで作る」。起票 `KICKOFF-kanmon-A3-ami.md`。
#
# 🔴★★**この段階が閉じるのは「申告が納品物に載ったか」までである。**
#   ★**チャットに貼ったかは、いまも観測できない。**★それは掟のままである(A-2)。
#   ⇒ ★**境界線**: 「納品物に載ったか」までが網。「チャットに貼ったか」と
#     「チェッカーの居ない環境で定型文を貼ったか」は掟。
#     ★**ただし後者は、その納品物が次に検査された瞬間に必ず捕まる。**
#
# ★★**閉じる不変量(★これが「網」の中身である)**:
#   ★**終了コード 0 ⇒ 段階Aを現に走らせており、かつ【この走行の申告】が納品物に同梱されている。**
#   ★`--links` を渡さなければ U-20/B-11 が ▲ で exit 3。渡しても同梱が無ければここが ✕ で exit 1。
#   ⇒ ★**納品しながら申告を省く経路が無い。**★渡さない自由は在っても、納品する自由は無い。
#
# ★★**囲み(フェンス)にした理由は3つあるが、腐り方が違うので分けて書く**:
#   ① 切り出した見本は囲みが1組なので、そこでは他の規則の母数に入らない ……★条件つき
#   ② 見本の在るファイルは、そもそも納品物として読まれない ……🔴★**現在形の事実**
#      (★2026-08-30 実測= R系の母集団 278本のうち `daicho-format.md` は 0本。★母集団が広がれば偽になる)
#   ③ ★**中身はこの走行の申告と1行も違ってはならないので、申告文以外を1文字も置けない**
#      ……✅★**腐らない(構造)。★正の理由はこれだけである。**
#   🔴★`strip_code_fences` は**印を覚えないトグル**なので、入れ子のときは①が成立しない
#     (★合成入力で実測)。★**それでも③が独立に効く。**★「見えないから安全」ではなく
#     ★**「入れられないから安全」**である。★前者はフェンスの釣り合いに依存し、後者は依存しない。
#
# 🔴★★**「1バイト違わない」とは書かない。**★読み込みは `open(encoding="utf-8")`+`splitlines()`
#   なので、**改行コードは比較の対象外**である。★突き合わせるのは**行の並び**である。
#
# ★印は**つなぎ合わせて作る**(`20-evidence-rules.md` §3-E 作法2。★自分の source を検体にしない)。
STAGE_A_MARK = "stage-a" + " v1"
STAGE_A_FENCES = ("`" * 3, "~" * 3)
STAGE_A_FENCE_OPEN = STAGE_A_FENCES[0] + STAGE_A_MARK
# ★★**`~~~` も受ける理由(★現物)**: 正典の「書き方の見本」は ```markdown の囲みの**中**に在り、
#   同じ印を入れ子にすると見本そのものが壊れる。★常設テスト F-24 がその見本を切り出して
#   `--type bunken` に通し、終了コード0を固定している。★**見本を対象外にはしない。**
STAGE_A_HEAD_RAN = "★事実の関門 段階A —— この納品物について、チェッカーが出した申告をそのまま同梱している"
STAGE_A_TAIL = "★この関門は「リンクが届くか」しか見ていない。合格は、文献が確かめられたという意味ではない。"
# ★チェッカーが無い環境で貼る定型文。★**空にしないための受け皿である。**
#   ★これが在れば、次に誰かがチェッカーを掛けたときに「走らせていない」と現に鳴る。
#   ★無ければ「0件だった」と「申告し忘れた」が区別できないまま残る(=A-2 が塞げなかった形)。
#   🔴★**3行目に句点を置かない。**★原典で鍵括弧に入れると `R-14`(句点は閉じ括弧の外)が鳴る。
#     ★**現に鳴らして、原典の文ではなく道具側の定型文を直した。**
STAGE_A_NORUN = (
    "★事実の関門 段階A —— ★チェッカーを走らせていない環境で作った納品物である",
    "・★リンクが現に届くかは、1本も確かめていない(段階Aを走らせていない)",
    "・★これは「0件だった」ではない。「確かめていない」である",
)
# ★台帳が【自分で】「原典に届いていない」と書いている欄。→ (規則ID, 鍵, 語)
#   ★★**チェッカーが新しく判断するのではない。**★台帳が既に書いている値を写すだけである。
#   ★uradori= 判定サマリーの5語のうち2つ(★`U-5` が台帳本体の実数と突合済み)。
#   ★bunken= 入手状況5語のうち1つ(`B-4`)と精読2語のうち1つ(`B-5`)。
#   🔴★**なぜ申告文に要るか(★現物で実演した)**: 正典の見本 `_test-renkei/uradori-daicho-sample.md`
#     は、段階Aが「リンク6本・届いた6本・未検査0件」と言う一方、**台帳の判定欄には未確認1行・未到達1行**が
#     在る。★リンクが 200 を返しても、その行は**原典に到達できていない**ことがある。
#     ⇒ ★「届いた n本」だけを貼ると、読み手は**台帳が確かめられた**と読む。
STAGE_A_SELF = {
    "uradori": (("U-5", "hantei_counts", ("未確認", "未到達")),),
    "bunken": (("B-4", "nyushu_counts", ("未入手",)),
               ("B-5", "seidoku_counts", ("抄録どまり",))),
}
STAGE_A_EMBED_RULES = {"uradori": "U-21", "bunken": "B-12"}


def fetch_and_save_links(args):
    """`--fetch-links`: 対象を集めて叩き、取得結果を保存する。→ 終了コード(0 なら検査へ進む)

    🔴★★**集める述語を書き起こさない。**★判定が使う `check_link_reach` にそのまま集めさせる ——
      別に書けば、**集めた先と判定した先がずれても誰も気づけない**(この体系が繰り返し踏んだ形)。
      ⇒ ここでは取得結果を渡さずに1回**空走り**させ、`LINK_WANTED` に溜まったものを叩く。
    ★同じ URL は1回しか叩かない(起票 §2-5)。★待ち時間の上限は `--link-timeout`。
    """
    import time
    del LINK_WANTED[:]
    for path in args.files:
        if os.path.isfile(path):
            inspect_file(path, args)          # ★取得結果は None のまま= 空走り
    urls = sorted(set(LINK_WANTED))
    print("★段階A: 取得を始める —— 対象 %d本(重複を除いた数)/ 待ち時間の上限 %g秒"
          % (len(urls), args.link_timeout))
    probe = link_probe()
    if probe is not http_probe:
        # ★★差し替えられた口で取得した結果を、黙って保存しない。★出所を画面に出す。
        print("  ★★注意: 取得の口が差し替えられている(%s)。★この結果は本物の到達ではない。"
              % getattr(probe, "__name__", repr(probe)))
    got = {}
    for i, url in enumerate(urls, 1):
        reach, detail = probe(url, args.link_timeout)
        got[url] = {"reach": reach, "detail": detail}
        print("  [%3d/%d] %-8s %s" % (i, len(urls), reach, url[:100]))
    try:
        link_evidence_save(args.links, got, time.strftime("%Y-%m-%dT%H:%M:%S"))
    except OSError as e:
        print("★★段階A: 取得結果を保存できなかった(%s): %s" % (e.__class__.__name__, args.links),
              file=sys.stderr)
        print("★**保存できない取得は、次の走行で再現できない。**★黙って検査へ進まない。", file=sys.stderr)
        return 2
    n = {"ok": 0, "dead": 0, "refused": 0}
    for rec in got.values():
        n[rec["reach"]] = n.get(rec["reach"], 0) + 1
    print("★段階A: 取得を終えた —— 届いた %d / 届かない %d / 測れていない %d  → %s"
          % (n.get("ok", 0), n.get("dead", 0), n.get("refused", 0), args.links))
    print()
    return 0


def stage_a_self_declared(kind, results):
    """★台帳が【自分で】「原典に届いていない」と書いている行の数。→ [(語, 件数)] or None

    ★**ここでは数え直さない。**★数えているのは `U-5` / `B-4` / `B-5` である ——
      同じ知識を2か所に置くと、原典を直したときに片方だけが古くなる
      (★この体系が5層で踏んだ病。`check_bunken` の `BUNKEN_COL_REQ` の註と同じ理由)。
    ★数が取れないとき(その規則が実行できていないとき)は **None** を返す。**0件と書かない。**
    """
    out = []
    for rid, key, names in STAGE_A_SELF.get(kind, ()):
        r = next((x for x in results if x.rule_id == rid), None)
        d = (r.state_info.get(key) if r is not None else None) or {}
        if not d:
            return None
        out.extend((n, d.get(n, 0)) for n in names)
    return out or None


def stage_a_declaration(kind, results):
    """★段階Aの申告文の正本。→ [行](★囲みの中身。★フェンスの行は含まない)

    🔴★★**ここが唯一の作成地点である。**★画面へ出す文と、納品物に同梱されているかを
      照合する文を**別々に書き起こさない** —— 別に書けば、**ずれても誰も気づけない。**
      ★先例= `fetch_and_save_links` が「集める述語を書き起こさない」と決めているのと同じ理由。
    """
    rid = LINK_RULES.get(kind)
    hit = [x for x in results if x.rule_id == rid] if rid else []
    info = (hit[0].state_info.get("stageA") if hit else None) or {}
    if not info:
        # ★段階Aの結果が取れない(規則が原典を失った等)。★**0で埋めない。**
        return [STAGE_A_HEAD_RAN,
                "・★段階Aの結果が取れなかった —— この走行では、届いたかどうかを1本も言えない"]
    total, n_ok, n_dead = info.get("total", 0), info.get("ok", 0), info.get("dead", 0)
    un = info.get("unmeasured", []) or []
    out = [STAGE_A_HEAD_RAN,
           "・確かめたこと: 台帳のリンク %d本のうち、現に届いた %d本 / 届かなかった %d本"
           % (total, n_ok, n_dead)]
    self_dec = stage_a_self_declared(kind, results)
    if self_dec is None:
        out.append("・★台帳自身の申告は数えられなかった(その列の検査が実行できていない)")
    else:
        out.append("・★台帳が自分で「原典に届いていない」と書いている行: %s"
                   % " / ".join("%s %d件" % (n, c) for n, c in self_dec))
    for line in LINK_UNSEEN:
        out.append("・★確かめていないこと: %s" % line)
    out.append("・★未検査 %d件%s"
               % (len(un), "" if un else "(★0件。★確かめた結果として0である)"))
    for lineno, value, why in un:
        out.append("   - %s%s —— %s"
                   % (("L%d " % lineno) if lineno else "", value[:110], why))
    out.append(STAGE_A_TAIL)
    return out


def find_stage_blocks(lines, want_mark):
    """★納品物から、その印の申告の囲みを取り出す。→ [(開始行, 終了行, [中身の行])]

    🔴★**`body` ではなく生の行を読む** —— `strip_code_fences` が囲みの中身を空にするので、
      `body` からは1行も見えない。★**それは意図した設計である**(囲みの中身が他の規則の母数に
      入らないための形)。⇒ ★この規則だけが生の行を読む。
    ★開いた印と同じ印で閉じるものだけを1組と数える(★``` と ~~~ を取り違えない)。
    🔴★★**印で分ける**(★段階B-2・2026-09-01)。★段階A の囲みと段階B の囲みは、
      **同じ納品物に並んで在りうる。**⇒ ★片方を数えるとき、もう片方を数に入れない。
    """
    out, i, n = [], 0, len(lines)
    while i < n:
        s = lines[i].strip()
        mark = s[:3]
        if mark in STAGE_A_FENCES and s[3:].strip() == want_mark:
            j, inner = i + 1, []
            while j < n and lines[j].strip() != mark:
                inner.append(lines[j])
                j += 1
            out.append((i + 1, j + 1, inner))
            i = j + 1
            continue
        i += 1
    return out


def find_stage_a_blocks(lines):
    """★段階A の申告の囲み。→ 共用の取り出しに、段階A の印を渡すだけ。"""
    return find_stage_blocks(lines, STAGE_A_MARK)


# ★★段階ごとの差分の【唯一の対応表】(★名前で引かない)。★器そのものは共用である。
#   🔴★**新しい器を作らない**(起票 `KICKOFF-kanmon-B2-ami.md` §8-2)——
#     段階B-2 が段階A-3 と違うのは【印・申告文・門・段階の名前】だけであり、
#     判定の骨組み(同梱の有無 / 個数 / 貼り直し / 置き場所 / 1行ずつの照合)は1つで足りる。
#   ★**関数にした理由**= 申告文を作る関数が、この下で定義されるためである。
def stage_embed_spec(stage):
    """→ その段階の差分。★呼ばれた時に解く(定義の順に縛られない)。"""
    if stage == "A":
        return {"name": "段階A", "mark": STAGE_A_MARK, "open": STAGE_A_FENCE_OPEN,
                "rules": LINK_RULES, "key": "stageA", "decl": stage_a_declaration,
                "norun": STAGE_A_NORUN, "column": "リンク列", "input_word": "取得結果",
                "column_note": "リンク列が見つからない(列名の確認が先)",
                "input": "段階Aの取得結果"}
    if stage == "C":
        # ★段階C-2(2026-09-01)。★器は共用のまま、差分だけをここに置く。
        return {"name": "段階C", "mark": STAGE_C_MARK, "open": STAGE_C_FENCE_OPEN,
                "rules": FULLTEXT_RULES, "key": "stageC", "decl": stage_c_declaration,
                "norun": STAGE_C_NORUN, "column": "リンク列・台帳本体の表",
                "input_word": "本文の取得結果",
                "column_note": "リンク列または台帳本体の表が見つからない(列名の確認が先)",
                "input": "段階Cの本文の取得結果"}
    if stage == "B":
        return {"name": "段階B", "mark": STAGE_B_MARK, "open": STAGE_B_FENCE_OPEN,
                "rules": BIBLIO_RULES, "key": "stageB", "decl": stage_b_declaration,
                "norun": STAGE_B_NORUN, "column": "書誌列・リンク列", "input_word": "照会結果",
                "column_note": "書誌列またはリンク列が見つからない(列名の確認が先)",
                "input": "段階Bの照会結果"}
    raise ValueError(stage)


def check_stage_a_embedded(rule_id, kind, lines, results, last_row_line):
    """段階A-3。→ 共用の器に段階A を渡すだけ。"""
    return check_stage_embedded(rule_id, kind, lines, results, last_row_line, "A")


def check_stage_b_embedded(rule_id, kind, lines, results, last_row_line):
    """段階B-2。→ 共用の器に段階B を渡すだけ。★2026-09-01。"""
    return check_stage_embedded(rule_id, kind, lines, results, last_row_line, "B")


def check_stage_c_embedded(rule_id, kind, lines, results, last_row_line):
    """段階C-2。→ 共用の器に段階C を渡すだけ。★2026-09-01。"""
    return check_stage_embedded(rule_id, kind, lines, results, last_row_line, "C")


def check_stage_embedded(rule_id, kind, lines, results, last_row_line, stage):
    """★**申告が納品物に載っており、この走行の申告と一致するか。**★段階A-3 と段階B-2 の共用。

    🔴★★**取得結果(照会結果)が渡されていない走行では、違反を立てない。**★理由は2つある:
      ① ★**判定できない。**★最新かどうかを言うには、この走行の申告が要る。
      ② ★**判定の3母集団は `--links` も `--biblio` も渡さない。**★無条件に違反へ倒すと、
         **exit 3 の群が丸ごと exit 1 になり、その母集団の識別力が失われる**(=測定の劣化)。
    ★★**それでも fail-open ではない。**★原典が「終了コードが 0 以外なら納品しない」と定めており、
      渡さない走行は段階の側の規則(`U-20`/`B-11`/`B-13`)が ▲ にするので
      **exit 3 のまま納品できない**。
      ⇒ ★**exit 0 に到達する道は「渡し、かつ最新の申告を同梱する」しかない。**
    ★**有無だけは、判定できない走行でも数えて画面に出す**(`00-principles.md` §12 条件2)。
    🔴★**渡したが段の側が ▲(測れなかったものが残る)の走行でも、突き合わせず ▲ に留める**(★結論を出していないから)。
      ★その走行の文は「渡されていない」ではなく「渡されたが、段の側が ▲」と書く(2026-10-04・下の註)。
      ★★この扱いは 2026-10-04 のユーザー裁定「▲ のまま」で正式な決まりになった
        (★規則表 U-21・U-23・B-12・B-15・B-16 の行に書いた。起票 `KICKOFF-kanmon-bunmen.md` §2-2)。
    """
    sp = stage_embed_spec(stage)
    r = Result(rule_id, *rule_meta(rule_id))
    rid = sp["rules"].get(kind)
    hit = [x for x in results if x.rule_id == rid] if rid else []
    info = (hit[0].state_info.get(sp["key"]) if hit else None) or {}
    state = info.get("state")
    blocks = find_stage_blocks(lines, sp["mark"])
    seen = {"blocks": len(blocks), "scanned": len(lines),
            "inner": sum(len(b[2]) + 2 for b in blocks)}
    # 🔴★★**段の側が【結論を出したか】で分ける**(★段階C-2・2026-09-01 の一般化)。
    #   ★**段階A・段階B では、これは `state` で分けるのと同値である** ——
    #     結論を出していない状態は `no_column`(―)と `not_fetched`(▲)の2つしかなく、
    #     どちらも段の側の記号が結論ではない。★常設テストが対照つきで固定している。
    #   🔴★**訂正(2026-10-04・起票 `KICKOFF-sankaku-bunmen.md`)**: ★上の「2つしかなく」は偽である。
    #     ★取得結果を渡したが測れなかったものが残った段(状態は `judged`・記号は ▲)も、結論を出していない。
    #     ★常設テスト LD-25 が同値を示したのは5通り(取得あり=全部届いた/取得なし/列なし)だけで、
    #       この形を含まない(★LD-60 の前提がその現物)。★旧版の A-3 は状態で分けていたので、この形は突き合わせの側へ行っていた。
    #     ★この偽の前提のもとで、下の ▲ の文は「渡されていない」の1つだけだった(★下で書き分けた)。
    #   🔴★**段階C だけは `state == "no_column"` が【2つの道】から来る**:
    #     ① リンク列が無い / 台帳本体の表が無い …… 段の側は「―」= **判定できない**
    #     ② 要旨(逐語)の列が無い …………………… 段の側は「◎」= **逐語0本という結論**
    #   ★②を①と同じに扱うと、**原典が「推奨」と定める列の不在で納品を止める**ことになる
    #     (★`SKIP_BY_SPEC` の註と同じ、逆向きの事故)。⇒ **記号で分けず、結論で分ける。**
    concluded = bool(hit) and hit[0].status in ("ok", "ng", "gray")
    if not concluded and state == "no_column":
        skip_as(r, sp["column_note"],
                "missing_input", what=sp["column"], supplier="納品物")
        r.state_info.update(seen)
        return r
    if not concluded:
        # 🔴★★**「渡されていない」と書いてよいのは、段の側が「取っていない」(`not_fetched`)と名乗ったときだけ**
        #   (2026-10-04・起票 `KICKOFF-sankaku-bunmen.md`)。
        #   ★旧版はここが1つの文だったので、取得結果を渡した走行でも、段の側が ▲(測れなかったものが残る)なら
        #     「…が渡されていないので」と出た。★渡したものを「渡されていない」と書くのは
        #     `40-report-format.md` §2 の偽の指摘の形であり、読み手は「取得の指定を付け忘れた」と誤読しうる。
        #   ⇒ ★段の側の状態で【文だけ】を3つに書き分ける。★記号(▲)・7状態・責任は3つとも同じ
        #     (★判定 ✕/▲/○・終了コード・門番が拾う責任を動かさない。★常設テスト LD-63)。
        #   ★取っていない走行の文は1字も変えていない(★判定の3母集団はこの文だけを通る。★LD-61)。
        #   ★既定は「結果が読めない」(★段の規則が落ちた等)。★段の側が状態を名乗ったときだけ上書きする。
        #     ★`elif` で繋がず `if` を2本並べたのは、変異ハーネスの条件の反転が単行の `if` しか反転しないからである
        #       (★`elif` はその死角として開示されている)。★2つの条件を両方とも変異の的に入れるため。
        stage_rule = rid or "?"
        head = ("%sの判定(%s)の結果が読めないので(★取得結果が渡されたかは、この規則からは分からない)"
                % (sp["name"], stage_rule))
        what = "%sの判定の結果(%s)" % (sp["name"], stage_rule)
        # ★2026-10-05(起票 `KICKOFF-kanmon-bunmen.md`): 門番が文を書き分けるため、「渡したか」も名乗る
        #   (★既定は None = 名乗らない。★文と同じく、段の側が状態を名乗ったときだけ上書きする)。
        handed = None
        if state == "not_fetched":
            head = "%sの%sが渡されていないので" % (sp["name"], sp["input_word"])
            what = sp["input"]
            handed = False
        if state == "judged":
            head = ("%sの%sは渡されたが、%sの判定(%s)が ▲(測れなかったものが残っている)で"
                    "結論を出していないので(★取得の指定の付け忘れではない。▲ の中身は %s の行)"
                    % (sp["name"], sp["input_word"], sp["name"], stage_rule, stage_rule))
            what = "%sの結論(%s が ▲)" % (sp["name"], stage_rule)
            handed = True
        r.blocked("%s、同梱された申告が最新かを判定できない"
                  " —— 同梱の囲みは %d個(★有無だけは数えた)" % (head, len(blocks)))
        r.observe("missing_input", what=what, supplier="呼び出し", handed=handed)
        r.state_info.update(seen)
        return r
    want = sp["decl"](kind, results)
    if not blocks:
        r.fail(None, "%sの申告が納品物に同梱されていない —— 出力の `%s` の囲みを、"
                     "台帳本体の表より後ろにそのまま貼る(★チャットに貼るだけでは、"
                     "納品物を受け取った人に届かない)" % (sp["name"], sp["open"]))
    elif len(blocks) > 1:
        r.fail(blocks[1][0], "%sの申告の囲みが %d個ある(1つだけ置く)—— "
               "複数あると、どれが本物か機械にも人にも決まらない" % (sp["name"], len(blocks)))
    else:
        start, _end, inner = blocks[0]
        if list(inner) == list(sp["norun"]):
            r.fail(start, "同梱された申告が「チェッカーを走らせていない」と名乗っているが、"
                          "この走行は%sを現に走らせている —— いま出した囲みに貼り替える"
                          % sp["name"])
        elif last_row_line and start < last_row_line:
            r.fail(start, "申告の囲みが台帳本体の表より前にある(表の最終行は L%d)—— "
                          "表より後ろに置く。前に置くと申告文の中の行番号が動き、"
                          "貼り直しても一致しなくなる" % last_row_line)
        elif list(inner) != list(want):
            n = 0
            for k in range(max(len(inner), len(want))):
                a = inner[k] if k < len(inner) else "(行が足りない)"
                b = want[k] if k < len(want) else "(行が余っている)"
                if a == b:
                    continue
                n += 1
                if n <= 5:
                    tail = "(末尾の空白だけが違う)" if a.rstrip() == b.rstrip() else ""
                    r.fail(start + k, "同梱された申告が、この走行の申告と違う%s / "
                           "同梱= %s / 走行= %s" % (tail, a[:70], b[:70]))
            if n > 5:
                r.fail(start, "…ほか %d行が違う(食い違いは全部で %d行)" % (n - 5, n))
        else:
            r.ok_note("同梱された申告が、この走行の申告と1行も違わない(%d行)" % len(want))
            r.observe("clean", scanned=len(lines), targets=len(inner) + 2)
    r.state_info.update(seen)
    return r


def print_link_disclosure(kind, results):
    """★段階Aの【見ていない範囲】と、★**貼るための申告文**を画面に出す。

    🔴★★**0件でも必ず出す。**★出さないと「0件だった」と「申告し忘れた」が区別できない
      (ユーザー裁定125)。★**違反があるときは人が読む。★違反0のときが一番危ない。**
    ★★**この文はチェッカーが出す** —— 人・エージェントに作文させると、書く人ごとに省かれる語が違う。
    🔴★★**囲みは字下げせずに出す。**★人が選んで写すからである ——
      字下げすると先頭の空白まで写り、突き合わせが落ちる。
      ★`00-principles.md` §11 条件2 の追補「**必要な人の動作を【軽くする】**」の実装である。
    🔴★**チャットに現に貼ったかは、いまも走行から観測できない。**★そこは掟のまま(A-2)であり、
      ★**この関数が毎回そう申告する**(=「閉じていない」を黙って落とさない)。
    """
    if kind not in LINK_RULES:
        return
    print("  [★事実の関門 段階A —— 下の囲みを**納品物に同梱**し、チャット本文にも写すこと"
          "(★違反0でも貼る)]")
    print(STAGE_A_FENCE_OPEN)
    for line in stage_a_declaration(kind, results):
        print(line)
    print(STAGE_A_FENCES[0])
    # ★★`00-principles.md` §12 —— **この関門が見ていない範囲を、走行のたびに件数で出す。**
    emb = next((x for x in results
                if x.rule_id == STAGE_A_EMBED_RULES.get(kind)), None)
    si = emb.state_info if emb is not None else {}
    if "scanned" in si:
        print("  ・★同梱の検査が読んだ範囲: 納品物 %d行のうち 囲み %d行"
              "(★外側 %d行は、この規則は見ていない)"
              % (si["scanned"], si.get("inner", 0), si["scanned"] - si.get("inner", 0)))
    else:
        print("  ・★同梱の検査が読んだ範囲: 測れていない(規則が実行できていない)")
    print("  ・★同梱の囲み: %s個" % si.get("blocks", "測れていない"))
    print("  ・★**チャットに現に貼ったかは、いまも1件も見ていない**"
          "(★母数は将来の納品の回数であり、数えられない)")
    print("  ・★チェッカーを走らせていない環境で作られた納品物は、"
          "**検査に掛けられるまで、この網の外に居る**")
    print()


def check_link_reach(rule_id, rows, link_i, header_present, evidence):
    """段階A の判定を1規則ぶん組み立てる。

    ★✕ は「現に届かない」が1本でもあるときだけ。★それ以外に未検査が残れば▲。
    ★どちらも無ければ◎で、**何本を確かめたかを註に書く**。
    """
    r = Result(rule_id, *rule_meta(rule_id))
    if not header_present:
        skip_as(r, "リンク列が見つからない(列名の確認が先)",
                "missing_input", what="リンク列", supplier="納品物")
        r.state_info["stageA"] = {"state": "no_column", "total": 0, "ok": 0,
                                  "dead": 0, "unmeasured": []}
        return r
    targets = []
    rows_with_link = set()
    for lineno, row in rows:
        for kind, value in extract_links(cell(row, link_i)):
            targets.append((lineno, kind, value))
            rows_with_link.add(lineno)
    if evidence is None:
        # 🔴★★**黙って合格にしない。**★この走行はリンクを1本も叩いていない。
        for lineno, kind, value in targets:
            if kind == "url":
                LINK_WANTED.append(value)
        r.blocked("リンクの取得結果が渡されていない —— この走行はリンクを1本も叩いていない"
                  "(--links で取得結果を渡す。--fetch-links で取得できる)。"
                  "対象は %d本(url %d / ローカル %d / doi: %d)"
                  % (len(targets),
                     sum(1 for t in targets if t[1] == "url"),
                     sum(1 for t in targets if t[1] == "path"),
                     sum(1 for t in targets if t[1] == "doi")))
        r.observe("missing_input", what="リンクの取得結果", supplier="呼び出し", handed=False)
        r.state_info["stageA"] = {
            "state": "not_fetched", "total": len(targets), "ok": 0, "dead": 0,
            "unmeasured": [(ln, v, "取得結果が渡されていない") for ln, _k, v in targets]}
        return r
    if not targets:
        # ★対象が0本。★**「確かめた」とは言わない。**★数え上げの結果として0だったと書く。
        r.ok_note("リンク列に、叩ける形のリンクが0本(この台帳では確かめるものが無かった)")
        # ★母集合= 読んだ行の数、対象= 叩ける形のリンクの数。★0本でも母集合は0ではない。
        r.observe("clean", scanned=len(rows), targets=0)
        r.state_info["stageA"] = {"state": "empty", "total": 0, "ok": 0,
                                  "dead": 0, "unmeasured": []}
        return r
    n_ok = n_dead = n_un = 0
    unmeasured = []
    for lineno, kind, value in targets:
        verdict, why = link_verdict(kind, value, evidence)
        if verdict == "dead":
            n_dead += 1
            r.fail(lineno, "リンクが届かない: %s —— %s" % (value[:110], why))
        elif verdict == "unmeasured":
            n_un += 1
            unmeasured.append((lineno, value, why))
        else:
            n_ok += 1
    # ★★語に注意 —— 「未検査」の語は F-44(◎ なのに註で未検査を自称している項目の見張り)が
    #   **実行時に**拾う。★段階Aが ◎ を出すのは未検査が 0本のとき【だけ】なので、
    #   ◎ の註にこの語を置くと **F-44 の偽陽性**になる。⇒ ◎ の側は「測れなかった」と書く。
    #   ★▲・✕ の註では「未検査」を使い続ける(★そこでは自称が真である)。
    note_ok = "段階A: %d本中 到達 %d / 届かない %d / 測れなかった %d" % (
        len(targets), n_ok, n_dead, n_un)
    note = "段階A: %d本中 到達 %d / 届かない %d / ★未検査 %d" % (
        len(targets), n_ok, n_dead, n_un)
    stage = {"state": "judged", "total": len(targets), "ok": n_ok,
             "dead": n_dead, "unmeasured": unmeasured}
    if n_dead:
        r.note = note
        r.state_info["stageA"] = stage
        return r
    if n_un:
        r.blocked(note + " —— **未検査が残っている。合格ではない。**")
        r.observe("missing_input", what="叩けなかったリンクの取得結果", supplier="呼び出し", handed=True)
        r.state_info["stageA"] = stage
        return r
    r.ok_note(note_ok)
    # ★勘定の単位は【行】である(`clean()` の逐語「母集合%d行のうち対象%d行を検査」)。
    #   ★★**本数で渡すと母集合を超えて落ちる** —— 1行が2本のリンクを持つ台帳が現にある
    #   (正典の見本がそれで、この工事で現に落ちた)。★本数は註のほうに書く。
    r.observe("clean", scanned=len(rows), targets=len(rows_with_link))
    r.state_info["stageA"] = stage
    return r


# ================================================================================
# 事実の関門【段階B】—— 書誌が、DOI の登録機関の記録と合っているか
# --------------------------------------------------------------------------------
# ★出所= ユーザーの裁定(2026-08-29)の3段階の設計の【B】。起票 `KICKOFF-jijitsu-kanmon-B.md`。
#   ★段階A(リンクが届くか)は 2026-08-29 に着地している。★**この段はその次である。**
#
# ★★**この段階が見るのは「書誌が登録機関の記録と合っているか」だけである。**
#   本文の中身と合っているか(段階C)は**見ていない**。リンクが届くかは**段階A の役**である。
#   ⇒ 見ていない範囲は `print_biblio_disclosure` が**走行のたびに件数で画面へ出す**(`00` §12)。
#
# 🔴★★**決定性**(段階A と同じ): **判定は、保存した取得結果だけから決まる。**
#   外へ出るのは `--fetch-biblio` を渡した取得のときだけである。
#   ⇒ **判定の3母集団の走行は、一度もネットワークに触らない。**
#
# 🔴★★**問い合わせられない DOI を【合格】にしない**(起票 §2-1)。
#   ★取得結果が渡されない走行は▲(検査不能・責任=**呼び出し**)で、終了コードは 3 になる。
#   ★★**「登録機関に無いから対象外」にしない。**★それは検査を弱めることであり、
#     担当も司令塔も決めてよい線ではない(起票 §2-1・§3)。**無かった場合も▲である。**
#
# 🔴🔴★★**原典との差を消さない(★起票の断定と現物が食い違った点・2026-08-31 に現物で確認)**:
#   ★**原典(`run-bunken-daicho/SKILL.md` 工程5)が人に求めているのは7項目である** ——
#     逐語=「書誌欄(著者名・年・題名・誌名・巻(号)・頁・出版社)を…1項目ずつ突き合わせる」。
#   ★**この段が機械で判定に繋ぐのは、そのうち【著者名・誌名・巻(号)】の3つだけ**である。
#   ★★**「3つ」の出所は原典ではなく【ユーザー裁定の3段階の表】である**
#     (逐語=「＋ DOI を公開の登録機関に問い合わせ、**著者名・誌名・巻号**を突合」)。
#     ★段階A の `LINK_UNSEEN` の文言も、その表を写したものである。★出所を取り違えないこと
#     (★起票 §3 は「原典が名指しした」と書いていたが、★2026-08-31 に現物で誤りと確認し、
#      ★司令塔24 が帰属の誤りとして訂正した)。
#   ⇒ ★残る4項目(年・題名・頁・出版社)は**判定に繋いでいない**。★その旨を毎回印字する。
#   ★**原典の人手の工程は1文字も減っていない。**★機械が3項目を見るようになっただけである。
BIBLIO_UNSEEN = (
    "本文の内容と、リンク先に書いてあることが合っているかは確かめていない —— 段階C",
    "リンクが現に届くかは、この段では見ていない —— 段階A の役",
)


def biblio_unseen_fields(si):
    """★7項目のうち、この走行が判定に繋いだ範囲を言う行。→ [行]

    ★項目ファイル(`--shoshi`)が渡されない走行は、これまでどおり3項目だけである(★その旨を毎回言う)。
    """
    if not si.get("items"):
        return ["原典(run-bunken-daicho/SKILL.md 工程5)が人に求める7項目のうち、機械が判定に繋ぐのは"
                "3項目(著者名・誌名・巻(号))である。年・題名・頁・出版社は判定に繋いでいない"
                "(★書誌の項目ファイル(--shoshi)を渡すと7項目を照らす)"]
    blank = si.get("blank") or {}
    out = ["書誌の項目ファイルあり: DOI を持つ行で7項目(著者名・年・題名・誌名・巻(号)・頁・出版社)を照らした"
           " —— ★DOI を持たない行は、この段では1項目も確かめていない"]
    out.append("項目ファイルに書いていないので照らしていない項目: %s"
               % ("・".join("%s %d本" % (k, blank[k]) for k in BIBLIO_FIELDS_ITEMS if blank.get(k))
                  or "0本(★書いていない項目は無かった)"))
    out.append("項目に分けていない行(sonomama): %d行 / 項目ファイルに無い行: %d行"
               % (si.get("sonomama", 0), si.get("no_item", 0)))
    return out

BIBLIO_EVIDENCE_VERSION = 1
BIBLIO_UA = "skill-review-checker/stage-B (bibliographic cross-check)"
BIBLIO_TIMEOUT_DEFAULT = 15.0

# ★DOI の取り出し。★段階A は `doi:` 形を **`https://doi.org/…` へ組み立てない**(裁定③)。
#   ★この段も**組み立てない** —— 叩く先は doi.org ではなく**登録機関の API** であり、
#     DOI は URL ではなく**識別子として**渡す。⇒ 裁定③ と矛盾しない。
#   ★括弧の扱いは `LINK_URL_RE` と同じ(★`_url_run`。前半 2026-09-28・後半 2026-10-04 の全角の括弧類)。
BIBLIO_DOI_URL_RE = re.compile(
    r"https?://(?:dx\.)?doi\.org/(10\.\d{4,9}/" + _url_run(r"\s<>\"'`|()（）\]}、。，．") + ")", re.I)


def normalize_doi(d):
    """DOI を突き合わせ用に揃える。★DOI は大小文字を区別しない規約なので小文字へ寄せる。

    ★末尾の `)` は削らない(2026-09-28)。★取り出しが `)` を通すのは対の閉じとしてだけなので、
      ★削ると `10.1016/0021-9991(84)` のような正しい DOI の末尾を落として、別の DOI を問い合わせる。
    """
    return (d or "").strip().strip("<>`,").rstrip(".").lower()


def extract_dois(cell):
    """セル1つから DOI を取り出す。→ [DOI]

    ★取り出し口は2つ: `https://doi.org/…` の URL と、`doi: 10.xxxx/…` の形。
    ★同じ DOI は1回しか返さない(★同じ DOI を1回の走行で二度叩かない・起票 §2-5)。
    """
    out, seen = [], set()
    text = cell or ""
    for m in BIBLIO_DOI_URL_RE.findall(text):
        d = normalize_doi(m)
        if d and d not in seen:
            seen.add(d)
            out.append(d)
    for m in LINK_DOI_RE.findall(text):
        d = normalize_doi(m)
        if d and d not in seen:
            seen.add(d)
            out.append(d)
    return out


# 🔴★★**この段が外へ出る口は、下の `biblio_probe` ただ1つである。**
#   ★常設テストはここを差し替える(★ネットワークの無い環境でもテストが通るため・起票 §2-3)。
#   ★★**差し替えたまま出荷していないこと**を常設テストが毎回確かめる ——
#     「差し替えたから通った」を「合格」と読ませないためである。
BIBLIO_PROBE = None


def biblio_probe_fn():
    """いま使う取得の口を返す。★差し替えられていなければ `biblio_probe`。"""
    return BIBLIO_PROBE or biblio_probe


def _biblio_json(url, timeout):
    """1本叩いて JSON を返す。→ (dict or None, 理由 or None)"""
    import json as _json
    import urllib.error
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": BIBLIO_UA,
                                               "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return _json.loads(res.read().decode("utf-8", "replace")), None
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None, "notfound"
        return None, "HTTP %d" % e.code
    except Exception as e:
        return None, e.__class__.__name__


def _rec_jalc(doc):
    """JaLC の応答から、突き合わせに使う値を取り出す。→ dict or None

    ★★**JaLC を先に当てる根拠(★現物で測って決めた・2026-08-31)**:
      和文の文献は、**Crossref には英語・ローマ字しか入っていないことが現にある**
      (実測= `10.11361/journalcpij.57.1` は Crossref の `container-title` が英語だけ・
       `original-title` は空・著者は "Yuki Hirahara")。
      ★JaLC は同じ DOI に **ja と en の両方**を持つ(誌名「都市計画論文集」・著者「平原/幸輝」)。
      ⇒ ★**Crossref だけに当てると、和文台帳はほぼ全行が「照合できない」に落ちる。**
    """
    d = (doc or {}).get("data")
    if not isinstance(d, dict):
        return None
    authors = []
    for c in d.get("creator_list") or []:
        names = [((n.get("last_name") or "").strip(), (n.get("first_name") or "").strip())
                 for n in (c.get("names") or [])]
        names = [x for x in names if x[0] or x[1]]
        if names:
            authors.append(names)
    pub = d.get("publication_date") or {}
    return {
        "agency": "JaLC",
        "authors": authors,
        "journals": [(j.get("journal_title_name") or "").strip()
                     for j in (d.get("journal_title_name_list") or [])
                     if (j.get("journal_title_name") or "").strip()],
        "volume": (d.get("volume") or "").strip(),
        "issue": (d.get("issue") or "").strip(),
        "titles": [t.get("title") for t in (d.get("title_list") or []) if t.get("title")],
        # ★副題は別の欄で持つ(★実測 2026-10-20: `10.5225/jjsm.1.19` は en にだけ subtitle が在り、ja には無い)。
        "subtitles": [t.get("subtitle") for t in (d.get("title_list") or []) if t.get("subtitle")],
        "year": (pub.get("publication_year") or "").strip(),
        "pages": "-".join(x for x in ((d.get("first_page") or "").strip(),
                                      (d.get("last_page") or "").strip()) if x),
        "publishers": [(p.get("publisher_name") or "").strip()
                       for p in (d.get("publisher_list") or []) if p.get("publisher_name")],
    }


def _rec_crossref(doc):
    """Crossref の応答から、突き合わせに使う値を取り出す。→ dict or None"""
    m = (doc or {}).get("message")
    if not isinstance(m, dict):
        return None
    issued = ((m.get("issued") or {}).get("date-parts") or [[None]])[0]
    return {
        "agency": "Crossref",
        "authors": [[((a.get("family") or "").strip(), (a.get("given") or "").strip())]
                    for a in (m.get("author") or []) if a.get("family") or a.get("given")],
        "journals": [x for x in (list(m.get("container-title") or [])
                                 + list(m.get("short-container-title") or [])) if x],
        "volume": (m.get("volume") or "").strip(),
        "issue": (m.get("issue") or "").strip(),
        "titles": [x for x in (list(m.get("title") or [])
                               + list(m.get("original-title") or [])) if x],
        "subtitles": [x for x in (m.get("subtitle") or []) if x],
        "year": str(issued[0]) if issued and issued[0] else "",
        "pages": (m.get("page") or "").strip(),
        "publishers": [x for x in [m.get("publisher")] if x],
    }


def _rec_datacite(doc):
    """DataCite の応答から、突き合わせに使う値を取り出す。→ dict or None"""
    a = ((doc or {}).get("data") or {}).get("attributes")
    if not isinstance(a, dict):
        return None
    authors = []
    for c in a.get("creators") or []:
        last = (c.get("familyName") or "").strip()
        first = (c.get("givenName") or "").strip()
        if not (last or first):
            last = (c.get("name") or "").strip()
        if last or first:
            authors.append([(last, first)])
    cont = a.get("container") or {}
    return {
        "agency": "DataCite",
        "authors": authors,
        "journals": [x for x in [cont.get("title"), a.get("publisher")]
                     if isinstance(x, str) and x],
        "volume": str(cont.get("volume") or "").strip(),
        "issue": str(cont.get("issue") or "").strip(),
        "titles": [t.get("title") for t in (a.get("titles") or [])
                   if t.get("title") and t.get("titleType") != "Subtitle"],
        "subtitles": [t.get("title") for t in (a.get("titles") or [])
                      if t.get("title") and t.get("titleType") == "Subtitle"],
        "year": str(a.get("publicationYear") or "").strip(),
        "pages": "",
        "publishers": [x for x in [a.get("publisher")] if isinstance(x, str)],
    }


# ★当てる順。★**JaLC を先頭に置いた根拠は `_rec_jalc` の註にある(現物で測った)。**
#   ★1本目で見つかったらそこで止める(★外部への負荷を最小にする・起票 §2-5)。
BIBLIO_AGENCIES = (
    ("JaLC", "https://api.japanlinkcenter.org/dois/%s", _rec_jalc),
    ("Crossref", "https://api.crossref.org/works/%s", _rec_crossref),
    ("DataCite", "https://api.datacite.org/dois/%s", _rec_datacite),
)


def biblio_probe(doi, timeout):
    """DOI を1本、登録機関へ問い合わせる。→ (state, record or 理由)

    state の意味:
      `found`    … 登録機関に記録が在った(record は dict)
      `notfound` … ★**どの登録機関にも無かった**(★合格ではない。★対象外にもしない)
      `refused`  … ★**測れていない**(拒まれた・時間切れ・相手側の失敗)

    🔴★★**`refused` を `notfound` に倒さない**(★段階A の裁定①と同じ筋)——
      「登録が無い」と「こちらが測れなかった」は別である。★**どちらも合格ではない**が、
      ✕ を立てるのは前者だけにしてある。
    """
    import urllib.parse
    quoted = urllib.parse.quote(doi, safe="/")
    why = []
    for name, tmpl, take in BIBLIO_AGENCIES:
        doc, err = _biblio_json(tmpl % quoted, timeout)
        if doc is not None:
            rec = take(doc)
            if rec:
                return "found", rec
            why.append("%s: 形が読めない" % name)
            continue
        if err == "notfound":
            why.append("%s: 無い" % name)
            continue
        why.append("%s: %s" % (name, err))
    if all(w.endswith(": 無い") for w in why):
        return "notfound", " / ".join(why)
    return "refused", " / ".join(why)


def biblio_evidence_load(path):
    """取得結果を読む。→ (対応表 or None, 読めなかった理由 or None)

    ★**判定はここから読んだものだけで決まる。**★走行中に外へ出ることはない。
    """
    import json
    try:
        with open(path, encoding="utf-8") as f:
            doc = json.load(f)
    except OSError as e:
        return None, "取得結果を開けなかった(%s): %s" % (e.__class__.__name__, path)
    except ValueError as e:
        return None, "取得結果が JSON として読めなかった(%s): %s" % (e.__class__.__name__, path)
    if not isinstance(doc, dict) or "results" not in doc:
        return None, "取得結果の形が違う(results が無い): %s" % path
    ver = doc.get("version")
    if ver != BIBLIO_EVIDENCE_VERSION:
        # ★★黙って読まない。★版が違えば、何を測ったものか分からない。
        return None, "取得結果の版が違う(この道具は %d を読む / 渡されたのは %r): %s" % (
            BIBLIO_EVIDENCE_VERSION, ver, path)
    if doc.get("stage") != "B":
        # ★★段階A の取得結果を黙って読まない。★**別の段の記録である。**
        return None, "取得結果が段階B のものでない(stage=%r): %s" % (doc.get("stage"), path)
    got = doc["results"]
    if not isinstance(got, dict):
        return None, "取得結果の results が対応表でない: %s" % path
    return got, None


def biblio_evidence_save(path, results, stamp):
    """取得結果を書く。★あとから監査できる形にする(起票 §2-5)。"""
    import json
    doc = {
        "version": BIBLIO_EVIDENCE_VERSION,
        "stage": "B",
        "tool": "check_deliverable.py",
        "fetched_at": stamp,
        "note": "段階B(書誌が登録機関の記録と合っているか)だけの記録である。"
                "リンクの到達(段階A)・本文の照合(段階C)は含まない。",
        "results": results,
    }
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")


# ★取得したい対象を、判定と**同じ述語**で集めるための置き場(★段階A の `LINK_WANTED` と同じ筋)。
BIBLIO_WANTED = []

# ★いま走っている検査が使う取得結果。★`main()` が `--biblio` から読み込んで置く。
#   ★★**None は「問い合わせていない」を意味する。**★既定は None であり、**黙って合格にはならない**。
BIBLIO_EVIDENCE = None


# ================================================================================
# 段階B の突き合わせの述語
# --------------------------------------------------------------------------------
# 🔴★★**この述語は【現物で測ってから】決めた**(起票 §2-4「完全一致で始めて、外れた件数と
#   中身を出す。規則は測ってから決める」)。★測ったのは 2026-08-31、母数は
#   **文献台帳807本に現れる実在らしい DOI 401本のうち、登録機関に記録が在った 378本**である。
#
# ★**外れの推移(★同じ母数・同じ取得結果で測り直したもの)**:
#     | 版 | 著者名 ✕ | 誌名 ✕ | 巻(号) ✕ |
#     |---|---:|---:|---:|
#     | 完全一致だけ            |  5 | 11 | 91 |
#     | いまの述語              |  1 |  0 |  1 |
#   ★**残った2件は、1件ずつ現物を見た結果【偽陽性ではない】**:
#     ① 実在の DOI に別人の書誌が付いている(台帳「山田太郎」/ 登録機関「氷見理」)
#     ② 早期公開のまま巻号が更新されていない(台帳「早期公開, 論文ID 14068」/ 登録機関「60(1)」)
#   ⇒ ★**この母数での偽陽性は 0件である。**★★**ただし「0件だった」であって「0件になる」ではない。**
#
# ★**ゆるめた点は3つだけで、どれも理由を現物で持っている**(★下の各所に註がある):
#   (a) 空白と**全角・半角の畳み込み**(NFKC) …… 幅違いで6件が✕になった
#   (b) 登録機関が1つの文字列に複数の名前を詰めた形を**分けて**当てる …… 「A = B」「A : B : C」
#   (c) 巻(号)の並びが合わないときの**数字だけの一致**(=ゆるい一致) …… 件数を毎回印字する
BIBLIO_WS_RE = re.compile(r"[\s　]+")
BIBLIO_KANJI_RE = re.compile("[㐀-鿿豈-﫿]")
BIBLIO_LATIN_RE = re.compile(r"[A-Za-z]{2,}")
BIBLIO_DIGIT_RE = re.compile(r"\d+")


def _bib_flat(s):
    """空白を落とし、全角・半角の違いを畳む(NFKC)。

    ★★**実測で必要になった**: 登録機関は誌名を全角の英数・括弧で持つことが在り
      (「土木学会論文集Ｄ３(土木計画学)」)、台帳は半角で書く(「土木学会論文集D3(土木計画学)」)。
      ★**同じ文字の幅違いであって、別の名前ではない。**★畳まないと 6件が✕になった。
    🔴★**これ以上ゆるめない** —— ★ゆるめるほど「合っている」に倒れる(=fail-open の側)。
    """
    import html as _html, unicodedata
    return BIBLIO_WS_RE.sub("", unicodedata.normalize("NFKC", _html.unescape(s or "")))


def _bib_has_kanji(s):
    return bool(BIBLIO_KANJI_RE.search(s or ""))


def _bib_has_latin(s):
    return bool(BIBLIO_LATIN_RE.search(s or ""))


def _bib_digits(s):
    """先頭の数字を取り出し、頭の 0 を落とす(★実測: 巻が "08" で登録されている誌が在る)。"""
    m = BIBLIO_DIGIT_RE.search(s or "")
    if not m:
        return ""
    return m.group(0).lstrip("0") or "0"


def _bib_author_forms(names):
    """1人ぶんの表記の候補。→ [str]  ★`names` は [(姓, 名)] の並び(言語ごと)。

    🔴★★**姓だけ・名だけを候補に入れない**(★登録機関が姓名の両方を持っているとき)。
      ★**壊しドリルで現に素通りした**: 「平原幸輝」を「平原**幸雄**」に変えても、
        候補に「平原」が入っていたために ◎ のままだった。★**姓が合っていれば通る**のは、
        原典が「特に見るのは**固有名詞**: 姓名の漢字(**別人の姓へ化ける**)」と書いている
        当のものを見ていないことになる。
      ⇒ ★**姓名がそろっている言語が1つでも在れば、その言語の【姓名の並び】だけを候補にする。**
      ★片方しか無い記録(団体名など)のときだけ、その片方を候補にする。
    ★区切りの揺れは候補として持つ(★実測: Crossref は「Alnes, P. K.」の形で持ち、
      台帳も「Alnes, P. K.」と書く。★区切りを1つに決めると当たらない)。
    """
    import html as _html
    full, part = [], []
    for last, first in names:
        # 🔴★**文字参照が生のまま入っている記録が現にある**(★実測: JaLC が `須&#xFA11;` を
        #   そのまま持っていた)。★**登録機関の側のデータの形であって、台帳の誤りではない。**
        last = _html.unescape(last or "")
        first = _html.unescape(first or "")
        if last and first:
            for sep in ("", " ", ", ", "・"):
                full.append(last + sep + first)
                full.append(first + sep + last)
            # ★★**欧文は名をイニシャルで書くのが台帳の実際である**(★実測: 台帳「Alnes, P. K.」/
            #   登録機関「Alnes Per Kristian」)。★**同じ人であって、書き方が違うだけである。**
            #   ★漢字の名には当てない(★「安田亘宏」を「安田 亘」で通してしまうため ——
            #     ★それは原典が名指しした「姓名の漢字の化け」を見逃す形になる)。
            if _bib_has_latin(first) and not _bib_has_kanji(first):
                ini = " ".join("%s." % w[0] for w in first.replace(".", " ").split() if w)
                if ini:
                    for sep in (", ", " "):
                        full.append(last + sep + ini)
                    full.append(ini + " " + last)
        elif last:
            part.append(last)
        elif first:
            part.append(first)
    return [x for x in dict.fromkeys(full or part) if x]


def _bib_journal_forms(j):
    """誌名1つぶんの候補。★登録機関が1つの文字列に複数の名前を詰めた形を分ける。

    ★**実測**: 「地域イノベーション : JRPS : journal for regional policy studies」/
      「ジオグラフィカ千里 = Geographica Senri」/「城西国際大学紀要 第34巻 第5号 観光学部」。
    ★**元の文字列も候補に残す**(=分けたことで当たらなくなる形を作らない)。
    """
    out = [j]
    for sep in (" = ", " : ", " / ", "／", " - "):
        if sep in j:
            out += [x.strip() for x in j.split(sep) if x.strip()]
    head = re.split(r"\s*第?\d+\s*巻", j)
    if len(head) > 1 and head[0].strip():
        out.append(head[0].strip())
    return [x for x in dict.fromkeys(out) if x]


def _bib_num_present(flat, num):
    """数字が、前後を数字に挟まれない形で在るか。★「1」が「2013」に当たるのを防ぐ。"""
    if not num:
        return False
    for m in re.finditer(re.escape(num), flat):
        a = flat[m.start() - 1] if m.start() else ""
        b = flat[m.end()] if m.end() < len(flat) else ""
        if not a.isdigit() and not b.isdigit():
            return True
    return False


def _bib_num_adjacent(flat, vnum, inum):
    """巻の数字のすぐ後ろに号の数字が在るか(★あいだに区切り3文字まで)。

    🔴★★**「号がどこかに在る」では通してはならない**(★壊しドリルで現に素通りした)。
      ★実測: 「57(1), 1-6」の号を **2** にずらしても、頁の「1-6」の "1" に当たって
        ◎ のままだった。★**これは巻号を1つずらす壊し方をそのまま通す**、つまり
        起票 §4 が名指しした壊し方に鳴らないということである。
      ⇒ ★**並びで見る。**★「57(1)」「57巻1号」「57-1」「57, 1」は拾い、
        ★「57(2), 1-6」は拾わない。
    """
    if not vnum or not inum:
        return False
    pat = r"(?<!\d)%s\D{0,3}%s(?!\d)" % (re.escape(vnum), re.escape(inum))
    return bool(re.search(pat, flat))


def _bib_judge(cands, cell, flat, what):
    """候補のどれかが書誌欄に在るか。→ (判定, 説明)

    🔴★★**表記系(スクリプト)が違うだけの不一致を✕にしない。**
      ★**実測(2026-08-31)**: 登録機関の記録が**ローマ字・カタカナ・英語だけ**で、
        台帳が漢字で書いている行が現に在る(法政大学・立教大学の紀要・土木学会論文集など)。
        ★**これは台帳の誤りではない。★登録機関がその表記を持っていない**のである。
      ⇒ ★**書誌欄が漢字で書いているのに、登録機関の候補に漢字が1つも無いときは
        【▲(測れなかった)】**にする。★★**◎(合格)にはしない。**
        ★▲は終了コード 3 に繋がるので、**これは fail-open ではない**。
      ★逆向きも同じ(★書誌欄が欧文だけなのに、候補が欧文を1つも持たないとき)。
    """
    hit = [c for c in cands if _bib_flat(c) and _bib_flat(c) in flat]
    if hit:
        return "ok", "%sが一致: %s" % (what, hit[0][:60])
    if _bib_has_kanji(cell) and not any(_bib_has_kanji(c) for c in cands):
        return "unmeasured", ("登録機関の%sは漢字の表記を持たず(%s)、書誌欄は漢字で書かれている"
                             % (what, " / ".join(cands[:2])[:70]))
    if (not _bib_has_kanji(cell)) and _bib_has_latin(cell) \
            and not any(_bib_has_latin(c) for c in cands):
        return "unmeasured", ("登録機関の%sは欧文の表記を持たず(%s)、書誌欄は欧文で書かれている"
                              % (what, " / ".join(cands[:2])[:70]))
    return "ng", "登録機関の%sが書誌欄に無い: %s" % (what, " / ".join(cands[:3])[:90])


# ★判定に繋ぐ項目。★**ここが唯一の対応表である**(名前を他所に書き並べない)。
BIBLIO_FIELDS = ("著者名", "誌名", "巻(号)")
# ★取得はするが**判定に繋いでいない**項目。★走行のたびに件数と名前を印字する(`00` §12)。
BIBLIO_FIELDS_UNJUDGED = ("年", "題名", "頁", "出版社")
# ★★書誌の項目ファイル(`--shoshi`)が渡された走行だけ、残る4項目も判定に繋ぐ(2026-10-20・ユーザー決定 D55)。
#   ★書誌欄は1つの文なので、年・題名・頁・出版社の境目を機械が決められない。★項目ファイルは
#     原典(run-bunken-daicho の shoshi.py)が7項目を分けて持つ物で、書誌欄はそこから書かれる。
#   ★著者名・誌名・巻(号)は、これまでどおり書誌欄で照らす(★測って決めた述語をそのまま使う)。
BIBLIO_FIELDS_ITEMS = ("年", "題名", "頁", "出版社")


def biblio_compare(rec, cell):
    """1本ぶんの突き合わせ。→ {項目名: (判定, 説明, ゆるい一致か)}

    判定: `ok` / `ng`(✕) / `unmeasured`(▲)
    """
    flat = _bib_flat(cell)
    out = {}

    # ---- 著者名 ----
    if not rec.get("authors"):
        out["著者名"] = ("unmeasured", "登録機関の記録に著者が無い", False)
    else:
        miss, unm = [], []
        # ★★**表記系を決めるのに使うのは、書誌欄の【先頭】である。**
        #   ★根拠= 原典の書誌欄の並びが「著者・年・題・誌名・巻(号)・頁」であり、
        #     **著者は先頭に書く**と決まっている(`run-bunken-daicho/references/daicho-format.md`)。
        #   🔴★**実測で必要になった**: 欧文で書いた書誌欄(「Akakabe, H. & Takezawa, N. (2021)…」)に、
        #     題名や註で漢字が混ざる行が在る。★セル全体で表記系を決めると
        #     「漢字が在る」と読み、漢字しか持たない登録機関の記録と突き合わせて✕になった。
        #     ★**著者の書き方は先頭で決まる。**★そこで見る。
        head = (cell or "")[:40]
        for names in rec["authors"]:
            forms = _bib_author_forms(names)
            st, _why = _bib_judge(forms, head, flat, "著者")
            if st == "ng":
                miss.append("/".join(forms[:3]))
            elif st == "unmeasured":
                unm.append("/".join(forms[:2]))
        if miss:
            out["著者名"] = ("ng", "登録機関の著者が書誌欄に無い: %s" % "・".join(miss[:4]), False)
        elif unm:
            out["著者名"] = ("unmeasured",
                             "登録機関の著者が書誌欄と表記系が違う(漢字を持っていない): %s"
                             % "・".join(unm[:3]), False)
        else:
            out["著者名"] = ("ok", "著者 %d名すべてが書誌欄に在る" % len(rec["authors"]), False)

    # ---- 誌名 ----
    journals = rec.get("journals") or []
    if not journals:
        out["誌名"] = ("unmeasured", "登録機関の記録に誌名が無い", False)
    else:
        full = [j for j in journals if _bib_flat(j) and _bib_flat(j) in flat]
        if full:
            out["誌名"] = ("ok", "誌名が一致: %s" % full[0][:60], False)
        else:
            parts = [p for j in journals for p in _bib_journal_forms(j)]
            hit = [p for p in parts if _bib_flat(p) and _bib_flat(p) in flat]
            if hit:
                out["誌名"] = ("ok", "誌名が一致(合成された名前を分けて当てた): %s" % hit[0][:60],
                               True)
            else:
                st, why = _bib_judge(journals, cell, flat, "誌名")
                out["誌名"] = (st, why, False)

    # ---- 巻(号) ----
    vraw = (rec.get("volume") or "").strip()
    iraw = (rec.get("issue") or "").strip()
    vnum, inum = _bib_digits(vraw), _bib_digits(iraw)
    # ★号が "0"・空・数字を含まない語のときは【号なし】として扱う。
    #   ★**実測**: 号の無い誌を JaLC は `issue="0"` で持つ(91件のうち大半がこれだった)。
    #   ★**実測**: 特集号は `issue="Special_Issue"` で持つ(数字を含まない)。
    has_issue = bool(inum) and inum != "0"
    if not vraw:
        out["巻(号)"] = ("unmeasured", "登録機関の記録に巻が無い", False)
    elif not vnum:
        out["巻(号)"] = ("unmeasured", "登録機関の巻に数字が無い: %s" % vraw, False)
    else:
        strict = []
        if has_issue:
            for v in dict.fromkeys([vraw, vnum]):
                for i in dict.fromkeys([iraw, inum]):
                    strict += ["%s(%s)" % (v, i), "%s（%s）" % (v, i), "%s巻%s号" % (v, i),
                               "第%s巻第%s号" % (v, i), "%s-%s" % (v, i), "%s_%s" % (v, i),
                               "%s.%s" % (v, i)]
        else:
            for v in dict.fromkeys([vraw, vnum]):
                strict += ["%s巻" % v, "第%s巻" % v, "vol.%s" % v, "Vol.%s" % v]
        hit = [c for c in strict if _bib_flat(c) and _bib_flat(c) in flat]
        if hit:
            out["巻(号)"] = ("ok", "巻(号)が一致: %s" % hit[0], False)
        else:
            okv = _bib_num_present(flat, vnum)
            # ★号が在る記録では、★**巻の隣に号が在ること**まで見る(→ `_bib_num_adjacent` の註)。
            oki = (not has_issue) or _bib_num_adjacent(flat, vnum, inum)
            if okv and oki:
                out["巻(号)"] = ("ok",
                                 "巻%s%s の数字が書誌欄に在る(★ゆるい一致= 並びは見ていない)"
                                 % (vnum, "・号%s" % inum if has_issue else ""), True)
            else:
                lack = ("巻%s" % vnum if not okv else "") + ("・号%s" % inum if not oki else "")
                out["巻(号)"] = ("ng",
                                 "登録機関の巻(号) %s%s が書誌欄に無い(足りない: %s)"
                                 % (vraw, "(%s)" % iraw if iraw else "", lack), False)
    return out


# ================================================================================
# 書誌の項目ファイル(`--shoshi`)で照らす4項目(年・題名・頁・出版社)
# --------------------------------------------------------------------------------
# ★出所= ユーザー決定(2026-10-20・claude-harness D55)「台帳の表はそのまま、別の項目ファイルに7項目を持ち、
#   チェッカーがそのファイルを読み7項目を照らす」。
# ★述語は【現物で測ってから】決めた(★2026-10-20。走行の取得結果 1045本 × 台帳の書誌欄の下見):
#     年 1043 一致 / 2 不一致(★登録機関と台帳が1年ずれる)
#     頁 1017 一致 / 20 は登録機関が「927-930,a1」「196_1」の形 / 4 は台帳がセッションID(頁を書いていない)
#     題名 638 完全一致 / 353 は副題の有無だけ / 40 はダッシュ・記号の書き方の違い(「―」「-」「&lt;」)
#   ⇒ ★題名は本題と副題を分けて持ち、★控えめにそろえて(★D52: 全体の NFKC はしない)完全一致で見る。
#   ⇒ ★年が1年ずれるものは ✕ にしない(▲)。★早期公開と冊子の年がずれる現物が在り、どちらの誤りとも言えない。
# 🔴★**項目ファイルに書いていない項目は照らさない**(★論文の出版社は台帳に書かないのがふつうである)。
#   ★その数は毎回印字する(=黙って落とさない)。★書いていないことは合格ではない。
SHOSHI_KIND = "bunken-shoshi"
SHOSHI_VERSION = 1
# ★いま走っている検査が使う項目ファイル。★`main()` が `--shoshi` から読み込んで置く。★None は「渡されていない」。
SHOSHI = None
_SHOSHI_DASH_RE = re.compile("[\u2010-\u2015\u2212\u2500\u2501\uFE58\uFE63]")
_SHOSHI_WAVE_RE = re.compile("[\u301C\u3030]")
_SHOSHI_OUTER = {"「": "」", "『": "』", "“": "”", '"': '"', "(": ")", "（": "）", "【": "】"}


def shoshi_load(path):
    """項目ファイルを読む。→ ({#の番号: 行} or None, 読めなかった理由 or None)"""
    import json
    try:
        with open(path, encoding="utf-8") as f:
            doc = json.load(f)
    except (OSError, ValueError, UnicodeDecodeError) as e:
        return None, "項目ファイルが読めない(%s): %s" % (e.__class__.__name__, path)
    if not (isinstance(doc, dict) and doc.get("kind") == SHOSHI_KIND
            and doc.get("v") == SHOSHI_VERSION and isinstance(doc.get("rows"), list)):
        return None, "項目ファイルの形でない(kind=%s・v=%d・rows が要る): %s" % (SHOSHI_KIND, SHOSHI_VERSION, path)
    out = {}
    for r in doc["rows"]:
        if not (isinstance(r, dict) and isinstance(r.get("n"), int)):
            return None, "項目ファイルに # の番号(n)を持たない行が在る: %s" % path
        if r["n"] in out:
            return None, "項目ファイルに #%d が2行在る: %s" % (r["n"], path)
        out[r["n"]] = r
    return out, None


def _shoshi_soroe(s):
    """控えめにそろえる(★D52): 文字参照とタグを除く・全角の英数記号だけ半角に・空白を消す・ダッシュと波を1つに・
    『』を「」に・異体字の選択子と末尾の * を落とす・英字を小文字に・外側の括弧を外す。

    ★かな・漢字(新字・旧字)は畳まない(★旧字体の著者名を人に見せるため)。★`run-bunken-daicho/scripts/kyotsu.py` の `soroe` と同じ規則。
    ★タグ・選択子・末尾の * は登録機関の側の書き方である(★実測 2026-10-20: `<b>…</b>`・`<br>`・「味噌」の後ろの
      異体字の選択子・題名の末尾の「＊」)。★『』は、台帳が外側を「」で囲むので内側を『』に替えた形である。
    """
    import html as _html
    s = _html.unescape(_html.unescape(s or ""))
    s = re.sub(r"<[^>]+>", "", s)
    s = re.sub("[︀-️\U000e0100-\U000e01ef]", "", s)
    s = "".join(chr(ord(c) - 0xFEE0) if 0xFF01 <= ord(c) <= 0xFF5E else c for c in s)
    s = BIBLIO_WS_RE.sub("", s).replace("『", "「").replace("』", "」")
    s = _SHOSHI_WAVE_RE.sub("~", _SHOSHI_DASH_RE.sub("-", s)).lower().rstrip("*")
    while len(s) >= 2 and _SHOSHI_OUTER.get(s[0]) == s[-1]:
        s = s[1:-1]
    return s


def _shoshi_kugiri_nashi(s):
    """本題と副題の区切り(: - ~ ・ と、副題を挟む長音の「ー」)まで消した形。★分け方だけが違う時に当てる(=ゆるい一致)。

    ★実測: 登録機関が副題を「 ー言説を用いた郵送調査からー」のように長音の字で挟む現物が在る。
      ★長音の字そのものは畳まない(★語の中の「ー」は語の一部である)。★空白の後ろと末尾のものだけを区切りと見る。
    """
    s = re.sub(r"(^|[\s　])ー", r"\1", s or "")
    s = re.sub(r"ー[\s　]*$", "", s)
    return re.sub(r"[:\-~・]", "", _shoshi_soroe(s))


def _shoshi_wa(s):
    """和字(かな・漢字)を含むか"""
    return bool(_bib_has_kanji(s) or re.search("[぀-ヿ]", s or ""))


def _shoshi_pages(s):
    """頁を (はじめ, おわり) にする。★登録機関の「927-930,a1」の後ろは落とす。★頭の 0 を落とす。"""
    s = _shoshi_soroe(s).replace("pp.", "").replace("p.", "")
    s = s.split(",")[0]
    parts = [x for x in re.split(r"[-~]", s) if x]
    norm = [x.lstrip("0") or "0" for x in parts]
    return (norm[0] if norm else "", norm[-1] if len(norm) > 1 else "")


def shoshi_cell_mismatch(item, cell):
    """書誌欄が項目ファイルの値を持っているか。→ 書誌欄に無い項目の説明の並び

    ★書誌欄は項目ファイルから書かれる(shoshi.py kaku)。★持っていなければ、どちらかを手で直したということである。
    ★書き方(区切り・括弧)は見ない —— 値が書誌欄に在るかだけを見る(★書き方を2か所に持たないため)。
    """
    flat = _bib_flat(cell)
    if item.get("shurui") == "sonomama":
        return [] if _bib_flat(item.get("shoshi")) == flat else ["書誌欄が項目ファイルの shoshi と違う"]
    miss = []
    names = item.get("chosha") if isinstance(item.get("chosha"), list) else []
    for name in names:
        if _bib_flat(name) not in flat:
            miss.append("著者名= %s" % str(name)[:30])
    for key, label in (("nen", "年"), ("dai", "題名"), ("fukudai", "副題"), ("shi", "誌名"),
                       ("maki", "巻"), ("gou", "号"), ("peji", "頁"), ("shuppan", "出版社")):
        v = item.get(key)
        if isinstance(v, str) and v.strip() and _bib_flat(v) not in flat:
            miss.append("%s= %s" % (label, v.strip()[:40]))
    return miss


def biblio_compare_items(rec, item):
    """項目ファイルの1行と登録機関の記録で、年・題名・頁・出版社を照らす。→ {項目名: (判定, 説明, ゆるい一致か)}

    判定: `ok` / `ng`(✕) / `unmeasured`(▲) / `blank`(項目ファイルに書いていない。★合格でも違反でもない。数を印字する)
    """
    out = {}
    if item.get("shurui") == "sonomama":
        return out
    # ---- 年 ----
    y = str(item.get("nen") or "").strip()
    ry = str(rec.get("year") or "").strip()
    if not y:
        out["年"] = ("blank", "項目ファイルに年が無い", False)
    elif not ry:
        out["年"] = ("unmeasured", "登録機関の記録に年が無い", False)
    elif y == ry:
        out["年"] = ("ok", "年が一致: %s" % y, False)
    elif y.isdigit() and ry.isdigit() and abs(int(y) - int(ry)) == 1:
        # ★実測: 早期公開と冊子の年がずれる現物が在る(★どちらの誤りとも言えない)。★✕ にせず ▲ にして人に見せる。
        out["年"] = ("unmeasured", "登録機関の年(%s)と1年ずれる(早期公開と冊子の年の違いがありうる)" % ry, False)
    else:
        out["年"] = ("ng", "登録機関の年は %s(項目ファイル %s)" % (ry, y), False)
    # ---- 題名 ----
    dai = str(item.get("dai") or "").strip()
    fuku = str(item.get("fukudai") or "").strip()
    titles = [x for x in (rec.get("titles") or []) if isinstance(x, str) and x.strip()]
    subs = [x for x in (rec.get("subtitles") or []) if isinstance(x, str) and x.strip()]
    if not dai:
        out["題名"] = ("blank", "項目ファイルに題名が無い", False)
    elif not titles:
        out["題名"] = ("unmeasured", "登録機関の記録に題名が無い", False)
    else:
        k_dai, k_fuku = _shoshi_soroe(dai), _shoshi_soroe(fuku)
        loose_all = _shoshi_kugiri_nashi(dai + fuku)
        hit_main = [t for t in titles if _shoshi_soroe(t) == k_dai]
        # ★副題は同じ表記系のものだけと比べる(★実測: JaLC は en にだけ副題を持ち、ja に持たない現物が在る)
        subs_same = [s for s in subs if _shoshi_wa(s) == _shoshi_wa(fuku)] if fuku else []
        hit_sub = [s for s in subs_same if _shoshi_soroe(s) == k_fuku]
        joined = [t for t in titles if _shoshi_kugiri_nashi(t) == loose_all] \
            + [t + s for t in titles for s in subs if _shoshi_kugiri_nashi(t + s) == loose_all]
        # ★登録機関が題名の後ろに特集名などを括弧で足した形(★実測: 「…を事例に(<特集>構造再編下の日本農業)」が7本)。
        noted = [t for t in titles if re.fullmatch(re.escape(loose_all) + r"\(.+\)", _shoshi_kugiri_nashi(t))]
        # ★登録機関が同じ表記系の副題を別の欄で持つのに、項目ファイルに副題が無い= 副題の欠落(★実例: 書誌の突合で直した「副題の欠落」)
        subs_dai = [s for s in subs if _shoshi_wa(s) == _shoshi_wa(dai)]
        if hit_main and not fuku and subs_dai:
            out["題名"] = ("ng", "登録機関は副題「%s」を持つが、項目ファイルに副題が無い" % subs_dai[0][:50], False)
        elif hit_main and (not fuku or hit_sub):
            out["題名"] = ("ok", "題名が一致: %s" % hit_main[0][:60], False)
        elif hit_main and fuku and not subs_same:
            out["題名"] = ("ok", "本題が一致(★副題は登録機関の記録に無いので照らしていない): %s" % hit_main[0][:60],
                           True)
        elif joined:
            out["題名"] = ("ok", "題名が一致(本題と副題の分け方だけが違う): %s" % joined[0][:60], True)
        elif noted:
            out["題名"] = ("ok", "題名が一致(★登録機関は後ろに括弧の注記を足している): %s" % noted[0][:60], True)
        elif _shoshi_wa(dai):
            if not any(_shoshi_wa(t) for t in titles):
                out["題名"] = ("unmeasured", "登録機関の題名は和字の表記を持たない(%s)" % " / ".join(titles[:2])[:70],
                               False)
            else:
                out["題名"] = ("ng", "登録機関の題名と違う: %s" % " / ".join(titles[:2])[:90], False)
        elif _bib_has_latin(dai) and not any(_bib_has_latin(t) for t in titles):
            out["題名"] = ("unmeasured", "登録機関の題名は欧文の表記を持たない(%s)" % " / ".join(titles[:2])[:70],
                           False)
        else:
            out["題名"] = ("ng", "登録機関の題名と違う: %s" % " / ".join(titles[:2])[:90], False)
    # ---- 頁 ----
    pg = str(item.get("peji") or "").strip()
    rp = str(rec.get("pages") or "").strip()
    if not pg:
        out["頁"] = ("blank", "項目ファイルに頁が無い", False)
    elif not rp:
        out["頁"] = ("unmeasured", "登録機関の記録に頁が無い", False)
    else:
        a, b = _shoshi_pages(pg)
        ra, rb = _shoshi_pages(rp)
        if a == ra and (b == rb or not rb or not b):
            loose = (b != rb) or (_shoshi_soroe(rp).split(",")[0] != _shoshi_soroe(rp))
            out["頁"] = ("ok", "頁が一致: %s%s" % (pg, "(★登録機関は %s)" % rp if loose else ""), loose)
        else:
            out["頁"] = ("ng", "登録機関の頁は %s(項目ファイル %s)" % (rp, pg), False)
    # ---- 出版社 ----
    pub = str(item.get("shuppan") or "").strip()
    pubs = [x for x in (rec.get("publishers") or []) if isinstance(x, str) and x.strip()]
    if not pub:
        out["出版社"] = ("blank", "項目ファイルに出版社が無い", False)
    elif not pubs:
        out["出版社"] = ("unmeasured", "登録機関の記録に出版社が無い", False)
    else:
        f = _bib_flat(pub)
        exact = [x for x in pubs if _bib_flat(x) == f]
        part = [x for x in pubs if f and (f in _bib_flat(x) or _bib_flat(x) in f)]
        if exact:
            out["出版社"] = ("ok", "出版社が一致: %s" % exact[0][:60], False)
        elif part:
            # ★実測: 登録機関は「公益社団法人 日本都市計画学会」、台帳は「日本都市計画学会」と書く。
            out["出版社"] = ("ok", "出版社が一致(★法人の種類などの付け足しを除いて): %s" % part[0][:60], True)
        elif _bib_has_kanji(pub) and not any(_bib_has_kanji(x) for x in pubs):
            out["出版社"] = ("unmeasured", "登録機関の出版社は漢字の表記を持たない(%s)" % " / ".join(pubs[:2])[:70],
                            False)
        else:
            out["出版社"] = ("ng", "登録機関の出版社は %s" % " / ".join(pubs[:2])[:90], False)
    return out


# ★段階Bの規則。★種別ごとに1本ずつ。★**ここが唯一の対応表である**(名前で引かない)。
#   🔴★**uradori は入れていない。**★理由= uradori の台帳には**書誌欄が無い**
#     (`run-uradori/references/daicho-format.md` の列は #・主張・分類・判定・ソース名・リンク・位置・
#      要旨/逐語・到達範囲・アクセス日・備考)。★**突き合わせる相手が原典に無い。**
#     ★**原典が黙っていることは実装しない**(`00-principles.md` の判断規則)。
#     ⇒ ★その旨は `print_biblio_disclosure` が uradori の走行でも印字する(=黙って落とさない)。
BIBLIO_RULES = {"bunken": "B-13"}


def check_biblio_match(rule_id, rows, biblio_i, link_i, header_present, evidence,
                       num_i=None, shoshi=None):
    """段階B の判定を1規則ぶん組み立てる。

    ★✕ は「登録機関の記録と現に食い違う」が1本でもあるときだけ。
    ★それ以外に未検査(問い合わせていない・登録機関に無い・表記系が違う)が残れば▲。
    ★どちらも無ければ◎で、**何本を確かめたかを註に書く**。
    ★`shoshi`(項目ファイル)が渡されたら、★年・題名・頁・出版社も照らし、★書誌欄が項目ファイルの値を
      持っているかも見る(★持っていなければ ✕。★その行が項目ファイルに無ければ ▲)。
    """
    r = Result(rule_id, *rule_meta(rule_id))
    items_info = {"items": shoshi is not None, "blank": {}, "sonomama": 0, "no_item": 0}
    if not header_present:
        skip_as(r, "書誌列またはリンク列が見つからない(列名の確認が先)",
                "missing_input", what="書誌列・リンク列", supplier="納品物")
        r.state_info["stageB"] = dict({"state": "no_column", "total": 0, "ok": 0, "ng": 0,
                                       "unmeasured": [], "rows_no_doi": 0, "notfound": 0,
                                       "loose": 0}, **items_info)
        return r
    # ★対象を集める。★DOI は**リンク欄と書誌欄の両方**から拾う
    #   (★実測: 書誌欄の末尾に `DOI:10.15002/00008193` と書いている行が現に在る)。
    targets, rows_no_doi = [], 0
    item_of, item_bad, item_un = {}, [], []
    for lineno, row in rows:
        cell_link = cell(row, link_i)
        cell_bib = cell(row, biblio_i)
        if shoshi is not None:
            # ★項目ファイルの行を # の番号で引く。★書誌欄がその値を持っているかを、DOI の有無に関わらず見る。
            num = cell(row, num_i).strip() if num_i is not None else ""
            item = shoshi.get(int(num)) if num.isdigit() else None
            if item is None:
                items_info["no_item"] += 1
                item_un.append((lineno, "#%s" % (num or "?"), "項目ファイルにこの行が無い(書誌の7項目を照らせない)"))
            else:
                item_of[lineno] = item
                if item.get("shurui") == "sonomama":
                    items_info["sonomama"] += 1
                miss = shoshi_cell_mismatch(item, cell_bib)
                if miss:
                    item_bad.append((lineno, "書誌欄が項目ファイルと食い違う(#%s): %s が書誌欄に無い"
                                     % (num, "・".join(miss[:4]))))
        dois = []
        for d in extract_dois(cell_link) + extract_dois(cell_bib):
            if d not in dois:
                dois.append(d)
        if not dois:
            rows_no_doi += 1
            continue
        for d in dois:
            targets.append((lineno, d, cell_bib))
    base = dict({"state": "judged", "total": len(targets), "ok": 0, "ng": 0, "unmeasured": [],
                 "rows_no_doi": rows_no_doi, "notfound": 0, "loose": 0}, **items_info)
    if evidence is None:
        # 🔴★★**黙って合格にしない。**★この走行は登録機関へ1本も問い合わせていない。
        for _ln, d, _c in targets:
            if d not in BIBLIO_WANTED:
                BIBLIO_WANTED.append(d)
        r.blocked("書誌の取得結果が渡されていない —— この走行は登録機関へ1本も問い合わせていない"
                  "(--biblio で取得結果を渡す。--fetch-biblio で取得できる)。"
                  "対象は %d本の DOI(DOI を持たない行 %d行)"
                  % (len(targets), rows_no_doi))
        r.observe("missing_input", what="書誌の取得結果", supplier="呼び出し", handed=False)
        base["state"] = "not_fetched"
        base["unmeasured"] = [(ln, d, "取得結果が渡されていない") for ln, d, _c in targets]
        r.state_info["stageB"] = base
        return r
    if not targets and not item_bad and not item_un:
        # ★対象が0本。★**「確かめた」とは言わない。**★数え上げの結果として0だったと書く。
        r.ok_note("リンク欄・書誌欄に DOI が0本(この台帳では登録機関に問い合わせるものが無かった)"
                  " ※DOI を持たない行 %d行の書誌は、この段では1項目も確かめていない" % rows_no_doi)
        r.observe("clean", scanned=len(rows), targets=0)
        base["state"] = "empty"
        r.state_info["stageB"] = base
        return r
    n_ok = n_ng = 0
    unmeasured, loose, notfound = list(item_un), 0, 0
    for lineno, why in item_bad:
        n_ng += 1
        r.fail(lineno, why)
    for lineno, doi, bib in targets:
        rec = evidence.get(doi)
        if not isinstance(rec, dict) or "state" not in rec:
            unmeasured.append((lineno, doi, "取得結果にこの DOI が無い"))
            continue
        st = rec.get("state")
        if st == "notfound":
            # 🔴★★**「登録機関に無いから対象外」にしない**(起票 §2-1)。★▲である。
            notfound += 1
            unmeasured.append((lineno, doi,
                               "どの登録機関にも記録が無い(★これは合格ではない): %s"
                               % (rec.get("why") or "")[:60]))
            continue
        if st != "found" or not isinstance(rec.get("rec"), dict):
            unmeasured.append((lineno, doi,
                               "登録機関へ問い合わせられなかった: %s" % (rec.get("why") or "")[:60]))
            continue
        res = biblio_compare(rec["rec"], bib)
        if lineno in item_of:
            for k, v in biblio_compare_items(rec["rec"], item_of[lineno]).items():
                if v[0] == "blank":
                    items_info["blank"][k] = items_info["blank"].get(k, 0) + 1
                else:
                    res[k] = v
        bad = [(k, v) for k, v in res.items() if v[0] == "ng"]
        un = [(k, v) for k, v in res.items() if v[0] == "unmeasured"]
        loose += sum(1 for v in res.values() if len(v) > 2 and v[2])
        if bad:
            n_ng += 1
            r.fail(lineno, "書誌が登録機関の記録と違う(%s / %s): %s"
                   % (doi[:60], rec["rec"].get("agency", "?"),
                      " / ".join("%s= %s" % (k, v[1]) for k, v in bad)[:220]))
        elif un:
            unmeasured.append((lineno, doi,
                               " / ".join("%s= %s" % (k, v[1]) for k, v in un)[:200]))
        else:
            n_ok += 1
    base.update({"ok": n_ok, "ng": n_ng, "unmeasured": unmeasured, "notfound": notfound,
                 "loose": loose, "blank": items_info["blank"]})
    # ★★語に注意 —— 段階A と同じ。◎ の註に「未検査」の語を置くと F-44 の偽陽性になる。
    note_ok = ("段階B: DOI %d本中 一致 %d / 食い違い %d / 測れなかった %d"
               " ※DOI を持たない行 %d行" % (len(targets), n_ok, n_ng, len(unmeasured),
                                            rows_no_doi))
    note = ("段階B: DOI %d本中 一致 %d / 食い違い %d / ★未検査 %d"
            " ※DOI を持たない行 %d行" % (len(targets), n_ok, n_ng, len(unmeasured), rows_no_doi))
    if n_ng:
        r.note = note
        r.state_info["stageB"] = base
        return r
    if unmeasured:
        r.blocked(note + " —— **未検査が残っている。合格ではない。**")
        r.observe("missing_input", what="問い合わせられなかった DOI の記録", supplier="呼び出し", handed=True)
        r.state_info["stageB"] = base
        return r
    r.ok_note(note_ok)
    r.observe("clean", scanned=len(rows), targets=len(targets))
    r.state_info["stageB"] = base
    return r


def fetch_and_save_biblio(args):
    """`--fetch-biblio`: 対象を集めて問い合わせ、取得結果を保存する。→ 終了コード(0 なら検査へ)

    🔴★★**集める述語を書き起こさない。**★判定が使う `check_biblio_match` にそのまま集めさせる ——
      別に書けば、**集めた先と判定した先がずれても誰も気づけない**(★段階A と同じ筋)。
      ⇒ ここでは取得結果を渡さずに1回**空走り**させ、`BIBLIO_WANTED` に溜まったものを叩く。
    ★同じ DOI は1回しか叩かない(起票 §2-5)。★待ち時間の上限は `--biblio-timeout`。
    """
    import time
    del BIBLIO_WANTED[:]
    for path in args.files:
        if os.path.isfile(path):
            inspect_file(path, args)          # ★取得結果は None のまま= 空走り
    dois = sorted(set(BIBLIO_WANTED))
    print("★段階B: 問い合わせを始める —— 対象 %d本の DOI(重複を除いた数)/ 待ち時間の上限 %g秒"
          % (len(dois), args.biblio_timeout))
    probe = biblio_probe_fn()
    if probe is not biblio_probe:
        # ★★差し替えられた口で取得した結果を、黙って保存しない。★出所を画面に出す。
        print("  ★★注意: 問い合わせの口が差し替えられている(%s)。★この結果は本物の照会ではない。"
              % getattr(probe, "__name__", repr(probe)))
    got = {}
    for i, doi in enumerate(dois, 1):
        state, payload = probe(doi, args.biblio_timeout)
        if state == "found":
            got[doi] = {"state": "found", "rec": payload}
            shown = payload.get("agency", "?")
        else:
            got[doi] = {"state": state, "why": payload}
            shown = state
        print("  [%3d/%d] %-9s %s" % (i, len(dois), shown, doi[:90]))
    try:
        biblio_evidence_save(args.biblio, got, time.strftime("%Y-%m-%dT%H:%M:%S"))
    except OSError as e:
        print("★★段階B: 取得結果を保存できなかった(%s): %s" % (e.__class__.__name__, args.biblio),
              file=sys.stderr)
        print("★**保存できない照会は、次の走行で再現できない。**★黙って検査へ進まない。",
              file=sys.stderr)
        return 2
    n = {}
    for rec in got.values():
        n[rec["state"]] = n.get(rec["state"], 0) + 1
    print("★段階B: 問い合わせを終えた —— 記録が在った %d / どこにも無い %d / 測れていない %d  → %s"
          % (n.get("found", 0), n.get("notfound", 0), n.get("refused", 0), args.biblio))
    print()
    return 0


# ★★事実の関門【段階B-2】—— 段階B の申告を**納品物に同梱**させ、この走行の申告と突き合わせる。
#   ★出所= 起票 `KICKOFF-kanmon-B2-ami.md`(2026-09-01)。★先例= 段階A-3(`U-21`/`B-12`)。
#
# 🔴★★**この段が閉じるのは「申告が納品物に載ったか」までである。**
#   ★**チャットに貼ったかは、いまも観測できない。**★そこは掟のままである(段階A-2 と同じ)。
#
# ★★**閉じる不変量**:
#   ★**終了コード 0 ⇒ 段階Bを現に走らせており、かつ【この走行の申告】が納品物に同梱されている。**
#   ★`--biblio` を渡さなければ `B-13` が ▲ で exit 3。渡しても同梱が無ければここが ✕ で exit 1。
#   ⇒ ★**納品しながら段階Bの申告を省く経路が無い。**
#
# 🔴★★**段階A の囲みとは【別に】置く。**★理由は「読みやすさ」ではない ——
#   ★**段階A と段階B は別々に走りうる**(`--links` だけ / `--biblio` だけ)。
#   ★1つの囲みに畳むと、**片方しか走らせていない走行の申告が、もう一方も走らせたように読める。**
#   ★また、段階A-3 が着地させた固定点(貼っても申告文が動かない)を、こちらの都合で動かすことになる。
#
# ★印は**つなぎ合わせて作る**(`20-evidence-rules.md` §3-E 作法2。★自分の source を検体にしない)。
STAGE_B_MARK = "stage-b" + " v1"
STAGE_B_FENCE_OPEN = STAGE_A_FENCES[0] + STAGE_B_MARK
STAGE_B_HEAD_RAN = ("★事実の関門 段階B —— この納品物について、"
                    "チェッカーが出した申告をそのまま同梱している")
STAGE_B_TAIL = ("★この関門は「書誌が登録機関の記録と合うか」しか見ていない。"
                "合格は、文献の中身が確かめられたという意味ではない。")
# ★チェッカーが無い環境で貼る定型文。★**空にしないための受け皿である。**
#   🔴★**3行目に句点を置かない**(★原典で鍵括弧に入れると `R-14` が鳴る。★段階A-3 が現に踏んだ)。
STAGE_B_NORUN = (
    "★事実の関門 段階B —— ★チェッカーを走らせていない環境で作った納品物である",
    "・★書誌が登録機関の記録と合うかは、1本も確かめていない(段階Bを走らせていない)",
    "・★これは「0件だった」ではない。「確かめていない」である",
)
STAGE_B_EMBED_RULES = {"bunken": "B-15"}


def biblio_unjudged_line(si):
    """★判定に繋いでいない項目の1行(★申告と画面で同じ文を使う)。"""
    if si.get("items"):
        return "・★判定に繋いでいない項目: なし(★項目ファイルに書いていない項目と、DOI を持たない行を除く)"
    return ("・★判定に繋いでいない項目: %s の %d項目"
            % ("・".join(BIBLIO_FIELDS_UNJUDGED), len(BIBLIO_FIELDS_UNJUDGED)))


def stage_b_declaration(kind, results):
    """★段階Bの申告文の正本。→ [行](★囲みの中身。★囲みの行は含まない)

    🔴★★**ここが唯一の作成地点である。**★画面へ出す文と、納品物に同梱されているかを
      照合する文を**別々に書き起こさない** —— 別に書けば、**ずれても誰も気づけない。**
      ★先例= `stage_a_declaration` の註と同じ理由である。
    ★**数え直さない。**★数えているのは `B-13` である(`state_info["stageB"]`)。
    """
    rid = BIBLIO_RULES.get(kind)
    hit = [x for x in results if x.rule_id == rid] if rid else []
    info = (hit[0].state_info.get("stageB") if hit else None) or {}
    if not info:
        # ★段階Bの結果が取れない(規則が原典を失った等)。★**0で埋めない。**
        return [STAGE_B_HEAD_RAN,
                "・★段階Bの結果が取れなかった —— この走行では、"
                "書誌が登録機関の記録と合うかを1本も言えない"]
    un = info.get("unmeasured", []) or []
    out = [STAGE_B_HEAD_RAN,
           "・確かめたこと: 台帳の DOI %d本のうち、登録機関の記録と一致 %d本 / 食い違い %d本"
           % (info.get("total", 0), info.get("ok", 0), info.get("ng", 0)),
           "・★DOI を持たない行: %d行(この段では1項目も確かめていない)"
           % info.get("rows_no_doi", 0),
           "・★どの登録機関にも記録が無い: %d本(★合格ではない。★対象外にもしていない)"
           % info.get("notfound", 0),
           "・★「ゆるい一致」で通した項目: %d件(★数字は在るが並びまでは見ていない)"
           % info.get("loose", 0)]
    for line in BIBLIO_UNSEEN:
        out.append("・★確かめていないこと: %s" % line)
    for line in biblio_unseen_fields(info):
        out.append("・★%s" % line)
    out.append(biblio_unjudged_line(info))
    out.append("・★測れなかった %d件%s"
               % (len(un), "" if un else "(★0件。★確かめた結果として0である)"))
    for lineno, doi, why in un:
        out.append("   - %s%s —— %s"
                   % (("L%d " % lineno) if lineno else "", str(doi)[:90], str(why)[:110]))
    out.append(STAGE_B_TAIL)
    return out


def print_biblio_disclosure(kind, results):
    """★段階Bの【見ていない範囲】と、★**貼るための申告文**を画面に出す(`00` §12)。

    🔴★★**0件でも必ず出す。**★出さないと「0件だった」と「申告し忘れた」が区別できない。
    🔴★★**この段の対象でない種別でも、その旨を1行出す** ——
      ★「段階Bが在る」と読んだ人が、uradori の台帳まで見られていると誤解しないため。
    🔴★★**囲みは字下げせずに出す。**★人が選んで写すからである(★段階A-3 と同じ)。
    """
    if kind not in ("bunken", "uradori"):
        return
    print("  [★事実の関門 段階B —— 書誌が、DOI の登録機関の記録と合っているか]")
    if kind not in BIBLIO_RULES:
        print("  ・★**この種別は段階Bの対象ではない**(★uradori の台帳には書誌欄が無く、"
              "突き合わせる相手が原典に無い)")
        print("  ・★**「確かめて合っていた」ではない。「見ていない」である**")
        print()
        return
    r = next((x for x in results if x.rule_id == BIBLIO_RULES[kind]), None)
    si = (r.state_info.get("stageB") if r is not None else None) or {}
    if not si:
        print("  ・★測れていない(規則が実行できていない)")
        print()
        return
    print("  ・★問い合わせた DOI: %d本(一致 %d / 食い違い %d / 測れなかった %d)"
          % (si.get("total", 0), si.get("ok", 0), si.get("ng", 0),
             len(si.get("unmeasured", ()))))
    print("  ・★①DOI を持たない行: %d行 —— **この段では1項目も確かめていない**"
          % si.get("rows_no_doi", 0))
    print("  ・★②DOI は在るが、どの登録機関にも記録が無い: %d本 —— "
          "**★合格ではない。★対象外にもしていない**" % si.get("notfound", 0))
    print("  ・★③『ゆるい一致』で通した項目: %d件 —— "
          "**数字は在るが並びまでは見ていない**(★偽陽性を作らないための緩めである)"
          % si.get("loose", 0))
    for line in BIBLIO_UNSEEN + tuple(biblio_unseen_fields(si)):
        print("  ・★%s" % line)
    print("  " + biblio_unjudged_line(si))
    # ★★段階B-2 —— **貼るための申告文**。★段階A のものとは別の囲みである。
    print("  [★事実の関門 段階B —— 下の囲みを**納品物に同梱**し、チャット本文にも写すこと"
          "(★違反0でも貼る)]")
    print(STAGE_B_FENCE_OPEN)
    for line in stage_b_declaration(kind, results):
        print(line)
    print(STAGE_A_FENCES[0])
    # ★★`00-principles.md` §12 —— **同梱の検査が見ていない範囲を、走行のたびに件数で出す。**
    emb = next((x for x in results
                if x.rule_id == STAGE_B_EMBED_RULES.get(kind)), None)
    esi = emb.state_info if emb is not None else {}
    if "scanned" in esi:
        print("  ・★同梱の検査が読んだ範囲: 納品物 %d行のうち 囲み %d行"
              "(★外側 %d行は、この規則は見ていない)"
              % (esi["scanned"], esi.get("inner", 0), esi["scanned"] - esi.get("inner", 0)))
    else:
        print("  ・★同梱の検査が読んだ範囲: 測れていない(規則が実行できていない)")
    print("  ・★段階Bの同梱の囲み: %s個" % esi.get("blocks", "測れていない"))
    print("  ・★**チャットに現に貼ったかは、いまも1件も見ていない**"
          "(★母数は将来の納品の回数であり、数えられない)")
    print()


# ================================================================================
# 事実の関門【段階C】—— 納品物が引いた【逐語】が、原典に現に在るか
# --------------------------------------------------------------------------------
# ★出所= ユーザーの裁定(2026-08-29)の3段階の設計の【C】。起票 `KICKOFF-jijitsu-kanmon-C.md`。
#   ★逐語= 「**その内容をどこまで確認したのか(本文なのか抄録なのか)ってのが大事だろう**」。
#
# 🔴🔴★★**この段の合格は「0件」ではない。**★**「取れたものについて0件」＋【取れなかった件数】が
#   セットである。**★片方だけでは嘘になる(起票 §2-1。★原典が既に「段階C は 0件にできない」と断っている)。
#
# 🔴★★**素の完全一致は【使えない】。★これは推測ではなく2点の実測である。**
#   ① 原典 `run-uradori/references/daicho-format.md` の逐語(2026-08-04 の多角評価ラウンド2)=
#      「**『逐語をそのまま検索すれば見つかる』という前提は実測で成り立たなかった(実在の5行を追試して、
#        逐語の素の検索で当たったのは1行だけ。残りは CIDフォントの文字化け・全角半角の違い・
#        PDFのテキスト層のエンコード違いで空振りした)**」。
#   ② 2026-08-31 の実測(★手順7 の台帳の逐語 75本)= **そのまま当たったのは 28本**。
#      ★**外れた47本の大半は「台帳が嘘」ではなく【ページが中身を渡していない】であった。**
#      ★J-STAGE の記事ページ・CiNii・PubMed は、タグを落とすと**題名と誌名とナビだけ**が残る。
#   ⇒ ★★**「本文に無かった」をそのまま✕にすると、正しい台帳を大量に赤くする。**
#     ★**偽陽性を出す検査は使われなくなる**(`30-round-flow.md`)。
#
# ★★**そこで【対照を2つ】置く。★✕ を立てるのは、2つとも通ってなお逐語が無いときだけである。**
#   ★**対照A= その文献の【題名】がページに在るか**(=このページはこの文献の頁である)。
#     ★★**「当たるはずのものが当たるか」を先に見る** —— ★検体を用意するのではなく、
#       **対象そのものから作る**(`00-principles.md` §11 の条件1 を、走行のたびに現物で作る形)。
#   ★**対照B= そのページが【散文】を渡しているか**(=和文の連なりの最長 ≥ しきい値)。
#     🔴★**A だけでは足りなかった** —— ★実測で、**35文字しか無い CiNii の頁が A を通った**
#       (★題名だけが載っている)。★**ナビは短い句の羅列、散文は長く続く。**
#
# ★★**しきい値の決め方(★都合のよい値を後から選んでいない)**:
#   ★**60 / 100 / 150 を先に並べて3つとも走らせた。**
#   ★**60 と 100 は ✕ の集合が【一致】した(4本)** ⇒ この範囲では結論がしきい値に依らない。
#   ★**150 にすると2本が▲へ移る** ⇒ そこからは依存する。
#   ⇒ ★**依存しない範囲の上端= 100 を採る。**★理由は「4本になるから」ではない。
#
# 🔴★★**対照B は【和文】の連なりで測る。★欧文だけのページは構造的に▲へ落ちる。**
#   ★**実測(2026-08-31)**: 取得できた 37本のうち**欧文が7割を超えるページは 5本**で、
#     ★その和文の連なりの最長は **1〜23** ——★**しきい値 100 に届かない。**
#   ⇒ ★**英文の文献は、この段では「測れなかった」に落ちる。**★**それは安全側だが、
#     ★**見ていない範囲として件数で出す**(`00` §12)。★**黙って落とさない。**
FULLTEXT_UNSEEN = (
    "逐語の引用が無い行は、この段では1項目も確かめていない(照合するものが無い)",
    "引用の出所が本文でない行(キーワード・副題・題目)を、本文に当てには行っていない",
    "欧文だけのページは、対照B(和文の連なり)に届かないので「測れなかった」に落ちる",
    "書誌が原典の記録と合っているかは、この段では見ていない —— 段階B の役",
)

FULLTEXT_EVIDENCE_VERSION = 1
FULLTEXT_UA = "skill-review-checker/stage-C (verbatim presence only)"
FULLTEXT_TIMEOUT_DEFAULT = 25.0
# ★対照B のしきい値。★上の註のとおり、3つ試して**答えが変わらない範囲の上端**を採った。
FULLTEXT_PROSE_MIN = 100
# ★取れたと数える下限。★これは「中身が在る」ではない(→ 対照B が別に見る)。
FULLTEXT_THIN_MIN = 400

# ★逐語の引用= 鍵括弧で囲まれた6文字以上の連なり。
#   ★**原典が「鍵括弧に入れたら逐語」と定めている**ので、その形だけを対象にする。
#   ★uradori= 「③は「」付き逐語引用(取得原文からの転記のみ)」
#   ★bunken = 「原文の文をそのまま持ってくるなら「」で囲み、逐語だと示す」
FULLTEXT_QUOTE_RE = re.compile(r"「([^「」]{6,})」")
# ★和文の連なり(★対照B)。★**ASCII の英字を入れていない**(→ 上の註のとおり、それが欧文の限界である)。
FULLTEXT_JP_RUN_RE = re.compile(r"[぀-ヿ㐀-鿿、。「」()（）・：:,，．\.\-0-9]+")
FULLTEXT_DASHES = "‐‑‒–—―−－ーｰ"


def extract_quotes(cell):
    """セル1つから逐語の引用を取り出す。→ [str]  ★同じ引用は1回だけ。"""
    out, seen = [], set()
    for q in FULLTEXT_QUOTE_RE.findall(cell or ""):
        q = q.strip()
        if q and q not in seen:
            seen.add(q)
            out.append(q)
    return out


def _ft_norm(s, level):
    """正規化の段。★L0 そのまま / L1 空白 / L2 +全角半角(NFKC) / L3 +ダッシュ類。

    🔴★**L4(記号を落とす)は採らない。**★対照の測定を L3 で行ったので、
      ★**測った述語と出荷する述語を揃える**(★測っていない段を出荷しない)。
    """
    import unicodedata
    if level <= 0:
        return s or ""
    t = s or ""
    if level >= 2:
        t = unicodedata.normalize("NFKC", t)
    t = re.sub(r"[\s　]+", "", t)
    if level >= 3:
        t = re.sub("[" + FULLTEXT_DASHES + "]", "-", t)
    return t


FULLTEXT_LEVELS = ((0, "そのまま"), (1, "空白を落とすと"), (2, "全角半角を畳むと"),
                   (3, "ダッシュ類を畳むと"))


# ================================================================================
# 段階C の【抜き書き】の欄(2026-10-31・起票 `KICKOFF-nukigaki-b14-b17.md`・claude-harness の D64)
# --------------------------------------------------------------------------------
# ★原典= 書式 `run-bunken-daicho/references/daicho-format.md` の「抜き書き」の節。★読み方はその節の決まりだけ:
#   ① 外側の「」を1本の抜き書きとして読む(原典「原文の中の「」は、そのまま写す(全体を外側の「」で囲む)」)。
#      ★要旨の欄の `FULLTEXT_QUOTE_RE` は入れ子を読めず、内側の「」だけを拾う ⇒ ★抜き書きの欄には使わない。
#      ★場所の括弧の中の「」(節の見出し)は抜き書きとして読まない。★「」の対が閉じない欄は照らさず ▲(★安全側)。
#   ②「…」で区切った抜き書きは、区切りごとに原文の中で順に照らす(原典「区切りごとに、原文の中で順に照らす」)。
#   ③ 数で始まる区切りは、原文で負号の直後にある所に当てない(原典「原文でその直前にある負号(−)ごと写す」)。
#      ★英数字の直後のハイフンは語の一部(COVID-19・18-65)なので負号にしない。★負号と数の間の空白は飛ばして見る。
#      ★長音の「ー」は、ダッシュ類を畳む段(L3)より前では負号にしない(★L3 では畳んだ後の字しか見えない —— 見ていない範囲)。
#   ④ 場所に「画像から書き写し」とある抜き書きは照らさず、件数と行を申告に出し、止めない
#      (★ユーザーの決定 2026-10-31・D64 の追記。原典「この印の抜き書きは機械では照らせないので、確かめ役が頁の画像と照らす」)。
#   ★頁が正しいかは見ない(★ユーザーの決定 D64 問1 =「在るか」まで)。
#   ★本体の道具 `run-bunken-daicho/scripts/nukigaki.py` は写していない(★同じ作りだと同じ誤りを共有する)。
# ★CiNii の書誌ページ(★ユーザーの決定 2026-10-31「.json も取って照らす」): ★書誌ページの HTML は、この口で取ると
#   中身が空で返る(HTTP 202・0 バイト。2026-10-31 に確かめた)。⇒ ★抜き書きの欄を持つ行に限り、同じ記録の `.json` も
#   当て先に足し、取得の口はその URL だけ JSON を文字として読む。★見つからなければ ▲(★本文と言えないページ)。
#   ★足した URL には印 `#nukigaki` を付ける(★取得の口が「足した URL だけ」を見分ける印。★断片(#…)は要求に乗らない)。
#     ★リンクの欄に `.json` が直に書かれた台帳では、それまでと同じに読む(★要旨の欄と uradori を動かさない)。
# ★★2026-10-31(★別の文脈の確かめで見つかった穴を塞いだ。記録 `runs/checker/JISSOU-nukigaki-b14-b17.md` §9):
#   ⑤ 区切りは1つずつ6字以上(★ユーザーの決定 2026-10-31「6字の下限を置く」。★6 は要旨の欄で「」を逐語と読む下限
#      `FULLTEXT_QUOTE_RE` と同じ数)。★6字に満たない区切りのある抜き書きは照らさず ▲(★細かく刻むと言い換えが通る穴)。
#   ⑥ 区切りは【1本のページの中で】順に照らす(★つないだページの上では照らさない —— 同じ本文が2本あると、順を入れ替えても通った)。
#   ⑦ 場所の括弧が閉じない欄・括弧の中にしか「」の無い欄も「対が閉じない」に数える(★「なし」で始まる欄は除く)。
#   ⑧ 和文のダッシュ(— ―)は負号にしない(★L3 ではダッシュ類を畳むので、そこでは負号に見える —— 見ていない範囲)。
NUKIGAKI_IMAGE_MARK = "画像から書き写し"
NUKIGAKI_SEP = "…"
NUKIGAKI_MINUS = "-−－‐‑‒–"
NUKIGAKI_PIECE_MIN = 6
NUKIGAKI_JSON_MARK = "#nukigaki"
NUKIGAKI_WORD = re.compile(r"[A-Za-z0-9%°]")
NUKIGAKI_NUM_HEAD = re.compile(r"[.]?\d")
NUKIGAKI_CRID_RE = re.compile(r"^https?://cir\.nii\.ac\.jp/crid/(\d+)/?$", re.I)
NUKIGAKI_CRID_JSON_RE = re.compile(r"^https://cir\.nii\.ac\.jp/crid/\d+\.json#nukigaki$")
NUKIGAKI_UNSEEN = (
    "頁が正しいか(★「在るか」までしか見ない —— ユーザーの決定。頁は台帳スキルの道具が書く時に出す)",
    "要旨の箇条が抜き書きと原典に支えられているか(★確かめ役の役)",
    "場所に「画像から書き写し」とある抜き書きが、本当に文字の層の無い頁から書き写した物か(★照らしていないので、"
    "言い換えた抜き書きにこの印を付けても通る —— 確かめ役が頁の画像と照らす)",
    "長音の「ー」・和文のダッシュの直後の数で始まる区切りは、ダッシュ類を畳む段(L3)では負号の直後に見えて当てない"
    "(★その前の段で当たれば当たる)",
    "6字以上の区切りに刻んで、言い換えた文を原文の語の並びで組み立てた抜き書き(★区切りが原文の中に順に在れば通る)",
    "CiNii の .json に関連する別の記録(別の文献の題名や抄録)が入っていると、別の文献の文に当たって「在った」と数えうる",
)


def extract_nukigaki(cell_text):
    """抜き書きの欄から抜き書きを取り出す。→ (照らす [str], 画像から書き写した [str], 「」の対が閉じない数)

    ★外側の「」だけを1本と数える。★場所の括弧(半角・全角)の中の「」は読まない。★括弧は「」の中では字として読む。
    """
    s = cell_text or ""
    stack, tops, start, broken = [], [], None, 0
    # ★分岐は `elif` で書かない(★変異の道具の cond-invert は `elif` を試さない —— 常設テスト F-36 の死角)。
    for i, ch in enumerate(s):
        top = stack[-1] if stack else None
        if ch == "「":
            if top is None:
                start = i
            stack.append("q")
            continue
        if ch == "」":
            if top == "q":
                stack.pop()
                if not stack:
                    tops.append((start, i))
            if top is None:
                broken += 1
            continue
        if ch in "(（" and top != "q":
            stack.append("p")
            continue
        if ch in ")）" and top == "p":
            stack.pop()
    if "q" in stack:
        broken += 1
    if "p" in stack and "q" not in stack:
        broken += 1          # ★場所の括弧が閉じない(★後ろの抜き書きを黙って飲み込まない)
    if not tops and broken == 0 and "「" in s and not s.lstrip().startswith("なし"):
        broken += 1          # ★括弧の中にしか「」が無い(★抜き書きを括弧で包んだ形を、引用の無い欄に数えない)
    out, img = [], []
    for k, (a, b) in enumerate(tops):
        q = s[a + 1:b].strip()
        if not q:
            broken += 1
            continue
        place = s[b + 1:(tops[k + 1][0] if k + 1 < len(tops) else len(s))]
        (img if NUKIGAKI_IMAGE_MARK in place else out).append(q)
    return out, img, broken


def _nk_prev(text, at):
    """at より前で、空白でない字の位置。→ int(★無ければ -1)"""
    j = at - 1
    while j >= 0 and text[j] in " \t\r\n　":
        j -= 1
    return j


def _nk_after_minus(text, at):
    """text の at の直前(★空白を飛ばす)が負号か。★英数字の直後のハイフンは語の一部なので負号にしない。"""
    import unicodedata
    j = _nk_prev(text, at)
    if j < 0 or text[j] not in NUKIGAKI_MINUS:
        return False
    k = _nk_prev(text, j)
    return not (k >= 0 and NUKIGAKI_WORD.fullmatch(unicodedata.normalize("NFKC", text[k])))


def nukigaki_short(q):
    """抜き書きに、空白を落として6字に満たない区切りが在るか。→ bool(★在れば照らさない —— ユーザーの決定 2026-10-31)"""
    pieces = [_ft_norm(x, 1) for x in (q or "").split(NUKIGAKI_SEP)]
    pieces = [p for p in pieces if p]
    return not pieces or min(len(p) for p in pieces) < NUKIGAKI_PIECE_MIN


def nukigaki_found(q, body, level):
    """抜き書き1本が、その正規化の段の本文(★`_ft_norm(本文, level)`)に原文のまま在るか。→ bool"""
    import unicodedata
    pieces = [p for p in (_ft_norm(x.strip(), level) for x in q.split(NUKIGAKI_SEP)) if p]
    if not pieces:
        return False
    pos = 0
    for p in pieces:
        num = NUKIGAKI_NUM_HEAD.match(unicodedata.normalize("NFKC", p[:2])) is not None
        at = body.find(p, pos)
        while at >= 0 and num and _nk_after_minus(body, at):
            at = body.find(p, at + 1)
        if at < 0:
            return False
        pos = at + len(p)
    return True


def nukigaki_urls(urls):
    """抜き書きを当てる URL。→ [str]  ★CiNii の書誌ページには同じ記録の `.json` を足す(★ユーザーの決定 2026-10-31)。"""
    out = list(urls)
    for u in urls:
        m = NUKIGAKI_CRID_RE.match(u)
        if m:
            j = "https://cir.nii.ac.jp/crid/%s.json%s" % (m.group(1), NUKIGAKI_JSON_MARK)
            if j not in out:
                out.append(j)
    return out


def _ft_prose(text):
    """そのページが渡した【和文の連なり】の最長。★対照B の物差し。"""
    return max((len(m) for m in FULLTEXT_JP_RUN_RE.findall(text or "")), default=0)


# 🔴★★**この段が外へ出る口は、下の `fulltext_probe` ただ1つである。**
FULLTEXT_PROBE = None


def fulltext_probe_fn():
    """いま使う取得の口を返す。★差し替えられていなければ `fulltext_probe`。"""
    return FULLTEXT_PROBE or fulltext_probe


def _ft_strip_html(raw, charset):
    """HTML からテキストを取り出す。★**標準ライブラリだけ**で行う。"""
    import html as _html
    t = raw.decode(charset or "utf-8", "replace")
    t = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", t)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    t = _html.unescape(t)
    return re.sub(r"[\s　]+", " ", t).strip()


# ★★PDF の読み取り手段= PyMuPDF(2026-09-28・起票 `KICKOFF-pdf-pymupdf.md`)。
#   ★原典 `run-bunken-daicho/references/wabun-db-guide.md`「本文PDFの読み取り」の手段の順序の 1(PyMuPDF を既定にする)と
#     3(pypdf は和文の本文抽出に使わない)に従う。★常設テストが原典のファイルにこの逐語が現に在ることを確かめる(★消えたら鳴る)。
#   🔴★**それまでは pypdf で読んでいた** —— ★J-STAGE の和文 PDF 15本のうち 8本が、日本語をほぼ1字も含まない文字列
#     (和字率 0.00〜0.08)のまま「取れた(ok)」になった(記録 `runs/checker/JISSOU-stagec-honbun-annai.md` §2-4)。
#     ★同じ15本を PyMuPDF で読むと15本とも読める日本語だった(記録 `runs/checker/JISSOU-pdf-pymupdf.md`)。
#   🔴★**pypdf は、PyMuPDF が無いときの代わりにも使わない**(★原典は「使わない」と言っており、代わりの道具としても挙げていない)。
#     ★無ければ「テキストにできない(no-text)」に数え、理由(PyMuPDF が無い)を名乗る。
#   ★原典の手段の順序の 2(入らない環境では pdfplumber か pdfminer.six)は【入れていない】
#     (★起票の範囲は PyMuPDF への置き換えであり、2 の道具は判定の材料で測っていない —— 測っていない段を出荷しない。
#      ★入れるかは記録 `runs/checker/JISSOU-pdf-pymupdf.md` の判断待ち)。
#   ★★2026-10-06(起票 `KICKOFF-pymupdf-install.md`・ユーザー裁定「説明書に1行足す」)—— ★名前は【`pymupdf` を先に試し、無ければ `fitz`】。
#     ★出所= ユーザーの実測(claude.ai のチャット): PyMuPDF は最初から無く、`pip install pymupdf` で入る(1.28.2)。
#       ★`import fitz` は非推奨の警告が出る(★この機械の 1.27.2.3 でも `fitz` は `pymupdf` を読み込み直すだけの別名だった)。
#     ★説明書 `run-bunken-daicho/SKILL.md` の工程4 に「無ければ機械照合の前に入れる」の1行を足した(★下の4つ目の逐語)。
#     ★判定・記号・終了コード・理由の文は変えていない(★両方無ければ、それまでと1字も同じ理由)。
FULLTEXT_PDF_ORIGIN = (
    ("run-bunken-daicho/references/wabun-db-guide.md",
     "**PyMuPDF(`import fitz` → `doc[i].get_text()`)を既定にする**"),
    ("run-bunken-daicho/references/wabun-db-guide.md",
     "**pypdf は和文の本文抽出に使わない**"),
    # ★uradori の手引きも同じ規定にした(2026-09-28・ユーザー裁定)。★それまでは逐語「**pypdfでテキスト抽出**する」と
    #   pypdf を勧めており、bunken の手引きと向きが逆だった。★手引きが pypdf の勧めに戻れば常設テストが鳴る。
    ("run-uradori/references/verification-playbook.md",
     "★**和文のPDFにpypdfは使わない**"),
    # ★2026-10-06: 説明書の1行(★PyMuPDF が無い環境では入れる)。★消えれば常設テスト LD-51・LD-127 が鳴る。
    #   ★2026-10-11(ch-ylp): uradori・bunken-daicho の説明書にあった同じ1行は、チェッカーの使い方の ref
    #     `ref-nohin-checker` の「走らせ方」に1つにまとめた(逐語は変えていない)。
    ("ref-nohin-checker/SKILL.md",
     "**PyMuPDF が無い環境(claude.ai など)では、上の機械照合を走らせる前に `pip install pymupdf` で入れる**"),
)


def _ft_pdf_text(raw):
    """PDF からテキストを取り出す。→ (text or None, 理由 or None)

    🔴★★**同梱の点検プログラムは標準ライブラリだけで動く。**★PDF の読み取りは
      **在れば使う・無ければ「取れなかった」と数える**。★**依存を必須にしない** ——
      ★この道具は `.skill` に同梱されて配られるので、依存を増やすと配布が壊れる。
    ★読む道具は **PyMuPDF だけ**(→ 上の `FULLTEXT_PDF_ORIGIN`)。★**pypdf は import もしない。**
    ★読むのは先頭 60 ページまで(★pypdf の時代と同じ)。★ページごとの `get_text()` を空白で繋ぎ、空白類を1つに畳む。
    ★名前は【`pymupdf` を先に試し、無ければ `fitz`】(2026-10-06・起票 `KICKOFF-pymupdf-install.md`)。
      ★新しい版の `import fitz` は非推奨の警告を出す(claude.ai の PyMuPDF 1.28.2・ユーザーの実測)。
      ★古い版は `fitz` の名だけのことがある(★記録 `runs/checker/JISSOU-pdf-pymupdf.md` §2-1 の4 の読み。★この機械では確かめていない)。
      ★どちらの名で読んでも、開き方と読み方は同じ。★両方とも import できなければ、それまでと1字も同じ理由を返す(★例外名は `fitz` の側)。
    """
    try:
        import pymupdf as fitz
    except Exception:
        try:
            import fitz
        except Exception as e:
            return None, "PDF を読む道具(PyMuPDF)が無い(%s)" % e.__class__.__name__
    try:
        import itertools as _it
        doc = fitz.open(stream=raw, filetype="pdf")
        parts = []
        for pg in _it.islice(doc, 60):
            try:
                parts.append(pg.get_text() or "")
            except Exception:
                pass
        return re.sub(r"[\s　]+", " ", " ".join(parts)).strip(), None
    except Exception as e:
        return None, "PDF を開けなかった(%s)" % e.__class__.__name__


# ★★段階C-5 —— 転送(リダイレクト)の【着いた先の URL】(2026-10-04・起票 `KICKOFF-stagec-doi-tensou.md`)。
#   ★出所= 担当27-3 の申し送り(記録 `runs/checker/JISSOU-stagec-honbun-annai.md` §15 の②)——
#     ★取得の口が転送後の URL を持たないので、★DOI(`doi.org/…`)で引いたページは、着いた先が J-STAGE の記事ページでも
#       【判定不能】に落ちていた。★bunken の原典は J-STAGE 収録誌に「DOIとJ-STAGE記事直URLを併記」を求めるので、
#       ★実際の台帳は DOI の行を持つ。★原典 `daicho-format.md` 自身が「doi.org はクロスホストのリダイレクトを返す」と書いている。
#   ★直し方: ★取得の口は【同じ要求の応答】が名乗る URL(`urlopen` の戻り値の `url`)を、取得結果に `final_url` として残す。
#     ★新しい要求はしない(★起票 §2「新しい取得の回数を増やさない」)。★追う転送は urllib の既定のまま
#       (★HTTP の転送を既定の段数まで。★頁の中の転送(meta refresh・スクリプト)は追わない)。
#   ★種別(`fulltext_page_kind`)は着いた先の URL で見る —— ★読んだ本文は、その URL の頁のものだからである。
#     ★着いた先の記録が無い取得結果(2026-10-04 より前の取得・差し替えた取得の口)は、引いた URL のままで見る(★それまでの形)。
#     ★★記録が無いものを「転送されなかった」とは言わない(★確かめていない。★申告は別の欄に数える)。
#   🔴★**判定(✕/▲/○)は動かない** —— ★URL を見るのは (イ)「J-STAGE の記事ページ(HTML で取ったもの)= 案内ページ」の1か所だけで、
#     ★案内ページも判定不能も本文に数えない(ユーザー裁定 2026-09-24 の案 (b))。★本文の見分け (ア) は URL を見ない。
#   ★申告は、転送されたページを【引いた URL → 着いた先】の組で名指しし、件数(転送された / されなかった / 記録が無い)を出す。
FULLTEXT_FINAL_KEY = "final_url"
FULLTEXT_HOP_MOVED = "転送された"
FULLTEXT_HOP_SAME = "転送されなかった"
FULLTEXT_HOP_NONE = "着いた先の記録が無い"
FULLTEXT_HOPS = (FULLTEXT_HOP_MOVED, FULLTEXT_HOP_SAME, FULLTEXT_HOP_NONE)
# ★種別の理由に添える一言(★転送されたページだけ。★理由の文は申告で 110字に切られるので、URL はここに入れない)。
FULLTEXT_HOP_NOTE = {FULLTEXT_HOP_MOVED: "(★転送の着いた先の URL で見た)", FULLTEXT_HOP_SAME: "",
                     FULLTEXT_HOP_NONE: ""}
FULLTEXT_HTTP_RE = re.compile(r"^https?://", re.I)


def _ft_final_url(res):
    """応答が名乗る【着いた先の URL】。→ str(★名乗らない・http(s) でない応答は空文字 —— 残さない)"""
    u = getattr(res, "url", None)
    if not isinstance(u, str) or not FULLTEXT_HTTP_RE.match(u):
        return ""
    return u


def _ft_landed(url, rec):
    """種別を見る URL と、転送の札。→ (URL, 札)  ★札は `FULLTEXT_HOPS` のどれか。

    ★記録が無ければ引いた URL のまま、札は「着いた先の記録が無い」(★「転送されなかった」とは言わない)。
    """
    fin = rec.get(FULLTEXT_FINAL_KEY) if isinstance(rec, dict) else None
    if not isinstance(fin, str) or not fin:
        return url, FULLTEXT_HOP_NONE
    if fin == url:
        return url, FULLTEXT_HOP_SAME
    return fin, FULLTEXT_HOP_MOVED


def _ft_shown_url(url, rec):
    """申告の「当てたページ」に出す URL。★転送されたページは「引いた URL → 着いた先」の組で出す。→ str"""
    seen, hop = _ft_landed(url, rec)
    if hop != FULLTEXT_HOP_MOVED:
        return url
    return "%s → %s" % (url, seen)


def _ft_hop_counts():
    """転送の札ごとの 0 の数え表。→ dict"""
    return dict((h, 0) for h in FULLTEXT_HOPS)


def fulltext_probe(url, timeout):
    """URL を1本取って、テキストにする。→ (state, record)

    state の意味:
      `ok`          … テキストが取れた(★「中身が在る」ではない。★対照B が別に見る)
      `thin`        … 取れたが短すぎる
      `no-text`     … テキストにできない(PDF を読む道具(PyMuPDF)が無い・画像PDF・別の種別)
      `unreachable` … ★**届かなかった**(HTTP エラー・接続不能)

    🔴★★**`unreachable`(届かない)と `thin`/`no-text`(届いたが中身が無い)を混ぜない。**
      ★**実測では後者のほうが多い。**★混ぜると「取れなかった」の大半が【届かなかった】と
      読まれるが、実際は**届いたのに渡してもらえなかった**である。
      ★**そして、段階A が見ているのは前者だけである**(=届くか)。★後者は段階A の外側にある。

    ★★`final_url`(2026-10-04・段階C-5): ★**同じ要求の応答**が名乗る【着いた先の URL】
      (★転送が無ければ引いた URL と同じ)。★種別はこの URL で見る。★**新しい要求はしない。**
      ★応答が名乗らなければ残さない(★「転送されなかった」と書かない)。★届かなかったものには残さない。
    """
    import urllib.error
    import urllib.request
    try:
        req = urllib.request.Request(url, headers={"User-Agent": FULLTEXT_UA})
        with urllib.request.urlopen(req, timeout=timeout) as res:
            raw = res.read()
            ctype = (res.headers.get("Content-Type") or "").lower()
            final = _ft_final_url(res)
    except urllib.error.HTTPError as e:
        return "unreachable", {"why": "HTTP %d" % e.code, "how": "-", "text": ""}
    except Exception as e:
        return "unreachable", {"why": e.__class__.__name__, "how": "-", "text": ""}
    if NUKIGAKI_CRID_JSON_RE.match(url) and "json" in ctype:
        # ★2026-10-31: 抜き書きの欄のために足した CiNii の `.json` だけを文字として読む(★ほかの URL の読み方は変えない)。
        state, rec = _ft_json_record(raw)
    else:
        state, rec = _ft_body_record(raw, ctype)
    if final:
        rec[FULLTEXT_FINAL_KEY] = final
    return state, rec


def _ft_json_record(raw):
    """CiNii の記録の `.json` を、取得結果の1本にする。→ (state, record)  ★文字の値を全部つないで本文にする。"""
    import json
    try:
        data = json.loads(raw.decode("utf-8", "replace"))
    except ValueError as e:
        return "no-text", {"why": "JSON として読めない(%s)" % e.__class__.__name__, "how": "json", "text": ""}
    vals, todo = [], [data]
    while todo:
        x = todo.pop()
        if isinstance(x, str):
            vals.append(x)
            continue
        if isinstance(x, dict):
            x = list(x.values())
        if isinstance(x, list):
            todo.extend(reversed(x))
    text = re.sub(r"[\s　]+", " ", " ".join(vals)).strip()
    return ("ok" if len(text) >= FULLTEXT_THIN_MIN else "thin"), {"how": "json", "text": text}


def _ft_body_record(raw, ctype):
    """届いた応答の中身を、取得結果の1本にする。→ (state, record)

    ★2026-10-04 に `fulltext_probe` から切り出した(★中身は1字も変えていない。★着いた先は呼び出し側が足す)。
    """
    if "pdf" in ctype or raw[:5] == b"%PDF-":
        text, why = _ft_pdf_text(raw)
        if text is None:
            return "no-text", {"why": why, "how": "pdf", "text": ""}
        st = "ok" if len(text) >= 200 else "thin"
        return st, {"how": "pdf", "text": text}
    if "html" in ctype or "xml" in ctype or not ctype:
        m = re.search(r"charset=([\w-]+)", ctype)
        text = _ft_strip_html(raw, m.group(1) if m else None)
        st = "ok" if len(text) >= FULLTEXT_THIN_MIN else "thin"
        return st, {"how": "html", "text": text}
    return "no-text", {"why": "テキストにできない種別: %s" % ctype, "how": "other", "text": ""}


def fulltext_evidence_load(path):
    """取得結果を読む。→ (対応表 or None, 読めなかった理由 or None)"""
    import json
    try:
        with open(path, encoding="utf-8") as f:
            doc = json.load(f)
    except OSError as e:
        return None, "取得結果を開けなかった(%s): %s" % (e.__class__.__name__, path)
    except ValueError as e:
        return None, "取得結果が JSON として読めなかった(%s): %s" % (e.__class__.__name__, path)
    if not isinstance(doc, dict) or "results" not in doc:
        return None, "取得結果の形が違う(results が無い): %s" % path
    if doc.get("version") != FULLTEXT_EVIDENCE_VERSION:
        return None, "取得結果の版が違う(この道具は %d を読む / 渡されたのは %r): %s" % (
            FULLTEXT_EVIDENCE_VERSION, doc.get("version"), path)
    if doc.get("stage") != "C":
        return None, "取得結果が段階C のものでない(stage=%r): %s" % (doc.get("stage"), path)
    got = doc["results"]
    if not isinstance(got, dict):
        return None, "取得結果の results が対応表でない: %s" % path
    return got, None


def fulltext_evidence_save(path, results, stamp):
    """取得結果を書く。

    🔴★★**本文そのものが入る。**★判定はここからしか決まらないためである。
      ★★**この置き場は呼び出し側が決める作業用のファイルであって、★木に置くものではない**
      (起票 §2-5「**全文を木に置かない**」)。★木へ入れる記録は**件数と長さだけ**である。
    """
    import json
    doc = {
        "version": FULLTEXT_EVIDENCE_VERSION,
        "stage": "C",
        "tool": "check_deliverable.py",
        "fetched_at": stamp,
        "note": "段階C(逐語が原典に現に在るか)だけの記録である。"
                "★本文が入っているので、木に置かないこと(起票 §2-5)。",
        "results": results,
    }
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")


FULLTEXT_WANTED = []
FULLTEXT_EVIDENCE = None

# ★段階Cの規則。★種別ごとに1本ずつ。★**ここが唯一の対応表である**。
FULLTEXT_RULES = {"uradori": "U-22", "bunken": "B-14"}

# ================================================================================
# 事実の関門【段階C-2】—— その申告が、**納品物に載ったか**
# --------------------------------------------------------------------------------
# ★出所= 起票 `KICKOFF-kanmon-C2-ami.md`(2026-09-01)。★先例= 段階A-3 / 段階B-2。
#
# 🔴★★**段階A の囲み・段階B の囲みとは【別に】置く。**★理由は「読みやすさ」ではない ——
#   ★**段階A・段階B・段階C は別々に走りうる**(`--links` だけ / `--biblio` だけ / `--fulltext` だけ)。
#   ★1つの囲みに畳むと、**片方しか走らせていない走行の申告が、他も走らせたように読める。**
#
# 🔴🔴★★**この工事が閉じたのは「載っていない」ではなく【逆に読める文が載っている】形である。**
#   ★走行の現物(2026-09-01)= 段階C が現に走って「逐語 2本中 在った 2」を出した走行でも、
#     ★**納品物に載るのは段階A(と bunken では段階B)の申告だけで、そこには逐語**
#     「本文の内容と、リンク先に書いてあることが合っているかは確かめていない —— 段階C」
#     ★**が印字されたまま、終了コード 0 で納品できた。**
#   ⇒ ★**受け取った人が納品物だけを読むと「本文は確かめられていない」と読む。**
#   🔴★**段階A・段階B の申告文は1文字も直していない** —— そこはユーザー裁定待ちである
#     (★起票 §2-5・§2-6)。★**この段の申告を隣に置くことで、読み手が現物を持てるようにした。**
#
# ★印は**つなぎ合わせて作る**(`20-evidence-rules.md` §3-E 作法2。★自分の source を検体にしない)。
STAGE_C_MARK = "stage-c" + " v1"
STAGE_C_FENCE_OPEN = STAGE_A_FENCES[0] + STAGE_C_MARK
STAGE_C_HEAD_RAN = ("★事実の関門 段階C —— この納品物について、"
                    "チェッカーが出した申告をそのまま同梱している")
STAGE_C_TAIL = ("★この関門は「引いた逐語が原典に現に在るか」しか見ていない。"
                "合格は、その中身が正しいという意味ではない。")
# ★チェッカーが無い環境で貼る定型文。★**空にしないための受け皿である。**
#   🔴★**3行目に句点を置かない**(★原典で鍵括弧に入れると `R-14` が鳴る。★段階A-3 が現に踏んだ)。
STAGE_C_NORUN = (
    "★事実の関門 段階C —— ★チェッカーを走らせていない環境で作った納品物である",
    "・★引いた逐語が原典に現に在るかは、1本も確かめていない(段階Cを走らせていない)",
    "・★これは「0件だった」ではない。「確かめていない」である",
)
STAGE_C_EMBED_RULES = {"uradori": "U-23", "bunken": "B-16"}

# ================================================================================
# 事実の関門【段階C-3】—— 当てたページは【本文】か【案内ページ】か(★申告に出すだけ)
# --------------------------------------------------------------------------------
# ★出所= 起票 `KICKOFF-stagec-honbun-annai.md`(2026-09-05)の逐語
#   「段階C の申告に「取れたのは本文か案内ページか」を出す」と、同 §7 のユーザー裁定(2026-09-22)。
# ★裁定③(2026-09-22)の時点では **✕/▲/○ を1つも動かさなかった**(★この段は種別を数えて申告に出すだけだった)。
# 🔴★★**2026-09-24 に動いた**(起票 `KICKOFF-stagec-nise-batsu.md`)——
#   ★**その行で取れたページに【本文】が1本も無く、対照A・B を通り、それでも逐語が無い**ときは ✕ にせず ▲ にする。
#   ★第1部(skills `b0ece6a`)= 案内ページだけの行。★第2部 = 判定不能のページを含む行も(★ユーザー裁定 2026-09-24 の案 (b)
#     「見分けられないページにしか当てられず、引用が見つからなかった行は、すべて ▲」)。
#   ★理由= 本文と数えないページ(案内ページ・判定不能)に無いことは、原典に無いことを言い切らない
#     (★本物の引用に偽の違反が立った現物が在る)。
#   ★**本文のページに当てて無かったものの ✕ は動かさない。**
#   ★裁定の条件=「▲ になった引用はチャットで報告する」⇒ ★申告の「測れなかった」の1件ずつに、当てたページの URL と種別を出す。
#   ★格上げの検出は別の起票(`KICKOFF-stagec-kakuage.md`)。
# ★★2026-10-04(段階C-5・起票 `KICKOFF-stagec-doi-tensou.md`): ★(イ)の頁は【転送の着いた先の URL】で見る(→ `fulltext_probe` の上の註)。
#   ★判定(✕/▲/○)は動かない(★案内ページも判定不能も本文に数えない)。★動くのは種別・数え・申告の行だけである。
# ★見分け方= 裁定①(ウ)。★語は3つ= 裁定②(★**判定不能は本文に数えない**)。
#   (イ) ★**原典が名指しする頁の種別** —— ★J-STAGE の記事ページ = 案内ページ。
#   (ア) ★**取り方と化け検知** —— ★取り方が PDF で、化けていない = 本文。
#        ★化けていない = ★**題名が出る**(原典の検知法)**かつ** ★**和字率がしきい値以上**。
#        ★和字率を足した理由= 第1段の実測で、★**題名だけ読めて本文の大半が化けた PDF が1本在った**
#          (★原典が挙げた「本文は読めるのに題名だけ化ける」の逆向き)。
#   ★**どちらにも当たらなければ【判定不能】**として、件数と名前(行と URL)で出す。
# 🔴🔴★★**和字率のしきい値= 0.2(★ユーザー裁定・2026-09-23)。★原典が決めていない値である。**
#   ★決め方(裁定の逐語「(ア)の和字率のしきい値は、第2段で先に並べて走らせてから決める」のとおり):
#     ★候補を先に並べて現物に当てた(記録 `runs/checker/JISSOU-stagec-honbun-annai.md` §13)——
#     ★化けた PDF の最大 0.082 / 読める PDF の最小 0.394。★0.09〜0.39 のどこに置いても結果が同じ。
#     ★ユーザーがその安全帯の真ん中として 0.2 を選んだ。★和字率の定義は第1段と同じ(空白込み)。
#   ★経緯: 第2段の1回目(skills `7727b5e`)は値を持たずに(None)出荷し、PDF を全部判定不能に置いていた。
#   ⇒ ★**None に戻すと、その振る舞いに戻る**(★歯止めとして枝を残す。★測っていないものを合格にしない)。
#   ⇒ ★**値は、走行のたびに申告の中で名乗る**(★黙って判定しない)。
# ★題名の照合は**対照A と同じ述語**(正規化 L3 の部分一致)を、ページ1本ずつに当てる(★新しい述語を書き起こさない)。
# ★★原典の逐語(★常設テストが原典のファイルに現に在ることを確かめる。★消えたら鳴る)。
FULLTEXT_KIND_ORIGIN = (
    ("run-uradori/references/daicho-format.md",
     "**抄録どまり** … 抄録・要約・書誌・目次だけで判定した(ペイウォール、J-STAGEの記事ページのみ 等)"),
    ("run-bunken-daicho/references/wabun-db-guide.md",
     "**★文字化けの検知は「日本語の割合」だけではすり抜ける。「書誌の題名が出るか」で行う**"),
)
# 🔴★2026-09-28(ユーザー裁定・起票 `KICKOFF-pdf-pymupdf.md` の続き)—— ★原典の上の一文は、それまで
#   「日本語の割合」【ではなく】「書誌の題名が出るか」で行う、だった(★割合を使うことを退ける字面)。
#   ★この点検プログラムは題名【に加えて】和字率も見るので、★字面の上で原典と食い違っていた。
#   ★原典が割合を退けた理由は「割合【だけでは】すり抜ける」(本文は読めるのに題名だけ化ける PDF)であり、
#     ★ここは題名を必須にしているので中身は矛盾しない ⇒ ★原典の字面を「だけではすり抜ける」に言い換えた(★案 (イ))。
FULLTEXT_KIND_BODY = "本文"
FULLTEXT_KIND_GUIDE = "案内ページ"
FULLTEXT_KIND_UNKNOWN = "判定不能"
FULLTEXT_KINDS = (FULLTEXT_KIND_BODY, FULLTEXT_KIND_GUIDE, FULLTEXT_KIND_UNKNOWN)
# ★「本文に近い」順。★引用がどのページで当たったかを1つに畳むときだけ使う(★判定不能は案内ページより前 ——
#   ★「案内ページだけで当たった」と言い切れないものを、案内ページに数えない)。
FULLTEXT_KIND_RANK = {FULLTEXT_KIND_BODY: 0, FULLTEXT_KIND_UNKNOWN: 1, FULLTEXT_KIND_GUIDE: 2}
# ★(イ)の頁= J-STAGE の記事ページ(`/article/…/_article`)。★`_pdf`・`_html` は当たらない。
FULLTEXT_GUIDE_PAGE_RE = re.compile(
    r"^https?://(?:www\.)?jstage\.jst\.go\.jp/article/[^?#\s]*/_article(?:[/?#]|$)", re.I)
# ★(イ)の頁を【取り方】でも確かめる —— ★HTML で取ったものだけを案内ページと言う(2026-09-24・起票 `KICKOFF-stagec-nise-batsu.md`)。
#   🔴★**この日から、種別は判定を1マス動かす**(案内ページにしか当てられなかった ✕ を ▲ にする)。
#   ★⇒ URL の形だけで決めると、★**記事ページの形の URL で PDF(本文)が返ったものまで案内ページと言い、
#     本文に当てて無かった ✕ を ▲ に下げる口になる**(★迂回する動機のある書き方)。★原典が名指しするのは【記事ページ】であり、PDF ではない。
FULLTEXT_GUIDE_HOWS = ("html",)
# ★和字= 平仮名・片仮名・漢字。★和字率= 和字の字数 ÷ 取れたテキストの全字数(★第1段の実測と同じ述語)。
FULLTEXT_WAJI_RE = re.compile(r"[぀-ヿ㐀-鿿]")
# ★ユーザー裁定(2026-09-23)。★変えるならユーザーの裁定で(★上の註)。
FULLTEXT_WAJI_MIN = 0.2
FULLTEXT_KIND_UNSEEN = (
    "抄録だけの PDF(発表要旨など)も、化けていなければ「本文」と数える(★見分けていない)",
    "HTML で本文を出すページは「本文」と言えず、判定不能に落ちる",
    "J-STAGE 以外の案内ページ(CiNii・機関リポジトリの書誌ページ等)は「案内ページ」と言えず、判定不能に落ちる",
    # ★2026-10-04(段階C-5): ★旧い行「DOI などで転送された先の頁の種別は見ていない(取得の口が転送後の URL を持たない)
    #   —— 判定不能に落ちる」は、取得の口が着いた先を残すようになって偽になった。★残る外側を下の2行で名乗る。
    "着いた先の URL の記録が無い取得結果(2026-10-04 より前の取得・差し替えた取得の口)では、転送された先の頁の種別は"
    "見ていない —— 引いた URL のままで見る(DOI は判定不能に落ちる)",
    "追う転送は HTTP の転送(urllib の既定の段数まで)だけ —— 頁の中の転送(meta refresh・スクリプト)は追わず、"
    "その頁を着いた先として見る",
    "英語の本文 PDF は、和字率で「本文」に届かず判定不能に落ちる",
    "判定不能のページが実は本文(J-STAGE 以外の HTML の本文・英語の本文 PDF・題名の照合で落ちる読める PDF)でも、"
    "そこで無かった逐語は違反にせず「測れなかった」に置く —— 本当に無い引用を違反として捕まえない"
    "(ユーザー裁定 2026-09-24)",
)
# ★★本文のページに1本も当てられなかった外れ(★ユーザー裁定 2026-09-24 = 案 (b))。→ {最良の種別: (数えの鍵, 理由)}
#   ★✕ にせず ▲(測れなかった)に置く。★本文と数えないページ(裁定②)では「無い」とも言い切らない。
#   ★案内ページと判定不能のページが混ざる行は、最良の種別(本文 → 判定不能 → 案内ページ)で判定不能に数える。
FULLTEXT_NOBODY = {
    FULLTEXT_KIND_GUIDE: ("guide_only",
                          "案内ページにしか当てられなかった —— 本文を取れていないので「無い」と言い切れない(違反にしない)"),
    FULLTEXT_KIND_UNKNOWN: ("unknown_only",
                            "本文と言えないページ(判定不能を含む)にしか当てられなかった —— 「無い」と言い切れない"
                            "(違反にしない)"),
}


def _ft_missing_label(d):
    """テキストの無いページの札(★申告の「当てたページ」に出す)。→ str"""
    return ("取れていない: %s" % (d.get("state") or "?")) if isinstance(d, dict) else "取得結果に無い"


def _ft_waji_ratio(text):
    """取れたテキストの【和字率】。→ 0.0〜1.0(★空なら 0.0)"""
    t = text or ""
    return len(FULLTEXT_WAJI_RE.findall(t)) / max(1, len(t))


def _ft_title_in(titles, text):
    """★対照A と同じ述語(正規化 L3 の部分一致)を、ページ1本に当てる。→ bool"""
    body = _ft_norm(text, 3)
    return any(_ft_norm(t, 3) and _ft_norm(t, 3) in body for t in titles)


def fulltext_page_kind(url, rec, titles):
    """当てたページ1本の種別。→ (種別, 理由)  ★種別は `FULLTEXT_KINDS` のどれか。

    ★裁定①(ウ)の順に見る —— (イ)名指しの頁(★HTML で取ったもの)→ (ア)化けていない PDF → 判定不能。
    🔴★**判定を動かす**(2026-09-24): ★その行のページに【本文】が1本も無ければ、逐語が無くても ✕ にせず ▲。
      ★○ と、他の ▲ の分岐には使わない。
    ★★(イ)の頁は【転送の着いた先の URL】で見る(2026-10-04・段階C-5)。★着いた先の記録が無ければ引いた URL のまま。
      ★(ア)は URL を見ない(★転送の有無で本文かどうかは変わらない)。
    """
    rec = rec or {}
    seen, hop = _ft_landed(url, rec)
    if FULLTEXT_GUIDE_PAGE_RE.search(seen or "") and rec.get("how") in FULLTEXT_GUIDE_HOWS:
        return FULLTEXT_KIND_GUIDE, ("J-STAGE の記事ページ(原典が「抄録どまり」の例に名指しする頁)"
                                     + FULLTEXT_HOP_NOTE[hop])
    if rec.get("how") != "pdf":
        return FULLTEXT_KIND_UNKNOWN, ("原典が名指しする頁でも PDF でもない(取り方= %s)"
                                       % (rec.get("how") or "?")) + FULLTEXT_HOP_NOTE[hop]
    text = rec.get("text") or ""
    if not titles:
        return FULLTEXT_KIND_UNKNOWN, "PDF だが、題名の鍵括弧が無く化けを確かめられない"
    if not _ft_title_in(titles, text):
        return FULLTEXT_KIND_UNKNOWN, "PDF だが、題名がテキストに出ない(化けの疑い)"
    ratio = _ft_waji_ratio(text)
    if FULLTEXT_WAJI_MIN is None:
        return FULLTEXT_KIND_UNKNOWN, ("PDF で題名は出たが、和字率(%.2f)のしきい値が無い"
                                       "(未設定)—— 本文と数えない" % ratio)
    if ratio < FULLTEXT_WAJI_MIN:
        return FULLTEXT_KIND_UNKNOWN, ("PDF だが、和字率 %.2f がしきい値 %.2f に届かない(化けの疑い)"
                                       % (ratio, FULLTEXT_WAJI_MIN))
    return FULLTEXT_KIND_BODY, "化けていない PDF(題名が出て、和字率 %.2f)" % ratio


def _ft_best_kind(kinds):
    """いちばん本文に近い種別。→ 種別(★空なら判定不能)"""
    return min(kinds, key=FULLTEXT_KIND_RANK.get) if kinds else FULLTEXT_KIND_UNKNOWN


def _ft_kind_counts():
    """種別ごとの 0 の数え表。→ dict"""
    return dict((k, 0) for k in FULLTEXT_KINDS)


def stage_c_declaration(kind, results):
    """★段階Cの申告文の正本。→ [行](★囲みの中身。★囲みの行は含まない)

    🔴★★**ここが唯一の作成地点である。**★画面へ出す文と、納品物に同梱されているかを
      照合する文を**別々に書き起こさない** —— 別に書けば、**ずれても誰も気づけない。**
      ★先例= `stage_a_declaration` / `stage_b_declaration` の註と同じ理由である。
    ★**数え直さない。**★数えているのは `U-22` / `B-14` である(`state_info["stageC"]`)。
    """
    rid = FULLTEXT_RULES.get(kind)
    hit = [x for x in results if x.rule_id == rid] if rid else []
    info = (hit[0].state_info.get("stageC") if hit else None) or {}
    if not info:
        # ★段階Cの結果が取れない(規則が原典を失った等)。★**0で埋めない。**
        return [STAGE_C_HEAD_RAN,
                "・★段階Cの結果が取れなかった —— この走行では、"
                "引いた逐語が原典に在るかを1本も言えない"]
    un = info.get("unmeasured", []) or []
    out = [STAGE_C_HEAD_RAN]
    if info.get("state") == "no_column":
        # 🔴★**0を並べるだけにしない。**★「列が無い」と「0本だった」は別の事実である。
        out.append("・★要旨(逐語)の列が無い —— この段は照合するものを持たない"
                   "(★確かめて合っていた、ではない)")
    out.append("・確かめたこと: 台帳の逐語の引用 %d本のうち、"
               "原典に現に在った %d本 / 無かった %d本"
               % (info.get("quotes", 0), info.get("ok", 0), info.get("ng", 0)))
    out.append("・★そのまま当たった %d本 / 正規化して当たった %d本"
               "(★正規化した分は「一字一句そのままではなかった」という事実である)"
               % (info.get("exact", 0), info.get("normalized", 0)))
    # ★★段階C-3 —— 当てたページの種別(★起票 `KICKOFF-stagec-honbun-annai.md`)。★数え直さない。
    kc = info.get("kinds") or _ft_kind_counts()
    n_pages = sum(kc.get(k, 0) for k in FULLTEXT_KINDS)
    out.append("・★当てたページの種別(取れたページ %d本・行ごとに数える): 本文 %d本 / 案内ページ %d本 / "
               "判定不能 %d本 —— ★判定不能は本文に数えない%s"
               % (n_pages, kc.get(FULLTEXT_KIND_BODY, 0), kc.get(FULLTEXT_KIND_GUIDE, 0),
                  kc.get(FULLTEXT_KIND_UNKNOWN, 0),
                  "" if n_pages else "(★取れたページが0本 —— 種別は1本も判定していない)"))
    for lineno, u, why in (info.get("kind_unknown") or []):
        out.append("   - %s%s —— 判定不能: %s"
                   % (("L%d " % lineno) if lineno else "", str(u)[:90], str(why)[:110]))
    # ★★段階C-5 —— 転送(リダイレクト)。★種別は着いた先の URL で見た(★数え直さない。★数えているのは `U-22` / `B-14`)。
    #   ★勘定は閉じる: 取れたページ = 転送された + 転送されなかった + 着いた先の記録が無い。
    #   ★名指しの行は「   - 転送 」で始める(★「測れなかった」の1件ずつ(「   - L」で始まる)と取り違えない)。
    hc = info.get("hops") or _ft_hop_counts()
    out.append("・★転送(リダイレクト): 取れたページ %d本のうち 転送された %d本 / 転送されなかった %d本 / "
               "着いた先の記録が無い %d本 —— ★転送されたページは着いた先の URL で種別を見た。"
               "★記録が無いページは引いた URL のままで見た%s"
               % (n_pages, hc.get(FULLTEXT_HOP_MOVED, 0), hc.get(FULLTEXT_HOP_SAME, 0),
                  hc.get(FULLTEXT_HOP_NONE, 0),
                  "" if n_pages else "(★取れたページが0本 —— 着いた先は1本も見ていない)"))
    for lineno, u, fin, kd in (info.get("moved") or []):
        out.append("   - 転送 %s%s → %s(%s)" % (("L%d " % lineno) if lineno else "", u, fin, kd))
    ok_k = info.get("ok_by_kind") or _ft_kind_counts()
    out.append("・★原典に在った %d本の内訳: 本文で当たった %d本 / 案内ページで当たった %d本 / "
               "判定不能のページで当たった %d本"
               % (info.get("ok", 0), ok_k.get(FULLTEXT_KIND_BODY, 0),
                  ok_k.get(FULLTEXT_KIND_GUIDE, 0), ok_k.get(FULLTEXT_KIND_UNKNOWN, 0)))
    ng_k = info.get("ng_by_kind") or _ft_kind_counts()
    # ★2026-09-24(起票 `KICKOFF-stagec-nise-batsu.md`・ユーザー裁定 (b)): ★本文のページに当てられなかったものは
    #   「無かった」に数えない(★✕ にせず ▲)。⇒ ★「無かった」は本文に当てて無かったものだけになる
    #   (★恒等的に 0 になる欄を印字しない)。★本文の無い外れは、別の2行で件数を出す。
    out.append("・★無かった %d本(★すべて本文のページに当てて無かったもの: %d本。★本文と言えないページにしか"
               "当てられなかった外れは、下の2行に数えて「無かった」に入れない)"
               % (info.get("ng", 0), ng_k.get(FULLTEXT_KIND_BODY, 0)))
    # 🔴★**申告の文に判定の記号を書かない**(★画面の記号を数える対照が、申告の中の記号を判定と取り違える)。
    out.append("・★案内ページにしか当てられず、無いと言い切れなかった: %d本 —— ★違反にせず「測れなかった」に置いた"
               "(★「無かった」に数えない。★本文に当てるまで確かめていない)" % info.get("guide_only", 0))
    out.append("・★判定不能のページ(案内ページと混ざる行を含む)にしか当てられず、無いと言い切れなかった: %d本 —— "
               "★違反にせず「測れなかった」に置いた(★ユーザー裁定 2026-09-24)" % info.get("unknown_only", 0))
    out.append("・★種別の見分け方: J-STAGE の記事ページ(HTML で取ったもの)= 案内ページ(原典が名指し)/ "
               "化けていない PDF(題名が出て、和字率がしきい値以上)= 本文 / どちらにも当たらない= 判定不能")
    out.append("・★化けの検知に使う和字率のしきい値: %s"
               % ("★未設定 —— PDF は題名が出ても本文と数えず、判定不能に置いている"
                  if FULLTEXT_WAJI_MIN is None else
                  "%.2f(★空白込みの全字数に対する平仮名・片仮名・漢字の割合。"
                  "★原典が決めていない値で、ユーザー裁定で決めた)" % FULLTEXT_WAJI_MIN))
    for line in FULLTEXT_KIND_UNSEEN:
        out.append("・★種別について確かめていないこと: %s" % line)
    # ★★2026-10-31(起票 `KICKOFF-nukigaki-b14-b17.md`)—— 抜き書きの欄(★bunken の台帳がその欄を持つときだけ出す。
    #   ★欄の無い台帳と uradori の申告は、それまでと1字も同じ)。★数え直さない(★数えているのは `B-14`)。
    nk = info.get("nukigaki")
    if nk:
        out.append("・★抜き書きの欄: 照らした %d本のうち 原典に在った %d本 / 無かった %d本 / 測れなかった %d本"
                   "(★外側の「」を1本として読み、「…」の区切りは順に、数で始まる区切りは負号の直後に当てずに照らした)"
                   % (nk.get("quotes", 0), nk.get("ok", 0), nk.get("ng", 0), nk.get("unmeasured", 0)))
        out.append("・★CiNii の書誌ページ(中身が空で返る)に、同じ記録の .json を当て先として足した: %d本"
                   "(★抜き書きだけに当てた。★本文と言えないページなので、無くても違反にしない)" % nk.get("json", 0))
        img = nk.get("image") or []
        out.append("・★画像から書き写した抜き書き: %d本 —— ★照らしていない(機械では照らせない。確かめ役が頁の画像と照らす。"
                   "★違反にも「測れなかった」にもしていない・ユーザーの決定 2026-10-31)" % len(img))
        for lineno, q in img:
            out.append("   - 画像 L%d 「%s」" % (lineno, str(q)[:80]))
        out.append("・★抜き書きの「」の対が閉じない: %d行%s —— ★照らさず「測れなかった」に置いた"
                   % (len(nk.get("broken") or []), lineno_list(nk.get("broken") or [])))
        out.append("・★区切りが %d字に満たない抜き書き: %d本 —— ★照らさず「測れなかった」に置いた"
                   "(★細かく刻むと言い換えが通るので・ユーザーの決定 2026-10-31)"
                   % (NUKIGAKI_PIECE_MIN, len(nk.get("short") or [])))
        for line in NUKIGAKI_UNSEEN:
            out.append("・★抜き書きについて確かめていないこと: %s" % line)
    out.append("・★逐語の引用が無い行: %d行(この段では1項目も確かめていない)"
               % info.get("rows_no_quote", 0))
    out.append("・★届かなかった: %d本(★段階A が見ているのはここだけである)"
               % info.get("unreachable", 0))
    out.append("・★届いたが中身を渡していない: %d本(★上とは別である)"
               % info.get("no_content", 0))
    out.append("・★対照が置けない(題名の鍵括弧が無い): %d本" % info.get("no_control", 0))
    for line in FULLTEXT_UNSEEN:
        out.append("・★確かめていないこと: %s" % line)
    out.append("・★測れなかった %d件%s"
               % (len(un), "" if un else "(★0件。★確かめた結果として0である)"))
    # ★2026-09-24(ユーザー裁定の条件「▲ になった引用はチャットで報告する。台帳をユーザーは基本的に見ない」):
    #   ★1件ずつ、行・引用の要点・理由に加えて【当てたページの URL と種別】を出す(★人に渡せる形。★チャットへ写す)。
    pages = info.get("pages") or {}
    for lineno, q, why in un:
        out.append("   - %s%s —— %s"
                   % (("L%d " % lineno) if lineno else "", str(q)[:90], str(why)[:110]))
        out.append("       当てたページ: %s"
                   % (" / ".join("%s(%s)" % (u, k) for u, k in (pages.get(lineno) or []))
                      or "(記録なし)"))
    out.append("・★この段の合格は「0件」ではない —— "
               "「取れたものについて0件」と【取れなかった件数】がセットである")
    out.append(STAGE_C_TAIL)
    return out


def check_quote_presence(rule_id, rows, quote_i, link_i, bib_i, header_present, evidence, nukigaki_i=None):
    """段階C の判定を1規則ぶん組み立てる。

    ★✕ は **対照A(題名が在る)と対照B(散文が在る)の両方を通り、それでも逐語が無い**ときだけ。
    ★それ以外の外れは ▲(測れなかった)であり、**合格ではない**。
    ★`nukigaki_i`(2026-10-31・bunken の「抜き書き」の欄)を渡したときだけ、その欄も同じ当て先・同じ対照・同じ ✕/▲ の
      分かれ方で照らす(★読み方は `extract_nukigaki` と `nukigaki_found` の上の註)。★渡さなければ、それまでと1字も同じ。
    """
    r = Result(rule_id, *rule_meta(rule_id))
    empty = {"state": "no_column", "quotes": 0, "ok": 0, "ng": 0, "unmeasured": [],
             "rows_no_quote": 0, "exact": 0, "normalized": 0, "unreachable": 0,
             "no_content": 0, "no_control": 0,
             # ★段階C-3(当てたページの種別)。★判定を動かすのは本文の無い外れ(`guide_only` / `unknown_only`)だけ(2026-09-24)。
             # ★`pages` = 行ごとの当てたページ(URL と種別)。★申告の「測れなかった」の一覧に出す。
             "kinds": _ft_kind_counts(), "kind_unknown": [],
             "ok_by_kind": _ft_kind_counts(), "ng_by_kind": _ft_kind_counts(), "guide_only": 0,
             "unknown_only": 0, "pages": {},
             # ★段階C-5(2026-10-04): 転送の札(`hops`)と、転送されたページの名指し(`moved` = 行・引いた URL・着いた先・種別)。
             "hops": _ft_hop_counts(), "moved": []}
    if link_i is None:
        # ★リンク列が無いと当て先が決まらない。★**そこは U-1 / B-1 が別に違反にする。**
        skip_as(r, "リンク列が見つからない(列名の確認が先)",
                "missing_input", what="リンク列", supplier="納品物")
        r.state_info["stageC"] = empty
        return r
    if quote_i is None and nukigaki_i is None:
        # 🔴★★**要旨(逐語)の列が無いことを、この規則は違反にしない。**
        #   ★原典はこの列を**推奨・条件付き**と定めており、★**必須ではない**
        #   (`daicho-format.md` の列の要否表)。★列が無ければ**逐語の引用が0本**であり、
        #   ★**この段は照合するものを持たない**、というだけである。
        #   ★★**ここを「検査に必要な情報が無い」にすると、門番(U-0/B-0)が納品を止める。**
        #     ★推奨の列が無いだけで納品を止めるのは、原典が定めていない。
        r.ok_note("要旨(逐語)の列が無い(= 鍵括弧で囲まれた逐語の引用が0本)"
                  " ※この段は照合するものを持たない。**確かめて合っていた、ではない**")
        r.observe("clean", scanned=len(rows), targets=0)
        r.state_info["stageC"] = dict(empty, state="no_column")
        return r
    if not header_present:
        skip_as(r, "台帳本体の表が見つからない(列名の確認が先)",
                "missing_input", what="要旨(逐語)列・リンク列", supplier="納品物")
        r.state_info["stageC"] = empty
        return r
    targets, rows_no_quote = [], 0
    # ★抜き書きの欄の数え(★欄が在るときだけ申告に出す)。`image` = 画像から書き写した (行, 抜き書き) /
    #   `broken` = 「」の対が閉じない行 / `short` = 6字に満たない区切りのある (行, 抜き書き) /
    #   `json` = CiNii の書誌ページに足した `.json` の本数。
    nk = None if nukigaki_i is None else {"quotes": 0, "ok": 0, "ng": 0, "unmeasured": 0,
                                          "image": [], "broken": [], "short": [], "json": 0}
    for lineno, row in rows:
        qs = extract_quotes(cell(row, quote_i)) if quote_i is not None else []
        nqs, nimg, nbr = extract_nukigaki(cell(row, nukigaki_i)) if nk is not None else ([], [], 0)
        nshort = [q for q in nqs if nukigaki_short(q)]
        nqs = [q for q in nqs if not nukigaki_short(q)]
        if nk is not None:
            nk["image"].extend((lineno, q) for q in nimg)
            nk["short"].extend((lineno, q) for q in nshort)
            if nbr:
                nk["broken"].append(lineno)
        if not qs and not nqs:
            if not nimg and not nbr and not nshort:
                rows_no_quote += 1
            continue
        urls = [u for u in LINK_URL_RE.findall(cell(row, link_i))]
        titles = extract_quotes(cell(row, bib_i)) if bib_i is not None else []
        if not urls:
            rows_no_quote += 1
            continue
        targets.append((lineno, qs, urls, titles, nqs))
    base = {"state": "judged", "quotes": sum(len(t[1]) + len(t[4]) for t in targets), "ok": 0, "ng": 0,
            "unmeasured": [], "rows_no_quote": rows_no_quote, "exact": 0, "normalized": 0,
            "unreachable": 0, "no_content": 0, "no_control": 0,
            "kinds": _ft_kind_counts(), "kind_unknown": [],
            "ok_by_kind": _ft_kind_counts(), "ng_by_kind": _ft_kind_counts(), "guide_only": 0,
            "unknown_only": 0, "pages": {}, "hops": _ft_hop_counts(), "moved": []}
    nk_broken = []
    if nk is not None:
        nk["quotes"] = sum(len(t[4]) for t in targets)
        nk["json"] = sum(len(nukigaki_urls(t[2])) - len(t[2]) for t in targets if t[4])
        base["nukigaki"] = nk
        nk_broken = [(ln, "抜き書きの欄", "抜き書きの「」の対が閉じない —— 外側の抜き書きを切り出せないので照らしていない")
                     for ln in nk["broken"]]
        nk_broken += [(ln, _nk_label(q, True), "区切りが %d字に満たない —— 照らしていない(★細かく刻むと言い換えが通るので)"
                       % NUKIGAKI_PIECE_MIN) for ln, q in nk["short"]]
    if evidence is None:
        if nk is not None:
            nk["unmeasured"] = nk["quotes"]
        for _ln, _qs, urls, _t, nqs in targets:
            for u in (nukigaki_urls(urls) if nqs else urls):
                if u not in FULLTEXT_WANTED:
                    FULLTEXT_WANTED.append(u)
        r.blocked("本文の取得結果が渡されていない —— この走行は原典を1本も取っていない"
                  "(--fulltext で取得結果を渡す。--fetch-fulltext で取得できる)。"
                  "対象は %d本の逐語(逐語の引用が無い行 %d行)%s"
                  % (base["quotes"], rows_no_quote, _nk_note(nk)))
        r.observe("missing_input", what="本文の取得結果", supplier="呼び出し", handed=False)
        base["state"] = "not_fetched"
        base["unmeasured"] = nk_broken + [(ln, _nk_label(q, k), "取得結果が渡されていない")
                                          for ln, qs, _u, _t, nqs in targets
                                          for q, k in [(x, False) for x in qs] + [(x, True) for x in nqs]]
        base["pages"] = dict((ln, [(u, "取っていない") for u in dict.fromkeys(nukigaki_urls(urls) if nqs else urls)])
                             for ln, _qs, urls, _t, nqs in targets)
        r.state_info["stageC"] = base
        return r
    base["unmeasured"].extend(nk_broken)
    if not targets:
        if base["unmeasured"]:
            r.blocked("段階C: 照らせる逐語が0本 / ★未検査 %d件%s —— **未検査が残っている。合格ではない。**"
                      % (len(base["unmeasured"]), _nk_note(nk)))
            r.observe("missing_input", what="抜き書きの欄", supplier="納品物")
            base["state"] = "empty"
            r.state_info["stageC"] = base
            return r
        r.ok_note("鍵括弧で囲まれた逐語の引用が0本(この台帳では照合するものが無かった)"
                  " ※逐語の引用が無い行 %d行の要旨は、この段では1項目も確かめていない%s"
                  % (rows_no_quote, _nk_note(nk)))
        r.observe("clean", scanned=len(rows), targets=0)
        base["state"] = "empty"
        r.state_info["stageC"] = base
        return r
    for lineno, qs, urls, titles, nqs in targets:
        # ★抜き書きの欄を持つ行は、CiNii の書誌ページに同じ記録の `.json` を足した当て先(★抜き書きだけが使う)。
        #   ★要旨の逐語は、それまでと同じ `urls` だけに当てる。
        all_urls = nukigaki_urls(urls) if nqs else urls
        # ★段階C-3: 当てたページの種別を1本ずつ数える(★行ごと。★同じ行の同じ URL は1回)。
        #   🔴★**判定に使うのは1か所だけ**(2026-09-24・起票 `KICKOFF-stagec-nise-batsu.md`)——
        #     ★✕ を立てる直前の「本文のページが在るか」。★○ と、他の ▲ の分岐はこの表を1度も読まない。
        #   ★テキストの無いページも「当てたページ」として札つきで残す(★申告の「測れなかった」に URL と種別を出すため)。
        #     ★種別の数え(`kinds`)はテキストの在るページだけである(★この段の前後で数えは変わらない)。
        paged = []
        where = []
        by_url = {}
        for u in dict.fromkeys(all_urls):
            d = evidence.get(u)
            if isinstance(d, dict) and d.get("text"):
                kd, why = fulltext_page_kind(u, d, titles)
                paged.append((kd, d))
                by_url[u] = (kd, d)
                where.append((_ft_shown_url(u, d), kd))
                base["kinds"][kd] += 1
                # ★段階C-5: 転送の札を、種別と同じ粒度(行ごと・URL ごと・テキストの在るページ)で数える(★数え直さない)。
                seen, hop = _ft_landed(u, d)
                base["hops"][hop] += 1
                if hop == FULLTEXT_HOP_MOVED:
                    base["moved"].append((lineno, u, seen, kd))
                if kd == FULLTEXT_KIND_UNKNOWN:
                    base["kind_unknown"].append((lineno, u, why))
            else:
                where.append((_ft_shown_url(u, d), _ft_missing_label(d)))
        base["pages"][lineno] = where
        # ★要旨の逐語は `urls` に、抜き書きは `all_urls` に当てる(★抜き書きの無い行は、それまでと同じ1組だけ)。
        groups = ([(urls, [(q, False) for q in qs])] if qs else []) + \
                 ([(all_urls, [(q, True) for q in nqs])] if nqs else [])
        counted = set()
        for g_urls, items in groups:
            docs = [evidence.get(u) for u in g_urls]
            docs = [d for d in docs if isinstance(d, dict)]
            texts = [d for d in docs if d.get("text")]
            g_paged = [by_url[u] for u in dict.fromkeys(g_urls) if u in by_url]
            if not texts:
                why = "/".join(sorted({d.get("state", "?") for d in docs})) or "取得結果に無い"
                # ★届かなかった本数は、同じ行で2度数えない(★抜き書きの当て先は要旨の当て先を含む)。
                #   ★数えるのはリンクの欄の URL だけ(★足した `.json` は数えない —— 申告の「届かなかった」は段階A と同じ物差し)。
                base["unreachable"] += sum(1 for u in g_urls if u in urls and u not in counted
                                           and isinstance(evidence.get(u), dict)
                                           and evidence[u].get("state") == "unreachable")
                counted.update(g_urls)
                for q, is_nk in items:
                    base["unmeasured"].append((lineno, _nk_label(q, is_nk), "本文が取れていない(%s)" % why))
                    if is_nk:
                        nk["unmeasured"] += 1
                continue
            counted.update(g_urls)
            body = {lv: " ".join(_ft_norm(d["text"], lv) for d in texts)
                    for lv, _n in FULLTEXT_LEVELS}
            prose = max(_ft_prose(d["text"]) for d in texts)
            title_hit = any(_ft_norm(t, 3) and _ft_norm(t, 3) in body[3] for t in titles)
            for q, is_nk in items:
                # ★✕ はここで立てる(★変異の道具の rule-hollow は、Result を作った関数の中の fail だけを規則のブロックと数える)。
                why_ng = _ft_judge_one(base, nk, lineno, q, is_nk, body, texts, prose, titles, title_hit, g_paged)
                if why_ng:
                    r.fail(lineno, why_ng)
    note_ok = ("段階C: 逐語 %d本中 在った %d(そのまま %d / 正規化して %d)"
               " / 無い %d / 測れなかった %d ※逐語の引用が無い行 %d行"
               % (base["quotes"], base["ok"], base["exact"], base["normalized"],
                  base["ng"], len(base["unmeasured"]), rows_no_quote)) + _nk_note(nk)
    note = note_ok.replace("測れなかった", "★未検査")
    if base["ng"]:
        r.note = note
        r.state_info["stageC"] = base
        return r
    if base["unmeasured"]:
        r.blocked(note + " —— **未検査が残っている。合格ではない。**")
        r.observe("missing_input", what="取れなかった本文", supplier="呼び出し", handed=True)
        r.state_info["stageC"] = base
        return r
    r.ok_note(note_ok)
    r.observe("clean", scanned=len(rows), targets=len(targets))
    r.state_info["stageC"] = base
    return r


def _nk_label(q, is_nk):
    """申告の「測れなかった」の1件に出す引用の書き方。★要旨の逐語はそれまでと同じ(そのまま)。"""
    return ("抜き書き「%s」" % q) if is_nk else q


def _nk_note(nk):
    """B-14 の文の後ろに足す、抜き書きの欄の数え。★欄が無ければ空(★それまでと1字も同じ)。"""
    if nk is None:
        return ""
    img = [ln for ln, _q in nk["image"]]
    return ("。★うち抜き書きの欄 %d本(在った %d / 無い %d / 測れなかった %d)"
            "・CiNii の書誌ページに足した .json %d本"
            "・★画像から書き写した %d本%sは照らしていない(止めない。確かめ役が頁の画像と照らす)"
            "・「」の対が閉じない %d行%s・区切りが %d字に満たない %d本%s"
            % (nk["quotes"], nk["ok"], nk["ng"], nk["unmeasured"], nk["json"],
               len(img), lineno_list(sorted(set(img))), len(nk["broken"]), lineno_list(nk["broken"]),
               NUKIGAKI_PIECE_MIN, len(nk["short"]), lineno_list(sorted(set(ln for ln, _q in nk["short"])))))


def _ft_judge_one(base, nk, lineno, q, is_nk, body, texts, prose, titles, title_hit, paged):
    """逐語(または抜き書き)1本を判定し、数えに足す。→ ✕ の文(★✕ でなければ None)

    ★2026-10-31 に `check_quote_presence` の中から切り出した(★要旨の逐語の判定は1字も変えていない)。
    ★抜き書き(`is_nk`)だけ、在るかを `nukigaki_found`(区切りは順に・負号の直後に当てない)で、★ページ1本ずつに見る
      (★つないだページの上で見ると、同じ本文が2本あるとき、順を入れ替えた区切りが通る)。
    """
    hit = None
    for lv, name in FULLTEXT_LEVELS:
        if is_nk:
            if any(nukigaki_found(q, _ft_norm(d["text"], lv), lv) for d in texts):
                hit = (lv, name)
                break
            continue
        qn = _ft_norm(q, lv)
        if qn and qn in body[lv]:
            hit = (lv, name)
            break
    lab = _nk_label(q, is_nk)
    if hit:
        base["ok"] += 1
        if is_nk:
            nk["ok"] += 1
        if hit[0] == 0:
            base["exact"] += 1
        else:
            base["normalized"] += 1
        # ★どのページで当たったか(★同じ正規化の段で、1本ずつ当て直す)。
        #   ★どの1本にも当たらない(=つないだ境目で当たった)なら判定不能に数える。
        if is_nk:
            kinds = [kd for kd, d in paged if nukigaki_found(q, _ft_norm(d["text"], hit[0]), hit[0])]
        else:
            qh = _ft_norm(q, hit[0])
            kinds = [kd for kd, d in paged if qh in _ft_norm(d["text"], hit[0])]
        base["ok_by_kind"][_ft_best_kind(kinds)] += 1
        return

    def unmeasured(why):
        base["unmeasured"].append((lineno, lab, why))
        if is_nk:
            nk["unmeasured"] += 1

    if prose < FULLTEXT_PROSE_MIN:
        base["no_content"] += 1
        unmeasured("ページが散文を渡していない(和文の連なりの最長 %d < %d)" % (prose, FULLTEXT_PROSE_MIN))
        return
    if not titles:
        base["no_control"] += 1
        unmeasured("対照が置けない(書誌欄に題名の鍵括弧が無い)")
        return
    if not title_hit:
        base["no_content"] += 1
        unmeasured("題名すらページに無い(このページはこの文献の中身を渡していない)")
        return
    # 🔴★★**本文のページに1本も当てられなかった外れは ✕ にしない**(2026-09-24・起票 `KICKOFF-stagec-nise-batsu.md`)。
    #   ★現物: 本文にだけ在る本物の引用が、抄録付きの記事ページや DOI のページに当てただけで ✕ になった(★偽の違反。
    #     `40-report-format.md` §2 の「実在する記述に対して『無い』」)。★本文と数えないページ(案内ページ・判定不能)に
    #     無いことは、原典に無いことを言い切らない(★ユーザー裁定 2026-09-24 の案 (b))。
    #   ⇒ ★▲(測れなかった)に置き、理由を名指しする。★合格にはしない(exit 3)。
    #   ★**本文のページが1本でも在れば ✕ のまま**(★`_ft_best_kind` の順= 本文 → 判定不能 → 案内ページ)。
    best = _ft_best_kind([kd for kd, _d in paged])
    if best != FULLTEXT_KIND_BODY:
        key, why_nb = FULLTEXT_NOBODY[best]
        base[key] += 1
        unmeasured(why_nb)
        return
    if is_nk:
        nk["ng"] += 1
    base["ng"] += 1
    base["ng_by_kind"][best] += 1
    if is_nk:
        return ("抜き書きが原典に無い: 「%s」 —— "
                "★題名は当たり、ページも散文を渡している(最長 %d)のに、"
                "この抜き書きだけが無い(★外側の「」を1本として・「…」の区切りは順に・数で始まる区切りは"
                "負号の直後に当てずに照らした)" % (q[:70], prose))
    return ("逐語の引用が原典に無い: 「%s」 —— "
            "★題名は当たり、ページも散文を渡している(最長 %d)のに、"
            "この引用だけが無い" % (q[:70], prose))


def _ft_progress_line(i, n, url, rec):
    """取得の途中経過の1行。→ str

    ★取れなかった理由(`why`)が在れば、行の末尾に名乗る(2026-09-28・起票 `KICKOFF-pdf-pymupdf.md`)。
      ★理由は取得結果の JSON にしか残っていなかった —— ★PyMuPDF の無い環境では PDF が全部「テキストにできない」に
      数えられるが、★画面からは画像 PDF と見分けられなかった。★理由の無い行は、それまでと1字も変わらない。
    """
    return ("  [%3d/%d] %-11s %-5s len=%-6d 和文の連なり=%-4d %s%s"
            % (i, n, rec.get("state"), rec.get("how", "-"), rec.get("len", 0), rec.get("prose", 0),
               url[:70], ("  理由: %s" % rec["why"]) if rec.get("why") else ""))


def fetch_and_save_fulltext(args):
    """`--fetch-fulltext`: 対象を集めて取り、取得結果を保存する。→ 終了コード(0 なら検査へ)

    🔴★★**集める述語を書き起こさない。**★判定と同じ経路を1回空走りさせる(★段階A・B と同じ筋)。
    """
    import time
    del FULLTEXT_WANTED[:]
    for path in args.files:
        if os.path.isfile(path):
            inspect_file(path, args)
    urls = sorted(set(FULLTEXT_WANTED))
    print("★段階C: 本文の取得を始める —— 対象 %d本の URL(重複を除いた数)/ 待ち時間の上限 %g秒"
          % (len(urls), args.fulltext_timeout))
    probe = fulltext_probe_fn()
    if probe is not fulltext_probe:
        print("  ★★注意: 取得の口が差し替えられている(%s)。★この結果は本物の取得ではない。"
              % getattr(probe, "__name__", repr(probe)))
    got = {}
    for i, url in enumerate(urls, 1):
        state, rec = probe(url, args.fulltext_timeout)
        rec = dict(rec or {})
        rec["state"] = state
        rec["len"] = len(rec.get("text") or "")
        rec["prose"] = _ft_prose(rec.get("text") or "")
        got[url] = rec
        print(_ft_progress_line(i, len(urls), url, rec))
    try:
        fulltext_evidence_save(args.fulltext, got, time.strftime("%Y-%m-%dT%H:%M:%S"))
    except OSError as e:
        print("★★段階C: 取得結果を保存できなかった(%s): %s"
              % (e.__class__.__name__, args.fulltext), file=sys.stderr)
        print("★**保存できない取得は、次の走行で再現できない。**★黙って検査へ進まない。",
              file=sys.stderr)
        return 2
    n = {}
    for rec in got.values():
        n[rec["state"]] = n.get(rec["state"], 0) + 1
    print("★段階C: 取得を終えた —— 取れた %d / 短すぎる %d / テキストにできない %d / "
          "★届かない %d  → %s"
          % (n.get("ok", 0), n.get("thin", 0), n.get("no-text", 0), n.get("unreachable", 0),
             args.fulltext))
    print()
    return 0


def print_stage_c_embed_block(kind, results):
    """★段階C-2 —— **貼るための申告文**と、同梱の検査が見ていない範囲。

    🔴★★**0件でも必ず出す。**★出さないと「0件だった」と「申告し忘れた」が区別できない
      (ユーザー裁定125)。★**段の側が測れていない走行でも出す** —— そこでこそ
      「走らせていない」と名乗る囲みが要る。
    🔴★★**囲みは字下げせずに出す。**★人が選んで写すからである(★段階A-3・段階B-2 と同じ)。
    """
    print("  [★事実の関門 段階C —— 下の囲みを**納品物に同梱**し、チャット本文にも写すこと"
          "(★違反0でも貼る)]")
    print(STAGE_C_FENCE_OPEN)
    for line in stage_c_declaration(kind, results):
        print(line)
    print(STAGE_A_FENCES[0])
    # ★★`00-principles.md` §12 —— **同梱の検査が見ていない範囲を、走行のたびに件数で出す。**
    emb = next((x for x in results
                if x.rule_id == STAGE_C_EMBED_RULES.get(kind)), None)
    esi = emb.state_info if emb is not None else {}
    if "scanned" in esi:
        print("  ・★同梱の検査が読んだ範囲: 納品物 %d行のうち 囲み %d行"
              "(★外側 %d行は、この規則は見ていない)"
              % (esi["scanned"], esi.get("inner", 0), esi["scanned"] - esi.get("inner", 0)))
    else:
        print("  ・★同梱の検査が読んだ範囲: 測れていない(規則が実行できていない)")
    print("  ・★段階Cの同梱の囲み: %s個" % esi.get("blocks", "測れていない"))
    print("  ・★**チャットに現に貼ったかは、いまも1件も見ていない**"
          "(★母数は将来の納品の回数であり、数えられない)")


def print_fulltext_disclosure(kind, results):
    """★段階Cの【見ていない範囲】を、走行のたびに件数で画面に出す(`00` §12)。"""
    if kind not in FULLTEXT_RULES:
        return
    print("  [★事実の関門 段階C —— 引いた逐語が、原典に現に在るか]")
    r = next((x for x in results if x.rule_id == FULLTEXT_RULES[kind]), None)
    si = (r.state_info.get("stageC") if r is not None else None) or {}
    if not si:
        print("  ・★測れていない(規則が実行できていない)")
        # 🔴★**ここで返らない。**★測れていない走行でこそ、囲みが要る(→ 段階A-3 の受け皿と同じ)。
        print_stage_c_embed_block(kind, results)
        print()
        return
    print("  ・★逐語の引用: %d本(在った %d / 無い %d / 測れなかった %d)"
          % (si.get("quotes", 0), si.get("ok", 0), si.get("ng", 0),
             len(si.get("unmeasured", ()))))
    print("  ・★そのうち **そのまま当たった %d / 正規化して当たった %d** —— "
          "★**正規化した分は「一字一句そのままではなかった」という事実である**"
          % (si.get("exact", 0), si.get("normalized", 0)))
    print("  ・★①逐語の引用が無い行: %d行 —— **そもそも照合するものが無い**"
          % si.get("rows_no_quote", 0))
    print("  ・★②届かなかった: %d本 —— ★**段階A が見ているのはここだけである**"
          % si.get("unreachable", 0))
    print("  ・★③届いたが中身を渡していない: %d本 —— ★**②とは別である。**"
          "★**実測ではこちらのほうが多い**" % si.get("no_content", 0))
    print("  ・★④対照が置けない(書誌欄に題名の鍵括弧が無い): %d本" % si.get("no_control", 0))
    for line in FULLTEXT_UNSEEN:
        print("  ・★%s" % line)
    print("  ・★**この段の合格は「0件」ではない。**"
          "★**「取れたものについて0件」＋【取れなかった件数】がセットである**")
    print_stage_c_embed_block(kind, results)
    print()


# ================================================================================
# 段0の足場(受理層・7コンストラクタ・勘定)
# --------------------------------------------------------------------------------
# **ここから下の段0ブロックは、どの規則の判定にも接続していない。**
# 出力するのは `--list-profile` / `--accounting` を明示したときだけである。
# ★2026-10-05(起票 `KICKOFF-juri-tsuzuki.md` §1-4・ユーザー裁定 問い4 (ア))から、受理層の【未対応の記録】だけは
#   普段の点検でも毎回画面に出す(`print_admit_record`)。★判定には接続しない(★合否・終了コードは変わらない)。
#   ★未対応の記録のうち3種(閉じていない囲み・全角の縦棒・文字コード)は、uradori・bunken では規則が別に判定している
#   (U-24・B-18 / U-25・B-19 / U-26・B-20)。★記録そのものを規則が読んでいるのではない。
# 「281項目が全緑のまま」であることが、この足場が不活性であることの証拠になる
# (DESIGN.md §6 段0)。
#
# なぜ足場が要るのか(DESIGN.md §0 の背骨):
#   Result の5状態はすべて**規則の結論**であり、**受理層の観測**を表す型が無い。
#   「読めなかった」を置く場所が無いので、認識の失敗はその場で最寄りの結論へ丸められ、
#   丸めた事実は出力に残らない。**列挙を増やす修正が効かないのは、列挙の外側を記録する
#   器が無いためである。**——器を先に作る。列挙は器の中身にすぎない。
# ================================================================================

# ---- 受理プロファイル(柱1) -------------------------------------------------
# 〈条項ID / 対象種別 / 受理する形 / 未対応時の記録名 / 原典の【控え】または「機械側の都合」/ 逐語の鍵〉
# ★「機械側の都合」の条項は**納品物を禁じない**。「当チェッカーはこの形を読めない」という
#   能力の開示にとどまるので、規則表 deliverable-rules.md の原則1(新しい品質基準を
#   発明しない)に抵触しない。
#
# ★★2026-08-18(申-9): **第5要素は【生成物】になった。手で書き換えないこと。**
#   `python sync_rules_md.py` が第6要素の鍵の逐語から導出して書き戻す(`--check` で差分だけ見られる)。
#   第6要素が `None` の条項は原典を名乗らないので**生成の対象外**である。
#
#   ★**なぜこの工事が要ったか**: 第5要素は導入時(段0)から手書きの `file:line` で、
#     **6個とも現に腐っていた**(名乗っていた位置にはもう規定が無かった)。それでも
#     **1つも赤くならなかった** —— 段4で赤くなった控えには照合する常設テストがあったのに、
#     ここには照合が無かったからである(fail-loud と fail-open の差)。
#   ★**なぜ控えを消さないか**: `origin_at()` と同じ理由である —— F-6 が「原典に到達できない
#     環境でも検査は動く」ことを保証しており、そこで空を返すと道具が死ぬ。**消さずに作り直せるようにする。**
#   ★**控えを持つ限り、控えを照合する項目を必ず併せて置く**(常設テスト F-14)。
ADMIT_PROFILE = [
    ("P-01", "md",   "GFM のパイプ表(見出し行+区切り行+同数の列を持つ本体行)",
     "table_unreadable", "run-uradori/references/daicho-format.md:23", "AP:P-01:台帳本体は表で書く"),
    ("P-02", "md",   "半角の縦棒「|」を区切りに使った表",
     "fullwidth_pipe", "run-uradori/references/daicho-format.md:26, run-bunken-daicho/references/daicho-format.md:76",
     "AP:P-02:表の縦棒に全角の「｜」を使わない"),
    ("P-03", "md",   "``` または ~~~ で**閉じた**フェンス付きコードブロック",
     "unclosed_fence", "run-uradori/references/daicho-format.md:4, run-bunken-daicho/references/daicho-format.md:4",
     "AP:P-03:コードの囲みは必ず閉じる"),
    ("P-04", "md",   "行頭 # 〜 #### の ATX 見出し",
     "heading_unreadable", "run-uradori/references/daicho-format.md:133-138", "AP:P-04:必須の節は見出しで区切る"),
    ("P-05", "md",   "「キー: 値」形式のヘッダーブロック(冒頭40行)",
     "header_unreadable", "run-uradori/references/daicho-format.md:7-15", "U-2"),
    ("P-06", "md",   "1つの列が高々1つの必須概念に割り当たる表(単射)",
     "ambiguous_column", "run-uradori/references/daicho-format.md:42, run-bunken-daicho/references/daicho-format.md:94",
     "AP:P-06:1つの物理列を2つの必須概念に兼用しない"),
    ("P-07", "html", "html.parser が最後まで消費できる HTML",
     "html_parse_error", "run-html-visualizer/SKILL.md:98", "H-2"),
    ("P-08", "html", "開始タグと終了タグが対応する主要コンテナ",
     "unbalanced_tag", "run-html-visualizer/SKILL.md:98", "H-2"),
    ("P-09", "html", "属性値に現れる資源辺(src/href/data/@import/url())",
     "resource_edge_unreadable",
     "run-html-visualizer/SKILL.md:74-78, run-html-visualizer/SKILL.md:79, run-html-visualizer/SKILL.md:97",
     "H-1"),
    ("P-10", "any",  "UTF-8 として読める有限のファイル",
     "encoding_error", "run-uradori/references/daicho-format.md:5, run-bunken-daicho/references/daicho-format.md:5",
     "AP:P-10:台帳は UTF-8 で保存する"),
]

# ★★契約表の【任意欄】の宣言(2026-10-05・起票 `KICKOFF-juri-tsuzuki.md` §1-0)。〈契約表の名前: 任意欄の列の添字〉
#   ★受理プロファイルの第6要素(原典の鍵)は None を取れる —— `admit_origin` は None のとき控え(第5要素)をそのまま出す。
#   ★変異の道具は任意欄を「今の値に None と文字列が混在する列」で見つけていたので、全部の条項が鍵を持った日に
#     列が任意欄と見えなくなり、「原典を名乗らなくする」変異が黙って母集合から消えた(★担当27-17 が現物で踏んだ)。
#   ⇒ ★**値の側から推さず、表の約束として宣言する。**★道具はこの dict を名前ではなく形で読む
#     (`mutation_harness.optional_column_declarations`)。★常設テスト F-26 が、宣言とは別の道で原典の鍵の列を見つけ、
#     それが狙われていることを毎回確かめる(★宣言を消したら鳴る)。
CONTRACT_OPTIONAL_COLUMNS = {"ADMIT_PROFILE": 5}


def admit_origin(clause):
    """受理プロファイルの1条項が名乗る原典を**逐語から導出する**(申-9)。

    ★表に出すのは**導出結果**である。控え(第5要素)が現れるのは原典に到達できない環境だけで、
      その環境で道具が死なないことは F-6 が保証している(だから控えは消せない)。
    ★鍵(第6要素)を持たない条項は原典を名乗らない(「機械側の都合」)ので、第5要素をそのまま返す。
    """
    key = clause[5]
    return clause[4] if key is None else derive_origin(key, clause[4])[0]


def admit_rows():
    """受理プロファイルを〈条項ID・対象種別・受理する形・記録名・原典〉で返す(原典は導出結果)。"""
    return [(c[0], c[1], c[2], c[3], admit_origin(c)) for c in ADMIT_PROFILE]

# 未対応の記録名 → 段1以降でどの状態へ写すかの**方針表**。
# ★規則の実装に散らさない(散らすと、次に足される未対応がまた自由文になる)。
# 段0では参照するだけで、どの規則にも接続していない。
# ★2026-10-05(C-5): `unclosed_fence` の行と同じ扱い(partial / 納品物)を、規則 U-24・B-18 が持つ(`check_fence_closed`)。
#   ★この表そのものは、いまも規則からは読まれない。★食い違えば常設テスト LD-107 が鳴る。
UNSUPPORTED_POLICY = {
    "table_unreadable":        ("partial",       "納品物"),
    "fullwidth_pipe":          ("partial",       "納品物"),
    "unclosed_fence":          ("partial",       "納品物"),
    "heading_unreadable":      ("partial",       "納品物"),
    "header_unreadable":       ("partial",       "納品物"),
    # ★2026-10-05(ユーザー裁定 問い2 (イ)): 「一部しか読めなかった」→「必要な列が無い(直すのは書き手)」。★bunken の
    #   「必須の列が無い」の判定(`bunken_missing_column_state`)と同じ名前にそろえた。★記号・直す人・合否は変わらない。
    "ambiguous_column":        ("missing_input", "納品物"),
    "html_parse_error":        ("partial",       "納品物"),
    "unbalanced_tag":          ("partial",       "納品物"),
    "resource_edge_unreadable": ("needs_human",  "人間"),
    # ★2026-10-05(ユーザー裁定 問い3 (ア)): 「呼び出し」→「納品物」。★説明書に「台帳は UTF-8 で保存する」が入ったので、
    #   読めない字は書き手が保存し直せば直る。★規則 U-26・B-20 が同じ扱い(partial / 納品物)を持つ(★食い違えば常設テストが鳴る)。
    #   ★R系・html には説明書の行が無く、判定にも繋いでいない(★起票「その2つは今のまま変えない」)。
    "encoding_error":          ("partial",       "納品物"),
}


class Unsupported:
    """受理層が「モデルへ写せなかった」と記録する構文。**第一級の記録**であって注記ではない。

    既定が閉じている(G6)ので、条項に無い構文の行き先は「合格」ではなく「未対応」になる。
    """

    __slots__ = ("construct", "lineno", "detail", "clause_id")

    def __init__(self, construct, lineno, detail, clause_id):
        self.construct = construct
        self.lineno = lineno
        self.detail = detail
        self.clause_id = clause_id

    def as_tuple(self):
        return (self.construct, self.lineno, self.detail, self.clause_id)

    def __repr__(self):
        return "Unsupported(%s, L%s, %s, %s)" % self.as_tuple()


class Document:
    """受理層の観測結果。**規則の結論を1つも含まない。**

    G5: 認識した表・行・セル・見出し・タグの数がすべて残る。
    規則が読んだ物理列と概念の対応表(`self.mapping`)も残す。
    """

    def __init__(self, kind, raw):
        self.kind = kind
        self.raw = raw
        self.raw_lines = raw.splitlines()
        self.body_lines = []          # フェンスを空行に置換した行(既存 strip_code_fences と同じ)
        self.tables = []              # parse_md_tables の結果
        self.headings = []            # (lineno, level, text)
        self.fence_lines = set()      # フェンスの内側+フェンス記号の行番号
        self.unclosed_fence = None
        self.html = {}                # タグ数・解析到達位置など
        self.unsupported = []
        self.mapping = {}             # {表index: {概念: 物理列index}} —— 規則が読んだ対応表
        self.counts = {}              # G5 の数

    def note_unsupported(self, construct, lineno, detail, clause_id):
        self.unsupported.append(Unsupported(construct, lineno, detail, clause_id))

    def summary(self):
        return dict(self.counts)


def _scan_fences(lines):
    """フェンスの行番号集合と、閉じ忘れの有無を返す。

    ★除外理由 E1 は逐語で「**閉じた**フェンスの内側」である(DESIGN 柱3)。
    閉じ忘れを黙って「フェンスの内側」に数えると、説明のつかない除外が表に出なくなる。
    """
    inside, opened_at, marks = set(), None, set()
    for i, ln in enumerate(lines):
        if re.match(r"^\s*(```|~~~)", ln):
            marks.add(i + 1)
            if opened_at is None:
                opened_at = i + 1
            else:
                for j in range(opened_at, i + 1):
                    inside.add(j)
                opened_at = None
    return inside, marks, opened_at


def admit(raw, kind, data=None):
    """受理層。`(Document, [Unsupported])` を返す。**規則はここを通った物だけを読む**(段1以降)。

    段0では呼ばれるのは `--accounting` / `--list-profile` のときだけで、判定には接続しない。
    ★2026-10-05(起票 `KICKOFF-juri-tsuzuki.md` §1-4)から、普段の点検でも毎回呼ぶ(`print_admit_record`)——
      ★記録を画面に並べるだけで、判定には接続しない(★合否・終了コードは変わらない)。
    ★data= ファイルのバイト(★渡されたときだけ、UTF-8 として読めない行を `encoding_error` として記録する)。
    """
    doc = Document(kind, raw)
    lines = doc.raw_lines
    doc.body_lines = strip_code_fences(lines)

    inside, marks, unclosed = _scan_fences(lines)
    doc.fence_lines = inside | marks
    doc.unclosed_fence = unclosed
    if unclosed is not None:
        doc.note_unsupported("unclosed_fence", unclosed,
                             "L%d で開いたフェンスが閉じていない" % unclosed, "P-03")

    # ★文字コード(2026-10-05・起票 `KICKOFF-juri-tsuzuki.md`): バイトが渡されたときだけ記録する
    #   (★渡らなければ、読み込みで生じた置き換えの字か元から書いてある字かを区別できない)。★P-10 は全種別。
    if data is not None:
        for ln in undecodable_lines(data)[0]:
            doc.note_unsupported("encoding_error", ln, "UTF-8 として読めない字を含む行", "P-10")

    if kind == "html":
        doc.html = _admit_html(doc, raw)
        doc.counts = {"行": len(lines), "タグ(パーサー)": doc.html.get("tags_parser", 0),
                      "タグ(外形)": doc.html.get("tags_shape", 0),
                      "未対応": len(doc.unsupported)}
        return doc, doc.unsupported

    # --- Markdown 系 ---
    for i, ln in enumerate(doc.body_lines):
        m = re.match(r"^(#{1,6})\s+(.*)$", ln.strip())
        if m:
            doc.headings.append((i + 1, len(m.group(1)), m.group(2).strip()))
    doc.tables = parse_md_tables(doc.body_lines)

    # ★2026-10-05(起票 `KICKOFF-juri-tsuzuki.md`): 見分けを規則 U-25・B-19 と同じ `fullwidth_table_rows` にそろえた。
    #   ★旧= 「1行に全角の縦棒が2つ以上」(★普通の文の「｜」まで記録していた)。★記録は判定に使っていない(★合否は変わらない)。
    zen, follow = fullwidth_table_rows(doc.body_lines)
    for ln in zen:
        doc.note_unsupported("fullwidth_pipe", ln,
                             "全角の縦棒「｜」で書いた表の行(表として読めなかった)", "P-02")
    for ln in follow:
        doc.note_unsupported("fullwidth_pipe", ln,
                             "全角の行で表が切れ、表の行として読まれなかった行", "P-02")

    ncells = sum(len(t["header"]) + sum(len(rc) for _l, rc in t["rows"]) for t in doc.tables)
    doc.counts = {"行": len(lines), "表": len(doc.tables),
                  "表の行": sum(len(t["rows"]) for t in doc.tables),
                  "セル": ncells, "見出し": len(doc.headings),
                  "未対応": len(doc.unsupported)}
    return doc, doc.unsupported


class _AdmitHtml(HTMLParser):
    """受理層側の HTML 走査。**判定は一切しない。**数えるだけ。"""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags = 0
        self.last_pos = (1, 0)

    def handle_starttag(self, tag, attrs):
        self.tags += 1
        self.last_pos = self.getpos()

    def handle_startendtag(self, tag, attrs):
        self.tags += 1
        self.last_pos = self.getpos()

    def handle_endtag(self, tag):
        self.last_pos = self.getpos()

    def handle_data(self, data):
        self.last_pos = self.getpos()


def _admit_html(doc, raw):
    p = _AdmitHtml()
    err = None
    try:
        p.feed(raw)
        p.close()
    except Exception as e:                      # noqa: BLE001 — 受理層は落ちない
        err = str(e)
        doc.note_unsupported("html_parse_error", p.last_pos[0], err, "P-07")
    # ★二挺の物差し。外形側は**愚直に保つ**(パーサーと同じ誤読を共有した瞬間、この
    #   物差しは何も検出しなくなる=DESIGN 柱3 層2 の要)。規則は「< に英字が続けば開始タグ」だけ。
    shape = len(re.findall(r"<[A-Za-z][^>]*>", raw))
    nlines = len(doc.raw_lines)
    return {"tags_parser": p.tags, "tags_shape": shape, "parse_error": err,
            "reached_line": p.last_pos[0], "total_lines": nlines,
            "reached_all": p.last_pos[0] >= nlines}


def list_profile():
    """受理プロファイルを機械可読で出力する(柱1)。"""
    print("# 受理プロファイル(check_deliverable.py の ADMIT_PROFILE 定義)")
    print("# 条項ID\t対象種別\t受理する形\t未対応時の記録名\t原典 file:line または機械側の都合")
    # ★原典は**導出結果**を出す(控えをそのまま出さない。控えは原典に到達できない環境の予備である)
    for cid, kind, form, name, origin in admit_rows():
        print("%s\t%s\t%s\t%s\t%s" % (cid, kind, form, name, origin))
    print("")
    print("# 未対応 → 状態の方針表(★規則の実装に散らさない)")
    print("# 記録名\t状態\t責任の所在")
    for name, (state, who) in UNSUPPORTED_POLICY.items():
        print("%s\t%s\t%s" % (name, state, who))


# ---- 段2: 表の役を「得点」から「述語」へ / 割当を単射に(柱1) -----------------
# ★いまの穴: 台帳本体を「必須列を最も多く満たす表」で選んでいる(得点最大での代用)。
#   得点は表の出現順と列の並び順に左右され、必須概念を1つ欠いた表でも台帳本体を名乗れる。
#   さらに find_col は「先に見つかった列」を返すので、**1つの物理列が2つの概念を兼ねる**。
#
# ★段2で変えるのは次の3点だけであり、どれも「読む対象を正しくする」話である:
#   1. 役の述語化 —— 台帳本体であるのは「必須概念のすべてに単射な列割当が存在する」ときに限る
#   2. 割当の単射化 —— 各列は高々1概念。定まらなければ「あり」と数えない(G8)
#   3. 複数表の結合 —— 台帳本体が複数あれば全部を結合する(bunken にも広げる)
def _norm2(s):
    """正規化後の比較用。全半角・大小・空白の違いを畳む。"""
    import unicodedata
    return unicodedata.normalize("NFKC", s).lower().replace(" ", "")


def match_rank(h, aliases):
    """列見出し h と概念の別名群との一致の**順位**。小さいほど強い。一致しなければ None。

    〈0 完全一致 > 1 正規化後完全一致 > 2 前方一致 > 3 部分一致〉
    """
    best = None
    for a in aliases:
        if h == a:
            r = 0
        elif _norm2(h) == _norm2(a):
            r = 1
        elif h.startswith(a):
            r = 2
        elif a in h:
            r = 3
        else:
            continue
        best = r if best is None else min(best, r)
    return best


def assign_columns(header, cols):
    """概念 → 物理列の**単射**な割当を解く。返り値: ({概念: 列index}, [解けなかった記録])

    ★G8: 割当は単射である。定まらない場合は「あり」と数えない。
    ★強い一致から順に確定させ、**確定した列は他の概念に回さない**。
      同順位で奪い合いになった概念は、どちらにも割り当てない(黙って片方に倒さない)。
    """
    assigned, taken, notes = {}, set(), []
    for rank in range(4):
        progress = True
        while progress:
            progress = False
            cand = {}
            for c, aliases in cols.items():
                if c in assigned:
                    continue
                v = [i for i, h in enumerate(header)
                     if i not in taken and match_rank(h, aliases) == rank]
                if v:
                    cand[c] = v
            singles = {c: v[0] for c, v in cand.items() if len(v) == 1}
            wanted = {}
            for c, i in singles.items():
                wanted.setdefault(i, []).append(c)
            for i, cs in sorted(wanted.items()):
                if len(cs) == 1:
                    assigned[cs[0]] = i
                    taken.add(i)
                    progress = True
        # この順位で残った競合を記録する(黙って捨てない)
        for c, aliases in cols.items():
            if c in assigned:
                continue
            v = [i for i, h in enumerate(header)
                 if i not in taken and match_rank(h, aliases) == rank]
            if len(v) > 1:
                notes.append((c, "順位%d の候補が %d 列あり一意に定まらない: %s"
                              % (rank, len(v), "・".join(header[i] for i in v))))
            elif len(v) == 1:
                notes.append((c, "順位%d で列「%s」を他の概念と奪い合っている" % (rank, header[v[0]])))
    return assigned, notes


def is_ledger_body(header, cols, must_have_keys):
    """★役の述語。**表の出現順にも列の並び順にも依存しない**(G7)。

    台帳本体であるのは「必須概念のすべてに単射な列割当が存在する」ときに限る。
    """
    a, _notes = assign_columns(header, cols)
    return all(k in a for k in must_have_keys)


def collect_ledger_tables(tables, cols, must_have_keys, doc=None):
    """台帳本体を**述語で選び、全部を結合する**。

    返り値: (primary_header, rows, hline, 結合した表の数, [役が確定しない表の記録])

    ★得点最大での代用をやめる。台帳本体が0個なら「未対応」であり、
      **必須概念を1つ欠いた表を台帳本体の代わりに使わない。**
    ★必須概念を持つが述語を満たさない表は「役が確定しない表」として記録する
      (これまでは黙って捨てていた)。
    """
    bodies = [t for t in tables if is_ledger_body(t["header"], cols, must_have_keys)]
    undecided = []
    for t in tables:
        if t in bodies:
            continue
        a, notes = assign_columns(t["header"], cols)
        hit = [k for k in must_have_keys if k in a]
        if hit:                                  # 必須概念を持つのに役が確定しなかった表
            lack = [k for k in must_have_keys if k not in a]
            undecided.append({"hline": t["hline"], "have": hit, "lack": lack, "notes": notes})
            if doc is not None:
                doc.note_unsupported(
                    "ambiguous_column", t["hline"],
                    "必須概念 %s は割り当てられたが %s が定まらず、台帳本体の役が確定しない"
                    % ("・".join(hit), "・".join(lack)), "P-06")
    if not bodies:
        return None, [], None, 0, undecided

    primary = bodies[0]
    header = primary["header"]
    pidx, _n = assign_columns(header, cols)
    width = len(header)
    rows = []
    for t in bodies:
        tidx, _n2 = assign_columns(t["header"], cols)
        for lineno, rc in t["rows"]:
            if t is primary:
                rows.append((lineno, rc))
                continue
            newrow = [""] * width
            for k, pi in pidx.items():
                if tidx.get(k) is not None:
                    newrow[pi] = cell(rc, tidx[k])
            rows.append((lineno, newrow))
    rows.sort(key=lambda x: x[0])
    return header, rows, primary["hline"], len(bodies), undecided


# ---- 7コンストラクタ(柱2) ---------------------------------------------------
# ★要点は引数である。「原典を書けない除外は書けない」「母集合を数えていなければ clean を
#   呼べない」。**後から規則を足す者も、この制約から逃げられない。**
#   これが「列挙を増やす修正」との決定的な違いである。
#
# 7状態 → 既存5状態(記号)への写像。**段0〜2では記号を1つも動かさない。**
STATE_TO_STATUS = {
    "not_applicable": "skip",     # ― 規定によりこの納品物には適用されない
    "clean":          "ok",       # ○ 対象はあるが違反がない
    "violation":      "ng",       # ✕ 違反
    "partial":        "blocked",  # ▲ 入力を一部しか読めなかった
    "missing_input":  "blocked",  # ▲ 検査に必要な情報がない
    "crashed":        "blocked",  # ▲ 検査処理が失敗した
    "needs_human":    "gray",     # △ 人間の判断が必要
}
# 責任の所在。★「▲かどうか」ではなく「**誰が直せるか**」で門番を分ける(DESIGN 柱2 の中心)。
# ★★**この表が唯一の正本である。**`responsibility()` はここを引くだけで、写像を持たない。
#   ★値 `None` は「**責任は supplier 引数で決まる**」という宣言であり、欠落ではない。
#   ⇒ 責任の分類を直す人は**ここだけ**を直せばよく、直せば判定が現に動く
#     (2026-08-21 までは動かなかった。この表は誰からも読まれていなかった)。
#   ★この表を書き写して別の場所で判定しないこと。常設テスト E-19 が
#     「表が現に読まれているか」を1マスずつ壊して確かめている。
STATE_RESPONSIBILITY = {
    "not_applicable": "規定", "clean": "—", "violation": "納品物",
    "partial": "納品物", "missing_input": None,      # supplier 引数で決まる
    "crashed": "チェッカー", "needs_human": "人間",
}
SUPPLIERS = ("納品物", "呼び出し", "チェッカー", "人間")
ORIGIN_RE = re.compile(r"[\w./\\-]+\.(?:md|py):\d+(?:[-,]\d+)*")

# ★★「まだ検査が終わっていない」状態。**上の表から導く**(書き写さない)——
#   `STATE_TO_STATUS` が ▲ へ写す3つと同一である。⇒ 表を1マス直せば終了コードが現に動く。
UNEXECUTED_STATES = tuple(s for s, st in sorted(STATE_TO_STATUS.items()) if st == "blocked")


def unexecuted(results):
    """★**記号ではなく状態**で「検査が終わっていない項目」を拾う。終了コード3の唯一の母数。

    ★★由来(2026-08-23・外部レビュー第2次の指摘を現物で再現)——
      `skip_as` は段1の設計どおり**記号を「―」に据え置いたまま7状態だけを併せて記録する**。
      ★★註に `skip_as` と丸括弧を**続けて**書かないこと —— `coverage_skipas.py` の
        **旧述語は生の正規表現**(その関数名の直後に丸括弧、を字面で探す)なので、
        註の行まで「地点」として拾ってしまい、AST で数える新述語との差が
        **「★★退行: 旧述語の地点を 1 件落とした」**として出る(実測。中身は註1行だった)。
        ★旧述語は**片道の網の対照**である。こちらを緩めず、註の書き方のほうを合わせる。
        ★ここに正規表現そのものを書くのもやめた(逆斜線が SyntaxWarning になる)。
      判定を繋いだ段3以降が拾ったのは `check_kanmon` の `latent`、すなわち
      **責任=納品物 の潜在分だけ**であり、残りは**記号が「―」であるという理由だけで
      終了コードから消えていた**。
      実例: 本文が `<sup>1,2</sup>` の原稿で、R-2 自身が画面に
      「読めなかったのは本スクリプトの側である(責任=チェッカー)」と出しているのに、
      R-0 は「検査不能の項目なし」と表示し、**終了コードは 0** だった。
    ★これは `DESIGN.md` G4 の逐語「**終了コード0は「違反0 かつ 未実行0」のときだけ出る**」に反する。
    ★`DESIGN.md` 柱2 の表は、責任=**呼び出し**/**チェッカー**/**規則未実装(人間)** の3行とも
      「違反にしない。★**ただし ▲ は残るので終了コードは 3 になる(合格ではない)**」で一貫している。
      ⇒ 2026-08-20 の裁定で**前半(違反にしない)は実装された**が、
        **後半(▲ が残る=終了コードに出る)が `skip_as` 経路だけ欠けていた。**
        この関数はその欠けた半分を埋めるものであって、新しい基準ではない。
    ★★**和(union)である。落とすものは1つも無い。**
      原典喪失は `blocked()` の直後に `observe("needs_human")` を呼ぶので
      **status は ▲ なのに state は `needs_human`** である。状態だけで数えると
      **いま出ている exit 3 が消える**(fail-open の逆流)。常設テスト G-11(3)(4) がこの形を固定している。
    ★`needs_human` を状態の側から数えないのは**意図した保留**である ——
      `DESIGN.md` は §4「スクリプトがあるとき **△(要目視)**。終了コードに影響させない」と
      柱2「規則未実装(H-6)… ▲ は残るので終了コードは 3」の**両方**を書いており、
      △ 一般を終了コードへ繋ぐかは原典が決めていない。**決まっていないことは実装しない。**
    """
    return [r for r in results
            if r.status == "blocked" or r.state_guess() in UNEXECUTED_STATES]


def _mk(rule_id, state, note, **info):
    title, origin = rule_meta(rule_id)
    r = Result(rule_id, title, origin)
    r.status = STATE_TO_STATUS[state]
    r.state = state
    r.state_info = info
    r.note = note
    return r


def not_applicable(rule_id, origin, reason):
    """規定によりこの納品物には適用されない(―)。★**原典 file:line が必須。**

    G3: 原典を書けない除外は**実装上そもそも書けない**。
    """
    if not origin or not ORIGIN_RE.search(str(origin)):
        raise ValueError(
            "not_applicable には原典の file:line が要る(規定による対象外を名乗る以上、"
            "その規定の在処を書けなければならない): rule=%s origin=%r" % (rule_id, origin))
    return _mk(rule_id, "not_applicable", "%s(規定: %s)" % (reason, origin), origin_cited=origin)


def clean(rule_id, scanned, targets, note=""):
    """対象はあるが違反がない(○)。★**母集合数・対象数が必須。**

    G1: 「読めなかったので何もしなかった」経路から ○ は出ない。
    G9: **対象行0件を「全行合格」と表現しない。**
    """
    if not isinstance(scanned, int) or not isinstance(targets, int) or scanned < 0 or targets < 0:
        raise ValueError("clean には母集合数と対象数(0以上の整数)が要る: rule=%s scanned=%r targets=%r"
                         % (rule_id, scanned, targets))
    if targets > scanned:
        raise ValueError("対象数が母集合数を超えている: rule=%s %d/%d" % (rule_id, targets, scanned))
    if targets == 0:
        head = "対象0件(母集合%d行を走査。**「全行合格」ではない**)" % scanned
    else:
        head = "母集合%d行のうち対象%d行を検査・違反なし" % (scanned, targets)
    return _mk(rule_id, "clean", head + (" — " + note if note else ""),
               scanned=scanned, targets=targets)


def violation(rule_id, findings, note=""):
    """違反(✕)。責任は納品物。"""
    r = _mk(rule_id, "violation", note)
    for lineno, msg in findings:
        r.findings.append((lineno, msg))
    r.status = "ng"
    return r


def partial(rule_id, read, total, reason):
    """入力を一部しか読めなかった(▲)。★**読めた数/全体数が必須。**責任は納品物。"""
    if not isinstance(read, int) or not isinstance(total, int):
        raise ValueError("partial には 読めた数/全体数 が要る: rule=%s" % rule_id)
    return _mk(rule_id, "partial",
               "%d/%d しか読めなかった — %s(未検査であって合格ではない)" % (read, total, reason),
               read=read, total=total)


def missing_input(rule_id, what, supplier):
    """検査に必要な情報がない(▲)。★**欠けた物と供給者が必須。**

    ★供給者で門番の扱いが変わる(DESIGN 柱2 の中心):
      納品物 = 書き手が書式を直せば解ける → 違反を立てる側
      呼び出し = 書き手には直せない → 違反にしない
    """
    if supplier not in SUPPLIERS:
        raise ValueError("missing_input の supplier は %s のいずれか: rule=%s supplier=%r"
                         % ("/".join(SUPPLIERS), rule_id, supplier))
    if not what:
        raise ValueError("missing_input には欠けた物の名前が要る: rule=%s" % rule_id)
    return _mk(rule_id, "missing_input", "%s が無い(供給者: %s)" % (what, supplier),
               what=what, supplier=supplier)


def exc_where(exc):
    """例外が**どこで**起きたかを1つの短い文字列にする(最も内側の枠)。

    ★ここは**手書きの file:line ではない** —— 例外そのものから実行時に導いた位置である。
      手書きの行番号は原典が伸び縮みすると腐るが、これは腐りようがない(毎回その場で作る)。
    """
    tb = getattr(exc, "__traceback__", None)
    last = None
    while tb is not None:
        last = tb
        tb = tb.tb_next
    if last is None:
        return "位置不明"
    return "%s:%d" % (os.path.basename(last.tb_frame.f_code.co_filename), last.tb_lineno)


def crashed(rule_id, exc):
    """検査処理が失敗した(▲)。★責任は**チェッカー**であって納品物ではない。

    ★段6(2026-08-20)まで、このコンストラクタは**1度も呼ばれていなかった**(被覆の実測でも
      L の呼び出し行が「★未実行」だった)。段6 で各規則を try で包み、**ここが唯一の受け皿**になった。
    ★**例外の中身を捨てない。**型・本文・発生位置の3つを画面に出す —— 責任がチェッカーである以上、
      画面を読むのは**直す人**であり、直す人に要るのはこの3つである。
    """
    return _mk(rule_id, "crashed",
               "検査処理が失敗した: %s: %s(発生位置 %s)"
               % (type(exc).__name__, exc, exc_where(exc)),
               exc=repr(exc))


def needs_human(rule_id, origin, assignee, reason=""):
    """人間の判断が必要(△)。★原典と割当先が必須。

    機械側で違反にすれば、原典に無い基準を発明することになる(規則表 :9 原則1)。
    """
    if not origin or not ORIGIN_RE.search(str(origin)):
        raise ValueError("needs_human には原典の file:line が要る: rule=%s origin=%r" % (rule_id, origin))
    if not assignee:
        raise ValueError("needs_human には割当先が要る: rule=%s" % rule_id)
    return _mk(rule_id, "needs_human",
               "%s目視で確認すること(規定: %s / 割当: %s)" % (reason + " — " if reason else "", origin, assignee),
               origin_cited=origin, assignee=assignee)


# ---- 段6: 各規則を try で包む(DESIGN §6・2026-08-20) --------------------------
# ★逐語:「`crashed`(**各規則を try で包む**)。**ファイル単位で `report` まで到達させ、
#   途中で全体が消える現在の挙動をやめる**」
#
# ★★**「try で囲んで pass」は最悪の実装である。**ここは握りつぶさない ——
#   例外は捨てられるのではなく `crashed`(▲)という**結果になる**。
# ★★2026-08-20(ユーザーの裁定)に伴い、**合格にしない道筋が変わった**。以前は門番
#   (`check_kanmon` の `stuck`)が ▲ を無条件で拾って ✕ を立てていたが、それは
#   `DESIGN.md` 柱2 の表(「チェッカー側は違反にしない」)と食い違っていた。
#   ⇒ いまは**門番は拾わない。**代わりに ▲ がそのまま残り、`report()` が `blocked` を数え、
#     `main()` が **終了コード 3(検査が完了していない)**を返す。**合格(0)にはならない。**
#   ⇒「検査できなかった」を合格に数えないという柱2の中心は、例外の場合にも効いている。
#     違うのは**答え方**である —— `1`(直すべきものが分かっている)ではなく
#     `3`(まだ検査が終わっていない)と答える。
# ★★これは「例外を無かったことにする工事」ではなく、**例外を1規則に閉じ込める工事**である。
#   閉じ込めなければ、例外1つで**同じ走行の他のファイルまで検査されないまま消える**。
#
# ★責任の所在は **チェッカー**(`STATE_RESPONSIBILITY["crashed"]`)である。書き手には直せない。
#   画面の「受理の記録」がそう申告するので、▲ を見た人が納品物を直そうとして途方に暮れることはない。
@contextlib.contextmanager
def guard(results, rule_id):
    """規則1本を try で包む。★例外はここで止め、**その規則だけ**を `crashed`(▲)にする。

    ★**途中まで積んだものは捨てる。**同じ規則が「判定つきの行」と「crashed の行」の
      2行で出ると、集計が二重になり、どちらが本当かも読めない。**1規則1行**を守る。
    """
    n = len(results)
    try:
        yield
    except Exception as exc:
        del results[n:]
        results.append(crashed(rule_id, exc))


def guarded(results, rule_id, thunk):
    """1つの式で済む規則(共用部品の呼び出し)を try で包んで積む。`guard` の呼び出し形。

    ★`with` 形と2つの形があるのは体裁ではない —— **字下げを動かさずに包める**ほうが、
      包み忘れも取り違えも起きにくい(この工事で触る規則は 56本ある)。

    ★★**引数ではなく thunk を取るのには理由がある。**最初は `guarded(results, id, fn, *a)` と
      書いていた。ところが Python は**呼び出しの前に引数を評価する**ので、
      `guarded(results, "U-6", check_uradori_legend, body, sm)` の `sm` が
      **上流の規則(U-5)の中で作られる**とき、U-5 が落ちると `sm` の評価が
      **guard の外**で失敗し、例外は規則単位で受け止められず**ファイル単位の網まで飛ぶ**。
      ★実測でそうなった —— U-4 に例外を注入したら、`sm` を評価する行で落ち、
      **U-4 と無関係な U-13・U-16・U-17 まで道連れ**になった
      (現物: `evidence/dan6-taisho-ato-U4-hairan.txt`)。
      ⇒ thunk にすれば評価も try の中に入る。**包みの外に計算を残さない。**
    """
    with guard(results, rule_id):
        results.append(thunk())


def rules_of(kind):
    """その種別に属する規則IDの全部。★出所は `RULES` **1か所**である(ここに書き並べない)。"""
    return [rid for rid, target, _t, _o, _lv in RULES if target == kind]


def crash_all(kind, results, exc):
    """★**規則の外**(共通処理)で落ちたときの後始末。**ファイル単位で `report` まで到達させる。**

    規則の中の例外は `guard` が規則単位で受け止める。ここで受け止めるのは、読み込み・種別判定・
    表の切り出しなど**どの規則にも属さない処理**で起きた例外である。
    ★そのとき**まだ出ていない規則は1本も検査できていない**のだから、全部 ▲ にするのが事実である。
    ★**すでに判定の出た規則はそのまま残す**(「他の規則の判定は残る」)。
    """
    got = {r.rule_id for r in results}
    for rid in rules_of(kind):
        if rid not in got:
            results.append(crashed(rid, exc))
    return results


# ---- 段1: 「―」の中身を7状態へ振り分ける ------------------------------------
# ★いまの穴の正体(課題B の診断・実測つき):
#   31か所の skip 引数はすべて日本語の1文字列で、原典の file:line を伴うものは 0か所である。
#   したがって「**規定による対象外**」と「**検査したかったのにできなかった**」が
#   同じ関数・同じ記号「―」・同じ集計欄に落ちる。
#   fail-open の病巣は「blocked を呼び忘れた」ことではなく、
#   **呼び分けるための情報を型が要求していないこと**にある。
#
# ★段1でやるのは「記録」だけである。記号は1つも動かさない(判定は段3以降で繋ぐ)。
#   動かさない理由は移行の順序そのもの —— **まず観測だけを足し、判定は最後に繋ぐ**。
def skip_as(r, reason, state, **info):
    """従来どおり「―」を立てつつ、それが7状態のどれなのかを**併せて記録する**。

    ★見た目は1文字も変わらない。変わるのは集計行2行目(受理の記録)だけである。
    """
    r.skip(reason)
    return r.observe(state, **info)


# ---- 段3: 列が無いときの状態を「原典の水準表」から決める ----------------------
# ★段1は31か所を一律 missing_input(supplier="納品物") に振り分けた。**そこに誤りがあった。**
#   uradori の必須列は**水準ごとに違う**。水準①で任意の列が無いのは「検査に必要な情報が
#   納品物に無い」のではなく、**規定による対象外**である。
#   段1の振り分けのままで門番に繋ぐと、水準①の正しい台帳を止める(=逆向きの事故)。
#   実測: `uradori-workspace\iteration-1\runs\E4-on-1\daicho.md` は水準①軽装で逐語列が無く、
#   原典が「任意」と定めているのに、段1の振り分けでは違反候補に数えられていた。
#
# ★下の表は原典 run-uradori/references/daicho-format.md の**水準表の転記であって、新しい基準ではない**
#   (規則表 deliverable-rules.md の原則1)。列を足す者はまず原典の表に足すこと。
# ★2026-08-18(申-3): 原典欄の行番号をやめ、**逐語から導出する鍵**に置き換えた。
#   ここは「規定による対象外」を名乗る根拠そのものなので、指し先が腐ると
#   **対象外の証明が嘘になる**(fail-open の型)。控えの file:line は F-11 が導出結果と照合する。
URADORI_COL_REQ = {
    # 概念:      (原典の鍵(控えは ORIGIN_FALLBACK に集約),  {水準: 要否})
    "分類":       ("COL:分類", {1: "任意", 2: "必須", 3: "必須"}),
    # ★逐語の①は原典が「必須(反証行)」と書いている。**列そのものの要否としては①=任意**であり、
    #   「反証の行があるなら逐語が要る」という条件つきの必須性は **U-11 が別に見ている**
    #   (反証行が0件なら clean(targets=0)、1件でもあれば逐語の空欄を違反にする)。
    #   ★この読み替えを黙って行わない —— ここに書いておかないと、次に読む者が誤記だと思う。
    "逐語":       ("COL:逐語", {1: "任意", 2: "必須", 3: "必須"}),
    "アクセス日": ("COL:アクセス日", {1: "—",   2: "推奨", 3: "必須"}),
    "備考":       ("COL:備考", {1: "任意", 2: "推奨", 3: "必須"}),
}


def col_req(concept):
    """その列の「水準ごとの要否」を返す。★添字で取り出さない。

    2026-08-18 に原典欄を鍵に置き換えたとき、要否を位置で引いていた2か所が
    黙って文字列を掴んだ(即座に例外になったので実害は無かったが、**位置で取ると次も同じことが起きる**)。
    """
    return URADORI_COL_REQ[concept][1]


def missing_column_state(concept, level):
    """その列が無いときの7状態を、原典の水準表から決める。返り値 (state, info)。

    ★水準が読めない(level is None)ときは「規定による対象外」を名乗れない。
      対象外だと言うには原典の**どの行が**それを許すかを指せねばならず、水準が分からなければ
      指せないからである。よって missing_input(納品物) に倒す(fail-close)。
      水準が読めないこと自体は U-2 が違反として報告する。
    """
    key, req = URADORI_COL_REQ[concept]
    if level in req and req[level] != "必須":
        return "not_applicable", {"origin": origin_at(key)}
    return "missing_input", {"what": "%s列" % concept, "supplier": "納品物"}


# ---- 勘定(柱3) --------------------------------------------------------------
# ★文書全体の1本だけにすると、未分類の行を「散文」へ既定落ちさせるだけで恒真化する。
#   だから3層に分ける。
#
# 除外の理由コードは**閉じた列挙**で、各理由は**述語として機械で再検証できる**。
# 列挙に無い理由で行を消すことはできず、消えれば層2の差集合に現れる。
EXCLUSION_CODES = {
    "E1": "閉じたフェンスの内側",
    "E2": "補助表(必須概念を全部は持たない表)",
    # ★E3「bunken 縦型台帳(2026-08-04 決定)」は 2026-08-19(段5-1)に**落とした**。
    #   ・落とした理由: その決定が挙げた唯一の理由「原典に『表以外を禁じる』規定が無い」は、
    #     F-001(2026-08-17)で原典に規定が入ったので消滅した。決定自身が
    #     「同じ厳密性を適用する可能性は捨てていない —— 文書側に規定を足すところから」と書いている。
    #   ・★縦型台帳を対象外にできない根拠は「表で書く」ではない。縦型も**表ではある**。
    #     根拠は行の向きを定めた句である(原典 run-bunken-daicho/references/daicho-format.md の逐語:
    #     「1行目がヘッダー行、2行目が `|---|` の区切り行、以降が**各文献の行**」)。
    #     ⇒ 縦型台帳は台帳本体として読めず、B-0(門番)が拾う。除外の理由コードは要らない。
    #   ・★この列挙にコードを戻すときは、必ずユーザー決定を伴わせること。
    #     常設テスト E-12 が「E3 が戻っていないこと」を見張っている。
    "E4": "マスク(URL・インラインコード・リンク先の伏せ字)",
    "E5": "水準・規定による対象外",
}


class Ledger:
    """勘定。**チェッカー自身の取り落としの検出器**であって、書き手の欺瞞の検出器ではない。

    ★G-0 の逐語(DESIGN 柱3): 納品物の品質を判定しない。チェッカー自身の実行が
    完全だったかを判定する。納品物への要求は1つも増えない。
    """

    def __init__(self, doc):
        self.doc = doc
        self.layer1 = {}
        self.layer2 = {}
        self.layer3 = []
        self.breaks = []

    # -- 層1: 文書=行の全数分配 ------------------------------------------------
    def build_layer1(self):
        doc = self.doc
        n = len(doc.raw_lines)
        if doc.kind == "html":
            h = doc.html
            self.layer1 = {"入力行": n, "パーサー到達行": h.get("reached_line", 0)}
            if not h.get("reached_all"):
                self.breaks.append("層1(HTML): パーサーが L%d で止まり、入力の末尾 L%d に届いていない"
                                   % (h.get("reached_line", 0), n))
            return self.layer1
        cls = {}
        table_lines = set()
        for t in doc.tables:
            table_lines.add(t["hline"])
            table_lines.add(t["hline"] + 1)
            for lineno, _rc in t["rows"]:
                table_lines.add(lineno)
        for i in range(1, n + 1):
            if i in doc.fence_lines:
                cls[i] = "フェンス"
            elif i in table_lines:
                cls[i] = "表"
            elif not doc.raw_lines[i - 1].strip():
                cls[i] = "空行"
            elif any(h[0] == i for h in doc.headings):
                cls[i] = "見出し"
            else:
                cls[i] = "散文"
        from collections import Counter
        self.layer1 = dict(Counter(cls.values()))
        self.layer1["入力行"] = n
        total = sum(v for k, v in self.layer1.items() if k != "入力行")
        if total != n:
            self.breaks.append("層1: 処分クラス別行数の合計 %d が入力行数 %d と一致しない" % (total, n))
        self._cls = cls
        return self.layer1

    # -- 層2: 二挺の物差し ------------------------------------------------------
    def build_layer2(self):
        """★この柱の要。同じ走査から両辺を導けば恒等式は恒真になり何も検出しない。

        外形分類器は**複雑化を禁じる**。仕様は「半角の縦棒を2本以上含む行は表らしい行」
        —— この1文がすべてであり、愚直で目視検証できる長さに保つこと。
        レンズ事件は測定器が対象と同じ誤読を共有した事故だった。
        """
        doc = self.doc
        if doc.kind == "html":
            h = doc.html
            self.layer2 = {"タグ(パーサー)": h.get("tags_parser", 0), "タグ(外形)": h.get("tags_shape", 0)}
            if h.get("tags_shape", 0) > h.get("tags_parser", 0):
                self.breaks.append("層2(HTML): 外形分類器が数えたタグ %d 個のうち %d 個しか"
                                   "パーサーが認識していない"
                                   % (h["tags_shape"], h["tags_parser"]))
            return self.layer2

        # 外形分類器(★愚直に保つ。これ以上のことをさせない)
        shape = set(i + 1 for i, l in enumerate(doc.raw_lines) if l.count("|") >= 2)

        parser_side = set()
        for t in doc.tables:
            parser_side.add(t["hline"])
            parser_side.add(t["hline"] + 1)
            for lineno, _rc in t["rows"]:
                parser_side.add(lineno)
        excluded = {}
        for i in sorted(shape - parser_side):
            if i in doc.fence_lines:
                excluded[i] = "E1"
        diff = sorted(shape - parser_side - set(excluded))
        self.layer2 = {"外形が表らしいと見た行": len(shape), "パーサーが表に数えた行": len(parser_side),
                       "理由コードつき除外": len(excluded), "差集合": len(diff)}
        if diff:
            self.breaks.append("層2: 外形が表らしいと見たのにパーサーが数えず、"
                               "理由コードも付かない行が %d 行ある(最初は L%d)" % (len(diff), diff[0]))
        self._layer2_diff = diff
        return self.layer2

    # -- 層3: 規則×行 -----------------------------------------------------------
    def note_rule(self, rule_id, applicable, checked, excluded_by_code):
        """規則が「母集合のうち何行を検査し、何行をどの理由で除いたか」を置く場所。

        applicable = checked + Σexcluded。合わなければ破れ。
        段1以降で規則側から呼ぶ。段0では誰も呼ばない。
        """
        s = sum(excluded_by_code.values())
        bad = [c for c in excluded_by_code if c not in EXCLUSION_CODES]
        if bad:
            self.breaks.append("層3(%s): 閉じた列挙に無い除外理由 %s" % (rule_id, "・".join(bad)))
        if applicable != checked + s:
            self.breaks.append("層3(%s): applicable %d ≠ checked %d + 除外 %d"
                               % (rule_id, applicable, checked, s))
        self.layer3.append((rule_id, applicable, checked, dict(excluded_by_code)))

    def build(self):
        self.build_layer1()
        self.build_layer2()
        return self

    def print_report(self):
        d = self.doc
        print("  [勘定 — チェッカー自身の取り落としの検出器。★納品物の品質は判定しない]")
        print("    受理: %s" % " / ".join("%s %s" % (k, v) for k, v in d.counts.items()))
        print("    層1(行の全数分配): %s" % " / ".join("%s %s" % (k, v) for k, v in self.layer1.items()))
        print("    層2(二挺の物差し): %s" % " / ".join("%s %s" % (k, v) for k, v in self.layer2.items()))
        if self.layer3:
            print("    層3(規則×行): %d 規則が母集合を申告" % len(self.layer3))
        if d.unsupported:
            print("    未対応の記録 %d件:" % len(d.unsupported))
            for u in d.unsupported[:20]:
                print("      L%-5s %-22s %s [%s]" % (u.lineno, u.construct, u.detail[:60], u.clause_id))
        if self.breaks:
            print("    ★勘定の破れ %d件:" % len(self.breaks))
            for b in self.breaks:
                print("      ・%s" % b)
        else:
            print("    勘定の破れ: なし")
        print("")


# ---------------------------------------------------------------- 台帳共通の検査
def check_link_column(rule_id, rows, link_i, header_present, empty_msg):
    title, origin = rule_meta(rule_id)
    r = Result(rule_id, title, origin)
    # ★段2以降この枝は到達不能である。台帳本体は「必須概念のすべてに単射な列割当が
    #   存在する」ときに限り本体を名乗れる(is_ledger_body)ので、本体が取れた時点で
    #   判定・リンク・主張は必ず割り当たっている。根拠の常設テスト= E-2。
    #   ★消していないのは防御のためであり、必須概念を変えたら E-2 が落ちてここが生き返る。
    if not header_present:
        skip_as(r, "リンク列が見つからない(列名の確認が先)",
                "missing_input", what="リンク列", supplier="納品物")
        return r
    for lineno, row in rows:
        v = cell(row, link_i)
        if is_empty(v):
            r.fail(lineno, "リンク列が空 — %s" % empty_msg)
        elif not looks_like_link(v):
            r.fail(lineno, "リンク列がURL・ファイルパスの形をしていない: %s" % v[:40])
    if r.status == "ok":
        r.ok_note("%d行すべてにリンクあり" % len(rows))
    return r


def check_date_column(rule_id, rows, date_i, required, label, absent=None):
    """absent = 段3で呼び出し側が渡す (state, info)。列が無いときの7状態を**呼び出し側が知っている**
    (水準ごとの要否は uradori 側にしか無い情報なので、この共用関数では決められない)。"""
    title, origin = rule_meta(rule_id)
    r = Result(rule_id, title, origin)
    if date_i is None:
        if required:
            r.fail(None, "アクセス日列が無い(%s)" % label)
        else:
            st, info = absent or ("missing_input", {"what": "アクセス日列", "supplier": "納品物"})
            skip_as(r, "アクセス日列が無い(%s)" % label, st, **info)
        return r
    checked = 0
    for lineno, row in rows:
        v = cell(row, date_i)
        if is_empty(v):
            if required:
                r.fail(lineno, "アクセス日が空(%s)" % label)
            continue
        checked += 1
        if not DATE_RE.search(v):
            r.fail(lineno, "アクセス日が日付の形でない: %s" % v[:30])
    if r.status == "ok":
        r.ok_note("%d行を照合(%s)" % (checked, label))
    return r


# ---------------------------------------------------------------- uradori 台帳
URADORI_COLS = {
    "#":        ["#", "No", "no", "番号"],
    "主張":     ["主張"],
    "分類":     ["分類"],
    "判定":     ["判定"],
    "ソース名": ["ソース名", "ソース", "出典名"],
    "リンク":   ["リンク", "URL", "url"],
    "位置":     ["位置", "所在"],
    "逐語":     ["要旨/逐語", "要旨・逐語", "逐語", "要旨"],
    "到達範囲": ["到達範囲", "精読"],
    "アクセス日": ["アクセス日"],
    "備考":     ["備考"],
}


def detect_uradori_level(text):
    """ヘッダーの「検証水準」を読む。

    水準が読めないと U-3 の必須列が全水準共通の5列に縮み、U-12 も「③=必須」から
    「推奨」に落ちる。つまり**書き方のゆれ一つで提出級の検査がまるごと消える**ので、
    キーの装飾(太字)・区切り(コロン/表のセル区切り)・値の言い換え(レベル3・3)に耐えさせる。
    """
    m = re.search(r"検証水準\s*\**\s*[:：|｜]\s*\**\s*(.+)", text)
    if not m:
        return None, None
    v = re.split(r"[|｜]", m.group(1))[0]        # 表形式で書かれたときの後続セルを落とす
    v = v.replace("*", "").strip()
    if "③" in v or "提出" in v:
        return 3, v
    if "②" in v or "標準" in v:
        return 2, v
    if "①" in v or "軽装" in v:
        return 1, v
    m2 = re.search(r"(?:レベル|水準|lv\.?|level)?\s*([123])(?![0-9])", v, re.I)
    if m2:
        return int(m2.group(1)), v
    return None, v


def collect_uradori_tables(tables, cols, must_have_keys):
    """★段2で使わなくなった(呼び出し 0か所)。後継は `collect_ledger_tables`。

    **消さずに残してあるのは、移行の「前」側を再現するためだけである**
    (`runs\\checker\\evidence\\dan2_probe.py` が旧新の読み取り行数を比べるのに使う)。
    ★新しい規則からこれを呼ばないこと —— 得点最大での代用は段2で捨てた方式である。
    段3の片付け候補。

    台帳本体を**すべて**集めて1つの行列に揃える(uradori 専用)。

    台帳を複数の表に分けて書くと、かつては1つ目の表しか検査されなかった。
    2つ目以降にリンク空・予約語・条件の欠落があっても全部合格になり、
    さらに反証・未確認の件数を数え落として「反証0件」と断定していた。

    ただし**全部の表を無条件に結合してはいけない**——実在の納品物は補助表(探索エンジン別の
    内訳など)を持つ。そこで:
      - 台帳本体(primary)の選び方は従来どおり(必須列を最も多く満たす表。>=2 で採用)
      - **追加で結合するのは、必須列を全部持つ表だけ**(補助表は列が違うので入らない)
      - 表ごとに列の並びが違ってよいように、primary の列順へ詰め替えてから結合する

    返り値: (primary_header, rows, hline, 結合した表の数) / 見つからなければ (None, [], None, 0)
    """
    must = [cols[k] for k in must_have_keys]
    scored = [(sum(1 for aliases in must if find_col(t["header"], aliases) is not None), t)
              for t in tables]
    primary, best = None, 0
    for score, t in scored:
        if score > best:
            primary, best = t, score
    if primary is None or best < 2:
        return None, [], None, 0

    header = primary["header"]
    pidx = {k: find_col(header, v) for k, v in cols.items()}
    width = len(header)
    rows, used = [], 0
    for score, t in scored:
        if t is not primary and score < len(must):
            continue                                   # 補助表は結合しない
        used += 1
        tidx = {k: find_col(t["header"], v) for k, v in cols.items()}
        for lineno, rc in t["rows"]:
            if t is primary:
                rows.append((lineno, rc))
                continue
            newrow = [""] * width
            for k, pi in pidx.items():
                if pi is not None and tidx.get(k) is not None:
                    newrow[pi] = cell(rc, tidx[k])
            rows.append((lineno, newrow))
    rows.sort(key=lambda x: x[0])
    return header, rows, primary["hline"], used


def norm_uradori_hantei(v):
    """判定セルの正規化(uradori 専用)。太字記号と丸かっこの注記を落とす。

    **全項目でこの1本を通すこと。** かつて U-4・U-5 だけが注記を落とし、
    U-8〜U-13 は生の値で比較していたため、「条件付き裏付け(近似値)」のように
    一言添えた行が「5語のうちの1つ」として合格・件数にも算入されながら、
    備考必須・逐語必須・探索記録必須の照合からは同時に外れていた。
    """
    v = v.replace("*", "").strip()
    return re.sub(r"[（(].*?[）)]", "", v).strip()


def pick_ledger_table(tables, must_have):
    """★段2で使わなくなった(呼び出し 0か所)。後継は `collect_ledger_tables`。

    残す理由は `collect_uradori_tables` と同じ(移行の「前」側の再現)。段3の片付け候補。
    ★**必須列を1つ欠いた表でも台帳本体を名乗れる**のがこの関数の欠陥だった。

    必須列を最も多く満たす表を台帳本体とみなす。"""
    best, best_score = None, 0
    for t in tables:
        score = sum(1 for aliases in must_have if find_col(t["header"], aliases) is not None)
        if score > best_score:
            best, best_score = t, score
    return best if best_score >= 2 else None


def check_uradori(path, raw, lines, sink=None, data=None):
    # ★段6: sink を渡されたら**そこへ積む**。規則の外で例外が起きても、
    #   すでに出た判定を呼び出し側が拾えるようにするための口である(判定は1つも変わらない)。
    results = [] if sink is None else sink
    body = strip_code_fences(lines)
    text = "\n".join(body)
    level, level_raw = detect_uradori_level(text)
    tables = parse_md_tables(body)
    # 段2: 得点最大での代用をやめ、**役の述語**で選ぶ。台帳本体が複数あれば全部を結合する。
    header, rows, hline, n_tbl, undecided = collect_ledger_tables(
        tables, URADORI_COLS, ("判定", "リンク", "主張"))
    tbl = None if header is None else True

    # U-2 ヘッダーブロック
    with guard(results, "U-2"):
        r = Result("U-2", *rule_meta("U-2"))
        head = "\n".join(body[:40])
        missing = [k for k in ("検証水準", "対象範囲", "探索エンジン", "実行日") if k not in head]
        if missing:
            r.fail(None, "ヘッダーブロックに %s が無い(冒頭40行を確認)" % "・".join(missing))
        else:
            r.ok_note("検証水準・対象範囲・探索エンジン・実行日 の4項目あり")
        results.append(r)

    if tbl is None:
        # **「検査できなかった」を「合格」と同じ出力にしない。**
        # 表として読めないと行単位の規則が丸ごと落ちるのに、かつては違反0・終了コード0だった。
        for rid in ("U-1", "U-3", "U-4", "U-5", "U-7", "U-9", "U-10", "U-11", "U-12", "U-13",
                    "U-15", "U-16", "U-17", "U-18", "U-19", "U-20", "U-21", "U-22",
                    "U-23"):
            with guard(results, rid):
                rr = Result(rid, *rule_meta(rid))
                rr.blocked("台帳本体が表として読めないため実行できなかった — 未検査であって合格ではない")
                rr.observe("partial", read=0, total=len(body))
                results.append(rr)
        guarded(results, "U-6", lambda: check_uradori_legend_only(body))
        guarded(results, "U-8", lambda: check_uradori_tansaku(body, []))
        guarded(results, "U-14", lambda: check_teishutsu(body, None, None))
        # U-24 コードの囲み(C-5)。★門番の前に置く —— 門番が ▲ を数えるためである。
        guarded(results, "U-24", lambda: check_fence_closed("U-24", lines))
        # U-25・U-26 全角の縦棒・文字コード(2026-10-05)。★門番の前に置く —— 門番が ▲ を数えるためである。
        guarded(results, "U-25", lambda: check_fullwidth_table("U-25", body))
        guarded(results, "U-26", lambda: check_utf8("U-26", raw, data))
        guarded(results, "U-0", lambda: check_uradori_kanmon(results, body, tables))
        return results, level_raw

    # 段2: 割当は**単射**。1つの物理列を2つの概念に兼用しない(G8)。
    idx = dict.fromkeys(URADORI_COLS)
    idx.update(assign_columns(header, URADORI_COLS)[0])

    # U-1 リンク全行必須
    guarded(results, "U-1",
            lambda: check_link_column("U-1", rows, idx["リンク"], idx["リンク"] is not None,
                                      "リンクのない裏付けは裏付けとして数えない"))

    # U-20 段階A: そのリンクが**現に届くか**。★U-1(在るか)とは別の検査である。
    guarded(results, "U-20",
            lambda: check_link_reach("U-20", rows, idx["リンク"],
                                     idx["リンク"] is not None, LINK_EVIDENCE))

    # U-22 段階C: 引いた逐語が**原典に現に在るか**。★U-20(届くか)とは別の検査である。
    #   ★対照A に使うのは **ソース名**(★uradori には書誌欄が無い。★資料の名前がその代わり)。
    guarded(results, "U-22",
            lambda: check_quote_presence("U-22", rows, idx["逐語"], idx["リンク"],
                                         idx["ソース名"], True, FULLTEXT_EVIDENCE))

    # U-3 必須列(水準依存)
    def lack_note(colname, note_by_level):
        """列が無いときの説明文。**台帳が名乗った水準の話をする**(かつて水準②の台帳に
        「水準①では任意」と説明を出し、書き手に欠落を誤りだと気づかせなかった)。"""
        if level is None:
            return "%s列が無い(水準がヘッダーから読めないため任意として扱った)" % colname
        return "%s列が無い(水準%s では%s)" % (colname, level_raw or level, note_by_level[level])

    with guard(results, "U-3"):
        r = Result("U-3", *rule_meta("U-3"))
        # 段3: 水準ごとの要否は URADORI_COL_REQ **1か所**から引く。
        #   かつては `if level in (2,3)` / `if level == 3` と条件に書き下しており、水準表と同じ知識が
        #   2か所にあった。★2か所にあると片方だけ直したときに誰も気づかない。
        #   (要旨/逐語は②=要旨・③=逐語で、どちらも同じ列に書く。②で必須に数えていなかったため、
        #    要旨の無い②台帳が「必須列すべてあり」で通っていた。)
        req = ["#", "主張", "判定", "ソース名", "リンク"]
        req += [c for c in ("分類", "逐語", "アクセス日", "備考")
                if col_req(c).get(level) == "必須"]
        lack = [k for k in req if idx[k] is None]
        if lack:
            r.fail(hline, "必須列が無い: %s（水準%s）" % ("・".join(lack), level_raw or "不明"))
        else:
            r.ok_note("水準%s の必須列 %d 個すべてあり" % (level_raw or "不明", len(req)))
        # **何行を検査したかを必ず見せる。** 台帳を複数の表に分けたとき、かつては1つ目の表しか
        # 検査していないのに「○」だけが出ていた(本番台帳で27行中4行しか見ていなかった実例がある)。
        r.note += "／台帳本体= 表%d つ・%d 行を検査" % (n_tbl, len(rows))
        if undecided:
            # これまでは黙って捨てていた。**捨てた事実を出力に残す。**
            r.note += "／★役が確定しない表 %d つ(L%s。必須概念を持つが単射な割当が成立しない)" % (
                len(undecided), "・L".join(str(u["hline"]) for u in undecided))
        if level is None:
            r.note += " ※水準がヘッダーから読めないため全水準共通の5列のみ照合"
        results.append(r)

    # U-4 判定語
    with guard(results, "U-4"):
        r = Result("U-4", *rule_meta("U-4"))
        hantei_vals = []
        # ★段2以降この枝は到達不能である。台帳本体は「必須概念のすべてに単射な列割当が
        #   存在する」ときに限り本体を名乗れる(is_ledger_body)ので、本体が取れた時点で
        #   判定・リンク・主張は必ず割り当たっている。根拠の常設テスト= E-2。
        #   ★消していないのは防御のためであり、必須概念を変えたら E-2 が落ちてここが生き返る。
        if idx["判定"] is None:
            skip_as(r, "判定列が無い", "missing_input", what="判定列", supplier="納品物")
        else:
            for lineno, row in rows:
                v = norm_uradori_hantei(cell(row, idx["判定"]))
                hantei_vals.append((lineno, v))
                if v in ("確定", "推論", "仮", "仮説", "要検証"):
                    r.fail(lineno, "「%s」はkikakusho体系の予約語。uradoriの判定語に流用しない" % v)
                elif v not in URADORI_HANTEI:
                    r.fail(lineno, "判定「%s」は5語(%s)に無い" % (v or "(空)", " / ".join(URADORI_HANTEI)))
            if r.status == "ok":
                r.ok_note("%d行すべて5語のいずれか" % len(rows))
        results.append(r)

    # U-5 判定サマリー
    with guard(results, "U-5"):
        # ★段6: 件数の数え上げは**U-5 の中**に置く。ここは U-5 しか使わないので、
        #   guard の外に置くと U-4 が落ちたときにファイル単位の網まで飛び、
        #   **U-5 と無関係な規則(U-13・U-16・U-17 など)まで道連れになる。**
        #   共通処理の面積が広いほど巻き添えが増える —— 面積は狭く保つ。
        counts = {k: 0 for k in URADORI_HANTEI}
        for _ln, v in hantei_vals:
            if v in counts:
                counts[v] += 1
        r = Result("U-5", *rule_meta("U-5"))
        sm = None
        for i, ln in enumerate(body):
            if re.match(r"^#{1,4}\s*判定サマリー", ln.strip()):
                sm = i
                break
        if sm is None:
            r.fail(None, "「## 判定サマリー」の見出しが無い(台帳末尾に必須)")
        else:
            got, cnt_line = read_summary_counts(body, sm)
            if len(got) < 5:
                # **飛ばした突合を「合格」に数えない。**旧実装はここで ok_note(=合格)を返しており、
                # 実際は裏付け2・反証1・未確認1なのに「裏付け5・反証0・未確認0」の嘘のサマリーが通っていた。
                r.blocked("件数の書式が読めず突合を実行できなかった(読めたのは %s)— "
                          "5種すべての件数を1行に書く(0件も省かない)"
                          % ("・".join(sorted(got)) or "0種"))
                r.observe("partial", read=len(got), total=5)
            else:
                diff = [(k, got[k], counts[k]) for k in URADORI_HANTEI if got[k] != counts[k]]
                if diff:
                    for k, a, b in diff:
                        r.fail(cnt_line or sm + 1,
                               "サマリーの%s=%d が台帳本体の実数%d と一致しない" % (k, a, b))
                else:
                    r.ok_note("見出しあり・5種の件数が台帳本体と一致")
        # ★段階A-3 の申告文へ渡す(→ `STAGE_A_SELF`)。★**ここが数えている当のものを渡す。**
        #   ★別に数え直さない(同じ知識を2か所に置くと、片方だけが古くなる)。
        #   🔴★`observe` は `state_info` を丸ごと置き換えるので、**その後に**載せる。
        r.state_info["hantei_counts"] = counts
        results.append(r)

    # U-6 凡例(判定)
    guarded(results, "U-6", lambda: check_uradori_legend(body, sm))

    # U-7 凡例(分類)
    with guard(results, "U-7"):
        r = Result("U-7", *rule_meta("U-7"))
        if idx["分類"] is None:
            # 段3: 状態は水準表から決める(水準①では原典が任意と定めているので対象外)
            _st, _in = missing_column_state("分類", level)
            skip_as(r, lack_note("分類", {1: "任意", 2: "必須 — U-3 で違反として報告済み",
                                      3: "必須 — U-3 で違反として報告済み"}), _st, **_in)
        else:
            used = set()
            for _ln, row in rows:
                v = cell(row, idx["分類"]).replace("*", "").strip()
                if v and not is_empty(v):
                    used.add(v)
            leg = next((l for l in body if "凡例" in l and "分類" in l), None)
            if leg is None:
                r.fail(None, "「**凡例(分類)**」の行が無い(台帳に分類列があるとき必須)")
            else:
                lack = [u for u in sorted(used) if u not in leg]
                if lack:
                    r.fail(None, "凡例(分類)に載っていない分類: %s" % "・".join(lack))
                else:
                    r.ok_note("登場する分類 %d 種すべてが凡例にあり" % len(used))
        results.append(r)

    # U-8 探索記録
    with guard(results, "U-8"):
        need = [(ln, v) for ln, v in hantei_vals if v in ("未確認", "未到達")]
        numbers = []
        if idx["#"] is not None:
            for lineno, row in rows:
                v = norm_uradori_hantei(cell(row, idx["判定"])) if idx["判定"] is not None else ""
                if v in ("未確認", "未到達"):
                    num = re.sub(r"\D", "", cell(row, idx["#"]))
                    if num:
                        numbers.append(num)
        results.append(check_uradori_tansaku(body, numbers, len(need)))

    # U-9 具体値の格上げ禁止
    # 旧実装は「備考に『未到達』の3文字があるか」だけを見ていたので、両方向に壊れていた:
    #   (a) 数値を含まない主張で、引用URLが403だった経緯を備考に正直に書いた行を違反にした
    #   (b) 本当に格上げしている行でも、備考の語を「到達不能」等に言い換えるだけで違反が消えた
    # 原典(daicho-format.md:40)の禁止事項は「原文に到達していないのに条件付きへ格上げすること」。
    # **原文に到達していれば逐語/要旨が書ける**ので、語彙ではなく逐語の有無で見る。
    with guard(results, "U-9"):
        r = Result("U-9", *rule_meta("U-9"))
        # ★段2以降この枝は到達不能である。台帳本体は「必須概念のすべてに単射な列割当が
        #   存在する」ときに限り本体を名乗れる(is_ledger_body)ので、本体が取れた時点で
        #   判定・リンク・主張は必ず割り当たっている。根拠の常設テスト= E-2。
        #   ★消していないのは防御のためであり、必須概念を変えたら E-2 が落ちてここが生き返る。
        if idx["判定"] is None:
            skip_as(r, "判定列が無い", "missing_input", what="判定列", supplier="納品物")
        elif idx["逐語"] is None:
            _st, _in = missing_column_state("逐語", level)
            skip_as(r, lack_note("要旨/逐語", {1: "任意。逐語が無いと格上げの当否を機械では見られない",
                                           2: "必須 — U-3 で違反として報告済み",
                                           3: "必須 — U-3 で違反として報告済み"}), _st, **_in)
        else:
            cnt = 0
            for lineno, row in rows:
                if norm_uradori_hantei(cell(row, idx["判定"])) != "条件付き裏付け":
                    continue
                cnt += 1
                # URLは伏せてから見る。**主張の中に引用元URLを埋めて書く実運用があり、
                # URL中の数字(例 /tokusan/1.html)を「具体値」と誤読すると、
                # 数値を主張していない行を弾いてしまう**(実在台帳 iteration-2/R1-retry #3 で踏んだ)。
                biko = mask_noise(cell(row, idx["備考"])) if idx["備考"] is not None else ""
                link = cell(row, idx["リンク"]) if idx["リンク"] is not None else ""
                shucho = mask_noise(cell(row, idx["主張"])) if idx["主張"] is not None else ""
                # (A) 語彙に頼らない検査: 原文の根拠が1文字も無い条件付きは格上げである
                if is_empty(cell(row, idx["逐語"])):
                    r.fail(lineno, "条件付き裏付けなのに原文の逐語・要旨が空 — "
                                   "原文に到達していない主張を条件付きに格上げしない(具体値の格上げ禁止)")
                    continue
                # (B) 逐語があっても、二次から採った逐語を貼れば(A)はすり抜ける。
                #     原典の但し書きは「具体値・数値」に範囲を限っているので、その条件で見る。
                #     アーカイブで確認した行は daicho-format.md が認めた正規の条件付きなので除く。
                if (GUTAICHI.search(shucho) and MITOTATSU_WORDS.search(biko)
                        and not ARCHIVE_WORDS.search(biko) and not ARCHIVE_HOSTS.search(link)):
                    r.fail(lineno, "具体値の主張なのに、備考が原文へ到達できていないと述べている — "
                                   "方向性が二次で支持されても条件付きに格上げせず、未到達/未確認に倒す")
            if r.status == "ok":
                r.ok_note("条件付き裏付け %d 行すべてに原文の逐語・要旨あり"
                          "(備考の語による到達判定は網羅ではない。逐語の出所は目視で確認すること)" % cnt)
        results.append(r)

    # U-10 条件付き裏付けは備考に条件
    with guard(results, "U-10"):
        r = Result("U-10", *rule_meta("U-10"))
        # ★段2以降この枝は到達不能である。台帳本体は「必須概念のすべてに単射な列割当が
        #   存在する」ときに限り本体を名乗れる(is_ledger_body)ので、本体が取れた時点で
        #   判定・リンク・主張は必ず割り当たっている。根拠の常設テスト= E-2。
        #   ★消していないのは防御のためであり、必須概念を変えたら E-2 が落ちてここが生き返る。
        if idx["判定"] is None:
            skip_as(r, "判定列が無い", "missing_input", what="判定列", supplier="納品物")
        elif idx["備考"] is None:
            _st, _in = missing_column_state("備考", level)
            skip_as(r, lack_note("備考", {1: "任意", 2: "推奨",
                                      3: "必須 — U-3 で違反として報告済み"}), _st, **_in)
        else:
            cnt = 0
            for lineno, row in rows:
                if norm_uradori_hantei(cell(row, idx["判定"])) == "条件付き裏付け":
                    cnt += 1
                    if is_empty(cell(row, idx["備考"])):
                        r.fail(lineno, "条件付き裏付けなのに備考が空 — 何が条件かを備考に必ず書く")
            if r.status == "ok":
                r.ok_note("条件付き裏付け %d 行すべてに備考あり" % cnt)
        results.append(r)

    # U-11 反証は逐語
    with guard(results, "U-11"):
        r = Result("U-11", *rule_meta("U-11"))
        # ★段2以降この枝は到達不能である。台帳本体は「必須概念のすべてに単射な列割当が
        #   存在する」ときに限り本体を名乗れる(is_ledger_body)ので、本体が取れた時点で
        #   判定・リンク・主張は必ず割り当たっている。根拠の常設テスト= E-2。
        #   ★消していないのは防御のためであり、必須概念を変えたら E-2 が落ちてここが生き返る。
        if idx["判定"] is None:
            skip_as(r, "判定列が無い", "missing_input", what="判定列", supplier="納品物")
        elif idx["逐語"] is None:
            # 水準①の必須列だけで表を組むと逐語を書く欄が無くなり、かつて検査ごと外れていた。
            # そのため「欄を作らないほうが通る」という逆向きの誘導がかかっていた。
            # 反証の逐語は本文修正を求める根拠なので、全水準で必須(daicho-format.md:34)。
            hansho_lines = [ln for ln, v in hantei_vals if v == "反証"]
            if hansho_lines:
                for ln in hansho_lines:
                    r.fail(ln, "反証の行があるのに要旨/逐語列が無い — "
                               "矛盾箇所の逐語は全水準で必須。列を立てて逐語を書く")
            else:
                # 反証の行が0件=対象0件。★「全行合格」ではないので clean(targets=0) で記録する
                skip_as(r, lack_note("要旨/逐語", {1: "任意(反証の行が無いため)",
                                               2: "必須 — U-3 で違反として報告済み",
                                               3: "必須 — U-3 で違反として報告済み"}),
                        "clean", scanned=len(rows), targets=0)
        else:
            cnt = 0
            for lineno, row in rows:
                if norm_uradori_hantei(cell(row, idx["判定"])) == "反証":
                    cnt += 1
                    if is_empty(cell(row, idx["逐語"])):
                        r.fail(lineno, "反証なのに逐語が空 — 矛盾箇所の逐語を必ず添える")
            if r.status == "ok":
                r.ok_note("反証 %d 行すべてに逐語あり" % cnt)
        results.append(r)

    # U-12 アクセス日 —— 必須かどうかも水準表から引く(条件に書き下さない)
    with guard(results, "U-12"):
        if col_req("アクセス日").get(level) == "必須":
            results.append(check_date_column("U-12", rows, idx["アクセス日"], True, "水準③=必須"))
        else:
            rr = check_date_column("U-12", rows, idx["アクセス日"], False,
                                   "水準%s=推奨のため空欄は違反にしない" % (level_raw or "不明"),
                                   absent=missing_column_state("アクセス日", level))
            if rr.status == "ok" and idx["アクセス日"] is not None:
                rr.note += "(書式のみ照合)"
            results.append(rr)

    # U-13 アーカイブ
    with guard(results, "U-13"):
        r = Result("U-13", *rule_meta("U-13"))
        # ★段2以降この枝は到達不能である。台帳本体は「必須概念のすべてに単射な列割当が
        #   存在する」ときに限り本体を名乗れる(is_ledger_body)ので、本体が取れた時点で
        #   判定・リンク・主張は必ず割り当たっている。根拠の常設テスト= E-2。
        #   ★消していないのは防御のためであり、必須概念を変えたら E-2 が落ちてここが生き返る。
        if idx["リンク"] is None or idx["判定"] is None:
            skip_as(r, "リンク列または判定列が無い", "missing_input",
                    what="リンク列または判定列", supplier="納品物")
        else:
            cnt = 0
            for lineno, row in rows:
                link = cell(row, idx["リンク"])
                if ARCHIVE_HOSTS.search(link):
                    cnt += 1
                    if norm_uradori_hantei(cell(row, idx["判定"])) == "裏付け":
                        r.fail(lineno, "アーカイブのみのソースで判定=裏付け — 条件付き裏付け止まりにする")
            if r.status == "ok":
                r.ok_note("既知のアーカイブ提供者に該当する行 %d 件"
                          "(提供者リストは網羅ではない。該当しない保存サービスは目視で確認すること)" % cnt)
        results.append(r)

    # U-15 水準③: 裏付け行の逐語
    # 水準③は「一次必須+逐語引用+アクセス日」(SKILL.md:26)だが、行単位で逐語の充填を見る規則が
    # U-11(反証の行だけ)しか無く、**逐語が1つも書かれていない提出級の台帳が全項目合格していた**。
    # 原文に到達していない判定(未確認・未到達)は逐語を書けないので対象から外す。
    # 条件付き裏付けは U-9 が、反証は U-11 が、いずれも全水準で見る(役割分担)。
    with guard(results, "U-15"):
        r = Result("U-15", *rule_meta("U-15"))
        if level != 3:
            # ★原典は水準表の「要旨/逐語」の行。COL:逐語(URADORI_COL_REQ)と**同じ行**なので鍵を共用する
            skip_as(r, "水準%s(逐語の全行必須は水準③の要件)" % (level_raw or "不明"),
                    "not_applicable",
                    origin=origin_at("COL:逐語"))
        elif idx["判定"] is None or idx["逐語"] is None:
            # 段3: 判定は台帳本体の必須概念なので実質「逐語列が無い」。水準③では原典が必須と定める。
            _st, _in = missing_column_state("逐語", level)
            skip_as(r, "判定列または要旨/逐語列が無い(U-3 で報告済み)", _st, **_in)
        else:
            cnt = 0
            for lineno, row in rows:
                if norm_uradori_hantei(cell(row, idx["判定"])) == "裏付け":
                    cnt += 1
                    if is_empty(cell(row, idx["逐語"])):
                        r.fail(lineno, "水準③の裏付けなのに逐語が空 — 原文からの逐語引用を必ず添える")
            if r.status == "ok":
                r.ok_note("裏付け %d 行すべてに逐語あり" % cnt)
        results.append(r)

    # U-16 水準③: 一次ソース必須の実体化
    # 「水準③は一次必須」(SKILL.md:26 / source-hierarchy.md:12)と「備考に一次・二次を書く」
    # (source-hierarchy.md:27)は原典にあるのに、備考の中身を見る規則が1つも無かった。
    # 全行を二次で固めた提出級の台帳も、格付けを全部消した台帳も、違反0で通っていた。
    # 格付けの**内容の妥当性**は人間の判断なので機械では決めない(規則表の原則3)。
    with guard(results, "U-16"):
        r = Result("U-16", *rule_meta("U-16"))
        if level != 3:
            skip_as(r, "水準%s(一次必須は水準③の要件。②は一次優先・①は二次可)" % (level_raw or "不明"),
                    "not_applicable",
                    origin=origin_at("SK:U-16:水準①②は一次必須でない"))
        elif idx["判定"] is None or idx["備考"] is None:
            # 段3: 判定は必須概念なので実質「備考列が無い」。水準③では原典が必須と定める。
            _st, _in = missing_column_state("備考", level)
            skip_as(r, "判定列または備考列が無い(U-3 で報告済み)", _st, **_in)
        else:
            cnt = miss = 0
            for lineno, row in rows:
                if norm_uradori_hantei(cell(row, idx["判定"])) != "裏付け":
                    continue
                cnt += 1
                b = cell(row, idx["備考"])
                if "一次" in b:
                    continue                      # 「一次(自己申告)」等の既存の書き方もここで通る
                if "二次" in b or "三次" in b:
                    r.fail(lineno, "水準③の裏付けなのに備考の格付けが一次でない — "
                                   "一次に到達できないなら代替探索の上「未到達」で残す")
                else:
                    miss += 1
                    r.gray(lineno, "水準③の裏付けだが備考に一次/二次の格付けが無い — 目視で確認すること")
            if r.status == "ok":
                r.ok_note("裏付け %d 行すべてに「一次」の格付けあり" % cnt)
            elif r.status == "gray" and miss:
                r.note = "格付けの内容の妥当性は機械では判定しない(規則表の原則3)"
        results.append(r)

    # U-17 到達範囲
    # 抄録しか読めなかった行と本文を読み切った行が、台帳上どちらも同じ「裏付け」になっていた。
    # 下流の ronbun-shippitsu は「裏付け」を断定してよいと処理するので、抄録の一文を根拠にした主張が
    # 本文を読み切った主張と同じ強さで論文に載る。姉妹スキル bunken は同じ軸を「精読」列で持っている。
    with guard(results, "U-17"):
        r = Result("U-17", *rule_meta("U-17"))
        todatsu_i = idx["到達範囲"]
        if level == 1:
            skip_as(r, "水準①(到達範囲の記載は水準②で推奨・③で必須)",
                    "not_applicable",
                    origin=origin_at("SK:U-17:到達範囲は水準①では任意"))
        # ★段2以降この枝は到達不能である。台帳本体は「必須概念のすべてに単射な列割当が
        #   存在する」ときに限り本体を名乗れる(is_ledger_body)ので、本体が取れた時点で
        #   判定・リンク・主張は必ず割り当たっている。根拠の常設テスト= E-2。
        #   ★消していないのは防御のためであり、必須概念を変えたら E-2 が落ちてここが生き返る。
        elif idx["判定"] is None:
            skip_as(r, "判定列が無い", "missing_input", what="判定列", supplier="納品物")
        elif todatsu_i is None:
            # 列が無い台帳をここで違反にすると既存の台帳を一斉に止めるので、要目視に留める。
            # ただし**「合格」には数えない**(検査していないものを合格として数えないため)。
            r.gray(None, "到達範囲の列が無い — 抄録どまりの資料を「裏付け」にしていないか目視で確認すること"
                         "(水準%s では%s)" % (level_raw or "不明", "必須" if level == 3 else "推奨"))
        else:
            cnt = 0
            for lineno, row in rows:
                h = norm_uradori_hantei(cell(row, idx["判定"]))
                if h not in ("裏付け", "条件付き裏付け"):
                    continue                       # 原典に到達していない行は対象外
                cnt += 1
                v = cell(row, todatsu_i).replace("*", "").strip()
                if is_empty(v):
                    r.fail(lineno, "判定=%s なのに到達範囲が空 — どこまで読んだか(%s)を書く"
                           % (h, " / ".join(URADORI_TOTATSU)))
                elif v not in URADORI_TOTATSU and v not in BUNKEN_SEIDOKU:
                    r.fail(lineno, "到達範囲「%s」は2語(%s)に無い" % (v, " / ".join(URADORI_TOTATSU)))
            if r.status == "ok":
                r.ok_note("裏付け・条件付き裏付け %d 行すべてに到達範囲あり" % cnt)
        results.append(r)

    # U-18 対象範囲の実体(受領と抽出)
    with guard(results, "U-18"):
        head40 = "\n".join(body[:40])
        zen = bool(re.search(r"対象範囲\s*\**\s*[:：|｜]\s*\**\s*[^\n]*全", head40))
        results.append(check_uradori_jittai(body, tables, rows, zen))

    # U-19 格付けの宣言とリンクの内部矛盾
    guarded(results, "U-19", lambda: check_uradori_kakuzuke(rows, idx, level))

    # U-14 「提出可」
    guarded(results, "U-14", lambda: check_teishutsu(body, [v for _l, v in hantei_vals]))

    # U-21 段階A-3: その申告が**納品物に載ったか**。★U-20(届くか)とは別の検査である。
    #   ★**U-5 の後・門番の前**に置く —— 申告文が U-20 と U-5 の結果を読むためである。
    guarded(results, "U-21",
            lambda: check_stage_a_embedded("U-21", "uradori", lines, results,
                                           max([ln for ln, _r in rows], default=0)))

    # U-23 段階C-2: その申告が**納品物に載ったか**。★U-22(在るか)とは別の検査である。
    #   ★**U-22 の後・門番の前**に置く —— 申告文が U-22 の結果を読むためである。
    guarded(results, "U-23",
            lambda: check_stage_c_embedded("U-23", "uradori", lines, results,
                                           max([ln for ln, _r in rows], default=0)))

    # U-24 コードの囲み(C-5・2026-10-05)。★門番の前に置く —— 門番が ▲ を数えるためである。
    guarded(results, "U-24", lambda: check_fence_closed("U-24", lines))

    # U-25・U-26 全角の縦棒・文字コード(2026-10-05)。★門番の前に置く —— 門番が ▲ を数えるためである。
    guarded(results, "U-25", lambda: check_fullwidth_table("U-25", body))
    guarded(results, "U-26", lambda: check_utf8("U-26", raw, data))

    # U-0 門番(最後に置く。ここまでの結果に ▲ が残っていれば違反を立てる)
    guarded(results, "U-0", lambda: check_uradori_kanmon(results, body, tables))

    return results, level_raw


# 判定サマリーの件数行を読む。旧実装が壊れていた原因は3つあった:
#   (a) 「裏付け」の式が「条件付き裏付け」にも一致し、条件付きを先に書くと数を取り違えた
#       → **正しい台帳に違反を出し、書き手に正しい台帳を壊す方向の修正をさせていた**
#   (b) 区切りが空白しか読めず、コロン・太字・全角数字・表形式で5種そろわなくなった
#   (c) 見出しからの8行窓の外に件数行が出ると読めなかった
SUMMARY_LABELS = (
    ("裏付け",         r"(?<!条件付き)(?<!条件付)裏付け"),
    ("条件付き裏付け", r"条件付き?裏付け|条件付き"),
    ("反証",           r"反証"),
    ("未確認",         r"未確認"),
    ("未到達",         r"未到達"),
)
SUMMARY_SEP = r"[ \t　|｜:：=＝]*"
ZEN_DIGITS = str.maketrans("０１２３４５６７８９", "0123456789")


def read_summary_counts(body, sm):
    """判定サマリー見出しから次の見出しまでを見て5種の件数を読む。返り値 (件数, 行番号)。

    **所見の散文に紛れた数字を件数として拾わない**ため、判定語を3つ以上含む行だけを候補にする。
    凡例行は判定5語すべてを含むが数字を持たないので自然に落ちる。
    """
    end = len(body)
    for j in range(sm + 1, len(body)):
        if re.match(r"^#{1,4}\s", body[j].strip()):
            end = j
            break
    best, best_line = {}, None
    for i in range(sm, end):
        ln = re.sub(r"[*_`]", "", body[i]).translate(ZEN_DIGITS)
        if "凡例" in ln:
            continue
        if sum(1 for _k, lab in SUMMARY_LABELS if re.search(lab, ln)) < 3:
            continue                       # 件数行ではない散文を候補にしない
        got = {}
        for key, lab in SUMMARY_LABELS:
            m = re.search(r"(?:%s)%s(\d+)" % (lab, SUMMARY_SEP), ln)
            if m:
                got[key] = int(m.group(1))
        if len(got) > len(best):
            best, best_line = got, i + 1
    return best, best_line


URADORI_DOKUSHU = ["全文可読", "部分可読", "不可読"]
JITTAI_HEAD = re.compile(r"^#{1,4}\s*対象範囲の実体")
CHOJIRI = re.compile(r"事実主張\s*[:：]?\s*(\d+)\s*[/／]\s*台帳掲載\s*[:：]?\s*(\d+)"
                     r"\s*[/／]\s*非掲載\s*[:：]?\s*(\d+)")


def check_uradori_jittai(body, tables, rows, taisho_zenshucho):
    """U-18。**この台帳の n 件は「何分の n」なのか**を成果物に書かせる。

    F-028(拾わなかった主張は台帳に行として現れないので、半分でも「全部調べた」に見える)と
    F-044(対象文書が読めなくても止まらず、拾えた分だけで完成品が出る)は、
    どちらも同じ1つの問いへの答えなので**1つの節に畳む**(ユーザー決定 2026-08-04):
      受領 = 対象文書のうち、そもそも文字として取り出せた範囲はどこか(分母の外枠)
      抽出 = 文字にできた範囲のうち、主張として拾った/拾わなかったのはどこか(分母の内訳)
    別の節に分けると、読み手が掛け算をしないと本当の網羅率が出ない。

    **網羅は保証しない。**保証するのは「拾わなかったことが台帳に書いてある」ことだけである。
    """
    r = Result("U-18", *rule_meta("U-18"))
    sec = next((i for i, l in enumerate(body) if JITTAI_HEAD.match(l.strip())), None)
    if sec is None:
        # 節が無いこと自体を違反にすると既存の台帳を一斉に止めるので要目視に留める。
        # ただし**合格には数えない**(検査していないものを合格にしない)。
        r.gray(None, "「## 対象範囲の実体(受領と抽出)」の節が無い — "
                     "対象文書のどこまでを読み、何件の主張のうち何件を載せたのかが成果物から分からない")
        return r

    end = len(body)
    for j in range(sec + 1, len(body)):
        if re.match(r"^#{1,2}\s", body[j].strip()):
            end = j
            break
    blk = body[sec:end]
    blk_text = "\n".join(blk)
    blk_tables = parse_md_tables(blk)

    # --- 受領(対象文書を読み切れたか)
    dokushu_vals = []
    for t in blk_tables:
        i = find_col(t["header"], ["読取状況"])
        if i is None:
            continue
        for lineno, rc in t["rows"]:
            v = cell(rc, i).replace("*", "").strip()
            if not is_empty(v):
                dokushu_vals.append((sec + lineno, v))
    if not dokushu_vals:
        r.fail(sec + 1, "受領の記録が無い — 渡された資料ごとに読取状況(%s)を書く"
               % " / ".join(URADORI_DOKUSHU))
    for lineno, v in dokushu_vals:
        if v not in URADORI_DOKUSHU:
            r.fail(lineno, "読取状況「%s」は3語(%s)に無い" % (v, " / ".join(URADORI_DOKUSHU)))
    partial = [v for _l, v in dokushu_vals if v in ("部分可読", "不可読")]
    if partial and taisho_zenshucho:
        r.fail(sec + 1, "読み切れていない資料があるのに、ヘッダーの対象範囲が「全主張」を名乗っている — "
                        "読めた範囲の全主張なのか、文書全体の全主張なのかを書き分ける")

    # --- 抽出(拾った/拾わなかった)
    m = CHOJIRI.search(blk_text)
    if not m:
        r.fail(sec + 1, "抽出の帳尻が無い — 「事実主張 n / 台帳掲載 n / 非掲載 n」の1行を書く")
    else:
        total, keisai, hikeisai = (int(x) for x in m.groups())
        if total != keisai + hikeisai:
            r.fail(sec + 1, "帳尻が合わない: 事実主張 %d ≠ 台帳掲載 %d + 非掲載 %d"
                   % (total, keisai, hikeisai))
        if rows is not None and keisai != len(rows):
            r.fail(sec + 1, "台帳掲載 %d と書いてあるが、台帳本体の実行数は %d 行"
                   % (keisai, len(rows)))
        if hikeisai:
            n_hi = 0
            for t in blk_tables:
                if find_col(t["header"], ["拾わなかった", "非掲載", "不掲載"]) is not None:
                    n_hi += len(t["rows"])
            if n_hi != hikeisai:
                r.fail(sec + 1, "非掲載 %d と書いてあるが、拾わなかった主張の記録は %d 行 — "
                                "1件1行で理由つきに書く" % (hikeisai, n_hi))
    if r.status == "ok":
        r.ok_note("受領 %d 件・抽出の帳尻あり(この検査は網羅を保証しない。"
                  "保証するのは拾わなかったことが書いてあることだけ)" % len(dokushu_vals))
    return r


# 格と類型を対で宣言させる。**名乗りとホスト名の一致は判定しない**(それが誤検知の正体)。
# 機械が見るのは「書き手自身の宣言とリンクの内部矛盾」の1点だけ。
KAKUZUKE = re.compile(r"(一次|二次|三次)\s*[（(]\s*([^）)]+?)\s*[）)]")
KOKO_HOST = re.compile(r"https?://([^/\s]+)")
KOTEKI_DOMAIN = re.compile(r"\.(?:go|lg)\.jp$|^(?:go|lg)\.jp$", re.I)


def check_uradori_kakuzuke(rows, idx, level=None):
    """U-19。「一次」だけが証拠なしの裸の断定で書ける状態をやめる。

    台帳は「裏付け(緑)」には逐語・リンク・アクセス日・到達範囲という証拠欄を必ず添えさせるのに、
    格付けだけは何も要求していなかった。そこで格と類型を対で宣言させ(例 `一次(官公庁)`)、
    **書き手自身の宣言とリンクのホストが食い違っている場合だけ**を違反にする。
    発行主体名とホスト名の一致は見ない——消費者庁→cao.go.jp、論文→jstage.jst.go.jp、
    成分DB→fooddb.mext.go.jp のような正当な行を大量に誤検知するため(実測)。
    """
    r = Result("U-19", *rule_meta("U-19"))
    if idx["備考"] is None or idx["リンク"] is None:
        # 段3: リンクは台帳本体の必須概念なので、ここに来るのは実質「備考列が無い」場合である。
        #      備考の要否は水準で変わる(①任意・②推奨・③必須)ので水準表から決める。
        _st, _in = missing_column_state("備考", level)
        skip_as(r, "備考列またはリンク列が無い(格付けの宣言を読めない)", _st, **_in)
        return r
    declared = bare = 0
    for lineno, row in rows:
        biko = cell(row, idx["備考"])
        m = KAKUZUKE.search(biko)
        if not m:
            if re.search(r"(一次|二次|三次)", biko):
                bare += 1
                r.gray(lineno, "格付けが「%s」とだけ書かれていて類型が無い — "
                               "`一次(官公庁)` のように格と類型を対で書く"
                       % re.search(r"(一次|二次|三次)", biko).group(1))
            continue
        declared += 1
        kaku, ruikei = m.group(1), m.group(2)
        if kaku != "一次" or "官公庁" not in ruikei:
            continue                     # 機械が言えるのは官公庁の宣言についてだけ
        host_m = KOKO_HOST.search(cell(row, idx["リンク"]))
        if not host_m:
            continue
        host = host_m.group(1).split(":")[0]
        if not KOTEKI_DOMAIN.search(host):
            r.fail(lineno, "「一次(官公庁)」と宣言しているのに、リンクの出所 %s が"
                           "公的ドメイン(.go.jp / .lg.jp)ではない — "
                           "発行主体を確かめ直すか、格付けの宣言を実態に合わせる" % host)
    if r.status == "ok":
        r.ok_note("格と類型を対で宣言した行 %d(宣言とリンクの食い違いなし)" % declared)
    return r


def diagnose_ledger_table(body, tables, must=("判定", "リンク", "主張")):
    """台帳本体の表が取れなかった理由を切り分ける。「表が見つからない」だけでは書き手が直せない。

    ★must = その種別の台帳本体が満たすべき必須概念(段5-1 で引数にした)。
      既定は uradori の3概念なので、既存の呼び出しの出力は1文字も変わらない。
    """
    reasons = []
    zen = [i + 1 for i, l in enumerate(body) if l.count("｜") >= 2]
    if zen:
        reasons.append("全角の縦棒「｜」を2個以上含む行が %d 行ある(最初は L%d)。"
                       "Markdownの表の区切りは半角の「|」で書く" % (len(zen), zen[0]))
    sep_cell = re.compile(r":?-{2,}:?")
    for i in range(len(body) - 1):
        if body[i].count("|") < 2 or "|" not in body[i + 1]:
            continue
        cells, nxt = split_row(body[i]), split_row(body[i + 1])
        if len(cells) < 2:
            continue
        good = sum(1 for c in nxt if sep_cell.fullmatch(c.replace(" ", "")))
        if good and good < len(nxt):
            bad = [c for c in nxt if not sep_cell.fullmatch(c.replace(" ", ""))]
            reasons.append("L%d は区切り行のつもりだが %s が区切りの形(---)になっていない"
                           % (i + 2, "・".join("「%s」" % b for b in bad[:3])))
        elif good == len(nxt) and len(nxt) != len(cells):
            reasons.append("L%d の区切り行の列数が見出し行と一致しない(見出し %d 列 / 区切り %d 列)"
                           % (i + 2, len(cells), len(nxt)))
    if tables and not reasons:
        heads = [" / ".join(t["header"][:4]) for t in tables]
        reasons.append("Markdown表は %d 個あるが、%sのうち2つ以上を列に持つ表が無い"
                       "(見つかった見出し: %s)"
                       % (len(tables), "・".join(must), " ｜ ".join(heads[:3])))
    elif not reasons:
        reasons.append("Markdownの表が1つも無い(台帳本体が定義リスト・箇条書きで書かれている可能性)")
    return reasons


# ---- 段5-1(2026-08-19): 門番を【種別ごとに独立したフラグ】で繋ぐ ------------------
# ★DESIGN §6 の逐語:「B/R/H を締める。★**切り替えは種別ごとに独立したフラグにし、
#   1種別ずつ本番の納品物で通す**」。
# ★1つのフラグでまとめて繋がない理由は運用ではなく**測定**である ——
#   巻き添えを測る母数が種別ごとに違う。R系は実在の納品物が2件しか見つかっておらず、
#   母数が作れていない(DESIGN §5・§8-6)。だから R系は最後に回す。
KANMON_ON = {
    "uradori": True,     # 段3(2026-08-17)で繋いだ
    "bunken":  True,     # 段5-1(2026-08-19)
    "html":    True,     # 段5-2(2026-08-19)
    "ronbun":  True,     # ★★段5-3(2026-08-20)= この工事。**これで4種別すべてが on になった**
                         #   ★★ただし**この段の安全性は測れていない。**実在の R系納品物は
                         #     2件しか見つかっておらず(DESIGN §5 の逐語:「ronbun は実在の
                         #     納品物が2件しか見つからず母数にならないため、R系の巻き添えは
                         #     どの案も測れていない」)、巻き添えを測る母数が作れない。
                         #   ★測ったのは「型判定で ronbun と同定される .md 278件」であって
                         #     **論文原稿の集合ではない**。278件のうち新たに不合格になるのは
                         #     11本で、**11本とも納品物ではない**(他スキルの手引き・検体・作業メモ)。
                         #     ⇒ **「安全だった」と読んではいけない。母数が2件しかないだけである。**
}

# 種別 → (門番の規則ID, 画面に出す原典の鍵, 表の診断を添えるか)
# ★原典の鍵を種別ごとに分けるのは体裁ではない —— bunken の納品物の画面に uradori の SKILL.md を
#   出したら、書き手は**どこを読めば直せるのか分からない**。門番は「直し方の入口」でもある。
# 種別 → (門番の規則ID, 画面に出す原典の鍵, 画面に出す規定の要約, 表の診断を添える条件)
KANMON = {
    "uradori": ("U-0", "MSG:U-0:未検査は合格ではない",
                "未検査は合格ではない", "stuck"),
    "bunken":  ("B-0", "MSG:B-0:検査できなかった項目が残っている",
                "検査できなかった項目が残っているなら「違反が無かった」ではない", "table"),
    # ★段5-2(2026-08-19): html。**第4要素は None である** —— 診断(なぜ表として読めなかったか)は
    #   台帳の話で、html の納品物には台帳本体が無い。「表が見つからない」を html の画面に出したら
    #   書き手はどこを直せばよいのか分からなくなる。**添えないことを表で宣言する。**
    "html":    ("H-0", "MSG:H-0:検査できなかった項目が残っている",
                "検査できなかった項目が残っているなら「違反が無かった」ではない", None),
    # ★段5-3(2026-08-20): ronbun。**第4要素は html と同じく None である** ——
    #   診断(なぜ表として読めなかったか)は台帳の話で、原稿には台帳本体が無い。
    #   ★原稿で門番が拾うのは R-2 の「上付き番号を読めない」枝**だけ**であり、
    #     直し方は「本文の引用番号を上付きにする」である。表の診断を出しても案内にならない。
    "ronbun":  ("R-0", "MSG:R-0:検査できなかった項目が残っている",
                "検査できなかった項目が残っているなら「違反が無かった」ではない", None),
}

# 種別ごとの「台帳本体が満たすべき必須概念」。★診断の文言に使う(何が足りないのかを名指しするため)。
#   ★実装の述語(collect_ledger_tables の must_have_keys)と同じものを2か所に書かない ——
#   ここは**表示のための写しではなく**、呼び出しに渡している当の値を検査側が持ち回る形にする。
KANMON_MUST = {"uradori": ("判定", "リンク", "主張"), "bunken": ("書誌", "リンク", "入手状況")}
NO_LEDGER_BODY = "台帳本体の表が見つからない"

# ★★2026-08-20(ユーザーの裁定): 門番が ✕ を立てるのは**責任=納品物 の ▲ だけ**である。
#   `DESIGN.md` 柱2 の表は「納品物側だけが違反を立てる/他の3行は違反にしない」で一貫しており、
#   `crashed` だけを例外扱いする理由が無かった。⇒ 責任=**呼び出し**と**人間**も外した。
# ★**外すのは「✕ を立てること」だけである。**▲ の状態そのものは残るので `report()` が数え、
#   `main()` が **終了コード 3(合格ではない)**を返す。**「画面から消す」でも「終了コードから
#   消す」でもない** —— どちらも fail-open の一種である。
# ★下の並びは**画面に出す名札**であって判定ではない(判定は `responsibility(x) == "納品物"` 1本)。
#   ★ここに無い責任が現れても ✕ にはしないが、**顔ぶれが画面から消えないよう既定の名札で名乗る**。
#   並びを固定してあるのは、複数の責任が同時に出たときの文言の順序を毎回同じにするためである。
KANMON_BLAMELESS = (
    ("呼び出し",   "検査に必要な情報が呼び出し側から渡らなかった項目"),
    # ★★2026-08-23: 名札を「検査処理そのものが失敗した項目」から広げた。責任=チェッカーには
    #   `crashed`(処理が落ちた)だけでなく `missing_input(supplier="チェッカー")`
    #   (本スクリプトが原典どおりの記法を読めなかった。R-2 の上付き引用番号が実例)も在り、
    #   前者の名札を後者に貼ると**画面が嘘になる**(落ちてはいない)。
    ("チェッカー", "本スクリプトの側の理由で検査が終わっていない項目"),
    ("人間",       "人間の判断が要るまま残っている項目"),
)

# ★★2026-10-05(起票 `KICKOFF-kanmon-bunmen.md`): 責任=呼び出し の ▲ の文を【渡したか】で書き分ける。
#   ★上の名札「呼び出し側から渡らなかった」は、取得結果を渡したのに段の側が ▲(測れなかったものが残る)の
#     走行でも、その項目に貼られていた ⇒ 渡したものを「渡らなかった」と書く(`40-report-format.md` §2 の
#     偽の指摘の形。★読み手は「取得の指定を付け忘れた」と誤読しうる)。
#   ★「渡したか」を知っているのは、その ▲ を立てた規則だけである ⇒ 規則が `missing_input` の記録に
#     `handed=`(True= 渡されたが測り切れなかった / False= 渡されていない)を名乗る。
#   🔴★**「渡らなかった」と書いてよいのは `handed=False` を名乗った項目だけ。**★名乗っていなければ
#     「知らない」と書く(★既定は「知らない」。★同梱の照合の文の書き分け(2026-10-04)と同じ筋)。
#   ★★判定(✕/▲/○)・7状態・責任・終了コードは動かさない。★動くのは門番の文だけ。
#     ★渡されていない項目だけの走行では、文は1字も変わらない(★判定の3母集団はこの形だけを通る)。
#   ★並びは固定(渡していない → 渡した → 知らない)。★「渡していない」の名札は上の表のものを使う(書き写さない)。
KANMON_HANDED = (
    (True,  "検査に必要な情報は呼び出し側から渡されたが、測れなかったものが残っている項目"
            "(★渡し忘れではない。▲ の中身は各規則の行)"),
    (None,  "検査に必要な情報が呼び出し側から渡ったかどうかを、この門番は知らない項目"
            "(★その規則が名乗っていない。▲ の中身は各規則の行)"),
)


def caller_handed(x):
    """★その ▲ を立てた規則が名乗った「呼び出し側が渡したか」。→ True / False / None(名乗っていない)。

    ★True・False のどちらでもない値は None に倒す(★名乗っていない値を「渡していない」と読まない)。
    """
    v = x.state_info.get("handed")
    if v is True or v is False:
        return v
    return None


def caller_parts(grp, label):
    """責任=呼び出し の ▲ を【渡したか】で (名札, 項目の並び) の組に分ける。★空の組は出さない。

    ★「渡していない」の名札は呼び出し元が渡す(=上の名札の表のもの)。★並びは 渡していない → 渡した → 知らない。
    """
    out = []
    for handed, lb in ((False, label),) + KANMON_HANDED:
        sub = [x for x in grp if caller_handed(x) is handed]
        if sub:
            out.append((lb, sub))
    return out


def blameless_note(blocked):
    """責任=納品物 **以外**の ▲ を、責任ごとに1文ずつ名乗る文字列を作る。★0件なら空文字。

    ★**画面から消さない。**違反にしないだけで、残った ▲ の顔ぶれと「合格ではない」ことは出す。
    ★空文字のときは1行も増えない(0件のときの出力を1バイトも変えないため)。
    ★名札の無い責任も**必ず名乗る** —— 名乗らなければ、責任の語彙が増えた日に
      その ▲ が**画面から静かに消える**(この体系がいちばん嫌う型)。
    ★2026-10-05: 責任=呼び出し だけは、名札を【渡したか】で書き分ける(→ `KANMON_HANDED` の註)。
      ★組が1つなら文は旧版と1字も同じ。★組が複数なら「、」で繋ぎ、尾(責任は…終了コードは 3)は1回。
    """
    named = [who for who, _label in KANMON_BLAMELESS]
    rest = sorted({responsibility(x) for x in blocked} - set(named) - {"納品物"})
    out = []
    for who in named + rest:
        grp = [x for x in blocked if responsibility(x) == who]
        if not grp:
            continue
        label = dict(KANMON_BLAMELESS).get(who, "責任が「%s」の検査不能項目" % who)
        parts = [(label, grp)]
        if who == "呼び出し":
            parts = caller_parts(grp, label)
        # ★★2026-08-23: 「ただし ▲ は残るので」と書いていたが、記号が「―」のまま
        #   状態だけが未実行の項目もここに来る(`skip_as` 経路)。**記号を根拠にしない。**
        out.append("%s— "
                   "**責任は%sであって納品物ではない**ので違反にはしない。"
                   "ただし**検査は終わっていない**ので**終了コードは 3(合格ではない)**"
                   % ("、".join("★%sが %d 件ある(%s)" % (lb, len(sub), "・".join(x.rule_id for x in sub))
                               for lb, sub in parts), who))
    return " ／ ".join(out)


# ★2026-08-19(段5-1): ここには KANMON_EXCLUDED(門番が拾わないと決めてある枝の台帳)が在った。
#   2026-08-04 のユーザー決定「bunken-daicho は現状維持(未検査のまま)」を実装で守る仕掛けである。
#   ★**機構ごと撤去した。**決定が挙げた理由が消滅し、除外すべき枝が1つも無くなったのに
#     空の台帳だけを残すと、次に誰かが「決定なしで」枝を足せる場所になる(既定を開ける形)。
#   戻すときは git revert でこの工事ごと戻すこと —— 決定は1コミットに閉じてある。


def check_uradori_kanmon(results, body, tables):
    """U-0 門番(uradori)。★中身は種別共通の `check_kanmon` に移した(段5-1)。"""
    return check_kanmon("uradori", results, body, tables)


def check_kanmon(kind, results, body, tables):
    """門番。**書き手が直せる未検査が1つでも残っていれば違反にする。**

    終了コードの共通ロジック(report / main)には触らない。
    ここで ✕ を立てれば、既存の「違反があれば終了コード1」がそのまま働く。

    ★段3(2026-08-17): **記号が「▲」かどうかではなく「誰が直せるか」で拾う**(柱2の中心)。
      段1が実測したとおり、記号が「―」の項目にも「検査しなくてよかった」ではないものが混じる。
      責任の所在が**納品物**のものは、書き手が書式を直せば検査できるようになる項目である。
      ★逆に、責任が**規定**(要否表が推奨・任意と定める列の不在)・**人間**(要目視)・
      **呼び出し**・**チェッカー**のものは拾わない —— 拾えば書き手に直せないもので
      納品を止める**逆向きの事故**になる。
      分類そのものは常設テスト E 部が固定している(誤ると落ちる)。
    ★段5-1(2026-08-19): 種別ごとの独立したフラグ `KANMON_ON` で繋ぐ。
      ★**off の種別ではこの関数は1度も呼ばれず、規則そのものが出力に現れない。**
      「繋いだが何もしない」ではなく「繋いでいない」ことが画面で分かる形にしてある。

    ★★2026-08-20(ユーザーの裁定): **責任=「チェッカー」(`crashed`)は拾わない。**
      それまでの `stuck` は `status == "blocked"` を**責任で絞らずに全部**拾っていたため、
      段6 で `crashed` が到達可能になった瞬間、**チェッカーが落ちたファイルが exit 1** になった。
      これは `DESIGN.md` 柱2 の表(「チェッカー側(`crashed`)/ 違反にしない /
      **納品物の欠陥ではない**」)と食い違う。★決め手は表のすぐ下の終了コードの定義である:
        逐語「`3`=検査が完了…★`3` は「納品してよいか」に答えず、
              「**まだ検査が終わっていない**」と答える。」
        逐語(`main()`)「`1` は**直すべきものが分かっている**」
      ⇒ `crashed` は「チェッカーが落ちて検査が終わっていない」状態そのものであり、
        **書き手に直すべきものは分かっていない**。`3` の定義に当てはまり、`1` には当てはまらない。

    ★★**衝突していたのは「拾う」と「✕ を立てる」を一体にしていた実装のほうである。**
      拾って ▲ のまま残せば `report()` が `blocked` を数え、`main()` が **終了コード 3** を返す。
      **合格(0)にはならない。**⇒ これは fail-open ではない。

    ★★★**除くのは責任=チェッカーだけである。**責任=納品物(`partial` / 供給者が
      「納品物」の `missing_input` / `Result` の `blocked()` で立てた ▲)は
      **従来どおり ✕(exit 1)**。
      ここを巻き込むと、**いま止まっている納品物が黙って通る**(=本物の fail-open を作る)。
      「▲ を全部 exit 3 にする」は誤りである。常設テスト G-3 が対照つきで固定している。

    ★★2026-08-20(ユーザーの裁定・第2弾): **除くのはチェッカーだけ「ではない」**。
      上の段落は当時の実装を正しく述べているが、**この行より下が正である** ——
      裁定は「`DESIGN.md` 柱2 の表の**残り2行も同じに扱う**」であった。
      ⇒ 責任=**呼び出し**(`missing_input(supplier="呼び出し")`)と、責任=**人間**
        (`needs_human` / 原典を失った枝)の ▲ も**拾わない**。
      理由は3つで、どれも上の裁定と同じ筋である:
        ① 表は3行とも「違反にしない」で一貫しており、`crashed` だけを例外にする理由が無い
        ② どちらも**書き手には直せない**(呼び出し側=引数の問題 / 原典喪失=環境の問題)。
           ✕ を立てるのは、表自身が H-6 について警告した**逆向きの事故**そのものである
        ③ 終了コードの定義に照らすと、両方とも「まだ検査が終わっていない」(=`3`)であって
           「直すべきものが分かっている」(=`1`)ではない
      ★**残るのは「責任=納品物 の ▲ だけを ✕ にする」という1本の規則**である。
        判定は `responsibility(x) == "納品物"` の1行に閉じてあり、責任の語彙が増えても
        **既定で ✕ を立てない**(だが ▲ は残るので終了コードは 3。**合格にはならない**)。
      ★★当時この2行を触らなかったのは「現に起きていないから」であった ——
        呼び出し側の ▲ は `missing_input()` を誰も呼んでいないため、原典喪失の ▲ は
        **門番より後(`inspect_file` の `origin_gate`)で立つため門番が見ていない**ためである。
        ⇒ ★後者は**順序に頼っていた**。順序が変われば ✕ になる状態だった。
          いまは**順序に依存しない** —— 先に倒しても後で倒しても、責任=人間 は拾わない。
          常設テスト E-18 が**両方の順序を現に走らせて**同じ判定になることを固定している。

    ★★この註の書き方には理由があった(次に書き足す者への申し送り)——
      変異ハーネスの演算子は**行の字面**で母集合を作っていたため、註の中に `supplier=`+"納品物" や
      ドット付きの `blocked(` をそのまま書くと、**註そのものが変異の的になり等価変異が増えた**
      (実測: 一度そう書いて responsibility-mutate 36→37・status-mutate 9→10 になった)。
      等価変異は殺せないので**生存が増え、殺傷率だけが薄まる**。⇒ 当時はそれを避けて書いていた。
    ★★2026-08-20: **この縛りはもう無い。**上の実測は「測定器が docstring の行まで
      母集合に入れていた」という**測定器の側の穴**が原因だった。`mutation_harness.py` を
      AST で直し、docstring の行を母集合から除外したので、いまは註にこれらの字面を書いても
      母集合は動かない(実測で確認済み。対照として同じ字面を**コードに**書けば動く)。
      ⇒ **文章の書き方を測定器に合わせる必要はもう無い。**この段落を残しているのは経緯を
      伝えるためであり、これから書き足す者はここに書かれた縛りを守らなくてよい。
    """
    rule_id, msg_key, msg_gist, diag_when = KANMON[kind]
    r = Result(rule_id, *rule_meta(rule_id))
    # ★★2026-08-23: 記号(▲)ではなく**状態**で拾う。`skip_as` は記号を「―」に据え置くので、
    #   記号で拾うと「―だが検査は終わっていない」項目が門番の視野から丸ごと落ちる
    #   (落ちていた実例と根拠は `unexecuted()` の註)。
    blocked = unexecuted(results)
    # ★責任で2つに分ける。**記号(▲)は同じでも意味が正反対**である ——
    #   「納品物の形が原因で読めなかった」は書き手が直せるが、それ以外は直せない。
    # ★★**✕ を立てるのは責任=納品物 の ▲ だけ**である(2026-08-20 のユーザーの裁定)。
    #   ★「▲ を全部 exit 3 にする」ではない —— 納品物の ▲ を巻き込めば、いま止まっている
    #     納品物が黙って通る(=本物の fail-open)。常設テスト G-3・E-18 が対照つきで固定している。
    # ★2つに分けたままにするのは**文言のため**である —— 記号が ▲ のものと「―」のものでは
    #   書き手への案内が違う(前者は「実行できなかった」、後者は「書式を直せば検査できる」)。
    #   ★判定はどちらも同じ(✕)なので、分け方を間違えても fail-open にはならない。
    stuck = [x for x in blocked if x.status == "blocked" and responsibility(x) == "納品物"]
    latent = [x for x in blocked if x.status != "blocked" and responsibility(x) == "納品物"]
    # ★★2026-08-23: 責任=納品物 **以外**の顔ぶれも、記号が「―」のものまで含めて名乗る。
    #   ここが「検査不能の項目なし」と嘘をついていた当の場所である ——
    #   R-2 が自ら「責任=チェッカー」と画面に出しているのに、門番は ○ で
    #   「検査不能の項目なし(19 規則すべてを実行できた)」と表示していた。
    crash_note = blameless_note(blocked)
    if not stuck and not latent:
        r.ok_note(crash_note or
                  "検査不能の項目なし(%d 規則すべてを実行できた、または規定・目視の担当)"
                  % len(results))
        return r
    if stuck:
        r.fail(None, "検査を実行できなかった項目が %d 件ある(%s)— "
                     "「検査できなかった」は「合格」ではない"
               % (len(stuck), "・".join(x.rule_id for x in stuck)))
    if latent:
        # ★この文言は**画面に出る**。原典の位置は逐語から導出する(手書きだと用語集の改稿で嘘になる)
        r.fail(None, "未検査(―)のうち %d 件は納品物の書式を直せば検査できる項目である(%s)— "
                     "規定による対象外ではない(%s %s)"
               % (len(latent), "・".join("%s: %s" % (x.rule_id, x.note.split("—")[-1].strip()[:40])
                                         for x in latent),
                  origin_short(msg_key), msg_gist))
    # ★違反を立てた場合も、責任=納品物 以外の ▲ が在ればその事実は画面に出す。
    #   ★★✕ の陰で黙らせない —— 「✕ が出たファイルでは書き手に直せない ▲ が消える」は
    #     fail-open の一種である(常設テスト E-18 の「混在」が対照つきで固定している)。
    #   ★空なら1行も増えない(0件のときの出力を1バイトも変えないため)。
    r.note = crash_note
    # ★「表が見つからない」だけでは書き手が直せない。**なぜ表として読めなかったか**を添える。
    #   ★添える条件を種別ごとに分けるのは、uradori の出力を1文字も動かさないためである
    #   (uradori は従来どおり ▲ が出たときだけ診断を添える)。
    if (diag_when == "stuck" and stuck) or (
            diag_when == "table"
            and any(NO_LEDGER_BODY in (x.note or "") for x in stuck + latent)):
        for msg in diagnose_ledger_table(body, tables, KANMON_MUST[kind]):
            r.fail(None, msg)
    return r


# ★探索記録の節の見出し。★U-6 と U-8 が同じ1つを使う(★同じ知識を2か所に書くと、片方だけが古くなる)。
TANSAKU_HEADING = re.compile(r"^#{1,4}\s*探索記録")

# ★★2026-10-05(起票 `KICKOFF-u6-nokori.md`・ユーザー裁定 2026-10-05「(イ) 別の見出しをはさまない」)。
#   ★判定サマリーと凡例(判定)の間に、**サマリーの見出しと同じ大きさ以上の見出し**(# の数が同じか少ない)が在り、
#     その見出しが「所見」「凡例」で始まらなければ ✕。★段落・箇条書き・サマリーより小さい見出しは自由。
#     ★原典 `run-uradori/SKILL.md` は「判定サマリー(…)と所見、その直後に**凡例**」と書き、所見を挟むことは許している。
#   ★見出しは Markdown の ATX 見出し(行頭の # が1〜6個で、その直後が空白か行末)だけを数える ——
#     「#1 は…」のように # の直後に空白の無い行は Markdown では見出しにならない(★偽の指摘を出さない向き)。
#   🔴★**見逃す形**(★裁定が承知している): 見出しを付けずに段落・箇条書きで別の話を挟む形 /
#     下線(=== / ---)で書いた見出し。★合格の文に毎回名指しで出す(`00-principles.md` §12)。
#   ★探索記録の見出しは下の旧の文(間に「探索記録」の節がある)で出す。★同じ行を2度数えない。
U6_ATX_HEADING = re.compile(r"^(#{1,6})(?:[ \t]+(.*?))?[ \t]*$")
U6_ALLOWED_HEADS = ("所見", "凡例")

# ★★F-026(b)(2026-10-05): 凡例(判定)を【段落】で読む。★旧は最初の1行しか読まず、凡例を原稿の上で
#   2行に折り返すと、2行目の語を「載っていない」と出していた(偽の指摘)。★Markdown では空行を挟まない
#   改行は同じ段落(表示では1行)である。
#   ★段落の終わり= 空行・見出し・箇条・表・引用・水平線・別の凡例の行(★「凡例」を含む行。凡例(分類)の行など)。
U6_PARA_STOP = re.compile(r"^(?:#{1,6}(?:[ \t]|$)|[-*+][ \t]|\d+[.)][ \t]|\||>|(?:-{3,}|\*{3,}|_{3,})$)")

# ★★F-045・F-026(a)(2026-10-05): 5語は【「語=意味」の形】で読む。
#   ★原典= `run-uradori/SKILL.md`「その直後に**凡例**(判定・分類の一行定義。書式はdaicho-format.md)」と、
#     その書式の行 `**凡例(判定)**: 裏付け=原文が主張を直接支持 / …`(`run-uradori/references/daicho-format.md`)。
#     ⇒ 凡例は【定義】であり、書式は「語=意味」を「 / 」で並べた形である。
#   ★F-045: 旧は行への部分一致だけを見ていたので、「条件付き裏付け」が在れば「裏付け」も在ることになった。
#     ⇒ 語の前が区切り(行頭・空白・/・:・太字の記号・括弧・読点など)のときだけ、その語と数える。
#   ★F-026(a): 旧は語が在れば定義が無くても合格だった。⇒ 「語=」の = の右(次の / まで)が空、または = が無ければ、定義が無い。
#   ★= は全角(＝)でもよい。★定義の中身(意味が正しいか)は照合しない(★合格の文に毎回出す)。
U6_TERM_BOUNDARY = frozenset(" \t/／:：*_|、,，(（「『・" + chr(0x3000))
U6_TERM_TAIL = re.compile(r"[*_」』\"']*[ \t]*[=＝]")


def u6_heading(line):
    """ATX 見出しなら (# の数, 見出しの文字) を返す。見出しでなければ None。★閉じの # は外す。"""
    m = U6_ATX_HEADING.match(line.strip())
    if m is None:
        return None
    return len(m.group(1)), re.sub(r"[ \t]+#+$", "", m.group(2) or "")


def u6_other_heads(body, sm, leg_i):
    """サマリーと凡例の間の、挟んではならない見出し [(行番号0始まり, 見出しの行)]。

    ★サマリーより小さい見出し・「所見」「凡例」で始まる見出し・探索記録の見出し(別の文で出す)は入れない。
    ★サマリーの大きさは、サマリーを見つけた行の頭の # の数で取る(★U-5 は # の直後の空白を求めない)。
    """
    top = len(re.match(r"#*", body[sm].strip()).group(0))
    out = []
    for k in range(sm + 1, leg_i):
        h = u6_heading(body[k])
        if h is None or TANSAKU_HEADING.match(body[k].strip()):
            continue
        if h[0] <= top and not re.sub(r"[*_\s]", "", h[1]).startswith(U6_ALLOWED_HEADS):
            out.append((k, body[k].strip()))
    return out


def u6_legend_lines(body, leg_i):
    """凡例(判定)の段落の行番号(0始まり)の並び。"""
    out = [leg_i]
    for k in range(leg_i + 1, len(body)):
        s = body[k].strip()
        if not s or "凡例" in s or U6_PARA_STOP.match(s):
            break
        out.append(k)
    return out


def u6_term_state(text, w):
    """凡例の段落の中の語 w の状態: 定義あり / 定義が空 / 定義なし / 部分(他の語の一部としてだけ在る)/ 無い。"""
    starts = [m.end() for m in re.finditer(re.escape(w), text)
              if m.start() == 0 or text[m.start() - 1] in U6_TERM_BOUNDARY]
    defs = []
    for e in starts:
        t = U6_TERM_TAIL.match(text, e)
        if t is not None:
            rest = re.split(r"[/／]", text[t.end():], maxsplit=1)[0]
            defs.append(re.sub(r"[\s*_]", "", rest) != "")
    if any(defs):
        return "定義あり"
    if defs:
        return "定義が空"
    if starts:
        return "定義なし"
    if w in text:
        return "部分"
    return "無い"


def u6_part_note(part, text):
    """「他の語の一部としてだけ在る」語の註(★F-045)。★0件なら空文字(★旧の文に1字も足さない)。"""
    if not part:
        return ""
    out = []
    for w in part:
        cont = [v for v in URADORI_HANTEI if v != w and w in v and v in text]
        out.append("「%s」は%sの一部としてしか現れない" % (w, "・".join("「%s」" % v for v in cont) or "他の語"))
    return " ※" + "・".join(out) + "(その中の字は数えない)"


def check_uradori_legend(body, summary_line):
    r = Result("U-6", *rule_meta("U-6"))
    leg_i = next((i for i, l in enumerate(body) if "凡例" in l and "判定" in l), None)
    if leg_i is None:
        r.fail(None, "「**凡例(判定)**」の行が無い(判定サマリーの直後に必須)")
        return r
    para = u6_legend_lines(body, leg_i)
    text = " ".join(body[k] for k in para)
    # ★段落が1行のときは、旧の文と1字も変えない(★行番号の欄が既にその行を指している)。
    where = "" if len(para) == 1 else "(L%d〜L%d の段落)" % (para[0] + 1, para[-1] + 1)
    states = dict((w, u6_term_state(text, w)) for w in URADORI_HANTEI)
    lack = [w for w in URADORI_HANTEI if states[w] in ("部分", "無い")]
    if lack:
        r.fail(leg_i + 1, "凡例(判定)%sに載っていない語: %s（判定5語は全て載せる）%s"
               % (where, "・".join(lack), u6_part_note([w for w in lack if states[w] == "部分"], text)))
    undef = [w for w in URADORI_HANTEI if states[w] in ("定義が空", "定義なし")]
    if undef:
        r.fail(leg_i + 1, "凡例(判定)%sに「語=意味」の定義が無い語: %s(原典の書式は「語=意味」を「 / 」で並べた一行の定義)"
               % (where, "・".join(w + ("(= の右が空)" if states[w] == "定義が空" else "") for w in undef)))
    if summary_line is not None and leg_i < summary_line:
        r.fail(leg_i + 1, "凡例が判定サマリーより前にある — サマリーの直後に置く")
    # ★2026-10-04(起票 `KICKOFF-a-nokori.md` U-6): サマリーと凡例の間に「探索記録」の節が在れば ✕。
    #   ★原典は「凡例の後に独立セクション「探索記録(再挑戦の起点)」を必ず置く」と順を定めている
    #     ⇒ 探索記録の節が間に在れば、「直後」をどう読んでも直後ではない(★凡例を台帳の一番下に置く形)。
    # ★2026-10-05(起票 `KICKOFF-u6-nokori.md`): 「直後」の残りはユーザー裁定 (イ) で決まった(→ `U6_ATX_HEADING` の註)。
    if summary_line is not None and summary_line < leg_i:
        between = [k for k in range(summary_line + 1, leg_i) if TANSAKU_HEADING.match(body[k].strip())]
        if between:
            r.fail(leg_i + 1, "凡例が判定サマリーの直後に無い — 間に「探索記録」の節がある(L%d)。"
                              "凡例はサマリーの直後に置き、探索記録はその後に置く" % (between[0] + 1))
        others = u6_other_heads(body, summary_line, leg_i)
        if others:
            r.fail(leg_i + 1, "凡例が判定サマリーの直後に無い — 間に別の節の見出し「%s」がある(L%d%s)。"
                              "サマリーと凡例の間には、所見・凡例以外の、サマリーと同じ大きさ以上の見出しを挟まない"
                   % (others[0][1], others[0][0] + 1,
                      "" if len(others) == 1 else "・ほか%d個" % (len(others) - 1)))
    if r.status == "ok":
        # ★2026-10-04: 旧文「判定5語すべて記載・サマリー直後」は、照合していない「直後」を名乗る偽の印字だった。
        #   ★照合したことだけを書き、照合しない範囲を名指す(★規則表の判定条件の欄と同じことを言う)。
        span = "" if len(para) == 1 else "(凡例は L%d〜L%d の段落として読んだ)" % (para[0] + 1, para[-1] + 1)
        if summary_line is None:
            r.ok_note("判定5語すべてに「語=意味」の定義あり%s ※判定サマリーの位置が取れていない経路"
                      "(見出しが無い・台帳本体が読めない)なので、凡例の位置は照合できない" % span)
        else:
            r.ok_note("判定5語すべてに「語=意味」の定義あり%s・判定サマリーより後で、間に「探索記録」の節も、"
                      "所見・凡例以外のサマリーと同じ大きさ以上の見出しも挟まない"
                      " ※照合しない範囲(所見のあとに挟むもの): 見出しを付けずに挟んだ段落・箇条書き / "
                      "サマリーより小さい見出し / 「#」の直後に空白の無い行・下線(=== / ---)で書いた見出し。"
                      "定義の中身(意味が正しいか)も照合しない" % span)
    return r


def check_uradori_legend_only(body):
    return check_uradori_legend(body, None)


# ---- U-24 / B-18 コードの囲みを閉じる(C-5・2026-10-05・起票 `KICKOFF-c5-fence.md`) ----------------------
# ★★ユーザー裁定(2026-10-05)「(ア) 説明書に1行足し不合格に」。★先に説明書(uradori と bunken-daicho の
#   `references/daicho-format.md`)へ「**コードの囲みは必ず閉じる**」を足してから繋いだ ——
#   ユーザー裁定1(2026-08-22)「説明書の裏づけの無い基準で納品を止めない。先に説明書の裏づけを用意する」の順番。
# ★なぜ要るか: `strip_code_fences` は閉じていない囲みの後ろを【全部】囲みの中として空にする。
#   ⇒ その後ろに書いた違反(例: 未処置が残るのに「提出可」)が、どの規則にも見えず、画面にも終了コードにも
#     出なかった(`--accounting` のときだけ1行出た)。★「点検できなかったもの」を合格にしない(`DESIGN.md` 柱2)。
# ★「ここから後ろは点検できなかった」と言える所は、点検の側が実際に空にした所と同じ所だけである。
#   ⇒ 見分けは `strip_code_fences` と【同じ字面】(`_scan_fences`。行頭の ``` / ~~~ を交互に開閉と読む)。
# ★★責任の分け方(★書き手の誤りでないものを書き手のせいにしない = 偽の指摘を出さない):
#   ・Markdown(CommonMark)の読み方 —— 開いた記号と同じ種類・同じ長さ以上の記号だけの行でだけ閉じる —— でも
#     閉じていない ⇒ 書き手が囲みを閉じれば直る。★責任= 納品物(`partial`。▲ ⇒ 門番 U-0・B-0 が ✕ ⇒ 終了コード 1)。
#     ★受理層の方針表 `UNSUPPORTED_POLICY` の `unclosed_fence` の行(partial / 納品物)と同じ扱い
#       (★表そのものは読まない。食い違えば常設テスト LD-107 が鳴る)。
#   ・Markdown では閉じているのに、字面の切り替えでは閉じていない(``` の囲みの中に ~~~ だけの行がある等)
#     ⇒ この点検プログラムの読み方の限界であって、書き手の誤りではない。★責任= チェッカー
#     (`missing_input`。▲ のまま・門番は拾わない ⇒ 終了コード 3)。
#   ★どちらも【合格にはしない】。
# ★R系(論文の原稿)には繋いでいない(★起票: 当てるかは別に決める。★今回は uradori と bunken-daicho だけ)。
FENCE_MD_OPEN = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
FENCE_MD_CLOSE = re.compile(r"^ {0,3}(`{3,}|~{3,})[ \t]*$")


def md_unclosed_fence(lines):
    """Markdown(CommonMark)の読み方で、閉じていない囲みが開いた行(1始まり)を返す。閉じていれば None。

    ★開く= 字下げ3つまでの ``` 以上か ~~~ 以上(``` の情報文字列に ` を含むものは囲みではない)。
    ★閉じる= 開いた記号と同じ種類で、同じ長さ以上の記号だけの行。★入れ物(引用・箇条)の終わりでは閉じない(見ていない)。
    """
    opened = None
    for i, ln in enumerate(lines):
        if opened is None:
            m = FENCE_MD_OPEN.match(ln)
            if m is not None and not (m.group(1)[0] == "`" and "`" in m.group(2)):
                opened = (i + 1, m.group(1)[0], len(m.group(1)))
            continue
        m = FENCE_MD_CLOSE.match(ln)
        if m is not None and m.group(1)[0] == opened[1] and len(m.group(1)) >= opened[2]:
            opened = None
    return None if opened is None else opened[0]


def check_fence_closed(rule_id, lines):
    """U-24 / B-18: コードの囲みが閉じているか。★閉じていなければ「そこから後ろは点検できなかった」と名乗る。"""
    r = Result(rule_id, *rule_meta(rule_id))
    _inside, marks, opened = _scan_fences(lines)
    if opened is None:
        r.ok_note("コードの囲みはすべて閉じている(行頭の ``` / ~~~ の行 %d 本・囲み %d 個)"
                  % (len(marks), len(marks) // 2))
        return r
    head = ("L%d で開いたコードの囲みが閉じていない — L%d から後ろ(%d 行)は点検できなかった"
            % (opened, opened, len(lines) - opened + 1))
    if md_unclosed_fence(lines) is None:
        r.blocked(head + "。★ただし Markdown の読み方では閉じている(囲みの中に、種類の違う記号か短い記号だけの行がある)"
                         "ので、書き手の誤りではない —— この点検プログラムが行頭の ``` / ~~~ を交互に開閉と読むためである"
                         "(責任=チェッカー)。**未検査であって合格ではない**")
        r.observe("missing_input", what="Markdown どおりに囲みを読む読み方", supplier="チェッカー")
        return r
    r.blocked(head + "。囲みを閉じれば点検できる(原典: コードの囲みは必ず閉じる)。"
                     "★後ろに在る見出し・表・凡例を「無い」と出す規則があれば、囲みの中として読んだためである。"
                     "**未検査であって合格ではない**")
    r.observe("partial", read=opened - 1, total=len(lines))
    return r


# ---- U-25 / B-19 全角の縦棒の表の行・U-26 / B-20 文字コード(2026-10-05・起票 `KICKOFF-juri-tsuzuki.md`) ------------
# ★★ユーザー裁定(2026-10-05)問い1「(ア) 説明書に1行足して合格にしない」・問い3「(ア) 説明書に「UTF-8 で保存する」を1行足して
#   合格にしない」。★先に説明書(uradori と bunken-daicho の `references/daicho-format.md`)へ1行ずつ足してから繋いだ
#   (★ユーザー裁定1(2026-08-22)「説明書の裏づけの無い基準で納品を止めない」の順番。C-5 と同じ)。
#
# ★U-25 / B-19(全角の縦棒): 表の行の形(行頭か行末が全角の「｜」・列が2つ以上)をしているのに、
#   `parse_md_tables` がどの表の見出し・区切り・行としても読まなかった行を名指す。
#   ★「表として読めなかった」と言える所は、点検の側が実際に読まなかった所と同じ所だけである(★C-5 と同じ考え方)。
#   ★列が2つ以上 = `parse_md_tables` が見出しに求める数と同じ(★表とみなす最小の形)。★両端の縦棒は区切りに数えない(`split_row` と同じ)。
#   🔴★**拾ってはいけない検体**: 普通の文に「｜」が2つある行(行頭・行末が「｜」でない)/ 囲みの中の行(`strip_code_fences` が空にする)/
#     半角の表の中のセルに入った「｜」(行頭・行末が半角の「|」⇒ 表の行として読まれる)/ 列が1つの「｜注意｜」。
#   ★全角の行で表が切れると、後ろの半角の行も表の行として読まれない(`parse_md_tables` は「|」の無い行で表を閉じる)。
#     ⇒ 全角の行のすぐ後ろに続く、表の行の形(行頭か行末が「|」か「｜」・列が2つ以上)で読まれなかった行も、件数と行番号で名指す。
#   ★責任= 納品物(`partial`。▲ ⇒ 門番 U-0・B-0 が ✕ ⇒ 終了コード 1)。★受理層の方針表 `fullwidth_pipe` の行と同じ。
#
# ★U-26 / B-20(文字コード): ファイルのバイトを UTF-8 として厳密に読めない行を名指す。
#   ★読み込みは今も `errors="replace"`(読めない字を置き換えの字 U+FFFD にして続ける)。★置き換えの字は2通りから来る:
#     ① 読み込みで【生じた】(バイトが UTF-8 でない)/ ② 元のファイルに【初めから書いてある】(UTF-8 として正しい U+FFFD)。
#   ★バイトを `surrogateescape` で読むと区別できる —— ① は U+DC80〜U+DCFF の代理の字になり、② は U+FFFD のまま残る。
#     ★行の区切りは `errors="replace"` と同じになる(★代理の字も置き換えの字も行の区切りではない)⇒ 行番号は点検の行番号と同じ。
#   ⇒ ★① だけを違反の側に数え、② は「元から書いてある置き換えの字」として件数と行番号を文に出す(★UTF-8 として正しいので咎めない)。
#   ★バイトが渡らなかった呼び出し(文字列を直に渡す試験など)では、① と ② を区別できない ⇒ 置き換えの字が無ければ ○、
#     在れば ▲(missing_input・責任= 呼び出し ⇒ 門番は拾わない ⇒ 終了コード 3)。★どちらも「バイトでは確かめていない」と文に出す。
#   ★責任= 納品物(`partial`。▲ ⇒ 門番が ✕ ⇒ 終了コード 1)。★受理層の方針表 `encoding_error` の行も同じ値へ直した(★2026-10-05)。
#   ★R系(論文の原稿)・html には繋いでいない(★起票 §1-3「その2つの納品物で置き換えの字が出たときの扱いは、今のまま変えない」)。
FULLWIDTH_BAR = "｜"
REPLACEMENT_CHAR = "\ufffd"
SURROGATE_ESCAPED = re.compile("[\udc80-\udcff]")


def table_row_cells(line, bar):
    """表の行の形なら列の数を、そうでなければ 0 を返す。★形= 行頭か行末が bar(★`split_row` と同じく、両端の bar は区切りに数えない)。"""
    s = line.strip()
    if not s or not (s.startswith(bar) or s.endswith(bar)):
        return 0
    s = s[len(bar):] if s.startswith(bar) else s
    s = s[:-len(bar)] if s.endswith(bar) else s
    return len(s.split(bar))


def fullwidth_table_rows(body):
    """全角の縦棒で書いた表の行の形(列が2つ以上)をしていて、表の行として読まれなかった行(1始まり)と、
    そのすぐ後ろに続いて表の行として読まれなかった表の行の形の行を返す。→ (全角の行, 続いて読まれなかった行)

    ★「読まれなかった」= `parse_md_tables` のどの表の見出し・区切り・行にも入っていない。
    """
    used = set()
    for t in parse_md_tables(body):
        used.update((t["hline"], t["hline"] + 1))
        used.update(ln for ln, _rc in t["rows"])
    zen = [i + 1 for i, l in enumerate(body)
           if (i + 1) not in used and table_row_cells(l, FULLWIDTH_BAR) >= 2]
    follow = []
    for z in zen:
        j = z                                   # ★1始まりの z の次の行 = 0始まりの z
        while j < len(body) and (j + 1) not in used and max(
                table_row_cells(body[j], "|"), table_row_cells(body[j], FULLWIDTH_BAR)) >= 2:
            if (j + 1) not in zen and (j + 1) not in follow:
                follow.append(j + 1)
            j += 1
    return zen, follow


def check_fullwidth_table(rule_id, body):
    """U-25 / B-19: 全角の縦棒で書いた表の行が無いか。★在れば「その行は表として読めなかった」と名乗る。"""
    r = Result(rule_id, *rule_meta(rule_id))
    zen, follow = fullwidth_table_rows(body)
    if not zen:
        r.ok_note("全角の縦棒「｜」で書いた表の行は無い(★表の行の形= 行頭か行末が「｜」・列が2つ以上で、表の行として読まれなかった行)")
        return r
    r.blocked("全角の縦棒「｜」で書いた表の行が %d 行ある%s —— その行は表として読めなかった(点検していない)%s。"
              "半角の縦棒「|」に直せば点検できる(原典: 表の縦棒に全角の「｜」を使わない)。"
              "**未検査であって合格ではない**"
              % (len(zen), lineno_list(zen),
                 ("。★その行で表が切れ、すぐ後ろの表の行 %d 行%s も表の行として読まれていない" % (len(follow), lineno_list(follow)))
                 if follow else ""))
    r.observe("partial", read=len(body) - len(zen) - len(follow), total=len(body))
    return r


def undecodable_lines(data):
    """バイトを UTF-8 として厳密に読めない行(1始まり)と、元から U+FFFD が書いてある行。→ (読めない行, 元からの行)"""
    se = data.decode("utf-8", "surrogateescape").splitlines()
    bad = [i + 1 for i, l in enumerate(se) if SURROGATE_ESCAPED.search(l)]
    orig = [i + 1 for i, l in enumerate(se) if REPLACEMENT_CHAR in l]
    return bad, orig


def check_utf8(rule_id, raw, data):
    """U-26 / B-20: 台帳が UTF-8 で読めるか。★data= ファイルのバイト(★渡らなければ None)。"""
    r = Result(rule_id, *rule_meta(rule_id))
    total = len(raw.splitlines())
    if data is None:
        n = sum(1 for l in raw.splitlines() if REPLACEMENT_CHAR in l)
        if n == 0:
            r.ok_note("置き換えの字(U+FFFD)は無い(★バイトが渡らなかったので、バイトでは確かめていない)")
            return r
        r.blocked("置き換えの字(U+FFFD)を含む行が %d 行ある —— ★バイトが渡らなかったので、読み込みで生じた字か元から書いてある字かを"
                  "区別できない(責任= 呼び出し)。**未検査であって合格ではない**" % n)
        r.observe("missing_input", what="ファイルのバイト", supplier="呼び出し")
        return r
    bad, orig = undecodable_lines(data)
    tail = ("／★元から書いてある置き換えの字(U+FFFD・UTF-8 として正しい)の行 %d 行%s は咎めない" % (len(orig), lineno_list(orig))
            if orig else "")
    if not bad:
        r.ok_note("UTF-8 で読めない行は無い(★バイトを UTF-8 として厳密に読んだ)%s" % tail)
        return r
    r.blocked("UTF-8 で読めない字を含む行が %d 行ある%s —— その行の字は読めなかった(点検の側では置き換えの字 U+FFFD になり、"
              "その行に書いてある見出し・表・凡例を「無い」と出す規則があれば、読めなかったためである)。"
              "UTF-8 で保存し直せば点検できる(原典: 台帳は UTF-8 で保存する)。**未検査であって合格ではない**%s"
              % (len(bad), lineno_list(bad), tail))
    r.observe("partial", read=total - len(bad), total=total)
    return r


# ---- 受理層の記録を普段の画面に出す(2026-10-05・起票 `KICKOFF-juri-tsuzuki.md` §1-4・ユーザー裁定 問い4 (ア)) ----
# ★`--accounting` のときしか出なかった受理層の【未対応の記録】(読めなかった形)を、普段の点検でも毎回並べる。
#   ★`00-principles.md` §12「測定器は、見ていない範囲を数えて、毎回画面に出す」の適用 ——
#     読めなかった形は、点検プログラムが「見ていない範囲」そのものである。
# ★★**合格・不合格は1つも変えない。終了コードも変えない**(★`print_admit_record` は印字だけで、何も返さない)。
# ★0件でも出す(★出さないと「0件だった」と「出していない」が区別できない)。
# ★同じ形を規則が別に判定している種類(uradori・bunken の 閉じていない囲み= U-24・B-18 / 全角の縦棒= U-25・B-19 /
#   文字コード= U-26・B-20)は、その規則を添える(★記録と規則の印を二重に数えたと読ませないため)。
#   ★記録からは外さない —— この一覧は「読めなかった形の全部」である。★記録そのものを規則が読んでいるのではない。
ADMIT_WIRED = {
    ("uradori", "unclosed_fence"): "U-24", ("bunken", "unclosed_fence"): "B-18",
    ("uradori", "fullwidth_pipe"): "U-25", ("bunken", "fullwidth_pipe"): "B-19",
    ("uradori", "encoding_error"): "U-26", ("bunken", "encoding_error"): "B-20",
}
ADMIT_SHOW_CAP = 20


def print_admit_record(path, kind, raw):
    """受理層の記録(読めなかった形)を毎回並べる。★判定は変えない(★印字だけ。何も返さない)。

    ★バイトは自分で読む(★`inspect_file` が読んだのと同じファイル)。★記録を作れなければ、作れなかったと1行出す
      (★黙って飛ばさない。★ただし合否・終了コードには触れない)。
    """
    try:
        with open(path, "rb") as f:
            data = f.read()
        _doc, unsupported = admit(raw, kind, data)
    except Exception as exc:                    # noqa: BLE001 — 印字だけの口は走行を止めない
        print("  [★受理層の記録 —— 読めなかった形] 記録を作れなかった: %s: %s(★合否・終了コードは変えない)"
              % (type(exc).__name__, exc))
        print()
        return
    print("  [★受理層の記録 —— 読めなかった形] %d件(★この記録は判定に使っていない —— 合否・終了コードは変えない)"
          % len(unsupported))
    for u in unsupported[:ADMIT_SHOW_CAP]:
        rid = ADMIT_WIRED.get((kind, u.construct))
        print("    L%-5s %-18s %s [%s]%s"
              % (u.lineno, u.construct, u.detail[:70], u.clause_id,
                 ("(★同じ形を規則 %s が別に判定している)" % rid) if rid else ""))
    if len(unsupported) > ADMIT_SHOW_CAP:
        print("    …ほか%d件" % (len(unsupported) - ADMIT_SHOW_CAP))
    print()


def check_uradori_tansaku(body, numbers, need_count=None):
    r = Result("U-8", *rule_meta("U-8"))
    sec_i = next((i for i, l in enumerate(body) if TANSAKU_HEADING.match(l.strip())), None)
    if need_count is None:
        skip_as(r, "台帳本体が読めないため未確認・未到達の有無を判定できない",
                "partial", read=0, total=len(body))
        return r
    if need_count == 0:
        if sec_i is None:
            r.ok_note("未確認・未到達が0件のためセクション不要")
        elif "該当なし" not in "\n".join(body[sec_i:sec_i + 5]):
            r.fail(sec_i + 1, "未確認・未到達は0件。セクションを置くなら「該当なし」と1行書く")
        else:
            r.ok_note("未確認・未到達0件・「該当なし」の明記あり")
        return r
    if sec_i is None:
        r.fail(None, "未確認・未到達が%d件あるのに「## 探索記録(再挑戦の起点)」セクションが無い" % need_count)
        return r
    tail = body[sec_i:]
    blocks = []
    cur = None
    for off, ln in enumerate(tail):
        if re.match(r"^#{3,4}\s", ln.strip()):
            cur = {"line": sec_i + off + 1, "head": ln.strip(), "text": []}
            blocks.append(cur)
        elif re.match(r"^#{1,2}\s", ln.strip()) and off > 0:
            break
        elif cur is not None:
            cur["text"].append(ln)
    for num in numbers:
        if not any(re.search(r"#\s*%s\b" % re.escape(num), b["head"]) for b in blocks):
            r.fail(sec_i + 1, "未確認/未到達の #%s に対応する探索記録の小見出しが無い" % num)
    for b in blocks:
        if "次の一手" not in "\n".join(b["text"]):
            r.fail(b["line"], "探索記録「%s」に「次の一手」が無い(再挑戦の起点の核)" % b["head"][:30])
    if r.status == "ok":
        r.ok_note("該当%d件・小見出し%d件・すべてに次の一手あり" % (need_count, len(blocks)))
    return r


# 「提出可」の否定形/肯定形。**○ と ✕ には原典が要るが、△ に落とすのに原典は要らない**
# (規則表の原則3)。判別できない書き方は △ に落とし、はっきり肯定しているものだけ ✕ にする。
TEISHUTSU_NEG = re.compile(
    r"提出可[^。\n]{0,40}?(?:とはできな|とは言えな|とは書けな|とは書かな|ではな|でな|としな"
    r"|は時期尚早|は避け|不可|見送|保留|至らな|ならな|とすべきでな)")
TEISHUTSU_POS = re.compile(r"提出可(?:能)?\s*(?:である|です|と判断|と結論|とする|と考え|[。、）\)]|$)")
# 未処置 = 本文側に「要検証」または修正要求が残る判定。この3語をひとまとまりに扱う規定が原典にある。
MISHOCHI = ("反証", "未確認", "未到達")


def check_teishutsu(body, hantei_values, _unused=None):
    """U-14。軸を「禁止語が出るか」から**「未処置の残高が0か」**に変える。

    旧実装は `bad = 反証+未確認 が0なら ok_note` で、**何も読まずに合格の印を押していた**。
    未到達が勘定に入っていないのはその症状であって、病巣は「0件なら対象外」の側にある。
    未到達は原典が「裏付けとしてカウントしない」「色は赤」「要検証のまま残す」と定めており、
    反証・未確認と同じく**未処置**である。
    """
    r = Result("U-14", *rule_meta("U-14"))
    if hantei_values is None:
        r.blocked("台帳本体が読めないため未処置の件数を数えられなかった")
        r.observe("partial", read=0, total=len(body))
        return r
    mishochi = [v for v in hantei_values if v in MISHOCHI]
    urazuke = [v for v in hantei_values if v in ("裏付け", "条件付き裏付け")]
    hits = [(i + 1, ln) for i, ln in enumerate(body) if "提出可" in ln]
    naiwake = "反証%d・未確認%d・未到達%d" % tuple(
        sum(1 for v in hantei_values if v == k) for k in MISHOCHI)

    if not mishochi:
        r.ok_note("未処置(反証・未確認・未到達)0件・裏付け系 %d 行" % len(urazuke))
        return r
    for lineno, ln in hits:
        if TEISHUTSU_NEG.search(ln):
            continue                                   # 「〜とはできない」型の正しい否定形
        if TEISHUTSU_POS.search(ln):
            r.fail(lineno, "未処置が%d件(%s)残った状態で「提出可」と書いている — "
                           "未到達は裏付けとして数えない" % (len(mishochi), naiwake))
        else:
            r.gray(lineno, "未処置が%d件(%s)残った状態で「提出可」の語がある。"
                           "肯定か否定かを機械では読み分けられないので目視で確認すること"
                   % (len(mishochi), naiwake))
    if r.status == "ok":
        r.ok_note("未処置%d件(%s)、「提出可」の断定なし" % (len(mishochi), naiwake))
    return r


# ---------------------------------------------------------------- bunken-daicho 台帳
BUNKEN_COLS = {
    "#":        ["#", "No", "no", "番号"],
    "書誌":     ["書誌"],
    "種別":     ["種別"],
    "言語":     ["言語"],
    "発見経路": ["発見経路"],
    "リンク":   ["リンク", "URL", "url"],
    "入手状況": ["入手状況"],
    "精読":     ["精読"],
    "要旨":     ["要旨"],
    # ★2026-10-31(起票 `KICKOFF-nukigaki-b14-b17.md`)。★B-14 が照らす。
    "抜き書き": ["抜き書き"],
    "用途タグ": ["用途タグ"],
    "アクセス日": ["アクセス日"],
}

# ---- 段5-1: 列が無いときの状態を「原典の列の要否表」から決める(2026-08-19) -------
# ★ここに表が無かったことが、段5-1 の工事の核心である。
#   `BUNKEN_COLS` は**列名の別名リスト**でしかなく、必須/推奨の別を1文字も持っていなかった。
#   そのため列の不在はすべて `missing_input(責任=納品物)` に落ちており、**原典が「推奨」と
#   定める精読列の不在まで「書き手が直せる欠落」に数えていた**。段3の門番はその分類だけを見て
#   納品を止めるので、繋いだ日に**原典が推奨と定める列の不在で納品が止まる**ことになる。
#   ★実装のメッセージ自身が「推奨列のため列自体の欠落は違反にしない」と言っており、
#     **分類と宣言が食い違っていた。**この表はその食い違いを閉じる。
#
# ★下の表は原典 run-bunken-daicho/references/daicho-format.md の**列の表の転記であって、
#   新しい基準ではない**(規則表 deliverable-rules.md の原則1)。列を足す者はまず原典の表に足すこと。
# ★uradori の `URADORI_COL_REQ` と同じ形。**違うのは水準が無いことだけ**である ——
#   bunken の原典は列ごとに必須度を1つ(必須/条件付き/推奨)しか定めていない。
#   **無い水準を捏造しない**(uradori の形へ無理に揃えると、原典に無い区別を発明することになる)。
# ★原典欄は逐語から導出する鍵で、**逐語は必須度のセルまで含む**(ORIGIN_QUOTES の "BCOL:" 参照)。
BUNKEN_COL_REQ = {
    # 概念:      (原典の鍵(控えは ORIGIN_FALLBACK に集約),  原典が定める必須度)
    "#":          ("BCOL:#", "必須"),
    "書誌":       ("BCOL:書誌", "必須"),
    "種別":       ("BCOL:種別", "必須"),
    "言語":       ("BCOL:言語", "条件付き"),
    "発見経路":   ("BCOL:発見経路", "推奨"),
    "リンク":     ("BCOL:リンク", "必須"),
    "入手状況":   ("BCOL:入手状況", "必須"),
    "精読":       ("BCOL:精読", "推奨"),
    "要旨":       ("BCOL:要旨", "推奨"),
    # ★2026-10-31(起票 `KICKOFF-nukigaki-b14-b17.md`): 要旨を本文か抄録から書いた行に要る列。
    #   ★行末に註を書かない(★変異の道具は、この表の1行が「),」で終わる形だけを読む —— 常設テスト F-16 が数える)。
    "抜き書き":   ("BCOL:抜き書き", "条件付き"),
    "用途タグ":   ("BCOL:用途タグ", "推奨"),
    "アクセス日": ("BCOL:アクセス日", "必須"),
}


def bunken_col_req(concept):
    """その列の必須度を返す。★添字で取り出さない(uradori の `col_req` と同じ理由)。"""
    return BUNKEN_COL_REQ[concept][1]


def bunken_missing_column_state(concept):
    """その列が無いときの7状態を、原典の列の要否表から決める。返り値 (state, info)。

    ★「必須」以外(推奨・条件付き)の不在は**規定による対象外**である。書き手が直すべき欠落ではない。
      ★条件付き(言語)も対象外に落とす —— 原典が「和のみで充足したら列ごと省略可」と定めており、
        省略が許される以上「検査に必要な情報が納品物に無い」とは言えない。
    """
    key, req = BUNKEN_COL_REQ[concept]
    if req != "必須":
        return "not_applicable", {"origin": origin_at(key)}
    return "missing_input", {"what": "%s列" % concept, "supplier": "納品物"}


# ---- 統計原表行の追加メタ(A-4・2026-07-20 / F-109・2026-08-17) --------------------
# ★★**実装の要点は「結合表ではなく生の行テキストを読む」ことである。**
#   段2の結合(`collect_ledger_tables`)は正典表 `BUNKEN_COLS` に無い列を**写さない**ので、
#   結合したあとの表を見ると調査年月・statInfId・fileKind の欄が**丸ごと消えている**
#   (実験の記録: `runs\checker\evidence\toukei-probe.txt` の①)。列を見に行くと必ず空振りする。
#
# ★★**行だけでなく【その表自身の見出し】も読む。**2026-08-22 の実測で分かったことで、
#   ここを外すと**偽陽性の山になる** —— メタの書き方は現物で2通りあり、どちらも正しい:
#     (ア) セルの中に欄名ごと書く …… `調査年月 2024年度` のように行の字面に欄名が出る
#     (イ) 列の見出しにして値だけ書く … 行の字面には欄名が出ず、**見出しにだけ**出る
#   実測(文献台帳807本の統計原表110行): statInfId は 行の字面52行 / 見出し53行 / **どちらかなら59行**。
#   行だけを見ると(イ)の台帳を「書いていない」と誤判定する。
#   ★**偽陽性を出す検査は使われなくなる**(PARENT-HANDOFF §6 の最上位の教訓。実例が3件ある)。
#
# ★★**必須度を一律にしない。**原典はこの3つの必須度を1文字も書いていないので、
#   3つとも必須にするのは**原典に無い基準の発明**になる(規則表 deliverable-rules.md の原則1)。
#   ★根拠は**すべて原典の中にある**(逐語は ORIGIN_QUOTES の "TMETA:" が持つ):
#     ・調査年月 = **必須**。原典が「**年代ゲートはこの調査年月で判定する**」と書いており、
#                  **下流の判定が現に依存している**。無ければ年代ゲートは判定できない
#     ・statInfId = **推奨**。「載せると再到達が1手 / 載せないと下流が検索からやり直し」は
#                  **不便の説明**であって義務ではない。無くても機能は成立する
#     ・fileKind  = **推奨**。「0=Excel(**既定**)」= **既定値がある**。無くても既定で動く
#
# ★下の表は原典 daicho-format.md「## 統計原表行の追加メタ」の**転記であって、新しい基準ではない**。
#   メタを足す者は**まず原典に足す**こと。★第3要素は「原典が名指しで禁じた旧欄名」で、
#   ★★**この字面が実装に在るのはここ1か所だけである**(常設テスト F-7 が数を固定して見張っている)。
#   検出のメッセージもこの値から組み立てる —— 字面を2か所に書かないための作法である。
TOUKEI_META = {
    # 欄名:        (原典の鍵(控えは ORIGIN_FALLBACK に集約), 原典から導いた必須度, 原典が禁じた旧欄名)
    "調査年月":   ("TMETA:調査年月", "必須", "提供年月"),
    "statInfId": ("TMETA:statInfId", "推奨", None),
    "fileKind":  ("TMETA:fileKind", "推奨", None),
}
# 規則ID → その規則が見る必須度。★**ここが「どの規則がどのメタを見るか」の唯一の正本**である。
#   規則の側に欄名を書き並べない(同じ知識が2か所にあると、原典を直したとき片方だけが古くなる。
#   この体系はその病気を5層で踏んでいる)。
TOUKEI_RULES = {"B-9": "必須", "B-10": "推奨"}
# 種別欄がこの語を含む行が「統計原表の行」である。★原典の種別の語彙(BCOL:種別 の逐語)より
#   **短く**取る —— 現物には「統計原表」「統計原表(Excel)」「統計原表(Excel・CSV)」が全部ある。
TOUKEI_SHUBETSU = "統計原表"

# ★画面に出す一言。**必須度の根拠をそのまま書く**(なぜ要るのかが読み手に伝わらないと直せない)。
TOUKEI_MSG = {
    "調査年月": "年代ゲートはこの調査年月で判定する。欄名を書き添えること"
                "(例: 調査年月: 2020年2月(e-Stat結果一覧『調査年月』欄))",
    "statInfId": "載せると原表へ1手で戻れる(推奨。違反ではない)。目視で確認すること",
    "fileKind": "0=Excel(既定)/1=CSV(推奨。既定値があるので違反ではない)。目視で確認すること",
}


def toukei_meta_req(name):
    """そのメタの必須度を返す。★添字で取り出さない(`bunken_col_req` と同じ理由)。"""
    return TOUKEI_META[name][1]


def toukei_meta_kinshi(name):
    """そのメタについて原典が名指しで禁じた旧欄名(無ければ None)。"""
    return TOUKEI_META[name][2]


def toukei_meta_names(req):
    """その必須度のメタの欄名。★**表から導く。**規則の側に欄名を書き並べないための口である。"""
    return [k for k in TOUKEI_META if toukei_meta_req(k) == req]


def collect_toukei_rows(tables, body):
    """統計原表の行を集める。返り値 [(行番号, 行の生テキスト, その表の見出し, 見出しの行番号)]。

    ★★**行番号でも列位置でも表の並び順でもなく、『種別』欄の値で見分ける。**
      原典は統計原表行を「学術文献行と**別セクション/別ブロック**に分ける」と定めているので、
      **台帳本体の表とは限らない**(段2の結合が拾う表とも限らない)。だから
      `collect_ledger_tables` ではなく、**文書内の表を全部**見て『種別』欄を持つものから拾う。
    ★『種別』欄を持たない表は対象にしない —— これが偽陽性の防波堤である。実測では、
      緩く「行の字面に統計原表があれば拾う」と**台帳の行でない22行**(報告書の中の表・採点表・
      確認ゲートの行・規則の引用)まで巻き込んだ(記録: evidence の突き合わせ)。
    """
    out = []
    for t in tables:
        idx = assign_columns(t["header"], BUNKEN_COLS)[0]
        if idx.get("種別") is None:
            continue
        head = " | ".join(t["header"])
        for lineno, rc in t["rows"]:
            if TOUKEI_SHUBETSU in cell(rc, idx["種別"]):
                out.append((lineno, body[lineno - 1], head, t["hline"]))
    return out


def check_bunken_toukei(rule_id, body):
    """統計原表行の追加メタ(B-9=必須 / B-10=推奨)。

    ★どのメタを見るかは `TOUKEI_RULES` と `TOUKEI_META` から**導く**。ここに欄名を書かない。
    ★統計原表の行が0件のときは `clean(targets=0)` にする。**「未検査(―)」にしない** ——
      対象が無いのは検査ができなかったのではないし、`not_applicable` でもない
      (規定がこの納品物を対象外にしているわけではなく、たまたま対象の行が無いだけである)。
      `clean` は「対象0件を『全行合格』と表現しない」ことを自分で強制する(G9)。
    """
    req = TOUKEI_RULES[rule_id]
    names = toukei_meta_names(req)
    tables = parse_md_tables(body)
    scanned = sum(len(t["rows"]) for t in tables)
    rows = collect_toukei_rows(tables, body)
    if not rows:
        return clean(rule_id, scanned, 0,
                     "種別が「%s」の行がこの納品物に無い" % TOUKEI_SHUBETSU)

    findings, kinshi_seen = [], set()
    for lineno, text, head, hline in rows:
        for name in names:
            # ★行の字面と見出しの**どちらか**に在れば足りる(上の註の(ア)(イ))
            if name not in text and name not in head:
                findings.append((lineno, "統計原表の行に「%s」が無い — %s"
                                 % (name, TOUKEI_MSG[name])))
            ng = toukei_meta_kinshi(name)
            # ★禁じられた旧欄名は**表ごとに1回だけ**言う(欠陥は行ではなく見出しに在ることが多い)
            if ng and hline not in kinshi_seen and (ng in text or ng in head):
                kinshi_seen.add(hline)
                findings.append((hline, "欄名「%s」は原典が名指しで禁じている(e-Stat に存在しない欄)"
                                        " — 「%s」に書き換える" % (ng, name)))
    findings.sort(key=lambda x: (x[0] is None, x[0]))
    if not findings:
        return clean(rule_id, scanned, len(rows),
                     "%s が全行にある" % "・".join(names))
    if req == "必須":
        return violation(rule_id, findings,
                         "統計原表%d行を検査・%d件の違反" % (len(rows), len(findings)))
    # ★推奨のメタの欠落は**違反にしない**(原典が義務と書いていない)。△ に留め、
    #   責任は「人間」に置く —— 門番は責任=納品物 の ▲ しか ✕ にしないので、これで納品は止まらない。
    r = needs_human(rule_id, rule_meta(rule_id)[1], "台帳の書き手",
                    "統計原表%d行を検査・推奨のメタが欠けている指摘が%d件"
                    % (len(rows), len(findings)))
    r.findings.extend(findings)
    return r



# ---- ヘッダーの「キー: 値」の行(F-063・2026-08-28) --------------------------------
# ★★採用された指摘の逐語(台帳 F-063)= 「B-2 を「冒頭40行のうち『(箇条書き記号)キー … :』の
#   形をした行にキーが現れること」を要求する厳格版に差し替え、ok_note の申告文を実態に合わせる」。
# ★原典の逐語(daicho-format.md)= 「**各項目は「キー: 値」の形で1行ずつ書く。**散文で
#   「本台帳の目的は〜であり、実行日は〜」とまとめない(人も点検プログラムもどの値がどのキーの
#   ものか拾えなくなる)。」/ SKILL.md= 「「目的: …」「実行日: …」という**キー: 値の形の行**として
#   実際に在るか。「あとで書き足すこと」という書き添えは在るうちに入らない」。
# ★★**旧実装は冒頭40行を1本に繋いだ上での部分文字列の一致**だった。⇒ 台帳の**表のセルの中**や
#   **散文**や**「あとで書き足すこと」という書き添え**でも◎を出していた。母集団807本の実測では
#   **22本**がその形で通っていた(記録= `runs/checker/JISSOU-bunken-h8-mitakuchi.md`)。
# ★★**間の文字を許すこと**が要点である(逐語の「…」)。★これを許さない版を母集団に当てたら
#   **9本が新たに落ち、うち7本が `- **実行日 / アクセス日**: 2026-07-19` という正しい形**だった。
#   ⇒ 厳しすぎる版は巻き添えであり、`00-principles.md` §6「偽陽性を出す検査は使われなくなる」を踏む。
# ★**表の行は当たらない** —— 行頭が `|` なので箇条書き記号にも太字にもキーにもならない。
#   ★間に `|` を許さないのは、表のセルを跨いで拾わないためである。
_HEADER_KEY_RE = {}


def header_key_line(head_lines, key):
    """冒頭の行のうち「(箇条書き記号)キー … :」の形をした行を1本返す。無ければ None。"""
    rx = _HEADER_KEY_RE.get(key)
    if rx is None:
        rx = re.compile(r"^\s{0,3}(?:[-*+]|\d+[.)])?\s*\**\s*%s\s*\**\s*[^|]{0,30}?[:：]"
                        % re.escape(key))
        _HEADER_KEY_RE[key] = rx
    for ln in head_lines:
        if rx.match(ln):
            return ln
    return None


# ---- 件数目安の宣言帯と実カウントの突合(F-021 前半・2026-08-28) --------------------
# ★★採用された指摘の逐語(台帳 F-021・チェッカー側)= 「その規定を機械化する(まず**件数目安の
#   宣言帯と実カウントの突合**)+B-2の未検査注記を集計行と見送り欄にも出す」。
# ★原典が決めていること(逐語):
#   ・daicho-format.md「**件数目安** — 実際の行数を数えて目安と比べる(超過しても落とさない
#     → SKILL.md ゲート項目5)」
#   ・SKILL.md ゲート項目5「**目安は「目標」であって上限ではない**」/
#     「統計原表・白書は**この枠と別に数える**(学術文献の枠を食わせない)」
# ★★**したがって超過は違反にしない。**原典が逐語で「落とさない」と定めている。
#   ★**不足のときどうするかは原典が黙っている**ので、ここでは判定を立てない(★埋めない)。
#   ⇒ **この突合は数を出す。判定は立てない。**★それでも「未検査」ではない ——
#     宣言と実カウントが**画面に並んで出る**ので、読み手が食い違いを自分で見られる。
#   ★「宣言そのものを必須にするか(=無いことを違反にするか)」は**判断待ちとして記録に出した。**
#     ★原典はヘッダーブロックを「冒頭に必須」と定めるが、B-2 が違反にしているのは目的・実行日の
#     2つだけであり、7項目すべてを必須へ倒すのは**採用された逐語の外**である。
KENSUU_BAND_RE = re.compile(r"(\d+)\s*(?:[〜～~－ー\-]\s*(\d+))?\s*件")
# ★別枠の種別。**原典の逐語「統計原表・白書は**この枠と別に数える**」の写しである。**
#   ★種別の語彙そのものは daicho-format.md の列の表に在る(統計原表(Excel・CSV)/ 白書・報告書)。
KENSUU_BEKKO = ("統計原表", "白書")


def bunken_kensuu_note(head_lines, header, rows):
    """件数目安の宣言帯と実カウントを突き合わせ、註の断片を返す(判定は立てない)。"""
    line = header_key_line(head_lines, "件数目安")
    if line is None:
        return ("件数目安= ヘッダーに宣言が無いため突合していない"
                "(★この規則が違反にするのは目的・実行日の2つだけである)")
    decl = re.split(r"[:：]", line, 1)[-1]
    m = KENSUU_BAND_RE.search(decl)
    if not m:
        return "件数目安= 宣言から件数の帯を取り出せないため突合していない(宣言「%s」)" % decl.strip()[:30]
    lo = int(m.group(1))
    hi = int(m.group(2)) if m.group(2) else lo
    if header is None:
        return "件数目安= 宣言 %s に対し、台帳本体の表が読めないので実カウントを取れない" % _band(lo, hi)
    # ★列の割当は**その場で引く**(B-2 は idx を組み立てる前に走るため)。
    #   ★`assign_columns` は読み取りだけで、判定を1つも変えない。
    sy_i = assign_columns(header, BUNKEN_COLS)[0].get("種別")
    bekko = 0
    gakujutsu = 0
    for _lineno, row in rows:
        sy = cell(row, sy_i).replace("*", "").strip() if sy_i is not None else ""
        if any(w in sy for w in KENSUU_BEKKO):
            bekko += 1
        else:
            gakujutsu += 1
    verdict = ("適合" if lo <= gakujutsu <= hi
               else ("超過(原典は『超過しても落とさない』と定める)" if gakujutsu > hi else "不足"))
    return ("件数目安= 宣言 %s に対し学術文献 %d件(統計原表・白書は別枠 %d件)→ %s"
            % (_band(lo, hi), gakujutsu, bekko, verdict))


def _band(lo, hi):
    return "%d件" % lo if lo == hi else "%d〜%d件" % (lo, hi)


# ---- B-17(2026-10-05・起票 `KICKOFF-daicho-mujun.md`): 台帳の【中】の食い違い -------------------------
# ★出所= ユーザー裁定(2026-10-04)「台帳の中の食い違いは別の工事として作る(推奨)」。★材料= 担当27-12 の記録
#   `runs/checker/JISSOU-stagec-kakuage.md` §5 の問い2。★同じ穴は bunken-daicho の評価で F-073(確定・P1)として出ていた
#   (★そのときの3役は「入手状況×精読の2枝は語彙が閉じていて崩せない」「要旨の枝は素朴に拾うと偽陽性」と書いた)。
# ★見るのは、精読が「本文精読済み」(原典「要旨を本文から書いたら「本文精読済み」」)の行で、
#   原典の言葉の定義だけで「両立しない」と言える組だけである(★ネットにも段階C の結果にも触らない):
#   ① 入手状況=抄録のみ …… 原典「抄録のみ — 抄録は読めたが全文は未入手」
#   ② 入手状況=未入手 ……… 原典「未入手 — 書誌は確定したが本文にまだ到達していない」
#   ③ 要旨に「(抄録より)」の印があり、本文の印が無い …… 原典(鉄則3)「抄録しか読めていなければ「(抄録より)」と明記する」
#   ★✕ にする理由: どの組も「どちらかの欄が事実と違う」ことが定義から決まる(★どちらを直すかは書き手が決める)。
#     ★入手状況の格上げは原典が「ゼロ許容違反」と書き、精読の格上げは「格上げしない」(★化けの文脈ではゼロ許容)と書く。
# 🔴★**入れないもの(★拾ってはいけない検体)**:
#   ・有料・学内限定 × 本文精読済み —— 課金・学内認証で読めるので両立しうる(★F-073 の再現係が偽陽性として固定した組)
#   ・要旨に本文の印「(…本文…より)」「(…全文…より)」と「(抄録より)」が両方ある行 —— 一部を抄録から書いた要旨の
#     精読をどう付けるかは原典が決めていない ⇒ 判定しない(★実物= 「(本文pp.263-264および抄録より)」は印の形が違うので
#     そもそも「(抄録より)」に当たらない)
#   ・「抄録」の語が「(抄録より)」の形でない行(「抄録の掲載はなく」「抄録より詳しい」「(英文抄録より)」など)
#     —— 原典が定める印の形ではない ⇒ 読めた範囲の印として読まない(★件数と行は毎回の文に出す)
#   ・抄録どまり の側(逆向き)—— ★2026-10-05 から ④ として見る(↓)
# ★精読・入手状況の読み方は B-5・B-4 と同じ(★語彙の外の値はこの規則では判定しない。★B-4・B-5 が ✕ にする)。
# ★見ていない範囲は、毎回の文に件数と行で出す(`00-principles.md` §12)。
#
# ★★2026-10-05(起票 `KICKOFF-b17-tsuika.md`・ユーザー裁定 2026-10-05 問い6「足す」)—— 同じ穴の延長の組を2つ足した:
#   ④ 精読=抄録どまり なのに 要旨に本文の印だけ(★逆向き)
#      …… 原典「抄録・書誌情報だけから書いたら「抄録どまり」」と、要旨の読めた範囲の印(下の2つの逐語)
#   ⑤ 入手状況=抄録のみ・未入手 なのに 要旨に本文の印(★精読を介さない)
#      …… ①② の入手状況の定義(全文は未入手 / 本文にまだ到達していない)と、同じ印
#   ★本文の印は【原典が書いている形だけ】を読む: 「(全文より)」(原典「読めた範囲を明記(全文/抄録より)」)と
#     「(ページ本文より)」(原典「要旨欄の出所ラベル(「(抄録より)」「(ページ本文より)」)は**どこまで読んだか**を表すもの」)。
#     ★半角・全角の括弧どちらも読む。★「(全文PDFより)」「(本文p.2-3より)」などは原典の形ではない(★「(本文より)」は 2026-10-06 から原典の形 —— ↓)
#     ⇒ 読めた範囲の印として読まない(★件数と行を毎回の文に出す)。★③ が「(抄録より)」の形だけを読み
#     「(英文抄録より)」を読まないのと同じ考え方である。
#   ★✕ を立てる側の印は原典の形だけで【狭く】読み、✕ を外す側の印(④ の「両方」)は【広く】読む
#     (★③ の「両方」が本文の印を `YOSHI_BODY_LABEL` で広く読むのと鏡写し)。⇒ どちらの向きも、疑わしい行に ✕ を立てない。
#   ★④ は、要旨に抄録の印「(…抄録…より)」も在れば判定しない(★一部を抄録から書いた要旨の精読の付け方は原典が決めていない)。
#   ★⑤ は、抄録の印が在っても判定する —— ★入手状況の定義は、要旨のどこかを本文から書いた時点で事実と違う
#     (★「一部を抄録から書いた」は精読の付け方の話であって、入手状況の真偽を変えない)。
#   ★⑤ は精読を問わない ⇒ ★精読列が無い台帳でも見る(★要旨列が無ければ見ない)。
#
# ★★2026-10-06(起票 `KICKOFF-honbun-yori.md`・ユーザー裁定 2026-10-05 ⑧「(ウ) 説明書に足してから数える」)——
#   ①説明書(bunken-daicho の書式の正本 `references/daicho-format.md`)に、逐語「**「(本文より)」も、本文を読んで書いた側の
#   印である**」の1行を足し、②④⑤ の本文の印(`YOSHI_BODY_LABEL_GENTEN`)に「(本文より)」を足した(★この順番で)。
#   ★足したのは「(本文より)」の形だけ(★括弧ごと。半角・全角の括弧は既存と同じに読む)。
#   ★本文の一部だけを読んだ印(「(本文冒頭より)」「(本文「1.はじめに」より)」)と、本文ではない頁を読んだ印
#     (「(書誌・リポジトリ本文ページより)」)は、今も読まない(★毎回の文に件数と行を出す)。★③ の判定は変えていない。
SEIDOKU_HONBUN = "本文精読済み"
SEIDOKU_ABST = "抄録どまり"
NYUSHU_NOT_REACHED = ("抄録のみ", "未入手")
YOSHI_ABST_LABEL = re.compile(r"[（(]抄録より[）)]")
YOSHI_BODY_LABEL = re.compile(r"[（(][^（()）]*(?:本文|全文)[^（()）]*より[）)]")
# ★2026-10-05: ④⑤ が ✕ を立てる側の本文の印(★原典の形だけ)/ ④ が ✕ を外す側の抄録の印(★広く)。
# ★2026-10-06: 原典の形に「(本文より)」を足した(★説明書に足した1行・ユーザー裁定 2026-10-05 ⑧ (ウ))。
YOSHI_BODY_LABEL_GENTEN = re.compile(r"[（(](?:全文|ページ本文|本文)より[）)]")
YOSHI_ABST_LABEL_ANY = re.compile(r"[（(][^（()）]*抄録[^（()）]*より[）)]")
# ★★2026-10-31(起票 `KICKOFF-nukigaki-b14-b17.md`・claude-harness の D64 の 8枚目の問3 A「精読の言い過ぎをチェッカーでも止める」)——
#   ⑥ 精読=本文精読済み なのに 要旨の本文の印が本文の一部を名乗る(★言い過ぎ)。
#   …… 原典(書式「精読フラグの運用」)「本文の一部を名乗る印と「本文精読済み」の組は、言い過ぎである」・
#      全部読んだ時の形「(本文より)」と「印は「(本文の画像より)」(全部読んだ時の形)」。
#   ★全部読んだ時の形(下の `YOSHI_BODY_LABEL_ZENBU`)が1つでも在る要旨は判定しない(★✕ を外す側は広く)。
#   ★抄録の印(広く `YOSHI_ABST_LABEL_ANY`)が在る要旨は判定しない(★③ の「両方」と同じ。一部を抄録から書いた要旨)。
#   ★「全」の字を含む本文の印(「(全文PDFより)」「(本文全6頁より)」「(節の全文より)」)が在る要旨は判定しない
#     (★ユーザーの決定 2026-10-31「「全」の入った印は外す」—— 一部を名乗る印ではない。★件数と行を毎回の文に出す)。
#   ★④⑤ の本文の印(`YOSHI_BODY_LABEL_GENTEN`)には「(本文の画像より)」を足していない(★頼まれたのは ⑥ だけ)。
#   ★★2026-10-31(★別の文脈の確かめの指摘): 全部読んだ時の形は括弧の中の空白を許す(「(本文 より)」)。★媒体だけを名乗る印
#     (「(本文PDFより)」「(本文画像より)」)は本文の一部を名乗らない ⇒ ✕ にせず、件数と行を出す(★ユーザーの決定の
#     「本文の一部を名乗る印」の外。★✕ の文「本文の一部を名乗る」が事実と違ってしまうため)。
YOSHI_BODY_LABEL_ZENBU = re.compile(r"[（(]\s*(?:全文|ページ本文|本文|本文の画像)\s*より\s*[）)]")
#   ★「(本文の画像より)」は全部読んだ時の形(★上)であり、媒体だけの印には入れない(★2つの読み方を重ねない)。
YOSHI_BODY_LABEL_BAITAI = re.compile(r"[（(]\s*本文\s*(?:PDF|ＰＤＦ|画像|の\s*(?:PDF|ＰＤＦ))\s*より\s*[）)]", re.I)


def lineno_list(ls, cap=5):
    """行番号の並びを「(L3・L8 ほか n行)」の形にする。★空なら空文字。"""
    head = "・".join("L%d" % x for x in ls[:cap])
    return ("(%s%s)" % (head, " ほか %d行" % (len(ls) - cap) if len(ls) > cap else "")) if ls else ""


def check_bunken_seidoku_mujun(rows, idx):
    """B-17: 精読・入手状況・要旨の読めた範囲が、原典の定義どうしで両立しない行を ✕ にする。

    ★組(①〜⑤)と、入れないものの理由は、すぐ上の註。★判定しなかった行は件数と行番号で毎回の文に出す。
    """
    r = Result("B-17", *rule_meta("B-17"))
    sdi, yi = idx["精読"], idx["要旨"]
    if sdi is None and yi is None:
        # ★原典は精読も要旨も「推奨」と定める ⇒ 列の不在は規定による対象外(★B-5 と同じ振り分け)。
        st, info = bunken_missing_column_state("精読")
        skip_as(r, "精読列が無い(推奨列のため列の欠落は違反にしない。★精読と他の欄の食い違いは見ようが無い)"
                   "・要旨列も無い(推奨列。★⑤ 入手状況と要旨の読めた範囲の食い違いも見ようが無い)", st, **info)
        return r
    honbun = 0
    abst_n = 0      # 精読=抄録どまり の行(★④)
    nr_n = 0        # 入手状況=抄録のみ・未入手 の行(★⑤)
    out_sd = []     # 精読が2語の外(★B-5 の担当)
    out_av = []     # 本文精読済み だが入手状況が5語の外(★B-4 の担当)
    mixed = []      # 要旨に本文の印と「(抄録より)」が両方(★原典が決めていない)
    other = []      # 要旨の「抄録」が「(抄録より)」の形でない(★読めた範囲の印として読まない)
    mixed_r = []    # ★④ の側: 抄録どまり で要旨に本文の印と抄録の印が両方(★原典が決めていない)
    other_b = []    # ★④⑤ の側: 要旨の本文の印が原典の形でない(★読めた範囲の印として読まない)
    zen6 = []       # ★⑥ の側: 本文の印に「全」の字(★一部を名乗る印として読まない・ユーザーの決定 2026-10-31)
    baitai6 = []    # ★⑥ の側: 本文の印が媒体だけを名乗る(「(本文PDFより)」など。★一部を名乗る印として読まない)
    abst6 = []      # ★⑥ の側: 一部の印と抄録の印が両方(★原典が決めていない)
    both6 = []      # ★⑥ の側: 全部読んだ時の形と、それ以外の本文の印が両方(★判定しない)
    for lineno, row in rows:
        sd = cell(row, sdi).replace("*", "").strip()
        if sd not in BUNKEN_SEIDOKU and not is_empty(sd):
            out_sd.append(lineno)
        av = re.sub(r"[（(].*?[）)]", "", cell(row, idx["入手状況"]).replace("*", "").strip()).strip()
        y = cell(row, yi)
        why = []
        if sd == SEIDOKU_HONBUN:
            honbun += 1
            if av not in BUNKEN_NYUSHU:
                out_av.append(lineno)
            abst = bool(YOSHI_ABST_LABEL.search(y))
            body = bool(YOSHI_BODY_LABEL.search(y))
            if av in NYUSHU_NOT_REACHED:
                why.append("入手状況が「%s」(★本文に届いていない側の語)" % av)
            if abst and not body:
                why.append("要旨に「(抄録より)」の印だけがある(★抄録しか読めていない側の印)")
            if abst and body:
                mixed.append(lineno)
            if "抄録" in YOSHI_ABST_LABEL.sub("", y):
                other.append(lineno)
            # ★⑥(2026-10-31)。★✕ を立てるのは、全部読んだ時の形も抄録の印も「全」も無い本文の印だけ。
            #   ★分岐は `elif` で書かない(★変異の道具の cond-invert は `elif` を試さない —— 常設テスト F-36 の死角)。
            parts6 = [m.group(0) for m in YOSHI_BODY_LABEL.finditer(y) if not YOSHI_BODY_LABEL_ZENBU.fullmatch(m.group(0))]
            zenbu6 = YOSHI_BODY_LABEL_ZENBU.search(y) is not None
            abst_any6 = YOSHI_ABST_LABEL_ANY.search(y) is not None
            zen_ji6 = any("全" in lb for lb in parts6)
            baitai_6 = any(YOSHI_BODY_LABEL_BAITAI.fullmatch(lb) for lb in parts6)
            if parts6 and zenbu6:
                both6.append(lineno)
            if parts6 and not zenbu6 and abst_any6:
                abst6.append(lineno)
            if parts6 and not zenbu6 and not abst_any6 and zen_ji6:
                zen6.append(lineno)
            if parts6 and not zenbu6 and not abst_any6 and not zen_ji6 and baitai_6:
                baitai6.append(lineno)
            if parts6 and not zenbu6 and not abst_any6 and not zen_ji6 and not baitai_6:
                why.append("要旨の本文の印「%s」が本文の一部を名乗る(★全部読んだ時の形「(本文より)」「(本文の画像より)」が無い。"
                           "言い過ぎ)" % parts6[0])
        # ★④⑤(2026-10-05)。★本文の印は原典の形だけで読む。
        why_new = []
        g = YOSHI_BODY_LABEL_GENTEN.search(y)
        if sd == SEIDOKU_ABST:
            abst_n += 1
            if g:
                if YOSHI_ABST_LABEL_ANY.search(y):
                    mixed_r.append(lineno)
                else:
                    why_new.append("精読が「抄録どまり」(抄録・書誌だけから要旨を書いた)なのに、要旨に本文の印「%s」だけがある"
                                   "(★本文から書いた側の印)" % g.group(0))
        if av in NYUSHU_NOT_REACHED:
            nr_n += 1
            if g:
                why_new.append("入手状況が「%s」(★本文に届いていない側の語)なのに、要旨に本文の印「%s」がある"
                               "(★本文から書いた側の印)" % (av, g.group(0)))
        if (sd == SEIDOKU_ABST or av in NYUSHU_NOT_REACHED) and g is None and YOSHI_BODY_LABEL.search(y):
            other_b.append(lineno)
        if why or why_new:
            # ★①②③ だけの行は、旧の文と1字も違わない(★④⑤ が重なったときだけ「 / 」で続ける)。
            parts = ["精読が「本文精読済み」(本文を読んで要旨を書いた)なのに、%s" % "・".join(why)] if why else []
            r.fail(lineno, "%s —— 原典の定義どうしが両立しない(どちらかの欄が事実と違う)。読めた範囲に合わせて直す"
                   % " / ".join(parts + why_new))
    # ★合格でも違反でも、照合した行数と【見ていない範囲】を出す(★`ok_note` は記号を動かさない)。
    r.ok_note("本文精読済みの行 %d行を照合(①入手状況=抄録のみ ②入手状況=未入手 ③要旨に「(抄録より)」の印だけ"
              " ⑥要旨の本文の印が本文の一部を名乗る)"
              "・抄録どまりの行 %d行を照合(④要旨に本文の印だけ)"
              "・入手状況が抄録のみ・未入手の行 %d行を照合(⑤要旨に本文の印)"
              "・★本文の印は原典の形「(全文より)」「(ページ本文より)」「(本文より)」だけを読む"
              "／★判定しなかった行: 精読が2語の外 %d行%s(B-5 の担当)・本文精読済みで入手状況が5語の外 %d行%s(B-4 の担当)"
              "・要旨に本文の印と「(抄録より)」が両方 %d行%s(原典が決めていない)"
              "・要旨の「抄録」が「(抄録より)」の形でない %d行%s(読めた範囲の印として読まない)"
              "・抄録どまりで要旨に本文の印と抄録の印が両方 %d行%s(原典が決めていない)"
              "・④⑤の側で要旨の本文の印が原典の形でない %d行%s(「(本文冒頭より)」など。読めた範囲の印として読まない)"
              "・⑥の側で本文の印に「全」の字 %d行%s(「(全文PDFより)」など。一部を名乗る印として読まない)"
              "・⑥の側で本文の印が媒体だけを名乗る %d行%s(「(本文PDFより)」など。一部を名乗る印として読まない)"
              "・⑥の側で一部の印と抄録の印が両方 %d行%s(原典が決めていない)"
              "・⑥の側で全部読んだ時の形とそれ以外の本文の印が両方 %d行%s(判定しない)"
              "・★⑥の全部読んだ時の形は「(全文より)」「(ページ本文より)」「(本文より)」「(本文の画像より)」%s%s"
              " ※有料・学内限定は本文精読済みと両立しうるので食い違いにしない"
              % (honbun, abst_n, nr_n, len(out_sd), lineno_list(out_sd), len(out_av), lineno_list(out_av),
                 len(mixed), lineno_list(mixed), len(other), lineno_list(other),
                 len(mixed_r), lineno_list(mixed_r), len(other_b), lineno_list(other_b),
                 len(zen6), lineno_list(zen6), len(baitai6), lineno_list(baitai6),
                 len(abst6), lineno_list(abst6), len(both6), lineno_list(both6),
                 "／★精読列が無いので①〜④は見ていない(推奨列のため規定による対象外)" if sdi is None else "",
                 "／★要旨列が無いので③は見ていない(④⑤も見ていない)" if yi is None else ""))
    return r


def check_bunken(path, raw, lines, sink=None, data=None):
    # ★段6: sink を渡されたら**そこへ積む**。規則の外で例外が起きても、
    #   すでに出た判定を呼び出し側が拾えるようにするための口である(判定は1つも変わらない)。
    results = [] if sink is None else sink
    body = strip_code_fences(lines)
    tables = parse_md_tables(body)
    # 段2: bunken にも複数表の結合を広げる。★台帳を2つ以上の表に分けて書くと、
    #      これまでは1つ目しか検査されず、2つ目以降の欠落が全部合格になっていた。
    header, rows, hline, n_tbl, undecided = collect_ledger_tables(
        tables, BUNKEN_COLS, ("書誌", "リンク", "入手状況"))
    tbl = None if header is None else True

    # B-2 ヘッダー
    with guard(results, "B-2"):
        r = Result("B-2", *rule_meta("B-2"))
        # ★★F-063(台帳・採用): **部分文字列の一致をやめ、「キー: 値」の【行の形】で見る。**
        #   ★経緯・原典の逐語・偽陽性の実測は `header_key_line` の註に書いた。
        head40 = body[:40]
        missing = [k for k in ("目的", "実行日") if header_key_line(head40, k) is None]
        if missing:
            r.fail(None, "ヘッダーブロックに %s が「キー: 値」の形の行として無い"
                         "(散文にまとめた形・表のセルの中・「あとで書き足すこと」の書き添えは"
                         "在るうちに入らない)" % "・".join(missing))
        # ★★F-021(台帳・採用)の前半: **件数目安の宣言帯と実カウントを突き合わせる。**
        #   ★★`ok_note` は註を書くだけで status を1つも動かさない(class Result 参照)。
        #     ⇒ **違反が立っていても、突合の結果と申告文は画面に出す。**黙って落とさない。
        #   ★件数目安が機械化できたので、申告文の「未検査」から件数目安を外した(5→4項目)。
        r.ok_note("目的・実行日あり(「キー: 値」の行として確認)／%s"
                  " ※中間行のうち 種別範囲・年代範囲・言語・エンジン の4項目は"
                  "【まだ機械化していない】ため未検査"
                  % bunken_kensuu_note(head40, header, rows))
        results.append(r)

    if tbl is None:
        for rid in ("B-1", "B-3", "B-4", "B-5", "B-8", "B-11", "B-12", "B-13", "B-14",
                    "B-15", "B-16", "B-17"):
            with guard(results, rid):
                rr = Result(rid, *rule_meta(rid))
                # ★2026-08-04 ユーザー決定により bunken は現状維持(記号は「―」のまま)。
                #   段1で足すのは記録だけ —— **これは「検査しなくてよかった」ではない。**
                skip_as(rr, "台帳本体の表が見つからない(書誌・リンク・入手状況の列を持つMarkdown表が必要)",
                        "partial", read=0, total=len(body))
                results.append(rr)
        guarded(results, "B-6", lambda: check_bunken_legend(body))
        guarded(results, "B-7", lambda: check_bunken_tansaku(body))
        # ★★B-9・B-10 は**台帳本体の表が見つからなくても走る。**統計原表の行は
        #   『種別』欄の値で拾っており、段2の結合(=ここで失敗しているもの)に依存していない。
        #   ここで一緒に諦めると、**表の割り方が原典どおり(別ブロック)の台帳ほど検査が届かない**
        #   という逆立ちした挙動になる。
        guarded(results, "B-9", lambda: check_bunken_toukei("B-9", body))
        guarded(results, "B-10", lambda: check_bunken_toukei("B-10", body))
        # B-18 コードの囲み(C-5)。★門番の前に置く —— 門番が ▲ を数えるためである。
        guarded(results, "B-18", lambda: check_fence_closed("B-18", lines))
        # B-19・B-20 全角の縦棒・文字コード(2026-10-05)。★門番の前に置く —— 門番が ▲ を数えるためである。
        guarded(results, "B-19", lambda: check_fullwidth_table("B-19", body))
        guarded(results, "B-20", lambda: check_utf8("B-20", raw, data))
        if KANMON_ON["bunken"]:
            guarded(results, "B-0", lambda: check_kanmon("bunken", results, body, tables))
        return results, None

    idx = dict.fromkeys(BUNKEN_COLS)
    idx.update(assign_columns(header, BUNKEN_COLS)[0])

    guarded(results, "B-1",
            lambda: check_link_column("B-1", rows, idx["リンク"], idx["リンク"] is not None,
                                      "DOIを優先し、なければ安定URL。リンクのない行は作らない"))

    # B-11 段階A: そのリンクが**現に届くか**。★B-1(在るか)とは別の検査である。
    guarded(results, "B-11",
            lambda: check_link_reach("B-11", rows, idx["リンク"],
                                     idx["リンク"] is not None, LINK_EVIDENCE))

    # B-13 段階B: その書誌が**登録機関の記録と合っているか**。
    #   ★B-11(届くか)とは別の検査である —— ★**リンクが 200 を返しても、書誌が別物のことがある。**
    guarded(results, "B-13",
            lambda: check_biblio_match("B-13", rows, idx["書誌"], idx["リンク"],
                                       idx["書誌"] is not None and idx["リンク"] is not None,
                                       BIBLIO_EVIDENCE, idx["#"], SHOSHI))

    # B-14 段階C: 要旨の中で**鍵括弧に入れた逐語**と、★抜き書きの欄の抜き書き(2026-10-31)が、原典に現に在るか。
    #   ★対照A に使うのは **書誌欄の題名**(鍵括弧の中身)。
    guarded(results, "B-14",
            lambda: check_quote_presence("B-14", rows, idx["要旨"], idx["リンク"],
                                         idx["書誌"], True, FULLTEXT_EVIDENCE,
                                         nukigaki_i=idx["抜き書き"]))

    # B-3 必須列
    with guard(results, "B-3"):
        r = Result("B-3", *rule_meta("B-3"))
        # ★段5-1: 必須/推奨の別は BUNKEN_COL_REQ **1か所**から引く。ここに列名を書き並べない ——
        #   同じ知識が2か所にあると、原典を直したときに片方だけが古くなる。この体系はその病気を
        #   5層で踏んでいる(規則表の原典欄・判定の理由・控えとテスト・ハーネスの記録・受理プロファイル)。
        # ★「必須%d列あり」の数も表から導く。**数字を書かない**ので、表の1マスを誤ると文言が動く
        #   —— それが常設テスト側から表の各マスを見張れるようにしている当のものである。
        req = [k for k in BUNKEN_COL_REQ if bunken_col_req(k) == "必須"]
        lack = [k for k in req if idx[k] is None]
        if lack:
            r.fail(hline, "必須列が無い: %s" % "・".join(lack))
        else:
            rec = [k for k in BUNKEN_COL_REQ if bunken_col_req(k) == "推奨" and idx[k] is None]
            r.ok_note("必須%d列あり" % len(req)
                      + ("／推奨列で欠けているもの: %s(違反ではない)" % "・".join(rec) if rec else ""))
        # ★何行を検査したかを必ず見せる(uradori の U-3 と同じ扱いに揃える)。
        r.note += "／台帳本体= 表%d つ・%d 行を検査" % (n_tbl, len(rows))
        if undecided:
            r.note += "／★役が確定しない表 %d つ(L%s)" % (
                len(undecided), "・L".join(str(u["hline"]) for u in undecided))
        r.note += " ※言語列は「和のみで充足したら省略可」のため未検査"
        # ★★F-017(台帳・採用): **列が【在る】ことと、その列の【値】が原典を満たすことは別である。**
        #   ★採用の逐語= 「B-3 に # の一意性と非空の検査を足す(または新規則)」。
        #   ★★着手前の実測(2026-08-28)= **# 列の【値】を読む箇所は bunken 側に0か所**だった
        #     (値を読むのは uradori の U-8 だけで、あちらは一意性も非空も見ていない)。
        #   ★原典の逐語(daicho-format.md の列の表)=
        #     「| # | **台帳全体で一意**の連番(1から)。**空欄・重複を禁じる。表を割っても通しで続ける**…」
        #   ★★**足すのは「一意」と「非空」だけである。**連番であること・1から始まること・
        #     表を割っても通しで続くことは**原典が定めているが、採用の逐語が求めていない**
        #     (★台帳 F-017 の applied 欄= 「表を割ったときの別系列表記は設計判断が残り」)。
        #     ⇒ **判断待ちとして記録に出した。★採用の逐語の外は、原典に在っても足さない。**
        #   ★`rows` は段2の結合の【あと】なので、**台帳全体**(複数の表)を横断して見ている。
        if idx["#"] is not None:
            first = {}
            for lineno, row in rows:
                v = cell(row, idx["#"]).replace("*", "").strip()
                # ★★`elif` を使わない。**常設テスト F-36 が現に止めた**(裁定19)——
                #   変異ハーネスの `cond-invert` は `elif` を1件も母集合に入れない死角を持つ。
                #   ★`elif` で書くと、この新しい条件は**変異で殺されたか誰も測れない**まま増える。
                #   ⇒ 素の `if` + `continue` で書く。★F-36 の錨(33件)も動かさずに済む。
                if v == "":
                    r.fail(lineno, "# が空欄(原典は「空欄・重複を禁じる」と定める)")
                    continue
                if v in first:
                    r.fail(lineno, "# 「%s」が重複(原典は「台帳全体で一意」と定める。最初は L%d)"
                                   % (v, first[v]))
                    continue
                first[v] = lineno
            # ★何行を照合したかを必ず出す(★0行でも出す。「網を通した」は通したことの証明にならない)。
            r.note += "／# の一意性・非空= %d行を照合" % len(rows)
        results.append(r)

    # B-4 入手状況
    with guard(results, "B-4"):
        r = Result("B-4", *rule_meta("B-4"))
        if idx["入手状況"] is None:
            # ★この枝は到達不能である(根拠= 常設テスト E-6)。振り分けを表経由に替えても
            #   到達不能のままだが、**表を1か所に集める方針から外さない**(次に必須概念が変われば生き返る)。
            st, info = bunken_missing_column_state("入手状況")
            skip_as(r, "入手状況列が無い", st, **info)
        else:
            # ★段階A-3 の申告文へ渡すため、同じループの中で数える(★別に数え直さない)。
            nyushu = dict((k, 0) for k in BUNKEN_NYUSHU)
            for lineno, row in rows:
                v = cell(row, idx["入手状況"]).replace("*", "").strip()
                v = re.sub(r"[（(].*?[）)]", "", v).strip()
                if v in nyushu:
                    nyushu[v] += 1
                if v in ("裏付け", "条件付き裏付け", "未確認", "未到達", "確定", "推論", "仮"):
                    r.fail(lineno, "「%s」は他スキルのラベル。入手状況は入手性の軸(%s)" % (v, " / ".join(BUNKEN_NYUSHU)))
                elif v not in BUNKEN_NYUSHU:
                    r.fail(lineno, "入手状況「%s」は5語(%s)に無い" % (v or "(空)", " / ".join(BUNKEN_NYUSHU)))
            if r.status == "ok":
                r.ok_note("%d行すべて5語のいずれか" % len(rows))
            r.state_info["nyushu_counts"] = nyushu    # ★→ `STAGE_A_SELF`(段階A-3 の申告文)
        results.append(r)

    # B-5 精読フラグ
    with guard(results, "B-5"):
        r = Result("B-5", *rule_meta("B-5"))
        if idx["精読"] is None:
            # ★★段5-1 で振り分けを変えた地点。**原典は精読を「推奨」と定めている**
            #   (逐語: `| 精読 | 要旨が**本文精読済み**か**抄録どまり**か。… | 推奨 |`)。
            #   それまでは `missing_input(責任=納品物)` に落としており、**この行のメッセージ自身の
            #   宣言(「推奨列のため列自体の欠落は違反にしない」)と矛盾していた。**
            st, info = bunken_missing_column_state("精読")
            skip_as(r, "精読列が無い(推奨列のため列自体の欠落は違反にしない)", st, **info)
        else:
            # ★段階A-3 の申告文へ渡すため、同じループの中で数える(★別に数え直さない)。
            seidoku = dict((k, 0) for k in BUNKEN_SEIDOKU)
            for lineno, row in rows:
                v = cell(row, idx["精読"]).replace("*", "").strip()
                if is_empty(v):
                    continue
                if v in seidoku:
                    seidoku[v] += 1
                if v not in BUNKEN_SEIDOKU:
                    r.fail(lineno, "精読「%s」は2語(%s)に無い" % (v, " / ".join(BUNKEN_SEIDOKU)))
            if r.status == "ok":
                r.ok_note("記入済みの行はすべて2語のいずれか")
            r.state_info["seidoku_counts"] = seidoku    # ★→ `STAGE_A_SELF`
        results.append(r)

    # B-17 台帳の【中】の食い違い(2026-10-05・起票 `KICKOFF-daicho-mujun.md`)。★B-4・B-5 と同じ読み方で、
    #   精読が「本文精読済み」の行の入手状況・要旨の読めた範囲を突き合わせる(★ネットにも段階C の結果にも触らない)。
    guarded(results, "B-17", lambda: check_bunken_seidoku_mujun(rows, idx))

    guarded(results, "B-6", lambda: check_bunken_legend(body))
    guarded(results, "B-7", lambda: check_bunken_tansaku(body))
    guarded(results, "B-8",
            lambda: check_date_column("B-8", rows, idx["アクセス日"], True, "必須列"))

    # B-9 / B-10 統計原表行の追加メタ。
    # ★★**規則IDは literal で書く。ループで回さない。**——2026-08-22 に一度ループで書いて、
    #   **常設テスト G-8・F-19 が現に赤くなった**。包みの地点を数える仕組み(`_guard_sites`)も
    #   変異ハーネスの crash-inject も**規則IDの literal で地点を見分ける**ので、変数で渡すと
    #   **新しい規則が測定器から見えなくなる**(= 母集合に乗らない)。
    #   ★これは本一連の工事1/5・2/5 が直していた当の病である(「規則IDが変数で渡される `Result(` を
    #   見落として U-0 の空洞化変異が黙って消えた」の同族)。**赤が教えてくれた。**
    #   ★どの規則がどのメタを見るかの知識は `TOUKEI_RULES` が1か所で持ち続けており、
    #   表と呼び出しの食い違いは常設テストが見張る(規則を足して呼び忘れれば G-8 が赤くなる)。
    guarded(results, "B-9", lambda: check_bunken_toukei("B-9", body))
    guarded(results, "B-10", lambda: check_bunken_toukei("B-10", body))

    # B-12 段階A-3: その申告が**納品物に載ったか**。★B-11(届くか)とは別の検査である。
    #   ★**B-4・B-5 の後・門番の前**に置く —— 申告文がそれらの数を読むためである。
    guarded(results, "B-12",
            lambda: check_stage_a_embedded("B-12", "bunken", lines, results,
                                           max([ln for ln, _r in rows], default=0)))

    # B-15 段階B-2: その申告が**納品物に載ったか**。★B-13(合っているか)とは別の検査である。
    #   ★**B-13 の後・門番の前**に置く —— 申告文が B-13 の数を読むためである。
    guarded(results, "B-15",
            lambda: check_stage_b_embedded("B-15", "bunken", lines, results,
                                           max([ln for ln, _r in rows], default=0)))

    # B-16 段階C-2: その申告が**納品物に載ったか**。★B-14(在るか)とは別の検査である。
    #   ★**B-14 の後・門番の前**に置く —— 申告文が B-14 の結果を読むためである。
    guarded(results, "B-16",
            lambda: check_stage_c_embedded("B-16", "bunken", lines, results,
                                           max([ln for ln, _r in rows], default=0)))

    # B-18 コードの囲み(C-5・2026-10-05)。★門番の前に置く —— 門番が ▲ を数えるためである。
    guarded(results, "B-18", lambda: check_fence_closed("B-18", lines))

    # B-19・B-20 全角の縦棒・文字コード(2026-10-05)。★門番の前に置く —— 門番が ▲ を数えるためである。
    guarded(results, "B-19", lambda: check_fullwidth_table("B-19", body))
    guarded(results, "B-20", lambda: check_utf8("B-20", raw, data))

    # B-0 門番(最後に置く。ここまでの結果に ▲ や「納品物の責任で未検査」が残っていれば違反を立てる)
    if KANMON_ON["bunken"]:
        guarded(results, "B-0", lambda: check_kanmon("bunken", results, body, tables))
    return results, None


def check_bunken_legend(body):
    r = Result("B-6", *rule_meta("B-6"))
    text = "\n".join(body)
    for kind in ("種別", "入手状況", "精読"):
        if not any(("凡例" in l and kind in l) for l in body):
            r.fail(None, "「**凡例(%s)**」の行が無い(必須・標準搭載)" % kind)
    if r.status == "ok":
        r.ok_note("凡例3種すべてあり")
    return r


# ★★探索記録の「論点ブロック」を**形で**決める(台帳 F-015・B'-2・2026-08-22)。
#   原典 run-bunken-daicho/references/daicho-format.md の節
#   「どの見出しが「論点」なのかを形で決める(F-015・2026-08-17)」が**3つとも決めている**(逐語):
#     ①「**論点ブロックの見出しは必ず `### 論点: (論点名)` で始める。**「次の一手」が要るのは
#        **この形の見出しの下だけ**である」
#     ②「探索記録セクションの中に置く**それ以外の見出し**(「注記」「補足」「使ったDB一覧」等)は
#        **論点ブロックではない**ので、「次の一手」を書かなくてよい」
#     ③「**論点を見出しではなく箇条書きで書かない。**見出しにしないと、点検プログラムからは
#        論点が1件も無い台帳に見える」
#   ★★③は**この体系が fail-open と呼んでいるものを、原典自身が名指しで禁じた句**である。
#     ⇒ 箇条書きの論点を違反にするのは**原典に無い基準の発明ではない。**
#   ★★台帳 F-015 は 2026-08-17 に**本体側だけ**適用され、`applied` 欄に逐語で
#     「本体側のみ実装。**チェッカー側は申し送りのみ**」と残っていた。ここで閉じる。
#
# ★①は「必ず `### 論点: `」と書いているが、**現物は番号・記号を挟む**
#   (`### 論点1:` `### 論点A:` `### 論点(b):`。実測: 833本の台帳で 873地点)。
#   ★★コロンまで決めうちにすると**本物の論点298地点が検査から落ち**、②を直したつもりで
#     ③の穴を広げることになる(実測して気づいた)。⇒ 見出しは「論点」で**始まる**ことだけを見る。
RONTEN_HEAD = re.compile("^#{3,4}[ \t]*論点")
# ★箇条書きの論点。**装飾を剥がしてから**見る。番号・記号は挟んでよいが、そのあとすぐコロンが要る
#   —— 「論点ブロックの見出しは…」「論点を見出しではなく…」のような**規定の文そのもの**を
#   巻き込まないためである(原典の写しが検体に混じっており、緩めると現に偽陽性が出る。実測で確認)。
RONTEN_BULLET = re.compile("^[ \t]*[-*+][ \t]+[*_`「『 \t]*論点[0-9A-Za-z()()  \t-]{0,8}[:：]")


def check_bunken_tansaku(body):
    r = Result("B-7", *rule_meta("B-7"))
    sec_i = next((i for i, l in enumerate(body) if re.match(r"^#{1,4}\s*探索記録", l.strip())), None)
    if sec_i is None:
        # ★手書きは `daicho-format.md:68-81` を名乗っていたが、2026-08-17 の bunken 改訂で
        #   その範囲は**別の規定(推奨欄の下限)**になっていた(探索記録は 174-197 に移動)。
        #   B-7 自身の原典と同じものを指すので、鍵を作らず r.origin(逐語から導出済み)を使う。
        skip_as(r, "探索記録セクションが無い。uradoriと違い「該当なし」明記の規定が原典に無いため違反としない(要目視)",
                "needs_human", origin=r.origin,
                assignee="人間(目視)")
        return r
    tail = body[sec_i:]
    heads, blocks, bullets, cur = [], [], [], None
    for off, ln in enumerate(tail):
        st = ln.strip()
        if re.match(r"^#{3,4}\s", st):
            cur = {"line": sec_i + off + 1, "head": st, "text": []}
            heads.append(cur)
            if RONTEN_HEAD.match(st):          # ★原典①② 論点で始まる見出しだけが論点ブロック
                blocks.append(cur)
            continue
        if re.match(r"^#{1,2}\s", st) and off > 0:
            break
        if RONTEN_BULLET.match(ln):            # ★原典③ 見出しにせず箇条書きで書いた論点
            bullets.append((sec_i + off + 1, st))
        if cur is not None:
            cur["text"].append(ln)
    for b in blocks:
        if "次の一手" not in "\n".join(b["text"]):
            r.fail(b["line"], "探索記録の論点「%s」に「次の一手」が無い" % b["head"][:30])
    # ★★原典③ —— 箇条書きで書かれた論点は、見出しにしない限り**点検プログラムから見えない**。
    #   原典がその穴を名指しで禁じているので、ここで拾う。**これが fail-open を塞ぐ当の行である。**
    for lineno, st in bullets:
        r.fail(lineno, "論点を見出しではなく箇条書きで書いている(点検プログラムからは論点0件に見える"
                       " — `### 論点: (論点名)` の見出しにする): %s" % st[:40])
    if r.status != "ok":
        r.note = "探索記録の見出し%d件のうち論点ブロック%d件を検査" % (len(heads), len(blocks))
        return r
    # ★★G9「**対象行0件を「全行合格」と表現しない**」。旧実装は論点が1件も無いとき
    #   「論点0件すべてに次の一手あり」と書いており、**見出しを使わなければ無条件で合格**に見えた。
    #   ⇒ 母集合(探索記録の見出しの数)と対象(論点ブロックの数)を数えて `clean` に渡す。
    #   ★これは**違反にしない**(原典は「見つからなかった論点があるなら」と条件つきで命じており、
    #     論点が1件も無いこと自体は禁じていない)。**言い方を正直にするのが G9 の要求である。**
    return clean("B-7", len(heads), len(blocks))


# ---------------------------------------------------------------- ronbun 原稿
def check_ronbun(path, raw, lines, sink=None):
    # ★段6: sink を渡されたら**そこへ積む**。規則の外で例外が起きても、
    #   すでに出た判定を呼び出し側が拾えるようにするための口である(判定は1つも変わらない)。
    results = [] if sink is None else sink
    body = strip_code_fences(lines)
    masked = [mask_noise(l) for l in body]
    text = "\n".join(masked)

    # R-1 図表参照とキャプション
    with guard(results, "R-1"):
        r = Result("R-1", *rule_meta("R-1"))
        refs, caps = {}, {}
        for i, ln in enumerate(masked):
            for m in re.finditer(r"[（(]\s*(?:次頁|前頁)?\s*図表?\s*(\d+)\s*[)）]", ln):
                refs.setdefault(m.group(1), i + 1)
            m = re.match(r"^[\s\*\-|>　]*図表?\s*(\d+)\s*[.．]", ln)
            if m:
                caps.setdefault(m.group(1), i + 1)
        if not refs and not caps:
            # 図表参照もキャプションも0件=対象0件。★「全行合格」ではない(G9)
            skip_as(r, "本文の(図表n)参照もキャプション(図表n.)も見つからない",
                    "clean", scanned=len(lines), targets=0)
        else:
            for n in sorted(refs, key=lambda x: int(x)):
                if n not in caps:
                    r.fail(refs[n], "本文が図表%s を参照しているがキャプション「図表%s.」が無い" % (n, n))
            for n in sorted(caps, key=lambda x: int(x)):
                if n not in refs:
                    r.fail(caps[n], "キャプション図表%s があるが本文から(図表%s)で参照されていない" % (n, n))
            if r.status == "ok":
                r.ok_note("参照%d件・キャプション%d件が双方向で一致" % (len(refs), len(caps)))
        results.append(r)

    # R-2 上付き引用番号と文献リスト
    guarded(results, "R-2", lambda: check_ronbun_citations(masked))

    # R-3 番号体系の混在
    with guard(results, "R-3"):
        r = Result("R-3", *rule_meta("R-3"))
        has_zuhyo = re.search(r"図表\s*\d", text)
        has_zu = re.search(r"図(?!表)\s*\d", text)
        if has_zuhyo and has_zu:
            ln = next((i + 1 for i, l in enumerate(masked) if re.search(r"図(?!表)\s*\d", l)), None)
            r.fail(ln, "「図表n」と「図n」が同一文書内に混在している(1つの文書内で混在させない)")
        elif has_zuhyo or has_zu:
            r.ok_note("「%s」体系で統一" % ("図表n" if has_zuhyo else "図n"))
        else:
            skip_as(r, "図表番号が見つからない", "clean", scanned=len(lines), targets=0)
        results.append(r)

    # R-4 句点位置
    with guard(results, "R-4"):
        r = Result("R-4", *rule_meta("R-4"))
        for i, ln in enumerate(masked):
            for m in re.finditer(r"。\s*[（(]\s*図表?\s*\d+\s*[)）]", ln):
                r.fail(i + 1, "句点が括弧の前にある: %s → 「〜となった（図表n）。」" % m.group(0).strip())
        if r.status == "ok":
            r.ok_note("該当なし")
        results.append(r)

    # R-5 用字用語(×側)
    with guard(results, "R-5"):
        r = Result("R-5", *rule_meta("R-5"))
        hits = 0
        for i, ln in enumerate(masked):
            for pat, good, src in YOJI_NG:
                for m in re.finditer(pat, ln):
                    hits += 1
                    r.fail(i + 1, "「%s」→ ◎「%s」(%s)"
                           % (m.group(0), good, origin_short(src)))
        if r.status == "ok":
            r.ok_note("×側の語 %d 種を照合、該当なし" % len(YOJI_NG))
        else:
            r.note = "×側の語 %d 種を照合" % len(YOJI_NG)
        results.append(r)

    # R-6 単位
    with guard(results, "R-6"):
        r = Result("R-6", *rule_meta("R-6"))
        for i, ln in enumerate(masked):
            rest = ln
            for word, good, src in TANI_NG:
                if word in rest:
                    r.fail(i + 1, "「%s」→ ◎「%s」(%s)"
                           % (word, good, origin_short(src)))
                    rest = rest.replace(word, "　" * len(word))
        if r.status == "ok":
            r.ok_note("単位%d種を照合、該当なし ※「トン◎/t×」は誤検出が支配的なため対象外" % len(TANI_NG))
        results.append(r)

    # R-7 全角数字
    with guard(results, "R-7"):
        r = Result("R-7", *rule_meta("R-7"))
        for i, ln in enumerate(masked):
            for m in re.finditer(r"[０-９]+", ln):
                r.fail(i + 1, "全角数字「%s」— 1ケタも半角" % m.group(0))
        if r.status == "ok":
            r.ok_note("全角数字なし")
        results.append(r)

    # R-8 5ケタ以上
    with guard(results, "R-8"):
        r = Result("R-8", *rule_meta("R-8"))
        for i, ln in enumerate(masked):
            for m in re.finditer(r"(?<![\d,万億兆．.])(\d{1,3}(?:,\d{3})+|\d{5,})(?![\d,])", ln):
                digits = len(re.sub(r"\D", "", m.group(1)))
                if digits >= 5:
                    r.fail(i + 1, "「%s」— 5ケタ以上は万・億で区切る(例 123万4,000)" % m.group(1))
            for m in re.finditer(r"\d+百万|\d{1,3},\d{3}千", ln):
                r.fail(i + 1, "「%s」— 万進法に統一する(× 123百万人 / × 1,234千人)" % m.group(0))
        if r.status == "ok":
            r.ok_note("該当なし(URL・インラインコードは除外して照合)")
        results.append(r)

    # R-9 全角英字
    with guard(results, "R-9"):
        r = Result("R-9", *rule_meta("R-9"))
        for i, ln in enumerate(masked):
            for m in re.finditer(r"[Ａ-Ｚａ-ｚ]+", ln):
                s = m.group(0)
                after = ln[m.end():m.end() + 3]
                if s == "Ｇ" and after.startswith(("8", "８")):
                    continue
                if s == "Ｕ" and after.startswith("ターン"):
                    continue
                r.fail(i + 1, "全角英字「%s」— 英字は基本的に半角(例外はＧ8・Ｕターン)" % s)
        if r.status == "ok":
            r.ok_note("該当なし")
        results.append(r)

    # R-10 元号
    with guard(results, "R-10"):
        r = Result("R-10", *rule_meta("R-10"))
        for i, ln in enumerate(masked):
            for m in re.finditer(r"(明治|大正|昭和|平成|令和)\s*(\d+|元)\s*年", ln):
                r.fail(i + 1, "「%s」— 西暦を使う" % m.group(0))
        if r.status == "ok":
            r.ok_note("該当なし")
        results.append(r)

    # R-11 プラス/マイナス
    with guard(results, "R-11"):
        r = Result("R-11", *rule_meta("R-11"))
        for i, ln in enumerate(masked):
            for m in re.finditer(r"(プラス|マイナス)\s*\d", ln):
                r.fail(i + 1, "「%s」— ◎「5％増」「3％減」の形" % m.group(0))
        if r.status == "ok":
            r.ok_note("該当なし")
        results.append(r)

    # R-12 分数
    with guard(results, "R-12"):
        r = Result("R-12", *rule_meta("R-12"))
        for i, ln in enumerate(masked):
            for m in re.finditer(r"\d\s*／\s*\d", ln):
                r.fail(i + 1, "「%s」— ◎「3分の1」" % m.group(0))
        if r.status == "ok":
            r.ok_note("該当なし")
        results.append(r)

    # R-13 並列鍵括弧の読点
    with guard(results, "R-13"):
        r = Result("R-13", *rule_meta("R-13"))
        for i, ln in enumerate(masked):
            if "」、「" in ln:
                r.fail(i + 1, "「」、「」— 並列の鍵括弧に読点を挟まない")
        if r.status == "ok":
            r.ok_note("該当なし")
        results.append(r)

    # R-14 句点は括弧の外
    with guard(results, "R-14"):
        r = Result("R-14", *rule_meta("R-14"))
        for i, ln in enumerate(masked):
            if "。」" in ln:
                r.fail(i + 1, "「。」」— 句点は閉じ括弧の外に打つ")
        if r.status == "ok":
            r.ok_note("該当なし")
        results.append(r)

    # R-15 グレー(原典が使い分けを指示)
    with guard(results, "R-15"):
        r = Result("R-15", *rule_meta("R-15"))
        for i, ln in enumerate(masked):
            for pat, note, src in YOJI_GRAY:
                for m in re.finditer(pat, ln):
                    r.gray(i + 1, "「%s」— %s (%s)"
                           % (m.group(0), note, origin_short(src)))
        if r.status == "ok":
            r.ok_note("該当なし(%d組を照合)" % len(YOJI_GRAY))
        else:
            r.note = "自動判定しない。原典が文脈での使い分けを指示している組"
        results.append(r)

    # R-16 モード依存
    with guard(results, "R-16"):
        r = Result("R-16", *rule_meta("R-16"))
        for i, ln in enumerate(masked):
            for pat, note, src in YOJI_MODE:
                for m in re.finditer(pat, ln):
                    r.gray(i + 1, "「%s」— %s (%s)"
                           % (m.group(0), note, origin_short(src)))
        if r.status == "ok":
            r.ok_note("該当なし(4組を照合)")
        else:
            r.note = "新規執筆なら用語集どおり／リライトなら原文尊重。モードを機械判定できないため要目視"
        results.append(r)

    # R-17 一人称
    with guard(results, "R-17"):
        r = Result("R-17", *rule_meta("R-17"))
        for i, ln in enumerate(masked):
            for m in re.finditer(r"(私(?:は|が|の|たち|達)|我々|我が社|当方)", ln):
                r.gray(i + 1, "一人称「%s」— 一人称は「筆者」、自分の研究は「本研究」「本稿」「本調査」" % m.group(0))
        if r.status == "ok":
            r.ok_note("該当なし")
        else:
            r.note = "引用文中の一人称は対象外のため要目視"
        results.append(r)

    # R-18 主観的評価語
    with guard(results, "R-18"):
        r = Result("R-18", *rule_meta("R-18"))
        for i, ln in enumerate(masked):
            for m in re.finditer(r"(素晴らし|非常に)", ln):
                r.gray(i + 1, "主観的評価語「%s」— 主観的評価語を避ける" % m.group(0))
        if r.status == "ok":
            r.ok_note("該当なし(原典に明示の2語のみを照合)")
        else:
            r.note = "原典が「素晴らしい・非常に等」と例示した2語のみを照合(リストを勝手に増やさない)"
        results.append(r)

    # R-19 県名+市
    with guard(results, "R-19"):
        r = Result("R-19", *rule_meta("R-19"))
        for i, ln in enumerate(masked):
            for m in re.finditer(r"(%s)県(?![内外の、。])[^\s、。（(]{1,5}市" % KYUSHU_KEN, ln):
                r.gray(i + 1, "「%s」— 九州・沖縄・山口管内の市は「〇〇市」と表記(県名を付けない)" % m.group(0))
        if r.status == "ok":
            r.ok_note("該当なし")
        else:
            r.note = "「県内の市」等の言い回しに当たることがあるため要目視"
        results.append(r)

    # R-0 門番(最後に置く。ここまでの結果に ▲ や「納品物の責任で未検査」が残っていれば違反を立てる)
    # ★★段5-3(2026-08-20)の要点を、繋いだ当人が正直に書いておく ——
    #   **この段の安全性は測れていない。**実在の R系納品物は2件しか見つかっておらず
    #   (`pipeline-kenkyu-workspace/phase3/manuscript/youkou_draft.md` と
    #    `.../phase3/uradori/youkou_badge.md`)、巻き添えを測る母数が作れない。
    #   ★その2件は**どちらも未検査0項目**なので R-0 は ○ になり、判定は動かない
    #     (どちらも別の違反で元から exit 1)。★**「安全だった」ではなく「測れていない」である。**
    # ★★門番が拾うのは R-2 の1枝**だけ**である(実測: 型判定で ronbun と同定される .md 278件で、
    #   拾われる項目を持つのは41本・すべて R-2)。R-1/R-3 の「対象0件」は `clean` なので拾わない。
    #   R-15〜R-19 は責任が**人間**(原典が文脈での使い分けを指示している組)なので拾わない ——
    #   ★**html の H-6 と同じ形である。「― を全部拾う」実装にすると R系も全滅する。**
    #   常設テスト E-17 が検体で固定している。
    # ★第4引数(表の診断)は使わない種別なので空の並びを渡す。KANMON の第4要素が None である。
    if KANMON_ON["ronbun"]:
        guarded(results, "R-0", lambda: check_kanmon("ronbun", results, lines, []))

    return results, None


# 引用記法の「痕跡」を拾う受理層の検出器(柱1)。★番号として**読めるか**は見ない。
# ここが拾うのは「この原稿は何らかの数字つきの引用らしきものを含むか」だけである。
#   <sup …>      … HTML の上付き(閉じ忘れ・中身が数字でない場合も含めて拾う)
#   ^…^          … キャレット記法
#   ⁰¹²³⁴⁵⁶⁷⁸⁹  … Unicode の上付き数字
#   [1] (1) 1)   … 角括弧・丸括弧の番号(本チェッカーが対応しない記法。**在ることだけ**を見る)
# ★この列挙は「対象外」を**狭める**方向にしか効かない —— 記法を1つ足すと、対象外だった原稿が
#   「読めなかった(partial)」へ移るだけで、その逆は起きない。だから F-025 の「列挙を増やす形の
#   修正は同じ穴を別の名前で再生産する」型には当たらない(あちらは列挙が**合格を与える**側だった)。
#
# ★★申-16(2026-08-20)の判断: `^n^` の `\^\S` は `2^10` のような**数式も拾う**。これを
#   `\^\d+\^`(閉じた対)へ**絞るかどうかを検討し、絞らないと決めた。**理由は3つ:
#   (1) ★**原典に根拠が無い**(規則表 deliverable-rules.md の原則1)。原典は本文の引用を
#       「上付き番号」と定めているだけで、**数式のキャレットと引用のキャレットを見分ける規則を
#       どこにも与えていない**。見分け方を書けば、それは原典に無い基準の発明である。
#   (2) ★★**絞るほうが危ない側へ倒れる。**痕跡がゼロになった原稿は、文献リストの見出しが
#       在れば `ronbun_cite_state([])` が **責任=納品物**を返す ⇒ **門番が拾って納品を止める。**
#       実測(合成入力): 「本文に `2^10`・見出し `## 参考文献` が在る原稿」は
#       いま 責任=チェッカー(止めない)だが、絞ると 責任=納品物(**止める**)へ動く。
#       ★**書き手に落ち度が無い原稿を新たに止める** —— 段5-3 が直したのと同じ**逆向きの事故**である。
#   (3) 絞らないことの代償も実測した。母集合278件のうち `\^\S` が拾うのは**5件**で、
#       いずれも数式か規則表の引用であり、**絞っても絞らなくても判定は1件も動かない**(実測0件)。
#       責任=チェッカーは門番が拾わないので、**納品を止めることは無い**。
#   ⇒ ★**払う代償は「未検査の1行」だけ**であり、絞って払う代償は「無実の原稿を止めること」である。
#     常設テスト E-16c がこの決定を固定する(黙って絞れないようにする)。
CITE_MARKS = [
    ("<sup>",        re.compile(r"<\s*sup\b", re.I)),
    ("^n^",          re.compile(r"\^\S")),
    ("Unicode上付き", re.compile(r"[⁰¹²³⁴⁵⁶⁷⁸⁹]")),
    ("[n]/(n)",      re.compile(r"[\[［(（]\s*\d{1,3}\s*[\]］)）]")),
]


# ★本スクリプトが**番号として読める**と名乗っている記法。段5-3(2026-08-20)に
#   `check_ronbun_citations` の中から持ち上げた(中身は1文字も変えていない)。
#   ★★持ち上げた理由は責任の所在の**独立な検算**である —— 原典は本文の引用記法を
#     「上付き番号」と定めており、この並びはその上付き記法そのものである。
#     ⇒ **ここに名前が在るのに番号を読めなかったのなら、落ち度は書き手ではなく本スクリプトにある。**
#     常設テスト E-16 は `RONBUN_CITE_RESP` の期待値をこの並びから作る(表そのものからは作らない
#     —— 表を1マス誤る変異と同じ誤りを期待値も共有すると、何も検出しなくなる)。
#   ★★申-16(2026-08-20): `<sup>` の読み手が**属性を許していなかった**。`<sup class="fn">1</sup>`
#     は原典どおりの上付き番号(原典は記法の綴りではなく「上付き番号」を定めている)なのに
#     読めず、段5-3 はそれを**責任=チェッカー**に分類して**未検査のまま置いた**。
#     分類は正しかったが**読めるようにはしていなかった** —— その宿題がこれである。
#     ⇒ 開きタグの属性・タグ内の空白・大文字小文字を許す形に広げた。
#     ★**閉じ忘れ(`<sup>1`)は読まない。**原典は上付き番号を定めているが、閉じていない印は
#       どこで番号が終わるのか原典のどこにも書かれていない(`<sup>12 である` の番号は 12 か 1 か)。
#       当てずっぽうで読むと**文献リストとの照合に偽の違反(✕)を作る**。読まない側に倒した。
#   ★★申-17(2026-08-20)で**原典側を確かめ、「いまのままが正しい」と結論した**(何も変えていない):
#     (1) 原典が定めているのは**意味**である —— 逐語「本文では「著者（発表年）上付き番号」で
#         引用する」(style-guide.md)。★**綴り(閉じタグの要否)を定める句は原典のどこにも無い。**
#         原典が挙げる実例そのものが**素の数字**であり(「中村（2012）16」)、
#         `<sup` という綴りは ronbun-shippitsu の .md に**1文字も出てこない**(実測)。
#         成果物の形式も Word / Markdown / チャット本文から毎回選ぶ(SKILL.md)ので、
#         ★**原典はそもそもマークアップ言語を前提にしていない。**
#     (2) ★**綴りを定めている種別では扱いが違う** —— html は原典 run-html-visualizer/SKILL.md が
#         「**構文**: タグの閉じ整合(…)を確認する」と定めており、だから H-2 は閉じ忘れを
#         **納品物の落ち度**として捕まえる。★ronbun の原典にはその句が無い。差はここである。
#     (3) 実測(`skill-review-harness\runs\checker\evidence\shin17-handan.txt`): 読む側へ倒すと、
#         欲張り読み・控えめ読みの**どちらに決めても**、その決めに合わない原稿で**偽の違反(✕)**が
#         現に出る。責任を納品物へ移すと、**原典がどこでも咎めていない原稿で終了コードが 0→1**
#         になる(門番が納品を止める)。★段5-3 が直したのと同じ**逆向きの事故**である。
#     ⇒ どちらも**原典に無い基準の発明**(規則表 deliverable-rules.md の原則1)なので採らない。
#     ★歯止め: **読まない側は E-16b**、★**責任を移さない側は E-16d** が固定する
#       (申-17 の前、責任の側は**誰も見張っておらず**、記法名を割る変更は1項目も赤くせずに
#        通った —— 1568→1573 全緑。`evidence\shin17-hadome.txt` がその実測と、塞いだ後の対照)。
CITE_READERS = (("<sup>", r"(?i)<\s*sup\b[^>]*>\s*(\d+)\s*[)）]?\s*<\s*/\s*sup\s*>"),
                ("^n^", r"\^(\d+)\^"),
                ("Unicode上付き", r"([¹²³⁰⁴-⁹]+)"))


def cite_read(text):
    """本文から**現に読めた**上付き引用番号を返す。返り値 (記法の名前 or None, 番号の集合)。

    ★`check_ronbun_citations` の中から持ち上げた(申-16・2026-08-20)。**中身は変えていない。**
      持ち上げた理由は段5-3 で `CITE_READERS` を持ち上げたのと同じ ——
      常設テストが「**読めると名乗っているのは本当か**」を確かめるとき、読み取りを写して
      持つと、写しと本体が食い違っても誰も気づかない。★**本体そのものを呼ばせる。**
    """
    for name, pat in CITE_READERS:
        found = re.findall(pat, text)
        if not found:
            continue
        if name == "Unicode上付き":
            table = str.maketrans("¹²³⁰⁴⁵⁶⁷⁸⁹", "1230456789")
            return name, {f.translate(table) for f in found}
        return name, set(found)
    return None, set()


def citation_marks(text):
    """引用記法の痕跡の名前を返す(無ければ空リスト)。"""
    return [name for name, pat in CITE_MARKS if pat.search(text)]


# ---- 段5-3(2026-08-20): 上付き番号が読めなかったときの「責任の所在」を原典から決める ------
# ★ここに表が無かったことが、段5-3 の工事の中身である。bunken の `BUNKEN_COL_REQ`・
#   html の `HTML_ARG_SUPPLIER` と**同じ形の欠落**で、これが3件目である。
#   検出した記法が何であれ一律 `partial`(責任=納品物)に落としており、実装のどこも
#   「なぜ書き手の責任なのか」を指していなかった。
#   ★段5-3 で門番を R系に繋ぐと、この値が**納品を止めるか止めないかを直接決める**
#     (門番は責任が「チェッカー」のものを拾わない)。根拠の無い値に納品の可否を委ねない。
#
# ★★分類が誤っていた枝が現にある(合成入力で実測。常設テスト E-5):
#     `<sup class="fn">1</sup>` は**原典どおりの上付き記法**だが、読み手側の正規表現が
#     `<sup>\s*(\d+)…` と属性を許していないため番号を読めない。旧実装はこれを
#     「書き手が書式を直せば検査できる欠落」に数えていた。門番を繋げば、
#     **原典どおりに書いた原稿で納品が止まる**——bunken の推奨列とまったく同じ
#     **逆向きの事故**である。読めなかったのは書き手ではなく**本スクリプトの側**である。
#
# ★下の表は原典 run-ronbun-shippitsu/references/style-guide.md の**1句の転記であって、
#   新しい基準ではない**(規則表 deliverable-rules.md の原則1)。原典は本文の引用記法を
#   「上付き番号」と定めている。だから四つの記法は**上付きか否か**で一意に割れる ——
#   括弧番号 `[n]`/`(n)` は原典が**文献リストの側**に与えた形(formats.md の
#   「リストは `[n]著者,年,…`」)であって、本文の引用記法ではない。
# ★記法を足す者は `CITE_MARKS` とこの表の**両方**に足すこと。片方だけだと KeyError で
#   即死する(黙って合格側へ流れない形)。顔ぶれの一致は常設テスト E-16 が毎回数える。
RONBUN_CITE_RESP = {
    # 記法の名前:      (原典の鍵(控えは ORIGIN_FALLBACK に集約),  読めなかったときの責任)
    "<sup>":          ("RCITE:本文中は上付き番号", "チェッカー"),
    "^n^":            ("RCITE:本文中は上付き番号", "チェッカー"),
    "Unicode上付き":  ("RCITE:本文中は上付き番号", "チェッカー"),
    "[n]/(n)":        ("RCITE:本文中は上付き番号", "納品物"),
}


def ronbun_cite_resp(mark):
    """その記法が読めなかったときの責任を返す。★添字で取り出さない(`col_req` と同じ理由)。"""
    return RONBUN_CITE_RESP[mark][1]


def ronbun_cite_origin(mark):
    """その記法の責任を定めている原典の鍵。★画面に出す位置はここから導く(手書きしない)。"""
    return RONBUN_CITE_RESP[mark][0]


def ronbun_cite_state(marks):
    """上付き番号が読めなかったときの7状態を、原典の引用記法の表から決める。返り値 (state, info)。

    ★1つでも「原典が本文に定めた形ではない記法」(括弧番号)が在れば、書き手が上付きへ直せば
      検査できる ⇒ 責任=**納品物**(門番が拾う)。
    ★検出したのが原典どおりの上付き記法だけなら、読めなかったのは**本スクリプトの側**である
      ⇒ 責任=**チェッカー**(門番は拾わない)。★これは免罪ではなく**チェッカー側の宿題**であり、
      画面にもそう出る。読み手が「合格だった」と誤読しないよう、記号は従来どおり「―」のままで
      未検査に数える。
    ★記法の痕跡が1つも無いのにここへ来るのは「文献リストだけが在る」場合で、
      相互対応の片側を書き手が書いていない ⇒ 納品物。
    """
    outsiders = [m for m in marks if ronbun_cite_resp(m) == "納品物"]
    if marks and not outsiders:
        return "missing_input", {"what": "読める上付き引用番号", "supplier": "チェッカー"}
    return "missing_input", {"what": "読める上付き引用番号", "supplier": "納品物"}


def ronbun_cite_why(marks):
    """★画面に出る一文。責任も原典の位置も**表から導く**(手書きだと原典の改稿で嘘になる)。"""
    outsiders = [m for m in marks if ronbun_cite_resp(m) == "納品物"]
    if marks and not outsiders:
        return ("検出した痕跡(%s)は原典どおりの上付き記法のものだけなので、読めなかったのは"
                "本スクリプトの側である(責任=チェッカー・書式を直す必要はない)"
                "— 引用ではない記述(数式の ^ など)を拾っている場合もこちらに数える" % "・".join(marks))
    if outsiders:
        return ("%s は原典が本文に定めた引用記法ではない(%s 本文は上付き番号)— "
                "上付きに直せば照合できる(責任=納品物)"
                % ("・".join(outsiders), origin_short(ronbun_cite_origin(outsiders[0]))))
    return ("本文に引用記法の痕跡が1つも無く、相互対応の片側が書かれていない"
            "(%s 本文は上付き番号)— 責任=納品物" % origin_short("RCITE:本文中は上付き番号"))


# 文献リストの見出し: `## 参考文献` / `【引用・参考文献】` / 素の `引用・参考文献` など(ch-4f9)
RONBUN_LIST_HEAD_RE = re.compile(
    r"^(?:#{1,4}\s*)?(?:【\s*(?:引用・参考文献|引用文献|参考文献|文献)\s*】|(?:引用・参考文献|引用文献|参考文献|文献))\s*$")


def check_ronbun_citations(masked):
    r = Result("R-2", *rule_meta("R-2"))
    text = "\n".join(masked)
    pat_used, body_nums = cite_read(text)
    # 文献リスト
    # ★2026-10-17(ch-4f9・ユーザー決定「型の3つを全部読む」): 見出しは `#` 付きの行だけを読んでいたため、
    #   原典 run-ronbun-shippitsu/references/formats.md が定める型どおりの原稿が ✕ になっていた
    #   (タイプA の `【引用・参考文献】`・タイプB の `#` 無しの `引用・参考文献`・形式A-1 の全角 `［1］`)。
    #   ⇒ 見出しは `#` 付き・`【】` 囲み・素の行のどれでも読み、`【…】` の行もリストの終わりとする。
    list_i = next((i for i, l in enumerate(masked)
                   if RONBUN_LIST_HEAD_RE.match(l.strip())), None)
    list_nums = set()
    if list_i is not None:
        for ln in masked[list_i + 1:]:
            if re.match(r"^#{1,4}\s", ln.strip()) or re.match(r"^【[^】]+】\s*$", ln.strip()):
                break
            m = re.match(r"^\s*[\[［（(]?(\d+)[\]］）).．]", ln.strip())
            if m:
                list_nums.add(m.group(1))
    if not body_nums and list_i is None:
        # ★受理層で2つに分ける(2026-08-17 ユーザー判断2)。かつては両方を partial に寄せており、
        #   **引用の無い正当な原稿まで「読めなかった」と言う過大報告**になっていた。
        #   原典 run-ronbun-shippitsu/SKILL.md:85 が求めるのは本文とリストの**相互対応**であって
        #   **引用があること**ではない。引用の無い原稿(短い梗概など)は規定違反ではないので、
        #   機械が ▲/✕ にすれば原典に無い基準の発明にあたる(規則表 :9 原則1)。
        marks = citation_marks(text)
        if not marks:
            skip_as(r, "引用記法の痕跡が本文に1つも無く、文献リストの見出しも無い — "
                       "原典が求めるのは本文とリストの相互対応であって引用の存在ではないため対象外",
                    "not_applicable", origin=r.origin)
            return r
        # ★段5-3(2026-08-20): 責任の所在を **RONBUN_CITE_RESP(原典の1句の転記)** から決める。
        #   旧実装は一律 `partial`(責任=納品物)で、しかも注記が「本スクリプトの対象外」と
        #   言いながら分類は「書き手の欠落」だった ——**宣言と分類が食い違っていた**
        #   (bunken の B-5 で踏んだのと同じ形)。
        #   ★状態も `partial` から `missing_input` へ改めた。`read=0/total=行数` は
        #     「1行も読めなかった」という**事実に反する申告**である(全行読めている。
        #     無いのは上付き番号のほうだ)。missing_input は「検査に必要な情報が無い」で、
        #     供給者を名乗ることを型が要求する。
        state, info = ronbun_cite_state(marks)
        skip_as(r, "引用記法らしき記述(%s)は在るが上付き番号として読めず、文献リスト見出しも無い — %s"
                % ("・".join(marks), ronbun_cite_why(marks)), state, **info)
        return r
    if not body_nums:
        # ★文献リストの見出しが在る以上「相互対応の相手」が存在するので、規定の対象外ではない。
        #   ★責任は上と同じ表から決める —— 本文の記法が原典どおりの上付きなのに読めないのなら、
        #     それは書き手ではなく本スクリプトの側の落ち度である。
        marks = citation_marks(text)
        state, info = ronbun_cite_state(marks)
        skip_as(r, "上付き引用番号の記法(<sup>n</sup> / ^n^ / Unicode上付き)を検出できない — "
                   "文献リストは%d件 — %s" % (len(list_nums), ronbun_cite_why(marks)),
                state, **info)
        return r
    if list_i is None:
        r.fail(None, "本文に上付き引用番号(%s)があるが「引用文献」「参考文献」「【引用・参考文献】」の見出しが無い" % pat_used)
        return r
    for n in sorted(body_nums, key=int):
        if n not in list_nums:
            r.fail(None, "本文の上付き番号 %s が文献リストに無い" % n)
    for n in sorted(list_nums, key=int):
        if n not in body_nums:
            r.fail(list_i + 1, "文献リストの %s が本文で参照されていない" % n)
    if r.status == "ok":
        r.ok_note("本文%d件・リスト%d件が双方向で一致(記法: %s)" % (len(body_nums), len(list_nums), pat_used))
    return r


# ---------------------------------------------------------------- html-visualizer 成果物
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
             "meta", "param", "source", "track", "wbr"}
# SKILL.md:70「主要コンテナ・style・scriptの開閉対応」。p/li/td 等の省略可能タグは誤検出源のため対象外。
CONTAINER_TAGS = {"html", "head", "body", "style", "script", "div", "section", "article",
                  "main", "header", "footer", "nav", "aside", "table", "thead", "tbody",
                  "tfoot", "tr", "ul", "ol", "details", "figure", "form", "svg", "select"}
SRC_ATTRS = {"script": "src", "img": "src", "iframe": "src", "video": "src", "audio": "src",
             "source": "src", "embed": "src", "track": "src", "object": "data",
             "link": "href", "image": "href", "use": "href", "input": "src"}

# ---- 柱5②(2026-10-04・H-7): 実行時の通信 —— 原典が名指す4つの書き方 -------------------
# ★原典の逐語(run-html-visualizer/SKILL.md「絶対制約: 完全自己完結」)=
#   「**実行時に外部と通信しない。**`fetch` / `XMLHttpRequest` / WebSocket / 動的な `import()` など、
#    **開いたあとにネットワークへ取りに行く書き方をしない**」。
# 🔴★★**「など」の先は足さない**(R-18 と同じ作法「リストを勝手に増やさない」)。
#   ★`DESIGN.md` 柱5 の逐語「機械にできるのは `fetch(` 等の【列挙】だけで、F-025 で『列挙は穴を別の名前で
#     再生産する』と実証済み」。⇒ ★名前を足しても穴は閉じない。★だから ✕ にせず △ にとどめ(ユーザー決定
#     2026-08-17)、★**照合しない口を毎回の画面に名指しで出す**(`00-principles.md` §12)。
# ★字面は識別子の境で切る(`prefetch`・`fetchData` には当てない)。★`fetch` は呼び出しの括弧を要求しない
#   (`const f = window.fetch;` のように名前だけで持ち出す書き方も拾う。★△ なので、拾いすぎの損は人が1回見ることだけ)。
HTML_RUNTIME_NET = (
    ("fetch", re.compile(r"(?<![\w$])fetch(?![\w$])")),
    ("XMLHttpRequest", re.compile(r"(?<![\w$])XMLHttpRequest(?![\w$])")),
    ("WebSocket", re.compile(r"(?<![\w$])WebSocket(?![\w$])")),
    ("動的な import()", re.compile(r"(?<![\w$.])import\s*\(")),
)
# ★原典の「など」の先(★名指しの例であって全部ではない)。★画面に出すだけで、照合には使わない。
HTML_RUNTIME_NET_OUTSIDE = ("字面を変えた書き方(window['fe'+'tch'] など)・EventSource・navigator.sendBeacon・"
                            "Worker・script 要素を作って読み込む書き方・静的な import 文・meta refresh・iframe の srcdoc の中")
# ★script 要素の開始タグ。★`<script` のあとに区切り(空白・/・>)が要る(`<scripts>` には当てない)。
#   ★注釈 `<!-- … -->` や属性の値の中の `<script` も開始と見なす(★拾いすぎる向き。△ なので損は人が1回見ることだけ)。
#   🔴★**注釈を飛ばす作りにしない** —— 属性の値に `<!--` を書くと、本物の script まで注釈として飛ばせてしまう(★素通りの向き)。
HTML_SCRIPT_OPEN_RE = re.compile(r"<script(?=[\t\n\f\r />])[^>]*>", re.I)
# ★script 要素の中身の終わり方 —— HTML の仕様の「script data」の3つの状態をそのまま写す。
#   0= script data(`<!--` で 1 へ / `</script` で終わり)
#   1= escaped(`-->` で 0 へ / `</script` で終わり / `<script` で 2 へ)
#   2= double escaped(`-->` で 0 へ / `</script` で 1 へ戻る —— ★ここでは終わらない)
#   ★2026-10-05: 最初の版は「最初の `</script>` で終わり」の正規表現だった。★`<!-- <script> </script> -->` を
#     中身に書くと、ブラウザは次の `</script>` で閉じずに先を実行するのに、その先を見ずに ○ を出していた
#     (★迂回する動機のある書き方。常設テスト LD-80)。
_HTML_SCRIPT_TOK = (
    re.compile(r"<!--|</script(?=[\t\n\f\r />])", re.I),
    re.compile(r"-->|</script(?=[\t\n\f\r />])|<script(?=[\t\n\f\r />])", re.I),
    re.compile(r"-->|</script(?=[\t\n\f\r />])", re.I),
)


def html_script_bodies(raw):
    """★script 要素の中身を〈始まりの位置, 終わりの位置〉で返す(★ブラウザと同じ所で閉じる)。
    ★閉じていない script は最後まで(★H-2 が閉じ忘れを別に ✕ にする)。"""
    out, i = [], 0
    while True:
        m = HTML_SCRIPT_OPEN_RE.search(raw, i)
        if m is None:
            return out
        j, state, end = m.end(), 0, len(raw)
        while True:
            t = _HTML_SCRIPT_TOK[state].search(raw, j)
            if t is None:
                break
            tok, j = t.group(0).lower(), t.end()
            if tok == "<!--":
                state = 1
                continue
            if tok == "-->":
                state = 0
                continue
            if tok == "<script":
                state = 2
                continue
            if state == 2:
                state = 1
                continue
            end = t.start()
            break
        out.append((m.end(), end))
        i = end


def html_script_sources(raw, scan):
    """★H-7: スクリプトの中身を〈行, 中身, どこ〉で返す。★口は3つ —— script 要素の中身 / on〜 属性の値 /
    javascript: の URL(後の2つは `HtmlScan._attrs` が集める)。★行は中身の始まりの行(属性はタグの行)。"""
    out = [(raw.count("\n", 0, a) + 1, raw[a:b], "script 要素") for a, b in html_script_bodies(raw)]
    return out + scan.scripts


class HtmlScan(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.tag_errors = []
        self.external = []
        self.has_theme = False
        self.doctype = False
        # ★H-7(柱5②・2026-10-04): 属性に書かれたスクリプト〈行, 中身, どこ〉(on〜 属性 / javascript: の URL)
        self.scripts = []

    def handle_decl(self, decl):
        if decl.lower().startswith("doctype"):
            self.doctype = True

    def handle_startendtag(self, tag, attrs):
        self._attrs(tag, attrs)

    def handle_starttag(self, tag, attrs):
        self._attrs(tag, attrs)
        if tag in CONTAINER_TAGS and tag not in VOID_TAGS:
            self.stack.append((tag, self.getpos()[0]))

    def handle_endtag(self, tag):
        if tag not in CONTAINER_TAGS:
            return
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                for t, ln in self.stack[i + 1:]:
                    self.tag_errors.append((ln, "<%s> が閉じられないまま </%s> が来ている" % (t, tag)))
                del self.stack[i:]
                return
        self.tag_errors.append((self.getpos()[0], "対応する開始タグの無い </%s>" % tag))

    def _attrs(self, tag, attrs):
        line = self.getpos()[0]
        for k, v in attrs:
            if k == "data-theme" or (k == "onclick" and v and "data-theme" in v):
                self.has_theme = True
            if v is None:
                continue
            # ★H-7(柱5②): 属性に書かれたスクリプトを集める —— on〜 属性の値 / javascript: の URL
            if k.startswith("on"):
                self.scripts.append((line, v, "%s 属性" % k))
            if not k.startswith("on") and v.strip().lower().startswith("javascript:"):
                self.scripts.append((line, v, "%s の javascript: の URL" % k))
            if k == "style" and re.search(r"url\(", v):
                for m in re.finditer(r"url\(\s*['\"]?([^'\")]+)", v):
                    if not m.group(1).strip().startswith(("data:", "#")):
                        self.external.append((line, "style属性のurl(%s)" % m.group(1)[:60]))
            if SRC_ATTRS.get(tag) == k:
                val = v.strip()
                if val.startswith(("data:", "#")) or val == "":
                    continue
                self.external.append((line, "<%s %s=\"%s\">" % (tag, k, val[:60])))


# ---- 段5-2(2026-08-19): 引数が与えられなかったときの状態を「原典」から決める ----------
# ★ここに表が無かったことが、段5-2 の工事の中身である。bunken の `BUNKEN_COL_REQ` と同じ筋 ——
#   H-5 の2つの枝は `supplier="呼び出し"` を**その場に手書き**しており、実装のどこも
#   「なぜ呼び出しなのか」を指していなかった。分類は正しかったが**根拠が無かった**。
#   ★段5-2 で門番を html に繋ぐと、この値が**納品を止めるか止めないかを直接決める**
#     (門番は責任が「呼び出し」のものを拾わない)。根拠の無い値に納品の可否を委ねない。
#
# ★下の表は原典 run-html-visualizer/SKILL.md の**1句の転記であって、新しい基準ではない**
#   (規則表 deliverable-rules.md の原則1)。引数を足す者はまず原典のその句に足すこと。
# ★★`--artifact` を**この表に入れない**。理由は2つあり、どちらも実測に基づく:
#   ① `--artifact` は「与えられなかった」状態が無い —— 付けなければ**ファイル出力**という
#      正当な様式になるだけで、検査に必要な情報が欠けるわけではない(H-3・H-4 は様式で分岐する)。
#      入れれば「不在の状態」を持たない行になり、どの規則からも引かれない。
#   ② どの規則にも接続しない行は**等価変異にしかならず殺傷率を薄める**。同じ形の
#      `UNSUPPORTED_POLICY` が現にその状態にあり、申-13 として別に起票されている。
#   ⇒ **表に入れるのは「不在が7状態を生む引数」だけ**である。常設テスト E-14 が
#      「原典の当該句から独立に読み出した引数の顔ぶれ」と表を突き合わせて毎回数える。
HTML_ARG_SUPPLIER = {
    # 引数:            (原典の鍵(控えは ORIGIN_FALLBACK に集約),  原典が定める供給者)
    "--expect-count":  ("HARG:全量保持の2引数は付けたときだけ照合される", "呼び出し"),
    "--count-pattern": ("HARG:全量保持の2引数は付けたときだけ照合される", "呼び出し"),
}


def html_arg_supplier(arg):
    """その引数を供給するのは誰かを返す。★添字で取り出さない(`col_req` と同じ理由)。"""
    return HTML_ARG_SUPPLIER[arg][1]


def html_arg_origin(arg):
    """その引数の供給者を定めている原典の位置。★**画面に出る**ので導出する(手書きにしない)。"""
    return origin_short(HTML_ARG_SUPPLIER[arg][0])


def html_missing_arg_state(arg):
    """その引数が与えられなかったときの7状態を、原典の供給者表から決める。返り値 (state, info)。

    ★`missing_input` である(規定による対象外ではない)—— 突合そのものは原典が求めている検査で、
      「この納品物には適用されない」わけではない。**足りないのは入力のほうで、出どころが呼び出し側**
      というだけである。だから記号は「―」でも「検査しなくてよかった」ではない。
    ★責任を「納品物」に誤ると、門番が拾って**書き手に直せない物で納品を止める**(逆向きの事故)。
      逆に本当に納品物の欠落を「呼び出し」へ寄せれば、欠陥が門番をすり抜ける。どちらもここで決まる。
    """
    # ★2026-10-05(起票 `KICKOFF-kanmon-bunmen.md`): ★この状態は「その引数が与えられなかった」なので、
    #   「渡していない」(handed=False)を名乗る(★門番がこの ▲ を「呼び出し側から渡らなかった」と書いてよい根拠)。
    return "missing_input", {"what": arg, "supplier": html_arg_supplier(arg), "handed": False}


def check_html(path, raw, lines, artifact=False, expect_count=None, count_pattern=None, sink=None):
    # ★段6: sink を渡されたら**そこへ積む**。規則の外で例外が起きても、
    #   すでに出た判定を呼び出し側が拾えるようにするための口である(判定は1つも変わらない)。
    results = [] if sink is None else sink
    scan = HtmlScan()
    parse_error = None
    try:
        scan.feed(raw)
        scan.close()
    except Exception as e:      # 壊れたHTMLでも他項目の報告は続ける
        parse_error = str(e)

    # H-1 外部リソース
    with guard(results, "H-1"):
        r = Result("H-1", *rule_meta("H-1"))
        for line, msg in scan.external:
            r.fail(line, "外部リソース参照: %s — CSS・JSはすべてインライン、外部CDN・Webフォント・外部画像は参照しない" % msg)
        for i, ln in enumerate(lines):
            for m in re.finditer(r"@import\s+(?:url\()?\s*['\"]?([^'\");]+)", ln):
                if not m.group(1).strip().startswith("data:"):
                    r.fail(i + 1, "CSSの@import: %s" % m.group(1)[:60])
            for m in re.finditer(r"url\(\s*['\"]?(https?://[^'\")]+)", ln):
                r.fail(i + 1, "CSSのurl()が外部を指している: %s" % m.group(1)[:60])
        if r.status == "ok":
            r.ok_note("script/link/img/iframe/video/audio/source/embed/object/use のsrc・data、@import、url() を照合(<a href>は対象外)")
        results.append(r)

    # H-2 タグ開閉
    with guard(results, "H-2"):
        r = Result("H-2", *rule_meta("H-2"))
        if parse_error:
            r.fail(None, "HTMLの解析に失敗: %s" % parse_error)
        for line, msg in scan.tag_errors:
            r.fail(line, msg)
        for tag, line in scan.stack:
            if tag in ("html", "head", "body") and artifact:
                continue
            r.fail(line, "<%s> が閉じられていない" % tag)
        if r.status == "ok":
            r.ok_note("主要コンテナ・style・scriptの開閉が一致(p/li/td等の省略可能タグは対象外)")
        results.append(r)

    # H-3 骨格
    with guard(results, "H-3"):
        r = Result("H-3", *rule_meta("H-3"))
        low = raw.lower()
        # タグ名の直後に区切り(空白・>・/)を要求する。単純な部分一致だと
        # <header> が "<head" に、<bodyfoo> が "<body" に当たって誤検出する
        # (<header> は generic.md レポート型が定める標準構成なので必ず踏む)。
        SKELETON = (("<!doctype", r"<!doctype\s"), ("<html", r"<html[\s>/]"),
                    ("<head", r"<head[\s>/]"), ("<body", r"<body[\s>/]"))
        present = [name for name, pat in SKELETON if re.search(pat, low)]
        if artifact:
            if present:
                r.fail(None, "アーティファクト出力では %s を書かない(スケルトンは発行時に付与される)" % "・".join(present))
            else:
                r.ok_note("DOCTYPE/html/head/body なし(アーティファクト前提として正しい)")
        else:
            lack = [name for name, pat in SKELETON if not re.search(pat, low)]
            if lack:
                r.fail(None, "ファイル出力では完全なHTML文書にする。欠けている: %s（アーティファクトなら --artifact を付ける）"
                       % "・".join(lack))
            else:
                r.ok_note("DOCTYPE〜body の完全なHTML文書")
        results.append(r)

    # H-4 画面は明るい色だけ・body に背景色(2026-10-18。ch-6o6・ユーザーの決定 D42)
    #   ★ファイルでもアーティファクトでも同じに見る。★見つけたものは △ —— 暗い画面を
    #     ユーザーが頼んだかは機械に見えない(頼まれた暗い画面を ✕ にすると納品できなくなる)。
    with guard(results, "H-4"):
        r = Result("H-4", *rule_meta("H-4"))
        dark = []
        if re.search(r"prefers-color-scheme\s*:\s*dark", raw, re.I):
            dark.append("prefers-color-scheme: dark")
        if re.search(r"data-theme\s*=\s*[\"']?dark", raw, re.I) or "dataset.theme" in raw:
            dark.append("data-theme の暗い画面・切替")
        css = "\n".join(re.findall(r"<style[^>]*>(.*?)</style>", raw, re.S | re.I))
        css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
        has_bg = any("body" in [x.strip() for x in m.group(1).split(",")]
                     and re.search(r"background(-color)?\s*:", m.group(2))
                     for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", css))
        has_bg = has_bg or bool(re.search(r"<body[^>]*\sstyle\s*=\s*[\"'][^\"']*background", raw, re.I))
        if dark:
            # ★この理由文は**画面に出る**。位置は逐語から導出する
            r.gray(None, "%s の規定で、暗い画面はユーザーが頼んだ時だけ付ける。暗い画面の規則がある(%s)"
                   " — 頼まれていなければ外す" % (origin_short("MSG:H-4:暗い画面は頼まれた時だけ"), "・".join(dark)))
        if not has_bg:
            r.gray(None, "body に背景色の指定が見つからない(<style> の body の規則と body の style 属性を見た)"
                   " — 明るい背景色を指定する")
        if r.status == "ok":
            r.ok_note("明るい画面だけ・body に背景色あり")
        results.append(r)

    # H-5 全量保持
    with guard(results, "H-5"):
        r = Result("H-5", *rule_meta("H-5"))
        if expect_count is None:
            # ★★段5-2(2026-08-19): 供給者を**その場に手書きせず**、原典を指す表から引く。
            #   供給者は「呼び出し」なので門番は拾わない —— 書き手には直せないからである(柱2)。
            #   ★理由文は**画面に出る**。位置は逐語から導出する(手書きだと原典の改稿で嘘になる)。
            st, info = html_missing_arg_state("--expect-count")
            skip_as(r, "--expect-count が未指定。入力の件数(案数・手法数・ステージ数)は外から与えないと突合できない"
                       "——この引数を供給するのは%s側である(%s)"
                    % (html_arg_supplier("--expect-count"), html_arg_origin("--expect-count")),
                    st, **info)
        elif not count_pattern:
            st, info = html_missing_arg_state("--count-pattern")
            skip_as(r, "--count-pattern が未指定。何を数えるかを与えないと突合できない"
                       "——この引数を供給するのは%s側である(%s)"
                    % (html_arg_supplier("--count-pattern"), html_arg_origin("--count-pattern")),
                    st, **info)
        else:
            got = len(re.findall(count_pattern, raw))
            if got != expect_count:
                r.fail(None, "件数不一致: 入力%d件 に対しHTML内は%d件(パターン: %s)" % (expect_count, got, count_pattern))
            else:
                # ★★この開示は**画面に出る**。位置は逐語から導出する(手書きだと原典の改稿で嘘になる)。
                #   ★合格の行にだけ添える —— 突合そのものは通ったが、
                #     **その N が入力を数えた値なのかは機械には見えない**からである。
                r.ok_note("入力%d件とHTML内%d件が一致 ※この N がどこから来たかは機械では"
                          "検証できない——2引数を正しく選ぶ責任は渡す側にある(%s)"
                          % (expect_count, got,
                             origin_short("MSG:H-5:件数の出どころは機械では検証できない")))
        results.append(r)

    # H-6 テンプレート必須要素
    with guard(results, "H-6"):
        r = Result("H-6", *rule_meta("H-6"))
        # ★規則未実装。原典が**目視のまま**と人間へ明示的に割り当てているので、
        #   機械側で違反にすれば規則表 :9 の原則1(新しい品質基準を発明しない)に反する。
        skip_as(r, "必須要素は使用テンプレート(run-html-visualizer/references/*.md)ごとに定義される。"
               "今回の照合対象外——テンプレの規定は目視で確認すること",
               # ★H-6 自身の原典と同じ(要求の本体 + 「機械照合の対象外——目視のまま」の割り当て行)。
               #   後者こそ needs_human の根拠なので、r.origin にすると根拠が1つ増えて正確になる。
               "needs_human", origin=r.origin, assignee="人間(目視)")
        results.append(r)

    # H-7 実行時の通信(柱5②・2026-10-04・起票 `KICKOFF-a-nokori.md`)
    # ★原典が名指す4つの書き方をスクリプトの中から字面で探し、在れば △(要目視)。★✕ にはしない ——
    #   実行時に通信するかは読むだけでは決まらない(`DESIGN.md` 柱5・ユーザー決定 2026-08-17「機械側は当面 △」)。
    # ★△ の責任は「人間」なので、門番 H-0 は拾わない・終了コードにも出ない(★納品は止めない)。
    # ★照合しない口(原典の「など」の先)は、合格のときも △ のときも毎回の文に出す(`00-principles.md` §12)。
    with guard(results, "H-7"):
        r = Result("H-7", *rule_meta("H-7"))
        srcs = html_script_sources(raw, scan)
        for line0, code, where in srcs:
            for name, pat in HTML_RUNTIME_NET:
                for m in pat.finditer(code):
                    r.gray(line0 + code.count("\n", 0, m.start()),
                           "%sの中に「%s」— 開いたあとに外部と通信する書き方かを目で確かめる"
                           "(原典は実行時に外部と通信しないと定める。読むだけでは通信するかが決まらないので ✕ にしない)"
                           % (where, name))
        outside = "※原典は「など」で閉じていない。照合しない口: %s" % HTML_RUNTIME_NET_OUTSIDE
        if r.status == "ok":
            if srcs:
                r.ok_note("該当なし(原典が名指す4つの書き方 fetch・XMLHttpRequest・WebSocket・動的な import() だけを、"
                          "スクリプトの中で字面で照合) " + outside)
            else:
                r.ok_note("スクリプト(script 要素の中身・on〜 属性・javascript: の URL)が無い " + outside)
        else:
            r.note = "原典が名指す4つの書き方だけを字面で照合(リストを勝手に増やさない) " + outside
        results.append(r)

    # H-0 門番(最後に置く。ここまでの結果に ▲ や「納品物の責任で未検査」が残っていれば違反を立てる)
    # ★★段5-2(2026-08-19)の要点を、繋いだ当人が正直に書いておく ——
    #   **いまの html には、この門番が拾う枝が1つも無い。**実測: 実在の html 納品物62件のうち
    #   ▲ を持つものは0件、「― かつ責任=納品物」を持つものも0件である(H-4=規定 / H-5=呼び出し /
    #   H-6=人間)。つまりこの工事で新たに不合格になる html 納品物は**0件**である。
    #   ⇒ これは「門番が空回りしている」のではなく、**約束を機械で守らせる形にした**ということである。
    #     今後 html に ▲ を出す規則や「書き手が書式を直せば検査できる」規則が足されたとき、
    #     その日から自動的に納品が止まる(繋いでいなければ、足した人が忘れれば止まらない)。
    # ★★H-6 を拾ってはならない。原典が「1(必須要素)はテンプレートごとの規定なので機械照合の
    #   対象外——目視のまま」と定めており、責任は**人間**である。「― を全部拾う」実装にすると
    #   H-6 が常に ― なので **html は62件全滅する**(記号の節のコメントに残っている当の事故)。
    #   門番は責任の所在で分けているので拾わない。常設テスト E-15 がそれを検体で固定している。
    # ★第4引数(表の診断)は使わない種別なので空の並びを渡す。KANMON の第4要素が None である。
    if KANMON_ON["html"]:
        guarded(results, "H-0", lambda: check_kanmon("html", results, lines, []))

    return results, ("アーティファクト" if artifact else "ファイル")


# ---------------------------------------------------------------- 種別判定・出力
# ---- 段(2026-08-23): `--artifact` を種別の宣言として配線する ------------------
# ★★これを配線していなかった間に何が起きていたか(外部レビュー第2次が現物で出した欠陥):
#   利用者が `--artifact` で「これはHTMLだ」と**明示している**のに、その指定が
#   `detect_type` へ1ミリも届かず、拡張子が `.html` でない断片は**既定の ronbun**として
#   検査された。⇒ **H-1〜H-6 が1本も走らないまま「違反0・終了コード0」**で終わる。
#   ★逐語(外部レビュー): 「本チェッカーの最悪失敗を『**検査していないのに合格と言うこと**』と
#     置くなら、[6] を先に置く」。**これは fail-open の中でも最も重い型である。**
#
# ★★`--type` と食い違ったときの扱いは【原典が決めていない】(2026-08-23 に調べた):
#   原典 run-html-visualizer/SKILL.md は `--type html` に `--artifact` を**足す**形しか書いておらず
#   (「`--type html` で機械照合できる(アーティファクト出力なら `--artifact`、…)」)、
#   `--type ronbun --artifact` のような組み合わせを**一度も許していない**。DESIGN.md にも記述が無い。
#   ⇒ ★**「原典が黙っている」のではなく「原典が書いていない組み合わせ」**なので、
#     **こちらで意味を発明せず、落とす。**(ユーザー裁定・司令塔第4代の裁定 2026-08-23)
#   ★退けた案と理由 —— どちらも**この工事で塞いでいる穴と同じ形**になる:
#     ・`--artifact` を優先 = 利用者の明示指定を機械が黙って上書きする
#     ・`--type` を優先(`--artifact` を無視)= 指定が判定に届かないまま「合格」が出る(現状と同型)
# ★DESIGN.md:365「種別同定の厳格化は運用を止めうる(`auto` を弱めると `--type` 無しの
#   呼び出しが一斉に引数エラーになる)」には抵触しない。★**`auto` を弱めていない** ——
#   手がかりを1つ**増やす**向きの変更であり、`--artifact` 無しの呼び出しは1つも挙動が変わらない。
ARTIFACT_DECLARES = "--artifact で「HTMLとして扱え」と宣言された"

# ★`--artifact` と両立する `--type`。**html は原典の正規形**なので当然エラーにしない。
ARTIFACT_COMPATIBLE_TYPES = ("auto", "html")


def declared_kind(args):
    """`--type` を使わずに利用者が宣言した種別。宣言が無ければ既定の ronbun。

    ★**`inspect_file` の2か所(落ちたときに名乗る種別 / 判定)から同じ1本を引く。**
      片方だけ直すと、読み込みで落ちたファイルだけ別の種別を名乗る。
    """
    return "html" if getattr(args, "artifact", False) else "ronbun"


def artifact_type_conflict(args):
    """`--artifact` と `--type` が両立しないなら理由を返す。両立するなら None。"""
    if not getattr(args, "artifact", False):
        return None
    if args.type in ARTIFACT_COMPATIBLE_TYPES:
        return None
    return ("--artifact は「この納品物をHTMLとして扱え」という宣言なので、"
            "--type %s とは両立しない。"
            "HTMLの成果物なら --type html と併用するか、--type を外すこと。"
            "★どちらが正しいかは機械には決められないので、"
            "検査を1本も走らせずに終了する(黙って片方を採ると、"
            "検査していないものを合格と呼ぶことになる)。" % args.type)


def detect_type(path, raw):
    """(種別, 判定の根拠) を返す。積極的な手がかりが無いまま ronbun に倒したときは
    その旨を根拠に残す(黙って原稿として検査すると、台帳の検査漏れに気づけないため)。

    ★**`--artifact` はここへ来ない。**利用者の宣言は推測より強いので `inspect_file` が
      この関数を呼ぶ前に反映する(`ARTIFACT_DECLARES`)。
    """
    ext = os.path.splitext(path)[1].lower()
    if ext in (".html", ".htm"):
        return "html", "拡張子"
    head = raw[:3000]
    if re.search(r"#\s*出典台帳", head):
        return "uradori", "見出し「出典台帳」"
    if re.search(r"#\s*文献台帳", head):
        return "bunken", "見出し「文献台帳」"
    if "検証水準" in head:
        return "uradori", "ヘッダーの「検証水準」"
    if "入手状況" in raw[:8000]:
        return "bunken", "「入手状況」の記載"
    if "<html" in head.lower() or "<!doctype" in head.lower():
        return "html", "HTMLの骨格"
    return "ronbun", "⚠ 台帳の手がかりが無いため既定で原稿として検査(--type で明示指定できる)"


TYPE_LABEL = {"uradori": "uradori 出典台帳", "bunken": "bunken-daicho 文献台帳",
              "ronbun": "ronbun-shippitsu 原稿", "html": "html-visualizer 成果物"}


def report(path, kind, extra, results, max_findings, lost=()):
    print("===== %s =====" % path)
    line = "種別: %s" % TYPE_LABEL[kind]
    if extra:
        line += "   / %s" % extra
    print(line)
    print()
    ng = gray = skip = ok = blocked = 0
    for r in results:
        if r.status == "ng":
            ng += 1
        elif r.status == "gray":
            gray += 1
        elif r.status == "skip":
            skip += 1
        elif r.status == "blocked":
            # **この枝が無いと ▲ が else に落ちて「合格」に数えられる。**
            blocked += 1
        else:
            ok += 1
        head = "  %s %-5s %s" % (MARK[r.status], r.rule_id, r.title)
        if r.status in ("ng", "gray"):
            head += "  (%d件)" % len(r.findings)
        elif r.note:
            head += "  — %s" % r.note
        print(head)
        if r.status in ("ng", "gray"):
            if r.note:
                print("        ※ %s" % r.note)
            shown = r.findings if max_findings <= 0 else r.findings[:max_findings]
            for lineno, msg in shown:
                loc = ("L%d" % lineno) if lineno else "  -"
                print("        %-6s %s" % (loc, msg))
            rest = len(r.findings) - len(shown)
            if rest > 0:
                print("        …ほか%d件(--max-findings 0 で全件表示)" % rest)
    print()
    # ★原典を失った規則の申告。**0件なら1行も印字しない**(既存の出力を1バイトも変えないため)。
    if lost:
        print("  [★原典を失った規則 — この規則は検査していない。**合格ではない。**]")
        for rid, problems in lost:
            for f, q, w in problems:
                print("    ・%-5s %s に「%s」が%s" % (rid, f, q[:36], WHY_LABEL[w]))
        print("     → 原典(スキル本体)が改稿され、規則が拠っていた文言が消えた可能性が高い。")
        print("        **チェッカーの誤検出として黙らせず、規則を原典に合わせ直すこと。**")
        print()
    unreach = origin_unreachable([r.rule_id for r in results])
    if unreach:
        print("  [★原典に到達できない — 逐語の照合ができていない]")
        for f in unreach:
            print("    ・%s" % f)
        print("     → チェッカーを4スキルの外へ写して使っている可能性がある。")
        print("        原典の在処は環境変数 CHECKER_SKILLS_ROOT で指定できる。")
        print()
    # ★★見ていない範囲(`00-principles.md` §12)。**走行のたびに、画面に。**
    #   ★0件でも印字する。分岐を足すと、0件のときだけ通る枝が誰にも試されなくなる。
    _cov_named, _cov_out, _cov_unnamed = origin_coverage()
    print("  [★原典の照合の被覆] 原典 file:line を名乗る地点 %d件 / 逐語で照合 %d件 / "
          "★照合の外側 %d件%s"
          % (len(_cov_named), len(_cov_named) - len(_cov_out), len(_cov_out),
             ("(%s)" % "・".join(_cov_out)) if _cov_out else ""))
    print("     ・原典を名乗っていない地点(規定により対象外): %d件%s"
          % (len(_cov_unnamed), ("(%s)" % "・".join(_cov_unnamed)) if _cov_unnamed else ""))
    print("     ★外側は「逐語を持たない控え」である —— 原典が伸び縮みしても誰も気づけない。")
    # ★★この勘定の【外側の外側】を名指しする(§12 の条件3)。実行時に数えられない部分である。
    print("     ★この勘定は【上の4つの表に載っている地点】だけを見ている。表に載らず"
          "ソースに直書きされた file:line は、構文木を読まないと数えられない ——"
          "常設テスト F-39 が構文木から数えて毎回名指しする。")
    print()
    nm = [x for x in NOT_MECHANIZED if x[0] == kind]
    if nm:
        print("  [機械化を見送った項目 — 目視で確認すること]")
        for _t, title, origin, why in nm:
            print("    ・%s (%s)" % (title, derive_origin(nm_key(_t, title), origin)[0]))
            print("       理由: %s" % why)
        print()
    # 既存の4数の並びは変えない(集計行を読む道具が依存している)。検査不能は後ろに足す。
    print("  → 違反 %d項目 / 要目視 %d項目 / 未検査 %d項目 / 合格 %d項目%s (検査した規則 %d)"
          % (ng, gray, skip, ok,
             (" / **検査不能 %d項目**" % blocked) if blocked else "", len(results)))
    # ★★F-021(台帳・採用)の後半: **B-2 の未検査注記を【集計行】にも出す。**
    #   ★見送り欄の側は 2026-08-22 に着地済み(`NOT_MECHANIZED`)。ここが残っていた片方である。
    #   ★★**上の4数は1つも動かさない**(集計行を読む道具が依存している)。**別の行として足す。**
    #   ★述語は**実行時に観測する** —— 「◎(合格)なのに、その註で『未検査』を自称している」もの。
    #     ★字面の走査ではなく走行の結果を見るので、**将来この形が増えても自動でここに出る。**
    #   ★0件のときは1行も増やさない(0件のときの出力を1バイトも変えないため)。
    #     ★**0件を黙って通していない証拠は常設テスト F-44 の恒等対照が持っている**
    #       (自称0件の納品物でこの行が1バイトも出ないことを毎回確かめる)。
    self_declared = [x for x in results if x.status == "ok" and x.note and "未検査" in x.note]
    if self_declared:
        print("     ※ ★合格(◎)なのに註で「未検査」を自称している項目 %d件: %s"
              " —— **上の「未検査 %d項目」には数えていない**(記号は◎のまま)。"
              "**合格ではない部分が◎の中に在る。**見送り欄も読むこと。"
              % (len(self_declared), "/".join(x.rule_id for x in self_declared), skip))
    if blocked:
        # ★★この工事の要点:★★**「▲=納品物の形が原因」は嘘である。**
        #   責任の所在は `STATE_RESPONSIBILITY`(柱2)が決めており、▲(blocked)には
        #   納品物だけでなく missing_input(supplier=呼び出し/チェッカー/人間)・
        #   crashed(=チェッカー)・原典喪失(=人間)も落ちてくる。それを一律に
        #   「納品物の形が原因」と言い切っていたのが不具合だった。
        #   ★**判定(✕を立てるかどうか)はここでは1文字も触らない**(それは check_kanmon の仕事)。
        #   ここは画面の文言だけを、実際の責任の内訳に合わせて直す。
        by = {}
        for who in SUPPLIERS:
            grp = [r for r in results if r.status == "blocked" and responsibility(r) == who]
            if grp:
                by[who] = len(grp)
        parts = " / ".join("%s %d件" % (who, n) for who, n in by.items())
        print("     ※ 検査不能(▲)= 実行できなかった項目(**合格ではない**)。"
              "責任の内訳: %s — **「納品物の形が原因」とは限らない**(誰が直せるかは規則ごとに違う)"
              % parts)
    # ★★2026-08-23: 記号が「―」のまま**状態だけが「検査が終わっていない」**である項目を名乗る。
    #   ★これを出さずに終了コードだけ 3 にすると「**終了コードに出るが画面に出ない**」になり、
    #     §6 が禁じている fail-open の**裏返し**になる。どちらも同じ罪である。
    #   ★0件なら1行も増えない(0件のときの出力を1バイトも変えないため)。
    latent_unexec = [r for r in unexecuted(results) if r.status != "blocked"]
    if latent_unexec:
        by_l = {}
        for x in latent_unexec:
            by_l.setdefault(responsibility(x), []).append(x.rule_id)
        print("     ※ ★記号は「―」だが**検査は終わっていない**項目が %d項目ある: %s"
              % (len(latent_unexec),
                 " / ".join("%s %d件(%s)" % (who, len(v), "・".join(sorted(set(v))))
                            for who, v in sorted(by_l.items()))))
        print("        → **合格ではない。**違反を立てるかは責任ごとに違うが、"
              "**終了コードは 0 にはならない**(違反が無ければ 3)")
    print_states(results)
    print()
    # ★★事実の関門【段階A】の開示と申告文。★**走行のたびに、画面に。★0件でも出す。**
    #   ★対象の種別でないときは1行も出さない(=`LINK_RULES` に無い種別)。
    print_link_disclosure(kind, results)
    # ★★事実の関門【段階B】の開示。★**走行のたびに、画面に。★0件でも出す。**
    #   ★対象でない種別(uradori)でも「対象でない」と1行出す —— 黙って落とさないため。
    print_biblio_disclosure(kind, results)
    # ★★事実の関門【段階C】の開示。★**走行のたびに、画面に。★0件でも出す。**
    print_fulltext_disclosure(kind, results)
    # ★段5(2026-08-19): 検査不能(▲)の件数も返す。**呼び出し側が終了コード3へ繋ぐ**。
    #   「画面に出るが終了コードに出ない」は fail-open の一種である
    #   (PARENT-HANDOFF §5「原典喪失(▲)は段5で必ず終了コードに繋ぐ。この行を消さない」)。
    # ★★2026-08-23: 返すのは**記号が ▲ の件数ではなく、状態が「未実行」の件数**である。
    #   記号で数えていたために `skip_as` 経路の未実行(R-2 の「読めなかった」など)が
    #   終了コードから消えていた(`unexecuted()` の註を参照)。
    #   ★集計行1行目は**status のまま**である(DESIGN「集計行1行目は1文字も変えない」)。
    return ng, len(unexecuted(results))


# ---- 段1: 集計行2行目(受理の記録) -------------------------------------------
# ★1行目は全段階を通じて1文字も変えない(counts() が唯一の消費者)。**2行目を新設する。**
STATE_LABEL = [
    ("not_applicable", "規定による対象外"),
    ("clean",          "検査して違反なし"),
    ("violation",      "違反"),
    ("partial",        "一部しか読めなかった"),
    ("missing_input",  "検査に必要な情報が無い"),
    ("crashed",        "検査処理が失敗"),
    ("needs_human",    "人間の判断が要る"),
]


def responsibility(r):
    """★誰が直せるか。門番の分岐はここ1本に集める(規則の実装に散らさない)。

    ★DESIGN §7-2 の警告を承知のうえで置く: 型は「分類を書け」と強制するが
    「正しく分類しろ」とは強制できない。**分類を誤ると逆向きの事故になる**ので、
    分類の正しさは人間の点検対象として残る。

    ★★**この関数は写像を持たない。**7状態 → 責任の所在の対応は
    `STATE_RESPONSIBILITY`(モジュール上部の表)**だけ**にある。
    ★行番号は書かない —— 本体を1行足すたびに黙ってずれる(常設テストは素通りする)。
    ★2026-08-21 まで、ここに同じ写像を dict リテラルで**書き写して**いた ——
    そして**判定に使われていたのは書き写したほう**で、表はどのコードからも
    読まれていなかった。**分類を直す人が表を直しても判定は1ミリも動かない**
    状態だったということである(常設テスト E-19 がこの再発を止める)。
    """
    who = STATE_RESPONSIBILITY[r.state_guess()]
    # ★表が None と書いた状態は「責任は **supplier 引数で決まる**」という宣言である
    #   (いまは missing_input だけ)。★状態の名前をここに書かない —— 書けば
    #   「どの状態が supplier で決まるか」がまた2か所に分かれ、畳んだ意味が消える。
    if who is None:
        return r.state_info.get("supplier") or "納品物"
    return who


def print_states(results):
    """7状態の内訳を印字する。★記号にも終了コードにも触れない、**観測の報告**である。"""
    from collections import Counter
    c = Counter(r.state_guess() for r in results)
    explicit = sum(1 for r in results if r.state is not None)
    print("  → 受理の記録: %s ／ 明示 %d / 推定 %d"
          % (" / ".join("%s %d" % (lab, c.get(k, 0)) for k, lab in STATE_LABEL),
             explicit, len(results) - explicit))

    # ★ここが段1の眼目。「未検査(―)」の中身は1種類ではない。
    dash = [r for r in results if r.status == "skip"]
    if dash:
        d = Counter(r.state_guess() for r in dash)
        parts = " / ".join("%s %d" % (lab, d[k]) for k, lab in STATE_LABEL if d.get(k))
        print("     ※ 「未検査 %d項目」の内訳: %s" % (len(dash), parts))
        moved = [r for r in dash if r.state_guess() != "not_applicable"]
        if moved:
            # ★「▲かどうか」ではなく「**誰が直せるか**」で分ける(柱2の中心)。
            #   納品物側だけが段3以降で違反へ繋ぐ候補になる。
            #   呼び出し側とチェッカー側と人間は、繋いでも書き手には直せない。
            by = {}
            for x in moved:
                by.setdefault(responsibility(x), []).append(x.rule_id)
            print("        ★このうち %d項目は「検査しなくてよかった」ではない。責任の所在: %s"
                  % (len(moved),
                     " / ".join("%s %d件(%s)" % (who, len(v), "・".join(sorted(set(v))))
                                for who, v in sorted(by.items()))))
            cand = by.get("納品物", [])
            print("        → 段3以降で違反へ繋ぐ候補は「納品物」の %d項目だけである%s"
                  % (len(cand), "" if cand else "(この納品物では0)"))
    # 原典を伴わない「規定による対象外」は G3(原典を書けない除外は書けない)の未達である。
    naked = [r.rule_id for r in results
             if r.state == "not_applicable" and not r.state_info.get("origin")]
    if naked:
        print("     ※ 原典 file:line を伴わない対象外: %s" % "・".join(naked))


def list_rules():
    print("# 実装されている規則一覧(check_deliverable.py の RULES 定義)")
    cur = None
    for rid, target, title, origin, lv in RULES:
        if target != cur:
            cur = target
            print("\n## %s" % TYPE_LABEL[target])
        # ★印は `derive_origin` が控えに付けて返す。**ここで2つ目の判定を書かない**
        #   —— 同じことを2か所に書くと必ず食い違う(この体系が繰り返し踏んだ形)。
        o, _problems = derive_origin(rid, origin)
        print("  %-5s [%-4s] %-34s %s" % (rid, lv, title, o))
    print("\n# 機械化を見送った項目")
    for target, title, origin, why in NOT_MECHANIZED:
        print("  [%s] %s (%s)" % (target, title, derive_origin(nm_key(target, title), origin)[0]))
        print("        理由: %s" % why)
    n_q = sum(1 for r in RULES if r[0] in ORIGIN_QUOTES)
    n_nm = sum(1 for t, ti, _o, _w in NOT_MECHANIZED if nm_key(t, ti) not in ORIGIN_QUOTES)
    print("\n# 原典の位置の持ち方")
    print("  逐語から導出している規則: %d / %d 本%s"
          % (n_q, len(RULES),
             "(★全規則。手書きの行番号だけに頼る規則は無い)" if n_q == len(RULES)
             else "(残り %d 本は手書きの行番号のまま)" % (len(RULES) - n_q)))
    # ★分岐を足さない(常に印字する)。分岐を1本足すと変異解析の母集合に**試験されない枝**が増える。
    print("  機械化を見送った項目のうち、まだ手書きの行番号のままのもの: %d 件" % n_nm)
    print("  ★導出している規則は、原典が改稿されて逐語が消えると ▲(検査不能)になる。")


def inspect_file(path, args):
    """1ファイルを検査して (種別, 見出しの補足, 結果, 原典を失った規則, 原文) を返す。

    ★★段6(2026-08-20)の要:**ここが「ファイル単位で `report` まで到達させる」の実装**である。
      規則の**中**で起きた例外は `guard` が規則単位で受け止める(その規則だけ ▲)。
      ここで受け止めるのは**規則の外** —— 読み込み・種別判定・表の切り出しなど、
      どの規則にも属さない共通処理で起きた例外である。
    ★包む前は、この例外が `main` を突き抜けて**走行そのものを終わらせていた** ——
      画面には `report` が1行も出ず、**同じ呼び出しの後続のファイルも検査されないまま消えた**。
      対照は `evidence/dan6-taisho-*.txt`(包む前は落ち、包んだ後は `report` に到達する)。
    ★**握りつぶしではない。**落ちた分は `crashed`(▲)になり、門番が拾い、終了コードに出る。
    """
    # ★落ちたときに名乗る種別。--type の指定があればそれ、次に --artifact の宣言、無ければ既定の ronbun。
    #   ★**ここを直し忘れると、読み込みで落ちたときだけ ronbun を名乗る**(下の判定と食い違う)。
    kind = args.type if args.type != "auto" else declared_kind(args)
    results = []
    raw = ""          # ★読み込みで落ちた場合の値。--accounting はこの値を受け取る
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            raw = f.read()
        # ★2026-10-05(U-26・B-20): 同じファイルのバイトも読む(★読み込みで生じた置き換えの字と、元から書いてある字を区別するため)。
        with open(path, "rb") as f:
            data = f.read()
        lines = raw.splitlines()
        if args.type != "auto":
            kind, why = args.type, "--type で指定"
        elif args.artifact:
            # ★**利用者の宣言は、手がかりの推測より強い。**`detect_type` の手前で反映する。
            kind, why = "html", ARTIFACT_DECLARES
        else:
            kind, why = detect_type(path, raw)
        if kind == "uradori":
            _res, extra = check_uradori(path, raw, lines, sink=results, data=data)
            extra = "検証水準: %s" % extra if extra else "検証水準: ヘッダーから読めず"
        elif kind == "bunken":
            _res, extra = check_bunken(path, raw, lines, sink=results, data=data)
        elif kind == "html":
            _res, extra = check_html(path, raw, lines, args.artifact,
                                     args.expect_count, args.count_pattern, sink=results)
            extra = "前提: %s出力" % extra
        else:
            _res, extra = check_ronbun(path, raw, lines, sink=results)
        extra = ("%s   / 種別判定: %s" % (extra, why)) if extra else "種別判定: %s" % why
    except Exception as exc:
        # ★まだ出ていない規則は**1本も検査できていない**。それが事実なので全部 ▲ にする。
        #   ★すでに判定の出た規則はそのまま残す(「他の規則の判定は残る」)。
        crash_all(kind, results, exc)
        extra = ("★検査の共通処理が失敗した: %s: %s(発生位置 %s)"
                 " — 規則の外で落ちたので、まだ出ていない規則は検査できていない"
                 % (type(exc).__name__, exc, exc_where(exc)))
    results.sort(key=lambda r: (r.rule_id.split("-")[0], int(r.rule_id.split("-")[1])))
    # ★原典を失った規則を ▲ へ倒す(黙って合格にしない)。**判定の直後・印字の直前に1か所だけ置く。**
    try:
        lost = origin_gate(results)
    except Exception as exc:
        # ★原典の照合そのものが落ちたら、**どの規則の「合格」も名乗れない。**全部 ▲ に倒す。
        #   ここだけ「残っている判定を捨てる」のは、捨てないと**照合されていない合格**が
        #   画面に出るからである(この体系がいちばん嫌う型 —— fail-open)。
        results = [crashed(r.rule_id, exc) for r in results]
        lost = ()
    return kind, extra, results, lost, raw


def main():
    ap = argparse.ArgumentParser(add_help=True, description="自作スキルの納品物の機械照合")
    ap.add_argument("files", nargs="*", help="検査するファイル")
    ap.add_argument("--type", choices=["auto", "uradori", "bunken", "ronbun", "html"], default="auto")
    ap.add_argument("--artifact", action="store_true",
                    help="この納品物をHTMLのアーティファクトとして扱う(--type html と同じ種別になる。"
                         "--type ronbun/uradori/bunken との併用はエラー)")
    ap.add_argument("--expect-count", type=int, default=None, help="H-5 全量保持: 入力の件数")
    ap.add_argument("--count-pattern", default=None, help="H-5 全量保持: HTML内で数える正規表現")
    ap.add_argument("--max-findings", type=int, default=12, help="1規則あたりの表示件数(0で全件)")
    ap.add_argument("--list-rules", action="store_true", help="規則一覧を出力して終了")
    # ---- 段0で足した観測用の口。**既定では何も出力せず、判定にも接続しない。** ----
    ap.add_argument("--list-profile", action="store_true",
                    help="受理プロファイル(このチェッカーが読めると宣言する形)を出力して終了")
    ap.add_argument("--accounting", action="store_true",
                    help="勘定(受理層の観測と3層の不変条件)を併せて印字する。★判定・終了コードは変わらない")
    # ---- 事実の関門【段階A】(2026-08-29・ユーザー裁定) ----
    ap.add_argument("--links", default=None, metavar="PATH",
                    help="段階A: リンク到達の取得結果(JSON)の置き場。★渡さないとリンク到達は"
                         "▲(未検査)になり、終了コードは 3 になる")
    ap.add_argument("--fetch-links", action="store_true",
                    help="段階A: ★実際に外部へアクセスし、--links の置き場へ取得結果を書く"
                         "(--links が必須)。★これを渡さない走行はネットワークに一切触れない")
    ap.add_argument("--link-timeout", type=float, default=LINK_TIMEOUT_DEFAULT, metavar="SEC",
                    help="段階A: 1本あたりの待ち時間の上限(秒。既定 %g)" % LINK_TIMEOUT_DEFAULT)
    # ---- 事実の関門【段階B】(2026-08-31・ユーザー裁定) ----
    ap.add_argument("--biblio", default=None, metavar="PATH",
                    help="段階B: 書誌の照会結果(JSON)の置き場。★渡さないと書誌の突合は"
                         "▲(未検査)になり、終了コードは 3 になる")
    ap.add_argument("--fetch-biblio", action="store_true",
                    help="段階B: ★実際に DOI の登録機関へ問い合わせ、--biblio の置き場へ"
                         "結果を書く(--biblio が必須)。★これを渡さない走行は外へ一切出ない")
    ap.add_argument("--biblio-timeout", type=float, default=BIBLIO_TIMEOUT_DEFAULT,
                    metavar="SEC",
                    help="段階B: 1本あたりの待ち時間の上限(秒。既定 %g)"
                         % BIBLIO_TIMEOUT_DEFAULT)
    ap.add_argument("--shoshi", default=None, metavar="PATH",
                    help="段階B(bunken): 書誌の項目ファイル(<台帳名>.shoshi.json)。★渡すと年・題名・頁・出版社も"
                         "登録機関の記録と照らし、書誌欄がその値を持っているかも見る")
    # ---- 事実の関門【段階C】(2026-08-31・ユーザー裁定) ----
    ap.add_argument("--fulltext", default=None, metavar="PATH",
                    help="段階C: 本文の取得結果(JSON)の置き場。★渡さないと逐語の照合は"
                         "▲(未検査)になり、終了コードは 3 になる。"
                         "★★本文が入るので木に置かないこと")
    ap.add_argument("--fetch-fulltext", action="store_true",
                    help="段階C: ★実際に原典を取得し、--fulltext の置き場へ書く"
                         "(--fulltext が必須)。★これを渡さない走行は外へ一切出ない")
    ap.add_argument("--fulltext-timeout", type=float, default=FULLTEXT_TIMEOUT_DEFAULT,
                    metavar="SEC",
                    help="段階C: 1本あたりの待ち時間の上限(秒。既定 %g)"
                         % FULLTEXT_TIMEOUT_DEFAULT)
    args = ap.parse_args()

    # ★★食い違いは**検査より先に**落とす。★`--list-rules` などより前に置くのは意図的ではない ——
    #   一覧の出力は納品物を1つも読まないので、順序はどちらでもよい。**判定より先**であることが要件。
    conflict = artifact_type_conflict(args)
    if conflict:
        ap.error(conflict)          # ★argparse が終了コード 2 で落とす(検査は1本も走らない)
    if args.fetch_links and not args.links:
        # ★保存しない取得は、次の走行で再現できない(`20-evidence-rules.md` §1「固定方法を明記」)。
        ap.error("--fetch-links には --links <保存先> が要る —— "
                 "保存しない取得は次の走行で再現できないため")
    if args.fetch_biblio and not args.biblio:
        # ★段階A と同じ理由。★**保存しない照会は、次の走行で再現できない。**
        ap.error("--fetch-biblio には --biblio <保存先> が要る —— "
                 "保存しない照会は次の走行で再現できないため")
    if args.fetch_fulltext and not args.fulltext:
        ap.error("--fetch-fulltext には --fulltext <保存先> が要る —— "
                 "保存しない取得は次の走行で再現できないため")

    if args.list_rules:
        list_rules()
        return 0
    if args.list_profile:
        list_profile()
        return 0
    if not args.files:
        ap.print_usage()
        print("検査するファイルを指定してください。規則一覧は --list-rules。")
        return 2

    # ---- 事実の関門【段階A】の下ごしらえ。★判定より前に、読めるかどうかを決着させる ----
    global LINK_EVIDENCE
    if args.fetch_links:
        rc = fetch_and_save_links(args)
        if rc:
            return rc
    if args.links:
        got, why = link_evidence_load(args.links)
        if got is None:
            print("★★段階A: %s" % why, file=sys.stderr)
            print("🔴★**黙って通さない。**★取得結果が読めない = リンクを確かめていない、である。",
                  file=sys.stderr)
            return 2
        LINK_EVIDENCE = got

    # ---- 事実の関門【段階B】の下ごしらえ。★段階A と同じ形にしてある ----
    global BIBLIO_EVIDENCE
    if args.fetch_biblio:
        rc = fetch_and_save_biblio(args)
        if rc:
            return rc
    if args.biblio:
        gotb, whyb = biblio_evidence_load(args.biblio)
        if gotb is None:
            print("★★段階B: %s" % whyb, file=sys.stderr)
            print("🔴★**黙って通さない。**★照会結果が読めない = 書誌を確かめていない、である。",
                  file=sys.stderr)
            return 2
        BIBLIO_EVIDENCE = gotb
    global SHOSHI
    if args.shoshi:
        gots, whys = shoshi_load(args.shoshi)
        if gots is None:
            print("★★段階B: %s" % whys, file=sys.stderr)
            print("🔴★**黙って通さない。**★項目ファイルが読めない = 7項目を照らしていない、である。",
                  file=sys.stderr)
            return 2
        SHOSHI = gots

    # ---- 事実の関門【段階C】の下ごしらえ。★段階A・B と同じ形にしてある ----
    global FULLTEXT_EVIDENCE
    if args.fetch_fulltext:
        rc = fetch_and_save_fulltext(args)
        if rc:
            return rc
    if args.fulltext:
        gotc, whyc = fulltext_evidence_load(args.fulltext)
        if gotc is None:
            print("★★段階C: %s" % whyc, file=sys.stderr)
            print("🔴★**黙って通さない。**★取得結果が読めない = 逐語を確かめていない、である。",
                  file=sys.stderr)
            return 2
        FULLTEXT_EVIDENCE = gotc

    total_ng = 0
    total_blocked = 0
    for path in args.files:
        if not os.path.isfile(path):
            print("===== %s =====" % path)
            print("  ✕ ファイルが見つからない\n")
            total_ng += 1
            continue
        kind, extra, results, lost, raw = inspect_file(path, args)
        ng, blocked = report(path, kind, extra, results, args.max_findings, lost)
        total_ng += ng
        total_blocked += blocked
        # ★2026-10-05(起票 `KICKOFF-juri-tsuzuki.md` §1-4・ユーザー裁定 問い4 (ア)): 受理層の記録を普段の点検でも毎回並べる。
        #   ★印字だけで、total_ng にも終了コードにも触れない(★`print_admit_record` は何も返さない)。
        print_admit_record(path, kind, raw)
        if args.accounting:
            # ★段0の足場。印字だけで、total_ng にも終了コードにも触れない。
            # ★2026-10-05: バイトも渡す(★普段の画面の記録と同じく、UTF-8 で読めない行を `encoding_error` として数える)。
            with open(path, "rb") as f:
                doc, _unsup = admit(raw, kind, f.read())
            Ledger(doc).build().print_report()
    # ★終了コード 0/1/2 の意味は変えず、3 だけを増やす(DESIGN §6 の約束)。
    #   違反があるときは従来どおり 1 を返す —— 1 は「直すべきものが分かっている」で、
    #   3 は「直すべきものが分かっていない(検査そのものが走らなかった)」である。
    #   ★両方あるときに 1 を返すのは、より具体的な指示を優先するためであって
    #     ▲ を軽く見るからではない。▲ の件数と理由は必ず画面に出ている。
    if total_ng:
        return 1
    if total_blocked:
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
