# -*- coding: utf-8 -*-
"""Beena Coach — live ops dashboard (findings, stats, progress), fresh on every load."""
import json
import os
import glob
from datetime import timedelta

from odoo import http, fields
from odoo.http import request

_REPORTS = '/mnt/uellowcom/beena_coach/reports'
_STATUS = '/mnt/uellowcom/beena_coach/status'


class BeenaCoachLive(http.Controller):

    def _ok(self, k):
        key = request.env['ir.config_parameter'].sudo().get_param(
            'uellow_ai.coach_dashboard_key', '')
        return bool(key) and k == key

    @http.route('/beena/coach/stats', type='http', auth='public', csrf=False)
    def stats(self, k='', **kw):
        if not self._ok(k):
            return request.make_response('forbidden', status=403)
        env = request.env
        now = fields.Datetime.now()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        wk = now - timedelta(days=7)
        wk2 = now - timedelta(days=14)

        def cnt(model, domain):
            m = env.get(model)
            try:
                return m.sudo().search_count(domain) if m is not None else 0
            except Exception:
                return 0

        def grp(model, field):
            out, m = {}, env.get(model)
            if m is None:
                return out
            try:
                for g in m.sudo().read_group([], [field], [field]):
                    key = g.get(field)
                    if isinstance(key, (list, tuple)):
                        key = key[1] if len(key) > 1 else key[0]
                    out[str(key or 'none')] = g.get('%s_count' % field, 0)
            except Exception:
                pass
            return out

        def summ(model, field, domain=None):
            m = env.get(model)
            if m is None:
                return 0.0
            try:
                g = m.sudo().read_group(domain or [], [field + ':sum'], [])
                return round((g[0].get(field) or 0.0), 4) if g else 0.0
            except Exception:
                return 0.0

        total = cnt('beena.coach.finding', [])
        applied = cnt('beena.coach.finding', [('state', '=', 'applied')])
        open_high = cnt('beena.coach.finding',
                        [('severity', 'in', ('high', 'critical')),
                         ('state', 'in', ('new', 'approved'))])
        new_wk = cnt('beena.coach.finding', [('create_date', '>=', wk)])
        new_prev = cnt('beena.coach.finding',
                       [('create_date', '>=', wk2), ('create_date', '<', wk)])
        fixed_wk = cnt('beena.coach.finding',
                       [('state', '=', 'applied'), ('write_date', '>=', wk)])

        resolution = round(100.0 * applied / total, 1) if total else 100.0
        # Robustness 0-100 = the honest resolution rate (share of all findings
        # that are fixed/applied). open_high is surfaced as its own KPI rather
        # than double-penalising here (unresolved items already lower resolution).
        robustness = max(0, min(100, int(round(resolution))))
        # progress: fewer NEW defects this week than last = improving
        if new_prev == 0:
            trend = 'up' if new_wk == 0 else 'flat'
        elif new_wk < new_prev:
            trend = 'up'
        elif new_wk > new_prev:
            trend = 'down'
        else:
            trend = 'flat'
        trend_pct = 0
        if new_prev:
            trend_pct = int(round(100.0 * (new_prev - new_wk) / new_prev))

        # per-day (last 14d)
        per_day = []
        F = env.get('beena.coach.finding')
        if F is not None:
            try:
                for g in F.sudo().read_group(
                        [('create_date', '>=', wk2)], ['create_date'],
                        ['create_date:day']):
                    per_day.append({'d': str(g.get('create_date:day') or '')[:11],
                                    'n': g.get('create_date_count', 0)})
            except Exception:
                pass

        recent = []
        if F is not None:
            try:
                for f in F.sudo().search([], order='id desc', limit=15):
                    recent.append({'title': (f.title or '')[:95],
                                   'severity': f.severity or 'medium',
                                   'category': f.category or 'other',
                                   'state': f.state or 'new',
                                   'date': str(f.create_date)[:16]})
            except Exception:
                pass

        # running status + last report
        running, run_ts = False, ''
        try:
            with open(_STATUS, encoding='utf-8') as fh:
                st = fh.read().strip().split('|')
                running = st[0] == 'running'
                run_ts = st[1] if len(st) > 1 else ''
        except Exception:
            pass
        last_report = {'name': None, 'text': ''}
        try:
            files = sorted(glob.glob(os.path.join(_REPORTS, '*.md')))
            if files:
                last_report['name'] = os.path.basename(files[-1])
                with open(files[-1], encoding='utf-8') as fh:
                    last_report['text'] = fh.read()[:6000]
        except Exception:
            pass

        data = {
            'ts': str(now)[:19],
            'running': running, 'run_ts': run_ts,
            'robustness': robustness, 'resolution': resolution,
            'trend': trend, 'trend_pct': trend_pct,
            'new_wk': new_wk, 'new_prev': new_prev, 'fixed_wk': fixed_wk,
            'findings_total': total, 'applied_total': applied,
            'applied_today': cnt('beena.coach.finding',
                                 [('state', '=', 'applied'), ('write_date', '>=', today)]),
            'open_high': open_high,
            'by_severity': grp('beena.coach.finding', 'severity'),
            'by_category': grp('beena.coach.finding', 'category'),
            'by_state': grp('beena.coach.finding', 'state'),
            'per_day': per_day, 'recent': recent,
            'runs_total': cnt('beena.coach.run', []),
            'scenarios': cnt('beena.coach.scenario', []),
            'lessons_len': len(env['ir.config_parameter'].sudo().get_param(
                'uellow_ai.learned_lessons', '') or ''),
            'beena_conversations': cnt('beena.conversation', []),
            'beena_messages': cnt('beena.message', []),
            'cost_today': summ('beena.message', 'cost', [('create_date', '>=', today)]),
            'cost_total': summ('beena.message', 'cost'),
            'last_report': last_report,
        }
        return request.make_response(
            json.dumps(data, ensure_ascii=False, default=str),
            headers=[('Content-Type', 'application/json; charset=utf-8'),
                     ('Cache-Control', 'no-store')])

    @http.route('/beena/coach/live', type='http', auth='public', csrf=False)
    def live(self, k='', **kw):
        if not self._ok(k):
            return request.make_response('forbidden', status=403)
        return request.make_response(_PAGE.replace('__K__', k),
                                     headers=[('Content-Type', 'text/html; charset=utf-8')])


