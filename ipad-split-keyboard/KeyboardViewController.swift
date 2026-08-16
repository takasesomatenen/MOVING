//
//  KeyboardViewController.swift
//  SplitKB — iPad 用 左右分割キーボード（ローマ字かな入力 / 英字入力）
//
//  使い方:
//  1. Xcode で iOS App プロジェクトを作る
//  2. File > New > Target… > Custom Keyboard Extension を追加
//  3. 自動生成された KeyboardViewController.swift の中身を全部消して、
//     このファイルの内容をまるごと貼り付ける
//  4. Deployment Target は iOS 15.0 以上にする
//
//  フルアクセスは不要です。
//

import UIKit
import SwiftUI

// MARK: - チューニング用の定数

enum KB {
    /// キーどうしの横の隙間
    static let keySpacing: CGFloat = 6
    /// 行どうしの縦の隙間
    static let rowSpacing: CGFloat = 6
    /// 左右パネルの内側の余白
    static let panelPadding: CGFloat = 8
    /// 真ん中の空きの幅（⟷ キーで切り替わる）
    static let gapOptions: [CGFloat] = [90, 150, 210, 280]
    /// キーボード全体の高さ（⇕ キーで切り替わる）
    static let heightOptions: [CGFloat] = [270, 310, 350, 390]
    /// 日本語モードで変換中でないときのスペース。全角にしたいときは "　" に変える
    static let japaneseSpace = " "
    /// パネルの角丸
    static let panelCorner: CGFloat = 16
    /// キーの角丸
    static let keyCorner: CGFloat = 8
}

// MARK: - ローマ字 → かな 変換テーブル

enum Romaji {

    private static let vowels: [String: String] = [
        "a": "あ", "i": "い", "u": "う", "e": "え", "o": "お",
        "yi": "い", "wu": "う",
    ]

    private static let kGroup: [String: String] = [
        "ka": "か", "ki": "き", "ku": "く", "ke": "け", "ko": "こ",
        "ga": "が", "gi": "ぎ", "gu": "ぐ", "ge": "げ", "go": "ご",
        "ca": "か", "cu": "く", "co": "こ",
    ]

    private static let sGroup: [String: String] = [
        "sa": "さ", "si": "し", "shi": "し", "su": "す", "se": "せ", "so": "そ",
        "za": "ざ", "zi": "じ", "ji": "じ", "zu": "ず", "ze": "ぜ", "zo": "ぞ",
    ]

    private static let tGroup: [String: String] = [
        "ta": "た", "ti": "ち", "chi": "ち", "tu": "つ", "tsu": "つ",
        "te": "て", "to": "と",
        "da": "だ", "di": "ぢ", "du": "づ", "de": "で", "do": "ど",
    ]

    private static let nGroup: [String: String] = [
        "na": "な", "ni": "に", "nu": "ぬ", "ne": "ね", "no": "の",
        "nn": "ん", "n'": "ん", "xn": "ん",
        // 「nn」の直後が母音・y のときは「ん＋な行」として扱う
        // （konnichiha → こんにちは、onna → おんな）
        "nna": "んな", "nni": "んに", "nnu": "んぬ", "nne": "んね", "nno": "んの",
        "nnya": "んにゃ", "nnyu": "んにゅ", "nnyo": "んにょ",
    ]

    private static let hGroup: [String: String] = [
        "ha": "は", "hi": "ひ", "hu": "ふ", "fu": "ふ", "he": "へ", "ho": "ほ",
        "ba": "ば", "bi": "び", "bu": "ぶ", "be": "べ", "bo": "ぼ",
        "pa": "ぱ", "pi": "ぴ", "pu": "ぷ", "pe": "ぺ", "po": "ぽ",
    ]

    private static let mGroup: [String: String] = [
        "ma": "ま", "mi": "み", "mu": "む", "me": "め", "mo": "も",
    ]

    private static let yGroup: [String: String] = [
        "ya": "や", "yu": "ゆ", "yo": "よ", "ye": "いぇ",
    ]

    private static let rGroup: [String: String] = [
        "ra": "ら", "ri": "り", "ru": "る", "re": "れ", "ro": "ろ",
    ]

    private static let wGroup: [String: String] = [
        "wa": "わ", "wo": "を", "wi": "うぃ", "we": "うぇ",
        "vu": "ヴ",
    ]

