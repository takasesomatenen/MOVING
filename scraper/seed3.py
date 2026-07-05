"""第3弾シード(WebSearch 由来の実在物件・2026-07 時点)。

瀬戸内(兵庫)・北海道(室蘭)へカバー拡大。海沿い≤300万・面積付き。
出所が検索サマリ由来のため現物・在庫の一次確認が必要(note に明記)。
"""

import os

from .store import Listing, load_master, merge, write_master

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MASTER_PATH = os.path.join(ROOT, "data", "listings_master.csv")

NOTE = "第3弾(WebSearch由来/2026-07) 現物・在庫要確認"

SEED = [
    Listing(source="websearch-seed", title="兵庫 姫路市網干区興浜 6DK 1969築 播磨灘",
            url="https://suumo.jp/chukoikkodate/hyogo/nj_175/#seed-17",
            price_man=200, location="兵庫県姫路市網干区興浜",
            land_m2=None, building_m2=164.75, madori="6DK", coastal=True, note=NOTE),
    Listing(source="websearch-seed", title="兵庫 たつの市 海近 広め 中古戸建",
            url="https://www.iju-style.jp/bukken/list#seed-18",
            price_man=200, location="兵庫県たつの市",
            land_m2=166.75, building_m2=123.32, madori="", coastal=True, note=NOTE),
    Listing(source="websearch-seed", title="北海道 室蘭市白鳥台 5LDK 海の街",
            url="https://www.athome.co.jp/kodate/chuko/hokkaido/list/#seed-19",
            price_man=100, location="北海道室蘭市白鳥台",
            land_m2=None, building_m2=125.03, madori="5LDK", coastal=True,
            note=NOTE + " 室蘭=海に囲まれた街/海沿い度要確認"),
    Listing(source="websearch-seed", title="北海道 室蘭市大沢町 5SLDK 海の街",
            url="https://www.athome.co.jp/kodate/chuko/hokkaido/list/#seed-20",
            price_man=120, location="北海道室蘭市大沢町",
            land_m2=None, building_m2=110.30, madori="5SLDK", coastal=True,
            note=NOTE + " 室蘭=海に囲まれた街/海沿い度要確認"),
]


def main():
    master = load_master(MASTER_PATH)
    master, new_count = merge(master, SEED, today="2026-07-05")
    write_master(MASTER_PATH, master)
    print(f"seed3 投入: 新規{new_count}件 / master {len(master)}件 -> {MASTER_PATH}")


if __name__ == "__main__":
    main()
