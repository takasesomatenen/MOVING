"""master から「海沿い物件レポート」= ヘッダークリックでソートできる表を生成。

data/report/table.html を出力。数値列(価格・面積・海まで距離・万/㎡)は
ヘッダクリックで昇順/降順ソート。セルは内容に応じた最小幅(nowrap)、
備考のみ折り返し。テーマ対応。外部依存なし(JSは同梱)。
"""

import csv
import datetime as dt
import html
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MASTER_PATH = os.path.join(ROOT, "data", "listings_master.csv")
OUT = os.path.join(ROOT, "data", "report", "table.html")

# (見出し, キー, 型)  型: num=数値ソート, text=文字列ソート
COLS = [
    ("物件名", "title", "text"),
    ("価格(万)", "price_man", "num"),
    ("所在地", "location", "text"),
    ("土地㎡", "land_m2", "num"),
    ("建物㎡", "building_m2", "num"),
    ("間取り", "madori", "text"),
    ("万/㎡", "_unit", "num"),
    ("海まで(m)", "sea_dist_m", "num"),
    ("海見え", "sea_view", "text"),
    ("車道", "road_access", "text"),
    ("備考", "note", "text"),
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
            p, b = _f(r.get("price_man")), _f(r.get("building_m2"))
            r["_unit"] = round(p / b, 2) if (p and b) else None
            rows.append(r)
    rows.sort(key=lambda r: (_f(r.get("price_man")) or 1e9))
    return rows


def _sortval(r, key, typ):
    """data-sort 用の数値。距離の ≈ は除去して数値化。空は末尾へ。"""
    if typ != "num":
        return ""
    raw = r.get(key)
    if key == "_unit":
        raw = r.get("_unit")
    if raw in (None, ""):
        return 1e18
    s = str(raw).replace("≈", "").replace(",", "")
    try:
        return float(s)
    except ValueError:
        return 1e18


def _disp(r, key):
    if key == "_unit":
        v = r.get("_unit")
        return "" if v is None else (f"{v}")
    v = r.get(key, "")
    return "" if v in (None, "None") else str(v)


def cell(r, key, typ):
    if key == "title":
        url = html.escape((r.get("url") or "").split("#")[0])
        t = html.escape(_disp(r, key))
        link = f'<a href="{url}" target="_blank" rel="noopener">{t}</a>' if url else t
        return f'<td class="ttl">{link}</td>'
    val = html.escape(_disp(r, key))
    cls = "note" if key == "note" else ("num" if typ == "num" else "")
    if key == "sea_view":
        cls = "mark"
    if key == "road_access":
        cls = "mark"
    sv = _sortval(r, key, typ)
    dattr = f' data-sort="{sv}"' if typ == "num" else f' data-sort="{val}"'
    return f'<td class="{cls}"{dattr}>{val}</td>'


def build(rows, today):
    priced = [r for r in rows if _f(r.get("price_man")) is not None]
    cheapest = min((_f(r["price_man"]) for r in priced), default=0)
    head = "".join(
        f'<th class="{ "num" if t=="num" else "" }" data-type="{t}" data-i="{i}">'
        f'<span>{html.escape(h)}</span><i class="ar"></i></th>'
        for i, (h, k, t) in enumerate(COLS)
    )
    body = "\n".join(
        "<tr>" + "".join(cell(r, k, t) for (_h, k, t) in COLS) + "</tr>"
        for r in rows
    )
    return f"""<!doctype html><html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>海沿い物件レポート</title>
<style>
  :root{{ --bg:#eef4f6; --card:#fff; --ink:#0f2733; --sub:#5b7079; --line:#dbe6ea;
         --accent:#0d7c94; --chip:#f1f8f9; --head:#e7f1f4; --zebra:#f7fbfc; }}
  @media (prefers-color-scheme:dark){{ :root{{ --bg:#0c1417; --card:#132025; --ink:#e7f0f2;
         --sub:#93a7ad; --line:#243a41; --accent:#3bb6cc; --chip:#182930; --head:#16282f; --zebra:#111d22; }} }}
  :root[data-theme="light"]{{ --bg:#eef4f6; --card:#fff; --ink:#0f2733; --sub:#5b7079; --line:#dbe6ea; --accent:#0d7c94; --chip:#f1f8f9; --head:#e7f1f4; --zebra:#f7fbfc; }}
  :root[data-theme="dark"]{{ --bg:#0c1417; --card:#132025; --ink:#e7f0f2; --sub:#93a7ad; --line:#243a41; --accent:#3bb6cc; --chip:#182930; --head:#16282f; --zebra:#111d22; }}
  *{{ box-sizing:border-box; margin:0; padding:0; }}
  body{{ font-family:system-ui,-apple-system,"Hiragino Kaku Gothic ProN","Noto Sans JP",Meiryo,sans-serif;
        background:var(--bg); color:var(--ink); -webkit-font-smoothing:antialiased; padding:22px 16px 60px; }}
  .head{{ max-width:1400px; margin:0 auto 14px; }}
  .kick{{ color:var(--accent); font-weight:700; letter-spacing:.16em; font-size:11px; }}
  h1{{ font-size:22px; margin:3px 0 4px; }}
  .sub{{ color:var(--sub); font-size:12.5px; }}
  .wrap{{ max-width:1400px; margin:0 auto; overflow-x:auto; border:1px solid var(--line); border-radius:12px; }}
  table{{ border-collapse:collapse; width:100%; font-size:12.5px; }}
  th,td{{ border-bottom:1px solid var(--line); border-right:1px solid var(--line);
         padding:7px 10px; white-space:nowrap; text-align:left; vertical-align:top; }}
  th:last-child,td:last-child{{ border-right:none; }}
  thead th{{ position:sticky; top:0; background:var(--head); cursor:pointer; user-select:none;
            font-weight:700; z-index:2; }}
  th.num,td.num{{ text-align:right; font-variant-numeric:tabular-nums; }}
  td.ttl a{{ color:var(--accent); text-decoration:none; font-weight:600; }}
  td.ttl a:hover{{ text-decoration:underline; }}
  td.mark{{ text-align:center; font-weight:700; }}
  td.note{{ white-space:normal; min-width:220px; max-width:320px; color:var(--sub); font-size:11.5px; line-height:1.5; }}
  tbody tr:nth-child(even){{ background:var(--zebra); }}
  tbody tr:hover{{ background:var(--chip); }}
  th .ar{{ display:inline-block; width:0; height:0; margin-left:5px; vertical-align:middle; opacity:.35;
          border-left:4px solid transparent; border-right:4px solid transparent; border-top:5px solid currentColor; }}
  th.asc .ar{{ opacity:.9; border-top:none; border-bottom:5px solid currentColor; }}
  th.desc .ar{{ opacity:.9; }}
  .legend{{ max-width:1400px; margin:12px auto 0; font-size:11px; color:var(--sub); line-height:1.8; }}
</style></head>
<body>
  <div class="head">
    <div class="kick">SEASIDE PROPERTY REPORT ・ 海沿い物件レポート</div>
    <h1>海沿い物件レポート</h1>
    <div class="sub">{len(rows)}件 ・ 最安 {int(cheapest)}万円 ・ {today} ・ 見出しをクリックで並べ替え(価格・面積・海までの距離など)</div>
  </div>
  <div class="wrap"><table id="t">
    <thead><tr>{head}</tr></thead>
    <tbody>
{body}
    </tbody>
  </table></div>
  <div class="legend">
    ● 物件名クリックで掲載元ページへ。海まで(m)=掲載文言からの抽出。<b>≈</b> は徒歩分(1分=80m換算)や「目の前」等からの<b>概算</b>。<br>
    ● 海見え: ◎=オーシャンビュー明記 / ○=高台・眺望 / △=堤防越し等 / —=不明(要現地確認)。 車道: ○=駐車・接道あり / △=軽自動車・私道等 / ✕=車進入不可 / —=不明(要確認)。<br>
    ● 価格・面積・制度・距離・眺望・接道はいずれも掲載元での一次確認が必要(シードはWebSearch由来、断定不可箇所は推定)。
  </div>
<script>
(function(){{
  var t=document.getElementById('t'), tb=t.tBodies[0];
  var ths=t.tHead.rows[0].cells;
  for(var i=0;i<ths.length;i++){{ (function(idx){{
    ths[idx].addEventListener('click',function(){{ sortBy(idx, ths[idx]); }});
  }})(i); }}
  var cur=-1, dir=1;
  function sortBy(idx, th){{
    var type=th.getAttribute('data-type');
    if(cur===idx){{ dir=-dir; }} else {{ dir=1; cur=idx; }}
    for(var j=0;j<ths.length;j++){{ ths[j].classList.remove('asc','desc'); }}
    th.classList.add(dir>0?'asc':'desc');
    var rows=[].slice.call(tb.rows);
    rows.sort(function(a,b){{
      var av=a.cells[idx].getAttribute('data-sort');
      var bv=b.cells[idx].getAttribute('data-sort');
      if(type==='num'){{ av=parseFloat(av); bv=parseFloat(bv); return (av-bv)*dir; }}
      return av.localeCompare(bv,'ja')*dir;
    }});
    var frag=document.createDocumentFragment();
    rows.forEach(function(r){{ frag.appendChild(r); }});
    tb.appendChild(frag);
  }}
}})();
</script>
</body></html>"""


def main():
    rows = load_rows()
    today = dt.date.today().isoformat()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(build(rows, today))
    print("table:", OUT, f"({len(rows)}件)")


if __name__ == "__main__":
    main()