    private static let youon: [String: String] = [
        "kya": "きゃ", "kyi": "きぃ", "kyu": "きゅ", "kye": "きぇ", "kyo": "きょ",
        "gya": "ぎゃ", "gyi": "ぎぃ", "gyu": "ぎゅ", "gye": "ぎぇ", "gyo": "ぎょ",
        "sha": "しゃ", "shu": "しゅ", "she": "しぇ", "sho": "しょ",
        "sya": "しゃ", "syu": "しゅ", "sye": "しぇ", "syo": "しょ",
        "ja": "じゃ", "ju": "じゅ", "je": "じぇ", "jo": "じょ",
        "jya": "じゃ", "jyu": "じゅ", "jye": "じぇ", "jyo": "じょ",
        "zya": "じゃ", "zyu": "じゅ", "zye": "じぇ", "zyo": "じょ",
        "cha": "ちゃ", "chu": "ちゅ", "che": "ちぇ", "cho": "ちょ",
        "cya": "ちゃ", "cyu": "ちゅ", "cye": "ちぇ", "cyo": "ちょ",
        "tya": "ちゃ", "tyu": "ちゅ", "tye": "ちぇ", "tyo": "ちょ",
        "dya": "ぢゃ", "dyu": "ぢゅ", "dyo": "ぢょ",
        "nya": "にゃ", "nyu": "にゅ", "nye": "にぇ", "nyo": "にょ",
        "hya": "ひゃ", "hyu": "ひゅ", "hye": "ひぇ", "hyo": "ひょ",
        "bya": "びゃ", "byu": "びゅ", "bye": "びぇ", "byo": "びょ",
        "pya": "ぴゃ", "pyu": "ぴゅ", "pye": "ぴぇ", "pyo": "ぴょ",
        "mya": "みゃ", "myu": "みゅ", "mye": "みぇ", "myo": "みょ",
        "rya": "りゃ", "ryu": "りゅ", "rye": "りぇ", "ryo": "りょ",
    ]

    private static let foreign: [String: String] = [
        "fa": "ふぁ", "fi": "ふぃ", "fe": "ふぇ", "fo": "ふぉ",
        "fya": "ふゃ", "fyu": "ふゅ", "fyo": "ふょ",
        "va": "ヴぁ", "vi": "ヴぃ", "ve": "ヴぇ", "vo": "ヴぉ",
        "tsa": "つぁ", "tsi": "つぃ", "tse": "つぇ", "tso": "つぉ",
        "tha": "てゃ", "thi": "てぃ", "thu": "てゅ", "the": "てぇ", "tho": "てょ",
        "dha": "でゃ", "dhi": "でぃ", "dhu": "でゅ", "dhe": "でぇ", "dho": "でょ",
        "twu": "とぅ", "dwu": "どぅ",
        "wha": "うぁ", "who": "うぉ",
    ]

    private static let smalls: [String: String] = [
        "la": "ぁ", "li": "ぃ", "lu": "ぅ", "le": "ぇ", "lo": "ぉ",
        "xa": "ぁ", "xi": "ぃ", "xu": "ぅ", "xe": "ぇ", "xo": "ぉ",
        "lya": "ゃ", "lyu": "ゅ", "lyo": "ょ",
        "xya": "ゃ", "xyu": "ゅ", "xyo": "ょ",
        "ltu": "っ", "xtu": "っ", "ltsu": "っ", "xtsu": "っ",
        "lwa": "ゎ", "xwa": "ゎ",
        "lka": "ヵ", "lke": "ヶ",
    ]

    /// ローマ字 → かな の全テーブル
    static let table: [String: String] = {
        var merged: [String: String] = [:]
        let groups: [[String: String]] = [
            vowels, kGroup, sGroup, tGroup, nGroup, hGroup,
            mGroup, yGroup, rGroup, wGroup, youon, foreign, smalls,
        ]
        for group in groups {
            merged.merge(group) { current, _ in current }
        }
        return merged
    }()

    /// 「まだ入力が続く可能性がある」判定用の接頭辞集合
    static let prefixes: Set<String> = {
        var set = Set<String>()
        for key in table.keys {
            var partial = ""
            for ch in key {
                partial.append(ch)
                set.insert(partial)
            }
        }
        // "n" 単独は「ん」にも「な行」にもなりうるので、必ず次の入力を待つ
        set.insert("n")
        return set
    }()

    /// それ自体で変換できるが、さらに長い綴りの先頭でもあるもの（"nn" など）。
    /// これらは即確定せず、次の入力を待つ。
    static let ambiguous: Set<String> = {
        var set = Set<String>()
        let keys = Array(table.keys)
        for key in keys {
            for other in keys where other.count > key.count && other.hasPrefix(key) {
                set.insert(key)
                break
            }
        }
        return set
    }()

    private static let consonants = Set("bcdfghjklmpqrstvwxyz")

    static func isConsonant(_ ch: Character) -> Bool {
        return consonants.contains(ch)
    }

