"""Speech-to-text via Gemini audio (multimodal). Used for the 200-file accuracy test
and the live demo (browser-recorded audio). Single thin API call — no local model."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile

STT_MODEL = os.environ.get("STT_MODEL", "gemini-3.1-flash-lite")

_PROMPT = ("Transcribe this audio to text verbatim. "
           "Output ONLY the transcription with no preamble, labels, or quotes.")

# Gemini accepts wav/mp3/aiff/aac/ogg/flac — NOT webm/opus, which is what browser
# MediaRecorder produces by default (and FormData often arrives as octet-stream). So we
# transcode whatever the browser sends to WAV via ffmpeg first. "Don't care what we record."
_GEMINI_AUDIO_MIMES = {"audio/wav", "audio/x-wav", "audio/mp3", "audio/mpeg",
                       "audio/aiff", "audio/aac", "audio/ogg", "audio/flac"}


def _to_wav(data: bytes) -> bytes | None:
    """Transcode arbitrary audio bytes (webm/opus, mp4, ogg, mp3, …) to mono 16kHz WAV.
    ffmpeg sniffs the input format, so the declared MIME doesn't matter. None if it fails."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as out:
        out_path = out.name
    try:
        proc = subprocess.run(
            ["ffmpeg", "-y", "-i", "pipe:0", "-ac", "1", "-ar", "16000", out_path],
            input=data, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
        if proc.returncode == 0:
            with open(out_path, "rb") as f:
                wav = f.read()
            return wav or None
    except Exception:
        pass
    finally:
        try:
            os.unlink(out_path)
        except OSError:
            pass
    return None

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
    # Normalize anything Gemini can't ingest (webm/opus, octet-stream) to WAV via ffmpeg.
    if mime not in _GEMINI_AUDIO_MIMES:
        wav = _to_wav(data)
        if wav is not None:
            data, mime = wav, "audio/wav"
        else:
            mime = "audio/mpeg"  # last-ditch guess if ffmpeg unavailable
    resp = _client_().models.generate_content(
        model=STT_MODEL,
        contents=[types.Part.from_bytes(data=data, mime_type=mime), _PROMPT],
    )
    return (resp.text or "").strip()


def detect_language(text: str) -> str:
    """Detect language of text. Returns ISO 639-1 code (e.g. 'en', 'es', 'fr')."""
    resp = _client_().models.generate_content(
        model=STT_MODEL,
        contents=[f"Detect the language of this text and respond ONLY with the ISO 639-1 code (e.g., 'en', 'es', 'fr', 'ja'). Text: {text}"],
    )
    return (resp.text or "en").strip().lower()


def translate_to_english(text: str, source_lang: str) -> str:
    """Translate text from source language to English."""
    if source_lang.lower() == "en":
        return text
    resp = _client_().models.generate_content(
        model=STT_MODEL,
        contents=[f"Translate this {source_lang} text to English. Output ONLY the translation with no preamble.\n\n{text}"],
    )
    return (resp.text or text).strip()


def translate_from_english(text: str, target_lang: str) -> str:
    """Translate a single English string INTO target_lang (ISO 639-1) for display. No-op for
    English or empty text."""
    if not text or (target_lang or "en").lower() == "en":
        return text
    resp = _client_().models.generate_content(
        model=STT_MODEL,
        contents=[f"Translate this English text to {target_lang}. Output ONLY the translation "
                  f"with no preamble or quotes.\n\n{text}"],
    )
    return (resp.text or text).strip()


def translate_map(items: dict, target_lang: str) -> dict:
    """Batch-translate all VALUES of `items` from English into target_lang in ONE Gemini call,
    preserving keys. Used to localize a whole agent turn's user-facing strings (reply, candidate
    titles/descriptions, reasoning, form.description) at once.

    Graceful by design: returns `items` unchanged for English, an empty map, or any response that
    is not valid same-keyed JSON — a translation hiccup must never break a turn."""
    if not items or (target_lang or "en").lower() == "en":
        return items
    payload = json.dumps(items, ensure_ascii=False)
    resp = _client_().models.generate_content(
        model=STT_MODEL,
        contents=[
            f"Translate the string VALUES of this JSON object from English into {target_lang}. "
            f"Keep the KEYS exactly the same. Output ONLY the resulting JSON object, no preamble, "
            f"no markdown fences.\n\n{payload}"],
    )
    raw = (resp.text or "").strip()
    # Tolerate ```json fences if the model adds them.
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw[raw.find("{"):raw.rfind("}") + 1] if "{" in raw else raw
    try:
        out = json.loads(raw)
    except (ValueError, TypeError):
        return items
    if not isinstance(out, dict):
        return items
    # Only trust keys we sent; fall back per-key to the original English on any miss.
    return {k: (out[k] if isinstance(out.get(k), str) else v) for k, v in items.items()}
