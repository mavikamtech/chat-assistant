"""Configuration and fixtures for Parser MCP server tests."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from datetime import datetime


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
    settings.parser_timeout_seconds = 30
    settings.aws_region = "us-east-1"
    settings.textract_max_pages = 3000
    return settings


@pytest.fixture
def sample_offering_memorandum_text():
    """Sample offering memorandum text content for testing."""
    return """
    PRIVATE & CONFIDENTIAL
    OFFERING MEMORANDUM
    
    $50,000,000
    300 HILLSBOROUGH STREET
    RALEIGH, NORTH CAROLINA
    
    INVESTMENT OPPORTUNITY
    
    EXECUTIVE SUMMARY
    
    Property Overview
    300 Hillsborough Street is a Class A office building located in downtown Raleigh, 
    North Carolina. The 12-story building contains approximately 150,000 square feet 
    of rentable space and was constructed in 1985 with major renovations completed in 2022.
    
    Investment Highlights
    • Prime downtown location with excellent accessibility
    • High-quality tenant roster with strong credit profiles  
    • Recent capital improvements including HVAC and elevator modernization
    • Below-market rents providing upside potential
    • Strong cash flow with projected 4% annual NOI growth
    
    Financial Summary
    Purchase Price: $50,000,000
    Price per SF: $333
    Going-In Cap Rate: 6.4%
    Year 1 Cash-on-Cash: 8.2%
    5-Year IRR: 12.8%
    
    PROPERTY DETAILS
    
    Location & Access
    The subject property is strategically positioned at the intersection of 
    Hillsborough Street and Fifth Avenue in downtown Raleigh. The location 
    provides excellent access to public transportation, major highways, and 
    the central business district.
    
    Building Specifications
    Year Built: 1985
    Renovation: 2022
    Total Building SF: 150,000
    Stories: 12
    Parking Ratio: 1.33/1,000 SF
    Elevators: 3 passenger elevators
    HVAC: Central system with zone controls
    
    TENANT PROFILE
    
    Major Tenants:
    
    Tenant Name           | Floor(s) | SF     | Lease Exp | Credit
    ---------------------|----------|--------|-----------|--------
    DataTech Solutions   | 8-10     | 25,000 | Dec 2029  | BBB+
    Morrison & Associates| 5-6      | 18,000 | Jun 2027  | A-
    Regional Bank        | 1        | 8,000  | Mar 2031  | AA-
    Various Small Tenants| Multiple | 60,000 | Various   | B+ Avg
    
    Occupancy: 92%
    WALT: 7.2 years
    Average Credit: BBB+
    
    MARKET ANALYSIS
    
    Submarket Performance
    The downtown Raleigh office market has demonstrated resilience with:
    • Class A average rent: $28.50/SF (subject at $26.75/SF)
    • Market vacancy: 12.3% (subject at 8.0%)
    • Average cap rates: 6.8% (subject at 6.4%)
    
    Comparable Sales
    Recent transactions in the submarket:
    • 123 Main Street: $340/SF, 6.2% cap rate
    • 456 Capital Blvd: $285/SF, 7.1% cap rate  
    • 789 Business Way: $315/SF, 6.5% cap rate
    
    FINANCIAL PROJECTIONS
    
    Operating Performance (Year 1)
    Gross Rental Income: $4,012,500
    Less: Vacancy @ 5%: $(200,625)
    Effective Gross Income: $3,811,875
    Less: Operating Expenses: $(811,875)
    Net Operating Income: $3,000,000
    
    5-Year Projections
    Year 1 NOI: $3,000,000
    Year 2 NOI: $3,120,000 (4.0% growth)
    Year 3 NOI: $3,244,800 (4.0% growth)
    Year 4 NOI: $3,374,592 (4.0% growth)  
    Year 5 NOI: $3,509,576 (4.0% growth)
    
    INVESTMENT ANALYSIS
    
    Capitalization Structure
    Total Investment: $50,000,000
    Equity (25%): $12,500,000
    Debt (75%): $37,500,000
    Interest Rate: 5.5%
    Amortization: 25 years
    
    Cash Flow Analysis
    Year 1 Cash Flow: $656,000
    Year 2 Cash Flow: $724,800
    Year 3 Cash Flow: $797,952
    Year 4 Cash Flow: $875,669
    Year 5 Cash Flow: $958,296
    
    Returns Summary
    Cash-on-Cash Return (Year 1): 8.2%
    5-Year IRR: 12.8%
    5-Year Equity Multiple: 1.67x
    
    RISK CONSIDERATIONS
    
    Key Risk Factors:
    • Interest rate sensitivity on refinancing
    • Tenant concentration (top 3 = 55% of income)
    • Capital expenditure requirements
    • Market competition for tenants
    • Economic conditions affecting occupancy
    
    Mitigation Strategies:
    • Diversified tenant base across industries
    • Conservative leverage at 75% LTV
    • Recent renovations reduce near-term capex
    • Strong market fundamentals in Raleigh
    • Professional property management
    
    CONCLUSION
    
    300 Hillsborough Street presents a compelling investment opportunity 
    combining stable cash flows, quality tenants, and value-add potential 
    through rent optimization. The property's prime location and recent 
    improvements position it well for continued strong performance.
    
    The projected returns of 8.2% cash-on-cash and 12.8% IRR reflect 
    the quality of the asset and strength of the Raleigh office market.
    
    CONFIDENTIALITY NOTICE
    This offering memorandum contains confidential and proprietary 
    information. Any reproduction or distribution without written 
    consent is strictly prohibited.
    """


@pytest.fixture
def sample_textract_blocks():
    """Comprehensive Textract blocks for testing complex documents."""
    return [
        # Page block
        {
            "Id": "page_001",
            "BlockType": "PAGE",
            "Page": 1,
            "Geometry": {
                "BoundingBox": {"Width": 1.0, "Height": 1.0, "Left": 0.0, "Top": 0.0}
            },
            "Relationships": [
                {"Type": "CHILD", "Ids": ["line_001", "line_002", "line_003", "table_001"]}
            ]
        },
        # Header line
        {
            "Id": "line_001",
            "BlockType": "LINE",
            "Text": "OFFERING MEMORANDUM",
            "Confidence": 99.8,
            "Page": 1,
            "Geometry": {
                "BoundingBox": {"Width": 0.6, "Height": 0.04, "Left": 0.2, "Top": 0.1}
            },
            "Relationships": [
                {"Type": "CHILD", "Ids": ["word_001", "word_002"]}
            ]
        },
        # Property name line  
        {
            "Id": "line_002",
            "BlockType": "LINE", 
            "Text": "300 HILLSBOROUGH STREET",
            "Confidence": 98.5,
            "Page": 1,
            "Geometry": {
                "BoundingBox": {"Width": 0.5, "Height": 0.03, "Left": 0.25, "Top": 0.15}
            },
            "Relationships": [
                {"Type": "CHILD", "Ids": ["word_003", "word_004", "word_005"]}
            ]
        },
        # Investment amount line
        {
            "Id": "line_003",
            "BlockType": "LINE",
            "Text": "$50,000,000",
            "Confidence": 99.2,
            "Page": 1,
            "Geometry": {
                "BoundingBox": {"Width": 0.3, "Height": 0.03, "Left": 0.35, "Top": 0.2}
            },
            "Relationships": [
                {"Type": "CHILD", "Ids": ["word_006"]}
            ]
        },
        # Words for lines
        {
            "Id": "word_001",
            "BlockType": "WORD",
            "Text": "OFFERING",
            "Confidence": 99.9,
            "Page": 1
        },
        {
            "Id": "word_002", 
            "BlockType": "WORD",
            "Text": "MEMORANDUM",
            "Confidence": 99.7,
            "Page": 1
        },
        {
            "Id": "word_003",
            "BlockType": "WORD", 
            "Text": "300",
            "Confidence": 98.8,
            "Page": 1
        },
        {
            "Id": "word_004",
            "BlockType": "WORD",
            "Text": "HILLSBOROUGH", 
            "Confidence": 98.2,
            "Page": 1
        },
        {
            "Id": "word_005",
            "BlockType": "WORD",
            "Text": "STREET",
            "Confidence": 98.5,
            "Page": 1  
        },
        {
            "Id": "word_006",
            "BlockType": "WORD",
            "Text": "$50,000,000",
            "Confidence": 99.2,
            "Page": 1
        },
        # Table block
        {
            "Id": "table_001",
            "BlockType": "TABLE", 
            "Confidence": 95.5,
            "Page": 1,
            "Geometry": {
                "BoundingBox": {"Width": 0.8, "Height": 0.4, "Left": 0.1, "Top": 0.4}
            },
            "Relationships": [
                {"Type": "CHILD", "Ids": [
                    "cell_001", "cell_002", "cell_003", "cell_004",
                    "cell_005", "cell_006", "cell_007", "cell_008"
                ]}
            ]
        },
        # Table cells - Header row
        {
            "Id": "cell_001",
            "BlockType": "CELL",
            "RowIndex": 0,
            "ColumnIndex": 0,
            "RowSpan": 1,
            "ColumnSpan": 1,
            "Confidence": 96.0,
            "EntityTypes": ["COLUMN_HEADER"],
            "Relationships": [{"Type": "CHILD", "Ids": ["word_007"]}]
        },
        {
            "Id": "cell_002", 
            "BlockType": "CELL",
            "RowIndex": 0,
            "ColumnIndex": 1,
            "RowSpan": 1,
            "ColumnSpan": 1,
            "Confidence": 95.8,
            "EntityTypes": ["COLUMN_HEADER"],
            "Relationships": [{"Type": "CHILD", "Ids": ["word_008"]}]
        },
        {
            "Id": "cell_003",
            "BlockType": "CELL", 
            "RowIndex": 0,
            "ColumnIndex": 2,
            "RowSpan": 1,
            "ColumnSpan": 1,
            "Confidence": 96.2,
            "EntityTypes": ["COLUMN_HEADER"], 
            "Relationships": [{"Type": "CHILD", "Ids": ["word_009"]}]
        },
        {
            "Id": "cell_004",
            "BlockType": "CELL",
            "RowIndex": 0, 
            "ColumnIndex": 3,
            "RowSpan": 1,
            "ColumnSpan": 1,
            "Confidence": 95.5,
            "EntityTypes": ["COLUMN_HEADER"],
            "Relationships": [{"Type": "CHILD", "Ids": ["word_010"]}]
        },
        # Table cells - Data row
        {
            "Id": "cell_005",
            "BlockType": "CELL",
            "RowIndex": 1,
            "ColumnIndex": 0,
            "RowSpan": 1, 
            "ColumnSpan": 1,
            "Confidence": 97.1,
            "Relationships": [{"Type": "CHILD", "Ids": ["word_011", "word_012"]}]
        },
        {
            "Id": "cell_006",
            "BlockType": "CELL",
            "RowIndex": 1,
            "ColumnIndex": 1,
            "RowSpan": 1,
            "ColumnSpan": 1, 
            "Confidence": 96.8,
            "Relationships": [{"Type": "CHILD", "Ids": ["word_013"]}]
        },
        {
            "Id": "cell_007",
            "BlockType": "CELL",
            "RowIndex": 1,
            "ColumnIndex": 2,
            "RowSpan": 1,
            "ColumnSpan": 1,
            "Confidence": 97.3,
            "Relationships": [{"Type": "CHILD", "Ids": ["word_014"]}]
        },
        {
            "Id": "cell_008",
            "BlockType": "CELL",
            "RowIndex": 1,
            "ColumnIndex": 3, 
            "RowSpan": 1,
            "ColumnSpan": 1,
            "Confidence": 96.9,
            "Relationships": [{"Type": "CHILD", "Ids": ["word_015"]}]
        },
        # Table cell words
        {
            "Id": "word_007",
            "BlockType": "WORD",
            "Text": "Tenant",
            "Confidence": 96.0
        },
        {
            "Id": "word_008",
            "BlockType": "WORD", 
            "Text": "SF",
            "Confidence": 95.8
        },
        {
            "Id": "word_009",
            "BlockType": "WORD",
            "Text": "Lease",
            "Confidence": 96.2
        },
        {
            "Id": "word_010", 
            "BlockType": "WORD",
            "Text": "Credit",
            "Confidence": 95.5
        },
        {
            "Id": "word_011",
            "BlockType": "WORD",
            "Text": "DataTech", 
            "Confidence": 97.1
        },
        {
            "Id": "word_012",
            "BlockType": "WORD",
            "Text": "Solutions",
            "Confidence": 96.8
        },
        {
            "Id": "word_013",
            "BlockType": "WORD",
            "Text": "25,000",
            "Confidence": 96.8
        },
        {
            "Id": "word_014",
            "BlockType": "WORD", 
            "Text": "2029",
            "Confidence": 97.3
        },
        {
            "Id": "word_015",
            "BlockType": "WORD",
            "Text": "BBB+",
            "Confidence": 96.9
        },
        # Key-value pairs for forms
        {
            "Id": "kv_key_001",
            "BlockType": "KEY_VALUE_SET",
            "EntityTypes": ["KEY"],
            "Confidence": 94.5,
            "Page": 1,
            "Relationships": [
                {"Type": "VALUE", "Ids": ["kv_value_001"]},
                {"Type": "CHILD", "Ids": ["word_016", "word_017"]}
            ]
        },
        {
            "Id": "kv_value_001", 
            "BlockType": "KEY_VALUE_SET",
            "EntityTypes": ["VALUE"],
            "Confidence": 95.2,
            "Page": 1,
            "Relationships": [
                {"Type": "CHILD", "Ids": ["word_018"]}
            ]
        },
        {
            "Id": "word_016",
            "BlockType": "WORD", 
            "Text": "Purchase",
            "Confidence": 94.8
        },
        {
            "Id": "word_017",
            "BlockType": "WORD",
            "Text": "Price:",
            "Confidence": 94.2
        },
        {
            "Id": "word_018",
            "BlockType": "WORD",
            "Text": "$50,000,000", 
            "Confidence": 95.2
        }
    ]


@pytest.fixture
def mock_multipage_textract_response():
    """Mock Textract response for multi-page document."""
    return {
        "JobStatus": "SUCCEEDED",
        "Blocks": [
            # Page 1
            {
                "Id": "page_1",
                "BlockType": "PAGE", 
                "Page": 1,
                "Relationships": [{"Type": "CHILD", "Ids": ["line_p1_1"]}]
            },
            {
                "Id": "line_p1_1",
                "BlockType": "LINE",
                "Text": "Page 1 Content",
                "Confidence": 99.0,
                "Page": 1,
                "Relationships": [{"Type": "CHILD", "Ids": ["word_p1_1"]}]
            },
            {
                "Id": "word_p1_1", 
                "BlockType": "WORD",
                "Text": "Content",
                "Confidence": 99.0,
                "Page": 1
            },
            # Page 2  
            {
                "Id": "page_2",
                "BlockType": "PAGE",
                "Page": 2,
                "Relationships": [{"Type": "CHILD", "Ids": ["line_p2_1"]}]
            },
            {
                "Id": "line_p2_1",
                "BlockType": "LINE",
                "Text": "Page 2 Content", 
                "Confidence": 98.5,
                "Page": 2,
                "Relationships": [{"Type": "CHILD", "Ids": ["word_p2_1"]}]
            },
            {
                "Id": "word_p2_1",
                "BlockType": "WORD",
                "Text": "Content",
                "Confidence": 98.5, 
                "Page": 2
            }
        ]
    }


@pytest.fixture
def mock_s3_document_metadata():
    """Mock S3 document metadata."""
    return {
        "ContentLength": 2048576,  # ~2MB
        "ContentType": "application/pdf",
        "LastModified": datetime(2024, 1, 15, 10, 30, 0),
        "Metadata": {
            "document-type": "offering-memorandum",
            "deal-id": "hillsborough-300", 
            "confidentiality": "private"
        }
    }


@pytest.fixture
def mock_parser_request():
    """Mock parser request for testing."""
    from mavik_common.models import ParserRequest
    
    return ParserRequest(
        document_source="s3://mavik-docs/deals/300-hillsborough-om.pdf",
        document_id="hillsborough_300_om",
        options={
            "extract_tables": True,
            "extract_forms": True,
            "extract_signatures": False
        }
    )


@pytest.fixture  
def mock_parser_upload_request():
    """Mock parser upload request for testing."""
    from mavik_common.models import ParserUploadRequest
    
    return ParserUploadRequest(
        s3_bucket="mavik-documents",
        s3_key="uploads/temp/document.pdf", 
        document_id="temp_upload_123",
        filename="investment-memo.pdf",
        options={
            "extract_tables": True,
            "extract_forms": False
        }
    )


@pytest.fixture
def expected_parsed_document():
    """Expected parsed document structure for testing."""
    from mavik_common.models import (
        ParsedDocument, DocumentMetadata, DocumentPage, 
        DocumentElement, BoundingBox
    )
    from datetime import datetime
    
    return ParsedDocument(
        metadata=DocumentMetadata(
            document_id="test_document",
            source_location="s3://test-bucket/test-doc.pdf",
            processing_timestamp=datetime(2024, 1, 15, 10, 30, 0),
            total_pages=1,
            content_type="application/pdf",
            file_size=1024000,
            parser_version="textract-1.0"
        ),
        pages=[
            DocumentPage(
                page_number=1,
                elements=[
                    DocumentElement(
                        element_type="line",
                        text="OFFERING MEMORANDUM", 
                        bounding_box=BoundingBox(
                            left=0.2, top=0.1, width=0.6, height=0.04
                        ),
                        confidence=99.8
                    )
                ],
                bounding_box=BoundingBox(
                    left=0.0, top=0.0, width=1.0, height=1.0
                ),
                width=1.0,
                height=1.0
            )
        ],
        tables=[],
        forms=[],
        full_text="OFFERING MEMORANDUM"
    )