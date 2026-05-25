/** @odoo-module **/
(function () {
    'use strict';

    function initNewArrivals(section) {
        if (!section || section._ywInit) return;
        section._ywInit = true;

        var root = section.querySelector('.yw-na-root') || section;

        var LIMIT    = 24;
        var PER_PAGE = 6;
        var CURRENCY = 'KD';
        /* website_id يتحدد تلقائياً من الصفحة الحالية */
        var _websiteId = (window.odoo && window.odoo.session_info && window.odoo.session_info.website_id)
                         || (document.querySelector('meta[name="website_id"]') && parseInt(document.querySelector('meta[name="website_id"]').content))
                         || null;
        var DOMAIN = _websiteId
            ? [['is_published','=',true],['sale_ok','=',true],'|',['website_id','=',false],['website_id','=',_websiteId]]
            : [['is_published','=',true],['sale_ok','=',true]];
        var FIELDS   = ['id','name','list_price','compare_list_price','website_url','description_sale','rating_avg','rating_count'];

        var _products   = [];
        var _page       = 0;
        var _totalPages = 0;
        var _lang       = 'ar';
        var _dir        = 'rtl';
        var _autoTimer  = null;

        var i18n = {
            ar: { title:'وصل حديثاً', badge:'جديد', viewall:'عرض الكل ←', viewallUrl:'/ar/shop?order=id+desc', errorTitle:'تعذّر تحميل المنتجات', retry:'إعادة المحاولة' },
            en: { title:'New Arrivals', badge:'New', viewall:'View All →', viewallUrl:'/en/shop?order=id+desc', errorTitle:'Failed to load products', retry:'Retry' }
        };

        function $q(sel) { return root.querySelector(sel); }

        function detectLang() {
            var h = document.documentElement.lang || '';
            var p = window.location.pathname;
            if (h.indexOf('ar') === 0 || p.indexOf('/ar') === 0) return 'ar';
            if (h.indexOf('en') === 0 || p.indexOf('/en') === 0) return 'en';
            return document.documentElement.dir === 'rtl' ? 'ar' : 'en';
        }

        function fmtPrice(val) {
            var n = parseFloat(val) || 0;
            var fmt = n.toLocaleString('en-KW', { minimumFractionDigits:3, maximumFractionDigits:3 });
            return _dir === 'rtl' ? fmt + ' ' + CURRENCY : CURRENCY + ' ' + fmt;
        }

        function starsHTML(avg, allGray) {
            var STAR = function(fill) {
                return '<svg class="yw-star" viewBox="0 0 14.5 14" xmlns="http://www.w3.org/2000/svg">' +
                    '<path d="M7.25 0L9.42 4.5L14.5 5.22L10.87 8.75L11.77 14L7.25 11.4L2.73 14L3.63 8.75L0 5.22L5.08 4.5Z" fill="' + fill + '"/>' +
                    '</svg>';
            };
            if (allGray) return Array(5).fill(STAR('#D9D9D9')).join('');
            var stars = [];
            for (var i = 1; i <= 5; i++) {
                if (avg >= i) {
                    stars.push(STAR('#F5C10A'));
                } else if (avg >= i - 0.5) {
                    var uid = 'yw-hg' + i + Math.floor(avg * 10);
                    stars.push('<svg class="yw-star" viewBox="0 0 14.5 14" xmlns="http://www.w3.org/2000/svg"><defs><linearGradient id="' + uid + '"><stop offset="50%" stop-color="#F5C10A"/><stop offset="50%" stop-color="#D9D9D9"/></linearGradient></defs><path d="M7.25 0L9.42 4.5L14.5 5.22L10.87 8.75L11.77 14L7.25 11.4L2.73 14L3.63 8.75L0 5.22L5.08 4.5Z" fill="url(#' + uid + ')"/></svg>');
                } else {
                    stars.push(STAR('#D9D9D9'));
                }
            }
            return stars.join('');
        }

        /* ══ Fetch ══ */
        function fetchProducts() {
            var langCode = _lang === 'ar' ? 'ar_001' : 'en_US';

            fetch('/uellow/new-arrivals?limit=' + LIMIT + '&lang=' + langCode)
            .then(function(r) {
                var ct = r.headers.get('content-type') || '';
                if (!ct.includes('application/json')) throw new Error('not_json');
                return r.json();
            })
            .then(function(data) {
                if (!data || data.status !== 'ok') throw new Error('err');
                return data.products || [];
            })
            .catch(function() {
                return fetch('/web/dataset/call_kw/product.template/search_read', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'include',
                    body: JSON.stringify({
                        jsonrpc: '2.0', method: 'call',
                        params: {
                            model: 'product.template', method: 'search_read', args: [],
                            kwargs: { domain: DOMAIN, fields: FIELDS, limit: LIMIT, order: 'id desc', context: { lang: langCode, website_id: _websiteId || 1 } }
                        }
                    })
                })
                .then(function(r) { return r.json(); })
                .then(function(d) {
                    if (d.error) throw new Error(d.error.data ? d.error.data.message : 'error');
                    return d.result || [];
                });
            })
            .then(function(products) {
                _products = products;
                if (!_products.length) throw new Error('لا توجد منتجات');
                _totalPages = Math.ceil(_products.length / PER_PAGE);
                _page = 0;
                renderAllCards();
                goToPage(0);
                buildDots();
                var nav = $q('.yw-center'); if (nav) nav.style.display = 'flex';
                startAutoPlay();
            })
            .catch(function(err) { renderError(err.message); });
        }

        /* ══ Render all cards once ══ */
        function renderAllCards() {
            var track = $q('.yw-track'); if (!track) return;
            track.innerHTML = _products.map(function(p) {
                var price    = parseFloat(p.list_price) || 0;
                var oldPrice = parseFloat(p.compare_list_price) || 0;
                var hasDisc  = oldPrice > price && oldPrice > 0;
                var discPct  = hasDisc ? Math.round(((oldPrice - price) / oldPrice) * 100) : 0;
                var name     = _lang === 'ar' ? (p.name || '') : (p.description_sale || p.name || '');
                var imgSrc   = '/web/image/product.template/' + p.id + '/image_512';
                var prodUrl  = p.website_url || '/shop/product/' + p.id;
                var rAvg     = parseFloat(p.rating_avg) || 0;
                var rCount   = parseInt(p.rating_count) || 0;
                var hasRating = rCount > 0;
                return (
                    '<a class="yw-card" href="' + prodUrl + '">' +
                        '<div class="yw-img-wrap"><div class="yw-img-inner">' +
                            '<img src="' + imgSrc + '" alt="' + name.replace(/"/g, '') + '" loading="lazy" ' +
                            'onerror="this.parentNode.innerHTML=\'<div class=yw-img-ph></div>\'">' +
                        '</div><span class="yw-new-tag">NEW</span></div>' +
                        '<div class="yw-body">' +
                            '<p class="yw-name">' + name + '</p>' +
                            '<div class="yw-rating">' +
                                '<div class="yw-stars">' + starsHTML(rAvg, !hasRating) + '</div>' +
                                (hasRating ? '<span class="yw-rating-count">(' + rCount + ')</span>' : '') +
                            '</div>' +
                            '<div class="yw-price-row">' +
                                '<span class="yw-price-current">' + fmtPrice(price) + '</span>' +
                                (hasDisc ? '<span class="yw-price-old">' + fmtPrice(oldPrice) + '</span>' : '') +
                                (hasDisc ? '<span class="yw-disc-badge">-' + discPct + '%</span>' : '') +
                            '</div>' +
                        '</div>' +
                    '</a>'
                );
            }).join('');
        }

        /* ══ Slider movement ══ */
        function getVisible() {
            var w = root.offsetWidth;
            if (w <= 440) return 2;
            if (w <= 680) return 3;
            if (w <= 1000) return 4;
            return PER_PAGE;
        }

        function goToPage(page) {
            _page = Math.max(0, Math.min(page, _totalPages - 1));
            var track = $q('.yw-track'); if (!track) return;
            var outer = $q('.yw-slider-outer'); if (!outer) return;

            var visible  = getVisible();
            var outerW   = outer.offsetWidth;
            var gap      = 8;
            var cardW    = (outerW - gap * (visible - 1)) / visible;
            var pageW    = (cardW + gap) * visible;
            var offset   = _page * pageW;

            /* تأكد إن كل الكروت بنفس العرض */
            var cards = track.querySelectorAll('.yw-card');
            for (var i = 0; i < cards.length; i++) {
                cards[i].style.width     = cardW + 'px';
                cards[i].style.minWidth  = cardW + 'px';
                cards[i].style.maxWidth  = cardW + 'px';
                cards[i].style.flexShrink = '0';
            }

            if (_dir === 'rtl') {
                track.style.transform = 'translateX(' + offset + 'px)';
            } else {
                track.style.transform = 'translateX(-' + offset + 'px)';
            }

            var prev = $q('.yw-nav-prev'); if (prev) prev.disabled = _page === 0;
            var next = $q('.yw-nav-next'); if (next) next.disabled = _page >= _totalPages - 1;
            updateDots();
        }

        /* ══ Auto-play ══ */
        function startAutoPlay() {
            if (_totalPages <= 1) return;
            if (_autoTimer) clearInterval(_autoTimer);
            _autoTimer = setInterval(function() {
                var next = _page + 1 >= _totalPages ? 0 : _page + 1;
                goToPage(next);
            }, 15000);
        }

        function resetAutoPlay() {
            if (_autoTimer) { clearInterval(_autoTimer); _autoTimer = null; }
            startAutoPlay();
        }

        /* ══ Dots ══ */
        function buildDots() {
            var dots = $q('.yw-dots'); if (!dots) return;
            dots.innerHTML = Array.from({ length: _totalPages }, function(_, i) {
                return '<button class="yw-dot' + (i === 0 ? ' active' : '') + '" data-page="' + i + '"></button>';
            }).join('');
            dots.addEventListener('click', function(e) {
                var btn = e.target;
                while (btn && btn !== dots && !btn.dataset.page) btn = btn.parentNode;
                if (btn && btn.dataset && btn.dataset.page !== undefined) {
                    resetAutoPlay(); goToPage(parseInt(btn.dataset.page));
                }
            });
        }

        function updateDots() {
            var items = root.querySelectorAll('.yw-dots .yw-dot');
            for (var i = 0; i < items.length; i++) items[i].classList.toggle('active', i === _page);
        }

        /* ══ Touch / Swipe ══ */
        function bindTouch() {
            var outer = $q('.yw-slider-outer'); if (!outer) return;
            var startX = 0, startY = 0, moved = false;

            outer.addEventListener('touchstart', function(e) {
                startX = e.touches[0].clientX;
                startY = e.touches[0].clientY;
                moved  = false;
            }, { passive: true });

            outer.addEventListener('touchmove', function(e) {
                var dx = Math.abs(e.touches[0].clientX - startX);
                var dy = Math.abs(e.touches[0].clientY - startY);
                if (dx > dy && dx > 5) { moved = true; e.preventDefault(); }
            }, { passive: false });

            outer.addEventListener('touchend', function(e) {
                if (!moved) return;
                var diffX = startX - e.changedTouches[0].clientX;
                if (Math.abs(diffX) < 30) return;
                resetAutoPlay();
                if (_dir === 'rtl') { goToPage(diffX > 0 ? _page - 1 : _page + 1); }
                else                { goToPage(diffX > 0 ? _page + 1 : _page - 1); }
            }, { passive: true });
        }

        /* ══ Error ══ */
        function renderError(msg) {
            var t = i18n[_lang]; var track = $q('.yw-track'); if (!track) return;
            track.innerHTML = '<div class="yw-error"><div style="font-size:20px;margin-bottom:6px">⚠</div>' +
                '<div style="font-weight:700;font-size:13px;margin-bottom:6px">' + t.errorTitle + '</div>' +
                '<div class="yw-error-box">' + msg + '</div>' +
                '<button class="yw-btn yw-btn-retry">' + t.retry + '</button></div>';
            var r = root.querySelector('.yw-btn-retry'); if (r) r.addEventListener('click', init);
        }

        /* ══ Lang ══ */
        function applyLang() {
            var t = i18n[_lang];
            root.setAttribute('dir', _dir);
            root.style.fontFamily = _lang === 'ar' ? "'Cairo',sans-serif" : "'Inter',sans-serif";
            var el;
            el = $q('.yw-title');   if (el) el.textContent = t.title;
            el = $q('.yw-badge');   if (el) el.textContent = t.badge;
            el = $q('.yw-viewall'); if (el) { el.textContent = t.viewall; el.href = t.viewallUrl; }
        }

        /* ══ Nav buttons ══ */
        function bindNav() {
            var prev = $q('.yw-nav-prev'); var next = $q('.yw-nav-next');
            if (prev) prev.addEventListener('click', function() { resetAutoPlay(); goToPage(_page - 1); });
            if (next) next.addEventListener('click', function() { resetAutoPlay(); goToPage(_page + 1); });
        }

        /* ══ Init ══ */
        function init() {
            _lang = detectLang();
            _dir  = _lang === 'ar' ? 'rtl' : 'ltr';
            applyLang(); bindNav(); bindTouch();
            fetchProducts();
        }

        init();
    }

    function scanAndInit() {
        document.querySelectorAll('.s_uellow_new_arrivals').forEach(function(el) {
            initNewArrivals(el);
        });
    }

    if (document.readyState === 'complete') { scanAndInit(); }
    else { window.addEventListener('load', scanAndInit); }

    /* دعم الـ Website Builder */
    var obs = new MutationObserver(function(mutations) {
        mutations.forEach(function(m) {
            m.addedNodes.forEach(function(node) {
                if (node.nodeType !== 1) return;
                if (node.classList && node.classList.contains('s_uellow_new_arrivals')) initNewArrivals(node);
                node.querySelectorAll && node.querySelectorAll('.s_uellow_new_arrivals').forEach(initNewArrivals);
            });
        });
    });
    if (document.body) obs.observe(document.body, { childList: true, subtree: true });
    else document.addEventListener('DOMContentLoaded', function() { obs.observe(document.body, { childList: true, subtree: true }); });

})();
