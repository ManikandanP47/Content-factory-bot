from __future__ import annotations

import hashlib
import json
import random
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from content_factory.config import project_root

# Large Unsplash pool — vertical crops for Shorts/Reels (curl-friendly).
_REMOTE: list[str] = [
    "https://images.unsplash.com/photo-1486312338219-ce68d2c6f44d?auto=format&fit=crop&w=1080&h=1920&q=82",
    "https://images.unsplash.com/photo-1519389950473-47ba0277781c?auto=format&fit=crop&w=1080&h=1920&q=82",
    "https://images.unsplash.com/photo-1522202176988-66273c2fd55f?auto=format&fit=crop&w=1080&h=1920&q=82",
    "https://images.unsplash.com/photo-1497215728101-856f4ea42174?auto=format&fit=crop&w=1080&h=1920&q=82",
    "https://images.unsplash.com/photo-1553877522-43269d4ea984?auto=format&fit=crop&w=1080&h=1920&q=82",
    "https://images.unsplash.com/photo-1504384308090-c894fdcc538d?auto=format&fit=crop&w=1080&h=1920&q=82",
    "https://images.unsplash.com/photo-1556761175-b413da4baf72?auto=format&fit=crop&w=1080&h=1920&q=82",
    "https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?auto=format&fit=crop&w=1080&h=1920&q=82",
    "https://images.unsplash.com/photo-1460925895917-afdab827c52f?auto=format&fit=crop&w=1080&h=1920&q=82",
    "https://images.unsplash.com/photo-1552664730-d307ca884978?auto=format&fit=crop&w=1080&h=1920&q=82",
    "https://images.unsplash.com/photo-1517245386807-bb43f82c33c4?auto=format&fit=crop&w=1080&h=1920&q=82",
    "https://images.unsplash.com/photo-1522071820081-009f0129c71c?auto=format&fit=crop&w=1080&h=1920&q=82",
    "https://images.unsplash.com/photo-1531482615713-2afd69097998?auto=format&fit=crop&w=1080&h=1920&q=82",
    "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=1080&h=1920&q=82",
    "https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&w=1080&h=1920&q=82",
    "https://images.unsplash.com/photo-1507679799987-c73779587ccf?auto=format&fit=crop&w=1080&h=1920&q=82",
    "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?auto=format&fit=crop&w=1080&h=1920&q=82",
    "https://images.unsplash.com/photo-1432888498266-38ffec3eaf0a?auto=format&fit=crop&w=1080&h=1920&q=82",
    "https://images.unsplash.com/photo-1521737711867-e3b97375f902?auto=format&fit=crop&w=1080&h=1920&q=82",
    "https://images.unsplash.com/photo-1542744173-8e7e53415bb0?auto=format&fit=crop&w=1080&h=1920&q=82",
    "https://images.unsplash.com/photo-1600880292203-757bb62b4baf?auto=format&fit=crop&w=1080&h=1920&q=82",
    "https://images.unsplash.com/photo-1551836022-d5d88e9218df?auto=format&fit=crop&w=1080&h=1920&q=82",
    "https://images.unsplash.com/photo-1573164713714-d95e436db8a7?auto=format&fit=crop&w=1080&h=1920&q=82",
    "https://images.unsplash.com/photo-1498050108023-c5249f4df085?auto=format&fit=crop&w=1080&h=1920&q=82",
    "https://images.unsplash.com/photo-1581091226825-a6a2a5aee158?auto=format&fit=crop&w=1080&h=1920&q=82",
    "https://images.unsplash.com/photo-1559136555-9303baea8ebd?auto=format&fit=crop&w=1080&h=1920&q=82",
    "https://images.unsplash.com/photo-1509248961158-e54f6934749c?auto=format&fit=crop&w=1080&h=1920&q=82",
    "https://images.unsplash.com/photo-1611224923853-80b023f02d71?auto=format&fit=crop&w=1080&h=1920&q=82",
    "https://images.unsplash.com/photo-1483058712412-4245e9b90334?auto=format&fit=crop&w=1080&h=1920&q=82",
    "https://images.unsplash.com/photo-1556761175-5973dc0f32e7?auto=format&fit=crop&w=1080&h=1920&q=82",
]

_KEN = ("zoom_in", "zoom_out", "pan_left", "pan_right", "drift_up")


def _assets_dir() -> Path:
    return project_root() / "assets" / "broll"


def _usage_path() -> Path:
    return _assets_dir() / ".usage.json"


