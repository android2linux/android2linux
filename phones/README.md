# Phones

One folder per phone: what runs on it, how to install it, what works and what doesn't, the fixes that phone needs, and how to go back to Android. The general method lives in the [guides](../skills/android2linux/references/guides/); these folders hold what is specific to one phone.

<!-- CATALOGUE:START -->
| Phone | Codename | Chip | Linux | Last checked |
|---|---|---|---|---|
| [Xiaomi Poco X8 Pro Max](xiaomi-dash/) | `dash` | MediaTek Dimensity 9500s (MT6991) | no Linux port yet | 2026-11-20 |
| [Xiaomi Redmi Note 9 Pro Max](xiaomi-excalibur/) | `excalibur` | Qualcomm Snapdragon 720G (SM7125) | Ubuntu Touch 24.04-2.2: works; postmarketOS v26.06, Phosh: works with gaps | 2026-11-28 |
<!-- CATALOGUE:END -->

## Hardware by area

Status: `works` tested and works; `partial` works with gaps; `broken` does not work; `reported` listed as working by the port's project, not tested here; `untested` not tried.

<!-- HARDWARE:START -->
| Phone, system | Display | Touch | GPU | Wi-Fi | Bluetooth | Modem | Audio | Charging | Battery | Suspend | USB | Cameras | Sensors | GPS | Buttons |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Xiaomi Redmi Note 9 Pro Max (`excalibur`), Ubuntu Touch 24.04-2.2 | works | works | works | works | untested | works | untested | works | untested | untested | untested | reported | untested | untested | untested |
| Xiaomi Redmi Note 9 Pro Max (`excalibur`), postmarketOS v26.06, Phosh | works | works | works | works | partial | partial | partial | partial | partial | works | works | partial | untested | untested | works |
<!-- HARDWARE:END -->

## Add a phone

A phone you got working, or learned can't work yet, is worth a folder, named `<vendor>-<codename>`:

```
phones/<vendor>-<codename>/
  phone.json    vendor, model, codename, family, chip; each Linux system tried: version, status, date checked, and its hardware by area
  README.md     facts, how to install, what works (the generated hardware table), phone-specific fixes, ways back, dates
  devicetree/   the phone's own device tree, if it needs one
  <area>/       a fix for one hardware area (camera/, charging/, …): patches, drivers, config, scripts
```

Each system in `phone.json` may have a `hardware` object that maps an area id to `status`, `notes`, an optional `guide` and an optional `fix`. The area ids and statuses are in [`catalogue.py`](catalogue.py), the single source of truth: display, touch, gpu, wifi, bluetooth, modem, audio, charging, battery, suspend, usb, cameras, sensors, gps, buttons; and works, partial, broken, reported, untested. Where its README shows the hardware table, put `<!-- HARDWARE:START -->` and `<!-- HARDWARE:END -->`; the catalogue fills the block.

A finding that holds for any phone goes in a [guide](../skills/android2linux/references/guides/); what is specific to this phone goes in its folder. In each fix, say whether it applies to this phone only, to its whole family, or to its chip.

Name phones by **codename**: marketing names collide (the Poco X8 Pro and Poco X8 Pro Max are unrelated inside). Leave out serial numbers, IMEIs, phone numbers and other private data. After adding or changing a phone, regenerate the tables above with `python3 phones/catalogue.py`.
