/* uellow_checkout checkout.js v4 -- ASCII-safe, no onerror */
(function (w, d) {
  'use strict';

  /* Only run on checkout pages */
  var path = w.location.pathname;
  var onPage = (
    path.indexOf('/shop/cart')          >= 0 ||
    path.indexOf('/shop/checkout')      >= 0 ||
    path.indexOf('/shop/payment')       >= 0 ||
    path.indexOf('/shop/order/success') >= 0 ||
    path.indexOf('/uellow/')            >= 0
  );
  if (!onPage) return;

  /* Language */
  var isAr = (d.documentElement.lang || '').indexOf('ar') >= 0 ||
             !!d.querySelector('[dir="rtl"]') ||
             path.indexOf('/ar/') >= 0;

  /* Selected payment state */
  var selPayId   = 0;
  var selPayCode = '';
  var selIsCod   = false;

  /* JSON-RPC helper */
  function rpc(url, params) {
    return fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ jsonrpc: '2.0', method: 'call', id: Date.now(), params: params }),
    }).then(function (r) { return r.json(); }).then(function (r2) { return r2.result; });
  }

  /* Render payment methods */
  /* Build an .uc-pay-opt node WITHOUT inline styles — CSS class controls
     look. User-controlled fields (name) inserted via textContent to prevent
     XSS. CSS class .uc-pay-opt + .sel state drives the entire visual. */
  function _buildPayOpt(m) {
    var opt = document.createElement('div');
    opt.className = 'uc-pay-opt';
    opt.dataset.id     = m.id;
    opt.dataset.code   = m.code || '';
    opt.dataset.isCod  = m.is_cod  ? '1' : '0';
    opt.dataset.isUpay = m.is_upay ? '1' : '0';

    var icon = document.createElement('div');
    icon.className = 'uc-pay-icon';
    var img = document.createElement('img');
    img.src = '/web/image/payment.method/' + m.id + '/image';
    img.alt = ''; // safe — decorative
    icon.appendChild(img);

    var name = document.createElement('span');
    name.className = 'uc-pay-name';
    name.textContent = m.name || ''; // safe — no HTML injection

    var check = document.createElement('span');
    check.className = 'uc-pay-check';
    check.textContent = '✓';

    opt.appendChild(icon);
    opt.appendChild(name);
    opt.appendChild(check);
    return opt;
  }

  function renderPayMethods(methods, listEls, payBtns) {
    listEls.forEach(function (el) {
      if (!el) return;
      var spin = el.querySelector('.uc-pay-loading');
      if (spin) spin.style.display = 'none';
      var body = el.querySelector('.uc-pay-body') || el;
      body.innerHTML = '';
      methods.forEach(function (m) { body.appendChild(_buildPayOpt(m)); });

      body.querySelectorAll('.uc-pay-opt').forEach(function (opt) {
        opt.addEventListener('click', function () {
          // Toggle .sel class on every mirrored list
          listEls.forEach(function (sib) {
            if (!sib) return;
            var sb = sib.querySelector('.uc-pay-body') || sib;
            sb.querySelectorAll('.uc-pay-opt').forEach(function (o) {
              o.classList.toggle('sel', o.dataset.id === opt.dataset.id);
            });
          });
          selPayId   = parseInt(opt.dataset.id || '0', 10);
          selPayCode = opt.dataset.code || '';
          selIsCod   = opt.dataset.isCod === '1';
          payBtns.forEach(function (b) { if (b) b.disabled = false; });
        });
      });
    });
  }

  /* Load payment methods */
  function loadPaymentMethods(listEls, payBtns) {
    payBtns.forEach(function (b) { if (b) b.disabled = true; });
    rpc('/uellow/payment_methods_json', {})
      .then(function (res) {
        if (res && res.methods && res.methods.length) {
          renderPayMethods(res.methods, listEls, payBtns);
        } else {
          listEls.forEach(function (el) {
            if (!el) return;
            var spin = el.querySelector('.uc-pay-loading');
            if (spin) spin.style.display = 'none';
            var body = el.querySelector('.uc-pay-body') || el;
            body.innerHTML = '<div style="padding:16px;color:#999;text-align:center">'
              + (isAr ? 'لا توجد وسائل دفع' : 'No payment methods available') + '</div>';
          });
        }
      })
      .catch(function () {
        listEls.forEach(function (el) {
          if (!el) return;
          var spin = el.querySelector('.uc-pay-loading');
          if (spin) spin.style.display = 'none';
        });
      });
  }

  // Lazy-build the spinner overlay (CSS in checkout.css)
  function _ensureOverlay() {
    var o = d.getElementById('uc-submit-overlay');
    if (o) return o;
    o = d.createElement('div');
    o.id = 'uc-submit-overlay';
    o.className = 'uc-submit-overlay';
    o.innerHTML =
      '<div class="uc-submit-overlay__box">' +
        '<div class="uc-submit-overlay__spinner"></div>' +
        '<div class="uc-submit-overlay__msg"></div>' +
      '</div>';
    d.body.appendChild(o);
    return o;
  }
  function _showOverlay(msg) {
    var o = _ensureOverlay();
    o.querySelector('.uc-submit-overlay__msg').textContent = msg || '';
    o.classList.add('on');
  }
  function _hideOverlay() {
    var o = d.getElementById('uc-submit-overlay');
    if (o) o.classList.remove('on');
  }
  // Bilingual toast — non-blocking, replaces alert()
  function _toast(en, ar, type) {
    var div = d.createElement('div');
    div.style.cssText =
      'position:fixed;top:18px;left:50%;transform:translateX(-50%);z-index:99998;' +
      'background:' + (type === 'error' ? '#ef4444' : '#412402') + ';color:#fff;' +
      'padding:11px 18px;border-radius:10px;font-size:13px;font-weight:700;' +
      'box-shadow:0 8px 24px rgba(0,0,0,.25);max-width:90vw;text-align:center;line-height:1.4;' +
      'animation:uc-toast-in .2s ease;';
    div.textContent = en + (ar ? ' · ' + ar : '');
    d.body.appendChild(div);
    setTimeout(function () { div.style.opacity = '0'; div.style.transition = 'opacity .3s'; }, 3500);
    setTimeout(function () { try { d.body.removeChild(div); } catch (e) {} }, 4000);
  }

  /* Submit order — debounced + idempotent (no double-charge on rapid taps) */
  var _submitInflight = false;
  function doPayment() {
    if (_submitInflight) return;
    if (!selPayId) {
      _toast('Please select a payment method', 'الرجاء اختيار وسيلة الدفع', 'error');
      return;
    }
    _submitInflight = true;
    // Disable every CTA on the page so duplicate clicks can't fire.
    d.querySelectorAll('.uc-confirm-btn, .uc-btn, .uc-desk-btn').forEach(function (b) {
      b.disabled = true;
    });
    _showOverlay(isAr ? 'جارٍ تأمين الدفعة…' : 'Securing your payment…');

    rpc('/uellow/checkout/submit', {
      payment_method:    selPayCode,
      payment_method_id: selPayId,
    }).then(function (res) {
      if (res && res.success && res.redirect) {
        w.location.href = res.redirect; // keep overlay visible during nav
        return;
      }
      _hideOverlay();
      _submitInflight = false;
      d.querySelectorAll('.uc-confirm-btn, .uc-btn, .uc-desk-btn').forEach(function (b) {
        b.disabled = false;
      });
      _payDialog((res && res.error) ||
        (isAr ? 'تعذّر إتمام الدفع، حاول مجدداً' : 'Payment could not be completed, please try again'));
    }).catch(function () {
      _hideOverlay();
      _submitInflight = false;
      d.querySelectorAll('.uc-confirm-btn, .uc-btn, .uc-desk-btn').forEach(function (b) {
        b.disabled = false;
      });
      _payDialog(isAr ? 'خطأ في الاتصال، تحقّق من الإنترنت وحاول مجدداً'
                      : 'Connection error, check your internet and try again');
    });
  }

  /* Professional centered payment-error dialog (replaces the red top toast) */
  function _payDialog(msg) {
    var existing = d.getElementById('uc-pay-dialog');
    if (existing) existing.remove();
    var ov = d.createElement('div');
    ov.id = 'uc-pay-dialog';
    ov.className = 'uc-dlg-ov';
    ov.setAttribute('dir', isAr ? 'rtl' : 'ltr');
    ov.innerHTML =
      '<div class="uc-dlg" role="alertdialog" aria-modal="true">' +
        '<div class="uc-dlg-ic">!</div>' +
        '<div class="uc-dlg-title">' + (isAr ? 'تعذّر إتمام الدفع' : 'Payment not completed') + '</div>' +
        '<div class="uc-dlg-msg"></div>' +
        '<button type="button" class="uc-dlg-btn">' + (isAr ? 'حسناً، اختيار وسيلة أخرى' : 'OK, choose another method') + '</button>' +
      '</div>';
    ov.querySelector('.uc-dlg-msg').textContent = msg || '';
    function close(){ ov.classList.remove('show'); setTimeout(function(){ try{ov.remove();}catch(e){} }, 180); }
    ov.querySelector('.uc-dlg-btn').addEventListener('click', close);
    ov.addEventListener('click', function (e) { if (e.target === ov) close(); });
    d.body.appendChild(ov);
    requestAnimationFrame(function(){ ov.classList.add('show'); });
  }

  /* Cart */
  function initCart() {
    var sym = 'KD';
    /* Detect currency symbol from existing totals */
    d.querySelectorAll('.uc-sum-row .v').forEach(function (el) {
      var parts = el.textContent.trim().split(' ');
      if (parts.length >= 2) sym = parts[parts.length - 1];
    });

    function fmt(n) { return parseFloat(n).toFixed(3); }

    function updateDOM(data) {
      if (!data || !data.success) return false;
      /* Per-line subtotals — find the price span in each item row */
      if (data.lines) {
        data.lines.forEach(function (l) {
          /* Update ALL qty elements with this line id (mobile + desktop) */
          d.querySelectorAll('.uc-qty[data-line-id="' + l.id + '"]').forEach(function (qEl) {
            var sp = qEl.querySelector('.uc-qty__n');
            if (sp) sp.textContent = l.qty;
            /* Find price span — it's the last span in the item row */
            var row = qEl.closest('.uc-item, .uc-desk-item');
            if (!row) return;
            /* Try multiple selectors for the subtotal span */
            var prEl = row.querySelector('.uc-item__right > span, .uc-desk-item__right > span')
                    || row.querySelector('span[style*="800"]')
                    || row.querySelectorAll('span')[row.querySelectorAll('span').length - 1];
            if (prEl) prEl.textContent = fmt(l.subtotal) + ' ' + sym;
          });
        });
      }
      /* Summary rows */
      d.querySelectorAll('.uc-sum').forEach(function (sumEl) {
        sumEl.querySelectorAll('.uc-sum-row').forEach(function (row) {
          var k = row.querySelector('.k');
          var v = row.querySelector('.v');
          if (!k || !v) return;
          var kt = k.textContent.trim();
          if (kt === 'المجموع الفرعي' || kt === 'Subtotal' || kt === 'المجموع')
            v.textContent = fmt(data.subtotal) + ' ' + sym;
          if (kt === 'الإجمالي' || kt === 'Total')
            v.textContent = fmt(data.total) + ' ' + sym;
          /* Never update shipping row in cart */
        });
      });
      return true;
    }

    /* Qty buttons — fully live, no reload */
    d.querySelectorAll('.uc-qty__btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var qEl   = btn.closest('.uc-qty');
        var lineId = qEl && parseInt(qEl.dataset.lineId || '0', 10);
        if (!lineId) return;
        var sp  = qEl.querySelector('.uc-qty__n');
        var cur = parseInt((sp && sp.textContent) || '1', 10);
        var next = btn.dataset.action === 'plus' ? cur + 1 : Math.max(0, cur - 1);

        /* Disable buttons during request */
        btn.disabled = true;
        var siblings = qEl.querySelectorAll('.uc-qty__btn');
        siblings.forEach(function (b) { b.disabled = true; });

        /* Optimistic qty display */
        if (sp) sp.textContent = next;

        var fd = new FormData();
        fd.append('line_id', lineId);
        fd.append('quantity', next);
        fetch('/uellow/cart_update', { method: 'POST', body: fd })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          siblings.forEach(function (b) { b.disabled = false; });
          if (!data || !data.success) { w.location.reload(); return; }
          if (data.removed) {
            d.querySelectorAll('[data-line-id="' + lineId + '"]').forEach(function (el) {
              var r2 = el.closest('.uc-item, .uc-desk-item');
              if (r2) r2.remove();
            });
          }
          updateDOM(data);
        })
        .catch(function () { w.location.reload(); });
      });
    });

    /* Delete button */
    d.querySelectorAll('.uc-del').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var lineId = parseInt(btn.dataset.lineId || '0', 10);
        if (!lineId) return;
        btn.disabled = true;
        var fd2 = new FormData();
        fd2.append('line_id', lineId);
        fd2.append('quantity', 0);
        fetch('/uellow/cart_update', { method: 'POST', body: fd2 })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          d.querySelectorAll('[data-line-id="' + lineId + '"]').forEach(function (el) {
            var row = el.closest('.uc-item, .uc-desk-item');
            if (row) row.remove();
          });
          if (data && data.success) updateDOM(data);
          else w.location.reload();
        })
        .catch(function () { w.location.reload(); });
      });
    });

    /* Coupon */
    var couponBtn = d.getElementById('uc-apply-coupon');
    var couponInp = d.getElementById('uc-coupon-inp');
    if (couponBtn && couponInp) {
      couponBtn.addEventListener('click', function () {
        var code = (couponInp.value || '').trim();
        if (!code) return;
        rpc('/web/dataset/call_kw', {
          model: 'sale.order', method: 'apply_coupon_code',
          args: [code], kwargs: {},
        }).then(function () { w.location.reload(); });
      });
    }

    /* To shipping */
    d.querySelectorAll('#uc-to-shipping, #uc-to-shipping-desk').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var pfx = '';
        var m = path.match(/^\/(ar|en|fr|de|es|it|tr|ku|ur)(\/|$)/);
        if (m) pfx = '/' + m[1];
        w.location.href = pfx + '/shop/checkout';
      });
    });
  }

  /* Map (address page) */
  /* Template IDs: uc-map-container / uc-map-container-desk, uc-locate-me / uc-locate-me-desk */
  /* Hidden inputs: field_map_lat, field_map_lng (mobile) / field_map_lat_desk, field_map_lng_desk (desk) */
  /* Fields: f_city, f_state, f_country, f_full_addr */
  function initOneMap(mapContainerId, latInputId, lngInputId, locBtnId) {
    var mapEl = d.getElementById(mapContainerId);
    if (!mapEl) return;
    function startMap() {
      var L   = w.L;
      var lat = 29.3797;
      var lng = 47.9734;
      /* Try GeoIP for initial position */
      try {
        var geo = w.__ucGeo || {};
        if (geo.lat) lat = geo.lat;
        if (geo.lng) lng = geo.lng;
      } catch (e) {}
      var map    = L.map(mapEl).setView([lat, lng], 12);
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: 'OpenStreetMap',
      }).addTo(map);
      var marker = L.marker([lat, lng], { draggable: true }).addTo(map);

      function applyLatLng(ll) {
        var latI = d.getElementById(latInputId);
        var lngI = d.getElementById(lngInputId);
        if (latI) latI.value = ll.lat.toFixed(6);
        if (lngI) lngI.value = ll.lng.toFixed(6);
        fetch('/uellow/reverse_geocode?lat=' + ll.lat + '&lng=' + ll.lng)
          .then(function (r) { return r.json(); })
          .then(function (geo) {
            if (geo.city) {
              var ci = d.getElementById('f_city') || d.querySelector('[name="city"]');
              if (ci && !ci.value) ci.value = geo.city;
            }
            if (geo.full_address) {
              var fa = d.getElementById('f_full_addr') || d.querySelector('[name="full_address"]');
              if (fa && !fa.value) fa.value = geo.full_address;
            }
            if (geo.country_id) {
              var cSel = d.getElementById('f_country') || d.querySelector('[name="country_id"]');
              if (cSel) {
                cSel.value = geo.country_id;
                cSel.dispatchEvent(new Event('change'));
              }
            }
          }).catch(function () {});
      }

      marker.on('dragend', function (e) { applyLatLng(e.target.getLatLng()); });
      map.on('click', function (e) { marker.setLatLng(e.latlng); applyLatLng(e.latlng); });

      var locBtn = d.getElementById(locBtnId);
      if (locBtn) {
        locBtn.addEventListener('click', function () {
          if (!navigator.geolocation) return;
          navigator.geolocation.getCurrentPosition(function (pos) {
            var ll = L.latLng(pos.coords.latitude, pos.coords.longitude);
            map.setView(ll, 15);
            marker.setLatLng(ll);
            applyLatLng(ll);
          });
        });
      }
    }
    /* Ensure map container has height */
    mapEl.style.minHeight = '220px';

    if (w.L) { startMap(); return; }
    if (!d.getElementById('leaflet-css')) {
      var css = d.createElement('link');
      css.id  = 'leaflet-css';
      css.rel = 'stylesheet';
      css.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
      d.head.appendChild(css);
    }
    if (!w._leafletCallbacks) w._leafletCallbacks = [];
    w._leafletCallbacks.push(startMap);
    if (!w._leafletLoading) {
      w._leafletLoading = true;
      var sc = d.createElement('script');
      sc.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
      sc.onload = function () {
        w._leafletLoading = false;
        (w._leafletCallbacks || []).forEach(function (fn) { fn(); });
        w._leafletCallbacks = [];
      };
      d.head.appendChild(sc);
    }
  }

  function initMap() {
    /* Load Leaflet, then use ipapi.co for location (browser-side, same as old module) */
    if (w.L) {
      _startMaps();
    } else {
      var css = d.createElement('link');
      css.rel = 'stylesheet';
      css.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
      d.head.appendChild(css);
      var sc = d.createElement('script');
      sc.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
      sc.onload = _startMaps;
      d.head.appendChild(sc);
    }

    /* Locate me buttons */
    d.querySelectorAll('#uc-locate-me, #uc-locate-me-desk').forEach(function (btn) {
      btn.addEventListener('click', function () {
        if (!navigator.geolocation) return;
        btn.disabled = true;
        navigator.geolocation.getCurrentPosition(function (pos) {
          btn.disabled = false;
          var lat = pos.coords.latitude, lng = pos.coords.longitude;
          Object.keys(_maps).forEach(function (id) {
            _maps[id].setView([lat, lng], 16);
            _placeMarker(lat, lng, _maps[id]);
          });
          _revGeo(lat, lng);
        }, function () { btn.disabled = false; });
      });
    });
  }

  var _maps = {};
  function _placeMarker(lat, lng, m) {
    if (!w.L) return;
    if (m._ucMk) m.removeLayer(m._ucMk);
    var mk = w.L.marker([lat, lng], { draggable: true }).addTo(m);
    mk.on('dragend', function (e) {
      var p = e.target.getLatLng();
      _setLatLng(p.lat, p.lng);
      _revGeo(p.lat, p.lng);
    });
    m._ucMk = mk;
    _setLatLng(lat, lng);
  }

  function _setLatLng(lat, lng) {
    var latI = d.getElementById('field_map_lat') || d.getElementById('field_map_lat_desk');
    var lngI = d.getElementById('field_map_lng') || d.getElementById('field_map_lng_desk');
    if (d.getElementById('field_map_lat'))      d.getElementById('field_map_lat').value = lat;
    if (d.getElementById('field_map_lat_desk')) d.getElementById('field_map_lat_desk').value = lat;
    if (d.getElementById('field_map_lng'))      d.getElementById('field_map_lng').value = lng;
    if (d.getElementById('field_map_lng_desk')) d.getElementById('field_map_lng_desk').value = lng;
  }

  function _revGeo(lat, lng) {
    /* Call Nominatim directly from browser - no Cloudflare issue */
    fetch('https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=' + lat + '&lon=' + lng + '&accept-language=' + (isAr ? 'ar,en' : 'en'))
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data) return;
        var a = data.address || {};
        var city    = a.city || a.town || a.village || a.county || '';
        var street  = [a.road, a.house_number].filter(Boolean).join(' ');
        var fullAddr = data.display_name || '';
        var cc = (a.country_code || '').toUpperCase();

        if (city)     d.querySelectorAll('[name="city"]').forEach(function (el) { if (!el.dataset.edited) el.value = city; });
        if (street)   d.querySelectorAll('[name="street"]').forEach(function (el) { if (!el.dataset.edited) el.value = street; });
        if (fullAddr) d.querySelectorAll('[name="full_address"]').forEach(function (el) { if (!el.dataset.edited) el.value = fullAddr; });

        /* Update Your Location label */
        var locLabel = city || fullAddr.split(',')[0] || '';
        if (locLabel) _updateGeoLabel(locLabel);

        /* Lookup country by ISO code (KW, SA, etc.) - most accurate */
        var gov = a.state || a.region || '';
        if (cc) {
          /* Use data-code attribute on options, or server lookup by code */
          /* Server route /uellow/country_id?code=KW returns {id, name} */
          fetch('/uellow/country_id?code=' + cc)
            .then(function (r) { return r.json(); })
            .then(function (res) {
              if (!res || !res.id) return;
              var cid = res.id;
              /* Set country dropdown */
              d.querySelectorAll('[name="country_id"]').forEach(function (sel) {
                if (!sel.dataset.edited) sel.value = cid;
              });
              /* Load states */
              fetch('/uellow/states?country_id=' + cid)
                .then(function (r2) { return r2.json(); })
                .then(function (states) {
                  if (!Array.isArray(states)) return;
                  d.querySelectorAll('[name="state_id"]').forEach(function (sel) {
                    if (sel.dataset.edited) return;
                    /* Populate if empty */
                    if (sel.options.length <= 1 && states.length) {
                      var ph = '<option value="">' + (isAr ? '-- اختر --' : '-- Select --') + '</option>';
                      states.forEach(function (s) { ph += '<option value="' + s.id + '">' + s.name + '</option>'; });
                      sel.innerHTML = ph;
                    }
                    if (!gov) return;
                    /* Match governorate by Arabic AND English name */
                    var govLower = gov.toLowerCase();
                    var arMap = {
                      'hawalli': 'hawalli', 'al asimah': 'asimah', 'asimah': 'asimah',
                      'al ahmadi': 'ahmadi', 'ahmadi': 'ahmadi',
                      'al farwaniyah': 'farwaniya', 'farwaniya': 'farwaniya',
                      'al jahra': 'jahra', 'jahra': 'jahra',
                      'mubarak al kabeer': 'mubarak', 'mubarak': 'mubarak',
                    };
                    /* Normalize: strip "Al " prefix */
                    var govNorm = govLower.replace(/^al /i, '').replace(/-/g, ' ').trim();
                    for (var i = 0; i < states.length; i++) {
                      var sn = states[i].name.toLowerCase().replace(/^al /i, '').trim();
                      if (sn.indexOf(govNorm.substr(0, 5)) >= 0 ||
                          govNorm.indexOf(sn.substr(0, 5)) >= 0) {
                        sel.value = states[i].id;
                        break;
                      }
                    }
                  });
                });
            }).catch(function () {});
        }
      }).catch(function () {});
  }

  function _updateGeoLabel(text) {
    /* IDs from template: uc-geo-val (mobile), uc-geo-val-desk (desktop) */
    ['uc-geo-val', 'uc-geo-val-desk'].forEach(function (id) {
      var el = d.getElementById(id);
      if (el) el.textContent = text;
    });
  }

  function _moveToLatLng(lat, lng, zoom) {
    Object.keys(_maps).forEach(function (id) {
      _maps[id].setView([lat, lng], zoom || 15);
      _placeMarker(lat, lng, _maps[id]);
    });
    _revGeo(lat, lng);
  }

  function _startMaps() {
    var L = w.L;
    if (!L) return;

    /* Default location: Kuwait City */
    var defLat = 29.3759, defLng = 47.9774;

    function buildMapEl(containerId) {
      var el = d.getElementById(containerId);
      if (!el || _maps[containerId]) return;
      el.style.cssText = 'width:100%;height:220px;display:block';
      var m = L.map(el, { zoomControl: true }).setView([defLat, defLng], 12);
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '(c) OpenStreetMap', maxZoom: 19,
      }).addTo(m);
      m.on('click', function (e) {
        _placeMarker(e.latlng.lat, e.latlng.lng, m);
        _revGeo(e.latlng.lat, e.latlng.lng);
      });
      _maps[containerId] = m;
      _placeMarker(defLat, defLng, m);
      [200, 600, 1500].forEach(function (t) { setTimeout(function () { m.invalidateSize(true); }, t); });
    }

    buildMapEl('uc-map-container');
    buildMapEl('uc-map-container-desk');

    /* Step 1: Try browser GPS first (most accurate) */
    _updateGeoLabel(isAr ? 'جاري تحديد موقعك...' : 'Detecting your location...');

    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        function (pos) {
          /* Browser GPS succeeded - use it */
          _moveToLatLng(pos.coords.latitude, pos.coords.longitude, 16);
        },
        function () {
          /* Browser GPS denied - fallback to ipapi.co */
          _fallbackIpApi();
        },
        { timeout: 8000, maximumAge: 60000, enableHighAccuracy: true }
      );
    } else {
      _fallbackIpApi();
    }

    function _fallbackIpApi() {
      fetch('https://ipapi.co/json/')
        .then(function (r) { return r.json(); })
        .then(function (g) {
          if (!g || !g.latitude) return;
          _moveToLatLng(g.latitude, g.longitude, 13);
        }).catch(function () {});
    }
  }

  /* Country/state dropdowns - template IDs: f_country, f_state, f_country_desk, f_state_desk */
  function bindCountryState(countrySelId, stateSelId) {
    var cSel = d.getElementById(countrySelId);
    var sSel = d.getElementById(stateSelId);
    if (!cSel || !sSel) return;
    cSel.addEventListener('change', function () {
      var cid = cSel.value;
      sSel.innerHTML = '<option value="">' + (isAr ? '-- اختر --' : '-- Select --') + '</option>';
      if (!cid) return;
      fetch('/uellow/states?country_id=' + cid)
        .then(function (r) { return r.json(); })
        .then(function (states) {
          if (!Array.isArray(states)) return;
          states.forEach(function (s) {
            var o = d.createElement('option');
            o.value = s.id; o.textContent = s.name;
            sSel.appendChild(o);
          });
        });
    });
  }

  function initCountry() {
    bindCountryState('f_country',      'f_state');
    bindCountryState('f_country_desk', 'f_state_desk');
    /* Auto-load states — and default to Kuwait if nothing pre-selected */
    setTimeout(function () {
      ['f_country', 'f_country_desk'].forEach(function (id) {
        var sel = d.getElementById(id);
        if (!sel) return;
        /* If no value, find Kuwait option and select it */
        if (!sel.value) {
          var kwOpt = Array.from(sel.options).find(function (o) {
            var t = o.textContent.trim();
            return t === 'Kuwait' || t === 'الكويت';
          });
          if (kwOpt) sel.value = kwOpt.value;
        }
        /* Trigger change to load states for whichever country is selected */
        if (sel.value) sel.dispatchEvent(new Event('change'));
      });
    }, 300);
  }

  /* Country/state dropdowns - template IDs: f_country, f_state, f_country_desk, f_state_desk */
  function bindCountryState(countrySelId, stateSelId) {
    var cSel = d.getElementById(countrySelId);
    var sSel = d.getElementById(stateSelId);
    if (!cSel || !sSel) return;
    cSel.addEventListener('change', function () {
      var cid = cSel.value;
      sSel.innerHTML = '<option value="">' + (isAr ? '-- اختر --' : '-- Select --') + '</option>';
      if (!cid) return;
      fetch('/uellow/states?country_id=' + cid)
        .then(function (r) { return r.json(); })
        .then(function (states) {
          if (!Array.isArray(states)) return;
          states.forEach(function (s) {
            var o = d.createElement('option');
            o.value = s.id; o.textContent = s.name;
            sSel.appendChild(o);
          });
        });
    });
  }

  function initCountry() {
    bindCountryState('f_country',      'f_state');
    bindCountryState('f_country_desk', 'f_state_desk');
    /* Auto-load states — and default to Kuwait if nothing pre-selected */
    setTimeout(function () {
      ['f_country', 'f_country_desk'].forEach(function (id) {
        var sel = d.getElementById(id);
        if (!sel) return;
        /* If no value, find Kuwait option and select it */
        if (!sel.value) {
          var kwOpt = Array.from(sel.options).find(function (o) {
            var t = o.textContent.trim();
            return t === 'Kuwait' || t === 'الكويت';
          });
          if (kwOpt) sel.value = kwOpt.value;
        }
        /* Trigger change to load states for whichever country is selected */
        if (sel.value) sel.dispatchEvent(new Event('change'));
      });
    }, 300);
  }

  function initShipping() {
    var opts = d.querySelectorAll('.uc-ship-opt');
    if (!opts.length) return;

    function selectOpt(opt) {
      /* Express-availability policy (matches the app): an out-of-hours method
         can't be selected — explain via a dialog instead. */
      if (opt.dataset.available === '0') {
        _payDialog(opt.dataset.note ||
          (isAr ? 'وسيلة التوصيل غير متاحة الآن' : 'This delivery method is unavailable right now'));
        return;
      }
      /* The page renders TWO layouts (mobile + desktop), each with its own
         carrier radios + address form. Sync the selection across BOTH by
         carrier id so whichever form the customer submits always carries the
         chosen carrier_id (previously only one layout got checked → the other
         form could submit with no carrier → no shipping line). */
      var cid = opt.dataset.carrierId ||
                ((opt.querySelector('input[type="radio"]') || {}).value);
      d.querySelectorAll('.uc-ship-opt').forEach(function (o) {
        var ocid = o.dataset.carrierId ||
                   ((o.querySelector('input[type="radio"]') || {}).value);
        var match = String(ocid) === String(cid);
        o.classList.toggle('sel', match);
        var r = o.querySelector('input[type="radio"]');
        if (r) r.checked = match;
      });

      /* Read price from data-price (set in template) */
      var priceStr = opt.dataset.price || opt.getAttribute('data-price') || '0';
      var price = parseFloat(priceStr) || 0;

      /* Get currency symbol */
      var sym = 'KD';
      d.querySelectorAll('.uc-sum-row .v, .uc-sum-row .k + span').forEach(function (el) {
        var t = el.textContent.trim();
        var parts = t.split(' ');
        if (parts.length >= 2) {
          var last = parts[parts.length - 1];
          if (last && last.length <= 5 && isNaN(parseFloat(last))) sym = last;
        }
      });

      /* Get base subtotal — read from first non-shipping .uc-sum-row */
      var baseSubtotal = 0;
      d.querySelectorAll('.uc-sum').forEach(function (sumEl) {
        var rows = Array.from(sumEl.querySelectorAll('.uc-sum-row'));
        rows.forEach(function (row) {
          var k = row.querySelector('.k');
          var v = row.querySelector('.v');
          if (!k || !v) return;
          var kt = k.textContent.trim();
          if (kt === 'المجموع الفرعي' || kt === 'Subtotal' || kt === 'المجموع') {
            var val = parseFloat(v.textContent) || 0;
            if (val > 0) baseSubtotal = val;
          }
        });
      });

      var grandTotal = baseSubtotal + price;

      /* Update every .uc-sum block */
      d.querySelectorAll('.uc-sum').forEach(function (sumEl) {
        /* Find or create shipping row */
        var rows = Array.from(sumEl.querySelectorAll('.uc-sum-row'));
        var totRow = rows.find(function (r) { return r.classList.contains('tot'); });
        var shipRow = rows.find(function (r) { return r.dataset.shipRow; });

        if (!shipRow && totRow) {
          var sep = d.createElement('div'); sep.className = 'uc-sum-sep';
          shipRow = d.createElement('div');
          shipRow.className = 'uc-sum-row';
          shipRow.dataset.shipRow = '1';
          shipRow.innerHTML = '<span class="k">' + (isAr ? 'الشحن' : 'Shipping')
            + '</span><span class="v uc-ship-val"></span>';
          totRow.before(sep);
          totRow.before(shipRow);
        }

        /* Update shipping value */
        var shipValEl = sumEl.querySelector('.uc-ship-val') ||
                        (shipRow && shipRow.querySelector('.v'));
        if (shipValEl) {
          shipValEl.textContent = price === 0
            ? (isAr ? 'مجاني' : 'Free')
            : price.toFixed(3) + ' ' + sym;
        }

        /* Update grand total */
        var totValEl = totRow && totRow.querySelector('.v');
        if (totValEl && baseSubtotal > 0) {
          totValEl.textContent = grandTotal.toFixed(3) + ' ' + sym;
        }
      });

      /* Also update the sticky bottom-bar total (mobile + desktop) so the
         amount next to the action button INCLUDES the selected shipping. */
      if (baseSubtotal > 0) {
        d.querySelectorAll('.uc-footer-total b').forEach(function (el) {
          el.textContent = grandTotal.toFixed(3) + ' ' + sym;
        });
      }
    }

    opts.forEach(function (opt) {
      opt.addEventListener('click', function () { selectOpt(opt); });
    });

    /* Auto-select the first AVAILABLE option on load (skip out-of-hours ones) */
    setTimeout(function () {
      var firstOpt = d.querySelector('.uc-ship-opt:not(.uc-ship-opt--off)')
                  || d.querySelector('.uc-ship-opt');
      if (firstOpt && firstOpt.dataset.available !== '0') selectOpt(firstOpt);
    }, 200);
  }

  /* Payment page */
  function initPayment() {
    var listMobile = d.getElementById('uc-pay-list-mobile');
    var listDesk   = d.getElementById('uc-pay-list-desk');
    var payNow     = d.getElementById('uc-pay-now');
    var payNowDesk = d.getElementById('uc-pay-now-desk');

    loadPaymentMethods([listMobile, listDesk], [payNow, payNowDesk]);
    if (payNow)     payNow.addEventListener('click',     doPayment);
    if (payNowDesk) payNowDesk.addEventListener('click', doPayment);

    /* Items dialog */
    var itemsBtn = d.getElementById('uc-view-items-btn');
    if (itemsBtn) {
      itemsBtn.addEventListener('click', function () {
        var existing = d.getElementById('uc-items-dlg');
        if (existing) { existing.remove(); return; }
        var summaryEl = d.querySelector('.uc-pay-summary');
        var orderId   = summaryEl ? (summaryEl.dataset.orderId || 0) : 0;
        var totalData = summaryEl ? (summaryEl.dataset.total || '0') : '0';
        var sym = 'KD';
        d.querySelectorAll('.uc-pay-summary__total').forEach(function (el) {
          var parts = el.textContent.trim().split(' ');
          if (parts.length >= 2) sym = parts[parts.length - 1];
        });

        function showDlg(rowsHtml, total, sym) {
          var footer = '<div style="display:flex;justify-content:space-between;align-items:center;'
            + 'padding:12px 0 0;margin-top:4px;border-top:2px solid #E2E8F0">'
            + '<span style="font-size:15px;font-weight:800;color:#1E293B">'
            + (isAr ? 'الإجمالي' : 'Total') + '</span>'
            + '<span style="font-size:18px;font-weight:800;color:#16A34A">' + parseFloat(total).toFixed(3) + ' ' + sym + '</span>'
            + '</div>';
          var dlg = d.createElement('div');
          dlg.id = 'uc-items-dlg';
          dlg.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.55);'
            + 'z-index:9999;display:flex;align-items:center;justify-content:center;padding:20px;';
          dlg.innerHTML = '<div style="background:#fff;border-radius:16px;'
            + 'width:100%;max-width:480px;max-height:80vh;display:flex;flex-direction:column;'
            + 'box-shadow:0 20px 60px rgba(0,0,0,.3);overflow:hidden">'
            + '<div style="display:flex;justify-content:space-between;align-items:center;'
            + 'padding:16px 20px;border-bottom:1px solid #E2E8F0;background:#F8FAFC;flex-shrink:0">'
            + '<span style="font-size:16px;font-weight:800;color:#1E293B">'
            + (isAr ? 'تفاصيل الطلب' : 'Order Details') + '</span>'
            + '<button id="uc-items-close" style="border:none;background:#E2E8F0;border-radius:50%;'
            + 'width:28px;height:28px;font-size:16px;cursor:pointer;color:#475569;'
            + 'display:flex;align-items:center;justify-content:center;line-height:1">&times;</button>'
            + '</div>'
            + '<div style="overflow-y:auto;padding:0 20px;flex:1">' + rowsHtml + '</div>'
            + '<div style="padding:0 20px 16px;flex-shrink:0">' + footer + '</div>'
            + '</div>';
          d.body.appendChild(dlg);
          d.getElementById('uc-items-close').onclick = function () { dlg.remove(); };
          dlg.addEventListener('click', function (e) { if (e.target === dlg) dlg.remove(); });
        }

        if (!orderId) {
          showDlg('<div style="padding:20px;color:#999;text-align:center">'
            + (isAr ? 'لا توجد منتجات' : 'No items') + '</div>', totalData, sym);
          return;
        }

        /* Use dedicated public endpoint — avoids sale.order ACL issues */
        fetch('/uellow/order_lines?order_id=' + orderId)
          .then(function (r) { return r.json(); })
          .then(function (data) {
            var lines = data.lines || [];
            var total = data.total || parseFloat(totalData) || 0;
            var html = '';
            lines.forEach(function (line) {
              var imgSrc = line.img_id ? ('/web/image/product.product/' + line.img_id + '/image_128') : '';
              html += '<div style="display:flex;align-items:center;gap:12px;padding:10px 0;border-bottom:1px solid #f0f0f0">'
                + (imgSrc ? '<img src="' + imgSrc + '" style="width:48px;height:48px;border-radius:8px;object-fit:cover;flex-shrink:0;background:#F1F5F9"/>' : '<div style="width:48px;height:48px;border-radius:8px;background:#F1F5F9;flex-shrink:0;display:flex;align-items:center;justify-content:center;font-size:22px">&#x1F4E6;</div>')
                + '<div style="flex:1;min-width:0">'
                + '<div style="font-size:13px;font-weight:700;color:#1E293B;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">' + line.name + '</div>'
                + '<div style="font-size:11px;color:#64748B;margin-top:2px">' + line.qty + ' × ' + line.price.toFixed(3) + ' ' + sym + '</div>'
                + '</div>'
                + '<span style="font-size:14px;font-weight:800;color:#16A34A;white-space:nowrap">' + line.subtotal.toFixed(3) + ' ' + sym + '</span>'
                + '</div>';
            });
            if (!html) html = '<div style="padding:20px;color:#999;text-align:center">'
              + (isAr ? 'لا توجد منتجات' : 'No items') + '</div>';
            showDlg(html, total.toFixed(3), sym);
          })
          .catch(function () {
            showDlg('<div style="padding:20px;color:#999;text-align:center">'
              + (isAr ? 'تعذّر التحميل' : 'Could not load items') + '</div>', totalData, sym);
          });
      });
    }
  }

  /* Form validation — highlight empty required fields in red */
  function initFormValidation() {
    /* Override native HTML5 validation with custom red highlight */
    var forms = d.querySelectorAll('#uc-address-form, #uc-address-form-desk');
    forms.forEach(function (form) {
      /* Disable native browser bubbles */
      form.setAttribute('novalidate', 'novalidate');

      form.addEventListener('submit', function (e) {
        var invalid = [];
        form.querySelectorAll('input[required], select[required], textarea[required]').forEach(function (el) {
          var val = (el.value || '').trim();
          var empty = !val || val === '0' || val === '';
          if (empty) invalid.push(el);
          else el.classList.remove('uc-invalid');
        });

        if (invalid.length) {
          e.preventDefault();
          e.stopPropagation();
          invalid.forEach(function (el) {
            el.classList.add('uc-invalid');
            /* Remove on fix */
            el.addEventListener('change', function () {
              if ((el.value || '').trim() && el.value !== '0')
                el.classList.remove('uc-invalid');
            });
            el.addEventListener('input', function () {
              if ((el.value || '').trim())
                el.classList.remove('uc-invalid');
            });
          });
          /* Scroll to first invalid field */
          var first = invalid[0];
          first.scrollIntoView({ behavior: 'smooth', block: 'center' });
          setTimeout(function () { first.focus(); }, 300);
        }
      });
    });
  }

  /* Hide theme bottom navbar (by class names only -- no position scan) */

  /* Form validation — highlight empty required fields in red */
  function initFormValidation() {
    /* Override native HTML5 validation with custom red highlight */
    var forms = d.querySelectorAll('#uc-address-form, #uc-address-form-desk');
    forms.forEach(function (form) {
      /* Disable native browser bubbles */
      form.setAttribute('novalidate', 'novalidate');

      form.addEventListener('submit', function (e) {
        var invalid = [];
        form.querySelectorAll('input[required], select[required], textarea[required]').forEach(function (el) {
          var val = (el.value || '').trim();
          var empty = !val || val === '0' || val === '';
          if (empty) invalid.push(el);
          else el.classList.remove('uc-invalid');
        });

        if (invalid.length) {
          e.preventDefault();
          e.stopPropagation();
          invalid.forEach(function (el) {
            el.classList.add('uc-invalid');
            /* Remove on fix */
            el.addEventListener('change', function () {
              if ((el.value || '').trim() && el.value !== '0')
                el.classList.remove('uc-invalid');
            });
            el.addEventListener('input', function () {
              if ((el.value || '').trim())
                el.classList.remove('uc-invalid');
            });
          });
          /* Scroll to first invalid field */
          var first = invalid[0];
          first.scrollIntoView({ behavior: 'smooth', block: 'center' });
          setTimeout(function () { first.focus(); }, 300);
        }
      });
    });
  }

  /* Hide theme bottom navbar (by class names only -- no position scan) */
  function hideThemeNav() {
    ['.o_bottom_bar', '#bottom-bar', '.d_bottom_bar',
     '[class*="bottom_nav"]', '[class*="bottom-nav"]',
     '[class*="bottomNav"]', '[class*="BottomNav"]',
     '.navbar-bottom', '.fixed-bottom-nav',
     '#bottom_nav', '.site-bottom-bar', '.o_livechat_button'
    ].forEach(function (sel) {
      try {
        d.querySelectorAll(sel).forEach(function (el) {
          el.style.setProperty('display', 'none', 'important');
        });
      } catch (e) {}
    });
  }

  /* Boot */
  function boot() {
    d.body.classList.add('uellow-checkout-active');
    hideThemeNav();
    setTimeout(hideThemeNav, 800);

    var isCart    = !!d.getElementById('uc-to-shipping');
    var isAddress = !!d.getElementById('uc-address-form');
    var isPayment = !!d.getElementById('uc-pay-list-mobile');

    if (isCart)    initCart();
    if (isAddress) { initMap(); initCountry(); initShipping(); initFormValidation(); }
    if (isPayment) initPayment();

    var contBtn = d.getElementById('uc-continue-shop');
    if (contBtn) contBtn.addEventListener('click', function () { w.location.href = '/shop'; });
    var contBtnDesk = d.getElementById('uc-continue-shop-desk');
    if (contBtnDesk) contBtnDesk.addEventListener('click', function () { w.location.href = '/shop'; });
  }

  if (d.readyState === 'loading') {
    d.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }

}(window, document));