    /// 残ったローマ字断片を確定させるときの読み替え（"n" → "ん"）
    static func resolveTail(_ tail: String) -> String {
        if tail.isEmpty { return "" }
        if tail == "n" { return "ん" }
        if let kana = table[tail] { return kana }
        return tail
    }

    /// ひらがな → カタカナ
    static func toKatakana(_ text: String) -> String {
        var scalars = String.UnicodeScalarView()
        for u in text.unicodeScalars {
            if u.value >= 0x3041, u.value <= 0x3096, let k = Unicode.Scalar(u.value + 0x60) {
                scalars.append(k)
            } else {
                scalars.append(u)
            }
        }
        return String(scalars)
    }

    /// 半角 ASCII → 全角
    static func toFullWidth(_ text: String) -> String {
        var scalars = String.UnicodeScalarView()
        for u in text.unicodeScalars {
            if u.value == 0x20 {
                scalars.append(Unicode.Scalar(UInt32(0x3000))!)
            } else if u.value >= 0x21, u.value <= 0x7E, let f = Unicode.Scalar(u.value + 0xFEE0) {
                scalars.append(f)
            } else {
                scalars.append(u)
            }
        }
        return String(scalars)
    }
}

// MARK: - ローマ字入力エンジン

final class RomajiConverter {

    /// 確定済みのかな
    private(set) var kana: String = ""
    /// まだかなになっていないローマ字
    private(set) var buffer: String = ""
    /// 打ったローマ字そのまま（英字候補用）
    private(set) var rawLatin: String = ""

    var isEmpty: Bool {
        return kana.isEmpty && buffer.isEmpty
    }

    /// 入力中に画面へ出す文字列（かな＋未変換ローマ字）
    var display: String {
        return kana + buffer
    }

    /// 確定するときのひらがな（末尾の "n" は「ん」にする）
    var hiragana: String {
        return kana + Romaji.resolveTail(buffer)
    }

    func input(_ character: Character) {
        let lower = String(character).lowercased()
        buffer += lower
        rawLatin += lower
        resolve()
    }

    private func resolve() {
        while !buffer.isEmpty {
            // 1. そのまま変換できる（ただし "nn" のように続きがありうるものは待つ）
            if let converted = Romaji.table[buffer] {
                if !Romaji.ambiguous.contains(buffer) {
                    kana += converted
                    buffer = ""
                }
                return
            }
            // 2. 促音（kk, tt, ss …）
            let chars = Array(buffer)
            if chars.count >= 2,
               chars[0] == chars[1],
               chars[0] != "n",
               Romaji.isConsonant(chars[0]) {
                kana += "っ"
                buffer.removeFirst()
                continue
            }
            // 3. まだ続きがありうるので待つ
            if Romaji.prefixes.contains(buffer) {
                return
            }
            // 4. 行き止まり。"nn" は 2 文字まとめて「ん」にする（nnk → んk）
            if buffer.hasPrefix("nn") {
                kana += "ん"
                buffer.removeFirst(2)
                continue
            }
            // 5. 先頭 1 文字を吐き出して残りを再評価
            let head = String(buffer.removeFirst())
            kana += Romaji.resolveTail(head)
        }
    }

    /// 長音「ー」など、変換を挟まずにそのまま変換中の文字へ足したいとき
    func appendKana(_ text: String, latin: String) {
        kana += Romaji.resolveTail(buffer) + text
        buffer = ""
        rawLatin += latin
    }

    /// 変換中の文字を 1 文字消す。消すものが無ければ false
    @discardableResult
    func deleteBackward() -> Bool {
        if !buffer.isEmpty {
            buffer.removeLast()
            if !rawLatin.isEmpty { rawLatin.removeLast() }
            return true
        }
        if !kana.isEmpty {
            kana.removeLast()
            if !rawLatin.isEmpty { rawLatin.removeLast() }
            return true
        }
        return false
    }

    func clear() {
        kana = ""
        buffer = ""
        rawLatin = ""
    }

    /// 変換候補を作る
    func candidates() -> [String] {
        let reading = hiragana
        if reading.isEmpty { return [] }

        var list: [String] = [reading]

        // ユーザー辞書（下の JapaneseDictionary を編集すれば語を増やせます）
        if let hits = JapaneseDictionary.words[reading] {
            list.append(contentsOf: hits)
        }

        list.append(Romaji.toKatakana(reading))

        if !rawLatin.isEmpty {
            list.append(rawLatin)
            list.append(rawLatin.uppercased())
            list.append(Romaji.toFullWidth(rawLatin))
        }

        // 重複を消しつつ順番は保つ
        var seen = Set<String>()
        var unique: [String] = []
        for item in list where !item.isEmpty {
            if seen.insert(item).inserted {
                unique.append(item)
            }
        }
        return unique
    }
}

