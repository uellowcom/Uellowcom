(function(){
'use strict';

var AC=[
  {bar:'#7f77dd',av:'#7f77dd'},
  {bar:'#1d9e75',av:'#1d9e75'},
  {bar:'#d85a30',av:'#d85a30'},
  {bar:'#378add',av:'#378add'},
  {bar:'#d4537e',av:'#d4537e'},
  {bar:'#854f0b',av:'#854f0b'}
];

function init(){
  var w = document.querySelector('.prw');
  if(!w || w.dataset.j) return;
  w.dataset.j = '1';

  var cards = Array.from(document.querySelectorAll('.prw-card'));

  // Apply accent colors
  cards.forEach(function(c, i){
    var ac = AC[i % AC.length];
    var bar = c.querySelector('.prw-accent-bar');
    var av  = c.querySelector('.prw-avatar');
    if(bar) bar.style.background = ac.bar;
    if(av)  av.style.background  = ac.av;
  });

  // ── Show More (1 card initially, overlay) ────────────
  var overlay  = document.getElementById('prwShowMoreOverlay');
  var showBtn  = document.getElementById('prwShowMoreBtn');
  var PER_PAGE = 5;
  var expanded = false;
  var pager    = document.getElementById('prwPager');
  var pages    = Math.ceil(cards.length / PER_PAGE);
  var page     = 0;

  function renderPage(p){
    page = p;
    cards.forEach(function(c, i){
      c.style.display = (i >= p*PER_PAGE && i < (p+1)*PER_PAGE) ? '' : 'none';
    });
    var info = document.getElementById('prwPgInfo');
    var prev = document.getElementById('prwPrev');
    var next = document.getElementById('prwNext');
    if(info) info.textContent = 'Page '+(p+1)+' of '+pages;
    if(prev) prev.disabled = p === 0;
    if(next) next.disabled = p >= pages-1;
  }

  function applyInitial(){
    // Show only 1 card, show overlay
    cards.forEach(function(c, i){ c.style.display = i === 0 ? '' : 'none'; });
    if(overlay) overlay.classList.remove('hidden');
    if(pager)   pager.style.display = 'none';
  }

  function applyExpanded(){
    expanded = true;
    renderPage(0);
    if(overlay) overlay.classList.add('hidden');
    if(cards.length > PER_PAGE && pager){
      pager.style.display = 'flex';
      var prev = document.getElementById('prwPrev');
      var next = document.getElementById('prwNext');
      if(prev) prev.addEventListener('click', function(){
        if(page > 0){ renderPage(page-1); document.querySelector('.prw-list-wrap').scrollIntoView({behavior:'smooth',block:'start'}); }
      });
      if(next) next.addEventListener('click', function(){
        if(page < pages-1){ renderPage(page+1); document.querySelector('.prw-list-wrap').scrollIntoView({behavior:'smooth',block:'start'}); }
      });
    }
  }

  if(cards.length > 0) applyInitial();
  if(showBtn) showBtn.addEventListener('click', applyExpanded);

  // ── Filter chips ──────────────────────────────────────
  document.querySelectorAll('.prw-chip').forEach(function(ch){
    ch.addEventListener('click', function(){
      document.querySelectorAll('.prw-chip').forEach(function(c){ c.style.opacity = '.5'; });
      this.style.opacity = '1';
      var f = this.dataset.filter;
      if(!expanded) applyExpanded();
      cards.forEach(function(c){
        if(f === 'all')      c.style.display = '';
        else if(f === 'photo')    c.style.display = c.dataset.img === '1' ? '' : 'none';
        else if(f === '5star')    c.style.display = c.dataset.rating === '5' ? '' : 'none';
        else if(f === 'verified') c.style.display = c.dataset.verified === '1' ? '' : 'none';
      });
    });
  });

  // ── Write Review Dialog ───────────────────────────────
  var logged    = w.dataset.logged === '1';
  var loginUrl  = w.dataset.loginUrl || '/web/login';
  var pid       = w.dataset.productId;
  var ov        = document.getElementById('prwOverlay');
  var dlgClose  = document.getElementById('prwDlgClose');
  var dlgCont   = document.getElementById('prwDlgContent');
  var succMsg   = document.getElementById('prwSuccessMsg');
  var succClose = document.getElementById('prwSuccessClose');
  var form      = document.getElementById('prwForm');

  function openDlg(){ if(!logged){ window.location.href = loginUrl; return; } if(ov){ ov.style.display='flex'; document.body.style.overflow='hidden'; } }
  function closeDlg(){ if(ov){ ov.style.display='none'; document.body.style.overflow=''; } if(succMsg) succMsg.style.display='none'; if(dlgCont) dlgCont.style.display='block'; if(form) form.reset(); resetStars(); }

  var wb = document.getElementById('prwWriteBtn');
  if(wb)       wb.addEventListener('click', openDlg);
  if(dlgClose) dlgClose.addEventListener('click', closeDlg);
  if(succClose)succClose.addEventListener('click', closeDlg);
  if(ov)       ov.addEventListener('click', function(e){ if(e.target===ov) closeDlg(); });
  document.addEventListener('keydown', function(e){ if(e.key==='Escape' && ov && ov.style.display!=='none') closeDlg(); });

  // Stars
  var sp  = document.getElementById('prwStarPick');
  var ri  = document.getElementById('prwRating');
  var sel = 0;
  function resetStars(){ sel=0; if(ri) ri.value=''; if(sp) sp.querySelectorAll('span').forEach(function(s){ s.classList.remove('on'); }); }
  if(sp){
    var stars = sp.querySelectorAll('span');
    stars.forEach(function(s, i){
      s.addEventListener('click', function(){ sel=i+1; if(ri) ri.value=sel; stars.forEach(function(x,j){ x.classList.toggle('on', j<sel); }); });
      s.addEventListener('mouseenter', function(){ stars.forEach(function(x,j){ x.classList.toggle('on', j<=i); }); });
    });
    sp.addEventListener('mouseleave', function(){ stars.forEach(function(x,j){ x.classList.toggle('on', j<sel); }); });
  }

  // Submit
  if(form){
    form.addEventListener('submit', function(e){
      e.preventDefault();
      if(!ri || !ri.value){ alert('Please select a rating.'); return; }
      var btn = form.querySelector('.prw-dlg-submit');
      if(btn){ btn.disabled=true; btn.textContent='Submitting...'; }
      var fd = new FormData(form);
      fd.append('product_id', pid);
      fetch('/reviews/write/ajax', { method:'POST', headers:{'X-Requested-With':'XMLHttpRequest'}, body:fd })
        .then(function(r){ return r.json(); })
        .then(function(d){
          if(d.success){ if(dlgCont) dlgCont.style.display='none'; if(succMsg) succMsg.style.display='block'; }
          else{ alert(d.error||'Error.'); if(btn){ btn.disabled=false; btn.textContent='Submit Review'; } }
        }).catch(function(){ alert('Error. Try again.'); if(btn){ btn.disabled=false; btn.textContent='Submit Review'; } });
    });
  }

  // File preview
  var fi = document.getElementById('prwFiles');
  var pv = document.getElementById('prwPrevs');
  var dz = document.getElementById('prwDrop');
  if(fi && pv){
    fi.addEventListener('change', function(){ buildPrev(this.files); });
    if(dz){
      dz.addEventListener('dragover',  function(e){ e.preventDefault(); dz.style.borderColor='#ffda23'; });
      dz.addEventListener('dragleave', function(){ dz.style.borderColor=''; });
      dz.addEventListener('drop', function(e){ e.preventDefault(); dz.style.borderColor=''; if(e.dataTransfer.files.length) buildPrev(e.dataTransfer.files); });
    }
  }
  function buildPrev(files){
    if(!pv) return; pv.innerHTML='';
    Array.from(files).slice(0,6).forEach(function(f){
      if(!f.type.startsWith('image/')) return;
      var r = new FileReader();
      r.onload = function(e){ var el=document.createElement('div'); el.className='prw-pv'; el.innerHTML='<img src="'+e.target.result+'"/><button type="button" class="prw-pv-rm">x</button>'; el.querySelector('.prw-pv-rm').onclick=function(){ el.remove(); }; pv.appendChild(el); };
      r.readAsDataURL(f);
    });
  }

  // Helpful
  document.addEventListener('click', function(e){
    var btn = e.target.closest('.prw-helpful');
    if(!btn || btn.classList.contains('voted')) return;
    fetch('/reviews/helpful/'+btn.dataset.id, { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({jsonrpc:'2.0',method:'call',params:{}}) })
      .then(function(r){ return r.json(); })
      .then(function(d){ if(d.result && d.result.count!==undefined){ btn.innerHTML='&#128077; Helpful ('+d.result.count+')'; btn.classList.add('voted'); }})
      .catch(function(){});
  });

  // Lightbox
  var lb    = document.getElementById('prwLb');
  var lbImg = document.getElementById('prwLbImg');
  document.addEventListener('click', function(e){
    var t = e.target.closest('.prw-thumb');
    if(!t) return; e.preventDefault();
    var src = t.dataset.src || (t.querySelector('img') && t.querySelector('img').src);
    if(src && lbImg && lb){ lbImg.src=src; lb.style.display='flex'; document.body.style.overflow='hidden'; }
  });
  if(lb){ lb.addEventListener('click', function(e){ if(e.target===lb || e.target.classList.contains('prw-lb-close')){ lb.style.display='none'; document.body.style.overflow=''; } }); }
}

if(document.readyState === 'loading'){ document.addEventListener('DOMContentLoaded', init); } else { init(); }
document.addEventListener('click', function(e){
  var t = e.target.closest('[href="#tp-product-rating-tab"],[data-bs-target="#tp-product-rating-tab"]');
  if(t) setTimeout(init, 200);
});
})();

