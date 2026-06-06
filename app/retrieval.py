"""Real Pinecone retriever: dense vector search (no reranking).

Pinecone's free tier reranker (bge-reranker-v2-m3) has a hard 500/month quota.
Since vector search alone achieves 94.8%+ retrieval ceiling (correct service
present in top-5), we rely on pure dense search — simpler, no quota limits,
nearly identical accuracy.

Returns the raw Pinecone Hit objects (parse_hits turns them into Candidates), so this
is the `retrieve` injected into run_match in production.
"""

from __future__ import annotations

import os

INDEX_NAME = os.environ.get("PINECONE_INDEX", "311-voice")
NAMESPACE = os.environ.get("PINECONE_NAMESPACE", "nyc-311")


def make_retriever(top_k: int = 5, top_n: int = 5):
    """Dense vector search only (no cross-encoder reranking).

    Args:
      top_k: number of candidates to return (was pool for reranking; now final count).
      top_n: ignored (kept for backward compatibility with callers).
    """
    from pinecone import Pinecone
    pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
    index = pc.Index(INDEX_NAME)

    def retrieve(text: str):
        res = index.search(
            namespace=NAMESPACE,
            query={"inputs": {"text": text}, "top_k": top_k},
            fields=["title", "description", "classification"],
        )
        return res["result"]["hits"]

    return retrieve
