/* ── Global RPC helper ───────────────────────────────────── */
function jsonRpc(route, params) {
    var fn = window.dpJsonRpc;
    if (fn) return fn(route, params);
    return new Promise(function(resolve, reject) {
        var xhr = new XMLHttpRequest();
        xhr.open('POST', route, true);
        xhr.withCredentials = true;
        xhr.setRequestHeader('Content-Type', 'application/json');
        xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
        xhr.onload = function() {
            try { var d = JSON.parse(xhr.responseText); resolve(d.result); }
            catch(e) { reject(e); }
        };
        xhr.onerror = function() { reject(new Error('Network error')); };
        xhr.send(JSON.stringify({jsonrpc:'2.0',method:'call',id:1,params:params||{}}));
    });
}
/* ── Global RPC helper — used by all IIFEs ──────────────── */
window.dpJsonRpc = function dpJsonRpc(route, params) {
    return new Promise(function(resolve, reject) {
        var xhr = new XMLHttpRequest();
        xhr.open('POST', route, true);
        xhr.withCredentials = true;
        xhr.setRequestHeader('Content-Type', 'application/json');
        xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
        var meta = document.querySelector('meta[name="csrf-token"]');
        if (meta) xhr.setRequestHeader('X-Csrf-Token', meta.getAttribute('content'));
        xhr.onload = function() {
            try {
                var d = JSON.parse(xhr.responseText);
                if (d.error) {
                    var msg = (d.error.data && d.error.data.message) || d.error.message || 'RPC error';
                    reject(new Error(msg));
                } else {
                    resolve(d.result);
                }
            } catch(e) { reject(e); }
        };
        xhr.onerror = function() { reject(new Error('Network error')); };
        xhr.send(JSON.stringify({ jsonrpc: '2.0', method: 'call', id: 1, params: params || {} }));
    });
};

/* =====================================================
   Delivery Carrier Portal — JS
   Features: Leaflet map, signature pad, confirm delivery,
             fail delivery, assign driver
   Bilingual: AR / EN based on <html lang>
   ===================================================== */
