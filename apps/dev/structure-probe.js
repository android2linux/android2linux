// Structure-only map of a page, for adapting a desktop web app to a phone without seeing its content.
// Reports ids, roles, data-testid values, box sizes, min-widths and overflow; never reads text,
// names, images or attribute values that could hold personal data.
// Usage: node cdp-eval.mjs <url-prefix> @structure-probe.js        Set ROOT below to start elsewhere.
(() => {
  const ROOT = document.getElementById('app') || document.body;
  const MAX_DEPTH = 8, MAX_LINES = 120;
  const lines = [];
  const walk = (el, depth) => {
    if (depth > MAX_DEPTH || lines.length >= MAX_LINES) return;
    const r = el.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) return;
    const cs = getComputedStyle(el);
    const name = el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') + (el.dataset.testid ? `[${el.dataset.testid}]` : '') +
      (el.getAttribute('role') ? `{${el.getAttribute('role')}}` : '');
    const flags = [cs.minWidth !== 'auto' && cs.minWidth !== '0px' ? 'minW=' + cs.minWidth : '',
      el.scrollWidth > el.clientWidth + 1 ? `overflowX ${el.scrollWidth}>${el.clientWidth}` : '',
      cs.position !== 'static' ? cs.position : ''].filter(Boolean).join(' ');
    lines.push(`${'  '.repeat(depth)}${name} [${Math.round(r.left)},${Math.round(r.top)} ${Math.round(r.width)}x${Math.round(r.height)}] ${flags}`);
    for (const child of el.children) walk(child, depth + 1);
  };
  walk(ROOT, 0);
  const testids = {};
  document.querySelectorAll('[data-testid]').forEach(e => { testids[e.dataset.testid] = (testids[e.dataset.testid] || 0) + 1; });
  return { viewport: [innerWidth, innerHeight], pageWidth: document.documentElement.scrollWidth, tree: lines, testids };
})()
