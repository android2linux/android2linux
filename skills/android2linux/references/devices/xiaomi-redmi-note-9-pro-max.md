# Xiaomi Redmi Note 9 Pro Max (`excalibur`)

This is the device dossier for one phone that was actually moved off Android onto mainline Linux: a Redmi Note 9 Pro Max, codename `excalibur`, in the `miatoll` family. It records the facts you need to identify the phone, the exact path taken from stock MIUI through Ubuntu Touch to postmarketOS, what works on each system, the specific fixes that made the last step boot, how to get back, and when each claim was last checked. Use it as a worked example next to the general guides in [`../guides/assess-your-phone.md`](../guides/assess-your-phone.md) and [`../guides/postmarketos-unsupported-variant.md`](../guides/postmarketos-unsupported-variant.md).

## Device facts

| | |
|---|---|
| Phone | Redmi Note 9 Pro Max, India model `M2003J6B1I` |
| Codename | `excalibur` |
| Family | `miatoll` — also `curtana` (Note 9S), `joyeuse` (Note 9 Pro global), `gram` (Poco M2 Pro) |
| SoC | Qualcomm Snapdragon 720G (`SM7125`), Adreno 618 GPU |
| Panel | Huaxing FT8756 (`dsi_ft8756_huaxing_vid_display`) with FocalTech touch; 1080×2400, rounded corners, camera hole at the top centre |
| Partitions | A-only, dynamic partitions; `boot` 128 MiB, `cache` 384 MiB, `dtbo` 24 MiB, `super` 8 GiB, `userdata` ~105 GiB |
| Bootloader | unlocked 2026-11-20 with MiUnlockTool; **never relock it** with non-stock software — that bricks the phone. The phone's own bootloader (ABL, with fastboot) is untouched |
| Anti-rollback | index 1; not enforced on this family as far as anyone knows |
| Slots | single system slot (A-only), so dual boot with Android is not realistic — Linux replaces Android |

A-only matters before you start: there is no second slot to fall back on, and every flash writes the one copy in use. See [`../guides/safe-flashing.md`](../guides/safe-flashing.md).

## The path taken

Each arrow is a separate install, with a wipe between them:

1. **Stock MIUI 14, Android 12** (`V14.0.2.0.SJXINXM`) — the state the phone arrived in.
2. **Bootloader unlock** (2026-11-20) — done from Linux with MiUnlockTool, no waiting period for this account, and the phone wiped immediately. See [`../guides/xiaomi-unlock-from-linux.md`](../guides/xiaomi-unlock-from-linux.md).
3. **Android 10 downgrade** — the official MIUI 12 fastboot ROM `excalibur_in_global_images_V12.0.4.0.QJXINXM` (Android 10), about 3.1 GB. Ubuntu Touch on this phone runs over Android 10's hardware drivers, and the installer does not downgrade for you.
4. **Ubuntu Touch 24.04** — installed with the UBports Installer 0.11.2, channel 24.04 stable, Wipe Userdata + Partitioning + Bootstrap on. Display, touch, GPU, Wi-Fi and a mobile data connection were seen working; UBports' device page also lists calls and the camera as working (not tested here). See [`../guides/ubuntu-touch.md`](../guides/ubuntu-touch.md).
5. **Ubuntu Touch 24.04-2.x** — switched channel to get cutout support for the rounded corners and camera hole; the 24.04-1.x series ran the status bar under them.
6. **postmarketOS v26.06** (2026-11-20) — a near-mainline kernel with open GPU drivers, on an **unsupported variant** of a supported family. Excalibur has no device tree of its own; the Note 9 Pro (`joyeuse`) tree is the closest. Making it boot took a 14-byte patch to U-Boot (not upstream) and a locally built device package. See [`../guides/postmarketos-unsupported-variant.md`](../guides/postmarketos-unsupported-variant.md).

Ubuntu Touch draws through Android's GPU drivers, so only its built-in browser (Qt WebEngine) gets acceleration. postmarketOS uses freedreno on mainline, so any current Chromium on any Wayland compositor gets the GPU — that was the reason for the move.

## Hardware status per OS

Status as tested. "Works" means it was exercised; "untested" means it was not tried, not that it fails.

