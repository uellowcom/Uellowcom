/** @odoo-module **/
import publicWidget from '@web/legacy/js/public/public_widget';

function runSlider(cfg) {
    var wrap=cfg.wrap,imgEl=cfg.img,prevBtn=cfg.prev,nextBtn=cfg.next,dotsEl=cfg.dots,overlay=cfg.overlay||null,slides=cfg.slides||[];
    if(!wrap||!imgEl||!prevBtn||!nextBtn||!dotsEl||!slides.length)return;
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

function runCopyBtn(btn,codeEl,lang){
    if(!btn||!codeEl)return;
    var COPY=lang==='en'?'Copy':'نسخ',COPIED=lang==='en'?'Done \u2713':'تم \u2713';
    btn.textContent=COPY;
    function onOk(){btn.textContent=COPIED;btn.classList.add('done');setTimeout(function(){btn.textContent=COPY;btn.classList.remove('done');},2000);}
    function onFail(){alert((lang==='en'?'Coupon: ':'كود الخصم: ')+(btn.dataset.code||codeEl.textContent||'').trim());}
    function fallback(text){try{var ta=document.createElement('textarea');ta.value=text;ta.setAttribute('readonly','');ta.style.cssText='position:fixed;top:0;left:0;width:1px;height:1px;opacity:0;pointer-events:none';document.body.appendChild(ta);ta.focus();ta.select();ta.setSelectionRange(0,text.length);var ok=document.execCommand('copy');document.body.removeChild(ta);ok?onOk():onFail();}catch(e){onFail();}}
    btn.onclick=function(e){e.preventDefault();e.stopPropagation();var code=(btn.dataset.code||codeEl.textContent||'').trim();if(!code)return false;if(navigator.clipboard&&window.isSecureContext){navigator.clipboard.writeText(code).then(onOk).catch(function(){fallback(code);});}else{fallback(code);}return false;};
}

function applyData(section,data){
    var lang=data.lang||'ar';
    var logo=section.querySelector('#uhs_logo');
    if(logo&&data.logo)logo.src=data.logo;
    if(data.banners){
        var b1i=section.querySelector('#uhs_b1_img'),b1l=section.querySelector('#uhs_b1_link');
        var b2i=section.querySelector('#uhs_b2_img'),b2l=section.querySelector('#uhs_b2_link');
        if(b1i&&data.banners.b1){b1i.src=data.banners.b1.src;b1i.alt=data.banners.b1.alt||'';}
        if(b1l&&data.banners.b1)b1l.href=data.banners.b1.href;
        if(b2i&&data.banners.b2){b2i.src=data.banners.b2.src;b2i.alt=data.banners.b2.alt||'';}
        if(b2l&&data.banners.b2)b2l.href=data.banners.b2.href;
    }
    var T={ar:{welcome:'مرحباً بك في يلو! 💛',voucher:'كود الخصم',join:'انضم إلينا الآن',login:'لديك حساب؟ سجل دخول'},en:{welcome:'Welcome to Uellow! 💛',voucher:'WELCOME VOUCHER',join:'Join Us Now',login:'Have an account? Sign in'}};
    var t=T[lang]||T.ar;
    var welcomeEl=section.querySelector('#uhs_welcome'),labelEl=section.querySelector('#uhs_voucher_label');
    var joinEl=section.querySelector('#uhs_signup_btn'),loginEl=section.querySelector('#uhs_login_btn');
    var copyBtn=section.querySelector('#uhs_copy_btn'),codeEl=section.querySelector('#uhs_coupon_code');
    var discEl=section.querySelector('#uhs_discount'),ticketWrap=section.querySelector('#uhs_ticket_wrap');
    if(welcomeEl)welcomeEl.textContent=t.welcome;
    if(labelEl)labelEl.textContent=t.voucher;
    if(joinEl){joinEl.textContent=t.join;if(data.signup_url)joinEl.href=data.signup_url;}
    if(loginEl){loginEl.textContent=t.login;if(data.login_url)loginEl.href=data.login_url;}
    if(data.show_coupon===false&&ticketWrap)ticketWrap.style.display='none';
    if(codeEl&&data.coupon_code){codeEl.textContent=data.coupon_code;if(copyBtn)copyBtn.dataset.code=data.coupon_code;}
    if(discEl&&data.coupon_discount)discEl.textContent=data.coupon_discount;
    runSlider({wrap:section.querySelector('#uhs_desktop_wrap'),img:section.querySelector('#uhs_desktop_img'),prev:section.querySelector('#uhs_d_prev'),next:section.querySelector('#uhs_d_next'),dots:section.querySelector('#uhs_d_dots'),overlay:section.querySelector('#uhs_d_overlay'),slides:data.desktop||[]});
    runSlider({wrap:section.querySelector('#uhs_mobile_wrap'),img:section.querySelector('#uhs_mobile_img'),prev:section.querySelector('#uhs_m_prev'),next:section.querySelector('#uhs_m_next'),dots:section.querySelector('#uhs_m_dots'),overlay:section.querySelector('#uhs_m_overlay'),slides:data.mobile||data.desktop||[]});
    runCopyBtn(copyBtn,codeEl,lang);
}

var FALLBACK={lang:'ar',logo:'/web/image/website/1/logo/Uellow?unique=13b1cfb',show_coupon:true,coupon_code:'WELCOME05',coupon_discount:'5%',signup_url:'/web/signup',login_url:'/web/login',banners:{b1:{src:'https://www.uellow.com/web/image/134895',href:'/shop',alt:'Banner 1'},b2:{src:'https://www.uellow.com/web/image/134896',href:'/shop',alt:'Banner 2'}},desktop:[{src:'https://uellow.com/web/image/product.image/9979/image_1024/slider1.webp',href:'/shop',overlay:false}],mobile:[{src:'https://uellow.com/web/image/product.image/9979/image_1024/slider1.webp',href:'/shop',overlay:false}]};

publicWidget.registry.UellowHomeSlider = publicWidget.Widget.extend({
    selector: '.s_uellow_home_slider',
    start: function(){
        var section=this.el;
        fetch('/uellow/slider/data',{credentials:'same-origin'})
            .then(function(r){if(!r.ok)throw new Error('HTTP '+r.status);return r.json();})
            .then(function(data){applyData(section,data);})
            .catch(function(err){console.warn('[UellowHomeSlider] fallback:',err);applyData(section,FALLBACK);});
        return this._super.apply(this,arguments);
    },
});

export default publicWidget.registry.UellowHomeSlider;
