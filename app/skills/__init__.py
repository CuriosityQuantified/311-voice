"""On-demand agent skills (LangChain skills pattern: progressive disclosure).

Each skill is a markdown knowledge package (examples, gotchas, troubleshooting) for a
SITUATION the agent runs into while filing a 311 request. The agent loads one only when it
needs it, via the `load_skill` tool in app/agent.py — keeping the base prompt small.

The 4 state tools (search/recommend/update_form/submit) are unchanged; skills only SUPPORT
them. See https://docs.langchain.com/oss/python/langchain/multi-agent/skills
"""

from __future__ import annotations

import os

_DIR = os.path.dirname(__file__)

# name -> one-line description (the catalog the agent sees in its system prompt)
SKILLS: dict[str, str] = {
    "service_selection": "Choosing the best 311 service among the reranked candidates.",
    "address_and_borough": "Parsing NYC addresses, boroughs, apartments, and cross-streets.",
    "emergency": "Handling 911 / emergency items (do NOT submit; tell the user to call 911).",
    "form_fields": "What each draft-form field means and how partial update_form merges work.",
    "submission_troubleshooting": "Recovering from failed/blocked submissions (422, missing fields).",
    "ambiguous_or_multiple": "Vague complaints or several issues in one utterance.",
}


def list_skills() -> str:
    """Formatted catalog of available skills for the system prompt."""
    return "\n".join(f"- {name}: {desc}" for name, desc in SKILLS.items())


def load_skill_content(name: str) -> str:
    """Return a skill's markdown body. Unknown name -> guidance + catalog (no exception),
    so the model can self-correct and call again with a valid name."""
    if name not in SKILLS:
        return (f"Unknown skill '{name}'. Call load_skill with one of these names:\n"
                f"{list_skills()}")
    with open(os.path.join(_DIR, f"{name}.md")) as f:
        return f.read()
