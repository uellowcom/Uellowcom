/**
 * Taly Product Widget JS
 * Updates installment breakdown text when product price changes
 * (e.g. variant selection)
 */
document.addEventListener('DOMContentLoaded', function () {
    'use strict';

    function updateTalyBanners() {
        document.querySelectorAll('.taly-product-widget').forEach(function (widget) {
            const price = parseFloat(widget.dataset.price) || 0;
            const instType = parseInt(widget.dataset.installmentType) || 3;
            const lang = widget.dataset.lang || 'ar';

            if (price <= 0) return;

            const downPayment = (price / instType).toFixed(3);
            const countEl = widget.querySelector('.taly-installments-count');
            const payEl = widget.querySelector('.taly-first-payment');
            if (countEl) countEl.textContent = instType;
            if (payEl) payEl.textContent = downPayment + ' ' + (document.documentElement.lang === 'ar' ? 'د.ك' : 'KWD');

            // Update iframe src if modal open
            const iframe = document.querySelector('#talyWidgetModal iframe');
            if (iframe) {
                iframe.src = `https://promo.taly.io/installment-widget?price=${price}&installmenttype=${instType}&lang=${lang}`;
            }
        });
    }

    // Initial run
    updateTalyBanners();

    // Re-run on variant change (Odoo fires this event)
    document.addEventListener('website_sale.updateCart', updateTalyBanners);
    document.addEventListener('change', function (e) {
        if (e.target && (e.target.name === 'product_id' || e.target.classList.contains('product_id'))) {
            setTimeout(updateTalyBanners, 300);
        }
    });
});
