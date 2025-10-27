# Pydantic v2 Compatibility Fix

## Issue

The mobile_api module was using Pydantic v1 syntax with `regex=` parameter in Field definitions, which was removed in Pydantic v2 in favor of `pattern=`.

## Error

```
pydantic.errors.PydanticUserError: `regex` is removed. use `pattern` instead
```

## Files Fixed

All instances of `Field(..., regex=...)` were replaced with `Field(..., pattern=...)` in the following files:

### 1. `routers/mobile_auth_router.py`
- `UserLogin.device_type` - Pattern for iOS/Android validation
- `FirebaseSMSAuth.phone_number` - E.164 phone format validation
- `SocialLogin.provider` - Provider validation (google|facebook|apple)

### 2. `schemas/auth_schemas.py`
- `UserRegisterRequest.phone` - E.164 phone format validation
- `UserRegisterRequest.country_code` - ISO country code validation
- `UserRegisterRequest.language` - Language code validation
- `UserRegisterRequest.currency` - Currency code validation
- `FirebaseSMSRequest.phone_number` - E.164 phone format validation
- `PasswordResetRequest.phone` - E.164 phone format validation (2 instances)

### 3. `api/v1/dependencies.py`
- `SortParams.sort_order` - Sort order validation (asc|desc)

### 4. `routers/mobile_wallet_router.py`
- `get_transaction_history.transaction_type` - Transaction type validation (credit|debit)

### 5. `routers/mobile_product_router.py`
- `get_products.sort_by` - Sort field validation
- `get_products.order` - Order direction validation

### 6. `api/v1/endpoints/products.py`
- `get_products.sort_by` - Sort field validation
- `get_products.order` - Order direction validation

## Total Changes

**16 instances** of `regex=` replaced with `pattern=`

## Testing

After applying these fixes, the module should load correctly without Pydantic errors.

Test the fix:
```bash
# Update the module
odoo-bin -d your_database -u mobile_api

# Test endpoint access
curl http://your-domain/mobile/health
```

## Pydantic v2 Migration Notes

Other Pydantic v1 to v2 changes that may be needed in the future:

1. ✅ `regex=` → `pattern=` (DONE)
2. `Config` class → `model_config` dictionary
3. `@validator` → `@field_validator`
4. `@root_validator` → `@model_validator`
5. `.dict()` → `.model_dump()`
6. `.json()` → `.model_dump_json()`
7. `.parse_obj()` → `.model_validate()`
8. `.parse_raw()` → `.model_validate_json()`

Currently, the module appears to use standard Pydantic features that are compatible with both v1 and v2, except for the `regex` parameter which has been fixed.

## References

- [Pydantic v2 Migration Guide](https://docs.pydantic.dev/latest/migration/)
- [Pydantic Field Documentation](https://docs.pydantic.dev/latest/concepts/fields/)

---

**Fixed:** October 27, 2025  
**Version:** 1.0.0

