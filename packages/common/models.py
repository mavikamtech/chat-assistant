"""Pydantic models used across Mavik AI (Phase 1 MVP).

These include user context, orchestrator request/response, and simple routing
decision models required by PR1/PR2 scaffolding and tests.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class UserContext(BaseModel):
    """Represents the authenticated user and RBAC context."""

    user_id: str
    email: str | None = None
    roles: list[str] = Field(default_factory=list)
    clearance: str = "PUBLIC"
    tenant_id: str | None = None


class OrchestratorRequest(BaseModel):
    """Input schema for the orchestrator REST endpoint."""

    message: str
    deal_id: str | None = None
    conversation_id: str | None = None
    attachments: list[str] = Field(default_factory=list)


class OrchestratorResponse(BaseModel):
    """Standard response from orchestrator."""

    conversation_id: str
    response: str
    citations: list[dict[str, Any]] = Field(default_factory=list)
    cost: float = 0.0
    model_used: str = "mock"
    agent_used: str = "pre-screening"
    latency_ms: float = 0.0


class RoutingDecision(BaseModel):
    """Simple routing decision used by rule-based classifier."""

    agent: str
    confidence: float
    reasoning: str | None = None
