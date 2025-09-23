# -*- coding: utf-8 -*-
"""Mobile Authentication Controller using Odoo HTTP and models"""

import json
import logging
from datetime import datetime, timedelta

from odoo import http, _, fields
from odoo.http import request, Response
from odoo.exceptions import ValidationError, AccessError

from ..services.firebase_service import FirebaseService
from ..services.jwt_service import JWTService

_logger = logging.getLogger(__name__)


class MobileAuthController(http.Controller):
    """Mobile Authentication HTTP Controller"""

    def _validate_request_data(self, required_fields, data):
        """Validate required fields in request data"""
        missing_fields = [
            field for field in required_fields if field not in data or not data[field]
        ]
        if missing_fields:
            return False, f"Missing required fields: {', '.join(missing_fields)}"
        return True, None

    def _create_response(self, data=None, error=None, status=200):
        """Create standardized JSON response"""
        if error:
            response_data = {"success": False, "error": error, "data": None}
            status = status or 400
        else:
            response_data = {"success": True, "error": None, "data": data or {}}

        return request.make_response(
            json.dumps(response_data),
            headers={"Content-Type": "application/json"},
            status=status,
        )

    @http.route(
        "/mobile/v1/auth/register",
        auth="public",
        methods=["POST"],
        type="json",
        csrf=False,
    )
    def register(self):
        """Register a new user with email and password"""
        try:
            data = request.jsonrequest

            # Validate required fields
            required_fields = ["email", "password", "name"]
            is_valid, error_msg = self._validate_request_data(required_fields, data)
            if not is_valid:
                return self._create_response(error=error_msg, status=400)

            # Check if user already exists
            existing_user = (
                request.env["res.partner"]
                .sudo()
                .search([("email", "=", data["email"])], limit=1)
            )

            if existing_user:
                return self._create_response(error="User already exists", status=409)

            # Create new user
            user_vals = {
                "name": data["name"],
                "email": data["email"],
                "phone": data.get("phone"),
                "is_company": False,
                "customer_rank": 1,
                "mobile_user": True,
            }

            partner = request.env["res.partner"].sudo().create(user_vals)

            # Create Odoo user account if needed
            if not partner.user_ids:
                user_vals = {
                    "partner_id": partner.id,
                    "login": data["email"],
                    "password": data["password"],
                    "groups_id": [(6, 0, [request.env.ref("base.group_portal").id])],
                }
                request.env["res.users"].sudo().create(user_vals)

            # Generate JWT tokens
            jwt_service = JWTService()
            access_token = jwt_service.create_access_token(partner.id)
            refresh_token = jwt_service.create_refresh_token(partner.id)

            # Create mobile device record if device info provided
            if data.get("device_id"):
                device_vals = {
                    "partner_id": partner.id,
                    "device_id": data["device_id"],
                    "device_type": data.get("device_type", "unknown"),
                    "is_active": True,
                    "last_used": fields.Datetime.now(),
                }
                request.env["mobile.device"].sudo().create(device_vals)

            response_data = {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "Bearer",
                "expires_in": 1800,  # 30 minutes
                "user": {
                    "id": partner.id,
                    "name": partner.name,
                    "email": partner.email,
                    "phone": partner.phone,
                },
            }

            return self._create_response(response_data)

        except Exception as e:
            _logger.error(f"Registration error: {str(e)}")
            return self._create_response(error="Registration failed", status=500)

    @http.route(
        "/mobile/v1/auth/login",
        auth="public",
        methods=["POST"],
        type="json",
        csrf=False,
    )
    def login(self):
        """Login with email and password"""
        try:
            data = request.jsonrequest

            # Validate required fields
            required_fields = ["email", "password"]
            is_valid, error_msg = self._validate_request_data(required_fields, data)
            if not is_valid:
                return self._create_response(error=error_msg, status=400)

            # Authenticate user
            user = (
                request.env["res.users"]
                .sudo()
                .search([("login", "=", data["email"])], limit=1)
            )

            if not user:
                return self._create_response(error="Invalid credentials", status=401)

            # Verify password
            try:
                user.sudo().check_credentials(data["password"])
            except:
                return self._create_response(error="Invalid credentials", status=401)

            partner = user.partner_id

            # Generate JWT tokens
            jwt_service = JWTService()
            access_token = jwt_service.create_access_token(partner.id)
            refresh_token = jwt_service.create_refresh_token(partner.id)

            # Update or create mobile device record
            device = None
            if data.get("device_id"):
                device = (
                    request.env["mobile.device"]
                    .sudo()
                    .search(
                        [
                            ("partner_id", "=", partner.id),
                            ("device_id", "=", data["device_id"]),
                        ],
                        limit=1,
                    )
                )

                if device:
                    device.sudo().write(
                        {"last_used": fields.Datetime.now(), "is_active": True}
                    )
                else:
                    device_vals = {
                        "partner_id": partner.id,
                        "device_id": data["device_id"],
                        "device_type": data.get("device_type", "unknown"),
                        "is_active": True,
                        "last_used": fields.Datetime.now(),
                    }
                    device = request.env["mobile.device"].sudo().create(device_vals)

            response_data = {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "Bearer",
                "expires_in": 1800,
                "user": {
                    "id": partner.id,
                    "name": partner.name,
                    "email": partner.email,
                    "phone": partner.phone,
                },
            }

            return self._create_response(response_data)

        except Exception as e:
            _logger.error(f"Login error: {str(e)}")
            return self._create_response(error="Login failed", status=500)

    @http.route(
        "/mobile/v1/auth/firebase-sms",
        auth="public",
        methods=["POST"],
        type="json",
        csrf=False,
    )
    def firebase_sms_auth(self):
        """Authenticate using Firebase SMS"""
        try:
            data = request.jsonrequest

            required_fields = ["phone_number"]
            is_valid, error_msg = self._validate_request_data(required_fields, data)
            if not is_valid:
                return self._create_response(error=error_msg, status=400)

            firebase_service = FirebaseService()

            # If verification code provided, verify it
            if data.get("verification_code") and data.get("verification_id"):
                try:
                    # Verify the SMS code with Firebase
                    result = firebase_service.verify_sms_code(
                        data["verification_id"], data["verification_code"]
                    )

                    if not result:
                        return self._create_response(
                            error="Invalid verification code", status=400
                        )

                    # Find or create user with phone number
                    partner = (
                        request.env["res.partner"]
                        .sudo()
                        .search([("phone", "=", data["phone_number"])], limit=1)
                    )

                    if not partner:
                        # Create new user
                        partner_vals = {
                            "name": f"User {data['phone_number']}",
                            "phone": data["phone_number"],
                            "is_company": False,
                            "customer_rank": 1,
                            "mobile_user": True,
                        }
                        partner = request.env["res.partner"].sudo().create(partner_vals)

                    # Generate JWT tokens
                    jwt_service = JWTService()
                    access_token = jwt_service.create_access_token(partner.id)
                    refresh_token = jwt_service.create_refresh_token(partner.id)

                    response_data = {
                        "access_token": access_token,
                        "refresh_token": refresh_token,
                        "token_type": "Bearer",
                        "expires_in": 1800,
                        "user": {
                            "id": partner.id,
                            "name": partner.name,
                            "phone": partner.phone,
                        },
                    }

                    return self._create_response(response_data)

                except Exception as e:
                    _logger.error(f"Firebase SMS verification error: {str(e)}")
                    return self._create_response(
                        error="SMS verification failed", status=400
                    )

            else:
                # Send SMS verification code
                try:
                    verification_id = firebase_service.send_sms_verification(
                        data["phone_number"]
                    )
                    return self._create_response(
                        {
                            "verification_id": verification_id,
                            "message": "SMS verification code sent",
                        }
                    )
                except Exception as e:
                    _logger.error(f"Firebase SMS send error: {str(e)}")
                    return self._create_response(error="Failed to send SMS", status=400)

        except Exception as e:
            _logger.error(f"Firebase SMS auth error: {str(e)}")
            return self._create_response(error="SMS authentication failed", status=500)

    @http.route(
        "/mobile/v1/auth/social/<string:provider>",
        auth="public",
        methods=["POST"],
        type="json",
        csrf=False,
    )
    def social_login(self, provider):
        """Login with social providers (Google, Facebook, Apple)"""
        try:
            data = request.jsonrequest

            if provider not in ["google", "facebook", "apple"]:
                return self._create_response(error="Unsupported provider", status=400)

            required_fields = ["id_token"]
            is_valid, error_msg = self._validate_request_data(required_fields, data)
            if not is_valid:
                return self._create_response(error=error_msg, status=400)

            firebase_service = FirebaseService()

            try:
                # Verify the social login token with Firebase
                user_info = firebase_service.verify_social_token(
                    provider, data["id_token"]
                )

                if not user_info:
                    return self._create_response(
                        error="Invalid social login token", status=401
                    )

                # Find or create user
                partner = (
                    request.env["res.partner"]
                    .sudo()
                    .search([("email", "=", user_info.get("email"))], limit=1)
                )

                if not partner:
                    # Create new user from social info
                    partner_vals = {
                        "name": user_info.get("name", f"{provider.title()} User"),
                        "email": user_info.get("email"),
                        "phone": user_info.get("phone"),
                        "is_company": False,
                        "customer_rank": 1,
                        "mobile_user": True,
                    }
                    partner = request.env["res.partner"].sudo().create(partner_vals)

                # Generate JWT tokens
                jwt_service = JWTService()
                access_token = jwt_service.create_access_token(partner.id)
                refresh_token = jwt_service.create_refresh_token(partner.id)

                response_data = {
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "token_type": "Bearer",
                    "expires_in": 1800,
                    "user": {
                        "id": partner.id,
                        "name": partner.name,
                        "email": partner.email,
                        "phone": partner.phone,
                    },
                }

                return self._create_response(response_data)

            except Exception as e:
                _logger.error(f"Social login verification error: {str(e)}")
                return self._create_response(
                    error="Social login verification failed", status=401
                )

        except Exception as e:
            _logger.error(f"Social login error: {str(e)}")
            return self._create_response(error="Social login failed", status=500)

    @http.route(
        "/mobile/v1/auth/refresh",
        auth="public",
        methods=["POST"],
        type="json",
        csrf=False,
    )
    def refresh_token(self):
        """Refresh access token"""
        try:
            data = request.jsonrequest

            required_fields = ["refresh_token"]
            is_valid, error_msg = self._validate_request_data(required_fields, data)
            if not is_valid:
                return self._create_response(error=error_msg, status=400)

            jwt_service = JWTService()

            try:
                # Verify and decode refresh token
                payload = jwt_service.decode_refresh_token(data["refresh_token"])
                partner_id = payload.get("sub")

                if not partner_id:
                    return self._create_response(
                        error="Invalid refresh token", status=401
                    )

                # Verify partner exists
                partner = request.env["res.partner"].sudo().browse(int(partner_id))
                if not partner.exists():
                    return self._create_response(error="User not found", status=401)

                # Generate new access token
                access_token = jwt_service.create_access_token(partner.id)

                response_data = {
                    "access_token": access_token,
                    "token_type": "Bearer",
                    "expires_in": 1800,
                }

                return self._create_response(response_data)

            except Exception as e:
                _logger.error(f"Token refresh error: {str(e)}")
                return self._create_response(error="Invalid refresh token", status=401)

        except Exception as e:
            _logger.error(f"Refresh token error: {str(e)}")
            return self._create_response(error="Token refresh failed", status=500)

    @http.route(
        "/mobile/v1/auth/logout",
        auth="public",
        methods=["POST"],
        type="json",
        csrf=False,
    )
    def logout(self):
        """Logout current user"""
        try:
            # Extract JWT token from Authorization header
            auth_header = request.httprequest.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return self._create_response(
                    error="Missing or invalid authorization header", status=401
                )

            token = auth_header.split(" ")[1]
            jwt_service = JWTService()

            try:
                # Verify token and get partner
                payload = jwt_service.decode_token(token)
                partner_id = payload.get("sub")

                if partner_id:
                    # Deactivate mobile devices for this user
                    devices = (
                        request.env["mobile.device"]
                        .sudo()
                        .search([("partner_id", "=", int(partner_id))])
                    )
                    devices.write({"is_active": False})

                return self._create_response({"message": "Logout successful"})

            except Exception as e:
                _logger.error(f"Logout token verification error: {str(e)}")
                # Even if token is invalid, return success for logout
                return self._create_response({"message": "Logout successful"})

        except Exception as e:
            _logger.error(f"Logout error: {str(e)}")
            return self._create_response(error="Logout failed", status=500)

    @http.route(
        "/mobile/health", auth="public", methods=["GET"], type="http", csrf=False
    )
    def health_check(self):
        """Health check endpoint"""
        response_data = {
            "status": "healthy",
            "service": "Yellow Mobile API",
            "version": "1.0.0",
            "timestamp": fields.Datetime.now().isoformat(),
        }

        return request.make_response(
            json.dumps(response_data), headers={"Content-Type": "application/json"}
        )
