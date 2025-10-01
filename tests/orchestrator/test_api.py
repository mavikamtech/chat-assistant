from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from apps.orchestrator.main import app


@pytest.mark.asyncio
async def test_health_ok() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "orchestrator"


@pytest.mark.asyncio
async def test_orchestrate_echo() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/orchestrate", json={"message": "hello"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["response"].startswith("Echo: hello")
    assert body["agent_used"] == "pre-screening"
