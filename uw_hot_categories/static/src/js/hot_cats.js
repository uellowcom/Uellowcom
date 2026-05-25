/** @odoo-module **/
/**
 * UW Hot Categories — Frontend Script  v4.0
 * Reads config from <script type="application/json" class="uw_hc_config">
 * Settings persist because Odoo saves the full page HTML
 */
(function () {
    'use strict';

    var DEFAULT_CFG = {
        mainCat: 603,
        subs: [861, 488, 770, 619, 526, 775],
        mainBgStart: '#1a365d',
        mainBgEnd:   '#2b6cb0',
        subColors:   ['#e0f2fe','#dcfce7','#f3e8ff','#fee2e2','#e0e7ff','#fef9c3'],
        sectionBg:   '#f8f9fa',
        btnColor:    '#f7d117',
        btnTextColor:'#000000',
        showMore:    true,
        showMain:    true,
        imgSize:     'image_512',
    };

    /* ── Read config from JSON script tag ── */
    function getCfg(section) {
        try {
            var el = section.querySelector('script.uw_hc_config');
            if (!el || !el.textContent.trim()) return Object.assign({}, DEFAULT_CFG);
            var parsed = JSON.parse(el.textContent);
            return Object.assign({}, DEFAULT_CFG, parsed);
        } catch (e) {
            return Object.assign({}, DEFAULT_CFG);
        }
    }

    /* ── Shuffle ── */
    function shuffle(arr) {
        var a = arr.slice();
        for (var i = a.length - 1; i > 0; i--) {
            var j = Math.floor(Math.random() * (i + 1));
            var t = a[i]; a[i] = a[j]; a[j] = t;
        }
        return a;
    }

    /* ── HTML escape ── */
    function esc(str) {
        return String(str || '')
            .replace(/&/g, '&amp;').replace(/</g, '&lt;')
            .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    /* ── Detect RTL/Arabic ── */
    function detectRTL() {
        if (document.documentElement.dir === 'rtl') return true;
        if (document.body && document.body.dir === 'rtl') return true;
        var lang = (document.documentElement.lang || '').toLowerCase();
        if (lang.startsWith('ar')) return true;
        var path = window.location.pathname;
        if (path === '/ar' || path.startsWith('/ar/')) return true;
        var match = document.cookie.match(/frontend_lang=([^;]+)/);
        if (match && decodeURIComponent(match[1]).startsWith('ar')) return true;
        try {
            if (window.getComputedStyle(document.documentElement).direction === 'rtl') return true;
        } catch (e) {}
        return false;
    }

    /* ── Get Odoo language code ── */
    function getOdooLang(isRTL) {
        if (!isRTL) return 'en_US';
        var match = document.cookie.match(/frontend_lang=([^;]+)/);
        if (match) {
            var l = decodeURIComponent(match[1]);
            if (l.startsWith('ar')) return l;
        }
        return 'ar_001';
    }

    /* ── Inject CSS color overrides ── */
    function applyColors(section, cfg) {
        section.style.background = cfg.sectionBg;
        var sid = section.id;
        var old = document.getElementById('uw_style_' + sid);
        if (old) old.remove();
        var s = document.createElement('style');
        s.id = 'uw_style_' + sid;
        s.textContent = [
            '#' + sid + ' .uw_f_large{',
            'background:linear-gradient(145deg,' + cfg.mainBgStart + ' 0%,' + cfg.mainBgEnd + ' 100%)!important;}',
            '#' + sid + ' .uw_f_shop_btn{background:' + cfg.btnColor + '!important;',
            'color:' + cfg.btnTextColor + '!important;border-color:' + cfg.btnColor + '!important;}',
            '#' + sid + ' .uw_f_more_btn{background:' + cfg.btnColor + '!important;',
            'color:' + cfg.btnTextColor + '!important;border-color:' + cfg.btnColor + '!important;}'
        ].join('');
        document.head.appendChild(s);
    }

    /* ── Apply RTL layout ── */
    function applyRTL(section, lp) {
        section.setAttribute('dir', 'rtl');
        section.classList.add('uw_rtl');
        var hdr = section.querySelector('.uw_f_header_flex');
        if (hdr) hdr.setAttribute('dir', 'rtl');
        var titleEl = section.querySelector('.uw_f_main_title');
        if (titleEl) titleEl.innerHTML = 'أقسام مميزة <span class="uw_f_flame">🔥</span>';
        var more = section.querySelector('.uw_f_more_btn');
        if (more) { more.textContent = 'المزيد ❯'; more.href = lp + '/shop'; }
    }

    /* ── Apply LTR layout ── */
    function applyLTR(section) {
        section.setAttribute('dir', 'ltr');
        section.classList.remove('uw_rtl');
        var hdr = section.querySelector('.uw_f_header_flex');
        if (hdr) hdr.setAttribute('dir', 'ltr');
        var more = section.querySelector('.uw_f_more_btn');
        if (more && more.textContent === 'المزيد ❯') {
            more.textContent = 'More ❯';
            more.href = '/shop';
        }
    }

    /* ── Fetch from public endpoint ── */
    function fetchData(catIds, lang) {
        return fetch('/uw_hot_cats/data', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                jsonrpc: '2.0', method: 'call',
                params: { cat_ids: catIds, limit: 50, lang: lang }
            })
        })
        .then(function (r) { return r.json(); })
        .then(function (d) { return d.result || {}; })
        .catch(function () { return {}; });
    }

    /* ── Build main card ── */
    function buildMain(catId, name, prods, cfg, lp, isRTL) {
        var p = shuffle(prods)[0];
        var label = isRTL ? '🛍 تصفح القسم' : 'Shop Now →';
        return '<div class="uw_f_card uw_f_large">' +
            '<a href="' + lp + '/shop/category/' + catId + '" class="uw_f_title">' + esc(name) + '</a>' +
            '<a href="' + lp + '/shop/category/' + catId + '" class="uw_f_shop_btn">' + label + '</a>' +
            '<div class="uw_f_hero_wrapper">' +
            '<a href="' + lp + '/shop/product/' + p.id + '" class="uw_f_hero">' +
            '<img src="/web/image/product.template/' + p.id + '/' + cfg.imgSize +
            '" loading="lazy" alt="' + esc(p.name) + '">' +
            '</a></div></div>';
    }

    /* ── Build sub card ── */
    function buildSub(catId, name, prods, idx, cfg, lp) {
        var bg = (cfg.subColors && cfg.subColors[idx]) || '#f5f5f5';
        var pick = shuffle(prods).slice(0, 3);
        var items = pick.map(function (p) {
            return '<a href="' + lp + '/shop/product/' + p.id + '" class="uw_f_item">' +
                '<img src="/web/image/product.template/' + p.id + '/' + cfg.imgSize +
                '" loading="lazy" alt="' + esc(p.name) + '">' + '</a>';
        }).join('');
        return '<div class="uw_f_card" style="background:' + bg + '!important;">' +
            '<a href="' + lp + '/shop/category/' + catId + '" class="uw_f_title">' + esc(name) + '</a>' +
            '<div class="uw_f_row">' + items + '</div>' +
            '</div>';
    }

    /* ── Core render ── */
    function renderSnippet(section) {
        var grid = section.querySelector('.uw_f_grid_box');
        if (!grid) return;

        var cfg    = getCfg(section);
        var isRTL  = detectRTL();
        var lang   = getOdooLang(isRTL);
        var lp     = isRTL ? '/ar' : '';

        // Direction layout
        if (isRTL) { applyRTL(section, lp); }
        else       { applyLTR(section); }

        // More button visibility
        var moreBtn = section.querySelector('.uw_f_more_btn');
        if (moreBtn) moreBtn.style.display = (cfg.showMore !== false) ? '' : 'none';

        // Colors
        applyColors(section, cfg);

        // Build IDs list
        var subs   = Array.isArray(cfg.subs) ? cfg.subs.filter(function (id) { return id > 0; }) : [];
        var allIds = (cfg.showMain !== false ? [cfg.mainCat] : []).concat(subs);

        if (!allIds.length) {
            grid.innerHTML = '<div class="uw_f_loader">' +
                (isRTL ? 'لم يتم تحديد أقسام.' : 'No categories configured.') + '</div>';
            return;
        }

        grid.innerHTML = '<div class="uw_f_loader">' + (isRTL ? 'جار التحميل...' : 'Loading...') + '</div>';

        // Mark render with lang
        section.setAttribute('data-uw-rendered', lang);

        fetchData(allIds, lang).then(function (data) {
            var html = '';

            if (cfg.showMain !== false) {
                var m = data[String(cfg.mainCat)];
                if (m && m.products && m.products.length) {
                    html += buildMain(cfg.mainCat, m.name, m.products, cfg, lp, isRTL);
                }
            }

            subs.forEach(function (id, i) {
                var s = data[String(id)];
                if (!s || !s.products || !s.products.length) return;
                html += buildSub(id, s.name, s.products, i, cfg, lp);
            });

            grid.innerHTML = html ||
                '<div class="uw_f_loader">' + (isRTL ? 'لا توجد منتجات.' : 'No products found.') + '</div>';

            if (isRTL) grid.setAttribute('dir', 'rtl');
            else grid.removeAttribute('dir');
        });
    }

    /* ── Init all ── */
    function initAll() {
        document.querySelectorAll('.uw_hot_cats').forEach(function (sec) {
            if (!sec.id) sec.id = 'uw_hc_' + Math.random().toString(36).substr(2, 8);
            renderSnippet(sec);
        });
    }

    /* ── Force reload (called by options JS) ── */
    window.uwHotCatsReload = function (section) {
        if (!section) { initAll(); return; }
        section.removeAttribute('data-uw-rendered');
        var old = document.getElementById('uw_style_' + section.id);
        if (old) old.remove();
        section.removeAttribute('dir');
        section.classList.remove('uw_rtl');
        renderSnippet(section);
    };

    /* ── Boot ── */
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initAll);
    } else {
        initAll();
    }
    window.addEventListener('load', function () {
        document.querySelectorAll('.uw_hot_cats').forEach(function (sec) {
            var rendered = sec.getAttribute('data-uw-rendered');
            var curLang  = getOdooLang(detectRTL());
            if (!rendered || rendered !== curLang) {
                sec.removeAttribute('data-uw-rendered');
                renderSnippet(sec);
            }
        });
    });

    var _t = setInterval(function () {
        var pending = document.querySelector('.uw_hot_cats:not([data-uw-rendered])');
        if (pending) initAll();
    }, 800);
    setTimeout(function () { clearInterval(_t); }, 30000);

}());
