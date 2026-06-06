"""LangChain ReAct agent for 311-voice — shared-state pattern (CopilotKit useAgent).

The agent owns ALL UI state; the frontend binds to it via useAgent and renders the screen
named by `screen`. Flow (each tool updates state):

  search_services(complaint)      -> candidates, transcript, screen="results"
  recommend_service(ka, reasoning)-> picked_ka, reasoning, emergency, form.ka
  update_form(...partial...)      -> form (the live draft), screen="form"
  submit_service_request()        -> submission, screen="confirm"

State (bind the UI to these):
  transcript str | candidates list | picked_ka str | reasoning str | emergency bool
  form {ka,description,address,borough,apartment,locationDetails} | submission {...}
  screen "mic"|"results"|"form"|"confirm"

LangSmith tracing is automatic via LANGSMITH_* env.
"""

from __future__ import annotations

import json
from typing import Annotated, Optional

from langchain.agents import AgentState, create_agent
from langchain_core.messages import ToolMessage
from langchain_core.tools import InjectedToolCallId, tool
from langgraph.prebuilt import InjectedState
from langgraph.types import Command

from app.llm.base import Candidate
from app.match import parse_hits
from app.submit import mock_submit

FORM_FIELDS = ("ka", "description", "address", "borough", "apartment", "locationDetails")
REQUIRED_TO_SUBMIT = ("ka", "address", "borough")

SYSTEM = (
    "You are an NYC 311 filing assistant driving a voice app.\n"
    "1. As soon as you receive the resident's complaint, call search_services with it to "
    "retrieve candidate 311 services.\n"
    "2. Then call recommend_service with the SINGLE best service (picked_ka MUST be one of "
    "the returned candidate KA ids) and one sentence of reasoning. Ask the user to confirm "
    "or choose another.\n"
    "3. As the user provides or revises details, call update_form with ONLY the fields to "
    "set or change (partial). On feedback like 'change the apartment to 5C', call update_form "
    "again — do NOT resubmit.\n"
    "4. Only after the user approves the on-screen form, call submit_service_request to file "
    "it (commits the current draft). Required: ka, address, borough. "
    "Boroughs: MANHATTAN, BROOKLYN, QUEENS, BRONX, STATEN ISLAND.\n"
    "If the recommended service is an emergency (911) item, tell the user to call 911 and do "
    "NOT submit."
)


class FormState(AgentState):
    """Agent state; the CopilotKit UI binds to every field here."""
    transcript: str
    candidates: list
    picked_ka: str
    reasoning: str
    emergency: bool
    form: dict
    submission: dict
    screen: str


def format_candidates(candidates: list[Candidate]) -> str:
    lines = []
    for i, c in enumerate(candidates, 1):
        lines.append(f"{i}. {c.ka} — {c.title}: {c.description} "
                     f"(score={c.score:.3f}, type={c.classification})")
    return "\n".join(lines)


def make_start_message(transcript: str) -> str:
    return (f"Complaint (from voice): {transcript}\n\n"
            f"Find the matching NYC 311 service and recommend the best one.")


def apply_form_updates(current: dict, updates: dict) -> dict:
    """Merge non-None updates into a copy of the draft form (pure)."""
    merged = dict(current)
    for k, v in updates.items():
        if v is not None:
            merged[k] = v
    return merged


def is_emergency(candidates: list[Candidate], picked_ka: str) -> bool:
    """True only if the picked candidate is classified as an emergency (911) item."""
    for c in candidates:
        if c.ka == picked_ka:
            return c.classification == "emergency"
    return False


def _candidate_dicts(candidates: list[Candidate]) -> list[dict]:
    return [c.__dict__ for c in candidates]


