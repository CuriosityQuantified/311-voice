import os
import json
from typing import List, Dict, Any

try:
    from pinecone import Pinecone
    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False

INDEX_NAME = "311-voice"
NAMESPACE = "nyc-311"
EMBEDDING_MODEL = "llama-text-embed-v2"
RERANK_MODEL = "bge-reranker-v2-m3"

def _get_pc():
    if not PINECONE_AVAILABLE:
        raise RuntimeError("pinecone SDK not installed")
    key = os.environ.get("PINECONE_API_KEY")
    if not key:
        raise RuntimeError("PINECONE_API_KEY not set")
    return Pinecone(api_key=key)


def query_311_content(query: str, top_k: int = 5, submittable_only: bool = True) -> List[Dict[str, Any]]:
    """
    Query Pinecone with integrated inference + rerank.
    Falls back to local JSON search if Pinecone is unavailable.
    """
    # Try Pinecone first
    try:
        pc = _get_pc()
        idx = pc.Index(INDEX_NAME)

        # 1. Embed query
        embedding = idx.inference.embed(
            model=EMBEDDING_MODEL,
            inputs=[query],
            parameters={"input_type": "query", "truncate": "END"},
        )
        vec = embedding[0]["values"]

        # 2. Vector search
        results = idx.query(
            namespace=NAMESPACE,
            vector=vec,
            top_k=top_k * 3,
            include_metadata=True,
        )

        passages = []
        for match in results["matches"]:
            meta = match["metadata"]
            if submittable_only and meta.get("classification") != "submittable":
                continue
            passages.append({
                "id": meta.get("id", ""),
                "title": meta.get("title", ""),
                "description": meta.get("description", ""),
                "classification": meta.get("classification", "unknown"),
                "categories": json.loads(meta.get("categories", "[]")),
                "text": meta.get("text", ""),
            })

        # 3. Rerank
        if len(passages) > 1:
            rerank = idx.inference.rerank(
                model=RERANK_MODEL,
                query=query,
                documents=[p["text"] for p in passages],
                top_n=top_k,
                return_documents=True,
            )
            out = []
            for r in rerank["data"]:
                p = passages[r["index"]]
                out.append({
                    "id": p["id"],
                    "title": p["title"],
                    "description": p["description"],
                    "classification": p["classification"],
                    "score": r["score"],
                    "categories": p["categories"],
                })
            return out
        else:
            return [
                {
                    "id": p["id"],
                    "title": p["title"],
                    "description": p["description"],
                    "classification": p["classification"],
                    "score": 1.0,
                    "categories": p["categories"],
                }
                for p in passages[:top_k]
            ]
    except Exception as e:
        # Fallback: local JSON search (simple keyword matching)
        return _local_search(query, top_k, submittable_only)


def _local_search(query: str, top_k: int, submittable_only: bool) -> List[Dict[str, Any]]:
    """Fallback search using local JSON data."""
    import json
    data_path = os.path.join(os.path.dirname(__file__), "..", "data", "311-content.json")
    with open(data_path) as f:
        data = json.load(f)

    q = query.lower()
    scored = []
    for item in data:
        if submittable_only and item.get("classification") != "submittable":
            continue
        title = item.get("title", "").lower()
        desc = item.get("description", "").lower()
        score = 0
        for word in q.split():
            if word in title:
                score += 3
            if word in desc:
                score += 1
        if score > 0:
            scored.append((score, item))

    scored.sort(key=lambda x: x[0], reverse=True)
    results = []
    for score, item in scored[:top_k]:
        results.append({
            "id": item["id"],
            "title": item["title"],
            "description": item["description"],
            "classification": item.get("classification", "unknown"),
            "score": float(score),
            "categories": item.get("categories", []),
        })
    return results
