# 引き継ぎ資料 — SplitKB（iPad 用 左右分割キーボード）

**作成日:** 2026-08-16
**引き継ぐ相手:** Mac / Xcode でローカルビルドできる方
**お願いしたいこと:** Xcode でのプロジェクト作成 → ビルド → iPad 実機での動作確認

---

## 1. これは何か

かつての iPad の「キーボードを分割」と同じ感覚で使える、iPad 用のカスタムキーボード（iOS の Custom Keyboard Extension）です。SwiftUI で書かれています。

**要件として求められたもの**

- iPad 用の分割キーボード（左右に分かれている）
- **真ん中が空いている**こと
- **ローマ字での日本語入力と、英語入力の両方**ができること

**3 つとも実装済みです。** ただし後述のとおり **Xcode でのビルド確認だけが未実施**で、そこを引き継ぎたい部分です。

---

## 2. 現在の状況（ここが一番大事）

| 項目 | 状態 |
| --- | --- |
| コード実装 | ✅ 完了（1,100 行強） |
| ローマ字変換ロジックの検証 | ✅ 完了（Python に移植して 39 ケース全通過） |
| **Xcode でのビルド** | ❌ **未実施** |
| **iPad 実機での動作確認** | ❌ **未実施** |
| Xcode プロジェクトファイル（`.xcodeproj`） | ❌ 無し（手順 3 で作っていただきます） |

**なぜ未実施か:** このコードは Linux コンテナ上で書かれており、その環境には Xcode も Swift ツールチェーンも存在しません（`swift: command not found`）。iOS の `UIKit` / `SwiftUI` は Linux 上でコンパイルできないため、構文・型チェックを一度も通せていません。

そのため、**初回ビルドでコンパイルエラーが出る可能性は十分あります。** 想定される箇所は「6. ビルドが通らなかったら」に列挙しました。

---

## 3. 置き場所

- **リポジトリ:** `takasesomatenen/MOVING`
- **ブランチ:** `claude/ipad-split-keyboard-app-xhgwv2`
- **PR（ドラフト）:** https://github.com/takasesomatenen/MOVING/pull/7
- **ディレクトリ:** `ipad-split-keyboard/`

```
ipad-split-keyboard/
├── README.md                                使い方・キーの説明
├── HANDOVER.md                              このファイル
├── SplitKB/                                 → App ターゲット
│   ├── SplitKBApp.swift                     @main エントリポイント
│   └── ContentView.swift                    動作確認用の入力欄
└── SplitKBKeyboard/                         → Custom Keyboard Extension ターゲット
    ├── KeyboardViewController.swift         キーボード本体（全部ここ・1,056行）
    └── Info.plist                           NSExtension の設定
```

ディレクトリ名がそのまま Xcode のターゲット名に対応するようにしてあります。

---

## 4. セットアップ手順（Mac 側）

`.xcodeproj` は同梱していません（手書きの `project.pbxproj` は壊れていても検証できないため、あえて入れていません）。Xcode に作らせてください。5 分ほどで終わります。

### 4-1. プロジェクトを作る

1. Xcode → **File > New > Project… > iOS > App**
   - Product Name: **`SplitKB`**
   - Interface: **SwiftUI** / Language: **Swift**
   - 保存先はどこでも構いません
2. **File > New > Target… > iOS > Application Extension > Custom Keyboard Extension**
   - Product Name: **`SplitKBKeyboard`**
   - 「Activate "SplitKBKeyboard" scheme?」→ **Activate**

> Product Name をこの 2 つに合わせておくと、`Info.plist` の
> `$(PRODUCT_MODULE_NAME).KeyboardViewController` がそのまま解決されます。
> 別名にする場合は Info.plist の `NSExtensionPrincipalClass` を合わせて直してください。

### 4-2. コードを差し替える

| 差し替え先（Xcode が自動生成したファイル） | 貼り付ける内容 |
| --- | --- |
| `SplitKBKeyboard/KeyboardViewController.swift` | `SplitKBKeyboard/KeyboardViewController.swift` |
| `SplitKB/SplitKBApp.swift` | `SplitKB/SplitKBApp.swift` |
| `SplitKB/ContentView.swift` | `SplitKB/ContentView.swift` |

いずれも**中身を全部消してから丸ごと貼り付け**てください。

`SplitKBKeyboard/Info.plist` は、Xcode が生成したものにも同じ `NSExtension` が入っているはずなので、基本はそのままで動きます。同梱の Info.plist は `PrimaryLanguage` を `ja-JP` にし `RequestsOpenAccess` を明示的に `false` にした版なので、差し替えるとより望ましい状態になります。

### 4-3. ビルド設定

- 両ターゲットの **Minimum Deployments** を **iOS 15.0 以上**に
- **Targeted Device Family** に iPad を含める（デフォルトで `1,2` なので通常は変更不要）
- **署名**: シミュレータだけなら不要。実機に入れるなら両ターゲットに Team を設定してください
  （Bundle Identifier は `xxx.SplitKB` と `xxx.SplitKB.SplitKBKeyboard` のように**親子関係**になっている必要があります）

