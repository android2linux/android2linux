# Contributing

Phones, apps, guide fixes and scripts are all welcome, whether something worked or not: a phone that can't run Linux yet is worth a folder too.

## Contents

- [How a change gets in](#how-a-change-gets-in)
- [What to contribute](#what-to-contribute)
- [Testing](#testing)
- [Privacy](#privacy)
- [Writing](#writing)
- [Using an AI assistant](#using-an-ai-assistant)
- [License](#license)

## How a change gets in

1. **Open an issue** with the form that fits: [a phone](https://github.com/android2linux/android2linux/issues/new?template=phone.yml), [an app](https://github.com/android2linux/android2linux/issues/new?template=app.yml), [a guide fix](https://github.com/android2linux/android2linux/issues/new?template=guide.yml) or [a script bug](https://github.com/android2linux/android2linux/issues/new?template=script.yml). Say what you want to change and why. Someone with the same phone may already be on it, and the issue is where that shows.
2. **Fork, branch and make the change.** Commit messages start with the area: `phones: xiaomi-curtana, postmarketOS v26.06`, `Safe flashing: …`, `apps/whatsapp: …`.
3. **Open a pull request** with `Closes #<issue>` on its first line, and fill in its checklist.

A small fix (a typo, a broken link, a wrong command) can go straight to a pull request.

## What to contribute

- **A phone.** A folder `phones/<vendor>-<codename>/` with a `phone.json` and a `README.md`, in the shape [`phones/README.md`](phones/README.md) describes. Name it by codename, not by marketing name. Then run `python3 phones/catalogue.py`.
- **An app.** A folder `apps/<id>/` with an `app.json`, and an extension if the site needs one; [`apps/README.md`](apps/README.md) has the format and the rules for an adapter (layout only, stable selectors, never read the user's content). Then run `python3 apps/catalogue.py`.
- **A guide fix.** The guides in [`skills/android2linux/references/guides/`](skills/android2linux/references/guides/) state the method that works, for any phone. What failed along the way belongs in a phone's folder, not in a guide. Update the guide's "Last verified" section.
- **A script.** In [`skills/android2linux/scripts/`](skills/android2linux/scripts/README.md): a header that says what it does, its arguments, what it changes and an example; `-h`/`--help`; the device or host as an argument, never written into the script; read-only wherever it can be. Add it to the scripts table.

## Testing

Test on a real phone, and say which: the codename, the system and its version, and the date. "It booted" is not "it works": say what you tested, what works, what doesn't, and what you didn't test.

## Privacy

Never commit:

- serial numbers, IMEIs, phone numbers, unlock tokens or passwords;
- IP addresses, Wi-Fi names, user names or home paths (use placeholders such as `<serial>` and `pmos`);
- screenshots or recordings that show a messenger, mail, a bank, notifications, or an overview with such an app open.

Check every image before adding it: the status bar, the notifications and the app thumbnails.

## Writing

- Short, plain sentences, without "we": say what to do and why.
- Commands short enough to copy; a long one goes into a script.
- Dates as `YYYY-MM-DD`.
- Link a guide rather than repeating it.

## Using an AI assistant

Contributions made with an AI assistant are welcome: helping people do this with one is what this repository is for. What counts is the same as for any contribution: you ran it on a real phone, you read what you submit, and you can answer questions about it.

The projects this builds on have their own rules. postmarketOS forbids contributions made with generative AI, so anything you post there is yours to write. [Communities and AI](skills/android2linux/references/guides/communities-and-ai.md) lists each project's policy.

## License

Contributions are under the repository's [MIT license](LICENSE).
