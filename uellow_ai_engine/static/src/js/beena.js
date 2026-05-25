/**
 * Uellow AI Engine — Beena.js
 * Phase 1: Chat UI + Claude API + Streaming + Animated Avatar
 */

(function () {
    'use strict';

    // ── SVG Generator ─────────────────────────────────────────────────────────
    // Draws Beena matching the Uellow logo bee precisely

    function beenaSVG(size) {
        const s  = size || 44;
        const cx = s / 2;
        const cy = s * 0.52;
        const hcy = cy - s * 0.32;

        return `<svg viewBox="0 0 ${s} ${s * 1.05}" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <!-- Wings -->
  <ellipse class="beena-wing"
    cx="${cx - s * .22}" cy="${hcy - s * .02}"
    rx="${s * .17}" ry="${s * .44}"
    fill="#D8E8F5" stroke="#A8C8E8" stroke-width="${s * .01}"
    opacity=".92" style="transform-origin:${cx - s * .22}px ${hcy}px"/>
  <ellipse class="beena-wing"
    cx="${cx + s * .22}" cy="${hcy - s * .02}"
    rx="${s * .17}" ry="${s * .44}"
    fill="#D8E8F5" stroke="#A8C8E8" stroke-width="${s * .01}"
    opacity=".92" style="transform-origin:${cx + s * .22}px ${hcy}px"/>

  <!-- Body -->
  <ellipse cx="${cx}" cy="${cy + s * .06}" rx="${s * .38}" ry="${s * .44}" fill="#F5C320" stroke="#C8980A" stroke-width="${s * .013}"/>
  <rect x="${cx - s * .32}" y="${cy - s * .04}" width="${s * .64}" height="${s * .1}" rx="${s * .05}" fill="#1A1A1A"/>
  <rect x="${cx - s * .32}" y="${cy + s * .1}" width="${s * .64}" height="${s * .1}" rx="${s * .05}" fill="#1A1A1A"/>
  <rect x="${cx - s * .32}" y="${cy + s * .24}" width="${s * .64}" height="${s * .1}" rx="${s * .05}" fill="#1A1A1A"/>

  <!-- Head -->
  <ellipse cx="${cx}" cy="${hcy}" rx="${s * .42}" ry="${s * .4}" fill="#F5C320" stroke="#C8980A" stroke-width="${s * .013}"/>

  <!-- Glasses frame bridge -->
  <rect x="${cx - s * .14}" y="${hcy - s * .09}" width="${s * .285}" height="${s * .03}" fill="#1A1A1A"/>

  <!-- Left lens -->
  <circle cx="${cx - s * .14}" cy="${hcy}" r="${s * .165}" fill="white" stroke="#1A1A1A" stroke-width="${s * .016}"/>
  <!-- Right lens -->
  <circle cx="${cx + s * .14}" cy="${hcy}" r="${s * .165}" fill="white" stroke="#1A1A1A" stroke-width="${s * .016}"/>
  <!-- Bridge fill -->
  <rect x="${cx - s * .15}" y="${hcy - s * .09}" width="${s * .3}" height="${s * .11}" fill="white"/>

  <!-- Pupils -->
  <circle cx="${cx - s * .14}" cy="${hcy + s * .01}" r="${s * .09}" fill="#1A1A1A"/>
  <circle cx="${cx + s * .14}" cy="${hcy + s * .01}" r="${s * .09}" fill="#1A1A1A"/>
  <!-- Shines -->
  <circle cx="${cx - s * .11}" cy="${hcy - s * .02}" r="${s * .035}" fill="white"/>
  <circle cx="${cx + s * .17}" cy="${hcy - s * .02}" r="${s * .035}" fill="white"/>

  <!-- Cheeks -->
  <circle cx="${cx - s * .12}" cy="${hcy + s * .1}" r="${s * .04}" fill="#F5A0A0"/>
  <circle cx="${cx + s * .12}" cy="${hcy + s * .1}" r="${s * .04}" fill="#F5A0A0"/>

  <!-- Antennas -->
  <path d="M${cx - s * .08} ${hcy - s * .38} Q${cx - s * .14} ${hcy - s * .56} ${cx - s * .24} ${hcy - s * .64}"
    fill="none" stroke="#1A1A1A" stroke-width="${s * .018}" stroke-linecap="round"/>
  <path d="M${cx + s * .08} ${hcy - s * .38} Q${cx + s * .14} ${hcy - s * .56} ${cx + s * .24} ${hcy - s * .64}"
    fill="none" stroke="#1A1A1A" stroke-width="${s * .018}" stroke-linecap="round"/>
  <circle cx="${cx - s * .26}" cy="${hcy - s * .66}" r="${s * .038}" fill="#1A1A1A"/>
  <circle cx="${cx + s * .26}" cy="${hcy - s * .66}" r="${s * .038}" fill="#1A1A1A"/>
  <circle cx="${cx - s * .24}" cy="${hcy - s * .72}" r="${s * .022}" fill="#F5C320" stroke="#1A1A1A" stroke-width="${s * .01}"/>
  <circle cx="${cx + s * .24}" cy="${hcy - s * .72}" r="${s * .022}" fill="#F5C320" stroke="#1A1A1A" stroke-width="${s * .01}"/>

  <!-- Feet -->
  <path d="M${cx - s * .28} ${cy + s * .36} Q${cx - s * .32} ${cy + s * .44} ${cx - s * .34} ${cy + s * .5}"
    fill="none" stroke="#1A1A1A" stroke-width="${s * .016}" stroke-linecap="round"/>
  <path d="M${cx + s * .28} ${cy + s * .36} Q${cx + s * .32} ${cy + s * .44} ${cx + s * .34} ${cy + s * .5}"
    fill="none" stroke="#1A1A1A" stroke-width="${s * .016}" stroke-linecap="round"/>
  <ellipse cx="${cx - s * .35}" cy="${cy + s * .53}" rx="${s * .055}" ry="${s * .038}" fill="#F5C320" stroke="#C8980A" stroke-width="${s * .01}"/>
  <ellipse cx="${cx + s * .35}" cy="${cy + s * .53}" rx="${s * .055}" ry="${s * .038}" fill="#F5C320" stroke="#C8980A" stroke-width="${s * .01}"/>

  <!-- State expression layer (mouth + extras) -->
  <g class="beena-expression"></g>

  <!-- Sparkles for happy/excited -->
  <circle class="beena-sparkle" cx="${cx - s * .44}" cy="${hcy - s * .15}" r="${s * .04}" fill="#F5C320" opacity="0"/>
  <circle class="beena-sparkle" cx="${cx + s * .44}" cy="${hcy - s * .15}" r="${s * .04}" fill="#F5C320" opacity="0"/>

  <!-- Question mark for thinking -->
  <text class="beena-question" x="${cx + s * .3}" y="${hcy - s * .08}"
    font-size="${s * .16}" fill="#C8980A" opacity="0" font-family="inherit">?</text>
</svg>`;
    }

    // State → mouth path + brows
    const STATE_EXPRESSIONS = {
        idle:     (s, cx, hcy) => `<path d="M${cx - s*.09} ${hcy + s*.13} Q${cx} ${hcy + s*.18} ${cx + s*.09} ${hcy + s*.13}" fill="none" stroke="#C8980A" stroke-width="${s*.018}" stroke-linecap="round"/>`,
        talking:  (s, cx, hcy) => `
            <ellipse cx="${cx}" cy="${hcy + s*.14}" rx="${s*.07}" ry="${s*.04}" fill="#C8980A" opacity=".8"/>
            <path d="M${cx - s*.1} ${hcy - s*.12} Q${cx - s*.06} ${hcy - s*.15} ${cx} ${hcy - s*.12}" fill="none" stroke="#1A1A1A" stroke-width="${s*.015}" stroke-linecap="round"/>
            <path d="M${cx} ${hcy - s*.12} Q${cx + s*.06} ${hcy - s*.15} ${cx + s*.1} ${hcy - s*.12}" fill="none" stroke="#1A1A1A" stroke-width="${s*.015}" stroke-linecap="round"/>`,
        thinking: (s, cx, hcy) => `
            <path d="M${cx - s*.08} ${hcy + s*.14} Q${cx} ${hcy + s*.15} ${cx + s*.08} ${hcy + s*.14}" fill="none" stroke="#C8980A" stroke-width="${s*.016}" stroke-linecap="round"/>
            <path d="M${cx - s*.1} ${hcy - s*.13} Q${cx - s*.05} ${hcy - s*.1} ${cx} ${hcy - s*.13}" fill="none" stroke="#1A1A1A" stroke-width="${s*.015}" stroke-linecap="round"/>
            <path d="M${cx} ${hcy - s*.11} L${cx + s*.1} ${hcy - s*.13}" fill="none" stroke="#1A1A1A" stroke-width="${s*.015}" stroke-linecap="round"/>`,
        happy:    (s, cx, hcy) => `
            <path d="M${cx - s*.11} ${hcy + s*.11} Q${cx} ${hcy + s*.21} ${cx + s*.11} ${hcy + s*.11}" fill="none" stroke="#C8980A" stroke-width="${s*.022}" stroke-linecap="round"/>
            <path d="M${cx - s*.12} ${hcy - s*.14} Q${cx - s*.07} ${hcy - s*.17} ${cx - s*.02} ${hcy - s*.14}" fill="none" stroke="#1A1A1A" stroke-width="${s*.018}" stroke-linecap="round"/>
            <path d="M${cx + s*.02} ${hcy - s*.14} Q${cx + s*.07} ${hcy - s*.17} ${cx + s*.12} ${hcy - s*.14}" fill="none" stroke="#1A1A1A" stroke-width="${s*.018}" stroke-linecap="round"/>`,
        excited:  (s, cx, hcy) => `
            <path d="M${cx - s*.12} ${hcy + s*.1} Q${cx} ${hcy + s*.22} ${cx + s*.12} ${hcy + s*.1}" fill="none" stroke="#C8980A" stroke-width="${s*.025}" stroke-linecap="round"/>
            <path d="M${cx - s*.13} ${hcy - s*.16} Q${cx - s*.07} ${hcy - s*.2} ${cx - s*.01} ${hcy - s*.15}" fill="none" stroke="#1A1A1A" stroke-width="${s*.02}" stroke-linecap="round"/>
            <path d="M${cx + s*.01} ${hcy - s*.15} Q${cx + s*.07} ${hcy - s*.2} ${cx + s*.13} ${hcy - s*.16}" fill="none" stroke="#1A1A1A" stroke-width="${s*.02}" stroke-linecap="round"/>`,
        sad:      (s, cx, hcy) => `
            <path d="M${cx - s*.09} ${hcy + s*.17} Q${cx} ${hcy + s*.12} ${cx + s*.09} ${hcy + s*.17}" fill="none" stroke="#C8980A" stroke-width="${s*.018}" stroke-linecap="round"/>
            <path d="M${cx - s*.1} ${hcy - s*.1} Q${cx - s*.06} ${hcy - s*.14} ${cx} ${hcy - s*.11}" fill="none" stroke="#1A1A1A" stroke-width="${s*.018}" stroke-linecap="round"/>
            <path d="M${cx} ${hcy - s*.11} Q${cx + s*.06} ${hcy - s*.14} ${cx + s*.1} ${hcy - s*.1}" fill="none" stroke="#1A1A1A" stroke-width="${s*.018}" stroke-linecap="round"/>`,
    };

    // ── Session ID ────────────────────────────────────────────────────────────

    function getSessionId() {
        let sid = localStorage.getItem('beena_session');
        if (!sid) {
            sid = 'bs_' + Date.now() + '_' + Math.random().toString(36).slice(2, 8);
            localStorage.setItem('beena_session', sid);
        }
        return sid;
    }

    // ── Chat History Persistence ──────────────────────────────────────────────
    const HISTORY_KEY = 'beena_chat_history';
    const MAX_HISTORY = 30; // max messages to persist

    function saveHistory(msgs) {
        try {
            localStorage.setItem(HISTORY_KEY, JSON.stringify(msgs.slice(-MAX_HISTORY)));
        } catch(e) {}
    }

    function loadHistory() {
        try {
            const raw = localStorage.getItem(HISTORY_KEY);
            return raw ? JSON.parse(raw) : [];
        } catch(e) { return []; }
    }

    function clearHistory() {
        localStorage.removeItem(HISTORY_KEY);
        localStorage.removeItem('beena_session');
    }

    // ── State Labels ──────────────────────────────────────────────────────────

    const STATE_LABELS = {
        idle:     { ar: 'جاهزة', en: 'Ready' },
        talking:  { ar: 'تتكلم', en: 'Typing...' },
        thinking: { ar: 'تفكر...', en: 'Thinking...' },
        happy:    { ar: 'سعيدة', en: 'Happy' },
        excited:  { ar: 'متحمسة', en: 'Excited!' },
        sad:      { ar: 'آسفة', en: 'Sorry' },
    };

    // ── Beena App ─────────────────────────────────────────────────────────────

    class BeenaApp {
        constructor(config) {
            this.config    = config;
            this.sessionId = getSessionId();
            this.isOpen    = false;
            this.state     = 'idle';
            this.nudgeTimer = null;
            this.productId  = null;
            this.lang       = document.documentElement.lang || 'ar';
            this._msgHistory = []; // in-memory mirror for saving

            this._buildUI();
            this._bindEvents();
            this._startNudgeTimer();
            this._applyColors();
        }

        // ── Build HTML ─────────────────────────────────────────────────────────

        _buildUI() {
            const color = this.config.button_color || '#F5C320';

            // Float button
            const floatEl = document.createElement('div');
            floatEl.id    = 'beena-float';
            floatEl.innerHTML = `
                <div id="beena-float-btn" role="button" aria-label="فتح مساعد Uellow" tabindex="0">
                    <div class="beena-body-group beena-state-idle" style="width:38px;height:38px">
                        ${beenaSVG(38)}
                    </div>
                    <div id="beena-badge">1</div>
                </div>
                <div id="beena-float-label">${this.config.name || 'Beena'}</div>`;

            // Chat dialog
            const chatEl = document.createElement('div');
            chatEl.id    = 'beena-chat';
            chatEl.setAttribute('role', 'dialog');
            chatEl.setAttribute('aria-label', `${this.config.name || 'Beena'} AI Chat`);
            chatEl.innerHTML = `
                <div id="beena-header">
                    <div id="beena-avatar-wrap">
                        <div class="beena-body-group beena-state-idle">
                            ${beenaSVG(40)}
                        </div>
                    </div>
                    <div id="beena-header-info">
                        <div id="beena-header-name">${this.config.name || 'Beena'}</div>
                        <div id="beena-header-status">
                            <span id="beena-status-dot"></span>
                            <span id="beena-status-text">${this.config.subtitle || ''}</span>
                        </div>
                    </div>
                    <button id="beena-close" aria-label="إغلاق">×</button>
                </div>
                <div id="beena-context" style="display:none"></div>
                <div id="beena-messages" role="log" aria-live="polite"></div>
                <div id="beena-input-row">
                    <button id="beena-cam-btn" title="بحث بالصورة" aria-label="رفع صورة">📷</button>
                    <button id="beena-voice-btn" title="تحدث بالصوت" aria-label="صوت">🎤</button>
                    <input id="beena-input" type="text" placeholder="${this.lang === 'ar' ? 'اسألي Beena...' : 'Ask Beena...'}" autocomplete="off" dir="auto"/>
                    <button id="beena-send-btn" aria-label="إرسال">➤</button>
                </div>`;

            document.body.appendChild(floatEl);
            document.body.appendChild(chatEl);

            this.floatEl    = floatEl;
            this.chatEl     = chatEl;
            this.messagesEl = document.getElementById('beena-messages');
            this.inputEl    = document.getElementById('beena-input');
            this.contextEl  = document.getElementById('beena-context');
        }

        _applyColors() {
            const c = this.config.button_color || '#F5C320';
            document.documentElement.style.setProperty('--beena-yellow', c);
        }

        // ── Events ─────────────────────────────────────────────────────────────

        _bindEvents() {
            document.getElementById('beena-float-btn').addEventListener('click', () => this.toggle());
            document.getElementById('beena-close').addEventListener('click', () => this.close());

            document.getElementById('beena-send-btn').addEventListener('click', () => this._send());
            this.inputEl.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); this._send(); }
            });

            document.getElementById('beena-cam-btn').addEventListener('click', () => this._openImageSearch());
            document.getElementById('beena-voice-btn').addEventListener('click', () => this._toggleVoice());

            // Close on outside click
            document.addEventListener('click', (e) => {
                if (this.isOpen && !this.chatEl.contains(e.target) && !this.floatEl.contains(e.target)) {
                    this.close();
                }
            });

            // Keyboard
            document.getElementById('beena-float-btn').addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') this.toggle();
            });
        }

        // ── Open / Close ───────────────────────────────────────────────────────

        toggle() {
            this.isOpen ? this.close() : this.open();
        }

        open(productId) {
            if (productId) this.productId = productId;
            this.isOpen = true;
            this.chatEl.classList.add('open');
            clearTimeout(this.nudgeTimer);
            this.floatEl.classList.remove('nudge');

            if (this.messagesEl.children.length === 0) {
                const history = loadHistory();
                if (history.length > 0) {
                    // Show history divider only if there IS history
                    this._restoreHistory(history);
                } else {
                    this._showWelcome();
                    // Check birthday bonus
                    this._checkBirthday();
                }
            }

            if (this.productId) {
                this._showProductContext(this.productId);
            }

            setTimeout(() => this.inputEl.focus(), 300);
        }

        close() {
            this.isOpen = false;
            this.chatEl.classList.remove('open');
            this._startNudgeTimer();
        }

        // ── Product Context Bar ────────────────────────────────────────────────

        _showProductContext(pid) {
            const productName  = document.querySelector('.product_name, h1.product-name, [itemprop="name"]');
            const productPrice = document.querySelector('.oe_price .oe_currency_value, .product-price .currency_value');

            if (!productName) return;

            this.contextEl.innerHTML = `
                <img id="beena-context-img"
                     src="/web/image/product.template/${pid}/image_128"
                     alt="${productName.textContent.trim()}"
                     onerror="this.style.display='none'">
                <div>
                    <div id="beena-context-name">${productName.textContent.trim()}</div>
                    <div id="beena-context-price">${productPrice ? productPrice.textContent.trim() + ' KD' : ''}</div>
                </div>`;
            this.contextEl.style.display = 'flex';
        }

        // ── Welcome ────────────────────────────────────────────────────────────

        _showWelcome() {
            // Try to get customer name from page
            const nameEl = document.querySelector('.o_account_name, .o_portal_name, [data-customer-name]');
            const customerName = nameEl ? nameEl.textContent.trim().split(' ')[0] : '';
            const greeting = customerName
                ? `أهلاً ${customerName}! أنا Beena 🐝 كيف أقدر أساعدك؟`
                : (this.config.welcome || 'أهلاً! أنا Beena 🐝 كيف أقدر أساعدك اليوم؟');
            const chips   = this.productId
                ? ['مواصفات المنتج', 'هل متوفر؟', 'اشتري الآن', 'قيّم هذا المنتج']
                : ['ابحث عن منتج', 'طلباتي', 'نقاطي', 'ادعو صديق', 'تواصل معنا'];

            this._addAIMessage(greeting, 'idle', chips);
        }

        // ── Restore History ───────────────────────────────────────────────────────

        _restoreHistory(history) {
            if (!history || !history.length) return;
            const indicator = document.createElement('div');
            indicator.style.cssText = 'text-align:center;font-size:10px;color:#aaa;padding:4px 0 8px;';
            indicator.textContent = '── محادثة سابقة ──';
            this.messagesEl.appendChild(indicator);

            history.forEach(msg => {
                if (msg.type === 'user') {
                    const div     = document.createElement('div');
                    div.className = 'beena-msg beena-msg-user';
                    div.textContent = msg.text;
                    this.messagesEl.appendChild(div);
                } else if (msg.type === 'ai') {
                    const div     = document.createElement('div');
                    div.className = 'beena-msg beena-msg-ai';
                    div.innerHTML = this._formatText(msg.text || '');
                    if (msg.chips && msg.chips.length) {
                        const chipWrap    = document.createElement('div');
                        chipWrap.className = 'beena-chips';
                        msg.chips.forEach(chip => {
                            const btn     = document.createElement('button');
                            btn.className = 'beena-chip';
                            btn.textContent = chip;
                            btn.addEventListener('click', () => this._send(chip));
                            chipWrap.appendChild(btn);
                        });
                        div.appendChild(chipWrap);
                    }
                    this.messagesEl.appendChild(div);
                }
            });

            this._addClearButton();
            this._scrollBottom();
        }

        _addClearButton() {
            const old = document.getElementById('beena-clear-btn');
            if (old) old.remove();
            const wrap = document.createElement('div');
            wrap.id    = 'beena-clear-btn';
            wrap.style.cssText = 'text-align:center;padding:8px 0 2px;';
            const btn  = document.createElement('button');
            btn.textContent = '🗑 مسح المحادثة';
            btn.style.cssText = `
                background:none;border:1px solid #ddd;border-radius:10px;
                padding:3px 12px;font-size:10px;color:#aaa;cursor:pointer;
                font-family:inherit;transition:color .15s;
            `;
            btn.onmouseover = () => btn.style.color = '#E24B4A';
            btn.onmouseout  = () => btn.style.color = '#aaa';
            btn.addEventListener('click', () => {
                clearHistory();
                this._msgHistory = [];
                this.messagesEl.innerHTML = '';
                this._showWelcome();
            });
            wrap.appendChild(btn);
            this.messagesEl.appendChild(wrap);
        }

        // ── Send Message ───────────────────────────────────────────────────────

        async _send(text) {
            const msg = (text || this.inputEl.value).trim();
            if (!msg) return;

            this.inputEl.value = '';
            this._addUserMessage(msg);
            this._showTyping();
            this._setState('thinking');

            try {
                const resp = await fetch('/ai/chat', {
                    method:  'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body:    JSON.stringify({
                        jsonrpc: '2.0',
                        method:  'call',
                        id:      1,
                        params:  {
                            message:    msg,
                            session_id: this.sessionId,
                            product_id: this.productId,
                        },
                    }),
                });

                const data   = await resp.json();
                const result = data.result || {};

                this._removeTyping();

                if (result.error) {
                    this._addAIMessage('عذراً، حدث خطأ. حاول مرة ثانية. 🐝', 'sad');
                    this._setState('sad');
                    return;
                }

                const reply = result.reply || '';
                const state = result.state || 'talking';
                const extra = result.extra || {};

                this._addAIMessage(reply, state);
                this._setState(state);

                // Handle extra UI blocks
                if (extra.order)    this._showOrderCard(extra.order, extra.payment);
                if (extra.products) this._showProductList(extra.products);

                // Reset to idle after 4s
                setTimeout(() => this._setState('idle'), 4000);

            } catch (err) {
                this._removeTyping();
                this._addAIMessage('مشكلة في الاتصال. تأكد من الإنترنت وحاول ثاني. 🐝', 'sad');
                this._setState('sad');
            }
        }

        // ── Image Search ───────────────────────────────────────────────────────

        // ── Birthday + Referral ───────────────────────────────────────────────────────

        async _checkBirthday() {
            try {
                const resp = await fetch('/loyalty/birthday/check', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({jsonrpc:'2.0',method:'call',id:1,params:{}}),
                });
                const data = await resp.json();
                const res  = data.result || {};
                if (res.birthday && !res.already_given && res.points_awarded) {
                    setTimeout(() => {
                        this._addAIMessage(
                            res.message || `🎂 عيد ميلاد سعيد! حصلت على ${res.points_awarded} نقطة هدية منا!`,
                            'excited'
                        );
                        this._setState('excited');
                    }, 1500);
                }
            } catch(e) {}
        }

        // ── Voice Engine ─────────────────────────────────────────────────────────────

        _toggleVoice() {
            this._voiceActive ? this._stopVoice() : this._startVoice();
        }

        _startVoice() {
            const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
            if (!SR) {
                this._addAIMessage('متصفحك لا يدعم الصوت. جرّب Chrome أو Edge.', 'sad');
                return;
            }
            this._recognition = new SR();

            // Auto-detect any language/dialect
            // Empty string or browser default = auto detect all languages
            // We use a broad list covering Arabic dialects + major languages
            this._recognition.lang = '';  // empty = browser decides based on OS language
            this._recognition.continuous     = false;
            this._recognition.interimResults = true;
            this._recognition.maxAlternatives = 3; // try 3 alternatives for better accuracy

            const btn = document.getElementById('beena-voice-btn');

            this._recognition.onstart = () => {
                this._voiceActive = true;
                if (btn) { btn.textContent = '🔴'; btn.style.background = '#FCEBEB'; }
                this.inputEl.placeholder = this.lang === 'ar' ? '🎤 استمع...' : '🎤 Listening...';
                this._setState('thinking');
            };

            this._recognition.onresult = (e) => {
                // Pick the most confident alternative
                let transcript = '';
                let bestConfidence = 0;
                const lastResult = e.results[e.results.length - 1];

                for (let i = 0; i < lastResult.length; i++) {
                    if (lastResult[i].confidence > bestConfidence) {
                        bestConfidence = lastResult[i].confidence;
                        transcript    = lastResult[i].transcript;
                    }
                }

                // Fallback to first if no confidence score
                if (!transcript) {
                    transcript = Array.from(e.results).map(r => r[0].transcript).join('');
                }

                this.inputEl.value = transcript;

                if (lastResult.isFinal) {
                    this._stopVoice();
                    setTimeout(() => { if (this.inputEl.value.trim()) this._send(); }, 400);
                }
            };

            this._recognition.onerror = (e) => {
                this._stopVoice();
                if (e.error !== 'no-speech') {
                    this._addAIMessage('ما سمعت شيء، حاول مرة ثانية.', 'sad');
                }
            };

            this._recognition.onend = () => this._stopVoice();

            try { this._recognition.start(); }
            catch(e) { this._addAIMessage('تعذّر تفعيل الميكروفون. تأكد من الأذونات.', 'sad'); }
        }

        _stopVoice() {
            this._voiceActive = false;
            const btn = document.getElementById('beena-voice-btn');
            if (btn) { btn.textContent = '🎤'; btn.style.background = ''; }
            this.inputEl.placeholder = this.lang === 'ar' ? 'اسألي Beena...' : 'Ask Beena...';
            if (this._recognition) { try { this._recognition.stop(); } catch(e) {} this._recognition = null; }
        }

        // ── Image Search ─────────────────────────────────────────────────────────────

        _openImageSearch() {
            const input  = document.createElement('input');
            input.type   = 'file';
            input.accept = 'image/*';
            input.onchange = async (e) => {
                const file = e.target.files[0];
                if (!file) return;

                // Show image preview in chat
                const reader = new FileReader();
                reader.onload = async (ev) => {
                    const base64 = ev.target.result;

                    // Show thumbnail
                    const msgDiv = document.createElement('div');
                    msgDiv.className = 'beena-msg beena-msg-user';
                    msgDiv.innerHTML = `
                        <img src="${base64}" alt="صورة البحث"
                             style="max-width:140px;max-height:140px;border-radius:8px;display:block;margin-bottom:4px">
                        <span style="font-size:10px;opacity:.8">🔍 جاري البحث بالصورة...</span>`;
                    this.messagesEl.appendChild(msgDiv);
                    this._scrollBottom();
                    this._msgHistory.push({type:'user', text:'[صورة بحث]'});
                    saveHistory(this._msgHistory);

                    // Show thinking
                    this._showTyping();
                    this._setState('thinking');

                    // Send image to Claude via visual search endpoint
                    try {
                        const resp = await fetch('/ai/visual_search', {
                            method:  'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({
                                jsonrpc: '2.0', method: 'call', id: 1,
                                params: {
                                    image_base64: base64,
                                    session_id:   this.sessionId,
                                },
                            }),
                        });
                        const data   = await resp.json();
                        const result = data.result || {};
                        this._removeTyping();

                        if (result.reply) {
                            this._addAIMessage(result.reply, result.state || 'talking');
                            this._setState(result.state || 'talking');
                        }
                        if (result.extra && result.extra.products) {
                            this._showProductList(result.extra.products);
                        }
                    } catch(err) {
                        this._removeTyping();
                        this._addAIMessage('تعذّر البحث بالصورة. حاول مرة ثانية.', 'sad');
                    }
                };
                reader.readAsDataURL(file);
            };
            input.click();
        }

        // ── Message Rendering ──────────────────────────────────────────────────

        _addUserMessage(text) {
            const div       = document.createElement('div');
            div.className   = 'beena-msg beena-msg-user';
            div.textContent = text;
            this.messagesEl.appendChild(div);
            this._scrollBottom();
            // Save to history
            this._msgHistory.push({type: 'user', text});
            saveHistory(this._msgHistory);
        }

        _addAIMessage(text, state, chips) {
            const div     = document.createElement('div');
            div.className = 'beena-msg beena-msg-ai';

            div.innerHTML = this._formatText(text);

            if (chips && chips.length) {
                const chipWrap = document.createElement('div');
                chipWrap.className = 'beena-chips';
                chips.forEach(chip => {
                    const btn       = document.createElement('button');
                    btn.className   = 'beena-chip';
                    btn.textContent = chip;
                    btn.addEventListener('click', () => this._send(chip));
                    chipWrap.appendChild(btn);
                });
                div.appendChild(chipWrap);
            }

            this.messagesEl.appendChild(div);
            this._scrollBottom();
            // Save to history
            this._msgHistory.push({type: 'ai', text, chips: chips || []});
            saveHistory(this._msgHistory);
        }

        _formatText(text) {
            return text
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/\n/g, '<br>');
        }

        _showTyping() {
            const div     = document.createElement('div');
            div.id        = 'beena-typing';
            div.className = 'beena-typing';
            div.innerHTML = '<span></span><span></span><span></span>';
            this.messagesEl.appendChild(div);
            this._scrollBottom();
        }

        _removeTyping() {
            const t = document.getElementById('beena-typing');
            if (t) t.remove();
        }

        _showOrderCard(order, payment) {
            const div     = document.createElement('div');
            div.className = 'beena-msg beena-msg-ai';
            div.innerHTML = `
                <div class="beena-order-card">
                    <div class="beena-order-row"><span>طلب ${order.order_name || ''}</span></div>
                    <div class="beena-order-row"><span>المبلغ</span><span>${(order.amount || 0).toFixed(3)} KD</span></div>
                </div>
                ${payment ? `
                <button class="beena-pay-btn beena-pay-upay" onclick="window.open('${payment.upay_url}', '_blank')">💳 ادفع الآن — UPayments</button>
                <button class="beena-pay-btn beena-pay-taly">📅 قسّط مع Taly — 4 دفعات</button>
                ` : ''}`;
            this.messagesEl.appendChild(div);
            this._scrollBottom();
        }

        _showProductList(products) {
            if (!products || !products.length) return;
            const div     = document.createElement('div');
            div.className = 'beena-msg beena-msg-ai';

            products.slice(0, 5).forEach(p => {
                const card = document.createElement('div');
                card.className = 'beena-product-card';
                const variantId = p.variant_id || p.id;
                const stockBadge = p.in_stock === false
                    ? '<span style="font-size:10px;color:#E24B4A">غير متوفر</span>'
                    : '<span style="font-size:10px;color:#1D9E75">متوفر ✓</span>';
                card.innerHTML = `
                    <img src="${p.image_url || '/web/image/product.template/'+p.id+'/image_128'}"
                         alt="${p.name}" onerror="this.style.display='none'"
                         style="width:44px;height:44px;border-radius:7px;object-fit:cover;flex-shrink:0">
                    <div style="flex:1;min-width:0">
                        <div class="beena-product-name" style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${p.name}</div>
                        <div class="beena-product-price">${(p.price || 0).toFixed(3)} KD</div>
                        ${stockBadge}
                    </div>
                    <div style="display:flex;flex-direction:column;gap:4px;flex-shrink:0">
                        <button class="beena-buy-btn"
                            onclick="window.location.href='/shop/product/${p.id}'"
                            style="font-size:10px;padding:3px 8px">عرض</button>
                        ${p.in_stock !== false ? `<button class="beena-buy-btn"
                            style="font-size:10px;padding:3px 8px;background:#1D9E75"
                            onclick="window._beenaAddToCart(${p.variant_id || p.id}, '${p.name}')">
                            +سلة</button>` : ''}
                    </div>`;
                div.appendChild(card);
            });

            this.messagesEl.appendChild(div);
            this._scrollBottom();
        }

        _scrollBottom() {
            requestAnimationFrame(() => {
                this.messagesEl.scrollTop = this.messagesEl.scrollHeight;
            });
        }

        // ── State Machine ──────────────────────────────────────────────────────

        _setState(state) {
            if (!STATE_LABELS[state]) state = 'idle';
            this.state = state;

            const lang  = this.lang === 'ar' ? 'ar' : 'en';
            const label = STATE_LABELS[state][lang];

            // Update status text
            const statusEl = document.getElementById('beena-status-text');
            if (statusEl) statusEl.textContent = label;

            // Update all body groups
            const bodyGroups = document.querySelectorAll('.beena-body-group');
            const stateClasses = Object.keys(STATE_LABELS).map(s => `beena-state-${s}`);

            bodyGroups.forEach(g => {
                stateClasses.forEach(c => g.classList.remove(c));
                g.classList.add(`beena-state-${state}`);

                // Update expression layer
                const s   = parseFloat(g.querySelector('svg').getAttribute('viewBox').split(' ')[2]);
                const cx  = s / 2;
                const hcy = s * 0.52 - s * 0.32;
                const exprEl = g.querySelector('.beena-expression');
                if (exprEl && STATE_EXPRESSIONS[state]) {
                    exprEl.innerHTML = STATE_EXPRESSIONS[state](s, cx, hcy);
                }

                // Toggle sparkles / question mark
                const sparkles = g.querySelectorAll('.beena-sparkle');
                const question = g.querySelector('.beena-question');
                sparkles.forEach(sp => {
                    sp.style.opacity = (state === 'happy' || state === 'excited') ? '.8' : '0';
                });
                if (question) {
                    question.style.opacity = state === 'thinking' ? '.9' : '0';
                }
            });
        }

        // ── Nudge Timer ────────────────────────────────────────────────────────

        _startNudgeTimer() {
            if (!this.config.nudge) return;
            const delay = (this.config.nudge_delay || 30) * 1000;
            clearTimeout(this.nudgeTimer);
            this.nudgeTimer = setTimeout(() => {
                if (!this.isOpen) {
                    this.floatEl.classList.add('nudge');
                    const label = document.getElementById('beena-float-label');
                    if (label) label.textContent = this.lang === 'ar' ? 'عندك سؤال؟ 🐝' : 'Need help? 🐝';
                }
            }, delay);
        }
    }

    // ── Inject Buy with AI buttons ────────────────────────────────────────────

    function injectBuyWithAI(config) {
        if (!config.buy_with_ai) return;

        // Find product ID from URL or page data
        const pid = _getProductId();
        if (!pid) return;

        // Find Add to Cart button
        const addToCart = document.querySelector(
            'a[id="add_to_cart"], button[id="add_to_cart"], .a-buy, #add_to_cart, [data-action="add_to_cart"]'
        );
        if (!addToCart) return;

        const btn = document.createElement('button');
        btn.className   = 'beena-buy-ai-btn';
        btn.innerHTML   = `<span style="font-size:18px">🐝</span> Buy with AI`;
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            if (!window._beenaApp) return;
            window._beenaApp.open(pid);
            setTimeout(() => {
                window._beenaApp._send('اشتري هذا المنتج');
            }, 700);
        });

        addToCart.parentNode.insertBefore(btn, addToCart.nextSibling);
    }

    function _getProductId() {
        // Try URL pattern: /shop/product/name-123
        const match = location.pathname.match(/\/shop\/product\/[^/]+-(\d+)$/);
        if (match) return parseInt(match[1]);

        // Try page meta or data attribute
        const productEl = document.querySelector('[data-product-id]');
        if (productEl) return parseInt(productEl.dataset.productId);

        // Try form input
        const input = document.querySelector('input[name="product_id"]');
        if (input) return parseInt(input.value);

        return null;
    }

    // ── Init ──────────────────────────────────────────────────────────────────

    async function init() {
        // Fetch config from Odoo
        let config = {};
        try {
            const resp = await fetch('/ai/config', {
                method:  'POST',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify({ jsonrpc: '2.0', method: 'call', id: 1, params: {} }),
            });
            const data = await resp.json();
            config = data.result || {};
        } catch (e) {
            console.warn('Beena: could not load config', e);
            return;
        }

        if (!config.enabled) return;

        // Build app
        const app = new BeenaApp(config);
        window._beenaApp = app;

        // Inject Buy with AI on product pages
        if (document.readyState === 'complete') {
            injectBuyWithAI(config);
        } else {
            window.addEventListener('load', () => injectBuyWithAI(config));
        }

        // Show float button
        if (config.float_button) {
            document.getElementById('beena-float').style.display = 'flex';
        }
    }

    // Start when DOM is ready — skip non-shop pages
    const EXCLUDED_PATHS = [
        '/web/login', '/web/', '/odoo/',
        '/web#', '/web?', '/reviewer/',
        '/my/account', '/auth/',
    ];

    function shouldRun() {
        const path = location.pathname;
        // Skip Odoo backend
        if (path.startsWith('/odoo') || path.startsWith('/web')) return false;
        // Skip login/auth pages
        if (EXCLUDED_PATHS.some(p => path.startsWith(p))) return false;
        // Skip reviewer portal (has its own JS)
        if (path.startsWith('/reviewer')) return false;
        return true;
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => { if (shouldRun()) init(); });
    } else {
        if (shouldRun()) init();
    }


