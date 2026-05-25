(function () {
    'use strict';
    var ERROR_MESSAGES = {
        'not_configured': 'خدمة تسجيل الدخول بـ Apple غير مُفعَّلة.',
        'no_token': 'لم يتم استلام رمز التحقق من Apple.',
        'token_invalid': 'فشل التحقق من هوية Apple.',
        'no_sub': 'لم يتم استلام معرف المستخدم.',
        'create_failed': 'فشل إنشاء الحساب.',
        'signup_disabled': 'التسجيل مغلق حالياً.',
        'user_cancelled_authorize': 'تم إلغاء تسجيل الدخول.',
    };
    document.addEventListener('DOMContentLoaded', function () {
        // Show error if present in URL
        var params = new URLSearchParams(window.location.search);
        var appleError = params.get('apple_error');
        if (appleError) {
            var msg = ERROR_MESSAGES[appleError] || ('خطأ: ' + appleError);
            var form = document.querySelector('form[action="/web/login"], .oe_login_form');
            if (form) {
                var alert = document.createElement('div');
                alert.className = 'alert alert-danger';
                alert.innerHTML = '<strong>Apple Login:</strong> ' + msg;
                form.insertBefore(alert, form.firstChild);
            }
            window.history.replaceState({}, document.title, window.location.pathname);
        }
        // Check if Apple login is enabled via JSON-RPC
        fetch('/apple/login/status', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({jsonrpc: '2.0', method: 'call', id: 1, params: {}})
        })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data && data.result && data.result.enabled) {
                var container = document.getElementById('apple_login_container');
                if (container) container.style.display = 'block';
            }
        })
        .catch(function(e) { console.warn('Apple login check failed:', e); });
    });
})();
