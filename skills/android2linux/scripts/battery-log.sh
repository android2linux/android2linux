#!/bin/sh
# battery-log.sh - log a phone's battery state periodically ON THE PHONE.
#
# What it does:
#   Every N seconds it appends a line with the time, capacity %, voltage (mV),
#   current (mA, the raw gauge value; the sign varies by driver) and whether a
#   USB supply is online. It auto-detects the power supply whose type is
#   "Battery" under /sys/class/power_supply.
#
#   Started with `systemd-run --user --unit=battery-log` when available, so it
#   keeps running after the SSH session ends; otherwise it falls back to setsid.
#   It cannot record anything while the phone is suspended (s2idle), so gaps in
#   the log are expected.
#
# Arguments:
#   -i, --interval <sec>   seconds between samples (default 60)
#   -o, --output <file>    log file (default ~/battery.log)
#   --foreground           run the loop in this process (used internally)
#   -h, --help             show this help
#
# Changes: yes. Writes only the log file and, when available, one user systemd
# unit. It reads sysfs.
#
# Example:
#   ./battery-log.sh -i 30 -o ~/battery.log
set -eu

usage() {
  sed -n '2,25p' "$0" | sed 's/^# \{0,1\}//'
}

interval=60
log="${HOME:-/tmp}/battery.log"
foreground=0

while [ $# -gt 0 ]; do
  case "$1" in
    -i|--interval)
      [ $# -ge 2 ] || { echo "battery-log: $1 needs a value" >&2; exit 2; }
      interval=$2; shift 2 ;;
    -o|--output)
      [ $# -ge 2 ] || { echo "battery-log: $1 needs a value" >&2; exit 2; }
      log=$2; shift 2 ;;
    --foreground) foreground=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "battery-log: unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

case "$interval" in
  ''|*[!0-9]*) echo "battery-log: interval must be a whole number of seconds" >&2; exit 2 ;;
esac
[ "$interval" -gt 0 ] || { echo "battery-log: interval must be > 0" >&2; exit 2; }

sample() {
  b=""
  for d in /sys/class/power_supply/*; do
    [ -r "$d/type" ] || continue
    if [ "$(cat "$d/type" 2>/dev/null || true)" = Battery ]; then b=$d; break; fi
  done

  usb=0
  for d in /sys/class/power_supply/*; do
    t=$(cat "$d/type" 2>/dev/null || true)
    [ "$t" = USB ] || continue
    [ "$(cat "$d/online" 2>/dev/null || echo 0)" = 1 ] && usb=1
  done

  cap='?'; mv='?'; ma='?'
  if [ -n "$b" ]; then
    cap=$(cat "$b/capacity" 2>/dev/null || echo '?')
    raw=$(cat "$b/voltage_now" 2>/dev/null || true)
    [ -n "$raw" ] && mv=$(awk -v x="$raw" 'BEGIN { printf "%.0f", x / 1000 }')
    raw=$(cat "$b/current_now" 2>/dev/null || true)
    [ -n "$raw" ] && ma=$(awk -v x="$raw" 'BEGIN { printf "%.1f", x / 1000 }')
  fi

  printf '%s cap=%s%% voltage=%smV current=%smA usb_online=%s\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$cap" "$mv" "$ma" "$usb"
}

if [ "$foreground" = 0 ]; then
  script=$(cd "$(dirname "$0")" && pwd)/$(basename "$0")
  started=0

  if command -v systemd-run >/dev/null 2>&1; then
    uid=$(id -u)
    XDG_RUNTIME_DIR=${XDG_RUNTIME_DIR:-/run/user/$uid}
    DBUS_SESSION_BUS_ADDRESS=${DBUS_SESSION_BUS_ADDRESS:-unix:path=/run/user/$uid/bus}
    export XDG_RUNTIME_DIR DBUS_SESSION_BUS_ADDRESS
    if command -v systemctl >/dev/null 2>&1 \
       && systemctl --user is-active --quiet battery-log 2>/dev/null; then
      echo "battery-log is already running (systemctl --user stop battery-log)" >&2
      exit 1
    fi
    if systemd-run --user --unit=battery-log --collect -- \
         "$script" --foreground -i "$interval" -o "$log"; then
      started=1
      echo "started battery-log as a user unit; log: $log" >&2
    fi
  fi

  if [ "$started" = 0 ]; then
    if command -v setsid >/dev/null 2>&1; then
      setsid -f "$script" --foreground -i "$interval" -o "$log" \
        </dev/null >/dev/null 2>&1
      echo "started battery-log with setsid; log: $log" >&2
    else
      echo "battery-log: neither systemd-run nor setsid is available; use --foreground" >&2
      exit 1
    fi
  fi
  exit 0
fi

[ -s "$log" ] || printf '# time capacity voltage current usb_online\n' >> "$log"
while :; do
  sample >> "$log"
  sleep "$interval"
done
