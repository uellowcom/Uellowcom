(function(){
    if(window.__fbReady) return;
    window.__fbReady = true;

    var isAr = (document.documentElement.lang||'').toLowerCase().startsWith('ar') || document.documentElement.dir==='rtl';
    var LR   = isAr ? 'left' : 'right';
    var DIR  = isAr ? 'rtl'  : 'ltr';

    /* ── CSS ── */
    if(!document.getElementById('qc-st')){
        var st=document.createElement('style'); st.id='qc-st';
        st.textContent=[
            '.qc-overlay{position:fixed;inset:0;z-index:99999;background:rgba(0,0,0,.55);display:flex;align-items:center;justify-content:center;opacity:0;transition:opacity .25s;pointer-events:none;}',
            '.qc-overlay.qc-show{opacity:1;pointer-events:all;}',
            '.qc-dialog{background:#fff;border-radius:20px;width:calc(100% - 24px);max-width:460px;max-height:92vh;display:flex;flex-direction:column;direction:'+DIR+';box-shadow:0 28px 70px rgba(0,0,0,.3);transform:translateY(36px) scale(.95);transition:transform .3s cubic-bezier(.34,1.56,.64,1);}',
            '.qc-overlay.qc-show .qc-dialog{transform:translateY(0) scale(1);}',
            '.qc-head{background:linear-gradient(135deg,#fdd835,#ffb300,#ff8f00);border-radius:20px 20px 0 0;padding:18px 22px 14px;position:relative;flex-shrink:0;}',
            '.qc-head h2{margin:0;font-size:18px;font-weight:800;color:#3e2000;}',
            '.qc-head p{margin:3px 0 0;font-size:12px;color:rgba(62,32,0,.6);}',
            '.qc-badge{display:inline-flex;align-items:center;gap:6px;margin-top:9px;background:rgba(255,255,255,.35);border:1px solid rgba(255,255,255,.5);border-radius:8px;padding:4px 10px;font-size:12px;font-weight:700;color:#3e2000;max-width:calc(100% - 44px);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}',
            '.qc-x{position:absolute;top:13px;'+LR+':14px;background:rgba(62,32,0,.12);border:none;width:30px;height:30px;border-radius:50%;font-size:16px;color:#3e2000;cursor:pointer;display:flex;align-items:center;justify-content:center;}',
            '.qc-x:hover{background:rgba(62,32,0,.22);}',
            '.qc-body{padding:18px 22px 0;overflow-y:auto;flex:1;}',
            '.qc-footer{padding:14px 22px 18px;flex-shrink:0;background:#fff;border-top:1px solid #f0f0f0;border-radius:0 0 20px 20px;position:sticky;bottom:0;}',
            '.qc-lbl{display:block;font-size:11px;font-weight:700;color:#f07b20;text-transform:uppercase;letter-spacing:.7px;margin-bottom:5px;}',
            '.qc-inp{width:100%;box-sizing:border-box;border:1.5px solid #ffe0a0;border-radius:10px;padding:10px 13px;font-size:15px;color:#222;background:#fffdf5;outline:none;margin-bottom:14px;font-family:inherit;direction:'+DIR+';transition:border .2s,box-shadow .2s;}',
            '.qc-inp:focus{border-color:#ff6b35;box-shadow:0 0 0 3px rgba(255,107,53,.15);background:#fff;}',
            'textarea.qc-inp{resize:vertical;min-height:60px;line-height:1.5;}',
            '.qc-inp.qf{border-color:#f7b731;background:#fffdf0;}',
            '.qc-mw{border:1.5px solid #ffe0a0;border-radius:12px;overflow:hidden;margin-bottom:6px;position:relative;}',
            '.qc-map{height:175px;width:100%;}',
            '.qc-loc{position:absolute;top:8px;'+LR+':8px;z-index:500;background:#fff;border:1px solid #f7b731;border-radius:8px;padding:5px 10px;font-size:12px;font-weight:600;color:#d4500a;cursor:pointer;}',
            '.qc-loc:hover{background:#f7b731;color:#1a1a1a;}',
            '.qc-hint{font-size:11px;padding:0 2px;margin-bottom:12px;line-height:1.4;}',
            '.qc-pl{display:flex;flex-direction:column;gap:8px;padding-bottom:4px;}',
            '.qc-po{display:flex;align-items:center;gap:12px;border:2px solid #ffe0a0;border-radius:12px;padding:12px 14px;cursor:pointer;transition:all .18s;background:#fffdf5;}',
            '.qc-po:hover,.qc-po.sel{border-color:#ff6b35;background:#fff5e0;box-shadow:0 0 0 3px rgba(255,107,53,.15);}',
            '.qc-pi{width:38px;height:38px;border-radius:8px;background:#ffe9c0;display:flex;align-items:center;justify-content:center;font-size:22px;flex-shrink:0;overflow:hidden;}',
            '.qc-pi img{width:100%;height:100%;object-fit:contain;}',
            '.qc-pn{font-size:14px;font-weight:600;color:#222;flex:1;}',
            '.qc-pc{width:22px;height:22px;border:2px solid #f7b731;border-radius:50%;display:flex;align-items:center;justify-content:center;flex-shrink:0;font-size:12px;font-weight:700;}',
            '.qc-po.sel .qc-pc{background:#ff6b35;border-color:#ff6b35;color:#fff;}',
            '.qc-btn{width:100%;padding:13px;border:none;border-radius:12px;background:linear-gradient(135deg,#fdd835,#ffb300);color:#3e2000;font-size:15px;font-weight:800;cursor:pointer;box-shadow:0 4px 14px rgba(253,216,53,.5);display:flex;align-items:center;justify-content:center;gap:8px;transition:all .18s;font-family:inherit;}',
            '.qc-btn:hover:not(:disabled){transform:translateY(-1px);}',
            '.qc-btn:disabled{opacity:.5;cursor:not-allowed;transform:none;}',
            '.qc-bs{width:100%;padding:10px;border:1.5px solid #fdd835;border-radius:12px;background:#fff;color:#b35c00;font-size:14px;font-weight:600;cursor:pointer;margin-top:9px;font-family:inherit;}',
            '.qc-bs:hover{background:#fffde7;}',
            '.qc-si{font-size:52px;text-align:center;margin:8px 0 4px;}',
            '.qc-st2{font-size:19px;font-weight:800;text-align:center;color:#1a1a1a;margin-bottom:6px;}',
            '.qc-ss{font-size:13px;text-align:center;color:#666;margin-bottom:16px;line-height:1.6;white-space:pre-line;}',
            '.qc-oc{background:#fffdf0;border:1.5px solid #f7d87b;border-radius:14px;padding:14px 16px;margin-bottom:4px;}',
            '.qc-or{display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #f5edd0;font-size:13px;gap:10px;}',
            '.qc-or:last-child{border-bottom:none;}',
            '.qc-or .k{color:#b07020;font-weight:600;flex-shrink:0;}',
            '.qc-or .v{color:#1a1a1a;font-weight:600;text-align:'+LR+';}',
            '.qc-ot .v{font-size:16px;color:#d4500a;font-weight:800;}',
            '.qc-toast{position:fixed;bottom:22px;left:50%;transform:translateX(-50%) translateY(70px);background:#2a1800;color:#fff;border-radius:10px;padding:11px 22px;font-size:14px;z-index:999999;transition:transform .3s;pointer-events:none;white-space:nowrap;}',
            '.qc-toast.on{transform:translateX(-50%) translateY(0);}',
            '.qc-toast.ok{background:#2d8a4e;}.qc-toast.err{background:#c0392b;}',
            '@keyframes qc-spin{to{transform:rotate(360deg);}}',
            '.qc-sp{width:17px;height:17px;border:2.5px solid rgba(0,0,0,.2);border-top-color:#1a1a1a;border-radius:50%;animation:qc-spin .7s linear infinite;display:inline-block;}',
            '.qc-lp{text-align:center;padding:20px;color:#c07020;font-size:14px;}'
        ].join('');
        document.head.appendChild(st);
    }

    /* ── Translations ── */
    var T={
        title:isAr?'اشتري سريعاً':'Fast Checkout',
        subtitle:isAr?'أكمل طلبك في ثوانٍ':'Complete your order in seconds',
        lbl_name:isAr?'الاسم الكامل':'Full Name',
        lbl_phone:isAr?'رقم الهاتف':'Phone Number',
        lbl_loc:isAr?'📍 موقع التوصيل':'📍 Delivery Location',
        lbl_addr:isAr?'العنوان التفصيلي':'Detailed Address',
        ph_name:isAr?'أدخل اسمك الكامل':'Enter your full name',
        ph_phone:isAr?'+965 XXXX XXXX':'+965 XXXX XXXX',
        ph_addr:isAr?'يمكنك تعديل العنوان هنا':'You can edit the address here',
        my_loc:isAr?'⊕ موقعي':'⊕ My Location',
        detecting:isAr?'جارٍ تحديد موقعك…':'Detecting your location…',
        loading_adr:isAr?'جارٍ تحميل العنوان…':'Loading address…',
        loc_err:isAr?'تعذّر الحصول على الموقع':'Could not get location',
        adr_err:isAr?'تعذّر جلب العنوان':'Could not fetch address',
        err_name:isAr?'الرجاء إدخال اسمك':'Please enter your name',
        err_phone:isAr?'الرجاء إدخال رقم الهاتف':'Please enter your phone',
        confirm:isAr?'← متابعة للدفع':'Continue to Payment →',
        choose_pay:isAr?'اختر طريقة الدفع':'Choose Payment Method',
        loading_pay:isAr?'جارٍ تحميل وسائل الدفع…':'Loading payment methods…',
        btn_pay:isAr?'تأكيد الطلب':'Place Order',
        back:isAr?'← رجوع':'← Back',
        processing:isAr?'جارٍ المعالجة…':'Processing…',
        empty_cart:isAr?'السلة فارغة':'Cart is empty',
        went_wrong:isAr?'حدث خطأ ما':'Something went wrong',
        prod_unavail:isAr?'المنتج غير متاح':'Product not available',
        wait:isAr?'لحظة…':'Please wait…',
        sel_pay:isAr?'الرجاء اختيار طريقة الدفع':'Please select a payment method',
        order_done:isAr?'تم تأكيد طلبك!':'Order Confirmed!',
        congrats:isAr?'مبروك! تم إتمام طلبك.\nسيتم التواصل معك قريباً.':'Congratulations! Order placed.\nWe\'ll contact you soon.',
        ord_num:isAr?'رقم الطلب':'Order #',
        ord_total:isAr?'المبلغ الإجمالي':'Total',
        del_addr:isAr?'عنوان التوصيل':'Delivery Address',
        phone_lbl:isAr?'رقم التواصل':'Phone',
        pay_lbl:isAr?'طريقة الدفع':'Payment',
        cont_shop:isAr?'🛍 متابعة التسوق':'🛍 Continue Shopping'
    };

    /* ── Helpers ── */
    var toastEl=null;
    function toast(msg,type){
        if(!toastEl){toastEl=document.createElement('div');toastEl.className='qc-toast';document.body.appendChild(toastEl);}
        toastEl.textContent=msg;
        toastEl.className='qc-toast'+(type==='ok'?' ok':type==='err'?' err':'');
        requestAnimationFrame(function(){toastEl.classList.add('on');});
        clearTimeout(toastEl._t);
        toastEl._t=setTimeout(function(){toastEl.classList.remove('on');},3200);
    }
    function getCsrf(){
        var m=document.querySelector('meta[name="csrf-token"]');
        if(m)return m.getAttribute('content');
        if(window.odoo&&window.odoo.csrf_token)return window.odoo.csrf_token;
        var c=document.cookie.match(/\bcsrf_token=([^;]+)/);
        return c?decodeURIComponent(c[1]):'';
    }
    function rpc(url,params){
        return fetch(url,{
            method:'POST',
            headers:{'Content-Type':'application/json','X-CSRFToken':getCsrf()},
            body:JSON.stringify({jsonrpc:'2.0',method:'call',id:Date.now(),params:params||{}})
        }).then(function(r){return r.json();}).then(function(d){
            if(d.error)throw new Error((d.error.data&&d.error.data.message)||'Server error');
            return d.result;
        });
    }
    var lfProm=null;
    function loadLeaflet(){
        if(lfProm)return lfProm;
        lfProm=new Promise(function(res){
            if(window.L)return res(window.L);
            var lnk=document.createElement('link');lnk.rel='stylesheet';
            lnk.href='https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
            document.head.appendChild(lnk);
            var s=document.createElement('script');
            s.src='https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
            s.onload=function(){res(window.L);};
            document.head.appendChild(s);
        });
        return lfProm;
    }

    /* ── State ── */
    var ov=null,lfMap=null,lfMk=null,locD={};
    var selPay=null,selPayName='',lastOD=null,addrEdited=false;
    var curProd={id:0,name:'',url:''};

    /* ── Dialog HTML ── */
    function buildDlg(){
        if(ov)return;
        ov=document.createElement('div');ov.className='qc-overlay';ov.id='qc-ov';
        ov.innerHTML=
          '<div class="qc-dialog">'+
            '<div id="qs1" style="display:flex;flex-direction:column;flex:1;min-height:0">'+
              '<div class="qc-head">'+
                '<button class="qc-x" id="qx1">\u2715</button>'+
                '<h2>\u26a1 '+T.title+'</h2><p>'+T.subtitle+'</p>'+
                '<div class="qc-badge" id="qbg" style="display:none">\ud83d\udce6 <span id="qpn"></span></div>'+
              '</div>'+
              '<div class="qc-body">'+
                '<label class="qc-lbl">'+T.lbl_name+'</label>'+
                '<input class="qc-inp" id="qnm" type="text" placeholder="'+T.ph_name+'" autocomplete="name"/>'+
                '<label class="qc-lbl">'+T.lbl_phone+'</label>'+
                '<input class="qc-inp" id="qph" type="tel" placeholder="'+T.ph_phone+'" autocomplete="tel"/>'+
                '<label class="qc-lbl">'+T.lbl_loc+'</label>'+
                '<div class="qc-mw"><div class="qc-map" id="qmap"></div>'+
                '<button class="qc-loc" id="qloc">'+T.my_loc+'</button></div>'+
                '<p class="qc-hint" id="qhint" style="color:#bbb">\ud83d\udccd '+T.detecting+'</p>'+
                '<label class="qc-lbl">'+T.lbl_addr+'</label>'+
                '<textarea class="qc-inp" id="qadr" placeholder="'+T.ph_addr+'"></textarea>'+
              '</div>'+
              '<div class="qc-footer"><button class="qc-btn" id="qs1n">'+T.confirm+'</button></div>'+
            '</div>'+
            '<div id="qs2" style="display:none;flex-direction:column;flex:1;min-height:0">'+
              '<div class="qc-head"><button class="qc-x" id="qx2">\u2715</button>'+
                '<h2>\ud83d\udcb3 '+T.choose_pay+'</h2><p>'+T.subtitle+'</p></div>'+
              '<div class="qc-body"><div id="qpl" class="qc-pl"><div class="qc-lp">\u23f3 '+T.loading_pay+'</div></div></div>'+
              '<div class="qc-footer">'+
                '<button class="qc-btn" id="qpb" disabled>'+T.btn_pay+'</button>'+
                '<button class="qc-bs" id="qbk">'+T.back+'</button>'+
              '</div>'+
            '</div>'+
            '<div id="qs3" style="display:none;flex-direction:column;flex:1;min-height:0">'+
              '<div class="qc-head"><button class="qc-x" id="qx3">\u2715</button>'+
                '<h2>\ud83c\udf89 '+T.order_done+'</h2><p>'+T.subtitle+'</p></div>'+
              '<div class="qc-body">'+
                '<div class="qc-si">\ud83c\udf8a</div>'+
                '<div class="qc-st2">\ud83c\udf89 '+T.order_done+'</div>'+
                '<div class="qc-ss">'+T.congrats+'</div>'+
                '<div class="qc-oc" id="qod"></div>'+
              '</div>'+
              '<div class="qc-footer" id="qf3">'+
                '<button class="qc-btn" id="qdb">'+T.cont_shop+'</button>'+
              '</div>'+
            '</div>'+
          '</div>';
        document.body.appendChild(ov);
        function on(id,ev,fn){var e=ov.querySelector('#'+id);if(e)e.addEventListener(ev,fn);}
        on('qx1','click',closeDlg);on('qx2','click',closeDlg);on('qx3','click',closeDlg);
        on('qloc','click',locateMe);
        on('qs1n','click',goToPay);
        on('qbk','click',function(){showStep(1);});
        on('qpb','click',placeOrder);
        on('qdb','click',function(){closeDlg();window.location.href='/shop';});
        on('qadr','input',function(){addrEdited=true;});
        ov.addEventListener('click',function(e){if(e.target===ov)closeDlg();});
        document.addEventListener('keydown',function(e){if(e.key==='Escape')closeDlg();});
    }

    function showStep(n){
        if(!ov)return;
        var s1=ov.querySelector('#qs1'),s2=ov.querySelector('#qs2'),s3=ov.querySelector('#qs3');
        if(s1)s1.style.display=n===1?'flex':'none';
        if(s2)s2.style.display=n===2?'flex':'none';
        if(s3)s3.style.display=n===3?'flex':'none';
    }

    function openDlg(pid,pname,purl){
        buildDlg();
        addrEdited=false;selPay=null;selPayName='';lastOD=null;locD={};
        curProd={id:pid||0,name:pname||'',url:purl||window.location.href};
        var nm=ov.querySelector('#qnm'),ph=ov.querySelector('#qph'),
            ad=ov.querySelector('#qadr'),hi=ov.querySelector('#qhint'),
            bg=ov.querySelector('#qbg'),pn=ov.querySelector('#qpn'),
            pl=ov.querySelector('#qpl'),pb=ov.querySelector('#qpb');
        if(nm)nm.value='';if(ph)ph.value='';
        if(ad){ad.value='';ad.classList.remove('qf');}
        if(hi){hi.style.color='#bbb';hi.textContent='\ud83d\udccd '+T.detecting;}
        if(bg&&pn){pn.textContent=pname||'';bg.style.display=pname?'inline-flex':'none';}
        if(pl)pl.innerHTML='<div class="qc-lp">\u23f3 '+T.loading_pay+'</div>';
        if(pb)pb.disabled=true;
        if(ov)ov.querySelectorAll('.qc-po').forEach(function(o){
            o.classList.remove('sel');var c=o.querySelector('.qc-pc');if(c)c.textContent='';});
        showStep(1);
        ov.classList.add('qc-show');
        document.body.style.overflow='hidden';
        if(nm)nm.focus();
        loadLeaflet().then(function(){setTimeout(initMap,200);});
        loadPays();
    }

    function closeDlg(){if(ov)ov.classList.remove('qc-show');document.body.style.overflow='';}

    /* ── Map ── */
    function mkIcon(){
        return window.L.divIcon({html:'<div style="width:26px;height:26px;background:#f7b731;border:3px solid #fff;border-radius:50% 50% 50% 0;transform:rotate(-45deg);box-shadow:0 2px 8px rgba(0,0,0,.3)"></div>',className:'',iconSize:[26,26],iconAnchor:[13,26]});
    }
    function initMap(){
        var L=window.L;if(!L)return;
        var mel=document.getElementById('qmap');if(!mel)return;
        if(!lfMap){
            lfMap=L.map(mel,{zoomControl:true}).setView([26.8,30.8],5);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'\u00a9 OSM'}).addTo(lfMap);
            lfMap.on('click',function(e){plMk(e.latlng.lat,e.latlng.lng);revGeo(e.latlng.lat,e.latlng.lng);});
        }else{lfMap.invalidateSize();}
        fetch('https://ipapi.co/json/').then(function(r){return r.json();}).then(function(g){
            if(!g||!g.latitude)return;
            lfMap.setView([g.latitude,g.longitude],13);plMk(g.latitude,g.longitude);
            locD={latitude:g.latitude,longitude:g.longitude,city:g.city||'',country_code:g.country_code||''};
            revGeo(g.latitude,g.longitude);
        }).catch(function(){});
    }
    function plMk(lat,lng){
        if(!window.L||!lfMap)return;
        if(lfMk)lfMap.removeLayer(lfMk);
        lfMk=window.L.marker([lat,lng],{icon:mkIcon(),draggable:true}).addTo(lfMap);
        lfMk.on('dragend',function(e){var p=e.target.getLatLng();locD.latitude=p.lat;locD.longitude=p.lng;revGeo(p.lat,p.lng);});
        locD.latitude=lat;locD.longitude=lng;
    }
    function revGeo(lat,lng){
        var hi=ov&&ov.querySelector('#qhint'),ab=ov&&ov.querySelector('#qadr');
        if(hi){hi.style.color='#aaa';hi.textContent='\ud83d\udccd '+T.loading_adr;}
        fetch('https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat='+lat+'&lon='+lng+'&accept-language='+(isAr?'ar,en':'en'))
            .then(function(r){return r.json();}).then(function(d){
                if(!d)return;
                var a=d.address||{};
                locD.street=[a.road,a.house_number].filter(Boolean).join(' ');
                locD.city=a.city||a.town||a.village||a.county||'';
                locD.country_code=(a.country_code||'').toUpperCase();
                locD.full_address=d.display_name||'';
                if(hi){hi.style.color='#555';hi.textContent='\ud83d\udccd '+(locD.full_address||'Location set');}
                if(ab&&!addrEdited){ab.value=locD.full_address||'';ab.classList.add('qf');setTimeout(function(){if(ab)ab.classList.remove('qf');},1500);}
            }).catch(function(){if(hi){hi.style.color='#c00';hi.textContent=T.adr_err;}});
    }
    function locateMe(){
        var btn=ov&&ov.querySelector('#qloc');
        if(!navigator.geolocation){toast(isAr?'تحديد الموقع غير مدعوم':'Geolocation not supported','err');return;}
        if(btn){btn.textContent=isAr?'جارٍ التحديد…':'Locating…';btn.disabled=true;}
        navigator.geolocation.getCurrentPosition(function(pos){
            if(lfMap)lfMap.setView([pos.coords.latitude,pos.coords.longitude],15);
            plMk(pos.coords.latitude,pos.coords.longitude);
            revGeo(pos.coords.latitude,pos.coords.longitude);
            if(btn){btn.textContent=T.my_loc;btn.disabled=false;}
        },function(){
            toast(T.loc_err,'err');
            if(btn){btn.textContent=T.my_loc;btn.disabled=false;}
        });
    }

    /* ── Payment methods ── */
    function getIcon(name,code){
        var n=(name||'').toLowerCase(),c=(code||'').toLowerCase();
        if(n.includes('knet')||c.includes('knet'))return{bg:'#fff',src:'https://upload.wikimedia.org/wikipedia/en/thumb/9/9e/KNET_logo.png/220px-KNET_logo.png',em:'\ud83c\udfe6'};
        if(n.includes('apple')||c.includes('apple'))return{bg:'#000',src:'https://developer.apple.com/assets/elements/icons/apple-pay/apple-pay.svg',em:'\ud83c\udf4e'};
        if(n.includes('google')||c.includes('google'))return{bg:'#fff',src:'https://upload.wikimedia.org/wikipedia/commons/thumb/f/f2/Google_Pay_Logo.svg/320px-Google_Pay_Logo.svg.png',em:'G'};
        if(n.includes('samsung')||c.includes('samsung'))return{bg:'#1428a0',src:'https://upload.wikimedia.org/wikipedia/commons/thumb/2/24/Samsung_Pay_wordmark.svg/320px-Samsung_Pay_wordmark.svg.png',em:'\ud83d\udcf1'};
        if(n.includes('visa')||n.includes('mastercard')||n.includes('credit')||c.includes('card'))return{bg:'#1a1f71',src:'https://upload.wikimedia.org/wikipedia/commons/thumb/5/5e/Visa_Inc._logo.svg/320px-Visa_Inc._logo.svg.png',em:'\ud83d\udcb3'};
        if(n.includes('cash')||n.includes('delivery')||n.includes('\u0627\u0633\u062a\u0644\u0627\u0645')||c==='cod')return{bg:'#e8f5e9',src:'',em:'\ud83d\udcb5'};
        return{bg:'#f5f5f5',src:'',em:'\ud83d\udcb3'};
    }
    function loadPays(){
        rpc('/shop/fb/payment_methods',{}).then(function(res){
            renderPays((res&&res.success&&res.methods&&res.methods.length)?res.methods:[{id:-1,name:isAr?'\u0627\u0644\u062f\u0641\u0639 \u0639\u0646\u062f \u0627\u0644\u0627\u0633\u062a\u0644\u0627\u0645':'Cash on Delivery',code:'cod',image:''}]);
        }).catch(function(){renderPays([{id:-1,name:'Cash on Delivery',code:'cod',image:''}]);});
    }
    function renderPays(methods){
        if(!ov)return;
        var list=ov.querySelector('#qpl');if(!list)return;
        var html='';
        for(var i=0;i<methods.length;i++){
            var m=methods[i],info=getIcon(m.name,m.code),src=info.src||m.image||'';
            var ic=src?'<img src="'+src+'" alt="" style="width:100%;height:100%;object-fit:contain" onerror="this.style.display=\'none\';this.nextSibling.style.display=\'flex\'"/><span style="display:none;width:100%;height:100%;align-items:center;justify-content:center;font-size:22px">'+info.em+'</span>':'<span style="font-size:24px;line-height:1">'+info.em+'</span>';
            html+='<div class="qc-po" data-id="'+m.id+'" data-code="'+m.code+'" data-name="'+m.name+'"><div class="qc-pi" style="background:'+info.bg+';padding:4px;overflow:hidden">'+ic+'</div><span class="qc-pn">'+m.name+'</span><span class="qc-pc"></span></div>';
        }
        list.innerHTML=html||'<div class="qc-lp" style="color:#c00">No methods</div>';
        var opts=list.querySelectorAll('.qc-po');
        opts.forEach(function(opt){
            opt.addEventListener('click',function(){
                opts.forEach(function(o){o.classList.remove('sel');var c=o.querySelector('.qc-pc');if(c)c.textContent='';});
                opt.classList.add('sel');
                var ch=opt.querySelector('.qc-pc');if(ch)ch.textContent='\u2713';
                selPay=opt.dataset.code;selPayName=opt.dataset.name;
                var pb=ov?ov.querySelector('#qpb'):null;if(pb)pb.disabled=false;
            });
        });
    }

    /* ── Steps ── */
    function goToPay(){
        var nm=ov&&ov.querySelector('#qnm'),ph=ov&&ov.querySelector('#qph'),ad=ov&&ov.querySelector('#qadr');
        var name=nm?nm.value.trim():'',phone=ph?ph.value.trim():'';
        var addr=(ad?ad.value.trim():'')||locD.full_address||'';
        if(!name){toast(T.err_name,'err');if(nm)nm.focus();return;}
        if(!phone){toast(T.err_phone,'err');if(ph)ph.focus();return;}
        lastOD={name:name,phone:phone,latitude:locD.latitude||'',longitude:locD.longitude||'',street:locD.street||'',city:locD.city||'',country_code:locD.country_code||'',full_address:addr};
        showStep(2);
    }
    function placeOrder(){
        if(!selPay){toast(T.sel_pay,'err');return;}
        var btn=ov&&ov.querySelector('#qpb');
        if(btn){btn.disabled=true;btn.innerHTML='<div class="qc-sp"></div>&nbsp;'+T.processing;}
        rpc('/shop/fb/submit',Object.assign({},lastOD,{payment_method:selPay}))
            .then(function(res){
                if(res&&res.success){showSuccess(res);}
                else{toast(res&&res.error==='empty_cart'?T.empty_cart:T.went_wrong,'err');if(btn){btn.disabled=false;btn.textContent=T.btn_pay;}}
            }).catch(function(err){toast('Error: '+err.message,'err');if(btn){btn.disabled=false;btn.textContent=T.btn_pay;}});
    }
    function showSuccess(res){
        var el=ov&&ov.querySelector('#qod');if(!el)return;
        var oname=res.order_name||res.order_id||'\u2014';
        var amt=(res.amount_total&&res.amount_total!=='0.000')?res.amount_total+' '+(res.currency||''):'\u2014';
        var pname=res.product_name||curProd.name||'\u2014';
        var purl=res.product_url||curProd.url||'';
        el.innerHTML=[
            {k:T.ord_num,v:'#'+oname,t:false},{k:T.ord_total,v:amt,t:true},
            {k:T.phone_lbl,v:lastOD?lastOD.phone:'\u2014',t:false},
            {k:T.del_addr,v:lastOD?(lastOD.full_address||'\u2014'):'\u2014',t:false},
            {k:T.pay_lbl,v:selPayName||selPay||'\u2014',t:false}
        ].map(function(r){return '<div class="qc-or'+(r.t?' qc-ot':'')+'"><span class="k">'+r.k+'</span><span class="v">'+r.v+'</span></div>';}).join('');
        var footer=ov&&ov.querySelector('#qf3');
        if(footer){
            var waMsg=isAr
                ?'\u0645\u0631\u062d\u0628\u0627\u064b\u060c \u0644\u0642\u062f \u0623\u062a\u0645\u0645\u062a \u0637\u0644\u0628\u064a.\n\ud83d\udce6 '+pname+'\n\ud83d\udd22 #'+oname+'\n\ud83d\udcb0 '+amt+'\n\ud83d\udcde '+(lastOD?lastOD.phone:'')+'\n\ud83d\udccd '+(lastOD?lastOD.full_address:'')+(purl?'\n\ud83d\udd17 '+purl:'')
                :'Hello, I just placed an order.\n\ud83d\udce6 '+pname+'\n\ud83d\udd22 #'+oname+'\n\ud83d\udcb0 '+amt+'\n\ud83d\udcde '+(lastOD?lastOD.phone:'')+'\n\ud83d\udccd '+(lastOD?lastOD.full_address:'')+(purl?'\n\ud83d\udd17 '+purl:'');
            var waUrl='https://wa.me/?text='+encodeURIComponent(waMsg);
            footer.innerHTML='<div style="display:flex;gap:10px">'+
                '<button class="qc-btn" id="qdb2" style="flex:1;font-size:13px;padding:12px 8px">'+T.cont_shop+'</button>'+
                '<a href="'+waUrl+'" target="_blank" style="flex:1;position:relative;display:flex;align-items:center;justify-content:center;gap:7px;padding:12px 8px;border:none;border-radius:12px;text-decoration:none;background:linear-gradient(135deg,#25d366,#128c7e);color:#fff;font-size:13px;font-weight:700;box-shadow:0 4px 14px rgba(37,211,102,.3)">'+
                '<span style="position:absolute;top:-9px;'+LR+':10px;background:#e53935;color:#fff;font-size:10px;font-weight:700;padding:2px 7px;border-radius:10px">'+(isAr?'\u0648\u0627\u062a\u0633\u0627\u0628':'WhatsApp')+'</span>'+
                '<svg width="18" height="18" viewBox="0 0 24 24" fill="#fff"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z"/><path d="M12 0C5.373 0 0 5.373 0 12c0 2.123.554 4.118 1.528 5.845L0 24l6.337-1.51A11.956 11.956 0 0012 24c6.627 0 12-5.373 12-12S18.627 0 12 0zm0 21.818a9.818 9.818 0 01-5.007-1.374l-.36-.214-3.73.889.933-3.617-.235-.372A9.818 9.818 0 0112 2.182c5.42 0 9.818 4.398 9.818 9.818 0 5.42-4.398 9.818-9.818 9.818z"/></svg>'+
                (isAr?'\u062a\u0648\u0627\u0635\u0644 \u0645\u0639\u0646\u0627':'Contact Us')+'</a></div>';
            var db2=ov&&ov.querySelector('#qdb2');
            if(db2)db2.addEventListener('click',function(){closeDlg();window.location.href='/shop';});
        }
        showStep(3);
    }

    /* ── Button binding ── */
    function bindBtn(){
        if(!document.body)return;
        // Attach directly to each button - bypasses theme_prime delegation
        function attachToBtn(btn){
            btn.addEventListener('click',function(e){
            e.preventDefault();e.stopPropagation();e.stopImmediatePropagation();
            var wrap=btn.closest('[data-template-id]')||btn.closest('[data-default-product-id]');
            var pid=0;
            if(wrap)pid=parseInt(wrap.getAttribute('data-template-id')||'0',10);
            if(!pid){var pm=window.location.pathname.match(/-([0-9]+)\/?(?:[?#]|$)/);if(pm)pid=parseInt(pm[1],10);}
            if(!pid){toast(T.prod_unavail,'err');return;}
            var orig=btn.innerHTML;
            btn.disabled=true;
            btn.innerHTML='<span class="qc-sp" style="width:14px;height:14px;margin-right:6px;vertical-align:middle;display:inline-block"></span>'+T.wait;
            rpc('/shop/fb/add/'+pid,{}).then(function(res){
                btn.disabled=false;btn.innerHTML=orig;
                if(res&&res.success){openDlg(res.product_id,res.product_name,res.product_url||window.location.href);}
                else{toast(T.prod_unavail,'err');}
            }).catch(function(err){btn.disabled=false;btn.innerHTML=orig;toast('Error: '+err.message,'err');});
            },true);
        }
        // Attach to all existing buttons
        document.querySelectorAll('.qc-open-btn').forEach(attachToBtn);
        // Watch for dynamically added buttons
        var obs=new MutationObserver(function(muts){
            muts.forEach(function(m){m.addedNodes.forEach(function(n){
                if(n.nodeType===1){
                    if(n.classList&&n.classList.contains('qc-open-btn'))attachToBtn(n);
                    n.querySelectorAll&&n.querySelectorAll('.qc-open-btn').forEach(attachToBtn);
                }
            });});
        });
        obs.observe(document.body,{childList:true,subtree:true});
    }
    if(document.body){bindBtn();}
    else{document.addEventListener('DOMContentLoaded',bindBtn);}

    window.__fbReady=true;
})();
