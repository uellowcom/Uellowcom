# Yellow Mobile API - Deployment Guide

## 🚀 Complete Deployment Instructions

This guide will help you deploy the Yellow Mobile API using Odoo models as the database backend and Firebase for authentication and notifications.

## 📋 Prerequisites

- Odoo 16.0+ instance running
- Python 3.10+
- PostgreSQL database
- Firebase project (optional, for push notifications)
- Access to Odoo addons directory

## 🛠️ Installation Steps

### 1. Install the Mobile API Module

```bash
# Copy the mobile_api folder to your Odoo addons directory
cp -r /Users/omarkhaled/uellowcom/mobile_api /path/to/odoo/addons/

# Or create a symbolic link
ln -s /Users/omarkhaled/uellowcom/mobile_api /path/to/odoo/addons/
```

### 2. Install Python Dependencies

```bash
# Navigate to your Odoo environment
cd /path/to/odoo

# Install required Python packages
pip install firebase-admin google-auth authlib httpx python-dotenv qrcode pillow
```

### 3. Update Odoo Configuration

Add the mobile_api module to your Odoo addons path in `odoo.conf`:

```ini
[options]
addons_path = /path/to/odoo/addons,/path/to/other/addons,/path/to/mobile_api
```

### 4. Install and Configure the Module

1. **Restart Odoo server**
2. **Go to Apps menu**
3. **Remove Apps filter**
4. **Search for "Yellow Mobile API"**
5. **Click Install**

### 5. Configure FastAPI Endpoint

The module automatically creates a FastAPI endpoint. Verify in:
- **Settings > Technical > FastAPI > Endpoints**
- Check that "Yellow Mobile API" endpoint is created with path `/mobile`

### 6. Configure Firebase (Optional)

If using Firebase for authentication and push notifications:

1. **Create Firebase project** at [Firebase Console](https://console.firebase.google.com)
2. **Generate service account key**:
   - Go to Project Settings > Service Accounts
   - Click "Generate new private key"
   - Save as `firebase_credentials.json`

3. **Configure environment variables**:
```bash
# Create .env file in Odoo root directory
echo "FIREBASE_CREDENTIALS_PATH=/path/to/firebase_credentials.json" >> .env
echo "JWT_SECRET_KEY=your-super-secret-jwt-key-change-in-production" >> .env
```

### 7. Configure System Parameters

Go to **Settings > Technical > Parameters > System Parameters** and configure:

| Key | Value | Description |
|-----|-------|-------------|
| `mobile_api.app_name` | Yellow | App name |
| `mobile_api.support_email` | support@yellow.com | Support email |
| `mobile_api.firebase_enabled` | true | Enable Firebase |
| `mobile_api.jwt_secret` | your-secret-key | JWT secret |

## 📡 API Endpoints

Once deployed, your API will be available at:

- **Base URL**: `https://your-odoo-domain.com/mobile`
- **Documentation**: `https://your-odoo-domain.com/mobile/v1/docs`
- **Health Check**: `https://your-odoo-domain.com/mobile/health`

### Key Endpoints

#### Authentication
```http
POST /mobile/v1/auth/register
POST /mobile/v1/auth/login
POST /mobile/v1/auth/firebase/sms
POST /mobile/v1/auth/social/google
POST /mobile/v1/auth/social/facebook
POST /mobile/v1/auth/social/apple
```

#### Products
```http
GET /mobile/v1/products
GET /mobile/v1/products/{id}
GET /mobile/v1/products/categories/list
GET /mobile/v1/products/search
GET /mobile/v1/products/wishlist
POST /mobile/v1/products/wishlist/add
```

#### Home
```http
GET /mobile/v1/home
GET /mobile/v1/home/intro-page
GET /mobile/v1/home/general-settings
GET /mobile/v1/home/categories
GET /mobile/v1/home/hit-products
```

#### Wallet
```http
GET /mobile/v1/wallet/balance
GET /mobile/v1/wallet/transactions
POST /mobile/v1/wallet/topup
POST /mobile/v1/wallet/transfer
```

#### Notifications
```http
GET /mobile/v1/notifications
POST /mobile/v1/notifications/register-token
PUT /mobile/v1/notifications/{id}/read
```

## 🔧 Configuration Options

### JWT Configuration
```python
# In system parameters or environment
JWT_SECRET_KEY = "your-super-secret-key"
JWT_EXPIRY_MINUTES = 30
```

### Firebase Configuration
```python
# Required for Firebase features
FIREBASE_CREDENTIALS_PATH = "/path/to/service-account.json"
```

### CORS Configuration
The FastAPI endpoint automatically configures CORS. To customize:

```xml
<!-- In data/fastapi_endpoint.xml -->
<field name="cors_origins">["https://yourdomain.com", "https://app.yourdomain.com"]</field>
```

## 🧪 Testing the API

### 1. Test Health Endpoint
```bash
curl https://your-odoo-domain.com/mobile/health
```

### 2. Test User Registration
```bash
curl -X POST https://your-odoo-domain.com/mobile/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePass123!",
    "name": "Test User"
  }'
```

### 3. Test Product Listing
```bash
# Get authentication token first, then:
curl -X GET https://your-odoo-domain.com/mobile/v1/products \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## 🔒 Security Considerations

### 1. JWT Secret
- Use a strong, random secret key in production
- Store in environment variables, not in code
- Rotate keys periodically

### 2. HTTPS
- Always use HTTPS in production
- Configure SSL certificates properly
- Use secure headers

### 3. Rate Limiting
- The API includes basic rate limiting (60 requests/minute)
- Configure based on your needs
- Monitor for abuse

### 4. Firebase Security
- Secure Firebase service account credentials
- Use Firebase security rules
- Monitor authentication events

## 📊 Monitoring and Logging

### 1. API Logs
Check Odoo logs for API activity:
```bash
tail -f /var/log/odoo/odoo.log | grep "mobile_api"
```

### 2. Database Monitoring
Monitor mobile-specific tables:
- `mobile_device` - Device registrations
- `mobile_notification` - Notifications sent
- `mobile_wallet_transaction` - Wallet transactions
- `mobile_wishlist` - User wishlists

### 3. Performance Monitoring
- Monitor API response times
- Track endpoint usage
- Monitor database query performance

## 🔄 Maintenance

### 1. Regular Tasks
- Clean up old notifications (30+ days)
- Monitor wallet transaction integrity
- Update Firebase credentials when needed
- Review and rotate JWT secrets

### 2. Updates
- Keep Odoo updated
- Update Python dependencies regularly
- Monitor Firebase SDK updates
- Review security patches

### 3. Backup
- Regular database backups
- Backup Firebase configuration
- Store environment configurations securely

## 🐛 Troubleshooting

### Common Issues

#### 1. Module Installation Fails
```bash
# Check dependencies
pip list | grep -E "(fastapi|firebase|authlib)"

# Check Odoo logs
tail -f /var/log/odoo/odoo.log
```

#### 2. FastAPI Endpoint Not Working
- Verify endpoint is created in Odoo
- Check if FastAPI addon is installed
- Restart Odoo server
- Check URL path configuration

#### 3. Firebase Authentication Fails
- Verify credentials file path
- Check Firebase project configuration
- Validate service account permissions
- Review Firebase logs

#### 4. JWT Token Issues
- Check secret key configuration
- Verify token expiration settings
- Validate token format
- Check system time synchronization

### Debug Mode
Enable debug logging in Odoo:
```ini
[options]
log_level = debug
log_handler = :DEBUG
```

## 📞 Support

For issues and support:
- Check the API documentation at `/mobile/v1/docs`
- Review Odoo logs for errors
- Check Firebase console for authentication issues
- Verify database model installations

## 🎯 Production Checklist

- [ ] Strong JWT secret configured
- [ ] HTTPS enabled with valid certificates
- [ ] Firebase credentials secured
- [ ] Database properly backed up
- [ ] Rate limiting configured
- [ ] Monitoring and logging enabled
- [ ] Security headers configured
- [ ] CORS properly restricted
- [ ] Error handling tested
- [ ] Performance tested under load

Your Yellow Mobile API is now ready for production! 🚀