// MARK: - 簡易辞書
//
//  iOS はかな漢字変換エンジンを外部アプリに開放していません。
//  そのため漢字は「ここに登録した語」だけが候補に出ます。
//  よく使う単語をここに足していってください。
//
enum JapaneseDictionary {
    static let words: [String: [String]] = [
        "わたし": ["私"], "あなた": ["貴方"], "ぼく": ["僕"],
        "にほん": ["日本"], "にほんご": ["日本語"], "えいご": ["英語"],
        "とうきょう": ["東京"], "おおさか": ["大阪"], "きょうと": ["京都"],
        "きょう": ["今日"], "あした": ["明日"], "きのう": ["昨日"],
        "じかん": ["時間"], "ねん": ["年"], "つき": ["月"], "しゅう": ["週"],
        "ひと": ["人"], "しごと": ["仕事"], "かいしゃ": ["会社"],
        "がっこう": ["学校"], "せんせい": ["先生"], "がくせい": ["学生"],
        "でんわ": ["電話"], "でんしゃ": ["電車"], "くるま": ["車"],
        "いえ": ["家"], "みず": ["水"], "ごはん": ["ご飯"],
        "たべる": ["食べる"], "のむ": ["飲む"], "いく": ["行く"],
        "くる": ["来る"], "みる": ["見る"], "きく": ["聞く"],
        "はなす": ["話す"], "よむ": ["読む"], "かく": ["書く"],
        "おもう": ["思う"], "しる": ["知る"], "つくる": ["作る"],
        "おおきい": ["大きい"], "ちいさい": ["小さい"],
        "あたらしい": ["新しい"], "ふるい": ["古い"],
        "たかい": ["高い"], "やすい": ["安い"],
        "ありがとう": ["有難う"], "おはよう": ["お早う"],
        "こんにちは": ["今日は"], "こんばんは": ["今晩は"],
        "すみません": ["済みません"], "ください": ["下さい"],
        "おねがい": ["お願い"], "よろしく": ["宜しく"],
        "しつれい": ["失礼"], "だいじょうぶ": ["大丈夫"],
        "もんだい": ["問題"], "しつもん": ["質問"], "へんじ": ["返事"],
        "れんらく": ["連絡"], "かいぎ": ["会議"], "しりょう": ["資料"],
        "ないよう": ["内容"], "かくにん": ["確認"], "ほうこく": ["報告"],
        "そうだん": ["相談"], "よてい": ["予定"], "じゅんび": ["準備"],
        "かんせい": ["完成"], "しゅうせい": ["修正"], "へんこう": ["変更"],
        "ついか": ["追加"], "さくじょ": ["削除"], "ほぞん": ["保存"],
        "せってい": ["設定"], "がめん": ["画面"], "にゅうりょく": ["入力"],
        "へんかん": ["変換"], "けんさく": ["検索"], "ひらく": ["開く"],
        "とじる": ["閉じる"], "かんたん": ["簡単"], "べんり": ["便利"],
    ]
}

// MARK: - キーの定義

enum InputMode {
    case japanese
    case english

    var label: String {
        switch self {
        case .japanese: return "あ"
        case .english: return "A"
        }
    }
}

enum KeyLayer {
    case letters
    case numbers
    case symbols
}

enum ShiftState {
    case off
    case on
    case capsLock

    var isActive: Bool {
        return self != .off
    }
}

enum KeyAction: Equatable {
    case char(String)
    case backspace
    case space
    case ret
    case shift
    case layer(KeyLayer)
    case modeToggle
    case globe
    case dismiss
    case candidate(Int)
    case cycleGap
    case cycleHeight
}

enum KeyStyle {
    case normal
    case special
}

struct KeyCap {
    var label: String
    var action: KeyAction
    var weight: CGFloat = 1
    var style: KeyStyle = .normal
    var highlighted: Bool = false
    var fontSize: CGFloat = 20
}

// MARK: - 画面の状態

final class KeyboardModel: ObservableObject {
    @Published var mode: InputMode = .japanese
    @Published var layer: KeyLayer = .letters
    @Published var shift: ShiftState = .off
    @Published var reading: String = ""
    @Published var candidates: [String] = []
    @Published var selected: Int = 0
    @Published var gapIndex: Int = 1
    @Published var heightIndex: Int = 1
    @Published var showsGlobeKey: Bool = true

    var gap: CGFloat {
        return KB.gapOptions[min(max(gapIndex, 0), KB.gapOptions.count - 1)]
    }

