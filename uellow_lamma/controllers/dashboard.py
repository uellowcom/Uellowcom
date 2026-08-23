# -*- coding: utf-8 -*-
import html as _h
from odoo import http
from odoo.http import request


def esc(s):
    return _h.escape(str(s if s is not None else ''))


def _kpi(label, value, sub='', accent='o'):
    return (
        '<div class="kpi kpi-%s"><div class="v">%s</div>'
        '<div class="l">%s</div>%s</div>'
        % (accent, esc(value), esc(label),
           ('<div class="s">%s</div>' % esc(sub)) if sub else ''))


def _trend_svg(trend):
    if not trend:
        return '<div class="empty">لا توجد بيانات بعد</div>'
    maxv = max([max(r['adds'], r['checkouts']) for r in trend] + [1])
    W, H, pad = 620, 180, 26
    n = len(trend)
    gw = (W - pad * 2) / max(n, 1)
    bars, labels = '', ''
    for i, r in enumerate(trend):
        x = pad + i * gw
        ah = (r['adds'] / maxv) * (H - 40)
        ch = (r['checkouts'] / maxv) * (H - 40)
        bw = min(gw / 2 - 3, 14)
        bars += ('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="3" fill="#FBBF00"/>'
                 % (x + gw / 2 - bw - 2, H - 22 - ah, bw, ah))
        bars += ('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="3" fill="#F26A2E"/>'
                 % (x + gw / 2 + 2, H - 22 - ch, bw, ch))
        if n <= 16:
            labels += ('<text x="%.1f" y="%d" text-anchor="middle" font-size="9" fill="#98a2b3">%s</text>'
                       % (x + gw / 2, H - 6, esc(r['d'])))
    return ('<svg viewBox="0 0 %d %d" class="chart">%s%s</svg>'
            '<div class="legend"><span><i style="background:#FBBF00"></i>إضافات</span>'
            '<span><i style="background:#F26A2E"></i>إتمامات</span></div>'
            % (W, H, bars, labels))


def _hbars(rows, key_label, key_val, color='#F26A2E'):
    if not rows:
        return '<div class="empty">—</div>'
    maxv = max([r[key_val] for r in rows] + [1])
    out = ''
    for r in rows:
        w = r[key_val] / maxv * 100
        img = ('<img src="%s" onerror="this.style.display=\'none\'"/>' % esc(r['image'])) if r.get('image') else ''
        out += ('<div class="hb">%s<div class="hb-main"><div class="hb-top">'
                '<span class="hb-n">%s</span><b>%s</b></div>'
                '<div class="hb-bar"><i style="width:%.0f%%;background:%s"></i></div></div></div>'
                % (img, esc(r[key_label]), esc(r[key_val]), w, color))
    return out


def _split(rows, kmap):
    if not rows:
        return '<div class="empty">—</div>'
    tot = sum(r['c'] for r in rows) or 1
    out = ''
    for r in rows:
        k = list(r.values())[0]
        c = r['c']
        out += ('<div class="hb"><div class="hb-main"><div class="hb-top">'
                '<span class="hb-n">%s</span><b>%s (%.0f%%)</b></div>'
                '<div class="hb-bar"><i style="width:%.0f%%"></i></div></div></div>'
                % (esc(kmap.get(k, k)), c, c / tot * 100, c / tot * 100))
    return out


def _recent(recent):
    if not recent:
        return '<tr><td colspan="6" class="empty">لا يوجد نشاط بعد</td></tr>'
    badge = {'checkout': 'ok', 'add': 'info', 'start': 'info', 'remove': 'warn', 'clear': 'mut', 'type': 'mut'}
    out = ''
    for r in recent:
        out += ('<tr><td class="mut">%s %s</td>'
                '<td><span class="tag tag-%s">%s</span></td>'
                '<td>%s</td><td>%s</td><td>%s</td><td class="mut">%s %s</td></tr>'
                % (esc(r['date']), esc(r['when']), badge.get(r['code'], 'mut'), esc(r['action']),
                   esc(r['product'] or '—'), esc(r['items'] or 0),
                   esc(r['source']), esc('· ' + r['country'] if r['country'] else ''), ''))
    return out


def _period(active):
    out = ''
    for n in (7, 30, 90):
        out += ('<a class="pb%s" href="/lamma/dashboard?days=%d&embed=1">%d يوم</a>'
                % (' on' if n == active else '', n, n))
    return out


