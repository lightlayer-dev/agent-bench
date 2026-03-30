#!/usr/bin/env python3
"""Fetch /llms.txt from popular websites and check adoption status.

Outputs:
  - llms_txt_survey.csv  (machine-readable)
  - llms_txt_survey.json (structured)
"""

import csv
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

import requests

# 249 sites across categories matching the blog post
SITES = {
    "JS Frameworks": [
        "react.dev",
        "nextjs.org",
        "vuejs.org",
        "svelte.dev",
        "astro.build",
        "angular.dev",
        "vite.dev",
        "turbo.build",
        "nuxt.com",
        "remix.run",
        "solidjs.com",
        "preactjs.com",
        "qwik.dev",
        "lit.dev",
        "alpinejs.dev",
        "htmx.org",
        "emberjs.com",
        "backbonejs.org",
        "mithril.js.org",
        "stimulus.hotwired.dev",
    ],
    "Developer Tools": [
        "github.com",
        "gitlab.com",
        "vercel.com",
        "netlify.com",
        "supabase.com",
        "render.com",
        "docker.com",
        "postman.com",
        "railway.app",
        "fly.io",
        "cloudflare.com",
        "digitalocean.com",
        "heroku.com",
        "aws.amazon.com",
        "azure.microsoft.com",
        "cloud.google.com",
        "hashicorp.com",
        "datadog.com",
        "sentry.io",
        "grafana.com",
        "newrelic.com",
        "pagerduty.com",
        "launchdarkly.com",
        "circleci.com",
        "travis-ci.com",
        "jenkins.io",
        "ansible.com",
        "puppet.com",
        "terraform.io",
        "pulumi.com",
    ],
    "AI / ML Platforms": [
        "openai.com",
        "anthropic.com",
        "cohere.com",
        "mistral.ai",
        "replicate.com",
        "together.ai",
        "pinecone.io",
        "qdrant.tech",
        "weaviate.io",
        "milvus.io",
        "huggingface.co",
        "wandb.ai",
        "mlflow.org",
        "ray.io",
        "modal.com",
        "anyscale.com",
        "deepmind.google",
        "stability.ai",
        "midjourney.com",
        "runway.ml",
        "jasper.ai",
        "writer.com",
        "copy.ai",
        "perplexity.ai",
        "you.com",
    ],
    "Enterprise SaaS": [
        "stripe.com",
        "slack.com",
        "notion.so",
        "shopify.com",
        "linear.app",
        "figma.com",
        "miro.com",
        "asana.com",
        "monday.com",
        "clickup.com",
        "jira.atlassian.com",
        "confluence.atlassian.com",
        "salesforce.com",
        "hubspot.com",
        "zendesk.com",
        "intercom.com",
        "twilio.com",
        "sendgrid.com",
        "mailchimp.com",
        "segment.com",
        "amplitude.com",
        "mixpanel.com",
        "heap.io",
        "fullstory.com",
        "hotjar.com",
        "auth0.com",
        "okta.com",
        "onelogin.com",
        "duo.com",
        "crowdstrike.com",
        "airtable.com",
        "retool.com",
        "appsmith.com",
        "bubble.io",
        "webflow.com",
        "squarespace.com",
        "wix.com",
        "ghost.org",
        "wordpress.com",
        "contentful.com",
    ],
    "Programming Languages & Runtimes": [
        "python.org",
        "nodejs.org",
        "rust-lang.org",
        "go.dev",
        "typescriptlang.org",
        "ruby-lang.org",
        "php.net",
        "swift.org",
        "kotlinlang.org",
        "dart.dev",
        "elixir-lang.org",
        "haskell.org",
        "scala-lang.org",
        "clojure.org",
        "erlang.org",
        "ziglang.org",
        "nim-lang.org",
        "crystal-lang.org",
        "gleam.run",
        "roc-lang.org",
    ],
    "Databases": [
        "postgresql.org",
        "mysql.com",
        "mongodb.com",
        "redis.io",
        "sqlite.org",
        "cockroachlabs.com",
        "planetscale.com",
        "neon.tech",
        "fauna.com",
        "couchbase.com",
        "neo4j.com",
        "dgraph.io",
        "arangodb.com",
        "timescale.com",
        "questdb.io",
    ],
    "News & Media": [
        "nytimes.com",
        "bbc.com",
        "cnn.com",
        "reuters.com",
        "theguardian.com",
        "forbes.com",
        "bloomberg.com",
        "techcrunch.com",
        "theverge.com",
        "wired.com",
        "arstechnica.com",
        "vice.com",
        "vox.com",
        "buzzfeed.com",
        "huffpost.com",
        "washingtonpost.com",
        "wsj.com",
        "ft.com",
        "economist.com",
        "time.com",
    ],
    "Consumer Web": [
        "google.com",
        "facebook.com",
        "twitter.com",
        "instagram.com",
        "tiktok.com",
        "youtube.com",
        "reddit.com",
        "pinterest.com",
        "linkedin.com",
        "snapchat.com",
        "amazon.com",
        "ebay.com",
        "walmart.com",
        "target.com",
        "bestbuy.com",
        "etsy.com",
        "nike.com",
        "apple.com",
        "spotify.com",
        "netflix.com",
        "airbnb.com",
        "uber.com",
        "doordash.com",
        "grubhub.com",
        "yelp.com",
        "tripadvisor.com",
        "booking.com",
        "expedia.com",
        "zillow.com",
        "redfin.com",
    ],
    "Documentation Platforms": [
        "docs.python.org",
        "docs.rs",
        "pkg.go.dev",
        "docs.oracle.com",
        "developer.mozilla.org",
        "devdocs.io",
        "readthedocs.org",
        "gitbook.com",
        "docusaurus.io",
        "mkdocs.org",
        "sphinx-doc.org",
        "doxygen.nl",
        "javadoc.io",
        "rubydoc.info",
        "hexdocs.pm",
    ],
    "Government & Education": [
        "usa.gov",
        "nasa.gov",
        "cdc.gov",
        "nih.gov",
        "mit.edu",
        "stanford.edu",
        "harvard.edu",
        "berkeley.edu",
        "ox.ac.uk",
        "cam.ac.uk",
    ],
    "Health": [
        "webmd.com",
        "healthline.com",
        "mayoclinic.org",
        "clevelandclinic.org",
        "medlineplus.gov",
    ],
    "Finance": [
        "chase.com",
        "bankofamerica.com",
        "wellsfargo.com",
        "paypal.com",
        "coinbase.com",
        "robinhood.com",
        "fidelity.com",
        "schwab.com",
        "stripe.dev",
    ],
}


