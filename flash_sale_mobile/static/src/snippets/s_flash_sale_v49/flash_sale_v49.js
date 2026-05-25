/* Flash Sale Mobile START */
(function () {
    "use strict";

    const i18n = {
        ar: { currency: "د.ك", save: "وفر",  more: "المزيد", title: "⚡ عروض خاطفة" },
        en: { currency: "KD",  save: "Save", more: "More",   title: "⚡ Flash Deals"  },
    };

    function getLang() {
        const dir  = document.documentElement.dir;
        const path = window.location.pathname;
        const lang = document.documentElement.lang || "";
        return (dir === "rtl" || path.startsWith("/ar") || lang.startsWith("ar")) ? "ar" : "en";
    }

    function runTimer(wrapper) {
        if (wrapper._timerRunning) return;
        wrapper._timerRunning = true;
        const cycle = 7 * 24 * 60 * 60 * 1000;
        const d = wrapper.querySelector("#v49_d");
        const h = wrapper.querySelector("#v49_h");
        const m = wrapper.querySelector("#v49_m");
        const s = wrapper.querySelector("#v49_s");
        if (!d) return;
        const tick = () => {
            const dist = cycle - (Date.now() % cycle);
            d.textContent = String(Math.floor(dist / 86400000)).padStart(2,"0");
            h.textContent = String(Math.floor((dist % 86400000) / 3600000)).padStart(2,"0");
            m.textContent = String(Math.floor((dist % 3600000) / 60000)).padStart(2,"0");
            s.textContent = String(Math.floor((dist % 60000) / 1000)).padStart(2,"0");
        };
        setInterval(tick, 1000);
        tick();
    }

    function startSwiper(wrapper, lang) {
        const el = wrapper.querySelector(".uellowV49Swiper");
        if (!el) return;
        if (el.swiper) el.swiper.destroy(true, true);
        new Swiper(el, {
            slidesPerView  : 2.3,
            spaceBetween   : 8,
            rtl            : lang === "ar",
            observer       : true,
            observeParents : true,
            touchRatio     : 1,
            touchAngle     : 45,
            grabCursor     : true,
            simulateTouch  : true,
        });
    }

    function render(wrapper, products, lang) {
        const t    = i18n[lang];
        const feed = wrapper.querySelector(".swiper-wrapper");
        if (!feed) return;
        feed.innerHTML = "";
        products.forEach((p) => {
            let badge = "", oldP = "";
            const np = parseFloat(p.list_price) || 0;
            const op = parseFloat(p.compare_list_price) || 0;
            if (op > np && op > 0) {
                const diff = (op - np).toFixed(3);
                const pct  = Math.round(((op - np) / op) * 100);
                oldP  = `<span class="v49-p-old">${op.toFixed(3)}</span>`;
                badge = `<div class="v49-save-badge">${t.save} ${diff} ${t.currency} (${pct}%)</div>`;
            }
            const slide = document.createElement("div");
            slide.className = "swiper-slide";
            slide.innerHTML = `
                <a href="${p.website_url}" class="v49-card">
                    <div class="v49-img-box">
                        <img src="/web/image/product.template/${p.id}/image_512"
                             loading="lazy"
                             onerror="this.src='/web/static/img/placeholder.png'">
                    </div>
                    <div class="v49-p-title">${p.name}</div>
                    <div class="v49-price-row">
                        <span class="v49-p-new">${np.toFixed(3)} ${t.currency}</span>
                        ${oldP}
                    </div>
                    ${badge}
                </a>`;
            feed.appendChild(slide);
        });
        setTimeout(() => startSwiper(wrapper, lang), 50);
    }

    async function fetchProducts() {
        try {
            const res = await fetch("/flash_sale_mobile/products", {
                method : "POST",
                headers: { "Content-Type": "application/json" },
                body   : JSON.stringify({
                    jsonrpc: "2.0", method: "call", id: 1,
                    params : { category_id: 871, limit: 20 },
                }),
            });
            const json = await res.json();
            if (json.result?.success && json.result.products?.length > 0) {
                return json.result.products;
            }
        } catch(e) {}
        return null;
    }

    async function initWidget(wrapper) {
        const lang = getLang();
        const t    = i18n[lang];

        // ✅ أزل فقط data-invisible و o_snippet_*_invisible
        // لا تزيل d-none و d-md-none لأنها تتحكم في موبايل/ديسكتوب
        wrapper.removeAttribute("data-invisible");
        wrapper.classList.remove(
            "o_snippet_desktop_invisible",
            "o_snippet_mobile_invisible"
        );

        // ✅ إذا كان hidden بـ data-invisible فقط — أظهره
        // أما إذا كان hidden بـ d-none (Odoo visibility) — احترم ذلك
        const isHiddenByOdoo = wrapper.classList.contains("o_snippet_desktop_invisible") ||
                               wrapper.classList.contains("o_snippet_mobile_invisible");
        if (!isHiddenByOdoo) {
            wrapper.style.removeProperty("display");
            wrapper.style.removeProperty("visibility");
        }

        const titleEl = wrapper.querySelector(".v49-title-text");
        const moreEl  = wrapper.querySelector(".v49-btn-more");
        if (titleEl) titleEl.textContent = t.title;
        if (moreEl)  moreEl.textContent  = t.more;

        // ✅ التايمر والـ Swiper دائماً
        runTimer(wrapper);
        setTimeout(() => startSwiper(wrapper, lang), 100);

        const feed = wrapper.querySelector(".swiper-wrapper");
        const hasRealSlides = feed &&
            feed.querySelectorAll(".swiper-slide:not(.v49-loader)").length > 0;
        if (hasRealSlides) return;

        const products = await fetchProducts();
        if (!products || products.length === 0) {
            const area = wrapper.querySelector(".v49-product-area");
            if (area) area.style.display = "none";
            return;
        }
        render(wrapper, products, lang);
    }

    function boot() {
        document.querySelectorAll(".uellow-v49-wrapper").forEach(w => initWidget(w));
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", boot);
    } else {
        boot();
    }
    window.addEventListener("load", boot);

})();
/* Flash Sale Mobile END */
