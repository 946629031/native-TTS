import SwiftUI

extension BackendModel.Status {
    var label: String {
        switch self {
        case .idle: return "未启动"
        case .starting: return "模型加载中…"
        case .ready: return "模型就绪"
        case .failed: return "启动失败"
        }
    }

    var color: Color {
        switch self {
        case .idle: return .secondary
        case .starting: return .orange
        case .ready: return .green
        case .failed: return .red
        }
    }

    var isFailed: Bool {
        if case .failed = self { return true }
        return false
    }
}

struct ContentView: View {
    @ObservedObject var model: BackendModel
    @FocusState private var textFocused: Bool

    private var selectedVoiceDesc: String {
        model.voices.first(where: { $0.name == model.voice })?.desc ?? ""
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            header
            editor
            options
            actions
            if let message = model.message {
                Text(message)
                    .font(.system(size: 11))
                    .foregroundStyle(.red)
                    .lineLimit(3)
                    .fixedSize(horizontal: false, vertical: true)
            }
            Divider()
            footer
        }
        .padding(14)
        .frame(width: 380)
        .background(Color(nsColor: .windowBackgroundColor))
        .onAppear { textFocused = true }
    }

    private var header: some View {
        HStack(spacing: 7) {
            Circle()
                .fill(model.status.color)
                .frame(width: 7, height: 7)
            Text("native-TTS")
                .font(.system(size: 13, weight: .semibold))
            Spacer()
            Text(model.status.label)
                .font(.system(size: 11))
                .foregroundStyle(.secondary)
            if model.status.isFailed {
                Button("重试") { model.retry() }
                    .buttonStyle(.link)
                    .font(.system(size: 11))
            }
        }
    }

    private var editor: some View {
        TextEditor(text: $model.text)
            .font(.system(size: 13))
            .scrollContentBackground(.hidden)
            .focused($textFocused)
            .padding(6)
            .frame(height: 88)
            .background(
                RoundedRectangle(cornerRadius: 8)
                    .fill(Color(nsColor: .textBackgroundColor))
            )
            .overlay(alignment: .topLeading) {
                if model.text.isEmpty {
                    Text("输入要朗读的文字，中英混排都可以…")
                        .font(.system(size: 13))
                        .foregroundStyle(.tertiary)
                        .padding(.top, 12)
                        .padding(.leading, 11)
                        .allowsHitTesting(false)
                }
            }
            .overlay(
                RoundedRectangle(cornerRadius: 8)
                    .strokeBorder(Color(nsColor: .separatorColor), lineWidth: 1)
            )
    }

    private var options: some View {
        VStack(alignment: .leading, spacing: 3) {
            HStack(spacing: 10) {
                Picker("音色", selection: $model.voice) {
                    ForEach(model.voices) { voice in
                        Text(voice.name).tag(voice.name)
                    }
                }
                .labelsHidden()
                .frame(width: 128)

                Toggle("文本规范化", isOn: $model.normalize)
                    .toggleStyle(.checkbox)
                    .font(.system(size: 12))

                Spacer()

                if let duration = model.lastDuration {
                    Text(String(format: "%.1f 秒", duration))
                        .font(.system(size: 11))
                        .foregroundStyle(.secondary)
                }
            }
            if !selectedVoiceDesc.isEmpty {
                Text(selectedVoiceDesc)
                    .font(.system(size: 10.5))
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
                    .padding(.leading, 2)
            }
        }
    }

    private var actions: some View {
        HStack(spacing: 8) {
            Button {
                model.speak()
            } label: {
                Label(model.busy ? "生成中…" : "朗读", systemImage: "play.fill")
            }
            .keyboardShortcut(.return, modifiers: [.command])
            .buttonStyle(.borderedProminent)
            .disabled(!model.canSpeak)

            Button {
                model.speakClipboard()
            } label: {
                Label("剪贴板", systemImage: "doc.on.clipboard")
            }
            .disabled(model.status != .ready)

            if model.playing {
                Button {
                    model.stopPlayback()
                } label: {
                    Label("停止", systemImage: "stop.fill")
                }
            }

            Spacer()
        }
    }

    private var footer: some View {
        HStack {
            Button("打开网页版") { model.openWeb() }
                .buttonStyle(.link)
                .font(.system(size: 12))
            Spacer()
            Button("退出") { NSApp.terminate(nil) }
                .buttonStyle(.link)
                .font(.system(size: 12))
        }
    }
}
