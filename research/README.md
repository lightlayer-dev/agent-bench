# Research: AI Bot Blocking Survey

Survey of `robots.txt` AI bot blocking across popular websites.

## Dataset

- **`robots_txt_survey.csv`** — Machine-readable results (domain, category, status per bot)
- **`robots_txt_survey.json`** — Structured data with metadata, summaries, and per-site results
- **`fetch_robots_txt.py`** — Script to reproduce the survey

## Methodology

1. Fetched `/robots.txt` from each domain over HTTPS
2. Parsed with Python's `urllib.robotparser`
3. Checked `can_fetch("/", bot)` for each of 8 AI user-agents

### AI Bots Checked

| Bot | Operator |
|-----|----------|
| GPTBot | OpenAI (training) |
| ChatGPT-User | OpenAI (browsing) |
| ClaudeBot | Anthropic |
| anthropic-ai | Anthropic |
| Google-Extended | Google (AI training) |
| CCBot | Common Crawl |
| PerplexityBot | Perplexity AI |
| Bytespider | ByteDance |

### Sites Surveyed

99 sites across 8 categories: News & Media (22), Social Media (10), Tech/Developer (20), E-commerce (12), Finance (10), Government (10), Education (10), Health (5).

## Reproducing

```bash
cd research/
pip install requests
python fetch_robots_txt.py
```

The script fetches live `robots.txt` files, so results may change over time as sites update their policies.

## Notes

- `robots.txt` is a voluntary standard — sites may use additional bot detection beyond what's measured here
- Some sites returned non-200 status codes (rate limiting, auth proxies) and are marked accordingly
- "not_found" (404) is treated as "all bots allowed" per the robots.txt spec
- Results reflect a point-in-time snapshot; the landscape evolves quickly

## Related

- [Blog post: Which Sites Block AI Bots?](https://company.lightlayer.dev/blog/which-sites-block-ai-bots.html)
- [agent-bench documentation](../README.md)
