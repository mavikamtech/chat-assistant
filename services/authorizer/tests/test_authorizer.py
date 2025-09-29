"""Unit tests for Lambda authorizer."""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from authorizer.handler import LambdaAuthorizer
from authorizer.jwt_validator import JWTValidator
from authorizer.access_control import AccessControlManager, Permission, AccessContext

from mavik_common.errors import (
    AuthenticationError,
    AuthorizationError,
    JWTValidationError,
)


@pytest.fixture
def mock_settings():
    """Mock application settings."""
    settings = Mock()
    settings.azure_ad_tenant_id = "test-tenant-id"
    settings.azure_ad_client_id = "test-client-id"
    settings.azure_ad_client_secret = "test-client-secret"
    settings.jwt_secret_key = "test-jwt-secret"
    settings.jwt_algorithm = "HS256"
    settings.mnpi_enforcement_enabled = True
    settings.mnpi_admin_roles = ["admin", "compliance_officer"]
    settings.mnpi_default_classification = "public"
    return settings


@pytest.fixture
def sample_token_claims():
    """Sample JWT token claims."""
    return {
        "sub": "test-user-123",
        "email": "test@mavikcapital.com",
        "preferred_username": "test@mavikcapital.com",
        "roles": ["analyst"],
        "department": ["real-estate"],
        "iat": datetime.now(timezone.utc).timestamp(),
        "exp": datetime.now(timezone.utc).timestamp() + 3600,
        "iss": "mavik-authorizer",
        "aud": "test-client-id",
    }


@pytest.fixture
def sample_api_gateway_event():
    """Sample API Gateway authorizer event."""
    return {
        "type": "REQUEST",
        "authorizationToken": "Bearer test-jwt-token",
        "methodArn": "arn:aws:execute-api:us-east-1:123456789012:abcdef123/test/GET/deals/123",
        "headers": {
            "Authorization": "Bearer test-jwt-token",
            "Content-Type": "application/json",
        },
        "queryStringParameters": {},
        "requestContext": {
            "identity": {
                "sourceIp": "192.168.1.1",
                "userAgent": "test-client/1.0",
            }
        }
    }