(function () {
    'use strict';

    var isAr = (document.documentElement.lang || '').startsWith('ar') ||
               document.documentElement.dir === 'rtl';

    var T = {
        ar: {
            locating:        'جارٍ تحديد موقعك…',
            map_drag:        'اسحب الدبوس لتحديد موقعك',
            open_maps:       '🗺️ فتح في خرائط Google',
            no_location:     'لا يوجد موقع محدد',
            confirm_title:   'تأكيد التسليم',
            confirm_msg:     'هل تأكد تسليم هذا الطلب للعميل؟',
            fail_title:      'تسجيل فشل التوصيل',
            reason_ph:       'أدخل سبب فشل التوصيل…',
            deliver_btn:     '✅ نعم، تم التسليم',
            fail_btn:        '❌ تأكيد الفشل',
            cancel:          'إلغاء',
            processing:      'جارٍ المعالجة…',
            success:         '✅ تم بنجاح',
            error:           '❌ حدث خطأ، حاول مجدداً',
            clear_sig:       'مسح',
            proof_tap:       'اضغط لرفع صورة إثبات',
            sig_label:       'توقيع العميل',
            assign_done:     'تم تخصيص السائق',
        },
        en: {
            locating:        'Locating…',
            map_drag:        'Drag pin to set delivery location',
            open_maps:       '🗺️ Open in Google Maps',
            no_location:     'No location set',
            confirm_title:   'Confirm Delivery',
            confirm_msg:     'Confirm this order was delivered to the customer?',
            fail_title:      'Register Delivery Failure',
            reason_ph:       'Enter reason for failure…',
            deliver_btn:     '✅ Yes, Delivered',
            fail_btn:        '❌ Confirm Failure',
            cancel:          'Cancel',
            processing:      'Processing…',
            success:         '✅ Done',
            error:           '❌ Error, please try again',
            clear_sig:       'Clear',
            proof_tap:       'Tap to upload proof image',
            sig_label:       'Customer Signature',
            assign_done:     'Driver assigned',
        },
    };
    var t = isAr ? T.ar : T.en;

    // ─── Helpers ──────────────────────────────────────────────────────────
    function $(sel, ctx) { return (ctx || document).querySelector(sel); }
    function $$(sel, ctx) { return Array.from((ctx || document).querySelectorAll(sel)); }



    function showAlert(msg, type) {
        var existing = $('.dp-flash-alert');
        if (existing) existing.remove();
        var div = document.createElement('div');
        div.className = 'dp-alert ' + (type || 'success') + ' dp-flash-alert';
        div.style.cssText = 'position:fixed;top:20px;inset-inline-start:50%;transform:translateX(-50%);z-index:99999;min-width:260px;text-align:center;';
        div.textContent = msg;
        document.body.appendChild(div);
        setTimeout(function () { div.remove(); }, 3000);
    }

    // ─── Leaflet Map (Order Detail — Driver View) ─────────────────────────
    function initOrderMap() {
        var mapEl = document.getElementById('dp-order-map');
        if (!mapEl) return;

        var lat = parseFloat(mapEl.dataset.lat || '0');
        var lng = parseFloat(mapEl.dataset.lng || '0');
        var addr = mapEl.dataset.addr || '';

        if (!lat && !lng) {
            // No coordinates saved — show fallback
            var hint = $('.dp-map-hint');
            if (hint) hint.textContent = t.no_location;
            mapEl.closest('.dp-map-container').style.background = '#f1f5f9';
            return;
        }

        loadLeaflet(function () {
            var map = L.map('dp-order-map', {
                center: [lat, lng],
                zoom: 15,
                zoomControl: false,
                attributionControl: false,
                dragging: false,
                scrollWheelZoom: false,
                doubleClickZoom: false,
                touchZoom: false,
            });

            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                maxZoom: 19,
            }).addTo(map);

            L.control.zoom({ position: isAr ? 'bottomleft' : 'bottomright' }).addTo(map);

            var pinIcon = L.divIcon({
                className: '',
                html: '<div class="dp-map-pin"></div>',
                iconSize: [28, 28],
                iconAnchor: [14, 28],
            });

            L.marker([lat, lng], { icon: pinIcon }).addTo(map);

            // Show address hint
            var hint = $('.dp-map-hint');
            if (hint) hint.textContent = addr || (lat.toFixed(4) + ', ' + lng.toFixed(4));

            // Google Maps link
            var gmLink = $('.dp-open-map-btn');
            if (gmLink) {
                gmLink.href = 'https://www.google.com/maps/search/?api=1&query=' + lat + ',' + lng;
                gmLink.textContent = t.open_maps;
                gmLink.style.display = 'inline-flex';
            }
        });
    }

    function loadLeaflet(cb) {
        if (typeof L !== 'undefined') { cb(); return; }
        if (!document.querySelector('link[href*="leaflet"]')) {
            var link = document.createElement('link');
            link.rel = 'stylesheet';
            link.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
            document.head.appendChild(link);
        }
        var s = document.createElement('script');
        s.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
        s.onload = cb;
        s.onerror = function () { console.error('[DP] Leaflet failed to load'); };
        document.head.appendChild(s);
    }

    // ─── Signature Pad ────────────────────────────────────────────────────
    function initSignaturePad() {
        var canvas = document.getElementById('dp-signature-canvas');
        if (!canvas) return;

        var ctx = canvas.getContext('2d');
        var drawing = false;
        var lastX = 0, lastY = 0;

        function getPos(e) {
            var rect = canvas.getBoundingClientRect();
            var src = e.touches ? e.touches[0] : e;
            return {
                x: (src.clientX - rect.left) * (canvas.width / rect.width),
                y: (src.clientY - rect.top) * (canvas.height / rect.height),
            };
        }

        function onStart(e) {
            e.preventDefault();
            drawing = true;
            var p = getPos(e);
            lastX = p.x; lastY = p.y;
        }
        function onMove(e) {
            e.preventDefault();
            if (!drawing) return;
            var p = getPos(e);
            ctx.beginPath();
            ctx.moveTo(lastX, lastY);
            ctx.lineTo(p.x, p.y);
            ctx.strokeStyle = '#1e293b';
            ctx.lineWidth = 2;
            ctx.lineCap = 'round';
            ctx.stroke();
            lastX = p.x; lastY = p.y;
        }
        function onEnd() { drawing = false; }

        canvas.addEventListener('mousedown', onStart);
        canvas.addEventListener('mousemove', onMove);
        canvas.addEventListener('mouseup', onEnd);
        canvas.addEventListener('mouseleave', onEnd);
        canvas.addEventListener('touchstart', onStart, { passive: false });
        canvas.addEventListener('touchmove', onMove, { passive: false });
        canvas.addEventListener('touchend', onEnd);

        // Clear button
        var clearBtn = document.getElementById('dp-sig-clear');
        if (clearBtn) {
            clearBtn.textContent = t.clear_sig;
            clearBtn.addEventListener('click', function () {
                ctx.clearRect(0, 0, canvas.width, canvas.height);
            });
        }
    }

    // ─── Proof Image Upload ───────────────────────────────────────────────
    function initProofUpload() {
        var area = document.getElementById('dp-proof-area');
        var input = document.getElementById('dp-proof-input');
        var preview = document.getElementById('dp-proof-preview');
        if (!area || !input) return;

        area.querySelector('.dp-proof-tap') && (area.querySelector('.dp-proof-tap').textContent = t.proof_tap);

        area.addEventListener('click', function () { input.click(); });
        input.addEventListener('change', function () {
            if (!input.files[0]) return;
            var reader = new FileReader();
            reader.onload = function (e) {
                if (preview) {
                    preview.src = e.target.result;
                    preview.style.display = 'block';
                }
            };
            reader.readAsDataURL(input.files[0]);
        });
    }

    // ─── Confirm Delivery Modal ───────────────────────────────────────────
    function initConfirmDelivery() {
        var btn = document.getElementById('dp-btn-confirm');
        if (!btn) return;
        var orderId = btn.dataset.orderId;

        btn.addEventListener('click', function () {
            showDeliveryModal(orderId);
        });
    }

    function showDeliveryModal(orderId) {
        var modal = document.createElement('div');
        modal.className = 'dp-modal-backdrop';
        modal.innerHTML = `
          <div class="dp-modal" dir="${isAr ? 'rtl' : 'ltr'}">
            <button class="dp-modal-close" id="dp-modal-close-x">✕</button>
            <div class="dp-modal-title">${t.confirm_title}</div>
            <p style="font-size:13px;color:var(--dp-muted);margin-bottom:20px;">${t.confirm_msg}</p>

            <div class="dp-field">
              <label>${t.proof_tap}</label>
              <div class="dp-proof-area" id="dp-m-proof-area" style="cursor:pointer;">
                <div class="icon">📷</div>
                <div class="dp-proof-tap">${t.proof_tap}</div>
              </div>
              <input type="file" id="dp-m-proof-input" accept="image/*" style="display:none;">
              <img id="dp-m-proof-preview" class="dp-proof-preview">
            </div>

            <div class="dp-field">
              <label>${t.sig_label}</label>
              <canvas id="dp-m-sig-canvas" width="400" height="120"
                style="border:1px solid var(--dp-border);border-radius:8px;width:100%;height:120px;cursor:crosshair;touch-action:none;background:#fff;"></canvas>
              <div class="dp-sig-actions">
                <button class="dp-btn sm secondary" id="dp-m-sig-clear">${t.clear_sig}</button>
              </div>
            </div>

            <div style="display:flex;gap:10px;margin-top:16px;">
              <button class="dp-btn primary full lg" id="dp-m-confirm">${t.deliver_btn}</button>
              <button class="dp-btn secondary full" id="dp-m-cancel">${t.cancel}</button>
            </div>
          </div>
        `;
        document.body.appendChild(modal);

        // Close
        modal.querySelector('#dp-modal-close-x').onclick = function () { modal.remove(); };
        modal.querySelector('#dp-m-cancel').onclick = function () { modal.remove(); };
        modal.addEventListener('click', function (e) { if (e.target === modal) modal.remove(); });

        // Proof upload inside modal
        var mProofArea = modal.querySelector('#dp-m-proof-area');
        var mProofInput = modal.querySelector('#dp-m-proof-input');
        var mProofPreview = modal.querySelector('#dp-m-proof-preview');
        mProofArea.addEventListener('click', function () { mProofInput.click(); });
        mProofInput.addEventListener('change', function () {
            if (!mProofInput.files[0]) return;
            var reader = new FileReader();
            reader.onload = function (e) {
                mProofPreview.src = e.target.result;
                mProofPreview.style.display = 'block';
            };
            reader.readAsDataURL(mProofInput.files[0]);
        });

        // Signature inside modal
        var sigCanvas = modal.querySelector('#dp-m-sig-canvas');
        var sigCtx = sigCanvas.getContext('2d');
        var sigDrawing = false, sigLX = 0, sigLY = 0;
        function sigPos(e) {
            var rect = sigCanvas.getBoundingClientRect();
            var src = e.touches ? e.touches[0] : e;
            return { x: (src.clientX - rect.left) * (sigCanvas.width / rect.width), y: (src.clientY - rect.top) * (sigCanvas.height / rect.height) };
        }
        sigCanvas.addEventListener('mousedown', function (e) { sigDrawing = true; var p = sigPos(e); sigLX = p.x; sigLY = p.y; });
        sigCanvas.addEventListener('mousemove', function (e) {
            if (!sigDrawing) return;
            var p = sigPos(e);
            sigCtx.beginPath(); sigCtx.moveTo(sigLX, sigLY); sigCtx.lineTo(p.x, p.y);
            sigCtx.strokeStyle = '#1e293b'; sigCtx.lineWidth = 2; sigCtx.lineCap = 'round'; sigCtx.stroke();
            sigLX = p.x; sigLY = p.y;
        });
        sigCanvas.addEventListener('mouseup', function () { sigDrawing = false; });
        sigCanvas.addEventListener('touchstart', function (e) { e.preventDefault(); sigDrawing = true; var p = sigPos(e); sigLX = p.x; sigLY = p.y; }, { passive: false });
        sigCanvas.addEventListener('touchmove', function (e) {
            e.preventDefault(); if (!sigDrawing) return;
            var p = sigPos(e);
            sigCtx.beginPath(); sigCtx.moveTo(sigLX, sigLY); sigCtx.lineTo(p.x, p.y);
            sigCtx.strokeStyle = '#1e293b'; sigCtx.lineWidth = 2; sigCtx.lineCap = 'round'; sigCtx.stroke();
            sigLX = p.x; sigLY = p.y;
        }, { passive: false });
        sigCanvas.addEventListener('touchend', function () { sigDrawing = false; });
        modal.querySelector('#dp-m-sig-clear').onclick = function () { sigCtx.clearRect(0, 0, sigCanvas.width, sigCanvas.height); };

        // Submit
        modal.querySelector('#dp-m-confirm').addEventListener('click', function () {
            var confirmBtn = this;
            confirmBtn.textContent = t.processing;
            confirmBtn.disabled = true;

            // Get proof image base64
            var proofBase64 = null;
            var proofName = null;
            if (mProofInput.files[0]) {
                var reader = new FileReader();
                reader.onload = function (e) {
                    proofBase64 = e.target.result.split(',')[1];
                    proofName = mProofInput.files[0].name;
                    doSubmit();
                };
                reader.readAsDataURL(mProofInput.files[0]);
            } else {
                doSubmit();
            }

            function doSubmit() {
                // Get signature
                var sigData = sigCanvas.toDataURL('image/png').split(',')[1];
                // Check if canvas is blank
                var blank = document.createElement('canvas');
                blank.width = sigCanvas.width; blank.height = sigCanvas.height;
                if (sigData === blank.toDataURL('image/png').split(',')[1]) sigData = null;

                jsonRpc('/delivery-portal/confirm-delivery', {
                    order_id: parseInt(orderId),
                    proof_image: proofBase64 || null,
                    proof_image_name: proofName || null,
                    proof_signature: sigData || null,
                    notes: '',
                }).then(function (result) {
                    modal.remove();
                    if (result && result.success) {
                        showAlert(t.success, 'success');
                        setTimeout(function () { window.location.reload(); }, 1200);
                    } else {
                        showAlert(t.error, 'error');
                    }
                }).catch(function () {
                    showAlert(t.error, 'error');
                    confirmBtn.textContent = t.deliver_btn;
                    confirmBtn.disabled = false;
                });
            }
        });
    }

    // ─── Fail Delivery Modal ──────────────────────────────────────────────
    function initFailDelivery() {
        var btn = document.getElementById('dp-btn-fail');
        if (!btn) return;
        var orderId = btn.dataset.orderId;

        btn.addEventListener('click', function () {
            var modal = document.createElement('div');
            modal.className = 'dp-modal-backdrop';
            modal.innerHTML = `
              <div class="dp-modal" dir="${isAr ? 'rtl' : 'ltr'}">
                <button class="dp-modal-close" id="dp-fail-close">✕</button>
                <div class="dp-modal-title">${t.fail_title}</div>
                <div class="dp-field">
                  <label>${isAr ? 'سبب الفشل' : 'Failure Reason'}</label>
                  <textarea id="dp-fail-reason" rows="3" placeholder="${t.reason_ph}"
                    style="resize:none;"></textarea>
                </div>
                <div style="display:flex;gap:10px;">
                  <button class="dp-btn red full lg" id="dp-fail-submit">${t.fail_btn}</button>
                  <button class="dp-btn secondary full" id="dp-fail-cancel">${t.cancel}</button>
                </div>
              </div>
            `;
            document.body.appendChild(modal);
            modal.querySelector('#dp-fail-close').onclick = function () { modal.remove(); };
            modal.querySelector('#dp-fail-cancel').onclick = function () { modal.remove(); };
            modal.addEventListener('click', function (e) { if (e.target === modal) modal.remove(); });

            modal.querySelector('#dp-fail-submit').addEventListener('click', function () {
                var reason = modal.querySelector('#dp-fail-reason').value;
                this.textContent = t.processing;
                this.disabled = true;
                var self = this;
                jsonRpc('/delivery-portal/fail-delivery', {
                    order_id: parseInt(orderId),
                    reason: reason,
                }).then(function (result) {
                    modal.remove();
                    if (result && result.success) {
                        showAlert(t.success, 'success');
                        setTimeout(function () { window.location.reload(); }, 1200);
                    } else {
                        showAlert(t.error, 'error');
                    }
                }).catch(function () {
                    showAlert(t.error, 'error');
                    self.textContent = t.fail_btn;
                    self.disabled = false;
                });
            });
        });
    }

    // ─── Assign Driver ────────────────────────────────────────────────────
    function initAssignDriver() {
        var sel = document.getElementById('dp-driver-select');
        var btn = document.getElementById('dp-driver-assign-btn');
        if (!sel || !btn) return;
        var orderId = btn.dataset.orderId;

        btn.addEventListener('click', function () {
            var driverId = sel.value;
            if (!driverId) return;
            btn.textContent = t.processing;
            btn.disabled = true;
            var self = this;
            jsonRpc('/delivery-portal/assign-driver', {
                order_id: parseInt(orderId),
                driver_id: parseInt(driverId),
            }).then(function (result) {
                if (result && result.success) {
                    showAlert(t.assign_done + ': ' + (result.driver_name || ''), 'success');
                    setTimeout(function () { window.location.reload(); }, 1200);
                } else {
                    showAlert(t.error, 'error');
                    btn.textContent = isAr ? 'تخصيص' : 'Assign';
                    btn.disabled = false;
                }
            }).catch(function () {
                showAlert(t.error, 'error');
                self.textContent = isAr ? 'تخصيص' : 'Assign';
                self.disabled = false;
            });
        });
    }

    // ─── Init ─────────────────────────────────────────────────────────────
    // Script is served inline via <script src> — DOM is already ready
    function dpInit() {
        initOrderMap();
        initSignaturePad();
        initProofUpload();
        initConfirmDelivery();
        initFailDelivery();
        initAssignDriver();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', dpInit);
    } else {
        dpInit();
    }

})();

