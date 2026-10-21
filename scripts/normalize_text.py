#!/usr/bin/env python3
"""轻量文本规范化：面向中英混读 TTS 的前处理。

只做「低风险、可逆性高」的改动，不擅自改写代码/品牌名：
  1. NFKC 归一（全角→半角，兼容字符）
  2. 去除零宽字符、emoji、控制字符
  3. 中文与拉丁字母/数字之间补空格（对 tokenizer 更友好）
  4. 合并多余空格、清理中文标点前的空格
  5. 可选：把常见单位/符号展开为中文读法

用法:
  python scripts/normalize_text.py "用Python写脚本，转化率3.5%"
  echo "..." | python scripts/normalize_text.py
"""
from __future__ import annotations

import argparse
import re
import sys
import unicodedata

CJK = r"\u4e00-\u9fff\u3400-\u4dbf"
RE_CJK_LATIN = re.compile(rf"([{CJK}])([A-Za-z0-9@#$%&])")
RE_LATIN_CJK = re.compile(rf"([A-Za-z0-9])([{CJK}])")
RE_MULTISPACE = re.compile(r"[ \t]{2,}")
RE_SPACE_BEFORE_PUNCT = re.compile(rf"\s+([，。！？、；：）】》」』])")
RE_SPACE_AFTER_OPEN = re.compile(rf"([（【《「『])\s+")

RE_EMOJI = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF\uFE0F\u200D]"
)
RE_ZERO_WIDTH = re.compile("[\u200b-\u200f\u202a-\u202e\ufeff]")
RE_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def fold_fullwidth(text: str) -> str:
    """只折叠全角 ASCII（字母/数字）与全角空格。

    注意：不能用 NFKC 整体规范化——中文逗号 U+FF0C 会被折成半角 ','，
    而中文标点对 TTS 的停顿判断很重要。
    """
    out = []
    for ch in text:
        cp = ord(ch)
        if 0xFF10 <= cp <= 0xFF19 or 0xFF21 <= cp <= 0xFF3A or 0xFF41 <= cp <= 0xFF5A:
            out.append(chr(cp - 0xFEE0))
        elif ch == "\u3000":
            out.append(" ")
        else:
            out.append(ch)
    return "".join(out)

# 顺序有意义：长的先匹配
UNIT_RULES = [
    (re.compile(r"(\d)\s*%"), r"\1%"),
    (re.compile(r"(\d)\s*(GB|MB|KB|TB)\b"), r"\1 \2"),
    (re.compile(r"(\d)\s*(ms|s|min|h)\b"), r"\1 \2"),
    (re.compile(r"(\d)\s*(km|kg|ml|cm|mm)\b"), r"\1 \2"),
]


def normalize(text: str, expand_units: bool = False) -> str:
    text = fold_fullwidth(text)
    text = RE_ZERO_WIDTH.sub("", text)
    text = RE_CONTROL.sub("", text)
    text = RE_EMOJI.sub(" ", text)

    text = text.replace("\u00a0", " ")
    # 常见中文标点统一（NFKC 已处理全角 ASCII，这里兜底）
    text = text.replace("...", "……")
    text = re.sub(r"!{2,}", "！", text)
    text = re.sub(r"\?{2,}", "？", text)

    if expand_units:
        for pattern, repl in UNIT_RULES:
            text = pattern.sub(repl, text)

    text = RE_CJK_LATIN.sub(r"\1 \2", text)
    text = RE_LATIN_CJK.sub(r"\1 \2", text)
    text = RE_SPACE_BEFORE_PUNCT.sub(r"\1", text)
    text = RE_SPACE_AFTER_OPEN.sub(r"\1", text)
    text = RE_MULTISPACE.sub(" ", text)
    return text.strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("text", nargs="*")
    ap.add_argument("--expand-units", action="store_true")
    args = ap.parse_args()
    raw = " ".join(args.text) if args.text else sys.stdin.read()
    print(normalize(raw, expand_units=args.expand_units))
    return 0


if __name__ == "__main__":
    sys.exit(main())
