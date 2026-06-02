# -*- coding: utf-8 -*-
"""
Screen renderers for /uellow-app-preview/screen/<name>.
Returns (html_body, page_title, show_bottom_nav).

Design system:
  • Brand yellow #F5C320, dark brown #412402
  • Monochrome SVG icons (color via currentColor)
  • Icon states: idle → grey, active → yellow
  • Mobile-first, all chrome rendered inside the phone frame.
"""
import html


# ─── Utilities ──────────────────────────────────────────────────────

def _esc(s):
    return html.escape(str(s or ''), quote=True)


def _bilingual(rec, field):
    try:
        en = rec.with_context(lang='en_US')[field] or ''
        ar = rec.with_context(lang='ar_001')[field] or en
    except Exception:
        v = rec[field] if field in rec._fields else ''
        en = ar = v or ''
    return {'en': en, 'ar': ar}


def _img(model, rec_id, field='image_512', unique=None):
    u = f'/web/image/{model}/{rec_id}/{field}'
    if unique:
        u += f'?unique={hash(str(unique)) & 0xffffff}'
    return u


def _emoji_for(name):
    n = (name or '').lower()
    rules = [
        (['phone','mobile','smart'], '📱'),
        (['laptop','computer','pc'], '💻'),
        (['fashion','cloth','dress','shirt'], '👗'),
        (['home','furniture','kitchen'], '🏠'),
        (['baby','kid'], '👶'),
        (['game','toy','sport'], '🎮'),
        (['beauty','cosmetic','perfume','make'], '💄'),
        (['watch'], '⌚'),
        (['shoe','sneaker'], '👟'),
        (['food','grocer'], '🛒'),
        (['health','vitamin'], '💊'),
        (['tv','televis'], '📺'),
        (['car','auto'], '🚗'),
        (['camera'], '📸'),
        (['music','speaker','earbud','headphone'], '🎧'),
        (['tool'], '🔧'),
        (['bag','luggage'], '👜'),
    ]
    for keywords, emoji in rules:
        if any(k in n for k in keywords):
            return emoji
    return '📦'


# ─── Reusable icon library (monochrome, currentColor) ──────────────

def _ico(name, size=16):
    """Brand-consistent monochrome SVGs. Color via CSS color:."""
    paths = {
        'truck': '<path d="M3 5h11v9H3zm12 4h3l3 3v2h-6zm-9 8a2 2 0 1 1 4 0 2 2 0 0 1-4 0zm10 0a2 2 0 1 1 4 0 2 2 0 0 1-4 0z" fill="currentColor"/>',
        'bolt':  '<path d="M13 2 3 14h7l-1 8 11-13h-7z" fill="currentColor"/>',
        'return':'<path d="M11 5V2L5 8l6 6v-3a6 6 0 1 1-6 6h-2a8 8 0 1 0 8-8z" fill="currentColor"/>',
        'shield':'<path d="M12 2 4 5v6c0 5 3.4 9.4 8 11 4.6-1.6 8-6 8-11V5z" fill="currentColor"/>',
        'star':  '<path d="M12 2 9.2 8.6 2 9.3l5.5 4.8L5.8 21 12 17.3 18.2 21l-1.7-6.9L22 9.3l-7.2-.7z" fill="currentColor"/>',
        'heart': '<path d="M12 21s-7-4.5-7-10a4 4 0 0 1 7-2 4 4 0 0 1 7 2c0 5.5-7 10-7 10z" fill="currentColor"/>',
        'cart':  '<path d="M7 4h-2L3 2H1v2h2l3.6 7.6L5.2 14a2 2 0 0 0 1.8 3h12v-2H7l1.1-2h7.4c.8 0 1.4-.4 1.8-1l3.6-6.4L21 4H5.2zM7 18a2 2 0 1 0 0 4 2 2 0 0 0 0-4zm10 0a2 2 0 1 0 0 4 2 2 0 0 0 0-4z" fill="currentColor"/>',
        'user':  '<path d="M12 12a4 4 0 1 0-4-4 4 4 0 0 0 4 4zm0 2c-3 0-9 1.6-9 5v3h18v-3c0-3.4-6-5-9-5z" fill="currentColor"/>',
        'home':  '<path d="M12 3 2 12h3v8h6v-6h2v6h6v-8h3z" fill="currentColor"/>',
        'grid':  '<path d="M4 4h7v7H4zm9 0h7v7h-7zm0 9h7v7h-7zm-9 0h7v7H4z" fill="currentColor"/>',
        'bell':  '<path d="M12 22a2 2 0 0 0 2-2h-4a2 2 0 0 0 2 2zm6-6V11a6 6 0 0 0-5-5.9V4a1 1 0 1 0-2 0v1.1A6 6 0 0 0 6 11v5l-2 2v1h16v-1z" fill="currentColor"/>',
        'box':   '<path d="M21 16V8a2 2 0 0 0-1-1.7l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.7l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16zm-9 4-7-4V9l7 4zm0-9L5 7l7-4 7 4zm9 5-7 4v-7l7-4z" fill="currentColor"/>',
        'pin':   '<path d="M12 2a7 7 0 0 0-7 7c0 5 7 13 7 13s7-8 7-13a7 7 0 0 0-7-7zm0 9.5a2.5 2.5 0 1 1 0-5 2.5 2.5 0 0 1 0 5z" fill="currentColor"/>',
        'check': '<path d="M9 16.2 4.8 12l-1.4 1.4L9 19 21 7l-1.4-1.4z" fill="currentColor"/>',
        'clock': '<path d="M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2zm4.2 14.2L11 13V7h1.5v5.2l4.5 2.7z" fill="currentColor"/>',
        'pen':   '<path d="M3 17.2V21h3.8L17.8 9.9l-3.8-3.8zm17.7-9.9a1 1 0 0 0 0-1.4l-2.6-2.6a1 1 0 0 0-1.4 0l-2 2 3.8 3.8z" fill="currentColor"/>',
        'gift':  '<path d="M20 6h-2.2a3 3 0 0 0 .2-1 3 3 0 0 0-3-3 4 4 0 0 0-3 1.5A4 4 0 0 0 9 2a3 3 0 0 0-3 3 3 3 0 0 0 .2 1H4a2 2 0 0 0-2 2v2a1 1 0 0 0 1 1v8a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-8a1 1 0 0 0 1-1V8a2 2 0 0 0-2-2zm-5-2a1 1 0 1 1 0 2h-2zm-6 1a1 1 0 0 1 1-1l2 2H9a1 1 0 0 1-1-1zm3 14H5v-8h7zm0-10H4V8h8zm7 10h-7v-8h7zm1-10h-8V8h8z" fill="currentColor"/>',
        'wallet':'<path d="M21 7H5V5h16zm0 2H3v10a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V11a2 2 0 0 0-2-2zM16 15a2 2 0 1 1 0-4 2 2 0 0 1 0 4z" fill="currentColor"/>',
        'chat':  '<path d="M20 2H4a2 2 0 0 0-2 2v18l4-4h14a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2z" fill="currentColor"/>',
        'globe': '<path d="M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2zm-1 17.9a8 8 0 0 1-7-7.9h3a17 17 0 0 0 1 6.9zm-4-9.9a8 8 0 0 1 4-6.5 11 11 0 0 0-1.5 6.5zM12 4a14 14 0 0 1 2 6h-4a14 14 0 0 1 2-6zm0 16a14 14 0 0 1-2-6h4a14 14 0 0 1-2 6zm5-10a17 17 0 0 0-1-6.9 8 8 0 0 1 5 6.9zm-3 0h-4a17 17 0 0 1 2-6.9 17 17 0 0 1 2 6.9zm-3 2h6a14 14 0 0 1-3 6 14 14 0 0 1-3-6zm7 0h3a8 8 0 0 1-5 6.9 17 17 0 0 0 2-6.9z" fill="currentColor"/>',
        'cog':   '<path d="M19.4 13a7 7 0 0 0 0-2l2-1.5-2-3.5L17 7a7 7 0 0 0-1.7-1L15 3.5h-4L10.7 6a7 7 0 0 0-1.7 1L6.6 6l-2 3.5L6.6 11a7 7 0 0 0 0 2L4.6 14.5l2 3.5L9 17a7 7 0 0 0 1.7 1l.3 2.5h4l.3-2.5a7 7 0 0 0 1.7-1l2.4 1 2-3.5zM12 15.5a3.5 3.5 0 1 1 0-7 3.5 3.5 0 0 1 0 7z" fill="currentColor"/>',
        'arrow_r':'<path d="M9 18l6-6-6-6" stroke="currentColor" stroke-width="2" fill="none"/>',
        'search':'<path d="M21 19l-4-4a8 8 0 1 0-2 2l4 4zm-12-3a6 6 0 1 1 6-6 6 6 0 0 1-6 6z" fill="currentColor"/>',
        'camera':'<path d="M9 4 8 6H4a2 2 0 0 0-2 2v11a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-4l-1-2zm3 4a5 5 0 1 1 0 10 5 5 0 0 1 0-10z" fill="currentColor"/>',
        'barcode':'<rect x="3" y="5" width="1.5" height="14"/><rect x="6" y="5" width="2.5" height="14"/><rect x="10" y="5" width="1" height="14"/><rect x="12.5" y="5" width="2" height="14"/><rect x="16" y="5" width="1.5" height="14"/><rect x="19" y="5" width="1.5" height="14"/>',
        'filter':'<path d="M3 4h18l-7 8v6l-4 2v-8z" fill="currentColor"/>',
        'sort':  '<path d="M3 6h18M6 12h12M10 18h4" stroke="currentColor" stroke-width="2" fill="none"/>',
        'share': '<path d="M18 16a3 3 0 0 0-2.4 1.2l-7.1-4.1a3 3 0 0 0 0-2.2l7.1-4.1a3 3 0 1 0-1-1.7l-7.1 4.1a3 3 0 1 0 0 5.6l7.1 4.1A3 3 0 1 0 18 16z" fill="currentColor"/>',
        'down':  '<path d="M7 10l5 5 5-5z" fill="currentColor"/>',
        'tag':   '<path d="M21 11.2V4a1 1 0 0 0-1-1h-7.2a1 1 0 0 0-.7.3L2.3 13.1a1 1 0 0 0 0 1.4l6.2 6.2a1 1 0 0 0 1.4 0l9.8-9.8a1 1 0 0 0 .3-.7zM15.5 9a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3z" fill="currentColor"/>',
        'fire':  '<path d="M12 2c1 5-3 6-3 10a3 3 0 0 0 6 0c0-1 1-2 1-2s2 3 2 5a6 6 0 0 1-12 0c0-3 3-5 3-9 0-2-1-4-1-4s4 1 4 4z" fill="currentColor"/>',
        'eye':   '<path d="M12 5C7 5 2.7 8.1 1 12c1.7 3.9 6 7 11 7s9.3-3.1 11-7c-1.7-3.9-6-7-11-7zm0 12a5 5 0 1 1 0-10 5 5 0 0 1 0 10zm0-8a3 3 0 1 0 0 6 3 3 0 0 0 0-6z" fill="currentColor"/>',
        'ruler': '<path d="M2 14l4-4 2 2 2-2 2 2 2-2 2 2 2-2 2 2 2-2v8H2z" fill="currentColor"/>',
        'logout':'<path d="M16 13v-2H7V8l-5 4 5 4v-3zM20 3H10a2 2 0 0 0-2 2v4h2V5h10v14H10v-4H8v4a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V5a2 2 0 0 0-2-2z" fill="currentColor"/>',
    }
    p = paths.get(name, '')
    return f'<svg viewBox="0 0 24 24" width="{size}" height="{size}" fill="none">{p}</svg>'


# ─── 1. SPLASH (logo + dropdown + bg) ──────────────────────────────

def render_splash(env):
    mappings = env['mobile.country.website'].sudo().search([('active', '=', True)])
    if not mappings:
        countries = [
            ('🇰🇼', 'Kuwait',         'الكويت',        'KWD'),
            ('🇸🇦', 'Saudi Arabia',   'السعودية',      'SAR'),
            ('🇦🇪', 'UAE',            'الإمارات',      'AED'),
            ('🇶🇦', 'Qatar',          'قطر',           'QAR'),
            ('🇴🇲', 'Oman',           'عُمان',          'OMR'),
            ('🇪🇬', 'Egypt',          'مصر',           'EGP'),
            ('🇺🇸', 'United States',  'الولايات المتحدة', 'USD'),
        ]
    else:
        countries = []
        for m in mappings:
            n = _bilingual(m.country_id, 'name')
            cur = m.currency_id.name if m.currency_id else m.website_id.currency_id.name
            countries.append((m.flag_emoji or '🌐', n['en'], n['ar'], cur))

    dropdown_items = ''.join(f'''
      <div class="dd-row" data-flag="{_esc(flag)}" data-en="{_esc(en)}" data-ar="{_esc(ar)}" data-cur="{_esc(cur)}">
        <span class="dd-flag">{_esc(flag)}</span>
        <div class="dd-text">
          <div class="dd-en">{_esc(en)}</div>
          <div class="dd-ar">{_esc(ar)}</div>
        </div>
        <span class="dd-cur">{_esc(cur)}</span>
      </div>''' for flag, en, ar, cur in countries)

    body = '''
<style>
  .splash-page { min-height: 100vh; padding: 0; position: relative;
       background: #FFFCEF; overflow: hidden; }
  /* Background image placeholder (settings will let admin set this) */
  .splash-bg { position: absolute; inset: 0; opacity: .85;
       background:
         radial-gradient(ellipse at top, #FFE066 0%, transparent 60%),
         radial-gradient(ellipse at bottom right, #F5C320 0%, transparent 50%),
         #FFFCEF; }
  .splash-bg::after { content: ""; position: absolute; inset: 0;
       background-image:
         radial-gradient(circle at 20% 20%, rgba(255,211,64,.35) 0, transparent 30%),
         radial-gradient(circle at 80% 70%, rgba(245,195,32,.25) 0, transparent 35%); }
  .splash-inner { position: relative; z-index: 1; padding: 50px 24px 130px;
       min-height: 100vh; display: flex; flex-direction: column; }
  /* Logo */
  .splash-logo-wrap { text-align: center; margin: 28px 0 22px; }
  .splash-logo { display: inline-flex; align-items: center; gap: 12px;
       padding: 10px 22px 10px 18px; background: #412402;
       border-radius: 18px; box-shadow: 0 14px 30px -8px rgba(65,36,2,.4); }
  .splash-logo .logo-dot { width: 38px; height: 38px; border-radius: 12px;
       background: linear-gradient(135deg,#FFE066,#F5C320);
       display: grid; place-items: center; color: #412402;
       font-weight: 900; font-size: 22px; }
  .splash-logo .logo-text { color: #FFD340; font-weight: 900;
       font-size: 24px; letter-spacing: -.5px; }
  .splash-tagline { text-align: center; color: #5d4d2e; margin: 14px 0 30px;
       font-size: 14px; line-height: 1.55; }
  .splash-tagline b { color: #412402; }
  /* Dropdown */
  .picker-card { background: #fff; border-radius: 18px;
       box-shadow: 0 14px 40px -10px rgba(65,36,2,.18); padding: 6px; }
  .picker-label { font-size: 11px; font-weight: 800; color: #9c8a5e;
       text-transform: uppercase; letter-spacing: .8px;
       padding: 12px 14px 6px; }
  .dropdown { position: relative; padding: 0 8px 8px; }
  .dd-button { width: 100%; display: flex; align-items: center; gap: 12px;
       background: #FFFCEF; border: 1.5px solid #F2EBD3; border-radius: 12px;
       padding: 12px 14px; cursor: pointer; }
  .dd-button .dd-flag { font-size: 22px; }
  .dd-button .dd-name { font-weight: 800; color: #412402; font-size: 15px; flex: 1;
       text-align: left; }
  .dd-button .dd-chev { color: #9c8a5e; transition: transform .15s; }
  .dd-button.open .dd-chev { transform: rotate(180deg); }
  .dd-panel { position: absolute; top: 100%; left: 8px; right: 8px;
       background: #fff; border: 1px solid #F2EBD3; border-radius: 12px;
       margin-top: 6px; max-height: 320px; overflow-y: auto; box-shadow: 0 12px 28px -10px rgba(0,0,0,.2);
       display: none; z-index: 10; }
  .dd-panel.show { display: block; }
  .dd-row { display: flex; align-items: center; gap: 12px; padding: 12px 14px;
       cursor: pointer; border-bottom: 1px solid #FAF5DD; }
  .dd-row:last-child { border-bottom: 0; }
  .dd-row:hover { background: #FFFCEF; }
  .dd-flag { font-size: 22px; }
  .dd-text { flex: 1; }
  .dd-en { font-weight: 700; font-size: 14px; color: #1a1108; }
  .dd-ar { font-size: 11px; color: #9c8a5e; direction: rtl; }
  .dd-cur { background: #F5C320; color: #412402; padding: 3px 10px;
       border-radius: 999px; font-weight: 800; font-size: 11px; }
  /* Detected hint */
  .detected-hint { display: flex; align-items: center; gap: 10px;
       background: rgba(255,255,255,.7); padding: 12px 16px; border-radius: 14px;
       margin: 14px 0; font-size: 12px; color: #412402;
       border: 1px solid rgba(245,195,32,.3); }
  .detected-hint b { color: #412402; }
  /* Language */
  .lang-block { padding: 6px 8px 6px; }
  .lang-tabs { display: flex; gap: 6px; background: #FFFCEF;
       padding: 4px; border-radius: 12px; border: 1.5px solid #F2EBD3; }
  .lang-tabs button { flex: 1; padding: 11px; border: 0; background: transparent;
       color: #5d4d2e; font-weight: 700; border-radius: 8px; cursor: pointer;
       font-size: 14px; }
  .lang-tabs button.on { background: #412402; color: #FFD340; }
  /* Continue */
  .continue-bar { position: fixed; left: 24px; right: 24px; bottom: 30px;
       z-index: 5; }
  .continue { width: 100%; padding: 16px; background: #412402; color: #FFD340;
       border: 0; border-radius: 16px; font-size: 15px; font-weight: 800;
       cursor: pointer; box-shadow: 0 14px 30px -8px rgba(65,36,2,.5); }
  /* Footer */
  .splash-foot { text-align: center; margin-top: auto; padding-top: 24px;
       color: #9c8a5e; font-size: 11px; }
</style>
<div class="splash-page">
  <div class="splash-bg"></div>
  <div class="splash-inner">
    <div class="splash-logo-wrap">
      <div class="splash-logo">
        <div class="logo-dot">U</div>
        <div class="logo-text">Uellow</div>
      </div>
    </div>
    <p class="splash-tagline">Your trusted marketplace in the Middle East.<br><b>Choose where you're shopping from.</b></p>
    <div class="picker-card">
      <div class="picker-label">Country</div>
      <div class="dropdown">
        <button class="dd-button open" onclick="document.querySelector('.dd-panel').classList.toggle('show'); this.classList.toggle('open');">
          <span class="dd-flag">🇰🇼</span>
          <span class="dd-name">Kuwait <span style="color:#9c8a5e;font-weight:500;font-size:12px;">· KWD</span></span>
          <span class="dd-chev">▾</span>
        </button>
        <div class="dd-panel">''' + dropdown_items + '''</div>
      </div>
      <div class="picker-label">Language</div>
      <div class="lang-block">
        <div class="lang-tabs">
          <button class="on">العربية</button>
          <button>English</button>
        </div>
      </div>
    </div>
    <div class="detected-hint">
      <span style="font-size:18px">📍</span>
      <span>Detected: <b>Kuwait</b> · Connecting to <b>The App</b></span>
    </div>
    <div class="splash-foot">By continuing you agree to our <b>Terms</b> &amp; <b>Privacy</b></div>
  </div>
</div>
<div class="continue-bar"><button class="continue">Continue →</button></div>
'''
    return body, 'Welcome', False


# ─── Reusable product card ─────────────────────────────────────────

def _product_card(p, *, in_stock_label=True, force_flash=False):
    cur = p.currency_id
    sym = cur.symbol if cur else 'KD'
    list_p = float(p.list_price or 0)
    comp_p = float(p.compare_list_price or 0)
    has_discount = comp_p > list_p > 0
    discount_pct = int((1 - list_p / comp_p) * 100) if has_discount else 0
    save_amt = comp_p - list_p if has_discount else 0

    # Decide flash-sale membership (demo logic: every 7th product OR forced)
    in_flash = force_flash or (hash(str(p.id)) % 7 == 0)

    # Image-corner badge — discount only
    img_badges = ''
    if discount_pct:
        img_badges += f'<span class="img-badge discount">-{discount_pct}%</span>'

    # Flash banner under the image (matches main flash style)
    flash_banner = ''
    if in_flash:
        flash_banner = f'''
        <div class="pc-flash">
          <span class="pcf-bolt">{_ico("bolt", 10)} FLASH</span>
          <span class="pcf-timer">02:14:37</span>
        </div>'''

    # delivery badges (under the name)
    free_dlv = list_p >= 10
    fast_dlv = (hash(str(p.id)) % 3 == 0)
    badges = []
    if free_dlv:
        badges.append(f'<span class="d-badge free">{_ico("truck", 10)} Free</span>')
    if fast_dlv:
        badges.append(f'<span class="d-badge fast">{_ico("bolt", 10)} Same-day</span>')
    badges_html = ''.join(badges)

    # price block — discount %, was-price (no "Save" word; savings shown as icon at bottom)
    if has_discount:
        price_block = f'''
          <div class="price-row-pc">
            <span class="now">{list_p:.3f} <span class="sym">{sym}</span></span>
            <span class="discount-pill">-{discount_pct}%</span>
          </div>
          <div class="was-row">
            <span class="was">{comp_p:.3f} {sym}</span>
          </div>'''
    else:
        price_block = f'<div class="price-row-pc"><span class="now">{list_p:.3f} <span class="sym">{sym}</span></span></div>'

    # rating — number only in parens
    rating_avg = float(getattr(p, 'rating_avg', 0) or 0)
    rating_count = int(getattr(p, 'rating_count', 0) or 0)
    if rating_count == 0:
        rating_count = (hash(str(p.id)) % 400) + 20
        rating_avg = 3.5 + ((hash(str(p.id)) % 15) / 10)
    rating_html = f'<div class="rating-row"><span class="stars">{"★" * round(rating_avg)}{"☆" * (5-round(rating_avg))}</span><b>{rating_avg:.1f}</b><span class="rcount">({rating_count})</span></div>'

    # Bottom row: SAVE as icon+amount (LEFT) | Availability (RIGHT)
    if has_discount:
        save_html = f'<span class="save-icon" title="You save {save_amt:.3f} {sym}">{_ico("tag",10)} <b>{save_amt:.3f}</b> {sym}</span>'
    else:
        sold = (hash(str(p.id)) % 1500) + 50
        save_html = f'<span class="sold-mini">{sold} sold</span>'

    # Availability — "OUT" or "Available"
    qty_av = int(p.qty_available or 0) if p.is_storable else 999
    if p.is_storable and qty_av <= 0:
        avail_html = '<span class="avail-pill out">OUT</span>'
    elif p.is_storable and qty_av <= 5:
        avail_html = f'<span class="avail-pill low">Only {qty_av}</span>'
    else:
        avail_html = '<span class="avail-pill ok">Available</span>'
    if not in_stock_label:
        avail_html = ''

    return f'''
    <div class="product-card">
      <div class="pc-img">
        {img_badges}
        <img src="{_img("product.template", p.id, "image_512", p.write_date)}" loading="lazy" alt="">
        <div class="pc-img-actions">
          <button class="pc-act wish">{_ico("heart", 14)}</button>
          <button class="pc-act share">{_ico("share", 14)}</button>
        </div>
      </div>
      {flash_banner}
      <div class="pc-body">
        <div class="name">{_esc(p.name)}</div>
        {price_block}
        <div class="meta-row">{rating_html}</div>
        <div class="dlv-badges">{badges_html}</div>
        <div class="bottom-row">
          {save_html}
          {avail_html}
        </div>
      </div>
    </div>'''


# Reusable product-card CSS — drop into any page that uses _product_card
_PRODUCT_CARD_CSS = '''
.product-card { background: #fff; border: 1px solid #F2EBD3; border-radius: 14px;
     padding: 0; position: relative; box-shadow: 0 1px 4px rgba(0,0,0,.05);
     overflow: hidden; transition: transform .15s, box-shadow .15s; }
.product-card:hover { transform: translateY(-2px);
     box-shadow: 0 8px 20px -6px rgba(65,36,2,.18); }
/* Image */
.product-card .pc-img { position: relative; background: #FAFAFA; }
.product-card .pc-img img { width: 100%; aspect-ratio: 1; object-fit: cover;
     display: block; }
.product-card .img-badge { position: absolute; top: 8px; left: 8px;
     padding: 3px 8px; font-size: 10px; font-weight: 800; border-radius: 6px;
     z-index: 2; display: inline-flex; align-items: center; gap: 3px;
     letter-spacing: .3px; }
.product-card .img-badge.discount { background: #FF4D4D; color: #fff;
     box-shadow: 0 3px 8px -2px rgba(255,77,77,.5); }
/* Image action row — bottom of image (not top anymore) */
.product-card .pc-img-actions { position: absolute; bottom: 8px; right: 8px;
     display: flex; gap: 6px; z-index: 2; }
.product-card .pc-act { width: 30px; height: 30px; background: rgba(255,255,255,.95);
     border: 0; border-radius: 50%; color: #9c8a5e; cursor: pointer;
     display: grid; place-items: center; box-shadow: 0 2px 6px rgba(0,0,0,.12);
     transition: color .15s, background .15s; }
.product-card .pc-act:hover { color: #412402; background: #fff; }
.product-card .pc-act.wish:hover { color: #FF4D4D; }
/* Flash banner — sits right under the image, same look as main flash */
.product-card .pc-flash { display: flex; align-items: center;
     justify-content: space-between; padding: 5px 8px;
     background: linear-gradient(135deg,#FF4D4D,#C81212); color: #fff;
     font-size: 10px; font-weight: 900; letter-spacing: .3px; }
.product-card .pcf-bolt { display: inline-flex; align-items: center; gap: 3px; }
.product-card .pcf-timer { font-family: monospace; background: rgba(0,0,0,.3);
     padding: 1px 6px; border-radius: 4px; font-size: 10px; letter-spacing: .5px; }
/* Body */
.product-card .pc-body { padding: 10px 10px 10px; }
.product-card .name { font-size: 12.5px; color: #1a1108; line-height: 1.35;
     overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2;
     -webkit-box-orient: vertical; min-height: 34px; margin-bottom: 8px;
     font-weight: 500; }
.product-card .price-row-pc { display: flex; align-items: center; gap: 6px;
     justify-content: space-between; }
.product-card .now { font-weight: 900; font-size: 17px; color: #412402;
     letter-spacing: -.3px; }
.product-card .now .sym { font-size: 11px; font-weight: 700; color: #9c8a5e;
     margin-inline-start: 2px; }
.product-card .discount-pill { background: #FFE3E3; color: #b91c1c;
     padding: 2px 6px; border-radius: 5px; font-size: 10px; font-weight: 900;
     letter-spacing: .3px; }
.product-card .was-row { margin-top: 2px; }
.product-card .was { font-size: 11.5px; color: #9c8a5e;
     text-decoration: line-through; font-weight: 500; }
.product-card .meta-row { display: flex; align-items: center; gap: 6px;
     margin-top: 6px; flex-wrap: wrap; }
.product-card .rating-row { display: flex; align-items: center; gap: 3px;
     font-size: 10.5px; }
.product-card .stars { color: #F5C320; letter-spacing: -1.5px; font-size: 10px; }
.product-card .rating-row b { color: #412402; font-weight: 800; font-size: 11px; }
.product-card .rcount { color: #9c8a5e; }
.product-card .dlv-badges { display: flex; gap: 4px; flex-wrap: wrap;
     margin: 6px 0 4px; }
.product-card .d-badge { font-size: 9.5px; padding: 2px 6px; border-radius: 5px;
     font-weight: 800; display: inline-flex; align-items: center; gap: 2px;
     letter-spacing: .2px; }
.product-card .d-badge.free { background: #E0F7EC; color: #047857; }
.product-card .d-badge.fast { background: #FFF5D0; color: #C99000; }
.product-card .bottom-row { display: flex; align-items: center;
     justify-content: space-between; margin-top: 6px;
     padding-top: 6px; border-top: 1px dashed #F2EBD3; }
.product-card .save-icon { display: inline-flex; align-items: center; gap: 3px;
     color: #047857; font-size: 11px; font-weight: 700; }
.product-card .save-icon svg { color: #10b981; }
.product-card .save-icon b { font-weight: 900; }
.product-card .sold-mini { font-size: 10px; color: #9c8a5e; font-weight: 600; }
.product-card .avail-pill { font-size: 9.5px; font-weight: 900;
     padding: 2px 7px; border-radius: 4px; letter-spacing: .5px; }
.product-card .avail-pill.ok { background: #ECFDF5; color: #047857; }
.product-card .avail-pill.low { background: #FFF5D0; color: #C99000; }
.product-card .avail-pill.out { background: #FFE3E3; color: #b91c1c; }
'''


