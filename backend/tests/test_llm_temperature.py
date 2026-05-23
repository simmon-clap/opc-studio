"""Temperature handling for provider-specific models."""

from app.services.llm_client import _is_moonshot_config, _temperature_for_payload
from app.services.role_config_service import RoleRuntimeConfig


def test_moonshot_kimi_uses_temperature_one():
    cfg = RoleRuntimeConfig(
        role_id="ceo",
        model="kimi-k2.6",
        api_provider="Custom",
        api_base_url="https://api.moonshot.cn/v1",
        api_key="sk-x",
        monthly_budget=800,
        tools=[],
        name="CEO",
        charter="",
    )
    assert _is_moonshot_config(cfg)
    assert _temperature_for_payload(cfg, 0.4) == 1


def test_openai_keeps_requested_temperature():
    cfg = RoleRuntimeConfig(
        role_id="ceo",
        model="gpt-4o",
        api_provider="OpenAI",
        api_base_url="https://api.openai.com/v1",
        api_key="sk-x",
        monthly_budget=800,
        tools=[],
        name="CEO",
        charter="",
    )
    assert not _is_moonshot_config(cfg)
    assert _temperature_for_payload(cfg, 0.4) == 0.4
