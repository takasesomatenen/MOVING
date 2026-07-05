"""初回シードデータ(WebSearch 由来の実在物件・2026-07 時点)。

Actions のスクレイパーが稼働するまでの「第1弾」として master に投入する。
出所が検索サマリ由来のため、各レコードは現物・最新在庫の確認が必要
(note に明記)。URL は発見元の一覧/検索ページ + #seed 断片。
"""

import os

from .store import Listing, load_master, merge, write_master

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MASTER_PATH = os.path.join(ROOT, "data", "listings_master.csv")

NOTE = "第1弾(WebSearch由来/2026-07) 現物・在庫要確認"

SEED = [
    Listing(source="websearch-seed", title="南房総市和田町和田 5DK 中古住宅 海近",
            url="https://www.athome.co.jp/kodate/chuko/chiba/minamiboso-city/list/#seed-1",
            price_man=180, location="千葉県南房総市和田町和田",
            land_m2=98.02, building_m2=100.80, madori="5DK", coastal=True, note=NOTE),
    Listing(source="websearch-seed", title="南房総市白浜町白浜 2SDK 灯台/海釣り",
            url="https://www.athome.co.jp/kodate/chuko/chiba/minamiboso-city/list/#seed-2",
            price_man=280, location="千葉県南房総市白浜町白浜",
            land_m2=31.30, building_m2=91.70, madori="2SDK", coastal=True, note=NOTE),
    Listing(source="websearch-seed", title="鴨川市太海浜 2K 木造 オーシャンビュー",
            url="https://www.homes.co.jp/akiyabank/btag/1/chiba/#seed-3",
            price_man=220, location="千葉県鴨川市太海浜",
            land_m2=None, building_m2=50.82, madori="2K", coastal=True, note=NOTE),
    Listing(source="websearch-seed", title="鴨川市広場 平屋2K スーパー徒歩圏",
            url="https://www.athome.co.jp/kodate/chuko/chiba/kamogawa-city/list/#seed-4",
            price_man=300, location="千葉県鴨川市広場",
            land_m2=200.00, building_m2=39.67, madori="2K", coastal=True,
            note=NOTE + " 海沿い度は要確認"),
    Listing(source="websearch-seed", title="匝瑳市 2LDK 新堀浜まで450m",
            url="https://www.akiya-athome.jp/buy/12/#seed-5",
            price_man=300, location="千葉県匝瑳市",
            land_m2=110.00, building_m2=None, madori="2LDK", coastal=True, note=NOTE),
    Listing(source="websearch-seed", title="志摩市大王町畔名 堤防越しに海",
            url="https://www.athome.co.jp/kodate/chuko/mie/shima-city/list/#seed-6",
            price_man=298, location="三重県志摩市大王町畔名",
            land_m2=216.09, building_m2=111.96, madori="", coastal=True, note=NOTE),
    Listing(source="websearch-seed", title="対馬市 4DK 海まで徒歩数秒",
            url="https://www.akiya-athome.jp/buy/42/#seed-7",
            price_man=100, location="長崎県対馬市",
            land_m2=None, building_m2=115.13, madori="4DK", coastal=True, note=NOTE),
    Listing(source="websearch-seed", title="対馬市 5K 海沿い",
            url="https://www.akiya-athome.jp/buy/42/#seed-8",
            price_man=200, location="長崎県対馬市",
            land_m2=None, building_m2=71.75, madori="5K", coastal=True, note=NOTE),
    Listing(source="websearch-seed", title="平戸市 海が目の前",
            url="https://www.homes.co.jp/akiyabank/btag/1/nagasaki/hirado/#seed-9",
            price_man=100, location="長崎県平戸市",
            land_m2=132.00, building_m2=None, madori="", coastal=True, note=NOTE),
    Listing(source="websearch-seed", title="佐伯市 6DK 海沿いの集落",
            url="https://www.akiya-athome.jp/buy/44/#seed-10",
            price_man=200, location="大分県佐伯市",
            land_m2=None, building_m2=111.74, madori="6DK", coastal=True, note=NOTE),
]


def main():
    master = load_master(MASTER_PATH)
    master, new_count = merge(master, SEED, today="2026-07-05")
    write_master(MASTER_PATH, master)
    print(f"seed 投入: 新規{new_count}件 / master {len(master)}件 -> {MASTER_PATH}")


if __name__ == "__main__":
    main()
