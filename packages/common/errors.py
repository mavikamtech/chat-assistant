"""Custom exception hierarchy for Mavik AI system.

This module defines all custom exceptions used across the MCP tools and orchestrator.
All exceptions include structured error codes and context for proper error handling.
"""

from typing import Any, Dict, Optional


class MavikError(Exception):
    """Base exception class for all Mavik AI errors."""
    
    def __init__(
        self,
        message: str,
        error_code: str = "MAVIK_ERROR",
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        """Initialize Mavik error.
        
        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
            context: Additional error context
            cause: Underlying exception that caused this error
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.context = context or {}
        self.cause = cause
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary representation."""
        return {
            "error_type": self.__class__.__name__,
            "error_code": self.error_code,
            "message": self.message,
            "context": self.context,
            "cause": str(self.cause) if self.cause else None,
        }


# ===== Configuration and Setup Errors =====

class ConfigurationError(MavikError):
    """Raised when there's an invalid configuration."""
    
    def __init__(self, message: str, config_key: Optional[str] = None, **kwargs):
        super().__init__(
            message=message,
            error_code="CONFIG_ERROR",
            context={"config_key": config_key} if config_key else {},
            **kwargs
        )


class MissingEnvironmentVariableError(ConfigurationError):
    """Raised when a required environment variable is missing."""
    
    def __init__(self, var_name: str, **kwargs):
        super().__init__(
            message=f"Required environment variable '{var_name}' is not set",
            error_code="MISSING_ENV_VAR",
            context={"variable_name": var_name},
            **kwargs
        )


class InvalidConfigurationValueError(ConfigurationError):
    """Raised when a configuration value is invalid."""
    
    def __init__(self, config_key: str, value: Any, expected: str, **kwargs):
        super().__init__(
            message=f"Invalid value for '{config_key}': {value}. Expected: {expected}",
            error_code="INVALID_CONFIG_VALUE", 
            context={"config_key": config_key, "value": str(value), "expected": expected},
            **kwargs
        )


# ===== Authentication and Authorization Errors =====

class AuthenticationError(MavikError):
    """Raised when authentication fails."""
    
    def __init__(self, message: str = "Authentication failed", **kwargs):
        super().__init__(
            message=message,
            error_code="AUTH_FAILED",
            **kwargs
        )


class AuthorizationError(MavikError):
    """Raised when authorization fails."""
    
    def __init__(self, message: str = "Authorization failed", resource: Optional[str] = None, **kwargs):
        super().__init__(
            message=message,
            error_code="AUTHZ_FAILED",
            context={"resource": resource} if resource else {},
            **kwargs
        )


class JWTValidationError(AuthenticationError):
    """Raised when JWT token validation fails."""
    
    def __init__(self, reason: str, token_type: str = "access_token", **kwargs):
        super().__init__(
            message=f"JWT validation failed: {reason}",
            error_code="JWT_INVALID",
            context={"reason": reason, "token_type": token_type},
            **kwargs
        )


class MNPIAccessDeniedError(AuthorizationError):
    """Raised when MNPI access is denied."""
    
    def __init__(self, clearance_required: str, clearance_held: str, **kwargs):
        super().__init__(
            message=f"MNPI access denied. Required: {clearance_required}, Held: {clearance_held}",
            error_code="MNPI_ACCESS_DENIED",
            context={"clearance_required": clearance_required, "clearance_held": clearance_held},
            **kwargs
        )


# ===== Validation Errors =====

class ValidationError(MavikError):
    """Raised when input validation fails."""
    
    def __init__(self, message: str, field: Optional[str] = None, value: Any = None, **kwargs):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            context={"field": field, "value": str(value) if value is not None else None},
            **kwargs
        )


class SchemaValidationError(ValidationError):
    """Raised when schema validation fails."""
    
    def __init__(self, schema_name: str, errors: list, **kwargs):
        super().__init__(
            message=f"Schema validation failed for {schema_name}: {errors}",
            error_code="SCHEMA_VALIDATION_ERROR",
            context={"schema_name": schema_name, "validation_errors": errors},
            **kwargs
        )


class RequiredFieldError(ValidationError):
    """Raised when a required field is missing."""
    
    def __init__(self, field_name: str, **kwargs):
        super().__init__(
            message=f"Required field '{field_name}' is missing",
            error_code="REQUIRED_FIELD_MISSING",
            context={"field_name": field_name},
            **kwargs
        )


# ===== AWS Service Errors =====

class AWSServiceError(MavikError):
    """Base class for AWS service-related errors."""
    
    def __init__(self, service: str, operation: str, message: str, **kwargs):
        super().__init__(
            message=f"AWS {service} {operation} failed: {message}",
            error_code="AWS_SERVICE_ERROR",
            context={"service": service, "operation": operation},
            **kwargs
        )


