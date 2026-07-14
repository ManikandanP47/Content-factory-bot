#!/usr/bin/env bash
# Daily Content Factory runner (macOS / laptop awake 09:00–20:00 IST).
# Picks a random unused topic from config/topics.txt (no immediate repeats via .topics_done).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export PATH="/Users/manikandan.palanisamy/homebrew/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
export TZ="Asia/Kolkata"

LOG_DIR="$ROOT/output/logs"
mkdir -p "$LOG_DIR"
STAMP="$(date +%Y%m%d-%H%M%S)"
LOG="$LOG_DIR/daily-$STAMP.log"

hour="$(date +%H)"
# Only run while laptop day window 09–20 IST (matches your routine)
if (( 10#$hour < 9 || 10#$hour >= 20 )); then
  echo "[skip] Outside 09:00–20:00 IST (now $(date))" | tee -a "$LOG"
  exit 0
fi

source "$ROOT/.venv/bin/activate"

TOPICS="$ROOT/config/topics.txt"
DONE="$ROOT/config/.topics_done"
touch "$DONE"

# Collect unused topics (skip blanks / comments). Bash 3.2–safe (no namerefs).
# When the pool is exhausted, clear .topics_done and reshape from the full list.
candidates=()
while IFS= read -r line || [[ -n "$line" ]]; do
  line="$(echo "$line" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
  [[ -z "$line" || "$line" == \#* ]] && continue
  if ! grep -Fxq "$line" "$DONE" 2>/dev/null; then
    candidates+=("$line")
  fi
done < "$TOPICS"

if [[ ${#candidates[@]} -eq 0 ]]; then
  : > "$DONE"
  while IFS= read -r line || [[ -n "$line" ]]; do
    line="$(echo "$line" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
    [[ -z "$line" || "$line" == \#* ]] && continue
    candidates+=("$line")
  done < "$TOPICS"
fi

if [[ ${#candidates[@]} -eq 0 ]]; then
  echo "[error] No topics in config/topics.txt" | tee -a "$LOG"
  exit 1
fi

idx=$((RANDOM % ${#candidates[@]}))
topic="${candidates[$idx]}"

echo "[run] $(date) IST — producing (random): $topic" | tee -a "$LOG"
set +e
content-factory produce --topic "$topic" >>"$LOG" 2>&1
code=$?
set -e

if [[ $code -eq 0 ]]; then
  echo "$topic" >> "$DONE"
  echo "[ok] Finished: $topic" | tee -a "$LOG"

  # Optional auto-publish — set AUTO_PUBLISH=1 in env or .env
  if [[ "${AUTO_PUBLISH:-0}" == "1" ]]; then
    job_id="$(ls -1t "$ROOT/output" | grep -v '^logs$' | head -1)"
    if [[ -n "$job_id" ]]; then
      # Default: YouTube Shorts only (MoticateUrself). Set PUBLISH_CHANNELS to override.
      echo "[publish] $job_id → ${PUBLISH_CHANNELS:-youtube}" | tee -a "$LOG"
      content-factory publish --job "$job_id" --channels "${PUBLISH_CHANNELS:-youtube}" >>"$LOG" 2>&1 || true
    fi
  fi
else
  echo "[fail] produce exited $code — see $LOG" | tee -a "$LOG"
  exit "$code"
fi
