/** @odoo-module **/
(function () {
'use strict';

/* ═══ 10 LIGHT PALETTES ══════════════════════════════════════════════════ */
var PALETTES = [
    { bg:'#f0f4ff', accent:'#4f46e5', rgb:'79,70,229',   price:'#3730a3', text:'#1e1b4b', sub:'#4f46e5', card:'rgba(79,70,229,.07)',  brd:'rgba(79,70,229,.18)'  },
    { bg:'#f0fdf9', accent:'#059669', rgb:'5,150,105',   price:'#065f46', text:'#064e3b', sub:'#059669', card:'rgba(5,150,105,.07)',   brd:'rgba(5,150,105,.18)'  },
    { bg:'#fff7ed', accent:'#ea580c', rgb:'234,88,12',   price:'#9a3412', text:'#431407', sub:'#ea580c', card:'rgba(234,88,12,.07)',   brd:'rgba(234,88,12,.18)'  },
    { bg:'#fdf4ff', accent:'#9333ea', rgb:'147,51,234',  price:'#6b21a8', text:'#3b0764', sub:'#9333ea', card:'rgba(147,51,234,.07)',  brd:'rgba(147,51,234,.18)' },
    { bg:'#eff6ff', accent:'#2563eb', rgb:'37,99,235',   price:'#1e40af', text:'#1e3a8a', sub:'#2563eb', card:'rgba(37,99,235,.07)',   brd:'rgba(37,99,235,.18)'  },
    { bg:'#fff1f2', accent:'#e11d48', rgb:'225,29,72',   price:'#9f1239', text:'#4c0519', sub:'#e11d48', card:'rgba(225,29,72,.07)',   brd:'rgba(225,29,72,.18)'  },
    { bg:'#f0fdfa', accent:'#0d9488', rgb:'13,148,136',  price:'#115e59', text:'#042f2e', sub:'#0d9488', card:'rgba(13,148,136,.07)',  brd:'rgba(13,148,136,.18)' },
    { bg:'#fefce8', accent:'#ca8a04', rgb:'202,138,4',   price:'#92400e', text:'#451a03', sub:'#ca8a04', card:'rgba(202,138,4,.07)',   brd:'rgba(202,138,4,.18)'  },
    { bg:'#fdf2f8', accent:'#db2777', rgb:'219,39,119',  price:'#9d174d', text:'#500724', sub:'#db2777', card:'rgba(219,39,119,.07)',  brd:'rgba(219,39,119,.18)' },
    { bg:'#ecfeff', accent:'#0891b2', rgb:'8,145,178',   price:'#164e63', text:'#083344', sub:'#0891b2', card:'rgba(8,145,178,.07)',   brd:'rgba(8,145,178,.18)'  },
];

var _pal    = Math.floor(Math.random() * PALETTES.length);
var _layout = Math.floor(Math.random() * 4);
function P() { return PALETTES[_pal]; }

/* ═══ HELPERS ════════════════════════════════════════════════════════════ */
function detectLang() {
    var h = (document.documentElement.lang || '').toLowerCase();
    return (h.startsWith('ar') || location.pathname.indexOf('/ar') === 0) ? 'ar' : 'en';
}
function esc(s) {
    return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
var IMG_ERR = "this.parentElement.style.background='rgba(0,0,0,.05)'";

/* ═══ TRANSLATIONS ═══════════════════════════════════════════════════════ */
var T = {
    ar: {
        badge:     'عروض القسم',
        cta:       'عرض الكل',
        handpick:  'منتجات مختارة بعناية لك',
        products:  'منتج متاح',
        noProducts:'لا توجد منتجات',
        topPick:   '★ الأفضل',
        arr:       '←',
    },
    en: {
        badge:     'Selected Deals',
        cta:       'View All',
        handpick:  'Hand-picked for you',
        products:  'products',
        noProducts:'No products found',
        topPick:   '★ TOP PICK',
        arr:       '→',
    }
};

/* ═══ BASE CSS ═══════════════════════════════════════════════════════════ */
function baseCSS(p, isRtl) {
    var d   = isRtl ? 'rtl' : 'ltr';
    var c   = '';
    c += '@import url("https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700;900&family=Inter:wght@400;600;700;900&display=swap");';
    c += ':host{display:block;font-family:' + (isRtl ? '"Tajawal"' : '"Inter"') + ',"Segoe UI",sans-serif;}';
    c += '*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}';
    c += '.dsp{width:100%;direction:' + d + ';padding:0 3px;}';
    c += '.outer{background:' + p.bg + ';border-radius:16px;overflow:hidden;';
    c += 'box-shadow:0 2px 20px rgba(0,0,0,.09);border:1px solid ' + p.brd + ';position:relative;}';

    /* badge */
    c += '.badge{display:inline-flex;align-items:center;gap:5px;background:' + p.card + ';';
    c += 'border:1px solid ' + p.brd + ';color:' + p.accent + ';padding:3px 10px;border-radius:20px;';
    c += 'font-size:9.5px;font-weight:700;letter-spacing:.4px;text-transform:uppercase;white-space:nowrap;}';
    c += '.dot{width:6px;height:6px;border-radius:50%;background:' + p.accent + ';flex-shrink:0;animation:pulse 1.8s infinite;}';
    c += '@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.3;transform:scale(.6)}}';

    /* cta button */
    c += '.cta{display:inline-flex;align-items:center;gap:5px;background:' + p.accent + ';color:#fff;';
    c += 'border:none;padding:7px 15px;border-radius:20px;font-size:11px;font-weight:700;';
    c += 'cursor:pointer;text-decoration:none;font-family:inherit;white-space:nowrap;flex-shrink:0;';
    c += 'transition:opacity .15s,transform .15s;}';
    c += '.cta:hover{opacity:.85;transform:scale(1.03);}';

    /* product card */
    c += '.pc{background:' + p.card + ';border:1px solid ' + p.brd + ';border-radius:12px;overflow:hidden;';
    c += 'text-decoration:none;display:flex;flex-direction:column;flex-shrink:0;';
    c += 'transition:transform .2s,box-shadow .2s;}';
    c += '.pc:hover{transform:translateY(-3px);box-shadow:0 6px 18px rgba(' + p.rgb + ',.18);}';
    c += '.pi{overflow:hidden;background:rgba(' + p.rgb + ',.05);flex-shrink:0;}';
    c += '.pi img{width:100%;height:100%;object-fit:cover;display:block;transition:transform .3s;}';
    c += '.pc:hover .pi img{transform:scale(1.05);}';
    c += '.pinfo{padding:7px 9px 9px;display:flex;flex-direction:column;flex-grow:1;}';

    /* product name — exactly 2 lines */
    c += '.pn{font-size:10.5px;color:' + p.text + ';line-height:1.35;height:28px;';
    c += 'overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;';
    c += 'margin-bottom:5px;' + (isRtl ? 'text-align:right;' : '') + '}';
    c += '.pp{font-size:12px;font-weight:800;color:' + p.price + ';' + (isRtl ? 'text-align:right;' : '') + '}';

    /* hero card */
    c += '.hpc{border:2px solid ' + p.accent + ';background:rgba(' + p.rgb + ',.1);}';
    c += '.hpc:hover{box-shadow:0 8px 24px rgba(' + p.rgb + ',.22);}';

    /* top-pick badge */
    c += '.tpick{position:absolute;top:7px;' + (isRtl?'right':'left') + ':7px;';
    c += 'background:' + p.accent + ';color:#fff;padding:2px 7px;border-radius:20px;';
    c += 'font-size:8px;font-weight:700;white-space:nowrap;}';

    /* skeleton */
    c += '.sk{background:linear-gradient(90deg,rgba(' + p.rgb + ',.06),rgba(' + p.rgb + ',.15),rgba(' + p.rgb + ',.06));';
    c += 'background-size:200%;animation:sk 1.5s infinite;border-radius:6px;}';
    c += '@keyframes sk{0%{background-position:200% 0}100%{background-position:-200% 0}}';

    return c;
}

/* ═══ LAYOUT CSS ═════════════════════════════════════════════════════════ */
function layoutCSS(p, isRtl, layout) {
    var bdr = isRtl ? 'left' : 'right';
    var c = '';
    var scrollCSS = 'display:flex;gap:9px;overflow-x:auto;padding-bottom:4px;'
        + 'scrollbar-width:thin;scrollbar-color:' + p.brd + ' transparent;';
    var scrollBar = '.row::-webkit-scrollbar{height:3px;}'
        + '.row::-webkit-scrollbar-thumb{background:' + p.brd + ';border-radius:2px;}';

    if (layout === 0) {
        /* A: header row + full-width products row */
        c += '.hdr{display:flex;align-items:center;gap:10px;padding:11px 14px;border-bottom:1px solid ' + p.brd + ';flex-wrap:wrap;}';
        c += '.dname{font-size:14px;font-weight:900;color:' + p.text + ';flex:1;min-width:80px;}';
        c += '.row{' + scrollCSS + 'padding:10px 14px;}' + scrollBar;
        c += '.pc{min-width:104px;max-width:104px;}.hpc{min-width:118px;max-width:118px;}';
        c += '.pi{height:108px;width:100%;}';
        c += '@media(max-width:580px){.pc{min-width:90px;max-width:90px;}.hpc{min-width:104px;max-width:104px;}.pi{height:95px;}}';
    }
    if (layout === 1) {
        /* B: hero left full-height + header + row */
        c += '.wrap{display:flex;min-height:195px;}';
        c += '.hleft{position:relative;min-width:148px;max-width:148px;flex-shrink:0;overflow:hidden;border-' + bdr + ':1px solid ' + p.brd + ';}';
        c += '.hleft img{width:100%;height:100%;object-fit:cover;display:block;}';
        c += '.hleft-ov{position:absolute;inset:0;background:linear-gradient(transparent 35%,rgba(0,0,0,.7));}';
        c += '.hleft-info{position:absolute;bottom:0;left:0;right:0;padding:10px 12px;}';
        c += '.hleft-name{font-size:10.5px;font-weight:700;color:#fff;line-height:1.3;height:28px;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;margin-bottom:3px;}';
        c += '.hleft-price{font-size:13px;font-weight:900;color:' + p.accent + ';}';
        c += '.right{flex:1;display:flex;flex-direction:column;overflow:hidden;}';
        c += '.hdr{display:flex;align-items:center;gap:10px;padding:10px 13px;border-bottom:1px solid ' + p.brd + ';flex-wrap:wrap;}';
        c += '.dname{font-size:13px;font-weight:900;color:' + p.text + ';flex:1;min-width:60px;}';
        c += '.row{' + scrollCSS + 'padding:9px 12px;flex:1;align-items:stretch;}' + scrollBar;
        c += '.pc{min-width:90px;max-width:90px;}.pi{height:92px;width:100%;}';
        c += '@media(max-width:580px){.wrap{flex-direction:column;}.hleft{min-width:100%;max-width:100%;height:170px;border-right:none;border-left:none;border-bottom:1px solid ' + p.brd + ';}}';
    }
    if (layout === 2) {
        /* C: sidebar + hero + products all in one row */
        c += '.wrap{display:flex;align-items:stretch;min-height:195px;}';
        c += '.side{min-width:140px;max-width:140px;padding:15px 13px;flex-shrink:0;border-' + bdr + ':1px solid ' + p.brd + ';display:flex;flex-direction:column;justify-content:space-between;}';
        c += '.dname{font-size:14px;font-weight:900;color:' + p.text + ';margin:7px 0 3px;}';
        c += '.dsub{font-size:9.5px;color:' + p.sub + ';margin-bottom:8px;line-height:1.4;}';
        c += '.dcount{font-size:22px;font-weight:900;color:' + p.accent + ';line-height:1;}';
        c += '.dcl{font-size:9px;color:' + p.sub + ';margin-top:1px;margin-bottom:10px;}';
        c += '.row{' + scrollCSS + 'padding:9px 11px;flex:1;align-items:stretch;}' + scrollBar;
        c += '.pc{min-width:86px;max-width:86px;}.hpc{min-width:115px;max-width:115px;}';
        c += '.pi{height:96px;width:100%;}';
        c += '@media(max-width:580px){.wrap{flex-direction:column;}.side{min-width:100%;max-width:100%;flex-direction:row;flex-wrap:wrap;align-items:center;gap:8px;padding:11px 13px;border-right:none;border-left:none;border-bottom:1px solid ' + p.brd + ';}.dcount,.dcl{display:none;}}';
    }
    if (layout === 3) {
        /* D: info block + TOP PICK hero + products — one row */
        c += '.wrap{display:flex;align-items:stretch;min-height:195px;}';
        c += '.iblk{min-width:128px;max-width:128px;flex-shrink:0;padding:13px 12px;background:rgba(' + p.rgb + ',.04);border-' + bdr + ':1px solid ' + p.brd + ';display:flex;flex-direction:column;justify-content:space-between;}';
        c += '.dname{font-size:13px;font-weight:900;color:' + p.text + ';margin:6px 0 3px;}';
        c += '.dsub{font-size:9.5px;color:' + p.sub + ';line-height:1.4;}';
        c += '.row{' + scrollCSS + 'padding:9px 11px;flex:1;align-items:stretch;}' + scrollBar;
        c += '.pc{min-width:86px;max-width:86px;}.hpc{min-width:110px;max-width:110px;}';
        c += '.pi{height:96px;width:100%;}';
        c += '.hero-rel{position:relative;flex-shrink:0;}';
        c += '@media(max-width:580px){.wrap{flex-direction:column;}.iblk{min-width:100%;max-width:100%;flex-direction:row;flex-wrap:wrap;align-items:center;gap:8px;padding:11px 13px;border-right:none;border-left:none;border-bottom:1px solid ' + p.brd + ';}}';
    }
    return c;
}

/* ═══ CARD BUILDERS ══════════════════════════════════════════════════════ */
function card(pr, hero) {
    var cls = hero ? 'pc hpc' : 'pc';
    return '<a href="/shop/' + pr.id + '" class="' + cls + '">'
        + '<div class="pi"><img src="/web/image/product.template/' + pr.id + '/image_256" alt="" loading="lazy" onerror="' + IMG_ERR + '"></div>'
        + '<div class="pinfo">'
        + '<div class="pn">' + esc(pr.name) + '</div>'
        + '<span class="pp">' + pr.price.toFixed(3) + ' ' + esc(pr.cur) + '</span>'
        + '</div></a>';
}

function skCard(w, h) {
    return '<div style="min-width:' + w + 'px;max-width:' + w + 'px;border-radius:12px;overflow:hidden;background:rgba(0,0,0,.04);flex-shrink:0">'
        + '<div class="sk" style="height:' + h + 'px;width:100%"></div>'
        + '<div style="padding:7px 9px">'
        + '<div class="sk" style="height:6px;width:82%;margin-bottom:4px"></div>'
        + '<div class="sk" style="height:6px;width:58%;margin-bottom:5px"></div>'
        + '<div class="sk" style="height:9px;width:42%"></div>'
        + '</div></div>';
}

/* ═══ RENDERERS ══════════════════════════════════════════════════════════ */
function renderA(shadow, p, isRtl, data, cfg) {
    var ar   = isRtl;
    var t    = T[ar ? 'ar' : 'en'];
    var name = ar ? (data.categ_name_ar || data.categ_name_en) : (data.categ_name_en || data.categ_name_ar);
    var shop = '/shop?category=' + data.categ_id;
    var rows = data.rows || [];
    var cards = rows.map(function(pr, i) { return card(pr, i === 0); }).join('');
    shadow.innerHTML = '<style>' + baseCSS(p, ar) + layoutCSS(p, ar, 0) + '</style>'
        + '<div class="dsp"><div class="outer">'
        + '<div class="hdr">'
        + '<div class="badge"><span class="dot"></span>' + esc(cfg.badge || t.badge) + '</div>'
        + '<span class="dname">' + esc(name) + '</span>'
        + '<a href="' + shop + '" class="cta">' + esc(cfg.cta || t.cta) + ' ' + t.arr + '</a>'
        + '</div>'
        + '<div class="row">' + cards + '</div>'
        + '</div></div>';
}

function renderB(shadow, p, isRtl, data, cfg) {
    var ar   = isRtl;
    var t    = T[ar ? 'ar' : 'en'];
    var name = ar ? (data.categ_name_ar || data.categ_name_en) : (data.categ_name_en || data.categ_name_ar);
    var shop = '/shop?category=' + data.categ_id;
    var rows = data.rows || [];
    var hero = rows[0];
    var rest = rows.slice(1);
    var heroImg = hero ? '/web/image/product.template/' + hero.id + '/image_512' : '';
    var imgErr  = "this.style.opacity='0'";
    shadow.innerHTML = '<style>' + baseCSS(p, ar) + layoutCSS(p, ar, 1) + '</style>'
        + '<div class="dsp"><div class="outer"><div class="wrap">'
        + '<div class="hleft">'
        + (hero ? '<img src="' + heroImg + '" alt="" onerror="' + imgErr + '">' : '')
        + '<div class="hleft-ov"></div>'
        + '<div class="hleft-info">'
        + (hero ? '<div class="hleft-name">' + esc(hero.name) + '</div>'
               + '<div class="hleft-price">' + hero.price.toFixed(3) + ' ' + esc(hero.cur) + '</div>' : '')
        + '</div></div>'
        + '<div class="right">'
        + '<div class="hdr">'
        + '<div class="badge"><span class="dot"></span>' + esc(cfg.badge || t.badge) + '</div>'
        + '<span class="dname">' + esc(name) + '</span>'
        + '<a href="' + shop + '" class="cta">' + esc(cfg.cta || t.cta) + ' ' + t.arr + '</a>'
        + '</div>'
        + '<div class="row">' + rest.map(function(pr) { return card(pr, false); }).join('') + '</div>'
        + '</div>'
        + '</div></div></div>';
}

function renderC(shadow, p, isRtl, data, cfg) {
    var ar   = isRtl;
    var t    = T[ar ? 'ar' : 'en'];
    var name = ar ? (data.categ_name_ar || data.categ_name_en) : (data.categ_name_en || data.categ_name_ar);
    var shop = '/shop?category=' + data.categ_id;
    var rows = data.rows || [];
    var cards = rows.map(function(pr, i) { return card(pr, i === 0); }).join('');
    shadow.innerHTML = '<style>' + baseCSS(p, ar) + layoutCSS(p, ar, 2) + '</style>'
        + '<div class="dsp"><div class="outer"><div class="wrap">'
        + '<div class="side">'
        + '<div>'
        + '<div class="badge"><span class="dot"></span>' + esc(cfg.badge || t.badge) + '</div>'
        + '<div class="dname">' + esc(name) + '</div>'
        + '<div class="dsub">' + t.handpick + '</div>'
        + '<div class="dcount">' + rows.length + '</div>'
        + '<div class="dcl">' + t.products + '</div>'
        + '</div>'
        + '<a href="' + shop + '" class="cta">' + esc(cfg.cta || t.cta) + ' ' + t.arr + '</a>'
        + '</div>'
        + '<div class="row">' + cards + '</div>'
        + '</div></div></div>';
}

function renderD(shadow, p, isRtl, data, cfg) {
    var ar   = isRtl;
    var t    = T[ar ? 'ar' : 'en'];
    var name = ar ? (data.categ_name_ar || data.categ_name_en) : (data.categ_name_en || data.categ_name_ar);
    var shop = '/shop?category=' + data.categ_id;
    var rows = data.rows || [];
    var hero = rows[0];
    var rest = rows.slice(1);
    var heroHTML = '';
    if (hero) {
        heroHTML = '<div class="hero-rel">'
            + '<a href="/shop/' + hero.id + '" class="pc hpc" style="min-width:110px;max-width:110px">'
            + '<div class="pi" style="height:96px;width:110px"><img src="/web/image/product.template/' + hero.id + '/image_256" alt="" loading="lazy" onerror="' + IMG_ERR + '"></div>'
            + '<div class="pinfo"><div class="pn">' + esc(hero.name) + '</div>'
            + '<span class="pp">' + hero.price.toFixed(3) + ' ' + esc(hero.cur) + '</span></div></a>'
            + '<div class="tpick">' + t.topPick + '</div>'
            + '</div>';
    }
    shadow.innerHTML = '<style>' + baseCSS(p, ar) + layoutCSS(p, ar, 3) + '</style>'
        + '<div class="dsp"><div class="outer"><div class="wrap">'
        + '<div class="iblk">'
        + '<div>'
        + '<div class="badge"><span class="dot"></span>' + esc(cfg.badge || t.badge) + '</div>'
        + '<div class="dname">' + esc(name) + '</div>'
        + '<div class="dsub">' + t.handpick + '</div>'
        + '</div>'
        + '<a href="' + shop + '" class="cta">' + esc(cfg.cta || t.cta) + ' ' + t.arr + '</a>'
        + '</div>'
        + '<div class="row">'
        + heroHTML
        + rest.map(function(pr) { return card(pr, false); }).join('')
        + '</div>'
        + '</div></div></div>';
}

var RENDERERS = [renderA, renderB, renderC, renderD];

/* ═══ SKELETON ═══════════════════════════════════════════════════════════ */
function showSkel(shadow, p, isRtl) {
    var sks = '';
    for (var i = 0; i < 8; i++) sks += skCard(100, 100);
    shadow.innerHTML = '<style>' + baseCSS(p, isRtl) + layoutCSS(p, isRtl, 0) + '</style>'
        + '<div class="dsp"><div class="outer">'
        + '<div style="display:flex;align-items:center;gap:10px;padding:11px 14px;border-bottom:1px solid ' + p.brd + '">'
        + '<div class="sk" style="width:105px;height:22px;border-radius:20px"></div>'
        + '<div class="sk" style="width:85px;height:15px;border-radius:4px;margin-left:8px"></div>'
        + '</div>'
        + '<div style="display:flex;gap:9px;padding:10px 14px;overflow:hidden">' + sks + '</div>'
        + '</div></div>';
}

/* ═══ INIT ═══════════════════════════════════════════════════════════════ */
function initSpotlight(host) {
    if (!host || host._dspInit) return;
    host._dspInit = true;

    var section = host.closest('section.s_dept_spotlight') || host.parentElement;
    var isRtl   = detectLang() === 'ar';
    var p       = P();
    var layout  = _layout;

    function getCfg() {
        return {
            ids:   (section.getAttribute('data-categ-ids') || '').trim(),
            badge: section.getAttribute(isRtl ? 'data-badge-ar' : 'data-badge-en') || '',
            cta:   section.getAttribute(isRtl ? 'data-cta-ar'   : 'data-cta-en')   || '',
        };
    }

    var shadow = host.attachShadow({ mode: 'open' });
    showSkel(shadow, p, isRtl);

    function load() {
        var cfg = getCfg();
        var url = '/dsp/products' + (cfg.ids ? '?categ_id=' + encodeURIComponent(cfg.ids) : '');

        fetch(url)
            .then(function(r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
            .then(function(d) {
                if (!d.ok) throw new Error(d.err || 'server error');
                var list = (d.results || []).filter(function(x) { return x.rows && x.rows.length > 0; });
                if (!list.length) {
                    shadow.innerHTML = '<style>' + baseCSS(p, isRtl) + '</style>'
                        + '<div class="dsp"><div class="outer" style="padding:18px;font-size:12px;color:' + p.sub + '">'
                        + T[isRtl ? 'ar' : 'en'].noProducts + '</div></div>';
                    return;
                }
                var data = list[Math.floor(Math.random() * list.length)];
                /* override isRtl from server response if available */
                var ar = data.is_arabic !== undefined ? data.is_arabic : isRtl;
                RENDERERS[layout](shadow, p, ar, data, getCfg());
            })
            .catch(function(e) {
                shadow.innerHTML = '<style>' + baseCSS(p, isRtl) + '</style>'
                    + '<div class="dsp"><div class="outer" style="padding:18px;font-size:12px;color:' + p.sub + '">Error: ' + esc(e.message) + '</div></div>';
            });
    }

    if ('IntersectionObserver' in window) {
        var io = new IntersectionObserver(function(entries) {
            if (entries[0].isIntersecting) { io.disconnect(); load(); }
        }, { rootMargin: '200px' });
        io.observe(host);
    } else {
        load();
    }
}

/* ═══ BOOT ═══════════════════════════════════════════════════════════════ */
function scan() { document.querySelectorAll('.dsp-host').forEach(initSpotlight); }
if (document.readyState === 'loading') { document.addEventListener('DOMContentLoaded', scan); }
else { scan(); }

new MutationObserver(function(ms) {
    ms.forEach(function(m) {
        m.addedNodes.forEach(function(n) {
            if (n.nodeType !== 1) return;
            if (n.classList && n.classList.contains('dsp-host')) initSpotlight(n);
            else if (n.querySelectorAll) n.querySelectorAll('.dsp-host').forEach(initSpotlight);
        });
    });
}).observe(document.body, { childList: true, subtree: true });

})();
