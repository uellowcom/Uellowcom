/**
 * Uellow Loyalty Brain — loyalty.js
 * Float badge + side panel + checkout redeem widget + portal page
 */

(function () {
    'use strict';

    function post(url, params) {
        return fetch(url, {
            method:  'POST',
            headers: {'Content-Type': 'application/json'},
            body:    JSON.stringify({jsonrpc: '2.0', method: 'call', id: 1, params}),
        }).then(r => r.json()).then(d => d.result || {});
    }

    const LEVEL_COLORS = {
        starter:  '#888',
        silver:   '#888780',
        gold:     '#F5C320',
        platinum: '#534AB7',
        elite:    '#1D9E75',
    };

    let accountData = null;

    // ── Init ──────────────────────────────────────────────────────────────────

    async function init() {
        const path = location.pathname;

        // Skip backend and auth pages
        if (path.startsWith('/odoo') || path.startsWith('/web') || path.startsWith('/reviewer')) return;

        // Portal page
        if (path === '/loyalty') {
            await initPortalPage();
            return;
        }

        // Load balance
        const data = await post('/loyalty/balance', {});
        if (!data.logged_in) return;

        accountData = data;

        // Show float badge on all public pages
        buildFloatBadge(data);
        buildPanel(data);

        // Inject checkout widget on cart/payment pages
        if (path.includes('/shop/cart') || path.includes('/shop/payment') || path.includes('/checkout')) {
            injectCheckoutWidget(data);
        }
    }

    // ── Float Badge ───────────────────────────────────────────────────────────

    function buildFloatBadge(data) {
        const badge = document.createElement('div');
        badge.id    = 'loyalty-float-badge';
        badge.setAttribute('role', 'button');
        badge.setAttribute('aria-label', 'نقاط الولاء');
        badge.innerHTML = `
            <span style="font-size:16px">⭐</span>
            <span id="loyalty-float-points">${data.points.toLocaleString()}</span>
            <span style="font-size:9px;opacity:.8">نقطة</span>`;
        badge.addEventListener('click', togglePanel);
        document.body.appendChild(badge);
    }

    // ── Side Panel ────────────────────────────────────────────────────────────

    function buildPanel(data) {
        const panel = document.createElement('div');
        panel.id    = 'loyalty-panel';
        panel.className = 'closed';

        const levelColor = LEVEL_COLORS[data.level] || '#F5C320';
        const progressPct = data.progress || 0;

        panel.innerHTML = `
<div class="lp-header">
    <button class="lp-close" onclick="window._loyaltyClose()" aria-label="إغلاق">×</button>
    <div class="lp-level-badge" style="background:${levelColor};color:#fff">
        ${data.level_label}
    </div>
    <div class="lp-points">${data.points.toLocaleString()}</div>
    <div class="lp-points-label">نقطة · قيمتها ${data.kd_value} KD</div>
</div>

<div class="lp-progress-wrap">
    <div class="lp-progress-label">
        <span>التقدم للمستوى القادم</span>
        <span>${data.to_next > 0 ? data.to_next.toLocaleString() + ' نقطة باقية' : 'أعلى مستوى 🎉'}</span>
    </div>
    <div class="lp-progress-bar">
        <div class="lp-progress-fill" style="width:${progressPct}%;background:${levelColor}"></div>
    </div>
</div>

${data.level_perks && data.level_perks.length ? `
<div class="lp-section">
    <div class="lp-section-title">مزايا مستواك الحالي</div>
    ${data.level_perks.map(p => `<div class="lp-perk">${p}</div>`).join('')}
</div>` : ''}

<div class="lp-section">
    <div class="lp-section-title">كيف تكسب نقاطاً؟</div>
    <div class="lp-earn-row"><span>كل 1 KD مشتريات</span><span class="lp-earn-pts">+10 نقطة</span></div>
    <div class="lp-earn-row"><span>كتابة مراجعة</span><span class="lp-earn-pts">+50 نقطة</span></div>
    <div class="lp-earn-row"><span>دعوة صديق</span><span class="lp-earn-pts">+200 نقطة</span></div>
    <div class="lp-earn-row"><span>استخدام ريفيور</span><span class="lp-earn-pts">+25 نقطة</span></div>
    <div class="lp-earn-row"><span>عيد الميلاد 🎂</span><span class="lp-earn-pts">+100 نقطة</span></div>
</div>

<div class="lp-redeem-wrap">
    <div class="lp-section-title">استبدل نقاطك</div>
    <div class="lp-redeem-info">
        1000 نقطة = 1 KD خصم على طلبك
        <br>رصيدك الحالي يساوي <strong>${data.kd_value} KD</strong>
    </div>
    <div class="lp-redeem-input">
        <input id="lp-redeem-pts" type="number" min="100" max="${data.points}"
               placeholder="عدد النقاط" step="100">
        <button class="lp-redeem-btn" onclick="window._loyaltyRedeem()">استبدل</button>
    </div>
    <div id="lp-redeem-msg" style="font-size:11px;margin-top:6px;color:#1D9E75;display:none"></div>
</div>

<div style="padding:10px 16px 14px">
    <a href="/loyalty" style="font-size:11px;color:#534AB7;text-decoration:none">
        عرض كل المعاملات ←
    </a>
</div>`;

        document.body.appendChild(panel);
    }

    function togglePanel() {
        const panel = document.getElementById('loyalty-panel');
        if (panel) panel.classList.toggle('closed');
    }

    window._loyaltyClose = function() {
        const panel = document.getElementById('loyalty-panel');
        if (panel) panel.classList.add('closed');
    };

    window._loyaltyRedeem = async function() {
        const input  = document.getElementById('lp-redeem-pts');
        const points = parseInt(input ? input.value : 0);
        const msg    = document.getElementById('lp-redeem-msg');

        if (!points || points < 100) {
            if (msg) { msg.textContent = 'الحد الأدنى 100 نقطة'; msg.style.display = 'block'; msg.style.color = '#E24B4A'; }
            return;
        }

        const data = await post('/loyalty/redeem', {points});

        if (data.success) {
            if (msg) {
                msg.textContent = `تم! وفّرت ${data.kd_saved} KD ✓`;
                msg.style.display = 'block';
                msg.style.color   = '#1D9E75';
            }
            // Update badge
            const badge = document.getElementById('loyalty-float-points');
            if (badge) badge.textContent = data.new_balance.toLocaleString();
            // Reload page to reflect discount
            setTimeout(() => location.reload(), 1500);
        } else {
            if (msg) {
                msg.textContent = data.error || 'حدث خطأ';
                msg.style.display = 'block';
                msg.style.color   = '#E24B4A';
            }
        }
    };

    // ── Checkout Widget ───────────────────────────────────────────────────────

    function injectCheckoutWidget(data) {
        if (!data.points || data.points < 100) return;

        const widget = document.createElement('div');
        widget.id    = 'loyalty-checkout-widget';
        widget.innerHTML = `
<div class="lcy-title">
    ⭐ عندك ${data.points.toLocaleString()} نقطة (${data.kd_value} KD)
</div>
<div style="font-size:12px;color:#888;margin-bottom:8px">
    استخدم نقاطك للحصول على خصم على هذا الطلب
</div>
<div style="display:flex;gap:7px;align-items:center">
    <input id="lcy-pts-input" type="number" min="100" max="${data.points}" step="100"
           placeholder="عدد النقاط"
           style="flex:1;border:0.5px solid rgba(0,0,0,.12);border-radius:8px;padding:8px 10px;font-size:12px;font-family:inherit;outline:none">
    <span style="font-size:12px;color:#888" id="lcy-kd-preview">= 0 KD</span>
    <button onclick="window._loyaltyApplyCheckout()"
            style="background:#F5C320;border:none;border-radius:8px;padding:8px 14px;font-size:12px;font-weight:700;cursor:pointer;font-family:inherit;color:#1A1A1A;white-space:nowrap">
        طبّق
    </button>
</div>`;

        // Update KD preview on input
        const ptsInput = widget.querySelector('#lcy-pts-input');
        const preview  = widget.querySelector('#lcy-kd-preview');
        if (ptsInput && preview) {
            ptsInput.addEventListener('input', () => {
                const kd = Math.round(parseInt(ptsInput.value || 0) * 0.001 * 1000) / 1000;
                preview.textContent = `= ${kd.toFixed(3)} KD`;
            });
        }

        // Find anchor in cart/checkout page
        const anchor = document.querySelector(
            '.o_loyalty_card, .js_cart_lines, #cart_total, ' +
            '.o_website_sale_coupon, #order_total, .oe_cart'
        );
        if (anchor) {
            anchor.parentNode.insertBefore(widget, anchor);
        }
    }

    window._loyaltyApplyCheckout = async function() {
        const input  = document.getElementById('lcy-pts-input');
        const points = parseInt(input ? input.value : 0);
        if (!points) return;
        const data = await post('/loyalty/redeem', {points});
        if (data.success) {
            alert(`تم تطبيق الخصم — وفّرت ${data.kd_saved} KD ✓`);
            location.reload();
        } else {
            alert(data.error || 'حدث خطأ');
        }
    };

    // ── Portal Page ───────────────────────────────────────────────────────────

    async function initPortalPage() {
        const root = document.getElementById('loyalty-portal-root');
        if (!root) return;

        root.innerHTML = `<div style="max-width:600px;margin:0 auto;padding:20px 16px">
            <div style="text-align:center;padding:30px;color:#888">جاري التحميل...</div>
        </div>`;

        const data = await post('/loyalty/transactions', {limit: 30});
        if (!data.account) {
            root.innerHTML = `<div style="text-align:center;padding:40px;color:#888">
                <div style="font-size:32px;margin-bottom:12px">⭐</div>
                <div>سجّل دخولك لرؤية نقاطك</div>
            </div>`;
            return;
        }

        const acc  = data.account;
        const txns = data.transactions || [];
        const levelColor = LEVEL_COLORS[acc.level] || '#F5C320';

        root.innerHTML = `
<div style="max-width:600px;margin:0 auto;padding:20px 16px;direction:rtl;font-family:inherit">

    <!-- Header -->
    <div style="background:#F5C320;border-radius:14px;padding:20px;margin-bottom:16px;text-align:center">
        <div style="display:inline-block;background:${levelColor};color:#fff;padding:4px 12px;border-radius:6px;font-size:11px;font-weight:700;margin-bottom:8px">
            ${acc.level_label}
        </div>
        <div style="font-size:36px;font-weight:800;color:#1A1A1A;line-height:1">${acc.points.toLocaleString()}</div>
        <div style="font-size:13px;color:#854F0B;margin-top:4px">نقطة · قيمتها ${acc.kd_value} KD</div>
    </div>

    <!-- Progress -->
    <div style="background:#fff;border:0.5px solid rgba(0,0,0,.08);border-radius:12px;padding:14px;margin-bottom:12px">
        <div style="display:flex;justify-content:space-between;font-size:12px;color:#888;margin-bottom:7px">
            <span>التقدم للمستوى القادم</span>
            <span>${acc.to_next > 0 ? acc.to_next.toLocaleString() + ' نقطة' : '🎉 أعلى مستوى'}</span>
        </div>
        <div style="height:8px;background:#F0EFE8;border-radius:4px;overflow:hidden">
            <div style="width:${acc.progress}%;height:100%;background:${levelColor};border-radius:4px;transition:width .5s"></div>
        </div>
        ${acc.level_perks && acc.level_perks.length ? `
        <div style="margin-top:10px">
            ${acc.level_perks.map(p => `<div style="font-size:11px;color:#1D9E75;padding:2px 0">✓ ${p}</div>`).join('')}
        </div>` : ''}
    </div>

    <!-- Stats -->
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:16px">
        <div style="background:#fff;border:0.5px solid rgba(0,0,0,.08);border-radius:10px;padding:12px;text-align:center">
            <div style="font-size:18px;font-weight:700;color:#1A1A1A">${acc.points.toLocaleString()}</div>
            <div style="font-size:10px;color:#888;margin-top:2px">الرصيد</div>
        </div>
        <div style="background:#fff;border:0.5px solid rgba(0,0,0,.08);border-radius:10px;padding:12px;text-align:center">
            <div style="font-size:18px;font-weight:700;color:#1D9E75">${acc.earned.toLocaleString()}</div>
            <div style="font-size:10px;color:#888;margin-top:2px">مكتسب</div>
        </div>
        <div style="background:#fff;border:0.5px solid rgba(0,0,0,.08);border-radius:10px;padding:12px;text-align:center">
            <div style="font-size:18px;font-weight:700;color:#534AB7">${acc.spent.toLocaleString()}</div>
            <div style="font-size:10px;color:#888;margin-top:2px">مستخدم</div>
        </div>
    </div>

    <!-- Transactions -->
    <div style="background:#fff;border:0.5px solid rgba(0,0,0,.08);border-radius:12px;overflow:hidden">
        <div style="padding:12px 16px;border-bottom:0.5px solid rgba(0,0,0,.06);font-size:13px;font-weight:700;color:#1A1A1A">
            سجل النقاط
        </div>
        ${txns.length ? txns.map(t => `
        <div style="display:flex;justify-content:space-between;align-items:center;padding:10px 16px;border-bottom:0.5px solid rgba(0,0,0,.04);font-size:12px">
            <div>
                <div style="color:#1A1A1A;font-weight:500">${t.reason || t.type}</div>
                <div style="color:#aaa;font-size:10px;margin-top:1px">${t.date}</div>
            </div>
            <div style="font-size:14px;font-weight:700;color:${t.points > 0 ? '#1D9E75' : '#E24B4A'}">
                ${t.points > 0 ? '+' : ''}${t.points.toLocaleString()}
            </div>
        </div>`).join('') : `
        <div style="padding:24px;text-align:center;color:#aaa;font-size:12px">
            لا توجد معاملات بعد — ابدأ التسوق لكسب نقاط!
        </div>`}
    </div>

</div>`;
    }

    // ── Boot ──────────────────────────────────────────────────────────────────

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
