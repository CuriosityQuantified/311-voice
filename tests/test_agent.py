from app.llm.base import Candidate
from app.agent import format_candidates, make_start_message

CANDS = [
    Candidate("KA-01036", "Heat or Hot Water", "no heat in apartment", 0.91, "submittable"),
    Candidate("KA-01093", "Pothole", "hole in the road", 0.40, "submittable"),
]


def test_format_candidates_numbers_each_with_ka_and_title():
    s = format_candidates(CANDS)
    assert "1." in s and "2." in s
    assert "KA-01036" in s and "Heat or Hot Water" in s
    assert "KA-01093" in s and "Pothole" in s


def test_make_start_message_includes_transcript_and_candidates():
    msg = make_start_message("my apartment is freezing", CANDS)
    assert "my apartment is freezing" in msg
    assert "KA-01036" in msg and "KA-01093" in msg
