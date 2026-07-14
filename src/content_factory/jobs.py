from __future__ import annotations

import json
import re
import uuid
from pathlib import Path

from content_factory.config import output_dir
from content_factory.models import JobStatus, VideoScript


def slugify(text: str, max_len: int = 48) -> str:
    s = text.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return (s or "job")[:max_len]


def new_job_id(topic: str) -> str:
    short = uuid.uuid4().hex[:8]
    return f"{slugify(topic, 32)}-{short}"


def save_job(status: JobStatus) -> Path:
    path = output_dir(status.job_id) / "job.json"
    path.write_text(status.model_dump_json(indent=2), encoding="utf-8")
    return path


def load_job(job_id: str) -> JobStatus:
    path = output_dir(job_id) / "job.json"
    if not path.exists():
        raise FileNotFoundError(f"No job found at {path}")
    return JobStatus.model_validate_json(path.read_text(encoding="utf-8"))


def save_script(job_id: str, script: VideoScript) -> Path:
    path = output_dir(job_id) / "script.json"
    path.write_text(script.model_dump_json(indent=2), encoding="utf-8")
    return path


def load_script(job_id: str) -> VideoScript:
    path = output_dir(job_id) / "script.json"
    return VideoScript.model_validate_json(path.read_text(encoding="utf-8"))


def update_job(job_id: str, **fields) -> JobStatus:
    status = load_job(job_id)
    data = status.model_dump()
    data.update(fields)
    updated = JobStatus.model_validate(data)
    save_job(updated)
    return updated


def dump_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
