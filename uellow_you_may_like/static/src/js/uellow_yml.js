/**
 * Uellow – You May Like  |  uellow_yml.js
 */
(function () {
    "use strict";

    const PAGE_SIZE    = 10;
    const AUTO_ROUNDS  = 5;
    const MANUAL_BATCH = 20;

    function detectEnv() {
        const lang  = (document.documentElement.lang || 'en_US').replace('-', '_');
        const isRTL = document.documentElement.dir === 'rtl' || lang.startsWith('ar');
        return { lang, isRTL };
    }

    function buildStars(avg) {
        const n = Math.round(avg || 0);
        let h = '';
        for (let i = 1; i <= 5; i++)
            h += `<i class="fa ${i <= n ? 'fa-star' : 'fa-star-o uyw_star_empty'}"></i>`;
        return h;
    }

    function buildTicker(saveVal, isRTL) {
        const has = saveVal > 0;
        const rows = [];
        if (has) rows.push({ cls: 'uyw_save_li', icon: 'fa-tag',
            text: (isRTL ? 'وفر: ' : 'Save: ') + saveVal.toFixed(2) + ' KD' });
        rows.push({ icon: 'fa-bolt',      text: isRTL ? 'توصيل سريع'  : 'Fast Delivery'      });
        rows.push({ icon: 'fa-shield',    text: isRTL ? 'جودة مضمونة' : 'Quality Guaranteed' });
        rows.push({ icon: 'fa-comment-o', text: isRTL ? 'منتج رائع'   : 'Great Product'      });
        if (has) rows.push({ cls: 'uyw_save_li', icon: 'fa-tag',
            text: (isRTL ? 'وفر: ' : 'Save: ') + saveVal.toFixed(2) + ' KD' });
        return rows.map(r =>
            `<li class="${r.cls||''}"><i class="fa ${r.icon}"></i> ${r.text}</li>`
        ).join('');
    }

    function renderCard(p, isRTL) {
        const hasDis  = p.compare_list_price > p.list_price;
        const saveVal = hasDis ? (p.compare_list_price - p.list_price) : 0;
        const perc    = hasDis ? Math.round(saveVal / p.compare_list_price * 100) : 0;
        const canBuy  = (p.qty_available > 0) || p.allow_out_of_stock_order;
        const inStock = p.qty_available > 0;

        const priceHTML = hasDis
            ? `<span class="uyw_price_now">${p.list_price.toFixed(2)} KD</span>
               <span class="uyw_price_old">${p.compare_list_price.toFixed(2)}</span>
               <span class="uyw_disc_inline">-${perc}%</span>`
            : `<span class="uyw_price_now">${p.list_price.toFixed(2)} KD</span>`;

        return `
<a href="${p.website_url}" class="uyw_card" title="${p.name}">
    <div class="uyw_img_box">
        <img src="/web/image/product.template/${p.id}/image_512"
             loading="lazy" alt="${p.name}"
             onerror="this.onerror=null;this.style.visibility='hidden'">
    </div>
    <div class="uyw_details">
        <div class="uyw_name">${p.name}</div>
        <div class="uyw_price_row">${priceHTML}</div>
        <div class="uyw_stars">${buildStars(p.rating_avg)}<span>(${p.rating_count||0})</span></div>
        <div class="uyw_ticker"><ul class="uyw_ticker_list">${buildTicker(saveVal, isRTL)}</ul></div>
        <div class="uyw_card_footer">
            <div class="uyw_badges">
                <span class="uyw_badge_exp">${isRTL ? 'إكسبريس' : 'EXPRESS'}</span>
                <span class="uyw_badge_taly">
                    <span class="uyw_taly_icon"><span></span><span></span></span>
                    ${isRTL ? 'تالي' : 'taly'}
                </span>
            </div>
            <div class="uyw_stock ${canBuy ? 'in' : 'out'}">
                ${inStock ? `<i class="fa fa-cubes"></i> ${Math.floor(p.qty_available)} ` : ''}
                ${canBuy ? (isRTL ? 'متوفر' : 'Available') : (isRTL ? 'نفذ' : 'Out')}
            </div>
        </div>
    </div>
</a>`;
    }

    async function fetchPublic(limit, offset) {
        const res = await fetch('/uellow/products', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                jsonrpc: '2.0', method: 'call', id: Date.now(),
                params:  { limit, offset },
            }),
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json = await res.json();
        if (json.error) throw new Error(json.error.data?.message || 'RPC error');
        return json.result?.products || [];
    }

    function appendProducts(grid, products, isRTL) {
        const wrapper = document.createElement('div');
        wrapper.innerHTML = products.map(p => renderCard(p, isRTL)).join('');
        const frag = document.createDocumentFragment();
        while (wrapper.firstChild) frag.appendChild(wrapper.firstChild);
        grid.appendChild(frag);
    }

    function initBlock(section) {
        if (section.dataset.uywInit) return;
        section.dataset.uywInit = '1';

        const grid    = section.querySelector('#uyw_grid');
        const spinner = section.querySelector('#uyw_spinner');
        const btnMore = section.querySelector('#uyw_btn_more');
        const titleEl = section.querySelector('.uyw_title');
        const viewAll = section.querySelector('.uyw_view_all');

        if (!grid) return;

        const { isRTL } = detectEnv();

        if (titleEl) titleEl.textContent = isRTL ? 'قد يعجبك أيضاً' : 'You May Like';
        if (btnMore) btnMore.textContent = isRTL ? 'عرض المزيد'     : 'Load More';
        if (viewAll) viewAll.textContent = isRTL ? 'المزيد'          : 'More';

        const show = (el) => { if (el) el.style.display = 'inline-block'; };
        const hide = (el) => { if (el) el.style.display = 'none'; };

        // offset يتتبع كم منتج حُمّل
        let currentOffset = 0;
        let busy = false;

        async function loadNext(limit) {
            if (busy) return;
            busy = true;
            show(spinner);
            hide(btnMore);

            try {
                const products = await fetchPublic(limit, currentOffset);

                if (!products.length) {
                    // انتهت المنتجات
                    hide(spinner);
                    hide(btnMore);
                    busy = false;
                    return;
                }

                appendProducts(grid, products, isRTL);
                currentOffset += products.length;

            } catch (err) {
                console.warn('[Uellow YML]', err.message);
            }

            busy = false;
            hide(spinner);

            // قرر ماذا تعرض بعد التحميل
            if (currentOffset >= AUTO_ROUNDS * PAGE_SIZE) {
                // وصلنا للـ AUTO_ROUNDS – أظهر زر Load More
                show(btnMore);
            } else {
                // لم نصل بعد – أظهر زر لتحميل الدفعة التالية
                show(btnMore);
            }
        }

        // زر Load More يحمّل MANUAL_BATCH منتج
        if (btnMore) {
            btnMore.addEventListener('click', () => loadNext(MANUAL_BATCH));
        }

        // ── Scroll trigger: كل ما اقترب المستخدم من الأسفل حمّل تلقائياً ──
        // يعمل فقط خلال الـ AUTO_ROUNDS الأولى
        function onScroll() {
            if (busy) return;
            if (currentOffset >= AUTO_ROUNDS * PAGE_SIZE) return;
            const scrollBottom = window.innerHeight + window.scrollY;
            const pageHeight   = document.documentElement.scrollHeight;
            if (scrollBottom >= pageHeight - 500) {
                loadNext(PAGE_SIZE);
            }
        }
        window.addEventListener('scroll', onScroll, { passive: true });

        // حمّل أول دفعة فوراً
        loadNext(PAGE_SIZE);
    }

    function bootstrap() {
        // ✅ امسح الـ uywInit عند كل تشغيل حتى لو كان JS قديم شغّله من قبل
        document.querySelectorAll('.s_uellow_you_may_like').forEach(s => {
            delete s.dataset.uywInit;
        });
        document.querySelectorAll('.s_uellow_you_may_like').forEach(initBlock);
    }

    // امسح الـ flag عند كل page load (يحل مشكلة الـ cache)
    document.querySelectorAll('.s_uellow_you_may_like').forEach(s => {
        delete s.dataset.uywInit;
        if (s.querySelector('#uyw_grid')) s.querySelector('#uyw_grid').innerHTML = '';
    });

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', bootstrap);
    } else {
        bootstrap();
    }
    document.addEventListener('snippets_loaded', bootstrap);

})();
