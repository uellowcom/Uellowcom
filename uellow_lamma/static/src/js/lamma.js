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
    /* current selected variant (colour/size) from the product form — Odoo keeps
       input[name="product_id"] in sync with the chosen combination. */
    function variantId() {
        var i = document.querySelector('#product_detail input[name="product_id"], .js_product input[name="product_id"], input.product_id[name="product_id"]');
        return i && i.value ? parseInt(i.value, 10) : 0;
    }

    /* ---------- persistent bar + sheet ---------- */
    var bar, mask, sheet;
    var barHidden = false;
    function buildChrome() {
        bar = el('<div id="ul-bar">' +
            '<div class="ul-thumbs"></div>' +
            '<div class="ul-pcol"><div class="ul-net"></div><div class="ul-was"></div></div>' +
            '<button type="button" class="ul-go">أكمل اللمّة</button>' +
            '<span class="ul-x" title="إخفاء">✕</span>' +
            '</div>');
        mask = el('<div id="ul-mask"></div>');
        sheet = el('<div id="ul-sheet"><div class="ul-grip"></div><h4></h4>' +
            '<div class="ul-shield"></div><div class="ul-items"></div>' +
            '<div class="ul-tier"></div><div class="ul-prog"></div><div class="ul-tot"></div>' +
            '<div class="ul-msg" id="ul-msg" style="display:none"></div>' +
            '<button type="button" class="ul-group" style="width:100%;margin-bottom:8px;padding:14px;border:0;border-radius:12px;font-weight:800;font-size:15px;color:#fff;background:linear-gradient(135deg,#FF7A1A,#FF9E45);cursor:pointer">🧺 ابدأ لمّة جماعية — شارك التوفير</button>' +
            '<button type="button" class="ul-checkout">إتمام اللمّة</button></div>');
        document.body.appendChild(bar);
        document.body.appendChild(mask);
        document.body.appendChild(sheet);
        bar.addEventListener("click", function (e) {
            if (e.target.classList.contains("ul-x")) { return; }
            openSheet();
        });
        bar.querySelector(".ul-go").addEventListener("click", function (e) { e.stopPropagation(); openSheet(); });
        bar.querySelector(".ul-x").addEventListener("click", function (e) {
            e.stopPropagation(); barHidden = true; bar.classList.remove("show");
        });
        mask.addEventListener("click", closeSheet);
        sheet.querySelector(".ul-checkout").addEventListener("click", function () {
            var b = this; b.disabled = true; b.textContent = "جارٍ التجهيز…";
            rpc("/lamma/checkout").then(function (r) {
                if (r && r.redirect) { window.location.href = r.redirect; return; }
                b.disabled = false; b.textContent = "إتمام اللمّة";
                if (r && r.error === "need_more") { sheetMsg("أضف " + (r.min_items || 2) + " منتجات على الأقل للّمّة"); return; }
                if (r && r.error === "disabled") { sheetMsg("خدمة اللمّة غير متاحة في منطقتك حالياً"); return; }
                window.location.href = "/shop/cart";
            }).catch(function () { window.location.href = "/shop/cart"; });
        });
        var gb = sheet.querySelector(".ul-group");
        if (gb) { gb.addEventListener("click", function () {
            var b = this; b.disabled = true; b.textContent = "جارٍ إنشاء اللمّة…";
            rpc("/lamma/group/create", {}).then(function (r) {
                if (r && r.code) { window.location.href = r.share_url || ("/lamma/g/" + r.code); return; }
                b.disabled = false; b.textContent = "🧺 ابدأ لمّة جماعية — شارك التوفير";
                sheetMsg("تعذّر إنشاء اللمّة، حاول مجددًا");
            }).catch(function () { b.disabled = false; b.textContent = "🧺 ابدأ لمّة جماعية — شارك التوفير"; sheetMsg("تعذّر إنشاء اللمّة"); });
        }); }
    }
    function renderBar() {
        if (!S) { return; }
        CUR = S.currency || CUR;
        var n = S.n || 0;
        var has = n > 0;
        var onCheckout = /^\/shop\/(cart|checkout|address|payment|confirmation|extra_info)/.test(location.pathname || "");
        bar.classList.toggle("show", has && !barHidden && !onCheckout);
        // net price
        bar.querySelector(".ul-net").innerHTML =
            '<b>' + fmt(S.pays) + '</b><span class="u">' + CUR + '</span>';
        // pre-discount "كان" pill (emphasised) — else a plain item count
        var pct = (S.discount_pct || 0);
        var was = bar.querySelector(".ul-was");
        if (pct > 0 && (S.subtotal || 0) > (S.pays || 0) + 0.0005) {
            var savedAmt = (S.subtotal || 0) - (S.pays || 0);
            was.innerHTML = '<span class="ul-oldpill">كان <s>' + fmt(S.subtotal) + '</s></span>' +
                '<span class="ul-savepill">وفّرت ' + fmt(savedAmt) + '</span>';
        } else {
            was.innerHTML = '<span class="ul-cntlbl">' + n + ' منتجات في لمّتك</span>';
        }
        // thumbnails + count chip
        var th = bar.querySelector(".ul-thumbs"); th.innerHTML = "";
        (S.items || []).slice(0, 3).forEach(function (it) {
            var im = document.createElement("img"); im.src = it.image; th.appendChild(im);
        });
        var c = document.createElement("div"); c.className = "ul-cnt"; c.textContent = n;
        th.appendChild(c);
    }
    function sheetMsg(t) {
        var m = sheet && sheet.querySelector(".ul-msg");
        if (!m) { return; }
        m.textContent = t || "";
        m.style.display = t ? "block" : "none";
    }

    function openSheet() {
        if (!S || !(S.n > 0)) { return; }
        sheetMsg("");
        sheet.querySelector("h4").textContent = (S.label || "لمّة يلو") + " 🧺";
        var box = sheet.querySelector(".ul-items"); box.innerHTML = "";
        (S.items || []).forEach(function (it) {
            var q = it.qty || 1;
            var row = el('<div class="ul-si"><img src="' + it.image + '"><div class="n">' + it.name +
                '<div class="ul-qs"><button type="button" class="qm">−</button><span class="qv">' + q +
                '</span><button type="button" class="qp">+</button></div></div>' +
                '<div class="p">' + fmt(it.line_total != null ? it.line_total : it.price) +
                '</div><button type="button" class="rm">✕</button></div>');
            row.querySelector(".rm").addEventListener("click", function () { removeItem(it.id); });
            row.querySelector(".qm").addEventListener("click", function () { setQty(it.id, q - 1); });
            row.querySelector(".qp").addEventListener("click", function () { setQty(it.id, q + 1); });
            box.appendChild(row);
        });
        var sh = sheet.querySelector(".ul-shield");
        var exc = S.excluded || 0, sv = S.saved || 0;
        if (exc > 0 && sv > 0) {
            sh.classList.add("show");
            sh.textContent = "✔️ طُبّق خصم اللمّة على المنتجات المؤهّلة، و" + exc +
                (exc === 1 ? " منتج" : " منتجات") + " عند حد الربح فبقيت بسعرها.";
        } else if (sv <= 0 && S.n >= 2) {
            sh.classList.add("show");
            sh.textContent = "ℹ️ منتجات هذه الباقة عند حد الربح حالياً، فلا يمكن تطبيق خصم اللمّة عليها.";
        } else if (S.capped) {
            sh.classList.add("show");
            sh.textContent = "✔️ خصم اللمّة وصل حده الأقصى لهذه الباقة.";
        } else { sh.classList.remove("show"); }
        sheet.querySelector(".ul-tier").textContent = (S.n < (S.min_items || 2))
            ? "أضف منتجاً آخر لبدء الخصم" : "";
        sheet.querySelector(".ul-tier").style.display = (S.n < (S.min_items || 2)) ? "block" : "none";
        (function(){
            var pr = sheet.querySelector(".ul-prog"); if (!pr) return;
            if (S.next_tier && (S.n || 0) >= 1) {
                var need = S.next_tier.need_items ? (S.next_tier.need_items + " منتج") : (fmt(S.next_tier.need_amount) + " " + CUR);
                pr.style.display = "block";
                pr.innerHTML = '<div class="ul-pg-top"><b>خصمك ' + Math.round(S.tier_pct||0) + '٪</b>'
                    + '<span>أضف ' + need + ' ← ' + Math.round(S.next_tier.pct) + '٪ 🔥</span></div>'
                    + '<div class="ul-pg-bar"><i style="width:' + Math.round((S.progress||0)*100) + '%"></i></div>';
            } else if (S.tier_pct) {
                pr.style.display = "block";
                pr.innerHTML = '<div class="ul-pg-top"><b>🎉 وصلت أقصى خصم ' + Math.round(S.tier_pct) + '٪</b></div>'
                    + '<div class="ul-pg-bar full"><i style="width:100%"></i></div>';
            } else { pr.style.display = "none"; }
        })();
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
    var _lastPct = -1;
    function celebrate(pct) {
        try {
            var host = document.createElement("div"); host.className = "ul-cel";
            var cols = ["#F5C320","#FF7A1A","#0A8A3F","#5B54E0","#D92D2D","#E7A400"];
            var cf = "";
            for (var i = 0; i < 18; i++) {
                cf += '<span class="ul-cf" style="left:' + Math.round((i * 5.5) % 100)
                    + '%;background:' + cols[i % 6] + ';animation-delay:' + ((i % 9) * 55) + 'ms"></span>';
            }
            host.innerHTML = cf + '<div class="ul-cel-card">🎉'
                + '<div class="ul-cel-t">فتحت خصم ' + Math.round(pct) + '٪!</div>'
                + '<div class="ul-cel-s">استمر في لمّتك ووفّر أكثر 🧺</div></div>';
            document.body.appendChild(host);
            if (navigator.vibrate) { try { navigator.vibrate(60); } catch (e) {} }
            setTimeout(function () { host.style.opacity = 0; }, 1700);
            setTimeout(function () { host.remove(); }, 2200);
        } catch (e) {}
    }
    function apply(s) {
        var np = (s && s.tier_pct) || 0;
        if (_lastPct >= 0 && np > _lastPct) { celebrate(np); }
        _lastPct = np;
        S = s; renderBar(); syncButton();
    }
    function addProduct(pid, type) {
        barHidden = false; // a fresh add always re-shows the bar
        var payload = { product_id: pid, lamma_type: type };
        var vid = variantId();
        if (vid) { payload.variant_id = vid; }
        return rpc("/lamma/add", payload).then(function (s) {
            apply(s); if (sheet.classList.contains("show")) { openSheet(); }
        });
    }
    function setQty(pid, q) {
        if (q < 1) return;
        return rpc("/lamma/qty", { product_id: pid, qty: q }).then(function (s) {
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
        refresh().then(function () { injectButton(); /* home promo banner removed per request */ });
    }
    if (document.readyState === "loading") { document.addEventListener("DOMContentLoaded", init); }
    else { init(); }
})();
