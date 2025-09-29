"""
Financial Database Service for property data and market analysis.

This module provides comprehensive financial database operations for commercial
real estate analysis, including market data queries, comparable property analysis,
cap rate calculations, and property valuation support.

Key Features:
- Market data queries and aggregation
- Comparable property analysis (comps)
- Cap rate and NOI calculations
- Property valuation metrics
- Market trend analysis
- SQL query optimization for real estate data
"""

import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple, Union
import json
import logging

import pandas as pd
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import text, select, and_, or_, func, desc
from sqlalchemy.exc import SQLAlchemyError
import structlog
from pydantic import BaseModel, Field, validator

# Import models from common package
import sys
import os
from mavik_common.models import (
    FinDBQuery, FinDBQueryType, CompsRequest, MarketDataRequest,
    PropertyData
)
from mavik_common.errors import FinDBError, DatabaseError, ValidationError
from mavik_config.settings import Settings

# Configure structured logging
logger = structlog.get_logger(__name__)

class DatabaseConfig(BaseModel):
    """Database connection configuration."""
    host: str = Field(..., description="Database host")
    port: int = Field(5432, description="Database port")
    database: str = Field(..., description="Database name")
    username: str = Field(..., description="Database username")
    password: str = Field(..., description="Database password")
    ssl_mode: str = Field("require", description="SSL mode")
    pool_size: int = Field(20, description="Connection pool size")
    max_overflow: int = Field(10, description="Max connection overflow")
    pool_timeout: int = Field(30, description="Pool timeout in seconds")
    pool_recycle: int = Field(3600, description="Pool recycle time in seconds")


class PropertyFilter(BaseModel):
    """Property filtering criteria."""
    property_type: Optional[str] = None
    min_size: Optional[int] = None
    max_size: Optional[int] = None
    min_price: Optional[Decimal] = None
    max_price: Optional[Decimal] = None
    location_radius: Optional[float] = None
    year_built_min: Optional[int] = None
    year_built_max: Optional[int] = None
    occupancy_min: Optional[float] = None
    cap_rate_min: Optional[float] = None
    cap_rate_max: Optional[float] = None


