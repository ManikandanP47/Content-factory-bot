#!/usr/bin/env bash
# Tiny setup on a personal laptop/PC — only enough to get token.json
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

python3 -m venv .venv-auth
# shellcheck disable=SC1091
source .venv-auth/bin/activate
pip install -q 'google-auth-oauthlib>=1.1' 'google-auth>=2.0' 'requests>=2.31'
exec python scripts/google_login_minimal.py
