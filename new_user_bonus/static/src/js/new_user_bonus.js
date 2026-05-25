/** @odoo-module **/
(function () {
    'use strict';

    function initBonusBanner(host) {
        if (!host || host._ub5kwd) return;
        host._ub5kwd = true;

        var TAG_ID  = parseInt(host.getAttribute('data-tag-id')  || '17', 10);
        var COUPON  = host.getAttribute('data-coupon')  || 'WELCOME5';
        var DISC_AR = host.getAttribute('data-disc-ar') || '5% خصم';
        var DISC_EN = host.getAttribute('data-disc-en') || '5% OFF';
        var SHOP    = '/shop?tags=' + TAG_ID;

        var hl   = (document.documentElement.lang || '').toLowerCase();
        var lang = hl.startsWith('ar') || location.pathname.indexOf('/ar') === 0 ? 'ar' : 'en';

        var T = {
            ar: { title:'عرض المستخدم الجديد', disc:DISC_AR, cta:'تسوق الآن', empty:'لا توجد منتجات', err:'تعذّر التحميل' },
            en: { title:'New User Bonus',        disc:DISC_EN, cta:'Shop Now',  empty:'No products.',   err:'Failed to load.' },
        };

        /* ══ Shadow DOM ══ */
        var shadow = host.attachShadow({ mode: 'open' });

        var css = [
            '@import url("https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700;900&family=Poppins:wght@400;700;900&display=swap");',
            ':host{display:block;font-family:"Tajawal","Poppins","Segoe UI",Arial,sans-serif;}',
            ':host(.rtl) .wrap{direction:rtl;}',
            ':host(.ltr) .wrap{direction:ltr;}',
            '*,*::before,*::after{box-sizing:border-box;}',
            '.wrap{width:100%;padding:0 3px;}',
            '.banner{background:#FFB700;border-radius:14px;display:flex;align-items:stretch;overflow:hidden;min-height:165px;}',
            ':host(.rtl) .info{border-left:1.5px dashed rgba(0,0,0,.15);}',
            ':host(.ltr) .info{border-right:1.5px dashed rgba(0,0,0,.15);}',
            '.info{padding:16px 18px;min-width:185px;flex-shrink:0;display:flex;flex-direction:column;justify-content:center;gap:6px;}',
            '.info-title{font-size:12px;font-weight:700;color:#5a3c00;margin:0;line-height:1.35;letter-spacing:.2px;}',
            '.disc{font-size:40px;font-weight:900;color:#1a1000;line-height:1;margin:2px 0;}',
            '.coupon{background:rgba(255,255,255,.5);border:1.5px dashed rgba(0,0,0,.25);padding:3px 9px;font-size:10.5px;font-weight:800;border-radius:5px;display:inline-block;letter-spacing:1.2px;color:#3a2600;width:fit-content;}',
            '.btn{background:#FF4646;color:#fff;border:none;padding:8px 18px;border-radius:50px;font-size:12px;font-weight:800;cursor:pointer;text-decoration:none;display:inline-flex;align-items:center;justify-content:center;width:fit-content;margin-top:5px;font-family:inherit;letter-spacing:.3px;transition:background .2s,transform .15s;white-space:nowrap;}',
            '.btn:hover{background:#e03a3a;transform:scale(1.04);}',
            '.scroll{display:flex;overflow-x:auto;gap:9px;padding:12px 14px;flex-grow:1;scrollbar-width:none;align-items:center;}',
            '.scroll::-webkit-scrollbar{display:none;}',
            '.card{background:#fff;min-width:118px;max-width:118px;border-radius:10px;padding:7px;flex-shrink:0;text-decoration:none;display:block;box-shadow:0 2px 7px rgba(0,0,0,.09);transition:transform .2s,box-shadow .2s;border:none;}',
            '.card:hover{transform:translateY(-3px);box-shadow:0 6px 16px rgba(0,0,0,.14);}',
            '.pimg{width:100%;height:86px;border-radius:7px;overflow:hidden;margin-bottom:6px;background:#f3f3ef;display:flex;align-items:center;justify-content:center;}',
            '.pimg img{width:100%;height:100%;object-fit:cover;display:block;}',
            '.pname{font-size:10.5px;color:#555;line-height:1.3;height:28px;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;margin-bottom:4px;text-align:center;}',
            '.pprice{font-size:12.5px;font-weight:800;color:#1a1000;text-align:center;display:block;}',
            '.skel{background:linear-gradient(90deg,#f0e8c0,#ffe69a,#f0e8c0);background-size:200%;animation:sh 1.4s infinite;border-radius:5px;}',
            '@keyframes sh{0%{background-position:200% 0}100%{background-position:-200% 0}}',
            '@media(max-width:600px){',
            '.banner{flex-direction:row;min-height:148px;}',
            ':host(.rtl) .info{border-left:1.5px dashed rgba(0,0,0,.15);border-right:none;}',
            ':host(.ltr) .info{border-right:1.5px dashed rgba(0,0,0,.15);border-left:none;}',
            '.info{min-width:0;width:135px;flex-shrink:0;padding:12px 10px;gap:5px;}',
            '.info-title{font-size:10.5px;}',
            '.disc{font-size:28px;}',
            '.coupon{font-size:9px;padding:2px 7px;letter-spacing:.8px;}',
            '.btn{font-size:10.5px;padding:7px 12px;margin-top:4px;}',
            '.scroll{padding:10px 8px;gap:7px;}',
            '.card{min-width:calc(50% - 11px);max-width:calc(50% - 11px);}',
            '.pimg{height:72px;}',
            '.pname{font-size:10px;height:26px;}',
            '.pprice{font-size:11.5px;}',
            '}',
        ].join('');

        shadow.innerHTML = '<style>' + css + '</style>' +
            '<div class="wrap"><div class="banner">' +
              '<div class="info">' +
                '<p class="info-title" id="s-title"></p>' +
                '<div class="disc" id="s-disc"></div>' +
                '<div class="coupon">' + COUPON + '</div>' +
                '<a href="' + SHOP + '" class="btn" id="s-cta"></a>' +
              '</div>' +
              '<div class="scroll" id="s-area"></div>' +
            '</div></div>';

        var elArea  = shadow.getElementById('s-area');
        var elTitle = shadow.getElementById('s-title');
        var elDisc  = shadow.getElementById('s-disc');
        var elCta   = shadow.getElementById('s-cta');

        function setLang(l) {
            lang = l;
            elTitle.textContent = T[l].title;
            elDisc.textContent  = T[l].disc;
            elCta.textContent   = T[l].cta;
            host.classList.toggle('rtl', l === 'ar');
            host.classList.toggle('ltr', l === 'en');
        }

        /* Skeleton */
        var sk = '';
        for (var i = 0; i < 6; i++) {
            sk += '<div style="min-width:118px;background:#fff;border-radius:10px;padding:7px;flex-shrink:0">'
                + '<div class="skel" style="width:100%;height:86px;margin-bottom:6px"></div>'
                + '<div class="skel" style="width:72%;height:9px;margin:0 auto 5px"></div>'
                + '<div class="skel" style="width:50%;height:12px;margin:0 auto"></div>'
                + '</div>';
        }
        elArea.innerHTML = sk;

        function render(rows) {
            if (!rows || !rows.length) {
                elArea.innerHTML = '<div style="padding:20px;color:#8a5c00;font-size:12px">' + T[lang].empty + '</div>';
                return;
            }
            var h = '';
            for (var j = 0; j < rows.length; j++) {
                var p = rows[j];
                h += '<a href="' + SHOP + '" class="card">'
                   + '<div class="pimg"><img src="/web/image/product.template/' + p.id + '/image_256" alt="" loading="lazy" onerror="this.style.display=\'none\'"></div>'
                   + '<div class="pname">' + p.name + '</div>'
                   + '<span class="pprice">' + p.price.toFixed(3) + ' ' + p.cur + '</span>'
                   + '</a>';
            }
            elArea.innerHTML = h;
        }

        /* ✅ Public endpoint — auth='public' في Python */
        setLang(lang);
        fetch('/nub/products?tag_id=' + TAG_ID + '&limit=20')
            .then(function (r) {
                if (!r.ok) throw new Error('HTTP ' + r.status);
                return r.json();
            })
            .then(function (d) {
                if (!d.ok) throw new Error(d.err || 'server error');
                render(d.rows);
            })
            .catch(function (e) {
                console.warn('[nub]', e.message);
                elArea.innerHTML = '<div style="padding:16px;color:#8a5c00;font-size:12px">' + T[lang].err + '</div>';
            });
    }

    function scanAndInit() {
        document.querySelectorAll('.uellow-bonus-host').forEach(initBonusBanner);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', scanAndInit);
    } else {
        scanAndInit();
    }

    new MutationObserver(function (mutations) {
        mutations.forEach(function (m) {
            m.addedNodes.forEach(function (node) {
                if (node.nodeType !== 1) return;
                if (node.classList && node.classList.contains('uellow-bonus-host')) {
                    initBonusBanner(node);
                } else if (node.querySelectorAll) {
                    node.querySelectorAll('.uellow-bonus-host').forEach(initBonusBanner);
                }
            });
        });
    }).observe(document.body, { childList: true, subtree: true });

})();