class BedrockError(AWSServiceError):
    """Raised when Bedrock API calls fail."""
    
    def __init__(self, operation: str, message: str, model_id: Optional[str] = None, **kwargs):
        super().__init__(
            service="Bedrock",
            operation=operation,
            message=message,
            context={"model_id": model_id} if model_id else {},
            **kwargs
        )


class BedrockModelNotFoundError(BedrockError):
    """Raised when specified Bedrock model is not available."""
    
    def __init__(self, model_id: str, **kwargs):
        super().__init__(
            operation="model_access",
            message=f"Model '{model_id}' not found or not accessible",
            error_code="BEDROCK_MODEL_NOT_FOUND",
            model_id=model_id,
            **kwargs
        )


class BedrockTokenLimitError(BedrockError):
    """Raised when Bedrock token limit is exceeded."""
    
    def __init__(self, requested_tokens: int, max_tokens: int, **kwargs):
        super().__init__(
            operation="invoke_model", 
            message=f"Token limit exceeded: {requested_tokens} > {max_tokens}",
            error_code="BEDROCK_TOKEN_LIMIT",
            context={"requested_tokens": requested_tokens, "max_tokens": max_tokens},
            **kwargs
        )


class S3Error(AWSServiceError):
    """Raised when S3 operations fail."""
    
    def __init__(self, operation: str, bucket: str, key: str, message: str, **kwargs):
        super().__init__(
            service="S3",
            operation=operation,
            message=message,
            context={"bucket": bucket, "key": key},
            **kwargs
        )


class S3ObjectNotFoundError(S3Error):
    """Raised when S3 object is not found."""
    
    def __init__(self, bucket: str, key: str, **kwargs):
        super().__init__(
            operation="get_object",
            bucket=bucket,
            key=key,
            message=f"Object not found: s3://{bucket}/{key}",
            error_code="S3_OBJECT_NOT_FOUND",
            **kwargs
        )


class DynamoDBError(AWSServiceError):
    """Raised when DynamoDB operations fail."""
    
    def __init__(self, operation: str, table: str, message: str, **kwargs):
        super().__init__(
            service="DynamoDB",
            operation=operation,
            message=message,
            context={"table": table},
            **kwargs
        )


class OpenSearchError(AWSServiceError):
    """Raised when OpenSearch operations fail."""
    
    def __init__(self, operation: str, index: str, message: str, **kwargs):
        super().__init__(
            service="OpenSearch",
            operation=operation,
            message=message,
            context={"index": index},
            **kwargs
        )


class RDSError(AWSServiceError):
    """Raised when RDS operations fail."""
    
    def __init__(self, operation: str, database: str, message: str, **kwargs):
        super().__init__(
            service="RDS",
            operation=operation,
            message=message,
            context={"database": database},
            **kwargs
        )


class TextractError(AWSServiceError):
    """Raised when Textract operations fail."""
    
    def __init__(self, operation: str, document: str, message: str, **kwargs):
        super().__init__(
            service="Textract",
            operation=operation,
            message=message,
            context={"document": document},
            **kwargs
        )


# ===== MCP Protocol Errors =====

class MCPError(MavikError):
    """Base class for MCP protocol errors."""
    
    def __init__(self, message: str, tool_name: Optional[str] = None, **kwargs):
        super().__init__(
            message=message,
            error_code="MCP_ERROR",
            context={"tool_name": tool_name} if tool_name else {},
            **kwargs
        )


class MCPConnectionError(MCPError):
    """Raised when MCP connection fails."""
    
    def __init__(self, tool_name: str, endpoint: str, **kwargs):
        super().__init__(
            message=f"Failed to connect to MCP tool '{tool_name}' at {endpoint}",
            error_code="MCP_CONNECTION_ERROR",
            tool_name=tool_name,
            context={"endpoint": endpoint},
            **kwargs
        )


class MCPTimeoutError(MCPError):
    """Raised when MCP call times out."""
    
    def __init__(self, tool_name: str, timeout_ms: int, **kwargs):
        super().__init__(
            message=f"MCP call to '{tool_name}' timed out after {timeout_ms}ms",
            error_code="MCP_TIMEOUT",
            tool_name=tool_name,
            context={"timeout_ms": timeout_ms},
            **kwargs
        )


class MCPProtocolError(MCPError):
    """Raised when MCP protocol violation occurs."""
    
    def __init__(self, message: str, tool_name: str, **kwargs):
        super().__init__(
            message=f"MCP protocol error with '{tool_name}': {message}",
            error_code="MCP_PROTOCOL_ERROR",
            tool_name=tool_name,
            **kwargs
        )


