"""Speech-to-text via Gemini audio (multimodal). Used for the 200-file accuracy test
and the live demo (browser-recorded audio). Single thin API call — no local model."""

from __future__ import annotations

import os

STT_MODEL = os.environ.get("STT_MODEL", "gemini-3.1-flash-lite")

_PROMPT = ("Transcribe this audio to text verbatim. "
           "Output ONLY the transcription with no preamble, labels, or quotes.")

_client = None


def _client_():
    global _client
    if _client is None:
        from google import genai
        key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        _client = genai.Client(api_key=key)
    return _client


def transcribe_audio(data: bytes, mime: str = "audio/mpeg") -> str:
    from google.genai import types
    resp = _client_().models.generate_content(
        model=STT_MODEL,
        contents=[types.Part.from_bytes(data=data, mime_type=mime), _PROMPT],
    )
    return (resp.text or "").strip()
