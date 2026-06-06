#!/usr/bin/env python3
"""
fetch_311_content.py — Regenerate the 311-voice source dataset from the live NYC 311 API.

Pulls every category via GetCategory, then every content article per category via
GetContentList, dedupes by KA id, and writes the unified source data used to build
the pgvector (or ChromaDB) store.

Outputs (to ../data/):
  - 311-categories.json     raw category tree
  - 311-content.json        deduped content articles: [{id, title, description, categories:[...]}]
  - 311-content.jsonl       one article per line (convenient for embedding pipelines)

Auth: reads NYC_311_SUBSCRIPTION_KEY from env, else falls back to the project key.
Rate limit: NYC gateway ~30 req/min. We throttle + back off on HTTP 429.
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error

KEY = os.environ.get("NYC_311_SUBSCRIPTION_KEY", "432af080a9ae45418cea43b1bc465dcd")
BASE = os.environ.get("NYC_311_READ_BASE", "https://api.nyc.gov/public/api")
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

THROTTLE_SEC = 2.2          # ~27 req/min, under the ~30/min ceiling
MAX_RETRIES = 5
TIMEOUT = 30


def get(path):
    """GET {BASE}/{path} with the subscription header. Retries on 429 with backoff."""
    url = f"{BASE}/{path}"
    req = urllib.request.Request(url, headers={
        "Cache-Control": "no-cache",
        "Ocp-Apim-Subscription-Key": KEY,
    })
    for attempt in range(MAX_RETRIES):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = (attempt + 1) * 5
                print(f"  429 rate-limited, backing off {wait}s...", file=sys.stderr)
                time.sleep(wait)
                continue
            raise
    raise RuntimeError(f"giving up on {url} after {MAX_RETRIES} retries")


def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    print("Fetching category tree...", file=sys.stderr)
    cats = get("GetCategory")["Categories"]
    cat_ids = [c["CategoryId"] for c in cats]
    with open(os.path.join(DATA_DIR, "311-categories.json"), "w") as f:
        json.dump(cats, f, indent=2)
    print(f"  {len(cat_ids)} categories", file=sys.stderr)

    # Dedupe articles by KA id; track which categories each appears in.
    by_id = {}
    for i, cid in enumerate(cat_ids, 1):
        time.sleep(THROTTLE_SEC)
        try:
            data = get(f"GetContentList?CategoryID={cid}")
        except urllib.error.HTTPError as e:
            print(f"  [{i}/{len(cat_ids)}] {cid}: HTTP {e.code}, skipping", file=sys.stderr)
            continue
        articles = data.get("ContentArticleList") or []
        for a in articles:
            kid = a.get("id")
            if not kid:
                continue
            if kid not in by_id:
                by_id[kid] = {
                    "id": kid,
                    "title": a.get("title", ""),
                    "description": a.get("description", ""),
                    "categories": [],
                }
            if cid not in by_id[kid]["categories"]:
                by_id[kid]["categories"].append(cid)
        print(f"  [{i}/{len(cat_ids)}] {cid}: {len(articles)} articles "
              f"(total unique: {len(by_id)})", file=sys.stderr)

    content = sorted(by_id.values(), key=lambda x: x["id"])
    with open(os.path.join(DATA_DIR, "311-content.json"), "w") as f:
        json.dump(content, f, indent=2)
    with open(os.path.join(DATA_DIR, "311-content.jsonl"), "w") as f:
        for item in content:
            f.write(json.dumps(item) + "\n")

    print(f"\nDone. {len(content)} unique articles written to {DATA_DIR}/311-content.json",
          file=sys.stderr)


if __name__ == "__main__":
    main()
