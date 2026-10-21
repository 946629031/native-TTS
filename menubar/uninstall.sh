#!/bin/zsh
# 卸载菜单栏 App（不影响网页版和右键服务）
set -euo pipefail

DEST="$HOME/Applications/native-TTS.app"
pkill -f "native-TTS.app/Contents/MacOS/NativeTTS" >/dev/null 2>&1 || true
rm -rf "$DEST"
echo "已删除: $DEST"
