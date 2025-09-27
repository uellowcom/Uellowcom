# -*- coding: utf-8 -*-
from typing import Annotated, Dict, Any, List, Optional
from datetime import datetime

from odoo.api import Environment

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel

from ..dependencies import odoo_env, get_current_user, get_authenticated_partner_env

# Define the router
router = APIRouter(prefix="/mobile/v1/wallet", tags=["wallet"])


# Models for response
class WalletTransaction(BaseModel):
    id: int
    date: datetime
    amount: float
    currency_symbol: str
    transaction_type: str
    reference: Optional[str] = None
    status: str


class Wallet(BaseModel):
    balance: float
    currency_symbol: str
    transactions: List[WalletTransaction] = []


class ApiResponse(BaseModel):
    success: bool = True
    error: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


@router.get("", response_model=ApiResponse)
async def get_wallet(
    env: Annotated[Environment, Depends(get_authenticated_partner_env)],
    current_user: Annotated[Dict[str, Any], Depends(get_current_user)],
):
    """Get wallet balance and transactions"""
    try:
        # Get partner from current user
        partner_id = current_user.get("partner_id")
        if not partner_id:
            return {"success": False, "error": "User has no associated partner"}

        partner = env["res.partner"].browse(partner_id)
        if not partner.exists():
            return {"success": False, "error": "Partner not found"}

        # Get wallet balance
        balance = 0.0
        currency_symbol = env.company.currency_id.symbol

        # Check if loyalty module is installed
        if "loyalty.card" in env:
            # Get loyalty cards for the partner
            loyalty_cards = (
                env["loyalty.card"].sudo().search([("partner_id", "=", partner_id)])
            )

            for card in loyalty_cards:
                # Add points as balance (convert to currency if needed)
                balance += card.points

        # Check if account module is installed for credit/debit tracking
        transactions = []
        if "account.move.line" in env:
            # Get account move lines for the partner
            move_lines = (
                env["account.move.line"]
                .sudo()
                .search([("partner_id", "=", partner_id)], limit=50, order="date desc")
            )

            for line in move_lines:
                transaction_type = "debit" if line.debit > 0 else "credit"
                amount = line.debit if line.debit > 0 else line.credit

                transactions.append(
                    {
                        "id": line.id,
                        "date": line.date,
                        "amount": amount,
                        "currency_symbol": line.currency_id.symbol or currency_symbol,
                        "transaction_type": transaction_type,
                        "reference": line.name or line.move_id.name,
                        "status": (
                            "posted" if line.move_id.state == "posted" else "draft"
                        ),
                    }
                )

        return {
            "success": True,
            "data": {
                "wallet": {
                    "balance": balance,
                    "currency_symbol": currency_symbol,
                    "transactions": transactions,
                }
            },
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/add-funds", response_model=ApiResponse)
async def add_funds(
    env: Annotated[Environment, Depends(get_authenticated_partner_env)],
    current_user: Annotated[Dict[str, Any], Depends(get_current_user)],
    amount: float,
):
    """Add funds to wallet (placeholder for payment integration)"""
    try:
        # Get partner from current user
        partner_id = current_user.get("partner_id")
        if not partner_id:
            return {"success": False, "error": "User has no associated partner"}

        partner = env["res.partner"].browse(partner_id)
        if not partner.exists():
            return {"success": False, "error": "Partner not found"}

        # This is a placeholder for actual payment processing
        # In a real implementation, this would integrate with a payment gateway

        # For now, just return success message
        return {
            "success": True,
            "data": {
                "message": f"Added {amount} to wallet (simulated)",
                "transaction_id": "sim_123456789",
            },
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/redeem-points", response_model=ApiResponse)
async def redeem_points(
    env: Annotated[Environment, Depends(get_authenticated_partner_env)],
    current_user: Annotated[Dict[str, Any], Depends(get_current_user)],
    points: int,
    program_id: Optional[int] = None,
):
    """Redeem loyalty points"""
    try:
        # Get partner from current user
        partner_id = current_user.get("partner_id")
        if not partner_id:
            return {"success": False, "error": "User has no associated partner"}

        # Check if loyalty module is installed
        if "loyalty.card" not in env:
            return {"success": False, "error": "Loyalty program not available"}

        # Get loyalty cards for the partner
        domain = [("partner_id", "=", partner_id)]
        if program_id:
            domain.append(("program_id", "=", program_id))

        loyalty_cards = env["loyalty.card"].sudo().search(domain)

        if not loyalty_cards:
            return {"success": False, "error": "No loyalty card found"}

        # Use the first card (or the one matching program_id)
        card = loyalty_cards[0]

        # Check if enough points
        if card.points < points:
            return {"success": False, "error": "Not enough points"}

        # Create a reward record (simplified)
        # In a real implementation, this would create a coupon or apply a discount
        reward = (
            env["loyalty.reward"]
            .sudo()
            .search([("program_id", "=", card.program_id.id)], limit=1)
        )

        if not reward:
            return {"success": False, "error": "No rewards available in this program"}

        # Deduct points (simplified)
        card.sudo().write({"points": card.points - points})

        return {
            "success": True,
            "data": {
                "message": f"Redeemed {points} points successfully",
                "remaining_points": card.points,
            },
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/transactions", response_model=ApiResponse)
async def get_wallet_transactions(
    env: Annotated[Environment, Depends(get_authenticated_partner_env)],
    current_user: Annotated[Dict[str, Any], Depends(get_current_user)],
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """Get wallet transactions with pagination"""
    try:
        # Get partner from current user
        partner_id = current_user.get("partner_id")
        if not partner_id:
            return {"success": False, "error": "User has no associated partner"}

        partner = env["res.partner"].browse(partner_id)
        if not partner.exists():
            return {"success": False, "error": "Partner not found"}

        transactions = []
        currency_symbol = env.company.currency_id.symbol

        # Check if account module is installed for credit/debit tracking
        if "account.move.line" in env:
            # Get account move lines for the partner with pagination
            move_lines = (
                env["account.move.line"]
                .sudo()
                .search(
                    [("partner_id", "=", partner_id)],
                    limit=limit,
                    offset=offset,
                    order="date desc",
                )
            )

            for line in move_lines:
                transaction_type = "debit" if line.debit > 0 else "credit"
                amount = line.debit if line.debit > 0 else line.credit

                transactions.append(
                    {
                        "id": line.id,
                        "date": line.date,
                        "amount": amount,
                        "currency_symbol": line.currency_id.symbol or currency_symbol,
                        "transaction_type": transaction_type,
                        "reference": line.name or line.move_id.name,
                        "status": (
                            "posted" if line.move_id.state == "posted" else "draft"
                        ),
                    }
                )

        # Check if loyalty module is installed
        if "loyalty.point" in env:
            # Get loyalty points history
            loyalty_points = (
                env["loyalty.point"]
                .sudo()
                .search(
                    [("partner_id", "=", partner_id)],
                    limit=limit,
                    offset=offset,
                    order="create_date desc",
                )
            )

            for point in loyalty_points:
                transactions.append(
                    {
                        "id": point.id,
                        "date": point.create_date,
                        "amount": point.points,
                        "currency_symbol": "pts",  # Points symbol
                        "transaction_type": "credit" if point.points > 0 else "debit",
                        "reference": f"Loyalty Program: {point.program_id.name}",
                        "status": "completed",
                    }
                )

        # Sort transactions by date (most recent first)
        transactions.sort(key=lambda x: x["date"], reverse=True)

        # Apply pagination manually if we have mixed sources
        if "loyalty.point" in env and "account.move.line" in env:
            transactions = transactions[offset : offset + limit]

        return {
            "success": True,
            "data": {"transactions": transactions, "count": len(transactions)},
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
