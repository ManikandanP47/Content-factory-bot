from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

import requests

GRAPH = "https://graph.facebook.com/v21.0"


def upload_instagram_reel(
    video_path: Path,
    caption: str,
    access_token: str | None = None,
    ig_user_id: str | None = None,
    share_to_feed: bool = True,
) -> dict[str, Any]:
    """
    Publish a Reel via Instagram Graph API.

    Requires a publicly reachable video URL for container creation in the
    standard API. For local files we use the resumable upload rupload path
    when available; otherwise we instruct the user to use a Drive public link.

    Flow used here:
    1. If INSTAGRAM_VIDEO_URL is set, use that URL.
    2. Else raise with clear setup instructions (local binary upload needs
       Facebook Page video upload + IG media publish).
    """
    token = access_token or os.getenv("INSTAGRAM_ACCESS_TOKEN")
    user_id = ig_user_id or os.getenv("INSTAGRAM_USER_ID")
    if not token or not user_id:
        raise RuntimeError(
            "Set INSTAGRAM_ACCESS_TOKEN and INSTAGRAM_USER_ID in .env "
            "(Instagram Professional account linked to a Facebook Page)."
        )
    if not video_path.exists():
        raise FileNotFoundError(video_path)

    # Prefer explicit public URL (e.g. Drive share link that yields video bytes)
    video_url = os.getenv("INSTAGRAM_VIDEO_URL")
    if not video_url:
        # Attempt Page-hosted upload via rupload + container from file handle
        # Simplified: upload to Facebook video, then publish IG media from URL if provided
        raise RuntimeError(
            "Instagram Reels API requires a public HTTPS video URL for container creation. "
            "After uploading to Drive, set INSTAGRAM_VIDEO_URL to a direct HTTPS link "
            "(or a Drive direct-download URL) and re-run publish --channels Instagram. "
            "Alternatively set it in the job environment for this publish call."
        )

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

    # Wait until finished
    for _ in range(60):
        status = requests.get(
            f"{GRAPH}/{creation_id}",
            params={
                "fields": "status_code",
                "access_token": token,
            },
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
    return {
        "creation_id": creation_id,
        "media_id": media_id,
        "video_url_used": video_url,
    }


def upload_instagram_reel_from_drive_link(
    drive_file_id: str,
    caption: str,
    access_token: str | None = None,
    ig_user_id: str | None = None,
    share_to_feed: bool = True,
) -> dict[str, Any]:
    """Publish using a Google Drive file id as video_url (uc?export=download)."""
    video_url = f"https://drive.google.com/uc?export=download&id={drive_file_id}"
    os.environ["INSTAGRAM_VIDEO_URL"] = video_url
    # dummy path for existence check skipped — call create path directly
    token = access_token or os.getenv("INSTAGRAM_ACCESS_TOKEN")
    user_id = ig_user_id or os.getenv("INSTAGRAM_USER_ID")
    if not token or not user_id:
        raise RuntimeError(
            "Set INSTAGRAM_ACCESS_TOKEN and INSTAGRAM_USER_ID in .env"
        )

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
    return {
        "creation_id": creation_id,
        "media_id": publish.json().get("id"),
        "video_url_used": video_url,
    }
