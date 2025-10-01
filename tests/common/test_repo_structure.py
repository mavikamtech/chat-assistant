"""Repo structure smoke tests for PR1 scaffolding.

Checks that key common modules and symbols exist and can be imported.
"""
from __future__ import annotations

from importlib import import_module
from pathlib import Path


def test_common_files_exist() -> None:
    root = Path(__file__).resolve().parents[2]
    assert (root / "packages" / "common" / "models.py").exists()
    assert (root / "packages" / "common" / "auth.py").exists()


def test_import_common_models() -> None:
    models = import_module("packages.common.models")
    assert hasattr(models, "UserContext")
    assert hasattr(models, "OrchestratorRequest")
    assert hasattr(models, "OrchestratorResponse")
    assert hasattr(models, "RoutingDecision")


def test_import_auth_helper() -> None:
    auth = import_module("packages.common.auth")
    assert hasattr(auth, "mock_user_context")