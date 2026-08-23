# -*- coding: utf-8 -*-
from odoo import api, fields, models


class UellowSearchLog(models.Model):
    """Lightweight analytics of what shoppers type into app search — and,
    crucially, which queries return NOTHING (a to-do list: add the product or
    a synonym). Written fire-and-forget from the products API; never blocks."""
    _name = 'uellow.search.log'
    _description = 'Uellow — سجل عمليات البحث في التطبيق'
    _order = 'create_date desc'
    _rec_name = 'query'

    query = fields.Char('كلمة البحث', index=True)
    query_norm = fields.Char('الصيغة المُطبّعة', index=True)
    result_count = fields.Integer('عدد النتائج')
    has_results = fields.Boolean('وُجدت نتائج؟', index=True)
    source = fields.Char('المصدر')
    partner_id = fields.Many2one('res.partner', string='العميل',
                                 ondelete='set null', index=True)
    session = fields.Char('الجلسة', index=True)

    @api.model
    def log_search(self, query, query_norm, result_count,
                   source='app', partner_id=False, session=False):
        try:
            q = (query or '').strip()
            if len(q) < 2:
                return
            self.sudo().create({
                'query': q[:120],
                'query_norm': (query_norm or '')[:120],
                'result_count': int(result_count or 0),
                'has_results': bool(result_count),
                'source': (source or 'app')[:16],
                'partner_id': partner_id or False,
                'session': (session or '')[:64],
            })
        except Exception:
            pass
