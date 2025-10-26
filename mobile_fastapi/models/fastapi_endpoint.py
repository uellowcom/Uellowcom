# -*- coding: utf-8 -*-
import logging
from typing import List

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from fastapi import APIRouter

from ..routers import (
    auth_router,
    product_router,
    home_router,
    wallet_router,
    notification_router,
)

_logger = logging.getLogger(__name__)


class FastapiEndpoint(models.Model):
    _inherit = "fastapi.endpoint"

    # Properly extend the app selection field
    app = fields.Selection(
        selection_add=[("mobile_api", "Mobile API")], ondelete={"mobile_api": "cascade"}
    )

    def _get_fastapi_routers(self) -> List[APIRouter]:
        """Return the API routers to use for the mobile API"""
        self.ensure_one()
        if self.app == "mobile_api":
            return [
                auth_router.router,
                product_router.router,
                home_router.router,
                wallet_router.router,
                notification_router.router,
            ]
        return super()._get_fastapi_routers()