/* ── Mark Failed as Returned ───────────────────────────────── */
(function () {
    function initMarkReturned() {
        document.querySelectorAll('.dp-btn-mark-returned').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var orderId = this.dataset.orderId;
                var self = this;
                var isAr = (document.documentElement.lang || '').startsWith('ar');
                if (!confirm(isAr ? 'تأكيد استلام الطلب من شركة التوصيل؟' : 'Confirm receiving this order back from carrier?')) return;
                self.disabled = true;
                self.textContent = isAr ? 'جارٍ…' : 'Processing…';
                jsonRpc('/delivery-portal/mark-returned', { order_id: parseInt(orderId) })
                .then(function (r) {
                    if (r && r.success) {
                        window.location.reload();
                    } else {
                        self.disabled = false;
                        self.textContent = 'Confirm Received';
                        alert('Error occurred');
                    }
                }).catch(function() {
                    self.disabled = false;
                    self.textContent = 'Confirm Received';
                    alert('Connection error');
                });
            });
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initMarkReturned);
    } else {
        initMarkReturned();
    }
})();

/* ── Assign Dialog ───────────────────────────────────────── */
(function () {
    var isAr = (document.documentElement.lang || '').startsWith('ar');

    var jsonRpc2 = jsonRpc;

    function initAssignDialog() {
        var openBtn = document.getElementById('dp-btn-open-assign');
        var unassignBtn = document.getElementById('dp-btn-unassign-driver');
        var driversEl = document.getElementById('dp-drivers-data');

        // Parse drivers list from data attribute
        var driversRaw = driversEl ? driversEl.dataset.drivers : '';
        var drivers = [];
        if (driversRaw) {
            drivers = driversRaw.split(',').map(function(d) {
                var parts = d.split('|');
                return { id: parseInt(parts[0]), name: parts[1] || '' };
            }).filter(function(d) { return d.id && d.name; });
        }

        // Open assign dialog
        if (openBtn) {
            openBtn.addEventListener('click', function () {
                var orderId = openBtn.dataset.orderId;
                var currentDriverId = parseInt(openBtn.dataset.driverId) || 0;
                var currentDriverName = openBtn.dataset.driverName || '';
                var currentStatus = openBtn.dataset.status || '';
                var currentPayment = openBtn.dataset.payment || '';

                showAssignDialog(orderId, currentDriverId, currentDriverName, currentStatus, currentPayment, drivers);
            });
        }

        // Unassign button
        if (unassignBtn) {
            unassignBtn.addEventListener('click', function () {
                var orderId = unassignBtn.dataset.orderId;
                var driverName = unassignBtn.dataset.driverName;
                var msg = isAr
                    ? 'إلغاء تخصيص السائق "' + driverName + '" من هذا الطلب؟'
                    : 'Unassign driver "' + driverName + '" from this order?';
                if (!confirm(msg)) return;
                unassignBtn.disabled = true;
                unassignBtn.textContent = isAr ? 'جارٍ…' : 'Processing…';
                jsonRpc2('/delivery-portal/unassign-driver', { order_id: parseInt(orderId) })
                    .then(function (r) {
                        if (r && r.success) { window.location.reload(); }
                        else {
                            alert(isAr ? 'حدث خطأ' : 'Error');
                            unassignBtn.disabled = false;
                        }
                    });
            });
        }
    }

    function showAssignDialog(orderId, currentDriverId, currentDriverName, currentStatus, currentPayment, drivers) {
        // Build driver options
        var driverOptions = '<option value="">' + (isAr ? '-- اختر سائق --' : '-- Select Driver --') + '</option>';
        drivers.forEach(function(d) {
            var sel = d.id === currentDriverId ? ' selected' : '';
            driverOptions += '<option value="' + d.id + '"' + sel + '>' + d.name + '</option>';
        });

        // Status badge
        var statusBadge = '';
        if (currentDriverId) {
            statusBadge = '<div class="dp-alert success" style="margin-bottom:12px;">' +
                '✅ ' + (isAr ? 'السائق الحالي: ' : 'Current Driver: ') + currentDriverName + '</div>';
        }

        // Payment badge
        var paymentInfo = currentPayment === 'cash'
            ? '<span class="dp-tag dp-tag-red">' + (isAr ? 'كاش' : 'Cash') + '</span>'
            : '<span class="dp-tag dp-tag-green">' + (isAr ? 'أونلاين' : 'Online') + '</span>';

        var modal = document.createElement('div');
        modal.className = 'dp-modal-backdrop';
        modal.innerHTML =
            '<div class="dp-modal" dir="' + (isAr ? 'rtl' : 'ltr') + '" style="max-width:400px;padding:24px;">' +
                '<button class="dp-modal-close" id="dp-assign-modal-close">✕</button>' +
                '<div class="dp-modal-title">🚚 ' + (isAr ? 'تخصيص سائق' : 'Assign Driver') + '</div>' +
                statusBadge +
                '<div class="dp-info-row" style="margin-bottom:16px;">' +
                    '<span class="dp-info-key">' + (isAr ? 'طريقة الدفع' : 'Payment') + '</span>' +
                    paymentInfo +
                '</div>' +
                (drivers.length > 0
                    ? '<div class="dp-field">' +
                        '<label>' + (isAr ? 'اختر السائق' : 'Select Driver') + '</label>' +
                        '<select id="dp-assign-driver-select" style="width:100%;padding:9px 12px;border:1px solid var(--dp-border);border-radius:7px;font-size:13px;">' +
                        driverOptions +
                        '</select>' +
                      '</div>' +
                      '<div style="display:flex;gap:10px;margin-top:16px;">' +
                        '<button class="dp-btn primary full lg" id="dp-assign-confirm-btn">' +
                            '✅ ' + (isAr ? 'تأكيد التخصيص' : 'Confirm Assignment') +
                        '</button>' +
                        '<button class="dp-btn secondary full" id="dp-assign-cancel-btn">' +
                            (isAr ? 'إلغاء' : 'Cancel') +
                        '</button>' +
                      '</div>'
                    : '<div class="dp-alert error">' + (isAr ? 'لا يوجد سائقون متاحون' : 'No drivers available') + '</div>'
                ) +
            '</div>';

        document.body.appendChild(modal);

        modal.querySelector('#dp-assign-modal-close').onclick = function () { modal.remove(); };
        modal.addEventListener('click', function (e) { if (e.target === modal) modal.remove(); });

        var cancelBtn = modal.querySelector('#dp-assign-cancel-btn');
        if (cancelBtn) cancelBtn.onclick = function () { modal.remove(); };

        var confirmBtn = modal.querySelector('#dp-assign-confirm-btn');
        if (confirmBtn) {
            confirmBtn.addEventListener('click', function () {
                var sel = modal.querySelector('#dp-assign-driver-select');
                var driverId = sel ? parseInt(sel.value) : 0;
                if (!driverId) {
                    alert(isAr ? 'اختر سائقاً أولاً' : 'Please select a driver');
                    return;
                }
                confirmBtn.textContent = isAr ? 'جارٍ المعالجة…' : 'Processing…';
                confirmBtn.disabled = true;
                jsonRpc2('/delivery-portal/assign-driver', {
                    order_id: parseInt(orderId),
                    driver_id: driverId,
                }).then(function (r) {
                    modal.remove();
                    if (r && r.success) {
                        // Show success flash
                        var flash = document.createElement('div');
                        flash.className = 'dp-alert success dp-flash-alert';
                        flash.style.cssText = 'position:fixed;top:20px;inset-inline-start:50%;transform:translateX(-50%);z-index:99999;min-width:260px;text-align:center;';
                        flash.textContent = '✅ ' + (isAr ? 'تم التخصيص بنجاح' : 'Driver assigned successfully');
                        document.body.appendChild(flash);
                        setTimeout(function () { window.location.reload(); }, 1000);
                    } else {
                        alert(r && r.error ? r.error : (isAr ? 'حدث خطأ' : 'Error occurred'));
                    }
                }).catch(function () {
                    alert(isAr ? 'حدث خطأ' : 'Error');
                    confirmBtn.disabled = false;
                });
            });
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initAssignDialog);
    } else {
        initAssignDialog();
    }
})();

