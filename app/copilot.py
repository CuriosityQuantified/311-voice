"""Expose the LangChain agent over AG-UI so the CopilotKit `useAgent` hook can drive it.

Frontend points CopilotKit `runtimeUrl` at the mounted path (default /api/copilotkit) and
binds its A2UI fixed-schema form to the agent's shared `form` state (see app/agent.py).
"""

from __future__ import annotations

import json
import os

from app.agent import build_agent

AGENT_NAME = "threeoneone"
_MAPPING_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "311-mapping.json")


def mount_copilotkit(app, path: str = "/api/copilotkit", mapping: dict | None = None,
                     model: str = "google_genai:gemini-3.1-flash-lite") -> str:
    """Mount the agent as an AG-UI FastAPI endpoint. Returns the agent name the frontend
    references in useAgent({ name })."""
    from ag_ui_langgraph import LangGraphAgent, add_langgraph_fastapi_endpoint

    if mapping is None:
        with open(_MAPPING_PATH) as f:
            mapping = json.load(f)

    graph = build_agent(mapping, model=model)
    add_langgraph_fastapi_endpoint(
        app,
        LangGraphAgent(name=AGENT_NAME, graph=graph,
                       description="NYC 311 voice complaint filing agent"),
        path=path,
    )
    return AGENT_NAME
