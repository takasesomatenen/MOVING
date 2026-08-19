# -*- coding: utf-8 -*-
"""design/spec.json から CG設計ベースのレポート HTML（図面SVG付き）を生成する。

    python -m design.make_hut_page      # data/report/hut.html を書き出す
"""

import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SPEC = os.path.join(HERE, "spec.json")
OUT = os.path.join(ROOT, "data", "report", "hut.html")


def load():
    with open(SPEC, encoding="utf-8") as fh:
        return json.load(fh)


# ------------------------------------------------------------------ SVG 部品

class Draw:
    """左下原点・メートル指定で描き、SVG座標（左上原点・px）に変換する。"""

    def __init__(self, x0, y0, x1, y1, scale, pad=26):
        self.x0, self.y0, self.x1, self.y1 = x0, y0, x1, y1
        self.s, self.pad = scale, pad
        self.w = (x1 - x0) * scale + pad * 2
        self.h = (y1 - y0) * scale + pad * 2
        self.parts = []

    def px(self, x):
        return self.pad + (x - self.x0) * self.s

    def py(self, y):
        return self.pad + (self.y1 - y) * self.s

    def rect(self, x0, y0, x1, y1, cls="", extra=""):
        a, b = self.px(x0), self.py(y1)
        return self.add(f'<rect x="{a:.1f}" y="{b:.1f}" width="{(x1-x0)*self.s:.1f}" '
                        f'height="{(y1-y0)*self.s:.1f}" class="{cls}" {extra}/>')

    def line(self, x0, y0, x1, y1, cls="", extra=""):
        return self.add(f'<line x1="{self.px(x0):.1f}" y1="{self.py(y0):.1f}" '
                        f'x2="{self.px(x1):.1f}" y2="{self.py(y1):.1f}" class="{cls}" {extra}/>')

    def poly(self, pts, cls="", extra=""):
        d = " ".join(f"{self.px(x):.1f},{self.py(y):.1f}" for x, y in pts)
        return self.add(f'<polygon points="{d}" class="{cls}" {extra}/>')

    def circle(self, x, y, r_px, cls="", extra=""):
        return self.add(f'<circle cx="{self.px(x):.1f}" cy="{self.py(y):.1f}" r="{r_px}" '
                        f'class="{cls}" {extra}/>')

    def text(self, x, y, s, cls="lbl", dx=0, dy=0, anchor="middle"):
        return self.add(f'<text x="{self.px(x)+dx:.1f}" y="{self.py(y)+dy:.1f}" '
                        f'text-anchor="{anchor}" class="{cls}">{s}</text>')

    def dim_h(self, x0, x1, y, label):
        """水平寸法線。"""
        self.line(x0, y, x1, y, "dim")
        for x in (x0, x1):
            self.add(f'<line x1="{self.px(x):.1f}" y1="{self.py(y)-4:.1f}" '
                     f'x2="{self.px(x):.1f}" y2="{self.py(y)+4:.1f}" class="dim"/>')
        return self.text((x0 + x1) / 2, y, label, "dimlbl", dy=-5)

    def dim_v(self, y0, y1, x, label):
        self.line(x, y0, x, y1, "dim")
        for y in (y0, y1):
            self.add(f'<line x1="{self.px(x)-4:.1f}" y1="{self.py(y):.1f}" '
                     f'x2="{self.px(x)+4:.1f}" y2="{self.py(y):.1f}" class="dim"/>')
        return self.add(f'<text x="{self.px(x)-6:.1f}" y="{self.py((y0+y1)/2):.1f}" '
                        f'text-anchor="middle" class="dimlbl" '
                        f'transform="rotate(-90 {self.px(x)-6:.1f} {self.py((y0+y1)/2):.1f})">{label}</text>')

    def add(self, s):
        self.parts.append(s)
        return self

    def svg(self, title, defs=""):
        body = "\n  ".join(self.parts)
        return (f'<figure class="dwg"><svg viewBox="0 0 {self.w:.0f} {self.h:.0f}" '
                f'style="color:var(--ink)" role="img" aria-label="{title}">{defs}\n  {body}\n</svg>'
                f'<figcaption>{title}</figcaption></figure>')


# ------------------------------------------------------------------ 各図面

