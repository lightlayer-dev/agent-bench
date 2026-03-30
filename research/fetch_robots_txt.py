#!/usr/bin/env python3
"""Fetch robots.txt from popular websites and check AI bot blocking status.

Outputs:
  - robots_txt_survey.csv  (machine-readable)
  - robots_txt_survey.json (structured)
  - README.md              (methodology + summary)
"""

import csv
import json
import sys
import time
import urllib.robotparser
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

import requests

AI_BOTS = [
    "GPTBot",
    "ChatGPT-User",
    "ClaudeBot",
    "anthropic-ai",
    "Google-Extended",
    "CCBot",
    "PerplexityBot",
    "Bytespider",
]

# 109 sites across 8 categories
SITES = {
    "News & Media": [
        "nytimes.com",
        "bbc.com",
        "npr.org",
        "usatoday.com",
        "huffpost.com",
        "nbcnews.com",
        "bloomberg.com",
        "forbes.com",
        "techcrunch.com",
        "vox.com",
        "theverge.com",
        "theatlantic.com",
        "buzzfeed.com",
        "wsj.com",
        "apnews.com",
        "cnn.com",
        "reuters.com",
        "theguardian.com",
        "time.com",
        "wired.com",
        "newyorker.com",
        "arstechnica.com",
    ],
    "Social Media": [
        "linkedin.com",
        "pinterest.com",
        "snapchat.com",
        "facebook.com",
        "instagram.com",
        "twitter.com",
        "youtube.com",
        "twitch.tv",
        "discord.com",
        "tiktok.com",
    ],
    "Tech / Developer": [
        "github.com",
        "gitlab.com",
        "medium.com",
        "dev.to",
        "vercel.com",
        "netlify.com",
        "cloudflare.com",
        "stripe.com",
        "twilio.com",
        "slack.com",
        "docker.com",
        "atlassian.com",
        "figma.com",
        "openai.com",
        "anthropic.com",
        "stackoverflow.com",
        "hashicorp.com",
        "digitalocean.com",
        "heroku.com",
        "aws.amazon.com",
    ],
    "E-commerce": [
        "amazon.com",
        "walmart.com",
        "target.com",
        "bestbuy.com",
        "etsy.com",
        "shopify.com",
        "nike.com",
        "homedepot.com",
        "ebay.com",
        "wayfair.com",
        "costco.com",
        "lowes.com",
    ],
    "Finance": [
        "chase.com",
        "bankofamerica.com",
        "wellsfargo.com",
        "paypal.com",
        "venmo.com",
        "robinhood.com",
        "coinbase.com",
        "fidelity.com",
        "schwab.com",
        "americanexpress.com",
    ],
    "Government": [
        "usa.gov",
        "nasa.gov",
        "cdc.gov",
        "irs.gov",
        "whitehouse.gov",
        "state.gov",
        "nih.gov",
        "fda.gov",
        "epa.gov",
        "ed.gov",
    ],
    "Education": [
        "mit.edu",
        "stanford.edu",
        "harvard.edu",
        "yale.edu",
        "berkeley.edu",
        "ox.ac.uk",
        "cam.ac.uk",
        "princeton.edu",
        "columbia.edu",
        "caltech.edu",
    ],
    "Health": [
        "webmd.com",
        "healthline.com",
        "mayoclinic.org",
        "clevelandclinic.org",
        "medlineplus.gov",
    ],
}


@dataclass
class SiteResult:
    domain: str
    category: str
    robots_txt_url: str = ""
    robots_txt_status: str = ""  # "ok", "not_found", "error", "timeout"
    bots: dict = field(
        default_factory=dict
    )  # bot_name -> "allowed" | "blocked" | "unknown"


def check_site(domain: str, category: str) -> SiteResult:
    """Fetch robots.txt and check each AI bot."""
    result = SiteResult(domain=domain, category=category)
    url = f"https://{domain}/robots.txt"
    result.robots_txt_url = url

    try:
        resp = requests.get(
            url, timeout=15, headers={"User-Agent": "agent-bench-research/1.0"}
        )
        if resp.status_code == 200:
            result.robots_txt_status = "ok"
            robots_content = resp.text
        elif resp.status_code == 404:
            result.robots_txt_status = "not_found"
            # No robots.txt = everything allowed
            for bot in AI_BOTS:
                result.bots[bot] = "allowed"
            return result
        else:
            result.robots_txt_status = f"http_{resp.status_code}"
            for bot in AI_BOTS:
                result.bots[bot] = "unknown"
            return result
    except requests.Timeout:
        result.robots_txt_status = "timeout"
        for bot in AI_BOTS:
            result.bots[bot] = "unknown"
        return result
    except Exception as e:
        result.robots_txt_status = f"error: {str(e)[:80]}"
        for bot in AI_BOTS:
            result.bots[bot] = "unknown"
        return result

    # Parse robots.txt for each bot
    for bot in AI_BOTS:
        rp = urllib.robotparser.RobotFileParser()
        rp.parse(robots_content.splitlines())
        try:
            can_fetch = rp.can_fetch(bot, "/")
            result.bots[bot] = "allowed" if can_fetch else "blocked"
        except Exception:
            result.bots[bot] = "unknown"

    return result


