#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
machines.json を読んで、機種ごとのページと sitemap.xml を生成する。

使い方:  python3 build.py

生成されるもの:
  m/<slug>.html   機種ごとのページ
  m/style.css     機種ページ共通のスタイル
  sitemap.xml     全ページを載せたサイトマップ（articles/ の解説記事も含む）
"""

import json
import math
import os
import re
from datetime import date

SITE = "https://pachi-tool.com/"
TODAY = date.today().isoformat()

# 早見表に出す回転数
TABLE_SPINS = [100, 200, 300, 500, 700, 1000, 1200, 1500, 2000, 2500, 3000]


def hamari_rate(prob, spin):
    """prob分の1の台で spin回転ハマる確率を返す（0〜1）"""
    return ((prob - 1) / prob) ** spin


def fmt_pct(v):
    """パーセント表示を桁数に応じて整える"""
    p = v * 100
    if p >= 10:
        return f"{p:.1f}%"
    if p >= 1:
        return f"{p:.2f}%"
    if p >= 0.01:
        return f"{p:.3f}%"
    if p >= 0.00001:
        return f"{p:.5f}%"
    # これ以上小さいと0が並ぶだけなので言葉で表す（頻度欄が実態を伝える）
    return "ほぼ0%"


def fmt_freq(v, prefix=True):
    """頻度の表現。50%以上は回数で言わず「よくあるハマり」とする"""
    if v <= 0:
        return "-"
    if v >= 0.5:
        return "よくあるハマり"
    n = 1 / v
    head = "初当たり約" if prefix else "約"
    # 桁が多すぎると読めなくなるので、1億を超えたら単位を使う
    if n >= 1_0000_0000_0000:
        return f"{head}{n/1_0000_0000_0000:,.1f}兆回に1回"
    if n >= 1_0000_0000:
        return f"{head}{n/1_0000_0000:,.1f}億回に1回"
    return f"{head}{round(n):,}回に1回"


def fmt_one_in(v):
    """表の頻度欄で使う（接頭辞なし）"""
    return fmt_freq(v, prefix=False)


def half_point(prob):
    """当たる確率が50%を超えるまでの回転数"""
    return math.ceil(math.log(0.5) / math.log((prob - 1) / prob))


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;"))


# ---------------------------------------------------------------
#  広告ブロック（1箇所直せば全ページに反映される）
# ---------------------------------------------------------------
AD_BLOCK = """<aside class="ad-block">
  <span class="ad-label">PR</span>
  <a href="https://px.a8.net/svt/ejp?a8mat=4BECGY+F6JY42+5FAA+5YZ75"
     rel="sponsored nofollow noopener" target="_blank">
    <img class="ad-banner" border="0" width="300" height="250" alt="アニメ・マンガ・ゲームのグッズ専門ショップ FaNeMa"
         loading="lazy"
         src="https://www25.a8.net/svt/bgt?aid=261009826918&amp;wid=001&amp;eno=01&amp;mid=s00000025309001003000&amp;mc=1">
  </a>
  <img border="0" width="1" height="1"
       src="https://www14.a8.net/0.gif?a8mat=4BECGY+F6JY42+5FAA+5YZ75" alt="">
</aside>"""


CTA_LINK = "https://px.a8.net/svt/ejp?a8mat=4BECGY+F6JY42+5FAA+5YRHE"
CTA_PIXEL = '<img border="0" width="1" height="1" src="https://www18.a8.net/0.gif?a8mat=4BECGY+F6JY42+5FAA+5YRHE" alt="">'


# ---------------------------------------------------------------
#  機種ページ共通のスタイル
# ---------------------------------------------------------------
STYLE = """:root{
  --hall-black:#0b0710; --hall-deep:#171025; --panel:#1e1630;
  --neon-pink:#ff2d78; --neon-cyan:#25e5ff; --lamp-gold:#ffc832;
  --text:#f2eefa; --text-dim:#9c93b5;
}
*{box-sizing:border-box;}
body{
  margin:0;
  background:
    radial-gradient(circle at 20% 0%, rgba(255,45,120,.18), transparent 45%),
    radial-gradient(circle at 85% 15%, rgba(37,229,255,.15), transparent 45%),
    var(--hall-black);
  color:var(--text); font-family:"Noto Sans JP",sans-serif;
  line-height:1.9; padding:0 16px 80px;
}
.wrap{max-width:760px;margin:0 auto;}

.crumb{font-size:12px;color:var(--text-dim);padding:18px 0 0;}
.crumb a{color:var(--neon-cyan);text-decoration:none;}

/* サイト共通ヘッダー */
.site-bar{
  background:rgba(11,7,16,.82);
  border-bottom:1px solid rgba(200,194,216,.18);
  backdrop-filter:blur(8px);
  margin:0 -16px;padding:0 16px;
}
.site-bar-inner{
  max-width:760px;margin:0 auto;
  display:flex;align-items:center;justify-content:space-between;
  gap:12px;flex-wrap:wrap;padding:12px 0;
}
.site-logo{
  font-family:"Reggae One",cursive;font-size:17px;
  color:var(--lamp-gold);text-decoration:none;
  letter-spacing:.06em;text-shadow:0 0 10px rgba(255,200,50,.5);
  white-space:nowrap;
}
.site-nav{display:flex;gap:18px;flex-wrap:wrap;}
.site-nav a{
  color:var(--text-dim);text-decoration:none;font-size:13px;
  padding:3px 0;border-bottom:2px solid transparent;white-space:nowrap;
}
.site-nav a:hover{color:var(--neon-cyan);}
.site-nav a.current{color:var(--text);border-bottom-color:var(--neon-pink);}

