# LLM-Powered Search Tools & Frameworks

**Date:** 2025-11-14
**Author:** Claude Code
**Status:** Research

## Question

Are there LLM tools/frameworks that help facilitate parallel web search, result fusion, and information extraction?

## Answer: YES! Many Options

## Category 1: LLM Frameworks with Built-in Search

### 1. LangChain Tools/Agents ⭐ (What You Should Use)

**What:** Framework with pre-built search tools and agent orchestration

**Built-in Search Tools:**
```python
from langchain.tools import DuckDuckGoSearchRun
from langchain.tools import GoogleSerperAPIWrapper
from langchain.tools import BraveSearch
from langchain.agents import initialize_agent, Tool

# Multiple search tools
tools = [
    Tool(
        name="DuckDuckGo",
        func=DuckDuckGoSearchRun().run,
        description="Search the web using DuckDuckGo"
    ),
    Tool(
        name="Brave",
        func=BraveSearch().run,
        description="Search using Brave"
    ),
]

# Agent decides which tool(s) to use
agent = initialize_agent(
    tools,
    llm,
    agent="zero-shot-react-description"
)

response = agent.run("What concerts are in Baltimore?")
```

**Pros:**
- ✅ Pre-built integrations for 20+ search APIs
- ✅ Agent can use multiple tools automatically
- ✅ Built-in prompt templates
- ✅ Chain results together
- ✅ Already using LangGraph (part of LangChain ecosystem)

**Cons:**
- ❌ Adds dependency complexity
- ❌ Some overhead for simple cases

**Best For:** You're already using LangGraph! This integrates perfectly.

**Available LangChain Search Tools:**
- `DuckDuckGoSearchRun` - Free
- `BraveSearchWrapper` - Free tier
- `GoogleSerperAPIWrapper` - Paid
- `SerpAPIWrapper` - Paid
- `WikipediaQueryRun` - Free
- `ArxivQueryRun` - Free (research papers)
- `PubMedQueryRun` - Free (medical)

### 2. LlamaIndex (Data Connectors)

**What:** Framework for connecting LLMs to external data

```python
from llama_index import SimpleWebPageReader, VectorStoreIndex
from llama_index.tools import QueryEngineTool

# Load web pages
documents = SimpleWebPageReader().load_data([
    "https://ticketmaster.com/...",
    "https://venue-site.com/..."
])

# Create searchable index
index = VectorStoreIndex.from_documents(documents)

# Query
response = index.as_query_engine().query("Concerts in Baltimore")
```

**Pros:**
- ✅ Excellent for document ingestion
- ✅ Vector search built-in
- ✅ Web page readers

**Cons:**
- ❌ More focused on document indexing than live search
- ❌ Additional framework to learn

**Best For:** Building persistent knowledge bases

### 3. AutoGPT / BabyAGI Style Agents

**What:** Autonomous agents that can use tools iteratively

```python
# Pseudo-code
agent = AutoGPTAgent(
    tools=[web_search, web_scrape, summarize],
    goal="Find all concerts in Baltimore this month"
)

# Agent automatically:
# 1. Searches multiple sources
# 2. Extracts relevant info
# 3. Cross-validates
# 4. Summarizes findings
```

**Pros:**
- ✅ Fully autonomous
- ✅ Can iterate and refine

**Cons:**
- ❌ Unpredictable behavior
- ❌ High token usage
- ❌ Slow (multiple LLM calls)

**Best For:** Complex research tasks, not real-time voice

## Category 2: Specialized Search-to-LLM Services

### 4. Exa (Metaphor) ⭐⭐ (Highly Recommended)

**URL:** https://exa.ai/ (formerly Metaphor)
**What:** Neural search API designed specifically for LLMs

**How It Works:**
```python
from exa_py import Exa

exa = Exa(api_key="your-key")

# AI-native search (understands intent)
results = exa.search_and_contents(
    "Find upcoming concerts in Baltimore",
    type="neural",  # AI-powered understanding
    num_results=5,
    text={"max_characters": 1000}
)

# Returns clean, LLM-ready content
for result in results.results:
    print(f"{result.title}: {result.text}")
```

