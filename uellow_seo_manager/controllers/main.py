# -*- coding: utf-8 -*-
"""Internal API for the SEO dashboard."""
import json
from odoo import http
from odoo.http import request


class SEOManagerAPI(http.Controller):

    @http.route('/uellow/seo/health', type='http', auth='user', methods=['GET'], csrf=False)
    def health(self, **kw):
        """Lightweight JSON snapshot of the latest audit — for dashboards."""
        if not request.env.user.has_group('base.group_system'):
            return request.make_response(json.dumps({'error':'forbidden'}), status=403)
        Audit = request.env['uellow.seo.audit'].sudo()
        latest = Audit.latest_for_dashboard()
        if not latest:
            return request.make_response(
                json.dumps({'score': None, 'pages_audited': 0, 'issues': {}}),
                headers=[('Content-Type', 'application/json')])
        return request.make_response(json.dumps({
            'score': latest.score,
            'pages_audited': latest.pages_audited,
            'create_date': latest.create_date and latest.create_date.isoformat(),
            'issues': {
                'critical': latest.issue_count_critical,
                'warning':  latest.issue_count_warning,
                'info':     latest.issue_count_info,
            },
        }), headers=[('Content-Type', 'application/json')])
