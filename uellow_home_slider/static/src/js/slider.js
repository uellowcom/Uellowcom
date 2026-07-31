/** @odoo-module **/
import publicWidget from '@web/legacy/js/public/public_widget';

/* ---------- icon set (keys match ICON_SELECTION in models/slider.py) ---------- */
var ICONS = {
    phone:'<rect x="6" y="2.5" width="12" height="19" rx="2.5"/><line x1="10.5" y1="18.5" x2="13.5" y2="18.5"/>',
    mobile:'<rect x="6" y="2.5" width="12" height="19" rx="2.5"/><line x1="10.5" y1="18.5" x2="13.5" y2="18.5"/>',
    tablet:'<rect x="4" y="3" width="16" height="18" rx="2"/><line x1="10" y1="18" x2="14" y2="18"/>',
    bolt:'<polygon points="13,2 4,14 11,14 10,22 20,9 13,9"/>',
    laptop:'<rect x="4" y="5" width="16" height="10" rx="1.5"/><line x1="2" y1="19" x2="22" y2="19"/>',
    tv:'<rect x="3" y="5" width="18" height="12" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/>',
    watch:'<circle cx="12" cy="12" r="5.5"/><path d="M9 6.5 9.6 3h4.8L15 6.5M9 17.5 9.6 21h4.8L15 17.5"/><line x1="12" y1="12" x2="12" y2="9.5"/>',
    drop:'<path d="M12 3s6 6.5 6 11a6 6 0 0 1-12 0c0-4.5 6-11 6-11z"/>',
    home:'<path d="M4 11 12 4l8 7"/><path d="M6 10v9h12v-9"/>',
    baby:'<circle cx="12" cy="8" r="3.2"/><path d="M5 21c1.5-4 4-6 7-6s5.5 2 7 6"/>',
    heart:'<path d="M12 20s-7-4.7-7-10a4 4 0 0 1 7-2.5A4 4 0 0 1 19 10c0 5.3-7 10-7 10z"/>',
    shirt:'<path d="M8 3 4 6l2 3 2-1v10h8V8l2 1 2-3-4-3-3 2z"/>',
    gem:'<path d="M6 3h12l3 5-9 13L3 8z"/><path d="M3 8h18M9 3 6 8l6 13 6-13-3-5"/>',
    camera:'<rect x="3" y="7" width="18" height="13" rx="2"/><circle cx="12" cy="13.5" r="3.4"/><path d="M8 7l1.5-3h5L16 7"/>',
    headphones:'<path d="M4 13a8 8 0 0 1 16 0"/><rect x="3" y="13" width="4" height="7" rx="1.5"/><rect x="17" y="13" width="4" height="7" rx="1.5"/>',
    game:'<rect x="3" y="7" width="18" height="10" rx="4"/><line x1="8" y1="10" x2="8" y2="14"/><line x1="6" y1="12" x2="10" y2="12"/><circle cx="16" cy="11" r="1"/><circle cx="18" cy="13" r="1"/>',
    car:'<path d="M3 13l2-5h14l2 5v5h-3M6 18H3v-5"/><circle cx="7.5" cy="18" r="1.8"/><circle cx="16.5" cy="18" r="1.8"/>',
    dumbbell:'<path d="M6 9v6M4 10v4M18 9v6M20 10v4M6 12h12"/>',
    tools:'<path d="M14 7a3.5 3.5 0 0 1-4.6 4.6L4 17v3h3l5.4-5.4A3.5 3.5 0 0 1 17 10l-3-3z"/>',
    shield:'<path d="M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6z"/>',
    tag:'<path d="M3 12l8-8 9 1 1 9-8 8z"/><circle cx="15.5" cy="8.5" r="1.4"/>',
    gift:'<rect x="3" y="8" width="18" height="4" rx="1"/><path d="M5 12v9h14v-9M12 8v13"/><path d="M12 8S9 3 7 4.5 9 8 12 8zM12 8s3-5 5-3.5S15 8 12 8z"/>',
    star:'<polygon points="12,3 14.6,9 21,9.6 16,14 17.6,21 12,17.5 6.4,21 8,14 3,9.6 9.4,9"/>',
    truck:'<rect x="1.5" y="6" width="12" height="9" rx="1"/><path d="M13.5 9h4l3 3v3h-7z"/><circle cx="6" cy="17.5" r="1.6"/><circle cx="17" cy="17.5" r="1.6"/>',
    cash:'<rect x="2" y="6" width="20" height="12" rx="2"/><circle cx="12" cy="12" r="2.4"/><path d="M5 9v6M19 9v6"/>',
    lock:'<rect x="5" y="10.5" width="14" height="9.5" rx="2"/><path d="M8 10.5V7.5a4 4 0 0 1 8 0v3"/>',
    percent:'<line x1="6" y1="18" x2="18" y2="6"/><circle cx="7.5" cy="7.5" r="2"/><circle cx="16.5" cy="16.5" r="2"/>'
};
function svg(key){
    var p = ICONS[key] || ICONS.tag;
    return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">'+p+'</svg>';
}
function esc(s){ return String(s==null?'':s).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];}); }

