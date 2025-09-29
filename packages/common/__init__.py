"""Common utilities and models for Mavik AI."""

# Export all models and errors for easy importing
from .errors import (
    # Base errors
    MavikError,
    format_error_response,
    
    # Configuration errors
    ConfigurationError,
    MissingEnvironmentVariableError,
    InvalidConfigurationValueError,
    
    # Auth errors
    AuthenticationError,
    AuthorizationError,
    JWTValidationError,
    MNPIAccessDeniedError,
    
    # Validation errors
    ValidationError,
    SchemaValidationError,
    RequiredFieldError,
    
    # AWS service errors
    AWSServiceError,
    BedrockError,
    BedrockModelNotFoundError,
    BedrockTokenLimitError,
    S3Error,
    S3ObjectNotFoundError,
    DynamoDBError,
    OpenSearchError,
    RDSError,
    TextractError,
    
    # MCP protocol errors
    MCPError,
    MCPConnectionError,
    MCPTimeoutError,
    MCPProtocolError,
    MCPToolUnavailableError,
    
    # Business logic errors
    BusinessLogicError,
    DealNotFoundError,
    InsufficientDataError,
    AnalysisError,
    DocumentParsingError,
    CalculationError,
    ReportGenerationError,
    
    # Resource errors
    ResourceError,
    RateLimitError,
    BudgetExceededError,
    ResourceUnavailableError,
)

from .models import (
    # Base models
    BaseRequest,
    BaseResponse,
    
    # Enums
    AssetType,
    GeographicRegion,
    MNPIClassification,
    CalculationFormula,
    
    # RAG models
    RAGSearchRequest,
    RAGChunk,
    RAGSearchResponse,
    
    # Parser models
    ParserExtractRequest,
    ParserTable,
    ParserTextSection,
    ParserExtractResponse,
    
    # FinDB models
    FinDBQueryRequest,
    FinDBMetrics,
    FinDBTenant,
    FinDBDebtTerms,
    FinDBQueryResponse,
    
    # Web search models
    WebSearchRequest,
    WebSearchResult,
    WebSearchResponse,
    
    # Calculator models
    CalcComputeRequest,
    CalcExplanation,
    CalcComputeResponse,
    
    # Report models
    ReportSection,
    ReportCreateRequest,
    ReportCreateResponse,
    
    # Analysis models
    AnalysisMetadata,
    AnalysisSection,
    StructuredAnalysis,
)
