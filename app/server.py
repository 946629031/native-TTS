#!/usr/bin/env python3
"""native-TTS 本地服务：模型常驻 + 极简 HTTP API + 静态页面。

启动:
  .venv/bin/python app/server.py            # http://127.0.0.1:8765
  .venv/bin/python app/server.py --port 9000

API:
  GET  /api/health      -> {status, error}
  GET  /api/voices      -> [{name, desc, native}]
  GET  /api/history     -> [{id, text, voice, url, duration, created}]
  POST /api/tts         -> {id, url, duration, path}
       body: {text, voice, lang, instruct, temperature, seed, normalize}
"""
from __future__ import annotations

import argparse
import json
import sys
import threading
import time
import uuid
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parent.parent
STATIC = Path(__file__).resolve().parent / "static"
MODEL_DIR = ROOT / "models" / "Qwen3-TTS-12Hz-0.6B-CustomVoice-8bit"
OUT_DIR = ROOT / "outputs" / "web"
HISTORY_FILE = OUT_DIR / "history.json"
MAX_HISTORY = 50
MAX_CHARS = 2000

sys.path.insert(0, str(ROOT / "scripts"))

VOICES = [
    {"name": "Vivian", "desc": "年轻女声，明亮、略带锋利感", "native": "中文"},
    {"name": "Serena", "desc": "年轻女声，温暖柔和", "native": "中文"},
    {"name": "Uncle_Fu", "desc": "成熟男声，低沉醇厚", "native": "中文"},
    {"name": "Dylan", "desc": "年轻男声，清亮自然", "native": "中文（北京）"},
    {"name": "Eric", "desc": "男声，活泼、略带沙哑", "native": "中文（四川）"},
    {"name": "Ryan", "desc": "男声，节奏感强、有推动力", "native": "英文"},
    {"name": "Aiden", "desc": "美式男声，阳光、中频清晰", "native": "英文"},
    {"name": "Ono_Anna", "desc": "日系女声，轻快俏皮", "native": "日文"},
    {"name": "Sohee", "desc": "韩系女声，温暖有情绪", "native": "韩文"},
]

STATE = {"status": "loading", "error": None, "model": None, "sr": 24000}
MODEL_LOCK = threading.Lock()
HISTORY: list[dict] = []


def load_history() -> None:
    if HISTORY_FILE.exists():
        try:
            HISTORY.extend(json.loads(HISTORY_FILE.read_text("utf-8"))[:MAX_HISTORY])
        except Exception:  # noqa: BLE001
            pass


def save_history() -> None:
    try:
        HISTORY_FILE.write_text(
            json.dumps(HISTORY[:MAX_HISTORY], ensure_ascii=False, indent=2), "utf-8"
        )
    except Exception:  # noqa: BLE001
        pass


def load_model_bg() -> None:
    try:
        from mlx_audio.tts.utils import load_model

        t0 = time.time()
        model = load_model(str(MODEL_DIR))
        STATE.update(model=model, sr=model.sample_rate, status="ready")
        print(f"[tts] 模型就绪，用时 {time.time()-t0:.1f}s", flush=True)
    except Exception as e:  # noqa: BLE001
        STATE.update(status="error", error=f"{type(e).__name__}: {e}")
        print(f"[tts] 模型加载失败: {e}", flush=True)


def synthesize(payload: dict) -> dict:
    if STATE["status"] != "ready":
        raise RuntimeError(STATE["error"] or "模型尚未就绪")

    import numpy as np
    from mlx_audio.audio_io import write as write_audio

    from normalize_text import normalize

    text = str(payload.get("text", "")).strip()
    if not text:
        raise ValueError("文本为空")
    if len(text) > MAX_CHARS:
        raise ValueError(f"文本过长（上限 {MAX_CHARS} 字）")

    voice = payload.get("voice") or "Vivian"
    if voice not in {v["name"] for v in VOICES}:
        raise ValueError(f"未知音色: {voice}")
    lang = payload.get("lang") or "auto"
    instruct = (payload.get("instruct") or "").strip()
    if payload.get("normalize"):
        text = normalize(text)

    kwargs = {"voice": voice, "lang_code": lang}
    if instruct:
        kwargs["instruct"] = instruct
    if payload.get("temperature") is not None:
        kwargs["temperature"] = float(payload["temperature"])

    seed = payload.get("seed")
    if seed is not None:
        import mlx.core as mx

        mx.random.seed(int(seed))

    model = STATE["model"]
    with MODEL_LOCK:  # MLX 不保证并发安全，串行化
        chunks = [np.asarray(r.audio).reshape(-1) for r in model.generate(text, **kwargs)]
    wav = np.concatenate(chunks) if len(chunks) > 1 else chunks[0]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    gid = uuid.uuid4().hex[:8]
    path = OUT_DIR / f"{gid}-{voice}.wav"
    write_audio(path, wav, STATE["sr"])

    item = {
        "id": gid,
        "text": text,
        "voice": voice,
        "lang": lang,
        "instruct": instruct,
        "url": f"/audio/{path.name}",
        "path": str(path),
        "duration": round(len(wav) / STATE["sr"], 2),
        "created": int(time.time()),
    }
    HISTORY.insert(0, item)
    del HISTORY[MAX_HISTORY:]
    save_history()
    return item


class Handler(SimpleHTTPRequestHandler):
    server_version = "nativeTTS/0.1"

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(STATIC), **kw)

    def log_message(self, fmt, *args):  # 安静一点
        if "/api/" in (args[0] if args else ""):
            print(f"[http] {args[0]}", flush=True)

    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_audio(self, name: str):
        path = (OUT_DIR / unquote(name)).resolve()
        if not str(path).startswith(str(OUT_DIR.resolve())) or not path.exists():
            self._json({"error": "not found"}, 404)
            return
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "audio/wav")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):  # noqa: N802
        path = urlparse(self.path).path
        if path == "/api/health":
            return self._json({"status": STATE["status"], "error": STATE["error"]})
        if path == "/api/voices":
            return self._json(VOICES)
        if path == "/api/history":
            return self._json(HISTORY)
        if path.startswith("/audio/"):
            return self._serve_audio(path[len("/audio/"):])
        if path == "/":
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):  # noqa: N802
        if urlparse(self.path).path != "/api/tts":
            return self._json({"error": "not found"}, 404)
        try:
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length) or b"{}")
            t0 = time.time()
            item = synthesize(payload)
            print(f"[tts] {item['id']} {item['voice']} {item['duration']}s "
                  f"(耗时 {time.time()-t0:.1f}s)", flush=True)
            return self._json(item)
        except ValueError as e:
            return self._json({"error": str(e)}, 400)
        except Exception as e:  # noqa: BLE001
            print(f"[tts] 失败: {e}", flush=True)
            return self._json({"error": f"{type(e).__name__}: {e}"}, 500)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    load_history()
    threading.Thread(target=load_model_bg, daemon=True).start()

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"[tts] http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[tts] bye", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