# ─── 2. HOME ──────────────────────────────────────────────────────

def render_home(env):
    # Slider
    sliders = env['mobile.slider'].sudo().search([('active','=',True)], order='sequence', limit=4)
    slider_html = ''
    for s in sliders:
        title = _bilingual(s, 'name')['en']
        slider_html += f'<div class="slide" style="background-image:url({_img("mobile.slider", s.id, "image", s.write_date)});"><div class="slide-overlay"><div class="slide-title">{_esc(title)}</div></div></div>'
    if not slider_html:
        slider_html = '<div class="slide demo"><div class="slide-overlay"><div class="slide-title">Big Sale — Up to 70% off · Free delivery KD 10+</div></div></div>'

    # Category strip (top — replaces the old features)
    cats = env['product.public.category'].sudo().search(
        [('parent_id', '=', False)], order='sequence, name', limit=10)
    cat_strip = ''
    if cats:
        cat_strip = '<a class="cstrip-item all">All</a>'
        for c in cats:
            cat_strip += f'<a class="cstrip-item">{_esc(c.name)}</a>'
    else:
        for n in ['All','Phones','Fashion','Home','Beauty','Sports','Watches','Gaming']:
            cat_strip += f'<a class="cstrip-item">{_esc(n)}</a>'

    # Category icons
    icons = env['mobile.category.icon'].sudo().search([('active','=',True)], order='sequence', limit=10)
    icons_html = ''
    if icons:
        for ic in icons:
            n = _bilingual(ic, 'name')['en']
            icons_html += f'<a class="cat-icon"><div class="cat-bubble" style="background-image:url({_img("mobile.category.icon", ic.id, "icon_image", ic.write_date)});"></div><div class="cat-label">{_esc(n)}</div></a>'
    else:
        for emoji, name in [('📱','Phones'),('💻','Laptops'),('👗','Fashion'),
                            ('🏠','Home'),('👶','Baby'),('🎮','Gaming'),
                            ('💄','Beauty'),('⚽','Sports')]:
            icons_html += f'<a class="cat-icon"><div class="cat-bubble emoji">{emoji}</div><div class="cat-label">{name}</div></a>'

    # Flash sale
    flash = env['mobile.flash.sale'].sudo().search([('active','=',True)], limit=1)
    if flash:
        prods = flash._resolved_products()[:6]
        flash_cards = ''.join(_flash_mini_card(p) for p in prods)
        flash_title = flash.name
        flash_sub = flash.subtitle or 'Up to 70% off — hurry!'
    else:
        flash_cards = _demo_flash_cards()
        flash_title = 'Flash Sale'
        flash_sub = 'Up to 70% off — ends tonight'

    flash_html = f'''
    <section class="flash">
      <div class="flash-head">
        <div>
          <div class="flash-title">{_ico("bolt", 16)} {_esc(flash_title)}</div>
          <div class="flash-sub">{_esc(flash_sub)}</div>
        </div>
        <div class="flash-timer"><span>02</span>:<span>14</span>:<span>37</span></div>
      </div>
      <div class="flash-row">{flash_cards}</div>
    </section>'''

    # Features chips (moved DOWN — below slider area)
    features_html = '''
    <div class="features-row">
      <div class="feature-chip">''' + _ico('truck', 14) + '''<span>Free delivery KD 10+</span></div>
      <div class="feature-chip">''' + _ico('bolt', 14) + '''<span>Same-day delivery</span></div>
      <div class="feature-chip">''' + _ico('return', 14) + '''<span>30-day returns</span></div>
      <div class="feature-chip">''' + _ico('shield', 14) + '''<span>Original products</span></div>
    </div>'''

    # Product sections
    sections = env['mobile.product.slider'].sudo().search([('active','=',True)], order='sequence', limit=3)
    sections_html = ''
    for sec in sections:
        title = _bilingual(sec, 'name')['en']
        if sec.category_id:
            tmpl = env['product.template'].sudo().search(
                [('public_categ_ids', 'child_of', sec.category_id.id),
                 ('is_published','=',True)],
                limit=6, order='create_date desc')
        else:
            tmpl = env['product.template'].sudo().search(
                [('is_published','=',True)], limit=6, order='create_date desc')
        cards = ''.join(_product_card(p) for p in tmpl)
        sections_html += f'<section class="psection"><div class="psection-head"><h2>{_esc(title)}</h2><a class="see-all">See all →</a></div><div class="psection-row">{cards}</div></section>'

    if not sections_html:
        tmpl = env['product.template'].sudo().search([('is_published','=',True)], limit=6, order='create_date desc')
        cards = ''.join(_product_card(p) for p in tmpl)
        sections_html = f'<section class="psection"><div class="psection-head"><h2>New arrivals</h2><a class="see-all">See all →</a></div><div class="psection-row">{cards}</div></section>'

    body = '''
<style>
  /* Top bar */
  .topbar { padding: 8px 14px 12px; display: flex; gap: 8px; }
  .topbar input { flex: 1; height: 40px; border-radius: 12px; border: 0;
       padding: 0 14px 0 38px; background: #F2EBD3; color: #5d4d2e;
       font-size: 13px; outline: 0;
       background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='%239c8a5e'><path d='M21 19l-4-4a8 8 0 1 0-2 2l4 4zm-12-3a6 6 0 1 1 6-6 6 6 0 0 1-6 6z'/></svg>");
       background-repeat: no-repeat; background-position: 12px center; }
  .topbar .icon-btn { width: 40px; height: 40px; background: #F2EBD3;
       color: #5d4d2e; border: 0; border-radius: 12px; cursor: pointer;
       display: grid; place-items: center; }
  .topbar .icon-btn:hover { color: #412402; background: #FFE8A0; }

  /* Category strip (top) */
  .cstrip { display: flex; gap: 6px; padding: 0 14px 12px;
       overflow-x: auto; scrollbar-width: none; }
  .cstrip::-webkit-scrollbar { display: none; }
  .cstrip-item { flex: 0 0 auto; padding: 7px 14px; background: #fff;
       border: 1px solid #F2EBD3; color: #5d4d2e; font-size: 12px;
       font-weight: 700; border-radius: 999px; cursor: pointer;
       white-space: nowrap; }
  .cstrip-item.all { background: #412402; color: #FFD340; border-color: #412402; }
  .cstrip-item:hover { border-color: #F5C320; color: #412402; }

  /* Hero slider */
  .hero { padding: 0 14px 14px; }
  .slide { height: 170px; border-radius: 18px; background: #412402;
       background-size: cover; background-position: center;
       position: relative; overflow: hidden; }
  .slide.demo { background: linear-gradient(135deg,#412402,#6e3d05); }
  .slide-overlay { position: absolute; inset: 0; padding: 18px;
       display: flex; align-items: flex-end;
       background: linear-gradient(180deg, transparent 40%, rgba(0,0,0,.55)); }
  .slide-title { color: #FFD340; font-size: 18px; font-weight: 800; max-width: 75%; }

  /* Features (moved below slider) */
  .features-row { display: flex; gap: 6px; padding: 0 14px 14px;
       overflow-x: auto; scrollbar-width: none; }
  .features-row::-webkit-scrollbar { display: none; }
  .feature-chip { flex: 0 0 auto; display: inline-flex; align-items: center;
       gap: 6px; padding: 7px 12px; background: #FFF5D0; color: #412402;
       border-radius: 999px; font-size: 11.5px; font-weight: 700;
       border: 1px solid #FFE8A0; }
  .feature-chip svg { color: #C99000; }

  /* Category icons row */
  .cat-row { display: flex; gap: 14px; padding: 0 14px 18px;
       overflow-x: auto; scrollbar-width: none; }
  .cat-row::-webkit-scrollbar { display: none; }
  .cat-icon { flex: 0 0 auto; width: 64px; text-align: center; cursor: pointer; }
  .cat-bubble { width: 60px; height: 60px; border-radius: 18px;
       background-size: cover; background-position: center; margin: auto;
       box-shadow: 0 4px 10px -5px rgba(65,36,2,.25); }
  .cat-bubble.emoji { background: #FFF5D0; display: grid; place-items: center;
       font-size: 26px; }
  .cat-label { font-size: 11px; color: #412402; margin-top: 6px; font-weight: 600;
       overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

  /* Flash */
  .flash { margin: 0 14px 18px; padding: 14px;
       background: linear-gradient(135deg,#FF4D4D 0%,#C81212 100%);
       border-radius: 18px; color: #fff;
       box-shadow: 0 10px 25px -8px rgba(200,18,18,.35); }
  .flash-head { display: flex; justify-content: space-between;
       align-items: flex-start; margin-bottom: 12px; }
  .flash-title { font-size: 18px; font-weight: 900; display: flex; align-items: center; gap: 6px; }
  .flash-sub { font-size: 11.5px; opacity: .9; margin-top: 2px; }
  .flash-timer { background: rgba(0,0,0,.25); padding: 6px 12px;
       border-radius: 8px; font-family: monospace; font-size: 14px;
       font-weight: 800; letter-spacing: 1px; }
  .flash-row { display: flex; gap: 8px; overflow-x: auto; scrollbar-width: none;
       padding-bottom: 4px; }
  .flash-row::-webkit-scrollbar { display: none; }
  .flash-mini { flex: 0 0 130px; background: #fff; border-radius: 12px;
       padding: 8px; color: #1a1108; }
  .flash-mini img { width: 100%; height: 100px; object-fit: cover; border-radius: 8px; }
  .flash-mini .price { color: #FF4D4D; font-weight: 900; font-size: 15px; margin-top: 4px; }
  .flash-mini .orig { font-size: 11px; color: #999; text-decoration: line-through;
       margin-inline-start: 4px; font-weight: 500; }
  .flash-mini .progress { height: 4px; border-radius: 999px; background: #FFE3E3;
       margin-top: 6px; overflow: hidden; }
  .flash-mini .progress > div { height: 100%; background: linear-gradient(90deg,#FF4D4D,#C81212); }
  .flash-mini .sold { font-size: 10px; color: #999; margin-top: 3px; }

  /* Product sections */
  .psection { padding: 0 14px 18px; }
  .psection-head { display: flex; justify-content: space-between;
       align-items: center; margin: 6px 0 12px; }
  .psection-head h2 { font-size: 16px; font-weight: 800; margin: 0; color: #1a1108; }
  .see-all { color: #5d4d2e; font-size: 12px; font-weight: 700; cursor: pointer; }
  .psection-row { display: flex; gap: 10px; overflow-x: auto;
       scrollbar-width: none; }
  .psection-row::-webkit-scrollbar { display: none; }
  .psection-row .product-card { flex: 0 0 150px; }
''' + _PRODUCT_CARD_CSS + '''
</style>
<div class="topbar">
  <input placeholder="ابحث عن منتج، ماركة، أو ﺗﺎﺟﺮ…">
  <button class="icon-btn">''' + _ico('barcode', 18) + '''</button>
  <button class="icon-btn">''' + _ico('camera', 18) + '''</button>
</div>
<div class="cstrip">''' + cat_strip + '''</div>
<div class="hero">''' + slider_html + '''</div>
''' + features_html + '''
<div class="cat-row">''' + icons_html + '''</div>
''' + flash_html + sections_html + '''

<!-- In-app popup demo (auto-hide) -->
<div id="popupOverlay" style="position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:200;display:none;align-items:center;justify-content:center;padding:30px">
  <div style="background:#fff;border-radius:18px;max-width:300px;overflow:hidden;box-shadow:0 20px 50px rgba(0,0,0,.3)">
    <div style="background:linear-gradient(135deg,#FFD340,#F5C320);height:140px;display:grid;place-items:center;font-size:48px">🎁</div>
    <div style="padding:18px 20px 14px;text-align:center">
      <h3 style="margin:0 0 6px;color:#412402;font-size:18px;font-weight:900">Welcome bonus!</h3>
      <p style="margin:0 0 16px;color:#5d4d2e;font-size:13px;line-height:1.5">Get <b>100 loyalty points</b> when you complete your profile.</p>
      <button onclick="document.getElementById('popupOverlay').style.display='none'" style="width:100%;padding:12px;background:#412402;color:#FFD340;border:0;border-radius:10px;font-weight:800;cursor:pointer">Claim now</button>
      <button onclick="document.getElementById('popupOverlay').style.display='none'" style="margin-top:6px;background:transparent;border:0;color:#9c8a5e;font-size:11px;cursor:pointer">Maybe later</button>
    </div>
  </div>
</div>
<script>
  setTimeout(function(){ document.getElementById('popupOverlay').style.display='flex'; }, 2000);
</script>
'''
    return body, 'Home', True


def _flash_mini_card(p):
    cur = p.currency_id
    sym = cur.symbol if cur else 'KD'
    orig = ''
    if (p.compare_list_price or 0) > (p.list_price or 0):
        orig = f'<span class="orig">{p.compare_list_price:.3f}</span>'
    progress = min(95, (hash(str(p.id)) % 80) + 20)
    sold = (hash(str(p.id)) % 90) + 10
    return f'<div class="flash-mini"><img src="{_img("product.template", p.id, "image_256", p.write_date)}" loading="lazy" alt=""><div class="price">{p.list_price:.3f} {orig}</div><div class="progress"><div style="width:{progress}%"></div></div><div class="sold">Sold {sold}%</div></div>'


def _demo_flash_cards():
    return '''
    <div class="flash-mini"><img src="https://placehold.co/200/F5C320/412402?text=Watch"><div class="price">14.900<span class="orig">29.000</span></div><div class="progress"><div style="width:72%"></div></div><div class="sold">Sold 72%</div></div>
    <div class="flash-mini"><img src="https://placehold.co/200/412402/F5C320?text=Phone"><div class="price">59.500<span class="orig">89.000</span></div><div class="progress"><div style="width:45%"></div></div><div class="sold">Sold 45%</div></div>
    <div class="flash-mini"><img src="https://placehold.co/200/FFE066/412402?text=Buds"><div class="price">9.900<span class="orig">19.500</span></div><div class="progress"><div style="width:88%"></div></div><div class="sold">Sold 88%</div></div>'''


# ─── 3. FLASH SALE — with category + vendor + filters ─────────────

def render_flash(env):
    flash = env['mobile.flash.sale'].sudo().search([('active','=',True)], limit=1)
    if flash:
        prods = flash._resolved_products()[:20]
        title = flash.name
        sub = flash.subtitle or 'Hurry, ends soon!'
    else:
        prods = env['product.template'].sudo().search([('is_published','=',True)], limit=12)
        title = 'Mega Flash Sale'
        sub = 'Up to 70% off · ends in 2h 14m'

    cards = ''.join(_product_card(p) for p in prods)

    # Categories chips (from real cats)
    cats = env['product.public.category'].sudo().search([('parent_id','=',False)], limit=8)
    cat_chips = '<a class="filter-pill on">All</a>'
    for c in cats:
        cat_chips += f'<a class="filter-pill">{_esc(c.name)}</a>'
    if not cats:
        for n in ['Phones','Fashion','Beauty','Home','Sports']:
            cat_chips += f'<a class="filter-pill">{n}</a>'

    # Vendor chips (avatars)
    Vendor = env.get('uellow.vendor')
    vendor_chips = ''
    if Vendor is not None:
        vendors = Vendor.sudo().search([], limit=8)
        for v in vendors:
            initial = (v.store_name_en or 'U')[0]
            vendor_chips += f'<a class="vendor-pill"><div class="vp-avatar">{_esc(initial)}</div><span>{_esc(v.store_name_en or "Uellow")}</span></a>'
    if not vendor_chips:
        for n, c in [('Uellow', '#412402'),('Anker','#FF4D4D'),('Samsung','#3b82f6'),('Huawei','#10b981')]:
            vendor_chips += f'<a class="vendor-pill"><div class="vp-avatar" style="background:{c}">{n[0]}</div><span>{n}</span></a>'

    body = '''
<style>
  .flash-hero { padding: 22px 18px; color: #fff;
       background: linear-gradient(135deg,#FF4D4D 0%,#C81212 100%); }
  .flash-hero h1 { margin: 0; font-size: 24px; font-weight: 900;
       display: flex; align-items: center; gap: 6px; }
  .flash-hero .sub { opacity: .85; margin-top: 4px; font-size: 13px; }
  .countdown { display: flex; gap: 8px; margin-top: 14px; }
  .countdown .cell { flex: 1; background: rgba(0,0,0,.25); border-radius: 10px;
       padding: 10px; text-align: center; }
  .countdown .num { font-size: 24px; font-weight: 900;
       font-variant-numeric: tabular-nums; }
  .countdown .lbl { font-size: 10px; opacity: .7; text-transform: uppercase;
       letter-spacing: .5px; }
  /* Section heading */
  .filter-sec { background: #fff; padding: 14px 14px 8px; border-bottom: 1px solid #F2EBD3; }
  .filter-sec h3 { font-size: 11.5px; color: #9c8a5e; font-weight: 700;
       margin: 0 0 8px; text-transform: uppercase; letter-spacing: .5px; }
  .filter-row { display: flex; gap: 6px; overflow-x: auto; scrollbar-width: none;
       padding-bottom: 8px; }
  .filter-row::-webkit-scrollbar { display: none; }
  .filter-pill { flex: 0 0 auto; padding: 7px 14px; background: #F2EBD3;
       color: #5d4d2e; border-radius: 999px; font-size: 12px;
       font-weight: 700; white-space: nowrap; cursor: pointer; border: 0; }
  .filter-pill.on { background: #412402; color: #FFD340; }
  .vendor-pill { display: inline-flex; align-items: center; gap: 6px;
       padding: 4px 12px 4px 4px; background: #fff; border: 1px solid #F2EBD3;
       border-radius: 999px; font-size: 12px; color: #412402; cursor: pointer;
       flex: 0 0 auto; }
  .vp-avatar { width: 28px; height: 28px; border-radius: 50%; background: #412402;
       color: #FFD340; display: grid; place-items: center;
       font-weight: 900; font-size: 11px; }
  /* Sort bar */
  .sortbar { display: flex; align-items: center; justify-content: space-between;
       background: #fff; padding: 10px 14px;
       border-bottom: 1px solid #F2EBD3; font-size: 12px; }
  .sortbar .count { color: #9c8a5e; }
  .sortbar .actions { display: flex; gap: 14px; }
  .sortbar .actions button { background: transparent; border: 0; cursor: pointer;
       display: inline-flex; align-items: center; gap: 4px;
       color: #412402; font-weight: 700; font-size: 12px; }
  /* Grid */
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px;
       padding: 12px; background: #F8F4E3; }
''' + _PRODUCT_CARD_CSS + '''
</style>
<div class="flash-hero">
  <h1>''' + _ico('bolt', 22) + ''' ''' + _esc(title) + '''</h1>
  <div class="sub">''' + _esc(sub) + '''</div>
  <div class="countdown">
    <div class="cell"><div class="num">02</div><div class="lbl">Hours</div></div>
    <div class="cell"><div class="num">14</div><div class="lbl">Minutes</div></div>
    <div class="cell"><div class="num">37</div><div class="lbl">Seconds</div></div>
  </div>
</div>

<div class="filter-sec">
  <h3>Filter by category</h3>
  <div class="filter-row">''' + cat_chips + '''</div>
  <h3>Filter by vendor</h3>
  <div class="filter-row" style="padding-bottom:4px">''' + vendor_chips + '''</div>
</div>

<div class="sortbar">
  <div class="count"><b>248</b> deals · in stock</div>
  <div class="actions">
    <button>''' + _ico('sort', 14) + '''<span>Sort</span></button>
    <button>''' + _ico('filter', 14) + '''<span>Filters</span></button>
  </div>
</div>

<div class="grid">''' + cards + '''</div>
'''
    return body, 'Flash Sale', True


# ─── 4. PRODUCT PAGE — comprehensive ─────────────────────────────

