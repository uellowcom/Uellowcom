/**
 * Uellow Reviewers — reviewers.js
 * Handles reviewer widget on product page + live chat panel
 */

(function () {
    'use strict';

    // ── Helpers ───────────────────────────────────────────────────────────────

    function post(url, params) {
        return fetch(url, {
            method:  'POST',
            headers: {'Content-Type': 'application/json'},
            body:    JSON.stringify({jsonrpc: '2.0', method: 'call', id: 1, params}),
        }).then(r => r.json()).then(d => d.result || {});
    }

    function stars(rating, max = 5) {
        let html = '';
        for (let i = 1; i <= max; i++) {
            html += i <= Math.round(rating) ? '★' : '☆';
        }
        return html;
    }

    function badgeClass(level) {
        const map = {elite:'elite', expert:'expert', regular:'regular', starter:'starter'};
        return map[level] || 'starter';
    }

    function getProductId() {
        // Try data attribute first
        const el = document.querySelector('#beena-reviewer-widget');
        if (el && el.dataset.productId) return el.dataset.productId;

        // Fallback: extract from URL /shop/product/name-123
        const match = location.pathname.match(/\/shop\/product\/[^/]+-?(\d+)\/?$/);
        if (match) return match[1];

        // Fallback: try page meta or form inputs
        const input = document.querySelector('input[name="product_id"]');
        if (input) return input.value;

        const productEl = document.querySelector('[data-product-id]');
        if (productEl) return productEl.dataset.productId;

        return null;
    }

    // ── State ─────────────────────────────────────────────────────────────────

    let reviewers       = [];
    let selectedId      = null;
    let sessionType     = 'written';
    let activeRequest   = null;  // {id, token, type}
    let chatTimer       = null;
    let timerSeconds    = 0;
    let settings        = {};
    let pollInterval    = null;

    // ── Init ──────────────────────────────────────────────────────────────────

    async function init() {
        // Only run on product pages
        const isProductPage = location.pathname.includes('/shop/product/') ||
                              document.querySelector('.js_product, #product_detail, .product_detail');
        if (!isProductPage) return;

        // Create widget div if not injected by template
        let widget = document.getElementById('beena-reviewer-widget');
        if (!widget) {
            // Theme Prime + standard Odoo selectors
            const anchors = [
                '.product_description_short',
                '#product_details',
                '.js_product',
                '.o_wsale_product_information',
                '#product-summary',
                '.product_detail',
                '.product_detail_extra',
                '.product_info',
                // Theme Prime specific
                '.pp-product-info',
                '.pp_product_detail',
                '.product-info-main',
                '.product-social-links',
                '[data-snippet="product_detail"]',
                // Last resort: add to cart area
                '#add_to_cart',
                '.a-buy',
            ];

            let anchor = null;
            for (const sel of anchors) {
                anchor = document.querySelector(sel);
                if (anchor) break;
            }

            if (!anchor) {
                // Absolute last resort: find product title area
                anchor = document.querySelector('h1, .product_name');
            }
            if (!anchor) return;

            widget = document.createElement('div');
            widget.id = 'beena-reviewer-widget';
            widget.style.cssText = 'margin-top:20px;margin-bottom:10px;';

            // Insert after the anchor's parent section
            const insertAfter = anchor.closest('.row, .container, section') || anchor;
            insertAfter.parentNode.insertBefore(widget, insertAfter.nextSibling);
        }

        const productId = getProductId();
        const data      = await post('/reviewers/online', {product_id: productId, limit: 8});

        if (!data.enabled) return;

        settings  = data.settings || {};
        reviewers = data.reviewers || [];

        renderWidget(widget, productId);
    }

    // ── Render Widget ─────────────────────────────────────────────────────────

    function renderWidget(container, productId) {
        container.innerHTML = `
<div style="margin-top:24px;border-top:1px solid rgba(0,0,0,.07);padding-top:18px">
  <div class="rv-section-title">
    👥 اطلب رأي متخصص
    <span style="font-size:11px;color:#1D9E75;font-weight:400">${reviewers.filter(r=>r.is_online).length} أونلاين الآن</span>
  </div>

  <div class="rv-list" id="rv-list"></div>

  <div id="rv-type-section" style="display:none">
    <div style="font-size:13px;font-weight:600;color:#1A1A1A;margin-bottom:8px">اختر نوع الاستشارة</div>
    <div class="rv-type-grid" id="rv-type-grid"></div>
    <button class="rv-cta-btn" id="rv-start-btn" onclick="window._rvStartSession()">ابدأ الاستشارة</button>
  </div>
</div>`;

        renderReviewerList();
    }

    function renderReviewerList() {
        const list = document.getElementById('rv-list');
        if (!list) return;

        if (!reviewers.length) {
            list.innerHTML = '<div style="text-align:center;color:#888;font-size:12px;padding:12px 0">لا يوجد ريفيورز متاحون حالياً</div>';
            return;
        }

        list.innerHTML = reviewers.map(r => `
<div class="rv-card${r.id === selectedId ? ' selected' : ''}"
     onclick="window._rvSelectReviewer(${r.id})">
  <div class="rv-avatar">
    ${r.avatar_url
        ? `<img src="${r.avatar_url}" style="width:46px;height:46px;border-radius:50%;object-fit:cover">`
        : r.name.charAt(0)}
    <div class="rv-online-dot ${r.is_online ? 'online' : 'offline'}"></div>
  </div>
  <div class="rv-info">
    <div class="rv-name">
      ${r.name}
      <span class="rv-badge ${badgeClass(r.level)}">${r.level_label}</span>
      ${r.verified_purchase ? '<span style="font-size:10px;color:#1D9E75">✓ مشترٍ معتمد</span>' : ''}
    </div>
    <div class="rv-specs">
      ${r.specialties.map(s => `<span class="rv-spec-tag">${s}</span>`).join('')}
      ${r.specialty_text ? `<span class="rv-spec-tag">${r.specialty_text}</span>` : ''}
    </div>
    <div class="rv-stars">${stars(r.rating)} <span>${r.rating} · ${r.review_count} مراجعة</span></div>
    ${r.bio ? `<div class="rv-bio">${r.bio}</div>` : ''}
    ${r.is_online
        ? `<div class="rv-price">
            ${r.allow_written ? `رأي مكتوب: ${r.price_written.toFixed(3)} KD` : ''}
            ${r.allow_chat    ? ` · شات: ${r.price_chat.toFixed(3)} KD` : ''}
           </div>`
        : `<div class="rv-offline-label">غير متصل الآن</div>`}
  </div>
</div>`).join('');
    }

    // ── Select Reviewer ───────────────────────────────────────────────────────

    window._rvSelectReviewer = function(id) {
        selectedId = id;
        renderReviewerList();

        const reviewer     = reviewers.find(r => r.id === id);
        const typeSection  = document.getElementById('rv-type-section');
        const typeGrid     = document.getElementById('rv-type-grid');
        if (!typeSection || !reviewer) return;

        if (!reviewer.is_online) {
            typeSection.style.display = 'none';
            return;
        }

        typeSection.style.display = 'block';

        const types = [
            { key: 'written', icon: '✍️', name: 'رأي مكتوب',   time: '~5 دقائق',  allowed: reviewer.allow_written && settings.allow_written },
            { key: 'chat',    icon: '💬', name: 'شات مباشر',   time: '~10 دقائق', allowed: reviewer.allow_chat    && settings.allow_chat },
            { key: 'photo',   icon: '📸', name: 'صورة + رأي',  time: '~7 دقائق',  allowed: reviewer.allow_photo   && settings.allow_photo },
            { key: 'video',   icon: '🎥', name: 'فيديو',       time: '~15 دقيقة', allowed: reviewer.allow_video   && settings.allow_video },
        ].filter(t => t.allowed);

        if (!types.length) {
            typeSection.style.display = 'none';
            return;
        }

        sessionType = types[0].key;

        typeGrid.innerHTML = types.map(t => `
<button class="rv-type-btn${t.key === sessionType ? ' active' : ''}"
        onclick="window._rvSelectType('${t.key}')">
  <div class="rv-type-icon">${t.icon}</div>
  <div class="rv-type-name">${t.name}</div>
  <div class="rv-type-time">${t.time}</div>
</button>`).join('');
    };

    window._rvSelectType = function(type) {
        sessionType = type;
        document.querySelectorAll('.rv-type-btn').forEach(b => {
            b.classList.toggle('active', b.textContent.includes(
                {written:'مكتوب', chat:'شات', photo:'صورة', video:'فيديو'}[type] || ''
            ));
        });
    };

    // ── Start Session ─────────────────────────────────────────────────────────

    window._rvStartSession = async function() {
        if (!selectedId) return;
        const btn = document.getElementById('rv-start-btn');
        if (btn) { btn.disabled = true; btn.textContent = 'جاري الإرسال...'; }

        const productId = getProductId();
        const result    = await post('/reviewers/request', {
            reviewer_id:  selectedId,
            product_id:   productId,
            session_type: sessionType,
        });

        if (btn) { btn.disabled = false; btn.textContent = 'ابدأ الاستشارة'; }

        if (result.error) {
            alert('خطأ: ' + result.error);
            return;
        }

        activeRequest = {
            id:    result.request_id,
            token: result.token,
            type:  sessionType,
            fee:   result.fee,
        };

        openChatPanel();
        startPolling();
    };

    // ── Chat Panel ────────────────────────────────────────────────────────────

    function openChatPanel() {
        closeChatPanel();

        const reviewer = reviewers.find(r => r.id === selectedId);
        if (!reviewer) return;

        const panel = document.createElement('div');
        panel.id    = 'rv-chat-panel';
        panel.innerHTML = `
<div class="rv-chat-hdr">
  <div class="rv-chat-hdr-ava">${reviewer.name.charAt(0)}</div>
  <div style="flex:1">
    <div class="rv-chat-name">${reviewer.name}</div>
    <div class="rv-chat-status" id="rv-status">بانتظار القبول...</div>
  </div>
  <div class="rv-timer" id="rv-timer" style="display:none">00:00</div>
  <button onclick="window._rvCloseChat()"
          style="background:none;border:none;font-size:20px;cursor:pointer;color:#1A1A1A;opacity:.6;padding:0">×</button>
</div>
<div class="rv-messages" id="rv-messages">
  <div style="text-align:center;color:#888;font-size:12px;padding:16px 0">
    <div class="rv-loading"><span></span><span></span><span></span></div>
    بانتظار قبول الريفيور طلبك...
  </div>
</div>
<div class="rv-input-row" id="rv-input-row" style="display:none">
  <input class="rv-input" id="rv-input" placeholder="اكتب رسالتك..." dir="auto"
         onkeydown="if(event.key==='Enter')window._rvSendMsg()">
  <button class="rv-send" onclick="window._rvSendMsg()">➤</button>
</div>`;

        document.body.appendChild(panel);
    }

    function closeChatPanel() {
        const old = document.getElementById('rv-chat-panel');
        if (old) old.remove();
        stopPolling();
        stopTimer();
    }

    window._rvCloseChat = function() {
        closeChatPanel();
        activeRequest = null;
    };

    // ── Polling for session updates ───────────────────────────────────────────

    function startPolling() {
        pollInterval = setInterval(async () => {
            if (!activeRequest) { stopPolling(); return; }

            const data = await post(
                `/reviewers/request/${activeRequest.token}`, {}
            );
            const req = data.request;
            if (!req) return;

            updateChatPanel(req);

            if (req.state === 'completed' || req.state === 'expired' || req.state === 'cancelled') {
                stopPolling();
            }
        }, 3000);
    }

    function stopPolling() {
        if (pollInterval) { clearInterval(pollInterval); pollInterval = null; }
    }

    function updateChatPanel(req) {
        const statusEl   = document.getElementById('rv-status');
        const messagesEl = document.getElementById('rv-messages');
        const inputRow   = document.getElementById('rv-input-row');

        const stateMap = {
            pending:   'بانتظار القبول...',
            accepted:  'قبل الطلب — الجلسة ستبدأ الآن',
            active:    'الجلسة نشطة',
            completed: 'اكتملت الجلسة',
            expired:   'انتهت صلاحية الطلب',
            cancelled: 'تم الإلغاء',
        };

        if (statusEl) statusEl.textContent = stateMap[req.state] || req.state;

        if (req.state === 'accepted' || req.state === 'active') {
            if (inputRow) inputRow.style.display = 'flex';
            if (req.state === 'active' && !chatTimer) startTimer();
        }

        if (req.state === 'completed') {
            if (inputRow) inputRow.style.display = 'none';
            stopTimer();
        }

        // Render messages
        if (messagesEl && req.messages && req.messages.length) {
            messagesEl.innerHTML = req.messages.map(m => `
<div class="rv-msg-${m.sender === 'customer' ? 'customer' : 'reviewer'}">
  ${m.text}
</div>`).join('');
            messagesEl.scrollTop = messagesEl.scrollHeight;
        }

        // Show verdict if completed
        if (req.state === 'completed' && req.verdict && messagesEl) {
            const verdictEl = document.createElement('div');
            verdictEl.className = `rv-verdict ${req.verdict}`;
            const labels = {
                recommend:     '✓ أنصح بالشراء',
                not_recommend: '✗ لا أنصح بالشراء',
                neutral:       '◉ محايد',
            };
            verdictEl.innerHTML = `
<div class="rv-verdict-title">${labels[req.verdict] || req.verdict}</div>
${req.notes ? `<div class="rv-verdict-sub">${req.notes}</div>` : ''}`;
            messagesEl.appendChild(verdictEl);

            // Show rating prompt
            showRatingPrompt(req.token, messagesEl);
        }
    }

    function showRatingPrompt(token, container) {
        const ratingDiv = document.createElement('div');
        ratingDiv.innerHTML = `
<div style="text-align:center;padding:10px 0;border-top:1px solid rgba(0,0,0,.07);margin-top:8px">
  <div style="font-size:12px;font-weight:600;color:#1A1A1A;margin-bottom:6px">قيّم الريفيور</div>
  <div class="rv-star-rating" id="rv-star-rating">
    ${[1,2,3,4,5].map(i => `<button onclick="window._rvSetRating(${i})" data-val="${i}">★</button>`).join('')}
  </div>
  <button onclick="window._rvSubmitRating('${token}')"
          style="background:var(--rv-yellow);border:none;border-radius:8px;padding:6px 18px;font-size:12px;font-weight:700;cursor:pointer;margin-top:6px;font-family:inherit">
    إرسال التقييم
  </button>
</div>`;
        container.appendChild(ratingDiv);
        window._currentRating = 5;

        // Highlight 5 stars by default
        document.querySelectorAll('#rv-star-rating button').forEach((b, i) => {
            b.classList.toggle('active', i < 5);
        });
    }

    window._rvSetRating = function(val) {
        window._currentRating = val;
        document.querySelectorAll('#rv-star-rating button').forEach((b, i) => {
            b.classList.toggle('active', i < val);
        });
    };

    window._rvSubmitRating = async function(token) {
        await post('/reviewers/rate', {
            token:  token,
            rating: window._currentRating || 5,
        });
        const ratingDiv = document.querySelector('#rv-chat-panel .rv-star-rating');
        if (ratingDiv) ratingDiv.closest('div').innerHTML = '<div style="color:#1D9E75;font-size:12px;text-align:center;padding:8px">شكراً على تقييمك! 🐝</div>';
    };

    // ── Send Message ──────────────────────────────────────────────────────────

    window._rvSendMsg = async function() {
        const input = document.getElementById('rv-input');
        const text  = (input ? input.value : '').trim();
        if (!text || !activeRequest) return;
        input.value = '';

        const messagesEl = document.getElementById('rv-messages');
        if (messagesEl) {
            const div = document.createElement('div');
            div.className   = 'rv-msg-customer';
            div.textContent = text;
            messagesEl.appendChild(div);
            messagesEl.scrollTop = messagesEl.scrollHeight;
        }

        await post('/reviewers/message', {
            token:  activeRequest.token,
            text,
            sender: 'customer',
        });
    };

    // ── Timer ─────────────────────────────────────────────────────────────────

    function startTimer() {
        const duration = (settings.chat_duration || 15) * 60;
        timerSeconds   = duration;
        const timerEl  = document.getElementById('rv-timer');
        if (timerEl) timerEl.style.display = 'block';

        chatTimer = setInterval(() => {
            timerSeconds--;
            const m = String(Math.floor(timerSeconds / 60)).padStart(2, '0');
            const s = String(timerSeconds % 60).padStart(2, '0');
            if (timerEl) timerEl.textContent = `${m}:${s}`;

            if (timerSeconds <= 0) {
                stopTimer();
                if (timerEl) timerEl.textContent = '00:00';
                if (timerEl) timerEl.style.background = 'rgba(226,75,74,.2)';
            }
        }, 1000);
    }

    function stopTimer() {
        if (chatTimer) { clearInterval(chatTimer); chatTimer = null; }
    }

    // ── Boot ──────────────────────────────────────────────────────────────────

    // Only run on shop/product pages
    function shouldRunReviewer() {
        const path = location.pathname;
        if (path.startsWith('/odoo') || path.startsWith('/web')) return false;
        if (path.startsWith('/reviewer')) return false;
        if (path.includes('/shop') || path.includes('/product')) return true;
        return false;
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => { if (shouldRunReviewer()) init(); });
    } else {
        if (shouldRunReviewer()) init();
    }

})();
