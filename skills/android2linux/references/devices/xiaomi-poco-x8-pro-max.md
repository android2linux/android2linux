# Xiaomi Poco X8 Pro Max (`dash`)

This is the dossier for a phone that has **no Linux path today**: a Poco X8 Pro Max, codename `dash`, on a MediaTek Dimensity 9500s. It explains why there is nothing to install yet, why a GitHub repo that looks like a port is not one, what the unlock situation is, and what you can do instead if the goal is simply Linux on this hardware. It is the counter-example to [`xiaomi-redmi-note-9-pro-max.md`](xiaomi-redmi-note-9-pro-max.md): same brand, very different outcome because of the chip and the codename. For the general method, see [`../guides/assess-your-phone.md`](../guides/assess-your-phone.md).

## Device facts

| | |
|---|---|
| Phone | Poco X8 Pro Max, global model `2602BPC18G` |
| Codename | `dash` |
| SoC | MediaTek Dimensity 9500s (`MT6991`) |
| OS as shipped | HyperOS 3 (Android 16) |
| Bootloader | locked |

## Why there is no Linux path today

- **No port exists for `dash`.** Neither postmarketOS/Nura, Ubuntu Touch, Droidian nor Sailfish list it. A mainline kernel with device tree support has to be written for the SoC and board first, and for a brand-new MediaTek flagship that has not happened.
- **MediaTek makes it harder than Qualcomm.** The practical distinction that matters when you assess a phone (in [`../guides/assess-your-phone.md`](../guides/assess-your-phone.md)) is Qualcomm mainline versus MediaTek. Mainline support for recent Qualcomm SoCs is far ahead; recent MediaTek chips, especially new flagships, usually have none.
- **There is no BROM rescue on this chip.** On many MediaTek phones a bad flash can be recovered through BROM mode. This one has no such recovery, so a failed experiment is not something you can undo with a tool — it is a dead phone. That alone argues for not experimenting until a real port exists.

## The `klee` confusion

There is a GitHub repository, `emir34-34/ubuntu-touch-poco-x8-pro`, whose name invites exactly the wrong conclusion. It is a **real** Ubuntu Touch port — but for the **Poco X8 Pro** (codename `klee`, Dimensity 8500), a **different phone** with a different chip. The installer refuses any codename other than `klee`.

"X8 Pro" and "X8 Pro Max" are unrelated phones inside. This is the single clearest example, in this whole project, of why you check the **codename** and not the marketing name: the repo is genuine, the instructions are genuine, and they still do not apply to this phone. See how to read a random port critically in [`../guides/assess-your-phone.md`](../guides/assess-your-phone.md).

## Unlock situation

Even before a port exists, unlocking this phone is harder than the Redmi was:

- The route is the **Xiaomi Community app**, not the simple Mi Unlock status flow. The quota resets at 00:00 Beijing time, which is 13:00 in Brasília.
- It typically means **a wait of a week or more** before the unlock is granted.
- Xiaomi reportedly allows **one unlock per account per year**. If the same Mi account was already used to unlock another phone (for example the Redmi in this project), that quota may already be spent.

So this is not a phone to plan an install around yet. Treat the unlock as a separate, slow prerequisite that may fail on quota, and check it before buying hardware to experiment on.

## What works instead

If the goal is Linux on this hardware rather than a full replacement OS, the phone already runs it:

- **Android 16's built-in Linux Terminal** — a Debian virtual machine managed by Android. You get a real Linux userland without touching the bootloader.
- **Termux** — a terminal environment with a package manager, running beside Android.

Both keep Android in place, so they are not "freeing the phone" in the sense the rest of this repo means, but they are legitimate ways to get Linux tools today without risking a locked, unrecoverable device. Which one fits depends on whether you want a full Debian VM (Linux Terminal) or a lighter terminal environment (Termux).

## What to watch

- Kernel source for `dash` was released in **July 2026**. Source is a prerequisite for a port, not a port, but it is the first thing that has to exist.
- Watch whether a mainline device tree and a postmarketOS/Nura device package appear for `dash` (or for `MT6991` more broadly). Until then there is nothing to flash.
- Keep an eye on the XDA forum section for this phone: <https://xdaforums.com/f/xiaomi-poco-x8-pro-max-and-redmi-turbo-5-max.13006/>. Community work usually shows up there before it reaches a distro.

## Last verified

Checked 2026-11-21. The "no port" and "no BROM rescue" findings are from the project notes at that date; re-check the distro wikis before acting, since ports appear over time.
