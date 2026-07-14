from __future__ import annotations

import asyncio
import importlib.util
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf


def _configure_ssl() -> None:
    """Help edge-tts on Homebrew Python find CA certs (call before import)."""
    try:
        import certifi

        ca = certifi.where()
        os.environ.setdefault("SSL_CERT_FILE", ca)
        os.environ.setdefault("REQUESTS_CA_BUNDLE", ca)
        os.environ.setdefault("CURL_CA_BUNDLE", ca)
    except Exception:
        pass


# Must run before edge_tts builds its SSL context at import time
_configure_ssl()


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
    import edge_tts

    _configure_ssl()
    communicate = edge_tts.Communicate(text, voice)
    mp3_path = out_path.with_suffix(".mp3")
    await communicate.save(str(mp3_path))
    return mp3_path


def _synthesize_macos_say(text: str, out_path: Path, voice: str) -> Path:
    """Local free macOS neural/premium voices via `say` (no network)."""
    if not shutil.which("say"):
        raise RuntimeError("macOS `say` not available")
    aiff = out_path.with_suffix(".aiff")
    wav = out_path.with_suffix(".wav")
    # Samantha / Ava are natural default English voices on macOS
    cmd = ["say", "-v", voice, "-o", str(aiff), text]
    subprocess.run(cmd, check=True, capture_output=True)
    if shutil.which("ffmpeg"):
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(aiff),
                "-ar",
                "48000",
                str(wav),
            ],
            check=True,
            capture_output=True,
        )
        aiff.unlink(missing_ok=True)
        return wav
    if shutil.which("afconvert"):
        subprocess.run(
            ["afconvert", "-f", "WAVE", "-d", "LEI16", str(aiff), str(wav)],
            check=True,
            capture_output=True,
        )
        aiff.unlink(missing_ok=True)
        return wav
    return aiff


def synthesize_voice(
    text: str, out_path: Path, config: dict[str, Any]
) -> Path:
    """
    Synthesize narration.

    Order for ``provider: auto``:
      1. Kokoro (best free long-term local neural)
      2. edge-tts (free cloud neural)
      3. macOS ``say`` (free local, humane enough)
    """
    voice_cfg = config.get("voice", {})
    provider = (voice_cfg.get("provider") or "auto").lower()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []

    def try_kokoro() -> Path | None:
        if not _kokoro_available() and provider != "kokoro":
            return None
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
            errors.append(f"kokoro: {exc}")
            print(f"[voice] Kokoro failed ({exc})")
            if provider == "kokoro":
                raise
            return None

    def try_edge() -> Path | None:
        try:
            return asyncio.run(
                _synthesize_edge(
                    text,
                    out_path,
                    voice=voice_cfg.get("edge_voice", "en-US-JennyNeural"),
                )
            )
        except Exception as exc:
            errors.append(f"edge-tts: {exc}")
            print(f"[voice] edge-tts failed ({exc})")
            # Clean partial downloads
            for p in (
                out_path.with_suffix(".mp3"),
                out_path.with_suffix(".wav"),
            ):
                if p.exists() and p.stat().st_size == 0:
                    p.unlink(missing_ok=True)
            if provider == "edge":
                raise
            return None

    def try_say() -> Path | None:
        try:
            return _synthesize_macos_say(
                text,
                out_path,
                voice=voice_cfg.get("macos_voice", "Samantha"),
            )
        except Exception as exc:
            errors.append(f"macos-say: {exc}")
            print(f"[voice] macOS say failed ({exc})")
            if provider == "macos":
                raise
            return None

    if provider == "kokoro":
        result = try_kokoro()
        if result:
            return result
        raise RuntimeError("; ".join(errors) or "Kokoro failed")
    if provider == "edge":
        result = try_edge()
        if result:
            return result
        raise RuntimeError("; ".join(errors) or "edge-tts failed")
    if provider == "macos":
        result = try_say()
        if result:
            return result
        raise RuntimeError("; ".join(errors) or "macOS say failed")

    # auto
    for fn in (try_kokoro, try_edge, try_say):
        result = fn()
        if result:
            return result

    raise RuntimeError(
        "No voice provider succeeded. Install Kokoro (Python 3.10–3.12), "
        "fix SSL certs for edge-tts, or use macOS. Errors: "
        + "; ".join(errors)
    )
