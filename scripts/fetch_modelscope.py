#!/usr/bin/env python3
"""从 ModelScope 下载模型文件（多连接并行，适配慢速网络）。

用法:
  python scripts/fetch_modelscope.py <repo> <dest> [--conn 12]

说明:
  - 本机直连 ModelScope 单连接约 128 KB/s，多连接可到 1 MB/s 以上；
  - 大文件按 Range 分片并行下载后合并，小文件直连；
  - 只依赖系统 curl。
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ENDPOINT = "https://www.modelscope.cn/api/v1/models/{repo}/repo/files?Revision=master&Recursive=true"
FILE_URL = "https://www.modelscope.cn/models/{repo}/resolve/master/{path}"
SMALL_FILE = 8 * 1024 * 1024


def run(cmd: list[str], **kw):
    return subprocess.run(cmd, check=True, **kw)


def api_get(url: str) -> str:
    return run(
        ["curl", "-4", "-sS", "--retry", "3", "--connect-timeout", "20", url],
        capture_output=True,
        text=True,
    ).stdout


def resolve_url(url: str) -> str:
    """跟随一次 302，拿到带签名的 CDN 直链（支持 Range）。"""
    out = run(
        ["curl", "-4", "-sS", "-o", "/dev/null", "-w", "%{redirect_url}", "--connect-timeout", "20", url],
        capture_output=True,
        text=True,
    ).stdout.strip()
    return out or url


def download_small(url: str, out: Path):
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(out.suffix + ".part")
    run(["curl", "-4", "-fL", "-sS", "--retry", "3", "--connect-timeout", "20", url, "-o", str(tmp)])
    tmp.rename(out)


def download_parallel(url: str, out: Path, size: int, conn: int):
    direct = resolve_url(url)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(out.suffix + ".part")
    chunk = math.ceil(size / conn)
    parts = []
    jobs = []

    def worker(i: int, start: int, end: int):
        part = tmp.with_name(f"{tmp.name}.{i:03d}")
        expect = end - start + 1
        for attempt in range(6):
            have = part.stat().st_size if part.exists() else 0
            if have >= expect:
                return
            if have:
                print(f"    resume chunk {i} at {have}/{expect}", flush=True)
            try:
                with part.open("ab") as fh:
                    run(
                        [
                            "curl", "-4", "-fL", "-sS", "--retry", "2",
                            "--connect-timeout", "20",
                            "--speed-limit", "1024", "--speed-time", "60",
                            "-r", f"{start + have}-{end}", direct,
                        ],
                        stdout=fh,
                    )
                if part.stat().st_size != expect:
                    raise IOError(f"chunk {i}: {part.stat().st_size} != {expect}")
                return
            except Exception as e:  # noqa: BLE001
                print(f"    retry chunk {i} ({attempt+1}): {e}", flush=True)
                time.sleep(2)
        raise SystemExit(f"chunk {i} failed")

    with ThreadPoolExecutor(max_workers=conn) as pool:
        for i in range(conn):
            start = i * chunk
            end = min(size - 1, start + chunk - 1)
            if start > end:
                break
            part = tmp.with_name(f"{tmp.name}.{i:03d}")
            parts.append(part)
            jobs.append(pool.submit(worker, i, start, end))
        for j in jobs:
            j.result()

    with tmp.open("wb") as fh:
        for part in parts:
            with part.open("rb") as pf:
                while buf := pf.read(1 << 20):
                    fh.write(buf)
            part.unlink()
    if tmp.stat().st_size != size:
        raise SystemExit(f"size mismatch: {tmp.stat().st_size} != {size}")
    tmp.rename(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("repo")
    ap.add_argument("dest")
    ap.add_argument("--conn", type=int, default=12)
    args = ap.parse_args()

    dest = Path(args.dest)
    files = json.loads(api_get(ENDPOINT.format(repo=args.repo)))["Data"]["Files"]
    blobs = [f for f in files if f["Type"] == "blob"]
    total = sum(f["Size"] for f in blobs)
    print(f"{args.repo}: {len(blobs)} files, {total/1e6:.0f} MB", flush=True)

    for f in blobs:
        path, size = f["Path"], f["Size"]
        out = dest / path
        if out.exists() and out.stat().st_size == size:
            print(f"skip {path}", flush=True)
            continue
        url = FILE_URL.format(repo=args.repo, path=path)
        print(f"get  {path} ({size/1e6:.1f} MB)", flush=True)
        if size > SMALL_FILE:
            download_parallel(url, out, size, args.conn)
        else:
            download_small(url, out)
    print("done", dest, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