header{text-align:center;padding:18px 0 20px;}
.eyebrow{font-family:"DotGothic16",monospace;color:var(--neon-cyan);
  letter-spacing:.25em;font-size:11px;margin:0 0 10px;}
h1{font-family:"Reggae One",cursive;font-size:clamp(21px,5vw,32px);
  margin:0;line-height:1.4;color:#fff;
  text-shadow:0 0 8px var(--neon-pink),0 0 24px rgba(255,45,120,.6),0 3px 0 #7a0b39;}

.spec-bar{
  display:flex;justify-content:center;gap:10px;flex-wrap:wrap;margin:18px 0 0;
}
.spec-bar span{
  background:rgba(255,255,255,.06);border:1px solid rgba(200,194,216,.28);
  border-radius:999px;padding:5px 14px;font-size:12px;color:var(--text-dim);
}
.spec-bar b{color:var(--lamp-gold);font-family:"DotGothic16",monospace;font-size:15px;}

.panel{
  background:linear-gradient(180deg,var(--panel),var(--hall-deep));
  border:2px solid rgba(200,194,216,.25);border-radius:14px;
  padding:22px;margin:22px 0;
  box-shadow:0 0 0 1px rgba(255,255,255,.05) inset,0 10px 30px rgba(0,0,0,.6);
}
h2{font-family:"Reggae One",cursive;font-size:18px;margin:0 0 14px;
  color:var(--lamp-gold);letter-spacing:.04em;}
h3{font-size:14px;color:var(--neon-cyan);margin:22px 0 6px;}
p{font-size:14px;color:#d8d1e8;margin:0 0 13px;}

/* 早見表 */
.table-scroll{overflow-x:auto;-webkit-overflow-scrolling:touch;}
table{width:100%;border-collapse:collapse;font-size:13px;min-width:330px;}
th,td{border:1px solid rgba(200,194,216,.25);padding:9px 6px;text-align:center;}
th{background:rgba(255,45,120,.2);color:#fff;font-size:12px;}
td:first-child{color:var(--lamp-gold);font-family:"DotGothic16",monospace;}
table.analogy td.left{text-align:left;font-size:12.5px;line-height:1.65;}
.panel p a{color:var(--neon-cyan);}
tr.mark td{background:rgba(255,200,50,.09);}

/* 計算機 */
.calc label{display:block;font-size:12px;color:var(--text-dim);margin-bottom:6px;}
.calc input{
  width:100%;background:#0a0612;border:2px solid rgba(200,194,216,.3);
  border-radius:8px;color:var(--neon-cyan);font-family:"DotGothic16",monospace;
  font-size:22px;padding:10px 12px;text-align:right;
}
.calc input:focus{outline:none;border-color:var(--neon-pink);
  box-shadow:0 0 12px rgba(255,45,120,.5);}
.calc button{
  width:100%;margin-top:14px;border:none;border-radius:999px;padding:14px;
  font-family:"Noto Sans JP",sans-serif;font-weight:900;font-size:15px;cursor:pointer;
  background:linear-gradient(180deg,#ff5c9a,var(--neon-pink));color:#fff;
  box-shadow:0 5px 0 #a30d4a,0 0 22px rgba(255,45,120,.5);
}
.calc button:active{transform:scale(.98);}

#out{display:none;margin-top:18px;background:#05030a;border:2px solid var(--lamp-gold);
  border-radius:10px;padding:18px;text-align:center;
  box-shadow:0 0 24px rgba(255,200,50,.3) inset;}
#out .lbl{font-size:11px;color:var(--text-dim);letter-spacing:.2em;}
#out .big{font-family:"DotGothic16",monospace;font-size:clamp(30px,9vw,50px);
  color:var(--lamp-gold);line-height:1.2;text-shadow:0 0 18px rgba(255,200,50,.8);}
#out .sub{font-family:"DotGothic16",monospace;font-size:16px;color:var(--neon-cyan);}
#out .cmp{
  font-size:13px;color:#d8d1e8;margin-top:12px;padding-top:12px;
  border-top:1px solid rgba(200,194,216,.2);text-align:left;
}
#out .btn-x{
  display:inline-block;margin-top:14px;
  background:#000;color:#fff;border:1px solid #555;
  text-decoration:none;font-weight:700;font-size:13px;
  padding:11px 22px;border-radius:999px;
}
#out .btn-x:hover{background:#181818;}

