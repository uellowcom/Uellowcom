/* Delivery Backend Dashboard */
'use strict';

(function () {
    // ── Helpers ──────────────────────────────────────────────────────────
    var isAr = document.documentElement.lang && document.documentElement.lang.startsWith('ar');

    function fmt(n) { return parseFloat(n || 0).toFixed(3); }
    function pct(n) { return (n || 0).toFixed(1) + '%'; }
    function t(ar, en) { return isAr ? ar : en; }

    function jsonRpc(route, params) {
        return fetch(route, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ jsonrpc: '2.0', method: 'call', id: 1, params: params || {} }),
        }).then(function (r) { return r.json(); }).then(function (d) { return d.result || d; });
    }

    function statusBadge(status) {
        var map = {
            'pending':          ['dp-tag dp-tag-gray', t('انتظار', 'Pending')],
            'assigned':         ['dp-tag dp-tag-blue', t('جديد', 'New')],
            'out_for_delivery': ['dp-tag dp-tag-yellow', t('🚚 في الطريق', '🚚 In Transit')],
            'delivered':        ['dp-tag dp-tag-green', t('✅ تم', '✅ Delivered')],
            'failed':           ['dp-tag dp-tag-red', t('❌ فشل', '❌ Failed')],
            'failed_returned':  ['dp-tag dp-tag-red', t('↩ مُستلم', '↩ Returned')],
        };
        var s = map[status] || ['dp-tag dp-tag-gray', status];
        return '<span class="' + s[0] + '">' + s[1] + '</span>';
    }

    function payBadge(type) {
        if (type === 'cash') return '<span class="dp-tag dp-tag-red">' + t('كاش', 'Cash') + '</span>';
        return '<span class="dp-tag dp-tag-green">' + t('أونلاين', 'Online') + '</span>';
    }

    // ── KPI Cards ────────────────────────────────────────────────────────
    function renderKPI(kpi) {
        var el = document.getElementById('db-kpi');
        if (!el) return;
        el.innerHTML =
            kpiCard('📦', t('إجمالي الطلبات', 'Total Orders'), kpi.total, '', 'blue', kpi.total > 0 ? t('↑ هذه الفترة', '↑ This period') : '') +
            kpiCard('✅', t('تم التوصيل', 'Delivered'), kpi.delivered, pct(kpi.success_rate), 'green', t('نسبة النجاح: ' + pct(kpi.success_rate), 'Success: ' + pct(kpi.success_rate))) +
            kpiCard('❌', t('فشل التوصيل', 'Failed'), kpi.failed, '', 'red', '') +
            kpiCard('🚚', t('في الطريق الآن', 'In Transit Now'), kpi.in_transit, '', 'yellow', t('لايف', 'Live')) +
            kpiCard('🕐', t('مخصص — انتظار', 'Assigned — Pending'), kpi.assigned, '', 'blue', '') +
            kpiCard('↩', t('مرتجعات معلقة', 'Pending Returns'), kpi.returns_awaiting, '', 'red', '');

        var fin = document.getElementById('db-financial');
        if (!fin) return;
        fin.innerHTML =
            kpiCard('💵', t('إجمالي المبيعات المُوصَّلة', 'Total Delivered Sales'), 'KD ' + fmt(kpi.total_delivered_amount), '', 'green', '') +
            kpiCard('💳', t('أونلاين مدفوعة', 'Online Paid'), 'KD ' + fmt(kpi.online_amount), '', 'blue', pct(kpi.total_delivered_amount ? kpi.online_amount / kpi.total_delivered_amount * 100 : 0) + t(' من الإجمالي', ' of total')) +
            kpiCard('💵', t('كاش محصّل', 'Cash Collected'), 'KD ' + fmt(kpi.cash_amount), '', 'yellow', '') +
            kpiCard('💰', t('كاش معلق (غير مُسوَّى)', 'Pending Cash'), 'KD ' + fmt(kpi.cash_pending), '', 'red', kpi.pending_remittances + t(' طلب تسوية معلق', ' pending remittances')) +
            kpiCard('📊', t('متوسط قيمة الطلب', 'Avg Order Value'), 'KD ' + fmt(kpi.avg_order), '', 'purple', '') +
            kpiCard('✅', t('كاش مُسوَّى', 'Cash Remitted'), 'KD ' + fmt(kpi.cash_remitted), '', 'green', '');
    }

    function kpiCard(icon, label, value, sub, color, note) {
        return '<div class="db-kpi-card db-kpi-' + color + '">' +
            '<div class="db-kpi-icon">' + icon + '</div>' +
            '<div class="db-kpi-label">' + label + '</div>' +
            '<div class="db-kpi-value">' + value + '</div>' +
            (note ? '<div class="db-kpi-note">' + note + '</div>' : '') +
        '</div>';
    }

    // ── Bar Chart ────────────────────────────────────────────────────────
    function renderChart(trend) {
        var el = document.getElementById('db-chart');
        if (!el) return;
        var maxVal = Math.max.apply(null, trend.map(function (d) { return d.total || 1; }));
        var bars = trend.map(function (d, i) {
            var h = Math.round((d.total / maxVal) * 130) || 2;
            var hf = Math.round((d.failed / maxVal) * 130) || 0;
            var dt = d.date ? d.date.slice(5) : '';
            var isToday = i === trend.length - 1;
            return '<div class="db-bar-wrap">' +
                '<div class="db-bar-col">' +
                    '<div class="db-bar-fail" style="height:' + hf + 'px;"></div>' +
                    '<div class="db-bar-del ' + (isToday ? 'today' : '') + '" style="height:' + h + 'px;" title="' + d.total + '"></div>' +
                '</div>' +
                '<div class="db-bar-label">' + dt + '</div>' +
            '</div>';
        });
        el.innerHTML = bars.join('');
    }

    // ── Donut ────────────────────────────────────────────────────────────
    function renderDonut(kpi) {
        var el = document.getElementById('db-donut-info');
        if (!el) return;
        var total = kpi.total || 1;
        var rows = [
            { label: t('✅ تم التوصيل', '✅ Delivered'), val: kpi.delivered, color: '#16a34a' },
            { label: t('🚚 في الطريق', '🚚 In Transit'), val: kpi.in_transit, color: '#2d6be4' },
            { label: t('🕐 مخصص', '🕐 Assigned'), val: kpi.assigned, color: '#d97706' },
            { label: t('❌ فشل', '❌ Failed'), val: kpi.failed, color: '#dc2626' },
        ];
        el.innerHTML = rows.map(function (r) {
            var p = total ? Math.round(r.val / total * 100) : 0;
            return '<div class="db-donut-row">' +
                '<div style="display:flex;justify-content:space-between;font-size:11px;margin-bottom:3px;">' +
                    '<span style="color:' + r.color + ';">' + r.label + '</span>' +
                    '<span style="font-weight:700;">' + r.val + ' (' + p + '%)</span>' +
                '</div>' +
                '<div class="db-prog"><div class="db-prog-fill" style="width:' + p + '%;background:' + r.color + ';"></div></div>' +
            '</div>';
        }).join('');

        var pct_el = document.getElementById('db-donut-pct');
        if (pct_el) pct_el.textContent = kpi.success_rate + '%';
    }

    // ── Carriers ─────────────────────────────────────────────────────────
    function renderCarriers(carriers) {
        var el = document.getElementById('db-carriers');
        if (!el) return;
        if (!carriers.length) { el.innerHTML = '<div style="padding:16px;color:#94a3b8;text-align:center;">—</div>'; return; }
        el.innerHTML = carriers.map(function (c) {
            var color = c.success_rate >= 80 ? '#16a34a' : c.success_rate >= 70 ? '#d97706' : '#dc2626';
            return '<div class="db-carrier-item">' +
                '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">' +
                    '<div style="font-size:12px;font-weight:700;">🚚 ' + c.name + '</div>' +
                    '<span style="font-size:10px;font-weight:700;color:' + color + ';">' + pct(c.success_rate) + ' ' + t('نجاح', 'success') + '</span>' +
                '</div>' +
                '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px;font-size:10px;margin-bottom:6px;">' +
                    '<div style="text-align:center;"><div style="color:#64748b;">' + t('طلبات', 'Orders') + '</div><div style="font-weight:700;">' + c.total + '</div></div>' +
                    '<div style="text-align:center;"><div style="color:#64748b;">' + t('مُوصَّل', 'Delivered') + '</div><div style="font-weight:700;color:#16a34a;">' + c.delivered + '</div></div>' +
                    '<div style="text-align:center;"><div style="color:#64748b;">' + t('فشل', 'Failed') + '</div><div style="font-weight:700;color:#dc2626;">' + c.failed + '</div></div>' +
                '</div>' +
                '<div class="db-prog" style="margin-bottom:4px;"><div class="db-prog-fill" style="width:' + c.success_rate + '%;background:' + color + ';"></div></div>' +
                '<div style="font-size:10px;color:#64748b;display:flex;justify-content:space-between;">' +
                    '<span>' + t('كاش معلق: ', 'Pending Cash: ') + '<strong>KD ' + fmt(c.cash_pending) + '</strong></span>' +
                    '<span>' + t('سائقين: ', 'Drivers: ') + '<strong>' + c.drivers_count + '</strong></span>' +
                '</div>' +
            '</div>';
        }).join('');
    }

    // ── Driver Leaderboard ───────────────────────────────────────────────
    function renderDrivers(drivers) {
        var el = document.getElementById('db-drivers');
        if (!el) return;
        if (!drivers.length) { el.innerHTML = '<tr><td colspan="5" style="text-align:center;padding:16px;color:#94a3b8;">—</td></tr>'; return; }
        var medals = ['🥇', '🥈', '🥉'];
        el.innerHTML = drivers.map(function (d, i) {
            var color = d.success_rate >= 80 ? '#16a34a' : d.success_rate >= 70 ? '#d97706' : '#dc2626';
            return '<tr>' +
                '<td>' + (medals[i] || (i + 1)) + '</td>' +
                '<td style="font-weight:700;">' + d.name + '</td>' +
                '<td><span style="font-size:10px;font-weight:700;color:' + color + ';">' + pct(d.success_rate) + '</span></td>' +
                '<td>' + d.total + '</td>' +
                '<td style="font-size:10px;color:#15803d;">KD ' + fmt(d.cash_collected) + '</td>' +
            '</tr>';
        }).join('');
    }

    // ── Recent Orders ────────────────────────────────────────────────────
    function renderOrders(orders) {
        var el = document.getElementById('db-orders');
        if (!el) return;
        el.innerHTML = orders.map(function (o) {
            return '<tr>' +
                '<td style="font-family:monospace;font-weight:700;color:#2d6be4;"><a href="/odoo/sales/' + o.id + '" target="_blank">' + o.name + '</a></td>' +
                '<td>' + o.partner + '</td>' +
                '<td style="font-size:10px;">' + o.carrier + '</td>' +
                '<td style="font-weight:700;">KD ' + fmt(o.amount) + '</td>' +
                '<td>' + payBadge(o.payment) + '</td>' +
                '<td>' + statusBadge(o.status) + '</td>' +
                '<td style="font-size:10px;">' + (o.driver || '—') + '</td>' +
                '<td style="font-size:10px;color:#64748b;">' + (o.date ? o.date.replace('T', ' ').slice(0, 16) : '') + '</td>' +
            '</tr>';
        }).join('');
    }

    // ── Alerts ───────────────────────────────────────────────────────────
    function renderAlerts(alerts) {
        var el = document.getElementById('db-alerts');
        if (!el) return;
        if (!alerts.length) {
            el.innerHTML = '<div style="padding:14px;color:#16a34a;font-size:12px;">✅ ' + t('لا توجد تنبيهات — كل شيء على ما يرام', 'No alerts — everything looks good') + '</div>';
            return;
        }
        el.innerHTML = alerts.map(function (a) {
            var cls = a.type === 'danger' ? 'db-alert-red' : 'db-alert-yellow';
            var icon = a.type === 'danger' ? '⚠️' : '⏰';
            return '<div class="db-alert ' + cls + '">' + icon + ' ' + (isAr ? a.msg : a.msg_en) + '</div>';
        }).join('');
    }

    // ── Cash Detail ─────────────────────────────────────────────────────
    function renderCashDetail(kpi) {
        var el = document.getElementById('db-cash-detail');
        if (!el) return;
        el.innerHTML =
            '<div style="text-align:center;margin-bottom:14px;">' +
                '<div style="font-size:26px;font-weight:800;color:#d97706;">KD ' + fmt(kpi.cash_pending) + '</div>' +
                '<div style="font-size:11px;color:#64748b;">' + t('إجمالي الكاش المعلق', 'Total Pending Cash') + '</div>' +
            '</div>' +
            '<div class="db-cash-item" style="background:#fff5f5;">' +
                '<span>' + t('💵 محصّل — لم يُسوَّ', '💵 Collected — Not Remitted') + '</span>' +
                '<span style="font-weight:700;color:#dc2626;">KD ' + fmt(kpi.cash_pending) + '</span>' +
            '</div>' +
            '<div class="db-cash-item" style="background:#f0fdf4;">' +
                '<span>' + t('✅ تمت التسوية', '✅ Remitted') + '</span>' +
                '<span style="font-weight:700;color:#16a34a;">KD ' + fmt(kpi.cash_remitted) + '</span>' +
            '</div>' +
            '<div style="margin-top:12px;display:flex;align-items:center;justify-content:space-between;">' +
                '<div><div style="font-size:10px;color:#64748b;">' + t('طلبات تسوية معلقة', 'Pending Remittances') + '</div>' +
                '<div style="font-size:22px;font-weight:800;color:#2d6be4;">' + kpi.pending_remittances + '</div></div>' +
                '<a href="/odoo/delivery/remittances" class="db-btn db-btn-primary" style="font-size:10px;">' + t('مراجعة', 'Review') + '</a>' +
            '</div>';
    }

    function renderReturnsDetail(kpi) {
        var el = document.getElementById('db-returns-detail');
        if (!el) return;
        el.innerHTML =
            '<div class="db-cash-item" style="background:#fff5f5;">' +
                '<span>⏳ ' + t('انتظار الإرجاع', 'Awaiting Return') + '</span>' +
                '<span style="font-size:13px;font-weight:800;color:#dc2626;">' + kpi.returns_awaiting + '</span>' +
            '</div>' +
            '<div class="db-cash-item" style="background:#fffbeb;">' +
                '<span>📅 ' + t('مجدول / في الطريق', 'Scheduled / In Transit') + '</span>' +
                '<span style="font-size:13px;font-weight:800;color:#d97706;">' + kpi.returns_scheduled + '</span>' +
            '</div>' +
            '<div class="db-cash-item" style="background:#f0fdf4;">' +
                '<span>✅ ' + t('استلمها Uellow', 'Received by Uellow') + '</span>' +
                '<span style="font-size:13px;font-weight:800;color:#16a34a;">' + kpi.returns_received + '</span>' +
            '</div>';
    }

    // ── Load Dashboard ───────────────────────────────────────────────────
    function loadDashboard() {
        var period = document.getElementById('db-period');
        var carrierSel = document.getElementById('db-carrier');
        var params = {
            period: period ? period.value : '30',
            carrier_id: carrierSel ? parseInt(carrierSel.value) || 0 : 0,
        };

        var spinner = document.getElementById('db-loading');
        if (spinner) spinner.style.display = 'flex';

        jsonRpc('/delivery-portal/dashboard-data', params).then(function (data) {
            if (spinner) spinner.style.display = 'none';
            if (!data || !data.kpi) return;
            renderKPI(data.kpi);
            renderChart(data.daily_trend || []);
            renderDonut(data.kpi);
            renderCarriers(data.carriers || []);
            renderDrivers(data.drivers || []);
            renderOrders(data.recent_orders || []);
            renderAlerts(data.alerts || []);
            renderCashDetail(data.kpi);
            renderReturnsDetail(data.kpi);

            // Update timestamp
            var ts = document.getElementById('db-timestamp');
            if (ts) ts.textContent = new Date().toLocaleTimeString();
        }).catch(function (e) {
            if (spinner) spinner.style.display = 'none';
            console.error('Dashboard error:', e);
        });
    }

    // ── Init ─────────────────────────────────────────────────────────────
    function init() {
        var period = document.getElementById('db-period');
        var carrierSel = document.getElementById('db-carrier');
        var refreshBtn = document.getElementById('db-refresh');

        if (period) period.addEventListener('change', loadDashboard);
        if (carrierSel) carrierSel.addEventListener('change', loadDashboard);
        if (refreshBtn) refreshBtn.addEventListener('click', loadDashboard);

        loadDashboard();

        // Auto-refresh every 3 minutes
        setInterval(loadDashboard, 3 * 60 * 1000);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
