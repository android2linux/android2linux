# Your own interface, as a session on the login screen

How to run an interface of your own on postmarketOS (a web page, a compositor setup, a shell you are building) as a session you pick on the login screen, next to Phosh. Phosh stays installed and stays the default, so getting back is a log out away.

Reference setup: postmarketOS v26.06 with Phosh and its login screen (Phrog on greetd), sway 1.12 (rc3) and Chromium 156, on a Xiaomi Redmi Note 9 Pro Max (excalibur).

## Contents

- [Why a session and not a kiosk switch](#why-a-session-and-not-a-kiosk-switch)
- [The three files](#the-three-files)
- [What Phosh did that your session must do](#what-phosh-did-that-your-session-must-do)
- [The power key](#the-power-key)
- [Logs and screenshots](#logs-and-screenshots)
- [Going back](#going-back)
- [Last verified](#last-verified)

## Why a session and not a kiosk switch

[The kiosk](chromium-kiosk.md#the-kiosk-greetd-switch) replaces Phosh by pointing greetd at another config: the phone boots straight into your interface, and getting back means SSH and `sudo`. A session is lighter: the login screen lists every file in `/usr/share/wayland-sessions/`, so you add one, pick it when you log in, and pick Phosh again when something breaks. Use the kiosk switch only once the interface is ready to be the only one.

## The three files

**The entry** the login screen lists, `/usr/share/wayland-sessions/myshell.desktop`:

```ini
[Desktop Entry]
Name=My shell
Comment=Log out to go back to Phosh
Exec=/usr/local/bin/myshell-session
Type=Application
```

**The launcher** it names, `/usr/local/bin/myshell-session`, which only starts a script in your home, so you can change the session without `sudo`:

```sh
#!/bin/sh
exec "$HOME/.local/opt/myshell/session.sh"
```

**The session** itself, `~/.local/opt/myshell/session.sh`: a compositor and what runs in it. With sway running Chromium as an app window:

```sh
#!/bin/sh
set -eu
export XDG_RUNTIME_DIR=${XDG_RUNTIME_DIR:-/run/user/$(id -u)}
export DBUS_SESSION_BUS_ADDRESS=${DBUS_SESSION_BUS_ADDRESS:-unix:path=$XDG_RUNTIME_DIR/bus}
export XDG_SESSION_TYPE=wayland XDG_CURRENT_DESKTOP=myshell
config=$XDG_RUNTIME_DIR/myshell-sway.conf
cat > "$config" <<CONF
default_border none
output * scale 3
input type:touch map_to_output DSI-1
exec chromium --ozone-platform=wayland --no-first-run --user-data-dir=$HOME/.local/share/myshell --app=https://example.org/
CONF
if command -v pulseaudio >/dev/null; then pulseaudio --start || true; fi
exec systemd-cat -t myshell sway --config "$config"
```

Install the first two as root (`install -m 644` for the entry, `install -m 755` for the launcher), make the script executable, then log out of Phosh and pick **My shell** on the login screen.

- `DSI-1` is the panel's output name on this phone; `swaymsg -t get_outputs` lists yours. Without `map_to_output`, touches land at the wrong place when another output appears.
- Scale 3 gives 360 × 800 CSS px on a 1080 × 2400 panel. A plain app window (`--app=`) has no minimum width; an installed web app can't be narrower than 500 px ([why](chromium-kiosk.md#why-the-page-is-opened-as-an-app-window)), so for one use scale 2 (540 px) and zoom the page.
- Its own `--user-data-dir` keeps this Chromium apart from the one you use in Phosh.

## What Phosh did that your session must do

Phosh's session starts things your session doesn't get for free. What was missing when sway ran on its own:

- **Sound.** postmarketOS starts PulseAudio from Phosh's autostart entries. Without them there is no sound until the session starts it (`pulseaudio --start`, above).
- **The session bus address.** Set `DBUS_SESSION_BUS_ADDRESS` before anything uses `gsettings`, NetworkManager's agent or notifications.
- **An on-screen keyboard.** sway has none. Draw one in your interface, as a web page must in the [kiosk](chromium-kiosk.md#no-on-screen-keyboard-in-cage).
- **Locking and the screen going off when idle.** Nothing does it until you add it: `swayidle`, or your interface.
- **Brightness.** Phosh sets it for you. A user can set it without root through logind's `SetBrightness` (`busctl call org.freedesktop.login1 /org/freedesktop/login1/session/auto org.freedesktop.login1.Session SetBrightness ssu backlight <device> <value>`, the device from `/sys/class/backlight/`).

## The power key

With Phosh gone, nobody claims the power key, and logind's default for a short press is to **power the phone off**. Hold that back, and give sway the key instead:

1. Start sway under an inhibitor, so logind leaves the key alone while the session runs:
   ```sh
   exec systemd-cat -t myshell systemd-inhibit --what=handle-power-key --who=myshell \
     --why="the session handles the power key" sway --config "$config"
   ```
2. Bind the key in sway, `--locked` so it works with the screen off:
   ```
   bindsym --locked XF86PowerOff exec ~/.local/opt/myshell/power-key
   ```
3. The script turns the screen off when it shows, else on. The panel's first commit after it was off can fail, so it asks again until the output reports power:
   ```sh
   #!/bin/sh
   if swaymsg -r -t get_outputs | grep -q '"power": true'; then
     swaymsg output '*' power off >/dev/null
   else
     for i in 1 2 3 4 5 6; do
       swaymsg output '*' power on >/dev/null
       sleep 0.4
       swaymsg -r -t get_outputs | grep -q '"power": true' && break
     done
   fi
   ```

Don't rely on the key reaching your interface as a key press: with the screen off it may not, and the phone then can't be woken. If the interface needs to know (to lock, say), have it follow the output's state: `swaymsg -m -t subscribe '["output"]'` prints a line whenever it changes.

## Logs and screenshots

- `systemd-cat -t myshell` sends the session's output to the journal: `journalctl -t myshell` over SSH. The login screen would otherwise give it the console, where you can't read it.
- A screenshot over SSH needs the session's Wayland socket. The newest one in the runtime directory is your session's:
  ```sh
  ssh pmos 'cd /run/user/$(id -u) && WAYLAND_DISPLAY=$(ls -t wayland-[0-9] | head -1) grim /tmp/screen.png'
  ```

## Going back

Log out (`swaymsg exit` over SSH, or a way out in your interface) and pick Phosh on the login screen. To remove the session, delete the entry and the launcher. While a session is broken, pick Phosh: the entry only adds a choice.

## Last verified

Not yet verified as written: the example session (sway and Chromium as an app window) is to be run on excalibur before this guide is published. The pieces it comes from (the entry and launcher, sway at scale 2 with touch mapped, PulseAudio, the inhibitor and the power key script, `systemd-cat`, logind brightness, `grim` on the newest socket) ran on excalibur with postmarketOS v26.06 from 2026-11-21 to 2026-11-22.