**Key Features:**
- 🔥 **Neural search:** Understands semantic meaning, not just keywords
- 🔥 **Finds similar content:** "Find pages like this example"
- 🔥 **LLM-optimized:** Returns clean text, not HTML
- 🔥 **Filters:** By domain, date, content type
- 🔥 **Autoprompt:** Converts natural language to search queries

**Example:**
```python
# Natural language query
exa.search("What are people saying about the new iPhone?")

# Finds similar
exa.find_similar("https://example-article.com")

# Time-based
exa.search(
    "Tech news",
    start_published_date="2024-01-01"
)
```

**Pricing:**
- Free: 1,000 searches/month
- Basic: $20/month (10,000 searches)
- Pro: $100/month (100,000 searches)

**Pros:**
- ✅ Specifically designed for LLM use cases
- ✅ Returns clean, contextual results
- ✅ Neural search understands intent
- ✅ Great for "find pages like this"
- ✅ Good free tier

**Cons:**
- ❌ Smaller index than Google
- ❌ Paid after 1,000/month

**Best For:** AI-native search, finding similar content, LLM RAG

### 5. Perplexity API (Coming Soon)

**What:** AI search engine with built-in LLM synthesis

**How It Would Work:**
```python
response = perplexity.ask(
    "What concerts are in Baltimore?",
    citations=True
)
# Returns: Synthesized answer + source links
```

**Status:** Not publicly available yet
**Expected:** Premium pricing when released

**Pros:**
- ✅ AI synthesizes answer for you
- ✅ Built-in citations
- ✅ Multiple sources automatically

**Cons:**
- ❌ Not available as API yet
- ❌ Would be expensive

### 6. You.com API

**What:** AI search with multiple sources

**Status:** Limited availability
**Pricing:** Enterprise only

## Category 3: LLM Tool-Use Frameworks

### 7. Function Calling (OpenAI/Anthropic Style)

**What:** LLM decides which functions/tools to call

**Your Implementation:**
```python
# Define tools for LLM
tools = [
    {
        "name": "search_web",
        "description": "Search the web for current information",
        "parameters": {"query": "string"}
    },
    {
        "name": "search_events",
        "description": "Search for concerts and events",
        "parameters": {"location": "string", "keywords": "string"}
    }
]

# LLM chooses which tool(s) to use
response = ollama.chat(
    model="llama3.1:8b",
    messages=[{"role": "user", "content": "Concerts in Baltimore"}],
    tools=tools
)

# LLM might return:
# [use_tool: search_events(location="Baltimore", keywords="concerts")]
```

**Pros:**
- ✅ LLM intelligently chooses tools
- ✅ Can call multiple tools
- ✅ Works with Ollama (llama3.1+)

**Cons:**
- ❌ You still need to implement the tools
- ❌ Adds an extra LLM call

**Best For:** Dynamic tool selection

### 8. DSPy (Declarative Self-improving Python)

**What:** Framework that optimizes prompts and tool use

```python
import dspy

class SearchAndSynthesize(dspy.Module):
    def __init__(self):
        self.search = dspy.ChainOfThought("query -> results")
        self.synthesize = dspy.ChainOfThought("results -> answer")

    def forward(self, query):
        results = self.search(query=query)
        answer = self.synthesize(results=results)
        return answer

# DSPy automatically optimizes the prompts
```

**Pros:**
- ✅ Automatically optimizes prompts
- ✅ Can improve over time

**Cons:**
- ❌ Complex setup
- ❌ Requires training examples

**Best For:** Research, optimization

## Category 4: Web Scraping + LLM Extraction

### 9. Firecrawl ⭐

**URL:** https://firecrawl.dev/
**What:** Turn websites into LLM-ready markdown

```python
from firecrawl import FirecrawlApp

app = FirecrawlApp(api_key="your-key")

# Crawl and convert to markdown
result = app.scrape_url(
    "https://venue-website.com/events",
    formats=["markdown", "html"]
)

# Returns clean markdown for LLM
print(result['markdown'])
```

**Pricing:**
- Free: 500 credits
- Starter: $20/month (5,000 pages)

**Pros:**
- ✅ Handles JavaScript rendering
- ✅ Converts to clean markdown
- ✅ LLM-ready output
- ✅ Can crawl entire sites

**Cons:**
- ❌ Paid after free tier
- ❌ Slower than APIs

**Best For:** Scraping specific venue websites

### 10. Jina AI Reader

