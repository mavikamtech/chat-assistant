"""
Comprehensive test suite for FinDB MCP Server.

Tests all aspects of financial database operations including:
- Comparable property analysis
- Market data queries
- Property valuation
- Cap rate analysis
- Trend analysis
- Database connectivity
- MCP protocol compliance
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

# Import modules to test
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))
from src.findb_server.main import app
from src.findb_server.financial_database import (
    FinDBService, CompsAnalyzer, MarketAnalyzer, FinancialCalculator,
    PropertyFilter
)
from packages.common.models import (
    FinDBQuery, FinDBQueryType, PropertyData, CompsRequest, MarketDataRequest,
    PropertyValuationRequest, CapRateAnalysisRequest, TrendAnalysisRequest,
    CompData, MarketDataResult, PropertyValuationResult
)
from packages.common.errors import FinDBError, ValidationError


@pytest.fixture
def test_client():
    """Test client for FastAPI app."""
    return TestClient(app)

@pytest.fixture
def mock_db_session():
    """Mock database session."""
    session = AsyncMock(spec=AsyncSession)
    return session

@pytest.fixture
def sample_property_data():
    """Sample property data for testing."""
    return PropertyData(
        property_id="prop_123",
        address="123 Main St",
        property_type="office",
        square_feet=50000,
        year_built=2010,
        latitude=40.7128,
        longitude=-74.0060,
        cap_rate=0.065,
        sale_date=datetime(2023, 6, 15),
        sale_price=Decimal("5000000")
    )

@pytest.fixture
def sample_comp_data():
    """Sample comparable property data."""
    return [
        CompData(
            property_id="comp_1",
            address="456 Oak Ave",
            property_type="office",
            square_feet=48000,
            year_built=2012,
            sale_price=Decimal("4800000"),
            sale_date=datetime(2023, 5, 20),
            cap_rate=0.062,
            noi=Decimal("297600"),
            price_per_sqft=Decimal("100.00"),
            occupancy_rate=0.92,
            distance_miles=2.3,
            similarity_score=85.5
        ),
        CompData(
            property_id="comp_2",
            address="789 Pine St",
            property_type="office",
            square_feet=52000,
            year_built=2008,
            sale_price=Decimal("5200000"),
            sale_date=datetime(2023, 4, 10),
            cap_rate=0.068,
            noi=Decimal("353600"),
            price_per_sqft=Decimal("100.00"),
            occupancy_rate=0.88,
            distance_miles=3.1,
            similarity_score=82.3
        )
    ]

@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    settings = MagicMock()
    settings.rds_host = "test-host"
    settings.rds_port = 5432
    settings.rds_database = "test_db"
    settings.rds_username = "test_user"
    settings.rds_password.get_secret_value.return_value = "test_pass"
    settings.debug = False
    return settings


class TestFinancialCalculator:
    """Test financial calculation methods."""

    def setup_method(self):
        """Setup test method."""
        self.calculator = FinancialCalculator()

    def test_calculate_cap_rate(self):
        """Test cap rate calculation."""
        noi = Decimal("300000")
        purchase_price = Decimal("5000000")

        cap_rate = self.calculator.calculate_cap_rate(noi, purchase_price)
        assert cap_rate == 0.06

    def test_calculate_cap_rate_zero_price(self):
        """Test cap rate with zero purchase price."""
        noi = Decimal("300000")
        purchase_price = Decimal("0")

        with pytest.raises(ValidationError):
            self.calculator.calculate_cap_rate(noi, purchase_price)

    def test_calculate_noi(self):
        """Test NOI calculation."""
        gross_income = Decimal("500000")
        operating_expenses = Decimal("200000")

        noi = self.calculator.calculate_noi(gross_income, operating_expenses)
        assert noi == Decimal("300000")

    def test_calculate_dscr(self):
        """Test DSCR calculation."""
        noi = Decimal("300000")
        debt_service = Decimal("250000")

        dscr = self.calculator.calculate_dscr(noi, debt_service)
        assert dscr == 1.2

    def test_calculate_dscr_zero_debt_service(self):
        """Test DSCR with zero debt service."""
        noi = Decimal("300000")
        debt_service = Decimal("0")

        with pytest.raises(ValidationError):
            self.calculator.calculate_dscr(noi, debt_service)

    def test_calculate_ltv(self):
        """Test LTV calculation."""
        loan_amount = Decimal("4000000")
        property_value = Decimal("5000000")

        ltv = self.calculator.calculate_ltv(loan_amount, property_value)
        assert ltv == 0.8

    def test_calculate_property_value_income_approach(self):
        """Test property valuation using income approach."""
        noi = Decimal("300000")
        cap_rate = 0.06

        value = self.calculator.calculate_property_value_income_approach(noi, cap_rate)
        assert value == Decimal("5000000")

    def test_calculate_irr_simple(self):
        """Test IRR calculation with simple cash flows."""
        cash_flows = [Decimal("-1000000"), Decimal("100000"), Decimal("100000"), Decimal("1200000")]

        irr = self.calculator.calculate_irr(cash_flows)
        # Should be approximately 12%
        assert 0.10 < irr < 0.15

    def test_calculate_irr_insufficient_flows(self):
        """Test IRR with insufficient cash flows."""
        cash_flows = [Decimal("-1000000")]

        with pytest.raises(ValidationError):
            self.calculator.calculate_irr(cash_flows)


class TestCompsAnalyzer:
    """Test comparable property analysis."""

    @pytest.mark.asyncio
    async def test_find_comparable_properties(self, mock_db_session, sample_property_data, sample_comp_data):
        """Test finding comparable properties."""
        analyzer = CompsAnalyzer(mock_db_session)

        # Mock database query results
        mock_rows = []
        for comp in sample_comp_data:
            mock_row = MagicMock()
            mock_row.property_id = comp.property_id
            mock_row.address = comp.address
            mock_row.property_type = comp.property_type
            mock_row.square_feet = comp.square_feet
            mock_row.year_built = comp.year_built
            mock_row.sale_price = float(comp.sale_price)
            mock_row.sale_date = comp.sale_date
            mock_row.cap_rate = comp.cap_rate
            mock_row.noi = float(comp.noi)
            mock_row.occupancy_rate = comp.occupancy_rate
            mock_row.latitude = 40.7150  # Slightly different coordinates
            mock_row.longitude = -74.0080
            mock_rows.append(mock_row)

        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows
        mock_db_session.execute.return_value = mock_result

        # Test the analysis
        comps = await analyzer.find_comparable_properties(
            target_property=sample_property_data,
            radius_miles=5.0,
            max_results=10
        )

        assert len(comps) == 2
        assert all(isinstance(comp, CompData) for comp in comps)
        assert comps[0].property_type == "office"
        assert comps[0].distance_miles > 0
        assert comps[0].similarity_score > 0

    @pytest.mark.asyncio
    async def test_find_comparable_properties_with_filter(self, mock_db_session, sample_property_data):
        """Test comps analysis with property filter."""
        analyzer = CompsAnalyzer(mock_db_session)

        property_filter = PropertyFilter(
            min_size=40000,
            max_size=60000,
            min_price=Decimal("4000000"),
            max_price=Decimal("6000000"),
            occupancy_min=0.85
        )

        # Mock empty results
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_db_session.execute.return_value = mock_result

        comps = await analyzer.find_comparable_properties(
            target_property=sample_property_data,
            radius_miles=3.0,
            max_results=5,
            property_filter=property_filter
        )

        assert comps == []

    def test_calculate_similarity_score(self, sample_property_data, sample_comp_data):
        """Test similarity score calculation."""
        analyzer = CompsAnalyzer(MagicMock())

        comp = sample_comp_data[0]
        score = analyzer._calculate_similarity_score(sample_property_data, comp)

        assert 0 <= score <= 100
        assert isinstance(score, float)


class TestMarketAnalyzer:
    """Test market data analysis."""

    @pytest.mark.asyncio
    async def test_get_market_data(self, mock_db_session):
        """Test market data retrieval."""
        analyzer = MarketAnalyzer(mock_db_session)

        # Mock market data query result
        mock_market_row = MagicMock()
        mock_market_row.property_count = 150
        mock_market_row.avg_sale_price = 4500000
        mock_market_row.median_sale_price = 4200000
        mock_market_row.avg_price_per_sqft = 95.0
        mock_market_row.avg_cap_rate = 0.065
        mock_market_row.cap_rate_stddev = 0.008
        mock_market_row.avg_occupancy = 0.89
        mock_market_row.avg_noi = 292500

        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_market_row

        # Mock trend data query (empty for simplicity)
        mock_trend_result = MagicMock()
        mock_trend_result.fetchall.return_value = []

        # Setup execute to return different results based on call
        mock_db_session.execute.side_effect = [mock_result, mock_trend_result]

        request = MarketDataRequest(
            property_type="office",
            city="New York",
            state="NY",
            start_date=datetime(2022, 1, 1),
            end_date=datetime(2023, 12, 31)
        )

        result = await analyzer.get_market_data(request)

        assert isinstance(result, MarketDataResult)
        assert result.property_type == "office"
        assert result.total_properties == 150
        assert result.avg_sale_price == Decimal("4500000")
        assert result.avg_cap_rate == 0.065

    @pytest.mark.asyncio
    async def test_get_market_data_no_results(self, mock_db_session):
        """Test market data with no results."""
        analyzer = MarketAnalyzer(mock_db_session)

        # Mock empty result
        mock_market_row = MagicMock()
        mock_market_row.property_count = 0

        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_market_row
        mock_db_session.execute.return_value = mock_result

        request = MarketDataRequest(
            property_type="retail",
            city="Nonexistent",
            state="XX",
            start_date=datetime(2022, 1, 1),
            end_date=datetime(2023, 12, 31)
        )

        with pytest.raises(FinDBError, match="No market data found"):
            await analyzer.get_market_data(request)


class TestFinDBService:
    """Test main FinDB service."""

    @pytest.mark.asyncio
    async def test_process_comps_query(self, mock_settings):
        """Test processing comparable properties query."""
        with patch('src.findb_server.financial_database.create_async_engine'), \
             patch('src.findb_server.financial_database.async_sessionmaker') as mock_sessionmaker:

            # Setup mocks
            mock_session = AsyncMock()
            mock_sessionmaker.return_value.__aenter__.return_value = mock_session
            mock_sessionmaker.return_value.__aexit__.return_value = None

            service = FinDBService(mock_settings)
            service.async_session = mock_sessionmaker

            # Mock CompsAnalyzer
            with patch.object(service, 'async_session') as mock_session_ctx:
                mock_session_ctx.return_value.__aenter__.return_value = mock_session
                mock_session_ctx.return_value.__aexit__.return_value = None

                with patch('src.findb_server.financial_database.CompsAnalyzer') as mock_analyzer_class:
                    mock_analyzer = AsyncMock()
                    mock_analyzer.find_comparable_properties.return_value = []
                    mock_analyzer_class.return_value = mock_analyzer

                    # Create test query
                    query = FinDBQuery(
                        query_id=str(uuid.uuid4()),
                        query_type=FinDBQueryType.COMPS,
                        target_property=PropertyData(
                            property_id="test_prop",
                            property_type="office",
                            square_feet=50000,
                            latitude=40.7128,
                            longitude=-74.0060
                        ),
                        radius_miles=5.0,
                        max_results=10
                    )

                    # Process query
                    result = await service.process_query(query)

                    assert result.success is True
                    assert result.query_type == FinDBQueryType.COMPS

    @pytest.mark.asyncio
    async def test_process_invalid_query_type(self, mock_settings):
        """Test processing invalid query type."""
        with patch('src.findb_server.financial_database.create_async_engine'), \
             patch('src.findb_server.financial_database.async_sessionmaker'):

            service = FinDBService(mock_settings)

            # Create query with invalid type (manually set invalid enum)
            query = FinDBQuery(
                query_id=str(uuid.uuid4()),
                query_type="INVALID_TYPE",  # This should cause validation error
                target_property=PropertyData(property_id="test")
            )

            with pytest.raises(Exception):  # Pydantic validation will catch this
                await service.process_query(query)

    @pytest.mark.asyncio
    async def test_health_check_success(self, mock_settings):
        """Test successful health check."""
        with patch('src.findb_server.financial_database.create_async_engine'), \
             patch('src.findb_server.financial_database.async_sessionmaker') as mock_sessionmaker:

            # Setup successful database connection
            mock_session = AsyncMock()

            # Mock query results
            mock_health_result = MagicMock()
            mock_health_result.fetchone.return_value = MagicMock()

            mock_freshness_result = MagicMock()
            mock_freshness_row = MagicMock()
            mock_freshness_row.latest_sale = datetime.now().date() - timedelta(days=5)
            mock_freshness_result.fetchone.return_value = mock_freshness_row

            mock_session.execute.side_effect = [mock_health_result, mock_freshness_result]

            mock_session_ctx = AsyncMock()
            mock_session_ctx.__aenter__.return_value = mock_session
            mock_session_ctx.__aexit__.return_value = None
            mock_sessionmaker.return_value = mock_session_ctx

            service = FinDBService(mock_settings)

            health_status = await service.health_check()

            assert health_status["status"] == "healthy"
            assert health_status["database_connected"] is True
            assert "latest_data_age_days" in health_status

    @pytest.mark.asyncio
    async def test_health_check_failure(self, mock_settings):
        """Test health check failure."""
        with patch('src.findb_server.financial_database.create_async_engine'), \
             patch('src.findb_server.financial_database.async_sessionmaker') as mock_sessionmaker:

            # Setup failing database connection
            mock_session = AsyncMock()
            mock_session.execute.side_effect = Exception("Database connection failed")

            mock_session_ctx = AsyncMock()
            mock_session_ctx.__aenter__.return_value = mock_session
            mock_session_ctx.__aexit__.return_value = None
            mock_sessionmaker.return_value = mock_session_ctx

            service = FinDBService(mock_settings)

            health_status = await service.health_check()

            assert health_status["status"] == "unhealthy"
            assert health_status["database_connected"] is False
            assert "error" in health_status


class TestHTTPEndpoints:
    """Test HTTP REST API endpoints."""

    def test_health_endpoint_service_not_initialized(self, test_client):
        """Test health endpoint when service is not initialized."""
        response = test_client.get("/health")
        assert response.status_code == 503

    def test_capabilities_endpoint(self, test_client):
        """Test capabilities endpoint."""
        response = test_client.get("/capabilities")
        assert response.status_code == 200

        data = response.json()
        assert "tools" in data
        assert "server_info" in data
        assert len(data["tools"]) > 0

        # Check for expected tools
        tool_names = [tool["name"] for tool in data["tools"]]
        expected_tools = [
            "find_comparable_properties",
            "get_market_data",
            "analyze_property_value",
            "analyze_cap_rates",
            "analyze_market_trends"
        ]

        for tool in expected_tools:
            assert tool in tool_names


class TestMCPProtocol:
    """Test MCP protocol compliance."""

    @pytest.mark.asyncio
    async def test_mcp_request_validation(self):
        """Test MCP request validation."""
        from packages.common.models import MCPRequest

        # Valid request
        valid_request = {
            "jsonrpc": "2.0",
            "id": "test-123",
            "method": "find_comparable_properties",
            "params": {"property_id": "prop_123"}
        }

        request = MCPRequest.model_validate(valid_request)
        assert request.method == "find_comparable_properties"
        assert request.params["property_id"] == "prop_123"

        # Invalid request (missing required fields)
        with pytest.raises(Exception):
            MCPRequest.model_validate({
                "jsonrpc": "2.0",
                "method": "test"
                # Missing id
            })

    def test_websocket_endpoint_structure(self, test_client):
        """Test WebSocket endpoint structure."""
        # This tests the endpoint setup, actual WebSocket testing would need more complex setup
        # The endpoint should be available
        assert hasattr(app, 'websocket_route')


class TestIntegration:
    """Integration tests for complete workflows."""

    @pytest.mark.asyncio
    async def test_comparable_analysis_workflow(self, mock_settings, sample_property_data):
        """Test end-to-end comparable analysis workflow."""
        with patch('src.findb_server.financial_database.create_async_engine'), \
             patch('src.findb_server.financial_database.async_sessionmaker') as mock_sessionmaker:

            # Setup service
            service = FinDBService(mock_settings)

            # Mock successful database operations
            mock_session = AsyncMock()
            mock_session_ctx = AsyncMock()
            mock_session_ctx.__aenter__.return_value = mock_session
            mock_session_ctx.__aexit__.return_value = None
            mock_sessionmaker.return_value = mock_session_ctx
            service.async_session = mock_sessionmaker

            # Mock CompsAnalyzer with realistic data
            with patch('src.findb_server.financial_database.CompsAnalyzer') as mock_analyzer_class:
                mock_analyzer = AsyncMock()

                # Create realistic comp data
                mock_comps = [
                    CompData(
                        property_id="comp_1",
                        address="123 Test St",
                        property_type="office",
                        square_feet=45000,
                        year_built=2015,
                        sale_price=Decimal("4500000"),
                        sale_date=datetime.now() - timedelta(days=90),
                        cap_rate=0.063,
                        noi=Decimal("283500"),
                        price_per_sqft=Decimal("100.00"),
                        occupancy_rate=0.91,
                        distance_miles=1.8,
                        similarity_score=88.5
                    )
                ]

                mock_analyzer.find_comparable_properties.return_value = mock_comps
                mock_analyzer_class.return_value = mock_analyzer

                # Create and process query
                query = FinDBQuery(
                    query_id=str(uuid.uuid4()),
                    query_type=FinDBQueryType.COMPS,
                    target_property=sample_property_data,
                    radius_miles=5.0,
                    max_results=10
                )

                result = await service.process_query(query)

                # Verify results
                assert result.success is True
                assert result.result is not None
                assert len(result.result.comparable_properties) == 1
                assert result.result.comparable_properties[0].similarity_score > 80

    @pytest.mark.asyncio
    async def test_error_handling_workflow(self, mock_settings):
        """Test error handling in complete workflow."""
        with patch('src.findb_server.financial_database.create_async_engine'), \
             patch('src.findb_server.financial_database.async_sessionmaker') as mock_sessionmaker:

            service = FinDBService(mock_settings)

            # Mock database error
            mock_session_ctx = AsyncMock()
            mock_session_ctx.__aenter__.side_effect = Exception("Database connection failed")
            mock_sessionmaker.return_value = mock_session_ctx
            service.async_session = mock_sessionmaker

            # Create query
            query = FinDBQuery(
                query_id=str(uuid.uuid4()),
                query_type=FinDBQueryType.COMPS,
                target_property=PropertyData(property_id="test")
            )

            # Process query and verify error handling
            result = await service.process_query(query)

            assert result.success is False
            assert result.error_message is not None
            assert result.error_code == "FINDB_PROCESSING_ERROR"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
