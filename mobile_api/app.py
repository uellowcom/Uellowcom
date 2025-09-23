# -*- coding: utf-8 -*-
"""
Yellow Mobile API - FastAPI Application
Modern RESTful API for Flutter E-commerce App
"""

import logging
import sys
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi

# Import API routers
from .api.v1.router import api_v1_router
from .core.config import get_settings
from .core.exceptions import APIException, ValidationException
from .middleware.auth_middleware import AuthMiddleware
from .middleware.logging_middleware import LoggingMiddleware
from .middleware.rate_limit_middleware import RateLimitMiddleware

# Initialize logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get application settings
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("🚀 Yellow Mobile API starting up...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    logger.info(f"API Version: {settings.API_VERSION}")

    yield

    # Shutdown
    logger.info("🛑 Yellow Mobile API shutting down...")


def create_application() -> FastAPI:
    """Create and configure FastAPI application"""

    app = FastAPI(
        title="Yellow Mobile API",
        description="""
        **Yellow Mobile API** - Modern RESTful API for Flutter E-commerce Application
        
        ## 🛍️ Features
        
        ### 🔐 Authentication & Security
        - Multi-provider authentication (Email, SMS, Social)
        - JWT token-based security
        - Role-based access control
        - Rate limiting and security headers
        
        ### 📱 Core E-commerce Features
        - **Products**: Search, filtering, categories, reviews
        - **Cart & Checkout**: Shopping cart, payment processing
        - **Orders**: Order management, tracking, history
        - **Users**: Profile management, preferences, addresses
        - **Wallet**: Digital wallet, transactions, top-up
        - **Notifications**: Push notifications, in-app alerts
        
        ### 🔧 Technical Features  
        - RESTful API design
        - Comprehensive request/response validation
        - Real-time features via WebSocket
        - File upload and media handling
        - Comprehensive error handling
        - API versioning support
        
        ## 📚 Documentation
        - **Interactive Docs**: [Swagger UI](/docs)
        - **Alternative Docs**: [ReDoc](/redoc)
        - **OpenAPI Spec**: [JSON](/openapi.json)
        """,
        version=settings.API_VERSION,
        debug=settings.DEBUG,
        docs_url=None,  # Disable default docs
        redoc_url=None,  # Disable default redoc
        openapi_url=None if settings.ENVIRONMENT == "production" else "/openapi.json",
        lifespan=lifespan,
    )

    # Add middlewares
    setup_middlewares(app)

    # Add routers
    app.include_router(
        api_v1_router, prefix=f"/api/v{settings.API_VERSION}", tags=["API v1"]
    )

    # Add exception handlers
    setup_exception_handlers(app)

    # Add custom routes
    setup_custom_routes(app)

    return app


def setup_middlewares(app: FastAPI) -> None:
    """Setup application middlewares"""

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_HOSTS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Trusted host middleware
    if settings.ENVIRONMENT == "production":
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)

    # Custom middlewares
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(AuthMiddleware)


def setup_exception_handlers(app: FastAPI) -> None:
    """Setup global exception handlers"""

    @app.exception_handler(APIException)
    async def api_exception_handler(request: Request, exc: APIException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": exc.error_code,
                    "message": exc.message,
                    "details": exc.details,
                },
                "data": None,
            },
        )

    @app.exception_handler(ValidationException)
    async def validation_exception_handler(request: Request, exc: ValidationException):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed",
                    "details": exc.errors,
                },
                "data": None,
            },
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {"code": "HTTP_ERROR", "message": exc.detail, "details": None},
                "data": None,
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": (
                        "Internal server error"
                        if settings.ENVIRONMENT == "production"
                        else str(exc)
                    ),
                    "details": None,
                },
                "data": None,
            },
        )


def setup_custom_routes(app: FastAPI) -> None:
    """Setup custom routes like health check, docs, etc."""

    @app.get("/health", tags=["System"])
    async def health_check():
        """API health check endpoint"""
        return {
            "success": True,
            "data": {
                "status": "healthy",
                "service": "Yellow Mobile API",
                "version": settings.API_VERSION,
                "environment": settings.ENVIRONMENT,
            },
        }

    # Custom documentation routes
    if settings.ENVIRONMENT != "production":

        @app.get("/docs", include_in_schema=False)
        async def custom_swagger_ui_html():
            return get_swagger_ui_html(
                openapi_url="/openapi.json",
                title=f"{app.title} - Documentation",
                swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
                swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
            )

        @app.get("/redoc", include_in_schema=False)
        async def redoc_html():
            return get_redoc_html(
                openapi_url="/openapi.json",
                title=f"{app.title} - Documentation",
                redoc_js_url="https://cdn.jsdelivr.net/npm/redoc/bundles/redoc.standalone.js",
            )


def custom_openapi():
    """Custom OpenAPI schema"""
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="Yellow Mobile API",
        version=settings.API_VERSION,
        description=app.description,
        routes=app.routes,
    )

    # Add custom security definitions
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema


# Create the FastAPI app
app = create_application()
app.openapi = custom_openapi

# Export for use in other modules
__all__ = ["app", "create_application"]