class TestLambdaAuthorizer:
    """Test cases for Lambda authorizer."""
    
    @patch('authorizer.handler.get_settings')
    def test_init_success(self, mock_get_settings, mock_settings):
        """Test successful authorizer initialization."""
        mock_get_settings.return_value = mock_settings
        
        authorizer = LambdaAuthorizer()
        
        assert authorizer.settings == mock_settings
        assert isinstance(authorizer.jwt_validator, JWTValidator)
        assert isinstance(authorizer.access_control, AccessControlManager)
    
    @patch('authorizer.handler.get_settings')
    def test_handle_request_success(
        self, 
        mock_get_settings, 
        mock_settings,
        sample_api_gateway_event,
        sample_token_claims
    ):
        """Test successful authorization request."""
        mock_get_settings.return_value = mock_settings
        
        authorizer = LambdaAuthorizer()
        
        # Mock JWT validation
        authorizer.jwt_validator.validate_token = Mock(return_value=sample_token_claims)
        
        # Mock access control
        authorizer.access_control.check_permission = Mock(return_value=True)
        authorizer.access_control.get_user_context_from_token = Mock(
            return_value=AccessContext(
                user_id="test-user-123",
                email="test@mavikcapital.com",
                roles=["analyst"],
                departments=["real-estate"]
            )
        )
        authorizer.access_control.create_policy_context = Mock(return_value={})
        
        # Execute request
        result = authorizer.handle_request(sample_api_gateway_event, Mock())
        
        # Verify result
        assert result["principalId"] == "test-user-123"
        assert result["policyDocument"]["Statement"][0]["Effect"] == "Allow"
        assert "deals/123" in result["policyDocument"]["Statement"][0]["Resource"]
    
    @patch('authorizer.handler.get_settings')
    def test_handle_request_missing_token(
        self, 
        mock_get_settings, 
        mock_settings,
        sample_api_gateway_event
    ):
        """Test request with missing authorization token."""
        mock_get_settings.return_value = mock_settings
        
        # Remove token from event
        del sample_api_gateway_event["authorizationToken"]
        del sample_api_gateway_event["headers"]["Authorization"]
        
        authorizer = LambdaAuthorizer()
        
        # Execute request - should generate deny policy
        result = authorizer.handle_request(sample_api_gateway_event, Mock())
        
        # Verify deny policy
        assert result["principalId"] == "unknown"
        assert result["policyDocument"]["Statement"][0]["Effect"] == "Deny"
        assert "error" in result["context"]
    
    @patch('authorizer.handler.get_settings')
    def test_handle_request_invalid_token(
        self, 
        mock_get_settings, 
        mock_settings,
        sample_api_gateway_event
    ):
        """Test request with invalid JWT token."""
        mock_get_settings.return_value = mock_settings
        
        authorizer = LambdaAuthorizer()
        
        # Mock JWT validation failure
        authorizer.jwt_validator.validate_token = Mock(
            side_effect=AuthenticationError("Invalid token")
        )
        
        # Execute request - should raise exception
        with pytest.raises(AuthenticationError):
            authorizer.handle_request(sample_api_gateway_event, Mock())
    
    @patch('authorizer.handler.get_settings')
    def test_handle_request_authorization_denied(
        self, 
        mock_get_settings, 
        mock_settings,
        sample_api_gateway_event,
        sample_token_claims
    ):
        """Test request with authorization denied."""
        mock_get_settings.return_value = mock_settings
        
        authorizer = LambdaAuthorizer()
        
        # Mock JWT validation success
        authorizer.jwt_validator.validate_token = Mock(return_value=sample_token_claims)
        
        # Mock user context creation
        authorizer.access_control.get_user_context_from_token = Mock(
            return_value=AccessContext(
                user_id="test-user-123",
                email="test@mavikcapital.com",
                roles=["viewer"],  # Limited role
                departments=["real-estate"]
            )
        )
        
        # Mock access control denial
        authorizer.access_control.check_permission = Mock(
            side_effect=AuthorizationError("Insufficient permissions")
        )
        
        # Execute request
        result = authorizer.handle_request(sample_api_gateway_event, Mock())
        
        # Verify deny policy
        assert result["principalId"] == "unknown"
        assert result["policyDocument"]["Statement"][0]["Effect"] == "Deny"
        assert "error" in result["context"]
    
    def test_extract_token_from_header(self, sample_api_gateway_event):
        """Test token extraction from Authorization header."""
        authorizer = LambdaAuthorizer.__new__(LambdaAuthorizer)
        
        token = authorizer._extract_token(sample_api_gateway_event)
        
        assert token == "Bearer test-jwt-token"
    
    def test_extract_token_from_query_param(self):
        """Test token extraction from query parameters."""
        authorizer = LambdaAuthorizer.__new__(LambdaAuthorizer)
        
        event = {
            "queryStringParameters": {
                "token": "query-token-123"
            }
        }
        
        token = authorizer._extract_token(event)
        
        assert token == "query-token-123"
    
    def test_determine_resource_type(self):
        """Test resource type determination from path."""
        authorizer = LambdaAuthorizer.__new__(LambdaAuthorizer)
        
        assert authorizer._determine_resource_type("deals/123") == "deal"
        assert authorizer._determine_resource_type("documents/upload") == "document"
        assert authorizer._determine_resource_type("analysis/run") == "analysis"
        assert authorizer._determine_resource_type("reports/generate") == "report"
        assert authorizer._determine_resource_type("unknown/path") == "api"
    
    def test_determine_required_permission(self):
        """Test permission determination from method and path."""
        authorizer = LambdaAuthorizer.__new__(LambdaAuthorizer)
        
        # Test deal permissions
        event = {"methodArn": "arn:aws:execute-api:region:account:api/stage/GET/deals/123"}
        assert authorizer._determine_required_permission(event) == Permission.READ_DEALS
        
        event = {"methodArn": "arn:aws:execute-api:region:account:api/stage/POST/deals"}
        assert authorizer._determine_required_permission(event) == Permission.WRITE_DEALS
        
        event = {"methodArn": "arn:aws:execute-api:region:account:api/stage/DELETE/deals/123"}
        assert authorizer._determine_required_permission(event) == Permission.DELETE_DEALS
        
        # Test document permissions
        event = {"methodArn": "arn:aws:execute-api:region:account:api/stage/POST/documents"}
        assert authorizer._determine_required_permission(event) == Permission.UPLOAD_DOCUMENTS
    
    def test_generate_allow_policy(self):
        """Test generation of allow policy."""
        authorizer = LambdaAuthorizer.__new__(LambdaAuthorizer)
        
        policy = authorizer._generate_policy(
            user_id="test-user",
            effect="Allow",
            resource="arn:aws:execute-api:region:account:api/stage/GET/deals",
            context={"role": "analyst"}
        )
        
        assert policy["principalId"] == "test-user"
        assert policy["policyDocument"]["Statement"][0]["Effect"] == "Allow"
        assert policy["policyDocument"]["Statement"][0]["Action"] == "execute-api:Invoke"
        assert policy["context"]["role"] == "analyst"
    
    def test_generate_deny_policy(self):
        """Test generation of deny policy."""
        authorizer = LambdaAuthorizer.__new__(LambdaAuthorizer)
        
        policy = authorizer._generate_policy(
            user_id="unknown",
            effect="Deny",
            resource="arn:aws:execute-api:region:account:api/stage/GET/deals",
            context={"error": "Access denied"}
        )
        
        assert policy["principalId"] == "unknown"
        assert policy["policyDocument"]["Statement"][0]["Effect"] == "Deny"
        assert policy["context"]["error"] == "Access denied"


