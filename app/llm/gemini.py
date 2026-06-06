"""Gemini backend — the cloud LLM contender (and safe demo default).

Model call is injectable (`generate`) so select_service is unit-testable without network;
the default calls gemini-3.1-flash-lite via google-genai.
"""

from __future__ import annotations

import os
from typing import Callable

from app.llm.base import Candidate, LLMBackend, Selection
from app.llm.prompt import build_prompt, gemini_selection_schema, parse_selection

MODEL = "gemini-3.1-flash-lite"


class GeminiBackend(LLMBackend):
    def __init__(self, generate: Callable[[str, list[str]], str] | None = None,
                 model: str = MODEL):
        self._generate = generate or self._default_generate
        self.model = model
        self._client = None

    def _default_generate(self, prompt: str, kas: list[str]) -> str:
        from google import genai
        from google.genai import types
        if self._client is None:
            key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
            self._client = genai.Client(api_key=key)
        # Structured output: response_schema with picked_ka enum'd to the candidate ids.
        cfg = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=gemini_selection_schema(kas),
            temperature=0,
        )
        resp = self._client.models.generate_content(
            model=self.model, contents=prompt, config=cfg)
        return resp.text or ""

    def select_service(self, complaint: str, candidates: list[Candidate]) -> Selection:
        prompt = build_prompt(complaint, candidates)
        raw = self._generate(prompt, [c.ka for c in candidates])
        return parse_selection(raw, candidates)
