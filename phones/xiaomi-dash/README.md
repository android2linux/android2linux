# Xiaomi Poco X8 Pro Max (`dash`)

No Linux system runs on this phone yet. Linux tools run inside Android, through Android 16's Linux Terminal or Termux.

## Contents

- [Facts](#facts)
- [Why there is no Linux port yet](#why-there-is-no-linux-port-yet)
- [Not the Poco X8 Pro](#not-the-poco-x8-pro)
- [Unlocking](#unlocking)
- [Linux inside Android](#linux-inside-android)
- [What exists, and what to watch](#what-exists-and-what-to-watch)
- [Last checked](#last-checked)

## Facts

| | |
|---|---|
| Phone | Poco X8 Pro Max, global model `2602BPC18G`; sold in China as the Redmi Turbo 5 Max |
| Codename | `dash` |
| SoC | MediaTek Dimensity 9500s (`MT6991`) |
| Ships with | HyperOS 3 (Android 16) |
| Partitions | A/B with virtual A/B and dynamic partitions |

## Why there is no Linux port yet

- **No system lists it.** postmarketOS, Ubuntu Touch, Droidian and Sailfish OS have no port for `dash`. A port needs a mainline kernel with a device tree for the board, or a Halium adaptation over its Android drivers, and neither exists.
- **Recent MediaTek flagships have little mainline support.** Mainline Linux has basic support for parts of the MT6991 (clocks, timers, PCIe, I2C), far from a working phone.
- **A failed flash may not be recoverable.** No public BROM exploit exists for this chip generation, and Xiaomi disables the preloader's USB port; recovery needs Xiaomi's authorised service tools. Don't experiment on this phone until a real port exists.

## Not the Poco X8 Pro

The GitHub repository `emir34-34/ubuntu-touch-poco-x8-pro` is a real Ubuntu Touch port, but for the **Poco X8 Pro**: codename `klee`, Dimensity 8500, a different phone. Its installer refuses any codename other than `klee`. Check the **codename**, not the marketing name, before trusting a port ([Assess your phone](../../skills/android2linux/references/guides/assess-your-phone.md)).

## Unlocking

- HyperOS phones are unlocked through the **Xiaomi Community app**: apply under *Unlock bootloader* with a global account at least about 30 days old. The daily quota resets at 00:00 Beijing time (UTC+8) and runs out within seconds.
- After approval, bind the phone in *Developer options → Mi Unlock status* and wait (Xiaomi's figure is 15 days, up to 60), then unlock with Mi Unlock or [MiUnlockTool](https://github.com/MiForge/MiUnlockTool) from Linux ([guide](../../skills/android2linux/references/guides/xiaomi-unlock-from-linux.md)).
- Xiaomi reportedly allows **one unlock per account per year**.
- Chinese units (Redmi Turbo 5 Max) can't be unlocked officially with a global account.

With no port to install, there is no reason to unlock this phone for Linux yet.

## Linux inside Android

- **Android 16's Linux Terminal**: a Debian virtual machine managed by Android (on this chip through MediaTek's GenieZone hypervisor). Turn it on in *Developer options → Linux development environment*. No unlock needed.
- **[Termux](https://termux.dev)**: a terminal with its own package manager, beside Android. Lighter than the virtual machine.

Both leave Android in place: they give you Linux tools, not a Linux phone.

## What exists, and what to watch

- **Kernel source** for `dash` was published in July 2026 (`dash-w-oss` in Xiaomi's `MiCode/Xiaomi_Kernel_OpenSource`). It is the starting point for a port, not a port.
- **Unofficial OrangeFox and TWRP recoveries** and an untested crDroid build exist on XDA; none is a Linux system.
- Watch for a postmarketOS device package or a Halium port for `dash` or the MT6991, and the [XDA forum for this phone](https://xdaforums.com/f/xiaomi-poco-x8-pro-max-and-redmi-turbo-5-max.13006/), where community work shows up first.

## Last checked

2026-11-21. Ports appear over time: check the systems' device lists before acting.
