import os
import json
from typing import List, Dict, Any, Optional

from app.mapping import get_mapping

# TODO: Replace with actual LangChain + OpenAI-compatible client once Claude's SLM
# endpoint is ready. For now, we use a simple heuristic selector.

SLM_API_URL = os.environ.get("SLM_API_URL", "http://localhost:8080/v1/chat/completions")
USE_SLM = os.environ.get("USE_SLM", "false").lower() == "true"


def select_best_match(query: str, matches: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Given a user query and top-k matches, return the best match.
    Stub: returns the highest-scored match for now.
    """
    if not matches:
        return None
    # Heuristic: prefer the highest score
    best = max(matches, key=lambda m: m.get("score", 0))
    return best


def fill_service_request(match: Dict[str, Any], location: Optional[str] = None) -> Dict[str, Any]:
    """
    Given a selected match, return the pre-filled service request form.
    """
    mapping = get_mapping(match["id"])
    form = {
        "match_id": match["id"],
        "title": match["title"],
        "description": match["description"],
        "location": location or "",
        "agency": "",
        "problem": "",
        "problemDetails": "",
        "locationType": "",
    }
    if mapping:
        form["agency"] = mapping.get("agency", "")
        form["problem"] = mapping.get("problem", "")
        form["problemDetails"] = mapping.get("problemDetails", "")
        form["locationType"] = mapping.get("locationType", "")
    return form


def _llm_reason(query: str, matches: List[Dict[str, Any]]) -> str:
    """
    Future: call the local SLM via OpenAI-compatible endpoint.
    """
    # Placeholder for LangChain integration
    return matches[0]["id"] if matches else ""
