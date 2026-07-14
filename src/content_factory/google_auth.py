from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Sequence

import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from content_factory.config import project_root

# Browser (Desktop) flow — full scopes
BROWSER_SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
]

# Device flow — Google only allows a limited scope set (includes youtube + drive.file).
# `youtube` is enough for Shorts upload; `youtube.upload` is NOT allowed on device flow.
DEVICE_SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/youtube",
]

DEFAULT_SCOPES = DEVICE_SCOPES

DEVICE_CODE_URL = "https://oauth2.googleapis.com/device/code"
TOKEN_URL = "https://oauth2.googleapis.com/token"


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


def _oauth_flow_mode() -> str:
    # device = phone/other PC approves at google.com/device (best for locked-down Macs)
    # browser = local browser popup (Desktop OAuth client)
    mode = (os.getenv("GOOGLE_OAUTH_FLOW") or "device").strip().lower()
    if mode not in {"device", "browser"}:
        raise ValueError(
            f"Invalid GOOGLE_OAUTH_FLOW={mode!r}; use 'device' or 'browser'"
        )
    return mode


def _load_client_secrets(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if "installed" in data:
        return data["installed"]
    if "web" in data:
        return data["web"]
    if "client_id" in data:
        return data
    raise ValueError(
        f"Unrecognized client secrets format in {path}. "
        "Expected installed/web OAuth client JSON from Google Cloud Console."
    )


def _save_token(token_path: Path, creds: Credentials) -> None:
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(creds.to_json(), encoding="utf-8")


def _run_device_flow(secrets_path: Path, scopes: Sequence[str]) -> Credentials:
    """OAuth device code flow — approve on phone at google.com/device."""
    client = _load_client_secrets(secrets_path)
    client_id = client["client_id"]
    client_secret = client.get("client_secret")
    if not client_secret:
        raise ValueError(
            "client_secrets.json is missing client_secret. "
            "Create an OAuth client of type "
            "'TVs and Limited Input devices' and download JSON again."
        )

    print(
        "[google] Starting device login (no browser on this Mac)…\n"
        "  Tip: On Google Cloud, the OAuth client type must be "
        "'TVs and Limited Input devices' (Desktop clients cannot use device flow)."
    )
    resp = requests.post(
        DEVICE_CODE_URL,
        data={"client_id": client_id, "scope": " ".join(scopes)},
        timeout=30,
    )
    if resp.status_code >= 400:
        detail = resp.text
        raise RuntimeError(
            "Device code request failed. "
            "If you see invalid_client, create a new OAuth client with type "
            "'TVs and Limited Input devices' and replace credentials/client_secrets.json.\n"
            f"HTTP {resp.status_code}: {detail}"
        )
    payload = resp.json()
    verify_url = payload.get("verification_url") or "https://www.google.com/device"
    user_code = payload["user_code"]
    device_code = payload["device_code"]
    interval = int(payload.get("interval") or 5)
    expires_in = int(payload.get("expires_in") or 1800)

    print(
        "\n========== Google device login ==========\n"
        f"1) On your phone (personal Gmail), open:\n   {verify_url}\n"
        f"2) Enter this code:\n   {user_code}\n"
        "3) Sign in as MotivateUrSelf (@MotivateUrSelf-y9h) owner → Allow\n"
        "=========================================\n"
        "Waiting for approval…"
    )

    deadline = time.time() + expires_in
    while time.time() < deadline:
        time.sleep(interval)
        token_resp = requests.post(
            TOKEN_URL,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "device_code": device_code,
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            },
            timeout=30,
        )
        body = token_resp.json()
        if token_resp.status_code == 200 and "access_token" in body:
            print("[google] Device login OK — saving token.json")
            return Credentials(
                token=body["access_token"],
                refresh_token=body.get("refresh_token"),
                token_uri=TOKEN_URL,
                client_id=client_id,
                client_secret=client_secret,
                scopes=list(scopes),
            )
        error = body.get("error")
        if error in {"authorization_pending", "slow_down"}:
            if error == "slow_down":
                interval += 2
            continue
        if error == "access_denied":
            raise RuntimeError("Google login denied in the phone browser.")
        if error == "expired_token":
            raise RuntimeError("Device code expired — run google-login again.")
        raise RuntimeError(f"Device login failed: {body}")

    raise RuntimeError("Timed out waiting for Google device approval.")


def _run_browser_flow(secrets_path: Path, scopes: Sequence[str]) -> Credentials:
    flow = InstalledAppFlow.from_client_secrets_file(str(secrets_path), scopes)
    auth_kwargs: dict[str, Any] = {
        "port": 0,
        "access_type": "offline",
        "prompt": "select_account",
    }
    login_hint = os.getenv("GOOGLE_LOGIN_HINT", "").strip()
    if login_hint:
        auth_kwargs["login_hint"] = login_hint
    return flow.run_local_server(**auth_kwargs)


def get_google_credentials(
    scopes: Sequence[str] | None = None,
) -> Credentials:
    mode = _oauth_flow_mode()
    if scopes is None:
        scopes = DEVICE_SCOPES if mode == "device" else BROWSER_SCOPES
    scopes = list(scopes)

    secrets, token_path = _paths()
    if not secrets.exists():
        raise FileNotFoundError(
            f"Missing Google OAuth client secrets at {secrets}. "
            "For device login, download an OAuth client of type "
            "'TVs and Limited Input devices' as credentials/client_secrets.json"
        )

    creds: Credentials | None = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), scopes)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        elif mode == "device":
            creds = _run_device_flow(secrets, scopes)
        else:
            creds = _run_browser_flow(secrets, scopes)
        _save_token(token_path, creds)

    return creds


def run_google_login(*, force: bool = False) -> Path:
    """Interactive login; writes credentials/token.json. Returns token path."""
    _, token_path = _paths()
    if force and token_path.exists():
        token_path.unlink()
    get_google_credentials()
    return token_path
