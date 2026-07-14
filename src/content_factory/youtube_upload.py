from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from content_factory.google_auth import get_google_credentials

Privacy = Literal["private", "unlisted", "public"]


def upload_youtube_short(
    video_path: Path,
    title: str,
    description: str,
    tags: list[str],
    privacy: Privacy = "private",
    category_id: str = "22",
) -> dict[str, Any]:
    if not video_path.exists():
        raise FileNotFoundError(video_path)

    if "#Shorts" not in title and "#shorts" not in title:
        title = f"{title} #Shorts"
    if "#Shorts" not in description and "#shorts" not in description:
        description = f"{description}\n\n#Shorts"

    creds = get_google_credentials()
    youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)

    body = {
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
    return {
        "video_id": video_id,
        "url": f"https://youtube.com/shorts/{video_id}",
        "privacy": privacy,
    }
