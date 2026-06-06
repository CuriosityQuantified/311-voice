"""Match a complaint to NYC 311 services via Pinecone search + rerank, then LLM pick.

Layers:
  parse_hits(hits)              — pure: Pinecone Hit objects -> list[Candidate]
  run_match(text, retrieve, backend) — orchestration: retrieve -> parse -> LLM select
"""

from __future__ import annotations

from typing import Callable

from app.llm.base import Candidate, LLMBackend


def parse_hits(hits) -> list[Candidate]:
    """Convert Pinecone rerank hits (.id/.score/.fields) into Candidates, order preserved."""
    out = []
    for h in hits:
        f = h.fields or {}
        out.append(Candidate(
            ka=h.id,
            title=f.get("title", ""),
            description=f.get("description", ""),
            score=float(h.score),
            classification=f.get("classification", "unlabeled"),
        ))
    return out


def run_match(text: str, retrieve: Callable[[str], list], backend: LLMBackend) -> dict:
    """Orchestrate a match: retrieve reranked hits, parse to candidates, LLM picks one.

    `retrieve` is injected (Pinecone in prod, a stub in tests) so this stays testable.
    Returns the /api/match response shape (candidates + picked_ka + reasoning).
    """
    candidates = parse_hits(retrieve(text))
    selection = backend.select_service(text, candidates)
    return {
        "candidates": [c.__dict__ for c in candidates],
        "picked_ka": selection.picked_ka,
        "reasoning": selection.reasoning,
    }
