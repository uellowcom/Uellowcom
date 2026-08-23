# -*- coding: utf-8 -*-
from odoo import models, _
from odoo.exceptions import ValidationError


class SaleOrderPhoneGuard(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        # Universal backstop: a website order must carry a customer phone before
        # it can become a real (sale) order. Covers COD / UPayments / Taly BNPL
        # webhook / mobile-app checkout — any path that reaches action_confirm.
        for o in self:
            if o.website_id and not (o.partner_id.phone or o.partner_id.mobile):
                raise ValidationError(_(
                    'لا يمكن تأكيد الطلب %s بدون رقم هاتف العميل. '
                    'الرجاء إدخال رقم الهاتف أولاً.') % (o.name or ''))
        return super().action_confirm()
