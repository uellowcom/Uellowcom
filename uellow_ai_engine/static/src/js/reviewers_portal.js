/**
 * Uellow Reviewers — reviewers_portal.js
 * Full portal page for reviewers: dashboard, chat, earnings, settings
 */

(function () {
    'use strict';

    // ── API Helpers ───────────────────────────────────────────────────────────

    function post(url, params) {
        return fetch(url, {
            method:  'POST',
            headers: {'Content-Type': 'application/json'},
            body:    JSON.stringify({jsonrpc: '2.0', method: 'call', id: 1, params}),
        }).then(r => r.json()).then(d => d.result || {});
    }

    function stars(rating) {
        const full  = Math.round(rating || 0);
        const empty = 5 - full;
        return '★'.repeat(full) + '☆'.repeat(empty);
    }

    // ── State ─────────────────────────────────────────────────────────────────

    let reviewerData    = null;
    let activeSession   = null;
    let pendingRequests = [];
    let chatPollTimer   = null;
    let countdownTimer  = null;
    let currentTab      = 'dashboard';

    // ── Boot ──────────────────────────────────────────────────────────────────

    async function init() {
        const dashRoot     = document.getElementById('reviewer-portal-root');
        const registerRoot = document.getElementById('reviewer-register-root');

        if (dashRoot) {
            dashRoot.innerHTML = renderSkeleton();
            await loadDashboard(dashRoot);
        }

        if (registerRoot) {
            renderRegisterForm(registerRoot);
        }
    }

    // ── Skeleton loader ───────────────────────────────────────────────────────

    function renderSkeleton() {
        return `<div style="max-width:900px;margin:0 auto;padding:20px 16px">
            <div style="background:#F5C320;border-radius:14px;padding:16px;display:flex;align-items:center;gap:12px;margin-bottom:16px;animation:rvpulse 1.2s infinite">
                <div style="width:48px;height:48px;border-radius:50%;background:rgba(0,0,0,.1)"></div>
                <div><div style="width:120px;height:14px;background:rgba(0,0,0,.1);border-radius:4px;margin-bottom:5px"></div>
                <div style="width:80px;height:10px;background:rgba(0,0,0,.08);border-radius:4px"></div></div>
            </div>
            <style>@keyframes rvpulse{0%,100%{opacity:.7}50%{opacity:1}}</style>
        </div>`;
    }

    // ── Load Dashboard ────────────────────────────────────────────────────────

    async function loadDashboard(root) {
        const data = await post('/reviewers/dashboard', {});

        if (!data.is_reviewer) {
            root.innerHTML = renderNotReviewer();
            return;
        }

        reviewerData    = data.reviewer;
        pendingRequests = data.pending_requests || [];
        activeSession   = data.active_session;

        root.innerHTML  = renderPortal();
        bindPortalEvents();

        if (activeSession) {
            switchTab('chat');
            startChatPoll();
        } else {
            startRequestPoll();
        }
    }

    // ── Not a reviewer ────────────────────────────────────────────────────────

    function renderNotReviewer() {
        return `
<div style="max-width:500px;margin:60px auto;padding:0 16px;text-align:center">
    <div style="font-size:48px;margin-bottom:16px">🐝</div>
    <h2 style="font-size:22px;font-weight:500;margin-bottom:8px">انضم لفريق الريفيورز</h2>
    <p style="color:#888;margin-bottom:24px;line-height:1.6">
        شارك خبرتك وساعد العملاء في اتخاذ قرار الشراء — واكسب عمولة على كل عملية ناجحة.
    </p>
    <a href="/reviewer/register"
       style="display:inline-block;background:#F5C320;color:#1A1A1A;padding:12px 28px;border-radius:8px;font-weight:700;text-decoration:none;font-size:14px">
        سجّل كريفيور الآن
    </a>
    <div style="margin-top:32px;display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px">
        <div style="background:#fff;border:0.5px solid rgba(0,0,0,.1);border-radius:10px;padding:14px;text-align:center">
            <div style="font-size:22px;font-weight:700;color:#F5C320">5%</div>
            <div style="font-size:11px;color:#888;margin-top:3px">عمولة على كل مبيعة</div>
        </div>
        <div style="background:#fff;border:0.5px solid rgba(0,0,0,.1);border-radius:10px;padding:14px;text-align:center">
            <div style="font-size:22px;font-weight:700;color:#1D9E75">مرن</div>
            <div style="font-size:11px;color:#888;margin-top:3px">اشتغل وقت ما تريد</div>
        </div>
        <div style="background:#fff;border:0.5px solid rgba(0,0,0,.1);border-radius:10px;padding:14px;text-align:center">
            <div style="font-size:22px;font-weight:700;color:#534AB7">سهل</div>
            <div style="font-size:11px;color:#888;margin-top:3px">فقط شارك رأيك</div>
        </div>
    </div>
</div>`;
    }

    // ── Main Portal HTML ──────────────────────────────────────────────────────

    function renderPortal() {
        const r        = reviewerData;
        const levelMap = {starter:'⭐ Starter', regular:'⭐⭐ Regular', expert:'⭐⭐⭐ Expert', elite:'⭐⭐⭐⭐ Elite'};
        const badgeColor = {elite:'#EEEDFE', expert:'#EAF3DE', regular:'#E6F1FB', starter:'#F5F4F2'};
        const badgeText  = {elite:'#3C3489', expert:'#27500A', regular:'#0C447C', starter:'#5F5E5A'};

        return `
<div style="max-width:900px;margin:0 auto;padding:20px 16px;font-family:inherit">

    <!-- Header -->
    <div style="background:#F5C320;border-radius:14px;padding:16px 20px;display:flex;align-items:center;gap:14px;margin-bottom:16px">
        <div style="width:50px;height:50px;border-radius:50%;background:#fff;display:flex;align-items:center;justify-content:center;font-size:18px;font-weight:700;color:#1A1A1A;flex-shrink:0">
            ${r.name ? r.name.charAt(0) : '?'}
        </div>
        <div style="flex:1">
            <div style="font-size:16px;font-weight:700;color:#1A1A1A">${r.name}</div>
            <div style="display:flex;align-items:center;gap:8px;margin-top:3px">
                <span style="font-size:11px;background:${badgeColor[r.level]};color:${badgeText[r.level]};padding:2px 8px;border-radius:4px;font-weight:600">${levelMap[r.level] || r.level}</span>
                <span style="color:#F5A020;font-size:12px">${stars(r.rating)}</span>
                <span style="font-size:11px;color:#854F0B">${r.rating} · ${r.review_count} مراجعة</span>
            </div>
        </div>
        <div style="display:flex;align-items:center;gap:8px">
            <span id="rv-online-label" style="font-size:11px;color:#854F0B;font-weight:500">${r.is_online ? 'أونلاين' : 'أوفلاين'}</span>
            <div id="rv-online-toggle"
                 style="width:36px;height:20px;border-radius:10px;background:${r.is_online ? '#1A1A1A' : '#ccc'};position:relative;cursor:pointer;transition:background .2s"
                 onclick="window._rvToggleOnline()">
                <div style="position:absolute;top:3px;${r.is_online ? 'left:19px' : 'left:3px'};width:14px;height:14px;border-radius:50%;background:#fff;transition:left .2s"></div>
            </div>
        </div>
    </div>

    <!-- Stats -->
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:16px">
        <div style="background:#fff;border:0.5px solid rgba(0,0,0,.08);border-radius:10px;padding:12px;text-align:center">
            <div style="font-size:20px;font-weight:700;color:#1D9E75">${r.wallet_balance ? r.wallet_balance.toFixed(3) : '0.000'}</div>
            <div style="font-size:10px;color:#888;margin-top:2px">KD محفظتي</div>
        </div>
        <div style="background:#fff;border:0.5px solid rgba(0,0,0,.08);border-radius:10px;padding:12px;text-align:center">
            <div style="font-size:20px;font-weight:700;color:#1A1A1A">${r.review_count || 0}</div>
            <div style="font-size:10px;color:#888;margin-top:2px">مراجعة</div>
        </div>
        <div style="background:#fff;border:0.5px solid rgba(0,0,0,.08);border-radius:10px;padding:12px;text-align:center">
            <div style="font-size:20px;font-weight:700;color:#534AB7">${r.conversion_rate ? r.conversion_rate.toFixed(0) : 0}%</div>
            <div style="font-size:10px;color:#888;margin-top:2px">معدل التحويل</div>
        </div>
        <div style="background:#fff;border:0.5px solid rgba(0,0,0,.08);border-radius:10px;padding:12px;text-align:center">
            <div style="font-size:20px;font-weight:700;color:#F5C320">${r.rating || 5}</div>
            <div style="font-size:10px;color:#888;margin-top:2px">تقييمي</div>
        </div>
    </div>

    <!-- Tabs -->
    <div style="display:flex;gap:4px;margin-bottom:14px;background:#fff;border-radius:10px;padding:4px;border:0.5px solid rgba(0,0,0,.08)">
        ${['dashboard','chat','requests','earnings','settings'].map(tab => {
            const labels = {dashboard:'الرئيسية', chat:'الشات', requests:'الطلبات', earnings:'الأرباح', settings:'الإعدادات'};
            const icons  = {dashboard:'ti-layout-dashboard', chat:'ti-messages', requests:'ti-bell', earnings:'ti-coin', settings:'ti-settings'};
            return `<button id="rv-tab-${tab}"
                onclick="window._rvSwitchTab('${tab}')"
                style="flex:1;padding:8px 6px;border:none;border-radius:7px;cursor:pointer;font-family:inherit;font-size:12px;font-weight:500;transition:background .15s;background:${currentTab===tab?'#F5C320':'transparent'};color:${currentTab===tab?'#1A1A1A':'#888'}">
                <i class="ti ${icons[tab]}" style="font-size:14px;display:block;margin:0 auto 2px" aria-hidden="true"></i>
                ${labels[tab]}
            </button>`;
        }).join('')}
    </div>

    <!-- Tab Content -->
    <div id="rv-tab-content">${renderTab(currentTab)}</div>

</div>`;
    }

    // ── Tab Content ───────────────────────────────────────────────────────────

    function renderTab(tab) {
        switch(tab) {
            case 'dashboard': return renderDashboardTab();
            case 'chat':      return renderChatTab();
            case 'requests':  return renderRequestsTab();
            case 'earnings':  return renderEarningsTab();
            case 'settings':  return renderSettingsTab();
            default:          return renderDashboardTab();
        }
    }

    function renderDashboardTab() {
        const pending = pendingRequests.slice(0, 5);
        return `
<div>
    ${pending.length ? `
    <div style="margin-bottom:16px">
        <div style="font-size:13px;font-weight:600;color:#1A1A1A;margin-bottom:9px;display:flex;align-items:center;gap:6px">
            <span style="width:8px;height:8px;border-radius:50%;background:#E24B4A;display:inline-block"></span>
            ${pending.length} طلب جديد بانتظارك
        </div>
        ${pending.map(req => renderRequestCard(req)).join('')}
    </div>` : `
    <div style="background:#fff;border-radius:12px;padding:28px;text-align:center;border:0.5px solid rgba(0,0,0,.08);margin-bottom:16px">
        <div style="font-size:32px;margin-bottom:8px">🐝</div>
        <div style="font-size:14px;color:#888">لا توجد طلبات جديدة حالياً</div>
        <div style="font-size:12px;color:#aaa;margin-top:4px">تأكد أنك أونلاين لاستقبال الطلبات</div>
    </div>`}

    ${activeSession ? `
    <div style="background:#FFF8E1;border:1px solid #F5C320;border-radius:12px;padding:14px;margin-bottom:16px;display:flex;align-items:center;gap:12px;cursor:pointer" onclick="window._rvSwitchTab('chat')">
        <div style="width:36px;height:36px;border-radius:50%;background:#F5C320;display:flex;align-items:center;justify-content:center;font-size:16px">💬</div>
        <div style="flex:1">
            <div style="font-size:13px;font-weight:600;color:#1A1A1A">لديك جلسة نشطة</div>
            <div style="font-size:11px;color:#854F0B">اضغط للذهاب للشات</div>
        </div>
        <i class="ti ti-arrow-left" style="font-size:18px;color:#854F0B" aria-hidden="true"></i>
    </div>` : ''}

    <div style="background:#fff;border:0.5px solid rgba(0,0,0,.08);border-radius:12px;padding:14px">
        <div style="font-size:13px;font-weight:600;color:#1A1A1A;margin-bottom:10px">أنواع الجلسات المفعّلة</div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">
            ${[
                {key:'allow_written', icon:'ti-writing', name:'رأي مكتوب',  price: reviewerData.price_written},
                {key:'allow_chat',    icon:'ti-messages', name:'شات مباشر', price: reviewerData.price_chat},
            ].map(t => `
            <div style="background:#F9F8F5;border-radius:8px;padding:10px;display:flex;align-items:center;gap:8px">
                <i class="ti ${t.icon}" style="font-size:18px;color:#F5C320" aria-hidden="true"></i>
                <div>
                    <div style="font-size:11px;font-weight:600;color:#1A1A1A">${t.name}</div>
                    <div style="font-size:10px;color:#854F0B">${(t.price||0).toFixed(3)} KD</div>
                </div>
            </div>`).join('')}
        </div>
    </div>
</div>`;
    }

    function renderRequestCard(req) {
        const typeIcon = {written:'ti-writing', chat:'ti-messages', photo:'ti-camera', video:'ti-video'};
        const typeLabel = {written:'رأي مكتوب', chat:'شات مباشر', photo:'صورة + رأي', video:'فيديو'};
        const timeAgo = req.create_date ? 'منذ قليل' : '';

        return `
<div style="background:#fff;border:0.5px solid rgba(0,0,0,.08);border-radius:10px;padding:12px;margin-bottom:8px;display:flex;gap:11px;align-items:flex-start">
    <div style="width:38px;height:38px;border-radius:8px;background:#F9F8F5;display:flex;align-items:center;justify-content:center;flex-shrink:0">
        <i class="ti ${typeIcon[req.session_type]||'ti-help'}" style="font-size:18px;color:#888" aria-hidden="true"></i>
    </div>
    <div style="flex:1">
        <div style="font-size:13px;font-weight:600;color:#1A1A1A">${req.product && req.product.name ? req.product.name : 'منتج'}</div>
        <div style="font-size:11px;color:#888;margin-top:2px">${typeLabel[req.session_type]||''} · ${(req.fee||0).toFixed(3)} KD</div>
        <div style="font-size:10px;color:#aaa;margin-top:2px">${timeAgo}</div>
    </div>
    <div style="display:flex;gap:6px;flex-shrink:0">
        <button onclick="window._rvAcceptRequest(${req.id})"
                style="background:#F5C320;border:none;border-radius:7px;padding:6px 14px;font-size:12px;font-weight:600;cursor:pointer;font-family:inherit">
            قبول
        </button>
        <button onclick="window._rvDeclineRequest(${req.id})"
                style="background:#fff;border:0.5px solid rgba(0,0,0,.12);border-radius:7px;padding:6px 10px;font-size:12px;cursor:pointer;font-family:inherit;color:#888">
            تجاهل
        </button>
    </div>
</div>`;
    }

    function renderChatTab() {
        if (!activeSession) {
            return `<div style="background:#fff;border-radius:12px;padding:40px;text-align:center;border:0.5px solid rgba(0,0,0,.08)">
                <div style="font-size:32px;margin-bottom:8px">💬</div>
                <div style="font-size:14px;color:#888">لا توجد جلسة نشطة حالياً</div>
                <div style="font-size:12px;color:#aaa;margin-top:4px">اقبل طلباً لبدء جلسة</div>
            </div>`;
        }

        const req      = activeSession;
        const messages = req.messages || [];

        return `
<div style="background:#fff;border:0.5px solid rgba(0,0,0,.08);border-radius:12px;overflow:hidden">
    <!-- Chat Header -->
    <div style="background:#F5C320;padding:12px 16px;display:flex;align-items:center;gap:10px">
        <div style="width:36px;height:36px;border-radius:50%;background:#fff;display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:700;color:#1A1A1A">
            ${req.reviewer && req.reviewer.name ? req.reviewer.name.charAt(0) : '?'}
        </div>
        <div style="flex:1">
            <div style="font-size:13px;font-weight:600;color:#1A1A1A">عميل</div>
            <div style="font-size:10px;color:#854F0B">جلسة ${req.session_type === 'chat' ? 'شات مباشر' : 'نشطة'}</div>
        </div>
        <div id="rv-countdown" style="background:rgba(0,0,0,.1);border-radius:6px;padding:3px 10px;font-size:12px;font-weight:600;color:#1A1A1A;font-family:monospace">
            --:--
        </div>
    </div>

    <!-- Product Context -->
    ${req.product && req.product.name ? `
    <div style="background:#FFF8E1;border-bottom:0.5px solid rgba(245,195,32,.3);padding:8px 16px;display:flex;align-items:center;gap:9px">
        <i class="ti ti-tag" style="font-size:16px;color:#854F0B" aria-hidden="true"></i>
        <div style="font-size:11px;font-weight:600;color:#854F0B">${req.product.name}</div>
    </div>` : ''}

    <!-- Messages -->
    <div id="rv-chat-messages" style="min-height:280px;max-height:360px;overflow-y:auto;padding:14px;display:flex;flex-direction:column;gap:8px">
        ${messages.length ? messages.map(m => `
        <div style="max-width:85%;padding:9px 12px;font-size:13px;line-height:1.5;
             border-radius:${m.sender==='reviewer' ? '10px 0 10px 10px' : '0 10px 10px 10px'};
             background:${m.sender==='reviewer' ? '#F5C320' : '#F5F4F2'};
             color:${m.sender==='reviewer' ? '#1A1A1A' : '#1A1A1A'};
             align-self:${m.sender==='reviewer' ? 'flex-end' : 'flex-start'};
             font-weight:${m.sender==='reviewer' ? '500' : '400'}">
            ${m.text}
        </div>`).join('') : `
        <div style="text-align:center;color:#aaa;font-size:12px;margin:auto;padding:20px 0">
            ابدأ المحادثة — العميل ينتظر رأيك
        </div>`}
    </div>

    <!-- Verdict Buttons -->
    <div style="padding:10px 14px;border-top:0.5px solid rgba(0,0,0,.07);background:#F9F8F5">
        <div style="font-size:11px;color:#888;margin-bottom:6px">رأيك النهائي:</div>
        <div style="display:flex;gap:6px;margin-bottom:8px">
            <button onclick="window._rvSubmitVerdict('recommend')"
                    style="flex:1;padding:8px;border-radius:8px;border:none;cursor:pointer;font-family:inherit;font-size:12px;font-weight:600;background:#E1F5EE;color:#085041">
                ✓ أنصح بالشراء
            </button>
            <button onclick="window._rvSubmitVerdict('neutral')"
                    style="flex:1;padding:8px;border-radius:8px;border:0.5px solid rgba(0,0,0,.1);cursor:pointer;font-family:inherit;font-size:12px;background:#fff;color:#888">
                ◉ محايد
            </button>
            <button onclick="window._rvSubmitVerdict('not_recommend')"
                    style="flex:1;padding:8px;border-radius:8px;border:none;cursor:pointer;font-family:inherit;font-size:12px;font-weight:600;background:#FCEBEB;color:#791F1F">
                ✗ لا أنصح
            </button>
        </div>
    </div>

    <!-- Input -->
    <div style="padding:10px 14px;border-top:0.5px solid rgba(0,0,0,.07);display:flex;gap:7px;align-items:center">
        <input id="rv-portal-input" type="text" placeholder="اكتب رسالتك..."
               style="flex:1;border:0.5px solid rgba(0,0,0,.1);border-radius:20px;padding:9px 14px;font-size:13px;outline:none;font-family:inherit;background:#F9F8F5;direction:rtl"
               onkeydown="if(event.key==='Enter')window._rvPortalSend()">
        <button onclick="window._rvPortalSend()"
                style="width:36px;height:36px;border-radius:50%;background:#F5C320;border:none;cursor:pointer;font-size:16px;display:flex;align-items:center;justify-content:center">
            ➤
        </button>
    </div>
</div>`;
    }

    function renderRequestsTab() {
        return `
<div>
    <div style="font-size:13px;font-weight:600;color:#1A1A1A;margin-bottom:10px">الطلبات المعلقة (${pendingRequests.length})</div>
    ${pendingRequests.length
        ? pendingRequests.map(req => renderRequestCard(req)).join('')
        : `<div style="background:#fff;border-radius:12px;padding:28px;text-align:center;border:0.5px solid rgba(0,0,0,.08);color:#888">
            لا توجد طلبات معلقة
           </div>`}
</div>`;
    }

    function renderEarningsTab() {
        const r = reviewerData;
        return `
<div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:16px">
        <div style="background:#E1F5EE;border-radius:12px;padding:16px;text-align:center">
            <div style="font-size:24px;font-weight:700;color:#085041">${(r.wallet_balance||0).toFixed(3)}</div>
            <div style="font-size:11px;color:#1D9E75;margin-top:3px">KD في المحفظة</div>
        </div>
        <div style="background:#fff;border:0.5px solid rgba(0,0,0,.08);border-radius:12px;padding:16px;text-align:center">
            <div style="font-size:24px;font-weight:700;color:#1A1A1A">${(r.total_earned||0).toFixed(3)}</div>
            <div style="font-size:11px;color:#888;margin-top:3px">KD إجمالي مكتسب</div>
        </div>
    </div>

    <div style="background:#fff;border:0.5px solid rgba(0,0,0,.08);border-radius:12px;padding:14px;margin-bottom:12px">
        <div style="font-size:13px;font-weight:600;color:#1A1A1A;margin-bottom:10px">معلومات العمولة</div>
        <div style="display:flex;flex-direction:column;gap:6px">
            <div style="display:flex;justify-content:space-between;font-size:12px;padding:6px 0;border-bottom:0.5px solid rgba(0,0,0,.06)">
                <span style="color:#888">رأي مكتوب + شراء</span>
                <span style="font-weight:600;color:#1A1A1A">5% من قيمة الطلب</span>
            </div>
            <div style="display:flex;justify-content:space-between;font-size:12px;padding:6px 0;border-bottom:0.5px solid rgba(0,0,0,.06)">
                <span style="color:#888">شات مباشر + شراء</span>
                <span style="font-weight:600;color:#1A1A1A">8% من قيمة الطلب</span>
            </div>
            <div style="display:flex;justify-content:space-between;font-size:12px;padding:6px 0">
                <span style="color:#888">بونص شراء خلال ساعة</span>
                <span style="font-weight:600;color:#1D9E75">+2% إضافي</span>
            </div>
        </div>
    </div>

    <button onclick="window._rvRequestPayout()"
            style="width:100%;background:#F5C320;border:none;border-radius:10px;padding:13px;font-size:14px;font-weight:700;cursor:pointer;font-family:inherit">
        طلب صرف الرصيد
    </button>
</div>`;
    }

    function renderSettingsTab() {
        const r = reviewerData;
        return `
<div style="background:#fff;border:0.5px solid rgba(0,0,0,.08);border-radius:12px;overflow:hidden">
    <div style="padding:14px 16px;border-bottom:0.5px solid rgba(0,0,0,.06)">
        <div style="font-size:13px;font-weight:600;color:#1A1A1A;margin-bottom:2px">أنواع الجلسات</div>
        <div style="font-size:11px;color:#aaa">فعّل أو أوقف كل نوع</div>
    </div>
    ${[
        {key:'allow_written', label:'رأي مكتوب',  icon:'ti-writing',  val: r.allow_written},
        {key:'allow_chat',    label:'شات مباشر',   icon:'ti-messages', val: r.allow_chat},
        {key:'allow_photo',   label:'صورة + رأي',  icon:'ti-camera',   val: r.allow_photo},
    ].map(item => `
    <div style="display:flex;align-items:center;justify-content:space-between;padding:12px 16px;border-bottom:0.5px solid rgba(0,0,0,.06)">
        <div style="display:flex;align-items:center;gap:9px">
            <i class="ti ${item.icon}" style="font-size:18px;color:#888" aria-hidden="true"></i>
            <span style="font-size:13px;color:#1A1A1A">${item.label}</span>
        </div>
        <div style="width:36px;height:20px;border-radius:10px;background:${item.val ? '#F5C320' : '#ddd'};position:relative;cursor:pointer"
             onclick="window._rvToggleSetting('${item.key}')">
            <div style="position:absolute;top:3px;${item.val ? 'left:19px' : 'left:3px'};width:14px;height:14px;border-radius:50%;background:#fff;transition:left .2s"></div>
        </div>
    </div>`).join('')}
    <div style="padding:14px 16px">
        <div style="font-size:13px;font-weight:600;color:#1A1A1A;margin-bottom:10px">النبذة الشخصية</div>
        <textarea id="rv-bio-input" rows="3"
                  style="width:100%;border:0.5px solid rgba(0,0,0,.1);border-radius:8px;padding:10px;font-size:12px;font-family:inherit;resize:none;outline:none;direction:rtl"
                  placeholder="اكتب نبذة عنك...">${r.bio || ''}</textarea>
        <button onclick="window._rvSaveBio()"
                style="margin-top:8px;background:#F5C320;border:none;border-radius:8px;padding:8px 20px;font-size:12px;font-weight:600;cursor:pointer;font-family:inherit">
            حفظ
        </button>
    </div>
</div>`;
    }

    // ── Tab Switch ────────────────────────────────────────────────────────────

    function switchTab(tab) {
        currentTab = tab;

        // Update tab buttons
        ['dashboard','chat','requests','earnings','settings'].forEach(t => {
            const btn = document.getElementById(`rv-tab-${t}`);
            if (btn) {
                btn.style.background = t === tab ? '#F5C320' : 'transparent';
                btn.style.color      = t === tab ? '#1A1A1A' : '#888';
            }
        });

        // Render content
        const content = document.getElementById('rv-tab-content');
        if (content) content.innerHTML = renderTab(tab);

        // Start countdown if chat tab
        if (tab === 'chat' && activeSession) {
            startCountdown();
            scrollChatBottom();
        }
    }

    window._rvSwitchTab = switchTab;

    // ── Actions ───────────────────────────────────────────────────────────────

    window._rvToggleOnline = async function() {
        const data = await post('/reviewers/toggle_online', {});
        if (reviewerData) reviewerData.is_online = data.is_online;
        const label  = document.getElementById('rv-online-label');
        const toggle = document.getElementById('rv-online-toggle');
        if (label)  label.textContent = data.is_online ? 'أونلاين' : 'أوفلاين';
        if (toggle) {
            toggle.style.background = data.is_online ? '#1A1A1A' : '#ccc';
            toggle.querySelector('div').style.left = data.is_online ? '19px' : '3px';
        }
    };

    window._rvAcceptRequest = async function(requestId) {
        const data = await post('/reviewers/accept', {request_id: requestId, action: 'accept'});
        if (data.success) {
            // Refresh dashboard
            const dashRoot = document.getElementById('reviewer-portal-root');
            if (dashRoot) {
                await loadDashboard(dashRoot);
                switchTab('chat');
            }
        }
    };

    window._rvDeclineRequest = async function(requestId) {
        await post('/reviewers/accept', {request_id: requestId, action: 'decline'});
        pendingRequests = pendingRequests.filter(r => r.id !== requestId);
        const content = document.getElementById('rv-tab-content');
        if (content) content.innerHTML = renderTab(currentTab);
    };

    window._rvPortalSend = async function() {
        const input = document.getElementById('rv-portal-input');
        const text  = (input ? input.value : '').trim();
        if (!text || !activeSession) return;
        input.value = '';

        // Show immediately
        const msgs = document.getElementById('rv-chat-messages');
        if (msgs) {
            const div = document.createElement('div');
            div.style.cssText = 'max-width:85%;padding:9px 12px;font-size:13px;line-height:1.5;border-radius:10px 0 10px 10px;background:#F5C320;color:#1A1A1A;align-self:flex-end;font-weight:500;margin-left:auto';
            div.textContent = text;
            msgs.appendChild(div);
            msgs.scrollTop = msgs.scrollHeight;
        }

        await post('/reviewers/message', {
            token:  activeSession.token,
            text,
            sender: 'reviewer',
        });
    };

    window._rvSubmitVerdict = async function(verdict) {
        if (!activeSession) return;
        const notes = '';
        const data  = await post('/reviewers/verdict', {
            token:   activeSession.token,
            verdict,
            notes,
        });
        if (data.success) {
            activeSession = null;
            stopChatPoll();
            stopCountdown();
            alert(verdict === 'recommend' ? 'تم إرسال رأيك — أنصح بالشراء ✓' :
                  verdict === 'not_recommend' ? 'تم إرسال رأيك — لا أنصح' :
                  'تم إرسال رأيك — محايد');
            switchTab('dashboard');
            const root = document.getElementById('reviewer-portal-root');
            if (root) await loadDashboard(root);
        }
    };

    window._rvRequestPayout = function() {
        alert('سيتم التواصل معك لاستكمال عملية الصرف. الحد الأدنى للصرف: 5 KD');
    };

    window._rvToggleSetting = function(key) {
        if (reviewerData) reviewerData[key] = !reviewerData[key];
        const content = document.getElementById('rv-tab-content');
        if (content) content.innerHTML = renderTab('settings');
    };

    window._rvSaveBio = function() {
        const bio = document.getElementById('rv-bio-input');
        if (bio && reviewerData) reviewerData.bio = bio.value;
        alert('تم حفظ النبذة ✓');
    };

    // ── Polling ───────────────────────────────────────────────────────────────

    function startRequestPoll() {
        setInterval(async () => {
            const data = await post('/reviewers/dashboard', {});
            if (!data.is_reviewer) return;
            pendingRequests = data.pending_requests || [];
            if (currentTab === 'dashboard' || currentTab === 'requests') {
                const content = document.getElementById('rv-tab-content');
                if (content) content.innerHTML = renderTab(currentTab);
            }
            // Show notification badge on requests tab
            const reqTab = document.getElementById('rv-tab-requests');
            if (reqTab && pendingRequests.length) {
                reqTab.style.position = 'relative';
            }
        }, 8000);
    }

    function startChatPoll() {
        chatPollTimer = setInterval(async () => {
            if (!activeSession) { stopChatPoll(); return; }
            const data = await post(`/reviewers/request/${activeSession.token}`, {});
            if (!data.request) return;
            activeSession = data.request;
            if (currentTab === 'chat') {
                const msgs = document.getElementById('rv-chat-messages');
                if (msgs && activeSession.messages) {
                    const wasAtBottom = msgs.scrollHeight - msgs.scrollTop <= msgs.clientHeight + 50;
                    msgs.innerHTML = activeSession.messages.map(m => `
                    <div style="max-width:85%;padding:9px 12px;font-size:13px;line-height:1.5;
                         border-radius:${m.sender==='reviewer' ? '10px 0 10px 10px' : '0 10px 10px 10px'};
                         background:${m.sender==='reviewer' ? '#F5C320' : '#F5F4F2'};
                         color:#1A1A1A;
                         align-self:${m.sender==='reviewer' ? 'flex-end' : 'flex-start'};
                         font-weight:${m.sender==='reviewer' ? '500' : '400'};
                         ${m.sender==='reviewer' ? 'margin-left:auto' : ''}">
                        ${m.text}
                    </div>`).join('');
                    if (wasAtBottom) msgs.scrollTop = msgs.scrollHeight;
                }
            }
        }, 3000);
    }

    function stopChatPoll() {
        if (chatPollTimer) { clearInterval(chatPollTimer); chatPollTimer = null; }
    }

    // ── Countdown Timer ───────────────────────────────────────────────────────

    let countdownSeconds = 15 * 60;

    function startCountdown() {
        stopCountdown();
        countdownSeconds = 15 * 60;
        countdownTimer = setInterval(() => {
            countdownSeconds--;
            const m   = String(Math.floor(countdownSeconds / 60)).padStart(2, '0');
            const s   = String(countdownSeconds % 60).padStart(2, '0');
            const el  = document.getElementById('rv-countdown');
            if (el)   el.textContent = `${m}:${s}`;
            if (countdownSeconds <= 0) stopCountdown();
        }, 1000);
    }

    function stopCountdown() {
        if (countdownTimer) { clearInterval(countdownTimer); countdownTimer = null; }
    }

    function scrollChatBottom() {
        setTimeout(() => {
            const msgs = document.getElementById('rv-chat-messages');
            if (msgs) msgs.scrollTop = msgs.scrollHeight;
        }, 100);
    }

    // ── Bind Events ───────────────────────────────────────────────────────────

    function bindPortalEvents() {
        // Already using onclick= in HTML
    }

    // ── Register Form ─────────────────────────────────────────────────────────

    function renderRegisterForm(root) {
        root.innerHTML = `
<div style="max-width:500px;margin:40px auto;padding:0 16px">
    <div style="background:#fff;border:0.5px solid rgba(0,0,0,.08);border-radius:14px;overflow:hidden">
        <div style="background:#F5C320;padding:16px 20px">
            <div style="font-size:16px;font-weight:700;color:#1A1A1A">🐝 سجّل كريفيور في Uellow</div>
            <div style="font-size:11px;color:#854F0B;margin-top:3px">شارك خبرتك واكسب عمولة</div>
        </div>
        <div style="padding:20px">
            <div style="margin-bottom:14px">
                <label style="font-size:12px;font-weight:600;color:#1A1A1A;display:block;margin-bottom:5px">الاسم المعروض *</label>
                <input id="rv-reg-name" type="text" placeholder="الاسم الذي سيظهر للعملاء"
                       style="width:100%;border:0.5px solid rgba(0,0,0,.12);border-radius:8px;padding:10px 12px;font-size:13px;font-family:inherit;outline:none;direction:rtl">
            </div>
            <div style="margin-bottom:14px">
                <label style="font-size:12px;font-weight:600;color:#1A1A1A;display:block;margin-bottom:5px">نبذة مختصرة</label>
                <textarea id="rv-reg-bio" rows="3" placeholder="عرّف بنفسك وخبرتك..."
                          style="width:100%;border:0.5px solid rgba(0,0,0,.12);border-radius:8px;padding:10px 12px;font-size:13px;font-family:inherit;outline:none;resize:none;direction:rtl"></textarea>
            </div>
            <div style="margin-bottom:20px">
                <label style="font-size:12px;font-weight:600;color:#1A1A1A;display:block;margin-bottom:5px">تخصصاتك</label>
                <input id="rv-reg-specialty" type="text" placeholder="مثال: موضة رجالي، إلكترونيات، رياضة"
                       style="width:100%;border:0.5px solid rgba(0,0,0,.12);border-radius:8px;padding:10px 12px;font-size:13px;font-family:inherit;outline:none;direction:rtl">
            </div>
            <div style="background:#FFF8E1;border-radius:8px;padding:10px 12px;margin-bottom:16px;font-size:11px;color:#854F0B;line-height:1.6">
                ✓ ستتلقى عمولة 5-8% على كل عملية شراء ناجحة<br>
                ✓ اشتغل من أي مكان وفي أي وقت<br>
                ✓ سيتم مراجعة طلبك خلال 24 ساعة
            </div>
            <button onclick="window._rvSubmitRegister()"
                    style="width:100%;background:#F5C320;border:none;border-radius:10px;padding:13px;font-size:14px;font-weight:700;cursor:pointer;font-family:inherit">
                إرسال الطلب
            </button>
        </div>
    </div>
</div>`;

        window._rvSubmitRegister = async function() {
            const name      = document.getElementById('rv-reg-name').value.trim();
            const bio       = document.getElementById('rv-reg-bio').value.trim();
            const specialty = document.getElementById('rv-reg-specialty').value.trim();

            if (!name) { alert('الاسم مطلوب'); return; }

            const data = await post('/reviewers/register', {
                display_name:  name,
                bio,
                specialty_ids: [],
            });

            if (data.success) {
                root.innerHTML = `
<div style="max-width:440px;margin:60px auto;padding:0 16px;text-align:center">
    <div style="font-size:48px;margin-bottom:16px">🎉</div>
    <h2 style="font-size:20px;font-weight:700;margin-bottom:8px">تم إرسال طلبك!</h2>
    <p style="color:#888;line-height:1.6;margin-bottom:20px">
        ${data.state === 'pending' ? 'سيتم مراجعة طلبك خلال 24 ساعة وسنتواصل معك.' : 'تم قبولك كريفيور! يمكنك البدء الآن.'}
    </p>
    <a href="/reviewer/dashboard" style="background:#F5C320;color:#1A1A1A;padding:11px 24px;border-radius:8px;text-decoration:none;font-weight:700;font-size:13px">
        الذهاب للـ Dashboard
    </a>
</div>`;
            } else {
                alert(data.error || 'حدث خطأ');
            }
        };
    }

    // ── Boot ──────────────────────────────────────────────────────────────────

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
