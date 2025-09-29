"""Configuration and fixtures for RAG MCP server tests."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_settings():
    """Mock application settings."""
    settings = Mock()
    settings.opensearch_index_name = "test-mavik-documents"
    settings.rag_timeout_seconds = 30
    settings.aws_region = "us-east-1"
    settings.bedrock_embedding_model = "amazon.titan-embed-text-v2:0"
    return settings


@pytest.fixture
def sample_document_content():
    """Sample document content for testing."""
    return """
    OFFERING MEMORANDUM
    
    CONFIDENTIAL
    
    $50,000,000
    300 Hillsborough Street
    Commercial Real Estate Investment Opportunity
    
    EXECUTIVE SUMMARY
    
    Property Overview:
    300 Hillsborough Street represents a premier commercial real estate investment opportunity 
    located in the heart of downtown. This Class A office building spans 150,000 square feet 
    across 12 floors and is currently 92% occupied by high-quality tenants.
    
    Key Investment Highlights:
    • Prime downtown location with excellent transportation access
    • Strong tenant roster with average lease term of 7.2 years
    • Recent renovations completed in 2022, including HVAC and elevator upgrades
    • Market-rate rents 15% below comparable properties, indicating upside potential
    • Net Operating Income of $3.2M with projected 4% annual growth
    
    Financial Summary:
    Purchase Price: $50,000,000
    Cap Rate: 6.4%
    Cash-on-Cash Return: 8.2% (Year 1)
    IRR Projection: 12.8% (5-year hold)
    
    PROPERTY DETAILS
    
    Location and Access:
    The property is strategically located at the intersection of Hillsborough Street and 
    Fifth Avenue, providing unparalleled access to public transportation, major highways, 
    and the central business district. The building is within walking distance of key 
    amenities including restaurants, retail, and parking facilities.
    
    Building Specifications:
    • Year Built: 1985, renovated 2022
    • Total Square Footage: 150,000 SF
    • Number of Floors: 12
    • Parking Spaces: 200 (1.33 spaces per 1,000 SF)
    • HVAC: Recently upgraded central system with zone controls
    • Elevators: 3 passenger elevators, recently modernized
    • Security: 24/7 on-site security and card access system
    
    TENANT PROFILE
    
    The building maintains a diverse tenant mix across professional services, technology, 
    and financial services sectors. Major tenants include:
    
    • DataTech Solutions (Floors 8-10): 25,000 SF, lease expires 2029
    • Morrison & Associates Law Firm (Floors 5-6): 18,000 SF, lease expires 2027
    • Regional Bank Branch (Floor 1): 8,000 SF, lease expires 2031
    • Various smaller tenants: 60,000 SF combined
    
    Average tenant credit rating: BBB+
    Weighted average lease term: 7.2 years
    Current occupancy rate: 92%
    
    MARKET ANALYSIS
    
    Submarket Overview:
    The downtown office market has shown resilience despite broader market challenges. 
    Key market metrics include:
    
    • Average Class A rent: $28.50 per SF (subject property at $26.75)
    • Vacancy rate: 12.3% (subject property at 8%)
    • Average transaction cap rate: 6.8% (subject property at 6.4%)
    
    Comparable Sales:
    Recent comparable transactions in the submarket range from $280 to $340 per SF, 
    supporting the current valuation of $333 per SF for 300 Hillsborough.
    
    FINANCIAL PROJECTIONS
    
    Year 1 Operating Performance:
    Gross Rental Income: $4,012,500
    Operating Expenses: $812,500
    Net Operating Income: $3,200,000
    
    5-Year Projections:
    The investment model assumes 3% annual rent growth and 2% annual expense growth, 
    resulting in 4% NOI growth. Key assumptions include:
    
    • Lease rollover: 15% annually
    • Capital expenditures: $1.50 per SF annually
    • Property management fee: 3% of gross income
    • Vacancy allowance: 5%
    
    INVESTMENT RETURNS
    
    Cash Flow Analysis (25% equity, 75% debt at 5.5%):
    Year 1 Cash Flow: $656,000
    Cash-on-Cash Return: 8.2%
    5-Year IRR: 12.8%
    5-Year Equity Multiple: 1.67x
    
    Exit Strategy:
    The investment thesis assumes a 5-year hold period with sale at a 7.0% cap rate, 
    reflecting market normalization and potential compression due to property improvements.
    
    RISK FACTORS
    
    Key risks to consider include:
    • Interest rate sensitivity on refinancing
    • Tenant concentration (top 3 tenants represent 55% of income)
    • Market rental rate competition
    • Capital expenditure requirements for aging building systems
    
    CONCLUSION
    
    300 Hillsborough Street presents an attractive investment opportunity with strong 
    fundamentals, quality tenants, and upside potential through rent optimization. 
    The combination of stable cash flow and growth potential supports the targeted 
    return metrics.
    
    This offering memorandum contains confidential and proprietary information. 
    Distribution is restricted to qualified investors only.
    """


@pytest.fixture
def sample_rag_chunks():
    """Sample RAG chunks for testing."""
    from mavik_common.models import RAGChunk
    from datetime import datetime
    
    return [
        RAGChunk(
            chunk_id="chunk_1",
            document_id="300_hillsborough_om",
            content="EXECUTIVE SUMMARY: 300 Hillsborough Street represents a premier commercial real estate investment opportunity located in the heart of downtown.",
            page_number=1,
            chunk_index=0,
            source_type="pdf",
            metadata={
                "title": "300 Hillsborough Street - Offering Memorandum",
                "deal_id": "hillsborough_300",
                "mnpi_classification": "confidential",
                "document_type": "offering_memorandum",
            },
            created_at=datetime.utcnow(),
        ),
        RAGChunk(
            chunk_id="chunk_2",
            document_id="300_hillsborough_om",
            content="Financial Summary: Purchase Price: $50,000,000, Cap Rate: 6.4%, Cash-on-Cash Return: 8.2% (Year 1), IRR Projection: 12.8% (5-year hold)",
            page_number=1,
            chunk_index=1,
            source_type="pdf",
            metadata={
                "title": "300 Hillsborough Street - Offering Memorandum", 
                "deal_id": "hillsborough_300",
                "mnpi_classification": "confidential",
                "document_type": "offering_memorandum",
            },
            created_at=datetime.utcnow(),
        ),
        RAGChunk(
            chunk_id="chunk_3", 
            document_id="300_hillsborough_om",
            content="Building Specifications: Year Built: 1985, renovated 2022, Total Square Footage: 150,000 SF, Number of Floors: 12, Parking Spaces: 200",
            page_number=2,
            chunk_index=2,
            source_type="pdf",
            metadata={
                "title": "300 Hillsborough Street - Offering Memorandum",
                "deal_id": "hillsborough_300", 
                "mnpi_classification": "confidential",
                "document_type": "offering_memorandum",
            },
            created_at=datetime.utcnow(),
        ),
    ]


@pytest.fixture
def mock_opensearch_response():
    """Mock OpenSearch search response."""
    return {
        "took": 25,
        "timed_out": False,
        "hits": {
            "total": {"value": 3, "relation": "eq"},
            "max_score": 0.95,
            "hits": [
                {
                    "_index": "test-mavik-documents",
                    "_id": "chunk_1",
                    "_score": 0.95,
                    "_source": {
                        "chunk_id": "chunk_1",
                        "document_id": "300_hillsborough_om",
                        "content": "EXECUTIVE SUMMARY: 300 Hillsborough Street represents a premier commercial real estate investment opportunity",
                        "page_number": 1,
                        "chunk_index": 0,
                        "source_type": "pdf",
                        "metadata": {
                            "title": "300 Hillsborough Street - Offering Memorandum",
                            "deal_id": "hillsborough_300",
                            "mnpi_classification": "confidential",
                        },
                        "content_embedding": [0.1] * 1536,
                        "indexed_at": "2024-01-15T10:30:00Z"
                    },
                    "highlight": {
                        "content": ["<em>commercial</em> real estate investment opportunity"]
                    }
                },
                {
                    "_index": "test-mavik-documents",
                    "_id": "chunk_2", 
                    "_score": 0.87,
                    "_source": {
                        "chunk_id": "chunk_2",
                        "document_id": "300_hillsborough_om",
                        "content": "Financial Summary: Purchase Price: $50,000,000, Cap Rate: 6.4%",
                        "page_number": 1,
                        "chunk_index": 1,
                        "source_type": "pdf",
                        "metadata": {
                            "title": "300 Hillsborough Street - Offering Memorandum",
                            "deal_id": "hillsborough_300", 
                            "mnpi_classification": "confidential",
                        },
                        "content_embedding": [0.2] * 1536,
                        "indexed_at": "2024-01-15T10:30:00Z"
                    }
                },
                {
                    "_index": "test-mavik-documents",
                    "_id": "chunk_3",
                    "_score": 0.72,
                    "_source": {
                        "chunk_id": "chunk_3",
                        "document_id": "300_hillsborough_om", 
                        "content": "Building Specifications: Total Square Footage: 150,000 SF, Number of Floors: 12",
                        "page_number": 2,
                        "chunk_index": 2,
                        "source_type": "pdf",
                        "metadata": {
                            "title": "300 Hillsborough Street - Offering Memorandum",
                            "deal_id": "hillsborough_300",
                            "mnpi_classification": "confidential",
                        },
                        "content_embedding": [0.3] * 1536,
                        "indexed_at": "2024-01-15T10:30:00Z"
                    }
                }
            ]
        }
    }


@pytest.fixture
def mock_bedrock_embeddings():
    """Mock Bedrock embeddings response."""
    # Return consistent 1536-dimensional vector for Titan Text Embeddings v2
    return [0.1 * i for i in range(1536)]


@pytest.fixture  
def mock_bulk_index_response():
    """Mock OpenSearch bulk index response."""
    return {
        "took": 150,
        "errors": False,
        "items": [
            {
                "index": {
                    "_index": "test-mavik-documents",
                    "_id": "chunk_1",
                    "_version": 1,
                    "result": "created",
                    "status": 201
                }
            },
            {
                "index": {
                    "_index": "test-mavik-documents", 
                    "_id": "chunk_2",
                    "_version": 1,
                    "result": "created",
                    "status": 201
                }
            },
            {
                "index": {
                    "_index": "test-mavik-documents",
                    "_id": "chunk_3", 
                    "_version": 1,
                    "result": "created",
                    "status": 201
                }
            }
        ]
    }


@pytest.fixture
def mock_textract_response():
    """Mock Textract document analysis response."""
    return {
        "Blocks": [
            {
                "Id": "block_1",
                "BlockType": "PAGE",
                "Page": 1,
                "Geometry": {"BoundingBox": {"Width": 1.0, "Height": 1.0, "Left": 0.0, "Top": 0.0}},
                "Relationships": [{"Type": "CHILD", "Ids": ["block_2", "block_3"]}]
            },
            {
                "Id": "block_2", 
                "BlockType": "LINE",
                "Text": "OFFERING MEMORANDUM",
                "Page": 1,
                "Geometry": {"BoundingBox": {"Width": 0.8, "Height": 0.05, "Left": 0.1, "Top": 0.1}},
                "Relationships": [{"Type": "CHILD", "Ids": ["block_4"]}]
            },
            {
                "Id": "block_3",
                "BlockType": "LINE", 
                "Text": "300 Hillsborough Street Commercial Real Estate Investment",
                "Page": 1,
                "Geometry": {"BoundingBox": {"Width": 0.9, "Height": 0.05, "Left": 0.05, "Top": 0.2}},
                "Relationships": [{"Type": "CHILD", "Ids": ["block_5"]}]
            },
            {
                "Id": "block_4",
                "BlockType": "WORD",
                "Text": "OFFERING",
                "Page": 1,
                "Geometry": {"BoundingBox": {"Width": 0.3, "Height": 0.05, "Left": 0.1, "Top": 0.1}}
            },
            {
                "Id": "block_5",
                "BlockType": "WORD", 
                "Text": "300",
                "Page": 1,
                "Geometry": {"BoundingBox": {"Width": 0.1, "Height": 0.05, "Left": 0.05, "Top": 0.2}}
            }
        ]
    }