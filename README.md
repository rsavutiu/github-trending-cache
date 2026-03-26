# github-trending-cache

A free, serverless backend that caches trending GitHub repositories daily via GitHub Actions and serves them as static JSON through GitHub Pages.

Built as the data backend for [GithubPublicRepoBrowser](https://github.com/rsavutiu/GithubPublicRepoBrowser).

## How it works

1. A GitHub Actions workflow runs daily at 04:15 UTC
2. A Python script queries GitHub's search API for trending repos across multiple time periods and topics
3. The resulting JSON files are committed to `data/` and deployed to GitHub Pages
4. The Android app fetches these lightweight JSON files instead of hitting the GitHub API directly

## Live endpoints

Base URL: `https://rsavutiu.github.io/github-trending-cache/`

| Endpoint | Description |
|----------|-------------|
| [`index.json`](https://rsavutiu.github.io/github-trending-cache/index.json) | Metadata: available topics, periods, last updated timestamp |
| [`trending-daily.json`](https://rsavutiu.github.io/github-trending-cache/trending-daily.json) | Repos created in the last 24 hours, sorted by stars |
| [`trending-weekly.json`](https://rsavutiu.github.io/github-trending-cache/trending-weekly.json) | Repos created in the last 7 days |
| [`trending-monthly.json`](https://rsavutiu.github.io/github-trending-cache/trending-monthly.json) | Repos created in the last 30 days |
| [`trending-yearly.json`](https://rsavutiu.github.io/github-trending-cache/trending-yearly.json) | Repos created in the last 365 days |
| [`topics/{name}.json`](https://rsavutiu.github.io/github-trending-cache/topics/kotlin.json) | Trending repos for a specific topic (weekly window) |

## Cached topics

The current topic list is configured in [`scripts/topics.json`](scripts/topics.json):

kotlin, android, java, python, javascript, typescript, rust, go, swift, flutter, react, vue, nextjs, machine-learning, deep-learning, data-science, docker, kubernetes, devops, web

To add or remove topics, edit that file. The Android app discovers available topics dynamically from `index.json`.

## JSON schema

Each trending file contains:

```json
{
  "generatedAt": "2026-03-26T04:15:00Z",
  "period": "daily",
  "totalCount": 1234,
  "repos": [
    {
      "id": "12345",
      "name": "repo-name",
      "nameWithOwner": "owner/repo-name",
      "description": "...",
      "url": "https://github.com/owner/repo-name",
      "stargazerCount": 500,
      "forkCount": 42,
      "languageName": "Kotlin",
      "ownerLogin": "owner",
      "ownerAvatarUrl": "https://avatars.githubusercontent.com/u/123",
      "topics": ["kotlin", "android"],
      "licenseName": "MIT",
      "createdAt": "2026-03-25T10:00:00Z",
      "updatedAt": "2026-03-26T01:00:00Z"
    }
  ]
}
```

Fields match the `Repo` data class in the Android app for direct deserialization.

## Running manually

Trigger the workflow from the Actions tab or via CLI:

```bash
gh workflow run update-data.yml
```

To run the script locally:

```bash
pip install requests
export GITHUB_TOKEN=ghp_your_token_here  # optional, increases rate limit
python scripts/fetch_trending.py
```

## Rate limits

- Without token: 10 search requests/minute (script takes ~2.5 min)
- With `GITHUB_TOKEN`: 30 search requests/minute (script takes ~50 sec)
- The GitHub Actions workflow uses the built-in `GITHUB_TOKEN` automatically
