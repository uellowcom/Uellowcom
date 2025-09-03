# -*- coding: utf-8 -*-
"""Mobile Wallet Router using Odoo models"""

from typing import Annotated, List
import logging
from decimal import Decimal

from odoo.api import Environment
from odoo.addons.fastapi.dependencies import odoo_env
from odoo.addons.base.models.res_partner import Partner

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from ..dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mobile/v1/wallet", tags=["Mobile Wallet"])


# Pydantic Models
class WalletBalance(BaseModel):
    balance: float
    currency: str
    formatted_balance: str


class TopupRequest(BaseModel):
    amount: float = Field(..., gt=0)
    payment_method: str
    reference: str = None


class TransferRequest(BaseModel):
    recipient: str  # email or phone
    amount: float = Field(..., gt=0)
    note: str = None


class TransactionResponse(BaseModel):
    id: int
    amount: float
    type: str
    description: str
    reference: str = None
    payment_method: str = None
    status: str
    date: str
    processed_date: str = None


@router.get("/balance", response_model=WalletBalance)
async def get_wallet_balance(
    env: Annotated[Environment, Depends(odoo_env)],
    current_user: Annotated[Partner, Depends(get_current_user)]
):
    """Get current wallet balance"""
    try:
        balance_data = current_user.get_wallet_balance()
        return WalletBalance(**balance_data)
        
    except Exception as e:
        logger.error(f"Error fetching wallet balance: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch wallet balance")


@router.get("/transactions", response_model=List[TransactionResponse])
async def get_transaction_history(
    env: Annotated[Environment, Depends(odoo_env)],
    current_user: Annotated[Partner, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    transaction_type: str = Query(None, regex="^(credit|debit)$")
):
    """Get wallet transaction history"""
    try:
        transactions = env['mobile.wallet.transaction'].get_transaction_history(
            partner_id=current_user.id,
            limit=limit,
            transaction_type=transaction_type
        )
        
        return [TransactionResponse(**txn) for txn in transactions]
        
    except Exception as e:
        logger.error(f"Error fetching transaction history: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch transaction history")


@router.post("/topup")
async def topup_wallet(
    topup_data: TopupRequest,
    env: Annotated[Environment, Depends(odoo_env)],
    current_user: Annotated[Partner, Depends(get_current_user)]
):
    """Top up wallet balance"""
    try:
        result = current_user.topup_wallet(
            amount=topup_data.amount,
            payment_method=topup_data.payment_method,
            reference=topup_data.reference
        )
        
        return {
            "message": "Wallet topped up successfully",
            "transaction_id": result['transaction_id'],
            "new_balance": result['new_balance'],
            "status": result['status']
        }
        
    except Exception as e:
        logger.error(f"Error topping up wallet: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/transfer")
async def transfer_funds(
    transfer_data: TransferRequest,
    env: Annotated[Environment, Depends(odoo_env)],
    current_user: Annotated[Partner, Depends(get_current_user)]
):
    """Transfer funds to another user"""
    try:
        result = current_user.transfer_wallet_funds(
            recipient_identifier=transfer_data.recipient,
            amount=transfer_data.amount,
            note=transfer_data.note
        )
        
        return {
            "message": "Transfer completed successfully",
            "transaction_ids": result['transaction_ids'],
            "sender_new_balance": result['sender_new_balance'],
            "recipient": result['recipient']
        }
        
    except Exception as e:
        logger.error(f"Error transferring funds: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/stats")
async def get_wallet_stats(
    env: Annotated[Environment, Depends(odoo_env)],
    current_user: Annotated[Partner, Depends(get_current_user)]
):
    """Get wallet statistics"""
    try:
        # Get transaction counts and totals
        transactions = env['mobile.wallet.transaction'].search([
            ('partner_id', '=', current_user.id)
        ])
        
        total_credits = sum(txn.amount for txn in transactions if txn.transaction_type == 'credit')
        total_debits = sum(abs(txn.amount) for txn in transactions if txn.transaction_type == 'debit')
        
        return {
            "current_balance": current_user.wallet_balance,
            "total_credits": total_credits,
            "total_debits": total_debits,
            "transaction_count": len(transactions),
            "currency": env.company.currency_id.name
        }
        
    except Exception as e:
        logger.error(f"Error fetching wallet stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch wallet statistics")