class CompsAnalyzer:
    """Comparable property analysis engine."""
    
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.logger = logger.bind(component="comps_analyzer")
    
    async def find_comparable_properties(
        self,
        target_property: PropertyData,
        radius_miles: float = 5.0,
        max_results: int = 10,
        property_filter: Optional[PropertyFilter] = None
    ) -> List[CompData]:
        """Find comparable properties based on criteria."""
        try:
            # Build base query for comparable properties
            query_parts = [
                "SELECT DISTINCT p.*, pm.*, l.*, f.*",
                "FROM properties p",
                "JOIN property_metrics pm ON p.property_id = pm.property_id",
                "JOIN locations l ON p.location_id = l.location_id", 
                "JOIN financials f ON p.property_id = f.property_id",
                "WHERE p.property_type = :property_type",
                "AND p.property_id != :target_id",
                "AND ST_DWithin(l.coordinates, ST_Point(:target_lng, :target_lat)::geography, :radius_meters)"
            ]
            
            params = {
                'property_type': target_property.property_type,
                'target_id': target_property.property_id,
                'target_lng': target_property.longitude,
                'target_lat': target_property.latitude,
                'radius_meters': radius_miles * 1609.34  # Convert miles to meters
            }
            
            # Apply additional filters
            if property_filter:
                if property_filter.min_size:
                    query_parts.append("AND p.square_feet >= :min_size")
                    params['min_size'] = property_filter.min_size
                
                if property_filter.max_size:
                    query_parts.append("AND p.square_feet <= :max_size")
                    params['max_size'] = property_filter.max_size
                
                if property_filter.min_price:
                    query_parts.append("AND f.sale_price >= :min_price")
                    params['min_price'] = property_filter.min_price
                
                if property_filter.max_price:
                    query_parts.append("AND f.sale_price <= :max_price")
                    params['max_price'] = property_filter.max_price
                
                if property_filter.year_built_min:
                    query_parts.append("AND p.year_built >= :year_built_min")
                    params['year_built_min'] = property_filter.year_built_min
                
                if property_filter.occupancy_min:
                    query_parts.append("AND pm.occupancy_rate >= :occupancy_min")
                    params['occupancy_min'] = property_filter.occupancy_min
                
                if property_filter.cap_rate_min:
                    query_parts.append("AND f.cap_rate >= :cap_rate_min")
                    params['cap_rate_min'] = property_filter.cap_rate_min
                
                if property_filter.cap_rate_max:
                    query_parts.append("AND f.cap_rate <= :cap_rate_max")
                    params['cap_rate_max'] = property_filter.cap_rate_max
            
            # Add scoring and ordering
            query_parts.extend([
                "ORDER BY (",
                "  ABS(p.square_feet - :target_size) * 0.3 +",
                "  ABS(EXTRACT(YEAR FROM f.sale_date) - EXTRACT(YEAR FROM :target_sale_date)) * 0.2 +",
                "  ST_Distance(l.coordinates, ST_Point(:target_lng, :target_lat)::geography) / 1609.34 * 0.2 +",
                "  ABS(f.cap_rate - :target_cap_rate) * 100 * 0.3",
                ") ASC",
                f"LIMIT {max_results}"
            ])
            
            params.update({
                'target_size': target_property.square_feet,
                'target_sale_date': target_property.sale_date or datetime.now(),
                'target_cap_rate': target_property.cap_rate or 0.06  # Default 6%
            })
            
            query = " ".join(query_parts)
            
            # Execute query
            result = await self.db_session.execute(text(query), params)
            rows = result.fetchall()
            
            # Convert to CompData objects
            comps = []
            for row in rows:
                comp = CompData(
                    property_id=row.property_id,
                    address=row.address,
                    property_type=row.property_type,
                    square_feet=row.square_feet,
                    year_built=row.year_built,
                    sale_price=row.sale_price,
                    sale_date=row.sale_date,
                    cap_rate=row.cap_rate,
                    noi=row.noi,
                    price_per_sqft=row.sale_price / row.square_feet if row.square_feet > 0 else None,
                    occupancy_rate=row.occupancy_rate,
                    distance_miles=0.0,  # Will calculate separately
                    similarity_score=0.0  # Will calculate separately
                )
                
                # Calculate distance and similarity score
                comp.distance_miles = await self._calculate_distance(
                    target_property.latitude, target_property.longitude,
                    row.latitude, row.longitude
                )
                
                comp.similarity_score = self._calculate_similarity_score(
                    target_property, comp
                )
                
                comps.append(comp)
            
            return comps
            
        except Exception as e:
            self.logger.error("Error finding comparable properties", error=str(e))
            raise FinDBError(f"Failed to find comparable properties: {e}")
    
    async def _calculate_distance(
        self, lat1: float, lng1: float, lat2: float, lng2: float
    ) -> float:
        """Calculate distance between two coordinates in miles."""
        # Haversine formula
        from math import radians, cos, sin, asin, sqrt
        
        # Convert to radians
        lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlng = lng2 - lng1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlng/2)**2
        c = 2 * asin(sqrt(a))
        r = 3956  # Radius of earth in miles
        
        return c * r
    
    def _calculate_similarity_score(
        self, target: PropertyData, comp: CompData
    ) -> float:
        """Calculate similarity score between target and comp property."""
        score = 100.0  # Start with perfect score
        
        # Size difference (up to -30 points)
        if target.square_feet and comp.square_feet:
            size_diff = abs(target.square_feet - comp.square_feet) / target.square_feet
            score -= min(30, size_diff * 100)
        
        # Age difference (up to -20 points)
        if target.year_built and comp.year_built:
            age_diff = abs(target.year_built - comp.year_built) / 50  # Normalize by 50 years
            score -= min(20, age_diff * 100)
        
        # Cap rate difference (up to -25 points)
        if target.cap_rate and comp.cap_rate:
            cap_diff = abs(target.cap_rate - comp.cap_rate) / 0.02  # Normalize by 2%
            score -= min(25, cap_diff * 100)
        
        # Distance penalty (up to -15 points)
        distance_penalty = min(15, comp.distance_miles * 3)
        score -= distance_penalty
        
        return max(0, score)


