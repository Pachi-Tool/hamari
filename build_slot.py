#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
slot_machines.json から スロット「レア役カウンター」ページを自動生成する。

出力:
  slot/index.html      機種一覧
  slot/m/<slug>.html   機種ごとのカウンターページ
  slot/sitemap.xml     スロット用サイトマップ

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
    <a href="__SLOT_HOME__">レア役カウンター</a>
    <a href="__HOME__">ハマり確率計算機</a>
  </nav>
</header>
"""

FOOT = """
<footer class="site">
  <a href="__SLOT_HOME__">レア役カウンター トップ</a>
  <a href="__HOME__">ハマり確率計算機</a>
  <a href="__PRIVACY__">プライバシーポリシー</a>
</footer>
</div>
<script src="__JS__"></script>
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


def foot(home, slot_home, privacy, js):
    return (FOOT
            .replace("__HOME__", home)
            .replace("__SLOT_HOME__", slot_home)
            .replace("__PRIVACY__", privacy)
            .replace("__JS__", js))


def role_card(role):
    name = esc(role["name"])
    return f"""      <li class="role" data-role="{name}">
        <div class="role-name">{name}</div>
        <button type="button" class="arrow up" aria-label="{name} を1回足す">▲</button>
        <div class="count">0</div>
        <button type="button" class="arrow down" aria-label="{name} を1回減らす">▼</button>
        <div class="prob">1/－</div>
      </li>
"""


def ref_table(machine):
    roles = [r for r in machine["roles"] if r.get("probs")]
    if not roles:
        return ""
    settings = []
    for r in roles:
        for k in r["probs"].keys():
            if k not in settings:
                settings.append(k)
    settings.sort()
    head_cells = "".join(f"<th>設定{esc(s)}</th>" for s in settings)
    rows = ""
    for r in roles:
        cells = ""
        for s in settings:
            v = r["probs"].get(s)
            cells += f"<td>{'1/' + esc(v) if v else '－'}</td>"
        rows += f'<tr><td class="rolecell">{esc(r["name"])}</td>{cells}</tr>\n'
    return f"""<h2>設定別のレア役確率（参考）</h2>
<div class="panel">
<table class="ref">
<tr><th>レア役</th>{head_cells}</tr>
{rows}</table>
<p class="note">※ 数値は参考値です。実際のカウント結果と見比べる目安としてお使いください。</p>
</div>
"""


def build_machine_page(machine, cfg):
    base = cfg["base_url"] + cfg["section_path"]
    name = machine["name"]
    title = f'{name} レア役合算・レア役カウンター'
    desc = (f'{name} のレア役（チェリー・スイカ・チャンス目など）を'
            f'▲▼ボタンのタップで1回ずつカウント。合算回数と出現率（1/○○）を自動計算します。')
    canonical = f'{base}m/{machine["slug"]}.html'
    cards = "".join(role_card(r) for r in machine["roles"])
    note = f'<p class="lead">{esc(machine["note"])}</p>' if machine.get("note") else ""
    tags = ""
    chips = [machine.get("maker"), machine.get("type"), machine.get("intro")]
    chips = [c for c in chips if c]
    if chips:
        tags = '<div class="tagrow">' + "".join(f'<span class="tag">{esc(c)}</span>' for c in chips) + "</div>"

    body = f"""<h1>{esc(title)}</h1>
{tags}{note}
<section class="panel counter" data-slug="{esc(machine['slug'])}" data-name="{esc(name)}">
  <div class="label">総ゲーム数</div>
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

  <div class="label" style="margin-top:18px">レア役カウント（▲で＋1／▼で−1）</div>
  <ul class="roles">
{cards}  </ul>

  <div class="label" style="margin-top:18px">合算</div>
  <div class="total">
    <div class="t-label">レア役合算</div>
    <div class="t-box"><div class="t-count">0</div><div class="t-cap">回</div></div>
    <div class="t-box"><div class="t-prob">1/－</div><div class="t-cap">合算確率</div></div>
  </div>

  <div class="actions">
    <button type="button" class="btn danger" id="reset">リセット</button>
    <button type="button" class="btn share" id="share">Xに投稿する</button>
  </div>
</section>

{ref_table(machine)}
<h2>使い方</h2>
<div class="panel">
  <p class="note">1. 打ち始めに「総ゲーム数」を入力します（あとから直しても確率は再計算されます）。<br>
  2. レア役を引くたびに、その役の <strong>▲</strong> をタップして1回ずつカウントします。押し間違えたら <strong>▼</strong> で戻せます。<br>
  3. 各レア役の出現率と、全レア役を足した「レア役合算」の確率が 1/○○ で自動表示されます。<br>
  4. カウントはこの端末のブラウザに自動保存されるので、席を立っても消えません。消したいときは「リセット」を2回押してください。</p>
</div>

<h2>他の機種を選ぶ</h2>
<div class="panel"><p class="note"><a href="../">機種一覧ページ</a>から他の機種のレア役カウンターを開けます。</p></div>
"""
    return (head(title, desc, canonical, "../style.css", "../../", "../")
            + body
            + foot("../../", "../", "../../privacy.html", "../counter.js"))


def build_index(cfg, machines):
    base = cfg["base_url"] + cfg["section_path"]
    title = "スロット レア役カウンター｜機種別のレア役合算をタップで集計"
    desc = ("パチスロのレア役（チェリー・スイカ・チャンス目など）を▲▼のタップで1回ずつカウントし、"
            "合算回数と出現率（1/○○）を自動計算できる無料ツールです。機種別ページを用意しています。")
    items = ""
    for m in machines:
        sub = " / ".join([c for c in [m.get("maker"), m.get("type")] if c])
        items += f"""    <li><a href="m/{esc(m['slug'])}.html">
      <div class="m-name">{esc(m['name'])} レア役カウンター</div>
      <div class="m-sub">{esc(sub) if sub else 'レア役 ' + str(len(m['roles'])) + '種'}</div></a></li>
"""
    body = f"""<h1>スロット レア役カウンター</h1>
<p class="lead">レア役を引くたびに▲をタップするだけ。各レア役の回数・合算回数と、1/○○の出現率が自動で出ます。</p>
<h2>機種を選ぶ</h2>
<div class="panel">
  <ul class="machines">
{items}  </ul>
</div>
<h2>このツールについて</h2>
<div class="panel">
  <p class="note">総ゲーム数とレア役の回数から、レア役ごとの出現率と合算確率を計算します。
  カウントは端末のブラウザに保存されるため、ページを閉じても残ります。設定推測や自身の実戦データの記録にお使いください。</p>
</div>
"""
    return (head(title, desc, base, "style.css", "../", "./")
            + body
            + foot("../", "./", "../privacy.html", "counter.js"))


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
        path = os.path.join(M_DIR, m["slug"] + ".html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(build_machine_page(m, cfg))
        print("wrote", os.path.relpath(path, ROOT))

    with open(os.path.join(OUT_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(build_index(cfg, machines))
    print("wrote slot/index.html")

    with open(os.path.join(OUT_DIR, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(build_sitemap(cfg, machines))
    print("wrote slot/sitemap.xml")
    print(f"完了: {len(machines)} 機種")


if __name__ == "__main__":
    main()
