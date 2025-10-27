# Parameter Ordering Fix for FastAPI Routers

## Issue

Python requires that parameters without default values must come before parameters with default values in function definitions. The mobile_api routers had several functions where `env: Annotated[Environment, Depends(odoo_env)]` (which has no default) was placed after parameters with defaults like `Query(...)`.

## Error

```
SyntaxError: parameter without a default follows parameter with a default
```

## Files Fixed

### 1. `routers/mobile_product_router.py` (6 functions fixed)

**Before:**
```python
async def search_products(
    q: str = Query(..., min_length=2),  # Has default
    env: Annotated[Environment, Depends(odoo_env)],  # No default - ERROR!
    current_user: Annotated[Partner, Depends(get_optional_user)] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
```

**After:**
```python
async def search_products(
    env: Annotated[Environment, Depends(odoo_env)],  # No default first
    q: str = Query(..., min_length=2),
    current_user: Annotated[Partner, Depends(get_optional_user)] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
```

**Functions fixed:**
- `search_products`
- `get_product_detail`
- `get_product_by_barcode`
- `add_to_wishlist`
- `remove_from_wishlist`
- `check_wishlist_item`

### 2. `routers/mobile_wallet_router.py` (2 functions fixed)

**Functions fixed:**
- `topup_wallet`
- `transfer_funds`

### 3. `routers/mobile_notification_router.py` (3 functions fixed)

**Functions fixed:**
- `mark_notification_read`
- `register_push_token`
- `delete_notification`

### 4. `routers/mobile_auth_router.py` (5 functions fixed)

**Functions fixed:**
- `register`
- `login`
- `firebase_sms_auth`
- `social_login`
- `refresh_token`

## Pattern Applied

**Standard FastAPI Router Parameter Order:**
1. `env: Annotated[Environment, Depends(odoo_env)]` (no default)
2. Path parameters (no defaults)
3. Request body parameters (no defaults)
4. Query parameters with defaults
5. Dependency parameters with defaults

## Example Template

```python
@router.get("/endpoint")
async def endpoint_function(
    env: Annotated[Environment, Depends(odoo_env)],  # 1. Environment first
    path_param: int,  # 2. Path parameters
    body_data: RequestModel,  # 3. Request body
    query_param: str = Query("default"),  # 4. Query parameters with defaults
    current_user: Annotated[Partner, Depends(get_current_user)] = None  # 5. Dependencies
):
    """Function implementation"""
    pass
```

## Total Functions Fixed

**16 functions** across 4 router files

## Testing

After applying these fixes, the module should load without syntax errors:

```bash
# Update the module
odoo-bin -d your_database -u mobile_api

# Test endpoint access
curl http://your-domain/mobile/health
```

## Python Parameter Rules

1. **Positional arguments** (no defaults) must come first
2. **Keyword arguments** (with defaults) must come after
3. **FastAPI dependencies** without defaults are treated as positional
4. **Query parameters** with defaults are keyword arguments

## References

- [Python Function Arguments](https://docs.python.org/3/tutorial/controlflow.html#more-on-defining-functions)
- [FastAPI Dependencies](https://fastapi.tiangolo.com/tutorial/dependencies/)

---

**Fixed:** October 27, 2025  
**Version:** 1.0.0
