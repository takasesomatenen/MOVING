"""海沿い格安物件マスタを全国地図にピン化する(1枚)。

リンクの“確度”で3分類してピン化する:
  ⭐ 殿堂(HALL)          … 金の星
  ✓ 直リンク物件         … 個別ページURL(掲載元でその物件に直接飛べる)。塗りつぶしピン
  〜 参考(一覧リンク)     … 一覧/バンク/検索ページへのリンク。中空ピン
     ※末尾 #anchor は飾りで、その物件が現在も掲載中とは限らない。

ポップアップのリンク文言も確度で出し分ける:
  detail → 「🏳️ この物件を見る（掲載元）」
  list   → 「🔎 掲載元サイトで探す（個別ページ未確定）」#フラグメントは外す

Leaflet + OpenStreetMap タイル。ブラウザ/Vercel配信で表示。
座標は scraper/data/listings_geo.json(id -> [lat,lng]・市町村目安)。未登録idは警告してスキップ。

使い方: python -m scraper.listings_map
出力: data/report/listings_map.html
"""

import csv
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MASTER = os.path.join(ROOT, "data", "listings_master.csv")
GEO = os.path.join(ROOT, "scraper", "data", "listings_geo.json")
OUT_HTML = os.path.join(ROOT, "data", "report", "listings_map.html")

# 個別物件ページ(直リンク)判定。verify.py の DETAIL_RE を拡張(haruka-f / homes b- を含む)
DETAIL_RE = re.compile(
    r"(/bukken/detail/|/detail/|athome\.co\.jp/kodate/\d{6,}|"
    r"athome\.co\.jp/tochi/\d{6,}|resort-bukken\.com/detail/|"
    r"homes\.co\.jp/akiyabank/b-\d+|haruka-f\.co\.jp/sale/detail/|"
    r"erajapan\.co\.jp/catalog/.+/\d+/|sinsei-heights\.jp/[^/]+/detail-)"
)

# 殿堂(hall.html)8選の master id と称号
HALL = {
    "303ae82ab60c": "王座",
    "fc84007889f7": "破格",
    "6381da52a5af": "渚百選",
    "01ec29dcfe54": "波打ち際",
    "f55e8312ad82": "黄昏",
    "943609188ef3": "全面展望",
    "4c471f47fcac": "豪",
    "be91490ff3f2": "北天",
}


def is_detail(url):
    return bool(DETAIL_RE.search((url or "").split("#")[0]))


def price_color(p):
    if p <= 100:
        return "#2f8f4e"
    if p <= 200:
        return "#2c6fb0"
    if p <= 300:
        return "#c07a1e"
    return "#8a4b9c"


