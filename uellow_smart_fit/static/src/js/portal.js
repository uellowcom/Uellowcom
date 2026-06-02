/* Uellow portal — tiny shared helpers (lightbox + flash dismiss) */
(function () {
    'use strict';

    function openLightbox(src) {
        const existing = document.getElementById('uellow-portal-lightbox');
        if (existing) existing.remove();
        const overlay = document.createElement('div');
        overlay.id = 'uellow-portal-lightbox';
        const img = document.createElement('img');
        img.src = src;
        overlay.appendChild(img);
        overlay.addEventListener('click', () => overlay.remove());
        document.addEventListener('keydown', function esc(e) {
            if (e.key === 'Escape') { overlay.remove(); document.removeEventListener('keydown', esc); }
        });
        document.body.appendChild(overlay);
    }

    // expose globally so templates can call it inline
    window._uellowLightbox = openLightbox;

    // Wire click-to-enlarge for any .uellow-tryon-session-image img
    document.addEventListener('click', function (ev) {
        const t = ev.target;
        if (t && t.tagName === 'IMG' &&
            t.closest && t.closest('.uellow-tryon-session-image')) {
            openLightbox(t.src);
        }
    });
})();
