"""Shared prompt build + response parsing for the LLM backends (Gemini, SLM).

Both backends differ only in the model call; the prompt and the parse/validation logic
live here so they're tested once and reused.
"""

from __future__ import annotations

import json

from app.llm.base import Candidate, Selection

SYSTEM = (
    "You are an NYC 311 routing assistant. Given a resident's complaint and a numbered "
    "list of candidate 311 service types (already ranked by relevance), pick the SINGLE "
    "best matching service. Respond ONLY with JSON: "
    '{"picked_ka": "<KA id>", "reasoning": "<one sentence>", "confidence": <0..1>}. '
    "picked_ka MUST be one of the candidate KA ids."
)


def build_prompt(complaint: str, candidates: list[Candidate]) -> str:
    lines = [SYSTEM, "", f"Complaint: {complaint}", "", "Candidates:"]
    for i, c in enumerate(candidates, 1):
        lines.append(f"{i}. {c.ka} — {c.title}: {c.description} "
                     f"(score={c.score:.3f}, type={c.classification})")
    lines.append("")
    lines.append("Return only the JSON object.")
    return "\n".join(lines)


def _fallback(candidates: list[Candidate], why: str) -> Selection:
    top = max(candidates, key=lambda c: c.score)
    return Selection(picked_ka=top.ka,
                     reasoning=f"Fallback to top match ({top.title}); {why}.",
                     confidence=top.score)


def parse_selection(text: str, candidates: list[Candidate]) -> Selection:
    # LLMs often wrap JSON in prose or ```fences```; extract the {...} span.
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return _fallback(candidates, "model returned no JSON")
    try:
        data = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return _fallback(candidates, "model returned unparseable JSON")

    picked = data.get("picked_ka")
    if picked not in {c.ka for c in candidates}:
        return _fallback(candidates, "model returned an invalid choice")
    return Selection(
        picked_ka=picked,
        reasoning=data.get("reasoning", ""),
        confidence=float(data.get("confidence", 0.0)),
    )
