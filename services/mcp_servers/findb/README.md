# FinDB MCP Server

Financial Database MCP Server for comprehensive real estate market data analysis and property valuation. This server provides sophisticated financial analysis capabilities for commercial real estate underwriting through both MCP protocol WebSocket connections and REST API endpoints.

## Architecture Overview

### Core Components

- **FinDBService**: Main orchestrator handling query processing and database operations
- **CompsAnalyzer**: Comparable property analysis with sophisticated scoring algorithms
- **MarketAnalyzer**: Market data aggregation and trend analysis
- **FinancialCalculator**: Real estate financial calculations (cap rates, NOI, DCF, IRR)
- **Database Layer**: PostgreSQL/RDS integration with connection pooling and async operations

### Key Features

- **Comparable Property Analysis**: Find and score comparable properties based on location, size, age, and financial metrics
- **Market Data Analysis**: Comprehensive market statistics including pricing trends, cap rates, and transaction volumes
- **Property Valuation**: Multi-approach property valuation using income, sales comparison, and cost approaches
- **Cap Rate Analysis**: Market cap rate analysis with statistical distributions and trend analysis
- **Trend Analysis**: Time-series analysis of market conditions and price movements
- **Financial Calculations**: Complete suite of real estate financial calculations and metrics

## API Reference

### MCP Protocol Methods

All MCP methods are available via WebSocket at `/mcp` endpoint.

#### `find_comparable_properties`

Find comparable properties based on search criteria.

**Parameters:**
```json
{
  "property_id": "string",           // Target property ID
  "radius_miles": 5.0,              // Search radius in miles (optional)
  "max_results": 10,                // Maximum number of results (optional)
  "property_filter": {              // Optional filtering criteria
    "min_size": 40000,              // Minimum square footage
    "max_size": 80000,              // Maximum square footage
    "min_price": 4000000,           // Minimum sale price
    "max_price": 8000000,           // Maximum sale price
    "year_built_min": 2000,         // Minimum year built
    "occupancy_min": 0.85,          // Minimum occupancy rate
    "cap_rate_min": 0.05,           // Minimum cap rate
    "cap_rate_max": 0.08            // Maximum cap rate
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "target_property_id": "prop_123",
    "comparable_properties": [
      {
        "property_id": "comp_001",
        "address": "123 Main St",
        "property_type": "office",
        "square_feet": 50000,
        "year_built": 2015,
        "sale_price": "5000000.00",
        "sale_date": "2023-06-15T00:00:00",
        "cap_rate": 0.065,
        "noi": "325000.00",
        "price_per_sqft": "100.00",
        "occupancy_rate": 0.92,
        "distance_miles": 2.3,
        "similarity_score": 85.5
      }
    ],
    "search_radius_miles": 5.0,
    "total_found": 1
  }
}
```

#### `get_market_data`

Retrieve comprehensive market data for a geographic area.

**Parameters:**
```json
{
  "property_type": "office",         // Property type (office, retail, industrial, etc.)
  "city": "New York",               // City name (optional)
  "state": "NY",                    // State abbreviation (optional)
  "zip_code": "10001",              // ZIP code (optional)
  "start_date": "2022-01-01T00:00:00",  // Analysis start date
  "end_date": "2023-12-31T23:59:59"     // Analysis end date
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "property_type": "office",
    "geographic_area": "New York, NY",
    "date_range_start": "2022-01-01T00:00:00",
    "date_range_end": "2023-12-31T23:59:59",
    "total_properties": 150,
    "avg_sale_price": "15750000.00",
    "median_sale_price": "14200000.00",
    "avg_price_per_sqft": "165.50",
    "avg_cap_rate": 0.063,
    "cap_rate_std": 0.012,
    "avg_occupancy": 0.91,
    "avg_noi": "992250.00",
    "trend_data": [
      {
        "period": "2023-Q1",
        "transaction_count": 45,
        "avg_price": "15200000.00",
        "avg_cap_rate": 0.068,
        "price_per_sqft": "155.50",
        "period_start": "2023-01-01T00:00:00",
        "period_end": "2023-03-31T23:59:59"
      }
    ],
    "market_velocity": 4
  }
}
```

