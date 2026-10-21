import AVFoundation
import AppKit
import Combine
import Foundation

struct Voice: Decodable, Identifiable, Equatable {
    let name: String
    let desc: String
    let native: String
    var id: String { name }
}

private struct Health: Decodable {
    let status: String
    let error: String?
}

private struct TTSResult: Decodable {
    let id: String
    let path: String
    let duration: Double
    let voice: String
}

private struct APIError: Decodable {
    let error: String
}

enum AppPaths {
    /// 优先用 build.sh 写进 Info.plist 的仓库路径；找不到就向上找 app/server.py。
    static var repo: URL {
        if let path = Bundle.main.object(forInfoDictionaryKey: "NativeTTSRepoPath") as? String,
           !path.isEmpty {
            return URL(fileURLWithPath: path)
        }
        var url = Bundle.main.bundleURL
        for _ in 0..<5 {
            url.deleteLastPathComponent()
            if FileManager.default.fileExists(atPath: url.appendingPathComponent("app/server.py").path) {
                return url
            }
        }
        return URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
    }
}

@MainActor
final class BackendModel: ObservableObject {
    enum Status: Equatable {
        case idle
        case starting
        case ready
        case failed(String)
    }

    static let fallbackVoices: [Voice] = [
        Voice(name: "Vivian", desc: "年轻女声，明亮", native: "中文"),
        Voice(name: "Serena", desc: "年轻女声，温暖柔和", native: "中文"),
        Voice(name: "Uncle_Fu", desc: "成熟男声，低沉醇厚", native: "中文"),
        Voice(name: "Dylan", desc: "年轻男声，清亮自然", native: "中文（北京）"),
        Voice(name: "Eric", desc: "男声，活泼、略带沙哑", native: "中文（四川）"),
        Voice(name: "Ryan", desc: "男声，节奏感强", native: "英文"),
        Voice(name: "Aiden", desc: "美式男声，阳光清晰", native: "英文"),
        Voice(name: "Ono_Anna", desc: "日系女声，轻快俏皮", native: "日文"),
        Voice(name: "Sohee", desc: "韩系女声，温暖有情绪", native: "韩文"),
    ]

    @Published var status: Status = .idle
    @Published var voices: [Voice] = BackendModel.fallbackVoices
    @Published var voice = "Serena"
    @Published var normalize = true
    @Published var text = ""
    @Published var busy = false
    @Published var playing = false
    @Published var message: String?
    @Published var lastDuration: Double?

    let repo: URL
    let base = URL(string: "http://127.0.0.1:8765")!

    private var instruct = ""
    private var bootstrapped = false
    private var serverProcess: Process?
    private var logHandle: FileHandle?
    private var player: AVAudioPlayer?
    private var playbackTask: Task<Void, Never>?
    private var monitorTask: Task<Void, Never>?

    private lazy var session: URLSession = {
        let config = URLSessionConfiguration.ephemeral
        config.timeoutIntervalForRequest = 2
        config.timeoutIntervalForResource = 300
        return URLSession(configuration: config)
    }()

    init(repo: URL = AppPaths.repo) {
        self.repo = repo
        loadConfig()
    }

    var canSpeak: Bool {
        guard case .ready = status, !busy else { return false }
        return !text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }

    // MARK: - 启动

    func bootstrap() {
        guard !bootstrapped else { return }
        bootstrapped = true
        startMonitorIfNeeded()
        Task { await boot() }
    }

    func retry() {
        bootstrapped = false
        message = nil
        status = .idle
        bootstrap()
    }

    /// 后台服务被手动杀掉或崩溃时，自动拉回来
    private func startMonitorIfNeeded() {
        guard monitorTask == nil else { return }
        monitorTask = Task { [weak self] in
            while !Task.isCancelled {
                try? await Task.sleep(nanoseconds: 5_000_000_000)
                guard let self else { return }
                guard case .ready = self.status else { continue }
                if await self.fetchHealth() == nil {
                    self.status = .starting
                    self.bootstrapped = false
                    self.bootstrap()
                }
            }
        }
    }

    private func boot() async {
        var alreadyLoading = false

        if let health = await fetchHealth() {
            switch health.status {
            case "ready":
                status = .ready
                await loadVoices()
                return
            case "error":
                status = .failed(health.error ?? "模型加载失败")
                return
            default:
                alreadyLoading = true
            }
        }

        status = .starting
        if !alreadyLoading {
            startServer()
            if case .failed = status { return }
        }

        for _ in 0..<120 {  // 最多等 60 秒
            try? await Task.sleep(nanoseconds: 500_000_000)
            guard let health = await fetchHealth() else { continue }
            switch health.status {
            case "ready":
                status = .ready
                await loadVoices()
                return
            case "error":
                status = .failed(health.error ?? "模型加载失败")
                return
            default:
                continue
            }
        }
        status = .failed("启动超时，详见 /tmp/native-tts-server.log")
    }

    private func startServer() {
        let python = repo.appendingPathComponent(".venv/bin/python")
        let script = repo.appendingPathComponent("app/server.py")

        guard FileManager.default.isExecutableFile(atPath: python.path),
              FileManager.default.fileExists(atPath: script.path) else {
            status = .failed("找不到 .venv 或 app/server.py\n仓库路径：\(repo.path)")
            return
        }
        if let process = serverProcess, process.isRunning { return }

        let process = Process()
        process.executableURL = python
        process.arguments = [script.path]
        process.currentDirectoryURL = repo

        let logURL = URL(fileURLWithPath: "/tmp/native-tts-server.log")
        if !FileManager.default.fileExists(atPath: logURL.path) {
            FileManager.default.createFile(atPath: logURL.path, contents: nil)
        }
        if let handle = try? FileHandle(forWritingTo: logURL) {
            handle.seekToEndOfFile()
            process.standardOutput = handle
            process.standardError = handle
            logHandle = handle
        }

        do {
            try process.run()
            serverProcess = process
        } catch {
            status = .failed("启动后台服务失败：\(error.localizedDescription)")
        }
    }

