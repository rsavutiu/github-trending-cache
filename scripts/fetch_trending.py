#!/usr/bin/env python3
"""
Fetches trending GitHub repositories and writes JSON files for consumption
by the GithubPublicRepoBrowser Android app.

Runs daily via GitHub Actions. Output lands in data/ and is served via GitHub Pages.
"""

import json
import os
import time
from datetime import datetime, timedelta, timezone

import requests

GITHUB_API = "https://api.github.com"
SEARCH_ENDPOINT = f"{GITHUB_API}/search/repositories"
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
TOPICS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "topics.json")

# periods: name -> days back
PERIODS = {
    "daily": 1,
    "weekly": 7,
    "monthly": 30,
    "yearly": 365,
}

PER_PAGE = 30
REQUEST_DELAY = 2  # seconds between API calls to respect rate limits


def get_headers():
    """Build request headers, using GITHUB_TOKEN if available."""
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def since_date(days_back: int) -> str:
    """Return ISO date string for N days ago."""
    dt = datetime.now(timezone.utc) - timedelta(days=days_back)
    return dt.strftime("%Y-%m-%d")


def map_repo(item: dict) -> dict:
    """Map a GitHub REST API repo item to our JSON schema (matches Repo.kt fields)."""
    owner = item.get("owner", {})
    license_info = item.get("license")
    return {
        "id": str(item["id"]),
        "name": item["name"],
        "nameWithOwner": item["full_name"],
        "description": item.get("description"),
        "url": item["html_url"],
        "stargazerCount": item.get("stargazers_count", 0),
        "forkCount": item.get("forks_count", 0),
        "languageName": item.get("language"),
        "languageColor": None,  # not available from REST search
        "ownerLogin": owner.get("login", ""),
        "ownerAvatarUrl": owner.get("avatar_url"),
        "ownerType": owner.get("type", "User"),
        "createdAt": item.get("created_at"),
        "updatedAt": item.get("updated_at"),
        "licenseName": license_info.get("spdx_id") if license_info else None,
        "topics": item.get("topics", []),
        "openIssuesCount": item.get("open_issues_count", 0),
        "closedIssuesCount": 0,  # not available from search endpoint
    }


def fetch_repos(query: str) -> tuple[list[dict], int]:
    """Fetch repos from GitHub search API. Returns (repos, total_count)."""
    params = {
        "q": query,
        "sort": "stars",
        "order": "desc",
        "per_page": PER_PAGE,
    }
    headers = get_headers()

    print(f"  GET {SEARCH_ENDPOINT}?q={query}")
    resp = requests.get(SEARCH_ENDPOINT, params=params, headers=headers, timeout=30)

    if resp.status_code == 403:
        # Rate limited — check for retry-after
        retry_after = int(resp.headers.get("Retry-After", 60))
        print(f"  Rate limited. Sleeping {retry_after}s...")
        time.sleep(retry_after)
        resp = requests.get(SEARCH_ENDPOINT, params=params, headers=headers, timeout=30)

    resp.raise_for_status()
    data = resp.json()

    repos = [map_repo(item) for item in data.get("items", [])]
    total_count = data.get("total_count", 0)
    print(f"  → {len(repos)} repos (total: {total_count})")
    return repos, total_count


def write_json(filepath: str, data: dict):
    """Write JSON data to file with pretty printing."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  Wrote {filepath}")


def fetch_trending_periods():
    """Fetch trending repos for each time period."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    for period_name, days_back in PERIODS.items():
        print(f"\nFetching trending-{period_name} (last {days_back} days)...")
        date = since_date(days_back)
        query = f"stars:>5 created:>{date} sort:stars"
        repos, total_count = fetch_repos(query)

        write_json(
            os.path.join(DATA_DIR, f"trending-{period_name}.json"),
            {
                "generatedAt": now,
                "period": period_name,
                "totalCount": total_count,
                "repos": repos,
            },
        )
        time.sleep(REQUEST_DELAY)


def fetch_topic_repos(topics: list[str]):
    """Fetch trending repos for each topic (using weekly window)."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    date = since_date(7)  # weekly window for topics

    for topic in topics:
        print(f"\nFetching topic: {topic}...")
        query = f"topic:{topic} stars:>5 created:>{date} sort:stars"
        repos, total_count = fetch_repos(query)

        write_json(
            os.path.join(DATA_DIR, "topics", f"{topic}.json"),
            {
                "generatedAt": now,
                "topic": topic,
                "totalCount": total_count,
                "repos": repos,
            },
        )
        time.sleep(REQUEST_DELAY)


def write_index(topics: list[str]):
    """Write the index.json metadata file."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    write_json(
        os.path.join(DATA_DIR, "index.json"),
        {
            "lastUpdated": now,
            "availableTopics": topics,
            "periods": list(PERIODS.keys()),
        },
    )


def main():
    print("=== GitHub Trending Cache Updater ===")
    print(f"Output dir: {DATA_DIR}")

    # Load topics
    with open(TOPICS_FILE, "r", encoding="utf-8") as f:
        topics = json.load(f)
    print(f"Topics to fetch: {len(topics)}")

    # Fetch all data
    fetch_trending_periods()
    fetch_topic_repos(topics)
    write_index(topics)

    print("\n=== Done! ===")


if __name__ == "__main__":
    main()
