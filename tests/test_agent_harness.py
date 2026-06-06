from langchain_core.language_models.fake_chat_models import GenericFakeChatModel

from app.agent import load_skill, SYSTEM, build_middleware
from app.skills import SKILLS

# A fake summary model so build_middleware() never reaches out for Google credentials in
# unit tests (SummarizationMiddleware initializes its model eagerly).
FAKE_SUMMARY = GenericFakeChatModel(messages=iter([]))


# --- slice 2: load_skill tool + system prompt --------------------------------

def test_load_skill_tool_returns_skill_markdown():
    out = load_skill.invoke({"skill_name": "emergency"})
    assert "911" in out


def test_load_skill_tool_unknown_is_graceful():
    out = load_skill.invoke({"skill_name": "nope"})
    assert "nope" in out  # echoes the bad name + catalog, no exception


def test_system_prompt_advertises_the_skills():
    for name in SKILLS:
        assert name in SYSTEM
    assert "load_skill" in SYSTEM


# --- slice 3: middleware factory ---------------------------------------------

def _by_type(mws):
    return {type(m).__name__: m for m in mws}


def test_build_middleware_includes_every_requested_type():
    names = {type(m).__name__ for m in build_middleware(summary_model=FAKE_SUMMARY)}
    for expected in (
        "PIIMiddleware",
        "TodoListMiddleware",
        "SummarizationMiddleware",
        "ContextEditingMiddleware",
        "ModelCallLimitMiddleware",
        "ToolCallLimitMiddleware",
        "ModelRetryMiddleware",
        "ToolRetryMiddleware",
    ):
        assert expected in names


def test_model_call_limit_is_configured():
    m = _by_type(build_middleware(summary_model=FAKE_SUMMARY))["ModelCallLimitMiddleware"]
    assert m.thread_limit == 25
    assert m.run_limit == 12


def test_search_services_has_its_own_tool_call_limit():
    limiters = [m for m in build_middleware(summary_model=FAKE_SUMMARY)
                if type(m).__name__ == "ToolCallLimitMiddleware"]
    # one global limiter + one scoped to search_services
    scoped = [m for m in limiters if getattr(m, "tool_name", None) == "search_services"]
    assert len(scoped) == 1