def render_dashboard(d):
    k = d['kpis']
    cur = d['currency']
    pbtns = _period(d['days'])
    countries = _split(
        [{'v': r['cc'], 'c': r['c']} for r in d.get('top_countries', [])],
        {}) if d.get('top_countries') else '<div class="empty">—</div>'
    cards = ''.join([
        _kpi('لمّة بدأت (30ي)', k['bundles'], accent='o'),
        _kpi('أتمّوا اللمّة', k['checkouts'], accent='ok'),
        _kpi('معدل التحويل', '%s%%' % k['conversion_rate'], accent='blue'),
        _kpi('الخصم المصروف', '%s %s' % (k['discount_sum'], cur), accent='o'),
        _kpi('متوسط المنتجات', k['avg_items'], accent='vio'),
        _kpi('حصة الأقساط', ('%.0f%%' % (k['inst_checkouts'] / k['checkouts'] * 100)) if k['checkouts'] else '0%', accent='vio'),
        _kpi('قيمة اللمّات', '%s %s' % (d.get('total_value', 0), cur), accent='ok'),
        _kpi('متوسط قيمة اللمّة', '%s %s' % (d.get('avg_value', 0), cur), accent='blue'),
        _kpi('لمّات مهجورة', d.get('abandoned', 0), 'بدأت ولم تُتمّ', accent='warn'),
        _kpi('إضافات', k['adds'], accent='ok'),
        _kpi('إزالات', k['removes'], accent='warn'),
    ])
    return CSS + (
        '<div class="wrap">'
        '<div class="hd"><div><h1>🧺 لوحة تحكّم لمّة يلو</h1>'
        '<p>ملخّص آخر %d يوم — تحديث لحظي</p></div>'
        '<div class="hd-actions">%s<a class="ref" href="/lamma/dashboard?days=%d&embed=1">↻ تحديث</a></div></div>'
        '<div class="kpis">%s</div>'
        '<div class="grid2">'
        '<div class="card"><h3>النشاط اليومي (14 يوم)</h3>%s</div>'
        '<div class="card"><h3>قمع التحويل</h3>%s</div>'
        '</div>'
        '<div class="grid2">'
        '<div class="card"><h3>حسب المصدر</h3>%s</div>'
        '<div class="card"><h3>نوع اللمّة (الإتمامات)</h3>%s</div>'
        '</div>'
        '<div class="grid2">'
        '<div class="card"><h3>🔝 الأكثر إضافةً للّمّة</h3><div class="hbs">%s</div></div>'
        '<div class="card"><h3>🗑️ الأكثر إزالةً</h3><div class="hbs">%s</div></div>'
        '</div>'
        '<div class="grid2">'
        '<div class="card"><h3>🌍 أكثر الدول تفاعلاً</h3>%s</div>'
        '<div class="card"><h3>💡 فرصة إعادة استهداف</h3>'
        '<div class="note">اللمّات المهجورة (بدأت ولم تُتمّ) عملاء أبدوا اهتماماً — تابعهم من «نشاط العملاء» لإعادة استهدافهم.</div></div>'
        '</div>'
        '<div class="card"><h3>🕒 نشاط مباشر</h3>'
        '<table class="rt"><thead><tr><th>الوقت</th><th>الحدث</th><th>المنتج</th><th>عدد</th><th>المصدر/الدولة</th><th></th></tr></thead>'
        '<tbody>%s</tbody></table></div>'
        '<div class="foot">لمّة يلو · Uellow 🐝</div>'
        '</div>'
        % (d['days'], pbtns, d['days'], cards,
           _trend_svg(d['trend']),
           _funnel(k),
           _split(d['sources'], {'web': 'الموقع', 'app': 'التطبيق'}),
           _split(d['types'], {'normal': 'عادي', 'installment': 'أقساط'}),
           _hbars(d['top_added'], 'name', 'count', '#12b76a'),
           _hbars(d['top_removed'], 'name', 'count', '#f04438'),
           countries,
           _recent(d['recent'])))


def _funnel(k):
    stages = [('لمّات بدأت', k['bundles'], '#FBBF00'),
              ('أتمّوا', k['checkouts'], '#F26A2E')]
    maxv = max([s[1] for s in stages] + [1])
    out = ''
    for name, val, col in stages:
        out += ('<div class="fn"><div class="fn-top"><span>%s</span><b>%s</b></div>'
                '<div class="fn-bar"><i style="width:%.0f%%;background:%s"></i></div></div>'
                % (esc(name), esc(val), val / maxv * 100, col))
    out += ('<div class="fn-rate">معدل التحويل: <b>%s%%</b></div>' % esc(k['conversion_rate']))
    return out


