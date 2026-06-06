"""LangChain ReAct agent for 311-voice.

Flow:
  1. Start: STT transcript + Pinecone top-5 candidates -> agent.
  2. Agent reasons (ReAct) and calls `recommend_service` to surface its pick.
  3. User selects an option -> message back to the agent (same thread via checkpointer).
  4. Agent calls `submit_service_request` (structured form) -> mock submission.

LangSmith tracing is automatic when LANGSMITH_* env is set; callers tag runs for the
LangSmith CLI (`langsmith trace list`, `langsmith experiment ...`).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from langchain.agents import create_agent
from langchain_core.tools import tool

from app.llm.base import Candidate
from app.submit import mock_submit

SYSTEM = (
    "You are an NYC 311 filing assistant. You receive a resident's complaint (transcribed "
    "from voice) and 5 candidate 311 service types ranked by relevance.\n"
    "1. Call recommend_service to recommend the SINGLE best service. picked_ka MUST be one "
    "of the candidate KA ids. Give one sentence of reasoning.\n"
    "2. Ask the user to confirm that service or pick a different one.\n"
    "3. Once the user confirms and provides their address and details, call "
    "submit_service_request to file it. Ask for any missing required field (address, "
    "borough) before submitting. Boroughs: MANHATTAN, BROOKLYN, QUEENS, BRONX, STATEN ISLAND."
)


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


class SubmissionForm(BaseModel):
    """Structured NYC 311 service-request form the agent fills in (structured output)."""
    ka: str = Field(description="Chosen service KA id, e.g. KA-01036")
    description: str = Field(description="The resident's complaint details")
    address: str = Field(description="Street address of the problem")
    borough: str = Field(description="MANHATTAN, BROOKLYN, QUEENS, BRONX, or STATEN ISLAND")
    apartment: str = Field(default="", description="Apartment/unit number if applicable")
    locationDetails: str = Field(default="", description="Specific spot within the address")


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

    @tool(args_schema=SubmissionForm)
    def submit_service_request(ka, description, address, borough,
                               apartment="", locationDetails="") -> dict:
        """File the NYC 311 service request (MOCK). Call only after the user confirms the
        service and provides their address/details."""
        return mock_submit({
            "ka": ka, "description": description, "address": address,
            "borough": borough, "apartment": apartment, "locationDetails": locationDetails,
        }, mapping)

    if checkpointer is None:
        from langgraph.checkpoint.memory import InMemorySaver
        checkpointer = InMemorySaver()

    return create_agent(
        model,
        tools=[recommend_service, submit_service_request],
        system_prompt=SYSTEM,
        checkpointer=checkpointer,
    )
