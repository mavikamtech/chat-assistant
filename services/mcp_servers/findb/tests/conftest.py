"""
Test fixtures and configuration for FinDB MCP Server tests.

Provides comprehensive fixtures for mocking database connections,
sample data, and test configuration across all test modules.
"""

import asyncio
from datetime import datetime, timedelta  
from decimal import Decimal
from typing import List, Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

# Test data and fixtures
from packages.common.models import (
    PropertyData, CompData, MarketTrendData, FinancialMetrics
)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_settings():
    """Mock application settings."""
    settings = MagicMock()
    settings.rds_host = "localhost"
    settings.rds_port = 5432
    settings.rds_database = "test_findb"
    settings.rds_username = "test_user"
    settings.rds_password = MagicMock()
    settings.rds_password.get_secret_value.return_value = "test_password"
    settings.debug = True
    return settings


@pytest.fixture
def mock_async_session():
    """Mock async database session."""
    session = AsyncMock(spec=AsyncSession)
    
    # Setup default behaviors
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    
    return session


@pytest.fixture
def sample_properties():
    """Sample property data for testing."""
    return [
        PropertyData(
            property_id="prop_001",
            address="100 Main Street, New York, NY 10001",
            property_type="office",
            square_feet=75000,
            year_built=2015,
            latitude=40.7505,
            longitude=-73.9934,
            cap_rate=0.065,
            sale_date=datetime(2023, 8, 15),
            sale_price=Decimal("12500000")
        ),
        PropertyData(
            property_id="prop_002", 
            address="250 Broadway, New York, NY 10007",
            property_type="office",
            square_feet=120000,
            year_built=2018,
            latitude=40.7127,
            longitude=-74.0059,
            cap_rate=0.058,
            sale_date=datetime(2023, 9, 22),
            sale_price=Decimal("24000000")
        ),
        PropertyData(
            property_id="prop_003",
            address="500 Park Avenue, New York, NY 10022",
            property_type="office", 
            square_feet=95000,
            year_built=2020,
            latitude=40.7614,
            longitude=-73.9776,
            cap_rate=0.055,
            sale_date=datetime(2023, 7, 10),
            sale_price=Decimal("19000000")
        ),
        PropertyData(
            property_id="prop_004",
            address="1000 Second Avenue, Seattle, WA 98104",
            property_type="office",
            square_feet=85000,
            year_built=2017,
            latitude=47.6062,
            longitude=-122.3321,
            cap_rate=0.072,
            sale_date=datetime(2023, 6, 5),
            sale_price=Decimal("11900000")
        ),
        PropertyData(
            property_id="prop_005",
            address="300 California Street, San Francisco, CA 94104",
            property_type="office",
            square_feet=110000,
            year_built=2019,
            latitude=37.7749,
            longitude=-122.4194,
            cap_rate=0.048,
            sale_date=datetime(2023, 10, 12),
            sale_price=Decimal("27500000")
        )
    ]


@pytest.fixture
def sample_comparable_properties():
    """Sample comparable property data."""
    return [
        CompData(
            property_id="comp_001",
            address="125 Main Street, New York, NY 10001",
            property_type="office",
            square_feet=72000,
            year_built=2014,
            sale_price=Decimal("11800000"),
            sale_date=datetime(2023, 7, 20),
            cap_rate=0.067,
            noi=Decimal("790600"),
            price_per_sqft=Decimal("163.89"),
            occupancy_rate=0.93,
            distance_miles=0.3,
            similarity_score=92.5
        ),
        CompData(
            property_id="comp_002",
            address="150 Broadway, New York, NY 10038",
            property_type="office", 
            square_feet=78000,
            year_built=2016,
            sale_price=Decimal("13200000"),
            sale_date=datetime(2023, 6, 8),
            cap_rate=0.062,
            noi=Decimal("818400"),
            price_per_sqft=Decimal("169.23"),
            occupancy_rate=0.91,
            distance_miles=1.8,
            similarity_score=87.3
        ),
        CompData(
            property_id="comp_003",
            address="80 Pine Street, New York, NY 10005",
            property_type="office",
            square_feet=68000,
            year_built=2013,
            sale_price=Decimal("10900000"),
            sale_date=datetime(2023, 5, 15),
            cap_rate=0.069,
            noi=Decimal("752100"),
            price_per_sqft=Decimal("160.29"),
            occupancy_rate=0.89,
            distance_miles=2.1,
            similarity_score=84.7
        )
    ]


