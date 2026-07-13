// Uellow Importer — content script injected on aliexpress.com.
// Adds Import / Import & Publish controls on product pages, search results,
// category and store pages. Reads the product id straight from the page links.
(function () {
  'use strict';

  // ---- id extraction ------------------------------------------------------
  function idFromUrl(u) {
    if (!u) return null;
    const m = String(u).match(/\/(?:item|i)\/(\d{8,})\.html/)
      || String(u).match(/[?&]productId=(\d{8,})/)
      || String(u).match(/\/(\d{8,})\.html/);
    return m ? m[1] : null;
  }

  function currentProductId() {
    return idFromUrl(location.href);
  }

  function collectCardLinks() {
    // every product tile on a listing/search/store page is an <a> to /item/<id>.html
    const map = new Map(); // id -> anchor element (first seen)
    document.querySelectorAll('a[href*="/item/"], a[href*="/i/"]').forEach((a) => {
      const id = idFromUrl(a.href);
      if (id && !map.has(id)) map.set(id, a);
    });
    return map;
  }

  // ---- server calls (via background worker) -------------------------------
  function send(type, payload) {
    return new Promise((resolve) => {
      chrome.runtime.sendMessage(Object.assign({ type }, payload), (r) =>
        resolve(r || { ok: false, error: 'no response' }));
    });
  }

  // ---- UI helpers ---------------------------------------------------------
  function el(tag, cls, txt) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (txt != null) e.textContent = txt;
    return e;
  }

  function toast(text, kind) {
    let t = el('div', 'uw-toast ' + (kind || ''));
    t.textContent = text;
    document.body.appendChild(t);
    requestAnimationFrame(() => t.classList.add('show'));
    setTimeout(() => { t.classList.remove('show'); setTimeout(() => t.remove(), 300); }, 3200);
  }

  async function doImport(ids, publish, btn) {
    if (!ids.length) { toast('No product found here', 'err'); return; }
    const label = btn ? btn.textContent : '';
    if (btn) { btn.disabled = true; btn.textContent = '…'; }
    const r = await send('import', { ids, publish });
    if (btn) { btn.disabled = false; btn.textContent = label; }
    if (!r || !r.ok) { toast('Import failed: ' + ((r && r.error) || '?'), 'err'); return; }
    if (!r.imported) {
      // nothing imported — tell the user WHY (blocked / not found)
      const sk = r.skipped || [];
      const blocked = sk.filter((s) => s.reason === 'blocked').length;
      const notFound = sk.filter((s) => s.reason === 'not_found' || s.reason === 'fetch_failed').length;
      let msg = 'Imported 0';
      if (blocked) msg = '⛔ Blocked — prohibited product (' + blocked + ')';
      else if (notFound) msg = '⚠️ Could not fetch product (' + notFound + ')';
      toast(msg, 'err');
      refreshBadges();
      return;
    }
    let msg = '✓ Imported ' + r.imported + (publish ? (' · published ' + r.published) : '');
    const sk = (r.skipped || []).length;
    if (sk) msg += ' · ' + sk + ' skipped';
    toast(msg, 'ok');
    refreshBadges();
  }

  // ---- per-card buttons ---------------------------------------------------
  function tagCard(id, anchor) {
    // find a stable card container to anchor the button onto
    let card = anchor;
    for (let i = 0; i < 4 && card.parentElement; i++) {
      if (card.offsetWidth >= 120 && card.offsetHeight >= 120) break;
      card = card.parentElement;
    }
    if (card.querySelector(':scope > .uw-card-btn')) return;
    if (getComputedStyle(card).position === 'static') card.style.position = 'relative';

    const wrap = el('div', 'uw-card-btn');
    const bImp = el('button', 'uw-mini', '＋ Import');
    bImp.title = 'Import to Uellow World';
    bImp.addEventListener('click', (ev) => {
      ev.preventDefault(); ev.stopPropagation();
      doImport([id], false, bImp);
    });
    const bPub = el('button', 'uw-mini uw-pub', '⇪ Publish');
    bPub.title = 'Import & Publish (show in app)';
    bPub.addEventListener('click', (ev) => {
      ev.preventDefault(); ev.stopPropagation();
      doImport([id], true, bPub);
    });
    wrap.appendChild(bImp);
    wrap.appendChild(bPub);
    wrap.dataset.uwId = id;
    card.appendChild(wrap);
  }

  function decorateCards() {
    const map = collectCardLinks();
    map.forEach((anchor, id) => tagCard(id, anchor));
    return map;
  }

  // mark already-imported cards with a ✓
  async function refreshBadges() {
    const ids = Array.from(document.querySelectorAll('.uw-card-btn'))
      .map((w) => w.dataset.uwId).filter(Boolean);
    const single = currentProductId();
    if (single && !ids.includes(single)) ids.push(single);
    if (!ids.length) return;
    const r = await send('check', { ids: ids.slice(0, 200) });
    if (!r || !r.ok) return;
    Object.entries(r.status || {}).forEach(([id, st]) => {
      document.querySelectorAll('.uw-card-btn[data-uw-id="' + id + '"]').forEach((w) => {
        w.classList.toggle('uw-done', !!st.imported);
        w.classList.toggle('uw-live', !!st.published);
      });
    });
    if (single && panelState) panelState(r.status[single]);
  }

  // ---- floating panel -----------------------------------------------------
  let panelState = null;
  function buildPanel() {
    if (document.getElementById('uw-panel')) return;
    const p = el('div'); p.id = 'uw-panel';
    const isProduct = !!currentProductId();

    const title = el('div', 'uw-title');
    title.innerHTML = '<span class="uw-logo">U</span> Uellow Importer';
    p.appendChild(title);

    const info = el('div', 'uw-info');
    p.appendChild(info);

    const row = el('div', 'uw-row');
    if (isProduct) {
      const bImp = el('button', 'uw-btn', 'Import');
      const bPub = el('button', 'uw-btn uw-primary', 'Import & Publish');
      bImp.addEventListener('click', () => doImport([currentProductId()], false, bImp));
      bPub.addEventListener('click', () => doImport([currentProductId()], true, bPub));
      row.appendChild(bImp); row.appendChild(bPub);
      panelState = (st) => {
        info.textContent = st && st.imported
          ? (st.published ? '✓ Imported · Live in app' : '✓ Imported (not published)')
          : 'This product · not imported yet';
        info.className = 'uw-info' + (st && st.imported ? ' uw-ok' : '');
      };
    } else {
      const bAll = el('button', 'uw-btn', 'Import page');
      const bAllPub = el('button', 'uw-btn uw-primary', 'Import & Publish page');
      bAll.addEventListener('click', () => bulk(false, bAll));
      bAllPub.addEventListener('click', () => bulk(true, bAllPub));
      row.appendChild(bAll); row.appendChild(bAllPub);
      panelState = null;
    }
    p.appendChild(row);

    const cfgLink = el('div', 'uw-cfg', '⚙ open the extension to set server + key');
    p.appendChild(cfgLink);

    document.body.appendChild(p);

    function updateInfo() {
      if (isProduct) { refreshBadges(); return; }
      const n = collectCardLinks().size;
      info.textContent = n + ' product(s) detected on this page';
    }
    updateInfo();
    p._update = updateInfo;
  }

  async function bulk(publish, btn) {
    const ids = Array.from(collectCardLinks().keys());
    if (!ids.length) { toast('No products detected on this page', 'err'); return; }
    if (!confirm('Import ' + ids.length + ' product(s) from this page' +
      (publish ? ' and publish them?' : '?'))) return;
    doImport(ids, publish, btn);
  }

  // ---- boot + observe -----------------------------------------------------
  async function boot() {
    const cfg = await send('cfg', {});
    buildPanel();
    decorateCards();
    refreshBadges();

    let t = null;
    const obs = new MutationObserver(() => {
      clearTimeout(t);
      t = setTimeout(() => {
        decorateCards();
        const p = document.getElementById('uw-panel');
        if (p && p._update) p._update();
      }, 600);
    });
    obs.observe(document.body, { childList: true, subtree: true });

    // AliExpress is an SPA — re-check on URL changes
    let lastUrl = location.href;
    setInterval(() => {
      if (location.href !== lastUrl) {
        lastUrl = location.href;
        const old = document.getElementById('uw-panel');
        if (old) old.remove();
        panelState = null;
        setTimeout(() => { buildPanel(); decorateCards(); refreshBadges(); }, 800);
      }
    }, 1000);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