/* ---------- MOBILE slider (unchanged behaviour) ---------- */
function runSlider(cfg) {
    var wrap=cfg.wrap,imgEl=cfg.img,prevBtn=cfg.prev,nextBtn=cfg.next,dotsEl=cfg.dots,overlay=cfg.overlay||null,slides=cfg.slides||[];
    if(!wrap||!imgEl||!prevBtn||!nextBtn||!dotsEl||!slides.length)return;
    imgEl.setAttribute('loading','eager');
    imgEl.setAttribute('fetchpriority','high');
    imgEl.setAttribute('decoding','async');
    var idx=0,timer,dots=[];
    dotsEl.innerHTML='';
    slides.forEach(function(_,i){var d=document.createElement('div');d.className='uhs-dot'+(i===0?' on':'');d.addEventListener('click',function(){goTo(i);});dotsEl.appendChild(d);dots.push(d);});
    imgEl.style.cursor='pointer';
    imgEl.addEventListener('click',function(){var s=slides[idx];if(s&&s.href){if(s.target==='_blank'){window.open(s.href,'_blank');}else{window.location.href=s.href;}}});
    function showOverlay(slide){if(!overlay)return;var t=overlay.querySelector('.uhs-overlay-title'),s=overlay.querySelector('.uhs-overlay-sub'),b=overlay.querySelector('.uhs-overlay-btn');if(slide.overlay&&slide.title){if(t)t.textContent=slide.title;if(s)s.textContent=slide.sub||'';if(b){b.textContent=slide.btn||'';b.href=slide.btn_url||slide.href||'/shop';b.style.display=slide.btn?'inline-block':'none';}overlay.style.display='block';}else{overlay.style.display='none';}}
    function goTo(n){idx=(n+slides.length)%slides.length;imgEl.classList.add('uhs-fade');setTimeout(function(){var s=slides[idx];if(s&&s.src)imgEl.src=s.src;if(s&&s.alt)imgEl.alt=s.alt;imgEl.classList.remove('uhs-fade');showOverlay(s||{});},200);dots.forEach(function(d,i){d.classList.toggle('on',i===idx);});}
    function startTimer(){timer=setInterval(function(){goTo(idx+1);},4500);}
    function stopTimer(){clearInterval(timer);}
    prevBtn.addEventListener('click',function(e){e.stopPropagation();goTo(idx+1);});
    nextBtn.addEventListener('click',function(e){e.stopPropagation();goTo(idx-1);});
    wrap.addEventListener('mouseenter',stopTimer);
    wrap.addEventListener('mouseleave',startTimer);
    if(slides[0]){imgEl.src=slides[0].src||imgEl.src;showOverlay(slides[0]);}
    startTimer();
}

