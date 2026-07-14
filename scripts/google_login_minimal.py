#!/usr/bin/env python3
"""Minimal Google OAuth (browser) — no full Content Factory install needed.

On any machine with personal Gmail + Python 3:

  python3 -m venv .venv-auth && source .venv-auth/bin/activate
  pip install 'google-auth-oauthlib>=1.1' 'google-auth>=2.0' 'requests>=2.31'
  # put Desktop OAuth JSON at credentials/client_secrets.json
  python scripts/google_login_minimal.py

Then copy credentials/token.json (and the same client_secrets.json) to your work Mac.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

ROOT = Path(__file__).resolve().parents[1]
SECRETS = Path(
    os.getenv("GOOGLE_CLIENT_SECRETS") or ROOT / "credentials" / "client_secrets.json"
)
TOKEN = Path(os.getenv("GOOGLE_TOKEN") or ROOT / "credentials" / "token.json")

# Match browser scopes used by content-factory publish
SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
]


def main() -> int:
    if not SECRETS.exists():
        print(
            f"Missing {SECRETS}\n"
            "Download a Desktop OAuth client JSON from Google Cloud Console "
            "and save it there.",
            file=sys.stderr,
        )
        return 1

    # Normalize flat / installed JSON for InstalledAppFlow
    raw = json.loads(SECRETS.read_text(encoding="utf-8"))
    if "installed" not in raw and "web" not in raw and "client_id" in raw:
        SECRETS.write_text(
            json.dumps({"installed": raw}, indent=2) + "\n", encoding="utf-8"
        )

    print("[google] Opening browser — sign in with personal Gmail (MotivateUrSelf)…")
    flow = InstalledAppFlow.from_client_secrets_file(str(SECRETS), SCOPES)
    creds = flow.run_local_server(
        port=0,
        access_type="offline",
        prompt="consent",
    )
    TOKEN.parent.mkdir(parents=True, exist_ok=True)
    TOKEN.write_text(creds.to_json(), encoding="utf-8")
    print(f"[google] Saved {TOKEN}")
    print("Copy token.json + client_secrets.json to the work Mac credentials/ folder.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
