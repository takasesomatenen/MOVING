"""master から「海沿い物件レポート」PDF を軽量生成(reportlab)。

CIDフォント(HeiseiKakuGo-W5, 非埋め込み)を使うため日本語でもファイルが小さく、
Google Drive へ base64 で載せられる(数十KB)。横A4・価格昇順の一覧表。

    python -m scraper.pdf_report            # -> data/report/report_light.pdf
    python -m scraper.pdf_report out.pdf
"""

import csv
import datetime as dt
import os
import sys

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle, Paragraph,
                                Spacer)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MASTER_PATH = os.path.join(ROOT, "data", "listings_master.csv")
OUT = os.path.join(ROOT, "data", "report", "report_light.pdf")

FONT = "HeiseiKakuGo-W5"
pdfmetrics.registerFont(UnicodeCIDFont(FONT))

HEAD = ["物件名", "価格(万)", "所在地", "土地㎡", "建物㎡", "間取り",
        "万/㎡", "海まで(m)", "海見", "車道"]
WIDTHS = [188, 40, 132, 42, 42, 44, 40, 50, 30, 30]


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _n(v):
    x = _f(v)
    return "" if x is None else (str(int(x)) if x == int(x) else str(round(x, 2)))


def load_rows():
    rows = []
    with open(MASTER_PATH, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    rows.sort(key=lambda r: (_f(r.get("price_man")) or 1e9))
    return rows


def build(path):
    rows = load_rows()
    today = dt.date.today().isoformat()
    priced = [r for r in rows if _f(r.get("price_man")) is not None]
    cheapest = int(min((_f(r["price_man"]) for r in priced), default=0))

    cell = ParagraphStyle("cell", fontName=FONT, fontSize=6.8, leading=8.2)
    cellc = ParagraphStyle("cellc", parent=cell, alignment=1)
    cellr = ParagraphStyle("cellr", parent=cell, alignment=2)
    headst = ParagraphStyle("head", fontName=FONT, fontSize=6.8, leading=8.2,
                            alignment=1, textColor=colors.white)
    h1 = ParagraphStyle("h1", fontName=FONT, fontSize=15, leading=18)
    sub = ParagraphStyle("sub", fontName=FONT, fontSize=8, leading=11,
                         textColor=colors.HexColor("#556"))

    def P(t, st=cell):
        return Paragraph((t or "").replace("&", "&amp;").replace("<", "&lt;"), st)

    data = [[P(h, headst) for h in HEAD]]
    for r in rows:
        p, b = _f(r.get("price_man")), _f(r.get("building_m2"))
        unit = round(p / b, 2) if (p and b) else None
        data.append([
            P(r.get("title", "")),
            P(_n(r.get("price_man")), cellr),
            P(r.get("location", "")),
            P(_n(r.get("land_m2")), cellr),
            P(_n(r.get("building_m2")), cellr),
            P(r.get("madori", ""), cellc),
            P("" if unit is None else str(unit), cellr),
            P(r.get("sea_dist_m", ""), cellr),
            P(r.get("sea_view", ""), cellc),
            P(r.get("road_access", ""), cellc),
        ])

    t = Table(data, colWidths=WIDTHS, repeatRows=1)
    style = [
        ("FONTNAME", (0, 0), (-1, -1), FONT),
        ("FONTSIZE", (0, 0), (-1, -1), 6.8),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0d7c94")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c9dade")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]
    for i in range(1, len(data)):
        if i % 2 == 0:
            style.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#f2f8f9")))
    t.setStyle(TableStyle(style))

    doc = SimpleDocTemplate(path, pagesize=landscape(A4),
                            leftMargin=14 * mm, rightMargin=14 * mm,
                            topMargin=12 * mm, bottomMargin=12 * mm,
                            title="海沿い物件レポート")
    story = [
        Paragraph("海沿い物件レポート", h1),
        Paragraph(f"{len(rows)}件 ・ 最安 {cheapest}万円 ・ {today}　"
                  "／ 海まで(m): ≈は徒歩分80m換算等の概算　"
                  "／ 海見: ◎ｵｰｼｬﾝﾋﾞｭｰ ○高台 △堤防越し —不明　"
                  "／ 車道: ○駐車接道 △狭/私道 ✕不可 —不明　"
                  "（価格・面積・距離・眺望・接道は要現地/掲載元確認）", sub),
        Spacer(1, 6),
        t,
    ]
    doc.build(story)
    return path


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else OUT
    os.makedirs(os.path.dirname(out), exist_ok=True)
    build(out)
    print("pdf:", out, f"({os.path.getsize(out)} bytes)")


if __name__ == "__main__":
    main()
