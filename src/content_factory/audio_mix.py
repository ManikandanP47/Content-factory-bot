from __future__ import annotations

import random
import shutil
import subprocess
from pathlib import Path
from typing import Any

from content_factory.config import resolve_path


def _have_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None


def probe_duration_seconds(audio_path: Path) -> float:
    if not _have_ffmpeg():
        # rough fallback for wav via soundfile
        try:
            import soundfile as sf

            info = sf.info(str(audio_path))
            return float(info.duration)
        except Exception:
            return 45.0
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(audio_path),
    ]
    out = subprocess.check_output(cmd, text=True).strip()
    return float(out)


def _pick_music(music_dir: Path) -> Path | None:
    if not music_dir.is_dir():
        return None
    files = [
        p
        for p in music_dir.iterdir()
        if p.suffix.lower() in {".mp3", ".wav", ".m4a", ".aac"}
    ]
    return random.choice(files) if files else None


def mix_audio(
    voice_path: Path, out_path: Path, config: dict[str, Any]
) -> Path:
    """Normalize voice and optionally duck a bed track under it."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    audio_cfg = config.get("audio", {})
    music_rel = audio_cfg.get("music_dir", "assets/music")
    music_dir = resolve_path(music_rel)
    music = _pick_music(music_dir)
    volume_db = float(audio_cfg.get("music_volume_db", -22))

    if not _have_ffmpeg():
        # copy through without mix
        shutil.copy2(voice_path, out_path.with_suffix(voice_path.suffix))
        return out_path.with_suffix(voice_path.suffix)

    out_wav = out_path.with_suffix(".wav")

    if music is None:
        # loudnorm voice only
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(voice_path),
            "-af",
            "loudnorm=I=-16:TP=-1.5:LRA=11",
            "-ar",
            "48000",
            str(out_wav),
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return out_wav

    # voice + music, music quieter, length follows voice
    filter_complex = (
        f"[1:a]volume={volume_db}dB,aloop=loop=-1:size=2e+09[bed];"
        f"[0:a]loudnorm=I=-16:TP=-1.5:LRA=11[voice];"
        f"[voice][bed]amix=inputs=2:duration=first:dropout_transition=2[a]"
    )
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(voice_path),
        "-i",
        str(music),
        "-filter_complex",
        filter_complex,
        "-map",
        "[a]",
        "-ar",
        "48000",
        str(out_wav),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return out_wav
