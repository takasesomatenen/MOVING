"""海沿い格安物件マスタを全国地図にピン化する(1枚)。

殿堂(HALL OF FAME)物件は金の★ピンで強調、その他は価格帯で色分けした●ピン。
Leaflet + OpenStreetMap タイル。ブラウザ/Vercel配信で表示(Artifactはタイル
CSPでブロックされるため standalone HTML)。

座標は scraper/data/listings_geo.json(id -> [lat,lng]・市町村目安の推定値)から。
未登録idは警告してスキップ。

使い方: python -m scraper.listings_map
出力: data/report/listings_map.html
"""

import csv
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MASTER = os.path.join(ROOT, "data", "listings_master.csv")
GEO = os.path.join(ROOT, "scraper", "data", "listings_geo.json")
OUT_HTML = os.path.join(ROOT, "data", "report", "listings_map.html")

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


def price_color(p):
    if p <= 100:
        return "#2f8f4e"   # 緑: 〜100万
    if p <= 200:
        return "#2c6fb0"   # 青: 〜200万
    if p <= 300:
        return "#c07a1e"   # 橙: 〜300万
    return "#8a4b9c"       # 紫: 300万超


def build(rows, geo):
    hall_markers = []
    other_markers = []
    missing = []
    for r in rows:
        rid = r["id"]
        coord = geo.get(rid)
        if not coord:
            missing.append((rid, r["location"]))
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
        title = r["title"]
        loc = r["location"]
        url = r.get("url") or ""
        is_hall = rid in HALL
        crown = HALL.get(rid, "")
        color = price_color(p)
        popup = (
            (f"【殿堂・{crown}】" if is_hall else "")
            + f"<b>{title}</b>"
            + f"<br>{int(p) if p==int(p) else p}万円 ／ {loc}"
            + (f"<br>建物単価 {mm}万/㎡" if mm else "")
        )
        popup = json.dumps(popup, ensure_ascii=False)
        url_j = json.dumps(url, ensure_ascii=False)
        crown_j = json.dumps(crown, ensure_ascii=False)
        m = (
            f"pin({lat},{lng},{popup},{json.dumps(color)},"
            f"{'true' if is_hall else 'false'},{crown_j},{url_j})"
        )
        if is_hall:
            hall_markers.append(m)
        else:
            other_markers.append(m)

    hall_js = ",\n      ".join(hall_markers)
    other_js = ",\n      ".join(other_markers)
    n_hall = len(hall_markers)
    n_other = len(other_markers)

    return f"""<!doctype html><html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>海沿い格安物件マップ</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  html,body {{ margin:0; height:100%; font-family:system-ui,-apple-system,"Hiragino Kaku Gothic ProN","Noto Sans JP",Meiryo,sans-serif; }}
  #map {{ position:absolute; inset:0; }}
  .title {{ position:absolute; z-index:1000; top:12px; left:12px; background:rgba(255,255,255,.93);
           padding:9px 14px; border-radius:10px; box-shadow:0 2px 10px rgba(0,0,0,.18); max-width:min(72vw,340px); }}
  .title h1 {{ margin:0; font-size:15px; }}
  .title p {{ margin:3px 0 0; font-size:11px; color:#556; line-height:1.5; }}
  .legend b {{ color:#334; }}
  .dot {{ display:inline-block; width:10px; height:10px; border-radius:50%; margin:0 3px -1px 8px; }}
  .pin-dot {{ width:16px; height:16px; border-radius:50%; border:2px solid #fff; box-shadow:0 1px 3px rgba(0,0,0,.5); }}
  .pin-hall {{ font-size:24px; line-height:24px; text-align:center; filter:drop-shadow(0 1px 2px rgba(0,0,0,.55)); }}
  .leaflet-popup-content {{ font-size:13px; line-height:1.5; }}
  .cnt {{ display:inline-block; margin-left:5px; color:#888; font-size:11px; }}
  .leaflet-control-layers {{ font-size:13px; }}
</style></head>
<body>
<div class="title"><h1>🗾 海沿い格安物件マップ</h1>
<p class="legend">全{n_hall + n_other}件をピン表示。<b>★=殿堂({n_hall})</b>／●価格帯:
<span class="dot" style="background:#2f8f4e"></span>〜100万
<span class="dot" style="background:#2c6fb0"></span>〜200万
<span class="dot" style="background:#c07a1e"></span>〜300万
<span class="dot" style="background:#8a4b9c"></span>300万超<br>
ピンをタップで詳細・掲載元・Googleマップ。座標は市町村目安の概算です。</p></div>
<div id="map"></div>
<script>
  const map = L.map('map', {{ center:[36.2,137.0], zoom:5 }});
  L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
    maxZoom:19, attribution:'&copy; OpenStreetMap'
  }}).addTo(map);

  function pin(lat,lng,popup,color,isHall,crown,url) {{
    let icon;
    if (isHall) {{
      icon = L.divIcon({{ className:'', html:'<div class="pin-hall">⭐</div>',
        iconSize:[26,26], iconAnchor:[13,13] }});
    }} else {{
      icon = L.divIcon({{ className:'',
        html:'<div class="pin-dot" style="background:'+color+'"></div>',
        iconSize:[16,16], iconAnchor:[8,8] }});
    }}
    const m = L.marker([lat,lng], {{icon, zIndexOffset: isHall?1000:0}});
    let html = popup;
    if (url) html += '<br><a href="'+url+'" target="_blank" rel="noopener">🏳️ 掲載元を見る</a>';
    html += '<br><a href="https://www.google.com/maps/search/?api=1&query='+lat+','+lng+
      '" target="_blank" rel="noopener">Googleマップで開く</a>';
    m.bindPopup(html);
    return m;
  }}

  const layer_hall = L.layerGroup([
      {hall_js}
  ]);
  const layer_other = L.layerGroup([
      {other_js}
  ]);
  layer_hall.addTo(map);
  layer_other.addTo(map);

  const overlays = {{
    "⭐ 殿堂<span class=cnt>{n_hall}</span>": layer_hall,
    "● その他物件<span class=cnt>{n_other}</span>": layer_other
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
    missing = [r["id"] for r in rows if r["id"] not in geo]
    print("map:", OUT_HTML, f"({placed}/{len(rows)}件ピン)")
    if missing:
        print("座標未登録(スキップ):", ", ".join(missing))


if __name__ == "__main__":
    main()
