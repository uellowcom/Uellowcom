/**
 * Uellow AI Engine — Beena.js
 * Phase 1: Chat UI + Claude API + Streaming + Animated Avatar
 */

(function () {
    'use strict';

    // ── SVG Generator ─────────────────────────────────────────────────────────
    // Draws Beena matching the Uellow logo bee precisely

    // Tiny console wrapper used by the voice stack to stay quiet by default.
    function _logger_warn() {
        if (window.localStorage && localStorage.getItem('beena_debug') === '1') {
            console.warn.apply(console, ['[beena]'].concat([].slice.call(arguments)));
        }
    }

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
            // Normalize: any of "ar", "ar-SA", "ar_001" → "ar"; everything else → "en"
            const rawLang = (document.documentElement.lang || '').toLowerCase();
            this.lang     = rawLang.startsWith('ar') ? 'ar' : 'en';
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
                    ${(this.config && this.config.voice_enabled && this.config.voice_phase_b) ? `
                    <button id="beena-voice-call" class="beena-voice-call-btn"
                            aria-label="${this.lang === 'ar' ? 'مكالمة صوتية' : 'Voice call'}"
                            title="${this.lang === 'ar' ? 'مكالمة صوتية مع بينا' : 'Voice call with Beena'}">
                        📞
                    </button>` : ''}
                    <div id="beena-traffic-lights">
                        <button id="beena-max" class="beena-tl beena-tl-max" aria-label="Maximize" title="${this.lang === 'ar' ? 'تكبير' : 'Maximize'}"><span>⛶</span></button>
                        <button id="beena-min" class="beena-tl beena-tl-min" aria-label="Minimize" title="${this.lang === 'ar' ? 'تصغير' : 'Minimize'}"><span>—</span></button>
                        <button id="beena-close" class="beena-tl beena-tl-close" aria-label="${this.lang === 'ar' ? 'إغلاق' : 'Close'}"><span>×</span></button>
                    </div>
                </div>
                <div id="beena-context" style="display:none"></div>
                <div id="beena-messages" role="log" aria-live="polite"></div>
                <div id="beena-input-row">
                    <button id="beena-cam-btn"
                            title="${this.lang === 'ar' ? 'ابحث عن منتج بالصورة' : 'Search for a product by image'}"
                            aria-label="${this.lang === 'ar' ? 'ابحث بالصورة' : 'Search by image'}">📷</button>
                    <button id="beena-voice-btn"
                            title="${this.lang === 'ar' ? 'اضغط مطوّلاً للتسجيل' : 'Hold to record'}"
                            aria-label="${this.lang === 'ar' ? 'رسالة صوتية' : 'Voice message'}">
                        <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor" aria-hidden="true">
                            <path d="M12 14a3 3 0 0 0 3-3V6a3 3 0 0 0-6 0v5a3 3 0 0 0 3 3zm5-3a5 5 0 1 1-10 0H5a7 7 0 0 0 6 6.92V21h2v-3.08A7 7 0 0 0 19 11h-2z"/>
                        </svg>
                    </button>
                    <input id="beena-input" type="text" placeholder="${this.lang === 'ar' ? 'اسأل بينا...' : 'Ask Beena...'}" autocomplete="off" dir="auto"/>
                    <button id="beena-send-btn" aria-label="إرسال">➤</button>
                </div>`;

            document.body.appendChild(floatEl);
            document.body.appendChild(chatEl);

            this.floatEl    = floatEl;
            this.chatEl     = chatEl;
            this.messagesEl = document.getElementById('beena-messages');
            // Capture any <a> click inside the chat — if it's a same-origin
            // link, open it in our dialog instead of navigating the host page.
            this.messagesEl.addEventListener('click', (ev) => {
                // Delegated sign-in buttons → open the smart sign-in dialog
                const sb = ev.target.closest && ev.target.closest('[data-action="beena-signin"]');
                if (sb) {
                    ev.preventDefault();
                    this._openSignInDialog('/web/login');
                    return;
                }
                const a = ev.target.closest && ev.target.closest('a[href]');
                if (!a) return;
                const href = a.getAttribute('href') || '';
                if (!href || a.dataset.beenaExternal === '1') return;
                // External links / mail / tel / # → leave default behaviour
                if (/^(mailto:|tel:|sms:|#)/i.test(href)) return;
                let u;
                try { u = new URL(href, location.href); }
                catch (e) { return; }
                if (u.origin !== location.origin) return;     // external host → new tab
                ev.preventDefault();
                this._openInternalLink(u.pathname + u.search + u.hash);
            });
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
            const maxBtn = document.getElementById('beena-max');
            const minBtn = document.getElementById('beena-min');
            if (maxBtn) maxBtn.addEventListener('click', () => this.toggleMaximize());
            if (minBtn) minBtn.addEventListener('click', () => this.close());

            document.getElementById('beena-send-btn').addEventListener('click', () => this._send());
            this.inputEl.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); this._send(); }
            });
            // Live-flip composer direction when user types Arabic on an EN page
            this.inputEl.addEventListener('input', (e) => {
                const v = e.target.value || '';
                const isRTL = /[؀-ۿݐ-ݿ]/.test(v);
                this.chatEl.classList.toggle('beena-input-rtl', isRTL);
                this.inputEl.style.direction = isRTL ? 'rtl' : 'ltr';
                this.inputEl.style.textAlign = isRTL ? 'right' : 'left';
            });

            document.getElementById('beena-cam-btn').addEventListener('click', () => this._openImageSearch());
            const callBtn = document.getElementById('beena-voice-call');
            if (callBtn) callBtn.addEventListener('click', () => this._startVoiceCall());
            this._bindVoiceHold();

            // Close on outside click — but only if we just didn't drag.
            //
            // We use composedPath() instead of contains() because some inner
            // handlers (e.g. the TTS pause button rewriting its own innerHTML)
            // detach the original click target before this listener runs —
            // contains() would then return false on a click that was clearly
            // INSIDE the panel and we'd close ourselves by mistake.
            document.addEventListener('click', (e) => {
                if (this._suppressOutsideClick) return;
                if (!this.isOpen) return;
                const path = (typeof e.composedPath === 'function') ? e.composedPath() : [];
                const insidePanel = path.includes(this.chatEl) || path.includes(this.floatEl)
                                 || (this.chatEl && this.chatEl.contains(e.target))
                                 || (this.floatEl && this.floatEl.contains(e.target));
                if (!insidePanel) this.close();
            });

            // Keyboard
            document.getElementById('beena-float-btn').addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') this.toggle();
            });

            // ── Drag the panel by its header ────────────────────────────
            this._bindDrag();
            this._restorePanelPosition();
        }

        /**
         * Make the header a drag handle: hold + move to reposition the panel.
         * Saves to localStorage so the position survives reload.
         * Mouse + touch support. Ignored when starting on a header button.
         */
        _bindDrag() {
            const header = document.getElementById('beena-header');
            if (!header) return;
            header.classList.add('beena-draggable');

            const start = (clientX, clientY, target) => {
                // Don't drag if user pressed a button or interactive element in header
                if (target && target.closest('button, input, a, select, textarea')) return false;
                if (this.chatEl.classList.contains('maximized')) return false;
                this._dragging = {
                    startX: clientX, startY: clientY,
                    origLeft: this.chatEl.offsetLeft,
                    origTop:  this.chatEl.offsetTop,
                };
                // Detach from right/bottom anchoring so we can use left/top freely
                this.chatEl.style.right  = 'auto';
                this.chatEl.style.bottom = 'auto';
                this.chatEl.classList.add('beena-dragging');
                return true;
            };

            const move = (clientX, clientY) => {
                if (!this._dragging) return;
                const dx = clientX - this._dragging.startX;
                const dy = clientY - this._dragging.startY;
                let left = this._dragging.origLeft + dx;
                let top  = this._dragging.origTop  + dy;
                // Clamp inside viewport (keep 10px margin)
                const w = this.chatEl.offsetWidth;
                const h = this.chatEl.offsetHeight;
                const maxLeft = window.innerWidth  - w - 10;
                const maxTop  = window.innerHeight - h - 10;
                left = Math.max(10, Math.min(maxLeft, left));
                top  = Math.max(10, Math.min(maxTop,  top));
                this.chatEl.style.left = left + 'px';
                this.chatEl.style.top  = top  + 'px';
            };

            const end = () => {
                if (!this._dragging) return;
                this._dragging = null;
                this.chatEl.classList.remove('beena-dragging');
                // Persist position
                try {
                    localStorage.setItem('beena_panel_pos', JSON.stringify({
                        left: this.chatEl.offsetLeft,
                        top:  this.chatEl.offsetTop,
                    }));
                } catch (e) {}
                // Suppress the click that immediately follows mouseup so the
                // outside-click listener doesn't close the panel.
                this._suppressOutsideClick = true;
                setTimeout(() => { this._suppressOutsideClick = false; }, 150);
            };

            // Mouse
            header.addEventListener('mousedown', (e) => {
                if (e.button !== 0) return;
                if (!start(e.clientX, e.clientY, e.target)) return;
                e.preventDefault();
                const onMove = (ev) => move(ev.clientX, ev.clientY);
                const onUp   = () => {
                    end();
                    document.removeEventListener('mousemove', onMove);
                    document.removeEventListener('mouseup',   onUp);
                };
                document.addEventListener('mousemove', onMove);
                document.addEventListener('mouseup',   onUp);
            });

            // Touch
            header.addEventListener('touchstart', (e) => {
                if (e.touches.length !== 1) return;
                const t = e.touches[0];
                if (!start(t.clientX, t.clientY, e.target)) return;
                const onMove = (ev) => {
                    if (ev.touches.length !== 1) return;
                    ev.preventDefault();
                    move(ev.touches[0].clientX, ev.touches[0].clientY);
                };
                const onEnd = () => {
                    end();
                    document.removeEventListener('touchmove', onMove);
                    document.removeEventListener('touchend',  onEnd);
                    document.removeEventListener('touchcancel', onEnd);
                };
                document.addEventListener('touchmove', onMove, {passive: false});
                document.addEventListener('touchend',  onEnd);
                document.addEventListener('touchcancel', onEnd);
            }, {passive: true});

            // Keep the panel on screen after a window resize
            window.addEventListener('resize', () => {
                if (!this.chatEl.style.left) return;   // not yet moved
                const w = this.chatEl.offsetWidth;
                const h = this.chatEl.offsetHeight;
                const maxLeft = Math.max(10, window.innerWidth  - w - 10);
                const maxTop  = Math.max(10, window.innerHeight - h - 10);
                this.chatEl.style.left = Math.min(parseFloat(this.chatEl.style.left) || 0, maxLeft) + 'px';
                this.chatEl.style.top  = Math.min(parseFloat(this.chatEl.style.top)  || 0, maxTop)  + 'px';
            });
        }

        _restorePanelPosition() {
            try {
                const raw = localStorage.getItem('beena_panel_pos');
                if (!raw) return;
                const pos = JSON.parse(raw);
                if (typeof pos.left !== 'number' || typeof pos.top !== 'number') return;
                const w = this.chatEl.offsetWidth  || 340;
                const h = this.chatEl.offsetHeight || 560;
                const maxLeft = Math.max(10, window.innerWidth  - w - 10);
                const maxTop  = Math.max(10, window.innerHeight - h - 10);
                this.chatEl.style.right  = 'auto';
                this.chatEl.style.bottom = 'auto';
                this.chatEl.style.left = Math.max(10, Math.min(maxLeft, pos.left)) + 'px';
                this.chatEl.style.top  = Math.max(10, Math.min(maxTop,  pos.top))  + 'px';
            } catch (e) {}
        }

        _resetPanelPosition() {
            try { localStorage.removeItem('beena_panel_pos'); } catch (e) {}
            this.chatEl.style.left   = '';
            this.chatEl.style.top    = '';
            this.chatEl.style.right  = '';
            this.chatEl.style.bottom = '';
        }

        // ── Open / Close ───────────────────────────────────────────────────────

        toggle() {
            this.isOpen ? this.close() : this.open();
        }

        async open(productId) {
            if (productId) this.productId = productId;
            this.isOpen = true;
            this.chatEl.classList.add('open');
            // Hide the float button while the panel is open
            if (this.floatEl) this.floatEl.style.display = 'none';
            clearTimeout(this.nudgeTimer);
            // Clear unread indicator
            this._unread = 0;
            this._renderUnreadBadge();

            if (this.messagesEl.children.length === 0) {
                // 1. Try server-side history (logged-in users)
                let restored = false;
                try {
                    const r = await fetch('/ai/history', {
                        method:  'POST',
                        headers: {'Content-Type': 'application/json'},
                        body:    JSON.stringify({jsonrpc:'2.0',method:'call',id:1,params:{limit: 30}}),
                    });
                    const j  = await r.json();
                    const res = (j && j.result) || {};
                    if (res.logged_in && Array.isArray(res.messages) && res.messages.length) {
                        this._restoreHistory(res.messages);
                        restored = true;
                        if (res.session_id) this.sessionId = res.session_id;
                    }
                } catch (e) { /* fall through to localStorage */ }

                // 2. Fallback: local history (guests)
                if (!restored) {
                    const local = loadHistory();
                    if (local.length > 0) {
                        this._restoreHistory(local);
                        restored = true;
                    }
                }

                // 3. First-ever open → welcome
                if (!restored) {
                    this._showWelcome();
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
            this.chatEl.classList.remove('maximized');
            if (this.floatEl && this.config.float_button) {
                this.floatEl.style.display = 'flex';
            }
            // Kill any in-flight or queued audio so it doesn't keep talking
            // in the background after the user closed the panel.
            if (this._autoplayTimer) {
                clearTimeout(this._autoplayTimer);
                this._autoplayTimer = null;
            }
            if (this._ttsAudio) {
                try { this._ttsAudio.pause(); } catch (e) {}
                this._ttsAudio = null;
            }
            if (window.speechSynthesis && window.speechSynthesis.speaking) {
                try { window.speechSynthesis.cancel(); } catch (e) {}
            }
            this._ttsButton = null;
            this._startNudgeTimer();
        }

        toggleMaximize() {
            this.chatEl.classList.toggle('maximized');
        }

        // ── Product Context Bar ────────────────────────────────────────────────

        _showProductContext(pid) {
            // Robust product-name detection across Theme Prime / Odoo / generic
            const nameEl = document.querySelector(
                'h1.product-name, h1.product_name, h1[itemprop="name"], ' +
                '.product_name, [itemprop="name"], ' +
                '#product_detail h1, #wrapwrap h1, ' +
                'main h1'
            );
            const priceEl = document.querySelector(
                '.oe_price .oe_currency_value, .product-price .currency_value, ' +
                '[itemprop="price"], .product_price_text, .price'
            );
            // Fall back: grab the <title> minus site suffix
            let name = nameEl ? nameEl.textContent.trim() : '';
            if (!name && document.title) {
                name = document.title.replace(/\s*[|·–-]\s*Uellow.*$/i, '').trim();
            }
            if (!name) return;

            const price = priceEl ? priceEl.textContent.trim() : '';

            this.contextEl.innerHTML = `
                <img id="beena-context-img"
                     src="/web/image/product.template/${pid}/image_128"
                     alt="${this._escapeHTML(name)}"
                     onerror="this.style.display='none'">
                <div>
                    <div id="beena-context-name">${this._escapeHTML(name)}</div>
                    <div id="beena-context-price">${this._escapeHTML(price)}${price ? ' KD' : ''}</div>
                </div>`;
            this.contextEl.style.display = 'flex';
        }

        // ── Welcome ────────────────────────────────────────────────────────────

        _showWelcome() {
            const nameEl = document.querySelector('.o_account_name, .o_portal_name, [data-customer-name]');
            const customerName = nameEl ? nameEl.textContent.trim().split(' ')[0] : '';

            let pName = '';
            if (this.productId) {
                const ctxName = document.getElementById('beena-context-name');
                pName = ctxName ? ctxName.textContent.trim() : '';
                if (!pName) {
                    const el = document.querySelector('.product_name, h1.product-name, [itemprop="name"], #product_details h2');
                    pName = el ? el.textContent.trim() : '';
                }
            }

            let arLine, enLine;
            if (this.productId) {
                const q = pName ? '"' + pName + '"' : 'هذا المنتج';
                const qe = pName ? '"' + pName + '"' : 'this product';
                arLine = 'هلا فيك' + (customerName ? ' ' + customerName : '') + '! أنا بينا من خدمة عملاء يلو 🐝 تسأل عن ' + q + '؟ أقدر أخبرك عن مواصفاته أو أنصحك إن كان يناسبك.';
                enLine = "Hi" + (customerName ? ' ' + customerName : '') + "! I'm Beena from Uellow support 🐝 Asking about " + qe + "? I can share its specs or advise if it suits you.";
            } else {
                arLine = 'هلا فيك' + (customerName ? ' ' + customerName : '') + '! أنا بينا، مساعدتك الذكية في يلو 🐝';
                enLine = "Hi" + (customerName ? ' ' + customerName : '') + "! I'm Beena, your smart assistant at Uellow 🐝";
            }

            const greeting = arLine + '\n\n' + enLine + '\n\nاختر لغتك / Choose your language:';
            const chips = ['العربية', 'English', 'لغة أخرى / Other'];
            this._addAIMessage(greeting, 'happy', chips);
        }

        _setBeenaLang(choice) {
            if (choice === 'العربية') {
                this.userLang = 'ar';
                this._send('أكمل بالعربية من فضلك');
            } else if (choice === 'English') {
                this.userLang = 'en';
                this._send('Please continue in English');
            } else {
                this.userLang = null;
                this._addAIMessage('اكتب لغتك المفضلة وسأكمل بها. / Type your preferred language and I will continue in it.', 'idle', []);
            }
        }

        // ── Restore History ───────────────────────────────────────────────────────

        _restoreHistory(history) {
            if (!history || !history.length) return;
            const indicator = document.createElement('div');
            indicator.style.cssText = 'text-align:center;font-size:10px;color:#aaa;padding:4px 0 8px;';
            indicator.textContent = this.lang === 'ar' ? '── محادثة سابقة ──' : '── Previous conversation ──';
            this.messagesEl.appendChild(indicator);

            // Suppress auto-play while we re-render older messages. Without
            // this flag the panel would speak every past AI bubble at once
            // when the user opens Beena (auto-play fires inside _addAIMessage).
            this._isRestoring = true;
            try {
                history.forEach(msg => {
                    if (msg.type === 'user') {
                        const div     = document.createElement('div');
                        div.className = 'beena-msg beena-msg-user';
                        div.textContent = msg.text;
                        this.messagesEl.appendChild(div);
                    } else if (msg.type === 'ai') {
                        if (msg.text) this._addAIMessage(msg.text, 'idle', msg.chips || []);
                        // Replay any rich cards stored on this turn
                        const ex = msg.extra;
                        if (ex && typeof ex === 'object') {
                            this._dispatchExtra(ex);
                        }
                    }
                });
            } finally {
                this._isRestoring = false;
            }

            this._addClearButton();
            this._scrollBottom();
        }

        /**
         * Re-render any extra cards from a stored turn. Mirrors the dispatch
         * list in _send so the same payload renders identically.
         */
        _dispatchExtra(extra) {
            if (!extra) return;
            if (extra.order)        this._showOrderCard(extra.order, extra.payment);
            if (extra.payment && !extra.order) this._showOrderCard({amount: extra.payment.amount, order_name: extra.payment.order_name}, extra.payment);
            if (extra.products)     this._showProductList(extra.products);
            if (extra.order_status) this._showOrderStatus(extra.order_status);
            if (extra.orders_list)  this._showOrdersList(extra.orders_list);
            if (extra.cart)         this._showCartAdded(extra.cart);
            if (extra.reviewers)    this._showReviewers(extra.reviewers);
            if (extra.size_rec)     this._showSizeRec(extra.size_rec);
            if (extra.tryon)        this._showTryOn(extra.tryon);
            if (extra.fit_check)    this._showFitCheck(extra.fit_check);
            if (extra.fit_replay)   this._showFitReplay(extra.fit_replay);
            if (extra.cart_view)        this._showCartView(extra.cart_view);
            if (extra.checkout)         this._showCheckout(extra.checkout);
            if (extra.quote)            this._showQuote(extra.quote);
            if (extra.company_location) this._showCompanyLocation(extra.company_location);
            if (extra.loyalty)         this._showLoyalty(extra.loyalty);
            if (extra.upsell)          this._showUpsell(extra.upsell);
            if (extra.payment_options) this._showPaymentOptions(extra.payment_options);
            if (extra.location)        this._showLocation(extra.location);
            if (extra.locations && Array.isArray(extra.locations))
                extra.locations.forEach(loc => this._showLocation(loc));
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

        /**
         * Bind hold-to-record behaviour on the mic button. Mouse + touch.
         * Slide away (drag finger/cursor > 80px upward) → cancel.
         */
        _bindVoiceHold() {
            const btn = document.getElementById('beena-voice-btn');
            if (!btn) return;
            let startY = 0;
            let cancelled = false;

            const begin = (clientY) => {
                // Self-heal stuck state — if the recorder vanished but the
                // flag is still true (e.g. mr.stop() threw, or onstop never
                // fired), force-reset so a fresh recording can start.
                if (this._voiceActive
                    && (!this._mediaRecorder || this._mediaRecorder.state === 'inactive')
                    && !this._recognition) {
                    this._voiceActive = false;
                    this._hideRecordingBubble();
                    btn.classList.remove('beena-mic-recording', 'beena-mic-cancel');
                }
                if (this._voiceActive) return;

                // Mute Beena's auto-play before we start listening — otherwise
                // the mic would pick up her own voice and the user would hear
                // her talking over their own recording.
                if (this._autoplayTimer) {
                    clearTimeout(this._autoplayTimer);
                    this._autoplayTimer = null;
                }
                if (this._ttsAudio) {
                    try { this._ttsAudio.pause(); } catch (e) {}
                    this._ttsAudio = null;
                }
                if (window.speechSynthesis && window.speechSynthesis.speaking) {
                    try { window.speechSynthesis.cancel(); } catch (e) {}
                }
                this._ttsButton = null;

                startY = clientY;
                cancelled = false;
                this._startVoice();
            };
            const move = (clientY) => {
                if (!this._voiceActive) return;
                if (startY - clientY > 80 && !cancelled) {
                    cancelled = true;
                    btn.classList.add('beena-mic-cancel');
                    this.inputEl.placeholder = this.lang === 'ar'
                        ? '✕ اترك للإلغاء'
                        : '✕ Release to cancel';
                }
            };
            const finish = () => {
                if (!this._voiceActive) return;
                if (cancelled) {
                    this._cancelVoice();
                } else {
                    // Stop recognition gracefully — onresult will _send() if final
                    this._endVoice();
                }
                btn.classList.remove('beena-mic-cancel');
            };

            btn.addEventListener('mousedown',  (e) => { e.preventDefault(); begin(e.clientY); });
            btn.addEventListener('touchstart', (e) => {
                if (e.touches.length !== 1) return;
                e.preventDefault();
                begin(e.touches[0].clientY);
            }, {passive: false});

            // Track movement on the whole document so the cursor can leave the button
            document.addEventListener('mousemove', (e) => move(e.clientY));
            document.addEventListener('touchmove', (e) => {
                if (e.touches.length === 1) move(e.touches[0].clientY);
            }, {passive: true});

            document.addEventListener('mouseup',     finish);
            document.addEventListener('touchend',    finish);
            document.addEventListener('touchcancel', finish);
        }

        _startVoice() {
            // Server-side STT path (preferred) — MediaRecorder → /ai/transcribe
            const useServer = this.config && this.config.voice_enabled && this.config.voice_phase_a;
            if (useServer && window.MediaRecorder && navigator.mediaDevices) {
                this._startVoiceServer();
                return;
            }
            // Browser fallback (Web Speech API)
            const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
            if (!SR) {
                this._addAIMessage(this._t(
                    'Your browser does not support voice input. Try Chrome or Edge.',
                    'متصفحك لا يدعم الصوت. جرّب Chrome أو Edge.'), 'sad');
                return;
            }
            this._recognition = new SR();

            // Explicit lang gives much better quality than empty / browser-default.
            // Use the panel lang first, fall back to page lang, then browser lang.
            const pickLang = () => {
                const a = (this.lang === 'ar') ? 'ar-KW' : null;
                if (a) return a;
                const docLang = (document.documentElement.lang || '').toLowerCase();
                if (docLang.startsWith('ar')) return 'ar-KW';
                if (docLang.startsWith('en')) return 'en-US';
                return navigator.language || 'en-US';
            };
            this._recognition.lang = pickLang();
            this._recognition.continuous      = false;
            this._recognition.interimResults  = true;
            this._recognition.maxAlternatives = 3;

            const btn = document.getElementById('beena-voice-btn');

            this._recognition.onstart = () => {
                this._voiceActive = true;
                this._voiceNoSpeech = 0;
                if (btn) btn.classList.add('beena-mic-recording');
                this.inputEl.placeholder = this.lang === 'ar' ? '🎤 جاري التسجيل...' : '🎤 Recording...';
                this._setState('thinking');
                this._showRecordingBubble();
            };

            this._recognition.onresult = (e) => {
                // Reset the no-speech counter — we're hearing something
                this._voiceNoSpeech = 0;
                // Pick the most confident alternative across ALL final results
                let transcript = '';
                let bestConfidence = 0;
                for (let r = 0; r < e.results.length; r++) {
                    const result = e.results[r];
                    for (let i = 0; i < result.length; i++) {
                        if ((result[i].confidence || 0) >= bestConfidence) {
                            bestConfidence = result[i].confidence || 0;
                            transcript    = result[i].transcript;
                        }
                    }
                }
                if (!transcript) {
                    transcript = Array.from(e.results).map(r => r[0].transcript).join(' ').trim();
                }
                this.inputEl.value = transcript;
                this._voiceLastTranscript = transcript;

                const lastResult = e.results[e.results.length - 1];
                if (lastResult.isFinal) {
                    this._stopVoice();
                    setTimeout(() => { if (this.inputEl.value.trim()) this._send(); }, 250);
                }
            };

            this._recognition.onerror = (e) => {
                // "no-speech" can fire spuriously on slow speech. Retry once
                // silently if the user is still holding the mic.
                if (e.error === 'no-speech' && this._voiceActive && (this._voiceNoSpeech || 0) < 1) {
                    this._voiceNoSpeech = (this._voiceNoSpeech || 0) + 1;
                    try { this._recognition.start(); } catch (e2) {}
                    return;
                }
                this._stopVoice();
                if (e.error === 'no-speech') return;       // user just stayed silent
                if (e.error === 'aborted')   return;       // we cancelled
                if (e.error === 'not-allowed' || e.error === 'service-not-allowed') {
                    this._addAIMessage(this._t(
                        'Microphone is blocked. Allow it in your browser settings.',
                        'الميكروفون محظور. فعّله من إعدادات المتصفح.'), 'sad');
                    return;
                }
                this._addAIMessage(this._t(
                    'I did not catch that. Try again.',
                    'ما سمعت شيء، حاول مرة ثانية.'), 'sad');
            };

            this._recognition.onend = () => this._stopVoice();

            try { this._recognition.start(); }
            catch(e) {
                this._addAIMessage(this._t(
                    'Could not enable the microphone. Check permissions.',
                    'تعذّر تفعيل الميكروفون. تأكد من الأذونات.'), 'sad');
            }
        }

        // Stop the recognition (called either after a successful final result,
        // or by the user releasing the mic).
        _endVoice() {
            if (this._mediaRecorder && this._mediaRecorder.state !== 'inactive') {
                const mr = this._mediaRecorder;
                let stopped = false;
                try { mr.stop(); stopped = true; } catch(e) {}
                if (!stopped) {
                    // stop() threw → onstop will never fire → flush state now
                    this._stopVoice();
                    return;
                }
                // Watchdog: if for any reason `onstop` doesn't fire (browser
                // dropping the stream, tab going hidden, etc.) force-clean
                // after 2s so the next mic press isn't dead.
                setTimeout(() => {
                    if (this._mediaRecorder === mr) this._stopVoice();
                }, 2000);
                return;
            }
            if (this._recognition) {
                try { this._recognition.stop(); } catch(e) {}
            }
        }

        // User slid away while holding → cancel the message
        _cancelVoice() {
            this._voiceCancelled = true;
            if (this._mediaRecorder && this._mediaRecorder.state !== 'inactive') {
                try { this._mediaRecorder.stop(); } catch(e) {}
            }
            if (this._recognition) {
                try { this._recognition.abort(); } catch(e) {}
            }
            // Clear the input so the cancelled transcript doesn't get sent
            this.inputEl.value = '';
            this._voiceLastTranscript = '';
        }

        _stopVoice() {
            const wasActive = this._voiceActive;
            this._voiceActive = false;
            const btn = document.getElementById('beena-voice-btn');
            if (btn) btn.classList.remove('beena-mic-recording', 'beena-mic-cancel');
            this.inputEl.placeholder = this.lang === 'ar' ? 'اسأل بينا...' : 'Ask Beena...';
            this._hideRecordingBubble();
            if (this._voiceCancelled) {
                this._voiceCancelled = false;
                this._setState('idle');
            }
            if (this._mediaRecorder) {
                try { this._mediaRecorder.stream.getTracks().forEach(t => t.stop()); } catch(e) {}
                this._mediaRecorder = null;
            }
            if (this._recognition) { try { this._recognition.stop(); } catch(e) {} this._recognition = null; }
        }

        /**
         * Server-side STT path: record audio via MediaRecorder, upload to
         * /ai/transcribe, then send the transcript through Beena's normal
         * chat flow. Much better quality than the browser Web Speech API.
         */
        async _startVoiceServer() {
            const self = this;
            const btn = document.getElementById('beena-voice-btn');
            this._voiceCancelled = false;
            let stream;
            try {
                stream = await navigator.mediaDevices.getUserMedia({audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl:  true,
                }});
            } catch (e) {
                this._addAIMessage(this._t(
                    'Microphone is blocked. Allow it in your browser settings.',
                    'الميكروفون محظور. فعّله من إعدادات المتصفح.'), 'sad');
                return;
            }

            // Pick the best supported container — Whisper, Scribe, Azure all
            // accept webm/opus; m4a is iOS Safari's preferred output.
            const mimes = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4', 'audio/ogg'];
            const mime = mimes.find(m => window.MediaRecorder.isTypeSupported(m)) || '';
            const mr = new MediaRecorder(stream, mime ? {mimeType: mime} : undefined);
            this._mediaRecorder = mr;
            this._voiceActive   = true;
            if (btn) btn.classList.add('beena-mic-recording');
            this.inputEl.placeholder = this.lang === 'ar' ? '🎤 جاري التسجيل...' : '🎤 Recording...';
            this._setState('thinking');
            this._showRecordingBubble();

            const chunks = [];
            mr.ondataavailable = (e) => { if (e.data && e.data.size) chunks.push(e.data); };
            mr.onstop = async () => {
                // Snapshot the cancel flag BEFORE _stopVoice clears it —
                // otherwise the "did user cancel?" check below always reads
                // false and we end up sending the cancelled audio anyway.
                const wasCancelled = this._voiceCancelled;
                this._stopVoice();
                if (wasCancelled) return;
                if (!chunks.length) return;
                const blob = new Blob(chunks, {type: mr.mimeType || mime || 'audio/webm'});
                // Drop sub-300ms blobs — usually accidental taps
                if (blob.size < 1500) return;
                await self._transcribeAndSend(blob, mr.mimeType || mime || 'audio/webm');
            };
            mr.onerror = () => this._stopVoice();
            mr.start();
        }

        /**
         * Upload a recorded audio blob to /ai/transcribe, then route the
         * transcript through _send() so it appears as a normal user message.
         */
        async _transcribeAndSend(blob, mimetype) {
            const self = this;
            // Show a placeholder so the user sees something is happening
            const ph = document.createElement('div');
            ph.className = 'beena-msg beena-msg-user beena-voice-transcribing';
            ph.dir = this.lang === 'ar' ? 'rtl' : 'ltr';
            ph.innerHTML = '<span class="beena-pay-spinner" style="margin-right:6px"></span>' +
                           this._t('Transcribing…', 'جاري التفريغ…');
            this.messagesEl.appendChild(ph);
            this._scrollBottom();

            try {
                const b64 = await new Promise((resolve, reject) => {
                    const r = new FileReader();
                    r.onload  = () => resolve(String(r.result).split(',')[1] || '');
                    r.onerror = reject;
                    r.readAsDataURL(blob);
                });
                const r = await fetch('/ai/transcribe', {
                    method:  'POST',
                    headers: {'Content-Type':'application/json'},
                    body:    JSON.stringify({jsonrpc:'2.0',method:'call',id:1,params:{
                        audio: b64, mimetype, lang: self.lang === 'ar' ? 'ar' : 'en',
                    }}),
                });
                const j = await r.json();
                const res = (j && j.result) || {};
                ph.remove();
                if (res.success && res.text) {
                    // Voice in → voice out: opt the user in so the next AI
                    // reply auto-speaks without requiring a prior Listen tap.
                    try { localStorage.setItem('beena_voice_opted_in', '1'); } catch (e) {}
                    self._send(res.text);
                    return;
                }
                // Surface the actual reason — most often the master switch is
                // off or the cap was reached, which is recoverable info.
                var reason = res.error || '';
                var humanAR = 'تعذّر تفريغ الصوت. حاول مرة ثانية أو اكتب رسالتك.';
                var humanEN = 'I could not transcribe that. Please try again or type your message.';
                if (reason === 'voice_disabled') {
                    humanAR = 'الصوت غير مفعّل. فعّله من إعدادات Beena → Voice.';
                    humanEN = 'Voice is disabled. Enable it from Beena Settings → Voice.';
                } else if (reason === 'monthly_cap_reached' || reason === 'customer_cap_reached') {
                    humanAR = 'تجاوزت الحد الشهري للصوت. حاول لاحقاً أو اكتب رسالتك.';
                    humanEN = 'Voice monthly limit reached. Try later or type your message.';
                } else if (reason === 'no_provider_enabled') {
                    humanAR = 'لا يوجد مزود صوت مفعّل. تحقق من الإعدادات.';
                    humanEN = 'No voice provider is enabled. Check settings.';
                }
                self._addAIMessage(self._t(humanEN, humanAR), 'sad');
            } catch (e) {
                ph.remove();
                self._addAIMessage(self._t(
                    'Transcription failed.', 'فشل التفريغ.'), 'sad');
            }
        }

        /**
         * Phase B — open a live voice call. Fetches an ephemeral token from
         * /ai/voice/realtime_token, then opens a WebSocket / WebRTC session
         * with OpenAI Realtime or ElevenLabs Convo AI. Displays a dialog
         * with a waveform and elapsed timer.
         */
        async _startVoiceCall() {
            const self = this;
            const t = (en, ar) => self._t(en, ar);
            if (!self.config || !self.config.voice_enabled || !self.config.voice_phase_b) {
                self._addAIMessage(t('Voice Call is not enabled yet.',
                                     'المكالمة الصوتية غير مفعّلة بعد.'), 'sad');
                return;
            }

            // Fetch handshake
            let token;
            try {
                const r = await fetch('/ai/voice/realtime_token', {
                    method: 'POST',
                    headers:{'Content-Type':'application/json'},
                    body:   JSON.stringify({jsonrpc:'2.0',method:'call',id:1,params:{}}),
                });
                token = ((await r.json()).result) || {};
            } catch (e) { token = {success: false}; }
            if (!token.success) {
                self._addAIMessage(t('Voice Call is unavailable right now.',
                                     'المكالمة الصوتية غير متاحة حالياً.'), 'sad');
                return;
            }

            // UI: dialog with mic + waveform + timer + end button
            const ovr = self._openDialog({
                title: t('Voice Call with Beena', 'مكالمة صوتية مع بينا'),
                html: `
                    <div class="beena-vc-wrap">
                        <div class="beena-vc-ring"><div class="beena-vc-pulse"></div>🎙</div>
                        <div class="beena-vc-status" data-role="status">${self._escapeHTML(t('Connecting…','جاري الاتصال…'))}</div>
                        <div class="beena-vc-timer" data-role="timer">00:00</div>
                        <button class="beena-vc-end" data-action="end">${t('End call', 'إنهاء المكالمة')}</button>
                    </div>`,
                onClose: () => { try { self._endVoiceCall(); } catch(e){} },
            });
            const $status = ovr.querySelector('[data-role="status"]');
            const $timer  = ovr.querySelector('[data-role="timer"]');
            ovr.querySelector('[data-action="end"]').addEventListener('click', () => {
                try { self._endVoiceCall(); } catch(e){}
                if (ovr._beenaClose) ovr._beenaClose();
            });

            // Provider-specific wire-up. For OpenAI Realtime we use WebRTC
            // with the ephemeral client_secret (recommended path), so audio
            // negotiation is browser-native.
            self._voiceCall = {provider: token.provider, startedAt: Date.now()};
            const maxMs = (token.max_seconds || 300) * 1000;
            self._voiceCall.maxTimer = setTimeout(() => {
                try { self._endVoiceCall(); } catch(e){}
                if (ovr._beenaClose) ovr._beenaClose();
            }, maxMs);

            // Timer tick
            self._voiceCall.tickTimer = setInterval(() => {
                const s = Math.floor((Date.now() - self._voiceCall.startedAt) / 1000);
                const mm = String(Math.floor(s/60)).padStart(2,'0');
                const ss = String(s%60).padStart(2,'0');
                if ($timer) $timer.textContent = mm + ':' + ss;
            }, 1000);

            try {
                if (token.provider === 'openai') {
                    await self._voiceCallOpenAI(token, $status);
                } else if (token.provider === 'eleven') {
                    await self._voiceCallEleven(token, $status);
                } else {
                    throw new Error('unknown_provider');
                }
                if ($status) $status.textContent = t('Speak now — Beena is listening.', 'تحدّث الآن — بينا تستمع.');
            } catch (e) {
                if ($status) $status.textContent = t('Could not start the call.', 'تعذّر بدء المكالمة.');
            }
        }

        /**
         * OpenAI Realtime via WebRTC. Browser opens a peer connection with
         * a single audio track in/out + a data channel for the JSON events.
         */
        async _voiceCallOpenAI(token, $status) {
            const stream = await navigator.mediaDevices.getUserMedia({audio: true});
            const pc = new RTCPeerConnection();
            this._voiceCall.pc = pc;
            this._voiceCall.stream = stream;
            const audioEl = new Audio();
            audioEl.autoplay = true;
            this._voiceCall.audioEl = audioEl;
            pc.ontrack = (e) => { audioEl.srcObject = e.streams[0]; };
            stream.getAudioTracks().forEach(tr => pc.addTrack(tr, stream));
            const dc = pc.createDataChannel('oai-events');
            this._voiceCall.dc = dc;
            const offer = await pc.createOffer();
            await pc.setLocalDescription(offer);
            const r = await fetch(token.ws_url.replace('wss:', 'https:').replace('/?model=', '?model='),
                                  {method:'POST', body: offer.sdp,
                                   headers:{Authorization: 'Bearer ' + token.client_secret,
                                            'Content-Type':'application/sdp'}});
            const answerSdp = await r.text();
            await pc.setRemoteDescription({type:'answer', sdp: answerSdp});
        }

        /** ElevenLabs Convo AI — WebSocket-based agent. */
        async _voiceCallEleven(token, $status) {
            const stream = await navigator.mediaDevices.getUserMedia({audio: true});
            this._voiceCall.stream = stream;
            const ws = new WebSocket(token.signed_url);
            this._voiceCall.ws = ws;
            ws.onmessage = (ev) => {
                try {
                    const msg = JSON.parse(ev.data);
                    if (msg.audio_event && msg.audio_event.audio_base_64) {
                        const audio = new Audio('data:audio/mpeg;base64,' + msg.audio_event.audio_base_64);
                        audio.play();
                    }
                } catch(e) {}
            };
        }

        _endVoiceCall() {
            const v = this._voiceCall;
            if (!v) return;
            if (v.maxTimer)  clearTimeout(v.maxTimer);
            if (v.tickTimer) clearInterval(v.tickTimer);
            if (v.pc) try { v.pc.close(); } catch(e){}
            if (v.ws) try { v.ws.close(); } catch(e){}
            if (v.stream) try { v.stream.getTracks().forEach(t => t.stop()); } catch(e){}
            if (v.audioEl) try { v.audioEl.pause(); v.audioEl.srcObject = null; } catch(e){}
            this._voiceCall = null;
        }

        // Floating bubble showing elapsed recording time (WhatsApp-style)
        _showRecordingBubble() {
            this._hideRecordingBubble();
            const bubble = document.createElement('div');
            bubble.id = 'beena-rec-bubble';
            bubble.className = 'beena-rec-bubble';
            const startTs = Date.now();
            const fmt = (ms) => {
                const s = Math.floor(ms / 1000);
                const mm = String(Math.floor(s / 60)).padStart(2, '0');
                const ss = String(s % 60).padStart(2, '0');
                return mm + ':' + ss;
            };
            bubble.innerHTML = `
                <span class="beena-rec-dot"></span>
                <span class="beena-rec-time">00:00</span>
                <span class="beena-rec-hint">${this.lang === 'ar' ? '← اسحب للأعلى للإلغاء' : '← slide up to cancel'}</span>
            `;
            // Anchor above the input row
            const inputRow = document.getElementById('beena-input-row');
            if (inputRow && inputRow.parentNode) {
                inputRow.parentNode.insertBefore(bubble, inputRow);
            } else {
                this.messagesEl && this.messagesEl.appendChild(bubble);
            }
            const timeEl = bubble.querySelector('.beena-rec-time');
            this._recTimer = setInterval(() => {
                if (timeEl) timeEl.textContent = fmt(Date.now() - startTs);
            }, 200);
        }

        _hideRecordingBubble() {
            const b = document.getElementById('beena-rec-bubble');
            if (b) b.remove();
            if (this._recTimer) { clearInterval(this._recTimer); this._recTimer = null; }
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
                        <img src="${base64}" alt="${this._t('Search image', 'صورة البحث')}"
                             style="max-width:140px;max-height:140px;border-radius:8px;display:block;margin-bottom:4px">
                        <span style="font-size:10px;opacity:.8">🔍 ${this._t('Searching by image…', 'جاري البحث بالصورة…')}</span>`;
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
            // Per-bubble direction follows the typed content (page lang may differ)
            const isRTL = /[؀-ۿݐ-ݿ]/.test(text || '');
            div.classList.add(isRTL ? 'beena-rtl' : 'beena-ltr');
            div.setAttribute('dir', isRTL ? 'rtl' : 'ltr');
            div.textContent = text;
            this.messagesEl.appendChild(div);
            this._scrollBottom();
            // Save to history
            this._msgHistory.push({type: 'user', text});
            saveHistory(this._msgHistory);
            // Keep the composer mirroring the user's typing language so the
            // next message stays comfortable to type even if the page is EN.
            if (this.chatEl) {
                this.chatEl.classList.toggle('beena-input-rtl', isRTL);
            }
        }

        _addAIMessage(text, state, chips) {
            const div     = document.createElement('div');
            div.className = 'beena-msg beena-msg-ai';

            // Per-message direction: detect Arabic letters anywhere in the text
            // and flip the bubble — works even when the page is in English.
            const isRTL = /[؀-ۿݐ-ݿ]/.test(text || '');
            div.classList.add(isRTL ? 'beena-rtl' : 'beena-ltr');
            div.setAttribute('dir', isRTL ? 'rtl' : 'ltr');

            // Wrap text + play button. Skip TTS for very short or empty text.
            const textWrap = document.createElement('div');
            textWrap.className = 'beena-msg-text';
            textWrap.innerHTML = this._formatText(text);
            div.appendChild(textWrap);

            if (text && text.replace(/[\s\W]+/g, '').length > 2) {
                const playBtn = document.createElement('button');
                playBtn.type = 'button';
                playBtn.className = 'beena-tts-btn';
                playBtn.dataset.state = 'paused';
                playBtn.title = this.lang === 'ar' ? 'استمع' : 'Listen';
                playBtn.setAttribute('aria-label', this.lang === 'ar' ? 'تشغيل صوت الرد' : 'Play reply audio');
                // Play icon + label — toggled to Pause inside _speak()
                playBtn.innerHTML =
                    '<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M8 5v14l11-7z"/></svg>' +
                    '<span>' + (this.lang === 'ar' ? 'استمع' : 'Listen') + '</span>';
                playBtn.addEventListener('click', () => this._speak(text, playBtn, isRTL));
                div.appendChild(playBtn);
            }

            if (chips && chips.length) {
                const chipWrap = document.createElement('div');
                chipWrap.className = 'beena-chips';
                chips.forEach(chip => {
                    const btn       = document.createElement('button');
                    btn.className   = 'beena-chip';
                    btn.textContent = chip;
                    btn.addEventListener('click', () => { if (['العربية','English','لغة أخرى / Other'].indexOf(chip) > -1) { this._setBeenaLang(chip); } else { this._send(chip); } });
                    chipWrap.appendChild(btn);
                });
                div.appendChild(chipWrap);
            }

            // Auto-inject a Sign-in button when Beena's reply asks the user
            // to log in. Pattern is loose-but-safe — only triggers on phrases
            // strongly tied to authentication. Beena will resume the flow
            // automatically once the user signs in (see _openSignInDialog).
            const lc = String(text || '').toLowerCase();
            const askLogin = /(sign\s*in|please\s*log\s*in|please\s*sign\s*in|first\s*then|need\s*to\s*login|need\s*to\s*log\s*in)/i.test(lc)
                          || /(سجّل\s*دخول|سجل\s*دخول|سجّلي\s*دخول|سجلي\s*دخول|تسجيل\s*الدخول|سجل\s*الدخول\s*أولاً|اعملي\s*تسجيل|قم\s*بتسجيل)/i.test(text || '');
            if (askLogin && !div.querySelector('[data-action="beena-signin"]')) {
                const sb = document.createElement('button');
                sb.type = 'button';
                sb.className = 'beena-signin-btn';
                sb.setAttribute('data-action', 'beena-signin');
                sb.style.marginTop = '8px';
                sb.innerHTML = '🔑 ' + (this.lang === 'ar' ? 'سجّل دخولك في نافذة' : 'Sign in here');
                sb.addEventListener('click', () => this._openSignInDialog('/web/login'));
                div.appendChild(sb);
            }

            // Wire up image lightbox + safe link rel attrs
            div.querySelectorAll('img.beena-rich-img').forEach(img => {
                img.addEventListener('click', () => this._openLightbox(img.src));
            });

            this.messagesEl.appendChild(div);
            this._scrollBottom();
            // Save to history
            this._msgHistory.push({type: 'ai', text, chips: chips || []});
            saveHistory(this._msgHistory);

            // Bump unread badge when the panel is closed
            if (!this.isOpen) {
                this._unread = (this._unread || 0) + 1;
                this._renderUnreadBadge();
            }

            // Auto-speak — but ONLY for newly arrived live messages.
            //
            //   ❌  Skip when replaying history on panel open  (this._isRestoring)
            //   ❌  Skip when the panel is closed              (would speak in the background)
            //   ✅  Only when the user has opted in once       (localStorage flag)
            //   ✅  Only when both master switches are on
            //
            // We also debounce: if several AI bubbles arrive in the same turn
            // we cancel earlier queued auto-plays so only the LATEST is spoken
            // — otherwise overlapping fetches would talk over each other.
            try {
                if (!this._isRestoring
                    && this.isOpen
                    && this.config && this.config.voice_enabled
                    && this.config.voice_autoplay
                    && localStorage.getItem('beena_voice_opted_in') === '1') {
                    const playBtn = div.querySelector('.beena-tts-btn');
                    if (playBtn) {
                        // Cancel any auto-play queued from a prior bubble in
                        // the same turn — only the latest reply should speak.
                        if (this._autoplayTimer) {
                            clearTimeout(this._autoplayTimer);
                            this._autoplayTimer = null;
                        }
                        const self = this;
                        this._autoplayTimer = setTimeout(function () {
                            self._autoplayTimer = null;
                            self._speak(text, playBtn, isRTL);
                        }, 250);
                    }
                }
            } catch (e) { /* localStorage may be blocked */ }
        }

        _renderUnreadBadge() {
            if (!this.floatEl) return;
            let badge = this.floatEl.querySelector('.beena-unread-badge');
            const count = this._unread || 0;
            if (!count) {
                if (badge) badge.remove();
                return;
            }
            if (!badge) {
                badge = document.createElement('span');
                badge.className = 'beena-unread-badge';
                this.floatEl.appendChild(badge);
            }
            badge.textContent = count > 99 ? '99+' : String(count);
        }

        /**
         * Speak the given text. When server-side voice is configured, calls
         * /ai/tts and plays the returned audio via <audio>. Falls back to
         * window.speechSynthesis when the server stack is off or fails.
         *
         * Server-side path supports play/pause, caching, and any of the four
         * configured providers (router decides). Browser-side path is the
         * degraded fallback that still works without API keys.
         */
        async _speak(text, button, forceRTL) {
            const isAR = !!forceRTL || /[؀-ۿݐ-ݿ]/.test(text || '');
            const useServer = this.config && this.config.voice_enabled && this.config.voice_phase_a;
            // Remember the user opted into voice — this enables auto-play
            // for subsequent assistant replies in this browser.
            try { localStorage.setItem('beena_voice_opted_in', '1'); } catch (e) {}

            // Clean up any previous playback / synthesis owned by this app.
            const setBtnState = (state) => {
                if (!button) return;
                button.dataset.state = state;
                button.classList.toggle('beena-tts-playing', state === 'playing');
                if (state === 'playing') {
                    button.innerHTML =
                        '<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M6 5h4v14H6zM14 5h4v14h-4z"/></svg>' +
                        '<span>' + (this.lang === 'ar' ? 'إيقاف' : 'Pause') + '</span>';
                } else {
                    button.innerHTML =
                        '<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M8 5v14l11-7z"/></svg>' +
                        '<span>' + (this.lang === 'ar' ? 'استمع' : 'Listen') + '</span>';
                }
            };

            // Toggle behaviour — same button while playing → pause/stop
            if (this._ttsButton === button) {
                if (this._ttsAudio) { try { this._ttsAudio.pause(); } catch(e){} this._ttsAudio = null; }
                if (window.speechSynthesis && window.speechSynthesis.speaking) {
                    try { window.speechSynthesis.cancel(); } catch(e){}
                }
                this._ttsButton = null;
                setBtnState('paused');
                return;
            }
            // Stop anything else first
            if (this._ttsAudio) { try { this._ttsAudio.pause(); } catch(e){} this._ttsAudio = null; }
            if (window.speechSynthesis && window.speechSynthesis.speaking) {
                try { window.speechSynthesis.cancel(); } catch(e){}
            }
            if (this._ttsButton) {
                const old = this._ttsButton;
                this._ttsButton = null;
                old.classList.remove('beena-tts-playing');
                old.dataset.state = 'paused';
                const lbl2 = old.querySelector('span');
                if (lbl2) lbl2.textContent = this.lang === 'ar' ? 'استمع' : 'Listen';
            }

            // ── Server-side path (preferred) ─────────────────────────────
            if (useServer) {
                try {
                    setBtnState('playing'); // optimistic — show pause immediately
                    this._ttsButton = button;
                    const r = await fetch('/ai/tts', {
                        method:  'POST',
                        headers: {'Content-Type':'application/json'},
                        body:    JSON.stringify({jsonrpc:'2.0',method:'call',id:1,params:{
                            text, lang: isAR ? 'ar' : 'en',
                        }}),
                    });
                    const j = await r.json();
                    const res = (j && j.result) || {};
                    if (res.success && res.audio) {
                        const mime = res.mimetype || 'audio/mpeg';
                        const audio = new Audio('data:' + mime + ';base64,' + res.audio);
                        this._ttsAudio = audio;
                        audio.onended = audio.onerror = () => {
                            if (this._ttsAudio === audio) {
                                this._ttsAudio = null;
                                this._ttsButton = null;
                                setBtnState('paused');
                            }
                        };
                        await audio.play();
                        return;
                    }
                    // Fall through to browser TTS on server failure
                    _logger_warn('voice', 'server tts failed:', res.error);
                } catch (e) {
                    _logger_warn('voice', 'server tts error:', e);
                    this._ttsButton = null;
                    setBtnState('paused');
                }
            }

            // ── Browser fallback (Web Speech API) ─────────────────────────
            const synth = window.speechSynthesis;
            if (!synth) return;
            // Aggressively clean the text for speech:
            //   - drop HTML tags
            //   - drop emoji (incl. ZWJ sequences)
            //   - drop markdown noise (**, __, `, ~~, > , #)
            //   - condense whitespace
            const plain = String(text || '')
                .replace(/<[^>]+>/g, ' ')
                .replace(/[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}\u{1F000}-\u{1F2FF}️‍]/gu, '')
                .replace(/[*_~`>#]+/g, ' ')
                .replace(/\s+/g, ' ')
                .trim();
            if (!plain) return;

            // isAR is already declared at the top of the function; the
            // fallback path uses the same detection.
            const utt = new SpeechSynthesisUtterance(plain);
            const voices = synth.getVoices() || [];

            const pickVoice = (langPrefix) => {
                // Prefer Google/Microsoft/Apple natural voices, in this order
                const score = (v) => {
                    const n = (v.name || '').toLowerCase();
                    let s = 0;
                    if ((v.lang || '').toLowerCase().startsWith(langPrefix)) s += 10;
                    if (/google/.test(n))     s += 5;
                    if (/microsoft|natural|neural/.test(n)) s += 4;
                    if (/(female|amira|salma|zayda|samia|aisha|nayf|jenny|aria)/.test(n)) s += 3;
                    if (/(remote|enhanced)/.test(n)) s += 2;
                    return s;
                };
                const matching = voices.filter(v => (v.lang || '').toLowerCase().startsWith(langPrefix));
                if (matching.length) {
                    matching.sort((a, b) => score(b) - score(a));
                    return matching[0];
                }
                return null;
            };

            const v = pickVoice(isAR ? 'ar' : 'en') || pickVoice('en') || voices[0];
            if (v) {
                utt.voice = v;
                utt.lang  = v.lang;
            } else {
                utt.lang = isAR ? 'ar-SA' : 'en-US';
            }
            // A little slower than default + slightly higher pitch reads more
            // naturally on both Arabic and English voices.
            utt.rate   = isAR ? 0.92 : 1.0;
            utt.pitch  = 1.05;
            utt.volume = 1.0;

            utt.onstart = () => {
                this._ttsButton = button;
                setBtnState('playing');
            };
            const done = () => {
                setBtnState('paused');
                if (this._ttsButton === button) this._ttsButton = null;
            };
            utt.onend   = done;
            utt.onerror = done;

            // Some browsers (Chrome) require voices to be loaded first
            if (!voices.length && synth.onvoiceschanged === null) {
                synth.onvoiceschanged = () => {
                    synth.onvoiceschanged = null;
                    synth.speak(utt);
                };
                return;
            }
            synth.speak(utt);
        }

        _openLightbox(src) {
            const existing = document.getElementById('beena-lightbox');
            if (existing) existing.remove();
            const overlay = document.createElement('div');
            overlay.id = 'beena-lightbox';
            overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.85);z-index:999999;display:flex;align-items:center;justify-content:center;cursor:zoom-out;padding:20px';
            overlay.innerHTML = `<img src="${src}" style="max-width:96vw;max-height:96vh;border-radius:8px;box-shadow:0 8px 32px rgba(0,0,0,0.5)">`;
            overlay.addEventListener('click', () => overlay.remove());
            document.body.appendChild(overlay);
        }

        /**
         * Generic modal dialog with custom HTML body + a title.
         * Returns the overlay element so callers can update its content.
         */
        _openDialog({title, html, onClose}) {
            const old = document.getElementById('beena-dialog');
            if (old) old.remove();
            const overlay = document.createElement('div');
            overlay.id = 'beena-dialog';
            overlay.className = 'beena-dialog-overlay';
            overlay.innerHTML = `
                <div class="beena-dialog" role="dialog" aria-modal="true">
                    <div class="beena-dialog-head">
                        <div class="beena-dialog-title">${this._escapeHTML(title || '')}</div>
                        <button class="beena-dialog-close" aria-label="Close">×</button>
                    </div>
                    <div class="beena-dialog-body">${html || ''}</div>
                </div>`;
            document.body.appendChild(overlay);
            const close = () => {
                overlay.remove();
                if (onClose) try { onClose(); } catch(e) {}
            };
            overlay.addEventListener('click', (e) => { if (e.target === overlay) close(); });
            overlay.querySelector('.beena-dialog-close').addEventListener('click', close);
            document.addEventListener('keydown', function esc(e) {
                if (e.key === 'Escape') { close(); document.removeEventListener('keydown', esc); }
            });
            overlay._beenaClose = close;
            return overlay;
        }

        /**
         * Open ANY internal Uellow URL in an iframe modal instead of leaving
         * the page. Used to keep the chat alive when the user clicks links.
         */
        _openInternalLink(url) {
            const safe = String(url || '');
            // Login/signup links → use the smarter sign-in dialog so we
            // can detect success and auto-continue Beena's flow.
            if (/^\/web\/(login|signup)/.test(safe)) {
                return this._openSignInDialog(safe);
            }
            this._openDialog({
                title: this._t('Loading…', 'جاري التحميل…'),
                html: `<iframe class="beena-dialog-iframe" src="${safe}" loading="lazy"
                              referrerpolicy="same-origin"></iframe>`,
            });
        }

        /**
         * Sign-in dialog: opens /web/login (or /web/signup) inside the chat
         * dialog and polls session-info every 2 seconds. When uid changes
         * from 0 (anonymous) to a real user, closes the dialog and notifies
         * Beena so she can resume whatever flow needed authentication.
         *
         * Bug fix: ticks queued before the first success-detection were each
         * firing `onLoggedIn` → which re-sent "Continue" in a tight loop.
         * The `handled` flag short-circuits any in-flight follow-up tick so
         * the resume runs exactly once per sign-in dialog.
         */
        _openSignInDialog(url) {
            const safe = String(url || '/web/login');
            const self = this;
            const t = (en, ar) => self._t(en, ar);
            // Capture the current uid so we know what "logged in" means.
            const beforeUid = (window.odoo && window.odoo.session_info && window.odoo.session_info.uid) || 0;

            // Local closure flag — one dialog, one resume, no matter how
            // many fetch ticks are in flight when login completes.
            let handled = false;
            let pollTimer = null;
            const stopPolling = () => {
                if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
                self._signinPoll = null;
            };

            const overlay = this._openDialog({
                title: t('Sign in', 'تسجيل الدخول'),
                html: `<iframe class="beena-dialog-iframe" src="${safe}" loading="lazy"
                              referrerpolicy="same-origin"></iframe>
                       <div class="beena-signin-status" data-role="status"></div>`,
                onClose: () => { stopPolling(); },
            });
            const $status = overlay.querySelector('[data-role="status"]');

            const onLoggedIn = (uid) => {
                if (handled) return;
                handled = true;
                stopPolling();
                if ($status) {
                    $status.style.padding = '10px';
                    $status.textContent = t('Signed in ✓ continuing…', 'تم تسجيل الدخول ✓ نكمل…');
                }
                setTimeout(() => {
                    if (overlay._beenaClose) overlay._beenaClose();
                    // Friendly resume message — no automatic "Continue" send,
                    // which previously fired repeatedly because each polling
                    // tick raced to call this branch.
                    self._addAIMessage(
                        t('Welcome back! What would you like to do next?',
                          'حياك! تحب نكمل من وين؟'),
                        'happy',
                        // Quick chips so the user picks the next step rather
                        // than us spamming the AI with auto "Continue" messages.
                        [
                            t('Continue', 'كمّلي'),
                            t('Try it on me', 'جرّبه عليّ'),
                            t('Check my size', 'افحص مقاسي'),
                        ],
                    );
                }, 600);
            };

            // Poll every 2 seconds — bounded to 5 minutes
            const start = Date.now();
            pollTimer = setInterval(async () => {
                if (handled) { stopPolling(); return; }
                if (Date.now() - start > 5 * 60 * 1000) { stopPolling(); return; }
                try {
                    const r = await fetch('/web/session/get_session_info', {
                        method:  'POST',
                        headers: {'Content-Type': 'application/json'},
                        body:    JSON.stringify({jsonrpc:'2.0',method:'call',id:1,params:{}}),
                    });
                    if (handled) return;          // a sibling tick already won
                    const j   = await r.json();
                    const uid = (j && j.result && j.result.uid) || 0;
                    if (uid && uid !== beforeUid && !handled) {
                        // Flip the flag BEFORE the next await/timeout, so any
                        // concurrent tick that resolves later bails out.
                        handled = true;
                        stopPolling();
                        onLoggedIn(uid);
                    }
                } catch (e) { /* keep polling silently */ }
            }, 2000);
            self._signinPoll = pollTimer;
        }

        /**
         * Product detail dialog. Fetches /ai/chat get_product_info?...
         * Falls back to opening the product page in iframe modal.
         */
        async _openProductDialog(productId) {
            // We just open the product page inside an iframe — full detail UI
            // (variants, gallery, add-to-cart) is already there.
            this._openInternalLink('/shop/product/' + productId);
        }

        /**
         * Quietly add a variant to the cart and re-render the inline cart card.
         */
        async _cartAddInline(variantId, productName) {
            const self = this;
            const t = (en, ar) => self._t(en, ar);
            try {
                // /shop/cart/update_json is the standard Odoo route
                const r = await fetch('/shop/cart/update_json', {
                    method:  'POST',
                    headers: {'Content-Type': 'application/json'},
                    body:    JSON.stringify({jsonrpc:'2.0',method:'call',id:1,
                                             params:{product_id: variantId, add_qty: 1}}),
                });
                const data = (await r.json()).result || {};
                // Render the same "added" card we use after Beena's add_to_cart tool
                self._showCartAdded({
                    success:     true,
                    product:     productName,
                    cart_count:  data.cart_quantity || 0,
                    cart_total:  data.amount_total  || 0,
                    cart_url:    '/shop/cart',
                });
                // Also auto-open the live cart card so they see qty controls
                const v = await self._jsonCall('/ai/cart_view', {});
                if (v) self._showCartView(v);
            } catch(e) {
                self._addAIMessage(t('Could not add to cart.', 'تعذّر الإضافة للسلة.'), 'sad');
            }
        }

        _escapeHTML(s) {
            return String(s == null ? '' : s)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#39;');
        }

        /**
         * Bilingual string helper. English is the source language, Arabic is the
         * translation. Returns the right one based on the current page lang.
         * Usage: this._t('Save', 'حفظ')
         */
        _t(en, ar) {
            if (en == null) return '';
            if (this.lang === 'ar' && ar) return ar;
            return en;
        }

        /**
         * Best-effort hex color from a color name (used when Odoo's product
         * attribute value has no html_color set). Covers the common Arabic
         * and English color names we see in the catalog.
         */
        _guessColorHex(name) {
            const n = String(name || '').trim().toLowerCase();
            if (!n) return '#cccccc';
            const map = {
                // English
                'black':'#111111','white':'#ffffff','red':'#e02b2b','blue':'#1f6feb',
                'green':'#1d9e75','yellow':'#f5c320','orange':'#ff7a18','purple':'#7c3aed',
                'pink':'#ec4899','brown':'#8b5a2b','gray':'#888888','grey':'#888888',
                'silver':'#c0c0c0','gold':'#d4af37','navy':'#0b2447','beige':'#f5f5dc',
                'cyan':'#22d3ee','magenta':'#d946ef','maroon':'#7f1d1d','olive':'#6b8e23',
                'tan':'#d2b48c','teal':'#0d9488','lime':'#84cc16',
                // Arabic
                'أسود':'#111111','اسود':'#111111','أبيض':'#ffffff','ابيض':'#ffffff',
                'أحمر':'#e02b2b','احمر':'#e02b2b','أزرق':'#1f6feb','ازرق':'#1f6feb',
                'أخضر':'#1d9e75','اخضر':'#1d9e75','أصفر':'#f5c320','اصفر':'#f5c320',
                'برتقالي':'#ff7a18','بنفسجي':'#7c3aed','وردي':'#ec4899','زهري':'#ec4899',
                'بني':'#8b5a2b','رمادي':'#888888','فضي':'#c0c0c0','ذهبي':'#d4af37',
                'كحلي':'#0b2447','بيج':'#f5f5dc','تركواز':'#0d9488','نيلي':'#3730a3',
            };
            return map[n] || '#cccccc';
        }

        _isSafeUrl(url) {
            const u = String(url || '').trim();
            if (!u) return false;
            return /^(https?:\/\/|\/|mailto:|tel:)/i.test(u) && !/^javascript:/i.test(u);
        }

        _isImageUrl(url) {
            return /\.(png|jpe?g|gif|webp|svg|avif)(\?.*)?$/i.test(url || '');
        }

        _formatText(text) {
            if (text == null) return '';
            let s = this._escapeHTML(text);

            // Image markdown:  ![alt](url)
            s = s.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, (m, alt, url) => {
                if (!this._isSafeUrl(url)) return m;
                return `<img src="${url}" alt="${this._escapeHTML(alt)}" class="beena-rich-img" loading="lazy">`;
            });

            // Link markdown:   [text](url)
            s = s.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (m, label, url) => {
                if (!this._isSafeUrl(url)) return m;
                return `<a href="${url}" target="_blank" rel="noopener" class="beena-rich-link">${this._escapeHTML(label)}</a>`;
            });

            // Bold:   **text**  or  __text__
            s = s.replace(/\*\*([^*\n]+)\*\*/g, '<strong>$1</strong>');
            s = s.replace(/__([^_\n]+)__/g, '<strong>$1</strong>');

            // Italic:  *text*  or  _text_   (avoid touching already-replaced bold)
            s = s.replace(/(^|[\s(])\*([^*\n]+)\*(?=[\s.,!?)]|$)/g, '$1<em>$2</em>');
            s = s.replace(/(^|[\s(])_([^_\n]+)_(?=[\s.,!?)]|$)/g, '$1<em>$2</em>');

            // Inline code:  `code`
            s = s.replace(/`([^`\n]+)`/g, '<code class="beena-rich-code">$1</code>');

            // Bullet lists:  lines starting with - or • or *
            s = s.replace(/(^|\n)([-•*])\s+(.+)(?=\n|$)/g, '$1<li>$3</li>');
            s = s.replace(/(<li>.+<\/li>)(?:\s*<br>\s*)+(?=<li>)/g, '$1');
            s = s.replace(/((?:<li>.+<\/li>\s*)+)/g, '<ul class="beena-rich-ul">$1</ul>');

            // Auto-link bare URLs (only ones not already in <a> or <img>)
            s = s.replace(
                /(^|[\s(>])(https?:\/\/[^\s<>"]+[^\s<>".,!?:;)])/g,
                (m, pre, url) => {
                    if (this._isImageUrl(url)) {
                        return `${pre}<img src="${url}" class="beena-rich-img" loading="lazy">`;
                    }
                    return `${pre}<a href="${url}" target="_blank" rel="noopener" class="beena-rich-link">${url}</a>`;
                }
            );

            // Newlines → <br> (but not inside lists)
            s = s.replace(/\n/g, '<br>');
            s = s.replace(/<\/ul>\s*<br>/g, '</ul>');
            s = s.replace(/<br>\s*<ul/g, '<ul');

            return s;
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
            const self = this;
            const t = (en, ar) => self._t(en, ar);
            const div = document.createElement('div');
            div.className = 'beena-msg beena-msg-ai';

            const stockBadge = (p) => {
                if (p.in_stock === false) {
                    return `<span class="beena-stock-badge out">● ${t('Out of stock', 'غير متوفر')}</span>`;
                }
                const qty = Number(p.qty_available || 0);
                if (qty > 0 && qty <= 5) {
                    return `<span class="beena-stock-badge low">● ${t('Low stock', 'مخزون قليل')} · ${qty}</span>`;
                }
                if (qty > 0) {
                    return `<span class="beena-stock-badge in">● ${t('In stock', 'متوفر')} · ${qty}</span>`;
                }
                if (p.continue_sell) {
                    return `<span class="beena-stock-badge cs">● ${t('Available on order', 'متوفر بالطلب')}</span>`;
                }
                return `<span class="beena-stock-badge in">● ${t('Available ✓', 'متوفر ✓')}</span>`;
            };

            // Compact variant summary for list view — replaces the full
            // colour/size chip rows (which clutter multi-product lists).
            // Three swatch dots + a count tell the customer "this comes in
            // several colours" without taking three lines per card.
            const variantSummary = (p) => {
                const parts = [];
                if (Array.isArray(p.colors) && p.colors.length) {
                    const dots = p.colors.slice(0, 3).map(c => {
                        const hex = (c.hex || '').trim() || self._guessColorHex(c.name);
                        return `<span class="beena-color-mini" style="background:${hex}" title="${self._escapeHTML(c.name)}"></span>`;
                    }).join('');
                    const more = p.colors.length > 3 ? `<span class="beena-variant-more">+${p.colors.length - 3}</span>` : '';
                    parts.push(`<span class="beena-variant-grp">${dots}${more}<span class="beena-variant-lbl">${p.colors.length} ${t('colors', 'لون')}</span></span>`);
                }
                if (Array.isArray(p.sizes) && p.sizes.length) {
                    parts.push(`<span class="beena-variant-grp"><span class="beena-variant-icon">📏</span><span class="beena-variant-lbl">${p.sizes.length} ${t('sizes', 'مقاس')}</span></span>`);
                }
                if (!parts.length) return '';
                return `<div class="beena-variant-summary">${parts.join('')}</div>`;
            };

            products.slice(0, 5).forEach(p => {
                const card = document.createElement('div');
                card.className = 'beena-product-card';
                const safeName = self._escapeHTML(p.name);
                card.innerHTML = `
                    <div style="display:flex;gap:10px;align-items:flex-start;width:100%">
                        <img src="${p.image_url || '/web/image/product.template/'+p.id+'/image_128'}"
                             alt="${safeName}" onerror="this.style.display='none'"
                             style="width:54px;height:54px;border-radius:7px;object-fit:cover;flex-shrink:0">
                        <div style="flex:1;min-width:0">
                            <div class="beena-product-name" style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${safeName}</div>
                            <div class="beena-product-price">${(p.price || 0).toFixed(3)} KD</div>
                            ${stockBadge(p)}
                        </div>
                        <div style="display:flex;flex-direction:column;gap:4px;flex-shrink:0">
                            <button class="beena-buy-btn" data-action="view"
                                    data-pid="${p.id}"
                                    style="font-size:10px;padding:3px 8px">${t('View', 'عرض')}</button>
                            ${p.in_stock !== false ? `<button class="beena-buy-btn" data-action="add"
                                    data-vid="${p.variant_id || p.id}"
                                    data-name="${safeName}"
                                    style="font-size:10px;padding:3px 8px;background:#1D9E75">
                                +${t('Cart', 'سلة')}</button>` : ''}
                        </div>
                    </div>
                    ${variantSummary(p)}`;
                // Wire programmatically so we control redirects / RPC
                card.querySelector('[data-action="view"]').addEventListener('click', () => {
                    self._openProductDialog(parseInt(card.querySelector('[data-action="view"]').dataset.pid, 10));
                });
                const addBtn = card.querySelector('[data-action="add"]');
                if (addBtn) addBtn.addEventListener('click', () => {
                    const vid  = parseInt(addBtn.dataset.vid, 10);
                    const name = addBtn.dataset.name;
                    self._cartAddInline(vid, name);
                });
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
            // Master nudge switch
            if (!this.config.nudge) return;

            // Mobile vs desktop split. Mobile heuristic = pointer:coarse OR <= 760px.
            const isMobile = window.matchMedia
                ? (window.matchMedia('(pointer: coarse)').matches || window.matchMedia('(max-width: 760px)').matches)
                : (window.innerWidth <= 760);

            // Per-device enable flags (default desktop on, mobile off)
            const enabled = isMobile
                ? (this.config.autoopen_mobile_enabled !== false)
                : (this.config.autoopen_desktop_enabled !== false);
            if (!enabled) return;

            // Per-device delay (seconds → ms)
            const baseDelay = isMobile
                ? (this.config.autoopen_mobile_seconds  || 120)
                : (this.config.autoopen_desktop_seconds || 60);
            const legacyDelay = this.config.nudge_delay || 30;
            const delay = Math.max(5, Math.min(3600, baseDelay || legacyDelay)) * 1000;

            // "open" = expand the panel; "message" = quiet background nudge with badge
            const mode = this.config.nudge_mode || 'message';

            clearTimeout(this.nudgeTimer);
            this.nudgeTimer = setTimeout(() => {
                if (this.isOpen || this._nudgeFired) return;
                this._nudgeFired = true;

                // Animated nudge class on the float button
                const anim = this.config.nudge_anim || 'bounce';
                this.floatEl.classList.add('nudge', `beena-anim-${anim}`);
                const label = document.getElementById('beena-float-label');
                if (label) label.textContent = this.lang === 'ar' ? 'عندك سؤال؟ 🐝' : 'Need help? 🐝';

                // Build the greeting once (used by both modes)
                const ctxName = document.getElementById('beena-context-name');
                const pName   = ctxName ? ctxName.textContent.trim() : '';
                const greetAR = pName
                    ? `أقدر أساعدك في شي يخصّ "${pName}"؟ اسألني عن المقاس، اللون، التوفّر، أو جرّبه افتراضياً ✨`
                    : 'أقدر أساعدك في شي يخصّ هذا المنتج؟ اسألني عن المقاس، اللون، التوفّر، أو جرّبه افتراضياً ✨';
                const greetEN = pName
                    ? `Can I help you with "${pName}"? Ask about size, color, stock, or try it on virtually ✨`
                    : 'Can I help you with this product? Ask about size, color, stock, or try it on virtually ✨';
                const greet = this.lang === 'ar' ? greetAR : greetEN;

                if (mode === 'open' && this.productId) {
                    // Classic behaviour: pop the panel open
                    this.open(this.productId);
                    setTimeout(() => {
                        if (this.config.nudge_message === false) return;
                        this._addAIMessage(greet, 'happy');
                    }, 250);
                } else {
                    // Background "message" mode — type into the closed panel,
                    // bump the unread badge, animate the float button.
                    if (this.messagesEl.children.length === 0) {
                        this._showWelcome();
                    }
                    this._addAIMessage(greet, 'happy');
                    this._unread = (this._unread || 0) + 1;
                    this._renderUnreadBadge();
                }
            }, delay);
        }
    }

    // Expose the class so out-of-scope prototype extensions (Phase 2+) work.
    window.BeenaApp = BeenaApp;

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

        // Bilingual: EN primary + AR translation
        const rawLang = (document.documentElement.lang || '').toLowerCase();
        const isAR    = rawLang.startsWith('ar');

        const btn = document.createElement('button');
        btn.className   = 'beena-buy-ai-btn';
        btn.type        = 'button';
        // PHASE 14c — render as a card (icon circle + title + sub + arrow)
        // matching the "Ask Beena" card in the reviewers dialog so the look
        // is consistent across Beena entry points.
        const arrow = isAR ? '←' : '→';
        const title = isAR ? 'اشترِ بمساعدة Beena' : 'Shop with Beena AI';
        const sub   = isAR ? 'إرشاد ذكي لخطوات الشراء — بدون احتكاك'
                           : 'Smart guidance through checkout — zero friction';
        btn.innerHTML =
            '<span class="bw-icon" aria-hidden="true">🐝</span>' +
            '<span class="bw-body">' +
                '<span class="bw-title">' + title + '</span>' +
                '<span class="bw-sub">' + sub + '</span>' +
            '</span>' +
            '<span class="bw-arrow" aria-hidden="true">' + arrow + '</span>';
        btn.addEventListener('click', async (e) => {
            e.preventDefault();
            e.stopPropagation();
            const app = window._beenaApp;
            if (!app) return;

            // Capture product name for a nicer pre-filled message
            let pname = '';
            const nameEl = document.querySelector(
                '#product_details h1, h1[itemprop="name"], .product_name, h1.product-name'
            );
            if (nameEl) pname = nameEl.textContent.trim().replace(/\s+/g, ' ');

            // Open the panel (loads history if any), then send the buy intent
            await app.open(pid);
            const msg = isAR
                ? (pname ? `أرغب في شراء "${pname}"، ساعديني من فضلك.`
                         : 'أرغب في شراء هذا المنتج، ساعديني من فضلك.')
                : (pname ? `I'd like to buy "${pname}". Please help me through it.`
                         : "I'd like to buy this product. Please help me through it.");
            // Defer one tick so the welcome / restored history settles first
            setTimeout(() => app._send(msg), 250);
        });

        // PHASE 14c — mount the Buy with AI card UNDER the CTA row, not
        // inline next to Add to Cart, so it reads as its own offer (like
        // the Ask Beena card in the reviewers dialog).
        const ctaWrap = document.getElementById('o_wsale_cta_wrapper')
                     || addToCart.closest('#o_wsale_cta_wrapper');
        if (ctaWrap && ctaWrap.parentNode) {
            ctaWrap.parentNode.insertBefore(btn, ctaWrap.nextSibling);
        } else {
            addToCart.parentNode.insertBefore(btn, addToCart.nextSibling);
        }
    }

    function _getProductId() {
        // Odoo 18: <html data-main-object="product.template(1834,)">
        const main = document.querySelector('[data-main-object^="product.template("]');
        if (main) {
            const m = main.getAttribute('data-main-object').match(/\((\d+)/);
            if (m) return parseInt(m[1], 10);
        }

        // URL pattern: /shop/product/name-123 (also /ar/shop/product/...)
        const u = location.pathname.match(/\/shop\/product\/[^/]*?-(\d+)(\/|$|\?)/);
        if (u) return parseInt(u[1], 10);

        // Data attribute on any element
        const el = document.querySelector('[data-product-id]');
        if (el) return parseInt(el.dataset.productId, 10);

        // Hidden input forms
        const input = document.querySelector('input[name="product_template_id"], input[name="product_id"]');
        if (input) return parseInt(input.value, 10);

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

        // Auto-detect the current product so Beena recognizes it even when
        // the user opens her via the float button (not just Buy-with-AI).
        const detectedPid = _getProductId();
        if (detectedPid) {
            app.productId = detectedPid;
        }

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

    // Defer init until: user interacts OR idle callback fires OR 4s passed.
    // Removes ~1MB of JS work from the critical render path on first paint.
    let _beenaStarted = false;
    function _boot() {
        if (_beenaStarted) return;
        _beenaStarted = true;
        if (shouldRun()) init();
    }
    function _scheduleBoot() {
        if (!shouldRun()) return;
        // Boot on first real user interaction
        const evts = ['mousemove', 'touchstart', 'scroll', 'keydown', 'click'];
        const once = () => { evts.forEach(e =>
            window.removeEventListener(e, once, {passive: true})); _boot(); };
        evts.forEach(e => window.addEventListener(e, once, {passive: true}));
        // Fallback: requestIdleCallback / setTimeout 4s, so non-interactive
        // visitors still get the widget (e.g. tabbed-away then comes back).
        if ('requestIdleCallback' in window) {
            requestIdleCallback(_boot, { timeout: 4000 });
        } else {
            setTimeout(_boot, 4000);
        }
    }
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', _scheduleBoot);
    } else {
        _scheduleBoot();
    }


/* ── Phase 2 additions (appended) ── */
(function(){
    // NOTE: the class `BeenaApp` is a local of the first IIFE; it is exposed
    // on window. Always access it via window.BeenaApp from here on.

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
            const self = this;
            const t = (en, ar) => self._t(en, ar);
            const div = document.createElement('div');
            div.className = 'beena-msg beena-msg-ai beena-order-track';

            const steps = Array.isArray(status.timeline) ? status.timeline : [];
            const stepsHtml = steps.map((s, i) => `
                <div class="beena-track-step ${s.status}">
                    <div class="beena-track-dot">${s.icon || ''}</div>
                    <div class="beena-track-label">${self._escapeHTML(s.label)}</div>
                </div>
                ${i < steps.length - 1 ? `<div class="beena-track-bar ${steps[i+1].status === 'pending' ? 'pending' : 'done'}"></div>` : ''}
            `).join('');

            const driverRow = (status.driver && status.delivery_key === 'assigned') || status.driver_phone
                ? `<div class="beena-track-driver">
                       <span>🧑‍✈️ ${self._escapeHTML(status.driver || t('Driver assigned','تم تعيين سائق'))}</span>
                       ${status.driver_phone ? `<a href="tel:${self._escapeHTML(status.driver_phone)}" class="beena-track-call">📞 ${self._escapeHTML(status.driver_phone)}</a>` : ''}
                   </div>` : '';

            const trackingRow = status.tracking_number
                ? `<div class="beena-track-tracking">${t('Tracking #', 'رقم الشحنة')}: <strong>${self._escapeHTML(status.tracking_number)}</strong></div>` : '';

            const etaRow = status.eta
                ? `<div class="beena-track-eta">⏱ ${self._escapeHTML(status.eta)}</div>` : '';

            const cur = status.currency || 'KD';
            div.innerHTML = `
                <div class="beena-track-head">
                    <div>
                        <div class="beena-track-name">📦 ${self._escapeHTML(status.order_name||'')}</div>
                        <div class="beena-track-meta">
                            <span>${self._escapeHTML(status.date_order || '')}</span>
                            <span class="beena-track-amount">${(status.amount||0).toFixed(3)} ${cur}</span>
                        </div>
                    </div>
                    <span class="beena-track-state ${status.is_failed ? 'failed' : status.is_delivered ? 'done' : 'active'}">
                        ${self._escapeHTML(status.delivery_status || status.state || '')}
                    </span>
                </div>
                <div class="beena-track-timeline">
                    ${stepsHtml}
                </div>
                ${driverRow}
                ${trackingRow}
                ${etaRow}
                <div class="beena-cart-actions" style="margin-top:9px">
                    <a href="${status.order_url || '/my/orders'}" class="beena-cart-btn beena-cart-btn-link">
                        📋 ${t('Full order details', 'تفاصيل الطلب')}
                    </a>
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
      <div style="font-size:13px;font-weight:700;color:#1A1A1A">${(data.points||0).toLocaleString()} نقطة</div>${data.tier ? `<div style="font-size:12px;font-weight:600;color:#7A5C00;margin-top:2px">${({bronze:'🥉 برونزي',silver:'🥈 فضي',gold:'🥇 ذهبي',platinum:'💎 بلاتيني'})[data.tier] || data.tier}</div>` : ''}
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
            const self = this;
            const t = (en, ar) => self._t(en, ar);
            const results = data.results.slice(0, 4);
            const rec     = results.find(r => r.recommended);

            const div     = document.createElement('div');
            div.className = 'beena-msg beena-msg-ai';

            const colorMap = {green:'#E1F5EE', yellow:'#FEFDF0', orange:'#FAEEDA', red:'#FCEBEB'};
            const textMap  = {green:'#085041', yellow:'#854F0B', orange:'#633806', red:'#791F1F'};

            // Localize fit_label (server sends Arabic)
            const fitLabelMap = {
                'مناسب تماماً': 'Perfect fit',
                'مناسب':        'Good fit',
                'مقبول':        'Acceptable',
                'غير مناسب':    'Poor fit',
            };

            let html = `<div style="font-size:12px;font-weight:600;color:#1A1A1A;margin-bottom:7px">📏 ${t('Size recommendation', 'توصية المقاس')}</div>`;

            if (rec) {
                const fl = t(fitLabelMap[rec.fit_label] || rec.fit_label, rec.fit_label);
                html += `<div style="background:${colorMap[rec.fit_color]};border-radius:8px;padding:8px 11px;margin-bottom:7px">
                    <div style="font-size:12px;font-weight:700;color:${textMap[rec.fit_color]}">
                        ${t('Size', 'مقاس')} ${rec.size} — ${fl}
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

        // ── Virtual Try-On card ────────────────────────────────────────────
        window.BeenaApp.prototype._showTryOn = function(data) {
            if (!data) return;
            const self  = this;
            const state = data.state || 'error';
            const pid   = data.product_id;
            const t = (en, ar) => self._t(en, ar);

            const div   = document.createElement('div');
            div.className = 'beena-msg beena-msg-ai beena-tryon-card';
            div.dataset.tryonProduct = pid || '';

            const header = `
                <div class="beena-tryon-head">
                    <div class="beena-tryon-icon">🎨</div>
                    <div class="beena-tryon-titles">
                        <div class="beena-tryon-title">${t('Virtual Try-On', 'التجربة الافتراضية')}</div>
                        <div class="beena-tryon-sub">${t('Try the product on yourself before buying', 'جرّب المنتج عليك قبل ما تشتري')}</div>
                    </div>
                </div>`;

            const msg = data.message
                ? `<div class="beena-tryon-msg">${this._escapeHTML(data.message)}</div>` : '';

            // ─── Passive states: just message + header ───
            const passive = ['disabled', 'needs_login', 'no_product', 'not_eligible',
                             'cap_reached', 'product_not_found', 'error'];
            if (passive.includes(state)) {
                let extra = '';
                if (state === 'needs_login') {
                    extra = `<button type="button" data-action="beena-signin" class="beena-tryon-btn beena-tryon-btn-primary">🔑 ${t('Sign in', 'سجّل دخولك')}</button>`;
                }
                div.innerHTML = header + msg + extra;
                this.messagesEl.appendChild(div);
                this._scrollBottom();
                return;
            }

            // ─── Interactive states (needs_photo or ready) ───
            const productImg = data.product_image_url
                ? `<img class="beena-tryon-product-img" src="${data.product_image_url}" alt="${this._escapeHTML(data.product_name||'')}" onerror="this.style.display='none'">`
                : '';
            const priceTxt = data.product_price_kd
                ? `<div class="beena-tryon-price">${Number(data.product_price_kd).toFixed(3)} KD</div>` : '';
            const productBlock = `
                <div class="beena-tryon-product">
                    ${productImg}
                    <div class="beena-tryon-product-info">
                        <div class="beena-tryon-product-name">${this._escapeHTML(data.product_name || '')}</div>
                        ${priceTxt}
                    </div>
                </div>`;

            // Existing-photo preview (only if user already uploaded one)
            const photoPreview = (state === 'ready' && data.photo_url)
                ? `<div class="beena-tryon-photo-row">
                       <img class="beena-tryon-photo-thumb" src="${data.photo_url}" alt="your saved photo">
                       <div class="beena-tryon-photo-meta">
                           <div class="beena-tryon-photo-label">📸 ${t('Your saved photo', 'صورتك المحفوظة')}</div>
                           <button type="button" class="beena-tryon-change-photo" id="beena-tryon-change-${pid}">${t('Change photo', 'غيّر الصورة')}</button>
                       </div>
                   </div>`
                : '';

            let controls = '';
            if (state === 'needs_photo') {
                controls = `
                    <input type="file" accept="image/*" id="beena-tryon-file-${pid}" style="display:none">
                    <button type="button" id="beena-tryon-upload-${pid}" class="beena-tryon-btn beena-tryon-btn-primary">
                        📷 ${t('Upload your photo', 'ارفع صورتك')}
                    </button>
                    <div class="beena-tryon-hint">${t('JPG / PNG · up to 8MB · full standing pose, good lighting', 'JPG / PNG · حتى 8MB · وقفة كاملة وإضاءة جيدة')}</div>`;
            } else if (state === 'ready') {
                controls = `
                    <input type="file" accept="image/*" id="beena-tryon-file-${pid}" style="display:none">
                    <button type="button" id="beena-tryon-go-${pid}" class="beena-tryon-btn beena-tryon-btn-primary">
                        ✨ ${t('Try it on now', 'جرّب الآن')}
                    </button>`;
            }

            const result = `<div id="beena-tryon-result-${pid}" class="beena-tryon-result"></div>`;

            div.innerHTML = header + productBlock + photoPreview + msg + controls + result;
            this.messagesEl.appendChild(div);
            this._scrollBottom();

            // ── Wire interactive handlers ──
            const fileInput  = div.querySelector(`#beena-tryon-file-${pid}`);
            const handleUpload = async (file, afterBtn) => {
                if (!file) return;
                if (file.size > 8 * 1024 * 1024) {
                    self._addAIMessage(t('The image is too large (over 8MB). Try a smaller one.', 'الصورة كبيرة (أكثر من 8 ميجا). حاول صورة أصغر.'), 'sad');
                    return;
                }
                if (afterBtn) { afterBtn.disabled = true; afterBtn.innerHTML = '⏳ ' + t('Uploading...', 'جاري الرفع...'); }
                const reader = new FileReader();
                reader.onload = async (e) => {
                    const b64 = e.target.result.split(',')[1];
                    const up = await self._jsonCall('/tryon/upload-photo', {
                        image_base64: b64, filename: file.name,
                    });
                    if (!up || !up.success) {
                        if (afterBtn) { afterBtn.disabled = false; afterBtn.innerHTML = '📷 ' + t('Upload your photo', 'ارفع صورتك'); }
                        self._addAIMessage(t('We couldn\'t upload the image. Please try again.', 'ما قدرنا نرفع الصورة. حاول مرة ثانية.'), 'sad');
                        return;
                    }
                    if (afterBtn) afterBtn.innerHTML = '✅ ' + t('Uploaded', 'تم الرفع');
                    self._tryonGenerate(pid, div);
                };
                reader.readAsDataURL(file);
            };

            if (state === 'needs_photo') {
                const uploadBtn = div.querySelector(`#beena-tryon-upload-${pid}`);
                uploadBtn.addEventListener('click', () => fileInput.click());
                fileInput.addEventListener('change', (ev) => handleUpload(ev.target.files[0], uploadBtn));
            } else if (state === 'ready') {
                const goBtn      = div.querySelector(`#beena-tryon-go-${pid}`);
                const changeBtn  = div.querySelector(`#beena-tryon-change-${pid}`);
                goBtn.addEventListener('click', () => {
                    goBtn.disabled = true;
                    goBtn.innerHTML = '⏳ ' + t('Generating...', 'جاري التوليد...');
                    self._tryonGenerate(pid, div);
                });
                if (changeBtn) {
                    changeBtn.addEventListener('click', () => fileInput.click());
                    fileInput.addEventListener('change', (ev) => handleUpload(ev.target.files[0], goBtn));
                }
            }
        };

        // Helper: call /tryon/generate then poll /tryon/status until done/failed
        window.BeenaApp.prototype._tryonGenerate = async function(productId, cardEl) {
            const self    = this;
            const t = (en, ar) => self._t(en, ar);
            self._lastTryonProductId = productId;  // remembered for color/bg regens
            const resultEl = cardEl.querySelector(`#beena-tryon-result-${productId}`);
            resultEl.innerHTML = '<div style="font-size:11px;color:#666">⏳ ' + t('Generating, takes ~30 seconds...', 'جاري التوليد، يستغرق ~30 ثانية...') + '</div>';

            const start = await this._jsonCall('/tryon/generate', {product_id: productId});
            if (!start || !start.success) {
                const err = (start && start.error) || 'unknown';
                resultEl.innerHTML = `<div style="font-size:11px;color:#791F1F">${t('Could not start try-on', 'تعذّر بدء التجربة')} (${err}).</div>`;
                return;
            }

            const imageId = start.image_id;
            const maxAttempts = 30;  // ~60 seconds at 2s interval
            let attempt = 0;

            const poll = async () => {
                attempt++;
                const s = await self._jsonCall(`/tryon/status/${imageId}`, {});
                if (!s || !s.success) {
                    resultEl.innerHTML = `<div style="font-size:11px;color:#791F1F">${t('Connection lost during generation.', 'انقطع الاتصال أثناء التوليد.')}</div>`;
                    return;
                }
                if (s.status === 'done' && s.image_url) {
                    resultEl.innerHTML = `
                        <div class="beena-tryon-result-wrap">
                            <img src="${s.image_url}" alt="try-on result" class="beena-tryon-result-img">
                            <div class="beena-tryon-result-caption">✨ ${t('Result — click to enlarge', 'النتيجة — اضغط للتكبير')}</div>
                            <div class="beena-tryon-features" data-image-id="${imageId}" data-product-id="${productId}"></div>
                        </div>`;
                    const im = resultEl.querySelector('img');
                    if (im) im.addEventListener('click', () => self._openLightbox(im.src));
                    self._renderTryonFeatures(resultEl, imageId, productId);
                    return;
                }
                if (s.status === 'failed') {
                    resultEl.innerHTML = `<div style="font-size:11px;color:#791F1F">${t('Generation failed. Try again with a clearer photo.', 'فشل التوليد. حاول مرة ثانية بصورة أوضح.')}</div>`;
                    return;
                }
                if (attempt >= maxAttempts) {
                    resultEl.innerHTML = `<div style="font-size:11px;color:#854F0B">${t('This is taking longer than expected. Check "My Try-Ons" shortly.', 'التوليد طوّل أكثر من المتوقع. راجع صفحة "تجاربي" بعد قليل.')}</div>`;
                    return;
                }
                setTimeout(poll, 2000);
            };
            setTimeout(poll, 2000);
        };

        // ── Post-generation feature buttons (color, styling, save, PDF, ...) ──
        window.BeenaApp.prototype._renderTryonFeatures = async function(resultEl, imageId, productId) {
            const self = this;
            const t = (en, ar) => self._t(en, ar);
            const container = resultEl.querySelector('.beena-tryon-features');
            if (!container) return;

            // Cache feature flags per instance to avoid repeat fetches
            if (!self._tryonFeatFlags) {
                try {
                    self._tryonFeatFlags = await self._jsonCall('/tryon/features', {});
                } catch (e) { self._tryonFeatFlags = {}; }
            }
            const f = self._tryonFeatFlags || {};

            const buttons = [];
            if (f.color_swap)
                buttons.push({key:'color',     icon:'🎨', en:'Change color',     ar:'غيّر اللون'});
            if (f.background_swap)
                buttons.push({key:'bg',        icon:'🏞', en:'Change background', ar:'غيّر الخلفية'});
            if (f.compare_models)
                buttons.push({key:'compare',   icon:'🔄', en:'Compare models',    ar:'قارن النماذج'});
            if (f.styling_tips)
                buttons.push({key:'styling',   icon:'💡', en:'Styling tips',      ar:'نصائح تنسيق'});
            if (f.save_wishlist)
                buttons.push({key:'wishlist',  icon:'💾', en:'Save to wishlist',  ar:'احفظ في المفضّلة'});
            if (f.pdf_download)
                buttons.push({key:'pdf',       icon:'📄', en:'PDF',               ar:'PDF'});
            if (f.reviewer_opinion)
                buttons.push({key:'reviewer',  icon:'👥', en:'Ask a reviewer',    ar:'استشر خبير'});

            if (!buttons.length) { container.remove(); return; }

            container.innerHTML = buttons.map(b =>
                `<button class="beena-tryon-feat-btn" data-feat="${b.key}">${b.icon} ${t(b.en, b.ar)}</button>`
            ).join('');

            container.querySelectorAll('.beena-tryon-feat-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    self._handleTryonFeature(btn.dataset.feat, imageId, productId, resultEl);
                });
            });
        };

        window.BeenaApp.prototype._handleTryonFeature = async function(key, imageId, productId, resultEl) {
            const self = this;
            const t = (en, ar) => self._t(en, ar);
            const notify = (en, ar, isErr) => self._addAIMessage(t(en, ar), isErr ? 'sad' : 'talking');

            // PDF: just open a new tab — auth handled by Odoo session
            if (key === 'pdf') {
                window.open(`/tryon/pdf/${imageId}`, '_blank');
                return;
            }

            // Save to wishlist
            if (key === 'wishlist') {
                const r = await self._jsonCall('/tryon/save-wishlist', {image_id: imageId});
                if (r && r.success) {
                    notify('Saved to your wishlist ✓', 'تم الحفظ في المفضّلة ✓');
                    if (r.wishlist_url) {
                        const div = document.createElement('div');
                        div.className = 'beena-msg beena-msg-ai';
                        div.innerHTML = `<a href="${r.wishlist_url}" class="beena-rich-link" target="_blank">${t('Open my wishlist', 'افتح مفضّلتي')} →</a>`;
                        self.messagesEl.appendChild(div);
                        self._scrollBottom();
                    }
                } else {
                    notify('Could not save to wishlist.', 'تعذّر الحفظ في المفضّلة.', true);
                }
                return;
            }

            // Ask reviewer — multi-select picker, then group vote
            if (key === 'reviewer') {
                const list = await self._jsonCall('/tryon/reviewers/list/' + imageId, {});
                if (!list || list.enabled === false || !Array.isArray(list.reviewers) || !list.reviewers.length) {
                    notify('No reviewers available.', 'لا يوجد خبراء متاحون.', true);
                    return;
                }
                self._promptReviewersPick(list.reviewers, async (pickedIds) => {
                    if (!pickedIds.length) return;
                    const r = await self._jsonCall('/tryon/reviewers/ask', {
                        image_id: imageId, reviewer_ids: pickedIds,
                    });
                    if (!r || !r.success) {
                        notify('Could not send request.', 'تعذّر إرسال الطلب.', true);
                        return;
                    }
                    notify(
                        `Sent to ${r.reviewer_count} reviewers — polling for replies…`,
                        `أرسلت لـ ${r.reviewer_count} خبراء — بنتابع الردود…`,
                    );
                    self._pollReviewerVotes(imageId);
                });
                return;
            }

            // Styling tips — endpoint is /tryon/styling-tips/<image_id>
            if (key === 'styling') {
                const r = await self._jsonCall('/tryon/styling-tips/' + imageId, {});
                if (!r || r.enabled === false) {
                    notify('Could not get styling tips.', 'تعذّر جلب نصائح التنسيق.', true);
                    return;
                }
                if (r.tip) self._addAIMessage(r.tip, 'talking');
                const sug = r.suggestions || r.matches || [];
                if (Array.isArray(sug) && sug.length) {
                    self._showProductList(sug.map(m => ({
                        id:        m.id,
                        name:      m.name,
                        price:     m.price_kd,
                        image_url: m.image_url,
                        in_stock:  true,
                    })));
                }
                return;
            }

            // Compare models — submits a new generation; we render result inline below
            if (key === 'compare') {
                const r = await self._jsonCall('/tryon/compare-models', {image_id: imageId});
                if (!r || !r.success) {
                    notify('Could not start comparison.', 'تعذّر بدء المقارنة.', true);
                    return;
                }
                self._pollNewTryonImage(r.image_id, r.model || 'alt model', resultEl);
                return;
            }

            // Background swap — endpoint is /tryon/regenerate-background
            if (key === 'bg') {
                self._promptBgPreset(async (preset) => {
                    const r = await self._jsonCall('/tryon/regenerate-background', {image_id: imageId, preset});
                    if (!r || !r.success) {
                        notify('Could not change background.', 'تعذّر تغيير الخلفية.', true);
                        return;
                    }
                    self._pollNewTryonImage(r.image_id, `bg: ${preset}`, resultEl);
                });
                return;
            }

            // Color swap — fetch color attribute values from the product
            if (key === 'color') {
                const cols = await self._jsonCall('/tryon/colors/' + imageId, {});
                if (!cols || cols.enabled === false || !Array.isArray(cols.colors) || !cols.colors.length) {
                    notify('No color options for this product.', 'لا توجد خيارات ألوان لهذا المنتج.', true);
                    return;
                }
                self._promptColorPick(cols.colors, async (avId) => {
                    const r = await self._jsonCall('/tryon/regenerate-color', {
                        image_id: imageId, color_attribute_value_id: avId,
                    });
                    if (!r || !r.success) {
                        notify('Could not regenerate with this color.', 'تعذّر التوليد بهذا اللون.', true);
                        return;
                    }
                    self._pollNewTryonImage(r.image_id, r.color || 'color', resultEl);
                });
                return;
            }
        };

        // Poll a brand-new image_id and append its result as a fresh card
        window.BeenaApp.prototype._pollNewTryonImage = function(imageId, label, anchorEl) {
            const self = this;
            const t = (en, ar) => self._t(en, ar);
            const card = document.createElement('div');
            card.className = 'beena-msg beena-msg-ai beena-tryon-card';
            card.innerHTML = `<div class="beena-tryon-msg">⏳ ${t('Generating', 'جاري التوليد')}: ${self._escapeHTML(label)}…</div>
                              <div class="beena-tryon-result"></div>`;
            self.messagesEl.appendChild(card);
            self._scrollBottom();
            const resultEl = card.querySelector('.beena-tryon-result');

            let attempt = 0;
            const max = 30;
            const poll = async () => {
                attempt++;
                const s = await self._jsonCall(`/tryon/status/${imageId}`, {});
                if (!s || !s.success) {
                    resultEl.innerHTML = `<div style="font-size:11px;color:#791F1F">${t('Connection lost.', 'انقطع الاتصال.')}</div>`;
                    return;
                }
                if (s.status === 'done' && s.image_url) {
                    resultEl.innerHTML = `
                        <div class="beena-tryon-result-wrap">
                            <img src="${s.image_url}" class="beena-tryon-result-img">
                            <div class="beena-tryon-result-caption">✨ ${self._escapeHTML(label)}</div>
                            <div class="beena-tryon-features beena-tryon-options"></div>
                        </div>`;
                    const im = resultEl.querySelector('img');
                    if (im) im.addEventListener('click', () => self._openLightbox(im.src));
                    // Re-render the same option strip (colors, ask reviewer,
                    // styling tips, etc.) so the customer can keep iterating
                    // on the freshly generated image.
                    const productId = (anchorEl && anchorEl.dataset && anchorEl.dataset.productId)
                                       || self._lastTryonProductId
                                       || self.productId;
                    self._renderTryonFeatures(resultEl, imageId, productId);
                    return;
                }
                if (s.status === 'failed') {
                    resultEl.innerHTML = `<div style="font-size:11px;color:#791F1F">${t('Generation failed.', 'فشل التوليد.')}</div>`;
                    return;
                }
                if (attempt >= max) {
                    resultEl.innerHTML = `<div style="font-size:11px;color:#854F0B">${t('Still working — check "My Try-Ons" later.', 'لسه يعمل — راجع "تجاربي" بعد قليل.')}</div>`;
                    return;
                }
                setTimeout(poll, 2000);
            };
            setTimeout(poll, 2000);
        };

        // Inline color picker (chips list)
        window.BeenaApp.prototype._promptColorPick = function(colors, onPick) {
            const self = this;
            const t = (en, ar) => self._t(en, ar);
            const div = document.createElement('div');
            div.className = 'beena-msg beena-msg-ai beena-tryon-picker';
            div.innerHTML = `
                <div class="beena-tryon-picker-title">${t('Pick a color', 'اختر اللون')}</div>
                <div class="beena-tryon-picker-chips">${colors.map(c => `
                    <button class="beena-tryon-picker-chip" data-id="${c.id}">${self._escapeHTML(c.name || '?')}</button>
                `).join('')}</div>`;
            self.messagesEl.appendChild(div);
            self._scrollBottom();
            div.querySelectorAll('.beena-tryon-picker-chip').forEach(btn => {
                btn.addEventListener('click', () => {
                    div.querySelectorAll('button').forEach(b => b.disabled = true);
                    btn.classList.add('active');
                    onPick(parseInt(btn.dataset.id, 10));
                });
            });
        };

        // Multi-select reviewer picker with cards
        window.BeenaApp.prototype._promptReviewersPick = function(reviewers, onSubmit) {
            const self = this;
            const t = (en, ar) => self._t(en, ar);
            const div = document.createElement('div');
            div.className = 'beena-msg beena-msg-ai beena-rev-picker';

            const initial = (n) => (n || '?').trim().charAt(0);
            const cards = reviewers.map(r => `
                <label class="beena-rev-pcard">
                    <input type="checkbox" data-id="${r.id}" class="beena-rev-pcheck">
                    <div class="beena-rev-pcard-inner">
                        <div class="beena-rev-pcard-avatar">
                            <img src="${r.avatar_url}" alt="${self._escapeHTML(r.name)}"
                                 onerror="this.style.display='none';this.nextElementSibling.style.display='flex';">
                            <span class="beena-rev-pcard-init">${self._escapeHTML(initial(r.name))}</span>
                            <span class="beena-rev-pcard-dot ${r.is_online ? 'on' : 'off'}"></span>
                        </div>
                        <div class="beena-rev-pcard-info">
                            <div class="beena-rev-pcard-name">${self._escapeHTML(r.name)}</div>
                            <div class="beena-rev-pcard-meta">
                                <span class="beena-rev-pcard-stars">${'★'.repeat(Math.round(r.rating||5))}${'☆'.repeat(5-Math.round(r.rating||5))}</span>
                                <span class="beena-rev-pcard-num">${(r.rating||0).toFixed(1)}</span>
                            </div>
                            <div class="beena-rev-pcard-level">${self._escapeHTML(r.level_label||'')}</div>
                        </div>
                    </div>
                </label>
            `).join('');

            div.innerHTML = `
                <div class="beena-rev-picker-title">${t('Pick one or more reviewers', 'اختر خبير أو أكثر')}</div>
                <div class="beena-rev-picker-cards">${cards}</div>
                <div class="beena-rev-picker-actions">
                    <span class="beena-rev-picker-hint">${t('Selected:', 'المُختار:')} <b id="beena-rev-picker-count">0</b></span>
                    <button class="beena-rev-picker-cancel">${t('Cancel', 'إلغاء')}</button>
                    <button class="beena-rev-picker-go" disabled>
                        ${t('Send to selected', 'أرسل للمختارين')} ✉️
                    </button>
                </div>`;

            self.messagesEl.appendChild(div);
            self._scrollBottom();

            const update = () => {
                const ids = [...div.querySelectorAll('.beena-rev-pcheck')]
                    .filter(c => c.checked).map(c => parseInt(c.dataset.id, 10));
                div.querySelector('#beena-rev-picker-count').textContent = ids.length;
                div.querySelector('.beena-rev-picker-go').disabled = ids.length === 0;
                return ids;
            };
            div.querySelectorAll('.beena-rev-pcheck').forEach(c => {
                c.addEventListener('change', update);
            });
            div.querySelector('.beena-rev-picker-cancel').addEventListener('click', () => {
                div.querySelectorAll('input, button').forEach(b => b.disabled = true);
                div.style.opacity = '0.5';
            });
            div.querySelector('.beena-rev-picker-go').addEventListener('click', () => {
                const ids = update();
                div.querySelectorAll('input, button').forEach(b => b.disabled = true);
                div.style.opacity = '0.7';
                onSubmit(ids);
            });
        };

        // Poll the votes endpoint and render a results card that updates live
        window.BeenaApp.prototype._pollReviewerVotes = function(imageId) {
            const self = this;
            const t = (en, ar) => self._t(en, ar);

            const card = document.createElement('div');
            card.className = 'beena-msg beena-msg-ai beena-rev-votes';
            self.messagesEl.appendChild(card);
            self._scrollBottom();

            const render = (data) => {
                const rec = data.recommend || 0;
                const no  = data.not_recommend || 0;
                const pend = data.pending || 0;
                const total = data.total || (rec + no + pend);
                const items = (data.votes || []).map(v => {
                    const verdictTxt = v.verdict === 'recommend' ? t('Recommend ✓','يوصي ✓')
                                     : (v.verdict === 'dont_recommend' || v.verdict === 'no') ? t("Don't ✗",'لا ✗')
                                     : t('Pending…','بالانتظار…');
                    const verdictCls = v.verdict === 'recommend' ? 'good'
                                     : (v.verdict === 'dont_recommend' || v.verdict === 'no') ? 'bad'
                                     : 'pending';
                    const note = v.note ? `<div class="beena-rev-vote-note">${self._escapeHTML(v.note)}</div>` : '';
                    return `<div class="beena-rev-vote">
                        <img class="beena-rev-vote-avatar" src="${v.avatar_url}" onerror="this.style.display='none'">
                        <div class="beena-rev-vote-name">${self._escapeHTML(v.reviewer_name||'')}</div>
                        <div class="beena-rev-vote-verdict ${verdictCls}">${verdictTxt}</div>
                        ${note}
                    </div>`;
                }).join('');

                card.innerHTML = `
                    <div class="beena-rev-votes-head">
                        <div class="beena-rev-votes-title">👥 ${t('Reviewer opinions', 'آراء الخبراء')}</div>
                        <div class="beena-rev-votes-totals">
                            <span class="t-good">✓ ${rec}</span>
                            <span class="t-bad">✗ ${no}</span>
                            <span class="t-pending">⏳ ${pend}</span>
                            <span class="t-total">/ ${total}</span>
                        </div>
                    </div>
                    <div class="beena-rev-votes-list">${items || '<div class="text-muted" style="font-size:11px">'+ t('Waiting for responses…','بانتظار الردود…') +'</div>'}</div>`;
            };

            let attempt = 0;
            const max = 60;   // ~5 minutes at 5s
            const tick = async () => {
                attempt++;
                const r = await self._jsonCall(`/tryon/reviewers/votes/${imageId}`, {});
                if (r && r.success) {
                    render(r);
                    if ((r.pending || 0) === 0) return;     // all answered
                }
                if (attempt >= max) return;
                setTimeout(tick, 5000);
            };
            tick();
        };

        // Inline background-preset picker
        window.BeenaApp.prototype._promptBgPreset = function(onPick) {
            const self = this;
            const t = (en, ar) => self._t(en, ar);
            const presets = [
                {k: 'studio', en: 'Studio', ar: 'استوديو', emoji: '📸'},
                {k: 'beach',  en: 'Beach',  ar: 'شاطئ',    emoji: '🏖️'},
                {k: 'street', en: 'Street', ar: 'شارع',    emoji: '🛣️'},
                {k: 'party',  en: 'Party',  ar: 'حفلة',    emoji: '🎉'},
                {k: 'office', en: 'Office', ar: 'مكتب',    emoji: '💼'},
            ];
            const div = document.createElement('div');
            div.className = 'beena-msg beena-msg-ai beena-tryon-picker';
            div.innerHTML = `
                <div class="beena-tryon-picker-title">${t('Pick a background', 'اختر الخلفية')}</div>
                <div class="beena-tryon-picker-chips">${presets.map(p => `
                    <button class="beena-tryon-picker-chip" data-k="${p.k}">${p.emoji} ${t(p.en, p.ar)}</button>
                `).join('')}</div>`;
            self.messagesEl.appendChild(div);
            self._scrollBottom();
            div.querySelectorAll('.beena-tryon-picker-chip').forEach(btn => {
                btn.addEventListener('click', () => {
                    div.querySelectorAll('button').forEach(b => b.disabled = true);
                    btn.classList.add('active');
                    onPick(btn.dataset.k);
                });
            });
        };

        // Tiny JSON-RPC helper (Odoo /web/dataset/call style not needed — using fetch)
        window.BeenaApp.prototype._jsonCall = async function(url, params) {
            try {
                const resp = await fetch(url, {
                    method:  'POST',
                    headers: {'Content-Type': 'application/json'},
                    body:    JSON.stringify({jsonrpc: '2.0', method: 'call', params: params || {}}),
                });
                const j = await resp.json();
                return j.result;
            } catch (e) {
                return null;
            }
        };

        // New: show reviewers list inside chat
        window.BeenaApp.prototype._showReviewers = function(data) {
            if (!data || !data.available) return;
            const self = this;
            const t = (en, ar) => self._t(en, ar);

            const div     = document.createElement('div');
            div.className = 'beena-msg beena-msg-ai beena-rev-wrap';

            const reviewers = data.reviewers || [];

            if (!reviewers.length) {
                div.innerHTML = `<div style="font-size:12px;color:#888">${t('No reviewers available right now', 'لا يوجد ريفيورز متاحون حالياً')}</div>`;
                this.messagesEl.appendChild(div);
                this._scrollBottom();
                return;
            }

            const onlineCount = data.online_count || 0;
            let html = `
                <div class="beena-rev-header">
                    <div class="beena-rev-header-title">👥 ${t('Available reviewers', 'الريفيورز المتاحون')}</div>
                    <div class="beena-rev-header-sub">${onlineCount > 0
                        ? `<span class="beena-rev-dot-on"></span> ${onlineCount} ${t('online now', 'أونلاين الآن')}`
                        : `<span class="beena-rev-dot-off"></span> ${t('Offline — you can leave a request', 'غير متصلين — يمكنك ترك طلب')}`}</div>
                </div>`;

            reviewers.slice(0, 4).forEach(r => {
                const rating = Number(r.rating) || 5;
                const stars  = '★'.repeat(Math.round(rating)) + '☆'.repeat(5 - Math.round(rating));
                const badgeColors = {
                    elite:    {fg:'#3C3489', bg:'#EEEDFE'},
                    expert:   {fg:'#27500A', bg:'#EAF3DE'},
                    regular:  {fg:'#0C447C', bg:'#E6F1FB'},
                    starter:  {fg:'#5F5E5A', bg:'#F5F4F2'},
                };
                const bc = badgeColors[r.level] || badgeColors.starter;
                const reviewCnt = r.review_count ? `<span class="beena-rev-reviews">· ${r.review_count} ${t('reviews', 'مراجعة')}</span>` : '';
                const safeName  = self._escapeHTML(r.name || '?');
                const initial   = (r.name || '?').trim().charAt(0);

                html += `
<div class="beena-rev-card" data-rev-id="${r.id}">
  <div class="beena-rev-avatar-wrap">
    <img class="beena-rev-avatar" src="${r.avatar_url}" alt="${safeName}"
         onerror="this.style.display='none';this.nextElementSibling.style.display='flex';">
    <div class="beena-rev-avatar-fallback">${self._escapeHTML(initial)}</div>
    <div class="beena-rev-status ${r.is_online ? 'on' : 'off'}"></div>
  </div>
  <div class="beena-rev-info">
    <div class="beena-rev-name-row">
      <span class="beena-rev-name">${safeName}</span>
      <span class="beena-rev-badge" style="background:${bc.bg};color:${bc.fg}">${self._escapeHTML(r.level_label || '')}</span>
    </div>
    <div class="beena-rev-rating">
      <span class="beena-rev-stars">${stars}</span>
      <span class="beena-rev-num">${rating.toFixed(1)}</span>
      ${reviewCnt}
    </div>
    ${r.specialty_text ? `<div class="beena-rev-specialty">${self._escapeHTML(r.specialty_text)}</div>` : ''}
    <div class="beena-rev-actions">
      ${r.allow_chat    ? `<button type="button" class="beena-rev-btn beena-rev-btn-chat"    data-action="chat"    data-rev-id="${r.id}">💬 ${t('Chat', 'شات')}</button>` : ''}
      ${r.allow_written ? `<button type="button" class="beena-rev-btn beena-rev-btn-written" data-action="written" data-rev-id="${r.id}">✍️ ${t('Written opinion', 'رأي مكتوب')}</button>` : ''}
      <span class="beena-rev-free">${t('Free', 'مجاناً')}</span>
    </div>
  </div>
</div>`;
            });

            div.innerHTML = html;
            this.messagesEl.appendChild(div);
            this._scrollBottom();

            // Wire action buttons → forward to chat as a follow-up question
            div.querySelectorAll('.beena-rev-btn').forEach(btn => {
                btn.addEventListener('click', (ev) => {
                    const action = btn.dataset.action;
                    const revId  = btn.dataset.revId;
                    const card   = ev.target.closest('.beena-rev-card');
                    const name   = card ? card.querySelector('.beena-rev-name').textContent : '';
                    const msg = action === 'chat'
                        ? t('I want to start a chat with '+name+' (rev:'+revId+')', 'أبي أبدأ شات مع '+name+' (rev:'+revId+')')
                        : t('I want a written opinion from '+name+' (rev:'+revId+')', 'أبي رأي مكتوب من '+name+' (rev:'+revId+')');
                    self._send(msg);
                });
            });

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
            const self = this;
            const t = (en, ar) => self._t(en, ar);
            const div = document.createElement('div');
            div.className = 'beena-msg beena-msg-ai beena-cart-added';
            div.innerHTML = `
                <div class="beena-cart-added-head">
                    ✓ ${t('Added to cart', 'تمت الإضافة للسلة')}
                </div>
                <div class="beena-cart-added-name">${self._escapeHTML(cart.product || '')}</div>
                <div class="beena-cart-added-total">
                    ${t('Total', 'الإجمالي')}: <strong>${(cart.cart_total||0).toFixed(3)} KD</strong>
                    <span class="beena-cart-added-count">· ${cart.cart_count || 0} ${t('items', 'قطعة')}</span>
                </div>
                <div class="beena-cart-added-actions">
                    <a href="${cart.cart_url||'/shop/cart'}" class="beena-cart-btn beena-cart-btn-link">
                        🛒 ${t('View cart', 'عرض السلة')}
                    </a>
                    <button type="button" class="beena-cart-btn beena-cart-btn-primary" data-action="checkout">
                        ✓ ${t('Checkout with Beena', 'أتمم الطلب مع بينا')}
                    </button>
                </div>`;
            this.messagesEl.appendChild(div);
            this._scrollBottom();
            const ck = div.querySelector('[data-action="checkout"]');
            if (ck) ck.addEventListener('click', () => self._send(t('Place the order', 'اتمم الطلب')));
        };

        // ── Cart view card (list of items + total) ─────────────────────────
        window.BeenaApp.prototype._showCartView = function(data) {
            if (!data) return;
            const self = this;
            const t = (en, ar) => self._t(en, ar);
            const div = document.createElement('div');
            div.className = 'beena-msg beena-msg-ai beena-cart-view';

            if (data.guest) {
                div.innerHTML = `<div class="beena-cart-empty">🔒 ${self._escapeHTML(data.message || t('Sign in to see your cart','سجّل دخولك لعرض السلة'))}</div>`;
                this.messagesEl.appendChild(div);
                this._scrollBottom();
                return;
            }
            if (data.empty || !Array.isArray(data.lines) || !data.lines.length) {
                div.innerHTML = `<div class="beena-cart-empty">🛒 ${self._escapeHTML(data.message || t('Your cart is empty','سلتك فاضية'))}</div>`;
                this.messagesEl.appendChild(div);
                this._scrollBottom();
                return;
            }

            const cur = data.currency || 'KD';
            const lines = data.lines.map(l => `
                <div class="beena-cart-line" data-line-id="${l.id}">
                    <img class="beena-cart-line-img" src="${l.image_url}" onerror="this.style.display='none'">
                    <div class="beena-cart-line-info">
                        <div class="beena-cart-line-name">${self._escapeHTML(l.name)}</div>
                        <div class="beena-cart-line-meta">
                            <div class="beena-cart-qty">
                                <button type="button" class="beena-qty-btn" data-action="dec" aria-label="−">−</button>
                                <span class="beena-qty-val">${l.qty}</span>
                                <button type="button" class="beena-qty-btn" data-action="inc" aria-label="+">+</button>
                            </div>
                            <strong>${(l.subtotal||0).toFixed(3)} ${cur}</strong>
                            <button type="button" class="beena-qty-del" data-action="del" aria-label="${t('Remove','احذف')}">🗑</button>
                        </div>
                    </div>
                </div>
            `).join('');

            div.innerHTML = `
                <div class="beena-cart-head">
                    <div class="beena-cart-head-title">🛒 ${t('Your cart', 'سلتك')}</div>
                    <div class="beena-cart-head-count">${data.item_count} ${t('items', 'قطعة')}</div>
                </div>
                <div class="beena-cart-lines">${lines}</div>
                <div class="beena-cart-total">
                    <span>${t('Total', 'الإجمالي')}</span>
                    <strong>${(data.amount_total||0).toFixed(3)} ${cur}</strong>
                </div>
                <div class="beena-cart-actions">
                    <a href="${data.cart_url||'/shop/cart'}" class="beena-cart-btn beena-cart-btn-link">
                        ✏️ ${t('Edit cart', 'عدّل السلة')}
                    </a>
                    <button type="button" class="beena-cart-btn beena-cart-btn-primary" data-action="checkout">
                        ✓ ${t('Checkout with Beena', 'أتمم الطلب مع بينا')}
                    </button>
                </div>`;
            this.messagesEl.appendChild(div);
            this._scrollBottom();
            const ck = div.querySelector('[data-action="checkout"]');
            if (ck) ck.addEventListener('click', () => self._send(t('Place the order', 'اتمم الطلب')));

            // Wire qty +/− and delete per line — calls RPC, then re-renders
            // the whole card by replacing the same DOM node (so we never
            // leak duplicate "Your cart" cards).
            const updateLine = async (lineId, qty) => {
                const r = await self._jsonCall('/ai/cart_set_qty', {line_id: lineId, qty});
                if (!r || r.success === false) return;
                // Replace the existing card with the freshly fetched cart
                const placeholder = document.createElement('div');
                div.replaceWith(placeholder);
                self._showCartView(r);
                placeholder.remove();
            };
            div.querySelectorAll('.beena-cart-line').forEach(row => {
                const lineId = parseInt(row.dataset.lineId, 10);
                const valEl  = row.querySelector('.beena-qty-val');
                const cur    = () => parseInt((valEl && valEl.textContent) || '0', 10) || 0;
                const inc = row.querySelector('[data-action="inc"]');
                const dec = row.querySelector('[data-action="dec"]');
                const del = row.querySelector('[data-action="del"]');
                if (inc) inc.addEventListener('click', () => updateLine(lineId, cur() + 1));
                if (dec) dec.addEventListener('click', () => updateLine(lineId, Math.max(0, cur() - 1)));
                if (del) del.addEventListener('click', () => updateLine(lineId, 0));
            });
        };

        // ── Editable Checkout card (editable form + Place order CTA) ──────
        window.BeenaApp.prototype._showCheckout = function(data) {
            if (!data) return;
            const self = this;
            const t = (en, ar) => self._t(en, ar);
            const div = document.createElement('div');
            div.className = 'beena-msg beena-msg-ai beena-checkout-card';

            if (data.state === 'needs_login') {
                div.innerHTML = `<div class="beena-checkout-msg">🔒 ${self._escapeHTML(data.message || t('Sign in to continue','سجّل دخولك للمتابعة'))}</div>
                                 <button type="button" data-action="beena-signin" class="beena-cart-btn beena-cart-btn-primary">🔑 ${t('Sign in', 'تسجيل الدخول')}</button>`;
                this.messagesEl.appendChild(div);
                this._scrollBottom();
                return;
            }
            if (data.state === 'empty_cart') {
                div.innerHTML = `<div class="beena-checkout-msg">🛒 ${self._escapeHTML(data.message || t('Your cart is empty','سلتك فاضية'))}</div>`;
                this.messagesEl.appendChild(div);
                this._scrollBottom();
                return;
            }

            const addr = data.address || {};
            const cur  = data.currency || 'KD';
            const uid  = 'co' + Math.random().toString(36).slice(2, 8);

            // ── Mode picker: manual vs Geo-IP ─────────────────────────────
            // Only shown when nothing on the address is filled yet (fresh start)
            // AND the user hasn't already picked a mode in this session.
            const addrEmpty = !addr.phone && !addr.governorate && !addr.city && !addr.street;
            if (addrEmpty && !self._coAddressMode) {
                const intro = document.createElement('div');
                intro.className = 'beena-msg beena-msg-ai beena-msg-wide';
                intro.dir = self.lang === 'ar' ? 'rtl' : 'ltr';
                intro.innerHTML = `
                    <div style="font-weight:700;margin-bottom:6px">${t(
                        'How would you like to enter your delivery address?',
                        'كيف تحب نأخذ عنوان التوصيل؟'
                    )}</div>
                    <div class="beena-mode-picker">
                        <button type="button" class="beena-mode-btn" data-mode="manual">
                            <span class="beena-mode-icon">✍️</span>
                            <span class="beena-mode-title">${t('Type it myself', 'أكتبه بنفسي')}</span>
                            <span class="beena-mode-sub">${t('Phone, governorate, city, street', 'الجوّال، المحافظة، المدينة، الشارع')}</span>
                        </button>
                        <button type="button" class="beena-mode-btn" data-mode="geo">
                            <span class="beena-mode-icon">📍</span>
                            <span class="beena-mode-title">${t('Use my current location', 'استخدم موقعي الحالي')}</span>
                            <span class="beena-mode-sub">${t('Fastest — auto-fills via GPS', 'الأسرع — يعبئ تلقائياً من GPS')}</span>
                        </button>
                    </div>`;
                this.messagesEl.appendChild(intro);
                this._scrollBottom();

                intro.querySelectorAll('.beena-mode-btn').forEach(b => {
                    b.addEventListener('click', () => {
                        const mode = b.dataset.mode;
                        self._coAddressMode = mode;
                        intro.remove();
                        // Render the actual form, then optionally auto-trigger geo
                        self._showCheckout(data);
                        if (mode === 'geo') {
                            // Click the geo button in the newly-rendered card
                            setTimeout(() => {
                                const last = self.messagesEl.querySelector('.beena-checkout-card:last-of-type [data-action="geo"]');
                                if (last) last.click();
                            }, 80);
                        }
                    });
                });
                return;
            }

            div.classList.add('beena-msg-wide');
            div.innerHTML = `
                <div class="beena-checkout-head">
                    <div class="beena-checkout-title">✓ ${t('Checkout', 'إتمام الطلب')}</div>
                    <div class="beena-checkout-total">${(data.amount_total||0).toFixed(3)} ${cur}</div>
                </div>

                <div class="beena-checkout-form">
                    <div class="beena-co-row">
                        <label class="beena-co-label" for="${uid}-phone">📞 ${t('Phone', 'الجوّال')}</label>
                        <input id="${uid}-phone"       type="tel"  class="beena-co-input"
                               placeholder="${t('e.g. 9988xxxx', 'مثال: 9988xxxx')}"
                               value="${self._escapeHTML(addr.phone||'')}">
                    </div>
                    <div class="beena-co-row">
                        <label class="beena-co-label" for="${uid}-gov">🗺 ${t('Governorate', 'المحافظة')}</label>
                        <input id="${uid}-gov"         type="text" class="beena-co-input"
                               placeholder="${t('e.g. Hawalli', 'مثال: حولي')}"
                               value="${self._escapeHTML(addr.governorate||'')}">
                    </div>
                    <div class="beena-co-row">
                        <label class="beena-co-label" for="${uid}-city">🏙 ${t('City / Area', 'المدينة / المنطقة')}</label>
                        <input id="${uid}-city"        type="text" class="beena-co-input"
                               placeholder="${t('e.g. Salmiya', 'مثال: السالمية')}"
                               value="${self._escapeHTML(addr.city||'')}">
                    </div>
                    <div class="beena-co-row">
                        <label class="beena-co-label" for="${uid}-street">📍 ${t('Street / Block / House', 'الشارع / القطعة / المنزل')}</label>
                        <input id="${uid}-street"      type="text" class="beena-co-input"
                               placeholder="${t('Block, street, building', 'القطعة، الشارع، المبنى')}"
                               value="${self._escapeHTML(addr.street||'')}">
                    </div>

                    <button type="button" class="beena-co-geo" data-action="geo">
                        📍 ${t('Use my current location', 'أحضر عنواني تلقائياً')}
                    </button>

                    <div class="beena-co-status" data-role="status"></div>

                    <button type="button" class="beena-cart-btn beena-cart-btn-primary beena-co-submit"
                            data-action="place">
                        ✓ ${t('Place the order', 'أكّد الطلب')}
                    </button>
                </div>`;
            this.messagesEl.appendChild(div);
            this._scrollBottom();

            const $phone  = div.querySelector(`#${uid}-phone`);
            const $gov    = div.querySelector(`#${uid}-gov`);
            const $city   = div.querySelector(`#${uid}-city`);
            const $street = div.querySelector(`#${uid}-street`);
            const $status = div.querySelector('[data-role="status"]');
            const $geo    = div.querySelector('[data-action="geo"]');
            const $place  = div.querySelector('[data-action="place"]');

            const setStatus = (msg, cls) => {
                if (!$status) return;
                $status.className = 'beena-co-status' + (cls ? (' ' + cls) : '');
                $status.textContent = msg || '';
            };

            // Geolocation + Nominatim reverse-geocode (free, no API key)
            $geo.addEventListener('click', () => {
                if (!navigator.geolocation) {
                    setStatus(t('Geolocation not supported by your browser.',
                               'متصفحك ما يدعم تحديد الموقع.'), 'err');
                    return;
                }
                $geo.disabled = true;
                setStatus(t('Detecting your location…', 'جاري تحديد موقعك…'), 'info');
                navigator.geolocation.getCurrentPosition(async (pos) => {
                    const lat = pos.coords.latitude;
                    const lon = pos.coords.longitude;
                    try {
                        const r = await fetch(
                            'https://nominatim.openstreetmap.org/reverse?format=jsonv2&accept-language=' +
                            (self.lang === 'ar' ? 'ar' : 'en') +
                            '&lat=' + lat + '&lon=' + lon
                        );
                        const j = await r.json();
                        const a = j.address || {};
                        const gov    = a.state || a.region || a.governorate || '';
                        const city   = a.city || a.town || a.suburb || a.village || a.county || '';
                        const street = [a.road, a.house_number, a.neighbourhood]
                                        .filter(Boolean).join(' · ') || '';
                        if (gov && !$gov.value)       $gov.value    = gov;
                        if (city && !$city.value)     $city.value   = city;
                        if (street && !$street.value) $street.value = street;
                        setStatus(t('Filled from your location ✓',
                                    'تم تعبئة الحقول من موقعك ✓'), 'ok');
                    } catch (e) {
                        setStatus(t('Could not look up your address.',
                                    'تعذّر جلب عنوانك.'), 'err');
                    }
                    $geo.disabled = false;
                }, () => {
                    $geo.disabled = false;
                    setStatus(t('Please allow location access.',
                                'الرجاء السماح بصلاحية الموقع.'), 'err');
                }, {enableHighAccuracy: false, timeout: 8000, maximumAge: 60000});
            });

            // Place order — sends address + creates Beena Order in one RPC
            $place.addEventListener('click', async () => {
                const phone  = ($phone.value || '').trim();
                const gov    = ($gov.value || '').trim();
                const city   = ($city.value || '').trim();
                const street = ($street.value || '').trim();
                if (!phone || !gov || !city || !street) {
                    setStatus(t('Please fill in all four fields.',
                                'الرجاء تعبئة الحقول الأربعة.'), 'err');
                    return;
                }
                $place.disabled = true;
                $place.innerHTML = '⏳ ' + t('Placing…', 'جاري التسجيل…');
                setStatus('', '');

                const r = await self._jsonCall('/beena/checkout/place', {
                    phone, governorate: gov, city, street,
                });
                if (!r || r.state !== 'created') {
                    $place.disabled = false;
                    $place.innerHTML = '✓ ' + t('Place the order', 'أكّد الطلب');
                    setStatus(t('Could not place the order. Make sure your cart has items.',
                                'تعذّر تسجيل الطلب. تأكد أن السلة فيها منتجات.'), 'err');
                    return;
                }
                self._showQuote(r);
                // Replace the form with a "saved" message
                div.querySelector('.beena-checkout-form').innerHTML =
                    `<div class="beena-co-status ok">✓ ${t('Order placed — see card below.',
                                                            'تم تسجيل الطلب — شوف الكارت تحت.')}</div>`;
            });
        };

        // ── Quote created card ─────────────────────────────────────────────
        window.BeenaApp.prototype._showQuote = function(q) {
            if (!q) return;
            const self = this;
            const t = (en, ar) => self._t(en, ar);
            const div = document.createElement('div');
            div.className = 'beena-msg beena-msg-ai beena-quote-card';

            if (q.state !== 'created') {
                // collecting / empty_cart / needs_login / error → fall through to checkout card
                return self._showCheckout(q);
            }
            const cur  = q.currency || 'KD';
            const addr = q.address || {};
            div.innerHTML = `
                <div class="beena-quote-head">
                    <div class="beena-quote-tag">🐝 ${t('Beena Order', 'طلب بينا')}</div>
                    <div class="beena-quote-name">${self._escapeHTML(q.order_name || '')}</div>
                </div>
                <div class="beena-quote-total">
                    <span>${t('Total', 'الإجمالي')}</span>
                    <strong>${(q.amount_total||0).toFixed(3)} ${cur}</strong>
                </div>
                <div class="beena-quote-meta">
                    <div>📞 ${self._escapeHTML(addr.phone || '')}</div>
                    <div>📍 ${self._escapeHTML([addr.governorate, addr.city, addr.street].filter(Boolean).join(' · '))}</div>
                    <div>📦 ${q.item_count} ${t('items', 'قطعة')}</div>
                </div>
                <div class="beena-cart-actions">
                    <button type="button" class="beena-cart-btn beena-cart-btn-primary" data-action="pay">
                        💳 ${t('Pay now', 'ادفع الآن')}
                    </button>
                    <a href="${q.order_url || '/my/orders'}" class="beena-cart-btn beena-cart-btn-link" target="_blank">
                        📋 ${t('View order', 'عرض الطلب')}
                    </a>
                </div>`;
            this.messagesEl.appendChild(div);
            this._scrollBottom();

            div.querySelector('[data-action="pay"]').addEventListener('click', () => {
                self._openPaymentPopup(q);
            });
        };

        /**
         * Open the payment URL in an in-chat dialog (NOT a new window) and
         * poll the order status until payment confirms. Renders a success
         * card inside chat once state flips to 'sale'.
         */
        window.BeenaApp.prototype._openPaymentPopup = function(q) {
            const self = this;
            const t = (en, ar) => self._t(en, ar);
            const url = q.checkout_url || ('/shop/payment?sale_order_id=' + q.order_id);

            // Open the gateway inside the chat dialog (iframe) — no redirect.
            const overlay = self._openDialog({
                title: t('Secure payment', 'دفع آمن'),
                html: `<iframe class="beena-dialog-iframe" src="${url}" loading="lazy"
                              referrerpolicy="same-origin"
                              allow="payment *; clipboard-write"></iframe>`,
                onClose: () => { paymentClosed = true; },
            });
            let paymentClosed = false;

            // Status banner inside chat
            const status = document.createElement('div');
            status.className = 'beena-msg beena-msg-ai beena-pay-status beena-msg-wide';
            status.innerHTML = `
                <div class="beena-pay-status-row">
                    <span class="beena-pay-spinner"></span>
                    <strong>${t('Waiting for payment…', 'بانتظار إتمام الدفع…')}</strong>
                </div>
                <div class="beena-pay-status-hint">${t('Complete payment in the dialog. This message updates automatically.',
                                                       'أكمل الدفع في النافذة. هذه الرسالة بتتحدّث تلقائياً.')}</div>`;
            this.messagesEl.appendChild(status);
            this._scrollBottom();

            // Poll the order status — works whether or not the iframe is closed.
            let tries = 0;
            const max = 120;          // ~10 minutes at 5s intervals
            const tick = async () => {
                tries++;
                try {
                    const r = await self._jsonCall('/beena/order/status/' + q.order_id, {});
                    if (r && r.success && r.paid) {
                        status.innerHTML = `
                            <div class="beena-pay-success">
                                <div class="beena-pay-success-icon">✓</div>
                                <div>
                                    <strong>${t('Payment received', 'تم استلام الدفع')}</strong>
                                    <div class="beena-pay-status-hint">${self._escapeHTML(r.order_name)} · ${(r.amount_total||0).toFixed(3)} ${r.currency||'KD'}</div>
                                </div>
                            </div>`;
                        if (overlay && overlay._beenaClose) try { overlay._beenaClose(); } catch (e) {}
                        setTimeout(() => {
                            self._addAIMessage(
                                t('🎉 Thank you! Your order is confirmed. Can I help you with anything else?',
                                  '🎉 تم! طلبك مأكد. أقدر أساعدك في شي تاني؟'),
                                'happy',
                            );
                        }, 400);
                        return;
                    }
                    if (r && r.success && r.state === 'cancel') {
                        status.innerHTML = `<div class="beena-pay-failed">✗ ${t('Order was cancelled.','تم إلغاء الطلب.')}</div>`;
                        return;
                    }
                } catch (e) { /* keep polling */ }

                if (paymentClosed && tries > 3) {
                    status.innerHTML = `<div class="beena-pay-pending">${t('Dialog closed before payment finished. If you paid, it will appear in your orders shortly.',
                                                                           'تم إغلاق النافذة قبل اكتمال الدفع. إذا دفعت، الطلب راح يظهر في صفحة الطلبات قريباً.')}</div>`;
                    return;
                }
                if (tries >= max) {
                    status.innerHTML = `<div class="beena-pay-pending">${t('Still waiting — check the order page later.',
                                                                           'لسه بانتظار الإكمال — راجع صفحة الطلبات لاحقاً.')}</div>`;
                    return;
                }
                setTimeout(tick, 5000);
            };
            setTimeout(tick, 5000);
        };

        // ── Location card (Google Maps embed) ─────────────────────────────
        // Rich company-location card: address + map + phone + WhatsApp + photo gallery
        window.BeenaApp.prototype._showCompanyLocation = function(loc) {
            if (!loc) return;
            const self = this;
            const t = (en, ar) => self._t(en, ar);
            const name    = self._escapeHTML(loc.name    || 'Uellow');
            const address = self._escapeHTML(loc.address || '');
            const phone   = self._escapeHTML(loc.phone   || '');
            const wa      = self._escapeHTML(loc.whatsapp|| '');
            const hours   = self._escapeHTML(loc.hours   || '');
            const photos  = Array.isArray(loc.photos) ? loc.photos : [];

            let mapQuery = '';
            if (loc.lat && loc.lng)      mapQuery = loc.lat + ',' + loc.lng;
            else if (loc.address)         mapQuery = encodeURIComponent(loc.address);
            else if (loc.name)            mapQuery = encodeURIComponent(loc.name);
            const mapsLink = loc.map_url || `https://www.google.com/maps?q=${mapQuery}`;
            const embedSrc = `https://maps.google.com/maps?q=${mapQuery}&output=embed&z=15`;

            const div = document.createElement('div');
            div.className = 'beena-msg beena-msg-ai beena-cloc-card';
            div.innerHTML = `
                <div class="beena-cloc-head">
                    <div class="beena-cloc-icon">📍</div>
                    <div class="beena-cloc-titles">
                        <div class="beena-cloc-name">${name}</div>
                        ${address ? `<div class="beena-cloc-addr">${address}</div>` : ''}
                    </div>
                </div>

                <div class="beena-cloc-map">
                    <iframe src="${embedSrc}" loading="lazy"
                            referrerpolicy="no-referrer-when-downgrade"
                            allowfullscreen></iframe>
                </div>

                ${photos.length ? `
                <div class="beena-cloc-photos">
                    ${photos.map((p) => `<img src="${self._escapeHTML(p)}" alt="" class="beena-cloc-photo" onerror="this.style.display='none'">`).join('')}
                </div>` : ''}

                <div class="beena-cloc-meta">
                    ${phone ? `<a class="beena-cloc-meta-item" href="tel:${phone}">📞 ${phone}</a>` : ''}
                    ${wa    ? `<a class="beena-cloc-meta-item" target="_blank"
                                href="https://wa.me/${wa.replace(/[^0-9]/g,'')}">💬 WhatsApp</a>` : ''}
                    ${hours ? `<span class="beena-cloc-meta-item">🕒 ${hours}</span>` : ''}
                </div>

                <div class="beena-cloc-actions">
                    <a class="beena-cart-btn beena-cart-btn-primary"
                       href="${mapsLink}" target="_blank" rel="noopener" data-beena-external="1">
                        🗺️ ${t('Open in Google Maps', 'افتح في Google Maps')}
                    </a>
                    ${phone ? `<a class="beena-cart-btn beena-cart-btn-link" href="tel:${phone}">📞 ${t('Call us', 'اتصل بنا')}</a>` : ''}
                </div>`;
            this.messagesEl.appendChild(div);
            this._scrollBottom();

            // Lightbox on photo click
            div.querySelectorAll('.beena-cloc-photo').forEach(img => {
                img.addEventListener('click', () => self._openLightbox(img.src));
            });
        };

        window.BeenaApp.prototype._showLocation = function(loc) {
            if (!loc) return;
            const self = this;
            const t = (en, ar) => self._t(en, ar);
            const name    = self._escapeHTML(loc.name || t('Location', 'الموقع'));
            const address = loc.address ? self._escapeHTML(loc.address) : '';
            const phone   = loc.phone   ? self._escapeHTML(loc.phone)   : '';
            const hours   = loc.hours   ? self._escapeHTML(loc.hours)   : '';

            let mapQuery = '';
            if (loc.lat != null && loc.lng != null) {
                mapQuery = `${loc.lat},${loc.lng}`;
            } else if (loc.address) {
                mapQuery = encodeURIComponent(loc.address);
            } else if (loc.name) {
                mapQuery = encodeURIComponent(loc.name);
            }

            const mapsLink  = `https://www.google.com/maps?q=${mapQuery}`;
            const embedSrc  = `https://maps.google.com/maps?q=${mapQuery}&output=embed&z=15`;

            const div = document.createElement('div');
            div.className = 'beena-msg beena-msg-ai beena-loc-card';
            div.innerHTML = `
                <div class="beena-loc-head">
                    <div class="beena-loc-icon">📍</div>
                    <div class="beena-loc-titles">
                        <div class="beena-loc-name">${name}</div>
                        ${address ? `<div class="beena-loc-address">${address}</div>` : ''}
                    </div>
                </div>
                <div class="beena-loc-map">
                    <iframe src="${embedSrc}" loading="lazy"
                            referrerpolicy="no-referrer-when-downgrade"
                            allowfullscreen></iframe>
                </div>
                ${(phone || hours) ? `<div class="beena-loc-meta">
                    ${phone ? `<a class="beena-loc-meta-item" href="tel:${phone}">📞 ${phone}</a>` : ''}
                    ${hours ? `<span class="beena-loc-meta-item">🕒 ${hours}</span>` : ''}
                </div>` : ''}
                <div class="beena-loc-actions">
                    <a class="beena-loc-btn beena-loc-btn-primary" href="${mapsLink}" target="_blank" rel="noopener">
                        🗺️ ${t('Open in Google Maps', 'افتح في Google Maps')}
                    </a>
                </div>`;
            this.messagesEl.appendChild(div);
            this._scrollBottom();
        };

        // ── Fit Check card (per-area + overall %) ─────────────────────────
        window.BeenaApp.prototype._showFitCheck = function(data) {
            if (!data) return;
            const self  = this;
            const state = data.state || 'error';
            const t = (en, ar) => self._t(en, ar);

            const div = document.createElement('div');
            div.className = 'beena-msg beena-msg-ai beena-fit-card';

            // ── Header (always shown) ──
            const header = `
                <div class="beena-fit-head">
                    <div class="beena-fit-icon">📏</div>
                    <div class="beena-fit-titles">
                        <div class="beena-fit-title">${t('Size Fit Check', 'فحص توافق المقاس')}</div>
                        <div class="beena-fit-sub">${t('Comparing this product\'s sizing to your saved measurements', 'مقارنة مقاسات المنتج بمقاساتك المحفوظة')}</div>
                    </div>
                </div>`;

            const msg = data.message
                ? `<div class="beena-fit-msg">${self._escapeHTML(data.message)}</div>` : '';

            // ── Passive states ──
            if (state === 'needs_login') {
                div.innerHTML = header + msg +
                    `<button type="button" data-action="beena-signin" class="beena-fit-btn beena-fit-btn-primary">🔑 ${t('Sign in', 'سجّل دخولك')}</button>`;
                this.messagesEl.appendChild(div); this._scrollBottom(); return;
            }
            if (state === 'needs_profile') {
                div.innerHTML = header + msg +
                    `<a href="${data.measurements_url || '/my/measurements'}" class="beena-fit-btn beena-fit-btn-primary" style="text-decoration:none;display:inline-block">📐 ${t('Complete my measurements', 'أكمل مقاساتي')}</a>`;
                this.messagesEl.appendChild(div); this._scrollBottom(); return;
            }
            if (['no_product', 'product_not_found', 'no_chart', 'error'].includes(state)) {
                div.innerHTML = header + msg;
                this.messagesEl.appendChild(div); this._scrollBottom(); return;
            }

            // ── Ready state: full card with breakdown ──
            const overall = Number(data.overall_pct || 0);
            const color   = data.fit_color || 'yellow';
            const colorMap = {
                green:  '#1D9E75',
                yellow: '#F5C320',
                orange: '#E89B23',
                red:    '#E24B4A',
            };
            const trackBg = '#F1EFE7';
            const gaugeColor = colorMap[color] || colorMap.yellow;
            const dash       = (overall * 1.76).toFixed(1);   // circumference ~ 2*pi*28 = 175.9

            // Localize fit label that came from the server (Arabic by default)
            const fitLabelMap = {
                'مناسب تماماً': {en: 'Perfect fit',     ar: 'مناسب تماماً'},
                'مناسب':        {en: 'Good fit',        ar: 'مناسب'},
                'مقبول':        {en: 'Acceptable fit',  ar: 'مقبول'},
                'غير مناسب':    {en: 'Poor fit',        ar: 'غير مناسب'},
            };
            const fl = fitLabelMap[data.fit_label] || {en: data.fit_label||'', ar: data.fit_label||''};
            const fitLabelText = t(fl.en, fl.ar);

            // SVG ring gauge
            const gauge = `
                <div class="beena-fit-gauge">
                    <svg width="78" height="78" viewBox="0 0 64 64">
                        <circle cx="32" cy="32" r="28" fill="none" stroke="${trackBg}" stroke-width="7"/>
                        <circle cx="32" cy="32" r="28" fill="none" stroke="${gaugeColor}" stroke-width="7"
                                stroke-linecap="round"
                                stroke-dasharray="${dash} 175.9"
                                transform="rotate(-90 32 32)"/>
                        <text x="32" y="37" text-anchor="middle"
                              font-size="15" font-weight="700" fill="#412402"
                              font-family="inherit">${overall}%</text>
                    </svg>
                    <div class="beena-fit-gauge-label" style="color:${gaugeColor}">${self._escapeHTML(fitLabelText)}</div>
                </div>`;

            // Product summary
            const productImg = data.product_image_url
                ? `<img class="beena-fit-product-img" src="${data.product_image_url}" alt="${self._escapeHTML(data.product_name||'')}" onerror="this.style.display='none'">`
                : '';
            const price = Number(data.product_price_kd || 0);
            const priceTxt = price ? `<div class="beena-fit-price">${price.toFixed(3)} KD</div>` : '';

            const productBlock = `
                <div class="beena-fit-product">
                    ${productImg}
                    <div class="beena-fit-product-info">
                        <div class="beena-fit-product-name">${self._escapeHTML(data.product_name||'')}</div>
                        <div class="beena-fit-size-pill">${t('Size:', 'المقاس:')} <strong>${self._escapeHTML(data.size||'-')}</strong></div>
                        ${priceTxt}
                    </div>
                    ${gauge}
                </div>`;

            // Localize area labels (server sends Arabic by default)
            const areaLabelMap = {
                'الصدر':     {en: 'Chest'},
                'الكتف':     {en: 'Shoulder'},
                'الكم':      {en: 'Sleeve'},
                'الطول':     {en: 'Length'},
                'الوسط':     {en: 'Waist'},
                'الورك':     {en: 'Hip'},
                'الساق':     {en: 'Inseam'},
                'الفخذ':     {en: 'Thigh'},
                'طول القدم': {en: 'Foot length'},
            };

            // Per-area breakdown
            const fitWordMap = {
                tight:       {en: 'Tight',        ar: 'ضيّق',     icon: '⬇', cls: 'tight'},
                comfortable: {en: 'Comfortable ✓', ar: 'مريح ✓',   icon: '✓', cls: 'good'},
                loose:       {en: 'Loose',        ar: 'واسع',     icon: '⬆', cls: 'loose'},
                unknown:     {en: 'Unknown',      ar: 'غير محدّد', icon: '·', cls: 'unknown'},
            };
            const areas = Array.isArray(data.areas) ? data.areas : [];
            const areasHtml = areas.map(a => {
                const w = fitWordMap[a.fit] || fitWordMap.unknown;
                const lblAr = a.label || a.key || '';
                const lblEn = (areaLabelMap[lblAr] && areaLabelMap[lblAr].en) || lblAr;
                const diffTxt = (a.diff_cm != null)
                    ? `<span class="beena-fit-area-diff">${a.diff_cm > 0 ? '+' : ''}${a.diff_cm}cm</span>`
                    : '';
                const pctBar = (a.pct != null)
                    ? `<div class="beena-fit-area-bar"><div class="beena-fit-area-bar-fill ${w.cls}" style="width:${Math.max(5,a.pct)}%"></div></div>`
                    : '';
                return `
                    <div class="beena-fit-area">
                        <div class="beena-fit-area-row">
                            <span class="beena-fit-area-label">${self._escapeHTML(t(lblEn, lblAr))}</span>
                            <span class="beena-fit-area-verdict ${w.cls}">${w.icon} ${t(w.en, w.ar)}</span>
                            ${diffTxt}
                        </div>
                        ${pctBar}
                    </div>`;
            }).join('');

            // Alternate sizes (chips)
            const alts = Array.isArray(data.alternates) ? data.alternates : [];
            const altsHtml = alts.length ? `
                <div class="beena-fit-alts">
                    <div class="beena-fit-alts-title">${t('Other sizes:', 'مقاسات أخرى:')}</div>
                    <div class="beena-fit-alts-chips">
                        ${alts.map(r => `
                            <button type="button" class="beena-fit-alt-chip"
                                data-size="${self._escapeHTML(r.size)}"
                                data-pid="${data.product_id}">
                                ${self._escapeHTML(r.size)}
                                <span class="beena-fit-alt-pct" style="color:${colorMap[r.fit_color]||'#888'}">${r.overall_pct}%</span>
                            </button>`).join('')}
                    </div>
                </div>` : '';

            // CTA
            let cta = '';
            if (overall >= 80) {
                cta = `<button type="button" class="beena-fit-btn beena-fit-btn-primary" data-action="cart" data-pid="${data.product_id}" data-vid="${data.variant_id||0}">
                            🛒 ${t('Add to cart (size '+self._escapeHTML(data.size)+')', 'أضف للسلة (المقاس '+self._escapeHTML(data.size)+')')}
                       </button>`;
            } else if (overall >= 60) {
                cta = `<button type="button" class="beena-fit-btn beena-fit-btn-primary" data-action="cart" data-pid="${data.product_id}" data-vid="${data.variant_id||0}">
                            🛒 ${t('Add to cart anyway', 'أضف للسلة على أي حال')}
                       </button>`;
            } else {
                const better = alts.find(a => a.overall_pct > overall);
                if (better) {
                    cta = `<button type="button" class="beena-fit-btn beena-fit-btn-primary" data-action="recheck" data-pid="${data.product_id}" data-size="${self._escapeHTML(better.size)}">
                                💡 ${t('Try size '+self._escapeHTML(better.size)+' ('+better.overall_pct+'%)', 'جرّب المقاس '+self._escapeHTML(better.size)+' ('+better.overall_pct+'%)')}
                           </button>`;
                } else {
                    cta = `<button type="button" class="beena-fit-btn beena-fit-btn-secondary" disabled>${t('This size may not fit you', 'المقاس قد لا يناسبك')}</button>`;
                }
            }

            div.innerHTML = header + productBlock +
                `<div class="beena-fit-areas">${areasHtml}</div>` +
                altsHtml +
                `<div class="beena-fit-cta">${cta}</div>`;

            this.messagesEl.appendChild(div);
            this._scrollBottom();

            // Wire alternates → ask Beena to recheck with that size
            div.querySelectorAll('.beena-fit-alt-chip').forEach(btn => {
                btn.addEventListener('click', () => {
                    const sz = btn.dataset.size;
                    self._send(t('Check size '+sz, 'افحص المقاس '+sz));
                });
            });
            // Wire CTAs
            div.querySelectorAll('.beena-fit-btn[data-action]').forEach(btn => {
                btn.addEventListener('click', async () => {
                    const action = btn.dataset.action;
                    if (action === 'cart') {
                        const vid = parseInt(btn.dataset.vid || '0', 10);
                        if (vid && window._beenaAddToCart) {
                            window._beenaAddToCart(vid, data.product_name);
                        } else {
                            self._send(t('Add size '+data.size+' to cart', 'أضف المقاس '+data.size+' للسلة'));
                        }
                    } else if (action === 'recheck') {
                        self._send(t('Check size '+btn.dataset.size, 'افحص المقاس '+btn.dataset.size));
                    }
                });
            });
        };

        // ── Fit replay banner (compact reminder of last check) ────────────
        window.BeenaApp.prototype._showFitReplay = function(data) {
            if (!data) return;
            const self = this;
            const t = (en, ar) => self._t(en, ar);

            // Dedup: don't show twice in same tab for same product
            this._fitReplayShown = this._fitReplayShown || new Set();
            if (this._fitReplayShown.has(data.product_id)) return;
            this._fitReplayShown.add(data.product_id);

            const colorMap = {green:'#1D9E75', yellow:'#F5C320', orange:'#E89B23', red:'#E24B4A'};
            const c = colorMap[data.fit_color] || colorMap.yellow;
            const days = data.ago_days || 1;
            const dayTxt =
                days === 1  ? t('Yesterday', 'أمس') :
                days <= 7   ? t(days+' days ago',                    'قبل '+days+' أيام') :
                days <= 30  ? t(Math.round(days/7)+' weeks ago',     'قبل '+Math.round(days/7)+' أسابيع') :
                              t(Math.round(days/30)+' months ago',   'قبل '+Math.round(days/30)+' شهور');

            const div = document.createElement('div');
            div.className = 'beena-msg beena-msg-ai beena-replay-card';
            div.innerHTML = `
                <div class="beena-replay-head">
                    <div class="beena-replay-icon">🕒</div>
                    <div class="beena-replay-body">
                        <div class="beena-replay-title">${t('Last check: size', 'آخر فحص: المقاس')} <strong>${self._escapeHTML(data.size||'-')}</strong></div>
                        <div class="beena-replay-meta">
                            <span class="beena-replay-pct" style="color:${c}">${data.overall_pct}%</span>
                            <span class="beena-replay-date">${dayTxt}</span>
                        </div>
                    </div>
                    <button type="button" class="beena-replay-dismiss" title="${t('Dismiss', 'إخفاء')}">✕</button>
                </div>
                <div class="beena-replay-actions">
                    <button type="button" class="beena-replay-btn beena-replay-btn-primary" data-action="recheck">
                        🔄 ${t('Re-check', 'أعد الفحص')}
                    </button>
                    <a href="/my/fit-history" class="beena-replay-btn beena-replay-btn-secondary">
                        📜 ${t('Fit history', 'سجل الفحوصات')}
                    </a>
                </div>`;
            this.messagesEl.appendChild(div);
            this._scrollBottom();

            const recheckBtn = div.querySelector('.beena-replay-btn-primary');
            recheckBtn.addEventListener('click', () => {
                self._send(t('Check size '+data.size+' for me', 'افحص توافق المقاس '+data.size+' عليّ'));
            });
            const dismissBtn = div.querySelector('.beena-replay-dismiss');
            dismissBtn.addEventListener('click', () => div.remove());
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
                if (extra.tryon)        this._showTryOn(extra.tryon);
                if (extra.fit_check)    this._showFitCheck(extra.fit_check);
                if (extra.fit_replay)   this._showFitReplay(extra.fit_replay);
                if (extra.cart_view)        this._showCartView(extra.cart_view);
                if (extra.checkout)         this._showCheckout(extra.checkout);
                if (extra.quote)            this._showQuote(extra.quote);
                if (extra.company_location) this._showCompanyLocation(extra.company_location);
                if (extra.loyalty)         this._showLoyalty(extra.loyalty);
                if (extra.upsell)          this._showUpsell(extra.upsell);
                if (extra.payment_options) this._showPaymentOptions(extra.payment_options);
                if (extra.location)        this._showLocation(extra.location);
                if (extra.locations && Array.isArray(extra.locations))
                    extra.locations.forEach(loc => this._showLocation(loc));

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


})();

})();
