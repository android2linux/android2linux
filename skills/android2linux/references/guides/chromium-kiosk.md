# Chromium in a kiosk, and in Phosh

This guide covers running Chromium as the whole interface of the phone — `cage`, a single-window Wayland compositor, launching Chromium full-screen on a local web page — and the smaller job of running Chromium as a normal app inside Phosh. It covers the greetd switch between the two, why the display scale must be set in the compositor as an integer, why the page must open as an app window, how to verify what the browser actually renders through DevTools over an SSH tunnel, how to take real screenshots with `grim`, the missing on-screen keyboard in `cage`, and the safe-area insets the notch and rounded corners impose. It builds on [`working-from-your-pc.md`](working-from-your-pc.md).

The setup used Chromium **156** and `cage` **0.3** on postmarketOS v26.06, with Phosh 0.55 / phoc 0.55.1 for the normal-app case.

## Two modes

- **Chromium inside Phosh** — a normal app window on the phone's desktop. Easiest; needs two fixes to fit the screen.
- **The kiosk** — no desktop, `cage` runs Chromium full-screen on one page. This is the base for an OS whose UI is a web app.

## The kiosk: greetd switch

The kiosk replaces the Phosh session by pointing `greetd` at a different config. The pieces:

- A launcher at `/usr/local/bin/lightos-kiosk` (a shell script that starts `cage` running Chromium).
- A greetd config at `/etc/greetd/lightos-kiosk.toml`:
  ```toml
  [terminal]
  vt = 7

  [default_session]
  command = "/usr/local/bin/lightos-kiosk"
  user = "user"
  ```
- A drop-in at `/etc/systemd/system/greetd.service.d/zz-lightos-kiosk.conf` that replaces greetd's start command:
  ```ini
  [Service]
  ExecStart=
  ExecStart=greetd -c /etc/greetd/lightos-kiosk.toml
  ```

Install the three, then `systemctl daemon-reload` and `systemctl restart greetd`. **Restarting greetd ends the Phosh session** and starts the kiosk. To go back, delete the drop-in and restart greetd again. On the reference device this was wrapped in `kiosk-on` / `kiosk-off` scripts that prompt for the phone password (or read it from `$PHONE_PIN`), because the user runs `sudo`, not the assistant.

The page lives at `~/lightos-trial/index.html` on the phone; `LIGHTOS_URL` in the launcher's environment overrides it. Chromium's kiosk log goes to `~/lightos-kiosk.log`.

Packages added on the phone: `cage`, `chromium`, `wlr-randr`, `grim`.

## Why the scale is set in the compositor, as an integer

Set the display scale with **`wlr-randr` inside `cage`**, not with Chromium:

```sh
wlr-randr --output DSI-1 --scale 3
```

- `--force-device-scale-factor` on Wayland renders at **2.75×** the logical width instead of fitting, so it does not give you the screen.
- `cage` scales by **integers** for Chromium, so a fractional value like 2.75 leaves a mismatch. **3** gives 360 × 800 CSS px — Android's usual size, and sharp on this 1080 × 2400 panel.

The window size is then the panel divided by the scale (`1080/3 × 2400/3` = `360,800`).

## Why the page is opened as an app window

A normal browser window **cannot be narrower than 500 CSS px**, even full-screen, because of its hidden toolbar layout. The screen is only 360 wide, so a normal window overflows. An **app window** can be narrower. Launch Chromium with `--app=<url>` together with `--kiosk`.

The launcher's core:

```sh
SIZE=$(awk -v s="$SCALE" 'BEGIN { printf "%d,%d", 1080 / s, 2400 / s }')
exec cage -s -- sh -c "
  wlr-randr --output DSI-1 --scale $SCALE
  exec chromium --kiosk --no-first-run --password-store=basic \
    --ozone-platform=wayland --touch-events=enabled --enable-features=OverlayScrollbar \
    --window-size=$SIZE \
    --remote-debugging-port=9222 --app='$URL'
"
```

`--no-first-run` avoids the first-run dialog (which is wider than the screen). `--remote-debugging-port=9222` is what makes the verifying step below possible.

## Measure what the browser really renders

DevTools shows the truth about viewport, pixel ratio and GPU. Over an SSH tunnel:

```sh
ssh -f -N -L 127.0.0.1:9223:127.0.0.1:9222 pmos
```

Then open `http://127.0.0.1:9223/json` (or `chrome://inspect` in Chrome on the PC). This needs **`AllowTcpForwarding local`** on the phone; postmarketOS ships `AllowTcpForwarding no`, so add it in `/etc/ssh/sshd_config.d/60-local-forwarding.conf`.