    var height: CGFloat {
        return KB.heightOptions[min(max(heightIndex, 0), KB.heightOptions.count - 1)]
    }

    var isComposing: Bool {
        return !reading.isEmpty
    }
}

// MARK: - キー配列

enum Layouts {

    static func left(_ model: KeyboardModel) -> [[KeyCap]] {
        switch model.layer {
        case .letters:
            return [
                letterRow(["q", "w", "e", "r", "t"], model),
                letterRow(["a", "s", "d", "f", "g"], model),
                [shiftKey(model)] + letterRow(["z", "x", "c", "v", "b"], model),
                bottomLeft(model),
            ]
        case .numbers:
            return [
                plainRow(["1", "2", "3", "4", "5"]),
                plainRow(["-", "/", ":", ";", "("]),
                [layerKey("#+=", .symbols)] + plainRow([".", ",", "?", "!"]),
                bottomLeft(model),
            ]
        case .symbols:
            return [
                plainRow(["[", "]", "{", "}", "#"]),
                plainRow(["_", "\\", "|", "~", "<"]),
                [layerKey("123", .numbers)] + plainRow(["。", "、", "？", "！"]),
                bottomLeft(model),
            ]
        }
    }

    static func right(_ model: KeyboardModel) -> [[KeyCap]] {
        switch model.layer {
        case .letters:
            return [
                letterRow(["y", "u", "i", "o", "p"], model) + [backspaceKey()],
                letterRow(["h", "j", "k", "l"], model) + [returnKey(model)],
                letterRow(["n", "m"], model) + punctuationKeys(model) + [shiftKey(model)],
                bottomRight(model),
            ]
        case .numbers:
            return [
                plainRow(["6", "7", "8", "9", "0"]) + [backspaceKey()],
                plainRow([")", "¥", "&", "@", "\""]) + [returnKey(model)],
                plainRow(["'", "「", "」", "・"]) + [layerKey("#+=", .symbols)],
                bottomRight(model),
            ]
        case .symbols:
            return [
                plainRow(["%", "^", "*", "+", "="]) + [backspaceKey()],
                plainRow([">", "$", "€", "£", "•"]) + [returnKey(model)],
                plainRow(["〜", "【", "】", "…"]) + [layerKey("123", .numbers)],
                bottomRight(model),
            ]
        }
    }

    // MARK: 部品

    private static func letterRow(_ letters: [String], _ model: KeyboardModel) -> [KeyCap] {
        return letters.map { letter in
            let shown = model.shift.isActive ? letter.uppercased() : letter
            return KeyCap(label: shown, action: .char(letter))
        }
    }

    private static func plainRow(_ items: [String]) -> [KeyCap] {
        return items.map { KeyCap(label: $0, action: .char($0), fontSize: 18) }
    }

    private static func punctuationKeys(_ model: KeyboardModel) -> [KeyCap] {
        if model.mode == .japanese {
            return [
                KeyCap(label: "、", action: .char(","), fontSize: 18),
                KeyCap(label: "。", action: .char("."), fontSize: 18),
                KeyCap(label: "ー", action: .char("-"), fontSize: 18),
            ]
        }
        return [
            KeyCap(label: ",", action: .char(","), fontSize: 18),
            KeyCap(label: ".", action: .char("."), fontSize: 18),
            KeyCap(label: "'", action: .char("'"), fontSize: 18),
        ]
    }

    private static func layerKey(_ label: String, _ target: KeyLayer) -> KeyCap {
        return KeyCap(label: label, action: .layer(target),
                      weight: 1.4, style: .special, fontSize: 16)
    }

    private static func shiftKey(_ model: KeyboardModel) -> KeyCap {
        let label = (model.shift == .capsLock) ? "⇪" : "⇧"
        return KeyCap(label: label,
                      action: .shift,
                      weight: 1.5,
                      style: .special,
                      highlighted: model.shift.isActive,
                      fontSize: 20)
    }

    private static func backspaceKey() -> KeyCap {
        return KeyCap(label: "⌫", action: .backspace, weight: 1.5, style: .special, fontSize: 20)
    }

    private static func returnKey(_ model: KeyboardModel) -> KeyCap {
        let label = model.isComposing ? "確定" : "改行"
        return KeyCap(label: label, action: .ret, weight: 1.8, style: .special, fontSize: 15)
    }

    private static func spaceKey(_ model: KeyboardModel) -> KeyCap {
        let label = model.isComposing ? "変換" : "空白"
        return KeyCap(label: label, action: .space, weight: 3, style: .normal, fontSize: 14)
    }

