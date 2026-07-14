from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path
from typing import Any

import edge_tts
import numpy as np
import soundfile as sf


def _kokoro_available() -> bool:
    return importlib.util.find_spec("kokoro") is not None


def _synthesize_kokoro(
    text: str, out_path: Path, voice: str, lang: str, speed: float
) -> Path:
    from kokoro import KPipeline

    pipeline = KPipeline(lang_code=lang)
    chunks: list[np.ndarray] = []
    for _, _, audio in pipeline(text, voice=voice, speed=speed):
        chunks.append(np.asarray(audio, dtype=np.float32))
    if not chunks:
        raise RuntimeError("Kokoro produced no audio")
    audio = np.concatenate(chunks)
    sf.write(str(out_path), audio, 24000)
    return out_path


async def _synthesize_edge(text: str, out_path: Path, voice: str) -> Path:
    communicate = edge_tts.Communicate(text, voice)
    # edge-tts writes mp3; we convert later if needed — use .mp3 path
    mp3_path = out_path.with_suffix(".mp3")
    await communicate.save(str(mp3_path))
    return mp3_path


def synthesize_voice(
    text: str, out_path: Path, config: dict[str, Any]
) -> Path:
    """Synthesize narration. Prefer Kokoro; fall back to edge-tts (free neural)."""
    voice_cfg = config.get("voice", {})
    provider = (voice_cfg.get("provider") or "auto").lower()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    use_kokoro = provider == "kokoro" or (
        provider == "auto" and _kokoro_available()
    )
    if provider == "edge":
        use_kokoro = False

    if use_kokoro:
        try:
            wav = out_path.with_suffix(".wav")
            return _synthesize_kokoro(
                text,
                wav,
                voice=voice_cfg.get("kokoro_voice", "af_heart"),
                lang=voice_cfg.get("kokoro_lang", "a"),
                speed=float(voice_cfg.get("speed", 1.0)),
            )
        except Exception as exc:
            if provider == "kokoro":
                raise
            print(f"[voice] Kokoro failed ({exc}); falling back to edge-tts")

    mp3 = asyncio.run(
        _synthesize_edge(
            text,
            out_path,
            voice=voice_cfg.get("edge_voice", "en-US-JennyNeural"),
        )
    )
    return mp3
