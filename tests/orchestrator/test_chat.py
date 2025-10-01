from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from apps.orchestrator.main import app, get_llm_gateway
from packages.llm.gateway import LLMResult


class FakeGateway:
    def complete(
        self, prompt: str, system_prompt: str | None = None, user_context=None
    ) -> LLMResult:  # noqa: D401
        return LLMResult(text=f"FAKE::{prompt}", model_id="fake-model")


@pytest.mark.asyncio
async def test_chat_uses_gateway_override() -> None:
    app.dependency_overrides[get_llm_gateway] = lambda: FakeGateway()  # type: ignore[assignment]
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post("/chat", json={"message": "hello"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["response"].startswith("FAKE::hello")
        assert data["model_used"] == "fake-model"
        assert data["agent_used"] == "orchestrator"
    finally:
        app.dependency_overrides.clear()
