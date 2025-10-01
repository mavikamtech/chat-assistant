"""Shared common utilities and models for Mavik AI.

This package provides pydantic models and lightweight helpers that are
intentionally decoupled from service-specific implementations so they can be
reused across orchestrator and MCP tools.
"""

from .models import (  # noqa: F401
    OrchestratorRequest,
    OrchestratorResponse,
    RoutingDecision,
    UserContext,
)
