#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json
import time
import random
import string
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8069"
DB_NAME = "odoo"  # Update with your database name
API_BASE = f"{BASE_URL}/mobile"

# Test user credentials
TEST_EMAIL = "test_mobile_api@example.com"
TEST_PASSWORD = "test123"
TEST_NAME = "Test Mobile User"

# Storage for tokens and IDs
access_token = None
refresh_token = None
test_product_id = None
test_transaction_id = None
test_notification_id = None

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(80)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}\n")

def print_subheader(text):
    print(f"\n{Colors.OKBLUE}{Colors.BOLD}{text}{Colors.ENDC}")
    print(f"{Colors.OKBLUE}{'-' * 50}{Colors.ENDC}\n")

def print_success(text):
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")

def print_warning(text):
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")

def print_error(text):
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")

def print_json(data):
    print(json.dumps(data, indent=2))

def make_request(method, endpoint, data=None, params=None, auth=False, content_type="json"):
    """Make HTTP request to the API"""
    url = f"{API_BASE}{endpoint}"
    headers = {}
    
    if auth and access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    
    if content_type == "json":
        headers["Content-Type"] = "application/json"
        response = requests.request(
            method, 
            url, 
            json=data, 
            params=params, 
            headers=headers
        )
    else:
        response = requests.request(
            method, 
            url, 
            data=data, 
            params=params, 
            headers=headers
        )
    
    try:
        return response.json(), response.status_code
    except:
        return {"text": response.text}, response.status_code

def test_health_check():
    """Test the health check endpoint"""
    print_subheader("Testing Health Check")
    
    response, status_code = make_request("GET", "/health", auth=False)
    
    if status_code == 200 and response.get("status") == "healthy":
        print_success("Health check successful")
        return True
    else:
        print_error(f"Health check failed: {status_code}")
        print_json(response)
        return False

def setup_test_user():
    """Register a test user or login if already exists"""
    global access_token, refresh_token
    
    print_subheader("Setting up test user")
    
    # Try to login first
    login_data = {
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    }
    
    response, status_code = make_request("POST", "/auth/login", data=login_data)
    
    if status_code == 200 and response.get("success"):
        print_success("Logged in with existing test user")
        access_token = response["data"]["access_token"]
        refresh_token = response["data"]["refresh_token"]
        return True
    
    # If login fails, try to register
    register_data = {
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD,
        "name": TEST_NAME,
        "device_id": f"test_device_{int(time.time())}"
    }
    
    response, status_code = make_request("POST", "/auth/register", data=register_data)
    
    if status_code == 200 and response.get("success"):
        print_success("Registered new test user")
        access_token = response["data"]["access_token"]
        refresh_token = response["data"]["refresh_token"]
        return True
    else:
        print_error(f"Failed to setup test user: {status_code}")
        print_json(response)
        return False

def test_auth_endpoints():
    """Test authentication endpoints"""
    global access_token, refresh_token
    
    print_subheader("Testing Authentication Endpoints")
    
    # Test refresh token
    response, status_code = make_request(
        "POST", 
        "/auth/refresh", 
        data={"refresh_token": refresh_token}
    )
    
    if status_code == 200 and response.get("success"):
        print_success("Token refresh successful")
        access_token = response["data"]["access_token"]
    else:
        print_error(f"Token refresh failed: {status_code}")
        print_json(response)
    
    # Test logout (will need to login again after this)
    response, status_code = make_request("POST", "/auth/logout", auth=True)
    
    if status_code == 200 and response.get("success"):
        print_success("Logout successful")
    else:
        print_error(f"Logout failed: {status_code}")
        print_json(response)
    
    # Login again to get fresh tokens
    login_data = {
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    }
    
    response, status_code = make_request("POST", "/auth/login", data=login_data)
    
    if status_code == 200 and response.get("success"):
        print_success("Login successful after logout")
        access_token = response["data"]["access_token"]
        refresh_token = response["data"]["refresh_token"]
    else:
        print_error(f"Login after logout failed: {status_code}")
        print_json(response)