def site_plan(sp):
    site, hut, deck, shed, hs = sp["site"], sp["hut"], sp["deck"], sp["shed"], sp["hardscape"]
    W, D = site["width_x"], site["depth_y"]
    d = Draw(-1.5, -1.5, W + 1.5, D + site["road"]["width"] + 0.5, 20)

    # 道路
    d.rect(-1.5, D, W + 1.5, D + site["road"]["width"], "road")
    d.text(W / 2, D + site["road"]["width"] / 2, "別荘地内道路 W=4.0m（砂利）", "lbl", dy=3)

    # 等高線（0.25m ごと）
    z = 0.25
    while z < D * site["slope"]:
        y = z / site["slope"]
        d.line(0, y, W, y, "contour")
        d.text(W - 0.15, y, f"+{z:.2f}", "tiny", dy=-3, anchor="end")
        z += 0.25

    # 敷地
    d.rect(0, 0, W, D, "site")

    # 駐車・アプローチ
    p = hs["parking"]
    d.rect(p["x0"], p["y0"], p["x1"], p["y1"], "gravel")
    d.text((p["x0"] + p["x1"]) / 2, (p["y0"] + p["y1"]) / 2, "駐車 5.5×4.5", "lbl", dy=3)
    half = hs["approach"]["width"] / 2
    pts = hs["approach"]["polyline"]
    for i in range(len(pts) - 1):
        (ax, ay), (bx, by) = pts[i], pts[i + 1]
        if abs(ax - bx) < 1e-6:
            d.rect(ax - half, min(ay, by), ax + half, max(ay, by), "gravel")
        else:
            d.rect(min(ax, bx), ay - half, max(ax, bx), ay + half, "gravel")

    # 軒の出
    ov = hut["overhang"]
    d.rect(hut["x0"] - ov["west"], hut["y0"] - ov["south"],
           hut["x1"] + ov["east"], hut["y1"] + ov["north"], "eave")
    # デッキ・主屋・別棟
    d.rect(deck["x0"], deck["y0"], deck["x1"], deck["y1"], "deck")
    d.text((deck["x0"] + deck["x1"]) / 2, (deck["y0"] + deck["y1"]) / 2, "デッキ 19.9㎡", "lbl", dy=3)
    d.rect(hut["x0"], hut["y0"], hut["x1"], hut["y1"], "bldg")
    d.text((hut["x0"] + hut["x1"]) / 2, (hut["y0"] + hut["y1"]) / 2 + 0.5, "主屋 39.7㎡", "lbl b", dy=3)
    d.text((hut["x0"] + hut["x1"]) / 2, (hut["y0"] + hut["y1"]) / 2 - 0.5, "7.28 × 5.46", "tiny", dy=3)
    d.rect(shed["x0"], shed["y0"], shed["x1"], shed["y1"], "bldg2")
    d.text((shed["x0"] + shed["x1"]) / 2, (shed["y0"] + shed["y1"]) / 2, "薪小屋 5.0㎡", "tiny", dy=3)

    # 樹木
    for x, y, h in sp["vegetation"]["trees"]:
        d.circle(x, y, max(3.5, h * 0.34), "tree")

    # 方位と眺望
    d.line(W + 0.75, D - 3.2, W + 0.75, D - 1.2, "arrow", 'marker-end="url(#ah)"')
    d.text(W + 0.75, D - 0.9, "N", "b", dy=0)
    av = math.radians(sp["view"]["azimuth_deg"])
    cx, cy = (hut["x0"] + hut["x1"]) / 2, hut["y0"]
    d.line(cx, cy, cx + 5.2 * math.sin(av), cy + 5.2 * math.cos(av), "view", 'marker-end="url(#ah2)"')
    d.text(cx + 2.6 * math.sin(av) - 1.5, cy + 2.6 * math.cos(av), "浅間山 203°", "tiny", dy=12)

    # 寸法
    d.dim_h(0, W, -0.85, "14.00 m")
    d.dim_v(0, D, -0.85, "19.50 m")
    return d.svg("配置図 ― 敷地 14.0×19.5m / 北→南 5%下り / 等高線0.25m", defs=DEFS)


