from __future__ import annotations

import asyncio
import importlib.util
import os
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf

from content_factory.config import project_root

_PIPER_MODEL_URL = (
    "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/"
    "en/en_US/ryan/high/en_US-ryan-high.onnx?download=true"
)
_PIPER_CFG_URL = (
    "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/"
    "en/en_US/ryan/high/en_US-ryan-high.onnx.json?download=true"
)


def _configure_ssl() -> None:
    try:
        import certifi

        ca = certifi.where()
        os.environ.setdefault("SSL_CERT_FILE", ca)
        os.environ.setdefault("REQUESTS_CA_BUNDLE", ca)
        os.environ.setdefault("CURL_CA_BUNDLE", ca)
    except Exception:
        pass


_configure_ssl()


def _piper_available() -> bool:
    return importlib.util.find_spec("piper") is not None


def _piper_model_paths(model_name: str = "en_US-ryan-high") -> tuple[Path, Path]:
    voices = project_root() / "tools" / "piper" / "voices"
    return voices / f"{model_name}.onnx", voices / f"{model_name}.onnx.json"


def ensure_piper_male_voice(model_name: str = "en_US-ryan-high") -> Path:
    """Download Piper Ryan (male, high quality) once via curl if missing."""
    model, cfg = _piper_model_paths(model_name)
    model.parent.mkdir(parents=True, exist_ok=True)
    if model.exists() and model.stat().st_size > 1_000_000 and cfg.exists():
        return model
    curl = shutil.which("curl")
    if not curl:
        raise RuntimeError("curl required to download Piper male voice model")
    print("[voice] Downloading Piper Ryan (genuine AI male neural)…")
    for url, dest in ((_PIPER_MODEL_URL, model), (_PIPER_CFG_URL, cfg)):
        if dest.exists() and dest.stat().st_size > 1000:
            continue
        proc = subprocess.run(
            [curl, "-fsSL", "-L", url, "-o", str(dest)],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"Failed to download {url}: {proc.stderr}")
    return model


def _synthesize_piper(text: str, out_path: Path, model_name: str, length_scale: float) -> Path:
    from piper import PiperVoice
    from piper.config import SynthesisConfig

    model = ensure_piper_male_voice(model_name)
    voice = PiperVoice.load(str(model))
    wav_path = out_path.with_suffix(".wav")
    # length_scale > 1.0 = slightly slower / more deliberate male read
    syn = SynthesisConfig(length_scale=length_scale)
    with wave.open(str(wav_path), "wb") as wf:
        voice.synthesize_wav(text, wf, syn_config=syn)
    return wav_path


def _kokoro_available() -> bool:
    return importlib.util.find_spec("kokoro") is not None


def _kokoro_python() -> Path | None:
    candidates = [
        project_root() / ".venv-voice" / "bin" / "python",
        project_root() / ".venv" / "bin" / "python",
    ]
    for py in candidates:
        if not py.exists():
            continue
        check = subprocess.run(
            [str(py), "-c", "import kokoro"],
            capture_output=True,
            text=True,
        )
        if check.returncode == 0:
            return py
    return None


def _synthesize_kokoro_sidecar(
    text: str, out_path: Path, voice: str, lang: str, speed: float, python: Path
) -> Path:
    script = project_root() / "scripts" / "kokoro_say.py"
    with tempfile.NamedTemporaryFile(
        "w", suffix=".txt", delete=False, encoding="utf-8"
    ) as f:
        f.write(text)
        text_path = Path(f.name)
    try:
        wav = out_path.with_suffix(".wav")
        proc = subprocess.run(
            [
                str(python),
                str(script),
                "--text-file",
                str(text_path),
                "--out",
                str(wav),
                "--voice",
                voice,
                "--lang",
                lang,
                "--speed",
                str(speed),
            ],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0 or not wav.exists():
            raise RuntimeError(
                (proc.stderr or proc.stdout or "kokoro sidecar failed").strip()
            )
        return wav
    finally:
        text_path.unlink(missing_ok=True)


async def _synthesize_edge(text: str, out_path: Path, voice: str) -> Path:
    import certifi
    import edge_tts

    os.environ["SSL_CERT_FILE"] = certifi.where()
    communicate = edge_tts.Communicate(text, voice)
    mp3_path = out_path.with_suffix(".mp3")
    await communicate.save(str(mp3_path))
    return mp3_path


def _synthesize_macos_say(text: str, out_path: Path, voice: str) -> Path:
    if not shutil.which("say"):
        raise RuntimeError("macOS `say` not available")
    aiff = out_path.with_suffix(".aiff")
    wav = out_path.with_suffix(".wav")
    spoken = text.replace(" … ", "[[slnc 420]] ").replace("…", "[[slnc 280]] ")
    cmd = ["say", "-v", voice, "-r", "175", "-o", str(aiff), spoken]
    subprocess.run(cmd, check=True, capture_output=True)
    if shutil.which("ffmpeg"):
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(aiff), "-ar", "48000", str(wav)],
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


