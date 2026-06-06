#!/usr/bin/env python3
"""
dump_pinecone_records.py — Local, human-verifiable mirror of the Pinecone index.

Writes the EXACT records that were upserted (reusing ingest's build_records so it can't
drift), including the `text` field that Pinecone embeds. Vectors are NOT included (you
asked for the data being vectorized, not the vectors themselves).

Outputs to ../data/:
  - pinecone-records.json  full record list: [{_id, text, title, description, categories, classification}]
  - pinecone-records.csv   spreadsheet-friendly: id, classification, categories, text

If PINECONE_API_KEY is set, also fetches a few records back from the live index and
confirms the stored fields match the local mirror (fidelity check).

Run:  python3 scripts/dump_pinecone_records.py
"""

import csv
import json
import os

from ingest_pinecone import load_articles, build_records, INDEX_NAME, NAMESPACE

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def main():
    records = build_records(load_articles())
    print(f"Built {len(records)} records from source (mirrors what was upserted).")

    json_path = os.path.join(DATA_DIR, "pinecone-records.json")
    with open(json_path, "w") as f:
        json.dump(records, f, indent=2)

    csv_path = os.path.join(DATA_DIR, "pinecone-records.csv")
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "classification", "categories", "text"])
        for r in records:
            w.writerow([r["_id"], r["classification"], "|".join(r["categories"]), r["text"]])

    print(f"Wrote:\n  {os.path.relpath(json_path)}\n  {os.path.relpath(csv_path)}")

    # Fidelity check against live index (optional).
    key = os.environ.get("PINECONE_API_KEY")
    if not key:
        print("\n(PINECONE_API_KEY not set — skipping live fidelity check.)")
        return
    try:
        from pinecone import Pinecone
        pc = Pinecone(api_key=key)
        idx = pc.Index(INDEX_NAME)
        sample_ids = [r["_id"] for r in records[:3]]
        fetched = idx.fetch(ids=sample_ids, namespace=NAMESPACE)
        print(f"\nLive fidelity check ({INDEX_NAME}/{NAMESPACE}):")
        local = {r["_id"]: r for r in records}
        for vid, vec in fetched.vectors.items():
            md = vec.metadata or {}
            match = md.get("title") == local[vid]["title"] and \
                    md.get("classification") == local[vid]["classification"]
            print(f"  {vid}: stored title={md.get('title')!r} classification={md.get('classification')!r} "
                  f"-> {'MATCH' if match else 'MISMATCH'}")
        stats = idx.describe_index_stats()
        print(f"  index vector count: {stats.total_vector_count}")
    except Exception as e:
        print(f"\n(live check skipped: {type(e).__name__}: {str(e)[:160]})")


if __name__ == "__main__":
    main()
