/** @odoo-module **/

import { onMounted } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";

// Self-executing setup — runs when the page service starts
registry.category("services").add("fast_order_qc", {
    dependencies: [],
    start() {
        // Run immediately
        _qcSetup();
        return {};
    }
});

function _qcSetup() {
if (_qcLoaded) return;
    _qcLoaded = true;
/* ── run after full page load to avoid any Odoo boot conflicts ── */
    function init() {

    var isAr = (document.documentElement.lang || '').toLowerCase().startsWith('ar')
            || document.documentElement.dir === 'rtl';
    var DIR = isAr ? 'rtl' : 'ltr';

    var T = {
        title:          isAr ? 'اشتري سريعاً'                  : 'Fast Checkout',
        subtitle:       isAr ? 'أكمل طلبك في ثوانٍ'            : 'Complete your order in seconds',
        lbl_name:       isAr ? 'الاسم الكامل'                   : 'Full Name',
        lbl_phone:      isAr ? 'رقم الهاتف'                     : 'Phone Number',
        lbl_location:   isAr ? '📍 موقع التوصيل'               : '📍 Delivery Location',
        lbl_address:    isAr ? 'العنوان التفصيلي'               : 'Detailed Address',
        ph_name:        isAr ? 'أدخل اسمك الكامل'              : 'Enter your full name',
        ph_phone:       isAr ? '+965 XXXX XXXX'                 : '+965 XXXX XXXX',
        ph_address:     isAr ? 'يمكنك تعديل العنوان هنا'       : 'You can edit the address here',
        my_loc:         isAr ? '⊕ موقعي'                        : '⊕ My Location',
        locating:       isAr ? 'جارٍ التحديد…'                 : 'Locating…',
        detecting:      isAr ? 'جارٍ تحديد موقعك…'            : 'Detecting your location…',
        loading_adr:    isAr ? 'جارٍ تحميل العنوان…'           : 'Loading address…',
        loc_selected:   isAr ? 'تم تحديد الموقع'               : 'Location selected',
        no_geo:         isAr ? 'تحديد الموقع غير مدعوم'        : 'Geolocation not supported',
        loc_err:        isAr ? 'تعذّر الحصول على الموقع'       : 'Could not get location',
        adr_err:        isAr ? 'تعذّر جلب العنوان'             : 'Could not fetch address',
        err_name:       isAr ? 'الرجاء إدخال اسمك'             : 'Please enter your name',
        err_phone:      isAr ? 'الرجاء إدخال رقم الهاتف'       : 'Please enter your phone',
        confirm:        isAr ? '← متابعة للدفع'                : 'Continue to Payment →',
        choose_payment: isAr ? 'اختر طريقة الدفع'             : 'Choose Payment Method',
        loading_pay:    isAr ? 'جارٍ تحميل وسائل الدفع…'      : 'Loading payment methods…',
        btn_pay:        isAr ? 'تأكيد الطلب'                   : 'Place Order',
        back:           isAr ? '← رجوع'                        : '← Back',
        processing:     isAr ? 'جارٍ المعالجة…'               : 'Processing…',
        empty_cart:     isAr ? 'السلة فارغة'                    : 'Cart is empty',
        went_wrong:     isAr ? 'حدث خطأ ما'                    : 'Something went wrong',
        prod_unavail:   isAr ? 'المنتج غير متاح'               : 'Product not available',
        wait:           isAr ? 'لحظة…'                         : 'Please wait…',
        select_pay:     isAr ? 'الرجاء اختيار طريقة الدفع'    : 'Please select a payment method',
        order_done:     isAr ? 'تم تأكيد طلبك!'               : 'Order Confirmed!',
        congrats:       isAr ? 'مبروك! تم إتمام طلبك بنجاح.\nسيتم التواصل معك قريباً لتأكيد التوصيل.' :
                                'Congratulations! Your order has been placed.\nWe\'ll contact you soon to confirm delivery.',
        order_num:      isAr ? 'رقم الطلب'                     : 'Order #',
        order_total:    isAr ? 'المبلغ الإجمالي'               : 'Total',
        delivery_addr:  isAr ? 'عنوان التوصيل'                 : 'Delivery Address',
        contact_phone:  isAr ? 'رقم التواصل'                   : 'Phone',
        payment_lbl:    isAr ? 'طريقة الدفع'                   : 'Payment',
        continue_shop:  isAr ? '🛍 متابعة التسوق'              : '🛍 Continue Shopping',
    };

    /* ── CSS ─────────────────────────────────────────────────── */
    if (!document.getElementById('qc-styles')) {
        var LR  = isAr ? 'left'  : 'right';
        var DIR2 = isAr ? 'rtl'  : 'ltr';
        var css = [
'/* overlay */',
'.qc-overlay{position:fixed;inset:0;z-index:99999;background:rgba(0,0,0,.55);',
'  display:flex;align-items:center;justify-content:center;',
'  opacity:0;transition:opacity .25s;pointer-events:none;}',
'.qc-overlay.qc-show{opacity:1;pointer-events:all;}',
'.qc-dialog{background:#fff;border-radius:20px;',
'  width:calc(100% - 24px);max-width:460px;',
'  height:auto;max-height:92vh;',
'  display:flex;flex-direction:column;',
'  direction:' + DIR2 + ';',
'  box-shadow:0 28px 70px rgba(0,0,0,.3);',
'  transform:translateY(36px) scale(.95);',
'  transition:transform .3s cubic-bezier(.34,1.56,.64,1);}',
'.qc-overlay.qc-show .qc-dialog{transform:translateY(0) scale(1);}',
'.qc-head{background:linear-gradient(135deg,#fdd835 0%,#ffb300 60%,#ff8f00 100%);',
'  border-radius:20px 20px 0 0;padding:18px 22px 14px;',
'  position:relative;flex-shrink:0;}',
'.qc-head h2{margin:0;font-size:18px;font-weight:800;color:#3e2000;}',
'.qc-head p{margin:3px 0 0;font-size:12px;color:rgba(62,32,0,.6);}',
'.qc-badge{display:inline-flex;align-items:center;gap:6px;margin-top:9px;',
'  background:rgba(255,255,255,.35);border:1px solid rgba(255,255,255,.5);',
'  border-radius:8px;padding:4px 10px;font-size:12px;font-weight:700;color:#3e2000;',
'  max-width:calc(100% - 44px);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}',
'.qc-x{position:absolute;top:13px;' + LR + ':14px;',
'  background:rgba(62,32,0,.12);border:none;width:30px;height:30px;',
'  border-radius:50%;font-size:16px;color:#3e2000;cursor:pointer;',
'  display:flex;align-items:center;justify-content:center;transition:background .15s;}',
'.qc-x:hover{background:rgba(62,32,0,.22);}',
'.qc-body{padding:18px 22px 0;overflow-y:auto;flex:1;}',
'.qc-footer{padding:14px 22px 18px;flex-shrink:0;background:#fff;',
'  border-top:1px solid #f0f0f0;border-radius:0 0 20px 20px;position:sticky;bottom:0;}',
'.qc-label{display:block;font-size:11px;font-weight:700;color:#f07b20;',
'  text-transform:uppercase;letter-spacing:.7px;margin-bottom:5px;}',
'.qc-input{width:100%;box-sizing:border-box;',
'  border:1.5px solid #ffe0a0;border-radius:10px;',
'  padding:10px 13px;font-size:15px;color:#222;background:#fffdf5;outline:none;',
'  margin-bottom:14px;font-family:inherit;direction:' + DIR2 + ';',
'  transition:border .2s,box-shadow .2s;}',
'.qc-input:focus{border-color:#ff6b35;box-shadow:0 0 0 3px rgba(255,107,53,.15);background:#fff;}',
'textarea.qc-input{resize:vertical;min-height:60px;line-height:1.5;}',
'.qc-input.map-filled{border-color:#f7b731;background:#fffdf0;animation:qc-flash .4s ease;}',
'@keyframes qc-flash{0%{background:#fff3b0}100%{background:#fffdf0}}',
'.qc-map-wrap{border:1.5px solid #ffe0a0;border-radius:12px;overflow:hidden;',
'  margin-bottom:6px;position:relative;}',
'.qc-map{height:175px;width:100%;}',
'.qc-locate{position:absolute;top:8px;' + LR + ':8px;z-index:500;',
'  background:#fff;border:1px solid #f7b731;border-radius:8px;',
'  padding:5px 10px;font-size:12px;font-weight:600;color:#d4500a;',
'  cursor:pointer;box-shadow:0 2px 6px rgba(0,0,0,.1);transition:all .15s;}',
'.qc-locate:hover{background:#f7b731;color:#1a1a1a;}',
'.qc-map-hint{font-size:11px;padding:0 2px;margin-bottom:12px;line-height:1.4;}',
'.qc-pay-list{display:flex;flex-direction:column;gap:8px;padding-bottom:4px;}',
'.qc-pay-opt{display:flex;align-items:center;gap:12px;',
'  border:2px solid #ffe0a0;border-radius:12px;padding:12px 14px;',
'  cursor:pointer;transition:all .18s;background:#fffdf5;}',
'.qc-pay-opt:hover{border-color:#ff6b35;background:#fff5e0;}',
'.qc-pay-opt.selected{border-color:#ff6b35;background:#fff5e0;',
'  box-shadow:0 0 0 3px rgba(255,107,53,.15);}',
'.qc-pay-icon{width:38px;height:38px;border-radius:8px;background:#ffe9c0;',
'  display:flex;align-items:center;justify-content:center;font-size:22px;flex-shrink:0;overflow:hidden;}',
'.qc-pay-icon img{width:100%;height:100%;object-fit:contain;}',
'.qc-pay-name{font-size:14px;font-weight:600;color:#222;flex:1;}',
'.qc-pay-check{width:22px;height:22px;border:2px solid #f7b731;border-radius:50%;',
'  display:flex;align-items:center;justify-content:center;flex-shrink:0;',
'  font-size:12px;font-weight:700;transition:all .15s;}',
'.qc-pay-opt.selected .qc-pay-check{background:#ff6b35;border-color:#ff6b35;color:#fff;}',
'.qc-btn{width:100%;padding:13px;border:none;border-radius:12px;',
'  background:linear-gradient(135deg,#fdd835 0%,#ffb300 100%);',
'  color:#3e2000;font-size:15px;font-weight:800;cursor:pointer;',
'  box-shadow:0 4px 14px rgba(253,216,53,.5);',
'  display:flex;align-items:center;justify-content:center;gap:8px;',
'  transition:all .18s;font-family:inherit;}',
'.qc-btn:hover:not(:disabled){transform:translateY(-1px);box-shadow:0 6px 20px rgba(253,216,53,.6);}',
'.qc-btn:disabled{opacity:.5;cursor:not-allowed;transform:none;}',
'.qc-btn-sec{width:100%;padding:10px;border:1.5px solid #fdd835;border-radius:12px;',
'  background:#fff;color:#b35c00;font-size:14px;font-weight:600;cursor:pointer;',
'  margin-top:9px;font-family:inherit;transition:all .15s;}',
'.qc-btn-sec:hover{background:#fffde7;border-color:#ffb300;}',
'.qc-success-icon{font-size:52px;text-align:center;margin:8px 0 4px;}',
'.qc-success-title{font-size:19px;font-weight:800;text-align:center;color:#1a1a1a;margin-bottom:6px;}',
'.qc-success-sub{font-size:13px;text-align:center;color:#666;',
'  margin-bottom:16px;line-height:1.6;white-space:pre-line;}',
'.qc-order-card{background:#fffdf0;border:1.5px solid #f7d87b;border-radius:14px;',
'  padding:14px 16px;margin-bottom:4px;}',
'.qc-order-row{display:flex;justify-content:space-between;align-items:flex-start;',
'  padding:6px 0;border-bottom:1px solid #f5edd0;font-size:13px;gap:10px;}',
'.qc-order-row:last-child{border-bottom:none;}',
'.qc-order-row .k{color:#b07020;font-weight:600;flex-shrink:0;}',
'.qc-order-row .v{color:#1a1a1a;font-weight:600;text-align:' + LR + ';}',
'.qc-order-total .v{font-size:16px;color:#d4500a;font-weight:800;}',
'.qc-toast{position:fixed;bottom:22px;left:50%;',
'  transform:translateX(-50%) translateY(70px);',
'  background:#2a1800;color:#fff;border-radius:10px;padding:11px 22px;',
'  font-size:14px;font-weight:500;z-index:999999;',
'  transition:transform .3s;pointer-events:none;white-space:nowrap;}',
'.qc-toast.on{transform:translateX(-50%) translateY(0);}',
'.qc-toast.ok{background:#2d8a4e;}.qc-toast.err{background:#c0392b;}',
'@keyframes qc-spin{to{transform:rotate(360deg);}}',
'.qc-spin{width:17px;height:17px;border:2.5px solid rgba(0,0,0,.2);',
'  border-top-color:#1a1a1a;border-radius:50%;animation:qc-spin .7s linear infinite;}',
'.qc-loading-pay{text-align:center;padding:20px;color:#c07020;font-size:14px;}'
].join('\n');
        var st = document.createElement('style');
        st.id = 'qc-styles';
        st.textContent = css;
        document.head.appendChild(st);
    }

    /* ── Helpers ──────────────────────────────────────────────── */
    var toastEl = null;
    function toast(msg, type) {
        if (!toastEl) {
            toastEl = document.createElement('div');
            toastEl.className = 'qc-toast';
            document.body.appendChild(toastEl);
        }
        toastEl.textContent = msg;
        toastEl.className = 'qc-toast' + (type === 'ok' ? ' ok' : type === 'err' ? ' err' : '');
        requestAnimationFrame(function () { toastEl.classList.add('on'); });
        clearTimeout(toastEl._t);
        toastEl._t = setTimeout(function () { toastEl.classList.remove('on'); }, 3200);
    }

    function qs(sel) {
        return overlay ? overlay.querySelector(sel) : null;
    }

    function getCsrf() {
        var m = document.querySelector('meta[name="csrf-token"]');
        if (m) return m.getAttribute('content');
        if (window.odoo && window.odoo.csrf_token) return window.odoo.csrf_token;
        var c = document.cookie.match(/\bcsrf_token=([^;]+)/);
        return c ? decodeURIComponent(c[1]) : '';
    }

    function rpc(url, params) {
        return fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrf() },
            body: JSON.stringify({ jsonrpc: '2.0', method: 'call', id: Date.now(), params: params || {} }),
        }).then(function (r) { return r.json(); }).then(function (d) {
            if (d.error) throw new Error((d.error.data && d.error.data.message) || 'Server error');
            return d.result;
        });
    }

    var leafletPromise = null;
    function loadLeaflet() {
        if (leafletPromise) return leafletPromise;
        leafletPromise = new Promise(function (resolve) {
            if (window.L) return resolve(window.L);
            var lnk = document.createElement('link');
            lnk.rel = 'stylesheet';
            lnk.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
            document.head.appendChild(lnk);
            var s = document.createElement('script');
            s.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
            s.onload = function () { resolve(window.L); };
            document.head.appendChild(s);
        });
        return leafletPromise;
    }

    /* ── State ────────────────────────────────────────────────── */
    var overlay = null;
    var leafMap = null, leafMarker = null, locData = {};
    var selectedPayment = null, selectedPaymentName = '';
    var lastOrderData = null;
    var addrManuallyEdited = false;
    var currentProduct = { id: 0, name: '', url: '' };

    /* ── Build DOM once ───────────────────────────────────────── */
    function buildDialog() {
        if (overlay) return;   /* guard: build only once */

        overlay = document.createElement('div');
        overlay.className = 'qc-overlay';
        overlay.id = 'qc-overlay';
        overlay.innerHTML =
          '<div class="qc-dialog">' +

            /* ── Step 1 — form ── */
            '<div id="qc-s1" style="display:flex;flex-direction:column;flex:1;min-height:0;">' +
              '<div class="qc-head">' +
                '<button class="qc-x" id="qc-x1">&#x2715;</button>' +
                '<h2>&#x26A1; ' + T.title + '</h2>' +
                '<p>' + T.subtitle + '</p>' +
                '<div class="qc-badge" id="qc-badge" style="display:none">&#x1F4E6; <span id="qc-pname"></span></div>' +
              '</div>' +
              '<div class="qc-body">' +
                '<label class="qc-label">' + T.lbl_name + '</label>' +
                '<input class="qc-input" id="qc-name" type="text" placeholder="' + T.ph_name + '" autocomplete="name"/>' +
                '<label class="qc-label">' + T.lbl_phone + '</label>' +
                '<input class="qc-input" id="qc-phone" type="tel" placeholder="' + T.ph_phone + '" autocomplete="tel"/>' +
                '<label class="qc-label">' + T.lbl_location + '</label>' +
                '<div class="qc-map-wrap">' +
                  '<div class="qc-map" id="qc-map"></div>' +
                  '<button class="qc-locate" id="qc-locate">' + T.my_loc + '</button>' +
                '</div>' +
                '<p class="qc-map-hint" id="qc-map-hint" style="color:#bbb">&#x1F4CD; ' + T.detecting + '</p>' +
                '<label class="qc-label">' + T.lbl_address + '</label>' +
                '<textarea class="qc-input" id="qc-address" placeholder="' + T.ph_address + '"></textarea>' +
              '</div>' +
              '<div class="qc-footer">' +
                '<button class="qc-btn" id="qc-s1-next">' + T.confirm + '</button>' +
              '</div>' +
            '</div>' +

            /* ── Step 2 — payment ── */
            '<div id="qc-s2" style="display:none;flex-direction:column;flex:1;min-height:0;">' +
              '<div class="qc-head">' +
                '<button class="qc-x" id="qc-x2">&#x2715;</button>' +
                '<h2>&#x1F4B3; ' + T.choose_payment + '</h2>' +
                '<p>' + T.subtitle + '</p>' +
              '</div>' +
              '<div class="qc-body">' +
                '<div id="qc-pay-list" class="qc-pay-list">' +
                  '<div class="qc-loading-pay">&#x23F3; ' + T.loading_pay + '</div>' +
                '</div>' +
              '</div>' +
              '<div class="qc-footer">' +
                '<button class="qc-btn" id="qc-pay-btn" disabled>' + T.btn_pay + '</button>' +
                '<button class="qc-btn-sec" id="qc-back">' + T.back + '</button>' +
              '</div>' +
            '</div>' +

            /* ── Step 3 — success ── */
            '<div id="qc-s3" style="display:none;flex-direction:column;flex:1;min-height:0;">' +
              '<div class="qc-head">' +
                '<button class="qc-x" id="qc-x3">&#x2715;</button>' +
                '<h2>&#x1F389; ' + T.order_done + '</h2>' +
                '<p>' + T.subtitle + '</p>' +
              '</div>' +
              '<div class="qc-body">' +
                '<div class="qc-success-icon">&#x1F38A;</div>' +
                '<div class="qc-success-title">&#x1F389; ' + T.order_done + '</div>' +
                '<div class="qc-success-sub">' + T.congrats + '</div>' +
                '<div class="qc-order-card" id="qc-order-details"></div>' +
              '</div>' +
              '<div class="qc-footer" id="qc-s3-footer">' +
                '<button class="qc-btn" id="qc-done-btn">' + T.continue_shop + '</button>' +
              '</div>' +
            '</div>' +

          '</div>';

        document.body.appendChild(overlay);

        /* ── attach events — all via qs() which is null-safe ── */
        function on(id, ev, fn) {
            var el = overlay.querySelector('#' + id);
            if (el) el.addEventListener(ev, fn);
        }

        on('qc-x1',     'click', closeDialog);
        on('qc-x2',     'click', closeDialog);
        on('qc-x3',     'click', closeDialog);
        on('qc-locate', 'click', locateMe);
        on('qc-s1-next','click', goToPayment);
        on('qc-back',   'click', function () { showStep(1); });
        on('qc-pay-btn','click', doPlaceOrder);
        on('qc-done-btn','click', function () { closeDialog(); window.location.href = '/shop'; });
        on('qc-address', 'input', function () { addrManuallyEdited = true; });

        overlay.addEventListener('click', function (e) { if (e.target === overlay) closeDialog(); });
        document.addEventListener('keydown', function (e) { if (e.key === 'Escape') closeDialog(); });
    }

    function showStep(n) {
        if (!overlay) return;
        var s1 = overlay.querySelector('#qc-s1');
        var s2 = overlay.querySelector('#qc-s2');
        var s3 = overlay.querySelector('#qc-s3');
        if (s1) s1.style.display = n === 1 ? 'flex' : 'none';
        if (s2) s2.style.display = n === 2 ? 'flex' : 'none';
        if (s3) s3.style.display = n === 3 ? 'flex' : 'none';
    }

    /* ── Open dialog ──────────────────────────────────────────── */
    function openDialog(productId, productName, productUrl) {
        buildDialog();

        addrManuallyEdited  = false;
        selectedPayment     = null;
        selectedPaymentName = '';
        lastOrderData       = null;
        locData             = {};
        currentProduct      = { id: productId || 0, name: productName || '', url: productUrl || window.location.href };

        var nameEl  = qs('#qc-name');
        var phoneEl = qs('#qc-phone');
        var adrEl   = qs('#qc-address');
        var hintEl  = qs('#qc-map-hint');
        var badge   = qs('#qc-badge');
        var pname   = qs('#qc-pname');
        var payList = qs('#qc-pay-list');
        var payBtn  = qs('#qc-pay-btn');

        if (nameEl)  nameEl.value  = '';
        if (phoneEl) phoneEl.value = '';
        if (adrEl)   { adrEl.value = ''; adrEl.classList.remove('map-filled'); }
        if (hintEl)  { hintEl.style.color = '#bbb'; hintEl.textContent = '📍 ' + T.detecting; }
        if (badge && pname) {
            if (productName) { pname.textContent = productName; badge.style.display = 'inline-flex'; }
            else             { badge.style.display = 'none'; }
        }
        if (payList) payList.innerHTML = '<div class="qc-loading-pay">⏳ ' + T.loading_pay + '</div>';
        if (payBtn)  payBtn.disabled = true;

        /* reset payment selection */
        (qs('#qc-pay-list') ? overlay.querySelectorAll('.qc-pay-opt') : []).forEach(function (o) {
            o.classList.remove('selected');
            var chk = o.querySelector('.qc-pay-check');
            if (chk) chk.textContent = '';
        });

        showStep(1);
        overlay.classList.add('qc-show');
        document.body.style.overflow = 'hidden';
        if (nameEl) nameEl.focus();

        loadLeaflet().then(function () { setTimeout(initMap, 200); });
        loadPaymentMethods();
    }

    function closeDialog() {
        if (overlay) overlay.classList.remove('qc-show');
        document.body.style.overflow = '';
    }

    /* ── Map ──────────────────────────────────────────────────── */
    function makeIcon() {
        return window.L.divIcon({
            html: '<div style="width:26px;height:26px;background:#f7b731;border:3px solid #fff;border-radius:50% 50% 50% 0;transform:rotate(-45deg);box-shadow:0 2px 8px rgba(0,0,0,.3)"></div>',
            className: '', iconSize: [26, 26], iconAnchor: [13, 26],
        });
    }

    function initMap() {
        var L = window.L;
        if (!L) return;
        var mapEl = document.getElementById('qc-map');
        if (!mapEl) return;

        if (!leafMap) {
            leafMap = L.map(mapEl, { zoomControl: true }).setView([26.8, 30.8], 5);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
                { attribution: '© OpenStreetMap' }).addTo(leafMap);
            leafMap.on('click', function (e) {
                placeMarker(e.latlng.lat, e.latlng.lng);
                reverseGeocode(e.latlng.lat, e.latlng.lng);
            });
        } else {
            leafMap.invalidateSize();
        }

        fetch('https://ipapi.co/json/')
            .then(function (r) { return r.json(); })
            .then(function (g) {
                if (!g || !g.latitude) return;
                leafMap.setView([g.latitude, g.longitude], 13);
                placeMarker(g.latitude, g.longitude);
                locData = { latitude: g.latitude, longitude: g.longitude,
                            city: g.city || '', country_code: g.country_code || '' };
                reverseGeocode(g.latitude, g.longitude);
            }).catch(function () {});
    }

    function placeMarker(lat, lng) {
        if (!window.L || !leafMap) return;
        if (leafMarker) leafMap.removeLayer(leafMarker);
        leafMarker = window.L.marker([lat, lng], { icon: makeIcon(), draggable: true }).addTo(leafMap);
        leafMarker.on('dragend', function (e) {
            var p = e.target.getLatLng();
            locData.latitude = p.lat; locData.longitude = p.lng;
            reverseGeocode(p.lat, p.lng);
        });
        locData.latitude = lat; locData.longitude = lng;
    }

    function reverseGeocode(lat, lng) {
        var hintEl = qs('#qc-map-hint');
        var adrBox = qs('#qc-address');
        if (hintEl) { hintEl.style.color = '#aaa'; hintEl.textContent = '📍 ' + T.loading_adr; }
        var lang = isAr ? 'ar,en' : 'en';
        fetch('https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=' + lat + '&lon=' + lng + '&accept-language=' + lang)
            .then(function (r) { return r.json(); })
            .then(function (d) {
                if (!d) return;
                var a = d.address || {};
                locData.street       = [a.road, a.house_number].filter(Boolean).join(' ');
                locData.city         = a.city || a.town || a.village || a.county || '';
                locData.country_code = (a.country_code || '').toUpperCase();
                locData.full_address = d.display_name || '';
                var hEl = qs('#qc-map-hint');
                if (hEl) { hEl.style.color = '#555'; hEl.textContent = '📍 ' + (locData.full_address || T.loc_selected); }
                var aBox = qs('#qc-address');
                if (aBox && !addrManuallyEdited) {
                    aBox.value = locData.full_address || '';
                    aBox.classList.add('map-filled');
                    setTimeout(function () { if (aBox) aBox.classList.remove('map-filled'); }, 1500);
                }
            })
            .catch(function () {
                var hEl = qs('#qc-map-hint');
                if (hEl) { hEl.style.color = '#c00'; hEl.textContent = T.adr_err; }
            });
    }

    function locateMe() {
        var btn = qs('#qc-locate');
        if (!navigator.geolocation) { toast(T.no_geo, 'err'); return; }
        if (btn) { btn.textContent = T.locating; btn.disabled = true; }
        navigator.geolocation.getCurrentPosition(function (pos) {
            if (leafMap) leafMap.setView([pos.coords.latitude, pos.coords.longitude], 15);
            placeMarker(pos.coords.latitude, pos.coords.longitude);
            reverseGeocode(pos.coords.latitude, pos.coords.longitude);
            if (btn) { btn.textContent = T.my_loc; btn.disabled = false; }
        }, function () {
            toast(T.loc_err, 'err');
            if (btn) { btn.textContent = T.my_loc; btn.disabled = false; }
        });
    }

    /* ── Payment methods ──────────────────────────────────────── */
    function loadPaymentMethods() {
        rpc('/shop/fast_buy/payment_methods', {})
            .then(function (res) {
                var methods = (res && res.success && res.methods && res.methods.length)
                    ? res.methods
                    : [{ id: -1, name: isAr ? 'الدفع عند الاستلام' : 'Cash on Delivery', code: 'cod', image: '' }];
                renderPaymentMethods(methods);
            })
            .catch(function () {
                renderPaymentMethods([{ id: -1, name: isAr ? 'الدفع عند الاستلام' : 'Cash on Delivery', code: 'cod', image: '' }]);
            });
    }

    /* icons keyed by method name keywords */
    function getPayIcon(name, code) {
        var n = (name || '').toLowerCase();
        var c = (code || '').toLowerCase();
        if (n.includes('knet') || c.includes('knet'))
            return { bg:'#fff', src:'https://upload.wikimedia.org/wikipedia/en/thumb/9/9e/KNET_logo.png/220px-KNET_logo.png', emoji:'🏦' };
        if (n.includes('apple') || c.includes('apple'))
            return { bg:'#000', src:'https://developer.apple.com/assets/elements/icons/apple-pay/apple-pay.svg', emoji:'🍎' };
        if (n.includes('google') || c.includes('google'))
            return { bg:'#fff', src:'https://upload.wikimedia.org/wikipedia/commons/thumb/f/f2/Google_Pay_Logo.svg/320px-Google_Pay_Logo.svg.png', emoji:'🔵' };
        if (n.includes('samsung') || c.includes('samsung'))
            return { bg:'#1428a0', src:'https://upload.wikimedia.org/wikipedia/commons/thumb/2/24/Samsung_Pay_wordmark.svg/320px-Samsung_Pay_wordmark.svg.png', emoji:'📱' };
        if (n.includes('visa') || n.includes('mastercard') || n.includes('credit') || c.includes('card'))
            return { bg:'#1a1f71', src:'https://upload.wikimedia.org/wikipedia/commons/thumb/5/5e/Visa_Inc._logo.svg/320px-Visa_Inc._logo.svg.png', emoji:'💳' };
        if (n.includes('cash') || n.includes('delivery') || n.includes('استلام') || c === 'cod')
            return { bg:'#e8f5e9', src:'', emoji:'💵' };
        return { bg:'#f5f5f5', src:'', emoji:'💳' };
    }

    function renderPaymentMethods(methods) {
        if (!overlay) return;
        var list = overlay.querySelector('#qc-pay-list');
        if (!list) return;

        var html = '';
        for (var i = 0; i < methods.length; i++) {
            var m    = methods[i];
            var info = getPayIcon(m.name, m.code);
            var imgSrc = info.src || m.image || '';

            var iconContent = imgSrc
                ? '<img src="' + imgSrc + '" alt="' + m.name + '" ' +
                  'style="width:100%;height:100%;object-fit:contain;" ' +
                  'onerror="this.style.display=\'none\';this.nextSibling.style.display=\'flex\'"/>' +
                  '<span style="display:none;width:100%;height:100%;align-items:center;justify-content:center;font-size:22px">' + info.emoji + '</span>'
                : '<span style="font-size:24px;line-height:1">' + info.emoji + '</span>';

            html += '<div class="qc-pay-opt" data-pay-id="' + m.id + '" ' +
                    'data-pay-code="' + m.code + '" data-pay-name="' + m.name + '">' +
                    '<div class="qc-pay-icon" style="background:' + info.bg + ';padding:4px;overflow:hidden">' + iconContent + '</div>' +
                    '<span class="qc-pay-name">' + m.name + '</span>' +
                    '<span class="qc-pay-check"></span>' +
                    '</div>';
        }
        list.innerHTML = html || '<div class="qc-loading-pay" style="color:#c00">لا توجد وسائل دفع</div>';

        var opts = list.querySelectorAll('.qc-pay-opt');
        opts.forEach(function (opt) {
            opt.addEventListener('click', function () {
                opts.forEach(function (o) {
                    o.classList.remove('selected');
                    var chk = o.querySelector('.qc-pay-check');
                    if (chk) chk.textContent = '';
                });
                opt.classList.add('selected');
                var myChk = opt.querySelector('.qc-pay-check');
                if (myChk) myChk.textContent = '✓';
                selectedPayment     = opt.dataset.payCode;
                selectedPaymentName = opt.dataset.payName;
                var payBtn = overlay ? overlay.querySelector('#qc-pay-btn') : null;
                if (payBtn) payBtn.disabled = false;
            });
        });
    }

    /* ── Step 1 → 2 ──────────────────────────────────────────── */
    function goToPayment() {
        var nameEl  = qs('#qc-name');
        var phoneEl = qs('#qc-phone');
        var adrEl   = qs('#qc-address');
        var name    = nameEl  ? nameEl.value.trim()  : '';
        var phone   = phoneEl ? phoneEl.value.trim() : '';
        var address = (adrEl  ? adrEl.value.trim()   : '') || locData.full_address || '';
        if (!name)  { toast(T.err_name,  'err'); if (nameEl)  nameEl.focus();  return; }
        if (!phone) { toast(T.err_phone, 'err'); if (phoneEl) phoneEl.focus(); return; }
        lastOrderData = {
            name: name, phone: phone,
            latitude:     locData.latitude     || '',
            longitude:    locData.longitude    || '',
            street:       locData.street       || '',
            city:         locData.city         || '',
            country_code: locData.country_code || '',
            full_address: address,
        };
        showStep(2);
    }

    /* ── Step 2: place order ──────────────────────────────────── */
    function doPlaceOrder() {
        if (!selectedPayment) { toast(T.select_pay, 'err'); return; }
        var btn = qs('#qc-pay-btn');
        if (btn) { btn.disabled = true; btn.innerHTML = '<div class="qc-spin"></div>&nbsp;' + T.processing; }

        rpc('/shop/fast_buy/submit', Object.assign({}, lastOrderData, { payment_method: selectedPayment }))
            .then(function (res) {
                if (res && res.success) {
                    showSuccessStep(res);
                } else {
                    toast(res && res.error === 'empty_cart' ? T.empty_cart : T.went_wrong, 'err');
                    if (btn) { btn.disabled = false; btn.textContent = T.btn_pay; }
                }
            }).catch(function (err) {
                toast('Error: ' + err.message, 'err');
                if (btn) { btn.disabled = false; btn.textContent = T.btn_pay; }
            });
    }

    /* ── Step 3: success ──────────────────────────────────────── */
    function showSuccessStep(res) {
        var el = qs('#qc-order-details');
        if (!el) return;

        var orderName   = res.order_name || res.order_id || '—';
        var amount      = (res.amount_total && res.amount_total !== '0.000') ? res.amount_total + ' ' + (res.currency || '') : '—';
        var productName = res.product_name || currentProduct.name || '—';
        var productUrl  = res.product_url  || currentProduct.url  || '';

        var rows = [
            { k: T.order_num,     v: '#' + orderName, big: false },
            { k: T.order_total,   v: amount,           big: true  },
            { k: T.contact_phone, v: lastOrderData ? lastOrderData.phone : '—', big: false },
            { k: T.delivery_addr, v: lastOrderData ? (lastOrderData.full_address || '—') : '—', big: false },
            { k: T.payment_lbl,   v: selectedPaymentName || selectedPayment || '—', big: false },
        ];
        el.innerHTML = rows.map(function (r) {
            return '<div class="qc-order-row' + (r.big ? ' qc-order-total' : '') + '">' +
                   '<span class="k">' + r.k + '</span><span class="v">' + r.v + '</span></div>';
        }).join('');

        /* build WhatsApp footer button */
        var footer = qs('#qc-s3-footer');
        if (footer) {
            var waMsg = isAr
                ? 'مرحباً، لقد أتممت طلبي عبر الموقع.\n' +
                  '📦 المنتج: ' + productName + '\n' +
                  '🔢 رقم الطلب: #' + orderName + '\n' +
                  '💰 المبلغ: ' + amount + '\n' +
                  '📞 الهاتف: ' + (lastOrderData ? lastOrderData.phone : '') + '\n' +
                  '📍 العنوان: ' + (lastOrderData ? (lastOrderData.full_address || '') : '') + '\n' +
                  (productUrl ? '🔗 رابط المنتج: ' + productUrl : '')
                : 'Hello, I just completed an order on your website.\n' +
                  '📦 Product: ' + productName + '\n' +
                  '🔢 Order #: ' + orderName + '\n' +
                  '💰 Total: ' + amount + '\n' +
                  '📞 Phone: ' + (lastOrderData ? lastOrderData.phone : '') + '\n' +
                  '📍 Address: ' + (lastOrderData ? (lastOrderData.full_address || '') : '') + '\n' +
                  (productUrl ? '🔗 Product: ' + productUrl : '');

            var waUrl = 'https://wa.me/?text=' + encodeURIComponent(waMsg);
            footer.innerHTML =
                '<div style="display:flex;gap:10px;">' +
                  '<button class="qc-btn" id="qc-done-btn" style="flex:1;font-size:13px;padding:12px 8px;">' + T.continue_shop + '</button>' +
                  '<a href="' + waUrl + '" target="_blank" rel="noopener" ' +
                     'style="flex:1;position:relative;display:flex;align-items:center;justify-content:center;gap:7px;' +
                            'padding:12px 8px;border:none;border-radius:12px;text-decoration:none;' +
                            'background:linear-gradient(135deg,#25d366,#128c7e);color:#fff;' +
                            'font-size:13px;font-weight:700;font-family:inherit;' +
                            'box-shadow:0 4px 14px rgba(37,211,102,.3);transition:all .18s;">' +
                    '<span style="position:absolute;top:-9px;' + (isAr?'left':'right') + ':10px;' +
                          'background:#e53935;color:#fff;font-size:10px;font-weight:700;' +
                          'padding:2px 7px;border-radius:10px;">' + (isAr ? 'واتساب' : 'WhatsApp') + '</span>' +
                    '<svg width="18" height="18" viewBox="0 0 24 24" fill="#fff" style="flex-shrink:0">' +
                      '<path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z"/>' +
                      '<path d="M12 0C5.373 0 0 5.373 0 12c0 2.123.554 4.118 1.528 5.845L0 24l6.337-1.51A11.956 11.956 0 0012 24c6.627 0 12-5.373 12-12S18.627 0 12 0zm0 21.818a9.818 9.818 0 01-5.007-1.374l-.36-.214-3.73.889.933-3.617-.235-.372A9.818 9.818 0 0112 2.182c5.42 0 9.818 4.398 9.818 9.818 0 5.42-4.398 9.818-9.818 9.818z"/>' +
                    '</svg>' +
                    (isAr ? 'تواصل معنا' : 'Contact Us') +
                  '</a>' +
                '</div>';

            /* re-bind continue button */
            var doneBtn = qs('#qc-done-btn');
            if (doneBtn) doneBtn.addEventListener('click', function () {
                closeDialog(); window.location.href = '/shop';
            });
        }

        showStep(3);
    }

    /* ── Button click handler ─────────────────────────────────── */
    function bindButtons() {
        document.body.addEventListener('click', function (e) {
            var btn = e.target.closest('.qc-open-btn');
            if (!btn) return;
            e.preventDefault();
            e.stopPropagation();

            var wrap = btn.closest('[data-template-id]') || btn.closest('[data-default-product-id]');

            // Read IDs — prefer variant input, fall back to template
            var pid = 0;

            // 1. Odoo variant selector (most accurate for multi-variant products)
            var vi = document.querySelector('input[name="product_id"]')
                  || document.querySelector('input[name="product-id"]');
            if (vi) pid = parseInt(vi.value || '0', 10);

            // 2. data-default-product-id (product.product id from template)
            if (!pid && wrap)
                pid = parseInt(wrap.getAttribute('data-default-product-id') || '0', 10);

            // 3. data-template-id (product.template id — controller resolves variant)
            if (!pid && wrap)
                pid = parseInt(wrap.getAttribute('data-template-id') || '0', 10);

            if (!pid) { toast(T.prod_unavail, 'err'); return; }

            var origHtml = btn.innerHTML;
            btn.disabled = true;
            btn.innerHTML = '<span style="display:inline-block;width:14px;height:14px;border:2px solid rgba(0,0,0,.25);border-top-color:#3e2000;border-radius:50%;animation:qc-spin .7s linear infinite;vertical-align:middle;margin-right:6px"></span>' + T.wait;

            rpc('/shop/fb/add/' + pid, {})
                .then(function (res) {
                    btn.disabled = false;
                    btn.innerHTML = origHtml;
                    if (res && res.success) {
                        openDialog(res.product_id, res.product_name, res.product_url || window.location.href);
                    } else {
                        toast(T.prod_unavail, 'err');
                    }
                })
                .catch(function (err) {
                    btn.disabled = false;
                    btn.innerHTML = origHtml;
                    toast('Error: ' + err.message, 'err');
                });
        });
    }

    bindButtons();

    } /* end init() */

    /* ── Boot — try all strategies ───────────────────────────── */
    function tryInit() {
        if (tryInit._done) return;
        tryInit._done = true;
        init();
    }
    tryInit._done = false;

    if (document.readyState === 'complete' || document.readyState === 'interactive') {
        setTimeout(tryInit, 0);
    }
    document.addEventListener('DOMContentLoaded', tryInit);
    window.addEventListener('load', tryInit);
    /* Odoo-specific: fires after all OWL components mount */
    document.addEventListener('odoo:ready', tryInit);
    setTimeout(tryInit, 2000); /* absolute fallback */
}