/* ── Payment Link + WhatsApp/SMS ─────────────────────────── */
(function () {
    var isAr = (document.documentElement.lang || '').startsWith('ar');

    function rpcCall(route, params, callback) {
        jsonRpc(route, params)
            .then(function(r) { callback(null, r); })
            .catch(function(e) { callback(e, null); });
    }

    function initPaymentLink() {
        var btn = document.getElementById('dp-btn-payment-link');
        console.log('[PaymentLink] init, btn found:', !!btn);
        if (!btn) return;

        btn.addEventListener('click', function () {
            var orderId   = btn.dataset.orderId;
            var orderName = btn.dataset.orderName;
            var amount    = btn.dataset.amount;
            var phone     = btn.dataset.partnerPhone || '';
            console.log('[PaymentLink] clicked, orderId:', orderId);

            btn.disabled = true;
            btn.innerHTML = '⏳ ' + (isAr ? 'جارٍ التحميل…' : 'Loading…');

            rpcCall('/delivery-portal/get-payment-link', { order_id: parseInt(orderId) }, function(err, r) {
                console.log('[PaymentLink] response:', err, r);
                btn.disabled = false;
                btn.innerHTML = '💳 ' + (isAr ? 'إرسال رابط دفع' : 'Send Payment Link');
                if (err) {
                    console.error('[PaymentLink] error:', err);
                    alert(isAr ? 'حدث خطأ في الاتصال' : 'Connection error: ' + err);
                    return;
                }
                if (r && r.success && r.link) {
                    showPaymentLinkDialog(orderId, r.order_name || orderName, r.amount || amount, r.partner_phone || phone, r.link);
                } else {
                    var errMsg = r && r.error ? r.error : (isAr ? 'حدث خطأ' : 'Error: no link');
                    console.warn('[PaymentLink] no link:', r);
                    alert(errMsg);
                }
            });
        });
    }

    function showPaymentLinkDialog(orderId, orderName, amount, phone, paymentUrl) {
        var amountFmt = parseFloat(amount || 0).toFixed(3);

        var waMsg = encodeURIComponent(
            (isAr ? 'مرحباً، يمكنك دفع طلبك ' : 'Hello, you can pay for your order ') +
            orderName + ' (KD ' + amountFmt + ') ' +
            (isAr ? 'عبر الرابط: ' : 'via link: ') +
            paymentUrl
        );

        var modal = document.createElement('div');
        modal.className = 'dp-modal-backdrop';
        modal.innerHTML =
            '<div class="dp-modal" dir="' + (isAr ? 'rtl' : 'ltr') + '" style="max-width:420px;">' +
                '<button class="dp-modal-close" id="dp-plink-close">✕</button>' +
                '<div class="dp-modal-title">💳 ' + (isAr ? 'إرسال رابط الدفع' : 'Send Payment Link') + '</div>' +

                '<div class="dp-info-card" style="margin-bottom:12px;background:#f0fdf4;border-color:#16a34a;">' +
                    '<div class="dp-info-row">' +
                        '<span class="dp-info-key">' + (isAr ? 'الطلب' : 'Order') + '</span>' +
                        '<span class="dp-info-val" style="font-family:monospace;">' + orderName + '</span>' +
                    '</div>' +
                    '<div class="dp-info-row">' +
                        '<span class="dp-info-key">' + (isAr ? 'المبلغ' : 'Amount') + '</span>' +
                        '<span class="dp-info-val" style="color:var(--dp-green);font-weight:800;">KD ' + amountFmt + '</span>' +
                    '</div>' +
                '</div>' +
                '<div style="margin-bottom:12px;">' +
                    '<div style="font-size:10px;font-weight:700;color:#475569;margin-bottom:4px;">' +
                        (isAr ? '🔗 رابط الدفع:' : '🔗 Payment Link:') +
                    '</div>' +
                    '<div style="display:flex;gap:6px;align-items:center;">' +
                        '<input id="dp-plink-url" type="text" readonly value="' + paymentUrl + '"' +
                            ' style="flex:1;padding:7px 10px;border:1px solid #bfdbfe;border-radius:6px;font-size:10px;' +
                            'color:#1d4ed8;background:#eff6ff;font-family:monospace;cursor:pointer;"' +
                            ' onclick="this.select()"/>' +
                    '</div>' +
                    '<div style="font-size:9px;color:#94a3b8;margin-top:3px;">' +
                        (isAr ? 'انقر على الخانة لتحديد الرابط كاملاً' : 'Click the field to select the full link') +
                    '</div>' +
                '</div>' +

                '<div class="dp-field">' +
                    '<label>' + (isAr ? 'رقم هاتف العميل' : 'Customer Phone') + '</label>' +
                    '<input type="tel" id="dp-plink-phone" class="dp-search-input" style="padding:9px 12px;" value="' + phone + '" dir="ltr"/>' +
                '</div>' +

                '<div style="display:flex;flex-direction:column;gap:10px;margin-top:16px;">' +
                    '<a id="dp-plink-whatsapp" target="_blank" rel="noopener"' +
                    '   class="dp-btn full lg" style="background:#25D366;color:#fff;text-align:center;justify-content:center;">' +
                    '   📱 ' + (isAr ? 'إرسال عبر واتساب' : 'Send via WhatsApp') +
                    '</a>' +
                    '<a id="dp-plink-sms" class="dp-btn full" style="background:#3b82f6;color:#fff;text-align:center;justify-content:center;">' +
                    '   💬 ' + (isAr ? 'إرسال رسالة SMS' : 'Send SMS') +
                    '</a>' +
                    '<button id="dp-plink-copy" class="dp-btn secondary full">' +
                    '   📋 ' + (isAr ? 'نسخ الرابط' : 'Copy Link') +
                    '</button>' +
                    '<button id="dp-plink-cancel" class="dp-btn secondary full">' + (isAr ? 'إغلاق' : 'Close') + '</button>' +
                '</div>' +
            '</div>';

        document.body.appendChild(modal);

        function buildLinks() {
            var ph = modal.querySelector('#dp-plink-phone').value.replace(/\s/g, '');
            var waPhone = ph.replace(/^\+/, '').replace(/^00/, '');
            var waLink = 'https://wa.me/' + waPhone + '?text=' + waMsg;
            var smsLink = 'sms:' + ph + '?body=' + decodeURIComponent(waMsg);

            modal.querySelector('#dp-plink-whatsapp').href = waLink;
            modal.querySelector('#dp-plink-sms').href = smsLink;
        }

        buildLinks();
        modal.querySelector('#dp-plink-phone').addEventListener('input', buildLinks);

        modal.querySelector('#dp-plink-close').onclick = function () { modal.remove(); };
        modal.querySelector('#dp-plink-cancel').onclick = function () { modal.remove(); };
        modal.addEventListener('click', function (e) { if (e.target === modal) modal.remove(); });

        modal.querySelector('#dp-plink-copy').addEventListener('click', function () {
            var b = modal.querySelector('#dp-plink-copy');
            try {
                if (navigator.clipboard && navigator.clipboard.writeText) {
                    navigator.clipboard.writeText(portalUrl).then(function () {
                        b.textContent = '✅ ' + (isAr ? 'تم النسخ' : 'Copied!');
                        setTimeout(function () { b.textContent = '📋 ' + (isAr ? 'نسخ الرابط' : 'Copy Link'); }, 2000);
                    }).catch(function() {
                        var inp = modal.querySelector('#dp-plink-url');
                        inp.select(); document.execCommand('copy');
                        b.textContent = '✅ Copied!';
                        setTimeout(function () { b.textContent = '📋 Copy Link'; }, 2000);
                    });
                } else {
                    var inp = modal.querySelector('#dp-plink-url');
                    inp.select(); document.execCommand('copy');
                    b.textContent = '✅ Copied!';
                    setTimeout(function () { b.textContent = '📋 Copy Link'; }, 2000);
                }
            } catch(e) { alert(portalUrl); }
        });
    }

    // Use setTimeout to ensure DOM is fully ready
    setTimeout(initPaymentLink, 100);
})();

