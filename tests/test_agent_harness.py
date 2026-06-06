from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import HumanMessage

from app.agent import (load_skill, SYSTEM, build_middleware, seed_form_on_continue,
                       form_editing_allowed)
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


def test_system_prompt_instructs_voice_friendly_replies():
    # replies are read aloud by TTS -> must be short, conversational, no markdown
    s = SYSTEM.lower()
    assert "read aloud" in s or "text-to-speech" in s
    assert "markdown" in s          # explicitly forbids markdown/bullets in the spoken reply


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


def test_continue_to_form_middleware_registered_first():
    mws = build_middleware(summary_model=FAKE_SUMMARY)
    assert type(mws[0]).__name__ == "ContinueToFormMiddleware"


# --- slice 4: deterministic Continue -> form seeding -------------------------

def test_seed_form_on_continue_fires_and_seeds_form_from_transcript():
    state = {
        "screen": "results",
        "picked_ka": "KA-01036",
        "transcript": "no heat in my apartment",
        "form": {"ka": "KA-01036"},
        "messages": [HumanMessage(content="Continue to the form")],
    }
    upd = seed_form_on_continue(state)
    assert upd is not None
    assert upd["screen"] == "form"
    assert upd["form"]["ka"] == "KA-01036"
    assert upd["form"]["description"] == "no heat in my apartment"


def test_seed_form_on_continue_does_not_fire_without_continue_intent():
    state = {
        "screen": "results",
        "picked_ka": "KA-01036",
        "transcript": "no heat in my apartment",
        "form": {"ka": "KA-01036"},
        "messages": [HumanMessage(content="actually pick the other one")],
    }
    assert seed_form_on_continue(state) is None


def test_seed_form_on_continue_does_not_fire_on_mic_screen():
    state = {
        "screen": "mic",
        "picked_ka": "KA-01036",
        "transcript": "no heat in my apartment",
        "form": {"ka": "KA-01036"},
        "messages": [HumanMessage(content="Continue to the form")],
    }
    assert seed_form_on_continue(state) is None


# --- update_form guard: not editable until the form is open -------------------

def test_form_editing_blocked_before_continue():
    assert form_editing_allowed({"screen": "results"}) is False
    assert form_editing_allowed({"screen": "mic"}) is False
    assert form_editing_allowed({}) is False


def test_form_editing_allowed_once_form_open():
    assert form_editing_allowed({"screen": "form"}) is True
    assert form_editing_allowed({"screen": "confirm"}) is True


def test_system_prompt_rules_no_premature_fill_blanks_and_clean_description():
    s = SYSTEM.lower()
    assert "not open until the user clicks continue" in s   # no fill before continue
    assert "leave it blank" in s and "never guess" in s     # blank unknown fields (e.g. borough)
    assert "not a verbatim copy" in s                       # well-formatted description
