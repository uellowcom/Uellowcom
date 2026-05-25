/* Uellow Video Modal - no bootstrap dependency */
(function() {
    'use strict';

    window.UellowVideoModal = {
        open: function(el) {
            var type = el.dataset.videoType;
            var body = document.getElementById('uellowVideoModalBody');
            var overlay = document.getElementById('uellowVideoModal');
            if (!body || !overlay) return;

            document.getElementById('uellowVideoModalLabel').textContent = el.dataset.videoName || '';
            body.innerHTML = '';

            if (type === 'tiktok_url') {
                var tikId = el.dataset.tiktokId;
                if (tikId) {
                    var wrap = document.createElement('div');
                    wrap.className = 'uellow-tiktok-wrap';
                    var ifr = document.createElement('iframe');
                    ifr.src = 'https://www.tiktok.com/embed/v2/' + tikId;
                    ifr.setAttribute('allowfullscreen', '');
                    ifr.allow = 'encrypted-media';
                    ifr.scrolling = 'no';
                    wrap.appendChild(ifr);
                    body.appendChild(wrap);
                }
            } else if (type === 'direct_upload') {
                var vid = document.createElement('video');
                vid.controls = true;
                vid.autoplay = true;
                vid.setAttribute('playsinline', '');
                var src = document.createElement('source');
                src.src = el.dataset.fileUrl;
                vid.appendChild(src);
                body.appendChild(vid);
            } else {
                var eu = el.dataset.embedUrl;
                if (eu) {
                    var wrap2 = document.createElement('div');
                    wrap2.className = 'uellow-iframe-wrap';
                    var ifr2 = document.createElement('iframe');
                    ifr2.src = eu;
                    ifr2.setAttribute('allowfullscreen', '');
                    ifr2.allow = 'autoplay;encrypted-media';
                    wrap2.appendChild(ifr2);
                    body.appendChild(wrap2);
                }
            }

            overlay.style.display = 'flex';
            document.body.style.overflow = 'hidden';
            var carousel = document.getElementById('o-carousel-product');
            if (carousel) { carousel.setAttribute('data-bs-touch', 'false'); carousel.style.touchAction = 'none'; }

            // ESC key close
            document.addEventListener('keydown', function escClose(e) {
                if (e.key === 'Escape') {
                    UellowVideoModal.close();
                    document.removeEventListener('keydown', escClose);
                }
            });
        },

        close: function() {
            var overlay = document.getElementById('uellowVideoModal');
            var body = document.getElementById('uellowVideoModalBody');
            if (overlay) overlay.style.display = 'none';
            if (body) body.innerHTML = '';
            document.body.style.overflow = '';
            var carousel = document.getElementById('o-carousel-product');
            if (carousel) { carousel.setAttribute('data-bs-touch', 'true'); carousel.style.touchAction = ''; }
        }
    };
})();