@dataclass
class SiteResult:
    domain: str
    category: str
    status: str  # "found", "not_found", "html_page", "error", "timeout"
    status_code: int = 0
    content_type: str = ""
    content_length: int = 0
    first_lines: str = ""  # first 3 lines for verification


def check_site(domain: str, category: str) -> SiteResult:
    result = SiteResult(domain=domain, category=category, status="unknown")
    url = f"https://{domain}/llms.txt"

    try:
        resp = requests.get(
            url,
            timeout=8,
            headers={
                "User-Agent": "agent-bench-research/1.0",
                "Accept": "text/plain, text/markdown, */*",
            },
            allow_redirects=True,
        )
        result.status_code = resp.status_code
        result.content_type = resp.headers.get("Content-Type", "")

        if resp.status_code == 200:
            content = resp.text.strip()
            # Check if it's actually HTML (error page, not real llms.txt)
            if (
                content.startswith("<!")
                or content.startswith("<html")
                or content.startswith("<HTML")
            ):
                result.status = "html_page"
            elif (
                "domain is for sale" in content.lower()
                or "buy this domain" in content.lower()
            ):
                result.status = "parked_domain"
            elif len(content) < 10:
                result.status = "empty"
            else:
                result.status = "found"
                result.content_length = len(content)
                lines = content.split("\n")[:3]
                result.first_lines = "\n".join(lines)
        elif resp.status_code == 404:
            result.status = "not_found"
        else:
            result.status = f"http_{resp.status_code}"
    except requests.Timeout:
        result.status = "timeout"
    except Exception as e:
        result.status = f"error: {str(e)[:80]}"

    return result


