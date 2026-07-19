# FastAPI Endpoint Setup for Mobile API

## Overview

The Mobile API module is now properly configured as a FastAPI endpoint in Odoo. This document explains the setup and how to use it.

## Configuration Structure

### 1. FastAPI Endpoint Model (`models/fastapi_endpoint.py`)

The module extends the `fastapi.endpoint` model to register the "mobile_api" app:

```python
class FastapiEndpoint(models.Model):
    _inherit = "fastapi.endpoint"

    app: str = fields.Selection(
        selection_add=[("mobile_api", "Mobile API")], 
        ondelete={"mobile_api": "cascade"}
    )

    def _get_fastapi_routers(self):
        if self.app == "mobile_api":
            return [
                mobile_auth_router.router,
                mobile_home_router.router,
                mobile_product_router.router,
                mobile_wallet_router.router,
                mobile_notification_router.router,
            ]
        return super()._get_fastapi_routers()
```

### 2. XML Data Configuration (`data/fastapi_endpoint.xml`)

The XML file defines:
- **FastAPI Endpoint Record**: Registers the app at `/mobile` path
- **JWT Configuration**: Secret key, algorithm, token expiration
- **App Configuration**: Name, version, support contact
- **Feature Flags**: Enable/disable features (wallet, reviews, wishlist, notifications)

## Installation

### Step 1: Update Module

```bash
# Restart Odoo and update the module
odoo-bin -d your_database -u mobile_api
```

### Step 2: Verify Endpoint Registration

After installation, go to:
**FastAPI > Endpoints** in Odoo backend

You should see:
- **Name**: Mobile API v1
- **App**: mobile_api
- **Root Path**: /mobile
- **User**: Administrator

### Step 3: Sync Registry

Click the **"Sync Registry"** button on the endpoint record to register all routes.

## Accessing the API

### Base URL Structure

```
http://your-domain/mobile/v1/{endpoint}
```

### Available Endpoints

**Authentication:**
- POST `/mobile/v1/auth/register` - Register new user
- POST `/mobile/v1/auth/login` - Login
- POST `/mobile/v1/auth/firebase/sms` - SMS authentication
- POST `/mobile/v1/auth/social/{provider}` - Social login
- POST `/mobile/v1/auth/refresh` - Refresh token
- POST `/mobile/v1/auth/logout` - Logout

**Home:**
- GET `/mobile/v1/home` - Get home page data
- GET `/mobile/v1/home/intro-page` - App intro
- GET `/mobile/v1/home/general-settings` - App settings
- GET `/mobile/v1/home/categories` - Featured categories
- GET `/mobile/v1/home/hit-products` - Bestsellers

**Products:**
- GET `/mobile/v1/products` - List products
- GET `/mobile/v1/products/{id}` - Product details
- GET `/mobile/v1/products/search` - Search products

**Wallet:**
- GET `/mobile/v1/wallet/balance` - Get balance
- POST `/mobile/v1/wallet/topup` - Add funds
- GET `/mobile/v1/wallet/transactions` - Transaction history

**Notifications:**
- GET `/mobile/v1/notifications` - List notifications
- POST `/mobile/v1/notifications/mark-read` - Mark as read
- POST `/mobile/v1/notifications/register-device` - Register device

### API Documentation

Once the endpoint is configured and synced, access the interactive documentation:

- **Swagger UI**: `http://your-domain/mobile/docs`
- **ReDoc**: `http://your-domain/mobile/redoc`
- **OpenAPI JSON**: `http://your-domain/mobile/openapi.json`

## Configuration Parameters

All configuration is stored in Odoo's `ir.config_parameter` and can be modified via:

**Settings > Technical > Parameters > System Parameters**

### JWT Configuration

| Key | Default Value | Description |
|-----|---------------|-------------|
| `mobile_api.jwt.secret_key` | `change-this-secret-key-in-production-please` | JWT secret key (CHANGE IN PRODUCTION!) |
| `mobile_api.jwt.algorithm` | `HS256` | JWT algorithm |
| `mobile_api.jwt.access_token_expire_minutes` | `30` | Access token expiration (minutes) |
| `mobile_api.jwt.refresh_token_expire_days` | `7` | Refresh token expiration (days) |

### App Configuration

| Key | Default Value | Description |
|-----|---------------|-------------|
| `mobile_api.app_name` | `Yellow` | Application name |
| `mobile_api.app_version` | `1.0.0` | Application version |
| `mobile_api.support_email` | `support@uellow.com` | Support email |
| `mobile_api.support_phone` | `+1234567890` | Support phone |

### Feature Flags

| Key | Default Value | Description |
|-----|---------------|-------------|
| `mobile_api.wallet_enabled` | `true` | Enable wallet feature |
| `mobile_api.reviews_enabled` | `true` | Enable reviews |
| `mobile_api.wishlist_enabled` | `true` | Enable wishlist |
| `mobile_api.notifications_enabled` | `true` | Enable notifications |

