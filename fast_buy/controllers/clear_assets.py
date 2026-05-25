from odoo import http
from odoo.http import request

class ClearAssets(http.Controller):

    @http.route(['/fb-clear-cache'], type='http', auth='user', website=True)
    def clear_cache(self, **post):
        """Delete all compiled JS/CSS bundles so Odoo rebuilds them fresh"""
        try:
            request.env['ir.attachment'].sudo().search([
                ('url', 'like', '/web/assets/')
            ]).unlink()
            request.env['ir.attachment'].sudo().search([
                ('name', 'like', 'web.assets_frontend')
            ]).unlink()
            return '<h2 style="font-family:sans-serif;padding:30px;color:green">✅ Assets cleared! Now reload the page with Ctrl+Shift+R</h2>'
        except Exception as e:
            return '<h2 style="font-family:sans-serif;padding:30px;color:red">Error: %s</h2>' % str(e)
