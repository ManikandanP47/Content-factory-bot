#!/usr/bin/env bash
# Install a dedicated Python 3.12 venv with Kokoro male AI voice (am_adam).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export PATH="/Users/manikandan.palanisamy/homebrew/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"

PY=""
for c in \
  "$(brew --prefix python@3.12 2>/dev/null)/bin/python3.12" \
  /Users/manikandan.palanisamy/homebrew/opt/python@3.12/bin/python3.12 \
  /opt/homebrew/opt/python@3.12/bin/python3.12 \
  "$(command -v python3.12 || true)"; do
  if [[ -n "$c" && -x "$c" ]]; then
    PY="$c"
    break
  fi
done

if [[ -z "$PY" ]]; then
  echo "Installing python@3.12 via Homebrew…"
  brew install python@3.12 espeak-ng
  PY="$(brew --prefix python@3.12)/bin/python3.12"
fi

echo "Using $PY"
"$PY" -m venv .venv-voice
source .venv-voice/bin/activate
pip install -U pip
pip install 'kokoro>=0.9.4' 'numpy<2' soundfile

# Smoke test
python - <<'PY'
from kokoro import KPipeline
print("Kokoro OK — default male voice target: am_adam")
PY

echo ""
echo "Done. config/default.yaml already prefers kokoro_voice: am_adam"
echo "Produce with: source .venv/bin/activate && content-factory produce --topic '...'"
