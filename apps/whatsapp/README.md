# WhatsApp Web on a Linux phone

WhatsApp has no Linux app, and WhatsApp Web is built for a desktop screen: a 748-px-wide two-pane layout with a rail of buttons on the left. On a phone it's cramped and cut off. This folder turns it into a phone app: one pane at a time, a back button in the header, and a bottom bar like the WhatsApp phone app.

It was built with the tools in [`../dev/`](../dev/): a probe that maps the page's structure without reading its content, and live CSS changes checked on the phone.

## What it does

- **One pane at a time.** The chat list fills the screen; opening a chat slides to the conversation; **←** in the conversation header slides back.
- **A bottom bar** with Chats, Calls, Status, Channels, Communities, Media and your profile, instead of the side rail. Meta AI is hidden.
- **Fits the screen natively.** It runs WhatsApp Web in a plain Chromium app window (`--app=`), which, unlike an installed web app, has no toolbar row and no 500-px minimum width, so it's exactly the phone's width.
- **Fails safe.** It only works from stable anchors (`#side`, `#main`, `data-testid` attributes), never WhatsApp's generated class names. If WhatsApp changes its page and an anchor disappears, the extension switches itself off and you get stock WhatsApp Web, not a broken one.

It only changes layout. It never reads message text, names or media, and never sends anything.

## Install on a Linux phone

Tested on postmarketOS v26.06 with Phosh and Chromium 156 (Redmi Note 9 Pro Max, 2026-11-21). On the phone, from a clone of this repository:

```sh
sh apps/install whatsapp --copy-profile --hide-web-app
```

- `--copy-profile` starts from a copy of your Chromium profile, so an existing WhatsApp Web login carries over (no QR code). Close Chromium first.
- `--hide-web-app` hides the icon of a WhatsApp web app you installed earlier from Chromium.

It creates `~/.local/share/android2linux/apps/whatsapp/` (a Chromium profile of its own and the extension), the launcher `~/.local/bin/a2l-whatsapp`, and a **WhatsApp** entry in the app grid. [`apps/install`](../install) explains each choice; `sh apps/install whatsapp --uninstall` removes it.

The installer also turns off Chromium's own window frame in the app's profile (`browser.custom_chrome_frame = false`), so Phosh shows the page edge to edge.

Any Chromium-based browser can also load the extension unpacked (`chrome://extensions` → Developer mode → Load unpacked, or `--load-extension=<this folder>/extension`; Google-branded Chrome ignores that flag since version 137, Chromium doesn't).

## How it works

[`extension/adapter.js`](extension/adapter.js) finds WhatsApp's layout root (the `.two`/`.three` ancestor of `#side`), the column holding the chat list and the column holding the conversation (`#main`, or the intro panel when no chat is open), and the nearest horizontally scrollable ancestor. It tags them with `data-wam="…"` and re-tags them whenever WhatsApp re-renders. [`extension/adapter.css`](extension/adapter.css) then makes the root two screens wide (page 1: the chat list, page 2: the conversation), and the script scrolls to the right page. The back button sends WhatsApp's own Escape shortcut, which closes the chat.

## Credit

The two-page layout (a root two viewports wide, scrolled between the list and the conversation) and the Escape-key back action come from [Etelis/whatsapp-web-ios](https://github.com/Etelis/whatsapp-web-ios) (MIT). Research into the other projects doing this ([Karere](https://github.com/tobagin/karere), [ZapZap](https://github.com/rafatosta/zapzap), [Whatsie](https://github.com/keshavbhatt/whatsie), [omarchy's WhatsApp Slim](https://github.com/omacom/omarchy-mac)) shaped the "stable anchors only, fail safe" rules. If you want a complete, maintained WhatsApp client for Linux phones instead, Karere is one.

## WhatsApp's terms

WhatsApp's terms of service forbid modifying its services and using unofficial clients. This extension runs the official WhatsApp Web in Chromium and only restyles the page; no bans have been reported for layout-only extensions as of November 2026, but the risk isn't zero. Use it knowing that.

## When WhatsApp changes its page

WhatsApp changes its page from time to time. Signs: the layout goes back to the desktop look (the extension switched itself off), or something sits in the wrong place. Map the page with [`../dev/structure-probe.js`](../dev/structure-probe.js) through Chromium DevTools to see which anchor moved, try the fix live with [`../dev/live-css.mjs`](../dev/live-css.mjs), then fold it into `extension/` and reinstall (`sh apps/install whatsapp`). Keep the rule: ids, roles and `data-testid` only.
