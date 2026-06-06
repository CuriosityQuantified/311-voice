#!/usr/bin/env python3
"""
query_pinecone.py — Search the 311 catalog with Pinecone integrated inference + rerank.

Pinecone embeds the query text server-side, retrieves top_k by cosine, then reranks
with a hosted cross-encoder (bge-reranker-v2-m3) and returns the top_n. This is the
retrieval the LangChain agent consumes: complaint text -> top-5 candidates + scores.

Env: PINECONE_API_KEY (required), PINECONE_INDEX, PINECONE_NAMESPACE (see ingest script).

Run:
  PINECONE_API_KEY=... python3 scripts/query_pinecone.py "my apartment has no heat"
  PINECONE_API_KEY=... python3 scripts/query_pinecone.py "pothole on my street" --top-k 10 --top-n 5
"""

import argparse
import os
import sys

INDEX_NAME = os.environ.get("PINECONE_INDEX", "311-voice")
NAMESPACE = os.environ.get("PINECONE_NAMESPACE", "nyc-311")
RERANK_MODEL = "bge-reranker-v2-m3"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query", help="complaint text")
    ap.add_argument("--top-k", type=int, default=10, help="candidates retrieved before rerank")
    ap.add_argument("--top-n", type=int, default=5, help="results returned after rerank")
    ap.add_argument("--submittable-only", action="store_true",
                    help="filter to classification == submittable")
    args = ap.parse_args()

    api_key = os.environ.get("PINECONE_API_KEY")
    if not api_key:
        sys.exit("ERROR: set PINECONE_API_KEY in the environment.")
    try:
        from pinecone import Pinecone
    except ImportError as e:
        sys.exit(f"ERROR: missing dependency ({e}). Run: pip install \"pinecone>=5\"")

    pc = Pinecone(api_key=api_key)
    index = pc.Index(INDEX_NAME)

    query = {"inputs": {"text": args.query}, "top_k": args.top_k}
    if args.submittable_only:
        query["filter"] = {"classification": "submittable"}

    res = index.search(
        namespace=NAMESPACE,
        query=query,
        rerank={
            "model": RERANK_MODEL,
            "top_n": args.top_n,
            "rank_fields": ["text"],
        },
        fields=["title", "description", "categories", "classification"],
    )

    hits = res["result"]["hits"]
    print(f"\nQuery: {args.query!r}\nTop {len(hits)} after rerank ({RERANK_MODEL}):\n")
    for h in hits:
        f = h["fields"]
        print(f"  {h['_score']:.4f}  {h['_id']}  {f.get('title')}  [{f.get('classification')}]")
        print(f"          {f.get('description')}")


if __name__ == "__main__":
    main()
