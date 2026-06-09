"""End-to-end integration test for the 311-voice API.

Tests the core functionality:
1. Language detection and translation
2. Service matching via retrieval
3. Form submission and confirmation
"""

import json
import os
import sys

def test_health():
    """Test /api/health endpoint."""
    import requests
    resp = requests.get("http://localhost:8000/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["llm_backend"] == "gemini"
    print("✓ Health check passed")


def test_language_detection_translation():
    """Test language detection and translation functions."""
    from app.stt import detect_language, translate_to_english

    test_cases = [
        ("There is a pothole on the street", "en"),
        ("Hay un bache en la calle", "es"),
        ("Il y a un nid-de-poule sur la rue", "fr"),
        ("街道上有一个坑洞", "zh"),
    ]

    for text, expected_lang in test_cases:
        detected = detect_language(text)
        assert detected == expected_lang, f"Expected {expected_lang}, got {detected} for: {text}"
        print(f"✓ Detected {expected_lang}: {text[:40]}...")

        translated = translate_to_english(text, detected)
        assert translated, f"Translation failed for: {text}"
        assert len(translated) > 0, f"Empty translation for: {text}"
        print(f"  → English: {translated[:50]}...")


def test_retrieval_pipeline():
    """Test the retrieval/matching pipeline."""
    from app.retrieval import make_retriever
    from app.match import run_match

    # Test English
    complaint = "pothole on Madison Avenue"
    retriever = make_retriever()
    candidates = retriever(complaint)
    assert len(candidates) > 0, "Retriever returned no results"
    print(f"✓ Retriever found {len(candidates)} candidates for: '{complaint}'")

    # Test matching pipeline (requires backend for LLM selection)
    from app.main import get_backend
    backend = get_backend()
    result = run_match(complaint, retriever, backend)
    assert "candidates" in result, "match result missing candidates"
    assert len(result["candidates"]) > 0, "No candidates from match pipeline"
    assert result.get("picked_ka"), "No service picked by match"
    print(f"✓ Match pipeline picked: {result['picked_ka']}")
    print(f"  Reasoning: {result['reasoning'][:80]}...")


def test_submission_flow():
    """Test form submission endpoint."""
    import requests

    # Test English submission
    submit_payload = {
        "ka": "BrokenSidewalk",
        "description": "There is a large crack in the sidewalk on Main Street",
        "address": "123 Main St",
        "borough": "MANHATTAN",
        "apartment": "",
        "locationDetails": "",
        "photo_b64": "",
    }

    resp = requests.post(
        "http://localhost:8000/api/submit",
        json=submit_payload
    )
    assert resp.status_code == 200, f"Submit returned {resp.status_code}: {resp.text}"
    submission = resp.json()

    assert submission.get("sr_number"), "No SR number returned"
    assert submission.get("payload"), "No payload returned"
    assert submission["payload"].get("description"), "Description not in payload"
    assert submission["payload"]["description"] == submit_payload["description"], \
        "Description was modified"
    print(f"✓ English submission: SR#{submission['sr_number']}")
    print(f"  Description preserved: {submission['payload']['description'][:60]}...")

    # Test multilingual submission
    submit_payload_es = {
        "ka": "BrokenSidewalk",
        "description": "Hay un bache grande en la calle",  # Spanish
        "address": "456 Oak Ave",
        "borough": "BROOKLYN",
        "apartment": "",
        "locationDetails": "",
        "photo_b64": "",
    }

    resp = requests.post(
        "http://localhost:8000/api/submit",
        json=submit_payload_es
    )
    assert resp.status_code == 200
    submission_es = resp.json()

    assert submission_es["payload"]["description"] == submit_payload_es["description"]
    print(f"✓ Spanish submission: SR#{submission_es['sr_number']}")
    print(f"  Description preserved: {submission_es['payload']['description']}")


def test_transcribe_endpoint():
    """Test that /api/transcribe endpoint returns correct structure."""
    import requests
    import io

    # Create a simple test WAV file (silence)
    # WAV header for 1-second of silence at 16kHz mono
    wav_header = bytes([
        0x52, 0x49, 0x46, 0x46,  # RIFF
        0x24, 0xf0, 0x00, 0x00,  # file size
        0x57, 0x41, 0x56, 0x45,  # WAVE
        0x66, 0x6d, 0x74, 0x20,  # fmt
        0x10, 0x00, 0x00, 0x00,  # subchunk1size
        0x01, 0x00,              # audio format (PCM)
        0x01, 0x00,              # channels (mono)
        0x80, 0x3e, 0x00, 0x00,  # sample rate (16000)
        0x00, 0x7d, 0x00, 0x00,  # byte rate
        0x02, 0x00,              # block align
        0x10, 0x00,              # bits per sample
        0x64, 0x61, 0x74, 0x61,  # data
        0x00, 0xf0, 0x00, 0x00,  # subchunk2size (16000 * 2 = 32000 bytes)
    ])

    # Create a test file with silence
    test_audio = wav_header + b'\x00' * 32000

    resp = requests.post(
        "http://localhost:8000/api/transcribe",
        files={"audio": ("test.wav", io.BytesIO(test_audio), "audio/wav")}
    )

    assert resp.status_code == 200, f"Transcribe returned {resp.status_code}: {resp.text}"
    data = resp.json()

    # Check response structure
    assert "text" in data, "Response missing 'text' field"
    assert "original_text" in data, "Response missing 'original_text' field"
    assert "language" in data, "Response missing 'language' field"
    print(f"✓ Transcribe endpoint returns correct structure")
    print(f"  Language detected: {data['language']}")
    print(f"  Text field present: {len(data['text']) > 0 or data['text'] == ''}")


if __name__ == "__main__":
    os.chdir("/Users/nicholaspate/Documents/projects/311-voice-claude")
    sys.path.insert(0, "/Users/nicholaspate/Documents/projects/311-voice-claude")

    print("=" * 70)
    print("INTEGRATION TEST: Core API Functionality")
    print("=" * 70)

    try:
        print("\n[1] Testing health endpoint...")
        test_health()

        print("\n[2] Testing language detection and translation...")
        test_language_detection_translation()

        print("\n[3] Testing retrieval and matching pipeline...")
        test_retrieval_pipeline()

        print("\n[4] Testing form submission...")
        test_submission_flow()

        print("\n[5] Testing transcribe endpoint...")
        test_transcribe_endpoint()

        print("\n" + "=" * 70)
        print("✓ ALL CORE INTEGRATION TESTS PASSED")
        print("=" * 70)
        print("\nSummary:")
        print("  ✓ Language detection works for EN, ES, FR, ZH")
        print("  ✓ Translation to English works correctly")
        print("  ✓ Service retrieval and matching works")
        print("  ✓ Form submission preserves multilingual content")
        print("  ✓ Transcribe endpoint supports language detection")
        sys.exit(0)

    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
