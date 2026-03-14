# agent-bench

**Benchmark suite for evaluating how AI-agent-native a website is.**

Most websites weren't built for AI agents. Some are easy to navigate programmatically; others are a maze of SPAs, CAPTCHAs, and undocumented APIs. **agent-bench** measures exactly where a site falls on that spectrum — and then proves it by running real agents against real tasks.

## Two Modes

### 1. Static Analysis — Score a site's agent-friendliness

Evaluate a website across six dimensions without running any agents:

- **API Surface** — REST/GraphQL endpoints, OpenAPI specs, CORS, content negotiation
- **Documentation** — robots.txt, sitemaps, OpenAPI specs, JSON-LD, `llms.txt`
- **Auth Complexity** — bot detection, CAPTCHAs, OAuth discovery, login form analysis
- **Structure** — semantic HTML, ARIA labels, stable selectors, SSR detection
- **Error Handling** — proper 404s, rate limit headers, HTTP method validation
- **Cost Efficiency** — token count, signal-to-noise ratio, DOM depth, CSS bloat

Produces an overall **Agent-Readiness Score** with a detailed breakdown.

### 2. Live Agent Runs — Test real agents on real tasks

Define tasks (e.g., "search for a product", "submit a form") and run them across:

- **Agent frameworks** — browser-use, Playwright-based agents, custom adapters
- **Foundation models** — Claude, GPT-4, Gemini, open-source models
- **Metrics** — success rate, step count, token cost, wall-clock time, consistency

## Quick Start

```bash
# Install from PyPI
pip install agent-bench

# Or install from source
pip install -e ".[dev]"

# Score a single site
agent-bench analyze https://example.com

# HTML report
agent-bench analyze https://example.com --format html -o report.html

# Classify a site and see what tasks agents would try
agent-bench classify https://example.com

# Score multiple sites at once
agent-bench batch https://github.com https://stripe.com https://reddit.com

# Generate a leaderboard from results
agent-bench leaderboard benchmark-results/*.json -o leaderboard.html

# List available models
agent-bench models
```

## Configuration

Create an `agent-bench.yaml` to define models and adapter settings. The CLI auto-discovers this file in the current directory.

```yaml
models:
  - name: claude-sonnet
    provider: anthropic
    model_id: claude-sonnet-4-20250514
    api_key_env: ANTHROPIC_API_KEY

  - name: gpt-4o
    provider: openai
    model_id: gpt-4o
    api_key_env: OPENAI_API_KEY

adapters:
  - type: browser-use
    headless: true
    timeout_seconds: 120
    max_steps: 50

default_timeout: 120
```

Also supports `.agent-bench.yaml`, `agent-bench.yml`, and `agent-bench.toml`.

See [`agent-bench.example.yaml`](agent-bench.example.yaml) for a full example.

## Live Agent Runs

```bash
# Install with browser-use adapter
pip install -e ".[browser-use,dev]"
playwright install chromium

# Run a task
agent-bench run tasks/example.yaml --model claude-sonnet --adapter browser-use

# Compare results
agent-bench compare --runs results/*.json
```

### ⚠️ Cost Warning

**Live agent runs call real LLM APIs and cost real money.** Each run sends multiple requests to your configured model as the agent navigates the site. Costs depend on the model, task complexity, and number of steps.

You must provide your own API keys via environment variables:
- `ANTHROPIC_API_KEY` for Claude models
- `OPENAI_API_KEY` for GPT models
- `GOOGLE_API_KEY` for Gemini models

Static analysis (`agent-bench analyze`) does **not** call any LLMs and is free to run.

## CLI Commands

| Command | Description |
|---------|-------------|
| `analyze <url>` | Static analysis with agent-readiness score |
| `batch <urls...>` | Analyze multiple sites, save results to a directory |
| `classify <url>` | Classify site type and generate benchmark tasks |
| `leaderboard <files...>` | Generate HTML leaderboard from result files |
| `models` | List available foundation models (built-in + config) |
| `run <task.yaml>` | Run live agent benchmarks (requires LLM API key) |
| `compare` | Compare results across different runs |

## Bring Your Own Agent

Plug in any agent via the custom adapter using a simple JSON-lines protocol over stdin/stdout:

```bash
AGENT_BENCH_CUSTOM_CMD="python my_agent.py" \
agent-bench run tasks/example.yaml --model claude-sonnet --adapter custom
```

```python
import json, sys

task = json.loads(sys.stdin.readline())

print(json.dumps({"step": 1, "action": "navigate", "result": "loaded site"}))
print(json.dumps({"step": 2, "action": "click", "result": "clicked button",
                   "input_tokens": 500, "output_tokens": 100}))

print(json.dumps({"done": True, "success": True, "summary": "Task completed"}))
```

See [`examples/custom_agent.py`](examples/custom_agent.py) for a complete example.

## Architecture

```
agent-bench/
├── analysis/           # Static site scoring
│   ├── checks/         # Check modules (api, auth, cost, docs, errors, structure)
│   ├── scorer.py       # Aggregates check results
│   ├── report.py       # Text/JSON/Markdown reports
│   ├── html_report.py  # Standalone HTML report
│   └── leaderboard.py  # Multi-site HTML leaderboard
├── runner/             # Live agent execution
│   ├── adapters/       # Framework adapters (browser-use, Playwright, custom)
│   ├── classifier.py   # Site classification (11 categories)
│   ├── generator.py    # Dynamic task generation
│   ├── executor.py     # Orchestrates runs
│   ├── task.py         # Task loading and validation
│   └── metrics.py      # Metrics collection
├── models/             # Foundation model registry
├── results/            # Storage and comparison
└── config.py           # Config file loading (YAML/TOML)
```

## CI Integration

Gate your PRs on agent-readiness score. If the score drops below your threshold, the build fails.

```bash
# In your CI pipeline:
agent-bench analyze https://api.example.com --threshold 0.5 --quiet
# Exit code 1 if score < 0.5
```

### GitHub Actions

Drop-in workflow examples in [`examples/`](examples/):

- **[`github-actions-ci.yml`](examples/github-actions-ci.yml)** — PR gate with threshold check, artifact upload, and optional PR comment with score breakdown
- **[`score-tracking.yml`](examples/score-tracking.yml)** — Weekly score tracking with history branch and automatic before/after comparison

### Compare Scores Over Time

```bash
# Diff two analysis snapshots:
agent-bench compare --before results/jan.json --after results/feb.json

# Output:
#   Overall: 38% → 65%  ▲ +27%
#   api          30%     60%  ▲ +30%
#   docs         40%     70%  ▲ +30%
```

## Development

```bash
git clone https://github.com/LightLayer-dev/agent-bench.git
cd agent-bench
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Run tests (169 unit tests + 5 integration tests)
python -m pytest tests/ -v

# Skip integration tests (which hit real websites)
python -m pytest tests/ -v -m "not integration"
```

## License

MIT
