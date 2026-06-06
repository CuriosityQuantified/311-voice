"""FastAPI app implementing the frozen 311-voice API contract (PLAN §6).

  GET  /api/health     -> {ok, llm_backend}
  POST /api/match      {text} -> {candidates, picked_ka, reasoning, emergency}
  POST /api/agent      {text, thread_id} -> full agent shared state  [tool-calling agent over REST]
  POST /api/submit     {ka, description, address, borough, apartment?, ...} -> {sr_number, payload, status}
  POST /api/transcribe (multipart audio) -> {text}    [Gemini STT]

Heavy deps (Pinecone retriever, LLM backend) are lazily built so import/startup is cheap
and tests can swap them.
"""

from __future__ import annotations

import json
import os
import io

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
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
_agent = None


def get_agent():
    """The full tool-calling agent (search/recommend/update_form/submit + middleware +
    skills), built once. Needs LLM creds, so only call when a key is present."""
    global _agent
    if _agent is None:
        from app.agent import build_agent
        _agent = build_agent(get_mapping())
    return _agent


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


class AgentReq(BaseModel):
    text: str
    thread_id: str


class SubmitReq(BaseModel):
    ka: str
    description: str = ""
    address: str = ""
    borough: str = ""
    apartment: str | None = None
    locationDetails: str | None = None
    photo_b64: str | None = None


class TTSReq(BaseModel):
    text: str
    voice: str = "Aoede"


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


def _text_of(content) -> str:
    """Flatten a message's content to plain text. Gemini (via LangChain) returns AI content
    as a LIST of blocks like [{'type':'text','text':...}], not a bare string — extract those."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for b in content:
            if isinstance(b, str):
                parts.append(b)
            elif isinstance(b, dict) and b.get("type") == "text" and b.get("text"):
                parts.append(b["text"])
        return " ".join(parts).strip()
    return ""


def _last_ai_text(messages) -> str:
    """The agent's most recent natural-language reply (skip tool-call-only turns). This is
    what the frontend reads aloud via /api/tts, so it must be the spoken text."""
    for m in reversed(messages or []):
        if getattr(m, "type", None) == "ai":
            txt = _text_of(getattr(m, "content", None))
            if txt.strip():
                return txt
    return ""


@app.post("/api/agent")
def agent_turn(req: AgentReq):
    """Run ONE turn of the tool-calling agent and return its shared state. The agent's tool
    calls (recommend_service / update_form / submit_service_request) drive `screen` + `form`
    + `candidates`, so the frontend just re-renders from the returned state — this is the
    REST-transport equivalent of CopilotKit shared state. Multi-turn via `thread_id`
    (the agent's checkpointer persists state across calls)."""
    if not req.text.strip():
        raise HTTPException(status_code=422, detail="text is required")
    from app.agent import make_start_message
    agent = get_agent()
    cfg = {"configurable": {"thread_id": req.thread_id}}
    prior = agent.get_state(cfg).values  # {} on a brand-new thread
    content = req.text if prior.get("messages") else make_start_message(req.text)
    out = agent.invoke({"messages": [{"role": "user", "content": content}]}, cfg)
    return {
        "transcript": out.get("transcript", ""),
        "candidates": out.get("candidates", []),
        "picked_ka": out.get("picked_ka", ""),
        "reasoning": out.get("reasoning", ""),
        "emergency": out.get("emergency", False),
        "form": out.get("form", {}),
        "submission": out.get("submission", {}),
        "screen": out.get("screen", "mic"),
        "reply": _last_ai_text(out.get("messages")),
    }


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


@app.post("/api/tts")
async def tts(req: TTSReq):
    """Generate TTS audio from the agent's reply text using Gemini 3.1 Flash TTS.
    Returns a WAV file that the browser can play directly.
    """
    if not req.text.strip():
        raise HTTPException(status_code=422, detail="text is required")
    from app.tts import generate_tts
    try:
        wav_bytes = generate_tts(req.text, voice=req.voice)
        return StreamingResponse(
            io.BytesIO(wav_bytes),
            media_type="audio/wav",
            headers={"Content-Disposition": "inline; filename=reply.wav"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS generation failed: {str(e)}")


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