@pytest.fixture
def sample_market_trends():
    """Sample market trend data."""
    base_date = datetime(2023, 1, 1)
    return [
        MarketTrendData(
            period="2023-Q1",
            transaction_count=45,
            avg_price=Decimal("15200000"),
            avg_cap_rate=0.068,
            price_per_sqft=Decimal("155.50"),
            period_start=base_date,
            period_end=base_date + timedelta(days=90)
        ),
        MarketTrendData(
            period="2023-Q2", 
            transaction_count=52,
            avg_price=Decimal("15800000"),
            avg_cap_rate=0.065,
            price_per_sqft=Decimal("162.30"),
            period_start=base_date + timedelta(days=90),
            period_end=base_date + timedelta(days=180)
        ),
        MarketTrendData(
            period="2023-Q3",
            transaction_count=48,
            avg_price=Decimal("16500000"),
            avg_cap_rate=0.062,
            price_per_sqft=Decimal("168.75"),
            period_start=base_date + timedelta(days=180),
            period_end=base_date + timedelta(days=270)
        ),
        MarketTrendData(
            period="2023-Q4",
            transaction_count=41,
            avg_price=Decimal("17100000"),
            avg_cap_rate=0.059,
            price_per_sqft=Decimal("174.20"),
            period_start=base_date + timedelta(days=270),
            period_end=base_date + timedelta(days=365)
        )
    ]


@pytest.fixture
def sample_financial_metrics():
    """Sample financial metrics data.""" 
    return [
        FinancialMetrics(
            cap_rate=0.065,
            noi=Decimal("812500"),
            gross_income=Decimal("1200000"),
            operating_expenses=Decimal("387500"),
            occupancy_rate=0.92,
            debt_service_coverage=1.35,
            loan_to_value=0.75,
            price_per_sqft=Decimal("166.67")
        ),
        FinancialMetrics(
            cap_rate=0.058,
            noi=Decimal("1392000"),
            gross_income=Decimal("1980000"),
            operating_expenses=Decimal("588000"),
            occupancy_rate=0.94,
            debt_service_coverage=1.42,
            loan_to_value=0.70,
            price_per_sqft=Decimal("200.00")
        ),
        FinancialMetrics(
            cap_rate=0.072,
            noi=Decimal("856800"),
            gross_income=Decimal("1275000"),
            operating_expenses=Decimal("418200"),
            occupancy_rate=0.89,
            debt_service_coverage=1.28,
            loan_to_value=0.80,
            price_per_sqft=Decimal("140.00")
        )
    ]


