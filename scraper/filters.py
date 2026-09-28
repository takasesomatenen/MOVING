"""物件テキストから価格・面積・海沿い判定を抽出する純粋関数群。

外部ネットワークに依存しないので、ローカルで単体テストできる。
日本の不動産掲載ページは表記ゆれがあるため、CSSセレクタではなく
テキストに対する正規表現/ヒューリスティックで拾う方針。
"""

import re
import unicodedata

# ---- 海沿いキーワード -------------------------------------------------------
# 物件テキストにこれらが含まれれば「海沿い/海近」候補とみなす。
COASTAL_KEYWORDS = [
    "海が見える", "海一望", "海望", "オーシャンビュー", "海沿い", "海近",
    "海まで", "海徒歩", "海辺", "浜辺", "ビーチ", "海岸", "港",
    "灯台", "漁港", "海水浴", "サーフ", "マリン", "海を望む", "潮風",
    "海側", "臨海", "シーサイド", "渚",
]

# 明確に海に近いことを示す強いシグナル（距離表記など）
_SEA_DISTANCE_RE = re.compile(
    r"海(?:岸|水浴場|浜)?(?:まで|へ)?\s*(?:徒歩\s*)?(\d+(?:\.\d+)?)\s*(m|ｍ|メートル|km|ｋｍ|分)"
)


def normalize(text: str) -> str:
    """全角英数・記号を半角へ、余分な空白を除去。"""
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def is_coastal(text: str) -> bool:
    """物件説明テキストが海沿い/海近を示すか。"""
    t = normalize(text)
    if any(kw in t for kw in COASTAL_KEYWORDS):
        return True
    if _SEA_DISTANCE_RE.search(t):
        return True
    return False


# ---- 価格 -------------------------------------------------------------------
# 「1,280万円」「980万」「1億2000万円」等に対応。返り値は万円単位の float。
_OKU_MAN_RE = re.compile(r"(\d+)\s*億\s*(\d[\d,]*)\s*万")
_OKU_RE = re.compile(r"(\d+)\s*億(?!\d*\s*万)")
_MAN_RE = re.compile(r"([\d,]+(?:\.\d+)?)\s*万")


def parse_price_man(text: str):
    """テキストから価格を万円単位(float)で返す。取れなければ None。"""
    if not text:
        return None
    t = normalize(text)
    m = _OKU_MAN_RE.search(t)
    if m:
        oku = int(m.group(1))
        man = float(m.group(2).replace(",", ""))
        return oku * 10000 + man
    m = _OKU_RE.search(t)
    if m:
        return int(m.group(1)) * 10000.0
    m = _MAN_RE.search(t)
    if m:
        try:
            return float(m.group(1).replace(",", ""))
        except ValueError:
            return None
    return None


# ---- 面積 -------------------------------------------------------------------
# 建物面積(延床) / 土地面積 を ㎡ で抽出。坪表記は㎡へ換算(1坪=3.30578㎡)。
TSUBO_TO_M2 = 3.305785

_M2_UNIT = r"(?:m²|㎡|m2|平米|平方メートル|平方m|ｍ2)"
_TSUBO_UNIT = r"(?:坪)"

_BUILDING_LABELS = r"(?:建物面積|延床面積|延べ床面積|建物|延床|専有面積|床面積)"
_LAND_LABELS = r"(?:土地面積|敷地面積|土地|敷地)"


def _extract_area(text: str, labels: str):
    """ラベル近傍の数値+単位を㎡で返す。"""
    t = normalize(text)
    # ラベル → 数値 → 単位（間に約・全角記号・コロン等を許容）
    pat_m2 = re.compile(labels + r"[^\d]{0,8}?(\d[\d,]*(?:\.\d+)?)\s*" + _M2_UNIT)
    m = pat_m2.search(t)
    if m:
        try:
            return round(float(m.group(1).replace(",", "")), 2)
        except ValueError:
            pass
    pat_tsubo = re.compile(labels + r"[^\d]{0,8}?(\d[\d,]*(?:\.\d+)?)\s*" + _TSUBO_UNIT)
    m = pat_tsubo.search(t)
    if m:
        try:
            return round(float(m.group(1).replace(",", "")) * TSUBO_TO_M2, 2)
        except ValueError:
            pass
    return None


def parse_building_m2(text: str):
    return _extract_area(text, _BUILDING_LABELS)


def parse_land_m2(text: str):
    return _extract_area(text, _LAND_LABELS)


# ---- 間取り -----------------------------------------------------------------
_MADORI_RE = re.compile(r"\b(\d{1,2})\s*([SLDK]{1,4})\b", re.IGNORECASE)


def parse_madori(text: str):
    t = normalize(text)
    m = _MADORI_RE.search(t.replace(" ", ""))
    if m:
        return f"{m.group(1)}{m.group(2).upper()}"
    # 平屋2K のような表記
    m = re.search(r"(\d{1,2}[SLDK]{1,4})", t.replace(" ", ""), re.IGNORECASE)
    return m.group(1).upper() if m else None


