"""LangChain ReAct agent for 311-voice.

Flow:
  1. Start: STT transcript + Pinecone top-5 candidates -> agent.
  2. Agent calls `recommend_service` to surface its pick; user confirms or picks another.
  3. Agent calls `update_form` to build/REVISE the draft form the user sees. The user can
     give feedback ("change the apartment to 5C") and the agent updates fields in place.
  4. After the user approves the on-screen form, agent calls `submit_service_request`,
     which commits the CURRENT draft (mock).

The draft lives in agent state (`form`) so it persists across turns (checkpointer) and the
CopilotKit UI can bind to it. LangSmith tracing is automatic via LANGSMITH_* env.
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
from app.submit import mock_submit

FORM_FIELDS = ("ka", "description", "address", "borough", "apartment", "locationDetails")
REQUIRED_TO_SUBMIT = ("ka", "address", "borough")

SYSTEM = (
    "You are an NYC 311 filing assistant. You receive a resident's complaint (transcribed "
    "from voice) and 5 candidate 311 service types ranked by relevance.\n"
    "1. Call recommend_service to recommend the SINGLE best service. picked_ka MUST be one "
    "of the candidate KA ids. Give one sentence of reasoning, then ask the user to confirm "
    "or choose another.\n"
    "2. As the user provides or revises details, call update_form with ONLY the fields to "
    "set or change. This keeps the on-screen draft form in sync. If the user gives feedback "
    "like 'change the apartment to 5C', call update_form again — do NOT resubmit.\n"
    "3. Only after the user approves the on-screen form, call submit_service_request to file "
    "it (it submits the current draft). Required: ka, address, borough. "
    "Boroughs: MANHATTAN, BROOKLYN, QUEENS, BRONX, STATEN ISLAND."
)


class FormState(AgentState):
    """Agent state extended with the draft form + final submission (UI binds to these)."""
    form: dict
    submission: dict


def format_candidates(candidates: list[Candidate]) -> str:
    lines = []
    for i, c in enumerate(candidates, 1):
        lines.append(f"{i}. {c.ka} — {c.title}: {c.description} "
                     f"(score={c.score:.3f}, type={c.classification})")
    return "\n".join(lines)


def make_start_message(transcript: str, candidates: list[Candidate]) -> str:
    return (f"Complaint (from voice): {transcript}\n\n"
            f"Candidate 311 services:\n{format_candidates(candidates)}\n\n"
            f"Recommend the single best service and explain why.")


def apply_form_updates(current: dict, updates: dict) -> dict:
    """Merge non-None updates into a copy of the draft form (pure)."""
    merged = dict(current)
    for k, v in updates.items():
        if v is not None:
            merged[k] = v
    return merged


def build_agent(mapping: dict,
                model="google_genai:gemini-3.1-flash-lite",
                checkpointer=None):
    """Create the ReAct agent. `model` may be a provider:model string or a chat model
    instance (the bake-off swaps Gemini <-> local SLM)."""

    @tool
    def recommend_service(picked_ka: str, reasoning: str) -> str:
        """Recommend the single best 311 service. picked_ka MUST be one of the candidate
        KA ids shown to you. reasoning is one sentence on why it fits the complaint."""
        return f"RECOMMENDATION: {picked_ka} — {reasoning}"

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
        """Update the draft 311 form the user sees BEFORE submission. Pass ONLY the fields
        to set or change (partial update). Use this whenever the user provides or revises
        information. This does NOT submit."""
        updates = {"ka": ka, "description": description, "address": address,
                   "borough": borough, "apartment": apartment, "locationDetails": locationDetails}
        new_form = apply_form_updates(state.get("form") or {}, updates)
        return Command(update={
            "form": new_form,
            "messages": [ToolMessage(f"Draft form updated: {json.dumps(new_form)}",
                                     tool_call_id=tool_call_id)],
        })

    @tool
    def submit_service_request(
        tool_call_id: Annotated[str, InjectedToolCallId],
        state: Annotated[dict, InjectedState],
    ) -> Command:
        """Submit the CURRENT on-screen draft form to NYC 311 (MOCK). Call only after the
        user confirms the form is correct. Requires ka, address, borough already set via
        update_form."""
        form = dict(state.get("form") or {})
        missing = [f for f in REQUIRED_TO_SUBMIT if not form.get(f)]
        if missing:
            return Command(update={"messages": [ToolMessage(
                f"Cannot submit yet — missing required fields {missing}. "
                f"Use update_form first.", tool_call_id=tool_call_id)]})
        result = mock_submit(form, mapping)
        return Command(update={
            "submission": result,
            "messages": [ToolMessage(json.dumps(result), tool_call_id=tool_call_id)],
        })

    if checkpointer is None:
        from langgraph.checkpoint.memory import InMemorySaver
        checkpointer = InMemorySaver()

    return create_agent(
        model,
        tools=[recommend_service, update_form, submit_service_request],
        system_prompt=SYSTEM,
        state_schema=FormState,
        checkpointer=checkpointer,
    )
