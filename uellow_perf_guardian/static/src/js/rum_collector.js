/* Uellow Perf Guardian — RUM beacon with attribution.
 *
 * Captures LCP/CLS/INP/FCP/TTFB plus the CSS selector for the LCP element
 * and the worst INP target. Reports via navigator.sendBeacon on pagehide.
 */
(function () {
    'use strict';

    var SAMPLE_RATE = 0.10;
    var html = document.documentElement;
    if (html && html.dataset && html.dataset.rumRate) {
        SAMPLE_RATE = parseFloat(html.dataset.rumRate) || SAMPLE_RATE;
    }
    if (Math.random() >= SAMPLE_RATE) {
        return;
    }
    if (!('PerformanceObserver' in window) || !('sendBeacon' in navigator)) {
        return;
    }

    function selectorFor(el) {
        if (!el || el.nodeType !== 1) { return ''; }
        if (el.id) { return '#' + el.id; }
        var parts = [];
        var n = el;
        while (n && n.nodeType === 1 && parts.length < 4) {
            var part = n.tagName.toLowerCase();
            if (n.className && typeof n.className === 'string') {
                var c = n.className.trim().split(/\s+/)[0];
                if (c) { part += '.' + c; }
            }
            parts.unshift(part);
            n = n.parentNode;
        }
        return parts.join(' > ').slice(0, 200);
    }

    var data = {
        page: location.pathname,
        ts: Date.now(),
        lcp: 0, cls: 0, inp: 0, fcp: 0, ttfb: 0, dom: 0, load: 0,
        lcp_el: '', inp_el: '',
        conn: (navigator.connection && navigator.connection.effectiveType) || '',
    };
    var sent = false;

    try {
        var nav = performance.getEntriesByType('navigation')[0];
        if (nav) {
            data.ttfb = Math.round(nav.responseStart);
            data.dom  = Math.round(nav.domContentLoadedEventEnd);
            data.load = Math.round(nav.loadEventEnd);
        }
    } catch (e) { /* ignore */ }

    try {
        new PerformanceObserver(function (list) {
            list.getEntries().forEach(function (e) {
                if (e.name === 'first-contentful-paint') {
                    data.fcp = Math.round(e.startTime);
                }
            });
        }).observe({ type: 'paint', buffered: true });
    } catch (e) { /* ignore */ }

    try {
        new PerformanceObserver(function (list) {
            var entries = list.getEntries();
            var last = entries[entries.length - 1];
            if (last) {
                data.lcp = Math.round(last.renderTime || last.loadTime ||
                                      last.startTime);
                if (last.element) {
                    data.lcp_el = selectorFor(last.element);
                }
            }
        }).observe({ type: 'largest-contentful-paint', buffered: true });
    } catch (e) { /* ignore */ }

    try {
        var clsValue = 0;
        new PerformanceObserver(function (list) {
            list.getEntries().forEach(function (e) {
                if (!e.hadRecentInput) {
                    clsValue += e.value;
                }
            });
            data.cls = +clsValue.toFixed(4);
        }).observe({ type: 'layout-shift', buffered: true });
    } catch (e) { /* ignore */ }

    try {
        var worstInp = 0;
        new PerformanceObserver(function (list) {
            list.getEntries().forEach(function (e) {
                if (e.duration > worstInp) {
                    worstInp = e.duration;
                    data.inp = Math.round(worstInp);
                    if (e.target) {
                        data.inp_el = selectorFor(e.target);
                    }
                }
            });
        }).observe({ type: 'event', buffered: true, durationThreshold: 40 });
    } catch (e) { /* ignore */ }

    function flush() {
        if (sent) { return; }
        sent = true;
        try {
            var blob = new Blob([JSON.stringify(data)], {
                type: 'application/json',
            });
            navigator.sendBeacon('/perf/rum', blob);
        } catch (e) { /* ignore */ }
    }

    addEventListener('visibilitychange', function () {
        if (document.visibilityState === 'hidden') { flush(); }
    });
    addEventListener('pagehide', flush);
})();
