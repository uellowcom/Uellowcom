# Yellow Mobile API Documentation

This document provides comprehensive documentation for the Yellow Mobile API implementation using FastAPI integrated with Odoo.

## Overview

The Yellow Mobile API provides a RESTful interface for mobile applications to interact with the Odoo backend. It includes endpoints for authentication, products, home data, wallet management, and notifications.

## Architecture

The API is built using FastAPI integrated with Odoo's ORM system. Key components include:

- **FastAPI Routers**: Organized by functionality (auth, products, home, wallet, notifications)
- **JWT Authentication**: Secure token-based authentication
- **Odoo Integration**: Direct access to Odoo models and business logic
- **Pydantic Models**: For request/response validation

## Authentication

All API endpoints (except health check and login/register) require JWT authentication.

### Endpoints

#### Health Check
```
GET /mobile/v1/auth/health
```
Returns the health status of the API.

#### Register
```
POST /mobile/v1/auth/register
```
Register a new mobile user.

**Request Body:**
```json
{
  "username": "string",
  "password": "string",
  "name": "string",
  "email": "string",
  "device_id": "string",
  "device_platform": "string"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "access_token": "string",
    "refresh_token": "string",
    "user": {
      "id": "integer",
      "username": "string",
      "name": "string",
      "email": "string"
    }
  }
}
```

#### Login
```
POST /mobile/v1/auth/login
```
Login with username and password.

**Request Body:**
```json
{
  "username": "string",
  "password": "string",
  "device_id": "string",
  "device_platform": "string"
}
```

**Response:** Same as register endpoint.

#### Refresh Token
```
POST /mobile/v1/auth/refresh
```
Get a new access token using a refresh token.

**Request Body:**
```json
{
  "refresh_token": "string"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "access_token": "string",
    "refresh_token": "string"
  }
}
```

#### Logout
```
POST /mobile/v1/auth/logout
```
Invalidate the current token.

**Response:**
```json
{
  "success": true,
  "data": {
    "message": "Logged out successfully"
  }
}
```

## Products

### Endpoints

#### Get Categories
```
GET /mobile/v1/products/categories
```
Get all product categories.

**Response:**
```json
{
  "success": true,
  "data": {
    "categories": [
      {
        "id": "integer",
        "name": "string",
        "image_url": "string",
        "product_count": "integer",
        "child_count": "integer"
      }
    ]
  }
}
```

#### Get Products
```
GET /mobile/v1/products
```
Get products with optional filtering.

**Query Parameters:**
- `category_id` (optional): Filter by category
- `offset` (optional): Pagination offset
- `limit` (optional): Pagination limit

**Response:**
```json
{
  "success": true,
  "data": {
    "products": [
      {
        "id": "integer",
        "name": "string",
        "price": "float",
        "list_price": "float",
        "currency": "string",
        "image_url": "string",
        "is_in_wishlist": "boolean",
        "rating": "float",
        "review_count": "integer"
      }
    ],
    "total_count": "integer"
  }
}
```

#### Get Product Detail
```
GET /mobile/v1/products/{product_id}
```
Get detailed information about a specific product.

**Response:**
```json
{
  "success": true,
  "data": {
    "product": {
      "id": "integer",
      "name": "string",
      "price": "float",
      "list_price": "float",
      "currency": "string",
      "description": "string",
      "images": ["string"],
      "attributes": [
        {
          "name": "string",
          "values": ["string"]
        }
      ],
      "variants": [
        {
          "id": "integer",
          "combination": "string",
          "price": "float"
        }
      ],
      "is_in_wishlist": "boolean",
      "rating": "float",
      "review_count": "integer"
    }
  }
}
```

#### Toggle Wishlist
```
POST /mobile/v1/products/wishlist/toggle/{product_id}
```
Add or remove a product from the user's wishlist.

**Response:**
```json
{
  "success": true,
  "data": {
    "is_in_wishlist": "boolean",
    "message": "string"
  }
}
```

#### Get Wishlist
```
GET /mobile/v1/products/wishlist
```
Get the user's wishlist.

**Response:**
```json
{
  "success": true,
  "data": {
    "products": [
      {
        "id": "integer",
        "name": "string",
        "price": "float",
        "list_price": "float",
        "currency": "string",
        "image_url": "string",
        "is_in_wishlist": true,
        "rating": "float",
        "review_count": "integer"
      }
    ]
  }
}
```

## Home

### Endpoints

#### Get Banners
```
GET /mobile/v1/home/banners
```
Get promotional banners for the home screen.

**Response:**
```json
{
  "success": true,
  "data": {
    "banners": [
      {
        "id": "integer",
        "name": "string",
        "image_url": "string",
        "target_type": "string",
        "target_id": "integer"
      }
    ]
  }
}
```

#### Get Featured Categories
```
GET /mobile/v1/home/featured-categories
```
Get featured categories for the home screen.

**Response:**
```json
{
  "success": true,
  "data": {
    "categories": [
      {
        "id": "integer",
        "name": "string",
        "image_url": "string",
        "product_count": "integer"
      }
    ]
  }
}
```

#### Get Featured Products
```
GET /mobile/v1/home/featured-products
```
Get featured products for the home screen.

