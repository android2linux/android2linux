// net-capture.mjs - list the domains a page requests through the DevTools protocol.
//
// What it does:
//   Connects to a Chromium/WebEngine debugging port (open a tunnel first with
//   devtools-tunnel), reloads the page, scrolls it, and prints every domain it
//   requested, with successful and failed request counts, the reached IPs and
//   the errors. A domain blocked by a hosts file shows ERR_CONNECTION_REFUSED.
//
// Arguments:
//   [port]        local debugging port (default 9222)
//   -h, --help    show this help
//
// Changes: read-only; it reloads and scrolls the page in the browser.
//
// Example:
//   node net-capture.mjs 9223
const args = process.argv.slice(2);
if (args.includes('-h') || args.includes('--help')) {
  const text = (await import('node:fs')).readFileSync(new URL(import.meta.url), 'utf8');
  const header = text.split('\n').filter(l => l.startsWith('//')).map(l => l.replace(/^\/\/ ?/, ''));
  console.log(header.join('\n'));
  process.exit(0);
}
const port = args[0] || '9222';

const targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json();
const page = targets.find(t => t.type === 'page');
if (!page) {
  console.error('net-capture: no page target on the debugging port');
  process.exit(1);
}

const ws = new WebSocket(page.webSocketDebuggerUrl);
ws.onerror = e => console.log('ws error', e.message);
let id = 0;
const send = (method, params = {}) => ws.send(JSON.stringify({ id: ++id, method, params }));
const reqs = new Map();
const hosts = new Map();
const host = u => { try { return new URL(u).hostname; } catch { return '?'; } };
const entry = h => hosts.get(h) || hosts.set(h, { ok: 0, fail: 0, ips: new Set(), errs: new Set() }).get(h);

ws.onmessage = (m) => {
  const d = JSON.parse(m.data);
  if (d.method === 'Network.requestWillBeSent') reqs.set(d.params.requestId, d.params.request.url);
  if (d.method === 'Network.responseReceived') {
    const e = entry(host(d.params.response.url));
    e.ok++;
    if (d.params.response.remoteIPAddress) e.ips.add(d.params.response.remoteIPAddress);
  }
  if (d.method === 'Network.loadingFailed') {
    const e = entry(host(reqs.get(d.params.requestId) || ''));
    e.fail++;
    e.errs.add(d.params.errorText);
  }
};

ws.onopen = () => {
  send('Network.enable');
  send('Page.enable');
  send('Network.setCacheDisabled', { cacheDisabled: true });
  setTimeout(() => send('Runtime.evaluate', { expression: 'location.reload()' }), 500);
  for (const s of [8000, 12000, 16000]) {
    setTimeout(() => send('Runtime.evaluate', { expression: 'window.scrollBy(0, 3000)' }), s);
  }
};

await new Promise(r => setTimeout(r, 25000));
const rows = [...hosts].sort((a, b) => (b[1].ok + b[1].fail) - (a[1].ok + a[1].fail));
for (const [h, e] of rows) {
  console.log(`${String(e.ok).padStart(4)} ok ${String(e.fail).padStart(3)} fail  ${h}  ${[...e.ips].join(',')} ${[...e.errs].join(',')}`);
}
process.exit(0);
