"""海沿い格安物件を各サイトから収集し、master/日次 CSV に保存する。

使い方:
    python -m scraper.scrape --price-cap 300

GitHub Actions から毎日実行される想定。ネットワークがオープンな環境が必要
(このリポジトリの開発用サンドボックスは外部サイトを遮断しているため、
 Actions ランナー上で動かすこと)。
"""

import argparse
import datetime as dt
import os
import sys

from .sources import SOURCES, make_session, scrape_source
from .store import load_master, merge, write_master, write_csv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MASTER_PATH = os.path.join(ROOT, "data", "listings_master.csv")
DAILY_DIR = os.path.join(ROOT, "data", "daily")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--price-cap", type=float, default=300.0,
                    help="価格上限(万円)。これを超える物件は除外。既定300。")
    ap.add_argument("--today", default=None, help="日付上書き(YYYY-MM-DD)")
    args = ap.parse_args(argv)

    today = args.today or dt.date.today().isoformat()
    logs = []
    def log(msg):
        print(msg, flush=True)
        logs.append(msg)

    log(f"=== 海沿い格安物件スクレイプ {today} (price_cap={args.price_cap}万) ===")

    session = make_session()
    all_listings = []
    for src in SOURCES:
        if not src.get("enabled", True):
            log(f"[source] {src['name']} (無効化: bot/403のためスキップ)")
            continue
        log(f"[source] {src['name']}")
        try:
            found = scrape_source(src, session, args.price_cap, log)
        except Exception as e:  # noqa: BLE001
            log(f"  [!!] source crashed: {e}")
            found = []
        log(f"  => {len(found)} 件(海沿い & <= {args.price_cap}万)")
        all_listings.extend(found)

    master = load_master(MASTER_PATH)
    before = len(master)
    master, new_count = merge(master, all_listings, today)
    write_master(MASTER_PATH, master)

    # 日次スナップショット(その日に見つかった件のみ)
    daily_rows = [lst.to_row() for lst in all_listings]
    for r in daily_rows:
        r["coastal"] = "1" if r.get("coastal") else "0"
    os.makedirs(DAILY_DIR, exist_ok=True)
    daily_path = os.path.join(DAILY_DIR, f"{today}.csv")
    write_csv(daily_path, daily_rows)

    log(f"--- 完了: 収集{len(all_listings)}件 / 新規{new_count}件 / "
        f"master {before}->{len(master)}件 ---")
    log(f"master: {MASTER_PATH}")
    log(f"daily : {daily_path}")

    # スクレイプが全滅(0件)でも異常終了はしない(サイト側ブロックの可能性)。
    return 0


if __name__ == "__main__":
    sys.exit(main())
