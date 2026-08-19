# ローカル（MacBook）への引き継ぎ

## まず結論：クラウド側からあなたのMacは動かせない

いま動いているセッションは**クラウド上の隔離されたコンテナ**で、あなたのMacBookのファイルにもアプリにも一切触れない。
Blenderをあなたの手元で起動することもできないし、逆にMacのファイルをこちらから読むこともできない。
接点は **GitHubのリポジトリだけ**。

コンテナは一定時間で回収されて中身は消えるので、残すものは全部pushしてある。
このブランチを引けば、あなたのMacで同じものが動く。

```
ブランチ : claude/most-discarded-construction-materials-paruns
PR       : https://github.com/takasesomatenen/MOVING/pull/9
```

---

## 1. 手元に落とす

```bash
cd ~/ 適当な作業場所
git clone https://github.com/takasesomatenen/MOVING.git
cd MOVING
git fetch origin claude/most-discarded-construction-materials-paruns
git checkout claude/most-discarded-construction-materials-paruns
```

すでにcloneしてあるなら `git fetch origin && git checkout claude/most-discarded-construction-materials-paruns` だけでいい。

## 2. Python側（Blender不要・すぐ動く）

macOS標準の `python3` で動く。外部パッケージは要らない。

```bash
python3 design/check_spec.py        # 寸法・日射・収まり・座標変換の検算
python3 -m design.make_hut_page     # data/report/hut.html を作り直す
open data/report/hut.html           # 図面を見る
```

## 3. Blender側

```bash
brew install --cask blender
```

インストールすると本体は `/Applications/Blender.app/Contents/MacOS/Blender`。
`blender` コマンドにパスを通していないなら、以下のエイリアスを `~/.zshrc` に入れておくと楽。

```bash
alias blender='/Applications/Blender.app/Contents/MacOS/Blender'
```

### 開く

```bash
blender --python design/blender_hut.py                 # GUIで開く
blender --python design/blender_hut.py -- --winter     # カラマツを落葉させた冬の状態
```

GUIが開いたら、テンキー `0` でカメラビュー、`Ctrl+↑`（macOSは `Ctrl+↑`）でカメラを切り替えられる。
カメラは4台（`south_winter` / `southwest_summer` / `interior_south` / `aerial`）入っている。

### 書き出す

```bash
blender --background --python design/blender_hut.py -- out/
blender --background --python design/blender_hut.py -- out/ --samples=128     # 高品質
blender --background --python design/blender_hut.py -- out/ --gpu             # Metalを使う
blender --background --python design/blender_hut.py -- out/ --winter --gpu
```

`--gpu` を効かせるには、一度GUIで **Preferences → System → Cycles Render Devices → Metal** を選んで
GPUにチェックを入れておく必要がある（Blender側の設定なので初回だけ）。

### Blenderアプリを使わずPythonから叩きたい場合

Python **3.11 ちょうど** が必要（3.12以降は不可）。

```bash
python3.11 -m pip install bpy
python3.11 design/blender_hut.py -- out/ --samples=48
```

このクラウド環境ではこの方法で実際に動作確認して、`design/renders/` の4枚を出力した。

---

## 4. Claude Code をローカルで続ける

Macのターミナルでリポジトリのディレクトリに入って `claude` を起動すれば、そのままこの続きができる。
ローカルのClaude CodeはあなたのMac上のBlenderを実際に起動できるので、
「レンダしてみて」「窓の位置を動かして」みたいなやり取りが実物で回せるようになる。

会話の文脈は引き継がれないので、最初にこれを渡せば足りる。

> `design/` に北軽井沢の小屋のCG設計ベースが入っている。`design/HANDOFF.md` と `design/spec.json` を読んで。

---

## 5. いまの状態

### 確認済み

- `design/check_spec.py` … 全項目パス（面積・屋根高・軒の出の日射制御・敷地への収まり・開口位置・太陽のeuler変換）
- `design/make_hut_page.py` … 生成したHTMLをChromiumで実描画し、配置図・平面・断面・立面を目視確認
- `design/blender_hut.py` … bpy 5.0.1 でヘッドレス実行し、4カメラぶんのレンダまで通した（`design/renders/`）
- 内観カットに**浅間山のプロキシが南の開口の中に入っている**ことを確認。眺望の方位設定は合っている

### まだ雑なところ（ローカルで詰めるならここから）

1. **内装が黒い** — 壁はいまテクスチャなしの箱で、内側の面にも外壁材（焼杉＝黒）が付いている。
   面ごとにマテリアルを割って、内側を石膏ボード端材（`materials.wall_int`）にすると内観が起きる。
   これが内観カットの最優先。
2. **軸組が入っていない** — 柱・登り梁・間柱は `spec.json` の `frame` に寸法だけあって、モデルには立てていない。
   セルフビルドの絵として見せるなら、登り梁 105×240 @910 を流すだけでかなり効く。
3. **樹木がローポリのコーン** — 位置と樹高は `spec.vegetation.trees` にあるので、
   実際のカラマツのアセットに差し替えれば絵が一段変わる。
4. **浅間山が三角錐のプロキシ** — 3km地点に見かけの仰角4.8°で置いてあるだけ。
   背景プレート（写真）に差し替えるのが早い。
5. **石膏ボード端材の目地割り** — 内装の見せ場にする予定だが、まだテクスチャがない。
   910×1820の割付けを崩した継ぎ目をUVかテクスチャで作る必要がある。

### 触りかたのルール

寸法は `design/spec.json` **だけ**を触る。図面（HTML）もモデル（Blender）も同じファイルから生成されるので、
片方だけずれることがない。触ったら `python3 design/check_spec.py` を走らせれば辻褄が崩れていないか分かる。
