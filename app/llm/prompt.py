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


def selection_schema(kas: list[str]) -> dict:
    """JSON Schema for a structured Selection, with picked_ka constrained to `kas` (the
    current candidate ids). Used as OpenAI/llama.cpp `response_format` json_schema."""
    return {
        "type": "object",
        "properties": {
            "picked_ka": {"type": "string", "enum": list(kas)},
            "reasoning": {"type": "string"},
            "confidence": {"type": "number"},
        },
        "required": ["picked_ka", "reasoning", "confidence"],
        "additionalProperties": False,
    }


def gemini_selection_schema(kas: list[str]) -> dict:
    """Same schema in the Gemini `response_schema` dialect (uppercase types +
    propertyOrdering)."""
    return {
        "type": "OBJECT",
        "properties": {
            "picked_ka": {"type": "STRING", "enum": list(kas)},
            "reasoning": {"type": "STRING"},
            "confidence": {"type": "NUMBER"},
        },
        "required": ["picked_ka", "reasoning", "confidence"],
        "propertyOrdering": ["picked_ka", "reasoning", "confidence"],
    }


def _fallback(candidates: list[Candidate], why: str) -> Selection:
    top = max(candidates, key=lambda c: c.score)
    return Selection(picked_ka=top.ka,
                     reasoning=f"Fallback to top match ({top.title}); {why}.",
                     confidence=top.score)


def _norm_ka(value) -> str:
    """Normalize a KA id for tolerant matching: lowercase, keep only alphanumerics, and
    drop a leading 'ka' prefix. So 'KA-01093', 'ka-01093', and '01093' all map to '01093'."""
    s = "".join(ch for ch in str(value).lower() if ch.isalnum())
    return s[2:] if s.startswith("ka") else s


def _match_ka(picked, candidates: list[Candidate]) -> str | None:
    """Resolve the model's picked_ka to a real candidate id, tolerating a dropped 'KA-'
    prefix / case differences (Qwen frequently returns the bare number)."""
    if picked is None:
        return None
    by_exact = {c.ka for c in candidates}
    if picked in by_exact:
        return picked
    target = _norm_ka(picked)
    for c in candidates:
        if _norm_ka(c.ka) == target:
            return c.ka
    return None


def parse_selection(text: str, candidates: list[Candidate]) -> Selection:
    # LLMs often wrap JSON in prose or ```fences```; extract the {...} span.
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return _fallback(candidates, "model returned no JSON")
    try:
        data = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return _fallback(candidates, "model returned unparseable JSON")

    picked = _match_ka(data.get("picked_ka"), candidates)
    if picked is None:
        return _fallback(candidates, "model returned an invalid choice")
    return Selection(
        picked_ka=picked,
        reasoning=data.get("reasoning", ""),
        confidence=float(data.get("confidence", 0.0)),
    )
