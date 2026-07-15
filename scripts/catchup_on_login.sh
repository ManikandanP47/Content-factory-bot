#!/usr/bin/env bash
# Non-admin fallback: when you open/login on weekday evenings, post if slots were missed.
# Does NOT wake a sleeping Mac — runs only while you are logged in.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export TZ="Asia/Kolkata"
hour="$(date +%H)"
dow="$(date +%u)"

if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
fi

if [[ "${POST_ON_WEEKENDS:-0}" != "1" ]] && (( dow >= 6 )); then
  exit 0
fi

if (( 10#$hour < 17 || 10#$hour >= 22 )); then
  exit 0
fi

TARGET="${DAILY_POST_TARGET:-5}"
TODAY="$(date +%Y-%m-%d)"
SLOT_DIR="$ROOT/config/.automation_slots"
mkdir -p "$SLOT_DIR"

count=0
for f in "$SLOT_DIR"/"$TODAY"-*; do
  [[ -e "$f" ]] || continue
  count=$((count + 1))
done

if (( count >= TARGET )); then
  exit 0
fi

# At most one catch-up per login hour (avoid spam if you keep waking the display)
CATCH_MARKER="$SLOT_DIR/.catchup_${TODAY}_$(date +%H)"
if [[ -f "$CATCH_MARKER" ]]; then
  exit 0
fi

LOG_DIR="$ROOT/output/logs"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/catchup-$(date +%Y%m%d-%H%M%S).log"

echo "[catchup] $(date) — posted $count/$TARGET today; running one slot" | tee -a "$LOG"
touch "$CATCH_MARKER"
exec "$ROOT/scripts/daily_run.sh" >>"$LOG" 2>&1
