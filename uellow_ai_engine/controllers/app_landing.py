# -*- coding: utf-8 -*-
# Public app landing page at /app + backend KPI dashboard at /app/dashboard.
#   - /app             creative page + auto-redirect by device; logs a "visit"
#   - /app/go/<store>  logs a "conversion" then redirects to the store
#   - /app/dashboard   professional KPI dashboard (admin only)
# Links/toggles are configurable from the backend (Beena settings → "App page").
# Raw events live in the backend model uellow.app.visit.
# NOTE: in controllers `fields` is NOT imported — use datetime.now().
import hashlib
import json

from odoo import http
from odoo.http import request

_DEFAULTS = {
    'app_url_appstore': 'https://apps.apple.com/app/id6769010765',
    'app_url_play': 'https://play.google.com/store/apps/details?id=com.uellow.app',
    'app_url_huawei': 'https://github.com/uellowcom/uellow-app/releases/download/v2.2.39/uellow-2.2.39-arm64-v8a.apk',
    'app_icon_url': 'https://www.uellow.com/uellow_smart_connector/static/mockup/uellow-ios-icon-1024.png',
    'app_screenshot_url': 'https://www.uellow.com/uellow_smart_connector/static/mockup/appstore/iphone_4.png',
}
_COUNTRY_AR = {
    'KW': 'الكويت', 'SA': 'السعودية', 'AE': 'الإمارات', 'QA': 'قطر',
    'BH': 'البحرين', 'OM': 'عُمان', 'EG': 'مصر', 'JO': 'الأردن',
    'IQ': 'العراق', 'LB': 'لبنان', 'US': 'United States', 'GB': 'United Kingdom',
}


