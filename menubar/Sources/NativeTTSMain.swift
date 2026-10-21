import AppKit

@main
struct NativeTTSMain {
    @MainActor
    static func main() {
        let args = CommandLine.arguments

        // 开发用：把面板离屏渲染成 PNG，方便检查布局
        if let i = args.firstIndex(of: "--snapshot"), i + 1 < args.count {
            _ = NSApplication.shared
            Snapshot.render(to: args[i + 1])
            exit(0)
        }

        // 开发用：命令行跑一遍启动 + 合成 + 播放
        if args.contains("--selftest") {
            _ = NSApplication.shared
            let model = BackendModel()
            Task { @MainActor in
                let ok = await model.selfTest()
                exit(ok ? 0 : 1)
            }
            RunLoop.main.run()
        }

        let app = NSApplication.shared
        let delegate = AppDelegate()
        app.delegate = delegate
        app.setActivationPolicy(.accessory)
        app.run()
    }
}