def render_product(env):
    p = env['product.template'].sudo().search(
        [('is_published','=',True)], limit=1, order='id desc')
    if not p:
        return '<div style="padding:40px;text-align:center">No products yet.</div>', 'Product', True

    cur = p.currency_id
    sym = cur.symbol if cur else 'KD'

    # Gallery
    images = [_img('product.template', p.id, 'image_1024', p.write_date)]
    for img in p.product_template_image_ids[:5]:
        images.append(_img('product.image', img.id, 'image_1024', img.write_date))
    img_slides = ''.join(f'<img src="{u}" loading="lazy" alt="">' for u in images)
    dots = ''.join(f'<span class="{"on" if i==0 else ""}"></span>' for i in range(len(images)))

    # Check if in active flash sale
    flash = env['mobile.flash.sale'].sudo().search([('active','=',True)], limit=1)
    in_flash = False
    flash_banner_html = ''
    if flash and flash.is_live:
        if p.id in flash._resolved_products().ids:
            in_flash = True
    if in_flash:
        flash_banner_html = f'''
        <div class="flash-banner">
          <div class="fb-left">
            <div class="fb-title">{_ico("bolt", 14)} FLASH SALE</div>
            <div class="fb-sub">Limited time only · selling fast</div>
          </div>
          <div class="fb-timer"><span>02</span>:<span>14</span>:<span>37</span></div>
        </div>'''

    # Variants — color = image swatch, size = Smart Fit button
    attribute_lines_html = ''
    has_size = False
    for line in p.attribute_line_ids:
        attr_name = line.attribute_id.name.lower()
        is_color = 'color' in attr_name or 'colour' in attr_name or 'لون' in attr_name
        is_size = 'size' in attr_name or 'مقاس' in attr_name
        if is_size:
            has_size = True
        attr_label = _esc(line.attribute_id.name)
        if is_color:
            sw = ''
            for i, v in enumerate(line.value_ids):
                on = ' on' if i == 0 else ''
                if v.image:
                    img = _img('product.attribute.value', v.id, 'image', v.write_date)
                    sw += f'<div class="img-swatch{on}"><img src="{img}" alt=""><span>{_esc(v.name)}</span></div>'
                else:
                    # Try to find a product.product variant image for this attr value
                    var = p.product_variant_ids.filtered(
                        lambda pv: v.id in pv.product_template_variant_value_ids.mapped('product_attribute_value_id').ids)
                    if var:
                        img = _img('product.product', var[0].id, 'image_256', var[0].write_date)
                        sw += f'<div class="img-swatch{on}"><img src="{img}" alt=""><span>{_esc(v.name)}</span></div>'
                    else:
                        clr = v.html_color or '#412402'
                        sw += f'<div class="img-swatch{on} no-img"><div style="background:{clr}"></div><span>{_esc(v.name)}</span></div>'
            attribute_lines_html += f'<div class="attr-block"><h4>{attr_label}</h4><div class="img-swatches">{sw}</div></div>'
        elif is_size:
            sz = ''
            for i, v in enumerate(line.value_ids):
                on = ' on' if i == 1 else ''
                sz += f'<div class="size-chip{on}">{_esc(v.name)}</div>'
            attribute_lines_html += f'''<div class="attr-block">
              <h4>{attr_label}
                <button class="smart-fit-btn">{_ico("ruler", 14)} Smart Fit</button>
              </h4>
              <div class="size-row">{sz}</div>
            </div>'''
        else:
            opts = ''
            for i, v in enumerate(line.value_ids):
                on = ' on' if i == 0 else ''
                opts += f'<div class="opt-chip{on}">{_esc(v.name)}</div>'
            attribute_lines_html += f'<div class="attr-block"><h4>{attr_label}</h4><div class="opt-row">{opts}</div></div>'

    # If no color attribute, show demo image swatches
    if not attribute_lines_html:
        attribute_lines_html = '''<div class="attr-block"><h4>Color</h4><div class="img-swatches">
          <div class="img-swatch on no-img"><div style="background:#412402"></div><span>Black</span></div>
          <div class="img-swatch no-img"><div style="background:#FF4D4D"></div><span>Red</span></div>
          <div class="img-swatch no-img"><div style="background:#F5C320"></div><span>Gold</span></div>
        </div></div>
        <div class="attr-block"><h4>Size <button class="smart-fit-btn">''' + _ico("ruler", 14) + ''' Smart Fit</button></h4>
        <div class="size-row">
          <div class="size-chip">S</div><div class="size-chip on">M</div>
          <div class="size-chip">L</div><div class="size-chip">XL</div>
        </div></div>'''

    # Vendor — simplified with rating, clickable
    vendor_html = ''
    if 'vendor_id' in p._fields and p.vendor_id:
        v = p.vendor_id
        vendor_html = f'''
        <a class="vendor-simple">
          <div class="vs-avatar">{_esc((v.store_name_en or "U")[0])}</div>
          <div class="vs-text">
            <div class="vs-name">{_esc(v.store_name_en or "Uellow")}</div>
            <div class="vs-rating"><span class="stars">★★★★★</span><span class="rcount">4.8 (1,200 ratings)</span></div>
          </div>
          <span class="vs-arrow">›</span>
        </a>'''

    # Related (same sub-category) — first page (12 items), with infinite scroll demo
    related_html = ''
    related = []
    if p.public_categ_ids:
        related = env['product.template'].sudo().search([
            ('id', '!=', p.id),
            ('public_categ_ids', 'in', p.public_categ_ids.ids),
            ('is_published', '=', True),
        ], limit=12)
    if not related:
        related = env['product.template'].sudo().search(
            [('id','!=',p.id),('is_published','=',True)], limit=12)
    cards = ''.join(_product_card(r) for r in related)
    related_html = f'''
    <section class="psection-block">
      <h3>Related products <span class="hint">{len(related)+88}+ similar items</span></h3>
      <div class="related-grid">{cards}</div>
      <div class="infinite-hint">Showing 12 of 100 · keep scrolling for more</div>
      <button class="load-more-btn">Load more</button>
    </section>'''

    # Recently viewed
    recent = env['product.template'].sudo().search(
        [('id','!=',p.id),('is_published','=',True)], limit=6, order='create_date desc')
    recent_cards = ''.join(_product_card(r) for r in recent)
    recent_html = f'<section class="psection-block"><h3>Recently viewed</h3><div class="rel-row">{recent_cards}</div></section>'

    # Reviewers
    reviewers_html = ''
    Profile = env.get('reviewer.profile')
    if Profile is not None:
        revs = Profile.sudo().search([('state','=','active')],
                                     order='is_online desc, rating desc', limit=3)
        if revs:
            chips = ''
            for r in revs:
                online_dot = '<span class="online-dot"></span>' if r.is_online else ''
                chips += f'<div class="reviewer-chip"><div class="r-avatar">{_esc((r.display_name or "R")[0])}{online_dot}</div><div class="r-text"><div class="r-name">{_esc(r.display_name)}</div><div class="r-meta">{_ico("star",10)} {r.rating:.1f} · {r.review_count} reviews</div></div><button class="r-ask">Ask</button></div>'
            reviewers_html = f'<section class="psection-block"><h3>Expert reviewers <span class="hint">get a second opinion</span></h3>{chips}</section>'

    list_p = float(p.list_price or 0)
    comp_p = float(p.compare_list_price or 0)
    has_disc = comp_p > list_p > 0

    # Stock check — for the CTA bar (Notify Me if out of stock)
    pp_qty = int(p.qty_available or 0) if p.is_storable else 999
    is_out_of_stock = p.is_storable and pp_qty <= 0
    if is_out_of_stock:
        cta_html = '''
        <button class="cta notify-me">''' + _ico('bell',16) + ''' Notify me when available</button>'''
    else:
        cta_html = '''
        <div class="qty"><button>−</button><span>1</span><button>+</button></div>
        <button class="cta cart">''' + _ico('cart',16) + ''' Add to cart</button>
        <button class="cta buy">''' + _ico('bolt',16) + ''' Buy now</button>'''

    body = '''
<style>
  body { background: #F8F4E3; }
  /* Gallery */
  .gallery { position: relative; background: #fff; }
  .slide-strip { display: flex; overflow-x: auto; scroll-snap-type: x mandatory; scrollbar-width: none; }
  .slide-strip::-webkit-scrollbar { display: none; }
  .slide-strip img { flex: 0 0 100%; width: 100%; height: 380px;
       object-fit: contain; scroll-snap-align: start; }
  .dots { position: absolute; bottom: 14px; left: 50%; transform: translateX(-50%);
       display: flex; gap: 6px; }
  .dots span { width: 6px; height: 6px; border-radius: 50%; background: rgba(0,0,0,.25); }
  .dots span.on { background: #412402; width: 18px; border-radius: 3px; }
  .back { position: absolute; top: 14px; left: 14px; width: 38px; height: 38px;
       background: rgba(255,255,255,.95); border-radius: 12px; display: grid;
       place-items: center; font-weight: 800; color: #412402; }
  .icons-tr { position: absolute; top: 14px; right: 14px; display: flex; gap: 8px; }
  .icons-tr button { width: 38px; height: 38px; background: rgba(255,255,255,.95);
       border: 0; border-radius: 12px; cursor: pointer; color: #412402;
       display: grid; place-items: center; }
  .icons-tr button:hover { color: #FF4D4D; }

  /* Flash banner under image */
  .flash-banner { background: linear-gradient(135deg,#FF4D4D,#C81212); color: #fff;
       padding: 12px 16px; display: flex; align-items: center;
       justify-content: space-between; }
  .fb-left .fb-title { font-weight: 900; font-size: 14px; display: flex; align-items: center; gap: 4px; }
  .fb-left .fb-sub { font-size: 11px; opacity: .9; }
  .fb-timer { background: rgba(0,0,0,.3); padding: 6px 12px; border-radius: 8px;
       font-family: monospace; font-weight: 800; letter-spacing: 1px; font-size: 14px; }

  /* Title section */
  .ptitle { padding: 14px 18px 6px; background: #fff; }
  .ptitle h1 { font-size: 18px; font-weight: 800; line-height: 1.4;
       margin: 0 0 8px; color: #1a1108; }
  .ptitle .meta-line { display: flex; gap: 6px; flex-wrap: wrap;
       margin-bottom: 8px; }
  .ptitle .meta-chip { display: inline-flex; align-items: center; gap: 4px;
       background: #F2EBD3; color: #5d4d2e; padding: 3px 8px;
       border-radius: 6px; font-size: 11px; font-weight: 700; }
  .ptitle .meta-chip svg { color: #9c8a5e; }
  .ptitle .ratings { display: flex; align-items: center; gap: 6px;
       font-size: 13px; color: #5d4d2e; }
  .ptitle .ratings .stars { color: #F5C320; letter-spacing: -1px; font-size: 14px; }
  .ptitle .ratings b { color: #412402; font-weight: 800; }
  .ptitle .ratings .reviews-link { color: #5d4d2e; font-weight: 600;
       text-decoration: underline; cursor: pointer; }
  .price-row { display: flex; align-items: flex-end; gap: 10px; flex-wrap: wrap;
       padding: 0 18px 14px; background: #fff; }
  .price-row .now { font-size: 28px; font-weight: 900; color: #412402; }
  .price-row .was { font-size: 14px; color: #999; text-decoration: line-through; }
  .price-row .save-pill { background: #FF4D4D; color: #fff; padding: 4px 8px;
       border-radius: 6px; font-size: 11px; font-weight: 800; }
  .price-row .save-pct { background: #ECFDF5; color: #047857; padding: 4px 8px;
       border-radius: 6px; font-size: 11px; font-weight: 800; }

  /* Compact delivery */
  .compact-delivery { background: #fff; padding: 12px 18px;
       border-top: 1px solid #F2EBD3; }
  .cd-row { display: flex; align-items: center; gap: 10px;
       cursor: pointer; }
  .cd-icon { width: 32px; height: 32px; background: #FFF5D0; color: #C99000;
       border-radius: 10px; display: grid; place-items: center; flex-shrink: 0; }
  .cd-body { flex: 1; font-size: 12px; color: #5d4d2e; line-height: 1.4; }
  .cd-body b { color: #412402; }
  .cd-body .city-row { font-weight: 700; color: #1a1108; }
  .cd-chev { color: #9c8a5e; font-size: 18px; }

  /* Vendor simple */
  .vendor-simple { display: flex; gap: 10px; align-items: center;
       padding: 12px 18px; background: #fff; cursor: pointer;
       border-top: 1px solid #F2EBD3; text-decoration: none; color: inherit; }
  .vs-avatar { width: 38px; height: 38px; border-radius: 10px; background: #FFD340;
       color: #412402; display: grid; place-items: center;
       font-weight: 900; font-size: 16px; }
  .vs-text { flex: 1; min-width: 0; }
  .vs-name { font-weight: 800; font-size: 13.5px; color: #1a1108; }
  .vs-rating { display: flex; align-items: center; gap: 4px;
       font-size: 11px; color: #9c8a5e; margin-top: 2px; }
  .vs-rating .stars { color: #F5C320; letter-spacing: -1px; }
  .vs-arrow { font-size: 20px; color: #cbb78a; }

  /* Attribute blocks */
  .attr-block { padding: 12px 18px; background: #fff;
       border-top: 1px solid #F2EBD3; }
  .attr-block h4 { font-size: 13px; margin: 0 0 10px; color: #412402;
       font-weight: 800; display: flex; align-items: center; justify-content: space-between; }
  .smart-fit-btn { background: linear-gradient(135deg,#FFD340,#F5C320);
       color: #412402; border: 0; padding: 6px 12px; border-radius: 8px;
       font-weight: 800; font-size: 11px; cursor: pointer;
       display: inline-flex; align-items: center; gap: 4px; }
  /* Image swatches */
  .img-swatches { display: flex; gap: 8px; flex-wrap: wrap; }
  .img-swatch { cursor: pointer; padding: 4px; border: 2px solid transparent;
       border-radius: 10px; width: 60px; transition: border-color .15s; }
  .img-swatch.on { border-color: #F5C320; background: #FFFCEF; }
  .img-swatch img, .img-swatch > div { width: 100%; height: 50px;
       object-fit: cover; border-radius: 6px; display: block; }
  .img-swatch.no-img > div { background: #412402; }
  .img-swatch span { display: block; font-size: 10px; text-align: center;
       margin-top: 4px; color: #5d4d2e; font-weight: 600; }
  /* Sizes */
  .size-row { display: flex; gap: 6px; flex-wrap: wrap; }
  .size-chip { min-width: 44px; padding: 8px 12px; border: 1.5px solid #F2EBD3;
       border-radius: 10px; text-align: center; font-weight: 700;
       font-size: 13px; cursor: pointer; color: #5d4d2e; background: #fff; }
  .size-chip.on { border-color: #412402; background: #412402; color: #FFD340; }
  /* Generic chips */
  .opt-row { display: flex; gap: 6px; flex-wrap: wrap; }
  .opt-chip { padding: 8px 14px; border-radius: 10px; background: #F2EBD3;
       font-weight: 700; font-size: 12px; color: #5d4d2e; cursor: pointer; }
  .opt-chip.on { background: #412402; color: #FFD340; }

  /* Generic block */
  .psection-block { background: #fff; padding: 16px 18px; margin-top: 8px; }
  .psection-block h3 { font-size: 14px; font-weight: 800; margin: 0 0 12px;
       color: #412402; display: flex; align-items: center; gap: 6px; }
  .psection-block h3 .hint { font-weight: 400; font-size: 11px;
       color: #9c8a5e; margin-inline-start: auto; }

  /* Bulk pricing PRO */
  .bulk-table-pro { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; }
  .bulk-tier { background: #FFFCEF; border: 2px solid #F2EBD3; border-radius: 12px;
       padding: 14px 8px 12px; text-align: center; cursor: pointer;
       transition: all .15s; }
  .bulk-tier.best { border-color: #F5C320; background: linear-gradient(180deg,#FFFCEF 0%,#FFF5D0 100%);
       box-shadow: 0 6px 14px -6px rgba(245,195,32,.4); position: relative; }
  .bulk-tier.best::before { content: "BEST VALUE"; position: absolute;
       top: -10px; left: 50%; transform: translateX(-50%); background: #412402;
       color: #FFD340; font-size: 9px; padding: 2px 8px; border-radius: 999px;
       font-weight: 800; letter-spacing: .5px; white-space: nowrap; }
  .bulk-qty { font-size: 11px; color: #9c8a5e; font-weight: 700; margin-bottom: 4px; }
  .bulk-price { font-size: 16px; font-weight: 900; color: #412402; }
  .bulk-unit { font-size: 10px; color: #9c8a5e; }
  .bulk-save { font-size: 10px; color: #10b981; font-weight: 800;
       background: #E0F7EC; padding: 2px 6px; border-radius: 4px;
       display: inline-block; margin-top: 6px; }

  /* Description — collapsible with fade */
  .desc-block .desc-collapsed { position: relative; max-height: 200px;
       overflow: hidden; color: #1a1108; }
  .desc-block .desc-collapsed p { margin: 0 0 10px; font-size: 13px;
       line-height: 1.6; color: #5d4d2e; }
  .desc-block .desc-collapsed ul { margin: 8px 0; padding-inline-start: 18px;
       color: #5d4d2e; font-size: 13px; line-height: 1.7; }
  .desc-block .desc-collapsed ul li { margin: 3px 0; }
  .desc-block .desc-fade { position: absolute; bottom: 0; left: 0; right: 0;
       height: 70px;
       background: linear-gradient(180deg, rgba(255,255,255,0) 0%, #fff 90%);
       backdrop-filter: blur(0.5px); pointer-events: none; }
  .desc-block .see-more-btn { width: 100%; margin-top: 10px; padding: 12px;
       background: #FFF5D0; border: 1px solid #FFE8A0; border-radius: 12px;
       color: #412402; font-weight: 800; font-size: 13px; cursor: pointer; }

  /* Specifications opener (separate section, opens dialog) */
  .specs-opener { cursor: pointer; transition: background .15s; }
  .specs-opener:hover { background: #FFFCEF; }
  .specs-opener .so-row { display: flex; align-items: center; gap: 12px; }
  .specs-opener .so-ico { width: 38px; height: 38px; background: #FFF5D0;
       color: #C99000; border-radius: 10px; display: grid; place-items: center;
       flex-shrink: 0; }
  .specs-opener .so-text { flex: 1; }
  .specs-opener .so-title { font-size: 14px; font-weight: 800; color: #412402; }
  .specs-opener .so-sub { font-size: 11px; color: #9c8a5e; margin-top: 2px; }
  .specs-opener .so-arrow { font-size: 22px; color: #cbb78a; }

  /* Dialog overlay (modal) */
  .dlg-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.55);
       z-index: 100; display: none; align-items: flex-end; justify-content: center; }
  .dlg-overlay.show { display: flex; }
  .dlg { background: #fff; width: 100%; max-height: 88vh; border-radius: 20px 20px 0 0;
       overflow: hidden; display: flex; flex-direction: column;
       animation: dlgUp .25s ease-out; }
  @keyframes dlgUp { from { transform: translateY(100%); } to { transform: translateY(0); } }
  .dlg-head { display: flex; align-items: center; justify-content: space-between;
       padding: 16px 18px 12px; border-bottom: 1px solid #F2EBD3; }
  .dlg-head h3 { margin: 0; color: #412402; font-size: 16px; font-weight: 800; }
  .dlg-close { width: 32px; height: 32px; background: #F2EBD3; color: #412402;
       border: 0; border-radius: 50%; font-size: 18px; font-weight: 700; cursor: pointer; }
  .dlg-body { padding: 16px 18px 30px; overflow-y: auto; flex: 1; }
  .dlg-body p { margin: 0 0 12px; font-size: 13.5px; line-height: 1.65; color: #1a1108; }
  .dlg-body h4 { margin: 16px 0 8px; font-size: 13px; color: #412402; font-weight: 800; }
  .dlg-body ul { padding-inline-start: 18px; color: #5d4d2e;
       font-size: 13px; line-height: 1.7; margin: 0 0 12px; }
  .specs-table { width: 100%; border-collapse: collapse; font-size: 13.5px; }
  .specs-table tr { border-bottom: 1px solid #F2EBD3; }
  .specs-table tr:last-child { border-bottom: 0; }
  .specs-table td { padding: 11px 0; }
  .specs-table td:first-child { color: #9c8a5e; font-weight: 600; width: 45%; }
  .specs-table td:last-child { color: #1a1108; font-weight: 700; }

  /* Reviewers */
  .reviewer-chip { display: flex; gap: 10px; align-items: center;
       background: #FFFBE5; border: 1px solid #FFE8A0; padding: 10px 12px;
       border-radius: 12px; margin-bottom: 6px; }
  .r-avatar { position: relative; width: 36px; height: 36px; border-radius: 50%;
       background: #412402; color: #FFD340; display: grid; place-items: center;
       font-weight: 800; }
  .r-avatar .online-dot { position: absolute; bottom: 0; right: 0;
       width: 10px; height: 10px; border-radius: 50%; background: #10b981;
       border: 2px solid #FFFBE5; }
  .r-text { flex: 1; }
  .r-name { font-weight: 700; font-size: 13px; color: #1a1108; }
  .r-meta { font-size: 11px; color: #9c8a5e; display: flex; align-items: center; gap: 4px; }
  .r-meta svg { color: #F5C320; }
  .r-ask { padding: 6px 14px; background: #FFD340; color: #412402; border: 0;
       border-radius: 8px; font-weight: 800; font-size: 12px; cursor: pointer; }

  /* Related grid + infinite */
  .related-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
  .infinite-hint { text-align: center; font-size: 11px; color: #9c8a5e;
       padding: 14px 0 10px; }
  .load-more-btn { width: 100%; padding: 12px; background: #FFF5D0;
       border: 1px solid #FFE8A0; color: #412402; font-weight: 800;
       border-radius: 12px; cursor: pointer; }
  /* Recently viewed row */
  .rel-row { display: flex; gap: 10px; overflow-x: auto; scrollbar-width: none;
       margin: 0 -18px; padding: 0 18px; }
  .rel-row::-webkit-scrollbar { display: none; }
  .rel-row .product-card { flex: 0 0 140px; }

  /* Sticky CTA */
  .cta-bar { position: fixed; bottom: 78px; left: 0; right: 0; padding: 12px 14px;
       background: #fff; border-top: 1px solid #F2EBD3; display: flex; gap: 8px;
       z-index: 40; box-shadow: 0 -4px 12px rgba(0,0,0,.04); }
  .cta-bar .qty { display: flex; align-items: center; background: #F2EBD3;
       border-radius: 10px; padding: 4px; gap: 4px; }
  .cta-bar .qty button { width: 28px; height: 28px; border: 0; background: #fff;
       color: #412402; font-weight: 900; border-radius: 6px; cursor: pointer; }
  .cta-bar .qty span { min-width: 22px; text-align: center; font-weight: 800; }
  .cta-bar .cta { flex: 1; padding: 13px; border: 0; border-radius: 12px;
       font-weight: 800; cursor: pointer; font-size: 14px;
       display: inline-flex; justify-content: center; align-items: center; gap: 6px; }
  .cta-bar .cart { background: #FFD340; color: #412402; }
  .cta-bar .buy { background: #412402; color: #FFD340; }
  .cta-bar .notify-me { width: 100%; padding: 14px; background: #412402;
       color: #FFD340; border: 0; border-radius: 12px; font-weight: 800;
       font-size: 14px; cursor: pointer;
       display: inline-flex; justify-content: center; align-items: center; gap: 8px; }
  .cta-bar .notify-me:hover { background: #2a1801; }

''' + _PRODUCT_CARD_CSS + '''
  /* Override product-card inside grids for consistency */
  .related-grid .product-card, .rel-row .product-card { padding: 6px; }
  .related-grid .product-card .pc-img img { aspect-ratio: 1; }
</style>

<div class="gallery">
  <div class="back">←</div>
  <div class="icons-tr">
    <button>''' + _ico('heart', 18) + '''</button>
    <button>''' + _ico('share', 18) + '''</button>
  </div>
  <div class="slide-strip">''' + img_slides + '''</div>
  <div class="dots">''' + dots + '''</div>
</div>

''' + flash_banner_html + '''

<div class="ptitle">
  <h1>''' + _esc(p.name) + '''</h1>
  <div class="meta-line">
    <span class="meta-chip">''' + _ico('box', 11) + ''' ID ''' + str(p.id) + '''</span>
    <span class="meta-chip">''' + _ico('cart', 11) + ''' 1.2k sold</span>
    <span class="meta-chip">''' + _ico('eye', 11) + ''' 71 views</span>
  </div>
  <div class="ratings"><span class="stars">★★★★★</span><b>4.7</b> <a class="reviews-link">(320)</a></div>
</div>

<div class="price-row">
  <span class="now">''' + f'{list_p:.3f} {sym}' + '''</span>
  ''' + (f'<span class="was">{comp_p:.3f}</span>' if has_disc else '') + '''
  ''' + (f'<span class="save-pct">-{int((1-list_p/comp_p)*100)}%</span>' if has_disc else '') + '''
  ''' + (f'<span class="save-pill">Save {comp_p-list_p:.3f} {sym}</span>' if has_disc else '') + '''
</div>

''' + vendor_html + attribute_lines_html + '''

<!-- Compact delivery — moved BELOW variations -->
<div class="compact-delivery">
  <div class="cd-row">
    <div class="cd-icon">''' + _ico('pin', 16) + '''</div>
    <div class="cd-body">
      <div class="city-row">Deliver to <b>Hawalli, Kuwait</b></div>
      <div>FREE · arrives <b>tomorrow</b> · Same-day <b>2.000 KD</b></div>
    </div>
    <span class="cd-chev">›</span>
  </div>
</div>

<!-- Bulk pricing — PRO version -->
<section class="psection-block">
  <h3>''' + _ico('tag', 14) + ''' Bulk pricing <span class="hint">save more, buy more</span></h3>
  <div class="bulk-table-pro">
    <div class="bulk-tier">
      <div class="bulk-qty">1 — 4 pcs</div>
      <div class="bulk-price">''' + f'{list_p:.3f}' + '''</div>
      <div class="bulk-unit">''' + sym + ''' / pc</div>
    </div>
    <div class="bulk-tier">
      <div class="bulk-qty">5 — 9 pcs</div>
      <div class="bulk-price">''' + f'{list_p*0.91:.3f}' + '''</div>
      <div class="bulk-unit">''' + sym + ''' / pc</div>
      <div class="bulk-save">Save 9%</div>
    </div>
    <div class="bulk-tier best">
      <div class="bulk-qty">10+ pcs</div>
      <div class="bulk-price">''' + f'{list_p*0.81:.3f}' + '''</div>
      <div class="bulk-unit">''' + sym + ''' / pc</div>
      <div class="bulk-save">Save 19%</div>
    </div>
  </div>
</section>

<!-- Description — collapsible with fade + See More dialog -->
<section class="psection-block desc-block">
  <h3>Description</h3>
  <div class="desc-collapsed">
    <p>Stay connected, fit, and stylish with the <b>''' + _esc(p.name) + '''</b>. Featuring a vibrant always-on AMOLED display, 24/7 heart rate monitoring, built-in GPS tracking, and an impressive 14-day battery life on a single charge. Perfect for active lifestyles and everyday wear.</p>
    <ul>
      <li>1.39" AMOLED touchscreen with always-on mode</li>
      <li>100+ workout modes with auto-detect</li>
      <li>5 ATM water resistance — swim-proof up to 50 meters</li>
      <li>Sleep, stress &amp; SpO2 monitoring</li>
      <li>Compatible with iOS 12+ and Android 8+</li>
      <li>Interchangeable silicone strap (22mm)</li>
      <li>Bluetooth 5.2 for stable, low-power connectivity</li>
    </ul>
    <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nullam vitae justo eu enim consectetur convallis. Donec auctor risus ac magna eleifend dictum.</p>
    <div class="desc-fade"></div>
  </div>
  <button class="see-more-btn" onclick="document.getElementById('descDialog').classList.add('show')">See full description ›</button>
</section>

<!-- Specifications — separate section, opens dialog -->
<section class="psection-block specs-opener" onclick="document.getElementById('specsDialog').classList.add('show')">
  <div class="so-row">
    <div class="so-ico">''' + _ico('grid', 18) + '''</div>
    <div class="so-text">
      <div class="so-title">Specifications</div>
      <div class="so-sub">Brand, dimensions, materials, warranty &amp; more</div>
    </div>
    <span class="so-arrow">›</span>
  </div>
</section>

<!-- Description dialog -->
<div class="dlg-overlay" id="descDialog">
  <div class="dlg">
    <div class="dlg-head">
      <h3>Description</h3>
      <button class="dlg-close" onclick="document.getElementById('descDialog').classList.remove('show')">×</button>
    </div>
    <div class="dlg-body">
      <p>Stay connected, fit, and stylish with the <b>''' + _esc(p.name) + '''</b>. Featuring a vibrant always-on AMOLED display, 24/7 heart rate monitoring, built-in GPS tracking, and an impressive 14-day battery life on a single charge. Perfect for active lifestyles and everyday wear.</p>
      <h4>Key features</h4>
      <ul>
        <li>1.39" AMOLED touchscreen with always-on mode</li>
        <li>100+ workout modes with auto-detect</li>
        <li>5 ATM water resistance — swim-proof up to 50 meters</li>
        <li>Sleep, stress &amp; SpO2 monitoring</li>
        <li>Compatible with iOS 12+ and Android 8+</li>
        <li>Interchangeable silicone strap (22mm)</li>
        <li>Bluetooth 5.2 for stable, low-power connectivity</li>
      </ul>
      <h4>What's in the box</h4>
      <ul>
        <li>1 × HainoTeko-18 Smart Watch</li>
        <li>1 × Magnetic charging cable</li>
        <li>1 × Quick start guide</li>
        <li>1 × Warranty card</li>
      </ul>
      <h4>Care &amp; maintenance</h4>
      <p>Wipe with a soft, dry cloth after exposure to sweat or water. Avoid harsh chemicals. While 5ATM rated, hot water and steam can damage the seals — avoid showers and saunas.</p>
    </div>
  </div>
</div>

<!-- Specifications dialog -->
<div class="dlg-overlay" id="specsDialog">
  <div class="dlg">
    <div class="dlg-head">
      <h3>Specifications</h3>
      <button class="dlg-close" onclick="document.getElementById('specsDialog').classList.remove('show')">×</button>
    </div>
    <div class="dlg-body">
      <table class="specs-table">
        <tr><td>Brand</td><td>HainoTeko</td></tr>
        <tr><td>Model</td><td>HainoTeko-18 Pro</td></tr>
        <tr><td>Display</td><td>1.39" AMOLED · 454 × 454</td></tr>
        <tr><td>Battery</td><td>410mAh · up to 14 days</td></tr>
        <tr><td>Water resistance</td><td>5 ATM (50m)</td></tr>
        <tr><td>Connectivity</td><td>Bluetooth 5.2</td></tr>
        <tr><td>Sensors</td><td>HR · SpO2 · Accelerometer · Gyro</td></tr>
        <tr><td>Compatibility</td><td>iOS 12+ / Android 8+</td></tr>
        <tr><td>Strap</td><td>Silicone · interchangeable 22mm</td></tr>
        <tr><td>Weight</td><td>52g (with strap)</td></tr>
        <tr><td>Charging</td><td>Magnetic · ~90 min full charge</td></tr>
        <tr><td>Warranty</td><td>12 months</td></tr>
        <tr><td>SKU</td><td>''' + _esc(p.default_code or "—") + '''</td></tr>
        <tr><td>Country of origin</td><td>China</td></tr>
      </table>
    </div>
  </div>
</div>

<!-- Customer reviews — moved BEFORE recently viewed + related -->
<section class="psection-block">
  <h3>Customer reviews</h3>
  <div style="display:flex;align-items:center;gap:14px;margin-bottom:12px">
    <div style="font-size:42px;font-weight:900;color:#412402;line-height:1">4.7</div>
    <div>
      <div style="color:#F5C320;font-size:16px">★★★★★</div>
      <div style="color:#9c8a5e;font-size:11px;margin-top:2px">Based on 320 verified buyers</div>
    </div>
  </div>
  <div style="background:#FFF5D0;padding:10px 14px;border-radius:10px">
    <div style="font-size:11px;color:#5d4d2e;display:flex;gap:8px;align-items:center;margin:3px 0"><b style="width:22px">5★</b><div style="flex:1;height:6px;background:rgba(0,0,0,.06);border-radius:999px;overflow:hidden"><div style="width:78%;height:100%;background:linear-gradient(90deg,#F5C320,#FFD340)"></div></div><span>250</span></div>
    <div style="font-size:11px;color:#5d4d2e;display:flex;gap:8px;align-items:center;margin:3px 0"><b style="width:22px">4★</b><div style="flex:1;height:6px;background:rgba(0,0,0,.06);border-radius:999px;overflow:hidden"><div style="width:14%;height:100%;background:linear-gradient(90deg,#F5C320,#FFD340)"></div></div><span>45</span></div>
    <div style="font-size:11px;color:#5d4d2e;display:flex;gap:8px;align-items:center;margin:3px 0"><b style="width:22px">3★</b><div style="flex:1;height:6px;background:rgba(0,0,0,.06);border-radius:999px;overflow:hidden"><div style="width:4%;height:100%;background:linear-gradient(90deg,#F5C320,#FFD340)"></div></div><span>13</span></div>
  </div>
  <div style="margin-top:14px">
    <h4 style="font-size:12px;color:#5d4d2e;margin:0 0 8px">📸 Photos from buyers (24)</h4>
    <div style="display:flex;gap:6px">
      <img src="https://placehold.co/120x120/F5C320/412402" style="width:64px;height:64px;border-radius:8px;object-fit:cover">
      <img src="https://placehold.co/120x120/412402/F5C320" style="width:64px;height:64px;border-radius:8px;object-fit:cover">
      <img src="https://placehold.co/120x120/FFE066/412402" style="width:64px;height:64px;border-radius:8px;object-fit:cover">
      <img src="https://placehold.co/120x120/c4a460/fff" style="width:64px;height:64px;border-radius:8px;object-fit:cover">
      <div style="width:64px;height:64px;border-radius:8px;background:#412402;color:#FFD340;display:grid;place-items:center;font-weight:900;font-size:13px">+20</div>
    </div>
  </div>
  <button class="load-more-btn" style="margin-top:14px">See all 320 reviews →</button>
</section>

''' + reviewers_html + recent_html + related_html + '''

<div style="height:100px"></div>
<div class="cta-bar">''' + cta_html + '''</div>
<script>
  // Dismiss dialogs on overlay click
  document.querySelectorAll('.dlg-overlay').forEach(function(o){
    o.addEventListener('click', function(e){
      if (e.target === o) o.classList.remove('show');
    });
  });
</script>
'''
    return body, 'Product', True


