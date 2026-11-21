# Safe flashing

This guide is the discipline that keeps a flash from turning a phone into a brick. It covers the read-only checks to run before any write, how to verify a Xiaomi fastboot ROM before you run it (checksum in the filename, the ROM's own `md5sum.xml`, and what `flash_all.sh` guarantees), how to target one device with `-s`, why you never relock, why a wrong-variant flash is the usual brick, and how to use a fast mirror when the vendor's server crawls. Every command here is something to understand before you type it; the checks are cheap, the mistakes are not.

## Read-only checks first

Before flashing anything, ask the phone what it is and what state it is in. These commands do not write:

```sh
fastboot getvar product      # must be your codename, e.g. excalibur
fastboot getvar anti         # anti-rollback index
fastboot getvar unlocked     # yes once unlocked
fastboot getvar slot-count   # 1 = A-only, 2 = A/B
```

If `product` is not the codename you expect, **stop**. You are about to flash the wrong phone or a mislabelled image.

If several devices are connected, `fastboot devices` lists them and every flash must name one with `-s <serial>`. Do not rely on "the only one connected" staying true mid-session.

## Verify a Xiaomi fastboot ROM before running it

A Xiaomi fastboot ROM archive and its contents can be checked before anything touches the phone:

1. **Checksum in the filename.** The official archive name embeds an MD5 prefix, e.g. `...V12.0.4.0.QJXINXM...` with `933f5d8da9…` in the filename. Confirm the file's MD5 matches that prefix.
2. **The ROM's own `md5sum.xml`.** Inside the extracted ROM, every image has an entry. Check all of them (the Android 10 ROM used here had **79 images**, all matching). A single mismatched image means a corrupted download — re-download rather than flash.
3. **The flash script's guards.** Read `flash_all.sh` before running it. The official script:
   - refuses any device whose codename is not the one the ROM is for,
   - declares `CURRENT_ANTI_VER` (the Android 10 ROM declared `1`, equal to the phone's index, so the downgrade cannot trip anti-rollback),
   - **never relocks the bootloader**.

If those guards are not present, do not run it.

## The scripts you must never run

- **`flash_all_lock.sh`** — it relocks the bootloader at the end. With anything but stock MIUI on the phone, this bricks it. Never run it.
- Any flash script from a ROM for a **different codename or region**, even a sibling variant. See below.

Run only the plain `flash_all.sh`:

```sh
bash flash_all.sh -s <serial>
```

## `-s <serial>` on every command

With more than one device, or with a device that re-enumerates, an unqualified `fastboot flash` can write to the wrong target. Put `-s <serial>` on every `fastboot` write and on `erase`:

```sh
fastboot -s <serial> flash boot  <image>
fastboot -s <serial> flash cache <image>
fastboot -s <serial> erase dtbo
fastboot -s <serial> reboot
```

## Never relock

The bootloader was unlocked to allow this. Relocking with modified software is the single most common way these phones die. Leave it unlocked permanently. "Ways back" to stock MIUI still leave it unlocked unless you deliberately run a lock script — don't.

## Wrong-variant flashes are the usual brick

Phones that look identical on the outside are different inside:

- The Redmi Note 9 Pro Max (`excalibur`), Note 9S (`curtana`), Note 9 Pro global (`joyeuse`) and Poco M2 Pro (`gram`) are one family but **not interchangeable**. Never flash a ROM for a sibling.
- Never flash a ROM from another **region**.
- On a family with a community EDL recovery, a brick may be recoverable (for miatoll, reports describe `bkerler/edl` with a patched loader; not tried here). On many MediaTek phones, including the Poco X8 Pro Max, there is **no BROM rescue** at all — a wrong flash is final.

The read-only `getvar product` check plus a ROM whose `flash_all.sh` enforces the codename is what prevents this.

## Fast mirrors for Xiaomi ROMs

Xiaomi's main download server can be extremely slow (about 20 KB/s was observed). A mirror, `bn.d.miui.com`, delivered the same ROM at about 25 MB/s. Use a mirror for the download, then verify the checksum as above — a mirror is acceptable **because** you verify the file, not instead of verifying it. This repository does not link to firmware downloads; get the ROM for your exact model from Xiaomi's official channel and verify it.

## Last verified

Verified ROM: `excalibur_in_global_images_V12.0.4.0.QJXINXM` (Android 10), MD5 `933f5d8da9…`, all 79 images matched `md5sum.xml`, `CURRENT_ANTI_VER=1`. Done 2026-11-20; checked 2026-11-21.
