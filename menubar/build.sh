#!/bin/zsh
# 编译菜单栏 App：dist/native-TTS.app
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
APP="$REPO/dist/native-TTS.app"
BIN="$APP/Contents/MacOS/NativeTTS"
RES="$APP/Contents/Resources"

echo "编译 Swift…"
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$RES"

swiftc -O -swift-version 5 -parse-as-library -target arm64-apple-macos13.0 \
  "$HERE/Sources/NativeTTSMain.swift" \
  "$HERE/Sources/AppDelegate.swift" \
  "$HERE/Sources/BackendModel.swift" \
  "$HERE/Sources/ContentView.swift" \
  "$HERE/Sources/Snapshot.swift" \
  -o "$BIN"

cat > "$APP/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>CFBundleDevelopmentRegion</key>
	<string>zh_CN</string>
	<key>CFBundleExecutable</key>
	<string>NativeTTS</string>
	<key>CFBundleIdentifier</key>
	<string>local.native-tts.menubar</string>
	<key>CFBundleInfoDictionaryVersion</key>
	<string>6.0</string>
	<key>CFBundleName</key>
	<string>native-TTS</string>
	<key>CFBundleDisplayName</key>
	<string>native-TTS</string>
	<key>CFBundlePackageType</key>
	<string>APPL</string>
	<key>CFBundleShortVersionString</key>
	<string>0.1</string>
	<key>CFBundleVersion</key>
	<string>1</string>
	<key>CFBundleIconFile</key>
	<string>AppIcon</string>
	<key>LSMinimumSystemVersion</key>
	<string>13.0</string>
	<key>LSUIElement</key>
	<true/>
	<key>NSHighResolutionCapable</key>
	<true/>
	<key>NSHumanReadableCopyright</key>
	<string>本地自用</string>
</dict>
</plist>
PLIST

# 把仓库绝对路径写进 App，安装到别处也能找到后端
/usr/libexec/PlistBuddy -c "Add :NativeTTSRepoPath string $REPO" "$APP/Contents/Info.plist"

# 顺手用现有 favicon 生成 App 图标（失败就跳过，不影响使用）
TMPICON="$(mktemp -d)"
trap 'rm -rf "$TMPICON"' EXIT
if qlmanage -t -s 1024 -o "$TMPICON" "$REPO/app/static/favicon.svg" >/dev/null 2>&1 \
   && [[ -f "$TMPICON/favicon.svg.png" ]]; then
  mkdir -p "$TMPICON/AppIcon.iconset"
  typeset -a spec
  spec=(
    "16 icon_16x16" "32 icon_16x16@2x"
    "32 icon_32x32" "64 icon_32x32@2x"
    "128 icon_128x128" "256 icon_128x128@2x"
    "256 icon_256x256" "512 icon_256x256@2x"
    "512 icon_512x512" "1024 icon_512x512@2x"
  )
  for item in $spec; do
    size="${item%% *}"
    name="${item#* }"
    sips -z "$size" "$size" "$TMPICON/favicon.svg.png" \
      --out "$TMPICON/AppIcon.iconset/$name.png" >/dev/null
  done
  iconutil -c icns "$TMPICON/AppIcon.iconset" -o "$RES/AppIcon.icns" || true
fi

codesign --force --sign - "$APP" >/dev/null 2>&1 || true

echo "完成: $APP"
echo "试运行: open \"$APP\""