**Response:**
```json
{
  "success": true,
  "data": {
    "products": [
      {
        "id": "integer",
        "name": "string",
        "price": "float",
        "list_price": "float",
        "currency": "string",
        "image_url": "string",
        "is_in_wishlist": "boolean",
        "rating": "float",
        "review_count": "integer"
      }
    ]
  }
}
```

#### Get Best Selling Products
```
GET /mobile/v1/home/best-selling
```
Get best selling products.

**Response:** Same as featured products.

#### Get Discounted Products
```
GET /mobile/v1/home/discounted
```
Get products with discounts.

**Response:** Same as featured products.

#### Get Search Suggestions
```
GET /mobile/v1/home/search-suggestions
```
Get search suggestions based on popular searches.

**Response:**
```json
{
  "success": true,
  "data": {
    "suggestions": ["string"]
  }
}
```

## Wallet

### Endpoints

#### Get Wallet Balance
```
GET /mobile/v1/wallet/balance
```
Get the user's wallet balance and loyalty points.

**Response:**
```json
{
  "success": true,
  "data": {
    "balance": "float",
    "currency": "string",
    "loyalty_points": [
      {
        "program_id": "integer",
        "program_name": "string",
        "points": "float"
      }
    ]
  }
}
```

#### Get Wallet Transactions
```
GET /mobile/v1/wallet/transactions
```
Get the user's wallet transactions.

**Query Parameters:**
- `offset` (optional): Pagination offset
- `limit` (optional): Pagination limit

**Response:**
```json
{
  "success": true,
  "data": {
    "transactions": [
      {
        "id": "integer",
        "date": "datetime",
        "description": "string",
        "amount": "float",
        "currency": "string",
        "transaction_type": "string"
      }
    ],
    "total_count": "integer"
  }
}
```

#### Add Funds
```
POST /mobile/v1/wallet/add-funds
```
Add funds to the user's wallet.

**Request Body:**
```json
{
  "amount": "float",
  "payment_method": "string"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "transaction_id": "string",
    "message": "string"
  }
}
```

#### Redeem Points
```
POST /mobile/v1/wallet/redeem-points
```
Redeem loyalty points for rewards.

**Request Body:**
```json
{
  "program_id": "integer",
  "reward_id": "integer",
  "points": "float"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "transaction_id": "string",
    "message": "string"
  }
}
```

## Notifications

### Endpoints

#### Get Notifications
```
GET /mobile/v1/notifications
```
Get the user's notifications.

**Query Parameters:**
- `offset` (optional): Pagination offset
- `limit` (optional): Pagination limit
- `unread_only` (optional): Filter for unread notifications only

**Response:**
```json
{
  "success": true,
  "data": {
    "notifications": [
      {
        "id": "integer",
        "title": "string",
        "message": "string",
        "date": "datetime",
        "is_read": "boolean",
        "notification_type": "string",
        "data": {
          "reference": {
            "model": "string",
            "id": "integer"
          }
        }
      }
    ],
    "unread_count": "integer",
    "total_count": "integer"
  }
}
```

#### Mark Notification as Read
```
POST /mobile/v1/notifications/mark-read/{notification_id}
```
Mark a specific notification as read.

**Response:**
```json
{
  "success": true,
  "data": {
    "message": "Notification marked as read"
  }
}
```

#### Mark All Notifications as Read
```
POST /mobile/v1/notifications/mark-all-read
```
Mark all notifications as read.

**Response:**
```json
{
  "success": true,
  "data": {
    "message": "X notifications marked as read"
  }
}
```

#### Register Device for Push Notifications
```
POST /mobile/v1/notifications/register-device
```
Register a device for push notifications.

**Query Parameters:**
- `device_token`: The device token for push notifications
- `device_type`: The device type (ios or android)

**Response:**
```json
{
  "success": true,
  "data": {
    "device_id": "integer",
    "message": "Device registered successfully"
  }
}
```

#### Unregister Device
```
POST /mobile/v1/notifications/unregister-device
```
Unregister a device from push notifications.

**Query Parameters:**
- `device_token`: The device token to unregister

**Response:**
```json
{
  "success": true,
  "data": {
    "message": "Device unregistered successfully"
  }
}
```

## Error Handling

All endpoints follow a consistent error response format:

```json
{
  "success": false,
  "error": "Error message"
}
```

Common HTTP status codes:
- `200`: Success
- `400`: Bad Request
- `401`: Unauthorized
- `404`: Not Found
- `500`: Internal Server Error

## Testing

A comprehensive test script is available at `/Users/omarkhaled/uellowcom/mobile_fastapi_test_extended.py` to test all API endpoints.

## Dependencies

- FastAPI
- Pydantic
- PyJWT
- Odoo

## Development and Deployment

### Local Development

1. Ensure Odoo is running
2. Set up the FastAPI module in the Odoo addons path
3. Install the module in Odoo
4. Access the API at `http://localhost:8069/mobile/v1/`

### Production Deployment

1. Deploy the module as part of the Odoo deployment
2. Configure proper security settings (HTTPS, rate limiting, etc.)
3. Set up proper logging and monitoring
