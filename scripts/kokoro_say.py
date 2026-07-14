#!/usr/bin/env python3
"""Kokoro male-voice sidecar (run under Python 3.10–3.12 venv)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import soundfile as sf


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--text-file", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--voice", default="am_adam")
    p.add_argument("--lang", default="a")
    p.add_argument("--speed", type=float, default=1.0)
    args = p.parse_args()

    text = Path(args.text_file).read_text(encoding="utf-8").strip()
    if not text:
        print("empty text", file=sys.stderr)
        return 2

    from kokoro import KPipeline

    pipeline = KPipeline(lang_code=args.lang)
    chunks: list[np.ndarray] = []
    # Prefer paragraph / sentence splits for more natural pacing
    for _, _, audio in pipeline(
        text, voice=args.voice, speed=args.speed, split_pattern=r"\n+|\. "
    ):
        if audio is None:
            continue
        arr = np.asarray(audio, dtype=np.float32).reshape(-1)
        chunks.append(arr)
        # short breath between chunks
        chunks.append(np.zeros(int(24000 * 0.14), dtype=np.float32))

    if not chunks:
        print("no audio produced", file=sys.stderr)
        return 3

    audio = np.concatenate(chunks)
    peak = float(np.max(np.abs(audio))) or 1.0
    if peak > 1.0:
        audio = audio / peak
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(out), audio, 24000)
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
