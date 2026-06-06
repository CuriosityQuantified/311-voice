"""Deterministic backend for tests — no network, no model. Picks top-scored candidate."""

from __future__ import annotations

from app.llm.base import Candidate, LLMBackend, Selection


class FakeBackend(LLMBackend):
    def select_service(self, complaint: str, candidates: list[Candidate]) -> Selection:
        best = max(candidates, key=lambda c: c.score)
        return Selection(
            picked_ka=best.ka,
            reasoning=f"Highest reranker score ({best.score:.2f}): {best.title}",
            confidence=best.score,
        )
