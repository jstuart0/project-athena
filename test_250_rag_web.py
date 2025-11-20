#!/usr/bin/env python3
"""
250-Question RAG + Web Search Flow Test

Focused test suite for questions that MUST use either:
1. RAG services (weather, sports, airports)
2. Web search (current events, recent news, time-sensitive data)
3. Both (RAG + web search supplement)

This tests the core principle: "Use RAG when appropriate, web search for everything else"
"""

import json
import asyncio
import httpx
import time
from typing import List, Dict, Any
from datetime import datetime

# Service URLs
GATEWAY_URL = "http://192.168.10.167:8000"
ORCHESTRATOR_URL = "http://192.168.10.167:8001"

# Use orchestrator directly
USE_ORCHESTRATOR_DIRECT = True

# 250 questions designed to trigger RAG or Web Search
QUESTIONS = [
    # ===== WEATHER QUERIES (50 questions) =====
    # These MUST use Weather RAG

    # Current weather
    "What's the weather today?",
    "What's the weather in Baltimore?",
    "What's the temperature outside?",
    "Is it sunny today?",
    "What's the humidity right now?",
    "What's the wind speed?",
    "How cold is it outside?",
    "What's the heat index?",
    "What's the UV index today?",
    "Is it foggy outside?",
    "What's the dew point?",
    "What's the air quality?",
    "What's the feels-like temperature?",
    "What's the barometric pressure?",
    "Is it cloudy today?",
    "What's the wind direction?",
    "Is it raining right now?",
    "Is the weather nice today?",
    "Is it humid outside?",

    # Forecast (should use forecast endpoint)
    "Will it rain tomorrow?",
    "Is it going to snow this week?",
    "What's the forecast for this weekend?",
    "Is there a storm coming?",
    "What's the weather forecast for tonight?",
    "Is it going to be windy?",
    "What's the chance of rain?",
    "When will the rain stop?",
    "Is it hotter than yesterday?",
    "Will there be thunderstorms?",
    "What's the low temperature tonight?",
    "What's the high temperature tomorrow?",
    "Is there a frost warning?",
    "Is it going to be clear tonight?",
    "When will the snow start?",
    "Is there a weather advisory?",

    # City-specific (test entity extraction)
    "What's the weather in Chicago?",
    "What's the weather in Seattle?",
    "What's the weather in Denver?",
    "What's the weather in San Francisco?",
    "What's the weather in Dallas?",
    "What's the weather in New York?",
    "What's the weather in Los Angeles?",
    "What's the weather in Miami?",
    "What's the weather in Boston?",
    "What's the weather in Atlanta?",
    "What's the weather in Phoenix?",

    # ===== SPORTS QUERIES (50 questions) =====
    # These MUST use Sports RAG + Web Search fallback

    # Current scores (time-sensitive - should trigger web search)
    "What's the Ravens score?",
    "Who won the Ravens game?",
    "Did the Ravens win?",
    "What's the Orioles score?",
    "Did the Orioles win yesterday?",
    "What's the Lakers score?",
    "Did the Lakers win?",
    "What's the Warriors game score?",
    "Who won the Super Bowl?",
    "What's the Seahawks score?",
    "Did the Bills win?",
    "What's the Penguins score?",
    "Did the Capitals win?",
    "What's the Cowboys score?",
    "Did the Patriots win?",
    "What's the Chiefs score?",
    "Did the 49ers win?",
    "What's the Eagles score?",
    "Did the Packers win?",
    "What's the Steelers score?",

    # Schedules (should use Sports RAG)
    "When do the Ravens play next?",
    "What time is the Ravens game?",
    "Ravens schedule this week",
    "When is the Orioles game today?",
    "Who's playing tonight in NFL?",
    "NBA scores today",
    "Who's playing Monday Night Football?",
    "MLB standings",
    "NFL scores this week",
    "NBA playoff schedule",

    # Team queries
    "How are the Orioles doing?",
    "Ravens playoff chances",
    "Who's leading the NBA?",
    "Did the Yankees win?",
    "What's the Red Sox score?",
    "Who's winning the World Series?",
    "NHL scores today",
    "Who won the Stanley Cup?",
    "Who's the MVP this season?",
    "Who won the basketball game?",
    "What's the score of the hockey game?",
    "Did the Dodgers win?",
    "What's the Cubs score?",
    "Who's playing in the playoffs?",
    "Did the Rams win?",
    "Who's playing college football today?",
    "What's the Alabama score?",
    "Did Ohio State win?",
    "Who won March Madness?",

    # ===== AIRPORT QUERIES (30 questions) =====
    # These MUST use Airports RAG

    "Are there delays at BWI?",
    "BWI flight status",
    "Any delays at Baltimore airport?",
    "Is BWI airport open?",
    "Flight delays at BWI?",
    "Are there cancellations at BWI?",
    "What's the wait time at BWI security?",
    "Is DCA airport delayed?",
    "Any issues at Reagan airport?",
    "IAD flight status",
    "Are there delays at Dulles?",
    "Is JFK airport delayed?",
    "Flight status for LaGuardia",
    "Are there delays at O'Hare?",
    "Is ATL airport open?",
    "Any delays at Atlanta airport?",
    "Flight status for Miami airport",
    "Are there delays at LAX?",
    "Is SFO airport delayed?",
    "Flight delays at Denver?",
    "Is SeaTac airport open?",
    "Any delays at Phoenix airport?",
    "Is Dallas airport delayed?",
    "Flight status for Houston",
    "Are there delays at Newark?",
    "Is Boston airport open?",
    "Any cancellations at Philadelphia?",
    "Flight delays at Charlotte?",
    "Is Orlando airport delayed?",
    "Any issues at Tampa airport?",

    # ===== CURRENT EVENTS / NEWS (30 questions) =====
    # These MUST use Web Search (time-sensitive)

    "What's in the news today?",
    "What happened today?",
    "What's the latest news?",
    "What are today's headlines?",
    "What's happening in the world?",
    "What's the breaking news?",
    "What happened yesterday?",
    "What's trending today?",
    "What's the top story today?",
    "What are the current events?",
    "What's the latest on the election?",
    "What's the news in technology?",
    "What's the latest in sports news?",
    "What happened in the stock market today?",
    "What's the Dow Jones at?",
    "What's the S&P 500 today?",
    "What's the price of Bitcoin?",
    "What's the latest on climate change?",
    "What's the news about AI?",
    "What's happening in Ukraine?",
    "What's the latest on the economy?",
    "What are gas prices today?",
    "What's the unemployment rate?",
    "What's the inflation rate?",
    "What's happening in Congress?",
    "What's the latest Supreme Court decision?",
    "What's the news about NASA?",
    "What's happening with SpaceX?",
    "What's the latest iPhone?",
    "What are the Oscar nominations?",

    # ===== TIME-SENSITIVE QUERIES (40 questions) =====
    # These should trigger web search due to time indicators

    "What movies are out right now?",
    "What's playing in theaters today?",
    "What shows are on TV tonight?",
    "What concerts are happening this week?",
    "What events are near me today?",
    "What restaurants are open now?",
    "What stores are open right now?",
    "What's the current time in Tokyo?",
    "What time is sunset today?",
    "What time is sunrise tomorrow?",
    "What phase is the moon tonight?",
    "What's the tide right now?",
    "What's traffic like right now?",
    "Are there any accidents on I-95?",
    "What's the wait time at the DMV?",
    "What's the best time to visit Disney World?",
    "What's popular on Netflix right now?",
    "What's trending on YouTube today?",
    "What's viral on TikTok?",
    "What's the #1 song today?",
    "What albums came out this week?",
    "What games are coming out this month?",
    "What's the latest iPhone model?",
    "What's the newest Samsung phone?",
    "What cars came out this year?",
    "What's the best laptop right now?",
    "What's on sale today?",
    "What deals are available now?",
    "What's the current mortgage rate?",
    "What's the interest rate today?",
    "What's the exchange rate for Euro?",
    "What's the price of gold today?",
    "What's the price of oil?",
    "What's the current temperature in Paris?",
    "What time does the sun set in London?",
    "What's the local time in Sydney?",
    "What's happening at the Olympics?",
    "What's the medal count?",
    "Who's performing at the Super Bowl?",
    "What's the halftime show?",

    # ===== RECENT HISTORICAL (20 questions) =====
    # Recent past events - should use web search

    "Who won the election?",
    "Who won the last Super Bowl?",
    "Who won the World Series last year?",
    "Who won the NBA championship?",
    "Who won the Stanley Cup last year?",
    "Who won the Masters?",
    "Who won Wimbledon?",
    "Who won the Kentucky Derby?",
    "Who won the Oscars?",
    "Who won the Grammy?",
    "Who won the Emmy?",
    "What was the biggest movie last year?",
    "What was the #1 song last month?",
    "What happened in the last presidential debate?",
    "What was announced at Apple's last event?",
    "What did Tesla announce recently?",
    "What's the latest from the Fed?",
    "What did the Supreme Court rule on recently?",
    "What natural disasters happened this year?",
    "What space missions launched recently?",
]

