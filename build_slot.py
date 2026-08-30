#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
slot_machines.json から スロット「レア小役カウンター」ページを自動生成する。

出力:
  slot/index.html        機種一覧
  slot/m/<slug>.html     機種ごとのカウンターページ
  slot/machines-data.js  全機種データ（ページ内の機種切替に使用）
  slot/sitemap.xml       スロット用サイトマップ

slot/style.css と slot/counter.js は固定ファイル（このスクリプトでは触らない）。
使い方:  python build_slot.py
"""
import json
import os
import html
from datetime import date

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "slot_machines.json")
OUT_DIR = os.path.join(ROOT, "slot")
M_DIR = os.path.join(OUT_DIR, "m")

HEAD = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<meta name="description" content="__DESC__">
<link rel="canonical" href="__CANONICAL__">
<meta property="og:type" content="website">
<meta property="og:title" content="__TITLE__">
<meta property="og:description" content="__DESC__">
<meta property="og:url" content="__CANONICAL__">
<meta name="twitter:card" content="summary">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=DotGothic16&family=Noto+Sans+JP:wght@400;700&family=Reggae+One&display=swap" rel="stylesheet">
<link rel="stylesheet" href="__CSS__">
</head>
<body>
<div class="wrap">
<header class="site">
  <a class="logo" href="__HOME__">PACHI-TOOL</a>
  <nav>
    <a href="__SLOT_HOME__">レア小役カウンター</a>
    <a href="__HOME__">ハマり確率計算機</a>
  </nav>
</header>
"""

FOOT = """
<footer class="site">
  <a href="__SLOT_HOME__">レア小役カウンター トップ</a>
  <a href="__HOME__">ハマり確率計算機</a>
  <a href="__PRIVACY__">プライバシーポリシー</a>
</footer>
</div>
__SCRIPTS__
</body>
</html>
"""


def esc(s):
    return html.escape(str(s), quote=True)


def head(title, desc, canonical, css, home, slot_home):
    return (HEAD
            .replace("__TITLE__", esc(title))
            .replace("__DESC__", esc(desc))
            .replace("__CANONICAL__", esc(canonical))
            .replace("__CSS__", css)
            .replace("__HOME__", home)
            .replace("__SLOT_HOME__", slot_home))


def foot(home, slot_home, privacy, scripts):
    return (FOOT
            .replace("__HOME__", home)
            .replace("__SLOT_HOME__", slot_home)
            .replace("__PRIVACY__", privacy)
            .replace("__SCRIPTS__", scripts))


# ---------------- 部品 ----------------

def theory_text(item):
    """公表されている出現確率の表示（1/○○ もしくは 設定1〜6の範囲）。"""
    if item.get("common"):
        return "1/" + esc(item["common"]), "解析"
    probs = item.get("probs") or {}
    keys = sorted(probs.keys())
    if len(keys) == 1:
        return "1/" + esc(probs[keys[0]]), "設定" + esc(keys[0])
    if len(keys) > 1:
        return ("1/" + esc(probs[keys[0]]) + "〜1/" + esc(probs[keys[-1]]),
                "設定" + esc(keys[0]) + "〜" + esc(keys[-1]))
    return "－", "解析"


def prob_block(item):
    val, label = theory_text(item)
    return (f'<div class="probs">'
            f'<div class="prob-row"><span class="k">{label}</span><span class="v theory">{val}</span></div>'
            f'<div class="prob-row"><span class="k">現在</span><span class="v now">1/－</span></div>'
            f'</div>')


def role_card(role):
    name = esc(role["name"])
    alias = f'<div class="role-alias">＝{esc(role["alias"])}</div>' if role.get("alias") else ""
    return f"""      <li class="role" data-role="{name}">
        <div class="role-name">{name}</div>{alias}
        <button type="button" class="arrow up" aria-label="{name} を1回足す">▲</button>
        <div class="count">0</div>
        <button type="button" class="arrow down" aria-label="{name} を1回減らす">▼</button>
{prob_block(role)}
      </li>
"""


