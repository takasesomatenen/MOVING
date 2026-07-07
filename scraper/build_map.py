"""館山 移住・運用マップ(1枚)を生成する。

ユーザー要望: 運用するマップは1つにして、これから色々なレイヤーの情報を
入れていきたい(夕陽スポット / カフェ / コンビニ / スーパー / ランドマーク …)。
Leaflet + OpenStreetMap タイルを使う自己完結 HTML。ブラウザで開けば
タイル・地図が表示される(Artifact ではタイル CSP でブロックされるため、
standalone HTML / Drive 配布用)。

使い方:
    python -m scraper.build_map path/to/poi.json
    # 省略時は scraper/data/tateyama_poi.json を読む
出力: data/report/tateyama_map.html
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_POI = os.path.join(ROOT, "scraper", "data", "tateyama_poi.json")
OUT_HTML = os.path.join(ROOT, "data", "report", "tateyama_map.html")

# レイヤー定義: key, 表示名, 絵文字ピン色(CSS), デフォルト表示
LAYERS = [
    ("sunset", "🌅 夕陽スポット", "#e8863b", True),
    ("cafe", "☕ カフェ", "#8b5e3c", False),
    ("convenience", "🏪 コンビニ", "#2f8f4e", False),
    ("supermarket", "🛒 スーパー", "#c0392b", False),
    ("landmark", "📍 ランドマーク", "#2c6fb0", True),
]


def load_poi(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build(poi):
    center = poi.get("center") or {"lat": 34.996, "lng": 139.87, "label": "館山駅"}
    layers_js = []
    controls = []
    for key, label, color, default_on in LAYERS:
        pts = poi.get(key) or []
        markers = []
        for p in pts:
            lat = p.get("lat")
            lng = p.get("lng")
            if lat is None or lng is None:
                continue
            name = json.dumps(p.get("name", ""), ensure_ascii=False)
            note = json.dumps(p.get("note", ""), ensure_ascii=False)
            markers.append(
                f"pin({lat},{lng},{name},{note},{json.dumps(color)},{json.dumps(label)})"
            )
        arr = ",\n      ".join(markers)
        var = f"layer_{key}"
        layers_js.append(
            f"  const {var} = L.layerGroup([\n      {arr}\n  ]);"
        )
        controls.append((var, label, default_on, len(pts)))

    add_default = "\n".join(
        f"  {var}.addTo(map);" for var, _l, on, _n in controls if on
    )
    overlays = ",\n    ".join(
        f'"{label}<span class=cnt>{n}</span>": {var}' for var, label, _on, n in controls
    )

    return f"""<!doctype html><html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>館山 移住・運用マップ</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  html,body {{ margin:0; height:100%; font-family:system-ui,-apple-system,"Hiragino Kaku Gothic ProN","Noto Sans JP",Meiryo,sans-serif; }}
  #map {{ position:absolute; inset:0; }}
  .title {{ position:absolute; z-index:1000; top:12px; left:12px; background:rgba(255,255,255,.92);
           padding:9px 14px; border-radius:10px; box-shadow:0 2px 10px rgba(0,0,0,.18); }}
  .title h1 {{ margin:0; font-size:15px; }}
  .title p {{ margin:2px 0 0; font-size:11px; color:#556; }}
  .pin-emoji {{ font-size:20px; line-height:20px; text-align:center; filter:drop-shadow(0 1px 1px rgba(0,0,0,.4)); }}
  .leaflet-popup-content {{ font-size:13px; }}
  .leaflet-popup-content b {{ font-size:13.5px; }}
  .cnt {{ display:inline-block; margin-left:5px; color:#888; font-size:11px; }}
  .leaflet-control-layers {{ font-size:13px; }}
</style></head>
<body>
<div class="title"><h1>🏖 館山 移住・運用マップ</h1>
<p>右上のレイヤーで表示切替(夕陽 / カフェ / コンビニ / スーパー / ランドマーク)</p></div>
<div id="map"></div>
<script>
  const map = L.map('map', {{ center:[{center['lat']},{center['lng']}], zoom:13 }});
  L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
    maxZoom:19, attribution:'&copy; OpenStreetMap'
  }}).addTo(map);

  function pin(lat,lng,name,note,color,cat) {{
    const icon = L.divIcon({{
      className:'', html:'<div class="pin-emoji">'+catEmoji(cat)+'</div>',
      iconSize:[22,22], iconAnchor:[11,11]
    }});
    const m = L.marker([lat,lng], {{icon}});
    m.bindPopup('<b>'+name+'</b>'+(note?'<br>'+note:'')+
      '<br><a href="https://www.google.com/maps/search/?api=1&query='+lat+','+lng+
      '" target="_blank" rel="noopener">Googleマップで開く</a>');
    return m;
  }}
  function catEmoji(cat) {{
    if (cat.indexOf('夕陽')>=0) return '🌅';
    if (cat.indexOf('カフェ')>=0) return '☕';
    if (cat.indexOf('コンビニ')>=0) return '🏪';
    if (cat.indexOf('スーパー')>=0) return '🛒';
    return '📍';
  }}

{chr(10).join(layers_js)}

{add_default}

  const overlays = {{
    {overlays}
  }};
  L.control.layers(null, overlays, {{collapsed:false}}).addTo(map);
</script>
</body></html>"""


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_POI
    poi = load_poi(path)
    os.makedirs(os.path.dirname(OUT_HTML), exist_ok=True)
    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(build(poi))
    n = sum(len(poi.get(k) or []) for k, *_ in LAYERS)
    print("map:", OUT_HTML, f"({n} POI)")


if __name__ == "__main__":
    main()
