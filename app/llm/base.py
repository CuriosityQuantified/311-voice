"""LLM abstraction for picking the best 311 service from reranked candidates.

The public interface is `LLMBackend.select_service(complaint, candidates) -> Selection`.
Concrete backends: FakeBackend (tests), GeminiBackend (cloud), SLMBackend (local llama).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Candidate:
    ka: str
    title: str
    description: str
    score: float
    classification: str = "unlabeled"


@dataclass
class Selection:
    picked_ka: str
    reasoning: str
    confidence: float


class LLMBackend(ABC):
    @abstractmethod
    def select_service(self, complaint: str, candidates: list[Candidate]) -> Selection:
        """Pick the best-matching candidate for the complaint."""
        raise NotImplementedError
