"""Test configuration and fixtures."""

import os
import pytest
from unittest.mock import Mock


@pytest.fixture(autouse=True)
def mock_environment():
    """Mock environment variables for testing."""
    env_vars = {
        "AWS_REGION": "us-east-1",
        "AZURE_AD_TENANT_ID": "test-tenant-id",
        "AZURE_AD_CLIENT_ID": "test-client-id", 
        "AZURE_AD_CLIENT_SECRET": "test-client-secret",
        "JWT_SECRET_KEY": "test-jwt-secret-key-for-testing",
        "JWT_ALGORITHM": "HS256",
        "MNPI_ENFORCEMENT_ENABLED": "true",
        "MNPI_DEFAULT_CLASSIFICATION": "public",
        "LOG_LEVEL": "INFO",
        "ENVIRONMENT": "test",
    }
    
    for key, value in env_vars.items():
        os.environ[key] = value
    
    yield
    
    # Cleanup
    for key in env_vars.keys():
        if key in os.environ:
            del os.environ[key]


@pytest.fixture
def lambda_context():
    """Mock AWS Lambda context."""
    context = Mock()
    context.function_name = "test-authorizer"
    context.function_version = "1"
    context.invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:test-authorizer"
    context.memory_limit_in_mb = 128
    context.remaining_time_in_millis = Mock(return_value=30000)
    context.aws_request_id = "test-request-id"
    return context