def hut_plan(sp):
    hut, deck = sp["hut"], sp["deck"]
    ov = hut["overhang"]
    d = Draw(hut["x0"] - ov["west"] - 0.9, deck["y0"] - 0.9,
             hut["x1"] + ov["east"] + 0.9, hut["y1"] + ov["north"] + 0.9, 42)

    # 910グリッド
    x = hut["x0"]
    while x <= hut["x1"] + 1e-6:
        d.line(x, hut["y0"], x, hut["y1"], "grid")
        x += 0.91
    y = hut["y0"]
    while y <= hut["y1"] + 1e-6:
        d.line(hut["x0"], y, hut["x1"], y, "grid")
        y += 0.91

    d.rect(hut["x0"] - ov["west"], hut["y0"] - ov["south"],
           hut["x1"] + ov["east"], hut["y1"] + ov["north"], "eave")
    d.rect(deck["x0"], deck["y0"], deck["x1"], deck["y1"], "deck")
    d.rect(hut["x0"], hut["y0"], hut["x1"], hut["y1"], "bldg")

    # 開口（平面に落ちるもの）
    t = 0.16
    for o in hut["openings"]:
        if o["wall"] == "south":
            d.rect(o["u0"], hut["y0"] - t / 2, o["u1"], hut["y0"] + t / 2, "open")
        elif o["wall"] == "north":
            d.rect(o["u0"], hut["y1"] - t / 2, o["u1"], hut["y1"] + t / 2, "open")
        elif o["wall"] == "west":
            d.rect(hut["x0"] - t / 2, o["u0"], hut["x0"] + t / 2, o["u1"], "open")
        else:
            d.rect(hut["x1"] - t / 2, o["u0"], hut["x1"] + t / 2, o["u1"], "open")
        d.text({"south": (o["u0"] + o["u1"]) / 2, "north": (o["u0"] + o["u1"]) / 2,
                "west": hut["x0"] - 0.55, "east": hut["x1"] + 0.55}[o["wall"]],
               {"south": hut["y0"] - 0.42, "north": hut["y1"] + 0.30,
                "west": (o["u0"] + o["u1"]) / 2, "east": (o["u0"] + o["u1"]) / 2}[o["wall"]],
               o["id"], "tiny", dy=3)

    # 独立基礎
    for x in sp["foundation"]["grid_x"]:
        for y in sp["foundation"]["grid_y"]:
            d.circle(x, y, 3.4, "pier")

    st = hut["stove"]
    d.rect(st["x"] - 0.3, st["y"] - 0.25, st["x"] + 0.3, st["y"] + 0.25, "fix")
    d.text(st["x"], st["y"] - 0.55, "薪ストーブ", "tiny", dy=3)
    wb = hut["washbasin"]
    d.rect(wb["x0"], wb["y0"], wb["x1"], wb["y1"], "fix")
    d.text((wb["x0"] + wb["x1"]) / 2 + 0.15, wb["y0"] - 0.28, "中古洗面ボウル", "tiny", dy=3)

    d.dim_h(hut["x0"], hut["x1"], hut["y1"] + ov["north"] + 0.55, "7,280（8P）")
    d.dim_v(hut["y0"], hut["y1"], hut["x0"] - ov["west"] - 0.55, "5,460（6P）")
    d.dim_v(deck["y0"], deck["y1"], hut["x1"] + ov["east"] + 0.55, "2,730")
    return d.svg("平面図 ― 910グリッド / 独立基礎20基 / FL=GL+1,050")