@pytest.fixture  
def mock_database_responses():
    """Mock database query responses."""
    return {
        "comparable_properties": [
            {
                "property_id": "comp_001",
                "address": "125 Main Street, New York, NY 10001",
                "property_type": "office",
                "square_feet": 72000,
                "year_built": 2014,
                "sale_price": 11800000,
                "sale_date": datetime(2023, 7, 20),
                "cap_rate": 0.067,
                "noi": 790600,
                "occupancy_rate": 0.93,
                "latitude": 40.7508,
                "longitude": -73.9930
            },
            {
                "property_id": "comp_002", 
                "address": "150 Broadway, New York, NY 10038",
                "property_type": "office",
                "square_feet": 78000,
                "year_built": 2016,
                "sale_price": 13200000,
                "sale_date": datetime(2023, 6, 8),
                "cap_rate": 0.062,
                "noi": 818400,
                "occupancy_rate": 0.91,
                "latitude": 40.7080,
                "longitude": -74.0134
            }
        ],
        "market_statistics": {
            "property_count": 125,
            "avg_sale_price": 15750000,
            "median_sale_price": 14200000,
            "avg_price_per_sqft": 165.50,
            "avg_cap_rate": 0.063,
            "cap_rate_stddev": 0.012,
            "avg_occupancy": 0.91,
            "avg_noi": 992250,
            "earliest_sale": datetime(2022, 1, 15),
            "latest_sale": datetime(2023, 10, 30)
        },
        "trend_data": [
            {
                "quarter": datetime(2023, 1, 1),
                "transaction_count": 45,
                "avg_price": 15200000,
                "avg_cap_rate": 0.068,
                "avg_price_per_sqft": 155.50
            },
            {
                "quarter": datetime(2023, 4, 1),
                "transaction_count": 52,
                "avg_price": 15800000,
                "avg_cap_rate": 0.065,
                "avg_price_per_sqft": 162.30
            },
            {
                "quarter": datetime(2023, 7, 1),
                "transaction_count": 48,
                "avg_price": 16500000,
                "avg_cap_rate": 0.062,
                "avg_price_per_sqft": 168.75
            },
            {
                "quarter": datetime(2023, 10, 1),
                "transaction_count": 41,
                "avg_price": 17100000,
                "avg_cap_rate": 0.059,
                "avg_price_per_sqft": 174.20
            }
        ],
        "cap_rate_data": [
            {"cap_rate": 0.055, "sale_price": 18500000, "noi": 1017500, "square_feet": 95000, "sale_date": datetime(2023, 8, 15)},
            {"cap_rate": 0.062, "sale_price": 13200000, "noi": 818400, "square_feet": 78000, "sale_date": datetime(2023, 7, 22)},
            {"cap_rate": 0.068, "sale_price": 11800000, "noi": 802400, "square_feet": 72000, "sale_date": datetime(2023, 6, 10)},
            {"cap_rate": 0.059, "sale_price": 16200000, "noi": 955800, "square_feet": 88000, "sale_date": datetime(2023, 9, 5)},
            {"cap_rate": 0.071, "sale_price": 9750000, "noi": 692250, "square_feet": 65000, "sale_date": datetime(2023, 5, 18)}
        ],
        "property_details": {
            "property_id": "prop_001",
            "address": "100 Main Street, New York, NY 10001",
            "property_type": "office",
            "square_feet": 75000,
            "year_built": 2015,
            "sale_price": 12500000,
            "sale_date": datetime(2023, 8, 15),
            "cap_rate": 0.065,
            "noi": 812500,
            "gross_income": 1200000,
            "operating_expenses": 387500,
            "occupancy_rate": 0.92,
            "latitude": 40.7505,
            "longitude": -73.9934
        }
    }


@pytest.fixture
def mock_sql_results(mock_database_responses):
    """Create mock SQL result objects."""
    results = {}
    
    # Mock comparable properties query result
    comp_rows = []
    for comp_data in mock_database_responses["comparable_properties"]:
        row = MagicMock()
        for key, value in comp_data.items():
            setattr(row, key, value)
        comp_rows.append(row)
    
    comp_result = MagicMock()
    comp_result.fetchall.return_value = comp_rows
    results["comparable_properties"] = comp_result
    
    # Mock market statistics query result  
    market_row = MagicMock()
    for key, value in mock_database_responses["market_statistics"].items():
        setattr(market_row, key, value)
    
    market_result = MagicMock()
    market_result.fetchone.return_value = market_row
    results["market_statistics"] = market_result
    
    # Mock trend data query result
    trend_rows = []
    for trend_data in mock_database_responses["trend_data"]:
        row = MagicMock()
        for key, value in trend_data.items():
            setattr(row, key, value)
        trend_rows.append(row)
    
    trend_result = MagicMock()
    trend_result.fetchall.return_value = trend_rows
    results["trend_data"] = trend_result
    
    # Mock cap rate data query result
    cap_rate_rows = []
    for cap_data in mock_database_responses["cap_rate_data"]:
        row = MagicMock()
        for key, value in cap_data.items():
            setattr(row, key, value)
        cap_rate_rows.append(row)
    
    cap_rate_result = MagicMock()
    cap_rate_result.fetchall.return_value = cap_rate_rows
    results["cap_rate_data"] = cap_rate_result
    
    # Mock property details query result
    property_row = MagicMock()
    for key, value in mock_database_responses["property_details"].items():
        setattr(property_row, key, value)
    
    property_result = MagicMock()
    property_result.fetchone.return_value = property_row
    results["property_details"] = property_result
    
    return results


