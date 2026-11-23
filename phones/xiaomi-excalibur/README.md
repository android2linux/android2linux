# Xiaomi Redmi Note 9 Pro Max (`excalibur`)

Runs Ubuntu Touch 24.04 (official port) and postmarketOS v26.06 (unsupported variant, with two fixes). On postmarketOS there is no charger driver yet (it charges slowly), and of the five cameras only the 5 MP macro works, with a device tree of its own and a kernel module fix ([below](#cameras-on-postmarketos)).

## Contents

- [Facts](#facts)
- [Which system](#which-system)
- [Installing Ubuntu Touch](#installing-ubuntu-touch)
- [Installing postmarketOS](#installing-postmarketos)
- [Hardware status](#hardware-status)
- [Going back](#going-back)
- [Notes from testing](#notes-from-testing)
- [Last checked](#last-checked)

## Facts

| | |
|---|---|
| Phone | Redmi Note 9 Pro Max, India model `M2003J6B1I` |
| Codename | `excalibur`, in the `miatoll` family with `curtana` (Note 9S), `joyeuse` (Note 9 Pro global) and `gram` (Poco M2 Pro) |
| SoC | Qualcomm Snapdragon 720G (`SM7125`), Adreno 618 GPU |
| Panel | Huaxing FT8756 (`dsi_ft8756_huaxing_vid_display`) with FocalTech touch; 1080 × 2400, rounded corners, camera hole at the top centre |
| Partitions | A-only (one system slot), dynamic partitions; `boot` 128 MiB, `cache` 384 MiB, `dtbo` 24 MiB, `super` 8 GiB, `userdata` ~105 GiB |
| Bootloader | Unlockable from Linux with MiUnlockTool ([guide](../../skills/android2linux/references/guides/xiaomi-unlock-from-linux.md)). Never relock it while anything but stock MIUI is installed |
| Anti-rollback | Index 1; reported as not enforced on this family |

With one system slot, Linux replaces Android: dual boot isn't practical.

## Which system

| | Ubuntu Touch 24.04 | postmarketOS v26.06 |
|---|---|---|
| Support | Official port, runs over Android 10's hardware drivers (Halium) | Unsupported variant of a supported family; boots with the `joyeuse` device tree and two fixes |
| Hardware | Most complete: charging works; UBports lists calls and the camera as working | Display, touch, GPU, Wi-Fi, 4G data and SMS work; no charger driver, no camera, call audio untested |
| Browser and GPU | Only Qt WebEngine (Chromium 140) gets the GPU | Any current Chromium (156) on any Wayland compositor gets the GPU |
| System | Read-only image, updated by UBports | Alpine-based, writable, packages with `apk` |

Choose Ubuntu Touch for a phone that just works; postmarketOS for a current Linux stack, a custom UI or a kiosk.

## Installing Ubuntu Touch

1. **Unlock the bootloader** ([guide](../../skills/android2linux/references/guides/xiaomi-unlock-from-linux.md)). Unlocking wipes the phone.
2. **Flash the stock Android 10 ROM** (MIUI 12, `excalibur_in_global_images_V12.0.4.0.QJXINXM`, about 3.1 GB): the port runs over Android 10's drivers, and the installer doesn't downgrade for you. Verify it first and use `flash_all.sh`, never `flash_all_lock.sh` ([Safe flashing](../../skills/android2linux/references/guides/safe-flashing.md)). The ROM's anti-rollback index is 1, the same as the phone's.
3. **Run the UBports Installer** (0.11.2) with channel `24.04-2.x` stable and **Wipe Userdata, Partitioning and Bootstrap** on ([Ubuntu Touch](../../skills/android2linux/references/guides/ubuntu-touch.md)). Use the 2.x series: from 24.04-2.0, the status bar avoids the rounded corners and the camera hole.

   <img src="../../docs/images/ubuntu-touch-status-bar-fix.png" width="540" alt="Status bar before and after: on 24.04-1.x the clock runs into the rounded corner; on 24.04-2.x it sits clear and the icons part around the camera hole">

   *Top: 24.04-1.x. Bottom: 24.04-2.x, which reads the phone's cutouts.*

## Installing postmarketOS

The full technique is in [postmarketOS on an unsupported variant](../../skills/android2linux/references/guides/postmarketos-unsupported-variant.md). What this phone needs:

| Fix | Why |
|---|---|
| U-Boot `hwname` match patch | The family's U-Boot picks a device tree by matching `androidboot.hwname=curtana` or `joyeuse` in the command line the phone's bootloader passes; this phone passes `excalibur`. Changing the two `androidboot.hwname=joyeuse` strings in U-Boot's placeholder device tree to `androidboot.hwname=excalib` (same length, a prefix of `excalibur`) makes it match the `joyeuse-huaxing` tree. [`uboot-match-patch.py`](../../skills/android2linux/scripts/uboot-match-patch.py) does it; from the 2025-06-02 release (SHA-256 `6878802d…`) the result has SHA-256 `1909a3d3…`. |
| pmbootstrap `boot_size = 256` | The kernel's boot partition goes into `cache` (384 MiB); pmbootstrap refuses less than 512 MiB unless patched ([`pmbootstrap-small-boot.patch`](../../skills/android2linux/scripts/pmbootstrap-small-boot.patch), then `PMB_ALLOW_SMALL_BOOT=1`). |
| `plymouth.enable=0` | The boot splash is reported to hang this family's display driver. Add it to `device-xiaomi-miatoll`'s `kernel-cmdline.conf` in a local pmaports checkout and bump `pkgrel`. |
| Upstream `tqftpserv` ≥ 1.3 | The modem stays offline with the packaged 1.1.1 ([Qualcomm modem debugging](../../skills/android2linux/references/guides/qualcomm-modem-debugging.md)). [`tqftpserv-upstream.sh install`](../../skills/android2linux/scripts/tqftpserv-upstream.sh) builds it and adds the systemd override. |

Flash from fastboot, U-Boot last:

```sh
fastboot -s <serial> flash cache    xiaomi-miatoll-boot.img
fastboot -s <serial> flash userdata xiaomi-miatoll-root.img
fastboot -s <serial> erase dtbo
fastboot -s <serial> flash boot     u-boot-sm7125-excalibur.img
fastboot -s <serial> reboot
```

After the first boot, for Chromium and web apps: `gsettings set sm.puri.phoc scale-to-fit true` and the other settings in [Chromium kiosk, and Chromium in Phosh](../../skills/android2linux/references/guides/chromium-kiosk.md).

## Hardware status

"Works" means it was tested; "not tested" means it wasn't tried, not that it fails.

| | Ubuntu Touch 24.04-2.x | postmarketOS v26.06 |
|---|---|---|
| Display, backlight | works | works |
| Touch | works | works (FocalTech FT8756) |
| GPU | works (Android drivers via Halium) | works: freedreno, firmware `a630_sqe.fw`, `a630_gmu.bin`; Phosh and WebGL render on the Adreno |
| Wi-Fi | works | works |
| Mobile data | works | works with upstream `tqftpserv`: LTE, IPv4 and IPv6, ~28 Mbit/s down; reconnects after reboot |
| SMS | not tested | works both ways |
| Calls | listed as working by UBports | connect; call audio not tested (`q6voiced` is probably needed) |
| Camera | listed as working by UBports | the 5 MP macro works with the [excalibur device tree and the CSIPHY fix](#cameras-on-postmarketos); main, ultrawide, depth and front don't |
| Speaker | not tested | works, quiet (TAS2562 amplifier) |
| Headphones, microphones, earpiece | not tested | not tested |
| Bluetooth | not tested | controller up |
| Sensors, rotation | not tested | sensor service runs; rotation not tested |
| Buttons, vibration, headset jack | not tested | detected (drv2624 haptics) |
| Charging | works (Android's `qpnp-smb5` driver) | wall charger only, slowly; no driver ([Charging without a driver](../../skills/android2linux/references/guides/charging-without-a-driver.md)) |
| Battery gauge | not tested | capacity and voltage; status always "Unknown" |
| Suspend | not tested | `s2idle` works |
| GPS, NFC, fingerprint | not tested | not tested; the family's postmarketOS wiki lists them as not working |

### Cameras on postmarketOS

The kernel picks the `joyeuse-huaxing` device tree (the U-Boot match patch above), which describes the Redmi Note 9 Pro's cameras: a front `ovti,ov16a1q` and a macro `samsung,s5k5e9` with a `dongwoon,dw9714` focus motor. With it, both fail at boot (`ov16a1q: Cannot read register 12299`, `s5k5e9: Cannot read register 0` after a CCI timeout), and because a sensor never binds, `qcom-camss` never registers `/dev/media0`: no app sees any camera.

The Pro Max's cameras ([camera guide](../../skills/android2linux/references/guides/mainline-camera.md) for how to find them):

| Camera | Sensor | Driver |
|---|---|---|
| Main, 64 MP | Samsung S5KGW1 | none anywhere |
| Ultrawide, 8 MP | OmniVision OV8856 or GalaxyCore GC8034, by unit | OV8856 in mainline; GC8034 none |
| Macro, 5 MP | Samsung S5K5E9 | in the sm7125 kernel (out of tree) |
| Depth, 2 MP | GalaxyCore GC02M1 | none |
| Front, 32 MP | OmniVision OV32A1Q (not joyeuse's OV16A1Q) | none |

**The macro works** with three changes, all in [`camera/`](camera/):

- [`sm7125-xiaomi-excalibur.dts`](camera/sm7125-xiaomi-excalibur.dts): joyeuse's tree with the front sensor and its CAMSS endpoint disabled, the macro's clock at 24 MHz and a second 2.8 V analog rail (TLMM GPIO 43), as Xiaomi's own excalibur kernel has them.
- [`camss-csiphy-fix.patch`](camera/camss-csiphy-fix.patch): the CSIPHY lane table and PHY-enable writes for this SoC, from [asidko/qcom-camss-mainline](https://github.com/asidko/qcom-camss-mainline).
- [`s5k5e9-probe-retry.patch`](camera/s5k5e9-probe-retry.patch): a retry in the sensor driver. On about a third of boots the first read gets no answer, and the CCI controller stays in that state until it suspends and resumes (its autosuspend delay is 1 s); the driver now power-cycles the sensor, waits 2 s and tries again, four tries in all. Eight boots in a row found the camera (four of them on the third try). The device tree also gives the sensor the camera block's power domain (`TITAN_TOP_GDSC`), without which a second try failed with `Failed to enable xvclk` (EBUSY).

Build both on the phone, against the kernel package's own source (tag `sm7125-6.14.7` for `linux-postmarketos-qcom-sm7125` 6.14.7-r0) and its config, and boot the tree from a second boot entry, so the original stays one menu choice away. The steps are in the [camera guide](../../skills/android2linux/references/guides/mainline-camera.md#build-on-the-phone). Then `dmesg` shows `s5k5e9 13-002d: Detected s5k5e9 sensor`, `cam -l` (libcamera 0.7.1) lists it as "Internal back camera", and `cam -c1 --capture=8 --stream role=still --file=frame#.ppm` writes 2584 × 1944 frames at 19 to 38 fps. The image is real and in focus but pale: libcamera has no tuning file for this sensor yet.

The first changes went in together, so which of them the macro needs isn't separated yet; removing the front sensor (so `qcom-camss` can register) is the likely one. Giving the rails a 5 ms start-up delay made no difference and isn't in the tree.

**In apps**, through PipeWire: WirePlumber lists it as "Built-in Back Camera" (libcamera) and the desktop portal reports a camera. Chromium reaches it with `--enable-features=WebRtcPipeWireCamera` once the session runs `graphical-session.target` (the portal's service needs it; a bare sway session doesn't start it).

## Going back

All through fastboot; read [Safe flashing](../../skills/android2linux/references/guides/safe-flashing.md) first.

- **To stock MIUI 12 (Android 10):** flash `excalibur_in_global_images_V12.0.4.0.QJXINXM` with its `flash_all.sh`. It refuses any device but `excalibur` and rewrites every partition, U-Boot included. Never run `flash_all_lock.sh`: relocking with anything but stock MIUI bricks the phone.
- **To Ubuntu Touch:** flash that ROM, then follow [Installing Ubuntu Touch](#installing-ubuntu-touch) from step 3.
- Never flash a ROM for `curtana`, `joyeuse` or `gram`, nor one from another region: a wrong-variant flash is the usual way to hard-brick this family.
- Community reports describe a free EDL recovery for this family (`bkerler/edl` with a patched loader); it's untested here, so don't rely on it.

## Notes from testing

Measurements behind the tables above, from 2026-11-20 and 2026-11-21.

**Charging.** Wall charger, screen off: 75 % → 83 % in 30 minutes, voltage 4152 → 4228 mV. From a PC's USB port the battery still supplied about 55–240 mA (200–350 mA unplugged). The gauge's `current_now` read only about −200 mA while charging; capacity and voltage are more reliable. Full brightness with Firefox open drew about 540 mA, roughly 10 % an hour on the 5,020 mAh battery. `s2idle` suspend and resume work, with a harmless kernel warning on resume.

**Chromium.** In a `cage` kiosk at scale 3: viewport 360 × 800, `devicePixelRatio` 3, WebGL `ANGLE (…, FD618, OpenGL ES 3.2)`, 58–60 fps with WebGL and CSS animations; no hardware video decoding. Safe area: the top 101 px (≈ 34 CSS px) for the camera hole and corners, corner radius about 29 px (≈ 10 CSS px), camera hole at x 491–581 px (≈ 164–194 CSS px).

**Modem.** With `tqftpserv` 1.1.1, its log showed about 30 `RRQ … rsize=0 seek=0` per boot and the `/readwrite` files stayed at 0 bytes. With upstream `v1.3-4-geb4b9a0` the modem registered by itself about 27 seconds after boot. The phone's own modem firmware (from the ROM's `NON-HLOS.bin`, joined with [`squash-mdt.py`](../../skills/android2linux/scripts/squash-mdt.py), `MPSS.AT.4.4.c2-00030`) behaves the same as the packaged one, so the packaged one is fine.

**Ubuntu Touch.** On the 2.x series the status bar is 101 px tall and its icons split around the camera hole. The StevenBlack hosts list misses Taboola's `tblcontent.com`; add it to block that feed.

## Last checked

Ubuntu Touch install: 2026-11-20. postmarketOS install and hardware: 2026-11-20 and 2026-11-21 (modem, SMS, data, charging, Chromium). Cameras: 2026-11-23 (the macro captures; the others not tried).