# ─── 5. VENDOR STORE — with flash + tabs ──────────────────────────

def render_vendor(env):
    Vendor = env.get('uellow.vendor')
    if Vendor is None:
        return '<p style="padding:40px;text-align:center">Multi-vendor module not installed.</p>', 'Vendor', True
    v = Vendor.sudo().search([], limit=1)
    if not v:
        return '<p style="padding:40px;text-align:center">No vendors yet.</p>', 'Vendor', True

    prods = env['product.template'].sudo().search(
        [('vendor_id', '=', v.id), ('is_published','=',True)], limit=12)
    if not prods:
        prods = env['product.template'].sudo().search([('is_published','=',True)], limit=12)

    # Vendor flash sale (mock)
    flash_prods = prods[:4]
    flash_cards = ''.join(_flash_mini_card(p) for p in flash_prods)

    # Best sellers vs new arrivals
    new_cards = ''.join(_product_card(p) for p in prods[:6])
    best_cards = ''.join(_product_card(p) for p in list(prods)[::-1][:6])

    body = '''
<style>
  body { background: #F8F4E3; }
  .v-hero { height: 160px; background: linear-gradient(135deg,#412402,#7a4a08);
       background-size: cover; background-position: center; position: relative; }
  .v-info { display: flex; gap: 14px; padding: 14px 18px 18px; background: #fff;
       margin-top: -40px; border-radius: 20px 20px 0 0; position: relative; }
  .v-logo { width: 78px; height: 78px; border-radius: 18px; background: #FFD340;
       display: grid; place-items: center; font-size: 30px; font-weight: 900;
       color: #412402; box-shadow: 0 8px 18px -6px rgba(0,0,0,.3); }
  .v-name { font-size: 17px; font-weight: 900; margin: 4px 0; color: #1a1108; }
  .v-meta { font-size: 11.5px; color: #7a6748; line-height: 1.4; }
  .follow-btn { padding: 7px 14px; background: #412402; color: #FFD340;
       border: 0; border-radius: 8px; font-weight: 700; font-size: 12px; margin-top: 8px;
       display: inline-flex; align-items: center; gap: 4px; }
  .chat-btn { padding: 7px 12px; background: #F2EBD3; color: #412402;
       border: 0; border-radius: 8px; font-weight: 700; font-size: 12px;
       margin-inline-start: 6px; display: inline-flex; align-items: center; gap: 4px; }
  .v-stats { display: flex; gap: 8px; padding: 0 18px 14px; background: #fff; }
  .v-stat { flex: 1; background: #FFFCEF; padding: 10px; border-radius: 12px;
       text-align: center; border: 1px solid #FFE8A0; }
  .v-stat strong { display: block; font-size: 16px; color: #412402; }
  .v-stat span { font-size: 10px; color: #7a6748; }
  /* Tabs */
  .v-tabs { display: flex; background: #fff; border-bottom: 1px solid #F2EBD3;
       overflow-x: auto; scrollbar-width: none; position: sticky; top: 0; z-index: 5; }
  .v-tabs::-webkit-scrollbar { display: none; }
  .v-tab { padding: 14px 16px; font-size: 13px; font-weight: 700; color: #9c8a5e;
       cursor: pointer; border-bottom: 2px solid transparent; white-space: nowrap; }
  .v-tab.on { color: #412402; border-bottom-color: #F5C320; }

  /* Internal flash */
  .v-flash { margin: 12px 14px 16px; padding: 14px;
       background: linear-gradient(135deg,#FF4D4D 0%,#C81212 100%);
       border-radius: 16px; color: #fff;
       box-shadow: 0 10px 25px -8px rgba(200,18,18,.3); }
  .v-flash-head { display: flex; justify-content: space-between;
       align-items: flex-start; margin-bottom: 10px; }
  .v-flash-title { font-size: 16px; font-weight: 900; display: flex; align-items: center; gap: 4px; }
  .v-flash-sub { font-size: 11px; opacity: .9; }
  .v-flash-timer { background: rgba(0,0,0,.25); padding: 5px 10px;
       border-radius: 8px; font-family: monospace; font-weight: 800;
       letter-spacing: 1px; font-size: 13px; }
  .v-flash-row { display: flex; gap: 8px; overflow-x: auto; scrollbar-width: none; }
  .v-flash-row::-webkit-scrollbar { display: none; }
  .flash-mini { flex: 0 0 120px; background: #fff; border-radius: 10px;
       padding: 6px; color: #1a1108; }
  .flash-mini img { width: 100%; height: 90px; object-fit: cover; border-radius: 6px; }
  .flash-mini .price { color: #FF4D4D; font-weight: 900; font-size: 13px; margin-top: 4px; }
  .flash-mini .orig { font-size: 10px; color: #999;
       text-decoration: line-through; font-weight: 500; margin-inline-start: 4px; }
  .flash-mini .progress { height: 3px; background: #FFE3E3; border-radius: 999px;
       margin-top: 4px; overflow: hidden; }
  .flash-mini .progress > div { height: 100%;
       background: linear-gradient(90deg,#FF4D4D,#C81212); }
  .flash-mini .sold { font-size: 9px; color: #999; }

  /* Section */
  .v-section { margin-top: 8px; background: #fff; padding: 14px 14px 14px; }
  .v-section h3 { font-size: 14px; font-weight: 800; color: #412402;
       margin: 0 0 12px; display: flex; align-items: center; }
  .v-section h3 .see { margin-inline-start: auto; font-size: 11px;
       color: #5d4d2e; font-weight: 700; }
  .v-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }

''' + _PRODUCT_CARD_CSS + '''
</style>
<div class="v-hero" style="background-image:url(''' + _img('uellow.vendor', v.id, 'banner_image') + ''')"></div>
<div class="v-info">
  <div class="v-logo">''' + _esc((v.store_name_en or 'U')[0]) + '''</div>
  <div style="flex:1">
    <div class="v-name">''' + _esc(v.store_name_en or 'Uellow') + '''</div>
    <div class="v-meta">''' + _esc(v.store_tagline_en or 'Official vendor') + '''<br>
    <span style="color:#F5C320">★★★★★</span> 4.8 · 1.2k reviews · Ships same-day</div>
    <div>
      <button class="follow-btn">+ Follow</button>
      <button class="chat-btn">''' + _ico('chat',12) + ''' Chat</button>
    </div>
  </div>
</div>
<div class="v-stats">
  <div class="v-stat"><strong>''' + str(len(prods)*20) + '''</strong><span>Products</span></div>
  <div class="v-stat"><strong>1.2k</strong><span>Orders</span></div>
  <div class="v-stat"><strong>4.8</strong><span>Rating</span></div>
  <div class="v-stat"><strong>24h</strong><span>Ships in</span></div>
</div>

<div class="v-tabs">
  <div class="v-tab on">All</div>
  <div class="v-tab">New arrivals</div>
  <div class="v-tab">Best sellers</div>
  <div class="v-tab">⚡ Flash sale</div>
  <div class="v-tab">Categories</div>
  <div class="v-tab">Reviews</div>
  <div class="v-tab">About</div>
</div>

<!-- Vendor's own flash sale -->
<div class="v-flash">
  <div class="v-flash-head">
    <div>
      <div class="v-flash-title">''' + _ico('bolt',14) + ''' Vendor Flash · ''' + _esc(v.store_name_en or 'Uellow') + '''</div>
      <div class="v-flash-sub">Exclusive deals from this store</div>
    </div>
    <div class="v-flash-timer"><span>02</span>:<span>14</span>:<span>37</span></div>
  </div>
  <div class="v-flash-row">''' + flash_cards + '''</div>
</div>

<div class="v-section">
  <h3>New arrivals <span class="see">See all →</span></h3>
  <div class="v-grid">''' + new_cards + '''</div>
</div>

<div class="v-section">
  <h3>Best sellers <span class="see">See all →</span></h3>
  <div class="v-grid">''' + best_cards + '''</div>
</div>
'''
    return body, v.store_name_en or 'Vendor', True


# ─── 6. CART ──────────────────────────────────────────────────────

def render_cart(env):
    body = '''
<style>
  body { background: #F8F4E3; }
  .topbar-cart { padding: 14px 18px; background: #fff; border-bottom: 1px solid #F2EBD3; }
  .topbar-cart h1 { margin: 0; font-size: 18px; font-weight: 800; color: #1a1108; }
  .topbar-cart .meta { font-size: 12px; color: #9c8a5e; margin-top: 2px; }
  .cart-list { padding: 12px 14px 0; }
  .cart-item { display: flex; gap: 12px; background: #fff; border-radius: 14px;
       padding: 12px; margin-bottom: 10px; box-shadow: 0 1px 4px rgba(0,0,0,.04); }
  .cart-item img { width: 84px; height: 84px; border-radius: 10px;
       object-fit: cover; background: #F2EBD3; flex-shrink: 0; }
  .ci-body { flex: 1; min-width: 0; }
  .ci-name { font-size: 13px; line-height: 1.4; color: #1a1108;
       display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
       overflow: hidden; }
  .ci-vendor { font-size: 11px; color: #9c8a5e; margin: 4px 0 8px;
       display: flex; align-items: center; gap: 4px; }
  .ci-row { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
  .ci-price { font-weight: 900; color: #412402; font-size: 15px; }
  .ci-price .was { font-size: 11px; color: #999; text-decoration: line-through;
       font-weight: 500; margin-inline-start: 4px; }
  .ci-qty { display: flex; align-items: center; background: #F2EBD3;
       border-radius: 10px; padding: 4px; gap: 4px; }
  .ci-qty button { width: 28px; height: 28px; border: 0; background: #fff;
       border-radius: 6px; color: #412402; font-weight: 800; font-size: 14px;
       cursor: pointer; }
  .ci-qty span { min-width: 24px; text-align: center; font-weight: 800; color: #1a1108; }
  .ci-actions { display: flex; gap: 14px; margin-top: 8px; font-size: 11px;
       color: #9c8a5e; }
  .ci-actions a { display: inline-flex; align-items: center; gap: 4px;
       cursor: pointer; }
  .ci-actions a.del { color: #FF4D4D; }
  .delivery-bar { background: #FFF5D0; padding: 12px 14px;
       margin: 4px 14px 14px; border-radius: 12px; font-size: 12px; color: #5d4d2e; }
  .delivery-bar .bar { height: 6px; background: #fff; border-radius: 999px; margin-top: 6px; }
  .delivery-bar .bar > div { height: 100%;
       background: linear-gradient(90deg,#FFD340,#F5C320); border-radius: 999px; }
  .coupon-row { padding: 0 14px 14px; display: flex; gap: 8px; }
  .coupon-row input { flex: 1; border-radius: 10px; border: 1px dashed #d6c79a;
       padding: 11px 14px; background: #fff; font-size: 13px; outline: 0; }
  .coupon-row input:focus { border-color: #F5C320; border-style: solid; }
  .coupon-row button { padding: 0 18px; border-radius: 10px; border: 0;
       background: #FFD340; color: #412402; font-weight: 800; cursor: pointer; }
  .applied-coupon { background: #FFF5D0; border: 1px dashed #FFD340;
       padding: 10px 12px; margin: 0 14px 14px; border-radius: 10px;
       display: flex; align-items: center; gap: 8px; font-size: 12px; }
  .applied-coupon .tag { background: #FFD340; color: #412402; padding: 2px 8px;
       border-radius: 4px; font-weight: 800; font-size: 11px; }
  .applied-coupon .rm { margin-inline-start: auto; color: #FF4D4D;
       font-weight: 700; cursor: pointer; }
  .totals { padding: 14px 18px; background: #fff; margin: 8px 0 0; }
  .total-row { display: flex; justify-content: space-between; margin: 7px 0;
       font-size: 13px; color: #5d4d2e; }
  .total-row.discount { color: #10b981; }
  .total-row.grand { font-size: 18px; font-weight: 900; color: #412402;
       border-top: 1px solid #F2EBD3; padding-top: 12px; margin-top: 12px; }
  .save-msg { background: #ECFDF5; border-radius: 8px; padding: 8px 12px;
       color: #047857; font-size: 11.5px; font-weight: 700;
       margin: 12px 0 4px; text-align: center; }
  .checkout-cta { position: fixed; bottom: 78px; left: 0; right: 0;
       padding: 12px 14px; background: #fff; border-top: 1px solid #eee;
       box-shadow: 0 -4px 12px rgba(0,0,0,.04); }
  .checkout-cta button { width: 100%; padding: 15px 20px; background: #412402;
       color: #FFD340; border: 0; border-radius: 14px; font-weight: 900;
       font-size: 15px; cursor: pointer;
       display: flex; justify-content: space-between; align-items: center; }
</style>
<div class="topbar-cart">
  <h1>My Cart</h1>
  <div class="meta">3 items · ready to checkout</div>
</div>
<div class="cart-list">
  <div class="cart-item">
    <img src="https://placehold.co/200/F5C320/412402?text=Watch">
    <div class="ci-body">
      <div class="ci-name">HainoTeko-18 Smart Watch For Female · Black</div>
      <div class="ci-vendor">''' + _ico('user',10) + ''' Uellow Official · Premium</div>
      <div class="ci-row">
        <div class="ci-price">8.500 KD<span class="was">12.000</span></div>
        <div class="ci-qty"><button>−</button><span>1</span><button>+</button></div>
      </div>
      <div class="ci-actions">
        <a>''' + _ico('heart',12) + ''' Save for later</a>
        <a class="del">Remove</a>
      </div>
    </div>
  </div>
  <div class="cart-item">
    <img src="https://placehold.co/200/412402/F5C320?text=Buds">
    <div class="ci-body">
      <div class="ci-name">Anker Soundcore C40i Earbuds — Dark Gray</div>
      <div class="ci-vendor">''' + _ico('user',10) + ''' Anker Authorized</div>
      <div class="ci-row">
        <div class="ci-price">14.900 KD</div>
        <div class="ci-qty"><button>−</button><span>2</span><button>+</button></div>
      </div>
      <div class="ci-actions">
        <a>''' + _ico('heart',12) + ''' Save for later</a>
        <a class="del">Remove</a>
      </div>
    </div>
  </div>
</div>
<div class="delivery-bar">
  Add <b>KD 6.6</b> more for <b>FREE delivery</b>
  <div class="bar"><div style="width:67%"></div></div>
</div>
<div class="applied-coupon">
  <span class="tag">SAVE15</span>
  <span>You saved 1.500 KD on this order</span>
  <span class="rm">✕</span>
</div>
<div class="coupon-row">
  <input placeholder="Got another promo code?">
  <button>Apply</button>
</div>
<div class="totals">
  <div class="total-row"><span>Subtotal (3 items)</span><span>38.300 KD</span></div>
  <div class="total-row"><span>Delivery</span><span style="color:#10b981;font-weight:700">FREE</span></div>
  <div class="total-row discount"><span>SAVE15 coupon</span><span>− 1.500 KD</span></div>
  <div class="total-row discount"><span>Loyalty (-150 pts)</span><span>− 0.500 KD</span></div>
  <div class="total-row grand"><span>Total</span><span>36.300 KD</span></div>
  <div class="save-msg">🎉 You saved <b>2.000 KD</b> on this order!</div>
</div>
<div style="height:100px"></div>
<div class="checkout-cta">
  <button><span>Checkout · 36.300 KD</span><span>→</span></button>
</div>
'''
    return body, 'My Cart', True


# ─── 7. CHECKOUT ──────────────────────────────────────────────────

def render_checkout(env):
    body = '''
<style>
  body { background: #F8F4E3; }
  .topbar-co { padding: 14px 18px; background: #fff; }
  .topbar-co h1 { margin: 0; font-size: 18px; font-weight: 800; color: #1a1108; }
  .steps { display: flex; gap: 4px; margin-top: 12px; padding-bottom: 4px; }
  .step { flex: 1; height: 4px; background: #F2EBD3; border-radius: 999px; }
  .step.on { background: #F5C320; }
  .step.done { background: #10b981; }
  .checkout-section { background: #fff; margin: 0 0 8px; padding: 16px 18px; }
  .checkout-section h3 { font-size: 13px; font-weight: 800; color: #412402;
       margin: 0 0 12px; text-transform: uppercase; letter-spacing: .5px;
       display: flex; align-items: center; gap: 6px; }
  .checkout-section h3 .num { background: #FFD340; color: #412402; width: 22px;
       height: 22px; display: inline-grid; place-items: center; border-radius: 50%;
       font-size: 12px; font-weight: 900; }
  .addr-card { display: flex; gap: 10px; padding: 14px; border: 2px solid #F5C320;
       border-radius: 12px; background: #FFFCEF; align-items: flex-start; }
  .addr-card .icon { color: #C99000; padding-top: 2px; }
  .addr-card .name { font-weight: 800; font-size: 13px; }
  .addr-card .body { font-size: 12px; color: #5d4d2e; line-height: 1.5; margin-top: 4px; }
  .addr-card .change { margin-inline-start: auto; color: #5d4d2e; font-size: 11px;
       font-weight: 700; }
  .ship-opt { display: flex; align-items: center; gap: 12px; padding: 12px;
       border-radius: 12px; border: 1px solid #eee; margin-bottom: 8px; cursor: pointer; }
  .ship-opt.on { border: 2px solid #F5C320; background: #FFFCEF; padding: 11px; }
  .ship-opt .ico-box { width: 36px; height: 36px; background: #F2EBD3;
       color: #9c8a5e; border-radius: 10px; display: grid; place-items: center; flex-shrink: 0; }
  .ship-opt.on .ico-box { background: #FFD340; color: #412402; }
  .ship-opt .body { flex: 1; min-width: 0; }
  .ship-opt .ttl { font-weight: 700; font-size: 13px; color: #1a1108; }
  .ship-opt .meta { font-size: 11px; color: #9c8a5e; margin-top: 2px; }
  .ship-opt .pri { font-weight: 800; color: #412402; font-size: 14px; flex-shrink: 0; }
  .ship-opt .pri.free { color: #10b981; }
  .ship-opt .radio { width: 20px; height: 20px; border: 2px solid #e5d8b2;
       border-radius: 50%; flex-shrink: 0; }
  .ship-opt.on .radio { border-color: #F5C320;
       background: radial-gradient(circle, #F5C320 40%, transparent 50%); }
  .pay-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
  .pay-opt { border: 1px solid #eee; padding: 14px 10px; border-radius: 12px;
       text-align: center; font-size: 12px; font-weight: 700; color: #5d4d2e;
       cursor: pointer; }
  .pay-opt.on { border: 2px solid #F5C320; background: #FFFCEF; padding: 13px 9px; color: #412402; }
  .pay-opt .ico-line { color: #9c8a5e; margin-bottom: 6px; display: flex; justify-content: center; }
  .pay-opt.on .ico-line { color: #412402; }
  .order-summary { font-size: 13px; }
  .order-summary .row { display: flex; justify-content: space-between; margin: 7px 0;
       color: #5d4d2e; }
  .order-summary .row.discount { color: #10b981; }
  .order-summary .row.total { font-weight: 900; font-size: 18px; color: #412402;
       border-top: 1px solid #F2EBD3; padding-top: 10px; margin-top: 10px; }
  .delivery-note { background: #FFF5D0; padding: 12px; border-radius: 10px;
       font-size: 12px; color: #5d4d2e; margin-top: 8px; line-height: 1.5;
       display: flex; gap: 8px; align-items: center; }
  .place-order { position: fixed; bottom: 78px; left: 0; right: 0;
       padding: 12px 16px; background: #fff; border-top: 1px solid #eee; }
  .place-order button { width: 100%; padding: 16px; background: #412402;
       color: #FFD340; border: 0; border-radius: 14px;
       font-weight: 900; font-size: 15px; cursor: pointer; }
  .secure-row { text-align: center; font-size: 11px; color: #9c8a5e;
       margin-top: 8px; display: flex; align-items: center; justify-content: center; gap: 4px; }
</style>
<div class="topbar-co">
  <h1>← Checkout</h1>
  <div class="steps"><div class="step done"></div><div class="step on"></div><div class="step"></div></div>
</div>

<div class="checkout-section">
  <h3><span class="num">1</span>Delivery address</h3>
  <div class="addr-card">
    <span class="icon">''' + _ico('pin',20) + '''</span>
    <div>
      <div class="name">Ali Mohammed</div>
      <div class="body">Block 5, Street 12, House 47<br>Hawalli, Kuwait · +965 9999 0000</div>
    </div>
    <span class="change">Change ›</span>
  </div>
</div>

<div class="checkout-section">
  <h3><span class="num">2</span>Shipping method</h3>
  <div class="ship-opt on">
    <div class="radio"></div>
    <div class="ico-box">''' + _ico('bolt',18) + '''</div>
    <div class="body">
      <div class="ttl">Same-day delivery</div>
      <div class="meta">Order before 2 PM · Arrives today</div>
    </div>
    <div class="pri">2.000 KD</div>
  </div>
  <div class="ship-opt">
    <div class="radio"></div>
    <div class="ico-box">''' + _ico('truck',18) + '''</div>
    <div class="body">
      <div class="ttl">Standard delivery</div>
      <div class="meta">1-3 business days</div>
    </div>
    <div class="pri free">Free</div>
  </div>
  <div class="ship-opt">
    <div class="radio"></div>
    <div class="ico-box">''' + _ico('home',18) + '''</div>
    <div class="body">
      <div class="ttl">Pickup from store</div>
      <div class="meta">Uellow Salmiya branch · Ready in 2h</div>
    </div>
    <div class="pri free">Free</div>
  </div>
</div>

<div class="checkout-section">
  <h3><span class="num">3</span>Payment method</h3>
  <div class="pay-grid">
    <div class="pay-opt on"><div class="ico-line">''' + _ico('wallet',20) + '''</div>Credit / Debit card</div>
    <div class="pay-opt"><div class="ico-line">''' + _ico('shield',20) + '''</div>KNET</div>
    <div class="pay-opt"><div class="ico-line">''' + _ico('user',20) + '''</div>Apple Pay</div>
    <div class="pay-opt"><div class="ico-line">''' + _ico('box',20) + '''</div>Cash on delivery</div>
  </div>
</div>

<div class="checkout-section">
  <h3>Order summary</h3>
  <div class="order-summary">
    <div class="row"><span>3 items</span><span>38.300 KD</span></div>
    <div class="row"><span>Delivery (Same-day)</span><span>2.000 KD</span></div>
    <div class="row discount"><span>SAVE15 coupon</span><span>− 1.500 KD</span></div>
    <div class="row discount"><span>Loyalty (-150 pts)</span><span>− 0.500 KD</span></div>
    <div class="row total"><span>You pay</span><span>38.300 KD</span></div>
  </div>
  <div class="delivery-note">
    ''' + _ico('chat',14) + ''' <b>Delivery instructions</b> — Leave at door · Call when arrived
  </div>
</div>

<div style="height:120px"></div>
<div class="place-order">
  <button>Place order · 38.300 KD</button>
  <div class="secure-row">''' + _ico('shield',12) + ''' Secure checkout · Your data is encrypted</div>
</div>
'''
    return body, 'Checkout', False


# ─── 8. ACCOUNT — order grid + monochrome + social + wishlist sections ─

