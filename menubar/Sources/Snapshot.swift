import AppKit
import SwiftUI

@MainActor
enum Snapshot {
    static func render(to path: String) {
        let model = BackendModel()
        model.previewConfigure()

        let hosting = NSHostingView(rootView: ContentView(model: model))
        hosting.setFrameSize(NSSize(width: 380, height: 420))
        hosting.layoutSubtreeIfNeeded()
        hosting.setFrameSize(hosting.fittingSize)
        hosting.layoutSubtreeIfNeeded()
        hosting.display()

        guard let rep = hosting.bitmapImageRepForCachingDisplay(in: hosting.bounds) else {
            FileHandle.standardError.write(Data("snapshot failed\n".utf8))
            return
        }
        hosting.cacheDisplay(in: hosting.bounds, to: rep)

        guard let png = rep.representation(using: .png, properties: [:]) else {
            FileHandle.standardError.write(Data("png failed\n".utf8))
            return
        }

        do {
            try png.write(to: URL(fileURLWithPath: path))
            print("snapshot -> \(path) \(Int(hosting.bounds.width))x\(Int(hosting.bounds.height))")
        } catch {
            FileHandle.standardError.write(Data("write failed: \(error)\n".utf8))
        }
    }
}
