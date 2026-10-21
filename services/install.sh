#!/bin/zsh
# 安装「用 native-TTS 朗读」右键服务
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
DEST="$HOME/Library/Services/native-TTS 朗读.workflow"

if [[ ! -x "$REPO/.venv/bin/python" ]]; then
  echo "找不到 $REPO/.venv/bin/python"
  echo "请先按 README 准备 Python 环境。"
  exit 1
fi

if [[ ! -f "$REPO/scripts/speak_stdin.py" ]]; then
  echo "找不到 scripts/speak_stdin.py"
  exit 1
fi

echo "安装到: $DEST"
rm -rf "$DEST"
mkdir -p "$DEST/Contents"
mkdir -p "$HOME/Library/Services"

cp "$HERE/template/Info.plist" "$DEST/Contents/Info.plist"
sed "s|__REPO__|$REPO|g" "$HERE/template/document.wflow" > "$DEST/Contents/document.wflow"
chmod -R u+rwX,go+rX "$DEST"

plutil -lint "$DEST/Contents/Info.plist" >/dev/null
plutil -lint "$DEST/Contents/document.wflow" >/dev/null

# 让系统重新扫描服务
/System/Library/CoreServices/pbs -update >/dev/null 2>&1 || true
killall pbs >/dev/null 2>&1 || true

echo
echo "✅ 已安装：右键 → 服务（Services）→「用 native-TTS 朗读」"
echo
echo "如果菜单里没出现，去这里勾选一次："
echo "  系统设置 → 键盘 → 键盘快捷键 → 服务 → 文本"
echo
echo "也可以在那里给它分配快捷键（例如 ⌥⌘S），选中文字直接按。"
echo "卸载：$HERE/uninstall.sh"
