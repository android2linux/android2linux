# Apps for your Linux phone

Many services have no Linux app, only a web app designed for a desktop screen. Each folder here turns one of them into a phone app: the site in a Chromium app window that fits the screen, with a small extension that reworks the layout for a phone where it's needed, and an icon in your app grid.

## Catalogue

<!-- CATALOGUE:START -->
| App | What it is | Status | Last tested on |
|---|---|---|---|
| [WhatsApp](whatsapp/) | WhatsApp Web with a phone layout: one pane at a time, a back button, a bottom bar. | works | Xiaomi Redmi Note 9 Pro Max (excalibur), postmarketOS v26.06, Phosh (2026-11-21) |
<!-- CATALOGUE:END -->

## Install an app

On the phone (postmarketOS with Phosh, or similar, with Chromium installed), from a clone of this repository:

```sh
sh apps/install whatsapp --copy-profile --hide-web-app
```

`--copy-profile` copies your Chromium profile so you stay logged in to the site (close Chromium first); without it, you log in once in the new app. `--hide-web-app` hides an older web-app icon for the same site. `sh apps/install whatsapp --uninstall` removes it. The installer's header explains what it creates and why.

## How an app is made

```
apps/<id>/
  app.json        name, URL, description, categories, status, where it was tested
  extension/      a Chromium extension (Manifest V3) that adapts the layout, if the site needs one
  icon.png        optional, 512×512
  README.md       what it does, how it works, its limits and risks, credit
```

`app.json`:

```json
{
  "id": "whatsapp",
  "name": "WhatsApp",
  "description": "One line on what it is.",
  "url": "https://web.whatsapp.com/",
  "extension": "extension",
  "categories": ["Network", "InstantMessaging"],
  "status": "works",
  "tested": [{ "date": "2026-11-21", "device": "…", "os": "…", "browser": "Chromium 156" }],
  "notes": "Anything a user should know first."
}
```

After adding or changing an app, regenerate the table above with `python3 apps/catalogue.py`.

## Build a new one

The method is in [dev/](dev/): run the site on the phone with DevTools, map its layout with the structure probe (it never reads content), and change CSS live while you look at the phone. Rules for an adapter:

- Select by ids, roles and `data-testid` attributes, never by generated class names.
- If an anchor is missing, switch the whole adapter off: the stock site is better than a broken one.
- Only change layout. Never read, store or send the user's content.
- Check the service's terms, and say plainly in the app's README what they are.

With the android2linux skill installed, ask your assistant to "build a phone app for <site>" and it will follow this method with you.