class AppLanding(http.Controller):

    # ── helpers ───────────────────────────────────────────
    def _cfg(self, key, default=''):
        return request.env['ir.config_parameter'].sudo().get_param('uellow_ai.' + key, default)

    def _bool(self, key, default=True):
        return self._cfg(key, 'True' if default else 'False') in ('True', '1', 'true', True)

    def _store_url(self, store):
        return self._cfg('app_url_' + store, _DEFAULTS.get('app_url_' + store, '/app'))

    def _platform(self):
        ua = (request.httprequest.user_agent.string or '').lower()
        if any(k in ua for k in ('iphone', 'ipad', 'ipod')):
            return 'ios'
        if any(k in ua for k in ('huawei', 'honor', 'hms', 'harmonyos')):
            return 'huawei'
        if 'android' in ua:
            return 'android'
        if any(k in ua for k in ('windows', 'macintosh', 'linux x86', 'cros')):
            return 'desktop'
        return 'other'

    def _country(self):
        h = request.httprequest.headers
        code = (h.get('CF-IPCountry') or h.get('X-Country-Code') or '').upper()
        if not code or code == 'XX':
            try:
                code = (request.geoip.get('country_code') or '').upper()
            except Exception:
                code = ''
        return code, _COUNTRY_AR.get(code, code)

    def _ip_hash(self):
        ip = request.httprequest.remote_addr or ''
        return hashlib.sha256(('uellow-app-salt:' + ip).encode()).hexdigest()[:16]

    def _log(self, action, platform, store=False):
        code, name = self._country()
        try:
            request.env['uellow.app.visit'].sudo().create({
                'action': action, 'platform': platform, 'store': store,
                'country_code': code or False, 'country_name': name or False,
                'user_agent': (request.httprequest.user_agent.string or '')[:300],
                'referrer': (request.httprequest.referrer or '')[:300],
                'ip_hash': self._ip_hash(),
            })
            request.env.cr.commit()
        except Exception:
            request.env.cr.rollback()

    # ── public routes ─────────────────────────────────────
    @http.route('/app', type='http', auth='public', website=False, csrf=False, sitemap=False)
    def app_landing(self, **kw):
        self._log('visit', self._platform())
        return request.make_response(self._render(), headers=[('Content-Type', 'text/html; charset=utf-8')])

    @http.route('/app/go/<string:store>', type='http', auth='public', website=False, csrf=False, sitemap=False)
    def app_go(self, store, **kw):
        if store not in ('appstore', 'play', 'huawei'):
            return request.redirect('/app')
        self._log('conversion', self._platform(), store=store)
        url = self._store_url(store)
        # v2.2.43 — on Android, open the Play Store APP (market://) instead of
        # the web page; the browser hands market:// to the Play app.
        if store == 'play' and self._platform() == 'android':
            url = 'market://details?id=' + self._cfg(
                'app_android_package', 'com.uellow.app')
        # Manual 302 so the exact URL is preserved (request.redirect/werkzeug
        # normalizes "market://details?id=" into "market://details/?id=" which
        # the Play app may not parse).
        return request.make_response('', status=302, headers=[('Location', url)])

    # ── landing page ──────────────────────────────────────
    def _render(self):
        badges = ''
        if self._bool('app_appstore_enabled', True):
            badges += _BADGE_APPSTORE
        if self._bool('app_play_enabled', True):
            badges += _BADGE_PLAY
        if self._bool('app_huawei_enabled', True):
            badges += _BADGE_HUAWEI
        return _PAGE % {
            'icon': self._cfg('app_icon_url', _DEFAULTS['app_icon_url']),
            'shot': self._cfg('app_screenshot_url', _DEFAULTS['app_screenshot_url']),
            'badges': badges,
            'auto': '1' if self._bool('app_auto_redirect', True) else '0',
            'openapp': '1' if self._bool('app_open_in_app', False) else '0',
            'deeplink': self._cfg('app_deeplink', 'uellow://home'),
            'pkg': self._cfg('app_android_package', 'com.uellow.app'),
        }

    # ── backend KPI dashboard ─────────────────────────────
    @http.route('/app/dashboard', type='http', auth='user', website=False, sitemap=False)
    def app_dashboard(self, **kw):
        if not request.env.user._is_admin() and not request.env.user.has_group('base.group_system'):
            return request.redirect('/web/login')
        cr = request.env.cr

        def rows(q):
            cr.execute(q)
            return cr.fetchall()

        total_visits = rows("SELECT count(*) FROM uellow_app_visit WHERE action='visit'")[0][0]
        total_conv = rows("SELECT count(*) FROM uellow_app_visit WHERE action='conversion'")[0][0]
        rate = round(100.0 * total_conv / total_visits, 1) if total_visits else 0.0
        by_plat = rows("SELECT coalesce(platform,'other'), count(*) FROM uellow_app_visit WHERE action='visit' GROUP BY 1 ORDER BY 2 DESC")
        by_store = rows("SELECT store, count(*) FROM uellow_app_visit WHERE action='conversion' AND store IS NOT NULL GROUP BY 1 ORDER BY 2 DESC")
        by_country = rows("SELECT coalesce(nullif(country_name,''),'—'), count(*) FROM uellow_app_visit WHERE action='visit' GROUP BY 1 ORDER BY 2 DESC LIMIT 8")
        trend = rows("""SELECT to_char(create_date,'MM-DD') d,
                          count(*) FILTER (WHERE action='visit') v,
                          count(*) FILTER (WHERE action='conversion') c
                        FROM uellow_app_visit
                        WHERE create_date >= (now() - interval '13 days')
                        GROUP BY 1 ORDER BY 1""")
        top_country = by_country[0][0] if by_country else '—'
        top_plat = by_plat[0][0] if by_plat else '—'
        data = {
            'visits': total_visits, 'conv': total_conv, 'rate': rate,
            'top_country': top_country, 'top_plat': top_plat,
            'plat_labels': [p[0] for p in by_plat], 'plat_vals': [p[1] for p in by_plat],
            'store_labels': [s[0] for s in by_store], 'store_vals': [s[1] for s in by_store],
            'ctry_labels': [c[0] for c in by_country], 'ctry_vals': [c[1] for c in by_country],
            'trend_labels': [t[0] for t in trend], 'trend_v': [t[1] for t in trend], 'trend_c': [t[2] for t in trend],
        }
        return request.make_response(
            _DASH % {'data': json.dumps(data)},
            headers=[('Content-Type', 'text/html; charset=utf-8')])


