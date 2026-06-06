#!/usr/bin/env python3
"""
ingest_pinecone.py — Upsert the NYC 311 catalog into Pinecone using INTEGRATED INFERENCE.

Pinecone embeds the text server-side (hosted model), so we upsert raw TEXT records,
not precomputed vectors. Title/description/categories/classification are stored as
fields; the `text` field (title + description) is what Pinecone embeds.

Embedding model:  llama-text-embed-v2  (Pinecone-hosted, 1024-dim dense)
Reranking (query side): bge-reranker-v2-m3  (see query_pinecone.py)

This is the "integrated inference + rerank" path: no local embedding model, no local
cross-encoder. STT (whisper) still runs locally; embedding + rerank are Pinecone calls.

Env:
  PINECONE_API_KEY   required
  PINECONE_INDEX     optional, default "311-voice"
  PINECONE_CLOUD     optional, default "aws"
  PINECONE_REGION    optional, default "us-east-1"
  PINECONE_NAMESPACE optional, default "nyc-311"

Install:
  pip install "pinecone>=5"

Run:
  PINECONE_API_KEY=... python3 scripts/ingest_pinecone.py
"""

import json
import os
import sys
import time

EMBED_MODEL = "llama-text-embed-v2"   # Pinecone-hosted; index dim follows this model
BATCH = 96                            # upsert_records max records per call

DATA = os.path.join(os.path.dirname(__file__), "..", "data", "311-content.json")
INDEX_NAME = os.environ.get("PINECONE_INDEX", "311-voice")
CLOUD = os.environ.get("PINECONE_CLOUD", "aws")
REGION = os.environ.get("PINECONE_REGION", "us-east-1")
NAMESPACE = os.environ.get("PINECONE_NAMESPACE", "nyc-311")


def load_articles():
    with open(DATA) as f:
        return json.load(f)


def main():
    api_key = os.environ.get("PINECONE_API_KEY")
    if not api_key:
        sys.exit("ERROR: set PINECONE_API_KEY in the environment.")

    try:
        from pinecone import Pinecone
    except ImportError as e:
        sys.exit(f"ERROR: missing dependency ({e}). Run: pip install \"pinecone>=5\"")

    articles = load_articles()
    print(f"Loaded {len(articles)} articles from {DATA}")

    pc = Pinecone(api_key=api_key)

    if not pc.has_index(INDEX_NAME):
        print(f"Creating index '{INDEX_NAME}' for model {EMBED_MODEL} in {CLOUD}/{REGION} ...")
        pc.create_index_for_model(
            name=INDEX_NAME,
            cloud=CLOUD,
            region=REGION,
            embed={
                "model": EMBED_MODEL,
                "field_map": {"text": "text"},   # which record field gets embedded
            },
        )
        # wait until ready
        while not pc.describe_index(INDEX_NAME).status.get("ready", False):
            print("  waiting for index to be ready...")
            time.sleep(3)
    else:
        print(f"Index '{INDEX_NAME}' already exists; upserting into it.")

    index = pc.Index(INDEX_NAME)

    records = []
    for a in articles:
        records.append({
            "_id": a["id"],
            "text": f"{a['title']}. {a['description']}".strip(),  # embedded field
            "title": a["title"],
            "description": a["description"],
            "categories": a.get("categories", []),
            "classification": a.get("classification", "unlabeled"),
        })

    print(f"Upserting {len(records)} text records to namespace '{NAMESPACE}' "
          f"in batches of {BATCH} (Pinecone embeds server-side) ...")
    for i in range(0, len(records), BATCH):
        index.upsert_records(NAMESPACE, records[i:i + BATCH])
        print(f"  upserted {min(i + BATCH, len(records))}/{len(records)}")

    time.sleep(5)  # give the index a moment to reflect counts
    stats = index.describe_index_stats()
    print(f"\nDone. Index '{INDEX_NAME}' reports {stats.get('total_vector_count')} vectors.")


if __name__ == "__main__":
    main()