// Arabic translation
(function(){
  function isArabic(){
    return document.documentElement.lang === 'ar' ||
           document.documentElement.dir === 'rtl' ||
           document.querySelector('html[dir="rtl"]') !== null;
  }

  var AR = {
    'Write a Review':     'اكتب تقييماً',
    'All':                'الكل',
    'Photos':             'صور',
    'Verified':           'موثق',
    'See More Reviews':   'عرض المزيد من التقييمات',
    'Prev':               'السابق',
    'Next':               'التالي',
    'Page':               'صفحة',
    'of':                 'من',
    'Helpful':            'مفيد',
    'Stars':              'نجوم',
    'Write a Review dialog title': 'اكتب تقييماً',
    'Rating *':           'التقييم *',
    'Review Title':       'عنوان التقييم',
    'Your Review *':      'تقييمك *',
    'Photos (optional)':  'صور (اختياري)',
    'Submit Review':      'إرسال التقييم',
    'Thank you!':         'شكراً لك!',
    'Your review is pending approval.': 'تقييمك قيد المراجعة.',
    'Close':              'إغلاق',
    'Summarize your experience': 'لخّص تجربتك',
    'Share your experience...':  'شارك تجربتك...',
    'Click or drag photos here': 'انقر أو اسحب الصور هنا',
    'Positive':           'إيجابي',
    'No reviews yet.':    'لا توجد تقييمات بعد.',
    'Please select a rating.': 'الرجاء اختيار تقييم.',
    'Submitting...':      'جارٍ الإرسال...',
    '5 stars': '5 نجوم', '4 stars': '4 نجوم', '3 stars': '3 نجوم',
    '2 stars': 'نجمتان', '1 star':  'نجمة',
  };

  function translateEl(sel, key){
    var el = document.querySelector(sel);
    if(el && AR[key]) el.textContent = AR[key];
  }

  function translateAll(){
    if(!isArabic()) return;

    // Btn
    var wb = document.getElementById('prwWriteBtn');
    if(wb) wb.textContent = '✏ ' + AR['Write a Review'];

    // Show more
    var sm = document.getElementById('prwShowMoreBtn');
    if(sm) sm.textContent = AR['See More Reviews'];

    // Chips
    document.querySelectorAll('.prw-chip').forEach(function(ch){
      var f = ch.dataset.filter;
      var txt = ch.textContent.trim();
      var num = txt.match(/\((\d+)\)/);
      num = num ? ' (' + num[1] + ')' : '';
      if(f==='all')      ch.textContent = AR['الكل'] || 'الكل' + num;
      if(f==='5star')    ch.textContent = '5★' + num;
      if(f==='photo')    ch.textContent = '📷 ' + AR['Photos'] + num;
      if(f==='verified') ch.textContent = '✓ ' + AR['Verified'] + num;
    });

    // Dialog labels
    var dlgTitle = document.querySelector('#prwDlgContent .prw-dlg-title');
    if(dlgTitle) dlgTitle.textContent = AR['Write a Review dialog title'];

    document.querySelectorAll('.prw-fld label').forEach(function(l){
      var t = l.textContent.trim();
      if(AR[t]) l.textContent = AR[t];
    });

    var inp = document.querySelector('[name="review_title"]');
    if(inp) inp.placeholder = AR['Summarize your experience'];
    var txt = document.querySelector('[name="feedback"]');
    if(txt) txt.placeholder = AR['Share your experience...'];
    var drop = document.querySelector('#prwDrop span');
    if(drop) drop.textContent = '📷 ' + AR['Click or drag photos here'];

    var sub = document.querySelector('.prw-dlg-submit:not(#prwSuccessClose)');
    if(sub && sub.form) sub.textContent = AR['Submit Review'];

    var sTitle = document.querySelector('.prw-success h4');
    if(sTitle) sTitle.textContent = AR['Thank you!'];
    var sMsg = document.querySelector('.prw-success p');
    if(sMsg) sMsg.textContent = AR['Your review is pending approval.'];
    var sClose = document.getElementById('prwSuccessClose');
    if(sClose) sClose.textContent = AR['Close'];

    // Bar labels
    document.querySelectorAll('.prw-bar-l').forEach(function(bl){
      var t = bl.textContent.trim();
      if(AR[t]) bl.textContent = AR[t];
    });

    // Stat labels
    document.querySelectorAll('.prw-stat-lbl').forEach(function(sl){
      var t = sl.textContent.trim();
      if(t==='Photos')   sl.textContent = AR['Photos'];
      if(t==='Verified') sl.textContent = AR['Verified'];
      if(t==='Positive') sl.textContent = AR['Positive'];
    });

    // Prev/Next
    var prev = document.getElementById('prwPrev');
    var next = document.getElementById('prwNext');
    if(prev) prev.textContent = '→ ' + AR['Prev'];
    if(next) next.textContent = AR['Next'] + ' ←';
  }

  if(document.readyState==='loading'){
    document.addEventListener('DOMContentLoaded', translateAll);
  } else {
    translateAll();
  }
  document.addEventListener('click', function(e){
    var t = e.target.closest('[href="#tp-product-rating-tab"],[data-bs-target="#tp-product-rating-tab"]');
    if(t) setTimeout(translateAll, 300);
  });
})();

