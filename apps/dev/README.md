# Tools for adapting web apps to a phone

How the WhatsApp adapter was built, packaged for the next app. You work from your PC; the app runs in Chromium on the phone with DevTools open to you through an SSH tunnel.

1. Start the app on the phone with `--remote-debugging-port=9222` (run it as a user service, `systemd-run --user …`, so it outlives your SSH session), and open the tunnel from the PC:
   `ssh -f -N -L 127.0.0.1:9223:127.0.0.1:9222 <phone>` (postmarketOS needs `AllowTcpForwarding local` in its SSH config).
2. Map the layout without reading anyone's content: `node cdp-eval.mjs https://web.example.com @structure-probe.js`.
3. Try CSS live while the person holding the phone says what looks wrong: `node live-css.mjs https://web.example.com try.css`. For measurements on screen, inject a ruler (`try.css` + a small HTML file); a full-height striped ruler at the right edge found a 140-px crop that screenshots and DOM sizes had hidden.
4. Fold what works into the extension and reload.

Privacy: the probe reports structure only. Don't screenshot or record personal apps unless their owner asks for it at that moment, and delete what you captured as soon as you've looked.
