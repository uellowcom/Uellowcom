/* لمّة يلو — storefront widget (plain IIFE, runs on every frontend page).
   Injects the "add to Lamma" button on product pages + a persistent bar/sheet,
   all wired to the /lamma/* JSON routes. Pure DOM injection — no template edits. */
(function () {
    "use strict";
    var S = null;              // current lamma summary
    var CUR = "د.ك";

    function rpc(url, params) {
        return fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ jsonrpc: "2.0", method: "call", params: params || {} }),
        }).then(function (r) { return r.json(); }).then(function (j) { return j.result; });
    }
    function fmt(n) { return (Number(n) || 0).toFixed(3); }
    function el(html) { var d = document.createElement("div"); d.innerHTML = html.trim(); return d.firstChild; }

    function productId() {
        var i = document.querySelector('input[name="product_template_id"]');
        if (i && i.value) { return parseInt(i.value, 10); }
        var m = (location.pathname || "").match(/-(\d+)(?:$|[\/?#])/);
        return m ? parseInt(m[1], 10) : 0;
    }
    function onProductPage() {
        return !!(document.querySelector("#product_detail, .js_product, form.js_add_cart_variants") && productId());
    }

    /* ---------- persistent bar + sheet ---------- */
    var bar, mask, sheet;
    function buildChrome() {
        bar = el('<div id="ul-bar"><div class="ul-top"><div class="ul-thumbs"></div>' +
            '<div class="ul-cnt">0</div><div class="ul-inf"></div>' +
            '<button type="button" class="ul-go">إتمام</button></div><div class="ul-meter"><i></i></div></div>');
        mask = el('<div id="ul-mask"></div>');
        sheet = el('<div id="ul-sheet"><div class="ul-grip"></div><h4></h4>' +
            '<div class="ul-shield"></div><div class="ul-items"></div>' +
            '<div class="ul-tier"></div><div class="ul-tot"></div>' +
            '<button type="button" class="ul-checkout">إتمام اللمّة</button></div>');
        document.body.appendChild(bar);
        document.body.appendChild(mask);
        document.body.appendChild(sheet);
        bar.addEventListener("click", function (e) { if (!e.target.classList.contains("ul-go")) { openSheet(); } });
        bar.querySelector(".ul-go").addEventListener("click", function (e) { e.stopPropagation(); openSheet(); });
        mask.addEventListener("click", closeSheet);
        sheet.querySelector(".ul-checkout").addEventListener("click", function () {
            var b = this; b.disabled = true; b.textContent = "جارٍ التجهيز…";
            rpc("/lamma/checkout").then(function (r) {
                if (r && r.redirect) { window.location.href = r.redirect; return; }
                if (r && r.error === "need_more") { b.disabled = false; b.textContent = "إتمام اللمّة"; alert("أضف " + (r.min_items || 2) + " منتجات على الأقل للّمّة"); return; }
                if (r && r.error === "disabled") { b.disabled = false; b.textContent = "إتمام اللمّة"; alert("خدمة اللمّة غير متاحة في منطقتك حالياً"); return; }
                // otherwise: go to cart anyway
                window.location.href = "/shop/cart";
            }).catch(function () { window.location.href = "/shop/cart"; });
        });
    }
    function renderBar() {
        if (!S) { return; }
        CUR = S.currency || CUR;
        var has = (S.n || 0) > 0;
        bar.classList.toggle("show", has);
        bar.querySelector(".ul-cnt").textContent = S.n || 0;
        var _pct = (S.discount_pct || 0);
        var _before = _pct > 0 ? ('<s style="color:#8b97a8">' + fmt(S.subtotal) + '</s> ') : "";
        var _off = _pct > 0 ? (' <span style="color:#4ade80">-' + _pct.toFixed(0) + "%</span>") : "";
        bar.querySelector(".ul-inf").innerHTML = (S.label || "لمّة يلو") + " · " + _before +
            '<b style="color:#FBBF00">' + fmt(S.pays) + " " + CUR + "</b>" + _off;
        bar.querySelector(".ul-meter i").style.width = Math.min((S.subtotal || 0) / 30 * 100, 100) + "%";
        var th = bar.querySelector(".ul-thumbs"); th.innerHTML = "";
        (S.items || []).slice(0, 4).forEach(function (it) {
            var im = document.createElement("img"); im.src = it.image; th.appendChild(im);
        });
    }
    function openSheet() {
        if (!S || !(S.n > 0)) { return; }
        sheet.querySelector("h4").textContent = (S.label || "لمّة يلو") + " 🧺";
        var box = sheet.querySelector(".ul-items"); box.innerHTML = "";
        (S.items || []).forEach(function (it) {
            var row = el('<div class="ul-si"><img src="' + it.image + '"><div class="n">' + it.name +
                '</div><div class="p">' + fmt(it.price) + '</div><button type="button" class="rm">✕</button></div>');
            row.querySelector(".rm").addEventListener("click", function () { removeItem(it.id); });
            box.appendChild(row);
        });
        var sh = sheet.querySelector(".ul-shield");
        if (S.capped) {
            sh.classList.add("show");
            sh.textContent = "✔️ خصم اللمّة وصل حده الأقصى لهذه الباقة.";
        } else { sh.classList.remove("show"); }
        sheet.querySelector(".ul-tier").textContent = (S.n < (S.min_items || 2))
            ? "أضف منتجاً آخر لبدء الخصم" : "";
        sheet.querySelector(".ul-tier").style.display = (S.n < (S.min_items || 2)) ? "block" : "none";
        // professional breakdown: subtotal / discount / [installment] / net
        var pctTxt = (S.discount_pct || 0) > 0 ? (" (-" + (S.discount_pct).toFixed(0) + "%)") : "";
        var rows = "";
        rows += '<div class="ul-brk-r"><span>الإجمالي قبل الخصم</span><span>' + fmt(S.subtotal) + " " + CUR + "</span></div>";
        rows += '<div class="ul-brk-r disc"><span>الخصم' + pctTxt + '</span><span>− ' + fmt(S.saved) + " " + CUR + "</span></div>";
        if (S.type === "installment") {
            rows += '<div class="ul-brk-r inst"><span>التقسيط</span><span>' + fmt(S.monthly) + " " + CUR + "/شهر</span></div>";
        }
        rows += '<div class="ul-brk-r net"><span>الصافي</span><span>' + fmt(S.pays) + " " + CUR + "</span></div>";
        sheet.querySelector(".ul-tot").innerHTML = '<div class="ul-brk">' + rows + "</div>";
        mask.classList.add("show"); sheet.classList.add("show");
    }
    function closeSheet() { mask.classList.remove("show"); sheet.classList.remove("show"); }

    /* ---------- actions ---------- */
    function refresh() { return rpc("/lamma/get").then(apply); }
    function apply(s) { S = s; renderBar(); syncButton(); }
    function addProduct(pid, type) {
        return rpc("/lamma/add", { product_id: pid, lamma_type: type }).then(function (s) {
            apply(s); if (sheet.classList.contains("show")) { openSheet(); }
        });
    }
    function removeItem(pid) {
        return rpc("/lamma/remove", { product_id: pid }).then(function (s) {
            apply(s); s.n > 0 ? openSheet() : closeSheet();
        });
    }
    function setType(t) { return rpc("/lamma/type", { lamma_type: t }).then(apply); }

    /* ---------- product-page button ---------- */
    var btn, seg;
    function inProduct() { return S && S.items && S.items.some(function (i) { return i.id === productId(); }); }
    function syncButton() {
        if (!btn) { return; }
        if (inProduct()) { btn.classList.add("in"); btn.innerHTML = "✓ في لمّتك"; }
        else { btn.classList.remove("in"); btn.innerHTML = "🧺 أضف للّمّة"; }
    }
    function hideBuyNow() {
        // hide any "Buy now / اشترِ الآن" button so Lamma is the primary CTA
        var sel = ".js_buy_now, #buy_now, [id*='buy_now'], a.btn-buy-now, .o_we_buy_now";
        document.querySelectorAll(sel).forEach(function (b) { b.style.display = "none"; });
        var scope = document.querySelectorAll("#product_detail a, #product_detail button, #o_wsale_cta_wrapper a, #o_wsale_cta_wrapper button");
        Array.prototype.forEach.call(scope, function (b) {
            var t = (b.textContent || "").trim();
            if (t === "اشترِ الآن" || t === "اشتر الآن" || /buy\s*now/i.test(t)) { b.style.display = "none"; }
        });
    }

    function injectButton() {
        if (!onProductPage() || !S || !S.enabled) { return; }
        var pid = productId();
        var anchor = document.querySelector("#o_wsale_cta_wrapper") ||
            document.querySelector("#add_to_cart, [id*='add_to_cart'], .js_add_cart") ;
        var box = el('<div class="ul-box"><div class="ul-h">🧺 ' + (S.label || "لمّة يلو") +
            ' — كوّن باقتك ووفّر</div><div class="ul-sub">اختر النوع ثم أضف هذا المنتج</div></div>');
        seg = el('<div class="ul-seg"><button type="button" data-t="normal" class="on">عادي</button>' +
            '<button type="button" data-t="installment">أقساط</button></div>');
        var instNote = el('<div class="ul-inst" id="ul-inst">💳 <b>الأقساط:</b> قسّم طلبك على دفعات مريحة عبر Taly / CINET · موافقة سريعة · بدون تعقيد. اختر «الأقساط» ثم أضف منتجاتك، وأكمل الدفع بالتقسيط من السلة.</div>');
        btn = el('<button type="button" class="ul-btn">🧺 أضف للّمّة</button>');
        if (!S.installment_enabled) { seg.querySelector('[data-t="installment"]').style.display = "none"; }
        seg.querySelectorAll("button").forEach(function (b) {
            b.addEventListener("click", function () {
                seg.querySelectorAll("button").forEach(function (x) { x.classList.remove("on"); });
                b.classList.add("on");
                instNote.classList.toggle("show", b.dataset.t === "installment");
                setType(b.dataset.t);
            });
        });
        btn.addEventListener("click", function (e) {
            e.preventDefault(); e.stopPropagation();
            var on = seg.querySelector("button.on");
            var t = on && on.dataset ? on.dataset.t : "normal";
            addProduct(pid, t);
        });
        box.appendChild(seg); box.appendChild(btn); box.appendChild(instNote);
        if (anchor && anchor.parentNode) {
            anchor.parentNode.insertBefore(box, anchor);
            if (S.replace_add_to_cart) { anchor.style.display = "none"; hideBuyNow(); }
        } else {
            var pd = document.querySelector("#product_detail") || document.body;
            pd.insertBefore(box, pd.firstChild);
            if (S.replace_add_to_cart) { hideBuyNow(); }
        }
        syncButton();
    }

    /* ---------- homepage promo banner ---------- */
    function injectHomePromo() {
        // The home page carries `.uhome` (uellow_home_slider). Robust + avoids
        // showing the promo on any other page.
        var home = document.querySelector(".uhome");
        if (!home || document.getElementById("ul-home-promo")) return;
        var label = (S && S.label) || "لمّة يلو";
        var b = el(
            '<div class="ul-home-promo" id="ul-home-promo">' +
            '<div class="ul-ic">🧺</div>' +
            '<div class="ul-txt"><h3>' + label + ' — كوّن باقتك ووفّر</h3>' +
            '<p>أضِف منتجاتك من أي صفحة والخصم يكبر معاك — محمي بهامش ربح.</p>' +
            '<div class="ul-pills"><span class="ul-pill">خصم حتى 20%</span>' +
            '<span class="ul-pill">أقساط بربح مضمون</span>' +
            '<span class="ul-pill">دفع عند الاستلام</span></div></div>' +
            '<a class="ul-cta" href="/shop">ابدأ التسوّق 🛒</a></div>'
        );
        home.parentNode.insertBefore(b, home);
    }

    function init() {
        buildChrome();
        refresh().then(function () { injectButton(); injectHomePromo(); });
    }
    if (document.readyState === "loading") { document.addEventListener("DOMContentLoaded", init); }
    else { init(); }
})();
