# -*- coding: utf-8 -*-
"""dropship.text.rule — brand-scrub / word-replacement rules.

Every incoming title/description is passed through these find→replace rules so
provider names ("AliExpress", "AE", store names, "Ship from China", ...) never
reach the customer. Rules are applied on ingest AND before display, so editing
a rule instantly cleans existing listings too.
"""
import re

from odoo import api, fields, models


class DropshipTextRule(models.Model):
    _name = 'dropship.text.rule'
    _description = 'Dropship Text Replacement Rule'
    _order = 'sequence, id'

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    find = fields.Char(string="Find", required=True, help="Word/phrase to remove or replace.")
    replace = fields.Char(string="Replace With", default="",
                          help="Leave empty to simply delete the word.")
    is_regex = fields.Boolean(string="Regex")
    case_sensitive = fields.Boolean(default=False)
    hit_count = fields.Integer(
        string="Replacements", default=0, readonly=True,
        help="Total number of times this rule has actually replaced text "
             "during ingest / clean-up (display-time scrubbing is not counted).")

    def action_reset_hits(self):
        """Zero the replacement counters (button on the list/form view)."""
        self.write({'hit_count': 0})

    @api.model
    def _apply_all(self, text, count=False):
        """Run every active rule over ``text``. Returns cleaned text.

        When ``count`` is True, each rule's ``hit_count`` is incremented by the
        number of substitutions it actually made (persisted). Callers on the
        DISPLAY path pass count=False so a page view never writes or inflates
        the counters — only ingest / one-off clean-ups count.
        """
        if not text:
            return text
        for rule in self.search([('active', '=', True)]):
            flags = 0 if rule.case_sensitive else re.IGNORECASE
            try:
                pattern = rule.find if rule.is_regex else re.escape(rule.find)
                if count:
                    text, n = re.subn(pattern, rule.replace or '', text,
                                      flags=flags)
                    if n:
                        rule.sudo().hit_count += n
                else:
                    text = re.sub(pattern, rule.replace or '', text,
                                  flags=flags)
            except re.error:
                # a broken regex rule must never break ingestion
                continue
        # tidy leftover double spaces from deletions
        return re.sub(r'\s{2,}', ' ', text).strip()
