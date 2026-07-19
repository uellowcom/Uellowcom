# Yellow Mobile API Architecture

## 🏗️ Project Structure

```
mobile_api/
├── __init__.py
├── __manifest__.py
├── README.md
├── ARCHITECTURE.md
├── requirements.txt
├── .env.example
│
├── api/
│   ├── __init__.py
│   ├── v1/
│   │   ├── __init__.py
│   │   ├── endpoints/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── home.py
│   │   │   ├── products.py
│   │   │   ├── orders.py
│   │   │   ├── users.py
│   │   │   ├── blog.py
│   │   │   ├── reviews.py
│   │   │   ├── notifications.py
│   │   │   ├── wallet.py
│   │   │   ├── coupons.py
│   │   │   └── categories.py
│   │   ├── dependencies.py
│   │   └── router.py
│   └── v2/
│       └── (future versions)
│
├── core/
│   ├── __init__.py
│   ├── config.py
│   ├── security.py
│   ├── exceptions.py
│   ├── constants.py
│   └── utils.py
│
├── models/
│   ├── __init__.py
│   ├── base.py
│   ├── auth_models.py
│   ├── product_models.py
│   ├── order_models.py
│   ├── user_models.py
│   ├── notification_models.py
│   ├── wallet_models.py
│   └── review_models.py
│
├── schemas/
│   ├── __init__.py
│   ├── auth_schemas.py
│   ├── product_schemas.py
│   ├── order_schemas.py
│   ├── user_schemas.py
│   ├── notification_schemas.py
│   ├── wallet_schemas.py
│   ├── review_schemas.py
│   └── common_schemas.py
│
├── services/
│   ├── __init__.py
│   ├── auth_service.py
│   ├── product_service.py
│   ├── order_service.py
│   ├── user_service.py
│   ├── notification_service.py
│   ├── wallet_service.py
│   ├── review_service.py
│   ├── cache_service.py
│   └── external_services/
│       ├── __init__.py
│       ├── firebase_service.py
│       ├── google_auth_service.py
│       ├── facebook_auth_service.py
│       ├── apple_auth_service.py
│       ├── payment_service.py
│       └── sms_service.py
│
├── middleware/
│   ├── __init__.py
│   ├── authentication.py
│   ├── rate_limiting.py
│   ├── cors.py
│   ├── logging.py
│   └── error_handling.py
│
├── database/
│   ├── __init__.py
│   ├── connection.py
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── base_repository.py
│   │   ├── product_repository.py
│   │   ├── order_repository.py
│   │   └── user_repository.py
│   └── migrations/
│       └── (migration files)
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
└── docs/
    ├── api_documentation.md
    ├── swagger/
    └── postman/
```

## 🔧 Component Architecture

### 1. API Layer (`api/`)
- **Version Management**: API versioning (v1, v2, etc.)
- **Endpoints**: RESTful endpoints organized by domain
- **Router**: Central routing configuration

### 2. Core Layer (`core/`)
- **Configuration**: Environment variables and app settings
- **Security**: JWT, OAuth, API key management
- **Exceptions**: Custom exception handling
- **Utils**: Common utility functions

### 3. Business Logic Layer (`services/`)
- **Service Classes**: Business logic implementation
- **External Services**: Third-party integrations
- **Cache Service**: Redis/Memcached integration

### 4. Data Layer
- **Models**: Odoo model extensions
- **Schemas**: Pydantic models for validation
- **Repositories**: Data access patterns

### 5. Middleware Layer
- **Authentication**: Token validation
- **Rate Limiting**: API throttling
- **CORS**: Cross-origin configuration
- **Logging**: Request/response logging

## 📊 API Endpoint Mapping

### Authentication Module
```
POST   /api/v1/auth/register
POST   /api/v1/auth/login
POST   /api/v1/auth/logout
POST   /api/v1/auth/refresh-token
POST   /api/v1/auth/forgot-password
POST   /api/v1/auth/reset-password
POST   /api/v1/auth/firebase/sms
POST   /api/v1/auth/firebase/token
POST   /api/v1/auth/social/google
POST   /api/v1/auth/social/facebook
POST   /api/v1/auth/social/apple
GET    /api/v1/auth/cookie
```

### Home Module
```
GET    /api/v1/home
GET    /api/v1/home/intro-page
GET    /api/v1/home/general-settings
GET    /api/v1/home/slider
GET    /api/v1/home/categories
GET    /api/v1/home/flash-sale
GET    /api/v1/home/mini-banner
GET    /api/v1/home/extend-products
GET    /api/v1/home/recent-view-products
GET    /api/v1/home/popular-categories
GET    /api/v1/home/hit-products
```