/* ---------- DESKTOP v2 spotlight slider ---------- */
function runSpot(cfg){
    var wrap=cfg.wrap,imgEl=cfg.img,prevBtn=cfg.prev,nextBtn=cfg.next,dotsEl=cfg.dots,pbar=cfg.pbar;
    var slides=cfg.slides||[],speed=(cfg.speed||5)*1000,autoplay=cfg.autoplay!==false;
    var kickerEl=cfg.kicker,titleEl=cfg.title,subEl=cfg.sub,ctaEl=cfg.cta,ctaLabel=cfg.ctaLabel||'Shop';
    var showText=cfg.showText!==false;
    if(!wrap||!imgEl||!slides.length)return;
    imgEl.setAttribute('loading','eager');imgEl.setAttribute('fetchpriority','high');imgEl.setAttribute('decoding','async');
    var idx=0,timer,dots=[];
    if(dotsEl){
        dotsEl.innerHTML='';
        if(cfg.showDots!==false){
            slides.forEach(function(_,i){var d=document.createElement('div');d.className='uhs-dot'+(i===0?' on':'');d.addEventListener('click',function(){goTo(i);});dotsEl.appendChild(d);dots.push(d);});
        } else { dotsEl.style.display='none'; }
    }
    imgEl.style.cursor='pointer';
    imgEl.addEventListener('click',function(){var s=slides[idx];if(s&&s.href){if(s.target==='_blank'){window.open(s.href,'_blank');}else{window.location.href=s.href;}}});
    function setText(el,val){ if(!el)return; if(showText&&val){el.textContent=val;el.style.display='';}else{el.style.display='none';} }
    function paint(s){
        s=s||{};
        setText(kickerEl, s.kicker);
        setText(titleEl, (s.overlay&&s.title)?s.title:'');
        setText(subEl, (s.overlay&&s.sub)?s.sub:'');
        if(ctaEl){ ctaEl.textContent=((s.overlay&&s.btn)?s.btn:ctaLabel)+' →'; ctaEl.href=(s.overlay&&s.btn_url)?s.btn_url:(s.href||'/shop'); }
    }
    function resetBar(){ if(!pbar)return; pbar.style.transition='none'; pbar.style.width='0%'; void pbar.offsetWidth;
        if(autoplay){ pbar.style.transition='width '+speed+'ms linear'; pbar.style.width='100%'; } }
    function goTo(n){idx=(n+slides.length)%slides.length;imgEl.classList.add('uhs-fade');
        setTimeout(function(){var s=slides[idx];if(s&&s.src)imgEl.src=s.src;if(s&&s.alt)imgEl.alt=s.alt;imgEl.classList.remove('uhs-fade');paint(s);},200);
        dots.forEach(function(d,i){d.classList.toggle('on',i===idx);});resetBar();}
    function startTimer(){if(!autoplay)return;timer=setInterval(function(){goTo(idx+1);},speed);resetBar();}
    function stopTimer(){clearInterval(timer);if(pbar){pbar.style.transition='none';}}
    if(prevBtn)prevBtn.addEventListener('click',function(e){e.stopPropagation();goTo(idx-1);});
    if(nextBtn)nextBtn.addEventListener('click',function(e){e.stopPropagation();goTo(idx+1);});
    wrap.addEventListener('mouseenter',stopTimer);
    wrap.addEventListener('mouseleave',startTimer);
    if(slides[0]){imgEl.src=slides[0].src||imgEl.src;paint(slides[0]);}
    startTimer();
}

