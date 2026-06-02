import json
import logging
import threading
from urllib import request as urlreq, error as urlerr

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


def _post_json(url, payload, headers=None, timeout=8):
    try:
        body = json.dumps(payload).encode()
        h = {'Content-Type': 'application/json'}
        h.update(headers or {})
        req = urlreq.Request(url, data=body, method='POST', headers=h)
        with urlreq.urlopen(req, timeout=timeout) as resp:
            return resp.getcode() < 300
    except (urlerr.URLError, urlerr.HTTPError, OSError) as e:
        _logger.warning('[perf-alert webhook] %s → %s', url[:60], e)
        return False


def _async_post(fn):
    threading.Thread(target=fn, daemon=True).start()


class PerfAlert(models.Model):
    _name = 'uellow.perf.alert'
    _description = 'Uellow Performance — alert event'
    _order = 'create_date desc'

    name = fields.Char(required=True)
    category = fields.Selection([
        ('synthetic', 'Synthetic check'),
        ('rum', 'Real-User vitals'),
        ('bot', 'Bot quota'),
        ('slowq', 'Slow query'),
        ('cache', 'Cache health'),
        ('system', 'System resource'),
        ('image', 'Image weight'),
        ('anomaly', 'Anomaly'),
    ], required=True, index=True)
    severity = fields.Selection([
        ('info', 'Info'), ('warning', 'Warning'), ('critical', 'Critical'),
    ], required=True, index=True)
    resolved = fields.Boolean(default=False, index=True)
    delivered = fields.Boolean(default=False, readonly=True)

    @api.model
    def fire(self, category, severity, message):
        recent = self.search([
            ('category', '=', category),
            ('severity', '=', severity),
            ('name', '=', message),
            ('create_date', '>=', fields.Datetime.subtract(
                fields.Datetime.now(), minutes=10)),
        ], limit=1)
        if recent:
            return recent
        rec = self.create({
            'name': message, 'category': category, 'severity': severity,
        })
        _logger.warning('[perf-alert] %s/%s: %s', category, severity, message)
        try:
            rec._deliver()
        except Exception:
            _logger.exception('[perf-alert] deliver failed')
        # Open incident for critical alerts
        if severity == 'critical' and category in ('synthetic', 'cache',
                                                    'system', 'rum'):
            try:
                self.env['uellow.perf.incident'].sudo().open_incident(
                    category if category in ('synthetic', 'cache', 'system')
                    else 'system',
                    message, alert=rec)
            except Exception:
                pass
        return rec

    def _deliver(self):
        for r in self:
            cfg = self.env['uellow.perf.config'].sudo().get_config()
            if r.severity == 'info':
                r.delivered = True
                continue
            sent = False
            if cfg.alert_email:
                try:
                    r._send_email(cfg.alert_email); sent = True
                except Exception:
                    _logger.exception('email')
            if cfg.alert_beena:
                try:
                    r._post_beena(); sent = True
                except Exception:
                    _logger.exception('beena')
            if cfg.alert_slack_webhook:
                _async_post(lambda u=cfg.alert_slack_webhook, x=r:
                            x._post_slack(u))
                sent = True
            if cfg.alert_discord_webhook:
                _async_post(lambda u=cfg.alert_discord_webhook, x=r:
                            x._post_discord(u))
                sent = True
            if cfg.alert_telegram_token and cfg.alert_telegram_chat:
                _async_post(lambda t=cfg.alert_telegram_token,
                                   c=cfg.alert_telegram_chat, x=r:
                            x._post_telegram(t, c))
                sent = True
            if cfg.alert_sentry_dsn and r.severity == 'critical':
                _async_post(lambda d=cfg.alert_sentry_dsn, x=r:
                            x._post_sentry(d))
                sent = True
            if sent:
                r.delivered = True

    def _send_email(self, to):
        self.ensure_one()
        subject = f'[Perf Guardian {self.severity.upper()}] {self.category}'
        body = (f'<p><b>Severity:</b> {self.severity}</p>'
                f'<p><b>Category:</b> {self.category}</p>'
                f'<p><b>Time:</b> {self.create_date}</p>'
                f'<p><b>Message:</b><br/>{self.name}</p>')
        self.env['mail.mail'].sudo().create({
            'subject': subject, 'body_html': body,
            'email_to': to, 'auto_delete': True,
        }).send()

    def _post_beena(self):
        self.ensure_one()
        Conv = self.env.get('beena.conversation')
        Msg = self.env.get('beena.message')
        if not Conv or not Msg:
            return
        admin = self.env.ref('base.user_admin', raise_if_not_found=False)
        if not admin:
            return
        conv = Conv.sudo().search([('user_id', '=', admin.id)],
            order='create_date desc', limit=1)
        if not conv:
            conv = Conv.sudo().create({'user_id': admin.id,
                                       'name': 'Perf Guardian alerts'})
        emoji = {'critical': '🔴', 'warning': '🟡'}.get(self.severity, '🔵')
        Msg.sudo().create({
            'conversation_id': conv.id, 'role': 'assistant',
            'content': f'{emoji} *Perf Guardian {self.severity.upper()}* '
                       f'({self.category})\n{self.name}',
        })

    def _post_slack(self, url):
        emoji = {'critical': ':red_circle:', 'warning': ':warning:'}.get(
            self.severity, ':information_source:')
        return _post_json(url, {
            'text': f'{emoji} *Perf Guardian {self.severity.upper()}* '
                    f'({self.category}): {self.name}',
        })

    def _post_discord(self, url):
        color = {'critical': 0xc92a2a, 'warning': 0xb8860b}.get(
            self.severity, 0x2cb67d)
        return _post_json(url, {
            'embeds': [{
                'title': f'Perf Guardian — {self.severity.upper()}',
                'description': self.name,
                'color': color,
                'fields': [
                    {'name': 'Category', 'value': self.category,
                     'inline': True},
                    {'name': 'Time', 'value': str(self.create_date),
                     'inline': True},
                ],
            }],
        })

    def _post_telegram(self, token, chat_id):
        url = f'https://api.telegram.org/bot{token}/sendMessage'
        emoji = {'critical': '🔴', 'warning': '🟡'}.get(self.severity, '🔵')
        return _post_json(url, {
            'chat_id': chat_id,
            'text': f'{emoji} *Perf Guardian {self.severity.upper()}* '
                    f'({self.category})\n{self.name}',
            'parse_mode': 'Markdown',
        })

    def _post_sentry(self, dsn):
        """Best-effort: parse DSN, post event."""
        try:
            from urllib.parse import urlparse
            p = urlparse(dsn)
            key, project = p.username, p.path.strip('/')
            url = (f'{p.scheme}://{p.hostname}'
                   f'{":" + str(p.port) if p.port else ""}'
                   f'/api/{project}/store/')
            return _post_json(url, {
                'message': self.name,
                'level': 'error' if self.severity == 'critical' else 'warning',
                'tags': {'category': self.category},
                'platform': 'python',
            }, headers={
                'X-Sentry-Auth': f'Sentry sentry_version=7,sentry_key={key}',
            })
        except Exception:
            return False
