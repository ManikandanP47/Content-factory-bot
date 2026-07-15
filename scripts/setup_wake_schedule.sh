#!/usr/bin/env bash
# Wake + stay-awake for evening Shorts (17:00–21:00 IST).
# Non-admin Macs: use keepawake-only + catchup-on-login (no sudo).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LABEL_AWAKE="com.contentfactory.keepawake"
LABEL_CATCHUP="com.contentfactory.catchup"
PLIST_AWAKE="$HOME/Library/LaunchAgents/${LABEL_AWAKE}.plist"
PLIST_CATCHUP="$HOME/Library/LaunchAgents/${LABEL_CATCHUP}.plist"
KEEP_SCRIPT="$ROOT/scripts/keep_awake_evening.sh"
CATCHUP_SCRIPT="$ROOT/scripts/catchup_on_login.sh"

chmod +x "$KEEP_SCRIPT" "$CATCHUP_SCRIPT"

cmd="${1:-install}"

launchctl_load() {
  local label="$1" plist="$2" name="$3"
  launchctl bootout "gui/$(id -u)/$label" 2>/dev/null || true
  if launchctl bootstrap "gui/$(id -u)" "$plist" 2>/dev/null; then
    launchctl enable "gui/$(id -u)/$label" 2>/dev/null || true
    echo "Installed $name"
    return 0
  fi
  # Stale registration — bootout again and retry once
  launchctl bootout "gui/$(id -u)/$label" 2>/dev/null || true
  sleep 1
  if launchctl bootstrap "gui/$(id -u)" "$plist"; then
    launchctl enable "gui/$(id -u)/$label" 2>/dev/null || true
    echo "Installed $name (retry)"
    return 0
  fi
  echo "Failed to load $name — try: launchctl bootout gui/$(id -u)/$label; launchctl bootstrap gui/$(id -u) $plist" >&2
  return 1
}

status() {
  for label in "$LABEL_AWAKE" "$LABEL_CATCHUP"; do
    if launchctl print "gui/$(id -u)/$label" &>/dev/null; then
      echo "OK  $label"
    else
      echo "MISSING  $label"
    fi
  done
}

uninstall() {
  launchctl bootout "gui/$(id -u)/$LABEL_AWAKE" 2>/dev/null || true
  launchctl bootout "gui/$(id -u)/$LABEL_CATCHUP" 2>/dev/null || true
  rm -f "$PLIST_AWAKE" "$PLIST_CATCHUP"
  echo "Removed keep-awake + catch-up agents"
  if command -v pmset >/dev/null 2>&1; then
    echo "If you had admin wake before: sudo pmset repeat cancel"
  fi
}

install_keepawake() {
  launchctl bootout "gui/$(id -u)/$LABEL_AWAKE" 2>/dev/null || true
  rm -f "$PLIST_AWAKE"
  cat > "$PLIST_AWAKE" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${LABEL_AWAKE}</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>${KEEP_SCRIPT}</string>
  </array>
  <key>StartCalendarInterval</key>
  <array>
    <dict><key>Weekday</key><integer>1</integer><key>Hour</key><integer>16</integer><key>Minute</key><integer>58</integer></dict>
    <dict><key>Weekday</key><integer>2</integer><key>Hour</key><integer>16</integer><key>Minute</key><integer>58</integer></dict>
    <dict><key>Weekday</key><integer>3</integer><key>Hour</key><integer>16</integer><key>Minute</key><integer>58</integer></dict>
    <dict><key>Weekday</key><integer>4</integer><key>Hour</key><integer>16</integer><key>Minute</key><integer>58</integer></dict>
    <dict><key>Weekday</key><integer>5</integer><key>Hour</key><integer>16</integer><key>Minute</key><integer>58</integer></dict>
  </array>
  <key>EnvironmentVariables</key>
  <dict>
    <key>TZ</key><string>Asia/Kolkata</string>
    <key>POST_ON_WEEKENDS</key><string>0</string>
  </dict>
  <key>StandardOutPath</key>
  <string>${ROOT}/output/logs/keepawake.out.log</string>
  <key>StandardErrorPath</key>
  <string>${ROOT}/output/logs/keepawake.err.log</string>
</dict>
</plist>
EOF
  launchctl_load "$LABEL_AWAKE" "$PLIST_AWAKE" "keep-awake (16:58 IST, no admin)"
}

install_catchup() {
  launchctl bootout "gui/$(id -u)/$LABEL_CATCHUP" 2>/dev/null || true
  rm -f "$PLIST_CATCHUP"
  cat > "$PLIST_CATCHUP" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${LABEL_CATCHUP}</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>${CATCHUP_SCRIPT}</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>ThrottleInterval</key>
  <integer>1800</integer>
  <key>EnvironmentVariables</key>
  <dict>
    <key>TZ</key><string>Asia/Kolkata</string>
    <key>POST_ON_WEEKENDS</key><string>0</string>
  </dict>
  <key>StandardOutPath</key>
  <string>${ROOT}/output/logs/catchup.out.log</string>
  <key>StandardErrorPath</key>
  <string>${ROOT}/output/logs/catchup.err.log</string>
</dict>
</plist>
EOF
  launchctl_load "$LABEL_CATCHUP" "$PLIST_CATCHUP" "login catch-up (no admin)"
}

install_wake_admin() {
  if ! command -v pmset >/dev/null 2>&1; then
    return 1
  fi
  echo "Installing system wake (requires admin password)…"
  sudo pmset repeat cancel 2>/dev/null || true
  sudo pmset repeat wake MTWRF 16:58:00
  pmset -g sched || true
}

case "$cmd" in
  install)
    install_keepawake
    install_catchup
    if install_wake_admin 2>/dev/null; then
      echo "Admin wake schedule installed."
    else
      echo ""
      echo "No admin access — that's OK. Use this workflow instead:"
      echo "  1. Open laptop Mon–Fri ~17:00–22:00 (logged in, lid open, plugged in)"
      echo "  2. keep-awake tries to prevent sleep while slots run"
      echo "  3. catch-up posts once per hour when you login if slots were missed"
    fi
    ;;
  install-no-admin)
    install_keepawake
    install_catchup || {
      echo ""
      echo "Catch-up agent failed — run: $0 catchup-only"
      exit 1
    }
    echo "Non-admin mode: open laptop evenings; catch-up handles missed slots."
    echo "Check: $0 status"
    ;;
  uninstall) uninstall ;;
  status) status ;;
  wake-only)
    install_wake_admin || {
      echo "Wake schedule needs admin (sudo). Use: install-no-admin"
      exit 1
    }
    ;;
  keepawake-only) install_keepawake ;;
  catchup-only) install_catchup ;;
  *)
    echo "Usage: $0 install|install-no-admin|uninstall|status|wake-only|keepawake-only|catchup-only"
    exit 1
    ;;
esac
