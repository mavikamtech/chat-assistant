"""Auth helpers for Phase 1 (mock mode)."""
from __future__ import annotations

from .models import UserContext


def mock_user_context(
    user_id: str = "test-user", roles: list[str] | None = None
) -> UserContext:
    """Construct a mock UserContext for local/dev testing.

    This avoids coupling to any IdP while enabling RBAC-like checks in code
    paths.
    """
    role_list = list(roles) if roles is not None else ["originations"]
    return UserContext(
        user_id=user_id,
        email=f"{user_id}@example.com",
        roles=role_list,
        clearance="PUBLIC",
        tenant_id="mavik",
    )
