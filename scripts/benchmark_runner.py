#!/usr/bin/env python3
"""
Benchmark runner for Project Athena orchestrator.

Runs 20 standardized queries and collects detailed performance metrics.
Designed to measure before/after optimization improvements.
"""
import asyncio
import httpx
import time
import json
import redis
import argparse
import hashlib
from typing import List, Dict, Optional
from pathlib import Path
from datetime import datetime

# Orchestrator and Redis configuration
ORCHESTRATOR_URL = "http://192.168.10.167:8001"
REDIS_TEST_URL = "redis://192.168.10.181:6379/1"  # Isolated test database (db=1, production uses db=0)

# 20 standardized benchmark queries across 5 categories
BENCHMARK_QUERIES = [
    # Control queries (7) - Target: ≤3.5s
    {"query": "Turn on the office lights", "category": "control", "target_ms": 3500},
    {"query": "Turn off bedroom lights", "category": "control", "target_ms": 3500},
    {"query": "Set living room temperature to 72", "category": "control", "target_ms": 3500},
    {"query": "Lock the front door", "category": "control", "target_ms": 3500},
    {"query": "Turn on the kitchen fan", "category": "control", "target_ms": 3500},
    {"query": "Open the garage door", "category": "control", "target_ms": 3500},
    {"query": "Turn off all lights", "category": "control", "target_ms": 3500},

    # Knowledge queries (6) - Target: ≤5.5s
    {"query": "What's the weather like today?", "category": "knowledge", "target_ms": 5500},
    {"query": "When is the next Warriors game?", "category": "knowledge", "target_ms": 5500},
    {"query": "What's the forecast for this weekend?", "category": "knowledge", "target_ms": 5500},
    {"query": "Tell me about SFO airport delays", "category": "knowledge", "target_ms": 5500},
    {"query": "What's the temperature outside?", "category": "knowledge", "target_ms": 5500},
    {"query": "Are there any concerts this week?", "category": "knowledge", "target_ms": 5500},

    # Search queries (4) - Target: ≤5.5s
    {"query": "Find events near me this weekend", "category": "search", "target_ms": 5500},
    {"query": "Search for Warriors tickets", "category": "search", "target_ms": 5500},
    {"query": "Find concerts in San Francisco", "category": "search", "target_ms": 5500},
    {"query": "Look up restaurants nearby", "category": "search", "target_ms": 5500},

    # Complex reasoning (2) - Target: ≤8.0s
    {"query": "Should I bring an umbrella tomorrow?", "category": "reasoning", "target_ms": 8000},
    {"query": "Plan my day based on the weather", "category": "reasoning", "target_ms": 8000},

    # Status queries (1) - Target: ≤3.5s
    {"query": "What lights are currently on?", "category": "status", "target_ms": 3500},
]


def flush_redis_cache():
    """Flush test Redis database to ensure clean benchmark."""
    try:
        r = redis.from_url(REDIS_TEST_URL)
        r.flushdb()
        print("✓ Redis cache flushed")
        return True
    except Exception as e:
        print(f"⚠ Warning: Could not flush Redis: {e}")
        print("  Benchmark will continue, but cache may affect results")
        return False


async def run_single_query(
    client: httpx.AsyncClient,
    query_data: Dict,
    run_number: int
) -> Dict:
    """
    Run single query and collect comprehensive metrics.

    Args:
        client: HTTP client for API calls
        query_data: Query dictionary with query, category, target_ms
        run_number: Current run number (for logging)

    Returns:
        Dictionary with timing and result data
    """
    query = query_data["query"]
    category = query_data["category"]
    target_ms = query_data["target_ms"]

    print(f"  [{run_number}/20] {category:10s} | {query}")

    # Start timing
    start_time = time.time()

    try:
        response = await client.post(
            f"{ORCHESTRATOR_URL}/query",
            json={"query": query},
            timeout=30.0  # 30 second timeout
        )

        # Calculate total time
        total_time_ms = (time.time() - start_time) * 1000

        # Parse response
        if response.status_code == 200:
            result = response.json()

            # Extract metrics from response
            return {
                "query": query,
                "category": category,
                "target_ms": target_ms,
                "success": True,
                "total_time_ms": total_time_ms,
                "meets_target": total_time_ms <= target_ms,
                "intent": result.get("intent"),
                "confidence": result.get("confidence"),
                "response_length": len(result.get("response", "")),
                "node_timings": result.get("node_timings", {}),
                "cache_hits": result.get("cache_hits", []),
                "http_status": 200
            }
        else:
            return {
                "query": query,
                "category": category,
                "target_ms": target_ms,
                "success": False,
                "total_time_ms": total_time_ms,
                "meets_target": False,
                "error": f"HTTP {response.status_code}",
                "http_status": response.status_code
            }

    except asyncio.TimeoutError:
        total_time_ms = (time.time() - start_time) * 1000
        return {
            "query": query,
            "category": category,
            "target_ms": target_ms,
            "success": False,
            "total_time_ms": total_time_ms,
            "meets_target": False,
            "error": "Timeout (>30s)"
        }
    except Exception as e:
        total_time_ms = (time.time() - start_time) * 1000
        return {
            "query": query,
            "category": category,
            "target_ms": target_ms,
            "success": False,
            "total_time_ms": total_time_ms,
            "meets_target": False,
            "error": str(e)
        }


