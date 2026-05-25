/** @odoo-module **/
import publicWidget from "@web/legacy/js/public/public_widget";

const FlashSaleWidget = publicWidget.Widget.extend({
    selector: '.uellow-flash-v30-root',

    start() {
        this._super(...arguments);
        this._loadFlashDeals();
        this._startTimer();
    },

    _isRTL() {
        return document.documentElement.dir === 'rtl' ||
               document.documentElement.lang.startsWith('ar');
    },

    _updateLabels(isRTL) {
        const t = this.el.querySelector('.v30-flash-title');
        const b = this.el.querySelector('.v30-btn');
        const e = this.el.querySelector('.v30-ends-in');
        if (t) t.innerText = isRTL ? 'عروض فلاش' : 'Flash Deals';
        if (b) b.innerText = isRTL ? 'عرض الكل'  : 'View All';
        if (e) e.innerText = isRTL ? 'تنتهي خلال': 'Ends In';
    },

    async _loadFlashDeals() {
        const container = this.el.querySelector('#v30_flash_list');
        if (!container) return;

        const isRTL       = this._isRTL();
        const currentLang = isRTL ? 'ar_001' : 'en_US';
        const dir         = isRTL ? 'rtl' : 'ltr';

        this._updateLabels(isRTL);

        try {
            const params = new URLSearchParams({ categ_id: 871, limit: 18, lang: currentLang });
            const response = await fetch(`/flash_sale/products?${params}`);
            const data = await response.json();
            const products = data.result || [];

            if (products.length > 0) {
                container.innerHTML = products.map(p => {
                    let priceRow = `<span class="v30-price-now">${p.list_price.toFixed(2)} KD</span>`;
                    // البادج الافتراضي لو ما في خصم
                    let badge = '';

                    if (p.compare_list_price > p.list_price) {
                        const perc  = Math.round(((p.compare_list_price - p.list_price) / p.compare_list_price) * 100);
                        const saved = (p.compare_list_price - p.list_price).toFixed(2);
                        priceRow += `
                            <span class="v30-f-price-old">${p.compare_list_price.toFixed(2)}</span>
                            <span class="v30-f-off">-${perc}%</span>`;
                        // pill صغير أبيض يشبه الصورة
                        badge = isRTL
                            ? `<span class="v30-f-badge">وفر ${saved} د.ك</span>`
                            : `<span class="v30-f-badge">Save ${saved} KD</span>`;
                    }

                    const align = isRTL ? 'text-right' : 'text-left';
                    return `
                        <div class="swiper-slide">
                            <a href="${p.website_url}" class="v30-f-card ${align}">
                                <div class="v30-f-img">
                                    ${badge}
                                    <img src="/web/image/product.template/${p.id}/image_512" loading="lazy" alt="${p.name}">
                                </div>
                                <div class="v30-product-name-single">${p.name}</div>
                                <div class="v30-price-row">${priceRow}</div>
                            </a>
                        </div>`;
                }).join('');

                new Swiper('.swiperV30Flash', {
                    slidesPerView: 2,
                    spaceBetween: 12,
                    dir: dir,
                    navigation: { nextEl: '.swiper-button-next', prevEl: '.swiper-button-prev' },
                    breakpoints: {
                        640:  { slidesPerView: 3 },
                        992:  { slidesPerView: 5 },
                        1200: { slidesPerView: 6 },
                    },
                });
            } else {
                const msg = isRTL ? 'لا توجد عروض حالياً.' : 'No Deals Currently.';
                container.innerHTML = `<div class="text-center w-100 py-3 text-muted">${msg}</div>`;
            }
        } catch (e) {
            console.error('[FlashSaleDesktop] Error:', e);
        }
    },

    _startTimer() {
        const tick = () => {
            const now = new Date();
            const h = this.el.querySelector('#v30_h');
            const m = this.el.querySelector('#v30_m');
            const s = this.el.querySelector('#v30_s');
            if (h) {
                h.innerText = String(23 - now.getHours()).padStart(2, '0');
                m.innerText = String(59 - now.getMinutes()).padStart(2, '0');
                s.innerText = String(59 - now.getSeconds()).padStart(2, '0');
            }
        };
        tick();
        this._timerInterval = setInterval(tick, 1000);
    },

    destroy() {
        if (this._timerInterval) clearInterval(this._timerInterval);
        this._super(...arguments);
    },
});

publicWidget.registry.FlashSaleDesktop = FlashSaleWidget;
export default FlashSaleWidget;