// Arabic fix
(function(){
  var AR = {
    'Write a Review': 'اكتب تقييماً',
    'See More Reviews': 'عرض المزيد',
    'Photos': 'صور', 'Verified': 'موثق', 'Positive': 'إيجابي',
    '5 ★': '5 ★', '4 ★': '4 ★', '3 ★': '3 ★', '2 ★': '2 ★', '1 ★': '1 ★',
    'Submit Review': 'إرسال التقييم',
    'Thank you!': 'شكراً لك!',
    'Your review is pending approval.': 'تقييمك قيد المراجعة.',
    'Close': 'إغلاق',
    'Rating *': 'التقييم *',
    'Review Title': 'عنوان التقييم',
    'Your Review *': 'تقييمك *',
    'Photos (optional)': 'صور (اختياري)',
    'reviews': 'تقييم',
    'Prev': '→ السابق', 'Next': 'التالي ←',
    'Page': 'صفحة', 'of': 'من',
  };

  function isAr(){
    return document.documentElement.lang === 'ar' ||
           document.documentElement.getAttribute('dir') === 'rtl';
  }

  function translateNode(sel, text){
    var el = document.querySelector(sel);
    if(el) el.textContent = text;
  }

  function tr(){
    if(!isAr()) return;
    var wb = document.getElementById('prwWriteBtn');
    if(wb) wb.innerHTML = '&#9998; ' + AR['Write a Review'];

    var sm = document.getElementById('prwShowMoreBtn');
    if(sm) sm.textContent = AR['See More Reviews'];

    document.querySelectorAll('.prw-chip').forEach(function(ch){
      var f = ch.dataset.filter;
      var m = ch.textContent.match(/\((\d+)\)/);
      var n = m ? ' (' + m[1] + ')' : '';
      if(f==='all')      ch.innerHTML = 'الكل' + n;
      if(f==='5star')    ch.innerHTML = '5&#9733;' + n;
      if(f==='photo')    ch.innerHTML = '&#128247; صور' + n;
      if(f==='verified') ch.innerHTML = '&#10003; موثق' + n;
    });

    document.querySelectorAll('.prw-stat-lbl').forEach(function(sl){
      if(sl.textContent==='Photos')   sl.textContent='صور';
      if(sl.textContent==='Verified') sl.textContent='موثق';
      if(sl.textContent==='Positive') sl.textContent='إيجابي';
    });

    var lbl = document.querySelector('.prw-big-lbl');
    if(lbl) lbl.textContent = lbl.textContent.replace('reviews', 'تقييم');

    // Dialog (translate on open)
    var writeBtn = document.getElementById('prwWriteBtn');
    if(writeBtn){
      writeBtn.addEventListener('click', function(){
        setTimeout(function(){
          var t = document.querySelector('#prwDlgContent .prw-dlg-title');
          if(t) t.textContent = 'اكتب تقييماً';
          document.querySelectorAll('.prw-fld label').forEach(function(l){
            if(AR[l.textContent.trim()]) l.textContent = AR[l.textContent.trim()];
          });
          var ri = document.querySelector('[name="review_title"]');
          if(ri) ri.placeholder = 'لخّص تجربتك';
          var fb = document.querySelector('[name="feedback"]');
          if(fb) fb.placeholder = 'شارك تجربتك...';
          var dr = document.querySelector('#prwDrop span');
          if(dr) dr.textContent = '&#128247; انقر أو اسحب الصور هنا';
          var sb = document.querySelector('#prwForm .prw-dlg-submit');
          if(sb) sb.textContent = AR['Submit Review'];
          var sh = document.querySelector('.prw-success h4');
          if(sh) sh.textContent = AR['Thank you!'];
          var sp = document.querySelector('.prw-success p');
          if(sp) sp.textContent = AR['Your review is pending approval.'];
          var sc = document.getElementById('prwSuccessClose');
          if(sc) sc.textContent = AR['Close'];
        }, 50);
      }, {once: false});
    }
  }

  if(document.readyState==='loading'){
    document.addEventListener('DOMContentLoaded', tr);
  } else {
    tr();
  }
  document.addEventListener('click', function(e){
    var t = e.target.closest('[href="#tp-product-rating-tab"],[data-bs-target="#tp-product-rating-tab"]');
    if(t) setTimeout(tr, 300);
  });
})();