def render_account(env):
    # Status counts (demo data — real impl reads sale.order)
    order_states = [
        ('pending',   'Pending',   'box',   2),
        ('paid',      'Paid',      'check', 1),
        ('packing',   'Packing',   'gift',  1),
        ('shipping',  'Shipping',  'truck', 3),
        ('delivered', 'Delivered', 'home', 14),
        ('returns',   'Returns',   'return',0),
    ]
    order_tiles_html = ''
    for key, label, ico, count in order_states:
        badge = f'<span class="ot-badge">{count}</span>' if count else ''
        active_cls = 'has-items' if count else ''
        order_tiles_html += f'''
        <a class="order-tile {active_cls}">
          <div class="ot-ico-wrap">{_ico(ico, 22)}{badge}</div>
          <div class="ot-lbl">{label}</div>
        </a>'''

    body = '''
<style>
  body { background: #F8F4E3; }
  .account-head { padding: 22px 20px 16px; background: #fff; }
  .acc-row { display: flex; gap: 14px; align-items: center; }
  .acc-avatar { width: 64px; height: 64px; border-radius: 18px;
       background: linear-gradient(135deg,#FFE066,#F5C320); display: grid;
       place-items: center; font-size: 26px; font-weight: 900; color: #412402; }
  .acc-info { flex: 1; min-width: 0; }
  .acc-name { font-size: 18px; font-weight: 800; color: #1a1108; }
  .acc-email { font-size: 12px; color: #9c8a5e; margin-top: 2px; }
  .acc-edit { background: #F2EBD3; color: #412402; padding: 8px 12px;
       border-radius: 10px; border: 0; font-weight: 700; font-size: 12px;
       cursor: pointer; display: inline-flex; align-items: center; gap: 4px; }

  /* Banners */
  .banner-row { display: flex; gap: 10px; padding: 12px 14px;
       overflow-x: auto; scrollbar-width: none; }
  .banner-row::-webkit-scrollbar { display: none; }
  .banner { flex: 0 0 78%; min-height: 140px; border-radius: 18px; padding: 16px;
       color: #412402; position: relative; overflow: hidden;
       display: flex; flex-direction: column; }
  .banner.loyalty { background: linear-gradient(135deg,#FFD340,#F5A800); }
  .banner.wallet { background: linear-gradient(135deg,#412402,#1F1100); color: #FFD340; }
  .banner h3 { margin: 0; font-size: 12px; font-weight: 700; opacity: .8;
       letter-spacing: .5px; text-transform: uppercase; }
  .banner .num { font-size: 30px; font-weight: 900; margin: 6px 0 2px; line-height: 1; }
  .banner .sub { font-size: 11px; opacity: .75; margin-bottom: 8px; }
  .banner .tier { background: #412402; color: #FFD340; font-size: 10px;
       font-weight: 800; padding: 3px 9px; border-radius: 999px;
       display: inline-block; align-self: flex-start; }
  .banner.wallet .tier { background: #FFD340; color: #412402; }
  .banner .progress { height: 6px; background: rgba(0,0,0,.15); border-radius: 999px;
       margin-top: 12px; overflow: hidden; }
  .banner .progress > div { height: 100%; background: #412402; border-radius: 999px; }
  .banner.wallet .progress > div { background: #FFD340; }
  .banner .progress-text { font-size: 10px; opacity: .8; margin-top: 4px; }
  .banner .cta { position: absolute; right: 16px; bottom: 16px; background: #412402;
       color: #FFD340; padding: 7px 12px; border-radius: 10px; font-weight: 700;
       font-size: 11px; border: 0; }
  .banner.wallet .cta { background: #FFD340; color: #412402; }

  /* Section card */
  .sec-card { background: #fff; margin: 8px 14px; border-radius: 16px;
       padding: 14px 14px 16px; box-shadow: 0 1px 3px rgba(0,0,0,.04); }
  .sec-head { display: flex; align-items: center; justify-content: space-between;
       margin-bottom: 12px; }
  .sec-head h3 { font-size: 14px; font-weight: 800; color: #412402; margin: 0; }
  .sec-head .see { font-size: 11px; color: #5d4d2e; font-weight: 700;
       text-decoration: none; cursor: pointer;
       display: inline-flex; align-items: center; gap: 2px; }

  /* Orders grid */
  .orders-grid { display: grid; grid-template-columns: repeat(6, 1fr); gap: 6px; }
  .order-tile { display: flex; flex-direction: column; align-items: center;
       gap: 4px; padding: 6px 2px; text-decoration: none;
       color: #9c8a5e; cursor: pointer; }
  .order-tile.has-items { color: #412402; }
  .order-tile .ot-ico-wrap { position: relative; width: 40px; height: 40px;
       background: #F2EBD3; border-radius: 12px; display: grid; place-items: center; }
  .order-tile.has-items .ot-ico-wrap { background: #FFF5D0; color: #C99000; }
  .order-tile .ot-badge { position: absolute; top: -4px; right: -4px;
       background: #FF4D4D; color: #fff; font-size: 9px; font-weight: 800;
       padding: 2px 5px; border-radius: 8px; min-width: 16px; text-align: center; }
  .order-tile .ot-lbl { font-size: 10px; font-weight: 700; text-align: center; }

  /* Action tiles row */
  .action-tiles { display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 6px; }
  .action-tile { display: flex; flex-direction: column; align-items: center;
       gap: 4px; padding: 8px 2px; cursor: pointer; color: #5d4d2e; }
  .action-tile .at-ico { width: 36px; height: 36px; background: #F2EBD3;
       color: #9c8a5e; border-radius: 12px; display: grid; place-items: center; position: relative; }
  .action-tile:hover .at-ico { background: #FFD340; color: #412402; }
  .action-tile .at-lbl { font-size: 11px; font-weight: 700; }
  .action-tile .at-bcount { position: absolute; top: -4px; right: -4px;
       background: #FF4D4D; color: #fff; font-size: 9px; font-weight: 800;
       padding: 1px 5px; border-radius: 6px; }

  /* Recent order card */
  .order-card { background: #fff; margin: 0 14px 14px; border-radius: 14px;
       padding: 14px; display: flex; gap: 12px; align-items: center;
       border-left: 4px solid #F5C320; box-shadow: 0 1px 4px rgba(0,0,0,.04); }
  .order-card .ico { color: #C99000; }
  .order-card .body { flex: 1; min-width: 0; }
  .order-card .name { font-weight: 800; font-size: 13px; color: #1a1108; }
  .order-card .meta { font-size: 11px; color: #9c8a5e; margin-top: 2px; }
  .order-card .track { background: #412402; color: #FFD340; padding: 8px 14px;
       border-radius: 10px; font-size: 11px; font-weight: 800; border: 0; flex-shrink: 0; cursor: pointer; }

  /* Wishlist + viewed row */
  .ww-row { display: flex; gap: 8px; overflow-x: auto; scrollbar-width: none; }
  .ww-row::-webkit-scrollbar { display: none; }
  .ww-item { flex: 0 0 80px; }
  .ww-item img { width: 80px; height: 80px; border-radius: 10px; object-fit: cover;
       background: #F2EBD3; }
  .ww-item .ww-price { font-size: 11px; color: #412402; font-weight: 800;
       margin-top: 4px; }

  /* Social */
  .social-row { display: flex; gap: 8px; justify-content: space-around; }
  .social-tile { width: 48px; height: 48px; background: #F2EBD3; color: #9c8a5e;
       border-radius: 14px; display: grid; place-items: center; cursor: pointer;
       transition: all .15s; }
  .social-tile:hover { background: #FFD340; color: #412402; transform: translateY(-2px); }
  .social-tile svg { width: 22px; height: 22px; }

  /* Menu list */
  .menu-list { background: #fff; margin: 8px 14px; border-radius: 14px;
       padding: 4px 0; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,.04); }
  .menu-list a { display: flex; gap: 12px; padding: 12px 16px; align-items: center;
       text-decoration: none; color: #1a1108; font-size: 13px; cursor: pointer; }
  .menu-list a + a { border-top: 1px solid #F8F4E3; }
  .menu-list a .ico-box { width: 32px; height: 32px; background: #F2EBD3;
       color: #9c8a5e; border-radius: 8px; display: grid; place-items: center;
       flex-shrink: 0; }
  .menu-list a:hover .ico-box { background: #FFD340; color: #412402; }
  .menu-list a .chev { margin-inline-start: auto; color: #cbb78a; }
  .menu-list .signout .ico-box { background: #FFE3E3; color: #FF4D4D; }
  .menu-list .signout > div:first-child { color: #FF4D4D; font-weight: 700; }
  .version { text-align: center; font-size: 11px; color: #9c8a5e;
       padding: 18px 14px 24px; }
</style>
<div class="account-head">
  <div class="acc-row">
    <div class="acc-avatar">A</div>
    <div class="acc-info">
      <div class="acc-name">Ali Mohammed</div>
      <div class="acc-email">ali@uellow.com · +965 9999 0000</div>
    </div>
    <button class="acc-edit">''' + _ico('pen',12) + ''' Edit</button>
  </div>
</div>

<div class="banner-row">
  <div class="banner loyalty">
    <h3>LOYALTY POINTS</h3>
    <div class="num">2,450</div>
    <div class="sub">= 24.500 KD redeem value</div>
    <div class="tier">⭐ SILVER TIER</div>
    <div class="progress"><div style="width:48%"></div></div>
    <div class="progress-text">2,550 pts to reach <b>GOLD</b></div>
    <button class="cta">Use →</button>
  </div>
  <div class="banner wallet">
    <h3>UELLOW WALLET</h3>
    <div class="num">12.750 <span style="font-size:16px">KD</span></div>
    <div class="sub">Last top-up: 3 days ago · KNET</div>
    <div class="tier">SECURE</div>
    <div class="progress"><div style="width:32%"></div></div>
    <div class="progress-text">3 transactions this month</div>
    <button class="cta">Top up →</button>
  </div>
</div>

<!-- My Orders grid -->
<div class="sec-card">
  <div class="sec-head">
    <h3>My Orders</h3>
    <a class="see">See all ›</a>
  </div>
  <div class="orders-grid">''' + order_tiles_html + '''</div>
</div>

<!-- Recent order tracker -->
<div class="order-card">
  <div class="ico">''' + _ico('truck',22) + '''</div>
  <div class="body">
    <div class="name">#S00532 · Out for delivery</div>
    <div class="meta">3 items · Arrives in 2 hours</div>
  </div>
  <button class="track">Track</button>
</div>

<!-- Wishlist -->
<div class="sec-card">
  <div class="sec-head">
    <h3>''' + _ico('heart',14) + ''' My Wishlist (12)</h3>
    <a class="see">See all ›</a>
  </div>
  <div class="ww-row">
    <div class="ww-item"><img src="https://placehold.co/200/F5C320/412402?text=W1"><div class="ww-price">14.9 KD</div></div>
    <div class="ww-item"><img src="https://placehold.co/200/412402/F5C320?text=W2"><div class="ww-price">59.5 KD</div></div>
    <div class="ww-item"><img src="https://placehold.co/200/FFE066/412402?text=W3"><div class="ww-price">9.9 KD</div></div>
    <div class="ww-item"><img src="https://placehold.co/200/c4a460/fff?text=W4"><div class="ww-price">45.0 KD</div></div>
    <div class="ww-item"><img src="https://placehold.co/200/8B7355/fff?text=W5"><div class="ww-price">29.0 KD</div></div>
  </div>
</div>

<!-- Recently viewed -->
<div class="sec-card">
  <div class="sec-head">
    <h3>''' + _ico('clock',14) + ''' Recently viewed</h3>
    <a class="see">Clear all</a>
  </div>
  <div class="ww-row">
    <div class="ww-item"><img src="https://placehold.co/200/412402/FFE066?text=V1"><div class="ww-price">29.0 KD</div></div>
    <div class="ww-item"><img src="https://placehold.co/200/FFE066/412402?text=V2"><div class="ww-price">12.5 KD</div></div>
    <div class="ww-item"><img src="https://placehold.co/200/FF4D4D/fff?text=V3"><div class="ww-price">9.0 KD</div></div>
    <div class="ww-item"><img src="https://placehold.co/200/3b82f6/fff?text=V4"><div class="ww-price">99.9 KD</div></div>
  </div>
</div>

<!-- Quick actions -->
<div class="sec-card">
  <div class="action-tiles">
    <a class="action-tile"><div class="at-ico">''' + _ico('pin',18) + '''</div><div class="at-lbl">Addresses</div></a>
    <a class="action-tile"><div class="at-ico">''' + _ico('truck',18) + '''</div><div class="at-lbl">Shipping</div></a>
    <a class="action-tile"><div class="at-ico">''' + _ico('star',18) + '''</div><div class="at-lbl">Reviews</div></a>
    <a class="action-tile"><div class="at-ico">''' + _ico('bell',18) + '''<span class="at-bcount">5</span></div><div class="at-lbl">Alerts</div></a>
    <a class="action-tile"><div class="at-ico">''' + _ico('gift',18) + '''</div><div class="at-lbl">Coupons</div></a>
    <a class="action-tile"><div class="at-ico">''' + _ico('user',18) + '''</div><div class="at-lbl">Followed</div></a>
    <a class="action-tile"><div class="at-ico">''' + _ico('globe',18) + '''</div><div class="at-lbl">Country</div></a>
    <a class="action-tile"><div class="at-ico">''' + _ico('cog',18) + '''</div><div class="at-lbl">Settings</div></a>
  </div>
</div>

<!-- Social -->
<div class="sec-card">
  <div class="sec-head"><h3>Follow Uellow</h3></div>
  <div class="social-row">
    <a class="social-tile" title="Facebook"><svg viewBox="0 0 24 24" fill="currentColor"><path d="M22 12a10 10 0 1 0-11.6 9.9V15h-2.5v-3h2.5V9.8c0-2.5 1.5-3.9 3.7-3.9 1.1 0 2.2.2 2.2.2v2.4h-1.2c-1.2 0-1.6.8-1.6 1.5V12h2.7l-.4 3h-2.3v6.9A10 10 0 0 0 22 12z"/></svg></a>
    <a class="social-tile" title="Instagram"><svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2.2a52 52 0 0 1 4.8.1c1.2.1 1.9.3 2.4.5l1.5 1 1 1.5c.2.5.4 1.2.5 2.4a52 52 0 0 1 .1 4.8 52 52 0 0 1-.1 4.8c-.1 1.2-.3 1.9-.5 2.4l-1 1.5-1.5 1c-.5.2-1.2.4-2.4.5a52 52 0 0 1-4.8.1 52 52 0 0 1-4.8-.1c-1.2-.1-1.9-.3-2.4-.5l-1.5-1-1-1.5c-.2-.5-.4-1.2-.5-2.4a52 52 0 0 1-.1-4.8 52 52 0 0 1 .1-4.8c.1-1.2.3-1.9.5-2.4l1-1.5 1.5-1c.5-.2 1.2-.4 2.4-.5a52 52 0 0 1 4.8-.1zm0 1.8a52 52 0 0 0-4.7.1c-1.1.1-1.7.3-2 .4l-1 .7-.7 1c-.1.3-.3.9-.4 2A52 52 0 0 0 4 12c0 2.7 0 4.2.2 4.7.1 1.1.3 1.7.4 2l.7 1 1 .7c.3.1.9.3 2 .4 1.4.1 1.9.1 4.7.1s4.2 0 4.7-.1c1.1-.1 1.7-.3 2-.4l1-.7.7-1c.1-.3.3-.9.4-2 .1-1.4.1-1.9.1-4.7s0-4.2-.1-4.7c-.1-1.1-.3-1.7-.4-2l-.7-1-1-.7c-.3-.1-.9-.3-2-.4-1.4-.1-1.9-.1-4.7-.1zm0 3a5 5 0 1 1 0 10 5 5 0 0 1 0-10zm0 1.8a3.2 3.2 0 1 0 0 6.4 3.2 3.2 0 0 0 0-6.4zm5.2-3a1.2 1.2 0 1 1 0 2.4 1.2 1.2 0 0 1 0-2.4z"/></svg></a>
    <a class="social-tile" title="TikTok"><svg viewBox="0 0 24 24" fill="currentColor"><path d="M19.6 6.7a4.8 4.8 0 0 1-2.9-1c-.4-.3-.7-.7-1-1.1-.4-.6-.5-1.3-.5-2h-3.4v13.6c0 .9-.4 1.6-1.1 2.1a2.5 2.5 0 0 1-3-.5 2.5 2.5 0 0 1 2-4.2c.3 0 .5 0 .8.1V10.4a6 6 0 0 0-3.5.9 6 6 0 0 0-2.5 5.4 6 6 0 0 0 5.7 5.6c1.6 0 3.1-.6 4.3-1.7a6 6 0 0 0 1.7-4.3V9.6c1.4.9 3 1.4 4.6 1.4v-3c-.5 0-.8 0-1.2-.1z"/></svg></a>
    <a class="social-tile" title="YouTube"><svg viewBox="0 0 24 24" fill="currentColor"><path d="M21.6 7.2a2.5 2.5 0 0 0-1.8-1.8C18.2 5 12 5 12 5s-6.2 0-7.8.4A2.5 2.5 0 0 0 2.4 7.2 26 26 0 0 0 2 12c0 1.6.1 3.2.4 4.8a2.5 2.5 0 0 0 1.8 1.8c1.6.4 7.8.4 7.8.4s6.2 0 7.8-.4a2.5 2.5 0 0 0 1.8-1.8c.3-1.6.4-3.2.4-4.8 0-1.6-.1-3.2-.4-4.8zM10 15.1V8.9l5.4 3.1z"/></svg></a>
    <a class="social-tile" title="X"><svg viewBox="0 0 24 24" fill="currentColor"><path d="M18.5 3h3l-7.5 8.6L23 21h-7l-5.4-7-6.2 7h-3L9.5 12 1 3h7l4.9 6.4z"/></svg></a>
    <a class="social-tile" title="WhatsApp"><svg viewBox="0 0 24 24" fill="currentColor"><path d="M20.5 3.5A10 10 0 0 0 3.5 17l-1.5 5 5-1.5a10 10 0 0 0 13.5-17zM12 20.4a8.4 8.4 0 0 1-4.3-1.2l-.3-.2-3.2 1 1-3.1-.2-.4a8.4 8.4 0 1 1 7 4zm4.6-6.3c-.3-.1-1.5-.7-1.7-.8-.2-.1-.4-.1-.6.1-.2.2-.6.8-.8 1l-.5.1c-.3-.1-1.2-.4-2.3-1.4a8 8 0 0 1-1.6-2c-.2-.3 0-.5 0-.6l.4-.4.2-.3v-.4l-.7-1.7c-.2-.4-.4-.4-.5-.4h-.5c-.2 0-.4 0-.7.3-.2.3-.9.9-.9 2.1 0 1.3.9 2.5 1 2.6.1.2 1.8 2.7 4.3 3.7l1.5.6c.6.2 1.2.2 1.6.1.5-.1 1.5-.6 1.7-1.2.2-.6.2-1.1.1-1.2-.1-.1-.2-.1-.5-.3z"/></svg></a>
  </div>
</div>

<!-- Menu -->
<div class="menu-list">
  <a><div class="ico-box">''' + _ico('chat',16) + '''</div><div>Customer support</div><div class="chev">›</div></a>
  <a><div class="ico-box">''' + _ico('shield',16) + '''</div><div>Privacy &amp; security</div><div class="chev">›</div></a>
  <a><div class="ico-box">''' + _ico('return',16) + '''</div><div>Returns &amp; refunds</div><div class="chev">›</div></a>
  <a><div class="ico-box">''' + _ico('star',16) + '''</div><div>Rate the app</div><div class="chev">›</div></a>
  <a><div class="ico-box">''' + _ico('globe',16) + '''</div><div>Country: Kuwait · العربية</div><div class="chev">›</div></a>
</div>
<div class="menu-list">
  <a class="signout"><div class="ico-box">''' + _ico('logout',16) + '''</div><div>Sign out</div></a>
</div>
<div class="version">Uellow v4.2.0 · build 87 · made with ❤ in Kuwait</div>
'''
    return body, 'Account', True


# ─── 9. BEENA AI ───────────────────────────────────────────────────

def render_beena(env):
    body = '''
<style>
  body { background: #FAFAFA; }
  .beena-head { padding: 18px; background: linear-gradient(135deg,#412402,#1F1100);
       color: #FFD340; }
  .beena-row { display: flex; gap: 12px; align-items: center; }
  .beena-orb-big { width: 48px; height: 48px; border-radius: 50%;
       background: radial-gradient(circle at 30% 25%, #FFE45E, #F5C320 60%, #C99000);
       box-shadow: 0 4px 12px -2px rgba(245,195,32,.5); display: grid;
       place-items: center; font-size: 22px; }
  .beena-head h2 { margin: 0; font-size: 17px; font-weight: 800; }
  .beena-head p { margin: 2px 0 0; font-size: 12px; opacity: .6; }
  .beena-chips { display: flex; gap: 6px; padding: 12px 14px;
       overflow-x: auto; scrollbar-width: none; background: #fff;
       border-bottom: 1px solid #F2EBD3; }
  .beena-chips::-webkit-scrollbar { display: none; }
  .beena-chip { flex: 0 0 auto; padding: 8px 12px; background: #FFF5D0;
       border-radius: 999px; color: #412402; font-size: 12px; font-weight: 600;
       border: 1px solid #FFE8A0; cursor: pointer; }
  .msg-list { padding: 16px 14px 0; }
  .msg { display: flex; gap: 10px; margin-bottom: 12px; align-items: flex-end; }
  .msg.user { flex-direction: row-reverse; }
  .msg .bubble { max-width: 80%; padding: 10px 14px; border-radius: 16px;
       font-size: 13.5px; line-height: 1.5; }
  .msg.bot .bubble { background: #fff; color: #1a1108;
       box-shadow: 0 1px 3px rgba(0,0,0,.05); border-bottom-left-radius: 6px; }
  .msg.user .bubble { background: #412402; color: #FFD340; border-bottom-right-radius: 6px; }
  .msg .avatar { width: 28px; height: 28px; border-radius: 50%;
       display: grid; place-items: center; font-weight: 800; font-size: 12px; flex-shrink: 0; }
  .msg.bot .avatar { background: #FFD340; color: #412402; }
  .msg.user .avatar { background: #412402; color: #FFD340; }
  .product-suggest { display: flex; gap: 8px; margin: 6px 0 0;
       overflow-x: auto; scrollbar-width: none; padding-bottom: 4px; max-width: 80%; }
  .product-suggest::-webkit-scrollbar { display: none; }
  .ps-card { flex: 0 0 130px; background: #fff; padding: 8px; border-radius: 10px;
       border: 1px solid #F2EBD3; }
  .ps-card img { width: 100%; height: 80px; object-fit: cover; border-radius: 6px; }
  .ps-card .name { font-size: 11px; line-height: 1.3; margin-top: 4px;
       height: 28px; overflow: hidden; }
  .ps-card .pr { font-weight: 800; font-size: 12px; color: #412402; margin-top: 2px; }
  .ps-card .pr-cta { background: #FFD340; color: #412402; padding: 4px;
       border-radius: 6px; text-align: center; font-size: 10px; font-weight: 800;
       margin-top: 4px; cursor: pointer; }
  .typing { display: inline-flex; gap: 3px; padding: 12px 14px;
       background: #fff; border-radius: 16px; border-bottom-left-radius: 6px;
       box-shadow: 0 1px 3px rgba(0,0,0,.05); }
  .typing span { width: 6px; height: 6px; border-radius: 50%; background: #ccc; }
  .input-bar { position: fixed; bottom: 78px; left: 0; right: 0;
       background: #fff; border-top: 1px solid #eee; padding: 10px 12px;
       display: flex; gap: 6px; align-items: center; }
  .input-bar input { flex: 1; height: 42px; border: 0; background: #F2EBD3;
       border-radius: 18px; padding: 0 14px; font-size: 13.5px; outline: 0; }
  .input-bar .icon-btn { width: 42px; height: 42px; border-radius: 12px;
       background: #F2EBD3; color: #5d4d2e; border: 0;
       display: grid; place-items: center; cursor: pointer; }
  .input-bar .send { background: #FFD340; color: #412402; font-size: 18px; }
</style>
<div class="beena-head">
  <div class="beena-row">
    <div class="beena-orb-big">✨</div>
    <div>
      <h2>Beena AI</h2>
      <p>🟢 online · powered by Uellow</p>
    </div>
  </div>
</div>
<div class="beena-chips">
  <span class="beena-chip">📸 Visual search</span>
  <span class="beena-chip">📦 Track my order</span>
  <span class="beena-chip">🎁 Use my points</span>
  <span class="beena-chip">💬 Ask a question</span>
  <span class="beena-chip">🎂 Gift ideas</span>
</div>
<div class="msg-list">
  <div class="msg bot">
    <div class="avatar">B</div>
    <div class="bubble">Hi Ali! 👋 I'm Beena. I can find products, track orders, redeem points, or just chat. What's up?</div>
  </div>
  <div class="msg user">
    <div class="avatar">A</div>
    <div class="bubble">عندي مناسبة عيد ميلاد، اقترح علي ساعة ذكية مناسبة كهدية لشاب</div>
  </div>
  <div class="msg bot">
    <div class="avatar">B</div>
    <div style="max-width:80%">
      <div class="bubble">اختيار رائع 🎂 إليك أفضل ٣ ساعات ذكية:</div>
      <div class="product-suggest">
        <div class="ps-card"><img src="https://placehold.co/200/F5C320/412402?text=W1"><div class="name">HainoTeko Pro Watch</div><div class="pr">14.900 KD</div><div class="pr-cta">View</div></div>
        <div class="ps-card"><img src="https://placehold.co/200/412402/F5C320?text=W2"><div class="name">Huawei GT4 Pro</div><div class="pr">65.000 KD</div><div class="pr-cta">View</div></div>
        <div class="ps-card"><img src="https://placehold.co/200/FFE066/412402?text=W3"><div class="name">Apple Watch SE</div><div class="pr">95.500 KD</div><div class="pr-cta">View</div></div>
      </div>
    </div>
  </div>
  <div class="msg bot">
    <div class="avatar">B</div>
    <div class="typing"><span></span><span></span><span></span></div>
  </div>
</div>
<div style="height:120px"></div>
<div class="input-bar">
  <button class="icon-btn">''' + _ico('camera',18) + '''</button>
  <button class="icon-btn">''' + _ico('chat',18) + '''</button>
  <input placeholder="اكتب رسالتك…">
  <button class="icon-btn send">➤</button>
</div>
'''
    return body, 'Beena AI', True


# ─── 10. CATEGORY — sidebar + sub-cats chips inside ─────────────