## Security Configuration

### 1. Change JWT Secret Key (IMPORTANT!)

For production, generate a secure secret key:

```python
import secrets
secret_key = secrets.token_urlsafe(32)
```

Then update via Odoo shell or UI:

```python
env['ir.config_parameter'].sudo().set_param(
    'mobile_api.jwt.secret_key', 
    'your-secure-production-key-here'
)
```

### 2. Configure Endpoint User

The endpoint runs with the configured user's permissions. For security:

1. Go to **FastAPI > Endpoints > Mobile API v1**
2. Change **User** field from Administrator to a dedicated API user
3. Create a dedicated user with minimal required permissions:

```xml
<record id="mobile_api_user" model="res.users">
    <field name="name">Mobile API User</field>
    <field name="login">mobile_api_user</field>
    <field name="groups_id" eval="[(6, 0, [
        ref('base.group_user'),
        ref('sales_team.group_sale_salesman'),
    ])]"/>
</record>
```

### 3. CORS Configuration

CORS is handled by the FastAPI module. Configure in Odoo if needed.

## Testing

### 1. Health Check

```bash
curl http://your-domain/mobile/health
```

Expected response:
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "service": "Yellow Mobile API",
    "version": "1",
    "environment": "development"
  }
}
```

### 2. Register User

```bash
curl -X POST "http://your-domain/mobile/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "Test123!",
    "name": "Test User",
    "phone": "+1234567890"
  }'
```

### 3. Login

```bash
curl -X POST "http://your-domain/mobile/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "Test123!"
  }'
```

### 4. Get Home Data (with authentication)

```bash
curl -X GET "http://your-domain/mobile/v1/home" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Troubleshooting

### Issue: Endpoint not found (404)

**Solution:**
1. Check if the endpoint is active: **FastAPI > Endpoints**
2. Click **"Sync Registry"** button
3. Restart Odoo server

### Issue: Authentication errors

**Solution:**
1. Check JWT configuration parameters
2. Ensure secret key is set
3. Verify token is included in Authorization header: `Bearer <token>`

### Issue: Module import errors

**Solution:**
1. Check that all router files exist in `routers/` directory
2. Verify `__init__.py` imports are correct
3. Check Odoo logs for detailed error messages

### Issue: CORS errors in browser

**Solution:**
1. FastAPI module handles CORS
2. Check FastAPI endpoint configuration
3. May need to add CORS middleware in app.py if needed

### Issue: Empty response or 500 errors

**Solution:**
1. Check Odoo logs: `tail -f /var/log/odoo/odoo.log`
2. Verify all dependencies are installed: `pip install -r requirements.txt`
3. Check database for configuration parameters
4. Verify user permissions on endpoint

## Development

### Adding New Routers

1. Create new router file in `routers/`:

```python
# routers/mobile_new_router.py
from fastapi import APIRouter
router = APIRouter(prefix="/mobile/v1/new", tags=["New Feature"])

@router.get("/")
async def get_new_data():
    return {"message": "New feature"}
```

2. Import in `routers/__init__.py`:

```python
from . import mobile_new_router
```

3. Add to `models/fastapi_endpoint.py`:

```python
def _get_fastapi_routers(self):
    if self.app == "mobile_api":
        from ..routers import mobile_new_router
        return [
            # ... existing routers ...
            mobile_new_router.router,
        ]
    return super()._get_fastapi_routers()
```

4. Update module and sync registry

### Modifying Configuration

Configuration parameters can be added in `data/fastapi_endpoint.xml`:

```xml
<record id="my_new_config" model="ir.config_parameter">
    <field name="key">mobile_api.my_new_setting</field>
    <field name="value">my_value</field>
</record>
```

Then access in code:

```python
config = env['ir.config_parameter'].sudo()
my_setting = config.get_param('mobile_api.my_new_setting', 'default_value')
```

## Best Practices

1. **Always change the JWT secret in production**
2. **Use a dedicated user for the endpoint** (not Administrator)
3. **Enable HTTPS in production**
4. **Monitor API usage and logs**
5. **Implement rate limiting** if needed
6. **Keep dependencies updated**
7. **Test endpoints after each deployment**
8. **Document all new endpoints**
9. **Use proper error handling** in routers
10. **Validate input data** with Pydantic models

## References

- [FastAPI Module Documentation](https://github.com/OCA/rest-framework/tree/16.0/fastapi)
- [FastAPI Official Docs](https://fastapi.tiangolo.com/)
- [Odoo Development Documentation](https://www.odoo.com/documentation/16.0/developer.html)

---

**Last Updated:** October 27, 2025  
**Module Version:** 1.0.0

