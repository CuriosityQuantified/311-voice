"""Real Pinecone retriever: integrated-inference search + rerank → hit list.

Returns the raw Pinecone Hit objects (parse_hits turns them into Candidates), so this
is the `retrieve` injected into run_match in production.
"""

from __future__ import annotations

import os

INDEX_NAME = os.environ.get("PINECONE_INDEX", "311-voice")
NAMESPACE = os.environ.get("PINECONE_NAMESPACE", "nyc-311")
RERANK_MODEL = "bge-reranker-v2-m3"


def make_retriever(top_k: int = 40, top_n: int = 5):
    from pinecone import Pinecone
    pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
    index = pc.Index(INDEX_NAME)

    def retrieve(text: str):
        res = index.search(
            namespace=NAMESPACE,
            query={"inputs": {"text": text}, "top_k": top_k},
            rerank={"model": RERANK_MODEL, "top_n": top_n, "rank_fields": ["text"]},
            fields=["title", "description", "classification"],
        )
        return res["result"]["hits"]

    return retrieve
