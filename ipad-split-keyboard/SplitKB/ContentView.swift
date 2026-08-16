//
//  ContentView.swift
//  SplitKB（本体アプリ）
//
//  キーボードの動作確認用。App ターゲットの ContentView.swift に貼り付けてください。
//  本体アプリ自体には機能はなく、キーボードを試すための入力欄を置いているだけです。
//

import SwiftUI

struct ContentView: View {
    @State private var text: String = ""

    var body: some View {
        NavigationView {
            VStack(alignment: .leading, spacing: 16) {
                Text("ここをタップして、🌐 キーで「SplitKB」に切り替えてください。")
                    .font(.callout)
                    .foregroundColor(.secondary)

                TextEditor(text: $text)
                    .font(.system(size: 20))
                    .padding(8)
                    .background(
                        RoundedRectangle(cornerRadius: 12)
                            .stroke(Color.secondary.opacity(0.4), lineWidth: 1)
                    )

                setupSteps

                Spacer(minLength: 0)
            }
            .padding(20)
            .navigationTitle("SplitKB")
        }
        .navigationViewStyle(StackNavigationViewStyle())
    }

    private var setupSteps: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("初回だけ必要な設定")
                .font(.headline)
            Text("設定 → 一般 → キーボード → キーボード → 新しいキーボードを追加… → SplitKB")
                .font(.footnote)
                .foregroundColor(.secondary)
            Text("フルアクセスは不要です。")
                .font(.footnote)
                .foregroundColor(.secondary)
        }
    }
}

struct ContentView_Previews: PreviewProvider {
    static var previews: some View {
        ContentView()
    }
}
