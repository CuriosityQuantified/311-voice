"""Speech-to-text via Gemini audio (multimodal). Used for the 200-file accuracy test
and the live demo (browser-recorded audio). Single thin API call — no local model."""

from __future__ import annotations

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
