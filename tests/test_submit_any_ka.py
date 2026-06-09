"""Universal submission: every KA in the 2,084-record corpus must file as a mock,
not just the 54 that have a hand-curated categorical mapping.

mock_submit is a MOCK — it never POSTs to NYC and returns the raw submission as the
payload (what the frontend Confirmation screen renders). So an unmapped KA must NOT
raise: the mapping lookup is gatekeeping we are deliberately removing.
"""

from app.submit import mock_submit

MAPPING = {
    "KA-01036": {"agency": "HPD", "problem": "Heat/Hot Water",
                 "problemDetails": "Apartment Only", "locationType": "Apartment"},
}


def test_mock_submit_accepts_unmapped_ka():
    # KA-99999 is NOT in the 54-entry mapping; it must still file as a mock.
    sub = {"ka": "KA-99999", "description": "graffiti on the wall",
           "address": "5 Oak Ave", "borough": "BROOKLYN"}
    res = mock_submit(sub, MAPPING, sr_number="311-MOCK-AAAA0001")
    assert res["sr_number"] == "311-MOCK-AAAA0001"
    assert res["status"] == "mock-submitted"
    # payload is the raw submission (what the frontend renders), not a KeyError
    assert res["payload"]["ka"] == "KA-99999"
    assert res["payload"]["description"] == "graffiti on the wall"
    assert res["payload"]["address"] == "5 Oak Ave"


def test_mock_submit_still_accepts_mapped_ka():
    sub = {"ka": "KA-01036", "description": "no heat", "address": "1 Broadway",
           "borough": "MANHATTAN"}
    res = mock_submit(sub, MAPPING, sr_number="311-MOCK-AAAA0002")
    assert res["sr_number"] == "311-MOCK-AAAA0002"
    assert res["payload"]["ka"] == "KA-01036"
