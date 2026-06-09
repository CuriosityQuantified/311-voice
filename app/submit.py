"""Mock NYC 311 CreateServiceRequest submission.

build_payload merges the KA's categorical mapping (agency/problem/problemDetails/
locationType) with the user's open-text fields into NYC's CreateServiceRequest shape.
mock_submit wraps it with a fake SR number — we NEVER POST to the real API.
"""

from __future__ import annotations

import uuid


def _normalize_borough(value: str) -> str:
    """Frontend may send a code like 'STATEN_ISLAND'; NYC expects 'STATEN ISLAND'."""
    return (value or "").replace("_", " ").strip().upper()


def build_payload(submission: dict, mapping: dict) -> dict:
    m = mapping[submission["ka"]]  # KeyError on unmapped KA — caller surfaces 4xx
    return {
        # categorical (must match NYC known values) — from the mapping
        "agency": m["agency"],
        "problem": m["problem"],
        "problemDetails": m["problemDetails"],
        "locationType": m["locationType"],
        # open-text — from the user's spoken complaint + form
        "description": "N/A",
        "additionalDetails": submission.get("description", ""),
        "fullAddress": submission.get("address", ""),
        "siteBorough": _normalize_borough(submission.get("borough", "")),
        "apartmentNumber": submission.get("apartment", ""),
        "locationDetails": submission.get("locationDetails", ""),
        # provenance
        "srsource": 614110008,  # iPhone
    }


def _new_sr_number() -> str:
    return f"311-MOCK-{uuid.uuid4().hex[:8].upper()}"


def mock_submit(submission: dict, mapping: dict, sr_number: str | None = None) -> dict:
    # Universal submission: ANY of the 2,084 corpus KAs files as a mock, not just the 54 with a
    # hand-curated categorical mapping. Mock-only (never POSTed to NYC), so an unmapped KA needs
    # no categorical lookup — we do not index `mapping` here, which is why it never raises.
    # Return the original submission as the payload so the frontend can display what was actually
    # submitted (ka, description, address, borough, apartment, locationDetails, photo_b64).
    # The NYC 311 payload (agency, problem, etc.) is built here but not returned — we never
    # POST it to the real API (mock submission only).
    return {
        "sr_number": sr_number or _new_sr_number(),
        "payload": submission,
        "status": "mock-submitted",
    }
