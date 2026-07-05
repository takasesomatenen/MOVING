"""master CSV から海沿い格安物件レポート(HTML)を生成する。

render.py で PNG/PDF 化してスクショ検証する前提。日本語は IPAGothic。
"""

import csv
import datetime as dt
import html
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MASTER_PATH = os.path.join(ROOT, "data", "listings_master.csv")
OUT_HTML = os.path.join(ROOT, "data", "report", "index.html")


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def load_rows(path=MASTER_PATH):
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            r["_price"] = _f(r.get("price_man"))
            r["_bld"] = _f(r.get("building_m2"))
            r["_land"] = _f(r.get("land_m2"))
            r["_unit"] = round(r["_price"] / r["_bld"], 2) if (r["_price"] and r["_bld"]) else None
            rows.append(r)
    return rows


def _fmt(v, suffix=""):
    if v is None or v == "":
        return "—"
    if isinstance(v, float):
        v = int(v) if v.is_integer() else round(v, 2)
    return f"{v}{suffix}"


def build_html(rows, today):
    priced = [r for r in rows if r["_price"] is not None]
    with_bld = [r for r in rows if r["_bld"]]
    cheapest = min(priced, key=lambda r: r["_price"]) if priced else None
    # 3枚が別物件になるよう、最安に選ばれた行は他ピックから除外する。
    cheap_id = cheapest["id"] if cheapest else None
    biggest = max([r for r in with_bld if r["id"] != cheap_id], key=lambda r: r["_bld"],
                  default=None)
    big_id = biggest["id"] if biggest else None
    used = {cheap_id, big_id}
    # 建物単価が割安(=お買い得)。最安・一番広い と重複しないものから選ぶ。
    best_unit = min([r for r in with_bld if r["_unit"] and r["id"] not in used],
                    key=lambda r: r["_unit"], default=None)
    avg_price = round(sum(r["_price"] for r in priced) / len(priced)) if priced else 0
    units = [r["_unit"] for r in with_bld if r["_unit"]]
    avg_unit = round(sum(units) / len(units), 1) if units else 0

    def card(label, r, color):
        if not r:
            return ""
        return f"""
        <div class="pick" style="--accent:{color}">
          <div class="pick-label">{label}</div>
          <div class="pick-price">{_fmt(r['_price'])}<span>万円</span></div>
          <div class="pick-title">{html.escape(r['title'])}</div>
          <div class="pick-meta">
            <span>📍 {html.escape(r['location'])}</span>
            <span>🏠 建物 {_fmt(r['_bld'],'㎡')}</span>
            <span>🌏 土地 {_fmt(r['_land'],'㎡')}</span>
            <span>🚪 {html.escape(r['madori'] or '—')}</span>
            {f'<span>💴 {r["_unit"]}万/㎡</span>' if r['_unit'] else ''}
          </div>
        </div>"""

    trs = []
    for i, r in enumerate(sorted(priced, key=lambda r: r["_price"]), 1):
        sea = "🌊" if r.get("coastal") == "1" else ""
        unit = f"{r['_unit']}" if r["_unit"] else "—"
        trs.append(f"""<tr>
          <td class="rank">{i}</td>
          <td class="price">{_fmt(r['_price'])}<span>万</span></td>
          <td class="loc">{sea} {html.escape(r['location'])}</td>
          <td>{_fmt(r['_bld'],'㎡')}</td>
          <td>{_fmt(r['_land'],'㎡')}</td>
          <td>{html.escape(r['madori'] or '—')}</td>
          <td class="unit">{unit}</td>
          <td class="note">{html.escape(r['title'])}</td>
        </tr>""")

    return f"""<!doctype html><html lang="ja"><head><meta charset="utf-8">
<title>海沿い格安物件レポート {today}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: "IPAGothic","Noto Sans JP",sans-serif; color:#0f2733;
         background:#eef4f6; -webkit-font-smoothing:antialiased; }}
  .wrap {{ width: 900px; margin: 0 auto; padding: 40px 44px 60px; background:#fff; }}
  header {{ border-bottom: 4px solid #0d7c94; padding-bottom: 20px; margin-bottom: 26px; }}
  .kicker {{ color:#0d7c94; font-weight:700; letter-spacing:.18em; font-size:13px; }}
  h1 {{ font-size: 32px; line-height:1.25; margin: 6px 0 4px; }}
  .sub {{ color:#5b7079; font-size: 14px; }}
  .stats {{ display:flex; gap:14px; margin: 22px 0 30px; }}
  .stat {{ flex:1; background:#f2f8f9; border:1px solid #d9e7ea; border-radius:12px;
          padding:14px 16px; }}
  .stat .n {{ font-size:26px; font-weight:800; color:#0d7c94; }}
  .stat .l {{ font-size:12px; color:#5b7079; margin-top:2px; }}
  h2 {{ font-size:19px; margin: 30px 0 14px; padding-left:11px;
        border-left:6px solid #0d7c94; }}
  .picks {{ display:flex; gap:14px; }}
  .pick {{ flex:1; border:1px solid #e0e9ec; border-top:5px solid var(--accent);
          border-radius:12px; padding:16px; background:#fff; }}
  .pick-label {{ font-size:12px; font-weight:700; color:var(--accent); }}
  .pick-price {{ font-size:30px; font-weight:800; margin:4px 0 6px; }}
  .pick-price span {{ font-size:14px; font-weight:600; color:#5b7079; }}
  .pick-title {{ font-size:13px; font-weight:700; margin-bottom:8px; min-height:36px; }}
  .pick-meta {{ display:flex; flex-wrap:wrap; gap:6px; font-size:11.5px; color:#3a5560; }}
  .pick-meta span {{ background:#f2f8f9; border-radius:6px; padding:3px 7px; }}
  table {{ width:100%; border-collapse:collapse; font-size:13px; margin-top:6px; }}
  thead th {{ background:#0d7c94; color:#fff; padding:9px 8px; text-align:left;
             font-size:12px; }}
  tbody td {{ padding:8px; border-bottom:1px solid #eaf1f3; vertical-align:top; }}
  tbody tr:nth-child(even) {{ background:#f7fbfc; }}
  td.rank {{ color:#9bb0b8; font-weight:700; width:26px; }}
  td.price {{ font-weight:800; color:#0d7c94; white-space:nowrap; }}
  td.price span {{ font-size:10px; color:#5b7079; }}
  td.loc {{ font-weight:600; }}
  td.unit {{ color:#c2570a; font-weight:700; }}
  td.note {{ color:#5b7079; font-size:12px; }}
  .cost {{ display:flex; gap:14px; }}
  .cost .box {{ flex:1; background:#f2f8f9; border:1px solid #d9e7ea;
              border-radius:12px; padding:16px 18px; }}
  .cost .box h3 {{ font-size:14px; color:#0d7c94; margin-bottom:8px; }}
  .cost .row {{ display:flex; justify-content:space-between; font-size:13px;
              padding:4px 0; border-bottom:1px dashed #d5e4e7; }}
  .cost .row.total {{ border-bottom:none; font-weight:800; font-size:15px;
                     color:#0f2733; padding-top:8px; }}
  .tips {{ display:flex; gap:14px; margin-top:12px; }}
  .tip {{ flex:1; background:#fff; border:1px solid #e0e9ec; border-radius:12px;
         padding:14px 16px; font-size:12.5px; line-height:1.6; }}
  .tip b {{ color:#0d7c94; }}
  .foot {{ margin-top:30px; padding-top:16px; border-top:1px solid #e0e9ec;
          font-size:11px; color:#8a9aa1; line-height:1.7; }}
  .legend {{ font-size:11px; color:#5b7079; margin-top:6px; }}
</style></head>
<body><div class="wrap">
  <header>
    <div class="kicker">SEASIDE HOUSE FINDER ・ 海沿い格安物件</div>
    <h1>海沿い・田舎の激安物件レポート</h1>
    <div class="sub">条件: 海沿い / 土地＋上物 〜300万円 / 多少ボロOK / 上物は面積(㎡)付き　—　{today} 時点</div>
  </header>

  <div class="stats">
    <div class="stat"><div class="n">{len(rows)}<span style="font-size:14px">件</span></div><div class="l">掲載物件(海沿い&le;300万)</div></div>
    <div class="stat"><div class="n">{_fmt(cheapest['_price']) if cheapest else '—'}<span style="font-size:14px">万</span></div><div class="l">最安値</div></div>
    <div class="stat"><div class="n">{avg_price}<span style="font-size:14px">万</span></div><div class="l">平均価格</div></div>
    <div class="stat"><div class="n">{avg_unit}<span style="font-size:14px">万/㎡</span></div><div class="l">平均 建物単価</div></div>
  </div>

  <h2>ベスト・ピック</h2>
  <div class="picks">
    {card("💰 最安", cheapest, "#0d7c94")}
    {card("⭐ 建物が割安", best_unit, "#c2570a")}
    {card("🏡 一番広い", biggest, "#2a8a5f")}
  </div>

  <h2>全物件ランキング（価格の安い順）</h2>
  <table>
    <thead><tr>
      <th>#</th><th>価格</th><th>所在地</th><th>建物</th><th>土地</th>
      <th>間取り</th><th>万/㎡</th><th>物件</th>
    </tr></thead>
    <tbody>{''.join(trs)}</tbody>
  </table>
  <div class="legend">🌊=海沿い判定あり　／　万/㎡=建物延床の単価(価格÷建物面積)　／　—=データ未取得</div>

  <h2>総額のリアル（取得＋リノベ）</h2>
  <div class="cost">
    <div class="box">
      <h3>ミニマム再生プラン（例：200万物件）</h3>
      <div class="row"><span>物件取得</span><b>200万</b></div>
      <div class="row"><span>諸費用(登記・仲介 等)</span><b>+30万</b></div>
      <div class="row"><span>最低限リノベ(水回り・屋根)</span><b>+150万</b></div>
      <div class="row total"><span>総額</span><b>約 380万円</b></div>
    </div>
    <div class="box">
      <h3>しっかり再生プラン（例：300万物件）</h3>
      <div class="row"><span>物件取得</span><b>300万</b></div>
      <div class="row"><span>諸費用</span><b>+40万</b></div>
      <div class="row"><span>フルリノベ</span><b>+450万</b></div>
      <div class="row total"><span>総額</span><b>約 790万円</b></div>
    </div>
    <div class="box">
      <h3>月々ローン目安(35年・金利1.5%)</h3>
      <div class="row"><span>総額 380万 → 月々</span><b>約 1.2万</b></div>
      <div class="row"><span>総額 790万 → 月々</span><b>約 2.4万</b></div>
      <div class="row"><span>参考: 都市の新築</span><b>月 8〜10万</b></div>
      <div class="row total"><span>海沿い田舎の強み</span><b>桁が違う</b></div>
    </div>
  </div>

  <h2>掘り出し物の探し方（川上へ遡る）</h2>
  <div class="tips">
    <div class="tip"><b>① 空き家バンク</b><br>アットホーム/LIFULL の空き家バンク。0円〜格安＋自治体の補助金。海タグ(btag)で海沿い抽出。</div>
    <div class="tip"><b>② 地場の不動産屋に直接</b><br>南房総なら地元業者へ週末に挨拶。未公開物件を握っている。「探してます」と言い続けるのが効く。</div>
    <div class="tip"><b>③ 2段階移住</b><br>いきなり買わず、狙う町にまず賃貸で仮住まい。地元とつながってから買うのが失敗しない王道。</div>
  </div>

  <div class="foot">
    ※ 本レポートの物件は WebSearch 由来の第1・2弾シードを含み、価格・在庫・面積は掲載元での一次確認が必要です。<br>
    ※ 毎日 GitHub Actions が海沿い&le;300万物件を収集し、この表と Google Drive へ自動反映されます。<br>
    自動収集フォルダ: 「海沿い格安物件 デイリースクレイプ」(Google Drive)
  </div>
</div></body></html>"""


def main():
    rows = load_rows()
    today = dt.date.today().isoformat()
    os.makedirs(os.path.dirname(OUT_HTML), exist_ok=True)
    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(build_html(rows, today))
    print("report:", OUT_HTML, f"({len(rows)}件)")


if __name__ == "__main__":
    main()
