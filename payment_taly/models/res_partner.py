# -*- coding: utf-8 -*-
import logging
import re

from odoo import api, models

_logger = logging.getLogger(__name__)

# Strong separators that almost always mean "two different numbers were typed
# into one field" (e.g. "60477731/97276887"). A normal single phone never uses
# these between two full numbers — spaces, dashes and () inside ONE number are
# left untouched.
_MULTI_SEP = re.compile(r'[\/,;|\n]+')


def _uellow_single_phone(value):
    """Collapse a multi-number phone string to the FIRST valid number.

    A "valid number" segment carries at least 7 digits. If two or more such
    segments are present, only the first is kept — so the phone field can never
    again store two mashed numbers (which breaks SMS/OTP, payment gateways and
    delivery). Single numbers (no strong separator) pass through unchanged."""
    if not value or not isinstance(value, str):
        return value
    segments = [s.strip() for s in _MULTI_SEP.split(value)]
    valid = [s for s in segments if len(re.sub(r'\D', '', s)) >= 7]
    if len(valid) >= 2:
        return valid[0]
    return value


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def _uellow_clean_phone_vals(self, vals):
        for fld in ('phone', 'mobile'):
            if vals.get(fld):
                cleaned = _uellow_single_phone(vals[fld])
                if cleaned != vals[fld]:
                    _logger.info("Sanitized partner %s '%s' -> '%s' (multi-number)",
                                 fld, vals[fld], cleaned)
                    vals[fld] = cleaned
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._uellow_clean_phone_vals(vals)
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('phone') or vals.get('mobile'):
            vals = dict(vals)
            self._uellow_clean_phone_vals(vals)
        return super().write(vals)
