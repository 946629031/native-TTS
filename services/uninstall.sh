#!/bin/zsh
# 卸载「用 native-TTS 朗读」右键服务
set -euo pipefail
DEST="$HOME/Library/Services/native-TTS 朗读.workflow"

if [[ -d "$DEST" ]]; then
  rm -rf "$DEST"
  echo "已删除: $DEST"
else
  echo "没有安装过（$DEST 不存在）"
fi

/System/Library/CoreServices/pbs -update >/dev/null 2>&1 || true
killall pbs >/dev/null 2>&1 || true
echo "完成。"
