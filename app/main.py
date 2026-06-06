from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
import json

from app.ingest import query_311_content
from app.agent import select_best_match, fill_service_request
from app.mapping import get_mapping

app = FastAPI(title="311-voice", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Models ──────────────────────────────────────────────────────

class VoiceInput(BaseModel):
    transcript: str
    location: Optional[str] = None

class MatchResult(BaseModel):
    id: str
    title: str
    description: str
    classification: str
    score: float
    categories: List[str]

class MatchResponse(BaseModel):
    query: str
    matches: List[MatchResult]
    selected: Optional[MatchResult] = None
    form: Optional[Dict[str, Any]] = None
    emergency: bool = False

class SubmitRequest(BaseModel):
    match_id: str
    form: Dict[str, Any]

class SubmitResponse(BaseModel):
    success: bool
    service_request_id: Optional[str] = None
    message: str
    mock: bool = True

# ── Health ──────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0"}

# ── Match ──────────────────────────────────────────────────────

@app.post("/api/match", response_model=MatchResponse)
def match(input: VoiceInput):
    """
    Given a transcript, return top-5 Pinecone matches + agent selection + form.
    """
    if not input.transcript or len(input.transcript.strip()) < 3:
        raise HTTPException(status_code=400, detail="Transcript too short")

    # 1. Query Pinecone (or mock if no key)
    try:
        matches = query_311_content(input.transcript, top_k=5)
    except Exception as e:
        # Fallback: return mock matches for dev
        matches = []

    # 2. Check for emergency
    emergency = any(m["classification"] == "emergency" for m in matches)

    # 3. Agent selects best match
    selected = None
    form = None
    if matches:
        selected = select_best_match(input.transcript, matches)
        if selected:
            form = fill_service_request(selected, input.location)

    return MatchResponse(
        query=input.transcript,
        matches=[MatchResult(**m) for m in matches],
        selected=MatchResult(**selected) if selected else None,
        form=form,
        emergency=emergency,
    )

# ── Voice (STT placeholder) ──────────────────────────────────────────────

@app.post("/api/voice")
def voice(input: VoiceInput):
    """
    Same as /api/match but named for voice flow.
    """
    return match(input)

# ── Submit (mock) ─────────────────────────────────────────────────────

@app.post("/api/submit", response_model=SubmitResponse)
def submit(req: SubmitRequest):
    """
    Mock submit to NYC 311 CreateServiceRequest.
    Never sends a real request.
    """
    mapping = get_mapping(req.match_id)
    if not mapping:
        return SubmitResponse(
            success=False,
            message=f"No mapping found for {req.match_id}",
            mock=True,
        )

    # In a real implementation, we would POST to:
    # https://api.nyc.gov/create-sr/api/CreateServiceRequest
    # with the Ocp-Apim-Subscription-Key header and the form data.
    # For the hackathon, we mock the response.

    mock_id = f"MOCK-{req.match_id}-{hash(json.dumps(req.form, sort_keys=True)) % 100000:05d}"
    return SubmitResponse(
        success=True,
        service_request_id=mock_id,
        message="Service request created (mock).",
        mock=True,
    )