def _local_stock() -> list[Path]:
    d = _assets_dir()
    if not d.is_dir():
        return []
    return sorted(
        [
            p
            for p in d.iterdir()
            if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
            and not p.name.startswith(".")
        ]
    )


def _download_curl(url: str, dest: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    curl = shutil.which("curl")
    if not curl:
        return False
    proc = subprocess.run(
        [
            curl,
            "-fsSL",
            "--retry",
            "2",
            "--connect-timeout",
            "20",
            "--max-time",
            "90",
            "-A",
            "ContentFactoryBot/1.0",
            url,
            "-o",
            str(dest),
        ],
        capture_output=True,
        text=True,
    )
    return proc.returncode == 0 and dest.exists() and dest.stat().st_size > 1000


def ensure_stock_library(min_count: int = 22) -> list[Path]:
    """Ensure assets/broll has a large photo pool (curl when missing)."""
    existing = _local_stock()
    if len(existing) >= min_count:
        return existing

    print(f"[broll] Expanding stock library (have {len(existing)}, want {min_count})…")
    for i, url in enumerate(_REMOTE):
        dest = _assets_dir() / f"{i + 1:02d}.jpg"
        if dest.exists() and dest.stat().st_size > 1000:
            continue
        ok = _download_curl(url, dest)
        if not ok:
            print(f"[broll] curl failed for index {i + 1}")
        if len(_local_stock()) >= max(min_count, len(_REMOTE)):
            break
    return _local_stock()


def _load_usage() -> dict[str, Any]:
    path = _usage_path()
    if not path.exists():
        return {"recent": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"recent": []}


def _save_usage(names: list[str]) -> None:
    path = _usage_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = _load_usage()
    recent = list(data.get("recent") or [])
    for n in names:
        if n in recent:
            recent.remove(n)
        recent.append(n)
    # Keep last ~48 so older images cycle back later
    data["recent"] = recent[-48:]
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _pick_fresh(
    topic: str,
    job_key: str,
    files: list[Path],
    n: int,
) -> list[Path]:
    """Unique images for this job; prefer ones not used in recent jobs."""
    if not files:
        return []

    usage = _load_usage()
    recent = list(usage.get("recent") or [])
    recent_set = set(recent)

    # Job-specific RNG so same topic at different times still differs
    seed_material = f"{topic}|{job_key}|{time.time_ns()}"
    rng = random.Random(int(hashlib.sha256(seed_material.encode()).hexdigest()[:16], 16))

    fresh = [p for p in files if p.name not in recent_set]
    stale = [p for p in files if p.name in recent_set]
    rng.shuffle(fresh)
    # Stale: oldest-used first
    stale_sorted = sorted(
        stale,
        key=lambda p: recent.index(p.name) if p.name in recent else -1,
    )

    pool = fresh + stale_sorted
    picks = pool[: min(n, len(pool))]
    if len(picks) < n:
        extras = [p for p in pool if p not in picks]
        picks.extend(extras[: n - len(picks)])
    return picks


def fetch_broll(
    topic: str,
    count: int,
    dest_dir: Path,
    *,
    public_dir: Path | None = None,
    job_key: str | None = None,
) -> list[dict[str, Any]]:
    """
    Copy unique stock photos into the job (and Remotion public/).

    - No repeats inside a single video when the library is large enough
    - Avoids recently used images across jobs via ``assets/broll/.usage.json``
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    if public_dir is not None:
        public_dir.mkdir(parents=True, exist_ok=True)

    need = max(count, 3)
    stock = ensure_stock_library(min_count=max(need + 8, 22))
    if not stock:
        raise RuntimeError(
            "No B-roll images available. Add JPGs under assets/broll/ "
            "or ensure curl can reach images.unsplash.com"
        )

    picks = _pick_fresh(topic or "focus", job_key or dest_dir.name, stock, need)
    if len(picks) < need:
        print(
            f"[broll] Warning: only {len(picks)} unique images for {need} beats; "
            "expand assets/broll for fresher variety"
        )

    clips: list[dict[str, Any]] = []
    used_names: list[str] = []
    for i, src in enumerate(picks[:need]):
        name = f"broll-{i}{src.suffix.lower()}"
        shutil.copy2(src, dest_dir / name)
        if public_dir is not None:
            shutil.copy2(src, public_dir / name)
        clips.append({"src": name, "ken": _KEN[i % len(_KEN)]})
        used_names.append(src.name)

    _save_usage(used_names)
    print(f"[broll] Selected unique stills: {', '.join(used_names)}")
    return clips
