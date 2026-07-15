#!/usr/bin/env bash
# Daily Content Factory: random topic → fresh B-roll → produce → YouTube Short.
# Up to 2 automatic posts/day (noon + evening IST) while laptop is awake 09:00–20:00.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export PATH="/Users/manikandan.palanisamy/homebrew/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
export TZ="Asia/Kolkata"

# Load AUTO_PUBLISH, YOUTUBE_PRIVACY, etc.
if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
fi

LOG_DIR="$ROOT/output/logs"
mkdir -p "$LOG_DIR"
STAMP="$(date +%Y%m%d-%H%M%S)"
LOG="$LOG_DIR/daily-$STAMP.log"

hour="$(date +%H)"
if (( 10#$hour < 9 || 10#$hour >= 20 )); then
  echo "[skip] Outside 09:00–20:00 IST (now $(date))" | tee -a "$LOG"
  exit 0
fi

TODAY="$(date +%Y-%m-%d)"
# noon slot ~12:00, evening slot ~17:30
if (( 10#$hour < 15 )); then
  SLOT="noon"
else
  SLOT="evening"
fi
LAST_RUN="$ROOT/config/.last_automation_${SLOT}"
if [[ -f "$LAST_RUN" ]] && [[ "$(cat "$LAST_RUN" 2>/dev/null)" == "$TODAY" ]]; then
  echo "[skip] Already ran $SLOT slot today ($TODAY)" | tee -a "$LOG"
  exit 0
fi

source "$ROOT/.venv/bin/activate"

TOPICS="$ROOT/config/topics.txt"
DONE="$ROOT/config/.topics_done"
touch "$DONE"

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

echo "[run] $(date) IST — slot=$SLOT — topic: $topic" | tee -a "$LOG"

produce_log="$(mktemp)"
set +e
content-factory produce --topic "$topic" 2>&1 | tee -a "$LOG" | tee "$produce_log"
code=${PIPESTATUS[0]}
set -e

job_id="$(grep '^\[job\]' "$produce_log" | tail -1 | sed 's/^\[job\] //' || true)"
rm -f "$produce_log"

if [[ $code -eq 0 && -n "$job_id" ]]; then
  echo "$topic" >> "$DONE"
  echo "[ok] Produced: $job_id" | tee -a "$LOG"

  if [[ "${AUTO_PUBLISH:-0}" == "1" ]]; then
    privacy="${YOUTUBE_PRIVACY:-public}"
    channels="${PUBLISH_CHANNELS:-youtube}"
    echo "[publish] $job_id → $channels ($privacy)" | tee -a "$LOG"
    set +e
    content-factory publish --job "$job_id" --channels "$channels" --privacy "$privacy" >>"$LOG" 2>&1
    pub_code=$?
    set -e
    if [[ $pub_code -eq 0 ]]; then
      echo "$TODAY" > "$LAST_RUN"
      echo "[ok] Published $job_id" | tee -a "$LOG"
    else
      echo "[fail] publish exited $pub_code — see $LOG" | tee -a "$LOG"
      exit "$pub_code"
    fi
  else
    echo "$TODAY" > "$LAST_RUN"
  fi
else
  echo "[fail] produce exited $code — see $LOG" | tee -a "$LOG"
  exit "${code:-1}"
fi