class MCPToolUnavailableError(MCPError):
    """Raised when MCP tool is unavailable."""
    
    def __init__(self, tool_name: str, reason: str = "Service unavailable", **kwargs):
        super().__init__(
            message=f"MCP tool '{tool_name}' is unavailable: {reason}",
            error_code="MCP_TOOL_UNAVAILABLE", 
            tool_name=tool_name,
            context={"reason": reason},
            **kwargs
        )


# ===== Business Logic Errors =====

class BusinessLogicError(MavikError):
    """Base class for business logic errors."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code="BUSINESS_LOGIC_ERROR",
            **kwargs
        )


class DealNotFoundError(BusinessLogicError):
    """Raised when a deal is not found."""
    
    def __init__(self, deal_id: str, **kwargs):
        super().__init__(
            message=f"Deal not found: {deal_id}",
            error_code="DEAL_NOT_FOUND",
            context={"deal_id": deal_id},
            **kwargs
        )


class InsufficientDataError(BusinessLogicError):
    """Raised when insufficient data is available for analysis."""
    
    def __init__(self, required_data: str, available_data: Optional[str] = None, **kwargs):
        super().__init__(
            message=f"Insufficient data for analysis. Required: {required_data}",
            error_code="INSUFFICIENT_DATA",
            context={"required_data": required_data, "available_data": available_data},
            **kwargs
        )


class AnalysisError(BusinessLogicError):
    """Raised when analysis fails."""
    
    def __init__(self, analysis_type: str, reason: str, **kwargs):
        super().__init__(
            message=f"Analysis failed for {analysis_type}: {reason}",
            error_code="ANALYSIS_ERROR", 
            context={"analysis_type": analysis_type, "reason": reason},
            **kwargs
        )


class DocumentParsingError(BusinessLogicError):
    """Raised when document parsing fails."""
    
    def __init__(self, document: str, reason: str, **kwargs):
        super().__init__(
            message=f"Failed to parse document '{document}': {reason}",
            error_code="DOCUMENT_PARSING_ERROR",
            context={"document": document, "reason": reason},
            **kwargs
        )


class CalculationError(BusinessLogicError):
    """Raised when financial calculations fail."""
    
    def __init__(self, formula: str, reason: str, **kwargs):
        super().__init__(
            message=f"Calculation failed for {formula}: {reason}",
            error_code="CALCULATION_ERROR",
            context={"formula": formula, "reason": reason},
            **kwargs
        )


class ReportGenerationError(BusinessLogicError):
    """Raised when report generation fails."""
    
    def __init__(self, template: str, reason: str, **kwargs):
        super().__init__(
            message=f"Report generation failed for template '{template}': {reason}",
            error_code="REPORT_GENERATION_ERROR",
            context={"template": template, "reason": reason},
            **kwargs
        )


# ===== Rate Limiting and Resource Errors =====

class ResourceError(MavikError):
    """Base class for resource-related errors."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code="RESOURCE_ERROR",
            **kwargs
        )


class RateLimitError(ResourceError):
    """Raised when rate limits are exceeded."""
    
    def __init__(self, limit: int, window: str, **kwargs):
        super().__init__(
            message=f"Rate limit exceeded: {limit} requests per {window}",
            error_code="RATE_LIMIT_EXCEEDED",
            context={"limit": limit, "window": window},
            **kwargs
        )


class BudgetExceededError(ResourceError):
    """Raised when cost budgets are exceeded."""
    
    def __init__(self, budget_type: str, limit: float, current: float, **kwargs):
        super().__init__(
            message=f"{budget_type} budget exceeded: ${current:.2f} > ${limit:.2f}",
            error_code="BUDGET_EXCEEDED",
            context={"budget_type": budget_type, "limit": limit, "current": current},
            **kwargs
        )


class ResourceUnavailableError(ResourceError):
    """Raised when a required resource is unavailable."""
    
    def __init__(self, resource_type: str, resource_id: str, **kwargs):
        super().__init__(
            message=f"{resource_type} resource unavailable: {resource_id}",
            error_code="RESOURCE_UNAVAILABLE",
            context={"resource_type": resource_type, "resource_id": resource_id},
            **kwargs
        )


# ===== Utility Functions =====

def format_error_response(error: Exception) -> dict:
    """Format any exception as a standardized error response.
    
    Args:
        error: Exception to format
        
    Returns:
        Dict containing formatted error response
    """
    if isinstance(error, MavikError):
        return {
            "success": False,
            "error_code": error.error_code,
            "error_message": error.message,
            "error_context": error.context,
        }
    else:
        return {
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "error_message": str(error),
            "error_context": {"exception_type": type(error).__name__},
        }