function runCopyBtn(btn,codeEl,lang){
    if(!btn||!codeEl)return;
    var COPY=lang==='en'?'Copy':'نسخ',COPIED=lang==='en'?'Done ✓':'تم ✓';
    btn.textContent=COPY;
    function onOk(){btn.textContent=COPIED;btn.classList.add('done');setTimeout(function(){btn.textContent=COPY;btn.classList.remove('done');},2000);}
    function onFail(){alert((lang==='en'?'Coupon: ':'كود الخصم: ')+(btn.dataset.code||codeEl.textContent||'').trim());}
    function fallback(text){try{var ta=document.createElement('textarea');ta.value=text;ta.setAttribute('readonly','');ta.style.cssText='position:fixed;top:0;left:0;width:1px;height:1px;opacity:0;pointer-events:none';document.body.appendChild(ta);ta.focus();ta.select();ta.setSelectionRange(0,text.length);var ok=document.execCommand('copy');document.body.removeChild(ta);ok?onOk():onFail();}catch(e){onFail();}}
    btn.onclick=function(e){e.preventDefault();e.stopPropagation();var code=(btn.dataset.code||codeEl.textContent||'').trim();if(!code)return false;if(navigator.clipboard&&window.isSecureContext){navigator.clipboard.writeText(code).then(onOk).catch(function(){fallback(code);});}else{fallback(code);}return false;};
}

function buildDept(section,data){
    var aside=section.querySelector('#uhs_dept'),list=section.querySelector('#uhs_dept_list');
    if(!aside||!list)return;
    if(data.show_menu===false||!(data.menu&&data.menu.length)){aside.style.display='none';return;}
    aside.style.display='';
    var chev=data.lang==='ar'?'‹':'›';
    list.innerHTML=data.menu.map(function(m){
        return '<li><a href="'+esc(m.url||'/shop')+'"><span class="uhs-dept-ic">'+svg(m.icon)+
               '</span><span class="uhs-dept-lbl">'+esc(m.label)+'</span><span class="uhs-dept-ch">'+chev+'</span></a></li>';
    }).join('');
    var title=section.querySelector('#uhs_dept_title');if(title&&data.menu_title)title.textContent=data.menu_title;
    var ft=section.querySelector('#uhs_dept_footer_t');if(ft&&data.menu_footer)ft.textContent=data.menu_footer;
    var fa=section.querySelector('#uhs_dept_footer');if(fa&&data.menu_footer_url)fa.href=data.menu_footer_url;
    var cnt=section.querySelector('#uhs_dept_count');if(cnt)cnt.textContent=(data.menu_total||data.menu.length)+' '+chev;
}

function buildFeats(section,data){
    var el=section.querySelector('#uhs_feats');if(!el)return;
    if(data.show_features===false||!(data.features&&data.features.length)){el.style.display='none';return;}
    el.style.display='';
    el.innerHTML=data.features.map(function(f){
        return '<span class="uhs-feat"><span class="uhs-feat-ic">'+svg(f.icon)+'</span>'+esc(f.label)+'</span>';
    }).join('');
}

