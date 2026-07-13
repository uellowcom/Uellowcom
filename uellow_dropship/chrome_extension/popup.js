// Uellow Importer — popup settings.
const $ = (id) => document.getElementById(id);

chrome.storage.sync.get(['baseUrl', 'key', 'publish'], (d) => {
  $('baseUrl').value = d.baseUrl || '';
  $('key').value = d.key || '';
  $('publish').checked = !!d.publish;
});

function msg(text, kind) {
  const m = $('msg');
  m.textContent = text;
  m.className = 'msg ' + (kind || '');
}

$('save').addEventListener('click', () => {
  const baseUrl = $('baseUrl').value.trim().replace(/\/+$/, '');
  const key = $('key').value.trim();
  chrome.storage.sync.set({ baseUrl, key, publish: $('publish').checked }, () => {
    msg('Saved ✓', 'ok');
  });
});

$('test').addEventListener('click', () => {
  const baseUrl = $('baseUrl').value.trim().replace(/\/+$/, '');
  const key = $('key').value.trim();
  if (!baseUrl || !key) { msg('Enter server URL + key first', 'err'); return; }
  msg('Testing…');
  // save first so the background worker uses the latest values
  chrome.storage.sync.set({ baseUrl, key, publish: $('publish').checked }, () => {
    chrome.runtime.sendMessage({ type: 'check', ids: ['0'] }, (r) => {
      if (r && r.ok) msg('Connected ✓ — key accepted', 'ok');
      else msg('Failed: ' + ((r && r.error) || 'no response'), 'err');
    });
  });
});