# ════════════════════ official-style store badges ════════════════════
_BTN = 'https://www.uellow.com/uellow_smart_connector/static/mockup/'
_BADGE_APPSTORE = ('\n     <a class="badge" href="/app/go/appstore">'
                   '<img src="%sbtn_appstore.png" alt="Download on the App Store"/></a>' % _BTN)
_BADGE_PLAY = ('\n     <a class="badge" href="/app/go/play">'
               '<img src="%sbtn_play.png" alt="Get it on Google Play"/></a>' % _BTN)
_BADGE_HUAWEI = ('\n     <a class="badge" href="/app/go/huawei">'
                 '<img src="%sbtn_huawei.png" alt="Explore it on AppGallery"/></a>' % _BTN)

# ════════════════════ landing page (yellow + phone mockup) ════════════════════
_PAGE = """<!DOCTYPE html>
<html lang="ar" dir="rtl"><head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>تطبيق يلو دوت كوم | Uellow.com App — تسوّق أونلاين بالكويت</title>
<meta name="description" content="حمّل تطبيق Uellow للتسوّق أونلاين في الكويت: عروض حصرية، توصيل سريع، ومساعد ذكي (بينا). متاح على App Store و Google Play و AppGallery. — Download the Uellow shopping app: exclusive deals, fast delivery & the Beena AI assistant. Available on the App Store, Google Play and Huawei AppGallery."/>
<meta name="keywords" content="Uellow, تطبيق يلو, يلو, تسوق اونلاين الكويت, تطبيق تسوق, عروض, توصيل سريع, Uellow app, online shopping Kuwait, shopping app, deals, App Store, Google Play, AppGallery, Huawei"/>
<meta name="robots" content="index, follow, max-image-preview:large"/>
<meta name="author" content="Uellow"/>
<meta name="theme-color" content="#F5C320"/>
<link rel="canonical" href="https://uellow.com/app"/>
<link rel="alternate" href="https://uellow.com/app" hreflang="ar"/>
<link rel="alternate" href="https://uellow.com/app" hreflang="en"/>
<link rel="alternate" href="https://uellow.com/app" hreflang="x-default"/>
<link rel="icon" href="%(icon)s"/>
<!-- Open Graph -->
<meta property="og:type" content="website"/>
<meta property="og:site_name" content="Uellow"/>
<meta property="og:url" content="https://uellow.com/app"/>
<meta property="og:title" content="تطبيق يلو دوت كوم | Uellow.com App"/>
<meta property="og:description" content="عروض حصرية · توصيل سريع · مساعد ذكي. متاح على App Store و Google Play و AppGallery. — Exclusive deals, fast delivery & AI assistant. On App Store, Google Play & AppGallery."/>
<meta property="og:image" content="%(icon)s"/>
<meta property="og:image:alt" content="Uellow app icon"/>
<meta property="og:locale" content="ar_AR"/>
<meta property="og:locale:alternate" content="en_US"/>
<!-- Twitter -->
<meta name="twitter:card" content="summary_large_image"/>
<meta name="twitter:title" content="تطبيق يلو دوت كوم | Uellow.com App"/>
<meta name="twitter:description" content="عروض حصرية · توصيل سريع · مساعد ذكي بينا — متاح على كل المتاجر."/>
<meta name="twitter:image" content="%(icon)s"/>
<!-- Structured data: mobile application -->
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"MobileApplication","name":"Uellow",
 "alternateName":"تطبيق يلو","operatingSystem":"iOS, Android, HarmonyOS",
 "applicationCategory":"ShoppingApplication","url":"https://uellow.com/app",
 "image":"%(icon)s","description":"تطبيق Uellow للتسوّق أونلاين: عروض حصرية وتوصيل سريع ومساعد ذكي. Uellow online shopping app with exclusive deals, fast delivery and an AI assistant.",
 "offers":{"@type":"Offer","price":"0","priceCurrency":"KWD"},
 "publisher":{"@type":"Organization","name":"Uellow","url":"https://uellow.com"}}
</script>
<style>
 :root{--y:#F5C320;--d:#412402;--ink:#3a2206}
 *{box-sizing:border-box;margin:0;padding:0}
 html,body{height:100%%}
 body{font-family:"Segoe UI",Tahoma,system-ui,sans-serif;color:var(--d);
   background:radial-gradient(1100px 700px at 80%% -5%%,#ffe07a 0%%,var(--y) 45%%,#eab415 100%%);
   min-height:100%%;overflow-x:hidden;display:flex;align-items:center;justify-content:center;padding:34px 20px}
 .deco{position:fixed;border-radius:50%%;filter:blur(10px);opacity:.25;z-index:0}
 .d1{width:160px;height:160px;background:#fff;top:8%%;left:6%%;opacity:.18}
 .d2{width:120px;height:120px;background:#fff;bottom:10%%;right:8%%;opacity:.14}
 .wrap{position:relative;z-index:1;max-width:1000px;width:100%%;display:flex;gap:48px;align-items:center;justify-content:center;flex-wrap:wrap}
 .left{flex:1 1 360px;max-width:480px;text-align:start}
 .brand{display:inline-flex;align-items:center;gap:11px;margin-bottom:18px}
 .brand img{width:62px;height:62px;border-radius:16px;box-shadow:0 8px 22px rgba(65,36,2,.25);background:#fff}
 .brand .nm{font-weight:800;font-size:22px}
 h1{font-size:44px;font-weight:900;line-height:1.1;margin-bottom:2px;letter-spacing:-.5px}
 h1 .u{color:var(--d);-webkit-text-decoration:underline 4px rgba(65,36,2,.3);
   text-decoration:underline 4px rgba(65,36,2,.3);text-underline-offset:7px}
 .h1en{font-size:20px;font-weight:800;letter-spacing:1px;opacity:.7;direction:ltr;
   text-align:center;margin-bottom:14px}
 p.sub{font-size:16.5px;opacity:.85;margin-bottom:4px;font-weight:600}
 p.en{font-size:13.5px;opacity:.6;direction:ltr;margin-bottom:14px;text-align:center}
 .stars{font-size:15px;color:#7a5a12;margin-bottom:22px;font-weight:700}
 .badges{display:flex;flex-direction:column;gap:13px;align-items:flex-start}
 .badge{display:block;width:230px;border-radius:14px;text-decoration:none;
   filter:drop-shadow(0 8px 18px rgba(65,36,2,.28));transition:transform .15s,filter .15s}
 .badge:hover{transform:translateY(-3px);filter:drop-shadow(0 14px 26px rgba(65,36,2,.4))}
 .badge img{width:100%%;height:auto;display:block}
 /* phone mockup */
 .right{flex:0 0 auto;display:flex;justify-content:center}
 .phone{position:relative;width:280px;height:580px;background:#0d0d0f;border-radius:46px;
   padding:13px;box-shadow:0 30px 70px rgba(65,36,2,.45),inset 0 0 0 2px #2a2a2e;animation:float 4s ease-in-out infinite}
 @keyframes float{0%%,100%%{transform:translateY(0)}50%%{transform:translateY(-14px)}}
 .phone .scr{width:100%%;height:100%%;border-radius:34px;overflow:hidden;background:#fff}
 .phone .scr img{width:100%%;height:100%%;object-fit:cover;object-position:top}
 .phone .notch{position:absolute;top:13px;left:50%%;transform:translateX(-50%%);width:120px;height:26px;background:#0d0d0f;border-radius:0 0 16px 16px;z-index:2}
 .bee{position:absolute;top:-22px;right:-14px;width:64px;height:64px;border-radius:18px;background:#fff;
   box-shadow:0 10px 24px rgba(65,36,2,.3);padding:6px;z-index:3;animation:float 3s ease-in-out infinite}
 .bee img{width:100%%;height:100%%}
 .redir{position:fixed;inset:0;z-index:5;background:var(--y);display:none;flex-direction:column;align-items:center;justify-content:center;gap:18px;color:var(--d)}
 .redir.show{display:flex}
 .redir img{width:96px;height:96px;border-radius:24px;background:#fff;box-shadow:0 12px 30px rgba(65,36,2,.3)}
 .spin{width:42px;height:42px;border:4px solid rgba(65,36,2,.2);border-top-color:var(--d);border-radius:50%%;animation:sp 1s linear infinite}
 @keyframes sp{to{transform:rotate(360deg)}}
 .foot{margin-top:26px;font-size:12px;opacity:.55}
 .foot a{color:var(--d)}
 @media(max-width:760px){
   .right{display:none}
   h1{font-size:34px}.h1en{font-size:18px;text-align:center}
   .left{text-align:center;max-width:420px}
   .badges{align-items:center}.brand{justify-content:center}
   .stars{text-align:center}.wrap{gap:0;justify-content:center}
 }
</style></head>
<body>
 <div class="deco d1"></div><div class="deco d2"></div>
 <div class="redir" id="redir"><img src="%(icon)s"/><div class="spin"></div>
   <div>جارٍ تحويلك إلى المتجر… <span style="opacity:.6">Redirecting…</span></div></div>

 <div class="wrap">
   <div class="left">
     <div class="brand"><img src="%(icon)s"/><span class="nm">Uellow</span></div>
     <h1>تطبيق <span class="u">يلو دوت كوم</span></h1>
     <div class="h1en">Uellow.com App</div>
     <p class="sub">عروض حصرية · توصيل سريع · مساعدك الذكي Beena</p>
     <p class="en">Exclusive deals · Fast delivery · Your AI assistant Beena</p>
     <div class="stars">★★★★★ <span style="opacity:.7">موثوق من آلاف العملاء</span></div>
     <div class="badges">%(badges)s</div>
     <div class="foot">© Uellow · uellow.com</div>
   </div>
   <div class="right">
     <div class="phone">
       <div class="notch"></div>
       <div class="scr"><img src="%(shot)s" alt="Uellow app"/></div>
     </div>
   </div>
 </div>
<script>
(function(){
 if('%(auto)s'!=='1') return;
 var ua=(navigator.userAgent||'').toLowerCase(),dest=null;
 if(/iphone|ipad|ipod/.test(ua)) dest='appstore';
 else if(/huawei|honor|hms|harmonyos/.test(ua)) dest='huawei';
 else if(/android/.test(ua)) dest='play';
 if(!dest) return;
 var store='/app/go/'+dest;
 document.getElementById('redir').classList.add('show');
 // If deep-linking is off, go straight to the store.
 if('%(openapp)s'!=='1'){ setTimeout(function(){window.location.href=store;},700); return; }
 var DL='%(deeplink)s', PKG='%(pkg)s';
 if(/android/.test(ua)){
   // intent:// opens the app if installed, else browser_fallback_url (the
   // logged store redirect). Most reliable path on Android.
   var parts=DL.split('://'), scheme=parts[0], path=(parts[1]||'');
   var fb=encodeURIComponent(location.origin+store);
   window.location.href='intent://'+path+'#Intent;scheme='+scheme+';package='+PKG+';S.browser_fallback_url='+fb+';end';
 } else {
   // iOS: try the custom scheme; if the app isn't there, the page stays
   // visible and the timeout sends us to the App Store.
   var t=setTimeout(function(){window.location.href=store;},1300);
   document.addEventListener('visibilitychange',function(){ if(document.hidden){clearTimeout(t);} });
   window.location.href=DL;
 }
})();
</script>
</body></html>"""