    private static func bottomLeft(_ model: KeyboardModel) -> [KeyCap] {
        var row: [KeyCap] = []
        if model.layer == .letters {
            row.append(layerKey("123", .numbers))
        } else {
            row.append(layerKey("ABC", .letters))
        }
        if model.showsGlobeKey {
            row.append(KeyCap(label: "🌐", action: .globe, weight: 1.2, style: .special, fontSize: 18))
        }
        row.append(KeyCap(label: "⟷", action: .cycleGap, weight: 1.2, style: .special, fontSize: 18))
        row.append(spaceKey(model))
        return row
    }

    private static func bottomRight(_ model: KeyboardModel) -> [KeyCap] {
        var row: [KeyCap] = []
        row.append(spaceKey(model))
        row.append(KeyCap(label: model.mode.label, action: .modeToggle,
                          weight: 1.4, style: .special,
                          highlighted: model.mode == .japanese, fontSize: 18))
        row.append(KeyCap(label: "⇕", action: .cycleHeight, weight: 1.2, style: .special, fontSize: 18))
        row.append(KeyCap(label: "⌨︎▾", action: .dismiss, weight: 1.4, style: .special, fontSize: 15))
        return row
    }
}

// MARK: - キー 1 個

struct KeyButton: View {
    let key: KeyCap
    let onKey: (KeyAction) -> Void

    @State private var pressed = false
    @State private var didRepeat = false
    @State private var delayTimer: Timer?
    @State private var repeatTimer: Timer?

    var body: some View {
        ZStack {
            RoundedRectangle(cornerRadius: KB.keyCorner, style: .continuous)
                .fill(fillColor)
                .overlay(
                    RoundedRectangle(cornerRadius: KB.keyCorner, style: .continuous)
                        .stroke(Color.black.opacity(0.08), lineWidth: 0.5)
                )
            Text(key.label)
                .font(.system(size: key.fontSize))
                .foregroundColor(textColor)
                .lineLimit(1)
                .minimumScaleFactor(0.5)
                .padding(.horizontal, 2)
        }
        .frame(maxHeight: .infinity)
        .contentShape(RoundedRectangle(cornerRadius: KB.keyCorner, style: .continuous))
        .gesture(
            DragGesture(minimumDistance: 0)
                .onChanged { _ in self.beginPress() }
                .onEnded { _ in self.endPress() }
        )
        .onDisappear { self.cancelTimers() }
    }

    private var fillColor: Color {
        if pressed {
            return Color(UIColor.systemGray3)
        }
        if key.highlighted {
            return Color.accentColor.opacity(0.85)
        }
        switch key.style {
        case .normal:
            return Color(UIColor.secondarySystemGroupedBackground)
        case .special:
            return Color(UIColor.systemGray4)
        }
    }

    private var textColor: Color {
        if key.highlighted && !pressed {
            return Color.white
        }
        return Color(UIColor.label)
    }

    private func beginPress() {
        guard !pressed else { return }
        pressed = true
        didRepeat = false
        guard key.action == .backspace else { return }
        delayTimer?.invalidate()
        delayTimer = Timer.scheduledTimer(withTimeInterval: 0.45, repeats: false) { _ in
            self.repeatTimer?.invalidate()
            self.repeatTimer = Timer.scheduledTimer(withTimeInterval: 0.09, repeats: true) { _ in
                self.didRepeat = true
                self.onKey(.backspace)
            }
        }
    }

    private func endPress() {
        guard pressed else { return }
        pressed = false
        cancelTimers()
        if !didRepeat {
            onKey(key.action)
        }
        didRepeat = false
    }

    private func cancelTimers() {
        delayTimer?.invalidate()
        delayTimer = nil
        repeatTimer?.invalidate()
        repeatTimer = nil
    }
}

// MARK: - 1 行

struct KeyRow: View {
    let keys: [KeyCap]
    let onKey: (KeyAction) -> Void

    var body: some View {
        GeometryReader { geo in
            HStack(spacing: KB.keySpacing) {
                ForEach(Array(self.keys.enumerated()), id: \.offset) { pair in
                    KeyButton(key: pair.element, onKey: self.onKey)
                        .frame(width: self.width(for: pair.element, total: geo.size.width))
                }
            }
        }
    }

    private func width(for key: KeyCap, total: CGFloat) -> CGFloat {
        let weights = keys.reduce(CGFloat(0)) { $0 + $1.weight }
        let gaps = KB.keySpacing * CGFloat(max(keys.count - 1, 0))
        let unit = (total - gaps) / max(weights, 0.001)
        return max(unit * key.weight, 1)
    }
}

// MARK: - 片側のパネル

