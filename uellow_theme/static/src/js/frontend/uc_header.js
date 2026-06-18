/* Uellow header — interactive layer */
(function () {
    "use strict";

    // ─── Mega-menu cascade ────────────────────────────────────────────
    function bindMega(root) {
        var rail   = root.querySelector(".uc-catmega-rail");
        var panels = root.querySelector(".uc-catmega-panels");
        if (!rail || !panels) return;

        function activate(catId) {
            rail.querySelectorAll(".uc-catmega-parent").forEach(function (li) {
                li.classList.toggle("is-active", li.dataset.cat === catId);
            });
            panels.querySelectorAll(".uc-catmega-panel").forEach(function (p) {
                p.classList.toggle("is-active", p.dataset.cat === catId);
            });
        }
        rail.querySelectorAll(".uc-catmega-parent").forEach(function (li) {
            li.addEventListener("mouseenter", function () { activate(li.dataset.cat); });
            li.addEventListener("focusin",    function () { activate(li.dataset.cat); });
        });
    }
    function initMega() {
        document.querySelectorAll(".uc-catmega").forEach(bindMega);
    }

    // ─── Auth popover — tabs + register opens signup modal ────────────
    function initAuth() {
        // Tab switching (login ↔ register inside the popover)
        document.addEventListener("click", function (ev) {
            var tab = ev.target.closest(".uc-auth-tab");
            if (tab) {
                ev.preventDefault();
                var menu = tab.closest(".uc-auth-menu");
                if (!menu) return;
                var target = tab.dataset.ucAuthTab;
                menu.querySelectorAll(".uc-auth-tab").forEach(function (t) {
                    t.classList.toggle("is-active", t.dataset.ucAuthTab === target);
                });
                menu.querySelectorAll(".uc-auth-pane").forEach(function (p) {
                    p.classList.toggle("is-active", p.dataset.ucAuthPane === target);
                });
                return;
            }

            // Register button → open signup modal (no navigation)
            var openSignup = ev.target.closest("[data-uc-open='signup']");
            if (openSignup) {
                ev.preventDefault();
                openSignupModal();
            }
        });
    }

    function openSignupModal() {
        var modalEl = document.getElementById("uc-signup-modal");
        if (!modalEl) {
            window.location.href = "/web/signup";
            return;
        }
        // Lazy-load the iframe so the bundle is not fetched on every page view
        var frame = document.getElementById("uc-signup-frame");
        if (frame && frame.dataset.ucSrc && frame.src !== frame.dataset.ucSrc) {
            try {
                var url = new URL(frame.dataset.ucSrc, window.location.origin);
                url.searchParams.set("redirect", window.location.pathname);
                frame.src = url.pathname + url.search;
            } catch (e) {
                frame.src = frame.dataset.ucSrc;
            }
        }
        try {
            (window.bootstrap && window.bootstrap.Modal
                ? window.bootstrap.Modal.getOrCreateInstance(modalEl)
                : new bootstrap.Modal(modalEl)
            ).show();
        } catch (e) {
            window.location.href = "/web/signup";
        }
    }

    // Cart now delegates to theme_prime's built-in sidebar
    // (`.tp-cart-sidebar-action` handler).

    // ─── Ask Beena trigger ────────────────────────────────────────────
    // Beena's JS hides its own widget on mobile, then we hide the floating
    // launcher to free the screen. Reach the toggle by force-visiblising
    // the launcher for one frame and firing every event flavour that
    // could possibly be bound.
    function openBeena() {
        var btn = document.getElementById("beena-float-btn");
        if (btn) {
            // Override any display:none so the click registers
            var orig = btn.getAttribute("style") || "";
            btn.setAttribute("style",
                "display:flex !important;position:fixed;inset:auto auto -200px auto;" +
                "opacity:0;visibility:hidden;pointer-events:auto;");

            var fired = false;
            try {
                if (window.jQuery && window.jQuery(btn).length) {
                    window.jQuery(btn).trigger("click");
                    fired = true;
                }
            } catch (e) {}
            try {
                if (typeof btn.click === "function") { btn.click(); fired = true; }
            } catch (e) {}
            try {
                ["pointerdown", "mousedown", "mouseup", "click"].forEach(function (t) {
                    btn.dispatchEvent(new MouseEvent(t, {
                        bubbles: true, cancelable: true, view: window,
                    }));
                });
            } catch (e) {}

            // If Beena's open animation moved the widget into the viewport,
            // it overrode our inline style; if not, restore the hidden
            // attribute so the launcher stays parked.
            setTimeout(function () {
                if (!document.querySelector(".beena-open, [data-beena-open='1']")) {
                    btn.setAttribute("style", orig);
                }
            }, 250);

            if (fired) return;
        }
        // Cross-page fallback — Beena widget isn't on the current page.
        // Land on home with a query flag the init loop watches for.
        window.location.href = "/?open_beena=1";
    }

    // ─── Loading state helper (spinner overlay) ───────────────────────
    function withLoading(el, fn) {
        if (!el) { try { fn(); } catch (e) {} return; }
        el.classList.add("uc-is-loading");
        // Yield a frame so the spinner paints BEFORE the proxy work runs.
        // Without this, synchronous code on the trigger can race past the
        // browser's repaint and the spinner never shows.
        requestAnimationFrame(function () {
            try { fn(); } catch (e) {}
            // Keep the spinner up long enough to actually register visually
            // (Fast Buy bundle can take a moment to wake up).
            setTimeout(function () { el.classList.remove("uc-is-loading"); }, 900);
        });
    }

    // ─── Mobile bottom navigation ─────────────────────────────────────
    function initMobNav() {
        // Highlight the item matching the current path
        var path = window.location.pathname || "/";
        document.querySelectorAll(".uc-mobnav .uc-mobnav-item").forEach(function (a) {
            var href = (a.getAttribute("href") || "").split("?")[0];
            if (!href || href === "#") return;
            var match = (href === "/")
                ? (path === "/" || path === "")
                : path === href || path.indexOf(href + "/") === 0;
            a.classList.toggle("is-active", match);
        });
    }

    // Trigger a click that fires BOTH native DOM listeners and jQuery
    // event handlers — fast_buy and Odoo's website_sale rely on jQuery,
    // so a single approach isn't enough.
    function triggerNativeClick(el) {
        if (!el) return false;
        var fired = false;
        try {
            if (window.jQuery && window.jQuery(el).length) {
                window.jQuery(el).trigger("click");
                fired = true;
            }
        } catch (e) {}
        try {
            if (typeof el.click === "function") {
                el.click();
                fired = true;
            }
        } catch (e) {}
        if (!fired) {
            ["pointerdown", "mousedown", "mouseup", "click"].forEach(function (t) {
                el.dispatchEvent(new MouseEvent(t, { bubbles: true, cancelable: true, view: window }));
            });
        }
        return true;
    }

    function proxyAddToCart() {
        var btn =
            document.querySelector("#add_to_cart:not(.uc-mobnav-prod-cart)") ||
            document.querySelector(".product-add-to-cart") ||
            document.querySelector("a.js_check_product[id='add_to_cart']") ||
            document.querySelector("[name='add_to_cart']");
        if (btn && triggerNativeClick(btn)) return;
        var form = document.querySelector("form.js_add_cart_json, #product_details form, form[action*='/shop/cart/update']");
        if (form) form.submit();
    }

    function proxyFastBuy() {
        // The zorder module attaches its handler to `.zo-btn-open`
        // (inside `.zo-wrap` carrying the product data attributes).
        // Trigger click on the button — its handler reads wrap's data
        // and opens the dialog. Older builds used `.qc-open-btn`; we
        // keep those as fallbacks in case the module gets renamed back.
        var btn =
            document.querySelector(".zo-btn-open") ||
            document.querySelector(".zo-wrap .btn") ||
            document.querySelector(".qc-open-btn") ||
            document.querySelector(".qc-btn-wrap .btn") ||
            document.querySelector("[data-zorder-fast-buy]") ||
            document.querySelector(".js_zorder_fast_buy");
        if (btn) {
            triggerNativeClick(btn);
            return;
        }
        // If zorder bundle hasn't loaded yet, give it one chance to
        // attach and try again.
        setTimeout(function () {
            var late = document.querySelector(".zo-btn-open, .qc-open-btn");
            if (late) triggerNativeClick(late);
        }, 350);
    }

    // ─── Click delegation (with spinner) ──────────────────────────────
    document.addEventListener("click", function (ev) {
        var btn;
        if ((btn = ev.target.closest("#uc-beena-btn, #uc-mobnav-beena, .uc-mobnav-prod-beena"))) {
            ev.preventDefault();
            withLoading(btn, openBeena);
            return;
        }
        if ((btn = ev.target.closest("#uc-mobnav-add-to-cart"))) {
            ev.preventDefault();
            withLoading(btn, proxyAddToCart);
            return;
        }
        if ((btn = ev.target.closest("#uc-mobnav-fast-buy"))) {
            ev.preventDefault();
            withLoading(btn, proxyFastBuy);
            return;
        }
    });

    // ─── Deals countdown ──────────────────────────────────────────────
    function initCountdown() {
        var card = document.getElementById("uc-deals-card");
        if (!card) return;
        var h = card.querySelector('[data-cd="hours"]');
        var m = card.querySelector('[data-cd="minutes"]');
        var s = card.querySelector('[data-cd="seconds"]');
        if (!h || !m || !s) return;
        function pad(n) { return n < 10 ? "0" + n : "" + n; }
        // Real flash-sale end (mobile.flash.sale.end_date) when present,
        // otherwise count down to end-of-day.
        var endAttr = card.getAttribute("data-deals-end");
        var endTime = endAttr ? new Date(endAttr).getTime() : null;
        if (endTime && isNaN(endTime)) endTime = null;
        function tick() {
            var now = new Date();
            var target;
            if (endTime) {
                target = endTime;
            } else {
                var eod = new Date(now);
                eod.setHours(23, 59, 59, 999);
                target = eod.getTime();
            }
            var diff = target - now.getTime();
            if (diff < 0) diff = 0;
            var hh = Math.floor(diff / 3600000);
            var mm = Math.floor((diff % 3600000) / 60000);
            var ss = Math.floor((diff % 60000) / 1000);
            h.textContent = pad(hh);
            m.textContent = pad(mm);
            s.textContent = pad(ss);
        }
        tick();
        setInterval(tick, 1000);
    }

    // ─── Inline search autocomplete ───────────────────────────────────
    function initSearch() {
        var form  = document.getElementById("uc-search-form");
        var input = document.getElementById("uc-search-input");
        var box   = document.getElementById("uc-search-suggest");
        if (!form || !input || !box) return;

        var token = 0;
        var debounce;
        function close() { box.hidden = true; box.innerHTML = ""; }
        function open() { box.hidden = false; }
        function escapeHtml(s) {
            return String(s || "")
                .replace(/&/g, "&amp;").replace(/</g, "&lt;")
                .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
        }
        function render(data) {
            var html = "";
            if (data.categories && data.categories.length) {
                html += '<div class="uc-sg-section"><div class="uc-sg-head"><i class="fa fa-th"></i> Categories</div>';
                data.categories.forEach(function (c) {
                    html += '<a class="uc-sg-item" href="' + escapeHtml(c.url) + '">' +
                        (c.image ? '<img class="uc-sg-img" src="' + escapeHtml(c.image) + '" alt=""/>'
                                 : '<span class="uc-sg-img uc-sg-img-fa"><i class="fa fa-folder-o"></i></span>') +
                        '<span class="uc-sg-name">' + escapeHtml(c.name) + '</span>' +
                        '</a>';
                });
                html += '</div>';
            }
            if (data.brands && data.brands.length) {
                html += '<div class="uc-sg-section"><div class="uc-sg-head"><i class="fa fa-bookmark"></i> Brands</div>';
                data.brands.forEach(function (b) {
                    html += '<a class="uc-sg-item" href="' + escapeHtml(b.url) + '">' +
                        (b.image ? '<img class="uc-sg-img" src="' + escapeHtml(b.image) + '" alt=""/>'
                                 : '<span class="uc-sg-img uc-sg-img-fa"><i class="fa fa-tag"></i></span>') +
                        '<span class="uc-sg-name">' + escapeHtml(b.name) + '</span>' +
                        '</a>';
                });
                html += '</div>';
            }
            if (data.products && data.products.length) {
                html += '<div class="uc-sg-section"><div class="uc-sg-head"><i class="fa fa-cube"></i> Products</div>';
                data.products.forEach(function (p) {
                    html += '<a class="uc-sg-item uc-sg-item-prod" href="' + escapeHtml(p.url) + '">' +
                        '<img class="uc-sg-img" src="' + escapeHtml(p.image) + '" alt=""/>' +
                        '<span class="uc-sg-prod"><span class="uc-sg-name">' + escapeHtml(p.name) + '</span></span>' +
                        '</a>';
                });
                html += '</div>';
            }
            if (!html) {
                html = '<div class="uc-sg-empty"><i class="fa fa-search"></i> No matches yet — keep typing…</div>';
            } else {
                var q = escapeHtml(input.value || "");
                html += '<a class="uc-sg-all" href="/shop?search=' + encodeURIComponent(input.value) +
                        '"><i class="fa fa-arrow-right"></i> See all results for "' + q + '"</a>';
            }
            box.innerHTML = html;
            open();
        }
        function fetchSuggest(q) {
            var me = ++token;
            fetch("/uc/search_suggest", {
                method: "POST",
                credentials: "same-origin",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ params: { q: q } }),
            })
            .then(function (r) { return r.json(); })
            .then(function (j) {
                if (me !== token) return; // stale
                var data = (j && j.result) || j || {};
                render(data);
            })
            .catch(function () { close(); });
        }
        input.addEventListener("input", function () {
            var q = (input.value || "").trim();
            clearTimeout(debounce);
            if (q.length < 2) { close(); return; }
            debounce = setTimeout(function () { fetchSuggest(q); }, 180);
        });
        input.addEventListener("focus", function () {
            if (box.innerHTML) open();
        });
        document.addEventListener("click", function (ev) {
            if (!form.contains(ev.target)) close();
        });
        input.addEventListener("keydown", function (ev) {
            if (ev.key === "Escape") { close(); input.blur(); }
        });
    }

    function init() {
        initMega();
        initAuth();
        initCountdown();
        initSearch();
        initMobNav();
    }
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }

    // Cross-page Beena fallback
    if (window.location.search.indexOf("open_beena=1") !== -1) {
        var tries = 0;
        var timer = setInterval(function () {
            tries += 1;
            if (document.getElementById("beena-float-btn")) {
                openBeena();
                clearInterval(timer);
            } else if (tries > 20) {
                clearInterval(timer);
            }
        }, 250);
    }
})();