def render_category(env):
    roots = env['product.public.category'].sudo().search(
        [('parent_id','=',False)], order='sequence, name', limit=20)
    if not roots:
        return '<div style="padding:40px;text-align:center">No categories yet.</div>', 'Categories', True

    # Sidebar — all root categories
    sidebar = ''
    for i, c in enumerate(roots):
        cls = 'on' if i == 0 else ''
        if c.image_512:
            ico_html = f'<div class="cat-ico" style="background-image:url({_img("product.public.category", c.id, "image_128", c.write_date)})"></div>'
        else:
            ico_html = f'<div class="cat-ico emoji">{_emoji_for(c.name)}</div>'
        sidebar += f'<a class="cat-side-item {cls}">{ico_html}<span>{_esc(c.name)}</span></a>'

    # Right content for the currently-selected main category
    first = roots[0]
    subs = env['product.public.category'].sudo().search(
        [('parent_id','=',first.id)], order='sequence, name', limit=12)

    # ── Sub-categories block (visual grid, only if any exist) ────────
    subcats_html = ''
    if subs:
        sc_cards = ''
        for s in subs:
            if s.image_512:
                bg = f'background-image:url({_img("product.public.category", s.id, "image_256", s.write_date)})'
                ico_text = ''
            else:
                bg = 'background:#FFE066'
                ico_text = _emoji_for(s.name)
            # count products in this sub
            try:
                sc_count = env['product.template'].sudo().search_count([
                    ('public_categ_ids', 'child_of', s.id),
                    ('is_published', '=', True),
                ])
            except Exception:
                sc_count = 0
            sc_cards += f'''
            <a class="sc-card">
              <div class="sc-img" style="{bg}">{ico_text}</div>
              <div class="sc-name">{_esc(s.name)}</div>
              <div class="sc-count">{sc_count} items</div>
            </a>'''
        subcats_html = f'''
        <section class="sec-block">
          <div class="sec-head">
            <h3>Sub-categories</h3>
            <span class="sec-meta">{len(subs)} in {_esc(first.name)}</span>
          </div>
          <div class="sc-grid">{sc_cards}</div>
        </section>'''

    # ── Latest products in this category (horizontal slider) ─────────
    latest = env['product.template'].sudo().search([
        ('public_categ_ids', 'child_of', first.id),
        ('is_published', '=', True),
    ], limit=10, order='create_date desc')
    if not latest:
        latest = env['product.template'].sudo().search(
            [('is_published','=',True)], limit=10, order='create_date desc')
    latest_cards = ''.join(_product_card(p) for p in latest[:10])
    latest_html = f'''
    <section class="sec-block">
      <div class="sec-head">
        <h3>{_ico("bolt", 14)} Latest in {_esc(first.name)}</h3>
        <a class="sec-see">See all →</a>
      </div>
      <div class="latest-row">{latest_cards}</div>
    </section>'''

    # ── Full product grid (paginated below) ─────────────────────────
    all_prods = env['product.template'].sudo().search([
        ('public_categ_ids', 'child_of', first.id),
        ('is_published', '=', True),
    ], limit=12)
    if not all_prods:
        all_prods = env['product.template'].sudo().search([('is_published','=',True)], limit=12)
    grid_cards = ''.join(_product_card(p) for p in all_prods)

    # Header label changes based on whether sub-cats exist
    grid_head_label = 'All products' if subs else f'Products in {first.name}'
    total_count = env['product.template'].sudo().search_count([
        ('public_categ_ids', 'child_of', first.id),
        ('is_published', '=', True),
    ]) or len(all_prods)

    body = '''
<style>
  body { background: #F8F4E3; }
  .cat-topbar { padding: 10px 14px; background: #fff;
       border-bottom: 1px solid #F2EBD3; display: flex; gap: 8px; align-items: center; }
  .cat-topbar input { flex: 1; height: 38px; border: 0; background: #F2EBD3;
       border-radius: 12px; padding: 0 14px 0 36px; font-size: 13px; outline: 0;
       background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='%239c8a5e'><path d='M21 19l-4-4a8 8 0 1 0-2 2l4 4zm-12-3a6 6 0 1 1 6-6 6 6 0 0 1-6 6z'/></svg>");
       background-repeat: no-repeat; background-position: 12px center; }
  .cat-topbar .icon-btn { width: 38px; height: 38px; background: #F2EBD3;
       color: #5d4d2e; border: 0; border-radius: 12px; cursor: pointer;
       display: grid; place-items: center; }

  .cat-layout { display: flex; height: calc(100vh - 26px - 78px - 60px);
       background: #F8F4E3; }
  .cat-sidebar { width: 88px; background: #fff; overflow-y: auto;
       padding: 4px 0; flex-shrink: 0;
       border-right: 1px solid #F2EBD3; }
  .cat-sidebar::-webkit-scrollbar { display: none; }
  .cat-side-item { display: flex; flex-direction: column; align-items: center;
       gap: 5px; padding: 12px 4px; text-decoration: none; color: #5d4d2e;
       font-size: 11px; font-weight: 600; text-align: center;
       border-inline-start: 3px solid transparent; cursor: pointer; }
  .cat-side-item:hover { background: rgba(245,195,32,.08); }
  .cat-side-item.on { background: #FFFCEF; border-inline-start-color: #F5C320;
       color: #412402; font-weight: 800; }
  .cat-side-item .cat-ico { width: 42px; height: 42px; border-radius: 12px;
       background-size: cover; background-position: center;
       background-color: #FFF5D0; }
  .cat-side-item .cat-ico.emoji { display: grid; place-items: center;
       font-size: 22px; background: #FFE066; }
  .cat-side-item span { font-size: 10.5px; line-height: 1.3; overflow: hidden;
       text-overflow: ellipsis; display: -webkit-box; -webkit-line-clamp: 2;
       -webkit-box-orient: vertical; max-height: 28px; }

  .cat-content { flex: 1; overflow-y: auto; padding: 8px 0; }
  .cat-content::-webkit-scrollbar { display: none; }

  /* Section block */
  .sec-block { background: #fff; margin: 0 10px 10px; border-radius: 14px;
       padding: 14px 12px; box-shadow: 0 1px 3px rgba(0,0,0,.04); }
  .sec-head { display: flex; align-items: center; justify-content: space-between;
       margin-bottom: 12px; padding: 0 2px; }
  .sec-head h3 { margin: 0; font-size: 14px; font-weight: 800; color: #1a1108;
       display: flex; align-items: center; gap: 6px; }
  .sec-head h3 svg { color: #C99000; }
  .sec-head .sec-meta { font-size: 11px; color: #9c8a5e; font-weight: 700; }
  .sec-head .sec-see { font-size: 12px; color: #5d4d2e; font-weight: 700;
       text-decoration: none; cursor: pointer; }

  /* Sub-category grid (visual cards 3-col) */
  .sc-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; }
  .sc-card { display: block; text-decoration: none; color: #1a1108;
       text-align: center; cursor: pointer; }
  .sc-img { width: 100%; aspect-ratio: 1; border-radius: 12px;
       background-size: cover; background-position: center;
       margin-bottom: 6px; display: grid; place-items: center; font-size: 32px;
       color: #412402; box-shadow: 0 2px 6px rgba(0,0,0,.05);
       transition: transform .15s, box-shadow .15s; }
  .sc-card:hover .sc-img { transform: translateY(-2px);
       box-shadow: 0 6px 14px -4px rgba(65,36,2,.2); }
  .sc-name { font-size: 11.5px; font-weight: 700; line-height: 1.3;
       overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2;
       -webkit-box-orient: vertical; max-height: 30px; }
  .sc-count { font-size: 10px; color: #9c8a5e; margin-top: 1px; }

  /* Latest products horizontal slider */
  .latest-row { display: flex; gap: 10px; overflow-x: auto; scrollbar-width: none;
       margin: 0 -12px; padding: 0 12px 4px; }
  .latest-row::-webkit-scrollbar { display: none; }
  .latest-row .product-card { flex: 0 0 145px; }

  /* Sort bar */
  .grid-head { display: flex; align-items: center; justify-content: space-between;
       padding: 0 14px 10px; }
  .grid-head h3 { font-size: 14px; font-weight: 800; color: #1a1108; margin: 0; }
  .grid-head .sort-acts { display: flex; gap: 12px; font-size: 11px; }
  .grid-head .sort-acts button { background: transparent; border: 0; cursor: pointer;
       color: #412402; font-weight: 700; font-size: 11px;
       display: inline-flex; align-items: center; gap: 4px; }
  .grid-head .total { font-size: 11px; color: #9c8a5e; }

  /* Main grid */
  .cc-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; padding: 0 10px 20px; }

''' + _PRODUCT_CARD_CSS + '''
</style>
<div class="cat-topbar">
  <input placeholder="Search categories…">
  <button class="icon-btn">''' + _ico('barcode',18) + '''</button>
  <button class="icon-btn">''' + _ico('camera',18) + '''</button>
</div>
<div class="cat-layout">
  <div class="cat-sidebar">''' + sidebar + '''</div>
  <div class="cat-content">
    ''' + subcats_html + '''
    ''' + latest_html + '''
    <div class="grid-head">
      <div>
        <h3>''' + _esc(grid_head_label) + '''</h3>
        <span class="total">''' + str(total_count) + ''' items</span>
      </div>
      <div class="sort-acts">
        <button>''' + _ico('sort',12) + ''' Sort</button>
        <button>''' + _ico('filter',12) + ''' Filter</button>
      </div>
    </div>
    <div class="cc-grid">''' + grid_cards + '''</div>
  </div>
</div>
'''
    return body, first.name or 'Categories', True


# ═════════════════════════════════════════════════════════════════
# Additional screens — Search, Order Detail, Wishlist, Notifications,
# Auth, Brands, Loyalty Full, Wallet Full, Coupons, Try-On / Smart Fit
# ═════════════════════════════════════════════════════════════════


# ─── 11. SEARCH (autocomplete + recent + trending) ─────────────────

def render_search(env):
    # Pull a few real products for the suggestion preview
    prods = env['product.template'].sudo().search([('is_published','=',True)], limit=4)
    sug_cards = ''
    for p in prods:
        cur = p.currency_id; sym = cur.symbol if cur else 'KD'
        sug_cards += f'''
        <a class="sug-result">
          <img src="{_img("product.template", p.id, "image_256", p.write_date)}">
          <div class="sr-text">
            <div class="sr-name">{_esc(p.name)}</div>
            <div class="sr-meta"><span class="sr-pr">{p.list_price:.3f} {sym}</span> · ⭐ 4.7</div>
          </div>
        </a>'''
    body = '''
<style>
  body { background: #FAFAFA; }
  .srch-top { padding: 10px 12px; background: #fff; display: flex; gap: 8px;
       align-items: center; border-bottom: 1px solid #F2EBD3; }
  .srch-back { width: 38px; height: 38px; background: #F2EBD3; color: #412402;
       border: 0; border-radius: 10px; display: grid; place-items: center; }
  .srch-input-wrap { flex: 1; position: relative; }
  .srch-input { width: 100%; height: 40px; border: 0; background: #F2EBD3;
       border-radius: 12px; padding: 0 42px 0 38px; font-size: 13px; outline: 0;
       background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='%239c8a5e'><path d='M21 19l-4-4a8 8 0 1 0-2 2l4 4zm-12-3a6 6 0 1 1 6-6 6 6 0 0 1-6 6z'/></svg>");
       background-repeat: no-repeat; background-position: 12px center; }
  .srch-input-wrap .icons { position: absolute; right: 8px; top: 50%;
       transform: translateY(-50%); display: flex; gap: 4px; }
  .srch-input-wrap .icons button { width: 30px; height: 30px; background: transparent;
       color: #9c8a5e; border: 0; cursor: pointer; display: grid; place-items: center; }
  .srch-cancel { color: #412402; font-weight: 700; font-size: 13px;
       background: transparent; border: 0; cursor: pointer; padding: 0 4px; }

  /* Suggestion dropdown (live as you type) */
  .sug-section { background: #fff; padding: 14px 16px;
       border-bottom: 8px solid #F8F4E3; }
  .sug-title { display: flex; align-items: center; justify-content: space-between;
       font-size: 11px; color: #9c8a5e; font-weight: 700; text-transform: uppercase;
       letter-spacing: .5px; margin-bottom: 10px; }
  .sug-title .clr { color: #5d4d2e; text-transform: none; cursor: pointer; }
  /* Recent searches */
  .recent-list { display: flex; flex-wrap: wrap; gap: 6px; }
  .recent-chip { display: inline-flex; align-items: center; gap: 6px;
       padding: 7px 12px 7px 10px; background: #F2EBD3; border-radius: 999px;
       font-size: 12.5px; color: #5d4d2e; cursor: pointer; }
  .recent-chip .rm { color: #b91c1c; opacity: .7; font-weight: 700; }
  /* Trending grid */
  .trend-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
  .trend-item { display: flex; align-items: center; gap: 8px;
       padding: 10px 12px; border-radius: 10px; background: #FFFCEF;
       border: 1px solid #FFE8A0; cursor: pointer; font-size: 12.5px;
       color: #412402; font-weight: 700; }
  .trend-item .rank { width: 22px; height: 22px; background: #FFD340;
       color: #412402; border-radius: 6px; display: grid; place-items: center;
       font-weight: 900; font-size: 11px; flex-shrink: 0; }
  .trend-item .rank.top { background: #FF4D4D; color: #fff; }
  /* Quick categories */
  .qcat-row { display: flex; gap: 8px; overflow-x: auto; scrollbar-width: none; padding-bottom: 4px; }
  .qcat-row::-webkit-scrollbar { display: none; }
  .qcat { flex: 0 0 80px; padding: 14px 8px; background: #FFF5D0;
       border-radius: 12px; text-align: center; cursor: pointer; color: #412402;
       font-size: 11px; font-weight: 700; }
  .qcat .ico { font-size: 24px; display: block; margin-bottom: 4px; }
  /* Suggested product results */
  .sug-result { display: flex; gap: 10px; padding: 10px 0;
       border-bottom: 1px solid #F8F4E3; text-decoration: none; color: inherit; }
  .sug-result:last-child { border-bottom: 0; }
  .sug-result img { width: 50px; height: 50px; border-radius: 8px;
       object-fit: cover; background: #F2EBD3; }
  .sr-text { flex: 1; min-width: 0; }
  .sr-name { font-size: 12.5px; color: #1a1108; line-height: 1.4;
       overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2;
       -webkit-box-orient: vertical; }
  .sr-meta { font-size: 11px; color: #9c8a5e; margin-top: 2px; }
  .sr-pr { color: #412402; font-weight: 800; }
</style>
<div class="srch-top">
  <button class="srch-back">←</button>
  <div class="srch-input-wrap">
    <input class="srch-input" placeholder="ابحث عن منتج، ماركة، أو ﺗﺎﺟﺮ…" value="smart watch">
    <div class="icons">
      <button>''' + _ico('barcode', 18) + '''</button>
      <button>''' + _ico('camera', 18) + '''</button>
    </div>
  </div>
  <button class="srch-cancel">Cancel</button>
</div>

<!-- Live suggestions (when typing) -->
<div class="sug-section">
  <div class="sug-title"><span>Suggested results</span></div>
  ''' + sug_cards + '''
  <button style="margin-top:10px;background:#412402;color:#FFD340;border:0;border-radius:10px;padding:11px;width:100%;font-weight:800;font-size:13px;cursor:pointer">See all results for "smart watch" →</button>
</div>

<!-- Recent -->
<div class="sug-section">
  <div class="sug-title"><span>Recent searches</span><span class="clr">Clear all</span></div>
  <div class="recent-list">
    <span class="recent-chip">apple watch <span class="rm">✕</span></span>
    <span class="recent-chip">huawei buds <span class="rm">✕</span></span>
    <span class="recent-chip">samsung tv 55 <span class="rm">✕</span></span>
    <span class="recent-chip">عطر زمزم <span class="rm">✕</span></span>
    <span class="recent-chip">red dress <span class="rm">✕</span></span>
  </div>
</div>

<!-- Trending -->
<div class="sug-section">
  <div class="sug-title"><span>Trending today</span><span style="color:#FF4D4D">🔥</span></div>
  <div class="trend-grid">
    <div class="trend-item"><span class="rank top">1</span>Smart watches</div>
    <div class="trend-item"><span class="rank top">2</span>iPhone 17 cases</div>
    <div class="trend-item"><span class="rank">3</span>Air fryer</div>
    <div class="trend-item"><span class="rank">4</span>Perfumes</div>
    <div class="trend-item"><span class="rank">5</span>Kids tablets</div>
    <div class="trend-item"><span class="rank">6</span>Gaming chair</div>
  </div>
</div>

<!-- Quick categories -->
<div class="sug-section" style="border-bottom:0">
  <div class="sug-title"><span>Browse categories</span></div>
  <div class="qcat-row">
    <div class="qcat"><span class="ico">📱</span>Phones</div>
    <div class="qcat"><span class="ico">👗</span>Fashion</div>
    <div class="qcat"><span class="ico">💄</span>Beauty</div>
    <div class="qcat"><span class="ico">🏠</span>Home</div>
    <div class="qcat"><span class="ico">⌚</span>Watches</div>
    <div class="qcat"><span class="ico">🎮</span>Gaming</div>
  </div>
</div>
'''
    return body, 'Search', False


# ─── 12. ORDER DETAIL (timeline + tracking) ─────────────────────────

def render_order(env):
    body = '''
<style>
  body { background: #F8F4E3; }
  .ord-top { padding: 14px 18px; background: #fff; border-bottom: 1px solid #F2EBD3; }
  .ord-top h1 { margin: 0; font-size: 17px; font-weight: 800; color: #1a1108; }
  .ord-top .ord-meta { font-size: 12px; color: #9c8a5e; margin-top: 4px; }
  .ord-top .ord-state { display: inline-flex; align-items: center; gap: 4px;
       background: #ECFDF5; color: #047857; padding: 3px 9px; border-radius: 6px;
       font-size: 11px; font-weight: 800; margin-top: 6px; letter-spacing: .3px; }
  .ord-state .dot { width: 6px; height: 6px; border-radius: 50%; background: #10b981;
       animation: pulse 1.5s ease-in-out infinite; }
  @keyframes pulse { 0%,100% {opacity:1;} 50% {opacity:.4;} }

  /* Live ETA card */
  .eta-card { background: linear-gradient(135deg,#412402,#1F1100); color: #FFD340;
       margin: 8px 14px; border-radius: 16px; padding: 16px;
       display: flex; gap: 12px; align-items: center;
       box-shadow: 0 10px 25px -8px rgba(65,36,2,.4); }
  .eta-icon { width: 56px; height: 56px; background: rgba(255,211,64,.2);
       border-radius: 14px; display: grid; place-items: center;
       color: #FFD340; flex-shrink: 0; }
  .eta-body { flex: 1; }
  .eta-title { font-size: 13px; opacity: .8; }
  .eta-time { font-size: 24px; font-weight: 900; margin: 2px 0; }
  .eta-sub { font-size: 11px; opacity: .65; }
  .eta-action { background: #FFD340; color: #412402; border: 0;
       padding: 8px 12px; border-radius: 10px; font-weight: 800; font-size: 11px;
       cursor: pointer; }

  /* Map placeholder */
  .map-box { background: #fff; margin: 8px 14px 0; border-radius: 16px;
       overflow: hidden; height: 160px; position: relative;
       background-image:
         linear-gradient(0deg, rgba(248,244,227,.4), rgba(248,244,227,.4)),
         repeating-linear-gradient(0deg, transparent 0 30px, #F2EBD3 30px 31px),
         repeating-linear-gradient(90deg, transparent 0 30px, #F2EBD3 30px 31px),
         #FFFCEF; }
  .map-driver { position: absolute; top: 90px; left: 60px;
       width: 28px; height: 28px; background: #412402; color: #FFD340;
       border-radius: 50%; display: grid; place-items: center;
       border: 3px solid #fff; box-shadow: 0 4px 12px rgba(0,0,0,.2); }
  .map-dest { position: absolute; bottom: 18px; right: 30px;
       background: #F5C320; color: #412402; padding: 4px 8px;
       border-radius: 8px; font-size: 11px; font-weight: 800; display: flex; gap: 4px; align-items: center;
       box-shadow: 0 4px 10px rgba(0,0,0,.15); }
  .map-line { position: absolute; top: 105px; left: 88px; right: 90px;
       height: 0; border-top: 2.5px dashed #F5C320; }

  /* Timeline */
  .tl-card { background: #fff; margin: 8px 14px; border-radius: 16px;
       padding: 18px 14px 8px; }
  .tl-card h3 { margin: 0 0 14px; font-size: 14px; font-weight: 800; color: #412402; }
  .tl-step { display: flex; gap: 12px; padding-bottom: 14px; position: relative; }
  .tl-step::before { content: ""; position: absolute; left: 13px; top: 28px;
       bottom: -2px; width: 2px; background: #F2EBD3; }
  .tl-step:last-child::before { display: none; }
  .tl-step.done .tl-ico { background: #10b981; color: #fff; }
  .tl-step.done::before { background: #10b981; }
  .tl-step.now .tl-ico { background: #FFD340; color: #412402;
       box-shadow: 0 0 0 4px rgba(245,195,32,.25);
       animation: pulse 1.5s ease-in-out infinite; }
  .tl-step.now::before { background: linear-gradient(180deg,#10b981,#F2EBD3); }
  .tl-ico { width: 28px; height: 28px; background: #F2EBD3; color: #9c8a5e;
       border-radius: 50%; display: grid; place-items: center; flex-shrink: 0;
       z-index: 1; position: relative; }
  .tl-text { flex: 1; padding-top: 3px; }
  .tl-title { font-size: 13px; font-weight: 800; color: #1a1108; }
  .tl-step.done .tl-title { color: #1a1108; }
  .tl-step:not(.done):not(.now) .tl-title { color: #9c8a5e; }
  .tl-time { font-size: 11px; color: #9c8a5e; margin-top: 2px; }
  .tl-note { font-size: 11.5px; color: #5d4d2e; margin-top: 4px;
       background: #FFFCEF; padding: 6px 10px; border-radius: 8px;
       border-left: 3px solid #FFD340; }

  /* Items */
  .items-card { background: #fff; margin: 8px 14px; border-radius: 16px;
       padding: 14px; }
  .items-card h3 { margin: 0 0 12px; font-size: 14px; font-weight: 800; color: #412402; }
  .ord-item { display: flex; gap: 10px; padding: 8px 0;
       border-bottom: 1px solid #F8F4E3; }
  .ord-item:last-child { border-bottom: 0; }
  .ord-item img { width: 60px; height: 60px; border-radius: 8px; object-fit: cover;
       background: #F2EBD3; flex-shrink: 0; }
  .oi-name { font-size: 12.5px; color: #1a1108; line-height: 1.35;
       overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2;
       -webkit-box-orient: vertical; }
  .oi-meta { font-size: 11px; color: #9c8a5e; margin-top: 4px;
       display: flex; justify-content: space-between; }
  .oi-meta b { color: #412402; font-weight: 800; }

  /* Summary */
  .sum-card { background: #fff; margin: 8px 14px; border-radius: 16px; padding: 14px 16px; }
  .sum-card h3 { margin: 0 0 12px; font-size: 14px; font-weight: 800; color: #412402; }
  .sum-row { display: flex; justify-content: space-between; margin: 6px 0;
       font-size: 12.5px; color: #5d4d2e; }
  .sum-row.total { font-weight: 900; font-size: 16px; color: #412402;
       border-top: 1px solid #F2EBD3; padding-top: 8px; margin-top: 8px; }
  /* Actions */
  .ord-actions { display: grid; grid-template-columns: 1fr 1fr; gap: 8px;
       padding: 8px 14px 100px; }
  .oa-btn { padding: 14px; border-radius: 12px; border: 1.5px solid #F2EBD3;
       background: #fff; font-weight: 800; font-size: 13px; color: #412402;
       cursor: pointer; display: inline-flex; justify-content: center;
       align-items: center; gap: 6px; }
  .oa-btn.primary { background: #412402; color: #FFD340; border-color: #412402; }
  .oa-btn.danger { color: #b91c1c; border-color: #FFE3E3; }
</style>
<div class="ord-top">
  <h1>← Order #S00532</h1>
  <div class="ord-meta">Placed on May 28, 2026 · 3 items · KD 36.300</div>
  <span class="ord-state"><span class="dot"></span>OUT FOR DELIVERY</span>
</div>

<div class="eta-card">
  <div class="eta-icon">''' + _ico('truck',28) + '''</div>
  <div class="eta-body">
    <div class="eta-title">Arrives by</div>
    <div class="eta-time">Today, 3-5 PM</div>
    <div class="eta-sub">Driver Mohammed · 5 min away</div>
  </div>
  <button class="eta-action">Call</button>
</div>

<div class="map-box">
  <div class="map-line"></div>
  <div class="map-driver">''' + _ico('truck', 14) + '''</div>
  <div class="map-dest">''' + _ico('pin',12) + ''' You</div>
</div>

<!-- Timeline -->
<div class="tl-card">
  <h3>Tracking</h3>
  <div class="tl-step done">
    <div class="tl-ico">''' + _ico('check',14) + '''</div>
    <div class="tl-text">
      <div class="tl-title">Order placed</div>
      <div class="tl-time">May 28 · 11:24 AM</div>
    </div>
  </div>
  <div class="tl-step done">
    <div class="tl-ico">''' + _ico('check',14) + '''</div>
    <div class="tl-text">
      <div class="tl-title">Payment confirmed</div>
      <div class="tl-time">May 28 · 11:24 AM · KNET ****1234</div>
    </div>
  </div>
  <div class="tl-step done">
    <div class="tl-ico">''' + _ico('check',14) + '''</div>
    <div class="tl-text">
      <div class="tl-title">Packed by Uellow warehouse</div>
      <div class="tl-time">May 29 · 02:14 PM</div>
    </div>
  </div>
  <div class="tl-step done">
    <div class="tl-ico">''' + _ico('check',14) + '''</div>
    <div class="tl-text">
      <div class="tl-title">Picked up by courier</div>
      <div class="tl-time">May 30 · 09:48 AM</div>
      <div class="tl-note">Handover signed by driver Mohammed · vehicle KW-5512</div>
    </div>
  </div>
  <div class="tl-step now">
    <div class="tl-ico">''' + _ico('truck',14) + '''</div>
    <div class="tl-text">
      <div class="tl-title">Out for delivery</div>
      <div class="tl-time">Today · arrives 3-5 PM</div>
    </div>
  </div>
  <div class="tl-step">
    <div class="tl-ico">''' + _ico('home',14) + '''</div>
    <div class="tl-text">
      <div class="tl-title">Delivered</div>
      <div class="tl-time">—</div>
    </div>
  </div>
</div>

<!-- Items -->
<div class="items-card">
  <h3>Items</h3>
  <div class="ord-item">
    <img src="https://placehold.co/200/F5C320/412402?text=Watch">
    <div style="flex:1;min-width:0">
      <div class="oi-name">HainoTeko-18 Smart Watch For Female · Black</div>
      <div class="oi-meta"><span>Qty 1</span><b>8.500 KD</b></div>
    </div>
  </div>
  <div class="ord-item">
    <img src="https://placehold.co/200/412402/F5C320?text=Buds">
    <div style="flex:1;min-width:0">
      <div class="oi-name">Anker Soundcore C40i Earbuds · Dark Gray</div>
      <div class="oi-meta"><span>Qty 2</span><b>14.900 KD</b></div>
    </div>
  </div>
</div>

<!-- Summary -->
<div class="sum-card">
  <h3>Payment summary</h3>
  <div class="sum-row"><span>Subtotal (3 items)</span><span>38.300 KD</span></div>
  <div class="sum-row"><span>Delivery (Same-day)</span><span>2.000 KD</span></div>
  <div class="sum-row" style="color:#10b981"><span>SAVE15 coupon</span><span>− 1.500 KD</span></div>
  <div class="sum-row" style="color:#10b981"><span>Loyalty (-150 pts)</span><span>− 0.500 KD</span></div>
  <div class="sum-row total"><span>Paid</span><span>38.300 KD</span></div>
</div>

<!-- Actions -->
<div class="ord-actions">
  <button class="oa-btn">''' + _ico('return',14) + ''' Reorder</button>
  <button class="oa-btn">''' + _ico('box',14) + ''' Invoice</button>
  <button class="oa-btn">''' + _ico('chat',14) + ''' Contact seller</button>
  <button class="oa-btn">''' + _ico('star',14) + ''' Rate items</button>
  <button class="oa-btn danger">''' + _ico('return',14) + ''' Request return</button>
  <button class="oa-btn primary">''' + _ico('chat',14) + ''' Support</button>
</div>
'''
    return body, 'Order #S00532', True


# ─── 13. WISHLIST ──────────────────────────────────────────────────

def render_wishlist(env):
    prods = env['product.template'].sudo().search([('is_published','=',True)], limit=8)
    cards = ''
    for i, p in enumerate(prods):
        cur = p.currency_id; sym = cur.symbol if cur else 'KD'
        # Inject alerts on some items
        alert = ''
        if i == 0:
            alert = '<div class="w-alert price">⬇ Price dropped 12% since you added</div>'
        elif i == 1:
            alert = '<div class="w-alert stock">⚠ Only 3 left in stock</div>'
        elif i == 2:
            alert = '<div class="w-alert flash">⚡ On flash sale now</div>'
        cards += f'''
        <div class="wish-card">
          <div class="wc-img"><img src="{_img("product.template", p.id, "image_512", p.write_date)}"><button class="wc-rm">{_ico("heart",14)}</button></div>
          <div class="wc-body">
            <div class="wc-name">{_esc(p.name)}</div>
            <div class="wc-pr">{p.list_price:.3f} <span>{sym}</span></div>
            {alert}
            <button class="wc-add">{_ico("cart",12)} Add to cart</button>
          </div>
        </div>'''
    body = '''
<style>
  body { background: #F8F4E3; }
  .wl-top { padding: 14px 18px; background: #fff; border-bottom: 1px solid #F2EBD3; }
  .wl-top h1 { margin: 0; font-size: 18px; font-weight: 800; color: #1a1108; }
  .wl-top .count { font-size: 12px; color: #9c8a5e; margin-top: 2px; }
  .wl-filters { display: flex; gap: 6px; padding: 10px 14px;
       background: #fff; border-bottom: 1px solid #F2EBD3;
       overflow-x: auto; scrollbar-width: none; }
  .wl-filters::-webkit-scrollbar { display: none; }
  .wl-pill { flex: 0 0 auto; padding: 6px 12px; background: #F2EBD3;
       color: #5d4d2e; border-radius: 999px; font-size: 11.5px;
       font-weight: 700; cursor: pointer; white-space: nowrap; }
  .wl-pill.on { background: #412402; color: #FFD340; }
  .wl-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; padding: 12px; }
  .wish-card { background: #fff; border-radius: 14px; overflow: hidden;
       box-shadow: 0 1px 4px rgba(0,0,0,.05); }
  .wc-img { position: relative; background: #FAFAFA; }
  .wc-img img { width: 100%; aspect-ratio: 1; object-fit: cover; display: block; }
  .wc-rm { position: absolute; top: 8px; right: 8px; width: 30px; height: 30px;
       background: rgba(255,255,255,.95); border: 0; border-radius: 50%;
       color: #FF4D4D; cursor: pointer; display: grid; place-items: center; }
  .wc-body { padding: 10px; }
  .wc-name { font-size: 12.5px; color: #1a1108; line-height: 1.35;
       overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2;
       -webkit-box-orient: vertical; min-height: 34px; }
  .wc-pr { font-weight: 900; font-size: 16px; color: #412402; margin: 6px 0 6px; }
  .wc-pr span { font-size: 11px; font-weight: 700; color: #9c8a5e; }
  .w-alert { font-size: 10.5px; padding: 4px 8px; border-radius: 6px;
       margin: 4px 0; font-weight: 700; }
  .w-alert.price { background: #ECFDF5; color: #047857; }
  .w-alert.stock { background: #FFF5D0; color: #C99000; }
  .w-alert.flash { background: linear-gradient(135deg,#FF4D4D,#C81212); color: #fff; }
  .wc-add { width: 100%; padding: 8px; background: #FFD340; color: #412402;
       border: 0; border-radius: 8px; font-weight: 800; font-size: 12px;
       cursor: pointer; margin-top: 6px;
       display: inline-flex; justify-content: center; align-items: center; gap: 4px; }
</style>
<div class="wl-top">
  <h1>← My Wishlist</h1>
  <div class="count">''' + str(len(prods)) + ''' items · 2 on sale · 1 price dropped</div>
</div>
<div class="wl-filters">
  <span class="wl-pill on">All</span>
  <span class="wl-pill">In stock</span>
  <span class="wl-pill">On sale</span>
  <span class="wl-pill">Price drop</span>
  <span class="wl-pill">Recently added</span>
</div>
<div class="wl-grid">''' + cards + '''</div>
'''
    return body, 'Wishlist', True


