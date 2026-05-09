from factory_agent.config import get_settings


def test_production_mode_prefers_production_llm_overrides(monkeypatch):
    monkeypatch.setenv("APP_MODE", "production")
    monkeypatch.setenv("PLANNER_MODEL", "dev-planner")
    monkeypatch.setenv("OPENAI_API_KEY", "dev-key")
    monkeypatch.setenv("PRODUCTION_PLANNER_MODEL", "gemma-3-12b-it")
    monkeypatch.setenv("PRODUCTION_SUMMARY_MODEL", "gemma-3-4b-it")
    monkeypatch.setenv("PRODUCTION_TOOL_RESULT_SUMMARY_MODEL", "gemma-3-4b-it")
    monkeypatch.setenv("PRODUCTION_TOOL_SELECTOR_MODEL", "gemma-3-12b-it")
    monkeypatch.setenv("PRODUCTION_OPENAI_API_KEY", "prod-key")

    settings = get_settings()

    assert settings.planner_model == "gemma-3-12b-it"
    assert settings.summary_model == "gemma-3-4b-it"
    assert settings.tool_result_summary_model == "gemma-3-4b-it"
    assert settings.tool_selector_model == "gemma-3-12b-it"
    assert settings.openai_api_key == "prod-key"


def test_development_mode_prefers_development_scoped_override(monkeypatch):
    monkeypatch.setenv("APP_MODE", "development")
    monkeypatch.setenv("PLANNER_MODEL", "shared-planner")
    monkeypatch.setenv("DEVELOPMENT_PLANNER_MODEL", "dev-scoped-planner")

    settings = get_settings()

    assert settings.planner_model == "dev-scoped-planner"
