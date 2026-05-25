/** @odoo-module **/
(function () {
    "use strict";
    var AR = (window.ppcLang || "en") === "ar";

    /* ── helpers ──────────────────────────────────────────── */
    function t(en, ar) { return AR ? ar : en; }

    function bindDescBtns() {
        document.querySelectorAll(".ppc-see-more,.ppc-see-less").forEach(function(btn) {
            if (btn._b) return; btn._b = true;
            btn.addEventListener("click", function(e) {
                e.preventDefault(); e.stopPropagation(); e.stopImmediatePropagation();
                var block = btn.closest(".ppc-desc-block"); if (!block) return;
                var inner = block.querySelector(".ppc-desc-inner");
                var exp = inner.classList.toggle("ppc-expanded");
                var fw = block.querySelector(".ppc-fade-more");
                var mb = block.querySelector(".ppc-see-more");
                var lb = block.querySelector(".ppc-see-less");
                if (fw) fw.style.display = exp ? "none" : "";
                if (mb) mb.style.display = exp ? "none" : "block";
                if (lb) lb.style.display = exp ? "block" : "none";
            }, true);
        });
    }

    /* ── Slider ───────────────────────────────────────────── */
    var _sl = 0;
    window.ppcSlide = function(dir) {
        var vp=document.querySelector(".ppc-slider-viewport"),sl=document.getElementById("ppcSlider");
        if(!vp||!sl) return;
        var cards=sl.querySelectorAll(".ppc-slide-card"); if(!cards.length) return;
        var w=cards[0].offsetWidth+10, vis=Math.floor(vp.offsetWidth/w);
        _sl=Math.max(0,Math.min(_sl+dir,Math.max(0,cards.length-vis)));
        sl.style.transform="translateX("+(_sl*w*(AR?1:-1))+"px)";
    };

    /* ── Load More: infinite from same category, message when done ── */
    var _lmBusy=false;
    window.ppcLoadMore=function(btn){
        if(_lmBusy)return;
        var grid=document.getElementById("ppcRelGrid"); if(!grid)return;
        var wrap=document.getElementById("ppcLoadMoreWrap");
        var gridSec=document.getElementById("ppcGridSection");
        if(gridSec) gridSec.style.display="block";
        _lmBusy=true; btn.disabled=true; btn.textContent=t("Loading...","جاري...");

        // Serve from _allP cache first
        if(_shown < _allP.length){
            var next=_allP.slice(_shown, _shown+_ps);
            var cur=grid.dataset.cur||window.ppcCur||"KD";
            next.forEach(function(p){ appendCard(grid,p); });
            _shown+=next.length;
            _lmBusy=false;
            btn.disabled=false;
            btn.textContent=t("Load More","عرض المزيد");
            if(wrap)wrap.classList.remove("ppc-hidden");
            return;
        }

        // Cache exhausted: fetch more from server by same category
        var categ=parseInt(grid.dataset.categ||0);
        var prod=parseInt(grid.dataset.prod||0);
        var cur=grid.dataset.cur||window.ppcCur||"KD";
        fetch("/web/dataset/call_kw",{method:"POST",headers:{"Content-Type":"application/json"},
            body:JSON.stringify({jsonrpc:"2.0",method:"call",id:Date.now(),params:{
                model:"product.template",method:"search_read",
                args:[[["id","!=",prod],["is_published","=",true],["categ_id","=",categ]]],
                kwargs:{fields:["id","name","list_price","compare_list_price","website_url"],
                    limit:_ps, offset:_allP.length, order:"website_sequence asc, id asc"}}})
        }).then(function(r){return r.json();}).then(function(j){
            var res=j.result||[];
            res.forEach(function(p){
                var disc=p.compare_list_price>p.list_price+0.001
                    ?Math.round((1-p.list_price/p.compare_list_price)*100):0;
                var card={id:p.id,name:p.name||"",url:p.website_url||"/shop/"+p.id,
                    price:p.list_price||0,orig:p.compare_list_price||0,disc:disc,cur:cur};
                _allP.push(card);
                appendCard(grid, card);
            });
            _shown=_allP.length;
            _lmBusy=false;
            if(res.length===0){
                // All products shown
                if(wrap){
                    wrap.innerHTML='<div class="ppc-all-done">'+
                        (AR?"✓ هذه جميع المنتجات في هذا القسم":"✓ That's all products in this category")+
                    '</div>';
                }
            } else {
                btn.disabled=false;
                btn.textContent=t("Load More","عرض المزيد");
                if(wrap)wrap.classList.remove("ppc-hidden");
            }
        }).catch(function(){
            _lmBusy=false;btn.disabled=false;
            btn.textContent=t("Load More","عرض المزيد");
        });
    };

    function buildGridCard(p, cur, disc){
        var price=p.list_price||p.price||0;
        var orig=p.compare_list_price||p.orig||0;
        if(!disc && orig>price+0.001) disc=Math.round((1-price/orig)*100);
        var badge=disc?'<span class="ppc-card-badge">-'+disc+'%</span>':"";
        var pr='<span class="ppc-card-price">'+parseFloat(price).toFixed(3)+"&nbsp;"+(cur||window.ppcCur||"KD")+"</span>";
        if(disc)pr+='<span class="ppc-card-orig">'+parseFloat(orig).toFixed(3)+'</span><span class="ppc-card-disc-pill">-'+disc+'%</span>';
        var a=document.createElement("a");
        a.href=p.website_url||p.url||"/shop/"+p.id;
        a.className="ppc-product-card";
        a.innerHTML='<div class="ppc-card-img">'+badge+'<img src="/web/image/product.template/'+p.id+'/image_256" alt="" loading="lazy"/></div><div class="ppc-card-body"><div class="ppc-card-name">'+(p.name||"")+'</div><div class="ppc-card-prices">'+pr+'</div></div>';
        return a;
    }

    /* ══ INIT ═════════════════════════════════════════════ */
    function init() {
        if (!document.getElementById("product_detail")) return;
        // Immediate: price + WA navbar
        try { buildPriceRow(); } catch(e) {}
        try { buildWaSticky(); } catch(e) {}
        // 150ms: UI elements
        setTimeout(function(){
            try { addProductId(); } catch(e) {}
            try { buildBanner(); } catch(e) {}
            try { moveStockInline(); } catch(e) {}
            try { placeDesc(); } catch(e) {}
            try { truncateEcomDesc(); } catch(e) {}
        }, 150);
        // 400ms: heavier
        setTimeout(function(){
            try { fixColorSwatches(); } catch(e) {}
            try { fixWaBtn(); } catch(e) {}
            try { addCountry(); } catch(e) {}
            try { moveTabsToLayout(); } catch(e) {}
            try { activateReviewsTab(); } catch(e) {}
            try { enhanceBulkOrder(); } catch(e) {}
        }, 400);
        // 800ms: async load
        setTimeout(function(){
            try { loadRelated(); } catch(e) {}
            try { loadTopSelling(); } catch(e) {}
        }, 800);
        // Hide unknown input border (review filter)
        setTimeout(function(){
            var inputs = document.querySelectorAll(
                ".tab-content input[type='search'],.tp-review-search,.tp-rating-search,"+
                ".o_product_page_reviews input,.tp-reviews-top input"
            );
            inputs.forEach(function(el){ el.style.display="none"; });
        }, 600);
        // Normalize button heights via JS (override inline styles)
        setTimeout(normalizeButtons, 200);
        setTimeout(normalizeButtons, 800);
    }

    function normalizeButtons(){
        var H = "44px";
        var R = "10px";
        // Add to Cart
        var atc = document.getElementById("add_to_cart");
        if(atc){
            atc.style.setProperty("height", H, "important");
            atc.style.setProperty("min-height", H, "important");
            atc.style.setProperty("border-radius", R, "important");
            atc.style.setProperty("display", "inline-flex", "important");
            atc.style.setProperty("align-items", "center", "important");
            atc.style.setProperty("line-height", "1", "important");
            atc.style.setProperty("padding", "0 18px", "important");
        }
        // Qty
        var qty = document.querySelector(".css_quantity");
        if(qty){
            qty.style.setProperty("height", H, "important");
            qty.style.setProperty("border-radius", R, "important");
            qty.style.setProperty("display", "inline-flex", "important");
            qty.style.setProperty("align-items", "center", "important");
            // Qty buttons
            qty.querySelectorAll("button,.btn").forEach(function(b){
                b.style.setProperty("height", "42px", "important");
                b.style.setProperty("line-height", "1", "important");
                b.style.setProperty("display", "flex", "important");
                b.style.setProperty("align-items", "center", "important");
            });
            // Qty input
            var qin = qty.querySelector("input");
            if(qin){
                qin.style.setProperty("height", "42px", "important");
                qin.style.setProperty("line-height", "1", "important");
            }
        }
        // WA button
        var wa = document.querySelector(".ppc-wa-btn, a.ppc-wa-btn");
        if(wa){
            wa.style.setProperty("height", H, "important");
            wa.style.setProperty("min-height", H, "important");
            wa.style.setProperty("border-radius", R, "important");
            wa.style.setProperty("display", "inline-flex", "important");
            wa.style.setProperty("align-items", "center", "important");
            wa.style.setProperty("line-height", "1", "important");
        }
        // Fast Order (Zorder)
        var fo = document.querySelector('[class*="zorder"] a,[id*="zorder"] a,.tp-zorder-btn');
        if(fo){
            fo.style.setProperty("height", H, "important");
            fo.style.setProperty("min-height", H, "important");
            fo.style.setProperty("border-radius", R, "important");
            fo.style.setProperty("display", "inline-flex", "important");
            fo.style.setProperty("align-items", "center", "important");
            fo.style.setProperty("line-height", "1", "important");
        }
        // CTA wrapper
        var cta = document.getElementById("o_wsale_cta_wrapper");
        if(cta){
            cta.style.setProperty("display", "flex", "important");
            cta.style.setProperty("align-items", "center", "important");
            cta.style.setProperty("gap", "8px", "important");
        }
        var atcw = document.getElementById("add_to_cart_wrap");
        if(atcw){
            atcw.style.setProperty("display", "flex", "important");
            atcw.style.setProperty("align-items", "center", "important");
            atcw.style.setProperty("gap", "8px", "important");
        }
    }
    /* ── Truncate ecommerce description (product.description_ecommerce) ── */
    function truncateEcomDesc() {
        // Selectors for the ecom description block
        var selectors = [
            ".tp-ecommerce-description",
            "div.oe_structure.tp-ecommerce-description",
            "#product_details .oe_structure[data-oe-field='description_ecommerce']",
            "#product_details div[data-oe-field='description_ecommerce']"
        ];
        var el = null;
        for (var i = 0; i < selectors.length; i++) {
            el = document.querySelector(selectors[i]);
            if (el) break;
        }
        if (!el) return;

        // Only truncate if content is tall enough (more than 5 lines)
        var lineH = parseFloat(getComputedStyle(el).lineHeight) || 24;
        var threshold = lineH * 5 + 10;
        if (el.scrollHeight <= threshold) return;

        // Wrap in a container if not already
        var wrapper = el.parentElement;
        if (!wrapper.classList.contains("ppc-ecom-wrap")) {
            var wrap = document.createElement("div");
            wrap.className = "ppc-ecom-wrap";
            wrap.style.cssText = "position:relative;overflow:hidden;";
            el.parentNode.insertBefore(wrap, el);
            wrap.appendChild(el);

            // Fade overlay
            var fade = document.createElement("div");
            fade.className = "ppc-ecom-fade";
            wrap.appendChild(fade);

            // Toggle button
            var btn = document.createElement("button");
            btn.type = "button";
            btn.className = "ppc-ecom-toggle";
            btn.textContent = AR ? "عرض المزيد" : "See more";
            wrap.after(btn);

            // Apply truncation
            el.style.cssText = "max-height:" + threshold + "px;overflow:hidden;position:relative;transition:max-height .3s ease;";

            btn.addEventListener("click", function () {
                var expanded = el.classList.toggle("ppc-ecom-expanded");
                if (expanded) {
                    el.style.maxHeight = el.scrollHeight + "px";
                    fade.style.display = "none";
                    btn.textContent = AR ? "▲ عرض أقل" : "▲ See less";
                } else {
                    el.style.maxHeight = threshold + "px";
                    fade.style.display = "";
                    btn.textContent = AR ? "عرض المزيد" : "See more";
                }
            });
        }
    }

    /* ── 0. Product ID + viewers next to ratings ─────────── */
    function addProductId(){
        var prodId = window.ppcProd; if(!prodId) return;
        var ratingEl = document.querySelector(".o_product_page_reviews_link, .o_website_rating_static");
        if(!ratingEl) return;
        var wrap = ratingEl.closest(".d-flex,.mb-2") || ratingEl.parentElement;
        if(!wrap) return;

        // Add product ID
        if(!wrap.querySelector(".ppc-product-id")){
            var idBadge = document.createElement("span");
            idBadge.className = "ppc-product-id";
            idBadge.textContent = "ID: " + prodId;
            wrap.appendChild(idBadge);
        }

        // Add stock badge + hide viewers
        setTimeout(function(){
            // Stock badge — green bold no bg
            var stkEl = document.querySelector("#ppcStockInline .ppc-stk");
            if(stkEl && !wrap.querySelector(".ppc-stk-inline")){
                var stk = document.createElement("span");
                stk.className = "ppc-stk-inline";
                stk.innerHTML = stkEl.innerHTML;
                wrap.appendChild(stk);
            }
            // Hide ALL viewers
            var viewEls = document.querySelectorAll(".tp-views-indicator");
            if(viewEls) viewEls.forEach(function(el){
                try{
                    var c = el.closest(".d-inline-flex,.d-flex") || el.parentElement;
                    if(c) c.style.display = "none";
                    el.style.display = "none";
                }catch(e){}
            });
        }, 500);
    }

    /* ── 0b. Color swatches — ppc/variant_images endpoint ─ */
    function fixColorSwatches(){
        var tmplId = parseInt(window.ppcProd||0);
        if(!tmplId) return;

        // Fetch variant → ptav mapping from our custom endpoint
        fetch('/ppc/variant_images/'+tmplId, {
            method:'POST',
            headers:{'Content-Type':'application/json'},
            body:JSON.stringify({jsonrpc:'2.0',method:'call',id:1,params:{}})
        }).then(function(r){return r.json();}).then(function(d){
            var map = d.result||{};
            buildSwatches(map);
        }).catch(function(){ buildSwatches({}); });

        function buildSwatches(ptavMap){
            try {
                var colorAttrs = document.querySelectorAll(
                    '.variant_attribute[data-attribute_name="Color"],' +
                    '.variant_attribute[data-attribute_name="Colour"],' +
                    '.variant_attribute[data-attribute_name="colour"],' +
                    '.variant_attribute[data-attribute_display_type="color"]'
                );
                if(!colorAttrs.length) return;

                colorAttrs.forEach(function(attr){
                    if(attr.querySelector(".ppc-swatches-wrap")) return;
                    var items = attr.querySelectorAll("li.list-inline-item");
                    if(!items.length) return;

                    var swWrap = document.createElement("div");
                    swWrap.className = "ppc-swatches-wrap";

                    items.forEach(function(item){
                        var label   = item.querySelector("label.css_attribute_color");
                        var inp     = item.querySelector("input.js_variant_change");
                        if(!inp) return;
                        var ptavId  = inp.getAttribute("data-value_id")||inp.value||"";
                        var name    = inp.getAttribute("data-value_name")||inp.getAttribute("title")||"";
                        var bgColor = label ? label.style.background||label.style.backgroundColor||"" : "";
                        var isActive = label ? label.classList.contains("active") : inp.checked;

                        var varInfo = ptavMap[ptavId]||{};
                        var imgSrc  = varInfo.img||"";
                        var hasImg  = varInfo.has_img||false;

                        var card = document.createElement("div");
                        card.className = "ppc-sw-card"+(isActive?" ppc-sw-active":"");
                        card.setAttribute("data-ptav", ptavId);

                        var imgBox = document.createElement("div");
                        imgBox.className = "ppc-sw-imgbox";

                        if(imgSrc && hasImg){
                            var img = document.createElement("img");
                            img.className = "ppc-sw-img";
                            img.alt = name;
                            img.src = imgSrc;
                            img.onerror = function(){
                                img.style.display = "none";
                                imgBox.style.background = bgColor||"#ddd";
                                imgBox.style.borderRadius = "50%";
                            };
                            imgBox.appendChild(img);
                        } else if(imgSrc){
                            // Variant exists but uses template image
                            var img2 = document.createElement("img");
                            img2.className = "ppc-sw-img";
                            img2.alt = name;
                            img2.src = imgSrc;
                            img2.onerror = function(){
                                img2.style.display = "none";
                                imgBox.style.background = bgColor||"#ddd";
                                imgBox.style.borderRadius = "50%";
                            };
                            imgBox.appendChild(img2);
                        } else {
                            imgBox.style.background = bgColor||"#ddd";
                            imgBox.style.borderRadius = "50%";
                        }

                        // Footer: color dot + name
                        var footer = document.createElement("div");
                        footer.className = "ppc-sw-footer";
                        var dot = document.createElement("span");
                        dot.className = "ppc-sw-dot";
                        dot.style.background = bgColor||"#ddd";
                        var nameLbl = document.createElement("span");
                        nameLbl.className = "ppc-sw-name";
                        nameLbl.textContent = name;
                        footer.appendChild(dot);
                        footer.appendChild(nameLbl);
                        card.appendChild(imgBox);
                        card.appendChild(footer);

                        card.addEventListener("click", function(){
                            swWrap.querySelectorAll(".ppc-sw-card").forEach(function(c){
                                c.classList.remove("ppc-sw-active");
                            });
                            card.classList.add("ppc-sw-active");
                            inp.click();
                        });

                        if(label){
                            var mo = new MutationObserver(function(){
                                card.classList.toggle("ppc-sw-active", label.classList.contains("active"));
                            });
                            mo.observe(label, {attributes:true, attributeFilter:["class"]});
                        }

                        swWrap.appendChild(card);
                    });

                    var origUl = attr.querySelector("ul");
                    if(origUl){
                        origUl.style.display = "none";
                        origUl.parentNode.insertBefore(swWrap, origUl.nextSibling);
                    }
                });
            } catch(e){ console.warn("PPC swatches:", e); }
        }
    }
    /* ── 1. Banner — G3 Floating card ───────────────────── */
    function buildBanner() {
        if (document.getElementById("ppcBanner")) return;
        var price = window.ppcPrice||0; if(!price) return;
        var installment = (price/4).toFixed(3);
        var cur = window.ppcCur||"KD";

        var txtTitle = AR ? "4 أقساط · 0% فائدة"      : "Pay in 4 · 0% interest";
        var txtDesc  = AR ? "خصم تلقائي · بدون رسوم"  : "Auto deduction · No fees";
        var txtApr   = AR ? "0% فائدة"                 : "0% APR";
        var txtSec   = AR ? "✓ آمن"                    : "✓ Secure";
        var labels   = AR
            ? ["القسط 1 · الآن","القسط 2 · شهر 1","القسط 3 · شهر 2","القسط 4 · شهر 3"]
            : ["1st · Now","2nd · Mo 1","3rd · Mo 2","4th · Mo 3"];

        var pillsHtml = labels.map(function(lbl,i){
            return '<div class="ppc-bn-pill'+(i===0?" ppc-bn-on":"")+'" data-idx="'+i+'">' +
                '<div class="ppc-bn-pn">'+lbl+'</div>' +
                '<div class="ppc-bn-pa">'+installment+'</div>' +
                '<div class="ppc-bn-pk">'+cur+'</div>' +
            '</div>';
        }).join("");

        var el = document.createElement("div");
        el.id = "ppcBanner";
        el.setAttribute("dir", AR?"rtl":"ltr");
        el.innerHTML =
            '<div class="ppc-bn3">' +
                '<div class="ppc-bn3-hd">' +
                    '<div class="ppc-bn3-l">' +
                        '<div class="ppc-bn3-ring">' +
                            '<svg width="10" height="10" viewBox="0 0 24 24" fill="#f97316"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>' +
                        '</div>' +
                        '<div>' +
                            '<div class="ppc-bn3-t">'+txtTitle+'</div>' +
                            '<div class="ppc-bn3-d">'+txtDesc+'</div>' +
                        '</div>' +
                    '</div>' +
                    '<div class="ppc-bn3-r">' +
                        '<span class="ppc-bn3-b1">'+txtApr+'</span>' +
                        '<span class="ppc-bn3-b2">'+txtSec+'</span>' +
                    '</div>' +
                '</div>' +
                '<div class="ppc-bn3-divider"></div>' +
                '<div class="ppc-bn3-pills">' +
                    '<div class="ppc-bn3-row">'+pillsHtml+'</div>' +
                '</div>' +
            '</div>';

        // Insert after h1
        var h1 = document.querySelector("h1[itemprop='name'],h1.product_name,h1");
        if(h1 && h1.parentNode) h1.parentNode.insertBefore(el, h1.nextSibling);

        // Animate cycling
        var cur2 = 0;
        setInterval(function(){
            el.querySelectorAll(".ppc-bn-pill").forEach(function(p){ p.classList.remove("ppc-bn-on"); });
            cur2 = (cur2+1)%4;
            var active = el.querySelectorAll(".ppc-bn-pill")[cur2];
            if(active) active.classList.add("ppc-bn-on");
        }, 1700);
    }
    /* ── 2. Price row ─────────────────────────────────────── */
    function buildPriceRow() {
        // Only hide on product detail page (has #product_detail), not shop listing
        if (!document.getElementById("product_detail")) return;
        document.querySelectorAll("#product_details .o_wsale_product_price, #product_details .product_price").forEach(function(el){el.style.cssText="display:none !important";});
        if(document.getElementById("ppcPriceRow"))return;
        var price=window.ppcPrice||0,orig=window.ppcOrig||0,cur=window.ppcCur||"KD";
        if(!price)return;
        var row=document.createElement("div");row.id="ppcPriceRow";row.className="ppc-price-row";
        if(orig&&orig>price+0.001){
            var pct=Math.round((1-price/orig)*100),sav=(orig-price).toFixed(3);
            row.innerHTML='<span class="ppc-pr-price">'+price.toFixed(3)+" "+cur+"</span>"+'<span class="ppc-pr-orig">'+orig.toFixed(3)+" "+cur+"</span>"+'<span class="ppc-pr-pct">-'+pct+"%</span>"+'<span class="ppc-pr-save">'+t("Save ","توفير ")+sav+" "+cur+"</span>";
        } else {
            row.innerHTML='<span class="ppc-pr-price">'+price.toFixed(3)+" "+cur+"</span>";
        }
        var anchor=document.querySelector("#product_details .o_wsale_product_price,#product_details .product_price,#add_to_cart");
        if(anchor)anchor.insertAdjacentElement("beforebegin",row);
    }

    /* ── 3. WA = same size as Buy Now ─────────────────────── */
    function fixWaBtn() {
        if(window.innerWidth < 768) return;
        var tries=0;
        function apply(){
            return !!document.getElementById("add_to_cart");
        }
        function retry(){ if(!apply() && ++tries<10) setTimeout(retry,400); }
        setTimeout(retry,200);
    }
    /* ── 4. Stock + delivery inline with qty ──────────────── */
    function moveStockInline() {
        var stockEl=document.getElementById("ppcStockInline");
        if(stockEl) stockEl.style.display="none";
        setTimeout(function(){
            document.querySelectorAll(".ppc-ship,.ppc-express,#ppcShipBadge,.ppc-delivery-row").forEach(function(el){
                el.style.display="none";
                var p=el.parentElement; if(p) p.style.display="none";
            });
        },300);
    }
    /* ── 5. Add country + delivery date to badges ─────────── */
    function addCountry() {
        var badge=document.getElementById("ppcShipBadge"); if(!badge)return;
        // Compute tomorrow's date
        var tomorrow=new Date(); tomorrow.setDate(tomorrow.getDate()+1);
        var months=["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
        var arMonths=["يناير","فبراير","مارس","أبريل","مايو","يونيو","يوليو","أغسطس","سبتمبر","أكتوبر","نوفمبر","ديسمبر"];
        var dateStr = AR
            ? tomorrow.getDate()+" "+arMonths[tomorrow.getMonth()]
            : months[tomorrow.getMonth()]+" "+tomorrow.getDate();

        fetch("https://ipapi.co/country_name/")
            .then(function(r){return r.text();})
            .then(function(c){
                c=(c||"").trim(); if(!c||c.length>40||c.includes("<"))c="";
                var countryPart = c ? (AR?" إلى "+c:(" to "+c)) : "";
                var svg12='<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="flex-shrink:0"><rect x="1" y="3" width="15" height="13"/><path d="M16 8h4l3 3v5h-7V8z"/><circle cx="5.5" cy="18.5" r="2.5"/><circle cx="18.5" cy="18.5" r="2.5"/></svg>';
                if(AR){
                    badge.innerHTML=svg12+'استلم'+countryPart+' '+dateStr;
                } else {
                    badge.innerHTML=svg12+'Arrives'+countryPart+': '+dateStr;
                }
            }).catch(function(){});

        // Express badge is static in XML - no JS override needed
    }

    /* ── 6. Place desc into Description tab ──────────────── */
    function filterDescLang(block){
        if(!block) return;
        var inner = block.querySelector(".ppc-desc-inner, .o_field_html");
        if(!inner) inner = block;
        // Get all direct children (p, div, ul, etc)
        var children = inner.children;
        for(var i=0; i<children.length; i++){
            var el = children[i];
            var txt = el.textContent || "";
            if(!txt.trim()) continue;
            // Detect Arabic text by Unicode range
            var arChars = (txt.match(/[\u0600-\u06FF]/g)||[]).length;
            var totalChars = txt.replace(/\s/g,"").length;
            var isArabic = totalChars > 0 && (arChars/totalChars) > 0.3;
            if(AR && !isArabic) el.style.display = "none";
            else if(!AR && isArabic) el.style.display = "none";
        }
    }

    function placeDesc() {
        var block=document.getElementById("ppcDescBlock"); if(!block)return;

        // Add title to desc wrapper if not already there
        var wrapper=block.querySelector(".ppc-desc-wrapper");
        if(wrapper && !wrapper.querySelector(".ppc-desc-title")){
            var titleEl=document.createElement("div");
            titleEl.className="ppc-desc-title";
            titleEl.innerHTML=
                '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14,2 14,8 20,8"/></svg>'+
                (AR?"وصف المنتج":"Product Description");
            wrapper.insertBefore(titleEl, wrapper.firstChild);
        }

        bindDescBtns();
        var descPane=document.getElementById("tp-product-description-tab");
        if(descPane){
            var inner=descPane.querySelector(".col-12,.container-fluid")||descPane;
            inner.innerHTML="";
            block.style.cssText="display:block !important;";
            block.classList.add("ppc-desc-ready");
            inner.appendChild(block);
            bindDescBtns();
            return;
        }
        // fallback
        var h1=document.querySelector("h1[itemprop='name'],h1.product_name,h1");
        var col=h1&&(h1.closest(".col-lg-6,.col-md-6,.col-6")||h1.parentElement);
        if(col)col.appendChild(block);
        block.style.cssText="display:block !important;width:100% !important;";
        // Add progress bar to description
        if(!block.querySelector(".ppc-desc-progress")){
            var prog = document.createElement("div");
            prog.className = "ppc-desc-progress";
            prog.innerHTML = '<div class="ppc-desc-progress-fill"></div>';
            block.appendChild(prog);
        }
        // Hide wrong-language content
        filterDescLang(block);
        block.classList.add("ppc-desc-ready");
        bindDescBtns();
    }

    /* ── 7. Load related slider + grid ───────────────────── */
    var _allP=[],_shown=0,_ps=12;
    function loadRelated(){
        var prodId=window.ppcProd||0; if(!prodId)return;
        var section=document.getElementById("ppcRelatedSection");
        fetch("/ppc/related/"+prodId,{method:"POST",headers:{"Content-Type":"application/json"},
            body:JSON.stringify({jsonrpc:"2.0",method:"call",id:Date.now(),params:{}})
        }).then(function(r){return r.json();}).then(function(j){
            var products=j.result||[]; if(!products.length)return;
            _allP=products;_shown=0;
            if(section)section.style.display="";
            // slider
            var slider=document.getElementById("ppcSlider");
            if(slider) products.slice(0,15).forEach(function(p){
                var price=p.price||0,cur=p.cur||window.ppcCur||"KD",disc=p.disc||0;
                var badge=disc?'<span class="ppc-slide-badge">-'+disc+'%</span>':"";
                var a=document.createElement("a");a.href=p.url||"/shop/"+p.id;a.className="ppc-slide-card";
                a.innerHTML='<div class="ppc-slide-img">'+badge+'<img src="/web/image/product.template/'+p.id+'/image_256" alt="" loading="lazy"/></div>'+
                    '<div class="ppc-slide-name">'+(p.name||"")+'</div>'+
                    '<div class="ppc-slide-prices">'+
                        '<span class="ppc-slide-price">'+price.toFixed(3)+"&nbsp;"+cur+'</span>'+
                        (p.orig&&p.orig>price+0.001?'<span class="ppc-slide-orig">'+p.orig.toFixed(3)+'</span><span class="ppc-slide-disc">-'+disc+'%</span>':'')+
                    '</div>';
                slider.appendChild(a);
            });
            // grid
            var grid=document.getElementById("ppcRelGrid"),gridSec=document.getElementById("ppcGridSection");
            if(grid){
                if(gridSec)gridSec.style.display="";
                products.slice(0,15).forEach(function(p){appendCard(grid,p);});
                _shown=Math.min(_ps,products.length);
            }
            var wrap=document.getElementById("ppcLoadMoreWrap");
            if(wrap){if(products.length>_ps)wrap.classList.remove("ppc-hidden");else wrap.classList.add("ppc-hidden");}
        }).catch(function(){});
    }

    function appendCard(grid,p){
        var cur=p.cur||window.ppcCur||"KD";
        grid.appendChild(buildGridCard(p, cur, p.disc||0));
    }

    /* ── 8. Top Selling ───────────────────────────────────── */
    function loadTopSelling(){
        var list=document.getElementById("ppcTopSellingList"); if(!list)return;

        // Update header to "New In" with spark icon
        var header=list.parentElement&&list.parentElement.querySelector(".ppc-ts-header");
        if(header){
            header.innerHTML=
                '<span class="ppc-ts-icon">'+
                    '<svg width="16" height="16" viewBox="0 0 24 24" fill="#f5a623"><path d="M12 2l2.4 7.4H22l-6.2 4.5 2.4 7.4L12 17l-6.2 4.3 2.4-7.4L2 9.4h7.6z"/></svg>'+
                '</span>'+
                (AR?'وصل حديثاً ✨':'New In ✨');
        }

        fetch("/ppc/top_selling",{method:"POST",headers:{"Content-Type":"application/json"},
            body:JSON.stringify({jsonrpc:"2.0",method:"call",id:Date.now(),params:{categ_id:window.ppcCatg||0,prod_id:window.ppcProd||0}})
        }).then(function(r){return r.json();}).then(function(j){
            var products=j.result||[];
            if(!products.length){
                // Fallback: load any published products
                fetch("/web/dataset/call_kw",{method:"POST",headers:{"Content-Type":"application/json"},
                    body:JSON.stringify({jsonrpc:"2.0",method:"call",id:Date.now(),params:{
                        model:"product.template",method:"search_read",
                        args:[[["is_published","=",true]]],
                        kwargs:{fields:["id","name","list_price","website_url"],limit:5,order:"id desc"}}})
                }).then(function(r2){return r2.json();}).then(function(j2){
                    renderTopSelling(list,j2.result||[]);
                }).catch(function(){});
                return;
            }
            renderTopSelling(list,products);
        }).catch(function(err){
            console.warn("PPC top_selling error:", err);
            // Emergency fallback: load any 5 products
            fetch("/web/dataset/call_kw",{method:"POST",headers:{"Content-Type":"application/json"},
                body:JSON.stringify({jsonrpc:"2.0",method:"call",id:Date.now(),params:{
                    model:"product.template",method:"search_read",
                    args:[[["is_published","=",true]]],
                    kwargs:{fields:["id","name","list_price","website_url"],limit:5,order:"id desc"}}})
            }).then(function(r){return r.json();}).then(function(j){
                renderTopSelling(list, (j.result||[]).map(function(p){
                    return {id:p.id,name:p.name,url:p.website_url,price:p.list_price,cur:window.ppcCur||"KD"};
                }));
            }).catch(function(){});
        });
    }

    function renderTopSelling(list, products){
        list.innerHTML="";
        products.slice(0,3).forEach(function(p){
            var price=(p.price||p.list_price||0);
            var cur=p.cur||window.ppcCur||"KD";
            var url=p.url||p.website_url||"/shop/"+p.id;
            var a=document.createElement("a");a.href=url;a.className="ppc-ts-item";
            a.innerHTML='<div class="ppc-ts-img"><img src="/web/image/product.template/'+p.id+'/image_256" alt="" loading="lazy" style="width:100%;height:100%;object-fit:cover;display:block;"/></div>'+
                '<div class="ppc-ts-info"><div class="ppc-ts-price">'+parseFloat(price).toFixed(3)+"&nbsp;"+cur+'</div><div class="ppc-ts-name">'+(p.name||"")+"</div></div>";
            list.appendChild(a);
        });
    }

    /* ── 9. Move Theme Prime tabs into our layout (safe) ──── */
    function moveTabsToLayout(){
        // Delay to let Odoo initialize its widgets first
        setTimeout(function(){
            try {
                var col=document.getElementById("ppcTabsCol"); if(!col)return;
                var tpTabs=document.querySelector(".tp-hook-product-tabs .tp-product-details-tab")||
                           document.querySelector(".tp-product-details-tab");
                if(tpTabs && tpTabs.parentNode !== col) col.appendChild(tpTabs);
            } catch(e) { console.warn("PPC moveTabsToLayout:", e); }
        }, 1200);
    }

    /* ── 10. Activate Reviews tab by default ──────────────── */
    function activateReviewsTab(){
        setTimeout(function(){
            // Find Reviews & Rating tab link
            var tabs=document.querySelectorAll(".tp-product-details-tab .nav-link,[data-bs-toggle='tab']");
            var ratingTab=null,descTab=null;
            tabs.forEach(function(tab){
                var txt=(tab.textContent||"").toLowerCase();
                if(txt.includes("review")||txt.includes("rating")||txt.includes("تقييم"))ratingTab=tab;
                if(txt.includes("description")||txt.includes("وصف"))descTab=tab;
            });
            // Deactivate description tab
            if(descTab){
                descTab.classList.remove("active");
                var descPane=document.querySelector(descTab.getAttribute("href")||descTab.dataset.bsTarget||"#x");
                if(descPane){descPane.classList.remove("show","active");}
            }
            // Activate reviews tab
            if(ratingTab){
                ratingTab.classList.add("active");
                var paneId=ratingTab.getAttribute("href")||ratingTab.dataset.bsTarget;
                if(paneId){
                    var pane=document.querySelector(paneId);
                    if(pane)pane.classList.add("show","active");
                }
            }
        },400);
    }

    /* ── Bulk Order F: custom block replaces original ──────── */
    function enhanceBulkOrder(){
        var tmplId = window.ppcProd;
        if(!tmplId) return;

        function buildFromApi(){
            if(document.getElementById("ppcBulkCustom")) return;
            fetch("/ppc/bulk_pricing/"+tmplId,{
                method:"POST",headers:{"Content-Type":"application/json"},
                body:JSON.stringify({jsonrpc:"2.0",method:"call",id:1,params:{}})
            }).then(function(r){return r.json();}).then(function(d){
                var items = d.result||[];
                if(!items.length) return;
                buildBulkFromApi(items);
            }).catch(function(){});
        }

        function buildBulkFromApi(items){
            if(document.getElementById("ppcBulkCustom")) return;
            var container = document.querySelector(".tp-bulk-price-container,.tp-bulk-price");
            if(!container){
                // Create our own container
                container = document.createElement("div");
                container.className = "tp-bulk-price-container";
                var priceEl = document.querySelector(".ppc-pr-price,.o_sale_price");
                if(priceEl && priceEl.parentNode){
                    priceEl.parentNode.insertBefore(container, priceEl.nextSibling);
                } else {
                    var h1 = document.querySelector("h1");
                    if(h1 && h1.parentNode) h1.parentNode.appendChild(container);
                    else return;
                }
            }

            // Build fake cells for buildBulk to consume
            var basePrice = window.ppcPrice || items[0].orig;
            // Prepend tier 0 (no discount)
            var allTiers = [{min_qty:1, price:basePrice, orig:basePrice, disc:0}].concat(items);
            var tiers = allTiers.map(function(item){
                return {
                    qty: item.min_qty === 1 ? (AR?"١":"1") : (AR?"":"") + item.min_qty + "+",
                    price: item.price,
                    orig: item.orig,
                    minQty: item.min_qty
                };
            });

            // Directly call the core build logic
            buildBulkDirect(tiers, container);
        }

        // Try Theme Prime container first, fallback to API
        var tries = 0;
        function tryTP(){
            if(document.getElementById("ppcBulkCustom")) return;
            var container = document.querySelector(".tp-bulk-price-container");
            var cells = container ? container.querySelectorAll(".tp-bulk-price-block") : [];
            if(cells.length){
                buildBulk(container, cells);
            } else if(++tries < 6){
                setTimeout(tryTP, 500);
            } else {
                buildFromApi();
            }
        }
        // Start immediately and after combination info
        setTimeout(tryTP, 400);
        // Also try directly from API right away as fallback
        setTimeout(function(){ if(!document.getElementById("ppcBulkCustom")) buildFromApi(); }, 3500);

        // Rebuild after variant change
        if(window.$){
            $(document).on("get_combination_info", function(){
                setTimeout(function(){
                    var old = document.getElementById("ppcBulkCustom");
                    if(old) old.remove();
                    var container = document.querySelector(".tp-bulk-price-container");
                    var cells = container ? container.querySelectorAll(".tp-bulk-price-block") : [];
                    if(cells.length) buildBulk(container, cells);
                    else buildFromApi();
                }, 300);
            });
        }
    }

    function buildBulkDirect(tiers, container){
        if(document.getElementById("ppcBulkCustom")) return;
        var cur = window.ppcCur||"KD";
        var activeIdx = 0;
        var maxDisc = 0;
        tiers.forEach(function(t){ var p=t.orig>t.price+.001?Math.round((1-t.price/t.orig)*100):0; if(p>maxDisc)maxDisc=p; });
        var n = tiers.length;
        var progId = "ppcBulkProg_"+Date.now();

        var wrap = document.createElement("div");
        wrap.className = "ppc-bulk-wrap";
        wrap.id = "ppcBulkCustom";
        if(AR) wrap.setAttribute("dir","rtl");

        wrap.innerHTML =
            '<div class="ppc-bulk-hd">'+
                '<div class="ppc-bulk-top">'+
                    '<div class="ppc-bulk-left">'+
                        '<div class="ppc-bulk-ico"><svg width="12" height="12" viewBox="0 0 24 24" fill="#0284c7"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg></div>'+
                        '<div><div class="ppc-bulk-title">'+t("Bulk Discounts","خصومات الكميات")+'</div>'+
                        '<div class="ppc-bulk-subtitle">'+t("More = cheaper","كلما زادت انخفض السعر")+'</div></div>'+
                    '</div>'+
                    '<div class="ppc-bulk-prog-track"><div class="ppc-bulk-prog-fill" id="'+progId+'" style="width:5%"></div></div>'+
                    '<div class="ppc-bulk-right">'+
                        '<span class="ppc-bulk-b1">'+(AR?"← مرر":"scroll →")+'</span>'+
                        '<span class="ppc-bulk-b2">-'+maxDisc+'% max</span>'+
                    '</div>'+
                '</div>'+
            '</div>'+
            '<div class="ppc-bulk-row" id="ppcBulkRow_'+progId+'"></div>';

        container.parentNode.insertBefore(wrap, container.nextSibling);
        wrap.style.display = "";

        var row = wrap.querySelector("[id^='ppcBulkRow']");

        function renderCells(){
            row.innerHTML = "";
            var display = AR ? tiers.slice().reverse() : tiers;
            display.forEach(function(tier,di){
                var ri = AR?(n-1-di):di;
                var on = ri===activeIdx;
                var pct = tier.orig>tier.price+.001?Math.round((1-tier.price/tier.orig)*100):0;
                var sv  = tier.orig>tier.price+.001?(tier.orig-tier.price).toFixed(3):null;
                var cell = document.createElement("div");
                cell.className = "ppc-bulk-cell"+(on?" ppc-bulk-on":"");
                var saveHtml = sv?'<span class="ppc-bulk-save-pill">'+t("Save","وفّر")+" "+sv+'</span>':'<span class="ppc-bulk-nodisc">'+t("No discount","لا خصم")+'</span>';
                cell.innerHTML =
                    (on?'<div class="ppc-bulk-tag">'+t("✓ Active","✓ مفعّل")+'</div>':'')+
                    '<div class="ppc-bulk-cell-in">'+
                        '<div class="ppc-bulk-qty">'+tier.qty+'</div>'+
                        '<div class="ppc-bulk-price-row">'+
                            '<span class="ppc-bulk-price">'+tier.price.toFixed(3)+'</span>'+
                            '<span class="ppc-bulk-kd">'+cur+'</span>'+
                            (sv?'<span class="ppc-bulk-orig-inline">'+tier.orig.toFixed(3)+'</span>':'')+
                        '</div>'+
                        '<div class="ppc-bulk-meta-row">'+
                            (pct>0?'<span class="ppc-bulk-disc-badge">-'+pct+'%</span>':'<span class="ppc-bulk-disc-badge" style="visibility:hidden">0%</span>')+
                            (sv?'<span class="ppc-bulk-save-pill">'+t("Save","وفّر")+' '+sv+'</span>':'<span class="ppc-bulk-nodisc">—</span>')+
                        '</div>'+
                    '</div>';
                cell.addEventListener("click",(function(i){return function(){
                    activeIdx=i;renderCells();
                    var pEl=document.getElementById(progId);
                    if(pEl) pEl.style.width=Math.max(5,Math.round((i/(n-1))*100))+"%";
                };})(ri));
                row.appendChild(cell);
            });
        }
        renderCells();
    }

    function buildBulk(container, cells){
        var tiers = [];
        var basePrice = window.ppcPrice||0;
        var baseOrig  = window.ppcOrig||0;
        var cur2 = window.ppcCur||"KD";

        // Pricelist discount map: minQty → disc%
        // Derived from Kuwait Main pricelist rules
        var plRules = [
            {minQty:2,  disc:5},
            {minQty:3,  disc:6},
            {minQty:5,  disc:10},
            {minQty:10, disc:20}
        ];

        cells.forEach(function(cell){
            var qtyEl  = cell.querySelector("small.fw-light");
            var priceEl= cell.querySelector("h5");
            var rawQty  = qtyEl ? qtyEl.textContent.trim() : "";
            var price  = priceEl ? parseFloat((priceEl.textContent||"").replace(/[^0-9.]/g,"")) : 0;
            var firstNum = (rawQty||"").match(/\d+/);
            var minQty = firstNum ? parseInt(firstNum[0]) : 1;
            // Clean qty label: "2 Units at" → "2+", keep Arabic numerals
            var qty = AR ? String(minQty).replace(/\d/g,function(d){return "٠١٢٣٤٥٦٧٨٩"[d];})+(minQty>1?"+":"") : (minQty>1?minQty+"+":"1");
            if(price && !basePrice) basePrice = price;
            tiers.push({qty:qty, price:price, minQty:minQty});
        });
        if(!tiers.length) return;

        // List price = base price (before any discount)
        // Derive from pricelist: price = listPrice * (1 - disc/100)
        // So listPrice = price / (1 - disc/100)
        var listPrice = window.ppcOrig || window.ppcPrice || basePrice;

        // If ppcOrig not set, reverse-calculate from first discounted tier
        if(!listPrice || listPrice <= basePrice) {
            // find first tier with a known disc%
            for(var ri=0;ri<plRules.length;ri++){
                var rule = plRules[ri];
                // find matching tier
                for(var ti=0;ti<tiers.length;ti++){
                    if(tiers[ti].minQty === rule.minQty && tiers[ti].price > 0){
                        listPrice = tiers[ti].price / (1 - rule.disc/100);
                        break;
                    }
                }
                if(listPrice > basePrice) break;
            }
        }
        if(!listPrice) listPrice = basePrice;

        // Assign orig (list price) to all tiers
        tiers.forEach(function(tier){
            tier.orig = listPrice;
        });

        // Prepend tier 0 = "1 unit" at list price (no discount)
        // Set orig=listPrice for all discount tiers
        tiers.forEach(function(tier){ tier.orig = listPrice; });
        tiers.unshift({qty: AR?"١":"1", price:listPrice, orig:listPrice, minQty:1});

        var activeIdx = 0;
        var cur = window.ppcCur||"KD";

        // Calc max discount
        var maxDisc = 0;
        tiers.forEach(function(t){
            if(t.orig>t.price+0.001){ var d=Math.round((1-t.price/t.orig)*100); if(d>maxDisc)maxDisc=d; }
        });

        // Build wrap
        var wrap = document.createElement("div");
        wrap.className = "ppc-bulk-wrap";
        wrap.id = "ppcBulkCustom";
        if(AR) wrap.setAttribute("dir","rtl");

        // Header
        var progId = "ppcBulkProg_"+Date.now();
        wrap.innerHTML =
            '<div class="ppc-bulk-hd">'+
                '<div class="ppc-bulk-top">'+
                    '<div class="ppc-bulk-left">'+
                        '<div class="ppc-bulk-ico"><svg width="12" height="12" viewBox="0 0 24 24" fill="#92400e"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg></div>'+
                        '<div>'+
                            '<div class="ppc-bulk-title">'+t("Bulk Discounts","خصومات الكميات")+'</div>'+
                            '<div class="ppc-bulk-subtitle">'+t("More = cheaper","كلما زادت انخفض السعر")+'</div>'+
                        '</div>'+
                    '</div>'+
                    '<div class="ppc-bulk-prog-track"><div class="ppc-bulk-prog-fill" id="'+progId+'" style="width:5%"></div></div>'+
                    '<div class="ppc-bulk-right">'+
                        '<span class="ppc-bulk-b1">'+(AR?"← مرر":"scroll →")+'</span>'+
                        '<span class="ppc-bulk-b2">-'+maxDisc+'% max</span>'+
                    '</div>'+
                '</div>'+
            '</div>'+
            '<div class="ppc-bulk-row" id="ppcBulkRow"></div>';

        container.parentNode.insertBefore(wrap, container.nextSibling);
        wrap.style.display = ""; // ensure visible
        var row = wrap.querySelector("#ppcBulkRow");

        function updateMainPrice(tierIdx){
            var tier = tiers[tierIdx];
            var p = tier.price, o = tier.orig||0, cur2 = window.ppcCur||"KD";
            var prEl = document.querySelector(".ppc-pr-price");
            if(prEl) prEl.textContent = p.toFixed(3)+" "+cur2;
            var pctEl = document.querySelector(".ppc-pr-pct");
            if(pctEl && o>p+0.001) pctEl.textContent = "-"+Math.round((1-p/o)*100)+"%";
            var svEl = document.querySelector(".ppc-pr-save");
            if(svEl && o>p+0.001) svEl.textContent = t("Save ","توفير ")+(o-p).toFixed(3)+" "+cur2;
            document.querySelectorAll("#product_details .oe_currency_value").forEach(function(el){ el.textContent = p.toFixed(3); });
            var qi = document.querySelector("input[name='add_qty'],input.quantity");
            if(qi){
                // tier 0 = 1 unit → always reset qty to 1
                var newQty = tierIdx === 0 ? 1 : tier.minQty;
                qi.value = newQty;
                qi.dispatchEvent(new Event("change"));
            }
        }

        function renderCells(){
            row.innerHTML="";
            var n = tiers.length;
            // In RTL, display tiers right-to-left (reverse visual order)
            var displayTiers = AR ? tiers.slice().reverse() : tiers;
            var activeDisplayIdx = AR ? (n-1-activeIdx) : activeIdx;
            displayTiers.forEach(function(tier,idx){
                var realIdx = AR ? (n-1-idx) : idx;
                var on = realIdx===activeIdx;
                var pct = tier.orig>tier.price+0.001?Math.round((1-tier.price/tier.orig)*100):0;
                var sv  = tier.orig>tier.price+0.001?(tier.orig-tier.price).toFixed(3):null;
                var cell = document.createElement("div");
                cell.className = "ppc-bulk-cell"+(on?" ppc-bulk-on":"");

                var saveHtml = sv
                    ? '<span class="ppc-bulk-save-pill">'+t("Save","وفّر")+" "+sv+'</span>'
                    : '<span class="ppc-bulk-nodisc">'+t("No discount","لا خصم")+'</span>';
                var discHtml = pct>0
                    ? '<span class="ppc-bulk-disc-badge">-'+pct+'%</span>'
                    : '';

                cell.innerHTML =
                    (on?'<div class="ppc-bulk-tag">'+t("✓ Active","✓ مفعّل")+'</div>':'')+
                    '<div class="ppc-bulk-cell-in">'+
                        '<div class="ppc-bulk-qty">'+tier.qty+'</div>'+
                        '<div class="ppc-bulk-price">'+tier.price.toFixed(3)+'<span class="ppc-bulk-kd"> '+cur+'</span></div>'+
                        (sv?'<div class="ppc-bulk-orig"><span class="ppc-bulk-orig-inner">'+tier.orig.toFixed(3)+' '+cur+'</span></div>':'<div class="ppc-bulk-orig"></div>')+
                        '<div class="ppc-bulk-save-wrap">'+saveHtml+'</div>'+
                        '<div class="ppc-bulk-disc">'+discHtml+'</div>'+
                    '</div>';

                cell.addEventListener("click", function(ri){ return function(){
                    activeIdx=ri;
                    renderCells();
                    updateMainPrice(ri);
                    var pEl=document.getElementById(progId);
                    if(pEl) pEl.style.width=Math.max(5,Math.round((ri/(n-1))*100))+"%";
                };}(realIdx));
                row.appendChild(cell);
            });
        }
        renderCells();

        // Qty input auto-select tier
        var qi = document.querySelector("input[name='add_qty'],input.quantity");
        if(qi){
            qi.addEventListener("change", function(){
                var qty=parseInt(qi.value)||1, best=0;
                tiers.forEach(function(tier,i){ if(qty>=tier.minQty) best=i; });
                if(best!==activeIdx){ activeIdx=best; renderCells(); updateMainPrice(best); }
            });
        }
    }

    /* ── Custom navbar NB-A with Fast Order ─────────────── */
    function buildWaSticky(){
        if(!window.ppcWa) return;

        var waUrl = "https://wa.me/" + window.ppcWa.replace(/[^0-9]/g,"");
        var h1 = document.querySelector("h1[itemprop='name'],h1.product_name,h1");
        if(h1) waUrl += "?text=" + encodeURIComponent(
            (AR ? "مرحباً، أريد طلب: " : "Hello, I'd like to order: ") +
            h1.textContent.trim() + "\n" + location.href
        );
        var price = window.ppcPrice ? window.ppcPrice.toFixed(3) : "";
        var cur   = window.ppcCur || "KD";

        var waSvg = '<svg style="fill:#fff;width:13px;height:13px;flex-shrink:0;" viewBox="0 0 24 24"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z M12 0C5.373 0 0 5.373 0 12c0 2.126.556 4.121 1.525 5.847L.5 23.5l5.821-1.005C7.973 23.46 9.95 24 12 24c6.627 0 12-5.373 12-12S18.627 0 12 0z"/></svg>';
        var cartSvg = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#1c1007" stroke-width="2.5" style="flex-shrink:0;"><circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/></svg>';
        var ltSvg  = '<svg width="11" height="11" viewBox="0 0 24 24" fill="#fff" style="flex-shrink:0;"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>';

        // Find Fast Order button URL from Zorder module
        var foBtn = document.querySelector('[class*="zorder"] a, [id*="zorder"] a, a[href*="zorder"]');
        var foUrl = foBtn ? foBtn.href : "#";
        var foBadge = AR ? "بـ 5 ثوان" : "in 5 Sec";
        var foLabel = AR ? "طلب سريع" : "Fast Order";

        var nav = document.createElement("div");
        nav.id = "ppcNavbar";
        nav.setAttribute("dir", AR ? "rtl" : "ltr");
        nav.innerHTML =
            '<div class="ppc-nb-inner">' +
                '<div class="ppc-nb-price">' +
                    '<div class="ppc-nb-lbl">' + (AR?"السعر":"Price") + '</div>' +
                    '<div class="ppc-nb-val"><span class="ppc-nb-cur">' + cur + ' </span><span class="ppc-nb-num" id="ppcNavPrice">' + price + '</span></div>' +
                '</div>' +
                '<div class="ppc-nb-wawrap">' +
                    '<span class="ppc-nb-badge"><span class="ppc-nb-odot"><span class="ppc-nb-oring"></span><span class="ppc-nb-oinner"></span></span>' +
                    (AR?"متاح":"Online") + '</span>' +
                    '<a href="' + waUrl + '" class="ppc-nb-wa" target="_blank" rel="noopener">' +
                        waSvg + '<span>' + (AR?"تحدث":"Chat") + '</span>' +
                    '</a>' +
                    '<span class="ppc-nb-tip">' + (AR?"الشراء عن طريق الواتساب":"Buy via WhatsApp") + '</span>' +
                '</div>' +
                '<button class="ppc-nb-cart" id="ppcNavCart">' +
                    cartSvg + '<span>' + (AR?"للسلة":"Cart") + '</span>' +
                '</button>' +
                '<div class="ppc-nb-fo-wrap">' +
                    '<span class="ppc-nb-fo-badge">' + foBadge + '</span>' +
                    '<a href="' + foUrl + '" class="ppc-nb-fo" id="ppcNavFo">' +
                        ltSvg + '<span>' + foLabel + '</span>' +
                    '</a>' +
                '</div>' +
            '</div>';

        function inject(){
            var bar = document.querySelector(".tp-sticky-add-to-cart");
            if(!bar || bar.querySelector("#ppcNavbar")) return;
            Array.prototype.forEach.call(bar.children, function(c){ c.style.display="none"; });
            bar.appendChild(nav);
            bar.style.cssText = "display:block !important;padding:0 !important;border-radius:0 !important;border:none !important;bottom:0 !important;left:0 !important;right:0 !important;width:100% !important;z-index:9999 !important;";
        }
        inject();
        setTimeout(inject, 300);
        setTimeout(inject, 800);
        setTimeout(inject, 2000);
        // Run on first scroll
        window.addEventListener("scroll", inject, {passive:true, once:true});

        // Cart click
        document.addEventListener("click", function(e){
            if(e.target.closest("#ppcNavCart")){
                var atc = document.getElementById("add_to_cart");
                if(atc) atc.click();
            }
            // Fast Order click — find Zorder button and click it
            if(e.target.closest("#ppcNavFo")){
                e.preventDefault();
                var fo = document.querySelector('[class*="zorder"] a, [id*="zorder"] a, .tp-zorder-btn, [data-action*="zorder"]');
                if(fo) fo.click();
                else if(foUrl && foUrl !== "#") location.href = foUrl;
            }
        });

        // Update price + Fast Order URL on variant change
        if(window.$){
            $(document).on("get_combination_info", function(){
                setTimeout(function(){
                    var p = window.ppcPrice, el = document.getElementById("ppcNavPrice");
                    if(p && el) el.textContent = p.toFixed(3);
                    // Re-find Fast Order URL
                    var fo2 = document.querySelector('[class*="zorder"] a, [id*="zorder"] a, a[href*="zorder"]');
                    var navFo = document.getElementById("ppcNavFo");
                    if(fo2 && navFo) navFo.href = fo2.href;
                }, 200);
            });
        }
    }
    /* ── Bulk: rebuild after combination event ───────────── */
    if(window.$){
        $(document).on("get_combination_info", function(){
            setTimeout(function(){
                var container = document.querySelector(".tp-bulk-price-container");
                if(!container) return;
                var cells = container.querySelectorAll(".tp-bulk-price-block");
                if(!cells.length) return;
                // Remove old, rebuild fresh
                var old = document.getElementById("ppcBulkCustom");
                if(old) old.remove();
                buildBulk(container, cells);
            }, 200);
        });
    }

    /* ── Boot ─────────────────────────────────────────────── */
    if(document.readyState==="loading"){document.addEventListener("DOMContentLoaded",init);}
    else{init();}
    document.addEventListener("DOMContentLoaded",function(){
        setTimeout(function(){
            if (!document.getElementById("product_detail")) return;
            document.querySelectorAll("#product_details .o_wsale_product_price, #product_details .product_price").forEach(function(el){el.style.cssText="display:none !important";});
        },600);
        setTimeout(function(){
            try {
                var col=document.getElementById("ppcTabsCol");
                if(col&&col.children.length===0){
                    var tpTabs=document.querySelector(".tp-product-details-tab");
                    if(tpTabs && tpTabs.parentNode !== col) col.appendChild(tpTabs);
                }
            } catch(e) { console.warn("PPC retry tabs:", e); }
            var block=document.getElementById("ppcDescBlock");
            var descPane=document.getElementById("tp-product-description-tab");
            if(block&&descPane&&block.parentElement!==descPane){
                var inner=descPane.querySelector(".col-12,.container-fluid")||descPane;
                block.style.display="block";inner.appendChild(block);
                if(!block._db){bindDescBtns();block._db=true;}
            }
            activateReviewsTab();
        },800);
    });
})();