class TestJWTValidator:
    """Test cases for JWT validator."""
    
    def test_init(self):
        """Test JWT validator initialization."""
        validator = JWTValidator(
            tenant_id="test-tenant",
            client_id="test-client",
            client_secret="test-secret",
            jwt_secret_key="test-key",
        )
        
        assert validator.tenant_id == "test-tenant"
        assert validator.client_id == "test-client"
        assert validator.jwt_secret_key == "test-key"
    
    @patch('requests.get')
    def test_get_azure_ad_keys(self, mock_get):
        """Test Azure AD keys retrieval."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "keys": [
                {
                    "kid": "test-key-id",
                    "kty": "RSA",
                    "use": "sig",
                    "n": "test-modulus",
                    "e": "AQAB"
                }
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        validator = JWTValidator(
            tenant_id="test-tenant",
            client_id="test-client",
            client_secret="test-secret"
        )
        
        keys = validator._get_azure_ad_keys()
        
        assert "keys" in keys
        assert len(keys["keys"]) == 1
        assert keys["keys"][0]["kid"] == "test-key-id"
        
        # Verify caching
        mock_get.assert_called_once()
        
        # Second call should use cache
        keys2 = validator._get_azure_ad_keys()
        assert keys == keys2
        mock_get.assert_called_once()  # Still only one call


class TestAccessControl:
    """Test cases for access control."""
    
    def test_init(self):
        """Test access control manager initialization."""
        manager = AccessControlManager(
            mnpi_enforcement_enabled=True,
            mnpi_admin_roles=["admin"],
            default_mnpi_classification="internal"
        )
        
        assert manager.mnpi_enforcement_enabled is True
        assert manager.mnpi_admin_roles == ["admin"]
        assert manager.default_mnpi_classification == "internal"
    
    def test_get_user_permissions(self):
        """Test user permission calculation."""
        manager = AccessControlManager()
        
        permissions = manager._get_user_permissions(["analyst"])
        
        assert Permission.READ_DEALS in permissions
        assert Permission.WRITE_DEALS in permissions
        assert Permission.RUN_ANALYSIS in permissions
        assert Permission.ACCESS_MNPI_INTERNAL in permissions
        assert Permission.ACCESS_MNPI_RESTRICTED not in permissions
    
    def test_check_permission_success(self):
        """Test successful permission check."""
        manager = AccessControlManager()
        
        access_context = AccessContext(
            user_id="test-user",
            email="test@example.com",
            roles=["analyst"]
        )
        
        # Should not raise exception
        result = manager.check_permission(access_context, Permission.READ_DEALS)
        assert result is True
    
    def test_check_permission_denied(self):
        """Test permission denied."""
        manager = AccessControlManager()
        
        access_context = AccessContext(
            user_id="test-user",
            email="test@example.com",
            roles=["viewer"]  # Limited permissions
        )
        
        with pytest.raises(AuthorizationError):
            manager.check_permission(access_context, Permission.DELETE_DEALS)
    
    def test_get_user_context_from_token(self):
        """Test user context extraction from token claims."""
        manager = AccessControlManager()
        
        token_claims = {
            "sub": "user-123",
            "email": "user@example.com",
            "roles": ["analyst", "senior_analyst"],
            "department": ["real-estate", "investment"]
        }
        
        context = manager.get_user_context_from_token(token_claims)
        
        assert context.user_id == "user-123"
        assert context.email == "user@example.com"
        assert context.roles == ["analyst", "senior_analyst"]
        assert context.departments == ["real-estate", "investment"]