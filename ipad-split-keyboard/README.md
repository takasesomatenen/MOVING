# SplitKB — iPad 用 左右分割キーボード（Swift / SwiftUI）

かつての iPad の「キーボードを分割」と同じ感覚で使える、自作のカスタムキーボードです。
左右に分かれていて**真ん中が空いています**（背景を敷いていないので、下のアプリが透けます）。

- **日本語モード**：ローマ字入力（`ka`→か、`kya`→きゃ、`tte`→って、`nn`→ん、`konnichiha`→こんにちは）
- **英語モード**：そのまま英字入力
- `あ / A` キーで 1 タップ切り替え

---

## ファイル

| ファイル | 貼り付け先 |
| --- | --- |
| `KeyboardViewController.swift` | Custom Keyboard Extension ターゲットの `KeyboardViewController.swift` |
| `HostApp/ContentView.swift` | App ターゲットの `ContentView.swift`（動作確認用・任意） |

---

## Xcode でのセットアップ（MacBook 側の手順）

1. Xcode を開く → **File > New > Project… > iOS > App**
   - Product Name: `SplitKB`
   - Interface: **SwiftUI**、Language: **Swift**
2. **File > New > Target… > iOS > Custom Keyboard Extension**
   - Product Name: `SplitKBKeyboard`
   - 「Activate scheme?」と聞かれたら **Activate** で OK
3. 生成された `SplitKBKeyboard/KeyboardViewController.swift` を開き、**中身を全部消して**
   このリポジトリの `KeyboardViewController.swift` を丸ごと貼り付ける
4. （任意）App 側の `ContentView.swift` も差し替えると、その場で試せます
5. プロジェクト設定 → 両方のターゲットの **Minimum Deployments** を **iOS 15.0** 以上にする
6. iPad（実機 or シミュレータ）を選んで **⌘R** で実行

### iPad 側での有効化（初回だけ）

```
設定 → 一般 → キーボード → キーボード → 新しいキーボードを追加… → SplitKB
```

あとは文字入力中に **🌐（地球儀）キー** を長押し／タップして `SplitKB` を選ぶだけです。

> フルアクセス（Allow Full Access）は **不要** です。通信も一切しません。

---

## キーの説明

| キー | 動作 |
| --- | --- |
| `あ / A` | 日本語（ローマ字）⇔ 英語 の切り替え |
| `空白` | スペース入力。変換中は **`変換`** になり、押すたびに候補が切り替わる |
| `改行` | 改行。変換中は **`確定`** になる |
| `⌫` | 1 文字削除（長押しで連続削除） |
| `⇧` | 1 回タップ＝一時シフト、もう 1 回＝ Caps Lock、もう 1 回＝解除 |
| `123` / `#+=` / `ABC` | 数字・記号レイヤーの切り替え |
| `⟷` | **真ん中の空きの幅**を 4 段階で切り替え（90 / 150 / 210 / 280pt） |
| `⇕` | キーボードの高さを 4 段階で切り替え（270〜390pt） |
| `🌐` | 他のキーボードへ切り替え |
| `⌨︎▾` | キーボードを閉じる |

`⟷` と `⇕` の設定は `UserDefaults` に保存されるので、次に開いたときも維持されます。

---

## 入力の流れ（日本語モード）

1. ローマ字を打つと、上のバーに変換中の文字（例：`にほんご`）が出ます
2. 候補チップが並びます（**ひらがな → 辞書の漢字 → カタカナ → 英字 → 全角英字**）
3. `変換` キーで候補を送るか、候補チップを直接タップ
4. `確定` キー（または候補タップ）で本文に入ります

記号キーや `あ/A` 切り替えを押したときも、変換中の文字は自動で確定されます。
`ー`（長音）だけは例外で、変換を切らずにそのまま続きます（`ko-hi-` → こーひー）。

### 「ん」の入れ方

一般的な IME と同じ挙動にしてあります。

| 打ち方 | 結果 |
| --- | --- |
| `n` ＋ 子音（`sensei`） | せんせい |
| `nn`（`gohann`） | ごはん |
| `nn` ＋ 母音（`konnichiha` / `onna`） | こんにちは / おんな |
| `nnn` ＋ 母音（`konnnichiha`） | こんにちは |
| `n'`（`hon'ya`） | ほんや |

促音も自動です（`itte` → いって、`kippu` → きっぷ、`hasshin` → はっしん）。

---

## 漢字変換について（正直な制限）

iOS は **かな漢字変換エンジンを外部アプリに開放していません**。Apple 純正キーボードが使っている
変換辞書を呼ぶ公開 API は存在しないため、このキーボードの漢字変換は
`KeyboardViewController.swift` 内の `JapaneseDictionary.words` に**登録した語だけ**が候補に出ます。

```swift
enum JapaneseDictionary {
    static let words: [String: [String]] = [
        "にほんご": ["日本語"],
        "かいぎ": ["会議"],
        // ここに増やしていけます
        "じぶんのなまえ": ["自分の名前"],
    ]
}
```

いまは常用語 80 語ほどを入れてあります。本格的にやるなら、
SKK / mozc などの公開辞書ファイルをアプリに同梱して、この辞書の読み込み元を
差し替えるのが現実的です（辞書ファイルのライセンスは要確認）。

ひらがな・カタカナ・英字の入力は辞書なしで完全に動きます。

---

## 見た目を変えたいとき

`KeyboardViewController.swift` の先頭にある `enum KB` をいじるだけで調整できます。

```swift
enum KB {
    static let keySpacing: CGFloat = 6            // キーの間隔
    static let gapOptions: [CGFloat] = [90, 150, 210, 280]   // 真ん中の空きの候補
    static let heightOptions: [CGFloat] = [270, 310, 350, 390] // 高さの候補
    static let japaneseSpace = " "                // "　" にすると全角スペース
}
```

キー配列そのものは `enum Layouts` の `left(_:)` / `right(_:)` を書き換えれば自由に変えられます。

---

## 既知の制限

- キー音・触覚フィードバックは付けていません（触覚はフルアクセスが必要なため）
- 変換中の文字はホスト側アプリに「未確定文字」としては渡していません（候補バー上に表示し、確定時にまとめて挿入します）。`UIInputViewController` には未確定文字を渡す公開 API がないためです
- 予測変換・学習機能はありません
