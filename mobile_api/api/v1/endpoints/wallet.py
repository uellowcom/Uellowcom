# -*- coding: utf-8 -*-
"""Wallet endpoints for Mobile API"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List, Dict, Any
from decimal import Decimal

from ....schemas.wallet_schemas import (
    WalletBalance, TopupRequest, TopupResponse,
    TransferRequest, TransferResponse, TransactionHistory
)
from ....services.wallet_service import WalletService
from ....core.security import get_current_user

router = APIRouter(prefix="/wallet", tags=["Wallet"])
wallet_service = WalletService()


@router.get("/balance", response_model=WalletBalance)
async def get_wallet_balance(current_user: Dict = Depends(get_current_user)):
    """Get current wallet balance"""
    balance = await wallet_service.get_balance(current_user["user_id"])
    return balance


@router.get("/transactions", response_model=List[TransactionHistory])
async def get_transaction_history(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    transaction_type: Optional[str] = None,
    current_user: Dict = Depends(get_current_user)
):
    """Get wallet transaction history"""
    transactions = await wallet_service.get_transactions(
        user_id=current_user["user_id"],
        page=page,
        limit=limit,
        transaction_type=transaction_type
    )
    return transactions


@router.post("/topup", response_model=TopupResponse)
async def topup_wallet(
    topup_data: TopupRequest,
    current_user: Dict = Depends(get_current_user)
):
    """Top up wallet balance"""
    try:
        result = await wallet_service.topup_wallet(
            user_id=current_user["user_id"],
            amount=topup_data.amount,
            payment_method=topup_data.payment_method,
            payment_reference=topup_data.payment_reference
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/transfer", response_model=TransferResponse)
async def transfer_funds(
    transfer_data: TransferRequest,
    current_user: Dict = Depends(get_current_user)
):
    """Transfer funds to another user"""
    try:
        # Check balance
        balance = await wallet_service.get_balance(current_user["user_id"])
        if balance["available_balance"] < transfer_data.amount:
            raise ValueError("Insufficient balance")
        
        result = await wallet_service.transfer_funds(
            from_user_id=current_user["user_id"],
            to_user_identifier=transfer_data.recipient,
            amount=transfer_data.amount,
            note=transfer_data.note
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/withdraw")
async def withdraw_funds(
    amount: Decimal,
    bank_account_id: int,
    current_user: Dict = Depends(get_current_user)
):
    """Withdraw funds from wallet to bank account"""
    try:
        result = await wallet_service.withdraw_funds(
            user_id=current_user["user_id"],
            amount=amount,
            bank_account_id=bank_account_id
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