#### `analyze_property_value`

Perform comprehensive property valuation analysis.

**Parameters:**
```json
{
  "property_id": "prop_123",        // Property to value
  "market_cap_rate": 0.065          // Market cap rate for income approach (optional)
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "property_id": "prop_123",
    "valuation_date": "2023-12-01T10:30:00",
    "income_approach_value": "5000000.00",
    "sales_comparison_value": "4850000.00",
    "cost_approach_value": null,
    "final_value_estimate": "4925000.00",
    "confidence_level": 85.0,
    "comparable_sales_count": 5,
    "market_conditions": "stable",
    "financial_metrics": {
      "cap_rate": 0.065,
      "noi": "325000.00",
      "gross_income": "480000.00",
      "operating_expenses": "155000.00",
      "occupancy_rate": 0.92,
      "price_per_sqft": "100.00"
    },
    "valuation_method": "income_approach"
  }
}
```

#### `analyze_cap_rates`

Analyze cap rates for a specific market area.

**Parameters:**
```json
{
  "property_type": "office",        // Property type
  "city": "New York",              // City name
  "state": "NY"                    // State abbreviation
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "property_type": "office",
    "geographic_area": "New York, NY",
    "analysis_date": "2023-12-01T10:30:00",
    "sample_size": 125,
    "avg_cap_rate": 0.063,
    "median_cap_rate": 0.062,
    "std_deviation": 0.012,
    "min_cap_rate": 0.048,
    "max_cap_rate": 0.085,
    "percentile_25": 0.055,
    "percentile_75": 0.070,
    "market_trend": "stable",
    "data_quality_score": 85.0
  }
}
```

#### `analyze_market_trends`

Perform comprehensive market trend analysis.

**Parameters:**
```json
{
  "property_type": "office",        // Property type
  "city": "New York",              // City name (optional)
  "state": "NY",                   // State abbreviation (optional)
  "start_date": "2022-01-01T00:00:00",  // Analysis start date
  "end_date": "2023-12-31T23:59:59"     // Analysis end date
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "property_type": "office",
    "geographic_area": "New York, NY",
    "analysis_period_start": "2022-01-01T00:00:00",
    "analysis_period_end": "2023-12-31T23:59:59",
    "trend_periods": [
      {
        "period": "2023-Q1",
        "transaction_count": 45,
        "avg_price": "15200000.00",
        "avg_cap_rate": 0.068,
        "price_per_sqft": "155.50"
      }
    ],
    "overall_price_trend": 8.5,      // Percentage change
    "volume_trend": -12.3,           // Percentage change in transaction volume
    "volatility_index": 15.2,        // Price volatility measure
    "market_momentum": "positive",
    "forecast_confidence": 75.0
  }
}
```

### REST API Endpoints

#### POST `/api/comparable-analysis`

HTTP endpoint for comparable property analysis.

**Request Body:**
```json
{
  "property_id": "prop_123",
  "radius_miles": 5.0,
  "max_results": 10,
  "property_type": "office",
  "min_size": 40000,
  "max_size": 80000
}
```

#### POST `/api/market-data`

HTTP endpoint for market data analysis.

**Request Body:**
```json
{
  "property_type": "office",
  "city": "New York",
  "state": "NY",
  "start_date": "2022-01-01T00:00:00",
  "end_date": "2023-12-31T23:59:59"
}
```

#### POST `/api/property-valuation`

HTTP endpoint for property valuation.

**Request Body:**
```json
{
  "property_id": "prop_123",
  "market_cap_rate": 0.065,
  "valuation_date": "2023-12-01T10:30:00"
}
```

## Database Schema

