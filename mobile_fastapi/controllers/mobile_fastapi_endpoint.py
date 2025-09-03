# -*- coding: utf-8 -*-
import logging
from typing import List

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from fastapi import APIRouter, Depends

from ..routers import auth_router, product_router, home_router, wallet_router, notification_router

_logger = logging.getLogger(__name__)


class MobileFastApiEndpoint(models.Model):
    _name = 'mobile.fastapi.endpoint'
    _inherit = 'fastapi.endpoint'
    _description = 'Mobile FastAPI Endpoint'

    @api.model
    def _selection_app(self):
        """Add mobile API to the list of available apps"""
        selection = super()._selection_app()
        return selection + [('mobile_api', 'Mobile API')]

    def _get_fastapi_routers(self) -> List[APIRouter]:
        """Return the API routers to use for the mobile API"""
        self.ensure_one()
        if self.app == 'mobile_api':
            return [
                auth_router.router,
                # Uncomment these as they are implemented
                # product_router.router,
                # home_router.router,
                # wallet_router.router,
                # notification_router.router,
            ]
        return super()._get_fastapi_routers()

    @api.model
    def _create_default_mobile_endpoint(self):
        """Create the default mobile API endpoint if it doesn't exist"""
        endpoint = self.search([('app', '=', 'mobile_api')], limit=1)
        if not endpoint:
            self.create({
                'name': 'Mobile API',
                'description': 'Mobile API endpoints for the Uellow mobile application',
                'root_path': '/mobile',
                'app': 'mobile_api',
                'save_http_session': False,
            })
            _logger.info('Created default Mobile API endpoint')
        return True
