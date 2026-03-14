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
# Install
pip install -e ".[browser,dev]"

# Static analysis
agent-bench analyze https://example.com

# Run a task
agent-bench run tasks/example.yaml --model claude-sonnet --adapter browser-use

# Compare results
agent-bench compare --runs results/*.json
```

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
