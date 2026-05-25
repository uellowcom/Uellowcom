(function () {
    'use strict';

    // منع التكرار بـ WeakSet بدلاً من data attribute
    var initialized = new WeakSet();

    async function initSlider(section) {
        if (initialized.has(section)) return;

        var track = section.querySelector('.uellow-track');
        var frame = section.querySelector('.uellow-frame');

        // إذا مفيش track — الـ snippet نسخة قديمة، نتجاهل
        if (!track || !frame) return;

        initialized.add(section);

        track.innerHTML = '<div class="uellow-loading"><div class="uellow-spinner"></div></div>';

        try {
            var resp = await fetch('/uellow/brands', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ jsonrpc: '2.0', method: 'call', id: 1, params: {} })
            });
            var data = await resp.json();
            var brands = (data.result && data.result.brands) || [];

            if (!brands.length) { track.innerHTML = ''; return; }

            // shuffle
            for (var i = brands.length - 1; i > 0; i--) {
                var j = Math.floor(Math.random() * (i + 1));
                var tmp = brands[i]; brands[i] = brands[j]; brands[j] = tmp;
            }

            track.innerHTML = brands.map(function(b) {
                return '<div class="uellow-card">' +
                    '<a href="' + b.shop_url + '">' +
                    '<img src="' + b.image_url + '" alt="' + b.name + '"' +
                    ' onerror="this.closest(\'.uellow-card\').style.display=\'none\'">' +
                    '</a></div>';
            }).join('');

            // أزرار التنقل
            var btnPrev = section.querySelector('.uellow-btn-prev');
            var btnNext = section.querySelector('.uellow-btn-next');
            if (btnPrev) btnPrev.addEventListener('click', function() {
                frame.scrollBy({ left: -frame.clientWidth * 0.75, behavior: 'smooth' });
            });
            if (btnNext) btnNext.addEventListener('click', function() {
                frame.scrollBy({ left: frame.clientWidth * 0.75, behavior: 'smooth' });
            });

        } catch(e) {
            console.error('[UellowBrands]', e);
            track.innerHTML = '';
        }
    }

    function initAll() {
        document.querySelectorAll('.uellow-brands-section').forEach(initSlider);
    }

    // تشغيل عند تحميل الصفحة
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initAll);
    } else {
        initAll();
    }
    window.addEventListener('load', initAll);

    // مراقبة أي snippet يُضاف لاحقاً (drag & drop في Builder)
    if (typeof MutationObserver !== 'undefined') {
        new MutationObserver(function(mutations) {
            mutations.forEach(function(m) {
                m.addedNodes.forEach(function(node) {
                    if (node.nodeType === 1) {
                        if (node.classList && node.classList.contains('uellow-brands-section')) {
                            initSlider(node);
                        }
                        node.querySelectorAll && node.querySelectorAll('.uellow-brands-section').forEach(initSlider);
                    }
                });
            });
        }).observe(document.body, { childList: true, subtree: true });
    }

})();