### 4-4. 実行と有効化

1. iPad（実機 or シミュレータ）を選んで **⌘R**
2. iPad 側で
   `設定 → 一般 → キーボード → キーボード → 新しいキーボードを追加… → SplitKB`
3. 文字入力中に **🌐（地球儀）キー**で `SplitKB` に切り替え

**フルアクセス（Allow Full Access）は不要です。** 通信も一切していません。

---

## 5. 設計の説明

全部 `KeyboardViewController.swift` の 1 ファイルに入っています。上から順に読める構成です。

| 行 | 要素 | 役割 |
| --- | --- | --- |
| 20 | `enum KB` | チューニング用定数。間隔・中央の空きの幅・高さなど |
| 41 | `enum Romaji` | ローマ字→かな変換テーブル（217 エントリ）と補助関数 |
| 225 | `final class RomajiConverter` | 入力エンジン本体 |
| 358 | `enum JapaneseDictionary` | 漢字変換用の簡易辞書（約 80 語） |
| 454 | `final class KeyboardModel` | `ObservableObject` の画面状態 |
| 480 | `enum Layouts` | キー配列（左右・レイヤーごと） |
| 620〜 | `KeyButton` / `KeyRow` / `KeyPanel` / `CandidateBar` / `SplitKeyboardView` | SwiftUI ビュー群 |
| 853 | `class KeyboardViewController` | `UIInputViewController`。キー入力の処理はすべてここ |

### 5-1. 「真ん中が空いている」の実現方法

`SplitKeyboardView`（811 行）で、左右それぞれの `KeyPanel` に角丸の背景を持たせ、**その間には `Color.clear` を置いているだけ**です。ルートビューと `UIInputViewController.view` の背景も `.clear` にしてあるので、中央には下のアプリが透けて見えます。

```swift
HStack(spacing: 0) {
    LeftHalf(model: model, onKey: onKey)
    Color.clear.frame(width: model.gap)   // ← ここが「空き」
    RightHalf(model: model, onKey: onKey)
}
```

空きの幅は `⟷` キーで 4 段階（90 / 150 / 210 / 280pt）、キーボード全体の高さは `⇕` キーで 4 段階（270〜390pt）に切り替わり、`UserDefaults` に保存されます。高さは `applyHeight()` が `view.heightAnchor` の制約（priority 999）を張り替えて反映しています。

### 5-2. ローマ字変換アルゴリズム

`RomajiConverter.resolve()`（249 行付近）が心臓部です。バッファに 1 文字足すたび、次のループを回します。

1. **完全一致** → かなに確定。ただし `nn` のように「さらに長い綴りの先頭でもある」もの（`Romaji.ambiguous`）は確定せず次を待つ
2. **促音** — 先頭 2 文字が同じ子音（`n` を除く）なら「っ」を出して 1 文字進める
3. **接頭辞** — まだ続きがありうるなら待つ
4. **行き止まりかつ `nn` 始まり** — 2 文字まとめて「ん」（`nnk` → `んk`。`んん` にしない）
5. **それ以外の行き止まり** — 先頭 1 文字を吐き出して残りを再評価（`nb` → `ん` + `b`）

`nn` を `ambiguous` 扱いにしたうえで `nna`〜`nno` / `nnya` 等をテーブルに入れてあるため、**一般的な IME と同じ「ん」の挙動**になります。

| 打ち方 | 結果 |
| --- | --- |
| `sensei`（n + 子音） | せんせい |
| `gohann`（nn 終わり） | ごはん |
| `konnichiha` / `onna`（nn + 母音） | こんにちは / おんな |
| `konnnichiha`（nnn + 母音） | こんにちは |
| `hon'ya` | ほんや |

### 5-3. 入力と確定の流れ

未確定文字はホストアプリに渡さず、`RomajiConverter` の中に保持し、候補バーに表示します。`UIInputViewController` には未確定文字（marked text）をホストに渡す公開 API が無いためです。確定時に `textDocumentProxy.insertText()` でまとめて挿入します。

- **空白キー** — 変換中は候補送り、そうでなければスペース入力
- **改行キー** — 変換中は確定、そうでなければ改行
- **候補チップのタップ** — 即確定
- **記号キー / `あ`⇄`A` 切り替え / 🌐 / キーボードを閉じる** — 変換中の文字を自動で確定してから実行
- **`ー`（長音）だけは例外** — 変換を切らずに続く（`ko-hi-` → こーひー）

### 5-4. 漢字変換の制限（重要・仕様として認識してください）

**iOS はかな漢字変換エンジンを外部アプリに開放していません。** Apple 純正キーボードが使っている変換辞書を呼ぶ公開 API は存在しません。

そのため漢字は `JapaneseDictionary.words`（358 行）に**登録した語だけ**が候補に出ます。現在は常用語 80 語ほどを同梱しています。

```swift
enum JapaneseDictionary {
    static let words: [String: [String]] = [
        "にほんご": ["日本語"],
        "かいぎ": ["会議"],
        // ここに足せば増えます
    ]
}
```