function applyData(section,data){
    var lang=data.lang||'ar';
    var v2=section.querySelector('.uhs-v2');if(v2)v2.setAttribute('dir',lang==='ar'?'rtl':'ltr');

    buildDept(section,data);
    buildFeats(section,data);
    var _scrim=section.querySelector('.uhs-spot-scrim');
    if(_scrim){ var _ov=(data.overlay_opacity==null?100:data.overlay_opacity); _scrim.style.opacity=Math.max(0,Math.min(100,_ov))/100; }

    // coupon (v2 markup)
    var T={ar:{voucher:'كوبون',shop:'تسوّق الآن'},en:{voucher:'Coupon',shop:'Shop now'}};
    var t=T[lang]||T.ar;
    var labelEl=section.querySelector('#uhs_voucher_label');
    var copyBtn=section.querySelector('#uhs_copy_btn'),codeEl=section.querySelector('#uhs_coupon_code');
    var discEl=section.querySelector('#uhs_discount'),ticketWrap=section.querySelector('#uhs_ticket_wrap');
    if(labelEl)labelEl.textContent=t.voucher;
    if(data.show_coupon===false&&ticketWrap)ticketWrap.style.display='none';
    else if(ticketWrap)ticketWrap.style.display='';
    if(codeEl&&data.coupon_code){codeEl.textContent=data.coupon_code;if(copyBtn)copyBtn.dataset.code=data.coupon_code;}
    if(discEl&&data.coupon_discount)discEl.textContent=data.coupon_discount;

    // arrows visibility
    var ctrls=section.querySelector('#uhs_d_controls');
    if(ctrls)ctrls.style.display=(data.show_arrows===false)?'none':'';

    // desktop spotlight
    runSpot({
        wrap:section.querySelector('#uhs_desktop_wrap'),img:section.querySelector('#uhs_desktop_img'),
        prev:section.querySelector('#uhs_d_prev'),next:section.querySelector('#uhs_d_next'),
        dots:section.querySelector('#uhs_d_dots'),pbar:section.querySelector('#uhs_d_pbar'),
        kicker:section.querySelector('#uhs_d_kicker'),title:section.querySelector('#uhs_d_title'),
        sub:section.querySelector('#uhs_d_sub'),cta:section.querySelector('#uhs_d_btn'),
        slides:data.desktop||[],ctaLabel:data.cta_label||t.shop,
        autoplay:data.autoplay,speed:data.autoplay_speed,
        showDots:data.show_dots,showText:data.show_overlay_text
    });

    // mobile (unchanged)
    runSlider({
        wrap:section.querySelector('#uhs_mobile_wrap'),img:section.querySelector('#uhs_mobile_img'),
        prev:section.querySelector('#uhs_m_prev'),next:section.querySelector('#uhs_m_next'),
        dots:section.querySelector('#uhs_m_dots'),overlay:section.querySelector('#uhs_m_overlay'),
        slides:data.mobile||data.desktop||[]
    });

    runCopyBtn(copyBtn,codeEl,lang);
}

/* ---------- v2 DOM skeleton (rebuilt at runtime so stale page copies upgrade) ---------- */
var SKELETON = '\
<div class="uhs-desktop uhs-v2 d-none d-lg-flex">\
  <aside class="uhs-dept" id="uhs_dept">\
    <div class="uhs-dept-h"><span class="uhs-dept-bars"><i></i><i></i><i></i></span> <span id="uhs_dept_title">All Departments</span></div>\
    <ul class="uhs-dept-list" id="uhs_dept_list"></ul>\
    <a class="uhs-dept-f" id="uhs_dept_footer" href="/shop"><span id="uhs_dept_footer_t">All departments</span><span class="uhs-dept-count" id="uhs_dept_count"></span></a>\
  </aside>\
  <div class="uhs-spot" id="uhs_desktop_wrap">\
    <img class="uhs-slide-img" id="uhs_desktop_img" src="/uellow_home_slider/static/src/img/placeholder_wide.svg" alt="slide"/>\
    <div class="uhs-spot-scrim"></div>\
    <div class="uhs-spot-in" id="uhs_d_overlay">\
      <span class="uhs-chip" id="uhs_d_kicker" style="display:none;"></span>\
      <h2 class="uhs-spot-title" id="uhs_d_title" style="display:none;"></h2>\
      <p class="uhs-spot-sub" id="uhs_d_sub" style="display:none;"></p>\
      <div class="uhs-spot-cta-row">\
        <a class="uhs-cta" id="uhs_d_btn" href="/shop">Shop now</a>\
        <div class="uhs-cpn" id="uhs_ticket_wrap">\
          <span class="uhs-cpn-label" id="uhs_voucher_label">Coupon</span>\
          <span class="uhs-cpn-code" id="uhs_coupon_code">WELCOME05</span>\
          <span class="uhs-cpn-off"><span id="uhs_discount">5%</span></span>\
          <button type="button" class="uhs-cpn-copy" id="uhs_copy_btn" data-code="WELCOME05">Copy</button>\
        </div>\
      </div>\
      <div class="uhs-feats" id="uhs_feats"></div>\
    </div>\
    <div class="uhs-nav-group" id="uhs_d_controls">\
      <button type="button" class="uhs-nav" id="uhs_d_prev" aria-label="Previous">‹</button>\
      <button type="button" class="uhs-nav" id="uhs_d_next" aria-label="Next">›</button>\
    </div>\
    <div class="uhs-dots uhs-dots-left" id="uhs_d_dots"></div>\
    <div class="uhs-pbar" id="uhs_d_pbar"></div>\
  </div>\
</div>\
<div class="uhs-mobile d-lg-none" id="uhs_mobile_wrap">\
  <img class="uhs-slide-img" id="uhs_mobile_img" src="/uellow_home_slider/static/src/img/placeholder_wide.svg" alt="slide"/>\
  <button type="button" class="uhs-arrow uhs-right" id="uhs_m_prev">›</button>\
  <button type="button" class="uhs-arrow uhs-left" id="uhs_m_next">‹</button>\
  <div class="uhs-dots" id="uhs_m_dots"></div>\
  <div class="uhs-overlay" id="uhs_m_overlay" style="display:none;">\
    <h2 class="uhs-overlay-title" id="uhs_m_title"></h2>\
    <p class="uhs-overlay-sub" id="uhs_m_sub"></p>\
    <a class="uhs-overlay-btn" id="uhs_m_btn" href="/shop"></a>\
  </div>\
</div>';

