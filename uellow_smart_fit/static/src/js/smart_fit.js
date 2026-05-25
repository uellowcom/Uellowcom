/**
 * Uellow Smart Fit Engine — smart_fit.js
 * Injects size recommendation widget on product pages
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

    function getProductId() {
        const match = location.pathname.match(/\/shop\/product\/[^/]+-?(\d+)\/?$/);
        if (match) return match[1];
        const input = document.querySelector('input[name="product_id"]');
        if (input) return input.value;
        const el = document.querySelector('[data-product-id]');
        if (el) return el.dataset.productId;
        return null;
    }

    // ── Render size grid with AI recommendations ──────────────────────────────

    function injectFitWidget(data) {
        if (!data || !data.has_sizes) return;

        // Find size selector on page — Theme Prime uses various selectors
        const sizeContainers = document.querySelectorAll(
            '.css_attribute_color, .variant_attribute, [data-attribute_id], ' +
            '.o_wsale_product_attributes, .js_attribute_value'
        );

        if (!sizeContainers.length) return;

        // Find the size attribute container specifically
        let sizeContainer = null;
        sizeContainers.forEach(el => {
            const label = el.closest('[data-attribute_name], .attribute_name, label');
            const text  = (el.textContent || '').toLowerCase();
            if (text.includes('size') || text.includes('مقاس') || text.includes('حجم')) {
                sizeContainer = el;
            }
        });

        // Create or get widget container
        let widget = document.getElementById('smart-fit-widget');
        if (!widget) {
            widget = document.createElement('div');
            widget.id = 'smart-fit-widget';

            // Insert after size selector area
            const anchor = sizeContainer ||
                document.querySelector('#add_to_cart, .a-buy, .css_attribute_color, .js_product');
            if (anchor) {
                anchor.parentNode.insertBefore(widget, anchor.nextSibling);
            }
        }

        if (!widget.parentNode) return;

        if (data.has_profile && data.results) {
            renderFitResults(widget, data);
        } else if (!data.has_profile) {
            renderProfilePrompt(widget, data.sizes || []);
        }
    }

    // ── Render full analysis ──────────────────────────────────────────────────

    function renderFitResults(container, data) {
        const results    = data.results || [];
        const recommended = results.find(r => r.recommended);

        const colorIcon = {green: '✓', yellow: '~', orange: '!', red: '✗'};

        container.innerHTML = `
<div style="border-top:0.5px solid rgba(0,0,0,.08);padding-top:14px;margin-top:4px">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px">
        <div style="font-size:13px;font-weight:600;color:#1A1A1A;display:flex;align-items:center;gap:6px">
            📏 Smart Fit
            <span style="font-size:10px;background:#F5C320;color:#1A1A1A;padding:2px 6px;border-radius:4px;font-weight:700">AI</span>
        </div>
        <button class="sf-toggle-btn" onclick="window._sfToggleDetails(this)">
            تفاصيل ▾
        </button>
    </div>

    ${recommended ? `
    <div class="sf-verdict ${recommended.fit_color}">
        <span class="sf-verdict-icon">${colorIcon[recommended.fit_color] || '•'}</span>
        <div>
            <div class="sf-verdict-text">مقاس ${recommended.size} — ${recommended.fit_label}</div>
            ${recommended.issues.length ? `<div style="font-size:10px;opacity:.8;margin-top:2px">${recommended.issues.join(' · ')}</div>` : ''}
        </div>
    </div>` : ''}

    <div class="sf-size-grid">
        ${results.map(r => `
        <button class="sf-size-btn fit-${r.fit_color}${r.recommended ? ' recommended' : ''}"
                title="${r.fit_label}${r.issues.length ? ': ' + r.issues.join(', ') : ''}"
                onclick="window._sfSelectSize('${r.size}')">
            ${r.size}
        </button>`).join('')}
    </div>

    <div id="sf-details" style="display:none">
        ${recommended ? renderDetails(recommended) : ''}
    </div>

    <button class="sf-toggle-btn" style="font-size:11px;color:#534AB7"
            onclick="window._sfEditProfile()">
        ✎ تعديل مقاساتي
    </button>
</div>`;
    }

    function renderDetails(result) {
        const details = result.details || {};
        const bars = [];

        Object.entries(details).forEach(([key, val]) => {
            if (!val || val.status === 'checked') return;
            const labels  = {chest:'الصدر', shoulder:'الكتف', waist:'الوسط', hip:'الورك', shoe:'الحذاء'};
            const label   = labels[key] || key;
            const pct     = val.status === 'perfect' ? 95 : val.status === 'ok' ? 75 : val.status === 'loose' ? 55 : 35;
            const color   = pct >= 85 ? 'green' : pct >= 65 ? '' : pct >= 45 ? 'orange' : 'red';
            const diffTxt = val.diff ? (val.diff > 0 ? `+${val.diff}cm` : `${val.diff}cm`) : '';
            const statusAr = {perfect:'مناسب', ok:'جيد', loose:'واسع', tight:'ضيق', close:'قريب', far:'بعيد'}[val.status] || val.status;

            bars.push(`
<div class="sf-detail-row">
    <span class="sf-detail-label">${label}</span>
    <div class="sf-detail-bar">
        <div class="sf-detail-fill ${color}" style="width:${pct}%"></div>
    </div>
    <span class="sf-detail-value">${statusAr}${diffTxt ? ' ' + diffTxt : ''}</span>
</div>`);
        });

        return bars.length ? `<div class="sf-fit-card" style="margin-top:8px">${bars.join('')}</div>` : '';
    }

    // ── Render profile prompt ─────────────────────────────────────────────────

    function renderProfilePrompt(container, sizes) {
        container.innerHTML = `
<div style="border-top:0.5px solid rgba(0,0,0,.08);padding-top:14px;margin-top:4px">
    <div style="font-size:13px;font-weight:600;color:#1A1A1A;margin-bottom:8px;display:flex;align-items:center;gap:6px">
        📏 Smart Fit
        <span style="font-size:10px;background:#F5C320;color:#1A1A1A;padding:2px 6px;border-radius:4px;font-weight:700">AI</span>
    </div>

    <div style="background:#F9F8F5;border-radius:10px;padding:12px;margin-bottom:10px">
        <div style="font-size:12px;color:#888;margin-bottom:10px">
            أدخل مقاساتك للحصول على توصية مقاس دقيقة
        </div>
        <div class="sf-input-grid">
            <div class="sf-input-group">
                <label>الصدر (cm)</label>
                <input id="sf-chest" type="number" placeholder="مثال: 96">
            </div>
            <div class="sf-input-group">
                <label>الوسط (cm)</label>
                <input id="sf-waist" type="number" placeholder="مثال: 80">
            </div>
            <div class="sf-input-group">
                <label>الكتف (cm)</label>
                <input id="sf-shoulder" type="number" placeholder="مثال: 44">
            </div>
            <div class="sf-input-group">
                <label>مقاس الحذاء EU</label>
                <input id="sf-shoe" type="number" placeholder="مثال: 42">
            </div>
        </div>
        <div class="sf-input-group" style="margin-bottom:10px">
            <label>تفضيل القصة</label>
            <select id="sf-fit-pref">
                <option value="regular">Regular — عادي</option>
                <option value="slim">Slim — ضيق شوي</option>
                <option value="loose">Loose — واسع شوي</option>
            </select>
        </div>
        <button class="sf-save-btn" onclick="window._sfQuickAnalyze()">
            احسب مقاسي المناسب
        </button>
    </div>
</div>`;
    }

    // ── Actions ───────────────────────────────────────────────────────────────

    window._sfToggleDetails = function(btn) {
        const details = document.getElementById('sf-details');
        if (!details) return;
        const isOpen = details.style.display !== 'none';
        details.style.display = isOpen ? 'none' : 'block';
        btn.textContent = isOpen ? 'تفاصيل ▾' : 'إخفاء ▴';
    };

    window._sfSelectSize = function(size) {
        // Find size option in page and click it
        const options = document.querySelectorAll(
            '.js_attribute_value input, .css_attribute_color input, ' +
            '[data-value_name], .attribute_value_ids'
        );
        options.forEach(opt => {
            const label = opt.closest('label, .attribute_value');
            if (label && label.textContent.trim() === size) {
                opt.click();
                label.click();
            }
        });
    };

    window._sfQuickAnalyze = async function() {
        const pid      = getProductId();
        const chest    = parseFloat(document.getElementById('sf-chest')?.value || 0);
        const waist    = parseFloat(document.getElementById('sf-waist')?.value || 0);
        const shoulder = parseFloat(document.getElementById('sf-shoulder')?.value || 0);
        const shoe     = parseFloat(document.getElementById('sf-shoe')?.value || 0);
        const pref     = document.getElementById('sf-fit-pref')?.value || 'regular';

        if (!chest && !shoe) {
            alert('أدخل مقاساتك أولاً');
            return;
        }

        const btn = document.querySelector('#smart-fit-widget .sf-save-btn');
        if (btn) { btn.disabled = true; btn.textContent = 'جاري التحليل...'; }

        const data = await post('/fit/quick', {
            product_id:   pid,
            chest, waist, shoulder,
            shoe_size_eu: shoe,
            preferred_fit: pref,
        });

        if (btn) { btn.disabled = false; btn.textContent = 'احسب مقاسي المناسب'; }

        if (data.results) {
            const widget = document.getElementById('smart-fit-widget');
            renderFitResults(widget, data);
        }
    };

    window._sfEditProfile = function() {
        const widget = document.getElementById('smart-fit-widget');
        if (widget) renderProfilePrompt(widget, []);
    };

    // ── Init ──────────────────────────────────────────────────────────────────

    async function init() {
        // Only on product pages
        if (!location.pathname.includes('/shop/product')) return;

        const pid = getProductId();
        if (!pid) return;

        // Fetch analysis
        const data = await post('/fit/analyze', {product_id: pid});
        if (data && data.has_sizes) {
            // Wait for page to fully render
            setTimeout(() => injectFitWidget(data), 800);
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
