from __future__ import annotations

import json
import re
import uuid
from pathlib import Path
from typing import Any

from content_factory.config import output_dir
from content_factory.models import Job, PublishResult, Stage, VideoScript

# Path keys accepted by update_job(**fields) → stored under Job.paths
_PATH_KEYS = {
    "script_path": "script",
    "voice_path": "voice",
    "mixed_audio_path": "mixed_audio",
    "props_path": "props",
    "video_path": "video",
}

# Bare path names (when callers pass paths["voice"]=...)
_PATH_ALIASES = {"voice", "mixed_audio", "props", "video"}


_STAGE_ALIASES: dict[str, Stage] = {
    "created": Stage.created,
    "script": Stage.scripted,
    "script_done": Stage.scripted,
    "scripted": Stage.scripted,
    "voice": Stage.voiced,
    "voice_done": Stage.voiced,
    "voiced": Stage.voiced,
    "audio": Stage.mixed,
    "audio_done": Stage.mixed,
    "mixed": Stage.mixed,
    "props": Stage.mixed,
    "props_done": Stage.mixed,
    "render": Stage.rendered,
    "rendered": Stage.rendered,
    "complete": Stage.rendered,
    "published_drive": Stage.uploaded_drive,
    "uploaded_drive": Stage.uploaded_drive,
    "published_youtube": Stage.published,
    "published_instagram": Stage.published,
    "published": Stage.published,
    "failed": Stage.failed,
}


def slugify(text: str, max_len: int = 48) -> str:
    s = text.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return (s or "job")[:max_len]


def new_job_id(topic: str) -> str:
    short = uuid.uuid4().hex[:8]
    return f"{slugify(topic, 32)}-{short}"


def save_job(job: Job) -> Path:
    path = output_dir(job.id) / "job.json"
    path.write_text(job.model_dump_json(indent=2), encoding="utf-8")
    return path


def load_job(job_id: str) -> Job:
    path = output_dir(job_id) / "job.json"
    if not path.exists():
        raise FileNotFoundError(f"No job found at {path}")
    return Job.model_validate_json(path.read_text(encoding="utf-8"))


def save_script(job_id: str, script: VideoScript) -> Path:
    path = output_dir(job_id) / "script.json"
    path.write_text(script.model_dump_json(indent=2), encoding="utf-8")
    return path


def load_script(job_id: str) -> VideoScript:
    path = output_dir(job_id) / "script.json"
    return VideoScript.model_validate_json(path.read_text(encoding="utf-8"))


def _normalize_stage(value: Any) -> Stage:
    if isinstance(value, Stage):
        return value
    key = str(value).strip().lower()
    if key in _STAGE_ALIASES:
        return _STAGE_ALIASES[key]
    try:
        return Stage(key)
    except ValueError:
        return Stage.created


def _as_publish_result(channel: str, payload: Any) -> PublishResult:
    if isinstance(payload, PublishResult):
        return payload
    if isinstance(payload, dict):
        ok = bool(payload.get("ok", True))
        url = payload.get("url") or payload.get("folder_url")
        detail = payload.get("detail") or payload.get("media_id") or ""
        if isinstance(detail, dict):
            detail = json.dumps(detail)
        meta = {
            k: v
            for k, v in payload.items()
            if k not in {"ok", "url", "folder_url", "detail", "channel"}
        }
        if "folder_url" in payload and "folder_url" not in meta:
            meta["folder_url"] = payload["folder_url"]
        if "files" in payload:
            meta["files"] = payload["files"]
        if "folder_id" in payload:
            meta["folder_id"] = payload["folder_id"]
        return PublishResult(
            channel=channel,
            ok=ok,
            detail=str(detail) if detail else "",
            url=url,
            meta=meta,
        )
    return PublishResult(channel=channel, ok=True, detail=str(payload))


def update_job(job_id: str, **fields: Any) -> Job:
    """Update a job. Accepts Stage aliases and path_* kwargs used by the CLI."""
    job = load_job(job_id)
    data = job.model_dump()
    paths = dict(data.get("paths") or {})
    publish_results = [
        PublishResult.model_validate(r) for r in (data.get("publish_results") or [])
    ]
    meta = dict(data.get("meta") or {})

    for key, value in fields.items():
        if key in _PATH_KEYS:
            paths[_PATH_KEYS[key]] = str(value)
        elif key in _PATH_ALIASES:
            paths[key] = str(value)
        elif key == "script" and not isinstance(value, (str, Path)):
            # VideoScript object (not a path string)
            data["script"] = (
                value.model_dump() if hasattr(value, "model_dump") else value
            )
        elif key in {"stage", "status"}:
            data["status"] = _normalize_stage(value).value
        elif key in {"drive", "youtube", "instagram"}:
            result = _as_publish_result(key, value)
            publish_results = [r for r in publish_results if r.channel != key]
            publish_results.append(result)
            meta[key] = (
                result.meta
                if result.meta
                else (
                    value.model_dump()
                    if isinstance(value, PublishResult)
                    else value
                )
            )
        elif key == "publish_results":
            publish_results = [
                r if isinstance(r, PublishResult) else PublishResult.model_validate(r)
                for r in (value or [])
            ]
        elif key == "error":
            data["error"] = value
            if value:
                data["status"] = Stage.failed.value
        elif key in data:
            data[key] = value
        else:
            meta[key] = value

    data["paths"] = paths
    data["publish_results"] = [r.model_dump() for r in publish_results]
    data["meta"] = meta
    updated = Job.model_validate(data)
    save_job(updated)
    return updated


def dump_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