struct KeyPanel: View {
    let rows: [[KeyCap]]
    let onKey: (KeyAction) -> Void

    var body: some View {
        VStack(spacing: KB.rowSpacing) {
            ForEach(Array(rows.enumerated()), id: \.offset) { pair in
                KeyRow(keys: pair.element, onKey: self.onKey)
            }
        }
        .padding(KB.panelPadding)
        .background(
            RoundedRectangle(cornerRadius: KB.panelCorner, style: .continuous)
                .fill(Color(UIColor.systemGray5))
                .shadow(color: Color.black.opacity(0.15), radius: 8, x: 0, y: 3)
        )
    }
}

// MARK: - 変換候補バー

struct CandidateBar: View {
    @ObservedObject var model: KeyboardModel
    let onKey: (KeyAction) -> Void

    var body: some View {
        HStack(spacing: 8) {
            if model.isComposing {
                Text(model.reading)
                    .font(.system(size: 15))
                    .foregroundColor(Color(UIColor.secondaryLabel))
                    .padding(.horizontal, 10)
                    .padding(.vertical, 5)
                    .background(Capsule().fill(Color(UIColor.systemGray5)))

                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 6) {
                        ForEach(Array(model.candidates.enumerated()), id: \.offset) { pair in
                            self.chip(index: pair.offset, text: pair.element)
                        }
                    }
                    .padding(.horizontal, 2)
                }
            } else {
                Text(model.mode == .japanese ? "日本語（ローマ字）" : "English")
                    .font(.system(size: 13))
                    .foregroundColor(Color(UIColor.secondaryLabel))
                    .padding(.horizontal, 10)
                    .padding(.vertical, 5)
                    .background(Capsule().fill(Color(UIColor.systemGray5).opacity(0.7)))
                Spacer(minLength: 0)
            }
        }
        .frame(height: 38)
    }

    private func chip(index: Int, text: String) -> some View {
        Button(action: { self.onKey(.candidate(index)) }) {
            Text(text)
                .font(.system(size: 17))
                .foregroundColor(index == model.selected ? Color.white : Color(UIColor.label))
                .padding(.horizontal, 12)
                .padding(.vertical, 5)
                .background(
                    Capsule().fill(index == model.selected
                                   ? Color.accentColor
                                   : Color(UIColor.secondarySystemGroupedBackground))
                )
        }
        .buttonStyle(PlainButtonStyle())
    }
}

// MARK: - キーボード全体

struct SplitKeyboardView: View {
    @ObservedObject var model: KeyboardModel
    let onKey: (KeyAction) -> Void

    var body: some View {
        VStack(spacing: 6) {
            CandidateBar(model: model, onKey: onKey)
            HStack(spacing: 0) {
                LeftHalf(model: model, onKey: onKey)
                // ここが「真ん中の空き」。背景を敷いていないので下のアプリが透けます
                Color.clear.frame(width: model.gap)
                RightHalf(model: model, onKey: onKey)
            }
        }
        .padding(.horizontal, 10)
        .padding(.top, 4)
        .padding(.bottom, 8)
    }
}

/// 左パネル（型チェックを軽くするために分離）
struct LeftHalf: View {
    @ObservedObject var model: KeyboardModel
    let onKey: (KeyAction) -> Void

    var body: some View {
        KeyPanel(rows: Layouts.left(model), onKey: onKey)
    }
}

/// 右パネル
struct RightHalf: View {
    @ObservedObject var model: KeyboardModel
    let onKey: (KeyAction) -> Void

    var body: some View {
        KeyPanel(rows: Layouts.right(model), onKey: onKey)
    }
}

// MARK: - キーボード本体（UIInputViewController）

class KeyboardViewController: UIInputViewController {

    private let model = KeyboardModel()
    private let converter = RomajiConverter()
    private var heightConstraint: NSLayoutConstraint?

    private let gapKey = "SplitKB.gapIndex"
    private let heightKey = "SplitKB.heightIndex"

    // MARK: ライフサイクル

    override func viewDidLoad() {
        super.viewDidLoad()

        let defaults = UserDefaults.standard
        if defaults.object(forKey: gapKey) != nil {
            model.gapIndex = defaults.integer(forKey: gapKey)
        }
        if defaults.object(forKey: heightKey) != nil {
            model.heightIndex = defaults.integer(forKey: heightKey)
        }
        model.showsGlobeKey = needsInputModeSwitchKey

        view.backgroundColor = .clear

        let root = SplitKeyboardView(model: model) { [weak self] action in
            self?.handle(action)
        }
        let hosting = UIHostingController(rootView: root)
        addChild(hosting)
        hosting.view.translatesAutoresizingMaskIntoConstraints = false
        hosting.view.backgroundColor = .clear
        view.addSubview(hosting.view)
        NSLayoutConstraint.activate([
            hosting.view.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            hosting.view.trailingAnchor.constraint(equalTo: view.trailingAnchor),
            hosting.view.topAnchor.constraint(equalTo: view.topAnchor),
            hosting.view.bottomAnchor.constraint(equalTo: view.bottomAnchor),
        ])
        hosting.didMove(toParent: self)

        applyHeight()
    }

