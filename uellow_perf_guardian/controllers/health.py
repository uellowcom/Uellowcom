"""Read-only health endpoint + dashboard JSON for auto-refresh."""
import json

from odoo import fields, http
from odoo.http import request, Response


class HealthController(http.Controller):

    @http.route('/perf/health', type='http', auth='public', csrf=False,
                methods=['GET'], save_session=False)
    def health(self, **kw):
        """200 OK when no critical alert in last 5 min AND last synthetic
        probe was OK. 503 otherwise. Body is a small JSON."""
        env = request.env
        cutoff = fields.Datetime.subtract(fields.Datetime.now(), minutes=5)
        n_crit = env['uellow.perf.alert'].sudo().search_count([
            ('severity', '=', 'critical'),
            ('create_date', '>=', cutoff),
            ('resolved', '=', False),
        ])
        last_synth = env['uellow.perf.synthetic'].sudo().search(
            [], order='create_date desc', limit=1)
        synth_ok = bool(last_synth) and last_synth.ok and \
            (last_synth.total_ms or 0) < 4000
        ok = (n_crit == 0) and synth_ok
        body = json.dumps({
            'ok': ok,
            'critical_alerts_5m': n_crit,
            'last_synthetic_ok': synth_ok,
            'last_synthetic_ms': int(last_synth.total_ms or 0)
                                  if last_synth else None,
        })
        return Response(body, status=200 if ok else 503,
                        content_type='application/json')

    @http.route('/perf/dashboard/json', type='http', auth='user',
                csrf=False, methods=['GET'])
    def dashboard_json(self, **kw):
        d = request.env['uellow.perf.dashboard'].sudo().get_summary()
        return Response(json.dumps(d, default=str), status=200,
                        content_type='application/json')
