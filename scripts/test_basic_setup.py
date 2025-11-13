#!/usr/bin/env python3
"""
Test basic setup for Gateway and Orchestrator services.
This validates that modules can be imported and basic initialization works.
"""

import sys
import os

# Add project to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_shared_utilities():
    """Test that shared utilities can be imported."""
    print("Testing shared utilities...")
    try:
        from shared.cache import CacheClient
        print("  ✓ CacheClient imported")

        # Check new methods exist
        cache = CacheClient()
        assert hasattr(cache, 'connect'), "CacheClient missing connect method"
        assert hasattr(cache, 'disconnect'), "CacheClient missing disconnect method"
        print("  ✓ CacheClient has connect/disconnect methods")

        from shared.ha_client import HomeAssistantClient
        print("  ✓ HomeAssistantClient imported")

        # Check health_check method exists
        assert hasattr(HomeAssistantClient, 'health_check'), "HomeAssistantClient missing health_check method"
        print("  ✓ HomeAssistantClient has health_check method")

        from shared.ollama_client import OllamaClient
        print("  ✓ OllamaClient imported")

        from shared.logging_config import configure_logging
        print("  ✓ Logging configuration imported")

        return True
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

def test_gateway_imports():
    """Test that gateway can be imported."""
    print("\nTesting gateway imports...")
    try:
        from gateway.main import (
            app,
            is_athena_query,
            ChatMessage,
            ChatCompletionRequest,
            ChatCompletionResponse
        )
        print("  ✓ Gateway app and models imported")

        # Test basic functionality
        msg = ChatMessage(role="user", content="Turn on the lights")
        result = is_athena_query([msg])
        assert result == True, "Should detect 'turn on' as Athena query"
        print("  ✓ Athena query detection works")

        return True
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

def test_orchestrator_imports():
    """Test that orchestrator can be imported."""
    print("\nTesting orchestrator imports...")
    try:
        from orchestrator.main import (
            app,
            IntentCategory,
            ModelTier,
            OrchestratorState,
            QueryRequest,
            QueryResponse,
            _pattern_based_classification
        )
        print("  ✓ Orchestrator app and models imported")

        # Test basic functionality
        intent = _pattern_based_classification("turn on the lights")
        assert intent == IntentCategory.CONTROL, "Should classify 'turn on' as CONTROL"
        print("  ✓ Pattern-based classification works")

        # Test state creation
        state = OrchestratorState(query="test query")
        assert state.query == "test query"
        assert state.mode == "owner"
        print("  ✓ Orchestrator state creation works")

        return True
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("Project Athena - Basic Setup Validation")
    print("=" * 60)

    tests_passed = 0
    tests_total = 3

    if test_shared_utilities():
        tests_passed += 1

    if test_gateway_imports():
        tests_passed += 1

    if test_orchestrator_imports():
        tests_passed += 1

    print("\n" + "=" * 60)
    if tests_passed == tests_total:
        print(f"✅ All {tests_total} tests passed! Services are ready to deploy.")
        return 0
    else:
        print(f"⚠️  {tests_passed}/{tests_total} tests passed. Some issues need fixing.")
        return 1

if __name__ == "__main__":
    exit(main())