/* ── GPS Location on Confirm/Sign ──────────────────────────── */
(function () {
    function captureGpsOnAction() {
        // When confirm delivery modal opens, capture GPS
        var origConfirm = window._dpConfirmDelivery;

        function getGps(callback) {
            if (!navigator.geolocation) { callback(null); return; }
            navigator.geolocation.getCurrentPosition(
                function (pos) { callback({ lat: pos.coords.latitude, lng: pos.coords.longitude }); },
                function () { callback(null); },
                { timeout: 5000, maximumAge: 60000 }
            );
        }

        // Hook into confirm delivery AJAX
        var origFetch = window.fetch;
        window.fetch = function (url, opts) {
            if (url && url.includes('/delivery-portal/confirm-delivery') && opts && opts.body) {
                try {
                    var body = JSON.parse(opts.body);
                    if (body.params && !body.params.gps_captured) {
                        // Try to get GPS
                        getGps(function (gps) {
                            if (gps) {
                                body.params.delivery_lat = gps.lat;
                                body.params.delivery_lng = gps.lng;
                                body.params.gps_captured = true;
                                opts.body = JSON.stringify(body);
                            }
                            origFetch.call(window, url, opts);
                        });
                        return new Promise(function (resolve) {
                            setTimeout(function () {
                                resolve(origFetch.call(window, url, opts));
                            }, 3000);
                        });
                    }
                } catch (e) {}
            }
            return origFetch.call(window, url, opts);
        };
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', captureGpsOnAction);
    } else {
        captureGpsOnAction();
    }
})();

