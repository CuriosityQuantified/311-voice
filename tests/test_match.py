from app.match import parse_hits, run_match
from app.llm.fake import FakeBackend


class _Hit:
    """Duck-typed stand-in for a Pinecone Hit (.id/.score/.fields)."""
    def __init__(self, id, score, fields):
        self.id, self.score, self.fields = id, score, fields


def test_parse_hits_maps_pinecone_hits_to_candidates():
    hits = [
        _Hit("KA-01036", 0.91, {"title": "Heat or Hot Water", "description": "no heat",
                                "classification": "submittable"}),
        _Hit("KA-01093", 0.40, {"title": "Pothole", "description": "road hole",
                                "classification": "submittable"}),
    ]
    cands = parse_hits(hits)

    assert [c.ka for c in cands] == ["KA-01036", "KA-01093"]
    assert cands[0].title == "Heat or Hot Water"
    assert cands[0].description == "no heat"
    assert cands[0].score == 0.91
    assert cands[0].classification == "submittable"


def test_run_match_returns_candidates_and_llm_pick():
    hits = [
        _Hit("KA-01093", 0.40, {"title": "Pothole", "description": "road hole",
                                "classification": "submittable"}),
        _Hit("KA-01036", 0.91, {"title": "Heat or Hot Water", "description": "no heat",
                                "classification": "submittable"}),
    ]
    result = run_match("no heat in my apartment", retrieve=lambda text: hits,
                       backend=FakeBackend())

    assert len(result["candidates"]) == 2
    assert result["picked_ka"] == "KA-01036"     # FakeBackend picks top score
    assert result["reasoning"]                    # non-empty

