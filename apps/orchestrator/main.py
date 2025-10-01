"""Minimal Orchestrator API (PR2 scaffold).

Provides:
- GET /health: simple health probe
- POST /orchestrate: echoes a mock response using common models
"""
from __future__ import annotations

import time
from functools import lru_cache
from typing import Annotated
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException
from starlette.concurrency import run_in_threadpool

from packages.common.models import (
    OrchestratorRequest,
    OrchestratorResponse,
    UserContext,
)
from packages.llm.gateway import BedrockGateway, LLMGateway, LLMResult

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


if __name__ == "__main__":
    # Optional direct run: `poetry run python apps/orchestrator/main.py`
    import os

    import uvicorn

    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run("apps.orchestrator.main:app", host=host, port=port, reload=True)


# --- Production LLM chat endpoint using AWS Bedrock ---


@lru_cache(maxsize=1)
def get_llm_gateway() -> LLMGateway:
    return BedrockGateway()


@app.post("/chat", response_model=OrchestratorResponse)
async def chat(
    req: OrchestratorRequest,
    gateway: Annotated[LLMGateway, Depends(get_llm_gateway)],
) -> OrchestratorResponse:
    """Production chat endpoint backed by AWS Bedrock.

    Reads AWS configuration from environment. Returns 503 if Bedrock is not
    configured/available.
    """
    start = time.perf_counter()
    conversation_id = req.conversation_id or f"conv_{uuid4().hex[:8]}"
    try:
        # In a real system, populate UserContext from auth; here it can be None.
        user_ctx: UserContext | None = None
        result: LLMResult = await run_in_threadpool(
            gateway.complete, req.message, None, user_ctx
        )
    except Exception as e:  # noqa: BLE001
        # Prefer a concise error to the client, details go to logs
        raise HTTPException(status_code=503, detail=str(e)) from e

    latency_ms = (time.perf_counter() - start) * 1000.0
    return OrchestratorResponse(
        conversation_id=conversation_id,
        response=result.text,
        citations=[],
        cost=0.0,
        model_used=result.model_id,
        agent_used="orchestrator",
        latency_ms=latency_ms,
    )
