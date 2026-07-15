#!/usr/bin/env bash
# Keep Mac awake Mon–Fri 16:58–22:05 IST so evening Shorts automation can run.
# Pair with: sudo pmset repeat wake MTWRF 16:58:00  (see setup_wake_schedule.sh)
set -euo pipefail

export TZ="Asia/Kolkata"
hour="$(date +%H)"
min="$(date +%M)"
dow="$(date +%u)"

# Only weekdays unless POST_ON_WEEKENDS=1
if [[ "${POST_ON_WEEKENDS:-0}" != "1" ]] && (( dow >= 6 )); then
  exit 0
fi

# Start window ~16:58; caffeinate until 22:05 IST
if (( 10#$hour < 16 || (10#$hour == 16 && 10#$min < 55) )); then
  exit 0
fi
if (( 10#$hour > 22 || (10#$hour == 22 && 10#$min > 10) )); then
  exit 0
fi

# ~5h10m — covers 17:00, 18:00, 19:00, 20:00, 21:00 produce+publish slots
exec caffeinate -dimsu -t 18600