def test_product_endpoints():
    """Test product-related endpoints"""
    global test_product_id
    
    print_subheader("Testing Product Endpoints")
    
    # Get product categories
    response, status_code = make_request("GET", "/products/categories", auth=True)
    
    if status_code == 200 and response.get("success"):
        print_success("Get categories successful")
        categories = response["data"].get("categories", [])
        if categories:
            print(f"Found {len(categories)} categories")
    else:
        print_error(f"Get categories failed: {status_code}")
        print_json(response)
    
    # Get products
    response, status_code = make_request("GET", "/products", params={"limit": 5}, auth=True)
    
    if status_code == 200 and response.get("success"):
        print_success("Get products successful")
        products = response["data"].get("products", [])
        if products:
            print(f"Found {len(products)} products")
            test_product_id = products[0]["id"]
            print(f"Selected test product ID: {test_product_id}")
    else:
        print_error(f"Get products failed: {status_code}")
        print_json(response)
    
    if test_product_id:
        # Get product detail
        response, status_code = make_request("GET", f"/products/{test_product_id}", auth=True)
        
        if status_code == 200 and response.get("success"):
            print_success(f"Get product detail successful for ID {test_product_id}")
        else:
            print_error(f"Get product detail failed: {status_code}")
            print_json(response)
        
        # Toggle wishlist
        response, status_code = make_request("POST", f"/products/{test_product_id}/wishlist", auth=True)
        
        if status_code == 200 and response.get("success"):
            print_success("Add to wishlist successful")
            in_wishlist = response["data"].get("in_wishlist")
            print(f"Product in wishlist: {in_wishlist}")
        else:
            print_error(f"Add to wishlist failed: {status_code}")
            print_json(response)
        
        # Get wishlist
        response, status_code = make_request("GET", "/products/wishlist", auth=True)
        
        if status_code == 200 and response.get("success"):
            print_success("Get wishlist successful")
            wishlist_products = response["data"].get("products", [])
            print(f"Found {len(wishlist_products)} products in wishlist")
        else:
            print_error(f"Get wishlist failed: {status_code}")
            print_json(response)
    else:
        print_warning("Skipping product detail and wishlist tests (no product ID available)")
    
    # Test search suggestions
    response, status_code = make_request("GET", "/products/search/suggestions", params={"q": "test"}, auth=True)
    
    if status_code == 200 and response.get("success"):
        print_success("Search suggestions successful")
    else:
        print_error(f"Search suggestions failed: {status_code}")
        print_json(response)

def test_home_endpoints():
    """Test home page endpoints"""
    print_subheader("Testing Home Endpoints")
    
    # Get home data
    response, status_code = make_request("GET", "/home", auth=True)
    
    if status_code == 200 and response.get("success"):
        print_success("Get home data successful")
    else:
        print_error(f"Get home data failed: {status_code}")
        print_json(response)
    
    # Get trending searches
    response, status_code = make_request("GET", "/home/search/trending", auth=True)
    
    if status_code == 200 and response.get("success"):
        print_success("Get trending searches successful")
    else:
        print_error(f"Get trending searches failed: {status_code}")
        print_json(response)
    
    # Get recommendations
    response, status_code = make_request("GET", "/home/recommendations", auth=True)
    
    if status_code == 200 and response.get("success"):
        print_success("Get recommendations successful")
    else:
        print_error(f"Get recommendations failed: {status_code}")
        print_json(response)
    
    # Get deals
    response, status_code = make_request("GET", "/home/deals", auth=True)
    
    if status_code == 200 and response.get("success"):
        print_success("Get deals successful")
    else:
        print_error(f"Get deals failed: {status_code}")
        print_json(response)

def test_wallet_endpoints():
    """Test wallet endpoints"""
    global test_transaction_id
    
    print_subheader("Testing Wallet Endpoints")
    
    # Get wallet balance
    response, status_code = make_request("GET", "/wallet/balance", auth=True)
    
    if status_code == 200 and response.get("success"):
        print_success("Get wallet balance successful")
        balance = response["data"].get("balance", 0)
        print(f"Current balance: {balance}")
    else:
        print_error(f"Get wallet balance failed: {status_code}")
        print_json(response)
    
    # Add money to wallet
    add_money_data = {
        "amount": 100,
        "payment_method": "card",
        "description": "Test top-up"
    }
    
    response, status_code = make_request("POST", "/wallet/add-money", data=add_money_data, auth=True)
    
    if status_code == 200 and response.get("success"):
        print_success("Add money to wallet successful")
        test_transaction_id = response["data"].get("transaction_id")
        print(f"Transaction ID: {test_transaction_id}")
    else:
        print_error(f"Add money to wallet failed: {status_code}")
        print_json(response)
    
    # Get wallet transactions
    response, status_code = make_request("GET", "/wallet/transactions", params={"limit": 5}, auth=True)
    
    if status_code == 200 and response.get("success"):
        print_success("Get wallet transactions successful")
        transactions = response["data"].get("transactions", [])
        print(f"Found {len(transactions)} transactions")
        
        if transactions and not test_transaction_id:
            test_transaction_id = transactions[0]["id"]
    else:
        print_error(f"Get wallet transactions failed: {status_code}")
        print_json(response)
    
    if test_transaction_id:
        # Get transaction detail
        response, status_code = make_request("GET", f"/wallet/transaction/{test_transaction_id}", auth=True)
        
        if status_code == 200 and response.get("success"):
            print_success(f"Get transaction detail successful for ID {test_transaction_id}")
        else:
            print_error(f"Get transaction detail failed: {status_code}")
            print_json(response)
    else:
        print_warning("Skipping transaction detail test (no transaction ID available)")
    
    # Send money (to a non-existent user - should fail gracefully)
    send_money_data = {
        "recipient_email": f"nonexistent_{int(time.time())}@example.com",
        "amount": 10,
        "description": "Test send money"
    }
    
    response, status_code = make_request("POST", "/wallet/send-money", data=send_money_data, auth=True)
    
    if status_code == 404:
        print_success("Send money to non-existent user correctly failed with 404")
    elif status_code == 200:
        print_warning("Send money unexpectedly succeeded - check implementation")
    else:
        print_error(f"Send money failed with unexpected status: {status_code}")
        print_json(response)

