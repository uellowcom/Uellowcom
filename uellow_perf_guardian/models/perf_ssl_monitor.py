"""SSL certificate + domain expiry monitor + anomaly detector + self-check.
"""
import logging
import socket
import ssl
import statistics
from datetime import datetime, timedelta

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class PerfSslMonitor(models.Model):
    _name = 'uellow.perf.ssl.monitor'
    _description = 'Uellow Performance — SSL + domain expiry'
    _order = 'create_date desc'

    domain = fields.Char(required=True, index=True)
    cert_subject = fields.Char()
    cert_issuer = fields.Char()
    cert_not_before = fields.Datetime()
    cert_not_after = fields.Datetime()
    cert_days_left = fields.Integer(index=True)
    domain_expiry = fields.Datetime()
    domain_days_left = fields.Integer()
    error = fields.Char()

    @api.model
    def cron_check(self):
        cfg = self.env['uellow.perf.config'].sudo().get_config()
        if not cfg.ssl_monitor_enabled:
            return 0
        domain = (cfg.ssl_monitor_domain or '').strip() or 'www.uellow.com'
        warn = max(1, int(cfg.ssl_warn_days or 30))
        crit = max(1, int(cfg.ssl_crit_days or 7))

        vals = {'domain': domain}
        # ─── SSL cert ──────────────────────────────────────────
        try:
            ctx = ssl.create_default_context()
            with socket.create_connection((domain, 443), timeout=8) as sock:
                with ctx.wrap_socket(sock, server_hostname=domain) as ssock:
                    cert = ssock.getpeercert()
            not_after = datetime.strptime(
                cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
            not_before = datetime.strptime(
                cert['notBefore'], '%b %d %H:%M:%S %Y %Z')
            days = (not_after - datetime.utcnow()).days
            vals.update({
                'cert_not_before': not_before,
                'cert_not_after': not_after,
                'cert_days_left': days,
                'cert_subject': str(dict(x[0] for x in cert.get('subject', []))),
                'cert_issuer': str(dict(x[0] for x in cert.get('issuer', []))),
            })
        except Exception as e:
            vals['error'] = f'SSL: {str(e)[:200]}'
            _logger.warning('[ssl-monitor] %s', vals['error'])

        # ─── Domain WHOIS expiry (best-effort, library optional) ──
        try:
            import whois  # type: ignore
            w = whois.whois(domain)
            expiry = w.expiration_date
            if isinstance(expiry, list):
                expiry = expiry[0] if expiry else None
            if expiry:
                if isinstance(expiry, str):
                    expiry = datetime.fromisoformat(expiry.replace('Z', ''))
                vals['domain_expiry'] = expiry
                vals['domain_days_left'] = (expiry - datetime.utcnow()).days
        except Exception:
            pass

        rec = self.create(vals)

        Alert = self.env['uellow.perf.alert'].sudo()
        Inc = self.env['uellow.perf.incident'].sudo()
        d_left = vals.get('cert_days_left') or 9999
        if d_left <= crit:
            a = Alert.fire('cache', 'critical',
                f'SSL cert for {domain} expires in {d_left} days')
            Inc.open_incident('ssl', f'SSL near expiry: {d_left}d', alert=a)
        elif d_left <= warn:
            Alert.fire('cache', 'warning',
                f'SSL cert for {domain} expires in {d_left} days')
        dom_left = vals.get('domain_days_left') or 9999
        if dom_left and dom_left <= warn:
            Alert.fire('cache', 'warning',
                f'Domain {domain} expires in {dom_left} days')
        return rec.id


class PerfAnomalyDetector(models.AbstractModel):
    """Computes rolling baseline + z-score for key metrics and alerts
    when a sample deviates significantly."""
    _name = 'uellow.perf.anomaly'
    _description = 'Uellow Performance — anomaly detector'

    @api.model
    def cron_detect(self):
        cfg = self.env['uellow.perf.config'].sudo().get_config()
        if not cfg.anomaly_enabled:
            return 0
        threshold = float(cfg.anomaly_z_threshold or 2.5)
        n = 0
        # System load 1m — compare last hour vs prior 24h
        self.env.cr.execute("""
            SELECT load_1m FROM uellow_perf_system_metric
            WHERE create_date >= NOW() - INTERVAL '24 hours'
              AND create_date <  NOW() - INTERVAL '1 hour'
        """)
        base = [r[0] for r in self.env.cr.fetchall() if r[0] is not None]
        self.env.cr.execute("""
            SELECT load_1m FROM uellow_perf_system_metric
            WHERE create_date >= NOW() - INTERVAL '5 minutes'
        """)
        recent = [r[0] for r in self.env.cr.fetchall() if r[0] is not None]
        if len(base) >= 30 and recent:
            mean = statistics.mean(base)
            stdev = statistics.pstdev(base) or 1
            cur = statistics.mean(recent)
            z = (cur - mean) / stdev if stdev else 0
            if z >= threshold:
                self.env['uellow.perf.alert'].sudo().fire(
                    'system', 'warning',
                    f'Anomaly: load 1m {cur:.2f} (baseline {mean:.2f}, z={z:.1f})')
                n += 1

        # RUM LCP — compare last hour vs prior 7 days same hour-of-day
        self.env.cr.execute("""
            SELECT lcp_ms FROM uellow_perf_metric
            WHERE create_date >= NOW() - INTERVAL '7 days'
              AND create_date <  NOW() - INTERVAL '1 hour'
              AND EXTRACT(hour FROM create_date) = EXTRACT(hour FROM NOW())
        """)
        base = [r[0] for r in self.env.cr.fetchall() if r[0]]
        self.env.cr.execute("""
            SELECT lcp_ms FROM uellow_perf_metric
            WHERE create_date >= NOW() - INTERVAL '1 hour' AND lcp_ms > 0
        """)
        recent = [r[0] for r in self.env.cr.fetchall() if r[0]]
        if len(base) >= 20 and len(recent) >= 5:
            mean = statistics.mean(base)
            stdev = statistics.pstdev(base) or 1
            cur = statistics.mean(recent)
            z = (cur - mean) / stdev if stdev else 0
            if z >= threshold:
                self.env['uellow.perf.alert'].sudo().fire(
                    'rum', 'warning',
                    f'Anomaly: LCP {int(cur)}ms (baseline {int(mean)}ms, z={z:.1f})')
                n += 1
        return n


class PerfSelfCheck(models.AbstractModel):
    """Self-check: verifies the throttle middleware is actually firing by
    making a synthetic bot request and checking the hit was logged.
    Alerts if not — means the middleware silently broke."""
    _name = 'uellow.perf.self.check'
    _description = 'Uellow Performance — self-check'

    @api.model
    def cron_run(self):
        """Fire a synthetic bot request and verify the throttle middleware
        bumped SOME bot class's counter. Uses UA containing 'bot' which
        is matched by the Generic bot class that always exists."""
        cfg = self.env['uellow.perf.config'].sudo().get_config()
        if not cfg.self_check_enabled:
            return False
        from urllib import request as urlreq
        cls_model = self.env['uellow.perf.bot.class'].sudo()
        # Sum req_today across all classes before
        self.env.cr.execute(
            "SELECT COALESCE(SUM(req_today), 0) FROM uellow_perf_bot_class")
        before = self.env.cr.fetchone()[0]
        try:
            req = urlreq.Request('http://localhost:8069/',
                headers={'User-Agent': 'Mozilla/5.0 (compatible; '
                                       'PerfGuardian-self-check-bot/1.0)',
                         'Cookie': ''})
            with urlreq.urlopen(req, timeout=5) as resp:
                resp.read(1024)
        except Exception as e:
            self.env['uellow.perf.alert'].sudo().fire(
                'system', 'warning',
                f'Self-check request failed: {str(e)[:100]}')
            return False
        # Re-query
        self.env.cr.commit()  # ensure we see the writer's commit
        self.env.cr.execute(
            "SELECT COALESCE(SUM(req_today), 0) FROM uellow_perf_bot_class")
        after = self.env.cr.fetchone()[0]
        if after > before:
            return True
        self.env['uellow.perf.alert'].sudo().fire(
            'system', 'critical',
            'Self-check: throttle middleware did NOT increment any counter')
        return False
