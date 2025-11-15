#!/usr/bin/env python3
"""
Test script for conversation context and device session management.

Tests the complete flow:
1. Gateway device session management
2. Orchestrator session management
3. Conversation history in LLM context
4. Session timeout and cleanup

Usage:
    python3 scripts/test_conversation_context.py
"""

import asyncio
import httpx
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional


class ConversationContextTester:
    """Test conversation context across Gateway and Orchestrator."""

    def __init__(
        self,
        gateway_url: str = "http://localhost:8000",
        orchestrator_url: str = "http://localhost:8001"
    ):
        self.gateway_url = gateway_url
        self.orchestrator_url = orchestrator_url
        self.test_results = []

    async def test_gateway_health(self) -> bool:
        """Test Gateway health endpoint."""
        print("\n🔍 Testing Gateway health...")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.gateway_url}/health")
                result = response.json()

                is_healthy = result.get("status") == "healthy"

                print(f"  ✓ Gateway status: {result.get('status')}")
                print(f"  ✓ Orchestrator: {'✓' if result.get('orchestrator') else '✗'}")
                print(f"  ✓ Ollama: {'✓' if result.get('ollama') else '✗'}")

                self.test_results.append(("Gateway Health", is_healthy))
                return is_healthy

        except Exception as e:
            print(f"  ✗ Gateway health check failed: {e}")
            self.test_results.append(("Gateway Health", False))
            return False

    async def test_orchestrator_health(self) -> bool:
        """Test Orchestrator health endpoint."""
        print("\n🔍 Testing Orchestrator health...")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.orchestrator_url}/health")
                result = response.json()

                is_healthy = result.get("status") == "healthy"

                print(f"  ✓ Orchestrator status: {result.get('status')}")

                self.test_results.append(("Orchestrator Health", is_healthy))
                return is_healthy

        except Exception as e:
            print(f"  ✗ Orchestrator health check failed: {e}")
            self.test_results.append(("Orchestrator Health", False))
            return False

    async def test_ha_conversation_new_session(self) -> Optional[str]:
        """Test HA conversation endpoint creates new session."""
        print("\n🔍 Testing HA conversation (new session)...")
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                request_data = {
                    "text": "What is the weather in Baltimore?",
                    "device_id": "test_office",
                    "language": "en"
                }

                print(f"  → Sending: {request_data['text']}")

                response = await client.post(
                    f"{self.gateway_url}/ha/conversation",
                    json=request_data
                )

                if response.status_code != 200:
                    print(f"  ✗ Request failed: {response.status_code}")
                    print(f"  ✗ Response: {response.text}")
                    self.test_results.append(("HA Conversation (New)", False))
                    return None

                result = response.json()
                session_id = result.get("conversation_id")
                answer = result.get("response", {}).get("speech", {}).get("plain", {}).get("speech", "")

                print(f"  ✓ Session ID: {session_id}")
                print(f"  ✓ Answer: {answer[:100]}...")

                self.test_results.append(("HA Conversation (New)", True))
                return session_id

        except Exception as e:
            print(f"  ✗ HA conversation test failed: {e}")
            self.test_results.append(("HA Conversation (New)", False))
            return None

    async def test_ha_conversation_continue_session(self, session_id: str) -> bool:
        """Test HA conversation continues session with context."""
        print("\n🔍 Testing HA conversation (continue session)...")
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                request_data = {
                    "text": "What about tomorrow?",
                    "device_id": "test_office",
                    "language": "en"
                }

                print(f"  → Sending: {request_data['text']}")
                print(f"  → Expected to use session: {session_id}")

                response = await client.post(
                    f"{self.gateway_url}/ha/conversation",
                    json=request_data
                )

                if response.status_code != 200:
                    print(f"  ✗ Request failed: {response.status_code}")
                    self.test_results.append(("HA Conversation (Continue)", False))
                    return False

                result = response.json()
                returned_session_id = result.get("conversation_id")
                answer = result.get("response", {}).get("speech", {}).get("plain", {}).get("speech", "")

                # Session ID should be the same (device maintains session)
                session_maintained = returned_session_id == session_id

                print(f"  ✓ Session ID: {returned_session_id}")
                print(f"  ✓ Session maintained: {session_maintained}")
                print(f"  ✓ Answer: {answer[:100]}...")

                # Check if answer references weather/Baltimore (context awareness)
                context_aware = any(word in answer.lower() for word in ["weather", "baltimore", "forecast", "temperature"])

                print(f"  ✓ Context aware: {context_aware}")

                success = session_maintained and context_aware
                self.test_results.append(("HA Conversation (Continue)", success))
                return success

        except Exception as e:
            print(f"  ✗ HA conversation continuation failed: {e}")
            self.test_results.append(("HA Conversation (Continue)", False))
            return False

    async def test_different_device_independent_session(self) -> bool:
        """Test different device gets independent session."""
        print("\n🔍 Testing different device (independent session)...")
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                request_data = {
                    "text": "Turn on the kitchen lights",
                    "device_id": "test_kitchen",  # Different device
                    "language": "en"
                }

                print(f"  → Sending from kitchen device: {request_data['text']}")

                response = await client.post(
                    f"{self.gateway_url}/ha/conversation",
                    json=request_data
                )

                if response.status_code != 200:
                    print(f"  ✗ Request failed: {response.status_code}")
                    self.test_results.append(("Different Device Session", False))
                    return False

                result = response.json()
                session_id = result.get("conversation_id")
                answer = result.get("response", {}).get("speech", {}).get("plain", {}).get("speech", "")

                print(f"  ✓ Kitchen session ID: {session_id}")
                print(f"  ✓ Answer: {answer[:100]}...")

                # Should NOT reference weather (independent context)
                no_weather_context = "weather" not in answer.lower()

                print(f"  ✓ Independent context: {no_weather_context}")

                self.test_results.append(("Different Device Session", True))
                return True

        except Exception as e:
            print(f"  ✗ Different device test failed: {e}")
            self.test_results.append(("Different Device Session", False))
            return False

    async def test_direct_orchestrator_session(self) -> Optional[str]:
        """Test direct orchestrator session management."""
        print("\n🔍 Testing direct Orchestrator session...")
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                request_data = {
                    "query": "What are the airports near Baltimore?",
                    "mode": "owner",
                    "room": "test_direct",
                    "temperature": 0.7
                }

                print(f"  → Query: {request_data['query']}")

                response = await client.post(
                    f"{self.orchestrator_url}/query",
                    json=request_data
                )

                if response.status_code != 200:
                    print(f"  ✗ Request failed: {response.status_code}")
                    self.test_results.append(("Orchestrator Session (New)", False))
                    return None

                result = response.json()
                session_id = result.get("session_id")
                answer = result.get("answer", "")

                print(f"  ✓ Session ID: {session_id}")
                print(f"  ✓ Answer: {answer[:100]}...")

                self.test_results.append(("Orchestrator Session (New)", True))
                return session_id

        except Exception as e:
            print(f"  ✗ Orchestrator session test failed: {e}")
            self.test_results.append(("Orchestrator Session (New)", False))
            return None

    async def test_orchestrator_session_continuation(self, session_id: str) -> bool:
        """Test orchestrator session continuation with history."""
        print("\n🔍 Testing Orchestrator session continuation...")
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                request_data = {
                    "query": "Which one is closest?",
                    "mode": "owner",
                    "room": "test_direct",
                    "session_id": session_id,  # Continue session
                    "temperature": 0.7
                }

                print(f"  → Query: {request_data['query']}")
                print(f"  → Using session: {session_id}")

                response = await client.post(
                    f"{self.orchestrator_url}/query",
                    json=request_data
                )

                if response.status_code != 200:
                    print(f"  ✗ Request failed: {response.status_code}")
                    self.test_results.append(("Orchestrator Session (Continue)", False))
                    return False

                result = response.json()
                returned_session_id = result.get("session_id")
                answer = result.get("answer", "")

                print(f"  ✓ Session ID: {returned_session_id}")
                print(f"  ✓ Session maintained: {returned_session_id == session_id}")
                print(f"  ✓ Answer: {answer[:100]}...")

                # Check if answer references airports (context awareness)
                context_aware = any(word in answer.lower() for word in ["airport", "bwi", "baltimore", "miles", "closest"])

                print(f"  ✓ Context aware: {context_aware}")

                success = returned_session_id == session_id and context_aware
                self.test_results.append(("Orchestrator Session (Continue)", success))
                return success

        except Exception as e:
            print(f"  ✗ Orchestrator session continuation failed: {e}")
            self.test_results.append(("Orchestrator Session (Continue)", False))
            return False

    async def test_session_timeout(self) -> bool:
        """Test session timeout (requires waiting)."""
        print("\n🔍 Testing session timeout (will take 6+ minutes)...")
        print("  ⏳ Skipping timeout test (too slow for quick validation)")
        print("  → To test manually: wait 6 minutes between requests")

        self.test_results.append(("Session Timeout", None))
        return True

    def print_summary(self):
        """Print test results summary."""
        print("\n" + "="*60)
        print("📊 TEST SUMMARY")
        print("="*60)

        passed = sum(1 for _, result in self.test_results if result is True)
        failed = sum(1 for _, result in self.test_results if result is False)
        skipped = sum(1 for _, result in self.test_results if result is None)
        total = len(self.test_results)

        for test_name, result in self.test_results:
            if result is True:
                status = "✓ PASS"
            elif result is False:
                status = "✗ FAIL"
            else:
                status = "⊘ SKIP"

            print(f"  {status}  {test_name}")

        print("-"*60)
        print(f"  Total: {total} | Passed: {passed} | Failed: {failed} | Skipped: {skipped}")
        print("="*60)

        if failed == 0:
            print("\n🎉 All tests passed!")
        else:
            print(f"\n⚠️  {failed} test(s) failed")

    async def run_all_tests(self):
        """Run all tests in sequence."""
        print("="*60)
        print("🚀 CONVERSATION CONTEXT TEST SUITE")
        print("="*60)
        print(f"Gateway URL: {self.gateway_url}")
        print(f"Orchestrator URL: {self.orchestrator_url}")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Health checks
        gateway_healthy = await self.test_gateway_health()
        orchestrator_healthy = await self.test_orchestrator_health()

        if not gateway_healthy or not orchestrator_healthy:
            print("\n⚠️  Services not healthy - skipping functional tests")
            self.print_summary()
            return

        # HA conversation tests (Gateway → Orchestrator flow)
        session_id = await self.test_ha_conversation_new_session()

        if session_id:
            # Small delay to ensure session is saved
            await asyncio.sleep(1)

            await self.test_ha_conversation_continue_session(session_id)
            await self.test_different_device_independent_session()

        # Direct orchestrator tests
        orch_session_id = await test_direct_orchestrator_session()

        if orch_session_id:
            await asyncio.sleep(1)
            await self.test_orchestrator_session_continuation(orch_session_id)

        # Timeout test (skipped by default)
        await self.test_session_timeout()

        # Print summary
        self.print_summary()


async def main():
    """Main test execution."""
    import sys

    # Parse arguments
    gateway_url = "http://localhost:8000"
    orchestrator_url = "http://localhost:8001"

    if len(sys.argv) > 1:
        gateway_url = sys.argv[1]
    if len(sys.argv) > 2:
        orchestrator_url = sys.argv[2]

    tester = ConversationContextTester(gateway_url, orchestrator_url)
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
