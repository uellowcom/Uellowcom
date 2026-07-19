# -*- coding: utf-8 -*-
"""Mobile Wallet Controller using Odoo HTTP"""

import json
import logging
from datetime import datetime

from odoo import http, fields
from odoo.http import request
from odoo.exceptions import ValidationError, UserError

from ..services.jwt_service import JWTService

_logger = logging.getLogger(__name__)


class MobileWalletController(http.Controller):
    """Mobile Wallet HTTP Controller"""

    def _get_current_user(self):
        """Get current authenticated user from JWT token"""
        try:
            auth_header = request.httprequest.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                return None

            token = auth_header.split(' ')[1]
            jwt_service = JWTService()
            payload = jwt_service.decode_token(token)
            partner_id = payload.get('sub')
            
            if partner_id:
                partner = request.env['res.partner'].sudo().browse(int(partner_id))
                return partner if partner.exists() else None
            return None
        except:
            return None

    def _create_response(self, data=None, error=None, status=200):
        """Create standardized JSON response"""
        if error:
            response_data = {
                'success': False,
                'error': error,
                'data': None
            }
            status = status or 400
        else:
            response_data = {
                'success': True,
                'error': None,
                'data': data or {}
            }
        
        return request.make_response(
            json.dumps(response_data),
            headers={'Content-Type': 'application/json'},
            status=status
        )

    def _get_wallet_balance(self, partner):
        """Get current wallet balance for partner"""
        # Calculate balance from transactions
        credit_total = sum(
            request.env['mobile.wallet.transaction'].sudo().search([
                ('partner_id', '=', partner.id),
                ('transaction_type', '=', 'credit'),
                ('status', '=', 'completed')
            ]).mapped('amount')
        )
        
        debit_total = sum(
            request.env['mobile.wallet.transaction'].sudo().search([
                ('partner_id', '=', partner.id),
                ('transaction_type', '=', 'debit'),
                ('status', '=', 'completed')
            ]).mapped('amount')
        )
        
        return credit_total - debit_total

    @http.route('/mobile/v1/wallet/balance', auth='public', methods=['GET'], type='http', csrf=False)
    def get_wallet_balance(self):
        """Get user's wallet balance"""
        try:
            current_user = self._get_current_user()
            if not current_user:
                return self._create_response(error="Authentication required", status=401)

            balance = self._get_wallet_balance(current_user)
            
            # Get currency
            currency = request.env.user.company_id.currency_id

            response_data = {
                'balance': balance,
                'currency': currency.name,
                'currency_symbol': currency.symbol,
                'formatted_balance': f"{currency.symbol}{balance:.2f}"
            }

            return self._create_response(response_data)

        except Exception as e:
            _logger.error(f"Get wallet balance error: {str(e)}")
            return self._create_response(error="Failed to fetch wallet balance", status=500)

    @http.route('/mobile/v1/wallet/transactions', auth='public', methods=['GET'], type='http', csrf=False)
    def get_wallet_transactions(self, **kwargs):
        """Get user's wallet transaction history"""
        try:
            current_user = self._get_current_user()
            if not current_user:
                return self._create_response(error="Authentication required", status=401)

            # Extract pagination parameters
            limit = int(kwargs.get('limit', 20))
            offset = int(kwargs.get('offset', 0))
            transaction_type = kwargs.get('type')  # credit, debit

            # Build domain
            domain = [('partner_id', '=', current_user.id)]
            if transaction_type and transaction_type in ['credit', 'debit']:
                domain.append(('transaction_type', '=', transaction_type))

            # Get transactions
            transactions = request.env['mobile.wallet.transaction'].sudo().search(
                domain,
                limit=limit,
                offset=offset,
                order='create_date desc'
            )

            transactions_data = []
            for transaction in transactions:
                transactions_data.append({
                    'id': transaction.id,
                    'amount': transaction.amount,
                    'transaction_type': transaction.transaction_type,
                    'description': transaction.description,
                    'status': transaction.status,
                    'reference': transaction.reference,
                    'created_at': transaction.create_date.isoformat() if transaction.create_date else None,
                    'currency': transaction.currency_id.name if transaction.currency_id else 'USD'
                })

            # Get total count
            total_count = request.env['mobile.wallet.transaction'].sudo().search_count(domain)

            response_data = {
                'transactions': transactions_data,
                'pagination': {
                    'total': total_count,
                    'limit': limit,
                    'offset': offset,
                    'has_more': offset + limit < total_count
                }
            }

            return self._create_response(response_data)

        except Exception as e:
            _logger.error(f"Get wallet transactions error: {str(e)}")
            return self._create_response(error="Failed to fetch transactions", status=500)

    @http.route('/mobile/v1/wallet/add-money', auth='public', methods=['POST'], type='json', csrf=False)
    def add_money(self):
        """Add money to wallet"""
        try:
            current_user = self._get_current_user()
            if not current_user:
                return self._create_response(error="Authentication required", status=401)

            data = request.jsonrequest
            
            # Validate required fields
            if not data.get('amount'):
                return self._create_response(error="Amount is required", status=400)

            amount = float(data['amount'])
            if amount <= 0:
                return self._create_response(error="Amount must be greater than 0", status=400)

            payment_method = data.get('payment_method', 'card')
            description = data.get('description', 'Wallet top-up')

            # Create wallet transaction
            transaction_vals = {
                'partner_id': current_user.id,
                'amount': amount,
                'transaction_type': 'credit',
                'description': description,
                'status': 'pending',
                'payment_method': payment_method,
                'reference': f"TOPUP-{current_user.id}-{int(datetime.now().timestamp())}"
            }
            
            transaction = request.env['mobile.wallet.transaction'].sudo().create(transaction_vals)

            # In a real implementation, you would integrate with payment gateway here
            # For now, we'll simulate successful payment
            transaction.sudo().write({'status': 'completed'})

            # Get updated balance
            new_balance = self._get_wallet_balance(current_user)

            response_data = {
                'transaction_id': transaction.id,
                'amount_added': amount,
                'new_balance': new_balance,
                'status': 'completed',
                'message': 'Money added successfully to wallet'
            }

            return self._create_response(response_data)

        except Exception as e:
            _logger.error(f"Add money error: {str(e)}")
            return self._create_response(error="Failed to add money to wallet", status=500)

    @http.route('/mobile/v1/wallet/send-money', auth='public', methods=['POST'], type='json', csrf=False)
    def send_money(self):
        """Send money to another user"""
        try:
            current_user = self._get_current_user()
            if not current_user:
                return self._create_response(error="Authentication required", status=401)

            data = request.jsonrequest
            
            # Validate required fields
            required_fields = ['recipient_email', 'amount']
            missing_fields = [field for field in required_fields if not data.get(field)]
            if missing_fields:
                return self._create_response(error=f"Missing fields: {', '.join(missing_fields)}", status=400)

            amount = float(data['amount'])
            if amount <= 0:
                return self._create_response(error="Amount must be greater than 0", status=400)

            # Check if sender has sufficient balance
            sender_balance = self._get_wallet_balance(current_user)
            if sender_balance < amount:
                return self._create_response(error="Insufficient wallet balance", status=400)

            # Find recipient
            recipient = request.env['res.partner'].sudo().search([
                ('email', '=', data['recipient_email'])
            ], limit=1)
            
            if not recipient:
                return self._create_response(error="Recipient not found", status=404)

            if recipient.id == current_user.id:
                return self._create_response(error="Cannot send money to yourself", status=400)

            description = data.get('description', f'Money transfer from {current_user.name}')

            # Create debit transaction for sender
            debit_transaction = request.env['mobile.wallet.transaction'].sudo().create({
                'partner_id': current_user.id,
                'amount': amount,
                'transaction_type': 'debit',
                'description': f"Money sent to {recipient.name}",
                'status': 'completed',
                'reference': f"SEND-{current_user.id}-{int(datetime.now().timestamp())}"
            })

            # Create credit transaction for recipient
            credit_transaction = request.env['mobile.wallet.transaction'].sudo().create({
                'partner_id': recipient.id,
                'amount': amount,
                'transaction_type': 'credit',
                'description': f"Money received from {current_user.name}",
                'status': 'completed',
                'reference': f"RECV-{recipient.id}-{int(datetime.now().timestamp())}"
            })

            # Get updated balance
            new_balance = self._get_wallet_balance(current_user)

            response_data = {
                'transaction_id': debit_transaction.id,
                'amount_sent': amount,
                'recipient_name': recipient.name,
                'new_balance': new_balance,
                'message': f'Successfully sent {amount} to {recipient.name}'
            }

            return self._create_response(response_data)

        except Exception as e:
            _logger.error(f"Send money error: {str(e)}")
            return self._create_response(error="Failed to send money", status=500)

    @http.route('/mobile/v1/wallet/transaction/<int:transaction_id>', auth='public', methods=['GET'], type='http', csrf=False)
    def get_transaction_detail(self, transaction_id):
        """Get detailed information about a specific transaction"""
        try:
            current_user = self._get_current_user()
            if not current_user:
                return self._create_response(error="Authentication required", status=401)

            # Find transaction
            transaction = request.env['mobile.wallet.transaction'].sudo().search([
                ('id', '=', transaction_id),
                ('partner_id', '=', current_user.id)
            ], limit=1)

            if not transaction:
                return self._create_response(error="Transaction not found", status=404)

            transaction_data = {
                'id': transaction.id,
                'amount': transaction.amount,
                'transaction_type': transaction.transaction_type,
                'description': transaction.description,
                'status': transaction.status,
                'reference': transaction.reference,
                'payment_method': transaction.payment_method,
                'created_at': transaction.create_date.isoformat() if transaction.create_date else None,
                'currency': transaction.currency_id.name if transaction.currency_id else 'USD'
            }

            return self._create_response(transaction_data)

        except Exception as e:
            _logger.error(f"Get transaction detail error: {str(e)}")
            return self._create_response(error="Failed to fetch transaction details", status=500)
