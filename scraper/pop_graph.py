"""人口動態グラフ(全国・千葉県・館山市・高齢化率)を inline SVG で生成。

外部依存なし → Artifact でも PDF レンダリング(chromium)でもそのまま表示可。
data/report/population.html を出力。数値ソースは research_population.md 準拠
(総務省人口推計/住民基本台帳/千葉県常住人口調査/館山市人口ビジョン/社人研)。
"""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "report", "population.html")

# --- データ(実測。推計は点線で別扱い) ---
NATION = [(2015, 127095), (2021, 125502), (2022, 124947), (2023, 124352), (2024, 123802)]  # 千人
CHIBA = [(2020, 6284.3), (2021, 6281.3), (2022, 6278.4), (2023, 6275.5), (2025, 6273.7)]   # 千人
TATE = [(1950, 59424), (2015, 47464), (2020, 45153), (2024, 44040)]                          # 人(実測)
TATE_EST = [(2024, 44040), (2050, 31000)]                                                     # 推計
AGING = [(2023, 29.1), (2024, 29.3), (2025, 29.4)]        # 全国 高齢化率 %
AGING_TATE = [(2020, 40.0), (2024, 40.4), (2040, 45.6)]   # 館山 高齢化率 %(2040推計)


def _line_chart(series, w=520, h=260, pad=44, color="#0d7c94", est=None,
                ymin=None, ymax=None, fmt=lambda v: f"{v:,.0f}", title=""):
    xs = [x for x, _ in series] + ([x for x, _ in (est or [])])
    ys = [y for _, y in series] + ([y for _, y in (est or [])])
    x0, x1 = min(xs), max(xs)
    y0 = ymin if ymin is not None else min(ys)
    y1 = ymax if ymax is not None else max(ys)
    if y1 == y0:
        y1 = y0 + 1
    if x1 == x0:
        x1 = x0 + 1

    def px(x):
        return pad + (x - x0) / (x1 - x0) * (w - pad - 14)

    def py(y):
        return h - pad - (y - y0) / (y1 - y0) * (h - pad - 24)

    # grid + y labels
    grid = []
    for i in range(5):
        yy = y0 + (y1 - y0) * i / 4
        gy = py(yy)
        grid.append(f'<line x1="{pad}" y1="{gy:.1f}" x2="{w-14}" y2="{gy:.1f}" class="grid"/>')
        grid.append(f'<text x="{pad-6}" y="{gy+3:.1f}" class="ylab">{fmt(yy)}</text>')
    # x labels
    xlab = []
    for x, _ in series + (est or []):
        xlab.append(f'<text x="{px(x):.1f}" y="{h-pad+16}" class="xlab">{x}</text>')
    # solid path
    pts = " ".join(f"{px(x):.1f},{py(y):.1f}" for x, y in series)
    dots = "".join(
        f'<circle cx="{px(x):.1f}" cy="{py(y):.1f}" r="3.2" fill="{color}"/>'
        for x, y in series
    )
    est_svg = ""
    if est:
        epts = " ".join(f"{px(x):.1f},{py(y):.1f}" for x, y in est)
        est_svg = (
            f'<polyline points="{epts}" fill="none" stroke="{color}" '
            f'stroke-width="2.2" stroke-dasharray="6 5" opacity=".7"/>'
            + "".join(f'<circle cx="{px(x):.1f}" cy="{py(y):.1f}" r="3" '
                      f'fill="none" stroke="{color}" stroke-width="1.6"/>' for x, y in est)
        )
    return f"""<figure class="chart">
  <figcaption>{title}</figcaption>
  <svg viewBox="0 0 {w} {h}" role="img">
    {''.join(grid)}
    <polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2.6"/>
    {est_svg}{dots}
    {''.join(xlab)}
  </svg>
</figure>"""


