#!/usr/bin/env python3
"""本地 Qwen3-TTS 合成入口（MLX）。

常用:
  python scripts/say.py "这个 API 的 latency 大概两百毫秒。"
  python scripts/say.py --voice Ryan --out outputs/hello.wav "Hello, 世界"
  python scripts/say.py --norm "用Python写脚本, 转化率3.5%"
  python scripts/say.py --list-voices
  python scripts/say.py --all-voices outputs/voices "同一句话，九个音色"
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from normalize_text import normalize

DEFAULT_MODEL = "models/Qwen3-TTS-12Hz-0.6B-CustomVoice-8bit"

# 名称 -> (音色描述, 母语/口音)
VOICE_INFO = {
    "Vivian": ("年轻女声，明亮、略带锋利感", "中文"),
    "Serena": ("年轻女声，温暖柔和", "中文"),
    "Uncle_Fu": ("成熟男声，低沉醇厚", "中文"),
    "Dylan": ("年轻男声，清亮自然", "中文（北京）"),
    "Eric": ("男声，活泼、略带沙哑", "中文（四川）"),
    "Ryan": ("男声，节奏感强、有推动力", "英文"),
    "Aiden": ("美式男声，阳光、中频清晰", "英文"),
    "Ono_Anna": ("日系女声，轻快俏皮", "日文"),
    "Sohee": ("韩系女声，温暖有情绪", "韩文"),
}
VOICES = list(VOICE_INFO)


def synth(model, text: str, voice: str, lang: str, instruct: str, temperature: float | None):
    import numpy as np

    kwargs = {"voice": voice, "lang_code": lang}
    if instruct:
        kwargs["instruct"] = instruct
    if temperature is not None:
        kwargs["temperature"] = temperature
    chunks = [np.asarray(r.audio).reshape(-1) for r in model.generate(text, **kwargs)]
    return np.concatenate(chunks)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("text", nargs="?", help="要合成的文本")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--voice", default="Vivian", choices=VOICES)
    ap.add_argument("--lang", default="auto", help="auto / chinese / english / ...")
    ap.add_argument("--instruct", default="", help="自然语言风格指令（可选）")
    ap.add_argument("--out", default="outputs/out.wav")
    ap.add_argument("--all-voices", metavar="DIR", help="用全部音色各生成一份到该目录")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--temperature", type=float, default=None)
    ap.add_argument("--norm", action="store_true", help="先做文本规范化")
    ap.add_argument("--list-voices", action="store_true")
    args = ap.parse_args()

    if args.list_voices:
        print(f"{'音色':<12}{'特点':<28}母语/口音")
        for name, (desc, native) in VOICE_INFO.items():
            print(f"{name:<12}{desc:<28}{native}")
        return 0
    if not args.text:
        ap.print_help()
        return 2

    import mlx.core as mx
    from mlx_audio.audio_io import write as write_audio
    from mlx_audio.tts.utils import load_model

    text = normalize(args.text) if args.norm else args.text
    if args.seed is not None:
        mx.random.seed(args.seed)

    print(f"text: {text}", file=sys.stderr)
    model = load_model(args.model)
    sr = model.sample_rate

    if args.all_voices:
        outdir = Path(args.all_voices)
        outdir.mkdir(parents=True, exist_ok=True)
        for name in VOICES:
            wav = synth(model, text, name, args.lang, args.instruct, args.temperature)
            out = outdir / f"{name}.wav"
            write_audio(out, wav, sr)
            print(f"saved {out}  ({len(wav)/sr:.2f}s)")
        return 0

    wav = synth(model, text, args.voice, args.lang, args.instruct, args.temperature)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    write_audio(out, wav, sr)
    print(f"saved {out}  ({len(wav)/sr:.2f}s @ {sr} Hz)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
