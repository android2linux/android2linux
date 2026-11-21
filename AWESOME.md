# Awesome: leaving Android for Linux

A curated list of what you need to put Linux on a phone and live with it, from the people and projects that made it possible. Everything here was used or checked while writing android2linux (November 2026). Suggestions welcome: open an issue or a pull request.

## Operating systems

- [postmarketOS](https://postmarketos.org) (renamed [Nura](https://nura.eco) in 2026): Alpine-based, near-mainline kernels, many devices; its [wiki](https://wiki.postmarketos.org) has a page per device with what works.
- [Ubuntu Touch](https://ubports.com): Ubuntu with the Lomiri shell, running over Android's hardware drivers (Halium); the most complete hardware support where a port exists. [Device list](https://devices.ubuntu-touch.io).
- [Droidian](https://droidian.org): Debian with Phosh over Android drivers (Halium).
- [Mobian](https://mobian-project.org): Debian for mainline-capable phones.
- [Sailfish OS](https://sailfishos.org): Jolla's OS, with community ports.

## Is my phone supported?

- [postmarketOS devices](https://wiki.postmarketos.org) and [Ubuntu Touch devices](https://devices.ubuntu-touch.io): check by **codename**, not marketing name.
- [LINMOB.net](https://linmob.net): news and context on Linux phones.

## Unlocking and flashing

- [MiUnlockTool](https://github.com/MiForge/MiUnlockTool): unlock a Xiaomi bootloader from Linux or macOS, with browser login.
- [Xiaomi Firmware Updater](https://xmfirmwareupdater.com): index of official Xiaomi ROMs by codename and version.
- [UBports Installer](https://github.com/ubports/ubports-installer): installs Ubuntu Touch from a PC.
- [pmbootstrap](https://gitlab.nura.eco/nura/pmbootstrap): builds and flashes postmarketOS images; install it from git, the PyPI release is old.
- [bkerler/edl](https://github.com/bkerler/edl) and [mtkclient](https://github.com/bkerler/mtkclient): low-level recovery tools for Qualcomm (EDL) and MediaTek (BROM) devices. Last resorts; read before running.

## Porting and bring-up

- [sm7125-mainline](https://github.com/sm7125-mainline): kernel, U-Boot and firmware for the Snapdragon 720G family (Redmi Note 9S/Pro/Pro Max, Poco M2 Pro, Galaxy A52/A72).
- [tqftpserv](https://github.com/linux-msm/tqftpserv): the file server Qualcomm modems use at startup. Version 1.3 or newer fixed a bug that kept some modems offline.

## Shells, compositors and screen tools

- [Phosh](https://phosh.mobi): the GNOME-based phone shell used by postmarketOS, Mobian and Droidian.
- [Plasma Mobile](https://plasma-mobile.org): KDE's phone shell.
- [cage](https://github.com/cage-kiosk/cage): a single-window Wayland compositor, the simplest base for a kiosk or a custom web UI.
- [grim](https://sr.ht/~emersion/grim/) and [wf-recorder](https://github.com/ammen99/wf-recorder): screenshots and screen recordings on wlroots-based compositors (Phosh, cage), runnable over SSH.

## Apps

- [LinuxPhoneApps.org](https://linuxphoneapps.org): the catalogue of apps made for Linux phones. Start here.
- [android2linux apps](apps/): web apps reworked for phone screens, with one installer.
- WhatsApp on a Linux phone: [Karere](https://github.com/tobagin/karere) ([Flathub](https://flathub.org/apps/io.github.tobagin.karere)), [ZapZap](https://github.com/rafatosta/zapzap) and [Whatsie](https://github.com/keshavbhatt/whatsie) are full clients; [whatsapp-web-ios](https://github.com/Etelis/whatsapp-web-ios) has the two-page layout technique the android2linux WhatsApp app borrows.
- [Waydroid](https://waydro.id): runs Android apps in a container on Linux, for the ones you can't replace yet.
- [StevenBlack/hosts](https://github.com/StevenBlack/hosts): a maintained hosts-file blocklist for system-wide ad and tracker blocking.

## Doing it with an AI pair

- [The android2linux skill](skills/android2linux/SKILL.md): loads the method, safety rules and references into your assistant.
- [Agent skills in Claude Code](https://code.claude.com/docs/en/skills): how skills are installed and used.
- Know the rules of the community you talk to: [postmarketOS/Nura's AI policy](https://docs.nura.eco/policies-and-processes/development/ai-policy.html) forbids AI-made contributions; the [Linux kernel's](https://docs.kernel.org/process/generated-content.html) allows them with disclosure. See [Communities and AI](skills/android2linux/references/guides/communities-and-ai.md).
