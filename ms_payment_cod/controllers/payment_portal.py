import urllib.parse

import werkzeug

from odoo import _, http
from odoo.exceptions import AccessError, ValidationError
from odoo.http import request

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.controllers.post_processing import PaymentPostProcessing
from odoo.addons.portal.controllers import portal
from odoo.addons.payment.controllers.portal import PaymentPortal


class PaymentPortalExtended(PaymentPortal):

    def _create_transaction(
            self, provider_id, payment_method_id, token_id, amount, currency_id, partner_id, flow,
            tokenization_requested, landing_route, reference_prefix=None, is_validation=False,
            custom_create_values=None, **kwargs
    ):
        provider_sudo = request.env['payment.provider'].sudo().browse(provider_id)
        reference = request.env['payment.transaction']._compute_reference(
            provider_sudo.code,
            prefix=reference_prefix,
            **(custom_create_values or {}),
            **kwargs
        )
        sale_sudo = request.env['sale.order'].sudo().search([
            ('name', '=', reference)
        ], limit=1)
        if provider_sudo.custom_mode == 'cod' and sale_sudo:
            sale_sudo.add_cod_fee()
            amount = sale_sudo.amount_total
        res = super()._create_transaction(
            provider_id=provider_id,
            payment_method_id=payment_method_id,
            token_id=token_id,
            amount=amount,
            currency_id=currency_id,
            partner_id=partner_id,
            flow=flow,
            tokenization_requested=tokenization_requested,
            landing_route=landing_route,
            reference_prefix=reference_prefix,
            is_validation=is_validation,
            custom_create_values=custom_create_values,
            **kwargs
        )
        return res
