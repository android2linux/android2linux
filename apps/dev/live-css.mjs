// Replaces a live <style> (and optional markup) in a page through Chromium DevTools, so CSS changes
// show at once on the phone without reloading. Run it again with an empty file to remove them.
// Usage: node live-css.mjs <url-prefix> <file.css> [file.html]      ($CDP as in cdp-eval.mjs)
import { readFileSync } from 'node:fs';
const [prefix, cssFile, htmlFile] = process.argv.slice(2);
if (!prefix || !cssFile) { console.error('usage: node live-css.mjs <url-prefix> <file.css> [file.html]'); process.exit(2); }
const css = readFileSync(cssFile, 'utf8');
const html = htmlFile ? readFileSync(htmlFile, 'utf8') : '';
const base = process.env.CDP || 'http://127.0.0.1:9223';
const target = (await (await fetch(`${base}/json`)).json()).find(t => t.type === 'page' && t.url.startsWith(prefix));
if (!target) { console.error(`no page starting with ${prefix}`); process.exit(1); }
const ws = new WebSocket(target.webSocketDebuggerUrl);
await new Promise(r => ws.onopen = r);
const expr = `(() => {
  let s = document.getElementById('live-css-style');
  if (!s) { s = document.createElement('style'); s.id = 'live-css-style'; document.head.appendChild(s); }
  s.textContent = ${JSON.stringify(css)};
  let d = document.getElementById('live-css-html');
  if (!d) { d = document.createElement('div'); d.id = 'live-css-html'; document.body.appendChild(d); }
  d.innerHTML = ${JSON.stringify(html)};
  return 'applied ' + s.textContent.length + ' bytes of CSS';
})()`;
ws.onmessage = m => { const d = JSON.parse(m.data); if (d.id === 1) { console.log(d.result?.result?.value ?? JSON.stringify(d)); process.exit(0); } };
ws.send(JSON.stringify({ id: 1, method: 'Runtime.evaluate', params: { expression: expr, returnByValue: true } }));
