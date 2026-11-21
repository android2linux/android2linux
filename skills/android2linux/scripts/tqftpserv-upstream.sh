#!/bin/sh
# tqftpserv-upstream.sh - build and install upstream tqftpserv ON THE PHONE.
#
# Why: the packaged tqftpserv 1.1.1 drops zero-valued tsize/seek options from
# its OACK ("a stat-style query against an empty file and an explicit zero seek
# were silently dropped", upstream PR #50). The modem's lctoem.tmp/mcfg.tmp then
# stay empty, the modem loops and refuses to go online. Upstream tqftpserv
# answers those queries correctly.
#
# What it does:
#   install  clones https://github.com/linux-msm/tqftpserv to /tmp, builds it
#            with meson+ninja (installing build deps with apk on Alpine and
#            postmarketOS), installs /usr/local/bin/tqftpserv, writes the
#            systemd drop-in /etc/systemd/system/tqftpserv.service.d/zz-upstream.conf
#            (ExecStart=/usr/local/bin/tqftpserv, StateDirectory=tqftpserv),
#            reloads systemd and restarts tqftpserv.
#   undo     removes that drop-in and restarts the packaged tqftpserv.
#   status   shows which binary the service is running.
#
# Arguments:
#   install | undo | status   (default: status)
#   -h, --help                show this help
#
# Changes: yes. Copy this file to the phone and run it with sudo:
#   scp tqftpserv-upstream.sh pmos:/tmp/ && ssh -t pmos 'sudo sh /tmp/tqftpserv-upstream.sh install'
#
# Example:
#   sudo sh tqftpserv-upstream.sh install
set -eu

SRC=https://github.com/linux-msm/tqftpserv
DEST=/usr/local/bin/tqftpserv
DROPIN=/etc/systemd/system/tqftpserv.service.d/zz-upstream.conf

usage() {
  sed -n '2,28p' "$0" | sed 's/^# \{0,1\}//'
}

need_root() {
  if [ "$(id -u)" != 0 ]; then
    echo "tqftpserv-upstream: run this with sudo" >&2
    exit 1
  fi
}

install_upstream() {
  need_root
  echo "This will build upstream tqftpserv and install it as $DEST, then point systemd at it."
  if command -v apk >/dev/null 2>&1; then
    echo "Installing build dependencies with apk..."
    apk add --no-cache git build-base meson ninja qrtr-dev xz-dev zstd-dev pkgconf
  else
    echo "Not an apk system; make sure git, a C compiler, meson, ninja and qrtr headers are installed." >&2
  fi

  rm -rf /tmp/tqftpserv-src
  git clone --depth 1 "$SRC" /tmp/tqftpserv-src
  cd /tmp/tqftpserv-src
  meson setup build --buildtype=release
  ninja -C build
  install -m 755 build/tqftpserv "$DEST"

  mkdir -p /etc/systemd/system/tqftpserv.service.d
  cat > "$DROPIN" <<'CONF'
[Service]
ExecStart=
ExecStart=/usr/local/bin/tqftpserv
StateDirectory=tqftpserv
CONF

  systemctl daemon-reload
  systemctl restart tqftpserv
  echo "installed $DEST and $DROPIN; tqftpserv restarted"
  status
}

undo() {
  need_root
  echo "This will remove $DROPIN and restart the packaged tqftpserv."
  rm -f "$DROPIN"
  rmdir /etc/systemd/system/tqftpserv.service.d 2>/dev/null || true
  systemctl daemon-reload
  systemctl restart tqftpserv
  echo "drop-in removed; packaged tqftpserv restarted"
  status
}

status() {
  echo "== tqftpserv status"
  systemctl --no-pager --lines=0 status tqftpserv 2>/dev/null || true
  echo "== ExecStart"
  systemctl cat tqftpserv 2>/dev/null | grep -E '^ExecStart' || true
  if [ -x "$DEST" ]; then
    echo "== $DEST"
    "$DEST" --version 2>/dev/null || ls -l "$DEST"
  else
    echo "$DEST is not installed"
  fi
}

action=${1:-status}
case "$action" in
  install) install_upstream ;;
  undo) undo ;;
  status) status ;;
  -h|--help) usage ;;
  *) echo "tqftpserv-upstream: unknown action: $action" >&2; usage >&2; exit 2 ;;
esac
