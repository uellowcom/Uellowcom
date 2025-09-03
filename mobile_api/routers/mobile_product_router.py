# -*- coding: utf-8 -*-
"""Mobile Product Router using Odoo models"""

from typing import Annotated, Optional, List
import logging

from odoo.api import Environment
from odoo.addons.fastapi.dependencies import odoo_env
from odoo.addons.base.models.res_partner import Partner

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from ..dependencies import get_current_user, get_optional_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mobile/v1/products", tags=["Mobile Products"])


# Pydantic Models
class ProductResponse(BaseModel):
    id: int
    name: str
    list_price: float
    currency: str
    image_url: Optional[str]
    in_stock: bool
    stock_quantity: float
    category: str
    brand: Optional[str]
    rating: float
    in_wishlist: bool = False


class ProductDetail(BaseModel):
    id: int
    name: str
    description: Optional[str]
    list_price: float
    currency: str
    images: List[str]
    in_stock: bool
    stock_quantity: float
    sku: Optional[str]
    barcode: Optional[str]
    weight: float
    category: str
    brand: Optional[str]
    rating: float
    review_count: int
    in_wishlist: bool = False
    variants: List[dict]
    tags: List[str]


@router.get("", response_model=List[ProductResponse])
async def get_products(
    env: Annotated[Environment, Depends(odoo_env)],
    current_user: Annotated[Partner, Depends(get_optional_user)] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    category_id: Optional[int] = None,
    search: Optional[str] = None,
    sort_by: Optional[str] = Query("name", regex="^(name|price|rating|created_at)$"),
    order: Optional[str] = Query("asc", regex="^(asc|desc)$")
):
    """Get list of products with pagination and filters"""
    try:
        domain = [('sale_ok', '=', True), ('active', '=', True)]
        
        if category_id:
            domain.append(('categ_id', '=', category_id))
        
        if search:
            domain.extend([
                '|', '|',
                ('name', 'ilike', search),
                ('description_sale', 'ilike', search),
                ('default_code', 'ilike', search)
            ])
        
        # Apply sorting
        order_by = sort_by
        if sort_by == 'price':
            order_by = 'list_price'
        elif sort_by == 'rating':
            order_by = 'rating_avg' if hasattr(env['product.product'], 'rating_avg') else 'name'
        elif sort_by == 'created_at':
            order_by = 'create_date'
        
        if order == 'desc':
            order_by = f'{order_by} desc'
        
        # Calculate offset
        offset = (page - 1) * limit
        
        products = env['product.product'].search(domain, limit=limit, offset=offset, order=order_by)
        
        result = []
        for product in products:
            # Check if in wishlist
            in_wishlist = False
            if current_user:
                in_wishlist = env['mobile.wishlist'].is_in_wishlist(current_user.id, product.id)
            
            result.append(ProductResponse(
                id=product.id,
                name=product.name,
                list_price=product.list_price,
                currency=product.currency_id.name,
                image_url=f'/web/image/product.product/{product.id}/image_1920' if product.image_1920 else None,
                in_stock=product.qty_available > 0,
                stock_quantity=product.qty_available,
                category=product.categ_id.name,
                brand=product.product_brand_id.name if hasattr(product, 'product_brand_id') and product.product_brand_id else None,
                rating=product.rating_avg if hasattr(product, 'rating_avg') else 0,
                in_wishlist=in_wishlist
            ))
        
        return result
        
    except Exception as e:
        logger.error(f"Error fetching products: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch products")


