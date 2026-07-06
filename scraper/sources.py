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


# 所在地の後ろに続きがちな交通/付帯情報。ここで所在地を打ち切る。
_LOC_CUT_RE = re.compile(
    r"(交通|アクセス|最寄|沿線|JR|私鉄|バス|駅(?:まで|から|徒歩)|【|（|\(|土地面積|建物面積|"
    r"面積|価格|間取|築年|\s{2,})"
)


def clean_location(raw: str) -> str:
    """交通情報等が混入した所在地を、都道府県〜番地までで打ち切る。"""
    raw = normalize(raw)
    m = _LOC_CUT_RE.search(raw)
    if m:
        raw = raw[: m.start()]
    return raw.strip(" 　-・,、")[:40]


def clean_title(raw: str) -> str:
    """装飾記号(★等)や区切りを整えたタイトル。"""
    t = normalize(raw)
    t = re.sub(r"[★☆■◆▲▼※\-—|｜]{1,}", " ", t)
    t = re.sub(r"\s{2,}", " ", t).strip()
    return t[:120]


def extract_listing(html, url, source):
    """詳細ページ HTML から Listing を構築(フィルタ前)。"""
    text = html_to_text(html)
    title_m = TITLE_RE.search(html)
    title = clean_title(title_m.group(1)) if title_m else url
    loc_m = LOCATION_RE.search(text)
    location = clean_location(loc_m.group(2)) if loc_m else ""
    building = parse_building_m2(text)
    madori = parse_madori(text) or ""
    # 売地/売土地(上物なし)で間取りが出るのは誤検出。建物が無ければ間取りを外す。
    is_land_only = building is None and re.search(r"売地|売土地|土地売|地目", text)
    if is_land_only:
        madori = ""
    return Listing(
        source=source,
        title=title,
        url=url,
        price_man=parse_price_man(text),
        location=location,
        land_m2=parse_land_m2(text),
        building_m2=building,
        madori=madori,
        coastal=is_coastal(text) or is_coastal(title),
        note="",
    )


# 対象サイト定義 -------------------------------------------------------------
# detail_href_re: 詳細ページ URL を判定する正規表現。
# 沿岸の主要県。akiya-athome は JIS 県コード、resort-bukken はローマ字 slug。
_ATHOME_PREF = {  # 実地ログで /buy/{code}/ は自治体選択ページ = 詳細リンク0だったため
    12: "chiba", 22: "shizuoka", 24: "mie", 28: "hyogo", 30: "wakayama",
    35: "yamaguchi", 38: "ehime", 39: "kochi", 42: "nagasaki", 44: "oita",
    46: "kagoshima", 1: "hokkaido",
}
_RESORT_PREF = [  # 実地ログで動作確認済み(chiba で25 detail links取得→パース成功)
    "chiba", "shizuoka", "mie", "wakayama", "kochi", "ehime", "nagasaki",
    "kagoshima", "yamaguchi", "oita", "tokushima", "hyogo", "kanagawa",
    "hiroshima", "okayama",
]

SOURCES = [
    {
        "name": "resort-bukken",
        # 海(ocean)こだわり検索。実地ログで動作確認済み(唯一 plain requests が通る)。
        # 元々「海」検索なので assume_coastal=True(本文に海キーワードが無くても海沿い扱い)。
        "enabled": True,
        "assume_coastal": True,
        "list_urls": [
            f"https://resort-bukken.com/search/kodawari:ocean/pref:{slug}"
            for slug in _RESORT_PREF
        ],
        "detail_href_re": re.compile(r"/(?:bukken|detail)/\d+"),
        "max_details": 30,
    },
    {
        "name": "athome-akiya",
        # アットホーム空き家バンク。実地ログで検索結果 /bukken/search/list/ が全URL HTTP403
        # (bot ブロック)。plain requests では到達不可のため無効化。
        # 再開するには headless ブラウザ等が必要(将来対応)。
        "enabled": False,
        "list_urls": [
            f"https://www.akiya-athome.jp/bukken/search/list/"
            f"?search_type=area&br_kbn=buy&sbt_kbn=house&pref_cd={code}"
            for code in _ATHOME_PREF
        ],
        "detail_href_re": re.compile(r"/bukken/\d{3,}"),
        "max_details": 30,
    },
    {
        "name": "homes-akiyabank-umi",
        # LIFULL HOME'S 空き家バンク「海が見える」タグ。実地ログで detail link 0(bot)。無効化。
        "enabled": False,
        "list_urls": [
            "https://www.homes.co.jp/akiyabank/btag/1/chiba/",
        ],
        "detail_href_re": re.compile(r"/akiyabank/[a-z]+/[a-z\-]+/b-\d+"),
        "max_details": 20,
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
            # 海沿い判定: assume_coastal のソース(元々「海」検索)は本文キーワードに
            # 依らず海沿い扱いにする(resort-bukken の ocean 検索など)。
            if src.get("assume_coastal") and not lst.coastal:
                lst.coastal = True
            # フィルタ: 海沿い かつ 価格が上限以下(価格不明は保留として残す)
            if not lst.coastal:
                continue
            if lst.price_man is not None and lst.price_man > price_cap_man:
                continue
            results.append(lst)
            time.sleep(1.0)  # 礼儀としてのレート制限
    return results
