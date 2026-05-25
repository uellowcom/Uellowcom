/* ZOrder v1.0 - Fast Checkout */
(function () {

    var isAr = document.documentElement.dir === 'rtl' ||
               (document.documentElement.lang || '').startsWith('ar');

    var T = {
        title:       isAr ? 'اشتري سريعاً'                 : 'Fast Order',
        subtitle:    isAr ? 'أكمل طلبك في ثوانٍ'           : 'Complete your order in seconds',
        lbl_name:    isAr ? 'الاسم الكامل'                  : 'Full Name',
        lbl_phone:   isAr ? 'رقم الهاتف'                    : 'Phone Number',
        lbl_email:   isAr ? 'البريد الإلكتروني'              : 'Email Address',
        ph_email:    isAr ? 'example@email.com'               : 'example@email.com',
        err_email:   isAr ? 'أدخل بريدًا إلكترونيًا صحيحًا' : 'Enter a valid email address',
        lbl_addr:    isAr ? 'العنوان التفصيلي'              : 'Detailed Address',
        ph_name:     isAr ? 'أدخل اسمك'                    : 'Enter your name',
        ph_phone:    isAr ? '+965 XXXX XXXX'                : '+965 XXXX XXXX',
        ph_addr:     isAr ? 'العنوان'                       : 'Address',
        my_loc:      isAr ? '⊕ موقعي'                      : '⊕ My Location',
        detecting:   isAr ? 'جارٍ تحديد موقعك…'           : 'Detecting location…',
        next:        isAr ? 'التالي ←'                      : 'Next →',
        pay_title:   isAr ? 'طريقة الدفع'                  : 'Payment Method',
        place_order: isAr ? 'تأكيد الطلب'                  : 'Place Order',
        back:        isAr ? '→ رجوع'                       : '← Back',
        processing:  isAr ? 'جارٍ المعالجة…'              : 'Processing…',
        done_title:  isAr ? '🎉 تم تأكيد طلبك!'           : '🎉 Order Confirmed!',
        done_msg:    isAr ? 'مبروك! سيتم التواصل معك قريباً.' : 'Congratulations! We\'ll contact you soon.',
        shop:        isAr ? '🛍 متابعة التسوق'             : '🛍 Continue Shopping',
        wa_lbl:      isAr ? 'واتساب'                       : 'WhatsApp',
        wa_btn:      isAr ? 'تواصل معنا'                   : 'Contact Us',
        ord_num:     isAr ? 'رقم الطلب'                    : 'Order #',
        ord_total:   isAr ? 'المبلغ'                       : 'Total',
        ord_phone:   isAr ? 'الهاتف'                       : 'Phone',
        ord_addr:    isAr ? 'العنوان'                       : 'Address',
        ord_pay:     isAr ? 'طريقة الدفع'                  : 'Payment',
        err_name:    isAr ? 'أدخل اسمك'                    : 'Enter your name',
        err_phone:   isAr ? 'أدخل رقم هاتفك'              : 'Enter your phone',
        err_pay:     isAr ? 'اختر طريقة دفع'               : 'Choose payment method',
        err_prod:    isAr ? 'المنتج غير متاح'               : 'Product not available',
        wait:        isAr ? 'لحظة…'                        : 'Please wait…',
        loading_pay: isAr ? 'جارٍ تحميل وسائل الدفع…'    : 'Loading payment methods…',
    };

    var DIR = isAr ? 'rtl' : 'ltr';
    var LR  = isAr ? 'left' : 'right';

    /* ── CSS ── */
    if (!document.getElementById('zo-css')) {
        var s = document.createElement('style');
        s.id = 'zo-css';
        s.textContent = [
            '.zo-ov{position:fixed;inset:0;z-index:99999;background:rgba(0,0,0,.5);display:flex;align-items:center;justify-content:center;opacity:0;transition:opacity .2s;pointer-events:none}',
            '.zo-ov.on{opacity:1;pointer-events:all}',
            '.zo-dlg{background:#fff;border-radius:18px;width:calc(100% - 20px);max-width:460px;max-height:92vh;display:flex;flex-direction:column;direction:'+DIR+';box-shadow:0 20px 60px rgba(0,0,0,.25);transform:translateY(30px) scale(.96);transition:transform .28s cubic-bezier(.34,1.56,.64,1)}',
            '.zo-ov.on .zo-dlg{transform:none}',
            '.zo-head{background:linear-gradient(135deg,#fdd835,#ffb300);border-radius:18px 18px 0 0;padding:16px 20px 12px;position:relative;flex-shrink:0}',
            '.zo-head h2{margin:0;font-size:17px;font-weight:800;color:#3e2000}',
            '.zo-head p{margin:3px 0 0;font-size:12px;color:rgba(62,32,0,.6)}',
            '.zo-badge{display:inline-flex;align-items:center;gap:5px;margin-top:8px;background:rgba(255,255,255,.35);border:1px solid rgba(255,255,255,.5);border-radius:7px;padding:3px 9px;font-size:11px;font-weight:700;color:#3e2000;max-width:90%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}',
            '.zo-x{position:absolute;top:11px;'+LR+':13px;background:rgba(62,32,0,.12);border:none;width:28px;height:28px;border-radius:50%;font-size:15px;color:#3e2000;cursor:pointer;display:flex;align-items:center;justify-content:center}',
            '.zo-body{padding:16px 20px 0;overflow-y:auto;flex:1}',
            '.zo-foot{padding:12px 20px 16px;flex-shrink:0;border-top:1px solid #f0f0f0;background:#fff;border-radius:0 0 18px 18px}',
            '.zo-lbl{display:block;font-size:10px;font-weight:700;color:#f07b20;text-transform:uppercase;letter-spacing:.6px;margin-bottom:4px}',
            '.zo-inp{width:100%;box-sizing:border-box;border:1.5px solid #ffe0a0;border-radius:9px;padding:9px 12px;font-size:14px;color:#222;background:#fffdf5;outline:none;margin-bottom:12px;font-family:inherit;direction:'+DIR+';transition:border .15s}',
            '.zo-inp:focus{border-color:#ffb300;background:#fff}',
            'textarea.zo-inp{resize:vertical;min-height:56px;line-height:1.4}',
            '.zo-inp.zo-flash{border-color:#ffb300;background:#fffde0}',
            '.zo-mwrap{border:1.5px solid #ffe0a0;border-radius:10px;overflow:hidden;margin-bottom:6px;position:relative}',
            '.zo-map{height:170px;width:100%}',
            '.zo-locbtn{position:absolute;top:7px;'+LR+':7px;z-index:500;background:#fff;border:1px solid #ffb300;border-radius:7px;padding:4px 9px;font-size:11px;font-weight:600;color:#d4500a;cursor:pointer}',
            '.zo-hint{font-size:11px;color:#888;margin-bottom:12px;line-height:1.4}',
            '.zo-pl{display:flex;flex-direction:column;gap:7px;padding-bottom:4px}',
            '.zo-po{display:flex;align-items:center;gap:10px;border:2px solid #ffe0a0;border-radius:10px;padding:10px 12px;cursor:pointer;background:#fffdf5;transition:border .15s}',
            '.zo-po:hover,.zo-po.sel{border-color:#ffb300;background:#fff8e0}',
            '.zo-pi{width:36px;height:36px;border-radius:7px;background:#ffe9c0;display:flex;align-items:center;justify-content:center;font-size:20px;flex-shrink:0;overflow:hidden}',
            '.zo-pi img{width:100%;height:100%;object-fit:contain}',
            '.zo-pn{font-size:13px;font-weight:600;color:#222;flex:1}',
            '.zo-pc{width:20px;height:20px;border:2px solid #ffb300;border-radius:50%;display:flex;align-items:center;justify-content:center;flex-shrink:0;font-size:11px;font-weight:700}',
            '.zo-po.sel .zo-pc{background:#ffb300;color:#3e2000}',
            '.zo-btn{width:100%;padding:12px;border:none;border-radius:10px;background:linear-gradient(135deg,#fdd835,#ffb300);color:#3e2000;font-size:14px;font-weight:800;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:7px;font-family:inherit;box-shadow:0 3px 12px rgba(253,216,53,.45);transition:all .15s}',
            '.zo-btn:hover:not(:disabled){transform:translateY(-1px)}',
            '.zo-btn:disabled{opacity:.5;cursor:not-allowed;transform:none}',
            '.zo-btn2{width:100%;padding:9px;border:1.5px solid #fdd835;border-radius:10px;background:#fff;color:#b35c00;font-size:13px;font-weight:600;cursor:pointer;margin-top:8px;font-family:inherit}',
            '.zo-sicon{font-size:48px;text-align:center;margin:6px 0 3px}',
            '.zo-stitle{font-size:17px;font-weight:800;text-align:center;color:#1a1a1a;margin-bottom:5px}',
            '.zo-smsg{font-size:12px;text-align:center;color:#666;margin-bottom:14px;line-height:1.5}',
            '.zo-ocard{background:#fffdf0;border:1.5px solid #f7d87b;border-radius:12px;padding:12px 14px;margin-bottom:4px}',
            '.zo-orow{display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #f5edd0;font-size:12px;gap:8px}',
            '.zo-orow:last-child{border-bottom:none}',
            '.zo-orow .k{color:#b07020;font-weight:600;flex-shrink:0}',
            '.zo-orow .v{color:#1a1a1a;font-weight:600;text-align:'+LR+'}',
            '.zo-ototal .v{font-size:15px;color:#d4500a;font-weight:800}',
            '.zo-toast{position:fixed;bottom:20px;left:50%;transform:translateX(-50%) translateY(60px);background:#2a1800;color:#fff;border-radius:9px;padding:10px 20px;font-size:13px;z-index:999999;transition:transform .25s;pointer-events:none;white-space:nowrap}',
            '.zo-toast.on{transform:translateX(-50%) translateY(0)}',
            '.zo-toast.ok{background:#2d8a4e}.zo-toast.err{background:#c0392b}',
            '@keyframes zo-spin{to{transform:rotate(360deg)}}',
            '.zo-sp{width:15px;height:15px;border:2px solid rgba(0,0,0,.2);border-top-color:#3e2000;border-radius:50%;animation:zo-spin .6s linear infinite;display:inline-block;vertical-align:middle}',
        ].join('\n');
        document.head.appendChild(s);
    }

    /* ── Toast ── */
    var _toast = null;
    function toast(msg, type) {
        if (!_toast) { _toast = document.createElement('div'); _toast.className = 'zo-toast'; document.body.appendChild(_toast); }
        _toast.textContent = msg;
        _toast.className = 'zo-toast' + (type === 'ok' ? ' ok' : type === 'err' ? ' err' : '');
        requestAnimationFrame(function () { _toast.classList.add('on'); });
        clearTimeout(_toast._t);
        _toast._t = setTimeout(function () { _toast.classList.remove('on'); }, 3000);
    }

    /* ── CSRF ── */
    function csrf() {
        var m = document.querySelector('meta[name="csrf-token"]');
        if (m) return m.getAttribute('content');
        if (window.odoo && window.odoo.csrf_token) return window.odoo.csrf_token;
        var c = document.cookie.match(/\bcsrf_token=([^;]+)/);
        return c ? decodeURIComponent(c[1]) : '';
    }

    /* ── RPC ── */
    function rpc(url, params) {
        return fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf() },
            body: JSON.stringify({ jsonrpc: '2.0', method: 'call', id: Date.now(), params: params || {} })
        }).then(function (r) { return r.json(); }).then(function (d) {
            if (d.error) throw new Error((d.error.data && d.error.data.message) || 'Server error');
            return d.result;
        });
    }

    /* ── Leaflet ── */
    var _leafProm = null;
    function loadLeaflet() {
        if (_leafProm) return _leafProm;
        _leafProm = new Promise(function (res) {
            if (window.L) return res(window.L);
            var lnk = document.createElement('link'); lnk.rel = 'stylesheet';
            lnk.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'; document.head.appendChild(lnk);
            var s = document.createElement('script'); s.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
            s.onload = function () { res(window.L); }; document.head.appendChild(s);
        });
        return _leafProm;
    }

    /* ── State ── */
    var dlg = null, leafMap = null, leafMk = null;
    var locData = {}, addrEdited = false;
    var selPay = null, selPayName = '', lastForm = null, curProd = {};

    /* ── Build dialog ── */
    function build() {
        if (dlg) return;
        dlg = document.createElement('div'); dlg.className = 'zo-ov'; dlg.id = 'zo-ov';
        dlg.innerHTML = [
            '<div class="zo-dlg">',
            /* step 1 */
            '<div id="zs1" style="display:flex;flex-direction:column;flex:1;min-height:0">',
            '<div class="zo-head"><button class="zo-x" id="zx1">\u2715</button>',
            '<h2>\u26a1 '+T.title+'</h2><p>'+T.subtitle+'</p>',
            '<div class="zo-badge" id="zbadge" style="display:none">\ud83d\udce6 <span id="zbname"></span></div>',
            '</div>',
            '<div class="zo-body">',
            '<label class="zo-lbl">'+T.lbl_name+'</label><input class="zo-inp" id="znm" type="text" placeholder="'+T.ph_name+'" autocomplete="name"/>',
            '<div style="display:flex;gap:8px">',
            '<div style="flex:1"><label class="zo-lbl">'+T.lbl_phone+'</label><input class="zo-inp" id="zph" type="tel" placeholder="'+T.ph_phone+'" autocomplete="tel" style="margin-bottom:0"/></div>',
            '<div style="flex:1"><label class="zo-lbl">'+T.lbl_email+'</label><input class="zo-inp" id="zeml" type="email" placeholder="'+T.ph_email+'" autocomplete="email" style="margin-bottom:0"/></div>',
            '</div>',
            '<div style="height:12px"></div>',
            '<label class="zo-lbl">'+T.lbl_loc+'</label>',
            '<div class="zo-mwrap"><div class="zo-map" id="zmap"></div><button class="zo-locbtn" id="zlocbtn">'+T.my_loc+'</button></div>',
            '<p class="zo-hint" id="zhint">'+T.detecting+'</p>',
            '<label class="zo-lbl">'+T.lbl_addr+'</label><textarea class="zo-inp" id="zadr" placeholder="'+T.ph_addr+'"></textarea>',
            '</div>',
            '<div class="zo-foot"><button class="zo-btn" id="zs1next">'+T.next+'</button></div>',
            '</div>',
            /* step 2 */
            '<div id="zs2" style="display:none;flex-direction:column;flex:1;min-height:0">',
            '<div class="zo-head"><button class="zo-x" id="zx2">\u2715</button>',
            '<h2>\ud83d\udcb3 '+T.pay_title+'</h2><p>'+T.subtitle+'</p></div>',
            '<div class="zo-body"><div id="zpl" class="zo-pl"><p style="text-align:center;color:#888;padding:20px">'+T.loading_pay+'</p></div></div>',
            '<div class="zo-foot"><button class="zo-btn" id="zpaybtn" disabled>'+T.place_order+'</button>',
            '<button class="zo-btn2" id="zback">'+T.back+'</button></div>',
            '</div>',
            /* step 3 */
            '<div id="zs3" style="display:none;flex-direction:column;flex:1;min-height:0">',
            '<div class="zo-head"><button class="zo-x" id="zx3">\u2715</button>',
            '<h2>\ud83c\udf89 '+T.done_title+'</h2><p>'+T.subtitle+'</p></div>',
            '<div class="zo-body">',
            '<div class="zo-sicon">\ud83c\udf8a</div>',
            '<div class="zo-stitle">'+T.done_title+'</div>',
            '<div class="zo-smsg">'+T.done_msg+'</div>',
            '<div class="zo-ocard" id="zocard"></div>',
            '</div>',
            '<div class="zo-foot" id="zfoot3"><button class="zo-btn" id="zdone">'+T.shop+'</button></div>',
            '</div>',
            '</div>'
        ].join('');
        document.body.appendChild(dlg);

        function on(id, fn) { var el = dlg.querySelector('#'+id); if (el) el.addEventListener('click', fn); }
        on('zx1', close); on('zx2', close); on('zx3', close);
        on('zs1next', goStep2);
        on('zback', function () { showStep(1); });
        on('zpaybtn', doSubmit);
        on('zdone', function () { close(); location.href = '/shop'; });
        on('zlocbtn', geoLocate);
        dlg.querySelector('#zadr').addEventListener('input', function () { addrEdited = true; });
        dlg.addEventListener('click', function (e) { if (e.target === dlg) close(); });
        document.addEventListener('keydown', function (e) { if (e.key === 'Escape') close(); });
    }

    function showStep(n) {
        if (!dlg) return;
        ['zs1','zs2','zs3'].forEach(function (id, i) {
            var el = dlg.querySelector('#'+id);
            if (el) el.style.display = (i+1 === n) ? 'flex' : 'none';
        });
    }

    function close() { if (dlg) dlg.classList.remove('on'); document.body.style.overflow = ''; }

    function open(tmplId, pname, purl) {
        build();
        addrEdited = false; selPay = null; selPayName = ''; selProviderId = 0;
        selMethodId = 0; selProviderCode = ''; selIsCod = false;
        lastForm = null; locData = {};
        curProd = { tmplId: tmplId, name: pname || '', url: purl || location.href };

        dlg.querySelector('#znm').value = '';
        dlg.querySelector('#zph').value = '';
        dlg.querySelector('#zeml').value = '';
        dlg.querySelector('#zadr').value = '';
        dlg.querySelector('#zadr').classList.remove('zo-flash');
        dlg.querySelector('#zhint').textContent = T.detecting;
        dlg.querySelector('#zbname').textContent = pname || '';
        dlg.querySelector('#zbadge').style.display = pname ? 'inline-flex' : 'none';
        dlg.querySelector('#zpl').innerHTML = '<p style="text-align:center;color:#888;padding:20px">'+T.loading_pay+'</p>';
        dlg.querySelector('#zpaybtn').disabled = true;
        dlg.querySelectorAll('.zo-po').forEach(function (o) { o.classList.remove('sel'); var c=o.querySelector('.zo-pc');if(c)c.textContent=''; });

        showStep(1);
        dlg.classList.add('on');
        document.body.style.overflow = 'hidden';
        dlg.querySelector('#znm').focus();
        loadLeaflet().then(function () { setTimeout(initMap, 150); });
        loadPayments();
    }

    /* ── Map ── */
    function mkIcon() {
        return window.L.divIcon({
            html: '<div style="width:24px;height:24px;background:#ffb300;border:3px solid #fff;border-radius:50% 50% 50% 0;transform:rotate(-45deg);box-shadow:0 2px 6px rgba(0,0,0,.3)"></div>',
            className: '', iconSize: [24,24], iconAnchor: [12,24]
        });
    }
    function initMap() {
        var L = window.L; if (!L) return;
        var el = document.getElementById('zmap'); if (!el) return;
        if (!leafMap) {
            leafMap = L.map(el).setView([26.8, 30.8], 5);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {attribution:'\xa9 OSM'}).addTo(leafMap);
            leafMap.on('click', function (e) { plMk(e.latlng.lat, e.latlng.lng); revGeo(e.latlng.lat, e.latlng.lng); });
        } else { leafMap.invalidateSize(); }
        fetch('https://ipapi.co/json/').then(function(r){return r.json();}).then(function(g){
            if (!g || !g.latitude) return;
            leafMap.setView([g.latitude, g.longitude], 13);
            plMk(g.latitude, g.longitude);
            locData = { lat: g.latitude, lng: g.longitude, city: g.city||'', cc: g.country_code||'' };
            revGeo(g.latitude, g.longitude);
        }).catch(function(){});
    }
    function plMk(lat, lng) {
        if (!leafMap) return;
        if (leafMk) leafMap.removeLayer(leafMk);
        leafMk = window.L.marker([lat,lng], {icon:mkIcon(), draggable:true}).addTo(leafMap);
        leafMk.on('dragend', function(e){ var p=e.target.getLatLng(); locData.lat=p.lat; locData.lng=p.lng; revGeo(p.lat,p.lng); });
        locData.lat = lat; locData.lng = lng;
    }
    function revGeo(lat, lng) {
        var hint = dlg && dlg.querySelector('#zhint');
        var adr  = dlg && dlg.querySelector('#zadr');
        if (hint) hint.textContent = '📍 Loading…';
        fetch('https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat='+lat+'&lon='+lng+'&accept-language='+(isAr?'ar,en':'en'))
            .then(function(r){return r.json();}).then(function(d){
                var a = d.address || {};
                locData.street = [a.road, a.house_number].filter(Boolean).join(' ');
                locData.city   = a.city || a.town || a.village || a.county || '';
                locData.cc     = (a.country_code||'').toUpperCase();
                locData.full   = d.display_name || '';
                if (hint) hint.textContent = '📍 ' + (locData.full || 'Location set');
                if (adr && !addrEdited) {
                    adr.value = locData.full || '';
                    adr.classList.add('zo-flash');
                    setTimeout(function(){ adr.classList.remove('zo-flash'); }, 1200);
                }
            }).catch(function(){ if(hint) hint.textContent = '📍 Could not fetch address'; });
    }
    function geoLocate() {
        var btn = dlg && dlg.querySelector('#zlocbtn');
        if (!navigator.geolocation) { toast('Geolocation not supported', 'err'); return; }
        if (btn) { btn.textContent = isAr ? 'جارٍ…' : 'Locating…'; btn.disabled = true; }
        navigator.geolocation.getCurrentPosition(function(p){
            leafMap.setView([p.coords.latitude, p.coords.longitude], 15);
            plMk(p.coords.latitude, p.coords.longitude);
            revGeo(p.coords.latitude, p.coords.longitude);
            if (btn) { btn.textContent = T.my_loc; btn.disabled = false; }
        }, function(){
            toast(isAr ? 'تعذّر الحصول على الموقع' : 'Could not get location', 'err');
            if (btn) { btn.textContent = T.my_loc; btn.disabled = false; }
        });
    }

    /* ── Payments ── */
    var PAY_ICONS = {
        cod:        { bg:'#e8f5e9', em:'💵', img:'' },
        knet:       { bg:'#fff',    em:'🏦', img:'https://upload.wikimedia.org/wikipedia/en/thumb/9/9e/KNET_logo.png/220px-KNET_logo.png' },
        apple_pay:  { bg:'#000',    em:'🍎', img:'https://developer.apple.com/assets/elements/icons/apple-pay/apple-pay.svg' },
        google_pay: { bg:'#fff',    em:'🔵', img:'https://upload.wikimedia.org/wikipedia/commons/thumb/f/f2/Google_Pay_Logo.svg/320px-Google_Pay_Logo.svg.png' },
        samsung_pay:{ bg:'#1428a0', em:'📱', img:'https://upload.wikimedia.org/wikipedia/commons/thumb/2/24/Samsung_Pay_wordmark.svg/320px-Samsung_Pay_wordmark.svg.png' },
        credit_card:{ bg:'#1a1f71', em:'💳', img:'https://upload.wikimedia.org/wikipedia/commons/thumb/5/5e/Visa_Inc._logo.svg/320px-Visa_Inc._logo.svg.png' },
    };
    function payIcon(name, code) {
        var n = (name||'').toLowerCase(), c = (code||'').toLowerCase();
        if (n.includes('knet') || c.includes('knet')) return PAY_ICONS.knet;
        if (n.includes('apple') || c.includes('apple')) return PAY_ICONS.apple_pay;
        if (n.includes('google') || c.includes('google')) return PAY_ICONS.google_pay;
        if (n.includes('samsung') || c.includes('samsung')) return PAY_ICONS.samsung_pay;
        if (n.includes('credit') || n.includes('visa') || c.includes('card')) return PAY_ICONS.credit_card;
        if (n.includes('cash') || n.includes('delivery') || c === 'cod') return PAY_ICONS.cod;
        return { bg:'#f5f5f5', em:'💳', img:'' };
    }
    /* ── extra payment state ── */
    var selProviderId = 0, selMethodId = 0, selProviderCode = '', selIsCod = false;

    function loadPayments() {
        rpc('/zorder/payments', {}).then(function(res){
            renderPayments((res && res.ok && res.methods) ? res.methods : []);
        }).catch(function(){ renderPayments([]); });
    }
    function renderPayments(methods) {
        if (!dlg) return;
        var list = dlg.querySelector('#zpl'); if (!list) return;
        if (!methods.length) methods = [{id:-1, name:'Cash on Delivery', code:'cod', icon:'', is_cod:true, provider_id:0, provider_code:'custom'}];
        var html = '';
        methods.forEach(function(m) {
            var info   = payIcon(m.name, m.code);
            var imgSrc = m.icon || info.img || '';
            var ic = imgSrc
                ? '<img src="'+imgSrc+'" alt="" style="width:100%;height:100%;object-fit:contain" onerror="this.style.display=\'none\'"/>'
                : '<span style="font-size:20px;line-height:1">'+info.em+'</span>';
            html += '<div class="zo-po"'
                  + ' data-code="'+(m.code||'')+'"'
                  + ' data-name="'+m.name+'"'
                  + ' data-provider-id="'+(m.provider_id||0)+'"'
                  + ' data-method-id="'+(m.id||0)+'"'
                  + ' data-provider-code="'+(m.provider_code||'')+'"'
                  + ' data-is-cod="'+(m.is_cod?'1':'0')+'">'
                  + '<div class="zo-pi" style="background:'+info.bg+';padding:3px">'+ic+'</div>'
                  + '<span class="zo-pn">'+m.name+'</span>'
                  + '<span class="zo-pc"></span></div>';
        });
        list.innerHTML = html;
        var opts = list.querySelectorAll('.zo-po');
        opts.forEach(function(opt) {
            opt.addEventListener('click', function() {
                opts.forEach(function(o){ o.classList.remove('sel'); var c=o.querySelector('.zo-pc');if(c)c.textContent=''; });
                opt.classList.add('sel');
                var ch = opt.querySelector('.zo-pc'); if (ch) ch.textContent = '✓';
                selPay          = opt.dataset.code;
                selPayName      = opt.dataset.name;
                selProviderId   = parseInt(opt.dataset.providerId || '0', 10);
                selMethodId     = parseInt(opt.dataset.methodId || '0', 10);
                selProviderCode = opt.dataset.providerCode || '';
                selIsCod        = opt.dataset.isCod === '1';
                var pb = dlg.querySelector('#zpaybtn'); if (pb) pb.disabled = false;
            });
        });
    }

    /* ── Step 1 → 2 ── */
    function goStep2() {
        var nm  = dlg.querySelector('#znm').value.trim();
        var ph  = dlg.querySelector('#zph').value.trim();
        var eml = dlg.querySelector('#zeml').value.trim();
        var ad  = dlg.querySelector('#zadr').value.trim() || locData.full || '';
        if (!nm)  { toast(T.err_name, 'err');  dlg.querySelector('#znm').focus();  return; }
        if (!ph)  { toast(T.err_phone, 'err'); dlg.querySelector('#zph').focus();  return; }
        if (!eml || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(eml)) {
            toast(T.err_email, 'err'); dlg.querySelector('#zeml').focus(); return;
        }
        lastForm = { name:nm, phone:ph, email:eml, full_address:ad,
                     street:locData.street||'', city:locData.city||'', country_code:locData.cc||'',
                     latitude:locData.lat||'', longitude:locData.lng||'' };
        showStep(2);
    }

    /* ── Submit ── */
    function doSubmit() {
        if (!selPay) { toast(T.err_pay, 'err'); return; }
        var btn = dlg.querySelector('#zpaybtn');
        if (btn) { btn.disabled = true; btn.innerHTML = '<span class="zo-sp"></span> '+T.processing; }

        // Step 1: confirm order (create partner, set address, confirm sale order)
        rpc('/zorder/submit', Object.assign({}, lastForm, {payment_method: selPay, is_cod: selIsCod}))
            .then(function(res) {
                if (!res || !res.ok) {
                    var msg = res && res.error === 'empty_cart'
                        ? (isAr ? 'السلة فارغة' : 'Cart is empty')
                        : (isAr ? 'حدث خطأ' : 'Something went wrong');
                    toast(msg, 'err');
                    if (btn) { btn.disabled = false; btn.textContent = T.place_order; }
                    return;
                }

                // Step 2a: COD → show success directly
                if (selIsCod || selProviderCode === 'custom') {
                    showDone(res);
                    return;
                }

                // Step 2b: Online payment → redirect via Odoo payment transaction
                var orderId     = res.order_id;
                var accessToken = res.access_token || '';
                var amount      = res.amount_total || '0';
                var currencyId  = res.currency_id || 0;
                var partnerId   = res.partner_id || 0;

                console.log('[ZO] Payment: provider='+selProviderId+' method='+selMethodId+' order='+orderId+' token='+(accessToken?'ok':'MISSING')+' isCod='+selIsCod);

                var payload = {
                    jsonrpc: '2.0', method: 'call', id: Date.now(),
                    params: {
                        access_token:           accessToken,
                        provider_id:            selProviderId,
                        payment_method_id:      selMethodId || false,
                        token_id:               false,
                        flow:                   'redirect',
                        landing_route:          '/shop/payment/validate',
                        tokenization_requested: false,
                    }
                };

                fetch('/shop/payment/transaction/' + orderId, {
                    method: 'POST',
                    credentials: 'same-origin',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest',
                    },
                    body: JSON.stringify(payload),
                })
                .then(function(r) {
                    var ct = r.headers.get('content-type') || '';
                    if (!ct.includes('json')) {
                        return r.text().then(function(t){ throw new Error('Server error: ' + t.substr(0,100)); });
                    }
                    return r.json();
                })
                .then(function(data) {
                    if (data.error) {
                        var errMsg = (data.error.data && data.error.data.message) || data.error.message || 'Unknown error';
                        throw new Error(errMsg);
                    }
                    var result = data.result;
                    var redirectUrl = null;

                    if (result) {
                        // Try all possible URL locations
                        redirectUrl = result.upay_payment_link_url
                            || result.redirect_url
                            || result.action_url
                            || null;

                        // Extract from redirect_form_html (UPayments style)
                        if (!redirectUrl && result.redirect_form_html) {
                            var tmp = document.createElement('div');
                            tmp.innerHTML = result.redirect_form_html;
                            var inp = tmp.querySelector('input[name="upay_payment_link_url"]');
                            if (inp && inp.value) { redirectUrl = inp.value; }
                            if (!redirectUrl) {
                                var form = tmp.querySelector('form');
                                if (form && form.action) { redirectUrl = form.action; }
                                if (!redirectUrl && form) {
                                    document.body.appendChild(form);
                                    form.submit();
                                    return;
                                }
                            }
                        }

                        // Nested rendering_values
                        if (!redirectUrl && result.rendering_values) {
                            redirectUrl = result.rendering_values.upay_payment_link_url
                                || result.rendering_values.redirect_url
                                || null;
                        }
                    }

                    window.location.href = redirectUrl || '/payment/status';
                })
                .catch(function(e) {
                    toast((isAr ? 'خطأ في الدفع: ' : 'Payment error: ') + e.message, 'err');
                    if (btn) { btn.disabled = false; btn.textContent = T.place_order; }
                });
            })
            .catch(function(e) {
                toast('Error: '+e.message, 'err');
                if (btn) { btn.disabled = false; btn.textContent = T.place_order; }
            });
    }

    /* ── Done ── */
    function showDone(res) {
        var card = dlg.querySelector('#zocard');
        if (!card) return;
        var oname = res.order_name || '—';
        var amt   = (res.amount_total && res.amount_total !== '0.000') ? res.amount_total+' '+(res.currency||'') : '—';
        card.innerHTML = [
            {k:T.ord_num,   v:'#'+oname,                                    big:false},
            {k:T.ord_total, v:amt,                                           big:true},
            {k:T.ord_phone, v:lastForm ? lastForm.phone : '—',              big:false},
            {k:T.ord_addr,  v:lastForm ? (lastForm.full_address||'—') : '—',big:false},
            {k:T.ord_pay,   v:selPayName||selPay||'—',                      big:false},
        ].map(function(r){
            return '<div class="zo-orow'+(r.big?' zo-ototal':'')+'"><span class="k">'+r.k+'</span><span class="v">'+r.v+'</span></div>';
        }).join('');

        var foot = dlg.querySelector('#zfoot3');
        if (foot) {
            var waMsg = (isAr
                ? 'مرحباً، لقد أتممت طلبي.\n📦 '+curProd.name+'\n🔢 #'+oname+'\n💰 '+amt+'\n📞 '+(lastForm?lastForm.phone:'')+'\n📍 '+(lastForm?lastForm.full_address:'')+(curProd.url?'\n🔗 '+curProd.url:'')
                : 'Hello, I placed an order.\n📦 '+curProd.name+'\n🔢 #'+oname+'\n💰 '+amt+'\n📞 '+(lastForm?lastForm.phone:'')+'\n📍 '+(lastForm?lastForm.full_address:'')+(curProd.url?'\n🔗 '+curProd.url:''));
            var waUrl = 'https://wa.me/?text='+encodeURIComponent(waMsg);
            foot.innerHTML =
                '<div style="display:flex;gap:8px">'
                +'<button class="zo-btn" id="zdone2" style="flex:1;font-size:12px;padding:10px 6px">'+T.shop+'</button>'
                +'<a href="'+waUrl+'" target="_blank" style="flex:1;position:relative;display:flex;align-items:center;justify-content:center;gap:6px;'
                +'padding:10px 6px;border:none;border-radius:10px;text-decoration:none;background:linear-gradient(135deg,#25d366,#128c7e);'
                +'color:#fff;font-size:12px;font-weight:700;box-shadow:0 3px 10px rgba(37,211,102,.3)">'
                +'<span style="position:absolute;top:-8px;'+LR+':8px;background:#e53935;color:#fff;font-size:9px;font-weight:700;padding:1px 6px;border-radius:8px">'+T.wa_lbl+'</span>'
                +'<svg width="16" height="16" viewBox="0 0 24 24" fill="#fff"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z"/><path d="M12 0C5.373 0 0 5.373 0 12c0 2.123.554 4.118 1.528 5.845L0 24l6.337-1.51A11.956 11.956 0 0012 24c6.627 0 12-5.373 12-12S18.627 0 12 0zm0 21.818a9.818 9.818 0 01-5.007-1.374l-.36-.214-3.73.889.933-3.617-.235-.372A9.818 9.818 0 0112 2.182c5.42 0 9.818 4.398 9.818 9.818 0 5.42-4.398 9.818-9.818 9.818z"/></svg>'
                +T.wa_btn+'</a></div>';
            var d2 = dlg.querySelector('#zdone2');
            if (d2) d2.addEventListener('click', function(){ close(); location.href='/shop'; });
        }
        showStep(3);
    }

    /* ── Button click ── */
    function handleBtn(btn) {
        var wrap = btn.closest('[data-template-id]');
        if (!wrap) return;
        var tmplId = parseInt(wrap.getAttribute('data-template-id') || '0', 10);
        if (!tmplId) { toast(T.err_prod, 'err'); return; }
        var orig = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<span class="zo-sp"></span> '+T.wait;
        rpc('/zorder/add/'+tmplId, {})
            .then(function(res){
                btn.disabled = false; btn.innerHTML = orig;
                if (res && res.ok) { open(tmplId, res.product_name, res.product_url); }
                else { toast(T.err_prod, 'err'); }
            })
            .catch(function(e){ btn.disabled=false; btn.innerHTML=orig; toast('Error: '+e.message,'err'); });
    }

    /* ── Init ── */
    function init() {
        document.querySelectorAll('.zo-btn-open').forEach(function(btn){
            btn.addEventListener('click', function(e){
                e.preventDefault(); e.stopImmediatePropagation(); handleBtn(btn);
            }, true);
        });
        // Watch for dynamic buttons
        new MutationObserver(function(muts){
            muts.forEach(function(m){ m.addedNodes.forEach(function(n){
                if (n.nodeType !== 1) return;
                var btns = n.classList && n.classList.contains('zo-btn-open') ? [n] : [];
                n.querySelectorAll && n.querySelectorAll('.zo-btn-open').forEach(function(b){ btns.push(b); });
                btns.forEach(function(b){ b.addEventListener('click', function(e){ e.preventDefault(); e.stopImmediatePropagation(); handleBtn(b); }, true); });
            });});
        }).observe(document.body, {childList:true, subtree:true});
        window.__zoReady = true;
    }

    if (document.body) { init(); }
    else { document.addEventListener('DOMContentLoaded', init); }

})();