_PAGE = r"""<!doctype html><html lang="ar" dir="rtl"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Beena Coach — Live</title>
<style>
:root{--bg:#0f1613;--card:#16211c;--line:#26332c;--ink:#e8f0ec;--mut:#8fa39a;--teal:#3ecf8e;--amber:#f0b429;--red:#f2545b;--blue:#4c9ffe}
@media(prefers-color-scheme:light){:root{--bg:#eef2f1;--card:#fff;--line:#e2e8e5;--ink:#1f3a35;--mut:#67807a}}
*{box-sizing:border-box}body{margin:0;font-family:'Segoe UI',Tahoma,Arial,sans-serif;background:var(--bg);color:var(--ink)}
.top{display:flex;align-items:center;gap:12px;padding:15px 22px;border-bottom:1px solid var(--line);position:sticky;top:0;background:var(--bg);z-index:5}
.dot{width:38px;height:38px;border-radius:11px;background:var(--teal);color:#04120b;display:flex;align-items:center;justify-content:center;font-size:20px;font-weight:800}
h1{font-size:16px;margin:0}.sub{font-size:12px;color:var(--mut)}
.live{margin-inline-start:auto;font-size:12px;font-weight:700;padding:5px 12px;border-radius:20px}
.on{background:rgba(62,207,142,.15);color:var(--teal)}.off{background:rgba(143,163,154,.15);color:var(--mut)}
.wrap{padding:20px;max-width:1200px;margin:0 auto}
.hero{display:grid;grid-template-columns:220px 1fr;gap:16px;margin-bottom:16px}@media(max-width:720px){.hero{grid-template-columns:1fr}}
.gauge{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:18px;text-align:center}
.ring{--p:0;width:150px;height:150px;border-radius:50%;margin:6px auto;background:conic-gradient(var(--teal) calc(var(--p)*1%),var(--line) 0);display:flex;align-items:center;justify-content:center}
.ring .in{width:116px;height:116px;border-radius:50%;background:var(--card);display:flex;flex-direction:column;align-items:center;justify-content:center}
.ring .n{font-size:34px;font-weight:800}.ring .t{font-size:11px;color:var(--mut)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:12px}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:13px}
.kpi .l{font-size:11px;color:var(--mut)}.kpi .v{font-size:23px;font-weight:800;margin-top:5px}.kpi .u{font-size:11px;color:var(--mut)}
.row{display:grid;grid-template-columns:1fr 1fr;gap:14px}@media(max-width:800px){.row{grid-template-columns:1fr}}
.panel{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px;margin-bottom:14px}
.panel h3{margin:0 0 12px;font-size:14px}
.bar{display:flex;height:14px;border-radius:8px;overflow:hidden;margin:8px 0}
.lg{display:flex;gap:14px;flex-wrap:wrap;font-size:12px;color:var(--mut)}
.lg i{width:10px;height:10px;border-radius:3px;display:inline-block;margin-inline-end:5px}
table{width:100%;border-collapse:collapse;font-size:12.5px}
td,th{padding:7px 8px;border-bottom:1px solid var(--line);text-align:right}
th{color:var(--mut);font-weight:600;font-size:11px}
.pill{padding:2px 8px;border-radius:20px;font-size:10.5px;font-weight:700;color:#04120b}
.spark{display:flex;align-items:flex-end;gap:3px;height:60px}.spark b{flex:1;background:var(--blue);border-radius:3px 3px 0 0;min-height:2px}
.rep{white-space:pre-wrap;font-size:12px;line-height:1.7;max-height:340px;overflow:auto;background:var(--bg);border-radius:10px;padding:12px;border:1px solid var(--line)}
.trend{font-size:13px;font-weight:700}.tu{color:var(--teal)}.td{color:var(--red)}.tf{color:var(--mut)}
.upd{font-size:11px;color:var(--mut)}
</style></head><body>
<div class="top"><div class="dot">🐝</div>
 <div><h1>Beena Coach — لوحة التطوّر والأخطاء الحيّة</h1><div class="sub">تتحدّث مع كل refresh · <span class="upd" id="upd">…</span></div></div>
 <div class="live off" id="live">…</div></div>
<div class="wrap">
 <div class="hero">
  <div class="gauge"><div class="ring" id="ring"><div class="in"><div class="n" id="rob">–</div><div class="t">متانة بينا</div></div></div>
   <div class="trend" id="trend">…</div></div>
  <div class="grid" id="kpis"></div>
 </div>
 <div class="row">
   <div class="panel"><h3>الأخطاء حسب الخطورة</h3><div class="bar" id="sevbar"></div><div class="lg" id="sevlg"></div>
     <h3 style="margin-top:16px">حسب الحالة</h3><div id="statebox" class="lg"></div></div>
   <div class="panel"><h3>أخطاء مكتشفة يومياً (14 يوم) — الاتجاه للأسفل = تحسّن</h3><div class="spark" id="spark"></div>
     <h3 style="margin-top:16px">حسب الفئة</h3><div id="catbox" class="lg"></div></div>
 </div>
 <div class="panel"><h3>أحدث الأخطاء</h3><table id="rtab"><thead><tr><th>العنوان</th><th>الخطورة</th><th>الفئة</th><th>الحالة</th><th>التاريخ</th></tr></thead><tbody></tbody></table></div>
 <div class="panel"><h3>آخر تقرير يومي <span class="upd" id="repname"></span></h3><div class="rep" id="rep">…</div></div>
</div>
<script>
const K="__K__";
const SEV={critical:'var(--red)',high:'#ff7a45',medium:'var(--amber)',low:'var(--blue)'};
const STC={applied:'var(--teal)',approved:'var(--blue)',new:'var(--amber)',dismissed:'var(--mut)'};
function kpi(l,v,u){return `<div class="kpi"><div class="l">${l}</div><div class="v">${v} <span class="u">${u||''}</span></div></div>`}
async function load(){
 try{
  const d=await(await fetch('/beena/coach/stats?k='+encodeURIComponent(K)+'&_='+Date.now())).json();
  document.getElementById('upd').textContent='آخر تحديث: '+d.ts;
  const lv=document.getElementById('live');
  lv.className='live '+(d.running?'on':'off');
  lv.textContent=d.running?'● تعمل الآن':'○ خاملة — الجولة القادمة 4 ص';
  // gauge
  const ring=document.getElementById('ring'); ring.style.setProperty('--p',d.robustness);
  document.getElementById('rob').textContent=d.robustness;
  const t=document.getElementById('trend');
  const tc=d.trend=='up'?'tu':(d.trend=='down'?'td':'tf');
  const tw=d.trend=='up'?'▲ في تقدّم':(d.trend=='down'?'▼ أخطاء أكثر':'■ ثابت');
  t.className='trend '+tc;
  t.innerHTML=tw+`<div class="upd">أخطاء جديدة هذا الأسبوع ${d.new_wk} مقابل ${d.new_prev} السابق · نسبة الإصلاح ${d.resolution}%</div>`;
  document.getElementById('kpis').innerHTML=[
   kpi('إجمالي الأخطاء',d.findings_total,''),
   kpi('تم إصلاحها',d.applied_total,''),
   kpi('أُصلحت اليوم',d.applied_today,''),
   kpi('حرجة/عالية مفتوحة',d.open_high,''),
   kpi('أُصلح هذا الأسبوع',d.fixed_wk,''),
   kpi('جولات الكوتش',d.runs_total,''),
   kpi('دروس بينا',d.lessons_len,'حرف'),
   kpi('تكلفة اليوم',(d.cost_today||0).toFixed(3),'$'),
  ].join('');
  const sv=d.by_severity||{},o=['critical','high','medium','low'],svt=o.reduce((a,s)=>a+(sv[s]||0),0)||1;
  document.getElementById('sevbar').innerHTML=o.map(s=>`<span style="width:${100*(sv[s]||0)/svt}%;background:${SEV[s]}"></span>`).join('');
  document.getElementById('sevlg').innerHTML=o.map(s=>`<span><i style="background:${SEV[s]}"></i>${s}: ${sv[s]||0}</span>`).join('');
  const st=d.by_state||{};
  document.getElementById('statebox').innerHTML=Object.keys(st).map(s=>`<span><i style="background:${STC[s]||'var(--mut)'}"></i>${s}: ${st[s]}</span>`).join('')||'—';
  const ct=d.by_category||{};
  document.getElementById('catbox').innerHTML=Object.keys(ct).map(c=>`<span><i style="background:var(--teal)"></i>${c}: ${ct[c]}</span>`).join('')||'—';
  const pd=d.per_day||[],mx=Math.max(1,...pd.map(x=>x.n));
  document.getElementById('spark').innerHTML=pd.map(x=>`<b title="${x.d}: ${x.n}" style="height:${100*x.n/mx}%"></b>`).join('')||'<span style="color:var(--mut)">لا بيانات</span>';
  document.querySelector('#rtab tbody').innerHTML=(d.recent||[]).map(f=>`<tr><td>${f.title}</td>
   <td><span class="pill" style="background:${SEV[f.severity]||'var(--mut)'}">${f.severity}</span></td>
   <td>${f.category}</td><td><span class="pill" style="background:${STC[f.state]||'var(--mut)'}">${f.state}</span></td><td>${f.date}</td></tr>`).join('')
   ||'<tr><td colspan=5 style="color:var(--mut)">لا أخطاء بعد</td></tr>';
  document.getElementById('repname').textContent=d.last_report&&d.last_report.name?('· '+d.last_report.name):'(لم يصدر بعد)';
  document.getElementById('rep').textContent=(d.last_report&&d.last_report.text)||'أول تقرير سيظهر بعد أول جولة كوتش.';
 }catch(e){document.getElementById('upd').textContent='خطأ: '+e}
}
load(); setInterval(load,20000);
</script></body></html>"""