def build_agent(mapping: dict,
                model="google_genai:gemini-3.1-flash-lite",
                retriever=None,
                checkpointer=None):
    """Create the ReAct agent. `model` may be a provider:model string or a chat model
    instance (the bake-off swaps Gemini <-> SLM). `retriever` is injected for tests; in
    production it is built lazily from Pinecone."""

    def _retrieve(text):
        nonlocal retriever
        if retriever is None:
            from app.retrieval import make_retriever
            retriever = make_retriever()
        return retriever(text)

    @tool
    def search_services(
        complaint: str,
        tool_call_id: Annotated[str, InjectedToolCallId],
    ) -> Command:
        """Retrieve the top NYC 311 candidate services for the complaint. Call this first."""
        candidates = parse_hits(_retrieve(complaint))
        return Command(update={
            "transcript": complaint,
            "candidates": _candidate_dicts(candidates),
            "screen": "results",
            "messages": [ToolMessage(
                f"Candidates:\n{format_candidates(candidates)}", tool_call_id=tool_call_id)],
        })

    @tool
    def recommend_service(
        picked_ka: str,
        reasoning: str,
        tool_call_id: Annotated[str, InjectedToolCallId],
        state: Annotated[dict, InjectedState],
    ) -> Command:
        """Recommend the single best 311 service. picked_ka MUST be one of the candidate KA
        ids from search_services. reasoning is one sentence."""
        cands = [Candidate(**c) for c in (state.get("candidates") or [])]
        emer = is_emergency(cands, picked_ka)
        form = apply_form_updates(state.get("form") or {}, {"ka": picked_ka})
        return Command(update={
            "picked_ka": picked_ka,
            "reasoning": reasoning,
            "emergency": emer,
            "form": form,
            "screen": "results",
            "messages": [ToolMessage(f"RECOMMENDATION: {picked_ka} — {reasoning}"
                                     + (" [EMERGENCY: tell user to call 911]" if emer else ""),
                                     tool_call_id=tool_call_id)],
        })

    @tool
    def update_form(
        tool_call_id: Annotated[str, InjectedToolCallId],
        state: Annotated[dict, InjectedState],
        ka: Optional[str] = None,
        description: Optional[str] = None,
        address: Optional[str] = None,
        borough: Optional[str] = None,
        apartment: Optional[str] = None,
        locationDetails: Optional[str] = None,
    ) -> Command:
        """Update the draft 311 form the user sees BEFORE submission. Pass ONLY the fields to
        set or change (partial). Use whenever the user provides or revises info. Does NOT submit."""
        updates = {"ka": ka, "description": description, "address": address,
                   "borough": borough, "apartment": apartment, "locationDetails": locationDetails}
        new_form = apply_form_updates(state.get("form") or {}, updates)
        return Command(update={
            "form": new_form,
            "screen": "form",
            "messages": [ToolMessage(f"Draft form updated: {json.dumps(new_form)}",
                                     tool_call_id=tool_call_id)],
        })

    @tool
    def submit_service_request(
        tool_call_id: Annotated[str, InjectedToolCallId],
        state: Annotated[dict, InjectedState],
    ) -> Command:
        """Submit the CURRENT on-screen draft form to NYC 311 (MOCK). Call only after the
        user confirms the form. Requires ka, address, borough set via update_form."""
        form = dict(state.get("form") or {})
        missing = [f for f in REQUIRED_TO_SUBMIT if not form.get(f)]
        if missing:
            return Command(update={"messages": [ToolMessage(
                f"Cannot submit yet — missing required fields {missing}. Use update_form first.",
                tool_call_id=tool_call_id)]})
        result = mock_submit(form, mapping)
        return Command(update={
            "submission": result,
            "screen": "confirm",
            "messages": [ToolMessage(json.dumps(result), tool_call_id=tool_call_id)],
        })

    if checkpointer is None:
        from langgraph.checkpoint.memory import InMemorySaver
        checkpointer = InMemorySaver()

    return create_agent(
        model,
        tools=[search_services, recommend_service, update_form, submit_service_request],
        system_prompt=SYSTEM,
        state_schema=FormState,
        checkpointer=checkpointer,
    )
