"""掲載の生存確認と、成約/掲載終了物件の退避(retire)。

この環境(開発サンドボックス)は不動産サイトへの外部アクセスを 403 で遮断するため、
実効的には GitHub Actions(daily-scrape.yml)のランナー上で走らせることを想定している。

方針(誤削除を避けるため保守的に):
  - 生死を判定できるのは「個別物件ページのURL」を持つ行だけ。
    一覧/空き家バンクのトップや検索結果URL(＋#アンカー)は個別の生死が判らないので
    絶対に退避しない(UNKNOWN 扱い)。
  - 200 応答かつ本文に「成約済/売約済/掲載終了…」等の明確な終了語がある、または
    404/410 の場合のみ GONE と判定して退避する。
  - 403/タイムアウト/接続不可(ランナーがブロックされた等)は SKIP=現状維持。
  - 退避は data/listings_retired.csv へ追記アーカイブし、master からは除去する
    (ハード削除しない=復元可能)。
  - --apply を付けたときだけ master を書き換える。既定は判定ログのみ。

使い方:
  python -m scraper.verify              # 判定してログ出力のみ(master不変)
  python -m scraper.verify --apply      # GONE を退避して master 更新
"""

import argparse
import csv
import datetime
import json
import os
import re
import sys

try:
    import requests
except Exception:  # requests が無い環境(サンドボックス)ではネット確認を諦める
    requests = None

from .store import FIELDNAMES

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MASTER = os.path.join(HERE, "data", "listings_master.csv")
RETIRED = os.path.join(HERE, "data", "listings_retired.csv")
LOG = os.path.join(HERE, "data", "verify_log.json")

# 個別物件ページと判定するURLパターン(このどれかに一致した行だけ生死判定の対象)
DETAIL_RE = re.compile(
    r"(/bukken/detail/|/detail/|athome\.co\.jp/kodate/\d{6,}|"
    r"athome\.co\.jp/tochi/\d{6,}|resort-bukken\.com/detail/|"
    r"erajapan\.co\.jp/catalog/.+/\d+/|sinsei-heights\.jp/[^/]+/detail-)"
)

# 200応答の本文にこれらが含まれれば「掲載終了/成約」とみなす
GONE_TOKENS = [
    "成約済", "ご成約", "売約済", "商談中", "申込済",
    "掲載を終了", "掲載終了", "掲載期間が終了", "公開を終了",
    "販売終了", "受付を終了", "sold out", "sold-out",
]

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def _today():
    return datetime.date.today().isoformat()


def _load_rows(path):
    """master を「ファイル順のリスト」で読む(表示順を保つため)。"""
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _classify(url, timeout):
    """(status, reason) を返す。status = ALIVE / GONE / UNKNOWN / SKIP。"""
    base = url.split("#")[0]
    if not DETAIL_RE.search(base):
        return "UNKNOWN", "一覧/バンクURL(個別判定不可)"
    if requests is None:
        return "SKIP", "requests未導入(サンドボックス)"
    try:
        r = requests.get(base, headers={"User-Agent": UA},
                         timeout=timeout, allow_redirects=True)
    except Exception as e:
        return "SKIP", f"接続不可: {type(e).__name__}"
    if r.status_code in (404, 410):
        return "GONE", f"HTTP {r.status_code}"
    if r.status_code in (401, 403, 429):
        return "SKIP", f"HTTP {r.status_code}(ブロック)"
    if r.status_code >= 500:
        return "SKIP", f"HTTP {r.status_code}(サーバ側)"
    if r.status_code == 200:
        body = r.text.lower()
        for tok in GONE_TOKENS:
            if tok.lower() in body:
                return "GONE", f"本文に「{tok}」"
        return "ALIVE", "HTTP 200"
    return "SKIP", f"HTTP {r.status_code}"


def _append_retired(rows, reason_by_id, day):
    header = FIELDNAMES + ["retired_on", "retire_reason"]
    exists = os.path.exists(RETIRED)
    with open(RETIRED, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=header)
        if not exists:
            w.writeheader()
        for row in rows:
            out = {k: row.get(k, "") for k in FIELDNAMES}
            out["retired_on"] = day
            out["retire_reason"] = reason_by_id.get(row["id"], "")
            w.writerow(out)


def _write_master(rows):
    with open(MASTER, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDNAMES)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in FIELDNAMES})


def main():
    ap = argparse.ArgumentParser(description="掲載の生存確認と成約/掲載終了物件の退避")
    ap.add_argument("--apply", action="store_true",
                    help="GONE を退避して master を更新(既定はログのみ)")
    ap.add_argument("--timeout", type=int, default=15)
    args = ap.parse_args()

    rows = _load_rows(MASTER)
    day = _today()
    results = []
    counts = {"ALIVE": 0, "GONE": 0, "UNKNOWN": 0, "SKIP": 0}
    gone_ids, reason_by_id = [], {}

    for row in rows:
        status, reason = _classify(row.get("url", ""), args.timeout)
        counts[status] += 1
        results.append({
            "id": row["id"], "location": row.get("location", ""),
            "price_man": row.get("price_man", ""), "url": row.get("url", ""),
            "status": status, "reason": reason,
        })
        if status == "GONE":
            gone_ids.append(row["id"])
            reason_by_id[row["id"]] = reason
        print(f"[{status:7}] {row.get('price_man',''):>5}万 "
              f"{row.get('location','')}  ({reason})")

    with open(LOG, "w", encoding="utf-8") as f:
        json.dump({"checked": day, "counts": counts, "results": results},
                  f, ensure_ascii=False, indent=1)

    print(f"\n判定: ALIVE={counts['ALIVE']} GONE={counts['GONE']} "
          f"UNKNOWN={counts['UNKNOWN']} SKIP={counts['SKIP']}  (計{len(rows)})")

    if not gone_ids:
        print("退避対象(成約/掲載終了が確証できた物件)なし。")
        return 0

    if not args.apply:
        print(f"※ --apply 未指定のため master は変更しません。"
              f"退避候補 {len(gone_ids)} 件。")
        return 0

    gone_rows = [r for r in rows if r["id"] in set(gone_ids)]
    keep_rows = [r for r in rows if r["id"] not in set(gone_ids)]
    _append_retired(gone_rows, reason_by_id, day)
    _write_master(keep_rows)
    print(f"退避 {len(gone_rows)} 件を data/listings_retired.csv へ移し、"
          f"master を {len(keep_rows)} 件に更新しました。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
