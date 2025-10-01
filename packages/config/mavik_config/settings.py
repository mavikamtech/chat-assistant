"""Pydantic settings for environment-based configuration."""

import os
from typing import Dict, List, Optional
from functools import lru_cache

from pydantic import Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from mavik_common.errors import (
    ConfigurationError,
    MissingEnvironmentVariableError,
    InvalidConfigurationValueError,
)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = Field(default="Mavik AI", description="Application name")
    debug: bool = Field(default=False, description="Debug mode")
    log_level: str = Field(default="INFO", description="Logging level")
    environment: str = Field(default="development", description="Environment (development, staging, production)")

    # AWS Configuration
    aws_region: str = Field(default="us-east-1", description="AWS region")
    aws_access_key_id: Optional[str] = Field(default=None, description="AWS access key ID")
    aws_secret_access_key: Optional[str] = Field(default=None, description="AWS secret access key")

    # AWS Bedrock
    bedrock_region: str = Field(default="us-east-1", description="Bedrock region")
    bedrock_model_default: str = Field(
        default="anthropic.claude-3-5-haiku-20241022-v1:0",
        description="Default Bedrock model for fast operations"
    )
    bedrock_model_upgrade: str = Field(
        default="anthropic.claude-3-sonnet-20240229-v1:0",
        description="Upgrade Bedrock model for complex operations"
    )
    bedrock_embedding_model: str = Field(
        default="amazon.titan-embed-text-v2:0",
        description="Embedding model for vector operations"
    )

    # S3 Configuration
    s3_bucket_documents: str = Field(..., description="S3 bucket for document storage")
    s3_bucket_reports: str = Field(..., description="S3 bucket for report storage")
    s3_bucket_temp: str = Field(..., description="S3 bucket for temporary files")

    # DynamoDB Configuration
    dynamodb_table_checkpoints: str = Field(
        default="mavik-langgraph-checkpoints",
        description="DynamoDB table for LangGraph checkpoints"
    )
    dynamodb_table_sessions: str = Field(
        default="mavik-user-sessions",
        description="DynamoDB table for user sessions"
    )

    # RDS Configuration
    rds_cluster_endpoint: Optional[str] = Field(default=None, description="RDS cluster endpoint")
    rds_database_name: str = Field(default="mavik_findb", description="RDS database name")
    rds_username: Optional[str] = Field(default=None, description="RDS username")
    rds_password: Optional[str] = Field(default=None, description="RDS password")
    rds_use_iam_auth: bool = Field(default=True, description="Use IAM authentication for RDS")

    # OpenSearch Configuration
    opensearch_domain_endpoint: Optional[str] = Field(default=None, description="OpenSearch domain endpoint")
    opensearch_index_documents: str = Field(
        default="mavik-documents",
        description="OpenSearch index for documents"
    )

    # Azure AD Authentication
    azure_ad_tenant_id: str = Field(..., description="Azure AD tenant ID")
    azure_ad_client_id: str = Field(..., description="Azure AD client ID")
    azure_ad_client_secret: str = Field(..., description="Azure AD client secret")
    jwt_secret_key: str = Field(..., description="JWT signing key")
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_expiration_hours: int = Field(default=24, description="JWT expiration in hours")

    # MNPI Configuration
    mnpi_enforcement_enabled: bool = Field(default=True, description="Enable MNPI access controls")
    mnpi_default_classification: str = Field(default="public", description="Default MNPI classification")
    mnpi_admin_roles: List[str] = Field(
        default=["admin", "compliance_officer"],
        description="Roles with MNPI admin access"
    )

    # MCP Tool Timeouts (milliseconds)
    mcp_timeout_rag: int = Field(default=800, description="RAG tool timeout")
    mcp_timeout_findb: int = Field(default=200, description="FinDB tool timeout")
    mcp_timeout_web: int = Field(default=1500, description="Web search tool timeout")
    mcp_timeout_calc: int = Field(default=150, description="Calculator tool timeout")
    mcp_timeout_parser: int = Field(default=30000, description="Parser tool timeout")
    mcp_timeout_report: int = Field(default=1500, description="Report tool timeout")

    # MCP Server Configuration
    mcp_server_host: str = Field(default="0.0.0.0", description="MCP server host")
    mcp_server_port_rag: int = Field(default=8001, description="RAG server port")
    mcp_server_port_findb: int = Field(default=8002, description="FinDB server port")
    mcp_server_port_web: int = Field(default=8003, description="Web server port")
    mcp_server_port_calc: int = Field(default=8004, description="Calculator server port")
    mcp_server_port_parser: int = Field(default=8005, description="Parser server port")
    mcp_server_port_report: int = Field(default=8006, description="Report server port")

    # MCP Server WebSocket Timeout Configuration
    rag_timeout_seconds: int = Field(default=60, description="RAG server WebSocket timeout in seconds")
    parser_timeout_seconds: int = Field(default=60, description="Parser server WebSocket timeout in seconds")
    findb_timeout_seconds: int = Field(default=60, description="FinDB server WebSocket timeout in seconds")

    # Rate Limiting
    rate_limit_requests_per_minute: int = Field(default=60, description="Rate limit per minute")
    rate_limit_budget_dollars_per_hour: float = Field(default=10.0, description="Budget limit per hour")

    # Circuit Breaker Configuration
    circuit_breaker_failure_threshold: int = Field(default=5, description="Circuit breaker failure threshold")
    circuit_breaker_recovery_timeout: int = Field(default=60, description="Circuit breaker recovery timeout")
    circuit_breaker_expected_exception: str = Field(
        default="Exception",
        description="Expected exception for circuit breaker"
    )

    # Health Check Configuration
    health_check_interval: int = Field(default=30, description="Health check interval in seconds")
    health_check_timeout: int = Field(default=10, description="Health check timeout in seconds")

    # LangGraph Configuration
    langgraph_max_iterations: int = Field(default=20, description="Maximum LangGraph iterations")
    langgraph_recursion_limit: int = Field(default=50, description="LangGraph recursion limit")

    # Mock Mode (for testing/development)
    mock_mode: bool = Field(default=False, description="Enable mock mode for testing")
    mock_bedrock_responses: bool = Field(default=False, description="Mock Bedrock responses")
    mock_aws_services: bool = Field(default=False, description="Mock AWS services")

    @validator("environment")
    def validate_environment(cls, v):
        """Validate environment value."""
        valid_envs = ["development", "staging", "production"]
        if v not in valid_envs:
            raise InvalidConfigurationValueError(
                f"Invalid environment '{v}'. Must be one of: {valid_envs}"
            )
        return v

    @validator("log_level")
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise InvalidConfigurationValueError(
                f"Invalid log level '{v}'. Must be one of: {valid_levels}"
            )
        return v.upper()

    @validator("jwt_algorithm")
    def validate_jwt_algorithm(cls, v):
        """Validate JWT algorithm."""
        valid_algorithms = ["HS256", "HS384", "HS512", "RS256", "RS384", "RS512"]
        if v not in valid_algorithms:
            raise InvalidConfigurationValueError(
                f"Invalid JWT algorithm '{v}'. Must be one of: {valid_algorithms}"
            )
        return v

    @validator("mnpi_default_classification")
    def validate_mnpi_classification(cls, v):
        """Validate MNPI classification."""
        valid_classifications = ["public", "internal", "confidential", "restricted"]
        if v not in valid_classifications:
            raise InvalidConfigurationValueError(
                f"Invalid MNPI classification '{v}'. Must be one of: {valid_classifications}"
            )
        return v

    def validate_required_production_settings(self) -> None:
        """Validate that all required production settings are present."""
        if self.environment == "production":
            required_fields = [
                ("azure_ad_tenant_id", self.azure_ad_tenant_id),
                ("azure_ad_client_id", self.azure_ad_client_id),
                ("azure_ad_client_secret", self.azure_ad_client_secret),
                ("jwt_secret_key", self.jwt_secret_key),
                ("s3_bucket_documents", self.s3_bucket_documents),
                ("s3_bucket_reports", self.s3_bucket_reports),
                ("s3_bucket_temp", self.s3_bucket_temp),
            ]

            missing_fields = [
                field_name for field_name, field_value in required_fields
                if not field_value
            ]

            if missing_fields:
                raise MissingEnvironmentVariableError(
                    f"Missing required production settings: {missing_fields}"
                )

    def get_mcp_server_url(self, service: str) -> str:
        """Get MCP server WebSocket URL for a service.

        Args:
            service: Service name (rag, findb, web, calc, parser, report)

        Returns:
            WebSocket URL for the service

        Raises:
            ConfigurationError: If service is unknown
        """
        port_mapping = {
            "rag": self.mcp_server_port_rag,
            "findb": self.mcp_server_port_findb,
            "web": self.mcp_server_port_web,
            "calc": self.mcp_server_port_calc,
            "parser": self.mcp_server_port_parser,
            "report": self.mcp_server_port_report,
        }

        if service not in port_mapping:
            raise ConfigurationError(f"Unknown MCP service: {service}")

        port = port_mapping[service]
        return f"ws://{self.mcp_server_host}:{port}/ws"

    def get_mcp_timeout(self, service: str) -> int:
        """Get timeout for MCP service in milliseconds.

        Args:
            service: Service name

        Returns:
            Timeout in milliseconds
        """
        timeout_mapping = {
            "rag": self.mcp_timeout_rag,
            "findb": self.mcp_timeout_findb,
            "web": self.mcp_timeout_web,
            "calc": self.mcp_timeout_calc,
            "parser": self.mcp_timeout_parser,
            "report": self.mcp_timeout_report,
        }

        return timeout_mapping.get(service, 5000)  # Default 5 second timeout

    def get_database_url(self) -> Optional[str]:
        """Get database connection URL.

        Returns:
            Database URL if RDS is configured
        """
        if not self.rds_cluster_endpoint:
            return None

        if self.rds_use_iam_auth:
            # IAM auth doesn't use password in URL
            return f"postgresql://{self.rds_username or 'mavik_readonly'}@{self.rds_cluster_endpoint}/{self.rds_database_name}?sslmode=require"
        else:
            # Standard auth with password
            if not self.rds_password:
                return None
            return f"postgresql://{self.rds_username}:{self.rds_password}@{self.rds_cluster_endpoint}/{self.rds_database_name}?sslmode=require"

    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"

    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"

    def should_use_mock_services(self) -> bool:
        """Check if mock services should be used."""
        return self.mock_mode or (self.is_development() and self.mock_aws_services)


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings.

    Returns:
        Settings instance loaded from environment

    Raises:
        ConfigurationError: If configuration is invalid
    """
    try:
        settings = Settings()

        # Validate production settings if in production
        if settings.is_production():
            settings.validate_required_production_settings()

        return settings

    except Exception as e:
        if isinstance(e, (ConfigurationError, MissingEnvironmentVariableError, InvalidConfigurationValueError)):
            raise
        raise ConfigurationError(f"Failed to load settings: {e}")


def reload_settings() -> Settings:
    """Force reload of settings (clears cache).

    Returns:
        Fresh settings instance
    """
    get_settings.cache_clear()
    return get_settings()