The FinDB server expects the following PostgreSQL database schema:

### Properties Table
```sql
CREATE TABLE properties (
    property_id VARCHAR(50) PRIMARY KEY,
    address TEXT NOT NULL,
    property_type VARCHAR(50) NOT NULL,
    square_feet INTEGER,
    year_built INTEGER,
    location_id VARCHAR(50) REFERENCES locations(location_id)
);

CREATE INDEX idx_properties_type ON properties(property_type);
CREATE INDEX idx_properties_size ON properties(square_feet);
CREATE INDEX idx_properties_year ON properties(year_built);
```

### Locations Table
```sql
CREATE TABLE locations (
    location_id VARCHAR(50) PRIMARY KEY,
    city VARCHAR(100),
    state VARCHAR(2),
    zip_code VARCHAR(10),
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    coordinates GEOGRAPHY(POINT, 4326)
);

CREATE INDEX idx_locations_city_state ON locations(city, state);
CREATE INDEX idx_locations_coordinates ON locations USING GIST(coordinates);
```

### Financials Table
```sql
CREATE TABLE financials (
    financial_id VARCHAR(50) PRIMARY KEY,
    property_id VARCHAR(50) REFERENCES properties(property_id),
    sale_price DECIMAL(15, 2),
    sale_date DATE,
    cap_rate DECIMAL(5, 4),
    noi DECIMAL(15, 2),
    gross_income DECIMAL(15, 2),
    operating_expenses DECIMAL(15, 2)
);

CREATE INDEX idx_financials_property ON financials(property_id);
CREATE INDEX idx_financials_sale_date ON financials(sale_date);
CREATE INDEX idx_financials_cap_rate ON financials(cap_rate);
```

### Property Metrics Table
```sql
CREATE TABLE property_metrics (
    metric_id VARCHAR(50) PRIMARY KEY,
    property_id VARCHAR(50) REFERENCES properties(property_id),
    occupancy_rate DECIMAL(5, 4),
    lease_rate_psf DECIMAL(8, 2),
    tenant_count INTEGER,
    avg_lease_term INTEGER
);

CREATE INDEX idx_metrics_property ON property_metrics(property_id);
CREATE INDEX idx_metrics_occupancy ON property_metrics(occupancy_rate);
```

## Configuration

### Environment Variables

```bash
# Database Configuration
RDS_HOST=localhost
RDS_PORT=5432
RDS_DATABASE=findb
RDS_USERNAME=findb_user
RDS_PASSWORD=secure_password

# Application Configuration
DEBUG=false
LOG_LEVEL=INFO

# Performance Configuration
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600
```

### Settings Class

```python
from packages.config.settings import Settings

settings = Settings(
    rds_host="localhost",
    rds_port=5432,
    rds_database="findb",
    rds_username="findb_user",
    rds_password="secure_password",
    debug=False
)
```

## Development

### Setup

```bash
# Install dependencies
poetry install

# Run tests
poetry run pytest

# Run with hot reload
poetry run uvicorn src.findb_server.main:app --reload --port 8003

# Run linting
poetry run ruff check src/
poetry run black src/
poetry run mypy src/
```

### Testing

```bash
# Run all tests
poetry run pytest tests/ -v

# Run with coverage
poetry run pytest tests/ --cov=src/findb_server --cov-report=html

# Run specific test categories
poetry run pytest tests/test_findb_server.py::TestCompsAnalyzer -v
poetry run pytest tests/test_findb_server.py::TestMarketAnalyzer -v
poetry run pytest tests/test_findb_server.py::TestFinancialCalculator -v
```

### Docker

```bash
# Build image
docker build -t findb-mcp-server .

# Run container
docker run -p 8003:8003 \
  -e RDS_HOST=localhost \
  -e RDS_DATABASE=findb \
  -e RDS_USERNAME=findb_user \
  -e RDS_PASSWORD=secure_password \
  findb-mcp-server

# Run with docker-compose
docker-compose up -d
```

