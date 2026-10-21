#!/usr/bin/env python3
"""本地 Qwen3-TTS 合成入口（MLX）。

用法:
  python scripts/say.py "这个 API 的 latency 大概两百毫秒。"
  python scripts/say.py --voice Ryan --out outputs/hello.wav "Hello, 世界"
  python scripts/say.py --norm "用Python写脚本, 转化率3.5%"      # 先做文本规范化
  python scripts/say.py --list-voices
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from normalize_text import normalize

DEFAULT_MODEL = "models/Qwen3-TTS-12Hz-0.6B-CustomVoice-8bit"
VOICES = ["Vivian", "Serena", "Uncle_Fu", "Dylan", "Eric", "Ryan", "Aiden", "Ono_Anna", "Sohee"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("text", nargs="?", help="要合成的文本")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--voice", default="Vivian", choices=VOICES)
    ap.add_argument("--lang", default="auto", help="auto / chinese / english / ...")
    ap.add_argument("--instruct", default="", help="自然语言风格指令（可选）")
    ap.add_argument("--out", default="outputs/out.wav")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--temperature", type=float, default=None)
    ap.add_argument("--norm", action="store_true", help="先做文本规范化")
    ap.add_argument("--list-voices", action="store_true")
    args = ap.parse_args()

    if args.list_voices:
        print("\n".join(VOICES))
        return 0
    if not args.text:
        ap.print_help()
        return 2

    import mlx.core as mx
    import numpy as np
    from mlx_audio.audio_io import write as write_audio
    from mlx_audio.tts.utils import load_model

    text = normalize(args.text) if args.norm else args.text
    if args.seed is not None:
        mx.random.seed(args.seed)

    print(f"text: {text}", file=sys.stderr)
    model = load_model(args.model)
    kwargs = {"voice": args.voice, "lang_code": args.lang}
    if args.instruct:
        kwargs["instruct"] = args.instruct
    if args.temperature is not None:
        kwargs["temperature"] = args.temperature

    chunks = [np.asarray(r.audio).reshape(-1) for r in model.generate(text, **kwargs)]
    wav = np.concatenate(chunks)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    write_audio(out, wav, model.sample_rate)
    print(f"saved {out}  ({len(wav)/model.sample_rate:.2f}s @ {model.sample_rate} Hz)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