### Product Module
```
GET    /api/v1/products
GET    /api/v1/products/{id}
GET    /api/v1/products/categories
GET    /api/v1/products/search
GET    /api/v1/products/barcode/{barcode}
GET    /api/v1/products/{id}/reviews
POST   /api/v1/products/{id}/reviews
GET    /api/v1/products/{id}/variations
GET    /api/v1/products/filter-attributes
GET    /api/v1/products/discount-rules
```

### Wishlist Module
```
GET    /api/v1/wishlist
POST   /api/v1/wishlist/check
POST   /api/v1/wishlist/add
DELETE /api/v1/wishlist/remove
```

### Order & Checkout Module
```
GET    /api/v1/orders
GET    /api/v1/orders/{id}
POST   /api/v1/checkout/data
POST   /api/v1/checkout/place-order
POST   /api/v1/checkout/apply-coupon
```

### User Module
```
GET    /api/v1/users/profile
PUT    /api/v1/users/profile
GET    /api/v1/users/reviews
```

### Notification Module
```
GET    /api/v1/notifications
PUT    /api/v1/notifications/{id}/read
POST   /api/v1/notifications/stock-alert
```

### Wallet Module
```
GET    /api/v1/wallet/balance
POST   /api/v1/wallet/topup
POST   /api/v1/wallet/transfer
GET    /api/v1/wallet/transactions
```

### Blog Module
```
GET    /api/v1/posts
GET    /api/v1/posts/{id}
POST   /api/v1/posts/{id}/comments
GET    /api/v1/posts/{id}/comments
```

### Categories Module
```
GET    /api/v1/categories
GET    /api/v1/categories/{id}
GET    /api/v1/categories/{id}/products
```

### Coupons Module
```
GET    /api/v1/coupons
GET    /api/v1/coupons/{code}
POST   /api/v1/coupons/validate
```

## 🔐 Security Architecture

### Authentication Flow
```
1. Multi-Provider Authentication
   - JWT Token-based
   - OAuth 2.0 (Google, Facebook, Apple)
   - Firebase SMS Authentication
   - Session Cookie Support

2. Authorization
   - Role-based Access Control (RBAC)
   - API Key Management
   - Rate Limiting per User/IP

3. Data Protection
   - Input Validation (Pydantic)
   - SQL Injection Prevention
   - XSS Protection
   - HTTPS Enforcement
```

## 🚀 Performance Optimization

### Caching Strategy
```python
- Redis for session management
- Response caching for static data
- Database query optimization
- CDN for static assets
```

### Database Optimization
```python
- Connection pooling
- Query optimization
- Indexed fields
- Lazy loading
```

## 📦 Technology Stack

### Backend
- **Framework**: FastAPI + Odoo
- **Python**: 3.10+
- **Database**: PostgreSQL
- **Cache**: Redis
- **Message Queue**: RabbitMQ/Celery

### Authentication
- **JWT**: PyJWT
- **OAuth**: Authlib
- **Firebase**: firebase-admin

### API Documentation
- **OpenAPI**: Automatic generation
- **Swagger UI**: Interactive documentation
- **ReDoc**: Alternative documentation

## 🔄 Development Workflow

### 1. API Development Process
```
1. Define Schema (Pydantic)
2. Create Service Layer
3. Implement Endpoint
4. Add Tests
5. Update Documentation
```

### 2. Testing Strategy
```
- Unit Tests: 80% coverage
- Integration Tests: API endpoints
- E2E Tests: Critical user flows
- Load Testing: Performance validation
```

### 3. Deployment
```
- Docker containerization
- Kubernetes orchestration
- CI/CD pipeline
- Blue-Green deployment
```

## 📝 Code Standards

### Naming Conventions
- **Files**: snake_case.py
- **Classes**: PascalCase
- **Functions**: snake_case
- **Constants**: UPPER_SNAKE_CASE

### Documentation
- Docstrings for all functions
- Type hints for all parameters
- OpenAPI descriptions
- README for each module

## 🎯 Key Design Principles

1. **Separation of Concerns**
   - Clear layer boundaries
   - Single responsibility

2. **DRY (Don't Repeat Yourself)**
   - Reusable components
   - Shared utilities

3. **SOLID Principles**
   - Dependency injection
   - Interface segregation

4. **Scalability**
   - Horizontal scaling support
   - Microservices ready

5. **Security First**
   - Input validation
   - Authentication/Authorization
   - Data encryption
