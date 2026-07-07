"""master CSV から写真ギャラリー風の HTML を生成する。

掲載元サイトの多くが自動アクセスを 403 で拒否するため実写真は埋め込めない。
代わりに各物件を写真カード化し、「写真・詳細を見る」で掲載元/画像検索へ
ワンクリックで飛べるようにする(実写真はクリック先で閲覧)。
テーマ対応(light/dark)。Artifact としても、repo の HTML としても使える。
"""

import csv
import datetime as dt
import html
import os
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MASTER_PATH = os.path.join(ROOT, "data", "listings_master.csv")
OUT_HTML = os.path.join(ROOT, "data", "report", "gallery.html")

# 価格帯ごとのカード上部グラデーション(海のトーン)
TIERS = [
    (150, "#0a3d4d", "#0d7c94", "〜150万"),
    (250, "#0d6478", "#1a9bb5", "〜250万"),
    (10**9, "#146c7a", "#37b0c4", "〜300万"),
]


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def load_rows():
    rows = []
    with open(MASTER_PATH, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            r["_price"] = _f(r.get("price_man"))
            r["_bld"] = _f(r.get("building_m2"))
            r["_land"] = _f(r.get("land_m2"))
            r["_unit"] = round(r["_price"] / r["_bld"], 2) if (r["_price"] and r["_bld"]) else None
            rows.append(r)
    rows.sort(key=lambda r: (r["_price"] if r["_price"] is not None else 1e9))
    return rows


def _tier(price):
    for cap, c1, c2, _label in TIERS:
        if price is None or price <= cap:
            return c1, c2
    return TIERS[-1][1], TIERS[-1][2]


def _fmt(v, suffix=""):
    if v is None or v == "":
        return "—"
    if isinstance(v, float):
        v = int(v) if v.is_integer() else round(v, 2)
    return f"{v}{suffix}"


def _img_search_url(r):
    """物件所在地ベースの画像検索(実写真がすぐ見つかる保険リンク)。"""
    q = f"{r.get('location','')} 中古住宅 空き家 海".strip()
    return "https://www.google.com/search?tbm=isch&q=" + urllib.parse.quote(q)


def card(r):
    c1, c2 = _tier(r["_price"])
    src = html.escape((r.get("url") or "").split("#")[0])
    loc = html.escape(r.get("location") or "")
    title = html.escape(r.get("title") or "")
    pref = loc[:3] if loc else "🌊"
    badges = []
    if r["_bld"]:
        badges.append(f'<span>🏠 建物 {_fmt(r["_bld"], "㎡")}</span>')
    if r["_land"]:
        badges.append(f'<span>🌏 土地 {_fmt(r["_land"], "㎡")}</span>')
    if r.get("madori"):
        badges.append(f'<span>🚪 {html.escape(r["madori"])}</span>')
    if r["_unit"]:
        badges.append(f'<span>💴 {r["_unit"]}万/㎡</span>')
    note = html.escape(r.get("note") or "")
    return f"""
    <article class="card">
      <div class="photo" style="--c1:{c1};--c2:{c2}">
        <div class="wave">〜〜〜</div>
        <div class="pref">{html.escape(pref)}</div>
        <div class="price">{_fmt(r['_price'])}<small>万円</small></div>
      </div>
      <div class="body">
        <div class="loc">📍 {loc}</div>
        <div class="ttl">{title}</div>
        <div class="badges">{''.join(badges)}</div>
        {f'<div class="note">※ {note}</div>' if note else ''}
        <div class="actions">
          <a class="btn primary" href="{src}" target="_blank" rel="noopener">📷 掲載元で写真・詳細</a>
          <a class="btn" href="{_img_search_url(r)}" target="_blank" rel="noopener">🔍 画像検索</a>
        </div>
      </div>
    </article>"""


def build_html(rows, today):
    priced = [r for r in rows if r["_price"] is not None]
    cheapest = min((r["_price"] for r in priced), default=0)
    cards = "\n".join(card(r) for r in rows)
    return f"""<!doctype html><html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>海沿い格安物件ギャラリー {today}</title>
<style>
  :root {{
    --bg:#eef4f6; --card:#ffffff; --ink:#0f2733; --sub:#5b7079;
    --line:#e0e9ec; --chip:#f2f8f9; --accent:#0d7c94;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{ --bg:#0c1417; --card:#132025; --ink:#e7f0f2; --sub:#93a7ad;
            --line:#22343a; --chip:#182930; --accent:#3bb6cc; }}
  }}
  :root[data-theme="light"] {{ --bg:#eef4f6; --card:#fff; --ink:#0f2733; --sub:#5b7079; --line:#e0e9ec; --chip:#f2f8f9; --accent:#0d7c94; }}
  :root[data-theme="dark"] {{ --bg:#0c1417; --card:#132025; --ink:#e7f0f2; --sub:#93a7ad; --line:#22343a; --chip:#182930; --accent:#3bb6cc; }}
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ font-family:system-ui,-apple-system,"Hiragino Kaku Gothic ProN","Noto Sans JP",Meiryo,"IPAGothic",sans-serif; background:var(--bg);
         color:var(--ink); -webkit-font-smoothing:antialiased; padding:28px 18px 60px; }}
  .head {{ max-width:1200px; margin:0 auto 22px; }}
  .kick {{ color:var(--accent); font-weight:700; letter-spacing:.16em; font-size:12px; }}
  h1 {{ font-size:26px; margin:4px 0 6px; }}
  .sub {{ color:var(--sub); font-size:13px; }}
  .grid {{ max-width:1200px; margin:0 auto; display:grid;
          grid-template-columns:repeat(auto-fill, minmax(260px, 1fr)); gap:18px; }}
  .card {{ background:var(--card); border:1px solid var(--line); border-radius:16px;
          overflow:hidden; display:flex; flex-direction:column; }}
  .photo {{ position:relative; height:130px; background:linear-gradient(135deg,var(--c1),var(--c2));
           color:#fff; display:flex; align-items:flex-end; padding:12px 14px; overflow:hidden; }}
  .photo .wave {{ position:absolute; inset:0; display:flex; align-items:center;
                 justify-content:center; font-size:60px; opacity:.18; letter-spacing:-6px; }}
  .photo .pref {{ position:absolute; top:10px; left:14px; font-size:12px; font-weight:700;
                 background:rgba(255,255,255,.22); padding:3px 9px; border-radius:20px; }}
  .photo .price {{ font-size:30px; font-weight:800; z-index:1; text-shadow:0 1px 4px rgba(0,0,0,.25); }}
  .photo .price small {{ font-size:13px; font-weight:600; }}
  .body {{ padding:13px 14px 14px; display:flex; flex-direction:column; gap:7px; flex:1; }}
  .loc {{ font-size:12px; color:var(--sub); font-weight:600; }}
  .ttl {{ font-size:13.5px; font-weight:700; line-height:1.4; }}
  .badges {{ display:flex; flex-wrap:wrap; gap:6px; margin-top:2px; }}
  .badges span {{ background:var(--chip); border-radius:7px; padding:3px 8px;
                 font-size:11.5px; color:var(--ink); }}
  .note {{ font-size:10.5px; color:var(--sub); line-height:1.5; }}
  .actions {{ display:flex; gap:8px; margin-top:auto; padding-top:6px; }}
  .btn {{ flex:1; text-align:center; text-decoration:none; font-size:12px; font-weight:700;
         padding:9px 6px; border-radius:9px; border:1px solid var(--line);
         color:var(--ink); background:var(--chip); }}
  .btn.primary {{ background:var(--accent); color:#fff; border-color:var(--accent); }}
  .foot {{ max-width:1200px; margin:26px auto 0; font-size:11px; color:var(--sub); line-height:1.7; }}
</style></head>
<body>
  <div class="head">
    <div class="kick">SEASIDE HOUSE GALLERY ・ 海沿い格安物件</div>
    <h1>海沿い・田舎の激安物件ギャラリー</h1>
    <div class="sub">条件: 海沿い / 土地＋上物 〜300万円 / 多少ボロOK ・ {len(rows)}件 ・ 最安 {_fmt(cheapest)}万円 ・ {today}</div>
  </div>
  <div class="grid">
    {cards}
  </div>
  <div class="foot">
    📷「掲載元で写真・詳細」＝物件の掲載ページ(実写真あり)を開きます。🔍「画像検索」＝所在地で画像検索します。<br>
    ※ 物件写真は掲載元サイトにあり、多くが自動アクセスを拒否するためカード内への実写真埋め込みは行っていません。<br>
    ※ 価格・在庫・面積は掲載元での一次確認が必要です(シードは WebSearch 由来)。
  </div>
</body></html>"""


def main():
    rows = load_rows()
    today = dt.date.today().isoformat()
    os.makedirs(os.path.dirname(OUT_HTML), exist_ok=True)
    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(build_html(rows, today))
    print("gallery:", OUT_HTML, f"({len(rows)}件)")


if __name__ == "__main__":
    main()