/* ── Returns: Schedule Dialog ────────────────────────────── */
(function () {
    var isAr = (document.documentElement.lang || '').startsWith('ar');



    function initReturns() {
        document.querySelectorAll('.dp-btn-schedule-return').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var orderId = btn.dataset.orderId;
                var orderName = btn.dataset.orderName;
                var currentStatus = btn.dataset.currentStatus;

                if (currentStatus === 'return_scheduled') {
                    // Mark as in transit
                    if (!confirm(isAr ? 'تأكيد إرسال المنتج في الطريق ليلو؟' : 'Confirm product is now in transit to Uellow?')) return;
                    btn.disabled = true;
                    jsonRpc('/delivery-portal/return-in-transit', { order_id: parseInt(orderId) })
                        .then(function (r) {
                            if (r && r.success) window.location.reload();
                        });
                    return;
                }

                // Show schedule dialog
                var modal = document.createElement('div');
                modal.className = 'dp-modal-backdrop';
                modal.innerHTML =
                    '<div class="dp-modal" dir="' + (isAr ? 'rtl' : 'ltr') + '" style="max-width:380px;">' +
                        '<button class="dp-modal-close" id="dp-ret-close">✕</button>' +
                        '<div class="dp-modal-title">📅 ' + (isAr ? 'تحديد موعد إرجاع ' : 'Schedule Return for ') + orderName + '</div>' +
                        '<div class="dp-field">' +
                            '<label>' + (isAr ? 'تاريخ الإرجاع' : 'Return Date') + '</label>' +
                            '<input type="datetime-local" id="dp-ret-date" style="width:100%;padding:9px 12px;border:1px solid var(--dp-border);border-radius:7px;font-size:13px;margin-bottom:10px;"/>' +
                        '</div>' +
                        '<div class="dp-field">' +
                            '<label>' + (isAr ? 'ملاحظات' : 'Notes') + '</label>' +
                            '<textarea id="dp-ret-notes" rows="2" style="width:100%;padding:9px 12px;border:1px solid var(--dp-border);border-radius:7px;font-size:12px;resize:none;" placeholder="' + (isAr ? 'تفاصيل إضافية…' : 'Additional details…') + '"></textarea>' +
                        '</div>' +
                        '<div style="display:flex;gap:8px;margin-top:14px;">' +
                            '<button class="dp-btn primary full lg" id="dp-ret-confirm">' +
                                '✅ ' + (isAr ? 'تأكيد الموعد' : 'Confirm Schedule') +
                            '</button>' +
                            '<button class="dp-btn secondary" id="dp-ret-cancel">' + (isAr ? 'إلغاء' : 'Cancel') + '</button>' +
                        '</div>' +
                    '</div>';
                document.body.appendChild(modal);

                modal.querySelector('#dp-ret-close').onclick = function () { modal.remove(); };
                modal.querySelector('#dp-ret-cancel').onclick = function () { modal.remove(); };
                modal.addEventListener('click', function (e) { if (e.target === modal) modal.remove(); });

                modal.querySelector('#dp-ret-confirm').addEventListener('click', function () {
                    var dateVal = modal.querySelector('#dp-ret-date').value;
                    var notes   = modal.querySelector('#dp-ret-notes').value;
                    if (!dateVal) { alert(isAr ? 'اختر التاريخ أولاً' : 'Please select a date'); return; }
                    jsonRpc('/delivery-portal/schedule-return', {
                        order_id: parseInt(orderId),
                        scheduled_date: dateVal,
                        notes: notes,
                    }).then(function (r) {
                        modal.remove();
                        if (r && r.success) window.location.reload();
                        else alert(isAr ? 'حدث خطأ' : 'Error');
                    });
                });
            });
        });

        // View signature
        document.querySelectorAll('.dp-btn-view-signature').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var orderId = btn.dataset.orderId;
                var modal = document.createElement('div');
                modal.className = 'dp-modal-backdrop';
                modal.innerHTML =
                    '<div class="dp-modal" style="max-width:400px;">' +
                        '<button class="dp-modal-close" onclick="this.closest(\'.dp-modal-backdrop\').remove()">✕</button>' +
                        '<div class="dp-modal-title">✍️ ' + (isAr ? 'توقيع موظف Uellow' : 'Uellow Staff Signature') + '</div>' +
                        '<img src="/delivery-portal/return-signature/' + orderId + '" style="max-width:100%;border:1px solid var(--dp-border);border-radius:8px;"/>' +
                    '</div>';
                document.body.appendChild(modal);
                modal.addEventListener('click', function (e) { if (e.target === modal) modal.remove(); });
            });
        });
    }

    setTimeout(initReturns, 100);
})();

