/* Uellow Category Page — app-style mobile filters.
   Turns the theme's filter groups into a horizontal bar of chips ("Brand ▾").
   Tapping a chip opens a bottom-sheet with that filter's REAL options (the actual
   theme nodes are moved in/out, so checkboxes/sliders keep their form membership).
   "Show results" returns the open group into the real <form class="js_attributes">
   and submits it natively — so every filter (brand/color/tags/stock/rating/price)
   applies exactly the way the theme intends. Active filters show a count badge on
   the chip + a "Clear" chip appears before them. */
(function () {
  "use strict";
  var MOBILE = 991;

  function isAr() {
    return (document.documentElement.lang || "").indexOf("ar") >= 0
        || document.documentElement.dir === "rtl"
        || location.pathname.indexOf("/ar") === 0;
  }

  // count active (checked) values inside one filter group
  function countSel(g) {
    var n = 0;
    g.querySelectorAll('input[name]:checked').forEach(function (i) {
      if ((i.type === "checkbox" || i.type === "radio") && i.name) n++;
    });
    return n;
  }
  // is the price group narrowed from its full range (via URL)?
  function priceActive() {
    var q = new URLSearchParams(location.search);
    return q.has("min_price") || q.has("max_price");
  }

  // set / clear a hidden price input on the form before submit
  function setHidden(form, name, val) {
    var h = form.querySelector('input[type=hidden][name="' + name + '"]');
    if (val !== "" && val != null) {
      if (!h) { h = document.createElement("input"); h.type = "hidden"; h.name = name; form.appendChild(h); }
      h.value = val;
    } else if (h) { h.remove(); }
  }

  function build() {
    if (window.innerWidth > MOBILE) return;                  // mobile only
    if (document.querySelector(".ucpf-bar")) return;          // once
    var col = document.getElementById("products_grid_before");
    if (!col) return;
    var form = col.querySelector("form.js_attributes") || document.querySelector("form.js_attributes");
    var groups = col.querySelectorAll(".tp-filter-attribute");
    if (!groups.length) return;

    var ar = isAr();
    var T = {
      results: ar ? "عرض النتائج" : "Show results",
      filter:  ar ? "تصفية" : "Filter",
      clear:   ar ? "مسح الكل" : "Clear all",
    };

    // ---- dialog (bottom sheet) ----
    var dlg = document.createElement("div");
    dlg.className = "ucpf-dlg";
    dlg.setAttribute("dir", ar ? "rtl" : "ltr");
    dlg.innerHTML =
      '<div class="ucpf-sheet">' +
        '<div class="ucpf-head"><b class="ucpf-title"></b><span class="ucpf-x">✕</span></div>' +
        '<div class="ucpf-body"></div>' +
        '<button type="button" class="ucpf-apply">' + T.results + "</button>" +
      "</div>";
    document.body.appendChild(dlg);
    var dBody = dlg.querySelector(".ucpf-body");
    var dTitle = dlg.querySelector(".ucpf-title");

    function returnHome() {
      var cur = dBody.firstElementChild;
      if (cur && cur._ucpHome) cur._ucpHome.appendChild(cur);
    }
    function close() { returnHome(); dlg.classList.remove("show"); }

    function apply() {
      returnHome();                            // put the open group back into the form
      if (!form) { location.reload(); return; }
      // price: give the unnamed slider text inputs real params so they submit
      var slider = form.querySelector('.tp-slider[data-key="price"]');
      if (slider) {
        var mn = form.querySelector(".tp-range-filter .min");
        var mx = form.querySelector(".tp-range-filter .max");
        var dmin = parseFloat(slider.getAttribute("data-min"));
        var dmax = parseFloat(slider.getAttribute("data-max"));
        var vmn = mn ? parseFloat(mn.value) : NaN;
        var vmx = mx ? parseFloat(mx.value) : NaN;
        setHidden(form, "min_price", (!isNaN(vmn) && vmn > dmin) ? vmn : "");
        setHidden(form, "max_price", (!isNaN(vmx) && vmx < dmax) ? vmx : "");
      }
      form.submit();                           // native GET — applies every filter
    }

    dlg.querySelector(".ucpf-x").addEventListener("click", close);
    dlg.querySelector(".ucpf-apply").addEventListener("click", apply);
    dlg.addEventListener("click", function (e) { if (e.target === dlg) close(); });

    // ---- chips bar ----
    var bar = document.createElement("div");
    bar.className = "ucpf-bar";

    var anyActive = false;

    groups.forEach(function (g) {
      if (g.classList.contains("tp-hook-categories")) return;  // categories live in the top pills
      var t = g.querySelector(".tp-filter-attribute-title h6, .tp-filter-attribute-title");
      var title = ((t && t.textContent) || T.filter).replace(/\s+/g, " ").trim();
      var area = g.querySelector(".tp-filter-attribute-collapsible-area") || g;
      area._ucpHome = g;

      var isPrice = g.classList.contains("tp-hook-filter-price");
      var n = isPrice ? (priceActive() ? 1 : 0) : countSel(g);
      if (n > 0) anyActive = true;

      var chip = document.createElement("button");
      chip.type = "button";
      chip.className = "ucpf-chip" + (n > 0 ? " ucpf-on" : "");
      var sp = document.createElement("span");
      sp.textContent = (n > 0 && !isPrice) ? (title + " (" + n + ")") : title;
      chip.appendChild(sp);
      if (n > 0) {
        chip.insertAdjacentHTML("beforeend", ' <i class="ucpf-chk">✓</i>');
      } else {
        chip.insertAdjacentHTML("beforeend", ' <i class="ucpf-arrow">▾</i>');
      }
      chip.addEventListener("click", function () {
        returnHome();
        dTitle.textContent = title;
        area.style.display = "block";
        dBody.appendChild(area);
        dlg.classList.add("show");
      });
      bar.appendChild(chip);
    });

    // ---- "Clear all" chip (only when something is active) ----
    if (anyActive) {
      var clear = document.createElement("a");
      clear.className = "ucpf-chip ucpf-clear";
      var q = new URLSearchParams(location.search);
      var keep = new URLSearchParams();
      ["search", "order"].forEach(function (k) { if (q.get(k)) keep.set(k, q.get(k)); });
      var qs = keep.toString();
      clear.href = location.pathname + (qs ? "?" + qs : "");
      clear.innerHTML = '<i class="ucpf-chk">✕</i> ' + T.clear;
      bar.insertBefore(clear, bar.firstChild);
    }

    // ---- place the bar right below the categories, above the products ----
    var anchor = document.querySelector(".tp-shop-row");
    if (anchor && anchor.parentNode) anchor.parentNode.insertBefore(bar, anchor);
    else col.parentNode.insertBefore(bar, col);
  }

  // ---- voice search (Web Speech API) on the hero search bar ----
  function voice() {
    var mic = document.querySelector(".ucp-ai-mic");
    var inp = document.querySelector(".ucp-ai-in");
    if (!mic || !inp) return;
    var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) { mic.style.display = "none"; return; }   // unsupported → hide
    mic.addEventListener("click", function () {
      try {
        var rec = new SR();
        rec.lang = isAr() ? "ar-SA" : "en-US";
        rec.interimResults = false;
        rec.maxAlternatives = 1;
        mic.classList.add("ucp-rec");
        rec.onresult = function (e) {
          var txt = (e.results[0][0].transcript || "").trim();
          if (txt) {
            inp.value = txt;
            var c = inp.getAttribute("data-cat");
            var b = c ? "/shop/category/" + c : "/shop";
            location.href = b + "?search=" + encodeURIComponent(txt);
          }
        };
        rec.onerror = function () { mic.classList.remove("ucp-rec"); };
        rec.onend = function () { mic.classList.remove("ucp-rec"); };
        rec.start();
      } catch (err) { mic.classList.remove("ucp-rec"); }
    });
  }

  // ---- live countdown for the flash strip (desktop boxes + mobile line) ----
  function countdown() {
    function pad(n) { return (n < 10 ? "0" : "") + n; }
    var boxes = document.querySelector(".ucp-cd[data-end]");
    var line = document.querySelector(".ucp-flashline-cd[data-end]");
    var end = (boxes && boxes.getAttribute("data-end")) ||
              (line && line.getAttribute("data-end"));
    if (!end) return;
    var endMs = Date.parse(end);
    if (isNaN(endMs)) return;
    function tick() {
      var diff = endMs - Date.now();
      if (diff < 0) diff = 0;
      var s = Math.floor(diff / 1000);
      var d = Math.floor(s / 86400); s -= d * 86400;
      var h = Math.floor(s / 3600);  s -= h * 3600;
      var m = Math.floor(s / 60);    s -= m * 60;
      if (boxes) {
        var bd = boxes.querySelector(".ucp-cd-d"), bh = boxes.querySelector(".ucp-cd-h"),
            bm = boxes.querySelector(".ucp-cd-m"), bs = boxes.querySelector(".ucp-cd-s");
        if (bd) bd.textContent = pad(d); if (bh) bh.textContent = pad(h);
        if (bm) bm.textContent = pad(m); if (bs) bs.textContent = pad(s);
      }
      if (line) line.textContent = (d > 0 ? d + "d " : "") + pad(h) + ":" + pad(m) + ":" + pad(s);
    }
    tick();
    setInterval(tick, 1000);
  }

  // ===== App-style rich card: upward perk ticker + no-wrap badge shrink =====
  function appcardTicker(box) {
    if (box.getAttribute("data-ucp-tk")) return;
    box.setAttribute("data-ucp-tk", "1");
    var list = box.querySelector(".ucp-ac-tlist");
    if (!list) return;
    var items = list.querySelectorAll(".ucp-ac-ti");
    if (items.length <= 2) return;            // 1 real item (+dup) → static
    var n = items.length - 1;                 // last item duplicates the first
    var h = items[0].offsetHeight || 18;
    var i = 0;
    setInterval(function () {
      i += 1;
      list.style.transform = "translateY(" + (-i * h) + "px)";
      if (i >= n) {                            // reached the duplicate → snap back
        setTimeout(function () {
          list.style.transition = "none";
          list.style.transform = "translateY(0)";
          void list.offsetHeight;              // reflow
          list.style.transition = "";
          i = 0;
        }, 440);
      }
    }, 2400);
  }
  function appcardShrink(row) {
    row.style.setProperty("--bs", "1");
    var s = 1, g = 0;
    while (row.scrollWidth > row.clientWidth + 1 && s > 0.66 && g++ < 16) {
      s -= 0.03;
      row.style.setProperty("--bs", s.toFixed(2));
    }
  }
  function appcard(root) {
    var scope = root || document;
    scope.querySelectorAll(".ucp-ac-ticker").forEach(function (b) { try { appcardTicker(b); } catch (e) {} });
    scope.querySelectorAll(".ucp-ac-badges").forEach(function (r) { try { appcardShrink(r); } catch (e) {} });
  }
  function observeGrid() {
    var grid = document.getElementById("products_grid");
    if (!grid || !window.MutationObserver) return;
    var t;
    new MutationObserver(function () {
      clearTimeout(t);
      t = setTimeout(function () { try { appcard(); } catch (e) {} }, 120);
    }).observe(grid, { childList: true, subtree: true });
  }

  function init() {
    try { build(); } catch (e) {}
    try { voice(); } catch (e) {}
    try { countdown(); } catch (e) {}
    try { appcard(); } catch (e) {}
    try { observeGrid(); } catch (e) {}
    window.addEventListener("resize", function () {
      document.querySelectorAll(".ucp-ac-badges").forEach(function (r) { try { appcardShrink(r); } catch (e) {} });
    });
  }
  if (document.readyState !== "loading") init();
  else document.addEventListener("DOMContentLoaded", init);
})();
