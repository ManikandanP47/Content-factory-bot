#!/usr/bin/env bash
# Install / uninstall launchd job for Content Factory (local laptop automation).
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
  # Mon–Fri: 5 evening slots (IST) — post-work / night Shorts scroll peak.
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
    <dict><key>Hour</key><integer>17</integer><key>Minute</key><integer>0</integer></dict>
    <dict><key>Hour</key><integer>18</integer><key>Minute</key><integer>0</integer></dict>
    <dict><key>Hour</key><integer>19</integer><key>Minute</key><integer>0</integer></dict>
    <dict><key>Hour</key><integer>20</integer><key>Minute</key><integer>0</integer></dict>
    <dict><key>Hour</key><integer>21</integer><key>Minute</key><integer>0</integer></dict>
  </array>
  <key>WorkingDirectory</key>
  <string>${ROOT}</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>TZ</key><string>Asia/Kolkata</string>
    <key>AUTO_PUBLISH</key><string>1</string>
    <key>PUBLISH_CHANNELS</key><string>youtube</string>
    <key>YOUTUBE_PRIVACY</key><string>public</string>
    <key>GOOGLE_OAUTH_FLOW</key><string>browser</string>
    <key>POST_ON_WEEKENDS</key><string>0</string>
  </dict>
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
  echo "  Schedule (Mon–Fri): 17:00, 18:00, 19:00, 20:00, 21:00 IST"
  echo "  5 public Shorts/day — evening / night scroll windows"
  echo "  Mac must be awake ~17:00–22:00 on weekdays"
  echo "  Config: $ROOT/.env"
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