# ════════════════════ KPI dashboard (backend) ════════════════════
_DASH = """<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>App Analytics — Uellow</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
 :root{--y:#F5C320;--d:#412402;--ink:#2c1c0e;--mut:#8a7a66;--ln:#ece3d4;--bg:#faf7f0}
 *{box-sizing:border-box;margin:0;padding:0}
 body{font-family:"Segoe UI",system-ui,sans-serif;background:var(--bg);color:var(--ink)}
 .top{background:linear-gradient(135deg,var(--d),#5c3410);color:#fff;padding:22px 26px;display:flex;align-items:center;gap:12px}
 .top .logo{background:var(--y);color:var(--d);font-weight:800;padding:6px 13px;border-radius:20px;font-size:13px}
 .top h1{font-size:19px;font-weight:800}
 .wrap{max-width:1120px;margin:0 auto;padding:22px 18px}
 .kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:14px;margin-bottom:18px}
 .kpi{background:#fff;border:1px solid var(--ln);border-radius:16px;padding:16px 18px;box-shadow:0 6px 20px rgba(65,36,2,.06)}
 .kpi .lab{font-size:12px;color:var(--mut);font-weight:700;text-transform:uppercase;letter-spacing:.4px}
 .kpi .val{font-size:30px;font-weight:900;margin-top:6px;color:var(--d)}
 .kpi .val small{font-size:14px;font-weight:700;color:var(--mut)}
 .kpi.accent{background:linear-gradient(135deg,#fff7df,#ffeeb0);border-color:#f0dca0}
 .grid{display:grid;grid-template-columns:2fr 1fr;gap:14px}
 .card{background:#fff;border:1px solid var(--ln);border-radius:16px;padding:18px;box-shadow:0 6px 20px rgba(65,36,2,.06);margin-bottom:14px}
 .card h3{font-size:14px;font-weight:800;margin-bottom:12px;color:var(--d)}
 canvas{max-height:280px}
 @media(max-width:820px){.grid{grid-template-columns:1fr}}
 .empty{color:var(--mut);font-size:13px;text-align:center;padding:30px}
</style></head>
<body>
 <div class="top"><span class="logo">🐝 Uellow</span><h1>App Analytics · /app</h1></div>
 <div class="wrap">
   <div class="kpis">
     <div class="kpi"><div class="lab">Total Visits</div><div class="val" id="k_visits">0</div></div>
     <div class="kpi accent"><div class="lab">Conversions</div><div class="val" id="k_conv">0</div></div>
     <div class="kpi"><div class="lab">Conversion Rate</div><div class="val" id="k_rate">0<small>%%</small></div></div>
     <div class="kpi"><div class="lab">Top Platform</div><div class="val" id="k_plat" style="font-size:22px">—</div></div>
     <div class="kpi"><div class="lab">Top Country</div><div class="val" id="k_ctry" style="font-size:22px">—</div></div>
   </div>
   <div class="grid">
     <div><div class="card"><h3>Visits &amp; Conversions — last 14 days</h3><canvas id="c_trend"></canvas></div></div>
     <div><div class="card"><h3>By Platform</h3><canvas id="c_plat"></canvas></div></div>
   </div>
   <div class="grid">
     <div class="card"><h3>Top Countries</h3><canvas id="c_ctry"></canvas></div>
     <div class="card"><h3>Conversions by Store</h3><canvas id="c_store"></canvas></div>
   </div>
 </div>
<script>
 var D=%(data)s;
 document.getElementById('k_visits').textContent=D.visits.toLocaleString();
 document.getElementById('k_conv').textContent=D.conv.toLocaleString();
 document.getElementById('k_rate').innerHTML=D.rate+'<small>%%</small>';
 document.getElementById('k_plat').textContent=D.top_plat||'—';
 document.getElementById('k_ctry').textContent=D.top_country||'—';
 var Y='#F5C320',Br='#412402',G='#2f9e6b';
 if(window.Chart){
  new Chart(c_trend,{type:'line',data:{labels:D.trend_labels,datasets:[
    {label:'Visits',data:D.trend_v,borderColor:Br,backgroundColor:'rgba(65,36,2,.08)',fill:true,tension:.3},
    {label:'Conversions',data:D.trend_c,borderColor:Y,backgroundColor:'rgba(245,195,32,.15)',fill:true,tension:.3}]},
    options:{plugins:{legend:{position:'bottom'}},scales:{y:{beginAtZero:true}}}});
  new Chart(c_plat,{type:'doughnut',data:{labels:D.plat_labels,datasets:[{data:D.plat_vals,
    backgroundColor:[Y,Br,'#c8102e','#3a78c2','#999']}]},options:{plugins:{legend:{position:'bottom'}}}});
  new Chart(c_ctry,{type:'bar',data:{labels:D.ctry_labels,datasets:[{label:'Visits',data:D.ctry_vals,backgroundColor:Y}]},
    options:{indexAxis:'y',plugins:{legend:{display:false}},scales:{x:{beginAtZero:true}}}});
  new Chart(c_store,{type:'bar',data:{labels:D.store_labels,datasets:[{label:'Conversions',data:D.store_vals,backgroundColor:G}]},
    options:{plugins:{legend:{display:false}},scales:{y:{beginAtZero:true}}}});
 }
</script>
</body></html>"""
