#!/bin/sh
# hosts-adblock.sh - build a hosts-file ad blocker and copy it to a phone.
#
# What it does:
#   Downloads the StevenBlack unified hosts list, merges it with an optional
#   custom list and the phone's current /etc/hosts, and validates that every
#   non-comment line is either "0.0.0.0 <domain>" or one of the standard
#   localhost lines. It copies the result to the phone's /tmp and prints the
#   command that installs it.
#
#   On Ubuntu Touch /etc/hosts is a writable bind mount: write it in place with
#   `cp`, not with `install` or `mv` (which replace the file and break the mount).
#
# Arguments:
#   <ssh-host>             SSH host alias or user@host
#   [custom-hosts-file]    extra entries to append (0.0.0.0 domain lines)
#   -o, --output <file>    also keep the merged file here
#   -h, --help             show this help
#
# Changes: read-only on the phone until you run the printed install command.
# The install command needs the phone password.
#
# Example:
#   ./hosts-adblock.sh pmos custom.hosts -o hosts.merged
set -eu

usage() {
  sed -n '2,24p' "$0" | sed 's/^# \{0,1\}//'
}

host=""
custom=""
output=""

while [ $# -gt 0 ]; do
  case "$1" in
    -o|--output)
      [ $# -ge 2 ] || { echo "hosts-adblock: $1 needs a file" >&2; exit 2; }
      output=$2; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    -*)
      echo "hosts-adblock: unknown option $1" >&2; usage >&2; exit 2 ;;
    *)
      if [ -z "$host" ]; then host=$1
      elif [ -z "$custom" ]; then custom=$1
      else echo "hosts-adblock: unexpected argument $1" >&2; exit 2
      fi
      shift ;;
  esac
done

[ -n "$host" ] || { usage >&2; exit 2; }
if [ -n "$custom" ] && [ ! -f "$custom" ]; then
  echo "hosts-adblock: $custom does not exist" >&2
  exit 2
fi

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

echo "Downloading the StevenBlack unified list..."
curl -sfL -o "$tmp/stevenblack.hosts" \
  https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts

echo "Reading the phone's current /etc/hosts..."
ssh -n "$host" 'cat /etc/hosts' > "$tmp/original.hosts"

{
  cat "$tmp/original.hosts"
  printf '\n# --- ad blocking: StevenBlack unified list (%s) ---\n' \
    "$(grep -m1 '^# Date:' "$tmp/stevenblack.hosts" | cut -d' ' -f3- || true)"
  grep -E '^0\.0\.0\.0[[:space:]]' "$tmp/stevenblack.hosts" \
    | grep -v '^0\.0\.0\.0[[:space:]]\+0\.0\.0\.0' \
    | awk 'NF == 2 { print $1, $2 }'
  if [ -n "$custom" ]; then
    printf '\n# --- custom additions ---\n'
    cat "$custom"
  fi
} > "$tmp/hosts.merged"

bad="$tmp/bad"
if ! awk '
  /^[[:space:]]*$/ { next }
  /^[[:space:]]*#/ { next }
  {
    ip = $1
    if (ip == "0.0.0.0") {
      if (NF != 2 || $2 !~ /^[A-Za-z0-9._-]+$/ || $2 == "0.0.0.0") {
        print FNR ": " $0
        bad = 1
      }
    } else if (ip == "127.0.0.1" || ip == "127.0.1.1" || ip == "::1" ||
               ip == "fe00::0" || ip == "ff02::1" || ip == "ff02::2" ||
               ip == "ff02::3") {
      # standard localhost line
    } else {
      print FNR ": " $0
      bad = 1
    }
  }
  END { exit bad ? 1 : 0 }
' "$tmp/hosts.merged" > "$bad"; then
  echo "hosts-adblock: refusing to install; these lines are not allowed:" >&2
  head -20 "$bad" >&2
  echo "(every line must be 0.0.0.0 <domain> or a standard localhost line)" >&2
  exit 1
fi

blocked=$(grep -c '^0\.0\.0\.0[[:space:]]' "$tmp/hosts.merged" || true)
echo "$blocked domains blocked"

if [ -n "$output" ]; then
  cp "$tmp/hosts.merged" "$output"
  echo "merged file: $output"
fi

scp -q "$tmp/hosts.merged" "$host:/tmp/hosts.adblock"
echo "Copied to $host:/tmp/hosts.adblock"
echo "Now run:"
echo "  ssh -t $host 'sudo cp /tmp/hosts.adblock /etc/hosts'"
echo "(On Ubuntu Touch /etc/hosts is a bind mount, so use cp, not install or mv.)"
