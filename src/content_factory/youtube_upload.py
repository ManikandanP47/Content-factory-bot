from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from content_factory.google_auth import get_google_credentials
from content_factory.models import PublishResult

Privacy = Literal["private", "unlisted", "public"]


def upload_youtube_short(
    video_path: Path,
    title: str,
    description: str,
    tags: list[str] | None = None,
    privacy: Privacy = "private",
    category_id: str = "22",
) -> PublishResult:
    """Upload a Short to YouTube. Returns PublishResult for the CLI/job store."""
    tags = tags or []
    if not video_path.exists():
        raise FileNotFoundError(video_path)

    if "#Shorts" not in title and "#shorts" not in title:
        title = f"{title} #Shorts"
    if "#Shorts" not in description and "#shorts" not in description:
        description = f"{description}\n\n#Shorts"

    creds = get_google_credentials()
    youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)

    # Confirm which channel this OAuth token will upload to (one-Gmail setups).
    channels = (
        youtube.channels()
        .list(part="snippet", mine=True)
        .execute()
        .get("items")
        or []
    )
    if channels:
        ch = channels[0]["snippet"]
        print(
            f"[youtube] Authenticated channel: {ch.get('title')} "
            f"(customUrl={ch.get('customUrl', 'n/a')})"
        )
    else:
        print(
            "[youtube] Warning: no channel returned for this Google account. "
            "Uploads may fail or go to the wrong place."
        )

    body: dict[str, Any] = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": tags[:15],
            "categoryId": category_id,
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }
    media = MediaFileUpload(
        str(video_path),
        mimetype="video/mp4",
        resumable=True,
        chunksize=1024 * 1024,
    )
    request = youtube.videos().insert(
        part="snippet,status", body=body, media_body=media
    )
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"[youtube] upload {int(status.progress() * 100)}%")

    video_id = response["id"]
    url = f"https://youtube.com/shorts/{video_id}"
    return PublishResult(
        channel="youtube",
        ok=True,
        detail=video_id,
        url=url,
        meta={"video_id": video_id, "privacy": privacy},
    )
