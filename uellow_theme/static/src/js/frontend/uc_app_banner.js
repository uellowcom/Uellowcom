/* Uellow — persistent "Get the app" banner, shown on every frontend page (mobile). */
(function () {
  "use strict";
  try {
    var ua = navigator.userAgent || "";
    var isIOS = /iPhone|iPad|iPod/i.test(ua);
    var isAnd = /Android/i.test(ua);
    if (!isIOS && !isAnd) return;                 // mobile app banner → phones only
    if (window.__ucAppBanner) return;             // once per page
    window.__ucAppBanner = 1;

    var IOS = "https://apps.apple.com/app/id6769010765";
    var AND = "https://play.google.com/store/apps/details?id=com.uellow.app";
    var store = isIOS ? IOS : AND;

    var htmlEl = document.documentElement;
    var ar = ((htmlEl.getAttribute("lang") || "").toLowerCase().indexOf("ar") === 0) ||
             (htmlEl.getAttribute("dir") === "rtl") ||
             /[؀-ۿ]/.test(document.title || "");

    var css =
      ".uc-appbar{position:fixed;left:8px;right:8px;z-index:90;display:flex;align-items:center;gap:11px;" +
      "background:#fff;border:1px solid #ececec;border-radius:16px;padding:9px 11px;" +
      "box-shadow:0 6px 22px rgba(0,0,0,.16);font-family:'Tajawal','SF Arabic',system-ui,-apple-system,'Segoe UI',sans-serif;" +
      "transform:translateY(140%);transition:transform .35s cubic-bezier(.2,.8,.2,1)}" +
      ".uc-appbar.in{transform:translateY(0)}" +
      ".uc-appbar-ic{width:44px;height:44px;border-radius:12px;object-fit:cover;flex:0 0 auto;background:#F5C320}" +
      ".uc-appbar-tx{flex:1;min-width:0;line-height:1.25}" +
      ".uc-appbar-tx strong{display:block;font-size:13.5px;font-weight:900;color:#2a2118}" +
      ".uc-appbar-tx span{display:block;font-size:11px;color:#8A7A66;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}" +
      ".uc-appbar-cta{flex:0 0 auto;background:#F5C320;color:#3a2711;font-size:13px;font-weight:900;" +
      "text-decoration:none;padding:9px 17px;border-radius:22px;white-space:nowrap}" +
      ".uc-appbar-cta:active{filter:brightness(.95)}" +
      ".uc-appbar-x{flex:0 0 auto;width:26px;height:26px;border:0;background:#F2F3F5;color:#9aa0a6;" +
      "border-radius:50%;font-size:13px;line-height:1;cursor:pointer;padding:0}" +
      "@media(min-width:820px){.uc-appbar{display:none}}";
    var st = document.createElement("style");
    st.textContent = css;
    document.head.appendChild(st);

    var logo = "/web/image/website/1/logo";
    var bar = document.createElement("div");
    bar.className = "uc-appbar";
    bar.setAttribute("role", "complementary");
    bar.innerHTML =
      '<img class="uc-appbar-ic" src="' + logo + '" alt="Uellow" ' +
      'onerror="this.style.visibility=\'hidden\'">' +
      '<div class="uc-appbar-tx"><strong>' +
      (ar ? "تطبيق يلو" : "Uellow App") + "</strong><span>" +
      (ar ? "تسوّق أسرع وعروض حصرية داخل التطبيق" : "Faster shopping & exclusive in-app deals") +
      "</span></div>" +
      '<a class="uc-appbar-cta" href="' + store + '" target="_blank" rel="noopener">' +
      (ar ? "تحميل" : "Get") + "</a>" +
      '<button class="uc-appbar-x" aria-label="' + (ar ? "إغلاق" : "Close") + '">✕</button>';
    document.body.appendChild(bar);

    var spacer = document.createElement("div");
    spacer.setAttribute("aria-hidden", "true");
    document.body.appendChild(spacer);

    function place() {
      var bn = document.querySelector(".botnav");
      var bnH = bn ? bn.offsetHeight : 0;
      var safe = 0;
      try { safe = parseInt(getComputedStyle(htmlEl).getPropertyValue("--sab")) || 0; } catch (e) {}
      bar.style.bottom = (bnH + 8) + "px";
      spacer.style.height = (bar.offsetHeight + bnH + 16) + "px";
    }
    place();
    requestAnimationFrame(function () { bar.classList.add("in"); place(); });
    setTimeout(place, 600);
    window.addEventListener("resize", place);

    bar.querySelector(".uc-appbar-x").addEventListener("click", function () {
      bar.classList.remove("in");
      setTimeout(function () { bar.remove(); spacer.remove(); }, 320);
      // no storage → banner returns on the next page (persistent across pages)
    });
  } catch (e) { /* never break the page */ }
})();