def build():
    c1 = _line_chart(NATION, color="#0d7c94", ymin=120000, ymax=128000,
                     fmt=lambda v: f"{v/1000:.1f}千万".replace("千万", "億") if v >= 100000 else f"{v:,.0f}",
                     title="全国 総人口(千人) ― 2015→2024で14年連続減")
    c1 = _line_chart(NATION, color="#0d7c94", ymin=120000, ymax=128000,
                     fmt=lambda v: f"{v/10000:.2f}億", title="全国 総人口 ― 14年連続減(2024=1.238億)")
    c2 = _line_chart(CHIBA, color="#2c6fb0", ymin=6270, ymax=6286,
                     fmt=lambda v: f"{v/1000:.3f}百万".replace("百万", "M") if False else f"{v:,.0f}千",
                     title="千葉県 総人口(千人) ― 社会増を自然減が相殺し微減")
    c3 = _line_chart(TATE, color="#c0392b", est=None, ymin=30000, ymax=60000,
                     title="館山市 総人口(実測) ― 1950ピーク5.9万→2024=4.4万")
    c3b = _line_chart(TATE[1:], color="#c0392b", est=TATE_EST, ymin=28000, ymax=48000,
                      title="館山市 人口 実測+2050推計(点線) ― 2020比▲約30%")
    c4 = _line_chart(AGING, color="#e8863b", ymin=28, ymax=47,
                     fmt=lambda v: f"{v:.0f}%", title="高齢化率 全国 ― 2024=29.3%(過去最高)")
    c4b = _line_chart(AGING_TATE, color="#b8531f", est=None, ymin=28, ymax=47,
                      fmt=lambda v: f"{v:.0f}%",
                      title="館山市 高齢化率 ― 2024=40.4%→2040推計45.6%(全国+11pt先行)")

    return f"""<!doctype html><html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>人口動態ダッシュボード ― 全国 / 関東 / 館山</title>
<style>
  :root {{ --bg:#f3f7f8; --card:#fff; --ink:#12303b; --sub:#5b727c; --line:#e2ebee; }}
  @media (prefers-color-scheme:dark) {{ :root {{ --bg:#0d1619; --card:#15242a; --ink:#e8f1f3; --sub:#94a9af; --line:#243940; }} }}
  :root[data-theme="light"] {{ --bg:#f3f7f8; --card:#fff; --ink:#12303b; --sub:#5b727c; --line:#e2ebee; }}
  :root[data-theme="dark"] {{ --bg:#0d1619; --card:#15242a; --ink:#e8f1f3; --sub:#94a9af; --line:#243940; }}
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ font-family:system-ui,-apple-system,"Hiragino Kaku Gothic ProN","Noto Sans JP",Meiryo,sans-serif;
         background:var(--bg); color:var(--ink); padding:30px 20px 60px; -webkit-font-smoothing:antialiased; }}
  .wrap {{ max-width:1160px; margin:0 auto; }}
  .kick {{ color:#0d7c94; font-weight:700; letter-spacing:.16em; font-size:12px; }}
  h1 {{ font-size:25px; margin:4px 0 4px; }}
  .sub {{ color:var(--sub); font-size:13px; margin-bottom:22px; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(340px,1fr)); gap:18px; }}
  .chart {{ background:var(--card); border:1px solid var(--line); border-radius:14px; padding:14px 12px 8px; }}
  .chart figcaption {{ font-size:13px; font-weight:700; margin:2px 6px 8px; }}
  svg {{ width:100%; height:auto; }}
  .grid line.grid {{ stroke:var(--line); stroke-width:1; }}
  .grid {{}}
  line.grid {{ stroke:var(--line); stroke-width:1; }}
  text.ylab {{ fill:var(--sub); font-size:9.5px; text-anchor:end; }}
  text.xlab {{ fill:var(--sub); font-size:10px; text-anchor:middle; }}
  .note {{ font-size:11px; color:var(--sub); line-height:1.8; margin-top:20px; }}
  .kpis {{ display:flex; flex-wrap:wrap; gap:12px; margin:6px 0 22px; }}
  .kpi {{ background:var(--card); border:1px solid var(--line); border-radius:12px; padding:12px 16px; }}
  .kpi b {{ font-size:22px; }} .kpi span {{ display:block; font-size:11px; color:var(--sub); }}
</style></head>
<body><div class="wrap">
  <div class="kick">POPULATION DASHBOARD ・ 全国 / 関東 / 館山</div>
  <h1>人口動態ダッシュボード</h1>
  <div class="sub">出所: 総務省 人口推計2024 ・ 住民基本台帳人口移動報告2024 ・ 千葉県 毎月常住人口調査 ・ 館山市 人口ビジョン ・ 社人研2023推計。点線=推計。</div>
  <div class="kpis">
    <div class="kpi"><b>▲55万</b><span>全国 24年 前年減(14年連続)</span></div>
    <div class="kpi"><b>29.3%</b><span>全国 高齢化率(過去最高)</span></div>
    <div class="kpi"><b>+13.6万</b><span>東京圏 転入超過(一極集中)</span></div>
    <div class="kpi"><b>40.4%</b><span>館山 高齢化率(全国+11pt)</span></div>
    <div class="kpi"><b>▲30%</b><span>館山 人口 2020→2050推計</span></div>
  </div>
  <div class="grid">
    {c1}{c2}{c3}{c3b}{c4}{c4b}
  </div>
  <div class="note">
    ● 全国は14年連続の自然減(2024年 出生71.7万＜死亡160.7万)。社会増(+34万)はほぼ外国人流入によるもので、日本人は▲2千の社会減。<br>
    ● 関東は「東京都＋埼玉」への一極集中が継続。千葉県は転入超過(+7,859人/全国3位規模の社会増)を維持するが、自然減が上回り総人口は微減局面。<br>
    ● 館山市(南房総)は千葉県内で最も高齢化・人口減が進む。高齢化率40.4%は全国29.3%を約11ポイント上回り、全国より10〜15年先行。<br>
    ● 示唆: 需要(移住・二拠点)より供給(空き家)が構造的に増える地域 → 買い手・借り手には価格交渉余地。一方で生活インフラ縮小リスクは織り込む必要。<br>
    ※ 2040/2050年値は社人研等の推計(推定)。基準時点が資料により異なるため各系列の年次を明記。
  </div>
</div></body></html>"""


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(build())
    print("population:", OUT)


if __name__ == "__main__":
    main()
