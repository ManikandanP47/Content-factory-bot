#!/usr/bin/env bash
# Install / uninstall launchd jobs for Content Factory (local laptop automation).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LABEL="com.contentfactory.daily"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"
SCRIPT="$ROOT/scripts/daily_run.sh"

chmod +x "$SCRIPT"

cmd="${1:-install}"

uninstall() {
  launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
  rm -f "$PLIST"
  echo "Removed $LABEL"
}

install() {
  uninstall
  # Runs at 10:00, 14:00, 17:00 local (IST if Mac timezone is Kolkata)
  cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>${SCRIPT}</string>
  </array>
  <key>StartCalendarInterval</key>
  <array>
    <dict><key>Hour</key><integer>10</integer><key>Minute</key><integer>0</integer></dict>
    <dict><key>Hour</key><integer>14</integer><key>Minute</key><integer>0</integer></dict>
    <dict><key>Hour</key><integer>17</integer><key>Minute</key><integer>0</integer></dict>
  </array>
  <key>WorkingDirectory</key>
  <string>${ROOT}</string>
  <key>StandardOutPath</key>
  <string>${ROOT}/output/logs/launchd.out.log</string>
  <key>StandardErrorPath</key>
  <string>${ROOT}/output/logs/launchd.err.log</string>
  <key>ProcessType</key>
  <string>Background</string>
</dict>
</plist>
EOF
  mkdir -p "$ROOT/output/logs"
  launchctl bootstrap "gui/$(id -u)" "$PLIST"
  launchctl enable "gui/$(id -u)/$LABEL"
  echo "Installed $LABEL"
  echo "  Schedule (Mac local time — set Mac to Asia/Kolkata for IST): 10:00, 14:00, 17:00"
  echo "  Script: $SCRIPT"
  echo "  Topics: $ROOT/config/topics.txt"
  echo "  Test now: $SCRIPT"
  echo "  Uninstall: $0 uninstall"
}

case "$cmd" in
  install) install ;;
  uninstall) uninstall ;;
  *)
    echo "Usage: $0 install|uninstall"
    exit 1
    ;;
esac