class MarketAnalyzer:
    """Market data analysis and trend calculations."""
    
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.logger = logger.bind(component="market_analyzer")
    
    async def get_market_data(
        self, request: MarketDataRequest
    ) -> MarketDataResult:
        """Get comprehensive market data for a geographic area."""
        try:
            # Query for market statistics
            query = """
            SELECT 
                COUNT(*) as property_count,
                AVG(f.sale_price) as avg_sale_price,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY f.sale_price) as median_sale_price,
                AVG(f.sale_price / p.square_feet) as avg_price_per_sqft,
                AVG(f.cap_rate) as avg_cap_rate,
                STDDEV(f.cap_rate) as cap_rate_stddev,
                AVG(pm.occupancy_rate) as avg_occupancy,
                AVG(f.noi) as avg_noi,
                MIN(f.sale_date) as earliest_sale,
                MAX(f.sale_date) as latest_sale
            FROM properties p
            JOIN financials f ON p.property_id = f.property_id
            JOIN property_metrics pm ON p.property_id = pm.property_id
            JOIN locations l ON p.location_id = l.location_id
            WHERE p.property_type = :property_type
            AND f.sale_date >= :start_date
            AND f.sale_date <= :end_date
            """
            
            params = {
                'property_type': request.property_type,
                'start_date': request.start_date,
                'end_date': request.end_date
            }
            
            # Add geographic constraints
            if request.city:
                query += " AND l.city = :city"
                params['city'] = request.city
            
            if request.state:
                query += " AND l.state = :state"
                params['state'] = request.state
            
            if request.zip_code:
                query += " AND l.zip_code = :zip_code"
                params['zip_code'] = request.zip_code
            
            # Execute market data query
            result = await self.db_session.execute(text(query), params)
            market_row = result.fetchone()
            
            if not market_row or market_row.property_count == 0:
                raise FinDBError("No market data found for specified criteria")
            
            # Get trend data (quarterly aggregation)
            trend_data = await self._get_trend_data(request)
            
            return MarketDataResult(
                property_type=request.property_type,
                geographic_area=f"{request.city or 'All'}, {request.state or 'All'}",
                date_range_start=request.start_date,
                date_range_end=request.end_date,
                total_properties=market_row.property_count,
                avg_sale_price=Decimal(str(market_row.avg_sale_price or 0)),
                median_sale_price=Decimal(str(market_row.median_sale_price or 0)),
                avg_price_per_sqft=Decimal(str(market_row.avg_price_per_sqft or 0)),
                avg_cap_rate=float(market_row.avg_cap_rate or 0),
                cap_rate_std=float(market_row.cap_rate_stddev or 0),
                avg_occupancy=float(market_row.avg_occupancy or 0),
                avg_noi=Decimal(str(market_row.avg_noi or 0)),
                trend_data=trend_data,
                market_velocity=len(trend_data),  # Simple proxy for market activity
                days_on_market_avg=None  # Would need additional data
            )
            
        except Exception as e:
            self.logger.error("Error getting market data", error=str(e))
            raise FinDBError(f"Failed to get market data: {e}")
    
    async def _get_trend_data(
        self, request: MarketDataRequest
    ) -> List[MarketTrendData]:
        """Get quarterly trend data for the market."""
        try:
            query = """
            SELECT 
                DATE_TRUNC('quarter', f.sale_date) as quarter,
                COUNT(*) as transaction_count,
                AVG(f.sale_price) as avg_price,
                AVG(f.cap_rate) as avg_cap_rate,
                AVG(f.sale_price / p.square_feet) as avg_price_per_sqft
            FROM properties p
            JOIN financials f ON p.property_id = f.property_id
            JOIN locations l ON p.location_id = l.location_id
            WHERE p.property_type = :property_type
            AND f.sale_date >= :start_date
            AND f.sale_date <= :end_date
            """
            
            params = {
                'property_type': request.property_type,
                'start_date': request.start_date,
                'end_date': request.end_date
            }
            
            # Add geographic constraints
            if request.city:
                query += " AND l.city = :city"
                params['city'] = request.city
            
            if request.state:
                query += " AND l.state = :state"
                params['state'] = request.state
            
            query += " GROUP BY quarter ORDER BY quarter"
            
            result = await self.db_session.execute(text(query), params)
            rows = result.fetchall()
            
            trend_data = []
            for row in rows:
                trend_data.append(MarketTrendData(
                    period=row.quarter.strftime("%Y-Q%q"),
                    transaction_count=row.transaction_count,
                    avg_price=Decimal(str(row.avg_price)),
                    avg_cap_rate=float(row.avg_cap_rate),
                    price_per_sqft=Decimal(str(row.avg_price_per_sqft)),
                    period_start=row.quarter,
                    period_end=row.quarter + timedelta(days=90)
                ))
            
            return trend_data
            
        except Exception as e:
            self.logger.error("Error getting trend data", error=str(e))
            return []