def test_notification_endpoints():
    """Test notification endpoints"""
    global test_notification_id
    
    print_subheader("Testing Notification Endpoints")
    
    # Get notifications
    response, status_code = make_request("GET", "/notifications", params={"limit": 5}, auth=True)
    
    if status_code == 200 and response.get("success"):
        print_success("Get notifications successful")
        notifications = response["data"].get("notifications", [])
        print(f"Found {len(notifications)} notifications")
        
        if notifications:
            test_notification_id = notifications[0]["id"]
    else:
        print_error(f"Get notifications failed: {status_code}")
        print_json(response)
    
    # Send test notification
    response, status_code = make_request("POST", "/notifications/send-test", auth=True)
    
    if status_code == 200 and response.get("success"):
        print_success("Send test notification successful")
        test_notification_id = response["data"].get("notification_id")
        print(f"Test notification ID: {test_notification_id}")
    else:
        print_error(f"Send test notification failed: {status_code}")
        print_json(response)
    
    if test_notification_id:
        # Mark notification as read
        response, status_code = make_request("POST", f"/notifications/{test_notification_id}/read", auth=True)
        
        if status_code == 200 and response.get("success"):
            print_success(f"Mark notification read successful for ID {test_notification_id}")
        else:
            print_error(f"Mark notification read failed: {status_code}")
            print_json(response)
    else:
        print_warning("Skipping mark notification read test (no notification ID available)")
    
    # Mark all notifications as read
    response, status_code = make_request("POST", "/notifications/read-all", auth=True)
    
    if status_code == 200 and response.get("success"):
        print_success("Mark all notifications read successful")
    else:
        print_error(f"Mark all notifications read failed: {status_code}")
        print_json(response)
    
    # Get notification settings
    response, status_code = make_request("GET", "/notifications/settings", auth=True)
    
    if status_code == 200 and response.get("success"):
        print_success("Get notification settings successful")
    else:
        print_error(f"Get notification settings failed: {status_code}")
        print_json(response)
    
    # Update notification settings
    settings_data = {
        "push_notifications": True,
        "email_notifications": False,
        "order_updates": True,
        "promotions": False
    }
    
    response, status_code = make_request("POST", "/notifications/settings", data=settings_data, auth=True)
    
    if status_code == 200 and response.get("success"):
        print_success("Update notification settings successful")
    else:
        print_error(f"Update notification settings failed: {status_code}")
        print_json(response)
    
    # Register device token
    device_token_data = {
        "device_token": f"test_token_{int(time.time())}",
        "device_type": "android",
        "device_id": f"test_device_{int(time.time())}"
    }
    
    response, status_code = make_request("POST", "/notifications/register-device", data=device_token_data, auth=True)
    
    if status_code == 200 and response.get("success"):
        print_success("Register device token successful")
    else:
        print_error(f"Register device token failed: {status_code}")
        print_json(response)

def run_all_tests():
    """Run all API tests"""
    print_header("YELLOW MOBILE API TESTS")
    print(f"Base URL: {API_BASE}")
    print(f"Test User: {TEST_EMAIL}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test health check
    if not test_health_check():
        print_error("Health check failed. Aborting tests.")
        return
    
    # Setup test user
    if not setup_test_user():
        print_error("Failed to setup test user. Aborting tests.")
        return
    
    # Run all test groups
    test_auth_endpoints()
    test_product_endpoints()
    test_home_endpoints()
    test_wallet_endpoints()
    test_notification_endpoints()
    
    print_header("TEST SUMMARY")
    print("All tests completed. Check the output above for details.")

if __name__ == "__main__":
    run_all_tests()