function ensureDom(section){
    // If the section still holds an old (pre-v2) copy saved inside the page,
    // replace it with the current skeleton so template upgrades always apply.
    if(section.querySelector('.uhs-dept'))return;
    var host=section.querySelector('.uellow-hero-section')||section;
    host.innerHTML=SKELETON;
}

var FALLBACK={lang:'ar',show_coupon:true,coupon_code:'WELCOME05',coupon_discount:'5%',
    show_menu:true,show_features:true,show_overlay_text:true,show_arrows:true,show_dots:true,autoplay:true,autoplay_speed:5,
    menu_title:'كل الأقسام',menu_footer:'كل الأقسام',menu_footer_url:'/shop',menu_total:23,cta_label:'تسوّق الآن',
    menu:[{label:'الجوّالات واللوحيات',icon:'phone',url:'/shop'},{label:'إلكترونيات',icon:'bolt',url:'/shop'},{label:'كمبيوتر ولابتوب',icon:'laptop',url:'/shop'},{label:'ساعات',icon:'watch',url:'/shop'},{label:'عطور',icon:'drop',url:'/shop'},{label:'المنزل',icon:'home',url:'/shop'},{label:'الأم والطفل',icon:'baby',url:'/shop'},{label:'العناية الصحية',icon:'heart',url:'/shop'},{label:'أزياء رجالية',icon:'shirt',url:'/shop'}],
    features:[{label:'توصيل مجاني',icon:'truck'},{label:'الدفع عند الاستلام',icon:'cash'},{label:'دفع آمن',icon:'lock'}],
    desktop:[{src:'https://uellow.com/web/image/product.image/9979/image_1024/slider1.webp',href:'/shop',overlay:false}],
    mobile:[{src:'https://uellow.com/web/image/product.image/9979/image_1024/slider1.webp',href:'/shop',overlay:false}]};

publicWidget.registry.UellowHomeSlider = publicWidget.Widget.extend({
    selector: '.s_uellow_home_slider',
    start: function(){
        var section=this.el;
        // If this element wraps another slider section, let the inner one render.
        if(section.querySelector('.s_uellow_home_slider')){return this._super.apply(this,arguments);}
        ensureDom(section);
        fetch('/uellow/slider/data',{credentials:'same-origin'})
            .then(function(r){if(!r.ok)throw new Error('HTTP '+r.status);return r.json();})
            .then(function(data){applyData(section,data&&data.desktop?data:FALLBACK);})
            .catch(function(err){console.warn('[UellowHomeSlider] fallback:',err);applyData(section,FALLBACK);});
        return this._super.apply(this,arguments);
    },
});

export default publicWidget.registry.UellowHomeSlider;
