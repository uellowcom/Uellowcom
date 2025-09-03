# -*- coding: utf-8 -*-
"""Order and checkout endpoints for Mobile API"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List, Optional, Dict, Any

from ....schemas.order_schemas import (
    OrderResponse, OrderDetail, CheckoutData,
    PlaceOrderRequest, PlaceOrderResponse,
    ApplyCouponRequest, ApplyCouponResponse
)
from ....services.order_service import OrderService
from ....core.security import get_current_user

router = APIRouter(tags=["Orders & Checkout"])
order_service = OrderService()


@router.get("/orders", response_model=List[OrderResponse])
async def get_user_orders(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    status: Optional[str] = None,
    current_user: Dict = Depends(get_current_user)
):
    """Get list of user's orders with pagination"""
    orders = await order_service.get_user_orders(
        user_id=current_user["user_id"],
        page=page,
        limit=limit,
        status=status
    )
    return orders


@router.get("/orders/{order_id}", response_model=OrderDetail)
async def get_order_detail(
    order_id: int,
    current_user: Dict = Depends(get_current_user)
):
    """Get detailed order information"""
    order = await order_service.get_order_detail(order_id)
    
    # Verify order belongs to user
    if order["user_id"] != current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return order


@router.get("/checkout/data", response_model=CheckoutData)
async def get_checkout_data(current_user: Dict = Depends(get_current_user)):
    """Get checkout data including cart, addresses, payment methods"""
    checkout_data = await order_service.get_checkout_data(current_user["user_id"])
    return checkout_data


@router.post("/checkout/place-order", response_model=PlaceOrderResponse)
async def place_order(
    order_data: PlaceOrderRequest,
    current_user: Dict = Depends(get_current_user)
):
    """Place a new order"""
    try:
        order = await order_service.place_order(
            user_id=current_user["user_id"],
            order_data=order_data
        )
        return order
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/checkout/apply-coupon", response_model=ApplyCouponResponse)
async def apply_coupon(
    coupon_data: ApplyCouponRequest,
    current_user: Dict = Depends(get_current_user)
):
    """Apply coupon code to checkout"""
    try:
        result = await order_service.apply_coupon(
            user_id=current_user["user_id"],
            coupon_code=coupon_data.coupon_code,
            cart_total=coupon_data.cart_total
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/orders/{order_id}/cancel")
async def cancel_order(
    order_id: int,
    reason: Optional[str] = None,
    current_user: Dict = Depends(get_current_user)
):
    """Cancel an order"""
    order = await order_service.get_order_detail(order_id)
    
    # Verify order belongs to user
    if order["user_id"] != current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Check if order can be cancelled
    if order["status"] not in ["pending", "processing"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order cannot be cancelled in current status"
        )
    
    await order_service.cancel_order(order_id, reason)
    return {"message": "Order cancelled successfully"}


@router.get("/orders/{order_id}/track")
async def track_order(
    order_id: int,
    current_user: Dict = Depends(get_current_user)
):
    """Get order tracking information"""
    tracking = await order_service.get_order_tracking(order_id)
    
    # Verify order belongs to user
    if tracking["user_id"] != current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return tracking