def machine_tags(machine):
    chips = [c for c in [machine.get("maker"), machine.get("type"), machine.get("intro")] if c]
    if not chips:
        return ""
    return "".join(f'<span class="tag">{esc(c)}</span>' for c in chips)


def settei_table(machine):
    """設定差のあるレア小役だけを設定別の表にする。"""
    roles = [r for r in machine["roles"] if r.get("diff") and r.get("probs")]
    if not roles:
        return ('<p class="note">この機種は、レア小役の出現率に設定差が確認されていません。'
                'カウントは実戦データの記録用としてお使いください。</p>')
    settings = []
    for r in roles:
        for k in r["probs"]:
            if k not in settings:
                settings.append(k)
    settings.sort()
    ths = "".join(f"<th>設定{esc(s)}</th>" for s in settings)
    rows = ""
    for r in roles:
        tds = ""
        for s in settings:
            v = r["probs"].get(s)
            tds += f"<td>{'1/' + esc(v) if v else '－'}</td>"
        rows += f'<tr><td class="rolecell hit">{esc(r["name"])}</td>{tds}</tr>\n'
    return f"""<div class="tablewrap"><table class="ref">
<tr><th>レア小役</th>{ths}</tr>
{rows}</table></div>
<p class="note">設定差が確認されているのはこのレア小役です。ここが伸びているかどうかが設定推測の手がかりになります。</p>"""


def other_table(machine):
    """設定差のない・不明なレア小役の確率一覧。"""
    roles = [r for r in machine["roles"] if not (r.get("diff") and r.get("probs"))]
    if not roles:
        return ""
    rows = ""
    for r in roles:
        if r.get("common"):
            v = f'1/{esc(r["common"])}<span class="cap">全設定共通</span>'
        elif r.get("probs", {}).get("1"):
            v = f'1/{esc(r["probs"]["1"])}<span class="cap">設定1の値</span>'
        else:
            v = '<span class="cap">調査中</span>'
        rows += f'<tr><td class="rolecell">{esc(r["name"])}</td><td>{v}</td></tr>\n'
    return f"""<h3 class="sub-h">そのほかのレア小役</h3>
<div class="tablewrap"><table class="ref">
<tr><th>レア小役</th><th>出現率</th></tr>
{rows}</table></div>"""


def sources_html(machine):
    if not machine.get("sources"):
        return ""
    links = "、".join(
        f'<a href="{esc(u)}" target="_blank" rel="nofollow noopener">{esc(u.split("/")[2])}</a>'
        for u in machine["sources"])
    return f'<p class="note src">確率の出典：{links}</p>'


def machine_select(machines, current_slug):
    real = [m for m in machines if not m["slug"].endswith("general")]
    gen = [m for m in machines if m["slug"].endswith("general")]

    def opts(lst):
        out = ""
        for m in lst:
            sel = " selected" if m["slug"] == current_slug else ""
            out += f'    <option value="{esc(m["slug"])}"{sel}>{esc(m["name"])}</option>\n'
        return out
    return f"""  <select id="machine-select" aria-label="機種を選ぶ">
  <optgroup label="機種を選ぶ">
{opts(real)}  </optgroup>
  <optgroup label="機種が一覧にないとき">
{opts(gen)}  </optgroup>
  </select>
"""


# ---------------- ページ生成 ----------------

