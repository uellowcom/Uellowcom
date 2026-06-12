/* Show the banner only on mobile UAs where the app is NOT already
 * installed (best-effort detection — can't be perfect without the
 * Android Asset Statement handshake / iOS Smart App Banner).
 *
 * CTA tries to open the app via the custom scheme (uellow://...). If
 * the OS doesn't intercept within 1.2s we assume the app isn't
 * installed and fall through to the Play Store / App Store / APK
 * download.
 */
(function () {
    'use strict';

    var ua = navigator.userAgent || '';
    var isMobile = /Mobi|Android|iPhone|iPad|iPod|Opera Mini|IEMobile|webOS|BlackBerry/i.test(ua);
    // v2.2.46 — used to early-return on desktop, so the banner NEVER appeared
    // for anyone on a computer. Now it shows everywhere; on desktop the CTA
    // jumps straight to the store, on mobile it tries the deep link first.

    // Hide for a week after dismissal
    try {
        var hideUntil = parseInt(localStorage.getItem('uellow_banner_hide_until') || '0', 10);
        if (hideUntil && Date.now() < hideUntil) return;
    } catch (e) {}

    document.addEventListener('DOMContentLoaded', function () {
        var banner = document.getElementById('uellow-app-banner');
        if (!banner) return;
        // Respect the admin device-scope setting (Mobile + Desktop / Mobile /
        // Desktop). Default 'both' so the banner shows on phones AND computers.
        var scope = banner.getAttribute('data-devices') || 'both';
        if (scope === 'mobile' && !isMobile) return;
        if (scope === 'desktop' && isMobile) return;
        banner.style.display = 'block';

        var cta = document.getElementById('uab-cta');
        var close = document.getElementById('uab-close');

        if (close) {
            close.addEventListener('click', function () {
                banner.style.display = 'none';
                try {
                    // Hide for 7 days
                    localStorage.setItem('uellow_banner_hide_until',
                        String(Date.now() + 7 * 24 * 60 * 60 * 1000));
                } catch (e) {}
            });
        }

        if (cta) {
            var isIos = /iPhone|iPad|iPod/i.test(ua);
            var isAndroid = /Android/i.test(ua);
            var path = window.location.pathname + window.location.search;
            var schemeUrl = 'uellow://' + path.replace(/^\//, '');
            var storeUrl;
            if (isIos) {
                storeUrl = 'https://apps.apple.com/app/id6769010765';
            } else if (isAndroid) {
                storeUrl = 'https://play.google.com/store/apps/details?id=com.uellow.app';
            } else {
                storeUrl = 'https://play.google.com/store/apps/details?id=com.uellow.app';
            }

            cta.addEventListener('click', function (ev) {
                ev.preventDefault();
                // Desktop: no app to deep-link into — go straight to the store.
                if (!isMobile) { window.open(storeUrl, '_blank'); return; }
                var resolved = false;
                function flagResolved() { resolved = true; }
                document.addEventListener('visibilitychange', flagResolved, { once: true });

                // Attempt the deep link
                window.location.href = schemeUrl;
                setTimeout(function () {
                    document.removeEventListener('visibilitychange', flagResolved);
                    if (!resolved) {
                        window.location.href = storeUrl;
                    }
                }, 1200);
            });
        }
    });
})();
