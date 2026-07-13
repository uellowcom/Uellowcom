/* Uellow website journey tracker (2026-06-26)
 * Mirrors the mobile app's ActivityTracker: logs a page view on load and a
 * page-leave (with time-on-page) on hide/unload, beaconed to /website/track
 * → uellow.customer.activity. Best-effort, fire-and-forget, never blocks. */
(function () {
    "use strict";
    var path = location.pathname + location.search;
    var entered = Date.now();
    var left = false;

    function send(events) {
        try {
            var blob = new Blob([JSON.stringify({ events: events })],
                { type: "application/json" });
            if (navigator.sendBeacon &&
                navigator.sendBeacon("/website/track", blob)) {
                return;
            }
        } catch (e) { /* fall through to fetch */ }
        try {
            fetch("/website/track", {
                method: "POST",
                body: JSON.stringify({ events: events }),
                headers: { "Content-Type": "application/json" },
                keepalive: true,
            });
        } catch (e) { /* give up silently */ }
    }

    function pageView() {
        var ev = { event: "screen_view", screen: path, label: document.title };
        // best-effort product reference on /shop/<slug>-<id>
        if (path.indexOf("/shop/") === 0) {
            var m = path.match(/-([0-9]+)(?:[/?#]|$)/);
            if (m) { ev.ref_model = "product.template"; ev.ref_id = parseInt(m[1], 10); }
        }
        send([ev]);
    }

    function pageLeave() {
        if (left) { return; }
        left = true;
        send([{ event: "screen_leave", screen: path,
                duration_ms: Date.now() - entered }]);
    }

    if (document.readyState !== "loading") {
        pageView();
    } else {
        document.addEventListener("DOMContentLoaded", pageView);
    }
    document.addEventListener("visibilitychange", function () {
        if (document.visibilityState === "hidden") { pageLeave(); }
    });
    window.addEventListener("pagehide", pageLeave);
})();
