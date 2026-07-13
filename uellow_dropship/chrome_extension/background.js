// Uellow Importer — background service worker.
// All network calls go through here: the service worker holds host_permissions
// for the Uellow server, so it bypasses the aliexpress.com page's CORS.

async function getCfg() {
  const d = await chrome.storage.sync.get(['baseUrl', 'key', 'publish']);
  return {
    baseUrl: (d.baseUrl || '').trim().replace(/\/+$/, ''),
    key: (d.key || '').trim(),
    publish: !!d.publish,
  };
}

async function call(path, body) {
  const c = await getCfg();
  if (!c.baseUrl || !c.key) {
    return { ok: false, error: 'Not configured — open the extension and set the server URL + key.' };
  }
  try {
    const res = await fetch(c.baseUrl + path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(Object.assign({ key: c.key }, body)),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) return { ok: false, error: data.error || ('HTTP ' + res.status) };
    return data;
  } catch (e) {
    return { ok: false, error: String(e && e.message || e) };
  }
}

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  (async () => {
    if (msg.type === 'cfg') {
      sendResponse(await getCfg());
    } else if (msg.type === 'check') {
      sendResponse(await call('/dropship/ext/check', { ids: msg.ids }));
    } else if (msg.type === 'import') {
      const c = await getCfg();
      const publish = (msg.publish !== undefined) ? msg.publish : c.publish;
      const r = await call('/dropship/ext/import', { ids: msg.ids, publish });
      if (r.ok) {
        try {
          chrome.notifications.create({
            type: 'basic',
            iconUrl: 'icons/icon128.png',
            title: 'Uellow Importer',
            message: `Imported ${r.imported} product(s)` +
              (r.published ? `, published ${r.published}` : ''),
          });
        } catch (e) { /* notifications optional */ }
      }
      sendResponse(r);
    }
  })();
  return true; // keep the message channel open for the async sendResponse
});
