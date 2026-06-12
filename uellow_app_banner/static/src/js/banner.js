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
    var isIosSafari = /iPhone|iPad|iPod/i.test(ua) && /Safari/i.test(ua) && !/CriOS|FxiOS|EdgiOS/i.test(ua);
    // v2.2.46 — used to early-return on desktop, so the banner NEVER appeared
    // for anyone on a computer. Now it shows everywhere; on desktop the CTA
    // jumps straight to the store, on mobile it tries the deep link first.

    // Hide for the admin-configured window after dismissal
    try {
        var hideUntil = parseInt(localStorage.getItem('uellow_banner_hide_until') || '0', 10);
        if (hideUntil && Date.now() < hideUntil) return;
    } catch (e) {}

    // Frequency throttle — don't re-show within the chosen cadence.
    function freqWindowMs(freq) {
        if (freq === 'always') return 0;
        if (freq === 'daily') return 24 * 60 * 60 * 1000;
        if (freq === 'weekly') return 7 * 24 * 60 * 60 * 1000;
        if (freq === 'once') return 100 * 365 * 24 * 60 * 60 * 1000; // ~forever
        return 24 * 60 * 60 * 1000;
    }

    document.addEventListener('DOMContentLoaded', function () {
        var banner = document.getElementById('uellow-app-banner');
        if (!banner) return;
        // On iOS Safari, Apple's native Smart App Banner handles everything
        // (auto-hide-if-installed + deep link), so suppress our custom bar.
        if (isIosSafari && banner.getAttribute('data-ios-smart') === '1') return;
        // Respect the admin device-scope setting (Mobile + Desktop / Mobile /
        // Desktop). Default 'both' so the banner shows on phones AND computers.
        var scope = banner.getAttribute('data-devices') || 'both';
        if (scope === 'mobile' && !isMobile) return;
        if (scope === 'desktop' && isMobile) return;
        // Frequency: skip if last shown inside the window.
        var freq = banner.getAttribute('data-frequency') || 'daily';
        var win = freqWindowMs(freq);
        try {
            var lastShown = parseInt(localStorage.getItem('uellow_banner_last_shown') || '0', 10);
            if (win && lastShown && (Date.now() - lastShown) < win) return;
            localStorage.setItem('uellow_banner_last_shown', String(Date.now()));
        } catch (e) {}
        banner.style.display = 'block';

        var cta = document.getElementById('uab-cta');
        var close = document.getElementById('uab-close');

        if (close) {
            close.addEventListener('click', function () {
                banner.style.display = 'none';
                try {
                    var days = parseInt(banner.getAttribute('data-dismiss-days') || '7', 10) || 7;
                    localStorage.setItem('uellow_banner_hide_until',
                        String(Date.now() + days * 24 * 60 * 60 * 1000));
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
