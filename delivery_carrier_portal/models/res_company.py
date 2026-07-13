# -*- coding: utf-8 -*-
import base64
import logging
from io import BytesIO

from odoo import models

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = 'res.company'

    def get_settlement_logo_data_uri(self):
        """Return the company logo flattened onto a solid white background.

        The company logo is a palette PNG with transparency; wkhtmltopdf
        renders transparent pixels as black, producing an ugly black box
        around the logo in PDF reports. Compositing onto white removes it.
        """
        self.ensure_one()
        if not self.logo:
            return ''
        try:
            from PIL import Image
            raw = base64.b64decode(self.logo)
            img = Image.open(BytesIO(raw)).convert('RGBA')
            bg = Image.new('RGBA', img.size, (255, 255, 255, 255))
            bg.alpha_composite(img)
            out = BytesIO()
            bg.convert('RGB').save(out, format='PNG')
            return 'data:image/png;base64,' + base64.b64encode(out.getvalue()).decode()
        except Exception as e:  # pragma: no cover - never break the report
            _logger.warning("settlement logo flatten failed: %s", e)
            return 'data:image/png;base64,' + (self.logo.decode() if isinstance(self.logo, bytes) else self.logo)