# ---- 海までの距離 / 海見え / 車道 -------------------------------------------
# いずれも掲載テキスト(タイトル+備考)からの推定。正確値は現地/掲載元で要確認。
_WALK_MIN_TO_M = 80  # 不動産表記の徒歩1分=80m 慣行

_DIST_M_RE = re.compile(
    r"(?:海|海岸|海水浴場|浜|漁港|ビーチ|渚)(?:まで|へ)?\s*(?:約\s*)?(\d+(?:\.\d+)?)\s*(m|ｍ|メートル|km|ｋｍ)"
)
_DIST_WALK_RE = re.compile(
    r"(?:海|海岸|海水浴場|浜|漁港|ビーチ|渚)(?:まで|へ)?\s*(?:徒歩|歩いて)\s*(?:約\s*)?(\d+(?:\.\d+)?)\s*分"
)
# 距離数値は無いが「至近」を示す語 → 概算メートル
_VERY_CLOSE = {
    "海が目の前": 30, "目の前が海": 30, "オーシャンフロント": 20, "波打ち際": 20,
    "海際": 30, "海に面": 30, "海まで徒歩数秒": 50, "徒歩数秒": 50, "渚まで": 60,
}


def parse_sea_distance_m(text: str):
    """海までの距離を m(概算含む)で返す。取れなければ None。
    戻り値は文字列: 実測=`300`, 徒歩/至近由来の概算=`≈160`。
    """
    if not text:
        return None
    t = normalize(text)
    m = _DIST_M_RE.search(t)
    if m:
        v = float(m.group(1))
        if m.group(2) in ("km", "ｋｍ"):
            v *= 1000
        return str(int(round(v)))
    m = _DIST_WALK_RE.search(t)
    if m:
        v = float(m.group(1)) * _WALK_MIN_TO_M
        return f"≈{int(round(v))}"
    for kw, meters in _VERY_CLOSE.items():
        if kw in t:
            return f"≈{meters}"
    return None


_VIEW_STRONG = ["オーシャンビュー", "海一望", "海を望む", "海が見える", "海望む",
                "全室海", "海望", "海ビュー", "海見え", "海が一望"]
_VIEW_MAYBE = ["高台", "見晴らし", "見晴し", "眺望", "展望", "小高い", "高台から海"]


def infer_sea_view(text: str):
    """海見え(高さ的に海が見えるか)を ◎/○/△/— で推定。—=不明(要確認)。"""
    t = normalize(text)
    if any(k in t for k in _VIEW_STRONG):
        return "◎"
    if "堤防越し" in t or "堤防越" in t:
        return "△"
    if any(k in t for k in _VIEW_MAYBE):
        return "○"
    return "—"


_ROAD_OK = ["駐車", "車庫", "ガレージ", "カーポート", "接道", "前面道路", "車進入可",
            "2台", "２台", "車庫あり", "駐車場あり", "私道負担なし"]
_ROAD_BAD = ["車進入不可", "車不可", "接道なし", "未接道", "階段のみ", "車入らない",
             "車が入らない", "無接道"]
_ROAD_WARN = ["軽自動車", "幅員狭", "狭い道", "路地", "私道", "旗竿"]


def infer_road_access(text: str):
    """車道接道・車の進入可否を ○/△/✕/— で推定。—=不明(要確認)。"""
    t = normalize(text)
    if any(k in t for k in _ROAD_BAD):
        return "✕"
    if any(k in t for k in _ROAD_OK):
        return "○"
    if any(k in t for k in _ROAD_WARN):
        return "△"
    return "—"


if __name__ == "__main__":
    # 簡易セルフテスト
    assert parse_sea_distance_m("海まで300m") == "300"
    assert parse_sea_distance_m("海まで徒歩5分") == "≈400"
    assert parse_sea_distance_m("海が目の前") == "≈30"
    assert parse_sea_distance_m("海まで1.2km") == "1200"
    assert infer_sea_view("オーシャンビュー") == "◎"
    assert infer_sea_view("高台から海望む") == "◎"
    assert infer_sea_view("高台の分譲地") == "○"
    assert infer_sea_view("堤防越しに海") == "△"
    assert infer_sea_view("駅前の家") == "—"
    assert infer_road_access("駐車2台可") == "○"
    assert infer_road_access("車進入不可の高台") == "✕"
    assert infer_road_access("軽自動車のみ") == "△"
    assert parse_price_man("1,280万円") == 1280
    assert parse_price_man("980万") == 980
    assert parse_price_man("1億2000万円") == 12000
    assert parse_price_man("3億円") == 30000
    assert parse_price_man("価格未定") is None
    assert parse_building_m2("建物面積 100.80㎡") == 100.80
    assert parse_building_m2("延床面積：71.75m²") == 71.75
    assert abs(parse_building_m2("建物 30坪") - 99.17) < 0.1
    assert parse_land_m2("土地面積 200.00㎡") == 200.0
    assert is_coastal("野島崎灯台をシンボルとする白浜で海や釣り") is True
    assert is_coastal("海まで徒歩5分のオーシャンビュー") is True
    assert is_coastal("駅前の便利な住宅街") is False
    assert parse_madori("平屋建2K") == "2K"
    assert parse_madori("2階建5DK") == "5DK"
    print("filters.py self-test OK")
