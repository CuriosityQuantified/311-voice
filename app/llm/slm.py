"""Local SLM backend — the on-device bake-off contender.

Calls a llama.cpp `llama-server` OpenAI-compatible endpoint (Qwen3.5-2B). Model call is
injectable so select_service is unit-testable without a running server.
"""

from __future__ import annotations

import json
import os
import urllib.request
from typing import Callable

from app.llm.base import Candidate, LLMBackend, Selection
from app.llm.prompt import build_prompt, parse_selection

SLM_URL = os.environ.get("SLM_URL", "http://localhost:8080/v1/chat/completions")


class SLMBackend(LLMBackend):
    def __init__(self, generate: Callable[[str], str] | None = None, url: str = SLM_URL):
        self._generate = generate or self._default_generate
        self.url = url

    def _default_generate(self, prompt: str) -> str:
        body = json.dumps({
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "max_tokens": 256,
        }).encode()
        req = urllib.request.Request(
            self.url, data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as r:
            data = json.loads(r.read())
        return data["choices"][0]["message"]["content"]

    def select_service(self, complaint: str, candidates: list[Candidate]) -> Selection:
        prompt = build_prompt(complaint, candidates)
        return parse_selection(self._generate(prompt), candidates)
