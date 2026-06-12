/* v2.2.46 — App-download popup: appears once per visit after a delay.
 * Dismissal (or close) suppresses it for 24h. Config (enable / delay /
 * copy) comes from Website ▸ Settings ▸ App-Download Popup. */
(function () {
    'use strict';

    var KEY = 'uellow_app_popup_seen_until';

    function suppressed() {
        try {
            var until = parseInt(sessionStorage.getItem(KEY) || '0', 10);
            if (until && Date.now() < until) { return true; }
            var dUntil = parseInt(localStorage.getItem(KEY) || '0', 10);
            return !!(dUntil && Date.now() < dUntil);
        } catch (e) { return false; }
    }

    function remember(days) {
        var ms = (days || 1) * 24 * 60 * 60 * 1000;
        try { localStorage.setItem(KEY, String(Date.now() + ms)); } catch (e) {}
        try { sessionStorage.setItem(KEY, String(Date.now() + ms)); } catch (e) {}
    }

    document.addEventListener('DOMContentLoaded', function () {
        var pop = document.getElementById('uellow-app-popup');
        if (!pop) { return; }
        if (suppressed()) { return; }

        var delay = parseInt(pop.getAttribute('data-delay') || '4000', 10);

        function close(rememberDays) {
            pop.classList.remove('uap-show');
            setTimeout(function () { pop.style.display = 'none'; }, 300);
            if (rememberDays) { remember(rememberDays); }
        }

        function open() {
            pop.style.display = 'flex';
            // next frame → transition kicks in
            requestAnimationFrame(function () { pop.classList.add('uap-show'); });
            // showing it counts as "seen" for this session
            try { sessionStorage.setItem(KEY,
                String(Date.now() + 24 * 60 * 60 * 1000)); } catch (e) {}
        }

        var closeBtn = pop.querySelector('.uap-close');
        var dismissBtn = pop.querySelector('.uap-dismiss');
        if (closeBtn) { closeBtn.addEventListener('click', function () { close(1); }); }
        if (dismissBtn) { dismissBtn.addEventListener('click', function () { close(1); }); }
        // click on the dimmed backdrop closes too
        pop.addEventListener('click', function (ev) {
            if (ev.target === pop) { close(1); }
        });
        // tapping a store badge = converted → don't nag again for a week
        pop.querySelectorAll('.uap-badge').forEach(function (a) {
            a.addEventListener('click', function () { remember(7); });
        });

        setTimeout(open, delay);
    });
})();