@router.get("/{product_id}", response_model=ProductDetail)
async def get_product_detail(
    product_id: int,
    env: Annotated[Environment, Depends(odoo_env)],
    current_user: Annotated[Partner, Depends(get_optional_user)] = None
):
    """Get detailed product information"""
    try:
        product = env['product.product'].browse(product_id)
        if not product.exists() or not product.active or not product.sale_ok:
            raise HTTPException(status_code=404, detail="Product not found")
        
        # Track view if user is authenticated
        if current_user:
            product.track_mobile_view(current_user.id)
        else:
            product.track_mobile_view()
        
        # Get product images
        images = []
        if product.image_1920:
            images.append(f'/web/image/product.product/{product.id}/image_1920')
        
        # Get variants
        variants = []
        if product.product_template_id.product_variant_count > 1:
            for variant in product.product_template_id.product_variant_ids:
                if variant.active:
                    variants.append({
                        'id': variant.id,
                        'name': variant.display_name,
                        'price': variant.list_price,
                        'attributes': variant.product_template_attribute_value_ids.mapped('name'),
                    })
        
        # Check if in wishlist
        in_wishlist = False
        if current_user:
            in_wishlist = env['mobile.wishlist'].is_in_wishlist(current_user.id, product.id)
        
        return ProductDetail(
            id=product.id,
            name=product.name,
            description=product.description_sale or product.description,
            list_price=product.list_price,
            currency=product.currency_id.name,
            images=images,
            in_stock=product.qty_available > 0,
            stock_quantity=product.qty_available,
            sku=product.default_code,
            barcode=product.barcode,
            weight=product.weight,
            category=product.categ_id.name,
            brand=product.product_brand_id.name if hasattr(product, 'product_brand_id') and product.product_brand_id else None,
            rating=product.rating_avg if hasattr(product, 'rating_avg') else 0,
            review_count=product.rating_count if hasattr(product, 'rating_count') else 0,
            in_wishlist=in_wishlist,
            variants=variants,
            tags=product.tag_ids.mapped('name') if hasattr(product, 'tag_ids') else []
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching product detail: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch product details")


@router.get("/categories/list")
async def get_product_categories(
    env: Annotated[Environment, Depends(odoo_env)]
):
    """Get all product categories"""
    try:
        categories = env['product.category'].search([])
        
        result = []
        for category in categories:
            # Count products in category
            product_count = env['product.product'].search_count([
                ('categ_id', '=', category.id),
                ('sale_ok', '=', True),
                ('active', '=', True)
            ])
            
            result.append({
                'id': category.id,
                'name': category.name,
                'parent_id': category.parent_id.id if category.parent_id else None,
                'parent_name': category.parent_id.name if category.parent_id else None,
                'product_count': product_count,
                'complete_name': category.complete_name,
            })
        
        return result
        
    except Exception as e:
        logger.error(f"Error fetching categories: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch categories")


@router.get("/search")
async def search_products(
    q: str = Query(..., min_length=2),
    env: Annotated[Environment, Depends(odoo_env)],
    current_user: Annotated[Partner, Depends(get_optional_user)] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    """Search products by name, description, or SKU"""
    try:
        domain = [
            ('sale_ok', '=', True),
            ('active', '=', True),
            '|', '|', '|',
            ('name', 'ilike', q),
            ('description_sale', 'ilike', q),
            ('description', 'ilike', q),
            ('default_code', 'ilike', q)
        ]
        
        offset = (page - 1) * limit
        products = env['product.product'].search(domain, limit=limit, offset=offset)
        total_count = env['product.product'].search_count(domain)
        
        result = []
        for product in products:
            in_wishlist = False
            if current_user:
                in_wishlist = env['mobile.wishlist'].is_in_wishlist(current_user.id, product.id)
            
            result.append({
                'id': product.id,
                'name': product.name,
                'list_price': product.list_price,
                'currency': product.currency_id.name,
                'image_url': f'/web/image/product.product/{product.id}/image_1920' if product.image_1920 else None,
                'in_stock': product.qty_available > 0,
                'category': product.categ_id.name,
                'in_wishlist': in_wishlist
            })
        
        return {
            'products': result,
            'total_count': total_count,
            'page': page,
            'limit': limit,
            'has_more': (page * limit) < total_count
        }
        
    except Exception as e:
        logger.error(f"Error searching products: {e}")
        raise HTTPException(status_code=500, detail="Failed to search products")


@router.get("/barcode/{barcode}")
async def get_product_by_barcode(
    barcode: str,
    env: Annotated[Environment, Depends(odoo_env)],
    current_user: Annotated[Partner, Depends(get_optional_user)] = None
):
    """Get product by barcode"""
    try:
        product = env['product.product'].search([
            ('barcode', '=', barcode),
            ('sale_ok', '=', True),
            ('active', '=', True)
        ], limit=1)
        
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        # Use the existing get_mobile_product_data method
        product_data = product.get_mobile_product_data(product.id, current_user.id if current_user else None)
        return product_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching product by barcode: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch product")


# Wishlist endpoints
@router.get("/wishlist", response_model=List[dict])
async def get_wishlist(
    env: Annotated[Environment, Depends(odoo_env)],
    current_user: Annotated[Partner, Depends(get_current_user)]
):
    """Get user's wishlist"""
    try:
        wishlist_items = env['mobile.wishlist'].get_wishlist(current_user.id)
        return wishlist_items
        
    except Exception as e:
        logger.error(f"Error fetching wishlist: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch wishlist")


@router.post("/wishlist/add")
async def add_to_wishlist(
    product_id: int,
    env: Annotated[Environment, Depends(odoo_env)],
    current_user: Annotated[Partner, Depends(get_current_user)]
):
    """Add product to wishlist"""
    try:
        env['mobile.wishlist'].add_to_wishlist(current_user.id, product_id)
        return {"message": "Product added to wishlist"}
        
    except Exception as e:
        logger.error(f"Error adding to wishlist: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/wishlist/remove")
async def remove_from_wishlist(
    product_id: int,
    env: Annotated[Environment, Depends(odoo_env)],
    current_user: Annotated[Partner, Depends(get_current_user)]
):
    """Remove product from wishlist"""
    try:
        env['mobile.wishlist'].remove_from_wishlist(current_user.id, product_id)
        return {"message": "Product removed from wishlist"}
        
    except Exception as e:
        logger.error(f"Error removing from wishlist: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/wishlist/check")
async def check_wishlist_item(
    product_id: int,
    env: Annotated[Environment, Depends(odoo_env)],
    current_user: Annotated[Partner, Depends(get_current_user)]
):
    """Check if product is in wishlist"""
    try:
        in_wishlist = env['mobile.wishlist'].is_in_wishlist(current_user.id, product_id)
        return {"product_id": product_id, "in_wishlist": in_wishlist}
        
    except Exception as e:
        logger.error(f"Error checking wishlist: {e}")
        raise HTTPException(status_code=500, detail="Failed to check wishlist")


@router.get("/recent-viewed")
async def get_recent_viewed_products(
    env: Annotated[Environment, Depends(odoo_env)],
    current_user: Annotated[Partner, Depends(get_current_user)],
    limit: int = Query(10, ge=1, le=20)
):
    """Get recently viewed products"""
    try:
        recent_products = env['mobile.product.view'].get_recent_viewed(current_user.id, limit)
        return recent_products
        
    except Exception as e:
        logger.error(f"Error fetching recent viewed products: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch recent products")
