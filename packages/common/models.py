"""Common Pydantic models for Mavik AI system.

This module contains all the data models used across the MCP tools and orchestrator.
All models follow the JSON schema patterns and include comprehensive validation.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, validator


# ===== Base Models =====

class BaseRequest(BaseModel):
    """Base class for all MCP tool requests."""
    
    request_id: Optional[str] = Field(None, description="Unique request identifier")
    timestamp: Optional[datetime] = Field(default_factory=datetime.utcnow)
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        validate_assignment = True
        extra = "forbid"


class BaseResponse(BaseModel):
    """Base class for all MCP tool responses."""
    
    success: bool = Field(True, description="Whether the request was successful")
    error_code: Optional[str] = Field(None, description="Error code if request failed")
    error_message: Optional[str] = Field(None, description="Human-readable error message")
    execution_time_ms: Optional[int] = Field(None, description="Execution time in milliseconds")
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        validate_assignment = True
        extra = "forbid"


# ===== Enums =====

class AssetType(str, Enum):
    """Commercial real estate asset types."""
    MULTIFAMILY = "multifamily"
    OFFICE = "office"
    RETAIL = "retail"
    INDUSTRIAL = "industrial"
    MIXED_USE = "mixed_use"
    HOSPITALITY = "hospitality"
    HEALTHCARE = "healthcare"
    STUDENT_HOUSING = "student_housing"
    SENIOR_HOUSING = "senior_housing"
    SELF_STORAGE = "self_storage"


class GeographicRegion(str, Enum):
    """Geographic regions for filtering."""
    SOUTHEAST = "southeast"
    NORTHEAST = "northeast"
    MIDWEST = "midwest"
    SOUTHWEST = "southwest"
    WEST = "west"
    MOUNTAIN = "mountain"
    PACIFIC = "pacific"


class MNPIClassification(str, Enum):
    """Material Non-Public Information classification levels."""
    PUBLIC = "public"
    INTERNAL = "internal" 
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class CalculationFormula(str, Enum):
    """Financial calculation formulas supported."""
    IRR = "irr"
    NPV = "npv"
    DSCR = "dscr"
    DEBT_YIELD = "debt_yield"
    LTV = "ltv"
    LTC = "ltc"
    CAP_RATE = "cap_rate"
    CASH_ON_CASH = "cash_on_cash"
    MOIC = "moic"


# ===== RAG Tool Models =====

class RAGSearchRequest(BaseRequest):
    """Request model for RAG search tool."""
    
    query: str = Field(..., min_length=1, max_length=1000, description="Search query")
    filters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Search filters (dealId, geo, asset, after, mnpi_clearance)"
    )
    top_k: int = Field(5, ge=1, le=50, description="Number of results to return")
    include_embeddings: bool = Field(False, description="Include embedding vectors in response")
    rerank: bool = Field(True, description="Apply LLM-based reranking to results")
    
    @validator('filters')
    def validate_filters(cls, v):
        """Validate filter parameters."""
        allowed_keys = {'dealId', 'geo', 'asset', 'after', 'mnpi_clearance', 'sponsor', 'property_type'}
        if not set(v.keys()).issubset(allowed_keys):
            raise ValueError(f"Invalid filter keys. Allowed: {allowed_keys}")
        return v


class RAGChunk(BaseModel):
    """Individual search result chunk."""
    
    text: str = Field(..., description="Text content of the chunk")
    citation_id: str = Field(..., description="Unique citation identifier")
    score: float = Field(..., ge=0.0, le=1.0, description="Relevance score")
    page: Optional[int] = Field(None, ge=1, description="Source document page number")
    eff_date: Optional[datetime] = Field(None, description="Effective date of the content")
    source_url: Optional[str] = Field(None, description="Source document URL or identifier")
    asset_type: Optional[AssetType] = Field(None, description="Asset type classification")
    geo_region: Optional[GeographicRegion] = Field(None, description="Geographic region")
    mnpi_level: Optional[MNPIClassification] = Field(None, description="MNPI classification")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Extraction confidence score")


class RAGSearchResponse(BaseResponse):
    """Response model for RAG search tool."""
    
    chunks: List[RAGChunk] = Field(default_factory=list, description="Search result chunks")
    total_matches: int = Field(0, ge=0, description="Total number of matches found")
    query_embedding: Optional[List[float]] = Field(None, description="Query embedding vector")
    search_metadata: Dict[str, Any] = Field(default_factory=dict, description="Search metadata")


# ===== Parser Tool Models =====

class ParserExtractRequest(BaseRequest):
    """Request model for document parser tool."""
    
    s3_uri: str = Field(..., description="S3 URI of document to parse")
    deal_id: str = Field(..., description="Deal identifier for context")
    force_reprocess: bool = Field(False, description="Force reprocessing if already parsed")
    extract_tables: bool = Field(True, description="Extract structured tables")
    extract_text: bool = Field(True, description="Extract text sections")
    ocr_config: Dict[str, Any] = Field(default_factory=dict, description="OCR configuration")


class ParserTable(BaseModel):
    """Structured table extracted from document."""
    
    name: str = Field(..., description="Table identifier (rent_roll, expense_breakdown, etc.)")
    headers: List[str] = Field(default_factory=list, description="Table column headers")
    rows: List[Dict[str, Any]] = Field(default_factory=list, description="Table data rows")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Extraction confidence")
    page: Optional[int] = Field(None, description="Source page number")
    bounding_box: Optional[Dict[str, float]] = Field(None, description="Table bounding box coordinates")


class ParserTextSection(BaseModel):
    """Text section extracted from document."""
    
    title: str = Field(..., description="Section title or heading")
    content: str = Field(..., description="Section text content") 
    page: Optional[int] = Field(None, description="Source page number")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Extraction confidence")
    section_type: Optional[str] = Field(None, description="Classified section type")


class ParserExtractResponse(BaseResponse):
    """Response model for document parser tool."""
    
    tables: Dict[str, List[ParserTable]] = Field(
        default_factory=dict,
        description="Extracted tables by category"
    )
    text_sections: List[ParserTextSection] = Field(
        default_factory=list,
        description="Extracted text sections"
    )
    overall_confidence: float = Field(1.0, ge=0.0, le=1.0, description="Overall extraction confidence")
    warnings: List[str] = Field(default_factory=list, description="Extraction warnings")
    document_metadata: Dict[str, Any] = Field(default_factory=dict, description="Document metadata")


# ===== FinDB Tool Models =====

class FinDBQueryRequest(BaseRequest):
    """Request model for financial database queries."""
    
    deal_id: Optional[str] = Field(None, description="Specific deal ID to query")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Query filters")
    include_metrics: bool = Field(True, description="Include financial metrics")
    include_tenants: bool = Field(False, description="Include tenant information")
    include_debt_terms: bool = Field(False, description="Include debt terms")
    mnpi_clearance: MNPIClassification = Field(
        MNPIClassification.PUBLIC,
        description="MNPI clearance level for data access"
    )


class FinDBMetrics(BaseModel):
    """Financial metrics from database."""
    
    # Coverage ratios
    dscr: Optional[float] = Field(None, ge=0, description="Debt Service Coverage Ratio")
    interest_coverage: Optional[float] = Field(None, ge=0, description="Interest Coverage Ratio")
    
    # Leverage ratios  
    ltv: Optional[float] = Field(None, ge=0, le=1, description="Loan-to-Value ratio")
    ltc: Optional[float] = Field(None, ge=0, le=1, description="Loan-to-Cost ratio")
    debt_yield: Optional[float] = Field(None, ge=0, description="Debt yield percentage")
    
    # Return metrics
    irr_equity: Optional[float] = Field(None, description="Equity IRR percentage")
    irr_project: Optional[float] = Field(None, description="Project IRR percentage")
    moic: Optional[float] = Field(None, ge=0, description="Multiple on Invested Capital")
    cash_on_cash: Optional[float] = Field(None, description="Cash-on-cash return")
    
    # Valuation metrics
    cap_rate: Optional[float] = Field(None, ge=0, description="Capitalization rate")
    exit_cap_rate: Optional[float] = Field(None, ge=0, description="Exit cap rate assumption")
    noi: Optional[Decimal] = Field(None, ge=0, description="Net Operating Income")
    noi_psf: Optional[Decimal] = Field(None, ge=0, description="NOI per square foot")


class FinDBTenant(BaseModel):
    """Tenant information from database."""
    
    tenant_name: str = Field(..., description="Tenant name")
    lease_start: Optional[datetime] = Field(None, description="Lease start date")
    lease_end: Optional[datetime] = Field(None, description="Lease end date")
    monthly_rent: Optional[Decimal] = Field(None, ge=0, description="Monthly rent amount")
    square_footage: Optional[int] = Field(None, ge=0, description="Leased square footage")
    rent_per_sf: Optional[Decimal] = Field(None, ge=0, description="Rent per square foot")
    security_deposit: Optional[Decimal] = Field(None, ge=0, description="Security deposit amount")
    tenant_improvements: Optional[Decimal] = Field(None, ge=0, description="TI allowance")


class FinDBDebtTerms(BaseModel):
    """Debt terms from database."""
    
    loan_amount: Optional[Decimal] = Field(None, ge=0, description="Total loan amount")
    interest_rate: Optional[float] = Field(None, ge=0, description="Interest rate percentage")
    loan_term_months: Optional[int] = Field(None, ge=0, description="Loan term in months")
    amortization_months: Optional[int] = Field(None, ge=0, description="Amortization period")
    monthly_payment: Optional[Decimal] = Field(None, ge=0, description="Monthly debt service")
    prepayment_penalty: Optional[str] = Field(None, description="Prepayment penalty structure")
    recourse: Optional[bool] = Field(None, description="Whether loan is recourse")


class FinDBQueryResponse(BaseResponse):
    """Response model for financial database queries."""
    
    metrics: Optional[FinDBMetrics] = Field(None, description="Financial metrics")
    tenants: List[FinDBTenant] = Field(default_factory=list, description="Tenant information")
    debt_terms: Optional[FinDBDebtTerms] = Field(None, description="Debt terms")
    data_as_of: Optional[datetime] = Field(None, description="Data freshness timestamp")


# ===== Web Search Tool Models =====

class WebSearchRequest(BaseRequest):
    """Request model for web search tool."""
    
    queries: List[str] = Field(
        ..., 
        min_items=1, 
        max_items=10,
        description="Search query strings"
    )
    allowlist_group: str = Field(..., description="Domain allowlist group to use")
    max_results_per_query: int = Field(5, ge=1, le=20, description="Max results per query")
    include_content: bool = Field(True, description="Include page content in results")
    
    @validator('queries')
    def validate_queries(cls, v):
        """Validate query strings."""
        for query in v:
            if not query.strip():
                raise ValueError("Query strings cannot be empty")
            if len(query) > 500:
                raise ValueError("Query strings must be under 500 characters")
        return v


class WebSearchResult(BaseModel):
    """Individual web search result."""
    
    title: str = Field(..., description="Page title")
    url: str = Field(..., description="Page URL")
    snippet: str = Field(..., description="Page content snippet")
    source: str = Field(..., description="Source domain")
    cred_score: float = Field(0.5, ge=0.0, le=1.0, description="Credibility score")
    publish_date: Optional[datetime] = Field(None, description="Content publish date")
    content: Optional[str] = Field(None, description="Full page content")
    cache_hit: bool = Field(False, description="Whether result was cached")


class WebSearchResponse(BaseResponse):
    """Response model for web search tool."""
    
    results: List[WebSearchResult] = Field(default_factory=list, description="Search results")
    total_results: int = Field(0, ge=0, description="Total results across all queries")
    cache_hits: int = Field(0, ge=0, description="Number of cache hits")
    queries_processed: int = Field(0, ge=0, description="Number of queries processed")


# ===== Calculator Tool Models =====

class CalcComputeRequest(BaseRequest):
    """Request model for financial calculations."""
    
    formula: CalculationFormula = Field(..., description="Calculation formula to use")
    inputs: Dict[str, Union[float, int, List[float]]] = Field(
        ...,
        description="Calculation inputs as key-value pairs"
    )
    precision: int = Field(4, ge=2, le=10, description="Decimal precision for results")
    
    @validator('inputs')
    def validate_inputs(cls, v, values):
        """Validate inputs based on formula type."""
        formula = values.get('formula')
        
        if formula == CalculationFormula.IRR:
            if 'cash_flows' not in v:
                raise ValueError("IRR calculation requires 'cash_flows' input")
            if not isinstance(v['cash_flows'], list):
                raise ValueError("'cash_flows' must be a list of numbers")
                
        elif formula == CalculationFormula.NPV:
            required = {'cash_flows', 'discount_rate'}
            if not required.issubset(v.keys()):
                raise ValueError(f"NPV calculation requires inputs: {required}")
                
        elif formula == CalculationFormula.DSCR:
            required = {'net_operating_income', 'debt_service'}
            if not required.issubset(v.keys()):
                raise ValueError(f"DSCR calculation requires inputs: {required}")
                
        return v


class CalcExplanation(BaseModel):
    """Calculation explanation and methodology."""
    
    formula_name: str = Field(..., description="Calculation formula name")
    inputs_used: Dict[str, Union[float, int, List[float]]] = Field(
        ...,
        description="Actual inputs used in calculation"
    )
    methodology: str = Field(..., description="Calculation methodology explanation")
    assumptions: List[str] = Field(default_factory=list, description="Calculation assumptions")
    limitations: List[str] = Field(default_factory=list, description="Result limitations")


class CalcComputeResponse(BaseResponse):
    """Response model for financial calculations."""
    
    value: float = Field(..., description="Calculated result value")
    formatted_value: str = Field(..., description="Human-readable formatted result")
    explanation: CalcExplanation = Field(..., description="Calculation explanation")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Result confidence score")


# ===== Report Tool Models =====

class ReportSection(BaseModel):
    """Individual report section."""
    
    title: str = Field(..., description="Section title")
    content: str = Field(..., description="Section content")
    order: int = Field(..., ge=0, description="Section ordering")
    subsections: List["ReportSection"] = Field(default_factory=list, description="Nested subsections")


class ReportCreateRequest(BaseRequest):
    """Request model for report generation."""
    
    structured_analysis: Dict[str, Any] = Field(..., description="Analysis data to include")
    schema_version: str = Field("mavik.analysis.v1", description="Analysis schema version")
    template_type: str = Field("standard", description="Report template to use")
    include_citations: bool = Field(True, description="Include citation references")
    include_charts: bool = Field(True, description="Include data visualizations")
    format: str = Field("docx", description="Output format")
    
    @validator('structured_analysis')
    def validate_analysis_structure(cls, v):
        """Validate analysis structure."""
        required_fields = {'deal_id', 'analysis_type', 'timestamp', 'sections'}
        if not required_fields.issubset(v.keys()):
            raise ValueError(f"Analysis must contain: {required_fields}")
        return v


class ReportCreateResponse(BaseResponse):
    """Response model for report generation."""
    
    s3_presigned_url: str = Field(..., description="S3 presigned URL for download")
    report_version: str = Field(..., description="Generated report version")
    file_size_bytes: int = Field(..., ge=0, description="Generated file size")
    expiry_time: datetime = Field(..., description="URL expiry timestamp")
    pages_generated: int = Field(..., ge=1, description="Number of pages in report")


# ===== Analysis Schema Models =====

class AnalysisMetadata(BaseModel):
    """Metadata for analysis results."""
    
    schema_version: str = Field("mavik.analysis.v1", description="Schema version")
    deal_id: str = Field(..., description="Deal identifier")
    analysis_type: str = Field(..., description="Type of analysis performed")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Analysis timestamp")
    analyst_agent: str = Field(..., description="Agent that performed analysis")
    confidence_score: float = Field(1.0, ge=0.0, le=1.0, description="Overall confidence")
    

class AnalysisSection(BaseModel):
    """Individual analysis section."""
    
    title: str = Field(..., description="Section title")
    content: str = Field(..., description="Section analysis content")
    citations: List[str] = Field(default_factory=list, description="Citation references")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Section confidence score")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Quantitative metrics")
    

class StructuredAnalysis(BaseModel):
    """Complete structured analysis result."""
    
    metadata: AnalysisMetadata = Field(..., description="Analysis metadata")
    sections: Dict[str, AnalysisSection] = Field(..., description="Analysis sections")
    summary: str = Field(..., description="Executive summary")
    recommendation: str = Field(..., description="Investment recommendation")
    risk_factors: List[str] = Field(default_factory=list, description="Identified risk factors")
    key_metrics: Dict[str, float] = Field(default_factory=dict, description="Key financial metrics")


# Update forward references
ReportSection.model_rebuild()