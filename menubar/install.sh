#!/bin/zsh
# 编译并安装到 ~/Applications，然后启动
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
DEST="$HOME/Applications/native-TTS.app"

"$HERE/build.sh"

mkdir -p "$HOME/Applications"
pkill -f "native-TTS.app/Contents/MacOS/NativeTTS" >/dev/null 2>&1 || true
rm -rf "$DEST"
cp -R "$HERE/../dist/native-TTS.app" "$DEST"
xattr -dr com.apple.quarantine "$DEST" >/dev/null 2>&1 || true

open "$DEST"

echo
echo "✅ 已安装并启动：$DEST"
echo "菜单栏右上角会出现一个波形图标，点它打开面板。"
echo
echo "想开机自启：系统设置 → 通用 → 登录项 → 点「+」→ 选择 $DEST"