    override func viewWillAppear(_ animated: Bool) {
        super.viewWillAppear(animated)
        model.showsGlobeKey = needsInputModeSwitchKey
        applyHeight()
    }

    override func textDidChange(_ textInput: UITextInput?) {
        super.textDidChange(textInput)
        model.showsGlobeKey = needsInputModeSwitchKey
    }

    private func applyHeight() {
        heightConstraint?.isActive = false
        let constraint = view.heightAnchor.constraint(equalToConstant: model.height)
        constraint.priority = UILayoutPriority(999)
        constraint.isActive = true
        heightConstraint = constraint
    }

    // MARK: キー処理

    private func handle(_ action: KeyAction) {
        switch action {
        case .char(let text):
            handleCharacter(text)

        case .backspace:
            if converter.deleteBackward() {
                refreshComposition()
            } else {
                textDocumentProxy.deleteBackward()
            }

        case .space:
            handleSpace()

        case .ret:
            if model.isComposing {
                commitComposition()
            } else {
                textDocumentProxy.insertText("\n")
            }

        case .shift:
            switch model.shift {
            case .off: model.shift = .on
            case .on: model.shift = .capsLock
            case .capsLock: model.shift = .off
            }

        case .layer(let target):
            model.layer = target

        case .modeToggle:
            commitComposition()
            model.mode = (model.mode == .japanese) ? .english : .japanese
            model.layer = .letters

        case .globe:
            commitComposition()
            advanceToNextInputMode()

        case .dismiss:
            commitComposition()
            dismissKeyboard()

        case .candidate(let index):
            guard index >= 0, index < model.candidates.count else { return }
            model.selected = index
            commitComposition()

        case .cycleGap:
            model.gapIndex = (model.gapIndex + 1) % KB.gapOptions.count
            UserDefaults.standard.set(model.gapIndex, forKey: gapKey)

        case .cycleHeight:
            model.heightIndex = (model.heightIndex + 1) % KB.heightOptions.count
            UserDefaults.standard.set(model.heightIndex, forKey: heightKey)
            applyHeight()
        }
    }

    private func handleCharacter(_ text: String) {
        let shifted = model.shift.isActive ? text.uppercased() : text

        if model.mode == .japanese, model.layer == .letters {
            if let ch = text.lowercased().first, ch.isASCII, ch.isLetter {
                converter.input(ch)
                refreshComposition()
                consumeShift()
                return
            }
            // 長音「ー」は変換中の文字にそのまま続ける（konpyu-ta → こんぴゅーた）
            if text == "-", model.isComposing {
                converter.appendKana("ー", latin: "-")
                refreshComposition()
                consumeShift()
                return
            }
            // それ以外の記号は、変換中の文字を確定してから入れる
            commitComposition()
            textDocumentProxy.insertText(japanesePunctuation(shifted))
            consumeShift()
            return
        }

        commitComposition()
        textDocumentProxy.insertText(shifted)
        consumeShift()
    }

    private func handleSpace() {
        if model.isComposing {
            guard !model.candidates.isEmpty else { return }
            model.selected = (model.selected + 1) % model.candidates.count
            return
        }
        let space = (model.mode == .japanese) ? KB.japaneseSpace : " "
        textDocumentProxy.insertText(space)
    }

    private func japanesePunctuation(_ text: String) -> String {
        switch text {
        case ",": return "、"
        case ".": return "。"
        case "-": return "ー"
        case "?": return "？"
        case "!": return "！"
        case "~": return "〜"
        default: return text
        }
    }

    private func consumeShift() {
        if model.shift == .on {
            model.shift = .off
        }
    }

    private func refreshComposition() {
        model.reading = converter.display
        model.candidates = model.reading.isEmpty ? [] : converter.candidates()
        model.selected = 0
    }

    private func commitComposition() {
        guard model.isComposing else { return }
        let text: String
        if model.selected >= 0, model.selected < model.candidates.count {
            text = model.candidates[model.selected]
        } else {
            text = converter.hiragana
        }
        textDocumentProxy.insertText(text)
        converter.clear()
        model.reading = ""
        model.candidates = []
        model.selected = 0
    }
}
