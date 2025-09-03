# -*- coding: utf-8 -*-
"""JWT Token Service for Mobile API authentication"""

import jwt
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import logging
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


class JWTService:
    """JWT Token Management Service"""
    
    def __init__(self, env=None):
        # Get configuration from Odoo system parameters
        if env is None:
            # Create a temporary environment to get config
            from odoo import registry
            import threading
            db_name = threading.current_thread().dbname if hasattr(threading.current_thread(), 'dbname') else 'postgres'
            try:
                with registry(db_name).cursor() as cr:
                    env = api.Environment(cr, SUPERUSER_ID, {})
                    self._load_config(env)
            except:
                # Fallback to defaults if can't access database
                self._load_defaults()
        else:
            self._load_config(env)
    
    def _load_config(self, env):
        """Load configuration from Odoo system parameters"""
        config = env['ir.config_parameter'].sudo()
        self.secret_key = config.get_param('mobile_api.jwt.secret_key', 'your-secret-key-change-in-production')
        self.algorithm = config.get_param('mobile_api.jwt.algorithm', 'HS256')
        self.access_token_expire_minutes = int(config.get_param('mobile_api.jwt.access_token_expire_minutes', '30'))
        self.refresh_token_expire_days = int(config.get_param('mobile_api.jwt.refresh_token_expire_days', '7'))
    
    def _load_defaults(self):
        """Load default configuration when database is not accessible"""
        self.secret_key = 'your-secret-key-change-in-production'
        self.algorithm = 'HS256'
        self.access_token_expire_minutes = 30
        self.refresh_token_expire_days = 7
    
    def create_access_token(self, user_id: int, additional_claims: Dict = None) -> str:
        """Create JWT access token"""
        now = datetime.utcnow()
        expire = now + timedelta(minutes=self.access_token_expire_minutes)
        
        payload = {
            'sub': str(user_id),
            'email': email,
            'iat': now,
            'exp': expire,
            'type': 'access'
        }
        
        if additional_claims:
            payload.update(additional_claims)
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def create_refresh_token(self, user_id: int, email: str) -> str:
        """Create JWT refresh token"""
        now = datetime.utcnow()
        expire = now + timedelta(days=self.refresh_token_expire_days)
        
        payload = {
            'sub': str(user_id),
            'email': email,
            'iat': now,
            'exp': expire,
            'type': 'refresh'
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def create_tokens(self, user_id: int, email: str, additional_claims: Dict = None) -> Dict[str, Any]:
        """Create both access and refresh tokens"""
        access_token = self.create_access_token(user_id, email, additional_claims)
        refresh_token = self.create_refresh_token(user_id, email)
        
        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'token_type': 'Bearer',
            'expires_in': self.access_token_expire_minutes * 60
        }
    
    def decode_token(self, token: str) -> Dict[str, Any]:
        """Decode and validate JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError:
            raise ValueError("Invalid token")
    
    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Create new access token from refresh token"""
        try:
            payload = self.decode_token(refresh_token)
            
            if payload.get('type') != 'refresh':
                raise ValueError("Invalid token type")
            
            user_id = int(payload.get('sub'))
            email = payload.get('email')
            
            # Create new access token
            access_token = self.create_access_token(user_id, email)
            
            return {
                'access_token': access_token,
                'token_type': 'Bearer',
                'expires_in': self.access_token_expire_minutes * 60
            }
            
        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            raise ValueError("Invalid refresh token")
    
    def verify_token(self, token: str, token_type: str = 'access') -> Dict[str, Any]:
        """Verify token and return payload"""
        payload = self.decode_token(token)
        
        if payload.get('type') != token_type:
            raise ValueError(f"Expected {token_type} token")
        
        return payload