The measured result on the reference device: viewport **360 × 800**, `devicePixelRatio` **3**, WebGL renderer `ANGLE (…, FD618, OpenGL ES 3.2)` — Mesa freedreno on the Adreno 618, GPU-accelerated — and **58–60 fps** with WebGL and CSS animations running. There is **no hardware video decode** (`vaInitialize failed`, expected); the GPU does the drawing.

`cage` sometimes logs `Atomic commit failed: Resource busy`, from the display driver being busy on a page flip. Expect occasional jank, not a fault.

## Real screenshots with `grim`

DevTools screenshots show only the page, not the actual screen. For the real screen:

```sh
ssh pmos 'XDG_RUNTIME_DIR=/run/user/10000 WAYLAND_DISPLAY=wayland-0 grim /tmp/screen.png'
scp pmos:/tmp/screen.png .
```

`grim` is a Wayland screenshot tool; it needs the session's runtime dir and display, which is why those are set explicitly over SSH.

## No on-screen keyboard in `cage`

`cage` has **no on-screen keyboard**. If your web UI needs text input, build the keyboard **into the web page**. A trial page that expects a system keyboard will simply not get one. (Phosh, by contrast, has one, and it works in Chromium there.)

## Safe-area insets: the notch and rounded corners

In the kiosk there is **no status bar**, so the page runs under the rounded corners and the camera hole. The web page must keep its own insets:

| Feature | Physical | CSS (at scale 3) |
|---|---|---|
| Top camera/notch region | 101 px | ≈ 34 px |
| Corner radius | ~29 px | ≈ 10 px |
| Camera hole, x range | 491–581 px | ≈ 164–194 px |

Chromium on this setup **does not fill `env(safe-area-inset-*)`**, so you cannot rely on the CSS environment variables — keep your own top inset and corner padding in the UI.

## Chromium inside Phosh

Phosh at scale 3 gives apps a screen 360 CSS px wide, and Chromium refuses to make a normal browser window narrower than 500. Three fixes, from what you need first to what makes web apps feel native:

1. **Create `~/.config/chromium/First Run`.** Without it, the first-run dialog opens wider than the screen with its button cut off. (The kiosk avoided this with `--no-first-run`.)
2. **Let phoc shrink windows that don't fit, globally:**
   ```sh
   gsettings set sm.puri.phoc scale-to-fit true
   ```
   Run `gsettings` with the session bus: `DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/10000/bus`. A per-app switch exists (`gsettings set sm.puri.phoc.application:/sm/puri/phoc/application/<app-id>/ scale-to-fit true`), but web-app windows get their own app ids (not `chromium`), and setting it for the ids from their `.desktop` file (`crx_<id>`, `chrome-<id>-Default`) didn't take effect: the window was **cropped** at 360 px, not shrunk. The global switch fixed it at once. A full-height striped ruler injected at the page's right edge is what proved the crop; DOM measurements alone looked fine.
3. **Open web apps as plain app windows, not installed web apps.** An installed web app (`--app-id=<id>`) has a toolbar row (title, menu) and the same 500-px minimum, so Phosh has to shrink it. A plain app window (`--app=https://site/`) has **no toolbar and no minimum width**: it opens exactly 360 px wide, sharp, at 100 % zoom. Also turn off Chromium's own window frame (`"browser": {"custom_chrome_frame": false}` in the profile's `Preferences`, with Chromium closed), so Phosh shows the page edge to edge. Phosh offers the decoration protocol (`zxdg_decoration_manager_v1`) and draws no frame itself.

Full-screen (`Browser.setWindowBounds` → `fullscreen`) also removes the toolbar, but it hides Phosh's status bar and its swipe gestures, and with the 500-px minimum the window is shrunk to fill only the top three quarters of the screen. Not worth it.

To run a web app with an extension every time, give it **its own profile** (`--user-data-dir=…`): Chromium runs one process per profile, and a second launch hands over to the running one, ignoring its command-line options such as `--load-extension`. Copying the existing profile (with Chromium closed) keeps the site's login. Alpine's Chromium (unbranded) honours `--load-extension`; Google Chrome ignores it since version 137. Content scripts run inside app windows. See [apps/whatsapp](../../../../apps/whatsapp/) for a complete example, and [`apps/install`](../../../../apps/install) for the installer that sets this up.

Phosh's on-screen keyboard works in Chromium. Firefox ESR 153 (with `mobile-config-firefox`) has no PWA install on Linux; GNOME Web (`epiphany`) does.

## A stuck Chromium

If Chromium is killed and won't restart, it leaves `~/.config/chromium/Singleton*` lock files. Remove them after killing it.

## Last verified

Kiosk, scaling, app window, DevTools measurements, `grim`, Phosh scale-to-fit (global), plain app windows and extensions in a separate profile: 2026-11-21 on postmarketOS v26.06. Checked 2026-11-21.
