from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from content_factory.config import resolve_path
from content_factory.google_auth import get_google_credentials
from content_factory.models import PublishResult


def _drive():
    creds = get_google_credentials()
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def _find_folder(service, name: str, parent_id: str | None = None) -> str | None:
    q = [
        f"name = '{name.replace(chr(39), chr(92) + chr(39))}'",
        "mimeType = 'application/vnd.google-apps.folder'",
        "trashed = false",
    ]
    if parent_id:
        q.append(f"'{parent_id}' in parents")
    result = (
        service.files()
        .list(q=" and ".join(q), spaces="drive", fields="files(id, name)", pageSize=1)
        .execute()
    )
    files = result.get("files", [])
    return files[0]["id"] if files else None


def _ensure_folder(service, name: str, parent_id: str | None = None) -> str:
    existing = _find_folder(service, name, parent_id)
    if existing:
        return existing
    meta: dict[str, Any] = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
    }
    if parent_id:
        meta["parents"] = [parent_id]
    created = service.files().create(body=meta, fields="id").execute()
    return created["id"]


def upload_job_to_drive(
    job_dir: Path,
    job_id: str,
    slug: str,
    config: dict[str, Any],
) -> dict[str, Any]:
    """Upload MP4 + script + props under Content Factory/YYYY-MM-DD/<slug>/.

    Returns a dict (folder_id/files/folder_url) so CLI/update_job can store
    it as PublishResult.meta. Use ``upload_job_to_drive_result`` for PublishResult.
    """
    service = _drive()
    root_name = config.get("channels", {}).get(
        "drive_root_folder", "Content Factory"
    )
    root_id = _ensure_folder(service, root_name)
    day_id = _ensure_folder(service, date.today().isoformat(), root_id)
    folder_id = _ensure_folder(service, slug or job_id, day_id)

    job_dir = resolve_path(job_dir)
    uploaded: list[dict[str, str]] = []
    candidates = [
        job_dir / "final.mp4",
        job_dir / "script.json",
        job_dir / "props.json",
        job_dir / "job.json",
    ]
    for path in candidates:
        if not path.exists():
            continue
        media = MediaFileUpload(str(path), resumable=True)
        meta = {"name": path.name, "parents": [folder_id]}
        file = (
            service.files()
            .create(body=meta, media_body=media, fields="id, name, webViewLink")
            .execute()
        )
        uploaded.append(
            {
                "id": file["id"],
                "name": file["name"],
                "link": file.get("webViewLink", ""),
            }
        )

    return {
        "folder_id": folder_id,
        "files": uploaded,
        "folder_url": f"https://drive.google.com/drive/folders/{folder_id}",
    }


def upload_job_to_drive_result(
    job_dir: Path,
    job_id: str,
    slug: str,
    config: dict[str, Any],
) -> PublishResult:
    data = upload_job_to_drive(job_dir, job_id, slug, config)
    return PublishResult(
        channel="drive",
        ok=True,
        detail=data.get("folder_id", ""),
        url=data.get("folder_url"),
        meta=data,
    )
