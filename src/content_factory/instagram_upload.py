from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

import requests

from content_factory.models import PublishResult

GRAPH = "https://graph.facebook.com/v21.0"


def _credentials(
    access_token: str | None, ig_user_id: str | None
) -> tuple[str, str]:
    token = access_token or os.getenv("INSTAGRAM_ACCESS_TOKEN")
    user_id = ig_user_id or os.getenv("INSTAGRAM_USER_ID")
    if not token or not user_id:
        raise RuntimeError(
            "Set INSTAGRAM_ACCESS_TOKEN and INSTAGRAM_USER_ID in .env "
            "(Instagram Professional account linked to a Facebook Page)."
        )
    return token, user_id


def _publish_from_url(
    video_url: str,
    caption: str,
    token: str,
    user_id: str,
    share_to_feed: bool = True,
) -> PublishResult:
    create = requests.post(
        f"{GRAPH}/{user_id}/media",
        data={
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption[:2200],
            "share_to_feed": "true" if share_to_feed else "false",
            "access_token": token,
        },
        timeout=120,
    )
    create.raise_for_status()
    creation_id = create.json().get("id")
    if not creation_id:
        raise RuntimeError(f"Instagram media create failed: {create.text}")

    for _ in range(60):
        status = requests.get(
            f"{GRAPH}/{creation_id}",
            params={"fields": "status_code", "access_token": token},
            timeout=60,
        )
        status.raise_for_status()
        code = status.json().get("status_code")
        if code == "FINISHED":
            break
        if code == "ERROR":
            raise RuntimeError(f"Instagram processing error: {status.text}")
        time.sleep(5)
    else:
        raise TimeoutError("Instagram media processing timed out")

    publish = requests.post(
        f"{GRAPH}/{user_id}/media_publish",
        data={"creation_id": creation_id, "access_token": token},
        timeout=120,
    )
    publish.raise_for_status()
    media_id = publish.json().get("id")
    return PublishResult(
        channel="instagram",
        ok=True,
        detail=str(media_id or ""),
        url=None,
        meta={
            "creation_id": creation_id,
            "media_id": media_id,
            "video_url_used": video_url,
        },
    )


def upload_instagram_reel(
    video_path: Path,
    caption: str,
    access_token: str | None = None,
    ig_user_id: str | None = None,
    share_to_feed: bool = True,
    video_url: str | None = None,
) -> PublishResult:
    """
    Publish a Reel via Instagram Graph API.

    Requires a publicly reachable HTTPS video URL for container creation.
    Pass ``video_url`` or set ``INSTAGRAM_VIDEO_URL``.
    """
    token, user_id = _credentials(access_token, ig_user_id)
    if video_path and not Path(video_path).exists() and not (
        video_url or os.getenv("INSTAGRAM_VIDEO_URL")
    ):
        raise FileNotFoundError(video_path)

    resolved_url = video_url or os.getenv("INSTAGRAM_VIDEO_URL")
    if not resolved_url:
        raise RuntimeError(
            "Instagram Reels API requires a public HTTPS video URL for "
            "container creation. After uploading to Drive, set "
            "INSTAGRAM_VIDEO_URL (or pass --instagram-video-url) to a direct "
            "HTTPS link and re-run publish --channels Instagram."
        )

    return _publish_from_url(
        resolved_url, caption, token, user_id, share_to_feed=share_to_feed
    )


def upload_instagram_reel_from_drive_link(
    drive_file_id: str,
    caption: str,
    access_token: str | None = None,
    ig_user_id: str | None = None,
    share_to_feed: bool = True,
) -> PublishResult:
    """Publish using a Google Drive file id (uc?export=download URL)."""
    video_url = f"https://drive.google.com/uc?export=download&id={drive_file_id}"
    token, user_id = _credentials(access_token, ig_user_id)
    return _publish_from_url(
        video_url, caption, token, user_id, share_to_feed=share_to_feed
    )


def upload_instagram_reel_raw(
    *args: Any, **kwargs: Any
) -> dict[str, Any]:
    """Back-compat dict wrapper around upload_instagram_reel."""
    result = upload_instagram_reel(*args, **kwargs)
    return result.model_dump()
