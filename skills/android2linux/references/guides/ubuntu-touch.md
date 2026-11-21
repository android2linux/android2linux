# Ubuntu Touch

This guide covers installing and living with Ubuntu Touch on a supported phone, as done on the `miatoll` family. It explains the UBports installer flow (including the Partitioning checkbox that is easy to miss), the Android-version prerequisite, enabling Developer Mode and SSH, what read-only system means in practice and which files are writable, why background apps are frozen, the difference between the 24.04-1.x and 2.x series for screen cutouts, screenshots, hosts-file ad blocking, the browser and its Chromium engine, and desktop apps. It is the step before [`postmarketos-unsupported-variant.md`](postmarketos-unsupported-variant.md) in the worked example, and the "ways back" target in [`../devices/xiaomi-redmi-note-9-pro-max.md`](../devices/xiaomi-redmi-note-9-pro-max.md).

## Prerequisite: the right Android base

Ubuntu Touch on this family runs over **Android 10's** hardware drivers through Halium (Halium 10). The installer does **not** downgrade Android for you. If the phone is on a newer Android, flash the appropriate stock Android 10 first (see [`safe-flashing.md`](safe-flashing.md)) or the install will not have the vendor base it expects.

The install described here was Ubuntu Touch **24.04-2.2**: Halium 10 over Android 10 vendor drivers, the Lomiri shell, and Qt WebEngine for the browser (Chromium 140).

## Install with the UBports installer

Use the **UBports Installer 0.11.2** AppImage, checksum verified, with the phone in **fastboot**. It recognises the `miatoll` family directly.

In the installer's options, set:

- **Channel:** `24.04` stable.
- **Wipe Userdata:** on.
- **Partitioning:** **on.** It is off by default, and you need it when coming from Android: it grows the system partition to about 3.5 GB so 24.04 fits.
- **Bootstrap:** on (the default).

The installer downloads about 1 GB, flashes, and the phone boots into Ubuntu Touch. On the Note 9 Pro Max, display, touch, GPU, Wi-Fi and mobile data were seen working; UBports' device page also lists calls and the camera (not tested here).

## Developer Mode and SSH

1. Set a **passcode**.
2. Settings → About → **Developer Mode** → on.
3. With USB connected, `adb shell` now logs in as the user `phablet`.

To work over SSH (key-only logins by default), push your public key and start the server:

```sh
adb shell 'mkdir -p ~/.ssh && chmod 700 ~/.ssh'
adb push ~/.ssh/id_rsa.pub /home/phablet/.ssh/authorized_keys
adb shell -t sudo systemctl enable --now ssh     # asks for the phone passcode
ssh phablet@<phone-ip>
```

Once SSH works, you can drop `adb` for most tasks. See [`working-from-your-pc.md`](working-from-your-pc.md).

## The read-only system, and what you can still change

Ubuntu Touch mounts the system read-only. A small number of files are writable bind mounts, and `/etc/hosts` is one of them. You edit them **in place** rather than replacing them.

The gotcha: `install` fails with **"Read-only file system"** even on those files. Write them with `sudo cp` instead:

```sh
sudo cp /tmp/hosts.new /etc/hosts
```

Apps run under **AppArmor**, and background apps are **SIGSTOPped** when they are not in front — a frozen app does not keep running in the background the way Android or desktop Linux would. Updates go through `system-image-cli`.

## 24.04-1.x versus 24.04-2.x: the cutouts

The phone's device profile describes its rounded corners and camera hole, but the Lomiri shell in the **24.04-1.x** series ignores them: the clock and status icons run under the corners and the camera hole. Cutout support landed in **24.04-2.x**, so switching channel fixes it with no hacks:

```sh
ssh -t phone sudo system-image-cli -v --switch 24.04-2.x/arm64/android9plus/stable
```

The update keeps data and takes about ten minutes. After it, the top bar grew to 101 px and the icons split around the camera. If you install 2.x directly, this is already done.

## Screenshots from the PC

There is no simple screenshot key to reach over SSH, so the project took one by injecting the Volume Up + Volume Down combination into the phone's input devices (`/dev/input/event4` and `event0`) with a small `python3` script over SSH, then copying the newest file out of `~/Pictures/Screenshots/`. The phone must be unlocked. This helper was written for Ubuntu Touch; on postmarketOS you use `grim` instead (see [`chromium-kiosk.md`](chromium-kiosk.md)).

## Hosts-file ad blocking

Because `/etc/hosts` is writable, you can block ads system-wide by merging the **StevenBlack** hosts list (about 76k domains) with the phone's own entries and your own additions, then copying the result into place.

The list missed at least one network: **Taboola's `tblcontent.com`**, which showed up while watching a site's requests over Chrome DevTools from the PC. Adding `0.0.0.0 tblcontent.com` (and its subdomains) to the custom entries closed it. The lesson is that a big list is a good start, not exhaustive — watch real traffic to fill gaps.

Keep the merge in a script and copy the result with `sudo cp`:

```sh
# build hosts.merged = original + StevenBlack + custom, then
scp hosts.merged phone:/tmp/hosts.adblock
ssh -t phone 'sudo cp /tmp/hosts.adblock /etc/hosts'
```

This was installed on Ubuntu Touch, not on postmarketOS. On Ubuntu Touch the browser's requests are visible through Morph's DevTools (below).

## Browser and Chromium

The default browser is **Morph**, whose engine is **Qt WebEngine** (Chromium 140). Only that built-in browser gets GPU acceleration, because Ubuntu Touch draws through Android's GPU drivers. To inspect a page, Morph can expose Chromium remote debugging via `QTWEBENGINE_REMOTE_DEBUGGING`, and the project's DevTools helper relaunches Morph with that set and tunnels the port to the PC:

```sh
systemctl --user set-environment QTWEBENGINE_REMOTE_DEBUGGING=127.0.0.1:9222
```

Then `http://127.0.0.1:9222/json` lists pages and Chrome's `chrome://inspect` attaches. This is also how you find domains to block.

## Desktop apps: Libertine and snaps

Ubuntu Touch can run desktop applications in containers (Libertine) and as snaps. This project **did not exercise either** on Ubuntu Touch, so the notes have nothing recorded on how well they work on this phone. If you need desktop apps, treat them as unverified here and check the current UBports documentation for your release.

## Last verified

Install, SSH, cutout switch, hosts ad blocking and Morph DevTools: done 2026-11-20 on Ubuntu Touch 24.04-2.2. Checked 2026-11-21. Libertine/snaps: not tested.
