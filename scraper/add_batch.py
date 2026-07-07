"""複数物件を JSON 一括で master CSV に追記する。

WebSearch 由来の「館山に似た立地」物件など、まとまった件数を安全に取り込む用途。
入力 JSON は物件オブジェクトの配列:
  [{"title","price_man","location","land_m2","building_m2","madori","url","note",
    "source"?,"coastal"?}, ...]
掲載元がリストページ URL を共有していても衝突しないよう、URL にタイトル由来の
フラグメントを付けて id を一意化する(リンク先は同じページを開く)。

使い方:
    python -m scraper.add_batch path/to/listings.json [--source websearch-similar] [--today YYYY-MM-DD]
"""

import argparse
import datetime as dt
import hashlib
import json
import os

from .store import Listing, load_master, merge, write_master

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MASTER_PATH = os.path.join(ROOT, "data", "listings_master.csv")


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _unique_url(url, title):
    """同一リストページ URL でも物件ごとに一意化(#フラグメント)。"""
    if not url:
        return url
    if "#" in url:
        return url
    slug = hashlib.sha1(title.encode("utf-8")).hexdigest()[:8]
    return f"{url}#{slug}"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("json_path")
    ap.add_argument("--source", default="websearch-similar")
    ap.add_argument("--today", default=None)
    args = ap.parse_args(argv)

    today = args.today or dt.date.today().isoformat()
    with open(args.json_path, encoding="utf-8") as f:
        rows = json.load(f)

    listings = []
    for r in rows:
        title = (r.get("title") or "").strip()
        if not title:
            continue
        listings.append(Listing(
            source=r.get("source") or args.source,
            title=title[:120],
            url=_unique_url(r.get("url") or "", title),
            price_man=_f(r.get("price_man")),
            location=(r.get("location") or "")[:60],
            land_m2=_f(r.get("land_m2")),
            building_m2=_f(r.get("building_m2")),
            madori=r.get("madori") or "",
            coastal=bool(r.get("coastal", True)),
            note=r.get("note") or "WebSearch由来 現物・在庫・価格は掲載元で要確認",
        ))

    master = load_master(MASTER_PATH)
    before = len(master)
    master, new_count = merge(master, listings, today)
    write_master(MASTER_PATH, master)
    print(f"追加: 入力{len(listings)}件 / 新規{new_count}件 / master {before}→{len(master)}件")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
