from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class Beat(BaseModel):
    text: str
    on_screen: str
    motion: str = "fade"


class VideoScript(BaseModel):
    topic: str = ""
    title: str
    hook: str
    beats: list[Beat] = Field(min_length=1, max_length=8)
    cta: str
    description: str
    hashtags: list[str] = Field(default_factory=list)
    narration: str = ""

    def full_narration(self) -> str:
        if self.narration.strip():
            return self.narration.strip()
        parts = [self.hook] + [b.text for b in self.beats] + [self.cta]
        return " ".join(p.strip() for p in parts if p.strip())


class CaptionCue(BaseModel):
    text: str
    start_ms: int
    end_ms: int


class BrandColors(BaseModel):
    bg_top: str = "#0B1F2A"
    bg_bottom: str = "#143447"
    accent: str = "#E8A54B"
    text: str = "#F4F7F5"
    muted: str = "#A8B8C0"


class RemotionProps(BaseModel):
    title: str
    hook: str
    captions: list[CaptionCue]
    beats_on_screen: list[str]
    brand: BrandColors
    audio_file: str
    audio_public_name: str = ""
    duration_in_frames: int
    fps: int = 30
    width: int = 1080
    height: int = 1920


class Stage(str, Enum):
    created = "created"
    scripted = "scripted"
    voiced = "voiced"
    mixed = "mixed"
    rendered = "rendered"
    uploaded_drive = "uploaded_drive"
    published = "published"
    failed = "failed"


class PublishResult(BaseModel):
    channel: str
    ok: bool
    detail: str = ""
    url: str | None = None


class Job(BaseModel):
    id: str
    topic: str
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    status: Stage = Stage.created
    script: Optional[VideoScript] = None
    audio_duration_seconds: float | None = None
    paths: dict[str, str] = Field(default_factory=dict)
    publish_results: list[PublishResult] = Field(default_factory=list)
    error: Optional[str] = None
    meta: dict[str, Any] = Field(default_factory=dict)


# Back-compat alias used by older drafts
JobStatus = Stage
Privacy = Literal["private", "unlisted", "public"]
