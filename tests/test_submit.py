import pytest

from app.submit import build_payload, mock_submit

MAPPING = {
    "KA-01036": {"agency": "HPD", "problem": "Heat/Hot Water",
                 "problemDetails": "Apartment Only", "locationType": "Apartment"},
}


def test_build_payload_merges_mapping_categoricals_and_user_text():
    sub = {"ka": "KA-01036", "description": "no heat for 3 days",
           "address": "123 Main St", "borough": "MANHATTAN", "apartment": "4B"}
    p = build_payload(sub, MAPPING)
    # categorical fields come from the mapping
    assert p["agency"] == "HPD"
    assert p["problem"] == "Heat/Hot Water"
    assert p["problemDetails"] == "Apartment Only"
    assert p["locationType"] == "Apartment"
    # open-text fields come from the user submission (NYC field names)
    assert p["additionalDetails"] == "no heat for 3 days"
    assert p["fullAddress"] == "123 Main St"
    assert p["siteBorough"] == "MANHATTAN"
    assert p["apartmentNumber"] == "4B"


def test_build_payload_rejects_unmapped_ka():
    with pytest.raises(KeyError):
        build_payload({"ka": "KA-99999", "description": "x"}, MAPPING)


def test_mock_submit_returns_sr_number_and_payload():
    sub = {"ka": "KA-01036", "description": "no heat", "address": "1 Broadway",
           "borough": "MANHATTAN"}
    res = mock_submit(sub, MAPPING, sr_number="311-MOCK-00000001")
    assert res["sr_number"] == "311-MOCK-00000001"
    assert res["status"] == "mock-submitted"
    assert res["payload"]["agency"] == "HPD"
