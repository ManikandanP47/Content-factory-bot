from __future__ import annotations

import os
from pathlib import Path
from typing import Sequence

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from content_factory.config import project_root

# Drive + YouTube in one OAuth consent for simpler setup
DEFAULT_SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
]


def _paths() -> tuple[Path, Path]:
    root = project_root()
    secrets = Path(
        os.getenv("GOOGLE_CLIENT_SECRETS")
        or root / "credentials" / "client_secrets.json"
    )
    if not secrets.is_absolute():
        secrets = root / secrets
    token = Path(
        os.getenv("GOOGLE_TOKEN") or root / "credentials" / "token.json"
    )
    if not token.is_absolute():
        token = root / token
    return secrets, token


def get_google_credentials(
    scopes: Sequence[str] | None = None,
) -> Credentials:
    scopes = list(scopes or DEFAULT_SCOPES)
    secrets, token_path = _paths()
    if not secrets.exists():
        raise FileNotFoundError(
            f"Missing Google OAuth client secrets at {secrets}. "
            "Download OAuth Desktop credentials from Google Cloud Console "
            "and save as credentials/client_secrets.json"
        )

    creds: Credentials | None = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), scopes)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(secrets), scopes
            )
            creds = flow.run_local_server(port=0)
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(creds.to_json(), encoding="utf-8")

    return creds
