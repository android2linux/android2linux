// Runs one JavaScript expression in a page through Chromium DevTools and prints the result as JSON.
// Usage: node cdp-eval.mjs <url-prefix> '<expression>'   (or '@file.js' to read the expression from a file)
// Needs DevTools reachable at $CDP (default http://127.0.0.1:9223), e.g. an SSH tunnel to the phone:
//   ssh -f -N -L 127.0.0.1:9223:127.0.0.1:9222 <phone>   with Chromium started with --remote-debugging-port=9222
import { readFileSync } from 'node:fs';
const [prefix, arg] = process.argv.slice(2);
if (!prefix || !arg) { console.error("usage: node cdp-eval.mjs <url-prefix> '<expression>' | @file.js"); process.exit(2); }
const expr = arg.startsWith('@') ? readFileSync(arg.slice(1), 'utf8') : arg;
const base = process.env.CDP || 'http://127.0.0.1:9223';
const target = (await (await fetch(`${base}/json`)).json()).find(t => t.type === 'page' && t.url.startsWith(prefix));
if (!target) { console.error(`no page starting with ${prefix}`); process.exit(1); }
const ws = new WebSocket(target.webSocketDebuggerUrl);
await new Promise(r => ws.onopen = r);
ws.onmessage = m => {
  const d = JSON.parse(m.data);
  if (d.id !== 1) return;
  console.log(JSON.stringify(d.result?.result?.value ?? d.result?.exceptionDetails ?? d.error, null, 1));
  process.exit(0);
};
ws.send(JSON.stringify({ id: 1, method: 'Runtime.evaluate', params: { expression: expr, returnByValue: true, awaitPromise: true } }));
setTimeout(() => { console.error('timeout'); process.exit(1); }, 15000);