ひらがな・カタカナ・英字・全角英字の入力は辞書なしで完全に動きます。本格的な漢字変換が必要なら、SKK / mozc などの公開辞書ファイルをアプリに同梱し、この辞書の読み込み元を差し替えるのが現実的です（辞書ファイルのライセンス確認が必要）。

---

## 6. ビルドが通らなかったら

型チェックを通せていないので、エラーが出るとすればこのあたりだと思っています。**上から順に疑ってください。**

1. **`Timer` のクロージャ内での `@State` 書き換え**（`KeyButton.beginPress()` / 670 行付近）
   `⌫` の長押しリピート用です。`@State` の setter は `nonmutating` なので struct でも通るはずですが、`escaping closure captures mutating self` 系のエラーが出たら、`KeyButton` からリピート機能ごと外して単純なタップのみにしてしまって構いません（機能的には劣化しますが本質ではありません）。

2. **SwiftUI の型チェックタイムアウト**（`unable to type-check this expression in reasonable time`）
   対策済みではあります（大きい辞書リテラルを 13 個のグループに分割、左右パネルを `LeftHalf` / `RightHalf` に分離、`GeometryReader` 内の計算を `width(for:total:)` メソッドに追い出し、ViewBuilder 内に `let` 文を書かない）。それでも出たら、出た式をさらに小さい `private var` / `private func` に切り出してください。

3. **`Unicode.Scalar` のイニシャライザ曖昧性**（`Romaji.toFullWidth` / 200 行付近）
   `Unicode.Scalar(UInt32(0x3000))!` と明示してありますが、環境によっては別の書き方を求められるかもしれません。

4. **`Info.plist` の `NSExtensionPrincipalClass`**
   ビルドは通るのにキーボードが真っ白 / 一覧に出ない場合はこれです。`$(PRODUCT_MODULE_NAME).KeyboardViewController` が実際のモジュール名と一致しているか確認してください。

5. **Deployment Target**
   iOS 15.0 未満だとエラーになる API を使っています。

6. **`enum KB` の名前衝突**
   `KB` という短い名前なので、他ファイルと衝突したら好きな名前にリネームしてください（このファイル内でしか使っていません）。

---

## 7. 実機で見ていただきたい確認項目

ビルドが通ったあと、iPad 実機でここを見てもらえると助かります。

**レイアウト**
- [ ] 左右に分かれて表示され、**中央が透けている**こと
- [ ] `⟷` で中央の空きが 4 段階に変わり、アプリを閉じて開き直しても維持されること
- [ ] `⇕` で高さが変わり、キーが潰れたり文字が切れたりしないこと
- [ ] 横向き / 縦向き、Split View / Slide Over で崩れないこと
- [ ] ダークモードで文字が読めること

**日本語入力**
- [ ] `nihongo` → にほんご
- [ ] `konnichiha` → こんにちは（`nn` + 母音）
- [ ] `gakkou` → がっこう、`kippu` → きっぷ（促音）
- [ ] `sensei` → せんせい、`gohann` → ごはん（撥音）
- [ ] `ko-hi-` → こーひー（長音で変換が切れない）
- [ ] 空白キーで候補が送られ、改行キーで確定されること
- [ ] 候補チップのタップで確定されること
- [ ] `かいぎ` で「会議」が候補に出ること（辞書の動作確認）

**英語入力・その他**
- [ ] `あ`/`A` キーで切り替わり、英字がそのまま入ること
- [ ] `⇧` の 3 状態（一時シフト → Caps Lock → 解除）
- [ ] `123` / `#+=` / `ABC` のレイヤー切り替え
- [ ] `⌫` の長押しで連続削除されること
- [ ] 🌐 で他のキーボードに切り替わること
- [ ] 変換中に 🌐 や `あ`/`A` を押すと、未確定文字が消えずに確定されること
- [ ] 入力欄を切り替えたときに未確定文字が変な形で残らないこと

---

## 8. 残タスク・改善候補

**必須（引き継ぎ先にお願いしたい）**
- Xcode でのビルドとエラー修正
- 実機での上記チェックリスト

**やるなら（優先度順）**
1. **辞書の拡充** — いまが一番の弱点です。外部辞書（SKK/mozc）の同梱と読み込み処理
2. **変換単位の分割** — 現在は 1 文節まるごとしか変換できません。文節の区切り変更が欲しくなるはずです
3. **学習機能** — 選んだ候補を `UserDefaults` に覚えて次回優先表示する。数十行で入ります
4. **キー音・触覚フィードバック** — 未実装。触覚はフルアクセスが必要になる点に注意
5. **フリック入力レイヤー** — ローマ字以外の選択肢が欲しくなったら
6. **App Group** — 本体アプリ側から設定（空きの幅など）を変えられるようにする場合に必要

---

## 9. 問い合わせ先

コードの意図で不明な点があれば、この PR にコメントをいただければ回答・修正します。

- PR: https://github.com/takasesomatenen/MOVING/pull/7
- ブランチ: `claude/ipad-split-keyboard-app-xhgwv2`
