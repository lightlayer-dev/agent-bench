# agent-bench

**Benchmark suite for evaluating how AI-agent-native a website is.**

Most websites weren't built for AI agents. Some are easy to navigate programmatically; others are a maze of SPAs, CAPTCHAs, and undocumented APIs. **agent-bench** measures exactly where a site falls on that spectrum — and then proves it by running real agents against real tasks.

## Two Modes

### 1. Static Analysis — Score a site's agent-friendliness

Evaluate a website across seven dimensions without running any agents:

- **API Surface** — REST/GraphQL endpoints, OpenAPI specs, CORS, content negotiation
- **Documentation** — robots.txt, sitemaps, OpenAPI specs, JSON-LD, `llms.txt`
- **Auth Complexity** — bot detection, CAPTCHAs, OAuth discovery, login form analysis
- **Structure** — semantic HTML, ARIA labels, stable selectors, SSR detection
- **Error Handling** — proper 404s, rate limit headers, HTTP method validation
- **Cost Efficiency** — token count, signal-to-noise ratio, DOM depth, CSS bloat
- **Accessibility** — landmark roles, image alt text, skip links, ARIA live regions, focus management

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

# Batch with CI gating (exit 1 if any site < 50%)
agent-bench batch https://api.example.com --threshold 50 --quiet

# Generate a leaderboard from results
agent-bench leaderboard benchmark-results/*.json -o leaderboard.html

# List available checks (built-in + plugins)
agent-bench checks

# List available models
agent-bench models

# View score history for a site
agent-bench trend https://example.com
```

## Configuration

Create an `agent-bench.yaml` to define models, adapter settings, and sites to benchmark:

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

# Define sites for batch analysis
sites:
  - url: https://stripe.com
    checks: ["api", "docs", "a11y"]
    label: "Stripe"
  - url: https://github.com
  - url: https://reddit.com

default_timeout: 120
```

Run `agent-bench batch` with no arguments to analyze all configured sites:

```bash
# Uses sites from agent-bench.yaml
agent-bench batch

# Mix config sites with CLI URLs
agent-bench batch https://extra-site.com

# Point at a specific config file
agent-bench batch --config path/to/config.yaml
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
| `batch [urls...]` | Analyze multiple sites (CLI args + config `sites`) |
| `checks` | List all available checks (built-in + plugins) |
| `classify <url>` | Classify site type and generate benchmark tasks |
| `compare` | Compare results across different runs or snapshots |
| `leaderboard <files...>` | Generate HTML leaderboard from result files |
| `models` | List available foundation models (built-in + config) |
| `run <task.yaml>` | Run live agent benchmarks (requires LLM API key) |
| `trend <url>` | Show score history over time for a site |

## Trend Tracking

agent-bench automatically stores timestamped results. Track how a site's score changes over time:

```bash
# Record a snapshot (happens automatically with analyze/batch)
agent-bench analyze https://example.com

# View score history
agent-bench trend https://example.com

# Output:
#   https://example.com — Score History
#   2026-03-01  42%
#   2026-03-08  48%  ▲ +6%
#   2026-03-15  55%  ▲ +7%
```

## Plugin System

Extend agent-bench with custom checks via Python entry points. Create a package that registers checks in the `agent_bench.checks` group:

```toml
# In your package's pyproject.toml:
[project.entry-points.'agent_bench.checks']
my_check = "my_package.checks:MyCustomCheck"
```

```python
# my_package/checks.py
from agent_bench.analysis.checks import BaseCheck
from agent_bench.analysis.models import CheckResult

class MyCustomCheck(BaseCheck):
    name = "my_check"

    def execute(self) -> CheckResult:
        # Your custom analysis logic
        return CheckResult(
            name=self.name,
            score=0.8,
            findings=["Found something interesting"],
        )
```

Plugins can also override built-in checks by using the same entry point name (e.g., `api`, `docs`).

List all available checks: `agent-bench checks`

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

## CI Integration

Gate your PRs on agent-readiness score. If the score drops below your threshold, the build fails.

```bash
# Single site
agent-bench analyze https://api.example.com --threshold 0.5 --quiet

# Multi-site (exit 1 if ANY site drops below threshold)
agent-bench batch --threshold 50 --quiet

# Push results to LightLayer Dashboard
agent-bench analyze https://example.com --post http://dashboard.example.com
agent-bench batch --post http://dashboard.example.com --source ci
```

### GitHub Action

Use the official GitHub Action for zero-config CI integration:

```yaml
# .github/workflows/agent-bench.yml
name: Agent-Readiness Check
on: [pull_request]

jobs:
  agent-bench:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: lightlayer-dev/agent-bench@main
        with:
          urls: "https://your-api.example.com"
          threshold: "40"
```

Features:
- **PR comments** — automatic score breakdown on every pull request
- **Step summary** — scores appear in GitHub Actions summary tab
- **Threshold gating** — fail the build if scores drop below your minimum
- **Dashboard integration** — push results to LightLayer Dashboard with `post-url` and `api-key`
- **Artifact upload** — results saved as build artifacts for 30 days
- **Config file support** — use `agent-bench.yaml` from your repo with `config` input

See [`examples/agent-bench-ci.yml`](examples/agent-bench-ci.yml) for more options.

| Input | Description | Default |
|-------|-------------|---------|
| `urls` | Space-separated URLs to analyze | |
| `config` | Path to `agent-bench.yaml` config file | |
| `threshold` | Minimum score (0-100), fails if below | |
| `format` | Output format: json, table, markdown, html | `json` |
| `post-url` | LightLayer Dashboard URL for result posting | |
| `api-key` | API key for dashboard | |
| `comment` | Post PR comment with results | `true` |
| `version` | Specific agent-bench version to install | latest |

### Compare Scores Over Time

```bash
# Diff two analysis snapshots:
agent-bench compare --before results/jan.json --after results/feb.json

# Output:
#   Overall: 38% → 65%  ▲ +27%
#   api          30%     60%  ▲ +30%
#   docs         40%     70%  ▲ +30%
```

## Architecture

```
agent-bench/
├── analysis/           # Static site scoring
│   ├── checks/         # Check modules (a11y, api, auth, cost, docs, errors, structure)
│   ├── scorer.py       # Aggregates check results + plugin discovery
│   ├── report.py       # Text/JSON/Markdown reports
│   ├── html_report.py  # Standalone HTML report
│   ├── leaderboard.py  # Multi-site HTML leaderboard
│   └── trend.py        # Score history tracking
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

## Development

```bash
git clone https://github.com/LightLayer-dev/agent-bench.git
cd agent-bench
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Run tests (221 unit tests + integration tests)
python -m pytest tests/ -v

# Skip integration tests (which hit real websites)
python -m pytest tests/ -v -m "not integration"
```

## License

MIT
