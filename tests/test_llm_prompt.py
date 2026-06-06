from app.llm.base import Candidate
from app.llm.prompt import build_prompt, parse_selection

CANDS = [
    Candidate("KA-01036", "Heat or Hot Water", "no heat in apartment", 0.91, "submittable"),
    Candidate("KA-01093", "Pothole", "hole in the road", 0.40, "submittable"),
]


def test_build_prompt_includes_complaint_and_all_candidates():
    p = build_prompt("my radiator is cold", CANDS)
    assert "my radiator is cold" in p
    assert "KA-01036" in p and "Heat or Hot Water" in p
    assert "KA-01093" in p and "Pothole" in p


def test_parse_selection_parses_clean_json():
    text = '{"picked_ka": "KA-01036", "reasoning": "no heat maps to heat complaint", "confidence": 0.95}'
    sel = parse_selection(text, CANDS)
    assert sel.picked_ka == "KA-01036"
    assert "heat" in sel.reasoning.lower()
    assert sel.confidence == 0.95


def test_parse_selection_falls_back_when_ka_not_a_candidate():
    # LLM hallucinates a KA that isn't in the candidate set -> use top-scored candidate.
    text = '{"picked_ka": "KA-99999", "reasoning": "made up", "confidence": 0.5}'
    sel = parse_selection(text, CANDS)
    assert sel.picked_ka == "KA-01036"  # highest score among CANDS


def test_parse_selection_handles_fenced_and_surrounded_json():
    text = 'Sure!\n```json\n{"picked_ka":"KA-01093","reasoning":"pothole on road","confidence":0.8}\n```'
    sel = parse_selection(text, CANDS)
    assert sel.picked_ka == "KA-01093"


def test_parse_selection_falls_back_on_unparseable_text():
    sel = parse_selection("I'm not sure, could you clarify?", CANDS)
    assert sel.picked_ka == "KA-01036"  # top-scored fallback, no crash