| | Ubuntu Touch 24.04-2.x | postmarketOS v26.06 |
|---|---|---|
| Display, backlight | works | works |
| Touch | works | works (FocalTech FT8756) |
| GPU | works (Android drivers via Halium) | driver and firmware load (`a630_sqe.fw`, `a630_gmu.bin`), `/dev/dri/renderD128`; acceleration confirmed by GPU interrupts, Phosh renders on the Adreno |
| Wi-Fi | works | works (NetworkManager manages it) |
| Calls | listed as working by UBports (not tested here) | connect (dial → ringing → active); **call audio unverified**, `q6voiced` probably needed and not installed |
| Mobile data | works (had a Claro data connection) | works since 2026-11-21; registered on Claro, LTE, signal ~71 %, packet attached, ~28.6 Mbit/s down over IPv4 + IPv6 on `qmapmux0.0` |
| SMS | not recorded | works both ways (2026-11-21) |
| Camera | listed as working by UBports (not tested here) | **none usable** — see below |
| Speaker | not recorded | works, but quiet (TAS2562 amp) |
| Headphones, microphones, earpiece | not recorded | not tested |
| Bluetooth | not recorded | controller up and powered |
| Sensors / rotation | not recorded | two IIO devices, iio-sensor-proxy runs; rotation not confirmed |
| Buttons, haptics, headset jack | not recorded | detected (drv2624 haptics; aw8695 fails its chip-ID check, harmless) |
| Battery gauge | not recorded | reads capacity and voltage; `current_now` sign tells charge direction; status always "Unknown" |
| Charging | charged properly (Android's `qpnp-smb5` driver) | wall charger works, slowly; **no mainline driver** — see [`../guides/charging-without-a-driver.md`](../guides/charging-without-a-driver.md) |
| Suspend | not recorded | `s2idle` works |
| Battery drain | not recorded | ~540 mA at full brightness with Firefox open, about 10 %/hour on the 5,020 mAh battery |
| GPS, NFC, fingerprint | not recorded | GPS not tested; the family wiki says GPS, NFC and fingerprint don't work, mics partial |

The camera deserves its own note. The joyeuse device tree describes a front `ov16a1q`, a macro `s5k5e9` and focus `dw9714`, and no main camera. On excalibur the `s5k5e9` is detected but `ov16a1q` fails (`Cannot read register`, -5) because the Pro Max has a different 32 MP front sensor. Since one sensor never binds, `qcom-camss` never registers its media device (`/sys/bus/media/devices` empty, no `/dev/media*`), so libcamera and Snapshot see nothing. Getting the macro camera would mean disabling the `ov16a1q` node and its camss endpoint in the device tree plus the community qcom-camss CSIPHY kernel patch; the front and main cameras need drivers that don't exist in mainline.

## The fixes that made it work

These are the specific changes that took postmarketOS from "can't boot" to usable on this variant. Each is explained in context in the linked guides; the short version is here so you can see the whole set at once.

| Fix | Why it was needed |
|---|---|
| U-Boot `hwname` match patch | The only U-Boot release for the family picks a device tree by matching `androidboot.hwname=curtana\|joyeuse` in the command line ABL passes. This phone's ABL says `excalibur`, so nothing matched. Changing two same-length placeholder strings `androidboot.hwname=joyeuse` → `androidboot.hwname=excalib` (a substring of `excalibur`) makes it match the joyeuse tree. See [`../guides/postmarketos-unsupported-variant.md`](../guides/postmarketos-unsupported-variant.md). |
| pmbootstrap `boot_size = 256` | The boot image goes into `cache`, which is 384 MiB, not the usual 512 MiB+ boot partition. pmbootstrap refuses a boot size below 512 unless patched; a local patch allows it with `PMB_ALLOW_SMALL_BOOT=1`. |
| `plymouth.enable=0` | The community reports that Plymouth (the boot splash) hangs on this family's display driver; switched off before the first boot. Added to the device's kernel cmdline in a local pmaports build, `pkgrel` bumped 1 → 2. |
| upstream `tqftpserv` ≥ 1.3 | The packaged tqftpserv 1.1.1 mishandled the modem's size queries, so the modem looped and refused to come online (`DeviceNotReady`). Built upstream `v1.3-4-geb4b9a0` and put it in `/usr/local/bin` with a systemd drop-in. See [`../guides/qualcomm-modem-debugging.md`](../guides/qualcomm-modem-debugging.md). |
| Chromium `scale-to-fit` in Phosh | Chromium opens wider than the 360 CSS px screen; a per-app phoc setting shrinks it to fit. Also needs `~/.config/chromium/First Run` to exist so the first-run dialog doesn't overflow. See [`../guides/chromium-kiosk.md`](../guides/chromium-kiosk.md). |
| kiosk boot | `cage` + Chromium full-screen instead of Phosh, through a greetd drop-in. Base for a Chromium-kiosk OS. See [`../guides/chromium-kiosk.md`](../guides/chromium-kiosk.md). |

## Ways back

You can return to either Android or Ubuntu Touch from postmarketOS. Both go through fastboot; see [`../guides/safe-flashing.md`](../guides/safe-flashing.md) before flashing anything.

- **Back to Ubuntu Touch:** flash the stock Android 10 ROM (below), then run the UBports Installer (0.11.2 AppImage, clicks only): channel `24.04-2.x` stable, Wipe Userdata + Partitioning + Bootstrap on. Nothing else to switch — 2.x already has the top-bar cutout fix.
- **Back to stock MIUI 12 (Android 10):** a fastboot flash of `excalibur_in_global_images_V12.0.4.0.QJXINXM` with its `flash_all.sh`. It refuses any device but `excalibur` and rewrites every partition, U-Boot included. **Never run `flash_all_lock.sh`** — relocking the bootloader with anything but stock MIUI bricks the phone.
- **Never** flash a ROM for `curtana`, `joyeuse` or `gram`, nor one from another region: a wrong-variant flash is the usual way to hard-brick.
- If it ever hard-bricks, community reports describe a free EDL recovery for this family (`bkerler/edl` with a patched loader). Not tried here; don't count on it.

## Last verified

- Bootloader unlock and the Android 10 → Ubuntu Touch install: 2026-11-20.
- postmarketOS v26.06 installed and hardware table: tested 2026-11-20.
- Modem registration, SMS, data, charging: 2026-11-21.
- Chromium in Phosh and the kiosk: 2026-11-21.
- Overall dossier: checked 2026-11-21.

Items marked "not recorded" above come from the earlier Ubuntu Touch morning and were not retested; treat them as unknown rather than working.
