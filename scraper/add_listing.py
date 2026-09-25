"""1 物件を master CSV に安全に追記する CLI。

毎日の WebSearch 補強セッションが、CSV を直接編集して壊すのを防ぐための
決定的インターフェース。重複(URL)は自動排除、価格・面積のパースも共通ロジック。

例:
    python -m scraper.add_listing \
      --title "尾鷲市 海近 中古戸建" --price 250 --loc "三重県尾鷲市" \
      --building 88.5 --land 120 --madori 4DK \
      --url "https://example.com/bukken/123" --source websearch-daily
"""

import argparse
import datetime as dt
import os
import re

from .filters import (parse_price_man, normalize, TSUBO_TO_M2,
                      parse_sea_distance_m, infer_sea_view, infer_road_access)
from .store import Listing, load_master, merge, write_master

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MASTER_PATH = os.path.join(ROOT, "data", "listings_master.csv")

DEFAULT_NOTE = "WebSearch由来 現物・在庫・価格は掲載元で要確認"


def _num(v):
    """数値 or '250万'/'88.5㎡'/'30坪' のような文字列を float へ。"""
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        pass
    s = normalize(str(v))
    if "万" in s or "億" in s:
        return parse_price_man(s)
    m = re.search(r"(\d[\d,]*(?:\.\d+)?)", s)
    if not m:
        return None
    num = float(m.group(1).replace(",", ""))
    if "坪" in s:
        num = round(num * TSUBO_TO_M2, 2)
    return num


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", required=True)
    ap.add_argument("--url", required=True, help="重複排除キー。掲載元URL。")
    ap.add_argument("--price", help="価格(万円)。数値 or '250万'")
    ap.add_argument("--loc", default="", help="所在地")
    ap.add_argument("--building", help="建物面積(㎡)")
    ap.add_argument("--land", help="土地面積(㎡)")
    ap.add_argument("--madori", default="")
    ap.add_argument("--source", default="websearch-daily")
    ap.add_argument("--coastal", type=int, default=1, help="海沿い(1/0)")
    ap.add_argument("--note", default=DEFAULT_NOTE)
    ap.add_argument("--sea-dist", default=None, help="海までの距離(m)。未指定なら文言から推定")
    ap.add_argument("--sea-view", default=None, help="海見え ◎/○/△/—。未指定なら推定")
    ap.add_argument("--road", default=None, help="車道 ○/△/✕/—。未指定なら推定")
    ap.add_argument("--today", default=None)
    args = ap.parse_args(argv)

    today = args.today or dt.date.today().isoformat()
    _text = f"{args.title} {args.note}"
    lst = Listing(
        source=args.source,
        title=args.title[:120],
        url=args.url,
        price_man=_num(args.price),
        location=args.loc[:60],
        land_m2=_num(args.land),
        building_m2=_num(args.building),
        madori=args.madori,
        coastal=bool(args.coastal),
        sea_dist_m=args.sea_dist if args.sea_dist is not None else (parse_sea_distance_m(_text) or ""),
        sea_view=args.sea_view if args.sea_view is not None else infer_sea_view(_text),
        road_access=args.road if args.road is not None else infer_road_access(_text),
        note=args.note,
    )
    master = load_master(MASTER_PATH)
    existed = lst.id in master
    master, new_count = merge(master, [lst], today)
    write_master(MASTER_PATH, master)
    status = "更新(既存)" if existed else "新規追加"
    print(f"{status}: {lst.title} / {lst.price_man}万 / {lst.location} "
          f"-> master {len(master)}件 (新規{new_count})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
