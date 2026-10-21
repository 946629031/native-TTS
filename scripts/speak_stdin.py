#!/usr/bin/env python3
"""朗读选中的文本（macOS 右键服务 / 快捷键调用）。

从 stdin 读取文本 → 调本地服务合成 → 用 afplay 播放。
服务没启动时会自动拉起，并等待模型就绪。

用法::

    pbpaste | .venv/bin/python scripts/speak_stdin.py
    echo "你好 world" | .venv/bin/python scripts/speak_stdin.py

配置（可选）``~/.config/native-tts/config.json``::

    {"voice": "Serena", "lang": "auto", "instruct": "", "normalize": true}

环境变量（优先级更高）：``NATIVE_TTS_VOICE`` / ``NATIVE_TTS_LANG`` /
``NATIVE_TTS_INSTRUCT`` / ``NATIVE_TTS_URL`` / ``NATIVE_TTS_CONFIG``。
"""
from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "outputs" / "web"
BASE = os.environ.get("NATIVE_TTS_URL", "http://127.0.0.1:8765").rstrip("/")

TMP = Path("/tmp")  # 与 .workflow 里的日志重定向保持一致
PIDFILE = TMP / "native-tts-play.pid"
LOGFILE = TMP / "native-tts-speak.log"
SERVER_LOG = TMP / "native-tts-server.log"

CHUNK = 800          # 每次请求的最大字数（服务端上限 2000）
MAX_TEXT = 20000     # 超长选区的保护上限
SERVER_WAIT = 90     # 等待模型加载的秒数


# ---------------------------------------------------------------- 基础工具

def log(msg: str) -> None:
    try:
        with LOGFILE.open("a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}\n")
    except Exception:  # noqa: BLE001
        pass


def notify(text: str, title: str = "native-TTS") -> None:
    """系统通知；失败就忽略（权限没给也不影响朗读）。"""
    def esc(s: str) -> str:
        return s.replace("\\", "\\\\").replace('"', '\\"')

    try:
        subprocess.run(
            ["/usr/bin/osascript", "-e",
             f'display notification "{esc(text)}" with title "{esc(title)}"'],
            capture_output=True, timeout=5,
        )
    except Exception:  # noqa: BLE001
        pass


def load_config() -> dict:
    cfg = {"voice": "Serena", "lang": "auto", "instruct": "", "normalize": True}
    path = Path(os.environ.get(
        "NATIVE_TTS_CONFIG", str(Path.home() / ".config/native-tts/config.json")
    )).expanduser()
    if path.exists():
        try:
            data = json.loads(path.read_text("utf-8"))
            cfg.update({k: v for k, v in data.items() if k in cfg})
        except Exception as e:  # noqa: BLE001
            log(f"配置文件读取失败: {e}")

    for key, env in (
        ("voice", "NATIVE_TTS_VOICE"),
        ("lang", "NATIVE_TTS_LANG"),
        ("instruct", "NATIVE_TTS_INSTRUCT"),
    ):
        if os.environ.get(env):
            cfg[key] = os.environ[env]
    cfg["voice"] = str(cfg["voice"] or "Serena")
    cfg["lang"] = str(cfg["lang"] or "auto")
    cfg["instruct"] = str(cfg.get("instruct") or "")
    return cfg


# ---------------------------------------------------------------- 服务

def health() -> dict | None:
    try:
        with urllib.request.urlopen(BASE + "/api/health", timeout=0.8) as r:
            return json.loads(r.read())
    except Exception:  # noqa: BLE001
        return None