class FinancialCalculator:
    """Financial calculations and property valuation methods."""
    
    def __init__(self):
        self.logger = logger.bind(component="financial_calculator")
    
    def calculate_cap_rate(
        self, noi: Decimal, purchase_price: Decimal
    ) -> float:
        """Calculate capitalization rate."""
        if purchase_price <= 0:
            raise ValidationError("Purchase price must be greater than zero")
        
        return float(noi / purchase_price)
    
    def calculate_noi(
        self, gross_income: Decimal, operating_expenses: Decimal
    ) -> Decimal:
        """Calculate Net Operating Income."""
        return gross_income - operating_expenses
    
    def calculate_dscr(
        self, noi: Decimal, debt_service: Decimal
    ) -> float:
        """Calculate Debt Service Coverage Ratio."""
        if debt_service <= 0:
            raise ValidationError("Debt service must be greater than zero")
        
        return float(noi / debt_service)
    
    def calculate_ltv(
        self, loan_amount: Decimal, property_value: Decimal
    ) -> float:
        """Calculate Loan-to-Value ratio."""
        if property_value <= 0:
            raise ValidationError("Property value must be greater than zero")
        
        return float(loan_amount / property_value)
    
    def calculate_irr(
        self, cash_flows: List[Decimal], periods: int = None
    ) -> float:
        """Calculate Internal Rate of Return using numpy."""
        if len(cash_flows) < 2:
            raise ValidationError("Need at least 2 cash flows for IRR calculation")
        
        # Convert to numpy array
        cash_flows_np = np.array([float(cf) for cf in cash_flows])
        
        # Use numpy's IRR calculation
        try:
            irr = np.irr(cash_flows_np) if hasattr(np, 'irr') else self._calculate_irr_manual(cash_flows_np)
            return float(irr) if irr is not None else 0.0
        except:
            return 0.0
    
    def _calculate_irr_manual(self, cash_flows: np.ndarray) -> float:
        """Manual IRR calculation using Newton-Raphson method."""
        def npv(rate):
            return sum(cf / (1 + rate) ** i for i, cf in enumerate(cash_flows))
        
        def npv_derivative(rate):
            return sum(-i * cf / (1 + rate) ** (i + 1) for i, cf in enumerate(cash_flows))
        
        # Initial guess
        rate = 0.1
        tolerance = 1e-6
        max_iterations = 100
        
        for _ in range(max_iterations):
            npv_val = npv(rate)
            if abs(npv_val) < tolerance:
                return rate
            
            npv_deriv = npv_derivative(rate)
            if abs(npv_deriv) < tolerance:
                break
            
            rate = rate - npv_val / npv_deriv
        
        return rate
    
    def calculate_property_value_income_approach(
        self, noi: Decimal, cap_rate: float
    ) -> Decimal:
        """Calculate property value using income approach."""
        if cap_rate <= 0:
            raise ValidationError("Cap rate must be greater than zero")
        
        return noi / Decimal(str(cap_rate))