def main():
    out_dir = Path(__file__).parent
    all_results: list[SiteResult] = []

    tasks = []
    for category, domains in SITES.items():
        for domain in domains:
            tasks.append((domain, category))

    print(f"Checking /llms.txt on {len(tasks)} sites...")

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(check_site, d, c): (d, c) for d, c in tasks}
        for i, future in enumerate(as_completed(futures), 1):
            domain, cat = futures[future]
            try:
                result = future.result()
                all_results.append(result)
                icon = "✓" if result.status == "found" else "✗"
                extra = (
                    f" ({result.content_length}B)" if result.status == "found" else ""
                )
                print(f"  [{i}/{len(tasks)}] {icon} {domain}: {result.status}{extra}")
            except Exception as e:
                print(f"  [{i}/{len(tasks)}] {domain}: FAILED - {e}", file=sys.stderr)

    cat_order = list(SITES.keys())
    all_results.sort(
        key=lambda r: (
            cat_order.index(r.category) if r.category in cat_order else 99,
            r.domain,
        )
    )

    # Deduplicate (stripe.com appears in both SaaS and Finance categories — keep first)
    seen = set()
    deduped = []
    for r in all_results:
        if r.domain not in seen:
            seen.add(r.domain)
            deduped.append(r)
    all_results = deduped

    # CSV
    csv_path = out_dir / "llms_txt_survey.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "domain",
                "category",
                "status",
                "status_code",
                "content_type",
                "content_length_bytes",
                "first_lines",
            ]
        )
        for r in all_results:
            writer.writerow(
                [
                    r.domain,
                    r.category,
                    r.status,
                    r.status_code,
                    r.content_type,
                    r.content_length,
                    r.first_lines,
                ]
            )
    print(f"\nWrote {csv_path}")

    # JSON
    json_path = out_dir / "llms_txt_survey.json"
    found = [r for r in all_results if r.status == "found"]
    total_checked = len(all_results)

    cat_summary = {}
    for cat in SITES:
        cat_results = [r for r in all_results if r.category == cat]
        cat_found = [r for r in cat_results if r.status == "found"]
        cat_summary[cat] = {
            "total": len(cat_results),
            "found": len(cat_found),
            "adoption_pct": round(len(cat_found) / len(cat_results) * 100, 1)
            if cat_results
            else 0,
        }

    json_data = {
        "metadata": {
            "description": "llms.txt adoption survey across popular websites",
            "date": time.strftime("%Y-%m-%d"),
            "total_sites": total_checked,
            "sites_with_llms_txt": len(found),
            "adoption_rate_pct": round(len(found) / total_checked * 100, 1),
            "methodology": "Fetched /llms.txt from each domain over HTTPS. Counted as 'found' if 200 status with non-HTML text content of 10+ characters.",
        },
        "category_summary": cat_summary,
        "sites": [
            {
                "domain": r.domain,
                "category": r.category,
                "status": r.status,
                "status_code": r.status_code,
                "content_type": r.content_type,
                "content_length_bytes": r.content_length,
            }
            for r in all_results
        ],
    }

    with open(json_path, "w") as f:
        json.dump(json_data, f, indent=2)
    print(f"Wrote {json_path}")

    # Summary
    print(f"\n{'=' * 60}")
    print(
        f"SUMMARY: {total_checked} sites checked, {len(found)} have llms.txt ({round(len(found) / total_checked * 100, 1)}%)"
    )
    print(f"{'=' * 60}")
    for cat, stats in cat_summary.items():
        print(f"  {cat}: {stats['found']}/{stats['total']} ({stats['adoption_pct']}%)")
    print("\nSites with llms.txt:")
    for r in found:
        print(f"  {r.domain} ({r.category}, {r.content_length}B)")


if __name__ == "__main__":
    main()