## Performance Considerations

### Database Optimization

- **Spatial Indexing**: Uses PostGIS geography columns with GiST indexes for efficient location-based queries
- **Connection Pooling**: Configured with appropriate pool sizes for concurrent operations
- **Query Optimization**: Optimized SQL queries with proper indexing strategies
- **Async Operations**: Fully async database operations for high concurrency

### Caching Strategy

- **Query Result Caching**: Consider implementing Redis caching for frequently accessed market data
- **Connection Caching**: Database connections are pooled and reused efficiently
- **Computation Caching**: Financial calculations can be cached for repeated property valuations

### Monitoring

```python
# Health check endpoint
GET /health

# Response includes:
{
  "status": "healthy",
  "database_connected": true,
  "latest_data_age_days": 5,
  "data_freshness": "good",
  "timestamp": "2023-12-01T10:30:00"
}
```

## Error Handling

### Error Response Format

```json
{
  "success": false,
  "error_message": "Property prop_999 not found",
  "error_code": "FINDB_PROCESSING_ERROR",
  "timestamp": "2023-12-01T10:30:00"
}
```

### Error Codes

- `FINDB_PROCESSING_ERROR`: General processing error
- `DATABASE_ERROR`: Database connectivity or query error
- `VALIDATION_ERROR`: Input validation error
- `MCP_ERROR`: MCP protocol error

### Logging

Structured logging with contextual information:

```python
logger.info("Processing FinDB query",
           query_type="COMPS",
           property_id="prop_123",
           radius_miles=5.0)
```

## Integration

### MCP Server Configuration

Add to your MCP servers configuration:

```yaml
mcp_servers:
  findb:
    command: "poetry"
    args:
      - "run"
      - "python"
      - "-m"
      - "uvicorn"
      - "src.findb_server.main:app"
      - "--host"
      - "0.0.0.0"
      - "--port"
      - "8003"
    cwd: "/path/to/findb-mcp-server"
    env:
      RDS_HOST: "your-rds-host"
      RDS_DATABASE: "findb"
      RDS_USERNAME: "findb_user"
      RDS_PASSWORD: "secure_password"
```

### Client Usage

```python
import asyncio
import websockets
import json

async def query_findb():
    uri = "ws://localhost:8003/mcp"

    async with websockets.connect(uri) as websocket:
        # Send MCP request
        request = {
            "jsonrpc": "2.0",
            "id": "req_001",
            "method": "find_comparable_properties",
            "params": {
                "property_id": "prop_123",
                "radius_miles": 5.0,
                "max_results": 10
            }
        }

        await websocket.send(json.dumps(request))
        response = await websocket.recv()

        result = json.loads(response)
        print(f"Found {len(result['result']['data']['comparable_properties'])} comps")

# Run client
asyncio.run(query_findb())
```

## Security

### Database Security

- Connection string encryption
- SQL injection prevention through parameterized queries
- Role-based database access controls
- Connection pooling with timeout controls

### API Security

- Input validation on all endpoints
- Rate limiting considerations
- Error message sanitization
- Audit logging for sensitive operations

## Troubleshooting

### Common Issues

1. **Database Connection Fails**
   - Check RDS_HOST and credentials
   - Verify network connectivity
   - Check security group settings

2. **No Comparable Properties Found**
   - Increase search radius
   - Adjust property filters
   - Verify property data exists in database

3. **Performance Issues**
   - Check database indexes
   - Monitor connection pool usage
   - Review query execution plans

4. **Memory Usage**
   - Monitor large result sets
   - Implement pagination for large queries
   - Check connection pool configuration

### Debug Mode

Enable debug mode for detailed logging:

```bash
export DEBUG=true
poetry run uvicorn src.findb_server.main:app --reload --log-level debug
```

This comprehensive FinDB MCP Server provides the financial database capabilities needed for sophisticated commercial real estate analysis and decision-making.
