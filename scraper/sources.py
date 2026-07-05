"""スクレイピング対象サイトの定義と、ページからの物件抽出。

方針:
  1. list_url(一覧ページ) を取得し、detail_href_re に一致するリンクを集める。
  2. 各 detail ページを取得し、ラベル付きテキストから価格・面積を正規表現で抽出。
  3. 海沿いキーワード + 価格上限でふるいにかけるのは scrape.py 側。

対象サイトは bot ブロックの可能性があるため、各ソースは独立して
try/except で回し、1つ落ちても他は動くようにする(scrape.py 側)。
"""

import re
import time
from urllib.parse import urljoin, urlparse

import requests

from .filters import (
    is_coastal, parse_price_man, parse_building_m2, parse_land_m2, parse_madori,
    normalize,
)
from .store import Listing

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
}

TAG_RE = re.compile(r"<[^>]+>")
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
LOCATION_RE = re.compile(r"(所在地|住所)[：: ]{0,3}([^<\n]{4,40})")


def make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update(HEADERS)
    return s


def fetch(session, url, timeout=25, retries=2):
    last = None
    for i in range(retries + 1):
        try:
            r = session.get(url, timeout=timeout)
            if r.status_code == 200:
                r.encoding = r.apparent_encoding or r.encoding
                return r.text
            last = f"HTTP {r.status_code}"
        except requests.RequestException as e:
            last = str(e)
        time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"fetch failed {url}: {last}")


def html_to_text(html: str) -> str:
    txt = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html,
                 flags=re.IGNORECASE | re.DOTALL)
    txt = TAG_RE.sub(" ", txt)
    return normalize(txt)


def collect_detail_urls(html, base_url, href_re):
    urls = set()
    for m in re.finditer(r'href=["\']([^"\']+)["\']', html, re.IGNORECASE):
        href = m.group(1)
        if href_re.search(href):
            urls.add(urljoin(base_url, href))
    return urls


def extract_listing(html, url, source):
    """詳細ページ HTML から Listing を構築(フィルタ前)。"""
    text = html_to_text(html)
    title_m = TITLE_RE.search(html)
    title = normalize(title_m.group(1)) if title_m else url
    loc_m = LOCATION_RE.search(text)
    location = loc_m.group(2).strip() if loc_m else ""
    return Listing(
        source=source,
        title=title[:120],
        url=url,
        price_man=parse_price_man(text),
        location=location[:60],
        land_m2=parse_land_m2(text),
        building_m2=parse_building_m2(text),
        madori=parse_madori(text) or "",
        coastal=is_coastal(text) or is_coastal(title),
        note="",
    )


# 対象サイト定義 -------------------------------------------------------------
# detail_href_re: 詳細ページ URL を判定する正規表現。
SOURCES = [
    {
        "name": "athome-akiya",
        # アットホーム空き家バンク: 海沿いを含む県のトップ(自治体一覧→物件)。
        # 実運用では県コード(12=千葉,22=静岡,24=三重,38=愛媛,39=高知,42=長崎,44=大分)。
        "list_urls": [
            "https://www.akiya-athome.jp/buy/12/",
            "https://www.akiya-athome.jp/buy/22/",
            "https://www.akiya-athome.jp/buy/24/",
            "https://www.akiya-athome.jp/buy/39/",
            "https://www.akiya-athome.jp/buy/42/",
            "https://www.akiya-athome.jp/buy/44/",
        ],
        "detail_href_re": re.compile(r"/bukken/(?:detail/)?\d+"),
        "max_details": 40,
    },
    {
        "name": "homes-akiyabank-umi",
        # LIFULL HOME'S 空き家バンク「海が見える暮らし」タグ(btag/1)。
        "list_urls": [
            "https://www.homes.co.jp/akiyabank/btag/1/chiba/",
            "https://www.homes.co.jp/akiyabank/btag/1/shizuoka/",
            "https://www.homes.co.jp/akiyabank/btag/1/mie/",
            "https://www.homes.co.jp/akiyabank/btag/1/kochi/",
            "https://www.homes.co.jp/akiyabank/btag/1/nagasaki/",
        ],
        "detail_href_re": re.compile(r"/akiyabank/[a-z]+/[a-z\-]+/b-\d+"),
        "max_details": 40,
    },
    {
        "name": "resort-bukken",
        # 海(ocean)こだわり検索。県別。
        "list_urls": [
            "https://resort-bukken.com/search/kodawari:ocean/pref:chiba",
            "https://resort-bukken.com/search/kodawari:ocean/pref:shizuoka",
            "https://resort-bukken.com/search/kodawari:ocean/pref:mie",
        ],
        "detail_href_re": re.compile(r"/(?:bukken|detail)/\d+"),
        "max_details": 30,
    },
]


def scrape_source(src, session, price_cap_man, log):
    """1ソースをスクレイプし Listing のリストを返す。例外は投げず log。"""
    results = []
    seen = set()
    for list_url in src["list_urls"]:
        try:
            html = fetch(session, list_url)
        except Exception as e:  # noqa: BLE001
            log(f"  [!] list fetch fail {list_url}: {e}")
            continue
        detail_urls = collect_detail_urls(html, list_url, src["detail_href_re"])
        log(f"  {list_url} -> {len(detail_urls)} detail links")
        for durl in list(detail_urls)[: src.get("max_details", 40)]:
            if durl in seen:
                continue
            seen.add(durl)
            try:
                dhtml = fetch(session, durl)
                lst = extract_listing(dhtml, durl, src["name"])
            except Exception as e:  # noqa: BLE001
                log(f"    [!] detail fail {durl}: {e}")
                continue
            # フィルタ: 海沿い かつ 価格が上限以下(価格不明は保留として残す)
            if not lst.coastal:
                continue
            if lst.price_man is not None and lst.price_man > price_cap_man:
                continue
            results.append(lst)
            time.sleep(1.0)  # 礼儀としてのレート制限
    return results