class FinDBService:
    """Main Financial Database service orchestrator."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = logger.bind(component="findb_service")
        
        # Initialize database
        self.db_config = DatabaseConfig(
            host=settings.rds_host,
            port=settings.rds_port,
            database=settings.rds_database,
            username=settings.rds_username,
            password=settings.rds_password.get_secret_value() if settings.rds_password else "",
        )
        
        # Create async engine
        db_url = (
            f"postgresql+asyncpg://{self.db_config.username}:{self.db_config.password}"
            f"@{self.db_config.host}:{self.db_config.port}/{self.db_config.database}"
            f"?ssl={self.db_config.ssl_mode}"
        )
        
        self.engine = create_async_engine(
            db_url,
            pool_size=self.db_config.pool_size,
            max_overflow=self.db_config.max_overflow,
            pool_timeout=self.db_config.pool_timeout,
            pool_recycle=self.db_config.pool_recycle,
            echo=settings.debug
        )
        
        self.async_session = async_sessionmaker(
            bind=self.engine, 
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # Initialize analyzers
        self.financial_calculator = FinancialCalculator()
    
    async def process_query(self, query: FinDBQuery) -> FinDBResponse:
        """Process a financial database query."""
        try:
            self.logger.info("Processing FinDB query", query_type=query.query_type)
            
            async with self.async_session() as session:
                if query.query_type == FinDBQueryType.COMPS:
                    analyzer = CompsAnalyzer(session)
                    comps = await analyzer.find_comparable_properties(
                        target_property=query.target_property,
                        radius_miles=query.radius_miles or 5.0,
                        max_results=query.max_results or 10,
                        property_filter=query.property_filter
                    )
                    
                    return FinDBResponse(
                        query_id=query.query_id,
                        query_type=query.query_type,
                        success=True,
                        result=CompsResult(
                            target_property_id=query.target_property.property_id,
                            comparable_properties=comps,
                            search_radius_miles=query.radius_miles or 5.0,
                            total_found=len(comps)
                        )
                    )
                
                elif query.query_type == FinDBQueryType.MARKET_DATA:
                    analyzer = MarketAnalyzer(session)
                    market_data = await analyzer.get_market_data(query.market_request)
                    
                    return FinDBResponse(
                        query_id=query.query_id,
                        query_type=query.query_type,
                        success=True,
                        result=market_data
                    )
                
                elif query.query_type == FinDBQueryType.VALUATION:
                    result = await self._perform_valuation(session, query.valuation_request)
                    
                    return FinDBResponse(
                        query_id=query.query_id,
                        query_type=query.query_type,
                        success=True,
                        result=result
                    )
                
                elif query.query_type == FinDBQueryType.CAP_RATE_ANALYSIS:
                    result = await self._perform_cap_rate_analysis(session, query.cap_rate_request)
                    
                    return FinDBResponse(
                        query_id=query.query_id,
                        query_type=query.query_type,
                        success=True,
                        result=result
                    )
                
                elif query.query_type == FinDBQueryType.TREND_ANALYSIS:
                    result = await self._perform_trend_analysis(session, query.trend_request)
                    
                    return FinDBResponse(
                        query_id=query.query_id,
                        query_type=query.query_type,
                        success=True,
                        result=result
                    )
                
                else:
                    raise ValidationError(f"Unsupported query type: {query.query_type}")
        
        except Exception as e:
            self.logger.error("Error processing FinDB query", error=str(e))
            return FinDBResponse(
                query_id=query.query_id,
                query_type=query.query_type,
                success=False,
                error_message=str(e),
                error_code="FINDB_PROCESSING_ERROR"
            )
    
    async def _perform_valuation(
        self, session: AsyncSession, request: PropertyValuationRequest
    ) -> PropertyValuationResult:
        """Perform comprehensive property valuation."""
        try:
            # Get property financial data
            query = """
            SELECT p.*, f.*, pm.*
            FROM properties p
            JOIN financials f ON p.property_id = f.property_id
            JOIN property_metrics pm ON p.property_id = pm.property_id
            WHERE p.property_id = :property_id
            """
            
            result = await session.execute(text(query), {'property_id': request.property_id})
            prop_data = result.fetchone()
            
            if not prop_data:
                raise FinDBError(f"Property {request.property_id} not found")
            
            # Calculate various valuation approaches
            income_value = None
            if prop_data.noi and request.market_cap_rate:
                income_value = self.financial_calculator.calculate_property_value_income_approach(
                    Decimal(str(prop_data.noi)), request.market_cap_rate
                )
            
            # Get comparable sales for sales comparison approach
            comps_analyzer = CompsAnalyzer(session)
            target_prop = PropertyData(
                property_id=prop_data.property_id,
                address=prop_data.address,
                property_type=prop_data.property_type,
                square_feet=prop_data.square_feet,
                year_built=prop_data.year_built,
                latitude=prop_data.latitude,
                longitude=prop_data.longitude,
                cap_rate=prop_data.cap_rate,
                sale_date=prop_data.sale_date
            )
            
            comps = await comps_analyzer.find_comparable_properties(
                target_property=target_prop,
                radius_miles=5.0,
                max_results=5
            )
            
            # Calculate sales comparison value
            sales_comparison_value = None
            if comps:
                avg_price_per_sqft = sum(c.price_per_sqft or 0 for c in comps) / len(comps)
                if avg_price_per_sqft > 0:
                    sales_comparison_value = Decimal(str(avg_price_per_sqft)) * prop_data.square_feet
            
            # Calculate financial metrics
            metrics = FinancialMetrics(
                cap_rate=float(prop_data.cap_rate or 0),
                noi=Decimal(str(prop_data.noi or 0)),
                gross_income=Decimal(str(prop_data.gross_income or 0)),
                operating_expenses=Decimal(str(prop_data.operating_expenses or 0)),
                occupancy_rate=float(prop_data.occupancy_rate or 0),
                debt_service_coverage=None,  # Would need loan data
                loan_to_value=None,  # Would need loan data
                price_per_sqft=Decimal(str(prop_data.sale_price / prop_data.square_feet)) if prop_data.sale_price and prop_data.square_feet > 0 else None
            )
            
            return PropertyValuationResult(
                property_id=request.property_id,
                valuation_date=datetime.now(),
                income_approach_value=income_value,
                sales_comparison_value=sales_comparison_value,
                cost_approach_value=None,  # Would need construction cost data
                final_value_estimate=income_value or sales_comparison_value,
                confidence_level=85.0 if income_value and sales_comparison_value else 70.0,
                comparable_sales_count=len(comps),
                market_conditions="stable",  # Would analyze trend data
                financial_metrics=metrics,
                valuation_method="income_approach" if income_value else "sales_comparison"
            )
            
        except Exception as e:
            self.logger.error("Error performing valuation", error=str(e))
            raise FinDBError(f"Failed to perform valuation: {e}")
    
    async def _perform_cap_rate_analysis(
        self, session: AsyncSession, request: CapRateAnalysisRequest
    ) -> CapRateAnalysisResult:
        """Perform cap rate analysis for market area."""
        try:
            # Query for cap rates in the area
            query = """
            SELECT 
                f.cap_rate,
                f.sale_price,
                f.noi,
                p.square_feet,
                f.sale_date
            FROM properties p
            JOIN financials f ON p.property_id = f.property_id
            JOIN locations l ON p.location_id = l.location_id
            WHERE p.property_type = :property_type
            AND l.city = :city
            AND l.state = :state
            AND f.cap_rate IS NOT NULL
            AND f.sale_date >= :start_date
            ORDER BY f.sale_date DESC
            """
            
            params = {
                'property_type': request.property_type,
                'city': request.city,
                'state': request.state,
                'start_date': datetime.now() - timedelta(days=365 * 2)  # Last 2 years
            }
            
            result = await session.execute(text(query), params)
            rows = result.fetchall()
            
            if not rows:
                raise FinDBError("No cap rate data found for specified criteria")
            
            # Calculate statistics
            cap_rates = [float(row.cap_rate) for row in rows]
            
            avg_cap_rate = np.mean(cap_rates)
            median_cap_rate = np.median(cap_rates)
            std_cap_rate = np.std(cap_rates)
            min_cap_rate = np.min(cap_rates)
            max_cap_rate = np.max(cap_rates)
            
            # Calculate percentiles
            percentile_25 = np.percentile(cap_rates, 25)
            percentile_75 = np.percentile(cap_rates, 75)
            
            return CapRateAnalysisResult(
                property_type=request.property_type,
                geographic_area=f"{request.city}, {request.state}",
                analysis_date=datetime.now(),
                sample_size=len(cap_rates),
                avg_cap_rate=float(avg_cap_rate),
                median_cap_rate=float(median_cap_rate),
                std_deviation=float(std_cap_rate),
                min_cap_rate=float(min_cap_rate),
                max_cap_rate=float(max_cap_rate),
                percentile_25=float(percentile_25),
                percentile_75=float(percentile_75),
                market_trend="stable",  # Would calculate from time series
                data_quality_score=85.0  # Based on sample size and recency
            )
            
        except Exception as e:
            self.logger.error("Error performing cap rate analysis", error=str(e))
            raise FinDBError(f"Failed to perform cap rate analysis: {e}")
    
    async def _perform_trend_analysis(
        self, session: AsyncSession, request: TrendAnalysisRequest
    ) -> TrendAnalysisResult:
        """Perform market trend analysis."""
        try:
            analyzer = MarketAnalyzer(session)
            
            # Convert to MarketDataRequest for trend analysis
            market_request = MarketDataRequest(
                property_type=request.property_type,
                city=request.city,
                state=request.state,
                start_date=request.start_date,
                end_date=request.end_date
            )
            
            trend_data = await analyzer._get_trend_data(market_request)
            
            if len(trend_data) < 2:
                raise FinDBError("Insufficient data for trend analysis")
            
            # Calculate trend metrics
            price_trend = self._calculate_price_trend(trend_data)
            volume_trend = self._calculate_volume_trend(trend_data)
            
            return TrendAnalysisResult(
                property_type=request.property_type,
                geographic_area=f"{request.city}, {request.state}",
                analysis_period_start=request.start_date,
                analysis_period_end=request.end_date,
                trend_periods=trend_data,
                overall_price_trend=price_trend,
                volume_trend=volume_trend,
                volatility_index=self._calculate_volatility(trend_data),
                market_momentum="positive" if price_trend > 0 else "negative",
                forecast_confidence=75.0
            )
            
        except Exception as e:
            self.logger.error("Error performing trend analysis", error=str(e))
            raise FinDBError(f"Failed to perform trend analysis: {e}")
    
    def _calculate_price_trend(self, trend_data: List[MarketTrendData]) -> float:
        """Calculate price trend percentage."""
        if len(trend_data) < 2:
            return 0.0
        
        first_price = float(trend_data[0].avg_price)
        last_price = float(trend_data[-1].avg_price)
        
        return ((last_price - first_price) / first_price) * 100
    
    def _calculate_volume_trend(self, trend_data: List[MarketTrendData]) -> float:
        """Calculate volume trend percentage."""
        if len(trend_data) < 2:
            return 0.0
        
        first_volume = trend_data[0].transaction_count
        last_volume = trend_data[-1].transaction_count
        
        return ((last_volume - first_volume) / first_volume) * 100
    
    def _calculate_volatility(self, trend_data: List[MarketTrendData]) -> float:
        """Calculate price volatility index."""
        if len(trend_data) < 3:
            return 0.0
        
        prices = [float(td.avg_price) for td in trend_data]
        returns = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]
        
        return float(np.std(returns)) * 100 if returns else 0.0
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the database service."""
        try:
            async with self.async_session() as session:
                # Test database connectivity
                result = await session.execute(text("SELECT 1"))
                result.fetchone()
                
                # Check data freshness
                freshness_result = await session.execute(text("""
                    SELECT MAX(f.sale_date) as latest_sale
                    FROM financials f
                """))
                latest_sale = freshness_result.fetchone()
                
                days_since_latest = (datetime.now().date() - latest_sale.latest_sale).days if latest_sale.latest_sale else 999
                
                return {
                    "status": "healthy",
                    "database_connected": True,
                    "latest_data_age_days": days_since_latest,
                    "data_freshness": "good" if days_since_latest < 30 else "stale",
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            self.logger.error("Health check failed", error=str(e))
            return {
                "status": "unhealthy",
                "database_connected": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def cleanup(self):
        """Cleanup resources."""
        if hasattr(self, 'engine'):
            await self.engine.dispose()
            self.logger.info("FinDB service cleaned up")