CSS = '''<meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>لوحة تحكّم لمّة يلو</title><style>
*{box-sizing:border-box}body{margin:0;background:#f5f6f8;color:#101828;font-family:"Tajawal","Segoe UI",system-ui,Arial,sans-serif;direction:rtl}
.wrap{max-width:1160px;margin:0 auto;padding:24px 18px 60px}
.hd{display:flex;align-items:center;justify-content:space-between;margin-bottom:18px}
.hd h1{margin:0;font-size:1.5rem;font-weight:900}
.hd p{margin:3px 0 0;color:#667085;font-size:.9rem}
.ref{background:linear-gradient(135deg,#FBBF00,#F26A2E);color:#1a1200;text-decoration:none;font-weight:800;padding:9px 16px;border-radius:11px;font-size:.9rem}
.hd-actions{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.pb{background:#fff;border:1px solid #eceff3;color:#667085;text-decoration:none;font-weight:700;padding:8px 12px;border-radius:10px;font-size:.82rem}
.pb.on{background:#101828;color:#fff;border-color:#101828}
.note{color:#8a6d1a;font-size:.9rem;line-height:1.7;background:#fffaeb;border:1px solid #fde68a;border-radius:12px;padding:12px 14px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:18px}
.kpi{background:#fff;border:1px solid #eceff3;border-radius:16px;padding:15px 16px;box-shadow:0 1px 3px rgba(16,24,40,.05);position:relative;overflow:hidden}
.kpi::before{content:"";position:absolute;top:0;right:0;width:5px;height:100%;background:#F26A2E}
.kpi.kpi-ok::before{background:#12b76a}.kpi.kpi-blue::before{background:#2e90fa}.kpi.kpi-vio::before{background:#7a5af8}.kpi.kpi-warn::before{background:#f79009}
.kpi .v{font-size:1.7rem;font-weight:900;line-height:1;font-variant-numeric:tabular-nums}
.kpi .l{color:#667085;font-size:.82rem;margin-top:5px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px}
@media(max-width:820px){.grid2{grid-template-columns:1fr}}
.card{background:#fff;border:1px solid #eceff3;border-radius:16px;padding:16px 18px;box-shadow:0 1px 3px rgba(16,24,40,.05)}
.card h3{margin:0 0 14px;font-size:1rem;font-weight:800}
.chart{width:100%;height:auto}
.legend{display:flex;gap:16px;margin-top:8px;font-size:.78rem;color:#667085;justify-content:center}
.legend span{display:inline-flex;align-items:center;gap:6px}.legend i{width:11px;height:11px;border-radius:3px}
.hbs{display:flex;flex-direction:column;gap:11px}
.hb{display:flex;align-items:center;gap:10px}
.hb img{width:34px;height:34px;border-radius:8px;object-fit:cover;background:#f0f2f5;flex:0 0 auto}
.hb-main{flex:1;min-width:0}
.hb-top{display:flex;justify-content:space-between;font-size:.82rem;margin-bottom:4px}
.hb-n{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:76%;color:#344054;font-weight:600}
.hb-top b{font-variant-numeric:tabular-nums}
.hb-bar{height:8px;background:#f0f2f5;border-radius:99px;overflow:hidden}
.hb-bar i{display:block;height:100%;background:#F26A2E;border-radius:99px}
.fn{margin-bottom:12px}.fn-top{display:flex;justify-content:space-between;font-size:.88rem;font-weight:700;margin-bottom:5px}
.fn-bar{height:26px;background:#f0f2f5;border-radius:8px;overflow:hidden}.fn-bar i{display:block;height:100%;border-radius:8px}
.fn-rate{margin-top:10px;font-size:.9rem;color:#667085}.fn-rate b{color:#12b76a;font-size:1.1rem}
.rt{width:100%;border-collapse:collapse;font-size:.84rem}
.rt th{text-align:right;color:#98a2b3;font-weight:700;padding:7px 8px;border-bottom:2px solid #f0f2f5;font-size:.76rem}
.rt td{padding:8px;border-bottom:1px solid #f5f6f8}
.rt .mut{color:#98a2b3;font-variant-numeric:tabular-nums}
.tag{font-size:.72rem;font-weight:800;padding:2px 9px;border-radius:99px}
.tag-ok{background:#ecfdf3;color:#067647}.tag-info{background:#eff8ff;color:#175cd3}.tag-warn{background:#fffaeb;color:#b54708}.tag-mut{background:#f2f4f7;color:#667085}
.empty{color:#98a2b3;text-align:center;padding:20px;font-size:.9rem}
.foot{text-align:center;color:#98a2b3;font-size:.8rem;margin-top:26px}
</style>'''


class LammaDashboardController(http.Controller):

    @http.route('/lamma/dashboard', type='http', auth='user')
    def dashboard(self, days=30, **kw):
        # Keep the Odoo top navbar: a TOP-LEVEL direct hit is bounced into the
        # backend action; a hit that is already inside a frame (the embed iframe,
        # even if an old cached asset dropped the embed flag) just renders with
        # embed=1 — so there is never a redirect loop / flashing navbar.
        if not kw.get('embed'):
            _d = int(days) if str(days).isdigit() else 30
            html = (
                '<!DOCTYPE html><meta charset="utf-8">'
                '<body style="margin:0;background:#f6f3ec"><script>'
                'if(window.top===window.self){'
                'location.replace("/odoo/action-uellow_lamma.action_lamma_dashboard_ui");'
                '}else{location.replace("/lamma/dashboard?embed=1&days=' + str(_d) + '");}'
                '</script></body>')
            return request.make_response(html, headers=[
                ('Content-Type', 'text/html; charset=utf-8'),
                ('Cache-Control', 'no-store')])
        data = request.env['uellow.lamma.activity'].sudo().dashboard_data(days)
        body = render_dashboard(data)
        return request.make_response(body, headers=[('Content-Type', 'text/html; charset=utf-8')])