    private func fetchHealth() async -> Health? {
        var request = URLRequest(url: base.appendingPathComponent("api/health"))
        request.timeoutInterval = 1
        do {
            let (data, _) = try await session.data(for: request)
            return try JSONDecoder().decode(Health.self, from: data)
        } catch {
            return nil
        }
    }

    private func loadVoices() async {
        var request = URLRequest(url: base.appendingPathComponent("api/voices"))
        request.timeoutInterval = 5
        do {
            let (data, _) = try await session.data(for: request)
            let list = try JSONDecoder().decode([Voice].self, from: data)
            if !list.isEmpty { voices = list }
            if !voices.contains(where: { $0.name == voice }) { voice = "Serena" }
        } catch {
            // 用内置音色列表兜底
        }
    }

    // MARK: - 朗读

    func speak() {
        let content = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard canSpeak, !content.isEmpty else { return }
        Task { await synthesize(content) }
    }

    func speakClipboard() {
        guard case .ready = status else { return }
        guard let raw = NSPasteboard.general.string(forType: .string) else {
            message = "剪贴板里没有文字"
            return
        }
        let content = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !content.isEmpty else {
            message = "剪贴板里没有文字"
            return
        }
        text = content
        Task { await synthesize(content) }
    }

    private func synthesize(_ content: String) async {
        busy = true
        message = nil
        defer { busy = false }

        do {
            var request = URLRequest(url: base.appendingPathComponent("api/tts"))
            request.httpMethod = "POST"
            request.timeoutInterval = 300
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.httpBody = try JSONSerialization.data(withJSONObject: [
                "text": content,
                "voice": voice,
                "lang": "auto",
                "instruct": instruct,
                "normalize": normalize,
            ])

            let (data, response) = try await session.data(for: request)
            guard let http = response as? HTTPURLResponse else {
                throw TTSError("网络响应异常")
            }
            guard http.statusCode == 200 else {
                let detail = (try? JSONDecoder().decode(APIError.self, from: data))?.error
                throw TTSError(detail ?? "HTTP \(http.statusCode)")
            }

            let result = try JSONDecoder().decode(TTSResult.self, from: data)
            lastDuration = result.duration
            play(path: result.path)
        } catch {
            message = "朗读失败：\(error.localizedDescription)"
        }
    }

    private func play(path: String) {
        stopPlayback()
        do {
            let player = try AVAudioPlayer(contentsOf: URL(fileURLWithPath: path))
            player.prepareToPlay()
            guard player.play() else {
                message = "播放失败：播放器无法启动"
                return
            }
            self.player = player
            playing = true

            playbackTask = Task { [weak self] in
                while !Task.isCancelled {
                    try? await Task.sleep(nanoseconds: 250_000_000)
                    guard let self else { return }
                    if let player = self.player, !player.isPlaying {
                        self.playing = false
                        self.player = nil
                        self.playbackTask = nil
                        return
                    }
                }
            }
        } catch {
            message = "播放失败：\(error.localizedDescription)"
        }
    }

    func stopPlayback() {
        playbackTask?.cancel()
        playbackTask = nil
        player?.stop()
        player = nil
        playing = false
    }

    // MARK: - 其他

    func openWeb() {
        NSWorkspace.shared.open(base)
    }

    private func loadConfig() {
        let url = FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent(".config/native-tts/config.json")
        guard let data = try? Data(contentsOf: url),
              let object = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            return
        }
        if let value = object["voice"] as? String, !value.isEmpty { voice = value }
        if let value = object["normalize"] as? Bool { normalize = value }
        if let value = object["instruct"] as? String { instruct = value }
    }

    // 开发用：快照时填一份假数据
    func previewConfigure() {
        status = .ready
        text = "这个 API 的 latency 从 800ms 降到 200ms，体验完全不一样。"
        lastDuration = 3.2
        message = nil
    }

    /// 开发用：命令行跑一遍「启动服务 → 合成 → 播放」
    func selfTest() async -> Bool {
        bootstrap()
        for _ in 0..<180 {
            if case .ready = status { break }
            if case .failed = status { break }
            try? await Task.sleep(nanoseconds: 500_000_000)
        }
        guard case .ready = status else {
            print("selftest: 服务未就绪 status=\(status) message=\(message ?? "nil")")
            return false
        }
        print("selftest: 就绪 voices=\(voices.count) voice=\(voice)")

        text = "菜单栏自测，hello world。"
        await synthesize(text)
        for _ in 0..<40 {
            if !busy { break }
            try? await Task.sleep(nanoseconds: 250_000_000)
        }
        let ok = message == nil && lastDuration != nil
        print("selftest: ok=\(ok) message=\(message ?? "nil") "
              + "duration=\(lastDuration ?? -1) playing=\(playing)")
        stopPlayback()
        return ok
    }
}

private struct TTSError: LocalizedError {
    let message: String
    init(_ message: String) { self.message = message }
    var errorDescription: String? { message }
}
