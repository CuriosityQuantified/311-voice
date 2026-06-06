"""FastAPI app implementing the frozen 311-voice API contract (PLAN §6).

  GET  /api/health     -> {ok, llm_backend}
  POST /api/match      {text} -> {candidates, picked_ka, reasoning, emergency}
  POST /api/submit     {ka, description, address, borough, apartment?, ...} -> {sr_number, payload, status}
  POST /api/transcribe (multipart audio) -> {text}    [Gemini STT]

Heavy deps (Pinecone retriever, LLM backend) are lazily built so import/startup is cheap
and tests can swap them.
"""

from __future__ import annotations

import json
import os

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.match import run_match
from app.submit import mock_submit

LLM_BACKEND = os.environ.get("LLM_BACKEND", "gemini")
_MAPPING_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "311-mapping.json")

app = FastAPI(title="311-voice", version="1.0.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# ── lazily-built singletons (overridable in tests) ──────────────
_retriever = None
_backend = None
_mapping = None


def get_retriever():
    global _retriever
    if _retriever is None:
        from app.retrieval import make_retriever
        _retriever = make_retriever()
    return _retriever


def get_backend():
    global _backend
    if _backend is None:
        if LLM_BACKEND == "fake":
            from app.llm.fake import FakeBackend
            _backend = FakeBackend()
        elif LLM_BACKEND == "slm":
            from app.llm.slm import SLMBackend
            _backend = SLMBackend()
        else:
            from app.llm.gemini import GeminiBackend
            _backend = GeminiBackend()
    return _backend


def get_mapping():
    global _mapping
    if _mapping is None:
        with open(_MAPPING_PATH) as f:
            _mapping = json.load(f)
    return _mapping


# ── request models ──────────────────────────────────────────────
class MatchReq(BaseModel):
    text: str


class SubmitReq(BaseModel):
    ka: str
    description: str = ""
    address: str = ""
    borough: str = ""
    apartment: str | None = None
    locationDetails: str | None = None
    photo_b64: str | None = None


# ── routes ──────────────────────────────────────────────────────
@app.get("/api/health")
def health():
    return {"ok": True, "llm_backend": LLM_BACKEND}


@app.post("/api/match")
def match(req: MatchReq):
    if not req.text.strip():
        raise HTTPException(status_code=422, detail="text is required")
    result = run_match(req.text, get_retriever(), get_backend())
    picked = next((c for c in result["candidates"] if c["ka"] == result["picked_ka"]), None)
    result["emergency"] = bool(picked and picked.get("classification") == "emergency")
    # Pre-fill fields for the frontend form. The complaint IS the description; address/
    # apartment/locationDetails come from GPS + the form (rarely reliable from short speech).
    result["extracted_fields"] = {
        "description": req.text,
        "address": "",
        "apartment": "",
        "locationDetails": "",
    }
    return result


@app.post("/api/submit")
def submit(req: SubmitReq):
    try:
        return mock_submit(req.model_dump(), get_mapping())
    except KeyError:
        raise HTTPException(status_code=422,
                            detail=f"No CreateServiceRequest mapping for KA '{req.ka}'")


@app.post("/api/transcribe")
async def transcribe(audio: UploadFile = File(...)):
    from app.stt import transcribe_audio
    data = await audio.read()
    text = transcribe_audio(data, audio.content_type or "audio/mpeg")
    return {"text": text}


# ── CopilotKit / AG-UI agent endpoint (for useAgent) ────────────
# Building the agent needs LLM creds, so only mount when a key is present (keeps keyless
# test imports fast and avoids slow credential-discovery failures).
if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
    try:
        from app.copilot import mount_copilotkit
        AGENT_NAME = mount_copilotkit(app)
    except Exception as _e:  # pragma: no cover
        import logging
        logging.getLogger("uvicorn").warning(f"CopilotKit agent endpoint not mounted: {_e}")
