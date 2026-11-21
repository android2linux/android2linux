# Phones

One folder per phone: what runs on it, how to install it, what works and what doesn't, the fixes that phone needs, and how to go back to Android. The general method lives in the [guides](../skills/android2linux/references/guides/); these folders hold what is specific to one phone.

<!-- CATALOGUE:START -->
| Phone | Codename | Chip | Linux | Last checked |
|---|---|---|---|---|
| [Xiaomi Poco X8 Pro Max](xiaomi-dash/) | `dash` | MediaTek Dimensity 9500s (MT6991) | no Linux port yet | 2026-11-20 |
| [Xiaomi Redmi Note 9 Pro Max](xiaomi-excalibur/) | `excalibur` | Qualcomm Snapdragon 720G (SM7125) | Ubuntu Touch 24.04-2.2: works; postmarketOS v26.06, Phosh: works with gaps | 2026-11-21 |
<!-- CATALOGUE:END -->

## Add a phone

A phone you got working, or learned can't work yet, is worth a folder, named `<vendor>-<codename>`:

```
phones/<vendor>-<codename>/
  phone.json    vendor, model, codename, family, chip, and each Linux system tried: version, status, date checked
  README.md     facts, how to install, what works and what doesn't, phone-specific fixes, ways back, dates
```

Name phones by **codename**: marketing names collide (the Poco X8 Pro and Poco X8 Pro Max are unrelated inside). Leave out serial numbers, IMEIs, phone numbers and other private data. After adding or changing a phone, regenerate the table above with `python3 phones/catalogue.py`.
