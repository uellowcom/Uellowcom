from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class TranslationGlossary(models.Model):
    """
    Shared EN→AR term dictionary (idea #38).

    Keeps product translations consistent: the same English term always maps
    to the same Arabic word across every product and every import. The active
    entries are injected into the AI translation prompt as a hard constraint.
    """
    _name = 'uellow.sc.glossary'
    _description = 'Smart Connector Translation Glossary'
    _order = 'term_en'

    term_en = fields.Char('English Term', required=True, index=True)
    term_ar = fields.Char('Arabic Term', required=True)
    note = fields.Char('Note', help='Optional context for translators / AI.')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('uniq_term_en', 'unique(term_en)',
         'This English term already exists in the glossary.'),
    ]

    @api.constrains('term_en', 'term_ar')
    def _check_terms(self):
        for rec in self:
            if not (rec.term_en or '').strip() or not (rec.term_ar or '').strip():
                raise ValidationError(_('Both English and Arabic terms are required.'))

    @api.model
    def build_prompt_block(self, limit=120):
        """Return a compact glossary block to embed in an AI prompt.

        Capped so a huge glossary can't blow the token budget; returns '' when
        empty so callers can skip the section cleanly.
        """
        terms = self.search([('active', '=', True)], limit=limit)
        if not terms:
            return ''
        pairs = '\n'.join('- "%s" => "%s"' % (t.term_en, t.term_ar) for t in terms)
        return (
            "\nGLOSSARY (MANDATORY): translate these terms EXACTLY as given, "
            "never invent a different Arabic word for them:\n" + pairs + "\n"
        )
