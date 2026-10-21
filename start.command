#!/bin/zsh
# 双击启动 native-TTS 网页版
cd "$(dirname "$0")" || exit 1

if lsof -ti tcp:8765 >/dev/null 2>&1; then
  echo "服务已在运行，直接打开页面。"
  open "http://127.0.0.1:8765"
  exit 0
fi

if [ ! -x .venv/bin/python ]; then
  echo "找不到 .venv，请先按 README 准备环境。"
  read -r "?按回车退出"
  exit 1
fi

.venv/bin/python app/server.py &
SERVER_PID=$!
trap 'kill $SERVER_PID 2>/dev/null' EXIT INT TERM

sleep 2
open "http://127.0.0.1:8765"
wait $SERVER_PID
