"""AWS Lambda authorizer handler."""

import json
import logging
import os
from typing import Any, Dict, Optional

from mavik_config import get_settings
from mavik_common.errors import (
    AuthenticationError,
    AuthorizationError,
    JWTValidationError,
    MNPIAccessDeniedError,
    ConfigurationError,
)

from .jwt_validator import JWTValidator
from .access_control import AccessControlManager, Permission, ResourceContext

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LambdaAuthorizer:
    """AWS Lambda authorizer for API Gateway."""
    
    def __init__(self):
        """Initialize the authorizer with configuration."""
        try:
            self.settings = get_settings()
            
            self.jwt_validator = JWTValidator(
                tenant_id=self.settings.azure_ad_tenant_id,
                client_id=self.settings.azure_ad_client_id,
                client_secret=self.settings.azure_ad_client_secret,
                jwt_secret_key=self.settings.jwt_secret_key,
                jwt_algorithm=self.settings.jwt_algorithm,
            )
            
            self.access_control = AccessControlManager(
                mnpi_enforcement_enabled=self.settings.mnpi_enforcement_enabled,
                mnpi_admin_roles=self.settings.mnpi_admin_roles,
                default_mnpi_classification=self.settings.mnpi_default_classification,
            )
            
            logger.info("Lambda authorizer initialized successfully")
            
        except Exception as e:
            logger.error(f"Authorizer initialization failed: {e}")
            raise ConfigurationError(f"Cannot initialize authorizer: {e}")
    
    def handle_request(self, event: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """Handle Lambda authorizer request from API Gateway.
        
        Args:
            event: API Gateway authorizer event
            context: Lambda context object
            
        Returns:
            API Gateway policy response
        """
        try:
            logger.info(f"Processing authorizer request: {event.get('methodArn')}")
            
            # Extract token from event
            token = self._extract_token(event)
            if not token:
                logger.warning("No authorization token provided")
                raise AuthenticationError("Missing authorization token")
            
            # Validate JWT token
            token_claims = self.jwt_validator.validate_token(token)
            
            # Create access context
            access_context = self.access_control.get_user_context_from_token(token_claims)
            
            # Extract resource information from method ARN
            resource_context = self._extract_resource_context(event)
            
            # Check basic access permission
            required_permission = self._determine_required_permission(event)
            
            # Perform access control check
            self.access_control.check_permission(
                access_context=access_context,
                permission=required_permission,
                resource_context=resource_context,
            )
            
            # Generate policy response
            policy = self._generate_policy(
                user_id=access_context.user_id,
                effect="Allow",
                resource=event["methodArn"],
                context=self.access_control.create_policy_context(
                    access_context, resource_context
                ),
            )
            
            logger.info(f"Access granted for user: {access_context.user_id}")
            return policy
            
        except AuthenticationError as e:
            logger.warning(f"Authentication failed: {e}")
            raise  # Re-raise to return 401
            
        except (AuthorizationError, MNPIAccessDeniedError) as e:
            logger.warning(f"Authorization failed: {e}")
            
            # Generate deny policy for authorization failures
            return self._generate_policy(
                user_id="unknown",
                effect="Deny",
                resource=event["methodArn"],
                context={"error": str(e)},
            )
            
        except Exception as e:
            logger.error(f"Authorizer error: {e}")
            
            # Generate deny policy for unexpected errors
            return self._generate_policy(
                user_id="unknown",
                effect="Deny",
                resource=event["methodArn"],
                context={"error": "Internal authorization error"},
            )
    
    def _extract_token(self, event: Dict[str, Any]) -> Optional[str]:
        """Extract JWT token from API Gateway event."""
        
        # Check authorizationToken (for TOKEN authorizer)
        if "authorizationToken" in event:
            return event["authorizationToken"]
        
        # Check headers (for REQUEST authorizer)
        headers = event.get("headers", {})
        
        # Try Authorization header
        auth_header = headers.get("Authorization") or headers.get("authorization")
        if auth_header:
            return auth_header
        
        # Try x-api-key header
        api_key = headers.get("x-api-key") or headers.get("X-API-Key")
        if api_key:
            return api_key
        
        # Check query parameters
        query_params = event.get("queryStringParameters") or {}
        token = query_params.get("token")
        if token:
            return token
        
        return None
    
    def _extract_resource_context(self, event: Dict[str, Any]) -> Optional[ResourceContext]:
        """Extract resource context from API Gateway event."""
        
        try:
            method_arn = event.get("methodArn", "")
            
            # Parse method ARN: arn:aws:execute-api:region:account:api-id/stage/method/resource-path
            arn_parts = method_arn.split("/")
            
            if len(arn_parts) < 3:
                return None
            
            http_method = arn_parts[2] if len(arn_parts) > 2 else "GET"
            resource_path = "/".join(arn_parts[3:]) if len(arn_parts) > 3 else ""
            
            # Determine resource type from path
            resource_type = self._determine_resource_type(resource_path)
            
            # Extract resource ID if present
            resource_id = self._extract_resource_id(resource_path)
            
            # Get MNPI classification from headers or path
            headers = event.get("headers", {})
            mnpi_classification = headers.get("x-mnpi-classification")
            
            return ResourceContext(
                resource_type=resource_type,
                resource_id=resource_id,
                mnpi_classification=mnpi_classification,
            )
            
        except Exception as e:
            logger.warning(f"Failed to extract resource context: {e}")
            return None
    
    def _determine_resource_type(self, resource_path: str) -> str:
        """Determine resource type from API path."""
        
        path_lower = resource_path.lower()
        
        if "deals" in path_lower:
            return "deal"
        elif "documents" in path_lower:
            return "document"
        elif "analysis" in path_lower or "analyze" in path_lower:
            return "analysis"
        elif "reports" in path_lower:
            return "report"
        elif "users" in path_lower:
            return "user"
        else:
            return "api"
    
    def _extract_resource_id(self, resource_path: str) -> Optional[str]:
        """Extract resource ID from API path."""
        
        # Common patterns: /resource/{id}, /resource/{id}/action
        path_parts = resource_path.split("/")
        
        for i, part in enumerate(path_parts):
            # Look for UUID-like patterns or numeric IDs
            if (len(part) > 8 and 
                (part.replace("-", "").replace("_", "").isalnum() or part.isdigit())):
                return part
        
        return None
    
    def _determine_required_permission(self, event: Dict[str, Any]) -> Permission:
        """Determine required permission based on HTTP method and resource."""
        
        method_arn = event.get("methodArn", "")
        arn_parts = method_arn.split("/")
        
        http_method = arn_parts[2].upper() if len(arn_parts) > 2 else "GET"
        resource_path = "/".join(arn_parts[3:]).lower() if len(arn_parts) > 3 else ""
        
        # Determine permission based on method and resource
        if "deals" in resource_path:
            if http_method in ["POST", "PUT", "PATCH"]:
                return Permission.WRITE_DEALS
            elif http_method == "DELETE":
                return Permission.DELETE_DEALS
            else:
                return Permission.READ_DEALS
        
        elif "documents" in resource_path:
            if http_method == "POST":
                return Permission.UPLOAD_DOCUMENTS
            elif http_method == "DELETE":
                return Permission.DELETE_DOCUMENTS
            else:
                return Permission.VIEW_DOCUMENTS
        
        elif "analysis" in resource_path or "analyze" in resource_path:
            if http_method == "POST":
                return Permission.RUN_ANALYSIS
            else:
                return Permission.VIEW_ANALYSIS
        
        elif "reports" in resource_path:
            if http_method == "POST":
                return Permission.GENERATE_REPORTS
            else:
                return Permission.VIEW_REPORTS
        
        elif "users" in resource_path or "admin" in resource_path:
            return Permission.MANAGE_USERS
        
        # Default to read permission for unknown resources
        return Permission.READ_DEALS
    
    def _generate_policy(
        self,
        user_id: str,
        effect: str,
        resource: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate API Gateway policy response.
        
        Args:
            user_id: User identifier (principal ID)
            effect: Allow or Deny
            resource: Resource ARN
            context: Additional context to pass to downstream services
            
        Returns:
            API Gateway policy response
        """
        
        policy = {
            "principalId": user_id,
            "policyDocument": {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Action": "execute-api:Invoke",
                        "Effect": effect,
                        "Resource": resource,
                    }
                ],
            },
        }
        
        # Add context for downstream services
        if context:
            # Limit context size to avoid Lambda limits
            context_str = json.dumps(context, default=str)
            if len(context_str) > 4096:  # API Gateway context limit
                context = {"user_id": user_id, "truncated": True}
            
            policy["context"] = context
        
        return policy


# Lambda handler function
def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """AWS Lambda handler for API Gateway authorizer.
    
    Args:
        event: API Gateway authorizer event
        context: Lambda runtime context
        
    Returns:
        API Gateway policy response
    """
    
    try:
        authorizer = LambdaAuthorizer()
        return authorizer.handle_request(event, context)
        
    except AuthenticationError:
        # Return 401 for authentication failures
        raise Exception("Unauthorized")
        
    except Exception as e:
        logger.error(f"Lambda handler error: {e}")
        
        # Generate deny policy for all errors
        return {
            "principalId": "unknown",
            "policyDocument": {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Action": "execute-api:Invoke",
                        "Effect": "Deny",
                        "Resource": event.get("methodArn", "*"),
                    }
                ],
            },
            "context": {
                "error": "Authorization failed",
            },
        }