**URL:** https://jina.ai/reader/
**What:** URL to LLM-ready text converter

```python
import httpx

# Convert any URL to clean text
response = httpx.get(
    f"https://r.jina.ai/{target_url}"
)

clean_text = response.text  # LLM-ready content
```

**Pricing:**
- Free: 20 requests/min
- Pro: $20/month (200 requests/min)

**Pros:**
- ✅ Simple API
- ✅ Removes ads, navigation, clutter
- ✅ Good free tier

**Cons:**
- ❌ Still need to find URLs first

**Best For:** Converting search results to clean text

## Recommendation for Project Athena

### Option A: LangChain Integration (Recommended) ⭐

**Why:**
- You're already using LangGraph (same ecosystem)
- Pre-built integrations for multiple search APIs
- Easy to add Ticketmaster, Brave, DuckDuckGo
- Agent can intelligently choose tools

**Implementation:**
```python
# src/orchestrator/langchain_search.py

from langchain.tools import Tool
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_community.utilities import BraveSearchWrapper

# Your custom Ticketmaster tool
class TicketmasterTool:
    def run(self, query: str) -> str:
        # Your Ticketmaster API logic
        return search_ticketmaster(query)

# Combine tools
tools = [
    Tool(
        name="TicketmasterEvents",
        func=TicketmasterTool().run,
        description="Search for concerts and events. Use this for queries about concerts, shows, or live events."
    ),
    Tool(
        name="BraveSearch",
        func=BraveSearchWrapper().run,
        description="Search the web for current information. Use for general queries."
    ),
    Tool(
        name="DuckDuckGo",
        func=DuckDuckGoSearchRun().run,
        description="Quick search for facts and definitions."
    )
]

# Use in your LangGraph flow
async def search_with_tools(query: str) -> List[Dict]:
    results = []

    # Parallel execution
    tasks = [
        asyncio.create_task(tool.func(query))
        for tool in tools
    ]

    for task in asyncio.as_completed(tasks):
        try:
            result = await task
            results.append(result)
        except Exception as e:
            logger.warning(f"Tool failed: {e}")

    return results
```

### Option B: Exa (Metaphor) for AI-Native Search

**Why:**
- Neural search understands intent better
- Returns LLM-ready content
- Good free tier (1,000/month)
- Perfect for "find similar events"

**Implementation:**
```python
from exa_py import Exa

exa = Exa(api_key=os.getenv("EXA_API_KEY"))

# For concert queries
results = exa.search_and_contents(
    "upcoming concerts in Baltimore Maryland",
    type="neural",
    category="events",
    num_results=5
)

# For finding similar
similar = exa.find_similar(
    "https://ticketmaster.com/event/123",
    num_results=5
)
```

### Option C: Hybrid Approach (Best)

```python
async def intelligent_search(query: str, intent: str):
    if intent == "event_search":
        # Use specialized APIs
        return await search_events(query)

    elif needs_deep_research(query):
        # Use Exa neural search
        return await exa_search(query)

    else:
        # Use fast general search
        return await parallel_search([
            duckduckgo_search(query),
            brave_search(query)
        ])
```

## Summary: What You Should Do

### Immediate (Next 30 minutes):
1. ✅ Add **Ticketmaster API** (FREE, perfect for events)
2. ✅ Keep **DuckDuckGo** (already working)
3. ✅ Implement parallel execution

### Near-term (Next session):
4. ⭐ Integrate **LangChain Tools** (you're already using LangGraph!)
5. ⭐ Add **Brave Search** (2,000 free/month)

### Future:
6. 🔮 Try **Exa/Metaphor** for neural search
7. 🔮 Add **SerpAPI** when budget allows

### Code Structure:
```
src/orchestrator/
├── search_providers/
│   ├── __init__.py
│   ├── base.py           # SearchProvider abstract class
│   ├── duckduckgo.py     # Current implementation
│   ├── ticketmaster.py   # NEW - events
│   ├── brave.py          # NEW - general web
│   └── exa.py            # FUTURE - neural search
├── parallel_search.py    # Orchestrates parallel execution
└── result_fusion.py      # Deduplicates & ranks results
```

**Want me to start with the LangChain + Ticketmaster integration?** It's the cleanest path forward since you're already using LangGraph.
