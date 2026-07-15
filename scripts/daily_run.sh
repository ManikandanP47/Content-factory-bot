#!/usr/bin/env bash
# Daily Content Factory: random topic → fresh B-roll → produce → YouTube Short.
# Mon–Fri: 5 evening slots (17:00–21:00 IST) — post-work / night scroll peak.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export PATH="/Users/manikandan.palanisamy/homebrew/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
export TZ="Asia/Kolkata"

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
# Active window: 09:00–21:59 IST (evening/night slots through 21:00)
if (( 10#$hour < 9 || 10#$hour >= 22 )); then
  echo "[skip] Outside 09:00–22:00 IST (now $(date))" | tee -a "$LOG"
  exit 0
fi

dow="$(date +%u)"  # 1=Mon … 7=Sun
if [[ "${POST_ON_WEEKENDS:-0}" != "1" ]] && (( dow >= 6 )); then
  echo "[skip] Weekends off — posts resume Monday (set POST_ON_WEEKENDS=1 to override)" | tee -a "$LOG"
  exit 0
fi

SLOT_DIR="$ROOT/config/.automation_slots"
mkdir -p "$SLOT_DIR"
SLOT_KEY="$(date +%Y-%m-%d-%H)"
MARKER="$SLOT_DIR/$SLOT_KEY"
if [[ -f "$MARKER" ]]; then
  echo "[skip] Slot $SLOT_KEY already completed" | tee -a "$LOG"
  exit 0
fi

LOCK_DIR="$ROOT/config/.automation.lockdir"
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  echo "[skip] Previous run still in progress — will catch next slot" | tee -a "$LOG"
  exit 0
fi
cleanup() { rmdir "$LOCK_DIR" 2>/dev/null || true; }
trap cleanup EXIT

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

echo "[run] $(date) IST — slot=$SLOT_KEY — topic: $topic" | tee -a "$LOG"

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
      touch "$MARKER"
      echo "[ok] Published $job_id (slot $SLOT_KEY)" | tee -a "$LOG"
    else
      echo "[fail] publish exited $pub_code — see $LOG" | tee -a "$LOG"
      exit "$pub_code"
    fi
  else
    touch "$MARKER"
  fi
else
  echo "[fail] produce exited $code — see $LOG" | tee -a "$LOG"
  exit "${code:-1}"
fi
