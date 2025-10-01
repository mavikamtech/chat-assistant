"""Tests for shared Pydantic models used in Phase 1 scaffolding."""

from packages.common.models import (
    OrchestratorRequest,
    RoutingDecision,
    UserContext,
)


def test_user_context_valid() -> None:
    user = UserContext(
        user_id="test-123",
        email="test@mavik.com",
        roles=["originations"],
        clearance="PUBLIC",
        tenant_id="mavik",
    )
    assert user.user_id == "test-123"
    assert "originations" in user.roles


def test_orchestrator_request_minimal() -> None:
    req = OrchestratorRequest(message="Test message")
    assert req.message == "Test message"
    assert req.deal_id is None
    assert req.attachments == []


def test_routing_decision_validation() -> None:
    decision = RoutingDecision(
        agent="pre-screening",
        confidence=0.95,
        reasoning="Test reasoning",
    )
    assert decision.agent == "pre-screening"
    assert decision.confidence == 0.95