def build(rows, geo):
    hall_m, detail_m, list_m = [], [], []
    missing = []
    n_detail_total = 0
    for r in rows:
        rid = r["id"]
        coord = geo.get(rid)
        if not coord:
            missing.append(rid)
            continue
        lat, lng = coord[0], coord[1]
        try:
            p = float(r["price_man"])
        except (TypeError, ValueError):
            p = 0.0
        b = r.get("building_m2") or ""
        mm = ""
        try:
            if b and b not in ("", "—", "0"):
                mm = f"{p/float(b):.2f}"
        except ValueError:
            mm = ""
        url = r.get("url") or ""
        detail = is_detail(url)
        if detail:
            n_detail_total += 1
        is_hall = rid in HALL
        crown = HALL.get(rid, "")
        color = price_color(p)
        pnum = int(p) if p == int(p) else p
        popup = (
            (f"【殿堂・{crown}】" if is_hall else "")
            + f"<b>{r['title']}</b>"
            + f"<br>{pnum}万円 ／ {r['location']}"
            + (f"<br>建物単価 {mm}万/㎡" if mm else "")
        )
        # リンク: detail は直リンク＋「この物件」/ list は #除去＋「検索」
        if detail:
            link = f'<br><a href="{url}" target="_blank" rel="noopener">🏳️ この物件を見る（掲載元）</a>'
        else:
            base = url.split("#")[0]
            link = (f'<br><a href="{base}" target="_blank" rel="noopener">🔎 掲載元サイトで探す（個別ページ未確定）</a>'
                    if base else "")
        popup_j = json.dumps(popup + link, ensure_ascii=False)
        marker = (
            f"pin({lat},{lng},{popup_j},{json.dumps(color)},"
            f"{'true' if is_hall else 'false'},{'true' if detail else 'false'})"
        )
        if is_hall:
            hall_m.append(marker)
        elif detail:
            detail_m.append(marker)
        else:
            list_m.append(marker)

    n_hall, n_det, n_lst = len(hall_m), len(detail_m), len(list_m)
    total = n_hall + n_det + n_lst
    hall_js = ",\n      ".join(hall_m)
    det_js = ",\n      ".join(detail_m)
    lst_js = ",\n      ".join(list_m)

    return f"""<!doctype html><html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>海沿い格安物件マップ</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  html,body {{ margin:0; height:100%; font-family:system-ui,-apple-system,"Hiragino Kaku Gothic ProN","Noto Sans JP",Meiryo,sans-serif; }}
  #map {{ position:absolute; inset:0; }}
  .title {{ position:absolute; z-index:1000; top:12px; left:12px; background:rgba(255,255,255,.94);
           padding:10px 14px; border-radius:10px; box-shadow:0 2px 10px rgba(0,0,0,.2); max-width:min(76vw,360px); }}
  .title h1 {{ margin:0; font-size:15px; }}
  .title p {{ margin:4px 0 0; font-size:11px; color:#556; line-height:1.55; }}
  .title .warn {{ color:#b4531f; font-weight:700; }}
  .dot {{ display:inline-block; width:10px; height:10px; border-radius:50%; margin:0 3px -1px 8px; }}
  .ring {{ display:inline-block; width:10px; height:10px; border-radius:50%; border:2px solid #7a8a90; margin:0 3px -1px 8px; }}
  .pin-dot {{ width:16px; height:16px; border-radius:50%; border:2px solid #fff; box-shadow:0 1px 3px rgba(0,0,0,.5); }}
  .pin-ring {{ width:14px; height:14px; border-radius:50%; border:2px dashed #8a8f93; background:rgba(255,255,255,.55); box-shadow:0 1px 2px rgba(0,0,0,.35); }}
  .pin-hall {{ font-size:24px; line-height:24px; text-align:center; filter:drop-shadow(0 1px 2px rgba(0,0,0,.55)); }}
  .leaflet-popup-content {{ font-size:13px; line-height:1.55; }}
  .cnt {{ display:inline-block; margin-left:5px; color:#888; font-size:11px; }}
  .leaflet-control-layers {{ font-size:13px; }}
</style></head>
<body>
<div class="title"><h1>🗾 海沿い格安物件マップ</h1>
<p>全<b>{total}</b>件。<span class="warn">個別ページに直接飛べるのは {n_detail_total}件</span>、残り<b>{n_lst}</b>件は掲載元サイトでの<b>検索リンク</b>（その物件が今も掲載中とは限りません）。<br>
<b>⭐殿堂{n_hall}</b>／<span class="dot" style="background:#2c6fb0"></span>✓直リンク{n_det}／<span class="ring"></span>〜参考{n_lst}。ピンをタップで詳細。</p></div>
<div id="map"></div>
<script>
  const map = L.map('map', {{ center:[36.2,137.0], zoom:5 }});
  L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
    maxZoom:19, attribution:'&copy; OpenStreetMap'
  }}).addTo(map);

  function pin(lat,lng,popup,color,isHall,detail) {{
    let icon;
    if (isHall) {{
      icon = L.divIcon({{ className:'', html:'<div class="pin-hall">⭐</div>', iconSize:[26,26], iconAnchor:[13,13] }});
    }} else if (detail) {{
      icon = L.divIcon({{ className:'', html:'<div class="pin-dot" style="background:'+color+'"></div>', iconSize:[16,16], iconAnchor:[8,8] }});
    }} else {{
      icon = L.divIcon({{ className:'', html:'<div class="pin-ring"></div>', iconSize:[14,14], iconAnchor:[7,7] }});
    }}
    const m = L.marker([lat,lng], {{icon, zIndexOffset: isHall?1000:(detail?500:0)}});
    m.bindPopup(popup);
    return m;
  }}

  const layer_hall = L.layerGroup([
      {hall_js}
  ]);
  const layer_detail = L.layerGroup([
      {det_js}
  ]);
  const layer_list = L.layerGroup([
      {lst_js}
  ]);
  layer_hall.addTo(map);
  layer_detail.addTo(map);
  layer_list.addTo(map);

  const overlays = {{
    "⭐ 殿堂<span class=cnt>{n_hall}</span>": layer_hall,
    "✓ 直リンク物件<span class=cnt>{n_det}</span>": layer_detail,
    "〜 参考・要検索<span class=cnt>{n_lst}</span>": layer_list
  }};
  L.control.layers(null, overlays, {{collapsed:false}}).addTo(map);
</script>
</body></html>"""


def main():
    with open(MASTER, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    with open(GEO, encoding="utf-8") as f:
        geo = json.load(f)
    html = build(rows, geo)
    os.makedirs(os.path.dirname(OUT_HTML), exist_ok=True)
    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    placed = sum(1 for r in rows if r["id"] in geo)
    detail = sum(1 for r in rows if r["id"] in geo and is_detail(r.get("url")))
    missing = [r["id"] for r in rows if r["id"] not in geo]
    print("map:", OUT_HTML, f"({placed}/{len(rows)}件ピン / うち個別直リンク{detail}件)")
    if missing:
        print("座標未登録(スキップ):", ", ".join(missing))


if __name__ == "__main__":
    main()
