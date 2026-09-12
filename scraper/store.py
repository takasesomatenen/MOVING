"""物件レコードのデータモデルと CSV への保存・重複排除。"""

import csv
import hashlib
import os
from dataclasses import dataclass, asdict, field, fields
from typing import Optional

FIELDNAMES = [
    "id", "source", "title", "price_man", "location",
    "land_m2", "building_m2", "madori", "coastal",
    "sea_dist_m", "sea_view", "road_access",
    "url", "first_seen", "last_seen", "note",
]


@dataclass
class Listing:
    source: str
    title: str
    url: str
    price_man: Optional[float] = None
    location: str = ""
    land_m2: Optional[float] = None
    building_m2: Optional[float] = None
    madori: str = ""
    coastal: bool = False
    sea_dist_m: str = ""      # 海までの距離(m)。徒歩分由来は概算(≈)
    sea_view: str = ""        # 海見え: ◎/○/△/—(要確認)
    road_access: str = ""     # 車道接道・車進入: ○/△/✕/—(要確認)
    note: str = ""
    first_seen: str = ""
    last_seen: str = ""
    id: str = field(default="")

    def __post_init__(self):
        if not self.id:
            self.id = hashlib.sha1(self.url.encode("utf-8")).hexdigest()[:12]

    def to_row(self) -> dict:
        d = asdict(self)
        return {k: d.get(k, "") for k in FIELDNAMES}


def load_master(path: str) -> dict:
    """master CSV を id->row の dict で読み込む。無ければ空。"""
    rows = {}
    if not os.path.exists(path):
        return rows
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows[r["id"]] = r
    return rows


def _num(v):
    if v in (None, "", "None"):
        return ""
    return v


def merge(master: dict, listings, today: str):
    """新規/更新を master に反映。戻り値: (updated_master, new_count)。"""
    new_count = 0
    for lst in listings:
        row = lst.to_row()
        row["price_man"] = _num(row["price_man"])
        row["land_m2"] = _num(row["land_m2"])
        row["building_m2"] = _num(row["building_m2"])
        row["coastal"] = "1" if lst.coastal else "0"
        if row["id"] in master:
            existing = master[row["id"]]
            row["first_seen"] = existing.get("first_seen") or today
            row["last_seen"] = today
            master[row["id"]] = row
        else:
            row["first_seen"] = today
            row["last_seen"] = today
            master[row["id"]] = row
            new_count += 1
    return master, new_count


def write_csv(path: str, rows) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDNAMES)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in FIELDNAMES})


def write_master(path: str, master: dict) -> None:
    # 価格が安い順、次に新着(last_seen)順で並べる
    def sort_key(r):
        try:
            p = float(r.get("price_man") or 1e9)
        except ValueError:
            p = 1e9
        return (p, r.get("last_seen", ""))
    rows = sorted(master.values(), key=sort_key)
    write_csv(path, rows)
