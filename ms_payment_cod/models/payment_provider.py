import requests
import uuid
import json
import hashlib
import base64
import hmac
import logging
import string

from datetime import datetime
from odoo import fields, models, http, _
from odoo.exceptions import ValidationError


_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    custom_mode = fields.Selection(selection_add=[
        ('cod', "Cash on Delivery")
    ])
    cod_rule_ids = fields.One2many(
        comodel_name='payment.provider.cod.rule',
        inverse_name='provider_id',
        string='Rules',
        required=False)
