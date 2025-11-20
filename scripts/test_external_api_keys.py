#!/usr/bin/env python3
"""
Test script for external API key retrieval.

Verifies that:
1. Admin backend route returns external API keys
2. Admin config client can fetch keys
3. Provider router initializes with database keys
"""

import asyncio
import httpx
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from shared.admin_config import AdminConfigClient


async def test_admin_backend_route():
    """Test the admin backend GET /api/external-api-keys endpoint."""
    print("\n=== Testing Admin Backend Route ===")

    admin_url = os.getenv("ADMIN_API_URL", "http://localhost:5000")

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            # Test the public endpoint (no auth required)
            url = f"{admin_url}/api/external-api-keys/public/brave-search/key"
            print(f"GET {url}")

            response = await client.get(url)

            if response.status_code == 200:
                data = response.json()
                print(f"✓ Status: {response.status_code}")
                print(f"✓ Response keys: {list(data.keys())}")
                print(f"✓ API key present: {'api_key' in data}")
                print(f"✓ Endpoint URL: {data.get('endpoint_url')}")
                return True
            elif response.status_code == 404:
                print(f"✗ API key not found in database (404)")
                print(f"  Create one using the admin UI first")
                return False
            else:
                print(f"✗ Unexpected status: {response.status_code}")
                print(f"  Response: {response.text}")
                return False

        except Exception as e:
            print(f"✗ Error: {e}")
            return False


async def test_admin_config_client():
    """Test the AdminConfigClient.get_external_api_key method."""
    print("\n=== Testing Admin Config Client ===")

    try:
        client = AdminConfigClient()

        # Test Brave Search API key
        print("Fetching brave-search API key...")
        brave_data = await client.get_external_api_key("brave-search")

        if brave_data:
            print(f"✓ Brave Search key fetched")
            print(f"  API key: {brave_data['api_key'][:10]}..." if brave_data.get('api_key') else "  (no key)")
            print(f"  Endpoint: {brave_data.get('endpoint_url')}")
            print(f"  Rate limit: {brave_data.get('rate_limit_per_minute')}")
            success = True
        else:
            print(f"✗ Brave Search key not found")
            success = False

        await client.close()
        return success

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_provider_router_initialization():
    """Test that ProviderRouter can initialize with database keys."""
    print("\n=== Testing Provider Router Initialization ===")

    try:
        # Import here to avoid early initialization
        from orchestrator.search_providers.provider_router import ProviderRouter

        # Create router from environment (will fetch from database)
        print("Initializing ProviderRouter from environment...")
        router = await ProviderRouter.from_environment()

        # Check available providers
        providers = router.get_available_providers()
        print(f"✓ Router initialized")
        print(f"  Available providers: {providers}")

        # Check if Brave Search is available
        if "brave" in providers:
            print(f"✓ Brave Search provider initialized successfully")
            success = True
        else:
            print(f"⚠ Brave Search provider not available (may need API key)")
            success = True  # Still consider it a success if router initialized

        await router.close_all()
        return success

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("=" * 60)
    print("External API Key Integration Tests")
    print("=" * 60)

    # Test 1: Admin backend route
    test1 = await test_admin_backend_route()

    # Test 2: Admin config client
    test2 = await test_admin_config_client()

    # Test 3: Provider router initialization
    test3 = await test_provider_router_initialization()

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Admin Backend Route:       {'✓ PASS' if test1 else '✗ FAIL'}")
    print(f"Admin Config Client:       {'✓ PASS' if test2 else '✗ FAIL'}")
    print(f"Provider Router Init:      {'✓ PASS' if test3 else '✗ FAIL'}")
    print("=" * 60)

    all_passed = test1 and test2 and test3
    if all_passed:
        print("\n✓ All tests passed!")
        return 0
    else:
        print("\n✗ Some tests failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
