# Scripts

Reusable helpers for moving a phone from Android to Linux. Every script takes
its device or host as an argument; none contains a serial number, address,
user name or password.

| Script | What it does | Runs on | Read-only? |
|---|---|---|---|
| `phone-info` | Prints model, device, build, region, verified-boot and slot facts from adb or fastboot. | PC | Read-only |
| `check-rom.py` | Verifies a Xiaomi fastboot ROM: archive MD5, every image in `md5sum.xml`, product check and `CURRENT_ANTI_VER`; warns about `flash_all_lock.sh`. | PC | Read-only |
| `uboot-match-patch.py` | Lists and retargets the appended U-Boot placeholder FDT (`androidboot.hwname`), simulating the match rule. Never touches the FIT. | PC | Read-only on input; writes `-o` |
| `squash-mdt.py` | Joins Qualcomm split firmware (`name.mdt` + `name.b00…bNN`) into one `.mbn`. | PC | Read-only on input; writes `-o` |
| `modem-diag` | Read-only modem checks over SSH: ModemManager summary, QMI mode/SIM state, tqftpserv version and readwrite folder. | PC (over SSH) | Read-only |
| `tqftpserv-upstream.sh` | Builds upstream tqftpserv on the phone and points systemd at it (`install`), or restores the packaged one (`undo`). | Phone | Changes system |
| `battery-log.sh` | Appends capacity, voltage, current and USB state to a log every N seconds; survives logout via `systemd-run`. | Phone | Writes a log |
| `screenshot` | Takes a screenshot over SSH with grim, or via the volume-key gesture on Ubuntu Touch. Refuses while a messenger or mail app is open (`$PRIVATE_APPS`) unless `--allow-private`. | PC | Read-only on Phosh; saves a file on Ubuntu Touch |
| `kiosk/phone-kiosk` | Starts cage + Chromium full-screen kiosk with the right compositor scale. | Phone | Changes the session |
| `kiosk/kiosk.toml` | greetd config that runs the kiosk as a given user. | Phone | Config file |
| `kiosk/zz-kiosk.conf` | greetd drop-in that selects `kiosk.toml`. | Phone | Config file |
| `kiosk/kiosk-on` | Installs and starts the kiosk over SSH (restarts greetd). | PC | Changes the phone |
| `kiosk/kiosk-off` | Removes the kiosk drop-in and restarts greetd. | PC | Changes the phone |
| `kiosk/trial.html` | Test page: FPS, device/WebGL info, CSS and WebGL animation, input, long list. | Phone | Read-only page |
| `devtools-tunnel` | Forwards a phone's DevTools port to the PC. | PC | Opens a local listener |
| `net-capture.mjs` | Lists the domains a page requests, with ok/fail counts and errors. | PC | Read-only |
| `hosts-adblock.sh` | Builds and validates a hosts-file ad blocker, copies it to the phone and prints the install command. | PC | Read-only until you run the printed command |
| `pmbootstrap-small-boot.patch` | Allows a 256 MiB boot partition with `PMB_ALLOW_SMALL_BOOT=1`. | PC | Patch file |

Every script accepts `-h`/`--help`. Scripts that need root on the phone use
`ssh -t <host> 'sudo …'` so the password is typed at the prompt; some also
accept it from `PHONE_PIN` and pipe it to `sudo -S` if you choose to set that.