/* ── Start Delivery Button ───────────────────────────────── */
(function () {
    var isAr = (document.documentElement.lang || '').startsWith('ar');



    function initStartDelivery() {
        var btn = document.getElementById('dp-btn-start-delivery');
        if (!btn) return;
        var orderId = btn.dataset.orderId;

        btn.addEventListener('click', function () {
            btn.disabled = true;
            btn.textContent = isAr ? 'جارٍ المعالجة…' : 'Processing…';

            jsonRpc('/delivery-portal/start-delivery', { order_id: parseInt(orderId) })
                .then(function (r) {
                    if (!r || !r.success) {
                        alert(isAr ? 'حدث خطأ' : 'Error');
                        btn.disabled = false;
                        return;
                    }

                    // Show WhatsApp dialog
                    var phone = r.phone || '';
                    var msgAr = encodeURIComponent(r.msg_ar || '');
                    var msgEn = encodeURIComponent(r.msg_en || '');
                    var waPhone = phone.replace(/^00/, '').replace(/^\+/, '');
                    var waLinkAr = 'https://wa.me/' + waPhone + '?text=' + msgAr;
                    var waLinkEn = 'https://wa.me/' + waPhone + '?text=' + msgEn;

                    var modal = document.createElement('div');
                    modal.className = 'dp-modal-backdrop';
                    modal.innerHTML =
                        '<div class="dp-modal" dir="' + (isAr ? 'rtl' : 'ltr') + '" style="max-width:400px;padding:24px;">' +
                            '<div class="dp-modal-title">📱 ' + (isAr ? 'إرسال إشعار للعميل' : 'Notify Customer') + '</div>' +
                            '<div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;padding:12px;margin-bottom:14px;font-size:12px;color:#15803d;">' +
                                '✅ ' + (isAr ? 'تم تغيير الحالة إلى "في الطريق"' : 'Status changed to "Out for Delivery"') +
                            '</div>' +
                            '<div style="font-size:12px;color:var(--dp-muted);margin-bottom:12px;">' +
                                (isAr ? 'أرسل رسالة واتساب للعميل لإعلامه بموعد الوصول:' : 'Send a WhatsApp message to notify the customer:') +
                            '</div>' +
                            '<div style="display:flex;flex-direction:column;gap:8px;">' +
                                '<a href="' + waLinkAr + '" target="_blank" rel="noopener"' +
                                '   class="dp-btn full lg" style="background:#25D366;color:#fff;justify-content:center;text-decoration:none;padding:14px 20px;font-size:15px;margin-bottom:10px;">' +
                                '   📱 ' + (isAr ? 'إرسال بالعربي' : 'Send in Arabic') +
                                '</a>' +
                                '<a href="' + waLinkEn + '" target="_blank" rel="noopener"' +
                                '   class="dp-btn full" style="background:#128C7E;color:#fff;justify-content:center;text-decoration:none;padding:14px 20px;font-size:15px;margin-bottom:10px;">' +
                                '   📱 ' + (isAr ? 'إرسال بالإنجليزي' : 'Send in English') +
                                '</a>' +
                                '<button id="dp-start-skip" class="dp-btn secondary full" style="padding:14px 20px;font-size:14px;">' +
                                    (isAr ? 'تخطّي — بدون إشعار' : 'Skip — No notification') +
                                '</button>' +
                            '</div>' +
                        '</div>';
                    document.body.appendChild(modal);

                    modal.querySelector('#dp-start-skip').onclick = function () {
                        modal.remove();
                        window.location.reload();
                    };
                    // Close on WA link click
                    modal.querySelectorAll('a').forEach(function (a) {
                        a.addEventListener('click', function () {
                            setTimeout(function () { modal.remove(); window.location.reload(); }, 1500);
                        });
                    });
                });
        });
    }

    setTimeout(initStartDelivery, 100);
})();

/* ── Mobile Hamburger Menu ───────────────────────────────── */
(function () {
    function initHamburger() {
        var hamburger = document.getElementById('dp-hamburger');
        var sidebar   = document.getElementById('dp-sidebar');
        var overlay   = document.getElementById('dp-overlay');
        if (!hamburger || !sidebar) return;

        hamburger.addEventListener('click', function () {
            sidebar.classList.toggle('open');
            if (overlay) overlay.classList.toggle('open');
            hamburger.textContent = sidebar.classList.contains('open') ? '✕' : '☰';
        });
        if (overlay) {
            overlay.addEventListener('click', function () {
                sidebar.classList.remove('open');
                overlay.classList.remove('open');
                hamburger.textContent = '☰';
            });
        }
    }
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initHamburger);
    } else {
        initHamburger();
    }
})();

/* ── Fix Modal Rendering on Desktop ─────────────────────── */
(function () {
    // Override modal creation to append to body directly
    var _orig = document.createElement.bind(document);
    // Patch: after any modal-backdrop is added, ensure it's in body
    var observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(m) {
            m.addedNodes.forEach(function(node) {
                if (node.classList && node.classList.contains('dp-modal-backdrop')) {
                    if (node.parentNode !== document.body) {
                        document.body.appendChild(node);
                    }
                    document.body.classList.add('dp-modal-open');
                }
            });
            m.removedNodes.forEach(function(node) {
                if (node.classList && node.classList.contains('dp-modal-backdrop')) {
                    document.body.classList.remove('dp-modal-open');
                }
            });
        });
    });
    observer.observe(document.body, { childList: true, subtree: true });
})();

