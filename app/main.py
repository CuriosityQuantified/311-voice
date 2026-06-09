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

from app import stt
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
    language: str = "en"  # ISO 639-1 of the resident's speech; drives outbound localization


class SubmitReq(BaseModel):
    ka: str
    description: str = ""
    address: str = ""
    borough: str = ""
    apartment: str | None = None
    locationDetails: str | None = None
    photo_b64: str | None = None
    language: str = "en"  # if non-English, description is translated to English for the NYC payload


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


def _localize_agent_out(out: dict, language: str) -> dict:
    """Translate the user-facing strings of an agent-turn response INTO `language` for display,
    in ONE batched Gemini call. Canonical/internal fields (picked_ka, candidate ka, form.ka and
    the other form fields, emergency, screen) stay English so the match/submit pipeline is
    unaffected. No-op for English. Mutates and returns `out`."""
    if (language or "en").lower() == "en":
        return out
    items: dict[str, str] = {}
    if out.get("reply"):
        items["reply"] = out["reply"]
    if out.get("reasoning"):
        items["reasoning"] = out["reasoning"]
    form = out.get("form") or {}
    if form.get("description"):
        items["form.description"] = form["description"]
    candidates = out.get("candidates") or []
    for i, c in enumerate(candidates):
        if c.get("title"):
            items[f"cand{i}.title"] = c["title"]
        if c.get("description"):
            items[f"cand{i}.description"] = c["description"]
    if not items:
        return out
    tr = stt.translate_map(items, language)
    if "reply" in tr:
        out["reply"] = tr["reply"]
    if "reasoning" in tr:
        out["reasoning"] = tr["reasoning"]
    if "form.description" in tr:
        form["description"] = tr["form.description"]
        out["form"] = form
    for i, c in enumerate(candidates):
        if f"cand{i}.title" in tr:
            c["title"] = tr[f"cand{i}.title"]
        if f"cand{i}.description" in tr:
            c["description"] = tr[f"cand{i}.description"]
    return out


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
    resp = {
        "transcript": out.get("transcript", ""),
        "candidates": out.get("candidates", []),
        "picked_ka": out.get("picked_ka", ""),
        "reasoning": out.get("reasoning", ""),
        "emergency": out.get("emergency", False),
        "form": out.get("form", {}),
        "submission": out.get("submission", {}),
        "screen": out.get("screen", "mic"),
        "reply": _last_ai_text(out.get("messages")),
        "language": req.language,
    }
    # Localize user-facing strings into the resident's language for display (no-op for English).
    return _localize_agent_out(resp, req.language)


@app.post("/api/submit")
def submit(req: SubmitReq):
    payload = req.model_dump()
    original_description = payload.get("description", "")
    # NYC must receive English: translate the (possibly localized) description to English for the
    # payload, then restore the original for display so the confirmation shows the user's language.
    if (req.language or "en").lower() != "en" and original_description:
        payload["description"] = stt.translate_to_english(original_description, req.language)
    result = mock_submit(payload, get_mapping())  # any KA files (mock); never raises now
    if (req.language or "en").lower() != "en" and original_description:
        result["payload"]["description"] = original_description
    return result


@app.post("/api/transcribe")
async def transcribe(audio: UploadFile = File(...)):
    from app.stt import transcribe_audio, detect_language, translate_to_english
    data = await audio.read()
    text = transcribe_audio(data, audio.content_type or "audio/mpeg")
    lang = detect_language(text)
    text_en = translate_to_english(text, lang) if lang != "en" else text
    return {
        "text": text_en,  # English version for agent processing
        "original_text": text,  # Original language for display
        "language": lang,  # ISO 639-1 code
    }


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
