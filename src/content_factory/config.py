from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from content_factory import PROJECT_ROOT


def project_root() -> Path:
    env = os.getenv("CONTENT_FACTORY_ROOT")
    if env:
        return Path(env).expanduser().resolve()
    return PROJECT_ROOT


def resolve_path(rel: str | Path) -> Path:
    p = Path(rel)
    if p.is_absolute():
        return p
    return project_root() / p


def load_config(config_path: str | Path | None = None) -> dict[str, Any]:
    load_dotenv(project_root() / ".env")
    root = project_root()
    path = Path(
        config_path
        or os.getenv("CONTENT_FACTORY_CONFIG")
        or os.getenv("CONFIG_PATH")
        or root / "config" / "default.yaml"
    )
    if not path.is_absolute():
        path = root / path
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if os.getenv("OLLAMA_BASE_URL") or os.getenv("OLLAMA_HOST"):
        data.setdefault("ollama", {})["base_url"] = os.getenv(
            "OLLAMA_BASE_URL"
        ) or os.getenv("OLLAMA_HOST")
    if os.getenv("OLLAMA_MODEL"):
        data.setdefault("ollama", {})["model"] = os.getenv("OLLAMA_MODEL")
    if os.getenv("VOICE_PROVIDER"):
        data.setdefault("voice", {})["provider"] = os.getenv("VOICE_PROVIDER")
    if os.getenv("YOUTUBE_PRIVACY"):
        data.setdefault("channels", {})["youtube_privacy"] = os.getenv(
            "YOUTUBE_PRIVACY"
        )
    return data


def output_dir(job_id: str | None = None) -> Path:
    base = project_root() / "output"
    base.mkdir(parents=True, exist_ok=True)
    if job_id:
        path = base / job_id
        path.mkdir(parents=True, exist_ok=True)
        return path
    return base
