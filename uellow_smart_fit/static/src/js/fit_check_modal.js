/**
 * Uellow Smart Fit — Product page "Check fit" button + modal
 *
 * Behaviour:
 *   1. On product page load, POST /fit/eligibility { product_id }.
 *   2. If eligible, inject a yellow "Check fit on me" button next to
 *      the "Add to Cart" button.
 *   3. On click, POST /fit/check { product_id } and render a modal
 *      with: ring gauge for overall %, per-area bars, body silhouette
 *      with colored regions, alt-size chips, add-to-cart CTA.
 *   4. If user has measurements profile incomplete, the modal shows a
 *      friendly CTA to /my/measurements.
 *
 * Storage / display unit: all measurements stored in cm. If the
 * user's preferred_unit is "inch", the modal converts on display.
 */
(function () {
    'use strict';

    // ── i18n (English source, Arabic translation) ────────────────────────
    const LANG = (document.documentElement.lang || 'en').startsWith('ar') ? 'ar' : 'en';
    const T = (en, ar) => (LANG === 'ar' && ar) ? ar : en;

    // ── Tiny JSON-RPC helper (matches Odoo's protocol) ───────────────────
    function rpc(url, params) {
        return fetch(url, {
            method:  'POST',
            headers: {'Content-Type': 'application/json'},
            body:    JSON.stringify({jsonrpc: '2.0', method: 'call', id: 1, params: params || {}}),
        }).then(r => r.json()).then(d => d.result || {});
    }

    function escapeHTML(s) {
        return String(s == null ? '' : s)
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    }

    function getProductId() {
        const root = document.querySelector('[data-main-object^="product.template("]');
        if (root) {
            const m = root.getAttribute('data-main-object').match(/\((\d+)/);
            if (m) return parseInt(m[1], 10);
        }
        const input = document.querySelector('input[name="product_template_id"]');
        if (input) return parseInt(input.value, 10);
        const m = location.pathname.match(/\/shop\/product\/[^/]*?-(\d+)(\/|$|\?)/);
        if (m) return parseInt(m[1], 10);
        return null;
    }

    // ── Unit conversion ──────────────────────────────────────────────────
    function fmt(value_cm, unit) {
        if (value_cm == null) return '—';
        if (unit === 'inch') return (value_cm * 0.393701).toFixed(1) + ' in';
        return (Math.round(value_cm * 10) / 10) + ' cm';
    }

    // ── Visualization: ring gauge ────────────────────────────────────────
    function ringGauge(pct, color) {
        const r = 48;
        const circ = 2 * Math.PI * r;
        const dash = (pct / 100 * circ).toFixed(1);
        return `
            <svg width="130" height="130" viewBox="0 0 120 120" class="usf-gauge">
                <circle cx="60" cy="60" r="${r}" fill="none" stroke="#F1EFE7" stroke-width="10"/>
                <circle cx="60" cy="60" r="${r}" fill="none" stroke="${color}" stroke-width="10"
                        stroke-linecap="round"
                        stroke-dasharray="${dash} ${circ}"
                        transform="rotate(-90 60 60)"
                        class="usf-gauge-arc"/>
                <text x="60" y="68" text-anchor="middle"
                      font-size="26" font-weight="800" fill="#412402"
                      font-family="inherit">${pct}%</text>
            </svg>`;
    }

    // ── Visualization: radar/spider chart (body vs garment polygons) ─────
    function radarChart(areas) {
        const size   = 230;
        const cx     = size / 2;
        const cy     = size / 2;
        const radius = 78;
        const valid  = areas.filter(a => a.body_cm != null && a.garment_cm != null);
        if (valid.length < 3) return '';

        // Normalize: for each axis, use max(body, garment, baseline) as 100%
        const ptsBody = [];
        const ptsGarm = [];
        const axes    = [];
        const n = valid.length;
        valid.forEach((a, i) => {
            const angle = (Math.PI * 2 * i / n) - Math.PI / 2;
            const max   = Math.max(a.body_cm, a.garment_cm, 1);
            const rB    = (a.body_cm    / max) * radius;
            const rG    = (a.garment_cm / max) * radius;
            ptsBody.push([cx + Math.cos(angle) * rB, cy + Math.sin(angle) * rB]);
            ptsGarm.push([cx + Math.cos(angle) * rG, cy + Math.sin(angle) * rG]);
            axes.push({
                x: cx + Math.cos(angle) * (radius + 14),
                y: cy + Math.sin(angle) * (radius + 14),
                label: a.label || a.key,
            });
        });

        const ringPaths = [0.25, 0.5, 0.75, 1].map(t => {
            const pts = [];
            for (let i = 0; i < n; i++) {
                const angle = (Math.PI * 2 * i / n) - Math.PI / 2;
                pts.push((cx + Math.cos(angle) * radius * t) + ',' + (cy + Math.sin(angle) * radius * t));
            }
            return `<polygon points="${pts.join(' ')}" fill="none" stroke="#ECE9E1" stroke-width="1"/>`;
        }).join('');

        const axisLines = [];
        for (let i = 0; i < n; i++) {
            const angle = (Math.PI * 2 * i / n) - Math.PI / 2;
            const x2 = cx + Math.cos(angle) * radius;
            const y2 = cy + Math.sin(angle) * radius;
            axisLines.push(`<line x1="${cx}" y1="${cy}" x2="${x2}" y2="${y2}" stroke="#ECE9E1" stroke-width="1"/>`);
        }

        const labelEls = axes.map(a => `
            <text x="${a.x}" y="${a.y}" text-anchor="middle"
                  font-size="10" fill="#5F5E5A" dominant-baseline="middle"
                  font-family="inherit">${escapeHTML(a.label)}</text>
        `).join('');

        const bodyPoly = `<polygon points="${ptsBody.map(p=>p.join(',')).join(' ')}"
                          fill="rgba(245,195,32,0.30)" stroke="#F5C320" stroke-width="2"/>`;
        const garmPoly = `<polygon points="${ptsGarm.map(p=>p.join(',')).join(' ')}"
                          fill="rgba(29,158,117,0.18)" stroke="#1D9E75" stroke-width="2" stroke-dasharray="4 3"/>`;

        return `
            <div class="usf-radar-wrap">
                <svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" class="usf-radar">
                    ${ringPaths}
                    ${axisLines.join('')}
                    ${garmPoly}
                    ${bodyPoly}
                    ${labelEls}
                </svg>
                <div class="usf-radar-legend">
                    <span><span class="usf-legend-swatch body"></span> ${T('Your body', 'جسمك')}</span>
                    <span><span class="usf-legend-swatch garm"></span> ${T('Garment', 'القطعة')}</span>
                </div>
            </div>`;
    }

    // ── Visualization: per-area horizontal bars ──────────────────────────
    function areasBreakdown(areas, unit) {
        const FIT = {
            tight:       {en: 'Tight',        ar: 'ضيّق',     cls: 'tight'},
            comfortable: {en: 'Comfortable ✓', ar: 'مريح ✓',   cls: 'good'},
            loose:       {en: 'Loose',        ar: 'واسع',     cls: 'loose'},
            unknown:     {en: 'Unknown',      ar: 'غير محدّد', cls: 'unknown'},
        };
        const labelMap = {
            'الصدر':    'Chest', 'الكتف': 'Shoulder', 'الكم': 'Sleeve',
            'الطول':    'Length', 'الوسط': 'Waist', 'الورك': 'Hip',
            'الساق':    'Inseam', 'الفخذ': 'Thigh', 'طول القدم': 'Foot length',
        };
        return areas.map(a => {
            const fitInfo = FIT[a.fit] || FIT.unknown;
            const lblAr = a.label || a.key || '';
            const lblEn = labelMap[lblAr] || lblAr;
            const lbl   = T(lblEn, lblAr);
            const diff  = (a.diff_cm != null)
                ? `<span class="usf-area-diff">${a.diff_cm > 0 ? '+' : ''}${fmt(Math.abs(a.diff_cm), unit).replace('cm','').replace('in','').trim()}${a.diff_cm > 0 ? '' : ''} ${unit === 'inch' ? 'in' : 'cm'}</span>`
                : '';
            const body  = a.body_cm    != null ? `<span class="usf-area-meas">${T('You','أنت')}: <b>${fmt(a.body_cm, unit)}</b></span>` : '';
            const garm  = a.garment_cm != null ? `<span class="usf-area-meas">${T('Garment','قماش')}: <b>${fmt(a.garment_cm, unit)}</b></span>` : '';
            const pct   = a.pct != null ? a.pct : 0;
            return `
                <div class="usf-area">
                    <div class="usf-area-row">
                        <span class="usf-area-label">${escapeHTML(lbl)}</span>
                        <span class="usf-area-verdict ${fitInfo.cls}">${T(fitInfo.en, fitInfo.ar)}</span>
                        ${diff}
                    </div>
                    <div class="usf-area-bar">
                        <div class="usf-area-bar-fill ${fitInfo.cls}" style="width:${Math.max(5, pct)}%"></div>
                    </div>
                    <div class="usf-area-meas-row">${body}${garm}</div>
                </div>`;
        }).join('');
    }

    // ── Visualization: body silhouette with tinted regions ───────────────
    function bodySilhouette(areas) {
        const fitColor = {
            comfortable: '#1D9E75',
            tight:       '#E24B4A',
            loose:       '#E89B23',
            unknown:     '#D1CFC4',
        };
        // Map area key → silhouette part
        const part = {};
        areas.forEach(a => { part[a.key] = fitColor[a.fit] || fitColor.unknown; });

        return `
            <svg viewBox="0 0 100 200" class="usf-body" aria-hidden="true">
                <!-- Head -->
                <circle cx="50" cy="18" r="11" fill="#F5F4F2" stroke="#BDB9B0" stroke-width="0.6"/>
                <!-- Shoulders -->
                <path d="M30 36 Q50 28 70 36 L72 44 L28 44 Z"
                      fill="${part.shoulder || '#F5F4F2'}" stroke="#BDB9B0" stroke-width="0.6" opacity="0.85"/>
                <!-- Chest -->
                <path d="M28 44 L72 44 L72 70 L28 70 Z"
                      fill="${part.chest || '#F5F4F2'}" stroke="#BDB9B0" stroke-width="0.6" opacity="0.85"/>
                <!-- Waist -->
                <path d="M30 70 L70 70 L66 92 L34 92 Z"
                      fill="${part.waist || '#F5F4F2'}" stroke="#BDB9B0" stroke-width="0.6" opacity="0.85"/>
                <!-- Hip -->
                <path d="M30 92 L70 92 L72 112 L28 112 Z"
                      fill="${part.hip || '#F5F4F2'}" stroke="#BDB9B0" stroke-width="0.6" opacity="0.85"/>
                <!-- Arms -->
                <path d="M28 44 L18 88 L24 90 L34 50 Z"
                      fill="${part.sleeve || '#F5F4F2'}" stroke="#BDB9B0" stroke-width="0.6" opacity="0.85"/>
                <path d="M72 44 L82 88 L76 90 L66 50 Z"
                      fill="${part.sleeve || '#F5F4F2'}" stroke="#BDB9B0" stroke-width="0.6" opacity="0.85"/>
                <!-- Thighs -->
                <path d="M30 112 L48 112 L46 158 L34 158 Z"
                      fill="${part.thigh || '#F5F4F2'}" stroke="#BDB9B0" stroke-width="0.6" opacity="0.85"/>
                <path d="M52 112 L70 112 L66 158 L54 158 Z"
                      fill="${part.thigh || '#F5F4F2'}" stroke="#BDB9B0" stroke-width="0.6" opacity="0.85"/>
                <!-- Legs / inseam -->
                <path d="M34 158 L46 158 L44 190 L36 190 Z"
                      fill="${part.inseam || '#F5F4F2'}" stroke="#BDB9B0" stroke-width="0.6" opacity="0.85"/>
                <path d="M54 158 L66 158 L64 190 L56 190 Z"
                      fill="${part.inseam || '#F5F4F2'}" stroke="#BDB9B0" stroke-width="0.6" opacity="0.85"/>
            </svg>`;
    }

    // ── The Modal ────────────────────────────────────────────────────────
    function openModal(html) {
        const existing = document.getElementById('usf-modal');
        if (existing) existing.remove();
        const overlay = document.createElement('div');
        overlay.id = 'usf-modal';
        overlay.className = 'usf-modal-overlay';
        overlay.innerHTML = `<div class="usf-modal" role="dialog" aria-modal="true">${html}</div>`;
        document.body.appendChild(overlay);
        document.body.style.overflow = 'hidden';

        const close = () => {
            overlay.remove();
            document.body.style.overflow = '';
            document.removeEventListener('keydown', onKey);
        };

        // Use event delegation so the close button keeps working after
        // every full re-render of the modal HTML.
        overlay.addEventListener('click', e => {
            if (e.target === overlay) { close(); return; }
            const closeBtn = e.target.closest && e.target.closest('[data-action="close"]');
            if (closeBtn) { e.preventDefault(); e.stopPropagation(); close(); }
        });

        const onKey = e => { if (e.key === 'Escape') close(); };
        document.addEventListener('keydown', onKey);

        return {close, root: overlay};
    }

    function renderLoading() {
        return `
            <div class="usf-modal-header">
                <h3>${T('Checking your fit…', 'جاري فحص توافق المقاس…')}</h3>
                <button data-action="close" class="usf-close" aria-label="Close">✕</button>
            </div>
            <div class="usf-modal-body">
                <div class="usf-spinner"></div>
                <p class="text-center text-muted">${T('Comparing your measurements with the size chart…',
                                                       'نقارن مقاساتك مع جدول مقاسات المنتج…')}</p>
            </div>`;
    }

    function renderError(state, data) {
        const messages = {
            no_profile: {
                title: T('Add your measurements first', 'أضف مقاساتك أول'),
                body:  T('Complete your body profile so we can give you an accurate fit.',
                         'أكمل مقاساتك الشخصية عشان نعطيك نتيجة دقيقة.'),
                cta:   T('Open my measurements', 'افتح مقاساتي'),
                href:  data.measurements_url || '/my/measurements',
            },
            no_chart: {
                title: T('No detailed size chart yet', 'لا يوجد جدول مقاسات تفصيلي'),
                body:  T('This product doesn\'t have a detailed measurement chart yet. Ask Beena for a recommendation instead.',
                         'هذا المنتج ما عنده جدول مقاسات تفصيلي بعد. اسأل بينا لتوصية تقريبية.'),
            },
            error: {
                title: T('Something went wrong', 'صار خطأ بسيط'),
                body:  T('Please try again in a moment.', 'حاول مرة ثانية بعد قليل.'),
            },
            product_not_found: {
                title: T('Product not found', 'المنتج غير موجود'),
            },
            no_product: {
                title: T('Open a product first', 'افتح منتج أول'),
            },
        };
        const m = messages[state] || messages.error;
        return `
            <div class="usf-modal-header">
                <h3>${escapeHTML(m.title)}</h3>
                <button data-action="close" class="usf-close" aria-label="Close">✕</button>
            </div>
            <div class="usf-modal-body usf-empty">
                <div class="usf-empty-icon">📏</div>
                <p>${escapeHTML(m.body || '')}</p>
                ${m.href ? `<a href="${m.href}" class="usf-btn usf-btn-primary">${escapeHTML(m.cta)}</a>` : ''}
            </div>`;
    }

    function renderSizePicker(allSizes, currentSize) {
        const colorMap = {green:'#1D9E75', yellow:'#F5C320', orange:'#E89B23', red:'#E24B4A'};
        if (!Array.isArray(allSizes) || !allSizes.length) return '';
        const currentLow = (currentSize || '').toLowerCase();
        const chips = allSizes.map(s => {
            const isActive = (s.size || '').toLowerCase() === currentLow;
            const pctColor = colorMap[s.fit_color] || '#888';
            const recBadge = s.recommended ? `<span class="usf-size-rec" title="${T('Recommended','الموصى به')}">★</span>` : '';
            return `
                <button class="usf-size-chip ${isActive ? 'active' : ''}"
                        data-size="${escapeHTML(s.size)}"
                        type="button">
                    <span class="usf-size-name">${escapeHTML(s.size)}${recBadge}</span>
                    <span class="usf-size-pct" style="color:${pctColor}">${s.overall_pct}%</span>
                </button>`;
        }).join('');
        return `
            <div class="usf-size-picker">
                <div class="usf-size-picker-label">${T('Change size', 'غيّر المقاس')}:</div>
                <div class="usf-size-picker-chips">${chips}</div>
            </div>`;
    }

    function renderResultBody(data) {
        const colorMap = {green:'#1D9E75', yellow:'#F5C320', orange:'#E89B23', red:'#E24B4A'};
        const c = colorMap[data.fit_color] || colorMap.yellow;
        const unit = data.preferred_unit || 'cm';

        const fitLabelMap = {
            'مناسب تماماً': T('Perfect fit',     'مناسب تماماً'),
            'مناسب':        T('Good fit',        'مناسب'),
            'مقبول':        T('Acceptable',      'مقبول'),
            'غير مناسب':    T('Poor fit',        'غير مناسب'),
        };
        const fitLabel = fitLabelMap[data.fit_label] || data.fit_label || '';

        const overall = Number(data.overall_pct || 0);
        let ctaHtml = '';
        if (overall >= 80) {
            ctaHtml = `<button class="usf-btn usf-btn-primary usf-btn-lg" data-action="add-to-cart"
                          data-variant-id="${data.variant_id || 0}"
                          data-product-name="${escapeHTML(data.product_name || '')}">
                          🛒 ${T('Add size '+escapeHTML(data.size)+' to cart',
                                  'أضف المقاس '+escapeHTML(data.size)+' للسلة')}
                      </button>`;
        } else if (overall >= 60) {
            ctaHtml = `<button class="usf-btn usf-btn-primary usf-btn-lg" data-action="add-to-cart"
                          data-variant-id="${data.variant_id || 0}"
                          data-product-name="${escapeHTML(data.product_name || '')}">
                          🛒 ${T('Add to cart anyway', 'أضف للسلة على أي حال')}
                      </button>`;
        } else {
            // Suggest the best alternate inside CTA (the picker above also shows it)
            const better = (data.all_sizes || data.alternates || [])
                .filter(s => (s.size || '').toLowerCase() !== (data.size || '').toLowerCase())
                .sort((a, b) => b.overall_pct - a.overall_pct)[0];
            if (better && better.overall_pct > overall) {
                ctaHtml = `<button class="usf-btn usf-btn-primary usf-btn-lg" data-action="recheck"
                              data-size="${escapeHTML(better.size)}">
                              💡 ${T('Try size '+escapeHTML(better.size)+' ('+better.overall_pct+'%)',
                                      'جرّب المقاس '+escapeHTML(better.size)+' ('+better.overall_pct+'%)')}
                          </button>`;
            } else {
                ctaHtml = `<button class="usf-btn usf-btn-secondary usf-btn-lg" disabled>
                              ${T('This size may not fit you', 'المقاس قد لا يناسبك')}
                          </button>`;
            }
        }

        return `
            ${renderSizePicker(data.all_sizes || [], data.size)}

            <div class="usf-top">
                <div class="usf-top-gauge">
                    ${ringGauge(overall, c)}
                    <div class="usf-top-label" style="color:${c}">${escapeHTML(fitLabel)}</div>
                    <div class="usf-top-size-pill">${T('Size', 'المقاس')}: <b>${escapeHTML(data.size||'-')}</b></div>
                </div>
                <div class="usf-top-body">
                    ${bodySilhouette(data.areas || [])}
                </div>
                <div class="usf-top-radar">
                    ${radarChart(data.areas || [])}
                </div>
            </div>

            <div class="usf-section-title">${T('Per-area breakdown', 'تفاصيل لكل منطقة')}</div>
            <div class="usf-areas">
                ${areasBreakdown(data.areas || [], unit)}
            </div>

            <div class="usf-cta">${ctaHtml}</div>

            <div class="usf-footer">
                <a href="/my/measurements" class="usf-link">
                    ✏️ ${T('Edit my measurements', 'تعديل مقاساتي')}
                </a>
                <a href="/my/fit-history" class="usf-link">
                    📜 ${T('My fit history', 'سجل فحوصاتي')}
                </a>
                <button class="usf-link" data-action="share">
                    🔗 ${T('Share result', 'شارك النتيجة')}
                </button>
            </div>`;
    }

    function renderResult(data) {
        return `
            <div class="usf-modal-header">
                <div>
                    <h3>${T('Size Fit Check', 'فحص توافق المقاس')}</h3>
                    <div class="usf-modal-sub">${escapeHTML(data.product_name || '')}</div>
                </div>
                <button data-action="close" class="usf-close" aria-label="Close">✕</button>
            </div>
            <div class="usf-modal-body" id="usf-modal-body">
                ${renderResultBody(data)}
            </div>`;
    }

    // ── Variant pre-selection on the product page ────────────────────────
    function preSelectVariantSize(sizeLabel) {
        if (!sizeLabel) return;
        const lbl = String(sizeLabel).trim().toLowerCase();
        // Theme Prime / Odoo variant selectors come in a few flavours:
        const radios = document.querySelectorAll(
            'input[type="radio"][name^="ptal-"]'
        );
        radios.forEach(r => {
            const id = r.id;
            const txt = (document.querySelector(`label[for="${id}"]`)?.textContent || '').trim().toLowerCase();
            if (txt === lbl) {
                r.checked = true;
                r.dispatchEvent(new Event('change', {bubbles: true}));
            }
        });
        // Some themes use <select>
        document.querySelectorAll('select.css_attribute_select').forEach(sel => {
            for (const opt of sel.options) {
                if ((opt.textContent || '').trim().toLowerCase() === lbl) {
                    sel.value = opt.value;
                    sel.dispatchEvent(new Event('change', {bubbles: true}));
                    break;
                }
            }
        });
    }

    // ── Add-to-cart helper (uses existing Beena helper if present) ───────
    function addToCart(variantId, productName) {
        if (variantId && window._beenaAddToCart) {
            window._beenaAddToCart(variantId, productName);
            return;
        }
        // Fallback: click the page's add-to-cart button
        const btn = document.querySelector('#add_to_cart, #product_details a.a-submit, .a-submit#add_to_cart');
        if (btn) btn.click();
    }

    function shareResult(data) {
        const text = T(
            `I checked the fit on Uellow! Size ${data.size} fits me ${data.overall_pct}% on ${data.product_name}.`,
            `جرّبت فحص توافق المقاس على Uellow! مقاس ${data.size} يناسبني ${data.overall_pct}% على ${data.product_name}.`
        );
        if (navigator.share) {
            navigator.share({title: 'Uellow Fit Check', text, url: location.href}).catch(() => {});
        } else if (navigator.clipboard) {
            navigator.clipboard.writeText(text + '\n' + location.href);
            alert(T('Copied to clipboard ✓', 'تم النسخ ✓'));
        }
    }

    /**
     * Wire the interactive controls inside the modal body after a render.
     * Called for every size change so handlers always point at the latest data.
     */
    function wireResultHandlers(root, modal, data, productId) {
        // Body click delegate not used here; we attach per-element for clarity.
        root.querySelectorAll('.usf-size-chip').forEach(btn => {
            btn.addEventListener('click', () => {
                const newSize = btn.dataset.size;
                if (!newSize || newSize.toLowerCase() === (data.size || '').toLowerCase()) return;
                updateModalForSize(modal, productId, newSize);
            });
        });
        root.querySelectorAll('[data-action="add-to-cart"]').forEach(btn => {
            btn.addEventListener('click', () => {
                const vid = parseInt(btn.dataset.variantId || '0', 10);
                preSelectVariantSize(data.size);
                addToCart(vid, btn.dataset.productName);
                setTimeout(() => modal.close(), 400);
            });
        });
        root.querySelectorAll('[data-action="recheck"]').forEach(btn => {
            btn.addEventListener('click', () => {
                updateModalForSize(modal, productId, btn.dataset.size);
            });
        });
        root.querySelectorAll('[data-action="share"]').forEach(btn => {
            btn.addEventListener('click', () => shareResult(data));
        });
        // Animate the ring once it lands
        const arc = root.querySelector('.usf-gauge-arc');
        if (arc) arc.style.animation = 'usfGaugeFill 1s ease-out';
    }

    /**
     * Re-fetch the analysis for a different size and swap ONLY the modal body
     * (keeps the header + scroll position, and shows a tiny inline spinner).
     */
    async function updateModalForSize(modal, productId, newSize) {
        const body = modal.root.querySelector('#usf-modal-body');
        if (!body) return;
        body.classList.add('usf-fading');
        const overlay = document.createElement('div');
        overlay.className = 'usf-inline-spinner';
        overlay.innerHTML = '<div class="usf-spinner-sm"></div>';
        body.appendChild(overlay);

        const data = await rpc('/fit/check', {product_id: productId, size: newSize || ''});
        if (!data || data.state !== 'ready') {
            body.classList.remove('usf-fading');
            overlay.remove();
            modal.root.querySelector('.usf-modal').innerHTML = renderError(data.state || 'error', data || {});
            return;
        }
        body.innerHTML = renderResultBody(data);
        body.classList.remove('usf-fading');
        wireResultHandlers(modal.root, modal, data, productId);
    }

    async function runFitCheck(productId, requestedSize) {
        const modal = openModal(renderLoading());
        const data  = await rpc('/fit/check', {product_id: productId, size: requestedSize || ''});
        const state = data.state || 'error';

        if (state !== 'ready') {
            modal.root.querySelector('.usf-modal').innerHTML = renderError(state, data);
            return;
        }

        modal.root.querySelector('.usf-modal').innerHTML = renderResult(data);
        wireResultHandlers(modal.root, modal, data, productId);
    }

    // ── Locate the "Size" attribute container on the product page ───────
    // Theme Prime + Odoo 18 render variant attributes inside one of several
    // wrappers depending on the display type. We find the row/container
    // holding the *Size* attribute by matching its label text.
    function findSizeAttributeAnchor() {
        const keywords = ['size', 'مقاس', 'حجم'];
        const isSize = txt => {
            const s = String(txt || '').trim().toLowerCase();
            if (!s) return false;
            return keywords.some(kw => s === kw || s.startsWith(kw) || (' ' + s + ' ').includes(' ' + kw + ' '));
        };

        // 1) Odoo 18 / theme_prime: a <tr> per attribute
        const rows = document.querySelectorAll(
            'tr.js_attribute_value, tr[data-attribute_id], .variant_attribute'
        );
        for (const row of rows) {
            const lbl = row.querySelector('.attribute_name, label, th, td:first-child');
            if (lbl && isSize(lbl.textContent)) return row;
        }

        // 2) data-attribute_name on any element
        const named = document.querySelectorAll('[data-attribute_name]');
        for (const el of named) {
            if (isSize(el.dataset.attributeName)) return el;
        }

        // 3) any label whose text == Size — walk up to its row container
        const labels = document.querySelectorAll(
            'strong, label, .o_wsale_product_attributes label, .attribute_name'
        );
        for (const lbl of labels) {
            if (isSize(lbl.textContent)) {
                let p = lbl.parentElement;
                for (let i = 0; i < 5 && p; i++, p = p.parentElement) {
                    if (p.matches && p.matches('tr, .variant_attribute, .form-group, .row, .js_attribute_value, [data-attribute_id]')) {
                        return p;
                    }
                }
                return lbl.parentElement;
            }
        }
        return null;
    }

    function _insertAfter(newNode, refNode) {
        if (refNode && refNode.parentNode) {
            refNode.parentNode.insertBefore(newNode, refNode.nextSibling);
            return true;
        }
        return false;
    }

    /**
     * Find the last visible size-value control on the page and return its
     * outer-most "sibling wrapper" — the element that should sit beside
     * our button. Returns null if no size controls were found.
     *
     * Example shapes we handle:
     *   <ul><li><input/><label>S</label></li>...<li>XL</li></ul>
     *   <td><label class="css_attribute_color">S</label>...<label>XL</label></td>
     *   <div><span class="o_wsale_product_attribute">S</span>...</div>
     *
     * The "sibling wrapper" is the element to clone (li/span/label/div) so
     * the new button inherits inline layout from the surrounding siblings.
     */
    function findLastSizeValueSibling() {
        const row = findSizeAttributeAnchor();
        if (!row) return null;

        const radios = row.querySelectorAll('input[type="radio"]');
        if (radios.length) {
            const last  = radios[radios.length - 1];
            // The visible element is usually a <label> for the radio, but
            // it might be wrapped in <li>/<div>. Walk up while we keep
            // having only ONE radio inside (so we don't escape to the row).
            let node = last;
            let parent = node.parentNode;
            while (parent && parent !== row) {
                const radiosIn = parent.querySelectorAll('input[type="radio"]');
                if (radiosIn.length !== 1) break;
                node = parent;
                parent = parent.parentNode;
            }
            return node;
        }

        // Color/size swatches without explicit radio
        const swatches = row.querySelectorAll('.css_attribute_color, .o_wsale_product_attribute, label');
        if (swatches.length) {
            const last = swatches[swatches.length - 1];
            // Walk up while we keep having only ONE swatch inside
            let node = last;
            let parent = node.parentNode;
            while (parent && parent !== row) {
                const inside = parent.querySelectorAll('.css_attribute_color, .o_wsale_product_attribute, label');
                if (inside.length !== 1) break;
                node = parent;
                parent = parent.parentNode;
            }
            return node;
        }

        // Select dropdown — just use the select itself
        const select = row.querySelector('select');
        if (select) return select;

        return null;
    }

    /**
     * Build the small inline pill-style button used inside the size row.
     */
    function _buildInlineBtn(idAttr, isLink, href, label) {
        const el = document.createElement(isLink ? 'a' : 'button');
        el.id = idAttr;
        if (!isLink) el.type = 'button';
        if (href) el.href = href;
        el.className = 'usf-check-fit-btn usf-inline' + (isLink ? ' usf-soft' : '');
        el.innerHTML = `<span class="usf-cf-icon">📏</span>
                        <span class="usf-cf-label">${label}</span>`;
        return el;
    }

    /**
     * Inject the button as a sibling of the last size value control.
     * If the siblings are <li>/<span>/<label>/<div>, we clone that wrapping
     * tag so our button inherits the surrounding flex/inline-block layout.
     * Returns true on success.
     */
    function injectInlineNextToSizes(buttonEl) {
        const sibling = findLastSizeValueSibling();
        if (!sibling || !sibling.parentNode) return false;
        const tag = (sibling.tagName || 'span').toLowerCase();
        let wrap;
        if (tag === 'li') {
            wrap = document.createElement('li');
            wrap.className = sibling.className || '';
            wrap.classList.add('usf-inline-wrap');
        } else if (tag === 'label' || tag === 'select') {
            // Use a plain span — labels/selects shouldn't nest others.
            wrap = document.createElement('span');
            wrap.className = 'usf-inline-wrap';
        } else {
            // Mirror the tag (span, div, etc.) so flex/inline-block parents
            // treat us the same as their existing children.
            wrap = document.createElement(tag);
            if (sibling.className) wrap.className = sibling.className;
            wrap.classList.add('usf-inline-wrap');
        }
        wrap.appendChild(buttonEl);
        sibling.parentNode.insertBefore(wrap, sibling.nextSibling);
        return true;
    }

    // ── Button injection ─────────────────────────────────────────────────
    function injectButton(eligibility) {
        if (document.getElementById('usf-check-fit-btn')) return;

        const button = _buildInlineBtn(
            'usf-check-fit-btn', false, null,
            T('Check fit on me', 'افحص توافقه عليّ'),
        );
        button.addEventListener('click', () => {
            const pid = getProductId();
            if (pid) runFitCheck(pid);
        });

        // 1) preferred: inline, as a sibling of the LAST size value
        if (injectInlineNextToSizes(button)) return;

        // 2) own line under the Size attribute row
        button.classList.remove('usf-inline');
        button.innerHTML = `<span class="usf-cf-icon">📏</span>
                            <span class="usf-cf-label">${T('Check fit on me', 'افحص توافقه عليّ')}</span>
                            <span class="usf-cf-sub">${T('Free · ~3 seconds', 'مجاناً · ~3 ثواني')}</span>`;
        const blockWrap = document.createElement('div');
        blockWrap.className = 'usf-check-fit-wrap';
        blockWrap.appendChild(button);
        const sizeAnchor = findSizeAttributeAnchor();
        if (sizeAnchor && _insertAfter(blockWrap, sizeAnchor)) return;

        // 3) before Add-to-Cart
        const addToCartBtn =
            document.querySelector('#add_to_cart') ||
            document.querySelector('a#add_to_cart') ||
            document.querySelector('.js_main_product .a-submit') ||
            document.querySelector('button[name="add_to_cart"]');
        if (addToCartBtn && addToCartBtn.parentNode) {
            addToCartBtn.parentNode.insertBefore(blockWrap, addToCartBtn);
            return;
        }

        // 4) floating
        button.classList.add('usf-floating');
        document.body.appendChild(button);
    }

    function injectNoProfileHint(eligibility) {
        if (document.getElementById('usf-need-profile-btn')) return;
        const btn = _buildInlineBtn(
            'usf-need-profile-btn', true,
            eligibility.measurements_url || '/my/measurements',
            T('Add measurements to check fit', 'أضف مقاساتك لفحص التوافق'),
        );

        if (injectInlineNextToSizes(btn)) return;

        // own line fallback
        btn.classList.remove('usf-inline');
        btn.innerHTML = `<span class="usf-cf-icon">📏</span>
                         <span class="usf-cf-label">${T('Add measurements to check fit', 'أضف مقاساتك لفحص التوافق')}</span>
                         <span class="usf-cf-sub">${T('1 minute setup', 'إعداد دقيقة واحدة')}</span>`;
        const blockWrap = document.createElement('div');
        blockWrap.className = 'usf-check-fit-wrap';
        blockWrap.appendChild(btn);
        const sizeAnchor = findSizeAttributeAnchor();
        if (sizeAnchor && _insertAfter(blockWrap, sizeAnchor)) return;

        const addToCartBtn =
            document.querySelector('#add_to_cart') ||
            document.querySelector('a#add_to_cart') ||
            document.querySelector('button[name="add_to_cart"]');
        if (addToCartBtn && addToCartBtn.parentNode) {
            addToCartBtn.parentNode.insertBefore(blockWrap, addToCartBtn);
        }
    }

    // ── Init ─────────────────────────────────────────────────────────────
    function _isProductDetailPage() {
        // 1. URL must match /shop/product/<slug>-<id>
        if (!/\/shop\/product\/[^/]+-\d+($|\/|\?)/.test(location.pathname)) return false;
        // 2. The page must expose the product detail anchor that
        //    template-level injections (XPath) hook into. Listing pages do
        //    NOT have this — they only carry per-card forms.
        return !!document.querySelector(
            '[data-main-object^="product.template("], #product_details, .js_main_product'
        );
    }

    async function init() {
        // Gate: only run on the product detail page. Without this guard the
        // script also fires on /shop and category listings because Theme
        // Prime cards expose hidden product_template_id inputs.
        if (!_isProductDetailPage()) return;

        const pid = getProductId();
        if (!pid) return;

        let elig;
        try {
            elig = await rpc('/fit/eligibility', {product_id: pid});
        } catch (e) {
            return;
        }
        if (!elig) return;

        if (elig.eligible) {
            injectButton(elig);
            return;
        }
        // Soft nudges for two recoverable states
        if (elig.reason === 'no_profile') {
            injectNoProfileHint(elig);
        }
        // logged_out / not_fashion / no_chart / product_not_found → silent
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
