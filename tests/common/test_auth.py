"""Tests for auth helpers in mock mode."""

from packages.common.auth import mock_user_context


def test_mock_user_context() -> None:
    user = mock_user_context("tester", ["originations", "cio"])
    assert user.user_id == "tester"
    assert "originations" in user.roles
    assert "cio" in user.roles
    assert user.clearance == "PUBLIC"