# ─── 14. NOTIFICATIONS ────────────────────────────────────────────

def render_notifications(env):
    body = '''
<style>
  body { background: #F8F4E3; }
  .nt-top { padding: 14px 18px; background: #fff; border-bottom: 1px solid #F2EBD3;
       display: flex; align-items: center; justify-content: space-between; }
  .nt-top h1 { margin: 0; font-size: 18px; font-weight: 800; color: #1a1108; }
  .nt-top .mark-all { background: transparent; border: 0; color: #5d4d2e;
       font-weight: 700; font-size: 12px; cursor: pointer; }
  .nt-tabs { display: flex; gap: 4px; padding: 10px 12px; background: #fff;
       border-bottom: 1px solid #F2EBD3; overflow-x: auto; scrollbar-width: none; }
  .nt-tabs::-webkit-scrollbar { display: none; }
  .nt-tab { flex: 0 0 auto; padding: 6px 12px; background: #F2EBD3;
       color: #5d4d2e; border-radius: 999px; font-size: 11.5px; font-weight: 700;
       white-space: nowrap; cursor: pointer; }
  .nt-tab.on { background: #412402; color: #FFD340; }
  .nt-tab .badge { background: #FF4D4D; color: #fff; padding: 1px 5px;
       border-radius: 999px; font-size: 9.5px; font-weight: 900; margin-inline-start: 4px; }
  .nt-tab.on .badge { background: #FFD340; color: #412402; }
  /* Group label */
  .nt-day { font-size: 11px; color: #9c8a5e; font-weight: 700;
       text-transform: uppercase; padding: 14px 18px 6px; letter-spacing: .5px; }
  /* Notification card */
  .nt-card { display: flex; gap: 12px; background: #fff; padding: 12px 16px;
       align-items: flex-start; border-bottom: 1px solid #F8F4E3; cursor: pointer; }
  .nt-card.unread { background: #FFFCEF; }
  .nt-ico { width: 38px; height: 38px; border-radius: 12px;
       display: grid; place-items: center; flex-shrink: 0; }
  .nt-ico.order { background: #FFF5D0; color: #C99000; }
  .nt-ico.promo { background: #FFE3E3; color: #b91c1c; }
  .nt-ico.beena { background: #412402; color: #FFD340; }
  .nt-ico.system { background: #E0F7EC; color: #047857; }
  .nt-text { flex: 1; min-width: 0; }
  .nt-title { font-weight: 800; font-size: 13px; color: #1a1108;
       display: flex; align-items: center; gap: 6px; }
  .nt-card.unread .nt-title::after { content: ""; display: inline-block;
       width: 6px; height: 6px; border-radius: 50%; background: #FF4D4D; }
  .nt-body { font-size: 12.5px; color: #5d4d2e; margin: 3px 0; line-height: 1.4; }
  .nt-time { font-size: 11px; color: #9c8a5e; }
  .nt-thumb { width: 56px; height: 56px; border-radius: 10px; object-fit: cover;
       flex-shrink: 0; background: #F2EBD3; }
</style>
<div class="nt-top">
  <h1>← Notifications</h1>
  <button class="mark-all">Mark all read</button>
</div>
<div class="nt-tabs">
  <span class="nt-tab on">All<span class="badge">12</span></span>
  <span class="nt-tab">Orders<span class="badge">3</span></span>
  <span class="nt-tab">Promos<span class="badge">5</span></span>
  <span class="nt-tab">Beena AI<span class="badge">2</span></span>
  <span class="nt-tab">System</span>
</div>

<div class="nt-day">Today</div>
<div class="nt-card unread">
  <div class="nt-ico order">''' + _ico('truck',20) + '''</div>
  <div class="nt-text">
    <div class="nt-title">Out for delivery</div>
    <div class="nt-body">Your order #S00532 is on its way · arrives 3-5 PM</div>
    <div class="nt-time">5 minutes ago</div>
  </div>
  <img class="nt-thumb" src="https://placehold.co/100/F5C320/412402?text=📦">
</div>

<div class="nt-card unread">
  <div class="nt-ico promo">''' + _ico('tag',20) + '''</div>
  <div class="nt-text">
    <div class="nt-title">Flash sale: up to 70% off</div>
    <div class="nt-body">Limited time deals on smart watches · ends tonight</div>
    <div class="nt-time">1 hour ago</div>
  </div>
</div>

<div class="nt-card unread">
  <div class="nt-ico beena">''' + _ico('chat',20) + '''</div>
  <div class="nt-text">
    <div class="nt-title">Beena suggested products for you</div>
    <div class="nt-body">Based on your search "smart watch", here are 5 picks just for you</div>
    <div class="nt-time">3 hours ago</div>
  </div>
</div>

<div class="nt-day">Yesterday</div>
<div class="nt-card">
  <div class="nt-ico order">''' + _ico('check',20) + '''</div>
  <div class="nt-text">
    <div class="nt-title">Order packed</div>
    <div class="nt-body">Your order #S00532 has been packed and is ready to ship</div>
    <div class="nt-time">Yesterday at 2:14 PM</div>
  </div>
</div>
<div class="nt-card">
  <div class="nt-ico system">''' + _ico('star',20) + '''</div>
  <div class="nt-text">
    <div class="nt-title">You earned 150 loyalty points</div>
    <div class="nt-body">Thanks for your purchase · 150 pts added to your account</div>
    <div class="nt-time">Yesterday at 11:30 AM</div>
  </div>
</div>
<div class="nt-card">
  <div class="nt-ico promo">''' + _ico('gift',20) + '''</div>
  <div class="nt-text">
    <div class="nt-title">⬇ Price drop on your wishlist</div>
    <div class="nt-body">"HainoTeko Watch" dropped from 12.000 → 8.500 KD (-29%)</div>
    <div class="nt-time">Yesterday at 9:12 AM</div>
  </div>
  <img class="nt-thumb" src="https://placehold.co/100/412402/F5C320?text=⌚">
</div>

<div class="nt-day">Earlier</div>
<div class="nt-card">
  <div class="nt-ico system">''' + _ico('shield',20) + '''</div>
  <div class="nt-text">
    <div class="nt-title">New login from iPhone 16 Pro</div>
    <div class="nt-body">If this wasn't you, secure your account immediately</div>
    <div class="nt-time">3 days ago</div>
  </div>
</div>
<div class="nt-card">
  <div class="nt-ico beena">✨</div>
  <div class="nt-text">
    <div class="nt-title">Try Beena's new visual search</div>
    <div class="nt-body">Take a photo of any product and let Beena find it for you</div>
    <div class="nt-time">5 days ago</div>
  </div>
</div>
'''
    return body, 'Notifications', True


# ─── 15. AUTH (sign in + sign up tabbed) ──────────────────────────

def render_auth(env):
    body = '''
<style>
  body { background: linear-gradient(160deg,#FFD340 0%, #F5C320 35%, #C99000 100%); }
  .auth-page { padding: 40px 24px 30px; min-height: 100vh; }
  .auth-logo { text-align: center; margin: 0 0 24px; }
  .auth-logo .b { display: inline-flex; align-items: center; gap: 10px;
       background: #412402; padding: 10px 18px; border-radius: 16px; }
  .auth-logo .dot { width: 32px; height: 32px; background: #FFD340;
       border-radius: 10px; display: grid; place-items: center;
       color: #412402; font-weight: 900; font-size: 18px; }
  .auth-logo .name { color: #FFD340; font-weight: 900; font-size: 20px; }
  .auth-card { background: #fff; border-radius: 20px; padding: 22px 20px 24px;
       box-shadow: 0 16px 40px -10px rgba(65,36,2,.25); }
  .auth-tabs { display: flex; gap: 4px; background: #F2EBD3; padding: 4px;
       border-radius: 12px; margin-bottom: 22px; }
  .auth-tabs button { flex: 1; padding: 10px; border: 0; background: transparent;
       color: #5d4d2e; font-weight: 800; border-radius: 8px; cursor: pointer; }
  .auth-tabs button.on { background: #412402; color: #FFD340; }
  .auth-form { display: grid; gap: 10px; }
  .auth-label { font-size: 11px; color: #9c8a5e; font-weight: 700;
       margin: 4px 0 4px; text-transform: uppercase; letter-spacing: .5px; }
  .auth-input { width: 100%; height: 46px; padding: 0 14px; border: 1.5px solid #F2EBD3;
       border-radius: 12px; font-size: 14px; outline: 0; background: #FFFCEF; }
  .auth-input:focus { border-color: #F5C320; background: #fff; }
  .auth-phone { display: flex; gap: 6px; }
  .auth-phone .code { width: 80px; height: 46px; border: 1.5px solid #F2EBD3;
       background: #FFFCEF; border-radius: 12px; display: flex; align-items: center;
       justify-content: center; font-weight: 800; color: #412402; gap: 4px; }
  .auth-phone input { flex: 1; }
  .auth-row { display: flex; align-items: center; justify-content: space-between;
       margin-top: 4px; font-size: 12px; }
  .auth-row label { display: inline-flex; align-items: center; gap: 6px;
       color: #5d4d2e; }
  .auth-row .forgot { color: #412402; font-weight: 800; cursor: pointer; }
  .auth-cta { width: 100%; padding: 14px; background: #412402; color: #FFD340;
       border: 0; border-radius: 12px; font-weight: 800; font-size: 15px;
       cursor: pointer; margin-top: 8px;
       box-shadow: 0 8px 20px -6px rgba(65,36,2,.45); }
  .auth-sep { display: flex; align-items: center; gap: 10px; margin: 18px 0 14px;
       color: #9c8a5e; font-size: 11px; }
  .auth-sep::before, .auth-sep::after { content: ""; flex: 1; height: 1px; background: #F2EBD3; }
  .social-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
  .social-btn { padding: 12px; border: 1.5px solid #F2EBD3; border-radius: 12px;
       background: #fff; color: #1a1108; font-weight: 700; font-size: 13px;
       display: inline-flex; align-items: center; justify-content: center; gap: 8px;
       cursor: pointer; }
  .social-btn svg { width: 18px; height: 18px; }
  .social-btn.google { color: #4285F4; }
  .social-btn.apple { color: #000; }
  .social-btn.fb { color: #1877F2; }
  .social-btn.phone { color: #412402; }
  .auth-foot { text-align: center; font-size: 11px; color: #5d4d2e;
       margin-top: 20px; line-height: 1.6; }
  .auth-foot b { color: #412402; }
</style>
<div class="auth-page">
  <div class="auth-logo">
    <div class="b">
      <div class="dot">U</div>
      <div class="name">Uellow</div>
    </div>
  </div>
  <div class="auth-card">
    <div class="auth-tabs">
      <button class="on">Sign in</button>
      <button>Create account</button>
    </div>
    <div class="auth-form">
      <div>
        <div class="auth-label">Email or phone</div>
        <input class="auth-input" type="text" placeholder="you@example.com" value="ali@uellow.com">
      </div>
      <div>
        <div class="auth-label">Password</div>
        <input class="auth-input" type="password" placeholder="••••••••" value="password">
      </div>
      <div class="auth-row">
        <label><input type="checkbox" checked> Remember me</label>
        <span class="forgot">Forgot password?</span>
      </div>
      <button class="auth-cta">Sign in →</button>
    </div>
    <div class="auth-sep">or continue with</div>
    <div class="social-grid">
      <button class="social-btn google"><svg viewBox="0 0 24 24" fill="currentColor"><path d="M22.5 12.3c0-.8-.1-1.5-.2-2.2H12v4.2h5.9c-.3 1.4-1 2.5-2.2 3.3v2.7h3.5c2-1.9 3.3-4.7 3.3-8z"/></svg>Google</button>
      <button class="social-btn apple"><svg viewBox="0 0 24 24" fill="currentColor"><path d="M16.4 1.6c-1 .1-2.2.7-2.9 1.5-.7.7-1.2 1.8-1 2.8 1.1.1 2.2-.5 3-1.3.7-.7 1.2-1.8.9-3zm3.4 16.8c-.4 1-1 2-1.6 2.9-.9 1.2-2 2.8-3.4 2.8-1.3 0-1.7-.9-3.5-.9-1.8 0-2.2.9-3.5.9-1.4 0-2.5-1.5-3.3-2.7C2.4 18.2 2 14 4 11.4c1.1-1.5 2.7-2.4 4.3-2.4 1.4 0 2.3.9 3.5.9 1.1 0 1.8-.9 3.5-.9 1.4 0 2.9.8 4 2.1-3.5 1.9-3 6.9.5 7.3z"/></svg>Apple</button>
      <button class="social-btn fb"><svg viewBox="0 0 24 24" fill="currentColor"><path d="M22 12a10 10 0 1 0-11.6 9.9V15h-2.5v-3h2.5V9.8c0-2.5 1.5-3.9 3.7-3.9 1.1 0 2.2.2 2.2.2v2.4h-1.2c-1.2 0-1.6.8-1.6 1.5V12h2.7l-.4 3h-2.3v6.9A10 10 0 0 0 22 12z"/></svg>Facebook</button>
      <button class="social-btn phone">''' + _ico('chat',16) + '''Phone OTP</button>
    </div>
    <div class="auth-foot">
      By continuing you agree to our <b>Terms</b> &amp; <b>Privacy</b>.<br>
      New to Uellow? <b>Create an account →</b>
    </div>
  </div>
</div>
'''
    return body, 'Sign in', False


# ─── 16. BRANDS ──────────────────────────────────────────────────

def render_brands(env):
    Vendor = env.get('uellow.vendor')
    vendor_cards = ''
    if Vendor is not None:
        vs = Vendor.sudo().search([], limit=50)
        for v in vs:
            initial = (v.store_name_en or 'U')[0]
            vendor_cards += f'''
            <a class="brand-card">
              <div class="bc-logo" style="background:{v.brand_color or "#FFD340"}">{_esc(initial)}</div>
              <div class="bc-name">{_esc(v.store_name_en or "Uellow")}</div>
              <div class="bc-meta">★ 4.8 · 1.2k</div>
            </a>'''
    if not vendor_cards:
        demo = [('Anker','#FF4D4D'),('Samsung','#3b82f6'),('Huawei','#10b981'),
                ('Apple','#000'),('Xiaomi','#FF9500'),('Bestrio','#412402'),
                ('Sumo','#FFD340'),('Vidvie','#8B5CF6'),('Borofone','#06B6D4'),
                ('Sayona','#EC4899'),('Sing-e','#84CC16'),('Hago','#F59E0B')]
        for n, c in demo:
            vendor_cards += f'<a class="brand-card"><div class="bc-logo" style="background:{c}">{n[0]}</div><div class="bc-name">{n}</div><div class="bc-meta">★ 4.6 · 850</div></a>'

    body = '''
<style>
  body { background: #F8F4E3; }
  .br-top { padding: 14px 18px; background: #fff; border-bottom: 1px solid #F2EBD3; }
  .br-top h1 { margin: 0; font-size: 18px; font-weight: 800; color: #1a1108; }
  .br-top .meta { font-size: 12px; color: #9c8a5e; margin-top: 2px; }
  .br-search { padding: 10px 14px; background: #fff; }
  .br-search input { width: 100%; height: 40px; border: 0; background: #F2EBD3;
       border-radius: 12px; padding: 0 14px 0 38px; font-size: 13px;
       background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='%239c8a5e'><path d='M21 19l-4-4a8 8 0 1 0-2 2l4 4zm-12-3a6 6 0 1 1 6-6 6 6 0 0 1-6 6z'/></svg>");
       background-repeat: no-repeat; background-position: 12px center; outline: 0; }
  /* Featured brands */
  .br-featured { padding: 14px; background: #fff; margin-bottom: 8px; }
  .br-featured h3 { margin: 0 0 12px; font-size: 13px; font-weight: 800; color: #412402; }
  .feat-row { display: flex; gap: 10px; overflow-x: auto; scrollbar-width: none; }
  .feat-row::-webkit-scrollbar { display: none; }
  .feat-card { flex: 0 0 140px; background: linear-gradient(135deg,#412402,#7a4a08);
       border-radius: 14px; padding: 14px; color: #FFD340; cursor: pointer; }
  .feat-card .fc-logo { width: 44px; height: 44px; background: #FFD340;
       color: #412402; border-radius: 12px; display: grid; place-items: center;
       font-weight: 900; font-size: 20px; margin-bottom: 10px; }
  .feat-card .fc-name { font-size: 14px; font-weight: 800; }
  .feat-card .fc-disc { background: #FFD340; color: #412402; padding: 2px 7px;
       border-radius: 6px; font-size: 10px; font-weight: 800; display: inline-block;
       margin-top: 6px; }
  /* A-Z bar */
  .alphabet { position: fixed; right: 8px; top: 50%; transform: translateY(-50%);
       display: flex; flex-direction: column; gap: 1px; z-index: 30; }
  .alphabet a { font-size: 10px; color: #9c8a5e; font-weight: 700;
       text-decoration: none; padding: 0 4px; cursor: pointer; }
  .alphabet a.on { color: #FF4D4D; }
  /* Grid */
  .brand-group { background: #fff; padding: 12px 14px;
       margin-bottom: 8px; }
  .brand-group h4 { margin: 0 0 10px; font-size: 13px; color: #412402;
       font-weight: 800; }
  .brand-grid { display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 8px; }
  .brand-card { display: block; text-decoration: none; color: inherit;
       text-align: center; padding: 10px 4px; background: #FFFCEF;
       border-radius: 10px; cursor: pointer; border: 1px solid #F2EBD3; }
  .brand-card:hover { border-color: #F5C320; }
  .bc-logo { width: 48px; height: 48px; border-radius: 12px; display: grid;
       place-items: center; color: #fff; font-weight: 900; font-size: 18px;
       margin: 0 auto 6px; }
  .bc-name { font-size: 11px; color: #1a1108; font-weight: 700; line-height: 1.2;
       overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .bc-meta { font-size: 9.5px; color: #9c8a5e; margin-top: 2px; }
</style>
<div class="br-top">
  <h1>← All Brands</h1>
  <div class="meta">Browse 120+ brands · vendors &amp; flagship stores</div>
</div>
<div class="br-search">
  <input placeholder="Search brand or vendor…">
</div>

<div class="br-featured">
  <h3>⭐ Featured brands this week</h3>
  <div class="feat-row">
    <div class="feat-card">
      <div class="fc-logo">A</div>
      <div class="fc-name">Anker Official</div>
      <div class="fc-disc">UP TO 35% OFF</div>
    </div>
    <div class="feat-card" style="background:linear-gradient(135deg,#FF4D4D,#C81212)">
      <div class="fc-logo" style="background:#fff;color:#FF4D4D">H</div>
      <div class="fc-name">Huawei Store</div>
      <div class="fc-disc" style="background:#fff;color:#FF4D4D">NEW LAUNCH</div>
    </div>
    <div class="feat-card" style="background:linear-gradient(135deg,#3b82f6,#1e40af);color:#fff">
      <div class="fc-logo" style="background:#fff;color:#3b82f6">S</div>
      <div class="fc-name">Samsung</div>
      <div class="fc-disc" style="background:#fff;color:#3b82f6">EXCLUSIVE</div>
    </div>
  </div>
</div>

<div class="alphabet">
  <a>#</a><a class="on">A</a><a>B</a><a>C</a><a>D</a><a>E</a>
  <a>F</a><a>G</a><a>H</a><a>I</a><a>J</a><a>K</a><a>L</a>
  <a>M</a><a>N</a><a>O</a><a>P</a><a>Q</a><a>R</a>
  <a>S</a><a>T</a><a>U</a><a>V</a><a>W</a><a>X</a>
  <a>Y</a><a>Z</a>
</div>

<div class="brand-group">
  <h4>A</h4>
  <div class="brand-grid">''' + vendor_cards + '''</div>
</div>
'''
    return body, 'Brands', True


# ─── 17. LOYALTY FULL ───────────────────────────────────────────

def render_loyalty(env):
    body = '''
<style>
  body { background: #F8F4E3; }
  .ly-top { padding: 14px 18px; background: #fff; border-bottom: 1px solid #F2EBD3; }
  .ly-top h1 { margin: 0; font-size: 17px; font-weight: 800; color: #1a1108; }
  /* Hero card */
  .ly-hero { background: linear-gradient(135deg,#FFD340 0%, #F5A800 100%);
       margin: 10px 14px; border-radius: 20px; padding: 22px;
       position: relative; overflow: hidden; color: #412402; }
  .ly-hero::after { content: ""; position: absolute; right: -30px; top: -30px;
       width: 160px; height: 160px; border-radius: 50%;
       background: radial-gradient(circle,#fff 0,transparent 60%); opacity: .25; }
  .ly-hero h2 { margin: 0; font-size: 14px; font-weight: 700; opacity: .8;
       text-transform: uppercase; letter-spacing: .5px; }
  .ly-pts { font-size: 48px; font-weight: 900; margin: 6px 0 2px; line-height: 1; }
  .ly-pts .lbl { font-size: 16px; font-weight: 700; }
  .ly-eq { font-size: 13px; color: #5b3c00; }
  .ly-tier-row { display: flex; align-items: center; gap: 10px; margin-top: 16px; }
  .ly-tier-badge { background: #412402; color: #FFD340; padding: 6px 14px;
       border-radius: 999px; font-size: 12px; font-weight: 800; }
  .ly-progress { flex: 1; }
  .ly-progress-bar { height: 8px; background: rgba(65,36,2,.2); border-radius: 999px;
       overflow: hidden; }
  .ly-progress-bar > div { height: 100%; background: #412402; border-radius: 999px; }
  .ly-progress-text { font-size: 11px; margin-top: 4px; color: #5b3c00; }
  .ly-hero-cta { margin-top: 16px; display: flex; gap: 8px; }
  .ly-hero-cta button { flex: 1; padding: 11px; border: 0; border-radius: 12px;
       font-weight: 800; font-size: 13px; cursor: pointer; }
  .ly-hero-cta .primary { background: #412402; color: #FFD340; }
  .ly-hero-cta .secondary { background: rgba(65,36,2,.15); color: #412402; }
  /* Tiers strip */
  .ly-tiers { display: flex; gap: 6px; padding: 14px;
       overflow-x: auto; scrollbar-width: none; }
  .ly-tiers::-webkit-scrollbar { display: none; }
  .ly-tier { flex: 0 0 130px; background: #fff; border-radius: 14px;
       padding: 14px 12px; text-align: center; position: relative; cursor: pointer;
       border: 2px solid transparent; }
  .ly-tier.current { border-color: #F5C320; }
  .ly-tier .badge-now { position: absolute; top: -8px; left: 50%;
       transform: translateX(-50%); background: #F5C320; color: #412402;
       padding: 2px 8px; border-radius: 999px; font-size: 9px; font-weight: 800;
       letter-spacing: .5px; }
  .ly-tier .ico { font-size: 28px; margin-bottom: 4px; }
  .ly-tier .nm { font-weight: 900; color: #412402; font-size: 13px; }
  .ly-tier .req { font-size: 10px; color: #9c8a5e; margin-top: 2px; }
  /* Sec card */
  .ly-sec { background: #fff; margin: 8px 14px; border-radius: 14px;
       padding: 14px 16px; }
  .ly-sec h3 { margin: 0 0 12px; font-size: 14px; font-weight: 800; color: #412402;
       display: flex; align-items: center; justify-content: space-between; }
  .ly-sec .see { font-size: 11px; color: #5d4d2e; }
  /* Earn ways */
  .earn-row { display: flex; align-items: center; gap: 12px;
       padding: 10px 0; border-bottom: 1px solid #F8F4E3; }
  .earn-row:last-child { border-bottom: 0; }
  .earn-ico { width: 36px; height: 36px; background: #FFF5D0; color: #C99000;
       border-radius: 10px; display: grid; place-items: center; flex-shrink: 0; }
  .earn-body { flex: 1; }
  .earn-title { font-size: 13px; font-weight: 700; color: #1a1108; }
  .earn-meta { font-size: 11px; color: #9c8a5e; }
  .earn-pts { background: #ECFDF5; color: #047857; padding: 4px 8px;
       border-radius: 6px; font-weight: 800; font-size: 11px; }
  /* History */
  .hist-row { display: flex; align-items: center; gap: 10px;
       padding: 8px 0; border-bottom: 1px solid #F8F4E3; font-size: 12.5px; }
  .hist-row:last-child { border-bottom: 0; }
  .hist-row .desc { flex: 1; color: #1a1108; }
  .hist-row .time { font-size: 11px; color: #9c8a5e; }
  .hist-row .pts.earn { color: #047857; font-weight: 800; }
  .hist-row .pts.spent { color: #b91c1c; font-weight: 800; }
  /* Redeem */
  .redeem-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
  .redeem-card { background: #FFFCEF; border: 1px solid #FFE8A0; border-radius: 12px;
       padding: 12px; text-align: center; cursor: pointer; }
  .redeem-card .gift-ico { font-size: 28px; margin-bottom: 4px; }
  .redeem-card .rc-name { font-weight: 800; color: #412402; font-size: 12px; }
  .redeem-card .rc-pts { font-size: 11px; color: #9c8a5e; margin-top: 2px; }
  .redeem-card .rc-btn { margin-top: 8px; padding: 6px 10px; background: #FFD340;
       color: #412402; border: 0; border-radius: 8px; font-weight: 800;
       font-size: 11px; cursor: pointer; width: 100%; }
</style>
<div class="ly-top"><h1>← Loyalty &amp; Rewards</h1></div>

<div class="ly-hero">
  <h2>YOUR POINTS</h2>
  <div class="ly-pts">2,450 <span class="lbl">pts</span></div>
  <div class="ly-eq">= 24.500 KD redeem value</div>
  <div class="ly-tier-row">
    <div class="ly-tier-badge">⭐ SILVER</div>
    <div class="ly-progress">
      <div class="ly-progress-bar"><div style="width:48%"></div></div>
      <div class="ly-progress-text">2,550 pts to GOLD</div>
    </div>
  </div>
  <div class="ly-hero-cta">
    <button class="primary">''' + _ico('gift',14) + ''' Redeem points</button>
    <button class="secondary">Transfer</button>
  </div>
</div>

<!-- Tier strip -->
<div class="ly-tiers">
  <div class="ly-tier"><div class="ico">🥉</div><div class="nm">Bronze</div><div class="req">0 pts</div></div>
  <div class="ly-tier current"><div class="badge-now">YOU</div><div class="ico">🥈</div><div class="nm">Silver</div><div class="req">1,000 pts</div></div>
  <div class="ly-tier"><div class="ico">🥇</div><div class="nm">Gold</div><div class="req">5,000 pts</div></div>
  <div class="ly-tier"><div class="ico">💎</div><div class="nm">Platinum</div><div class="req">15,000 pts</div></div>
</div>

<!-- Tier benefits -->
<div class="ly-sec">
  <h3>Silver tier perks</h3>
  <div style="display:flex;gap:8px;flex-wrap:wrap">
    <span style="background:#FFF5D0;color:#412402;padding:6px 10px;border-radius:8px;font-size:12px;font-weight:700">2× points on weekends</span>
    <span style="background:#FFF5D0;color:#412402;padding:6px 10px;border-radius:8px;font-size:12px;font-weight:700">Free standard delivery</span>
    <span style="background:#FFF5D0;color:#412402;padding:6px 10px;border-radius:8px;font-size:12px;font-weight:700">Early sale access</span>
    <span style="background:#FFF5D0;color:#412402;padding:6px 10px;border-radius:8px;font-size:12px;font-weight:700">Birthday gift</span>
  </div>
</div>

<!-- Ways to earn -->
<div class="ly-sec">
  <h3>Ways to earn more</h3>
  <div class="earn-row">
    <div class="earn-ico">''' + _ico('cart',18) + '''</div>
    <div class="earn-body"><div class="earn-title">Place an order</div><div class="earn-meta">1 KD = 10 points</div></div>
    <span class="earn-pts">+10 / KD</span>
  </div>
  <div class="earn-row">
    <div class="earn-ico">''' + _ico('star',18) + '''</div>
    <div class="earn-body"><div class="earn-title">Write a review</div><div class="earn-meta">Verified purchase</div></div>
    <span class="earn-pts">+50</span>
  </div>
  <div class="earn-row">
    <div class="earn-ico">''' + _ico('user',18) + '''</div>
    <div class="earn-body"><div class="earn-title">Refer a friend</div><div class="earn-meta">Both get 250 pts</div></div>
    <span class="earn-pts">+250</span>
  </div>
  <div class="earn-row">
    <div class="earn-ico">''' + _ico('gift',18) + '''</div>
    <div class="earn-body"><div class="earn-title">Daily check-in</div><div class="earn-meta">Streak: 4 days</div></div>
    <span class="earn-pts">+5</span>
  </div>
</div>

<!-- Redeem options -->
<div class="ly-sec">
  <h3>Redeem your points <span class="see">See all →</span></h3>
  <div class="redeem-grid">
    <div class="redeem-card"><div class="gift-ico">💵</div><div class="rc-name">5 KD off coupon</div><div class="rc-pts">500 pts</div><button class="rc-btn">Redeem</button></div>
    <div class="redeem-card"><div class="gift-ico">🚚</div><div class="rc-name">Free same-day</div><div class="rc-pts">300 pts</div><button class="rc-btn">Redeem</button></div>
    <div class="redeem-card"><div class="gift-ico">🎁</div><div class="rc-name">Mystery box</div><div class="rc-pts">1000 pts</div><button class="rc-btn">Redeem</button></div>
    <div class="redeem-card"><div class="gift-ico">💎</div><div class="rc-name">10% off any</div><div class="rc-pts">800 pts</div><button class="rc-btn">Redeem</button></div>
  </div>
</div>

<!-- History -->
<div class="ly-sec">
  <h3>Points history <span class="see">See all →</span></h3>
  <div class="hist-row"><div><div class="desc">Order #S00532</div><div class="time">Yesterday</div></div><span class="pts earn">+150</span></div>
  <div class="hist-row"><div><div class="desc">Used 150 pts on order #S00532</div><div class="time">Yesterday</div></div><span class="pts spent">−150</span></div>
  <div class="hist-row"><div><div class="desc">Review on HainoTeko Watch</div><div class="time">2 days ago</div></div><span class="pts earn">+50</span></div>
  <div class="hist-row"><div><div class="desc">Birthday gift bonus</div><div class="time">May 14</div></div><span class="pts earn">+500</span></div>
</div>
<div style="height:20px"></div>
'''
    return body, 'Loyalty', True


