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
from langchain.agents.middleware import (
    AgentMiddleware,
    ClearToolUsesEdit,
    ContextEditingMiddleware,
    ModelCallLimitMiddleware,
    ModelRetryMiddleware,
    PIIMiddleware,
    SummarizationMiddleware,
    TodoListMiddleware,
    ToolCallLimitMiddleware,
    ToolRetryMiddleware,
)
from langchain_core.messages import ToolMessage
from langchain_core.tools import InjectedToolCallId, tool
from langgraph.prebuilt import InjectedState
from langgraph.types import Command

from app.llm.base import Candidate
from app.match import parse_hits
from app.skills import list_skills, load_skill_content
from app.submit import mock_submit

FORM_FIELDS = ("ka", "description", "address", "borough", "apartment", "locationDetails")
REQUIRED_TO_SUBMIT = ("ka", "address", "borough")

SYSTEM = (
    "You are an NYC 311 filing assistant driving a voice app.\n"
    "1. As soon as you receive the resident's complaint, call search_services with it to "
    "retrieve candidate 311 services.\n"
    "2. Then call recommend_service with the SINGLE best service (picked_ka MUST be one of "
    "the returned candidate KA ids) and one sentence of reasoning. Ask the user to confirm or "
    "choose another, and to click Continue when ready. Then STOP — do NOT call update_form "
    "yet. The form is not open until the user clicks Continue; trying to fill it on the "
    "results screen is rejected.\n"
    "3. Once the user clicks Continue (the form opens), call update_form to fill it:\n"
    "   - description: write a CLEAR, well-formatted summary of the complaint in your own "
    "words — concise and grammatical, NOT a verbatim copy of what the user said.\n"
    "   - Only set address, borough, apartment, or locationDetails if the user ACTUALLY "
    "provided them. If a field (e.g. borough) was not given, LEAVE IT BLANK — never guess or "
    "invent an address or borough.\n"
    "   - On later feedback like 'change the apartment to 5C', call update_form again with "
    "just that field. Do NOT resubmit.\n"
    "4. Only after the user approves the on-screen form, call submit_service_request to file "
    "it (commits the current draft). Required: ka, address, borough. "
    "Boroughs: MANHATTAN, BROOKLYN, QUEENS, BRONX, STATEN ISLAND.\n"
    "EVERY service is fileable. If the recommended service is an emergency (911) item, tell the "
    "user to call 911 immediately — but you may STILL file the report as normal.\n\n"
    "You also have SKILLS — on-demand notes (examples, gotchas, troubleshooting) for tricky "
    "situations. Call load_skill(skill_name) to read one BEFORE acting when you hit it:\n"
    f"{list_skills()}\n"
    "Use them e.g. when picking among close candidates (service_selection), parsing an "
    "address (address_and_borough), a complaint sounds dangerous (emergency), a submit fails "
    "(submission_troubleshooting), or the complaint is vague/multi-issue (ambiguous_or_multiple)."
    "\n\n"
    "VOICE REPLY STYLE — your text replies are READ ALOUD by text-to-speech, and the screen "
    "already shows the service + form details. So every reply you write must be:\n"
    "- Short: one or two sentences, ideally under ~30 words.\n"
    "- Conversational and natural, the way a helpful person would speak.\n"
    "- Plain spoken text ONLY: no markdown, no bullet points, no asterisks, no headings, no "
    "KA codes, no field labels like 'Address:'.\n"
    "- Do NOT read back the whole form or list every field — the user can see it. Confirm just "
    "the key thing you changed and ask ONE short follow-up question.\n"
    "Example — instead of a bulleted recap, say: \"Got it, I've set the borough to Brooklyn. "
    "Want me to submit this, or change anything else?\""
)


@tool
def load_skill(skill_name: str) -> str:
    """Load an on-demand skill note (examples, gotchas, troubleshooting) for a situation.
    Available skills: service_selection, address_and_borough, emergency, form_fields,
    submission_troubleshooting, ambiguous_or_multiple. Returns the note's text."""
    return load_skill_content(skill_name)


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


_CONTINUE_PHRASES = ("continue", "go to the form", "proceed to the form")


def _message_text(msg) -> str:
    """Best-effort plain-text extraction from a langchain message object (or a dict).
    Content may be a str or a list of content blocks ({"type": "text", "text": ...})."""
    content = getattr(msg, "content", None)
    if content is None and isinstance(msg, dict):
        content = msg.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                parts.append(block.get("text") or block.get("content") or "")
        return " ".join(p for p in parts if p)
    return ""