async def run_benchmark(flush_cache: bool = True, output_file: Optional[str] = None) -> Dict:
    """
    Run complete benchmark suite.

    Args:
        flush_cache: Whether to flush Redis cache before benchmark
        output_file: Optional output file path for results

    Returns:
        Complete benchmark results
    """
    print("\n" + "="*70)
    print("Project Athena Benchmark Runner")
    print("="*70)
    print(f"Orchestrator: {ORCHESTRATOR_URL}")
    print(f"Redis (test):  {REDIS_TEST_URL}")
    print(f"Queries:      {len(BENCHMARK_QUERIES)}")
    print(f"Flush cache:  {flush_cache}")
    print("="*70 + "\n")

    # Flush cache if requested
    if flush_cache:
        flush_redis_cache()
        print()

    # Run all queries
    results = []

    async with httpx.AsyncClient() as client:
        for i, query_data in enumerate(BENCHMARK_QUERIES, 1):
            result = await run_single_query(client, query_data, i)
            results.append(result)

            # Brief pause between queries
            await asyncio.sleep(0.5)

    # Calculate summary statistics
    total_queries = len(results)
    successful_queries = sum(1 for r in results if r["success"])
    failed_queries = total_queries - successful_queries

    meets_target = sum(1 for r in results if r.get("meets_target", False))
    total_time_ms = sum(r["total_time_ms"] for r in results)
    avg_time_ms = total_time_ms / total_queries if total_queries > 0 else 0

    # Category breakdown
    categories = {}
    for result in results:
        cat = result["category"]
        if cat not in categories:
            categories[cat] = {
                "count": 0,
                "successful": 0,
                "total_time_ms": 0,
                "meets_target": 0
            }
        categories[cat]["count"] += 1
        if result["success"]:
            categories[cat]["successful"] += 1
        categories[cat]["total_time_ms"] += result["total_time_ms"]
        if result.get("meets_target", False):
            categories[cat]["meets_target"] += 1

    # Calculate category averages
    for cat, stats in categories.items():
        stats["avg_time_ms"] = stats["total_time_ms"] / stats["count"]
        stats["target_rate"] = (stats["meets_target"] / stats["count"]) * 100

    # Build complete results object
    benchmark_results = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "orchestrator_url": ORCHESTRATOR_URL,
        "redis_url": REDIS_TEST_URL,
        "cache_flushed": flush_cache,
        "summary": {
            "total_queries": total_queries,
            "successful": successful_queries,
            "failed": failed_queries,
            "meets_target": meets_target,
            "target_rate": (meets_target / total_queries) * 100,
            "total_time_ms": total_time_ms,
            "avg_time_ms": avg_time_ms
        },
        "by_category": categories,
        "results": results
    }

    # Print summary
    print("\n" + "="*70)
    print("BENCHMARK SUMMARY")
    print("="*70)
    print(f"Total queries:     {total_queries}")
    print(f"Successful:        {successful_queries} ({(successful_queries/total_queries)*100:.1f}%)")
    print(f"Failed:            {failed_queries}")
    print(f"Meets target:      {meets_target} ({(meets_target/total_queries)*100:.1f}%)")
    print(f"Total time:        {total_time_ms:.0f}ms ({total_time_ms/1000:.1f}s)")
    print(f"Average time:      {avg_time_ms:.0f}ms")
    print()

    print("BY CATEGORY:")
    print("-" * 70)
    for cat, stats in sorted(categories.items()):
        print(f"{cat:12s} | {stats['count']:2d} queries | "
              f"avg: {stats['avg_time_ms']:6.0f}ms | "
              f"target: {stats['target_rate']:5.1f}%")
    print("="*70 + "\n")

    # Save to file if specified
    if output_file:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(benchmark_results, f, indent=2)

        print(f"✓ Results saved to: {output_path}\n")

    return benchmark_results


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run Project Athena orchestrator benchmarks"
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Output file for JSON results (default: results/benchmark-TIMESTAMP.json)"
    )
    parser.add_argument(
        "--no-flush",
        action="store_true",
        help="Don't flush Redis cache before benchmark (not recommended)"
    )

    args = parser.parse_args()

    # Determine output file
    if args.output:
        output_file = args.output
    else:
        timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
        output_file = f"results/benchmark-{timestamp}.json"

    # Run benchmark
    try:
        results = asyncio.run(run_benchmark(
            flush_cache=not args.no_flush,
            output_file=output_file
        ))

        # Exit with status based on success rate
        if results["summary"]["failed"] > 0:
            print("⚠ Some queries failed - check results for details")
            exit(1)
        else:
            print("✓ All queries successful!")
            exit(0)

    except KeyboardInterrupt:
        print("\n\nBenchmark interrupted by user")
        exit(130)
    except Exception as e:
        print(f"\n✗ Benchmark failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    main()