def section_ns(sp):
    hut = sp["hut"]
    ov, fl, p = hut["overhang"], hut["fl"], hut["roof_pitch"]
    ry0, ry1 = hut["y0"] - ov["south"], hut["y1"] + ov["north"]

    def rz(y):
        return hut["eave_z_south"] + (y - hut["y0"]) * p

    d = Draw(sp["deck"]["y0"] - 0.9, -1.6, ry1 + 1.5, 6.9, 40)

    # 地盤
    gy0, gy1 = sp["deck"]["y0"] - 0.9, ry1 + 1.5
    d.poly([(gy0, sp["site"]["slope"] * gy0), (gy1, sp["site"]["slope"] * gy1),
            (gy1, -1.6), (gy0, -1.6)], "ground")

    # 屋根
    th = 0.22
    d.poly([(ry0, rz(ry0)), (ry1, rz(ry1)), (ry1, rz(ry1) + th), (ry0, rz(ry0) + th)], "roofsec")
    # 壁と床
    d.rect(hut["y0"], fl, hut["y0"] + 0.14, rz(hut["y0"]), "wallsec")
    d.rect(hut["y1"] - 0.14, fl, hut["y1"], rz(hut["y1"]), "wallsec")
    d.rect(hut["y0"], fl - 0.25, hut["y1"], fl, "wallsec")
    d.rect(sp["deck"]["y0"], fl - 0.05, hut["y0"], fl, "decksec")

    # 開口（南の掃き出し・北の窓）
    d.rect(hut["y0"], fl, hut["y0"] + 0.14, fl + 2.00, "opensec")
    d.rect(hut["y1"] - 0.14, 2.05, hut["y1"], 2.95, "opensec")

    # 独立基礎
    for y in sp["foundation"]["grid_y"]:
        gz = sp["site"]["slope"] * y
        d.rect(y - 0.15, gz - 1.0, y + 0.15, fl - 0.45, "piersec")

    # 冬至・夏至の南中光線（南軒先から）
    for alt, cls, lab in ((30.0, "raywin", "冬至 南中 30.0°"), (76.9, "raysum", "夏至 南中 76.9°")):
        x0, z0 = ry0, rz(ry0) + th
        dz = math.tan(math.radians(alt))
        # 北向き（+y）に進むと下がる
        yend = x0 + (z0 - (-0.2)) / dz
        yend = min(yend, hut["y1"])
        d.line(x0, z0, yend, z0 - (yend - x0) * dz, cls)
        d.text(x0 + 0.12, z0 + 0.62 if alt > 60 else z0 + 0.12, lab, "tiny", dy=0, anchor="start")

    d.dim_v(fl, rz(hut["y0"]), sp["deck"]["y0"] - 0.45, "2,400")
    d.dim_v(fl, rz(hut["y1"]), ry1 + 1.05, "4,311")
    d.text((hut["y0"] + hut["y1"]) / 2, rz((hut["y0"] + hut["y1"]) / 2) + 0.55,
           "片流れ 3.5寸（19.3°）", "tiny", dy=0)
    d.text(hut["y0"] - 0.45, fl + 0.28, "FL +1.050", "tiny", dy=0, anchor="end")
    return d.svg("断面図（南北）― 南が低い片流れ。軒の出900mmで夏の日射を切り、冬は床奥まで入れる")


def elevation_south(sp):
    hut = sp["hut"]
    ov, fl, p = hut["overhang"], hut["fl"], hut["roof_pitch"]
    rx0, rx1 = hut["x0"] - ov["west"], hut["x1"] + ov["east"]
    zs = hut["roof_edge_z_south"]
    d = Draw(rx0 - 0.8, -0.55, rx1 + 0.8, 4.3, 42)

    gz = sp["site"]["slope"] * hut["y0"]                 # 南壁位置の地盤高 +0.30
    for i, x in enumerate(sp["foundation"]["grid_x"]):
        d.rect(x - 0.15, gz - 0.55, x + 0.15, fl - 0.45, "piersec")
    d.rect(hut["x0"], fl - 0.45, hut["x1"], fl, "wallsec")   # 土台＋床組
    d.poly([(rx0 - 0.8, gz), (rx1 + 0.8, gz), (rx1 + 0.8, -0.55), (rx0 - 0.8, -0.55)], "ground")
    d.text(rx0 - 0.55, gz + 0.10, "GL +0.30", "tiny", dy=0, anchor="start")
    d.rect(rx0, zs, rx1, zs + 0.22, "roofsec")           # 軒先小口
    d.rect(hut["x0"], fl, hut["x1"], zs, "wallsec")      # 壁
    d.rect(sp["deck"]["x0"], fl - 0.05, sp["deck"]["x1"], fl, "decksec")
    for o in hut["openings"]:
        if o["wall"] == "south":
            d.rect(o["u0"], o["z0"], o["u1"], o["z1"], "opensec")
            d.text((o["u0"] + o["u1"]) / 2, (o["z0"] + o["z1"]) / 2,
                   "掃き出し 5,460×2,000", "tiny", dy=3)
    d.dim_h(rx0, rx1, -0.55, "8,480（軒の出込み）")
    d.text(rx1 + 0.42, zs + 0.11, "+3.135", "tiny", dy=3, anchor="start")
    return d.svg("南立面 ― 焼杉（黒）の壁にガルバの軒。南面は6P分をまるごと開口")


# ------------------------------------------------------------------ ページ

