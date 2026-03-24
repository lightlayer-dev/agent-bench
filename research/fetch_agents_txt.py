#!/usr/bin/env python3
"""Fetch /agents.txt from popular websites and check adoption status.

agents.txt is a proposed standard (similar to robots.txt) that declares
permissions and instructions for AI agents interacting with a site.

Outputs:
  - agents_txt_survey.csv  (machine-readable)
  - agents_txt_survey.json (structured)
"""

import csv
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

import requests

# Same sites as fetch_llms_txt.py — 249 sites across categories
SITES = {
    "JS Frameworks": [
        "react.dev", "nextjs.org", "vuejs.org", "svelte.dev", "astro.build",
        "angular.dev", "vite.dev", "turbo.build", "nuxt.com", "remix.run",
        "solidjs.com", "preactjs.com", "qwik.dev", "lit.dev", "alpinejs.dev",
        "htmx.org", "emberjs.com", "backbonejs.org", "mithril.js.org", "stimulus.hotwired.dev",
    ],
    "Developer Tools": [
        "github.com", "gitlab.com", "vercel.com", "netlify.com", "supabase.com",
        "render.com", "docker.com", "postman.com", "railway.app", "fly.io",
        "cloudflare.com", "digitalocean.com", "heroku.com", "aws.amazon.com", "azure.microsoft.com",
        "cloud.google.com", "hashicorp.com", "datadog.com", "sentry.io", "grafana.com",
        "newrelic.com", "pagerduty.com", "launchdarkly.com", "circleci.com", "travis-ci.com",
        "jenkins.io", "ansible.com", "puppet.com", "terraform.io", "pulumi.com",
    ],
    "AI / ML Platforms": [
        "openai.com", "anthropic.com", "cohere.com", "mistral.ai", "replicate.com",
        "together.ai", "pinecone.io", "qdrant.tech", "weaviate.io", "milvus.io",
        "huggingface.co", "wandb.ai", "mlflow.org", "ray.io", "modal.com",
        "anyscale.com", "deepmind.google", "stability.ai", "midjourney.com", "runway.ml",
        "jasper.ai", "writer.com", "copy.ai", "perplexity.ai", "you.com",
    ],
    "Enterprise SaaS": [
        "stripe.com", "slack.com", "notion.so", "shopify.com", "linear.app",
        "figma.com", "miro.com", "asana.com", "monday.com", "clickup.com",
        "jira.atlassian.com", "confluence.atlassian.com", "salesforce.com", "hubspot.com", "zendesk.com",
        "intercom.com", "twilio.com", "sendgrid.com", "mailchimp.com", "segment.com",
        "amplitude.com", "mixpanel.com", "heap.io", "fullstory.com", "hotjar.com",
        "auth0.com", "okta.com", "onelogin.com", "duo.com", "crowdstrike.com",
        "airtable.com", "retool.com", "appsmith.com", "bubble.io", "webflow.com",
        "squarespace.com", "wix.com", "ghost.org", "wordpress.com", "contentful.com",
    ],
    "Programming Languages & Runtimes": [
        "python.org", "nodejs.org", "rust-lang.org", "go.dev", "typescriptlang.org",
        "ruby-lang.org", "php.net", "swift.org", "kotlinlang.org", "dart.dev",
        "elixir-lang.org", "haskell.org", "scala-lang.org", "clojure.org", "erlang.org",
        "ziglang.org", "nim-lang.org", "crystal-lang.org", "gleam.run", "roc-lang.org",
    ],
    "Databases": [
        "postgresql.org", "mysql.com", "mongodb.com", "redis.io", "sqlite.org",
        "cockroachlabs.com", "planetscale.com", "neon.tech", "fauna.com", "couchbase.com",
        "neo4j.com", "dgraph.io", "arangodb.com", "timescale.com", "questdb.io",
    ],
    "News & Media": [
        "nytimes.com", "bbc.com", "cnn.com", "reuters.com", "theguardian.com",
        "forbes.com", "bloomberg.com", "techcrunch.com", "theverge.com", "wired.com",
        "arstechnica.com", "vice.com", "vox.com", "buzzfeed.com", "huffpost.com",
        "washingtonpost.com", "wsj.com", "ft.com", "economist.com", "time.com",
    ],
    "Consumer Web": [
        "google.com", "facebook.com", "twitter.com", "instagram.com", "tiktok.com",
        "youtube.com", "reddit.com", "pinterest.com", "linkedin.com", "snapchat.com",
        "amazon.com", "ebay.com", "walmart.com", "target.com", "bestbuy.com",
        "etsy.com", "nike.com", "apple.com", "spotify.com", "netflix.com",
        "airbnb.com", "uber.com", "doordash.com", "grubhub.com", "yelp.com",
        "tripadvisor.com", "booking.com", "expedia.com", "zillow.com", "redfin.com",
    ],
    "Documentation Platforms": [
        "docs.python.org", "docs.rs", "pkg.go.dev", "docs.oracle.com", "developer.mozilla.org",
        "devdocs.io", "readthedocs.org", "gitbook.com", "docusaurus.io", "mkdocs.org",
        "sphinx-doc.org", "doxygen.nl", "javadoc.io", "rubydoc.info", "hexdocs.pm",
    ],
    "Government & Education": [
        "usa.gov", "nasa.gov", "cdc.gov", "nih.gov", "mit.edu",
        "stanford.edu", "harvard.edu", "berkeley.edu", "ox.ac.uk", "cam.ac.uk",
    ],
    "Health": [
        "webmd.com", "healthline.com", "mayoclinic.org", "clevelandclinic.org", "medlineplus.gov",
    ],
    "Finance": [
        "chase.com", "bankofamerica.com", "wellsfargo.com", "paypal.com", "coinbase.com",
        "robinhood.com", "fidelity.com", "schwab.com", "stripe.dev",
    ],
}

