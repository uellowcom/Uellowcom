# -*- coding: utf-8 -*-
"""FastAPI Endpoint Registration for Mobile API"""

from odoo import fields, models


class FastapiEndpoint(models.Model):
    """Extend fastapi.endpoint to register mobile_api app"""

    _inherit = "fastapi.endpoint"

    app: str = fields.Selection(
        selection_add=[("mobile_api", "Mobile API")], ondelete={"mobile_api": "cascade"}
    )

    def _get_fastapi_routers(self):
        """Return the FastAPI routers for the mobile_api app"""
        if self.app == "mobile_api":
            # Import routers here to avoid circular imports
            from ..routers import (
                mobile_auth_router,
                mobile_home_router,
                mobile_product_router,
                mobile_wallet_router,
                mobile_notification_router,
            )

            return [
                mobile_auth_router.router,
                mobile_home_router.router,
                mobile_product_router.router,
                mobile_wallet_router.router,
                mobile_notification_router.router,
            ]
        return super()._get_fastapi_routers()