# Verify count
print(f"Total questions: {len(QUESTIONS)}")
assert len(QUESTIONS) == 250, f"Expected 250 questions, got {len(QUESTIONS)}"


async def test_question(client: httpx.AsyncClient, question: str, index: int) -> Dict[str, Any]:
    """Test a single question and analyze the data flow."""
    start_time = time.time()

    try:
        if USE_ORCHESTRATOR_DIRECT:
            url = f"{ORCHESTRATOR_URL}/query"
            payload = {
                "query": question,
                "session_id": f"test-250-{index}",
                "user_id": "test-user"
            }
        else:
            url = f"{GATEWAY_URL}/ha/conversation"
            payload = {
                "text": question,
                "conversation_id": f"test-250-{index}"
            }

        response = await client.post(
            url,
            json=payload,
            timeout=60.0
        )

        elapsed = time.time() - start_time

        if response.status_code != 200:
            return {
                "index": index,
                "question": question,
                "success": False,
                "error": f"HTTP {response.status_code}",
                "response_time": elapsed
            }

        data = response.json()

        # Extract answer and metadata
        if USE_ORCHESTRATOR_DIRECT:
            answer = data.get("answer", "")
            intent = data.get("intent", "unknown")
            data_source = data.get("data_source", "unknown")
        else:
            answer = data.get("response", {}).get("speech", {}).get("plain", {}).get("speech", "")
            intent = data.get("intent", "unknown")
            data_source = data.get("data_source", "unknown")

        # Analyze if RAG/web search was used
        used_rag = any(src in data_source.lower() for src in [
            "openweathermap", "weather", "espn", "sports", "thesportsdb",
            "flightaware", "airports", "flight"
        ])

        used_web = any(src in data_source.lower() for src in [
            "duckduckgo", "brave", "web search", "parallel search",
            "ticketmaster", "eventbrite"
        ])

        used_llm_only = "llm knowledge" in data_source.lower()

        # Check if answer is helpful (basic heuristic)
        is_helpful = (
            len(answer) > 20 and
            "i don't have" not in answer.lower() and
            "i cannot provide" not in answer.lower() and
            "i'm unable to" not in answer.lower()
        )

        return {
            "index": index,
            "question": question,
            "success": True,
            "answer": answer,
            "intent": intent,
            "data_source": data_source,
            "used_rag": used_rag,
            "used_web": used_web,
            "used_llm_only": used_llm_only,
            "is_helpful": is_helpful,
            "response_time": elapsed,
            "answer_length": len(answer)
        }

    except asyncio.TimeoutError:
        elapsed = time.time() - start_time
        return {
            "index": index,
            "question": question,
            "success": False,
            "error": "Timeout",
            "response_time": elapsed
        }
    except Exception as e:
        elapsed = time.time() - start_time
        return {
            "index": index,
            "question": question,
            "success": False,
            "error": str(e),
            "response_time": elapsed
        }


