-- init-findb.sql - Initialize test database for FinDB MCP Server

-- Enable PostGIS extension
CREATE EXTENSION IF NOT EXISTS postgis;

-- Create locations table
CREATE TABLE IF NOT EXISTS locations (
    location_id VARCHAR(50) PRIMARY KEY,
    city VARCHAR(100),
    state VARCHAR(2),
    zip_code VARCHAR(10),
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    coordinates GEOGRAPHY(POINT, 4326)
);

-- Create properties table
CREATE TABLE IF NOT EXISTS properties (
    property_id VARCHAR(50) PRIMARY KEY,
    address TEXT NOT NULL,
    property_type VARCHAR(50) NOT NULL,
    square_feet INTEGER,
    year_built INTEGER,
    location_id VARCHAR(50) REFERENCES locations(location_id)
);

-- Create financials table
CREATE TABLE IF NOT EXISTS financials (
    financial_id VARCHAR(50) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    property_id VARCHAR(50) REFERENCES properties(property_id),
    sale_price DECIMAL(15, 2),
    sale_date DATE,
    cap_rate DECIMAL(5, 4),
    noi DECIMAL(15, 2),
    gross_income DECIMAL(15, 2),
    operating_expenses DECIMAL(15, 2)
);

-- Create property metrics table
CREATE TABLE IF NOT EXISTS property_metrics (
    metric_id VARCHAR(50) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    property_id VARCHAR(50) REFERENCES properties(property_id),
    occupancy_rate DECIMAL(5, 4),
    lease_rate_psf DECIMAL(8, 2),
    tenant_count INTEGER,
    avg_lease_term INTEGER
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_properties_type ON properties(property_type);
CREATE INDEX IF NOT EXISTS idx_properties_size ON properties(square_feet);
CREATE INDEX IF NOT EXISTS idx_properties_year ON properties(year_built);
CREATE INDEX IF NOT EXISTS idx_locations_city_state ON locations(city, state);
CREATE INDEX IF NOT EXISTS idx_locations_coordinates ON locations USING GIST(coordinates);
CREATE INDEX IF NOT EXISTS idx_financials_property ON financials(property_id);
CREATE INDEX IF NOT EXISTS idx_financials_sale_date ON financials(sale_date);
CREATE INDEX IF NOT EXISTS idx_financials_cap_rate ON financials(cap_rate);
CREATE INDEX IF NOT EXISTS idx_metrics_property ON property_metrics(property_id);
CREATE INDEX IF NOT EXISTS idx_metrics_occupancy ON property_metrics(occupancy_rate);

-- Insert sample test data

-- Sample locations
INSERT INTO locations (location_id, city, state, zip_code, latitude, longitude, coordinates) VALUES
('loc_001', 'New York', 'NY', '10001', 40.7505, -73.9934, ST_Point(-73.9934, 40.7505)),
('loc_002', 'New York', 'NY', '10007', 40.7127, -74.0059, ST_Point(-74.0059, 40.7127)),
('loc_003', 'New York', 'NY', '10022', 40.7614, -73.9776, ST_Point(-73.9776, 40.7614)),
('loc_004', 'Seattle', 'WA', '98104', 47.6062, -122.3321, ST_Point(-122.3321, 47.6062)),
('loc_005', 'San Francisco', 'CA', '94104', 37.7749, -122.4194, ST_Point(-122.4194, 37.7749))
ON CONFLICT (location_id) DO NOTHING;

-- Sample properties
INSERT INTO properties (property_id, address, property_type, square_feet, year_built, location_id) VALUES
('prop_001', '100 Main Street, New York, NY 10001', 'office', 75000, 2015, 'loc_001'),
('prop_002', '250 Broadway, New York, NY 10007', 'office', 120000, 2018, 'loc_002'),
('prop_003', '500 Park Avenue, New York, NY 10022', 'office', 95000, 2020, 'loc_003'),
('prop_004', '1000 Second Avenue, Seattle, WA 98104', 'office', 85000, 2017, 'loc_004'),
('prop_005', '300 California Street, San Francisco, CA 94104', 'office', 110000, 2019, 'loc_005'),
('prop_006', '125 Main Street, New York, NY 10001', 'office', 72000, 2014, 'loc_001'),
('prop_007', '150 Broadway, New York, NY 10007', 'office', 78000, 2016, 'loc_002'),
('prop_008', '80 Pine Street, New York, NY 10007', 'office', 68000, 2013, 'loc_002')
ON CONFLICT (property_id) DO NOTHING;

-- Sample financials
INSERT INTO financials (property_id, sale_price, sale_date, cap_rate, noi, gross_income, operating_expenses) VALUES
('prop_001', 12500000.00, '2023-08-15', 0.065, 812500.00, 1200000.00, 387500.00),
('prop_002', 24000000.00, '2023-09-22', 0.058, 1392000.00, 1980000.00, 588000.00),
('prop_003', 19000000.00, '2023-07-10', 0.055, 1045000.00, 1520000.00, 475000.00),
('prop_004', 11900000.00, '2023-06-05', 0.072, 856800.00, 1275000.00, 418200.00),
('prop_005', 27500000.00, '2023-10-12', 0.048, 1320000.00, 1890000.00, 570000.00),
('prop_006', 11800000.00, '2023-07-20', 0.067, 790600.00, 1150000.00, 359400.00),
('prop_007', 13200000.00, '2023-06-08', 0.062, 818400.00, 1200000.00, 381600.00),
('prop_008', 10900000.00, '2023-05-15', 0.069, 752100.00, 1100000.00, 347900.00)
ON CONFLICT (financial_id) DO NOTHING;

-- Sample property metrics
INSERT INTO property_metrics (property_id, occupancy_rate, lease_rate_psf, tenant_count, avg_lease_term) VALUES
('prop_001', 0.92, 22.50, 15, 60),
('prop_002', 0.94, 18.75, 25, 72),
('prop_003', 0.88, 24.00, 12, 84),
('prop_004', 0.89, 16.50, 18, 60),
('prop_005', 0.96, 28.00, 20, 96),
('prop_006', 0.93, 21.00, 14, 60),
('prop_007', 0.91, 19.25, 16, 72),
('prop_008', 0.89, 20.50, 13, 60)
ON CONFLICT (metric_id) DO NOTHING;

-- Add some historical data for trend analysis
INSERT INTO financials (property_id, sale_price, sale_date, cap_rate, noi, gross_income, operating_expenses) VALUES
-- Q1 2023 data
('prop_001', 11800000.00, '2023-03-15', 0.068, 802400.00, 1180000.00, 377600.00),
('prop_002', 22500000.00, '2023-02-20', 0.061, 1372500.00, 1950000.00, 577500.00),
-- Q2 2023 data  
('prop_003', 18200000.00, '2023-04-25', 0.057, 1037400.00, 1500000.00, 462600.00),
('prop_004', 11200000.00, '2023-05-10', 0.075, 840000.00, 1250000.00, 410000.00),
-- Additional Q3 2023 data
('prop_005', 26800000.00, '2023-08-30', 0.050, 1340000.00, 1880000.00, 540000.00)
ON CONFLICT (financial_id) DO NOTHING;

ANALYZE locations;
ANALYZE properties;
ANALYZE financials;
ANALYZE property_metrics;