def _synthesize_espeak(text: str, out_path: Path, voice: str, speed: float) -> Path:
    espeak = shutil.which("espeak-ng") or shutil.which("espeak")
    if not espeak:
        raise RuntimeError("espeak-ng not available")
    wav = out_path.with_suffix(".wav")
    wpm = int(175 * speed)
    cmd = [espeak, "-v", voice, "-s", str(wpm), "-w", str(wav), text]
    subprocess.run(cmd, check=True, capture_output=True)
    return wav


def synthesize_voice(text: str, out_path: Path, config: dict[str, Any]) -> Path:
    """
    Prefer genuine AI **male** neural voice:

      1. Piper Ryan (local neural, free) — best default on Apple Silicon
      2. Kokoro am_adam (if `.venv-voice` / install available)
      3. edge-tts AndrewNeural
      4. macOS Daniel
      5. espeak-ng (offline last resort — no network/model download needed)
    """
    voice_cfg = config.get("voice", {})
    provider = (voice_cfg.get("provider") or "auto").lower()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []

    piper_model = voice_cfg.get("piper_model", "en_US-ryan-high")
    piper_length = float(voice_cfg.get("piper_length_scale", 1.05))
    kokoro_voice = voice_cfg.get("kokoro_voice", "am_adam")
    kokoro_lang = voice_cfg.get("kokoro_lang", "a")
    speed = float(voice_cfg.get("speed", 0.95))
    edge_voice = voice_cfg.get("edge_voice", "en-US-AndrewNeural")
    macos_voice = voice_cfg.get("macos_voice", "Daniel")
    espeak_voice = voice_cfg.get("espeak_voice", "en-us+m3")

    def try_piper() -> Path | None:
        if not _piper_available() and provider != "piper":
            return None
        try:
            print(f"[voice] Piper AI male neural ({piper_model})")
            return _synthesize_piper(text, out_path, piper_model, piper_length)
        except Exception as exc:
            errors.append(f"piper: {exc}")
            print(f"[voice] Piper failed ({exc})")
            if provider == "piper":
                raise
            return None

    def try_kokoro() -> Path | None:
        try:
            py = _kokoro_python()
            if py is None and not _kokoro_available():
                return None
            print(f"[voice] Kokoro male AI ({kokoro_voice})")
            if py is not None:
                return _synthesize_kokoro_sidecar(
                    text, out_path.with_suffix(".wav"), kokoro_voice, kokoro_lang, speed, py
                )
            from kokoro import KPipeline

            pipeline = KPipeline(lang_code=kokoro_lang)
            chunks: list[np.ndarray] = []
            for _, _, audio in pipeline(
                text, voice=kokoro_voice, speed=speed, split_pattern=r"\n+|\. "
            ):
                if audio is None:
                    continue
                chunks.append(np.asarray(audio, dtype=np.float32).reshape(-1))
                chunks.append(np.zeros(int(24000 * 0.14), dtype=np.float32))
            if not chunks:
                raise RuntimeError("no audio")
            audio = np.concatenate(chunks)
            wav = out_path.with_suffix(".wav")
            sf.write(str(wav), audio, 24000)
            return wav
        except Exception as exc:
            errors.append(f"kokoro: {exc}")
            print(f"[voice] Kokoro failed ({exc})")
            if provider == "kokoro":
                raise
            return None

    def try_edge() -> Path | None:
        try:
            print(f"[voice] edge-tts neural male ({edge_voice})")
            return asyncio.run(_synthesize_edge(text, out_path, edge_voice))
        except Exception as exc:
            errors.append(f"edge-tts: {exc}")
            print(f"[voice] edge-tts failed ({exc})")
            if provider == "edge":
                raise
            return None

    def try_say() -> Path | None:
        try:
            print(f"[voice] macOS say male ({macos_voice})")
            return _synthesize_macos_say(text, out_path, macos_voice)
        except Exception as exc:
            errors.append(f"macos-say: {exc}")
            print(f"[voice] macOS say failed ({exc})")
            if provider == "macos":
                raise
            return None

    def try_espeak() -> Path | None:
        try:
            print(f"[voice] espeak-ng offline fallback ({espeak_voice})")
            return _synthesize_espeak(text, out_path, espeak_voice, speed)
        except Exception as exc:
            errors.append(f"espeak: {exc}")
            print(f"[voice] espeak-ng failed ({exc})")
            if provider == "espeak":
                raise
            return None

    order = {
        "auto": (try_piper, try_kokoro, try_edge, try_say, try_espeak),
        "piper": (try_piper,),
        "kokoro": (try_kokoro,),
        "edge": (try_edge,),
        "macos": (try_say,),
        "espeak": (try_espeak,),
    }.get(provider, (try_piper, try_kokoro, try_edge, try_say, try_espeak))

    for fn in order:
        result = fn()
        if result:
            return result

    raise RuntimeError(
        "No voice provider succeeded. `pip install piper-tts` recommended. Errors: "
        + "; ".join(errors)
    )