def ensure_server() -> None:
    h = health()
    if h and h.get("status") == "ready":
        return
    if h and h.get("status") == "error":
        raise RuntimeError(f"模型加载失败：{h.get('error')}")

    if not h:  # 服务没起来，后台拉起一个
        notify("正在启动语音服务，首次使用需要加载模型（约 10 秒）…")
        log("启动 app/server.py")
        f = SERVER_LOG.open("ab")
        try:
            subprocess.Popen(
                [str(ROOT / ".venv" / "bin" / "python"), str(ROOT / "app" / "server.py")],
                cwd=str(ROOT), stdin=subprocess.DEVNULL,
                stdout=f, stderr=f,
                start_new_session=True, close_fds=True,
            )
        finally:
            f.close()

    deadline = time.time() + SERVER_WAIT
    while time.time() < deadline:
        h = health()
        if h and h.get("status") == "ready":
            return
        if h and h.get("status") == "error":
            raise RuntimeError(f"模型加载失败：{h.get('error')}")
        time.sleep(0.4)
    raise RuntimeError(f"服务启动超时，详情见 {SERVER_LOG}")


def synth(text: str, cfg: dict) -> dict:
    body = json.dumps({
        "text": text,
        "voice": cfg["voice"],
        "lang": cfg["lang"],
        "instruct": cfg["instruct"],
        "normalize": bool(cfg.get("normalize", True)),
    }, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        BASE + "/api/tts", data=body, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            detail = json.loads(e.read() or b"{}").get("error") or str(e)
        except Exception:  # noqa: BLE001
            detail = str(e)
        raise RuntimeError(detail) from e


# ---------------------------------------------------------------- 播放

def stop_previous() -> None:
    """停掉上一次的朗读（包括正在放的 afplay）。"""
    try:
        pid = int(PIDFILE.read_text().strip())
        os.kill(pid, signal.SIGTERM)
    except (FileNotFoundError, ValueError, ProcessLookupError, PermissionError):
        pass
    subprocess.run(["/usr/bin/pkill", "-f", f"afplay {OUT_DIR}/"], capture_output=True)


def split_text(text: str, limit: int = CHUNK) -> list[str]:
    text = text.strip()
    if len(text) <= limit:
        return [text]

    # 先按句末标点/换行切成句子，再拼成不超过 limit 的块
    parts = re.split(r"(?<=[。！？!?；;…\n])", text)
    chunks: list[str] = []
    cur = ""
    for part in parts:
        part = part.strip()
        if not part:
            continue
        while len(part) > limit:
            # 优先在逗号或空格处断开
            cut = max(
                part.rfind("，", 0, limit),
                part.rfind(",", 0, limit),
                part.rfind(" ", 0, limit),
            )
            cut = cut + 1 if cut > limit * 0.5 else limit
            piece, part = part[:cut], part[cut:]
            if cur:
                chunks.append(cur)
                cur = ""
            chunks.append(piece)
        if len(cur) + len(part) > limit:
            chunks.append(cur)
            cur = part
        else:
            cur += part
    if cur:
        chunks.append(cur)
    return [c for c in chunks if c.strip()]


def play(path: str) -> int:
    PIDFILE.write_text(str(os.getpid()), "utf-8")
    proc = subprocess.Popen(["/usr/bin/afplay", path])
    return proc.wait()


# ---------------------------------------------------------------- 主流程

def main() -> int:
    try:
        sys.stdin.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

    text = sys.stdin.read().strip()
    if not text:
        return 0
    if len(text) > MAX_TEXT:
        text = text[:MAX_TEXT]
        notify(f"选区过长，只朗读前 {MAX_TEXT} 字")

    cfg = load_config()
    log(f"朗读 {len(text)} 字，voice={cfg['voice']}")

    try:
        ensure_server()
        stop_previous()
        for i, chunk in enumerate(split_text(text), 1):
            item = synth(chunk, cfg)
            log(f"第 {i} 块 {item.get('duration')}s -> {item.get('path')}")
            rc = play(item["path"])
            if rc != 0:
                raise RuntimeError(f"afplay 退出码 {rc}")
        return 0
    except Exception as e:  # noqa: BLE001
        log(f"失败: {e}")
        notify(f"朗读失败：{e}")
        return 1
    finally:
        try:
            if PIDFILE.read_text("utf-8").strip() == str(os.getpid()):
                PIDFILE.unlink()
        except Exception:  # noqa: BLE001
            pass


if __name__ == "__main__":
    raise SystemExit(main())
