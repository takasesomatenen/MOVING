# design/ ― 北軽井沢 セルフビルド小屋のCG設計ベース

実現性の検証ではなく、**CGで起こすために寸法・方位・地形・光を固定した一式**。

| ファイル | 役割 |
|---|---|
| `spec.json` | 数値の単一の情報源。敷地・建物・開口・材料・太陽・カメラを全部ここに置く |
| `blender_hut.py` | `spec.json` を読んでBlender上にマッシングを生成する |
| `make_hut_page.py` | `spec.json` から図面付きレポート `data/report/hut.html` を生成する |
| `check_spec.py` | 面積・屋根高・軒の出の効き・敷地への収まり・太陽変換の検算（ネット不要） |

## 座標系

右手系・メートル。原点＝敷地南西隅のGL±0、**+X=東 / +Y=真北 / +Z=上**でBlender標準と一致する。
地盤高は `z = 0.05 * y` の一次式（北→南へ5%の下り）。

## 使い方

```bash
python design/check_spec.py            # 寸法の辻褄を検算
python -m design.make_hut_page         # data/report/hut.html を作り直す

blender --python design/blender_hut.py                 # GUIで開く
blender --python design/blender_hut.py -- --winter     # カラマツを落葉させる
blender --background --python design/blender_hut.py -- out/   # 4カット書き出し
```

寸法を変えるときは `spec.json` だけを触る。図面もモデルも同じ数値から生成されるのでずれない。

## 主要諸元

- 敷地 14.0 × 19.5 m ＝ 273㎡（想定区画・北→南へ5%下り・標高1,100m）
- 主屋 7.28 × 5.46 m ＝ 39.75㎡（平屋・910mmグリッド・8P×6P）
- 屋根 片流れ3.5寸（19.29°）・北高南低、南軒の出900mm
- FL ＝ GL+1,050／独立基礎20基・根入れ1.0m（想定凍結深度0.9m超）
- 南面に5,460×2,000の掃き出し。浅間山は方位203°・17.4km・見かけの仰角4.8°

## 太陽

方位角は真北から時計回り。Blenderの Sun は
`rotation_euler = (radians(90 − alt), 0, radians(180 − az))` で一致する（`check_spec.py` が検算する）。
