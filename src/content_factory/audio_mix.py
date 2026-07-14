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
        and not p.name.startswith(".")
    ]
    return random.choice(files) if files else None


# Professional voice chain: gentle highpass, light compression, broadcast loudnorm
_VOICE_AF = (
    "highpass=f=80,"
    "acompressor=threshold=-18dB:ratio=2.5:attack=15:release=120:makeup=2,"
    "loudnorm=I=-14:TP=-1.5:LRA=9"
)


def mix_audio(
    voice_path: Path, out_path: Path, config: dict[str, Any]
) -> Path:
    """Normalize voice (highpass + compress + loudnorm) and optionally duck a bed."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    audio_cfg = config.get("audio", {})
    music_rel = audio_cfg.get("music_dir", "assets/music")
    music_dir = resolve_path(music_rel)
    music = _pick_music(music_dir)
    volume_db = float(audio_cfg.get("music_volume_db", -24))

    end_pad = float(audio_cfg.get("end_pad_seconds", 2.2))
    out_wav = out_path.with_suffix(".wav")

    if not _have_ffmpeg():
        # Pad with silence locally so endings still complete without ffmpeg
        try:
            import numpy as np
            import soundfile as sf

            audio, sr = sf.read(str(voice_path))
            pad = np.zeros(int(sr * end_pad), dtype=np.float32)
            if audio.ndim > 1:
                pad = np.zeros((int(sr * end_pad), audio.shape[1]), dtype=np.float32)
            sf.write(str(out_wav), np.concatenate([audio, pad]), sr)
            return out_wav
        except Exception:
            shutil.copy2(voice_path, out_path.with_suffix(voice_path.suffix))
            return out_path.with_suffix(voice_path.suffix)

    if music is None:
        # Pad trailing silence so the Short can hold CTA without hard audio cut
        af = f"{_VOICE_AF},apad=pad_dur={end_pad}"
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(voice_path),
            "-af",
            af,
            "-ar",
            "48000",
            str(out_wav),
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return out_wav

    # Soft bed under narration; pad after voice so ending completes fully
    filter_complex = (
        f"[1:a]volume={volume_db}dB,aloop=loop=-1:size=2e+09,"
        f"afade=t=in:st=0:d=1.2[bed];"
        f"[0:a]{_VOICE_AF},apad=pad_dur={end_pad}[voice];"
        f"[voice][bed]amix=inputs=2:duration=first:dropout_transition=2,"
        f"loudnorm=I=-14:TP=-1.5:LRA=9[a]"
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
