/* اختيار المجتمع — زر ترشيح صغير في صفحة المنتج (أي زائر).
   يقرأ معرّف المنتج من data-main-object ويضيف زرًّا + نافذة صغيرة للاسم،
   ثم يرسل الترشيح إلى /uellow/community/nominate. يعمل على صفحات المنتج
   القياسية وصفحات يلو المخصّصة (سطح المكتب والجوال) لأن السمة قياسية. */
(function () {
  "use strict";

  // استخراج معرّف قالب المنتج من سمة Odoo القياسية
  function productTmplId() {
    var el = document.querySelector('[data-main-object^="product.template("]');
    if (!el) return 0;
    var m = (el.getAttribute("data-main-object") || "").match(/product\.template\((\d+)/);
    return m ? parseInt(m[1], 10) : 0;
  }

  // اختيار موضع مناسب لزرّ الترشيح قرب منطقة الشراء
  function anchorEl() {
    var sels = [
      'form[action*="/shop/cart/update"]',
      ".js_add_cart_json",
      "#product_details",
      ".o_wsale_product_information",
      "h1",
    ];
    for (var i = 0; i < sels.length; i++) {
      var e = document.querySelector(sels[i]);
      if (e) return e;
    }
    return null;
  }

  function h(tag, cls, html) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html != null) e.innerHTML = html;
    return e;
  }

  function build(tmplId) {
    var wrap = h("div", "uc-cpk");
    var btn = h("button", "uc-cpk-btn",
      '<span class="uc-cpk-ic">★</span> رشّح هذا المنتج');
    btn.type = "button";
    var pop = h("div", "uc-cpk-pop");
    pop.innerHTML =
      '<div class="uc-cpk-ttl">رشّح للمجتمع ✨</div>' +
      '<div class="uc-cpk-sub">اكتب اسمك ليظهر مع ترشيحك</div>' +
      '<div class="uc-cpk-row"><input class="uc-cpk-name" maxlength="24" ' +
      'placeholder="اسمك الأول" />' +
      '<button type="button" class="uc-cpk-send">رشّح</button></div>' +
      '<div class="uc-cpk-msg"></div>';
    wrap.appendChild(btn);
    wrap.appendChild(pop);

    var nameInp = pop.querySelector(".uc-cpk-name");
    var sendBtn = pop.querySelector(".uc-cpk-send");
    var msg = pop.querySelector(".uc-cpk-msg");

    btn.addEventListener("click", function () {
      wrap.classList.toggle("open");
      if (wrap.classList.contains("open")) {
        setTimeout(function () { nameInp.focus(); }, 30);
      }
    });

    function done(txt, ok) {
      msg.textContent = txt;
      msg.className = "uc-cpk-msg " + (ok ? "ok" : "err");
    }

    function markNominated(count) {
      btn.innerHTML = '<span class="uc-cpk-ic">✔</span> ' +
        'رشّحته — شكرًا!';
      btn.classList.add("done");
      btn.disabled = true;
      wrap.classList.remove("open");
    }

    function submit() {
      var name = (nameInp.value || "").trim();
      if (name.length < 2) { done("يرجى كتابة اسمك.", false); return; }
      sendBtn.disabled = true;
      var fd = new FormData();
      fd.append("product_id", tmplId);
      fd.append("name", name);
      fetch("/uellow/community/nominate", {
        method: "POST", body: fd, credentials: "same-origin",
      }).then(function (r) { return r.json(); }).then(function (d) {
        sendBtn.disabled = false;
        if (d && d.ok) {
          done("تمّ ترشيحك! يظهر الآن في «اختيار المجتمع».", true);
          setTimeout(function () { markNominated(d.count); }, 900);
        } else {
          done((d && d.error) || "تعذّر الترشيح.", false);
        }
      }).catch(function () {
        sendBtn.disabled = false;
        done("حدث خطأ، حاول لاحقًا.", false);
      });
    }

    sendBtn.addEventListener("click", submit);
    nameInp.addEventListener("keydown", function (e) {
      if (e.key === "Enter") { e.preventDefault(); submit(); }
    });

    // إن كان الجهاز قد رشّح المنتج من قبل، نعطّل الزر
    fetch("/uellow/community/state?product_id=" + tmplId, {
      credentials: "same-origin",
    }).then(function (r) { return r.json(); }).then(function (d) {
      if (d && d.nominated) markNominated();
    }).catch(function () {});

    return wrap;
  }

  function init() {
    if (document.querySelector(".uc-cpk")) return;
    var tmplId = productTmplId();
    if (!tmplId) return;
    var anchor = anchorEl();
    if (!anchor) return;
    var node = build(tmplId);
    anchor.parentNode.insertBefore(node, anchor.nextSibling);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