/* ── Phase 2 additions (appended) ── */
(function(){
    const _orig = BeenaApp && BeenaApp.prototype && BeenaApp.prototype._showOrderCard;

    // Patch _showOrderCard to include Taly + order status link
    if (window.BeenaApp) {
        window.BeenaApp.prototype._showOrderCard = function(order, payment) {
            const div = document.createElement('div');
            div.className = 'beena-msg beena-msg-ai';

            const taly        = payment && payment.taly_enabled;
            const cod         = payment && payment.cod_enabled;
            const checkoutUrl = (payment && payment.checkout_url) || '/shop/payment';

            div.innerHTML = `
<div class="beena-order-card">
  <div class="beena-order-row">
    <span>🎉 طلب <strong>${order.order_name || ''}</strong></span>
  </div>
  <div class="beena-order-row">
    <span>المبلغ الإجمالي</span>
    <span><strong>${(order.amount || 0).toFixed(3)} KD</strong></span>
  </div>
</div>
<div style="font-size:11px;color:#854F0B;margin:6px 0 4px">اختر طريقة الدفع:</div>
<button class="beena-pay-btn beena-pay-upay"
  onclick="window.open('${checkoutUrl}','_self')">
  💳 ادفع الآن — بطاقة / KNET
</button>
${taly ? `<button class="beena-pay-btn beena-pay-taly"
  onclick="window.open('${checkoutUrl}?payment=taly','_self')">
  📅 قسّط مع Taly — 4 دفعات بدون فوائد
</button>` : ''}
${cod ? `<button class="beena-pay-btn beena-pay-cod"
  onclick="window.open('${checkoutUrl}?payment=cod','_self')">
  💵 الدفع عند الاستلام (COD)
</button>` : ''}
<div style="text-align:center;margin-top:6px">
  <a href="/my/orders" style="font-size:11px;color:#854F0B">عرض جميع طلباتي ←</a>
</div>`;
            this.messagesEl.appendChild(div);
            this._scrollBottom();
        };

        // New: show order status card
        window.BeenaApp.prototype._showOrderStatus = function(status) {
            if (!status || status.error) return;
            const div = document.createElement('div');
            div.className = 'beena-msg beena-msg-ai';
            div.innerHTML = `
<div class="beena-order-card">
  <div class="beena-order-row"><span>طلب ${status.order_name}</span><span>${status.date_order || ''}</span></div>
  <div class="beena-order-row"><span>الحالة</span><span><strong>${status.state}</strong></span></div>
  <div class="beena-order-row"><span>التوصيل</span><span>${status.delivery_status || 'غير محدد'}</span></div>
  <div class="beena-order-total"><span>الإجمالي</span><span>${(status.amount || 0).toFixed(3)} KD</span></div>
</div>`;
            this.messagesEl.appendChild(div);
            this._scrollBottom();
        };

        // New: show upsell products
        window.BeenaApp.prototype._showUpsell = function(products) {
            if (!products || !products.length) return;
            const div = document.createElement('div');
            div.className = 'beena-msg beena-msg-ai';
            let html = '<div style="font-size:11px;color:#888;margin-bottom:6px">قد يعجبك أيضاً:</div>';
            products.slice(0, 2).forEach(p => {
                html += `<div style="display:flex;align-items:center;gap:8px;background:#F9F8F5;border-radius:8px;padding:7px 9px;margin-bottom:5px">
                    <img src="${p.image_url||''}" style="width:36px;height:36px;border-radius:6px;object-fit:cover;flex-shrink:0" onerror="this.style.display='none'">
                    <div style="flex:1;min-width:0">
                        <div style="font-size:12px;font-weight:600;color:#1A1A1A;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${p.name}</div>
                        <div style="font-size:11px;color:#854F0B">${(p.price||0).toFixed(3)} KD</div>
                    </div>
                    <button onclick="window.location.href='/shop/product/${p.id}'"
                            style="background:#F5C320;border:none;border-radius:6px;padding:4px 10px;font-size:10px;font-weight:600;cursor:pointer;flex-shrink:0">
                        عرض
                    </button>
                </div>`;
            });
            div.innerHTML = html;
            this.messagesEl.appendChild(div);
            this._scrollBottom();
        };

        // New: show full payment options
        window.BeenaApp.prototype._showPaymentOptions = function(data) {
            if (!data || !data.options || !data.options.length) return;
            const div = document.createElement('div');
            div.className = 'beena-msg beena-msg-ai';
            let html = `<div style="background:#F9F8F5;border-radius:10px;padding:10px 12px">
                <div style="font-size:12px;font-weight:700;color:#1A1A1A;margin-bottom:8px">
                    🎉 طلب ${data.order_name} — ${(data.amount||0).toFixed(3)} KD
                </div>
                <div style="font-size:11px;color:#888;margin-bottom:7px">اختر طريقة الدفع:</div>`;
            data.options.forEach(opt => {
                html += `<button onclick="window.open('${opt.url}','_self')"
                    style="display:flex;align-items:center;gap:10px;width:100%;background:#fff;border:0.5px solid rgba(0,0,0,.1);border-radius:8px;padding:9px 12px;margin-bottom:6px;cursor:pointer;font-family:inherit;text-align:right">
                    <span style="font-size:18px;flex-shrink:0">${opt.icon}</span>
                    <div style="flex:1">
                        <div style="font-size:12px;font-weight:600;color:#1A1A1A">${opt.label}</div>
                        <div style="font-size:10px;color:#888;margin-top:1px">${opt.detail}</div>
                    </div>
                    <span style="color:#aaa;font-size:14px">←</span>
                </button>`;
            });
            html += '</div>';
            div.innerHTML = html;
            this.messagesEl.appendChild(div);
            this._scrollBottom();
            // Save to history
            this._msgHistory.push({type:'ai', text:'[خيارات الدفع]', chips:[]});
            saveHistory(this._msgHistory);
        };

        // New: show loyalty points inside chat
        window.BeenaApp.prototype._showLoyalty = function(data) {
            if (!data || !data.available) return;
            if (!data.logged_in) {
                this._addAIMessage('سجّل دخولك لرؤية نقاطك وعروض الولاء 🌟', 'talking');
                return;
            }

            const levelColors = {starter:'#888',silver:'#888780',gold:'#F5C320',platinum:'#534AB7',elite:'#1D9E75'};
            const color = levelColors[data.level] || '#F5C320';

            const div     = document.createElement('div');
            div.className = 'beena-msg beena-msg-ai';
            div.innerHTML = `
<div style="background:#FEFDF0;border-radius:8px;padding:10px 12px;border:1px solid #F5C320">
  <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">
    <span style="font-size:18px">⭐</span>
    <div>
      <div style="font-size:13px;font-weight:700;color:#1A1A1A">${(data.points||0).toLocaleString()} نقطة</div>
      <div style="font-size:10px;color:#854F0B">= ${data.kd_value||0} KD</div>
    </div>
    <span style="margin-right:auto;background:${color};color:#fff;font-size:9px;padding:2px 7px;border-radius:4px;font-weight:700">${data.level_label||''}</span>
  </div>
  ${data.to_next > 0 ? `
  <div style="height:4px;background:#F0EFE8;border-radius:2px;overflow:hidden;margin-bottom:5px">
    <div style="width:${data.progress||0}%;height:100%;background:${color};border-radius:2px"></div>
  </div>
  <div style="font-size:10px;color:#854F0B">${data.to_next.toLocaleString()} نقطة للمستوى القادم</div>` : '<div style="font-size:10px;color:#1D9E75">أعلى مستوى 🎉</div>'}
  <a href="/loyalty" style="display:block;text-align:center;background:#F5C320;color:#1A1A1A;border-radius:6px;padding:6px;font-size:11px;font-weight:700;text-decoration:none;margin-top:8px">
    عرض كل نقاطي ←
  </a>
</div>`;
            this.messagesEl.appendChild(div);
            this._scrollBottom();
        };

        // New: show size recommendation inside chat
        window.BeenaApp.prototype._showSizeRec = function(data) {
            if (!data || !data.has_sizes || !data.results) return;
            const results = data.results.slice(0, 4);
            const rec     = results.find(r => r.recommended);

            const div     = document.createElement('div');
            div.className = 'beena-msg beena-msg-ai';

            const colorMap = {green:'#E1F5EE', yellow:'#FEFDF0', orange:'#FAEEDA', red:'#FCEBEB'};
            const textMap  = {green:'#085041', yellow:'#854F0B', orange:'#633806', red:'#791F1F'};

            let html = `<div style="font-size:12px;font-weight:600;color:#1A1A1A;margin-bottom:7px">📏 توصية المقاس</div>`;

            if (rec) {
                html += `<div style="background:${colorMap[rec.fit_color]};border-radius:8px;padding:8px 11px;margin-bottom:7px">
                    <div style="font-size:12px;font-weight:700;color:${textMap[rec.fit_color]}">
                        مقاس ${rec.size} — ${rec.fit_label}
                    </div>
                    ${rec.issues.length ? `<div style="font-size:10px;color:${textMap[rec.fit_color]};opacity:.8;margin-top:2px">${rec.issues.join(' · ')}</div>` : ''}
                </div>`;
            }

            html += `<div style="display:flex;flex-wrap:wrap;gap:5px;">`;
            results.forEach(r => {
                html += `<span style="padding:5px 10px;border-radius:7px;border:1px solid;font-size:12px;font-weight:600;
                    background:${colorMap[r.fit_color]};color:${textMap[r.fit_color]};
                    border-color:${r.recommended ? '#F5C320' : 'transparent'}">
                    ${r.size}${r.recommended ? ' ✓' : ''}
                </span>`;
            });
            html += `</div>`;

            div.innerHTML = html;
            this.messagesEl.appendChild(div);
            this._scrollBottom();
        };

        // New: show reviewers list inside chat
        window.BeenaApp.prototype._showReviewers = function(data) {
            if (!data || !data.available) return;

            const div     = document.createElement('div');
            div.className = 'beena-msg beena-msg-ai';

            const reviewers = data.reviewers || [];

            if (!reviewers.length) {
                div.innerHTML = '<div style="font-size:12px;color:#888">لا يوجد ريفيورز متاحون حالياً</div>';
                this.messagesEl.appendChild(div);
                this._scrollBottom();
                return;
            }

            let html = `<div style="font-size:12px;font-weight:600;color:#1A1A1A;margin-bottom:8px">
                👥 ${data.online_count || 0} ريفيور أونلاين الآن:
            </div>`;

            reviewers.slice(0, 4).forEach(r => {
                const stars = '★'.repeat(Math.round(r.rating || 5)) + '☆'.repeat(5 - Math.round(r.rating || 5));
                const badge = {elite:'#3C3489', expert:'#27500A', regular:'#0C447C', starter:'#5F5E5A'}[r.level] || '#5F5E5A';
                const bgBadge = {elite:'#EEEDFE', expert:'#EAF3DE', regular:'#E6F1FB', starter:'#F5F4F2'}[r.level] || '#F5F4F2';

                html += `
<div style="background:#F9F8F5;border-radius:8px;padding:9px;margin-bottom:6px;display:flex;gap:9px;align-items:flex-start;cursor:pointer;border:1px solid transparent"
     onclick="window.open('/shop?reviewer=${r.id}','_self')"
     onmouseover="this.style.borderColor='#F5C320'" onmouseout="this.style.borderColor='transparent'">
  <div style="width:36px;height:36px;border-radius:50%;background:#F5C320;display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:700;flex-shrink:0;position:relative">
    ${r.name ? r.name.charAt(0) : '?'}
    <div style="position:absolute;bottom:0;right:0;width:9px;height:9px;border-radius:50%;background:${r.is_online ? '#1D9E75' : '#ccc'};border:1.5px solid #fff"></div>
  </div>
  <div style="flex:1;min-width:0">
    <div style="font-size:12px;font-weight:700;color:#1A1A1A;display:flex;align-items:center;gap:5px">
      ${r.name}
      <span style="font-size:9px;padding:1px 5px;border-radius:3px;background:${bgBadge};color:${badge}">${r.level_label || ''}</span>
    </div>
    <div style="color:#F5C320;font-size:11px">${stars} <span style="color:#888;font-size:10px">${r.rating}</span></div>
    ${r.specialty_text ? `<div style="font-size:10px;color:#888">${r.specialty_text}</div>` : ''}
    <div style="font-size:10px;color:#854F0B;margin-top:2px">
      ${r.allow_written ? `✍️ ${(r.price_written||0).toFixed(3)} KD` : ''}
      ${r.allow_chat    ? ` 💬 ${(r.price_chat||0).toFixed(3)} KD` : ''}
    </div>
  </div>
</div>`;
            });

            if (data.all_offline) {
                html += '<div style="font-size:11px;color:#888;text-align:center;margin-top:4px">غير متصلين حالياً — يمكنك ترك طلب</div>';
            }

            div.innerHTML = html;
            this.messagesEl.appendChild(div);
            this._scrollBottom();

            // Save to history
            this._msgHistory.push({type:'ai', text:'[قائمة ريفيورز]', chips:[]});
            saveHistory(this._msgHistory);
        };

        // New: show orders list
        window.BeenaApp.prototype._showOrdersList = function(orders) {
            if (!orders || !orders.length) return;
            const div = document.createElement('div');
            div.className = 'beena-msg beena-msg-ai';
            let html = '<div class="beena-order-card">';
            orders.forEach(o => {
                html += `<div class="beena-order-row">
                    <span>${o.name}</span>
                    <span>${(o.amount||0).toFixed(3)} KD</span>
                  </div>`;
            });
            html += '</div>';
            div.innerHTML = html;
            this.messagesEl.appendChild(div);
            this._scrollBottom();
        };

        // New: show cart confirmation
        window.BeenaApp.prototype._showCartAdded = function(cart) {
            if (!cart || !cart.success) return;
            const div = document.createElement('div');
            div.className = 'beena-msg beena-msg-ai';
            div.innerHTML = `
<div style="background:#E1F5EE;border-radius:8px;padding:8px 12px;font-size:12px;color:#085041">
  ✓ تمت الإضافة للسلة — الإجمالي: <strong>${(cart.cart_total||0).toFixed(3)} KD</strong>
  <a href="${cart.cart_url||'/shop/cart'}" style="margin-right:8px;color:#085041;font-weight:600">عرض السلة ←</a>
</div>`;
            this.messagesEl.appendChild(div);
            this._scrollBottom();
        };

        // Patch _send to handle new extra fields
        const origSend = window.BeenaApp.prototype._send;
        window.BeenaApp.prototype._send = async function(text) {
            const msg = (text || this.inputEl.value).trim();
            if (!msg) return;
            this.inputEl.value = '';
            this._addUserMessage(msg);
            this._showTyping();
            this._setState('thinking');

            try {
                const resp = await fetch('/ai/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        jsonrpc: '2.0', method: 'call', id: 1,
                        params: {
                            message: msg,
                            session_id: this.sessionId,
                            product_id: this.productId,
                        },
                    }),
                });
                const data   = await resp.json();
                const result = data.result || {};
                this._removeTyping();

                if (result.error) {
                    this._addAIMessage('عذراً، حدث خطأ. حاول مرة ثانية.', 'sad');
                    this._setState('sad');
                    return;
                }

                const reply = result.reply || '';
                const state = result.state || 'talking';
                const extra = result.extra || {};

                this._addAIMessage(reply, state);
                this._setState(state);

                if (extra.order)        this._showOrderCard(extra.order, extra.payment);
                if (extra.payment && !extra.order) this._showOrderCard({amount: extra.payment.amount, order_name: extra.payment.order_name}, extra.payment);
                if (extra.products)     this._showProductList(extra.products);
                if (extra.order_status) this._showOrderStatus(extra.order_status);
                if (extra.orders_list)  this._showOrdersList(extra.orders_list);
                if (extra.cart)         this._showCartAdded(extra.cart);
                if (extra.reviewers)    this._showReviewers(extra.reviewers);
                if (extra.size_rec)     this._showSizeRec(extra.size_rec);
                if (extra.loyalty)         this._showLoyalty(extra.loyalty);
                if (extra.upsell)          this._showUpsell(extra.upsell);
                if (extra.payment_options) this._showPaymentOptions(extra.payment_options);

                setTimeout(() => this._setState('idle'), 4000);

            } catch(err) {
                this._removeTyping();
                this._addAIMessage('مشكلة في الاتصال. تأكد من الإنترنت وحاول ثاني.', 'sad');
                this._setState('sad');
            }
        };
    }
    // ── Direct Add to Cart (global helper) ──────────────────────────────────
    window._beenaAddToCart = function(variantId, productName) {
        if (!variantId) return;
        var xhr = new XMLHttpRequest();
        xhr.open('POST', '/shop/cart/update_json', true);
        xhr.setRequestHeader('Content-Type', 'application/json');
        xhr.onload = function() {
            try {
                var data = JSON.parse(xhr.responseText);
                var r = (data && data.result) || {};
                if (r.cart_quantity !== undefined) {
                    var app = window._beenaApp;
                    if (app) {
                        var div = document.createElement('div');
                        div.className = 'beena-msg beena-msg-ai';
                        div.innerHTML = '<div style="background:#E1F5EE;border-radius:8px;padding:9px 12px">'
                            + '<div style="font-size:13px;font-weight:600;color:#085041">✓ تمت الإضافة للسلة</div>'
                            + '<div style="font-size:11px;color:#1D9E75;margin-top:3px">' + productName + '</div>'
                            + '<a href="/shop/cart" style="display:inline-block;margin-top:6px;background:#1D9E75;color:#fff;padding:4px 12px;border-radius:6px;font-size:11px;font-weight:600;text-decoration:none">'
                            + 'عرض السلة (' + r.cart_quantity + ') ←</a></div>';
                        app.messagesEl.appendChild(div);
                        app._scrollBottom();
                    }
                    var badge = document.querySelector('.my_cart_quantity, #cart-total-quantity');
                    if (badge) badge.textContent = r.cart_quantity;
                }
            } catch(e) { console.error('cart parse error', e); }
        };
        xhr.send(JSON.stringify({jsonrpc:'2.0',method:'call',id:1,params:{product_id:variantId,add_qty:1}}));
    };


});

})();