# Known agent names that may appear in agents.txt directives
KNOWN_AGENTS = [
    "ChatGPT", "GPTBot", "Claude", "ClaudeBot", "Anthropic",
    "Bard", "Google-Extended", "Gemini", "Perplexity", "PerplexityBot",
    "Copilot", "GitHub-Copilot", "Devin", "Cursor", "Windsurf",
    "Codex", "OpenAI", "Cohere", "CohereBot", "Meta-ExternalAgent",
    "CCBot", "Amazonbot", "AppleBot", "FacebookBot", "Bytespider",
]

# Directives commonly found in agents.txt (robots.txt-like format)
KNOWN_DIRECTIVES = [
    "User-agent", "Allow", "Disallow", "Crawl-delay",
    "Agent", "Permission", "Rate-limit", "Contact",
    "Scope", "Action", "Description", "Sitemap",
]


@dataclass
class AgentsTxtResult:
    domain: str
    category: str
    has_agents_txt: bool = False
    status_code: int = 0
    content_length: int = 0
    directives_found: list[str] = field(default_factory=list)
    agent_names_mentioned: list[str] = field(default_factory=list)
    timestamp: str = ""


def parse_agents_txt(content: str) -> tuple[list[str], list[str]]:
    """Parse agents.txt content for directives and agent names.

    Returns (directives_found, agent_names_mentioned).
    """
    directives = set()
    agents = set()

    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        # Check for directive: value pattern
        match = re.match(r"^([A-Za-z][\w-]*)\s*:", line)
        if match:
            directive = match.group(1)
            # Normalise to title-case for matching
            for known in KNOWN_DIRECTIVES:
                if directive.lower() == known.lower():
                    directives.add(known)
                    break
            else:
                directives.add(directive)

        # Check for known agent names anywhere in the line
        line_lower = line.lower()
        for agent in KNOWN_AGENTS:
            if agent.lower() in line_lower:
                agents.add(agent)

    return sorted(directives), sorted(agents)


def check_site(domain: str, category: str) -> AgentsTxtResult:
    """Fetch /agents.txt for a single domain."""
    result = AgentsTxtResult(
        domain=domain,
        category=category,
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    )
    url = f"https://{domain}/agents.txt"

    try:
        resp = requests.get(url, timeout=10, headers={
            "User-Agent": "agent-bench-research/1.0",
            "Accept": "text/plain, */*",
        }, allow_redirects=True)
        result.status_code = resp.status_code

        if resp.status_code == 200:
            content = resp.text.strip()
            # Filter out HTML error pages masquerading as 200
            if (content.startswith("<!") or content.startswith("<html")
                    or content.startswith("<HTML") or content.startswith("<head")):
                result.has_agents_txt = False
            elif "domain is for sale" in content.lower() or "buy this domain" in content.lower():
                result.has_agents_txt = False
            elif len(content) < 5:
                result.has_agents_txt = False
            else:
                result.has_agents_txt = True
                result.content_length = len(content)
                result.directives_found, result.agent_names_mentioned = parse_agents_txt(content)
        # Any other status code means no agents.txt

    except requests.Timeout:
        result.status_code = 0
    except Exception:
        result.status_code = -1

    return result


