from app.llm.base import Candidate
from app.llm.slm import SLMBackend

CANDS = [
    Candidate("KA-01036", "Heat or Hot Water", "no heat", 0.91, "submittable"),
    Candidate("KA-01093", "Pothole", "hole in the road", 0.40, "submittable"),
]


def test_slm_backend_wires_prompt_through_model_to_selection():
    captured = {}

    def fake_generate(prompt: str) -> str:
        captured["prompt"] = prompt
        return 'thinking...\n{"picked_ka": "KA-01036", "reasoning": "no heat", "confidence": 0.8}'

    backend = SLMBackend(generate=fake_generate)
    sel = backend.select_service("freezing, no heat at all", CANDS)

    assert sel.picked_ka == "KA-01036"
    assert "freezing, no heat at all" in captured["prompt"]
