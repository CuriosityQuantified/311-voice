from app.llm.base import Candidate
from app.agent import (format_candidates, make_start_message, apply_form_updates,
                       is_emergency)

CANDS = [
    Candidate("KA-01036", "Heat or Hot Water", "no heat in apartment", 0.91, "submittable"),
    Candidate("KA-01093", "Pothole", "hole in the road", 0.40, "submittable"),
]


def test_format_candidates_numbers_each_with_ka_and_title():
    s = format_candidates(CANDS)
    assert "1." in s and "2." in s
    assert "KA-01036" in s and "Heat or Hot Water" in s
    assert "KA-01093" in s and "Pothole" in s


def test_make_start_message_frames_the_complaint():
    msg = make_start_message("my apartment is freezing")
    assert "my apartment is freezing" in msg


def test_is_emergency_true_only_when_picked_is_emergency_class():
    cands = [
        Candidate("KA-911", "Gas Leak", "call 911", 0.9, "emergency"),
        Candidate("KA-01036", "Heat", "no heat", 0.5, "submittable"),
    ]
    assert is_emergency(cands, "KA-911") is True
    assert is_emergency(cands, "KA-01036") is False


def test_apply_form_updates_merges_changes_ignores_none_and_is_pure():
    current = {"ka": "KA-01036", "address": "1 Main St", "apartment": "4B"}
    updated = apply_form_updates(current, {"apartment": "5C", "borough": "MANHATTAN",
                                           "description": None})
    assert updated["apartment"] == "5C"        # user feedback changed a field
    assert updated["borough"] == "MANHATTAN"   # new field added
    assert updated["ka"] == "KA-01036"         # untouched field preserved
    assert "description" not in updated         # None means "don't set"
    assert current["apartment"] == "4B"         # original not mutated
