# 海沿い格安物件 デイリー収集

「海沿い・田舎OK・土地＋上物で〜300万円・多少ボロOK・上物ありは面積(㎡)も」
という条件の中古住宅／空き家を、**毎日自動で収集**して蓄積する仕組み。

## 全体の流れ

```
 ┌──────────────────┐   毎朝    ┌───────────────────┐   毎朝    ┌──────────────┐
 │ GitHub Actions   │ ───────▶ │ この repo /data/  │ ───────▶ │ Google Drive │
 │ daily-scrape.yml │  scrape  │ CSV にコミット     │  upload  │ 新規フォルダ  │
 └──────────────────┘          └───────────────────┘          └──────────────┘
   実サイトへアクセス            master + 日次スナップ         Claude セッションが投入
   (ランナーは網開放)                                          (Drive 連携 MCP)
```

- **スクレイプはこの開発サンドボックス内では動きません。**
  組織ネットワークポリシーで外部サイトが 403 ブロックされるため。
  実収集は **GitHub Actions ランナー**(ネットワーク開放)で行う。
- **Google Drive 投入先フォルダ**:
  「海沿い格安物件 デイリースクレイプ」
  <https://drive.google.com/drive/folders/1pfboH0QbE6n_2_qXy1Mi60bDENMNbJ4Y>

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
  filters.py    価格・面積・海沿い判定の純粋関数(単体テスト付き)
  store.py      Listing データモデル / CSV 保存 / 重複排除
  sources.py    対象サイト定義とページ抽出
  scrape.py     実行エントリ (python -m scraper.scrape)
  seed.py       初回シード(第1弾・WebSearch 由来の実在物件)
data/
  listings_master.csv   全物件マスタ(価格の安い順)
  daily/YYYY-MM-DD.csv  その日に見つかった物件
.github/workflows/
  daily-scrape.yml       毎日 06:17 JST に実行
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
```

Actions では **workflow_dispatch** で手動起動可能(price_cap 指定可)。
`schedule` は既定ブランチ上でのみ発火するため、PR マージ後に毎日実行が有効化される。

## 対象サイトを追加するには

`scraper/sources.py` の `SOURCES` に
`{name, list_urls, detail_href_re, max_details}` を追記するだけ。
詳細ページからの価格・面積抽出は `filters.py` の汎用ロジックが処理する。

## 注意 / 免責

- 第1弾シード(`source=websearch-seed`)は検索サマリ由来のため、
  **現物・最新在庫・価格は必ず一次情報(掲載元)で確認**すること。
- 各サイトの利用規約・robots・レート制限を尊重する
  (`sources.py` は 1 リクエスト毎に 1 秒スリープ)。
