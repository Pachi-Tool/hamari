#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
machines.json を読んで、機種ごとのページと sitemap.xml を生成する。

使い方:  python3 build.py

生成されるもの:
  m/<slug>.html   機種ごとのページ
  m/style.css     機種ページ共通のスタイル
  sitemap.xml     全ページを載せたサイトマップ
"""

import json
import math
import os
import re
from datetime import date

SITE = "https://pachi-tool.github.io/hamari/"
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
    if p >= 0.0001:
        return f"{p:.5f}%"
    # これ以上小さいと0が並んで読めないので「◯万回に1度」側に任せる
    return f"{p:.7f}%"


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
  <a href="https://px.a8.net/svt/ejp?a8mat=4BAFPF+FM17UA+5PLE+5YZ75"
     rel="sponsored nofollow noopener" target="_blank">
    <img class="ad-banner" border="0" width="300" height="250" alt="広告"
         loading="lazy"
         src="https://www25.a8.net/svt/bgt?aid=260827395944&amp;wid=001&amp;eno=01&amp;mid=s00000026645001003000&amp;mc=1">
  </a>
  <img border="0" width="1" height="1"
       src="https://www17.a8.net/0.gif?a8mat=4BAFPF+FM17UA+5PLE+5YZ75" alt="">
</aside>"""


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
}
"""


# ---------------------------------------------------------------
#  1機種分のページを組み立てる
# ---------------------------------------------------------------
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

    # 他機種へのリンク
    other_items = "\n".join(
        f'      <li><a href="./{o["slug"]}.html"><span>{esc(o["short"])}</span>'
        f'<span class="p">1/{o["prob"]}</span></a></li>'
        for o in others
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
</head>
<body>
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
  <h2>他の機種のハマり確率</h2>
  <ul class="others">
{other_items}
  </ul>
  <a class="cta" href="../">確率を自由に入力して計算する</a>
</section>

<footer>
  <p>本ページの数値は確率計算による理論値です。実際の遊技結果を保証するものではありません。<br>
     スペックは変更される場合があります。正確な情報はメーカー公式をご確認ください。<br>
     遊技は20歳以上・自己資金の範囲内でお楽しみください。</p>
  <p style="margin-top:12px;"><a href="../privacy.html">プライバシーポリシー</a></p>
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
  return p.toFixed(5);
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

// 身近な出来事とくらべる
var COMPARE = [
  [2,'コイン投げで表を出す'],[4,'コイン投げで2回連続表を出す'],[6,'サイコロで1の目を出す'],
  [8,'コイン投げで3回連続表を出す'],[13,'トランプでエースを引く'],[20,'サイコロ2個でゾロ目を出す'],
  [36,'サイコロ2個で狙ったゾロ目を出す'],[50,'50人から自分が選ばれる'],[64,'コイン投げで6回連続表を出す'],
  [100,'1から100の数字を当てる'],[216,'サイコロ3個でピンゾロを出す'],[365,'知らない人と誕生日が一致する'],
  [500,'ペットボトルのキャンペーンで当たりが出る'],[1024,'コイン投げで10回連続表を出す'],
  [2000,'四つ葉のクローバーを一発で見つける'],[4500,'同姓同名の人に出会う'],[10000,'宝くじで1万円に当たる'],
  [43000,'宝くじで10万円に当たる'],[220000,'ナンバーズ4をストレートで当てる'],[1000000,'雷に打たれる'],
  [6100000,'ロト6で1等に当たる'],[20000000,'宝くじ1等に当たる'],[60000000,'ロト7で1等に当たる']
];
function makeCompare(oneIn){{
  var best = COMPARE[0], gap = Infinity;
  for(var i=0;i<COMPARE.length;i++){{
    var r = oneIn > COMPARE[i][0] ? oneIn/COMPARE[i][0] : COMPARE[i][0]/oneIn;
    if(r < gap){{ gap = r; best = COMPARE[i]; }}
  }}
  var label = '約1/' + best[0].toLocaleString();
  if(gap < 1.15) return 'これは「' + best[1] + '」（' + label + '）とほぼ同じ確率です。';
  if(gap < 1.8)  return 'これは「' + best[1] + '」（' + label + '）と同じくらいの珍しさです。';
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


def update_index(targets):
    """トップページの機種リンク一覧を書き換える"""
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

    # サイトマップ
    urls = [(SITE, "weekly", "1.0"), (SITE + "privacy.html", "yearly", "0.3")]
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

    # トップページのリンク一覧
    update_index(targets)

    print(f"\n完了: {len(targets)}ページ生成 / sitemap.xml に{len(urls)}件を登録")


if __name__ == "__main__":
    main()
