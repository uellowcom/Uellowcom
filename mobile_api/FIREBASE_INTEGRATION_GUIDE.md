# 🔥 Firebase Integration Guide - Yellow Mobile API

## Table of Contents
1. [Why Firebase?](#why-firebase)
2. [Setup Instructions](#setup-instructions)
3. [Features Available](#features-available)
4. [Implementation Examples](#implementation-examples)
5. [Testing](#testing)
6. [Troubleshooting](#troubleshooting)

---

## Why Firebase?

Firebase provides essential services for modern mobile applications:

### 📱 **Push Notifications (FCM)**
- **Real-time engagement**: Reach users instantly
- **High delivery rate**: 95%+ delivery success
- **Free tier**: 10M messages/month
- **Rich notifications**: Images, actions, custom sounds

**E-commerce Use Cases:**
- Order confirmations & updates
- Shipping notifications
- Payment confirmations
- Flash sales & promotions
- Cart abandonment reminders
- Product back-in-stock alerts
- Personalized offers

### 🔐 **Authentication**
- **SMS/Phone verification**: OTP-based authentication
- **Social login**: Google, Facebook, Apple Sign-In
- **Email/Password**: Traditional authentication
- **Anonymous auth**: Guest checkout

### 📊 **Analytics** (Optional)
- User behavior tracking
- Conversion tracking
- A/B testing
- User segmentation

---

## Setup Instructions

### Step 1: Create Firebase Project

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Click **"Add Project"**
3. Enter project name: `yellow-mobile-app`
4. Enable Google Analytics (optional but recommended)
5. Click **"Create Project"**

### Step 2: Add Mobile Apps

#### For Android (Flutter):
```bash
1. In Firebase Console, click "Add App" → Android icon
2. Package name: com.yellow.mobileapp (or your package name)
3. Download google-services.json
4. Place in: android/app/google-services.json
```

#### For iOS (Flutter):
```bash
1. In Firebase Console, click "Add App" → iOS icon
2. Bundle ID: com.yellow.mobileapp (or your bundle ID)
3. Download GoogleService-Info.plist
4. Place in: ios/Runner/GoogleService-Info.plist
```

### Step 3: Enable Firebase Services

#### Enable Authentication
```
Firebase Console → Authentication → Get Started
Enable:
✅ Email/Password
✅ Phone (SMS) - Requires billing enabled
✅ Google
✅ Facebook (requires FB App setup)
✅ Apple (requires Apple Developer account)
```

#### Enable Cloud Messaging
```
Firebase Console → Cloud Messaging
- Automatically enabled for new projects
- Note your Server Key for later
```

### Step 4: Generate Service Account Key

```bash
# In Firebase Console:
1. Go to Project Settings (⚙️) → Service Accounts
2. Click "Generate new private key"
3. Save as firebase_credentials.json
4. Upload to your server in a secure location
```

**Security Note**: Keep this file secure! It has admin access to your Firebase project.

### Step 5: Install Firebase Admin SDK

```bash
# On your server (where Odoo is running):
pip install firebase-admin

# Or add to requirements.txt:
echo "firebase-admin>=6.2.0" >> requirements.txt
pip install -r requirements.txt
```

### Step 6: Configure Odoo

#### Option A: Environment Variables
Create `.env` file in Odoo root:
```bash
FIREBASE_PROJECT_ID=yellow-mobile-app
FIREBASE_CREDENTIALS_PATH=/path/to/firebase_credentials.json
```

#### Option B: Odoo System Parameters
```
Settings → Technical → Parameters → System Parameters

Create two parameters:
1. Key: mobile_api.firebase.project_id
   Value: yellow-mobile-app

2. Key: mobile_api.firebase.credentials_path
   Value: /path/to/firebase_credentials.json
```

### Step 7: Restart Odoo
```bash
# Restart your Odoo server
sudo systemctl restart odoo
# or
./odoo-bin --config=/path/to/odoo.conf
```

---

## Features Available

### ✅ Implemented Features

#### 1. Push Notifications
- ✅ Single device notifications
- ✅ Multicast (multiple devices)
- ✅ Topic-based notifications
- ✅ Rich notifications (images, custom sounds)
- ✅ Platform-specific configs (Android/iOS)

#### 2. Authentication
- ✅ Email/Password (JWT-based)
- ✅ SMS verification (framework ready)
- ✅ Social login (framework ready)
- ✅ Token management

#### 3. Device Management
- ✅ Register FCM tokens
- ✅ Multiple devices per user
- ✅ Device deactivation on logout

---

## Implementation Examples

### 1. Send Push Notification (Single Device)

```python
from odoo import api, models

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    def action_confirm(self):
        res = super().action_confirm()
        
        # Send order confirmation notification
        if self.partner_id.mobile_notification_token:
            self.env['mobile.notification'].create_notification(
                partner_id=self.partner_id.id,
                title='Order Confirmed! 🎉',
                message=f'Your order {self.name} has been confirmed',
                notification_type='order',
                data={
                    'order_id': self.id,
                    'order_name': self.name,
                    'amount_total': self.amount_total,
                },
                send_push=True
            )
        
        return res
```

### 2. Send to Multiple Users (Multicast)

```python
from odoo import api, models

class ProductProduct(models.Model):
    _inherit = 'product.product'
    
    async def notify_back_in_stock(self):
        """Notify users when product is back in stock"""
        # Get users who favorited this product
        favorites = self.env['product.favorite'].search([
            ('product_id', '=', self.id)
        ])
        
        # Get FCM tokens
        tokens = [
            fav.partner_id.mobile_notification_token 
            for fav in favorites 
            if fav.partner_id.mobile_notification_token
        ]
        
        if tokens:
            firebase_service = self.env['mobile_api.firebase'].get_service()
            await firebase_service.send_push_notification_multicast(
                tokens=tokens,
                title='🎉 Back in Stock!',
                body=f'{self.name} is now available',
                data={
                    'product_id': self.id,
                    'product_name': self.name,
                    'type': 'back_in_stock'
                }
            )
```

### 3. Topic-Based Notifications (Promotions)

```python
from odoo import api, models

class SalePromotion(models.Model):
    _name = 'sale.promotion'
    
    async def send_promotion_notification(self):
        """Send promotion to all users subscribed to promotions topic"""
        firebase_service = self.env['mobile_api.firebase'].get_service()
        
        await firebase_service.send_topic_notification(
            topic='promotions',
            title='🔥 Flash Sale!',
            body=f'{self.discount}% off on selected items',
            data={
                'promotion_id': self.id,
                'discount': self.discount,
                'type': 'flash_sale'
            }
        )
```

### 4. Flutter Client Integration

```dart
// Add to pubspec.yaml
dependencies:
  firebase_core: ^2.24.0
  firebase_messaging: ^14.7.0
  flutter_local_notifications: ^16.3.0

// Initialize Firebase
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Firebase.initializeApp();
  
  // Get FCM token
  final fcmToken = await FirebaseMessaging.instance.getToken();
  print('FCM Token: $fcmToken');
  
  // Register token with your API
  await apiService.registerPushToken(fcmToken);
  
  // Handle foreground notifications
  FirebaseMessaging.onMessage.listen((RemoteMessage message) {
    print('Received notification: ${message.notification?.title}');
    // Show local notification
  });
  
  runApp(MyApp());
}

// API Service
class ApiService {
  Future<void> registerPushToken(String token) async {
    final response = await http.post(
      Uri.parse('$baseUrl/mobile/v1/notifications/register-token'),
      headers: {
        'Authorization': 'Bearer $accessToken',
        'Content-Type': 'application/json',
      },
      body: jsonEncode({
        'token': token,
        'device_type': Platform.isIOS ? 'ios' : 'android',
      }),
    );
  }
}
```

---

## Testing

### Test Push Notifications

#### 1. Register Device Token
```bash
curl -X POST 'http://localhost:8069/mobile/mobile/v1/notifications/register-token' \
  -H 'Authorization: Bearer YOUR_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "token": "YOUR_FCM_TOKEN",
    "device_type": "android"
  }'
```

#### 2. Send Test Notification
```bash
curl -X POST 'http://localhost:8069/mobile/mobile/v1/notifications/test-push' \
  -H 'Authorization: Bearer YOUR_ACCESS_TOKEN' \
  -H 'Content-Type: application/json'
```

#### 3. Test from Python Console
```python
# In Odoo shell (odoo-bin shell -c odoo.conf -d your_db)
import asyncio

# Get Firebase service
from odoo.addons.mobile_api.services.firebase_service import FirebaseService
firebase = FirebaseService()

# Test single notification
asyncio.run(firebase.send_push_notification(
    token='YOUR_FCM_TOKEN',
    title='Test Notification',
    body='This is a test from Odoo shell',
    data={'type': 'test'}
))
```

---

## Notification Examples for E-commerce

### Order Notifications
```python
# Order Placed
{
    'title': '🛍️ Order Placed Successfully',
    'body': 'Your order #SO001 has been received',
    'data': {'type': 'order_placed', 'order_id': 1}
}

# Payment Confirmed
{
    'title': '✅ Payment Confirmed',
    'body': 'Payment received for order #SO001',
    'data': {'type': 'payment_confirmed', 'order_id': 1}
}

# Order Shipped
{
    'title': '📦 Your Order is On the Way!',
    'body': 'Order #SO001 has been shipped. Track: TRK123456',
    'data': {'type': 'order_shipped', 'order_id': 1, 'tracking': 'TRK123456'}
}

# Delivered
{
    'title': '🎉 Order Delivered',
    'body': 'Your order has been delivered. Enjoy!',
    'data': {'type': 'order_delivered', 'order_id': 1}
}
```

### Marketing Notifications
```python
# Flash Sale
{
    'title': '⚡ Flash Sale - 50% Off!',
    'body': 'Limited time offer on selected items',
    'data': {'type': 'flash_sale', 'category': 'electronics'}
}

# Cart Abandonment
{
    'title': '🛒 You Left Items in Cart',
    'body': 'Complete your purchase and save 10%!',
    'data': {'type': 'cart_reminder', 'discount_code': 'SAVE10'}
}

# Wishlist Alert
{
    'title': '💝 Price Drop on Wishlist Item',
    'body': 'Product X is now 30% off!',
    'data': {'type': 'price_drop', 'product_id': 123}
}
```

---

## Troubleshooting

### Issue: Firebase not initializing
```
Error: Firebase initialization failed
```
**Solution:**
1. Check credentials path is correct
2. Verify firebase_credentials.json is valid
3. Ensure Firebase project ID matches
4. Check server has internet access

### Issue: Notifications not received on device
```
FCM send failed: Invalid registration token
```
**Solutions:**
1. Verify FCM token is still valid (tokens can expire)
2. Re-register device token
3. Check Firebase project configuration
4. Verify google-services.json/GoogleService-Info.plist in app

### Issue: Import error
```
ImportError: No module named 'firebase_admin'
```
**Solution:**
```bash
pip install firebase-admin
# Restart Odoo after installation
```

### Issue: Authentication error
```
google.auth.exceptions.DefaultCredentialsError
```
**Solution:**
Set GOOGLE_APPLICATION_CREDENTIALS environment variable:
```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/firebase_credentials.json"
```

---

## Best Practices

### 1. **Token Management**
- Refresh tokens regularly
- Remove inactive tokens
- Handle token expiration gracefully

### 2. **Notification Content**
- Keep titles under 40 characters
- Keep body under 100 characters
- Use emojis sparingly but effectively
- Include actionable information

### 3. **Timing**
- Don't send too many notifications
- Respect user's timezone
- Allow users to configure preferences

### 4. **Security**
- Keep credentials secure
- Use environment variables
- Never commit credentials to git
- Rotate keys regularly

### 5. **Testing**
- Test on real devices
- Test both Android and iOS
- Test with app in foreground/background
- Test notification actions

---

## Resources

- [Firebase Console](https://console.firebase.google.com/)
- [FCM Documentation](https://firebase.google.com/docs/cloud-messaging)
- [Firebase Admin SDK](https://firebase.google.com/docs/admin/setup)
- [Flutter Firebase Setup](https://firebase.flutter.dev/docs/overview)

---

## Support

For issues related to:
- Firebase setup: Check Firebase Console logs
- Odoo integration: Check Odoo server logs
- Flutter client: Check device logs (logcat/console)

**Module Version:** 1.0.0  
**Last Updated:** October 27, 2025

