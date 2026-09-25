"""master の各物件に 海距離(m)/海見え/車道 を推定して埋める(バックフィル)。

タイトル+備考のテキストから filters の推定関数で補完する。既に値が入って
いる行は上書きしない(手入力・掲載元由来を尊重)。正確値は現地/掲載元で要確認。

    python -m scraper.enrich
"""

import os

from .filters import parse_sea_distance_m, infer_sea_view, infer_road_access
from .store import load_master, write_master

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MASTER_PATH = os.path.join(ROOT, "data", "listings_master.csv")


def enrich_row(r: dict) -> bool:
    """1行を推定補完。変更があれば True。"""
    text = f"{r.get('title','')} {r.get('note','')}"
    changed = False
    if not r.get("sea_dist_m"):
        d = parse_sea_distance_m(text)
        if d is not None:
            r["sea_dist_m"] = d
            changed = True
    if not r.get("sea_view"):
        v = infer_sea_view(text)
        r["sea_view"] = v
        changed = True
    if not r.get("road_access"):
        a = infer_road_access(text)
        r["road_access"] = a
        changed = True
    return changed


def main():
    master = load_master(MASTER_PATH)
    n = 0
    for r in master.values():
        if enrich_row(r):
            n += 1
    write_master(MASTER_PATH, master)
    with_dist = sum(1 for r in master.values() if r.get("sea_dist_m"))
    with_view = sum(1 for r in master.values() if r.get("sea_view") not in ("", "—"))
    print(f"enrich: {n}行更新 / 距離あり{with_dist}件 / 海見え判定{with_view}件 / 計{len(master)}件")


if __name__ == "__main__":
    main()
