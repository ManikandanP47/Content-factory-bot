from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from content_factory.audio_mix import probe_duration_seconds
from content_factory.config import project_root
from content_factory.models import BrandColors, CaptionCue, RemotionProps, VideoScript


def build_caption_cues(script: VideoScript, duration_s: float) -> list[CaptionCue]:
    segments: list[str] = (
        [script.hook] + [b.on_screen for b in script.beats] + [script.cta]
    )
    spoken = [script.hook] + [b.text for b in script.beats] + [script.cta]
    weights = [max(1, len(s.split())) for s in spoken]
    total_w = sum(weights) or 1
    cues: list[CaptionCue] = []
    cursor = 0.0
    for text, w in zip(segments, weights):
        span = duration_s * (w / total_w)
        cues.append(
            CaptionCue(
                text=text.strip()[:72],
                start_ms=int(cursor * 1000),
                end_ms=int((cursor + span) * 1000),
            )
        )
        cursor += span
    if cues:
        cues[-1].end_ms = int(duration_s * 1000)
    return cues


def write_remotion_props(
    script: VideoScript,
    audio_path: Path,
    job_dir: Path,
    config: dict[str, Any],
) -> tuple[Path, RemotionProps]:
    video_cfg = config.get("video", {})
    fps = int(video_cfg.get("fps", 30))
    width = int(video_cfg.get("width", 1080))
    height = int(video_cfg.get("height", 1920))
    brand_raw = video_cfg.get("brand", {})
    brand = BrandColors(
        bg_top=brand_raw.get("bg_top", "#0B1F2A"),
        bg_bottom=brand_raw.get("bg_bottom", "#143447"),
        accent=brand_raw.get("accent", "#E8A54B"),
        text=brand_raw.get("text", "#F4F7F5"),
        muted=brand_raw.get("muted", "#A8B8C0"),
    )
    duration_s = max(probe_duration_seconds(audio_path) + 0.4, 8.0)
    frames = max(int(round(duration_s * fps)), fps * 8)
    cues = build_caption_cues(script, duration_s)

    local_audio = job_dir / f"narration{audio_path.suffix}"
    if audio_path.resolve() != local_audio.resolve():
        shutil.copy2(audio_path, local_audio)

    # Also copy into Remotion public/ for staticFile playback
    video_dir = project_root() / "video"
    public_dir = video_dir / "public"
    public_dir.mkdir(parents=True, exist_ok=True)
    audio_public_name = f"job-audio-{job_dir.name}{local_audio.suffix}"
    shutil.copy2(local_audio, public_dir / audio_public_name)

    props = RemotionProps(
        title=script.title.replace(" #Shorts", "").replace(" #shorts", ""),
        hook=script.hook,
        captions=cues,
        beats_on_screen=[b.on_screen for b in script.beats],
        brand=brand,
        audio_file=local_audio.name,
        audio_public_name=audio_public_name,
        duration_in_frames=frames,
        fps=fps,
        width=width,
        height=height,
    )
    props_path = job_dir / "props.json"
    props_path.write_text(props.model_dump_json(indent=2), encoding="utf-8")
    return props_path, props


def render_video(
    props_path: Path, job_dir: Path, props: RemotionProps
) -> Path:
    """Render via Remotion CLI; fall back to FFmpeg still+audio video."""
    out_mp4 = job_dir / "final.mp4"
    video_dir = project_root() / "video"
    remotion_entry = video_dir / "src" / "index.ts"

    if (video_dir / "package.json").exists() and remotion_entry.exists():
        if not (video_dir / "node_modules").exists():
            subprocess.run(["npm", "install"], cwd=str(video_dir), check=True)
        cmd = [
            "npx",
            "remotion",
            "render",
            str(remotion_entry),
            "Short",
            str(out_mp4),
            f"--props={props_path}",
        ]
        try:
            subprocess.run(cmd, cwd=str(video_dir), check=True)
            if out_mp4.exists():
                return out_mp4
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            print(f"[video] Remotion render failed ({exc}); using FFmpeg fallback")

    return _ffmpeg_fallback(props_path, job_dir, props)


def _ffmpeg_fallback(
    props_path: Path, job_dir: Path, props: RemotionProps
) -> Path:
    out_mp4 = job_dir / "final.mp4"
    audio = job_dir / props.audio_file
    duration = props.duration_in_frames / props.fps
    bg = props.brand.bg_top.lstrip("#")
    data = json.loads(props_path.read_text(encoding="utf-8"))
    lines = [c["text"][:48] for c in data.get("captions", [])[:4]]
    title = (props.title or "Content Factory")[:40]

    def esc(s: str) -> str:
        return (
            s.replace("\\", "\\\\")
            .replace(":", "\\:")
            .replace("'", "\\'")
            .replace("%", "%%")
        )

    if not shutil.which("ffmpeg"):
        raise RuntimeError(
            "Neither Remotion nor ffmpeg is available. Install: brew install ffmpeg"
        )

    draw = (
        f"drawtext=text='{esc(title)}':fontcolor=white:fontsize=64:"
        f"x=(w-text_w)/2:y=h*0.18:line_spacing=16"
    )
    y = 0.35
    for i, line in enumerate(lines[:3]):
        draw += (
            f",drawtext=text='{esc(line)}':fontcolor=0xE8A54B:fontsize=42:"
            f"x=(w-text_w)/2:y=h*{y + i * 0.12}"
        )

    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"color=c=0x{bg}:s={props.width}x{props.height}:d={duration:.3f}:r={props.fps}",
        "-i",
        str(audio),
        "-vf",
        draw,
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-shortest",
        str(out_mp4),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return out_mp4
