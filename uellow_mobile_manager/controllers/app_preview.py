# -*- coding: utf-8 -*-
"""
Hosted interactive app mockup — /uellow-app-preview/

A single self-contained HTML page that demonstrates the new app design.
Renders inside a phone-frame on desktop and full-screen on mobile.
Pulls REAL data from the v2 API so editors can preview the actual
home / category / product / cart flows the customer will see.

Why this lives in `controllers/` and not `static/`:
  Odoo's static asset URLs require module registration + bundle hashes,
  but a marketing/preview page should just respond at a clean URL with
  no caching headaches. This controller streams the HTML directly.
"""
from odoo import http
from odoo.http import request


PREVIEW_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#F5C320">
<title>Uellow App — Interactive Preview</title>
<style>
  * { box-sizing: border-box; }
  body {
    margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI",
      "SF Pro Display", system-ui, sans-serif;
    background:
      radial-gradient(circle at top left, #2a1a0a, #0f0905 60%, #000 100%);
    color: #fff; min-height: 100vh;
    display: grid; grid-template-rows: auto 1fr auto;
  }
  /* Stage that holds the phone */
  .stage {
    display: grid; grid-template-columns: 1fr auto 1fr; gap: 28px;
    align-items: start; padding: 32px 24px 60px;
  }
  .copy { color: #fbf3da; padding-top: 60px; max-width: 460px; justify-self: end; }
  .copy h1 { font-size: 36px; line-height: 1.15; margin: 0 0 14px;
    background: linear-gradient(90deg,#FFD340,#F5C320); -webkit-background-clip: text;
    -webkit-text-fill-color: transparent; }
  .copy p { color: #cdbfa1; font-size: 15px; line-height: 1.65; }
  .copy .pill { display:inline-block; padding: 5px 12px; border-radius:999px;
    background: rgba(245,195,32,.12); color:#FFD340;
    border:1px solid rgba(245,195,32,.4); font-size:12px; letter-spacing:.6px;
    margin-bottom: 12px; text-transform:uppercase; font-weight:700; }
  .copy nav { display:flex; flex-wrap:wrap; gap:8px; margin-top:18px; }
  .copy nav a { padding: 7px 14px; border-radius:8px;
    background: rgba(255,255,255,.05); color:#fbf3da; text-decoration:none;
    font-size:12px; transition: background .15s, transform .15s; cursor:pointer; }
  .copy nav a:hover { background: rgba(245,195,32,.18); transform: translateY(-1px); }
  .copy nav a.active { background:#F5C320; color:#1a0f00; font-weight:700; }
  .side { padding-top: 60px; }
  .side h3 { color: #FFD340; font-size: 13px; letter-spacing:.5px;
    text-transform: uppercase; margin: 0 0 10px; }
  .side ul { list-style:none; padding:0; margin:0; color:#a89c80; font-size:13px; line-height:1.85; }
  .side ul li::before { content:"▸ "; color:#F5C320; }

  /* Phone frame */
  .phone {
    width: 380px; height: 800px;
    border-radius: 44px; background: #0d0a05;
    padding: 14px; position: relative;
    box-shadow:
      0 0 0 1.5px #2a1f0d,
      0 0 0 8px #110a02,
      0 25px 60px -10px rgba(245,195,32,.18),
      0 50px 120px -30px rgba(0,0,0,.7);
  }
  .phone::before { content:""; position:absolute; top:18px; left:50%;
    transform:translateX(-50%); width: 120px; height: 28px; border-radius: 16px;
    background:#0d0a05; z-index:10; }
  .phone .screen {
    width: 100%; height: 100%; border-radius: 32px; background: #fff;
    overflow: hidden; position: relative;
  }
  .frame { width:100%; height:100%; border:0; display:block; }

  /* Bottom strip */
  .credits { text-align:center; color:#6c5a3a; font-size:11px;
    padding: 18px; border-top: 1px solid #1a120a; }
  .credits a { color:#FFD340; text-decoration:none; }

  /* Header */
  header { padding: 22px 32px; display:flex; align-items:center;
    justify-content:space-between; border-bottom: 1px solid rgba(255,255,255,.04); }
  .brand { display:flex; align-items:center; gap:10px; color:#FFD340;
    font-weight:800; font-size:18px; letter-spacing:-.3px; }
  .brand-dot { width:24px; height:24px; border-radius:8px;
    background: linear-gradient(135deg,#FFE066,#F5C320); }
  .legend { display:flex; gap:18px; font-size:12px; color:#a89c80; }

  @media (max-width: 900px) {
    .stage { grid-template-columns: 1fr; padding: 16px; }
    .copy, .side { justify-self: start; padding-top: 0; max-width: 100%; }
    .phone { margin: 0 auto; transform: scale(.95); transform-origin: top center; }
  }
</style>
</head>
<body>
<header>
  <div class="brand"><div class="brand-dot"></div>Uellow App Preview</div>
  <div class="legend">Live preview · pulls real data from <code>/api/mobile/v2/*</code></div>
</header>

<div class="stage">
  <aside class="copy">
    <span class="pill">Interactive Mockup</span>
    <h1>The new Uellow app.</h1>
    <p>Country picker, flash sales, multi-vendor storefronts, Beena AI,
       barcode &amp; image search, native checkout, loyalty + wallet — all
       managed from <strong>Mobile App Manager</strong> in your Odoo backend.</p>
    <p>Every screen below pulls real data from the v2 API running on this
       server. Click between screens — no logins or fake data.</p>
    <nav id="nav">
      <a data-screen="splash" class="active">1 · Country picker</a>
      <a data-screen="auth">2 · Sign in</a>
      <a data-screen="home">3 · Home</a>
      <a data-screen="search">4 · Search</a>
      <a data-screen="category">5 · Categories</a>
      <a data-screen="brands">6 · Brands</a>
      <a data-screen="flash">7 · Flash sale</a>
      <a data-screen="product">8 · Product</a>
      <a data-screen="vendor">9 · Vendor store</a>
      <a data-screen="tryon">10 · Try-On + Smart Fit</a>
      <a data-screen="cart">11 · Cart</a>
      <a data-screen="checkout">12 · Checkout</a>
      <a data-screen="order">13 · Order tracking</a>
      <a data-screen="account">14 · Account</a>
      <a data-screen="loyalty">15 · Loyalty</a>
      <a data-screen="wallet">16 · Wallet</a>
      <a data-screen="coupons">17 · Coupons</a>
      <a data-screen="wishlist">18 · Wishlist</a>
      <a data-screen="notifications">19 · Notifications</a>
      <a data-screen="beena">20 · Beena AI</a>
    </nav>
  </aside>

  <div class="phone">
    <div class="screen">
      <iframe id="frame" class="frame" src="/uellow-app-preview/screen/splash"></iframe>
    </div>
  </div>

  <aside class="side">
    <h3>What you're seeing</h3>
    <ul id="notes">
      <li>Auto-detect country from IP</li>
      <li>Switch language (EN/AR) inline</li>
      <li>Saved choice survives reboots</li>
      <li>Re-prompt only if user travels</li>
    </ul>
  </aside>
</div>

<div class="credits">
  Built by Claude · data:
  <a href="/api/mobile/v2/docs" target="_blank">/api/mobile/v2/docs</a> ·
  Swagger:
  <a href="/api/mobile/v2/openapi.json" target="_blank">openapi.json</a>
</div>

<script>
  const NOTES = {
    splash: ['Auto-detect country from IP','Switch language (EN/AR) inline',
             'Saved choice survives reboots','Re-prompt only if user travels'],
    auth:   ['Tabbed sign-in / sign-up flow','Social: Google/Apple/FB + Phone OTP',
             'Token stored in flutter_secure_storage','onAuthChanged stream reactive UI'],
    home:   ['1 home call returns sliders + sections + flash + popups',
             'Pulled from mobile.* models — independent of website',
             'Bilingual labels handled per-locale',
             'Auto in-app popup demo (after 2s)'],
    search: ['Live autocomplete as you type','Recent + Trending + Browse cats',
             'Barcode + image search entry points','Cleared individually'],
    category:['Sidebar-on-left pattern (SHEIN/Banggood)','Sub-cat chips inside main cat',
             'Featured deal banner at top','Auto emoji per category'],
    brands: ['A-Z scroll bar (jump letters)','Featured brands carousel',
             'Vendor logo + rating + count','Tap → vendor store'],
    flash:  ['Multi-source: manual / vendor-flagged / auto-discount',
             'Filter by category + vendor chips','Sort + Filters drawer',
             'Per-user quantity cap at /cart/add'],
    product:['Description partial + See More dialog',
             'Specifications opens dedicated dialog',
             'Color image swatches + Size + Smart Fit',
             'Out of stock → Notify me button'],
    vendor: ['Internal vendor flash sale',
             '7 tabs (All/New/Best/Flash/Cats/Reviews/About)',
             'Brand color from vendor settings',
             'Follow + Chat with seller'],
    tryon:  ['AI-generated try-on image','Live color swap',
             'Smart Fit measurements form','Recommended size + alternatives'],
    cart:   ['Guest cart via X-Cart-Token header',
             'Save for later + Remove actions',
             'Applied coupons inline',
             'Free-delivery progress bar'],
    checkout:['3-step progress bar',
             'Native shipping picker (not webview)',
             'KNET / Apple Pay / Card / COD',
             'Delivery instructions field'],
    order:  ['Live tracking timeline',
             'ETA card + driver call button',
             'Map placeholder for live driver',
             '6 actions: reorder/invoice/return/etc'],
    account:['Order status grid 6×1 (matching current app)',
             'Loyalty + wallet gradient banners',
             'Wishlist + recently viewed sections',
             'Social media follow icons'],
    loyalty:['Hero card with points + tier progress',
             'Tier strip (Bronze→Platinum)',
             'Earn ways + Redeem grid',
             'Points history with +/- transactions'],
    wallet: ['Brown gradient hero with balance',
             'Quick top-up pills',
             'Monthly spend stats',
             'Transactions in/out with status'],
    coupons:['3 tabs: Available / Used / Expired',
             'Visual coupon design (perforated edges)',
             'Different color tiers',
             'Min spend + expiry shown'],
    wishlist:['Grid 2-col with stock/price alerts',
             'Filter chips (All/On sale/Drop)',
             'Quick add-to-cart button',
             'Hot-pink heart to remove'],
    notifications:['Categorized tabs (Orders/Promos/Beena)',
             'Read/unread states with dot',
             'Thumbnail preview',
             'Grouped by day (Today/Yesterday/Earlier)'],
    beena:  ['Chat passthrough to /ai/chat',
             'Vision search: take a photo',
             'Voice ready (eleven/openai)',
             'Quick-action chips']
  };

  const nav = document.getElementById('nav');
  const frame = document.getElementById('frame');
  const notes = document.getElementById('notes');

  nav.addEventListener('click', e => {
    if (e.target.tagName !== 'A') return;
    e.preventDefault();
    nav.querySelectorAll('a').forEach(a => a.classList.remove('active'));
    e.target.classList.add('active');
    const screen = e.target.dataset.screen;
    frame.src = '/uellow-app-preview/screen/' + screen;
    notes.innerHTML = NOTES[screen].map(n => `<li>${n}</li>`).join('');
  });
</script>
</body>
</html>"""


def _screen_html(body, *, title='Uellow', bottom_nav=True):
    """Wrap a screen body in the consistent phone-frame chrome:
    status bar, top bar, optional bottom tab nav. Returns full HTML."""
    nav_html = ''
    if bottom_nav:
        nav_html = '''
        <nav class="tabbar">
          <a class="tab active" href="/uellow-app-preview/screen/home">
            <svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 3 2 12h3v8h6v-6h2v6h6v-8h3z"/></svg>
            <span>Home</span>
          </a>
          <a class="tab" href="/uellow-app-preview/screen/category">
            <svg viewBox="0 0 24 24" fill="currentColor"><path d="M4 4h7v7H4zm9 0h7v7h-7zm0 9h7v7h-7zm-9 0h7v7H4z"/></svg>
            <span>Shop</span>
          </a>
          <a class="tab beena-tab" href="/uellow-app-preview/screen/beena">
            <div class="beena-orb"></div>
            <span>Beena</span>
          </a>
          <a class="tab" href="/uellow-app-preview/screen/cart">
            <svg viewBox="0 0 24 24" fill="currentColor"><path d="M7 4h-2L3 2H1v2h2l3.6 7.59-1.35 2.45C5.16 14.37 5 14.67 5 15a2 2 0 0 0 2 2h12v-2H7.42c-.14 0-.25-.11-.25-.25l.03-.12L8.1 13h7.45c.75 0 1.41-.41 1.75-1.03L20.88 5H5.21z"/></svg>
            <span>Cart</span><span class="badge">2</span>
          </a>
          <a class="tab" href="/uellow-app-preview/screen/account">
            <svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 12a4 4 0 1 0-4-4 4 4 0 0 0 4 4zm0 2c-3 0-9 1.6-9 5v3h18v-3c0-3.4-6-5-9-5z"/></svg>
            <span>Account</span>
          </a>
        </nav>'''
    return f'''<!DOCTYPE html><html><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<style>
  *,*::before,*::after {{ box-sizing:border-box; }}
  body {{ margin:0; font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text",
       "Segoe UI",system-ui,sans-serif; background:#F8F4E3; color:#1a1108;
       overflow-x:hidden; }}
  .statusbar {{ height: 26px; background: transparent; display:flex;
       align-items: flex-end; padding: 0 22px 4px; font-size:12px;
       font-weight:600; color:#1a1108; justify-content: space-between;}}
  .statusbar .right {{ display:flex; gap:5px; align-items:center;
       font-variant-numeric: tabular-nums; }}
  .screenbody {{ overflow-y:auto; padding-bottom: 78px; height: calc(100vh - 26px); }}
  /* Top bar */
  .topbar {{ padding: 8px 18px 14px; display:flex; align-items:center; gap:12px;
       background: linear-gradient(180deg, #fff, #fff 80%, transparent); }}
  .topbar input {{ flex:1; height:40px; border-radius:12px; border:0;
       padding: 0 14px 0 38px; background: #F2EBD3; color:#5d4d2e;
       font-size:14px; outline:0;
       background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='%23A89060'><path d='M21 19l-4-4a8 8 0 1 0-2 2l4 4zm-12-3a6 6 0 1 1 6-6 6 6 0 0 1-6 6z'/></svg>");
       background-repeat:no-repeat; background-position: 12px center; }}
  .icon-btn {{ width:40px; height:40px; border-radius:12px; border:0;
       display:grid; place-items:center; background:#F2EBD3; cursor:pointer;
       color:#5d4d2e; }}
  .icon-btn svg {{ width:18px; height:18px; }}
  /* Bottom tab bar */
  .tabbar {{ position: fixed; bottom:0; left:0; right:0; height:78px;
       background: rgba(255,255,255,.98); backdrop-filter: blur(20px);
       display:flex; padding: 0 8px;
       border-top: 0.5px solid rgba(0,0,0,.08); z-index:50;
       padding-bottom: env(safe-area-inset-bottom, 0); }}
  .tab {{ flex:1; display:flex; flex-direction:column; align-items:center;
       justify-content:center; color:#9d8a60; text-decoration:none;
       font-size:10.5px; font-weight:600; gap:4px; position:relative; }}
  .tab svg {{ width:22px; height:22px; }}
  .tab.active {{ color:#412402; }}
  .tab .badge {{ position:absolute; top:10px; right:calc(50% - 18px);
       background:#FF4D4D; color:#fff; font-size:10px; font-weight:800;
       padding: 0 5px; border-radius:9px; min-width: 18px; height:18px;
       display:grid; place-items:center; }}
  .beena-tab {{ position: relative; }}
  .beena-orb {{ width:44px; height:44px; border-radius:50%;
       background: radial-gradient(circle at 30% 25%, #FFE45E, #F5C320 60%, #C99000);
       box-shadow: 0 6px 18px -3px rgba(245,195,32,.65),
                   inset 0 1px 2px rgba(255,255,255,.6);
       margin-top: -16px; position: relative; }}
  .beena-orb::after {{ content:"✨"; position:absolute; inset:0; display:grid;
       place-items:center; font-size:20px; }}
  .beena-tab span {{ color:#412402; font-weight:700; }}
</style></head><body>
<div class="statusbar">
  <span>9:41</span>
  <span class="right">
    <svg width="14" height="10" viewBox="0 0 14 10" fill="currentColor"><rect x="1" y="6" width="2" height="3" rx=".5"/><rect x="4" y="4" width="2" height="5" rx=".5"/><rect x="7" y="2" width="2" height="7" rx=".5"/><rect x="10" y="0" width="2" height="9" rx=".5"/></svg>
    <svg width="15" height="10" viewBox="0 0 15 10" fill="currentColor"><path d="M7.5 1.6c-2 0-3.9.7-5.4 2L3.4 5a5.7 5.7 0 0 1 8.2 0L13 3.6c-1.5-1.3-3.4-2-5.5-2zm0 3a3.8 3.8 0 0 0-2.7 1.1l1.3 1.3a2 2 0 0 1 2.8 0L10.2 5.7a3.8 3.8 0 0 0-2.7-1zm0 3a1 1 0 1 0 1 1 1 1 0 0 0-1-1z"/></svg>
    <svg width="22" height="10" viewBox="0 0 24 10" fill="none" stroke="currentColor"><rect x=".5" y=".5" width="20" height="9" rx="2"/><rect x="2" y="2" width="17" height="6" rx="1" fill="currentColor"/><rect x="21" y="3" width="2" height="4" fill="currentColor" rx="1"/></svg>
  </span>
</div>
<div class="screenbody">{body}</div>
{nav_html}
</body></html>'''


class UellowAppPreview(http.Controller):

    @http.route('/uellow-app-preview', type='http', auth='public', csrf=False,
                methods=['GET'])
    @http.route('/uellow-app-preview/', type='http', auth='public', csrf=False,
                methods=['GET'])
    def index(self, **kw):
        return request.make_response(PREVIEW_HTML, headers=[
            ('Content-Type', 'text/html; charset=utf-8'),
            ('Cache-Control', 'no-store'),
        ])

    @http.route('/uellow-app-preview/screen/<string:screen>', type='http',
                auth='public', csrf=False, methods=['GET'])
    def screen(self, screen, **kw):
        from .api_v2_preview_screens import RENDERERS
        renderer = RENDERERS.get(screen) or RENDERERS['home']
        body, title, has_nav = renderer(request.env)
        return request.make_response(
            _screen_html(body, title=title, bottom_nav=has_nav),
            headers=[
                ('Content-Type', 'text/html; charset=utf-8'),
                ('Cache-Control', 'no-store'),
            ],
        )