@pytest.fixture
def mock_mcp_requests():
    """Sample MCP request payloads."""
    return {
        "find_comparable_properties": {
            "jsonrpc": "2.0",
            "id": "req_001",
            "method": "find_comparable_properties",
            "params": {
                "property_id": "prop_001",
                "radius_miles": 5.0,
                "max_results": 10,
                "property_filter": {
                    "min_size": 60000,
                    "max_size": 100000,
                    "occupancy_min": 0.85
                }
            }
        },
        "get_market_data": {
            "jsonrpc": "2.0",
            "id": "req_002", 
            "method": "get_market_data",
            "params": {
                "property_type": "office",
                "city": "New York",
                "state": "NY",
                "start_date": "2022-01-01T00:00:00",
                "end_date": "2023-12-31T23:59:59"
            }
        },
        "analyze_property_value": {
            "jsonrpc": "2.0",
            "id": "req_003",
            "method": "analyze_property_value", 
            "params": {
                "property_id": "prop_001",
                "market_cap_rate": 0.065
            }
        },
        "analyze_cap_rates": {
            "jsonrpc": "2.0",
            "id": "req_004",
            "method": "analyze_cap_rates",
            "params": {
                "property_type": "office",
                "city": "New York", 
                "state": "NY"
            }
        },
        "analyze_market_trends": {
            "jsonrpc": "2.0",
            "id": "req_005",
            "method": "analyze_market_trends",
            "params": {
                "property_type": "office",
                "city": "New York",
                "state": "NY", 
                "start_date": "2022-01-01T00:00:00",
                "end_date": "2023-12-31T23:59:59"
            }
        }
    }


@pytest.fixture
def expected_mcp_responses():
    """Expected MCP response structures."""
    return {
        "find_comparable_properties": {
            "jsonrpc": "2.0",
            "id": "req_001",
            "result": {
                "success": True,
                "data": {
                    "target_property_id": "prop_001", 
                    "comparable_properties": [],
                    "search_radius_miles": 5.0,
                    "total_found": 0
                },
                "error": None
            }
        },
        "get_market_data": {
            "jsonrpc": "2.0", 
            "id": "req_002",
            "result": {
                "success": True,
                "data": {
                    "property_type": "office",
                    "geographic_area": "New York, NY",
                    "total_properties": 125,
                    "avg_sale_price": "15750000",
                    "market_velocity": 4
                },
                "error": None
            }
        }
    }


@pytest.fixture
def test_error_scenarios():
    """Test error scenario configurations."""
    return {
        "database_connection_error": {
            "error": Exception("Failed to connect to database"),
            "expected_response": {
                "success": False,
                "error_message": "Failed to connect to database",
                "error_code": "FINDB_PROCESSING_ERROR"
            }
        },
        "invalid_property_id": {
            "error": Exception("Property prop_999 not found"),
            "expected_response": {
                "success": False,
                "error_message": "Property prop_999 not found", 
                "error_code": "FINDB_PROCESSING_ERROR"
            }
        },
        "no_market_data": {
            "error": Exception("No market data found for specified criteria"),
            "expected_response": {
                "success": False,
                "error_message": "No market data found for specified criteria",
                "error_code": "FINDB_PROCESSING_ERROR"
            }
        },
        "validation_error": {
            "error": ValueError("Invalid cap rate: must be between 0 and 1"),
            "expected_response": {
                "success": False,
                "error_message": "Invalid cap rate: must be between 0 and 1",
                "error_code": "FINDB_PROCESSING_ERROR"
            }
        }
    }


@pytest_asyncio.fixture
async def mock_findb_service(mock_settings, mock_async_session):
    """Mock FinDB service with database session."""
    with patch('src.findb_server.financial_database.create_async_engine'), \
         patch('src.findb_server.financial_database.async_sessionmaker') as mock_sessionmaker:
        
        # Setup session manager mock
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__.return_value = mock_async_session
        mock_session_ctx.__aexit__.return_value = None
        mock_sessionmaker.return_value = mock_session_ctx
        
        # Import and create service
        from src.findb_server.financial_database import FinDBService
        service = FinDBService(mock_settings)
        service.async_session = mock_sessionmaker
        
        yield service
        
        # Cleanup
        await service.cleanup()


@pytest.fixture
def performance_test_data():
    """Large dataset for performance testing."""
    properties = []
    for i in range(1000):
        properties.append(PropertyData(
            property_id=f"perf_prop_{i:04d}",
            address=f"{i * 10} Test Street, City, ST 12345",
            property_type="office" if i % 2 == 0 else "retail",
            square_feet=50000 + (i * 100),
            year_built=1990 + (i % 30),
            latitude=40.7 + (i * 0.001),
            longitude=-74.0 + (i * 0.001),
            cap_rate=0.04 + (i % 40) * 0.001,
            sale_date=datetime(2023, 1, 1) + timedelta(days=i % 365),
            sale_price=Decimal(str(5000000 + i * 10000))
        ))
    return properties