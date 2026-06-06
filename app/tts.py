"""Text-to-Speech using Gemini 3.1 Flash TTS Preview.

Generates WAV audio from text using the Google GenAI Gemini TTS API.
Returns a WAV buffer that the frontend can play directly.
"""

from __future__ import annotations

import io
import os
import struct
import mimetypes
from typing import Iterator

from google import genai
from google.genai import types


def parse_audio_mime_type(mime_type: str) -> dict[str, int]:
    """Extract bits-per-sample and sample rate from audio MIME type string.
    Example: audio/L16;rate=24000 -> {"bits_per_sample": 16, "rate": 24000}
    """
    bits_per_sample = 16
    rate = 24000
    for param in mime_type.split(";"):
        param = param.strip()
        if param.lower().startswith("rate="):
            try:
                rate = int(param.split("=", 1)[1])
            except (ValueError, IndexError):
                pass
        elif param.startswith("audio/L"):
            try:
                bits_per_sample = int(param.split("L", 1)[1])
            except (ValueError, IndexError):
                pass
    return {"bits_per_sample": bits_per_sample, "rate": rate}


def _build_wav_header(data: bytes, mime_type: str) -> bytes:
    """Prepend a WAV header to raw PCM audio data."""
    params = parse_audio_mime_type(mime_type)
    bits_per_sample = params["bits_per_sample"]
    sample_rate = params["rate"]
    num_channels = 1
    data_size = len(data)
    bytes_per_sample = bits_per_sample // 8
    block_align = num_channels * bytes_per_sample
    byte_rate = sample_rate * block_align
    chunk_size = 36 + data_size
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        chunk_size,
        b"WAVE",
        b"fmt ",
        16,  # Subchunk1Size
        1,   # AudioFormat (PCM)
        num_channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b"data",
        data_size,
    )
    return header + data


def generate_tts(
    text: str,
    voice: str = "Aoede",
    model: str = "gemini-3.1-flash-tts-preview",
) -> bytes:
    """Generate a WAV audio file from text using Gemini TTS.
    Returns the full WAV bytes ready for browser playback.
    """
    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY or GEMINI_API_KEY must be set")

    client = genai.Client(api_key=api_key)

    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(
                    text=f"# Audio Profile\nA helpful and professional NYC 311 voice assistant.\n"
                    f"# Director's Note\nStyle: Empathetic. Pace: Natural. Accent: American.\n"
                    f"# Transcript\n{text}"
                ),
            ],
        ),
    ]

    config = types.GenerateContentConfig(
        temperature=1,
        response_modalities=["audio"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)
            )
        ),
    )

    audio_parts: list[bytes] = []
    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=config,
    ):
        if chunk.parts is None:
            continue
        if chunk.parts[0].inline_data and chunk.parts[0].inline_data.data:
            audio_parts.append(chunk.parts[0].inline_data.data)

    if not audio_parts:
        raise RuntimeError("No audio generated")

    raw_audio = b"".join(audio_parts)
    # The API returns raw PCM (mime_type typically audio/L16;rate=24000)
    # We wrap it in a WAV header for browser compatibility
    return _build_wav_header(raw_audio, "audio/L16;rate=24000")


def generate_tts_stream(
    text: str,
    voice: str = "Aoede",
    model: str = "gemini-3.1-flash-tts-preview",
) -> Iterator[bytes]:
    """Stream audio chunks for real-time playback.
    Yields chunks that the frontend can feed to an AudioContext.
    """
    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY or GEMINI_API_KEY must be set")

    client = genai.Client(api_key=api_key)

    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(
                    text=f"# Audio Profile\nA helpful and professional NYC 311 voice assistant.\n"
                    f"# Director's Note\nStyle: Empathetic. Pace: Natural. Accent: American.\n"
                    f"# Transcript\n{text}"
                ),
            ],
        ),
    ]

    config = types.GenerateContentConfig(
        temperature=1,
        response_modalities=["audio"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)
            )
        ),
    )

    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=config,
    ):
        if chunk.parts is None:
            continue
        if chunk.parts[0].inline_data and chunk.parts[0].inline_data.data:
            yield chunk.parts[0].inline_data.data