async def run_all_tests():
    """Run all 250 tests sequentially with detailed flow analysis."""
    print("\n" + "="*80)
    print("250-Question RAG + Web Search Flow Test")
    print("="*80)
    print(f"Testing: {len(QUESTIONS)} questions")
    print(f"Gateway URL: {GATEWAY_URL}")
    print(f"Orchestrator URL: {ORCHESTRATOR_URL}")
    print(f"Test started at: {datetime.now().isoformat()}")
    print("="*80 + "\n")

    results = []

    async with httpx.AsyncClient() as client:
        for i, question in enumerate(QUESTIONS, 1):
            result = await test_question(client, question, i)
            results.append(result)

            # Progress update every 10 questions
            if i % 10 == 0:
                successful = sum(1 for r in results if r["success"])
                helpful = sum(1 for r in results if r.get("is_helpful", False))
                used_rag = sum(1 for r in results if r.get("used_rag", False))
                used_web = sum(1 for r in results if r.get("used_web", False))
                used_llm = sum(1 for r in results if r.get("used_llm_only", False))

                print(f"Progress: {i}/{len(QUESTIONS)} | "
                      f"Success: {successful}/{i} ({successful/i*100:.1f}%) | "
                      f"Helpful: {helpful}/{i} ({helpful/i*100:.1f}%) | "
                      f"RAG: {used_rag} | Web: {used_web} | LLM: {used_llm}")

    # Analyze results
    print("\n" + "="*80)
    print("FLOW ANALYSIS")
    print("="*80 + "\n")

    total = len(results)
    successful = sum(1 for r in results if r["success"])
    helpful = sum(1 for r in results if r.get("is_helpful", False))

    # Data source analysis
    used_rag = sum(1 for r in results if r.get("used_rag", False))
    used_web = sum(1 for r in results if r.get("used_web", False))
    used_llm_only = sum(1 for r in results if r.get("used_llm_only", False))
    used_both = sum(1 for r in results if r.get("used_rag", False) and r.get("used_web", False))

    print(f"Total Questions: {total}")
    print(f"Successful Responses: {successful} ({successful/total*100:.1f}%)")
    print(f"Helpful Responses: {helpful} ({helpful/total*100:.1f}%)")
    print()
    print("Data Source Usage:")
    print(f"  RAG Only: {used_rag - used_both} ({(used_rag - used_both)/total*100:.1f}%)")
    print(f"  Web Search Only: {used_web - used_both} ({(used_web - used_both)/total*100:.1f}%)")
    print(f"  RAG + Web Search: {used_both} ({used_both/total*100:.1f}%)")
    print(f"  LLM Knowledge Only: {used_llm_only} ({used_llm_only/total*100:.1f}%)")
    print()

    # Response time stats
    response_times = [r["response_time"] for r in results if r["success"]]
    if response_times:
        print("Response Time Stats:")
        print(f"  Average: {sum(response_times)/len(response_times):.2f}s")
        print(f"  Min: {min(response_times):.2f}s")
        print(f"  Max: {max(response_times):.2f}s")
        print()

    # Identify flow issues
    print("="*80)
    print("FLOW ISSUES ANALYSIS")
    print("="*80 + "\n")

    # Questions that should have used RAG but didn't
    should_use_rag = []
    for i, r in enumerate(results):
        q = QUESTIONS[i]
        if r.get("success") and r.get("used_llm_only"):
            if any(keyword in q.lower() for keyword in ["weather", "ravens", "orioles", "bwi", "airport", "flight"]):
                should_use_rag.append((i, q, r.get("data_source", "unknown")))

    if should_use_rag:
        print(f"❌ Questions that should have used RAG but didn't: {len(should_use_rag)}")
        for i, q, ds in should_use_rag[:10]:  # Show first 10
            print(f"  Q{i}: {q}")
            print(f"      Data source: {ds}")
        if len(should_use_rag) > 10:
            print(f"  ... and {len(should_use_rag) - 10} more")
        print()
    else:
        print("✅ All RAG-appropriate questions used RAG")
        print()

    # Questions that got unhelpful answers
    unhelpful = [(i, QUESTIONS[i], r.get("answer", "")[:100], r.get("data_source", "unknown"))
                 for i, r in enumerate(results)
                 if r.get("success") and not r.get("is_helpful", False)]

    if unhelpful:
        print(f"❌ Unhelpful responses: {len(unhelpful)} ({len(unhelpful)/total*100:.1f}%)")
        for i, q, ans, ds in unhelpful[:10]:  # Show first 10
            print(f"  Q{i}: {q}")
            print(f"      Answer: {ans}...")
            print(f"      Source: {ds}")
        if len(unhelpful) > 10:
            print(f"  ... and {len(unhelpful) - 10} more")
        print()

    # Save detailed results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"test_250_rag_web_results_{timestamp}.json"

    summary = {
        "total": total,
        "successful": successful,
        "helpful": helpful,
        "used_rag": used_rag,
        "used_web": used_web,
        "used_llm_only": used_llm_only,
        "used_both": used_both,
        "should_use_rag_but_didnt": len(should_use_rag),
        "unhelpful": len(unhelpful),
        "avg_response_time": sum(response_times)/len(response_times) if response_times else 0
    }

    output = {
        "summary": summary,
        "results": results,
        "flow_issues": {
            "should_use_rag_but_didnt": [{"index": i, "question": q, "data_source": ds}
                                         for i, q, ds in should_use_rag],
            "unhelpful_responses": [{"index": i, "question": q, "answer": ans, "data_source": ds}
                                   for i, q, ans, ds in unhelpful]
        }
    }

    with open(results_file, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"Detailed results saved to: {results_file}")
    print()

    # Final verdict
    print("="*80)
    target_helpful = 0.95
    if helpful / total >= target_helpful:
        print(f"✅ SUCCESS: {helpful/total*100:.1f}% helpful rate (target: {target_helpful*100}%)")
    else:
        print(f"❌ FAILURE: {helpful/total*100:.1f}% helpful rate (target: {target_helpful*100}%)")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(run_all_tests())
