# agent-bench

**Benchmark suite for evaluating how AI-agent-native a website is.**

Most websites weren't built for AI agents. Some are easy to navigate programmatically; others are a maze of SPAs, CAPTCHAs, and undocumented APIs. **agent-bench** measures exactly where a site falls on that spectrum — and then proves it by running real agents against real tasks.

> 🚧 Early stage — architecture is set, implementation is in progress.

## Two Modes

### 1. Static Analysis — Score a site's agent-friendliness

Evaluate a website across multiple dimensions without running any agents:

- **API surface** — REST/GraphQL endpoints, OpenAPI specs, response structure
- **Documentation** — machine-readable docs, schema quality, examples
- **Auth complexity** — OAuth flows, API keys, session management
- **Structure** — semantic HTML, ARIA labels, predictable navigation
- **Error handling** — structured errors, rate limit headers, retry guidance

Produces an overall **Agent-Readiness Score** with a detailed breakdown.

### 2. Live Agent Runs — Test real agents on real tasks

Define tasks (e.g., "search for a product", "book a flight", "submit a form") and run them across:

- **Agent frameworks** — browser-use, Playwright-based agents, custom adapters
- **Foundation models** — Claude, GPT-4, Gemini, open-source models

### Metrics

| Metric | Description |
|--------|-------------|
| ✅ Success rate | Did the agent complete the task? |
| 🔢 Steps | How many actions were needed? |
| 💰 Cost | Token/API costs per run |
| ⏱️ Time | Wall-clock time to completion |
| 🔄 Consistency | Success rate across repeated runs |

### Compare

See how different agent × model combinations perform on the same site — or how different sites compare for the same agent.

## Quick Start

```bash
# Install (static analysis only)
pip install -e ".[dev]"

# Install with browser-use adapter
pip install -e ".[browser-use,dev]"
playwright install chromium

# Install with Playwright adapter
pip install -e ".[playwright,dev]"
playwright install chromium

# Static analysis
agent-bench analyze https://example.com

# Generate an HTML report
agent-bench analyze https://example.com --format html -o report.html

# Classify a site and see generated tasks
agent-bench classify https://example.com

# Run a task
agent-bench run tasks/example.yaml --model claude-sonnet --adapter browser-use

# Compare results
agent-bench compare --runs results/*.json
```

## ⚠️ Cost Warning

**Live agent runs call real LLM APIs and cost real money.** Each run sends multiple requests to your configured model (Claude, GPT-4, Gemini, etc.) as the agent navigates the site. Costs depend on the model, task complexity, and number of steps.

You must provide your own API keys via environment variables:
- `ANTHROPIC_API_KEY` for Claude models
- `OPENAI_API_KEY` for GPT models
- `GOOGLE_API_KEY` for Gemini models

Static analysis (`agent-bench analyze`) does **not** call any LLMs and is free to run.

## Bring Your Own Agent

Don't want to use browser-use or Playwright? Plug in any agent via the custom adapter. Your agent just needs to speak a simple JSON-lines protocol over stdin/stdout:

```bash
AGENT_BENCH_CUSTOM_CMD="python my_agent.py" \
agent-bench run tasks/example.yaml --model claude-sonnet --adapter custom
```

Your agent receives the task as JSON on stdin and reports steps + results on stdout:

```python
import json, sys

# Read task
task = json.loads(sys.stdin.readline())

# Report steps
print(json.dumps({"step": 1, "action": "navigate", "result": "loaded site"}))
print(json.dumps({"step": 2, "action": "click", "result": "clicked button",
                   "input_tokens": 500, "output_tokens": 100}))

# Report final result
print(json.dumps({"done": True, "success": True, "summary": "Task completed"}))
```

See [`examples/custom_agent.py`](examples/custom_agent.py) for a complete example.

## Task Definitions

Tasks are defined in YAML:

```yaml
name: search-product
site: https://example-store.com
description: Search for a specific product and add it to cart
steps:
  - action: navigate
    url: https://example-store.com
  - action: search
    query: "wireless headphones"
  - action: select_result
    criteria: "first product under $50"
  - action: add_to_cart
success_criteria:
  - cart_count: 1
```

## Architecture

```
agent-bench/
├── analysis/        # Static site scoring
│   ├── checks/      # Individual check modules (API, auth, docs, etc.)
│   ├── scorer.py    # Aggregates check results into a score
│   └── report.py    # Human-readable reports
├── runner/          # Live agent execution
│   ├── adapters/    # Framework adapters (browser-use, Playwright, etc.)
│   ├── executor.py  # Orchestrates runs
│   ├── task.py      # Task loading and validation
│   └── metrics.py   # Metrics collection
├── models/          # Foundation model registry
└── results/         # Storage and comparison
```

## License

MIT