def _last_human_text(messages: list) -> str:
    """Return the text of the most recent human message, or '' if there is none."""
    for msg in reversed(messages or []):
        msg_type = getattr(msg, "type", None)
        if msg_type is None and isinstance(msg, dict):
            msg_type = msg.get("type") or msg.get("role")
        if msg_type == "human":
            return _message_text(msg)
    return ""


def seed_form_on_continue(state: dict) -> dict | None:
    """Deterministically seed the initial form draft and flip to the form screen when the
    user clicks Continue on the results screen.

    Fires ONLY when ALL hold:
      * state screen == "results"
      * state has a non-empty picked_ka
      * the most recent human message signals continue intent

    Returns the state-update dict to merge, or None if it should not fire. Idempotent: once
    screen becomes "form" the screen=="results" guard prevents it from firing again."""
    if (state.get("screen") or "") != "results":
        return None
    picked_ka = state.get("picked_ka") or ""
    if not picked_ka:
        return None
    text = _last_human_text(state.get("messages")).lower()
    if not any(phrase in text for phrase in _CONTINUE_PHRASES):
        return None
    current_form = state.get("form") or {}
    seeded = apply_form_updates(current_form, {
        "ka": picked_ka,
        "description": current_form.get("description") or state.get("transcript", ""),
    })
    return {"form": seeded, "screen": "form"}


def form_editing_allowed(state: dict) -> bool:
    """The form may only be edited once it is OPEN — i.e. the user has clicked Continue and
    the screen is the form (or the confirmation). Before that (mic/results) update_form is
    blocked, so the agent can't skip the results review or fill the form prematurely."""
    return (state.get("screen") or "") in ("form", "confirm")


class ContinueToFormMiddleware(AgentMiddleware):
    """Guarantees the initial form-fill + screen transition when the user clicks Continue.

    Runs BEFORE the model each turn. When the guard in `seed_form_on_continue` passes, it
    merges the seeded form and screen="form" into agent state so the transition does not
    depend on the LLM choosing to call update_form."""

    state_schema = FormState

    def before_model(self, state, runtime) -> dict | None:
        return seed_form_on_continue(state)


def build_middleware(summary_model="google_genai:gemini-3.1-flash-lite") -> list:
    """The agent's built-in middleware harness (LangChain v1). Order matters: PII guards
    input first; summarization/context-editing keep the window small; the limits and retries
    wrap the model/tool calls for a resilient single-shot demo.

    Notes for langchain==1.2.7:
      * PII built-in detectors (email/credit_card/ip) never match street addresses, so the
        form's address data is preserved; apply_to_output needs >=1.3.2, so input-only.
      * Summarization uses tokens/messages triggers (Gemini lacks a token profile here, so
        a `fraction` trigger would not resolve).
    """
    return [
        ContinueToFormMiddleware(),
        PIIMiddleware("email", strategy="redact", apply_to_input=True),
        PIIMiddleware("credit_card", strategy="mask", apply_to_input=True),
        PIIMiddleware("ip", strategy="redact", apply_to_input=True),
        TodoListMiddleware(),
        SummarizationMiddleware(model=summary_model, trigger=("tokens", 3000),
                                keep=("messages", 12)),
        ContextEditingMiddleware(
            edits=[ClearToolUsesEdit(trigger=20000, keep=3, clear_tool_inputs=False)]),
        ModelCallLimitMiddleware(thread_limit=25, run_limit=12, exit_behavior="end"),
        ToolCallLimitMiddleware(thread_limit=30, run_limit=15),
        ToolCallLimitMiddleware(tool_name="search_services", run_limit=3),
        ModelRetryMiddleware(max_retries=2, retry_on=(Exception,)),
        ToolRetryMiddleware(max_retries=2, tools=["search_services"], retry_on=(Exception,)),
    ]


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
        """Update the draft 311 form the user sees. Only usable AFTER the user clicks Continue
        (the form screen is open) — calling it earlier is rejected. Pass ONLY the fields to set
        or change (partial); leave a field out (blank) if the user has not provided it. Does NOT
        submit."""
        # Guard: do not let the agent fill the form before the user clicks Continue. This keeps
        # the results-review step intact and prevents skipping straight to the form.
        if not form_editing_allowed(state):
            return Command(update={"messages": [ToolMessage(
                "The form isn't open yet — do NOT fill it. Ask the user to review the "
                "recommendation and click Continue first.", tool_call_id=tool_call_id)]})
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

    summary_model = model if isinstance(model, str) else "google_genai:gemini-3.1-flash-lite"
    return create_agent(
        model,
        tools=[search_services, recommend_service, update_form, submit_service_request,
               load_skill],
        system_prompt=SYSTEM,
        state_schema=FormState,
        middleware=build_middleware(summary_model=summary_model),
        checkpointer=checkpointer,
    )
