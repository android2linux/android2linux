# Debugging a Qualcomm modem on Linux

This guide is the investigation method that took a modem from "present but refusing to come online" to registered, with data, SMS and calls, on a mainline Qualcomm phone. It is written as a sequence of narrowing steps: confirm the basics, learn the operating-mode states, rule out ModemManager, compare against an OS where the modem works, read the helper-service logs, apply the fix, and know what was ruled out along the way. The actual cause was a userspace helper (`tqftpserv`), not the modem firmware. Use it with [`working-from-your-pc.md`](working-from-your-pc.md) for running commands on the phone and [`../devices/xiaomi-redmi-note-9-pro-max.md`](../devices/xiaomi-redmi-note-9-pro-max.md) for the device context.

## 1. Confirm the basics

Before touching anything, confirm the SIM is seen and the card is usable, without printing identifiers. Over QMI as root on the phone:

```sh
qmicli -d qrtr://0 -p --uim-get-card-status
```

Look at `Card state`, `Application state`, `PIN1 state`, the slot list and personalization. A card that is absent, PIN-locked or not ready explains a lot before you go further.

Ask the modem for its operating mode and, through ModemManager, its operator, signal and access technology:

```sh
qmicli -d qrtr://0 -p --dms-get-operating-mode
mmcli -L
mmcli -m <n>              # state, power state, access tech, signal quality, operator
```

Bands and operator details come from the ModemManager modem object. If the card is fine and the mode is wrong, the section below is the next thing to understand.

## 2. Probe the operating mode

ModemManager's "couldn't enable the modem: … `DeviceNotReady`" (QMI error 52) only says the modem refused to switch its radio on. Ask the modem directly, and try the modes it offers:

```sh
qmicli -d qrtr://0 -p --dms-get-operating-mode
qmicli -d qrtr://0 -p --dms-set-operating-mode=low-power   # or offline, online, reset
```

What the Note 9 Pro Max's modem did, which is the pattern to recognise:

| Request | Result |
|---|---|
| (straight after boot) | already in `shutting-down`, with `HW restricted: no` |
| `low-power` | accepted |
| `offline` | accepted |
| `online` | refused: `DeviceNotReady` |
| `offline` → `low-power` | refused: `InvalidTransition` |
| `reset` (from `shutting-down` or `offline`) | accepted, but the modem never actually restarted: no restart in the kernel log, same mode afterwards |

The modem reported no "offline reason". A modem that accepts every mode except `online` thinks something it needs isn't ready, which points at what it depends on, not at the radio.

Since `reset` may do nothing, restart the modem's processor through the kernel instead, as root:

```sh
echo stop  > /sys/class/remoteproc/remoteproc0/state   # check .../name says "modem" first
echo start > /sys/class/remoteproc/remoteproc0/state
dmesg | grep -i remoteproc0
```

Watch `dmesg` for `remoteproc`, `qcom_q6v5`, `modem`, `sysmon`, `crash`, `fatal`. A clean "remote processor modem is now up" with no crash tells you the firmware loaded and the problem is above it.

## 3. Rule out ModemManager

ModemManager changes the modem's mode on its own, so take it out of the picture:

1. Stop ModemManager (`systemctl stop ModemManager`).
2. Restart the modem through `remoteproc` as above, and wait 10–15 s.
3. Read the mode **before anything touches it**, then try `online` by hand with `qmicli`.
4. Start ModemManager again afterwards.

On this phone the freshly restarted modem was **already in `shutting-down`** with ModemManager stopped, and `online` was still refused. So ModemManager was ruled out, and the modem was giving up during its own startup: something it needs from the Linux side in its first seconds was missing.

## 4. Compare with an OS where it works

