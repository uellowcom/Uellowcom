(function () {
    'use strict';

    var TR = {
        ar: {
            title: 'آراء متخصصين موثّقين', free: 'مجاناً',
            recN: function (n) { return n + ' ينصح'; },
            neuN: function (n) { return n + ' محايد'; },
            notN: function (n) { return n + ' لا ينصح'; },
            consultsN: function (n) { return '· ' + n + ' استشارة'; },
            availN: function (n) { return n + ' متخصصين متاحون'; },
            availTail: 'الآن للاستشارة',
            method: 'طريقة الاستشارة:', written: 'مكتوب', chat: 'شات',
            askCta: 'اطلب استشارة مجانية', bnLabel: 'جرّب الآن',
            bnName: 'اسأل Beena', bnSub: 'رد فوري ذكي',
            g1: 'مستقلة', g2: 'مجانية',
            gReply: function (m) { return 'رد ~' + m + 'د'; },
            verdict: { recommend: 'ينصح بالشراء', neutral: 'محايد', not_recommend: 'لا ينصح' },
            noOnline: 'لا يوجد متخصص متاح الآن — اطلب رأياً مكتوباً ويردّون قريباً',
            dlgTitle: 'اطلب رأي متخصص — مجاناً',
            dlgSub: 'متخصصون حقيقيون يساعدونك قبل الشراء',
            colRequest: 'اطلب استشارة', colLog: 'سجل الآراء',
            onlineNow: 'المتاحون الآن', viewAll: 'مشاهدة الكل',
            startConsult: 'ابدأ الاستشارة المجانية',
            freeNote: 'مجانية — المتخصص يأخذ عمولته من يلو',
            beenaCta: 'اسأل Beena AI فوراً', beenaCtaSub: 'إجابة ذكية بدون انتظار متخصص',
            recommendSummary: function (r, t) { return r + ' من ' + t + ' متخصصين ينصحون بشراء هذا المنتج'; },
            moreExperts: function (n) { return '+ ' + n + ' متخصصين آخرين'; },
            close: 'إغلاق', level: { starter: 'مبتدئ', regular: 'منتظم', expert: 'متخصص', elite: 'نخبة' },
            sending: 'جارٍ الإرسال...', requestSent: 'تم إرسال طلبك — سيتواصل المتخصص قريباً',
            pickOne: 'اختر متخصصاً أولاً',
        },
        en: {
            title: 'Verified expert reviews', free: 'Free',
            recN: function (n) { return n + ' yes'; },
            neuN: function (n) { return n + ' neutral'; },
            notN: function (n) { return n + ' no'; },
            consultsN: function (n) { return '· ' + n + ' consults'; },
            availN: function (n) { return n + ' experts available'; },
            availTail: 'now for a consult',
            method: 'Consult type:', written: 'Written', chat: 'Chat',
            askCta: 'Request a free consult', bnLabel: 'Try now',
            bnName: 'Ask Beena', bnSub: 'Instant smart reply',
            g1: 'Independent', g2: 'Free',
            gReply: function (m) { return '~' + m + ' min reply'; },
            verdict: { recommend: 'Recommends', neutral: 'Neutral', not_recommend: 'Not recommended' },
            noOnline: 'No expert online now — request a written opinion and they will reply soon',
            dlgTitle: 'Ask an expert — free',
            dlgSub: 'Real specialists help you before you buy',
            colRequest: 'Request a consult', colLog: 'Opinion log',
            onlineNow: 'Online now', viewAll: 'View all',
            startConsult: 'Start free consult',
            freeNote: 'Free — the expert is paid by Uellow',
            beenaCta: 'Ask Beena AI now', beenaCtaSub: 'Smart answer, no waiting',
            recommendSummary: function (r, t) { return r + ' of ' + t + ' experts recommend this product'; },
            moreExperts: function (n) { return '+ ' + n + ' more experts'; },
            close: 'Close', level: { starter: 'Starter', regular: 'Regular', expert: 'Expert', elite: 'Elite' },
            sending: 'Sending...', requestSent: 'Request sent — the expert will reach out soon',
            pickOne: 'Pick an expert first',
        }
    };

    function post(url, params) {
        return fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ jsonrpc: '2.0', method: 'call', id: 1, params: params || {} }),
        }).then(function (r) { return r.json(); }).then(function (d) { return d.result || {}; });
    }
    function esc(s) {
        return String(s == null ? '' : s)
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }
    function timeAgo(iso, lang) {
        if (!iso) return '';
        var then = new Date(iso).getTime();
        if (isNaN(then)) return '';
        var mins = Math.max(1, Math.round((Date.now() - then) / 60000));
        if (lang === 'en') {
            if (mins < 60) return mins + ' min ago';
            var h = Math.round(mins / 60);
            if (h < 24) return h + 'h ago';
            return Math.round(h / 24) + 'd ago';
        }
        if (mins < 60) return 'قبل ' + mins + ' دقيقة';
        var hh = Math.round(mins / 60);
        if (hh < 24) return 'قبل ' + hh + ' ساعة';
        return 'قبل ' + Math.round(hh / 24) + ' يوم';
    }
    function avatarHtml(item, size, fontSize) {
        var s = size || 32, fs = fontSize || 11;
        var initial = esc((item.name || '?').charAt(0));
        var bg = ['#FAEEDA', '#EEEDFE', '#E6F1FB', '#FAECE7', '#E1F5EE'][(item.id || 0) % 5];
        var fg = ['#854F0B', '#534AB7', '#185FA5', '#993C1D', '#0F6E56'][(item.id || 0) % 5];
        var img = item.avatar_url
            ? '<img src="' + esc(item.avatar_url) + '" style="width:100%;height:100%;border-radius:50%;object-fit:cover" ' +
              'onerror="this.style.display=\'none\';this.nextSibling.style.display=\'flex\'"/>' +
              '<span style="display:none;width:100%;height:100%;border-radius:50%;align-items:center;justify-content:center;font-size:' + fs + 'px;font-weight:500;color:' + fg + ';background:' + bg + '">' + initial + '</span>'
            : '<span style="display:flex;width:100%;height:100%;border-radius:50%;align-items:center;justify-content:center;font-size:' + fs + 'px;font-weight:500;color:' + fg + ';background:' + bg + '">' + initial + '</span>';
        return '<div style="position:relative;width:' + s + 'px;height:' + s + 'px;border-radius:50%;overflow:hidden;background:' + bg + '">' + img + '</div>';
    }
    function verdictBadge(v, t) {
        var cls = v === 'recommend' ? 'uellow-rv-vb-rec' : v === 'not_recommend' ? 'uellow-rv-vb-not' : 'uellow-rv-vb-neu';
        return '<span class="' + cls + '" style="font-size:9px;padding:1px 7px;border-radius:4px;font-weight:500">' + esc(t.verdict[v] || '') + '</span>';
    }

    function renderCard(mount, data, lang) {
        var t = TR[lang];
        var s = data.stats || {};
        var online = data.online || [];
        var lo = data.last_opinion;

        var stackMax = 4;
        var shown = online.slice(0, stackMax);
        var rest = Math.max(0, (data.online_count || 0) - shown.length);
        var avatarsHtml = '<div class="uellow-rv-avatars" style="display:flex;flex-shrink:0">';
        shown.forEach(function (o, i) {
            var mr = i === 0 ? '' : 'margin-' + (lang === 'en' ? 'left' : 'right') + ':-10px;';
            var dot = i === 0 ? '<span style="position:absolute;bottom:-1px;' + (lang === 'en' ? 'right' : 'left') + ':-1px;width:9px;height:9px;border-radius:50%;background:#1D9E75;border:1.5px solid #fff"></span>' : '';
            avatarsHtml += '<div class="uellow-rv-av" style="position:relative;border:2px solid #fff;border-radius:50%;' + mr + '">' + avatarHtml(o, 32, 11) + dot + '</div>';
        });
        if (rest > 0) {
            avatarsHtml += '<div style="width:32px;height:32px;border-radius:50%;background:#F1EFE8;border:2px solid #fff;display:flex;align-items:center;justify-content:center;font-size:9px;font-weight:500;color:#5F5E5A;margin-' + (lang === 'en' ? 'left' : 'right') + ':-10px">+' + rest + '</div>';
        }
        avatarsHtml += '</div>';

        var hasOnline = (data.online_count || 0) > 0;
        var availLine = hasOnline
            ? '<span style="color:#0F6E56;font-weight:500">' + esc(t.availN(data.online_count)) + '</span> ' + esc(t.availTail)
            : '<span style="color:#A32D2D;font-weight:500">' + esc(t.noOnline) + '</span>';

        var quoteLine = lo
            ? '«' + esc((lo.notes || '').slice(0, 60)) + '» — ' + esc(lo.reviewer_name) + '، ' + timeAgo(lo.when_ts, lang)
            : '';

        var avgM = s.avg_minutes || 5;

        mount.innerHTML =
        '<div class="uellow-rv-card" dir="' + (lang === 'en' ? 'ltr' : 'rtl') + '">' +
          '<div style="padding:11px 14px 9px;display:flex;align-items:center;gap:12px">' +
            '<div style="position:relative;width:46px;height:46px;flex-shrink:0">' +
              '<svg viewBox="0 0 36 36" style="width:46px;height:46px;transform:rotate(-90deg)">' +
                '<circle cx="18" cy="18" r="15.9" fill="none" stroke="#F1EFE8" stroke-width="3.6"></circle>' +
                '<circle cx="18" cy="18" r="15.9" fill="none" stroke="#1D9E75" stroke-width="3.6" stroke-dasharray="' + (s.recommend_pct || 0) + ' 100" stroke-linecap="round"></circle>' +
              '</svg>' +
              '<div style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:500;color:#0F6E56">' + (s.recommend_pct || 0) + '%</div>' +
            '</div>' +
            '<div style="flex:1;min-width:0">' +
              '<div style="display:flex;align-items:center;gap:6px">' +
                '<span style="font-size:13px;font-weight:500;color:#1A1A1A">' + esc(t.title) + '</span>' +
                '<i class="ti ti-rosette-discount-check" style="font-size:14px;color:#F5C320" aria-hidden="true"></i>' +
              '</div>' +
              '<div style="display:flex;gap:10px;margin-top:3px">' +
                '<span style="font-size:10px;color:#0F6E56;display:flex;align-items:center;gap:2px"><i class="ti ti-thumb-up" style="font-size:11px" aria-hidden="true"></i> ' + esc(t.recN(s.recommend || 0)) + '</span>' +
                '<span style="font-size:10px;color:#5F5E5A;display:flex;align-items:center;gap:2px"><i class="ti ti-minus" style="font-size:11px" aria-hidden="true"></i> ' + esc(t.neuN(s.neutral || 0)) + '</span>' +
                '<span style="font-size:10px;color:#aaa">' + esc(t.consultsN(s.total_consults || 0)) + '</span>' +
              '</div>' +
            '</div>' +
            '<span style="font-size:10px;font-weight:500;color:#412402;background:#F5C320;padding:3px 9px;border-radius:20px;flex-shrink:0">' + esc(t.free) + '</span>' +
          '</div>' +
          '<div style="margin:0 14px 12px;padding-top:9px;border-top:0.5px solid rgba(0,0,0,.08);display:flex;align-items:center;gap:10px">' +
            avatarsHtml +
            '<div style="flex:1;min-width:0">' +
              '<div style="font-size:11px;color:#666">' + availLine + '</div>' +
              (quoteLine ? '<div style="font-size:10px;color:#aaa;line-height:1.4;margin-top:1px;overflow:hidden;text-overflow:ellipsis;display:-webkit-box;-webkit-line-clamp:1;-webkit-box-orient:vertical">' + quoteLine + '</div>' : '') +
            '</div>' +
          '</div>' +
          '<div style="padding:0 14px 14px;display:flex;align-items:flex-end;gap:9px">' +
            '<div style="flex:1;display:flex;flex-direction:column;gap:6px">' +
              '<div style="display:flex;gap:6px;align-items:center">' +
                '<span style="font-size:10px;color:#aaa">' + esc(t.method) + '</span>' +
                '<div class="uellow-rv-seg" data-type="written" style="display:flex;align-items:center;gap:4px;background:#FAEEDA;border:0.5px solid #F5C320;border-radius:7px;padding:3px 9px;cursor:pointer">' +
                  '<i class="ti ti-writing" style="font-size:13px;color:#854F0B" aria-hidden="true"></i>' +
                  '<span style="font-size:11px;color:#854F0B;font-weight:500">' + esc(t.written) + '</span>' +
                '</div>' +
                '<div class="uellow-rv-seg" data-type="chat" style="display:flex;align-items:center;gap:4px;background:transparent;border:0.5px solid rgba(0,0,0,.12);border-radius:7px;padding:3px 9px;cursor:pointer">' +
                  '<i class="ti ti-messages" style="font-size:13px;color:#888" aria-hidden="true"></i>' +
                  '<span style="font-size:11px;color:#888">' + esc(t.chat) + '</span>' +
                '</div>' +
              '</div>' +
              '<button type="button" class="uellow-rv-open" style="width:100%;background:#1A1A1A;border:none;border-radius:11px;padding:13px;font-size:14px;font-weight:500;color:#fff;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:7px">' +
                '<i class="ti ti-messages" style="font-size:17px" aria-hidden="true"></i> ' + esc(t.askCta) +
              '</button>' +
            '</div>' +
            '<div style="position:relative;width:108px;flex-shrink:0;padding-top:9px">' +
              (data.settings && data.settings.beena_enabled ?
                '<span class="uellow-rv-bn-label">' + esc(t.bnLabel) + '</span>' +
                '<button type="button" class="uellow-rv-bn-btn uellow-rv-beena">' +
                  '<i class="ti ti-sparkles uellow-rv-bn-star" style="font-size:18px;color:#412402" aria-hidden="true"></i>' +
                  '<span class="uellow-rv-bn-name">' + esc(t.bnName) + '</span>' +
                  '<span style="font-size:8px;color:#633806;position:relative;z-index:1">' + esc(t.bnSub) + '</span>' +
                  '<span class="uellow-rv-bn-shine"></span>' +
                '</button>'
              : '') +
            '</div>' +
          '</div>' +
          '<div style="display:flex;align-items:center;justify-content:center;gap:13px;padding:0 14px 13px">' +
            '<span style="font-size:10px;color:#aaa;display:flex;align-items:center;gap:3px"><i class="ti ti-lock" style="font-size:11px" aria-hidden="true"></i> ' + esc(t.g1) + '</span>' +
            '<span style="font-size:10px;color:#aaa;display:flex;align-items:center;gap:3px"><i class="ti ti-gift" style="font-size:11px" aria-hidden="true"></i> ' + esc(t.g2) + '</span>' +
            '<span style="font-size:10px;color:#aaa;display:flex;align-items:center;gap:3px"><i class="ti ti-bolt" style="font-size:11px" aria-hidden="true"></i> ' + esc(t.gReply(avgM)) + '</span>' +
          '</div>' +
        '</div>';

        bindCard(mount, data, lang);
    }

    var selectedType = 'written';

    function bindCard(mount, data, lang) {
        var segs = mount.querySelectorAll('.uellow-rv-seg');
        segs.forEach(function (seg) {
            seg.addEventListener('click', function (e) {
                e.preventDefault(); e.stopPropagation();
                selectedType = seg.getAttribute('data-type');
                segs.forEach(function (s2) {
                    var on = s2 === seg;
                    s2.style.background = on ? '#FAEEDA' : 'transparent';
                    s2.style.borderColor = on ? '#F5C320' : 'rgba(0,0,0,.12)';
                    var ic = s2.querySelector('i'), tx = s2.querySelector('span');
                    if (ic) ic.style.color = on ? '#854F0B' : '#888';
                    if (tx) { tx.style.color = on ? '#854F0B' : '#888'; tx.style.fontWeight = on ? '500' : '400'; }
                });
            });
        });
        var openBtn = mount.querySelector('.uellow-rv-open');
        if (openBtn) openBtn.addEventListener('click', function (e) { e.preventDefault(); e.stopPropagation(); openDialog(data, lang); });
        var beena = mount.querySelector('.uellow-rv-beena');
        if (beena) beena.addEventListener('click', function (e) { e.preventDefault(); e.stopPropagation(); launchBeena(data); });
    }

    function launchBeena(data) {
        var pid = data.product_id;
        // Preferred: drive the real Beena instance directly so it shows the
        // product context card and scopes the conversation to this product.
        if (window._beenaApp && typeof window._beenaApp.open === 'function') {
            try { window._beenaApp.open(pid); return; } catch (e) {}
        }
        // Fallback: open via FAB, then push product context once it's ready.
        var btn = document.querySelector('#beena-float-btn') || document.querySelector('#beena-float');
        if (btn) {
            btn.click();
            var tries = 0;
            var timer = setInterval(function () {
                tries++;
                if (window._beenaApp && typeof window._beenaApp.open === 'function') {
                    try { window._beenaApp.open(pid); } catch (e) {}
                    clearInterval(timer);
                } else if (tries > 20) {
                    clearInterval(timer);
                }
            }, 100);
            return;
        }
        window.dispatchEvent(new CustomEvent('beena:open', { detail: { product_id: pid } }));
    }

    function openDialog(data, lang) {
        var t = TR[lang];
        var s = data.stats || {};
        var online = data.online || [];

        var overlay = document.createElement('div');
        overlay.className = 'uellow-rv-overlay';
        overlay.setAttribute('dir', lang === 'en' ? 'ltr' : 'rtl');

        var showN = 3;
        function onlineRows(expanded) {
            var list = expanded ? online : online.slice(0, showN);
            var html = list.map(function (o, i) {
                var sel = i === 0 ? 'border:0.5px solid #F5C320;background:#FAEEDA' : 'border:0.5px solid rgba(0,0,0,.1);background:transparent';
                return '<div class="uellow-rv-onrow" data-id="' + o.id + '" style="display:flex;align-items:center;gap:9px;padding:8px 9px;' + sel + ';border-radius:8px;margin-bottom:6px;cursor:pointer">' +
                    '<div style="position:relative;flex-shrink:0">' + avatarHtml(o, 32, 12) +
                      '<span style="position:absolute;bottom:0;' + (lang === 'en' ? 'right' : 'left') + ':0;width:8px;height:8px;border-radius:50%;background:#1D9E75;border:1.5px solid #fff"></span>' +
                    '</div>' +
                    '<div style="flex:1;min-width:0">' +
                      '<div style="font-size:12px;font-weight:500;color:#1A1A1A">' + esc(o.name) + '</div>' +
                      '<div style="font-size:10px;color:#aaa">' + esc(t.level[o.level] || '') + '</div>' +
                    '</div>' +
                    '<i class="ti ti-circle-check" style="font-size:17px;color:#F5C320;' + (i === 0 ? '' : 'display:none') + '" aria-hidden="true"></i>' +
                '</div>';
            }).join('');
            var more = (!expanded && online.length > showN)
                ? '<button class="uellow-rv-more" style="width:100%;border:none;background:transparent;color:#185FA5;font-size:11px;cursor:pointer;padding:4px;margin-bottom:8px">' + esc(t.moreExperts(online.length - showN)) + '</button>'
                : '';
            return html + more;
        }

        var logHtml = '';
        if (data.last_opinion) {
            var lo = data.last_opinion;
            logHtml = '<div style="display:flex;gap:9px;padding:9px 0;border-bottom:0.5px solid rgba(0,0,0,.08)">' +
                '<div style="flex-shrink:0">' + avatarHtml({ id: 1, name: lo.reviewer_name, avatar_url: lo.avatar_url }, 28, 11) + '</div>' +
                '<div style="flex:1;min-width:0">' +
                  '<div style="display:flex;align-items:center;gap:5px"><span style="font-size:11px;font-weight:500;color:#1A1A1A">' + esc(lo.reviewer_name) + '</span>' + verdictBadge(lo.verdict, t) + '</div>' +
                  '<div style="font-size:11px;color:#666;margin-top:2px;line-height:1.5">' + esc(lo.notes) + '</div>' +
                '</div>' +
            '</div>';
        } else {
            logHtml = '<div style="text-align:center;color:#aaa;font-size:12px;padding:24px 0">—</div>';
        }

        overlay.innerHTML =
        '<div class="uellow-rv-dialog">' +
          '<div style="background:#F5C320;padding:15px 18px;display:flex;align-items:center;gap:11px">' +
            '<div style="width:38px;height:38px;border-radius:50%;background:#412402;display:flex;align-items:center;justify-content:center;flex-shrink:0">' +
              '<i class="ti ti-users" style="font-size:20px;color:#F5C320" aria-hidden="true"></i></div>' +
            '<div style="flex:1"><div style="font-size:17px;font-weight:500;color:#412402">' + esc(t.dlgTitle) + '</div>' +
              '<div style="font-size:12px;color:#633806;margin-top:1px">' + esc(t.dlgSub) + '</div></div>' +
            '<button class="uellow-rv-close" aria-label="' + esc(t.close) + '" style="border:none;background:rgba(65,36,2,.12);width:30px;height:30px;border-radius:50%;cursor:pointer;display:flex;align-items:center;justify-content:center">' +
              '<i class="ti ti-x" style="font-size:17px;color:#412402" aria-hidden="true"></i></button>' +
          '</div>' +
          '<div style="background:#FAEEDA;padding:10px 18px;display:flex;align-items:center;gap:12px;border-bottom:0.5px solid #FAC775">' +
            '<div style="position:relative;width:42px;height:42px;flex-shrink:0">' +
              '<svg viewBox="0 0 36 36" style="width:42px;height:42px;transform:rotate(-90deg)">' +
                '<circle cx="18" cy="18" r="15.9" fill="none" stroke="#F5DFB0" stroke-width="3.6"></circle>' +
                '<circle cx="18" cy="18" r="15.9" fill="none" stroke="#0F6E56" stroke-width="3.6" stroke-dasharray="' + (s.recommend_pct || 0) + ' 100" stroke-linecap="round"></circle></svg>' +
              '<div style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:500;color:#0F6E56">' + (s.recommend_pct || 0) + '%</div></div>' +
            '<div style="font-size:12px;color:#633806;line-height:1.5">' + esc(t.recommendSummary(s.recommend || 0, s.total_verdicts || 0)) + '</div>' +
          '</div>' +
          '<div class="uellow-rv-dialog-cols" style="display:grid;grid-template-columns:1fr 1fr">' +
            '<div style="padding:16px 18px;border-' + (lang === 'en' ? 'right' : 'left') + ':0.5px solid rgba(0,0,0,.08)">' +
              '<div style="font-size:13px;font-weight:500;color:#666;margin-bottom:11px;display:flex;align-items:center;gap:6px"><i class="ti ti-message-circle" style="font-size:16px;color:#BA7517" aria-hidden="true"></i> ' + esc(t.colRequest) + '</div>' +
              '<div style="font-size:11px;color:#aaa;margin-bottom:9px">' + esc(t.onlineNow) + ' · ' + (data.online_count || 0) + '</div>' +
              '<div class="uellow-rv-online-wrap">' + onlineRows(false) + '</div>' +
              '<button class="uellow-rv-submit" style="width:100%;background:#F5C320;border:none;border-radius:8px;padding:11px;font-size:13px;font-weight:500;color:#412402;cursor:pointer;margin-top:6px">' + esc(t.startConsult) + '</button>' +
              '<div style="font-size:10px;color:#0F6E56;text-align:center;margin-top:7px;display:flex;align-items:center;justify-content:center;gap:4px"><i class="ti ti-gift" style="font-size:13px" aria-hidden="true"></i> ' + esc(t.freeNote) + '</div>' +
            '</div>' +
            '<div style="padding:16px 18px;max-height:300px;overflow-y:auto">' +
              '<div style="font-size:13px;font-weight:500;color:#666;margin-bottom:11px;display:flex;align-items:center;gap:6px"><i class="ti ti-history" style="font-size:16px;color:#BA7517" aria-hidden="true"></i> ' + esc(t.colLog) + ' (' + (s.total_verdicts || 0) + ')</div>' +
              logHtml +
            '</div>' +
          '</div>' +
          (data.settings && data.settings.beena_enabled ?
          '<div style="padding:11px 18px;border-top:0.5px solid rgba(0,0,0,.08)">' +
            '<div class="uellow-rv-beena-dlg" style="display:flex;align-items:center;gap:9px;background:#FAEEDA;border:0.5px solid #FAC775;border-radius:8px;padding:9px 12px;cursor:pointer">' +
              '<div style="width:28px;height:28px;border-radius:50%;background:#F5C320;display:flex;align-items:center;justify-content:center;flex-shrink:0"><i class="ti ti-sparkles" style="font-size:15px;color:#412402" aria-hidden="true"></i></div>' +
              '<div style="flex:1"><div style="font-size:12px;font-weight:500;color:#412402">' + esc(t.beenaCta) + '</div>' +
                '<div style="font-size:10px;color:#854F0B">' + esc(t.beenaCtaSub) + '</div></div>' +
              '<i class="ti ti-arrow-' + (lang === 'en' ? 'right' : 'left') + '" style="font-size:16px;color:#854F0B" aria-hidden="true"></i>' +
            '</div>' +
          '</div>' : '') +
        '</div>';

        document.body.appendChild(overlay);
        requestAnimationFrame(function () { overlay.classList.add('is-open'); });

        var selectedReviewer = online.length ? online[0].id : null;

        function bindOnline() {
            overlay.querySelectorAll('.uellow-rv-onrow').forEach(function (row) {
                row.addEventListener('click', function () {
                    selectedReviewer = parseInt(row.getAttribute('data-id'), 10);
                    overlay.querySelectorAll('.uellow-rv-onrow').forEach(function (r2) {
                        var on = r2 === row;
                        r2.style.border = on ? '0.5px solid #F5C320' : '0.5px solid rgba(0,0,0,.1)';
                        r2.style.background = on ? '#FAEEDA' : 'transparent';
                        var chk = r2.querySelector('.ti-circle-check');
                        if (chk) chk.style.display = on ? 'block' : 'none';
                    });
                });
            });
            var moreBtn = overlay.querySelector('.uellow-rv-more');
            if (moreBtn) moreBtn.addEventListener('click', function () {
                overlay.querySelector('.uellow-rv-online-wrap').innerHTML = onlineRows(true);
                bindOnline();
            });
        }
        bindOnline();

        function close() {
            overlay.classList.remove('is-open');
            setTimeout(function () { overlay.remove(); }, 200);
        }
        overlay.querySelector('.uellow-rv-close').addEventListener('click', close);
        overlay.addEventListener('click', function (e) { if (e.target === overlay) close(); });

        var beenaDlg = overlay.querySelector('.uellow-rv-beena-dlg');
        if (beenaDlg) beenaDlg.addEventListener('click', function () { close(); launchBeena(data); });

        var submit = overlay.querySelector('.uellow-rv-submit');
        if (submit) submit.addEventListener('click', function () {
            if (!selectedReviewer) { submit.textContent = t.pickOne; return; }
            submit.disabled = true; submit.textContent = t.sending;
            post('/reviewers/request', {
                reviewer_id: selectedReviewer,
                product_id: data.product_id,
                session_type: selectedType,
            }).then(function (res) {
                if (res && res.success) {
                    submit.textContent = '✓ ' + t.requestSent;
                    submit.style.background = '#E1F5EE';
                    submit.style.color = '#0F6E56';
                } else {
                    submit.disabled = false;
                    submit.textContent = (res && res.error) ? res.error : t.startConsult;
                }
            }).catch(function () {
                submit.disabled = false; submit.textContent = t.startConsult;
            });
        });
    }

    function hydrate(mount) {
        if (mount.dataset.bound === '1') return;
        mount.dataset.bound = '1';

        var productId = mount.getAttribute('data-product-id');
        var rawLang = (mount.getAttribute('data-lang') || 'ar').toLowerCase();
        var lang = rawLang.indexOf('en') === 0 ? 'en' : 'ar';
        if (!productId) return;

        mount.innerHTML = '<div class="uellow-rv-skeleton"></div>';

        post('/reviewers/product_summary', { product_id: productId }).then(function (data) {
            if (!data || data.enabled === false || data.error) {
                mount.innerHTML = '';
                return;
            }
            data.product_id = parseInt(productId, 10);
            renderCard(mount, data, lang);
        }).catch(function () { mount.innerHTML = ''; });
    }

    function init() {
        var mounts = document.querySelectorAll('#uellow-reviewer-card, .uellow-rv-card-mount');
        var seen = false;
        mounts.forEach(function (m) {
            if (seen) { m.remove(); return; }
            seen = true;
            hydrate(m);
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
