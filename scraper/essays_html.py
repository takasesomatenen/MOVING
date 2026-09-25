#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""essays/*.md を レポートハブと同じ見た目の HTML に変換し、
   エッセイ索引ページ(data/report/essays.html)と各記事(data/report/essays/<title>.html)を生成する。
   markdown ライブラリ非依存の軽量コンバータ。"""
import os, re, json, html, glob, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ESSAY_DIR = os.path.join(ROOT, "essays")
OUT_DIR = os.path.join(ROOT, "data", "report", "essays")

CSS = """
  :root{ --bg:#eaf2f4; --card:#fff; --ink:#0f2a33; --sub:#5f7681; --line:#d8e5e8; --accent:#0d7c94; --chip:#f1f8f9; }
  @media (prefers-color-scheme:dark){ :root{ --bg:#0a1417; --card:#12232a; --ink:#e7f1f3; --sub:#8ba3aa; --line:#22383f; --accent:#3bb6cc; --chip:#152a31; } }
  :root[data-theme="light"]{ --bg:#eaf2f4; --card:#fff; --ink:#0f2a33; --sub:#5f7681; --line:#d8e5e8; --accent:#0d7c94; --chip:#f1f8f9; }
  :root[data-theme="dark"]{ --bg:#0a1417; --card:#12232a; --ink:#e7f1f3; --sub:#8ba3aa; --line:#22383f; --accent:#3bb6cc; --chip:#152a31; }
  *{ box-sizing:border-box; margin:0; padding:0; }
  body{ font-family:system-ui,-apple-system,"Hiragino Kaku Gothic ProN","Noto Sans JP",Meiryo,sans-serif;
        background:var(--bg); color:var(--ink); -webkit-font-smoothing:antialiased; padding:30px 18px 80px; line-height:1.9; }
  .wrap{ max-width:680px; margin:0 auto; }
  .back{ font-size:12.5px; color:var(--accent); font-weight:700; text-decoration:none; display:inline-block; margin-bottom:18px; }
  h1.ttl{ font-size:26px; margin:2px 0 20px; letter-spacing:.01em; }
  h1.chap{ font-size:21px; margin:34px 0 4px; padding-top:22px; border-top:1px solid var(--line); letter-spacing:.01em; }
  .lead-h{ font-size:13px; color:var(--accent); font-weight:700; margin:0 0 14px; }
  h2.sub{ font-size:15px; color:var(--sub); margin:22px 0 6px; font-weight:700; }
  p{ font-size:14.5px; margin:10px 0; }
  p.italic{ color:var(--sub); font-style:italic; font-size:13.5px; }
  strong{ color:var(--ink); font-weight:700; }
  a{ color:var(--accent); font-weight:700; text-decoration:none; }
  a:hover{ text-decoration:underline; }
  hr{ border:0; border-top:1px dashed var(--line); margin:8px 0; }
  a.flag{ display:inline-block; margin:6px 0; padding:9px 13px; background:var(--chip); border:1px solid var(--line);
          border-radius:12px; font-size:13px; }
  a.flag:hover{ border-color:var(--accent); text-decoration:none; }
  table{ width:100%; border-collapse:collapse; margin:14px 0; font-size:12.5px; }
  th,td{ border:1px solid var(--line); padding:7px 9px; text-align:left; vertical-align:top; }
  th{ background:var(--chip); color:var(--accent); }
  .cards{ display:grid; grid-template-columns:repeat(auto-fit,minmax(230px,1fr)); gap:14px; margin-top:6px; }
  a.card{ display:block; text-decoration:none; color:var(--ink); background:var(--card); border:1px solid var(--line);
          border-radius:16px; padding:18px; transition:transform .12s, border-color .12s; }
  a.card:hover{ transform:translateY(-2px); border-color:var(--accent); }
  a.card .ico{ font-size:24px; } a.card h2{ font-size:15px; margin:9px 0 4px; border:0; padding:0; color:var(--ink); }
  a.card p{ font-size:12.5px; color:var(--sub); line-height:1.55; }
  .note{ font-size:11.5px; color:var(--sub); line-height:1.8; margin-top:28px; border-top:1px dashed var(--line); padding-top:14px; }
"""

def inline(s):
    """**bold**, [text](url), 素のURL以外はエスケープしてからinline装飾を戻す。"""
    # リンクを一旦プレースホルダに退避（中身をエスケープ）
    links = []
    def _link(m):
        label, url = m.group(1), m.group(2)
        links.append((label, url))
        return "\x00L%d\x00" % (len(links) - 1)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", _link, s)
    s = html.escape(s)
    # bold
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    # リンクを復元
    def _restore(m):
        label, url = links[int(m.group(1))]
        cls = "flag" if label.strip().startswith("🏳") else ""
        a = '<a class="%s" href="%s">%s</a>' % (cls, html.escape(url, quote=True), html.escape(label))
        return a
    s = re.sub(r"\x00L(\d+)\x00", _restore, s)
    return s

def md_to_html(md):
    lines = md.split("\n")
    out, i = [], 0
    n = len(lines)
    while i < n:
        ln = lines[i].rstrip()
        if not ln.strip():
            i += 1; continue
        if ln.strip() == "---":
            # 連続する --- はまとめて1本の区切りに
            while i < n and lines[i].strip() == "---":
                i += 1
            out.append("<hr>")
            continue
        if ln.startswith("# "):
            out.append('<h1 class="chap">%s</h1>' % inline(ln[2:].strip()))
            i += 1; continue
        if ln.startswith("## "):
            out.append('<h2 class="sub">%s</h2>' % inline(ln[3:].strip()))
            i += 1; continue
        # テーブル（| で始まる連続行）
        if ln.startswith("|"):
            tbl = []
            while i < n and lines[i].strip().startswith("|"):
                tbl.append(lines[i].strip()); i += 1
            rows = []
            for r in tbl:
                cells = [c.strip() for c in r.strip().strip("|").split("|")]
                rows.append(cells)
            # 区切り行(---)を除去、先頭をヘッダに
            body = [r for r in rows if not all(set(c) <= set("-: ") for c in r)]
            html_rows = []
            for idx, r in enumerate(body):
                tag = "th" if idx == 0 else "td"
                html_rows.append("<tr>" + "".join("<%s>%s</%s>" % (tag, inline(c), tag) for c in r) + "</tr>")
            out.append("<table>" + "".join(html_rows) + "</table>")
            continue
        # 物件ヘッダ（**所在地 / 価格 …** だけの行）
        if re.fullmatch(r"\*\*.+\*\*", ln.strip()):
            out.append('<p class="lead-h">%s</p>' % inline(ln.strip().strip("*")))
            i += 1; continue
        # イタリック段落（*…* だけの行）
        if re.fullmatch(r"\*[^*].*\*", ln.strip()):
            out.append('<p class="italic">%s</p>' % inline(ln.strip()[1:-1]))
            i += 1; continue
        # 通常段落
        out.append("<p>%s</p>" % inline(ln.strip()))
        i += 1
    return "\n".join(out)

def page(title, body_html, back_href="../home.html"):
    return ('<!doctype html><html lang="ja"><head><meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            '<title>%s ― MOVING 海沿い物件エッセイ</title>\n<style>%s</style></head>\n'
            '<body><div class="wrap">\n<a class="back" href="%s">← レポートハブへ戻る</a>\n'
            '%s\n</div></body></html>\n') % (html.escape(title), CSS, back_href, body_html)

def build():
    os.makedirs(OUT_DIR, exist_ok=True)
    state_path = os.path.join(ESSAY_DIR, "state.json")
    order = []
    if os.path.exists(state_path):
        st = json.load(open(state_path, encoding="utf-8"))
        for e in st.get("essays", []):
            base = os.path.basename(e["file"])
            order.append((base, e.get("title", base[:-3])))
    # state に無い .md も拾う
    seen = {b for b, _ in order}
    for p in sorted(glob.glob(os.path.join(ESSAY_DIR, "*.md"))):
        b = os.path.basename(p)
        if b not in seen:
            order.append((b, b[:-3]))
    items = []
    for base, title in order:
        src = os.path.join(ESSAY_DIR, base)
        if not os.path.exists(src):
            continue
        md = open(src, encoding="utf-8").read()
        # 記事タイトル（1本目の # 見出し群の親題として md ファイル名ベースを使う）
        disp = base[:-3]
        body = '<h1 class="ttl">%s</h1>\n%s' % (html.escape(disp), md_to_html(md))
        out_name = base[:-3] + ".html"
        with open(os.path.join(OUT_DIR, out_name), "w", encoding="utf-8") as f:
            f.write(page(disp, body))
        # リード（各章題を拾って一言に）
        chaps = re.findall(r"^# (.+)$", md, re.M)
        chaps = [c for c in chaps if "、" not in c or c == chaps[-1]]  # ざっくり
        sub = " / ".join(re.sub(r"（.*?）", "", c).strip() for c in re.findall(r"^# (.+)$", md, re.M)[:-1]) or "海沿い物件をめぐる読み物。"
        items.append((disp, out_name, sub))
    # 索引ページ
    cards = []
    for disp, out_name, sub in items:
        href = urllib.parse.quote("essays/" + out_name)
        cards.append(
            '<a class="card" href="%s"><div class="ico">📖</div><h2>%s</h2>'
            '<p>%s</p><span class="go" style="color:var(--accent);font-weight:700;font-size:12px;">読む →</span></a>'
            % (href, html.escape(disp), html.escape(sub)))
    idx_body = ('<h1 class="ttl">📖 海沿い物件エッセイ</h1>\n'
                '<p style="color:var(--sub);font-size:13.5px;margin-bottom:18px;">'
                '格安物件の「その先の暮らし」を、実在の周辺情報（魚・灯台・カフェ・人口・海の種類）で編んだ読み物。'
                '各章末の🏳️から掲載元へ飛べます。</p>\n<div class="cards">\n%s\n</div>') % ("\n".join(cards))
    with open(os.path.join(ROOT, "data", "report", "essays.html"), "w", encoding="utf-8") as f:
        f.write(page("海沿い物件エッセイ", idx_body, back_href="home.html"))
    print("essays-html: %d本 → data/report/essays.html + data/report/essays/*.html" % len(items))
    return len(items)

if __name__ == "__main__":
    build()