CSS = """
:root{ --bg:#eef4f5; --surface:#ffffff; --surface2:#f5fafb; --ink:#0f2a33; --sub:#5f7681;
  --line:#d5e3e6; --accent:#0d7c94; --gold:#b8862b; --warm:#c9821f;
  --shadow:0 1px 2px rgba(15,42,51,.05),0 8px 22px rgba(15,42,51,.06); }
@media (prefers-color-scheme:dark){ :root:not([data-theme="light"]){
  --bg:#081115; --surface:#11222a; --surface2:#0d1c22; --ink:#e7f1f3; --sub:#8ea6ad;
  --line:#20353c; --accent:#3bb6cc; --gold:#d7a94b; --warm:#e2a24e;
  --shadow:0 1px 2px rgba(0,0,0,.3),0 10px 26px rgba(0,0,0,.4); }}
:root[data-theme="dark"]{ --bg:#081115; --surface:#11222a; --surface2:#0d1c22; --ink:#e7f1f3;
  --sub:#8ea6ad; --line:#20353c; --accent:#3bb6cc; --gold:#d7a94b; --warm:#e2a24e;
  --shadow:0 1px 2px rgba(0,0,0,.3),0 10px 26px rgba(0,0,0,.4); }
*{ box-sizing:border-box; margin:0; padding:0; }
body{ font-family:system-ui,-apple-system,"Hiragino Kaku Gothic ProN","Noto Sans JP",Meiryo,sans-serif;
  background:var(--bg); color:var(--ink); line-height:1.65; -webkit-font-smoothing:antialiased;
  padding:26px 16px 72px; }
.wrap{ max-width:900px; margin:0 auto; }
a.back{ font-size:12px; color:var(--accent); text-decoration:none; font-weight:700; }
.eyebrow{ font-size:11px; letter-spacing:.2em; font-weight:700; color:var(--accent);
  text-transform:uppercase; margin-top:12px; }
h1{ font-size:25px; margin:5px 0 6px; letter-spacing:.01em; }
.lead{ font-size:12.5px; color:var(--sub); line-height:1.75; }
section{ background:var(--surface); border:1px solid var(--line); border-radius:16px;
  padding:17px 17px 18px; margin-top:16px; box-shadow:var(--shadow); }
h2{ font-size:15px; margin-bottom:4px; }
.subh{ font-size:11.5px; color:var(--sub); margin-bottom:12px; }
table{ width:100%; border-collapse:collapse; font-size:12px; margin-top:6px; }
th,td{ text-align:left; padding:6px 8px; border-bottom:1px solid var(--line); vertical-align:top; }
th{ color:var(--sub); font-size:10.5px; font-weight:700; letter-spacing:.04em; white-space:nowrap; }
td.n{ text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; }
code{ font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:11.5px;
  background:var(--surface2); border:1px solid var(--line); border-radius:5px; padding:1px 5px; }
pre{ background:var(--surface2); border:1px solid var(--line); border-radius:10px; padding:11px 13px;
  overflow-x:auto; font-size:11.5px; line-height:1.7; margin-top:8px; }
pre code{ background:none; border:none; padding:0; }
.sw{ display:inline-block; width:13px; height:13px; border-radius:3px; border:1px solid var(--line);
  vertical-align:-2px; margin-right:6px; }
.dwg{ margin:10px 0 2px; }
.dwg svg{ width:100%; height:auto; display:block; background:var(--surface2);
  border:1px solid var(--line); border-radius:12px; }
.dwg figcaption{ font-size:10.5px; color:var(--sub); margin-top:6px; line-height:1.6; }
svg text{ font-family:system-ui,-apple-system,"Hiragino Kaku Gothic ProN",sans-serif;
  fill:var(--ink); font-size:9.5px; }
svg text.tiny{ font-size:8px; fill:var(--sub); }
svg text.b{ font-weight:700; }
svg text.dimlbl{ font-size:8.5px; fill:var(--accent); font-weight:700; }
svg .site{ fill:none; stroke:var(--ink); stroke-width:1.6; }
svg .road{ fill:var(--line); stroke:none; opacity:.55; }
svg .contour{ stroke:var(--sub); stroke-width:.5; stroke-dasharray:4 4; opacity:.55; }
svg .gravel{ fill:var(--sub); opacity:.28; stroke:var(--sub); stroke-width:.5; }
svg .eave{ fill:none; stroke:var(--sub); stroke-width:.8; stroke-dasharray:5 3; }
svg .deck{ fill:var(--warm); opacity:.30; stroke:var(--warm); stroke-width:.8; }
svg .bldg{ fill:var(--accent); opacity:.34; stroke:var(--accent); stroke-width:1.5; }
svg .bldg2{ fill:var(--accent); opacity:.18; stroke:var(--accent); stroke-width:1; }
svg .tree{ fill:#4a7a48; opacity:.30; stroke:#4a7a48; stroke-width:.5; }
svg .grid{ stroke:var(--accent); stroke-width:.4; opacity:.30; }
svg .open{ fill:var(--surface); stroke:var(--accent); stroke-width:1.4; }
svg .pier{ fill:none; stroke:var(--ink); stroke-width:.9; }
svg .fix{ fill:var(--sub); opacity:.35; stroke:var(--sub); stroke-width:.6; }
svg .ground{ fill:var(--sub); opacity:.22; stroke:var(--sub); stroke-width:.8; }
svg .roofsec{ fill:var(--sub); opacity:.55; stroke:var(--ink); stroke-width:1; }
svg .wallsec{ fill:var(--accent); opacity:.40; stroke:var(--accent); stroke-width:1.2; }
svg .decksec{ fill:var(--warm); opacity:.45; stroke:var(--warm); stroke-width:1; }
svg .opensec{ fill:#7fd4e8; opacity:.45; stroke:var(--accent); stroke-width:1.1; }
svg .piersec{ fill:var(--sub); opacity:.45; stroke:var(--sub); stroke-width:.7; }
svg .raywin{ stroke:var(--gold); stroke-width:1.2; stroke-dasharray:6 3; }
svg .raysum{ stroke:var(--accent); stroke-width:1.2; stroke-dasharray:2 3; }
svg .dim{ stroke:var(--accent); stroke-width:.8; }
svg .arrow{ stroke:var(--ink); stroke-width:1.4; }
svg .view{ stroke:var(--gold); stroke-width:1.3; stroke-dasharray:7 4; }
.note{ font-size:11.5px; color:var(--sub); margin-top:10px; line-height:1.75; }
.foot{ font-size:11px; color:var(--sub); text-align:center; margin-top:22px; line-height:1.8; }
"""

