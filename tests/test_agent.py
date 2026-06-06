from app.llm.base import Candidate
from app.agent import format_candidates, make_start_message, apply_form_updates

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


def test_apply_form_updates_merges_changes_ignores_none_and_is_pure():
    current = {"ka": "KA-01036", "address": "1 Main St", "apartment": "4B"}
    updated = apply_form_updates(current, {"apartment": "5C", "borough": "MANHATTAN",
                                           "description": None})
    assert updated["apartment"] == "5C"        # user feedback changed a field
    assert updated["borough"] == "MANHATTAN"   # new field added
    assert updated["ka"] == "KA-01036"         # untouched field preserved
    assert "description" not in updated         # None means "don't set"
    assert current["apartment"] == "4B"         # original not mutated