# ─── 18. WALLET FULL ────────────────────────────────────────────

def render_wallet(env):
    body = '''
<style>
  body { background: #F8F4E3; }
  .w-top { padding: 14px 18px; background: #fff; border-bottom: 1px solid #F2EBD3; }
  .w-top h1 { margin: 0; font-size: 17px; font-weight: 800; color: #1a1108; }
  /* Hero */
  .w-hero { background: linear-gradient(135deg,#412402,#1F1100); color: #FFD340;
       margin: 10px 14px; border-radius: 20px; padding: 22px 20px;
       position: relative; overflow: hidden;
       box-shadow: 0 14px 30px -10px rgba(65,36,2,.5); }
  .w-hero::after { content: ""; position: absolute; right: -40px; bottom: -40px;
       width: 180px; height: 180px; border-radius: 50%;
       background: radial-gradient(circle,#FFD340 0,transparent 60%); opacity: .12; }
  .w-hero h2 { margin: 0; font-size: 12px; font-weight: 700; opacity: .7;
       text-transform: uppercase; letter-spacing: .8px; }
  .w-bal { font-size: 44px; font-weight: 900; margin: 6px 0 4px; line-height: 1; }
  .w-bal .lbl { font-size: 18px; font-weight: 700; opacity: .8; }
  .w-sub { font-size: 12px; opacity: .65; }
  .w-actions { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px;
       margin-top: 18px; }
  .w-action { padding: 10px 6px; background: rgba(255,211,64,.18);
       color: #FFD340; border: 0; border-radius: 12px;
       font-weight: 800; font-size: 11.5px; cursor: pointer;
       display: flex; flex-direction: column; align-items: center; gap: 4px; }
  .w-action svg { color: #FFD340; }
  .w-action.primary { background: #FFD340; color: #412402; }
  .w-action.primary svg { color: #412402; }
  /* Quick stats */
  .w-stats { display: grid; grid-template-columns: 1fr 1fr; gap: 8px;
       padding: 0 14px; }
  .w-stat { background: #fff; padding: 12px; border-radius: 12px; text-align: center; }
  .w-stat .lbl { font-size: 10px; color: #9c8a5e; font-weight: 700;
       text-transform: uppercase; letter-spacing: .4px; }
  .w-stat .val { font-size: 18px; font-weight: 900; color: #412402; margin-top: 4px; }
  .w-stat .delta { font-size: 10px; font-weight: 700; }
  .w-stat .delta.up { color: #047857; }
  .w-stat .delta.down { color: #b91c1c; }
  /* Quick topup */
  .w-topup { background: #fff; margin: 8px 14px; border-radius: 14px; padding: 14px; }
  .w-topup h3 { margin: 0 0 10px; font-size: 13px; font-weight: 800; color: #412402; }
  .w-topup-grid { display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 6px; }
  .topup-pill { padding: 12px 4px; background: #FFFCEF; border: 1.5px solid #F2EBD3;
       border-radius: 10px; text-align: center; cursor: pointer;
       color: #412402; font-weight: 800; font-size: 13px; }
  .topup-pill.popular { border-color: #F5C320; background: #FFF5D0; position: relative; }
  .topup-pill.popular::after { content: "POPULAR"; position: absolute; top: -8px;
       left: 50%; transform: translateX(-50%); background: #F5C320; color: #412402;
       padding: 1px 6px; border-radius: 999px; font-size: 8px; font-weight: 800; }
  /* Sec */
  .w-sec { background: #fff; margin: 8px 14px; border-radius: 14px; padding: 14px 16px; }
  .w-sec h3 { margin: 0 0 12px; font-size: 14px; font-weight: 800; color: #412402;
       display: flex; align-items: center; justify-content: space-between; }
  .w-sec .filter { font-size: 11px; color: #5d4d2e; }
  /* TX */
  .tx-row { display: flex; gap: 10px; align-items: center;
       padding: 10px 0; border-bottom: 1px solid #F8F4E3; }
  .tx-row:last-child { border-bottom: 0; }
  .tx-ico { width: 36px; height: 36px; border-radius: 10px;
       display: grid; place-items: center; flex-shrink: 0; }
  .tx-ico.in { background: #ECFDF5; color: #047857; }
  .tx-ico.out { background: #FFE3E3; color: #b91c1c; }
  .tx-text { flex: 1; min-width: 0; }
  .tx-title { font-size: 13px; font-weight: 700; color: #1a1108; }
  .tx-meta { font-size: 11px; color: #9c8a5e; margin-top: 2px; }
  .tx-amt { font-weight: 900; font-size: 14px; }
  .tx-amt.in { color: #047857; }
  .tx-amt.out { color: #b91c1c; }
  .tx-status { font-size: 9.5px; font-weight: 700; padding: 2px 6px;
       border-radius: 4px; display: inline-block; margin-top: 2px; }
  .tx-status.completed { background: #ECFDF5; color: #047857; }
  .tx-status.pending { background: #FFF5D0; color: #C99000; }
</style>
<div class="w-top"><h1>← My Wallet</h1></div>

<div class="w-hero">
  <h2>AVAILABLE BALANCE</h2>
  <div class="w-bal">12.750 <span class="lbl">KD</span></div>
  <div class="w-sub">Last top-up 3 days ago via KNET</div>
  <div class="w-actions">
    <button class="w-action primary">''' + _ico('wallet',16) + '''Top up</button>
    <button class="w-action">''' + _ico('share',16) + '''Send</button>
    <button class="w-action">''' + _ico('return',16) + '''History</button>
  </div>
</div>

<div class="w-stats">
  <div class="w-stat"><div class="lbl">This month spent</div><div class="val">−45.300</div><div class="delta down">+15% vs last</div></div>
  <div class="w-stat"><div class="lbl">Earned cashback</div><div class="val">+2.150</div><div class="delta up">+8 transactions</div></div>
</div>

<div class="w-topup">
  <h3>Quick top-up</h3>
  <div class="w-topup-grid">
    <div class="topup-pill">5 KD</div>
    <div class="topup-pill">10 KD</div>
    <div class="topup-pill popular">25 KD</div>
    <div class="topup-pill">50 KD</div>
  </div>
</div>

<div class="w-sec">
  <h3>Recent transactions <span class="filter">Filter ▾</span></h3>
  <div class="tx-row">
    <div class="tx-ico out">−</div>
    <div class="tx-text">
      <div class="tx-title">Order #S00532</div>
      <div class="tx-meta">Today · 11:24 AM</div>
      <span class="tx-status completed">Completed</span>
    </div>
    <div class="tx-amt out">−5.500</div>
  </div>
  <div class="tx-row">
    <div class="tx-ico in">+</div>
    <div class="tx-text">
      <div class="tx-title">Top-up via KNET</div>
      <div class="tx-meta">3 days ago · ****1234</div>
      <span class="tx-status completed">Completed</span>
    </div>
    <div class="tx-amt in">+25.000</div>
  </div>
  <div class="tx-row">
    <div class="tx-ico in">+</div>
    <div class="tx-text">
      <div class="tx-title">Cashback — order #S00498</div>
      <div class="tx-meta">5 days ago</div>
      <span class="tx-status completed">Completed</span>
    </div>
    <div class="tx-amt in">+0.250</div>
  </div>
  <div class="tx-row">
    <div class="tx-ico out">−</div>
    <div class="tx-text">
      <div class="tx-title">Order #S00498</div>
      <div class="tx-meta">May 25 · 4:32 PM</div>
      <span class="tx-status completed">Completed</span>
    </div>
    <div class="tx-amt out">−8.900</div>
  </div>
  <div class="tx-row">
    <div class="tx-ico in">+</div>
    <div class="tx-text">
      <div class="tx-title">Refund — order #S00489</div>
      <div class="tx-meta">May 20</div>
      <span class="tx-status pending">Pending</span>
    </div>
    <div class="tx-amt in">+12.500</div>
  </div>
</div>
<div style="height:20px"></div>
'''
    return body, 'Wallet', True


# ─── 19. COUPONS ────────────────────────────────────────────────

def render_coupons(env):
    body = '''
<style>
  body { background: #F8F4E3; }
  .cp-top { padding: 14px 18px; background: #fff; border-bottom: 1px solid #F2EBD3; }
  .cp-top h1 { margin: 0; font-size: 17px; font-weight: 800; color: #1a1108; }
  .cp-tabs { display: flex; background: #fff; border-bottom: 1px solid #F2EBD3; }
  .cp-tab { flex: 1; padding: 14px; font-size: 13px; font-weight: 700; color: #9c8a5e;
       text-align: center; cursor: pointer; border-bottom: 2px solid transparent; }
  .cp-tab.on { color: #412402; border-bottom-color: #F5C320; }
  .cp-list { padding: 12px; }
  .coupon { background: #fff; border-radius: 14px; overflow: hidden;
       margin-bottom: 10px; display: flex; box-shadow: 0 1px 4px rgba(0,0,0,.05);
       position: relative; }
  .coupon::before, .coupon::after { content: ""; position: absolute;
       width: 14px; height: 14px; background: #F8F4E3; border-radius: 50%; top: 50%;
       transform: translateY(-50%); z-index: 2; }
  .coupon::before { left: -7px; }
  .coupon::after { right: -7px; }
  .cp-left { width: 90px; background: linear-gradient(135deg,#FFD340,#F5A800);
       color: #412402; display: flex; flex-direction: column; justify-content: center;
       align-items: center; padding: 12px 6px; position: relative; }
  .cp-left::after { content: ""; position: absolute; right: -1px; top: 8px; bottom: 8px;
       width: 0; border-right: 2px dashed #fff; opacity: .8; }
  .cp-left.brown { background: linear-gradient(135deg,#412402,#1F1100); color: #FFD340; }
  .cp-left.red { background: linear-gradient(135deg,#FF4D4D,#C81212); color: #fff; }
  .cp-amt { font-size: 26px; font-weight: 900; line-height: 1; }
  .cp-amt-sub { font-size: 10px; font-weight: 700; opacity: .85; }
  .cp-right { flex: 1; padding: 12px 16px;
       display: flex; flex-direction: column; justify-content: center; }
  .cp-name { font-weight: 800; color: #1a1108; font-size: 13px; }
  .cp-min { font-size: 11px; color: #9c8a5e; margin-top: 2px; }
  .cp-exp { font-size: 10.5px; color: #b91c1c; font-weight: 700; margin-top: 4px;
       display: inline-flex; align-items: center; gap: 4px; }
  .cp-code { background: #F2EBD3; color: #412402; padding: 4px 8px;
       border-radius: 6px; font-family: monospace; font-weight: 800;
       font-size: 11px; letter-spacing: 1px; margin-top: 4px;
       display: inline-block; }
  .cp-cta { position: absolute; right: 12px; bottom: 12px; background: #412402;
       color: #FFD340; padding: 6px 12px; border-radius: 8px; font-weight: 800;
       font-size: 11px; border: 0; cursor: pointer; }
  .cp-cta.used { background: #F2EBD3; color: #9c8a5e; }
</style>
<div class="cp-top"><h1>← My Coupons</h1></div>
<div class="cp-tabs">
  <div class="cp-tab on">Available (5)</div>
  <div class="cp-tab">Used (12)</div>
  <div class="cp-tab">Expired (3)</div>
</div>
<div class="cp-list">

  <div class="coupon">
    <div class="cp-left"><div class="cp-amt">15%</div><div class="cp-amt-sub">OFF</div></div>
    <div class="cp-right">
      <div class="cp-name">15% off any order</div>
      <div class="cp-min">Min spend KD 20 · Max discount KD 5</div>
      <div class="cp-code">SAVE15</div>
      <div class="cp-exp">⏰ Expires in 2 days</div>
    </div>
    <button class="cp-cta">Use</button>
  </div>

  <div class="coupon">
    <div class="cp-left brown"><div class="cp-amt">5 KD</div><div class="cp-amt-sub">OFF</div></div>
    <div class="cp-right">
      <div class="cp-name">5 KD off new arrivals</div>
      <div class="cp-min">Valid on selected categories</div>
      <div class="cp-code">NEW5</div>
      <div class="cp-exp" style="color:#C99000">⏰ Expires Aug 15</div>
    </div>
    <button class="cp-cta">Use</button>
  </div>

  <div class="coupon">
    <div class="cp-left red"><div class="cp-amt">⚡</div><div class="cp-amt-sub">FREE</div></div>
    <div class="cp-right">
      <div class="cp-name">Free same-day delivery</div>
      <div class="cp-min">Order before 2 PM · Kuwait only</div>
      <div class="cp-code">SAMEDAY</div>
      <div class="cp-exp" style="color:#C99000">⏰ Expires May 31</div>
    </div>
    <button class="cp-cta">Use</button>
  </div>

  <div class="coupon">
    <div class="cp-left"><div class="cp-amt">10%</div><div class="cp-amt-sub">OFF</div></div>
    <div class="cp-right">
      <div class="cp-name">Loyalty member exclusive</div>
      <div class="cp-min">Silver tier and above</div>
      <div class="cp-code">LOYAL10</div>
      <div class="cp-exp" style="color:#9c8a5e">No expiration</div>
    </div>
    <button class="cp-cta">Use</button>
  </div>

  <div class="coupon">
    <div class="cp-left brown"><div class="cp-amt">2 KD</div><div class="cp-amt-sub">CASHBACK</div></div>
    <div class="cp-right">
      <div class="cp-name">2 KD cashback on KNET</div>
      <div class="cp-min">Pay with KNET · Min 10 KD</div>
      <div class="cp-code">KNET2</div>
      <div class="cp-exp" style="color:#C99000">⏰ 7 days left</div>
    </div>
    <button class="cp-cta">Use</button>
  </div>

</div>
'''
    return body, 'Coupons', True


# ─── 20. TRY-ON + SMART FIT ─────────────────────────────────────

def render_tryon(env):
    body = '''
<style>
  body { background: #F8F4E3; }
  .to-top { padding: 14px 18px; background: linear-gradient(135deg,#412402,#1F1100);
       color: #FFD340; }
  .to-top h1 { margin: 0; font-size: 18px; font-weight: 800;
       display: flex; align-items: center; gap: 6px; }
  .to-top .sub { font-size: 12px; opacity: .7; margin-top: 4px; }
  /* Result preview */
  .to-canvas { background: #fff; margin: 10px 14px; border-radius: 16px;
       overflow: hidden; box-shadow: 0 4px 14px rgba(0,0,0,.06); }
  .to-canvas-head { padding: 12px 16px; display: flex; align-items: center;
       justify-content: space-between; border-bottom: 1px solid #F2EBD3; }
  .to-canvas-head h3 { margin: 0; font-size: 13px; font-weight: 800; color: #412402; }
  .to-canvas-head .gen { font-size: 11px; color: #5d4d2e; }
  .to-image { aspect-ratio: 3/4; background:
       repeating-linear-gradient(45deg, #FFF5D0 0 12px, #FFE8A0 12px 24px);
       display: grid; place-items: center; position: relative; }
  .to-image::after { content: "✨"; font-size: 60px; opacity: .7; }
  .to-image .ribbon { position: absolute; top: 12px; left: 12px;
       background: linear-gradient(135deg,#FFD340,#F5C320); color: #412402;
       padding: 4px 10px; border-radius: 999px; font-size: 11px; font-weight: 800;
       display: flex; align-items: center; gap: 4px; }
  /* Color picker */
  .to-colors { padding: 12px 16px; border-bottom: 1px solid #F2EBD3; }
  .to-colors h4 { margin: 0 0 8px; font-size: 12px; color: #5d4d2e; font-weight: 700; }
  .to-color-row { display: flex; gap: 8px; }
  .to-color { width: 36px; height: 36px; border-radius: 50%; cursor: pointer;
       border: 2px solid transparent; }
  .to-color.on { border-color: #412402; box-shadow: 0 0 0 3px rgba(245,195,32,.3); }
  /* Actions under canvas */
  .to-canvas-actions { padding: 10px 14px; display: flex; gap: 8px;
       border-top: 1px solid #F2EBD3; }
  .to-canvas-actions button { flex: 1; padding: 10px; background: #F2EBD3;
       color: #412402; border: 0; border-radius: 10px; font-weight: 800;
       font-size: 12px; cursor: pointer;
       display: inline-flex; justify-content: center; align-items: center; gap: 4px; }
  .to-canvas-actions button.primary { background: #FFD340; }
  /* Upload card */
  .upload-card { background: #fff; margin: 10px 14px; border-radius: 14px;
       padding: 20px 14px; border: 2px dashed #FFE8A0; text-align: center; }
  .upload-card .ico { width: 56px; height: 56px; background: #FFF5D0;
       color: #C99000; border-radius: 18px; display: grid; place-items: center;
       margin: 0 auto 10px; }
  .upload-card h3 { margin: 0 0 4px; font-size: 14px; color: #412402; font-weight: 800; }
  .upload-card p { margin: 0; font-size: 12px; color: #9c8a5e; line-height: 1.5; }
  .upload-btns { display: flex; gap: 8px; margin-top: 14px; }
  .upload-btns button { flex: 1; padding: 11px; border: 0; border-radius: 10px;
       font-weight: 800; font-size: 12px; cursor: pointer;
       display: inline-flex; justify-content: center; align-items: center; gap: 4px; }
  .upload-btns .camera { background: #412402; color: #FFD340; }
  .upload-btns .gallery { background: #F2EBD3; color: #412402; }
  /* Smart Fit */
  .sf-card { background: #fff; margin: 10px 14px; border-radius: 14px;
       padding: 16px; }
  .sf-card h3 { margin: 0 0 4px; font-size: 14px; font-weight: 800; color: #412402;
       display: flex; align-items: center; gap: 6px; }
  .sf-card .lead { margin: 0 0 14px; font-size: 12.5px; color: #5d4d2e; line-height: 1.5; }
  .sf-row { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 8px; }
  .sf-field label { display: block; font-size: 11px; color: #9c8a5e;
       font-weight: 700; margin-bottom: 4px; text-transform: uppercase; letter-spacing: .4px; }
  .sf-field .ip { display: flex; gap: 4px; }
  .sf-field input { width: 100%; height: 42px; padding: 0 12px;
       border: 1.5px solid #F2EBD3; border-radius: 10px; background: #FFFCEF;
       font-size: 14px; font-weight: 700; color: #412402; outline: 0; }
  .sf-field .unit { width: 50px; height: 42px; background: #F2EBD3;
       border-radius: 10px; display: grid; place-items: center;
       font-weight: 800; color: #412402; font-size: 11px; }
  /* Recommendation */
  .sf-result { background: linear-gradient(135deg,#FFD340,#F5C320);
       padding: 14px 16px; border-radius: 12px; margin-top: 12px;
       color: #412402; }
  .sf-result-head { display: flex; align-items: center; gap: 6px;
       font-weight: 800; font-size: 13px; }
  .sf-result-size { font-size: 36px; font-weight: 900; margin: 6px 0;
       line-height: 1; }
  .sf-result-meta { font-size: 11.5px; opacity: .85; }
  .sf-alts { display: flex; gap: 6px; margin-top: 8px; }
  .sf-alt { background: rgba(65,36,2,.15); padding: 4px 10px; border-radius: 999px;
       font-size: 11px; font-weight: 700; color: #412402; }
  .sf-fit { width: 100%; padding: 12px; background: #412402; color: #FFD340;
       border: 0; border-radius: 12px; font-weight: 800; font-size: 13px;
       margin-top: 12px; cursor: pointer; }
</style>
<div class="to-top">
  <h1>✨ Virtual Try-On</h1>
  <div class="sub">See how it looks on you — powered by AI</div>
</div>

<div class="to-canvas">
  <div class="to-canvas-head">
    <h3>Preview</h3>
    <span class="gen">Generated in 4.2s</span>
  </div>
  <div class="to-image">
    <div class="ribbon">''' + _ico('star',12) + ''' AI Generated</div>
  </div>
  <div class="to-colors">
    <h4>Try different colors</h4>
    <div class="to-color-row">
      <div class="to-color on" style="background:#412402"></div>
      <div class="to-color" style="background:#FF4D4D"></div>
      <div class="to-color" style="background:#F5C320"></div>
      <div class="to-color" style="background:#3b82f6"></div>
      <div class="to-color" style="background:#fff;border:2px solid #ccc"></div>
    </div>
  </div>
  <div class="to-canvas-actions">
    <button>''' + _ico('share',14) + ''' Share</button>
    <button>''' + _ico('user',14) + ''' Ask reviewer</button>
    <button class="primary">''' + _ico('cart',14) + ''' Add to cart</button>
  </div>
</div>

<div class="upload-card">
  <div class="ico">''' + _ico('camera',26) + '''</div>
  <h3>Want to try with your photo?</h3>
  <p>Upload a clear front-facing photo for a personalised preview</p>
  <div class="upload-btns">
    <button class="camera">''' + _ico('camera',14) + ''' Camera</button>
    <button class="gallery">''' + _ico('grid',14) + ''' Gallery</button>
  </div>
</div>

<div class="sf-card">
  <h3>''' + _ico('ruler',16) + ''' Smart Fit</h3>
  <p class="lead">Enter a few measurements and we'll recommend your exact size — no more guessing.</p>

  <div class="sf-row">
    <div class="sf-field"><label>Height</label><div class="ip"><input value="175"><div class="unit">cm</div></div></div>
    <div class="sf-field"><label>Weight</label><div class="ip"><input value="72"><div class="unit">kg</div></div></div>
    <div class="sf-field"><label>Chest</label><div class="ip"><input value="98"><div class="unit">cm</div></div></div>
    <div class="sf-field"><label>Waist</label><div class="ip"><input value="82"><div class="unit">cm</div></div></div>
  </div>

  <div class="sf-result">
    <div class="sf-result-head">''' + _ico('check',14) + ''' Recommended size</div>
    <div class="sf-result-size">M</div>
    <div class="sf-result-meta">94% match · True to size · No stretch</div>
    <div class="sf-alts">
      <span class="sf-alt">L (relaxed fit)</span>
      <span class="sf-alt">S (tight fit)</span>
    </div>
  </div>
  <button class="sf-fit">Add size M to cart</button>
</div>
<div style="height:30px"></div>
'''
    return body, 'Try-On', True


# ─── Registry ──────────────────────────────────────────────────────

RENDERERS = {
    'splash':        render_splash,
    'home':          render_home,
    'flash':         render_flash,
    'product':       render_product,
    'vendor':        render_vendor,
    'cart':          render_cart,
    'checkout':      render_checkout,
    'account':       render_account,
    'beena':         render_beena,
    'category':      render_category,
    # New screens
    'search':        render_search,
    'order':         render_order,
    'wishlist':      render_wishlist,
    'notifications': render_notifications,
    'auth':          render_auth,
    'brands':        render_brands,
    'loyalty':       render_loyalty,
    'wallet':        render_wallet,
    'coupons':       render_coupons,
    'tryon':         render_tryon,
}
