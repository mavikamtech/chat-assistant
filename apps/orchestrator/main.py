"""Minimal Orchestrator API (PR2 scaffold).

Provides:
- GET /health: simple health probe
- POST /orchestrate: echoes a mock response using common models
"""
from __future__ import annotations

from uuid import uuid4

from fastapi import FastAPI

from packages.common.models import OrchestratorRequest, OrchestratorResponse

app = FastAPI(title="Mavik Orchestrator", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "orchestrator", "version": app.version or "0"}


@app.post("/orchestrate", response_model=OrchestratorResponse)
async def orchestrate(req: OrchestratorRequest) -> OrchestratorResponse:
    conversation_id = req.conversation_id or f"conv_{uuid4().hex[:8]}"
    # Mock behavior: echo the message and provide a canned agent/model
    return OrchestratorResponse(
        conversation_id=conversation_id,
        response=f"Echo: {req.message}",
        citations=[],
        cost=0.0,
        model_used="mock-llm",
        agent_used="pre-screening",
        latency_ms=0.0,
    )


__all__ = ["app"]
