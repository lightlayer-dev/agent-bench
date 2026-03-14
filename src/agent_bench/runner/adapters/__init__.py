"""Agent framework adapters."""

# Import adapters to trigger registration via @register_adapter
from agent_bench.runner.adapters import browser_use  # noqa: F401
from agent_bench.runner.adapters import playwright_agent  # noqa: F401
from agent_bench.runner.adapters import custom  # noqa: F401
