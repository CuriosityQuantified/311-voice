from app.skills import SKILLS, list_skills, load_skill_content

EXPECTED = {
    "service_selection",
    "address_and_borough",
    "emergency",
    "form_fields",
    "submission_troubleshooting",
    "ambiguous_or_multiple",
}


def test_registry_has_the_six_skills():
    assert set(SKILLS) == EXPECTED


def test_list_skills_names_every_skill_with_its_description():
    cat = list_skills()
    for name, desc in SKILLS.items():
        assert name in cat
        assert desc in cat


def test_load_skill_content_returns_the_markdown_body():
    body = load_skill_content("emergency")
    # the emergency skill must tell the agent to route 911 items, not submit
    assert "911" in body
    assert len(body.strip()) > 50


def test_load_skill_content_unknown_returns_guidance_and_catalog():
    msg = load_skill_content("does_not_exist")
    # no exception; the model should be able to self-correct from the reply
    assert "does_not_exist" in msg
    for name in SKILLS:
        assert name in msg
