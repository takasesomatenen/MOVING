# 海沿い格安物件 デイリー収集

「海沿い・田舎OK・土地＋上物で〜300万円・多少ボロOK・上物ありは面積(㎡)も」
という条件の中古住宅／空き家を、**毎日自動で収集**して蓄積する仕組み。

## 全体の流れ（2エンジン構成）

```
 ┌──────────────────┐          ┌───────────────────┐          ┌──────────────┐
 │ ① GitHub Actions │ ───────▶ │ この repo /data/  │ ───────▶ │ Google Drive │
 │  scraper(毎朝)   │  scrape  │ master CSV        │  upload  │ 新規フォルダ  │
 ├──────────────────┤          │ + 日次スナップ     │          └──────────────┘
 │ ② 毎朝Claude     │ ───────▶ │ + レポートHTML     │   毎朝Claudeセッションが
 │  WebSearch補強   │ add_list │                   │   render→Driveへ投入
 └──────────────────┘          └───────────────────┘
```

### 実地検証で分かったこと（重要）
- **日本の主要不動産サイトはほぼ全て自動アクセスを 403 で拒否**する
  (akiya-athome / homes / SUUMO 等)。Actions ランナーの素の HTTP でも同じ。
  → これらは無効化済み(`enabled=False`)。
- 素のリクエストで**到達できたのは `resort-bukken.com` のみ**。ただし別荘中心で
  ≤300万の在庫は少ない(実測で日1件程度)。
- そこで**新規物件の主供給は WebSearch 補強**にした。WebSearch はバックエンド経由で
  ブロックされない。毎朝の Claude セッションが数件の実在物件を見つけ、
  `add_listing` CLI で master に追記する。この 20件超のシードも WebSearch 由来。

- **Google Drive 投入先フォルダ**「海沿い格安物件 デイリースクレイプ」:
  <https://drive.google.com/drive/folders/1pfboH0QbE6n_2_qXy1Mi60bDENMNbJ4Y>
- この開発サンドボックスは外部サイトが 403 で遮断されるため、スクレイプ実体は
  **GitHub Actions**(ネットワーク開放)で走らせる。ローカルのレポート描画は可。

## 収集条件

| 項目 | 条件 |
|------|------|
| エリア | 海沿い・海近(田舎可)。千葉/静岡/三重/高知/愛媛/長崎/大分 等 |
| 価格 | 既定 **300万円以下**(`--price-cap` で変更可) |
| 種別 | 中古一戸建て・古民家・空き家(多少ボロOK) |
| 面積 | 上物ありは **建物面積(㎡)** と **土地面積(㎡)** を抽出 |
| 判定 | 「海が見える/海まで◯m/オーシャンビュー」等のキーワード + 距離表記 |

## ディレクトリ構成

```
scraper/
  filters.py     価格・面積・海沿い判定の純粋関数(単体テスト付き)
  store.py       Listing データモデル / CSV 保存 / 重複排除
  sources.py     対象サイト定義とページ抽出(assume_coastal/enabled 対応)
  scrape.py      スクレイパー実行エントリ (python -m scraper.scrape)
  add_listing.py 1物件を安全に追記する CLI(毎朝WebSearch補強が使用)
  report.py      master → レポートHTML(ベストピック/ランキング/総額試算)
  render.py      Chromium で HTML→PNG/PDF(日本語 IPAGothic)
  seed*.py       初回シード(第1〜3弾・WebSearch 由来の実在物件20件)
data/
  listings_master.csv   全物件マスタ(価格の安い順)
  daily/YYYY-MM-DD.csv  その日に見つかった物件
  report/index.html     レポート(PNG/PDF は再生成可のため git 管理外)
.github/workflows/
  daily-scrape.yml       毎日 06:17 JST(UTC 21:17)に実行
```

## CSV の列

`id, source, title, price_man, location, land_m2, building_m2, madori, coastal, url, first_seen, last_seen, note`

- `price_man` … 価格(万円)
- `building_m2` … 建物(延床)面積㎡ / `land_m2` … 土地面積㎡
- `coastal` … 海沿い判定(1/0)
- `note` … 備考(第1弾シードは「現物・在庫要確認」)

## 手動実行 / 検証

```bash
# コアロジックの単体テスト(ネット不要)
python scraper/filters.py

# 第1弾シードを master へ投入
python -m scraper.seed

# 本番スクレイプ(要オープンネットワーク = Actions 上)
python -m scraper.scrape --price-cap 300

# WebSearch で見つけた物件を手で追記(重複はURLで排除)
python -m scraper.add_listing --title "尾鷲 海近 中古戸建" --price "250万" \
  --loc "三重県尾鷲市" --building "88.5㎡" --land "120㎡" --madori 4DK \
  --url "https://example.com/bukken/123"

# レポート生成＆描画(ローカル可)
python -m scraper.report
python scraper/render.py data/report/index.html data/report/report.png data/report/report.pdf
```

Actions では **workflow_dispatch** で手動起動可能(price_cap 指定可)。
`schedule` は既定ブランチ上でのみ発火するため、PR マージ後に毎日実行が有効化される。

## 対象サイトを追加するには

`scraper/sources.py` の `SOURCES` に
`{name, enabled, assume_coastal, list_urls, detail_href_re, max_details}` を追記。
`enabled=False` で無効化、`assume_coastal=True` で本文の海キーワード判定を省略
(元々「海」検索のソース向け)。抽出は `filters.py`/`sources.py` の汎用ロジックが処理。

## 注意 / 免責

- 第1弾シード(`source=websearch-seed`)は検索サマリ由来のため、
  **現物・最新在庫・価格は必ず一次情報(掲載元)で確認**すること。
- 各サイトの利用規約・robots・レート制限を尊重する
  (`sources.py` は 1 リクエスト毎に 1 秒スリープ)。
