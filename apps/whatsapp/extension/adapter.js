// WhatsApp Web on a phone: shows one pane at a time (chat list, or the open conversation) with a
// back button. It only changes layout: it never reads message text, names or media, and never
// sends anything. The two-page layout idea comes from Etelis/whatsapp-web-ios (MIT).
//
// How it works: WhatsApp's layout root (.two/.three, the ancestor of #side) is made two screens
// wide; the column holding #side is page 1, the column holding #main or the intro panel is page 2,
// and the nearest horizontally scrollable ancestor is scrolled to the right page. Elements are
// found from stable anchors (#side, #main, data-testid), tagged with data-wam="...", and re-tagged
// whenever WhatsApp re-renders. If the anchors can't be found, nothing is applied and WhatsApp's
// own layout stays as it is.
(() => {
  const html = document.documentElement;

  // The .two/.three child that contains `el`: one of the layout root's columns.
  function columnOf(root, el) {
    while (el && el.parentElement !== root) el = el.parentElement;
    return el;
  }

  // The nearest ancestor of `el` that scrolls horizontally (overflow-x auto or scroll). Once found
  // it is tagged, and adapter.css then sets its overflow-x to hidden, so the tag is checked first:
  // otherwise the next check wouldn't find it and the adapter would switch itself off.
  function scrollerOf(el) {
    for (let p = el.parentElement; p && p !== document.body; p = p.parentElement) {
      if (p.getAttribute('data-wam') === 'scroller') return p;
      const o = getComputedStyle(p).overflowX;
      if (o === 'auto' || o === 'scroll') return p;
    }
    return null;
  }

  function tag(el, name) {
    if (el && el.getAttribute('data-wam') !== name) el.setAttribute('data-wam', name);
  }

  let scroller = null;

  // Finds and tags the parts; turns the adapter on only when all of them exist.
  function update() {
    const side = document.getElementById('side');
    const root = side && side.closest('.two, .three');
    const main = document.getElementById('main');
    const intro = document.querySelector('[data-testid="intro-panel"]');
    const list = root && columnOf(root, side);
    const conv = root && columnOf(root, main || intro);
    scroller = root && scrollerOf(root);
    if (!(root && list && conv && scroller && list !== conv)) {
      html.removeAttribute('data-wam-on');
      return;
    }
    tag(root, 'root');
    tag(list, 'list');
    tag(conv, 'conv');
    tag(scroller, 'scroller');
    html.setAttribute('data-wam-on', '');
    showPage(main ? 2 : 1);
  }

  function showPage(page) {
    if (html.getAttribute('data-wam-page') !== String(page)) html.setAttribute('data-wam-page', String(page));
    const left = page === 2 ? scroller.clientWidth : 0;
    if (Math.abs(scroller.scrollLeft - left) > 1) scroller.scrollTo({ left, behavior: 'smooth' });
  }

  // Back: close the chat the way WhatsApp's own Escape key does; #main then disappears and
  // update() slides back to the list.
  const back = document.createElement('button');
  back.id = 'wam-back';
  back.type = 'button';
  back.textContent = '←';
  back.setAttribute('aria-label', 'Back to chats');
  back.addEventListener('click', () => {
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', code: 'Escape', keyCode: 27, bubbles: true }));
    setTimeout(update, 50);
  });
  document.body.appendChild(back);

  // WhatsApp re-renders often: re-check after DOM changes, at most once per animation frame.
  let queued = false;
  new MutationObserver(() => {
    if (queued) return;
    queued = true;
    requestAnimationFrame(() => { queued = false; update(); });
  }).observe(document.body, { childList: true, subtree: true });
  addEventListener('resize', update);
  update();
})();