def main():
    out_dir = Path(__file__).parent
    all_results: list[AgentsTxtResult] = []

    tasks = []
    for category, domains in SITES.items():
        for domain in domains:
            tasks.append((domain, category))

    print(f"Checking /agents.txt on {len(tasks)} sites...")

    with ThreadPoolExecutor(max_workers=15) as executor:
        futures = {executor.submit(check_site, d, c): (d, c) for d, c in tasks}
        for i, future in enumerate(as_completed(futures), 1):
            domain, cat = futures[future]
            try:
                result = future.result()
                all_results.append(result)
                icon = "✓" if result.has_agents_txt else "✗"
                extra = ""
                if result.has_agents_txt:
                    extra = f" ({result.content_length}B, {len(result.directives_found)} directives)"
                print(f"  [{i}/{len(tasks)}] {icon} {domain}: {result.status_code}{extra}")
            except Exception as e:
                print(f"  [{i}/{len(tasks)}] {domain}: FAILED - {e}", file=sys.stderr)

    # Sort by category order, then domain
    cat_order = list(SITES.keys())
    all_results.sort(key=lambda r: (cat_order.index(r.category) if r.category in cat_order else 99, r.domain))

    # Deduplicate (stripe.com appears in both SaaS and Finance categories)
    seen: set[str] = set()
    deduped: list[AgentsTxtResult] = []
    for r in all_results:
        if r.domain not in seen:
            seen.add(r.domain)
            deduped.append(r)
    all_results = deduped

    # CSV
    csv_path = out_dir / "agents_txt_survey.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "domain", "category", "has_agents_txt", "status_code",
            "content_length", "directives_found", "agent_names_mentioned", "timestamp",
        ])
        for r in all_results:
            writer.writerow([
                r.domain, r.category, r.has_agents_txt, r.status_code,
                r.content_length,
                ";".join(r.directives_found),
                ";".join(r.agent_names_mentioned),
                r.timestamp,
            ])
    print(f"\nWrote {csv_path}")

    # JSON
    json_path = out_dir / "agents_txt_survey.json"
    found = [r for r in all_results if r.has_agents_txt]
    total_checked = len(all_results)

    cat_summary = {}
    for cat in SITES:
        cat_results = [r for r in all_results if r.category == cat]
        cat_found = [r for r in cat_results if r.has_agents_txt]
        cat_summary[cat] = {
            "total": len(cat_results),
            "found": len(cat_found),
            "adoption_pct": round(len(cat_found) / len(cat_results) * 100, 1) if cat_results else 0,
        }

    # Aggregate directive and agent stats
    all_directives: dict[str, int] = {}
    all_agents: dict[str, int] = {}
    for r in found:
        for d in r.directives_found:
            all_directives[d] = all_directives.get(d, 0) + 1
        for a in r.agent_names_mentioned:
            all_agents[a] = all_agents.get(a, 0) + 1

    json_data = {
        "metadata": {
            "description": "agents.txt adoption survey across popular websites",
            "date": time.strftime("%Y-%m-%d"),
            "total_sites": total_checked,
            "sites_with_agents_txt": len(found),
            "adoption_rate_pct": round(len(found) / total_checked * 100, 1) if total_checked else 0,
            "methodology": (
                "Fetched /agents.txt from each domain over HTTPS with 10s timeout. "
                "Counted as 'found' if HTTP 200 with non-HTML text content of 5+ characters. "
                "Parsed for robots.txt-like directives and known AI agent names."
            ),
        },
        "category_summary": cat_summary,
        "directive_frequency": dict(sorted(all_directives.items(), key=lambda x: -x[1])),
        "agent_mention_frequency": dict(sorted(all_agents.items(), key=lambda x: -x[1])),
        "sites": [
            {
                "domain": r.domain,
                "category": r.category,
                "has_agents_txt": r.has_agents_txt,
                "status_code": r.status_code,
                "content_length": r.content_length,
                "directives_found": r.directives_found,
                "agent_names_mentioned": r.agent_names_mentioned,
                "timestamp": r.timestamp,
            }
            for r in all_results
        ],
    }

    with open(json_path, "w") as f:
        json.dump(json_data, f, indent=2)
    print(f"Wrote {json_path}")

    # Summary
    print(f"\n{'='*60}")
    print(f"SUMMARY: {total_checked} sites checked, {len(found)} have agents.txt "
          f"({round(len(found)/total_checked*100,1) if total_checked else 0}%)")
    print(f"{'='*60}")
    for cat, stats in cat_summary.items():
        print(f"  {cat}: {stats['found']}/{stats['total']} ({stats['adoption_pct']}%)")

    if found:
        print(f"\nSites with agents.txt:")
        for r in found:
            directives_str = ", ".join(r.directives_found) if r.directives_found else "none parsed"
            print(f"  {r.domain} ({r.category}, {r.content_length}B, directives: {directives_str})")

    if all_agents:
        print(f"\nAgent names mentioned across all agents.txt files:")
        for agent, count in sorted(all_agents.items(), key=lambda x: -x[1]):
            print(f"  {agent}: {count} site(s)")


if __name__ == "__main__":
    main()
