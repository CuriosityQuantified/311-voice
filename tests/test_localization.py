"""Outbound localization helpers (app/stt.py): translate English internal strings INTO the
language the resident spoke, for display only. The internal pipeline (Pinecone match, KA ids,
NYC payload) stays English; only user-facing text is translated on the way out.

The Gemini client is mocked so these run without credentials/network.
"""

import json

import app.stt as stt


class _FakeResp:
    def __init__(self, text):
        self.text = text


class _FakeModels:
    def __init__(self, handler):
        self._handler = handler

    def generate_content(self, model, contents):
        return _FakeResp(self._handler(contents))


class _FakeClient:
    def __init__(self, handler):
        self.models = _FakeModels(handler)


def _install_fake(monkeypatch, handler):
    monkeypatch.setattr(stt, "_client_", lambda: _FakeClient(handler))


# ── translate_from_english ──────────────────────────────────────

def test_translate_from_english_noop_for_english(monkeypatch):
    # Must not call Gemini at all for English.
    def boom(contents):
        raise AssertionError("Gemini should not be called for en")
    _install_fake(monkeypatch, boom)
    assert stt.translate_from_english("Heat complaint", "en") == "Heat complaint"


def test_translate_from_english_noop_for_empty(monkeypatch):
    def boom(contents):
        raise AssertionError("Gemini should not be called for empty text")
    _install_fake(monkeypatch, boom)
    assert stt.translate_from_english("", "es") == ""


def test_translate_from_english_translates(monkeypatch):
    _install_fake(monkeypatch, lambda contents: "Queja de calefacción")
    out = stt.translate_from_english("Heat complaint", "es")
    assert out == "Queja de calefacción"


# ── translate_map (batched) ─────────────────────────────────────

def test_translate_map_noop_for_english(monkeypatch):
    def boom(contents):
        raise AssertionError("Gemini should not be called for en")
    _install_fake(monkeypatch, boom)
    items = {"reply": "Hello", "title": "Pothole"}
    assert stt.translate_map(items, "en") == items


def test_translate_map_translates_all_values_one_call(monkeypatch):
    calls = {"n": 0}

    def handler(contents):
        calls["n"] += 1
        # Echo back a JSON object keyed identically, values "ES:" prefixed.
        # The prompt embeds the source JSON; pull it out to stay realistic but simple.
        return json.dumps({"reply": "Hola", "title": "Bache"})

    _install_fake(monkeypatch, handler)
    items = {"reply": "Hello", "title": "Pothole"}
    out = stt.translate_map(items, "es")
    assert out == {"reply": "Hola", "title": "Bache"}
    assert calls["n"] == 1  # batched: a single Gemini call for the whole map


def test_translate_map_graceful_on_parse_failure(monkeypatch):
    # If Gemini returns non-JSON, fall back to the original (never crash a turn).
    _install_fake(monkeypatch, lambda contents: "not json at all")
    items = {"reply": "Hello", "title": "Pothole"}
    assert stt.translate_map(items, "es") == items


def test_translate_map_empty_is_noop(monkeypatch):
    def boom(contents):
        raise AssertionError("Gemini should not be called for empty map")
    _install_fake(monkeypatch, boom)
    assert stt.translate_map({}, "es") == {}


# ── _localize_agent_out (app/main.py) ───────────────────────────
# Localizes a whole agent-turn response for display while leaving internal/canonical fields
# (picked_ka, form.ka, emergency) in English.

import app.main as main


def _fake_translate_map(items, target_lang):
    # Deterministic stand-in for Gemini: prefix every value with the target lang code.
    return {k: f"{target_lang}:{v}" for k, v in items.items()}


def _sample_out():
    return {
        "reply": "Call 911 now.",
        "reasoning": "Best match for a gas leak.",
        "picked_ka": "KA-911",
        "emergency": True,
        "candidates": [
            {"ka": "KA-911", "title": "Gas Leak", "description": "smell of gas",
             "score": 0.9, "classification": "emergency"},
            {"ka": "KA-01036", "title": "Heat", "description": "no heat",
             "score": 0.5, "classification": "submittable"},
        ],
        "form": {"ka": "KA-911", "description": "Resident reports a gas leak.",
                 "address": "1 Main St", "borough": "MANHATTAN"},
        "screen": "results",
    }


def test_localize_agent_out_noop_for_english(monkeypatch):
    monkeypatch.setattr(main.stt, "translate_map", _fake_translate_map)
    out = _sample_out()
    res = main._localize_agent_out(out, "en")
    assert res["reply"] == "Call 911 now."
    assert res["candidates"][0]["title"] == "Gas Leak"


def test_localize_agent_out_translates_display_fields(monkeypatch):
    monkeypatch.setattr(main.stt, "translate_map", _fake_translate_map)
    res = main._localize_agent_out(_sample_out(), "es")
    # user-facing text localized
    assert res["reply"] == "es:Call 911 now."
    assert res["reasoning"] == "es:Best match for a gas leak."
    assert res["candidates"][0]["title"] == "es:Gas Leak"
    assert res["candidates"][1]["description"] == "es:no heat"
    assert res["form"]["description"] == "es:Resident reports a gas leak."


def test_localize_agent_out_preserves_canonical_fields(monkeypatch):
    monkeypatch.setattr(main.stt, "translate_map", _fake_translate_map)
    res = main._localize_agent_out(_sample_out(), "es")
    # internal/canonical fields are NOT translated
    assert res["picked_ka"] == "KA-911"
    assert res["candidates"][0]["ka"] == "KA-911"
    assert res["form"]["ka"] == "KA-911"
    assert res["form"]["borough"] == "MANHATTAN"
    assert res["emergency"] is True


# ── /api/submit localized round-trip ────────────────────────────

def test_submit_translates_description_to_english_but_displays_original(monkeypatch):
    from fastapi.testclient import TestClient

    # mock_submit needs no real mapping now; stub translate_to_english deterministically.
    monkeypatch.setattr(main.stt, "translate_to_english",
                        lambda text, lang: f"EN[{text}]")
    client = TestClient(main.app)
    r = client.post("/api/submit", json={
        "ka": "KA-99999", "description": "Hay un bache en la calle",
        "address": "5 Oak Ave", "borough": "BROOKLYN", "language": "es",
    })
    assert r.status_code == 200
    body = r.json()
    # confirmation shows the ORIGINAL Spanish description (display)
    assert body["payload"]["description"] == "Hay un bache en la calle"
    # ...and an unmapped KA still files
    assert body["payload"]["ka"] == "KA-99999"
    assert body["status"] == "mock-submitted"