If the modem works under another OS (Android, or Ubuntu Touch over Android's kernel and services), you have a known-good baseline: same SIM, same tower, same bands. That comparison rules out the SIM, the carrier account and the hardware, and tells you the fault is in the Linux userspace or kernel you are debugging. On the Note 9 Pro Max, Ubuntu Touch had a working mobile data connection on the same SIM, so the hardware and SIM were never suspect.

## 5. Read the helper-service logs

The kernel loads the modem's firmware (`remoteproc`, from `/lib/firmware`). While it starts, the modem then relies on two small Linux services:

- **`rmtfs`** gives it its stored settings (EFS) from the `modemst1`, `modemst2` and `fsg` partitions.
- **`tqftpserv`** serves it files over **QRTR**: extra firmware such as `wlanmdsp.mbn` under `/readonly/…`, and a scratch folder, `/readwrite/`, where the modem saves temporary files. On Android that folder is persistent storage on the `persist` partition.

```sh
journalctl -b -u tqftpserv -u rmtfs --no-pager
ls -la /tmp/tqftpserv /var/lib/tqftpserv   # where the /readwrite files land, depending on the version
```

The tell was in `tqftpserv`'s log and that folder. The modem wrote `lctoem.tmp` and `mcfg.tmp` (its configuration system, MCFG), then checked their size with **`RRQ … rsize=0 seek=0`**, and did that **about 30 times per boot**. The files in `/readwrite` **stayed 0 bytes**. A modem that can't save and verify its configuration files gives up and refuses `online`.

The cause was **`tqftpserv` 1.1.1**, the version packaged in postmarketOS v26.06: it treated "option requested with value 0" as "option not requested", so the modem's size checks on empty files never got the reply they expected. Upstream fixed it in pull request #50 (September 2026: "a stat-style query against an empty file and an explicit zero seek were silently dropped from the OACK").

Some lines in that log are noise: the modem tries several paths for `wlanmdsp.mbn` (`/readonly/vendor/firmware_mnt/…`, `/readonly/vendor/firmware/…`) and gets it from the last one, and `ota_firewall/ruleset` is simply absent.

## 6. The fix

Use the **upstream `tqftpserv`**, version 1.3 or newer. The one used here was `v1.3-4-geb4b9a0` from `github.com/linux-msm/tqftpserv`, built on the phone itself with **meson** from a checkout in `/tmp/tq`, and installed as `/usr/local/bin/tqftpserv`.

Override the packaged service with a systemd drop-in at `/etc/systemd/system/tqftpserv.service.d/zz-upstream.conf`:

```ini
[Service]
ExecStart=
ExecStart=/usr/local/bin/tqftpserv
StateDirectory=tqftpserv
```

`StateDirectory=tqftpserv` makes its `/readwrite` persist at `/var/lib/tqftpserv` across reboots. Then:

```sh
sudo systemctl daemon-reload
sudo systemctl restart tqftpserv
```

The result on this phone: the modem registered **by itself about 27 s after boot**, data reconnected automatically, and after a real reboot it came up without intervention. SMS worked both ways (`mmcli --messaging-create-sms` to send, text quoted as `text='…'`; Chatty ingests the reply), and calls connected with `mmcli --voice-create-call`, which starts the call by itself. **Call audio was unverified**; `q6voiced`, which routes call audio, is in the v26.06 repo but was not installed.

The packaged 1.1.1 stays installed underneath. **If postmarketOS/Nura ever ships `tqftpserv` ≥ 1.3, remove the override** so the packaged one takes over.

**To undo:** delete the drop-in, then `systemctl daemon-reload` and `systemctl restart tqftpserv`.

## What was ruled out

These were suspected, checked and ruled out:

- **The phone's own modem firmware.** Xiaomi's modem firmware differs per variant, so the variant's own firmware was a natural suspect. Its split parts (`modem.mdt` + `modem.b00…`) were extracted from the ROM's `NON-HLOS.bin`, joined into one `modem.mbn` with [`squash-mdt.py`](../../scripts/squash-mdt.py), and placed at `/lib/firmware/updates/qcom/sm7125/miatoll/modem.mbn`, where the kernel prefers it over the packaged copy. It loaded (`MPSS.AT.4.4.c2-00030`, March 2021) and behaved exactly the same, so it was removed again. Delete the file and reboot to undo.
- **`pd-mapper`.** The userspace `pd-mapper` service isn't installed, but the kernel's built-in `qcom_pd_mapper` maps `qcom,sm7125` to the same table as the SC7180 (modem domains `msm/modem/root_pd`, `msm/modem/wlan_pd`), so the modem's service lookups are answered.
- **The SIM slot.** The SIM was first in slot 2; moving it to slot 1 changed which slot the boot-time `msm-modem-uim-selection` picked, and nothing else.
- **The card, IMEI and bands.** Card present and ready, no PIN, IMEI present, LTE bands covering the carrier.

All are reasonable suspects when a modem won't come online; ruling them out is what pointed to the file server.

## Harmless noise

NetworkManager logs an MTU warning on `qrtr0` and a failure from `50-dns-filter.sh`. Neither breaks connectivity; do not chase them as the cause.

## Last verified

Modem working (Claro, LTE, ~71 % signal, ~28.6 Mbit/s down over IPv4 + IPv6, auto-registration after reboot), SMS both ways, calls connecting: 2026-11-21. Call audio not verified. Checked 2026-11-21.