def build_machine_page(machine, cfg, machines):
    base = cfg["base_url"] + cfg["section_path"]
    name = machine["name"]
    title = f'{name} レア小役合算・レア小役カウンター'
    role_names = "・".join(r["name"] for r in machine["roles"][:4])
    desc = (f'{name} のレア小役（{role_names}など）を▲▼ボタンのタップで1回ずつカウント。'
            f'合算回数と出現率（1/○○）を自動計算します。設定差のあるレア小役も確認できます。')
    canonical = f'{base}m/{machine["slug"]}.html'
    cards = "".join(role_card(r) for r in machine["roles"])
    has_diff = any(r.get("diff") and r.get("probs") for r in machine["roles"])
    if machine.get("combined"):
        cval, clabel = theory_text(machine["combined"])
        total_theory = f'解析値（{clabel}）：{cval}'
    else:
        total_theory = ""
    ref_heading = "設定推測に使えるレア小役" if has_diff else "レア小役の出現率"

    body = f"""<h1 id="machine-title">{esc(title)}</h1>
<div class="tagrow" id="machine-tags">{machine_tags(machine)}</div>
<p class="lead" id="machine-note">{esc(machine.get("note", ""))}</p>

<section class="panel counter" data-slug="{esc(machine['slug'])}" data-name="{esc(name)}">
  <div class="label">機種</div>
{machine_select(machines, machine["slug"])}

  <div class="label" style="margin-top:16px">総ゲーム数</div>
  <div class="games-row">
    <button type="button" class="step" data-step="-100">−100</button>
    <input id="games" type="number" inputmode="numeric" min="0" step="1" value="0" aria-label="総ゲーム数">
    <button type="button" class="step" data-step="100">＋100</button>
  </div>
  <div class="label" style="margin-top:6px">
    <button type="button" class="step" data-step="-10">−10</button>
    <button type="button" class="step" data-step="10">＋10</button>
    <span class="unit">G</span>
  </div>

  <div class="label" style="margin-top:18px">レア小役カウント（▲で＋1／▼で−1）</div>
  <ul class="roles">
{cards}  </ul>

  <div class="label" style="margin-top:18px">合算</div>
  <div class="total">
    <div class="t-label">レア小役合算</div>
    <div class="t-box"><div class="t-count">0</div><div class="t-cap">回</div></div>
    <div class="t-box"><div class="t-prob">1/－</div><div class="t-cap">現在の合算確率</div></div>
  </div>
  <div class="total-theory" id="total-theory">{total_theory}</div>

  <div class="actions">
    <button type="button" class="btn danger" id="reset">リセット</button>
    <button type="button" class="btn share" id="share">Xに投稿する</button>
  </div>
</section>

<h2 id="ref-heading">{ref_heading}</h2>
<div class="panel" id="ref-area">
{settei_table(machine)}
{other_table(machine)}
{sources_html(machine)}
</div>

<h2>使い方</h2>
<div class="panel">
  <p class="note">1. 上の「機種」から打っている機種を選ぶと、その機種のレア小役が並びます。<br>
  2. 打ち始めに「総ゲーム数」を入力します（あとから直しても確率は再計算されます）。<br>
  3. レア小役を引くたびに、その役の <strong>▲</strong> をタップして1回ずつカウントします。押し間違えたら <strong>▼</strong> で戻せます。<br>
  4. 各レア小役の出現率と、全レア小役を足した「レア小役合算」の確率が 1/○○ で自動表示されます。<br>
  5. カウントは機種ごとにこの端末へ自動保存されます。消したいときは「リセット」を2回押してください。</p>
</div>

<h2>他の機種を選ぶ</h2>
<div class="panel"><p class="note">上のプルダウンで切り替えられます。<a href="../">機種一覧ページ</a>からも開けます。</p></div>
"""
    scripts = '<script src="../machines-data.js"></script>\n<script src="../counter.js"></script>'
    return (head(title, desc, canonical, "../style.css", "../../", "../")
            + body
            + foot("../../", "../", "../../privacy.html", scripts))