DEFS = ('<defs>'
        '<marker id="ah" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" '
        'orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="currentColor"/></marker>'
        '<marker id="ah2" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" '
        'orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#b8862b"/></marker>'
        '</defs>')


def rows(pairs):
    return "\n".join(f'<tr><th>{k}</th><td>{v}</td></tr>' for k, v in pairs)


def build(sp):
    site, hut, view = sp["site"], sp["hut"], sp["view"]

    site_rows = rows([
        ("想定地", site["address_assumed"]),
        ("敷地", f'{site["width_x"]} × {site["depth_y"]} m ＝ <b>{site["area_m2"]}㎡</b>（{site["area_tsubo"]}坪）'),
        ("標高 / 緯度", f'{site["base_elevation_m"]} m ／ {site["latitude"]}°N {site["longitude"]}°E'),
        ("地形", site["slope_note"]),
        ("接道", f'北側・{site["road"]["surface"]} W={site["road"]["width"]}m'),
        ("地盤", site["ground"]),
        ("凍結深度 / 積雪", f'想定 {site["frost_depth_m"]} m ／ 設計 {site["design_snow_m"]} m'),
        ("眺望", f'{view["target"]}：方位 {view["azimuth_deg"]}°・{view["distance_km"]}km・'
                 f'見かけの仰角 {view["apparent_altitude_deg"]}°'),
        ("植生", f'{sp["vegetation"]["dominant"]}／{sp["vegetation"]["secondary"]}／'
                 f'下草 {sp["vegetation"]["understory"]}'),
    ])

    bldg_rows = rows([
        ("構法", hut["structure"]),
        ("平面", f'{hut["span_x"]} × {hut["span_y"]} m ＝ <b>{hut["area_m2"]}㎡</b>（{hut["area_tsubo"]}坪）'),
        ("床高 FL", f'GL+1,050（絶対 Z=+{hut["fl"]} m）'),
        ("屋根", f'{hut["roof_type"]}・勾配 3.5寸（{hut["roof_pitch_deg"]}°）'),
        ("軒高", f'南 Z+{hut["eave_z_south"]} → 北 Z+{hut["ridge_z_north_wall"]:.3f}'),
        ("軒先高", f'南 Z+{hut["roof_edge_z_south"]} ／ 北 Z+{hut["roof_edge_z_north"]}'),
        ("軒の出", f'南 {hut["overhang"]["south"]*1000:.0f} ／ 北 {hut["overhang"]["north"]*1000:.0f} ／ '
                   f'東西 {hut["overhang"]["east"]*1000:.0f} mm'),
        ("天井", hut["ceiling"]),
        ("基礎", f'{sp["foundation"]["type"]} {sp["foundation"]["count"]}基・'
                 f'根入れ {sp["foundation"]["embed_depth"]}m（{sp["foundation"]["note"].split("。")[0]}）'),
        ("架構", " ／ ".join(sp["frame"].values())),
        ("デッキ", f'{sp["deck"]["area_m2"]}㎡・FLと同レベル・{sp["deck"]["material"]}'),
        ("別棟", f'{sp["shed"]["name"]} {sp["shed"]["area_m2"]}㎡（{sp["shed"]["note"]}）'),
        ("便所", hut["toilet"]),
    ])

    op_rows = "\n".join(
        f'<tr><td><b>{o["id"]}</b></td><td>{ {"south":"南","north":"北","east":"東","west":"西"}[o["wall"]] }</td>'
        f'<td class="n">{(o["u1"]-o["u0"])*1000:,.0f}</td><td class="n">{(o["z1"]-o["z0"])*1000:,.0f}</td>'
        f'<td class="n">+{o["z0"]:.2f}</td><td>{o["kind"]}</td></tr>'
        for o in hut["openings"])

    mat_rows = "\n".join(
        f'<tr><th>{k}</th><td><span class="sw" style="background:{m.get("srgb","#888")}"></span>'
        f'{m["spec"]}</td><td class="n">{m.get("srgb","—")}</td>'
        f'<td class="n">{m.get("roughness","—")}</td></tr>'
        for k, m in sp["materials"].items())

    sun_rows = "\n".join(
        f'<tr><td><code>{p["id"]}</code></td><td>{p["label"]}</td>'
        f'<td class="n">{p["azimuth_deg"]}°</td><td class="n">{p["altitude_deg"]}°</td>'
        f'<td class="n">{p["kelvin"]} K</td></tr>' for p in sp["sun_presets"])

    cam_rows = "\n".join(
        f'<tr><td><code>{c["id"]}</code></td><td>{c["label"]}</td>'
        f'<td class="n">{c["loc"][0]}, {c["loc"][1]}, {c["loc"][2]}</td>'
        f'<td class="n">{c["target"][0]}, {c["target"][1]}, {c["target"][2]}</td>'
        f'<td class="n">{c["lens"]}mm</td><td><code>{c["sun"]}</code></td></tr>'
        for c in sp["cameras"])

    reuse_rows = rows([
        ("再生砕石", "解体ブロック塀を割ったもの。駐車 24.8㎡＋アプローチ＋雨落ち帯の全面。"
                     "構造には一切使わない（凍上で持ち上がるため）"),
        ("中古の陶器洗面ボウル", "北西の窓下に古材カウンターで据える。再利用材の中で唯一そのまま使える衛生陶器"),
        ("石膏ボード", "新築現場の端材 t12.5 を内装下地に。継ぎ目をパテ埋めせず素地現し＋クリアで"
                       "<b>ランダムな目地割りをそのまま意匠にする</b>。CG内観の主題"),
        ("中古グラスウール", "主屋には使わず<b>別棟の薪小屋</b>へ。寒冷地の居室断熱は建物寿命に直結するため賭けない"),
        ("足場板・古材", "デッキ床 t35／内部床 t30／洗面カウンター。色ムラをテクスチャの素材にする"),
        ("中古アルミサッシ", "北面の小窓2つ・西面1つ。南面の主開口だけは新規のペアガラスにして断熱の芯を通す"),
    ])

    html = f"""<!doctype html><html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>北軽井沢 セルフビルド小屋 ― CG設計ベース</title>
<style>{CSS}</style></head>
<body><div class="wrap">
<a class="back" href="home.html">← レポートハブ</a>
<div class="eyebrow">MOVING ・ DESIGN BASE FOR CG</div>
<h1>🏔 北軽井沢 セルフビルド小屋 ― CG設計ベース</h1>
<div class="lead">実現性の検証ではなく、<b>CGで起こすために寸法・方位・地形・光を全部固定した版</b>。
座標系は右手系メートル、原点＝敷地南西隅のGL±0、+X=東 / +Y=真北 / +Z=上でBlender標準と一致する。
数値の単一の情報源は <code>design/spec.json</code>、この頁とBlenderスクリプトはどちらもそこから生成・参照する。</div>

<section>
  <h2>① 敷地</h2>
  <div class="subh">実在の分譲事例（274㎡／100万円帯）を下敷きにした想定区画。地形は北軽井沢の緩傾斜地として単純化した</div>
  {site_plan(sp)}
  <table>{site_rows}</table>
  <div class="note">南に向かって下る地形なので、南の大開口＝浅間方向＝下り方向が揃う。
  地盤高は <code>z = 0.05 × y</code> の一次式なので、CG側は平面を1枚傾けるだけで再現できる。</div>
</section>

<section>
  <h2>② 建物</h2>
  <div class="subh">平屋・延べ39.7㎡。910mmグリッドに全部載せてあるので、部材も再利用材の割付けもグリッドで拾える</div>
  {hut_plan(sp)}
  {section_ns(sp)}
  {elevation_south(sp)}
  <table>{bldg_rows}</table>
</section>

<section>
  <h2>③ 開口</h2>
  <div class="subh">u は壁に沿った座標（南北面ならX、東西面ならY）。z は絶対高さ</div>
  <table>
    <tr><th>ID</th><th>面</th><th>幅 mm</th><th>高 mm</th><th>下端 Z</th><th>仕様</th></tr>
    {op_rows}
  </table>
</section>

<section>
  <h2>④ 再利用材をどこに落とすか</h2>
  <div class="subh">「もらってくれるならあげる」側の材料を、CG上で意味が出る位置に割り当てた</div>
  <table>{reuse_rows}</table>
</section>

<section>
  <h2>⑤ 材料パレット（PBR用）</h2>
  <div class="subh">Base Color は sRGB。Blenderスクリプト側でリニア変換して Principled BSDF に入る</div>
  <table>
    <tr><th>キー</th><th>仕様</th><th>sRGB</th><th>Rough</th></tr>
    {mat_rows}
  </table>
</section>

<section>
  <h2>⑥ 光環境</h2>
  <div class="subh">{sp["solar_note"]}</div>
  <table>
    <tr><th>ID</th><th>条件</th><th>方位角</th><th>高度</th><th>色温度</th></tr>
    {sun_rows}
  </table>
  <div class="note">方位角は真北から時計回り。Blenderの Sun は
  <code>rotation_euler = (radians(90 − alt), 0, radians(180 − az))</code> で一致する。
  カラマツは落葉針葉樹なので、冬カットでは樹冠を落として幹だけにすると光の入り方が実際に近づく
  （<code>--winter</code> オプション）。</div>
</section>

<section>
  <h2>⑦ カメラ</h2>
  <div class="subh">4カットぶんの位置・注視点・画角。各カットに既定の太陽プリセットを紐づけてある</div>
  <table>
    <tr><th>ID</th><th>カット</th><th>位置 (x,y,z)</th><th>注視点</th><th>画角</th><th>太陽</th></tr>
    {cam_rows}
  </table>
</section>

<section>
  <h2>⑧ 立てかた</h2>
  <div class="subh">spec.json を読んでマッシングを丸ごと生成する。地形・敷地境界・基礎・軸組・屋根・デッキ・別棟・砕石・樹木・太陽・カメラまで入る</div>
<pre><code># GUIで開いて確認する
blender --python design/blender_hut.py

# 冬（カラマツ落葉）で開く
blender --python design/blender_hut.py -- --winter

# 4カットまとめて書き出す
blender --background --python design/blender_hut.py -- out/</code></pre>
  <div class="note">寸法を変えたいときは <code>design/spec.json</code> だけを触る。
  この頁は <code>python -m design.make_hut_page</code> で作り直せるので、図面とモデルがずれない。</div>
</section>

<div class="foot">寸法・方位・光はすべて設計上の仮定値。<br>
敷地は実在の分譲事例を下敷きにした想定区画であり、特定の物件を指すものではない。</div>
</div></body></html>
"""
    return html


def main():
    sp = load()
    html = build(sp)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(html)
    print(f"wrote {OUT}  ({len(html):,} bytes)")


if __name__ == "__main__":
    main()
