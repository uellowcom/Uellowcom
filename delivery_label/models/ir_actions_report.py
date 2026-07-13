# -*- coding: utf-8 -*-
"""Force UTF-8 in wkhtmltopdf.

Odoo's `_build_wkhtmltopdf_args` never passes `--encoding`, and `_prepare_html`
splits the document into header/body/footer fragments — dropping the
`<meta charset="utf-8">` from <head>. wkhtmltopdf then defaults to latin-1 and
Arabic text renders as garbled mojibake (e.g. "Ø¹Ù„ÙŠ" instead of "علي").

Passing `--encoding utf-8` explicitly fixes it for every PDF report. This is
safe for latin reports too, since all Odoo QWeb templates are UTF-8.
"""
from odoo import models


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _build_wkhtmltopdf_args(self, *args, **kwargs):
        command_args = super()._build_wkhtmltopdf_args(*args, **kwargs)
        if '--encoding' not in command_args:
            command_args = command_args + ['--encoding', 'utf-8']
        return command_args
