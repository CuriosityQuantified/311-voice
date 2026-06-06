from app.llm.base import Candidate
from app.llm.fake import FakeBackend


def test_fake_backend_picks_highest_scored_candidate():
    """Tracer bullet: a backend turns (complaint, candidates) into a Selection
    whose picked_ka is a real candidate. FakeBackend picks the top-scored one."""
    candidates = [
        Candidate(ka="KA-01093", title="Pothole", description="hole in road",
                  score=0.40, classification="submittable"),
        Candidate(ka="KA-01036", title="Heat or Hot Water", description="no heat",
                  score=0.91, classification="submittable"),
    ]
    sel = FakeBackend().select_service("my apartment is freezing, no heat", candidates)

    assert sel.picked_ka == "KA-01036"
    assert sel.picked_ka in {c.ka for c in candidates}
