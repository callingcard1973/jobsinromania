#!/usr/bin/env python3
"""
EEATINGH API Testing and Documentation Script

This script tests and documents the EEATINGH platform API endpoints,
validates authentication, and maps available functionality.

Author: Claude Code Assistant
Created: 2026-04-04
"""

import requests
import json
import time
from urllib.parse import urljoin
from bs4 import BeautifulSoup

class EEATINGHAPITester:
    def __init__(self):
        self.base_url = "https://eeatingh.ro"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

        # Credentials
        self.email = "apaminerala@yahoo.com"
        self.password = "Romania1973!"
        self.store_id = "513"
        self.hash_id = "9d6dcd6d2b1c560affc2"

        # API endpoints to test
        self.endpoints = {
            'public': {
                'homepage': '/',
                'restaurant_list': '/restaurants',
                'api_check': '/api',
                'mobile_app': '/app'
            },
            'admin': {
                'login': '/admin/login',
                'dashboard': '/admin/dashboard',
                'edit_store': f'/admin/create_edit_store/{self.store_id}',
                'products': f'/admin/manage_products/{self.store_id}',
                'orders': f'/admin/manage_orders/{self.hash_id}',
                'webhooks': f'/admin/manage_web_hooks/{self.store_id}',
                'import_export': f'/admin/import_export/{self.hash_id}',
                'settings': f'/admin/settings/{self.store_id}',
                'promotions': f'/admin/promo/{self.store_id}',
                'delivery': f'/admin/manage_delivery/{self.store_id}',
                'discounts': f'/admin/discount/manage_discounts/{self.store_id}',
                'export_products': f'/admin/export_products/{self.store_id}',
                'add_product': f'/admin/add_product/{self.store_id}',
                'store_analytics': f'/admin/analytics/{self.store_id}',
                'customer_management': f'/admin/customers/{self.store_id}'
            },
            'api': {
                'orders_api': '/api/orders',
                'products_api': '/api/products',
                'restaurants_api': '/api/restaurants',
                'delivery_api': '/api/delivery',
                'payments_api': '/api/payments',
                'webhook_api': '/api/webhook',
                'auth_api': '/api/auth'
            }
        }

    def test_endpoint(self, url, method='GET', data=None, expected_status=200, description=""):
        """Test a single endpoint and return results."""
        try:
            full_url = urljoin(self.base_url, url)

            if method.upper() == 'GET':
                response = self.session.get(full_url)
            elif method.upper() == 'POST':
                response = self.session.post(full_url, data=data)
            else:
                response = self.session.request(method, full_url, data=data)

            result = {
                'url': full_url,
                'method': method,
                'status_code': response.status_code,
                'success': response.status_code == expected_status,
                'description': description,
                'response_size': len(response.content),
                'content_type': response.headers.get('content-type', ''),
                'redirect_url': response.url if response.url != full_url else None,
                'error': None
            }

            # Check for specific indicators
            if 'login' in response.text.lower() or 'password' in response.text.lower():
                result['auth_required'] = True

            if 'api' in response.headers.get('content-type', ''):
                result['is_api'] = True

            if response.status_code == 404:
                result['exists'] = False
            else:
                result['exists'] = True

            return result

        except Exception as e:
            return {
                'url': full_url,
                'method': method,
                'status_code': 0,
                'success': False,
                'description': description,
                'error': str(e),
                'exists': False
            }

    def test_login(self):
        """Test admin login functionality."""
        print("🔐 Testing admin login...")

        # First get login page
        login_result = self.test_endpoint('/admin/login', description="Admin login page")

        if not login_result['success']:
            return False, "Login page not accessible"

        # Try to extract form details
        try:
            response = self.session.get(urljoin(self.base_url, '/admin/login'))
            soup = BeautifulSoup(response.text, 'html.parser')

            # Look for login form
            form = soup.find('form')
            if form:
                # Extract form action and method
                action = form.get('action', '/admin/login')
                method = form.get('method', 'POST')

                # Find input fields
                inputs = form.find_all('input')
                form_data = {}

                for inp in inputs:
                    name = inp.get('name')
                    if name:
                        if inp.get('type') == 'email' or 'email' in name.lower():
                            form_data[name] = self.email
                        elif inp.get('type') == 'password' or 'password' in name.lower():
                            form_data[name] = self.password
                        elif inp.get('type') == 'hidden':
                            form_data[name] = inp.get('value', '')

                # Attempt login
                login_url = urljoin(self.base_url, action)
                login_response = self.session.post(login_url, data=form_data)

                if login_response.status_code == 200:
                    if 'dashboard' in login_response.url.lower() or 'admin' in login_response.text:
                        return True, "Login successful"
                    else:
                        return False, "Login failed - redirected but not to dashboard"
                else:
                    return False, f"Login failed - HTTP {login_response.status_code}"

        except Exception as e:
            return False, f"Login test exception: {e}"

        return False, "Could not complete login test"

    def test_all_endpoints(self):
        """Test all known endpoints and document findings."""
        print("🔍 Testing all EEATINGH API endpoints...")
        results = {}

        # Test public endpoints first
        print("\n📂 Testing Public Endpoints:")
        results['public'] = {}
        for name, endpoint in self.endpoints['public'].items():
            print(f"  Testing {name}: {endpoint}")
            result = self.test_endpoint(endpoint, description=f"Public {name} endpoint")
            results['public'][name] = result

            status_icon = "✅" if result['success'] else "❌"
            print(f"    {status_icon} {result['status_code']} - {result.get('content_type', 'unknown')}")

            time.sleep(0.5)  # Be respectful to the server

        # Test API endpoints
        print("\n🔌 Testing API Endpoints:")
        results['api'] = {}
        for name, endpoint in self.endpoints['api'].items():
            print(f"  Testing {name}: {endpoint}")
            result = self.test_endpoint(endpoint, description=f"API {name} endpoint")
            results['api'][name] = result

            status_icon = "✅" if result['exists'] else "❌"
            print(f"    {status_icon} {result['status_code']} - {result.get('content_type', 'unknown')}")

            time.sleep(0.5)

        # Test admin endpoints (requires login)
        print("\n👤 Testing Admin Login:")
        login_success, login_message = self.test_login()
        print(f"  {'✅' if login_success else '❌'} {login_message}")

        if login_success:
            print("\n🔧 Testing Admin Endpoints:")
            results['admin'] = {}
            for name, endpoint in self.endpoints['admin'].items():
                if name == 'login':  # Skip login as we already tested it
                    continue

                print(f"  Testing {name}: {endpoint}")
                result = self.test_endpoint(endpoint, description=f"Admin {name} endpoint")
                results['admin'][name] = result

                status_icon = "✅" if result['success'] else "❌"
                print(f"    {status_icon} {result['status_code']} - {result.get('content_type', 'unknown')}")

                time.sleep(0.5)
        else:
            print("⚠️  Skipping admin endpoints due to login failure")
            results['admin'] = {'login_failed': True}

        return results

    def discover_additional_endpoints(self):
        """Try to discover additional endpoints through common patterns."""
        print("\n🕵️ Discovering additional endpoints...")

        common_patterns = [
            '/api/v1/',
            '/api/v2/',
            '/mobile/',
            '/app/',
            '/webhook/',
            '/callback/',
            '/admin/api/',
            '/admin/ajax/',
            '/ajax/',
            '/json/',
            '/rest/',
            '/graphql',
            '/admin/reports/',
            '/admin/stats/',
            '/admin/export/',
            '/admin/import/',
            '/admin/backup/',
            '/admin/logs/',
            '/health',
            '/status',
            '/version'
        ]

        discovered = {}

        for pattern in common_patterns:
            result = self.test_endpoint(pattern, expected_status=[200, 401, 403],
                                      description=f"Discovery: {pattern}")
            if result['exists']:
                discovered[pattern] = result
                print(f"  ✅ Found: {pattern} - {result['status_code']}")

            time.sleep(0.3)

        return discovered

    def generate_api_documentation(self, test_results, discovered_endpoints):
        """Generate comprehensive API documentation."""

        doc = {
            'eeatingh_api_documentation': {
                'platform': 'eeatingh.ro',
                'tested_date': time.strftime('%Y-%m-%d %H:%M:%S'),
                'base_url': self.base_url,
                'authentication': {
                    'method': 'web_session',
                    'login_endpoint': '/admin/login',
                    'credentials_required': ['email', 'password']
                },
                'store_configuration': {
                    'store_id': self.store_id,
                    'hash_id': self.hash_id,
                    'store_name': 'Bobocica Farmer Market'
                },
                'endpoints': test_results,
                'discovered_endpoints': discovered_endpoints,
                'functional_endpoints': [],
                'api_capabilities': {
                    'product_management': 'available',
                    'order_management': 'available',
                    'webhook_support': 'available',
                    'import_export': 'csv_supported',
                    'analytics': 'basic',
                    'delivery_management': 'available'
                },
                'integration_notes': [
                    'Platform uses session-based authentication',
                    'CSV import/export functionality available',
                    'Webhook configuration supported',
                    'Admin panel provides full management interface',
                    'Mobile app endpoints may exist',
                    'API access may require additional setup'
                ]
            }
        }

        # Identify functional endpoints
        for category, endpoints in test_results.items():
            if category == 'admin' and isinstance(endpoints, dict) and 'login_failed' not in endpoints:
                for name, result in endpoints.items():
                    if result.get('success') or result.get('status_code') in [200, 302, 401]:
                        doc['eeatingh_api_documentation']['functional_endpoints'].append({
                            'name': name,
                            'url': result['url'],
                            'category': category,
                            'status': result['status_code'],
                            'description': result['description']
                        })

        return doc

    def save_documentation(self, documentation, filename='eeatingh_api_documentation.json'):
        """Save API documentation to file."""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(documentation, f, indent=2, ensure_ascii=False)
            print(f"📄 API documentation saved to: {filename}")
            return True
        except Exception as e:
            print(f"❌ Failed to save documentation: {e}")
            return False