/* ── Touch Swipe for Tables ──────────────────────────────── */
(function () {
    function initTableSwipe() {
        document.querySelectorAll('.dp-table-wrap').forEach(function(wrap) {
            var startX = 0, scrollLeft = 0, isDragging = false;

            wrap.addEventListener('touchstart', function(e) {
                startX = e.touches[0].pageX - wrap.offsetLeft;
                scrollLeft = wrap.scrollLeft;
                isDragging = true;
            }, { passive: true });

            wrap.addEventListener('touchmove', function(e) {
                if (!isDragging) return;
                var x = e.touches[0].pageX - wrap.offsetLeft;
                wrap.scrollLeft = scrollLeft - (x - startX);
            }, { passive: true });

            wrap.addEventListener('touchend', function() {
                isDragging = false;
            });
        });
    }
    setTimeout(initTableSwipe, 200);
})();

/* ── Remittance New Page ─────────────────────────────────── */
(function () {
    // Use global or define locally
    var jsonRpc = window.dpJsonRpc || function(route, params) {
        return new Promise(function(resolve, reject) {
            var xhr = new XMLHttpRequest();
            xhr.open('POST', route, true);
            xhr.withCredentials = true;
            xhr.setRequestHeader('Content-Type', 'application/json');
            xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
            var meta = document.querySelector('meta[name="csrf-token"]');
            if (meta) xhr.setRequestHeader('X-Csrf-Token', meta.getAttribute('content'));
            xhr.onload = function() {
                try {
                    var d = JSON.parse(xhr.responseText);
                    if (d.error) reject(new Error(d.error.message || 'RPC error'));
                    else resolve(d.result);
                } catch(e) { reject(e); }
            };
            xhr.onerror = function() { reject(new Error('Network error')); };
            xhr.send(JSON.stringify({jsonrpc:'2.0',method:'call',id:1,params:params||{}}));
        });
    };
    function init() {
        var submitBtn = document.getElementById('dp-submit-remittance');
        if (!submitBtn) return;

        var selectAll = document.getElementById('dp-select-all');
        var totalEl   = document.getElementById('dp-selected-total');
        var countEl   = document.getElementById('dp-selected-count');

        function getChecked() {
            return Array.from(document.querySelectorAll('.dp-order-check:checked'));
        }

        function updateTotals() {
            var checked = getChecked();
            var total = checked.reduce(function(s, c) {
                return s + parseFloat(c.dataset.amount || c.getAttribute('data-amount') || 0);
            }, 0);
            if (totalEl) totalEl.textContent = 'KD ' + total.toFixed(3);
            if (countEl) countEl.textContent = checked.length + ' orders';
            submitBtn.disabled = checked.length === 0;
            submitBtn.style.opacity = checked.length === 0 ? '0.5' : '1';
        }

        // Checkbox listeners
        document.querySelectorAll('.dp-order-check').forEach(function(cb) {
            cb.addEventListener('change', function() {
                var all = document.querySelectorAll('.dp-order-check');
                if (selectAll) {
                    selectAll.checked = Array.from(all).every(function(c) { return c.checked; });
                    selectAll.indeterminate = !selectAll.checked &&
                        Array.from(all).some(function(c) { return c.checked; });
                }
                updateTotals();
            });
        });

        // Select all listener
        if (selectAll) {
            selectAll.addEventListener('change', function() {
                document.querySelectorAll('.dp-order-check').forEach(function(cb) {
                    cb.checked = selectAll.checked;
                });
                updateTotals();
            });
        }

        // Check all on init
        document.querySelectorAll('.dp-order-check').forEach(function(cb) {
            cb.checked = true;
        });
        if (selectAll) selectAll.checked = true;
        updateTotals();

        // Submit
        submitBtn.addEventListener('click', function(e) {
            e.preventDefault();
            if (submitBtn.disabled) return;

            var checked = getChecked();
            var orderIds = checked.map(function(c) {
                return parseInt(c.dataset.orderId || c.getAttribute('data-order-id'));
            }).filter(Boolean);

            if (!orderIds.length) {
                alert('Please select at least one order');
                return;
            }

            var carrierRefEl = document.getElementById('dp-carrier-ref');
            var carrierRef   = carrierRefEl ? carrierRefEl.value.trim() : '';

            submitBtn.disabled = true;
            submitBtn.textContent = 'Sending…';

            jsonRpc('/delivery-portal/remittance/submit',
                    { order_ids: orderIds, carrier_ref: carrierRef })
            .then(function(r) {
                if (r && r.success) {
                    window.location.href = '/delivery-portal/remittance/' + r.remittance_id;
                } else {
                    alert((r && r.error) ? r.error : 'An error occurred');
                    submitBtn.disabled = false;
                    submitBtn.textContent = 'Send to Uellow ←';
                }
            })
            .catch(function(err) {
                console.error('Remittance error:', err);
                alert('Connection error. Please try again.');
                submitBtn.disabled = false;
                submitBtn.textContent = 'Send to Uellow ←';
            });
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();

/* ── Trip Receive Buttons ────────────────────────────────── */
(function () {

    function init() {
        // Receive All
        var receiveAll = document.getElementById('dp-receive-all');
        if (receiveAll) {
            receiveAll.addEventListener('click', function () {
                var btns = document.querySelectorAll('.dp-btn-receive');
                if (!btns.length) { alert('No pending orders to receive'); return; }
                receiveAll.disabled = true;
                receiveAll.textContent = 'Processing…';
                var promises = Array.from(btns).map(function (btn) {
                    return jsonRpc('/delivery-portal/receive-order', {
                        order_id: parseInt(btn.dataset.orderId),
                        line_id:  parseInt(btn.dataset.lineId) || 0,
                    });
                });
                Promise.all(promises).then(function () {
                    window.location.reload();
                }).catch(function (e) {
                    alert('Error: ' + e.message);
                    receiveAll.disabled = false;
                    receiveAll.textContent = '✅ Receive All';
                });
            });
        }

        // Per-row Received
        document.querySelectorAll('.dp-btn-receive').forEach(function (btn) {
            btn.addEventListener('click', function () {
                btn.disabled = true;
                jsonRpc('/delivery-portal/receive-order', {
                    order_id: parseInt(btn.dataset.orderId),
                    line_id:  parseInt(btn.dataset.lineId) || 0,
                }).then(function () {
                    window.location.reload();
                }).catch(function (e) {
                    alert('Error: ' + e.message);
                    btn.disabled = false;
                });
            });
        });

        // Per-row No
        document.querySelectorAll('.dp-btn-no-receive').forEach(function (btn) {
            btn.addEventListener('click', function () {
                if (!confirm('Mark as not received (Failed — Returned)?')) return;
                btn.disabled = true;
                jsonRpc('/delivery-portal/no-receive-order', {
                    order_id: parseInt(btn.dataset.orderId),
                    line_id:  parseInt(btn.dataset.lineId) || 0,
                }).then(function () {
                    window.location.reload();
                }).catch(function (e) {
                    alert('Error: ' + e.message);
                    btn.disabled = false;
                });
            });
        });
    }
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else { init(); }
})();
