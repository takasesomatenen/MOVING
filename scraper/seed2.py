"""第2弾シード(WebSearch 由来の実在物件・2026-07 時点)。

第1弾に続き、海沿い≤300万・面積/間取り付きで裏取りできたものを追加。
出所が検索サマリ由来のため現物・在庫の一次確認が必要(note に明記)。
"""

import os

from .store import Listing, load_master, merge, write_master

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MASTER_PATH = os.path.join(ROOT, "data", "listings_master.csv")

NOTE = "第2弾(WebSearch由来/2026-07) 現物・在庫要確認"

SEED = [
    Listing(source="websearch-seed", title="和歌山 白浜町堅田 1LDK 1984築 海近",
            url="https://www.athome.co.jp/kodate/chuko/wakayama/list/#seed-11",
            price_man=248, location="和歌山県西牟婁郡白浜町堅田",
            land_m2=None, building_m2=61.00, madori="1LDK", coastal=True, note=NOTE),
    Listing(source="websearch-seed", title="和歌山 由良町大引 高台から海望む リフォーム済",
            url="https://www.wakayamagurashi.jp/house/search/#seed-12",
            price_man=300, location="和歌山県日高郡由良町大引",
            land_m2=None, building_m2=None, madori="", coastal=True,
            note=NOTE + " リフォーム済/建物面積要確認"),
    Listing(source="websearch-seed", title="高知 室戸市 土地95㎡ 海近(格安)",
            url="https://www.homes.co.jp/akiyabank/kochi/muroto/#seed-13",
            price_man=100, location="高知県室戸市",
            land_m2=95.86, building_m2=None, madori="", coastal=True, note=NOTE),
    Listing(source="websearch-seed", title="高知 室戸市 土地111㎡ 海近",
            url="https://www.homes.co.jp/akiyabank/kochi/muroto/#seed-14",
            price_man=300, location="高知県室戸市",
            land_m2=111.82, building_m2=None, madori="", coastal=True, note=NOTE),
    Listing(source="websearch-seed", title="高知 土佐市新居 6DK 広め 海沿い",
            url="https://www.athome.co.jp/kodate/chuko/kochi/list/#seed-15",
            price_man=290, location="高知県土佐市新居",
            land_m2=181.30, building_m2=155.61, madori="6DK", coastal=True, note=NOTE),
    Listing(source="websearch-seed", title="山口 周防大島町 7DK 木造2階 瀬戸内",
            url="https://teiju-suo-oshima.com/akiya/akiya_condition_category/oceanview#seed-16",
            price_man=290, location="山口県大島郡周防大島町",
            land_m2=None, building_m2=None, madori="7DK", coastal=True,
            note=NOTE + " 建物面積要確認"),
]


def main():
    master = load_master(MASTER_PATH)
    master, new_count = merge(master, SEED, today="2026-07-05")
    write_master(MASTER_PATH, master)
    print(f"seed2 投入: 新規{new_count}件 / master {len(master)}件 -> {MASTER_PATH}")


if __name__ == "__main__":
    main()
