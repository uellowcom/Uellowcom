"""FAQ entries on a landing page — emitted as schema.org/FAQPage JSON-LD."""
from odoo import models, fields


class SEOPageFAQ(models.Model):
    _name = 'uellow.seo.page.faq'
    _description = 'Landing Page FAQ Entry'
    _order = 'sequence, id'

    page_id = fields.Many2one(
        'uellow.seo.page', ondelete='cascade', required=True, index=True,
    )
    sequence = fields.Integer(default=10)

    question_en = fields.Char('Question (EN)', required=True)
    question_ar = fields.Char('Question (AR)')
    answer_en = fields.Text('Answer (EN)', required=True)
    answer_ar = fields.Text('Answer (AR)')
