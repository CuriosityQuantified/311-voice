from app.llm.base import Candidate
from app.llm.gemini import GeminiBackend

CANDS = [
    Candidate("KA-01036", "Heat or Hot Water", "no heat", 0.91, "submittable"),
    Candidate("KA-01093", "Pothole", "hole in the road", 0.40, "submittable"),
]


def test_gemini_backend_wires_prompt_through_model_to_selection():
    """select_service builds a prompt containing the complaint, sends it to the model
    (injected here), and parses the model's JSON into a Selection. No network."""
    captured = {}

    def fake_generate(prompt: str) -> str:
        captured["prompt"] = prompt
        return '{"picked_ka": "KA-01093", "reasoning": "pothole", "confidence": 0.7}'

    backend = GeminiBackend(generate=fake_generate)
    sel = backend.select_service("there is a big hole in the road", CANDS)

    assert sel.picked_ka == "KA-01093"
    assert "hole in the road" in captured["prompt"]   # complaint reached the model