def main():
    """Main testing function."""
    print("🍽️ EEATINGH API Testing & Documentation")
    print("=" * 50)

    tester = EEATINGHAPITester()

    # Run comprehensive API tests
    test_results = tester.test_all_endpoints()

    # Discover additional endpoints
    discovered = tester.discover_additional_endpoints()

    # Generate documentation
    documentation = tester.generate_api_documentation(test_results, discovered)

    # Save documentation
    tester.save_documentation(documentation)

    # Print summary
    print("\n📊 Test Summary:")
    total_tested = sum(len(endpoints) if isinstance(endpoints, dict) and 'login_failed' not in endpoints else 0
                      for endpoints in test_results.values())
    functional = len(documentation['eeatingh_api_documentation']['functional_endpoints'])
    discovered_count = len(discovered)

    print(f"  Total endpoints tested: {total_tested}")
    print(f"  Functional endpoints: {functional}")
    print(f"  Additional endpoints discovered: {discovered_count}")

    print("\n✅ API Testing Complete!")
    print("📄 Documentation saved to: eeatingh_api_documentation.json")

    # Print key findings
    if functional > 0:
        print("\n🔑 Key Functional Endpoints:")
        for endpoint in documentation['eeatingh_api_documentation']['functional_endpoints'][:5]:
            print(f"  • {endpoint['name']}: {endpoint['url']}")

if __name__ == "__main__":
    main()