def build_index(cfg, machines):
    base = cfg["base_url"] + cfg["section_path"]
    title = "スロット レア小役カウンター｜機種別のレア小役合算をタップで集計"
    desc = ("パチスロのレア小役（チェリー・スイカ・チャンス目など）を▲▼のタップで1回ずつカウントし、"
            "合算回数と出現率（1/○○）を自動計算できる無料ツールです。機種を選ぶとその機種のレア小役が並びます。")
    real = [m for m in machines if not m["slug"].endswith("general")]
    gen = [m for m in machines if m["slug"].endswith("general")]

    def items(lst):
        out = ""
        for m in lst:
            sub = " / ".join([c for c in [m.get("maker"), m.get("type")] if c])
            diff = [r["name"] for r in m["roles"] if r.get("diff")]
            badge = f'<span class="m-badge">設定差：{esc("・".join(diff))}</span>' if diff else ""
            out += f"""    <li><a href="m/{esc(m['slug'])}.html">
      <div class="m-name">{esc(m['name'])}</div>
      <div class="m-sub">{esc(sub) if sub else 'レア小役 ' + str(len(m['roles'])) + '種'}</div>{badge}</a></li>
"""
        return out
    body = f"""<h1>スロット レア小役カウンター</h1>
<p class="lead">レア小役を引くたびに▲をタップするだけ。各レア小役の回数・合算回数と、1/○○の出現率が自動で出ます。機種を選べば、その機種のレア小役がそのまま並びます。</p>
<h2>機種を選ぶ</h2>
<div class="panel">
  <ul class="machines">
{items(real)}  </ul>
</div>
<h2>機種が一覧にないとき</h2>
<div class="panel">
  <ul class="machines">
{items(gen)}  </ul>
</div>
<h2>このツールについて</h2>
<div class="panel">
  <p class="note">総ゲーム数とレア小役の回数から、レア小役ごとの出現率と合算確率を計算します。
  カウントは機種ごとに端末のブラウザへ保存されるため、ページを閉じても残ります。<br>
  なお、レア小役の出現率に設定差がある機種は多くありません。設定差が確認されている役は機種ページに明記しているので、そこを見比べてください。</p>
</div>
"""
    return (head(title, desc, base, "style.css", "../", "./")
            + body
            + foot("../", "./", "../privacy.html", ""))


def build_data_js(machines):
    slim = []
    for m in machines:
        slim.append({
            "slug": m["slug"], "name": m["name"], "maker": m.get("maker", ""),
            "type": m.get("type", ""), "intro": m.get("intro", ""),
            "note": m.get("note", ""), "sources": m.get("sources", []),
            "combined": m.get("combined"),
            "roles": m["roles"],
        })
    return ("/* 自動生成ファイル。編集しないでください（slot_machines.json を直してください） */\n"
            "window.SLOT_MACHINES = " + json.dumps(slim, ensure_ascii=False) + ";\n")


def build_sitemap(cfg, machines):
    base = cfg["base_url"] + cfg["section_path"]
    today = date.today().isoformat()
    urls = [base] + [f"{base}m/{m['slug']}.html" for m in machines]
    body = "\n".join(
        f"  <url><loc>{esc(u)}</loc><lastmod>{today}</lastmod></url>" for u in urls)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            f'{body}\n</urlset>\n')


def main():
    with open(DATA, encoding="utf-8") as f:
        cfg = json.load(f)
    machines = [m for m in cfg["machines"] if m.get("page", True)]
    os.makedirs(M_DIR, exist_ok=True)

    for m in machines:
        with open(os.path.join(M_DIR, m["slug"] + ".html"), "w", encoding="utf-8") as f:
            f.write(build_machine_page(m, cfg, machines))

    with open(os.path.join(OUT_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(build_index(cfg, machines))
    with open(os.path.join(OUT_DIR, "machines-data.js"), "w", encoding="utf-8") as f:
        f.write(build_data_js(machines))
    with open(os.path.join(OUT_DIR, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(build_sitemap(cfg, machines))
    print(f"完了: {len(machines)} 機種のページと一覧・データ・サイトマップを生成しました")


if __name__ == "__main__":
    main()
