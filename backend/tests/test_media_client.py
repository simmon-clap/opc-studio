"""Media client — image and video generation."""

from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

import pytest

from app.services.media_client import generate_media, generate_video
from app.services.llm_client import LlmError


def test_generate_video_placeholder_on_404():
    session = MagicMock()
    dashboard = {"roleConfig": [], "roles": []}
    config = MagicMock()
    config.is_configured = True
    config.api_base_url = "https://api.example.com/v1"
    config.api_key = "sk-test"
    config.model = "test-video"

    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.text = "not found"

    async def _run():
        with patch(
            "app.services.media_client.get_role_runtime_config", return_value=config
        ), patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
            return await generate_video(session, dashboard, "ceo", "brand intro")

    result = asyncio.run(_run())
    assert result["ok"] is True
    assert result["type"] == "video"
    assert result.get("placeholder") is True


def test_generate_media_not_configured():
    session = MagicMock()
    dashboard = {}
    config = MagicMock()
    config.is_configured = False

    async def _run():
        with patch("app.services.media_client.get_role_runtime_config", return_value=config):
            await generate_media(session, dashboard, "ceo", "x", capability="image")

    with pytest.raises(LlmError) as exc:
        asyncio.run(_run())
    assert exc.value.code == "MEDIA_NOT_CONFIGURED"