def main():
    out_dir = Path(__file__).parent
    all_results: list[SiteResult] = []

    # Flatten sites
    tasks = []
    for category, domains in SITES.items():
        for domain in domains:
            tasks.append((domain, category))

    print(f"Fetching robots.txt from {len(tasks)} sites...")

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(check_site, d, c): (d, c) for d, c in tasks}
        for i, future in enumerate(as_completed(futures), 1):
            domain, cat = futures[future]
            try:
                result = future.result()
                all_results.append(result)
                blocked = sum(1 for v in result.bots.values() if v == "blocked")
                status = (
                    f"{blocked}/{len(AI_BOTS)} blocked"
                    if result.robots_txt_status == "ok"
                    else result.robots_txt_status
                )
                print(f"  [{i}/{len(tasks)}] {domain}: {status}")
            except Exception as e:
                print(f"  [{i}/{len(tasks)}] {domain}: FAILED - {e}", file=sys.stderr)

    # Sort by category then domain
    cat_order = list(SITES.keys())
    all_results.sort(key=lambda r: (cat_order.index(r.category), r.domain))

    # Write CSV
    csv_path = out_dir / "robots_txt_survey.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["domain", "category", "robots_txt_status"]
            + AI_BOTS
            + ["bots_blocked", "bots_allowed"]
        )
        for r in all_results:
            blocked = sum(1 for v in r.bots.values() if v == "blocked")
            allowed = sum(1 for v in r.bots.values() if v == "allowed")
            writer.writerow(
                [r.domain, r.category, r.robots_txt_status]
                + [r.bots.get(bot, "unknown") for bot in AI_BOTS]
                + [blocked, allowed]
            )
    print(f"\nWrote {csv_path}")

    # Write JSON
    json_path = out_dir / "robots_txt_survey.json"
    json_data = {
        "metadata": {
            "description": "AI bot blocking survey of popular websites via robots.txt",
            "date": time.strftime("%Y-%m-%d"),
            "total_sites": len(all_results),
            "ai_bots_checked": AI_BOTS,
            "methodology": "Fetched /robots.txt from each domain over HTTPS, parsed with Python urllib.robotparser, checked can_fetch('/', bot) for each AI user-agent.",
        },
        "summary": {},
        "sites": [],
    }

    # Summary stats
    ok_results = [r for r in all_results if r.robots_txt_status == "ok"]
    for bot in AI_BOTS:
        blocked = sum(1 for r in ok_results if r.bots.get(bot) == "blocked")
        json_data["summary"][bot] = {
            "blocked": blocked,
            "allowed": len(ok_results) - blocked,
            "blocked_pct": round(blocked / len(ok_results) * 100, 1)
            if ok_results
            else 0,
        }

    # Category summary
    cat_summary = {}
    for cat in SITES:
        cat_results = [r for r in ok_results if r.category == cat]
        blocks_any = sum(
            1 for r in cat_results if any(v == "blocked" for v in r.bots.values())
        )
        cat_summary[cat] = {
            "total": len(cat_results),
            "blocking_any": blocks_any,
            "blocking_pct": round(blocks_any / len(cat_results) * 100, 1)
            if cat_results
            else 0,
        }
    json_data["category_summary"] = cat_summary

    for r in all_results:
        json_data["sites"].append(
            {
                "domain": r.domain,
                "category": r.category,
                "robots_txt_status": r.robots_txt_status,
                "bots": r.bots,
            }
        )

    with open(json_path, "w") as f:
        json.dump(json_data, f, indent=2)
    print(f"Wrote {json_path}")

    # Print summary
    print(f"\n{'=' * 60}")
    print(f"SUMMARY: {len(all_results)} sites checked")
    print(f"{'=' * 60}")
    for cat, stats in cat_summary.items():
        print(
            f"  {cat}: {stats['blocking_any']}/{stats['total']} block at least one bot ({stats['blocking_pct']}%)"
        )
    print()
    for bot in AI_BOTS:
        s = json_data["summary"][bot]
        print(
            f"  {bot}: blocked by {s['blocked']}/{len(ok_results)} sites ({s['blocked_pct']}%)"
        )


if __name__ == "__main__":
    main()