.cta{display:block;text-align:center;background:linear-gradient(180deg,#3ff0ff,var(--neon-cyan));
  color:#04222b;text-decoration:none;font-weight:900;font-size:14px;
  padding:14px;border-radius:999px;box-shadow:0 4px 0 #0b7f96;margin-top:8px;}

/* 広告ブロック */
.ad-block{
  position:relative;
  background:rgba(255,255,255,.03);
  border:1px solid rgba(200,194,216,.22);
  border-radius:12px;
  padding:18px 20px 20px;
  margin:22px 0;
  text-align:center;
}
.ad-label{
  position:absolute;top:-9px;left:16px;
  background:var(--hall-deep);
  border:1px solid rgba(200,194,216,.3);
  border-radius:4px;
  color:var(--text-dim);
  font-size:10px;letter-spacing:.14em;
  padding:1px 8px;
}
.ad-lead{font-size:13px;color:var(--text-dim);margin:0 0 12px;}
.ad-banner{
  display:block;margin:0 auto;
  max-width:100%;height:auto;
  border-radius:6px;
}
.ad-link{
  display:inline-block;
  color:var(--neon-cyan);
  text-decoration:none;
  font-size:14px;font-weight:700;
  border:1px solid rgba(37,229,255,.5);
  border-radius:999px;
  padding:11px 24px;
  transition:background .15s;
}
.ad-link:hover{background:rgba(37,229,255,.12);}

/* 計算直後に出る広告ボタン */
.cta-pr{margin-top:16px;padding-top:14px;border-top:1px dashed rgba(200,194,216,.25);text-align:center;}
.cta-pr .pr{display:inline-block;font-size:10px;letter-spacing:.14em;color:var(--text-dim);
  border:1px solid rgba(200,194,216,.3);border-radius:4px;padding:0 7px;margin-bottom:8px;}
.cta-pr a.cta-btn{display:block;text-decoration:none;font-weight:900;font-size:14px;
  color:#2a1300;background:linear-gradient(180deg,#ffe08a,var(--lamp-gold));
  border-radius:999px;padding:13px 16px;box-shadow:0 4px 0 #a37a10,0 0 18px rgba(255,200,50,.45);}
.cta-pr a.cta-btn:active{transform:scale(.98);}
.cta-pr .note{font-size:11px;color:var(--text-dim);margin:6px 0 0;}

.others{list-style:none;padding:0;margin:0;}
.others li{border-bottom:1px solid rgba(200,194,216,.16);}
.others a{display:flex;justify-content:space-between;gap:10px;
  padding:12px 2px;color:var(--text);text-decoration:none;font-size:14px;}
.others a:hover{color:var(--neon-cyan);}
.others .p{font-family:"DotGothic16",monospace;color:var(--lamp-gold);white-space:nowrap;}

footer{text-align:center;color:var(--text-dim);font-size:12px;padding:26px 0 0;}
footer a{color:var(--text-dim);}

@media (max-width:480px){
  body{padding:0 12px 60px;}
  .panel{padding:16px;}
  .site-bar{margin:0 -12px;padding:0 12px;}
  .site-bar-inner{padding:10px 0;}
  .site-logo{font-size:15px;}
  .site-nav{gap:14px;}
  .site-nav a{font-size:12px;}
}
"""


# ---------------------------------------------------------------
#  身近な確率でたとえる（数学的に確率が決まるものだけを使う）
# ---------------------------------------------------------------
def build_analogies():
    """(分母, 出来事, コイン投げか) のリスト"""
    a = [(2, "コインを投げて表が出る", True)]
    for n in range(2, 41):
        a.append((2 ** n, f"コインを投げて{n}回続けて表が出る", True))
    a += [(6, "サイコロを振って1の目が出る", False),
          (36, "サイコロ2個がどちらも1の目になる", False),
          (216, "サイコロ3個でピンゾロ（全部1の目）が出る", False)]
    for n in range(4, 10):
        a.append((6 ** n, f"サイコロ{n}個がすべて1の目になる", False))
    for n in range(2, 16):
        a.append((3 ** n, f"じゃんけんで{n}連勝する", False))
    a += [(13, "トランプから引いた1枚がエースである", False),
          (52, "トランプから狙った1枚を引き当てる", False),
          (1000, "ナンバーズ3をストレートで当てる", False),
          (10000, "ナンバーズ4をストレートで当てる", False),
          (169911, "ミニロトで1等に当たる", False),
          (6096454, "ロト6で1等に当たる", False),
          (10295472, "ロト7で1等に当たる", False)]
    return sorted(a)


ANALOGIES = build_analogies()


def analogy(one_in):
    """1/one_in に一番近い出来事を選んで、たとえの文を返す。
    コイン投げは2倍刻みでどこにでも近いので、ほかの出来事を少し優先する"""
    best, best_score, best_gap = None, None, None
    for d, label, coin in ANALOGIES:
        gap = one_in / d if one_in > d else d / one_in
        score = gap * (1.12 if coin else 1.0)
        if best_score is None or score < best_score:
            best, best_score, best_gap = (d, label), score, gap
    d, label = best
    if best_gap < 1.15:
        tail = "とほぼ同じ確率"
    elif best_gap < 1.5:
        tail = "と同じくらいの珍しさ"
    else:
        tail = "に近い珍しさ"
    return f"「{label}」（1/{d:,}）{tail}"


def analogy_section(m):
    """よく話題になる回転数のハマりを、身近な確率でたとえる表（静的に出す）"""
    prob = m["prob"]
    short = esc(m["short"])
    rows = []
    for spin in (500, 1000, 1500, 2000):
        r = hamari_rate(prob, spin)
        yutime = m.get("yutime")
        if yutime and spin > yutime:
            text = f"遊タイム（低確率{yutime}回転で発動）があるため、実際にはほぼ起こりません"
        elif r >= 0.5:
            text = "よくあるハマりなので、たとえるまでもありません"
        else:
            text = analogy(1 / r)
        rows.append(f"      <tr><td>{spin:,}回転</td><td>{fmt_pct(r)}</td>"
                    f"<td>{fmt_freq(r)}</td><td class=\"left\">{text}</td></tr>")
    r1000 = hamari_rate(prob, 1000)
    if m.get("yutime"):
        lead = (f"{short}（1/{prob}）には、低確率を{m['yutime']}回転消化すると発動する遊タイムがあります。"
                "下の表は遊タイムを考えない場合の確率で、遊タイムの回転数を超えるハマりは実際にはほぼ起こりません。")
    else:
        lead = (f"{short}（1/{prob}）で1000回転ハマるのは、{analogy(1 / r1000)}です。"
                if r1000 < 0.5 else
                f"{short}（1/{prob}）では、1000回転ハマりも珍しくありません。")
    return f"""
<section class="panel">
  <h2>{short}のハマりを身近な確率でたとえると</h2>
  <p>{lead}</p>
  <div class="table-scroll">
    <table class="analogy">
      <tr><th>ハマり</th><th>起こる確率</th><th>頻度</th><th>たとえると</th></tr>
{chr(10).join(rows)}
    </table>
  </div>
  <p style="margin-top:10px;font-size:12px;color:var(--text-dim);">
    ※たとえには、コイン・サイコロ・じゃんけん・トランプ・数字選択式宝くじ（ナンバーズ、ミニロト、ロト6、ロト7）など、
    確率が計算で決まる出来事だけを使っています。
  </p>
</section>
"""


# ---------------------------------------------------------------
#  1機種分のページを組み立てる
# ---------------------------------------------------------------
def num(v):
    """75.0 → 75、71.1 → 71.1 のように表示する"""
    return f"{v:g}"


def has_spec(m):
    return bool(m.get("rush_rate")) and bool(m.get("rush_cont"))


def spec_section(m, pool):
    """machines.json に rush_rate（突入率%）と rush_cont（継続率%）がある機種だけ、
    その機種のスペックから計算した数値を出す。pool はページを作る全機種。"""
    if not has_spec(m):
        return ""
    prob = m["prob"]
    short = esc(m["short"])
    rn = esc(m.get("rush_name") or "RUSH")
    rate = float(m["rush_rate"])
    cont = float(m["rush_cont"])
    r = rate / 100
    c = cont / 100

    # rush_cont_first があれば「RUSH最初の1回の継続率」として使う（2段階のRUSH向け）
    first = float(m.get("rush_cont_first") or cont)
    c1 = first / 100
    chain = 1 + c1 / (1 - c)     # 初当たりを含めた平均連チャン数
    p10 = c1 * c ** 8            # 突入後、10連以上する確率
    if first != cont:
        cont_text = f"継続率が最初は{num(first)}%、2回目以降は{num(cont)}%の場合"
    else:
        cont_text = f"継続率{num(cont)}%の場合"
    parts = []

    # RUSHに入るまで
    if r >= 1:
        parts.append(f"""  <h3>{rn}に入るまで</h3>
  <p>初当たりは必ず{rn}に入ります。そのため、{rn}に入るまでに回す通常時の回転数は、
     大当たり確率と同じ平均約{round(prob):,}回転です。</p>""")
    else:
        avg = prob / r
        miss2 = (1 - r) ** 2
        miss3 = (1 - r) ** 3
        parts.append(f"""  <h3>{rn}に入るまで</h3>
  <p>初当たりのうち{num(rate)}%が{rn}に入ります。単純計算では、{rn}に入るまでに
     通常時を<strong>平均約{avg:,.0f}回転</strong>回すことになります（{prob} ÷ {num(rate)}%）。</p>
  <p>初当たりを引いても{rn}に入らないことが2回続く確率は{fmt_pct(miss2)}、
     3回続く確率は{fmt_pct(miss3)}です。</p>""")

    # 連チャン
    parts.append(f"""  <h3>{rn}の連チャン</h3>
  <p>{cont_text}、1回の{rn}で続く連チャン数は、初当たりを含めて
     <strong>平均約{chain:.1f}回</strong>です。{rn}に入っても、1回も当たらずに終わる確率は{num(round(100 - first, 1))}%あります。</p>
  <p>{rn}に入ってから10連以上する確率は{fmt_pct(p10)}で、{rn}約{1 / p10:,.0f}回に1回の計算です。""")
    if r < 1:
        x = r * p10
        parts[-1] += (f"\n     初当たりから数えると、{rn}に入ってさらに10連以上する確率は{fmt_pct(x)}"
                      f"（初当たり約{1 / x:,.0f}回に1回）です。")
    parts[-1] += "</p>"

    # サイト内の比較（スペックを載せている機種の中での順位）
    ranked = sorted([o for o in pool if has_spec(o)], key=lambda o: -float(o["rush_cont"]))
    if len(ranked) >= 3:
        higher = [o for o in ranked if float(o["rush_cont"]) > cont]
        rank = len(higher) + 1
        lower = [o for o in ranked if float(o["rush_cont"]) < cont]
        near = []
        if higher:
            o = higher[-1]
            near.append(f'すぐ上は<a href="./{o["slug"]}.html">{esc(o["short"])}</a>（{num(float(o["rush_cont"]))}%）')
        if lower:
            o = lower[0]
            near.append(f'すぐ下は<a href="./{o["slug"]}.html">{esc(o["short"])}</a>（{num(float(o["rush_cont"]))}%）')
        near_text = ("、".join(near) + "です。") if near else ""
        ties = [o for o in ranked if float(o["rush_cont"]) == cont and o["slug"] != m["slug"]]
        if ties:
            near_text += "同じ継続率の機種は、" + "、".join(
                f'<a href="./{o["slug"]}.html">{esc(o["short"])}</a>' for o in ties) + "です。"
        parts.append(f"""  <h3>ほかの機種と比べると</h3>
  <p>当サイトでスペックを載せている{len(ranked)}機種のうち、{short}の継続率{num(cont)}%は
     {rank}番目に高い数字です。{near_text}</p>""")

    # ひとこと
    if m.get("comment"):
        parts.append(f"""  <h3>この機種のポイント</h3>
  <p>{esc(m["comment"])}</p>""")

    note = esc(m.get("rush_note") or "")
    src = ""
    if m.get("spec_url"):
        src = (f'スペックの出典：<a href="{esc(m["spec_url"])}" target="_blank" '
               f'rel="noopener nofollow">{esc(m.get("spec_src") or "出典")}</a>')
    rows = (f"      <tr><td>大当たり確率</td><td>1/{prob}</td></tr>\n"
            f"      <tr><td>{rn}突入率</td><td>{'' if rate >= 100 else '約'}{num(rate)}%</td></tr>\n"
            f"      <tr><td>{rn}継続率</td><td>約{num(cont)}%</td></tr>")
    return f"""
<section class="panel">
  <h2>{short}のスペックから計算</h2>
  <div class="table-scroll">
    <table>
      <tr><th>項目</th><th>数値</th></tr>
{rows}
    </table>
  </div>
  <p style="margin-top:10px;font-size:12px;color:var(--text-dim);">※{note}</p>
{chr(10).join(parts)}
  <p style="margin-top:14px;font-size:12px;color:var(--text-dim);">
    ※突入率と継続率は公表値をもとにした単純計算の目安です。V入賞や残保留の扱いなど、細かい条件は機種ごとに異なります。<br>
    {src}
  </p>
  <p style="margin-top:12px;"><a href="../tools/renchan.html?c={num(cont)}&amp;f={num(first)}">継続率計算ツールで、ほかの連チャン数も計算する →</a></p>
</section>
"""


def build_page(m, others):
    prob = m["prob"]
    name = m["name"]
    short = m["short"]
    half = half_point(prob)

    title = f"{short}のハマり確率｜1/{prob}で何回転ハマるとどのくらい珍しいのか"
    desc = (f"{name}（大当たり確率1/{prob}）のハマり確率early表。"
            f"100回転から3000回転まで、そのハマりが何％の確率で起こるのか、"
            f"何回に1度の出来事なのかを一覧で確認できます。回転数を入れて計算もできます。")
    desc = desc.replace("early", "早見")
    if has_spec(m):
        rn = m.get("rush_name") or "RUSH"
        title = f"{short}のハマり確率と継続率｜1/{prob}・{rn}突入率{num(float(m['rush_rate']))}%を計算"
        desc = (f"{name}（大当たり確率1/{prob}、{rn}突入率約{num(float(m['rush_rate']))}%、"
                f"継続率約{num(float(m['rush_cont']))}%）のハマり確率と、スペックから計算した"
                f"{rn}までの平均回転数・平均連チャン数を掲載。回転数を入れて計算もできます。")

    # 早見表
    rows = []
    for s in TABLE_SPINS:
        r = hamari_rate(prob, s)
        cls = ' class="mark"' if s in (1000, 2000) else ""
        rows.append(f"      <tr{cls}><td>{s:,}回転</td><td>{fmt_pct(r)}</td>"
                    f"<td>{fmt_one_in(r)}</td></tr>")
    table_rows = "\n".join(rows)

    # この機種ならではの数値
    r_at_prob = hamari_rate(prob, round(prob))
    r1000 = hamari_rate(prob, 1000)
    r2000 = hamari_rate(prob, 2000)

    # スペックの注記があれば表示する
    note_html = ""
    if m.get("note"):
        note_html = "<br>※" + esc(m["note"])

    # Xへの投稿に付けるハッシュタグ（呼称 + サイト名 + ジャンル）
    tag = (m.get("tag") or "").strip()
    tag_text = (f"#{tag} #ハマり計算機 #パチンコ" if tag else "#ハマり計算機 #パチンコ")

    # 投稿の先頭に付ける絵文字（machines.json で変更できる）
    emoji = (m.get("emoji") or "").strip()
    emoji_text = (emoji + " ") if emoji else ""

    # 計算直後に出す広告ボタン（machines.json に goods_url があれば、その作品のグッズへ飛ばす）
    goods_url = (m.get("goods_url") or "").strip()
    if goods_url:
        cta_href = goods_url
        cta_text = f"{emoji_text}{esc(short)}のグッズを見る"
        cta_pixel = ""
    else:
        cta_href = CTA_LINK
        cta_text = "🎁 アニメ・ゲームのグッズを探す"
        cta_pixel = CTA_PIXEL

    # スペックから計算したセクション（データがある機種だけ）
    spec_html = spec_section(m, others + [m])
    analogy_html = analogy_section(m)
    compare_json = json.dumps([[d, l, c] for d, l, c in ANALOGIES], ensure_ascii=False)

    # 他機種へのリンク（確率が近い機種を8つ。全機種の一覧はトップページにある）
    import math
    near_ms = sorted(others, key=lambda o: (abs(math.log(o["prob"] / prob)), o["slug"]))[:8]
    near_ms = sorted(near_ms, key=lambda o: o["prob"])
    other_items = "\n".join(
        f'      <li><a href="./{o["slug"]}.html"><span>{esc(o["short"])}</span>'
        f'<span class="p">1/{o["prob"]}</span></a></li>'
        for o in near_ms
    )

    # FAQ構造化データ
    faq = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": f"{short}で1000回転ハマる確率は？",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": f"大当たり確率1/{prob}の{name}で1000回転ハマる確率は"
                            f"{fmt_pct(r1000)}です。これは{fmt_one_in(r1000)}起こる計算になります。"
                }
            },
            {
                "@type": "Question",
                "name": f"{short}は何回転回せば半分の確率で当たりますか？",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": f"約{half:,}回転です。1/{prob}の台では、この回転数を回した時点で"
                            f"大当たりを引いている確率が50%を超えます。"
                }
            },
            {
                "@type": "Question",
                "name": f"{short}で大ハマりした後は当たりやすくなりますか？",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": f"なりません。何回転ハマった直後でも、次の1回転で当たる確率は"
                            f"1/{prob}のままです。抽選は1回転ごとに独立しているためです。"
                }
            }
        ]
    }
    if has_spec(m):
        rn = m.get("rush_name") or "RUSH"
        rate = float(m["rush_rate"])
        cont = float(m["rush_cont"])
        faq["mainEntity"].append({
            "@type": "Question",
            "name": f"{short}の{rn}突入率と継続率は？",
            "acceptedAnswer": {
                "@type": "Answer",
                "text": f"{rn}突入率は約{num(rate)}%、継続率は約{num(cont)}%です。"
                        f"継続率{num(cont)}%の場合、1回の{rn}での連チャン数は初当たりを含めて"
                        f"平均約{1 + float(m.get('rush_cont_first') or cont) / 100 / (1 - cont / 100):.1f}回の計算です。"
            }
        })
    faq_json = json.dumps(faq, ensure_ascii=False, indent=2)

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<meta name="robots" content="index, follow">
<link rel="canonical" href="{SITE}m/{m['slug']}.html">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:type" content="article">
<meta property="og:url" content="{SITE}m/{m['slug']}.html">
<meta property="og:site_name" content="ハマり確率計算機">
<meta property="og:locale" content="ja_JP">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=DotGothic16&family=Reggae+One&family=Noto+Sans+JP:wght@400;700;900&display=swap" rel="stylesheet">
<link rel="stylesheet" href="./style.css">
<script type="application/ld+json">
{faq_json}
</script>
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-9907298996043161"
     crossorigin="anonymous"></script>
</head>
<body>

<!-- サイト共通ヘッダー -->
<div class="site-bar">
  <div class="site-bar-inner">
    <a class="site-logo" href="../">PACHI-TOOL</a>
    <nav class="site-nav">
      <a href="../slot/">レア小役カウンター</a>
      <a class="current" href="../">ハマり確率計算機</a>
      <a href="../tools/renchan.html">継続率計算</a>
      <a href="../articles/">解説記事</a>
    </nav>
  </div>
</div>

<div class="wrap">

<p class="crumb"><a href="../">ハマり確率計算機</a> ／ {esc(short)}</p>

<header>
  <p class="eyebrow">HAMARI PROBABILITY</p>
  <h1>{esc(short)}<br>ハマり確率</h1>
  <div class="spec-bar">
    <span>大当たり確率 <b>1/{prob}</b></span>
    <span>{esc(m.get('type',''))}</span>
    <span>{esc(m.get('maker',''))}</span>
  </div>
</header>

<section class="panel calc">
  <h2>ハマり回転数を入れて計算する</h2>
  <label for="spin">{esc(short)}で何回転ハマったか</label>
  <input type="number" id="spin" value="1000" min="1" step="1" inputmode="numeric">
  <button id="btn">計算する</button>

  <div id="out">
    <div class="lbl">この ハマリ が 起こる 確率</div>
    <div class="big"><span id="pct">--</span></div>
    <div class="sub" id="oneIn">--</div>
    <div class="cmp" id="cmp"></div>
    <div class="cta-pr">
      <span class="pr">PR</span>
      <a class="cta-btn" href="{cta_href}" rel="sponsored nofollow noopener" target="_blank">{cta_text}</a>
      <p class="note">アニメ・マンガ・ゲームのグッズ専門ショップ FaNeMa</p>
      {cta_pixel}
    </div>
    <a id="share" class="btn-x" href="#" target="_blank" rel="noopener">この結果をXに投稿する</a>
  </div>
</section>

{AD_BLOCK}

<section class="panel">
  <h2>回転数別 ハマり確率</h2>
  <div class="table-scroll">
    <table>
      <tr><th>ハマり回転数</th><th>そこまで当たらない確率</th><th>遭遇する頻度</th></tr>
{table_rows}
    </table>
  </div>
  <p style="margin-top:14px;font-size:12px;color:var(--text-dim);">
    ※「遭遇する頻度」は、大当たりを引くたびにそのハマりに何回に1度出会うかの目安です。
    たとえば「約151回に1度」なら、大当たり151回につき1回はそこまでハマる計算になります。<br>
    ※通常時の大当たり確率1/{prob}をもとに算出した理論値です。{note_html}
  </p>
</section>
{spec_html}{analogy_html}
<section class="panel">
  <h2>1/{prob}という数字の読み方</h2>

  <h3>{prob:.0f}回転回しても当たらないことは珍しくない</h3>
  <p>大当たり確率と同じ{round(prob):,}回転を回した時点でも、まだ当たっていない確率は
     {fmt_pct(r_at_prob)}あります。「確率の分母だけ回せば当たる」わけではなく、
     3回に1度以上は分母を超えてハマる計算です。</p>

  <h3>半分の確率で当たるのは約{half:,}回転</h3>
  <p>{short}を打ち始めてから、大当たりを引いている確率が50%を超えるのは
     約{half:,}回転を回した時点です。大当たり確率の分母より多く回して、
     ようやく五分五分になります。</p>

  <h3>1000回転・2000回転のハマりはどのくらい珍しいか</h3>
  <p>1000回転のハマりは{fmt_pct(r1000)}（{fmt_one_in(r1000)}）、
     2000回転のハマりは{fmt_pct(r2000)}（{fmt_one_in(r2000)}）です。
     1000回転程度であれば長く打っていれば遭遇する範囲ですが、
     2000回転を超えると相当まれな部類に入ります。</p>

  <h3>ハマった後は当たりやすくなるのか</h3>
  <p>なりません。{short}の抽選は1回転ごとに独立しているため、
     何回転ハマった直後でも次の1回転の当選確率は1/{prob}のままです。
     「そろそろ当たる」と感じるのはギャンブラーの誤謬と呼ばれる錯覚です。</p>
</section>

<section class="panel">
  <h2>ハマり確率をもっと知る</h2>
  <ul class="others">
    <li><a href="../articles/hamari-keisan.html"><span>ハマり確率の計算方法をやさしく解説</span></a></li>
    <li><a href="../articles/bunbo.html"><span>分母まで回せば当たる？本当の当たりやすさ</span></a></li>
    <li><a href="../articles/hamari-dai.html"><span>ハマり台は当たりやすい？数字で確かめる</span></a></li>
  </ul>
</section>

<section class="panel">
  <h2>1/{prob}に近い確率の機種</h2>
  <ul class="others">
{other_items}
  </ul>
  <a class="cta" href="../">確率を自由に入力して計算する</a>
</section>

<footer>
  <p>本ページの数値は確率計算による理論値です。実際の遊技結果を保証するものではありません。<br>
     スペックは変更される場合があります。正確な情報はメーカー公式をご確認ください。<br>
     遊技は20歳以上・自己資金の範囲内でお楽しみください。</p>
  <p style="margin-top:12px;"><a href="../privacy.html">プライバシーポリシー</a> ／ <a href="../about.html">運営者情報</a> ／ <a href="../contact.html">お問い合わせ</a></p>
</footer>

</div>

<script>
var PROB = {prob};
var NAME = "{esc(short)}";
var PAGE = "{SITE}m/{m['slug']}.html";
var TAGS = "{tag_text}";
var EMOJI = "{emoji_text}";

var spin  = document.getElementById('spin');
var out   = document.getElementById('out');
var pct   = document.getElementById('pct');
var one   = document.getElementById('oneIn');
var cmp   = document.getElementById('cmp');
var share = document.getElementById('share');

function fmtPct(p){{
  if(p >= 10) return p.toFixed(1);
  if(p >= 1)  return p.toFixed(2);
  if(p >= 0.01) return p.toFixed(3);
  if(p >= 0.00001) return p.toFixed(5);
  return 'ほぼ0';   // 0が並ぶだけになるので言葉で表す
}}
function fmtFreq(p, prefix){{
  // 50%以上は回数で言わない
  if(p >= 0.5) return 'よくあるハマり';
  var n = 1 / p;
  var head = prefix ? '初当たり約' : '約';
  // 桁が多すぎると読めなくなるので単位を使う
  if(n >= 1e12) return head + (n/1e12).toFixed(1) + '兆回に1回';
  if(n >= 1e8)  return head + (n/1e8).toFixed(1) + '億回に1回';
  return head + Math.round(n).toLocaleString() + '回に1回';
}}

// 身近な出来事とくらべる（build.py の ANALOGIES と同じリスト）
var COMPARE = {compare_json};
function makeCompare(oneIn){{
  var best = COMPARE[0], score = Infinity, gap = Infinity;
  for(var i=0;i<COMPARE.length;i++){{
    var g = oneIn > COMPARE[i][0] ? oneIn/COMPARE[i][0] : COMPARE[i][0]/oneIn;
    var sc = g * (COMPARE[i][2] ? 1.12 : 1);
    if(sc < score){{ score = sc; gap = g; best = COMPARE[i]; }}
  }}
  var label = '1/' + best[0].toLocaleString();
  if(gap < 1.15) return 'これは「' + best[1] + '」（' + label + '）とほぼ同じ確率です。';
  if(gap < 1.5)  return 'これは「' + best[1] + '」（' + label + '）と同じくらいの珍しさです。';
  return 'これは「' + best[1] + '」（' + label + '）に近い珍しさです。';
}}

document.getElementById('btn').addEventListener('click', function(){{
  var s = parseInt(spin.value, 10);
  if(!s || s < 1) return;
  var p = Math.pow((PROB - 1) / PROB, s);

  pct.textContent = fmtPct(p * 100) + '%';
  one.textContent = fmtFreq(p, true);
  cmp.textContent = makeCompare(1 / p);

  // Xへの投稿文を組み立てる
  var freq = (p >= 0.5) ? 'よくあるハマり'
                        : '初当たり約' + Math.round(1 / p).toLocaleString() + '回に1回のレア度';
  var text = EMOJI + NAME + '\\n'
    + s.toLocaleString() + '回転ハマり（1/' + PROB + '）\\n'
    + freq + '\\n'
    + TAGS;
  share.href = 'https://twitter.com/intent/tweet?text='
    + encodeURIComponent(text) + '&url=' + encodeURIComponent(PAGE + '?utm_source=x');

  out.style.display = 'block';
}});
</script>
</body>
</html>
"""


def sort_by_new(machines):
    """導入日の新しい順に並べる（導入日が未記入のものは後ろに回す）"""
    return sorted(machines, key=lambda m: (m.get("intro") or "0000-00-00"), reverse=True)


def build_news(data, targets, limit=10):
    """トップページの「更新履歴」。machines.json の news と、新台の導入日から自動で作る"""
    items = [(n["date"], n.get("tag", "更新"), esc(n["text"])) for n in data.get("news", [])]
    groups = {}
    for m in targets:
        d = m.get("intro") or ""
        if d and d <= TODAY:
            groups.setdefault(d, []).append(m)
    for d, ms in groups.items():
        names = "、".join(f'<a href="./m/{x["slug"]}.html">{esc(x["short"])}</a>' for x in ms[:3])
        more = f" ほか{len(ms) - 3}機種" if len(ms) > 3 else ""
        mo, da = int(d[5:7]), int(d[8:10])
        items.append((d, "新台", f"{mo}/{da}導入の{names}{more}のハマり確率ページ"))
    items.sort(key=lambda x: x[0], reverse=True)
    lis = "\n".join(
        f'    <li><time datetime="{d}">{d.replace("-", ".")}</time>'
        f'<span class="tag">{esc(t)}</span><span class="txt">{txt}</span></li>'
        for d, t, txt in items[:limit])
    return ('<!-- NEWS_START ここから下は build.py が自動生成します。手で編集しないでください -->\n'
            '  <ul class="news">\n' + lis + '\n  </ul>\n'
            '  <!-- NEWS_END -->')


def update_index(targets, news_block=None):
    """トップページの機種リンク一覧（と更新履歴）を書き換える"""
    path = "index.html"
    if not os.path.exists(path):
        print("  ※ index.html が見つからないため、リンク一覧の更新をスキップしました")
        return

    items = "\n".join(
        f'    <li><a href="./m/{m["slug"]}.html">'
        f'<span>{esc(m["short"])}</span>'
        f'<span class="p">1/{m["prob"]}</span></a></li>'
        for m in targets
    )
    block = ('<!-- MACHINE_LINKS_START ここから下は build.py が自動生成します。'
             '手で編集しないでください -->\n'
             '  <ul class="machine-links">\n' + items + '\n  </ul>\n'
             '  <!-- MACHINE_LINKS_END -->')

    html = open(path, encoding="utf-8").read()
    new_html, n = re.subn(
        r"<!-- MACHINE_LINKS_START.*?MACHINE_LINKS_END -->",
        lambda _: block, html, flags=re.S)

    if n == 0:
        print("  ※ index.html に目印が見つからないため更新できませんでした")
        return

    if news_block:
        new_html, k = re.subn(r"<!-- NEWS_START.*?NEWS_END -->",
                              lambda _: news_block, new_html, flags=re.S)
        if k:
            print("  更新: index.html の更新履歴")

    open(path, "w", encoding="utf-8").write(new_html)
    print(f"  更新: index.html のリンク一覧（{len(targets)}件）")


# ---------------------------------------------------------------
#  実行
# ---------------------------------------------------------------
def main():
    data = json.load(open("machines.json", encoding="utf-8"))
    machines = data["machines"]
    # 新しい機種が上に来るように並べ替える
    targets = sort_by_new([m for m in machines if m.get("page")])

    os.makedirs("m", exist_ok=True)

    # 共通スタイル
    with open("m/style.css", "w", encoding="utf-8") as f:
        f.write(STYLE)

    # 各機種ページ
    for m in targets:
        others = [o for o in targets if o["slug"] != m["slug"]]
        with open(f"m/{m['slug']}.html", "w", encoding="utf-8") as f:
            f.write(build_page(m, others))
        print(f"  生成: m/{m['slug']}.html  ({m['short']} 1/{m['prob']})")

    # "page": false にした機種の古いページを消す（machines.json に載っている機種だけが対象。
    # 機種データは残るので、"page": true に戻せば次の実行でページが復活する）
    for m in machines:
        if not m.get("page"):
            old = f"m/{m['slug']}.html"
            if os.path.exists(old):
                os.remove(old)
                print(f"  削除: {old}  ({m['short']})")

    # サイトマップ
    urls = [(SITE, "weekly", "1.0"), (SITE + "privacy.html", "yearly", "0.3")]
    for page_name in ("about.html", "contact.html"):
        if os.path.exists(page_name):
            urls.append((SITE + page_name, "yearly", "0.3"))
    # 解説記事（articles/ フォルダにあるHTMLをすべて載せる）
    if os.path.isdir("articles"):
        urls.append((SITE + "articles/", "monthly", "0.7"))
        for fn in sorted(os.listdir("articles")):
            if fn.endswith(".html") and fn != "index.html":
                urls.append((f"{SITE}articles/{fn}", "monthly", "0.7"))
    # ツール（tools/ フォルダにあるHTMLをすべて載せる）
    if os.path.isdir("tools"):
        for fn in sorted(os.listdir("tools")):
            if fn.endswith(".html"):
                urls.append((f"{SITE}tools/{fn}", "monthly", "0.8"))
    for m in targets:
        urls.append((f"{SITE}m/{m['slug']}.html", "monthly", "0.8"))

    body = "\n".join(
        f"  <url>\n    <loc>{u}</loc>\n    <lastmod>{TODAY}</lastmod>\n"
        f"    <changefreq>{c}</changefreq>\n    <priority>{p}</priority>\n  </url>"
        for u, c, p in urls
    )
    with open("sitemap.xml", "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n'
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                + body + "\n</urlset>\n")

    # テキスト形式のサイトマップ（1行1URL。XMLとは別経路の予備）
    with open("sitemap.txt", "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(u for u, _, _ in urls) + "\n")

    # トップページのリンク一覧
    update_index(targets, build_news(data, targets))

    print(f"\n完了: {len(targets)}ページ生成 / sitemap.xml に{len(urls)}件を登録")


if __name__ == "__main__":
    main()
